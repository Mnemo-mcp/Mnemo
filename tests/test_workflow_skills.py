"""Tests for workflow skills infrastructure: quality gates, skill loading, plan file handoff."""

import json
import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from mnemo.quality.gates import check_gate, check_all_gates
from mnemo.skills import WORKFLOW_SKILLS


@pytest.fixture
def repo(tmp_path):
    (tmp_path / ".mnemo").mkdir()
    return tmp_path


# --- Quality Gates ---

class TestGateTestsPass:
    def test_no_test_runner_skips(self, repo):
        passed, msg = check_gate(repo, "tests_pass")
        assert passed is True
        assert "skipped" in msg.lower()

    def test_pytest_detected(self, repo):
        (repo / "pyproject.toml").write_text("[tool.pytest]\n")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="5 passed", stderr="")
            passed, msg = check_gate(repo, "tests_pass")
        assert passed is True
        assert "✅" in msg

    def test_pytest_fails(self, repo):
        (repo / "pyproject.toml").write_text("[tool.pytest]\n")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stdout="FAILED test_x.py", stderr="")
            passed, msg = check_gate(repo, "tests_pass")
        assert passed is False
        assert "FAILED" in msg

    def test_npm_detected(self, repo):
        (repo / "package.json").write_text("{}")
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            passed, msg = check_gate(repo, "tests_pass")
        assert passed is True

    def test_timeout_fails(self, repo):
        (repo / "pyproject.toml").write_text("[tool.pytest]\n")
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.TimeoutExpired(cmd="pytest", timeout=300)
            passed, msg = check_gate(repo, "tests_pass")
        assert passed is False
        assert "timed out" in msg.lower()

    def test_runner_not_found_skips(self, repo):
        (repo / "pyproject.toml").write_text("[tool.pytest]\n")
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()
            passed, msg = check_gate(repo, "tests_pass")
        assert passed is True
        assert "skipped" in msg.lower()


class TestGatePlanDone:
    def test_no_plan_skips(self, repo):
        passed, msg = check_gate(repo, "plan_done")
        assert passed is True
        assert "skipped" in msg.lower()

    def test_all_done_passes(self, repo):
        plans = [{"id": "P1", "title": "Test", "status": "active", "tasks": [
            {"id": "T1", "title": "Do X", "status": "done"},
            {"id": "T2", "title": "Do Y", "status": "done"},
        ]}]
        (repo / ".mnemo" / "plans.json").write_text(json.dumps(plans))
        passed, msg = check_gate(repo, "plan_done")
        assert passed is True
        assert "✅" in msg

    def test_pending_tasks_fail(self, repo):
        plans = [{"id": "P1", "title": "Test", "status": "active", "tasks": [
            {"id": "T1", "title": "Do X", "status": "done"},
            {"id": "T2", "title": "Do Y", "status": "pending"},
        ]}]
        (repo / ".mnemo" / "plans.json").write_text(json.dumps(plans))
        passed, msg = check_gate(repo, "plan_done")
        assert passed is False
        assert "1/2 pending" in msg


class TestGateNoFindings:
    def test_no_findings_file_skips(self, repo):
        passed, msg = check_gate(repo, "no_findings")
        assert passed is True

    def test_all_resolved_passes(self, repo):
        findings = [
            {"severity": "high", "summary": "SQL injection", "resolved": True},
            {"severity": "critical", "summary": "Auth bypass", "resolved": True},
        ]
        (repo / ".mnemo" / "review_findings.json").write_text(json.dumps(findings))
        passed, msg = check_gate(repo, "no_findings")
        assert passed is True
        assert "✅" in msg

    def test_unresolved_critical_fails(self, repo):
        findings = [
            {"severity": "high", "summary": "SQL injection in user query", "resolved": False},
            {"severity": "low", "summary": "Naming convention", "resolved": False},
        ]
        (repo / ".mnemo" / "review_findings.json").write_text(json.dumps(findings))
        passed, msg = check_gate(repo, "no_findings")
        assert passed is False
        assert "SQL injection" in msg

    def test_low_severity_unresolved_passes(self, repo):
        findings = [
            {"severity": "low", "summary": "Minor naming issue", "resolved": False},
        ]
        (repo / ".mnemo" / "review_findings.json").write_text(json.dumps(findings))
        passed, msg = check_gate(repo, "no_findings")
        assert passed is True


class TestCheckAllGates:
    def test_returns_all_three_gates(self, repo):
        results = check_all_gates(repo)
        assert len(results) == 3
        gate_names = [r[0] for r in results]
        assert "tests_pass" in gate_names
        assert "plan_done" in gate_names
        assert "no_findings" in gate_names

    def test_unknown_gate(self, repo):
        passed, msg = check_gate(repo, "nonexistent_gate")
        assert passed is False
        assert "Unknown" in msg


# --- Skill Templates ---

class TestSkillTemplates:
    def test_all_skills_exist(self):
        expected = {"investigate", "plan", "implement", "verify", "review", "ship"}
        assert set(WORKFLOW_SKILLS.keys()) == expected

    def test_skills_have_frontmatter(self):
        for name, content in WORKFLOW_SKILLS.items():
            assert content.strip().startswith("---"), f"{name} missing frontmatter"
            # Check closing ---
            lines = content.strip().split("\n")
            frontmatter_end = None
            for i, line in enumerate(lines[1:], 1):
                if line.strip() == "---":
                    frontmatter_end = i
                    break
            assert frontmatter_end is not None, f"{name} missing frontmatter closing ---"

    def test_skills_have_name_field(self):
        for name, content in WORKFLOW_SKILLS.items():
            assert f"name: {name}" in content, f"{name} missing name field in frontmatter"

    def test_skills_are_on_demand(self):
        for name, content in WORKFLOW_SKILLS.items():
            assert "inclusion: on-demand" in content, f"{name} should be on-demand"

    def test_skills_have_steps(self):
        for name, content in WORKFLOW_SKILLS.items():
            assert "## Step" in content or "## Step 1" in content, f"{name} missing steps"

    def test_skills_reference_mnemo_tools(self):
        for name, content in WORKFLOW_SKILLS.items():
            assert "mnemo" in content.lower(), f"{name} doesn't reference mnemo tools"

    def test_skills_have_quality_gate_section(self):
        # implement, verify, review, ship should mention quality/gates/done-checks
        for name in ("implement", "verify", "review", "ship"):
            content = WORKFLOW_SKILLS[name]
            has_gate_ref = "gate" in content.lower() or "quality" in content.lower() or "not done if" in content.lower()
            assert has_gate_ref, f"{name} missing quality/gate/completeness mention"

    def test_investigate_is_read_only(self):
        content = WORKFLOW_SKILLS["investigate"]
        assert "NO code changes" in content or "Read-only" in content

    def test_implement_marks_tasks_done(self):
        content = WORKFLOW_SKILLS["implement"]
        assert "plan" in content.lower() and "done" in content.lower()

    def test_review_has_all_specialists(self):
        content = WORKFLOW_SKILLS["review"].lower()
        assert "security" in content
        assert "performance" in content
        assert "maintainability" in content
        assert "adversarial" in content

    def test_ship_checks_gates_before_commit(self):
        content = WORKFLOW_SKILLS["ship"]
        # Ship should verify tests and plan completion before committing
        assert "test" in content.lower()
        assert "plan" in content.lower()


# --- Skill Installation ---

class TestSkillInstallation:
    def test_kiro_installs_workflow_skills(self, repo):
        # Simulate the kiro install
        from mnemo.skills import WORKFLOW_SKILLS
        for skill_name, skill_content in WORKFLOW_SKILLS.items():
            s_dir = repo / ".kiro" / "skills" / skill_name
            s_dir.mkdir(parents=True, exist_ok=True)
            s_path = s_dir / "SKILL.md"
            s_path.write_text(skill_content.lstrip(), encoding="utf-8")

        # Verify all installed
        for skill_name in WORKFLOW_SKILLS:
            skill_path = repo / ".kiro" / "skills" / skill_name / "SKILL.md"
            assert skill_path.exists(), f"{skill_name} not installed"
            content = skill_path.read_text()
            assert "---" in content
            assert len(content) > 100

    def test_skills_are_valid_yaml_frontmatter(self, repo):
        """Verify the frontmatter can be parsed as YAML."""
        import re
        for name, content in WORKFLOW_SKILLS.items():
            # Extract frontmatter
            match = re.match(r"^---\n(.*?)\n---", content.strip(), re.DOTALL)
            assert match is not None, f"{name} has invalid frontmatter structure"
            fm = match.group(1)
            # Simple check: has key: value lines
            assert "name:" in fm
            assert "description:" in fm
            assert "inclusion:" in fm


# --- Orchestrator ---

from mnemo.skills.orchestrator import (  # noqa: E402
    get_phase_status,
    start_autorun,
    advance_phase,
    get_skill_for_phase,
    reset_autorun,
    format_status,
    PHASES,
)


class TestOrchestrator:
    def test_initial_state_is_not_started(self, repo):
        status = get_phase_status(repo)
        assert status["current_phase"] is None
        assert status["phases_completed"] == []

    def test_start_from_beginning(self, repo):
        state = start_autorun(repo)
        assert state["current_phase"] == "investigate"
        assert state["phase_index"] == 0
        assert state["phases_completed"] == []

    def test_start_from_middle(self, repo):
        state = start_autorun(repo, start_from="implement")
        assert state["current_phase"] == "implement"
        assert state["phase_index"] == 2
        assert "investigate" in state["phases_completed"]
        assert "plan" in state["phases_completed"]

    def test_invalid_start_phase(self, repo):
        with pytest.raises(ValueError, match="Unknown phase"):
            start_autorun(repo, start_from="nonexistent")

    def test_advance_through_phases_no_gates(self, repo):
        start_autorun(repo)
        # investigate → plan (no gate)
        result = advance_phase(repo)
        assert result["advanced"] is True
        assert result["from"] == "investigate"
        assert result["to"] == "plan"

        # plan → implement (no gate)
        result = advance_phase(repo)
        assert result["advanced"] is True
        assert result["to"] == "implement"

        # implement → verify (no gate)
        result = advance_phase(repo)
        assert result["advanced"] is True
        assert result["to"] == "verify"

    def test_advance_to_review_requires_tests_pass(self, repo):
        start_autorun(repo, start_from="verify")
        # verify → review requires tests_pass gate
        # No test runner = gate skipped (passes)
        result = advance_phase(repo)
        assert result["advanced"] is True
        assert result["to"] == "review"

    def test_advance_to_ship_requires_all_gates(self, repo):
        start_autorun(repo, start_from="review")
        # review → ship requires tests_pass + plan_done + no_findings
        # No test runner = skip, no plan = skip, no findings file = skip
        result = advance_phase(repo)
        assert result["advanced"] is True
        assert result["to"] == "ship"

    def test_advance_to_ship_blocked_by_pending_plan(self, repo):
        # Create a plan with pending tasks
        plans = [{"id": "P1", "title": "Test", "status": "active", "tasks": [
            {"id": "T1", "title": "Do X", "status": "pending"},
        ]}]
        (repo / ".mnemo" / "plans.json").write_text(json.dumps(plans))

        start_autorun(repo, start_from="review")
        result = advance_phase(repo)
        assert result["advanced"] is False
        assert result["gate_failed"] == "plan_done"
        assert "pending" in result["message"]

    def test_advance_past_ship_completes(self, repo):
        start_autorun(repo, start_from="ship")
        result = advance_phase(repo)
        assert result["advanced"] is True
        assert result["to"] == "done"
        assert result.get("complete") is True

    def test_advance_when_not_started(self, repo):
        result = advance_phase(repo)
        assert result["advanced"] is False
        assert "not_started" in result.get("gate_failed", "")

    def test_get_skill_for_valid_phase(self, repo):
        skill = get_skill_for_phase("investigate")
        assert skill is not None
        assert "mnemo_lookup" in skill

    def test_get_skill_for_done_returns_none(self, repo):
        assert get_skill_for_phase("done") is None

    def test_reset_clears_state(self, repo):
        start_autorun(repo)
        advance_phase(repo)
        reset_autorun(repo)
        status = get_phase_status(repo)
        assert status["current_phase"] is None

    def test_format_status_not_started(self, repo):
        output = format_status(repo)
        assert "not started" in output.lower()

    def test_format_status_in_progress(self, repo):
        start_autorun(repo)
        advance_phase(repo)  # → plan
        output = format_status(repo)
        assert "✅" in output  # investigate completed
        assert "▶️" in output or "CURRENT" in output  # plan is current

    def test_format_status_complete(self, repo):
        start_autorun(repo, start_from="ship")
        advance_phase(repo)  # → done
        output = format_status(repo)
        assert "COMPLETE" in output

    def test_phases_list_is_correct(self, repo):
        assert PHASES == ["investigate", "plan", "implement", "verify", "review", "ship"]

    def test_state_persists_across_reads(self, repo):
        start_autorun(repo)
        advance_phase(repo)
        # Re-read state (simulates new session)
        status = get_phase_status(repo)
        assert status["current_phase"] == "plan"
        assert "investigate" in status["phases_completed"]
