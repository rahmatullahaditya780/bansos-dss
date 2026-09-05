# Permintaan Data ke Kelurahan — Evaluasi Ulang

**Tanggal:** 5 September 2026 · **Pemicu:** surat permohonan (masuk 4 September 2026) ditolak
sebagian — pihak kelurahan **tidak bersedia memberikan data diri riwayat penerima bantuan** dengan
alasan data tersebut bersifat sensitif.

Dokumen ini menggantikan asumsi permintaan data di
[`ketentuan-data-dtks-kelurahan.pdf`](ketentuan-data-dtks-kelurahan.pdf) (6 Agustus 2026), yang
disusun sebelum penolakan ini terjadi.

---

## 1. Penolakannya benar secara hukum — jangan dibantah, ubah permintaannya

Menurut **UU No. 27 Tahun 2022 tentang Pelindungan Data Pribadi**, nama, NIK, dan alamat adalah data
pribadi. Ketika digabung dengan **status penerima bantuan sosial**, gabungan itu menjadi keterangan
tentang kondisi ekonomi seseorang yang dapat diidentifikasi. Kelurahan tidak punya dasar hukum
menyerahkannya kepada pihak ketiga tanpa persetujuan tiap orang yang datanya diserahkan.

Artinya penolakan itu **bukan hambatan birokratis yang bisa dilobi**, melainkan pelaksanaan aturan.
Surat susulan dengan isi sama dan nada lebih memohon akan ditolak lagi.

Yang mengubah keadaan hanya satu: **menghapus data pribadi dari permintaannya.**

## 2. Sistem ini tidak pernah membutuhkan identitas siapa pun

Ini bukan kompromi, melainkan fakta teknis yang dapat diperiksa di kode:

| Yang dikonsumsi model | Kolom | Data pribadi? |
|---|---|---|
| Tier 2 (kelayakan) | `pendapatan`, `jumlah_tanggungan`, `usia`, `aset_produktif`, `riwayat_bantuan`, `housing_need` (turunan lantai/dinding/air/luas) | **Tidak satu pun** |
| Label latih | `label_historis` (layak / tidak layak) | Tidak, selama tidak melekat pada orang tertentu |
| Tier 1 (urgensi) | `teks_naratif` + label urgensi | Tidak, setelah dianonimkan |
| Tier 3 (peringkat) | keluaran Tier 1 & 2 + bobot kriteria | Tidak |

`nik`, `nama`, dan `alamat` **hanya dipakai untuk ditampilkan di dashboard**, tidak masuk model.
Presedennya sudah ada di proyek ini: data publik Alatas dkk. diberi penanda buatan
`PUB-ALATAS-<hhid>` — deterministik, jelas bukan NIK asli, dan sistem berjalan normal.

**Konsekuensi:** seluruh kebutuhan pelatihan model dapat dipenuhi oleh tabel tanpa identitas.

## 3. Periksa dulu — kemungkinan besar kelurahan memang tidak punya yang kita cari

Tier 1 membutuhkan **teks naratif** (uraian kondisi rumah tangga dalam kalimat bebas). Arsip DTKS
dan berkas bansos umumnya **tabular murni** — tidak memuat narasi sama sekali.

Bila benar demikian, maka:

- teks naratif lokal **tidak pernah bisa** datang dari arsip kelurahan, sekooperatif apa pun mereka;
- satu-satunya sumbernya adalah **pengumpulan data primer** (wawancara/survei ke warga);
- artinya penolakan kemarin **memblokir sumber label Tier 2, bukan Tier 1** — kerugiannya lebih
  kecil daripada yang terlihat.

**Tanyakan ini sebelum menyusun surat baru**, karena jawabannya menentukan apakah Lapisan C di bawah
wajib atau opsional.

## 4. Struktur permintaan yang baru — tiga lapisan

Kesalahan surat pertama bukan hanya isinya, melainkan **menggabungkan semuanya jadi satu permintaan**:
satu butir yang tidak boleh disetujui menjatuhkan seluruh surat. Pisahkan.

### Lapisan A — nol data pribadi (minta sekarang; peluang disetujui tinggi)

Tidak satu pun butir di bawah menyentuh data perorangan, jadi alasan penolakan kemarin tidak berlaku
untuknya:

1. **Kuota & anggaran** bansos per gelombang penyaluran (angka agregat).
2. **Kriteria dan prosedur penentuan penerima** yang berlaku sekarang (SOP / juknis / surat edaran).
3. **Pembobotan kepentingan antar kriteria menurut petugas** — mis. seberapa penting pendapatan
   dibanding kondisi rumah dibanding jumlah tanggungan.
   → Butir ini **langsung menutup OI-12/13**, yaitu bobot Fuzzy TOPSIS yang sampai sekarang masih
   provisional. Bawa hasil analisis sensitivitas (bobot digeser ±20% hanya mengubah 3–7% peringkat)
   sebagai bahan diskusi; itu menunjukkan pertanyaannya serius, bukan formalitas.
4. **Statistik agregat** kelurahan: jumlah KK, sebaran pekerjaan, jumlah penerima per gelombang —
   angka ringkasan, bukan baris per orang.
5. **Kesediaan 2–3 petugas** ikut sesi penilaian label dan UAT.
   → Ini permintaan **waktu orang, bukan data**, dan satu-satunya jalan menuju angka efektivitas
   ≥85% (OI-18) yang sampai kini nol pengukuran.

### Lapisan B — data tanpa identitas (permintaan lama yang diformulasi ulang)

Diminta sebagai tabel dengan **kode urut** `KK-001`, `KK-002`, … . Penting: **kelurahan sendiri yang
menghapus identitasnya**, bukan mahasiswa. Yang diserahkan sudah tidak mengandung data pribadi sejak
awal, sehingga tidak ada penyerahan data pribadi yang terjadi.

**Kolom yang diminta:**

| Kolom | Bentuk | Catatan |
|---|---|---|
| kode | `KK-001` … | pengganti identitas, dibuat kelurahan |
| usia kepala keluarga | tahun | |
| jumlah tanggungan | angka | |
| pendapatan | rupiah/bulan (rentang pun cukup) | |
| status pekerjaan | teks singkat | |
| aset produktif | ya / tidak | |
| pernah menerima bantuan | ya / tidak | **tanpa** menyebut program & tanggalnya |
| jenis lantai | tanah / kayu / papan / semen / plester / ubin / keramik | kosakata harus persis |
| jenis dinding | bambu / anyaman / kayu / papan / seng / batu bata / tembok | kosakata harus persis |
| sumber air | sungai / hujan / mata air / sumur / sumur bor / pdam / ledeng | kosakata harus persis |
| luas rumah | m² | |
| status penerima | layak / tidak layak | **label latih** — inti kebutuhan Tier 2 |

Kosakata kategorikal harus persis karena nilai yang tidak dikenal **diam-diam** dipetakan ke 0,5 oleh
`app/services/features.py` — salah tulis tidak memunculkan galat apa pun, hanya angka yang salah.

**Kolom yang TIDAK diminta — cantumkan daftar ini secara eksplisit di surat:**
NIK · nama · nama anggota keluarga · alamat · nomor KK · nomor telepon · tanggal lahir · foto ·
nomor rekening.

> Penolakan kemarin kemungkinan besar dipicu frasa **"data diri riwayat penerima bantuan"**.
> Hilangkan frasa itu dan cantumkan daftar "tidak diminta" di atas — permintaannya berubah sifat,
> dari penyerahan data pribadi menjadi penyerahan tabel anonim.

**Bila tetap tidak boleh keluar kantor:** ajukan **pengolahan di tempat** — mahasiswa datang, petugas
yang membuka berkas, mahasiswa hanya menyalin kolom di atas ke lembar kerja anonim. Tidak ada berkas
dibawa pulang. Opsi ini sering diterima justru ketika penyerahan berkas ditolak.

Sertakan **pernyataan penanganan data**: disimpan luring di satu laptop, hanya untuk keperluan
skripsi, tidak dipublikasikan per baris, dihapus setelah sidang.

### Lapisan C — tidak butuh izin kelurahan sama sekali (jalankan paralel, jangan menunggu)

6. **Data primer dari warga langsung**, dengan lembar persetujuan (*informed consent*): target
   **≥100 KK** (ambang OI-08). Satu wawancara menghasilkan **dua-duanya sekaligus** — fitur tabular
   untuk Tier 2 dan uraian kondisi dalam kalimat untuk Tier 1. Anonim sejak lahir (kode responden),
   jadi tidak ada persoalan PDP.
7. **Label dari penilaian petugas atas berkas anonim hasil (6)** — bukan dari arsip.
   [`protokol-validasi-label-historis.md`](protokol-validasi-label-historis.md) sudah ditulis dan
   tinggal dipakai.
   → Secara metodologis ini **lebih bersih daripada label arsip**: labelnya dibuat untuk penelitian
   dengan prosedur tercatat dan penilai yang diketahui, bukan warisan keputusan lama yang biasnya
   tak terlacak. Sirkularitas OI-18 (dilatih pada keputusan petugas, dinilai oleh petugas) tetap
   wajib ditulis sebagai keterbatasan.

## 5. Akibatnya pada klaim skripsi

| Skenario | Yang didapat | Klaim yang bisa dipertahankan |
|---|---|---|
| A + B + C | lengkap | Klaim penuh: model lokal, label arsip & petugas, efektivitas terukur |
| **A + C** (paling mungkin) | tanpa arsip penerima historis | **Tetap utuh.** Tier 1 & 2 dilatih/diuji pada data primer lokal; Tier 3 pakai bobot hasil kesepakatan; efektivitas diukur dari verifikasi petugas. Yang hilang hanya validasi terhadap arsip historis → ditulis sebagai keterbatasan |
| A saja | tanpa data lokal apa pun | *Proof-of-concept* di data publik; tiap tier tervalidasi terpisah, integrasi 3-tier diuji fungsional (blackbox) saja, bukan statistik |

Perhatikan: **Lapisan A saja sudah menutup dua butir yang macet** — bobot fuzzy final (Fase 6) dan
sesi petugas untuk efektivitas (Fase 7). Keduanya tidak pernah membutuhkan data pribadi, dan
seharusnya diminta terpisah supaya tidak ikut tertolak.

## 6. Yang harus diputuskan minggu ini

- [ ] Konfirmasi ke kelurahan: **apakah arsipnya memuat teks naratif?** (menentukan wajib/tidaknya
      Lapisan C)
- [ ] Susun surat kedua yang **hanya berisi Lapisan A** — jangan digabung dengan permintaan tabel
- [ ] Susun surat ketiga untuk Lapisan B: daftar kolom + daftar "tidak diminta" + opsi pengolahan di
      tempat + pernyataan penanganan data
- [ ] Tetapkan **tanggal go/no-go**: bila sampai tanggal itu Lapisan B belum disetujui, Lapisan C
      dijalankan penuh dan klaim skripsi dikunci ke skenario "A + C"
- [ ] Siapkan lembar persetujuan responden & instrumen wawancara untuk Lapisan C
