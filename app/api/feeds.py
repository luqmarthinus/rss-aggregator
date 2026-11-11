import sqlite3

from aiosqlite import Connection
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from loguru import logger

from app.database import get_db
from app.dependencies import rate_limit, require_api_key
from app.schemas import FeedCreate, FeedOut
from app.services.refresh_service import refresh_feed
from app.utils.security import validate_feed_url

router = APIRouter(prefix="/feeds", tags=["Feeds"])


@router.get("", response_model=list[FeedOut])
async def list_feeds(db: Connection = Depends(get_db)):
    cursor = await db.execute(
        """
        SELECT f.id, f.url, f.title, f.added_at, f.last_fetch_at,
               COUNT(a.id) FILTER (WHERE a.is_read = 0) AS unread_count
        FROM feeds f
        LEFT JOIN articles a ON a.feed_id = f.id
        GROUP BY f.id
        ORDER BY COALESCE(f.title, f.url) COLLATE NOCASE
        """
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


@router.post("", status_code=201, dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def add_feed(feed: FeedCreate, background_tasks: BackgroundTasks, db: Connection = Depends(get_db)):
    url = validate_feed_url(str(feed.url))
    try:
        cursor = await db.execute("INSERT INTO feeds (url) VALUES (?)", (url,))
        await db.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Feed URL already exists")
    feed_id = cursor.lastrowid
    logger.info("Added feed id={} url={}", feed_id, url)
    # Fetch the new feed right away so it isn't empty until the next refresh cycle.
    background_tasks.add_task(refresh_feed, feed_id)
    return {"id": feed_id, "url": url}


@router.delete("/{feed_id}", dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def delete_feed(feed_id: int, db: Connection = Depends(get_db)):
    cursor = await db.execute("DELETE FROM feeds WHERE id = ?", (feed_id,))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Feed not found")
    await db.commit()
    logger.info("Deleted feed id={}", feed_id)
    return {"ok": True}
