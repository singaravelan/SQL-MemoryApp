from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class SRSItem:
    id: int
    question: str
    answer: str
    level: str
    next_review_at: Optional[datetime]
    difficulty_level: str
    question_type: str
    explanation: str
    topic: str
    unlocked_at: Optional[datetime]
