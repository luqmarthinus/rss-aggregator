import hmac

from fastapi import Header, HTTPException, Request

from app.config import settings
from app.utils.rate_limit import rate_limit_middleware


async def require_api_key(x_api_key: str = Header(...)):
    # Constant-time comparison avoids leaking the key through response timing.
    if not hmac.compare_digest(x_api_key.encode(), settings.api_key.encode()):
        raise HTTPException(status_code=403, detail="Invalid API Key")


async def rate_limit(request: Request):
    rate_limit_middleware(request)
