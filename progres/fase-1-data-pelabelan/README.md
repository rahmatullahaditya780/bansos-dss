# Fase 1 — Data: Publik, Lokal & Pelabelan

**Jalur:** B (Data, non-koding) · **Target:** mulai minggu 1, berjalan terus · **Status:** 🔶 Berjalan

## Tujuan
Menyiapkan data untuk melatih pipeline (dataset publik) dan untuk klaim final (data lokal Bontoramba),
beserta prosedur pelabelan urgensi yang konsisten.

## Deliverable / Checklist
- [ ] Unduh & siapkan **dataset publik**: SUSENAS/Kaggle kemiskinan (terstruktur) + IndoNLU / laporan masyarakat (teks)
- [ ] **Harmonisasi skema** kolom publik → `data_survei` TRD (petakan fitur)
- [ ] Urus **izin resmi** akses data DTKS/kependudukan kelurahan (OI-09) — paralel, tidak memblokir
- [ ] Susun **rubrik pelabelan urgensi biner** (OI-11); rekrut ≥2 pelabel; ukur Cohen's kappa
- [ ] Terapkan pelabelan pada teks naratif **lokal** (sumber gold Tier 1)
- [ ] Target ukuran data (OI-08): ≥100 KK lokal untuk klaim final
- [ ] Validasi/koreksi label historis oleh petugas ahli (kurangi bias — OI-10)
- [ ] Ekspor CSV latih:uji = 80:20 tanpa kebocoran, dengan penanda asal data (publik/lokal) per baris

## Exit criteria
Tersedia dataset (publik untuk latih + lokal untuk final) dalam format CSV siap-pakai, rubrik pelabelan
terdokumentasi, dan skor kappa antar-pelabel terukur.

## Catatan & artefak
Taruh di folder ini: rubrik pelabelan, tautan/berkas dataset publik, skrip harmonisasi skema, ringkasan
statistik data, surat/izin (jangan commit data pribadi warga — lihat `.gitignore`).
