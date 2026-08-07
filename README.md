# DSS Bansos — Kelurahan Bontoramba

Decision Support System penentuan kelayakan & prioritas penerima bantuan sosial.
Pipeline tiga tingkat: **Tier 1** IndoBERT (skor urgensi) → **Tier 2** klasifikasi ML (layak/tidak) →
**Tier 3** Fuzzy TOPSIS (perangkingan prioritas), disajikan di dashboard web FastAPI.

Turunan teknis dari `../TRD.md`. Lihat rencana tahapan di
`C:\Users\adity\.claude\plans\berdasarkan-trd-pada-direktori-vectorized-bee.md`.

## Status

**Fase 3 — Tier 2 matang.** Skor urgensi berasal dari **IndoBERT hasil fine-tuning** (Fase 2) dan
kelayakan dari **Random Forest** hasil perbandingan RF vs Gradient Boosting (Fase 3); Tier 3 masih
*stub* dan diganti pada Fase 4. Model kedua tier masih dilatih di data sintetis/augmentasi —
**metriknya memvalidasi pipa, bukan klaim skripsi**; angka final menunggu data lokal (Fase 6).
Rincian per fase: [`progres/`](progres/) · tinjauan lintas-fase:
[`progres/evaluasi-pra-fase-3.md`](progres/evaluasi-pra-fase-3.md).

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
| `app/services` | Logika tiap tier (Tier 1 & 2 asli; Tier 3 stub) + generator alasan + metrik |
| `app/templates` | Dashboard Jinja2 + Bootstrap 5 + HTMX |
| `ml/tier1` | Preprocessing, korpus, pelatihan, evaluasi & inference IndoBERT (Tier 1) |
| `ml/artifacts` | Artefak model terlatih (tidak di-commit — lihat `.gitignore`) |
| `config/fuzzy_config.yaml` | Bobot kriteria & fungsi keanggotaan Fuzzy TOPSIS |
| `data/synthetic` | Generator data simulasi + skrip seed |
| `data/corpus` | Korpus teks berlabel urgensi + split latih/uji (dibangkitkan, tidak di-commit) |

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

## Catatan

- **Database**: default SQLite untuk dev lokal (nol setup); PostgreSQL di jalur Docker. Model DB-agnostik.
- **Privasi**: data warga nyata tidak boleh di-commit (lihat `.gitignore`); tanpa pengiriman data ke LLM eksternal.
