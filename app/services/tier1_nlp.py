"""Tier 1 — Skor urgensi dari teks naratif (FR-11…FR-14).

Fase 2: stub heuristik Fase 0 DIGANTI oleh inference IndoBERT hasil fine-tuning
(`ml.tier1.infer`). Keluaran = probabilitas kelas 'tinggi' (0..1), disimpan ke `skor_urgensi`
bersama `versi_model`.

Kontrak fungsi dipertahankan agar `app/services/pipeline.py` tidak berubah:
    preprocess(text) -> str
    score_urgency(text) -> Tier1Output(skor: float, versi_model: str)

Bila artefak model belum tersedia (mis. baru clone repo, artefak tidak di-commit — lihat
`.gitignore`), modul turun ke heuristik cadangan dan menandai `versi_model` =
'heuristik-fallback-v0' sehingga hasil non-model selalu dapat dibedakan di basis data.
"""
from __future__ import annotations

from dataclasses import dataclass

from ml.tier1.infer import VERSI_FALLBACK, get_scorer
from ml.tier1.preprocessing import preprocess  # FR-11 — re-ekspor, sumber tunggal

__all__ = ["Tier1Output", "preprocess", "score_urgency", "score_urgency_batch", "info_model"]


@dataclass
class Tier1Output:
    skor: float  # 0..1, probabilitas kelas 'tinggi'
    versi_model: str


def score_urgency(text: str) -> Tier1Output:
    """Kembalikan skor urgensi 0..1 untuk satu teks naratif."""
    hasil = get_scorer().score(text)
    return Tier1Output(skor=hasil.skor, versi_model=hasil.versi_model)


def score_urgency_batch(texts: list[str]) -> list[Tier1Output]:
    """Versi batch (satu forward pass) — lebih cepat untuk pengajuan bernarasi banyak."""
    return [Tier1Output(skor=h.skor, versi_model=h.versi_model) for h in get_scorer().score_batch(texts)]


def info_model() -> dict[str, object]:
    """Status model Tier 1 (path artefak, versi, apakah fallback aktif)."""
    return get_scorer().info()


# Nilai lama dipertahankan sebagai referensi versi fallback (dipakai di tes & dokumentasi).
VERSI_MODEL_FALLBACK = VERSI_FALLBACK
