"""Orkestrasi pipeline analisis: Tier 1 -> Tier 2 (per pengajuan) dan Tier 3 (batch ranking).

Menyimpan keluaran antar-tier dan mencatat durasi ke log_pengujian (FR-25).
Alur OI-15: Tier 3 hanya merangking pengajuan yang diprediksi 'layak' oleh Tier 2.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import models
from app.services import explanation, tier1_nlp, tier2_ml, tier3_topsis
from app.services.features import build_features
from app.services.fuzzy_config import load_fuzzy_config


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _sudah_hangat() -> bool:
    """True bila kedua artefak model sudah termuat sebelum permintaan ini dilayani.

    Dipakai menandai baris log `cold`/`warm` (D-02). Satu permintaan pertama setelah proses
    dimulai memakan ~14 detik untuk memuat IndoBERT; permintaan berikutnya ~200 ms. Tanpa
    penanda, yang pertama tercatat sebagai pelanggaran NFR-01 padahal ia biaya pemuatan
    (evaluasi pra-Fase 5 §5.3).
    """
    return tier1_nlp.sudah_dimuat() and tier2_ml.sudah_dimuat()


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
    hangat = _sudah_hangat()

    # --- Tier 1: skor urgensi per narasi (satu forward pass untuk semua narasi) ---
    t_tier1 = time.perf_counter()
    narasi = list(pengajuan.teks_naratif)
    skor_tier1 = tier1_nlp.score_urgency_batch([t.isi_teks for t in narasi])
    durasi_tier1_ms = int((time.perf_counter() - t_tier1) * 1000)
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
    t_tier2 = time.perf_counter()
    pred = tier2_ml.predict_eligibility(features)
    durasi_tier2_ms = int((time.perf_counter() - t_tier2) * 1000)
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

    margin = max((o.margin for o in skor_tier1), default=None) if skor_tier1 else None
    alasan = explanation.build_reason(
        features,
        urgensi,
        pred.hasil,
        pred.probabilitas,
        versi_tier1=skor_tier1[0].versi_model if skor_tier1 else None,
        versi_tier2=pred.versi_model,
        margin_urgensi=margin,
    )

    pengajuan.status = models.StatusPengajuan.DIANALISIS

    # --- Log durasi per tier (FR-25, D-03) ---
    waktu_selesai = _now()
    durasi_ms = int((waktu_selesai - waktu_mulai).total_seconds() * 1000)
    db.add(
        models.LogPengujian(
            pengajuan_id=pengajuan.id,
            waktu_mulai=waktu_mulai,
            waktu_selesai=waktu_selesai,
            durasi_ms=durasi_ms,
            durasi_tier1_ms=durasi_tier1_ms,
            durasi_tier2_ms=durasi_tier2_ms,
            jenis_muat="warm" if hangat else "cold",
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
        "durasi_tier1_ms": durasi_tier1_ms,
        "durasi_tier2_ms": durasi_tier2_ms,
        "jenis_muat": "warm" if hangat else "cold",
    }


def jumlah_menunggu_analisis(db: Session) -> int:
    """Berapa pengajuan berdata lengkap yang belum pernah dianalisis."""
    return db.execute(
        select(func.count())
        .select_from(models.Pengajuan)
        .join(models.DataSurvei)
        .outerjoin(models.PrediksiML)
        .where(models.PrediksiML.id.is_(None))
    ).scalar_one()


def analisis_batch(db: Session, limit: int = 25) -> dict:
    """Analisis sekelompok pengajuan yang belum pernah dianalisis (Tier 1 → Tier 2).

    Dashboard menyebut ribuan pengajuan menunggu analisis sementara satu-satunya jalan
    mengerjakannya adalah satu per satu — angka utama halaman itu tidak dapat ditindaklanjuti.
    Fungsi ini **memanggil ulang `analisis_pengajuan()`**, bukan menulis logika tier baru:
    durasi per pengajuan, penanda cold/warm, dan penyimpanan hasil tetap persis sama, sehingga
    FR-25 tidak berubah dan satu baris log tetap berarti satu analisis.

    `limit` sengaja kecil: tiap panggilan harus selesai cepat agar antarmuka dapat memperlihatkan
    kemajuan per gelombang alih-alih menggantung pada satu permintaan panjang.
    """
    kandidat = db.execute(
        select(models.Pengajuan)
        .join(models.DataSurvei)
        .outerjoin(models.PrediksiML)
        .where(models.PrediksiML.id.is_(None))
        .order_by(models.Pengajuan.id)
        .limit(max(1, limit))
    ).scalars().all()

    diproses, gagal = 0, 0
    for p in kandidat:
        try:
            analisis_pengajuan(db, p)
            diproses += 1
        except Exception:  # noqa: BLE001 — satu pengajuan bermasalah tidak boleh menghentikan batch
            db.rollback()
            gagal += 1

    return {
        "diproses": diproses,
        "gagal": gagal,
        "sisa": jumlah_menunggu_analisis(db),
    }


def susun_hasil(pengajuan: models.Pengajuan) -> dict:
    """Rakit gabungan hasil tiga tier untuk satu pengajuan (GET /hasil/{id})."""
    urgensi = _urgensi_pengajuan(pengajuan)
    pred = pengajuan.prediksi_ml
    sudah_dianalisis = pred is not None

    topsis = None
    if pengajuan.ranking:
        latest = max(pengajuan.ranking, key=lambda r: r.created_at)
        snapshot = latest.bobot_snapshot or {}
        topsis = {
            "nilai_preferensi": latest.nilai_preferensi,
            "peringkat": latest.peringkat,
            "batch_id": latest.batch_id,
            "seri_dengan": latest.seri_dengan,
            "keanggotaan": latest.keanggotaan,
            "versi_metode": snapshot.get("versi_metode"),
            "versi_konfigurasi": snapshot.get("versi_konfigurasi"),
        }

    prediksi_ml = None
    alasan = None
    penjelasan = None
    if sudah_dianalisis:
        features = _features_pengajuan(pengajuan, urgensi) if pengajuan.data_survei else {}
        prediksi_ml = {
            "hasil": pred.hasil,
            "probabilitas": pred.probabilitas,
            "versi_model": pred.versi_model,
        }
        versi_t1 = next(
            (t.skor_urgensi.versi_model for t in pengajuan.teks_naratif if t.skor_urgensi), None
        )
        penjelasan = explanation.susun_penjelasan(
            features,
            urgensi,
            pred.hasil,
            pred.probabilitas,
            versi_tier1=versi_t1,
            versi_tier2=pred.versi_model,
            topsis=topsis,
        )
        alasan = penjelasan.teks

    durasi = None
    log_terakhir = None
    if pengajuan.log_pengujian:
        log_terakhir = max(pengajuan.log_pengujian, key=lambda log: log.waktu_mulai)
        durasi = log_terakhir.durasi_ms

    return {
        "pengajuan_id": pengajuan.id,
        "skor_urgensi": round(urgensi, 4) if sudah_dianalisis else None,
        "prediksi_ml": prediksi_ml,
        "topsis": topsis,
        "alasan": alasan,
        "penjelasan": penjelasan,
        "durasi_ms": durasi,
        "durasi_tier1_ms": log_terakhir.durasi_tier1_ms if log_terakhir else None,
        "durasi_tier2_ms": log_terakhir.durasi_tier2_ms if log_terakhir else None,
        "jenis_muat": log_terakhir.jenis_muat if log_terakhir else None,
    }


def jalankan_ranking(db: Session, pengajuan_ids: list[int] | None = None) -> dict:
    """Tier 3: rangking pengajuan yang lolos ML (hasil == 'layak'), simpan per batch.

    Kriteria urgensi difuzzifikasi dari **margin logit**, bukan dari probabilitasnya — lihat
    `ml/tier3/keanggotaan.py`. Margin itu tidak disimpan tersendiri di basis data; ia diturunkan
    kembali dari `skor_urgensi.skor` (bijektif, dan sejak Fase 4 skor disimpan presisi penuh).
    Baris yang dianalisis SEBELUM Fase 4 tersimpan terbulat 4 desimal dan karenanya kehilangan
    daya beda pada kriteria ini sampai pengajuannya dianalisis ulang lewat `POST /analisis`.
    """
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

    t_tier3 = time.perf_counter()
    ranking = tier3_topsis.rank_topsis(alternatives, bobot, arah)
    durasi_tier3_ms = int((time.perf_counter() - t_tier3) * 1000)

    batch_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    nama_map = {p.id: p.warga.nama for p in kandidat}
    urg_map = {p.id: _urgensi_pengajuan(p) for p in kandidat}
    versi_metode = ranking[0].versi_metode if ranking else tier3_topsis.VERSI_METODE

    # Snapshot lengkap, bukan sekadar bobot: peringkat lama harus dapat ditelusuri ke SELURUH
    # konfigurasi yang menghasilkannya — termasuk versi berkas, aturan tiebreak, dan apakah batch
    # ini benar-benar dirangking Fuzzy TOPSIS atau oleh cadangan crisp.
    snapshot = {
        "bobot": dict(bobot),
        "arah": dict(arah),
        "versi_konfigurasi": cfg.get("versi"),
        "versi_metode": versi_metode,
        "tiebreak": cfg.get("tiebreak") or [],
    }

    for entry in ranking:
        db.add(
            models.RankingTopsis(
                batch_id=batch_id,
                pengajuan_id=entry.pengajuan_id,
                nilai_preferensi=entry.nilai_preferensi,
                peringkat=entry.peringkat,
                bobot_snapshot=snapshot,
                # Bahan penjelasan Tier 3 (OI-07): sudah dihitung `rank_topsis()` sejak Fase 4,
                # tetapi sampai Fase 5 dibuang di sini sehingga petugas tidak pernah tahu mengapa
                # sebuah pengajuan berada di posisinya (evaluasi pra-Fase 5 §5.2).
                jarak_positif=entry.jarak_positif,
                jarak_negatif=entry.jarak_negatif,
                seri_dengan=entry.seri_dengan,
                keanggotaan=entry.keanggotaan or None,
            )
        )

    # Durasi Tier 3 dicatat PER BATCH — membaginya ke tiap pengajuan akan mengarang angka
    # per-pengajuan yang tidak pernah diukur (D-03).
    db.add(
        models.LogRanking(
            batch_id=batch_id,
            jumlah_alternatif=len(ranking),
            durasi_ms=durasi_tier3_ms,
            versi_metode=versi_metode,
            versi_konfigurasi=cfg.get("versi"),
        )
    )
    db.commit()

    return {
        "batch_id": batch_id,
        "jumlah_alternatif": len(ranking),
        "versi_metode": versi_metode,
        "versi_konfigurasi": cfg.get("versi"),
        "durasi_ms": durasi_tier3_ms,
        "ranking": [
            {
                "peringkat": e.peringkat,
                "pengajuan_id": e.pengajuan_id,
                "warga_nama": nama_map.get(e.pengajuan_id, "-"),
                "nilai_preferensi": e.nilai_preferensi,
                "prediksi": models.HasilKelayakan.LAYAK,
                "skor_urgensi": round(urg_map.get(e.pengajuan_id, 0.0), 4),
                "seri_dengan": e.seri_dengan,
                "keanggotaan": e.keanggotaan,
            }
            for e in ranking
        ],
    }
