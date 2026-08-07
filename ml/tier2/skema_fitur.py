"""Perakitan vektor fitur Tier 2 — **satu sumber** untuk jalur latih dan jalur inference.

Modul ini sengaja dipisah dari `app/services/features.py`: yang di sana menghitung *nilai* fitur
dari data survei (termasuk `housing_need`), yang di sini mengunci *urutan dan kelengkapannya*
menjadi vektor numerik. Keduanya dipakai oleh kedua jalur, sehingga train/serve skew tidak mungkin
terjadi — pelajaran yang sama dengan `ml/tier1/preprocessing.py`.

Urutan fitur ikut disimpan ke `metadata.json` artefak dan diperiksa ulang saat pemuatan
(`infer.periksa_skema`), sehingga perubahan pada `FITUR` tidak dapat lolos diam-diam.
"""
from __future__ import annotations

from ml.tier2 import FITUR


class SkemaFiturError(ValueError):
    """Vektor fitur tidak dapat dirakit atau tidak cocok dengan artefak."""


def vektor(features: dict[str, float]) -> list[float]:
    """Ubah dict fitur (keluaran `build_features`) menjadi vektor terurut `FITUR`."""
    kurang = [f for f in FITUR if f not in features]
    if kurang:
        raise SkemaFiturError(
            f"fitur wajib tidak ada: {kurang}. Vektor Tier 2 menuntut {FITUR}"
        )
    nilai: list[float] = []
    for f in FITUR:
        try:
            nilai.append(float(features[f]))
        except (TypeError, ValueError) as exc:
            raise SkemaFiturError(f"fitur {f!r} bukan angka: {features[f]!r}") from exc
    return nilai


def matriks(daftar_features: list[dict[str, float]]) -> list[list[float]]:
    """Rakit banyak vektor sekaligus (urutan baris dipertahankan)."""
    return [vektor(f) for f in daftar_features]


def periksa_skema(fitur_artefak: list[str]) -> None:
    """Pastikan artefak dilatih dengan urutan fitur yang sama seperti kode saat ini.

    Model scikit-learn menerima array polos tanpa nama kolom, sehingga urutan yang bergeser
    tidak menimbulkan galat apa pun — hanya prediksi yang salah secara senyap. Pemeriksaan ini
    mengubah kegagalan senyap itu menjadi kegagalan yang berisik.
    """
    if list(fitur_artefak) != FITUR:
        raise SkemaFiturError(
            "urutan/isi fitur artefak berbeda dengan kode.\n"
            f"  artefak: {list(fitur_artefak)}\n"
            f"  kode   : {FITUR}\n"
            "Latih ulang Tier 2 atau kembalikan `ml.tier2.FITUR` ke urutan semula."
        )
