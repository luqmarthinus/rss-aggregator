import aiohttp
from loguru import logger
from app.config import settings

async def send_ntfy_notification(title: str, message: str, link: str):
    if not settings.ntfy_topic:
        return
    url = f"{settings.ntfy_url.rstrip('/')}/{settings.ntfy_topic}"
    data = f"{title}\n\n{message}\n\n{link}"
    try:
        async with aiohttp.ClientSession() as session:
            await session.post(url, data=data.encode("utf-8"), headers={"Title": "New RSS Article"})
        logger.debug("ntfy notification sent for: {}", title)
    except Exception as e:
        logger.warning("ntfy send failed: {}", e)
