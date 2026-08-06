"""Tier 2 — Klasifikasi kelayakan (layak / tidak_layak).

STUB Fase 0: skor logistik sederhana dari fitur, deterministik. Pada Fase 3 DIGANTI oleh
model terlatih (Random Forest / Gradient Boosting, pilih terbaik — OI-01) yang dimuat dari artefak.
Kontrak fungsi (input fitur → hasil, probabilitas, versi) dipertahankan.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from app.db.models import HasilKelayakan

VERSI_MODEL = "stub-classifier-v0"


@dataclass
class Tier2Output:
    hasil: str
    probabilitas: float
    versi_model: str


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def predict_eligibility(features: dict[str, float]) -> Tier2Output:
    """Prediksi kelayakan dari vektor fitur (lihat features.build_features)."""
    pendapatan = features.get("pendapatan", 0.0)
    tanggungan = features.get("jumlah_tanggungan", 0.0)
    housing = features.get("housing_need", 0.5)
    urgensi = features.get("skor_urgensi", 0.0)
    aset = features.get("aset_produktif", 0.0)
    riwayat = features.get("riwayat_bantuan", 0.0)

    # Skor kebutuhan (semakin tinggi → makin layak). Pendapatan dinormalisasi ke jutaan.
    z = (
        1.4
        - 1.1 * (pendapatan / 1_000_000.0)
        + 0.35 * tanggungan
        + 1.5 * housing
        + 1.2 * urgensi
        - 0.8 * aset
        - 0.3 * riwayat
    )
    prob = _sigmoid(z)
    hasil = HasilKelayakan.LAYAK if prob >= 0.5 else HasilKelayakan.TIDAK_LAYAK
    return Tier2Output(hasil=hasil, probabilitas=round(prob, 4), versi_model=VERSI_MODEL)
