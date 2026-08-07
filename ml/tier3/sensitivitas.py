"""Analisis sensitivitas & atribusi Tier 3 — deliverable Fase 4, bukan lampiran.

Tier 3 tidak punya label kebenaran, sehingga akurasi tidak akan pernah dapat dilaporkan untuknya
(evaluasi pra-Fase 4 §5.5). Yang **dapat** dilaporkan, dan sah dilaporkan sekalipun datanya
sintetis, adalah sifat metode terhadap perturbasi — karena yang diukur perilaku metode, bukan
ketepatannya terhadap suatu kebenaran. Modul ini menghasilkan dua tabel itu:

  1. **Sensitivitas bobot** — seberapa banyak daftar penerima berubah saat bobot yang masih
     provisional (OI-12 belum tuntas) digoyang. Menjawab: apakah keluaran Tier 3 hari ini
     ditentukan data atau ditentukan tebakan bobot?
  2. **Atribusi** — berapa bagian selisih "fuzzy vs crisp" yang sebenarnya berasal dari rumusan
     TOPSIS-nya, bukan dari kefuzzian. Tanpa tabel ini, 42% pergantian daftar penerima akan salah
     dilaporkan sebagai efek fuzzifikasi (§5.3).

Sengaja tanpa numpy/pandas: modul ini ikut diuji di suite yang harus tetap hijau pada instalasi
`requirements.txt` polos.
"""
from __future__ import annotations

import random
from typing import Any, Mapping, Sequence

from ml.tier3.crisp import nilai_preferensi_crisp
from ml.tier3.fuzzy_topsis import matriks_fuzzy, rangking
from ml.tier3.keanggotaan import KriteriaFuzzy


# --------------------------------------------------------------------------------------
# Ukuran pembanding
# --------------------------------------------------------------------------------------
def peringkat_map(hasil) -> dict[int, int]:
    return {h.pengajuan_id: h.peringkat for h in hasil}


def peringkat_dari_nilai(ids: Sequence[int], nilai: Sequence[float]) -> dict[int, int]:
    urut = sorted(zip(ids, nilai), key=lambda t: (-t[1], t[0]))
    return {pid: i for i, (pid, _) in enumerate(urut, start=1)}


def spearman(a: Mapping[int, int], b: Mapping[int, int]) -> float:
    """Korelasi peringkat Spearman; 1,0 = urutan identik."""
    ids = sorted(set(a) & set(b))
    n = len(ids)
    if n < 2:
        return 1.0
    mx = sum(a[i] for i in ids) / n
    my = sum(b[i] for i in ids) / n
    num = sum((a[i] - mx) * (b[i] - my) for i in ids)
    dx = sum((a[i] - mx) ** 2 for i in ids) ** 0.5
    dy = sum((b[i] - my) ** 2 for i in ids) ** 0.5
    return num / (dx * dy) if dx > 0 and dy > 0 else 1.0


def tumpang_tindih_topk(a: Mapping[int, int], b: Mapping[int, int], k: int) -> float:
    """Porsi penerima top-K yang sama pada kedua perangkingan."""
    if k <= 0:
        return 1.0
    sa = {i for i, r in a.items() if r <= k}
    sb = {i for i, r in b.items() if r <= k}
    return len(sa & sb) / k


def statistik_seri(nilai: Sequence[float], kuota: int) -> dict[str, Any]:
    """Seri pada nilai preferensi — khususnya di garis potong kuota, tempat ia menentukan orang."""
    jumlah: dict[float, int] = {}
    for v in nilai:
        jumlah[v] = jumlah.get(v, 0) + 1
    urut = sorted(nilai, reverse=True)
    batas = urut[kuota - 1] if 0 < kuota <= len(urut) else (urut[-1] if urut else 0.0)
    return {
        "n": len(nilai),
        "nilai_unik": len(jumlah),
        "grup_seri_terbesar": max(jumlah.values()) if jumlah else 0,
        "seri_di_batas_kuota": jumlah.get(batas, 0),
    }


# --------------------------------------------------------------------------------------
# Tabel 1 — sensitivitas bobot
# --------------------------------------------------------------------------------------
def sensitivitas_bobot(
    alternatif: Sequence[Mapping[str, Any]],
    kriteria: Mapping[str, KriteriaFuzzy],
    bobot: Mapping[str, float],
    arah: Mapping[str, str],
    *,
    tiebreak: Sequence[Mapping[str, str]] = (),
    kuota: int = 50,
    n_perturbasi: int = 200,
    goyang: float = 0.2,
    seed: int = 42,
    mode: str = "fuzzy",
) -> dict[str, float]:
    """Goyang tiap bobot secara acak ±`goyang`, renormalisasi, ukur perpindahan daftar penerima.

    Kembalikan porsi top-K yang bertahan, churn rata-rata, dan seberapa sering peringkat 1 berpindah.
    """
    rng = random.Random(seed)
    kuota = max(1, min(kuota, len(alternatif)))

    # Fuzzifikasi tidak bergantung bobot — hitung sekali, pakai untuk seluruh perturbasi.
    matriks = matriks_fuzzy(alternatif, kriteria, mode=mode)

    def hitung(w: Mapping[str, float]) -> dict[int, int]:
        return peringkat_map(
            rangking(alternatif, kriteria, w, arah, tiebreak, mode=mode, matriks=matriks)
        )

    acuan = hitung(bobot)
    top_acuan = {i for i, r in acuan.items() if r <= kuota}
    juara_acuan = min(acuan, key=lambda i: acuan[i])

    tumpang, juara_beda = [], 0
    for _ in range(n_perturbasi):
        w = {k: v * rng.uniform(1 - goyang, 1 + goyang) for k, v in bobot.items()}
        total = sum(w.values()) or 1.0
        w = {k: v / total for k, v in w.items()}
        r = hitung(w)
        top = {i for i, rr in r.items() if rr <= kuota}
        tumpang.append(len(top_acuan & top) / kuota)
        if min(r, key=lambda i: r[i]) != juara_acuan:
            juara_beda += 1

    rerata = sum(tumpang) / len(tumpang) if tumpang else 1.0
    return {
        "kuota": kuota,
        "goyang": goyang,
        "n_perturbasi": n_perturbasi,
        "topk_bertahan": rerata,
        "churn": 1.0 - rerata,
        "peringkat1_berubah": juara_beda / n_perturbasi if n_perturbasi else 0.0,
    }


# --------------------------------------------------------------------------------------
# Tabel 2 — atribusi selisih
# --------------------------------------------------------------------------------------
def atribusi(
    alternatif: Sequence[Mapping[str, Any]],
    kriteria: Mapping[str, KriteriaFuzzy],
    bobot: Mapping[str, float],
    arah: Mapping[str, str],
    *,
    tiebreak: Sequence[Mapping[str, str]] = (),
    kuota: int = 50,
) -> list[dict[str, Any]]:
    """Pisahkan efek rumusan TOPSIS dari efek kefuzzian.

    Baris `crisp -> degenerat` memakai bilangan fuzzy berlebar NOL: apa pun yang berubah di situ
    berasal dari normalisasi & solusi ideal mutlak Chen (2000), **bukan** dari logika fuzzy. Baris
    `degenerat -> fuzzy` barulah efek kefuzzian yang sesungguhnya.
    """
    ids = [int(a["pengajuan_id"]) for a in alternatif]
    kuota = max(1, min(kuota, len(alternatif)))

    r_crisp = peringkat_dari_nilai(ids, nilai_preferensi_crisp(alternatif, bobot, arah))
    hasil_deg = rangking(alternatif, kriteria, bobot, arah, tiebreak, mode="degenerat")
    hasil_fuz = rangking(alternatif, kriteria, bobot, arah, tiebreak, mode="fuzzy")
    r_deg, r_fuz = peringkat_map(hasil_deg), peringkat_map(hasil_fuz)

    return [
        {
            "perbandingan": "crisp -> degenerat (efek rumusan TOPSIS)",
            "spearman": spearman(r_crisp, r_deg),
            "topk_sama": tumpang_tindih_topk(r_crisp, r_deg, kuota),
        },
        {
            "perbandingan": "degenerat -> fuzzy (efek kefuzzian)",
            "spearman": spearman(r_deg, r_fuz),
            "topk_sama": tumpang_tindih_topk(r_deg, r_fuz, kuota),
        },
        {
            "perbandingan": "crisp -> fuzzy (selisih total)",
            "spearman": spearman(r_crisp, r_fuz),
            "topk_sama": tumpang_tindih_topk(r_crisp, r_fuz, kuota),
        },
    ]
