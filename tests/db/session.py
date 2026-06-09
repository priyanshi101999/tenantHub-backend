import os
from urllib.parse import urlparse

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

import app.models  # noqa: F401


load_dotenv()

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL") or (
    f"postgresql+asyncpg://{os.getenv('POSTGRES_USER')}:"
    f"{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST')}:"
    f"{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}_test"
)

database_name = urlparse(TEST_DATABASE_URL).path.lstrip("/")
if not database_name.endswith("_test"):
    raise RuntimeError("Tests require a database name ending with _test.")

os.environ["DATABASE_URL"] = TEST_DATABASE_URL

from app.api.deps import get_db
from app.db.base import Base
from app.main import app


@pytest.fixture
def test_database_url():
    return TEST_DATABASE_URL


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
