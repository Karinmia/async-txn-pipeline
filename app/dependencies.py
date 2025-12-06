from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_engine, make_session


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for getting database session.

    Yields:
        AsyncSession: Database session
    """
    async with make_session(get_engine()) as session:
        try:
            yield session
            # await session.commit()
        except Exception:
            await session.rollback()
            raise
