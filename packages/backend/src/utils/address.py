"""EVM address validation utilities."""
import re
from web3 import Web3


def is_valid_eth_address(address: str) -> bool:
    """
    Check if a string is a valid Ethereum address.
    
    Args:
        address: Address string to validate
        
    Returns:
        True if valid EVM address format
    """
    if not address:
        return False
    
    # Check basic format (0x followed by 40 hex chars)
    if not re.match(r"^0x[a-fA-F0-9]{40}$", address):
        return False
    
    return True


def checksum_address(address: str) -> str:
    """
    Convert address to checksummed format.
    
    Args:
        address: Address to checksum
        
    Returns:
        Checksummed address
        
    Raises:
        ValueError: If address is invalid
    """
    if not is_valid_eth_address(address):
        raise ValueError(f"Invalid Ethereum address: {address}")
    
    return Web3.to_checksum_address(address)


def validate_and_checksum(address: str) -> str:
    """
    Validate and return checksummed address.
    
    Args:
        address: Address to validate
        
    Returns:
        Checksummed address
        
    Raises:
        ValueError: If address is invalid
    """
    if not is_valid_eth_address(address):
        raise ValueError(f"Invalid Ethereum address format: {address}")
    
    try:
        return checksum_address(address)
    except Exception as e:
        raise ValueError(f"Failed to checksum address: {str(e)}")



