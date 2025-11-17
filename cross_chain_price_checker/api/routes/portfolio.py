"""Portfolio management endpoints."""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...database import get_db, Portfolio, Trade
from ...price_checker import PriceChecker
from sqlalchemy import select, and_

router = APIRouter()


class PortfolioCreate(BaseModel):
    """Portfolio entry creation model."""
    user_id: str
    token_symbol: str
    amount: float
    avg_buy_price: float
    exchange_name: Optional[str] = None
    notes: Optional[str] = None


class PortfolioResponse(BaseModel):
    """Portfolio response model."""
    id: int
    user_id: str
    token_symbol: str
    amount: float
    avg_buy_price: float
    exchange_name: Optional[str] = None
    current_price: Optional[float] = None
    current_value: Optional[float] = None
    profit_loss: Optional[float] = None
    profit_loss_percent: Optional[float] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TradeCreate(BaseModel):
    """Trade creation model."""
    user_id: str
    token_symbol: str
    trade_type: str  # buy, sell
    amount: float
    price: float
    exchange_name: str
    fee: float = 0.0
    notes: Optional[str] = None


class TradeResponse(BaseModel):
    """Trade response model."""
    id: int
    user_id: str
    token_symbol: str
    trade_type: str
    amount: float
    price: float
    exchange_name: str
    fee: float
    total_value: float
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/", response_model=PortfolioResponse)
async def add_to_portfolio(portfolio: PortfolioCreate):
    """Add or update portfolio entry."""
    db = get_db()

    async for session in db.get_session():
        # Check if entry exists
        result = await session.execute(
            select(Portfolio).where(
                and_(
                    Portfolio.user_id == portfolio.user_id,
                    Portfolio.token_symbol == portfolio.token_symbol,
                    Portfolio.exchange_name == portfolio.exchange_name,
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing entry
            total_cost = (existing.amount * existing.avg_buy_price) + (portfolio.amount * portfolio.avg_buy_price)
            existing.amount += portfolio.amount
            existing.avg_buy_price = total_cost / existing.amount
            existing.updated_at = datetime.utcnow()
            await session.flush()
            await session.refresh(existing)
            return PortfolioResponse.model_validate(existing)
        else:
            # Create new entry
            new_portfolio = Portfolio(**portfolio.model_dump())
            session.add(new_portfolio)
            await session.flush()
            await session.refresh(new_portfolio)
            return PortfolioResponse.model_validate(new_portfolio)


@router.get("/user/{user_id}", response_model=List[PortfolioResponse])
async def get_user_portfolio(user_id: str):
    """Get user's portfolio with current prices."""
    db = get_db()
    checker = PriceChecker()

    try:
        async for session in db.get_session():
            result = await session.execute(
                select(Portfolio).where(Portfolio.user_id == user_id)
            )
            portfolio_items = result.scalars().all()

            # Get current prices for all tokens
            tokens = list(set(item.token_symbol for item in portfolio_items))
            current_prices = {}

            for token in tokens:
                analysis = await checker.check_token_price(token)
                if analysis.get('valid_count', 0) > 0:
                    current_prices[token] = analysis['avg_price']

            # Build response with current values
            response = []
            for item in portfolio_items:
                item_dict = {
                    "id": item.id,
                    "user_id": item.user_id,
                    "token_symbol": item.token_symbol,
                    "amount": item.amount,
                    "avg_buy_price": item.avg_buy_price,
                    "exchange_name": item.exchange_name,
                    "notes": item.notes,
                    "created_at": item.created_at,
                    "updated_at": item.updated_at,
                }

                current_price = current_prices.get(item.token_symbol)
                if current_price:
                    item_dict["current_price"] = current_price
                    item_dict["current_value"] = item.amount * current_price
                    cost_basis = item.amount * item.avg_buy_price
                    item_dict["profit_loss"] = item_dict["current_value"] - cost_basis
                    item_dict["profit_loss_percent"] = (item_dict["profit_loss"] / cost_basis) * 100

                response.append(PortfolioResponse(**item_dict))

            return response

    finally:
        await checker.close()


@router.post("/trades", response_model=TradeResponse)
async def record_trade(trade: TradeCreate):
    """Record a new trade."""
    db = get_db()

    async for session in db.get_session():
        total_value = trade.amount * trade.price + trade.fee

        new_trade = Trade(
            user_id=trade.user_id,
            token_symbol=trade.token_symbol,
            trade_type=trade.trade_type,
            amount=trade.amount,
            price=trade.price,
            exchange_name=trade.exchange_name,
            fee=trade.fee,
            total_value=total_value,
            status="executed",
            executed_at=datetime.utcnow(),
            notes=trade.notes,
        )

        session.add(new_trade)
        await session.flush()
        await session.refresh(new_trade)
        return TradeResponse.model_validate(new_trade)


@router.get("/trades/{user_id}", response_model=List[TradeResponse])
async def get_user_trades(user_id: str, limit: int = 50):
    """Get user's trade history."""
    db = get_db()

    async for session in db.get_session():
        result = await session.execute(
            select(Trade)
            .where(Trade.user_id == user_id)
            .order_by(Trade.created_at.desc())
            .limit(limit)
        )
        trades = result.scalars().all()
        return [TradeResponse.model_validate(t) for t in trades]
