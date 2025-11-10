"""Database setup and session management."""
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from utils.config import settings

# Disable verbose SQLite logging
logging.getLogger("aiosqlite").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

Base = declarative_base()

engine = create_async_engine(
    settings.database_url,
    echo=False,  # Disable SQL echo
    future=True
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def init_db():
    """Create all tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections."""
    await engine.dispose()


async def get_db():
    """Get database session dependency."""
    async with async_session_maker() as session:
        yield session

