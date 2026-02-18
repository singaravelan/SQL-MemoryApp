from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Optional

from data.models import SRSItem


UTC = timezone.utc


def to_iso(dt: Optional[datetime]) -> Optional[str]:
    if dt is None:
        return None
    return dt.astimezone(UTC).isoformat()


def from_iso(raw: Optional[str]) -> Optional[datetime]:
    if raw is None:
        return None
    return datetime.fromisoformat(raw).astimezone(UTC)


class ItemRepository:
    def __init__(self, db_path: str = "srs.db") -> None:
        self.db_path = db_path
        self.init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    question TEXT NOT NULL,
                    answer TEXT NOT NULL,
                    review_step INTEGER NOT NULL DEFAULT 0,
                    level TEXT NOT NULL,
                    next_review_at TEXT,
                    difficulty_level TEXT NOT NULL DEFAULT 'beginner',
                    question_type TEXT NOT NULL DEFAULT 'concept',
                    explanation TEXT NOT NULL DEFAULT '',
                    topic TEXT NOT NULL DEFAULT 'SELECT, WHERE',
                    unlocked_at TEXT
                )
                """
            )
            self._migrate_columns(conn)
            conn.commit()

    def _migrate_columns(self, conn: sqlite3.Connection) -> None:
        cols = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(items)").fetchall()
        }
        if "difficulty_level" not in cols:
            conn.execute(
                "ALTER TABLE items ADD COLUMN difficulty_level TEXT NOT NULL DEFAULT 'beginner'"
            )
        if "question_type" not in cols:
            conn.execute(
                "ALTER TABLE items ADD COLUMN question_type TEXT NOT NULL DEFAULT 'concept'"
            )
        if "explanation" not in cols:
            conn.execute(
                "ALTER TABLE items ADD COLUMN explanation TEXT NOT NULL DEFAULT ''"
            )
        if "topic" not in cols:
            conn.execute(
                "ALTER TABLE items ADD COLUMN topic TEXT NOT NULL DEFAULT 'SELECT, WHERE'"
            )
        if "unlocked_at" not in cols:
            conn.execute("ALTER TABLE items ADD COLUMN unlocked_at TEXT")

    def add_item(
        self,
        question: str,
        answer: str,
        level: str,
        next_review_at: Optional[datetime],
        review_step: int,
        difficulty_level: str,
        question_type: str,
        explanation: str,
        topic: str,
        unlocked_at: Optional[datetime] = None,
    ) -> SRSItem:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO items (
                    question, answer, review_step, level, next_review_at,
                    difficulty_level, question_type, explanation, topic, unlocked_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    question,
                    answer,
                    review_step,
                    level,
                    to_iso(next_review_at),
                    difficulty_level,
                    question_type,
                    explanation,
                    topic,
                    to_iso(unlocked_at),
                ),
            )
            item_id = cursor.lastrowid
            conn.commit()
        return self.get_item(item_id)

    def get_item(self, item_id: int) -> SRSItem:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT id, question, answer, level, next_review_at,
                       difficulty_level, question_type, explanation, topic, unlocked_at
                FROM items
                WHERE id = ?
                """,
                (item_id,),
            ).fetchone()
        if row is None:
            raise ValueError(f"item_id {item_id} not found")
        return self._row_to_item(row)

    def get_item_with_step(self, item_id: int) -> sqlite3.Row:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT *
                FROM items
                WHERE id = ?
                """,
                (item_id,),
            ).fetchone()
        if row is None:
            raise ValueError(f"item_id {item_id} not found")
        return row

    def get_due_items(
        self,
        now: datetime,
        difficulty_level: Optional[str] = None,
    ) -> list[SRSItem]:
        query = """
            SELECT id, question, answer, level, next_review_at,
                   difficulty_level, question_type, explanation, topic, unlocked_at
            FROM items
            WHERE level != 'Burned'
              AND unlocked_at IS NOT NULL
              AND next_review_at IS NOT NULL
              AND next_review_at <= ?
        """
        params: list[object] = [to_iso(now)]
        if difficulty_level:
            query += " AND difficulty_level = ?"
            params.append(difficulty_level)
        query += " ORDER BY next_review_at ASC, id ASC"

        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [self._row_to_item(row) for row in rows]

    def update_review_state(
        self,
        item_id: int,
        review_step: int,
        level: str,
        next_review_at: Optional[datetime],
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE items
                SET review_step = ?, level = ?, next_review_at = ?
                WHERE id = ?
                """,
                (review_step, level, to_iso(next_review_at), item_id),
            )
            conn.commit()

    def get_counts(self, now: datetime) -> dict[str, int]:
        with self._connect() as conn:
            total_due = conn.execute(
                """
                SELECT COUNT(*) FROM items
                WHERE level != 'Burned' AND unlocked_at IS NOT NULL AND next_review_at <= ?
                """,
                (to_iso(now),),
            ).fetchone()[0]
            beginner_due = conn.execute(
                """
                SELECT COUNT(*) FROM items
                WHERE level != 'Burned' AND unlocked_at IS NOT NULL AND next_review_at <= ?
                  AND difficulty_level = 'beginner'
                """,
                (to_iso(now),),
            ).fetchone()[0]
            intermediate_due = conn.execute(
                """
                SELECT COUNT(*) FROM items
                WHERE level != 'Burned' AND unlocked_at IS NOT NULL AND next_review_at <= ?
                  AND difficulty_level = 'intermediate'
                """,
                (to_iso(now),),
            ).fetchone()[0]
            advanced_due = conn.execute(
                """
                SELECT COUNT(*) FROM items
                WHERE level != 'Burned' AND unlocked_at IS NOT NULL AND next_review_at <= ?
                  AND difficulty_level = 'advanced'
                """,
                (to_iso(now),),
            ).fetchone()[0]
        return {
            "total_due": total_due,
            "beginner_due": beginner_due,
            "intermediate_due": intermediate_due,
            "advanced_due": advanced_due,
        }

    def get_topic_progress(self) -> list[sqlite3.Row]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    topic,
                    COUNT(*) AS total_items,
                    SUM(CASE WHEN unlocked_at IS NOT NULL THEN 1 ELSE 0 END) AS learned_items,
                    SUM(CASE WHEN level = 'Burned' THEN 1 ELSE 0 END) AS burned_items
                FROM items
                GROUP BY topic
                ORDER BY topic
                """
            ).fetchall()
        return rows

    def get_next_lesson(
        self,
        topic: Optional[str] = None,
        difficulty_level: Optional[str] = None,
    ) -> Optional[SRSItem]:
        query = """
            SELECT id, question, answer, level, next_review_at,
                   difficulty_level, question_type, explanation, topic, unlocked_at
            FROM items
            WHERE unlocked_at IS NULL
        """
        params: list[object] = []
        if topic:
            query += " AND topic = ?"
            params.append(topic)
        if difficulty_level:
            query += " AND difficulty_level = ?"
            params.append(difficulty_level)
        query += " ORDER BY id ASC LIMIT 1"

        with self._connect() as conn:
            row = conn.execute(query, tuple(params)).fetchone()
        if row is None:
            return None
        return self._row_to_item(row)

    def unlock_lesson(self, item_id: int, now: datetime) -> SRSItem:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE items
                SET unlocked_at = ?, review_step = 0, level = 'Apprentice', next_review_at = ?
                WHERE id = ?
                """,
                (to_iso(now), to_iso(now), item_id),
            )
            conn.commit()
        return self.get_item(item_id)

    def list_topics(self) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT DISTINCT topic FROM items ORDER BY topic"
            ).fetchall()
        return [r[0] for r in rows]

    def list_items(
        self,
        topic: Optional[str] = None,
        difficulty_level: Optional[str] = None,
        question_type: Optional[str] = None,
        limit: int = 500,
    ) -> list[SRSItem]:
        query = """
            SELECT id, question, answer, level, next_review_at,
                   difficulty_level, question_type, explanation, topic, unlocked_at
            FROM items
            WHERE 1=1
        """
        params: list[object] = []
        if topic:
            query += " AND topic = ?"
            params.append(topic)
        if difficulty_level:
            query += " AND difficulty_level = ?"
            params.append(difficulty_level)
        if question_type:
            query += " AND question_type = ?"
            params.append(question_type)
        query += " ORDER BY id ASC LIMIT ?"
        params.append(limit)

        with self._connect() as conn:
            rows = conn.execute(query, tuple(params)).fetchall()
        return [self._row_to_item(row) for row in rows]

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
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE items
                SET question = ?,
                    answer = ?,
                    explanation = ?,
                    topic = ?,
                    difficulty_level = ?,
                    question_type = ?
                WHERE id = ?
                """,
                (
                    question,
                    answer,
                    explanation,
                    topic,
                    difficulty_level,
                    question_type,
                    item_id,
                ),
            )
            conn.commit()
        return self.get_item(item_id)

    @staticmethod
    def _row_to_item(row: sqlite3.Row) -> SRSItem:
        return SRSItem(
            id=row["id"],
            question=row["question"],
            answer=row["answer"],
            level=row["level"],
            next_review_at=from_iso(row["next_review_at"]),
            difficulty_level=row["difficulty_level"],
            question_type=row["question_type"],
            explanation=row["explanation"],
            topic=row["topic"],
            unlocked_at=from_iso(row["unlocked_at"]),
        )
