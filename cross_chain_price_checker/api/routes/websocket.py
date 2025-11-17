"""WebSocket endpoints for real-time price streaming."""

import asyncio
import json
from typing import Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from loguru import logger

from ...price_checker import PriceChecker

router = APIRouter()


class ConnectionManager:
    """Manage WebSocket connections."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.token_subscriptions: dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket):
        """Accept and register new connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"Client connected. Total connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Remove connection."""
        self.active_connections.discard(websocket)

        # Remove from all token subscriptions
        for token in list(self.token_subscriptions.keys()):
            self.token_subscriptions[token].discard(websocket)
            if not self.token_subscriptions[token]:
                del self.token_subscriptions[token]

        logger.info(f"Client disconnected. Total connections: {len(self.active_connections)}")

    def subscribe_token(self, websocket: WebSocket, token: str):
        """Subscribe connection to token updates."""
        token = token.upper()
        if token not in self.token_subscriptions:
            self.token_subscriptions[token] = set()
        self.token_subscriptions[token].add(websocket)
        logger.info(f"Client subscribed to {token}")

    def unsubscribe_token(self, websocket: WebSocket, token: str):
        """Unsubscribe connection from token updates."""
        token = token.upper()
        if token in self.token_subscriptions:
            self.token_subscriptions[token].discard(websocket)
            if not self.token_subscriptions[token]:
                del self.token_subscriptions[token]
        logger.info(f"Client unsubscribed from {token}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send message to specific connection."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")

    async def broadcast_token_update(self, token: str, data: dict):
        """Broadcast price update to all subscribers of a token."""
        token = token.upper()
        if token not in self.token_subscriptions:
            return

        disconnected = set()
        for connection in self.token_subscriptions[token]:
            try:
                await connection.send_json({
                    "type": "price_update",
                    "token": token,
                    "data": data,
                })
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected.add(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)


manager = ConnectionManager()


@router.websocket("/prices")
async def websocket_prices(websocket: WebSocket):
    """
    WebSocket endpoint for real-time price updates.

    Protocol:
    - Client sends: {"action": "subscribe", "token": "SOL"}
    - Server sends: {"type": "price_update", "token": "SOL", "data": {...}}
    - Client sends: {"action": "unsubscribe", "token": "SOL"}
    """
    await manager.connect(websocket)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)

            action = message.get("action")
            token = message.get("token")

            if action == "subscribe" and token:
                manager.subscribe_token(websocket, token)
                await manager.send_personal_message(
                    {
                        "type": "subscribed",
                        "token": token.upper(),
                        "message": f"Subscribed to {token.upper()} price updates",
                    },
                    websocket,
                )

                # Send initial price data
                checker = PriceChecker()
                try:
                    analysis = await checker.check_token_price(token)
                    if 'error' not in analysis:
                        await manager.send_personal_message(
                            {
                                "type": "price_update",
                                "token": token.upper(),
                                "data": {
                                    "avg_price": analysis.get('avg_price', 0),
                                    "min_price": analysis.get('min_price', 0),
                                    "max_price": analysis.get('max_price', 0),
                                    "spread_percent": analysis.get('spread_percent', 0),
                                    "opportunities": len(analysis.get('opportunities', [])),
                                },
                            },
                            websocket,
                        )
                finally:
                    await checker.close()

            elif action == "unsubscribe" and token:
                manager.unsubscribe_token(websocket, token)
                await manager.send_personal_message(
                    {
                        "type": "unsubscribed",
                        "token": token.upper(),
                        "message": f"Unsubscribed from {token.upper()} price updates",
                    },
                    websocket,
                )

            elif action == "ping":
                await manager.send_personal_message({"type": "pong"}, websocket)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


async def price_update_worker():
    """
    Background worker to fetch and broadcast price updates.
    This should be run as a background task.
    """
    checker = PriceChecker()

    try:
        while True:
            # Get all subscribed tokens
            tokens = list(manager.token_subscriptions.keys())

            if tokens:
                logger.info(f"Fetching updates for {len(tokens)} tokens")

                for token in tokens:
                    try:
                        analysis = await checker.check_token_price(token)

                        if 'error' not in analysis:
                            await manager.broadcast_token_update(
                                token,
                                {
                                    "avg_price": analysis.get('avg_price', 0),
                                    "min_price": analysis.get('min_price', 0),
                                    "max_price": analysis.get('max_price', 0),
                                    "spread_percent": analysis.get('spread_percent', 0),
                                    "valid_count": analysis.get('valid_count', 0),
                                    "opportunities": len(analysis.get('opportunities', [])),
                                    "timestamp": asyncio.get_event_loop().time(),
                                },
                            )
                    except Exception as e:
                        logger.error(f"Error updating {token}: {e}")

            # Wait before next update (30 seconds)
            await asyncio.sleep(30)

    finally:
        await checker.close()
