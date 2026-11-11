import asyncio
import os
import tempfile

import pytest

# Configure settings before the app (and app.config) is imported.
_tmpdir = tempfile.mkdtemp()
os.environ["API_KEY"] = "test-key"
os.environ["DATABASE_PATH"] = os.path.join(_tmpdir, "test.db")
os.environ["RATE_LIMIT_PER_MINUTE"] = "1000"

from fastapi.testclient import TestClient  # noqa: E402

from app import database  # noqa: E402
from app.api import feeds as feeds_api, opml as opml_api  # noqa: E402
from app.main import app  # noqa: E402

AUTH = {"X-API-Key": "test-key"}


@pytest.fixture(autouse=True)
def fresh_db(monkeypatch):
    if database.DB_PATH.exists():
        database.DB_PATH.unlink()
    asyncio.run(database.init_db())

    # Never hit the network from API tests.
    async def noop(*args, **kwargs):
        return None

    monkeypatch.setattr(feeds_api, "refresh_feed", noop)
    monkeypatch.setattr(opml_api, "refresh_all_feeds", noop)
    yield


@pytest.fixture
def client():
    # Not used as a context manager, so the periodic refresh loop doesn't start.
    return TestClient(app)


def run_db(coro_fn):
    """Run ``coro_fn(db)`` against the test database."""
    async def runner():
        async for db in database.get_db():
            return await coro_fn(db)
    return asyncio.run(runner())
