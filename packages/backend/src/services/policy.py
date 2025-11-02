"""Policy enforcement service."""
from datetime import date
from decimal import Decimal
from typing import Dict, Optional
from sqlalchemy.orm import Session
from ..db.models import Policy, SpendBucket, Wallet
from ..utils.logging import get_logger

logger = get_logger(__name__)


class PolicyViolationError(Exception):
    """Raised when a policy check fails."""
    pass


class PolicyService:
    """Service for managing and enforcing spend policies."""
    
    def __init__(self, db: Session):
        """
        Initialize policy service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def get_policy(self, wallet_id: str) -> Optional[Policy]:
        """
        Get policy for a wallet.
        
        Args:
            wallet_id: Wallet ID
            
        Returns:
            Policy object or None
        """
        return self.db.query(Policy).filter(Policy.wallet_id == wallet_id).first()
    
    def get_or_create_policy(self, wallet_id: str) -> Policy:
        """
        Get or create policy for a wallet.
        
        Args:
            wallet_id: Wallet ID
            
        Returns:
            Policy object
        """
        policy = self.get_policy(wallet_id)
        if not policy:
            policy = Policy(
                wallet_id=wallet_id,
                enabled=False,
                per_tx_max=None,
                daily_cap=None
            )
            self.db.add(policy)
            self.db.commit()
            self.db.refresh(policy)
        return policy
    
    def grant_authority(
        self,
        wallet_id: str,
        per_tx_max: Decimal,
        daily_cap: Decimal
    ) -> Policy:
        """
        Grant spending authority with limits.
        
        Args:
            wallet_id: Wallet ID
            per_tx_max: Maximum per transaction
            daily_cap: Maximum per day
            
        Returns:
            Updated policy
        """
        policy = self.get_or_create_policy(wallet_id)
        policy.enabled = True
        policy.per_tx_max = per_tx_max
        policy.daily_cap = daily_cap
        
        self.db.commit()
        self.db.refresh(policy)
        
        logger.info(f"Granted authority for wallet {wallet_id}: "
                   f"per_tx={per_tx_max}, daily={daily_cap}")
        
        return policy
    
    def revoke_authority(self, wallet_id: str) -> Policy:
        """
        Revoke spending authority.
        
        Args:
            wallet_id: Wallet ID
            
        Returns:
            Updated policy
        """
        policy = self.get_or_create_policy(wallet_id)
        policy.enabled = False
        
        self.db.commit()
        self.db.refresh(policy)
        
        logger.info(f"Revoked authority for wallet {wallet_id}")
        
        return policy
    
    def get_daily_spent(self, wallet_id: str, target_date: Optional[date] = None) -> Decimal:
        """
        Get amount spent today for a wallet.
        
        Args:
            wallet_id: Wallet ID
            target_date: Date to check (defaults to today)
            
        Returns:
            Amount spent
        """
        target_date = target_date or date.today()
        
        bucket = self.db.query(SpendBucket).filter(
            SpendBucket.wallet_id == wallet_id,
            SpendBucket.date == target_date
        ).first()
        
        return bucket.sum if bucket else Decimal("0")
    
    def enforce_policy(self, wallet_id: str, amount: Decimal) -> None:
        """
        Check if a transfer is allowed under current policy.
        
        Args:
            wallet_id: Wallet ID
            amount: Transfer amount
            
        Raises:
            PolicyViolationError: If policy check fails
        """
        policy = self.get_policy(wallet_id)
        
        if not policy or not policy.enabled:
            raise PolicyViolationError("Authority not granted - policy not enabled")
        
        # Check per-transaction limit
        if policy.per_tx_max and amount > policy.per_tx_max:
            raise PolicyViolationError(
                f"Per-transaction limit exceeded: {amount} > {policy.per_tx_max}"
            )
        
        # Check daily cap
        if policy.daily_cap:
            spent_today = self.get_daily_spent(wallet_id)
            if spent_today + amount > policy.daily_cap:
                raise PolicyViolationError(
                    f"Daily limit exceeded: {spent_today} + {amount} > {policy.daily_cap}"
                )
    
    def record_spend(self, wallet_id: str, amount: Decimal, target_date: Optional[date] = None) -> None:
        """
        Record a spend in the daily bucket.
        
        Args:
            wallet_id: Wallet ID
            amount: Amount spent
            target_date: Date of spend (defaults to today)
        """
        target_date = target_date or date.today()
        
        bucket = self.db.query(SpendBucket).filter(
            SpendBucket.wallet_id == wallet_id,
            SpendBucket.date == target_date
        ).first()
        
        if not bucket:
            bucket = SpendBucket(
                wallet_id=wallet_id,
                date=target_date,
                sum=Decimal("0")
            )
            self.db.add(bucket)
        
        bucket.sum += amount
        self.db.commit()
        
        logger.info(f"Recorded spend for wallet {wallet_id}: {amount} on {target_date}")
    
    def get_policy_status(self, wallet_id: str) -> Dict:
        """
        Get full policy status including current spend.
        
        Args:
            wallet_id: Wallet ID
            
        Returns:
            Dict with policy details
        """
        policy = self.get_policy(wallet_id)
        spent_today = self.get_daily_spent(wallet_id)
        
        if not policy:
            return {
                "enabled": False,
                "per_tx_max": None,
                "daily_cap": None,
                "spent_today": float(spent_today)
            }
        
        return {
            "enabled": policy.enabled,
            "per_tx_max": float(policy.per_tx_max) if policy.per_tx_max else None,
            "daily_cap": float(policy.daily_cap) if policy.daily_cap else None,
            "spent_today": float(spent_today)
        }



