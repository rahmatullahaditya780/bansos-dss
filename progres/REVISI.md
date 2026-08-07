# Catatan Revisi — DSS Bansos Bontoramba

Log kronologis setiap perubahan penting di tengah pengembangan (**terbaru di atas**).
Format tiap entri: `tanggal — fase — ringkasan perubahan (alasan)`.

Gunakan berkas ini untuk mencatat: keputusan teknis yang diambil, penyimpangan dari rencana/TRD,
perbaikan bug penting, penggantian pustaka/versi, dan hasil pengujian yang mengubah arah.

---

## 2026-08-07 — Gerbang Fase 4: evaluasi lintas-fase + probe pra-Fase 4 (rancangan Tier 3 terkunci)

**Dikerjakan:** [evaluasi pra-Fase 4](evaluasi-pra-fase-4.md) atas Fase 0–3, verifikasi pemasangan
artefak kedua tier lewat `info_model()` (keduanya asli, `fallback_aktif=False`), 48 tes lulus, dan
[`probe_fuzzy_topsis.py`](fase-4-tier3-fuzzy-topsis/probe_fuzzy_topsis.py) atas **991 alternatif
nyata** (batch OI-15 sungguhan: pengajuan yang diloloskan Tier 2, skor urgensi dari IndoBERT).
Belum ada kode Tier 3 yang ditulis — probe sengaja dijalankan lebih dulu, meniru pola Fase 3 yang
berhasil meramalkan RF vs GB tidak dapat dipilih.

**Temuan 1 — `skor_urgensi` tersaturasi (BARU, berdampak lintas-tier).** Hanya **5 nilai berbeda**
pada 991 alternatif; 105 di 0,0002, 886 di ≥0,9939, tidak ada di antaranya. Penyebabnya konsekuensi
langsung korpus Fase 2 yang terpisah sempurna: margin logit membentang −8,6…+8,7 (resolusi
berlimpah), tetapi softmax meremasnya jadi dua titik. Untuk Tier 2 tidak fatal (pohon hanya butuh
urutan); untuk Tier 3 fatal, karena kriteria berbobot **0,25** ini bekerja sebagai saklar biner.
Ini membatalkan sebagian anggapan OI-02 bahwa "probabilitas otomatis menjadi skor kontinu".
**Butuh keputusan** — rekomendasi: pakai margin logit sebagai nilai crisp kriteria urgensi.

**Temuan 2 — kuantisasi linguistik polos ditolak.** Bentuk Fuzzy TOPSIS yang paling lazim ditulis di
skripsi (petakan nilai ke satu himpunan linguistik) memeras 991 alternatif jadi 81 nilai preferensi
dan menyeret **25 dari 50 kursi kuota ke posisi seri** — setengah daftar penerima ditentukan urutan
baris basis data. Varian **derajat keanggotaan penuh** (nilai tidak dipaksa ke satu himpunan)
menghasilkan 550 nilai berbeda dan **nol seri di garis kuota** dengan fungsi keanggotaan yang sama.
**Rancangan Fase 4 memakai varian keanggotaan.**

**Temuan 3 — 42% "efek fuzzy" bukan efek fuzzy.** Kontrol dengan TFN berlebar nol (l=m=u) sudah
menggeser 42% daftar top-50 terhadap TOPSIS crisp. Selisih itu berasal dari rumusan Chen (2000)
(solusi ideal mutlak) vs stub Fase 0 (maksimum teramati), bukan dari fuzzifikasi. Kefuzzian sendiri
hanya menggeser 26%. **Kontrol `degenerat` wajib ikut dilaporkan** agar bab hasil tidak salah
atribusi.

**Temuan 4 — bobot provisional bukan risiko dominan, dan fuzzy menstabilkan.** Perturbasi bobot ±20%
hanya menggeser 3–7% kursi top-50. Varian fuzzy lebih stabil daripada crisp (97–98% vs 93%), dan
peringkat-1 crisp berpindah pada 32% perturbasi ±50% sementara varian fuzzy tidak pernah. Ini
**argumen substantif pertama untuk memakai fuzzy sama sekali**, dan sah dilaporkan sekalipun datanya
sintetis karena yang diukur sifat metode, bukan ketepatan terhadap kebenaran.

**Temuan 5 — seri sejati ada, dan stub memproduksi seri tambahan.** 6,1% alternatif punya vektor
kriteria persis kembar (grup terbesar 10) — tidak dapat dihapus metode apa pun, perlu aturan tiebreak
tercatat. Terpisah dari itu, `tier3_topsis.py:65` membulatkan nilai preferensi ke 4 desimal *sebelum*
mengurutkan, sehingga grup seri terbesarnya 14 padahal kembar sejati hanya 10. **Fase 4 mengurutkan
pada presisi penuh, membulatkan hanya untuk tampilan.**

**Perbedaan penting dari Fase 3:** Tier 3 tidak punya label kebenaran, sehingga akurasi tidak akan
pernah dapat dilaporkan untuknya — di data sintetis maupun lokal. Yang dapat divalidasi hanya
kebenaran aritmetik (perhitungan manual) dan sifat metode (sensitivitas, atribusi). **Keduanya tidak
butuh data lokal**, jadi Fase 4 adalah fase Jalur A pertama sejak Fase 0 yang dapat ditutup tanpa
menulis "menunggu data lokal" di kolom hasilnya.

**Tertunggak (kedua kalinya dicatat):** riwayat git masih di `43fecd6`; hasil Fase 1, 2, dan 3 masih
untracked/modified. Tiga fase penuh tanpa cadangan.

---

## 2026-08-07 — Fase 3: Tier 2 klasifikasi kelayakan (kode SELESAI, model final menunggu data lokal)

**Dibangun:** paket `ml/tier2/` (skema fitur, ekspor+split, latih+banding, evaluasi, inference),
`app/services/tier2_ml.py` ditulis ulang jadi pembungkus tipis, 18 tes Tier 2. Stub logistik Fase 0
DIGANTI inference Random Forest — kontrak `predict_eligibility()` tidak berubah, sehingga
`pipeline.py` **tidak disentuh sama sekali** (taruhan kerangka tipis Fase 0 terbayar untuk kedua
kalinya). Tes: **48 lulus** (sebelumnya 30).

**Hasil (asal data sintetis, 2.020 pengajuan / 2.000 warga, kebocoran 0):** validasi silang 5×5
memberi F1 kelas `layak` 0,9128–0,9176 untuk keempat kandidat — **selisih dua teratas 0,0005
berbanding simpangan gabungan 0,0201**. Persis seperti ramalan probe: keempatnya tidak dapat
dibedakan. Prosedur pemilihan mendeteksi sendiri, menulis `dapat_dibedakan: false` ke metadata, dan
memutus lewat recall kelas `layak` → `random_forest`. Holdout: akurasi 0,9012 ± 0,0291, ROC-AUC
0,9670, Brier 0,0718, TN 189 · FP 17 · FN 23 · TP 176 — di dalam selang kepercayaannya sendiri
terhadap langit-langit oracle 0,9252.

**Temuan dari analisis FP/FN:** 40 kasus salah **tidak punya ciri apa pun** — median pendapatan,
housing_need, dan skor_urgensi-nya praktis sama dengan median seluruh data uji — dan 24 dari 40
terjadi pada probabilitas yang percaya diri (di luar 0,3–0,7). Itu tanda **label yang salah, bukan
model yang lemah**: derau `U(-0,15; 0,15)` generator membalik sebagian label. Konfirmasi ketiga bahwa
data sintetis sudah habis daya diagnostiknya; berhenti mengoptimalkan di sini.

**Keputusan teknis:**
- **Pemilihan model memakai repeated stratified group k-fold (5×5)**, holdout 80:20 tetap dilaporkan
  demi kepatuhan TRD. Aturan putusan: F1 kelas `layak`; bila selisih < simpangan gabungan, kandidat
  dinyatakan tidak dapat dibedakan dan penentunya recall kelas `layak` (FN = warga layak yang
  ditolak; FP masih tersaring verifikasi manual). Alasan putusan ikut ditulis ke `metadata.json`.
- **Lipatan CV dikelompokkan per warga**, sama seperti split latih/uji — kalau tidak, kebocoran yang
  sudah dicegah `dataset.py` masuk lagi lewat pintu belakang.
- **Urutan fitur dikunci di artefak & diverifikasi saat pemuatan.** Model sklearn menerima array
  polos tanpa nama kolom, jadi urutan yang bergeser salah secara *senyap*; `periksa_skema`
  mengubahnya jadi kegagalan berisik yang jatuh ke fallback.
- **Permutation importance, bukan impurity importance** — diukur di data uji, tidak bias ke fitur
  berkardinalitas tinggi.
- **Brier score dilaporkan** karena `probabilitas` tampil ke petugas dan probabilitas Random Forest
  (rerata voting) terkenal tidak terkalibrasi. Kalibrasi ditunda ke Fase 6.
- **Fallback `stub-logistik-fallback-v0`** meniru pola Tier 1: hasil non-model selalu dapat dipisahkan.
- Artefak jadi direktori `ml/artifacts/tier2/`; `ml_model_path` diubah dari
  `ml/artifacts/classifier.joblib`. Versi scikit-learn dicatat & diperiksa (joblib rapuh lintas versi).

**Dua bug integrasi yang terungkap saat verifikasi end-to-end (sudah diperbaiki):**
1. **`.env` lokal menimpa `ml_model_path`** dengan nilai lama, sehingga aplikasi diam-diam tetap
   memakai fallback meski artefak sudah ada — **dan seluruh tes tetap hijau**, karena tes kontrak
   hanya memeriksa bentuk keluaran. Yang menyingkapnya adalah penanda `versi_model`, bukan tes.
   Memperbarui `.env.example` saja tidak cukup.
2. **`info()` melaporkan `fallback_aktif: false` sebelum pemuatan pertama** — kebalikan dari yang
   ingin diketahui pemanggilnya. Kini `info()` memaksa percobaan muat. `ml/tier1/infer.py` masih
   berperilaku lama (di luar cakupan Fase 3, dicatat di README Fase 3).

**Belum dikerjakan:** generator sintetis v2 (butir opsional — menguji bahwa prosedur CV sanggup
mendeteksi perbedaan ketika perbedaan itu ada), pelatihan versi `lokal`, dan protokol validasi label
historis (OI-10). Ketiganya menunggu Fase 1/6.

---

## 2026-08-07 — Pra-Fase 3: evaluasi lintas-fase & rencana kerja Tier 2

**Dibangun:** [`progres/evaluasi-pra-fase-3.md`](evaluasi-pra-fase-3.md) (tinjauan Fase 0–2),
[`probe_kelayakan_sintetis.py`](fase-3-tier2-ml/probe_kelayakan_sintetis.py), dan penulisan ulang
[README Fase 3](fase-3-tier2-ml/README.md) menjadi rencana kerja lengkap. Tes ulang: **30 lulus**.

**Temuan pokok — probe dijalankan SEBELUM kode Tier 2 ditulis.** Di atas data sintetis (n=3.000):
RF 0,9117 · GB 0,9167 · **oracle yang mengetahui faktor laten `k` persis hanya 0,9252**. Selisih RF vs
GB 0,0050 berbanding galat baku 0,0113 — empat kali lebih kecil daripada ketidakpastiannya sendiri.
**Data sintetis tidak sanggup memilih pemenang RF vs GB**, padahal itu deliverable inti Fase 3. Ini
pengulangan pelajaran Fase 2 dengan wajah berbeda: angka ~91% yang tampak wajar sama tak bermaknanya
dengan angka 100% yang mencurigakan. Batas ini kini ditulis **sebelum** pelatihan, bukan sesudah.

**Temuan lain yang mengubah rencana:**
- *Feature importance sintetis adalah artefak generator.* GB menaruh 79,1% bobot pada `skor_urgensi`,
  RF membaginya rata bertiga — dua cerita berbeda dari data yang sama, karena `label_urgensi` dan
  `label_historis` sama-sama turunan `k`. Tidak boleh masuk skripsi dalam bentuk apa pun.
- *Sirkularitas OI-18.* Tier 2 dilatih pada keputusan petugas masa lalu, lalu dinilai terhadap
  verifikasi manual petugas. Mitigasi: jalankan protokol validasi label historis (OI-10) **sebelum**
  pelatihan final, dan tulis sirkularitasnya sebagai keterbatasan eksplisit.
- *Split 80:20 tidak memadai untuk memilih model.* Pada target ≥100 KK lokal, data uji ~20 baris →
  selang kepercayaan akurasi ±15,6 poin persen. **Keputusan: pemilihan model digerakkan oleh repeated
  stratified k-fold**, holdout 80:20 tetap dilaporkan demi kepatuhan TRD.
- *Kebocoran split harus dikelompokkan per warga*, bukan per baris — satu warga dapat mengajukan lebih
  dari sekali (setara pelajaran grup teks di Tier 1).

**Keputusan sumber data (opsi A):** kode Tier 2 dibangun di atas data sintetis sekarang, proxy publik
dikejar paralel di Jalur B, pemilihan model ditunda ke data lokal (Fase 6). Alasan sama dengan Fase 2 —
Fase 3 tidak boleh memblokir Fase 4/5.

**Catatan kebersihan repo:** riwayat git berhenti di `43fecd6`; seluruh hasil Fase 1 & 2 (`ml/tier1/`,
notebook Colab, rubrik, perkakas kappa, `tests/test_tier1.py`) masih untracked/modified. Commit
sebelum kode Fase 3 ditulis, agar diff Tier 2 terbaca terpisah.

**Yang diperiksa dan ternyata bukan masalah:** semantik `pendapatan` konsisten sebagai *per kapita per
bulan* di seluruh lapisan (skema DB, `PengajuanCreate`, label formulir, ambang `fuzzy_config.yaml`,
generator sintetis) — tidak ada ketidakcocokan satuan yang perlu ditambal sebelum Tier 2.

---

## 2026-08-06 — Fase 1: Rubrik pelabelan (OI-11) & protokol validasi label historis (OI-10)

**Dibangun:** dua dokumen kerja di `progres/fase-1-data-pelabelan/`, masing-masing dalam Markdown +
PDF dari satu sumber konten (`doc_render.py` → blok konten, dua perender — mencegah kedua format
melenceng saat rubrik diamandemen):

- **`rubrik-pelabelan-urgensi`** (6 halaman) — 7 aturan dasar, 8 indikator TINGGI, 19 kasus batas,
  25 contoh terkalibrasi, prosedur 6 tahap dengan ambang Cohen's kappa ≥ 0,61, kewajiban anonimisasi,
  dan tabel riwayat amandemen.
- **`protokol-validasi-label-historis`** (3 halaman) — prosedur sesi bersama petugas kelurahan:
  sampel 30–50 KK, penilaian TEPAT/TIDAK TEPAT/TIDAK TAHU, aturan koreksi tanpa menimpa label asli,
  dan tindak lanjut menurut tingkat kekeliruan.

**Keputusan teknis:**
- Pelabel = peneliti + rekan mahasiswa (bukan petugas) → rubrik ditulis tanpa istilah ML sama sekali,
  bertumpu pada contoh terkalibrasi, dan **mewajibkan anonimisasi** teks sebelum dibagikan karena
  pelabel dari luar kelurahan bukan pihak berwenang atas data warga.
- Opsi ketiga `TIDAK DAPAT DINILAI` ditambahkan sebagai kategori **proses**, bukan kelas model —
  teks administratif dikeluarkan dari dataset, tidak dipaksa menjadi `rendah` (mencegah label sampah).
- Aturan R5 ("jangan menyimpulkan yang tidak tertulis") dijadikan aturan emas dengan pasangan contoh
  12/13 yang kalimatnya nyaris identik tetapi labelnya berbeda.

**Temuan penting — uji silang rubrik vs model:** 24 contoh terkalibrasi dijalankan lewat
`uji_silang_rubrik.py` terhadap `indobert-p1-augmentasi-v1`. Hasil **87,5% (21/24)**, berbanding
100% pada data uji template. Ketiga kesalahan mengungkap celah nyata korpus augmentasi
(ketidakberdayaan yang tersirat; variasi ungkapan "sudah teratasi"; putus sekolah bukan karena biaya).
Rincian di `progres/fase-2-tier1-indobert/README.md`.

**Tindak lanjut (2026-08-07):** ketiga celah ditambal dan model dilatih ulang dua kali —
`indobert-p1-augmentasi-v2` lalu `v3`. Uji kalimat manusia: v1 87,5% → v2 95,8% → v3 95,8%,
sementara uji template tetap 100% di ketiganya. **Kegagalan berpindah, bukan berkurang:** v2
menciptakan jalan pintas "sudah … sekarang … = sudah selesai" (merusak #10 yang v1 sudah benar);
v3 menutupnya tetapi merusak #13 ("Kepala keluarga penderita diabetes." → TINGGI), yang v1 dan v2
benar. Penyebabnya ketegangan nyata antar aturan rubrik: ketidakberdayaan tersirat harus dihitung
(#6), tetapi sebutan diagnosis tanpa dampak tidak (#13, aturan R5).

**Perangkat pelabelan (2026-08-07):** `buat_lembar_kerja.py` (lembar Excel per pelabel — dropdown
label, sheet rujukan cepat, sheet petunjuk) dan `hitung_kappa.py` (Cohen's kappa + tafsir Landis &
Koch + putusan terhadap ambang 0,61 + ekspor `ketidaksepakatan.xlsx` siap adjudikasi). Baris
`tidak_dapat_dinilai` sengaja dikeluarkan dari perhitungan kappa — ia penanda proses, bukan kelas
model, dan memasukkannya akan menaikkan kappa secara semu. Lembar berisi narasi warga ditambahkan
ke `.gitignore`.

**Rubrik v1.1 (2026-08-07):** ditambahkan asas **"keterbatasan fungsi, bukan sebutan"** pada Bagian 3
beserta tiga kasus batas baru. Pemicunya temuan uji silang: batas antara contoh 6 (keterbatasan
tersirat → TINGGI) dan contoh 13 (sebutan diagnosis tanpa dampak → RENDAH) belum tertulis tegas,
padahal keduanya bertetangga dekat — ketegangan yang sama persis membuat model v3 gagal pada #13.
Ditegaskan pula bahwa penanda waktu ("sudah", "sekarang") tidak menentukan label.

**Keputusan: berhenti menyetel korpus terhadap 24 kalimat uji** — iterasi berikutnya menjadi
pengepasan terhadap set uji sendiri. Tindak lanjut yang benar: amandemen rubrik (pertajam batas
"keterbatasan fungsi" vs "sebutan diagnosis"), perbesar set uji jujur ke ≥70 kalimat, lalu fine-tune
versi `lokal` di Fase 6. Ditambahkan tes regresi korpus agar keempat kategori kasus sulit dan
keseimbangan penanda waktu antar kelas tidak hilang tanpa sengaja.

---

## 2026-08-06 — Fase 2: Tier 1 IndoBERT (kode SELESAI, model final menunggu data lokal)

**Dibangun:** paket `ml/tier1/` (preprocessing FR-11, pembangkit korpus, split 80:20 anti-kebocoran,
fine-tuning, evaluasi, inference), notebook Colab GPU, 17 tes Tier 1. Stub heuristik Fase 0 di
`app/services/tier1_nlp.py` DIGANTI inference IndoBERT — kontrak `score_urgency()` tidak berubah,
sehingga `pipeline.py` hanya perlu satu penyesuaian (skoring batch).

**Penyimpangan/keputusan teknis:**
- **Data latih Fase 2 = korpus augmentasi buatan**, bukan dataset publik siap pakai. Alasan: teks
  lokal berlabel belum ada (Fase 1 berjalan) dan dataset publik berbahasa Indonesia untuk *urgensi
  sosial* tidak tersedia sepadan — IndoNLU tidak memuat tugas ini. Korpus dirancang memuat ±32%
  *hard negative* (kata urgen dalam konteks negasi) dan *hard positive* (urgen tanpa kata kunci)
  agar model tidak sekadar mencocokkan kata kunci. **Metrik atasnya hanya memvalidasi pipeline,
  bukan klaim skripsi** — klaim final diambil dari versi `lokal` di Fase 6.
- **Loop PyTorch biasa, bukan `Trainer` HuggingFace.** Menghindari dependensi `accelerate` dan
  menjamin kode yang jalan di CPU lokal identik dengan di Colab GPU.
- **Stemming/stopword removal TIDAK dipakai di jalur BERT** (tetap tersedia untuk baseline non-BERT):
  subword tokenizer memerlukan kata utuh, dan stopword negasi ("tidak ada yang sakit") justru
  penentu label.
- **Fallback heuristik dipertahankan + ditandai.** Bila artefak tak ada, `versi_model` ditulis
  `heuristik-fallback-v0` ke `skor_urgensi.versi_model` agar hasil non-model tak pernah tercampur
  dengan hasil model saat analisis.
- **Pelatihan lokal 2 epoch, bukan 3** (rencana tetap 3 epoch di Colab GPU). Alasan: CPU lokal
  ±21 detik/step → 3 epoch ≈ 2,3 jam. Run lokal hanya memvalidasi pipeline.

**Dependensi:** `requirements-ml.txt` terpasang. Versi aktual jauh lebih baru dari batas bawah:
torch 2.13.0+cpu, transformers 5.14.1, scikit-learn 1.7.2, numpy 1.26.4. Tidak ada masalah
kompatibilitas; `GradScaler` dipindah ke `torch.amp` dengan fallback ke `torch.cuda.amp` untuk
torch lama (Colab).

**Perubahan lain:** `pipeline.py` memakai `score_urgency_batch()` (satu forward pass per pengajuan,
mendukung NFR-01 ≤5 detik); `config.py` menambah `indobert_max_length`; `.gitignore` mengecualikan
`data/corpus/*.csv` (reproducible dari seed).

---

## 2026-08-06 — Fase 0: Kerangka Integrasi Tipis (SELESAI)

**Dibangun:** proyek FastAPI greenfield di `bansos-dss/`, pipeline 3-tier end-to-end dengan tier stub,
skema DB TRD 6.4 + Alembic, autentikasi JWT+cookie & RBAC, 10 endpoint REST (TRD Bab 8), dashboard
Jinja2/Bootstrap/HTMX, generator data simulasi, 11 tes blackbox (lulus). Commit awal `f491dec`.

**Penyimpangan/keputusan teknis (vs TRD, reversibel):**
- **Database dev = SQLite**, bukan PostgreSQL. Alasan: Docker belum terpasang di mesin pengembangan.
  `DATABASE_URL` dibuat konfigurabel; PostgreSQL tetap dipakai di jalur Docker (`docker-compose.yml`).
  Model SQLAlchemy dijaga DB-agnostik.
- **Hashing password = pbkdf2_sha256**, bukan bcrypt. Alasan: passlib 1.7.4 tidak kompatibel dengan
  bcrypt 5.x (error `__about__` + batas 72 byte). pbkdf2_sha256 murni-Python, stabil, tetap aman.
- **Skor urgensi = probabilitas kelas 'tinggi' (0–1)**, bukan skala 1–10 di contoh TRD Bab 8.
  Konsekuensi keputusan OI-02 (label biner). Konsisten dengan rencana.

**Perbaikan bug saat integrasi:**
- `models.py`: `Column` belum diimpor dari SQLAlchemy → ditambahkan.
- `web.py`: signature `Jinja2Templates.TemplateResponse` di Starlette 1.4.x berubah jadi
  `(request, name, context)` → seluruh pemanggilan disesuaikan.
- `analisis.py`: rute statis `POST /analisis/ranking` tertangkap oleh `POST /analisis/{pengajuan_id}`
  → rute statis dipindah agar terdaftar lebih dulu.
- Secret key dev diperpanjang ≥32 byte (menghindari peringatan HMAC PyJWT).

**Dependensi:** ML berat (torch/transformers/scikit-fuzzy) dipisah ke `requirements-ml.txt` — belum
dipasang; hanya diperlukan mulai Fase 2.
