"""Entry point FastAPI: menyatukan router API + dashboard web + static."""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import analisis, auth, hasil, pengajuan, web
from app.core.config import settings

logger = logging.getLogger(__name__)


def panaskan_model() -> dict[str, float]:
    """Muat artefak Tier 1 & Tier 2 sebelum permintaan pertama masuk (Fase 5, D-02).

    Tanpa ini, petugas pertama setelah setiap restart menunggu ~14 detik (13.998 ms terukur)
    sementara permintaan berikutnya ~200 ms — dan angka itu masuk laporan NFR-01 sebagai
    kegagalan, padahal ia biaya pemuatan model (evaluasi pra-Fase 5 §5.3).

    Kegagalan pemanasan sengaja tidak menjatuhkan aplikasi: jalur fallback bertanda versi sudah
    ada di kedua tier, dan menolak start hanya akan menyembunyikannya.
    """
    durasi: dict[str, float] = {}
    from app.services import tier1_nlp, tier2_ml  # impor lokal: berat, hanya saat startup

    for nama, info in (("tier1", tier1_nlp.info_model), ("tier2", tier2_ml.info_model)):
        t0 = time.perf_counter()
        try:
            status = info()  # info() memaksa pemuatan — itulah yang diinginkan di sini
            durasi[nama] = (time.perf_counter() - t0) * 1000
            logger.info(
                "Pemanasan %s: %s (%.0f ms, fallback=%s)",
                nama, status.get("versi_model"), durasi[nama], status.get("fallback_aktif"),
            )
        except Exception as exc:  # noqa: BLE001
            durasi[nama] = (time.perf_counter() - t0) * 1000
            logger.warning("Pemanasan %s gagal: %s", nama, exc)
    return durasi


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.panaskan_model_saat_start:
        panaskan_model()
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.5.0-fase5",
    description="DSS penentuan kelayakan & prioritas penerima bansos (pipeline 3-tier): "
    "Tier 1 IndoBERT, Tier 2 klasifikasi ML, Tier 3 Fuzzy TOPSIS (Chen 2000).",
    lifespan=lifespan,
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
