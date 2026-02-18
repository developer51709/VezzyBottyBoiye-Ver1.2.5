"""Database connection and session management."""

from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from vezbot.config import settings
from vezbot.models.base import Base
from vezbot.utils.logging import get_logger, get_correlation_id, set_correlation_id

logger = get_logger(__name__)


def _prepare_database_url(url: str) -> tuple[str, dict]:
    url = url.replace("postgresql://", "postgresql+asyncpg://")
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    connect_args = {}
    if "sslmode" in params:
        ssl_value = params.pop("sslmode")[0]
        if ssl_value == "disable":
            connect_args["ssl"] = False

    clean_query = urlencode({k: v[0] for k, v in params.items()})
    clean_url = urlunparse(parsed._replace(query=clean_query))
    return clean_url, connect_args


_db_url, _connect_args = _prepare_database_url(settings.database_url)

engine = create_async_engine(
    _db_url,
    echo=False,
    future=True,
    connect_args=_connect_args,
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
