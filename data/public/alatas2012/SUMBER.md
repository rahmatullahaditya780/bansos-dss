# Sumber data — Targeting the Poor (Alatas dkk., 2012)

Sumber **data latih Tier 2 nyata**, menggantikan data sintetis untuk klaim publik/PoC.

> **Status: TERUNDUH & TEREKSTRAK** (13 Agustus 2026). Terverifikasi 5.756 rumah tangga dan
> 640 desa — cocok persis dengan angka di paper. Integritas 360 berkas tercatat di
> [`MANIFES.sha256`](MANIFES.sha256). Arsip `.zip` asli tidak disimpan, sehingga checksum yang
> berlaku adalah checksum berkas hasil ekstrak, bukan checksum arsip Dataverse.
>
> Verifikasi ulang kapan saja:
> ```bash
> cd data/public/alatas2012 && sha256sum -c MANIFES.sha256
> ```

## Identitas

| | |
|---|---|
| Judul | Replication data for: Targeting the Poor: Evidence from a Field Experiment in Indonesia |
| Penulis | Vivi Alatas, Abhijit Banerjee, Rema Hanna, Benjamin A. Olken, Julia Tobias |
| Publikasi | *American Economic Review* 102(4): 1206–1240, 2012 |
| Repositori | Harvard Dataverse |
| DOI | [`10.7910/DVN/M7SKQZ`](https://doi.org/10.7910/DVN/M7SKQZ) |
| Versi | 5 (rilis 31 Maret 2020) |
| Lisensi | **CC0 1.0** (domain publik — bebas dipakai & diterbitkan ulang) |
| Cermin | openICPSR proyek [112522](https://www.openicpsr.org/openicpsr/project/112522) |

## Cakupan

- **640 desa**, **5.756 rumah tangga**, survei dasar **2008**.
- Provinsi: **Sumatera Utara, Sulawesi Selatan, Jawa Tengah** — stratifikasi ±30% perkotaan,
  70% perdesaan.
- Eksperimen membandingkan tiga cara menyasar warga miskin: **PMT** (aset → prediksi konsumsi),
  **community targeting** (warga meranking sedesa dari terkaya ke termiskin), dan **hibrida**.
- Variabel survei dasar: konsumsi per kapita, aset, karakteristik rumah, demografi, jaringan
  keluarga/pertemanan, serta partisipasi program bantuan.

## Cara mengunduh

Buka <https://dataverse.harvard.edu/dataset.xhtml?persistentId=doi:10.7910/DVN/M7SKQZ> →
tab **Files** → centang berkas → **Download**.

**Tidak bisa lewat `curl`/skrip.** Dataverse mewajibkan respons *guestbook* (nama, email,
institusi, tujuan penggunaan); panggilan API tanpa itu ditolak:

```
{"status":"ERROR","message":"You may not download this file without the required
 Guestbook response for guestbookID 269."}
```

Formulirnya gratis dan **tidak butuh akun** — isi di browser, unduhan langsung jalan.

Simpan seluruh arsip ke `data/public/alatas2012/raw/`, lalu ekstrak:

```powershell
cd d:\Apps\Gilang\bansos-dss
foreach ($z in Get-ChildItem data\public\alatas2012\raw\*.zip) {
  Expand-Archive $z.FullName -DestinationPath data\public\alatas2012\ -Force
}
```

## Peta isi (hasil inventarisasi 13 Agustus 2026)

Struktur nyata di disk: `data/public/alatas2012/Targeting_Indonesia/`.

| Berkas | Bentuk | Isi penting |
|---|---|---|
| `codeddata/coding_suseti_pmt.dta` | 5.756 × 347 | **Sumber fitur Tier 2.** `hhid`, `CONSUMPTION`, `hhsize`, `hhage`, `tfloor`, `twall`, `troof`, `water`, `toilet`, `floor`, aset (`se2_125` motor, `se2_138` lahan pertanian) |
| `codeddata/mistargeting_CORRECTED.dta` | 5.756 × 95 | **Sumber label.** `poor`, `verypoor`, `nearpoor`, `povline_poor`, `RTS`, `ranking_PMT`, `ranking_meeting` |
| `codeddata/finalranks.dta` | 6.112 × 6 | `hhid` + `RANKCONSUMPTION`, `RANK_rthead` — **satu-satunya berkas peringkat yang punya `hhid`** |
| `codeddata/analysis01.dta` | 40.417 × 416 | Berkas analisis utama (level individu) |
| `data/baseline/` | 69 `.dta` | Modul survei dasar mentah |
| `dofiles/` | 43 `.do` | Kode replikasi Stata — rujukan bagaimana variabel dibentuk |

Sebaran label terverifikasi: `poor` = 2.028 miskin / 3.725 tidak (35,2% positif, 3 kosong);
`RTS` (benar-benar menerima Rp 30.000) = 1.719 / 5.756. Konsumsi per kapita median 405,7
(ribu Rp/bulan, 2008), rentang 55,4–17.662,8. `hhsize` median 4 (maks 16), `hhage` median 46
(rentang 14–105).

## ⚠️ Lima jebakan yang sudah terverifikasi — baca sebelum menulis skrip harmonisasi

1. **`CONSUMPTION` bersatuan RIBU rupiah.** Median 405,7 berarti Rp 405.700/kapita/bulan (2008).
   `data_survei.pendapatan` bersatuan rupiah penuh → **kali 1.000**, lalu deflasi ke tahun
   rujukan. Memasukkannya mentah membuat nilainya 1.000× terlalu kecil; Tier 2 tetap jalan tanpa
   galat, tapi fungsi keanggotaan fuzzy Tier 3 yang dikalibrasi dalam rupiah jadi omong kosong.

2. **Variabel rumah sudah biner, bukan kategori teks.** `tfloor` = "Not earth floor" (0/1),
   `twall` = "Brick or cement wall", `water` = "Clean drinking water". Sementara
   `app/services/features.py` menanti string (`"tanah"`, `"bambu"`, `"pdam"`) dan **nilai tak
   dikenal diam-diam menjadi `0.5`** — bukan galat, cuma angka salah. Pemetaan harus eksplisit,
   dan sadari granularitasnya turun: `_LANTAI` punya 7 tingkat, data ini hanya 2.

3. **Label `poor` TIDAK ada di berkas fitur** — wajib join. Kunci amannya `hhid`
   (`coding_suseti_pmt` ↔ `finalranks`, irisan 5.756/5.756). **`mistargeting_CORRECTED.dta`
   tidak punya `hhid`**, hanya `hhea` (640 desa). Urutan barisnya memang identik dengan
   `coding_suseti_pmt` (sudah diuji: `CONSUMPTION` dan `hhea` cocok baris-per-baris), tapi
   menggabung berdasarkan urutan baris itu rapuh — verifikasi ulang lewat `dofiles/mistargeting.do`
   sebelum mengandalkannya.

4. **Perbandingan PMT vs musyawarah hanya mungkin pada 867 rumah tangga, bukan 5.756.** Sebaran
   sebenarnya: hanya `ranking_PMT` 1.816, hanya `ranking_meeting` 2.922, **punya keduanya 867**,
   tidak punya keduanya 151. Sebabnya desain eksperimen — tiap desa hanya menerima satu perlakuan
   (PMT / COMMUNITY / HYBRID), dan yang punya kedua peringkat hanyalah lengan hibrida. Rencana
   "dua varian label = dua eksperimen" tetap sah pada skala penuh **bila** masing-masing peringkat
   dibandingkan terhadap `poor` berbasis konsumsi (tersedia 5.753); yang berskala 867 adalah
   adu-langsung PMT lawan musyawarah.

5. **`se2_139` bukan dummy kepemilikan** meski labelnya "Non-agricultural land": nilainya
   `{3.0: 5.226, 1.0: 517}` — **sudah dipastikan `1 = Ya`, `3 = Tidak`** (rincian di bagian
   berikutnya). Tulis `(se2_139 == 1)`; menulis `bool(se2_139)` membalik maknanya.
   Bandingkan `se2_138` (lahan pertanian) yang memang 0/1 dengan 2.335 pemilik, dan `se2_125`
   (motor) 0/1 dengan 3.080 pemilik — dua ini kandidat wajar untuk `aset_produktif`.

## Hasil Tier 2 di data ini (14 Agustus 2026)

Varian yang dipakai: **label musyawarah**, `asal_data='publik-musy'`, ablasi 6 fitur
(tanpa `skor_urgensi`, karena sumbernya tanpa teks naratif). n = 3.788 → 3.031 latih / 757 uji,
kebocoran warga 0.

| | Validasi silang 5×5 | Holdout n=757 |
|---|---|---|
| **F1 kelas 'layak'** | 0,5750 ± 0,0250 | 0,6090 |
| Akurasi | 0,6985 ± 0,0189 | 0,7133 ± 0,0322 |
| Recall | 0,6786 | 0,7412 |
| Presisi | — | 0,5168 |
| ROC-AUC | — | 0,7825 |
| Brier | — | 0,1906 |
| Baseline tebak-mayoritas | 0,6988 | — |

Artefak: `tier2-gradient-boosting-seimbang-publik-musy-tanpa-urgensi-v1`.

**Temuan metodologis terpenting: untuk PERTAMA KALINYA di proyek ini pemilihan model menghasilkan
pemenang yang dapat dibedakan secara statistik** — `dapat_dibedakan: true`, unggul 0,0572
melampaui simpangan gabungan 0,0385. Bandingkan dengan riwayatnya:

| Data | Sebaran F1 kandidat | Dapat dibedakan? |
|---|---|---|
| Sintetis (Fase 3) | 0,9128–0,9176, selisih 0,0005 vs simpangan 0,0201 | ❌ |
| Publik, label `poor` (bocor) | keempatnya ±0,94 | ❌ |
| **Publik, label musyawarah** | 0,4590–0,5750 | ✅ |

Ini membenarkan keputusan menunda pemilihan model ke data nyata, dan sekaligus menunjukkan
penyeimbangan kelas benar-benar berpengaruh di sini (GB polos 0,4590 → GB seimbang 0,5750),
padahal pada label yang bocor perbedaannya tenggelam.

**Cara membaca angkanya, dan cara mempertahankannya.** Akurasi 0,713 hanya sedikit di atas
baseline 0,699, tetapi baseline itu menebak "tidak layak" untuk semua orang — tidak berguna bagi
DSS. Yang relevan adalah recall 0,741 pada kelas 'layak' dengan ROC-AUC 0,783: model menemukan
tiga dari empat rumah tangga yang dipilih musyawarah, dari fitur tabular saja. Presisi 0,517
berarti sekitar separuh usulannya tetap perlu diverifikasi petugas — persis peran yang dirancang
untuk sistem ini (FR-26 verifikasi manual), bukan kegagalan.

Angka ini juga harus dibaca berdampingan dengan fakta bahwa **musyawarah warga sendiri hanya
sepakat 66,3% dengan kemiskinan berbasis konsumsi** (n=3.788; silang: 1.905/536/742/605). Artinya
"kebenaran" yang ditiru model memang bukan ukuran objektif, melainkan penilaian manusia — inti
persoalan OI-18, kini dengan angka.

## 🚨 Jebakan keenam — `poor` adalah AMBANG DETERMINISTIK atas `CONSUMPTION`

Ditemukan 13 Agustus 2026, saat melatih Tier 2 di data ini untuk pertama kalinya dan hasilnya
terlihat terlalu bagus.

**`poor == (CONSUMPTION < povline_poor)` pada 99,97% dari 5.753 baris.** Ada enam garis kemiskinan
berbeda (per provinsi × kota/desa: 260,6 · 303,2 · 304,5 · 332,3 · 349,0 · 352,9). Sementara itu
`data_survei.pendapatan` diisi `CONSUMPTION × 1.000` — jadi **labelnya adalah fungsi dari salah
satu fiturnya sendiri.**

Akibatnya terukur:

| Himpunan fitur | F1 | Akurasi |
|---|---|---|
| 6 fitur, **dengan** `pendapatan` | 0,9431 ± 0,0089 | 0,9596 |
| 5 fitur, **tanpa** `pendapatan` | **0,5403 ± 0,0153** | 0,7164 |
| tebak mayoritas | — | 0,6475 |

Angka 0,95 itu bukan kinerja, melainkan model yang memulihkan stratum wilayah dari fitur lain lalu
menerapkan ambang. **Jangan pernah melaporkannya.** Ini kelas kesalahan yang sama dengan akurasi
1,0000 di korpus augmentasi Fase 2, hanya menyamar dalam bentuk baru — dan sekali lagi yang
menyingkapnya bukan tes hijau, melainkan mencurigai angka yang kelewat bagus.

Dua jalan keluar yang sah, dan keduanya perlu keputusan sadar:

1. **Buang `pendapatan` dari fitur** → tugasnya menjadi PMT yang sesungguhnya: menduga kemiskinan
   dari aset, kondisi rumah, dan demografi. Persis yang dikerjakan paper aslinya. F1 0,54 dengan
   akurasi 0,716 di atas baseline 0,648 adalah **sinyal nyata yang sederhana**, dan sejalan dengan
   temuan pustaka bahwa PMT memang jauh dari sempurna.
2. **Ganti labelnya** ke `ranking_meeting` (penilaian musyawarah warga), yang tidak diturunkan dari
   konsumsi. Ini varian yang menjawab OI-18 — tetapi ingat batasan n=867 untuk adu-langsung.

Yang TIDAK sah: memakai konfigurasi 6 fitur apa adanya dan menuliskan 0,95 ke skripsi.

## Jawaban atas tiga pertanyaan terbuka (ditelusuri 13 Agustus 2026)

`Codebooks.zip` **tidak ikut terekstrak** — yang ada hanya `questionnaires.zip` (= `Surveys.zip`)
dan `ReadMe.pdf`. Ketiganya tetap terjawab dari sumber yang lebih otoritatif: kode Stata yang
membentuk variabelnya, di `dofiles/Coding_files/coding_baseline.do`.

### 1. `se2_139` — sudah jelas, dan memang bukan dummy

```stata
coding_baseline.do:340   rename hr01e se2_139        // salinan mentah, TIDAK di-recode
coding_baseline.do:342   gen se2_138 = (hr01a==1 | hr01b==1 | hr01c==1)   // ini baru dummy
coding_baseline.do:344   recode house (3 8=0)        // `house` di-recode, se2_139 tidak
```

Asalnya `hh_hr1.dta`, pertanyaan `hr01` = **"Apakah rumah tangga ini memiliki saat ini?"** dengan
label nilai `1 = Ya`, `3 = Tidak`, `8 = tidak tahu`, `9 = missing` (8/9 sudah dijadikan kosong).

→ **`aset_produktif` dari `se2_139` harus ditulis `(se2_139 == 1)`, bukan `bool(se2_139)`.**
Menulis `bool()` membalik maknanya: 5.226 rumah tangga yang **tidak** memiliki lahan justru
tercatat memiliki. Kandidat yang aman dan sudah biner: `se2_138` (lahan pertanian, 2.335 pemilik)
dan `se2_125` (motor, 3.080 pemilik).

### 2. Satuan & tahun konsumsi — terkonfirmasi dari rumusnya

```stata
coding_baseline.do:55   gen hhconsumption = mfood + mnonfood
coding_baseline.do:71   gen CONSUMPTION = (hhconsumption/hhsize)/1000
```

→ Konsumsi (pangan + non-pangan) per kapita per bulan, **dibagi 1.000**, dalam **rupiah nominal
2008**; tidak ada deflator apa pun di kode replikasi. Untuk `data_survei.pendapatan`:
**× 1.000**, lalu deflasi sendiri ke tahun rujukan dan catat faktornya di skripsi.

### 3. `riwayat_bantuan` — sumbernya ADA, dan cocok sempurna

`data/baseline/hh_ksr2.dta` (11.512 × 13), kolom **`ksr04`** = *"Apakah rumah tangga ini menerima
PKPS BBM-SLT/BLT?"* — label nilai `1 = Ya (ada nomor kartu)`, `2 = Ya (tanpa kartu)`, `3 = Tidak`.
Kolom `ksr2type` memisahkan tahun: `a` = 2005, `b` = 2008, masing-masing 5.756 baris.

**Irisan `hhid` dengan berkas fitur: 5.756 / 5.756 — sempurna, tanpa kehilangan baris.**

| Gelombang | Menerima | Tidak | Tidak tahu/kosong |
|---|---|---|---|
| BLT 2005 (`ksr2type=='a'`) | 1.397 (24,3%) | 4.359 | 0 |
| BLT 2008 (`ksr2type=='b'`) | 1.701 (29,6%) | 4.055 | 0 |

→ `riwayat_bantuan = ksr04.isin([1, 2])`. **Pakai gelombang 2005**: ia mendahului eksperimen 2008
sehingga bebas dari kekhawatiran kebocoran sepenuhnya.

Silang dengan label kemiskinan menunjukkan sinyal yang nyata tapi jauh dari deterministik —
persis yang hilang dari data sintetis:

| | `poor`=0 | `poor`=1 | % miskin |
|---|---|---|---|
| tidak pernah BLT 2005 | 3.121 | 1.235 | 28,3% |
| pernah BLT 2005 | 604 | 793 | **56,8%** |

⚠️ **Jangan pakai `RTS` sebagai fitur masukan** — itu hasil pembagian Rp 30.000 dari eksperimennya
sendiri, memakainya akan membocorkan label.

## Manifes berkas

Arsip Dataverse versi 5 berjumlah tujuh berkas, total ±33,4 MB terkompresi
(`Codebooks.zip` 0,12 · `ReadMe.docx` 0,01 · `Coded Data.zip` 11,75 · `Data.zip` 16,54 ·
`Surveys.zip` 3,70 · `Replication Files.zip` 0,09 · `Output.zip` 1,23 MB).

**Yang tersimpan di sini adalah hasil ekstraknya**, 360 berkas / ±169 MB, tercatat lengkap di
[`MANIFES.sha256`](MANIFES.sha256). Direktori `raw/` sengaja dibiarkan kosong (arsip `.zip` asli
tidak disimpan); bila kelak arsipnya diunduh ulang, taruh di sana dan perbarui manifes.

```bash
# verifikasi seluruh 360 berkas
cd data/public/alatas2012 && sha256sum -c MANIFES.sha256

# buat ulang manifes setelah menambah/mengganti berkas
find Targeting_Indonesia LICENSE.txt -type f | sort | xargs sha256sum > MANIFES.sha256
```

`questionnaires.zip` di dalam `Targeting_Indonesia/` masih terkompresi — ekstrak bila perlu
menelusuri pertanyaan survei asal sebuah variabel.

## Kenapa dataset ini yang dipilih

1. **Sulawesi Selatan termasuk cakupan** — provinsi yang sama dengan Bontoramba, Jeneponto.
2. **Masalahnya identik dengan yang di-otomatiskan DSS ini**: PMT berbasis fitur tabular versus
   penilaian manusia sedesa. Itu persis Tier 2 versus penilaian petugas kelurahan.
3. **Punya dua label kebenaran sekaligus** — konsumsi per kapita (garis PPP$2) *dan* peringkat
   komunitas. Ini yang membuat **OI-18 (sirkularitas: model dilatih pada keputusan petugas lalu
   dinilai petugas) dapat diukur, bukan sekadar ditulis sebagai keterbatasan.** Temuan asli
   papernya: komunitas memakai konsep kemiskinan yang berbeda dari konsumsi.
4. Menggantikan angka Fase 3 yang sudah terbukti tak bermakna — keempat kandidat RF/GB memberi
   F1 0,9128–0,9176 di data sintetis, selisih dua teratas 0,0005 vs simpangan gabungan 0,0201.

## Batasan yang wajib ditulis di skripsi

- **Data 2008.** `data_survei.pendapatan` bersatuan rupiah per kapita per bulan; angka Alatas
  adalah **konsumsi**, bukan pendapatan, dalam rupiah 2008. Harus dideflasi atau dinyatakan
  eksplisit. Jangan dimasukkan mentah-mentah.
- **Tidak ada teks naratif** → tidak ada `skor_urgensi`. Run Tier 2 di data ini adalah **ablasi
  6 fitur, bukan pipeline penuh.** `ml/tier2/dataset.py` menuntut skor urgensi per pengajuan;
  tanpa `TeksNaratif` seluruh baris jatuh ke `lewat["tanpa_skor_urgensi"]` dan ekspor berhenti.
  Butuh mode eksplisit (mis. `--tanpa-urgensi`) yang menandai ketiadaan fitur itu sampai ke
  `metadata.json` artefak. **Jangan mengisi `skor_urgensi = 0.5` diam-diam** — itu kelas bug
  "nilai tier hulu salah dipakai tanpa ketahuan sementara tes tetap hijau" yang sudah tiga kali
  menggigit proyek ini, dan satu-satunya yang pernah menyingkapnya adalah penanda versi.
- Konteks perdesaan/perkotaan tiga provinsi ≠ Bontoramba. Hasilnya *proof-of-concept*; klaim
  final tetap menunggu data lokal (Fase 6).

## Langkah berikutnya setelah arsip ada

~~1. Inventarisasi variabel~~ — **selesai 13 Agustus 2026**, hasilnya ada di bagian
[Peta isi](#peta-isi-hasil-inventarisasi-13-agustus-2026) dan
[Lima jebakan](#️-lima-jebakan-yang-sudah-terverifikasi--baca-sebelum-menulis-skrip-harmonisasi)
di atas.

~~2. Buka `Codebooks/`~~ — **selesai**. `Codebooks.zip` tidak ikut terekstrak, tapi ketiga
pertanyaan (pengkodean `se2_139`, satuan/tahun konsumsi, sumber `riwayat_bantuan`) sudah terjawab
dari `dofiles/Coding_files/coding_baseline.do` — lihat bagian
[Jawaban atas tiga pertanyaan terbuka](#jawaban-atas-tiga-pertanyaan-terbuka-ditelusuri-13-agustus-2026).
**Tidak ada lagi yang memblokir penulisan skrip harmonisasi.**

3. Petakan ke skema `data_survei`. Nilai kategorikal rumah **harus** memakai kosakata persis di
   `app/services/features.py` (`tanah`/`kayu`/`semen`/`keramik`; `bambu`/`kayu`/`seng`/`tembok`;
   `sungai`/`sumur`/`pdam`) — nilai tak dikenal diam-diam menjadi `0.5`. Sumbernya biner, jadi
   pemetaannya kasar (`tfloor=0 → "tanah"`, `tfloor=1 → "semen"` dan seterusnya); catat sebagai
   keterbatasan.
4. Seed ke basis data dengan `asal_data='publik'`, lalu:
   ```powershell
   python -m ml.tier2.dataset --outdir data/corpus --asal-data publik
   ```
   Ingat penghadang `skor_urgensi` di bagian Batasan — ekspor akan berhenti sebelum menulis
   apa pun bila mode tanpa-urgensi belum ada.
5. Latih ulang Tier 2 dengan *repeated stratified k-fold*; laporkan tiga kolom berdampingan:
   sintetis / publik-`poor` / publik-`ranking_meeting`. Ingat: adu-langsung PMT lawan musyawarah
   hanya n=867.
