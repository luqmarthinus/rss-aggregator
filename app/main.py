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
        while True:
            await asyncio.sleep(settings.refresh_interval_minutes * 60)
            logger.info("Background refresh starting")
            await refresh_all_feeds()
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

app = FastAPI(title="RSS Aggregator API", version="1.0.0", lifespan=lifespan)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers (unversioned) for backward compatibility
app.include_router(feeds.router)
app.include_router(articles.router)
app.include_router(refresh.router)
app.include_router(stats.router)
app.include_router(opml.router)

app.include_router(feeds.router, prefix="/v1")   # adds /v1/feeds
app.include_router(articles.router, prefix="/v1")
app.include_router(refresh.router, prefix="/v1")
app.include_router(stats.router, prefix="/v1")
app.include_router(opml.router, prefix="/v1")

# Health check
@app.get("/health")
async def health():
    return {"status": "ok"}

# Serve static frontend at root
app.mount("/", StaticFiles(directory="static", html=True), name="static")