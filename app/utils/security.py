"""URL safety checks used to prevent server-side request forgery (SSRF).

Two layers are applied:

1. ``check_feed_url`` validates the URL syntactically and rejects IP literals
   and well-known hostnames that point at non-public addresses.
2. ``PublicOnlyResolver`` is plugged into aiohttp so that every DNS lookup made
   while fetching (including redirect targets) is filtered, which also covers
   hostnames that resolve to private addresses and DNS rebinding.
"""
import ipaddress
import socket
from typing import Any, Dict, List
from urllib.parse import urlparse

from aiohttp.abc import AbstractResolver
from aiohttp.resolver import DefaultResolver
from fastapi import HTTPException

BLOCKED_HOSTNAMES = {"localhost", "localhost.localdomain", "ip6-localhost", "ip6-loopback"}


class UnsafeURLError(ValueError):
    """Raised when a URL is not allowed to be fetched."""


def is_public_ip(address: str) -> bool:
    try:
        ip = ipaddress.ip_address(address.split("%", 1)[0])  # strip IPv6 zone id
    except ValueError:
        return False
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


def check_feed_url(url: str) -> str:
    """Return the URL if it is safe to fetch, otherwise raise UnsafeURLError."""
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise UnsafeURLError("Only HTTP/HTTPS URLs allowed")
    host = (parsed.hostname or "").rstrip(".").lower()
    if not host:
        raise UnsafeURLError("Invalid URL")
    if host in BLOCKED_HOSTNAMES or host.endswith(".localhost"):
        raise UnsafeURLError("Local/private URLs not allowed")
    try:
        ipaddress.ip_address(host)
        is_ip_literal = True
    except ValueError:
        is_ip_literal = False
    if is_ip_literal and not is_public_ip(host):
        raise UnsafeURLError("Local/private URLs not allowed")
    return url.strip()


def validate_feed_url(url: str) -> str:
    """API-layer wrapper that converts UnsafeURLError into an HTTP 400."""
    try:
        return check_feed_url(url)
    except UnsafeURLError as e:
        raise HTTPException(status_code=400, detail=str(e))


class PublicOnlyResolver(AbstractResolver):
    """aiohttp resolver that drops any non-public address from DNS results."""

    def __init__(self) -> None:
        self._inner = DefaultResolver()

    async def resolve(self, host: str, port: int = 0, family: int = socket.AF_INET) -> List[Dict[str, Any]]:
        infos = await self._inner.resolve(host, port, family)
        public = [info for info in infos if is_public_ip(info["host"])]
        if not public:
            raise OSError(f"Refusing to connect to non-public address for host {host!r}")
        return public

    async def close(self) -> None:
        await self._inner.close()
