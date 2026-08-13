"""Masukkan data publik Alatas dkk. (2012) ke basis data dengan `asal_data='publik'`.

Jalankan setelah `alembic upgrade head` dan setelah arsip Dataverse diekstrak:

    python -m data.alatas.seed                  # seluruh 5.753 rumah tangga
    python -m data.alatas.seed --batas 200      # sebagian, untuk uji cepat
    python -m data.alatas.seed --force          # tambah walau data publik sudah ada
    python -m data.alatas.seed --deflator 2.6   # skala rupiah 2008 → tahun rujukan

TIDAK ADA `TeksNaratif` YANG DIBUAT — sumbernya tidak punya teks naratif sama sekali. Akibatnya
`python -m ml.tier2.dataset --asal-data publik` akan melewatkan SELURUH baris ini dengan alasan
`tanpa_skor_urgensi` lalu berhenti tanpa menulis apa pun. Itu perilaku yang benar dan disengaja:
run Tier 2 di data publik adalah ablasi 6 fitur, dan ketiadaan fitur ketujuh harus dinyatakan
lewat mode yang eksplisit, bukan diisi nilai netral diam-diam.
"""
from __future__ import annotations

import argparse

from sqlalchemy import func, select

from app.db import models
from app.db.session import SessionLocal
from data.alatas.harmonisasi import AKAR_BAWAAN, ASAL_DATA, muat_records, ringkasan
from data.synthetic.seed import ensure_users


def _sudah_ada(db) -> int:
    return db.execute(
        select(func.count())
        .select_from(models.DataSurvei)
        .where(models.DataSurvei.asal_data == ASAL_DATA)
    ).scalar_one()


def seed(
    *,
    akar: str = str(AKAR_BAWAAN),
    gelombang_blt: str = "2005",
    deflator: float = 1.0,
    batas: int | None = None,
    force: bool = False,
) -> int:
    records = muat_records(akar, gelombang_blt=gelombang_blt, deflator=deflator)
    if batas:
        records = records[:batas]

    db = SessionLocal()
    try:
        ada = _sudah_ada(db)
        if ada > 0 and not force:
            print(
                f"Sudah ada {ada} baris asal_data='{ASAL_DATA}'; seeding dilewati "
                "(pakai --force untuk menambah)."
            )
            return 0

        petugas = ensure_users(db)
        ditambah = 0
        for r in records:
            warga = db.execute(
                select(models.Warga).where(models.Warga.nik == r["nik"])
            ).scalar_one_or_none()
            if warga is None:
                warga = models.Warga(
                    nik=r["nik"],
                    nama=r["nama"],
                    usia=r["usia"],
                    jenis_kelamin=r["jenis_kelamin"],
                    status_pernikahan=r["status_pernikahan"],
                    jumlah_tanggungan=r["jumlah_tanggungan"],
                    alamat=r["alamat"],
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
                    pengajuan_id=pengajuan.id,
                    asal_data=ASAL_DATA,
                    pendapatan=r["pendapatan"],
                    status_pekerjaan=r["status_pekerjaan"],
                    aset_produktif=r["aset_produktif"],
                    riwayat_bantuan=r["riwayat_bantuan"],
                    luas_rumah=r["luas_rumah"],
                    jenis_lantai=r["jenis_lantai"],
                    jenis_dinding=r["jenis_dinding"],
                    sumber_air=r["sumber_air"],
                    label_historis=r["label_historis"],
                )
            )
            ditambah += 1
            if ditambah % 500 == 0:
                print(f"  {ditambah}/{len(records)} ...")

        db.commit()
        return ditambah
    finally:
        db.close()


def main() -> None:
    ap = argparse.ArgumentParser(description="Seed data publik Alatas dkk. (2012)")
    ap.add_argument("--akar", default=str(AKAR_BAWAAN))
    ap.add_argument("--gelombang-blt", default="2005", choices=["2005", "2008"])
    ap.add_argument(
        "--deflator",
        type=float,
        default=1.0,
        help="pengali rupiah 2008 (default 1.0 = tetap nominal 2008)",
    )
    ap.add_argument("--batas", type=int, default=None)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    records = muat_records(args.akar, gelombang_blt=args.gelombang_blt, deflator=args.deflator)
    if args.batas:
        records = records[: args.batas]
    print("Ringkasan sumber:")
    for k, v in ringkasan(records).items():
        print(f"  {k:<24} {v}")

    n = seed(
        akar=args.akar,
        gelombang_blt=args.gelombang_blt,
        deflator=args.deflator,
        batas=args.batas,
        force=args.force,
    )
    if n:
        print(f"\nSelesai: {n} pengajuan asal_data='{ASAL_DATA}' ditambahkan.")
        print(
            "\nCATATAN: tidak ada TeksNaratif untuk baris-baris ini (sumbernya tanpa teks).\n"
            "`python -m ml.tier2.dataset --asal-data publik` akan melewatkan semuanya dengan\n"
            "alasan `tanpa_skor_urgensi` sampai mode tanpa-urgensi yang eksplisit ditambahkan."
        )


if __name__ == "__main__":
    main()
