# SQL schema strings – single source of truth used by database.init_db
FEEDS_TABLE = """
CREATE TABLE IF NOT EXISTS feeds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    title TEXT,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_fetch_at TIMESTAMP
)
"""

ARTICLES_TABLE = """
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
"""

INDEXES = (
    "CREATE INDEX IF NOT EXISTS idx_articles_feed_id ON articles (feed_id)",
    "CREATE INDEX IF NOT EXISTS idx_articles_published ON articles (published_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_articles_read ON articles (is_read)",
)
