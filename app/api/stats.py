from aiosqlite import Connection
from fastapi import APIRouter, Depends

from app.database import get_db

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get("")
async def get_stats(db: Connection = Depends(get_db)):
    feeds_cursor = await db.execute("SELECT COUNT(*) FROM feeds")
    feeds_count = (await feeds_cursor.fetchone())[0]
    articles_cursor = await db.execute("SELECT COUNT(*) FROM articles")
    articles_count = (await articles_cursor.fetchone())[0]
    unread_cursor = await db.execute("SELECT COUNT(*) FROM articles WHERE is_read = 0")
    unread_count = (await unread_cursor.fetchone())[0]
    return {"feeds": feeds_count, "articles": articles_count, "unread": unread_count}
