from fastapi import APIRouter, BackgroundTasks, Depends
from loguru import logger

from app.dependencies import rate_limit, require_api_key
from app.services.refresh_service import refresh_all_feeds

router = APIRouter(prefix="/refresh", tags=["Refresh"])

@router.post("", dependencies=[Depends(require_api_key), Depends(rate_limit)])
async def manual_refresh(background_tasks: BackgroundTasks):
    background_tasks.add_task(refresh_all_feeds)
    logger.info("Manual refresh triggered")
    return {"message": "Refresh started in background"}