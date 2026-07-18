from __future__ import annotations

import subprocess
import sys
import threading
import time
from pathlib import Path

from dotenv import load_dotenv

from app.common.custom_exception import CustomException
from app.common.logger import get_logger
from app.config.settings import settings

logger = get_logger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
UI_PATH = PROJECT_ROOT / "app" / "frontend" / "ui.py"

load_dotenv(PROJECT_ROOT / ".env")


def run_backend() -> None:
    logger.info(
        "Starting backend service on %s:%s",
        settings.backend_host,
        settings.backend_port,
    )
    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.backend.api:app",
                "--host",
                settings.backend_host,
                "--port",
                str(settings.backend_port),
            ],
            check=True,
            cwd=PROJECT_ROOT,
        )
    except Exception as exc:
        logger.error("Backend service failed")
        raise CustomException("Failed to start backend", error_detail=exc) from exc


def run_frontend() -> None:
    logger.info("Starting frontend service")
    try:
        subprocess.run(
            [
                sys.executable,
                "-m",
                "streamlit",
                "run",
                str(UI_PATH),
                "--server.headless",
                "true",
            ],
            check=True,
            cwd=PROJECT_ROOT,
        )
    except Exception as exc:
        logger.error("Frontend service failed")
        raise CustomException("Failed to start frontend", error_detail=exc) from exc


def main() -> None:
    backend_thread = threading.Thread(target=run_backend, name="backend", daemon=True)
    backend_thread.start()
    time.sleep(2)
    run_frontend()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Shutting down application")
    except CustomException as exc:
        logger.exception("Application error: %s", exc)
        sys.exit(1)
