from fastapi import APIRouter, Depends, BackgroundTasks
from aiosqlite import Connection
from app.database import get_db
from app.dependencies import require_api_key, rate_limit
from app.services.refresh_service import refresh_all_feeds
from loguru import logger

router = APIRouter(prefix="/refresh", tags=["Refresh"])

@router.post("/", dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def manual_refresh(background_tasks: BackgroundTasks, db: Connection = Depends(get_db)):
    background_tasks.add_task(refresh_all_feeds, db)
    logger.info("Manual refresh triggered")
    return {"message": "Refresh started in background"}
