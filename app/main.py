"""Entry point FastAPI: menyatukan router API + dashboard web + static."""
from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import analisis, auth, hasil, pengajuan, web
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0-fase0",
    description="DSS penentuan kelayakan & prioritas penerima bansos (pipeline 3-tier). "
    "Fase 0: kerangka integrasi tipis dengan tier stub.",
)

_static_dir = Path("app/static")
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

# Router API (JSON, terdokumentasi di /docs)
app.include_router(auth.router)
app.include_router(pengajuan.router)
app.include_router(analisis.router)
app.include_router(hasil.router)
# Router web (HTML, tidak masuk skema OpenAPI)
app.include_router(web.router)


@app.get("/health", include_in_schema=False)
def health() -> dict:
    return {"status": "ok", "app": settings.app_name, "env": settings.app_env}
