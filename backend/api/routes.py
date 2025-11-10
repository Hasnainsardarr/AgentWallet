"""API routes."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db.database import get_db
from schemas.requests import ChatRequest
from schemas.responses import ChatResponse, WalletInfo
from services.cdp_service import CDPService
from services.db_service import DatabaseService
from agent.core import WalletAgent

logger = logging.getLogger(__name__)

chat_router = APIRouter()

# Global CDP service (initialized once)
cdp_service = CDPService()


async def get_db_service(db: AsyncSession = Depends(get_db)) -> DatabaseService:
    """Get database service dependency."""
    return DatabaseService(db)


@chat_router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db_service: DatabaseService = Depends(get_db_service)
):
    """Process chat message with agent."""
    try:
        logger.info(f"Chat request from session: {request.session_id}")
        
        wallet = await db_service.get_wallet_for_session(request.session_id)
        wallet_address = wallet.address if wallet else None
        
        logger.info(f"Active wallet before agent: {wallet_address or 'None'}")
        
        agent = WalletAgent(cdp_service=cdp_service, db_service=db_service)
        
        response_text = await agent.process(
            message=request.message,
            session_id=request.session_id,
            wallet_address=wallet_address
        )
        
        logger.info(f"Agent response received: {response_text[:100]}...")
        
        updated_wallet = await db_service.get_wallet_for_session(request.session_id)
        
        logger.info(f"Active wallet after agent: {updated_wallet.address if updated_wallet else 'None'}")
        
        wallet_info = None
        if updated_wallet:
            # Fetch latest balances similar to previous implementation
            assets = []
            try:
                balance_info = await cdp_service.get_balance(updated_wallet.address, network=updated_wallet.network)
                assets = balance_info.get("assets", [])
            except Exception as e:
                logger.warning(f"Could not fetch balance for {updated_wallet.address}: {e}")
            wallet_info = WalletInfo(
                wallet_id=updated_wallet.wallet_id,
                address=updated_wallet.address,
                network=updated_wallet.network,
                assets=assets
            )
        
        return ChatResponse(
            response=response_text,
            wallet=wallet_info
        )
        
    except Exception as e:
        logger.error(f"Chat processing error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@chat_router.get("/wallet/{session_id}")
async def get_wallet(
    session_id: str,
    db_service: DatabaseService = Depends(get_db_service)
):
    """Get wallet for session."""
    try:
        wallet = await db_service.get_wallet_for_session(session_id)
        
        if not wallet:
            return {"wallet": None}
        
        assets = []
        try:
            balance_info = await cdp_service.get_balance(wallet.address, network=wallet.network)
            assets = balance_info.get("assets", [])
        except Exception as e:
            logger.warning(f"Could not fetch balance for {wallet.address}: {e}")
        
        return {
            "wallet": {
                "wallet_id": wallet.wallet_id,
                "address": wallet.address,
                "network": wallet.network,
                "assets": assets
            }
        }
        
    except Exception as e:
        logger.error(f"Get wallet error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

