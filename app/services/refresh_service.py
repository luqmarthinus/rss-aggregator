import asyncio

from loguru import logger

from app.database import get_db
from app.services.feed_fetcher import fetch_and_store_feed


async def refresh_all_feeds():
    """Refresh all feeds using its own database connection."""
    async for db in get_db():
        try:
            cursor = await db.execute("SELECT id, url, title FROM feeds")
            feeds = await cursor.fetchall()
            if not feeds:
                logger.info("No feeds to refresh")
                return

            semaphore = asyncio.Semaphore(5)

            async def refresh_one(feed):
                async with semaphore:
                    await fetch_and_store_feed(db, feed["id"], feed["url"])

            tasks = [refresh_one(feed) for feed in feeds]
            await asyncio.gather(*tasks, return_exceptions=True)
            logger.info("Refresh cycle completed")
        except Exception as e:
            logger.error(f"Refresh cycle failed: {e}")
        finally:
            break
