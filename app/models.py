# SQL schema strings – used by database.py
# Kept here for maintainability
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
