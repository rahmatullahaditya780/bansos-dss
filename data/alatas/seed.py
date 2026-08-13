"""Masukkan data publik Alatas dkk. (2012) ke basis data.

Jalankan setelah `alembic upgrade head` dan setelah arsip Dataverse diekstrak:

    python -m data.alatas.seed                  # label musyawarah (default), 3.788 RT
    python -m data.alatas.seed --batas 200      # sebagian, untuk uji cepat
    python -m data.alatas.seed --label poor     # varian BOCOR, hanya untuk demonstrasi
    python -m data.alatas.seed --deflator 2.6   # skala rupiah 2008 → tahun rujukan

DUA VARIAN LABEL, dibedakan lewat kolom `asal_data` sehingga tidak dapat tertukar sampai ke CSV
korpus dan metadata artefak:

    musyawarah → asal_data='publik-musy'   (default; label dari peringkat musyawarah warga)
    poor       → asal_data='publik'        (ambang konsumsi — BOCOR terhadap fitur `pendapatan`)

Seeder MENOLAK mencampur keduanya dalam satu basis data tanpa `--force`, karena korpus berlabel
campuran tidak akan memunculkan galat apa pun saat diekspor maupun dilatih.

TIDAK ADA `TeksNaratif` YANG DIBUAT — sumbernya tidak punya teks naratif sama sekali. Ekspornya
karena itu wajib memakai `--tanpa-urgensi` (ablasi 6 fitur); tanpa itu seluruh baris gugur dengan
alasan `tanpa_skor_urgensi`. Ketiadaan fitur ketujuh harus dinyatakan lewat mode yang eksplisit,
bukan diisi nilai netral diam-diam.
"""
from __future__ import annotations

import argparse

from sqlalchemy import func, select

from app.db import models
from app.db.session import SessionLocal
from data.alatas.harmonisasi import (
    AKAR_BAWAAN,
    LABEL_MUSYAWARAH,
    LABEL_POOR,
    asal_data_untuk,
    muat_records,
    ringkasan,
)
from data.synthetic.seed import ensure_users


def _sudah_ada(db, asal: str) -> int:
    return db.execute(
        select(func.count())
        .select_from(models.DataSurvei)
        .where(models.DataSurvei.asal_data == asal)
    ).scalar_one()


def _asal_lain(db, asal: str) -> list[str]:
    """Varian label publik LAIN yang sudah ada di basis data.

    Mencampur dua pelabelan berarti mengekspor korpus yang separuhnya berlabel konsumsi dan
    separuhnya berlabel musyawarah — tanpa satu pun galat. Dicegah di sini, berisik.
    """
    semua = {asal_data_untuk(l) for l in (LABEL_POOR, LABEL_MUSYAWARAH)} - {asal}
    return [a for a in sorted(semua) if _sudah_ada(db, a) > 0]


def seed(
    *,
    akar: str = str(AKAR_BAWAAN),
    label: str = LABEL_MUSYAWARAH,
    gelombang_blt: str = "2005",
    deflator: float = 1.0,
    batas: int | None = None,
    force: bool = False,
) -> int:
    asal = asal_data_untuk(label)
    records = muat_records(akar, label=label, gelombang_blt=gelombang_blt, deflator=deflator)
    if batas:
        records = records[:batas]

    db = SessionLocal()
    try:
        lain = _asal_lain(db, asal)
        if lain and not force:
            raise SystemExit(
                f"Basis data sudah berisi varian label publik lain: {lain}.\n"
                f"  Mencampurnya dengan '{asal}' menghasilkan korpus berlabel campuran tanpa\n"
                "  galat apa pun. Kosongkan basis data lebih dulu, atau pakai --force bila\n"
                "  memang sengaja."
            )
        ada = _sudah_ada(db, asal)
        if ada > 0 and not force:
            print(
                f"Sudah ada {ada} baris asal_data='{asal}'; seeding dilewati "
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
                    asal_data=asal,
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
    ap.add_argument(
        "--label",
        default=LABEL_MUSYAWARAH,
        choices=[LABEL_MUSYAWARAH, LABEL_POOR],
        help="musyawarah (default, aman) | poor (BOCOR terhadap fitur `pendapatan`)",
    )
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

    asal = asal_data_untuk(args.label)
    records = muat_records(
        args.akar, label=args.label, gelombang_blt=args.gelombang_blt, deflator=args.deflator
    )
    if args.batas:
        records = records[: args.batas]
    print(f"Label    : {args.label}  →  asal_data='{asal}'")
    if args.label == LABEL_POOR:
        print(
            "  ⚠ PERINGATAN: `poor` adalah ambang atas CONSUMPTION, sedangkan `pendapatan`\n"
            "    = CONSUMPTION × 1.000. Labelnya fungsi dari fiturnya sendiri (cocok 99,97%).\n"
            "    Metrik dari varian ini TIDAK boleh dilaporkan sebagai kinerja."
        )
    print("Ringkasan sumber:")
    for k, v in ringkasan(records).items():
        print(f"  {k:<24} {v}")

    n = seed(
        akar=args.akar,
        label=args.label,
        gelombang_blt=args.gelombang_blt,
        deflator=args.deflator,
        batas=args.batas,
        force=args.force,
    )
    if n:
        print(f"\nSelesai: {n} pengajuan asal_data='{asal}' ditambahkan.")
        print(
            "\nCATATAN: tidak ada TeksNaratif untuk baris-baris ini (sumbernya tanpa teks).\n"
            f"Ekspor dengan:\n"
            f"  python -m ml.tier2.dataset --asal-data {asal} --tanpa-urgensi"
        )


if __name__ == "__main__":
    main()
