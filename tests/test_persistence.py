from __future__ import annotations

import sqlite3

import pytest

from data.repository import ItemRepository


@pytest.mark.p0
@pytest.mark.unit
def test_db_init_creates_schema(db_path):
    repo = ItemRepository(db_path=db_path)
    with sqlite3.connect(db_path) as conn:
        cols = {
            row[1]
            for row in conn.execute("PRAGMA table_info(items)").fetchall()
        }
    assert {"id", "question", "answer", "topic", "unlocked_at", "difficulty_level", "question_type"} <= cols
    assert repo is not None


@pytest.mark.p0
@pytest.mark.unit
def test_add_item_persists_fields(service, fixed_now):
    item = service.add_item(
        question="What is HAVING used for?",
        answer="Filtering grouped results.",
        difficulty_level="intermediate",
        question_type="concept",
        explanation="HAVING filters after aggregation.",
        topic="GROUP BY, HAVING",
        unlock_now=False,
        now=fixed_now,
    )
    loaded = service.get_item(item.id)
    assert loaded.question == "What is HAVING used for?"
    assert loaded.difficulty_level == "intermediate"
    assert loaded.question_type == "concept"
    assert loaded.topic == "GROUP BY, HAVING"
    assert loaded.unlocked_at is None


@pytest.mark.p1
@pytest.mark.unit
def test_update_item_content_persists(service, unlocked_item):
    updated = service.update_item_content(
        item_id=unlocked_item.id,
        question="Updated question?",
        answer="Updated answer",
        explanation="Updated explanation",
        topic="Subqueries",
        difficulty_level="advanced",
        question_type="output_prediction",
    )
    assert updated.question == "Updated question?"
    assert updated.answer == "Updated answer"
    assert updated.explanation == "Updated explanation"
    assert updated.topic == "Subqueries"
    assert updated.difficulty_level == "advanced"
    assert updated.question_type == "output_prediction"


@pytest.mark.p1
@pytest.mark.unit
def test_legacy_migration_adds_new_columns(tmp_path):
    db_path = str(tmp_path / "legacy.db")
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                review_step INTEGER NOT NULL DEFAULT 0,
                level TEXT NOT NULL,
                next_review_at TEXT
            )
            """
        )
        conn.commit()
    ItemRepository(db_path=db_path)
    with sqlite3.connect(db_path) as conn:
        cols = {
            row[1]
            for row in conn.execute("PRAGMA table_info(items)").fetchall()
        }
    assert {"difficulty_level", "question_type", "explanation", "topic", "unlocked_at"} <= cols
