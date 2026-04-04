"""
FastAPI application entry point.

Start with:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import chat, documents, health
from app.config.settings import get_settings
from app.utils.logger import logger


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialise all components at startup; clean up on shutdown."""
    s = get_settings()
    logger.info(f"Starting {s.agent_name} v{s.agent_version}...")

    # Defer heavy init (RAG, embedding model) to a background task
    # so the HTTP port binds immediately and Render detects it.
    async def _deferred_init():
        await asyncio.sleep(0.1)  # let the server bind first
        from app.agent.core import get_agent
        try:
            get_agent()
        except Exception as e:
            logger.error(f"Agent init failed: {e}")

    asyncio.create_task(_deferred_init())

    # Start background workflows
    scheduler = None
    file_observer = None

    try:
        from app.workflows.scheduler import start_scheduler

        scheduler = start_scheduler()
    except Exception as e:
        logger.warning(f"Scheduler failed to start: {e}")

    try:
        from app.workflows.file_watcher import start_file_watcher

        file_observer = start_file_watcher()
    except Exception as e:
        logger.warning(f"File watcher failed to start: {e}")

    logger.info(f"{s.agent_name} running on http://{s.api_host}:{s.api_port}")

    yield  # ← application runs here

    # Shutdown
    logger.info("Shutting down...")

    if scheduler:
        from app.workflows.scheduler import stop_scheduler

        stop_scheduler()

    if file_observer:
        from app.workflows.file_watcher import stop_file_watcher

        stop_file_watcher()


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    s = get_settings()

    app = FastAPI(
        title=s.agent_name,
        description=s.agent_description,
        version=s.agent_version,
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],   # Tighten in production via config
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(health.router)
    app.include_router(chat.router)
    app.include_router(documents.router)

    # Serve static UI assets (embeddable widget)
    static_dir = Path(__file__).parent.parent / "ui" / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "agent": s.agent_name,
            "version": s.agent_version,
            "docs": "/docs",
            "chat": "/chat",
            "health": "/health",
        }

    return app


app = create_app()
