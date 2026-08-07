"""Probe pra-Fase 4 — apakah Fuzzy TOPSIS dapat mencapai tujuannya di atas data yang ada?

Dijalankan SEBELUM menulis kode Fase 4, meniru pola `probe_kelayakan_sintetis.py` (Fase 3) yang
berhasil meramalkan bahwa data sintetis tidak sanggup memilih RF vs GB.

Pertanyaan yang diuji — semuanya berdampak langsung ke rancangan Fase 4:

  P1. Sejauh mana skor_urgensi (keluaran Tier 1) benar-benar bervariasi?
      Bila bimodal 0/1, ia bukan kriteria kontinu melainkan saklar biner berbobot 0,25 — dan
      memfuzzifikasinya ke 4 himpunan linguistik tidak bermakna.

  P2. Berapa banyak SERI yang ditimbulkan fuzzifikasi linguistik?
      Fuzzifikasi ke k himpunan adalah kuantisasi lossy: 4 kriteria x 4 himpunan = 256 sel untuk
      ~1.000 alternatif. Seri pada batas kuota berarti keputusan siapa yang dapat bantuan jatuh ke
      urutan baris di basis data — bukan ke metode.

  P3. Apakah peringkat Fuzzy TOPSIS berbeda dari TOPSIS crisp (stub Fase 0)?
      Bila korelasinya ~1,0 dan tumpang tindih top-K 100%, "Fuzzy" hanya dekoratif: seluruh Fase 4
      tidak mengubah satu pun keputusan, dan itu harus diketahui sebelum, bukan sesudah.

  P4. Seberapa stabil peringkat terhadap bobot yang MASIH PROVISIONAL (OI-12 belum tuntas)?
      Bila churn top-K besar, keluaran Tier 3 hari ini tidak dapat dijadikan klaim apa pun sampai
      bobot disepakati kelurahan.

Pakai:
    python progres/fase-4-tier3-fuzzy-topsis/probe_fuzzy_topsis.py
    python progres/fase-4-tier3-fuzzy-topsis/probe_fuzzy_topsis.py --sumber db
"""
from __future__ import annotations

import argparse
import math
import statistics
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.services.fuzzy_config import load_fuzzy_config  # noqa: E402
from app.services.tier3_topsis import rank_topsis  # noqa: E402

TFN = tuple[float, float, float]


# --------------------------------------------------------------------------------------
# Pemuatan alternatif = batch OI-15 (hanya yang diprediksi `layak` oleh Tier 2)
# --------------------------------------------------------------------------------------
def muat_alternatif(sumber: str, kriteria: list[str]) -> pd.DataFrame:
    """Kembalikan DataFrame alternatif: pengajuan_id + kolom kriteria, hanya yang `layak`."""
    if sumber == "korpus":
        paths = [ROOT / "data/corpus/tier2_train.csv", ROOT / "data/corpus/tier2_test.csv"]
        hilang = [p for p in paths if not p.exists()]
        if hilang:
            raise SystemExit(f"Korpus belum diekspor: {hilang}. Jalankan `python -m ml.tier2.dataset` dulu.")
        df = pd.concat([pd.read_csv(p) for p in paths], ignore_index=True)
    else:
        from sqlalchemy import select

        from app.db import models
        from app.db.session import SessionLocal
        from app.services.pipeline import _features_pengajuan, _urgensi_pengajuan

        with SessionLocal() as db:
            rows = db.execute(select(models.Pengajuan)).scalars().all()
            recs = []
            for p in rows:
                if p.data_survei is None:
                    continue
                u = _urgensi_pengajuan(p)
                recs.append({"pengajuan_id": p.id, **_features_pengajuan(p, u)})
        df = pd.DataFrame(recs)

    # Tier 2 sungguhan menentukan siapa yang masuk batch (OI-15).
    from app.services.tier2_ml import info_model, predict_eligibility

    info = info_model()
    print(f"  Tier 2 dipakai menyaring batch: {info['versi_model']} (fallback={info['fallback_aktif']})")
    if info["fallback_aktif"]:
        print("  ! PERINGATAN: Tier 2 memakai fallback — batch tidak sah untuk klaim apa pun.")

    fitur_cols = ["pendapatan", "jumlah_tanggungan", "usia", "aset_produktif", "riwayat_bantuan",
                  "housing_need", "skor_urgensi"]
    layak = [predict_eligibility({c: float(r[c]) for c in fitur_cols}).hasil == "layak"
             for _, r in df.iterrows()]
    df = df.loc[layak, ["pengajuan_id"] + kriteria].reset_index(drop=True)
    return df


# --------------------------------------------------------------------------------------
# Tiga varian fuzzifikasi yang menjadi pilihan rancangan Fase 4
# --------------------------------------------------------------------------------------
def _breakpoints(kol: pd.Series, k: int = 4) -> list[float]:
    """Batas himpunan linguistik dari kuantil data (pengganti OI-13 yang belum tuntas)."""
    qs = [kol.quantile(i / k) for i in range(1, k)]
    return sorted(set(float(q) for q in qs))


def fuzz_linguistik(x: float, batas: list[float], k: int = 4) -> TFN:
    """(A) Kuantisasi linguistik: nilai -> SATU himpunan -> TFN wakil himpunan itu.

    Bentuk yang paling sering ditulis di skripsi Fuzzy TOPSIS. Lossy: seluruh nilai dalam satu
    himpunan menjadi bilangan fuzzy yang persis sama.
    """
    idx = 0
    for b in batas:
        if x > b:
            idx += 1
    idx = min(idx, k - 1)
    lebar = 1.0 / (k - 1)
    m = idx * lebar
    return (max(0.0, m - lebar), m, min(1.0, m + lebar))


def fuzz_langsung(x: float, lo: float, hi: float, spread: float = 0.05) -> TFN:
    """(B) Fuzzifikasi langsung: skala ke 0..1, jadikan modus TFN, beri lebar tetap.

    Mempertahankan urutan crisp sepenuhnya — dugaannya menghasilkan peringkat identik TOPSIS crisp.
    """
    rentang = (hi - lo) or 1.0
    m = (x - lo) / rentang
    return (max(0.0, m - spread), m, min(1.0, m + spread))


def fuzz_hibrida(x: float, batas: list[float], lo: float, hi: float, k: int = 4) -> TFN:
    """(C) Hibrida: modus mengikuti nilai crisp (kontinu), LEBAR mengikuti kedekatan ke batas himpunan.

    Nilai yang duduk tepat di perbatasan dua kategori ("hampir rendah, hampir sedang") memperoleh
    bilangan fuzzy lebar = ketidakpastian kategorisasinya ikut terbawa ke perhitungan jarak, tanpa
    menghapus perbedaan antar-alternatif di dalam satu kategori.
    """
    rentang = (hi - lo) or 1.0
    m = (x - lo) / rentang
    if not batas:
        return (max(0.0, m - 0.05), m, min(1.0, m + 0.05))
    jarak_ternorm = min(abs(x - b) for b in batas) / rentang
    lebar_maks = 1.0 / (2 * (k - 1))
    lebar = lebar_maks * math.exp(-jarak_ternorm / (lebar_maks / 2))
    lebar = max(lebar, 0.01)
    return (max(0.0, m - lebar), m, min(1.0, m + lebar))


# --------------------------------------------------------------------------------------
# Fuzzy TOPSIS (Chen 2000): normalisasi linier -> bobot -> FPIS/FNIS -> jarak vertex -> CC
# --------------------------------------------------------------------------------------
def _d(a: TFN, b: TFN) -> float:
    return math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(3)) / 3.0)


def fuzzy_topsis(mat: dict[str, list[TFN]], bobot: dict[str, float], arah: dict[str, str]) -> list[float]:
    kriteria = list(mat.keys())
    n = len(next(iter(mat.values())))
    ternorm: dict[str, list[TFN]] = {}
    for k in kriteria:
        kol = mat[k]
        if arah.get(k, "benefit") == "benefit":
            c = max(t[2] for t in kol) or 1.0
            ternorm[k] = [(t[0] / c, t[1] / c, t[2] / c) for t in kol]
        else:
            a = min(t[0] for t in kol)
            ternorm[k] = [(a / t[2] if t[2] else 1.0, a / t[1] if t[1] else 1.0,
                           a / t[0] if t[0] else 1.0) for t in kol]
    berbobot = {k: [(t[0] * bobot[k], t[1] * bobot[k], t[2] * bobot[k]) for t in ternorm[k]]
                for k in kriteria}
    fpis = {k: (bobot[k], bobot[k], bobot[k]) for k in kriteria}
    fnis = {k: (0.0, 0.0, 0.0) for k in kriteria}

    cc = []
    for i in range(n):
        dp = sum(_d(berbobot[k][i], fpis[k]) for k in kriteria)
        dm = sum(_d(berbobot[k][i], fnis[k]) for k in kriteria)
        cc.append(dm / (dp + dm) if (dp + dm) > 1e-12 else 0.0)
    return cc


def _pusat_himpunan(kol: pd.Series, k: int = 4) -> list[float]:
    """Puncak tiap himpunan linguistik = kuantil merata (pengganti OI-13 yang belum tuntas)."""
    return [float(kol.quantile(i / (k - 1))) for i in range(k)]


def fuzz_keanggotaan(x: float, pusat: list[float], k: int = 4) -> TFN:
    """(E) Fuzzifikasi berbasis DERAJAT KEANGGOTAAN penuh — kandidat rancangan Fase 4.

    Nilai tidak dipaksa masuk ke satu himpunan. Derajat keanggotaannya terhadap SELURUH himpunan
    (segitiga bertetangga, saling tumpang tindih) dihitung, lalu TFN hasil = rerata berbobot
    keanggotaan atas TFN wakil tiap himpunan. Ini fuzzifikasi sebagaimana definisinya; varian
    `linguistik` di atas justru sudah men-defuzzifikasi diam-diam dengan memilih satu himpunan.

    Karena mu_j(x) berubah kontinu terhadap x, urutan antar-alternatif di dalam satu kategori tetap
    terjaga — tetapi bilangan fuzzy tetap melebar di daerah perbatasan antar-kategori.
    """
    mu = []
    for j, c in enumerate(pusat):
        kiri = pusat[j - 1] if j > 0 else c - (pusat[1] - pusat[0] if len(pusat) > 1 else 1.0)
        kanan = pusat[j + 1] if j < len(pusat) - 1 else c + (c - pusat[-2] if len(pusat) > 1 else 1.0)
        if x <= kiri or x >= kanan:
            d = 0.0
        elif x == c:
            d = 1.0
        elif x < c:
            d = (x - kiri) / (c - kiri) if c > kiri else 1.0
        else:
            d = (kanan - x) / (kanan - c) if kanan > c else 1.0
        mu.append(max(0.0, d))
    total = sum(mu)
    if total <= 1e-12:  # di luar seluruh dukungan (mis. pencilan) — jatuhkan ke himpunan terdekat
        j = min(range(len(pusat)), key=lambda i: abs(x - pusat[i]))
        mu = [1.0 if i == j else 0.0 for i in range(len(pusat))]
        total = 1.0

    lebar = 1.0 / (k - 1)
    l = m = u = 0.0
    for j, w in enumerate(mu):
        mj = j * lebar
        l += w * max(0.0, mj - lebar)
        m += w * mj
        u += w * min(1.0, mj + lebar)
    return (l / total, m / total, u / total)


def fuzz_degenerat(x: float, lo: float, hi: float) -> TFN:
    """(D) KONTROL: TFN berlebar nol (l = m = u). Mesin fuzzy dijalankan TANPA kefuzzian.

    Selisih 'degenerat vs crisp' mengukur efek definisi TOPSIS-nya (normalisasi linier, solusi ideal
    mutlak (1,1,1)/(0,0,0), jarak vertex dijumlahkan antar-kriteria). Selisih 'hibrida vs degenerat'
    mengukur efek fuzzifikasi yang sesungguhnya. Tanpa pemisahan ini, seluruh perbedaan salah
    diatribusikan ke "fuzzy".
    """
    rentang = (hi - lo) or 1.0
    m = (x - lo) / rentang
    return (m, m, m)


def bangun_matriks(df: pd.DataFrame, kriteria: list[str], varian: str) -> dict[str, list[TFN]]:
    mat: dict[str, list[TFN]] = {}
    for k in kriteria:
        kol = df[k]
        lo, hi = float(kol.min()), float(kol.max())
        batas = _breakpoints(kol)
        if varian == "linguistik":
            mat[k] = [fuzz_linguistik(float(x), batas) for x in kol]
        elif varian == "keanggotaan":
            pusat = _pusat_himpunan(kol)
            mat[k] = [fuzz_keanggotaan(float(x), pusat) for x in kol]
        elif varian == "langsung":
            mat[k] = [fuzz_langsung(float(x), lo, hi) for x in kol]
        elif varian == "degenerat":
            mat[k] = [fuzz_degenerat(float(x), lo, hi) for x in kol]
        else:
            mat[k] = [fuzz_hibrida(float(x), batas, lo, hi) for x in kol]
    return mat


# --------------------------------------------------------------------------------------
# Ukuran pembanding
# --------------------------------------------------------------------------------------
def peringkat_dari_skor(ids: list[int], skor: list[float]) -> dict[int, int]:
    urut = sorted(zip(ids, skor), key=lambda t: (-t[1], t[0]))
    return {pid: i for i, (pid, _) in enumerate(urut, start=1)}


def spearman(a: dict[int, int], b: dict[int, int]) -> float:
    ids = sorted(a)
    x = np.array([a[i] for i in ids], dtype=float)
    y = np.array([b[i] for i in ids], dtype=float)
    return float(np.corrcoef(x, y)[0, 1])


def topk_overlap(a: dict[int, int], b: dict[int, int], k: int) -> float:
    sa = {i for i, r in a.items() if r <= k}
    sb = {i for i, r in b.items() if r <= k}
    return len(sa & sb) / k if k else 1.0


def statistik_seri(skor: list[float], k_kuota: int, ndigit: int = 4) -> dict:
    bulat = [round(s, ndigit) for s in skor]
    c = Counter(bulat)
    urut = sorted(bulat, reverse=True)
    nilai_batas = urut[k_kuota - 1] if k_kuota <= len(urut) else urut[-1]
    return {
        "nilai_unik": len(c),
        "n": len(bulat),
        "grup_seri_terbesar": max(c.values()),
        "seri_di_batas_kuota": c[nilai_batas],
        "nilai_batas": nilai_batas,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sumber", choices=["korpus", "db"], default="korpus")
    ap.add_argument("--kuota", type=int, default=50, help="ukuran top-K yang menentukan keputusan")
    ap.add_argument("--perturbasi", type=int, default=200, help="jumlah sampel sensitivitas bobot")
    ap.add_argument("--goyang", type=float, default=0.2, help="lebar perturbasi bobot relatif (0.2 = ±20%%)")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rng = np.random.default_rng(args.seed)
    cfg = load_fuzzy_config()
    bobot: dict[str, float] = dict(cfg["bobot"])
    arah: dict[str, str] = dict(cfg["arah"])
    kriteria = list(bobot)

    print("=" * 78)
    print("PROBE PRA-FASE 4 — FUZZY TOPSIS")
    print("=" * 78)
    print(f"Konfigurasi: versi={cfg['versi']}  bobot={bobot}")
    print(f"Arah       : {arah}")
    print(f"\nMemuat alternatif (sumber={args.sumber}) ...")
    df = muat_alternatif(args.sumber, kriteria)
    n = len(df)
    print(f"  Alternatif lolos Tier 2 (batch OI-15): {n}")
    if n < 20:
        raise SystemExit("Alternatif terlalu sedikit untuk probe. Isi basis data / ekspor korpus dulu.")
    kuota = min(args.kuota, n // 2)
    ids = df["pengajuan_id"].astype(int).tolist()

    # ---------------- P1: apakah tiap kriteria benar-benar bervariasi? ----------------
    print("\n" + "-" * 78)
    print("P1. Distribusi kriteria — apakah ada yang bukan kontinu?")
    print("-" * 78)
    print(f"{'kriteria':<20}{'min':>12}{'median':>12}{'maks':>12}{'unik':>8}{'%ekstrem':>10}")
    for k in kriteria:
        kol = df[k].astype(float)
        lo, hi = kol.min(), kol.max()
        rentang = (hi - lo) or 1.0
        ternorm = (kol - lo) / rentang
        ekstrem = float(((ternorm < 0.02) | (ternorm > 0.98)).mean() * 100)
        print(f"{k:<20}{lo:>12.4f}{kol.median():>12.4f}{hi:>12.4f}{kol.nunique():>8}{ekstrem:>9.1f}%")
    print("  '%ekstrem' = porsi nilai yang menempel di ujung rentang. Nilai tinggi (>80%) berarti")
    print("  kriteria itu berperilaku biner, bukan kontinu — fuzzifikasi 4 himpunan tak bermakna.")
    for k in kriteria:
        kol = df[k].astype(float)
        if kol.nunique() <= 10:
            c = Counter(round(float(x), 4) for x in kol)
            rinci = "  ".join(f"{v}×{n}" for v, n in sorted(c.items()))
            print(f"  Rincian '{k}' (hanya {kol.nunique()} nilai berbeda): {rinci}")

    # Seri pada TOPSIS crisp: berapa yang berasal dari pembulatan, berapa dari fitur kembar?
    print("\n" + "-" * 78)
    print("P1b. Asal-usul seri pada TOPSIS crisp — pembulatan atau vektor fitur kembar?")
    print("-" * 78)
    vektor = [tuple(round(float(r[k]), 6) for k in kriteria) for _, r in df.iterrows()]
    kembar = Counter(vektor)
    n_kembar = sum(v for v in kembar.values() if v > 1)
    print(f"  Alternatif dengan vektor kriteria persis kembar : {n_kembar} dari {n} "
          f"({n_kembar / n * 100:.1f}%), grup terbesar {max(kembar.values())}")
    print("  Seri yang lahir dari vektor kembar TIDAK dapat dihilangkan metode apa pun — dua warga")
    print("  yang datanya identik memang layak diperlakukan sama; yang harus ditangani adalah")
    print("  aturan tiebreak yang tercatat, bukan pura-pura tidak ada seri.")

    # ---------------- Peringkat crisp (stub Fase 0) ----------------
    alts = [{"pengajuan_id": int(r["pengajuan_id"]), **{k: float(r[k]) for k in kriteria}}
            for _, r in df.iterrows()]
    crisp_entries = rank_topsis(alts, bobot, arah)
    crisp_skor_map = {e.pengajuan_id: e.nilai_preferensi for e in crisp_entries}
    crisp_skor = [crisp_skor_map[i] for i in ids]
    r_crisp = peringkat_dari_skor(ids, crisp_skor)

    # ---------------- P2 & P3: tiga varian fuzzifikasi ----------------
    print("\n" + "-" * 78)
    print(f"P2/P3. Tiga varian fuzzifikasi vs TOPSIS crisp   (kuota top-{kuota} dari {n})")
    print("-" * 78)
    hasil_varian = {}
    print(f"{'varian':<14}{'nilai unik':>12}{'seri terbesar':>15}{'seri@kuota':>12}"
          f"{'rho crisp':>11}{'top-K sama':>12}")
    for varian in ("degenerat", "linguistik", "keanggotaan", "langsung", "hibrida"):
        mat = bangun_matriks(df, kriteria, varian)
        cc = fuzzy_topsis(mat, bobot, arah)
        hasil_varian[varian] = cc
        r_f = peringkat_dari_skor(ids, cc)
        st = statistik_seri(cc, kuota)
        rho = spearman(r_crisp, r_f)
        ov = topk_overlap(r_crisp, r_f, kuota)
        print(f"{varian:<14}{st['nilai_unik']:>12}{st['grup_seri_terbesar']:>15}"
              f"{st['seri_di_batas_kuota']:>12}{rho:>11.4f}{ov * 100:>11.1f}%")
    st_crisp = statistik_seri(crisp_skor, kuota)
    print(f"{'(crisp)':<14}{st_crisp['nilai_unik']:>12}{st_crisp['grup_seri_terbesar']:>15}"
          f"{st_crisp['seri_di_batas_kuota']:>12}{'1.0000':>11}{'100.0%':>12}")
    print("\n  'seri@kuota' = berapa alternatif berbagi nilai preferensi PERSIS SAMA di garis potong")
    print("  kuota. Angka > 1 berarti urutan pemenang di batas ditentukan tiebreak, bukan metode.")
    print("  'rho crisp' ~ 1,00 + 'top-K sama' 100% berarti fuzzifikasi tidak mengubah keputusan.")

    # ---------------- P3b: atribusi selisih — mesin TOPSIS atau kefuzzian? ----------------
    print("\n" + "-" * 78)
    print("P3b. Atribusi selisih: berapa bagian dari 'efek fuzzy' yang sebenarnya bukan fuzzy?")
    print("-" * 78)
    r_deg = peringkat_dari_skor(ids, hasil_varian["degenerat"])
    for nama, kunci in (("crisp   -> degenerat (efek mesin TOPSIS)", "degenerat"),
                        ("degenerat -> keanggotaan (efek kefuzzian penuh)", "keanggotaan"),
                        ("degenerat -> hibrida  (efek kefuzzian lebar)", "hibrida"),
                        ("degenerat -> linguistik (efek kuantisasi)", "linguistik")):
        r_x = peringkat_dari_skor(ids, hasil_varian[kunci])
        acuan = r_crisp if kunci == "degenerat" else r_deg
        print(f"  {nama:<44} rho={spearman(acuan, r_x):.4f}  "
              f"top-{kuota} sama={topk_overlap(acuan, r_x, kuota) * 100:.1f}%")
    print("  Baris pertama memakai TFN berlebar NOL: apa pun yang berubah di situ berasal dari")
    print("  normalisasi & solusi ideal mutlak Chen (2000), bukan dari logika fuzzy.")

    # ---------------- P4: sensitivitas bobot (OI-12 masih provisional) ----------------
    print("\n" + "-" * 78)
    print(f"P4. Sensitivitas bobot — OI-12 belum tuntas ({args.perturbasi} perturbasi "
          f"±{args.goyang * 100:.0f}%)")
    print("-" * 78)
    print(f"{'metode':<14}{'top-K bertahan':>16}{'rerata churn':>14}{'peringkat-1 berubah':>21}")

    def sensitivitas(fn_skor) -> tuple[float, float, float]:
        base = peringkat_dari_skor(ids, fn_skor(bobot))
        top_base = {i for i, r in base.items() if r <= kuota}
        juara_base = min(base, key=lambda i: base[i])
        overlaps, juara_beda = [], 0
        for _ in range(args.perturbasi):
            faktor = rng.uniform(1 - args.goyang, 1 + args.goyang, size=len(kriteria))
            w = {k: bobot[k] * f for k, f in zip(kriteria, faktor)}
            tot = sum(w.values())
            w = {k: v / tot for k, v in w.items()}
            r = peringkat_dari_skor(ids, fn_skor(w))
            top = {i for i, rr in r.items() if rr <= kuota}
            overlaps.append(len(top_base & top) / kuota)
            if min(r, key=lambda i: r[i]) != juara_base:
                juara_beda += 1
        return (statistics.mean(overlaps), 1 - statistics.mean(overlaps), juara_beda / args.perturbasi)

    def skor_crisp(w):
        e = rank_topsis(alts, w, arah)
        m = {x.pengajuan_id: x.nilai_preferensi for x in e}
        return [m[i] for i in ids]

    tahan, churn, juara = sensitivitas(skor_crisp)
    print(f"{'crisp':<14}{tahan * 100:>15.1f}%{churn * 100:>13.1f}%{juara * 100:>20.1f}%")
    for varian in ("linguistik", "keanggotaan", "hibrida"):
        mat = bangun_matriks(df, kriteria, varian)
        tahan, churn, juara = sensitivitas(lambda w, m=mat: fuzzy_topsis(m, w, arah))
        print(f"{varian:<14}{tahan * 100:>15.1f}%{churn * 100:>13.1f}%{juara * 100:>20.1f}%")
    print("\n  'top-K bertahan' = rerata porsi penerima top-K yang tetap masuk saat bobot digoyang")
    print("  ±20%. Di bawah ~85% berarti daftar penerima ditentukan bobot provisional, bukan data.")

    print("\n" + "=" * 78)
    print("Probe selesai. Baca P2 lebih dulu: bila 'seri@kuota' > 1 pada varian linguistik,")
    print("rancangan fuzzifikasi Fase 4 tidak boleh memakai kuantisasi linguistik polos.")
    print("=" * 78)


if __name__ == "__main__":
    main()
