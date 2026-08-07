"""Loader konfigurasi Fuzzy TOPSIS (bobot, arah kriteria, ambang kategori pendapatan)."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from app.core.config import settings

_DEFAULT: dict[str, Any] = {
    "versi": "default-builtin",
    "bobot": {
        "pendapatan": 0.35,
        "jumlah_tanggungan": 0.20,
        "housing_need": 0.20,
        "skor_urgensi": 0.25,
    },
    "arah": {
        "pendapatan": "cost",
        "jumlah_tanggungan": "benefit",
        "housing_need": "benefit",
        "skor_urgensi": "benefit",
    },
    "pendapatan_kategori": {"sangat_rendah": 500000, "rendah": 1000000, "sedang": 2000000},
    # Sengaja TIDAK memuat definisi fungsi keanggotaan (OI-13) maupun aturan tiebreak: keduanya
    # hanya hidup di `config/fuzzy_config.yaml` supaya ada satu sumber. Bila berkas itu hilang,
    # Tier 3 turun ke TOPSIS crisp bertanda `topsis-crisp-fallback-v0` — terlihat jelas di
    # `bobot_snapshot`, bukan diam-diam memakai definisi bayangan yang berbeda dari berkas.
    "keanggotaan": {},
    "tiebreak": [],
}


@lru_cache
def load_fuzzy_config() -> dict[str, Any]:
    path = Path(settings.fuzzy_config_path)
    if not path.exists():
        return _DEFAULT
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    # Gabung dangkal dengan default agar kunci yang hilang tetap ada.
    merged = {**_DEFAULT, **data}
    for key in ("bobot", "arah", "pendapatan_kategori"):
        merged[key] = {**_DEFAULT[key], **(data.get(key) or {})}
    return merged


def reset_fuzzy_config() -> None:
    """Lupakan konfigurasi yang sudah di-cache (dipakai tes / setelah berkas diubah)."""
    load_fuzzy_config.cache_clear()
