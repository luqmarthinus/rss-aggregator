import calendar
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import aiohttp
import feedparser
from aiosqlite import Connection
from loguru import logger

from app.utils.security import PublicOnlyResolver, UnsafeURLError, check_feed_url

USER_AGENT = "RSS-Aggregator/1.1 (+https://github.com/luqmarthinus/rss-aggregator)"
MAX_FEED_BYTES = 5 * 1024 * 1024
MAX_REDIRECTS = 5
FETCH_TIMEOUT = aiohttp.ClientTimeout(total=20)


def create_session() -> aiohttp.ClientSession:
    """HTTP session whose DNS lookups refuse private/loopback addresses."""
    connector = aiohttp.TCPConnector(resolver=PublicOnlyResolver(), limit=10)
    return aiohttp.ClientSession(
        connector=connector,
        timeout=FETCH_TIMEOUT,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/rss+xml, application/atom+xml, application/xml;q=0.9, */*;q=0.8",
        },
    )


async def download_feed(session: aiohttp.ClientSession, feed_url: str) -> Optional[bytes]:
    """Download a feed, validating every redirect hop and capping the body size."""
    url = feed_url
    for _ in range(MAX_REDIRECTS + 1):
        check_feed_url(url)
        async with session.get(url, allow_redirects=False) as resp:
            if resp.status in (301, 302, 303, 307, 308) and "Location" in resp.headers:
                url = urljoin(url, resp.headers["Location"])
                continue
            if resp.status != 200:
                logger.warning("Feed {} returned status {}", feed_url, resp.status)
                return None
            body = await resp.content.read(MAX_FEED_BYTES + 1)
            if len(body) > MAX_FEED_BYTES:
                logger.warning("Feed {} exceeds {} bytes, skipping", feed_url, MAX_FEED_BYTES)
                return None
            return body
    logger.warning("Feed {} exceeded {} redirects", feed_url, MAX_REDIRECTS)
    return None


def _entry_timestamp(entry: Any) -> Optional[str]:
    """Return the entry's publish (or update) time as a naive UTC SQLite timestamp."""
    struct = entry.get("published_parsed") or entry.get("updated_parsed")
    if not struct:
        return None
    # feedparser normalises to UTC; timegm keeps it in UTC.
    dt = datetime.fromtimestamp(calendar.timegm(struct), tz=timezone.utc)
    return dt.strftime("%Y-%m-%d %H:%M:%S")


async def store_feed(db: Connection, feed_id: int, feed_url: str, raw: bytes) -> List[Dict[str, Any]]:
    """Parse raw feed bytes and insert unseen entries. Returns the new articles."""
    # Passing bytes lets feedparser honour the document's declared encoding.
    parsed = feedparser.parse(raw)
    if parsed.bozo and not parsed.entries:
        logger.warning("Feed {} parsing error: {}", feed_url, parsed.get("bozo_exception"))

    new_articles = []
    for entry in parsed.entries:
        guid = (entry.get("id") or entry.get("link") or "")[:255]
        if not guid:
            continue
        title = (entry.get("title") or "No title")[:500]
        summary = (entry.get("summary") or "")[:2000]
        link = entry.get("link") or feed_url
        contents = entry.get("content") or [{}]
        content = (contents[0].get("value") or "")[:10000]

        cursor = await db.execute(
            """INSERT OR IGNORE INTO articles (feed_id, guid, title, link, summary, published_at, content)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (feed_id, guid, title, link, summary, _entry_timestamp(entry), content),
        )
        if cursor.rowcount:
            new_articles.append({"title": title, "link": link, "summary": summary, "feed_id": feed_id})

    feed_title = (parsed.feed.get("title") or "").strip()[:300] or None
    await db.execute(
        "UPDATE feeds SET last_fetch_at = CURRENT_TIMESTAMP, title = COALESCE(?, title) WHERE id = ?",
        (feed_title, feed_id),
    )
    await db.commit()
    logger.info("Feed {} fetched, {} new articles", feed_url, len(new_articles))
    return new_articles


async def fetch_and_store_feed(
    db: Connection, feed_id: int, feed_url: str, session: Optional[aiohttp.ClientSession] = None
) -> List[Dict[str, Any]]:
    """Fetch a single RSS/Atom feed and store new articles. Returns list of new articles."""
    try:
        if session is None:
            async with create_session() as own_session:
                raw = await download_feed(own_session, feed_url)
        else:
            raw = await download_feed(session, feed_url)
    except UnsafeURLError as e:
        logger.warning("Refusing to fetch {}: {}", feed_url, e)
        return []
    except Exception as e:
        logger.error("Failed to fetch {}: {}", feed_url, e)
        return []
    if raw is None:
        return []
    return await store_feed(db, feed_id, feed_url, raw)
