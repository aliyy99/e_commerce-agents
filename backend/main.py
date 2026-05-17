"""
Techno Track AI - FastAPI Application Entry Point
"""
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .routes import vision_router, analyze_router, style_router, orchestrate_router, tracking_router, user_data_router, stream_router, chat_router, price_history_router, compare_devices_router, campaigns_router

# ── Logging setup ─────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("technotrack")


# ── Lifespan (startup / shutdown hooks) ──────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Techno Track AI backend starting up (env=%s)", settings.APP_ENV)
    yield
    logger.info("Techno Track AI backend shut down.")


# ── FastAPI app ────────────────────────────────────────────────
app = FastAPI(
    title="Techno Track – Hybrid Multi-Agent Backend",
    description=(
        "A high-performance, async FastAPI backend powering the Techno Track dashboard. "
        "Orchestrates specialized AI agents:\n\n"
        "- **Vision Agent** (Gemini 3 Flash → Gemini 2.5 Flash fallback) – product identification from images\n"
        "- **Detective Agent** – search execution and review scraping\n"
        "- **Analyst Agent** (Gemini 2.5 Flash) – review analysis & buy/wait strategy\n"
        "- **Visualizer Agent** (Imagen 3) – outfit & room placement generation\n\n"
        "All endpoints are validated with Pydantic v2. Results are persisted in Supabase."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all for dev WebSockets
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request timing middleware ──────────────────────────────────
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = int((time.monotonic() - start) * 1000)
    response.headers["X-Process-Time-Ms"] = str(duration_ms)
    logger.debug("%s %s → %d (%dms)", request.method, request.url.path, response.status_code, duration_ms)
    return response


# ── Global error handler ──────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Check server logs for details."},
    )


# ── Register routers ──────────────────────────────────────────
app.include_router(vision_router,      prefix="/api/v1")
app.include_router(analyze_router,     prefix="/api/v1")
app.include_router(style_router,       prefix="/api/v1")
app.include_router(orchestrate_router, prefix="/api/v1")
app.include_router(tracking_router,    prefix="/api/v1")
app.include_router(user_data_router,   prefix="/api/v1")
app.include_router(stream_router,      prefix="/api/v1")
app.include_router(chat_router,        prefix="/api/v1")
app.include_router(price_history_router, prefix="/api/v1")
app.include_router(compare_devices_router, prefix="/api/v1")
app.include_router(campaigns_router,   prefix="/api/v1")


# ── Health check ──────────────────────────────────────────────
@app.get("/health", tags=["Health"], summary="Health check")
async def health():
    return {"status": "ok", "env": settings.APP_ENV, "version": "1.0.0"}


# ── Dev entry-point ───────────────────────────────────────────
def _find_listener_pid(port: int) -> int | None:
    """Best-effort lookup of the PID holding a TCP listen socket on ``port``.

    Uses ``netstat`` on Windows and ``lsof`` on POSIX so we don't depend on
    ``psutil``. Returns ``None`` if the platform tool isn't available or the
    output can't be parsed.
    """
    import platform
    import subprocess

    try:
        if platform.system() == "Windows":
            out = subprocess.check_output(
                ["netstat", "-ano", "-p", "TCP"],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            needle = f":{port} "
            for line in out.splitlines():
                if "LISTENING" in line and needle in line:
                    parts = line.split()
                    return int(parts[-1])
        else:
            out = subprocess.check_output(
                ["lsof", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            line = out.strip().splitlines()
            if line:
                return int(line[0])
    except Exception:
        return None
    return None


def _ensure_port_available(host: str, port: int) -> None:
    """Exit early with an actionable message if the port is already taken.

    Without this the user sees the raw OS error (WinError 10048 on Windows,
    EADDRINUSE on POSIX) plus a long traceback — neither tells them what to
    do. We replace it with the offending PID and the exact command to free
    the port on their platform.
    """
    import socket
    import sys

    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        probe.bind((host if host != "0.0.0.0" else "127.0.0.1", port))
    except OSError:
        probe.close()
        pid = _find_listener_pid(port)
        print(
            f"\n[X] Port {port} is already in use"
            + (f" by PID {pid}" if pid else "")
            + " - the backend cannot start.",
            file=sys.stderr,
        )
        print("    Free it and try again:", file=sys.stderr)
        if sys.platform == "win32":
            if pid:
                print(f"      PowerShell:  Stop-Process -Id {pid} -Force", file=sys.stderr)
                print(f"      CMD:         taskkill /F /PID {pid}", file=sys.stderr)
            else:
                print(
                    "      PowerShell:  Get-NetTCPConnection -LocalPort "
                    f"{port} | ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force }}",
                    file=sys.stderr,
                )
        else:
            if pid:
                print(f"      kill -9 {pid}", file=sys.stderr)
            else:
                print(f"      lsof -iTCP:{port} -sTCP:LISTEN", file=sys.stderr)
        print(
            "    Tip: run the dev server with --reload (already on by default in development)"
            " so you rarely need to manually restart.\n",
            file=sys.stderr,
        )
        sys.exit(1)
    else:
        probe.close()


if __name__ == "__main__":
    import uvicorn

    _ensure_port_available("0.0.0.0", settings.PORT)
    is_dev = settings.APP_ENV == "development"
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=is_dev,
        # Scope the reloader to backend/ only. Without this, watchfiles scans
        # the whole project root (frontend/, node_modules/, *.log) and the log
        # file we ourselves write triggers a restart loop, racing the previous
        # worker for the port → WinError 10048 on Windows.
        reload_dirs=["backend"] if is_dev else None,
        reload_excludes=["*.log", "*.pyc", "__pycache__/*", ".venv/*"] if is_dev else None,
        log_level=settings.LOG_LEVEL.lower(),
    )
