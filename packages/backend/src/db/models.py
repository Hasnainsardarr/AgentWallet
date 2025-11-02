"""SQLAlchemy database models."""
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import (
    Column, String, DateTime, Boolean, Numeric, 
    Date, ForeignKey, Enum, JSON, create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import enum


Base = declarative_base()


class User(Base):
    """User model (optional for demo)."""
    __tablename__ = "users"
    
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    wallets = relationship("Wallet", back_populates="user")


class Wallet(Base):
    """Wallet model."""
    __tablename__ = "wallets"
    
    id = Column(String, primary_key=True)  # wallet_id from CDP
    user_id = Column(String, ForeignKey("users.id"), nullable=True)
    address = Column(String, unique=True, nullable=False)
    network = Column(String, nullable=False)  # e.g., base-sepolia
    created_at = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="wallets")
    policy = relationship("Policy", back_populates="wallet", uselist=False)
    spend_buckets = relationship("SpendBucket", back_populates="wallet")
    ledger_entries = relationship("LedgerEntry", back_populates="wallet")


class Policy(Base):
    """Policy model for spend limits."""
    __tablename__ = "policies"
    
    wallet_id = Column(String, ForeignKey("wallets.id"), primary_key=True)
    enabled = Column(Boolean, default=False, nullable=False)
    per_tx_max = Column(Numeric(precision=18, scale=6), nullable=True)
    daily_cap = Column(Numeric(precision=18, scale=6), nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    wallet = relationship("Wallet", back_populates="policy")


class SpendBucket(Base):
    """Daily spend tracking."""
    __tablename__ = "spend_buckets"
    
    wallet_id = Column(String, ForeignKey("wallets.id"), primary_key=True)
    date = Column(Date, primary_key=True)
    sum = Column(Numeric(precision=18, scale=6), default=Decimal("0"), nullable=False)
    
    wallet = relationship("Wallet", back_populates="spend_buckets")


class DirectionEnum(enum.Enum):
    """Transaction direction."""
    outbound = "outbound"
    inbound = "inbound"
    faucet = "faucet"


class LedgerEntry(Base):
    """Immutable transaction ledger."""
    __tablename__ = "ledger"
    
    id = Column(String, primary_key=True)
    wallet_id = Column(String, ForeignKey("wallets.id"), nullable=False)
    direction = Column(Enum(DirectionEnum), nullable=False)
    to_address = Column(String, nullable=True)
    amount = Column(Numeric(precision=18, scale=6), nullable=False)
    asset = Column(String, nullable=False)  # e.g., USDC
    network = Column(String, nullable=False)
    tx_hash = Column(String, nullable=True)
    request_meta = Column(JSON, nullable=True)  # idempotencyKey, ip, etc.
    ts = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    wallet = relationship("Wallet", back_populates="ledger_entries")


class IdempotencyKey(Base):
    """Idempotency key storage."""
    __tablename__ = "idempotency_keys"
    
    key = Column(String, primary_key=True)
    result_data = Column(JSON, nullable=False)  # Full response to replay
    created_at = Column(DateTime, default=datetime.utcnow)


# Database initialization
def init_db(database_url: str):
    """Initialize database and create tables."""
    engine = create_engine(database_url, echo=False)
    Base.metadata.create_all(engine)
    return engine


def get_session_maker(engine):
    """Get session maker."""
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)



