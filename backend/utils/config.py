"""Application configuration."""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with all environment variables."""
    
    # Server
    port: int = 8000
    node_env: str = "development"
    
    # Database
    database_url: str = "sqlite+aiosqlite:///./wallet_agent.db"
    
    # Coinbase CDP
    cdp_api_key_id: str = ""
    cdp_api_base: str = "https://api.cdp.coinbase.com"
    cdp_api_key_secret: str = ""
    cdp_wallet_secret: str = ""
    network: str = "base-sepolia"
    usdc_contract_address: str = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
    # Optional RPC override and faucet endpoint
    rpc_url: str | None = None
    faucet_endpoint: str | None = None
    
    # Agent (Gemini)
    google_api_key: str = ""
    
    # Explorer URLs
    basescan_testnet: str = "https://sepolia.basescan.org"
    basescan_mainnet: str = "https://basescan.org"
    
    # Optional JWT
    jwt_secret: str = ""
    
    @field_validator("database_url", mode="before")
    @classmethod
    def convert_sqlite_url(cls, v: str) -> str:
        """Convert sqlite:// to sqlite+aiosqlite:// for async support."""
        if isinstance(v, str) and v.startswith("sqlite:///"):
            return v.replace("sqlite:///", "sqlite+aiosqlite:///")
        return v
    
    @property
    def environment(self) -> str:
        """Alias for node_env."""
        return self.node_env
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields in .env


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
