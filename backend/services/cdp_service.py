"""CDP SDK service."""
import logging
import asyncio
import re
from typing import Dict, List, Optional
from cdp import CdpClient, parse_units
from cdp.evm_transaction_types import TransactionRequestEIP1559
from eth_abi import encode as abi_encode
from eth_utils import to_checksum_address

import httpx
from services.faucet_service import FaucetService

from utils.config import settings

ADDR_RE = re.compile(r"0x[a-fA-F0-9]{40}")

logger = logging.getLogger(__name__)


class CDPService:
    """Service for interacting with Coinbase CDP."""
    
    def __init__(self):
        self.client = CdpClient(
            api_key_id=settings.cdp_api_key_id or None,
            api_key_secret=settings.cdp_api_key_secret or None,
            wallet_secret=settings.cdp_wallet_secret or None,
        )
        self.network = settings.network

    def _rpc_url_for(self, network: Optional[str] = None) -> str:
        """Return JSON-RPC URL based on network or settings override."""
        if settings.rpc_url:
            return settings.rpc_url
        net = (network or self.network or "").lower()
        if net in ("base-sepolia", "base_sepolia", "basesepolia"):
            return "https://sepolia.base.org"
        if net in ("base", "base-mainnet", "base_mainnet", "basemainnet"):
            return "https://mainnet.base.org"
        return "https://sepolia.base.org"

    def _extract_address(self, value: str) -> Optional[str]:
        """Extract the first 0x-prefixed 40-hex address and return checksummed."""
        if not isinstance(value, str):
            return None
        m = ADDR_RE.search(value.strip())
        if not m:
            return None
        try:
            return to_checksum_address(m.group(0))
        except Exception:
            return None
    
    async def create_wallet(self) -> Dict:
        """Create a new wallet."""
        try:
            account = await self.client.evm.create_account()
            return {
                "id": account.address,  # Match old format
                "address": account.address,
                "network": self.network
            }
        except Exception as e:
            logger.error(f"Wallet creation failed: {e}")
            raise
    
    async def get_balance(self, address: str, network: str = None) -> Dict:
        """Get wallet balance via RPC for reliability (ETH + USDC)."""
        net = network or self.network
        try:
            addr = self._extract_address(address)
            if not addr:
                raise ValueError(f"Invalid EVM address: {address!r}")

            rpc_url = self._rpc_url_for(net)
            assets: List[Dict] = []

            # Get ETH balance via RPC
            try:
                eth_result = await self._rpc_call(rpc_url, "eth_getBalance", [addr, "latest"])
                eth_wei = int(eth_result, 16)
                eth_balance = eth_wei / 10**18
                assets.append({"symbol": "ETH", "balance": f"{eth_balance:.18f}".rstrip("0").rstrip("."), "decimals": 18})
            except Exception as e:
                logger.warning(f"ETH balance fetch failed: {e}")

            # Get USDC balance via RPC
            try:
                usdc_token = settings.usdc_contract_address or "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
                usdc_balance = await self._get_erc20_balance(rpc_url, addr, usdc_token)
                assets.append({"symbol": "USDC", "balance": f"{usdc_balance:.6f}".rstrip("0").rstrip("."), "decimals": 6})
            except Exception as e:
                logger.warning(f"USDC balance fetch failed: {e}")

            # Best-effort: try SDK balances for other assets
            try:
                balances = await self.client.evm.list_token_balances(address=addr, network=net)
                for b in balances or []:
                    symbol = (getattr(b, "symbol", None) or getattr(b, "token_symbol", None) or getattr(b, "asset_symbol", None))
                    raw = (getattr(b, "balance", None) or getattr(b, "amount", None) or getattr(b, "value", None))
                    dec = (getattr(b, "decimals", None) or getattr(b, "token_decimals", None) or getattr(b, "asset_decimals", None))
                    if symbol and raw is not None and dec is not None:
                        symbol_u = str(symbol).upper()
                        try:
                            val = float(raw) if isinstance(raw, (int, float)) else float(raw) if "." in str(raw) else int(raw) / (10**int(dec))
                            if not any(a["symbol"] == symbol_u for a in assets):
                                assets.append({"symbol": symbol_u, "balance": str(val), "decimals": int(dec)})
                        except Exception:
                            continue
            except Exception as e:
                logger.debug(f"SDK list_token_balances skipped: {e}")

            return {"assets": assets}
        except Exception as e:
            logger.error(f"Balance fetch failed: {e}")
            # Return empty assets to avoid crashing callers
            return {"assets": []}
    
    def _pad_32(self, hex_no_0x: str) -> str:
        """Pad hex string to 32 bytes (64 hex chars)."""
        return hex_no_0x.rjust(64, "0")
    
    def _encode_address_32(self, addr: str) -> str:
        """Encode address for ERC20 call - strip 0x and pad to 32 bytes."""
        return self._pad_32(addr.lower().replace("0x", ""))
    
    async def _get_erc20_balance(self, rpc_url: str, address: str, token_address: str, decimals: int = 6) -> float:
        """Get ERC20 token balance (matching old implementation)."""
        # ERC20 balanceOf(address) => 0x70a08231 + 32-byte address
        selector = "70a08231"
        data = "0x" + selector + self._encode_address_32(address)
        
        call_obj = {"to": token_address, "data": data}
        result = await self._rpc_call(rpc_url, "eth_call", [call_obj, "latest"])
        raw = int(result, 16)
        return raw / (10**decimals)
    
    async def _rpc_call(self, rpc_url: str, method: str, params: list) -> str:
        """Make RPC call to given RPC URL."""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": 1
        }
        
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(rpc_url, json=payload)
            response.raise_for_status()
            data = response.json()
            if "error" in data:
                raise Exception(f"RPC error: {data['error']}")
            return data["result"]
    
    async def request_faucet(
        self,
        address: str,
        token: str = "eth",
        wait_for_confirmation: bool = False
    ) -> Dict:
        """Request testnet funds using CDP SDK (preferred), fallback to external faucet if configured."""
        try:
            token_clean = (token or "eth").strip().lower()
            if token_clean not in ("eth", "usdc", "eurc", "cbbtc"):
                raise ValueError("Unsupported faucet token. Use 'eth', 'usdc', 'eurc', or 'cbbtc'.")

            addr = self._extract_address(address)
            if not addr:
                raise ValueError(f"Invalid EVM address: {address!r}")

            tx_hash = None
            used_sdk = False
            # Preferred: CDP SDK faucet
            try:
                result = await self.client.evm.request_faucet(
                    address=addr,
                    network=self.network,
                    token=token_clean,
                )

                # Normalize tx hash
                if isinstance(result, str):
                    tx_hash = result
                elif isinstance(result, dict):
                    tx_hash = result.get("transactionHash") or result.get("txHash") or result.get("tx_hash")
                elif hasattr(result, "transaction_hash"):
                    tx_hash = getattr(result, "transaction_hash")
                elif hasattr(result, "tx_hash"):
                    tx_hash = getattr(result, "tx_hash")
                else:
                    tx_hash = str(result)
                used_sdk = True
            except Exception as e:
                logger.error(f"CDP SDK faucet failed: {e}", exc_info=True)
                # Fallback: external faucet endpoint if configured
                if settings.faucet_endpoint:
                    try:
                        faucet = FaucetService()
                        data = await faucet.request(address=addr, token=token_clean, network=self.network)
                        tx_hash = data.get("txHash") or data.get("transactionHash")
                    except Exception as e2:
                        logger.error(f"External faucet request failed: {e2}", exc_info=True)
                        raise
                else:
                    raise

            if wait_for_confirmation:
                logger.info("Waiting for funds to arrive...")
                initial = 0.0
                try:
                    bal0 = await self.get_balance(addr)
                    for a in bal0.get("assets", []):
                        if a.get("symbol", "").upper() == token_clean.upper():
                            initial = float(a.get("balance", 0) or 0)
                except Exception:
                    pass
                for _ in range(24):
                    await asyncio.sleep(5)
                    try:
                        bal = await self.get_balance(addr)
                        current = 0.0
                        for a in bal.get("assets", []):
                            if a.get("symbol", "").upper() == token_clean.upper():
                                current = float(a.get("balance", 0) or 0)
                        if current > initial:
                            break
                    except Exception:
                        continue

            return {
                "tx_hash": tx_hash,
                "status": "submitted",
                "asset": token_clean.upper(),
                "source": "sdk" if used_sdk else "external",
            }
        except Exception as e:
            logger.error(f"Faucet request failed: {e}", exc_info=True)
            raise
    
    async def transfer_usdc(
        self,
        from_address: str,
        to_address: str,
        amount: str,
        network: Optional[str] = None,
        usdc_contract: Optional[str] = None,
    ) -> Dict:
        """Transfer USDC using EIP-1559 transaction via CDP SDK."""
        try:
            src = self._extract_address(from_address)
            dst = self._extract_address(to_address)
            if not src or not dst:
                raise ValueError("Invalid from/to address.")

            amount_base = int(parse_units(str(amount), 6))

            selector = bytes.fromhex("a9059cbb")  # transfer(address,uint256)
            to_addr_cs = to_checksum_address(dst)
            data_tail = abi_encode(["address", "uint256"], [to_addr_cs, amount_base])
            data_hex = "0x" + (selector + data_tail).hex()

            usdc_to = to_checksum_address(usdc_contract or settings.usdc_contract_address)

            tx = TransactionRequestEIP1559(
                to=usdc_to,
                value=0,
                data=data_hex,
            )

            tx_hash = await self.client.evm.send_transaction(
                address=src,
                transaction=tx,
                network=network or self.network,
            )

            return {"tx_hash": tx_hash, "status": "submitted"}
        except Exception as e:
            logger.error(f"Transfer failed: {e}")
            raise
    
    async def close(self):
        """Close client connection."""
        await self.client.aclose()

