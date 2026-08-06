# Fase 0 — Fondasi & Kerangka Integrasi Tipis

**Jalur:** A (Pengembangan) · **Target:** minggu 1–2 · **Status:** ✅ **SELESAI** (2026-08-06, commit `f491dec`)

## Tujuan
Membangun tulang punggung sistem end-to-end lebih dulu, dengan tiap tier sebagai *stub* (nilai dummy
bertipe benar), agar risiko integrasi di akhir hilang dan tiap tier bisa dimatangkan satu per satu.

## Deliverable / Checklist
- [x] Setup proyek: subfolder, `git init`, venv Python 3.10, `requirements*.txt`, `.env`, Docker files
- [x] Skema DB penuh (SQLAlchemy + Alembic) sesuai TRD 6.4 — 9 tabel
- [x] Autentikasi (FR-01…FR-04): login, hash password, JWT+cookie, RBAC petugas/pemohon
- [x] Generator data simulasi (Faker id_ID) + skrip seed (20 pengajuan)
- [x] 10 endpoint REST TRD Bab 8 (+ Swagger `/docs`)
- [x] Stub Tier 1/2/3 terpasang di pipeline + generator alasan berbasis aturan + log durasi & metrik
- [x] Dashboard web Jinja2 + Bootstrap 5 + HTMX (login, daftar, detail, ranking, form, ringkasan real-time)
- [x] 11 tes blackbox (TRD 9.1) — semua lulus

## Exit criteria (terpenuhi)
`uvicorn` jalan → login petugas → buat pengajuan → analisis (Tier 1→2) → ranking (Tier 3) → hasil &
ranking tampil di dashboard. Semua alur diverifikasi via TestClient dan server langsung.

## Hasil verifikasi
- **pytest:** 11/11 lulus.
- **Smoke test server:** `/login`, `/docs`, dashboard (cookie), analisis→hasil OK. Contoh:
  `urgensi=0.625, prediksi=layak, durasi=7ms` dengan alasan Bahasa Indonesia yang koheren.
- Durasi analisis stub ~7 ms (jauh di bawah target 5 dtk NFR-01; model asli akan lebih berat).

## Catatan
Penyesuaian teknis (SQLite dev, pbkdf2, dsb.) & perbaikan bug tercatat di [../REVISI.md](../REVISI.md).
Yang **masih stub** dan akan diganti: [tier1_nlp.py](../../app/services/tier1_nlp.py) (→ Fase 2),
[tier2_ml.py](../../app/services/tier2_ml.py) (→ Fase 3), [tier3_topsis.py](../../app/services/tier3_topsis.py) (→ Fase 4).
