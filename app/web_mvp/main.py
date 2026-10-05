import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.web_mvp.api.appointments import router as appointments_router
from app.web_mvp.api.auth import router as auth_router
from app.web_mvp.api.chat import router as chat_router
from app.web_mvp.api.professors import router as professors_router
from app.web_mvp.api.admin import router as admin_router
from app.web_mvp.config import CORS_ORIGINS
from app.web_mvp.store import close_store, demo_mode_active, init_store, store_ready

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    await init_store()
    yield
    await close_store()


app = FastAPI(title="RGMCET AI Campus Assistant", version="0.3.0", lifespan=lifespan)

@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(professors_router)
app.include_router(appointments_router)
app.include_router(admin_router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error processing request %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred. Please try again later."},
    )


from pathlib import Path
from fastapi.staticfiles import StaticFiles

@app.get("/health")
@app.get("/api/health")
async def health():
    from app.web_mvp.llm import configured_provider
    return {
        "status": "ok",
        "demo_mode": demo_mode_active(),
        "database": "connected" if store_ready() and not demo_mode_active() else ("demo" if demo_mode_active() else "unavailable"),
        "llm_provider": configured_provider() or "none",
        "version": "0.3.0",
    }


@app.get("/api/llm-status")
async def llm_status():
    from app.web_mvp.llm import configured_provider
    from app.web_mvp import config
    provider = configured_provider() or "none"
    model = config.GEMINI_MODEL if provider == "gemini" else (config.OPENAI_MODEL if provider == "openai" else "none")
    return {
        "status": "ok" if provider != "none" else "fallback",
        "provider": provider,
        "model": model,
        "ready": provider != "none",
    }


dist_dir = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if dist_dir.exists():
    from starlette.responses import FileResponse, Response

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        candidate = dist_dir / full_path
        if full_path and candidate.is_file():
            return FileResponse(candidate)
        index_file = dist_dir / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return Response(status_code=404)