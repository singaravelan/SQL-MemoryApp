from __future__ import annotations

from datetime import timedelta


STEP_PLAN = [
    ("Apprentice", timedelta(hours=4)),
    ("Apprentice", timedelta(hours=8)),
    ("Apprentice", timedelta(days=1)),
    ("Guru", timedelta(days=3)),
    ("Guru", timedelta(days=7)),
    ("Master", timedelta(days=30)),
    ("Burned", None),
]


def next_state(review_step: int, is_correct: bool) -> tuple[int, str, timedelta | None]:
    if is_correct:
        next_step = min(review_step + 1, len(STEP_PLAN) - 1)
    else:
        next_step = 0
    level, interval = STEP_PLAN[next_step]
    return next_step, level, interval
