from __future__ import annotations

from datetime import datetime
from typing import Optional

from core.srs_service import SRSService
from data.models import SRSItem


class SRSEngine:
    """
    Backward-compatible facade around the service/repository architecture.
    """

    def __init__(self, db_path: str = "srs.db") -> None:
        self.service = SRSService(db_path=db_path)

    def add_item(
        self,
        question: str,
        answer: str,
        now: Optional[datetime] = None,
        difficulty_level: str = "beginner",
        question_type: str = "concept",
        explanation: str = "",
        topic: Optional[str] = None,
        unlock_now: bool = False,
    ) -> SRSItem:
        return self.service.add_item(
            question=question,
            answer=answer,
            now=now,
            difficulty_level=difficulty_level,
            question_type=question_type,
            explanation=explanation,
            topic=topic,
            unlock_now=unlock_now,
        )

    def get_due_items(
        self,
        now: Optional[datetime] = None,
        difficulty_level: Optional[str] = None,
    ) -> list[SRSItem]:
        return self.service.get_due_items(now=now, difficulty_level=difficulty_level)

    def submit_answer(
        self,
        item_id: int,
        user_answer: str,
        now: Optional[datetime] = None,
    ) -> SRSItem:
        return self.service.submit_answer(item_id=item_id, user_answer=user_answer, now=now)

    def get_item(self, item_id: int) -> SRSItem:
        return self.service.get_item(item_id)

    def get_home_counts(self, now: Optional[datetime] = None) -> dict[str, int]:
        return self.service.get_home_counts(now=now)

    def get_topic_progress(self) -> list[dict[str, int | str]]:
        return self.service.get_topic_progress()

    def get_next_lesson(
        self,
        topic: Optional[str] = None,
        difficulty_level: Optional[str] = None,
    ) -> Optional[SRSItem]:
        return self.service.get_next_lesson(topic=topic, difficulty_level=difficulty_level)

    def unlock_lesson(self, item_id: int, now: Optional[datetime] = None) -> SRSItem:
        return self.service.unlock_lesson(item_id=item_id, now=now)

    def list_topics(self) -> list[str]:
        return self.service.list_topics()

    def list_items(
        self,
        topic: Optional[str] = None,
        difficulty_level: Optional[str] = None,
        question_type: Optional[str] = None,
        limit: int = 500,
    ) -> list[SRSItem]:
        return self.service.list_items(
            topic=topic,
            difficulty_level=difficulty_level,
            question_type=question_type,
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
        return self.service.update_item_content(
            item_id=item_id,
            question=question,
            answer=answer,
            explanation=explanation,
            topic=topic,
            difficulty_level=difficulty_level,
            question_type=question_type,
        )


__all__ = ["SRSItem", "SRSEngine"]
