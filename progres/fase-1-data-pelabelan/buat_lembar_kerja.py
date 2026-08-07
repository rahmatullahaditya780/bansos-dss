"""Pembuat lembar kerja pelabelan (Excel) — satu berkas per pelabel.

Tiap pelabel bekerja pada salinannya sendiri dan **tidak** melihat pekerjaan pelabel lain (syarat
Tahap 1 rubrik; bila saling melihat, Cohen's kappa mengukur kesepakatan semu). Berkas digabungkan
hanya setelah keduanya selesai, lewat `hitung_kappa.py`.

Isi berkas:
- sheet **Pelabelan** — kolom isian dengan dropdown label, baris terkunci selain kolom isian;
- sheet **Rujukan Cepat** — ringkasan aturan, indikator, dan kasus batas, agar PDF tidak perlu dibuka;
- sheet **Petunjuk** — cara pengisian dan versi rubrik yang berlaku.

Pemakaian:
    # dari daftar teks yang sudah dianonimkan (kolom: id_teks, teks_anonim)
    python progres/fase-1-data-pelabelan/buat_lembar_kerja.py --input teks_anonim.csv --pelabel A B

    # tanpa data — menghasilkan berkas contoh berisi 25 kalimat kalibrasi rubrik
    python progres/fase-1-data-pelabelan/buat_lembar_kerja.py --contoh --pelabel A B
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

sys.path.insert(0, str(Path(__file__).parent))

from generate_rubrik_urgensi import (  # noqa: E402
    ATURAN_DASAR, CONTOH, INDIKATOR, KASUS_BATAS, VERSI_RUBRIK,
)

LABEL_SAH = ["tinggi", "rendah", "tidak_dapat_dinilai"]

NAVY = "1E3A5F"
LIGHT = "EBEFF5"
KUNING = "FFF9DB"
TEPI = Side(style="thin", color="C8C8C8")
KOTAK = Border(left=TEPI, right=TEPI, top=TEPI, bottom=TEPI)


def _judul_sheet(ws, teks: str, lebar_gabung: int) -> None:
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=lebar_gabung)
    sel = ws.cell(row=1, column=1, value=teks)
    sel.font = Font(bold=True, size=13, color="FFFFFF")
    sel.fill = PatternFill("solid", fgColor=NAVY)
    sel.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 26


def _header(ws, baris: int, kolom: list[str], lebar: list[int]) -> None:
    for i, (judul, w) in enumerate(zip(kolom, lebar), start=1):
        sel = ws.cell(row=baris, column=i, value=judul)
        sel.font = Font(bold=True, color=NAVY)
        sel.fill = PatternFill("solid", fgColor=LIGHT)
        sel.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        sel.border = KOTAK
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.row_dimensions[baris].height = 30


def _sheet_pelabelan(wb: Workbook, baris: list[tuple[str, str]], pelabel: str) -> None:
    ws = wb.create_sheet("Pelabelan", 0)
    _judul_sheet(ws, f"Lembar Pelabelan Urgensi - Pelabel {pelabel}", 4)
    _header(ws, 2, ["id_teks", "teks_anonim", "label", "catatan"], [12, 82, 20, 34])

    dv = DataValidation(
        type="list", formula1='"' + ",".join(LABEL_SAH) + '"', allow_blank=True, showDropDown=False,
    )
    dv.error = "Pilih salah satu dari daftar: tinggi, rendah, tidak_dapat_dinilai."
    dv.errorTitle = "Label tidak sah"
    dv.prompt = "Pilih label sesuai rubrik. Ragu? Lihat sheet 'Rujukan Cepat'."
    dv.promptTitle = "Label urgensi"
    ws.add_data_validation(dv)

    for i, (id_teks, teks) in enumerate(baris, start=3):
        ws.cell(row=i, column=1, value=id_teks).border = KOTAK
        sel = ws.cell(row=i, column=2, value=teks)
        sel.alignment = Alignment(wrap_text=True, vertical="top")
        sel.border = KOTAK
        isian = ws.cell(row=i, column=3)
        isian.fill = PatternFill("solid", fgColor=KUNING)
        isian.border = KOTAK
        isian.alignment = Alignment(horizontal="center", vertical="center")
        dv.add(isian)
        ws.cell(row=i, column=4).border = KOTAK
        ws.row_dimensions[i].height = 30

    ws.freeze_panes = "A3"
    ws.auto_filter.ref = f"A2:D{len(baris) + 2}"


def _sheet_rujukan(wb: Workbook) -> None:
    ws = wb.create_sheet("Rujukan Cepat")
    _judul_sheet(ws, "Rujukan Cepat - ringkasan rubrik", 3)
    r = 3

    def blok(judul: str, kolom: list[str], lebar: list[int], baris: list[list[str]]) -> None:
        nonlocal r
        sel = ws.cell(row=r, column=1, value=judul)
        sel.font = Font(bold=True, size=11, color=NAVY)
        r += 1
        _header(ws, r, kolom, lebar)
        r += 1
        for isi in baris:
            for i, teks in enumerate(isi, start=1):
                c = ws.cell(row=r, column=i, value=str(teks).replace("**", ""))
                c.alignment = Alignment(wrap_text=True, vertical="top")
                c.border = KOTAK
            ws.row_dimensions[r].height = 28
            r += 1
        r += 1

    blok("Tujuh aturan dasar", ["#", "Aturan", "Mengapa"], [6, 60, 60], ATURAN_DASAR)
    blok("Indikator TINGGI (satu saja sudah cukup)", ["Indikator", "Bentuk yang termasuk"],
         [34, 92], INDIKATOR)
    blok("Kasus batas", ["Situasi", "Putusan", "Dasar"], [46, 18, 62], KASUS_BATAS)
    ws.freeze_panes = "A3"


def _sheet_petunjuk(wb: Workbook, pelabel: str, jumlah: int) -> None:
    ws = wb.create_sheet("Petunjuk")
    _judul_sheet(ws, "Petunjuk Pengisian", 2)
    langkah = [
        ("Versi rubrik", VERSI_RUBRIK),
        ("Pelabel", pelabel),
        ("Jumlah teks", str(jumlah)),
        ("", ""),
        ("1", "Baca rubrik lengkap sekali sebelum mulai (berkas rubrik-pelabelan-urgensi.pdf)."),
        ("2", "Isi kolom 'label' di sheet Pelabelan lewat dropdown. Jangan mengetik bebas."),
        ("3", "Kerjakan SENDIRI. Jangan melihat lembar pelabel lain dan jangan berdiskusi "
              "sebelum keduanya selesai - kesepakatan yang diukur harus asli."),
        ("4", "Ragu? Buka sheet 'Rujukan Cepat'. Bila situasinya tidak ada di sana, isi label "
              "terbaik menurut Anda lalu tulis alasannya di kolom catatan."),
        ("5", "Pakai 'tidak_dapat_dinilai' hanya untuk teks kosong atau administratif - "
              "bukan untuk menyatakan ragu."),
        ("6", "Jangan mengubah kolom id_teks dan teks_anonim."),
        ("7", "Setelah selesai, kirimkan berkas ini apa adanya kepada peneliti."),
    ]
    ws.column_dimensions["A"].width = 14
    ws.column_dimensions["B"].width = 104
    for i, (k, v) in enumerate(langkah, start=3):
        a = ws.cell(row=i, column=1, value=k)
        a.font = Font(bold=True)
        a.alignment = Alignment(vertical="top")
        b = ws.cell(row=i, column=2, value=v)
        b.alignment = Alignment(wrap_text=True, vertical="top")
        ws.row_dimensions[i].height = 30


def buat(baris: list[tuple[str, str]], pelabel: str, out: Path) -> Path:
    wb = Workbook()
    wb.remove(wb.active)
    _sheet_pelabelan(wb, baris, pelabel)
    _sheet_rujukan(wb)
    _sheet_petunjuk(wb, pelabel, len(baris))
    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    return out


def muat_teks(path: Path) -> list[tuple[str, str]]:
    with path.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise SystemExit(f"Berkas kosong: {path}")
    kol_teks = next((k for k in ("teks_anonim", "teks", "isi_teks") if k in rows[0]), None)
    if kol_teks is None:
        raise SystemExit(f"Kolom teks tidak ditemukan di {path} (ada: {list(rows[0])})")
    kol_id = "id_teks" if "id_teks" in rows[0] else None
    return [
        (r[kol_id] if kol_id else f"T{i:04d}", (r[kol_teks] or "").strip())
        for i, r in enumerate(rows, start=1)
        if (r[kol_teks] or "").strip()
    ]


def main() -> None:
    ap = argparse.ArgumentParser(description="Buat lembar kerja pelabelan Excel per pelabel.")
    ap.add_argument("--input", help="CSV teks yang SUDAH dianonimkan (kolom: id_teks, teks_anonim)")
    ap.add_argument("--contoh", action="store_true",
                    help="pakai 25 kalimat kalibrasi rubrik (untuk Tahap 0 / melihat formatnya)")
    ap.add_argument("--pelabel", nargs="+", default=["A", "B"], help="daftar kode pelabel")
    ap.add_argument("--outdir", default=None, help="folder keluaran (default: folder skrip ini)")
    args = ap.parse_args()

    if args.contoh:
        baris = [(f"KAL{int(no):02d}", teks) for no, teks, _, _ in CONTOH]
        nama = "lembar-kerja-kalibrasi"
    elif args.input:
        baris = muat_teks(Path(args.input))
        nama = "lembar-kerja-pelabelan"
    else:
        raise SystemExit("Sebutkan --input <csv> atau --contoh. Lihat --help.")

    outdir = Path(args.outdir) if args.outdir else Path(__file__).parent
    for pelabel in args.pelabel:
        path = buat(baris, pelabel, outdir / f"{nama}-{pelabel}.xlsx")
        print(f"Pelabel {pelabel}: {path}  ({len(baris)} teks)")

    if args.contoh:
        print("\nBerkas kalibrasi memuat kunci jawaban di rubrik Bagian 6 - pakai untuk Tahap 0,")
        print("JANGAN dipakai sebagai data pilot Tahap 1.")


if __name__ == "__main__":
    main()
