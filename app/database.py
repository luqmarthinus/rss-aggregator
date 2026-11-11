from pathlib import Path

import aiosqlite
from loguru import logger

from app.config import settings
from app.models import ARTICLES_TABLE, FEEDS_TABLE, INDEXES

DB_PATH = Path(settings.database_path)


async def _configure(db: aiosqlite.Connection) -> None:
    await db.execute("PRAGMA foreign_keys = ON")
    # Wait instead of failing immediately when the background refresh holds the write lock.
    await db.execute("PRAGMA busy_timeout = 5000")
    db.row_factory = aiosqlite.Row


async def get_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await _configure(db)
        yield db


async def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await _configure(db)
        await db.execute("PRAGMA journal_mode=WAL")
        await db.execute(FEEDS_TABLE)
        await db.execute(ARTICLES_TABLE)
        for statement in INDEXES:
            await db.execute(statement)
        await db.commit()
        logger.info("Database initialized at {}", DB_PATH)
