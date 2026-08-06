"""Perhitungan efisiensi & efektivitas (TRD Bab 9.2/9.3, OI-18/OI-19)."""
from __future__ import annotations

from typing import Optional

WAKTU_IDEAL_DETIK = 5.0  # OI-19: batas atas dipakai sebagai nilai tunggal


def hitung_efisiensi(durasi_ms: float, waktu_ideal_detik: float = WAKTU_IDEAL_DETIK) -> float:
    """Efisiensi = min(waktu_ideal / waktu_aktual, 1) x 100% (di-cap 100%, OI-19)."""
    aktual = max(durasi_ms / 1000.0, 1e-6)
    return round(min(waktu_ideal_detik / aktual, 1.0) * 100.0, 2)


def persen_di_bawah_ambang(
    durations_ms: list[Optional[int]], ambang_detik: float = WAKTU_IDEAL_DETIK
) -> Optional[float]:
    """Persentase permintaan dengan durasi <= ambang (metrik alternatif OI-19)."""
    valid = [d for d in durations_ms if d is not None]
    if not valid:
        return None
    n = sum(1 for d in valid if d / 1000.0 <= ambang_detik)
    return round(n / len(valid) * 100.0, 2)


def hitung_efektivitas(pairs: list[tuple[Optional[str], Optional[str]]]) -> Optional[float]:
    """Efektivitas = (rekomendasi tepat / total pengujian) x 100%.

    pairs: daftar (hasil_sistem, hasil_manual_petugas). Baris tanpa keduanya diabaikan.
    """
    valid = [(s, m) for s, m in pairs if s and m]
    if not valid:
        return None
    tepat = sum(1 for s, m in valid if s == m)
    return round(tepat / len(valid) * 100.0, 2)
