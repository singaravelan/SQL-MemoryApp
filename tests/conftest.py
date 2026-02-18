from __future__ import annotations

from datetime import datetime, timezone

import pytest

from core.srs_service import SRSService


@pytest.fixture
def db_path(tmp_path):
    return str(tmp_path / "test_srs.db")


@pytest.fixture
def service(db_path):
    return SRSService(db_path=db_path)


@pytest.fixture
def fixed_now():
    return datetime(2026, 2, 18, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def locked_item(service, fixed_now):
    return service.add_item(
        question="What does SELECT do?",
        answer="Returns columns",
        difficulty_level="beginner",
        question_type="concept",
        explanation="Projection of result columns.",
        topic="SELECT, WHERE",
        unlock_now=False,
        now=fixed_now,
    )


@pytest.fixture
def unlocked_item(service, fixed_now):
    item = service.add_item(
        question="Write a WHERE clause for salary > 1000.",
        answer="SELECT * FROM employees WHERE salary > 1000;",
        difficulty_level="beginner",
        question_type="syntax_writing",
        explanation="Filter rows before grouping.",
        topic="SELECT, WHERE",
        unlock_now=False,
        now=fixed_now,
    )
    return service.unlock_lesson(item.id, now=fixed_now)
