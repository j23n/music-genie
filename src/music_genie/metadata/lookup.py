from __future__ import annotations

import re
from dataclasses import dataclass, field

import musicbrainzngs

musicbrainzngs.set_useragent("music-genie", "0.1.0", "https://github.com/music-genie/music-genie")


@dataclass
class TrackMeta:
    artist: str
    title: str
    album: str | None = None
    year: str | None = None
    mb_release_id: str | None = None
    cover_url: str | None = None  # fallback URL (e.g. from Shazam)

    @property
    def query(self) -> str:
        return f"{self.artist} - {self.title}"


def mb_lookup(artist: str, title: str) -> TrackMeta | None:
    try:
        result = musicbrainzngs.search_recordings(
            artist=artist, recording=title, limit=5
        )
    except musicbrainzngs.WebServiceError:
        return None

    recordings = result.get("recording-list", [])
    if not recordings:
        return None

    best = recordings[0]

    # Canonical artist name from credit
    canon_artist = artist
    credits = best.get("artist-credit", [])
    if credits and isinstance(credits[0], dict):
        canon_artist = credits[0].get("artist", {}).get("name", artist)

    # Album + year from first release
    album: str | None = None
    year: str | None = None
    mb_release_id: str | None = None
    releases = best.get("release-list", [])
    if releases:
        rel = releases[0]
        album = rel.get("title")
        date = rel.get("date", "")
        year = date[:4] if date else None
        mb_release_id = rel.get("id")

    return TrackMeta(
        artist=canon_artist,
        title=best.get("title", title),
        album=album,
        year=year,
        mb_release_id=mb_release_id,
    )


def parse_video_title(title: str, uploader: str) -> tuple[str, str]:
    """Best-effort parse of a YouTube video title into (artist, track_title)."""
    # Strip common suffixes: (Official Video), [Official Audio], (Lyrics), etc.
    cleaned = re.sub(r"[\(\[].*?[\)\]]", "", title).strip()
    if " - " in cleaned:
        artist, track = cleaned.split(" - ", 1)
        return artist.strip(), track.strip()
    # Fall back to uploader as artist
    return uploader.strip(), cleaned.strip()
