"""Tier 3 — perangkingan prioritas penerima dengan Fuzzy TOPSIS (FR-18…FR-21).

Submodul:
- `keanggotaan` : fungsi keanggotaan per kriteria (OI-13) + fuzzifikasi ke bilangan fuzzy segitiga
- `fuzzy_topsis`: Chen (2000) — normalisasi, pembobotan, FPIS/FNIS, jarak vertex, nilai preferensi
- `sensitivitas`: perturbasi bobot & atribusi selisih (crisp / degenerat / fuzzy)

Batas klaim yang berbeda dari Tier 1 & 2: **Tier 3 tidak punya label kebenaran.** Tidak ada
"peringkat yang benar" untuk dibandingkan, sehingga akurasi tidak akan pernah dapat dilaporkan
untuk tier ini — di data sintetis maupun lokal. Yang dapat divalidasi hanya:

  1. kebenaran aritmetik  → contoh perhitungan manual di `tests/test_tier3.py`;
  2. sifat metode         → sensitivitas bobot & atribusi di `sensitivitas.py`;
  3. kesepakatan pakar    → Fase 6/7 bersama petugas kelurahan (OI-12, OI-18).

Lihat `progres/evaluasi-pra-fase-4.md` §5.5.
"""

VERSI_METODE = "fuzzy-topsis-chen2000-v1"

# Dipakai bila konfigurasi keanggotaan tidak ada/tidak sah: sistem tetap merangking memakai TOPSIS
# crisp Fase 0, tetapi hasilnya DITANDAI agar tak pernah disangka keluaran Fuzzy TOPSIS. Pola yang
# sama dengan `heuristik-fallback-v0` (Tier 1) dan `stub-logistik-fallback-v0` (Tier 2).
VERSI_FALLBACK = "topsis-crisp-fallback-v0"

# Bilangan fuzzy segitiga (l, m, u) dengan l <= m <= u.
TFN = tuple[float, float, float]
