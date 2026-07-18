from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

from .models import ParsedExam


class ExamRepository:
    def __init__(self, db_path: str = "exams.db") -> None:
        self.db_path = db_path
        self.initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def initialize(self) -> None:
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS exams (
                    id INTEGER PRIMARY KEY, filename TEXT NOT NULL UNIQUE, title TEXT NOT NULL,
                    raw_text TEXT NOT NULL, parsed_json TEXT NOT NULL, created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS attempts (
                    id INTEGER PRIMARY KEY, exam_id INTEGER NOT NULL, filename TEXT NOT NULL,
                    exam_title TEXT NOT NULL, attempted_at TEXT NOT NULL, total_questions INTEGER NOT NULL,
                    correct_answers INTEGER NOT NULL, percentage REAL NOT NULL,
                    submitted_answers_json TEXT NOT NULL,
                    FOREIGN KEY(exam_id) REFERENCES exams(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY, value TEXT NOT NULL
                );
            """)

    def get_setting(self, key: str, default: str) -> str:
        with self.connect() as db:
            row = db.execute("SELECT value FROM app_settings WHERE key = ?", (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value: str) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO app_settings(key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )

    def get_exam_by_filename(self, filename: str):
        with self.connect() as db:
            return db.execute("SELECT * FROM exams WHERE filename = ?", (filename,)).fetchone()

    def list_exams(self):
        with self.connect() as db:
            return db.execute("SELECT id, filename, title, created_at FROM exams ORDER BY filename").fetchall()

    def save_exam(self, exam: ParsedExam, raw_text: str, replace: bool = False) -> None:
        existing = self.get_exam_by_filename(exam.source_filename)
        if existing and not replace:
            raise ValueError("An exam with this filename already exists. Select replace to overwrite it.")
        now = datetime.now(timezone.utc).isoformat()
        with self.connect() as db:
            if existing:
                db.execute("DELETE FROM exams WHERE filename = ?", (exam.source_filename,))
            db.execute("INSERT INTO exams(filename, title, raw_text, parsed_json, created_at) VALUES (?, ?, ?, ?, ?)",
                       (exam.source_filename, exam.exam_title, raw_text, exam.model_dump_json(), now))

    def load_exam(self, filename: str) -> tuple[int, ParsedExam]:
        row = self.get_exam_by_filename(filename)
        if not row:
            raise ValueError("Exam no longer exists.")
        return row["id"], ParsedExam.model_validate_json(row["parsed_json"])

    def save_attempt(self, exam_id: int, exam: ParsedExam, answers: dict[str, int]) -> tuple[int, int, float]:
        total = sum(len(section.questions) for section in exam.sections)
        correct = sum(answers.get(f"{section.section_number}:{q.question_number}") == q.correct_option_number
                      for section in exam.sections for q in section.questions)
        percentage = round(correct / total * 100, 2) if total else 0.0
        with self.connect() as db:
            db.execute("INSERT INTO attempts(exam_id, filename, exam_title, attempted_at, total_questions, correct_answers, percentage, submitted_answers_json) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (exam_id, exam.source_filename, exam.exam_title, datetime.now(timezone.utc).isoformat(), total, correct, percentage, json.dumps(answers, ensure_ascii=False)))
        return correct, total, percentage

    def list_attempts(self, filename: str | None = None, after: date | None = None):
        query, values = "SELECT * FROM attempts WHERE 1=1", []
        if filename:
            query += " AND filename = ?"; values.append(filename)
        if after:
            query += " AND attempted_at >= ?"; values.append(after.isoformat())
        query += " ORDER BY attempted_at DESC"
        with self.connect() as db:
            return db.execute(query, values).fetchall()
