"""Database models."""
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, DateTime, Boolean, Numeric, Date, JSON
from sqlalchemy.orm import Mapped, mapped_column
from db.database import Base


class Session(Base):
    """User session tracking."""
    __tablename__ = "sessions"
    
    session_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    wallet_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Wallet(Base):
    """Wallet information."""
    __tablename__ = "wallets"
    
    wallet_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    address: Mapped[str] = mapped_column(String, unique=True, index=True)
    network: Mapped[str] = mapped_column(String, default="base-sepolia")
    session_id: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Policy(Base):
    """Spending policies per wallet."""
    __tablename__ = "policies"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    wallet_id: Mapped[str] = mapped_column(String, index=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    per_tx_max: Mapped[Decimal | None] = mapped_column(Numeric(precision=20, scale=6), nullable=True)
    daily_cap: Mapped[Decimal | None] = mapped_column(Numeric(precision=20, scale=6), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SpendBucket(Base):
    """Daily spending tracking."""
    __tablename__ = "spend_buckets"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    wallet_id: Mapped[str] = mapped_column(String, index=True)
    date: Mapped[date] = mapped_column(Date, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=6), default=Decimal("0"))


class Transaction(Base):
    """Transaction history."""
    __tablename__ = "transactions"
    
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    wallet_id: Mapped[str] = mapped_column(String, index=True)
    tx_hash: Mapped[str] = mapped_column(String, unique=True)
    to_address: Mapped[str] = mapped_column(String)
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=20, scale=6))
    asset: Mapped[str] = mapped_column(String, default="USDC")
    status: Mapped[str] = mapped_column(String, default="submitted")
    tx_metadata: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

