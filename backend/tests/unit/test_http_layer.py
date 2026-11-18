"""Origin check, problem details and role checks, on a small app without a database."""

from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from saps.api.deps import current_user, require_roles
from saps.api.origin_check import OriginCheckMiddleware
from saps.api.problems import install_problem_handlers
from saps.domain.users import CurrentUser, Role

ORIGIN = "http://localhost:5173"


class Body(BaseModel):
    name: str


def _app(role: Role = Role.ACCOUNTING_MEMBER) -> FastAPI:
    app = FastAPI()
    app.add_middleware(OriginCheckMiddleware, allowed_origin=ORIGIN + "/")
    install_problem_handlers(app)

    @app.get("/thing")
    async def get_thing() -> dict[str, str]:
        return {"ok": "yes"}

    @app.post("/thing")
    async def post_thing(body: Body) -> dict[str, str]:
        return {"name": body.name}

    @app.get("/teapot")
    async def teapot() -> None:
        raise HTTPException(418, "short and stout", headers={"X-Extra": "1"})

    @app.get("/managers-only", dependencies=[Depends(require_roles(Role.ACCOUNTING_MANAGER))])
    async def managers_only() -> dict[str, str]:
        return {"ok": "yes"}

    app.dependency_overrides[current_user] = lambda: CurrentUser(uuid4(), uuid4(), "u", "U", role)
    return app


def _client(app: FastAPI) -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def test_unsafe_methods_need_the_web_app_origin() -> None:
    async with _client(_app()) as client:
        missing = await client.post("/thing", json={"name": "a"})
        foreign = await client.post("/thing", json={"name": "a"}, headers={"Origin": "https://evil.example"})
        allowed = await client.post("/thing", json={"name": "a"}, headers={"Origin": ORIGIN})
        safe = await client.get("/thing")
    assert missing.status_code == foreign.status_code == 403
    assert missing.headers["content-type"] == "application/problem+json"
    assert missing.json()["detail"] == "The request origin is not allowed."
    assert allowed.status_code == 200 and safe.status_code == 200


async def test_errors_are_problem_details() -> None:
    async with _client(_app()) as client:
        teapot = await client.get("/teapot")
        invalid = await client.post("/thing", json={"wrong": 1}, headers={"Origin": ORIGIN})
    assert teapot.status_code == 418
    assert teapot.json() == {
        "type": "about:blank",
        "title": "I'm a Teapot",
        "status": 418,
        "detail": "short and stout",
    }
    assert teapot.headers["x-extra"] == "1"
    assert invalid.status_code == 400
    assert invalid.json()["errors"][0]["field"] == "name"


async def test_role_check_refuses_and_allows() -> None:
    async with _client(_app(Role.ACCOUNTING_MEMBER)) as client:
        refused = await client.get("/managers-only")
    async with _client(_app(Role.ACCOUNTING_MANAGER)) as client:
        allowed = await client.get("/managers-only")
    assert refused.status_code == 403
    assert allowed.status_code == 200
