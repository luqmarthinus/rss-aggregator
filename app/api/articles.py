from typing import Optional

from aiosqlite import Connection
from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger

from app.database import get_db
from app.dependencies import rate_limit, require_api_key
from app.schemas import ArticleOut, ArticleReadUpdate

router = APIRouter(prefix="/articles", tags=["Articles"])


@router.get("", response_model=list[ArticleOut])
async def list_articles(
    feed_id: Optional[int] = Query(None),
    is_read: Optional[bool] = Query(None),
    search: Optional[str] = Query(None, max_length=200),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Connection = Depends(get_db),
):
    query = "SELECT id, feed_id, title, link, summary, published_at, is_read FROM articles WHERE 1=1"
    params: list = []
    if feed_id is not None:
        query += " AND feed_id = ?"
        params.append(feed_id)
    if is_read is not None:
        query += " AND is_read = ?"
        params.append(1 if is_read else 0)
    if search:
        # Escape LIKE wildcards so a search for "100%" matches literally.
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query += " AND (title LIKE ? ESCAPE '\\' OR summary LIKE ? ESCAPE '\\')"
        params.extend([f"%{escaped}%", f"%{escaped}%"])
    # Entries without a publish date fall back to when we first saw them.
    query += " ORDER BY COALESCE(published_at, created_at) DESC, id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


@router.put("/{article_id}/read", dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def mark_read(article_id: int, update: ArticleReadUpdate, db: Connection = Depends(get_db)):
    cursor = await db.execute(
        "UPDATE articles SET is_read = ? WHERE id = ?", (1 if update.is_read else 0, article_id)
    )
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Article not found")
    await db.commit()
    logger.debug("Article {} marked read={}", article_id, update.is_read)
    return {"ok": True}


@router.post("/mark-all-read", dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def mark_all_read(feed_id: Optional[int] = Query(None), db: Connection = Depends(get_db)):
    """Mark every unread article as read, optionally limited to one feed."""
    query = "UPDATE articles SET is_read = 1 WHERE is_read = 0"
    params: list = []
    if feed_id is not None:
        query += " AND feed_id = ?"
        params.append(feed_id)
    cursor = await db.execute(query, params)
    await db.commit()
    logger.info("Marked {} articles read (feed_id={})", cursor.rowcount, feed_id)
    return {"updated": cursor.rowcount}
