"""Price alerts management endpoints."""

from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...database import get_db, Alert
from sqlalchemy import select, and_

router = APIRouter()


class AlertCreate(BaseModel):
    """Alert creation model."""
    user_id: str
    token_symbol: str
    alert_type: str  # price_above, price_below, arbitrage
    threshold: float
    exchange_name: Optional[str] = None
    notification_channel: str = "telegram"


class AlertResponse(BaseModel):
    """Alert response model."""
    id: int
    user_id: str
    token_symbol: str
    alert_type: str
    threshold: float
    exchange_name: Optional[str] = None
    is_active: bool
    notification_channel: str
    last_triggered: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/", response_model=AlertResponse)
async def create_alert(alert: AlertCreate):
    """Create a new price alert."""
    db = get_db()

    async for session in db.get_session():
        new_alert = Alert(**alert.model_dump())
        session.add(new_alert)
        await session.flush()
        await session.refresh(new_alert)
        return AlertResponse.model_validate(new_alert)


@router.get("/user/{user_id}", response_model=List[AlertResponse])
async def get_user_alerts(user_id: str, active_only: bool = True):
    """Get all alerts for a user."""
    db = get_db()

    async for session in db.get_session():
        query = select(Alert).where(Alert.user_id == user_id)

        if active_only:
            query = query.where(Alert.is_active == True)

        result = await session.execute(query)
        alerts = result.scalars().all()
        return [AlertResponse.model_validate(a) for a in alerts]


@router.delete("/{alert_id}")
async def delete_alert(alert_id: int):
    """Delete an alert."""
    db = get_db()

    async for session in db.get_session():
        result = await session.execute(
            select(Alert).where(Alert.id == alert_id)
        )
        alert = result.scalar_one_or_none()

        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        await session.delete(alert)
        return {"status": "deleted", "id": alert_id}


@router.patch("/{alert_id}/toggle")
async def toggle_alert(alert_id: int):
    """Toggle alert active status."""
    db = get_db()

    async for session in db.get_session():
        result = await session.execute(
            select(Alert).where(Alert.id == alert_id)
        )
        alert = result.scalar_one_or_none()

        if not alert:
            raise HTTPException(status_code=404, detail="Alert not found")

        alert.is_active = not alert.is_active
        await session.flush()
        return {"status": "toggled", "is_active": alert.is_active}
