"""Flexoki-based color theme with automatic dark/light detection."""

from __future__ import annotations

import os
import select
import sys
import termios
import tty

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


def _perceived_lightness(r: int, g: int, b: int) -> float:
    """Return perceptual lightness (0 = black, 1 = white) using sRGB luminance."""
    def linearize(c: int) -> float:
        s = c / 65535  # OSC 11 reports 16-bit components
        return s / 12.92 if s <= 0.04045 else ((s + 0.055) / 1.055) ** 2.4

    lum = 0.2126 * linearize(r) + 0.7152 * linearize(g) + 0.0722 * linearize(b)
    return lum


def _query_terminal_bg() -> str | None:
    """Ask the terminal for its background colour via OSC 11.

    Returns ``"dark"`` or ``"light"`` if the terminal responds, otherwise
    ``None``. Works on virtually all modern terminals (xterm, iTerm2, kitty,
    WezTerm, Alacritty, GNOME Terminal / VTE, Windows Terminal, etc.).
    """
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return None

    try:
        fd = sys.stdin.fileno()
        old_attrs = termios.tcgetattr(fd)
    except (termios.error, ValueError):
        return None

    try:
        tty.setraw(fd)
        # OSC 11 = query background colour; ST = ESC backslash
        sys.stdout.write("\033]11;?\033\\")
        sys.stdout.flush()

        # Wait up to 100 ms for the terminal to respond
        if not select.select([fd], [], [], 0.1)[0]:
            return None

        response = b""
        while select.select([fd], [], [], 0.05)[0]:
            response += os.read(fd, 128)

        # Response looks like: ESC ] 11 ; rgb:RRRR/GGGG/BBBB ST
        text = response.decode("latin-1")
        if "rgb:" not in text:
            return None

        rgb_part = text.split("rgb:", 1)[1]
        # Strip any trailing ST (BEL \x07, or ESC \ )
        for term in ("\x07", "\x1b\\", "\x1b"):
            rgb_part = rgb_part.split(term, 1)[0]

        parts = rgb_part.strip().split("/")
        if len(parts) != 3:
            return None

        r, g, b = (int(c, 16) for c in parts)
        return "light" if _perceived_lightness(r, g, b) > 0.5 else "dark"
    except (OSError, ValueError):
        return None
    finally:
        termios.tcsetattr(fd, termios.TCSAFLUSH, old_attrs)


def _detect_scheme() -> str:
    """Detect whether the terminal is dark or light.

    Checks (in order):
    1. ``MUSIC_GENIE_THEME`` env var (``dark`` / ``light``)
    2. ``COLORFGBG`` env var (``<fg>;<bg>`` – many terminals set this)
    3. OSC 11 query to the terminal for its actual background colour
    4. Falls back to ``dark``.
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

    osc_result = _query_terminal_bg()
    if osc_result:
        return osc_result

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
