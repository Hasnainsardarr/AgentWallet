"""Response schemas."""
from pydantic import BaseModel
from typing import Optional


class WalletInfo(BaseModel):
    wallet_id: str
    address: str
    network: str
    assets: Optional[list[dict]] = None


class ChatResponse(BaseModel):
    response: str
    wallet: Optional[WalletInfo] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "response": "Wallet created successfully...",
                "wallet": {
                    "wallet_id": "0x123...",
                    "address": "0x123...",
                    "network": "base-sepolia",
                    "assets": [
                        {"symbol": "ETH", "balance": "0.0001", "decimals": 18},
                        {"symbol": "USDC", "balance": "10", "decimals": 6}
                    ]
                }
            }
        }

