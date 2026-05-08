from fastapi import Header, HTTPException, Request

from app.config import settings


async def require_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid API Key")

async def rate_limit(request: Request):
    from app.utils.rate_limit import rate_limit_middleware
    rate_limit_middleware(request)

# Database session dependency is already in database.get_db
