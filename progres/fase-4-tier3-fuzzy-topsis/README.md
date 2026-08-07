# Fase 4 — Tier 3 Matang: Fuzzy TOPSIS (Perangkingan)

**Jalur:** A · **Target:** minggu 7–8 · **Status:** ✅ SELESAI (2026-08-07) — exit criteria terpenuhi; bobot & rentang final menunggu kelurahan (Fase 6)

## Tujuan

Mengganti stub TOPSIS crisp dengan **Fuzzy TOPSIS penuh** (Chen 2000: fuzzifikasi → matriks keputusan
fuzzy → pembobotan → solusi ideal fuzzy → jarak vertex → nilai preferensi → peringkat) untuk
merangking prioritas penerima bantuan (FR-18…FR-21).

Berbeda dari Fase 2 dan Fase 3, **tujuan ini dapat dicapai sepenuhnya sekarang.** Alasannya di
[evaluasi pra-Fase 4](../evaluasi-pra-fase-4.md) §5.5: Tier 3 tidak punya label kebenaran, sehingga
tidak ada metrik yang harus menunggu data bermutu. Yang divalidasi adalah **kebenaran aritmetik** dan
**sifat metode** — keduanya tidak memerlukan data lokal.

## Yang sudah diketahui sebelum menulis kode

[`probe_fuzzy_topsis.py`](probe_fuzzy_topsis.py) dijalankan lebih dulu atas **991 alternatif nyata**
(pengajuan yang diloloskan `tier2-random-forest-sintetis-v1`, skor urgensi dari IndoBERT sungguhan) —
batch OI-15 yang sebenarnya. Keluaran mentah: [`hasil_probe.txt`](hasil_probe.txt). Empat temuan
mengubah rancangan fase ini:

**1. `skor_urgensi` tersaturasi — 5 nilai berbeda, 100% menempel di ujung rentang.** 105 alternatif di
0,0002; 886 di ≥0,9939; tidak ada di antaranya. Kriteria berbobot 0,25 ini bekerja sebagai saklar
biner, bukan derajat kemendesakan. Penyebabnya korpus Fase 2 yang terpisah sempurna → margin logit
lebar (−8,6…+8,7) → softmax jenuh. Informasi urutannya masih ada di logit; hilangnya di sigmoid.

**2. Kuantisasi linguistik polos menghancurkan perangkingan.** Bentuk yang paling lazim ditulis di
skripsi Fuzzy TOPSIS memeras 991 alternatif menjadi 81 nilai preferensi, dan menyeret **25 dari 50
kursi kuota ke posisi seri.** Setengah daftar penerima akan ditentukan urutan baris di basis data.

**3. Fuzzifikasi berbasis derajat keanggotaan penuh tidak punya masalah itu** — 550 nilai berbeda
(paling halus dari seluruh varian), **nol seri di garis kuota**, dengan fungsi keanggotaan segitiga
yang sama persis. Kefuzzian tidak perlu dibayar dengan daya beda.

**4. 42% selisih "fuzzy vs crisp" ternyata bukan berasal dari kefuzzian.** Kontrol dengan bilangan
fuzzy berlebar nol (l=m=u) sudah menggeser 42% daftar top-50 — itu efek rumusan TOPSIS Chen (solusi
ideal mutlak) yang berbeda dari stub Fase 0 (maksimum teramati), bukan efek fuzzy.

| Varian fuzzifikasi | nilai unik | seri terbesar | **seri di garis kuota** | ρ vs crisp | top-50 sama |
|---|---|---|---|---|---|
| degenerat *(kontrol, lebar 0)* | 456 | 37 | 1 | 0,7724 | 58,0% |
| linguistik *(kuantisasi polos)* | 81 | 72 | **25** | 0,9160 | 54,0% |
| **keanggotaan *(dipilih)*** | **550** | **18** | **1** | 0,8635 | 54,0% |
| langsung *(lebar tetap)* | 470 | 34 | 1 | 0,7888 | 58,0% |
| hibrida *(lebar adaptif)* | 453 | 37 | 5 | 0,7768 | 62,0% |
| *(crisp — stub Fase 0)* | 859 | 14 | 14 | 1,0000 | 100% |

Dan satu kabar baik: **bobot provisional bukan risiko dominan.** Perturbasi ±20% hanya menggeser
3–7% kursi; varian fuzzy lebih stabil daripada crisp (97–98% bertahan vs 93%), dan peringkat-1 crisp
berpindah pada 32% perturbasi ±50% sementara varian fuzzy tidak pernah. Ini **argumen substantif
pertama untuk memakai fuzzy sama sekali**: lebar bilangan fuzzy menyerap ketidakpastian bobot.

## Keputusan rancangan (terkunci sebelum implementasi)

1. **Fuzzifikasi memakai derajat keanggotaan penuh.** Nilai crisp tidak dipaksa masuk satu himpunan;
   derajat keanggotaannya terhadap seluruh himpunan (segitiga bertetangga, saling tumpang tindih)
   dihitung, lalu TFN hasil = rerata berbobot keanggotaan atas TFN wakil tiap himpunan. Varian
   "petakan ke satu himpunan" **ditolak** — ia sudah men-defuzzifikasi diam-diam di langkah pertama
   dan menyeret 25 seri ke garis kuota (evaluasi §5.2).
2. **Rumusan Chen (2000) dipakai utuh** — normalisasi linier, FPIS/FNIS mutlak, jarak vertex — dan
   **kontrol `degenerat` (TFN berlebar nol) wajib ikut dilaporkan.** Tanpa itu, selisih terhadap
   TOPSIS crisp akan salah diatribusikan ke fuzzifikasi (evaluasi §5.3).
3. **Urutkan pada presisi penuh; bulatkan hanya untuk tampilan.** Stub Fase 0 membulatkan ke 4 desimal
   *sebelum* mengurutkan (`tier3_topsis.py:65`) sehingga memproduksi seri sendiri: grup seri terbesar
   14 padahal kembar sejati terbesar 10.
4. **Aturan tiebreak eksplisit, deterministik, tercatat.** 6,1% alternatif punya vektor kriteria
   persis kembar — seri sejati yang tidak dapat dihapus metode apa pun. Urutan tiebreak yang
   diusulkan: skor urgensi lebih tinggi → pendapatan lebih rendah → `pengajuan_id` lebih kecil (agar
   reproducible). Disimpan ke `metadata` batch, bukan tersembunyi di kode.
5. **Fungsi keanggotaan didefinisikan di `config/fuzzy_config.yaml`, bukan di kode** (FR-19, NFR-06,
   OI-13). Rentang provisional; nilai final dari kelurahan di Fase 6. Versi konfigurasi ikut
   di-snapshot per batch bersama bobot.
6. **Validasi lewat perhitungan manual, bukan metrik akurasi.** Tier 3 tidak punya label kebenaran
   (evaluasi §5.5). Contoh 4–5 alternatif dihitung tangan dan dicocokkan sampai digit terakhir sebagai
   tes — inilah pengganti "akurasi" bagi Tier 3.
7. **Analisis sensitivitas bobot adalah deliverable, bukan lampiran.** Ia satu-satunya klaim Tier 3
   yang sah dilaporkan dari data sintetis, karena yang diukur sifat metode terhadap perturbasi, bukan
   ketepatan terhadap kebenaran.
8. **Kontrak `rank_topsis()` dipertahankan.** Pola yang sudah dua kali terbayar di Tier 1 & Tier 2.
9. **Fallback bertanda versi.** Bila konfigurasi fuzzy tidak sah/tidak lengkap, sistem tetap jalan
   dengan TOPSIS crisp bertanda `topsis-crisp-fallback-v0` di `bobot_snapshot`, agar hasil non-fuzzy
   tidak pernah tercampur ke analisis — meniru `heuristik-fallback-v0` (Tier 1) dan
   `stub-logistik-fallback-v0` (Tier 2).

## Keputusan yang menunggu: perlakuan `skor_urgensi`

Kriteria berbobot 0,25 ini saat ini hanya punya 5 nilai berbeda (evaluasi §5.1). Tiga pilihan:

| Opsi | Isi | Konsekuensi |
|---|---|---|
| **A (rekomendasi)** | Pakai **margin logit** Tier 1 sebagai nilai crisp kriteria urgensi, dinormalisasi lewat fungsi keanggotaan | Resolusi penuh kembali (−8,6…+8,7); butuh `score_urgency()` mengekspos margin (perubahan kecil, kontrak tidak rusak); menambah satu paragraf metodologi |
| B | Pertahankan probabilitas, turunkan bobot urgensi | Tidak menyentuh Tier 1, tetapi bobot jadi tambalan teknis yang mencemari OI-12 |
| C | Biarkan, tulis sebagai keterbatasan | Paling murah; kriteria berbobot 0,25 bekerja sebagai saklar biner tanpa terlihat di bab hasil |

Saturasinya sendiri **artefak korpus sintetis** — pada teks lokal efeknya kemungkinan mengecil.
Jalur logit tetap benar dan tidak merugikan bila saturasi hilang. **Butuh persetujuan sebelum
implementasi dimulai.**

## Yang akan dibangun

| Berkas | Isi |
|---|---|
| `ml/tier3/__init__.py` | Konstanta versi metode & fallback, tipe `TFN`, batas klaim tier |
| `ml/tier3/keanggotaan.py` | Fungsi keanggotaan segitiga/trapesium per kriteria + fuzzifikasi derajat penuh; **satu sumber** untuk fuzzifikasi *dan* label penjelasan (anti-skew, meniru `skema_fitur.py`) |
| `ml/tier3/fuzzy_topsis.py` | Chen (2000) lengkap: arah → normalisasi → bobot → FPIS/FNIS → jarak vertex → nilai preferensi; mode `degenerat` untuk kontrol; perakitan peringkat + tiebreak |
| `ml/tier3/crisp.py` | TOPSIS crisp Fase 0 — jalur cadangan **dan** pembanding atribusi; pembulatan sebelum pengurutan dihapus |
| `ml/tier3/sensitivitas.py` | Perturbasi bobot, churn top-K, atribusi crisp/degenerat/fuzzy, statistik seri — perkakas yang menghasilkan tabel deliverable |
| `config/fuzzy_config.yaml` | + blok `keanggotaan:` (bentuk & rentang per kriteria, OI-13) + `tiebreak:` + `versi` |
| `app/services/tier3_topsis.py` | Pembungkus tipis + `info_fuzzy()`; **kontrak `rank_topsis()` dipertahankan** |
| `app/services/pipeline.py` | Snapshot konfigurasi lengkap ke batch (bobot, arah, versi konfigurasi, versi metode, tiebreak) |
| `app/services/fuzzy_config.py` | Kunci `keanggotaan`/`tiebreak` + `reset_fuzzy_config()` |
| `app/schemas/hasil.py` | `versi_metode` & `versi_konfigurasi` pada `RankingResult` |
| `ml/tier1/infer.py`, `app/services/tier1_nlp.py` | Margin logit diekspos; **pembulatan probabilitas di sumber dihapus** |
| `tests/test_tier3.py` | 34 tes: perhitungan manual, monotonisitas, seri & tiebreak, presisi penuh, skala logit, fallback bertanda, validasi konfigurasi, kesetaraan dengan scikit-fuzzy |

## Hasil

Seluruh angka di bawah berasal dari **implementasi yang terpasang** (`ml/tier3/`, kode yang sama
yang melayani `POST /analisis/ranking`) atas **991 alternatif** batch OI-15 — pengajuan yang
diloloskan `tier2-random-forest-sintetis-v1`. Reproduksi:
[`hasil_fase4.py`](hasil_fase4.py) → [`hasil_fase4.txt`](hasil_fase4.txt).

**Tidak satu pun tabel di bawah berupa akurasi**, dan itu disengaja: Tier 3 tidak punya label
kebenaran (evaluasi §5.5).

### Efek samping yang menentukan: resolusi urgensi pulih

Keputusan memakai margin logit dijalankan dengan menghapus pembulatan 4 desimal di sumber Tier 1
(`ml/tier1/infer.py`). Dampaknya jauh lebih besar dari perkiraan:

| | skor_urgensi (2.020 narasi) | margin logit |
|---|---|---|
| Sebelum (dibulatkan 4 desimal) | **5** nilai berbeda | — |
| Sesudah (presisi penuh) | **65** nilai berbeda | −8,688 … +8,851 |

Kriteria berbobot 0,25 yang tadinya saklar biner kembali menjadi kriteria sungguhan. Seluruh tabel
berikut memakai korpus yang sudah diekspor ulang; angka probe pra-fase **tidak sebanding** dengannya
karena probe berjalan di atas korpus lama yang terbulat.

### Tabel 1 — daya beda & seri (kuota top-50 dari 991)

| Metode | Nilai preferensi unik | Grup seri terbesar | Seri di garis kuota |
|---|---|---|---|
| **Fuzzy TOPSIS (terpasang)** | **972** | **3** | **1** |
| TOPSIS crisp (cadangan) | 972 | 3 | 1 |

Bandingkan dengan varian kuantisasi linguistik yang ditolak di muka: 81 nilai unik, grup seri 72,
dan **25 seri di garis kuota**. Rancangan yang dipilih menghapus persoalan itu sepenuhnya — hanya
**1** alternatif berada di garis potong, dan itu pun karena kembar sejati.

Alternatif dengan vektor kriteria persis kembar turun dari 6,1% (probe) ke **3,6%**, sekali lagi
karena urgensi kembali membedakan. Seri sisa tidak dapat dihapus metode apa pun; ia ditangani
aturan tiebreak yang tercatat di konfigurasi: `skor_urgensi → pendapatan → jumlah_tanggungan →
pengajuan_id`.

### Tabel 2 — atribusi: berapa bagian "efek fuzzy" yang sebenarnya bukan fuzzy

| Perbandingan | ρ | top-50 sama | Yang diukur |
|---|---|---|---|
| crisp → **degenerat** *(TFN lebar nol)* | 0,9546 | **88,0%** | Rumusan Chen: normalisasi linier + solusi ideal mutlak |
| degenerat → fuzzy | 0,9973 | 90,0% | Kefuzzian yang sesungguhnya |
| crisp → fuzzy *(selisih total)* | 0,9627 | 82,0% | Gabungan keduanya |

Dari 18 poin persen pergantian daftar penerima, **12 pp terjadi tanpa satu pun bilangan fuzzy yang
punya lebar**. Klaim yang sah berbunyi: *rumusan Fuzzy TOPSIS Chen (2000) menghasilkan perangkingan
berbeda dari TOPSIS crisp, dan sebagian besar perbedaan itu berasal dari definisi solusi idealnya,
bukan dari fuzzifikasi.* Baris `degenerat` wajib ikut ke bab hasil.

### Tabel 3 — sensitivitas bobot (200 perturbasi per baris, OI-12 belum tuntas)

| Goyang bobot | top-50 bertahan | Churn | Peringkat-1 berubah |
|---|---|---|---|
| ±10% | 99,1% | 0,9% | 0,0% |
| ±20% | 98,0% | 2,0% | 0,0% |
| ±50% | 92,7% | 7,3% | **0,0%** |

**Ini satu-satunya klaim Tier 3 yang sah dilaporkan dari data sintetis**, karena yang diukur sifat
metode terhadap perturbasi — bukan ketepatan terhadap suatu kebenaran. Bacaannya: daftar penerima
tidak ditentukan oleh bobot provisional. Bahkan pada goyangan ±50%, 92,7% penerima bertahan dan
peringkat teratas tidak pernah berpindah. Menunggu OI-12 tidak memblokir apa pun; yang belum boleh
diklaim hanyalah nilai preferensi sebagai angka pasti.

### Verifikasi end-to-end

300 pengajuan dianalisis ulang lewat `POST /analisis`, lalu dirangking:

- `versi_metode` = `fuzzy-topsis-chen2000-v1`, `versi_konfigurasi` = `provisional-1`,
  `fallback_aktif` = `False`, pustaka keanggotaan = **scikit-fuzzy**;
- 145 dari 300 lolos Tier 2 dan masuk batch (OI-15 utuh);
- `bobot_snapshot` menyimpan bobot, arah, versi konfigurasi, versi metode, dan aturan tiebreak;
- **82 tes lulus** (sebelumnya 48; +34 tes Tier 3).

### Kontaminasi yang tersingkap saat verifikasi

Perangkingan pertama menghasilkan skor urgensi 0,625 dan 0,75 — pola yang mustahil bagi IndoBERT.
Penelusurannya: kelima baris `skor_urgensi` di basis data bertanda **`stub-indobert-v0`**, yaitu
stub Fase 0, dan tidak pernah diperbarui setelah artefak Tier 1 terpasang. Perangkingan Fuzzy TOPSIS
yang sepenuhnya benar sedang bekerja di atas masukan stub.

Ini kejadian ketiga dari jenis kegagalan yang sama (setelah dua kali `.env` menimpa `.env.example`),
dan ketiganya **hanya tersingkap oleh penanda versi**, bukan oleh tes — tes kontrak memeriksa bentuk
keluaran, dan bentuknya selalu benar. Baris-baris itu sudah dianalisis ulang; kini seluruh 300 baris
bertanda `indobert-p1-augmentasi-v3`.

## Deliverable / Checklist

- [x] Probe pra-fase: apakah tujuan Fase 4 tercapai di data yang ada → [`hasil_probe.txt`](hasil_probe.txt)
- [x] Uji lima varian fuzzifikasi; pilih berdasarkan bukti, bukan konvensi → varian **keanggotaan**
- [x] Kontrol atribusi (TFN lebar nol) memisahkan efek mesin TOPSIS dari efek kefuzzian
- [x] Putuskan perlakuan `skor_urgensi` → **opsi A (margin logit)**, disetujui 2026-08-07
- [x] Definisikan fungsi keanggotaan per kriteria (bentuk & rentang) di `config/fuzzy_config.yaml` (OI-13)
- [x] Implementasi Fuzzy TOPSIS Chen (2000) (FR-18…FR-21) di `ml/tier3/`
- [x] Aturan tiebreak deterministik + pengurutan presisi penuh
- [x] Ganti `app/services/tier3_topsis.py` — kontrak `rank_topsis()` dipertahankan
- [x] Alur OI-15 tetap: batch = pengajuan dengan `prediksi_ml = layak` saja (145 dari 300, utuh)
- [x] Snapshot bobot **dan** versi konfigurasi keanggotaan per batch
- [x] **Contoh perhitungan manual** 3 alternatif simetris → CC = 0,75 / 0,50 / 0,25, cocok sampai digit terakhir
- [x] **Analisis sensitivitas bobot** (±10/20/50%) + tabel atribusi → [`hasil_fase4.txt`](hasil_fase4.txt)
- [x] `tests/test_tier3.py` + seluruh tes lama tetap lulus (**82 lulus**, sebelumnya 48)
- [ ] Formalisasi bobot & rentang keanggotaan dengan kelurahan (OI-12/OI-13) — **menunggu Fase 6**
- [ ] *(warisan)* `ml/tier1/infer.py` — `info()` masih melaporkan `fallback_aktif: false` sebelum pemuatan pertama; rapikan saat Tier 1 disentuh lagi

## Exit criteria

**Untuk menutup Fase 4 (dapat dicapai sekarang, tanpa data lokal):** `rank_topsis()` memakai Fuzzy
TOPSIS asli; hasil cocok dengan perhitungan manual sampai digit terakhir; `ranking_topsis` menyimpan
nilai preferensi + peringkat + snapshot bobot & versi keanggotaan; tiebreak deterministik dan tercatat;
tabel sensitivitas bobot & atribusi tersedia; pipeline 3-tier nyata end-to-end; seluruh tes lulus.
→ **TERPENUHI** (2026-08-07), lihat [Hasil](#hasil). Untuk pertama kalinya sejak Fase 0, sebuah fase
Jalur A ditutup tanpa menuliskan "menunggu data lokal" di kolom hasilnya.

**Untuk klaim skripsi (Fase 6):** bobot & fungsi keanggotaan yang disepakati kelurahan, dan
kesesuaian perangkingan dengan penilaian petugas.

## Alur reproduksi

```powershell
# 1) Ekspor ulang korpus — WAJIB setelah pembulatan Tier 1 dihapus, agar skor urgensi
#    tersimpan presisi penuh (tanpa ini kriteria urgensi hanya punya 5 nilai berbeda).
python -m ml.tier2.dataset --outdir data/corpus --asal-data sintetis

# 2) Tabel deliverable Fase 4 (daya beda & seri, atribusi, sensitivitas bobot)
python progres/fase-4-tier3-fuzzy-topsis/hasil_fase4.py

# 3) Verifikasi konfigurasi terpasang
python -c "from app.services.tier3_topsis import info_fuzzy; print(info_fuzzy())"

# Probe pra-fase (arsip keputusan rancangan; ulangi bila kriteria/bobot berubah)
python progres/fase-4-tier3-fuzzy-topsis/probe_fuzzy_topsis.py
python progres/fase-4-tier3-fuzzy-topsis/probe_fuzzy_topsis.py --goyang 0.5
```

Keduanya memakai `data/corpus/tier2_*.csv` dan menyaringnya lewat Tier 2 sungguhan; keduanya
mencetak peringatan bila Tier 2 sedang memakai fallback, karena batch dari fallback tidak sah.

**Cara memverifikasi pemasangan** (`info_fuzzy()`): `fallback_aktif` harus `False`, `versi_metode`
harus `fuzzy-topsis-chen2000-v1`, dan `skala.skor_urgensi` harus `logit`. Bila `versi_metode`
bertuliskan `topsis-crisp-fallback-v0`, konfigurasi keanggotaan tidak terbaca dan sistem sedang
merangking **tanpa logika fuzzy** — seluruh tes akan tetap hijau, persis seperti tiga kegagalan
senyap sebelumnya.

## Catatan & artefak

Taruh di folder ini: definisi fungsi keanggotaan (grafik/rentang), contoh perhitungan manual,
tabel sensitivitas bobot, dan tabel atribusi crisp/degenerat/fuzzy. Setiap tabel wajib menyertakan
**asal data** dan **ukuran ketidakpastian**. Untuk Tier 3, tambahkan satu kolom lagi yang tidak
berlaku di tier lain: **apakah angka itu sifat metode atau klaim tentang kelayakan** — hanya yang
pertama yang sah dilaporkan dari data sintetis.
