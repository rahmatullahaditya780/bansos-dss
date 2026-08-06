# Fase 4 — Tier 3 Matang: Fuzzy TOPSIS (Perangkingan)

**Jalur:** A · **Target:** minggu 7–8 · **Status:** ⬜ Belum mulai

## Tujuan
Mengganti stub TOPSIS crisp dengan **Fuzzy TOPSIS penuh** (fuzzifikasi + bilangan fuzzy
segitiga/trapesium via scikit-fuzzy) untuk merangking prioritas penerima.

## Deliverable / Checklist
- [ ] Implementasi Fuzzy TOPSIS (scikit-fuzzy): fuzzifikasi → matriks keputusan fuzzy → bobot →
      solusi ideal +/- → jarak → nilai preferensi → ranking (FR-18…FR-21)
- [ ] Definisikan fungsi keanggotaan per kriteria (bentuk & rentang) di `config/fuzzy_config.yaml` (OI-13)
- [ ] Bobot & fungsi keanggotaan **provisional** dulu; di-snapshot per batch (`bobot_snapshot`)
- [ ] Pastikan alur OI-15: batch = pengajuan dengan `prediksi_ml = layak` saja
- [ ] Ganti `app/services/tier3_topsis.py` (rank_topsis) dengan Fuzzy TOPSIS — kontrak dipertahankan

## Exit criteria
`rank_topsis(...)` memakai logika fuzzy asli, menyimpan `ranking_topsis` (nilai preferensi + peringkat +
snapshot bobot); pipeline 3-tier nyata end-to-end; tes blackbox tetap lulus.

## Catatan & artefak
Taruh di folder ini: definisi fungsi keanggotaan (grafik/rentang), contoh perhitungan manual untuk
validasi, catatan sensitivitas bobot. **Formalisasi bobot final dgn kelurahan dilakukan di Fase 6.**
