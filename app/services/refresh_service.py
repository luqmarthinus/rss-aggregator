import asyncio

from loguru import logger

from app.database import get_db
from app.services.feed_fetcher import create_session, fetch_and_store_feed

MAX_CONCURRENT_FETCHES = 5

# Prevents the scheduled refresh and a manual refresh from running at the same time.
_refresh_lock = asyncio.Lock()


def is_refreshing() -> bool:
    return _refresh_lock.locked()


async def refresh_all_feeds() -> None:
    """Refresh all feeds using its own database connection."""
    if _refresh_lock.locked():
        logger.info("Refresh already in progress, skipping")
        return
    async with _refresh_lock:
        try:
            async for db in get_db():
                cursor = await db.execute("SELECT id, url FROM feeds")
                feeds = await cursor.fetchall()
                if not feeds:
                    logger.info("No feeds to refresh")
                    return

                semaphore = asyncio.Semaphore(MAX_CONCURRENT_FETCHES)
                async with create_session() as session:
                    async def refresh_one(feed):
                        async with semaphore:
                            await fetch_and_store_feed(db, feed["id"], feed["url"], session)

                    await asyncio.gather(*(refresh_one(f) for f in feeds), return_exceptions=True)
                logger.info("Refresh cycle completed ({} feeds)", len(feeds))
        except Exception as e:
            logger.exception("Refresh cycle failed: {}", e)


async def refresh_feed(feed_id: int) -> None:
    """Fetch a single feed immediately (used right after a feed is added)."""
    try:
        async for db in get_db():
            cursor = await db.execute("SELECT id, url FROM feeds WHERE id = ?", (feed_id,))
            feed = await cursor.fetchone()
            if feed:
                await fetch_and_store_feed(db, feed["id"], feed["url"])
    except Exception as e:
        logger.exception("Refresh of feed {} failed: {}", feed_id, e)
