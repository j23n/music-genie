from __future__ import annotations

import re

import httpx

_LRC_LINE = re.compile(r"\[(\d{2}):(\d{2})\.(\d{2,3})\]\s*(.*)")


def _parse_lrc(lrc: str) -> list[tuple[str, int]]:
    """Parse LRC-format lyrics into (text, timestamp_ms) pairs."""
    result: list[tuple[str, int]] = []
    for line in lrc.splitlines():
        m = _LRC_LINE.match(line)
        if not m:
            continue
        minutes, seconds, frac, text = m.groups()
        # Normalise fractional part to milliseconds (2-digit = centiseconds)
        ms_frac = int(frac) * (10 if len(frac) == 2 else 1)
        ts_ms = int(minutes) * 60_000 + int(seconds) * 1_000 + ms_frac
        result.append((text, ts_ms))
    return result


def fetch_synced_lyrics(
    artist: str, title: str, album: str | None = None
) -> tuple[list[tuple[str, int]] | None, str | None]:
    """Fetch synced + plain lyrics from LRCLIB.

    Returns ``(synced, plain)`` where *synced* is a list of
    ``(text, timestamp_ms)`` tuples suitable for a SYLT frame, and *plain* is
    the raw lyrics text for a USLT frame.  Either or both may be ``None``.
    """
    params: dict[str, str] = {"artist_name": artist, "track_name": title}
    if album:
        params["album_name"] = album

    try:
        r = httpx.get(
            "https://lrclib.net/api/get",
            params=params,
            timeout=5,
        )
        if r.status_code != 200:
            return None, None
        data = r.json()
    except Exception:
        return None, None

    synced: list[tuple[str, int]] | None = None
    raw_synced = data.get("syncedLyrics")
    if raw_synced:
        parsed = _parse_lrc(raw_synced)
        if parsed:
            synced = parsed

    plain: str | None = data.get("plainLyrics") or None

    return synced, plain
