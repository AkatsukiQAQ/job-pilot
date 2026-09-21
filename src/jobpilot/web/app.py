"""FastAPI application factory: JSON API under /api, built frontend (if present) at /."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from jobpilot import get_version
from jobpilot.settings import Settings
from jobpilot.store.db import connect, run_migrations
from jobpilot.web.api import router

# <repo>/frontend/dist when running from a checkout; absent in an installed wheel (step 7 revisits).
DIST_DIR = Path(__file__).resolve().parents[3] / "frontend" / "dist"

LOOPBACK_HOSTS = ("127.0.0.1", "localhost", "::1")


def create_app(
    settings: Settings, *, dist_dir: Path = DIST_DIR, bind_host: str | None = None
) -> FastAPI:
    """Build the app. Refuses a non-loopback bind while no auth mode is implemented."""
    effective_host = bind_host or settings.host
    if effective_host not in LOOPBACK_HOSTS and settings.auth_mode == "none":
        raise RuntimeError(
            f"refusing to serve on {effective_host!r} with JOBPILOT_AUTH_MODE=none: auth modes are"
            " not implemented yet, bind to 127.0.0.1 / localhost instead"
        )

    conn = connect(settings.db_path)
    try:
        run_migrations(conn)
    finally:
        conn.close()

    app = FastAPI(
        title="Mita JobPilot",
        version=get_version(),
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        redoc_url=None,
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=list(dict.fromkeys([*LOOPBACK_HOSTS, settings.host, effective_host])),
    )
    app.state.settings = settings
    app.include_router(router)

    dist = dist_dir.resolve()
    if (dist / "index.html").is_file():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

        @app.get("/{path:path}", include_in_schema=False)
        def spa(path: str) -> FileResponse:
            candidate = (dist / path).resolve()
            if candidate.is_file() and candidate.is_relative_to(dist):
                return FileResponse(candidate)
            return FileResponse(dist / "index.html")

    return app


def app_from_env() -> FastAPI:
    """Factory for `uvicorn --factory` (used by `jobpilot serve --reload`)."""
    return create_app(Settings())


__all__ = ["DIST_DIR", "LOOPBACK_HOSTS", "app_from_env", "create_app"]
