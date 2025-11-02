"""FastAPI dependency providers."""
from sqlalchemy.orm import Session
from .db.models import get_session_maker, init_db
from .services.cdp_client import CdpSdk
from .services.faucet import FaucetService
from .config import get_settings

settings = get_settings()
engine = init_db(settings.database_url)
SessionLocal = get_session_maker(engine)

# Single CdpSdk instance for the app; FastAPI startup will close it on shutdown.
_cdp = CdpSdk(settings)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_cdp_client():
    """Provide the CDP SDK wrapper."""
    return _cdp

def get_faucet_service():
    # IMPORTANT: pass the SDK into FaucetService
    return FaucetService(_cdp)