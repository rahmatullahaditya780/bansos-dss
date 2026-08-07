"""
Generator PDF: "Ketentuan Data DTKS Kelurahan Bontoramba"
Catatan persiapan internal untuk Muhammad Gilang sebelum berhubungan dengan pihak kelurahan.

Menghasilkan: ketentuan-data-dtks-kelurahan.pdf (di folder yang sama)
Field diturunkan dari TRD Bab 6.1 & 6.2 + skema DB (data_survei / teks_naratif / warga).

Jalankan:
    .venv/Scripts/python.exe progres/fase-1-data-pelabelan/generate_ketentuan_pdf.py
"""

from pathlib import Path
from datetime import date
from fpdf import FPDF

# ---------------------------------------------------------------------------
# Utilitas teks: jaga kompatibel Latin-1 (Helvetica bawaan tidak mendukung
# karakter Unicode di luar Latin-1). Ganti tanda tipografis yang umum.
# ---------------------------------------------------------------------------
_REPL = {
    "–": "-", "—": "-", "‘": "'", "’": "'",
    "“": '"', "”": '"', "…": "...", "≥": ">=",
    "≤": "<=", "•": "-", " ": " ", "→": "->",
}


def s(text: str) -> str:
    for a, b in _REPL.items():
        text = text.replace(a, b)
    return text.encode("latin-1", "replace").decode("latin-1")


# Palet warna
NAVY = (30, 58, 95)
GREY = (90, 90, 90)
LIGHT = (235, 239, 245)
LINE = (200, 200, 200)


class PDF(FPDF):
    def header(self):
        if self.page_no() == 1:
            return
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GREY)
        self.cell(0, 6, s("Ketentuan Data DTKS - Kelurahan Bontoramba"), align="L")
        self.cell(0, 6, s("Catatan Persiapan Internal"), align="R", new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*LINE)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*GREY)
        self.cell(0, 10, s(f"Halaman {self.page_no()}"), align="C")


pdf = PDF(orientation="P", unit="mm", format="A4")
pdf.set_auto_page_break(auto=True, margin=18)
pdf.set_margins(left=20, top=18, right=20)
pdf.add_page()

EPW = pdf.w - pdf.l_margin - pdf.r_margin  # effective page width


# ---------------------------------------------------------------------------
# Helper blok
# ---------------------------------------------------------------------------
def h1(num, text):
    pdf.ln(2)
    pdf.set_fill_color(*NAVY)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 8, s(f"  {num}. {text}"), new_x="LMARGIN", new_y="NEXT", fill=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln(2)


def para(text, size=10, style=""):
    pdf.set_font("Helvetica", style, size)
    pdf.set_text_color(0, 0, 0)
    pdf.set_x(pdf.l_margin)
    pdf.multi_cell(0, 5.2, s(text), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def bullet(text, indent=4):
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(0, 0, 0)
    x0 = pdf.get_x()
    pdf.set_x(x0 + indent)
    pdf.cell(4, 5.2, s("-"))
    pdf.multi_cell(EPW - indent - 4, 5.2, s(text))
    pdf.set_x(x0)


def field_table(rows):
    """rows: list of (kategori, field, catatan). Kategori boleh '' untuk menyatu."""
    w_kat, w_field, w_cat = 34, 78, EPW - 34 - 78
    # header
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_fill_color(*LIGHT)
    pdf.set_text_color(*NAVY)
    pdf.cell(w_kat, 7, s("Kategori"), border=1, fill=True, align="C")
    pdf.cell(w_field, 7, s("Field diminta"), border=1, fill=True, align="C")
    pdf.cell(w_cat, 7, s("Catatan / pemetaan"), border=1, fill=True, align="C",
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    line_h = 4.8
    pad = 1.5

    def n_lines(txt, w, style):
        pdf.set_font("Helvetica", style, 9)
        return max(1, len(pdf.multi_cell(w, line_h, s(txt), dry_run=True,
                                         output="LINES")))

    for kat, field, cat in rows:
        rows_h = max(n_lines(kat, w_kat - 2, "B"),
                     n_lines(field, w_field - 2, ""),
                     n_lines(cat, w_cat - 2, ""))
        h = rows_h * line_h + pad
        # page break manual
        if pdf.get_y() + h > pdf.h - pdf.b_margin:
            pdf.add_page()
        x0 = pdf.l_margin
        y0 = pdf.get_y()
        # teks tanpa border (sedikit padding kiri)
        pdf.set_xy(x0 + 1, y0 + pad / 2)
        pdf.set_font("Helvetica", "B", 9)
        pdf.multi_cell(w_kat - 2, line_h, s(kat), border=0, align="L",
                       new_x="LMARGIN", new_y="TOP")
        pdf.set_xy(x0 + w_kat + 1, y0 + pad / 2)
        pdf.set_font("Helvetica", "", 9)
        pdf.multi_cell(w_field - 2, line_h, s(field), border=0, align="L",
                       new_x="LMARGIN", new_y="TOP")
        pdf.set_xy(x0 + w_kat + w_field + 1, y0 + pad / 2)
        pdf.multi_cell(w_cat - 2, line_h, s(cat), border=0, align="L",
                       new_x="LMARGIN", new_y="TOP")
        # border baris (grid)
        pdf.set_draw_color(*LINE)
        pdf.rect(x0, y0, w_kat, h)
        pdf.rect(x0 + w_kat, y0, w_field, h)
        pdf.rect(x0 + w_kat + w_field, y0, w_cat, h)
        pdf.set_xy(x0, y0 + h)
    pdf.ln(2)


# ---------------------------------------------------------------------------
# 1. Judul & konteks (halaman sampul ringkas)
# ---------------------------------------------------------------------------
pdf.set_font("Helvetica", "B", 18)
pdf.set_text_color(*NAVY)
pdf.multi_cell(0, 9, s("Ketentuan Data DTKS yang Diminta"), align="C", new_x="LMARGIN", new_y="NEXT")
pdf.set_font("Helvetica", "B", 13)
pdf.multi_cell(0, 7, s("Kelurahan Bontoramba"), align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(1)
pdf.set_font("Helvetica", "I", 10)
pdf.set_text_color(*GREY)
pdf.multi_cell(0, 6, s("Catatan Persiapan Internal - Bukan Surat Resmi"), align="C", new_x="LMARGIN", new_y="NEXT")
pdf.ln(4)
pdf.set_draw_color(*NAVY)
pdf.set_line_width(0.5)
pdf.line(pdf.l_margin + 30, pdf.get_y(), pdf.w - pdf.r_margin - 30, pdf.get_y())
pdf.set_line_width(0.2)
pdf.ln(5)

pdf.set_text_color(0, 0, 0)
pdf.set_font("Helvetica", "", 10)
meta = [
    ("Proyek", "Decision Support System Penentuan Kelayakan & Prioritas Penerima Bansos"),
    ("Peneliti", "Muhammad Gilang"),
    ("Lokasi", "Kelurahan Bontoramba"),
    ("Tanggal disusun", date.today().strftime("%d %B %Y")),
    ("Dasar", "TRD Bab 6.1 & 6.2; Fase 1 (OI-08, OI-09, OI-10, OI-11)"),
]
for k, v in meta:
    pdf.set_x(pdf.l_margin)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(38, 6, s(k))
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(EPW - 38, 6, s(": " + v), new_x="LMARGIN", new_y="NEXT")
pdf.ln(3)
para(
    "Dokumen ini adalah catatan pribadi peneliti untuk persiapan pertemuan dengan pihak "
    "Kelurahan Bontoramba. Tujuannya memastikan seluruh data yang dibutuhkan pipeline tiga "
    "tier (IndoBERT -> klasifikasi ML -> Fuzzy TOPSIS) diminta secara lengkap dan konsisten, "
    "serta pengurusan izin akses data (OI-09) berjalan sejak awal. Pengumpulan data lokal ini "
    "bersifat paralel dan tidak memblokir pengembangan, karena pipeline dilatih lebih dulu "
    "memakai dataset publik.",
    style="",
)

# ---------------------------------------------------------------------------
# 2. Ringkasan permintaan
# ---------------------------------------------------------------------------
h1(1, "Ringkasan Permintaan")
para(
    "Meminta akses data DTKS/kependudukan untuk minimal 100 Kepala Keluarga (KK), mencakup "
    "(A) data terstruktur demografi-ekonomi-kondisi rumah, (B) label historis penerima bansos, "
    "dan (C) sumber teks naratif kondisi keluarga. Seluruh data diminta dalam bentuk "
    "TER-ANONIMISASI (tanpa NIK & nama, memakai kode unik per KK), diserahkan dalam format "
    "CSV atau Excel dengan kolom yang disepakati bersama."
)

# ---------------------------------------------------------------------------
# 3. A. Data terstruktur DTKS
# ---------------------------------------------------------------------------
h1(2, "Data Terstruktur DTKS (per KK)")
para("Sumber: data kependudukan/DTKS kelurahan + arsip survei. Satu baris per KK.", style="I", size=9)
field_table([
    ("Demografi",
     "Usia; jenis kelamin; jumlah tanggungan; status pernikahan",
     "Profil kepala keluarga. -> tabel warga"),
    ("Ekonomi",
     "Pendapatan per kapita; status pekerjaan; kepemilikan aset produktif",
     "Dikategorikan ke himpunan fuzzy (sangat rendah..tinggi). -> data_survei"),
    ("Kondisi rumah",
     "Luas rumah; jenis lantai; jenis dinding; kondisi sumber air bersih",
     "Indikator kelayakan hunian. -> data_survei"),
])
para(
    "Field di atas adalah masukan untuk Tier 2 (klasifikasi ML kelayakan) dan Tier 3 "
    "(Fuzzy TOPSIS perangkingan). Jika kelurahan memiliki tambahan indikator kemiskinan "
    "standar DTKS, mohon disertakan sebagai kolom ekstra.",
    size=9, style="I",
)

# ---------------------------------------------------------------------------
# 4. B. Label historis penerima bansos
# ---------------------------------------------------------------------------
h1(3, "Label Historis Penerima Bansos")
para(
    "Data status penerima bansos periode sebelumnya (ya/tidak) per KK. Ini adalah TARGET "
    "pelatihan model Tier 2, sehingga sangat menentukan. Mohon sertakan:"
)
bullet("Status penerima: ya / tidak (per KK).")
bullet("Periode / tahun bantuan.")
bullet("Jenis bantuan (mis. PKH, BPNT/sembako, BLT, dsb.).")
pdf.ln(1)
para(
    "Catatan bias (OI-10): keputusan historis berpotensi mewarisi subjektivitas. Mohon "
    "kesediaan petugas ahli untuk memvalidasi/mengoreksi label ini agar model tidak "
    "mereplikasi ketidakadilan lama.",
    size=9, style="I",
)

# ---------------------------------------------------------------------------
# 5. C. Sumber teks naratif
# ---------------------------------------------------------------------------
h1(4, "Sumber Teks Naratif")
para(
    "Bahan pelabelan urgensi untuk Tier 1 (IndoBERT). Berupa teks bebas terkait kondisi "
    "keluarga, dipetakan ke tabel teks_naratif. Sumber yang diminta:"
)
bullet("Catatan observasi/survei petugas kelurahan.")
bullet("Uraian kondisi keluarga (deskripsi kesulitan/kerentanan).")
bullet("Alasan pengajuan / surat permohonan warga.")
bullet("Laporan masyarakat terkait keluarga bersangkutan.")
pdf.ln(1)
para(
    "Idealnya tiap teks naratif dapat dikaitkan ke kode KK yang sama dengan data "
    "terstruktur, agar bisa digabung menjadi satu profil.",
    size=9, style="I",
)

# ---------------------------------------------------------------------------
# 6. Cakupan & jumlah
# ---------------------------------------------------------------------------
h1(5, "Cakupan & Jumlah Data (OI-08)")
bullet("Target minimum: >= 100 KK untuk klaim final penelitian.")
bullet("Prioritas: KK yang memiliki riwayat pengajuan/penerimaan bantuan, agar tersedia label historis.")
bullet("Bila data yang tersedia < 100 KK: mohon diberikan sebanyak yang ada; peneliti menyiapkan "
       "strategi cadangan (augmentasi data, model lebih sederhana).")

# ---------------------------------------------------------------------------
# 7. Ketentuan pengenal & anonimisasi
# ---------------------------------------------------------------------------
h1(6, "Ketentuan Pengenal & Anonimisasi")
para("Untuk melindungi privasi warga, peneliti TIDAK meminta identitas pribadi:")
bullet("Gunakan kode unik per KK, mis. KK-001, KK-002, ... (dibuat oleh pihak kelurahan).")
bullet("TANPA NIK dan TANPA nama warga.")
bullet("Alamat cukup pada tingkat RT/RW/dusun bila memang diperlukan; tidak perlu alamat detail.")
bullet("Kode KK harus KONSISTEN antara berkas data terstruktur dan berkas teks naratif.")

# ---------------------------------------------------------------------------
# 8. Komitmen penanganan data pribadi
# ---------------------------------------------------------------------------
h1(7, "Komitmen Penanganan Data (Peneliti)")
para("Sebagai jaminan kepada pihak kelurahan, peneliti berkomitmen:")
bullet("Data hanya digunakan untuk keperluan penelitian skripsi ini.")
bullet("Tidak mengunggah data mentah warga ke layanan/pihak eksternal.")
bullet("Data disimpan secara lokal dan aman, dengan akses terbatas.")
bullet("Data dihapus setelah penelitian selesai / sesuai kesepakatan.")
para("(Selaras dengan NFR-04 dan mitigasi risiko R-06 pada TRD.)", size=9, style="I")

# ---------------------------------------------------------------------------
# 9. Format serah-terima
# ---------------------------------------------------------------------------
h1(8, "Format Serah-Terima Data (OI-09)")
bullet("Format berkas: CSV atau Excel (.xlsx).")
bullet("Struktur: satu baris per KK; satu kolom per field pada daftar di atas.")
bullet("Dua berkas berkaitan lewat kode KK: (1) data terstruktur, (2) teks naratif.")
bullet("Sertakan keterangan periode/tahun data.")
bullet("Bila memungkinkan, sertakan kamus kolom singkat (arti tiap kolom & satuannya).")

# ---------------------------------------------------------------------------
# 10. Daftar pertanyaan untuk petugas
# ---------------------------------------------------------------------------
h1(9, "Daftar Pertanyaan untuk Petugas (Checklist)")
para("Yang perlu dipastikan saat pertemuan:", style="")
for q in [
    "Field mana saja pada daftar terstruktur yang tersedia? Adakah yang tidak terdata?",
    "Periode/tahun berapa saja data yang tersedia?",
    "Apakah label historis penerima bansos lengkap dan bisa divalidasi petugas ahli?",
    "Apakah tersedia catatan naratif/observasi, dan dalam bentuk apa (digital/kertas)?",
    "Bisakah kelurahan melakukan anonimisasi (mengganti NIK/nama dengan kode) dari sisi mereka?",
    "Siapa PIC/kontak yang menangani penyerahan data?",
    "Kapan perkiraan waktu data dapat diserahkan?",
    "Apakah diperlukan surat pengantar resmi/izin tambahan dari kampus?",
]:
    bullet(q)

# ---------------------------------------------------------------------------
# 11. Catatan penutup
# ---------------------------------------------------------------------------
h1(10, "Catatan Penutup")
para(
    "Pengumpulan data lokal ini paralel dan tidak menghentikan pengembangan sistem. Pipeline "
    "dibangun dan dilatih lebih dulu memakai dataset publik (SUSENAS/Kaggle/IndoNLU); data "
    "Bontoramba dipakai untuk pelatihan ulang dan klaim akhir. Bila akses data lokal tertunda "
    "(risiko OI-09/R-03), hasil berbasis data publik tetap dapat dikunci sebagai proof-of-concept."
)

# ---------------------------------------------------------------------------
# Simpan
# ---------------------------------------------------------------------------
out = Path(__file__).parent / "ketentuan-data-dtks-kelurahan.pdf"
pdf.output(str(out))
print(f"OK -> {out} ({out.stat().st_size} bytes)")
