from app.services.feed_fetcher import store_feed
from tests.conftest import run_db

RSS = b"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel>
  <title>Example Feed</title>
  <item><guid>1</guid><title>First</title><link>https://example.com/1</link>
        <pubDate>Tue, 10 Jun 2025 12:00:00 +0200</pubDate><description>Hello</description></item>
  <item><guid>2</guid><title>No date</title><link>https://example.com/2</link></item>
</channel></rss>"""


def _setup_and_store(raw):
    async def go(db):
        await db.execute("INSERT INTO feeds (id, url) VALUES (1, 'https://example.com/rss')")
        await db.commit()
        first = await store_feed(db, 1, "https://example.com/rss", raw)
        second = await store_feed(db, 1, "https://example.com/rss", raw)
        feed = await (await db.execute("SELECT title FROM feeds WHERE id = 1")).fetchone()
        rows = await (await db.execute("SELECT guid, published_at FROM articles ORDER BY guid")).fetchall()
        return first, second, feed["title"], [tuple(r) for r in rows]

    return run_db(go)


def test_store_feed_sets_title_dedupes_and_normalises_dates():
    first, second, title, rows = _setup_and_store(RSS)
    assert len(first) == 2
    assert second == []  # duplicates ignored on re-fetch
    assert title == "Example Feed"
    assert rows == [("1", "2025-06-10 10:00:00"), ("2", None)]  # converted to UTC
