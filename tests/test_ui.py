"""Tes penjaga antarmuka — Fase UI/UX.

Sampai sekarang **tidak ada satu pun tes yang memeriksa isi HTML**; seluruhnya hanya memeriksa
kode status. Akibatnya regresi tampilan tidak pernah tertangkap: pemanasan Tier 1 yang no-op dan
ramp meter yang terbalik keduanya lolos dari 105 tes hijau dan hanya tersingkap saat aplikasinya
dijalankan dan dilihat.

Tes di sini tidak mencoba menilai keindahan — yang dijaga adalah sifat yang bila rusak membuat
halaman **menyesatkan** atau **gagal tampil di tempat yang salah**:

  * tidak ada aset yang diambil dari internet (kalau bocor, halaman polos saat sidang);
  * penanda versi ketiga tier hadir di layar;
  * status selalu membawa kata, tidak pernah warna saja;
  * metrik menolak menampilkan angka saat pengamatannya nol.
"""
from __future__ import annotations

import re

import pytest

from app.services import grafik
from tests.conftest import payload

HALAMAN = ["/dashboard", "/daftar", "/peringkat", "/metrik", "/form"]


@pytest.fixture
def masuk(client):
    client.post(
        "/login", data={"username": "petugas", "password": "petugas123"}, follow_redirects=False
    )
    return client


# ---------------------------------------------------------------- aset lokal
@pytest.mark.parametrize("jalur", HALAMAN)
def test_tidak_ada_aset_dari_internet(masuk, jalur):
    """Satu rujukan CDN yang lolos = halaman tanpa gaya saat jaringan mati di ruang sidang."""
    html = masuk.get(jalur).text
    luar = re.findall(r'(?:src|href)="(https?://[^"]+)"', html)
    assert not luar, f"{jalur} memuat aset dari luar: {luar}"


def test_aset_vendor_benar_benar_dilayani(masuk):
    for aset in (
        "/static/vendor/bootstrap/bootstrap.min.css",
        "/static/vendor/bootstrap-icons/bootstrap-icons.min.css",
        "/static/vendor/htmx/htmx.min.js",
        "/static/vendor/font/inter-latin-wght-normal.woff2",
        "/static/favicon.svg",
    ):
        r = masuk.get(aset)
        assert r.status_code == 200 and len(r.content) > 400, aset


# ------------------------------------------------------------ penanda versi
@pytest.mark.parametrize("jalur", HALAMAN)
def test_penanda_versi_tier_tampil_di_setiap_halaman(masuk, jalur):
    """Tiga kegagalan senyap proyek ini hanya tersingkap oleh penanda versi — ia harus di layar."""
    html = masuk.get(jalur).text
    assert "tag-versi" in html, f"{jalur} tidak menampilkan penanda versi model"


# ------------------------------------------------------- status bukan warna
def test_status_membawa_kata_bukan_warna_saja(masuk, petugas_headers):
    masuk.post("/pengajuan", json=payload("7100000000000801"), headers=petugas_headers)
    html = masuk.get("/daftar").text
    assert "pill" in html
    for kata in ("Baru", "Dianalisis", "Diverifikasi"):
        if f">{kata}" in html or f"> {kata}" in html:
            break
    else:
        pytest.fail("tidak satu pun pil status membawa katanya")


# ------------------------------------------------- metrik menolak mengarang
def test_efektivitas_menolak_tampil_tanpa_pasangan(masuk):
    html = masuk.get("/metrik").text
    if "Belum dapat dihitung" in html:
        assert "0.0%" not in html.split("Efektivitas terhadap verifikasi manual")[1][:1200], (
            "efektivitas tampil sebagai 0% padahal belum ada pasangan"
        )


# --------------------------------------------------------- polling 5 detik
def test_ringkasan_menjawab_204_saat_angka_tidak_berubah(masuk):
    """Tanpa ini dashboard berkedip tiap 5 detik dan grafiknya tumbuh ulang selamanya."""
    html = masuk.get("/dashboard").text
    sig = re.search(r"sig=([0-9a-f]+)", html)
    assert sig, "blok ringkasan tidak membawa sidik isinya"
    assert masuk.get(f"/dashboard/ringkasan-partial?sig={sig.group(1)}").status_code == 204
    assert masuk.get("/dashboard/ringkasan-partial?sig=basi").status_code == 200


# ----------------------------------------------------------- ekspor & rute
def test_ekspor_csv_membawa_penanda_versi(masuk, petugas_headers):
    masuk.post("/pengajuan", json=payload("7100000000000802"), headers=petugas_headers)
    pid = masuk.get("/pengajuan", headers=petugas_headers).json()[0]["id"]
    masuk.post(f"/analisis/{pid}", headers=petugas_headers)
    masuk.post("/analisis/ranking", headers=petugas_headers)

    r = masuk.get("/peringkat/ekspor.csv")
    assert r.status_code == 200
    isi = r.text
    for kunci in ("# batch_id", "# versi_metode", "# versi_konfigurasi", "peringkat,pengajuan_id"):
        assert kunci in isi, f"CSV tidak memuat {kunci}"


def test_halaman_metrik_bukan_json(masuk):
    """Rute API /metrik/ringkasan pernah menutupi halaman web /metrik — jangan terulang."""
    assert "<html" in masuk.get("/metrik").text.lower()
    assert masuk.get("/metrik/ringkasan").json()["efisiensi"] is not None


# ------------------------------------------------------------------ grafik
def test_histogram_menempatkan_garis_potong_pada_nilai_yang_benar():
    nilai = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    s = grafik.histogram(nilai, bins=5, kuota=3)
    assert s.n == 10 and s.minimum == 0.1 and s.maksimum == 1.0
    assert s.nilai_potong == 0.8          # peringkat ke-3 dari atas
    assert 0 <= s.potong_persen <= 100
    assert sum(b.n for b in s.bins) == 10  # tidak ada nilai yang hilang dari bin mana pun


def test_histogram_tidak_mengarang_saat_data_kosong_atau_seragam():
    assert grafik.histogram([]).ada_isi is False
    assert grafik.histogram([0.5, 0.5, 0.5]).ada_isi is False


def test_komposisi_membuang_bagian_nol():
    potongan = grafik.komposisi([("A", 3), ("B", 0), ("C", 1)])
    assert [p.label for p in potongan] == ["A", "C"]
    assert abs(sum(p.persen for p in potongan) - 100) < 1e-9
    assert grafik.komposisi([("A", 0)]) == []
