from aiosqlite import Connection
from fastapi import APIRouter, Depends

from app.database import get_db

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get("")
async def get_stats(db: Connection = Depends(get_db)):
    cursor = await db.execute(
        """
        SELECT (SELECT COUNT(*) FROM feeds) AS feeds,
               (SELECT COUNT(*) FROM articles) AS articles,
               (SELECT COUNT(*) FROM articles WHERE is_read = 0) AS unread
        """
    )
    row = await cursor.fetchone()
    return dict(row)
