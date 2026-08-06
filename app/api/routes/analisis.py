"""Endpoint menjalankan pipeline analisis (TRD Bab 8)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import require_petugas
from app.db import models
from app.db.session import get_db
from app.schemas.hasil import AnalisisResult, RankingResult
from app.services import pipeline

router = APIRouter(prefix="/analisis", tags=["analisis"])


# Catatan: rute statis '/ranking' HARUS didaftarkan sebelum '/{pengajuan_id}'
# agar tidak tertangkap sebagai id (yang menyebabkan 422).
@router.post("/ranking", response_model=RankingResult)
def analisis_ranking(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_petugas),
) -> dict:
    """Jalankan Fuzzy TOPSIS (Tier 3) untuk seluruh pengajuan yang lolos ML (FR-21, OI-15)."""
    return pipeline.jalankan_ranking(db)


@router.post("/{pengajuan_id}", response_model=AnalisisResult)
def analisis_satu(
    pengajuan_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_petugas),
) -> dict:
    """Jalankan Tier 1 -> Tier 2 untuk satu pengajuan (FR-15, FR-25)."""
    p = db.get(models.Pengajuan, pengajuan_id)
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pengajuan tidak ditemukan")
    if p.data_survei is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Data survei belum lengkap"
        )
    return pipeline.analisis_pengajuan(db, p)
