"""Fuzzy TOPSIS — Chen (2000). FR-18…FR-21.

Langkah (TRD Bab 7.3): fuzzifikasi → matriks keputusan fuzzy → pembobotan → solusi ideal fuzzy
positif/negatif → jarak vertex → nilai preferensi → peringkat.

**Adaptasi yang disengaja terhadap rumus asli, dan alasannya.** Chen menormalkan kriteria *cost*
dengan resiprokal `(a⁻/u, a⁻/m, a⁻/l)`. Rumus itu mengandaikan matriks keputusan berisi nilai
mentah yang seluruhnya positif. Di sini fuzzifikasi (`keanggotaan.py`) sudah memetakan setiap
kriteria ke skala preferensi 0..1 yang sama, sehingga nilai 0 sah muncul dan resiprokal akan
membagi nol — di samping meregangkan jarak antar-alternatif secara non-linier pada skala yang
justru sudah seragam. Pada skala terbatas 0..1, pengubah cost→benefit yang benar adalah
**komplemen** `(1-u, 1-m, 1-l)`: monoton, mempertahankan lebar bilangan fuzzy, dan tidak pernah
gagal. Sisa rumus Chen dipakai apa adanya, termasuk normalisasi linier terhadap maksimum batch dan
solusi ideal mutlak.

Konsekuensi yang perlu diketahui pembaca hasil: karena normalisasi memakai maksimum yang teramati
**di dalam batch**, nilai preferensi bersifat relatif terhadap batch — menambah satu alternatif
dapat menggeser nilai alternatif lain. Peringkat itulah yang bermakna, bukan nilai absolutnya.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from ml.tier3 import TFN
from ml.tier3.keanggotaan import KriteriaFuzzy

MODE = ("fuzzy", "degenerat")


@dataclass(frozen=True)
class HasilRanking:
    pengajuan_id: int
    nilai_preferensi: float  # presisi penuh — pembulatan dikerjakan saat menyimpan/menampilkan
    peringkat: int
    jarak_positif: float
    jarak_negatif: float
    seri_dengan: int = 0  # banyak alternatif lain bernilai preferensi identik


# --------------------------------------------------------------------------------------
# Operasi bilangan fuzzy segitiga
# --------------------------------------------------------------------------------------
def jarak_vertex(a: TFN, b: TFN) -> float:
    """Jarak antar-TFN metode vertex (Chen 2000): sqrt(1/3 * jumlah kuadrat selisih per titik)."""
    return (((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) / 3.0) ** 0.5


def _komplemen(t: TFN) -> TFN:
    """Ubah kriteria cost menjadi benefit pada skala 0..1; urutan titik ikut terbalik."""
    return (1.0 - t[2], 1.0 - t[1], 1.0 - t[0])


def _nilai_dan_margin(alt: Mapping[str, Any], nama: str) -> tuple[float, float | None]:
    """Ambil nilai crisp kriteria, beserta margin logit bila alternatif menyediakannya.

    Konvensi kunci `<kriteria>_margin` dipakai oleh kriteria berskala `logit` (saat ini hanya
    `skor_urgensi`): memakai margin yang dihitung model lebih tepat daripada membalik probabilitas
    yang mungkin sudah kehilangan digit di perjalanan lewat basis data.
    """
    return float(alt.get(nama, 0.0) or 0.0), alt.get(f"{nama}_margin")


def matriks_fuzzy(
    alternatif: Sequence[Mapping[str, Any]],
    kriteria: Mapping[str, KriteriaFuzzy],
    mode: str = "fuzzy",
) -> dict[str, list[TFN]]:
    """Matriks keputusan fuzzy: satu TFN per (alternatif, kriteria).

    `mode='degenerat'` menghasilkan TFN berlebar nol (l = m = u) pada posisi linier nilai di dalam
    domain. Itu **kontrol**, bukan metode alternatif: menjalankan seluruh mesin Fuzzy TOPSIS tanpa
    kefuzzian sama sekali, sehingga selisih terhadap TOPSIS crisp dapat diatribusikan ke rumusan
    TOPSIS-nya, dan selisih terhadap mode fuzzy ke kefuzzian (evaluasi pra-Fase 4 §5.3).
    """
    if mode not in MODE:
        raise ValueError(f"mode '{mode}' tidak dikenal (pilih: {', '.join(MODE)})")

    matriks: dict[str, list[TFN]] = {}
    for nama, kf in kriteria.items():
        pasangan = [_nilai_dan_margin(alt, nama) for alt in alternatif]
        nilai = [p[0] for p in pasangan]
        margin = [p[1] for p in pasangan]
        if mode == "fuzzy":
            matriks[nama] = kf.fuzzifikasi_kolom(nilai, margin)
        else:
            lo, hi = kf.domain
            rentang = (hi - lo) or 1.0
            matriks[nama] = [
                ((x - lo) / rentang,) * 3
                for x in (kf.nilai_crisp(v, m) for v, m in zip(nilai, margin))
            ]
    return matriks


def nilai_preferensi(
    matriks: Mapping[str, Sequence[TFN]],
    bobot: Mapping[str, float],
    arah: Mapping[str, str],
) -> tuple[list[float], list[float], list[float]]:
    """Kembalikan (nilai preferensi, jarak ke solusi ideal positif, jarak ke negatif)."""
    nama_kriteria = list(bobot)
    n = len(next(iter(matriks.values()))) if matriks else 0
    if n == 0:
        return [], [], []

    # 1) Arah kriteria: cost diubah menjadi benefit lewat komplemen pada skala 0..1.
    searah: dict[str, list[TFN]] = {}
    for k in nama_kriteria:
        kolom = list(matriks[k])
        benefit = arah.get(k, "benefit") == "benefit"
        searah[k] = kolom if benefit else [_komplemen(t) for t in kolom]

    # 2) Normalisasi linier terhadap maksimum batch (Chen 2000).
    ternorm: dict[str, list[TFN]] = {}
    for k in nama_kriteria:
        c = max((t[2] for t in searah[k]), default=0.0)
        if c <= 1e-12:
            ternorm[k] = [(0.0, 0.0, 0.0)] * n
        else:
            ternorm[k] = [(t[0] / c, t[1] / c, t[2] / c) for t in searah[k]]

    # 3) Pembobotan.
    berbobot = {
        k: [(t[0] * bobot[k], t[1] * bobot[k], t[2] * bobot[k]) for t in ternorm[k]]
        for k in nama_kriteria
    }

    # 4) Solusi ideal fuzzy positif & negatif — MUTLAK, bukan teramati (inilah beda utama dari
    #    TOPSIS crisp, dan penyumbang terbesar selisih peringkat antar keduanya).
    fpis = {k: (bobot[k], bobot[k], bobot[k]) for k in nama_kriteria}
    fnis = {k: (0.0, 0.0, 0.0) for k in nama_kriteria}

    # 5) Jarak vertex, dijumlahkan antar-kriteria (Chen), lalu 6) rasio kedekatan.
    d_plus: list[float] = []
    d_minus: list[float] = []
    cc: list[float] = []
    for i in range(n):
        dp = sum(jarak_vertex(berbobot[k][i], fpis[k]) for k in nama_kriteria)
        dm = sum(jarak_vertex(berbobot[k][i], fnis[k]) for k in nama_kriteria)
        total = dp + dm
        d_plus.append(dp)
        d_minus.append(dm)
        cc.append(dm / total if total > 1e-12 else 0.0)
    return cc, d_plus, d_minus


# --------------------------------------------------------------------------------------
# Perakitan peringkat + pemecah seri
# --------------------------------------------------------------------------------------
def _kunci_tiebreak(
    alt: Mapping[str, Any], aturan: Sequence[Mapping[str, str]]
) -> tuple[float, ...]:
    """Kunci pengurutan sekunder; setiap butir dibalik tandanya bila arahnya menurun."""
    kunci: list[float] = []
    for butir in aturan:
        nama = butir.get("kriteria")
        nilai = float(alt.get(nama, 0.0) or 0.0)
        kunci.append(-nilai if butir.get("arah", "asc") == "desc" else nilai)
    return tuple(kunci)


def rangking(
    alternatif: Sequence[Mapping[str, Any]],
    kriteria: Mapping[str, KriteriaFuzzy],
    bobot: Mapping[str, float],
    arah: Mapping[str, str],
    tiebreak: Sequence[Mapping[str, str]] = (),
    mode: str = "fuzzy",
    matriks: Mapping[str, Sequence[TFN]] | None = None,
) -> list[HasilRanking]:
    """Jalankan Fuzzy TOPSIS penuh dan kembalikan peringkat terurut (peringkat 1 = prioritas tertinggi).

    Pengurutan memakai **presisi penuh** nilai preferensi; seri sejati diputus oleh `tiebreak` yang
    dikonfigurasi, dengan `pengajuan_id` sebagai pemutus terakhir agar hasilnya reproducible.

    `matriks` boleh diberikan bila sudah dihitung sebelumnya. Fuzzifikasi **tidak bergantung pada
    bobot**, sehingga analisis sensitivitas yang menjalankan ratusan perangkingan atas alternatif
    yang sama cukup memfuzzifikasi sekali — itu bagian termahal dari perhitungan.
    """
    if not alternatif:
        return []
    if len(alternatif) == 1:
        return [
            HasilRanking(
                pengajuan_id=int(alternatif[0]["pengajuan_id"]),
                nilai_preferensi=1.0, peringkat=1, jarak_positif=0.0, jarak_negatif=0.0,
            )
        ]

    if matriks is None:
        matriks = matriks_fuzzy(alternatif, kriteria, mode=mode)
    cc, d_plus, d_minus = nilai_preferensi(matriks, bobot, arah)

    jumlah_seri: dict[float, int] = {}
    for nilai in cc:
        jumlah_seri[nilai] = jumlah_seri.get(nilai, 0) + 1

    baris = [
        (
            alt,
            HasilRanking(
                pengajuan_id=int(alt["pengajuan_id"]),
                nilai_preferensi=cc[i],
                peringkat=0,
                jarak_positif=d_plus[i],
                jarak_negatif=d_minus[i],
                seri_dengan=jumlah_seri[cc[i]] - 1,
            ),
        )
        for i, alt in enumerate(alternatif)
    ]

    baris.sort(
        key=lambda p: (-p[1].nilai_preferensi, _kunci_tiebreak(p[0], tiebreak), p[1].pengajuan_id)
    )
    return [
        HasilRanking(
            pengajuan_id=h.pengajuan_id,
            nilai_preferensi=h.nilai_preferensi,
            peringkat=i,
            jarak_positif=h.jarak_positif,
            jarak_negatif=h.jarak_negatif,
            seri_dengan=h.seri_dengan,
        )
        for i, (_, h) in enumerate(baris, start=1)
    ]
