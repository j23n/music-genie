from __future__ import annotations

import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path

import shutil

from rich.console import Console
from rich.live import Live
from rich.text import Text

from music_genie.config import snippets_dir

console = Console()


def _input_candidates() -> list[list[str]]:
    """Return FFmpeg input arg lists to try, in preference order."""
    if sys.platform == "darwin":
        return [["-f", "avfoundation", "-i", ":0"]]
    elif sys.platform == "win32":
        return [["-f", "dshow", "-i", "audio=default"]]
    else:
        # pulse works on PulseAudio and PipeWire; alsa as fallback
        return [
            ["-f", "pulse", "-i", "default"],
            ["-f", "alsa", "-i", "default"],
        ]


def _make_snippet_path() -> Path:
    sdir = snippets_dir()
    sdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    uid = uuid.uuid4().hex[:8]
    return sdir / f"{stamp}_{uid}.wav"


def _system_ffmpeg() -> str:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError(
            "Recording requires a system ffmpeg (the bundled static binary cannot "
            "access audio devices).\n"
            "  Debian/Ubuntu:  sudo apt install ffmpeg\n"
            "  macOS:          brew install ffmpeg\n"
            "  Fedora:         sudo dnf install ffmpeg"
        )
    return ffmpeg


def record_snippet(duration: int = 8, sample_rate: int = 44100) -> Path:
    out_path = _make_snippet_path()
    ffmpeg = _system_ffmpeg()

    console.print(f"[bold cyan]Recording for {duration} seconds...[/bold cyan]")

    last_stderr = b""
    for input_args in _input_candidates():
        cmd = [
            ffmpeg,
            *input_args,
            "-t", str(duration),
            "-ar", str(sample_rate),
            "-ac", "1",
            "-y",
            str(out_path),
        ]

        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

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
        last_stderr = proc.stderr.read()

        if proc.returncode == 0:
            console.print(f"[green]Snippet saved:[/green] {out_path}")
            return out_path

    raise RuntimeError(
        f"FFmpeg recording failed (exit {proc.returncode}). "
        "Check that a microphone is connected and accessible.\n"
        + last_stderr.decode(errors="replace")
    )
