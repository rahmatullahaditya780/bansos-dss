"""Evaluasi Tier 1: Akurasi + F1 (utama), plus precision/recall, confusion matrix, ROC-AUC.

Dipanggil otomatis di akhir `ml.tier1.train`, dan dapat dijalankan mandiri atas artefak yang
sudah ada — misalnya untuk mengevaluasi model versi *augmentasi* pada data uji **lokal**
(rencana Fase 2: dokumentasikan metrik per versi & asal data).

Pemakaian:
    python -m ml.tier1.evaluate --model ml/artifacts/indobert --test data/corpus/tier1_test.csv
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from ml.tier1 import ID2LABEL, LABEL2ID
from ml.tier1.dataset import TeksUrgensiDataset, muat_csv

AMBANG_DEFAULT = 0.5  # p(tinggi) >= ambang -> diprediksi 'tinggi'


def prediksi_batch(model, dataloader, device) -> tuple[list[int], list[float], float]:
    """Kembalikan (label_benar, probabilitas kelas 'tinggi', rata-rata loss)."""
    import torch

    model.eval()
    y_true: list[int] = []
    y_prob: list[float] = []
    total_loss = 0.0
    with torch.no_grad():
        for batch in dataloader:
            batch = {k: v.to(device) for k, v in batch.items()}
            out = model(**batch)
            total_loss += out.loss.item()
            prob = torch.softmax(out.logits, dim=-1)[:, LABEL2ID["tinggi"]]
            y_true.extend(batch["labels"].cpu().tolist())
            y_prob.extend(prob.cpu().tolist())
    return y_true, y_prob, total_loss / max(1, len(dataloader))


def hitung_metrik(
    y_true: list[int], y_prob: list[float], ambang: float = AMBANG_DEFAULT
) -> dict[str, object]:
    """Metrik klasifikasi biner dengan kelas positif = 'tinggi'."""
    from sklearn.metrics import (
        accuracy_score,
        confusion_matrix,
        f1_score,
        precision_score,
        recall_score,
        roc_auc_score,
    )

    pos = LABEL2ID["tinggi"]
    y_pred = [pos if p >= ambang else LABEL2ID["rendah"] for p in y_prob]
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[LABEL2ID["rendah"], pos]).ravel()

    try:
        auc = round(float(roc_auc_score(y_true, y_prob)), 4)
    except ValueError:  # hanya satu kelas hadir di data uji
        auc = None

    return {
        "ambang": ambang,
        "jumlah_uji": len(y_true),
        "akurasi": round(float(accuracy_score(y_true, y_pred)), 4),
        "f1": round(float(f1_score(y_true, y_pred, pos_label=pos, zero_division=0)), 4),
        "precision": round(float(precision_score(y_true, y_pred, pos_label=pos, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, pos_label=pos, zero_division=0)), 4),
        "roc_auc": auc,
        "confusion_matrix": {
            "label_urutan": [ID2LABEL[LABEL2ID["rendah"]], ID2LABEL[pos]],
            "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
        },
    }


def evaluate_artifact(
    model_dir: str, test_csv: str, batch_size: int = 32, max_length: int = 128, ambang: float = AMBANG_DEFAULT
) -> dict[str, object]:
    """Muat artefak tersimpan lalu evaluasi pada satu CSV uji."""
    import torch
    from torch.utils.data import DataLoader
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    path = Path(model_dir)
    tokenizer = AutoTokenizer.from_pretrained(path)
    model = AutoModelForSequenceClassification.from_pretrained(path)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    baris = muat_csv(test_csv)
    dl = DataLoader(TeksUrgensiDataset(baris, tokenizer, max_length), batch_size=batch_size)
    y_true, y_prob, _ = prediksi_batch(model, dl, device)

    metrik = hitung_metrik(y_true, y_prob, ambang)

    # Rincian per asal data & per kategori — memperlihatkan performa pada kasus "sulit".
    pos = LABEL2ID["tinggi"]
    y_pred = [pos if p >= ambang else LABEL2ID["rendah"] for p in y_prob]
    for dimensi, ambil in (("per_asal_data", lambda b: b.asal_data), ("per_kategori", lambda b: b.kategori)):
        rincian: dict[str, dict[str, float]] = {}
        for nilai in sorted({ambil(b) for b in baris if ambil(b)}):
            idx = [i for i, b in enumerate(baris) if ambil(b) == nilai]
            benar = sum(1 for i in idx if y_pred[i] == y_true[i])
            rincian[nilai] = {"n": len(idx), "akurasi": round(benar / len(idx), 4)}
        metrik[dimensi] = rincian

    meta_path = path / "metadata.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        metrik["versi_model"] = meta.get("versi_model")
        metrik["asal_data_latih"] = meta.get("asal_data")
    return metrik


def main() -> None:
    ap = argparse.ArgumentParser(description="Evaluasi artefak IndoBERT Tier 1.")
    ap.add_argument("--model", default="ml/artifacts/indobert")
    ap.add_argument("--test", default="data/corpus/tier1_test.csv")
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--max-length", type=int, default=128)
    ap.add_argument("--ambang", type=float, default=AMBANG_DEFAULT)
    ap.add_argument("--out", default=None, help="tulis hasil ke berkas JSON")
    args = ap.parse_args()

    metrik = evaluate_artifact(args.model, args.test, args.batch_size, args.max_length, args.ambang)
    teks = json.dumps(metrik, indent=2, ensure_ascii=False)
    print(teks)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(teks, encoding="utf-8")
        print(f"\nDitulis ke {args.out}")


if __name__ == "__main__":
    main()
