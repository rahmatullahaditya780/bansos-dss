"""Agregasi statistik dashboard + metrik efisiensi/efektivitas (dipakai API & web).

Sampai Fase 4 fungsi `ringkasan()` memuat SELURUH baris `log_pengujian` sebagai objek ORM setiap
kali dipanggil — dan dashboard memanggilnya tiap 5 detik. Pada 305 baris biayanya 9,3 ms; pada
10.000 baris ~306 ms per polling per petugas (evaluasi pra-Fase 5 §5.5). Sejak Fase 5 hanya kolom
yang dibutuhkan yang diambil, dan pencacahan dikerjakan basis data.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import models
from app.schemas.hasil import DashboardRingkasan
from app.services import metrics, tier1_nlp, tier2_ml, tier3_topsis, verifikasi


def _count(db: Session, stmt) -> int:
    return db.execute(stmt).scalar_one()


def _baris_log(db: Session):
    """Kolom durasi saja — bukan objek ORM utuh (lihat catatan modul)."""
    return db.execute(
        select(
            models.LogPengujian.durasi_ms,
            models.LogPengujian.durasi_tier1_ms,
            models.LogPengujian.durasi_tier2_ms,
            models.LogPengujian.jenis_muat,
        )
    ).all()


def _batch_tier3(db: Session):
    return db.execute(
        select(models.LogRanking.durasi_ms, models.LogRanking.jumlah_alternatif)
    ).all()


def efisiensi(db: Session) -> metrics.RingkasanEfisiensi:
    return metrics.ringkas_efisiensi(_baris_log(db), _batch_tier3(db))


def efektivitas(db: Session) -> metrics.RingkasanEfektivitas:
    return metrics.ringkas_efektivitas(verifikasi.pasangan_efektivitas(db))


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

    eff = efisiensi(db)
    efek = efektivitas(db)
    rata = db.execute(
        select(func.avg(models.LogPengujian.durasi_ms)).where(
            models.LogPengujian.jenis_muat == "warm"
        )
    ).scalar_one_or_none()

    return DashboardRingkasan(
        total_pengajuan=total,
        baru=baru,
        dianalisis=dianalisis,
        diverifikasi=diverifikasi,
        layak=layak,
        tidak_layak=tidak_layak,
        rata_durasi_ms=round(rata, 2) if rata is not None else None,
        persen_le_5s=eff.persen_le_5s,
        efisiensi_persen=eff.efisiensi_persen,
        p50_durasi_ms=eff.p50_ms,
        permintaan_cold=eff.n_cold,
        efektivitas_persen=efek.persen,
        pasangan_verifikasi=efek.pasangan,
    )


# --------------------------------------------------------------------------------------
# Status pemasangan model (D-05) — supaya penanda versi terlihat di layar, bukan hanya
# di baris perintah. Tiga kegagalan senyap proyek ini semuanya hanya tersingkap olehnya.
# --------------------------------------------------------------------------------------
@dataclass
class StatusTier:
    nama: str
    versi: str
    fallback: bool
    keterangan: Optional[str] = None


def status_model() -> list[StatusTier]:
    """Versi & status fallback ketiga tier. Aman dipanggil dari template."""
    hasil: list[StatusTier] = []
    try:
        t1 = tier1_nlp.info_model()
        hasil.append(
            StatusTier("Tier 1 · IndoBERT", str(t1.get("versi_model")), bool(t1.get("fallback_aktif")),
                       str(t1.get("alasan_fallback") or ""))
        )
    except Exception as exc:  # noqa: BLE001 — status tidak boleh menjatuhkan halaman
        hasil.append(StatusTier("Tier 1 · IndoBERT", "?", True, str(exc)))
    try:
        t2 = tier2_ml.info_model()
        hasil.append(
            StatusTier("Tier 2 · Klasifikasi", str(t2.get("versi_model")), bool(t2.get("fallback_aktif")),
                       str(t2.get("alasan_fallback") or ""))
        )
    except Exception as exc:  # noqa: BLE001
        hasil.append(StatusTier("Tier 2 · Klasifikasi", "?", True, str(exc)))
    try:
        t3 = tier3_topsis.info_fuzzy()
        hasil.append(
            StatusTier(
                "Tier 3 · Fuzzy TOPSIS",
                f"{t3.get('versi_metode')} · cfg {t3.get('versi_konfigurasi')}",
                bool(t3.get("fallback_aktif")),
                str(t3.get("alasan_fallback") or ""),
            )
        )
    except Exception as exc:  # noqa: BLE001
        hasil.append(StatusTier("Tier 3 · Fuzzy TOPSIS", "?", True, str(exc)))
    return hasil


def ada_fallback_aktif() -> bool:
    return any(s.fallback for s in status_model())
