from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from srs_engine import SRSEngine


@pytest.fixture
def fixed_now() -> datetime:
    return datetime(2026, 2, 18, 10, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def engine(tmp_path) -> SRSEngine:
    db_path = tmp_path / "integration_srs.db"
    return SRSEngine(db_path=str(db_path))


def test_add_sql_item_persists_to_sqlite(engine: SRSEngine, fixed_now: datetime) -> None:
    created = engine.add_item(
        question="Write SQL to fetch all users.",
        answer="SELECT * FROM users;",
        difficulty_level="beginner",
        question_type="syntax_writing",
        explanation="Projection of all columns.",
        topic="SELECT, WHERE",
        unlock_now=False,
        now=fixed_now,
    )

    loaded = engine.get_item(created.id)
    assert loaded.id == created.id
    assert loaded.question == "Write SQL to fetch all users."
    assert loaded.answer == "SELECT * FROM users;"
    assert loaded.difficulty_level == "beginner"
    assert loaded.question_type == "syntax_writing"
    assert loaded.topic == "SELECT, WHERE"
    assert loaded.unlocked_at is None


def test_fetch_due_items_returns_only_due_unlocked_items(
    engine: SRSEngine, fixed_now: datetime
) -> None:
    due_item = engine.add_item(
        question="What does WHERE do?",
        answer="Filters rows.",
        difficulty_level="beginner",
        question_type="concept",
        topic="SELECT, WHERE",
        unlock_now=False,
        now=fixed_now,
    )
    not_due_item = engine.add_item(
        question="What does HAVING do?",
        answer="Filters grouped rows.",
        difficulty_level="intermediate",
        question_type="concept",
        topic="GROUP BY, HAVING",
        unlock_now=False,
        now=fixed_now,
    )

    engine.unlock_lesson(due_item.id, now=fixed_now)
    engine.unlock_lesson(not_due_item.id, now=fixed_now + timedelta(hours=1))

    due = engine.get_due_items(now=fixed_now)
    due_ids = {item.id for item in due}

    assert due_item.id in due_ids
    assert not_due_item.id not in due_ids


def test_submit_answer_updates_database_state_correctly(
    engine: SRSEngine, fixed_now: datetime
) -> None:
    item = engine.add_item(
        question="Write SQL for all orders.",
        answer="SELECT * FROM orders;",
        difficulty_level="beginner",
        question_type="syntax_writing",
        topic="SELECT, WHERE",
        unlock_now=False,
        now=fixed_now,
    )
    engine.unlock_lesson(item.id, now=fixed_now)

    correct_update = engine.submit_answer(
        item_id=item.id,
        user_answer="SELECT * FROM orders;",
        now=fixed_now,
    )
    assert correct_update.level == "Apprentice"
    assert correct_update.next_review_at == fixed_now + timedelta(hours=8)

    wrong_update = engine.submit_answer(
        item_id=item.id,
        user_answer="wrong answer",
        now=fixed_now + timedelta(hours=8),
    )
    assert wrong_update.level == "Apprentice"
    assert wrong_update.next_review_at == fixed_now + timedelta(hours=12)
