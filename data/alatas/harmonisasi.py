"""Petakan data publik Alatas dkk. (2012) → skema `data_survei` proyek ini.

Sumber: `data/public/alatas2012/Targeting_Indonesia/` (CC0, doi:10.7910/DVN/M7SKQZ).
Provenans lengkap & angka verifikasinya di `data/public/alatas2012/SUMBER.md`.

Modul ini SENGAJA murni: ia membaca `.dta` dan mengembalikan list dict, tanpa menyentuh basis
data. Penulisan ke basis data ada di `data/alatas/seed.py`, sehingga pemetaan di sini dapat diuji
tanpa DB — dan sebaliknya, kesalahan pemetaan tidak dapat bersembunyi di balik transaksi DB.

TIGA HAL YANG DIPUTUSKAN DI SINI DAN HARUS MASUK SKRIPSI
--------------------------------------------------------
1. `CONSUMPTION` adalah konsumsi (pangan + non-pangan) per kapita per bulan dalam RIBU rupiah
   NOMINAL 2008 — dipastikan dari rumusnya di `dofiles/Coding_files/coding_baseline.do:71`,
   `(hhconsumption/hhsize)/1000`. Di sini dikalikan 1.000 agar bersatuan rupiah seperti
   `data_survei.pendapatan`, lalu dikalikan `deflator` yang WAJIB ditentukan pemanggil bila
   angkanya hendak dibandingkan dengan rupiah masa kini. Default 1.0 = tetap rupiah 2008.
   Ini konsumsi, bukan pendapatan; perbedaannya harus dinyatakan, bukan disamarkan.

2. Variabel rumah di sumbernya BINER, sedangkan `app/services/features.py` menanti string dan
   diam-diam memetakan nilai tak dikenal ke 0,5. Proyeksi biner → kategori itu lossy (7 tingkat
   jadi 2). Aturan yang dipakai: sisi yang maknanya TUNGGAL diberi nilai persisnya; sisi "bukan X"
   yang maknanya MAJEMUK diberi opsi TENGAH dari rentang yang mungkin, bukan yang terburuk —
   memilih yang terburuk akan melebih-lebihkan kemiskinan responden. Lihat `_PETA_RUMAH`.

3. `label_historis` diambil dari `mistargeting_CORRECTED.dta` yang TIDAK punya `hhid`. Barisnya
   memang sejajar dengan berkas fitur, tetapi menggabung berdasarkan urutan baris itu rapuh.
   `_ambil_label()` karena itu MEMVERIFIKASI kesejajaran (`CONSUMPTION` + `hhea` baris-per-baris)
   dan melempar galat bila meleset. Proyek ini sudah tiga kali digigit nilai hulu yang salah
   dipakai diam-diam sementara seluruh tes hijau; kesejajaran diam-diam adalah bentuk yang sama.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

# Akar hasil ekstrak arsip Dataverse.
AKAR_BAWAAN = Path("data/public/alatas2012/Targeting_Indonesia")

BERKAS_FITUR = "codeddata/coding_suseti_pmt.dta"
BERKAS_LABEL = "codeddata/mistargeting_CORRECTED.dta"
BERKAS_BLT = "data/baseline/hh_ksr2.dta"

# Penanda asal agar dapat ditelusuri di basis data & CSV korpus.
ASAL_DATA = "publik"
VERSI_HARMONISASI = "alatas2012-v1"

# Biner sumber → kosakata `app/services/features.py`. Nilai dalam komentar adalah skor kebutuhan
# yang dihasilkan `housing_need_score` (1,0 = paling butuh).
_PETA_RUMAH = {
    # `tfloor` = "Not earth floor". 0 hanya bisa berarti tanah; 1 mencakup kayu/semen/keramik.
    "jenis_lantai": {0: "tanah", 1: "semen"},      # 1,0  |  0,3 (tengah dari kayu..keramik)
    # `twall` = "Brick or cement wall". 1 tunggal (tembok); 0 mencakup bambu/kayu/seng.
    "jenis_dinding": {0: "kayu", 1: "tembok"},     # 0,6 (tengah)  |  0,0
    # `water` = "Clean drinking water". 1 tunggal (pdam); 0 mencakup sungai/hujan/mata air/sumur.
    "sumber_air": {0: "sumur", 1: "pdam"},         # 0,5 (tengah)  |  0,0
}
_KOLOM_RUMAH = {"jenis_lantai": "tfloor", "jenis_dinding": "twall", "sumber_air": "water"}

# `ksr2type` memisahkan gelombang BLT. 'a' = 2005 (mendahului eksperimen 2008 → bebas kebocoran),
# 'b' = 2008. `ksr04`: 1 = ya (ada nomor kartu), 2 = ya (tanpa kartu), 3 = tidak.
_GELOMBANG_BLT = {"2005": "a", "2008": "b"}
_KSR04_MENERIMA = (1, 2)


class HarmonisasiError(RuntimeError):
    """Data sumber tidak sesuai anggapan modul ini."""


def _baca(akar: Path, relatif: str) -> pd.DataFrame:
    path = akar / relatif
    if not path.exists():
        raise HarmonisasiError(
            f"Berkas sumber tidak ada: {path}\n"
            "Unduh & ekstrak arsip Dataverse lebih dulu — lihat data/public/alatas2012/SUMBER.md"
        )
    return pd.read_stata(path, convert_categoricals=False)


def _ambil_label(fitur: pd.DataFrame, label: pd.DataFrame) -> pd.Series:
    """Ambil kolom `poor`, setelah membuktikan kedua tabel benar-benar sejajar.

    `mistargeting_CORRECTED.dta` tidak membawa `hhid`, jadi satu-satunya cara menggabungkannya
    adalah lewat urutan baris. Itu boleh dilakukan HANYA bila kesejajarannya dibuktikan, bukan
    diandaikan.
    """
    if len(fitur) != len(label):
        raise HarmonisasiError(
            f"jumlah baris berbeda: fitur {len(fitur)} vs label {len(label)} — "
            "tidak dapat digabung berdasarkan urutan baris"
        )
    if not (fitur["hhea"].to_numpy() == label["hhea"].to_numpy()).all():
        raise HarmonisasiError("kolom `hhea` tidak cocok baris-per-baris — urutan baris berbeda")
    kiri = fitur["CONSUMPTION"].fillna(-1).to_numpy()
    kanan = label["CONSUMPTION"].fillna(-1).to_numpy()
    if not (abs(kiri - kanan) < 1e-6).all():
        raise HarmonisasiError("kolom `CONSUMPTION` tidak cocok baris-per-baris — urutan berbeda")
    return label["poor"]


def _riwayat_bantuan(akar: Path, hhid: pd.Series, gelombang: str) -> pd.Series:
    """Peta hhid → pernah menerima BLT pada gelombang yang diminta."""
    if gelombang not in _GELOMBANG_BLT:
        raise HarmonisasiError(
            f"gelombang BLT tidak dikenal: {gelombang!r} (pilih {list(_GELOMBANG_BLT)})"
        )
    ksr = _baca(akar, BERKAS_BLT)
    ksr = ksr[ksr["ksr2type"] == _GELOMBANG_BLT[gelombang]]
    peta = dict(zip(ksr["hhid"].astype(str), ksr["ksr04"]))
    hilang = sum(1 for h in hhid.astype(str) if h not in peta)
    if hilang:
        raise HarmonisasiError(
            f"{hilang} hhid tidak ada di {BERKAS_BLT} gelombang {gelombang} — "
            "irisan seharusnya 5.756/5.756; periksa berkas sumber"
        )
    return hhid.astype(str).map(lambda h: peta[h] in _KSR04_MENERIMA)


def _aset_produktif(f: pd.DataFrame) -> pd.Series:
    """Kepemilikan aset produktif: lahan pertanian, lahan non-pertanian, atau motor.

    `se2_138` (lahan pertanian) dan `se2_125` (motor) sudah dummy 0/1 dari `coding_baseline.do`.
    `se2_139` TIDAK — ia salinan mentah pertanyaan `hr01` ("Apakah rumah tangga ini memiliki saat
    ini?") dengan 1 = Ya dan 3 = Tidak. Menulis `bool(se2_139)` akan membalik maknanya untuk 5.226
    rumah tangga tanpa memunculkan galat apa pun.
    """
    return (f["se2_138"] == 1) | (f["se2_125"] == 1) | (f["se2_139"] == 1)


def muat_records(
    akar: Path | str = AKAR_BAWAAN,
    *,
    gelombang_blt: str = "2005",
    deflator: float = 1.0,
) -> list[dict]:
    """Baca sumber Alatas dan kembalikan baris siap-seed (satu dict per rumah tangga).

    `deflator` mengalikan rupiah 2008 agar sebanding dengan tahun rujukan skripsi; biarkan 1.0
    bila memang ingin memakai rupiah nominal 2008, dan catat pilihannya.
    """
    akar = Path(akar)
    f = _baca(akar, BERKAS_FITUR)
    poor = _ambil_label(f, _baca(akar, BERKAS_LABEL))
    riwayat = _riwayat_bantuan(akar, f["hhid"], gelombang_blt)
    aset = _aset_produktif(f)

    records: list[dict] = []
    for i in range(len(f)):
        baris = f.iloc[i]
        label = poor.iloc[i]
        # Rumah tangga tanpa label kemiskinan tidak dapat dipakai melatih Tier 2 (3 baris).
        if pd.isna(label) or pd.isna(baris["CONSUMPTION"]):
            continue
        hhid = str(baris["hhid"])
        records.append(
            {
                # NIK semu, deterministik, dan JELAS bukan NIK asli — data ini tidak membawa
                # identitas apa pun, dan tidak boleh terlihat seolah membawanya.
                "nik": f"PUB-ALATAS-{hhid}",
                "nama": f"RT Alatas {hhid}",
                "usia": _int_atau(baris["hhage"], 0),
                "jenis_kelamin": "L" if baris.get("hhmale") == 1 else "P",
                "status_pernikahan": "Kawin" if baris.get("hhmarried") == 1 else "Tidak diketahui",
                "jumlah_tanggungan": max(0, _int_atau(baris["hhsize"], 1) - 1),
                "alamat": f"hhea {int(baris['hhea'])} (publik, tanpa alamat)",
                "pendapatan": float(baris["CONSUMPTION"]) * 1000.0 * deflator,
                "status_pekerjaan": None,  # tidak ada padanannya di sumber
                "aset_produktif": bool(aset.iloc[i]),
                "riwayat_bantuan": bool(riwayat.iloc[i]),
                "luas_rumah": _float_atau_none(baris["floor"]),
                **{k: _peta_rumah(baris, k) for k in _KOLOM_RUMAH},
                "label_historis": bool(label == 1),
                "asal_data": ASAL_DATA,
                "hhid": hhid,
            }
        )
    return records


def _peta_rumah(baris: pd.Series, bidang: str) -> str | None:
    nilai = baris[_KOLOM_RUMAH[bidang]]
    if pd.isna(nilai):
        return None  # biarkan kosong; features.py memakai default 0,5 untuk yang tidak diketahui
    return _PETA_RUMAH[bidang].get(int(nilai))


def _int_atau(nilai, bawaan: int) -> int:
    return bawaan if pd.isna(nilai) else int(nilai)


def _float_atau_none(nilai) -> float | None:
    return None if pd.isna(nilai) else float(nilai)


def ringkasan(records: list[dict]) -> dict[str, object]:
    """Statistik ringkas untuk dicetak setelah harmonisasi — bahan periksa cepat."""
    if not records:
        return {"jumlah": 0}
    n = len(records)
    layak = sum(1 for r in records if r["label_historis"])
    pendapatan = sorted(r["pendapatan"] for r in records)
    return {
        "jumlah": n,
        "label_historis_true": layak,
        "label_historis_false": n - layak,
        "proporsi_true": round(layak / n, 4),
        "pendapatan_min": round(pendapatan[0]),
        "pendapatan_median": round(pendapatan[n // 2]),
        "pendapatan_maks": round(pendapatan[-1]),
        "aset_produktif_true": sum(1 for r in records if r["aset_produktif"]),
        "riwayat_bantuan_true": sum(1 for r in records if r["riwayat_bantuan"]),
        "lantai": _hitung(records, "jenis_lantai"),
        "dinding": _hitung(records, "jenis_dinding"),
        "air": _hitung(records, "sumber_air"),
    }


def _hitung(records: list[dict], bidang: str) -> dict[str, int]:
    hasil: dict[str, int] = {}
    for r in records:
        kunci = str(r[bidang])
        hasil[kunci] = hasil.get(kunci, 0) + 1
    return dict(sorted(hasil.items()))


if __name__ == "__main__":  # pragma: no cover
    import argparse
    import json

    ap = argparse.ArgumentParser(description="Pratinjau harmonisasi Alatas dkk. (tanpa DB).")
    ap.add_argument("--akar", default=str(AKAR_BAWAAN))
    ap.add_argument("--gelombang-blt", default="2005", choices=sorted(_GELOMBANG_BLT))
    ap.add_argument("--deflator", type=float, default=1.0)
    args = ap.parse_args()

    recs = muat_records(args.akar, gelombang_blt=args.gelombang_blt, deflator=args.deflator)
    print(json.dumps(ringkasan(recs), indent=2, ensure_ascii=False))
    print("\ncontoh baris pertama:")
    print(json.dumps(recs[0], indent=2, ensure_ascii=False))
