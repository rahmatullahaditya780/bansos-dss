"""Generator data simulasi (Bahasa Indonesia) untuk pengembangan Fase 0.

Menghasilkan rumah tangga dengan fitur terstruktur + teks naratif + label historis/urgensi yang
SALING BERKORELASI (via faktor laten kemiskinan `k`) agar dataset dapat dipelajari model pada
fase berikutnya. Data ini bersifat sintetis (asal_data='sintetis'), bukan data warga nyata.
"""
from __future__ import annotations

import random

from faker import Faker

fake = Faker("id_ID")

PEKERJAAN = [
    "Tidak bekerja", "Buruh tani", "Buruh harian", "Nelayan", "Pedagang kecil",
    "Tukang ojek", "Petani", "Wiraswasta", "Karyawan swasta", "Pensiunan",
]
STATUS_NIKAH = ["Belum Kawin", "Kawin", "Cerai Hidup", "Cerai Mati"]
LANTAI = ["tanah", "kayu", "semen", "keramik"]        # buruk -> baik
DINDING = ["bambu", "kayu", "seng", "tembok"]          # buruk -> baik
AIR = ["sungai", "sumur", "pdam"]                      # buruk -> baik

FRASA_URGEN = [
    "kepala keluarga menderita sakit kronis dan tidak mampu bekerja",
    "rumah gubuk nyaris roboh serta atap bocor parah saat hujan",
    "anak balita mengalami gizi buruk dan stunting",
    "tulang punggung keluarga baru saja meninggal dunia",
    "menanggung lansia jompo yang sakit-sakitan",
    "ibu sedang hamil tanpa biaya persalinan",
    "beberapa anak terancam putus sekolah karena biaya",
    "kepala keluarga menyandang disabilitas",
]
FRASA_BIASA = [
    "kondisi ekonomi keluarga tergolong menengah dan cukup stabil",
    "kepala keluarga bekerja tetap dengan penghasilan memadai",
    "keluarga memiliki usaha kecil yang berjalan lancar",
    "tidak ada anggota keluarga yang sakit berat",
]


def _pick(options: list[str], k: float, noise: float = 0.18) -> str:
    """Pilih opsi berdasarkan faktor k (k tinggi -> opsi lebih buruk di indeks awal)."""
    base = (1.0 - k) * (len(options) - 1)
    idx = round(base + random.uniform(-noise, noise) * (len(options) - 1))
    return options[max(0, min(len(options) - 1, idx))]


def _narasi(k: float, urgen: bool) -> str:
    inti = random.choice(FRASA_URGEN if urgen else FRASA_BIASA)
    if urgen and random.random() < 0.5:
        inti += ", " + random.choice([f for f in FRASA_URGEN if f != inti])
    return f"Berdasarkan observasi petugas, {inti}."


def generate_records(n: int = 12, seed: int | None = 42) -> list[dict]:
    if seed is not None:
        random.seed(seed)
        Faker.seed(seed)

    records: list[dict] = []
    for _ in range(n):
        k = random.random()  # faktor laten kemiskinan 0..1

        pendapatan = int(max(150_000, random.gauss(2_800_000 * (1 - k) + 300_000, 400_000)))
        tanggungan = max(0, round(random.gauss(1 + k * 4, 1.2)))
        aset = random.random() < 0.5 * (1 - k)
        riwayat = random.random() < 0.25 + 0.35 * k
        luas = round(random.uniform(18, 80) * (0.6 + 0.5 * (1 - k)), 1)

        urgen = (k + random.uniform(-0.12, 0.12)) > 0.55
        eligible = (k + random.uniform(-0.15, 0.15)) > 0.5

        records.append(
            {
                "nik": fake.numerify("################"),
                "nama": fake.name(),
                "usia": random.randint(25, 75),
                "jenis_kelamin": random.choice(["L", "P"]),
                "status_pernikahan": random.choice(STATUS_NIKAH),
                "jumlah_tanggungan": tanggungan,
                "alamat": fake.address().replace("\n", ", "),
                "pendapatan": pendapatan,
                "status_pekerjaan": _pick(PEKERJAAN, k),
                "aset_produktif": aset,
                "riwayat_bantuan": riwayat,
                "luas_rumah": luas,
                "jenis_lantai": _pick(LANTAI, k),
                "jenis_dinding": _pick(DINDING, k),
                "sumber_air": _pick(AIR, k),
                "narasi": _narasi(k, urgen),
                "label_urgensi": "tinggi" if urgen else "rendah",
                "label_historis": bool(eligible),
            }
        )
    return records
