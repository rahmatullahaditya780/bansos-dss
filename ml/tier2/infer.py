"""Inference Tier 2 (FR-15…FR-17): kelayakan = probabilitas kelas 'layak' (0..1) + label.

Dipakai oleh `app/services/tier2_ml.py` di dalam siklus permintaan HTTP, sehingga menganut tiga
sifat yang sama dengan Tier 1:

- **pemuatan malas & sekali saja** (singleton) — artefak tidak dibaca ulang tiap permintaan;
- **thread-safe** — FastAPI menjalankan endpoint sinkron di thread pool;
- **degradasi anggun** — bila artefak/pustaka tidak tersedia, sistem tetap berjalan memakai skor
  logistik Fase 0 dan menandainya lewat `versi_model`, sehingga hasil non-model tak pernah
  disangka berasal dari model terlatih.

Tambahan khas Tier 2: **urutan fitur diverifikasi saat pemuatan**. Model scikit-learn menerima
array polos tanpa nama kolom, jadi urutan yang bergeser tidak menimbulkan galat apa pun — hanya
prediksi yang salah secara senyap. `periksa_skema` mengubahnya menjadi kegagalan yang berisik.
"""
from __future__ import annotations

import json
import logging
import math
import threading
from dataclasses import dataclass
from pathlib import Path

from ml.tier2 import KELAS_POSITIF, LABEL2ID, NAMA_BERKAS_MODEL, VERSI_FALLBACK
from ml.tier2.skema_fitur import periksa_skema, vektor

logger = logging.getLogger(__name__)

ID_POSITIF = LABEL2ID[KELAS_POSITIF]
AMBANG = 0.5


@dataclass(frozen=True)
class HasilPrediksi:
    hasil: str           # 'layak' | 'tidak_layak'
    probabilitas: float  # probabilitas kelas 'layak', 0..1
    versi_model: str
    fallback: bool = False


def skor_logistik(features: dict[str, float]) -> float:
    """Cadangan tanpa model: skor logistik berbobot tangan, dipertahankan dari stub Fase 0.

    Sengaja kasar — hanya menjaga sistem tetap berjalan saat artefak belum ada.
    """
    pendapatan = features.get("pendapatan", 0.0)
    tanggungan = features.get("jumlah_tanggungan", 0.0)
    housing = features.get("housing_need", 0.5)
    urgensi = features.get("skor_urgensi", 0.0)
    aset = features.get("aset_produktif", 0.0)
    riwayat = features.get("riwayat_bantuan", 0.0)

    z = (
        1.4
        - 1.1 * (pendapatan / 1_000_000.0)
        + 0.35 * tanggungan
        + 1.5 * housing
        + 1.2 * urgensi
        - 0.8 * aset
        - 0.3 * riwayat
    )
    return round(1.0 / (1.0 + math.exp(-z)), 4)


def _ke_hasil(prob: float, versi: str, fallback: bool = False) -> HasilPrediksi:
    label = KELAS_POSITIF if prob >= AMBANG else "tidak_layak"
    return HasilPrediksi(hasil=label, probabilitas=round(float(prob), 4), versi_model=versi,
                         fallback=fallback)


class EligibilityClassifier:
    """Pemuat & pemanggil artefak klasifikasi kelayakan (RF/GB hasil `ml.tier2.train`)."""

    def __init__(self, model_path: str | Path) -> None:
        self.model_path = Path(model_path)
        self._lock = threading.Lock()
        self._model = None
        self._metadata: dict | None = None
        self._versi_model: str | None = None
        self._gagal: str | None = None  # alasan fallback (dicatat sekali)

    # -- pemuatan -----------------------------------------------------------
    def tersedia(self) -> bool:
        """True bila artefak ada di disk (belum tentu sudah dimuat)."""
        return (self.model_path / NAMA_BERKAS_MODEL).exists()

    def sudah_dimuat(self) -> bool:
        """True bila artefak sudah berada di memori — **tanpa memicu pemuatan**.

        Dipakai menandai baris log `cold`/`warm` (Fase 5, D-02). `info()` sengaja memaksa
        pemuatan; memanggilnya untuk mengukur biaya pemuatan akan memindahkan biaya itu ke luar
        rentang yang sedang diukur.
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
                logger.warning("metadata.json Tier 2 tidak terbaca; versi memakai nama folder")
        return f"tier2-{self.model_path.name}"

    def _muat(self) -> bool:
        """Muat artefak sekali; kembalikan False bila tidak memungkinkan (pakai fallback)."""
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
                import joblib

                metadata = json.loads(
                    (self.model_path / "metadata.json").read_text(encoding="utf-8")
                )
                periksa_skema(metadata["fitur"])
                self._peringatkan_versi_sklearn(metadata)
                self._model = joblib.load(self.model_path / NAMA_BERKAS_MODEL)
                self._metadata = metadata
                logger.info(
                    "Tier 2: model %s (%s) dimuat dari %s",
                    self.versi_model, metadata.get("algoritma", "?"), self.model_path,
                )
                return True
            except Exception as exc:  # noqa: BLE001 — apa pun sebabnya, sistem harus tetap jalan
                self._gagal = str(exc)
                logger.warning(
                    "Tier 2: gagal memuat artefak (%s). Memakai skor logistik cadangan '%s' — "
                    "hasil BUKAN keluaran model dan tidak sah untuk klaim evaluasi.",
                    exc, VERSI_FALLBACK,
                )
                return False

    @staticmethod
    def _peringatkan_versi_sklearn(metadata: dict) -> None:
        """Artefak joblib rapuh lintas versi — beritahu, jangan gagal diam-diam."""
        import sklearn

        dilatih = metadata.get("scikit_learn")
        if dilatih and dilatih != sklearn.__version__:
            logger.warning(
                "Tier 2: artefak dilatih dengan scikit-learn %s, sekarang %s. "
                "Prediksi mungkin bergeser; latih ulang bila hasil terasa janggal.",
                dilatih, sklearn.__version__,
            )

    # -- prediksi -----------------------------------------------------------
    def predict(self, features: dict[str, float]) -> HasilPrediksi:
        return self.predict_batch([features])[0]

    def predict_batch(self, daftar_features: list[dict[str, float]]) -> list[HasilPrediksi]:
        """Prediksi beberapa pengajuan sekaligus (satu panggilan `predict_proba`)."""
        if not daftar_features:
            return []
        if not self._muat():
            return [
                _ke_hasil(skor_logistik(f), VERSI_FALLBACK, fallback=True) for f in daftar_features
            ]

        X = [vektor(f) for f in daftar_features]
        prob = self._model.predict_proba(X)[:, ID_POSITIF]
        return [_ke_hasil(p, self.versi_model) for p in prob]

    def info(self) -> dict[str, object]:
        """Status pemuatan — dipakai untuk diagnostik/dokumentasi hasil.

        Pemuatan sengaja **dipaksa** lebih dulu. Tanpa itu `fallback_aktif` selalu `False` sebelum
        prediksi pertama — persis kebalikan dari yang ingin diketahui orang yang memanggil fungsi
        ini untuk memverifikasi bahwa artefak sudah terpasang benar.
        """
        self._muat()
        return {
            "model_path": str(self.model_path),
            "tersedia": self.tersedia(),
            "dimuat": self._model is not None,
            "versi_model": self.versi_model if self.tersedia() else VERSI_FALLBACK,
            "algoritma": (self._metadata or {}).get("algoritma"),
            "asal_data": (self._metadata or {}).get("asal_data"),
            "fallback_aktif": self._gagal is not None,
            "alasan_fallback": self._gagal,
        }


_classifier: EligibilityClassifier | None = None
_classifier_lock = threading.Lock()


def get_classifier(model_path: str | Path | None = None) -> EligibilityClassifier:
    """Kembalikan singleton classifier. `model_path` default dari `settings.ml_model_path`."""
    global _classifier
    if model_path is None:
        from app.core.config import settings

        model_path = settings.ml_model_path
    if _classifier is None or Path(model_path) != _classifier.model_path:
        with _classifier_lock:
            if _classifier is None or Path(model_path) != _classifier.model_path:
                _classifier = EligibilityClassifier(model_path)
    return _classifier


def reset_classifier() -> None:
    """Lepas singleton (dipakai di tes / setelah artefak baru dilatih)."""
    global _classifier
    with _classifier_lock:
        _classifier = None
