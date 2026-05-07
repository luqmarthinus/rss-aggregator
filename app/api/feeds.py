from fastapi import APIRouter, Depends, HTTPException
from aiosqlite import Connection
from app.database import get_db
from app.dependencies import require_api_key, rate_limit
from app.schemas import FeedCreate, FeedOut
from app.utils.security import validate_feed_url
from loguru import logger

router = APIRouter(prefix="/feeds", tags=["Feeds"])

@router.get("", response_model=list[FeedOut])
async def list_feeds(db: Connection = Depends(get_db)):
    cursor = await db.execute("SELECT id, url, title, added_at, last_fetch_at FROM feeds ORDER BY added_at DESC")
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]

@router.post("", status_code=201, dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def add_feed(feed: FeedCreate, db: Connection = Depends(get_db)):
    url = validate_feed_url(str(feed.url))
    try:
        cursor = await db.execute("INSERT INTO feeds (url) VALUES (?)", (url,))
        await db.commit()
        feed_id = cursor.lastrowid
        logger.info("Added feed id={} url={}", feed_id, url)
        return {"id": feed_id, "url": url}
    except Exception:
        raise HTTPException(status_code=400, detail="Feed URL already exists or invalid")

@router.delete("/{feed_id}", dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def delete_feed(feed_id: int, db: Connection = Depends(get_db)):
    cursor = await db.execute("DELETE FROM feeds WHERE id = ?", (feed_id,))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Feed not found")
    await db.commit()
    logger.info("Deleted feed id={}", feed_id)
    return {"ok": True}
