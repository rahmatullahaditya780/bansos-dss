"""Generator alasan/penjelasan keputusan berbasis aturan (OI-07 — TANPA LLM).

Menyusun kalimat penjelasan untuk ketiga tier agar setiap hasil dapat ditinjau petugas
(T-04, FR-23). Tidak mengirim data ke layanan eksternal mana pun.

**Satu sumber label (Fase 5, D-01).** Seluruh label linguistik berasal dari
`ml.tier3.keanggotaan.KriteriaFuzzy.label()` — fungsi keanggotaan yang sama persis yang dipakai
memfuzzifikasi kriteria saat merangking. Sampai Fase 4 modul ini punya ambang kerasnya sendiri,
dan hasilnya terukur: label penjelasan tidak sepakat dengan label fuzzy pada **70,3%** pengajuan
untuk kondisi rumah, **58,0%** untuk urgensi, dan **13,3%** untuk pendapatan (evaluasi pra-Fase 5
§5.1). Petugas membaca "kondisi rumah cukup" di layar sementara peringkatnya dihitung dari `buruk`.

Konsekuensi yang disengaja: mengubah rentang keanggotaan di `config/fuzzy_config.yaml` (yang akan
terjadi di Fase 6 bersama kelurahan, OI-13) otomatis mengubah kalimat penjelasan. Itu justru
tujuannya — dua definisi untuk kata yang sama adalah cara skew yang lama kembali diam-diam.

Bila konfigurasi keanggotaan tidak sah, modul turun ke label cadangan berbasis ambang dan
menandainya lewat `sumber_label` = 'ambang-cadangan-v0', meniru pola penanda versi yang sudah tiga
kali menjadi satu-satunya hal yang menyingkap kegagalan senyap di proyek ini.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from app.services.fuzzy_config import load_fuzzy_config
from ml.tier3.keanggotaan import KonfigurasiKeanggotaanError, KriteriaFuzzy, muat_kriteria

logger = logging.getLogger(__name__)

__all__ = [
    "SUMBER_LABEL_FUZZY",
    "SUMBER_LABEL_CADANGAN",
    "Penjelasan",
    "label_kriteria",
    "labeli",
    "build_reason",
    "susun_penjelasan",
]

SUMBER_LABEL_FUZZY = "keanggotaan-fuzzy-v1"
SUMBER_LABEL_CADANGAN = "ambang-cadangan-v0"

# Kriteria yang punya fungsi keanggotaan (kunci `bobot` di konfigurasi) dan cara membacanya
# ke bahasa manusia.
_FRASA = {
    "pendapatan": "pendapatan per kapita {label}",
    "jumlah_tanggungan": "tanggungan {label}",
    "housing_need": "kondisi rumah {label}",
    "skor_urgensi": "urgensi narasi {label}",
}


def _kriteria() -> dict[str, KriteriaFuzzy]:
    cfg = load_fuzzy_config()
    try:
        return muat_kriteria(cfg, list(cfg.get("bobot") or {}))
    except KonfigurasiKeanggotaanError as exc:
        logger.warning(
            "Penjelasan: konfigurasi keanggotaan tidak sah (%s). Memakai label cadangan '%s' — "
            "label yang tampil TIDAK dijamin sepakat dengan yang dipakai merangking.",
            exc, SUMBER_LABEL_CADANGAN,
        )
        return {}


def _rapikan(label: str) -> str:
    """`sangat_buruk` -> `sangat buruk`. Ejaan saja; makna tidak disentuh."""
    return label.replace("_", " ")


# --------------------------------------------------------------------------------------
# Label cadangan — HANYA dipakai bila konfigurasi keanggotaan tidak dapat dimuat.
# --------------------------------------------------------------------------------------
def _label_cadangan(nama: str, nilai: float) -> str:
    if nama == "pendapatan":
        amb = load_fuzzy_config()["pendapatan_kategori"]
        if nilai <= amb["sangat_rendah"]:
            return "sangat rendah"
        if nilai <= amb["rendah"]:
            return "rendah"
        if nilai <= amb["sedang"]:
            return "sedang"
        return "tinggi"
    if nama == "housing_need":
        return "buruk" if nilai >= 0.66 else ("cukup" if nilai >= 0.33 else "baik")
    if nama == "skor_urgensi":
        return "tinggi" if nilai >= 0.5 else "rendah"
    if nama == "jumlah_tanggungan":
        return "banyak" if nilai >= 4 else ("sedang" if nilai >= 2 else "sedikit")
    return "-"


def label_kriteria(nama: str, nilai: float, margin: Optional[float] = None) -> str:
    """Label linguistik satu kriteria — dari fungsi keanggotaan yang dipakai merangking."""
    kf = _kriteria().get(nama)
    if kf is None:
        return _label_cadangan(nama, nilai)
    return _rapikan(kf.label(nilai, margin))


def labeli(
    features: Mapping[str, float], margin_urgensi: Optional[float] = None
) -> dict[str, str]:
    """Label seluruh kriteria sekaligus."""
    kriteria = _kriteria()
    hasil: dict[str, str] = {}
    for nama in _FRASA:
        nilai = float(features.get(nama, 0.0) or 0.0)
        kf = kriteria.get(nama)
        if kf is None:
            hasil[nama] = _label_cadangan(nama, nilai)
        else:
            hasil[nama] = _rapikan(
                kf.label(nilai, margin_urgensi if nama == "skor_urgensi" else None)
            )
    return hasil


@dataclass
class Penjelasan:
    """Penjelasan terstruktur ketiga tier — dipakai UI, dan diringkas jadi kalimat oleh `teks`."""

    label: dict[str, str] = field(default_factory=dict)
    sumber_label: str = SUMBER_LABEL_FUZZY
    tier1: str = ""
    tier2: str = ""
    tier3: Optional[str] = None
    kontribusi: list[dict[str, Any]] = field(default_factory=list)
    teks: str = ""


def _kontribusi(
    label: Mapping[str, str], keanggotaan: Optional[Mapping[str, str]] = None
) -> list[dict[str, Any]]:
    """Kriteria diurutkan menurut bobotnya — 'kenapa peringkat segini' versi yang dapat dibaca.

    Bobot adalah pengaruh kriteria terhadap peringkat menurut konfigurasi (OI-12); label adalah
    posisi pengajuan ini pada kriteria tersebut. Keduanya bersama-sama menjawab pertanyaan petugas
    tanpa satu pun angka jarak yang tidak bermakna baginya.

    `keanggotaan` bila diberikan adalah label yang **tersimpan saat batch dirangking**; ia menang
    atas label yang dihitung ulang, karena konfigurasi bisa saja sudah berubah sejak batch itu.
    """
    bobot = load_fuzzy_config().get("bobot") or {}
    baris = []
    for nama, w in sorted(bobot.items(), key=lambda kv: -kv[1]):
        tersimpan = (keanggotaan or {}).get(nama)
        baris.append(
            {
                "kriteria": nama,
                "bobot": w,
                "label": _rapikan(tersimpan) if tersimpan else label.get(nama, "-"),
                "dari_snapshot": bool(tersimpan),
            }
        )
    return baris


def susun_penjelasan(
    features: Mapping[str, float],
    skor_urgensi: float,
    prediksi_hasil: str,
    probabilitas: float,
    *,
    versi_tier1: Optional[str] = None,
    versi_tier2: Optional[str] = None,
    topsis: Optional[Mapping[str, Any]] = None,
    margin_urgensi: Optional[float] = None,
) -> Penjelasan:
    """Rakit penjelasan ketiga tier (OI-07).

    `topsis` bila ada: dict berisi `peringkat`, `nilai_preferensi`, `seri_dengan`, `keanggotaan`,
    `versi_metode` — persis yang disimpan `ranking_topsis`.
    """
    label = labeli(features, margin_urgensi)
    sumber = SUMBER_LABEL_FUZZY if _kriteria() else SUMBER_LABEL_CADANGAN

    tanggungan = int(features.get("jumlah_tanggungan", 0))
    tier1 = f"Narasi menunjukkan urgensi {label['skor_urgensi']} (skor {skor_urgensi:.2f})"
    if versi_tier1:
        tier1 += f" — {versi_tier1}"

    kondisi = [
        _FRASA["pendapatan"].format(label=label["pendapatan"]).capitalize(),
        f"{tanggungan} tanggungan ({label['jumlah_tanggungan']})",
        _FRASA["housing_need"].format(label=label["housing_need"]),
    ]
    if features.get("aset_produktif", 0.0) >= 1.0:
        kondisi.append("memiliki aset produktif")
    if features.get("riwayat_bantuan", 0.0) >= 1.0:
        kondisi.append("pernah menerima bantuan")

    putusan = "LAYAK" if prediksi_hasil == "layak" else "TIDAK LAYAK"
    tier2 = (
        "; ".join(kondisi)
        + f". Model memprediksi {putusan} (probabilitas {probabilitas:.2f})"
    )
    if versi_tier2:
        tier2 += f" — {versi_tier2}"

    tier3 = None
    keanggotaan_snapshot = None
    if topsis:
        keanggotaan_snapshot = topsis.get("keanggotaan")
        peringkat = topsis.get("peringkat")
        nilai = topsis.get("nilai_preferensi")
        seri = topsis.get("seri_dengan") or 0
        bagian = [f"Peringkat prioritas #{peringkat} di antara pengajuan yang lolos kelayakan"]
        if nilai is not None:
            bagian.append(f"nilai preferensi {nilai:.4f}")
        if seri:
            bagian.append(
                f"seri dengan {seri} pengajuan lain — urutan diputus aturan tiebreak tercatat"
            )
        tier3 = "; ".join(bagian) + "."
        if topsis.get("versi_metode"):
            tier3 = tier3[:-1] + f" — {topsis['versi_metode']}."

    teks = f"{tier1}. {tier2}."
    if tier3:
        teks += f" {tier3}"

    return Penjelasan(
        label=label,
        sumber_label=sumber,
        tier1=tier1 + ".",
        tier2=tier2 + ".",
        tier3=tier3,
        kontribusi=_kontribusi(label, keanggotaan_snapshot),
        teks=teks,
    )


def build_reason(
    features: Mapping[str, float],
    skor_urgensi: float,
    prediksi_hasil: str,
    probabilitas: float,
    **kwargs: Any,
) -> str:
    """Kalimat penjelasan tunggal — kontrak lama dipertahankan (dipakai API & tes)."""
    return susun_penjelasan(
        features, skor_urgensi, prediksi_hasil, probabilitas, **kwargs
    ).teks
