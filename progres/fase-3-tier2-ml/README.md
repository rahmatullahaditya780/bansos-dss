# Fase 3 — Tier 2 Matang: Klasifikasi ML (Kelayakan)

**Jalur:** A · **Target:** minggu 5–6 · **Status:** ⬜ Belum mulai

## Tujuan
Mengganti stub Tier 2 dengan model terlatih (Random Forest vs Gradient Boosting, pilih terbaik) yang
memprediksi kelayakan (layak / tidak_layak) dari fitur terstruktur + skor urgensi Tier 1.

## Deliverable / Checklist
- [ ] Rakit fitur: demografi + ekonomi + kondisi rumah + riwayat bantuan + **skor urgensi (Tier 1)**
- [ ] Latih **Random Forest & Gradient Boosting** offline (OI-01), split 80:20
- [ ] Latih dulu di proxy publik (SUSENAS/Kaggle), lalu latih ulang & evaluasi final di data **lokal**
- [ ] Bandingkan **akurasi, precision, recall, confusion matrix**; pilih terbaik; analisis FP/FN
- [ ] Tangani bias label (OI-10): validasi/koreksi label oleh petugas ahli; dokumentasikan keterbatasan
- [ ] Ekspor artefak + versi ke `ml/artifacts/`; set `ML_MODEL_PATH`
- [ ] Ganti `app/services/tier2_ml.py` (predict_eligibility) dengan model asli — kontrak dipertahankan

## Exit criteria
`predict_eligibility(fitur)` memuat model terpilih, mengembalikan hasil+probabilitas+versi ke
`prediksi_ml`; metrik (akurasi/precision/recall/confusion) terdokumentasi; tes blackbox tetap lulus.

## Catatan & artefak
Taruh di folder ini: skrip/notebook pelatihan (`ml/train_classifier.py`), confusion matrix, tabel
perbandingan RF vs GB, feature importance, catatan pemilihan model.
