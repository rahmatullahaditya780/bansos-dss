"""Ekstraksi fitur dari data survei untuk dipakai Tier 2 (ML) & Tier 3 (TOPSIS).

Nilai kategorikal kondisi rumah dipetakan ke skor "kebutuhan" 0..1 (1 = paling buruk/butuh).
Pemetaan ini provisional dan akan diselaraskan dengan fungsi keanggotaan fuzzy pada Fase 4.
"""
from __future__ import annotations

from typing import Optional

# Peta kondisi rumah → skor kebutuhan (1.0 = paling tidak layak huni).
_LANTAI = {"tanah": 1.0, "kayu": 0.6, "papan": 0.6, "semen": 0.3, "plester": 0.3, "keramik": 0.0, "ubin": 0.1}
_DINDING = {"bambu": 1.0, "anyaman": 1.0, "kayu": 0.6, "papan": 0.6, "seng": 0.5, "tembok": 0.0, "batu bata": 0.1}
_AIR = {"sungai": 1.0, "hujan": 0.9, "mata air": 0.6, "sumur": 0.5, "sumur bor": 0.4, "pdam": 0.0, "ledeng": 0.0}


def _lookup(mapping: dict[str, float], value: Optional[str], default: float = 0.5) -> float:
    if not value:
        return default
    return mapping.get(value.strip().lower(), default)


def housing_need_score(
    jenis_lantai: Optional[str],
    jenis_dinding: Optional[str],
    sumber_air: Optional[str],
    luas_rumah: Optional[float],
    jumlah_tanggungan: int,
) -> float:
    """Skor kebutuhan kondisi rumah 0..1 (semakin tinggi = kondisi semakin buruk)."""
    lantai = _lookup(_LANTAI, jenis_lantai)
    dinding = _lookup(_DINDING, jenis_dinding)
    air = _lookup(_AIR, sumber_air)

    # Kepadatan: luas per orang < 8 m2 dianggap tidak layak (Kemenkes ~7.2 m2/orang).
    if luas_rumah and luas_rumah > 0:
        penghuni = max(1, jumlah_tanggungan + 1)
        per_kapita = luas_rumah / penghuni
        kepadatan = 1.0 if per_kapita < 8 else max(0.0, 1.0 - (per_kapita - 8) / 12)
    else:
        kepadatan = 0.5

    return round((lantai + dinding + air + kepadatan) / 4.0, 4)


def build_features(
    *,
    pendapatan: float,
    jumlah_tanggungan: int,
    usia: int,
    aset_produktif: bool,
    riwayat_bantuan: bool,
    jenis_lantai: Optional[str],
    jenis_dinding: Optional[str],
    sumber_air: Optional[str],
    luas_rumah: Optional[float],
    skor_urgensi: float,
) -> dict[str, float]:
    """Rakit vektor fitur numerik untuk Tier 2 & kriteria Tier 3."""
    return {
        "pendapatan": float(pendapatan),
        "jumlah_tanggungan": float(jumlah_tanggungan),
        "usia": float(usia),
        "aset_produktif": 1.0 if aset_produktif else 0.0,
        "riwayat_bantuan": 1.0 if riwayat_bantuan else 0.0,
        "housing_need": housing_need_score(
            jenis_lantai, jenis_dinding, sumber_air, luas_rumah, jumlah_tanggungan
        ),
        "skor_urgensi": float(skor_urgensi),
    }
