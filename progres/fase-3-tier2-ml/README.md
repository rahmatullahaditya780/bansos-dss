# Fase 3 — Tier 2 Matang: Klasifikasi ML (Kelayakan)

**Jalur:** A · **Target:** minggu 5–6 · **Status:** 🔶 Kode & pipa SELESAI (opsi A dijalankan); pemilihan model & metrik final menunggu data lokal

## Tujuan

Mengganti stub Tier 2 dengan model terlatih (Random Forest vs Gradient Boosting) yang memprediksi
kelayakan (`layak` / `tidak_layak`) dari fitur terstruktur + skor urgensi Tier 1, beserta perkakas
perbandingan model yang sanggup memilih pemenang **ketika data yang layak dipilih sudah tersedia**.

Tujuan itu sengaja dirumuskan dalam dua bagian, karena [evaluasi pra-Fase 3](../evaluasi-pra-fase-3.md)
§5.1 menunjukkan bagian kedua belum dapat diselesaikan sekarang.

## Batas yang sudah diketahui sebelum mulai

Probe [`probe_kelayakan_sintetis.py`](probe_kelayakan_sintetis.py) dijalankan lebih dulu untuk menguji
apakah Fase 3 dapat mencapai tujuannya di atas data yang ada:

| Model | Akurasi | Catatan |
|---|---|---|
| Dummy (mayoritas) | 0,5050 | dasar acuan |
| Random Forest | 0,9117 | |
| Gradient Boosting | 0,9167 | |
| **Oracle (tahu faktor laten `k`)** | **0,9252** | langit-langit teoritis data sintetis |

Selisih RF vs GB **0,0050** berbanding galat baku **0,0113** — selisihnya empat kali lebih kecil daripada
ketidakpastiannya sendiri. **Data sintetis tidak dapat memilih pemenang.** Ini pengulangan pelajaran
Fase 2 dalam bentuk lain: angka ~91% yang tampak wajar sama tak bermaknanya dengan angka 100% yang
mencurigakan, karena keduanya berasal dari data yang kita karang sendiri.

Karena itu Fase 3 dijalankan dengan pembagian tugas yang tegas:

| Yang dikerjakan Fase 3 | Yang ditunda ke Fase 6 |
|---|---|
| Seluruh kode: fitur, split, latih, banding, evaluasi, inference | Pemilihan final RF vs GB |
| Bukti pipa berjalan utuh dari DB → prediksi tersimpan | Angka akurasi/presisi/recall untuk bab hasil |
| Perkakas analisis FP/FN & permutation importance | Grafik feature importance untuk skripsi |
| Prosedur pemilihan model (CV berulang) yang teruji | Angka efektivitas OI-18 |

## Keputusan yang menunggu: sumber data latih

Proxy publik (SUSENAS/Kaggle) adalah deliverable Fase 1 yang **belum tercentang**, sehingga Fase 3
memasuki kondisi yang sama dengan Fase 2 sebulan lalu. Tiga pilihan:

| Opsi | Isi | Konsekuensi |
|---|---|---|
| **A (rekomendasi)** | Bangun kode di atas data sintetis sekarang; Jalur B mengejar proxy publik paralel; pemilihan model ditunda ke data lokal | Fase 3 tidak memblokir Fase 4; batas klaim sudah dinyatakan di muka |
| B | Tunggu proxy publik siap, baru mulai | Fase 4 & 5 ikut tergeser; ketersediaan data rumah tangga BPS tidak dapat dipastikan waktunya |
| C | Tunggu data lokal | Menghentikan Jalur A sepenuhnya sampai izin OI-09 tuntas |

Opsi A dipilih dengan alasan yang sama seperti Fase 2, dan dengan kejujuran yang sama: **metrik atas
data sintetis hanya memvalidasi pipa.** Perbedaannya, kali ini batas itu ditulis sebelum pelatihan,
bukan sesudah. **Opsi A dijalankan pada 2026-08-07** — hasilnya di bagian [Hasil](#hasil) di bawah.

## Yang dibangun

| Berkas | Isi |
|---|---|
| `ml/tier2/__init__.py` | `FITUR` (urutan kanonik), `LABEL2ID`, konstanta versi fallback |
| `ml/tier2/skema_fitur.py` | `vektor(features) -> list[float]` — **satu sumber**, dipakai jalur latih *dan* inference (anti train/serve skew, meniru pola Tier 1) |
| `ml/tier2/dataset.py` | Muat dari DB/CSV; split 80:20 stratified **dikelompokkan per warga**; `periksa_kebocoran()` |
| `ml/tier2/train.py` | Latih RF & GB, banding lewat *repeated stratified k-fold*, simpan artefak + metadata + tabel perbandingan |
| `ml/tier2/evaluate.py` | Akurasi, presisi, recall, F1, confusion matrix, ROC-AUC, Brier; **analisis FP/FN** & permutation importance |
| `ml/tier2/infer.py` | `EligibilityClassifier` — pemuatan malas, thread-safe, fallback ke skor logistik Fase 0 |
| `app/services/tier2_ml.py` | Pembungkus tipis; **kontrak `predict_eligibility()` dipertahankan** |
| `tests/test_tier2.py` | Skema fitur, split & kebocoran, kontrak inference, fallback bertanda, model asli |

Artefak disimpan sebagai direktori `ml/artifacts/tier2/` (`model.joblib`, `metadata.json`,
`metrics.json`, `perbandingan.csv`) agar simetris dengan Tier 1; `settings.ml_model_path` disesuaikan
dari `ml/artifacts/classifier.joblib` menjadi `ml/artifacts/tier2` (ikut diperbarui di `.env.example`
**dan** `.env` lokal — lihat catatan integrasi di bawah).

## Hasil

### Data

`data/synthetic/seed.py` mengisi 2.000 pengajuan sintetis, lalu `ml.tier2.dataset` mengekspornya
dengan skor urgensi dihitung oleh model Tier 1 yang sungguhan (`indobert-p1-augmentasi-v3`), bukan
proksi — supaya fitur yang dilihat model saat latih identik dengan yang dilihatnya saat melayani.

| | Jumlah | Warga unik | layak / tidak_layak |
|---|---|---|---|
| Total | 2.020 | 2.000 | 1.001 / 1.019 |
| Latih | 1.615 | 1.600 | 802 / 813 |
| Uji | 405 | 400 | 199 / 206 |

Kebocoran warga uji ke latih: **0**. Perhatikan selisih jumlah pengajuan dan warga unik — generator
memang menghasilkan warga yang mengajukan lebih dari sekali, sehingga pengelompokan per warga
(§5.5 evaluasi) bukan kehati-hatian teoretis: tanpa itu, 20 kembaran akan tersebar ke kedua sisi.

### Perbandingan kandidat (validasi silang 5 lipatan × 5 ulangan = 25 pengukuran)

| Kandidat | F1 (`layak`) | Akurasi | Recall (`layak`) |
|---|---|---|---|
| **random_forest** | 0,9171 ± 0,0138 | 0,9194 ± 0,0123 | **0,9021** |
| random_forest_seimbang | 0,9176 ± 0,0146 | 0,9199 ± 0,0128 | 0,9020 |
| gradient_boosting | 0,9128 ± 0,0155 | 0,9154 ± 0,0137 | 0,8956 |
| gradient_boosting_seimbang | 0,9145 ± 0,0161 | 0,9169 ± 0,0141 | 0,8984 |

**Keempat kandidat tidak dapat dibedakan.** Selisih F1 dua teratas 0,0005 berbanding simpangan
gabungan 0,0201 — persis seperti yang diramalkan probe. Prosedur pemilihan mendeteksinya sendiri,
menuliskan `dapat_dibedakan: false` ke `metadata.json`, dan menjatuhkan putusan pada recall kelas
`layak` sesuai keputusan teknis #8. Pemenang formalnya `random_forest`, dan status itu **tidak boleh
dilaporkan sebagai temuan** — ia hanya cara yang tercatat untuk memilih satu artefak yang harus
dipakai sistem.

### Holdout 80:20 — `tier2-random-forest-sintetis-v1`

| Metrik | Nilai |
|---|---|
| Akurasi | 0,9012 ± 0,0291 (95%) |
| Presisi / Recall (`layak`) | 0,9119 / 0,8844 |
| F1 (`layak`) | 0,8980 |
| ROC-AUC | 0,9670 |
| Brier | 0,0718 |
| Confusion | TN 189 · FP 17 · FN 23 · TP 176 |

Bandingkan dengan **langit-langit oracle 0,9252**: model duduk di dalam selang kepercayaannya sendiri
terhadap batas teoretis. Tidak ada ruang perbaikan tersisa di data ini — menyetel hyperparameter
lebih jauh hanya akan mengejar derau, seperti iterasi keempat korpus Tier 1 yang sudah dihentikan.

### Analisis FP/FN — 40 kasus salah (23 FN, 17 FP)

Daftar lengkapnya di [`analisis_kesalahan.csv`](analisis_kesalahan.csv). Yang menarik justru bahwa
kasus salah itu **tidak punya ciri apa pun**:

| Fitur | Median kasus salah | Median seluruh data uji |
|---|---|---|
| pendapatan | 1.738.561 | 1.737.735 |
| housing_need | 0,558 | 0,575 |
| skor_urgensi | 0,000 | 0,000 |

Kesalahan tidak menumpuk di wilayah fitur tertentu, dan **24 dari 40 terjadi dengan probabilitas
yang percaya diri** (di luar rentang 0,3–0,7). Pada model yang lemah, kesalahan berkumpul di dekat
ambang dan pada wilayah fitur yang membingungkan. Pola di sini kebalikannya, dan artinya jelas:
**yang salah bukan modelnya, melainkan labelnya** — derau `U(-0,15; 0,15)` yang sengaja disuntikkan
generator membalik sebagian label, dan model dengan percaya diri melaporkan apa yang sebenarnya
terjadi. Ini konfirmasi ketiga bahwa data sintetis sudah habis daya diagnostiknya.

### Permutation importance (penurunan F1 saat fitur diacak, diukur di data uji)

| Fitur | Penurunan F1 |
|---|---|
| skor_urgensi | +0,1263 ± 0,0158 |
| housing_need | +0,0389 ± 0,0091 |
| pendapatan | +0,0159 ± 0,0069 |
| riwayat_bantuan · aset_produktif · jumlah_tanggungan · usia | ≈ 0 atau negatif |

> **Jangan masukkan tabel ini ke skripsi.** Empat fitur terbawah tampak tidak berguna semata-mata
> karena generator tidak memakainya untuk menentukan label; `skor_urgensi` mendominasi karena
> urgensi dan kelayakan sama-sama diturunkan dari faktor laten `k` yang sama (evaluasi §5.2).
> Tabel ini dilampirkan sebagai bukti perkakasnya berjalan, bukan sebagai temuan tentang kelayakan.

### Catatan integrasi

Dua hal terungkap saat verifikasi end-to-end setelah pelatihan, keduanya sudah diperbaiki:

1. **`.env` lokal menimpa `ml_model_path`** dengan nilai lama `ml/artifacts/classifier.joblib`,
   sehingga aplikasi diam-diam tetap memakai skor logistik cadangan meski artefak sudah ada — dan
   seluruh tes tetap hijau, karena tes kontrak hanya memeriksa *bentuk* keluaran. Ini persis jenis
   kegagalan senyap yang dicegah penanda `versi_model`: yang menyingkapnya adalah `versi_model`
   bertuliskan `stub-logistik-fallback-v0`, bukan kegagalan tes.
2. **`info()` melaporkan `fallback_aktif: false` sebelum pemuatan pertama** — kebalikan dari yang
   ingin diketahui orang yang memanggilnya untuk memverifikasi pemasangan artefak. Kini `info()`
   memaksa percobaan muat lebih dulu. *(`ml/tier1/infer.py` masih berperilaku lama; tidak diubah
   karena di luar cakupan Fase 3, tetapi `info_model()` Tier 1 sebaiknya dipanggil setelah satu
   kali skoring bila dipakai untuk verifikasi.)*

Verifikasi akhir: `versi_model` = `tier2-random-forest-sintetis-v1`, `fallback_aktif` = `False`,
rumah tangga miskin → `layak` (p=0,9978), rumah tangga mampu → `tidak_layak` (p=0,0003).
**48 tes lulus** (sebelumnya 30; +18 tes Tier 2).

## Keputusan teknis

1. **Pemilihan model dipisahkan dari pelaporan.** Pemenang ditentukan oleh *repeated stratified
   k-fold* (5 lipatan × 5 ulangan) di atas porsi latih, dilaporkan sebagai rerata ± simpangan baku;
   holdout 80:20 tetap dijalankan dan dilaporkan demi kepatuhan TRD. Alasannya di evaluasi §5.4: pada
   data lokal ≥100 KK, data uji holdout hanya ~20 baris — selang kepercayaan akurasinya ±15 poin
   persen, terlalu lebar untuk memutuskan apa pun.
2. **Urutan fitur dikunci di dalam artefak.** `metadata.json` menyimpan daftar `FITUR`; `infer.py`
   memverifikasinya saat memuat dan menolak artefak yang tidak cocok. Mencegah pergeseran senyap bila
   `build_features()` berubah di kemudian hari.
3. **Versi scikit-learn dicatat & diperiksa.** Artefak joblib rapuh lintas versi; ketidakcocokan
   dicatat sebagai peringatan, bukan kegagalan diam-diam.
4. **Fallback bertanda versi.** Bila artefak tidak ada, skor logistik Fase 0 tetap dipakai dengan
   `versi_model = "stub-logistik-fallback-v0"`. Baris ber-versi fallback **tidak sah untuk klaim
   evaluasi** — pola yang sama dengan `heuristik-fallback-v0` di Tier 1.
5. **Probabilitas ikut diukur mutunya, bukan hanya kelasnya.** Angka `probabilitas` tampil ke petugas
   di dashboard dan menjadi dasar kepercayaan mereka, sedangkan probabilitas Random Forest (rerata
   voting pohon) terkenal tidak terkalibrasi. Brier score + reliability dilaporkan; bila buruk,
   `CalibratedClassifierCV` dipertimbangkan di Fase 6 — bukan sekarang, karena kalibrasi di atas data
   sintetis tidak bermakna.
6. **Ambang 0,5 dipertahankan dulu.** Penyetelan ambang lewat kurva presisi-recall menunggu data lokal;
   distribusi label lokal belum diketahui dan menyetelnya sekarang berarti menyetel terhadap generator.
7. **Ketidakseimbangan kelas ditangani eksplisit.** Varian `class_weight="balanced"` masuk grid
   perbandingan, dan metrik dilaporkan **per kelas** — bukan akurasi tunggal. Data lokal kemungkinan
   besar timpang (mayoritas pengaju dinilai layak).
8. **Saat seri, recall kelas `layak` diutamakan.** False negative berarti warga yang layak ditolak
   sistem; false positive berarti berkas tidak layak yang tetap akan disaring petugas pada verifikasi
   manual. Kedua kekeliruan tidak setara secara sosial, dan kriteria pemilihan model harus mencerminkan
   itu — bukan memakai akurasi sebagai wasit tunggal.
9. **`asal_data` dipakai memfilter, selalu.** Baris `sintetis` tidak boleh tercampur ke perhitungan yang
   dijadikan klaim; kolom ini sudah ada di `data_survei` sejak Fase 0.

## Deliverable / Checklist

- [ ] Commit seluruh pekerjaan Fase 1 & 2 yang belum masuk git (prasyarat — lihat evaluasi §2)
- [x] Rakit fitur: demografi + ekonomi + kondisi rumah + riwayat bantuan + **skor urgensi (Tier 1)** → `ml/tier2/skema_fitur.py`
- [x] Ekspor dataset dari DB dengan penanda `asal_data`; split 80:20 stratified **berkelompok per warga**, kebocoran = 0
- [x] Latih **Random Forest & Gradient Boosting** (OI-01) + varian `class_weight="balanced"`
- [x] Bandingkan lewat CV berulang **dan** holdout; laporkan akurasi, presisi, recall, F1, confusion matrix, rerata ± simpangan baku
- [x] Analisis FP/FN: daftar kasus salah beserta fiturnya, bukan sekadar jumlah
- [x] Permutation importance (bukan impurity importance) — dengan catatan bahwa angka dari data sintetis adalah artefak generator
- [x] Ekspor artefak + `versi_model` ke `ml/artifacts/tier2/`; sesuaikan `settings.ml_model_path`
- [x] Ganti `app/services/tier2_ml.py` dengan inference asli — kontrak `predict_eligibility()` dipertahankan
- [x] `tests/test_tier2.py` + seluruh tes blackbox tetap lulus (**48 lulus**)
- [ ] *(opsional)* Generator sintetis v2 dengan label beraturan non-monoton + derau mandiri — dipakai **menguji perkakas pemilihan model**, bukan menguji model: membuktikan prosedur CV sanggup mendeteksi perbedaan ketika perbedaan itu memang ada
- [ ] Latih ulang & evaluasi final di data **lokal** — **menunggu Fase 1**
- [ ] Tangani bias label (OI-10): jalankan protokol validasi label historis **sebelum** pelatihan final; dokumentasikan tingkat kekeliruan label & sirkularitasnya (evaluasi §5.3)

## Exit criteria

**Untuk menutup Fase 3 (dapat dicapai sekarang):** `predict_eligibility(fitur)` memuat artefak asli,
mengembalikan `hasil + probabilitas + versi_model` yang tersimpan ke `prediksi_ml`; prosedur
perbandingan RF vs GB berjalan dan menghasilkan tabel lengkap dengan ukuran ketidakpastian; analisis
FP/FN terdokumentasi; seluruh tes lulus. → **TERPENUHI** (2026-08-07), lihat [Hasil](#hasil).

**Untuk klaim skripsi (Fase 6):** pemilihan model final, metrik untuk bab hasil, feature importance,
dan angka efektivitas OI-18 — semuanya di atas data lokal yang labelnya sudah divalidasi petugas.

## Alur reproduksi

```powershell
# Probe pra-fase (ulangi bila generator berubah)
python progres/fase-3-tier2-ml/probe_kelayakan_sintetis.py --n 3000

# Jalur penuh yang menghasilkan artefak terpasang saat ini:
python -m data.synthetic.seed 2000 --force
python -m ml.tier2.dataset  --outdir data/corpus --asal-data sintetis
python -m ml.tier2.train    --outdir ml/artifacts/tier2 --asal-data sintetis
python -m ml.tier2.evaluate --model ml/artifacts/tier2 --test data/corpus/tier2_test.csv \
    --outdir progres/fase-3-tier2-ml
```

Ekspor memakai `--skor-urgensi hitung` (bawaan): skor urgensi dihitung sekarang oleh model Tier 1,
tanpa menulis ke basis data. Pakai `--skor-urgensi tersimpan` bila pengajuan sudah pernah dianalisis
lewat `POST /analisis` dan hasil Tier 1 yang tersimpan itu yang ingin dipakai.

## Cara memasang artefak model

1. Jalankan alur reproduksi di atas (artefak tidak di-commit — lihat `.gitignore`).
2. Pastikan `ML_MODEL_PATH=ml/artifacts/tier2` di `.env` **lokal**, bukan hanya di `.env.example`.
3. Verifikasi: `python -c "from app.services.tier2_ml import info_model; print(info_model())"`
   → `fallback_aktif` harus `False` dan `versi_model` harus diawali `tier2-`.

## Catatan & artefak

Taruh di folder ini: tabel perbandingan RF vs GB, confusion matrix, daftar kasus FP/FN beserta
analisisnya, permutation importance, dan catatan pemilihan model. Setiap tabel wajib menyertakan
**asal data** dan **ukuran ketidakpastian** — angka tanpa keduanya tidak dapat dipakai.
