"""Hasil Fase 4 — tabel deliverable Tier 3 di atas implementasi yang sebenarnya dipakai sistem.

Bedanya dari `probe_fuzzy_topsis.py`: probe menguji lima varian fuzzifikasi memakai prototipe
sekali pakai untuk MEMILIH rancangan; skrip ini menjalankan `ml.tier3` yang sungguhan — kode yang
sama yang melayani `POST /analisis/ranking` — untuk menghasilkan angka yang dilaporkan.

Menghasilkan tiga tabel, dan tidak satu pun di antaranya berupa akurasi. Tier 3 tidak punya label
kebenaran (evaluasi pra-Fase 4 §5.5), jadi yang dilaporkan hanya:

  1. **Daya beda & seri** — apakah nilai preferensi sanggup memisahkan alternatif, khususnya di
     garis potong kuota tempat ia menentukan orang.
  2. **Atribusi** — berapa bagian selisih terhadap TOPSIS crisp yang berasal dari rumusan Chen,
     bukan dari kefuzzian.
  3. **Sensitivitas bobot** — apakah daftar penerima ditentukan data atau ditentukan bobot yang
     masih provisional (OI-12 belum tuntas).

Pakai:
    python progres/fase-4-tier3-fuzzy-topsis/hasil_fase4.py
    python progres/fase-4-tier3-fuzzy-topsis/hasil_fase4.py --kuota 100 --perturbasi 500
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.services.fuzzy_config import load_fuzzy_config  # noqa: E402
from app.services.tier3_topsis import info_fuzzy  # noqa: E402
from ml.tier3.crisp import nilai_preferensi_crisp  # noqa: E402
from ml.tier3.fuzzy_topsis import rangking  # noqa: E402
from ml.tier3.keanggotaan import muat_kriteria  # noqa: E402
from ml.tier3.sensitivitas import atribusi, sensitivitas_bobot, statistik_seri  # noqa: E402

FITUR_TIER2 = ["pendapatan", "jumlah_tanggungan", "usia", "aset_produktif", "riwayat_bantuan",
               "housing_need", "skor_urgensi"]


def muat_batch(kriteria: list[str]) -> pd.DataFrame:
    """Batch OI-15 yang sebenarnya: alternatif yang diloloskan Tier 2 sungguhan."""
    paths = [ROOT / "data/corpus/tier2_train.csv", ROOT / "data/corpus/tier2_test.csv"]
    if any(not p.exists() for p in paths):
        raise SystemExit("Korpus belum diekspor. Jalankan `python -m ml.tier2.dataset` lebih dulu.")
    df = pd.concat([pd.read_csv(p) for p in paths], ignore_index=True)

    from app.services.tier2_ml import info_model, predict_eligibility

    info = info_model()
    print(f"  Tier 2 penyaring batch : {info['versi_model']} (fallback={info['fallback_aktif']})")
    if info["fallback_aktif"]:
        print("  ! Tier 2 memakai fallback — batch TIDAK sah untuk klaim apa pun.")

    layak = [
        predict_eligibility({c: float(r[c]) for c in FITUR_TIER2}).hasil == "layak"
        for _, r in df.iterrows()
    ]
    return df.loc[layak, ["pengajuan_id"] + kriteria].reset_index(drop=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kuota", type=int, default=50, help="ukuran top-K yang menentukan keputusan")
    ap.add_argument("--perturbasi", type=int, default=200)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    cfg = load_fuzzy_config()
    bobot, arah = dict(cfg["bobot"]), dict(cfg["arah"])
    nama_kriteria = list(bobot)
    kriteria = muat_kriteria(cfg, nama_kriteria)
    info = info_fuzzy()

    print("=" * 78)
    print("HASIL FASE 4 — FUZZY TOPSIS (implementasi terpasang)")
    print("=" * 78)
    print(f"Metode        : {info['versi_metode']}")
    print(f"Konfigurasi   : {info['versi_konfigurasi']}  (pustaka MF: {info['pustaka_keanggotaan']})")
    print(f"Bobot         : {bobot}")
    print(f"Skala kriteria: {info['skala']}")
    print(f"Tiebreak      : {' -> '.join(info['tiebreak'])}")
    if info["fallback_aktif"]:
        print(f"! FALLBACK AKTIF: {info['alasan_fallback']} — angka di bawah BUKAN Fuzzy TOPSIS.")

    print("\nMemuat batch ...")
    df = muat_batch(nama_kriteria)
    n = len(df)
    print(f"  Alternatif lolos Tier 2: {n}")
    if n < 20:
        raise SystemExit("Alternatif terlalu sedikit. Ekspor korpus / isi basis data dulu.")
    kuota = min(args.kuota, n // 2)

    alternatif = [
        {"pengajuan_id": int(r["pengajuan_id"]), **{k: float(r[k]) for k in nama_kriteria}}
        for _, r in df.iterrows()
    ]

    # --- Tabel 1: daya beda & seri -----------------------------------------
    hasil = rangking(alternatif, kriteria, bobot, arah, tiebreak=cfg.get("tiebreak") or [])
    nilai_fuzzy = [h.nilai_preferensi for h in hasil]
    nilai_crisp = nilai_preferensi_crisp(alternatif, bobot, arah)

    print("\n" + "-" * 78)
    print(f"TABEL 1. Daya beda & seri   (kuota top-{kuota} dari {n} alternatif)")
    print("-" * 78)
    print(f"{'metode':<28}{'nilai unik':>12}{'seri terbesar':>15}{'seri di batas kuota':>21}")
    for nama, nilai in (("Fuzzy TOPSIS (terpasang)", nilai_fuzzy), ("TOPSIS crisp (cadangan)", nilai_crisp)):
        st = statistik_seri(nilai, kuota)
        print(f"{nama:<28}{st['nilai_unik']:>12}{st['grup_seri_terbesar']:>15}"
              f"{st['seri_di_batas_kuota']:>21}")
    kembar = sum(1 for _, g in df[nama_kriteria].round(6).groupby(nama_kriteria) if len(g) > 1
                 for _ in range(len(g)))
    print(f"\n  Alternatif dengan vektor kriteria persis kembar: {kembar} ({kembar / n * 100:.1f}%)")
    print("  Seri yang berasal dari kembar sejati tidak dapat dihapus metode apa pun — dua warga")
    print("  berdata identik memang layak diperlakukan sama. Yang menanganinya adalah aturan")
    print(f"  tiebreak yang tercatat: {' -> '.join(info['tiebreak'])}.")

    # --- Tabel 2: atribusi --------------------------------------------------
    print("\n" + "-" * 78)
    print("TABEL 2. Atribusi selisih — berapa bagian 'efek fuzzy' yang sebenarnya bukan fuzzy")
    print("-" * 78)
    print(f"{'perbandingan':<46}{'rho':>10}{'top-K sama':>14}")
    for baris in atribusi(alternatif, kriteria, bobot, arah,
                          tiebreak=cfg.get("tiebreak") or [], kuota=kuota):
        print(f"{baris['perbandingan']:<46}{baris['spearman']:>10.4f}{baris['topk_sama'] * 100:>13.1f}%")
    print("\n  Baris pertama memakai bilangan fuzzy BERLEBAR NOL: apa pun yang berubah di situ")
    print("  berasal dari normalisasi & solusi ideal mutlak Chen (2000), bukan dari logika fuzzy.")
    print("  Tanpa baris itu, seluruh selisih akan salah dilaporkan sebagai efek fuzzifikasi.")

    # --- Tabel 3: sensitivitas bobot ---------------------------------------
    print("\n" + "-" * 78)
    print(f"TABEL 3. Sensitivitas bobot — OI-12 belum tuntas ({args.perturbasi} perturbasi/baris)")
    print("-" * 78)
    print(f"{'goyang bobot':<16}{'top-K bertahan':>18}{'churn':>10}{'peringkat-1 berubah':>22}")
    for goyang in (0.1, 0.2, 0.5):
        st = sensitivitas_bobot(
            alternatif, kriteria, bobot, arah, tiebreak=cfg.get("tiebreak") or [],
            kuota=kuota, n_perturbasi=args.perturbasi, goyang=goyang, seed=args.seed,
        )
        print(f"{'+-' + str(int(goyang * 100)) + '%':<16}{st['topk_bertahan'] * 100:>17.1f}%"
              f"{st['churn'] * 100:>9.1f}%{st['peringkat1_berubah'] * 100:>21.1f}%")
    print("\n  Ini satu-satunya klaim Tier 3 yang sah dari data sintetis: yang diukur sifat metode")
    print("  terhadap perturbasi, bukan ketepatannya terhadap suatu kebenaran (§5.5).")

    print("\n" + "=" * 78)
    print("Catatan: nilai preferensi bersifat relatif terhadap batch (normalisasi memakai maksimum")
    print("teramati). Yang bermakna adalah PERINGKAT, bukan besar nilainya.")
    print("=" * 78)


if __name__ == "__main__":
    main()
