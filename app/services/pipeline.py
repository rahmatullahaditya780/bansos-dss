"""Orkestrasi pipeline analisis: Tier 1 -> Tier 2 (per pengajuan) dan Tier 3 (batch ranking).

Menyimpan keluaran antar-tier dan mencatat durasi ke log_pengujian (FR-25).
Alur OI-15: Tier 3 hanya merangking pengajuan yang diprediksi 'layak' oleh Tier 2.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models
from app.services import explanation, tier1_nlp, tier2_ml, tier3_topsis
from app.services.features import build_features
from app.services.fuzzy_config import load_fuzzy_config


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _urgensi_pengajuan(pengajuan: models.Pengajuan) -> float:
    """Agregasi skor urgensi seluruh narasi pengajuan (ambil maksimum = kasus paling mendesak)."""
    skor = [t.skor_urgensi.skor for t in pengajuan.teks_naratif if t.skor_urgensi is not None]
    return max(skor) if skor else 0.0


def _features_pengajuan(pengajuan: models.Pengajuan, urgensi: float) -> dict[str, float]:
    s = pengajuan.data_survei
    return build_features(
        pendapatan=s.pendapatan,
        jumlah_tanggungan=pengajuan.warga.jumlah_tanggungan,
        usia=pengajuan.warga.usia,
        aset_produktif=s.aset_produktif,
        riwayat_bantuan=s.riwayat_bantuan,
        jenis_lantai=s.jenis_lantai,
        jenis_dinding=s.jenis_dinding,
        sumber_air=s.sumber_air,
        luas_rumah=s.luas_rumah,
        skor_urgensi=urgensi,
    )


def analisis_pengajuan(db: Session, pengajuan: models.Pengajuan) -> dict:
    """Jalankan Tier 1 -> Tier 2 untuk satu pengajuan; simpan hasil & catat durasi."""
    waktu_mulai = _now()

    # --- Tier 1: skor urgensi per narasi (satu forward pass untuk semua narasi) ---
    narasi = list(pengajuan.teks_naratif)
    skor_tier1 = tier1_nlp.score_urgency_batch([t.isi_teks for t in narasi])
    for teks, out in zip(narasi, skor_tier1):
        if teks.skor_urgensi is not None:
            db.delete(teks.skor_urgensi)
            db.flush()
        db.add(
            models.SkorUrgensi(
                teks_naratif_id=teks.id,
                skor=out.skor,
                versi_model=out.versi_model,
                waktu_inference=_now(),
            )
        )
    db.flush()
    db.refresh(pengajuan)

    urgensi = _urgensi_pengajuan(pengajuan)
    features = _features_pengajuan(pengajuan, urgensi)

    # --- Tier 2: klasifikasi kelayakan ---
    pred = tier2_ml.predict_eligibility(features)
    if pengajuan.prediksi_ml is not None:
        db.delete(pengajuan.prediksi_ml)
        db.flush()
    db.add(
        models.PrediksiML(
            pengajuan_id=pengajuan.id,
            hasil=pred.hasil,
            probabilitas=pred.probabilitas,
            versi_model=pred.versi_model,
            waktu_prediksi=_now(),
        )
    )

    alasan = explanation.build_reason(features, urgensi, pred.hasil, pred.probabilitas)

    pengajuan.status = models.StatusPengajuan.DIANALISIS

    # --- Log durasi (FR-25) ---
    waktu_selesai = _now()
    durasi_ms = int((waktu_selesai - waktu_mulai).total_seconds() * 1000)
    db.add(
        models.LogPengujian(
            pengajuan_id=pengajuan.id,
            waktu_mulai=waktu_mulai,
            waktu_selesai=waktu_selesai,
            durasi_ms=durasi_ms,
            hasil_sistem=pred.hasil,
        )
    )
    db.commit()

    return {
        "pengajuan_id": pengajuan.id,
        "skor_urgensi": urgensi,
        "prediksi_ml": {
            "hasil": pred.hasil,
            "probabilitas": pred.probabilitas,
            "versi_model": pred.versi_model,
        },
        "alasan": alasan,
        "durasi_ms": durasi_ms,
    }


def susun_hasil(pengajuan: models.Pengajuan) -> dict:
    """Rakit gabungan hasil tiga tier untuk satu pengajuan (GET /hasil/{id})."""
    urgensi = _urgensi_pengajuan(pengajuan)
    pred = pengajuan.prediksi_ml
    sudah_dianalisis = pred is not None

    prediksi_ml = None
    alasan = None
    if sudah_dianalisis:
        features = _features_pengajuan(pengajuan, urgensi) if pengajuan.data_survei else {}
        prediksi_ml = {
            "hasil": pred.hasil,
            "probabilitas": pred.probabilitas,
            "versi_model": pred.versi_model,
        }
        alasan = explanation.build_reason(features, urgensi, pred.hasil, pred.probabilitas)

    topsis = None
    if pengajuan.ranking:
        latest = max(pengajuan.ranking, key=lambda r: r.created_at)
        topsis = {
            "nilai_preferensi": latest.nilai_preferensi,
            "peringkat": latest.peringkat,
            "batch_id": latest.batch_id,
        }

    durasi = None
    if pengajuan.log_pengujian:
        latest_log = max(pengajuan.log_pengujian, key=lambda log: log.waktu_mulai)
        durasi = latest_log.durasi_ms

    return {
        "pengajuan_id": pengajuan.id,
        "skor_urgensi": round(urgensi, 4) if sudah_dianalisis else None,
        "prediksi_ml": prediksi_ml,
        "topsis": topsis,
        "alasan": alasan,
        "durasi_ms": durasi,
    }


def jalankan_ranking(db: Session, pengajuan_ids: list[int] | None = None) -> dict:
    """Tier 3: rangking pengajuan yang lolos ML (hasil == 'layak'), simpan per batch."""
    cfg = load_fuzzy_config()
    bobot = cfg["bobot"]
    arah = cfg["arah"]

    q = (
        select(models.Pengajuan)
        .join(models.PrediksiML)
        .where(models.PrediksiML.hasil == models.HasilKelayakan.LAYAK)
    )
    if pengajuan_ids:
        q = q.where(models.Pengajuan.id.in_(pengajuan_ids))
    kandidat = db.execute(q).scalars().all()

    alternatives = []
    for p in kandidat:
        urgensi = _urgensi_pengajuan(p)
        f = _features_pengajuan(p, urgensi)
        alternatives.append({"pengajuan_id": p.id, **{k: f[k] for k in bobot.keys()}})

    ranking = tier3_topsis.rank_topsis(alternatives, bobot, arah)

    batch_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    nama_map = {p.id: p.warga.nama for p in kandidat}
    urg_map = {p.id: _urgensi_pengajuan(p) for p in kandidat}

    for entry in ranking:
        db.add(
            models.RankingTopsis(
                batch_id=batch_id,
                pengajuan_id=entry.pengajuan_id,
                nilai_preferensi=entry.nilai_preferensi,
                peringkat=entry.peringkat,
                bobot_snapshot=bobot,
            )
        )
    db.commit()

    return {
        "batch_id": batch_id,
        "jumlah_alternatif": len(ranking),
        "ranking": [
            {
                "peringkat": e.peringkat,
                "pengajuan_id": e.pengajuan_id,
                "warga_nama": nama_map.get(e.pengajuan_id, "-"),
                "nilai_preferensi": e.nilai_preferensi,
                "prediksi": models.HasilKelayakan.LAYAK,
                "skor_urgensi": round(urg_map.get(e.pengajuan_id, 0.0), 4),
            }
            for e in ranking
        ],
    }
