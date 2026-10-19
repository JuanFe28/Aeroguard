"""Pruebas aisladas: SQLite temporal, sin PostgreSQL ni RabbitMQ."""

import os

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

# Se fija antes de importar la aplicación para no conectar a una BD de exposición.
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"

from app.main import app  # noqa: E402 - DATABASE_URL debe fijarse antes de importar.
from app.core import database  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def isolated_client(tmp_path_factory):
    db_path = tmp_path_factory.mktemp("aeroguard") / "test.db"
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path.as_posix()}")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(database, "engine", engine)
        patch.setattr(database, "AsyncSessionLocal", sessions)
        with TestClient(app) as client:
            yield client
            client.portal.call(engine.dispose)


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def async_client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        yield client
