"""Tes Tier 1 (Fase 2): preprocessing, korpus & split, serta kontrak inference.

Tes di sini TIDAK memerlukan artefak model: jalur fallback diuji secara eksplisit, dan jalur
model asli diuji hanya bila `ml/artifacts/indobert` tersedia (dilewati bila belum diunduh),
supaya suite tetap hijau di mesin tanpa artefak.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.services import tier1_nlp
from ml.tier1 import LABEL2ID
from ml.tier1.corpus import generate_corpus
from ml.tier1.dataset import Baris, periksa_kebocoran, split_80_20
from ml.tier1.infer import VERSI_FALLBACK, UrgencyScorer, reset_scorer
from ml.tier1.preprocessing import preprocess

ARTEFAK = Path("ml/artifacts/indobert")
butuh_artefak = pytest.mark.skipif(
    not (ARTEFAK / "config.json").exists(), reason="artefak IndoBERT belum tersedia"
)


# --- Preprocessing (FR-11) -------------------------------------------------

def test_preprocess_lowercase_dan_rapikan_spasi():
    assert preprocess("  Kepala   Keluarga\n SAKIT  ") == "kepala keluarga sakit"


def test_preprocess_buang_url_email_dan_nik():
    hasil = preprocess("Lapor ke http://kel.go.id / admin@kel.go.id NIK 7371012345678901 sakit")
    assert "http" not in hasil and "@" not in hasil and "7371012345678901" not in hasil
    assert "sakit" in hasil


def test_preprocess_normalisasi_singkatan():
    hasil = preprocess("KK tdk bekerja krn sakit, anak2 blm sekolah")
    assert "kepala keluarga" in hasil
    assert "tidak" in hasil and "karena" in hasil and "belum" in hasil


def test_preprocess_pertahankan_negasi():
    """Kata negasi menentukan label; tidak boleh hilang saat pembersihan."""
    assert "tidak" in preprocess("Tidak ada anggota keluarga yang sakit kronis.")


def test_preprocess_input_kosong_aman():
    assert preprocess("") == ""
    assert preprocess(None) == ""


def test_preprocess_idempoten():
    teks = "KK tdk bekerja krn sakiiiit kronis!!!"
    sekali = preprocess(teks)
    assert preprocess(sekali) == sekali


# --- Korpus & split --------------------------------------------------------

def test_korpus_deterministik_dan_berlabel_valid():
    a = generate_corpus(n=200, seed=7)
    b = generate_corpus(n=200, seed=7)
    assert [s.teks for s in a] == [s.teks for s in b]
    assert {s.label for s in a} <= set(LABEL2ID)


def test_korpus_memuat_kasus_sulit():
    """Hard negative/positive wajib ada agar model tidak sekadar mencocokkan kata kunci.

    Empat kategori ini menutup celah yang ditemukan uji silang rubrik (2026-08-06); menghapus
    salah satunya akan mengembalikan kegagalan yang sudah pernah diperbaiki.
    """
    sampel = generate_corpus(n=600, seed=7)
    kategori = {s.kategori for s in sampel}
    assert "biasa_sulit" in kategori          # kata urgen dalam kalimat ingkar
    assert "urgen_halus" in kategori          # urgen tanpa kata kunci mencolok
    assert "urgen_tersirat" in kategori       # ketidakberdayaan disampaikan tersirat
    assert "biasa_teratasi" in kategori       # kondisi urgen yang sudah teratasi (aturan R3)
    assert "urgen_berlanjut" in kategori      # penanda waktu sama, maknanya berlanjut


def test_frame_teratasi_hanya_untuk_kondisi_yang_masuk_akal():
    """Kematian & disabilitas permanen tidak boleh dibingkai 'sudah pulih' — kalimatnya nonsens."""
    from ml.tier1.corpus import KATEGORI_DAPAT_TERATASI

    assert "kehilangan_pencari_nafkah" not in KATEGORI_DAPAT_TERATASI
    assert "disabilitas_lansia" not in KATEGORI_DAPAT_TERATASI


def test_penanda_waktu_tidak_menentukan_label():
    """Susunan "sudah ... sekarang ..." harus muncul di KEDUA kelas.

    Bila hanya muncul di kelas 'rendah' (lewat frame teratasi), model memakai jalan pintas dangkal:
    menganggap penanda waktu itu selalu berarti masalah sudah selesai. Persis itu yang terjadi pada
    versi v2 dan membuatnya salah pada "sudah tiga bulan menunggak listrik, sekarang menyambung
    dari rumah tetangga".
    """
    sampel = generate_corpus(n=800, seed=5)
    berpenanda = [s for s in sampel if "sudah" in s.teks and "sekarang" in s.teks]
    label = {s.label for s in berpenanda}
    assert label == {"tinggi", "rendah"}, f"penanda waktu hanya muncul di kelas {label}"


def test_split_80_20_stratified_tanpa_kebocoran():
    sampel = generate_corpus(n=600, seed=7)
    baris = [Baris(teks=s.teks, label=s.label, kategori=s.kategori, gaya=s.gaya) for s in sampel]
    latih, uji = split_80_20(baris, test_size=0.2, seed=42)

    assert periksa_kebocoran(latih, uji) == 0
    assert len(latih) + len(uji) == len(baris)
    porsi = len(uji) / len(baris)
    assert 0.15 < porsi < 0.25
    # Kedua kelas terwakili di sisi uji.
    assert {b.label for b in uji} == {"tinggi", "rendah"}


# --- Inference: kontrak & fallback ----------------------------------------

def test_fallback_saat_artefak_tidak_ada(tmp_path):
    scorer = UrgencyScorer(tmp_path / "tidak-ada")
    hasil = scorer.score("kepala keluarga sakit kronis dan rumah nyaris roboh")
    assert 0.0 <= hasil.skor <= 1.0
    assert hasil.fallback is True
    assert hasil.versi_model == VERSI_FALLBACK, "hasil non-model wajib dapat dibedakan di DB"


def test_fallback_batch_konsisten_dengan_satuan(tmp_path):
    scorer = UrgencyScorer(tmp_path / "tidak-ada")
    teks = ["rumah gubuk nyaris roboh", "kondisi ekonomi stabil"]
    assert [h.skor for h in scorer.score_batch(teks)] == [scorer.score(t).skor for t in teks]


def test_kontrak_score_urgency_dipertahankan():
    """pipeline.py bergantung pada bentuk keluaran ini — tidak boleh berubah."""
    out = tier1_nlp.score_urgency("kepala keluarga sakit kronis")
    assert isinstance(out, tier1_nlp.Tier1Output)
    assert isinstance(out.skor, float) and 0.0 <= out.skor <= 1.0
    assert isinstance(out.versi_model, str) and out.versi_model


def test_score_urgency_batch_sepanjang_input():
    keluaran = tier1_nlp.score_urgency_batch(["rumah bocor parah", "keluarga berkecukupan"])
    assert len(keluaran) == 2
    assert all(0.0 <= o.skor <= 1.0 for o in keluaran)


def test_score_urgency_batch_kosong():
    assert tier1_nlp.score_urgency_batch([]) == []


@butuh_artefak
def test_model_asli_membedakan_urgen_dan_biasa():
    reset_scorer()
    scorer = UrgencyScorer(ARTEFAK)
    urgen = scorer.score("kepala keluarga menderita sakit kronis dan rumah nyaris roboh").skor
    biasa = scorer.score("kondisi ekonomi keluarga stabil dan seluruh anak bersekolah").skor
    assert urgen > 0.5 > biasa
    assert scorer.info()["fallback_aktif"] is False


@butuh_artefak
def test_model_asli_tahan_hard_negative():
    """Kalimat bernegasi memuat kata 'sakit kronis' harus tetap berskor rendah."""
    scorer = UrgencyScorer(ARTEFAK)
    assert scorer.score("tidak ada anggota keluarga yang menderita sakit kronis").skor < 0.5


@butuh_artefak
def test_versi_model_dari_metadata():
    scorer = UrgencyScorer(ARTEFAK)
    assert scorer.versi_model.startswith("indobert")
    assert scorer.versi_model != VERSI_FALLBACK
