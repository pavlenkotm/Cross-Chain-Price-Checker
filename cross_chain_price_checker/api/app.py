"""FastAPI application factory."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from ..database import get_db
from .routes import prices, exchanges, alerts, portfolio, analytics, websocket


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting Cross-Chain Price Checker API...")
    db = get_db()
    await db.create_tables()
    logger.info("API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down API...")
    await db.close()
    logger.info("API shutdown complete")


def create_app() -> FastAPI:
    """
    Create and configure FastAPI application.

    Returns:
        FastAPI application instance
    """
    app = FastAPI(
        title="Cross-Chain Price Checker API",
        description="REST API for comparing cryptocurrency prices across DEXs and CEXs",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, specify exact origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(prices.router, prefix="/api/v1/prices", tags=["Prices"])
    app.include_router(exchanges.router, prefix="/api/v1/exchanges", tags=["Exchanges"])
    app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["Alerts"])
    app.include_router(portfolio.router, prefix="/api/v1/portfolio", tags=["Portfolio"])
    app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
    app.include_router(websocket.router, prefix="/api/v1/ws", tags=["WebSocket"])

    @app.get("/")
    async def root():
        """Root endpoint."""
        return {
            "name": "Cross-Chain Price Checker API",
            "version": "1.0.0",
            "docs": "/api/docs",
        }

    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "healthy"}

    @app.exception_handler(Exception)
    async def global_exception_handler(request, exc):
        """Global exception handler."""
        logger.error(f"Unhandled exception: {exc}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )

    return app
