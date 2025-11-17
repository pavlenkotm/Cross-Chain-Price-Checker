"""Exchange status and health endpoints."""

from typing import List
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel

from ...database import get_db, ExchangeStatus
from sqlalchemy import select

router = APIRouter()


class ExchangeStatusResponse(BaseModel):
    """Exchange status response model."""
    exchange_name: str
    exchange_type: str
    is_available: bool
    last_check: datetime
    response_time_ms: float | None = None
    error_count: int
    last_error: str | None = None

    class Config:
        from_attributes = True


@router.get("/", response_model=List[ExchangeStatusResponse])
async def get_all_exchanges():
    """Get status of all exchanges."""
    db = get_db()

    async for session in db.get_session():
        result = await session.execute(select(ExchangeStatus))
        exchanges = result.scalars().all()
        return [ExchangeStatusResponse.model_validate(e) for e in exchanges]


@router.get("/{exchange_name}", response_model=ExchangeStatusResponse)
async def get_exchange_status(exchange_name: str):
    """Get status of a specific exchange."""
    db = get_db()

    async for session in db.get_session():
        result = await session.execute(
            select(ExchangeStatus).where(ExchangeStatus.exchange_name == exchange_name)
        )
        exchange = result.scalar_one_or_none()

        if not exchange:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Exchange not found")

        return ExchangeStatusResponse.model_validate(exchange)


@router.get("/available/count")
async def get_available_count():
    """Get count of available exchanges."""
    db = get_db()

    async for session in db.get_session():
        result = await session.execute(
            select(ExchangeStatus).where(ExchangeStatus.is_available == True)
        )
        available = result.scalars().all()

        total_result = await session.execute(select(ExchangeStatus))
        total = len(total_result.scalars().all())

        return {
            "available": len(available),
            "total": total,
            "percentage": (len(available) / total * 100) if total > 0 else 0,
        }
