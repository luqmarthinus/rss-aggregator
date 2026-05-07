from fastapi import APIRouter, Depends, BackgroundTasks
from app.dependencies import require_api_key, rate_limit
from app.services.refresh_service import refresh_all_feeds
from loguru import logger

router = APIRouter(prefix="/refresh", tags=["Refresh"])

@router.post("", dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def manual_refresh(background_tasks: BackgroundTasks):
    background_tasks.add_task(refresh_all_feeds)
    logger.info("Manual refresh triggered")
    return {"message": "Refresh started in background"}