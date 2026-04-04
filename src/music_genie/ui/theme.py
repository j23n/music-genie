"""Flexoki-based color theme with automatic dark/light detection."""

from __future__ import annotations

import os

from rich.console import Console
from rich.style import Style
from rich.theme import Theme

# ---------------------------------------------------------------------------
# Flexoki palette  (https://stephango.com/flexoki)
#
# The base scale mirrors itself: paper <-> black, base-50 <-> base-950, etc.
# Accent colours use the -400 variants in dark mode (brighter) and
# -600 variants in light mode (deeper) for proper contrast.
# ---------------------------------------------------------------------------

_FLEXOKI = {
    "dark": {
        # Accents (-400 variants for dark backgrounds)
        "red": "#D14D41",
        "orange": "#DA702C",
        "yellow": "#D0A215",
        "green": "#879A39",
        "cyan": "#3AA99F",
        "blue": "#4385BE",
        "purple": "#8B7EC8",
        "magenta": "#CE5D97",
        # Base scale
        "tx": "#FFFCF0",       # paper  – primary text
        "tx2": "#878580",       # base-500 – secondary text
        "tx3": "#6F6E69",       # base-600 – muted text
        "ui": "#403E3C",        # base-800 – border
        "ui2": "#575653",       # base-700 – strong border
        "ui3": "#343331",       # base-850 – subtle border / highlight
        "bg": "#100F0F",        # black – background
        "bg2": "#1C1B1A",       # base-950 – surface
    },
    "light": {
        # Accents (-600 variants for light backgrounds)
        "red": "#AF3029",
        "orange": "#BC5215",
        "yellow": "#AD8301",
        "green": "#66800B",
        "cyan": "#24837B",
        "blue": "#205EA6",
        "purple": "#5E409D",
        "magenta": "#A02F6F",
        # Base scale (mirrored)
        "tx": "#100F0F",        # black – primary text
        "tx2": "#878580",       # base-500 – secondary text
        "tx3": "#9F9D96",       # base-400 – muted text
        "ui": "#CECDC3",        # base-200 – border
        "ui2": "#B7B5AC",       # base-300 – strong border
        "ui3": "#E6E4D9",       # base-100 – subtle border / highlight
        "bg": "#FFFCF0",        # paper – background
        "bg2": "#F2F0E5",       # base-50 – surface
    },
}


def _detect_scheme() -> str:
    """Detect whether the terminal is dark or light.

    Checks (in order):
    1. ``MUSIC_GENIE_THEME`` env var (``dark`` / ``light``)
    2. ``COLORFGBG`` env var (``<fg>;<bg>`` – many terminals set this)
    3. Falls back to ``dark``.
    """
    explicit = os.environ.get("MUSIC_GENIE_THEME", "").lower()
    if explicit in ("dark", "light"):
        return explicit

    colorfgbg = os.environ.get("COLORFGBG", "")
    if ";" in colorfgbg:
        try:
            bg = int(colorfgbg.rsplit(";", 1)[-1])
            # ANSI colour indices 0-6 and 8 are considered dark
            return "light" if bg > 8 else "dark"
        except ValueError:
            pass

    return "dark"


def _build_theme(scheme: str) -> Theme:
    p = _FLEXOKI[scheme]
    return Theme(
        {
            # Semantic roles
            "primary": Style(color=p["cyan"], bold=True),
            "secondary": Style(color=p["blue"]),
            "success": Style(color=p["green"]),
            "warning": Style(color=p["yellow"]),
            "error": Style(color=p["red"]),
            "accent": Style(color=p["purple"]),
            "muted": Style(color=p["tx3"]),
            "text": Style(color=p["tx"]),
            # Table columns
            "col.index": Style(color=p["cyan"], bold=True),
            "col.title": Style(color=p["tx"]),
            "col.uploader": Style(color=p["green"]),
            "col.duration": Style(color=p["yellow"]),
            "col.views": Style(color=p["blue"]),
            "col.id": Style(color=p["tx3"]),
            "col.status": Style(color=p["yellow"]),
            "col.file": Style(color=p["blue"]),
            "col.time": Style(color=p["tx"]),
            # Progress / recording bar
            "bar": Style(color=p["yellow"]),
        }
    )


scheme = _detect_scheme()
console = Console(
    theme=_build_theme(scheme),
    style=Style(color=_FLEXOKI[scheme]["tx"], bgcolor=_FLEXOKI[scheme]["bg"]),
)
