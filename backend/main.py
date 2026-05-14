"""
ShopSage AI - FastAPI Application Entry Point
"""
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import settings
from .routes import vision_router, analyze_router, style_router, orchestrate_router, tracking_router, user_data_router, stream_router, chat_router

# ── Logging setup ─────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("shopsage")


# ── Lifespan (startup / shutdown hooks) ──────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("ShopSage AI backend starting up (env=%s)", settings.APP_ENV)
    yield
    logger.info("ShopSage AI backend shut down.")


# ── FastAPI app ────────────────────────────────────────────────
app = FastAPI(
    title="ShopSage AI – Hybrid Multi-Agent Backend",
    description=(
        "A high-performance, async FastAPI backend powering the ShopSage AI dashboard. "
        "Orchestrates specialized AI agents:\n\n"
        "- **Vision Agent** (Gemini 3 Flash → Gemini 2.5 Pro fallback) – product identification from images\n"
        "- **Detective Agent** – search execution and review scraping\n"
        "- **Analyst Agent** (Gemini 2.5 Pro) – review analysis & buy/wait strategy\n"
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


# ── Health check ──────────────────────────────────────────────
@app.get("/health", tags=["Health"], summary="Health check")
async def health():
    return {"status": "ok", "env": settings.APP_ENV, "version": "1.0.0"}


# ── Dev entry-point ───────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.APP_ENV == "development",
        log_level=settings.LOG_LEVEL.lower(),
    )
