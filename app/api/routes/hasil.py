"""Endpoint hasil, ranking, ringkasan dashboard, dan verifikasi manual (TRD Bab 8)."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_petugas
from app.db import models
from app.db.session import get_db
from app.schemas.hasil import (
    DashboardRingkasan,
    HasilResponse,
    RankingItem,
    VerifikasiIn,
)
from app.services import dashboard_service, pipeline

router = APIRouter(tags=["hasil"])


@router.get("/hasil/{pengajuan_id}", response_model=HasilResponse)
def hasil(
    pengajuan_id: int,
    db: Session = Depends(get_db),
    user: models.User = Depends(get_current_user),
) -> dict:
    p = db.get(models.Pengajuan, pengajuan_id)
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pengajuan tidak ditemukan")
    if user.role != models.Role.PETUGAS:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akses ditolak")
    return pipeline.susun_hasil(p)


@router.get("/ranking", response_model=list[RankingItem])
def ranking_terakhir(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_petugas),
) -> list[RankingItem]:
    latest_batch = db.execute(
        select(models.RankingTopsis.batch_id).order_by(models.RankingTopsis.created_at.desc()).limit(1)
    ).scalar_one_or_none()
    if latest_batch is None:
        return []
    rows = db.execute(
        select(models.RankingTopsis)
        .where(models.RankingTopsis.batch_id == latest_batch)
        .order_by(models.RankingTopsis.peringkat)
    ).scalars().all()
    items: list[RankingItem] = []
    for r in rows:
        p = r.pengajuan
        items.append(
            RankingItem(
                peringkat=r.peringkat,
                pengajuan_id=r.pengajuan_id,
                warga_nama=p.warga.nama,
                nilai_preferensi=r.nilai_preferensi,
                prediksi=p.prediksi_ml.hasil if p.prediksi_ml else "-",
                skor_urgensi=round(pipeline._urgensi_pengajuan(p), 4),
            )
        )
    return items


@router.get("/dashboard/ringkasan", response_model=DashboardRingkasan)
def dashboard_ringkasan(
    db: Session = Depends(get_db),
    user: models.User = Depends(require_petugas),
) -> DashboardRingkasan:
    return dashboard_service.ringkasan(db)


@router.post("/verifikasi/{pengajuan_id}")
def verifikasi(
    pengajuan_id: int,
    payload: VerifikasiIn,
    db: Session = Depends(get_db),
    user: models.User = Depends(require_petugas),
) -> dict:
    """Rekam hasil verifikasi manual petugas (FR-26, bahan uji efektivitas)."""
    p = db.get(models.Pengajuan, pengajuan_id)
    if p is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pengajuan tidak ditemukan")

    if p.log_pengujian:
        latest = max(p.log_pengujian, key=lambda log: log.waktu_mulai)
        latest.hasil_manual_petugas = payload.hasil_manual
    else:
        db.add(
            models.LogPengujian(
                pengajuan_id=p.id,
                waktu_mulai=datetime.now(timezone.utc),
                hasil_manual_petugas=payload.hasil_manual,
            )
        )
    p.status = models.StatusPengajuan.DIVERIFIKASI
    db.commit()
    return {"pengajuan_id": p.id, "status": p.status, "hasil_manual": payload.hasil_manual}
