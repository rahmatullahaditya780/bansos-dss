"""Perekaman verifikasi manual petugas (FR-26) — bahan metrik efektivitas (Bab 9.3, OI-18).

Keputusan rancangan Fase 5 (D-04). Sampai Fase 4, penilaian manual ditumpangkan ke baris
`log_pengujian` **terbaru**, sementara tiap analisis membuat baris log **baru**. Dua urutan kerja
yang sepenuhnya wajar merusak pasangannya:

    analisis -> verifikasi -> analisis ulang : pasangan memakai putusan sistem LAMA
    verifikasi -> analisis                   : pasangan tidak pernah terbentuk, hilang tanpa pesan

Keduanya bukan hipotetis — 5 pengajuan sudah berlog ganda akibat analisis ulang di Fase 4
(evaluasi pra-Fase 5 §5.4).

Perbaikannya bukan menambal urutan pencarian baris, melainkan **menyimpan apa yang benar-benar
dinilai petugas**: putusan sistem, probabilitas, versi model, dan peringkat di-snapshot pada saat
verifikasi direkam. Pasangan (sistem, manual) karenanya hidup di satu baris yang tidak dapat
dibatalkan oleh analisis berikutnya, dan `versi_model` membuat setiap pasangan dapat ditelusuri ke
model yang benar-benar menghasilkannya.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models

__all__ = ["SnapshotSistem", "rekam_verifikasi", "verifikasi_terakhir", "pasangan_efektivitas"]


@dataclass(frozen=True)
class SnapshotSistem:
    """Putusan sistem yang dilihat petugas saat menilai."""

    hasil: Optional[str] = None
    probabilitas: Optional[float] = None
    versi_model: Optional[str] = None
    peringkat: Optional[int] = None


def snapshot_sistem(pengajuan: models.Pengajuan) -> SnapshotSistem:
    """Baca putusan sistem yang sedang tampil untuk sebuah pengajuan."""
    pred = pengajuan.prediksi_ml
    peringkat = None
    if pengajuan.ranking:
        peringkat = max(pengajuan.ranking, key=lambda r: r.created_at).peringkat
    if pred is None:
        return SnapshotSistem(peringkat=peringkat)
    return SnapshotSistem(
        hasil=pred.hasil,
        probabilitas=pred.probabilitas,
        versi_model=pred.versi_model,
        peringkat=peringkat,
    )


def rekam_verifikasi(
    db: Session,
    pengajuan: models.Pengajuan,
    hasil_manual: str,
    petugas_id: Optional[int] = None,
    catatan: Optional[str] = None,
) -> models.VerifikasiManual:
    """Rekam penilaian manual + snapshot putusan sistem yang dinilai.

    Setiap verifikasi menjadi baris baru: bila petugas menilai ulang setelah analisis ulang,
    keduanya tersimpan dan riwayatnya utuh. Metrik memakai yang terbaru per pengajuan.
    """
    snap = snapshot_sistem(pengajuan)
    baris = models.VerifikasiManual(
        pengajuan_id=pengajuan.id,
        petugas_id=petugas_id,
        hasil_manual=hasil_manual,
        hasil_sistem=snap.hasil,
        probabilitas_sistem=snap.probabilitas,
        versi_model=snap.versi_model,
        peringkat_sistem=snap.peringkat,
        catatan=catatan,
    )
    db.add(baris)
    pengajuan.status = models.StatusPengajuan.DIVERIFIKASI
    db.commit()
    db.refresh(baris)
    return baris


def verifikasi_terakhir(
    db: Session, pengajuan_id: int
) -> Optional[models.VerifikasiManual]:
    """Penilaian manual terbaru untuk satu pengajuan (yang ditampilkan di halaman detail)."""
    return db.execute(
        select(models.VerifikasiManual)
        .where(models.VerifikasiManual.pengajuan_id == pengajuan_id)
        .order_by(models.VerifikasiManual.created_at.desc(), models.VerifikasiManual.id.desc())
        .limit(1)
    ).scalars().first()


def pasangan_efektivitas(db: Session) -> list[tuple[Optional[str], Optional[str]]]:
    """Pasangan (putusan sistem yang dinilai, penilaian manual) — satu per pengajuan.

    Bila sebuah pengajuan diverifikasi lebih dari sekali, hanya penilaian terbaru yang dihitung;
    kalau tidak, pengajuan yang ditinjau berulang akan punya bobot lebih besar di metrik
    ketimbang yang ditinjau sekali.
    """
    baris = db.execute(
        select(models.VerifikasiManual).order_by(
            models.VerifikasiManual.created_at.asc(), models.VerifikasiManual.id.asc()
        )
    ).scalars().all()
    terakhir: dict[int, models.VerifikasiManual] = {v.pengajuan_id: v for v in baris}
    return [(v.hasil_sistem, v.hasil_manual) for v in terakhir.values()]
