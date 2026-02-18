from __future__ import annotations

import hashlib
import math
import re
from collections import Counter


_TOKEN_RE = re.compile(r"[a-z0-9_]+")
_VECTOR_DIM = 256
_EPSILON = 1e-12

_SYNONYM_MAP = {
    "retrieve": "select",
    "retrieves": "select",
    "retrieved": "select",
    "fetch": "select",
    "fetches": "select",
    "return": "select",
    "returns": "select",
    "returned": "select",
    "records": "rows",
    "record": "row",
    "filtering": "filter",
    "filtered": "filter",
    "where": "filter",
    "grouping": "group",
}


def _normalize_token(token: str) -> str:
    return _SYNONYM_MAP.get(token, token)


def _tokenize(text: str) -> list[str]:
    raw_tokens = _TOKEN_RE.findall(text.lower())
    return [_normalize_token(t) for t in raw_tokens]


def _hash_to_index_and_sign(token: str) -> tuple[int, float]:
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    idx = int.from_bytes(digest[:8], "big") % _VECTOR_DIM
    sign = 1.0 if digest[8] % 2 == 0 else -1.0
    return idx, sign


def _embed_text(text: str) -> list[float]:
    tokens = _tokenize(text)
    if not tokens:
        return [0.0] * _VECTOR_DIM

    counts: Counter[str] = Counter(tokens)
    for i in range(len(tokens) - 1):
        # Add lightweight phrase signal to capture token context.
        counts[f"{tokens[i]}__{tokens[i + 1]}"] += 1

    vector = [0.0] * _VECTOR_DIM
    for token, tf in counts.items():
        idx, sign = _hash_to_index_and_sign(token)
        weight = 1.0 + math.log(tf)
        vector[idx] += sign * weight
    return vector


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a < _EPSILON or norm_b < _EPSILON:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


def _classify_similarity(similarity: float) -> tuple[str, str]:
    if similarity >= 0.75:
        return "correct", "Answer meaning matches the reference."
    if similarity >= 0.60:
        return "partially_correct", "Answer is close but misses important details."
    return "incorrect", "Answer meaning does not match the reference."


def evaluate_answer(user_answer: str, reference_answer: str) -> dict[str, object]:
    """
    Semantic answer evaluation using hashed embeddings + cosine similarity.

    Returns:
      - result: "pass" or "fail"
      - similarity: float
      - feedback: short human-readable feedback
      - classification: "correct" | "partially_correct" | "incorrect"
    """
    if not reference_answer or not reference_answer.strip():
        return {
            "result": "fail",
            "similarity": 0.0,
            "feedback": "Reference answer is empty; cannot evaluate.",
            "classification": "incorrect",
        }

    if not user_answer or not user_answer.strip():
        return {
            "result": "fail",
            "similarity": 0.0,
            "feedback": "No answer submitted.",
            "classification": "incorrect",
        }

    user_vec = _embed_text(user_answer)
    ref_vec = _embed_text(reference_answer)
    similarity = _cosine_similarity(user_vec, ref_vec)
    classification, feedback = _classify_similarity(similarity)
    result = "pass" if similarity >= 0.75 else "fail"

    return {
        "result": result,
        "similarity": round(similarity, 4),
        "feedback": feedback,
        "classification": classification,
    }


__all__ = ["evaluate_answer"]
