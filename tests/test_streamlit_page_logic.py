from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

import ui.app as app


@dataclass
class FakeItem:
    id: int


class FakeSidebar:
    def __init__(self, value: str) -> None:
        self.value = value

    def radio(self, *_args, **_kwargs) -> str:
        return self.value


class FakeStreamlit:
    def __init__(self, page: str = "Home") -> None:
        self.session_state = FakeSessionState()
        self.sidebar = FakeSidebar(page)
        self.page_config_called = False

    def set_page_config(self, **_kwargs) -> None:
        self.page_config_called = True


class FakeEngine:
    def __init__(self, _db_path: str) -> None:
        self.last_due_filter = None
        self.get_due_calls = 0
        self.items = [FakeItem(id=101), FakeItem(id=102)]

    def get_due_items(self, now: datetime, difficulty_level=None):
        assert now.tzinfo == timezone.utc
        self.last_due_filter = difficulty_level
        self.get_due_calls += 1
        return self.items

    def get_item(self, item_id: int):
        for item in self.items:
            if item.id == item_id:
                return item
        raise ValueError("not found")


class FakeSessionState(dict):
    def __getattr__(self, name):
        try:
            return self[name]
        except KeyError as exc:
            raise AttributeError(name) from exc

    def __setattr__(self, name, value):
        self[name] = value


@pytest.mark.unit
def test_init_state_resets_stale_session_state(monkeypatch):
    fake_st = FakeStreamlit()
    fake_st.session_state.update(
        {
            "state_version": app.STATE_VERSION - 1,
            "engine": "old-engine",
            "review_item_id": 999,
            "lesson_item_id": 555,
        }
    )

    monkeypatch.setattr(app, "st", fake_st)
    monkeypatch.setattr(app, "SRSEngine", FakeEngine)

    app.init_state()

    assert fake_st.session_state["state_version"] == app.STATE_VERSION
    assert isinstance(fake_st.session_state["engine"], FakeEngine)
    assert fake_st.session_state["review_item_id"] is None
    assert fake_st.session_state["lesson_item_id"] is None
    assert fake_st.session_state["review_filter"] == "all"
    assert fake_st.session_state["modify_qtype_filter"] == "all"


@pytest.mark.unit
def test_get_or_pick_review_item_progresses_queue_state(monkeypatch):
    fake_st = FakeStreamlit()
    fake_st.session_state.update(
        {
            "state_version": app.STATE_VERSION,
            "engine": FakeEngine("ignored.db"),
            "review_item_id": None,
            "review_filter": "beginner",
        }
    )
    monkeypatch.setattr(app, "st", fake_st)

    first = app.get_or_pick_review_item()
    assert first.id == 101
    assert fake_st.session_state["review_item_id"] == 101
    assert fake_st.session_state["engine"].last_due_filter == "beginner"

    second = app.get_or_pick_review_item()
    assert second.id == 101
    # Should use cached review_item_id path, not query due queue again.
    assert fake_st.session_state["engine"].get_due_calls == 1


@pytest.mark.unit
@pytest.mark.parametrize(
    ("page", "expected"),
    [
        ("Home", "home"),
        ("Review", "review"),
        ("Lessons", "lessons"),
        ("Modify Lessons", "modify"),
    ],
)
def test_run_streamlit_app_navigation_state(monkeypatch, page: str, expected: str):
    fake_st = FakeStreamlit(page=page)
    called = {"home": 0, "review": 0, "lessons": 0, "modify": 0}

    monkeypatch.setattr(app, "st", fake_st)
    monkeypatch.setattr(app, "init_state", lambda: None)
    monkeypatch.setattr(app, "render_home_page", lambda: called.__setitem__("home", called["home"] + 1))
    monkeypatch.setattr(
        app, "render_review_page", lambda: called.__setitem__("review", called["review"] + 1)
    )
    monkeypatch.setattr(
        app, "render_lessons_page", lambda: called.__setitem__("lessons", called["lessons"] + 1)
    )
    monkeypatch.setattr(
        app, "render_modify_lessons_page", lambda: called.__setitem__("modify", called["modify"] + 1)
    )

    app.run_streamlit_app()

    assert fake_st.page_config_called is True
    assert called[expected] == 1
    for key, value in called.items():
        if key != expected:
            assert value == 0
