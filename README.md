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

**Tag existing MP3 files:**
```
mg tag ~/Music
```
Scans a folder for MP3 files and enriches them with metadata (artist, album, year, cover art, lyrics) sourced from MusicBrainz and LRCLib. Pass `--skip-tagged` to skip files that already have complete tags, or `--force` to overwrite existing tags.

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

## 🤖 AI Disclaimer

This project uses AI-assisted development tools. See the [AI usage policy](https://j23n.com/public/posts/2026/my-ai-policy) for details.

**Tools**

- Claude Code (Anthropic) · `claude-sonnet-4-6` · Agentic

### Contribution Profile

```
Phase                               Human│ AI
─────────────────────────────────────────┼───────────────
Requirements & Scope       85%   ████████│░░          15%
Architecture & Design      50%      █████│░░░░░       50%
Implementation              5%           │░░░░░░░░░░  95%
Testing                   n/a
Documentation               5%           │░░░░░░░░░░  95%
```

**Oversight**: Autonomous

AI drives end-to-end; human reviews final output only.

### Process

AI agent operated autonomously across multi-step tasks. Human reviewed diffs, resolved conflicts, and approved merges.

### Accountability

The human author(s) are solely responsible for the content, accuracy, and fitness-for-purpose of this project.

---
*Last updated: 2026-02-20 · Generated with [ai-disclaimer](https://github.com/j23n/ai-disclaimer)*
