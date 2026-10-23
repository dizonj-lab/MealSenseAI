import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app import models  # noqa: F401  (register tables)
from app.api import ai, auth, dashboard, meals, users
from app.core import cache
from app.core.config import settings
from app.core.db import Base, engine
from app.services import slm, vision

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_app):
    Base.metadata.create_all(engine)
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    vision.status()  # warm models
    yield
    vision.close()


app = FastAPI(lifespan=lifespan, title="MealSenseAI API", version="0.1.0",
              description="Meal capture, food recognition, nutrition estimation and educational insights.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

api = APIRouter(prefix="/api/v1")
for r in (auth.router, users.router, meals.router, dashboard.router, ai.router):
    api.include_router(r)


@api.get("/health", tags=["system"])
def health():
    try:
        with engine.connect() as c:
            c.execute(text("select 1"))
        db_ok = True
    except Exception:
        db_ok = False
    v, s = vision.status(), slm.status()
    return {"status": "ok" if db_ok else "degraded", "database": db_ok, "redis": cache.ping(),
            "vision": v["available"], "slm": s["available"], "slm_model": s["selected"]}


app.include_router(api)


dist = settings.frontend_dist
if dist.exists():
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = dist / path
        return FileResponse(f if path and f.is_file() else dist / "index.html")
