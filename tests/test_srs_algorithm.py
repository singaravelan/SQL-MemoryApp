from __future__ import annotations

from datetime import timedelta

import pytest


@pytest.mark.p0
@pytest.mark.unit
def test_correct_answer_advances_step_and_interval(service, unlocked_item, fixed_now):
    updated = service.submit_answer(unlocked_item.id, unlocked_item.answer, now=fixed_now)
    assert updated.level == "Apprentice"
    assert updated.next_review_at == fixed_now + timedelta(hours=8)


@pytest.mark.p0
@pytest.mark.unit
def test_wrong_answer_resets_to_apprentice_4h(service, unlocked_item, fixed_now):
    updated = service.submit_answer(unlocked_item.id, "__wrong__", now=fixed_now)
    assert updated.level == "Apprentice"
    assert updated.next_review_at == fixed_now + timedelta(hours=4)


@pytest.mark.p0
@pytest.mark.unit
def test_burned_has_no_next_review(service, unlocked_item, fixed_now):
    now = fixed_now
    for _ in range(6):
        updated = service.submit_answer(unlocked_item.id, unlocked_item.answer, now=now)
        now = updated.next_review_at or now
    assert updated.level == "Burned"
    assert updated.next_review_at is None


@pytest.mark.p1
@pytest.mark.unit
def test_answer_evaluation_is_casefold_and_trim(service, unlocked_item, fixed_now):
    updated = service.submit_answer(
        unlocked_item.id,
        f"  {unlocked_item.answer.upper()}  ",
        now=fixed_now,
    )
    assert updated.next_review_at == fixed_now + timedelta(hours=8)
