from datetime import datetime
from typing import Any, Dict, List

import aiohttp
import feedparser
from aiosqlite import Connection
from loguru import logger


async def fetch_and_store_feed(db: Connection, feed_id: int, feed_url: str) -> List[Dict[str, Any]]:
    """Fetch a single RSS/Atom feed and store new articles. Returns list of new articles."""
    new_articles = []
    try:
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(feed_url, headers={"User-Agent": "RSS-Aggregator/1.0"}) as resp:
                if resp.status != 200:
                    logger.warning("Feed {} returned status {}", feed_url, resp.status)
                    return []
                text = await resp.text()
                parsed = feedparser.parse(text)
                if parsed.bozo:
                    logger.warning("Feed {} parsing error: {}", feed_url, parsed.bozo_exception)
    except Exception as e:
        logger.error("Failed to fetch {}: {}", feed_url, e)
        return []

    for entry in parsed.entries:
        guid = entry.get("id") or entry.get("link")
        if not guid:
            continue
        # Check if article already exists
        cursor = await db.execute(
            "SELECT id FROM articles WHERE feed_id = ? AND guid = ?",
            (feed_id, guid[:255])
        )
        exists = await cursor.fetchone()
        if exists:
            continue

        # Sanitise: feedparser already converts HTML to plain text in 'summary'
        title = entry.get("title", "No title")[:500]
        summary = entry.get("summary", "")[:2000]
        link = entry.get("link", feed_url)
        published = None
        if entry.get("published_parsed"):
            published = datetime(*entry.published_parsed[:6])
        # Store raw content if needed (optional, safe because frontend will sanitise)
        content = entry.get("content", [{}])[0].get("value", "")[:10000]

        await db.execute(
            """INSERT INTO articles (feed_id, guid, title, link, summary, published_at, content)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (feed_id, guid[:255], title, link, summary, published, content)
        )
        new_articles.append({
            "title": title,
            "link": link,
            "summary": summary,
            "feed_id": feed_id
        })

    await db.execute("UPDATE feeds SET last_fetch_at = CURRENT_TIMESTAMP WHERE id = ?", (feed_id,))
    await db.commit()
    logger.info("Feed {} fetched, {} new articles", feed_url, len(new_articles))
    return new_articles
