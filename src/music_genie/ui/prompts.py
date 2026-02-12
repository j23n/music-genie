from __future__ import annotations

import questionary

from music_genie.youtube.search import VideoResult
from music_genie.ui.display import _fmt_duration


def _choice_label(i: int, r: VideoResult) -> str:
    dur = _fmt_duration(r.duration_s)
    return f"{i:2d}. {r.title[:55]:<55}  [{r.uploader[:20]}]  {dur}"


def prompt_pick(results: list[VideoResult]) -> VideoResult | None:
    choices = [
        questionary.Choice(title=_choice_label(i, r), value=r)
        for i, r in enumerate(results, start=1)
    ]
    choices.append(questionary.Choice(title="  Cancel", value=None))
    return questionary.select("Pick a track to download:", choices=choices).ask()


def prompt_confirm(msg: str) -> bool:
    result = questionary.confirm(msg).ask()
    return bool(result)
