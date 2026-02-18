from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from core.srs_logic import STEP_PLAN, next_state
from data.models import SRSItem
from data.repository import ItemRepository


UTC = timezone.utc
VALID_DIFFICULTY = {"beginner", "intermediate", "advanced"}
QUESTION_TYPE_MAP = {
    "concept": "concept",
    "syntax": "syntax_writing",
    "syntax_writing": "syntax_writing",
    "output": "output_prediction",
    "output_prediction": "output_prediction",
}


class SRSService:
    def __init__(self, db_path: str = "srs.db") -> None:
        self.repo = ItemRepository(db_path=db_path)

    def add_item(
        self,
        question: str,
        answer: str,
        difficulty_level: str = "beginner",
        question_type: str = "concept",
        explanation: str = "",
        topic: Optional[str] = None,
        unlock_now: bool = False,
        now: Optional[datetime] = None,
    ) -> SRSItem:
        question = question.strip()
        answer = answer.strip()
        explanation = explanation.strip()
        difficulty_level = difficulty_level.strip().lower()
        question_type = question_type.strip().lower()

        if not question:
            raise ValueError("question cannot be empty")
        if not answer:
            raise ValueError("answer cannot be empty")
        if difficulty_level not in VALID_DIFFICULTY:
            raise ValueError("difficulty_level must be beginner, intermediate, or advanced")
        question_type = QUESTION_TYPE_MAP.get(question_type, question_type)
        if question_type not in QUESTION_TYPE_MAP.values():
            raise ValueError(
                "question_type must be concept, syntax_writing, or output_prediction"
            )

        now = now or datetime.now(tz=UTC)
        level, _ = STEP_PLAN[0]
        topic = (topic or infer_topic(question)).strip()
        unlocked_at = now if unlock_now else None
        next_review_at = now if unlock_now else None
        return self.repo.add_item(
            question=question,
            answer=answer,
            level=level,
            next_review_at=next_review_at,
            review_step=0,
            difficulty_level=difficulty_level,
            question_type=question_type,
            explanation=explanation,
            topic=topic,
            unlocked_at=unlocked_at,
        )

    def get_due_items(
        self,
        now: Optional[datetime] = None,
        difficulty_level: Optional[str] = None,
    ) -> list[SRSItem]:
        now = now or datetime.now(tz=UTC)
        level_filter = difficulty_level.lower() if difficulty_level else None
        if level_filter and level_filter not in VALID_DIFFICULTY:
            raise ValueError("difficulty_level filter must be beginner, intermediate, or advanced")
        return self.repo.get_due_items(now=now, difficulty_level=level_filter)

    def submit_answer(
        self,
        item_id: int,
        user_answer: str,
        now: Optional[datetime] = None,
    ) -> SRSItem:
        now = now or datetime.now(tz=UTC)
        item_row = self.repo.get_item_with_step(item_id)
        expected = item_row["answer"]
        is_correct = user_answer.strip().casefold() == expected.strip().casefold()
        next_step, level, interval = next_state(
            review_step=item_row["review_step"],
            is_correct=is_correct,
        )
        next_review_at = None if interval is None else now + interval
        self.repo.update_review_state(
            item_id=item_id,
            review_step=next_step,
            level=level,
            next_review_at=next_review_at,
        )
        return self.repo.get_item(item_id)

    def get_item(self, item_id: int) -> SRSItem:
        return self.repo.get_item(item_id)

    def get_home_counts(self, now: Optional[datetime] = None) -> dict[str, int]:
        now = now or datetime.now(tz=UTC)
        return self.repo.get_counts(now=now)

    def get_topic_progress(self) -> list[dict[str, int | str]]:
        rows = self.repo.get_topic_progress()
        return [
            {
                "topic": row["topic"],
                "total_items": row["total_items"],
                "learned_items": row["learned_items"],
                "burned_items": row["burned_items"],
            }
            for row in rows
        ]

    def get_next_lesson(
        self,
        topic: Optional[str] = None,
        difficulty_level: Optional[str] = None,
    ) -> Optional[SRSItem]:
        if difficulty_level and difficulty_level not in VALID_DIFFICULTY:
            raise ValueError("difficulty_level filter must be beginner, intermediate, or advanced")
        return self.repo.get_next_lesson(topic=topic, difficulty_level=difficulty_level)

    def unlock_lesson(self, item_id: int, now: Optional[datetime] = None) -> SRSItem:
        now = now or datetime.now(tz=UTC)
        return self.repo.unlock_lesson(item_id=item_id, now=now)

    def list_topics(self) -> list[str]:
        return self.repo.list_topics()

    def list_items(
        self,
        topic: Optional[str] = None,
        difficulty_level: Optional[str] = None,
        question_type: Optional[str] = None,
        limit: int = 500,
    ) -> list[SRSItem]:
        difficulty = difficulty_level.lower() if difficulty_level else None
        if difficulty and difficulty not in VALID_DIFFICULTY:
            raise ValueError("difficulty_level filter must be beginner, intermediate, or advanced")
        qtype = QUESTION_TYPE_MAP.get(question_type.lower(), question_type.lower()) if question_type else None
        if qtype and qtype not in QUESTION_TYPE_MAP.values():
            raise ValueError("question_type filter must be concept, syntax_writing, or output_prediction")
        return self.repo.list_items(
            topic=topic,
            difficulty_level=difficulty,
            question_type=qtype,
            limit=limit,
        )

    def update_item_content(
        self,
        item_id: int,
        question: str,
        answer: str,
        explanation: str,
        topic: str,
        difficulty_level: str,
        question_type: str,
    ) -> SRSItem:
        question = question.strip()
        answer = answer.strip()
        explanation = explanation.strip()
        topic = topic.strip()
        difficulty = difficulty_level.strip().lower()
        qtype = QUESTION_TYPE_MAP.get(question_type.strip().lower(), question_type.strip().lower())

        if not question:
            raise ValueError("question cannot be empty")
        if not answer:
            raise ValueError("answer cannot be empty")
        if not topic:
            raise ValueError("topic cannot be empty")
        if difficulty not in VALID_DIFFICULTY:
            raise ValueError("difficulty_level must be beginner, intermediate, or advanced")
        if qtype not in QUESTION_TYPE_MAP.values():
            raise ValueError("question_type must be concept, syntax_writing, or output_prediction")

        return self.repo.update_item_content(
            item_id=item_id,
            question=question,
            answer=answer,
            explanation=explanation,
            topic=topic,
            difficulty_level=difficulty,
            question_type=qtype,
        )


def infer_topic(question: str) -> str:
    q = question.casefold()
    if "window" in q or "row_number" in q or "rank(" in q or "dense_rank" in q or "lag(" in q:
        return "Window functions"
    if "subquery" in q or "exists" in q or " in (" in q:
        return "Subqueries"
    if "join" in q:
        return "JOINs"
    if "group by" in q or "having" in q:
        return "GROUP BY, HAVING"
    return "SELECT, WHERE"
