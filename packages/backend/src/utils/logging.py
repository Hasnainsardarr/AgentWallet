"""Structured logging utilities."""
import logging
import json
from datetime import datetime
from typing import Any, Dict, Optional


# Configure basic logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance."""
    return logging.getLogger(name)


def log_action(
    logger: logging.Logger,
    action: str,
    wallet_id: Optional[str] = None,
    status: str = "success",
    **kwargs: Any
) -> None:
    """
    Log a structured action event.
    
    Args:
        logger: Logger instance
        action: Action type (e.g., 'create_wallet', 'transfer')
        wallet_id: Optional wallet ID
        status: Status of the action
        **kwargs: Additional fields to log
    """
    log_data: Dict[str, Any] = {
        "timestamp": datetime.utcnow().isoformat(),
        "action": action,
        "status": status,
    }
    
    if wallet_id:
        log_data["wallet_id"] = wallet_id
    
    log_data.update(kwargs)
    
    logger.info(json.dumps(log_data))


def log_error(
    logger: logging.Logger,
    action: str,
    error: Exception,
    wallet_id: Optional[str] = None,
    **kwargs: Any
) -> None:
    """
    Log a structured error event.
    
    Args:
        logger: Logger instance
        action: Action type where error occurred
        error: Exception instance
        wallet_id: Optional wallet ID
        **kwargs: Additional fields to log
    """
    log_data: Dict[str, Any] = {
        "timestamp": datetime.utcnow().isoformat(),
        "action": action,
        "status": "error",
        "error_type": type(error).__name__,
        "error_message": str(error),
    }
    
    if wallet_id:
        log_data["wallet_id"] = wallet_id
    
    log_data.update(kwargs)
    
    logger.error(json.dumps(log_data))



