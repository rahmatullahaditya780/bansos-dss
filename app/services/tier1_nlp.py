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

Fase 4 menambahkan `margin` (logit kelas 'tinggi' dikurangi logit kelas 'rendah') di samping
`skor`. Keduanya membawa informasi yang sama secara matematis, tetapi **hanya margin yang punya
resolusi yang dapat dipakai untuk merangking**: pada model yang memisahkan kelas dengan sangat
baik, softmax menjenuh sehingga 991 alternatif hanya menghasilkan 5 nilai probabilitas berbeda
(evaluasi pra-Fase 4 §5.1). `skor` tetap menjadi keluaran resmi Tier 1 (FR-16, disimpan ke basis
data); `margin` dipakai Tier 3 sebagai nilai crisp kriteria urgensi.
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
    margin: float = 0.0  # logit('tinggi') - logit('rendah'); dipakai Tier 3, lihat catatan di bawah


def _ke_output(hasil) -> Tier1Output:
    return Tier1Output(skor=hasil.skor, versi_model=hasil.versi_model, margin=hasil.margin_efektif)


def score_urgency(text: str) -> Tier1Output:
    """Kembalikan skor urgensi 0..1 untuk satu teks naratif."""
    return _ke_output(get_scorer().score(text))


def score_urgency_batch(texts: list[str]) -> list[Tier1Output]:
    """Versi batch (satu forward pass) — lebih cepat untuk pengajuan bernarasi banyak."""
    return [_ke_output(h) for h in get_scorer().score_batch(texts)]


def info_model() -> dict[str, object]:
    """Status model Tier 1 (path artefak, versi, apakah fallback aktif)."""
    return get_scorer().info()


# Nilai lama dipertahankan sebagai referensi versi fallback (dipakai di tes & dokumentasi).
VERSI_MODEL_FALLBACK = VERSI_FALLBACK
