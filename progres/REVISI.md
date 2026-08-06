# Catatan Revisi — DSS Bansos Bontoramba

Log kronologis setiap perubahan penting di tengah pengembangan (**terbaru di atas**).
Format tiap entri: `tanggal — fase — ringkasan perubahan (alasan)`.

Gunakan berkas ini untuk mencatat: keputusan teknis yang diambil, penyimpangan dari rencana/TRD,
perbaikan bug penting, penggantian pustaka/versi, dan hasil pengujian yang mengubah arah.

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
