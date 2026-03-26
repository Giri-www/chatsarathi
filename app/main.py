"""FastAPI entrypoint for the ChatSarathi backend."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import ErrorResponse, ChatSarathiError, logger, settings
from app.routes.chat_routes import router as chat_router
from app.services.analytics_service import analytics_service
from app.services.langserve_service import get_langserve_runnable

try:
    from langserve import add_routes
except ImportError:  # pragma: no cover - optional dependency at runtime
    add_routes = None


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Initialize service dependencies on startup."""
    await analytics_service.initialize()
    logger.info("app.startup", app_name=settings.app_name)
    yield
    logger.info("app.shutdown", app_name=settings.app_name)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title=settings.app_name, version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(ChatSarathiError)
    async def handle_ChatSarathi_error(_: Request, exc: ChatSarathiError) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(error=exc.message, code=exc.code, details=exc.details).model_dump(),
        )

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "ok", "service": settings.app_name}

    app.include_router(chat_router, prefix=settings.api_prefix, tags=["chat"])

    langserve_runnable = get_langserve_runnable()
    if add_routes is not None and langserve_runnable is not None:
        add_routes(app, langserve_runnable, path=f"{settings.api_prefix}/langserve")
        logger.info("langserve.enabled", path=f"{settings.api_prefix}/langserve")
    else:
        logger.info("langserve.disabled", reason="langserve dependencies not installed")

    return app


app = create_app()
