"""Tes generator penjelasan (OI-07, FR-23) — Fase 5, keputusan D-01.

Yang dijaga di sini bukan "kalimatnya enak dibaca", melainkan satu sifat yang dapat dilanggar
diam-diam: **label yang dibaca petugas harus label yang sama dengan yang dipakai merangking.**
Sebelum Fase 5 keduanya berbeda pada 70,3% pengajuan untuk kondisi rumah dan 58,0% untuk urgensi
(evaluasi pra-Fase 5 §5.1), dan tidak satu pun tes menangkapnya — karena tes lama hanya memeriksa
bahwa `alasan` berupa string tidak kosong.
"""
from __future__ import annotations

import pytest

from app.services import explanation
from app.services.fuzzy_config import load_fuzzy_config
from ml.tier3.keanggotaan import muat_kriteria


@pytest.fixture(scope="module")
def kriteria():
    cfg = load_fuzzy_config()
    return muat_kriteria(cfg, list(cfg["bobot"]))


def _features(pendapatan, tanggungan, housing, urgensi):
    return {
        "pendapatan": pendapatan,
        "jumlah_tanggungan": tanggungan,
        "housing_need": housing,
        "skor_urgensi": urgensi,
        "aset_produktif": 0.0,
        "riwayat_bantuan": 0.0,
    }


# Kisi nilai yang menyapu seluruh domain tiap kriteria, termasuk perbatasan antar-himpunan —
# tempat dua definisi ambang paling mudah berselisih.
KISI = [
    (p, t, h, u)
    for p in (0, 250_000, 500_000, 750_000, 1_000_000, 1_500_000, 2_000_000, 2_999_999)
    for t in (0, 1, 3, 5, 6, 9)
    for h in (0.0, 0.2, 0.33, 0.5, 0.67, 0.9, 1.0)
    for u in (0.0001, 0.05, 0.3, 0.5, 0.7, 0.95, 0.9999)
]


def test_label_penjelasan_identik_dengan_label_fuzzy(kriteria):
    """Skew HARUS nol di seluruh domain — bukan hanya di contoh yang kebetulan dipilih."""
    beda = []
    for p, t, h, u in KISI:
        f = _features(p, t, h, u)
        label = explanation.labeli(f)
        for nama, kf in kriteria.items():
            harapan = kf.label(f[nama]).replace("_", " ")
            if label[nama] != harapan:
                beda.append((nama, f[nama], label[nama], harapan))
    assert not beda, f"{len(beda)} dari {len(KISI) * len(kriteria)} label menyimpang: {beda[:5]}"


def test_sumber_label_menandai_asalnya():
    """Penanda sumber label wajib ada — pola yang tiga kali jadi satu-satunya penyingkap."""
    pen = explanation.susun_penjelasan(
        _features(400_000, 5, 0.8, 0.99), 0.99, "layak", 0.93
    )
    assert pen.sumber_label == explanation.SUMBER_LABEL_FUZZY


def test_label_urgensi_memakai_skala_logit_bukan_ambang_setengah():
    """Probabilitas 0,6 TIDAK otomatis 'tinggi': pada skala logit ia masih di sekitar nol.

    Ini persis kekeliruan yang diperbaiki D-01 — `kategori_urgensi()` lama memotong probabilitas
    di 0,5 padahal sejak Fase 4 kriteria ini difuzzifikasi pada margin logit.
    """
    label_06 = explanation.label_kriteria("skor_urgensi", 0.6)
    label_jenuh = explanation.label_kriteria("skor_urgensi", 0.9999)
    assert label_06 != "tinggi"
    assert label_jenuh == "tinggi"


def test_margin_dipakai_bila_diberikan():
    """Margin logit dari Tier 1 lebih tepat daripada membalik probabilitas yang terbulat."""
    tanpa = explanation.label_kriteria("skor_urgensi", 0.99)
    dengan = explanation.label_kriteria("skor_urgensi", 0.99, margin=-8.0)
    assert dengan == "sangat rendah"
    assert dengan != tanpa


def test_penjelasan_menyebut_ketiga_tier():
    """0/300 kalimat menyebut Tier 3 sebelum Fase 5 (evaluasi §5.2)."""
    pen = explanation.susun_penjelasan(
        _features(300_000, 6, 0.9, 0.999),
        0.999,
        "layak",
        0.95,
        versi_tier1="indobert-uji-v1",
        versi_tier2="tier2-uji-v1",
        topsis={
            "peringkat": 7,
            "nilai_preferensi": 0.6421,
            "seri_dengan": 2,
            "versi_metode": "fuzzy-topsis-chen2000-v1",
            "keanggotaan": {"pendapatan": "sangat_rendah"},
        },
    )
    assert "indobert-uji-v1" in pen.tier1
    assert "tier2-uji-v1" in pen.tier2
    assert pen.tier3 and "#7" in pen.tier3 and "0.6421" in pen.tier3
    assert "seri" in pen.tier3
    assert "fuzzy-topsis-chen2000-v1" in pen.tier3
    for potongan in ("indobert-uji-v1", "#7", "LAYAK"):
        assert potongan in pen.teks


def test_kontribusi_terurut_bobot_dan_memakai_snapshot():
    """Label dari batch yang tersimpan menang atas label yang dihitung ulang.

    Konfigurasi keanggotaan boleh berubah (OI-13 difinalkan Fase 6); peringkat lama harus tetap
    diterangkan dengan label yang berlaku SAAT ia dirangking.
    """
    pen = explanation.susun_penjelasan(
        _features(2_500_000, 0, 0.1, 0.001),
        0.001,
        "tidak_layak",
        0.05,
        topsis={"peringkat": 3, "nilai_preferensi": 0.4, "keanggotaan": {"pendapatan": "sangat_rendah"}},
    )
    bobot = [k["bobot"] for k in pen.kontribusi]
    assert bobot == sorted(bobot, reverse=True)

    pendapatan = next(k for k in pen.kontribusi if k["kriteria"] == "pendapatan")
    assert pendapatan["label"] == "sangat rendah"  # dari snapshot, bukan hitung ulang ('tinggi')
    assert pendapatan["dari_snapshot"] is True


def test_build_reason_kontrak_lama_dipertahankan():
    """Pemanggil lama (API, tes Fase 0) tidak boleh rusak."""
    teks = explanation.build_reason(_features(400_000, 4, 0.7, 0.98), 0.98, "layak", 0.9)
    assert isinstance(teks, str) and teks.strip()
    assert "LAYAK" in teks


def test_label_cadangan_ditandai_saat_konfigurasi_tidak_sah(monkeypatch):
    """Bila keanggotaan tidak dapat dimuat, penjelasan tetap jalan TAPI mengaku memakai cadangan."""
    monkeypatch.setattr(explanation, "_kriteria", lambda: {})
    pen = explanation.susun_penjelasan(_features(400_000, 4, 0.7, 0.98), 0.98, "layak", 0.9)
    assert pen.sumber_label == explanation.SUMBER_LABEL_CADANGAN
    assert pen.teks.strip()
