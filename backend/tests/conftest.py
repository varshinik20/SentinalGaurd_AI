"""
Test fixtures.

We test against an in-memory SQLite DB (aiosqlite) rather than Postgres —
fast, no external services required, matches our agreed workflow of
native/fast iteration during development, Docker/Postgres reserved for
integration testing. Postgres-only features (native UUID/ENUM types) are
handled fine by SQLAlchemy's cross-dialect columns used in the models.
"""
import asyncio
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import Role, User
from app.models import document  # noqa: F401  (registers documents table)
from app.core.security import hash_password
from app.core.config import settings

TEST_DATABASE_URL = "sqlite+aiosqlite://"

test_engine = create_async_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSessionLocal = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture(autouse=True)
async def _prepare_database():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _override_get_db():
    async with TestSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = _override_get_db


@pytest_asyncio.fixture
async def db_session():
    async with TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def seed_admin():
    """Creates a SUPER_ADMIN directly in the DB (bypassing the admin-only
    /register endpoint, mirroring what scripts/create_superadmin.py does)."""
    async with TestSessionLocal() as db:
        admin = User(
            id=uuid.uuid4(),
            email="admin@sentinelguard.ai",
            hashed_password=hash_password("AdminPass123!"),
            full_name="Root Admin",
            role=Role.SUPER_ADMIN,
            department="Platform",
        )
        db.add(admin)
        await db.commit()
    return {"email": "admin@sentinelguard.ai", "password": "AdminPass123!"}


@pytest.fixture(autouse=True)
def _tmp_upload_dir(tmp_path, monkeypatch):
    """Redirects file storage to a per-test temp directory instead of the
    container path (/app/data/uploads) baked into .env, since tests run
    natively on the host."""
    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir()
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(upload_dir))
    return upload_dir
