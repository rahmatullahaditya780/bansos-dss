"""Generator dokumen: "Rubrik Pelabelan Urgensi Teks Naratif" (OI-11).

Menghasilkan `rubrik-pelabelan-urgensi.md` + `.pdf` dari satu sumber konten.

Jalankan:
    .venv/Scripts/python.exe progres/fase-1-data-pelabelan/generate_rubrik_urgensi.py
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from doc_render import (  # noqa: E402
    Bullets, Dokumen, H1, H2, Note, Numbered, P, Table, hari_ini, tulis_dua_format,
)

VERSI_RUBRIK = "v1.1 (draf)"

# ---------------------------------------------------------------------------
# 2 — Aturan dasar
# ---------------------------------------------------------------------------
ATURAN_DASAR = [
    ["R1", "Labeli **hanya dari isi teks**. Jangan membuka data pendapatan, DTKS, atau berkas lain "
           "milik keluarga tersebut.",
     "Model nantinya juga hanya membaca teks. Bila pelabel menilai dari informasi yang tidak ada di "
     "teks, model diminta menebak sesuatu yang tidak dapat ia lihat."],
    ["R2", "**Urgensi bukan kelayakan.** Urgensi = seberapa mendesak kondisi ini bila dibiarkan "
           "beberapa minggu ke depan.",
     "Miskin tetapi stabil adalah urusan Tier 2 yang membaca data ekonomi. Bila urgensi dipakai "
     "untuk menilai kemiskinan, dua bagian sistem menilai hal yang sama dan yang lain kosong."],
    ["R3", "Nilai **kondisi yang sedang berlangsung**, bukan yang sudah lewat atau sudah teratasi.",
     "\"Pernah sakit, sekarang sudah kerja lagi\" bukan kondisi mendesak hari ini."],
    ["R4", "Baca kalimat **utuh**. Perhatikan kata ingkar: tidak, bukan, belum, tanpa.",
     "\"Tidak ada yang sakit kronis\" memuat kata 'sakit kronis' tetapi maknanya justru sebaliknya."],
    ["R5", "**Jangan menyimpulkan yang tidak tertulis.** Bila dampaknya tidak disebutkan, jangan "
           "diandaikan.",
     "Ini penyebab ketidaksepakatan terbesar antar-pelabel. Dua orang menebak ke arah berbeda dari "
     "teks yang sama."],
    ["R6", "Abaikan nama, jenis kelamin, dan alamat.",
     "Bila label ikut dipengaruhi hal ini, prasangka tersebut ikut dipelajari model."],
    ["R7", "Satu teks satu label. Bila ada beberapa kondisi sekaligus, ikuti **yang paling mendesak**.",
     "Sistem juga mengambil nilai tertinggi ketika satu pengajuan punya beberapa narasi."],
]

# ---------------------------------------------------------------------------
# 3 — Indikator TINGGI
# ---------------------------------------------------------------------------
INDIKATOR = [
    ["A. Kesehatan berat atau menahun",
     "Sakit kronis/menahun yang membuat tidak bisa bekerja; perawatan rutin yang membebani "
     "(cuci darah, kemoterapi, obat harian); sakit berat tanpa jaminan kesehatan; menunggu operasi."],
    ["B. Kehilangan pencari nafkah",
     "Pencari nafkah utama meninggal, hilang, atau meninggalkan keluarga; orang tua tunggal yang "
     "belum punya penghasilan pengganti."],
    ["C. Tempat tinggal tidak layak atau berbahaya",
     "Rumah rusak/nyaris roboh; bocor parah sampai menggenang; menumpang karena tidak punya tempat "
     "tinggal; tanpa air bersih atau tanpa jamban."],
    ["D. Pangan dan gizi",
     "Gizi buruk atau stunting pada balita; makan kurang dari dua kali sehari; ibu hamil atau "
     "menyusui kekurangan asupan; bayi tidak tercukupi kebutuhan makannya."],
    ["E. Pendidikan anak terancam berhenti",
     "Anak sudah berhenti atau terancam berhenti sekolah **karena biaya**; anak bekerja demi biaya "
     "sekolah saudaranya; tunggakan sekolah yang membuat anak tidak masuk."],
    ["F. Disabilitas dan lansia tanpa pendamping",
     "Penyandang disabilitas yang menghambat mencari nafkah; lansia yang tidak dapat mengurus diri "
     "sendiri dan tidak ada yang merawat; anak berkebutuhan khusus yang terapinya tidak terjangkau."],
    ["G. Pendapatan hilang atau tidak mencukupi kebutuhan pokok",
     "Baru kehilangan pekerjaan dan belum ada pengganti; terlilit hutang rentenir; menunggak "
     "kebutuhan pokok (pangan, listrik, air, sewa) sampai berdampak; menggantungkan hidup pada "
     "pemberian orang lain."],
    ["H. Bencana atau musibah",
     "Rumah terdampak banjir, kebakaran, longsor, angin kencang; kehilangan harta benda utama; "
     "kehilangan alat kerja (perahu, gerobak, mesin jahit)."],
]

# ---------------------------------------------------------------------------
# 5 — Kasus batas
# ---------------------------------------------------------------------------
KASUS_BATAS = [
    ["Sakit disebutkan, dampaknya tidak", "RENDAH",
     "R5 — jangan mengarang dampak. \"Bapak penderita diabetes\" saja: RENDAH."],
    ["Sakit disebutkan beserta dampaknya", "TINGGI",
     "Indikator A. \"...diabetes, kakinya diamputasi, tidak bisa melaut lagi\": TINGGI."],
    ["Sakit ringan atau sudah sembuh", "RENDAH", "R3 — bukan kondisi yang sedang berlangsung."],
    ["Rumah bocor ringan / sudah ditambal", "RENDAH", "R3 — sudah teratasi."],
    ["Rumah bocor parah, air menggenang di dalam", "TINGGI", "Indikator C — mengancam kelayakan huni."],
    ["Menganggur, tetapi anggota lain berpenghasilan tetap", "RENDAH",
     "Kebutuhan pokok masih tertutup; tidak ada kondisi mendesak."],
    ["Menganggur dan tidak ada sumber pendapatan lain", "TINGGI", "Indikator G."],
    ["Lansia, tetapi sehat dan mandiri", "RENDAH", "Indikator F menuntut ketidakmampuan mengurus diri."],
    ["Lansia tinggal sendiri dan tidak mampu mengurus diri", "TINGGI", "Indikator F."],
    ["Punya hutang, angsuran lancar", "RENDAH", "Hutang biasa bukan kondisi mendesak."],
    ["Terlilit hutang rentenir untuk makan sehari-hari", "TINGGI", "Indikator G."],
    ["Anak berhenti sekolah bukan karena biaya", "RENDAH",
     "Indikator E khusus untuk hambatan biaya, bukan keputusan lain."],
    ["Anak bekerja agar saudaranya tetap bersekolah", "TINGGI", "Indikator E."],
    ["Ibu hamil, kontrol rutin, tidak ada keluhan", "RENDAH", "Tidak ada indikator berlangsung."],
    ["Ibu hamil tanpa biaya persalinan atau kurang gizi", "TINGGI", "Indikator D."],
    ["Kondisi buruk disebut, tetapi ditulis sudah dibantu/teratasi", "RENDAH", "R3."],
    ["Kata mendesak muncul dalam kalimat ingkar", "RENDAH", "R4 — baca kalimat utuh."],
    ["Teks sangat pendek tetapi jelas (\"rumah ambruk kena angin\")", "TINGGI",
     "Panjang teks tidak menentukan; isinya yang menentukan."],
    ["Teks administratif, tidak menggambarkan kondisi", "TIDAK DAPAT DINILAI",
     "Contoh: \"berkas menyusul\", \"sudah disurvei\", tanda hubung."],
    # --- amandemen v1.1 ---
    ["Sebutan penyakit/status saja, tanpa keterangan fungsi", "RENDAH",
     "v1.1 — diagnosis bukan keterbatasan. \"Bapak penderita diabetes\": RENDAH."],
    ["Keterbatasan digambarkan lewat kegiatan sehari-hari", "TINGGI",
     "v1.1 — dipapah, disuapi, diantar makan tetangga: keterbatasan fungsi nyata meski kata "
     "\"disabilitas\" tidak muncul."],
    ["Menunggak kebutuhan pokok dan masih berlangsung", "TINGGI",
     "Indikator G. Perhatikan: \"sudah tiga bulan menunggak\" berarti berlanjut, bukan selesai."],
]

# ---------------------------------------------------------------------------
# 6 — Contoh terkalibrasi
# ---------------------------------------------------------------------------
CONTOH = [
    ["1", "Bapak sudah dua tahun cuci darah seminggu dua kali. Ibu berhenti berjualan karena harus "
          "mengantar tiap kali.", "TINGGI", "A — perawatan rutin sekaligus hilangnya penghasilan ibu."],
    ["2", "Sejak suami wafat bulan Maret, ibu menanggung tiga anak sendirian dan belum ada penghasilan "
          "tetap.", "TINGGI", "B — pencari nafkah hilang, belum ada pengganti."],
    ["3", "Bagian belakang rumah ambruk waktu hujan besar minggu lalu, sekarang semua tidur di ruang "
          "depan.", "TINGGI", "C — tempat tinggal rusak dan sedang berlangsung."],
    ["4", "Anak bungsu umur dua tahun berat badannya tidak naik-naik, dari posyandu disarankan "
          "dirujuk.", "TINGGI", "D — indikasi gizi buruk pada balita."],
    ["5", "Kata ibunya, dua anaknya sudah tidak masuk sekolah sejak awal semester karena belum bayar.",
     "TINGGI", "E — anak berhenti sekolah karena biaya."],
    ["6", "Nenek tinggal sendiri, jalan pakai tongkat, tetangga yang bantu masak.", "TINGGI",
     "F — lansia tidak mampu mengurus diri, tanpa pendamping keluarga."],
    ["7", "Bapak diberhentikan dari pabrik bulan lalu, sekarang serabutan tidak tentu.", "TINGGI",
     "G — kehilangan pekerjaan, belum ada pengganti tetap."],
    ["8", "Rumah kena banjir bulan Januari, kasur dan lemari rusak semua, sampai sekarang belum "
          "diganti.", "TINGGI", "H — dampak musibah masih berlangsung."],
    ["9", "Kalau tidak ada kiriman dari anaknya di Makassar, mereka tidak masak hari itu.", "TINGGI",
     "D/G — kebutuhan pangan tidak terpenuhi, meski tanpa kata mencolok."],
    ["10", "Sudah tiga bulan menunggak listrik, sekarang menyambung dari rumah tetangga.", "TINGGI",
     "G — kebutuhan pokok tidak tertutup."],
    ["11", "Anak sulung berhenti kuliah lalu ikut melaut supaya adiknya bisa tetap sekolah.", "TINGGI",
     "E — pendidikan dikorbankan karena biaya."],
    ["12", "Kepala keluarga penderita diabetes, kakinya sudah diamputasi dan tidak bisa melaut lagi.",
     "TINGGI", "A — penyakit beserta dampaknya tertulis jelas."],
    ["13", "Kepala keluarga penderita diabetes.", "RENDAH",
     "R5 — dampaknya tidak disebutkan; jangan diandaikan. Bandingkan dengan contoh 12."],
    ["14", "Tidak ada anggota keluarga yang sakit menahun ataupun cacat.", "RENDAH",
     "R4 — memuat kata mendesak dalam kalimat ingkar."],
    ["15", "Atap dapur sempat bocor tahun lalu, sudah ditambal sendiri.", "RENDAH", "R3 — sudah teratasi."],
    ["16", "Bapak pernah sakit tipes awal tahun, sekarang sudah kerja lagi seperti biasa.", "RENDAH",
     "R3 — kondisi lampau."],
    ["17", "Penghasilan pas-pasan, tapi masih cukup untuk makan dan biaya sekolah anak.", "RENDAH",
     "R2 — ekonomi lemah namun stabil; kelayakannya dinilai Tier 2, bukan di sini."],
    ["18", "Ibu sedang hamil anak kedua, kontrol rutin di puskesmas, tidak ada keluhan.", "RENDAH",
     "Tidak ada indikator yang sedang berlangsung."],
    ["19", "Orang tua sudah sepuh tapi masih sehat, tiap pagi masih ke kebun.", "RENDAH",
     "F tidak terpenuhi — masih mandiri."],
    ["20", "Bapak sempat menganggur dua bulan, sekarang sudah masuk kerja di bengkel.", "RENDAH",
     "R3 — sudah teratasi."],
    ["21", "Anaknya berhenti sekolah karena tidak mau lagi, orang tuanya sudah berkali-kali membujuk.",
     "RENDAH", "E tidak terpenuhi — bukan karena biaya."],
    ["22", "Utang di koperasi masih ada, angsurannya lancar tiap bulan.", "RENDAH",
     "Hutang biasa, tidak ada jerat rentenir."],
    ["23", "Rumah semi permanen, lantai sudah disemen, air dari sumur bor.", "RENDAH",
     "Sederhana tetapi layak huni."],
    ["24", "Keluarga ini rajin ikut kegiatan RT dan gotong royong.", "RENDAH",
     "Tidak menggambarkan kondisi mendesak apa pun."],
    ["25", "Pengajuan susulan, berkas menyusul.", "TIDAK DAPAT DINILAI",
     "Teks administratif — keluarkan dari dataset, jangan dipaksa jadi RENDAH."],
]

# ---------------------------------------------------------------------------
# 7 — Kappa
# ---------------------------------------------------------------------------
KAPPA = [
    ["< 0,00", "Tidak ada kesepakatan", "Definisi bermasalah — susun ulang bersama pembimbing."],
    ["0,00 - 0,20", "Sangat lemah", "Hentikan pelabelan; tinjau ulang rubrik menyeluruh."],
    ["0,21 - 0,40", "Lemah", "Hentikan; perjelas definisi TINGGI dan kasus batas."],
    ["0,41 - 0,60", "Sedang", "Belum cukup. Revisi rubrik, ulangi pilot dengan 50 teks baru."],
    ["0,61 - 0,80", "Kuat", "**Boleh lanjut** ke pelabelan penuh."],
    ["0,81 - 1,00", "Sangat kuat", "Boleh lanjut."],
]

LEMBAR_KERJA = [
    ["id_teks", "Kode unik teks (bukan NIK/nama)"],
    ["teks_anonim", "Isi narasi yang sudah dianonimkan"],
    ["label_A", "Label pelabel A: tinggi / rendah / tidak_dapat_dinilai"],
    ["label_B", "Label pelabel B (diisi tanpa melihat kolom label_A)"],
    ["label_final", "Hasil setelah diskusi/adjudikasi — kolom inilah yang dipakai melatih model"],
    ["catatan", "Alasan singkat bila sempat berbeda, atau kasus batas yang dipakai"],
    ["versi_rubrik", "Versi rubrik yang berlaku saat pelabelan baris ini"],
    ["tanggal", "Tanggal pelabelan"],
]

AMANDEMEN = [
    ["v1.0", "6 Agustus 2026",
     "Draf awal: 7 aturan dasar, 8 indikator, 19 kasus batas, 25 contoh terkalibrasi.",
     "Menyelesaikan OI-11 sebelum pelabelan dimulai."],
    ["v1.1", "7 Agustus 2026",
     "Ditambahkan asas \"keterbatasan fungsi, bukan sebutan\" pada Bagian 3, tiga kasus batas baru, "
     "dan penegasan bahwa penanda waktu tidak menentukan label.",
     "Uji silang contoh terkalibrasi terhadap model memperlihatkan batas antara contoh 6 "
     "(keterbatasan tersirat, TINGGI) dan contoh 13 (sebutan diagnosis, RENDAH) belum tertulis "
     "tegas, padahal keduanya bertetangga dekat."],
]


def bangun_dokumen() -> Dokumen:
    return Dokumen(
        judul="Rubrik Pelabelan Urgensi Teks Naratif",
        subjudul="DSS Bansos - Kelurahan Bontoramba",
        kicker="Panduan kerja untuk pelabel - resolusi OI-11",
        meta=[
            ("Versi rubrik", VERSI_RUBRIK),
            ("Tanggal", hari_ini()),
            ("Peneliti", "Muhammad Gilang"),
            ("Pelabel", "2 orang (peneliti + rekan), bekerja independen"),
            ("Dasar", "TRD Bab 6.2 & 7.1; OI-02, OI-08, OI-10, OI-11; risiko R-01 & R-02"),
        ],
        intro=(
            "Dokumen ini adalah panduan kerja untuk memberi label pada teks naratif kondisi keluarga. "
            "Label yang dihasilkan dipakai melatih model Tier 1 sistem DSS Bansos. Bacalah seluruh "
            "dokumen sekali sebelum mulai, lalu gunakan Bagian 5 dan 6 sebagai rujukan cepat saat "
            "bekerja. Anda tidak perlu tahu cara kerja model untuk mengerjakan tugas ini - yang "
            "dibutuhkan hanyalah membaca teks dan menerapkan aturan di bawah secara konsisten."
        ),
        blok=[
            # 1
            H1(1, "Apa yang Anda Kerjakan"),
            P("Anda akan membaca teks pendek berisi catatan petugas tentang kondisi sebuah keluarga, "
              "lalu memilih satu dari tiga pilihan: **TINGGI**, **RENDAH**, atau **TIDAK DAPAT DINILAI**."),
            P("Pertanyaan yang Anda jawab hanya satu:"),
            P("\"Berdasarkan teks ini saja, apakah keluarga tersebut sedang berada dalam kondisi yang "
              "mendesak - yaitu kondisi yang akan memburuk atau membahayakan bila dibiarkan beberapa "
              "minggu ke depan?\"", tebal=True),
            P("Jika ya, pilih TINGGI. Jika tidak, pilih RENDAH. Jika teksnya tidak menggambarkan "
              "kondisi keluarga sama sekali, pilih TIDAK DAPAT DINILAI."),
            Note(
                "TIDAK DAPAT DINILAI bukan kelas ketiga bagi model - baris itu akan dikeluarkan dari "
                "dataset. Gunakan pilihan ini hanya untuk teks kosong, teks administratif, atau teks "
                "yang tidak berisi keterangan kondisi. Jangan memakainya sekadar karena Anda ragu; "
                "untuk keraguan, gunakan Bagian 5.",
                judul="Kapan memakai TIDAK DAPAT DINILAI",
            ),
            H2("Mengapa label ini penting"),
            P("Sistem DSS bekerja dalam tiga tingkat. Tingkat pertama membaca teks dan menilai "
              "urgensi, tingkat kedua menilai kelayakan dari data ekonomi, tingkat ketiga menyusun "
              "peringkat prioritas. Label Anda melatih tingkat pertama. Bila dua pelabel memakai "
              "definisi berbeda, model mempelajari definisi yang saling bertentangan, dan hasilnya "
              "tidak dapat dipertanggungjawabkan di sidang."),

            # 2
            H1(2, "Tujuh Aturan Dasar"),
            P("Aturan berikut berlaku untuk setiap teks, tanpa kecuali. Sebagian besar perbedaan "
              "penilaian antara dua pelabel berasal dari salah satu aturan ini dilanggar."),
            Table(["#", "Aturan", "Mengapa"], ATURAN_DASAR, lebar=[4, 46, 50]),
            Note(
                "R5 adalah aturan yang paling sering dilupakan. Bila teks hanya menyebut sebuah "
                "kondisi tanpa menyebut akibatnya, jangan menambahkan akibat dari kepala Anda sendiri. "
                "Bandingkan contoh 12 dan 13 di Bagian 6 - kalimatnya mirip, labelnya berbeda, dan "
                "seluruh perbedaannya terletak pada apa yang benar-benar tertulis.",
                judul="Aturan emas",
            ),

            # 3
            H1(3, "Kapan Sebuah Teks Diberi Label TINGGI"),
            P("Beri label **TINGGI** bila teks menyebutkan **sekurang-kurangnya satu** indikator di "
              "bawah ini, dan kondisi itu **sedang berlangsung**. Satu indikator sudah cukup; tidak "
              "perlu menunggu beberapa indikator terpenuhi."),
            Table(["Indikator", "Bentuk yang termasuk"], INDIKATOR, lebar=[30, 70]),
            H2("Asas: keterbatasan fungsi, bukan sebutan  (amandemen v1.1)"),
            P("Yang membuat sebuah kondisi masuk indikator di atas adalah **keterbatasan fungsi atau "
              "kebutuhan yang tidak terpenuhi** - bukan sebutan penyakit, status, atau istilah "
              "tertentu. Dua sisi asas ini sama pentingnya:"),
            Bullets([
                "**Sebutan saja belum cukup.** \"Kepala keluarga penderita diabetes\" hanya menyebut "
                "diagnosis; tidak ada keterangan apa yang tidak lagi bisa dilakukan atau kebutuhan "
                "apa yang tidak tertutup. Labelnya RENDAH (lihat juga R5).",
                "**Sebutan tidak wajib ada.** \"Ibu tidak dapat bangun dari tempat tidur tanpa "
                "dipapah\" tidak memuat kata disabilitas maupun lansia, tetapi keterbatasan "
                "fungsinya jelas tergambar. Labelnya TINGGI.",
                "**Penanda waktu tidak menentukan label.** Kata \"sudah\" dan \"sekarang\" bisa "
                "berarti selesai (\"sudah bocor, sekarang sudah ditambal\" - RENDAH) maupun "
                "berlanjut (\"sudah tiga bulan menunggak, sekarang menyambung dari tetangga\" - "
                "TINGGI). Yang dibaca maknanya, bukan kata penandanya.",
            ]),
            Note(
                "Bandingkan contoh 6, 12, dan 13 di Bagian 6 secara berurutan. Ketiganya berdekatan "
                "dan hanya asas inilah yang memisahkannya. Bila dua pelabel sering berbeda, "
                "kemungkinan besar sumbernya di sini - bukan pada indikator A sampai H.",
                judul="Tiga contoh yang harus dibaca berdampingan",
            ),

            # 4
            H1(4, "Kapan Sebuah Teks Diberi Label RENDAH"),
            P("Beri label **RENDAH** bila tidak ada satu pun indikator A-H yang sedang berlangsung. "
              "Termasuk di dalamnya: kondisi ekonomi sederhana namun stabil, kesulitan yang sudah "
              "teratasi, keluhan yang tidak berdampak pada kebutuhan dasar, serta teks yang hanya "
              "berisi keterangan netral."),
            Note(
                "RENDAH tidak berarti keluarga itu mampu, dan tidak berarti pengajuannya ditolak. "
                "Banyak keluarga miskin akan mendapat label urgensi RENDAH - dan itu benar. "
                "Kemiskinan mereka dinilai di tingkat kedua sistem yang membaca data pendapatan, "
                "tanggungan, dan kondisi rumah. Tugas label ini hanya memisahkan mana yang sedang "
                "dalam keadaan mendesak. Salah paham pada titik ini adalah kesalahan pelabelan yang "
                "paling merusak.",
                judul="Jangan tertukar: RENDAH bukan berarti tidak layak dibantu",
            ),

            # 5
            H1(5, "Kasus Batas - Rujukan Cepat"),
            P("Bila ragu, cari situasi Anda pada tabel berikut. Bila tetap tidak ketemu, catat teks "
              "tersebut dan lanjutkan; bahas belakangan bersama pelabel lain, lalu tambahkan "
              "putusannya sebagai amandemen di Bagian 10."),
            Table(["Situasi dalam teks", "Putusan", "Dasar"], KASUS_BATAS, lebar=[38, 16, 46]),

            # 6
            H1(6, "Contoh Terkalibrasi"),
            P("Kerjakan 25 contoh ini **bersama-sama** sebelum pelabelan sesungguhnya dimulai, lalu "
              "cocokkan dengan kunci di kolom kanan. Contoh-contoh ini bukan bagian dari dataset."),
            Table(["#", "Teks", "Label", "Alasan"], CONTOH, lebar=[4, 48, 13, 35], kolom1_tebal=False),

            # 7
            H1(7, "Prosedur Pelabelan"),
            Numbered([
                "**Tahap 0 - Kalibrasi.** Kedua pelabel membaca rubrik ini, lalu mengerjakan 25 contoh "
                "Bagian 6 bersama-sama sambil mendiskusikan perbedaan tafsir. Belum ada data yang "
                "dilabeli pada tahap ini.",
                "**Tahap 1 - Pilot 50 teks.** Kedua pelabel melabeli 50 teks yang sama, secara "
                "independen, tanpa berdiskusi dan tanpa melihat pekerjaan satu sama lain.",
                "**Tahap 2 - Ukur kesepakatan.** Hitung Cohen's kappa dari 50 teks tersebut, lalu "
                "bandingkan dengan tabel di bawah. Jangan lanjut sebelum kappa mencapai 0,61.",
                "**Tahap 3 - Pelabelan penuh.** Bila ambang tercapai, labeli sisa teks secara "
                "independen dengan rubrik yang sama.",
                "**Tahap 4 - Penyelesaian selisih.** Teks yang labelnya berbeda didiskusikan berdua. "
                "Bila tetap tidak sepakat, putusan diserahkan kepada pihak ketiga (dosen pembimbing "
                "atau petugas kelurahan). Karena pelabel hanya dua orang, tidak ada suara mayoritas.",
                "**Tahap 5 - Amandemen.** Setiap putusan baru atas kasus yang belum tercakup dicatat "
                "di Bagian 10 dengan nomor versi dan tanggal.",
            ]),
            H2("Ambang kesepakatan (Cohen's kappa, tafsir Landis & Koch)"),
            Table(["Nilai kappa", "Tafsir", "Tindakan"], KAPPA, lebar=[18, 22, 60]),
            Note(
                "Kappa yang rendah adalah masalah rubrik, bukan masalah pelabel. Yang direvisi adalah "
                "dokumen ini - biasanya definisi indikator atau tabel kasus batas - lalu pilot diulang "
                "dengan 50 teks yang belum pernah dilihat. Jangan mengulang pilot dengan teks yang "
                "sama: keduanya sudah mengingat jawabannya, dan kappa akan tinggi secara semu.",
                judul="Bila kappa belum mencapai ambang",
            ),

            # 8
            H1(8, "Anonimisasi Wajib"),
            P("Teks yang diberikan kepada pelabel **harus** sudah dianonimkan lebih dulu oleh peneliti:"),
            Bullets([
                "Nama orang diganti menjadi [NAMA]; nama tempat/dusun yang menunjuk keluarga tertentu "
                "menjadi [ALAMAT].",
                "NIK, nomor KK, dan nomor telepon dihapus seluruhnya.",
                "Hubungan keluarga tetap dipertahankan (bapak, ibu, anak, nenek) - informasi ini "
                "diperlukan untuk menilai urgensi.",
            ]),
            Note(
                "Pelabel dari luar kelurahan bukan pihak berwenang atas data warga. Anonimisasi adalah "
                "syarat, bukan anjuran, dan sejalan dengan komitmen penanganan data pada dokumen "
                "Ketentuan Data DTKS. Pembersihan otomatis di sistem hanya membuang angka panjang - "
                "nama dan alamat tetap harus disamarkan secara manual sebelum berkas dibagikan.",
                judul="Batas kewenangan dan privasi",
            ),

            # 9
            H1(9, "Pencatatan dan Target Data"),
            P("Setiap baris pelabelan dicatat dengan kolom berikut. Lembar kerja siap-isi akan "
              "disediakan terpisah."),
            Table(["Kolom", "Isi"], LEMBAR_KERJA, lebar=[24, 76]),
            Bullets([
                "**Target jumlah data:** sekurang-kurangnya 100 kepala keluarga, dan sebanyak mungkin "
                "teks naratif dari keluarga tersebut.",
                "**Kolom label_B diisi tanpa melihat label_A.** Cara termudah: masing-masing pelabel "
                "memakai salinan berkasnya sendiri, digabungkan hanya setelah keduanya selesai.",
                "**Bila proporsi kelas timpang** (misalnya TINGGI kurang dari 30 persen), itu wajar "
                "dan tidak perlu dipaksa seimbang. Konsekuensinya, kinerja model dilaporkan memakai "
                "F1, bukan akurasi.",
                "Label final disimpan pada kolom `label_urgensi_manual` di basis data sistem.",
            ]),

            # 10
            H1(10, "Riwayat Amandemen Rubrik"),
            P("Setiap perubahan tafsir dicatat di sini. Label yang sudah terlanjur dibuat tidak diubah "
              "diam-diam: bila sebuah amandemen mengubah tafsir kasus yang sudah pernah dilabeli, "
              "batch yang terdampak dilabeli ulang dan hal itu dicatat pada kolom keterangan."),
            Table(["Versi", "Tanggal", "Perubahan", "Alasan"], AMANDEMEN, lebar=[10, 18, 42, 30]),
            P("Riwayat ini dilampirkan di skripsi sebagai bukti prosedur pelabelan terkendali "
              "(mitigasi risiko R-02: kualitas pelabelan manual tidak konsisten)."),
        ],
    )


def main() -> None:
    dasar = Path(__file__).parent / "rubrik-pelabelan-urgensi"
    md, pdf = tulis_dua_format(bangun_dokumen(), dasar)
    print(f"Markdown : {md}")
    print(f"PDF      : {pdf}")


if __name__ == "__main__":
    main()
