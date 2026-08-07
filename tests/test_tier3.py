"""Tes Tier 3 (Fase 4): Fuzzy TOPSIS, fungsi keanggotaan, seri, dan fallback bertanda.

**Tier 3 tidak punya label kebenaran** — tidak ada "peringkat yang benar" untuk dibandingkan,
sehingga akurasi tidak akan pernah dapat dilaporkan untuknya (evaluasi pra-Fase 4 §5.5). Yang
menggantikan peran metrik di sini adalah `test_perhitungan_manual_*`: satu contoh kecil yang
dihitung tangan sampai digit terakhir, lalu dicocokkan dengan keluaran kode. Bila contoh itu
cocok, aritmetika Chen (2000)-nya benar; bila tidak, ada yang salah — dan tidak ada label yang
akan menangkapnya selain tes ini.

Seperti tes tier lain, berkas ini TIDAK memerlukan artefak model maupun scikit-fuzzy: fungsi
keanggotaan bawaan dipakai bila pustaka tidak terpasang, dan kesetaraan keduanya diuji eksplisit
supaya "cadangan" tidak berarti "diam-diam berbeda".
"""
from __future__ import annotations

import math

import pytest

from app.services import tier3_topsis
from app.services.fuzzy_config import load_fuzzy_config
from ml.tier3 import VERSI_FALLBACK, VERSI_METODE
from ml.tier3.crisp import nilai_preferensi_crisp
from ml.tier3.fuzzy_topsis import jarak_vertex, matriks_fuzzy, rangking
from ml.tier3.keanggotaan import (
    PUSTAKA_MF,
    KonfigurasiKeanggotaanError,
    muat_kriteria,
    trapmf,
    trimf,
)
from ml.tier3.sensitivitas import atribusi, sensitivitas_bobot, statistik_seri

# --------------------------------------------------------------------------------------
# Konfigurasi contoh — dipilih agar aritmetikanya dapat dikerjakan tangan
# --------------------------------------------------------------------------------------
# Dua kriteria, tiga himpunan linguistik masing-masing, domain 0..10. Dengan tiga himpunan,
# TFN wakilnya berpusat di 0 / 0,5 / 1 dengan lebar satu langkah (0,5).
CFG_CONTOH = {
    "keanggotaan": {
        "a": {
            "domain": [0, 10],
            "himpunan": [
                {"nama": "rendah", "bentuk": "segitiga", "titik": [0, 0, 5]},
                {"nama": "sedang", "bentuk": "segitiga", "titik": [0, 5, 10]},
                {"nama": "tinggi", "bentuk": "segitiga", "titik": [5, 10, 10]},
            ],
        },
        "b": {
            "domain": [0, 10],
            "himpunan": [
                {"nama": "rendah", "bentuk": "segitiga", "titik": [0, 0, 5]},
                {"nama": "sedang", "bentuk": "segitiga", "titik": [0, 5, 10]},
                {"nama": "tinggi", "bentuk": "segitiga", "titik": [5, 10, 10]},
            ],
        },
    }
}
BOBOT_CONTOH = {"a": 0.6, "b": 0.4}
ARAH_CONTOH = {"a": "benefit", "b": "cost"}


@pytest.fixture
def kriteria_contoh():
    return muat_kriteria(CFG_CONTOH, ["a", "b"])


# --------------------------------------------------------------------------------------
# Fungsi keanggotaan
# --------------------------------------------------------------------------------------
def test_trimf_titik_penting():
    assert trimf(0, [0, 5, 10]) == 0.0
    assert trimf(5, [0, 5, 10]) == 1.0
    assert trimf(2.5, [0, 5, 10]) == pytest.approx(0.5)
    assert trimf(10, [0, 5, 10]) == 0.0


def test_trimf_puncak_di_ujung_bernilai_penuh():
    """Himpunan terluar ditulis sebagai segitiga berpuncak di ujung domain — puncaknya harus 1,0.

    Bila ini salah, nilai ekstrem kehilangan keanggotaan dan fuzzifikasi jatuh ke cabang darurat.
    """
    assert trimf(0, [0, 0, 5]) == 1.0
    assert trimf(10, [5, 10, 10]) == 1.0


def test_trapmf_plateau():
    assert trapmf(3, [1, 2, 4, 5]) == 1.0
    assert trapmf(1.5, [1, 2, 4, 5]) == pytest.approx(0.5)
    assert trapmf(0, [1, 2, 4, 5]) == 0.0


@pytest.mark.skipif(PUSTAKA_MF != "scikit-fuzzy", reason="scikit-fuzzy tidak terpasang")
def test_keanggotaan_bawaan_setara_scikit_fuzzy():
    """Implementasi cadangan harus identik dengan scikit-fuzzy, bukan sekadar mirip."""
    import numpy as np
    from skfuzzy import membership as skf

    titik_tri = [0.0, 5.0, 10.0]
    titik_trap = [1.0, 3.0, 6.0, 9.0]
    for x in [float(v) / 4 for v in range(-4, 45)]:
        harap_tri = float(skf.trimf(np.asarray([x]), np.asarray(titik_tri))[0])
        harap_trap = float(skf.trapmf(np.asarray([x]), np.asarray(titik_trap))[0])
        assert trimf(x, titik_tri) == pytest.approx(harap_tri)
        assert trapmf(x, titik_trap) == pytest.approx(harap_trap)


def test_fuzzifikasi_derajat_penuh_bukan_satu_himpunan(kriteria_contoh):
    """Nilai di perbatasan dua himpunan menghasilkan TFN campuran, bukan TFN salah satu himpunan.

    Inilah beda varian 'keanggotaan' dari 'kuantisasi linguistik' yang ditolak di §5.2: kuantisasi
    akan memberi (0, 0, 0.5) atau (0, 0.5, 1) apa adanya, dan seluruh nilai di dalam satu himpunan
    menjadi identik.
    """
    kf = kriteria_contoh["a"]
    assert kf.fuzzifikasi(2.5) == pytest.approx((0.0, 0.25, 0.75))
    assert kf.fuzzifikasi(5.0) == pytest.approx((0.0, 0.5, 1.0))
    assert kf.fuzzifikasi(0.0) == pytest.approx((0.0, 0.0, 0.5))
    assert kf.fuzzifikasi(10.0) == pytest.approx((0.5, 1.0, 1.0))


def test_fuzzifikasi_mempertahankan_urutan(kriteria_contoh):
    """Modus TFN harus menaik seiring nilai crisp — kalau tidak, perangkingan kehilangan makna."""
    kf = kriteria_contoh["a"]
    modus = [kf.fuzzifikasi(x / 10)[1] for x in range(0, 101)]
    assert all(modus[i] <= modus[i + 1] + 1e-12 for i in range(len(modus) - 1))
    assert modus[0] < modus[-1]


def test_nilai_di_luar_domain_dijepit(kriteria_contoh):
    kf = kriteria_contoh["a"]
    assert kf.fuzzifikasi(999) == pytest.approx(kf.fuzzifikasi(10))
    assert kf.fuzzifikasi(-999) == pytest.approx(kf.fuzzifikasi(0))


# --------------------------------------------------------------------------------------
# Perhitungan manual — pengganti "akurasi" bagi Tier 3
# --------------------------------------------------------------------------------------
def test_perhitungan_manual_nilai_preferensi(kriteria_contoh):
    """Tiga alternatif simetris, dihitung tangan sampai digit terakhir.

    Alternatif (kriteria a = benefit, b = cost; bobot 0,6 dan 0,4):
        A1: a=10, b=0   -> terbaik pada kedua kriteria
        A2: a=5,  b=5   -> tepat di tengah
        A3: a=0,  b=10  -> terburuk pada kedua kriteria

    Fuzzifikasi   : a -> A1 (0,5;1;1)   A2 (0;0,5;1)   A3 (0;0;0,5)
                    b -> A1 (0;0;0,5)   A2 (0;0,5;1)   A3 (0,5;1;1)
    Komplemen (b cost)  : A1 (0,5;1;1)  A2 (0;0,5;1)   A3 (0;0;0,5)
    Normalisasi (maks u = 1 pada kedua kolom) : tidak mengubah apa pun
    Pembobotan    : a x 0,6 ; b x 0,4

    A1: d+ = sqrt(0,09/3) + sqrt(0,04/3)          = 0,1732051 + 0,1154701 = 0,2886751
        d- = sqrt(0,81/3) + sqrt(0,36/3)          = 0,5196152 + 0,3464102 = 0,8660254
        CC = 0,8660254 / 1,1547005                = 0,75
    A2: d+ = d- (simetris)                        -> CC = 0,50
    A3: cerminan A1                               -> CC = 0,25
    """
    alternatif = [
        {"pengajuan_id": 1, "a": 10.0, "b": 0.0},
        {"pengajuan_id": 2, "a": 5.0, "b": 5.0},
        {"pengajuan_id": 3, "a": 0.0, "b": 10.0},
    ]
    hasil = rangking(alternatif, kriteria_contoh, BOBOT_CONTOH, ARAH_CONTOH)
    nilai = {h.pengajuan_id: h.nilai_preferensi for h in hasil}

    assert nilai[1] == pytest.approx(0.75)
    assert nilai[2] == pytest.approx(0.50)
    assert nilai[3] == pytest.approx(0.25)
    assert [h.pengajuan_id for h in hasil] == [1, 2, 3]
    assert [h.peringkat for h in hasil] == [1, 2, 3]


def test_perhitungan_manual_jarak_vertex():
    """Jarak vertex Chen: akar dari rerata kuadrat selisih ketiga titik."""
    assert jarak_vertex((0.3, 0.6, 0.6), (0.6, 0.6, 0.6)) == pytest.approx(math.sqrt(0.09 / 3))
    assert jarak_vertex((0.3, 0.6, 0.6), (0.0, 0.0, 0.0)) == pytest.approx(math.sqrt(0.81 / 3))
    assert jarak_vertex((0.5, 0.5, 0.5), (0.5, 0.5, 0.5)) == 0.0


def test_kriteria_cost_membalik_preferensi(kriteria_contoh):
    """Pada kriteria cost, nilai lebih kecil harus menghasilkan peringkat lebih tinggi."""
    alternatif = [
        {"pengajuan_id": 1, "a": 5.0, "b": 9.0},
        {"pengajuan_id": 2, "a": 5.0, "b": 1.0},
    ]
    hasil = rangking(alternatif, kriteria_contoh, BOBOT_CONTOH, ARAH_CONTOH)
    assert hasil[0].pengajuan_id == 2


def test_alternatif_dominan_selalu_peringkat_satu(kriteria_contoh):
    """Invarian: alternatif yang lebih baik pada SETIAP kriteria tidak boleh kalah."""
    alternatif = [
        {"pengajuan_id": 1, "a": 3.0, "b": 7.0},
        {"pengajuan_id": 2, "a": 6.0, "b": 4.0},
        {"pengajuan_id": 3, "a": 9.0, "b": 1.0},  # dominan
    ]
    hasil = rangking(alternatif, kriteria_contoh, BOBOT_CONTOH, ARAH_CONTOH)
    assert hasil[0].pengajuan_id == 3


# --------------------------------------------------------------------------------------
# Seri, presisi, dan tiebreak (§5.6)
# --------------------------------------------------------------------------------------
def test_alternatif_kembar_seri_dan_diputus_deterministik(kriteria_contoh):
    """Dua warga berdata identik memang layak bernilai sama; urutannya harus deterministik."""
    alternatif = [
        {"pengajuan_id": 7, "a": 5.0, "b": 5.0},
        {"pengajuan_id": 3, "a": 5.0, "b": 5.0},
    ]
    hasil = rangking(alternatif, kriteria_contoh, BOBOT_CONTOH, ARAH_CONTOH)
    assert hasil[0].nilai_preferensi == hasil[1].nilai_preferensi
    assert hasil[0].seri_dengan == 1
    assert [h.pengajuan_id for h in hasil] == [3, 7]  # pemutus terakhir: id terkecil

    terbalik = rangking(alternatif[::-1], kriteria_contoh, BOBOT_CONTOH, ARAH_CONTOH)
    assert [h.pengajuan_id for h in terbalik] == [3, 7]  # tidak bergantung urutan masukan


def test_tiebreak_terkonfigurasi_dipakai_sebelum_id(kriteria_contoh):
    """Aturan tiebreak dari konfigurasi harus menang atas pemutus terakhir (pengajuan_id)."""
    alternatif = [
        {"pengajuan_id": 1, "a": 5.0, "b": 5.0, "prioritas": 1.0},
        {"pengajuan_id": 2, "a": 5.0, "b": 5.0, "prioritas": 9.0},
    ]
    aturan = [{"kriteria": "prioritas", "arah": "desc"}]
    hasil = rangking(alternatif, kriteria_contoh, BOBOT_CONTOH, ARAH_CONTOH, tiebreak=aturan)
    assert [h.pengajuan_id for h in hasil] == [2, 1]


def test_pengurutan_memakai_presisi_penuh(kriteria_contoh):
    """Beda tipis tidak boleh hilang ditelan pembulatan sebelum pengurutan.

    Ini regresi langsung atas cacat stub Fase 0 (`tier3_topsis.py:65` membulatkan ke 4 desimal
    SEBELUM mengurutkan), yang memproduksi grup seri 14 padahal kembar sejati hanya 10 (§5.6).
    """
    alternatif = [
        {"pengajuan_id": 1, "a": 5.0, "b": 5.0},
        {"pengajuan_id": 2, "a": 5.000001, "b": 5.0},
    ]
    hasil = rangking(alternatif, kriteria_contoh, BOBOT_CONTOH, ARAH_CONTOH)
    assert hasil[0].nilai_preferensi != hasil[1].nilai_preferensi
    assert hasil[0].pengajuan_id == 2
    assert hasil[0].seri_dengan == 0


def test_statistik_seri_menghitung_batas_kuota():
    st = statistik_seri([0.9, 0.5, 0.5, 0.5, 0.1], kuota=3)
    assert st["nilai_unik"] == 3
    assert st["grup_seri_terbesar"] == 3
    assert st["seri_di_batas_kuota"] == 3  # tiga alternatif berbagi nilai di garis potong


# --------------------------------------------------------------------------------------
# Skala logit — regresi atas temuan saturasi (§5.1)
# --------------------------------------------------------------------------------------
def test_skala_logit_membedakan_probabilitas_yang_menjenuh():
    """Probabilitas 0,9997 vs 0,9998 HARUS menghasilkan peringkat berbeda.

    Inilah alasan kriteria urgensi difuzzifikasi dari margin logit, bukan dari probabilitasnya:
    pada skala probabilitas keduanya praktis berimpit, sementara margin logitnya berbeda ~0,5.
    """
    cfg = {
        "keanggotaan": {
            "u": {
                "skala": "logit",
                "domain": [-10, 10],
                "himpunan": [
                    {"nama": "rendah", "bentuk": "segitiga", "titik": [-10, -10, 0]},
                    {"nama": "sedang", "bentuk": "segitiga", "titik": [-10, 0, 10]},
                    {"nama": "tinggi", "bentuk": "segitiga", "titik": [0, 10, 10]},
                ],
            }
        }
    }
    kriteria = muat_kriteria(cfg, ["u"])
    alternatif = [
        {"pengajuan_id": 1, "u": 0.9997},
        {"pengajuan_id": 2, "u": 0.9998},
    ]
    hasil = rangking(alternatif, kriteria, {"u": 1.0}, {"u": "benefit"})
    assert hasil[0].pengajuan_id == 2
    assert hasil[0].nilai_preferensi > hasil[1].nilai_preferensi


def test_margin_eksplisit_dipakai_bila_tersedia():
    """Kunci '<kriteria>_margin' menang atas pembalikan probabilitas."""
    cfg = {
        "keanggotaan": {
            "u": {
                "skala": "logit",
                "domain": [-10, 10],
                "himpunan": [
                    {"nama": "rendah", "bentuk": "segitiga", "titik": [-10, -10, 0]},
                    {"nama": "tinggi", "bentuk": "segitiga", "titik": [-10, 0, 10]},
                ],
            }
        }
    }
    kf = muat_kriteria(cfg, ["u"])["u"]
    assert kf.nilai_crisp(0.5, margin=7.0) == 7.0
    assert kf.nilai_crisp(0.5) == pytest.approx(0.0)  # logit(0,5) = 0


# --------------------------------------------------------------------------------------
# Mode degenerat & atribusi (§5.3)
# --------------------------------------------------------------------------------------
def test_mode_degenerat_menghasilkan_tfn_berlebar_nol(kriteria_contoh):
    alternatif = [{"pengajuan_id": 1, "a": 3.0, "b": 7.0}]
    matriks = matriks_fuzzy(alternatif, kriteria_contoh, mode="degenerat")
    for kolom in matriks.values():
        l, m, u = kolom[0]
        assert l == m == u


def test_atribusi_memisahkan_efek_rumusan_dari_efek_fuzzi(kriteria_contoh):
    """Tabel atribusi harus memuat ketiga baris dan nilai yang terdefinisi."""
    alternatif = [
        {"pengajuan_id": i, "a": float(i % 11), "b": float((i * 3) % 11)} for i in range(1, 21)
    ]
    tabel = atribusi(alternatif, kriteria_contoh, BOBOT_CONTOH, ARAH_CONTOH, kuota=5)
    assert len(tabel) == 3
    assert all(-1.0 <= b["spearman"] <= 1.0 for b in tabel)
    assert all(0.0 <= b["topk_sama"] <= 1.0 for b in tabel)


def test_sensitivitas_bobot_mengembalikan_ukuran_yang_masuk_akal(kriteria_contoh):
    alternatif = [
        {"pengajuan_id": i, "a": float(i % 11), "b": float((i * 7) % 11)} for i in range(1, 31)
    ]
    st = sensitivitas_bobot(
        alternatif, kriteria_contoh, BOBOT_CONTOH, ARAH_CONTOH,
        kuota=10, n_perturbasi=25, goyang=0.2, seed=7,
    )
    assert 0.0 <= st["topk_bertahan"] <= 1.0
    assert st["churn"] == pytest.approx(1.0 - st["topk_bertahan"])
    assert 0.0 <= st["peringkat1_berubah"] <= 1.0


def test_sensitivitas_deterministik_pada_seed_sama(kriteria_contoh):
    alternatif = [
        {"pengajuan_id": i, "a": float(i % 11), "b": float((i * 7) % 11)} for i in range(1, 31)
    ]
    kwargs = dict(kuota=10, n_perturbasi=20, goyang=0.3, seed=99)
    a = sensitivitas_bobot(alternatif, kriteria_contoh, BOBOT_CONTOH, ARAH_CONTOH, **kwargs)
    b = sensitivitas_bobot(alternatif, kriteria_contoh, BOBOT_CONTOH, ARAH_CONTOH, **kwargs)
    assert a == b


# --------------------------------------------------------------------------------------
# Validasi konfigurasi (OI-13) — gagal berisik, bukan diam-diam
# --------------------------------------------------------------------------------------
@pytest.mark.parametrize(
    "rusak, pesan",
    [
        ({"domain": [10, 0], "himpunan": [{"nama": "x", "bentuk": "segitiga", "titik": [0, 1, 2]}]},
         "domain"),
        ({"domain": [0, 10], "himpunan": [{"nama": "x", "bentuk": "segitiga", "titik": [0, 1, 2]}]},
         "minimal dua himpunan"),
        ({"domain": [0, 10], "himpunan": [
            {"nama": "x", "bentuk": "lingkaran", "titik": [0, 1, 2]},
            {"nama": "y", "bentuk": "segitiga", "titik": [1, 2, 3]}]},
         "tidak dikenal"),
        ({"domain": [0, 10], "himpunan": [
            {"nama": "x", "bentuk": "segitiga", "titik": [0, 1]},
            {"nama": "y", "bentuk": "segitiga", "titik": [1, 2, 3]}]},
         "butuh 3 titik"),
        ({"domain": [0, 10], "himpunan": [
            {"nama": "x", "bentuk": "segitiga", "titik": [5, 1, 2]},
            {"nama": "y", "bentuk": "segitiga", "titik": [1, 2, 3]}]},
         "harus menaik"),
        ({"domain": [0, 10], "himpunan": [
            {"nama": "x", "bentuk": "segitiga", "titik": [5, 6, 7]},
            {"nama": "y", "bentuk": "segitiga", "titik": [1, 2, 3]}]},
         "diurutkan menaik"),
    ],
)
def test_konfigurasi_keanggotaan_rusak_ditolak(rusak, pesan):
    with pytest.raises(KonfigurasiKeanggotaanError, match=pesan):
        muat_kriteria({"keanggotaan": {"a": rusak}}, ["a"])


def test_konfigurasi_tanpa_blok_keanggotaan_ditolak():
    with pytest.raises(KonfigurasiKeanggotaanError, match="tidak ada"):
        muat_kriteria({}, ["a"])


# --------------------------------------------------------------------------------------
# Kontrak layanan & fallback bertanda versi
# --------------------------------------------------------------------------------------
def _alternatif_nyata(n: int = 5) -> list[dict]:
    cfg = load_fuzzy_config()
    kriteria = list(cfg["bobot"])
    dasar = {"pendapatan": 800_000.0, "jumlah_tanggungan": 4.0, "housing_need": 0.7,
             "skor_urgensi": 0.9}
    keluar = []
    for i in range(1, n + 1):
        alt = {"pengajuan_id": i}
        for k in kriteria:
            alt[k] = dasar[k] * (1 + 0.1 * i)
        keluar.append(alt)
    return keluar


def test_rank_topsis_mempertahankan_kontrak():
    """Kontrak Fase 0 tidak berubah: pengajuan_id + nilai_preferensi + peringkat berurutan."""
    cfg = load_fuzzy_config()
    hasil = tier3_topsis.rank_topsis(_alternatif_nyata(5), cfg["bobot"], cfg["arah"])
    assert [h.peringkat for h in hasil] == [1, 2, 3, 4, 5]
    nilai = [h.nilai_preferensi for h in hasil]
    assert nilai == sorted(nilai, reverse=True)
    assert all(0.0 <= v <= 1.0 for v in nilai)
    assert {h.pengajuan_id for h in hasil} == {1, 2, 3, 4, 5}


def test_rank_topsis_kosong_dan_tunggal():
    cfg = load_fuzzy_config()
    assert tier3_topsis.rank_topsis([], cfg["bobot"], cfg["arah"]) == []
    satu = tier3_topsis.rank_topsis(_alternatif_nyata(1), cfg["bobot"], cfg["arah"])
    assert len(satu) == 1 and satu[0].peringkat == 1


def test_konfigurasi_nyata_memakai_fuzzy_bukan_fallback():
    """config/fuzzy_config.yaml harus sah — kalau tidak, seluruh sistem diam-diam jadi crisp."""
    info = tier3_topsis.info_fuzzy()
    assert info["fallback_aktif"] is False, info["alasan_fallback"]
    assert info["versi_metode"] == VERSI_METODE
    assert info["skala"]["skor_urgensi"] == "logit"
    assert set(info["kriteria"]) == set(load_fuzzy_config()["bobot"])


def test_fallback_bertanda_saat_keanggotaan_tidak_sah(monkeypatch):
    """Tanpa definisi keanggotaan, sistem tetap merangking — tetapi hasilnya DITANDAI."""
    cfg = dict(load_fuzzy_config())
    cfg["keanggotaan"] = {}
    monkeypatch.setattr(tier3_topsis, "load_fuzzy_config", lambda: cfg)

    hasil = tier3_topsis.rank_topsis(_alternatif_nyata(4), cfg["bobot"], cfg["arah"])
    assert all(h.versi_metode == VERSI_FALLBACK for h in hasil)
    assert [h.peringkat for h in hasil] == [1, 2, 3, 4]
    assert tier3_topsis.info_fuzzy()["fallback_aktif"] is True


def test_label_keanggotaan_untuk_penjelasan():
    """Setiap hasil membawa label linguistik per kriteria (bahan penjelasan ke petugas, FR-23)."""
    cfg = load_fuzzy_config()
    hasil = tier3_topsis.rank_topsis(_alternatif_nyata(3), cfg["bobot"], cfg["arah"])
    for h in hasil:
        assert set(h.keanggotaan) == set(cfg["bobot"])
        assert all(isinstance(v, str) and v for v in h.keanggotaan.values())


def test_fuzzy_berbeda_dari_crisp_pada_data_yang_sama():
    """Fuzzy TOPSIS bukan pembungkus kosmetik: nilainya harus benar-benar berbeda dari crisp.

    Yang diuji hanya bahwa keduanya BEDA. Berapa besar bedanya, dan berapa bagian yang berasal
    dari kefuzzian alih-alih dari rumusan TOPSIS-nya, dijawab tabel atribusi — bukan oleh tes.
    """
    cfg = load_fuzzy_config()
    alternatif = _alternatif_nyata(8)
    fuzzy = [h.nilai_preferensi for h in
             tier3_topsis.rank_topsis(alternatif, cfg["bobot"], cfg["arah"])]
    crisp = sorted(nilai_preferensi_crisp(alternatif, cfg["bobot"], cfg["arah"]), reverse=True)
    assert fuzzy != pytest.approx(crisp)
