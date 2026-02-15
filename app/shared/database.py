"""Database configuration and session management."""
from typing import AsyncGenerator
from datetime import datetime, UTC
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config import settings


Base = declarative_base()

engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
    pool_pre_ping=True,
    pool_size=20,
    max_overflow=10
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def get_utc_now() -> datetime:
    """
    Get current UTC datetime without timezone info (for database storage).

    Returns:
        Naive datetime in UTC
    """
    return datetime.now(UTC).replace(tzinfo=None)

