"""Pydantic models for API requests and responses."""
from pydantic import BaseModel, Field, validator
from typing import Optional
from decimal import Decimal
from ..utils.address import is_valid_eth_address


class CreateWalletRequest(BaseModel):
    """Request to create a new wallet."""
    user_id: Optional[str] = Field(None, description="Optional user ID")


class CreateWalletResponse(BaseModel):
    """Response for wallet creation."""
    wallet_id: str
    address: str
    network: str


class FundTestnetRequest(BaseModel):
    """Request to fund a wallet with testnet tokens."""
    wallet_id: str


class FundTestnetResponse(BaseModel):
    """Response for testnet funding."""
    faucet_tx: str
    success: bool
    message: Optional[str] = None


class GetWalletResponse(BaseModel):
    """Response for wallet info."""
    wallet_id: str
    address: str
    network: str
    assets: Optional[list] = None


class GrantAuthorityRequest(BaseModel):
    """Request to grant spending authority."""
    wallet_id: str
    per_tx_max: float = Field(..., gt=0, description="Maximum per transaction")
    daily_cap: float = Field(..., gt=0, description="Maximum per day")


class RevokeAuthorityRequest(BaseModel):
    """Request to revoke spending authority."""
    wallet_id: str


class AuthorityResponse(BaseModel):
    """Response for grant/revoke operations."""
    ok: bool
    wallet_id: str
    message: Optional[str] = None


class TransferRequest(BaseModel):
    """Request to transfer funds."""
    wallet_id: str
    to: str = Field(..., description="Destination EVM address")
    amount: float = Field(..., gt=0, description="Amount to transfer")
    asset: str = Field(default="USDC", description="Asset symbol")
    idempotency_key: str = Field(..., alias="idempotencyKey", description="Client-supplied UUID")
    
    @validator("to")
    def validate_address(cls, v):
        """Validate EVM address format."""
        if not is_valid_eth_address(v):
            raise ValueError(f"Invalid EVM address: {v}")
        return v
    
    class Config:
        populate_by_name = True  # Allow both snake_case and camelCase


class TransferResponse(BaseModel):
    """Response for transfer operation."""
    tx_hash: str = Field(..., alias="txHash")
    status: str
    explorer: str
    wallet_id: str
    to: str
    amount: float
    asset: str
    
    class Config:
        populate_by_name = True


class PolicyStatusResponse(BaseModel):
    """Response for policy status."""
    wallet_id: str
    enabled: bool
    per_tx_max: Optional[float]
    daily_cap: Optional[float]
    spent_today: float


class TransactionStatusResponse(BaseModel):
    """Response for transaction status."""
    hash: str
    status: str
    block_number: Optional[int] = None
    network: str


class ErrorResponse(BaseModel):
    """Error response."""
    error: str
    detail: Optional[str] = None



