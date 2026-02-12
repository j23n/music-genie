from __future__ import annotations

from pathlib import Path

import httpx
from mutagen.id3 import APIC, ID3, TALB, TDRC, TIT2, TPE1, ID3NoHeaderError

from music_genie.metadata.lookup import TrackMeta


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


def embed(path: Path, meta: TrackMeta) -> None:
    try:
        tags = ID3(str(path))
    except ID3NoHeaderError:
        tags = ID3()

    tags["TIT2"] = TIT2(encoding=3, text=meta.title)
    tags["TPE1"] = TPE1(encoding=3, text=meta.artist)
    if meta.album:
        tags["TALB"] = TALB(encoding=3, text=meta.album)
    if meta.year:
        tags["TDRC"] = TDRC(encoding=3, text=meta.year)

    cover_data = _fetch_cover(meta)
    if cover_data:
        tags["APIC"] = APIC(
            encoding=3,
            mime="image/jpeg",
            type=3,  # front cover
            desc="Cover",
            data=cover_data,
        )

    tags.save(str(path))
