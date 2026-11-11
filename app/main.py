from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger
import sys
import asyncio
from app.database import init_db
from app.config import settings
from app.services.refresh_service import refresh_all_feeds
from app.api import feeds, articles, refresh, stats, opml

# Configure Loguru
logger.remove()
logger.add(sys.stdout, format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{line} | {message}", level="INFO")
logger.add("logs/app.log", rotation="10 MB", retention="7 days", level="DEBUG")

# Background refresh task
refresh_task = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    logger.info("Database ready")
    # Start background refresh loop
    async def periodic_refresh():
        # Refresh once shortly after startup, then on the configured interval.
        await asyncio.sleep(5)
        while True:
            logger.info("Background refresh starting")
            try:
                await refresh_all_feeds()
            except Exception:
                logger.exception("Background refresh failed")
            await asyncio.sleep(settings.refresh_interval_minutes * 60)
    global refresh_task
    refresh_task = asyncio.create_task(periodic_refresh())
    yield
    # Shutdown
    if refresh_task:
        refresh_task.cancel()
        try:
            await refresh_task
        except asyncio.CancelledError:
            logger.info("Background refresh stopped")

app = FastAPI(title="RSS Aggregator API", version="1.1.0", lifespan=lifespan)

# CORS: the bundled frontend is same-origin; set CORS_ORIGINS to allow others.
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "X-API-Key"],
    )

# Include routers (unversioned) for backward compatibility
# OPML router goes before feeds so /feeds/export.opml isn't shadowed by future /feeds/{id} GET routes.
for router in (opml.router, feeds.router, articles.router, refresh.router, stats.router):
    app.include_router(router)                  # unversioned, for backward compatibility
    app.include_router(router, prefix="/v1")    # e.g. /v1/feeds

# Health check
@app.get("/health")
async def health():
    return {"status": "ok"}

# Serve static frontend at root
app.mount("/", StaticFiles(directory="static", html=True), name="static")