"""Blackbox testing 7 skenario minimum TRD Bab 9.1."""
from __future__ import annotations

from tests.conftest import payload


# Skenario 1 — Login valid/invalid
def test_login_valid(client):
    r = client.post("/auth/login", data={"username": "petugas", "password": "petugas123"})
    assert r.status_code == 200
    assert r.json()["role"] == "petugas"


def test_login_invalid(client):
    r = client.post("/auth/login", data={"username": "petugas", "password": "salah"})
    assert r.status_code == 401


# Skenario 2 — Pengisian form lengkap tersimpan & muncul di daftar
def test_buat_dan_daftar(client, petugas_headers):
    r = client.post("/pengajuan", json=payload("1111000000000001"), headers=petugas_headers)
    assert r.status_code == 201, r.text
    pid = r.json()["id"]

    r2 = client.get("/pengajuan", headers=petugas_headers)
    assert r2.status_code == 200
    assert any(p["id"] == pid for p in r2.json())


# Skenario 3 — Validasi form menolak input tidak valid
def test_validasi_form_ditolak(client, petugas_headers):
    bad = payload("1111000000000002")
    bad["warga"]["nik"] = "123"  # < 8 karakter
    bad["data_survei"]["pendapatan"] = -5  # negatif
    r = client.post("/pengajuan", json=bad, headers=petugas_headers)
    assert r.status_code == 422


# Skenario 4 — Analisis satu pengajuan menghasilkan skor, prediksi, alasan
def test_analisis_satu(client, petugas_headers):
    pid = client.post(
        "/pengajuan", json=payload("1111000000000003"), headers=petugas_headers
    ).json()["id"]

    r = client.post(f"/analisis/{pid}", headers=petugas_headers)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["skor_urgensi"] is not None
    assert body["prediksi_ml"]["hasil"] in ("layak", "tidak_layak")
    assert body["alasan"]
    assert body["durasi_ms"] >= 0

    hasil = client.get(f"/hasil/{pid}", headers=petugas_headers).json()
    assert hasil["prediksi_ml"] is not None
    assert hasil["alasan"]


# Skenario 5 — Perangkingan batch menghasilkan daftar terurut
def test_ranking_terurut(client, petugas_headers):
    ids = []
    for i in range(4, 7):
        pid = client.post(
            "/pengajuan", json=payload(f"111100000000000{i}"), headers=petugas_headers
        ).json()["id"]
        client.post(f"/analisis/{pid}", headers=petugas_headers)
        ids.append(pid)

    r = client.post("/analisis/ranking", headers=petugas_headers)
    assert r.status_code == 200, r.text
    ranking = r.json()["ranking"]
    assert len(ranking) >= 2
    nilai = [it["nilai_preferensi"] for it in ranking]
    assert nilai == sorted(nilai, reverse=True)
    assert [it["peringkat"] for it in ranking] == list(range(1, len(ranking) + 1))


# Skenario 6 — Dashboard/ringkasan mencerminkan perubahan
def test_dashboard_ringkasan(client, petugas_headers):
    r = client.get("/dashboard/ringkasan", headers=petugas_headers)
    assert r.status_code == 200
    body = r.json()
    assert body["total_pengajuan"] >= 1
    assert body["dianalisis"] >= 1  # dari skenario 4/5


# Skenario 7 — Pembatasan akses: pemohon ditolak (403)
def test_akses_pemohon_ditolak(client, pemohon_headers, petugas_headers):
    pid = client.post(
        "/pengajuan", json=payload("1111000000000009"), headers=petugas_headers
    ).json()["id"]

    assert client.get("/pengajuan", headers=pemohon_headers).status_code == 403
    assert client.get(f"/hasil/{pid}", headers=pemohon_headers).status_code == 403
    # tanpa autentikasi -> 401
    assert client.get("/pengajuan").status_code == 401


# Verifikasi manual (FR-26) terekam
def test_verifikasi_manual(client, petugas_headers):
    pid = client.post(
        "/pengajuan", json=payload("1111000000000010"), headers=petugas_headers
    ).json()["id"]
    client.post(f"/analisis/{pid}", headers=petugas_headers)

    r = client.post(
        f"/verifikasi/{pid}", json={"hasil_manual": "layak"}, headers=petugas_headers
    )
    assert r.status_code == 200
    assert r.json()["status"] == "diverifikasi"


# Halaman web utama dapat diakses
def test_web_login_page(client):
    assert client.get("/login").status_code == 200


def test_web_root_redirect(client):
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (302, 303, 307)
