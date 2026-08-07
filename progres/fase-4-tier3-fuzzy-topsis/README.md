# Fase 4 — Tier 3 Matang: Fuzzy TOPSIS (Perangkingan)

**Jalur:** A · **Target:** minggu 7–8 · **Status:** 🔶 Siap dimulai — probe pra-fase selesai, rancangan terkunci

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
| `ml/tier3/__init__.py` | Konstanta versi, nama himpunan linguistik, versi fallback |
| `ml/tier3/keanggotaan.py` | Fungsi keanggotaan segitiga/trapesium per kriteria; **satu sumber** untuk fuzzifikasi & penjelasan (anti-skew, meniru `skema_fitur.py`) |
| `ml/tier3/fuzzy_topsis.py` | Chen (2000) lengkap: normalisasi → bobot → FPIS/FNIS → jarak vertex → nilai preferensi; mode `degenerat` untuk kontrol |
| `ml/tier3/sensitivitas.py` | Perturbasi bobot, churn top-K, atribusi crisp/degenerat/fuzzy — perkakas yang menghasilkan tabel deliverable |
| `config/fuzzy_config.yaml` | + blok `keanggotaan:` (bentuk & rentang per kriteria, OI-13) + `tiebreak:` + `versi` |
| `app/services/tier3_topsis.py` | Pembungkus tipis; **kontrak `rank_topsis()` dipertahankan** |
| `app/services/pipeline.py` | Snapshot versi konfigurasi keanggotaan ke batch (di samping `bobot_snapshot`) |
| `tests/test_tier3.py` | Perhitungan manual, monotonisitas, penanganan seri, fallback bertanda, invarian (mis. alternatif dominan selalu peringkat 1) |

## Deliverable / Checklist

- [x] Probe pra-fase: apakah tujuan Fase 4 tercapai di data yang ada → [`hasil_probe.txt`](hasil_probe.txt)
- [x] Uji lima varian fuzzifikasi; pilih berdasarkan bukti, bukan konvensi → varian **keanggotaan**
- [x] Kontrol atribusi (TFN lebar nol) memisahkan efek mesin TOPSIS dari efek kefuzzian
- [ ] Definisikan fungsi keanggotaan per kriteria (bentuk & rentang) di `config/fuzzy_config.yaml` (OI-13)
- [ ] Implementasi Fuzzy TOPSIS Chen (2000) (FR-18…FR-21) di `ml/tier3/`
- [ ] Aturan tiebreak deterministik + pengurutan presisi penuh
- [ ] Ganti `app/services/tier3_topsis.py` — kontrak `rank_topsis()` dipertahankan
- [ ] Alur OI-15 tetap: batch = pengajuan dengan `prediksi_ml = layak` saja (sudah benar, jangan rusak)
- [ ] Snapshot bobot **dan** versi konfigurasi keanggotaan per batch
- [ ] **Contoh perhitungan manual** 4–5 alternatif, cocok sampai digit terakhir → jadi tes
- [ ] **Analisis sensitivitas bobot** (tabel ±20% & ±50%) + tabel atribusi → artefak fase
- [ ] `tests/test_tier3.py` + seluruh tes lama tetap lulus (baseline saat ini: 48)
- [ ] Putuskan perlakuan `skor_urgensi` (opsi A/B/C di atas) — **menunggu persetujuan**
- [ ] Formalisasi bobot & rentang keanggotaan dengan kelurahan (OI-12/OI-13) — **menunggu Fase 6**

## Exit criteria

**Untuk menutup Fase 4 (dapat dicapai sekarang, tanpa data lokal):** `rank_topsis()` memakai Fuzzy
TOPSIS asli; hasil cocok dengan perhitungan manual sampai digit terakhir; `ranking_topsis` menyimpan
nilai preferensi + peringkat + snapshot bobot & versi keanggotaan; tiebreak deterministik dan tercatat;
tabel sensitivitas bobot & atribusi tersedia; pipeline 3-tier nyata end-to-end; seluruh tes lulus.

**Untuk klaim skripsi (Fase 6):** bobot & fungsi keanggotaan yang disepakati kelurahan, dan
kesesuaian perangkingan dengan penilaian petugas.

## Alur reproduksi

```powershell
# Probe pra-fase (ulangi bila kriteria/bobot/generator berubah)
python progres/fase-4-tier3-fuzzy-topsis/probe_fuzzy_topsis.py
python progres/fase-4-tier3-fuzzy-topsis/probe_fuzzy_topsis.py --goyang 0.5   # sensitivitas lebih lebar
python progres/fase-4-tier3-fuzzy-topsis/probe_fuzzy_topsis.py --sumber db    # langsung dari basis data
```

Probe memakai `data/corpus/tier2_*.csv` (hasil ekspor Fase 3) dan menyaringnya lewat Tier 2 sungguhan;
ia mencetak peringatan bila Tier 2 sedang memakai fallback, karena batch dari fallback tidak sah.

## Catatan & artefak

Taruh di folder ini: definisi fungsi keanggotaan (grafik/rentang), contoh perhitungan manual,
tabel sensitivitas bobot, dan tabel atribusi crisp/degenerat/fuzzy. Setiap tabel wajib menyertakan
**asal data** dan **ukuran ketidakpastian**. Untuk Tier 3, tambahkan satu kolom lagi yang tidak
berlaku di tier lain: **apakah angka itu sifat metode atau klaim tentang kelayakan** — hanya yang
pertama yang sah dilaporkan dari data sintetis.
