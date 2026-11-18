"""SAPS API entry point (contract: docs/02-architecture/api/saps-api.openapi.yaml)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, Response, status
from pydantic import BaseModel

from saps.adapters.persistence.db import database_is_reachable, dispose_engines, get_engine
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
    app = FastAPI(title="SAPS API", version="0.4.0", lifespan=lifespan)

    @app.get("/health", operation_id="getHealth", tags=["Health"])
    async def get_health() -> Health:
        """Liveness: the process is running (no dependency checks)."""
        return Health(status="ok")

    @app.get("/ready", tags=["Health"], include_in_schema=False)
    async def get_ready(response: Response) -> Readiness:
        """Readiness for Docker Compose: the SAPS Database is reachable."""
        db_ok = await database_is_reachable(get_engine(get_settings().database_url))
        if not db_ok:
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return Readiness(status="ready" if db_ok else "not_ready", database=db_ok)

    return app


app = create_app()
