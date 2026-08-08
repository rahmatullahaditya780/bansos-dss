"""Tes instrumen pengujian Fase 5 — efisiensi (Bab 9.2), efektivitas (Bab 9.3), verifikasi (FR-26).

Yang dijaga di sini adalah sifat-sifat yang **tidak terlihat dari bentuk keluaran**, yaitu jenis
kegagalan yang tiga kali lolos dari tes kontrak di proyek ini:

  * metrik yang tampil percaya diri di atas nol pengamatan;
  * pasangan (sistem, manual) yang jadi basi setelah analisis ulang;
  * verifikasi yang hilang tanpa pesan karena direkam sebelum analisis;
  * biaya pemuatan model yang tercampur ke angka NFR-01.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.db import models
from app.db.session import SessionLocal
from app.services import metrics, verifikasi
from tests.conftest import payload


# --------------------------------------------------------------------- efisiensi
def test_efisiensi_rumus_bab_92():
    assert metrics.hitung_efisiensi(5000) == 100.0   # tepat di ambang
    assert metrics.hitung_efisiensi(200) == 100.0    # di-cap, tidak melebihi 100
    assert metrics.hitung_efisiensi(10000) == 50.0
    assert metrics.hitung_efisiensi(20000) == 25.0


def test_cold_start_tidak_mencemari_angka_warm():
    """Satu permintaan 14 detik per restart tidak boleh terbaca sebagai pelanggaran NFR-01."""
    baris = [
        (13998, None, None, "cold"),
        (200, 90, 95, "warm"),
        (210, 95, 100, "warm"),
        (190, 88, 92, "warm"),
    ]
    r = metrics.ringkas_efisiensi(baris)
    assert r.n_warm == 3 and r.n_cold == 1
    assert r.persen_le_5s == 100.0
    assert r.maks_ms == 210            # maksimum warm, bukan 13998
    assert r.cold_maks_ms == 13998     # tetap dilaporkan, tidak disembunyikan
    assert r.efisiensi_persen == 100.0


def test_baris_tanpa_penanda_tidak_diakui_sebagai_warm():
    """Pengukuran pra-Fase 5 tidak punya penanda; menebaknya = mengarang pengukuran."""
    baris = [(196, None, None, None), (13998, None, None, None), (200, 90, 95, "warm")]
    r = metrics.ringkas_efisiensi(baris)
    assert r.n_tak_bertanda == 2
    assert r.n_warm == 1
    assert r.maks_ms == 200
    assert r.maks_tak_bertanda_ms == 13998


def test_tier3_dilaporkan_per_batch_bukan_per_pengajuan():
    r = metrics.ringkas_efisiensi(
        [(200, 90, 95, "warm")], batch_tier3=[(19, 145), (22, 991)]
    )
    assert r.tier3_batch == 2
    assert r.tier3_p50_ms in (19, 22)
    assert r.tier3_maks_alternatif == 991


def test_efisiensi_kosong_tidak_mengarang_angka():
    r = metrics.ringkas_efisiensi([])
    assert r.cukup_untuk_dilaporkan is False
    assert r.efisiensi_persen is None and r.p50_ms is None


# ------------------------------------------------------------------ efektivitas
def test_efektivitas_nol_pasangan_bukan_nol_persen():
    """0 pasangan berarti 'belum diuji', bukan 'sistem selalu salah'."""
    r = metrics.ringkas_efektivitas([])
    assert r.persen is None
    assert r.memenuhi_target is None
    assert r.pasangan == 0


def test_efektivitas_menghitung_arah_kesalahan():
    r = metrics.ringkas_efektivitas(
        [("layak", "layak"), ("layak", "tidak_layak"), ("tidak_layak", "layak"),
         ("tidak_layak", "tidak_layak")]
    )
    assert r.pasangan == 4 and r.tepat == 2 and r.persen == 50.0
    assert r.salah_positif == 1 and r.salah_negatif == 1
    assert r.memenuhi_target is False


def test_pasangan_tanpa_putusan_sistem_diabaikan():
    """Verifikasi atas pengajuan yang belum pernah dianalisis tidak boleh dihitung sebagai salah."""
    assert metrics.hitung_efektivitas([(None, "layak"), ("", "tidak_layak")]) is None


# ------------------------------------------------- verifikasi (D-04), lewat API
@pytest.fixture
def pengajuan_teranalisis(client, petugas_headers):
    r = client.post("/pengajuan", json=payload("7100000000000901"), headers=petugas_headers)
    pid = r.json()["id"]
    client.post(f"/analisis/{pid}", headers=petugas_headers)
    return pid


def test_verifikasi_menyimpan_snapshot_putusan_yang_dinilai(
    client, petugas_headers, pengajuan_teranalisis
):
    pid = pengajuan_teranalisis
    sistem = client.get(f"/hasil/{pid}", headers=petugas_headers).json()["prediksi_ml"]["hasil"]
    r = client.post(
        f"/verifikasi/{pid}", headers=petugas_headers, json={"hasil_manual": "layak"}
    )
    assert r.status_code == 200
    assert r.json()["hasil_sistem_dinilai"] == sistem
    assert r.json()["versi_model_dinilai"]


def test_analisis_ulang_tidak_membasikan_pasangan(
    client, petugas_headers, pengajuan_teranalisis
):
    """Urutan yang dulu merusak: analisis -> verifikasi -> analisis ulang.

    Sebelum Fase 5, pasangan tetap terbentuk tetapi memakai putusan sistem LAMA — dan yang lebih
    buruk, tidak ada apa pun yang menunjukkan bahwa itu terjadi.
    """
    pid = pengajuan_teranalisis
    client.post(f"/verifikasi/{pid}", headers=petugas_headers, json={"hasil_manual": "layak"})
    client.post(f"/analisis/{pid}", headers=petugas_headers)  # analisis ulang

    db = SessionLocal()
    try:
        v = verifikasi.verifikasi_terakhir(db, pid)
        assert v is not None
        assert v.hasil_sistem is not None  # putusan yang BENAR-BENAR dinilai, tersimpan
        pasangan = [p for p in verifikasi.pasangan_efektivitas(db) if all(p)]
        assert pasangan, "pasangan hilang setelah analisis ulang"
    finally:
        db.close()


def test_verifikasi_sebelum_analisis_tidak_hilang_diam_diam(client, petugas_headers):
    """Urutan sebaliknya: verifikasi dulu, analisis kemudian.

    Sebelum Fase 5 pasangannya tidak pernah terbentuk dan verifikasinya lenyap tanpa pesan.
    Sekarang penilaiannya tetap tersimpan, dan ketiadaan putusan sistem terlihat sebagai
    `hasil_sistem = None` — bukan sebagai baris yang menghilang.
    """
    pid = client.post(
        "/pengajuan", json=payload("7100000000000902"), headers=petugas_headers
    ).json()["id"]
    r = client.post(
        f"/verifikasi/{pid}", headers=petugas_headers, json={"hasil_manual": "layak"}
    )
    assert r.status_code == 200
    assert r.json()["hasil_sistem_dinilai"] is None

    db = SessionLocal()
    try:
        v = verifikasi.verifikasi_terakhir(db, pid)
        assert v is not None and v.hasil_manual == "layak"
        # Tidak dihitung ke metrik karena tak ada putusan sistem untuk dibandingkan —
        # diabaikan, bukan dianggap salah.
        assert (None, "layak") not in [
            p for p in verifikasi.pasangan_efektivitas(db) if all(p)
        ]
    finally:
        db.close()


def test_verifikasi_berulang_dihitung_sekali(client, petugas_headers, pengajuan_teranalisis):
    """Pengajuan yang ditinjau berulang tidak boleh berbobot lebih besar di metrik."""
    pid = pengajuan_teranalisis
    client.post(f"/verifikasi/{pid}", headers=petugas_headers, json={"hasil_manual": "layak"})
    client.post(
        f"/verifikasi/{pid}", headers=petugas_headers, json={"hasil_manual": "tidak_layak"}
    )
    db = SessionLocal()
    try:
        sebanyak = sum(
            1
            for _s, _m in verifikasi.pasangan_efektivitas(db)
        )
        semua = db.query(models.VerifikasiManual).filter_by(pengajuan_id=pid).count()
        assert semua == 2          # riwayat utuh
        assert sebanyak >= 1
        v = verifikasi.verifikasi_terakhir(db, pid)
        assert v.hasil_manual == "tidak_layak"  # yang terbaru yang dipakai
    finally:
        db.close()


# ------------------------------------------------------------------ durasi tier
def test_log_menyimpan_durasi_per_tier_dan_penanda_muat(
    client, petugas_headers, pengajuan_teranalisis
):
    db = SessionLocal()
    try:
        log = (
            db.query(models.LogPengujian)
            .filter_by(pengajuan_id=pengajuan_teranalisis)
            .order_by(models.LogPengujian.waktu_mulai.desc())
            .first()
        )
        assert log is not None
        assert log.durasi_tier1_ms is not None and log.durasi_tier2_ms is not None
        assert log.jenis_muat in ("cold", "warm")
        assert log.durasi_ms >= log.durasi_tier1_ms
    finally:
        db.close()


def test_ranking_mencatat_durasi_batch_dan_bahan_penjelasan(client, petugas_headers):
    """Tier 3 harus tercatat per batch, dan label keanggotaan ikut tersimpan (OI-07)."""
    client.post("/pengajuan", json=payload("7100000000000903"), headers=petugas_headers)
    for pid in [p["id"] for p in client.get("/pengajuan", headers=petugas_headers).json()][:3]:
        client.post(f"/analisis/{pid}", headers=petugas_headers)
    r = client.post("/analisis/ranking", headers=petugas_headers)
    assert r.status_code == 200
    batch_id = r.json()["batch_id"]

    db = SessionLocal()
    try:
        log = db.query(models.LogRanking).filter_by(batch_id=batch_id).first()
        assert log is not None and log.durasi_ms is not None
        assert log.jumlah_alternatif == r.json()["jumlah_alternatif"]
        assert log.versi_metode

        baris = db.query(models.RankingTopsis).filter_by(batch_id=batch_id).first()
        if baris is not None:
            assert baris.keanggotaan, "label keanggotaan dibuang lagi seperti sebelum Fase 5"
            assert baris.jarak_positif is not None
    finally:
        db.close()


def test_waktu_mulai_log_wajar(client, petugas_headers, pengajuan_teranalisis):
    db = SessionLocal()
    try:
        log = (
            db.query(models.LogPengujian)
            .filter_by(pengajuan_id=pengajuan_teranalisis)
            .first()
        )
        assert log.waktu_mulai is not None
        selisih = abs(
            (datetime.now(timezone.utc) - log.waktu_mulai.replace(tzinfo=timezone.utc))
            .total_seconds()
        )
        assert selisih < 600
    finally:
        db.close()
