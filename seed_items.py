from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from srs_engine import SRSEngine


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


def seed(db_path: str = "srs.db", json_path: str = "sql_srs_items.json") -> None:
    engine = SRSEngine(db_path)
    source = Path(json_path)
    if not source.exists():
        raise FileNotFoundError(f"Missing dataset: {json_path}")

    with source.open("r", encoding="utf-8") as f:
        items = json.load(f)

    # Avoid duplicate loads by checking existing exact question+answer pairs.
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, question, answer FROM items")
    existing_rows = cur.fetchall()
    existing = {(row[1], row[2]): row[0] for row in existing_rows}
    conn.close()

    inserted = 0
    skipped = 0
    updated = 0
    conn = sqlite3.connect(db_path)
    for item in items:
        q = item["question"].strip()
        a = item["correct_answer"].strip()
        difficulty_level = item.get("level", "beginner").strip().lower()
        question_type = item.get("question_type", "concept").strip().lower()
        explanation = item.get("explanation", "").strip()
        topic = infer_topic(q)
        existing_id = existing.get((q, a))
        if existing_id is not None:
            conn.execute(
                """
                UPDATE items
                SET difficulty_level = ?, question_type = ?, explanation = ?, topic = ?
                WHERE id = ?
                """,
                (difficulty_level, question_type, explanation, topic, existing_id),
            )
            updated += 1
            skipped += 1
            continue
        engine.add_item(
            question=q,
            answer=a,
            difficulty_level=difficulty_level,
            question_type=question_type,
            explanation=explanation,
            topic=topic,
            unlock_now=False,
        )
        existing[(q, a)] = -1
        inserted += 1
    conn.commit()
    conn.close()

    print(
        "Inserted: "
        f"{inserted}, Updated: {updated}, Skipped: {skipped}, Total dataset rows: {len(items)}"
    )


if __name__ == "__main__":
    seed()
