"""TOPSIS crisp — jalur cadangan Tier 3 dan pembanding untuk analisis atribusi.

Ini algoritma stub Fase 0 yang dipertahankan dengan **satu perbaikan**: nilai preferensi tidak lagi
dibulatkan sebelum diurutkan. Pembulatan 4 desimal yang dulu ada di sana adalah pembulatan untuk
tampilan yang bocor ke perhitungan — ia memproduksi seri yang tidak ada di datanya sendiri (grup
seri terbesar 14 padahal alternatif berdata persis kembar terbesar hanya 10; evaluasi pra-Fase 4
§5.6). Pembulatan sekarang dikerjakan di lapisan penyimpanan/tampilan.

Dipakai untuk dua hal:
  1. **fallback bertanda versi** bila konfigurasi keanggotaan tidak sah (lihat `VERSI_FALLBACK`);
  2. **pembanding** pada analisis atribusi — berapa bagian selisih "fuzzy vs crisp" yang sebenarnya
     berasal dari rumusan TOPSIS-nya, bukan dari kefuzzian (evaluasi pra-Fase 4 §5.3).
"""
from __future__ import annotations

import math
from typing import Mapping, Sequence


def nilai_preferensi_crisp(
    alternatif: Sequence[Mapping[str, float]],
    bobot: Mapping[str, float],
    arah: Mapping[str, str],
) -> list[float]:
    """Nilai preferensi TOPSIS crisp (normalisasi vektor, solusi ideal teramati).

    Perhatikan bedanya dari Fuzzy TOPSIS Chen: solusi ideal di sini adalah maksimum/minimum yang
    **teramati di batch**, bukan (1,1,1)/(0,0,0) mutlak. Perbedaan definisi inilah — bukan
    fuzzifikasi — yang menyumbang bagian terbesar selisih peringkat antara kedua metode.
    """
    if not alternatif:
        return []
    kriteria = list(bobot)
    if len(alternatif) == 1:
        return [1.0]

    denom: dict[str, float] = {}
    for k in kriteria:
        ss = math.sqrt(sum((a.get(k, 0.0) or 0.0) ** 2 for a in alternatif))
        denom[k] = ss if ss > 1e-12 else 1e-12

    berbobot = [
        {k: bobot[k] * ((a.get(k, 0.0) or 0.0) / denom[k]) for k in kriteria} for a in alternatif
    ]

    a_plus: dict[str, float] = {}
    a_minus: dict[str, float] = {}
    for k in kriteria:
        kolom = [w[k] for w in berbobot]
        benefit = arah.get(k, "benefit") == "benefit"
        a_plus[k] = max(kolom) if benefit else min(kolom)
        a_minus[k] = min(kolom) if benefit else max(kolom)

    hasil: list[float] = []
    for w in berbobot:
        s_plus = math.sqrt(sum((w[k] - a_plus[k]) ** 2 for k in kriteria))
        s_minus = math.sqrt(sum((w[k] - a_minus[k]) ** 2 for k in kriteria))
        total = s_plus + s_minus
        hasil.append((s_minus / total) if total > 1e-12 else 0.0)
    return hasil
