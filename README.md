# DSS Bansos — Kelurahan Bontoramba

Decision Support System penentuan kelayakan & prioritas penerima bantuan sosial.
Pipeline tiga tingkat: **Tier 1** IndoBERT (skor urgensi) → **Tier 2** klasifikasi ML (layak/tidak) →
**Tier 3** Fuzzy TOPSIS (perangkingan prioritas), disajikan di dashboard web FastAPI.

Turunan teknis dari `../TRD.md`. Lihat rencana tahapan di
`C:\Users\adity\.claude\plans\berdasarkan-trd-pada-direktori-vectorized-bee.md`.

## Status

**Fase 0 — Kerangka Integrasi Tipis.** Pipeline berjalan end-to-end dengan tiap tier sebagai *stub*
(nilai dummy bertipe benar). Model asli dipasang pada Fase 2–4.

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
| `app/services` | Logika tiap tier (Fase 0: stub) + generator alasan + metrik |
| `app/templates` | Dashboard Jinja2 + Bootstrap 5 + HTMX |
| `ml/` | Notebook/skrip pelatihan model (offline) + artefak |
| `config/fuzzy_config.yaml` | Bobot kriteria & fungsi keanggotaan Fuzzy TOPSIS |
| `data/synthetic` | Generator data simulasi + skrip seed |

## Catatan

- **Database**: default SQLite untuk dev lokal (nol setup); PostgreSQL di jalur Docker. Model DB-agnostik.
- **Privasi**: data warga nyata tidak boleh di-commit (lihat `.gitignore`); tanpa pengiriman data ke LLM eksternal.
