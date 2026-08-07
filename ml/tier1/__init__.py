"""Tier 1 — skor urgensi teks naratif dengan IndoBERT.

Submodul:
- `preprocessing` : pembersihan teks (FR-11), dipakai bersama saat latih & inference
- `corpus`        : pembangkit korpus naratif berlabel (augmentasi) untuk validasi pipeline
- `dataset`       : pemuatan CSV + split latih/uji 80:20 stratified tanpa kebocoran
- `train`         : fine-tuning `indobert-base-p1` (klasifikasi biner urgensi)
- `evaluate`      : Akurasi, F1, precision/recall, confusion matrix per versi model
- `infer`         : pemuatan artefak & skoring probabilitas kelas 'tinggi' (0..1)
"""

LABELS = ["rendah", "tinggi"]
LABEL2ID = {label: i for i, label in enumerate(LABELS)}
ID2LABEL = {i: label for i, label in enumerate(LABELS)}

BASE_MODEL = "indobenchmark/indobert-base-p1"
