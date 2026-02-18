from __future__ import annotations

import sqlite3
from collections import Counter

import pytest


def _normalize_result(rows: list[sqlite3.Row]) -> Counter[tuple[str, ...]]:
    """
    Normalize rows to support:
    - order-insensitive row comparison
    - alias-insensitive comparison (ignore column names)
    - column-order-insensitive comparison
    """
    normalized = []
    for row in rows:
        # Compare row values only; sort values within each row to ignore column order.
        values = tuple(sorted(repr(v) for v in tuple(row)))
        normalized.append(values)
    return Counter(normalized)


def validate_sql(conn: sqlite3.Connection, user_sql: str, expected_sql: str) -> tuple[bool, str]:
    try:
        user_rows = conn.execute(user_sql).fetchall()
    except sqlite3.DatabaseError as exc:
        return False, f"user_sql_error: {exc}"

    expected_rows = conn.execute(expected_sql).fetchall()

    if len(user_rows) != len(expected_rows):
        return (
            False,
            f"row_count_mismatch: expected={len(expected_rows)} actual={len(user_rows)}",
        )

    if _normalize_result(user_rows) != _normalize_result(expected_rows):
        return False, "result_set_mismatch"

    return True, "ok"


@pytest.fixture
def sample_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE departments (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );

        CREATE TABLE employees (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            department_id INTEGER NOT NULL,
            salary INTEGER NOT NULL,
            FOREIGN KEY (department_id) REFERENCES departments(id)
        );

        INSERT INTO departments (id, name) VALUES
            (1, 'Engineering'),
            (2, 'Sales'),
            (3, 'HR');

        INSERT INTO employees (id, name, department_id, salary) VALUES
            (1, 'Alice', 1, 120000),
            (2, 'Bob', 1, 95000),
            (3, 'Cara', 2, 80000),
            (4, 'Dan', 2, 60000),
            (5, 'Eli', 3, 70000);
        """
    )
    yield conn
    conn.close()


def test_validation_handles_extra_whitespace(sample_db: sqlite3.Connection) -> None:
    user_sql = """
        SELECT    name
        FROM      employees
        WHERE     salary >= 80000
    """
    expected_sql = "SELECT name FROM employees WHERE salary >= 80000;"
    ok, reason = validate_sql(sample_db, user_sql, expected_sql)
    assert ok is True
    assert reason == "ok"


def test_validation_handles_alias_differences(sample_db: sqlite3.Connection) -> None:
    user_sql = """
        SELECT e.name AS employee_label
        FROM employees e
        WHERE e.department_id = 1
    """
    expected_sql = """
        SELECT employees.name AS employee_name
        FROM employees
        WHERE department_id = 1
    """
    ok, reason = validate_sql(sample_db, user_sql, expected_sql)
    assert ok is True
    assert reason == "ok"


def test_validation_handles_column_order_differences(sample_db: sqlite3.Connection) -> None:
    user_sql = """
        SELECT name, id
        FROM employees
        WHERE department_id = 2
    """
    expected_sql = """
        SELECT id, name
        FROM employees
        WHERE department_id = 2
    """
    ok, reason = validate_sql(sample_db, user_sql, expected_sql)
    assert ok is True
    assert reason == "ok"


def test_validation_is_row_order_insensitive(sample_db: sqlite3.Connection) -> None:
    user_sql = """
        SELECT id, name
        FROM employees
        WHERE salary >= 70000
        ORDER BY id DESC
    """
    expected_sql = """
        SELECT id, name
        FROM employees
        WHERE salary >= 70000
        ORDER BY id ASC
    """
    ok, reason = validate_sql(sample_db, user_sql, expected_sql)
    assert ok is True
    assert reason == "ok"


def test_validation_detects_incorrect_row_count(sample_db: sqlite3.Connection) -> None:
    user_sql = "SELECT name FROM employees WHERE salary >= 90000;"
    expected_sql = "SELECT name FROM employees WHERE salary >= 70000;"
    ok, reason = validate_sql(sample_db, user_sql, expected_sql)
    assert ok is False
    assert reason.startswith("row_count_mismatch")
