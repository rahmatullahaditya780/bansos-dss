"""Generator alasan/penjelasan keputusan berbasis aturan (OI-07 — TANPA LLM).

Menyusun kalimat penjelasan dari kategori fitur & skor tiap tier agar setiap hasil dapat
ditinjau petugas (T-04, FR-23). Tidak mengirim data ke layanan eksternal mana pun.
"""
from __future__ import annotations

from app.services.fuzzy_config import load_fuzzy_config


def kategori_pendapatan(pendapatan: float) -> str:
    amb = load_fuzzy_config()["pendapatan_kategori"]
    if pendapatan <= amb["sangat_rendah"]:
        return "sangat rendah"
    if pendapatan <= amb["rendah"]:
        return "rendah"
    if pendapatan <= amb["sedang"]:
        return "sedang"
    return "tinggi"


def kategori_urgensi(skor: float) -> str:
    return "tinggi" if skor >= 0.5 else "rendah"


def kategori_rumah(housing_need: float) -> str:
    if housing_need >= 0.66:
        return "buruk"
    if housing_need >= 0.33:
        return "cukup"
    return "baik"


def build_reason(
    features: dict[str, float],
    skor_urgensi: float,
    prediksi_hasil: str,
    probabilitas: float,
) -> str:
    """Rangkai kalimat penjelasan dari fitur & hasil prediksi."""
    tanggungan = int(features.get("jumlah_tanggungan", 0))
    frasa = [
        f"Pendapatan per kapita kategori {kategori_pendapatan(features.get('pendapatan', 0.0))}",
        f"{tanggungan} tanggungan",
        f"kondisi rumah {kategori_rumah(features.get('housing_need', 0.5))}",
        f"narasi menunjukkan urgensi {kategori_urgensi(skor_urgensi)}",
    ]
    if features.get("aset_produktif", 0.0) >= 1.0:
        frasa.append("memiliki aset produktif")
    if features.get("riwayat_bantuan", 0.0) >= 1.0:
        frasa.append("pernah menerima bantuan")

    label = "LAYAK" if prediksi_hasil == "layak" else "TIDAK LAYAK"
    return "; ".join(frasa) + f". Model memprediksi {label} (probabilitas {probabilitas:.2f})."
