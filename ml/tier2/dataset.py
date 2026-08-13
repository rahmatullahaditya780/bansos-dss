"""Ekspor dataset Tier 2 dari basis data + split latih:uji 80:20 tanpa kebocoran.

**Kebocoran dicegah dengan mengelompokkan baris per warga, bukan per pengajuan.** Seorang warga
dapat mengajukan lebih dari sekali dan pengajuannya nyaris identik fiturnya; split acak per baris
akan menempatkan kembaran di kedua sisi dan menaikkan akurasi secara semu. Ini masalah yang sama
dengan kembaran teks di Tier 1, dengan kunci grup yang berbeda.

Split juga *stratified* per label agar proporsi layak/tidak_layak sama di kedua sisi, dan
deterministik terhadap `seed`.

Skor urgensi (fitur Tier 1 → Tier 2) diambil dengan dua cara, dipilih lewat `--skor-urgensi`:

- `hitung`    : skor dihitung sekarang lewat model Tier 1 (satu forward pass per potongan).
                Dipakai saat data hasil seeding belum pernah dianalisis. **Default.**
- `tersimpan` : memakai baris `skor_urgensi` yang sudah ada di basis data (hasil `POST /analisis`).
                Pengajuan yang belum dianalisis dilewati dan jumlahnya dilaporkan.

Pemakaian:
    python -m ml.tier2.dataset --outdir data/corpus --asal-data sintetis
"""
from __future__ import annotations

import argparse
import csv
import random
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from ml.tier2 import FITUR, FITUR_TANPA_URGENSI, ID2LABEL, LABEL2ID, nama_set_fitur

UKURAN_POTONGAN_SKOR = 64  # jumlah narasi per forward pass Tier 1


@dataclass
class Baris:
    """Satu pengajuan berlabel, siap dijadikan vektor fitur."""

    warga_id: int            # kunci grup split — bukan pengajuan_id
    pengajuan_id: int
    label: str               # 'layak' | 'tidak_layak'
    asal_data: str           # 'sintetis' | 'publik' | 'lokal'
    fitur: dict[str, float] = field(default_factory=dict)

    @property
    def label_id(self) -> int:
        return LABEL2ID[self.label]


# --------------------------------------------------------------------------- basis data
def _skor_urgensi_tersimpan(pengajuan) -> float | None:
    skor = [t.skor_urgensi.skor for t in pengajuan.teks_naratif if t.skor_urgensi is not None]
    return max(skor) if skor else None


def muat_dari_db(
    *,
    skor_urgensi: str = "hitung",
    asal_data: str | None = None,
    batas: int | None = None,
    tanpa_urgensi: bool = False,
) -> tuple[list[Baris], dict[str, int]]:
    """Baca pengajuan berlabel dari basis data. Kembalikan (baris, statistik pelewatan).

    `tanpa_urgensi=True` merakit vektor ablasi enam fitur: `skor_urgensi` DIHILANGKAN dari dict
    fitur (bukan diisi nilai netral), dan pengajuan tanpa teks naratif tidak lagi dibuang. Dipakai
    untuk data publik yang memang tidak punya narasi.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.db import models
    from app.db.session import SessionLocal
    from app.services.features import build_features

    lewat = {"tanpa_label": 0, "tanpa_survei": 0, "tanpa_skor_urgensi": 0}
    db = SessionLocal()
    try:
        q = (
            select(models.Pengajuan)
            .options(
                selectinload(models.Pengajuan.warga),
                selectinload(models.Pengajuan.data_survei),
                selectinload(models.Pengajuan.teks_naratif).selectinload(
                    models.TeksNaratif.skor_urgensi
                ),
            )
            .join(models.DataSurvei)
            .order_by(models.Pengajuan.id)
        )
        if asal_data:
            q = q.where(models.DataSurvei.asal_data == asal_data)
        if batas:
            q = q.limit(batas)
        pengajuan = list(db.execute(q).scalars().all())

        kandidat = []
        for p in pengajuan:
            if p.data_survei is None:
                lewat["tanpa_survei"] += 1
                continue
            if p.data_survei.label_historis is None:
                lewat["tanpa_label"] += 1
                continue
            kandidat.append(p)

        urgensi = {} if tanpa_urgensi else _kumpulkan_urgensi(kandidat, skor_urgensi, lewat)

        baris: list[Baris] = []
        for p in kandidat:
            if not tanpa_urgensi and p.id not in urgensi:
                continue
            s = p.data_survei
            baris.append(
                Baris(
                    warga_id=p.warga_id,
                    pengajuan_id=p.id,
                    label=ID2LABEL[int(bool(s.label_historis))],
                    asal_data=s.asal_data,
                    fitur=build_features(
                        pendapatan=s.pendapatan,
                        jumlah_tanggungan=p.warga.jumlah_tanggungan,
                        usia=p.warga.usia,
                        aset_produktif=s.aset_produktif,
                        riwayat_bantuan=s.riwayat_bantuan,
                        jenis_lantai=s.jenis_lantai,
                        jenis_dinding=s.jenis_dinding,
                        sumber_air=s.sumber_air,
                        luas_rumah=s.luas_rumah,
                        # None → kunci `skor_urgensi` tidak ikut dirakit sama sekali.
                        skor_urgensi=None if tanpa_urgensi else urgensi[p.id],
                    ),
                )
            )
        return baris, lewat
    finally:
        db.close()


def _kumpulkan_urgensi(kandidat, mode: str, lewat: dict[str, int]) -> dict[int, float]:
    """Peta pengajuan_id → skor urgensi (maksimum antar narasi, seperti di `pipeline.py`)."""
    if mode == "tersimpan":
        hasil = {}
        for p in kandidat:
            skor = _skor_urgensi_tersimpan(p)
            if skor is None:
                lewat["tanpa_skor_urgensi"] += 1
            else:
                hasil[p.id] = skor
        return hasil

    if mode != "hitung":
        raise ValueError(f"mode skor urgensi tidak dikenal: {mode!r} (pilih 'hitung'/'tersimpan')")

    from app.services.tier1_nlp import score_urgency_batch

    # Kumpulkan seluruh narasi lebih dulu, lalu skor per potongan — bukan per pengajuan —
    # agar jumlah forward pass sebanding dengan jumlah narasi, bukan jumlah pengajuan.
    pemilik: list[int] = []
    teks: list[str] = []
    for p in kandidat:
        for t in p.teks_naratif:
            pemilik.append(p.id)
            teks.append(t.isi_teks)

    hasil: dict[int, float] = {}
    for awal in range(0, len(teks), UKURAN_POTONGAN_SKOR):
        potongan = teks[awal : awal + UKURAN_POTONGAN_SKOR]
        for pid, out in zip(pemilik[awal : awal + UKURAN_POTONGAN_SKOR], score_urgency_batch(potongan)):
            hasil[pid] = max(hasil.get(pid, 0.0), out.skor)
        print(f"  skor urgensi: {min(awal + UKURAN_POTONGAN_SKOR, len(teks))}/{len(teks)} narasi")

    for p in kandidat:
        if p.id not in hasil:
            lewat["tanpa_skor_urgensi"] += 1
    return hasil


# --------------------------------------------------------------------------- CSV
KOLOM_META = ["pengajuan_id", "warga_id", "label", "label_id", "asal_data"]


def kolom(fitur: list[str] = FITUR) -> list[str]:
    return [*KOLOM_META, *fitur]


# Nama lama dipertahankan agar pemanggil yang sudah ada tidak perlu diubah.
KOLOM = kolom(FITUR)


def fitur_csv(path: str | Path) -> list[str]:
    """Baca himpunan fitur dari HEADER berkas, bukan dari `ml.tier2.FITUR`.

    Ini yang membuat berkas ablasi dan berkas lengkap tidak dapat tertukar: himpunan fiturnya
    melekat pada berkasnya sendiri, dan `nama_set_fitur` menolak apa pun yang bukan salah satu
    dari dua bentuk sah.
    """
    path = Path(path)
    with path.open(encoding="utf-8", newline="") as f:
        header = next(csv.reader(f), None)
    if not header:
        raise ValueError(f"Dataset kosong: {path}")
    kurang = [k for k in KOLOM_META if k not in header]
    if kurang:
        raise ValueError(f"Kolom {kurang} tidak ada di {path} (ada: {header})")
    sisa = [k for k in header if k not in KOLOM_META]
    try:
        nama_set_fitur(sisa)
    except ValueError as exc:
        raise ValueError(f"{path}: {exc}") from exc
    return sisa


def tulis_csv(baris: list[Baris], path: str | Path, fitur: list[str] = FITUR) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(kolom(fitur))
        for b in baris:
            w.writerow(
                [b.pengajuan_id, b.warga_id, b.label, b.label_id, b.asal_data]
                + [b.fitur[k] for k in fitur]
            )
    return path


def muat_csv(path: str | Path) -> list[Baris]:
    path = Path(path)
    fitur = fitur_csv(path)
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"Dataset kosong: {path}")

    baris = []
    for r in rows:
        label = (r["label"] or "").strip().lower()
        if label not in LABEL2ID:
            raise ValueError(f"Label tidak dikenal: {label!r} (harus {list(LABEL2ID)})")
        baris.append(
            Baris(
                warga_id=int(r["warga_id"]),
                pengajuan_id=int(r["pengajuan_id"]),
                label=label,
                asal_data=(r.get("asal_data") or "sintetis").strip(),
                fitur={k: float(r[k]) for k in fitur},
            )
        )
    return baris


# --------------------------------------------------------------------------- split
def split_80_20(
    baris: list[Baris], test_size: float = 0.2, seed: int = 42
) -> tuple[list[Baris], list[Baris]]:
    """Bagi stratified per label, dengan seluruh pengajuan satu warga tidak terpecah antar split."""
    grup: dict[int, list[Baris]] = defaultdict(list)
    for b in baris:
        grup[b.warga_id].append(b)

    # Label grup = label mayoritas anggotanya (warga dengan riwayat pengajuan campuran itu mungkin).
    per_label: dict[str, list[list[Baris]]] = defaultdict(list)
    for anggota in grup.values():
        mayoritas = max(
            {x.label for x in anggota}, key=lambda l: sum(1 for x in anggota if x.label == l)
        )
        per_label[mayoritas].append(anggota)

    rng = random.Random(seed)
    latih: list[Baris] = []
    uji: list[Baris] = []
    for label in sorted(per_label):
        grup_label = sorted(per_label[label], key=lambda g: g[0].warga_id)
        rng.shuffle(grup_label)
        n_uji = max(1, round(len(grup_label) * test_size))
        for g in grup_label[:n_uji]:
            uji.extend(g)
        for g in grup_label[n_uji:]:
            latih.extend(g)

    rng.shuffle(latih)
    rng.shuffle(uji)
    return latih, uji


def periksa_kebocoran(latih: list[Baris], uji: list[Baris]) -> int:
    """Jumlah baris uji yang warganya juga muncul di latih (harus 0)."""
    warga_latih = {b.warga_id for b in latih}
    return sum(1 for b in uji if b.warga_id in warga_latih)


def ringkasan(baris: list[Baris]) -> dict[str, object]:
    per_label: dict[str, int] = defaultdict(int)
    per_asal: dict[str, int] = defaultdict(int)
    for b in baris:
        per_label[b.label] += 1
        per_asal[b.asal_data] += 1
    return {
        "jumlah": len(baris),
        "warga_unik": len({b.warga_id for b in baris}),
        "per_label": dict(per_label),
        "per_asal_data": dict(per_asal),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Ekspor & split dataset Tier 2 dari basis data.")
    ap.add_argument("--outdir", default="data/corpus")
    ap.add_argument("--asal-data", default=None, help="saring per asal: sintetis | publik | lokal")
    ap.add_argument("--skor-urgensi", default="hitung", choices=["hitung", "tersimpan"])
    ap.add_argument("--test-size", type=float, default=0.2)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--batas", type=int, default=None, help="ambil maksimal N pengajuan")
    ap.add_argument(
        "--tanpa-urgensi",
        action="store_true",
        help="ablasi 6 fitur: buang `skor_urgensi` dari skema. Untuk data publik tanpa teks "
             "naratif. Artefak hasilnya SENGAJA ditolak pipeline live.",
    )
    args = ap.parse_args()

    fitur = FITUR_TANPA_URGENSI if args.tanpa_urgensi else FITUR
    baris, lewat = muat_dari_db(
        skor_urgensi=args.skor_urgensi,
        asal_data=args.asal_data,
        batas=args.batas,
        tanpa_urgensi=args.tanpa_urgensi,
    )
    if not baris:
        # Cetak `lewat` DI SINI, bukan hanya di jalur sukses di bawah: tanpa ini pesan galatnya
        # menyembunyikan satu-satunya keterangan yang menjelaskan sebabnya. Terbukti menyesatkan
        # saat data publik Alatas (tanpa teks naratif) diekspor — pesan lama menyuruh menjalankan
        # seeder sintetis, padahal seluruh baris gugur karena `tanpa_skor_urgensi`.
        raise SystemExit(
            "Tidak ada pengajuan berlabel yang dapat diekspor.\n"
            f"  Dilewati: {lewat}\n"
            "  tanpa_survei / tanpa_label  → jalankan `python -m data.synthetic.seed <n> --force`\n"
            "  tanpa_skor_urgensi          → pengajuan tidak punya teks naratif atau belum\n"
            "                                dianalisis. Data publik tanpa teks (mis. Alatas dkk.)\n"
            "                                memang selalu jatuh ke sini; ekspornya membutuhkan\n"
            "                                mode tanpa-urgensi yang eksplisit, bukan nilai netral\n"
            "                                yang diisikan diam-diam."
        )

    latih, uji = split_80_20(baris, test_size=args.test_size, seed=args.seed)
    bocor = periksa_kebocoran(latih, uji)

    outdir = Path(args.outdir)
    tulis_csv(latih, outdir / "tier2_train.csv", fitur)
    tulis_csv(uji, outdir / "tier2_test.csv", fitur)

    print(f"Skema  : {nama_set_fitur(fitur)} ({len(fitur)} fitur) — {fitur}")
    if args.tanpa_urgensi:
        print(
            "         ABLASI: artefak yang dilatih dari CSV ini tidak dapat melayani aplikasi;\n"
            "         `periksa_skema()` akan menolaknya. Gunakan hanya untuk pembandingan luring."
        )
    print(f"Dilewati: {lewat}")
    print(f"Total   : {ringkasan(baris)}")
    print(f"Latih   : {ringkasan(latih)}")
    print(f"Uji     : {ringkasan(uji)}")
    print(f"Kebocoran warga uji ke latih: {bocor} (harus 0)")
    print(f"Ditulis ke {outdir / 'tier2_train.csv'} & {outdir / 'tier2_test.csv'}")


if __name__ == "__main__":
    main()
