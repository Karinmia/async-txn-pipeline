from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
import logging

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

settings = get_settings()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)


# Create a single engine instance
_engine: AsyncEngine | None = None


def get_engine(db_uri: str = settings.get_postgres_url()) -> AsyncEngine:
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            db_uri,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            echo=settings.db_echo,  # Set to True for SQL query logging
        )
    return _engine


@asynccontextmanager
async def make_session(
    engine: AsyncEngine | None = None,
) -> AsyncGenerator[AsyncSession, None]:
    """Create async session context manager."""

    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        yield session
