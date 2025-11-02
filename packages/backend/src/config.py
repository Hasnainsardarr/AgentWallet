"""Configuration management using pydantic-settings."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""
    
    # Server
    port: int = 8000
    node_env: str = "development"
    
    # Coinbase CDP
    cdp_api_key_id: str = "c363f207-2edd-4d24-9da2-a430e055ad77"
    cdp_api_base: str = "https://api.cdp.coinbase.com"
    cdp_api_key_secret: str = "60Bf3WxtOcfakVU2+z1Zbi3Wq6Evki40Kf9/06UZZCLmw/4qPntU+FK5lVI5sFeHmnmnotONkUwZYyCUoc8FCA=="   # PEM private key string for that API key
    cdp_wallet_secret: str = "MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQg0v0+wUcFQq1XqV1ibECNmC+AbejJ1VtbIbADux1wwhOhRANCAASwObmAtaf/z51+bwr4WCoj8zLsJ6h4VFfYiISYHrsA28R9u6acJbIB+6hrRRHx9N6RlA1Bb/bZUtpZeur0+Re4"
    network: str = "base-sepolia"
    
    # Database
    database_url: str = "sqlite:///./wallet_demo.db"
    
    # Explorer
    basescan_testnet: str = "https://sepolia.basescan.org"
    basescan_mainnet: str = "https://basescan.org"
    
    # JWT (optional)
    jwt_secret: str = "dev-secret-change-in-production"

    google_api_key: str | None = None
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()



