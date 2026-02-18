# Pytest Test Matrix (Priority-Based)

## P0 (Critical)

| ID | Area | Test | Type | File |
|---|---|---|---|---|
| P0-U1 | SRS | Correct answer advances step/level | unit | `tests/test_srs_algorithm.py` |
| P0-U2 | SRS | Wrong answer resets to Apprentice + 4h | unit | `tests/test_srs_algorithm.py` |
| P0-U3 | SRS | Burned has no next review (`None`) | unit | `tests/test_srs_algorithm.py` |
| P0-U4 | Persistence | DB init creates required schema | unit | `tests/test_persistence.py` |
| P0-U5 | Persistence | Add item persists all key fields | unit | `tests/test_persistence.py` |
| P0-I1 | Flow | Lesson unlock moves item to due queue | integration | `tests/test_integration_flow.py` |
| P0-I2 | Scheduling | Home due counts by difficulty are accurate | integration | `tests/test_integration_flow.py` |

## P1 (Important)

| ID | Area | Test | Type | File |
|---|---|---|---|---|
| P1-U1 | SRS | Interval mapping per step progression | unit | `tests/test_srs_algorithm.py` |
| P1-U2 | Eval | Case-insensitive + trim comparison | unit | `tests/test_srs_algorithm.py` |
| P1-U3 | Persistence | Update existing Q/A/explanation/topic | unit | `tests/test_persistence.py` |
| P1-U4 | Migration | Legacy DB column migration (topic/unlocked/type) | unit | `tests/test_persistence.py` |
| P1-I1 | Progress | Topic progress counters update after unlock | integration | `tests/test_integration_flow.py` |

## P2 (Nice-to-have)

| ID | Area | Test | Type | Status |
|---|---|---|---|---|
| P2-U1 | Input validation | Invalid difficulty/type rejected | unit | backlog |
| P2-U2 | Time parsing | Malformed timestamps handled safely | unit | backlog |
| P2-I1 | Concurrency | Rapid double-submit does not corrupt state | integration | backlog |
| P2-I2 | Scale | Large dataset query latency sanity check | integration | backlog |

## Fixture Design

| Fixture | Scope | Purpose |
|---|---|---|
| `db_path` | function | Isolated SQLite file under pytest temp dir |
| `service` | function | Fresh `SRSService` per test |
| `fixed_now` | function | Deterministic UTC timestamp for interval checks |
| `locked_item` | function | Seeded lesson item not yet unlocked |
| `unlocked_item` | function | Seeded lesson item already in review queue |

## Execution Plan

- Run critical path only: `pytest -m "p0"`
- Run all unit tests: `pytest -m "unit"`
- Run all integration tests: `pytest -m "integration"`
- Full suite: `pytest`
