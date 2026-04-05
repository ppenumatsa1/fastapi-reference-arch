import os
import tempfile

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db
from app.main import app


@pytest_asyncio.fixture()
async def async_session_factory() -> async_sessionmaker[AsyncSession]:
    fd, db_path = tempfile.mkstemp(prefix="user-test-", suffix=".db")
    os.close(fd)

    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        future=True,
        connect_args={"check_same_thread": False},
    )
    async_session_factory = async_sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    try:
        yield async_session_factory
    finally:
        await engine.dispose()
        if os.path.exists(db_path):
            os.remove(db_path)


@pytest_asyncio.fixture()
async def client(
    async_session_factory: async_sessionmaker[AsyncSession],
) -> AsyncClient:
    async def override_get_db():
        async with async_session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as test_client:
        yield test_client
    app.dependency_overrides.clear()
