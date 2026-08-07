"""Evaluasi Tier 2: metrik, confusion matrix, analisis FP/FN, dan permutation importance.

Tiga hal sengaja dilaporkan meski tidak diminta TRD:

- **Brier score** — `probabilitas` ditampilkan ke petugas di dashboard dan menjadi dasar
  kepercayaan mereka, sedangkan probabilitas Random Forest (rerata voting pohon) terkenal tidak
  terkalibrasi. Akurasi yang baik tidak menjamin angka probabilitasnya layak dibaca.
- **Metrik per kelas** — akurasi tunggal menyembunyikan ketimpangan kelas, yang kemungkinan besar
  terjadi pada data lokal (mayoritas pengaju dinilai layak).
- **Permutation importance**, bukan impurity importance bawaan pohon. Yang bawaan bias ke fitur
  berkardinalitas tinggi (`pendapatan`, `usia`) dan diukur di data latih; permutation importance
  diukur di data uji dan menjawab pertanyaan yang benar: seberapa turun kinerja bila fitur ini dirusak.

Pemakaian:
    python -m ml.tier2.evaluate --model ml/artifacts/tier2 --test data/corpus/tier2_test.csv
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ml.tier2 import FITUR, KELAS_POSITIF, LABEL2ID
from ml.tier2.dataset import Baris, muat_csv
from ml.tier2.skema_fitur import matriks

ID_POSITIF = LABEL2ID[KELAS_POSITIF]


def hitung_metrik(y_true, y_prob, ambang: float = 0.5) -> dict[str, object]:
    """Metrik lengkap terhadap kelas positif 'layak'."""
    import numpy as np
    from sklearn.metrics import (
        accuracy_score,
        brier_score_loss,
        confusion_matrix,
        precision_recall_fscore_support,
        roc_auc_score,
    )

    y_true = np.asarray(y_true)
    y_prob = np.asarray(y_prob, dtype=float)
    y_pred = (y_prob >= ambang).astype(int)

    presisi, recall, f1, dukungan = precision_recall_fscore_support(
        y_true, y_pred, labels=[0, 1], zero_division=0
    )
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()

    # ROC-AUC tidak terdefinisi bila data uji hanya berisi satu kelas.
    dua_kelas = len(set(y_true.tolist())) == 2
    return {
        "ambang": ambang,
        "n": int(len(y_true)),
        "akurasi": round(float(accuracy_score(y_true, y_pred)), 4),
        "presisi": round(float(presisi[ID_POSITIF]), 4),
        "recall": round(float(recall[ID_POSITIF]), 4),
        "f1": round(float(f1[ID_POSITIF]), 4),
        "roc_auc": round(float(roc_auc_score(y_true, y_prob)), 4) if dua_kelas else None,
        "brier": round(float(brier_score_loss(y_true, y_prob)), 4) if dua_kelas else None,
        "confusion": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)},
        "per_kelas": {
            "tidak_layak": {
                "presisi": round(float(presisi[0]), 4),
                "recall": round(float(recall[0]), 4),
                "f1": round(float(f1[0]), 4),
                "dukungan": int(dukungan[0]),
            },
            "layak": {
                "presisi": round(float(presisi[1]), 4),
                "recall": round(float(recall[1]), 4),
                "f1": round(float(f1[1]), 4),
                "dukungan": int(dukungan[1]),
            },
        },
    }


def galat_baku(akurasi: float, n: int) -> float:
    """Galat baku akurasi binomial — pendamping wajib setiap angka akurasi."""
    return (akurasi * (1 - akurasi) / n) ** 0.5 if n else 0.0


def analisis_kesalahan(
    baris: list[Baris], y_true, y_prob, ambang: float = 0.5
) -> list[dict[str, object]]:
    """Daftar kasus salah beserta fiturnya — bukan sekadar jumlah FP/FN.

    Dipakai untuk membaca *pola* kekeliruan: apakah FN terkumpul pada rumah tangga berpendapatan
    menengah dengan urgensi naratif tinggi, atau tersebar acak. Pada data lokal, daftar inilah yang
    dibawa ke petugas untuk ditinjau.
    """
    salah = []
    for b, benar, prob in zip(baris, y_true, y_prob):
        prediksi = 1 if prob >= ambang else 0
        if prediksi == benar:
            continue
        salah.append(
            {
                "pengajuan_id": b.pengajuan_id,
                "warga_id": b.warga_id,
                "label_sebenarnya": b.label,
                "prediksi": "layak" if prediksi else "tidak_layak",
                "jenis": "FN" if benar == ID_POSITIF else "FP",
                "probabilitas": round(float(prob), 4),
                **{f: round(b.fitur[f], 4) for f in FITUR},
            }
        )
    # Kesalahan paling percaya diri lebih dulu — itu yang paling informatif.
    salah.sort(key=lambda r: abs(r["probabilitas"] - ambang), reverse=True)
    return salah


def permutation_importance_ringkas(model, X, y, seed: int = 42, n_ulangan: int = 20) -> list[dict]:
    from sklearn.inspection import permutation_importance

    hasil = permutation_importance(
        model, X, y, n_repeats=n_ulangan, random_state=seed, scoring="f1"
    )
    urut = sorted(
        (
            {
                "fitur": f,
                "rerata_penurunan_f1": round(float(hasil.importances_mean[i]), 4),
                "simpangan": round(float(hasil.importances_std[i]), 4),
            }
            for i, f in enumerate(FITUR)
        ),
        key=lambda r: -r["rerata_penurunan_f1"],
    )
    return urut


def cetak_laporan(metrik: dict, judul: str = "Hasil evaluasi") -> None:
    se = galat_baku(metrik["akurasi"], metrik["n"])
    c = metrik["confusion"]
    print(f"\n{judul} (n={metrik['n']}, ambang={metrik['ambang']})")
    print(f"  Akurasi  : {metrik['akurasi']:.4f}  ±{1.96 * se:.4f} (95%)")
    print(f"  Presisi  : {metrik['presisi']:.4f}   Recall: {metrik['recall']:.4f}   F1: {metrik['f1']:.4f}")
    if metrik["roc_auc"] is not None:
        print(f"  ROC-AUC  : {metrik['roc_auc']:.4f}   Brier: {metrik['brier']:.4f}")
    print(f"  Confusion: TN={c['tn']} FP={c['fp']} FN={c['fn']} TP={c['tp']}")
    for kelas, m in metrik["per_kelas"].items():
        print(
            f"    {kelas:12s} presisi={m['presisi']:.4f} recall={m['recall']:.4f} "
            f"f1={m['f1']:.4f} n={m['dukungan']}"
        )


def main() -> None:
    ap = argparse.ArgumentParser(description="Evaluasi artefak Tier 2 di data uji.")
    ap.add_argument("--model", default="ml/artifacts/tier2")
    ap.add_argument("--test", default="data/corpus/tier2_test.csv")
    ap.add_argument("--ambang", type=float, default=0.5)
    ap.add_argument("--outdir", default=None, help="tulis analisis_kesalahan.csv ke sini")
    args = ap.parse_args()

    import csv as _csv

    import joblib
    import numpy as np

    from ml.tier2 import NAMA_BERKAS_MODEL
    from ml.tier2.skema_fitur import periksa_skema

    model_dir = Path(args.model)
    metadata = json.loads((model_dir / "metadata.json").read_text(encoding="utf-8"))
    periksa_skema(metadata["fitur"])
    model = joblib.load(model_dir / NAMA_BERKAS_MODEL)

    baris = muat_csv(args.test)
    X = np.array(matriks([b.fitur for b in baris]))
    y = np.array([b.label_id for b in baris])
    y_prob = model.predict_proba(X)[:, ID_POSITIF]

    metrik = hitung_metrik(y, y_prob, args.ambang)
    cetak_laporan(metrik, f"Evaluasi {metadata['versi_model']} (asal data: {metadata['asal_data']})")

    print("\nPermutation importance (penurunan F1 saat fitur diacak, diukur di data uji):")
    for r in permutation_importance_ringkas(model, X, y):
        print(f"  {r['fitur']:20s} {r['rerata_penurunan_f1']:+.4f} ± {r['simpangan']:.4f}")
    if metadata["asal_data"] != "lokal":
        print(
            "  [PERINGATAN] Data bukan 'lokal': angka di atas mencerminkan aturan pembangkit data,"
            "\n  bukan kenyataan lapangan. Jangan masukkan ke skripsi (evaluasi pra-Fase 3 §5.2)."
        )

    salah = analisis_kesalahan(baris, y, y_prob, args.ambang)
    print(f"\nKasus salah: {len(salah)} ({sum(1 for r in salah if r['jenis'] == 'FN')} FN, "
          f"{sum(1 for r in salah if r['jenis'] == 'FP')} FP)")
    for r in salah[:5]:
        print(
            f"  [{r['jenis']}] pengajuan {r['pengajuan_id']}: p={r['probabilitas']:.3f} "
            f"pendapatan={r['pendapatan']:,.0f} tanggungan={r['jumlah_tanggungan']:.0f} "
            f"rumah={r['housing_need']:.2f} urgensi={r['skor_urgensi']:.2f}"
        )

    if args.outdir and salah:
        out = Path(args.outdir) / "analisis_kesalahan.csv"
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8", newline="") as f:
            w = _csv.DictWriter(f, fieldnames=list(salah[0].keys()))
            w.writeheader()
            w.writerows(salah)
        print(f"\nDaftar lengkap kasus salah ditulis ke {out}")


if __name__ == "__main__":
    main()
