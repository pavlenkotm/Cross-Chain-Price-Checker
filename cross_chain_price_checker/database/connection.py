"""Database connection management."""

import os
from typing import AsyncGenerator, Optional
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from loguru import logger

Base = declarative_base()


class Database:
    """Database connection manager."""

    def __init__(self, database_url: Optional[str] = None):
        """
        Initialize database connection.

        Args:
            database_url: Database URL. If None, uses DATABASE_URL env var or SQLite.
        """
        if database_url is None:
            database_url = os.getenv(
                "DATABASE_URL",
                "sqlite+aiosqlite:///./cross_chain_price_checker.db"
            )

        # Convert postgres:// to postgresql+asyncpg://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        self.engine = create_async_engine(
            database_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )

        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        logger.info(f"Database initialized: {database_url.split('@')[-1] if '@' in database_url else database_url}")

    async def create_tables(self):
        """Create all database tables."""
        from .models import Base
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created")

    async def drop_tables(self):
        """Drop all database tables."""
        from .models import Base
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.info("Database tables dropped")

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session."""
        async with self.async_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def close(self):
        """Close database connection."""
        await self.engine.dispose()
        logger.info("Database connection closed")


# Global database instance
_db_instance: Optional[Database] = None


def get_db(database_url: Optional[str] = None) -> Database:
    """
    Get or create global database instance.

    Args:
        database_url: Database URL

    Returns:
        Database instance
    """
    global _db_instance
    if _db_instance is None:
        _db_instance = Database(database_url)
    return _db_instance
