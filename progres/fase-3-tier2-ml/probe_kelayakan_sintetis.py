"""Probe pra-Fase 3: seberapa jauh data sintetis dapat dipakai memilih RF vs Gradient Boosting?

Bukan bagian dari pipeline — skrip diagnostik sekali jalan, dijalankan SEBELUM menulis kode Tier 2
supaya kekeliruan Fase 2 (mengejar angka di atas data buatan sendiri) tidak terulang.

Yang diukur:

1. **Akurasi RF & GB** di atas `data/synthetic/generator.py` dengan vektor fitur yang sama persis
   dengan yang akan dipakai Tier 2 (`app/services/features.py`).
2. **Batas atas teoritis (oracle)** — akurasi prediktor yang mengetahui faktor laten kemiskinan `k`
   secara persis. Generator memberi label `label_historis = (k + U(-0,15; 0,15)) > 0,5`, sehingga
   sebagian label memang tidak dapat ditebak siapa pun; oracle mengukur langit-langit itu.
3. **Selisih RF vs GB** dibandingkan lebar ketidakpastian akurasi pada ukuran data uji tersebut.

Kesimpulan yang dicari: bila RF dan GB sama-sama menempel di langit-langit oracle dan selisihnya
lebih kecil dari ketidakpastian, maka data sintetis **tidak sanggup memilih pemenang** — pemilihan
model harus ditunda ke data lokal, dan angka di sini hanya boleh dilaporkan sebagai validasi pipa.

Pemakaian:
    python progres/fase-3-tier2-ml/probe_kelayakan_sintetis.py --n 3000
"""
from __future__ import annotations

import argparse
import math
import random
import sys
from pathlib import Path

# Jalankan langsung dari root repo maupun dari folder fase.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from app.services.features import build_features  # noqa: E402
from data.synthetic.generator import generate_records  # noqa: E402

# Urutan fitur kanonik yang akan dipakai Tier 2 (lihat rencana Fase 3).
FITUR = [
    "pendapatan",
    "jumlah_tanggungan",
    "usia",
    "aset_produktif",
    "riwayat_bantuan",
    "housing_need",
    "skor_urgensi",
]


def rakit_dataset(n: int, seed: int):
    """Bangun (X, y) dari generator sintetis memakai vektor fitur Tier 2 yang sebenarnya.

    Skor urgensi di-proksi, bukan dihitung ulang lewat IndoBERT: narasi sintetis berasal dari
    template yang sudah dipelajari model Tier 1 dengan akurasi praktis sempurna, sehingga
    inference sungguhan hanya menambah waktu tanpa mengubah angka.
    """
    import numpy as np

    catatan = generate_records(n, seed=seed)
    X, y = [], []
    for r in catatan:
        urgensi = 0.97 if r["label_urgensi"] == "tinggi" else 0.03
        f = build_features(
            pendapatan=r["pendapatan"],
            jumlah_tanggungan=r["jumlah_tanggungan"],
            usia=r["usia"],
            aset_produktif=r["aset_produktif"],
            riwayat_bantuan=r["riwayat_bantuan"],
            jenis_lantai=r["jenis_lantai"],
            jenis_dinding=r["jenis_dinding"],
            sumber_air=r["sumber_air"],
            luas_rumah=r["luas_rumah"],
            skor_urgensi=urgensi,
        )
        X.append([f[k] for k in FITUR])
        y.append(int(r["label_historis"]))
    return np.array(X), np.array(y)


def akurasi_oracle(n: int = 500_000, seed: int = 42) -> float:
    """Langit-langit: akurasi prediktor yang tahu `k` persis, atas aturan label generator."""
    rng = random.Random(seed)
    benar = sum(
        1
        for _ in range(n)
        for k in (rng.random(),)
        if ((k + rng.uniform(-0.15, 0.15)) > 0.5) == (k > 0.5)
    )
    return benar / n


def galat_baku(akurasi: float, n: int) -> float:
    """Galat baku akurasi binomial — pembanding kasar untuk selisih antar model."""
    return math.sqrt(akurasi * (1 - akurasi) / n)


def main() -> None:
    ap = argparse.ArgumentParser(description="Probe daya diagnostik data sintetis untuk Tier 2.")
    ap.add_argument("--n", type=int, default=3000, help="jumlah rumah tangga sintetis")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    from sklearn.dummy import DummyClassifier
    from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
    from sklearn.metrics import accuracy_score, confusion_matrix, precision_recall_fscore_support
    from sklearn.model_selection import train_test_split

    X, y = rakit_dataset(args.n, args.seed)
    print(f"n={len(y)}  proporsi 'layak'={y.mean():.3f}  fitur={FITUR}\n")

    X_latih, X_uji, y_latih, y_uji = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=args.seed
    )

    hasil: dict[str, float] = {}
    for nama, clf in [
        ("Dummy (mayoritas)", DummyClassifier(strategy="most_frequent")),
        ("Random Forest", RandomForestClassifier(n_estimators=300, random_state=args.seed)),
        ("Gradient Boosting", GradientBoostingClassifier(random_state=args.seed)),
    ]:
        clf.fit(X_latih, y_latih)
        pred = clf.predict(X_uji)
        akurasi = accuracy_score(y_uji, pred)
        presisi, recall, f1, _ = precision_recall_fscore_support(
            y_uji, pred, average="binary", zero_division=0
        )
        tn, fp, fn, tp = confusion_matrix(y_uji, pred).ravel()
        hasil[nama] = akurasi
        print(
            f"{nama:20s} akurasi={akurasi:.4f}  presisi={presisi:.4f}  recall={recall:.4f}  "
            f"F1={f1:.4f}  [TN={tn} FP={fp} FN={fn} TP={tp}]"
        )
        if hasattr(clf, "feature_importances_"):
            urut = sorted(zip(FITUR, clf.feature_importances_), key=lambda t: -t[1])
            print("    importance: " + ", ".join(f"{k}={v:.3f}" for k, v in urut))

    oracle = akurasi_oracle()
    selisih = abs(hasil["Random Forest"] - hasil["Gradient Boosting"])
    se = galat_baku(max(hasil["Random Forest"], hasil["Gradient Boosting"]), len(y_uji))

    print(f"\nLangit-langit oracle (tahu k persis) : {oracle:.4f}")
    print(f"Selisih RF vs GB                     : {selisih:.4f}")
    print(f"Galat baku akurasi (n_uji={len(y_uji)})     : {se:.4f}  (±1,96·SE = {1.96 * se:.4f})")

    if selisih < 1.96 * se:
        print(
            "\nPUTUSAN: selisih RF vs GB lebih kecil dari ketidakpastiannya sendiri.\n"
            "Data sintetis TIDAK dapat dipakai memilih pemenang — tunda pemilihan model ke data lokal."
        )
    else:
        print("\nPUTUSAN: selisih melampaui ketidakpastian; periksa apakah nyata atau artefak generator.")


if __name__ == "__main__":
    main()
