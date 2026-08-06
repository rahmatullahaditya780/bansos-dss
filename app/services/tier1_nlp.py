"""Tier 1 — Skor urgensi dari teks naratif.

STUB Fase 0: heuristik berbasis kata kunci, deterministik, agar pipeline dapat berjalan
end-to-end sebelum model asli tersedia. Pada Fase 2 modul ini DIGANTI oleh inference IndoBERT
hasil fine-tuning; keluaran = probabilitas kelas 'tinggi' (0..1). Kontrak fungsi dipertahankan.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

VERSI_MODEL = "stub-indobert-v0"

# Kata kunci indikatif urgensi tinggi (bobot kasar). Hanya untuk stub.
_KATA_URGEN = {
    "meninggal": 3, "sakit": 2, "kronis": 3, "cacat": 3, "disabilitas": 3,
    "darurat": 3, "kelaparan": 3, "tidak mampu": 2, "menganggur": 2, "phk": 2,
    "hutang": 1, "terlilit": 2, "yatim": 2, "piatu": 2, "lansia": 2, "jompo": 2,
    "bocor": 1, "gubuk": 2, "roboh": 3, "menumpang": 2, "putus sekolah": 2,
    "bayi": 1, "balita": 1, "hamil": 1, "stunting": 2,
}


def preprocess(text: str) -> str:
    """Pembersihan dasar (FR-11): lowercasing, hapus karakter non-informatif, rapikan spasi.

    Pada Fase 2 ditambah tokenisasi bawaan IndoBERT.
    """
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s.,!?]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


@dataclass
class Tier1Output:
    skor: float  # 0..1, probabilitas kelas 'tinggi'
    versi_model: str


def score_urgency(text: str) -> Tier1Output:
    """Kembalikan skor urgensi 0..1 untuk satu teks naratif."""
    clean = preprocess(text)
    bobot = sum(w for kata, w in _KATA_URGEN.items() if kata in clean)
    # Normalisasi kasar ke 0..1 (jenuh di sekitar bobot 8).
    skor = min(1.0, bobot / 8.0)
    # Sedikit pengaruh panjang narasi (narasi sangat pendek cenderung kurang informatif).
    if len(clean) < 40:
        skor *= 0.7
    return Tier1Output(skor=round(skor, 4), versi_model=VERSI_MODEL)
