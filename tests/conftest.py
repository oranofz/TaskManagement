"""Test configuration and fixtures."""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.shared.database import Base
from app.config import settings

# Import all models to ensure they're registered with Base
from app.auth.domain.models import User, RefreshToken
from app.task.domain.models import Task, Comment, AuditLogEntry
from app.tenant.domain.models import Tenant, Department, Team, Project


DATABASE_URL = "postgresql+asyncpg://postgres:postgres@localhost:5432/task_management"


@pytest_asyncio.fixture(scope="function")
async def db_engine():
    """Create test database engine."""
    engine = create_async_engine(DATABASE_URL, echo=False)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Create test database session."""
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    async with async_session() as session:
        yield session


@pytest.fixture
def test_tenant_id():
    """Test tenant ID."""
    from uuid import UUID
    return UUID("00000000-0000-0000-0000-000000000001")


@pytest.fixture
def test_user_id():
    """Test user ID."""
    from uuid import UUID
    return UUID("00000000-0000-0000-0000-000000000002")

