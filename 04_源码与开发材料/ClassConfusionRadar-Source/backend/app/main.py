"""
本文件的作用是：创建并启动应用的主入口。
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.api.router import router
from app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.project_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    configure_frontend_routes(app)
    return app


def configure_frontend_routes(app: FastAPI) -> None:
    frontend_dist_dir = resolve_frontend_dist_dir()
    if not frontend_dist_dir:
        return

    index_file = frontend_dist_dir / "index.html"
    if not index_file.exists():
        return

    excluded_prefixes = ("api/", "docs", "redoc", "openapi.json", "health")

    @app.get("/", include_in_schema=False)
    async def serve_frontend_index() -> FileResponse:
        return FileResponse(index_file, headers={"Cache-Control": "no-store, max-age=0"})

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend_app(full_path: str) -> FileResponse:
        if full_path.startswith(excluded_prefixes):
            raise HTTPException(status_code=404, detail="Not Found")

        candidate = frontend_dist_dir / full_path
        if candidate.is_file():
            return FileResponse(candidate, headers={"Cache-Control": "no-cache"})

        return FileResponse(index_file, headers={"Cache-Control": "no-store, max-age=0"})


def resolve_frontend_dist_dir() -> Path | None:
    configured_path = os.getenv("FRONTEND_DIST_DIR")
    candidate_paths = []
    if configured_path:
        candidate_paths.append(Path(configured_path))

    project_default = Path(__file__).resolve().parents[2] / "frontend" / "dist"
    candidate_paths.append(project_default)

    for candidate in candidate_paths:
        if candidate.is_dir() and (candidate / "index.html").exists():
            return candidate
    return None


app = create_app()
