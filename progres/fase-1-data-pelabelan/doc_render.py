"""Perender dokumen dua format: satu sumber konten -> Markdown + PDF.

Dokumen Fase 1 (rubrik pelabelan, protokol validasi) harus tersedia sebagai **Markdown** (dibaca di
repo, dikutip di skripsi) sekaligus **PDF** (dicetak untuk sesi pelabelan). Menulis keduanya terpisah
dijamin melenceng begitu rubrik diamandemen — dan rubrik memang dirancang untuk diamandemen. Karena
itu konten didefinisikan sekali sebagai daftar blok, lalu dirender dua kali.

Gaya visual PDF mengikuti `generate_ketentuan_pdf.py` (palet navy, bilah judul, tabel bergaris).

Pemakaian:
    from doc_render import Dokumen, H1, H2, P, Bullets, Numbered, Table, Note, tulis_dua_format

    dok = Dokumen(judul="...", blok=[H1(1, "Bagian"), P("isi"), ...])
    tulis_dua_format(dok, Path("nama-berkas"))   # -> nama-berkas.md & nama-berkas.pdf
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from fpdf import FPDF

# --- Palet & metrik halaman (identik dengan generate_ketentuan_pdf.py) -----
NAVY = (30, 58, 95)
GREY = (90, 90, 90)
LIGHT = (235, 239, 245)
LINE = (200, 200, 200)
KUNING = (255, 249, 219)
KUNING_TEPI = (222, 190, 60)

# Helvetica bawaan fpdf2 hanya mendukung Latin-1; tanda tipografis diganti padanan ASCII.
_REPL = {
    "–": "-", "—": "-", "‘": "'", "’": "'", "“": '"', "”": '"', "…": "...",
    "≥": ">=", "≤": "<=", "•": "-", " ": " ", "→": "->", "κ": "kappa", "×": "x",
    "±": "+/-", "✓": "v", "✗": "x", "≠": "!=",
}


def s(text: str) -> str:
    """Buat teks aman untuk Helvetica/Latin-1."""
    for a, b in _REPL.items():
        text = text.replace(a, b)
    return text.encode("latin-1", "replace").decode("latin-1")


def _bersih_md(text: str) -> str:
    """Buang penanda tebal Markdown untuk keluaran PDF (PDF memakai gaya font, bukan `**`)."""
    return text.replace("**", "").replace("`", "")


# ---------------------------------------------------------------------------
# Blok konten
# ---------------------------------------------------------------------------

@dataclass
class H1:
    nomor: int
    judul: str


@dataclass
class H2:
    judul: str


@dataclass
class P:
    teks: str
    tebal: bool = False


@dataclass
class Bullets:
    butir: list[str]


@dataclass
class Numbered:
    butir: list[str]


@dataclass
class Table:
    header: list[str]
    baris: list[list[str]]
    lebar: list[int] | None = None      # proporsi kolom; None = rata
    kolom1_tebal: bool = True


@dataclass
class Note:
    teks: str
    judul: str = "Catatan penting"


@dataclass
class Dokumen:
    judul: str
    subjudul: str = ""
    kicker: str = ""                     # baris miring di bawah subjudul
    meta: list[tuple[str, str]] = field(default_factory=list)
    intro: str = ""
    blok: list[object] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Perender Markdown
# ---------------------------------------------------------------------------

def render_markdown(dok: Dokumen) -> str:
    out: list[str] = [f"# {dok.judul}"]
    if dok.subjudul:
        out.append(f"\n**{dok.subjudul}**")
    if dok.kicker:
        out.append(f"\n*{dok.kicker}*")
    if dok.meta:
        out.append("")
        for k, v in dok.meta:
            out.append(f"- **{k}:** {v}")
    if dok.intro:
        out.append(f"\n{dok.intro}")

    for b in dok.blok:
        if isinstance(b, H1):
            out.append(f"\n## {b.nomor}. {b.judul}")
        elif isinstance(b, H2):
            out.append(f"\n### {b.judul}")
        elif isinstance(b, P):
            out.append(f"\n**{b.teks}**" if b.tebal else f"\n{b.teks}")
        elif isinstance(b, Bullets):
            out.append("")
            out.extend(f"- {x}" for x in b.butir)
        elif isinstance(b, Numbered):
            out.append("")
            out.extend(f"{i}. {x}" for i, x in enumerate(b.butir, start=1))
        elif isinstance(b, Table):
            out.append("")
            out.append("| " + " | ".join(b.header) + " |")
            out.append("|" + "|".join("---" for _ in b.header) + "|")
            for r in b.baris:
                sel = [str(c).replace("\n", "<br>").replace("|", "\\|") for c in r]
                out.append("| " + " | ".join(sel) + " |")
        elif isinstance(b, Note):
            out.append(f"\n> **{b.judul}** — {b.teks}")
        else:
            raise TypeError(f"Blok tidak dikenal: {type(b).__name__}")

    return "\n".join(out).strip() + "\n"


# ---------------------------------------------------------------------------
# Perender PDF
# ---------------------------------------------------------------------------

class _PDF(FPDF):
    judul_berjalan = ""
    kicker_berjalan = ""

    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GREY)
        self.cell(0, 6, s(self.judul_berjalan), align="L")
        self.cell(0, 6, s(self.kicker_berjalan), align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*LINE)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GREY)
        self.cell(0, 10, s(f"Halaman {self.page_no()}"), align="C")


class _Renderer:
    def __init__(self, dok: Dokumen) -> None:
        self.dok = dok
        pdf = _PDF(orientation="P", unit="mm", format="A4")
        pdf.judul_berjalan = dok.judul
        pdf.kicker_berjalan = dok.subjudul or dok.kicker
        pdf.set_auto_page_break(auto=True, margin=18)
        pdf.set_margins(left=20, top=18, right=20)
        pdf.add_page()
        self.pdf = pdf
        self.epw = pdf.w - pdf.l_margin - pdf.r_margin

    # -- blok dasar ---------------------------------------------------------
    def h1(self, nomor: int, teks: str) -> None:
        pdf = self.pdf
        if pdf.get_y() + 24 > pdf.h - pdf.b_margin:   # jangan tinggalkan judul menggantung
            pdf.add_page()
        pdf.ln(2)
        pdf.set_fill_color(*NAVY)
        pdf.set_text_color(255, 255, 255)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 8, s(f"  {nomor}. {teks}"), new_x="LMARGIN", new_y="NEXT", fill=True)
        pdf.set_text_color(0, 0, 0)
        pdf.ln(2)

    def h2(self, teks: str) -> None:
        pdf = self.pdf
        if pdf.get_y() + 20 > pdf.h - pdf.b_margin:
            pdf.add_page()
        pdf.ln(1)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(*NAVY)
        pdf.multi_cell(0, 6, s(_bersih_md(teks)), new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(0, 0, 0)
        pdf.ln(0.5)

    def para(self, teks: str, tebal: bool = False) -> None:
        pdf = self.pdf
        pdf.set_font("Helvetica", "B" if tebal else "", 10)
        pdf.set_text_color(0, 0, 0)
        pdf.set_x(pdf.l_margin)
        pdf.multi_cell(0, 5.2, s(_bersih_md(teks)), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(1)

    def bullets(self, butir: list[str], penanda: str = "-") -> None:
        pdf = self.pdf
        for i, teks in enumerate(butir, start=1):
            tanda = penanda if penanda != "#" else f"{i}."
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(0, 0, 0)
            x0 = pdf.l_margin
            pdf.set_x(x0 + 4)
            pdf.cell(5, 5.2, s(tanda))
            pdf.multi_cell(self.epw - 9, 5.2, s(_bersih_md(teks)))
            pdf.set_x(x0)
        pdf.ln(1.5)

    def note(self, teks: str, judul: str) -> None:
        pdf = self.pdf
        pdf.set_font("Helvetica", "", 9.5)
        isi = s(_bersih_md(teks))
        n = max(1, len(pdf.multi_cell(self.epw - 10, 4.8, isi, dry_run=True, output="LINES")))
        h = n * 4.8 + 12
        if pdf.get_y() + h > pdf.h - pdf.b_margin:
            pdf.add_page()
        x0, y0 = pdf.l_margin, pdf.get_y()
        pdf.set_fill_color(*KUNING)
        pdf.set_draw_color(*KUNING_TEPI)
        pdf.rect(x0, y0, self.epw, h, style="DF")
        pdf.set_xy(x0 + 5, y0 + 3)
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(*NAVY)
        pdf.multi_cell(self.epw - 10, 5, s(judul), new_x="LMARGIN", new_y="NEXT")
        pdf.set_xy(x0 + 5, y0 + 8)
        pdf.set_font("Helvetica", "", 9.5)
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(self.epw - 10, 4.8, isi, new_x="LMARGIN", new_y="TOP")
        pdf.set_xy(x0, y0 + h)
        pdf.ln(3)

    def table(self, header: list[str], baris: list[list[str]],
              lebar: list[int] | None = None, kolom1_tebal: bool = True) -> None:
        pdf = self.pdf
        n_kol = len(header)
        prop = lebar or [1] * n_kol
        total = sum(prop)
        w = [self.epw * p / total for p in prop]
        line_h, pad = 4.4, 1.6

        def n_lines(txt: str, lebar_kolom: float, style: str) -> int:
            pdf.set_font("Helvetica", style, 8.5)
            return max(1, len(pdf.multi_cell(lebar_kolom, line_h, s(_bersih_md(str(txt))),
                                             dry_run=True, output="LINES")))

        def gambar_header() -> None:
            pdf.set_font("Helvetica", "B", 8.5)
            pdf.set_fill_color(*LIGHT)
            pdf.set_text_color(*NAVY)
            pdf.set_draw_color(*LINE)
            tinggi = max(n_lines(h, w[i] - 2, "B") for i, h in enumerate(header)) * line_h + pad
            y0 = pdf.get_y()
            x = pdf.l_margin
            for i, h in enumerate(header):
                pdf.rect(x, y0, w[i], tinggi, style="DF")
                pdf.set_xy(x + 1, y0 + pad / 2)
                pdf.multi_cell(w[i] - 2, line_h, s(h), align="C", new_x="LMARGIN", new_y="TOP")
                x += w[i]
            pdf.set_xy(pdf.l_margin, y0 + tinggi)
            pdf.set_text_color(0, 0, 0)

        gambar_header()
        for r in baris:
            gaya = ["B" if (i == 0 and kolom1_tebal) else "" for i in range(n_kol)]
            tinggi = max(n_lines(sel, w[i] - 2, gaya[i]) for i, sel in enumerate(r)) * line_h + pad
            if pdf.get_y() + tinggi > pdf.h - pdf.b_margin:
                pdf.add_page()
                gambar_header()                     # ulangi header di halaman baru
            y0 = pdf.get_y()
            x = pdf.l_margin
            pdf.set_draw_color(*LINE)
            for i, sel in enumerate(r):
                pdf.rect(x, y0, w[i], tinggi)
                pdf.set_xy(x + 1, y0 + pad / 2)
                pdf.set_font("Helvetica", gaya[i], 8.5)
                pdf.multi_cell(w[i] - 2, line_h, s(_bersih_md(str(sel))),
                               align="L", new_x="LMARGIN", new_y="TOP")
                x += w[i]
            pdf.set_xy(pdf.l_margin, y0 + tinggi)
        pdf.ln(3)

    # -- sampul & perakitan -------------------------------------------------
    def sampul(self) -> None:
        pdf, dok = self.pdf, self.dok
        pdf.set_font("Helvetica", "B", 17)
        pdf.set_text_color(*NAVY)
        pdf.multi_cell(0, 9, s(dok.judul), align="C", new_x="LMARGIN", new_y="NEXT")
        if dok.subjudul:
            pdf.set_font("Helvetica", "B", 12)
            pdf.multi_cell(0, 7, s(dok.subjudul), align="C", new_x="LMARGIN", new_y="NEXT")
        if dok.kicker:
            pdf.ln(1)
            pdf.set_font("Helvetica", "I", 10)
            pdf.set_text_color(*GREY)
            pdf.multi_cell(0, 6, s(dok.kicker), align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)
        pdf.set_draw_color(*NAVY)
        pdf.set_line_width(0.5)
        pdf.line(pdf.l_margin + 30, pdf.get_y(), pdf.w - pdf.r_margin - 30, pdf.get_y())
        pdf.set_line_width(0.2)
        pdf.ln(5)

        pdf.set_text_color(0, 0, 0)
        for k, v in dok.meta:
            pdf.set_x(pdf.l_margin)
            pdf.set_font("Helvetica", "B", 10)
            # Lebar label 38 mm adalah nilai bawaan, BUKAN batas keras: `cell()` tidak memotong
            # maupun melipat teks yang lebih panjang, sehingga label panjang tertimpa nilainya
            # tanpa galat apa pun. Terbukti pada baris "Lama menangani penyaluran bantuan"
            # (lembar pembobotan, 5 September 2026). Label pendek tetap 38 mm, jadi tata letak
            # dokumen yang sudah ada tidak berubah sedikit pun.
            w_label = max(38.0, pdf.get_string_width(s(k)) + 2)
            pdf.cell(w_label, 6, s(k))
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(self.epw - w_label, 6, s(": " + v), new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)
        if dok.intro:
            self.para(dok.intro)

    def render(self, path: Path) -> Path:
        self.sampul()
        for b in self.dok.blok:
            if isinstance(b, H1):
                self.h1(b.nomor, b.judul)
            elif isinstance(b, H2):
                self.h2(b.judul)
            elif isinstance(b, P):
                self.para(b.teks, b.tebal)
            elif isinstance(b, Bullets):
                self.bullets(b.butir)
            elif isinstance(b, Numbered):
                self.bullets(b.butir, penanda="#")
            elif isinstance(b, Table):
                self.table(b.header, b.baris, b.lebar, b.kolom1_tebal)
            elif isinstance(b, Note):
                self.note(b.teks, b.judul)
            else:
                raise TypeError(f"Blok tidak dikenal: {type(b).__name__}")
        path.parent.mkdir(parents=True, exist_ok=True)
        self.pdf.output(str(path))
        return path


def render_pdf(dok: Dokumen, path: Path) -> Path:
    return _Renderer(dok).render(path)


def tulis_dua_format(dok: Dokumen, dasar: Path) -> tuple[Path, Path]:
    """Tulis `<dasar>.md` dan `<dasar>.pdf`; kembalikan kedua path."""
    md = dasar.with_suffix(".md")
    md.parent.mkdir(parents=True, exist_ok=True)
    md.write_text(render_markdown(dok), encoding="utf-8")
    pdf = render_pdf(dok, dasar.with_suffix(".pdf"))
    return md, pdf


def hari_ini() -> str:
    bulan = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
             "Agustus", "September", "Oktober", "November", "Desember"]
    t = date.today()
    return f"{t.day} {bulan[t.month - 1]} {t.year}"
