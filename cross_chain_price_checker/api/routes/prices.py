"""Price-related API endpoints."""

from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ...price_checker import PriceChecker
from ...database import get_db, PriceHistory
from sqlalchemy import select, and_

router = APIRouter()


class PriceResponse(BaseModel):
    """Price response model."""
    token_symbol: str
    exchange_name: str
    exchange_type: str
    chain: Optional[str] = None
    pair: Optional[str] = None
    price: float
    timestamp: datetime

    class Config:
        from_attributes = True


class PriceComparisonResponse(BaseModel):
    """Price comparison response."""
    token: str
    prices: List[dict]
    statistics: dict
    arbitrage_opportunities: List[dict]


@router.get("/current/{token}", response_model=PriceComparisonResponse)
async def get_current_prices(token: str):
    """
    Get current prices for a token across all exchanges.

    Args:
        token: Token symbol (e.g., 'SOL', 'BTC')

    Returns:
        Price comparison data
    """
    checker = PriceChecker()

    try:
        analysis = await checker.check_token_price(token)

        if 'error' in analysis:
            raise HTTPException(status_code=404, detail=analysis['error'])

        # Save to database
        db = get_db()
        async for session in db.get_session():
            for price_data in analysis['prices']:
                if price_data.is_valid:
                    price_record = PriceHistory(
                        token_symbol=price_data.token_symbol,
                        exchange_name=price_data.exchange_name,
                        exchange_type=price_data.exchange_type.value,
                        chain=price_data.chain,
                        pair=price_data.pair,
                        price=price_data.price,
                        liquidity=price_data.liquidity,
                    )
                    session.add(price_record)

        return {
            "token": token.upper(),
            "prices": [
                {
                    "exchange": p.exchange_name,
                    "type": p.exchange_type.value,
                    "chain": p.chain,
                    "pair": p.pair,
                    "price": p.price,
                    "valid": p.is_valid,
                    "error": p.error,
                }
                for p in analysis['prices']
            ],
            "statistics": {
                "count": analysis.get('count', 0),
                "valid_count": analysis.get('valid_count', 0),
                "avg_price": analysis.get('avg_price', 0),
                "min_price": analysis.get('min_price', 0),
                "max_price": analysis.get('max_price', 0),
                "spread_percent": analysis.get('spread_percent', 0),
            },
            "arbitrage_opportunities": [
                {
                    "buy_exchange": opp.buy_exchange,
                    "sell_exchange": opp.sell_exchange,
                    "buy_price": opp.buy_price,
                    "sell_price": opp.sell_price,
                    "profit_percent": opp.potential_profit_percent,
                }
                for opp in analysis.get('opportunities', [])
            ],
        }

    finally:
        await checker.close()


@router.get("/history/{token}", response_model=List[PriceResponse])
async def get_price_history(
    token: str,
    exchange: Optional[str] = Query(None, description="Filter by exchange name"),
    hours: int = Query(24, description="Number of hours to look back", ge=1, le=720),
    limit: int = Query(100, description="Maximum number of records", ge=1, le=1000),
):
    """
    Get historical prices for a token.

    Args:
        token: Token symbol
        exchange: Optional exchange filter
        hours: Number of hours to look back
        limit: Maximum records to return

    Returns:
        List of historical prices
    """
    db = get_db()
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)

    async for session in db.get_session():
        query = select(PriceHistory).where(
            and_(
                PriceHistory.token_symbol == token.upper(),
                PriceHistory.timestamp >= cutoff_time,
            )
        )

        if exchange:
            query = query.where(PriceHistory.exchange_name == exchange)

        query = query.order_by(PriceHistory.timestamp.desc()).limit(limit)

        result = await session.execute(query)
        prices = result.scalars().all()

        return [PriceResponse.model_validate(p) for p in prices]


@router.post("/compare")
async def compare_tokens(tokens: List[str]):
    """
    Compare prices for multiple tokens.

    Args:
        tokens: List of token symbols

    Returns:
        Comparison data for all tokens
    """
    checker = PriceChecker()

    try:
        results = await checker.check_multiple_tokens(tokens)

        return {
            token: {
                "statistics": {
                    "avg_price": analysis.get('avg_price', 0),
                    "spread_percent": analysis.get('spread_percent', 0),
                },
                "best_arbitrage": (
                    {
                        "profit_percent": analysis['opportunities'][0].potential_profit_percent,
                        "buy_exchange": analysis['opportunities'][0].buy_exchange,
                        "sell_exchange": analysis['opportunities'][0].sell_exchange,
                    }
                    if analysis.get('opportunities')
                    else None
                ),
            }
            for token, analysis in results.items()
            if 'error' not in analysis
        }

    finally:
        await checker.close()
