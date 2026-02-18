from __future__ import annotations

import pytest


@pytest.mark.p0
@pytest.mark.integration
def test_unlock_lesson_moves_item_to_due_queue(service, locked_item, fixed_now):
    assert service.get_home_counts(now=fixed_now)["total_due"] == 0
    service.unlock_lesson(locked_item.id, now=fixed_now)
    due = service.get_due_items(now=fixed_now)
    assert len(due) == 1
    assert due[0].id == locked_item.id


@pytest.mark.p0
@pytest.mark.integration
def test_home_due_counts_split_by_difficulty(service, fixed_now):
    b = service.add_item(
        question="B1",
        answer="A1",
        difficulty_level="beginner",
        question_type="concept",
        topic="SELECT, WHERE",
        unlock_now=False,
        now=fixed_now,
    )
    i = service.add_item(
        question="I1",
        answer="A2",
        difficulty_level="intermediate",
        question_type="concept",
        topic="GROUP BY, HAVING",
        unlock_now=False,
        now=fixed_now,
    )
    a = service.add_item(
        question="A1",
        answer="A3",
        difficulty_level="advanced",
        question_type="concept",
        topic="Window functions",
        unlock_now=False,
        now=fixed_now,
    )
    service.unlock_lesson(b.id, now=fixed_now)
    service.unlock_lesson(i.id, now=fixed_now)
    service.unlock_lesson(a.id, now=fixed_now)

    counts = service.get_home_counts(now=fixed_now)
    assert counts["total_due"] == 3
    assert counts["beginner_due"] == 1
    assert counts["intermediate_due"] == 1
    assert counts["advanced_due"] == 1


@pytest.mark.p1
@pytest.mark.integration
def test_topic_progress_updates_after_unlock(service, fixed_now):
    item = service.add_item(
        question="What is INNER JOIN?",
        answer="Rows that match in both tables.",
        difficulty_level="beginner",
        question_type="concept",
        topic="JOINs",
        unlock_now=False,
        now=fixed_now,
    )
    before = {row["topic"]: row for row in service.get_topic_progress()}
    assert before["JOINs"]["learned_items"] == 0

    service.unlock_lesson(item.id, now=fixed_now)
    after = {row["topic"]: row for row in service.get_topic_progress()}
    assert after["JOINs"]["learned_items"] == 1
