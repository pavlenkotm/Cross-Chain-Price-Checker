"""Database models for Cross-Chain Price Checker."""

from datetime import datetime
from typing import Optional
from sqlalchemy import String, Float, Integer, Boolean, DateTime, Text, ForeignKey, Index, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class PriceHistory(Base):
    """Historical price data."""

    __tablename__ = "price_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    token_symbol: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    exchange_name: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    exchange_type: Mapped[str] = mapped_column(String(10), nullable=False)  # DEX or CEX
    chain: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    pair: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    liquidity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volume_24h: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True, nullable=False)

    __table_args__ = (
        Index('idx_token_exchange_time', 'token_symbol', 'exchange_name', 'timestamp'),
    )

    def __repr__(self) -> str:
        return f"<PriceHistory(token={self.token_symbol}, exchange={self.exchange_name}, price={self.price})>"


class TokenInfo(Base):
    """Token metadata and information."""

    __tablename__ = "token_info"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    coingecko_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Contract addresses as JSON
    addresses: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Metadata
    decimals: Mapped[int] = mapped_column(Integer, default=18, nullable=False)
    total_supply: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    market_cap: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<TokenInfo(symbol={self.symbol}, name={self.name})>"


class ExchangeStatus(Base):
    """Exchange status and health monitoring."""

    __tablename__ = "exchange_status"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    exchange_name: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    exchange_type: Mapped[str] = mapped_column(String(10), nullable=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_check: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    last_success: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    def __repr__(self) -> str:
        return f"<ExchangeStatus(exchange={self.exchange_name}, available={self.is_available})>"


class Alert(Base):
    """Price alerts configuration."""

    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    token_symbol: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    alert_type: Mapped[str] = mapped_column(String(20), nullable=False)  # price_above, price_below, arbitrage
    threshold: Mapped[float] = mapped_column(Float, nullable=False)
    exchange_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notification_channel: Mapped[str] = mapped_column(String(20), default="telegram", nullable=False)
    last_triggered: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self) -> str:
        return f"<Alert(user={self.user_id}, token={self.token_symbol}, type={self.alert_type})>"


class Portfolio(Base):
    """User portfolio tracking."""

    __tablename__ = "portfolios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    token_symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    avg_buy_price: Mapped[float] = mapped_column(Float, nullable=False)
    exchange_name: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationship to trades
    trades: Mapped[list["Trade"]] = relationship("Trade", back_populates="portfolio", cascade="all, delete-orphan")

    __table_args__ = (
        Index('idx_user_token', 'user_id', 'token_symbol'),
    )

    def __repr__(self) -> str:
        return f"<Portfolio(user={self.user_id}, token={self.token_symbol}, amount={self.amount})>"


class Trade(Base):
    """Trade execution history."""

    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    portfolio_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("portfolios.id"), nullable=True)
    user_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    token_symbol: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    trade_type: Mapped[str] = mapped_column(String(10), nullable=False)  # buy, sell
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)
    exchange_name: Mapped[str] = mapped_column(String(50), nullable=False)
    fee: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_value: Mapped[float] = mapped_column(Float, nullable=False)

    # For arbitrage trades
    is_arbitrage: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    related_trade_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("trades.id"), nullable=True)

    # Execution details
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False)  # pending, executed, failed
    tx_hash: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True, nullable=False)

    # Relationship
    portfolio: Mapped[Optional["Portfolio"]] = relationship("Portfolio", back_populates="trades")

    __table_args__ = (
        Index('idx_user_trade_time', 'user_id', 'created_at'),
    )

    def __repr__(self) -> str:
        return f"<Trade(user={self.user_id}, type={self.trade_type}, token={self.token_symbol}, amount={self.amount})>"


class ArbitrageOpportunityLog(Base):
    """Log of detected arbitrage opportunities."""

    __tablename__ = "arbitrage_opportunities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    token_symbol: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    buy_exchange: Mapped[str] = mapped_column(String(50), nullable=False)
    sell_exchange: Mapped[str] = mapped_column(String(50), nullable=False)
    buy_price: Mapped[float] = mapped_column(Float, nullable=False)
    sell_price: Mapped[float] = mapped_column(Float, nullable=False)
    profit_percent: Mapped[float] = mapped_column(Float, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True, nullable=False)

    # Track if opportunity was acted upon
    was_executed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    execution_trade_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("trades.id"), nullable=True)

    __table_args__ = (
        Index('idx_token_profit_time', 'token_symbol', 'profit_percent', 'detected_at'),
    )

    def __repr__(self) -> str:
        return f"<ArbitrageOpportunity(token={self.token_symbol}, profit={self.profit_percent}%)>"
