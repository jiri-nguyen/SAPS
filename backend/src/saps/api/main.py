"""SAPS API entry point (contract: docs/02-architecture/api/saps-api.openapi.yaml)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, Response, status
from pydantic import BaseModel

from saps.adapters.persistence.db import database_is_reachable, dispose_engines, get_engine
from saps.api.origin_check import OriginCheckMiddleware
from saps.api.problems import install_problem_handlers
from saps.api.routers import invoices, matching_settings, notifications, session
from saps.api.upload_limit import UploadSizeLimitMiddleware
from saps.config import get_settings
from saps.logging_config import configure_logging


class Health(BaseModel):
    status: Literal["ok"]


class Readiness(BaseModel):
    status: Literal["ready", "not_ready"]
    database: bool


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging(get_settings().log_level)
    yield
    await dispose_engines()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="SAPS API", version="0.4.4", lifespan=lifespan)
    # The last middleware added runs first: Origin check, then the upload size guard.
    app.add_middleware(
        UploadSizeLimitMiddleware,
        path="/v1/invoices",
        max_file_bytes=settings.max_upload_size_mb * 1024 * 1024,
    )
    app.add_middleware(OriginCheckMiddleware, allowed_origin=settings.web_app_origin)
    install_problem_handlers(app)
    app.include_router(session.router)
    app.include_router(invoices.router)
    app.include_router(matching_settings.router)
    app.include_router(notifications.router)

    @app.get("/health", operation_id="getHealth", tags=["Health"])
    async def get_health() -> Health:
        """Liveness: the process is running (no dependency checks)."""
        return Health(status="ok")

    @app.get("/ready", tags=["Health"], include_in_schema=False)
    async def get_ready(response: Response) -> Readiness:
        """Readiness for Docker Compose: the SAPS Database is reachable."""
        db_ok = await database_is_reachable(get_engine(get_settings().app_database_url))
        if not db_ok:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return Readiness(status="ready" if db_ok else "not_ready", database=db_ok)

    return app


app = create_app()
