"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .routes import wallet, auth, transfer
from .config import get_settings
from .utils.logging import get_logger
from .dependencies import get_cdp_client

logger = get_logger(__name__)
settings = get_settings()
app = FastAPI(title="Coinbase CDP Wallet Demo", description="AI Agent + Coinbase Server Wallets (CDP) on Base Sepolia", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

app.include_router(wallet.router)
app.include_router(auth.router)
app.include_router(transfer.router)

@app.get("/")
async def root():
    return {"service": "CDP Wallet Demo", "status": "running", "network": settings.network, "docs": "/docs"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting CDP Wallet Demo on {settings.network}")
    logger.info(f"Database: {settings.database_url}")

@app.on_event("shutdown")
async def shutdown_event():
    # Close SDK HTTP session cleanly
    cdp = get_cdp_client()
    try:
        await cdp.aclose()
    except Exception as e:
        logger.warning(f"Error closing CDP SDK client: {e}")
    logger.info("Shutting down CDP Wallet Demo")
