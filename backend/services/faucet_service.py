"""Simple faucet service client using settings.faucet_endpoint."""
from typing import Optional, Dict
import logging
import httpx

from utils.config import settings

logger = logging.getLogger(__name__)


class FaucetService:
    """Client for an external faucet endpoint that dispenses testnet funds."""

    def __init__(self, endpoint: Optional[str] = None):
        self.endpoint = endpoint or settings.faucet_endpoint

    async def request(self, *, address: str, token: str, network: Optional[str] = None) -> Dict:
        if not self.endpoint:
            raise RuntimeError("Faucet endpoint not configured. Set settings.faucet_endpoint.")
        payload = {
            "address": address,
            "token": token,
            "network": (network or settings.network),
        }
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(self.endpoint, json=payload)
            resp.raise_for_status()
            return resp.json()
