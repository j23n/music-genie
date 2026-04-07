from __future__ import annotations

import re
from pathlib import Path

import httpx
from mutagen.id3 import (
    APIC, ID3, SYLT, TALB, TDRC, TIT2, TPE1, USLT,
    ID3NoHeaderError,
)

from music_genie.metadata.lookup import TrackMeta

_LRC_LINE = re.compile(r"\[(\d+):(\d+)\.(\d+)\](.*)")


def _fetch_cover(meta: TrackMeta) -> bytes | None:
    # Try Cover Art Archive first (high-res, correct album art)
    if meta.mb_release_id:
        try:
            r = httpx.get(
                f"https://coverartarchive.org/release/{meta.mb_release_id}/front",
                follow_redirects=True,
                timeout=5,
            )
            if r.status_code == 200:
                return r.content
        except Exception:
            pass

    # Fall back to Shazam / other cover URL
    if meta.cover_url:
        try:
            r = httpx.get(meta.cover_url, follow_redirects=True, timeout=5)
            if r.status_code == 200:
                return r.content
        except Exception:
            pass

    return None


def _lrc_to_sylt(lrc: str) -> list[tuple[str, int]]:
    result = []
    for line in lrc.splitlines():
        m = _LRC_LINE.match(line)
        if m:
            mins, secs, centis, text = m.groups()
            ms = int(mins) * 60_000 + int(secs) * 1_000 + int(centis) * 10
            result.append((text.strip(), ms))
    return result


def _lrc_to_plain(lrc: str) -> str:
    lines = []
    for line in lrc.splitlines():
        stripped = _LRC_LINE.sub(r"\4", line).strip()
        if stripped:
            lines.append(stripped)
    return "\n".join(lines)


def embed(path: Path, meta: TrackMeta, force: bool = False) -> None:
    try:
        tags = ID3(str(path))
    except ID3NoHeaderError:
        tags = ID3()

    if force or "TIT2" not in tags:
        tags["TIT2"] = TIT2(encoding=3, text=meta.title)
    if force or "TPE1" not in tags:
        tags["TPE1"] = TPE1(encoding=3, text=meta.artist)
    if meta.album and (force or "TALB" not in tags):
        tags["TALB"] = TALB(encoding=3, text=meta.album)
    if meta.year and (force or "TDRC" not in tags):
        tags["TDRC"] = TDRC(encoding=3, text=meta.year)

    if force or "APIC:" not in tags:
        cover_data = _fetch_cover(meta)
        if cover_data:
            tags["APIC:"] = APIC(
                encoding=3,
                mime="image/jpeg",
                type=3,  # front cover
                desc="Cover",
                data=cover_data,
            )

    if meta.lyrics:
        is_lrc = bool(_LRC_LINE.search(meta.lyrics))
        if force or "USLT::eng" not in tags:
            plain = _lrc_to_plain(meta.lyrics) if is_lrc else meta.lyrics
            tags["USLT::eng"] = USLT(encoding=3, lang="eng", desc="", text=plain)
        if is_lrc and (force or "SYLT::eng" not in tags):
            sylt_entries = _lrc_to_sylt(meta.lyrics)
            if sylt_entries:
                tags["SYLT::eng"] = SYLT(
                    encoding=3, lang="eng", format=2, type=1,
                    text=sylt_entries,
                )

    tags.save(str(path))
