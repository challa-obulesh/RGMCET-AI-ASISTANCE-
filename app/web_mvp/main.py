import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.web_mvp.api.appointments import router as appointments_router
from app.web_mvp.api.chat import router as chat_router
from app.web_mvp.api.professors import router as professors_router
from app.web_mvp.config import CORS_ORIGINS
from app.web_mvp.store import close_store, demo_mode_active, init_store

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    await init_store()
    yield
    await close_store()


app = FastAPI(title="RGMCET AI Campus Assistant", version="0.2.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(chat_router)
app.include_router(professors_router)
app.include_router(appointments_router)


@app.get("/api/health")
async def health():
    from app.web_mvp.llm import configured_provider
    return {
        "status": "ok",
        "demo_mode": demo_mode_active(),
        "llm_provider": configured_provider() or "none",
        "version": "0.2.0",
    }