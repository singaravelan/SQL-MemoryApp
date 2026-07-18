# Repository Guidelines

## Project Structure & Module Organization

This is a Python Streamlit application for SQL spaced-repetition study. Keep entry-point code in `streamlit_app.py`; it delegates to `ui/app.py`. Put scheduling and application rules in `core/` (`srs_logic.py`, `srs_service.py`, and semantic evaluation), SQLite models and persistence in `data/`, and reusable UI code in `ui/`. The seeded database is `srs.db`; `seed_items.py` and `sql_srs_items.json` support seed data. Tests live in `tests/`, with priorities documented in `tests/TEST_MATRIX.md`.

## Build, Test, and Development Commands

- `python -m pip install streamlit pytest` installs the runtime and test dependencies when no `requirements.txt` is present.
- `streamlit run streamlit_app.py` starts the local app (normally at `http://localhost:8501`).
- `pytest` runs the full suite.
- `pytest -m "p0"` runs critical-path tests; use `pytest -m "unit"` or `pytest -m "integration"` for focused checks.

The development container uses Python 3.11 and starts the same Streamlit command automatically.

## Coding Style & Naming Conventions

Use four-space indentation, standard Python naming (`snake_case` for functions and variables, `PascalCase` for classes), and type annotations for public APIs. Keep UI, persistence, and scheduling responsibilities separate. Favor small, focused functions and composition over inheritance; inject database paths, clocks, and external dependencies so core logic remains testable. Preserve UTC-aware timestamps and existing domain terminology such as `unlock_lesson` and `difficulty_level`.

No formatter or linter is configured currently. Follow nearby code and avoid drive-by formatting changes.

## Testing Guidelines

Tests use `pytest` and names follow `test_<behavior>.py` / `test_<behavior>`. Add coverage for any changed scheduling, persistence, or UI-page behavior. Use fixtures from `tests/conftest.py`, especially the temporary `db_path` and deterministic `fixed_now`; do not rely on the tracked `srs.db` in tests. Mark tests with the existing `p0`, `p1`, `p2`, `unit`, or `integration` markers as appropriate.

## Commit & Pull Request Guidelines

Existing history uses short, imperative summaries, for example `Add .gitignore and remove local artifacts from git`. Keep commits similarly focused. Pull requests should explain the behavioral change, list test commands run, link the relevant issue when available, and include screenshots for Streamlit UI changes. Do not commit virtual environments, caches, or generated local artifacts.
