from urllib.parse import urlparse

from fastapi import HTTPException


def validate_feed_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Only HTTP/HTTPS URLs allowed")
    host = parsed.hostname
    if not host:
        raise HTTPException(status_code=400, detail="Invalid URL")
    # Block localhost, private IPs
    banned_hosts = ["localhost", "127.0.0.1", "0.0.0.0", "::1"]
    if host in banned_hosts or host.startswith("192.168.") or host.startswith("10.") or host.startswith("172."):
        raise HTTPException(status_code=400, detail="Local/private URLs not allowed")
    return url
