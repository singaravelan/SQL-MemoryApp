from __future__ import annotations

import pytest

from core import semantic_evaluation as sem
from core.semantic_evaluation import evaluate_answer


@pytest.mark.unit
def test_evaluate_answer_empty_user_answer():
    result = evaluate_answer("   ", "SELECT returns columns")
    assert result["result"] == "fail"
    assert result["similarity"] == 0.0
    assert result["classification"] == "incorrect"


@pytest.mark.unit
def test_evaluate_answer_empty_reference_answer():
    result = evaluate_answer("returns rows", " ")
    assert result["result"] == "fail"
    assert result["similarity"] == 0.0
    assert result["classification"] == "incorrect"


@pytest.mark.unit
def test_threshold_at_075_is_pass(monkeypatch):
    monkeypatch.setattr(sem, "_cosine_similarity", lambda _a, _b: 0.75)
    result = evaluate_answer("a", "b")
    assert result["result"] == "pass"
    assert result["classification"] == "correct"


@pytest.mark.unit
def test_threshold_at_060_is_partial_fail(monkeypatch):
    monkeypatch.setattr(sem, "_cosine_similarity", lambda _a, _b: 0.60)
    result = evaluate_answer("a", "b")
    assert result["result"] == "fail"
    assert result["classification"] == "partially_correct"


@pytest.mark.unit
def test_below_060_is_incorrect_fail(monkeypatch):
    monkeypatch.setattr(sem, "_cosine_similarity", lambda _a, _b: 0.59)
    result = evaluate_answer("a", "b")
    assert result["result"] == "fail"
    assert result["classification"] == "incorrect"


@pytest.mark.unit
def test_semantic_similarity_handles_whitespace_and_synonyms():
    user = "  Fetch   rows   where salary > 50000 "
    reference = "SELECT rows filter salary > 50000"
    result = evaluate_answer(user, reference)
    assert result["similarity"] >= 0.75
    assert result["result"] == "pass"
