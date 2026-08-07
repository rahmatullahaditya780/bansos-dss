"""Generator dokumen: "Protokol Validasi Label Historis Penerima Bansos" (OI-10).

Menghasilkan `protokol-validasi-label-historis.md` + `.pdf` dari satu sumber konten.
Audiens: petugas ahli Kelurahan Bontoramba (bukan pelabel mahasiswa).

Jalankan:
    .venv/Scripts/python.exe progres/fase-1-data-pelabelan/generate_protokol_label_historis.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from doc_render import (  # noqa: E402
    Bullets, Dokumen, H1, H2, Note, Numbered, P, Table, hari_ini, tulis_dua_format,
)

VERSI = "v1.0 (draf)"

PENILAIAN = [
    ["TEPAT", "Menurut kondisi keluarga pada masa itu, keputusan tersebut sudah sesuai.",
     "Label dipakai apa adanya."],
    ["TIDAK TEPAT", "Keputusan tersebut tidak sesuai dengan kondisi keluarga pada masa itu.",
     "Dicatat sebagai usulan koreksi beserta alasannya."],
    ["TIDAK TAHU", "Informasi tidak cukup untuk menilai, atau petugas tidak menangani wilayah/periode "
                   "tersebut.", "Baris dikeluarkan dari perhitungan, tidak dipaksa menjadi salah satu."],
]

LEMBAR = [
    ["kode_kk", "Kode unik keluarga (bukan NIK/nama)"],
    ["periode", "Tahun/periode penyaluran bantuan yang dinilai"],
    ["label_asli", "Keputusan yang tercatat: menerima / tidak menerima"],
    ["penilaian", "TEPAT / TIDAK TEPAT / TIDAK TAHU"],
    ["label_koreksi", "Diisi hanya bila penilaian TIDAK TEPAT"],
    ["alasan", "Alasan singkat, satu kalimat"],
    ["petugas", "Nama/inisial petugas penilai"],
    ["tanggal", "Tanggal penilaian"],
]

ARAH = [
    ["Menerima, dinilai TIDAK TEPAT", "Bantuan pernah diberikan kepada keluarga yang dinilai belum "
     "seharusnya menerima.", "Model cenderung terlalu longgar - meloloskan yang belum layak."],
    ["Tidak menerima, dinilai TIDAK TEPAT", "Keluarga yang dinilai seharusnya menerima justru "
     "terlewat.", "Model cenderung terlalu ketat - inilah bentuk ketidakadilan yang paling merugikan "
     "warga."],
]

TINDAK_LANJUT = [
    ["Di bawah 10 persen", "Label historis dipakai apa adanya; koreksi tetap diterapkan pada baris "
     "yang bersangkutan, dan tingkat kesalahan dilaporkan sebagai catatan."],
    ["10 sampai 25 persen", "Model Tier 2 dilatih dua kali - dengan dan tanpa koreksi - lalu kedua "
     "hasilnya dibandingkan dan dibahas."],
    ["Di atas 25 persen", "Label historis tidak cukup andal untuk dijadikan satu-satunya acuan. "
     "Perluas sampel validasi dan bahas ulang bersama pembimbing sebelum melanjutkan pelatihan."],
]


def bangun_dokumen() -> Dokumen:
    return Dokumen(
        judul="Protokol Validasi Label Historis Penerima Bansos",
        subjudul="DSS Bansos - Kelurahan Bontoramba",
        kicker="Panduan sesi validasi bersama petugas kelurahan - resolusi OI-10",
        meta=[
            ("Versi", VERSI),
            ("Tanggal", hari_ini()),
            ("Peneliti", "Muhammad Gilang"),
            ("Penilai", "Petugas kelurahan yang menangani penyaluran bansos"),
            ("Dasar", "TRD Bab 6.1 & 7.2; OI-10; risiko R-05"),
        ],
        intro=(
            "Sistem DSS ini belajar dari keputusan penyaluran bansos periode sebelumnya: data siapa "
            "yang dahulu menerima dan siapa yang tidak dipakai sebagai contoh yang benar saat melatih "
            "model. Konsekuensinya lugas - bila ada keputusan lama yang keliru, model akan "
            "mempelajari kekeliruan itu dan mengulanginya secara otomatis pada setiap pengajuan baru. "
            "Protokol ini adalah langkah pemeriksaan agar hal tersebut diketahui lebih dulu, bukan "
            "ditemukan setelah sistem dipakai."
        ),
        blok=[
            H1(1, "Tujuan"),
            Bullets([
                "Mengukur seberapa sering keputusan penyaluran periode lalu dinilai tidak tepat oleh "
                "petugas yang memahami kondisi lapangan.",
                "Mengetahui **arah** kecenderungan kekeliruan - lebih sering meloloskan yang belum "
                "layak, atau lebih sering melewatkan yang layak.",
                "Menyediakan dasar tertulis untuk membahas keterbatasan data pada laporan penelitian.",
            ]),
            Note(
                "Kegiatan ini bukan audit dan bukan penilaian atas kinerja siapa pun. Sasarannya "
                "adalah kualitas data yang akan dipakai melatih sistem. Tidak ada nama petugas "
                "pengambil keputusan lama yang dicatat maupun dilaporkan.",
                judul="Yang perlu ditegaskan di awal sesi",
            ),

            H1(2, "Siapa yang Menilai"),
            P("Penilaian hanya boleh dilakukan oleh **petugas kelurahan yang berwenang** dan memahami "
              "kondisi keluarga pada periode yang dinilai. Peneliti dan pelabel mahasiswa **tidak "
              "menilai dan tidak mengoreksi** label historis; peran peneliti terbatas pada menyiapkan "
              "sampel, mencatat hasil, dan mengolahnya."),

            H1(3, "Prosedur"),
            Numbered([
                "Peneliti mengambil **sampel acak 30 sampai 50 keluarga** dari data penerima periode "
                "sebelumnya, dengan komposisi mencakup keduanya: yang menerima dan yang tidak menerima.",
                "Untuk setiap keluarga, petugas melihat keputusan yang tercatat lalu menjawab satu "
                "pertanyaan: **\"Menurut kondisi keluarga ini pada masa itu, apakah keputusan tersebut "
                "sudah tepat?\"**",
                "Jawaban dipilih dari tiga kemungkinan pada Bagian 4, disertai alasan singkat satu "
                "kalimat.",
                "Bila jawabannya TIDAK TEPAT, petugas menuliskan keputusan yang menurutnya seharusnya "
                "diambil pada kolom koreksi.",
                "Peneliti merekap hasil, menghitung persentase serta arah kekeliruan, lalu "
                "mengembalikan ringkasannya kepada kelurahan.",
            ]),
            Note(
                "Nilailah berdasarkan kondisi keluarga **pada masa keputusan itu diambil**, bukan "
                "kondisinya sekarang. Keluarga yang keadaannya sudah membaik hari ini bisa saja dahulu "
                "memang layak menerima.",
                judul="Pegangan saat menilai",
            ),

            H1(4, "Tiga Pilihan Penilaian"),
            Table(["Pilihan", "Arti", "Perlakuan data"], PENILAIAN, lebar=[16, 47, 37]),

            H1(5, "Lembar Penilaian"),
            P("Data yang dibawa ke sesi sudah tanpa NIK dan tanpa nama, memakai kode unik per keluarga, "
              "sejalan dengan ketentuan penanganan data yang disepakati."),
            Table(["Kolom", "Isi"], LEMBAR, lebar=[24, 76]),
            Bullets([
                "**Label asli tidak pernah ditimpa.** Koreksi ditulis pada kolom terpisah, sehingga "
                "kedua versi data tetap tersedia dan dapat dibandingkan.",
                "Setiap koreksi wajib disertai alasan, nama petugas, dan tanggal - tanpa itu koreksi "
                "tidak dapat dipertanggungjawabkan dalam laporan penelitian.",
            ]),

            H1(6, "Membaca Hasil"),
            H2("Arah kekeliruan"),
            Table(["Pola", "Artinya", "Dampak bila dibiarkan"], ARAH, lebar=[24, 38, 38]),
            H2("Tindak lanjut menurut tingkat kekeliruan"),
            Table(["Persentase dinilai TIDAK TEPAT", "Tindak lanjut"], TINDAK_LANJUT, lebar=[26, 74]),
            P("Persentase dihitung dari baris yang dinilai saja; baris TIDAK TAHU dikeluarkan dari "
              "penyebut dan jumlahnya dilaporkan terpisah."),

            H1(7, "Yang Dilaporkan dalam Skripsi"),
            Bullets([
                "Jumlah sampel yang divalidasi dan persentase yang dinilai tidak tepat.",
                "Arah kekeliruan yang ditemukan.",
                "Perbandingan kinerja model Tier 2 ketika dilatih **dengan** dan **tanpa** koreksi - "
                "akurasi, precision, recall, dan confusion matrix untuk kedua versi.",
                "Pembahasan keterbatasan: model belajar dari keputusan manusia, sehingga sebagian "
                "prasangka lama dapat tetap terbawa meski koreksi sudah diterapkan.",
            ]),
            Note(
                "Bila kelurahan tidak dapat memberikan akses untuk melakukan koreksi, penelitian tetap "
                "berjalan memakai label apa adanya - dan protokol ini tetap dilampirkan sebagai "
                "pembahasan keterbatasan. Itu adalah pilihan yang memang disediakan pada OI-10. Yang "
                "tidak boleh terjadi adalah memakai label lama tanpa menyebutkan risikonya sama "
                "sekali.",
                judul="Bila validasi tidak dapat dilaksanakan",
            ),

            H1(8, "Ringkasan Kebutuhan dari Kelurahan"),
            Bullets([
                "Satu sesi bersama petugas yang menangani penyaluran bansos, perkiraan 60 sampai 90 "
                "menit untuk 30 sampai 50 keluarga.",
                "Kesediaan menilai keputusan periode lalu dan memberikan alasan singkat.",
                "Tidak diperlukan berkas tambahan apa pun di luar data yang sudah diserahkan.",
            ]),
        ],
    )


def main() -> None:
    dasar = Path(__file__).parent / "protokol-validasi-label-historis"
    md, pdf = tulis_dua_format(bangun_dokumen(), dasar)
    print(f"Markdown : {md}")
    print(f"PDF      : {pdf}")


if __name__ == "__main__":
    main()
