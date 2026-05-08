from typing import Optional

from aiosqlite import Connection
from fastapi import APIRouter, Depends, Query
from loguru import logger

from app.database import get_db
from app.dependencies import rate_limit, require_api_key
from app.schemas import ArticleOut, ArticleReadUpdate

router = APIRouter(prefix="/articles", tags=["Articles"])


@router.get("", response_model=list[ArticleOut])
async def list_articles(
    feed_id: Optional[int] = Query(None),
    is_read: Optional[bool] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: Connection = Depends(get_db),
):
    query = "SELECT id, feed_id, title, link, summary, published_at, is_read FROM articles WHERE 1=1"
    params = []
    if feed_id:
        query += " AND feed_id = ?"
        params.append(feed_id)
    if is_read is not None:
        query += " AND is_read = ?"
        params.append(1 if is_read else 0)
    if search:
        query += " AND (title LIKE ? OR summary LIKE ?)"
        search_param = f"%{search}%"
        params.extend([search_param, search_param])
    query += " ORDER BY published_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]


@router.put("/{article_id}/read", dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def mark_read(article_id: int, update: ArticleReadUpdate, db: Connection = Depends(get_db)):
    await db.execute("UPDATE articles SET is_read = ? WHERE id = ?", (1 if update.is_read else 0, article_id))
    await db.commit()
    logger.debug("Article {} marked read={}", article_id, update.is_read)
    return {"ok": True}
