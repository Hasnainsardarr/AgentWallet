"""Wallet-related routes (SDK-powered)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..models.schemas import (
    CreateWalletRequest, CreateWalletResponse,
    FundTestnetRequest, FundTestnetResponse,
    GetWalletResponse
)
from ..db.models import Wallet, User
from ..services.cdp_client import CdpSdk
from ..services.faucet import FaucetService
from ..utils.logging import get_logger, log_action, log_error
from ..dependencies import get_db, get_cdp_client, get_faucet_service

router = APIRouter(prefix="/wallet", tags=["wallet"])
logger = get_logger(__name__)

@router.post("/create", response_model=CreateWalletResponse)
async def create_wallet(
    request: CreateWalletRequest,
    db: Session = Depends(get_db),
    cdp: CdpSdk = Depends(get_cdp_client)
):
    try:
        result = await cdp.create_account()
        wallet_id = result["id"]
        address = result["address"]
        network = result["network"]

        if request.user_id:
            user = db.query(User).filter(User.id == request.user_id).first()
            if not user:
                user = User(id=request.user_id)
                db.add(user); db.commit()

        wallet = Wallet(id=wallet_id, user_id=request.user_id, address=address, network=network)
        db.add(wallet); db.commit()

        log_action(logger, "create_wallet", wallet_id=wallet_id, address=address, network=network)
        return CreateWalletResponse(wallet_id=wallet_id, address=address, network=network)
    except Exception as e:
        log_error(logger, "create_wallet", e)
        raise HTTPException(status_code=500, detail=str(e))

# routes/wallet.py
@router.post("/fund_testnet", response_model=FundTestnetResponse)
async def fund_testnet(
    request: FundTestnetRequest,
    db: Session = Depends(get_db),
    faucet: FaucetService = Depends(get_faucet_service),
    token: str = "usdc",   # <-- choose "eth" or "usdc"
    wait: bool = False,    # <-- wait for funds to arrive before returning
):
    """
    Request testnet funds from CDP faucet.
    
    Args:
        token: "eth" or "usdc" (default: usdc)
        wait: if True, waits up to 60s for funds to arrive (useful for automated tests)
    """
    try:
        wallet = db.query(Wallet).filter(Wallet.id == request.wallet_id).first()
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")

        result = await faucet.request_funds(
            wallet.address, 
            wallet.network, 
            token=token, 
            wait_for_confirmation=wait
        )

        txh = result["txHash"]
        log_action(logger, "fund_testnet", wallet_id=request.wallet_id, tx_hash=txh)

        return FundTestnetResponse(
            faucet_tx=txh,
            success=True,
            message=result.get("message")
        )

    except HTTPException:
        raise
    except Exception as e:
        log_error(logger, "fund_testnet", e, wallet_id=request.wallet_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/address", response_model=GetWalletResponse)
async def get_wallet(
    wallet_id: str,
    db: Session = Depends(get_db),
    cdp: CdpSdk = Depends(get_cdp_client)
):
    try:
        wallet = db.query(Wallet).filter(Wallet.id == wallet_id).first()
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")

        try:
            balance_info = await cdp.get_balance(address=wallet.address, network=wallet.network)
            assets = balance_info.get("assets", [])
        except Exception as e:
            logger.warning(f"Failed to get balance: {e}")
            assets = None

        return GetWalletResponse(wallet_id=wallet.id, address=wallet.address, network=wallet.network, assets=assets)
    except HTTPException:
        raise
    except Exception as e:
        log_error(logger, "get_wallet", e, wallet_id=wallet_id)
        raise HTTPException(status_code=500, detail=str(e))
