"""Database service layer."""
import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Session as SessionModel, Wallet, Policy, SpendBucket, Transaction

logger = logging.getLogger(__name__)


class DatabaseService:
    def _norm_wallet_id(self, wallet_id: str) -> str:
        try:
            return (wallet_id or "").strip().lower()
        except Exception:
            return wallet_id

    """Service for database operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_or_create_session(self, session_id: str) -> SessionModel:
        """Get or create session."""
        result = await self.db.execute(
            select(SessionModel).where(SessionModel.session_id == session_id)
        )
        session = result.scalar_one_or_none()
        
        if not session:
            session = SessionModel(session_id=session_id)
            self.db.add(session)
            await self.db.commit()
            await self.db.refresh(session)
        
        return session
    
    async def get_wallet_for_session(self, session_id: str) -> Optional[Wallet]:
        """Get active wallet for session."""
        session = await self.get_or_create_session(session_id)
        
        if not session.wallet_id:
            return None
        
        result = await self.db.execute(
            select(Wallet).where(Wallet.wallet_id == session.wallet_id)
        )
        return result.scalar_one_or_none()
    
    async def create_or_update_wallet(
        self,
        session_id: str,
        wallet_id: str,
        address: str,
        network: str
    ) -> Wallet:
        """Create or update wallet for session."""
        try:
            result = await self.db.execute(
                select(Wallet).where(Wallet.wallet_id == wallet_id)
            )
            wallet = result.scalar_one_or_none()
            
            if wallet:
                logger.info(f"Wallet {wallet_id} already exists, updating session")
            else:
                wallet = Wallet(
                    wallet_id=wallet_id,
                    address=address,
                    network=network,
                    session_id=session_id
                )
                self.db.add(wallet)
                logger.info(f"Creating new wallet {wallet_id} for session {session_id}")
            
            await self.db.execute(
                update(SessionModel)
                .where(SessionModel.session_id == session_id)
                .values(wallet_id=wallet_id, updated_at=datetime.utcnow())
            )
            
            await self.db.commit()
            await self.db.refresh(wallet)
            
            logger.info(f"✅ Wallet {wallet_id} saved successfully for session {session_id}")
            
            return wallet
        except Exception as e:
            logger.error(f"Error saving wallet: {e}", exc_info=True)
            await self.db.rollback()
            raise

    async def set_wallet_for_session(self, session_id: str, address: str, network: Optional[str] = None) -> Wallet:
        """Convenience helper to persist a wallet for a session.
        Creates a new Wallet row if needed and updates the session's active wallet.
        The wallet_id is the address by convention.
        """
        wallet_id = address
        return await self.create_or_update_wallet(
            session_id=session_id,
            wallet_id=wallet_id,
            address=address,
            network=network or self._infer_network_default(),
        )

    def _infer_network_default(self) -> str:
        """Infer a default network if not provided; fallback to base-sepolia."""
        try:
            from utils.config import settings
            return getattr(settings, "network", "base-sepolia")
        except Exception:
            return "base-sepolia"
    
    async def get_policy(self, wallet_id: str) -> Optional[Policy]:
        """Get policy for wallet."""
        wid = self._norm_wallet_id(wallet_id)
        result = await self.db.execute(
            select(Policy)
            .where(Policy.wallet_id == wid)
            .order_by(Policy.created_at.desc())
        )
        return result.scalar_one_or_none()
    
    async def create_or_update_policy(
        self,
        wallet_id: str,
        enabled: bool,
        per_tx_max: float,
        daily_cap: float
    ) -> Policy:
        """Create or update policy."""
        wid = self._norm_wallet_id(wallet_id)
        policy = await self.get_policy(wid)
        
        if policy:
            policy.enabled = enabled
            policy.per_tx_max = Decimal(str(per_tx_max))
            policy.daily_cap = Decimal(str(daily_cap))
            policy.updated_at = datetime.utcnow()
        else:
            policy = Policy(
                wallet_id=wid,
                enabled=enabled,
                per_tx_max=Decimal(str(per_tx_max)),
                daily_cap=Decimal(str(daily_cap))
            )
            self.db.add(policy)
        
        await self.db.commit()
        await self.db.refresh(policy)
        
        return policy
    
    async def get_daily_spent(self, wallet_id: str) -> Decimal:
        """Get amount spent today."""
        today = date.today()
        wid = self._norm_wallet_id(wallet_id)
        result = await self.db.execute(
            select(SpendBucket)
            .where(SpendBucket.wallet_id == wid, SpendBucket.date == today)
        )
        bucket = result.scalar_one_or_none()
        
        return bucket.amount if bucket else Decimal("0")
    
    async def record_spend(self, wallet_id: str, amount: float):
        """Record a spend."""
        today = date.today()
        wid = self._norm_wallet_id(wallet_id)
        result = await self.db.execute(
            select(SpendBucket)
            .where(SpendBucket.wallet_id == wid, SpendBucket.date == today)
        )
        bucket = result.scalar_one_or_none()
        
        if bucket:
            bucket.amount += Decimal(str(amount))
        else:
            bucket = SpendBucket(
                wallet_id=wid,
                date=today,
                amount=Decimal(str(amount))
            )
            self.db.add(bucket)
        
        await self.db.commit()
    
    async def validate_transaction(self, wallet_id: str, amount: float) -> dict:
        """
        Validate if a transaction is allowed under current policy.
        
        Returns:
            dict with keys:
            - allowed (bool): Whether transaction is allowed
            - reason (str): Reason if not allowed
            - policy_info (dict): Current policy information
        """
        wid = self._norm_wallet_id(wallet_id)
        
        try:
            # Get current policy
            policy = await self.get_policy(wid)
            
            if not policy or not policy.enabled:
                return {
                    "allowed": False,
                    "reason": "No active spending policy found. Please grant spending authority first.",
                    "policy_info": {"enabled": False}
                }
            
            # Check per-transaction limit
            per_tx_max = float(policy.per_tx_max)
            if amount > per_tx_max:
                return {
                    "allowed": False,
                    "reason": f"Amount {amount} USDC exceeds per-transaction limit of {per_tx_max} USDC",
                    "policy_info": {
                        "enabled": True,
                        "per_tx_max": per_tx_max,
                        "daily_cap": float(policy.daily_cap),
                        "amount_requested": amount,
                        "excess_amount": amount - per_tx_max
                    }
                }
            
            # Check daily spending limit
            daily_cap = float(policy.daily_cap)
            daily_spent = float(await self.get_daily_spent(wid))
            remaining_daily = daily_cap - daily_spent
            
            if amount > remaining_daily:
                return {
                    "allowed": False,
                    "reason": f"Amount {amount} USDC exceeds remaining daily limit of {remaining_daily} USDC",
                    "policy_info": {
                        "enabled": True,
                        "per_tx_max": per_tx_max,
                        "daily_cap": daily_cap,
                        "daily_spent": daily_spent,
                        "remaining_daily": remaining_daily,
                        "amount_requested": amount,
                        "excess_amount": amount - remaining_daily
                    }
                }
            
            # Transaction is allowed
            return {
                "allowed": True,
                "reason": "Transaction within policy limits",
                "policy_info": {
                    "enabled": True,
                    "per_tx_max": per_tx_max,
                    "daily_cap": daily_cap,
                    "daily_spent": daily_spent,
                    "remaining_daily": remaining_daily,
                    "amount_requested": amount
                }
            }
            
        except Exception as e:
            return {
                "allowed": False,
                "reason": f"Policy validation failed: {str(e)}",
                "policy_info": {"enabled": False, "error": str(e)}
            }
    
    async def record_transaction(
        self,
        wallet_id: str,
        tx_hash: str,
        to_address: str,
        amount: float,
        asset: str = "USDC"
    ) -> Transaction:
        """Record a transaction."""
        wid = self._norm_wallet_id(wallet_id)
        tx = Transaction(
            wallet_id=wid,
            tx_hash=tx_hash,
            to_address=to_address,
            amount=Decimal(str(amount)),
            asset=asset,
            status="submitted"
        )
        self.db.add(tx)
        await self.db.commit()
        await self.db.refresh(tx)
        
        return tx

