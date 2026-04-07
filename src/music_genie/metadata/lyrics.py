from __future__ import annotations

import syncedlyrics


def fetch_lyrics(artist: str, title: str) -> str | None:
    """Fetch synced (LRC) lyrics, falling back to plain text."""
    query = f"{artist} {title}"
    try:
        lrc = syncedlyrics.search(query)
        if lrc:
            return lrc
    except Exception:
        pass
    try:
        plain = syncedlyrics.search(query, plain_only=True)
        return plain
    except Exception:
        return None
