from aiosqlite import Connection
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response
from loguru import logger

from app.database import get_db
from app.dependencies import rate_limit, require_api_key
from app.services.opml_service import generate_opml, parse_opml
from app.services.refresh_service import refresh_all_feeds
from app.utils.security import UnsafeURLError, check_feed_url

MAX_OPML_BYTES = 2 * 1024 * 1024

router = APIRouter(prefix="/feeds", tags=["OPML"])


@router.get("/export.opml")
async def export_opml(db: Connection = Depends(get_db)):
    cursor = await db.execute("SELECT url, title FROM feeds ORDER BY COALESCE(title, url) COLLATE NOCASE")
    feeds = await cursor.fetchall()
    return Response(
        content=generate_opml(feeds),
        media_type="text/x-opml",
        headers={"Content-Disposition": 'attachment; filename="feeds.opml"'},
    )


@router.post("/import.opml", dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def import_opml(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Connection = Depends(get_db),
):
    content = await file.read(MAX_OPML_BYTES + 1)
    if len(content) > MAX_OPML_BYTES:
        raise HTTPException(status_code=413, detail="OPML file too large")
    try:
        urls = parse_opml(content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    added, skipped, rejected = 0, 0, []
    for url in dict.fromkeys(urls):  # de-duplicate, keep order
        try:
            url = check_feed_url(url)
        except UnsafeURLError:
            rejected.append(url)
            continue
        cursor = await db.execute("INSERT OR IGNORE INTO feeds (url) VALUES (?)", (url,))
        if cursor.rowcount:
            added += 1
        else:
            skipped += 1
    await db.commit()
    logger.info("OPML import: added={} skipped={} rejected={}", added, skipped, len(rejected))
    if added:
        background_tasks.add_task(refresh_all_feeds)
    return {"added": added, "skipped": skipped, "rejected": rejected}
