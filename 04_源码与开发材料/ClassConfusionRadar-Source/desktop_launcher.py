"""
本文件的作用是：启动本地后端服务、打开浏览器并管理桌面程序生命周期。
"""
from __future__ import annotations

import json
import logging
import os
import socket
import sys
import threading
import time
import webbrowser
from pathlib import Path
from urllib import error, request

import uvicorn


APP_NAME = "Class Confusion Radar"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def main() -> int:
    runtime_dir = get_runtime_dir()
    bundle_dir = get_bundle_dir()
    app_data_dir = runtime_dir / "app_data"
    uploads_dir = app_data_dir / "uploads"
    logs_dir = app_data_dir / "logs"
    database_path = app_data_dir / "class_confusion_radar.db"
    frontend_dist_dir = resolve_frontend_dist_dir(bundle_dir)

    app_data_dir.mkdir(parents=True, exist_ok=True)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)

    configure_logging(logs_dir / "launcher.log")

    host = os.getenv("CCR_HOST", DEFAULT_HOST)
    port = int(os.getenv("CCR_PORT", str(DEFAULT_PORT)))
    base_url = f"http://{host}:{port}"

    if not ensure_can_start(host, port, base_url):
        return 0

    configure_environment(database_path, uploads_dir, frontend_dist_dir)
    add_backend_path(bundle_dir)

    from app.core.config import reset_settings_cache
    from app.db.base import Base
    from app.db.session import get_engine, reset_db_state
    from app.main import create_app

    reset_settings_cache()
    reset_db_state()
    engine = get_engine()
    Base.metadata.create_all(bind=engine)

    app = create_app()

    bootstrap_thread = threading.Thread(
        target=bootstrap_after_start,
        kwargs={
            "bundle_dir": bundle_dir,
            "base_url": base_url,
        },
        daemon=True,
    )
    bootstrap_thread.start()

    logging.info("Starting desktop server at %s", base_url)
    uvicorn.run(app, host=host, port=port, log_level="info")
    return 0


def get_bundle_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent


def get_runtime_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def resolve_frontend_dist_dir(bundle_dir: Path) -> Path:
    if getattr(sys, "frozen", False):
        return bundle_dir / "frontend_dist"
    return bundle_dir / "frontend" / "dist"


def configure_environment(database_path: Path, uploads_dir: Path, frontend_dist_dir: Path) -> None:
    os.environ.setdefault("APP_ENV", "desktop")
    os.environ.setdefault("DEBUG", "false")
    os.environ.setdefault("AI_PROVIDER", "offline")
    os.environ.setdefault("DATABASE_URL", f"sqlite:///{database_path.resolve().as_posix()}")
    os.environ.setdefault("STORAGE_DIR", str(uploads_dir.resolve()))
    os.environ.setdefault("FRONTEND_DIST_DIR", str(frontend_dist_dir.resolve()))


def add_backend_path(bundle_dir: Path) -> None:
    backend_dir = bundle_dir / "backend"
    backend_path = str(backend_dir.resolve())
    if backend_dir.exists() and backend_path not in sys.path:
        sys.path.insert(0, backend_path)


def configure_logging(log_path: Path) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
    )


def ensure_can_start(host: str, port: int, base_url: str) -> bool:
    if is_backend_ready(base_url):
        logging.info("Existing service detected at %s, opening browser only", base_url)
        webbrowser.open(base_url)
        return False

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind((host, port))
        except OSError as exc:
            message = (
                f"{APP_NAME} failed to start because port {port} is already in use. "
                f"Close the conflicting program or set CCR_PORT to a different value. "
                f"Original error: {exc}"
            )
            logging.error(message)
            raise SystemExit(message) from exc
    return True


def bootstrap_after_start(bundle_dir: Path, base_url: str) -> None:
    try:
        wait_for_backend(base_url)
        maybe_seed_builtin_demos(bundle_dir, base_url)
    except Exception as exc:  # pragma: no cover - launcher runtime path
        logging.exception("Desktop bootstrap failed: %s", exc)
    finally:
        webbrowser.open(base_url)


def wait_for_backend(base_url: str) -> None:
    health_url = f"{base_url}/health"
    for _ in range(60):
        if is_backend_ready(base_url):
            return
        time.sleep(1)
    raise RuntimeError(f"Backend did not become ready in time: {health_url}")


def is_backend_ready(base_url: str) -> bool:
    try:
        with request.urlopen(f"{base_url}/health", timeout=2) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return payload.get("status") == "ok"
    except Exception:
        return False


def maybe_seed_builtin_demos(bundle_dir: Path, base_url: str) -> None:
    sessions = api_request("GET", f"{base_url}/api/v1/sessions")
    if sessions:
        logging.info("Existing sessions detected, skipping builtin demo seeding")
        return

    logging.info("No sessions found, seeding bundled demo sessions")
    seed_competition_demo(bundle_dir, base_url)
    seed_public_demo(bundle_dir, base_url)


def seed_competition_demo(bundle_dir: Path, base_url: str) -> None:
    import scripts.demo_seed as demo_seed

    demo_seed.ROOT_DIR = bundle_dir
    demo_seed.SAMPLE_DIR = bundle_dir / "docs" / "samples" / "competition-demo"
    demo_seed.DEFAULT_FRONTEND_URL = base_url
    run_seed_main(
        demo_seed,
        [
            "--base-url",
            base_url,
            "--frontend-url",
            base_url,
            "--run-analytics",
            "--generate-suggestions",
        ],
    )


def seed_public_demo(bundle_dir: Path, base_url: str) -> None:
    import scripts.public_demo_seed as public_demo_seed

    public_demo_seed.ROOT_DIR = bundle_dir
    public_demo_seed.SAMPLE_DIR = bundle_dir / "docs" / "samples" / "public-demo"
    public_demo_seed.DEFAULT_FRONTEND_URL = base_url
    run_seed_main(
        public_demo_seed,
        [
            "--base-url",
            base_url,
            "--frontend-url",
            base_url,
            "--run-analytics",
            "--generate-enhanced",
        ],
    )


def run_seed_main(module, arguments: list[str]) -> None:
    original_argv = sys.argv[:]
    try:
        sys.argv = [module.__name__, *arguments]
        exit_code = module.main()
        if exit_code not in (None, 0):
            raise RuntimeError(f"{module.__name__} exited with code {exit_code}")
    finally:
        sys.argv = original_argv


def api_request(method: str, url: str):
    req = request.Request(url, method=method, headers={"Accept": "application/json"})
    try:
        with request.urlopen(req, timeout=15) as response:
            payload = response.read()
            return json.loads(payload.decode("utf-8")) if payload else None
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"{method} {url} failed: {detail}") from exc


if __name__ == "__main__":
    raise SystemExit(main())
