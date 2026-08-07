# Evaluasi Pra-Fase 3 — Tinjauan Fase 0, 1, dan 2

**Tanggal:** 2026-08-07 · **Cakupan:** seluruh pekerjaan sejak commit awal sampai sebelum Tier 2 disentuh

Tinjauan ini dikerjakan sebagai syarat masuk Fase 3, bukan sebagai laporan seremonial. Pertanyaannya
satu: **apa yang sudah terbukti berdiri, dan kekeliruan mana yang akan terulang di Fase 3 kalau tidak
dicegat sekarang.**

Dasar penilaian: seluruh berkas kode dan dokumen fase dibaca ulang; `pytest` dijalankan (**30 tes lulus**,
84 detik); dan satu probe diagnostik baru dijalankan atas data sintetis
([`probe_kelayakan_sintetis.py`](fase-3-tier2-ml/probe_kelayakan_sintetis.py)) untuk menguji lebih dulu
apakah Fase 3 dapat mencapai tujuannya sendiri.

---

## 1. Putusan ringkas

| Fase | Status nyata | Putusan |
|---|---|---|
| 0 — Kerangka integrasi | Selesai, terbukti di praktik | **Sehat.** Rancangan seam-nya terbayar |
| 1 — Data & pelabelan | Perkakas & dokumen selesai; **data belum ada satu pun** | **Jalur kritis.** Bukan Fase 3 yang menghambat skripsi, melainkan ini |
| 2 — Tier 1 IndoBERT | Kode selesai; model hanya sah sebagai validasi pipa | **Sehat, dan jujur.** Batas klaimnya sudah ditulis sendiri dengan benar |
| 3 — Tier 2 | Belum mulai | **Siap dimulai secara kode**, tetapi tujuan "pilih RF atau GB" belum dapat dicapai — lihat §5.1 |

---

## 2. Fase 0 — kerangka integrasi tipis

Keputusan membangun kerangka lebih dulu dengan tier berupa stub sekarang sudah dapat dinilai dari
hasilnya, bukan dari niatnya. Buktinya ada di Fase 2: mengganti stub Tier 1 dengan IndoBERT sungguhan
**tidak menyentuh satu pun rute, skema, atau template** — hanya `app/services/tier1_nlp.py` yang diisi
ulang, ditambah satu penyesuaian di `pipeline.py` (skoring batch). Itulah imbalan yang dijanjikan
kerangka tipis, dan ia benar-benar datang.

Konsekuensinya untuk Fase 3 bersifat memprediksi: penggantian Tier 2 akan sama murahnya, selama
kontrak `predict_eligibility(features) -> (hasil, probabilitas, versi_model)` dipertahankan. Ini
menghilangkan seluruh risiko integrasi dari Fase 3 dan memusatkan risikonya di satu tempat saja: data.

Penyimpangan Fase 0 (SQLite alih-alih PostgreSQL, pbkdf2_sha256 alih-alih bcrypt) tetap
terdokumentasi, reversibel, dan sampai sekarang tidak menimbulkan biaya. Tidak perlu ditinjau ulang
sebelum Fase 7.

**Catatan kebersihan repo — perlu tindakan.** Riwayat git berhenti di dua commit
(`f491dec`, `43fecd6`). Seluruh hasil Fase 1 dan Fase 2 — paket `ml/tier1/`, notebook Colab, rubrik,
protokol, perkakas kappa, `tests/test_tier1.py` — masih *untracked* atau *modified*. Pekerjaan dua fase
penuh saat ini hanya ada di satu salinan kerja tanpa cadangan. Commit sebelum menulis kode Fase 3, agar
diff Tier 2 nanti dapat dibaca terpisah.

## 3. Fase 1 — data & pelabelan

Yang sudah ada di sini berkualitas tinggi dan, penting, **saling terhubung**: rubrik pelabelan tidak
berhenti sebagai dokumen, ia diuji silang terhadap model Tier 1, kegagalannya dibaca balik sebagai
kelemahan rubrik, lalu rubrik diamandemen menjadi v1.1. Lingkar umpan balik dokumen ↔ model itu jarang
dikerjakan pada skripsi dan layak dijadikan bahan bab metodologi tersendiri.

Namun perlu dilihat apa adanya: dari sembilan butir daftar deliverable Fase 1, **yang tercentang hanya
dua** — keduanya dokumen. Yang belum ada:

- dataset publik (SUSENAS/Kaggle) — belum diunduh, belum diharmonisasi ke skema `data_survei`;
- pelabel kedua — belum direkrut, sehingga Cohen's kappa belum pernah dihitung terhadap data nyata;
- teks lokal Bontoramba — belum ada, izin data (OI-09) belum tuntas;
- sesi validasi label historis bersama petugas (OI-10) — belum berjalan.

Artinya seluruh perkakas Fase 1 sudah siap dipakai tetapi belum pernah dipakai pada data sungguhan.
**Inilah jalur kritis proyek.** Fase 2 sudah menabrak batas ini sekali (model final tertunda), dan §5
menunjukkan Fase 3 akan menabraknya dengan cara yang persis sama. Setiap minggu Jalur B tertunda,
tertunda pula klaim final Tier 1 *dan* Tier 2 sekaligus.

## 4. Fase 2 — Tier 1 IndoBERT

Penilaian teknisnya sudah dikerjakan sendiri dengan baik di
[README Fase 2](fase-2-tier1-indobert/README.md), dan penilaian itu benar. Tiga hal yang layak
ditegaskan ulang karena akan dipakai sebagai preseden di Fase 3:

1. **Akurasi 1,0000 dibaca sebagai temuan negatif, bukan prestasi.** Data uji yang tersusun dari bank
   klausa yang sama dengan data latih tidak menuntut generalisasi apa pun. Kesimpulan itu diambil
   sendiri sebelum ada yang menegur — itu standar yang harus dipertahankan.
2. **Satu-satunya angka informatif datang dari 24 kalimat tulisan manusia** (87,5% → 95,8%), dan
   perbaikan v1→v3 memindahkan kegagalan alih-alih mengurangi. Keputusan berhenti menyetel di iterasi
   ketiga tepat: iterasi keempat akan menjadi pengepasan terhadap set uji sendiri.
3. **Penanda `heuristik-fallback-v0`** memastikan hasil non-model tidak pernah dapat tercampur ke
   analisis. Pola ini wajib ditiru Tier 2.

Yang masih menganggur dari Fase 2: set uji jujur belum diperbesar ke ≥70 kalimat (target yang
ditetapkan sendiri), dan versi `lokal` belum ada. Keduanya bergantung pada Fase 1, bukan pada kode.

---

## 5. Temuan yang berdampak langsung ke Fase 3

Bagian ini adalah alasan sesungguhnya tinjauan ini dikerjakan.

### 5.1 Data sintetis tidak sanggup memilih RF atau GB — dan itu tujuan utama Fase 3

Deliverable inti Fase 3 adalah *membandingkan Random Forest dengan Gradient Boosting lalu memilih yang
terbaik* (OI-01). Probe dijalankan lebih dulu untuk menguji apakah itu mungkin di atas data yang kita
punya sekarang. Hasilnya (n=3.000 sintetis, uji 600, vektor fitur Tier 2 yang sebenarnya):

| Model | Akurasi | Presisi | Recall | F1 |
|---|---|---|---|---|
| Dummy (kelas mayoritas) | 0,5050 | — | — | — |
| Random Forest | 0,9117 | 0,9122 | 0,9091 | 0,9106 |
| Gradient Boosting | 0,9167 | 0,9273 | 0,9024 | 0,9147 |
| **Oracle (mengetahui faktor laten `k` persis)** | **0,9252** | — | — | — |

Baca baris terakhir lebih dulu. `data/synthetic/generator.py` menurunkan label dari
`label_historis = (k + U(-0,15; 0,15)) > 0,5`, sedangkan seluruh fiturnya juga diturunkan dari `k` yang
sama. Prediktor sempurna sekalipun — yang mengetahui `k` tanpa galat — hanya mencapai **92,52%**, karena
sisanya adalah derau yang sengaja disuntikkan generator dan tidak dapat ditebak siapa pun.

RF dan GB sudah menempel di langit-langit itu: selisih keduanya **0,0050**, sementara galat baku akurasi
pada 600 sampel uji adalah **0,0113** (±1,96·SE = ±0,0221). Selisih antar model **empat kali lebih kecil
daripada ketidakpastiannya sendiri**.

> **Konsekuensi: perbandingan RF vs GB di atas data sintetis tidak menghasilkan pemenang, hanya
> menghasilkan angka.** Menuliskan "Gradient Boosting terpilih karena akurasinya 91,67% berbanding
> 91,17%" ke dalam skripsi berarti melaporkan derau sebagai temuan.

Ini pengulangan persis pelajaran Fase 2, dengan wajah berbeda: di sana data buatan sendiri menghasilkan
100% yang tak bermakna, di sini menghasilkan ~91% yang tak bermakna. Angka 91% justru lebih berbahaya
karena *terlihat wajar* — ia tidak memicu kecurigaan seperti angka sempurna. Rencana Fase 3 harus
menyatakan batas ini di muka, bukan menemukannya belakangan.

### 5.2 Feature importance dari data sintetis adalah artefak generator

Perhatikan dua baris importance pada probe. Gradient Boosting menaruh **79,1%** bobot pada
`skor_urgensi`, sementara Random Forest membaginya rata bertiga (`housing_need` 0,29 · `skor_urgensi`
0,28 · `pendapatan` 0,26) — dua cerita yang sama sekali berbeda dari data yang sama.

Penyebabnya: di generator, `label_urgensi` dan `label_historis` sama-sama turunan langsung dari `k`,
sehingga `skor_urgensi` adalah jendela paling bersih ke arah label. Model tidak sedang menemukan bahwa
urgensi naratif penting bagi kelayakan; ia sedang menemukan cara pintas menuju `k`. **Grafik feature
importance dari data sintetis tidak boleh masuk skripsi**, dalam bentuk apa pun.

### 5.3 Sirkularitas label historis mengancam klaim efektivitas ≥85% (OI-18)

Rantai ini perlu ditulis terang-terangan sebelum Fase 3 dimulai:

- Tier 2 dilatih pada `label_historis`, yang pada data lokal berarti **keputusan petugas di masa lalu**;
- efektivitas sistem (target ≥85%, OI-18) diukur dengan membandingkan keluaran sistem terhadap
  **verifikasi manual petugas** (`log_pengujian.hasil_manual_petugas`).

Model dilatih meniru hakim, lalu dinilai oleh hakim yang sama. Akurasi tinggi dalam susunan ini
sebagian mengukur keberhasilan peniruan, bukan ketepatan penentuan kelayakan — termasuk **meniru bias
keputusan lama** bila ada. Ini bukan cacat yang bisa dikode habis; yang bisa dilakukan hanya dua:

1. Jalankan **protokol validasi label historis** (OI-10, sudah siap di Fase 1) **sebelum** pelatihan
   final Tier 2, sehingga label yang keliru terkoreksi lebih dulu dan tingkat kekeliruannya terukur.
2. Tuliskan sirkularitas ini sebagai keterbatasan eksplisit di bab hasil, disertai angka tingkat
   kekeliruan label dari butir 1.

### 5.4 Data lokal ≥100 KK terlalu kecil untuk split 80:20 sebagai dasar pemilihan model

Target OI-08 adalah ≥100 KK lokal. Dengan split 80:20 seperti tertulis di TRD, data uji berisi ~20
baris. Pada akurasi 0,85, galat baku 20 sampel adalah 0,080 — selang kepercayaan 95% membentang
**±15,6 poin persen**, kira-kira 0,69–1,00.

Artinya bahkan pada data lokal sekalipun, satu split 80:20 tidak akan sanggup membedakan RF dari GB, dan
angka efektivitas yang dilaporkan akan punya selang selebar itu. Split 80:20 tetap dijalankan demi
kepatuhan pada TRD, tetapi **pemilihan model harus digerakkan oleh validasi silang berulang**
(*repeated stratified k-fold*) di atas porsi latih, dengan rerata ± simpangan baku dilaporkan
berdampingan. Ini perubahan metodologi, dan lebih baik diputuskan sekarang daripada saat menulis bab IV.

### 5.5 Kebocoran antar-split harus dikelompokkan per warga, bukan per baris

Satu warga dapat mengajukan lebih dari sekali (`Warga` → banyak `Pengajuan`), dan pengajuan dari warga
yang sama nyaris identik fiturnya. Split acak per baris akan menempatkan kembaran di kedua sisi dan
menaikkan akurasi secara semu. Tier 1 sudah memecahkan masalah setara ini dengan pengelompokan berbasis
hash teks; Tier 2 harus melakukan hal yang sama dengan kunci `warga_id`/NIK.

### 5.6 Sumber data Fase 3 belum tersedia — sama seperti yang menghambat Fase 2

Rencana Fase 3 berbunyi "latih dulu di proxy publik (SUSENAS/Kaggle), lalu latih ulang di data lokal".
Proxy publik itu bagian dari deliverable Fase 1 yang **belum tercentang**. Fase 3 karena itu memasuki
kondisi yang persis sama dengan Fase 2 sebulan lalu: kode siap, data tidak ada. Keputusan sadar
diperlukan di muka, bukan improvisasi di tengah jalan — pilihan dan rekomendasinya ada di
[rencana Fase 3](fase-3-tier2-ml/README.md).

---

## 6. Kesiapan masuk Fase 3

**Sudah siap dan tidak perlu disentuh:**

- Kontrak `predict_eligibility()` beserta seam-nya di `pipeline.py` — penggantian model berbiaya rendah.
- Vektor fitur `app/services/features.py` sudah memuat tujuh fitur yang dibutuhkan, termasuk
  `skor_urgensi` dari Tier 1 (semantik `pendapatan` konsisten sebagai per kapita per bulan di seluruh
  lapisan: skema, formulir, ambang fuzzy).
- Tabel `prediksi_ml` sudah menampung `hasil`, `probabilitas`, `versi_model` — tidak ada migrasi baru.
- Dependensi terpasang: scikit-learn 1.7.2, pandas 2.3.3, joblib 1.5.3.
- Pola artefak, metadata, dan fallback bertanda versi sudah terbukti di Tier 1 dan tinggal ditiru.

**Harus diputuskan sebelum menulis kode:** sumber data latih Fase 3 (§5.6).

**Harus dikerjakan lebih dulu:** commit seluruh pekerjaan Fase 1 & 2 yang belum masuk git (§2).

**Diwariskan ke Fase 6, bukan Fase 3:** pemilihan pemenang RF vs GB (§5.1), feature importance untuk
skripsi (§5.2), dan angka efektivitas OI-18 (§5.3).
