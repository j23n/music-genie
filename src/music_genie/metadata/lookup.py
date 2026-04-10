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
    lyrics: str | None = None  # LRC text (synced) or plain text

    @property
    def query(self) -> str:
        return f"{self.artist} - {self.title}"


def _pick_best_release(releases: list[dict]) -> dict:
    """Choose the most relevant release, preferring original albums over compilations."""

    def _score(rel: dict) -> tuple[int, str]:
        rg = rel.get("release-group", {})
        primary = rg.get("type", "").lower()
        secondary = [t.lower() for t in rg.get("secondary-type-list", [])]

        # Compilations / soundtracks / DJ-mixes etc. are almost never what we want.
        is_compilation = "compilation" in secondary or primary == "compilation"

        if primary == "album" and not is_compilation:
            rank = 0  # best
        elif primary in ("single", "ep") and not is_compilation:
            rank = 1
        elif primary == "album" and is_compilation:
            rank = 2
        else:
            rank = 3  # broadcast, other, or missing type

        # Within the same rank, prefer the earliest release date so we get
        # the original pressing rather than a re-issue.
        date = rel.get("date", "") or ""
        return (rank, date)

    return min(releases, key=_score)


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

    # Album + year – prefer the artist's own album over compilations
    album: str | None = None
    year: str | None = None
    mb_release_id: str | None = None
    releases = best.get("release-list", [])
    if releases:
        rel = _pick_best_release(releases)
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
