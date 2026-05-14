"""Tests for plan features: draft plans, frontier scoring, templates."""

import json
import time
from pathlib import Path

import pytest

from mnemo.plan import (
    _get_next_task,
    _load_plans,
    _save_plans,
    create_plan,
    from_template,
    get_status,
    save_template,
    handle_plan,
)


def make_repo(tmp_path):
    mnemo_dir = tmp_path / ".mnemo"
    mnemo_dir.mkdir()
    (mnemo_dir / "memory.json").write_text("[]")
    (mnemo_dir / "decisions.json").write_text("[]")
    (mnemo_dir / "plans.json").write_text("[]")
    (mnemo_dir / "context.json").write_text("{}")
    return tmp_path


class TestDraftPlans:
    def test_create_draft_sets_flags(self, tmp_path):
        repo = make_repo(tmp_path)
        create_plan(repo, "Migration Plan", ["task 1", "task 2"], draft=True)
        plans = _load_plans(repo)
        assert len(plans) == 1
        assert plans[0]["draft"] is True
        assert plans[0]["status"] == "draft"
        assert plans[0]["expires_at"] is not None
        assert plans[0]["expires_at"] > time.time()

    def test_expired_drafts_gc_in_get_status(self, tmp_path):
        repo = make_repo(tmp_path)
        # Manually create an expired draft
        expired_plan = {
            "title": "Old Draft",
            "priority": "high",
            "created": time.time() - 200000,
            "status": "draft",
            "draft": True,
            "expires_at": time.time() - 100,  # expired
            "tasks": [{"id": "MNO-001", "title": "task", "status": "open", "created": time.time(), "completed": None, "summary": ""}],
        }
        _save_plans(repo, [expired_plan])
        result = get_status(repo)
        # After GC, no plans remain
        assert "No active plans" in result
        plans = _load_plans(repo)
        assert len(plans) == 0

    def test_promote_removes_draft_flag(self, tmp_path):
        repo = make_repo(tmp_path)
        create_plan(repo, "Draft Plan", ["step 1", "step 2"], draft=True)
        result = handle_plan(repo, {"action": "promote", "title": "Draft Plan"})
        assert "promoted" in result
        plans = _load_plans(repo)
        assert plans[0]["draft"] is False
        assert plans[0]["expires_at"] is None
        assert plans[0]["status"] == "active"


class TestFrontierScoring:
    def test_returns_highest_priority_task(self, tmp_path):
        repo = make_repo(tmp_path)
        now = time.time()
        plans = [{
            "title": "Test Plan",
            "priority": "high",
            "created": now,
            "status": "active",
            "draft": False,
            "expires_at": None,
            "tasks": [
                {"id": "MNO-001", "title": "Low priority", "status": "open", "created": now, "completed": None, "summary": "", "priority": 1},
                {"id": "MNO-002", "title": "High priority", "status": "open", "created": now, "completed": None, "summary": "", "priority": 5},
                {"id": "MNO-003", "title": "Done task", "status": "done", "created": now, "completed": now, "summary": "", "priority": 10},
            ],
        }]
        next_task = _get_next_task(plans, now)
        assert next_task is not None
        assert next_task["id"] == "MNO-002"

    def test_waiting_time_boosts_score(self, tmp_path):
        now = time.time()
        plans = [{
            "title": "Test",
            "priority": "high",
            "created": now,
            "status": "active",
            "draft": False,
            "expires_at": None,
            "tasks": [
                {"id": "MNO-001", "title": "New task", "status": "open", "created": now, "completed": None, "summary": "", "priority": 3},
                {"id": "MNO-002", "title": "Old task", "status": "open", "created": now - 60 * 86400, "completed": None, "summary": "", "priority": 3},
            ],
        }]
        next_task = _get_next_task(plans, now)
        # Same priority but MNO-002 waited longer → higher score
        assert next_task["id"] == "MNO-002"

    def test_no_open_tasks_returns_none(self, tmp_path):
        now = time.time()
        plans = [{
            "title": "Done Plan",
            "priority": "high",
            "created": now,
            "status": "active",
            "draft": False,
            "expires_at": None,
            "tasks": [
                {"id": "MNO-001", "title": "Done", "status": "done", "created": now, "completed": now, "summary": "", "priority": 3},
            ],
        }]
        assert _get_next_task(plans, now) is None


class TestTemplates:
    def test_save_template_stores_structure(self, tmp_path):
        repo = make_repo(tmp_path)
        create_plan(repo, "SOAP Migration", ["Convert controllers", "Add WSDL", "Update tests"])
        result = save_template(repo, "SOAP Migration", "soap-template")
        assert "saved" in result
        templates_path = repo / ".mnemo" / "templates.json"
        assert templates_path.exists()
        templates = json.loads(templates_path.read_text())
        assert len(templates) == 1
        assert templates[0]["name"] == "soap-template"
        assert len(templates[0]["tasks"]) == 3

    def test_from_template_creates_plan(self, tmp_path):
        repo = make_repo(tmp_path)
        create_plan(repo, "API Migration", ["Step A", "Step B"])
        save_template(repo, "API Migration", "api-tmpl")
        # Clear plans
        _save_plans(repo, [])
        result = from_template(repo, "api-tmpl")
        assert "Plan Created" in result
        plans = _load_plans(repo)
        assert len(plans) == 1
        assert len(plans[0]["tasks"]) == 2

    def test_from_template_not_found(self, tmp_path):
        repo = make_repo(tmp_path)
        result = from_template(repo, "nonexistent")
        assert "No templates found" in result
