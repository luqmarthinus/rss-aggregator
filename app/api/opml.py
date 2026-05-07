from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import PlainTextResponse
from aiosqlite import Connection
from app.database import get_db
from app.dependencies import require_api_key, rate_limit
from app.services.opml_service import generate_opml, parse_opml
from loguru import logger
import xml.etree.ElementTree as ET

router = APIRouter(prefix="/feeds", tags=["OPML"])

@router.get("/export.opml", response_class=PlainTextResponse)
async def export_opml(db: Connection = Depends(get_db)):
    cursor = await db.execute("SELECT url, title FROM feeds")
    feeds = await cursor.fetchall()
    opml = generate_opml(feeds)
    return PlainTextResponse(content=opml, media_type="text/xml")

@router.post("/import.opml", dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def import_opml(file: UploadFile = File(...), db: Connection = Depends(get_db)):
    content = await file.read()
    try:
        urls = parse_opml(content)
        added = 0
        for url in urls:
            try:
                await db.execute("INSERT INTO feeds (url) VALUES (?)", (url,))
                added += 1
            except:
                pass
        await db.commit()
        logger.info("OPML import added {} feeds", added)
        return {"added": added}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
