from __future__ import annotations

import syncedlyrics


_PROVIDERS = ["lrclib"]


def fetch_lyrics(artist: str, title: str) -> str | None:
    """Fetch synced (LRC) lyrics via LRCLib, falling back to plain text."""
    query = f"{artist} {title}"
    try:
        result = syncedlyrics.search(query, providers=_PROVIDERS)
        if result:
            return result
    except Exception:
        pass
    try:
        plain = syncedlyrics.search(query, providers=_PROVIDERS, plain_only=True)
        return plain
    except Exception:
        return None
