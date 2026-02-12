from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from music_genie.config import snippets_dir


def _json_path(wav_path: Path) -> Path:
    return wav_path.with_suffix(".json")


def save_snippet(wav_path: Path) -> dict:
    stem = wav_path.stem
    record: dict = {
        "id": stem,
        "recorded_at": datetime.now().isoformat(timespec="seconds"),
        "wav_path": str(wav_path),
        "status": "recorded",
        "identified_as": None,
        "youtube_url": None,
    }
    json_path = _json_path(wav_path)
    json_path.write_text(json.dumps(record, indent=2))
    return record


def list_pending() -> list[dict]:
    sdir = snippets_dir()
    records: list[dict] = []
    for jf in sorted(sdir.glob("*.json")):
        try:
            data = json.loads(jf.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if data.get("status") == "recorded":
            records.append(data)
    return records


def list_all() -> list[dict]:
    sdir = snippets_dir()
    records: list[dict] = []
    for jf in sorted(sdir.glob("*.json")):
        try:
            data = json.loads(jf.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        records.append(data)
    return records


def delete_snippet(snippet_id: str) -> bool:
    """Delete the WAV and JSON files for a snippet. Returns True if found."""
    sdir = snippets_dir()
    for jf in sdir.glob("*.json"):
        try:
            data = json.loads(jf.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if data.get("id") == snippet_id:
            Path(data["wav_path"]).unlink(missing_ok=True)
            jf.unlink(missing_ok=True)
            return True
    return False


def update_snippet(snippet_id: str, **fields: object) -> dict | None:
    sdir = snippets_dir()
    for jf in sdir.glob("*.json"):
        try:
            data = json.loads(jf.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        if data.get("id") == snippet_id:
            data.update(fields)
            jf.write_text(json.dumps(data, indent=2))
            return data
    return None
