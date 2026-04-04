from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated

import typer
from rich.status import Status
from rich.table import Table

from music_genie.config import get_settings
from music_genie.youtube.search import search_youtube
from music_genie.youtube.download import download_audio
from music_genie.audio.record import record_snippet
from music_genie.audio.identify import is_online, identify_song_sync
from music_genie.queue.store import save_snippet, list_pending, update_snippet, delete_snippet
from music_genie.ui.prompts import prompt_pick, prompt_confirm
from music_genie.ui.theme import console
from music_genie.metadata.lookup import TrackMeta, mb_lookup, parse_video_title
from music_genie.metadata.embed import embed

app = typer.Typer(help="music-genie: search, identify, and download music.")

_UNSAFE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def _safe(name: str) -> str:
    """Strip filesystem-unsafe characters from a path component."""
    return _UNSAFE.sub("", name).strip(". ")


# ---------------------------------------------------------------------------
# Shared helper: search → pick → download → tag
# ---------------------------------------------------------------------------

def _search_and_download(query: str, meta: TrackMeta | None = None) -> None:
    settings = get_settings()

    with Status(f"[primary]Searching YouTube for:[/primary] {query}", console=console, spinner="dots"):
        results = search_youtube(query)

    if not results:
        console.print("[error]No results found.[/error]")
        raise typer.Exit(1)

    pick = prompt_pick(results)
    if pick is None:
        console.print("[warning]Cancelled.[/warning]")
        raise typer.Exit(0)

    console.print(f"\n[text bold]Downloading:[/text bold] {pick.title}")
    raw_path = download_audio(
        url=pick.url,
        output_dir=settings.output_dir,
        fmt=settings.audio_format,
        quality=settings.audio_quality,
    )

    # ---- metadata ----
    if meta is None:
        artist, title = parse_video_title(pick.title, pick.uploader)
        with Status("[secondary]Looking up metadata...[/secondary]", console=console, spinner="dots"):
            meta = mb_lookup(artist, title)
        if meta is None:
            meta = TrackMeta(artist=artist, title=title)
    elif not (meta.album and meta.year):
        with Status("[secondary]Looking up metadata...[/secondary]", console=console, spinner="dots"):
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

    with Status("[secondary]Embedding tags...[/secondary]", console=console, spinner="dots"):
        embed(final_path, meta)

    console.print(f"\n[success bold]Saved:[/success bold] {final_path}")
    parts = [f"[success]{meta.artist}[/success] — {meta.title}"]
    if meta.album:
        parts.append(f"[muted]{meta.album}[/muted]")
    if meta.year:
        parts.append(f"[muted]{meta.year}[/muted]")
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
            "[success]Snippet saved.[/success] "
            "Run [text bold]music-genie process[/text bold] to identify it."
        )
        return

    if not is_online():
        console.print(
            "[warning]You appear to be offline.[/warning] "
            "Snippet queued. Run [text bold]music-genie process[/text bold] when connected."
        )
        return

    with Status("[primary]Identifying song...[/primary]", console=console, spinner="dots"):
        meta = identify_song_sync(wav_path)

    if not meta:
        console.print(
            "[warning]Could not identify the song.[/warning] "
            "Snippet saved — run [text bold]music-genie process[/text bold] to retry."
        )
        return

    update_snippet(record["id"], status="identified", identified_as=meta.query)
    console.print(f"[success bold]Identified:[/success bold] {meta.query}")
    _search_and_download(meta.query, meta=meta)


@app.command()
def pending() -> None:
    """List all queued snippets not yet identified."""
    records = list_pending()
    if not records:
        console.print("[success]No pending snippets.[/success]")
        return

    table = Table(title="Pending Snippets")
    table.add_column("#", style="col.index", width=4, justify="right")
    table.add_column("ID", style="col.id", max_width=25)
    table.add_column("Recorded At", style="col.time")
    table.add_column("WAV File", style="col.file", max_width=50)
    table.add_column("Status", style="col.status")

    for i, r in enumerate(records, start=1):
        wav_name = Path(r["wav_path"]).name if r.get("wav_path") else "?"
        table.add_row(str(i), r["id"], r.get("recorded_at", "?"), wav_name, r.get("status", "?"))

    console.print(table)


@app.command()
def process() -> None:
    """Identify pending snippets and prompt to search + download each."""
    records = list_pending()
    if not records:
        console.print("[success]No pending snippets to process.[/success]")
        return

    if not is_online():
        console.print("[error]You appear to be offline. Cannot identify snippets.[/error]")
        raise typer.Exit(1)

    identified_count = 0
    downloaded_count = 0
    skipped_count = 0

    for i, record in enumerate(records, start=1):
        console.rule(f"[text bold]Snippet {i}/{len(records)}[/text bold]")
        console.print(f"  Recorded: [secondary]{record.get('recorded_at', '?')}[/secondary]")
        console.print(f"  File:     [muted]{Path(record['wav_path']).name}[/muted]")

        wav_path = Path(record["wav_path"])
        if not wav_path.exists():
            console.print("[error]WAV file missing — skipping.[/error]")
            update_snippet(record["id"], status="skipped")
            skipped_count += 1
            continue

        with Status("[primary]Identifying...[/primary]", console=console, spinner="dots"):
            meta = identify_song_sync(wav_path)

        if not meta:
            console.print("[warning]Could not identify this snippet.[/warning]")
            if prompt_confirm("Delete this snippet?"):
                delete_snippet(record["id"])
                console.print("[muted]Deleted.[/muted]")
            skipped_count += 1
            continue

        identified_count += 1
        update_snippet(record["id"], status="identified", identified_as=meta.query)
        console.print(f"[success bold]Identified:[/success bold] {meta.query}")

        if prompt_confirm(f"Search YouTube for '{meta.query}'?"):
            _search_and_download(meta.query, meta=meta)
            update_snippet(record["id"], status="downloaded")
            downloaded_count += 1
        else:
            update_snippet(record["id"], status="skipped")
            skipped_count += 1

    console.rule("[text bold]Summary[/text bold]")
    console.print(
        f"  Identified: [success]{identified_count}[/success]  "
        f"Downloaded: [success]{downloaded_count}[/success]  "
        f"Skipped: [warning]{skipped_count}[/warning]"
    )


if __name__ == "__main__":
    app()
