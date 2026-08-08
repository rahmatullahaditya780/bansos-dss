"""Inference Tier 1 (FR-12…FR-14): skor urgensi = probabilitas kelas 'tinggi' (0..1).

Dipakai oleh `app/services/tier1_nlp.py` di dalam siklus permintaan HTTP, sehingga:
- **pemuatan malas & sekali saja** (singleton) — model tidak dimuat ulang tiap permintaan;
- **thread-safe** — FastAPI menjalankan endpoint sinkron di thread pool;
- **degradasi anggun** — bila artefak/pustaka ML tidak tersedia, sistem tetap berjalan memakai
  heuristik cadangan dan menandainya lewat `versi_model`, sehingga hasil tak pernah disangka
  berasal dari model asli.
"""
from __future__ import annotations

import json
import logging
import math
import threading
from dataclasses import dataclass
from pathlib import Path

from ml.tier1 import LABEL2ID
from ml.tier1.preprocessing import preprocess

logger = logging.getLogger(__name__)

VERSI_FALLBACK = "heuristik-fallback-v0"

# Penjepit probabilitas saat membalik ke logit — mencegah pembagian nol pada p tepat 0 atau 1.
# Batas ini setara margin +-27,6; jauh di luar rentang teramati (-8,6..+8,7).
_EPS_PROB = 1e-12

# Bobot kata kunci untuk heuristik cadangan (dipertahankan dari stub Fase 0).
_KATA_URGEN = {
    "meninggal": 3, "sakit": 2, "kronis": 3, "cacat": 3, "disabilitas": 3,
    "darurat": 3, "kelaparan": 3, "tidak mampu": 2, "menganggur": 2, "phk": 2,
    "hutang": 1, "terlilit": 2, "yatim": 2, "piatu": 2, "lansia": 2, "jompo": 2,
    "bocor": 1, "gubuk": 2, "roboh": 3, "menumpang": 2, "putus sekolah": 2,
    "bayi": 1, "balita": 1, "hamil": 1, "stunting": 2,
}


@dataclass(frozen=True)
class HasilSkor:
    skor: float            # probabilitas kelas 'tinggi', 0..1
    versi_model: str
    fallback: bool = False
    margin: float | None = None  # logit('tinggi') - logit('rendah'); None bila dari heuristik

    @property
    def margin_efektif(self) -> float:
        """Margin logit; diturunkan dari probabilitas bila model tidak menyediakannya langsung.

        Dipakai Tier 3 sebagai nilai crisp kriteria urgensi. Probabilitas **tidak** dapat dipakai
        apa adanya: pada model yang memisahkan kelas dengan sangat baik, softmax menjenuh dan
        seluruh kasus mendesak menumpuk di ~0,9998 — 991 alternatif hanya menghasilkan 5 nilai
        berbeda (evaluasi pra-Fase 4 §5.1). Margin logit-nya membentang -8,6..+8,7 dengan resolusi
        utuh; informasi urutannya tidak hilang di model, melainkan di sigmoid.
        """
        if self.margin is not None:
            return self.margin
        p = min(max(self.skor, _EPS_PROB), 1.0 - _EPS_PROB)
        return math.log(p / (1.0 - p))


def skor_heuristik(text: str) -> float:
    """Cadangan tanpa model: penjumlahan bobot kata kunci, dinormalisasi ke 0..1.

    Sengaja kasar — hanya menjaga sistem tetap berjalan saat artefak belum diunduh.
    """
    clean = preprocess(text)
    bobot = sum(w for kata, w in _KATA_URGEN.items() if kata in clean)
    skor = min(1.0, bobot / 8.0)
    if len(clean) < 40:
        skor *= 0.7
    return round(skor, 4)


class UrgencyScorer:
    """Pemuat & pemanggil model IndoBERT hasil fine-tuning."""

    def __init__(self, model_path: str | Path, max_length: int = 128, device: str | None = None) -> None:
        self.model_path = Path(model_path)
        self.max_length = max_length
        self._device_paksa = device
        self._lock = threading.Lock()
        self._model = None
        self._tokenizer = None
        self._device = None
        self._versi_model: str | None = None
        self._gagal: str | None = None      # alasan fallback (dicatat sekali)

    # -- pemuatan -----------------------------------------------------------
    def tersedia(self) -> bool:
        """True bila artefak ada di disk (belum tentu sudah dimuat)."""
        return (self.model_path / "config.json").exists()

    def sudah_dimuat(self) -> bool:
        """True bila artefak sudah berada di memori — **tanpa memicu pemuatan**.

        Dipakai menandai baris log `cold`/`warm` (Fase 5, D-02). Sengaja tidak memakai `info()`:
        `info()` Tier 2 memaksa pemuatan lebih dulu, sehingga memanggilnya untuk *mengukur* biaya
        pemuatan justru memindahkan biaya itu ke luar rentang yang diukur.
        """
        return self._model is not None

    @property
    def versi_model(self) -> str:
        if self._versi_model is None:
            self._versi_model = self._baca_versi()
        return self._versi_model

    def _baca_versi(self) -> str:
        meta = self.model_path / "metadata.json"
        if meta.exists():
            try:
                return json.loads(meta.read_text(encoding="utf-8"))["versi_model"]
            except (json.JSONDecodeError, KeyError, OSError):
                logger.warning("metadata.json Tier 1 tidak terbaca; versi model memakai nama folder")
        return f"indobert-{self.model_path.name}"

    def _muat(self) -> bool:
        """Muat model sekali; kembalikan False bila tidak memungkinkan (pakai fallback)."""
        if self._model is not None:
            return True
        if self._gagal is not None:
            return False

        with self._lock:
            if self._model is not None:
                return True
            if self._gagal is not None:
                return False
            try:
                if not self.tersedia():
                    raise FileNotFoundError(f"artefak tidak ditemukan di {self.model_path.resolve()}")
                import torch
                from transformers import AutoModelForSequenceClassification, AutoTokenizer

                self._device = torch.device(
                    self._device_paksa or ("cuda" if torch.cuda.is_available() else "cpu")
                )
                self._tokenizer = AutoTokenizer.from_pretrained(self.model_path)
                model = AutoModelForSequenceClassification.from_pretrained(self.model_path)
                model.to(self._device).eval()
                self._model = model
                logger.info(
                    "Tier 1: model %s dimuat dari %s (%s)",
                    self.versi_model, self.model_path, self._device,
                )
                return True
            except Exception as exc:  # noqa: BLE001 — apa pun penyebabnya, sistem harus tetap jalan
                self._gagal = str(exc)
                logger.warning(
                    "Tier 1: gagal memuat IndoBERT (%s). Memakai heuristik cadangan '%s' — "
                    "skor BUKAN keluaran model dan tidak sah untuk klaim evaluasi.",
                    exc, VERSI_FALLBACK,
                )
                return False

    # -- skoring ------------------------------------------------------------
    def score(self, text: str) -> HasilSkor:
        return self.score_batch([text])[0]

    def score_batch(self, texts: list[str]) -> list[HasilSkor]:
        """Skor beberapa teks sekaligus (satu forward pass) — dipakai saat analisis batch."""
        if not texts:
            return []
        if not self._muat():
            return [HasilSkor(skor_heuristik(t), VERSI_FALLBACK, fallback=True) for t in texts]

        import torch

        bersih = [preprocess(t) for t in texts]
        enc = self._tokenizer(
            bersih, truncation=True, padding=True, max_length=self.max_length, return_tensors="pt"
        ).to(self._device)
        with torch.no_grad():
            logits = self._model(**enc).logits
        prob = torch.softmax(logits, dim=-1)[:, LABEL2ID["tinggi"]].cpu().tolist()
        # Margin logit disimpan berdampingan dengan probabilitas: ia yang dipakai Tier 3, karena
        # softmax meremas seluruh kasus mendesak ke satu titik (lihat `HasilSkor.margin_efektif`).
        selisih = (logits[:, LABEL2ID["tinggi"]] - logits[:, LABEL2ID["rendah"]]).cpu().tolist()
        # Probabilitas TIDAK dibulatkan di sini. Pembulatan 4 desimal yang dulu ada di baris ini
        # adalah pembulatan untuk tampilan yang bocor ke perhitungan — kekeliruan yang sama dengan
        # `tier3_topsis.py` yang membulatkan sebelum mengurutkan. Bulatkan saat menampilkan.
        return [
            HasilSkor(float(p), self.versi_model, margin=float(m)) for p, m in zip(prob, selisih)
        ]

    def info(self) -> dict[str, object]:
        """Status pemuatan — dipakai untuk diagnostik/dokumentasi hasil.

        Pemuatan sengaja **dipaksa** lebih dulu, menyamai `info()` Tier 2. Tanpa itu
        `fallback_aktif` selalu `False` sebelum skoring pertama — persis kebalikan dari yang ingin
        diketahui orang yang memanggilnya untuk memastikan artefak sudah terpasang. Perilaku lama
        tercatat sebagai warisan sejak evaluasi pra-Fase 4 §2 dan **sempat membuat pemanasan
        startup Fase 5 menjadi no-op untuk Tier 1**: aplikasi mengira sudah memanaskan model,
        sementara permintaan pertama tetap menanggung 10 detik pemuatan.
        """
        self._muat()
        return {
            "model_path": str(self.model_path),
            "tersedia": self.tersedia(),
            "dimuat": self._model is not None,
            "versi_model": self.versi_model if self.tersedia() else VERSI_FALLBACK,
            "fallback_aktif": self._gagal is not None,
            "alasan_fallback": self._gagal,
        }


_scorer: UrgencyScorer | None = None
_scorer_lock = threading.Lock()


def get_scorer(model_path: str | Path | None = None, max_length: int = 128) -> UrgencyScorer:
    """Kembalikan singleton scorer. `model_path` default dari `settings.indobert_model_path`."""
    global _scorer
    if model_path is None:
        from app.core.config import settings

        model_path = settings.indobert_model_path
    if _scorer is None or Path(model_path) != _scorer.model_path:
        with _scorer_lock:
            if _scorer is None or Path(model_path) != _scorer.model_path:
                _scorer = UrgencyScorer(model_path, max_length=max_length)
    return _scorer


def reset_scorer() -> None:
    """Lepas singleton (dipakai di tes / setelah artefak baru diunduh)."""
    global _scorer
    with _scorer_lock:
        _scorer = None
