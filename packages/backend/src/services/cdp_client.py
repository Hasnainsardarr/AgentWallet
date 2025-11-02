"""CDP SDK wrapper for Server Wallet v2."""
from typing import Dict, Optional, List
from cdp import CdpClient, parse_units  # SDK
from ..config import Settings
from ..utils.logging import get_logger
from cdp.evm_transaction_types import TransactionRequestEIP1559
from eth_abi import encode as abi_encode
from eth_utils import to_checksum_address
from .evm_readonly import get_native_eth_balance, get_erc20_balance

logger = get_logger(__name__)

USDC_BASE_SEPOLIA = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"

class CdpSdk:
    """
    Thin wrapper over the official CDP Python SDK.

    We expose the same methods your routes use: create_account, send_usdc, get_balance.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        # If you pass nothing, SDK reads from env. Otherwise, you can pass here.
        self._client = CdpClient(
            api_key_id=settings.cdp_api_key_id or None,
            api_key_secret=settings.cdp_api_key_secret or None,
            wallet_secret=settings.cdp_wallet_secret or None,
        )
        self._network = settings.network

    @property
    def client(self) -> CdpClient:
        return self._client

    @property
    def network(self) -> str:
        return self._network

    async def aclose(self):
        # SDK client is an async context manager; close its session when app stops.
        await self._client.aclose()

    # ---- Operations used by routes ----

    async def create_account(self, *, name: Optional[str] = None) -> Dict:
        # EVM account (EOA). Returns an object with .address per SDK.
        acct = await self._client.evm.create_account(name=name)  # or get_or_create_account
        return {"id": acct.address, "address": acct.address, "network": self._network}

    async def send_usdc(self, *, from_address: str, to_address: str, amount: str,
                        network: Optional[str] = None) -> Dict:
        """
        Send USDC using CDP Python SDK by calling ERC-20 transfer().
        - Builds an EIP-1559 transaction with `to` = USDC contract on Base Sepolia
        - `data` = abi-encoded transfer(recipient, amount_wei)
        """
        net = network or self._network

        # Base Sepolia USDC contract (official Circle docs)
        USDC_BASE_SEPOLIA = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"  # 6 decimals
        # ref: https://developers.circle.com/stablecoins/usdc-contract-addresses  :contentReference[oaicite:1]{index=1}

        # Convert human amount string (e.g., "0.01") to base units for USDC (6 dp)
        amount_base = int(parse_units(amount, 6))

        # ABI-encode ERC20 transfer(address,uint256)
        # function selector: keccak256("transfer(address,uint256)")[:4] = 0xa9059cbb
        selector = bytes.fromhex("a9059cbb")
        to_addr_cs = to_checksum_address(to_address)
        data_tail = abi_encode(["address", "uint256"], [to_addr_cs, amount_base])
        data_hex = "0x" + (selector + data_tail).hex()

        tx = TransactionRequestEIP1559(
            to=USDC_BASE_SEPOLIA,
            value=0,             # ERC-20 transfer never sends native ETH
            data=data_hex,
            # Optional advanced fields if you want to override gas/nonce:
            # gas=..., maxFeePerGas=..., maxPriorityFeePerGas=..., nonce=...
        )

        tx_hash = await self._client.evm.send_transaction(
            address=from_address,
            transaction=tx,
            network=net,
        )  # returns a hex tx hash per SDK docs. :contentReference[oaicite:2]{index=2}

        return {"txHash": tx_hash, "status": "submitted"}


    async def get_balance(self, *, address: str, network: Optional[str] = None) -> Dict:
        """
        Reliable balances:
        - Always fetch native ETH via RPC.
        - Always fetch USDC via ERC-20 balanceOf via RPC (6 decimals).
        - Also try SDK's list_token_balances for any extra tokens.
        """
        net = network or self._network
        assets: List[Dict] = []

        # 1) Native ETH (RPC)
        try:
            eth = await get_native_eth_balance(address, net)
            assets.append({"symbol": "ETH", "balance": f"{eth:.18f}".rstrip("0").rstrip("."), "decimals": 18})
            logger.info(f"[balance] ETH={eth} on {net}")
        except Exception as e:
            logger.warning(f"[balance] native ETH read failed: {e}")

        # 2) USDC (RPC)
        try:
            usdc = await get_erc20_balance(address, USDC_BASE_SEPOLIA, net, decimals=6)
            assets.append({"symbol": "USDC", "balance": f"{usdc:.6f}".rstrip("0").rstrip("."), "decimals": 6})
            logger.info(f"[balance] USDC={usdc} on {net}")
        except Exception as e:
            logger.warning(f"[balance] USDC read failed: {e}")

        # 3) Best-effort: SDK token list (optional, may lag / omit ETH)
        try:
            balances = await self._client.evm.list_token_balances(address=address, network=net)
            for b in balances or []:
                symbol = (getattr(b, "symbol", None) or getattr(b, "token_symbol", None) or getattr(b, "asset_symbol", None))
                raw = (getattr(b, "balance", None) or getattr(b, "amount", None) or getattr(b, "value", None))
                dec = (getattr(b, "decimals", None) or getattr(b, "token_decimals", None) or getattr(b, "asset_decimals", None))
                if symbol and raw is not None and dec is not None:
                    symbol_u = str(symbol).upper()
                    # Convert string/int to float based on decimals
                    val = float(raw) if isinstance(raw, (int, float)) else float(raw) if "." in str(raw) else int(raw)/ (10**int(dec))
                    # Merge if already present from RPC
                    existing = next((a for a in assets if a["symbol"] == symbol_u), None)
                    if existing:
                        existing["balance"] = max(float(existing["balance"]), val)
                    else:
                        assets.append({"symbol": symbol_u, "balance": str(val), "decimals": int(dec)})
        except Exception as e:
            logger.info(f"[balance] SDK list_token_balances skipped/failed: {e}")

        return {"assets": assets}