import logging
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text

from app import models  # noqa: F401  (register tables)
from app.api import ai, auth, dashboard, glucose, meals, users
from app.core import cache
from app.core.config import settings
from app.core.db import engine
from app.core.migrate import upgrade_db
from app.services import slm, vision

logging.basicConfig(level=logging.INFO)


def register_trained_model():
    """Record the active fine-tuned classifier's held-out test metrics as an Experiment (once per version)."""
    import json
    from app.core.db import SessionLocal
    from app.models import Experiment
    card_path = settings.models_dir / "exp002" / "model_card.json"
    if not card_path.exists():
        return
    card = json.loads(card_path.read_text())
    name = f"{card['version']} (reported)"
    parity = settings.models_dir / "exp002" / "evidence" / "onnx_parity.json"
    with SessionLocal() as db:
        if db.query(Experiment).filter(Experiment.name == name).first():
            return
        rep = card["metrics"]["reported_by_developer"]
        db.add(Experiment(name=name, model_name=card["name"], dataset=" + ".join(card["training_data"]) + " (developer test split)",
                          n_samples=0, has_ground_truth=True,
                          metrics={k: rep[k] for k in ("top1_accuracy", "top3_accuracy", "macro_f1")},
                          notes=rep["source"]))
        if parity.exists():
            pj = json.loads(parity.read_text())
            db.add(Experiment(name=f"{card['version']} ONNX parity", model_name=card["name"], dataset="; ".join(pj["image_sources"]),
                              n_samples=pj["images"], has_ground_truth=False,
                              metrics={k: pj[k] for k in ("preprocessing_max_abs_diff", "logits_max_abs_diff",
                                                         "top1_agreement", "top3_set_agreement")},
                              notes="Equivalence of the deployed runtime with the PyTorch checkpoint (not an accuracy measure)"))
        db.commit()


@asynccontextmanager
async def lifespan(_app):
    upgrade_db()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    vision.warmup()  # load models once at startup
    register_trained_model()
    yield
    vision.close()


app = FastAPI(lifespan=lifespan, title="MealSenseAI API", version="0.1.0",
              description="Meal capture, food recognition, nutrition estimation and educational insights.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

api = APIRouter(prefix="/api/v1")
for r in (auth.router, users.router, meals.router, dashboard.router, ai.router, glucose.router):
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
