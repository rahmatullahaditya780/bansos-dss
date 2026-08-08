"""Setup Jinja2Templates + filter kustom (dipakai rute web)."""
from __future__ import annotations

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="app/templates")


def rupiah(value: float | int | None) -> str:
    if value is None:
        return "-"
    return "Rp" + f"{int(value):,}".replace(",", ".")


def persen(value: float | None) -> str:
    return "-" if value is None else f"{value:.1f}%"


def skor(value: float | None) -> str:
    return "-" if value is None else f"{value:.2f}"


def milidetik(value: float | int | None) -> str:
    """Durasi terbaca manusia. `None` -> '-' (belum terukur), BUKAN '0 ms'."""
    if value is None:
        return "-"
    return f"{value / 1000:.1f} s" if value >= 1000 else f"{int(value)} ms"


def label_rapi(value: str | None) -> str:
    """`sangat_buruk` -> `sangat buruk`."""
    return "-" if not value else str(value).replace("_", " ")


templates.env.filters["rupiah"] = rupiah
templates.env.filters["persen"] = persen
templates.env.filters["skor"] = skor
templates.env.filters["milidetik"] = milidetik
templates.env.filters["label_rapi"] = label_rapi
