# Fase 5 — Dashboard, Penjelasan & Instrumen Pengujian

**Jalur:** A · **Target:** minggu 9 · **Status:** 🔶 Siap dimulai (probe selesai 2026-08-08; menunggu
persetujuan 6 keputusan rancangan)

## Tujuan

Mematangkan tiga hal yang dibangun tipis di Fase 0: **dashboard** (FR-22…FR-24), **penjelasan
keputusan** berbasis aturan (OI-07, tanpa LLM), dan **instrumen pengukuran** efisiensi/efektivitas
(TRD Bab 9.2/9.3, FR-25/FR-26).

Berbeda dari Fase 4, tujuan ini **tidak dapat dicapai sepenuhnya sekarang** — dan itu diketahui
sebelum fase dimulai, bukan ditemukan di akhirnya. Alasannya di
[evaluasi pra-Fase 5](../evaluasi-pra-fase-5.md) §5.4: efektivitas mengukur kesesuaian sistem dengan
penilaian **petugas sungguhan**; belum ada satu pun penilaian manual terekam, dan tidak akan ada
sampai sistem dipakai orang (Fase 7). Yang dapat ditutup Fase 5 adalah **instrumennya**, bukan
angkanya. Lihat [Exit criteria](#exit-criteria).

## Yang sudah diketahui sebelum menulis kode

[`probe_dashboard_metrik.py`](probe_dashboard_metrik.py) dijalankan lebih dulu atas basis data
pengembangan yang sama yang melayani aplikasi — **2.020 pengajuan, 300 hasil analisis pipeline
sungguhan, 305 baris log, 145 alternatif di batch peringkat terakhir**. Keluaran mentah:
[`hasil_probe.txt`](hasil_probe.txt). Enam temuan mengubah rancangan fase ini.

**1. Penjelasan ke petugas tidak sepakat dengan metode yang menghasilkan peringkat.** Fase 4
membangun `KriteriaFuzzy.label()` sebagai "satu sumber untuk fuzzifikasi *dan* label penjelasan";
sumber itu ada, berfungsi, dan tidak dipakai. `explanation.py` masih memakai ambang kerasnya sendiri
dari Fase 0:

| Kriteria | Label penjelasan ≠ label fuzzy | Ketidaksepakatan terbesar |
|---|---|---|
| `pendapatan` | 40/300 (**13,3%**) | 30× "tinggi" vs `sedang` |
| `housing_need` | 211/300 (**70,3%**) | 70× "cukup" vs `buruk`; 54× "buruk" vs `sangat_buruk` |
| `skor_urgensi` | 174/300 (**58,0%**) | 168× "rendah" vs `sangat_rendah` |

Pada 7 dari 10 pengajuan, layar memberi tahu petugas bahwa kondisi rumah "cukup" sementara metode
yang menyusun peringkatnya memperlakukannya sebagai `buruk`. Untuk `skor_urgensi` akarnya lebih
dalam: penjelasan memotong **probabilitas** di 0,5, sedangkan sejak Fase 4 kriteria itu difuzzifikasi
pada **skala logit** — kalimatnya masih hidup di dunia sebelum keputusan opsi A.

**2. Penjelasan tidak menyebut Tier 3 sama sekali.** Dari 300 kalimat: 196 berbeda (65,3%), 116 pola
frasa — tetapi **0/300** menyebut peringkat atau nilai preferensi, **0/300** menyebut versi model,
**0/300** menyebut kontribusi kriteria, dan derajat urgensi hanya punya dua nilai. Yang menentukan
siapa benar-benar menerima bantuan saat kuota terbatas adalah Tier 3, dan Tier 3 tidak diterangkan.
Bahannya sudah dihitung: `RankingEntry` membawa `keanggotaan`, `jarak_positif`, `jarak_negatif`,
`seri_dengan` — dan `pipeline.jalankan_ranking()` membuang keempatnya sebelum menyimpan.

**3. Instrumen waktu mengukur separuh pipeline dan mencampur cold start.** p50 196 ms, p90 214 ms,
99,67% ≤5 detik — satu-satunya pelanggaran adalah **13.998 ms pada log ke-6 kronologis**, permintaan
pertama setelah artefak IndoBERT terpasang; permintaan berikutnya 209 ms. Itu biaya pemuatan model:
setiap restart proses membuat satu petugas menunggu 14 detik, dan angka itu masuk laporan NFR-01
sebagai kegagalan. Selain itu **Tier 3 (~20 ms untuk 145 alternatif) tidak pernah tercatat**, dan
rumus resmi Bab 9.2 `metrics.hitung_efisiensi()` **tidak dipanggil dari mana pun** — dashboard hanya
menampilkan persentase ≤5 detik.

**4. Efektivitas: nol pasangan, dan mekanismenya rusak sebelum sempat dipakai.** 305 log punya
`hasil_sistem`, **0** punya `hasil_manual_petugas`. Sebabnya bukan kemalasan pengguna melainkan
lubang antarmuka: FR-26 hanya ada sebagai endpoint `POST /verifikasi/{id}` — **tidak satu pun
template menyediakan tombolnya.** Mekanisme pemasangannya pun cacat: verifikasi ditulis ke baris log
*terbaru*, sedangkan tiap analisis membuat baris log *baru*.

| Urutan kerja petugas | Akibat |
|---|---|
| analisis → verifikasi → analisis ulang | Pasangan memakai putusan sistem **lama** — 5 pengajuan sudah berlog ganda |
| verifikasi dulu → analisis | Pasangan **tidak pernah terbentuk**; verifikasi hilang tanpa peringatan |

**5. Biaya instrumen dan biaya halaman.** `ringkasan()` dipanggil dashboard tiap 5 detik dan memuat
seluruh tabel log ke memori: 9,3 ms pada 305 baris, ~306 ms pada 10.000. `/daftar` merender 2.020
baris tanpa paginasi/penyaring/pencarian: **1.801 ms, 833 KiB** (26 ms kueri + 1.775 ms render, pola
N+1 karena `p.warga` diakses per baris). Halaman peringkat lebih buruk secara alur: `GET /peringkat`
selalu kosong, dan satu-satunya cara melihat peringkat adalah tombol yang **menjalankan batch baru**
— 145 baris `ranking_topsis` tertulis setiap kali seseorang ingin melihat hasil kemarin. `GET /ranking`
yang mengembalikan batch terakhir sudah ada dan tidak dipakai halaman mana pun.

**6. Antarmuka masih mengaku Fase 0.** Footer di setiap halaman: "Fase 0 (kerangka). Model tier masih
*stub*." Halaman peringkat: "*Fase 0: memakai TOPSIS crisp sebagai stub*". Keduanya salah sejak dua
fase lalu. Yang lebih berbahaya: **tidak ada apa pun di layar yang menampilkan versi model atau status
fallback.** Bila konfigurasi keanggotaan rusak dan Tier 3 turun ke `topsis-crisp-fallback-v0`, halaman
akan tetap menampilkan angka serapi biasa — dan tiga kegagalan senyap proyek ini semuanya hanya
tersingkap oleh penanda versi.

## Keputusan rancangan (perlu persetujuan sebelum implementasi)

Enam keputusan di bawah berasal langsung dari temuan di atas ([evaluasi §6](../evaluasi-pra-fase-5.md#6-keputusan-yang-harus-diambil-sebelum-menulis-kode-fase-5)).
Tidak satu pun memerlukan data lokal.

| # | Keputusan | Rekomendasi |
|---|---|---|
| **D-01** | Sumber label penjelasan | **`KriteriaFuzzy.label()` jadi satu-satunya sumber**; `explanation.py` berhenti punya ambang sendiri. Konsekuensi yang harus diterima: label kondisi rumah berubah pada ~70% pengajuan — karena yang sekarang tampil memang keliru, bukan karena definisinya diperlonggar |
| **D-02** | Cold start pada metrik efisiensi | **Panaskan artefak saat startup** + laporkan warm/cold terpisah; `hitung_efisiensi()` mulai dipakai dashboard, bukan sekadar ada |
| **D-03** | Cakupan FR-25 | **Catat durasi per tier + total**, termasuk Tier 3, agar bab hasil dapat menyebut cakupannya alih-alih menyiratkannya |
| **D-04** | Perekaman verifikasi manual | **Pasangkan verifikasi ke putusan sistem yang benar-benar dilihat petugas** (snapshot hasil + versi model saat verifikasi), bukan ke baris log terbaru |
| **D-05** | Penanda versi di UI | **Tampilkan** versi model tiap tier + status fallback di detail, peringkat, dan dashboard — mencegah kegagalan senyap keempat |
| **D-06** | Paginasi/penyaring `/daftar` | **Sekarang**, bukan Fase 7 — halaman inilah yang dipakai saat UAT diukur |

Dua aturan yang sudah terbayar dan tetap berlaku di fase ini:

- **Bulatkan hanya saat menyimpan/menampilkan.** Fase 5 adalah fase yang paling banyak menyentuh
  angka-untuk-ditampilkan; kelas bug ini sudah muncul dua kali (`ml/tier1/infer.py`,
  `tier3_topsis.py:65`).
- **Metrik menolak tampil ketika masukannya nol.** Efektivitas dari 0 pasangan bukan 0% dan bukan
  100%; ia harus tampil sebagai "belum dapat dihitung" beserta jumlah pasangan yang tersedia.

## Yang akan dibangun

| Berkas | Isi |
|---|---|
| `app/services/explanation.py` | Ditulis ulang di atas `KriteriaFuzzy.label()` (D-01); alasan mencakup Tier 1 (derajat, bukan biner), Tier 2, **dan Tier 3** (peringkat, nilai preferensi, kriteria penyumbang, status seri) |
| `app/services/metrics.py` | `hitung_efisiensi()` dipakai sungguhan; pemisahan warm/cold; agregasi per tier |
| `app/services/dashboard_service.py` | Agregasi lewat kueri SQL (bukan memuat seluruh tabel); tambah metrik per tier, status pemasangan model, jumlah pasangan verifikasi |
| `app/services/pipeline.py` | Simpan durasi per tier; simpan `keanggotaan`/jarak/seri dari `RankingEntry` (kini dibuang); catat durasi Tier 3 |
| `app/services/verifikasi.py` *(baru)* | Perekaman verifikasi manual yang memasangkan diri ke putusan sistem yang dilihat petugas (D-04) |
| `app/db/models.py` + migrasi | Kolom penampung durasi per tier, snapshot putusan saat verifikasi, dan label keanggotaan per baris ranking |
| `app/api/routes/web.py` | Paginasi + penyaring status + pencarian NIK/nama di `/daftar`; `/peringkat` menampilkan batch terakhir tanpa menghitung ulang; tombol verifikasi di detail |
| `app/templates/` | Halaman metrik (Bab 9.2/9.3); panel penjelasan per tier; badge versi model & fallback (D-05); teks "Fase 0" dibuang; `eager load` warga untuk membunuh N+1 |
| `tests/test_metrik.py`, `tests/test_penjelasan.py` *(baru)* | Kesetaraan label penjelasan dengan label fuzzy; efisiensi warm/cold; pemasangan verifikasi tahan analisis ulang & tahan urutan terbalik; metrik menolak tampil pada masukan nol |

## Deliverable / Checklist

- [x] Probe pra-fase: apakah tujuan Fase 5 tercapai di sistem yang ada → [`hasil_probe.txt`](hasil_probe.txt)
- [ ] **D-01…D-06 disetujui** sebelum implementasi dimulai
- [ ] Generator alasan memakai `KriteriaFuzzy.label()` — skew terhadap label fuzzy **0%**, diuji
- [ ] Alasan mencakup ketiga tier, termasuk posisi & kriteria penyumbang Tier 3 (OI-07)
- [ ] Durasi per tier tercatat (FR-25), Tier 3 termasuk; cold start terpisah dari warm
- [ ] `hitung_efisiensi()` (Bab 9.2) tampil di dashboard, bukan kode mati
- [ ] Tombol verifikasi manual di UI (FR-26) + pemasangan yang tahan analisis ulang (D-04)
- [ ] Halaman metrik efisiensi/efektivitas; efektivitas menolak tampil selama 0 pasangan
- [ ] Badge versi model tiap tier + peringatan fallback di UI (D-05)
- [ ] `/daftar` berpaginasi + penyaring + pencarian; N+1 dibunuh; `/peringkat` menampilkan batch terakhir
- [ ] Teks "Fase 0 / stub" dibuang dari seluruh template
- [ ] Dashboard responsif desktop & smartphone diperiksa nyata (NFR-03)
- [ ] Seluruh tes lama tetap lulus (**82** saat ini) + tes baru
- [ ] *(menunggu Fase 7)* Angka efektivitas ≥85% terhadap verifikasi petugas sungguhan (OI-18)
- [ ] *(warisan)* `ml/tier1/infer.py` — `info()` melaporkan `fallback_aktif: false` sebelum pemuatan pertama

## Exit criteria

**Untuk menutup Fase 5 (dapat dicapai sekarang, tanpa data lokal):** petugas dapat meninjau seluruh
hasil tiga tier beserta alasan yang **sepakat dengan metode yang menghasilkannya**; verifikasi manual
dapat direkam dari antarmuka dan terpasang ke putusan sistem yang benar; durasi tiap tier tercatat dan
metrik efisiensi Bab 9.2 terhitung otomatis; versi model & status fallback terlihat di layar; halaman
utama tetap responsif pada volume data yang ada; seluruh tes lulus.

**Yang sengaja TIDAK masuk exit criteria:** angka efektivitas. Ia butuh petugas sungguhan (Fase 7),
dan menampilkannya dari nol pasangan akan menghasilkan angka yang menyesatkan. Rencana awal menulis
"metrik efisiensi/efektivitas tampil dan terhitung otomatis dari `log_pengujian`"; setengahnya
dipindahkan ke Fase 7 dengan alasan tertulis, bukan dibiarkan gagal diam-diam.

**Untuk klaim skripsi (Fase 7):** efektivitas ≥85% terhadap verifikasi petugas, dengan sirkularitas
OI-18 (dilatih pada keputusan petugas, dinilai oleh petugas) ditulis sebagai keterbatasan.

## Alur reproduksi

```powershell
# Probe pra-fase (arsip keputusan rancangan; ulangi setelah implementasi untuk membuktikan skew = 0)
python progres/fase-5-dashboard-pengujian/probe_dashboard_metrik.py

# Verifikasi pemasangan ketiga tier sebelum percaya angka mana pun
python -c "from app.services.tier1_nlp import info_model; print(info_model())"
python -c "from app.services.tier2_ml import info_model; print(info_model())"
python -c "from app.services.tier3_topsis import info_fuzzy; print(info_fuzzy())"
```

## Catatan & artefak

Taruh di folder ini: tangkapan layar dashboard final (desktop & smartphone), catatan uji usability
awal, desain laporan metrik, dan hasil probe setelah implementasi. Setiap tabel metrik wajib
menyertakan **asal data**, **ukuran ketidakpastian**, dan — khusus fase ini — **berapa banyak masukan
nyata yang menyusunnya**, karena satu-satunya cara metrik pengujian menipu adalah dengan tampil
percaya diri di atas nol pengamatan.
