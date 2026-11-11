from fastapi import APIRouter, BackgroundTasks, Depends
from loguru import logger

from app.dependencies import rate_limit, require_api_key
from app.services.refresh_service import is_refreshing, refresh_all_feeds

router = APIRouter(prefix="/refresh", tags=["Refresh"])


@router.post("", status_code=202, dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def manual_refresh(background_tasks: BackgroundTasks):
    if is_refreshing():
        return {"message": "Refresh already in progress", "refreshing": True}
    background_tasks.add_task(refresh_all_feeds)
    logger.info("Manual refresh triggered")
    return {"message": "Refresh started in background", "refreshing": True}


@router.get("/status")
async def refresh_status():
    return {"refreshing": is_refreshing()}
