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


templates.env.filters["rupiah"] = rupiah
templates.env.filters["persen"] = persen
templates.env.filters["skor"] = skor
