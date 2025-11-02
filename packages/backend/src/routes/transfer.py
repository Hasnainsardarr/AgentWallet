"""Transfer routes."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from decimal import Decimal
import uuid

from ..models.schemas import TransferRequest, TransferResponse, TransactionStatusResponse
from ..db.models import Wallet, LedgerEntry, DirectionEnum
from ..services.cdp_client import CdpSdk  # <-- SDK wrapper
from ..services.policy import PolicyService, PolicyViolationError
from ..services.idempotency import IdempotencyService
from ..config import get_settings
from ..utils.logging import get_logger, log_action, log_error
from ..utils.address import validate_and_checksum
from ..dependencies import get_db, get_cdp_client

router = APIRouter(tags=["transfer"])
logger = get_logger(__name__)


@router.post("/transfer", response_model=TransferResponse)
async def transfer(
    request: TransferRequest,
    db: Session = Depends(get_db),
    cdp: CdpSdk = Depends(get_cdp_client)  # <-- use SDK wrapper
):
    """
    Transfer USDC to an address using CDP SDK.
    """
    settings = get_settings()

    try:
        # Idempotency
        idempotency_service = IdempotencyService(db)
        cached_result = idempotency_service.check_key(request.idempotency_key)
        if cached_result:
            logger.info(f"Returning cached result for idempotency key: {request.idempotency_key}")
            return TransferResponse(**cached_result)

        # Wallet lookup
        wallet = db.query(Wallet).filter(Wallet.id == request.wallet_id).first()
        if not wallet:
            raise HTTPException(status_code=404, detail="Wallet not found")

        # Validate destination address
        try:
            to_address = validate_and_checksum(request.to)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Amount as Decimal
        amount = Decimal(str(request.amount))

        # Enforce policy
        policy_service = PolicyService(db)
        try:
            policy_service.enforce_policy(request.wallet_id, amount)
        except PolicyViolationError as e:
            log_action(
                logger, "transfer",
                wallet_id=request.wallet_id,
                status="policy_violation",
                error=str(e)
            )
            raise HTTPException(status_code=403, detail=str(e))

        # Execute transfer via CDP SDK
        try:
            result = await cdp.send_usdc(
                from_address=wallet.address,     # <-- use EOA address
                to_address=to_address,
                amount=str(amount),              # decimal-string, SDK converts to base units
                network=wallet.network
            )
            tx_hash = result["txHash"]
        except Exception as e:
            log_error(logger, "transfer_cdp", e, wallet_id=request.wallet_id)
            raise HTTPException(status_code=500, detail=f"Transfer failed: {str(e)}")

        # Record spend after successful submit
        policy_service.record_spend(request.wallet_id, amount)

        # Ledger entry
        ledger_entry = LedgerEntry(
            id=str(uuid.uuid4()),
            wallet_id=request.wallet_id,
            direction=DirectionEnum.outbound,
            to_address=to_address,
            amount=amount,
            asset=request.asset,
            network=wallet.network,
            tx_hash=tx_hash,
            request_meta={
                "idempotency_key": request.idempotency_key,
                "user_agent": None
            }
        )
        db.add(ledger_entry)
        db.commit()

        # Explorer URL
        if wallet.network == "base-sepolia":
            explorer_url = f"{settings.basescan_testnet}/tx/{tx_hash}"
        else:
            explorer_url = f"{settings.basescan_mainnet}/tx/{tx_hash}"

        # Response
        response_data = {
            "txHash": tx_hash,
            "status": result.get("status", "submitted"),
            "explorer": explorer_url,
            "wallet_id": request.wallet_id,
            "to": to_address,
            "amount": float(amount),
            "asset": request.asset
        }

        # Idempotency cache
        idempotency_service.store_result(request.idempotency_key, response_data)

        log_action(
            logger, "transfer",
            wallet_id=request.wallet_id,
            to=to_address,
            amount=float(amount),
            tx_hash=tx_hash
        )

        return TransferResponse(**response_data)

    except HTTPException:
        raise
    except Exception as e:
        log_error(logger, "transfer", e, wallet_id=request.wallet_id)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tx/{tx_hash}", response_model=TransactionStatusResponse)
async def get_transaction(
    tx_hash: str,
    db: Session = Depends(get_db)
):
    """
    Get transaction status.

    Note: This is a simplified version. In production, query chain/CDP for real status.
    """
    try:
        entry = db.query(LedgerEntry).filter(LedgerEntry.tx_hash == tx_hash).first()
        if not entry:
            raise HTTPException(status_code=404, detail="Transaction not found")

        return TransactionStatusResponse(
            hash=tx_hash,
            status="submitted",
            block_number=None,
            network=entry.network
        )

    except HTTPException:
        raise
    except Exception as e:
        log_error(logger, "get_transaction", e, tx_hash=tx_hash)
        raise HTTPException(status_code=500, detail=str(e))
