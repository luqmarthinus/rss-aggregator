import aiosqlite
from pathlib import Path
from loguru import logger
from app.config import settings

DB_PATH = Path(settings.database_path)

async def get_db():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        yield db

async def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL")
        # feeds table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS feeds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT UNIQUE NOT NULL,
                title TEXT,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_fetch_at TIMESTAMP
            )
        """)
        # articles table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                feed_id INTEGER NOT NULL,
                guid TEXT,
                title TEXT,
                link TEXT NOT NULL,
                summary TEXT,
                published_at TIMESTAMP,
                content TEXT,
                is_read BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (feed_id) REFERENCES feeds (id) ON DELETE CASCADE,
                UNIQUE(feed_id, guid)
            )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_articles_feed_id ON articles (feed_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_articles_published ON articles (published_at DESC)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_articles_read ON articles (is_read)")
        await db.commit()
        logger.info("Database initialized at {}", DB_PATH)
