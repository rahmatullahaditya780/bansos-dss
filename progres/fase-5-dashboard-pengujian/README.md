# Fase 5 — Dashboard, Penjelasan & Instrumen Pengujian

**Jalur:** A · **Target:** minggu 9 · **Status:** ✅ SELESAI (2026-08-08) — exit criteria terpenuhi;
**angka efektivitas sengaja ditunda ke Fase 7** (butuh petugas sungguhan, bukan data)

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

## Keputusan rancangan (disetujui 2026-08-08, seluruhnya sesuai rekomendasi)

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

## Hasil

Seluruh angka di bawah berasal dari **kode yang terpasang**, diukur atas basis data yang sama yang
melayani aplikasi. Probe yang sama dijalankan sebelum dan sesudah implementasi, sehingga kedua
kolom dapat dibandingkan langsung: [`hasil_probe.txt`](hasil_probe.txt) →
[`hasil_probe_setelah.txt`](hasil_probe_setelah.txt).

### Tabel 1 — penjelasan sepakat dengan metode yang menghasilkan peringkat (D-01)

| Kriteria | Skew sebelum | Skew sesudah |
|---|---|---|
| `pendapatan` | 40/300 (13,3%) | **0/300 (0,0%)** |
| `housing_need` | 211/300 (70,3%) | **0/300 (0,0%)** |
| `skor_urgensi` | 174/300 (58,0%) | **0/300 (0,0%)** |

Nol itu dijaga tes, bukan sekadar tercapai sekali: `tests/test_penjelasan.py` menyapu kisi 2.352
kombinasi nilai × 4 kriteria = **9.408 perbandingan label** di seluruh domain, termasuk perbatasan
antar-himpunan. Bila seseorang menambahkan ambang keras lagi di kemudian hari, tes yang gagal.

### Tabel 2 — isi penjelasan (OI-07)

| | Sebelum | Sesudah |
|---|---|---|
| Kalimat berbeda dari 300 | 196 (65,3%) | **251 (83,7%)** |
| Pola frasa berbeda | 116 | **130** |
| Nilai frasa urgensi | 2 (tinggi/rendah) | **3** (tinggi 126 · sangat rendah 168 · sedang 6) |
| Menyebut posisi Tier 3 | **0/300** | **146/300** (seluruh yang punya baris peringkat) |
| Menyebut versi model Tier 1 & 2 | 0/300 | **300/300** |
| Tabel kontribusi kriteria | tidak ada | **300/300** |

### Tabel 3 — instrumen waktu (FR-25, D-02/D-03)

| Populasi | n | p50 | maks | Perlakuan |
|---|---|---|---|---|
| `warm` | 7 | **204 ms** | 229 ms | Dasar metrik NFR-01: ≤5 detik **100%**, efisiensi Bab 9.2 **100%** |
| `cold` | 1 | — | **11.922 ms** | Dipisahkan, **tidak disembunyikan** — biaya pemuatan artefak |
| tanpa penanda (pra-Fase 5) | 305 | 196 ms | 13.998 ms | Dilaporkan terpisah; menebak penandanya = mengarang pengukuran |

Durasi per tahap: **Tier 1 93 ms · Tier 2 96 ms** (per pengajuan) · **Tier 3 19 ms per batch**
untuk 145 alternatif. Satuan Tier 3 sengaja berbeda: ia merangking seluruh alternatif sekaligus,
dan membaginya per pengajuan akan mengarang angka yang tidak pernah diukur.

Pemanasan artefak saat startup menghapus cold start dari pengalaman petugas: baris `cold` di atas
adalah permintaan pertama pada proses uji yang sengaja dijalankan tanpa pemanasan.

### Tabel 4 — halaman (D-05/D-06)

| Halaman | Sebelum | Sesudah |
|---|---|---|
| `/daftar` | 2.020 baris, 833 KiB, **1.801 ms**, pola N+1 | 25 baris/halaman, 16,8 KiB, **49 ms**, `joinedload` |
| `/peringkat` | selalu kosong; melihat hasil = **menjalankan batch baru** (145 baris tertulis tiap kali) | batch tersimpan ditampilkan, 114,9 KiB, 353 ms |
| `/metrik` | tidak ada | ada, 8,9 KiB, 31 ms |
| `ringkasan()` (polling 5 detik) | 9,3 ms | 9,5 ms **sambil menghitung jauh lebih banyak** |

Baris terakhir jujur dilaporkan sebagai **imbang, bukan perbaikan**: pemuatan objek ORM diganti
pengambilan kolom, tetapi jumlah kuerinya bertambah (efisiensi per tier, efektivitas, pencacahan
cold). Biayanya tetap ± sama sementara yang dihitung bertambah banyak.

### Efektivitas — instrumen selesai, angkanya tidak ada (dan itu benar)

Tombol verifikasi kini ada di halaman detail; `verifikasi_manual` menyimpan **snapshot putusan
sistem yang benar-benar dinilai** beserta versi modelnya, petugas penilainya, dan catatannya. Dua
urutan kerja yang dulu merusak pasangan sekarang ditutup dan **diuji**: analisis ulang tidak
membasikan pasangan, dan verifikasi-sebelum-analisis tidak lagi hilang tanpa pesan.

Angkanya sendiri: **0 pasangan → metrik menolak tampil**, bukan 0%. Uji ujung-ke-ujung sempat
dijalankan dengan 3 verifikasi buatan (menghasilkan 66,67%, 1 salah positif) untuk membuktikan
jalurnya bekerja; ketiganya **dihapus setelah verifikasi** agar tidak ada angka efektivitas karangan
yang mengendap di basis data — kelas kontaminasi yang sudah tiga kali menggigit proyek ini.

### Verifikasi

- **105 tes lulus** (sebelumnya 82; +23: `test_penjelasan.py` 8, `test_metrik.py` 15).
- Migrasi `9a1c4f7be210` diterapkan ke basis data dev; 305 baris log lama utuh.
- Ketiga tier terverifikasi pada baris DB, `fallback_aktif=False` seluruhnya.

### Cacat yang tersingkap saat implementasi

1. **Rute API `GET /metrik` menutupi halaman web `/metrik`** — router API terdaftar lebih dulu,
   sehingga halaman metrik mengembalikan JSON. Ini **tabrakan yang sama persis** dengan bug Fase 0
   antara `POST /analisis/ranking` dan `POST /analisis/{pengajuan_id}`. Endpoint API dipindah ke
   `/metrik/ringkasan`, mengikuti pola `/dashboard` (web) vs `/dashboard/ringkasan` (API).
2. **Penanda cold/warm nyaris menjadi kebohongan statistik.** Versi pertama memperlakukan 305 baris
   pra-Fase 5 sebagai `warm`, sehingga cold start 13.998 ms masuk ke angka NFR-01 lewat pintu
   belakang. Diperbaiki: baris tanpa penanda jadi populasi ketiga yang dilaporkan terpisah.
3. **Pemeriksaan cold/warm sempat merusak yang diukurnya.** `info_model()` Tier 2 memaksa pemuatan;
   memanggilnya untuk mendeteksi cold start memindahkan biaya muat ke luar rentang yang diukur.
   Ditambahkan `sudah_dimuat()` yang tidak memicu pemuatan.

## Deliverable / Checklist

- [x] Probe pra-fase: apakah tujuan Fase 5 tercapai di sistem yang ada → [`hasil_probe.txt`](hasil_probe.txt)
- [x] **D-01…D-06 disetujui** (2026-08-08, seluruhnya sesuai rekomendasi)
- [x] Generator alasan memakai `KriteriaFuzzy.label()` — skew **0%**, dijaga 9.408 perbandingan
- [x] Alasan mencakup ketiga tier, termasuk posisi & kriteria penyumbang Tier 3 (OI-07)
- [x] Durasi per tier tercatat (FR-25); Tier 3 per batch di `log_ranking`; cold terpisah dari warm
- [x] `hitung_efisiensi()` (Bab 9.2) tampil di dashboard & halaman metrik, bukan kode mati
- [x] Tombol verifikasi manual di UI (FR-26) + pemasangan tahan analisis ulang & urutan terbalik (D-04)
- [x] Halaman metrik efisiensi/efektivitas; efektivitas menolak tampil selama 0 pasangan
- [x] Badge versi model tiap tier + spanduk peringatan fallback di seluruh halaman (D-05)
- [x] `/daftar` berpaginasi + penyaring + pencarian, N+1 dibunuh; `/peringkat` menampilkan batch tersimpan
- [x] Teks "Fase 0 / stub" dibuang dari seluruh template
- [x] Seluruh tes lama tetap lulus (**105 lulus**, sebelumnya 82)
- [ ] Dashboard diperiksa nyata di smartphone (NFR-03) — kelas Bootstrap responsif sudah dipakai,
      **belum diuji di perangkat sungguhan**; masuk UAT Fase 7
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

→ **TERPENUHI** (2026-08-08), lihat [Hasil](#hasil).

**Untuk klaim skripsi (Fase 7):** efektivitas ≥85% terhadap verifikasi petugas, dengan sirkularitas
OI-18 (dilatih pada keputusan petugas, dinilai oleh petugas) ditulis sebagai keterbatasan.

## Alur reproduksi

```powershell
# Terapkan skema Fase 5 (durasi per tier, log_ranking, verifikasi_manual)
python -m alembic upgrade head

# Probe: dijalankan sebelum & sesudah implementasi; yang kedua membuktikan skew = 0
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
