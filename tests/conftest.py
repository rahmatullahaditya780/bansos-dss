"""Fixtures pytest: DB SQLite terisolasi + TestClient + token peran."""
from __future__ import annotations

import os

# Set env SEBELUM mengimpor modul app (agar engine memakai DB uji terpisah).
os.environ["DATABASE_URL"] = "sqlite:///./test_bansos.db"
os.environ["SECRET_KEY"] = "test-secret-key-that-is-at-least-32-bytes-long"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.core.security import get_password_hash  # noqa: E402
from app.db import models  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.add(
        models.User(
            username="petugas", password_hash=get_password_hash("petugas123"),
            role=models.Role.PETUGAS, nama="Petugas",
        )
    )
    db.add(
        models.User(
            username="pemohon", password_hash=get_password_hash("pemohon123"),
            role=models.Role.PEMOHON, nama="Pemohon",
        )
    )
    db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    try:
        os.remove("test_bansos.db")
    except OSError:
        pass


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _token(client: TestClient, username: str, password: str) -> str:
    r = client.post("/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


@pytest.fixture
def petugas_headers(client: TestClient) -> dict:
    return {"Authorization": f"Bearer {_token(client, 'petugas', 'petugas123')}"}


@pytest.fixture
def pemohon_headers(client: TestClient) -> dict:
    return {"Authorization": f"Bearer {_token(client, 'pemohon', 'pemohon123')}"}


def payload(nik: str, *, miskin: bool = True) -> dict:
    """Bangun payload pengajuan valid. miskin=True -> cenderung diprediksi 'layak'."""
    if miskin:
        return {
            "warga": {
                "nik": nik, "nama": "Warga Uji", "usia": 45, "jenis_kelamin": "L",
                "status_pernikahan": "Kawin", "jumlah_tanggungan": 5, "alamat": "Dusun A",
            },
            "data_survei": {
                "pendapatan": 300000, "status_pekerjaan": "Buruh tani", "aset_produktif": False,
                "riwayat_bantuan": False, "luas_rumah": 20, "jenis_lantai": "tanah",
                "jenis_dinding": "bambu", "sumber_air": "sungai",
            },
            "teks_naratif": [
                {"sumber": "petugas",
                 "isi_teks": "kepala keluarga sakit kronis dan rumah gubuk nyaris roboh, anak putus sekolah"}
            ],
        }
    return {
        "warga": {
            "nik": nik, "nama": "Warga Mampu", "usia": 40, "jenis_kelamin": "P",
            "status_pernikahan": "Kawin", "jumlah_tanggungan": 0, "alamat": "Perumahan B",
        },
        "data_survei": {
            "pendapatan": 6000000, "status_pekerjaan": "Karyawan swasta", "aset_produktif": True,
            "riwayat_bantuan": False, "luas_rumah": 80, "jenis_lantai": "keramik",
            "jenis_dinding": "tembok", "sumber_air": "pdam",
        },
        "teks_naratif": [
            {"sumber": "petugas", "isi_teks": "kondisi ekonomi keluarga stabil dan memadai"}
        ],
    }
