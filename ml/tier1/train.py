"""Fine-tuning IndoBERT untuk klasifikasi biner urgensi (OI-20).

Base model: `indobenchmark/indobert-base-p1`; kepala klasifikasi 2 kelas (rendah/tinggi).
Skor urgensi yang dipakai sistem adalah **probabilitas kelas 'tinggi'** (kontinu 0..1),
sesuai keputusan OI-02.

Ditulis dengan loop PyTorch biasa (tanpa `Trainer`/`accelerate`) agar identik saat dijalankan
di **Colab GPU** maupun di CPU lokal, dengan dependensi minimal.

Pemakaian:
    python -m ml.tier1.train --train data/corpus/tier1_train.csv --test data/corpus/tier1_test.csv \
        --outdir ml/artifacts/indobert --epochs 3 --batch-size 16 --asal-data augmentasi
"""
from __future__ import annotations

import argparse
import json
import platform
import random
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from ml.tier1 import BASE_MODEL, ID2LABEL, LABEL2ID
from ml.tier1.dataset import TeksUrgensiDataset, muat_csv, ringkasan


@dataclass
class KonfigLatih:
    base_model: str = BASE_MODEL
    epochs: int = 3
    batch_size: int = 16
    learning_rate: float = 2e-5
    weight_decay: float = 0.01
    warmup_ratio: float = 0.1
    max_length: int = 128
    seed: int = 42
    fp16: bool = False


def set_seed(seed: int) -> None:
    import numpy as np
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def pilih_device(paksa: str | None = None):
    import torch

    if paksa:
        return torch.device(paksa)
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def _kurva_ke_csv(kurva: list[dict], path: Path) -> None:
    import csv as _csv

    with path.open("w", encoding="utf-8", newline="") as f:
        w = _csv.DictWriter(f, fieldnames=list(kurva[0].keys()))
        w.writeheader()
        w.writerows(kurva)


def train(
    train_csv: str,
    test_csv: str,
    outdir: str,
    cfg: KonfigLatih,
    versi_model: str,
    asal_data: str,
    device_paksa: str | None = None,
) -> dict:
    """Fine-tune, evaluasi di data uji, lalu simpan artefak + metadata + metrik ke `outdir`."""
    import torch
    from torch.utils.data import DataLoader
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        get_linear_schedule_with_warmup,
    )

    from ml.tier1.evaluate import hitung_metrik, prediksi_batch

    set_seed(cfg.seed)
    device = pilih_device(device_paksa)
    print(f"Device: {device} | base: {cfg.base_model}")

    baris_latih = muat_csv(train_csv)
    baris_uji = muat_csv(test_csv)
    print(f"Latih: {ringkasan(baris_latih)}")
    print(f"Uji  : {ringkasan(baris_uji)}")

    tokenizer = AutoTokenizer.from_pretrained(cfg.base_model)
    model = AutoModelForSequenceClassification.from_pretrained(
        cfg.base_model, num_labels=len(LABEL2ID), id2label=ID2LABEL, label2id=LABEL2ID
    ).to(device)

    ds_latih = TeksUrgensiDataset(baris_latih, tokenizer, cfg.max_length)
    ds_uji = TeksUrgensiDataset(baris_uji, tokenizer, cfg.max_length)
    dl_latih = DataLoader(ds_latih, batch_size=cfg.batch_size, shuffle=True)
    dl_uji = DataLoader(ds_uji, batch_size=cfg.batch_size)

    optimizer = torch.optim.AdamW(
        model.parameters(), lr=cfg.learning_rate, weight_decay=cfg.weight_decay
    )
    total_steps = len(dl_latih) * cfg.epochs
    scheduler = get_linear_schedule_with_warmup(
        optimizer, int(total_steps * cfg.warmup_ratio), total_steps
    )
    pakai_fp16 = cfg.fp16 and device.type == "cuda"
    # torch>=2.4 memindahkan GradScaler ke torch.amp; torch lama (mis. Colab) masih di torch.cuda.amp.
    scaler = (
        torch.amp.GradScaler("cuda", enabled=pakai_fp16)
        if hasattr(torch.amp, "GradScaler")
        else torch.cuda.amp.GradScaler(enabled=pakai_fp16)
    )

    kurva: list[dict] = []
    mulai = time.time()
    for epoch in range(1, cfg.epochs + 1):
        model.train()
        total_loss = 0.0
        for step, batch in enumerate(dl_latih, start=1):
            batch = {k: v.to(device) for k, v in batch.items()}
            optimizer.zero_grad(set_to_none=True)
            with torch.autocast(device.type, enabled=scaler.is_enabled()):
                out = model(**batch)
            scaler.scale(out.loss).backward()
            scaler.unscale_(optimizer)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            scaler.step(optimizer)
            scaler.update()
            scheduler.step()
            total_loss += out.loss.item()
            if step % 20 == 0 or step == len(dl_latih):
                print(f"  epoch {epoch} step {step}/{len(dl_latih)} loss {total_loss / step:.4f}")

        y_true, y_prob, loss_uji = prediksi_batch(model, dl_uji, device)
        m = hitung_metrik(y_true, y_prob)
        kurva.append(
            {
                "epoch": epoch,
                "loss_latih": round(total_loss / len(dl_latih), 4),
                "loss_uji": round(loss_uji, 4),
                "akurasi": m["akurasi"],
                "f1": m["f1"],
            }
        )
        print(f"  -> epoch {epoch}: {kurva[-1]}")

    durasi = round(time.time() - mulai, 1)

    # Evaluasi final + artefak
    y_true, y_prob, _ = prediksi_batch(model, dl_uji, device)
    metrik = hitung_metrik(y_true, y_prob)

    out = Path(outdir)
    out.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(out)
    tokenizer.save_pretrained(out)

    metadata = {
        "versi_model": versi_model,
        "tier": 1,
        "tugas": "klasifikasi biner urgensi (rendah/tinggi)",
        "skor": "probabilitas kelas 'tinggi' (0..1)",
        "asal_data": asal_data,
        "base_model": cfg.base_model,
        "hyperparameter": asdict(cfg),
        "data": {
            "train_csv": str(train_csv),
            "test_csv": str(test_csv),
            "latih": ringkasan(baris_latih),
            "uji": ringkasan(baris_uji),
            "split": "80:20 stratified, grup teks-identik tidak terpecah",
        },
        "durasi_latih_detik": durasi,
        "device": str(device),
        "python": platform.python_version(),
        "dilatih_pada": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (out / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (out / "metrics.json").write_text(
        json.dumps({"versi_model": versi_model, "asal_data": asal_data, **metrik}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    _kurva_ke_csv(kurva, out / "kurva_pelatihan.csv")

    print(f"\nArtefak tersimpan di {out.resolve()}")
    print(f"Akurasi={metrik['akurasi']:.4f}  F1={metrik['f1']:.4f}  (versi {versi_model})")
    return {"metrik": metrik, "metadata": metadata, "kurva": kurva}


def main() -> None:
    ap = argparse.ArgumentParser(description="Fine-tune IndoBERT untuk skor urgensi Tier 1.")
    ap.add_argument("--train", default="data/corpus/tier1_train.csv")
    ap.add_argument("--test", default="data/corpus/tier1_test.csv")
    ap.add_argument("--outdir", default="ml/artifacts/indobert")
    ap.add_argument("--base-model", default=BASE_MODEL)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--max-length", type=int, default=128)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--fp16", action="store_true", help="mixed precision (Colab GPU)")
    ap.add_argument("--device", default=None, help="paksa 'cuda' atau 'cpu'")
    ap.add_argument("--asal-data", default="augmentasi", help="augmentasi | publik | lokal")
    ap.add_argument("--versi-model", default=None, help="default: indobert-p1-<asal_data>-vN")
    args = ap.parse_args()

    versi = args.versi_model or f"indobert-p1-{args.asal_data}-v1"
    cfg = KonfigLatih(
        base_model=args.base_model,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
        max_length=args.max_length,
        seed=args.seed,
        fp16=args.fp16,
    )
    train(args.train, args.test, args.outdir, cfg, versi, args.asal_data, args.device)


if __name__ == "__main__":
    main()
