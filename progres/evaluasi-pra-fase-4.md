# Evaluasi Pra-Fase 4 — Tinjauan Fase 0–3

**Tanggal:** 2026-08-07 · **Cakupan:** seluruh pekerjaan sampai Tier 2 terpasang, sebelum Tier 3 disentuh

Seperti [evaluasi pra-Fase 3](evaluasi-pra-fase-3.md), tinjauan ini bukan laporan seremonial.
Pertanyaannya dua: **apa yang sekarang benar-benar berdiri**, dan **kekeliruan mana yang akan
terulang di Fase 4 kalau tidak dicegat lebih dulu.**

Dasar penilaian: seluruh kode dan dokumen fase dibaca ulang; `pytest` dijalankan (**48 tes lulus**,
17 detik); pemasangan artefak diverifikasi lewat `info_model()` kedua tier; dan satu probe diagnostik
baru dijalankan atas 991 alternatif nyata
([`probe_fuzzy_topsis.py`](fase-4-tier3-fuzzy-topsis/probe_fuzzy_topsis.py), keluaran mentah di
[`hasil_probe.txt`](fase-4-tier3-fuzzy-topsis/hasil_probe.txt)).

---

## 1. Putusan ringkas

| Fase | Status nyata | Putusan |
|---|---|---|
| 0 — Kerangka integrasi | Selesai; sudah dua kali terbayar (Tier 1 & Tier 2) | **Sehat.** Berhenti mengevaluasinya sampai Fase 7 |
| 1 — Data & pelabelan | Perkakas lengkap; **data nyata masih nol** | **Jalur kritis, dan sekarang menua.** Sudah memblokir klaim final dua tier |
| 2 — Tier 1 IndoBERT | Kode selesai; artefak terpasang & terverifikasi | **Sehat**, tetapi §5.1 menemukan efek samping yang belum pernah terlihat |
| 3 — Tier 2 ML | Kode selesai; artefak terpasang & terverifikasi | **Sehat dan jujur.** Batas klaim ditulis sebelum pelatihan — perbaikan nyata atas Fase 2 |
| 4 — Tier 3 | Belum mulai | **Siap dimulai**, dan tidak seperti Fase 3, tujuannya **dapat dicapai sekarang** — lihat §5 |

**Satu tindakan tertunggak dan makin mendesak:** riwayat git masih berhenti di `43fecd6`
(2 commit). Hasil Fase 1, 2, dan 3 — paket `ml/tier1/`, `ml/tier2/`, rubrik, protokol, notebook,
30 tes baru — seluruhnya masih *untracked* atau *modified*. Ini sudah dicatat sebagai prasyarat di
evaluasi pra-Fase 3 §2 dan **tetap tidak dikerjakan**; sekarang tiga fase penuh menggantung di satu
salinan kerja tanpa cadangan. Lihat §7.

---

## 2. Verifikasi pemasangan — pelajaran `.env` sudah dipakai

Kali ini pemasangan artefak diperiksa lebih dulu, bukan diasumsikan:

| Tier | `versi_model` | `fallback_aktif` | Putusan |
|---|---|---|---|
| 1 | `indobert-p1-augmentasi-v3` | `False` | Artefak asli dipakai |
| 2 | `tier2-random-forest-sintetis-v1` | `False` | Artefak asli dipakai |

Kedua tier melayani dari model sungguhan, bukan dari cadangan. Jebakan `.env` menimpa `.env.example`
yang menjatuhkan Fase 2 *dan* Fase 3 tidak terulang di sini — bukan karena beruntung, melainkan
karena Fase 3 menambahkan penanda `versi_model` dan memperbaiki `info()` agar memaksa percobaan muat
lebih dulu. **Pola ini sekarang terbukti; jangan hilangkan.**

> Satu sisa: `ml/tier1/infer.py` masih berperilaku lama — `info()`-nya melaporkan
> `fallback_aktif: false` sebelum pemuatan pertama. Di verifikasi di atas ia benar hanya karena satu
> kali skoring dijalankan lebih dulu. Rapikan saat Tier 1 disentuh berikutnya (bukan pekerjaan Fase 4).

## 3. Fase 3 — apa yang terbukti benar

Dua ramalan evaluasi pra-Fase 3 terbukti persis, dan itu memberi kepercayaan pada metode kerjanya:

1. **Probe meramalkan RF vs GB tidak dapat dipilih** (selisih 0,0050 vs galat baku 0,0113). Fase 3
   dijalankan penuh dan menemukan hal yang sama pada keempat kandidat: selisih F1 dua teratas 0,0005
   berbanding simpangan gabungan 0,0201. Prosedur pemilihan **mendeteksinya sendiri** dan menulis
   `dapat_dibedakan: false` ke metadata — bukan sekadar melaporkan pemenang.
2. **Pengelompokan split per warga bukan kehati-hatian teoretis:** generator memang menghasilkan
   2.020 pengajuan dari 2.000 warga. Tanpa pengelompokan, 20 kembaran akan tersebar ke kedua sisi.

Yang paling bernilai dari Fase 3 justru bukan modelnya, melainkan **analisis 40 kasus salah**: tanpa
ciri fitur apa pun, dan 24 dari 40 terjadi pada probabilitas yang percaya diri. Itu tanda tangan
*label yang salah*, bukan model yang lemah — dan ia menutup pertanyaan "apakah masih ada ruang
perbaikan di data sintetis" dengan bukti, bukan dengan pendapat. **Berhenti menyetel Tier 2 di data
sintetis adalah keputusan yang benar dan sudah beralasan cukup.**

## 4. Fase 1 masih jalur kritis — dan sekarang menua

Tidak ada perubahan sejak evaluasi sebelumnya, dan itulah masalahnya. Yang masih kosong: dataset
publik (SUSENAS/Kaggle), pelabel kedua (kappa belum pernah dihitung atas data nyata), teks lokal
Bontoramba (izin OI-09), dan sesi validasi label historis (OI-10).

Neraca sekarang: **tiga tier akan selesai secara kode sementara nol angka yang layak masuk bab hasil
sudah dihasilkan.** Fase 4 tidak akan memperbaiki neraca itu — Tier 3 bahkan tidak punya label
kebenaran sama sekali (§5.5). Setelah Fase 4, Jalur A hampir kehabisan pekerjaan yang dapat
dikerjakan tanpa data; Fase 5 (dashboard) adalah sisa terakhirnya.

---

## 5. Temuan probe yang berdampak langsung ke Fase 4

Probe menjalankan **991 alternatif nyata** — pengajuan sintetis yang diloloskan Tier 2 sungguhan
(`tier2-random-forest-sintetis-v1`), dengan skor urgensi dari IndoBERT sungguhan. Ini batch OI-15
yang sebenarnya, bukan data mainan terpisah.

### 5.1 `skor_urgensi` tersaturasi — ia bukan kriteria kontinu, melainkan saklar biner

Temuan paling penting, dan sepenuhnya baru:

| Kriteria | min | median | maks | nilai berbeda | % menempel di ujung |
|---|---|---|---|---|---|
| pendapatan | 150.000 | 1.017.849 | 2.569.595 | 906 | 8,4% |
| jumlah_tanggungan | 0 | 4 | 8 | 9 | 0,5% |
| housing_need | 0,325 | 0,775 | 1,000 | 343 | 17,0% |
| **skor_urgensi** | **0,0002** | **0,9998** | **0,9999** | **5** | **100,0%** |

Sebarannya: 105 alternatif di 0,0002; 886 sisanya di ≥0,9939. **Tidak ada satu pun di antaranya.**

Penyebabnya dapat ditelusuri persis, dan ia adalah konsekuensi langsung dari temuan Fase 2 yang
selama ini hanya dibaca sebagai soal metrik. Korpus augmentasi membuat kedua kelas terpisah sempurna
(akurasi 1,0000) → IndoBERT belajar memisahkannya dengan margin sangat lebar → softmax menjenuh.
Diperiksa pada margin logit mentahnya:

| Kalimat | margin logit | probabilitas (presisi penuh) | tersimpan |
|---|---|---|---|
| "Suami saya di-PHK dan kami belum makan layak dua hari ini." | +8,656 | 0,999825906 | 0,9998 |
| "Rumah kami bocor parah, anak sakit, tidak ada biaya berobat." | +8,204 | 0,999726404 | 0,9997 |
| "Anak saya putus sekolah karena tidak ada biaya." | +7,446 | 0,999416835 | 0,9994 |
| "Kadang atap sedikit rembes kalau hujan deras, tapi masih bisa ditambal." | −6,385 | 0,001684351 | 0,0017 |
| "Kondisi keluarga kami masih tercukupi dan tidak ada yang sakit." | −8,559 | 0,000191831 | 0,0002 |

**Margin logit membentang −8,6 sampai +8,7 dengan resolusi berlimpah; sigmoid-lah yang meremasnya
menjadi dua titik.** Informasi urutannya tidak hilang di model — ia hilang di langkah terakhir.

Ini membatalkan sebagian keputusan OI-02 yang selama ini dianggap terkunci. "Label urgensi biner,
probabilitas menjadi skor kontinu" benar sebagai rancangan, tetapi **pada model yang terpisah sempurna,
probabilitas tidak kontinu.** Untuk Tier 2 itu tidak fatal (pohon keputusan hanya butuh urutan). Untuk
Tier 3 itu fatal: sebuah kriteria berbobot **0,25** yang seharusnya membedakan derajat kemendesakan
justru hanya menjawab ya/tidak, dan memfuzzifikasinya ke empat himpunan linguistik berarti mengisi
dua himpunan dan mengosongkan dua sisanya.

Keputusan yang diperlukan ada di §6 butir 2. Perlu ditegaskan: **saturasi ini artefak korpus sintetis**
— pada teks lokal yang beragam, pemisahannya hampir pasti tidak sesempurna ini. Yang harus dilakukan
Fase 4 bukan memperbaiki Tier 1, melainkan **tidak berpura-pura kriteria itu kontinu** dan menyediakan
jalur yang siap ketika datanya membaik.

### 5.2 Kuantisasi linguistik polos menghancurkan perangkingan

Bentuk Fuzzy TOPSIS yang paling lazim ditulis di skripsi — petakan tiap nilai ke satu himpunan
linguistik (sangat rendah/rendah/sedang/tinggi), lalu pakai bilangan fuzzy wakil himpunan itu —
diuji langsung. Kuota diandaikan 50 penerima dari 991 alternatif:

| Varian fuzzifikasi | nilai preferensi unik | grup seri terbesar | **seri di garis kuota** | ρ vs crisp | top-50 sama |
|---|---|---|---|---|---|
| degenerat *(kontrol, lebar TFN = 0)* | 456 | 37 | 1 | 0,7724 | 58,0% |
| **linguistik** *(kuantisasi polos)* | **81** | **72** | **25** | 0,9160 | 54,0% |
| **keanggotaan** *(derajat penuh)* | **550** | **18** | **1** | 0,8635 | 54,0% |
| langsung *(lebar tetap)* | 470 | 34 | 1 | 0,7888 | 58,0% |
| hibrida *(lebar adaptif)* | 453 | 37 | 5 | 0,7768 | 62,0% |
| *(TOPSIS crisp — stub Fase 0)* | 859 | 14 | 14 | 1,0000 | 100% |

Baca kolom **seri di garis kuota**. Pada varian linguistik, **25 dari 50 kursi penerima bantuan
jatuh pada nilai preferensi yang persis sama.** Setengah daftar penerima akan ditentukan oleh urutan
baris di basis data, bukan oleh metode apa pun. 991 alternatif diperas menjadi 81 nilai berbeda —
kuantisasi lossy, dan yang dibuang justru perbedaan halus yang menjadi alasan perangkingan ada.

Varian **keanggotaan** — nilai tidak dipaksa ke satu himpunan, melainkan derajat keanggotaannya
terhadap seluruh himpunan dihitung lalu bilangan fuzzy dirata-rata berbobot — menghasilkan **550
nilai berbeda** (lebih halus daripada seluruh varian lain) dan **tanpa seri di garis kuota**, dengan
tetap memakai fungsi keanggotaan segitiga yang sama. Kefuzzian tidak perlu dibayar dengan daya beda.

Yang layak dicatat: varian linguistik **sudah men-defuzzifikasi diam-diam** di langkah pertama dengan
memilih satu himpunan. Ia bukan versi yang lebih fuzzy, melainkan yang lebih kasar.

### 5.3 Sebagian besar "efek fuzzy" ternyata bukan efek fuzzy

Selisih antara Fuzzy TOPSIS dan TOPSIS crisp besar (top-50 hanya 54–62% sama). Godaannya adalah
menulis "fuzzifikasi mengubah 40% daftar penerima" ke bab hasil. Probe menjalankan satu kontrol untuk
mengujinya: **mesin Fuzzy TOPSIS dijalankan dengan bilangan fuzzy berlebar nol** (l = m = u). Fuzzy
secara mekanik, tanpa kefuzzian sama sekali.

| Perbandingan | ρ | top-50 sama | Apa yang diukur |
|---|---|---|---|
| crisp → degenerat | 0,7724 | **58,0%** | Definisi TOPSIS-nya: normalisasi linier, solusi ideal mutlak (1,1,1)/(0,0,0), jarak vertex dijumlahkan antar-kriteria |
| degenerat → keanggotaan | 0,8526 | 74,0% | Kefuzzian yang sesungguhnya |
| degenerat → hibrida | 0,9968 | 96,0% | Kefuzzian (lebar adaptif) |
| degenerat → linguistik | 0,8332 | **34,0%** | Kuantisasi — merusak, bukan menambah |

**42% pergantian daftar penerima terjadi tanpa satu pun bilangan fuzzy yang punya lebar.** Ia berasal
dari perbedaan rumusan TOPSIS (Chen 2000 memakai solusi ideal *mutlak*; stub Fase 0 memakai
maksimum/minimum *teramati*), bukan dari logika fuzzy. Kefuzzian sendiri hanya menggeser 26%
(keanggotaan) atau 4% (hibrida).

> Tanpa kontrol ini, seluruh selisih akan salah diatribusikan ke "fuzzy" di bab hasil. Klaim yang
> sah berbunyi: *rumusan Fuzzy TOPSIS Chen (2000) menghasilkan perangkingan yang berbeda dari TOPSIS
> crisp, dan sebagian besar perbedaan itu berasal dari definisi solusi idealnya, bukan dari
> fuzzifikasi.* Baris `degenerat` wajib ikut dilaporkan sebagai kontrol.

### 5.4 Bobot provisional ternyata BUKAN risiko dominan — dan fuzzy justru menstabilkan

Kekhawatiran yang wajar: OI-12 belum tuntas, jadi bobot masih karangan sendiri. Diuji dengan 200
perturbasi acak per metode:

| Metode | top-50 bertahan (±20%) | peringkat-1 berubah | top-50 bertahan (±50%) | peringkat-1 berubah |
|---|---|---|---|---|
| crisp | 93,2% | 3,5% | 86,8% | **32,0%** |
| linguistik | 92,9% | 0,0% | 88,7% | 0,0% |
| keanggotaan | 97,2% | 0,0% | 89,3% | 0,0% |
| hibrida | 98,4% | 0,0% | 96,4% | 0,0% |

Dua hal terbaca sekaligus. **Pertama, kabar baik:** daftar penerima cukup kokoh terhadap
ketidakpastian bobot — ±20% hanya menggeser 3–7% kursi. Tier 3 tidak lumpuh menunggu OI-12; ia hanya
tidak boleh mengklaim nilai preferensi sebagai angka pasti. **Kedua, argumen substantif pertama untuk
memakai fuzzy sama sekali:** varian fuzzy lebih stabil daripada crisp, dan peringkat-1 crisp berpindah
pada 32% perturbasi ±50% sementara varian fuzzy tidak pernah. Lebar bilangan fuzzy menyerap
ketidakpastian bobot — persis fungsi yang seharusnya dijalankan logika fuzzy.

Ini bahan bab hasil yang sah **sekalipun datanya sintetis**, karena yang diukur sifat metode terhadap
perturbasi, bukan ketepatan prediksi terhadap kebenaran. Bandingkan dengan seluruh metrik Tier 1 & 2
yang tidak dapat diklaim — di sinilah Tier 3 berbeda (§5.5).

### 5.5 Tier 3 tidak punya label kebenaran — dan itu mengubah cara memvalidasinya

Tier 1 dan Tier 2 punya label; Tier 3 tidak. Tidak ada "peringkat yang benar" untuk dibandingkan.
Konsekuensinya tegas: **akurasi tidak akan pernah dapat dilaporkan untuk Tier 3**, di data sintetis
maupun lokal. Yang dapat divalidasi hanya tiga hal, dan ketiganya harus masuk rencana Fase 4:

1. **Kebenaran aritmetik** — contoh perhitungan manual 4–5 alternatif dihitung tangan, dicocokkan
   dengan keluaran kode sampai digit terakhir. Ini pengganti "akurasi" bagi Tier 3, dan wajib jadi tes.
2. **Sifat metode** — sensitivitas bobot, atribusi §5.3, perilaku seri. Sah dilaporkan sekarang.
3. **Kesepakatan pakar** — apakah peringkat sistem masuk akal bagi petugas (Fase 6/7, OI-12 & OI-18).

Kabar baiknya: **berbeda dari Fase 3, tujuan Fase 4 dapat dicapai sepenuhnya sekarang.** Fase 3 tidak
dapat memilih RF vs GB karena butuh label yang bermutu; Fase 4 tidak butuh label sama sekali untuk
butir 1 dan 2. Data sintetis cukup — asalkan yang diklaim hanya butir 1 dan 2.

### 5.6 Seri sejati ada dan tidak dapat dihapus — perlu aturan tiebreak yang tercatat

6,1% alternatif (60 dari 991) memiliki vektor kriteria yang **persis kembar**, grup terbesar 10 warga.
Dua warga dengan data identik memang layak memperoleh nilai preferensi identik; yang salah bukan
serinya, melainkan tidak adanya aturan yang menentukan apa yang terjadi sesudahnya.

Terpisah dari itu, stub Fase 0 **memproduksi seri tambahan sendiri**: `rank_topsis()` membulatkan
nilai preferensi ke 4 desimal *sebelum* mengurutkan (`tier3_topsis.py:65`), sehingga grup seri
terbesarnya 14 padahal kembar sejati terbesar hanya 10. Pembulatan itu untuk tampilan, dan ia bocor
ke keputusan. Fase 4 harus mengurutkan pada presisi penuh dan membulatkan hanya saat menampilkan.

---

## 6. Keputusan yang harus diambil sebelum menulis kode Fase 4

| # | Keputusan | Dasar |
|---|---|---|
| 1 | **Fuzzifikasi memakai derajat keanggotaan penuh**, bukan pemetaan ke satu himpunan | §5.2 — kuantisasi polos menyeret 25 seri ke garis kuota; varian keanggotaan nol seri dan justru paling halus |
| 2 | **`skor_urgensi` tidak diperlakukan sebagai kriteria kontinu selama masih tersaturasi** | §5.1 — 5 nilai berbeda, 100% menempel di ujung |
| 3 | **Laporkan kontrol `degenerat`** berdampingan dengan hasil fuzzy | §5.3 — 42% selisih bukan berasal dari kefuzzian |
| 4 | **Analisis sensitivitas bobot menjadi deliverable Fase 4**, bukan catatan tambahan | §5.4 — satu-satunya klaim Tier 3 yang sah di data sintetis |
| 5 | **Aturan tiebreak eksplisit, deterministik, tercatat**; urutkan pada presisi penuh | §5.6 — seri sejati 6,1% + seri buatan akibat pembulatan |
| 6 | **Validasi lewat perhitungan manual, bukan metrik akurasi** | §5.5 — Tier 3 tidak punya label kebenaran |

Untuk butir 2, tiga pilihan tersedia — keputusan ada pada pembimbing/penulis:

| Opsi | Isi | Konsekuensi |
|---|---|---|
| **2a (rekomendasi)** | Pakai **margin logit** Tier 1 (bukan probabilitas) sebagai nilai crisp kriteria urgensi, dinormalisasi ke 0–1 lewat fungsi keanggotaan | Resolusi penuh kembali (§5.1); butuh `score_urgency()` mengekspos margin — perubahan kecil & tak merusak kontrak; menambah satu paragraf metodologi |
| 2b | Pertahankan probabilitas, turunkan bobot urgensi sampai sifat binernya tidak mendominasi | Tidak menyentuh Tier 1, tetapi bobot menjadi tambalan teknis yang harus dijelaskan ke kelurahan — mencemari OI-12 |
| 2c | Biarkan apa adanya, tulis sebagai keterbatasan | Paling murah; tetapi kriteria berbobot 0,25 bekerja sebagai saklar biner tanpa ada yang menyadarinya saat membaca bab hasil |

Rekomendasi **2a**, dengan catatan bahwa saturasinya sendiri artefak korpus sintetis: pada data lokal
efeknya kemungkinan mengecil, tetapi jalur logit tetap benar dan tidak merugikan bila saturasi hilang.

---

## 7. Kesiapan masuk Fase 4

**Sudah siap dan tidak perlu disentuh:**

- Kontrak `rank_topsis(alternatives, bobot, arah) -> list[RankingEntry]` beserta seam-nya di
  `pipeline.jalankan_ranking()`; penggantian Tier 3 sudah dibuktikan murah dua kali (Tier 1, Tier 2).
- Alur OI-15 sudah terpasang benar: batch dibentuk dari `PrediksiML.hasil == LAYAK` — probe
  memverifikasinya menghasilkan 991 dari 2.020.
- `config/fuzzy_config.yaml` + `load_fuzzy_config()` sudah memisahkan bobot & arah dari kode (FR-19,
  NFR-06); tinggal ditambah blok fungsi keanggotaan (OI-13).
- Tabel `ranking_topsis` sudah menampung `nilai_preferensi`, `peringkat`, `bobot_snapshot` — tidak
  ada migrasi baru yang diperlukan.
- Dependensi terpasang dan lebih baru dari batas bawah: **scikit-fuzzy 0.5.0**, numpy 1.26.4,
  scipy 1.15.3.
- Kedua tier hulu melayani dari artefak asli, terverifikasi (§2) — batch Tier 3 tidak tercemar fallback.

**Harus dikerjakan lebih dulu:** commit pekerjaan Fase 1–3 ke git (§1). Tertunggak sejak evaluasi
sebelumnya; sarannya tiga commit terpisah per fase agar diff Tier 3 nanti terbaca sendiri.

**Harus diputuskan sebelum menulis kode:** perlakuan `skor_urgensi` (§6 butir 2).

**Diwariskan ke Fase 6, bukan Fase 4:** nilai bobot final (OI-12), rentang fungsi keanggotaan final
dalam Rupiah (OI-13), kesepakatan pakar atas perangkingan, dan angka efektivitas OI-18.

**Yang berbeda dari Fase 3 dan layak disyukuri:** Fase 4 tidak perlu menunggu data untuk menyelesaikan
tujuannya. Kebenaran aritmetik dan sifat metode dapat divalidasi penuh hari ini. Untuk pertama kalinya
sejak Fase 0, sebuah fase Jalur A dapat ditutup **tanpa** menuliskan "menunggu data lokal" di kolom
hasilnya — asalkan yang diklaim memang hanya kedua hal itu.
