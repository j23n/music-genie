from __future__ import annotations

import asyncio
import warnings
from pathlib import Path

import httpx
with warnings.catch_warnings():
    warnings.simplefilter("ignore", RuntimeWarning)
    from shazamio import Shazam

from music_genie.metadata.lookup import TrackMeta


def is_online() -> bool:
    try:
        httpx.head("https://1.1.1.1", timeout=2.0)
        return True
    except Exception:
        return False


async def _identify_async(wav_path: Path) -> TrackMeta | None:
    shazam = Shazam()
    result = await shazam.recognize(str(wav_path))

    track = result.get("track")
    if not track:
        return None

    title = track.get("title", "")
    artist = track.get("subtitle", "")
    if not title:
        return None

    # Extract album, year, cover from Shazam response
    album: str | None = None
    year: str | None = None
    for section in track.get("sections", []):
        for item in section.get("metadata", []):
            key = item.get("title", "").lower()
            if key == "album":
                album = item.get("text")
            elif key == "released":
                year = item.get("text", "")[:4]

    cover_url: str | None = track.get("images", {}).get("coverart")

    return TrackMeta(
        artist=artist,
        title=title,
        album=album,
        year=year,
        cover_url=cover_url,
    )


def identify_song_sync(wav_path: Path) -> TrackMeta | None:
    return asyncio.run(_identify_async(wav_path))
