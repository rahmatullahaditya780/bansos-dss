# Evaluasi Pra-Fase 5 — Tinjauan Fase 0–4

**Tanggal:** 2026-08-08 · **Cakupan:** seluruh pekerjaan sampai Tier 3 terpasang, sebelum dashboard
dan instrumen pengujian disentuh

Seperti dua evaluasi sebelumnya ([pra-Fase 3](evaluasi-pra-fase-3.md) ·
[pra-Fase 4](evaluasi-pra-fase-4.md)), tinjauan ini bukan laporan seremonial. Pertanyaannya dua:
**apa yang sekarang benar-benar berdiri**, dan **kekeliruan mana yang akan terulang di Fase 5 kalau
tidak dicegat lebih dulu.**

Dasar penilaian: seluruh kode dan dokumen fase dibaca ulang; `pytest` dijalankan (**82 tes lulus**,
19 detik); pemasangan ketiga tier diverifikasi lewat `info_model()` dan `info_fuzzy()`; dan satu
probe diagnostik baru dijalankan atas basis data nyata berisi 2.020 pengajuan / 300 hasil analisis
([`probe_dashboard_metrik.py`](fase-5-dashboard-pengujian/probe_dashboard_metrik.py), keluaran mentah
di [`hasil_probe.txt`](fase-5-dashboard-pengujian/hasil_probe.txt)).

---

## 1. Putusan ringkas

| Fase | Status nyata | Putusan |
|---|---|---|
| 0 — Kerangka integrasi | Selesai; sudah **tiga kali** terbayar (Tier 1, 2, 3) | **Sehat.** Berhenti mengevaluasinya sampai Fase 7 |
| 1 — Data & pelabelan | Perkakas lengkap; **data nyata masih nol** | **Jalur kritis, dan kini satu-satunya penghalang tersisa.** Lihat §4 |
| 2 — Tier 1 IndoBERT | Terpasang & terverifikasi; pembulatan sumber sudah dihapus | **Sehat.** Satu sisa warisan (`info()` optimistis) masih terbuka |
| 3 — Tier 2 ML | Terpasang & terverifikasi; batas klaim ditulis lebih dulu | **Sehat dan jujur** |
| 4 — Tier 3 Fuzzy TOPSIS | Selesai penuh; angka deliverable dihasilkan implementasi terpasang | **Sehat.** Metode kerjanya terbukti (§3) |
| 5 — Dashboard & instrumen | Belum mulai; fondasi Fase 0 masih apa adanya | **Siap dimulai, tetapi separuh janjinya tidak dapat ditutup** — lihat §5 & §6 |

**Riwayat git sudah beres.** Prasyarat yang dua kali dicatat sebagai tertunggak di evaluasi
pra-Fase 3 dan pra-Fase 4 kini selesai: enam commit, satu per fase, `master` terhubung ke remote
privat. Tidak ada lagi tindakan tertunggak dari evaluasi sebelumnya.

---

## 2. Verifikasi pemasangan — tiga tier, tiga penanda

| Tier | Penanda | `fallback_aktif` | Putusan |
|---|---|---|---|
| 1 | `indobert-p1-augmentasi-v3` (300/300 baris DB) | `False` | Artefak asli dipakai |
| 2 | `tier2-random-forest-sintetis-v1` (300/300 baris DB) | `False` | Artefak asli dipakai |
| 3 | `fuzzy-topsis-chen2000-v1` / cfg `provisional-1` | `False` | Logika fuzzy sungguhan dipakai |

Kali ini penanda diperiksa **pada baris basis data**, bukan hanya pada pemanggilan langsung — persis
pelajaran yang dibayar mahal di Fase 4, ketika Fuzzy TOPSIS yang sepenuhnya benar ternyata bekerja di
atas skor `stub-indobert-v0`. Tidak ada kontaminasi tersisa.

> **Namun penanda itu tidak pernah sampai ke layar petugas.** `info_fuzzy()` hanya dapat dilihat dari
> baris perintah; tidak satu pun halaman menampilkan versi model atau status fallback. Tiga kegagalan
> senyap proyek ini semuanya tersingkap oleh penanda versi — dan semuanya tersingkap **terlambat**,
> karena satu-satunya cara melihat penanda adalah dengan curiga lebih dulu lalu mengetik perintah.
> Ini yang seharusnya diperbaiki Fase 5 (§6, D-05).

## 3. Fase 4 — apa yang terbukti benar

Dua hal layak dicatat sebagai metode kerja yang sudah membuktikan diri, bukan sekadar kebiasaan:

1. **Probe sebelum kode kembali membayar.** Varian fuzzifikasi "linguistik polos" — bentuk yang
   paling lazim ditulis di skripsi Fuzzy TOPSIS — akan menyeret 25 dari 50 kursi kuota ke posisi seri.
   Itu ditemukan **sebelum** satu baris pun ditulis, lalu dihindari lewat pilihan rancangan. Dokumen
   ini melanjutkan kebiasaan yang sama.
2. **Kontrol atribusi mengubah klaim.** Tanpa baris `degenerat`, 18 pp pergantian daftar penerima akan
   diklaim sebagai "efek fuzzy"; kenyataannya 12 pp di antaranya terjadi tanpa satu pun bilangan fuzzy
   berlebar. Klaim yang selamat dari kontrol adalah klaim yang tahan sidang.

Dan satu pelajaran yang kini berstatus **kelas bug berulang** — pembulatan untuk tampilan yang bocor
ke perhitungan, muncul di `ml/tier1/infer.py` dan `tier3_topsis.py:65`. Fase 5 adalah fase yang paling
banyak menyentuh angka-untuk-ditampilkan sepanjang proyek ini. Aturannya tetap: **bulatkan hanya saat
menyimpan/menampilkan, jangan pernah sebelum menghitung, mengurutkan, atau membandingkan.**

## 4. Fase 1 kini satu-satunya penghalang tersisa

Neraca yang diramalkan evaluasi pra-Fase 4 sudah terjadi: **ketiga tier selesai secara kode, dan nol
angka yang layak masuk bab hasil sudah dihasilkan.** Yang masih kosong tidak berubah sejak dua
evaluasi lalu: dataset publik, pelabel kedua (kappa belum pernah dihitung atas data nyata), teks lokal
Bontoramba (izin OI-09), sesi validasi label historis (OI-10).

Fase 5 adalah sisa terakhir Jalur A yang dapat dikerjakan tanpa data lokal — dan §5.4 menunjukkan
bahwa bahkan Fase 5 pun **tidak dapat ditutup penuh**, karena setengah janjinya (efektivitas ≥85%)
membutuhkan petugas sungguhan, bukan sekadar data. Setelah Fase 5, tidak ada lagi pekerjaan Jalur A
yang bebas hambatan.

---

## 5. Temuan probe yang berdampak langsung ke Fase 5

Seluruh angka di bawah berasal dari basis data pengembangan yang sama yang melayani aplikasi:
2.020 pengajuan, 300 sudah dianalisis pipeline sungguhan, 305 baris `log_pengujian`, 145 alternatif
di batch peringkat terakhir.

### 5.1 Penjelasan ke petugas tidak sepakat dengan metode yang menghasilkan peringkat

Fase 4 membangun `KriteriaFuzzy.label()` dan menuliskannya sebagai **"satu sumber untuk fuzzifikasi
*dan* label penjelasan (anti-skew, meniru `skema_fitur.py`)"**. Sumber itu ada, berfungsi, dan
**tidak dipakai oleh generator penjelasan.** `app/services/explanation.py` masih memakai ambang
kerasnya sendiri dari Fase 0. Hasilnya diukur atas 300 pengajuan yang sama:

| Kriteria | Label penjelasan ≠ label fuzzy | Ketidaksepakatan terbesar |
|---|---|---|
| `pendapatan` | **40/300 (13,3%)** | 30× "tinggi" vs `sedang`; 10× "sangat rendah" vs `rendah` |
| `housing_need` | **211/300 (70,3%)** | 70× "cukup" vs `buruk`; 54× "buruk" vs `sangat_buruk`; 50× "baik" vs `cukup` |
| `skor_urgensi` | **174/300 (58,0%)** | 168× "rendah" vs `sangat_rendah`; 6× "tinggi" vs `sedang` |

*(Perbedaan ejaan `sangat rendah` vs `sangat_rendah` tidak dihitung sebagai ketidaksepakatan.)*

Bacaannya: pada **7 dari 10 pengajuan**, layar memberi tahu petugas bahwa kondisi rumah "cukup"
sementara metode yang menyusun peringkatnya memperlakukannya sebagai `buruk`. Penjelasan yang
menerangkan keputusan yang berbeda dari keputusan yang benar-benar diambil bukan penjelasan — dan
OI-07 justru ada supaya petugas dapat mempertanggungjawabkan hasil sistem.

Dua akarnya berbeda dan keduanya perlu diperbaiki:

- **Ambang ganda.** `kategori_rumah()` memotong di 0,33/0,66 secara keras, sedangkan konfigurasi
  fuzzy memakai empat himpunan segitiga bertumpang tindih dengan puncak di 0/0,33/0,67/1,0. Dua
  definisi untuk kata yang sama, di aplikasi yang sama.
- **Skala yang sudah usang.** `kategori_urgensi()` memotong **probabilitas** di 0,5, sedangkan sejak
  Fase 4 kriteria urgensi difuzzifikasi pada **skala logit**. Kalimat penjelasan masih hidup di dunia
  sebelum keputusan opsi A diambil.

### 5.2 Kalimat penjelasan tidak menyebut Tier 3 sama sekali

Dari 300 kalimat yang dihasilkan: 196 berbeda (65,3%), 116 pola frasa berbeda setelah angka
probabilitas dibuang. Itu bukan angka buruk. Yang bermasalah adalah isinya:

| Yang seharusnya diterangkan | Muncul di berapa kalimat |
|---|---|
| Posisi peringkat / nilai preferensi Tier 3 | **0/300** |
| Versi model yang mengambil keputusan | **0/300** |
| Kontribusi relatif tiap kriteria | **0/300** |
| Derajat urgensi | 2 nilai saja ("tinggi" 132 / "rendah" 168) |

Penjelasan hari ini hanya menerangkan Tier 2. Tier 1 masuk sebagai satu kata biner, Tier 3 tidak masuk
sama sekali — padahal Tier 3-lah yang menentukan siapa yang benar-benar menerima bantuan ketika kuota
terbatas. Bahan untuk memperbaikinya **sudah ada dan sudah dihitung**: `RankingEntry` Fase 4 membawa
`keanggotaan`, `jarak_positif`, `jarak_negatif`, dan `seri_dengan` — dan `pipeline.jalankan_ranking()`
membuang keempatnya sebelum menyimpan.

### 5.3 Instrumen waktu hanya mengukur separuh pipeline — dan mencampur cold start

| | Nilai |
|---|---|
| Baris log dengan durasi | 305 |
| p50 / p90 | **196 ms / 214 ms** |
| Maksimum | **13.998 ms** |
| Permintaan ≤5 detik | 99,67% (1 pelanggaran) |
| Efisiensi Bab 9.2 pada p50 / pada maksimum | **100% / 35,72%** |

Satu-satunya pelanggaran 5 detik adalah **log ke-6 secara kronologis** — permintaan pertama setelah
artefak IndoBERT terpasang. Permintaan berikutnya, 14 detik kemudian, memakan 209 ms. Itu biaya
pemuatan model, bukan beban komputasi: **setiap kali proses aplikasi dimulai ulang, satu petugas akan
menunggu 14 detik**, dan angka itu akan masuk ke laporan efisiensi sebagai kegagalan NFR-01. Perlu
diputuskan cara memperlakukannya (§6, D-02) — dilaporkan terpisah, atau dihilangkan dengan pemanasan
saat startup, atau keduanya.

Dua kekosongan lain pada instrumen yang sama:

- **Tier 3 tidak pernah masuk log.** `rank_topsis()` atas 145 alternatif memakan ~20 ms, dan tidak ada
  satu pun baris `log_pengujian` yang mencatatnya. Angka efisiensi yang dilaporkan hari ini hanya
  mencakup Tier 1 + Tier 2. Untuk skripsi, cakupan itu harus dinyatakan atau diperluas.
- **Rumus resmi Bab 9.2 tidak pernah dipanggil.** `metrics.hitung_efisiensi()` — `min(5s/aktual,1)×100%`,
  rumus yang akan ditulis di bab pengujian — tidak dirujuk dari mana pun di aplikasi. Dashboard hanya
  menampilkan persentase ≤5 detik. Rumusnya ada, kodenya mati.

### 5.4 Efektivitas: nol pasangan, dan mekanismenya rusak sebelum dipakai

`hitung_efektivitas()` mengembalikan `None`, dan akan terus begitu:

| | Nilai |
|---|---|
| Log dengan `hasil_sistem` | 305 |
| Log dengan `hasil_manual_petugas` | **0** |
| Pasangan lengkap | **0** |
| Pengajuan berlog ganda | 5 |

Nol itu **bukan kemalasan pengguna, melainkan lubang antarmuka**: perekaman verifikasi manual (FR-26)
hanya ada sebagai endpoint `POST /verifikasi/{id}`. Tidak satu pun template menyediakan tombolnya.
Petugas yang memakai dashboard secara fisik tidak dapat memasukkan penilaian manual, sehingga metrik
target skripsi (≥85%) tidak akan pernah punya masukan.

Lebih dari itu, mekanisme pemasangannya sendiri cacat. Verifikasi ditulis ke **baris log terbaru**,
sedangkan tiap analisis membuat **baris log baru** — dua urutan kerja yang sepenuhnya wajar merusaknya:

| Urutan kerja petugas | Akibat |
|---|---|
| analisis → verifikasi → **analisis ulang** | Pasangan tetap ada tetapi memakai putusan sistem **lama**; efektivitas dihitung terhadap hasil yang sudah tidak tampil di layar |
| **verifikasi dulu** → analisis | Pasangan tidak pernah terbentuk; verifikasi hilang tanpa peringatan |

Kasus pertama bukan hipotetis: 5 pengajuan sudah berlog ganda akibat analisis ulang di Fase 4. Bila
verifikasi sudah berjalan waktu itu, lima pasangan basi sudah masuk ke metrik hari ini.

**Dan bahkan setelah diperbaiki, angkanya tetap tidak dapat dilaporkan di Fase 5.** Efektivitas
mengukur kesesuaian sistem dengan penilaian petugas sungguhan; yang dapat dibangun sekarang hanyalah
instrumennya. Angkanya milik Fase 7 (UAT), dengan sirkularitas OI-18 — model dilatih pada keputusan
petugas lalu dinilai oleh petugas — tetap wajib ditulis sebagai keterbatasan.

### 5.5 Biaya instrumen dan biaya halaman

| Yang diukur | Hasil |
|---|---|
| `ringkasan()` (dipanggil dashboard **tiap 5 detik**) | 9,3 ms pada 305 baris log; O(n) — seluruh tabel dimuat ke memori tiap panggilan |
| Perkiraan pada 10.000 baris log | ~306 ms per polling, per petugas yang membuka dashboard |
| `/daftar` (2.020 baris) | **1.801 ms**, HTML **833 KiB** |

`/daftar` memuat seluruh tabel tanpa paginasi, penyaring status, maupun pencarian. Kuerinya sendiri
hanya 26 ms; sisanya 1.775 ms adalah render — sebagian besar karena `p.warga` diakses per baris
sehingga menghasilkan pola N+1. Pada 2.020 baris ini masih di bawah 5 detik; ia tidak akan tetap
begitu, dan yang lebih penting: **inilah halaman yang akan dipakai petugas saat UAT diukur.**

Ada juga cacat alur di halaman peringkat: `GET /peringkat` selalu menampilkan kotak kosong, dan
satu-satunya cara melihat peringkat adalah menekan tombol yang **menjalankan batch baru**. Melihat
hasil kemarin berarti menghitung ulang hari ini; setiap kali dilihat, 145 baris `ranking_topsis` baru
tertulis. Endpoint `GET /ranking` yang mengembalikan batch terakhir sudah ada, tetapi tidak dipakai
halaman mana pun.

### 5.6 Antarmuka masih mengaku Fase 0

Tiga tempat menyatakan hal yang sudah tidak benar sejak dua fase lalu:

| Berkas | Tulisan | Kenyataan |
|---|---|---|
| `base.html` (footer, tiap halaman) | "Fase 0 (kerangka). Model tier masih *stub*." | Ketiga tier memakai model/metode sungguhan |
| `peringkat.html` | "*Fase 0: memakai TOPSIS crisp sebagai stub*" | Fuzzy TOPSIS Chen (2000) sejak Fase 4 |
| `partials/_hasil.html` | "0–1 (probabilitas urgensi tinggi)" | Benar untuk tampilan, tetapi Tier 3 memakai skala logit — dan itu tidak terlihat di mana pun |

Ini bukan sekadar teks basi. Bila konfigurasi keanggotaan rusak dan Tier 3 turun ke
`topsis-crisp-fallback-v0`, halaman peringkat akan tetap menampilkan angka yang sama rapinya, dengan
keterangan yang kebetulan justru "benar" — dan tidak ada apa pun di layar yang memberi tahu petugas
(atau penguji sidang) bahwa hasil di hadapannya bukan keluaran Fuzzy TOPSIS.

---

## 6. Keputusan yang harus diambil sebelum menulis kode Fase 5

| # | Keputusan | Rekomendasi | Konsekuensi bila ditunda |
|---|---|---|---|
| **D-01** | Sumber label penjelasan: ambang `explanation.py` atau `KriteriaFuzzy.label()`? | **Pakai `KriteriaFuzzy.label()` sebagai satu-satunya sumber**, konfigurasi ikut versi | 70% penjelasan kondisi rumah terus bertentangan dengan peringkat yang ditampilkan di halaman yang sama |
| **D-02** | Perlakuan cold start pada metrik efisiensi | **Panaskan artefak saat startup + laporkan warm/cold terpisah**, `hitung_efisiensi()` dipakai di dashboard | Satu permintaan 14 detik per restart masuk laporan NFR-01 sebagai kegagalan |
| **D-03** | Cakupan FR-25: Tier 1+2 saja, atau termasuk Tier 3? | **Catat durasi per tier + total**, agar bab hasil dapat menyebut cakupannya | Angka efisiensi skripsi diam-diam tidak mencakup metode utamanya |
| **D-04** | Model perekaman verifikasi manual | **Pasangkan verifikasi ke putusan sistem yang benar-benar dilihat petugas** (snapshot saat verifikasi), bukan ke baris log terbaru | Metrik ≥85% dihitung dari pasangan basi atau hilang diam-diam |
| **D-05** | Apakah versi model & status fallback tampil di UI | **Tampilkan** di detail, peringkat, dan dashboard | Kegagalan senyap keempat menunggu; tiga yang lalu hanya tersingkap oleh penanda versi |
| **D-06** | Paginasi/penyaring `/daftar` sekarang atau Fase 7 | **Sekarang** — halaman ini yang dipakai saat UAT diukur | 833 KiB per muat, tumbuh linear terhadap data lokal |

Enam-enamnya adalah pekerjaan Fase 5 dan tidak satu pun memerlukan data lokal. Yang **tidak** dapat
diselesaikan Fase 5 hanya satu: angka efektivitas itu sendiri.

## 7. Kesiapan masuk Fase 5

**Siap dimulai.** Tidak ada prasyarat yang tertunggak: tes hijau, tiga tier terverifikasi pada baris
basis data, git bersih, dan data pengembangan (2.020 pengajuan, 300 teranalisis, 145 teringkat) cukup
untuk melatih seluruh instrumen kecuali satu.

Satu penyesuaian ekspektasi wajib ditulis sekarang, bukan ditemukan di akhir fase: **exit criteria
Fase 5 versi rencana tidak dapat dipenuhi seluruhnya.** Kalimatnya berbunyi "metrik efisiensi/efektivitas
tampil dan terhitung otomatis dari `log_pengujian`" — efisiensi dapat, efektivitas **tidak**, karena
belum ada satu pun penilaian manual dan tidak akan ada sampai petugas sungguhan memakai sistem (Fase 7).
Yang dapat ditutup Fase 5 adalah **instrumennya**: jalur perekaman yang benar, halaman metrik yang
menghitung otomatis begitu pasangan pertama masuk, dan angka yang menolak tampil selama masukannya nol
— bukan menampilkan 0% atau 100% yang menyesatkan.

Pola ini sudah dikenal. Fase 2 dan Fase 3 juga ditutup dengan kode selesai dan angka ditunda; bedanya,
kali ini penundaannya diketahui **sebelum** fase dimulai dan tertulis di exit criteria-nya sendiri.
