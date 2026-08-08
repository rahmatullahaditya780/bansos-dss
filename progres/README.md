# Progres Pengembangan — DSS Bansos Bontoramba

Folder ini melacak kemajuan pengembangan **per fase** sesuai rencana bertahap
(`C:\Users\adity\.claude\plans\berdasarkan-trd-pada-direktori-vectorized-bee.md`).

## Cara pakai folder ini

- Tiap fase punya subfoldernya sendiri berisi `README.md` (tujuan, checklist deliverable, exit criteria, status).
- Taruh **artefak khusus fase** di subfoldernya: notebook pelatihan, hasil evaluasi model, tangkapan layar, catatan rapat, dsb.
- Setiap perubahan penting di tengah pengembangan dicatat kronologis di [REVISI.md](REVISI.md).
- Perbarui kolom **Status** di tabel bawah setiap sebuah fase berubah.
- Tinjauan lintas-fase ditulis sebagai dokumen tersendiri, satu per gerbang fase:
  [evaluasi-pra-fase-3.md](evaluasi-pra-fase-3.md) · [evaluasi-pra-fase-4.md](evaluasi-pra-fase-4.md) ·
  [evaluasi-pra-fase-5.md](evaluasi-pra-fase-5.md).

Legenda status: ✅ Selesai · 🔶 Sedang berjalan · ⬜ Belum mulai

## Ringkasan status

| Fase | Judul | Jalur | Status |
|---|---|---|---|
| [0](fase-0-kerangka-integrasi/) | Fondasi & Kerangka Integrasi Tipis | A | ✅ Selesai |
| [1](fase-1-data-pelabelan/) | Data: Publik, Lokal & Pelabelan | B | 🔶 Berjalan |
| [2](fase-2-tier1-indobert/) | Tier 1 Matang — IndoBERT (skor urgensi) | A | 🔶 Kode selesai; fine-tune final menunggu data lokal |
| [3](fase-3-tier2-ml/) | Tier 2 Matang — Klasifikasi ML (kelayakan) | A | 🔶 Kode selesai; pemilihan model final menunggu data lokal |
| [4](fase-4-tier3-fuzzy-topsis/) | Tier 3 Matang — Fuzzy TOPSIS (ranking) | A | ✅ Selesai — bobot & rentang final menunggu kelurahan (Fase 6) |
| [5](fase-5-dashboard-pengujian/) | Dashboard, Penjelasan & Instrumen Pengujian | A | ✅ Selesai — angka efektivitas ditunda ke Fase 7 (butuh petugas) |
| [6](fase-6-integrasi-data-lokal/) | Integrasi Data Lokal & Finalisasi Konfigurasi | A+B | ⬜ Belum |
| [7](fase-7-pengujian-uat-deploy/) | Pengujian, UAT & Deployment | A | ⬜ Belum |
| [8](fase-8-dokumentasi-skripsi/) | Dokumentasi Skripsi & Revisi TRD | — | ⬜ Belum |

## Keputusan terkunci (ringkas)

Label urgensi biner (probabilitas → skor kontinu) · Tier 2 uji RF+GB pilih terbaik · Tier 3 hanya
merangking yang lolos ML (OI-15) · aktor hanya petugas · tanpa LLM (alasan berbasis aturan) ·
efektivitas target ≥85% · fine-tune di Colab GPU · data publik untuk latih, data lokal untuk klaim final.
Detail lengkap di plan file.
