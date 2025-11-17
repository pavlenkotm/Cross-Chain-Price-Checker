"""Analytics and statistics endpoints."""

from typing import List, Dict
from datetime import datetime, timedelta
from fastapi import APIRouter, Query
from pydantic import BaseModel

from ...database import get_db, PriceHistory, ArbitrageOpportunityLog
from sqlalchemy import select, func, and_

router = APIRouter()


class PriceStatistics(BaseModel):
    """Price statistics model."""
    token_symbol: str
    exchange_name: str
    period_hours: int
    avg_price: float
    min_price: float
    max_price: float
    price_change_percent: float
    data_points: int


class ArbitrageStats(BaseModel):
    """Arbitrage opportunity statistics."""
    token_symbol: str
    total_opportunities: int
    avg_profit_percent: float
    max_profit_percent: float
    most_common_buy_exchange: str
    most_common_sell_exchange: str


@router.get("/price-stats/{token}")
async def get_price_statistics(
    token: str,
    hours: int = Query(24, ge=1, le=720),
) -> List[PriceStatistics]:
    """Get price statistics for a token across all exchanges."""
    db = get_db()
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)

    async for session in db.get_session():
        # Get statistics grouped by exchange
        query = (
            select(
                PriceHistory.exchange_name,
                func.avg(PriceHistory.price).label('avg_price'),
                func.min(PriceHistory.price).label('min_price'),
                func.max(PriceHistory.price).label('max_price'),
                func.count(PriceHistory.id).label('data_points'),
            )
            .where(
                and_(
                    PriceHistory.token_symbol == token.upper(),
                    PriceHistory.timestamp >= cutoff_time,
                )
            )
            .group_by(PriceHistory.exchange_name)
        )

        result = await session.execute(query)
        stats = result.all()

        response = []
        for stat in stats:
            # Calculate price change
            first_price_query = (
                select(PriceHistory.price)
                .where(
                    and_(
                        PriceHistory.token_symbol == token.upper(),
                        PriceHistory.exchange_name == stat.exchange_name,
                        PriceHistory.timestamp >= cutoff_time,
                    )
                )
                .order_by(PriceHistory.timestamp.asc())
                .limit(1)
            )
            first_result = await session.execute(first_price_query)
            first_price = first_result.scalar_one_or_none()

            last_price_query = (
                select(PriceHistory.price)
                .where(
                    and_(
                        PriceHistory.token_symbol == token.upper(),
                        PriceHistory.exchange_name == stat.exchange_name,
                    )
                )
                .order_by(PriceHistory.timestamp.desc())
                .limit(1)
            )
            last_result = await session.execute(last_price_query)
            last_price = last_result.scalar_one_or_none()

            price_change = 0.0
            if first_price and last_price and first_price > 0:
                price_change = ((last_price - first_price) / first_price) * 100

            response.append(
                PriceStatistics(
                    token_symbol=token.upper(),
                    exchange_name=stat.exchange_name,
                    period_hours=hours,
                    avg_price=float(stat.avg_price),
                    min_price=float(stat.min_price),
                    max_price=float(stat.max_price),
                    price_change_percent=price_change,
                    data_points=stat.data_points,
                )
            )

        return response


@router.get("/arbitrage-stats/{token}")
async def get_arbitrage_statistics(
    token: str,
    hours: int = Query(24, ge=1, le=720),
) -> ArbitrageStats:
    """Get arbitrage opportunity statistics for a token."""
    db = get_db()
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)

    async for session in db.get_session():
        # Get all arbitrage opportunities
        query = (
            select(ArbitrageOpportunityLog)
            .where(
                and_(
                    ArbitrageOpportunityLog.token_symbol == token.upper(),
                    ArbitrageOpportunityLog.detected_at >= cutoff_time,
                )
            )
        )

        result = await session.execute(query)
        opportunities = result.scalars().all()

        if not opportunities:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="No arbitrage data found")

        # Calculate statistics
        total = len(opportunities)
        avg_profit = sum(opp.profit_percent for opp in opportunities) / total
        max_profit = max(opp.profit_percent for opp in opportunities)

        # Most common exchanges
        buy_exchanges = [opp.buy_exchange for opp in opportunities]
        sell_exchanges = [opp.sell_exchange for opp in opportunities]

        from collections import Counter
        most_common_buy = Counter(buy_exchanges).most_common(1)[0][0]
        most_common_sell = Counter(sell_exchanges).most_common(1)[0][0]

        return ArbitrageStats(
            token_symbol=token.upper(),
            total_opportunities=total,
            avg_profit_percent=avg_profit,
            max_profit_percent=max_profit,
            most_common_buy_exchange=most_common_buy,
            most_common_sell_exchange=most_common_sell,
        )


@router.get("/trending")
async def get_trending_arbitrage(limit: int = Query(10, ge=1, le=50)):
    """Get tokens with most arbitrage opportunities."""
    db = get_db()
    cutoff_time = datetime.utcnow() - timedelta(hours=24)

    async for session in db.get_session():
        query = (
            select(
                ArbitrageOpportunityLog.token_symbol,
                func.count(ArbitrageOpportunityLog.id).label('opportunity_count'),
                func.avg(ArbitrageOpportunityLog.profit_percent).label('avg_profit'),
                func.max(ArbitrageOpportunityLog.profit_percent).label('max_profit'),
            )
            .where(ArbitrageOpportunityLog.detected_at >= cutoff_time)
            .group_by(ArbitrageOpportunityLog.token_symbol)
            .order_by(func.count(ArbitrageOpportunityLog.id).desc())
            .limit(limit)
        )

        result = await session.execute(query)
        trending = result.all()

        return [
            {
                "token": t.token_symbol,
                "opportunities_24h": t.opportunity_count,
                "avg_profit_percent": float(t.avg_profit),
                "max_profit_percent": float(t.max_profit),
            }
            for t in trending
        ]


@router.get("/volume/{token}")
async def get_price_volume(
    token: str,
    hours: int = Query(24, ge=1, le=720),
    interval_minutes: int = Query(60, ge=5, le=1440),
):
    """Get price volume data for charting."""
    db = get_db()
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)

    async for session in db.get_session():
        # This is a simplified version - in production you'd use time buckets
        query = (
            select(
                PriceHistory.timestamp,
                PriceHistory.exchange_name,
                PriceHistory.price,
                PriceHistory.volume_24h,
            )
            .where(
                and_(
                    PriceHistory.token_symbol == token.upper(),
                    PriceHistory.timestamp >= cutoff_time,
                )
            )
            .order_by(PriceHistory.timestamp.asc())
        )

        result = await session.execute(query)
        data = result.all()

        return [
            {
                "timestamp": row.timestamp.isoformat(),
                "exchange": row.exchange_name,
                "price": row.price,
                "volume_24h": row.volume_24h,
            }
            for row in data
        ]
