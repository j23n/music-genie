from __future__ import annotations

import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import imageio_ffmpeg
from rich.console import Console
from rich.live import Live
from rich.text import Text

from music_genie.config import snippets_dir

console = Console()


def _input_args() -> list[str]:
    """Return FFmpeg input arguments for the default microphone on each platform."""
    if sys.platform == "darwin":
        return ["-f", "avfoundation", "-i", ":0"]
    elif sys.platform == "win32":
        return ["-f", "dshow", "-i", "audio=default"]
    else:
        return ["-f", "alsa", "-i", "default"]


def _make_snippet_path() -> Path:
    sdir = snippets_dir()
    sdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    uid = uuid.uuid4().hex[:8]
    return sdir / f"{stamp}_{uid}.wav"


def record_snippet(duration: int = 8, sample_rate: int = 44100) -> Path:
    out_path = _make_snippet_path()
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()

    cmd = [
        ffmpeg,
        *_input_args(),
        "-t", str(duration),
        "-ar", str(sample_rate),
        "-ac", "1",
        "-y",
        str(out_path),
    ]

    console.print(f"[bold cyan]Recording for {duration} seconds...[/bold cyan]")

    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    with Live(console=console, refresh_per_second=4) as live:
        start = time.time()
        while True:
            elapsed = time.time() - start
            remaining = max(0.0, duration - elapsed)
            filled = int((elapsed / duration) * 20)
            bar = "[" + "#" * filled + "." * (20 - filled) + "]"
            live.update(Text(f"  {bar}  {remaining:.1f}s remaining", style="yellow"))
            if proc.poll() is not None or remaining <= 0:
                break
            time.sleep(0.1)

    proc.wait()

    if proc.returncode != 0:
        raise RuntimeError(
            f"FFmpeg recording failed (exit {proc.returncode}). "
            "Check that a microphone is connected and accessible."
        )

    console.print(f"[green]Snippet saved:[/green] {out_path}")
    return out_path
