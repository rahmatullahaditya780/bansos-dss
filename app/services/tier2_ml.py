"""Tier 2 — Klasifikasi kelayakan (layak / tidak_layak), FR-15…FR-17.

Fase 3: stub logistik Fase 0 DIGANTI oleh model terlatih (Random Forest / Gradient Boosting,
pilih terbaik — OI-01) yang dimuat dari artefak `ml/artifacts/tier2/`. Keluaran = probabilitas
kelas 'layak' (0..1) + label pada ambang 0,5, disimpan ke `prediksi_ml` bersama `versi_model`.

Kontrak fungsi dipertahankan agar `app/services/pipeline.py` tidak berubah:
    predict_eligibility(features) -> Tier2Output(hasil, probabilitas, versi_model)

Bila artefak belum tersedia (mis. baru clone repo — artefak tidak di-commit), modul turun ke skor
logistik cadangan dan menandai `versi_model` = 'stub-logistik-fallback-v0', sehingga hasil
non-model selalu dapat dipisahkan saat analisis.
"""
from __future__ import annotations

from dataclasses import dataclass

from ml.tier2.infer import VERSI_FALLBACK, get_classifier

__all__ = [
    "Tier2Output",
    "predict_eligibility",
    "predict_eligibility_batch",
    "info_model",
    "VERSI_MODEL_FALLBACK",
]


@dataclass
class Tier2Output:
    hasil: str           # 'layak' | 'tidak_layak'
    probabilitas: float  # 0..1, probabilitas kelas 'layak'
    versi_model: str


def predict_eligibility(features: dict[str, float]) -> Tier2Output:
    """Prediksi kelayakan dari vektor fitur (lihat `app/services/features.build_features`)."""
    hasil = get_classifier().predict(features)
    return Tier2Output(
        hasil=hasil.hasil, probabilitas=hasil.probabilitas, versi_model=hasil.versi_model
    )


def predict_eligibility_batch(daftar_features: list[dict[str, float]]) -> list[Tier2Output]:
    """Versi batch — dipakai saat menganalisis banyak pengajuan sekaligus."""
    return [
        Tier2Output(hasil=h.hasil, probabilitas=h.probabilitas, versi_model=h.versi_model)
        for h in get_classifier().predict_batch(daftar_features)
    ]


def info_model() -> dict[str, object]:
    """Status model Tier 2 (path artefak, algoritma, asal data, apakah fallback aktif)."""
    return get_classifier().info()


# Versi cadangan dipertahankan sebagai rujukan di tes & dokumentasi.
VERSI_MODEL_FALLBACK = VERSI_FALLBACK
