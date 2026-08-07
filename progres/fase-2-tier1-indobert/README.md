# Fase 2 — Tier 1 Matang: IndoBERT (Skor Urgensi)

**Jalur:** A · **Target:** minggu 3–4 · **Status:** 🔶 Kode & pipeline SELESAI, menunggu data lokal berlabel

## Tujuan
Mengganti stub Tier 1 dengan inference IndoBERT hasil fine-tuning untuk menghasilkan skor urgensi
(probabilitas kelas 'tinggi', 0–1) dari teks naratif.

## Deliverable / Checklist
- [x] Preprocessing (FR-11): pembersihan, lowercasing, tokenizer IndoBERT; utilitas NLTK/Sastrawi seperlunya
- [x] **Fine-tuning di Colab GPU** (OI-20): base `indobert-base-p1`, klasifikasi biner tinggi/rendah, split 80:20
      → notebook `finetune_indobert_colab.ipynb`; skrip `ml/tier1/train.py` (dipakai identik lokal & Colab)
- [x] Latih dulu di teks publik/augmentasi (validasi pipeline) — **selesai**
- [ ] Fine-tune final di teks **lokal** berlabel — **menunggu Fase 1** (pelabelan berjalan)
- [x] Evaluasi **Akurasi + F1** pada data uji; dokumentasikan per versi & asal data
- [x] Ekspor artefak + `versi_model`; unduh ke `ml/artifacts/`; set `INDOBERT_MODEL_PATH`
- [x] Ganti `app/services/tier1_nlp.py` (score_urgency) dengan inference asli — kontrak fungsi dipertahankan
- [x] Pasang `requirements-ml.txt` (torch/transformers) di venv

## Exit criteria
`score_urgency(teks)` memuat model asli, mengeluarkan probabilitas 0–1 yang tersimpan ke `skor_urgensi`;
metrik Akurasi+F1 terdokumentasi; pipeline tetap lulus tes blackbox. → **Terpenuhi untuk versi
augmentasi.** Klaim final skripsi menunggu versi `lokal` (Fase 6).

---

## Yang dibangun

| Berkas | Isi |
|---|---|
| `ml/tier1/preprocessing.py` | FR-11 — pembersihan teks, dipakai **identik** saat latih & inference (anti train/serve skew) |
| `ml/tier1/corpus.py` | Pembangkit korpus naratif berlabel (augmentasi) — data latih sementara |
| `ml/tier1/dataset.py` | Split latih:uji 80:20 stratified, anti-kebocoran; `Dataset` PyTorch |
| `ml/tier1/train.py` | Fine-tuning `indobert-base-p1` (loop PyTorch biasa, tanpa `Trainer`) |
| `ml/tier1/evaluate.py` | Akurasi, F1, precision/recall, confusion matrix, ROC-AUC, rincian per kategori |
| `ml/tier1/infer.py` | `UrgencyScorer` — pemuatan malas, thread-safe, batch, fallback heuristik |
| `app/services/tier1_nlp.py` | Pembungkus tipis; **kontrak `score_urgency()` dipertahankan** + `score_urgency_batch()` |
| `finetune_indobert_colab.ipynb` | Notebook Colab GPU (OI-20) — memanggil modul repo, bukan menyalin kode |
| `tests/test_tier1.py` | 17 tes: preprocessing, korpus, split, kontrak inference, fallback, model asli |

### Alur reproduksi
```powershell
python -m ml.tier1.corpus  --n 3200 --seed 42 --out data/corpus/tier1_urgensi.csv
python -m ml.tier1.dataset --input data/corpus/tier1_urgensi.csv --outdir data/corpus
python -m ml.tier1.train   --epochs 3 --batch-size 16 --lr 2e-5 --asal-data augmentasi
python -m ml.tier1.evaluate --model ml/artifacts/indobert --test data/corpus/tier1_test.csv
```

## Data latih sementara (augmentasi)

Teks lokal Bontoramba berlabel belum tersedia (Fase 1 masih berjalan), sehingga pipeline divalidasi
dengan korpus **augmentasi** — teks naratif Bahasa Indonesia bergaya laporan petugas, dirakit dari bank
klausa dengan variasi pembuka/penghubung/penutup dan tiga gaya penulisan (formal, semi-formal,
informal bersingkatan + typo).

Agar model tidak sekadar mencocokkan kata kunci, korpus memuat ±32% **kasus sulit**:

| Jenis | Contoh | Label |
|---|---|---|
| *Hard negative* | "tidak ada anggota keluarga yang menderita sakit kronis maupun disabilitas" | rendah |
| *Hard negative* | "atap rumah pernah bocor namun sudah diperbaiki secara swadaya" | rendah |
| *Hard positive* | "penghasilan harian tidak cukup untuk makan tiga kali sehari" | tinggi |
| *Hard positive* | "biaya sekolah anak sudah tiga bulan menunggak dan belum terbayar" | tinggi |

Statistik: **2.606 sampel unik** (tinggi 1.448 / rendah 1.158), rata-rata 23,6 kata.
Split 80:20 → latih 2.091, uji 515, **kebocoran teks uji ke latih = 0** (dedup berbasis hash teks
bersih tanpa tanda baca, sehingga varian singkatan/typo dari kalimat yang sama tidak terpecah antar split).

> ⚠️ **Batas klaim.** Metrik atas korpus augmentasi **hanya memvalidasi pipeline**, bukan bukti
> kinerja pada narasi warga nyata (distribusi bahasanya lebih beragam dan berlabel manusia).
> Angka untuk skripsi diambil dari versi `lokal` pada Fase 6.

## Hasil pelatihan

**Artefak terpasang: `indobert-p1-augmentasi-v3`** — 2 epoch, CPU, 2026-08-07.
Ketiga versi menghasilkan metrik data uji yang identik; rincian per versi di bagian riwayat di bawah.

| Metrik (data uji v3, n=557) | Nilai |
|---|---|
| Akurasi | **1,0000** |
| F1 (kelas `tinggi`) | **1,0000** |
| Precision / Recall | 1,0000 / 1,0000 |
| ROC-AUC | 1,0000 |
| Confusion matrix | TN 252 · FP 0 · FN 0 · TP 305 |

| Epoch | Loss latih | Loss uji | Akurasi | F1 |
|---|---|---|---|---|
| 1 | 0,1405 | 0,0004 | 1,0000 | 1,0000 |
| 2 | 0,0004 | 0,0003 | 1,0000 | 1,0000 |

Angka v1 sebagai pembanding: n=515, loss latih epoch 1 = 0,1215 → epoch 2 = 0,0002, metrik sama-sama
1,0000. Perbedaan korpus antar versi tidak menggeser metrik ini sedikit pun — alasannya di bawah.

### Membaca angka ini dengan benar

> **Akurasi sempurna di sini adalah temuan negatif, bukan prestasi.** Model menyelesaikan tugas tanpa
> satu pun kesalahan **sejak epoch pertama**, dan loss uji (0,0002) turun jauh di bawah loss latih —
> tanda klasik bahwa data uji tidak menuntut generalisasi apa pun.

Penyebabnya ada pada data, bukan pada model: korpus dirakit dari bank klausa terbatas, sehingga
kalimat uji adalah **kombinasi ulang dari potongan yang pola sintaksisnya sudah dilihat saat latih**.
Split anti-kebocoran menjamin tidak ada *kalimat* yang sama di kedua sisi, tetapi tidak bisa —
dan memang tidak dimaksudkan untuk — mencegah kesamaan *pola*.

Konsekuensi praktis:

1. **Angka ini tidak boleh masuk bab hasil skripsi sebagai kinerja Tier 1.** Yang dibuktikan hanyalah
   rantai preprocess → latih → simpan artefak → inference berjalan utuh dan menghasilkan probabilitas
   yang benar arahnya. Itu memang tujuan run ini.
2. **Data uji augmentasi kini tidak punya daya diagnostik lagi.** Tidak ada kasus salah yang bisa
   dianalisis, sehingga menambah epoch, menyetel hyperparameter, atau membandingkan varian model di
   atas korpus ini tidak akan memberi informasi apa pun. Berhenti mengoptimalkan di sini.
3. **Uji jujur berikutnya harus datang dari kalimat tulisan manusia** — mulai dari contoh terkalibrasi
   di rubrik pelabelan (Fase 1), lalu teks lokal berlabel (Fase 6). Baru di sanalah metrik Tier 1
   bermakna sebagai klaim.

### Uji silang terhadap kalimat tulisan manusia

Dugaan di atas langsung terkonfirmasi. Ke-24 contoh terkalibrasi rubrik pelabelan
(`progres/fase-1-data-pelabelan/rubrik-pelabelan-urgensi.md` Bagian 6) ditulis manusia dengan gaya
catatan petugas dan sengaja menyimpang dari pola bank klausa. Dijalankan lewat
`progres/fase-1-data-pelabelan/uji_silang_rubrik.py`:

| Data uji | Hasil |
|---|---|
| Template augmentasi (n=515) | 100,0% |
| **Kalimat tulisan manusia (n=24)** | **87,5% (21/24)** |

Tiga kesalahan, dan ketiganya jatuh tepat pada penalaran yang kurang terwakili di korpus:

| # | Teks | Rubrik | Model | Celah |
|---|---|---|---|---|
| 6 | "Nenek tinggal sendiri, jalan pakai tongkat, tetangga yang bantu masak" | TINGGI | RENDAH (0,13) | Ketidakmampuan mengurus diri disampaikan **tersirat**; korpus hanya memuat bentuk eksplisit ("lansia jompo", "tanpa pendamping") |
| 15 | "Atap dapur sempat bocor tahun lalu, sudah ditambal sendiri" | RENDAH | TINGGI (0,93) | Aturan "sudah teratasi" (R3) tidak bertahan pada susunan kalimat di luar template hard negative |
| 21 | "Anaknya berhenti sekolah karena tidak mau lagi" | RENDAH | TINGGI (1,00) | Korpus **tidak pernah** mengajarkan pengecualian: putus sekolah yang bukan karena biaya |

Selisih 100% → 87,5% inilah ukuran sesungguhnya dari jarak antara korpus buatan dan bahasa lapangan —
dan angka 87,5% pun masih optimistis, karena 24 kalimat terlalu sedikit untuk menyimpulkan apa pun.

### Riwayat perbaikan v1 → v3, dan mengapa berhenti di sini

Ketiga celah ditambal di `ml/tier1/corpus.py` lalu model dilatih ulang dua kali. Hasilnya:

| Versi | Uji template | **Uji kalimat manusia** | Yang berubah | Kegagalan tersisa |
|---|---|---|---|---|
| v1 | 100% (n=515) | 87,5% (21/24) | korpus awal | #6 tersirat · #15 teratasi · #21 putus sekolah |
| v2 | 100% (n=534) | 95,8% (23/24) | +`URGEN_TERSIRAT`, +`FRAME_TERATASI`, +klausa putus-sekolah-bukan-biaya | **#10 (regresi — v1 benar)** |
| v3 | 100% (n=557) | 95,8% (23/24) | +`FRAME_BERLANJUT`, +`URGEN_TUNGGAKAN` | **#13 (regresi — v1 & v2 benar)** |

Perhatikan kolom kedua: **100% di ketiga versi**, sementara kolom ketiga bergerak. Seluruh informasi
diagnostik datang dari 24 kalimat tulisan manusia; data uji template tidak mengukur apa pun.

Yang lebih penting: **kegagalan berpindah, bukan berkurang.**

- v2 menutup tiga celah v1, tetapi menciptakan jalan pintas dangkal — susunan "sudah … sekarang …"
  dianggap selalu berarti masalah sudah selesai, sehingga *"sudah tiga bulan menunggak listrik,
  sekarang menyambung dari rumah tetangga"* (#10) jatuh ke RENDAH padahal v1 sudah benar.
- v3 menutup jalan pintas itu (#10 kembali benar, p=0,9997), tetapi *"Kepala keluarga penderita
  diabetes."* (#13) naik ke TINGGI (p=0,97) padahal v1 (p=0,0016) dan v2 (p=0,32) benar.

**Ini bukan bug yang bisa ditambal lagi — ini ketegangan nyata antara dua aturan rubrik.** Contoh #6
("nenek jalan pakai tongkat, tetangga yang bantu masak") menuntut ketidakberdayaan **tersirat**
dihitung TINGGI. Contoh #13 menuntut sebutan penyakit **tanpa keterangan dampak** dihitung RENDAH
(aturan R5). Mengajari model yang pertama melemahkan yang kedua. Manusia pun membedakannya lewat
prinsip yang belum ditulis tegas di rubrik.

**Keputusan: berhenti menyetel korpus terhadap 24 kalimat ini.** Tiga iterasi sudah cukup untuk
menyimpulkan bahwa peningkatan berikutnya akan menjadi pengepasan terhadap set uji sendiri, dan
angkanya berhenti jujur. Tindak lanjut yang benar bukan latih ulang keempat, melainkan:

1. **Amandemen rubrik (Bagian 10)** — pertajam batas antara #6 dan #13: yang dihitung adalah
   **keterbatasan fungsi atau kebutuhan yang tidak terpenuhi**, bukan sebutan diagnosis atau status
   semata. Ini memperbaiki konsistensi pelabel manusia, yang justru tujuan sesungguhnya.
2. **Perbesar set uji jujur** dari 24 menjadi ≥70 kalimat tulisan manusia sebelum menyentuh model lagi.
3. **Fine-tune versi `lokal`** (Fase 6) — di sanalah metrik Tier 1 baru bermakna sebagai klaim.

Untuk skripsi, laporkan tabel v1→v3 di atas sebagai **riwayat perbaikan terdokumentasi beserta
batasnya**, bukan v3 saja sebagai capaian. Riwayat ini justru memperlihatkan pemahaman atas
keterbatasan data augmentasi — yang lebih kuat daripada satu angka tanpa konteks.

## Hyperparameter

| Parameter | Nilai | Catatan |
|---|---|---|
| base model | `indobenchmark/indobert-base-p1` | uncased, 124M parameter |
| epochs | 3 | dataset kecil — lebih dari itu cepat overfit |
| batch size | 16 | |
| learning rate | 2e-5 | linear decay, warmup 10% |
| weight decay | 0.01 | |
| max length | 128 token | narasi terpanjang korpus 60 kata |
| grad clipping | 1.0 | |
| seed | 42 | seluruh jalur (korpus, split, latih) deterministik |
| fp16 | aktif di Colab GPU, mati di CPU | |

## Keputusan teknis

1. **Loop PyTorch biasa, bukan `Trainer`.** Menghindari dependensi `accelerate` dan memastikan kode
   yang jalan di CPU lokal identik dengan yang jalan di Colab GPU.
2. **Preprocessing satu sumber.** `ml/tier1/preprocessing.py` diimpor oleh jalur latih *dan* jalur
   inference; `app/services/tier1_nlp.py` hanya me-re-ekspor. Tidak mungkin terjadi train/serve skew.
3. **Stemming/stopword TIDAK dipakai di jalur BERT.** Subword tokenizer IndoBERT memerlukan kata utuh,
   dan stopword membawa negasi ("tidak ada yang sakit") yang justru menentukan label. Sastrawi tetap
   disediakan di `stem_tokens()` untuk baseline/analisis non-BERT.
4. **Fallback heuristik + penanda versi.** Bila artefak tidak ada (repo baru di-clone — artefak tidak
   di-commit), sistem tetap jalan dengan heuristik kata kunci dan menulis `versi_model =
   'heuristik-fallback-v0'` ke kolom `skor_urgensi.versi_model`, sehingga hasil non-model selalu bisa
   dipisahkan saat analisis. **Baris ber-versi fallback tidak boleh dipakai untuk klaim evaluasi.**
5. **Skoring batch.** `pipeline.py` kini memanggil `score_urgency_batch()` — seluruh narasi satu
   pengajuan diskor dalam satu forward pass (mendukung NFR-01 ≤5 detik).
6. **Pemuatan malas & thread-safe.** Model dimuat sekali pada permintaan pertama (singleton dengan
   lock), bukan saat impor — startup aplikasi tetap ringan dan tes tanpa artefak tetap jalan.

## Cara memasang artefak model

1. Jalankan notebook Colab → unduh `indobert-p1-<asal_data>-v1.zip`.
2. Ekstrak isinya ke `ml/artifacts/indobert/` (harus berisi `config.json`, `model.safetensors`,
   `tokenizer.json`, `metadata.json`, `metrics.json`).
3. Opsional: set `INDOBERT_MODEL_PATH` di `.env` bila menaruh artefak di lokasi lain.
4. Verifikasi: `python -c "from app.services.tier1_nlp import info_model; print(info_model())"`
   → `fallback_aktif` harus `False`.

## Langkah berikutnya (Fase 6)

- Fine-tune ulang dengan `--asal-data lokal --versi-model indobert-p1-lokal-v1` setelah teks
  Bontoramba berlabel siap (≥100 KK, rubrik + Cohen's kappa dari Fase 1).
- Evaluasi silang: model versi `augmentasi` diuji pada data uji **lokal** → memperlihatkan seberapa
  jauh korpus buatan mewakili narasi nyata. Laporkan kedua angka di skripsi.
- Tinjau ulang ambang 0,5: bila distribusi label lokal timpang, kalibrasi ambang dengan kurva
  precision-recall pada data validasi.

## Catatan & artefak
Taruh di folder ini: notebook Colab fine-tuning, kurva pelatihan, tabel metrik (akurasi/F1), catatan
hyperparameter, dan tautan artefak model.
