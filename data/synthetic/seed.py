"""Isi database dengan akun demo + data pengajuan simulasi.

Jalankan setelah `alembic upgrade head`:
    python -m data.synthetic.seed            # 12 pengajuan
    python -m data.synthetic.seed 30         # 30 pengajuan
    python -m data.synthetic.seed 30 --force # paksa tambah walau sudah ada data
"""
from __future__ import annotations

import argparse

from sqlalchemy import func, select

from app.core.security import get_password_hash
from app.db import models
from app.db.session import SessionLocal
from data.synthetic.generator import generate_records

DEMO_USERS = [
    {"username": "petugas", "password": "petugas123", "role": models.Role.PETUGAS, "nama": "Petugas Kelurahan"},
    {"username": "pemohon", "password": "pemohon123", "role": models.Role.PEMOHON, "nama": "Warga Pemohon"},
]


def ensure_users(db) -> models.User:
    petugas = None
    for u in DEMO_USERS:
        existing = db.execute(
            select(models.User).where(models.User.username == u["username"])
        ).scalar_one_or_none()
        if existing is None:
            existing = models.User(
                username=u["username"],
                password_hash=get_password_hash(u["password"]),
                role=u["role"],
                nama=u["nama"],
            )
            db.add(existing)
            db.flush()
        if u["role"] == models.Role.PETUGAS:
            petugas = existing
    db.commit()
    return petugas


def seed(n: int, force: bool) -> None:
    db = SessionLocal()
    try:
        petugas = ensure_users(db)

        existing = db.execute(select(func.count()).select_from(models.Pengajuan)).scalar_one()
        if existing > 0 and not force:
            print(f"Sudah ada {existing} pengajuan; lewati seeding data (pakai --force untuk menambah).")
            print("Akun demo dipastikan tersedia: petugas/petugas123, pemohon/pemohon123")
            return

        records = generate_records(n)
        for r in records:
            warga = db.execute(
                select(models.Warga).where(models.Warga.nik == r["nik"])
            ).scalar_one_or_none()
            if warga is None:
                warga = models.Warga(
                    nik=r["nik"], nama=r["nama"], usia=r["usia"],
                    jenis_kelamin=r["jenis_kelamin"], status_pernikahan=r["status_pernikahan"],
                    jumlah_tanggungan=r["jumlah_tanggungan"], alamat=r["alamat"],
                )
                db.add(warga)
                db.flush()

            pengajuan = models.Pengajuan(
                warga_id=warga.id, dibuat_oleh=petugas.id, status=models.StatusPengajuan.BARU
            )
            db.add(pengajuan)
            db.flush()

            db.add(
                models.DataSurvei(
                    pengajuan_id=pengajuan.id, asal_data="sintetis",
                    pendapatan=r["pendapatan"], status_pekerjaan=r["status_pekerjaan"],
                    aset_produktif=r["aset_produktif"], riwayat_bantuan=r["riwayat_bantuan"],
                    luas_rumah=r["luas_rumah"], jenis_lantai=r["jenis_lantai"],
                    jenis_dinding=r["jenis_dinding"], sumber_air=r["sumber_air"],
                    label_historis=r["label_historis"],
                )
            )
            db.add(
                models.TeksNaratif(
                    pengajuan_id=pengajuan.id, sumber=models.SumberNaratif.PETUGAS,
                    isi_teks=r["narasi"], label_urgensi_manual=r["label_urgensi"],
                )
            )
        db.commit()
        print(f"Seed selesai: {len(records)} pengajuan ditambahkan.")
        print("Akun demo: petugas/petugas123 (petugas), pemohon/pemohon123 (pemohon)")
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed data simulasi DSS Bansos")
    parser.add_argument("n", nargs="?", type=int, default=12, help="jumlah pengajuan (default 12)")
    parser.add_argument("--force", action="store_true", help="tambah data walau sudah ada")
    args = parser.parse_args()
    seed(args.n, args.force)
