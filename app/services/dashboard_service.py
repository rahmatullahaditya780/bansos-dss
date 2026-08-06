"""Agregasi statistik dashboard + metrik efisiensi/efektivitas (dipakai API & web)."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import models
from app.schemas.hasil import DashboardRingkasan
from app.services import metrics


def _count(db: Session, stmt) -> int:
    return db.execute(stmt).scalar_one()


def ringkasan(db: Session) -> DashboardRingkasan:
    P = models.Pengajuan
    M = models.PrediksiML
    S = models.StatusPengajuan
    H = models.HasilKelayakan

    total = _count(db, select(func.count()).select_from(P))
    baru = _count(db, select(func.count()).select_from(P).where(P.status == S.BARU))
    dianalisis = _count(db, select(func.count()).select_from(P).where(P.status == S.DIANALISIS))
    diverifikasi = _count(db, select(func.count()).select_from(P).where(P.status == S.DIVERIFIKASI))
    layak = _count(db, select(func.count()).select_from(M).where(M.hasil == H.LAYAK))
    tidak_layak = _count(db, select(func.count()).select_from(M).where(M.hasil == H.TIDAK_LAYAK))

    logs = db.execute(select(models.LogPengujian)).scalars().all()
    durasi = [log.durasi_ms for log in logs if log.durasi_ms is not None]
    rata = round(sum(durasi) / len(durasi), 2) if durasi else None

    return DashboardRingkasan(
        total_pengajuan=total,
        baru=baru,
        dianalisis=dianalisis,
        diverifikasi=diverifikasi,
        layak=layak,
        tidak_layak=tidak_layak,
        rata_durasi_ms=rata,
        persen_le_5s=metrics.persen_di_bawah_ambang([log.durasi_ms for log in logs]),
        efektivitas_persen=metrics.hitung_efektivitas(
            [(log.hasil_sistem, log.hasil_manual_petugas) for log in logs]
        ),
    )
