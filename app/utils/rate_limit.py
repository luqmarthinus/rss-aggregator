import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import HTTPException, Request

from app.config import settings

WINDOW_SECONDS = 60

# key: client IP, value: timestamps of requests inside the current window
request_log: Dict[str, Deque[float]] = defaultdict(deque)


def rate_limit_middleware(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    timestamps = request_log[client_ip]
    while timestamps and now - timestamps[0] >= WINDOW_SECONDS:
        timestamps.popleft()
    if len(timestamps) >= settings.rate_limit_per_minute:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    timestamps.append(now)

    # Drop idle clients occasionally so the dict doesn't grow without bound.
    if len(request_log) > 1000:
        for ip in [ip for ip, ts in request_log.items() if not ts or now - ts[-1] >= WINDOW_SECONDS]:
            del request_log[ip]
