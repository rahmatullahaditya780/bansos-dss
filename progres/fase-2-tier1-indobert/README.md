# Fase 2 — Tier 1 Matang: IndoBERT (Skor Urgensi)

**Jalur:** A · **Target:** minggu 3–4 · **Status:** ⬜ Belum mulai

## Tujuan
Mengganti stub Tier 1 dengan inference IndoBERT hasil fine-tuning untuk menghasilkan skor urgensi
(probabilitas kelas 'tinggi', 0–1) dari teks naratif.

## Deliverable / Checklist
- [ ] Preprocessing (FR-11): pembersihan, lowercasing, tokenizer IndoBERT; utilitas NLTK/Sastrawi seperlunya
- [ ] **Fine-tuning di Colab GPU** (OI-20): base `indobert-base-p1`, klasifikasi biner tinggi/rendah, split 80:20
- [ ] Latih dulu di teks publik/augmentasi (validasi pipeline), lalu fine-tune final di teks **lokal** berlabel
- [ ] Evaluasi **Akurasi + F1** pada data uji; dokumentasikan per versi & asal data (publik/lokal)
- [ ] Ekspor artefak + `versi_model`; unduh ke `ml/artifacts/`; set `INDOBERT_MODEL_PATH`
- [ ] Ganti `app/services/tier1_nlp.py` (score_urgency) dengan inference asli — kontrak fungsi dipertahankan
- [ ] Pasang `requirements-ml.txt` (torch/transformers) di venv

## Exit criteria
`score_urgency(teks)` memuat model asli, mengeluarkan probabilitas 0–1 yang tersimpan ke `skor_urgensi`;
metrik Akurasi+F1 terdokumentasi; pipeline tetap lulus tes blackbox.

## Catatan & artefak
Taruh di folder ini: notebook Colab fine-tuning, kurva pelatihan, tabel metrik (akurasi/F1), catatan
hyperparameter, dan tautan artefak model.
