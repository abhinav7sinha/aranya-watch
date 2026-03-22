"""FastAPI application entrypoint."""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from app.api.routes import router
from app.core.config import get_settings
from app.db.init_db import init_db

logger = logging.getLogger("aranyacore.app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database resources on startup."""

    settings = get_settings()
    app.state.preview_mode = settings.preview_mode

    if not settings.preview_mode:
        try:
            init_db()
        except Exception as exc:  # pragma: no cover - fallback behavior
            app.state.preview_mode = True
            logger.warning("Falling back to preview mode because database init failed: %s", exc)
    yield


def create_app() -> FastAPI:
    """Build and configure the FastAPI app."""

    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        lifespan=lifespan,
    )
    app.state.preview_mode = settings.preview_mode
    app.include_router(router)
    return app


app = create_app()
