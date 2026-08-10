# DSS Bansos — Kelurahan Bontoramba

Decision Support System penentuan kelayakan & prioritas penerima bantuan sosial.
Pipeline tiga tingkat: **Tier 1** IndoBERT (skor urgensi) → **Tier 2** klasifikasi ML (layak/tidak) →
**Tier 3** Fuzzy TOPSIS (perangkingan prioritas), disajikan di dashboard web FastAPI.

Turunan teknis dari `../TRD.md`. Lihat rencana tahapan di
`C:\Users\adity\.claude\plans\berdasarkan-trd-pada-direktori-vectorized-bee.md`.

## Status

**Fase 4 — ketiga tier asli, tidak ada lagi stub.** Skor urgensi dari **IndoBERT hasil fine-tuning**
(Fase 2), kelayakan dari **Random Forest** hasil perbandingan RF vs Gradient Boosting (Fase 3), dan
perangkingan dari **Fuzzy TOPSIS Chen (2000)** dengan fungsi keanggotaan yang dikonfigurasi (Fase 4).

Batas klaim, dan ia berbeda per tier. Tier 1 & 2 masih dilatih di data sintetis/augmentasi —
**metriknya memvalidasi pipa, bukan klaim skripsi**; angka final menunggu data lokal (Fase 6).
Tier 3 tidak punya label kebenaran sama sekali, sehingga **akurasi tidak akan pernah dilaporkan
untuknya**: yang divalidasi adalah kebenaran aritmetik (perhitungan manual) dan sifat metode
(sensitivitas bobot, atribusi) — keduanya sudah tuntas.

Rincian per fase: [`progres/`](progres/) · tinjauan lintas-fase:
[`evaluasi-pra-fase-3.md`](progres/evaluasi-pra-fase-3.md) ·
[`evaluasi-pra-fase-4.md`](progres/evaluasi-pra-fase-4.md).

## Menjalankan (dev lokal, tanpa Docker)

Prasyarat: Python 3.10.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env          # default DATABASE_URL = SQLite
alembic upgrade head            # buat skema database
python -m data.synthetic.seed   # isi data simulasi + akun petugas demo
uvicorn app.main:app --reload
```

Buka http://127.0.0.1:8000 (dashboard) atau http://127.0.0.1:8000/docs (Swagger).
Akun demo: **petugas / petugas123**.

> **Startup sengaja memakan ~10–15 detik.** Artefak Tier 1 & Tier 2 dimuat lebih dulu
> (`panaskan_model_saat_start`, bawaan `true`), supaya bukan petugas pertama yang menanggung biaya
> pemuatan model: tanpa pemanasan, permintaan analisis pertama terukur **10.182 ms**, sesudahnya
> **213 ms**. Tunggu baris `Application startup complete` sebelum membuka halaman.
> Untuk iterasi cepat, matikan lewat `PANASKAN_MODEL_SAAT_START=false` di `.env`.
>
> **Tidak butuh internet.** Seluruh aset antarmuka dilayani dari `app/static/vendor/`.

## Menjalankan (Docker, PostgreSQL)

```bash
docker compose up --build
```

API di http://localhost:8000. Skema dibuat otomatis (`alembic upgrade head`).

## Struktur

| Path | Isi |
|---|---|
| `app/core` | Konfigurasi & keamanan (hash password, JWT, RBAC) |
| `app/db` | Model SQLAlchemy (skema TRD 6.4) + migrasi Alembic |
| `app/api/routes` | Endpoint REST (TRD Bab 8) |
| `app/services` | Logika tiap tier (ketiganya asli) + generator alasan + metrik |
| `app/templates` | Dashboard Jinja2 + Bootstrap 5 + HTMX |
| `app/static/vendor` | Aset pihak ketiga **dilayani lokal** (lihat di bawah) — dashboard tidak butuh internet |
| `ml/tier1` | Preprocessing, korpus, pelatihan, evaluasi & inference IndoBERT (Tier 1) |
| `ml/tier2` | Skema fitur, ekspor+split, latih & banding RF/GB, evaluasi, inference (Tier 2) |
| `ml/tier3` | Fungsi keanggotaan, Fuzzy TOPSIS, TOPSIS crisp cadangan, sensitivitas (Tier 3) |
| `ml/artifacts` | Artefak model terlatih (tidak di-commit — lihat `.gitignore`) |
| `config/fuzzy_config.yaml` | Bobot kriteria, arah, fungsi keanggotaan (OI-13) & aturan tiebreak |
| `data/synthetic` | Generator data simulasi + skrip seed |
| `data/corpus` | Korpus teks berlabel urgensi + split latih/uji (dibangkitkan, tidak di-commit) |

## Aset antarmuka (dilayani lokal, bukan CDN)

Dashboard **tidak memuat apa pun dari internet**. Sampai Fase 5 seluruh aset diambil dari
jsDelivr/unpkg, sehingga tanpa jaringan — di ruang sidang atau di kantor kelurahan saat UAT —
halaman tampil tanpa gaya sama sekali. Semuanya kini di `app/static/vendor/`:

| Aset | Versi | Sumber unduhan |
|---|---|---|
| Bootstrap (CSS + bundle JS) | 5.3.3 | `cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/` |
| Bootstrap Icons (CSS + woff2/woff) | 1.11.3 | `cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/` |
| HTMX | 1.9.12 | `unpkg.com/htmx.org@1.9.12/dist/htmx.min.js` |
| Inter Variable (subset latin, woff2) | fontsource 5.0.20 | `cdn.jsdelivr.net/npm/@fontsource-variable/inter@5.0.20/files/` |

Total ±790 KB. *Source map* Bootstrap sengaja tidak ikut diunduh (hanya diminta peramban saat
DevTools terbuka; ketiadaannya tidak berpengaruh pada pengguna).

**Cara memeriksa tidak ada yang bocor ke CDN:** `grep -rn "https://" app/templates app/static/css`
harus kosong, dan halaman tetap utuh saat jaringan dimatikan.

## Model Tier 1 (IndoBERT)

Skor urgensi = probabilitas kelas `tinggi` (0–1) dari `indobert-base-p1` hasil fine-tuning.
Dependensi ML: `pip install -r requirements-ml.txt`.

```powershell
python -m ml.tier1.corpus  --n 3200 --out data/corpus/tier1_urgensi.csv   # korpus augmentasi
python -m ml.tier1.dataset --input data/corpus/tier1_urgensi.csv --outdir data/corpus
python -m ml.tier1.train   --epochs 3 --batch-size 16 --asal-data augmentasi   # fine-tune
python -m ml.tier1.evaluate --model ml/artifacts/indobert --test data/corpus/tier1_test.csv
```

Fine-tuning produksi dijalankan di **Colab GPU** —
`progres/fase-2-tier1-indobert/finetune_indobert_colab.ipynb`. Artefak hasilnya diekstrak ke
`ml/artifacts/indobert/` (atau set `INDOBERT_MODEL_PATH` di `.env`).

Tanpa artefak, sistem tetap berjalan memakai **heuristik cadangan** dan menandai hasilnya
`versi_model = heuristik-fallback-v0` — baris tersebut tidak sah dipakai untuk klaim evaluasi.
Cek status: `python -c "from app.services.tier1_nlp import info_model; print(info_model())"`.

## Tier 3 (Fuzzy TOPSIS)

Perangkingan memakai Chen (2000) dengan fuzzifikasi **derajat keanggotaan penuh**: nilai crisp tidak
dipaksa ke satu himpunan linguistik, melainkan derajatnya terhadap seluruh himpunan dihitung lalu
bilangan fuzzy dirata-rata berbobot. Bentuk & rentang fungsi keanggotaan (OI-13), bobot (OI-12), dan
aturan tiebreak seluruhnya ada di `config/fuzzy_config.yaml` — **dapat diubah tanpa menyentuh kode**
(FR-19, NFR-06). Nilainya masih provisional sampai disepakati kelurahan (Fase 6).

Kriteria urgensi difuzzifikasi dari **margin logit** Tier 1, bukan probabilitasnya: pada model yang
memisahkan kelas dengan sangat baik softmax menjenuh, dan 2.020 narasi hanya menghasilkan 5 nilai
probabilitas berbeda. Pada margin, angka itu menjadi 65.

```powershell
python -c "from app.services.tier3_topsis import info_fuzzy; print(info_fuzzy())"
python progres/fase-4-tier3-fuzzy-topsis/hasil_fase4.py   # sensitivitas bobot & atribusi
```

Bila konfigurasi keanggotaan tidak sah, sistem tetap merangking memakai TOPSIS crisp dan menandainya
`versi_metode = topsis-crisp-fallback-v0` — batch tersebut tidak sah dipakai untuk klaim evaluasi.
**Tes tidak akan menangkap keadaan ini** (bentuk keluarannya tetap benar); yang menangkapnya hanya
penanda versi, jadi periksa `info_fuzzy()` setelah mengubah konfigurasi.

## Catatan

- **Database**: default SQLite untuk dev lokal (nol setup); PostgreSQL di jalur Docker. Model DB-agnostik.
- **Privasi**: data warga nyata tidak boleh di-commit (lihat `.gitignore`); tanpa pengiriman data ke LLM eksternal.
