from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.status import Status
from rich.table import Table

from music_genie.config import get_settings
from music_genie.youtube.search import search_youtube
from music_genie.youtube.download import download_audio
from music_genie.audio.record import record_snippet
from music_genie.audio.identify import is_online, identify_song_sync
from music_genie.queue.store import save_snippet, list_pending, update_snippet, delete_snippet
from music_genie.ui.prompts import prompt_pick, prompt_confirm
from music_genie.metadata.lookup import TrackMeta, mb_lookup, parse_video_title
from music_genie.metadata.embed import embed

app = typer.Typer(help="music-genie: search, identify, and download music.")
console = Console()

_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _safe(name: str) -> str:
    """Strip filesystem-unsafe characters from a path component."""
    return _UNSAFE.sub("", name).strip(". ")


# ---------------------------------------------------------------------------
# Shared helper: search → pick → download → tag
# ---------------------------------------------------------------------------

def _search_and_download(query: str, meta: TrackMeta | None = None) -> None:
    settings = get_settings()

    with Status(f"[bold cyan]Searching YouTube for:[/bold cyan] {query}", spinner="dots"):
        results = search_youtube(query)

    if not results:
        console.print("[red]No results found.[/red]")
        raise typer.Exit(1)

    pick = prompt_pick(results)
    if pick is None:
        console.print("[yellow]Cancelled.[/yellow]")
        raise typer.Exit(0)

    console.print(f"\n[bold]Downloading:[/bold] {pick.title}")
    raw_path = download_audio(
        url=pick.url,
        output_dir=settings.output_dir,
        fmt=settings.audio_format,
        quality=settings.audio_quality,
    )

    # ---- metadata ----
    if meta is None:
        artist, title = parse_video_title(pick.title, pick.uploader)
        with Status("[cyan]Looking up metadata...[/cyan]", spinner="dots"):
            meta = mb_lookup(artist, title)
        if meta is None:
            meta = TrackMeta(artist=artist, title=title)
    elif not (meta.album and meta.year):
        with Status("[cyan]Looking up metadata...[/cyan]", spinner="dots"):
            mb_meta = mb_lookup(meta.artist, meta.title)
        if mb_meta:
            meta.album = meta.album or mb_meta.album
            meta.year = meta.year or mb_meta.year
            meta.mb_release_id = mb_meta.mb_release_id

    # ---- rename to <output_dir>/<artist>/<title>.<fmt> ----
    artist_dir = settings.output_dir / _safe(meta.artist)
    artist_dir.mkdir(parents=True, exist_ok=True)
    final_path = artist_dir / f"{_safe(meta.title)}{raw_path.suffix}"
    raw_path.rename(final_path)

    with Status("[cyan]Embedding tags...[/cyan]", spinner="dots"):
        embed(final_path, meta)

    console.print(f"\n[bold green]Saved:[/bold green] {final_path}")
    parts = [f"[green]{meta.artist}[/green] — {meta.title}"]
    if meta.album:
        parts.append(f"[dim]{meta.album}[/dim]")
    if meta.year:
        parts.append(f"[dim]{meta.year}[/dim]")
    console.print("  Tagged: " + "  ·  ".join(parts))


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

@app.command()
def search(
    query: Annotated[str, typer.Argument(help="Free-text search query for YouTube")],
) -> None:
    """Search YouTube for music and download the selected track."""
    _search_and_download(query)


@app.command()
def listen(
    save: Annotated[bool, typer.Option("--save", help="Queue snippet without identifying now")] = False,
) -> None:
    """Record a mic snippet, identify the song, then search and download."""
    settings = get_settings()
    wav_path = record_snippet(duration=settings.record_duration)
    record = save_snippet(wav_path)

    if save:
        console.print(
            "[green]Snippet saved.[/green] "
            "Run [bold]music-genie process[/bold] to identify it."
        )
        return

    if not is_online():
        console.print(
            "[yellow]You appear to be offline.[/yellow] "
            "Snippet queued. Run [bold]music-genie process[/bold] when connected."
        )
        return

    with Status("[bold cyan]Identifying song...[/bold cyan]", spinner="dots"):
        meta = identify_song_sync(wav_path)

    if not meta:
        console.print(
            "[yellow]Could not identify the song.[/yellow] "
            "Snippet saved — run [bold]music-genie process[/bold] to retry."
        )
        return

    update_snippet(record["id"], status="identified", identified_as=meta.query)
    console.print(f"[bold green]Identified:[/bold green] {meta.query}")
    _search_and_download(meta.query, meta=meta)


@app.command()
def pending() -> None:
    """List all queued snippets not yet identified."""
    records = list_pending()
    if not records:
        console.print("[green]No pending snippets.[/green]")
        return

    table = Table(title="Pending Snippets")
    table.add_column("#", style="cyan", width=4, justify="right")
    table.add_column("ID", style="dim", max_width=25)
    table.add_column("Recorded At", style="white")
    table.add_column("WAV File", style="blue", max_width=50)
    table.add_column("Status", style="yellow")

    for i, r in enumerate(records, start=1):
        wav_name = Path(r["wav_path"]).name if r.get("wav_path") else "?"
        table.add_row(str(i), r["id"], r.get("recorded_at", "?"), wav_name, r.get("status", "?"))

    console.print(table)


@app.command()
def process() -> None:
    """Identify pending snippets and prompt to search + download each."""
    records = list_pending()
    if not records:
        console.print("[green]No pending snippets to process.[/green]")
        return

    if not is_online():
        console.print("[red]You appear to be offline. Cannot identify snippets.[/red]")
        raise typer.Exit(1)

    identified_count = 0
    downloaded_count = 0
    skipped_count = 0

    for i, record in enumerate(records, start=1):
        console.rule(f"[bold]Snippet {i}/{len(records)}[/bold]")
        console.print(f"  Recorded: [cyan]{record.get('recorded_at', '?')}[/cyan]")
        console.print(f"  File:     [dim]{Path(record['wav_path']).name}[/dim]")

        wav_path = Path(record["wav_path"])
        if not wav_path.exists():
            console.print("[red]WAV file missing — skipping.[/red]")
            update_snippet(record["id"], status="skipped")
            skipped_count += 1
            continue

        with Status("[bold cyan]Identifying...[/bold cyan]", spinner="dots"):
            meta = identify_song_sync(wav_path)

        if not meta:
            console.print("[yellow]Could not identify this snippet.[/yellow]")
            if prompt_confirm("Delete this snippet?"):
                delete_snippet(record["id"])
                console.print("[dim]Deleted.[/dim]")
            skipped_count += 1
            continue

        identified_count += 1
        update_snippet(record["id"], status="identified", identified_as=meta.query)
        console.print(f"[bold green]Identified:[/bold green] {meta.query}")

        if prompt_confirm(f"Search YouTube for '{meta.query}'?"):
            _search_and_download(meta.query, meta=meta)
            update_snippet(record["id"], status="downloaded")
            downloaded_count += 1
        else:
            update_snippet(record["id"], status="skipped")
            skipped_count += 1

    console.rule("[bold]Summary[/bold]")
    console.print(
        f"  Identified: [green]{identified_count}[/green]  "
        f"Downloaded: [green]{downloaded_count}[/green]  "
        f"Skipped: [yellow]{skipped_count}[/yellow]"
    )


if __name__ == "__main__":
    app()
