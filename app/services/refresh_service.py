import asyncio
from aiosqlite import Connection
from loguru import logger
from app.services.feed_fetcher import fetch_and_store_feed
from app.services.ntfy_notifier import send_ntfy_notification

async def refresh_all_feeds(db: Connection):
    cursor = await db.execute("SELECT id, url, title FROM feeds")
    feeds = await cursor.fetchall()
    if not feeds:
        logger.info("No feeds to refresh")
        return

    semaphore = asyncio.Semaphore(5)
    async def refresh_one(feed):
        async with semaphore:
            new_articles = await fetch_and_store_feed(db, feed["id"], feed["url"])
            # Send notifications for new articles
            for art in new_articles:
                await send_ntfy_notification(
                    title=art["title"],
                    message=art["summary"][:200],
                    link=art["link"]
                )
    tasks = [refresh_one(feed) for feed in feeds]
    await asyncio.gather(*tasks, return_exceptions=True)
    logger.info("Refresh cycle completed")
