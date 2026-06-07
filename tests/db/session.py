import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.api.deps import get_db
from app.core.config import settings
from app.db.base import Base
from app.main import app
import app.models  # noqa: F401


@pytest.fixture
def test_database_url():
    explicit_url = os.getenv("TEST_DATABASE_URL")

    if explicit_url:
        return explicit_url

    if os.getenv("USE_SETTINGS_TEST_DATABASE") == "1":
        return (
            f"postgresql+asyncpg://{settings.postgres_user}:"
            f"{settings.postgres_password}@{settings.postgres_host}:"
            f"{settings.postgres_port}/{settings.postgres_db}_test"
        )

    pytest.skip("Set TEST_DATABASE_URL or USE_SETTINGS_TEST_DATABASE=1 to run real database tests")


@pytest.fixture
async def test_engine(test_database_url):
    engine = create_async_engine(test_database_url, echo=False, poolclass=NullPool)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def Session(test_engine):
    TestingSessionLocal = async_sessionmaker(
        bind=test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with TestingSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def db_session(Session):
    yield Session


@pytest.fixture
async def client(Session):
    async def override_get_db():
        yield Session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
