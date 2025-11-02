"""Authorization/policy routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal

from ..models.schemas import (
    GrantAuthorityRequest, RevokeAuthorityRequest,
    AuthorityResponse, PolicyStatusResponse
)
from ..db.models import Wallet
from ..services.policy import PolicyService
from ..utils.logging import get_logger, log_action, log_error
from ..dependencies import get_db

router = APIRouter(prefix="/auth", tags=["authorization"])
logger = get_logger(__name__)


@router.post("/grant", response_model=AuthorityResponse)
async def grant_authority(
    request: GrantAuthorityRequest,
    db: Session = Depends(get_db)
):
    """
    Grant spending authority with limits.
    
    Args:
        request: Grant authority request
        db: Database session
        
    Returns:
        Success response
    """
    try:
        # Check wallet exists
        wallet = db.query(Wallet).filter(Wallet.id == request.wallet_id).first()
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")
        
        # Grant authority
        policy_service = PolicyService(db)
        policy = policy_service.grant_authority(
            wallet_id=request.wallet_id,
            per_tx_max=Decimal(str(request.per_tx_max)),
            daily_cap=Decimal(str(request.daily_cap))
        )
        
        log_action(
            logger, "grant_authority",
            wallet_id=request.wallet_id,
            per_tx_max=request.per_tx_max,
            daily_cap=request.daily_cap
        )
        
        return AuthorityResponse(
            ok=True,
            wallet_id=request.wallet_id,
            message=f"Authority granted: {request.per_tx_max} per tx, {request.daily_cap} daily"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(logger, "grant_authority", e, wallet_id=request.wallet_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/revoke", response_model=AuthorityResponse)
async def revoke_authority(
    request: RevokeAuthorityRequest,
    db: Session = Depends(get_db)
):
    """
    Revoke spending authority.
    
    Args:
        request: Revoke authority request
        db: Database session
        
    Returns:
        Success response
    """
    try:
        # Check wallet exists
        wallet = db.query(Wallet).filter(Wallet.id == request.wallet_id).first()
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")
        
        # Revoke authority
        policy_service = PolicyService(db)
        policy = policy_service.revoke_authority(request.wallet_id)
        
        log_action(logger, "revoke_authority", wallet_id=request.wallet_id)
        
        return AuthorityResponse(
            ok=True,
            wallet_id=request.wallet_id,
            message="Authority revoked"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(logger, "revoke_authority", e, wallet_id=request.wallet_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/policy", response_model=PolicyStatusResponse)
async def get_policy(
    wallet_id: str,
    db: Session = Depends(get_db)
):
    """
    Get policy status for a wallet.
    
    Args:
        wallet_id: Wallet ID
        db: Database session
        
    Returns:
        Policy status
    """
    try:
        # Check wallet exists
        wallet = db.query(Wallet).filter(Wallet.id == wallet_id).first()
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")
        
        # Get policy status
        policy_service = PolicyService(db)
        status = policy_service.get_policy_status(wallet_id)
        
        return PolicyStatusResponse(
            wallet_id=wallet_id,
            **status
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log_error(logger, "get_policy", e, wallet_id=wallet_id)
        raise HTTPException(status_code=500, detail=str(e))



