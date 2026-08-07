"""FR-11 — Preprocessing teks naratif Bahasa Indonesia.

Satu-satunya sumber kebenaran pembersihan teks: dipakai identik saat **pelatihan** dan saat
**inference**, sehingga tidak ada train/serve skew.

Tahapan `preprocess()` (ringan, mempertahankan makna kalimat untuk BERT):
1. normalisasi unicode & spasi (termasuk newline/tab dari isian formulir),
2. lowercasing (IndoBERT p1 adalah model *uncased*),
3. pembuangan artefak non-informatif (URL, email, NIK/angka panjang, karakter aneh),
4. normalisasi singkatan/slang umum laporan petugas (`tdk` → `tidak`, `yg` → `yang`, …),
5. pemadatan pengulangan huruf berlebih (`sakiiiit` → `sakiit`).

Catatan: **tidak** dilakukan stemming/stopword removal pada jalur BERT — subword tokenizer
IndoBERT justru memerlukan bentuk kata utuh, dan stopword membawa informasi negasi
("tidak ada yang sakit") yang penting untuk label urgensi. Utilitas Sastrawi/NLTK disediakan
terpisah di `stem_tokens()` untuk keperluan analisis/baseline non-BERT saja.
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

# Singkatan & slang yang lazim muncul pada catatan lapangan petugas kelurahan.
_SINGKATAN = {
    "tdk": "tidak", "tk": "tidak", "gk": "tidak", "ga": "tidak", "gak": "tidak",
    "nggak": "tidak", "engga": "tidak", "enggak": "tidak", "tp": "tapi", "krn": "karena",
    "krna": "karena", "karna": "karena", "dgn": "dengan", "dg": "dengan", "yg": "yang",
    "sdh": "sudah", "udh": "sudah", "udah": "sudah", "blm": "belum", "blum": "belum",
    "utk": "untuk", "u/": "untuk", "dlm": "dalam", "dr": "dari", "kk": "kepala keluarga",
    "rt": "rumah tangga", "ortu": "orang tua", "anak2": "anak anak", "org": "orang",
    "sakit2an": "sakit sakitan", "pny": "punya", "pnya": "punya", "hrs": "harus",
    "bs": "bisa", "bsa": "bisa", "jd": "jadi", "sy": "saya", "ybs": "yang bersangkutan",
    "thn": "tahun", "bln": "bulan", "rmh": "rumah", "pekerjaan": "pekerjaan",
}

_RE_URL = re.compile(r"https?://\S+|www\.\S+")
_RE_EMAIL = re.compile(r"\S+@\S+\.\S+")
_RE_ANGKA_PANJANG = re.compile(r"\b\d{6,}\b")          # NIK/KK/no. telepon → tidak informatif
_RE_NON_TEKS = re.compile(r"[^a-z0-9\s.,!?/-]")
_RE_ULANG = re.compile(r"(.)\1{2,}")                    # sakiiiit -> sakiit
_RE_SPASI = re.compile(r"\s+")
_RE_TANDA_BACA_ULANG = re.compile(r"([.,!?])\1+")


def preprocess(text: str) -> str:
    """Bersihkan satu teks naratif. Aman untuk input `None`/kosong (mengembalikan string kosong)."""
    if not text:
        return ""

    text = unicodedata.normalize("NFKC", str(text))
    text = text.lower()
    text = _RE_URL.sub(" ", text)
    text = _RE_EMAIL.sub(" ", text)
    text = _RE_ANGKA_PANJANG.sub(" ", text)
    text = _RE_NON_TEKS.sub(" ", text)
    text = _RE_ULANG.sub(r"\1\1", text)
    text = _RE_TANDA_BACA_ULANG.sub(r"\1", text)

    kata = [_SINGKATAN.get(k, k) for k in text.split()]
    text = " ".join(kata)

    # Rapikan spasi sebelum tanda baca yang tersisa.
    text = re.sub(r"\s+([.,!?])", r"\1", text)
    return _RE_SPASI.sub(" ", text).strip()


@lru_cache(maxsize=1)
def _stemmer():
    """Stemmer Sastrawi (lazy — pustaka hanya diperlukan untuk baseline non-BERT)."""
    from Sastrawi.Stemmer.StemmerFactory import StemmerFactory

    return StemmerFactory().create_stemmer()


@lru_cache(maxsize=1)
def _stopwords() -> frozenset[str]:
    from Sastrawi.StopWordRemover.StopWordRemoverFactory import StopWordRemoverFactory

    return frozenset(StopWordRemoverFactory().get_stop_words())


def stem_tokens(text: str, buang_stopword: bool = True) -> list[str]:
    """Tokenisasi + stemming Sastrawi — **hanya** untuk baseline/analisis kata, bukan jalur BERT.

    Kata negasi (`tidak`, `bukan`, `belum`, `tanpa`) sengaja dipertahankan meski masuk daftar
    stopword, karena membalik makna urgensi.
    """
    negasi = {"tidak", "bukan", "belum", "tanpa", "jangan"}
    stop = _stopwords() - negasi if buang_stopword else frozenset()
    bersih = preprocess(text)
    stemmer = _stemmer()
    return [stemmer.stem(t) for t in re.findall(r"[a-z0-9]+", bersih) if t not in stop]
