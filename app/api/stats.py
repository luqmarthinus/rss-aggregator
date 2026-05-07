from fastapi import APIRouter, Depends
from aiosqlite import Connection
from app.database import get_db

router = APIRouter(prefix="/stats", tags=["Stats"])

@router.get("/")
async def get_stats(db: Connection = Depends(get_db)):
    feeds_count = await db.execute_scalar("SELECT COUNT(*) FROM feeds")
    articles_count = await db.execute_scalar("SELECT COUNT(*) FROM articles")
    unread_count = await db.execute_scalar("SELECT COUNT(*) FROM articles WHERE is_read = 0")
    return {"feeds": feeds_count, "articles": articles_count, "unread": unread_count}
