"""Pembangkit korpus naratif berlabel urgensi (augmentasi) — data latih SEMENTARA Fase 2.

Peran: memvalidasi pipeline fine-tuning end-to-end (preprocess → latih → evaluasi → inference)
**sebelum** teks lokal Bontoramba berlabel tersedia (Fase 1 masih berjalan). Pada Fase 6 korpus ini
digantikan/ditambah teks lokal berlabel; kolom `asal_data` menandai asal tiap baris agar metrik
dapat dilaporkan per sumber (rencana Fase 2, poin evaluasi).

Desain agar model tidak sekadar menghafal kata kunci:
- **hard negative** — klausa non-urgen yang MEMUAT kata urgen dalam konteks negasi/teratasi
  ("tidak ada anggota keluarga yang sakit kronis", "atap pernah bocor namun sudah diperbaiki");
- **hard positive** — klausa urgen TANPA kata kunci mencolok
  ("penghasilan harian tidak cukup untuk makan tiga kali sehari");
- **variasi gaya** — formal petugas, semi-formal, dan informal bersingkatan/typo, karena isian
  lapangan tidak selalu rapi.

Pemakaian:
    python -m ml.tier1.corpus --n 2400 --out data/corpus/tier1_urgensi.csv
"""
from __future__ import annotations

import argparse
import csv
import random
from dataclasses import dataclass
from pathlib import Path

ASAL_DATA = "augmentasi"

# ---------------------------------------------------------------------------
# Bank klausa
# ---------------------------------------------------------------------------

# Klausa urgen dengan penanda leksikal jelas, dikelompokkan per kategori kondisi.
URGEN: dict[str, list[str]] = {
    "kesehatan": [
        "kepala keluarga menderita sakit kronis menahun dan tidak mampu lagi bekerja",
        "istri menjalani cuci darah rutin dua kali seminggu tanpa jaminan kesehatan",
        "anggota keluarga mengidap tuberkulosis dan biaya berobat ditanggung sendiri",
        "kepala keluarga terkena stroke sehingga lumpuh sebagian sejak tahun lalu",
        "anak menderita penyakit jantung bawaan dan menunggu operasi",
        "ibu rumah tangga sakit-sakitan sehingga tidak dapat berjualan lagi",
    ],
    "kehilangan_pencari_nafkah": [
        "tulang punggung keluarga baru saja meninggal dunia dan belum ada pengganti",
        "suami meninggal enam bulan lalu meninggalkan tiga anak yang masih kecil",
        "ayah dari keluarga ini wafat sehingga ibu menjadi orang tua tunggal",
        "kepala keluarga hilang kontak sejak merantau dan keluarga tanpa penghasilan",
    ],
    "rumah": [
        "rumah berupa gubuk berdinding bambu yang nyaris roboh saat angin kencang",
        "atap rumah bocor parah sehingga lantai tergenang setiap kali hujan",
        "keluarga masih menumpang di rumah kerabat karena tidak memiliki tempat tinggal",
        "rumah tidak memiliki sanitasi maupun sumber air bersih yang layak",
        "dinding rumah lapuk dan lantai masih berupa tanah",
    ],
    "pangan_gizi": [
        "anak balita mengalami gizi buruk dan terindikasi stunting",
        "keluarga hanya mampu makan satu kali sehari dalam sebulan terakhir",
        "bayi berusia delapan bulan kekurangan asupan susu dan makanan pendamping",
        "ibu hamil kekurangan gizi dan belum pernah memeriksakan kandungan",
    ],
    "pendidikan": [
        "dua anak terancam putus sekolah karena tunggakan biaya",
        "anak sulung berhenti sekolah dan ikut bekerja membantu orang tua",
        "anak tidak dapat melanjutkan ke jenjang berikutnya karena ketiadaan biaya",
    ],
    "disabilitas_lansia": [
        "kepala keluarga menyandang disabilitas fisik sehingga sulit mencari kerja",
        "keluarga merawat lansia jompo yang tidak dapat beraktivitas sendiri",
        "anak berkebutuhan khusus memerlukan terapi rutin yang tidak terjangkau",
        "nenek berusia delapan puluh tahun tinggal seorang diri tanpa pendamping",
    ],
    "pekerjaan": [
        "kepala keluarga terkena pemutusan hubungan kerja dan belum mendapat pekerjaan baru",
        "penghasilan sebagai buruh harian tidak menentu dan sering tidak ada panggilan kerja",
        "keluarga terlilit hutang rentenir untuk menutup kebutuhan sehari-hari",
        "usaha kecil keluarga bangkrut sehingga tidak ada lagi sumber pendapatan",
    ],
    "bencana": [
        "rumah keluarga terdampak banjir dan seluruh perabot rusak",
        "kebakaran menghanguskan rumah beserta isinya bulan lalu",
        "tanah longsor merusak bagian belakang rumah dan belum diperbaiki",
    ],
}

# Ketidakberdayaan yang disampaikan TERSIRAT — lewat perilaku sehari-hari, bukan sebutan langsung
# seperti "jompo" atau "disabilitas". Ditambahkan setelah uji silang rubrik (2026-08-06) menunjukkan
# model gagal pada bentuk tersirat, karena korpus awal hanya memuat bentuk eksplisit.
URGEN_TERSIRAT = [
    "orang tua hanya bisa berbaring dan tetangga yang mengantarkan makanan tiap hari",
    "kakek berjalan dengan bantuan tongkat dan tidak ada yang menemani di rumah",
    "ibu tidak dapat bangun dari tempat tidur tanpa dipapah",
    "bapak sudah tidak sanggup mengangkat jaring sejak tangannya melemah",
    "keperluan mandi dan makan orang tua bergantung sepenuhnya pada bantuan orang lain",
    "sehari-hari hanya duduk di kursi dan tidak mampu berjalan sendiri",
    "tidak ada anggota keluarga yang sanggup mengurus kebutuhan harian orang tua",
    "nenek mengurus dua cucu seorang diri sementara kondisinya sendiri sudah renta",
]

# Klausa urgen TANPA kata kunci mencolok (hard positive).
URGEN_HALUS = [
    "penghasilan harian tidak cukup untuk makan tiga kali sehari",
    "keluarga menggantungkan hidup pada pemberian tetangga sejak beberapa bulan terakhir",
    "seluruh anggota keluarga tidur berdesakan dalam satu ruangan sempit",
    "biaya sekolah anak sudah tiga bulan menunggak dan belum terbayar",
    "tidak ada satu pun anggota keluarga usia produktif yang memiliki penghasilan tetap",
    "kebutuhan obat rutin sering tidak tertebus karena keterbatasan biaya",
    "keluarga terpaksa menjual perabot rumah untuk menutup kebutuhan pangan",
    "listrik rumah sempat diputus karena tunggakan yang belum terbayar",
]

# Klausa non-urgen biasa.
BIASA = [
    "kondisi ekonomi keluarga tergolong cukup dan stabil",
    "kepala keluarga bekerja tetap sebagai karyawan dengan penghasilan bulanan memadai",
    "keluarga memiliki usaha warung kecil yang berjalan lancar",
    "rumah dalam kondisi layak huni dengan dinding tembok dan lantai keramik",
    "seluruh anak bersekolah dengan biaya yang tercukupi",
    "keluarga telah memiliki jaminan kesehatan dan rutin memanfaatkannya",
    "penghasilan dari hasil panen mencukupi kebutuhan sehari-hari",
    "anggota keluarga dalam keadaan sehat dan beraktivitas normal",
    "keluarga memiliki kendaraan bermotor dan lahan garapan sendiri",
    "sumber air bersih tersedia dari sambungan pdam di rumah",
]

# Hard negative: memuat kosakata urgen, tetapi dinegasikan / sudah teratasi.
BIASA_SULIT = [
    "tidak ada anggota keluarga yang menderita sakit kronis maupun disabilitas",
    "atap rumah pernah bocor namun sudah diperbaiki secara swadaya",
    "kepala keluarga sempat sakit tahun lalu namun kini sudah sembuh dan kembali bekerja",
    "anak sempat terancam putus sekolah namun kini melanjutkan dengan beasiswa",
    "keluarga pernah menerima bantuan saat terdampak banjir dan kondisinya telah pulih",
    "orang tua sudah lansia namun masih sehat dan mampu mengurus diri sendiri",
    "kepala keluarga sempat menganggur namun sekarang telah memiliki pekerjaan tetap",
    "rumah bukan gubuk dan tidak dalam kondisi rusak",
    "tidak ditemukan anak balita dengan gizi buruk pada keluarga ini",
    "hutang usaha keluarga sudah lunas dan usaha kembali berjalan",
    "tidak ada anggota keluarga yang meninggal maupun sakit berat dalam setahun terakhir",
    "ibu sedang hamil dengan kondisi sehat dan biaya persalinan sudah disiapkan",
    # Putus sekolah dengan SEBAB SELAIN BIAYA — indikator pendidikan hanya berlaku bila
    # hambatannya biaya. Ditambahkan setelah uji silang rubrik (2026-08-06).
    "anak berhenti sekolah bukan karena biaya melainkan karena tidak berminat lagi",
    "anak memilih tidak melanjutkan sekolah meski biayanya masih tercukupi",
    "anak sempat bolos berhari-hari karena malas, orang tua sudah berkali-kali menasihati",
    "putus sekolah terjadi bukan karena tunggakan, pembayaran selama ini lancar",
    "anak pindah sekolah mengikuti kerabat, biaya pendidikan tetap tertanggung",
]

# Frame "sudah teratasi": mengubah klausa urgen menjadi hard negative. Dipakai sebagai
# TRANSFORMASI, bukan daftar tetap, agar model mempelajari POLA "dulu bermasalah, kini selesai"
# pada beragam kondisi — bukan menghafal beberapa kalimat. Ditambahkan setelah uji silang rubrik
# (2026-08-06): aturan R3 gagal begitu susunan kalimatnya di luar contoh yang pernah dilihat.
FRAME_TERATASI = [
    "{k}, namun kondisi itu sudah teratasi dan keluarga kembali seperti biasa",
    "{k}, tetapi sekarang keadaannya sudah pulih sepenuhnya",
    "beberapa waktu lalu {k}, sekarang hal itu sudah tidak terjadi lagi",
    "tahun lalu {k}, kini keadaannya sudah membaik",
    "{k}, hal tersebut sudah ditangani sendiri secara swadaya oleh keluarga",
    "sempat tercatat bahwa {k}, namun sudah selesai beberapa bulan lalu",
]

# Hanya kategori yang masuk akal untuk "pulih". Kematian pencari nafkah dan disabilitas permanen
# dikecualikan — frame teratasi akan menghasilkan kalimat yang tidak masuk akal.
KATEGORI_DAPAT_TERATASI = ["kesehatan", "rumah", "pangan_gizi", "pendidikan", "pekerjaan", "bencana"]

# Frame "masih berlanjut" — PENYEIMBANG frame teratasi, memakai penanda waktu yang sama
# ("sudah ...", "sekarang ...") tetapi bermakna sebaliknya. Tanpa ini model memakai jalan pintas
# dangkal: menganggap susunan "sudah X, sekarang Y" selalu berarti masalah sudah selesai.
# Ditambahkan setelah v2 justru salah pada "sudah tiga bulan menunggak listrik, sekarang
# menyambung dari rumah tetangga" — kalimat yang v1 sudah benar.
FRAME_BERLANJUT = [
    "sudah beberapa bulan {k}, sekarang keadaannya semakin berat",
    "{k}, sampai sekarang belum ada perubahan sama sekali",
    "sudah lama {k}, sekarang justru bertambah parah",
    "sejak tahun lalu {k}, kini kondisinya makin sulit",
    "sudah berulang kali disampaikan bahwa {k}, sekarang masih terus berlangsung",
]

# Tunggakan kebutuhan pokok (indikator G rubrik) — bentuk paling sering muncul dengan penanda
# waktu "sudah ... bulan", sehingga penting hadir sebagai kelas TINGGI.
URGEN_TUNGGAKAN = [
    "tunggakan listrik sudah tiga bulan dan sambungan terancam diputus",
    "sewa rumah menunggak beberapa bulan dan pemilik sudah meminta keluarga pindah",
    "air bersih terpaksa dibeli dari tetangga karena sambungan sendiri telah diputus",
    "cicilan kebutuhan dapur di warung menumpuk dan sudah tidak diberi utang lagi",
    "biaya berobat rutin sudah dua bulan tidak tertebus",
]

PEMBUKA_FORMAL = [
    "berdasarkan hasil observasi petugas di lapangan",
    "menurut hasil kunjungan dan wawancara petugas kelurahan",
    "dari hasil survei rumah tangga yang dilakukan",
    "hasil verifikasi lapangan menunjukkan bahwa",
    "berdasarkan keterangan ketua rt setempat",
]
PEMBUKA_SEMI = [
    "petugas mencatat bahwa",
    "kondisi yang ditemukan di lapangan",
    "dari pengamatan langsung",
    "keterangan dari tetangga menyebutkan",
]
PENUTUP_URGEN = [
    "sehingga keluarga sangat membutuhkan bantuan segera",
    "kondisi ini dinilai mendesak untuk ditangani",
    "keluarga tidak memiliki sumber pendapatan lain untuk bertahan",
    "situasi ini berlangsung terus-menerus tanpa perbaikan",
]
PENUTUP_BIASA = [
    "sehingga kebutuhan dasar keluarga masih dapat terpenuhi",
    "kondisi keluarga dinilai masih dalam batas wajar",
    "tidak ditemukan kondisi mendesak pada keluarga ini",
    "keluarga menyatakan mampu memenuhi kebutuhan sendiri",
]
PENGHUBUNG = [" serta ", " dan ", ", selain itu ", ". selain itu, ", ", ditambah lagi "]

# Peta singkatan untuk gaya informal (kebalikan normalisasi di preprocessing).
_INFORMALKAN = {
    "tidak": ["tdk", "gak", "ga"], "dengan": ["dgn", "dg"], "yang": ["yg"],
    "sudah": ["sdh", "udah"], "belum": ["blm"], "karena": ["krn", "karna"],
    "untuk": ["utk"], "kepala keluarga": ["kk"], "orang tua": ["ortu"], "tahun": ["thn"],
    "bulan": ["bln"], "rumah": ["rmh"], "sakit-sakitan": ["sakit2an"], "tetapi": ["tp"],
}


@dataclass
class Sampel:
    teks: str
    label: str          # 'tinggi' | 'rendah'
    kategori: str
    gaya: str           # 'formal' | 'semi' | 'informal'
    asal_data: str = ASAL_DATA


def _informalkan(rng: random.Random, teks: str) -> str:
    """Terapkan singkatan & typo ringan agar model tahan terhadap isian lapangan yang tidak rapi."""
    for baku, varian in _INFORMALKAN.items():
        if baku in teks and rng.random() < 0.6:
            teks = teks.replace(baku, rng.choice(varian), 1)
    if rng.random() < 0.3:  # typo: huruf berulang
        kata = teks.split()
        i = rng.randrange(len(kata))
        if len(kata[i]) > 4:
            p = rng.randrange(1, len(kata[i]) - 1)
            kata[i] = kata[i][:p] + kata[i][p] * rng.randint(2, 3) + kata[i][p:]
        teks = " ".join(kata)
    if rng.random() < 0.4:  # hilangkan tanda baca akhir
        teks = teks.rstrip(".")
    return teks


def _rakit(rng: random.Random, klausa: list[str], urgen: bool, gaya: str) -> str:
    inti = klausa[0]
    for tambahan in klausa[1:]:
        inti += rng.choice(PENGHUBUNG) + tambahan

    bagian: list[str] = []
    if gaya == "formal":
        bagian.append(rng.choice(PEMBUKA_FORMAL))
    elif gaya == "semi" and rng.random() < 0.7:
        bagian.append(rng.choice(PEMBUKA_SEMI))
    bagian.append(inti)
    if rng.random() < (0.55 if urgen else 0.5):
        bagian.append(rng.choice(PENUTUP_URGEN if urgen else PENUTUP_BIASA))

    teks = ", ".join(bagian).replace(", .", ".") + "."
    if gaya == "informal":
        teks = _informalkan(rng, teks)
    return teks


def _pilih_gaya(rng: random.Random) -> str:
    return rng.choices(["formal", "semi", "informal"], weights=[0.45, 0.3, 0.25])[0]


def generate_corpus(n: int = 2400, seed: int = 42, rasio_tinggi: float = 0.5) -> list[Sampel]:
    """Bangkitkan `n` sampel berlabel, seimbang antar kelas dan deterministik terhadap `seed`.

    Sekitar 30% sampel tiap kelas berasal dari bank "sulit" (hard positive / hard negative).
    Duplikat teks persis dibuang, sehingga jumlah akhir bisa sedikit di bawah `n`.
    """
    rng = random.Random(seed)
    urgen_flat = [(kat, k) for kat, daftar in URGEN.items() for k in daftar]
    hasil: list[Sampel] = []
    terlihat: set[str] = set()

    n_tinggi = int(n * rasio_tinggi)
    rencana = [True] * n_tinggi + [False] * (n - n_tinggi)
    rng.shuffle(rencana)

    for urgen in rencana:
        gaya = _pilih_gaya(rng)
        sulit = rng.random() < 0.3

        if urgen:
            if sulit:
                undian = rng.random()
                if undian < 0.3:
                    klausa = rng.sample(URGEN_TERSIRAT, k=rng.choice([1, 1, 2]))
                    kategori = "urgen_tersirat"
                elif undian < 0.6:
                    # Penanda waktu yang sama dengan frame teratasi, maknanya berlawanan.
                    kat = rng.choice(KATEGORI_DAPAT_TERATASI)
                    inti = rng.choice(URGEN[kat] + URGEN_TUNGGAKAN)
                    klausa = [rng.choice(FRAME_BERLANJUT).format(k=inti)]
                    kategori = "urgen_berlanjut"
                else:
                    klausa = rng.sample(URGEN_HALUS + URGEN_TUNGGAKAN, k=rng.choice([1, 1, 2]))
                    kategori = "urgen_halus"
            else:
                dipilih = rng.sample(urgen_flat, k=rng.choice([1, 1, 2, 3]))
                klausa = [k for _, k in dipilih]
                kategori = dipilih[0][0]
                # Sebagian kasus urgen disandingkan dengan fakta netral (realistis, menambah noise).
                if rng.random() < 0.2:
                    klausa.append(rng.choice(BIASA))
        else:
            if sulit:
                if rng.random() < 0.4:
                    # Ambil klausa urgen yang masuk akal untuk pulih, lalu bingkai "sudah teratasi".
                    kat = rng.choice(KATEGORI_DAPAT_TERATASI)
                    inti = rng.choice(URGEN[kat])
                    klausa = [rng.choice(FRAME_TERATASI).format(k=inti)]
                    kategori = "biasa_teratasi"
                else:
                    klausa = rng.sample(BIASA_SULIT, k=rng.choice([1, 1, 2]))
                    kategori = "biasa_sulit"
            else:
                klausa = rng.sample(BIASA, k=rng.choice([1, 1, 2]))
                kategori = "biasa"

        teks = _rakit(rng, klausa, urgen, gaya)
        if teks in terlihat:
            continue
        terlihat.add(teks)
        hasil.append(
            Sampel(teks=teks, label="tinggi" if urgen else "rendah", kategori=kategori, gaya=gaya)
        )

    rng.shuffle(hasil)
    return hasil


def tulis_csv(sampel: list[Sampel], path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["teks", "label", "kategori", "gaya", "asal_data"])
        for s in sampel:
            w.writerow([s.teks, s.label, s.kategori, s.gaya, s.asal_data])
    return path


def main() -> None:
    ap = argparse.ArgumentParser(description="Bangkitkan korpus naratif berlabel urgensi.")
    ap.add_argument("--n", type=int, default=2400, help="jumlah sampel target")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="data/corpus/tier1_urgensi.csv")
    args = ap.parse_args()

    sampel = generate_corpus(n=args.n, seed=args.seed)
    path = tulis_csv(sampel, args.out)
    n_tinggi = sum(1 for s in sampel if s.label == "tinggi")
    print(f"{len(sampel)} sampel unik ditulis ke {path}")
    print(f"  tinggi={n_tinggi}  rendah={len(sampel) - n_tinggi}")
    sulit = {"urgen_halus", "urgen_tersirat", "urgen_berlanjut", "biasa_sulit", "biasa_teratasi"}
    n_sulit = sum(1 for s in sampel if s.kategori in sulit)
    print(f"  sulit (hard pos/neg)={n_sulit} ({n_sulit / len(sampel):.0%})")


if __name__ == "__main__":
    main()
