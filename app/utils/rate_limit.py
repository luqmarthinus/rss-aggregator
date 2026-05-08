import time
from collections import defaultdict

from fastapi import HTTPException, Request

from app.config import settings

# key: IP, value: list of timestamps
request_log = defaultdict(list)

def rate_limit_middleware(request: Request):
    client_ip = request.client.host
    now = time.time()
    window = 60  # 1 minute
    # Clean old entries
    request_log[client_ip] = [t for t in request_log[client_ip] if now - t < window]
    if len(request_log[client_ip]) >= settings.rate_limit_per_minute:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    request_log[client_ip].append(now)
