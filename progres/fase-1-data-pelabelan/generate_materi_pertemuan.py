"""Generator dokumen pertemuan Kelurahan Bontoramba (Senin, 7 September 2026).

Menghasilkan TIGA dokumen `.md` + `.pdf` dari satu sumber konten, karena audiensnya berbeda dan
tidak boleh tercampur:

    materi-pertemuan-kelurahan       PEGANGAN PENELITI  - jangan diserahkan; memuat taktik & catatan
    lampiran-permintaan-data-anonim  DISERAHKAN         - lampiran surat, bahasa netral
    lembar-pembobotan-kriteria       DIISI PETUGAS      - lembar kerja sesi pembobotan (OI-12/OI-13)

Latar: surat permohonan data (masuk 4 September 2026) ditolak sebagian - pihak kelurahan tidak
bersedia menyerahkan data diri riwayat penerima bantuan. Analisis & permintaan yang disusun ulang
ada di `permintaan-data-kelurahan-revisi.md`; dokumen di sini adalah bentuk siap-pakainya.

Jalankan:
    .venv/Scripts/python.exe progres/fase-1-data-pelabelan/generate_materi_pertemuan.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from doc_render import (  # noqa: E402
    Bullets, Dokumen, H1, H2, Note, Numbered, P, Table, hari_ini, tulis_dua_format,
)

VERSI = "v1.0"
TANGGAL_PERTEMUAN = "Senin, 7 September 2026"

# Ruang tulis tangan di dalam sel tabel: tiap "\n" menambah satu baris tinggi sel.
TULIS = "\n\n"
TULIS_PANJANG = "\n\n\n"

# Empat kriteria Tier 3 persis seperti di config/fuzzy_config.yaml. Bobot provisional
# (0,35 / 0,20 / 0,20 / 0,25) SENGAJA tidak dicantumkan di lembar isian - lihat Bagian C
# pegangan peneliti: menunjukkannya lebih dulu membuat petugas sekadar menyetujui.
KRITERIA = [
    ("Penghasilan keluarga", "Penghasilan per orang per bulan dalam satu keluarga."),
    ("Jumlah tanggungan", "Berapa orang yang harus dihidupi oleh keluarga tersebut."),
    ("Kondisi kelayakan rumah", "Lantai, dinding, sumber air bersih, dan luas rumah."),
    ("Kegentingan keadaan", "Seberapa mendesak keadaan yang diuraikan dalam keterangan kondisi "
                            "keluarga - misalnya sakit menahun, kehilangan pekerjaan, atau musibah."),
]

KOLOM_DIMINTA = [
    ["kode", "KK-001, KK-002, dan seterusnya", "Pengganti identitas, dibuat oleh kelurahan"],
    ["usia kepala keluarga", "Angka, dalam tahun", ""],
    ["jumlah tanggungan", "Angka", "Jumlah orang yang dihidupi"],
    ["penghasilan", "Rupiah per bulan", "Boleh berupa rentang, misalnya 500.000-1.000.000"],
    ["status pekerjaan", "Teks singkat", "Misalnya: petani, buruh harian, tidak bekerja"],
    ["aset produktif", "Ya / Tidak", "Kepemilikan sawah, ternak, kendaraan usaha, dan sejenisnya"],
    ["pernah menerima bantuan", "Ya / Tidak", "TANPA menyebut nama program maupun tanggalnya"],
    ["jenis lantai", "tanah / kayu / papan / semen / plester / ubin / keramik", "Pilih satu istilah"],
    ["jenis dinding", "bambu / anyaman / kayu / papan / seng / batu bata / tembok", "Pilih satu istilah"],
    ["sumber air", "sungai / hujan / mata air / sumur / sumur bor / pdam / ledeng", "Pilih satu istilah"],
    ["luas rumah", "Meter persegi", ""],
    ["status penerima", "Layak / Tidak layak", "Keterangan inilah yang dipelajari sistem"],
]

KOLOM_TIDAK_DIMINTA = [
    "Nomor Induk Kependudukan (NIK)",
    "Nama kepala keluarga maupun nama anggota keluarga",
    "Alamat dan nomor Kartu Keluarga",
    "Nomor telepon dan tanggal lahir",
    "Foto rumah maupun foto keluarga",
    "Nomor rekening dan data keuangan pribadi lainnya",
]

PILIHAN_PENYERAHAN = [
    ["Pilihan 1 - Berkas tanpa identitas",
     "Petugas kelurahan menghapus sendiri kolom identitas, mengganti setiap baris dengan kode urut, "
     "lalu menyerahkan berkasnya dalam bentuk Excel atau salinan cetak.",
     "Yang berpindah tangan sudah bukan data pribadi."],
    ["Pilihan 2 - Pengolahan di tempat",
     "Berkas tidak keluar dari kantor kelurahan. Peneliti datang pada waktu yang disepakati, petugas "
     "yang membuka berkas, dan peneliti hanya menyalin kolom pada Bagian 2 ke dalam lembar kerja "
     "berkode.",
     "Tidak ada berkas yang dibawa pulang."],
    ["Pilihan 3 - Kelurahan hanya memberi penilaian",
     "Peneliti mengumpulkan sendiri data dari warga yang bersedia, lalu petugas cukup menilai "
     "layak atau tidak layak atas berkas berkode tersebut.",
     "Kelurahan tidak menyerahkan data apa pun."],
]


# ---------------------------------------------------------------------------
# Dokumen 1 - pegangan peneliti (JANGAN diserahkan)
# ---------------------------------------------------------------------------

def dokumen_materi() -> Dokumen:
    return Dokumen(
        judul="Materi & Daftar Pertanyaan Pertemuan Kelurahan",
        subjudul="Pegangan peneliti - JANGAN diserahkan kepada pihak kelurahan",
        kicker=f"Pertemuan {TANGGAL_PERTEMUAN} - Kelurahan Bontoramba",
        meta=[
            ("Versi", VERSI),
            ("Disusun", hari_ini()),
            ("Peneliti", "Muhammad Gilang"),
            ("Perkiraan durasi", "60 sampai 90 menit"),
            ("Dibawa", "Lampiran Permintaan Data + Lembar Pembobotan Kriteria (dokumen terpisah)"),
        ],
        intro=(
            "Surat permohonan data yang masuk 4 September 2026 ditolak sebagian: pihak kelurahan "
            "tidak bersedia menyerahkan data diri riwayat penerima bantuan karena bersifat sensitif. "
            "Pertemuan ini BUKAN untuk membantah penolakan itu. Penolakannya benar menurut Undang-"
            "Undang Nomor 27 Tahun 2022 tentang Pelindungan Data Pribadi, dan tidak akan berubah oleh "
            "permintaan yang diulang dengan nada lebih memohon. Yang mengubah keadaan hanya satu hal: "
            "mengubah bentuk permintaannya, sampai tidak ada lagi data pribadi di dalamnya."
        ),
        blok=[
            H1(1, "Tiga Hasil yang Harus Dibawa Pulang"),
            P("Disusun menurut prioritas. Bila waktu habis, pastikan nomor 1 dan 2 selesai - keduanya "
              "tidak menyentuh data pribadi sama sekali, sehingga alasan penolakan kemarin tidak "
              "berlaku untuk keduanya."),
            Table(
                header=["Prioritas", "Hasil yang dikejar", "Mengapa ini yang didahulukan"],
                baris=[
                    ["1", "Lembar Pembobotan Kriteria terisi dan ditandatangani",
                     "Menutup butir yang tertunda sejak perancangan metode: bobot kriteria "
                     "perangkingan sampai kini masih memakai nilai sementara yang ditetapkan sendiri "
                     "oleh peneliti. Sekali terisi, butir ini selesai selamanya."],
                    ["2", "Jawaban atas lima pertanyaan konfirmasi (Bagian A)",
                     "Menentukan seluruh rencana berikutnya - terutama apakah arsip kelurahan memuat "
                     "uraian kalimat atau tidak."],
                    ["3", "Kesediaan dua sampai tiga petugas ikut sesi penilaian dan uji coba, "
                     "beserta tanggalnya",
                     "Satu-satunya jalan menuju angka efektivitas sistem. Ini permintaan waktu, "
                     "bukan permintaan data."],
                    ["4 (bonus)", "Kesepakatan bentuk penyerahan data tanpa identitas",
                     "Bila tercapai, penelitian memakai data kelurahan. Bila tidak, rencana "
                     "pengumpulan data langsung ke warga tetap berjalan."],
                ],
                lebar=[10, 34, 56],
            ),
            Note(
                "Jangan menaruh seluruh harapan pada nomor 4. Nomor 1 sampai 3 sudah cukup untuk "
                "membuat penelitian ini berjalan utuh, dan ketiganya berada di luar jangkauan alasan "
                "penolakan kemarin. Bila nomor 4 gagal pun, pertemuan ini tetap berhasil.",
                judul="Ukuran keberhasilan pertemuan",
            ),

            H1(2, "Cara Membuka Pertemuan"),
            P("Buka dengan mengakui penolakannya, bukan dengan mempertanyakannya. Petugas yang "
              "menolak kemarin sedang menjalankan aturan, dan menunjukkan bahwa hal itu dipahami "
              "akan mengubah seluruh nada pertemuan."),
            P("Kalimat pembuka yang disarankan:", tebal=True),
            Bullets([
                "\"Terima kasih sudah menanggapi surat saya. Setelah saya pelajari, keberatan Bapak/Ibu "
                "soal data penerima itu memang tepat - data seperti itu tidak boleh diserahkan begitu "
                "saja, dan saya tidak akan memintanya lagi.\"",
                "\"Kedatangan saya hari ini justru untuk memperbaiki permintaan saya. Setelah saya "
                "periksa kembali, ternyata sistem yang saya bangun sama sekali tidak membutuhkan "
                "identitas siapa pun - yang dibutuhkan hanya angka dan kategori.\"",
                "\"Ada juga beberapa hal yang saya butuhkan dan sama sekali tidak berhubungan dengan "
                "data warga. Justru itu yang paling penting bagi saya hari ini.\"",
            ]),

            H2("Yang tidak boleh dikatakan"),
            Table(
                header=["Jangan", "Sebabnya"],
                baris=[
                    ["Menyebut ulang frasa \"data diri riwayat penerima bantuan\"",
                     "Itu frasa yang memicu penolakan. Sekali terucap, pertemuan kembali ke titik "
                     "yang sama."],
                    ["Mengutip undang-undang untuk membantah petugas",
                     "Terdengar menggurui, dan tidak ada yang bisa dimenangkan dari perdebatan itu. "
                     "Undang-undang justru sedang berpihak pada mereka."],
                    ["Menyatakan data akan aman \"karena hanya untuk skripsi\"",
                     "Alasan itu tidak mengubah status hukum data pribadi, dan pihak kelurahan "
                     "mengetahuinya."],
                    ["Meminta seluruh kebutuhan dalam satu paket sekaligus",
                     "Inilah kesalahan surat pertama: satu butir yang tidak boleh disetujui "
                     "menjatuhkan seluruh permintaan. Ajukan berlapis."],
                ],
                lebar=[38, 62],
            ),

            H1(3, "Bagian A - Lima Pertanyaan Konfirmasi"),
            P("Ajukan lebih dulu, sebelum permintaan apa pun. Jawabannya menentukan sisa pertemuan, "
              "dan tidak satu pun menyinggung data pribadi. Sediakan waktu menulis jawabannya."),
            Table(
                header=["#", "Pertanyaan", "Mengapa penting", "Jawaban"],
                baris=[
                    ["1", "Apakah berkas pengajuan atau verifikasi memuat uraian kondisi keluarga "
                          "dalam bentuk kalimat - misalnya catatan petugas - atau seluruhnya berupa "
                          "kolom isian?",
                     "PALING MENENTUKAN. Salah satu bagian sistem membaca uraian kalimat. Bila arsip "
                     "hanya berupa kolom, uraian itu memang tidak pernah ada di kelurahan, dan "
                     "harus dikumpulkan sendiri dari warga.", TULIS_PANJANG],
                    ["2", "Arsipnya berbentuk apa - berkas kertas, Excel, atau aplikasi seperti "
                          "SIKS-NG?",
                     "Menentukan apakah penyalinan tanpa identitas bisa dikerjakan dengan cepat atau "
                     "harus manual.", TULIS],
                    ["3", "Berapa gelombang penyaluran bantuan dalam setahun, dan berapa kuota "
                          "penerima tiap gelombang?",
                     "Angka agregat, bukan data orang. Dipakai menetapkan jumlah penerima pada "
                     "perhitungan peringkat.", TULIS],
                    ["4", "Siapa yang berwenang memutuskan pemberian data tanpa identitas - cukup "
                          "Lurah, atau harus melalui Dinas Sosial kabupaten?",
                     "Menentukan kepada siapa surat berikutnya ditujukan. Salah alamat berarti "
                     "kehilangan dua sampai tiga minggu.", TULIS],
                    ["5", "Apakah ada format atau prosedur baku permintaan data untuk keperluan "
                          "penelitian?",
                     "Bila ada, ikuti persis. Surat yang mengikuti format mereka jauh lebih mudah "
                     "disetujui.", TULIS],
                ],
                lebar=[5, 30, 35, 30],
            ),

            H1(4, "Bagian B - Permintaan yang Tidak Menyentuh Data Warga"),
            P("Sampaikan bagian ini sebagai permintaan tersendiri, dan tegaskan bahwa tidak satu pun "
              "butir di dalamnya berkaitan dengan data perorangan. Inilah bagian dengan peluang "
              "disetujui paling tinggi."),
            Numbered([
                "Jumlah kuota dan anggaran bantuan per gelombang penyaluran - angka keseluruhan, "
                "bukan per orang.",
                "Dokumen kriteria dan prosedur penentuan penerima yang berlaku sekarang - petunjuk "
                "teknis, surat edaran, atau catatan prosedur.",
                "Pembobotan kepentingan antar kriteria menurut petugas - dikerjakan langsung di "
                "pertemuan ini memakai Lembar Pembobotan Kriteria.",
                "Statistik keseluruhan kelurahan: jumlah kepala keluarga, sebaran jenis pekerjaan, "
                "jumlah penerima per gelombang.",
                "Kesediaan dua sampai tiga petugas mengikuti satu sesi penilaian dan satu sesi uji "
                "coba sistem.",
            ]),

            H1(5, "Bagian C - Memandu Sesi Pembobotan Kriteria"),
            P("Ini bagian terpenting pertemuan, dan yang paling mudah dirusak oleh cara bertanya yang "
              "keliru. Alokasikan 15 sampai 20 menit."),
            Note(
                "JANGAN menyebutkan nilai bobot yang sekarang dipakai sistem (penghasilan 0,35; "
                "tanggungan 0,20; kondisi rumah 0,20; kegentingan 0,25) SEBELUM petugas mengisi "
                "lembarnya. Bila angka itu disebut lebih dulu, petugas cenderung sekadar "
                "menyetujuinya, dan hasilnya bukan lagi pendapat kelurahan melainkan pantulan "
                "tebakan peneliti sendiri. Tunjukkan perbandingannya SESUDAH lembar terisi - dan "
                "bila ternyata berbeda jauh, itu temuan yang berharga, bukan masalah.",
                judul="Aturan yang menentukan sah atau tidaknya hasil sesi ini",
            ),
            Bullets([
                "Hindari istilah teknis. Jangan sebut \"bobot fuzzy\", \"kriteria TOPSIS\", atau "
                "\"fungsi keanggotaan\". Cukup: \"seberapa penting\" dan \"batas berapa\".",
                "Minta petugas MENGURUTKAN keempat kriteria lebih dulu, baru memberi angka. Urutan "
                "lebih mudah dijawab daripada angka, dan angkanya jadi lebih konsisten.",
                "Bila memungkinkan, mintalah dua atau tiga petugas mengisi lembar MASING-MASING, "
                "tidak berunding jadi satu. Perbedaan di antara mereka adalah data, bukan gangguan - "
                "dan bila selisihnya besar, hal itu wajib ditulis di laporan.",
                "Langkah 3 pada lembar (batas nilai penghasilan) sama pentingnya dengan bobotnya. "
                "Nilai yang dipakai sistem sekarang - 500 ribu, 1 juta, 2 juta - murni tebakan "
                "peneliti dan belum pernah diperiksa siapa pun.",
                "Tutup dengan membacakan ulang hasil isiannya, lalu minta tanda tangan dan nama "
                "terang. Tanpa tanda tangan, hasilnya tidak dapat dilampirkan ke laporan.",
            ]),
            P("Bahan pendukung bila petugas bertanya seberapa besar pengaruh angka ini:", tebal=True),
            P("Pengujian yang sudah dilakukan menunjukkan bahwa menggeser bobot sampai 20 persen "
              "hanya mengubah 3 sampai 7 persen urutan penerima. Artinya angka ini tidak perlu "
              "sempurna - tetapi harus berasal dari pihak yang memahami keadaan warga, bukan dari "
              "mahasiswa yang menebak. Sampaikan apa adanya; kejujuran ini justru membuat "
              "permintaannya masuk akal."),

            H1(6, "Bagian D - Menawarkan Bentuk Data yang Baru"),
            P("Baru masuk bagian ini setelah Bagian A sampai C selesai. Serahkan Lampiran Permintaan "
              "Data, dan tunjuk langsung ke daftar \"data yang tidak diminta\" - itu bagian yang "
              "paling menenangkan pihak kelurahan."),
            P("Tawarkan ketiga pilihan secara berjenjang, dan biarkan mereka memilih yang paling "
              "ringan. Jangan memaksakan Pilihan 1."),
            Table(
                header=["Pilihan", "Isi", "Kalimat penawaran"],
                baris=[
                    ["1", "Berkas tanpa identitas, disiapkan kelurahan",
                     "\"Kalau memungkinkan, Bapak/Ibu yang menghapus kolom nama dan NIK-nya, lalu "
                     "diganti kode urut. Yang saya terima sudah bukan data pribadi lagi.\""],
                    ["2", "Pengolahan di tempat",
                     "\"Kalau berkasnya tidak boleh keluar kantor, saya bisa datang ke sini. Bapak/Ibu "
                     "yang membuka berkasnya, saya hanya menyalin angkanya. Tidak ada yang saya bawa "
                     "pulang.\""],
                    ["3", "Kelurahan hanya menilai",
                     "\"Kalau keduanya tetap tidak memungkinkan, saya kumpulkan sendiri datanya dari "
                     "warga yang bersedia. Bapak/Ibu cukup menilai layak atau tidak layak, tanpa "
                     "menyerahkan data apa pun.\""],
                ],
                lebar=[13, 29, 58],
            ),
            Note(
                "Pilihan 3 hampir selalu dapat diterima, karena kelurahan tidak menyerahkan apa pun. "
                "Bila Pilihan 1 dan 2 ditolak, JANGAN tutup pembicaraan - langsung tawarkan "
                "Pilihan 3, dan pertemuan tetap membuahkan hasil.",
                judul="Jaring pengaman",
            ),

            H1(7, "Bagian E - Kesediaan Petugas dan Jadwal"),
            P("Sampaikan bahwa yang diminta adalah waktu, bukan data, dan sebutkan durasinya secara "
              "jujur. Bawa pulang tanggalnya, jangan hanya kesediaan lisan."),
            Table(
                header=["Kegiatan", "Kebutuhan", "Durasi", "Tanggal disepakati"],
                baris=[
                    ["Sesi penilaian kelayakan", "2 sampai 3 petugas yang memahami kondisi warga",
                     "60 sampai 90 menit", TULIS],
                    ["Uji coba sistem oleh petugas", "2 sampai 3 petugas, memakai laptop peneliti",
                     "60 menit", TULIS],
                ],
                lebar=[26, 34, 16, 24],
            ),

            H1(8, "Bagian F - Izin Sosial Mengumpulkan Data dari Warga"),
            P("Pertanyaan yang paling sering terlupakan, dan paling merugikan bila terlupa. "
              "Pengumpulan data langsung dari warga yang bersedia secara hukum tidak memerlukan izin "
              "kelurahan - tetapi mengerjakannya tanpa sepengetahuan kelurahan berisiko menimbulkan "
              "salah paham di lapangan, dan dapat menutup pintu yang masih terbuka."),
            P("Tanyakan: \"Seandainya saya mengumpulkan sendiri datanya dari warga yang bersedia, "
              "dengan lembar persetujuan dan tanpa mencatat nama, apakah pihak kelurahan berkeberatan? "
              "Dan apakah sebaiknya saya didampingi ketua RT/RW?\"", tebal=True),
            P("Bila jawabannya tidak berkeberatan, catat siapa yang menyampaikannya. Bila menawarkan "
              "pendampingan RT/RW, terima - itu mempercepat pekerjaan lapangan sekaligus menjadikannya "
              "resmi."),

            H1(9, "Bila Semuanya Ditolak"),
            Bullets([
                "Jangan menunjukkan kekecewaan, dan jangan menutup pembicaraan dengan nada menyerah. "
                "Pertemuan berikutnya masih dibutuhkan untuk uji coba sistem.",
                "Pastikan Bagian B dan E tetap dibawa pulang - keduanya tidak pernah bergantung pada "
                "penyerahan data.",
                "Pastikan Bagian F terjawab. Selama pengumpulan data dari warga tidak dipersoalkan, "
                "penelitian ini tetap dapat diselesaikan secara utuh.",
                "Tanyakan apakah pihak kelurahan bersedia menerima presentasi hasil setelah sistemnya "
                "jadi. Menawarkan sesuatu kembali sering membuka pintu yang tadinya tertutup.",
            ]),

            H1(10, "Lembar Catatan Hasil"),
            P("Isi sebelum meninggalkan kantor kelurahan, jangan ditunda sampai di rumah."),
            Table(
                header=["Butir", "Hasil", "Tindak lanjut & tenggat"],
                baris=[
                    ["Lembar pembobotan terisi", TULIS, TULIS],
                    ["Jumlah petugas yang mengisi", TULIS, TULIS],
                    ["Arsip memuat uraian kalimat?", TULIS, TULIS],
                    ["Bentuk arsip", TULIS, TULIS],
                    ["Kuota per gelombang", TULIS, TULIS],
                    ["Pihak yang berwenang memberi izin data", TULIS, TULIS],
                    ["Pilihan penyerahan yang disepakati", TULIS, TULIS],
                    ["Tanggal sesi penilaian", TULIS, TULIS],
                    ["Tanggal uji coba sistem", TULIS, TULIS],
                    ["Keberatan atas pengumpulan data dari warga", TULIS, TULIS],
                    ["Nama & jabatan penerima tamu", TULIS, TULIS],
                ],
                lebar=[34, 33, 33],
            ),

            H1(11, "Daftar Bawaan"),
            Bullets([
                "Surat pengantar dari kampus (bawa salinan cadangan).",
                "Lampiran Permintaan Data - cetak dua rangkap, satu untuk ditinggalkan.",
                "Lembar Pembobotan Kriteria - cetak minimal tiga rangkap, satu per petugas.",
                "Kartu tanda mahasiswa dan tanda pengenal.",
                "Alat tulis, papan jalan, dan map untuk berkas yang mungkin diserahkan.",
                "Laptop - hanya bila diminta memperagakan sistemnya. Bila diperagakan, sampaikan "
                "sejak awal bahwa data yang tampil masih data contoh, bukan data warga sungguhan.",
                "Ponsel untuk memotret dokumen yang boleh difoto - minta izin lebih dulu, setiap kali.",
            ]),
        ],
    )


# ---------------------------------------------------------------------------
# Dokumen 2 - lampiran yang diserahkan ke kelurahan
# ---------------------------------------------------------------------------

def dokumen_lampiran() -> Dokumen:
    return Dokumen(
        judul="Lampiran Permintaan Data Penelitian",
        subjudul="Bentuk data tanpa identitas - pengganti permintaan sebelumnya",
        kicker="Kelurahan Bontoramba",
        meta=[
            # Tanggal pertemuan, bukan tanggal pembuatan berkas: lampiran ini DISERAHKAN saat
            # pertemuan, jadi tanggal yang tercetak harus tanggal penyerahannya. Bila jadwal
            # bergeser, ubah TANGGAL_PERTEMUAN lalu jalankan ulang generator ini.
            ("Tanggal", TANGGAL_PERTEMUAN),
            ("Peneliti", "Muhammad Gilang"),
            ("Program studi", "____________________________"),
            ("Dosen pembimbing", "____________________________"),
            ("Judul penelitian", "Sistem Pendukung Keputusan Penentuan Kelayakan dan Prioritas "
                                 "Penerima Bantuan Sosial"),
        ],
        intro=(
            "Lampiran ini menggantikan bentuk permintaan data pada surat sebelumnya. Setelah "
            "menerima keberatan dari pihak Kelurahan Bontoramba mengenai data penerima bantuan, "
            "permintaan disusun ulang sehingga tidak lagi memuat data pribadi dalam bentuk apa pun. "
            "Keberatan tersebut dipahami sebagai hal yang sudah semestinya, dan permintaan lama "
            "tidak diajukan kembali."
        ),
        blok=[
            H1(1, "Pokok Perubahan"),
            P("Sistem yang dibangun dalam penelitian ini bekerja atas angka dan kategori, bukan atas "
              "identitas seseorang. Nama, Nomor Induk Kependudukan, dan alamat tidak pernah "
              "diperlukan pada proses perhitungannya. Karena itu permintaan data dapat dipenuhi "
              "sepenuhnya oleh tabel yang setiap barisnya hanya bertanda kode urut."),

            H1(2, "Data yang Diminta"),
            P("Setiap baris mewakili satu keluarga, ditandai kode urut yang dibuat oleh pihak "
              "kelurahan. Untuk tiga kolom kondisi rumah, mohon dipilih salah satu istilah yang "
              "tercantum, karena istilah di luar daftar tidak dapat dibaca oleh sistem."),
            Table(
                header=["Kolom", "Bentuk isian", "Keterangan"],
                baris=KOLOM_DIMINTA,
                lebar=[24, 43, 33],
            ),
            P("Jumlah baris yang diharapkan sekurang-kurangnya 100 keluarga, dengan komposisi "
              "mencakup keduanya: yang dinilai layak dan yang dinilai tidak layak."),

            H1(3, "Data yang TIDAK Diminta"),
            P("Keterangan berikut tidak diperlukan, tidak diminta, dan mohon tidak disertakan "
              "sekalipun tersedia:", tebal=True),
            Bullets(KOLOM_TIDAK_DIMINTA),
            P("Apabila salah satu keterangan di atas ikut terbawa, peneliti akan menghapusnya "
              "sebelum data digunakan, dan hal tersebut akan diberitahukan kepada pihak kelurahan."),

            H1(4, "Tiga Pilihan Bentuk Penyerahan"),
            P("Pihak kelurahan dipersilakan memilih bentuk yang paling sesuai dengan ketentuan yang "
              "berlaku. Ketiganya sama-sama mencukupi bagi penelitian ini."),
            Table(
                header=["Pilihan", "Cara pelaksanaan", "Kedudukan data"],
                baris=PILIHAN_PENYERAHAN,
                lebar=[24, 50, 26],
            ),

            H1(5, "Keterangan yang Tidak Berkaitan dengan Data Warga"),
            P("Selain tabel di atas, penelitian ini membutuhkan keterangan berikut, yang seluruhnya "
              "tidak berhubungan dengan data perorangan:"),
            Numbered([
                "Jumlah kuota dan anggaran bantuan pada setiap gelombang penyaluran.",
                "Dokumen kriteria dan prosedur penentuan penerima yang berlaku saat ini.",
                "Pendapat petugas mengenai tingkat kepentingan antar kriteria penentuan penerima, "
                "melalui lembar isian yang disediakan peneliti.",
                "Data statistik keseluruhan kelurahan: jumlah kepala keluarga, sebaran jenis "
                "pekerjaan, dan jumlah penerima pada setiap gelombang.",
                "Kesediaan dua sampai tiga petugas mengikuti satu sesi penilaian kelayakan dan satu "
                "sesi uji coba sistem, masing-masing sekitar satu jam.",
            ]),

            H1(6, "Pernyataan Penanganan Data"),
            P("Peneliti menyatakan hal-hal berikut mengikat dirinya:", tebal=True),
            Numbered([
                "Data disimpan pada satu perangkat milik peneliti tanpa disalin ke layanan "
                "penyimpanan daring mana pun.",
                "Data digunakan semata-mata untuk keperluan penyusunan tugas akhir ini.",
                "Tidak ada baris data perorangan yang ditampilkan pada laporan, presentasi, maupun "
                "publikasi. Yang ditampilkan hanya angka keseluruhan.",
                "Data tidak dibagikan kepada pihak mana pun di luar peneliti dan dosen pembimbing.",
                "Seluruh salinan data dihapus setelah tugas akhir dinyatakan selesai, dan "
                "pemberitahuan penghapusan disampaikan kepada pihak kelurahan apabila diminta.",
                "Apabila pihak kelurahan meminta penghentian penggunaan data sewaktu-waktu, "
                "permintaan tersebut dipenuhi tanpa syarat.",
            ]),

            H1(7, "Persetujuan"),
            Table(
                header=["Pihak Kelurahan Bontoramba", "Peneliti"],
                baris=[
                    ["Nama:\n\nJabatan:\n\nTanggal:\n\n\nTanda tangan:\n\n",
                     "Nama: Muhammad Gilang\n\nNIM:\n\nTanggal:\n\n\nTanda tangan:\n\n"],
                ],
                lebar=[50, 50],
                kolom1_tebal=False,
            ),
        ],
    )


# ---------------------------------------------------------------------------
# Dokumen 3 - lembar isian untuk petugas
# ---------------------------------------------------------------------------

def dokumen_pembobotan() -> Dokumen:
    # Kolom penjelasan sengaja TIDAK diulang di sini (sudah ada di Bagian 1): tanpa itu tabel
    # Langkah 1 dan Langkah 2 muat pada satu halaman, dan tabel isian empat kriteria tidak
    # terbelah - petugas yang mengisi lembar terbelah berisiko melewatkan kriteria terakhir.
    baris_urutan = [[nama, ""] for nama, _ in KRITERIA]
    baris_bobot = [[nama, "", ""] for nama, _ in KRITERIA]
    return Dokumen(
        judul="Lembar Pembobotan Kriteria Prioritas Penerima Bantuan",
        subjudul="Diisi oleh petugas Kelurahan Bontoramba",
        kicker="Satu lembar untuk satu petugas - mohon tidak diisi bersama-sama",
        meta=[
            ("Tanggal", "____________________"),
            ("Nama pengisi", "____________________________"),
            ("Jabatan", "____________________________"),
            ("Lama menangani penyaluran bantuan", "________ tahun"),
        ],
        intro=(
            "Sistem yang sedang dibangun mengurutkan calon penerima bantuan berdasarkan empat hal. "
            "Keempatnya tidak sama pentingnya, dan yang paling memahami perbandingannya adalah "
            "petugas yang menangani langsung di lapangan - bukan peneliti. Lembar ini menanyakan hal "
            "tersebut. Tidak ada jawaban benar atau salah, dan pengisian tidak memerlukan pengetahuan "
            "teknis apa pun."
        ),
        blok=[
            H1(1, "Empat Hal yang Dinilai"),
            Table(
                header=["Kriteria", "Yang dimaksud"],
                baris=[[nama, ket] for nama, ket in KRITERIA],
                lebar=[30, 70],
            ),

            H1(2, "Langkah 1 - Urutan Kepentingan"),
            P("Berilah nomor 1 sampai 4 pada kolom terakhir. Nomor 1 untuk yang PALING menentukan "
              "apakah sebuah keluarga layak diprioritaskan, dan nomor 4 untuk yang paling kurang "
              "menentukan. Setiap nomor hanya boleh dipakai satu kali."),
            Table(
                header=["Kriteria", "Urutan (1-4)"],
                baris=baris_urutan,
                lebar=[74, 26],
            ),

            H1(3, "Langkah 2 - Seberapa Besar Bedanya"),
            P("Setelah urutannya ditetapkan, bagilah angka 100 ke keempat kriteria menurut tingkat "
              "kepentingannya. Semakin penting, semakin besar angkanya. Jumlah seluruhnya harus tepat "
              "100."),
            P("Contoh cara mengisi - hanya contoh, bukan saran: 40 + 30 + 20 + 10 = 100.", tebal=True),
            Table(
                header=["Kriteria", "Angka (jumlah harus 100)", "Alasan singkat (boleh dikosongkan)"],
                baris=baris_bobot,
                lebar=[30, 22, 48],
            ),
            P("Jumlah:  ______________  (mohon diperiksa kembali agar tepat 100)", tebal=True),

            H1(4, "Langkah 3 - Batas Nilai Penghasilan"),
            P("Sistem perlu mengetahui, menurut keadaan warga Bontoramba, penghasilan sebesar apa "
              "yang tergolong sangat rendah dan sebesar apa yang sudah tergolong cukup. Angka yang "
              "dipakai sistem saat ini masih perkiraan peneliti dan belum pernah diperiksa siapa pun."),
            P("Yang dimaksud adalah penghasilan PER ORANG PER BULAN dalam satu keluarga - yaitu "
              "seluruh penghasilan keluarga dibagi jumlah anggotanya.", tebal=True),
            Table(
                header=["Golongan", "Menurut Bapak/Ibu, kisarannya berapa rupiah?"],
                baris=[
                    ["Sangat rendah", "di bawah Rp ______________________"],
                    ["Rendah", "Rp ____________ sampai Rp ____________"],
                    ["Sedang", "Rp ____________ sampai Rp ____________"],
                    ["Cukup / tinggi", "di atas Rp ______________________"],
                ],
                lebar=[26, 74],
            ),

            H1(5, "Langkah 4 - Jumlah Tanggungan"),
            Table(
                header=["Pertanyaan", "Jawaban"],
                baris=[
                    ["Berapa orang tanggungan yang menurut Bapak/Ibu sudah tergolong BANYAK untuk "
                     "satu keluarga?", "________ orang"],
                    ["Berapa jumlah tanggungan terbanyak yang pernah ditemui di kelurahan ini?",
                     "________ orang"],
                ],
                lebar=[64, 36],
            ),

            H1(6, "Langkah 5 - Kondisi Rumah"),
            P("Kondisi rumah dinilai dari empat hal. Berilah nomor 1 sampai 4, nomor 1 untuk yang "
              "paling menunjukkan bahwa sebuah keluarga membutuhkan bantuan."),
            Table(
                header=["Bagian rumah", "Urutan (1-4)"],
                baris=[
                    ["Jenis lantai", ""],
                    ["Jenis dinding", ""],
                    ["Sumber air bersih", ""],
                    ["Luas rumah dibanding jumlah penghuni", ""],
                ],
                lebar=[74, 26],
            ),

            H1(7, "Langkah 6 - Hal Lain yang Belum Tertampung"),
            P("Adakah keadaan yang menurut Bapak/Ibu ikut menentukan prioritas, tetapi belum "
              "tercantum pada keempat kriteria di atas? Mohon dituliskan."),
            Table(
                header=["Keadaan yang belum tertampung", "Seberapa sering ditemui"],
                baris=[
                    [TULIS_PANJANG, ""],
                    [TULIS_PANJANG, ""],
                ],
                lebar=[68, 32],
                kolom1_tebal=False,
            ),

            H1(8, "Pengesahan"),
            P("Isian pada lembar ini akan dipakai sebagai dasar penetapan bobot kriteria pada sistem, "
              "dan dilampirkan pada laporan penelitian sebagai keterangan asal-usul angka tersebut. "
              "Tidak ada penilaian atas kinerja siapa pun yang dilakukan melalui lembar ini."),
            Table(
                header=["Pengisi", "Peneliti"],
                baris=[
                    ["Nama terang:\n\n\nTanda tangan:\n\n",
                     "Nama: Muhammad Gilang\n\n\nTanda tangan:\n\n"],
                ],
                lebar=[50, 50],
                kolom1_tebal=False,
            ),
        ],
    )


def main() -> None:
    folder = Path(__file__).parent
    berkas = [
        ("materi-pertemuan-kelurahan", dokumen_materi()),
        ("lampiran-permintaan-data-anonim", dokumen_lampiran()),
        ("lembar-pembobotan-kriteria", dokumen_pembobotan()),
    ]
    for nama, dok in berkas:
        md, pdf = tulis_dua_format(dok, folder / nama)
        print(f"{nama}:")
        print(f"  Markdown : {md}")
        print(f"  PDF      : {pdf}")


if __name__ == "__main__":
    main()
