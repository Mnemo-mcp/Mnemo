"""Tests for mnemo/slots.py — structured memory slots."""
import pytest
from unittest.mock import patch
from mnemo.memory.slots import get_slot, set_slot, get_pinned_slots, DEFAULT_SLOTS


@pytest.fixture
def repo(tmp_path):
    (tmp_path / ".mnemo").mkdir()
    with patch("mnemo.memory.slots.mnemo_path", return_value=tmp_path / ".mnemo"):
        yield tmp_path


def test_get_slot_returns_empty_for_new(repo):
    with patch("mnemo.memory.slots.mnemo_path", return_value=repo / ".mnemo"):
        assert get_slot(repo, "project_context") == ""


def test_set_slot_stores_content(repo):
    with patch("mnemo.memory.slots.mnemo_path", return_value=repo / ".mnemo"):
        set_slot(repo, "project_context", "My project info")
        assert get_slot(repo, "project_context") == "My project info"


def test_size_limit_enforcement(repo):
    with patch("mnemo.memory.slots.mnemo_path", return_value=repo / ".mnemo"):
        long_content = "x" * 5000
        set_slot(repo, "project_context", long_content)
        result = get_slot(repo, "project_context")
        assert len(result) == 2000  # default limit


def test_get_pinned_slots_returns_only_pinned_with_content(repo):
    with patch("mnemo.memory.slots.mnemo_path", return_value=repo / ".mnemo"):
        set_slot(repo, "project_context", "context info")
        set_slot(repo, "pending_items", "some items")
        result = get_pinned_slots(repo)
        assert "project_context" in result
        # pending_items is not pinned
        assert "pending_items" not in result


def test_default_slots_exist():
    assert "project_context" in DEFAULT_SLOTS
    assert "user_preferences" in DEFAULT_SLOTS
    assert "conventions" in DEFAULT_SLOTS
    assert "pending_items" in DEFAULT_SLOTS
    assert "known_gotchas" in DEFAULT_SLOTS
