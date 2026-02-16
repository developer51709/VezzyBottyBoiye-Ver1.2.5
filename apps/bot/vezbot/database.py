"""Database connection and session management."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from vezbot.config import settings
from vezbot.models.base import Base
from vezbot.utils.logging import get_logger, get_correlation_id, set_correlation_id

logger = get_logger(__name__)

# Create async engine
engine = create_async_engine(
    settings.database_url.replace("postgresql://", "postgresql+asyncpg://"),
    echo=False,
    future=True,
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def get_session():
    """Get async database session (generator for dependency injection)."""
    try:
        async with AsyncSessionLocal() as session:
            try:
                try:
                    yield session
                finally:
                    await session.close()
            except Exception as e:
                logger.error(f"Session error: {e}")
    except Exception as e:
        logger.error(f"Database session error: {e}")


async def init_db() -> None:
    """Initialize database (create tables)."""
    try:
        async with engine.begin() as conn:
            try:
                await conn.run_sync(Base.metadata.create_all)
            except Exception as e:
                logger.error(f"Error creating tables: {e}")
    except Exception as e:
        logger.error(f"Database connection error: {e}")


async def close_db() -> None:
    """Close database connections."""
    try:
        await engine.dispose()
    except Exception as e:
        logger.error(f"Error closing database: {e}")
