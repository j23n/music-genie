from __future__ import annotations

from rich.console import Console
from rich.table import Table

from music_genie.youtube.search import VideoResult

console = Console()


def _fmt_duration(seconds: int | None) -> str:
    if seconds is None:
        return "?"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


def _fmt_views(count: int | None) -> str:
    if count is None:
        return "?"
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)


def show_results(results: list[VideoResult]) -> None:
    table = Table(title="Search Results", show_lines=False)
    table.add_column("#", style="bold cyan", width=3, justify="right")
    table.add_column("Title", style="white", max_width=60)
    table.add_column("Uploader", style="green", max_width=25)
    table.add_column("Duration", style="yellow", width=9, justify="right")
    table.add_column("Views", style="blue", width=8, justify="right")

    for i, r in enumerate(results, start=1):
        table.add_row(
            str(i),
            r.title,
            r.uploader,
            _fmt_duration(r.duration_s),
            _fmt_views(r.view_count),
        )

    console.print(table)
