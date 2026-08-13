"""Tes harmonisasi data publik Alatas dkk. (2012) → skema `data_survei`.

Data sumbernya TIDAK di-commit (169 MB, lihat .gitignore), jadi mayoritas tes di sini bekerja
pada DataFrame buatan yang bentuknya meniru sumber. Tes yang menyentuh berkas asli ditandai
`butuh_data` dan dilewati di mesin yang baru meng-clone repo.

Yang dijaga bukan "kodenya jalan", melainkan tiga cara pemetaan ini bisa salah TANPA memunculkan
galat apa pun — ketiganya kelas bug yang sudah pernah menggigit proyek ini:

  1. `se2_139` dibaca sebagai boolean (1 = Ya, 3 = Tidak → `bool(3)` itu True);
  2. label diambil dari tabel yang urutannya ternyata tidak sejajar;
  3. konsumsi ribuan rupiah masuk sebagai rupiah.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from data.alatas import harmonisasi
from data.alatas.harmonisasi import (
    AKAR_BAWAAN,
    HarmonisasiError,
    _ambil_label,
    _aset_produktif,
    muat_records,
    ringkasan,
)

butuh_data = pytest.mark.skipif(
    not (AKAR_BAWAAN / harmonisasi.BERKAS_FITUR).exists(),
    reason="data publik Alatas belum diunduh (lihat data/public/alatas2012/SUMBER.md)",
)


# --------------------------------------------------------------------------- contoh buatan
def _fitur_palsu(n: int = 3, **ubah) -> pd.DataFrame:
    d = pd.DataFrame(
        {
            "hhid": [f"{i:06d}" for i in range(n)],
            "hhea": list(range(n)),
            "CONSUMPTION": [300.0 + i for i in range(n)],
            "hhsize": [4] * n,
            "hhage": [45] * n,
            "hhmale": [1] * n,
            "hhmarried": [1] * n,
            "floor": [50.0] * n,
            "tfloor": [1] * n,
            "twall": [1] * n,
            "water": [1] * n,
            "se2_125": [0] * n,
            "se2_138": [0] * n,
            "se2_139": [3] * n,  # 3 = TIDAK memiliki
        }
    )
    for k, v in ubah.items():
        d[k] = v
    return d


def _label_palsu(fitur: pd.DataFrame, poor=None) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "hhea": fitur["hhea"],
            "CONSUMPTION": fitur["CONSUMPTION"],
            "poor": [0] * len(fitur) if poor is None else poor,
        }
    )


def _ksr_palsu(fitur: pd.DataFrame, ksr04=None) -> pd.DataFrame:
    n = len(fitur)
    return pd.DataFrame(
        {
            "hhid": list(fitur["hhid"]) * 2,
            "ksr2type": ["a"] * n + ["b"] * n,
            "ksr04": ([3] * n if ksr04 is None else list(ksr04)) + [3] * n,
        }
    )


@pytest.fixture
def sumber_palsu(monkeypatch):
    """Ganti pembacaan berkas dengan tabel buatan; kembalikan penyetelnya."""
    simpanan: dict[str, pd.DataFrame] = {}

    def pasang(fitur: pd.DataFrame, label: pd.DataFrame = None, ksr: pd.DataFrame = None):
        simpanan[harmonisasi.BERKAS_FITUR] = fitur
        simpanan[harmonisasi.BERKAS_LABEL] = label if label is not None else _label_palsu(fitur)
        simpanan[harmonisasi.BERKAS_BLT] = ksr if ksr is not None else _ksr_palsu(fitur)

    def _baca_palsu(akar: Path, relatif: str) -> pd.DataFrame:
        return simpanan[relatif].copy()

    monkeypatch.setattr(harmonisasi, "_baca", _baca_palsu)
    return pasang


# --------------------------------------------------------------------------- jebakan 1: se2_139
def test_se2_139_tiga_berarti_tidak_memiliki():
    """`bool(3)` itu True — pemetaan harus membandingkan dengan 1, bukan mengandalkan truthiness."""
    f = _fitur_palsu(se2_139=[3, 3, 3])
    assert not _aset_produktif(f).any(), "nilai 3 (= Tidak) tidak boleh terbaca sebagai memiliki"


def test_se2_139_satu_berarti_memiliki():
    assert _aset_produktif(_fitur_palsu(se2_139=[1, 1, 1])).all()


def test_aset_produktif_gabungan_tiga_sumber():
    f = _fitur_palsu(n=3, se2_139=[3, 3, 3], se2_138=[1, 0, 0], se2_125=[0, 1, 0])
    assert list(_aset_produktif(f)) == [True, True, False]


# --------------------------------------------------------------------------- jebakan 2: kesejajaran
def test_label_menolak_jumlah_baris_berbeda():
    f = _fitur_palsu(3)
    with pytest.raises(HarmonisasiError, match="jumlah baris berbeda"):
        _ambil_label(f, _label_palsu(_fitur_palsu(2)))


def test_label_menolak_hhea_tidak_sejajar():
    f = _fitur_palsu(3)
    salah = _label_palsu(f)
    salah["hhea"] = [9, 9, 9]
    with pytest.raises(HarmonisasiError, match="hhea"):
        _ambil_label(f, salah)


def test_label_menolak_consumption_tidak_sejajar():
    f = _fitur_palsu(3)
    salah = _label_palsu(f)
    salah["CONSUMPTION"] = salah["CONSUMPTION"][::-1].to_numpy()
    with pytest.raises(HarmonisasiError, match="CONSUMPTION"):
        _ambil_label(f, salah)


def test_label_menerima_yang_benar_benar_sejajar():
    f = _fitur_palsu(3)
    assert list(_ambil_label(f, _label_palsu(f, poor=[1, 0, 1]))) == [1, 0, 1]


# --------------------------------------------------------------------------- jebakan 3: satuan
def test_konsumsi_ribuan_dikali_seribu(sumber_palsu):
    sumber_palsu(_fitur_palsu(1))
    r = muat_records()[0]
    assert r["pendapatan"] == pytest.approx(300_000.0), "CONSUMPTION 300 (ribu Rp) → Rp 300.000"


def test_deflator_diterapkan(sumber_palsu):
    sumber_palsu(_fitur_palsu(1))
    r = muat_records(deflator=2.5)[0]
    assert r["pendapatan"] == pytest.approx(750_000.0)


# --------------------------------------------------------------------------- pemetaan rumah
@pytest.mark.parametrize(
    "kolom,bidang,nilai,harapan",
    [
        ("tfloor", "jenis_lantai", 0, "tanah"),
        ("tfloor", "jenis_lantai", 1, "semen"),
        ("twall", "jenis_dinding", 0, "kayu"),
        ("twall", "jenis_dinding", 1, "tembok"),
        ("water", "sumber_air", 0, "sumur"),
        ("water", "sumber_air", 1, "pdam"),
    ],
)
def test_peta_rumah_memakai_kosakata_features(sumber_palsu, kolom, bidang, nilai, harapan):
    """Kosakatanya harus persis yang dikenal features.py — yang tak dikenal diam-diam jadi 0,5."""
    sumber_palsu(_fitur_palsu(1, **{kolom: [nilai]}))
    assert muat_records()[0][bidang] == harapan


def test_kosakata_rumah_dikenali_features():
    from app.services.features import _AIR, _DINDING, _LANTAI

    for nilai in harmonisasi._PETA_RUMAH["jenis_lantai"].values():
        assert nilai in _LANTAI
    for nilai in harmonisasi._PETA_RUMAH["jenis_dinding"].values():
        assert nilai in _DINDING
    for nilai in harmonisasi._PETA_RUMAH["sumber_air"].values():
        assert nilai in _AIR


# --------------------------------------------------------------------------- riwayat bantuan
def test_riwayat_bantuan_memakai_gelombang_2005(sumber_palsu):
    """ksr04 1/2 = menerima, 3 = tidak; gelombang 'a' (2005) mendahului eksperimen 2008."""
    f = _fitur_palsu(3)
    sumber_palsu(f, ksr=_ksr_palsu(f, ksr04=[1, 2, 3]))
    assert [r["riwayat_bantuan"] for r in muat_records()] == [True, True, False]


def test_riwayat_bantuan_menolak_hhid_yang_hilang(sumber_palsu):
    f = _fitur_palsu(3)
    ksr = _ksr_palsu(f)
    sumber_palsu(f, ksr=ksr[ksr["hhid"] != "000001"])
    with pytest.raises(HarmonisasiError, match="tidak ada di"):
        muat_records()


def test_gelombang_tidak_dikenal_ditolak(sumber_palsu):
    sumber_palsu(_fitur_palsu(1))
    with pytest.raises(HarmonisasiError, match="gelombang BLT"):
        muat_records(gelombang_blt="2099")


# --------------------------------------------------------------------------- baris tanpa label
def test_baris_tanpa_label_dibuang(sumber_palsu):
    f = _fitur_palsu(3)
    sumber_palsu(f, label=_label_palsu(f, poor=[1, None, 0]))
    assert len(muat_records()) == 2


def test_berkas_hilang_memberi_pesan_yang_menuntun():
    with pytest.raises(HarmonisasiError, match="SUMBER.md"):
        muat_records("jalan/yang/tidak/ada")


# --------------------------------------------------------------------------- data sungguhan
@butuh_data
def test_data_asli_cocok_dengan_angka_paper():
    recs = muat_records()
    r = ringkasan(recs)
    assert r["jumlah"] == 5753, "5.756 rumah tangga dikurangi 3 tanpa label konsumsi"
    assert r["label_historis_true"] == 2028
    assert r["label_historis_false"] == 3725
    assert r["riwayat_bantuan_true"] == 1397, "penerima BLT 2005"
    assert 400_000 < r["pendapatan_median"] < 410_000, "median Rp 405.745 (nominal 2008)"


@butuh_data
def test_data_asli_nik_unik_dan_jelas_bukan_nik_sungguhan():
    recs = muat_records()
    nik = [r["nik"] for r in recs]
    assert len(set(nik)) == len(nik)
    assert all(n.startswith("PUB-ALATAS-") for n in nik)


@butuh_data
def test_data_asli_gelombang_2008_berbeda_dari_2005():
    """Kalau keduanya sama, berarti penyaring `ksr2type` tidak bekerja."""
    a = sum(r["riwayat_bantuan"] for r in muat_records(gelombang_blt="2005"))
    b = sum(r["riwayat_bantuan"] for r in muat_records(gelombang_blt="2008"))
    assert (a, b) == (1397, 1701)
