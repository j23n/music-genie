from __future__ import annotations

import questionary

from music_genie.youtube.search import VideoResult
from music_genie.ui.display import show_results


def prompt_pick(results: list[VideoResult]) -> VideoResult | None:
    show_results(results)

    n = len(results)

    def _validate(val: str) -> bool | str:
        if (val.strip().isdigit() and 0 <= int(val.strip()) <= n) or val == "":
            return True
        return f"Enter a number between 1 and {n}, or 0 to cancel"

    answer = questionary.text(
        f"Pick [1-{n}] or 0 to cancel [1]:",
        validate=_validate,
    ).ask()
    
    if answer is None or answer == "":
        return results[0]
    if answer.strip() == "0":
        return None
    return results[int(answer.strip()) - 1]


def prompt_confirm(msg: str) -> bool:
    result = questionary.confirm(msg).ask()
    return bool(result)
