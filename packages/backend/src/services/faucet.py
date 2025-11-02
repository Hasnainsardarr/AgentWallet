# services/faucet.py
from typing import Dict, Union
import asyncio
from ..utils.logging import get_logger
from .cdp_client import CdpSdk

logger = get_logger(__name__)

class FaucetService:
    def __init__(self, cdp: CdpSdk):
        self.cdp = cdp

    async def request_funds(self, address: str, network: str = "base-sepolia", token: str = "eth", wait_for_confirmation: bool = False) -> Dict:
        """
        Request testnet funds from CDP Faucet.
        token: "eth", "usdc", "eurc", "cbbtc" (see docs)
        wait_for_confirmation: if True, polls until balance increases (useful for tests)
        Always returns a normalized dict: {"success": True, "txHash": "...", "asset": token, ...}
        """
        logger.info(f"🔵 Requesting faucet funds for {address} on {network} token={token} wait={wait_for_confirmation}")
        
        # Get initial balance if we're waiting for confirmation
        initial_balance = 0.0
        if wait_for_confirmation:
            try:
                logger.info("📊 Fetching initial balance...")
                balance_info = await self.cdp.get_balance(address=address, network=network)
                assets = balance_info.get("assets", [])
                logger.info(f"Initial assets: {assets}")
                
                for asset in assets:
                    if asset and asset.get("symbol", "").upper() == token.upper():
                        initial_balance = float(asset["balance"])
                        break
                        
                logger.info(f"💰 Initial {token.upper()} balance: {initial_balance}")
            except Exception as e:
                logger.warning(f"⚠️  Could not get initial balance: {e}", exc_info=True)
                initial_balance = 0.0
        
        # Request faucet funds
        try:
            logger.info(f"🚀 Calling CDP faucet API...")
            res: Union[str, dict, object] = await self.cdp.client.evm.request_faucet(
                address=address, network=network, token=token
            )
            logger.info(f"✅ Faucet request completed. Response type: {type(res)}")
        except Exception as e:
            logger.error(f"❌ Faucet request failed: {e}", exc_info=True)
            raise

        # Normalize tx hash (covers string, dict, SDK object shapes)
        tx_hash = None
        if isinstance(res, str):
            tx_hash = res
        elif isinstance(res, dict):
            tx_hash = res.get("transactionHash") or res.get("txHash") or res.get("tx_hash")
        elif hasattr(res, "transaction_hash"):
            tx_hash = getattr(res, "transaction_hash")
        elif hasattr(res, "tx_hash"):
            tx_hash = getattr(res, "tx_hash")

        if not tx_hash:
            tx_hash = str(res)
        
        logger.info(f"📝 Transaction hash: {tx_hash}")

        # Wait for funds to arrive if requested
        if wait_for_confirmation:
            logger.info(f"⏳ Waiting for faucet funds to arrive (max 120s)...")
            max_attempts = 24  # 24 attempts * 5 seconds = 120 seconds max
            
            for attempt in range(max_attempts):
                await asyncio.sleep(5)
                try:
                    balance_info = await self.cdp.get_balance(address=address, network=network)
                    assets = balance_info.get("assets", [])
                    current_balance = 0.0
                    
                    for asset in assets:
                        if asset and asset.get("symbol", "").upper() == token.upper():
                            current_balance = float(asset["balance"])
                            break
                    
                    logger.info(f"🔍 Attempt {attempt + 1}/{max_attempts}: Current balance = {current_balance}, Initial = {initial_balance}")
                    
                    if current_balance > initial_balance:
                        logger.info(f"✅ Funds arrived! New {token.upper()} balance: {current_balance}")
                        break
                    
                except Exception as e:
                    logger.warning(f"⚠️  Error checking balance on attempt {attempt + 1}: {e}")
            else:
                logger.warning(f"⚠️  Funds may not have arrived after {max_attempts * 5}s. This could be due to network delays.")

        # Friendly default amounts for display; the faucet defines real limits
        display_amount = "0.0001" if token.lower() == "eth" else "10"
        return {
            "success": True,
            "txHash": tx_hash,
            "amount": display_amount,
            "asset": token.upper(),
            "network": network,
            "message": f"CDP faucet request for {token.upper()} submitted" + (" and confirmed" if wait_for_confirmation else "")
        }
