from __future__ import annotations

import asyncio
from dataclasses import dataclass

from yt_dlp import YoutubeDL


@dataclass
class VideoResult:
    title: str
    uploader: str
    duration_s: int | None
    url: str
    view_count: int | None


def _sync_search(query: str, max_results: int) -> list[VideoResult]:
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "skip_download": True,
    }
    with YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(f"ytsearch{max_results}:{query}", download=False)

    results: list[VideoResult] = []
    for entry in info.get("entries", []):
        if not entry:
            continue
        results.append(
            VideoResult(
                title=entry.get("title") or "Unknown",
                uploader=entry.get("uploader") or entry.get("channel") or "Unknown",
                duration_s=entry.get("duration"),
                url=entry.get("url") or entry.get("webpage_url") or "",
                view_count=entry.get("view_count"),
            )
        )
    return results


async def search_youtube_async(query: str, max_results: int = 10) -> list[VideoResult]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_search, query, max_results)


def search_youtube(query: str, max_results: int = 10) -> list[VideoResult]:
    return _sync_search(query, max_results)
