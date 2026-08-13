"""Tes Tier 2 (Fase 3): skema fitur, split berkelompok, kontrak inference, dan aturan pemilihan model.

Seperti Tier 1, tes di sini TIDAK memerlukan artefak: jalur fallback diuji eksplisit, dan jalur
model asli hanya dijalankan bila `ml/artifacts/tier2` tersedia — supaya suite tetap hijau di mesin
yang baru meng-clone repo (artefak tidak di-commit).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.services import tier2_ml
from app.services.features import build_features
from ml.tier2 import FITUR, FITUR_TANPA_URGENSI, NAMA_BERKAS_MODEL, nama_set_fitur
from ml.tier2.dataset import (
    Baris,
    fitur_csv,
    muat_csv,
    periksa_kebocoran,
    split_80_20,
    tulis_csv,
)
from ml.tier2.infer import VERSI_FALLBACK, EligibilityClassifier, reset_classifier
from ml.tier2.skema_fitur import SkemaFiturError, periksa_skema, vektor
from ml.tier2.train import pilih_pemenang

ARTEFAK = Path("ml/artifacts/tier2")
butuh_artefak = pytest.mark.skipif(
    not (ARTEFAK / NAMA_BERKAS_MODEL).exists(), reason="artefak Tier 2 belum dilatih"
)


def _fitur(**ubah) -> dict[str, float]:
    dasar = dict(
        pendapatan=400_000, jumlah_tanggungan=4, usia=45, aset_produktif=False,
        riwayat_bantuan=False, jenis_lantai="tanah", jenis_dinding="bambu",
        sumber_air="sungai", luas_rumah=20, skor_urgensi=0.9,
    )
    dasar.update(ubah)
    return build_features(**dasar)


def _baris(warga_id: int, label: str, n: int = 1) -> list[Baris]:
    return [
        Baris(warga_id=warga_id, pengajuan_id=warga_id * 100 + i, label=label,
              asal_data="sintetis", fitur=_fitur())
        for i in range(n)
    ]


# --- Skema fitur -----------------------------------------------------------

def test_vektor_mengikuti_urutan_kanonik():
    f = _fitur(pendapatan=123_456, usia=61)
    v = vektor(f)
    assert len(v) == len(FITUR)
    assert v[FITUR.index("pendapatan")] == 123_456.0
    assert v[FITUR.index("usia")] == 61.0


def test_vektor_menolak_fitur_kurang():
    with pytest.raises(SkemaFiturError, match="fitur wajib tidak ada"):
        vektor({"pendapatan": 1.0})


def test_vektor_menolak_nilai_bukan_angka():
    f = _fitur()
    f["pendapatan"] = "empat ratus ribu"
    with pytest.raises(SkemaFiturError, match="bukan angka"):
        vektor(f)


def test_periksa_skema_menolak_urutan_bergeser():
    """Model sklearn menerima array polos; urutan yang bergeser salah secara SENYAP tanpa ini."""
    with pytest.raises(SkemaFiturError, match="urutan/isi fitur artefak berbeda"):
        periksa_skema(list(reversed(FITUR)))
    periksa_skema(FITUR)  # urutan benar tidak boleh melempar


# --- Split berkelompok per warga -------------------------------------------

def test_split_tidak_memecah_pengajuan_satu_warga():
    """Satu warga bisa mengajukan berkali-kali; kembarannya tidak boleh jatuh di dua sisi."""
    baris = []
    for w in range(1, 41):
        baris += _baris(w, "layak" if w % 2 else "tidak_layak", n=3)

    latih, uji = split_80_20(baris, test_size=0.2, seed=42)

    assert periksa_kebocoran(latih, uji) == 0
    assert len(latih) + len(uji) == len(baris)
    assert {b.warga_id for b in latih} & {b.warga_id for b in uji} == set()


def test_split_stratified_dan_proporsional():
    baris = []
    for w in range(1, 101):
        baris += _baris(w, "layak" if w % 2 else "tidak_layak")
    latih, uji = split_80_20(baris, test_size=0.2, seed=42)

    assert 0.15 < len(uji) / len(baris) < 0.25
    assert {b.label for b in uji} == {"layak", "tidak_layak"}


def test_split_deterministik():
    baris = []
    for w in range(1, 51):
        baris += _baris(w, "layak" if w % 3 else "tidak_layak")
    a = split_80_20(baris, seed=42)[1]
    b = split_80_20(baris, seed=42)[1]
    assert [x.pengajuan_id for x in a] == [x.pengajuan_id for x in b]


# --- Aturan pemilihan model ------------------------------------------------

def _ringkas(nama: str, f1: float, simpangan: float, recall: float) -> dict:
    return {"nama": nama, "f1_rerata": f1, "f1_simpangan": simpangan, "recall_rerata": recall}


def test_pemenang_jelas_saat_selisih_melampaui_simpangan():
    nama, alasan, dapat_dibedakan = pilih_pemenang(
        [_ringkas("random_forest", 0.70, 0.01, 0.70), _ringkas("gradient_boosting", 0.90, 0.01, 0.85)]
    )
    assert nama == "gradient_boosting"
    assert dapat_dibedakan is True
    assert "melampaui" in alasan


def test_selisih_dalam_derau_dinyatakan_tidak_dapat_dibedakan():
    """Temuan probe pra-Fase 3: selisih RF vs GB 0,0050 jauh di bawah simpangannya sendiri.

    Dalam keadaan itu pemenang TIDAK boleh diklaim lebih baik; penentunya recall kelas 'layak'
    (false negative = warga layak yang ditolak sistem) — keputusan teknis #8 rencana Fase 3.
    """
    nama, alasan, dapat_dibedakan = pilih_pemenang(
        [
            _ringkas("gradient_boosting", 0.9167, 0.03, 0.9024),
            _ringkas("random_forest", 0.9117, 0.03, 0.9500),
        ]
    )
    assert dapat_dibedakan is False
    assert nama == "random_forest", "saat seri, recall kelas 'layak' yang menentukan"
    assert "TIDAK DAPAT DIBEDAKAN" in alasan


# --- Inference: kontrak & fallback ----------------------------------------

def test_fallback_saat_artefak_tidak_ada(tmp_path):
    clf = EligibilityClassifier(tmp_path / "tidak-ada")
    hasil = clf.predict(_fitur())
    assert 0.0 <= hasil.probabilitas <= 1.0
    assert hasil.fallback is True
    assert hasil.versi_model == VERSI_FALLBACK, "hasil non-model wajib dapat dibedakan di DB"


def test_fallback_batch_konsisten_dengan_satuan(tmp_path):
    clf = EligibilityClassifier(tmp_path / "tidak-ada")
    daftar = [_fitur(), _fitur(pendapatan=6_000_000, jenis_lantai="keramik")]
    assert [h.probabilitas for h in clf.predict_batch(daftar)] == [
        clf.predict(f).probabilitas for f in daftar
    ]


def test_fallback_menolak_artefak_berskema_beda(tmp_path):
    """Artefak dengan urutan fitur lain harus jatuh ke fallback, bukan memprediksi diam-diam."""
    import json

    palsu = tmp_path / "tier2"
    palsu.mkdir()
    (palsu / NAMA_BERKAS_MODEL).write_bytes(b"bukan model")
    (palsu / "metadata.json").write_text(
        json.dumps({"versi_model": "palsu-v1", "fitur": list(reversed(FITUR))}), encoding="utf-8"
    )

    clf = EligibilityClassifier(palsu)
    hasil = clf.predict(_fitur())
    assert hasil.fallback is True
    assert "urutan/isi fitur" in (clf.info()["alasan_fallback"] or "")


def test_kontrak_predict_eligibility_dipertahankan():
    """pipeline.py bergantung pada bentuk keluaran ini — tidak boleh berubah."""
    out = tier2_ml.predict_eligibility(_fitur())
    assert isinstance(out, tier2_ml.Tier2Output)
    assert out.hasil in {"layak", "tidak_layak"}
    assert isinstance(out.probabilitas, float) and 0.0 <= out.probabilitas <= 1.0
    assert isinstance(out.versi_model, str) and out.versi_model


def test_predict_eligibility_batch_sepanjang_input():
    keluaran = tier2_ml.predict_eligibility_batch([_fitur(), _fitur(pendapatan=6_000_000)])
    assert len(keluaran) == 2
    assert all(o.hasil in {"layak", "tidak_layak"} for o in keluaran)


def test_predict_eligibility_batch_kosong():
    assert tier2_ml.predict_eligibility_batch([]) == []


@butuh_artefak
def test_model_asli_membedakan_miskin_dan_mampu():
    reset_classifier()
    clf = EligibilityClassifier(ARTEFAK)
    miskin = clf.predict(_fitur()).probabilitas
    mampu = clf.predict(
        _fitur(pendapatan=6_000_000, jumlah_tanggungan=0, aset_produktif=True,
               jenis_lantai="keramik", jenis_dinding="tembok", sumber_air="pdam",
               luas_rumah=80, skor_urgensi=0.02)
    ).probabilitas
    assert miskin > 0.5 > mampu
    assert clf.info()["fallback_aktif"] is False


@butuh_artefak
def test_versi_model_dari_metadata():
    clf = EligibilityClassifier(ARTEFAK)
    assert clf.versi_model.startswith("tier2-")
    assert clf.versi_model != VERSI_FALLBACK


@butuh_artefak
def test_metadata_mencatat_batas_klaim():
    """Asal data & keterbedaan kandidat wajib tercatat — dasar kejujuran laporan skripsi."""
    import json

    meta = json.loads((ARTEFAK / "metadata.json").read_text(encoding="utf-8"))
    assert meta["fitur"] == FITUR
    assert meta["asal_data"] in {"sintetis", "publik", "lokal"}
    assert isinstance(meta["pemilihan_model"]["dapat_dibedakan"], bool)
    assert meta["pemilihan_model"]["alasan"]


# --------------------------------------------------------------------------- ablasi tanpa urgensi
# Jalur untuk data publik yang tidak punya teks naratif (mis. Alatas dkk. 2012), sehingga Tier 1
# tidak dapat memberi `skor_urgensi`. Yang dijaga di sini adalah SATU sifat: ketiadaan fitur itu
# harus mustahil lolos diam-diam — tidak lewat nilai netral, tidak lewat CSV yang tertukar, dan
# tidak lewat artefak yang nyelonong melayani aplikasi.


def test_build_features_tanpa_urgensi_menghilangkan_kuncinya():
    """None berarti fiturnya TIDAK ADA — bukan diisi 0,0 atau 0,5."""
    f = build_features(
        pendapatan=400_000, jumlah_tanggungan=4, usia=45, aset_produktif=False,
        riwayat_bantuan=False, jenis_lantai="tanah", jenis_dinding="bambu",
        sumber_air="sungai", luas_rumah=20, skor_urgensi=None,
    )
    assert "skor_urgensi" not in f
    assert set(f) == set(FITUR_TANPA_URGENSI)


def test_vektor_lengkap_menolak_dict_tanpa_urgensi():
    """Kalau ini lolos, ablasi bisa mencemari jalur produksi tanpa suara."""
    f = _fitur()
    del f["skor_urgensi"]
    with pytest.raises(SkemaFiturError, match="skor_urgensi"):
        vektor(f)


def test_vektor_ablasi_menerima_enam_fitur():
    f = _fitur()
    del f["skor_urgensi"]
    assert len(vektor(f, FITUR_TANPA_URGENSI)) == 6


def test_periksa_skema_menolak_artefak_ablasi_dengan_alasan():
    """Model 6 fitur menerima vektor 7 fitur tanpa galat — hanya prediksinya yang salah."""
    with pytest.raises(SkemaFiturError, match="tidak boleh melayani pipeline"):
        periksa_skema(FITUR_TANPA_URGENSI)


def test_nama_set_fitur_mengenali_keduanya():
    assert nama_set_fitur(FITUR) == "lengkap"
    assert nama_set_fitur(FITUR_TANPA_URGENSI) == "tanpa_urgensi"


def test_nama_set_fitur_menolak_himpunan_karangan():
    with pytest.raises(ValueError, match="tidak dikenal"):
        nama_set_fitur(["pendapatan", "usia"])


def _tulis_baca(tmp_path, fitur):
    baris = _baris(1, "layak")
    for b in baris:
        b.fitur = {k: v for k, v in b.fitur.items() if k in fitur}
    path = tmp_path / "tier2_train.csv"
    tulis_csv(baris, path, fitur)
    return path


def test_csv_membawa_himpunan_fiturnya_sendiri(tmp_path):
    """Header berkas, bukan `ml.tier2.FITUR`, yang menentukan skema — supaya tak bisa tertukar."""
    assert fitur_csv(_tulis_baca(tmp_path / "a", FITUR)) == FITUR
    assert fitur_csv(_tulis_baca(tmp_path / "b", FITUR_TANPA_URGENSI)) == FITUR_TANPA_URGENSI


def test_muat_csv_ablasi_tidak_mengarang_skor_urgensi(tmp_path):
    baris = muat_csv(_tulis_baca(tmp_path, FITUR_TANPA_URGENSI))
    assert "skor_urgensi" not in baris[0].fitur


def test_csv_dengan_kolom_fitur_karangan_ditolak(tmp_path):
    path = tmp_path / "aneh.csv"
    path.write_text("pengajuan_id,warga_id,label,label_id,asal_data,pendapatan\n", encoding="utf-8")
    with pytest.raises(ValueError, match="tidak dikenal"):
        fitur_csv(path)
