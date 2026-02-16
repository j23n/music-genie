# music-genie

Search YouTube for music, identify songs from mic recordings, and download them as tagged MP3s.

Invoked as `mg` or `music-genie`.

## Installation

Requires Python 3.11+ and [uv](https://docs.astral.sh/uv/).

```
uv tool install music-genie        # from PyPI
uv tool install .                  # local dev
```

Recording also requires a system `ffmpeg` (the bundled download binary cannot access audio devices):

```
sudo apt install ffmpeg   # Debian/Ubuntu
brew install ffmpeg       # macOS
sudo dnf install ffmpeg   # Fedora
```

## Usage

**Search and download by query:**
```
mg search "tame impala let it happen"
```
Presents up to 10 YouTube results, prompts for a selection, downloads as MP3, and embeds metadata (artist, album, year, cover art) sourced from MusicBrainz.

**Identify a song from the microphone:**
```
mg listen
```
Records an 8-second snippet, identifies it via Shazam, then flows into search and download. Pass `--save` to queue the snippet for later identification instead.

**List unidentified snippets:**
```
mg pending
```

**Process queued snippets:**
```
mg process
```
Attempts to identify each pending snippet and prompts to search and download. Unidentifiable snippets can be deleted.

## Output layout

Files are saved to `~/Music/<artist>/<title>.mp3` by default.

## Configuration

Settings can be overridden via environment variables or a TOML file at `~/.config/music-genie/config.toml`.

| Key | Default | Description |
|---|---|---|
| `output_dir` | `~/Music` | Download destination |
| `audio_format` | `mp3` | Output format (mp3, m4a, opus, …) |
| `audio_quality` | `192` | Bitrate in kbps |
| `record_duration` | `8` | Snippet length in seconds |

Environment variables use the prefix `MUSIC_GENIE_`, e.g. `MUSIC_GENIE_OUTPUT_DIR=/tmp/music`.

Example config file:

```toml
output_dir = "/home/user/Music"
audio_format = "mp3"
audio_quality = 320
record_duration = 10
```

## Data storage

Snippets and their metadata are stored in `~/.local/share/music-genie/snippets/` as `.wav` + `.json` pairs.

## AI disclaimer

This tool was built with Claude Code, following [my AI policy](https://j23n.com/public/posts/2026/my-ai-policy).

### Tools
- Claude Code (Anthropic) — primary development assistant

### Usage
- **Architecture & design**: Human-driven
- **Implementation**: AI-collaborative (human-directed, AI-written, human-reviewed)
- **Tests**: N/A
- **Documentation**: AI-generated with human review

### Process
AI agents propose changes as a PR, which are reviewed and merged by me. I try to make interactions transparent in the relevant issues or proposed patches. AI-authored commits are tagged with `Co-Authored-By` in the git history.
