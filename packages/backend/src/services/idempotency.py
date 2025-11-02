"""Idempotency service for safe retries."""
from typing import Dict, Optional
from sqlalchemy.orm import Session
from ..db.models import IdempotencyKey
from ..utils.logging import get_logger

logger = get_logger(__name__)


class IdempotencyService:
    """Service for handling idempotent operations."""
    
    def __init__(self, db: Session):
        """
        Initialize idempotency service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    def check_key(self, key: str) -> Optional[Dict]:
        """
        Check if an idempotency key has been used.
        
        Args:
            key: Idempotency key
            
        Returns:
            Previous result if key exists, None otherwise
        """
        entry = self.db.query(IdempotencyKey).filter(
            IdempotencyKey.key == key
        ).first()
        
        if entry:
            logger.info(f"Idempotency key {key} already exists - returning cached result")
            return entry.result_data
        
        return None
    
    def store_result(self, key: str, result: Dict) -> None:
        """
        Store the result for an idempotency key.
        
        Args:
            key: Idempotency key
            result: Result data to store
        """
        entry = IdempotencyKey(
            key=key,
            result_data=result
        )
        self.db.add(entry)
        self.db.commit()
        
        logger.info(f"Stored result for idempotency key {key}")
    
    def get_or_execute(self, key: str, execute_fn):
        """
        Execute a function only if the idempotency key hasn't been used.
        
        Args:
            key: Idempotency key
            execute_fn: Function to execute if key is new
            
        Returns:
            Either cached result or result of execute_fn
        """
        # Check if key exists
        cached = self.check_key(key)
        if cached:
            return cached
        
        # Execute function
        result = execute_fn()
        
        # Store result
        self.store_result(key, result)
        
        return result



