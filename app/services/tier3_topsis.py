"""Tier 3 — Perangkingan prioritas.

STUB Fase 0: TOPSIS *crisp* murni-Python (tanpa scikit-fuzzy) sebagai pengganti sementara.
Pada Fase 4 DIGANTI oleh Fuzzy TOPSIS penuh (fuzzifikasi + bilangan fuzzy segitiga/trapesium via
scikit-fuzzy). Kontrak (daftar alternatif + bobot/arah → nilai preferensi + peringkat) dipertahankan.
"""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class RankingEntry:
    pengajuan_id: int
    nilai_preferensi: float
    peringkat: int


def rank_topsis(
    alternatives: list[dict],
    bobot: dict[str, float],
    arah: dict[str, str],
) -> list[RankingEntry]:
    """Rangking alternatif dengan TOPSIS.

    alternatives: list dict berisi 'pengajuan_id' + nilai tiap kriteria (kunci = kunci di `bobot`).
    """
    if not alternatives:
        return []

    kriteria = list(bobot.keys())

    # Kasus satu alternatif: langsung peringkat 1.
    if len(alternatives) == 1:
        return [RankingEntry(pengajuan_id=alternatives[0]["pengajuan_id"], nilai_preferensi=1.0, peringkat=1)]

    # 1) Matriks & normalisasi vektor per kolom.
    denom: dict[str, float] = {}
    for k in kriteria:
        ss = math.sqrt(sum((a.get(k, 0.0) or 0.0) ** 2 for a in alternatives))
        denom[k] = ss if ss > 1e-12 else 1e-12

    # 2) Matriks ternormalisasi berbobot.
    weighted: list[dict[str, float]] = []
    for a in alternatives:
        weighted.append({k: bobot[k] * ((a.get(k, 0.0) or 0.0) / denom[k]) for k in kriteria})

    # 3) Solusi ideal positif (A+) & negatif (A-) sesuai arah kriteria.
    a_plus: dict[str, float] = {}
    a_minus: dict[str, float] = {}
    for k in kriteria:
        col = [w[k] for w in weighted]
        is_benefit = arah.get(k, "benefit") == "benefit"
        a_plus[k] = max(col) if is_benefit else min(col)
        a_minus[k] = min(col) if is_benefit else max(col)

    # 4) Jarak ke A+ / A- dan nilai preferensi (closeness coefficient).
    hasil: list[RankingEntry] = []
    for a, w in zip(alternatives, weighted):
        s_plus = math.sqrt(sum((w[k] - a_plus[k]) ** 2 for k in kriteria))
        s_minus = math.sqrt(sum((w[k] - a_minus[k]) ** 2 for k in kriteria))
        total = s_plus + s_minus
        c = (s_minus / total) if total > 1e-12 else 0.0
        hasil.append(RankingEntry(pengajuan_id=a["pengajuan_id"], nilai_preferensi=round(c, 4), peringkat=0))

    # 5) Urutkan menurun & tetapkan peringkat.
    hasil.sort(key=lambda e: e.nilai_preferensi, reverse=True)
    for i, e in enumerate(hasil, start=1):
        e.peringkat = i
    return hasil
