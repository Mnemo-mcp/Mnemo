"""Comprehensive tests for the hooks system (discovery, kiro, claude, git, integration)."""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from unittest.mock import patch

import pytest

from mnemo.hooks import install_hooks, run_check
from mnemo.hooks.discovery import find_mnemo_cli, find_mnemo_mcp
from mnemo.hooks.kiro import install_kiro_hooks
from mnemo.hooks.claude import install_claude_hooks
from mnemo.hooks.git import install_git_hooks


# ─── 1. Binary Discovery Tests ───────────────────────────────────────────────


class TestBinaryDiscovery:
    def test_find_mnemo_mcp_on_path(self):
        with patch("shutil.which", return_value="/usr/local/bin/mnemo-mcp"):
            assert find_mnemo_mcp() == "/usr/local/bin/mnemo-mcp"

    def test_find_mnemo_mcp_fallback_candidates(self, tmp_path):
        candidate = tmp_path / ".local" / "bin" / "mnemo-mcp"
        candidate.parent.mkdir(parents=True)
        candidate.touch()

        with patch("shutil.which", return_value=None), \
             patch("pathlib.Path.home", return_value=tmp_path):
            result = find_mnemo_mcp()
            assert result == str(candidate)

    def test_find_mnemo_mcp_returns_fallback_string_when_not_found(self, tmp_path):
        with patch("shutil.which", return_value=None), \
             patch("pathlib.Path.home", return_value=tmp_path):
            assert find_mnemo_mcp() == "mnemo-mcp"

    def test_find_mnemo_cli(self):
        with patch("shutil.which", return_value="/usr/local/bin/mnemo"):
            assert find_mnemo_cli() == "/usr/local/bin/mnemo"

    def test_find_mnemo_cli_fallback(self):
        with patch("shutil.which", return_value=None):
            assert find_mnemo_cli() == "mnemo"


# ─── 2. Kiro Hook Installation Tests ─────────────────────────────────────────


class TestKiroHooks:
    @pytest.fixture()
    def repo(self, tmp_path):
        """Create a minimal repo structure and run kiro install."""
        with patch("shutil.which", return_value="/usr/bin/mnemo"):
            install_kiro_hooks(tmp_path)
        return tmp_path

    def test_kiro_creates_agent_config(self, repo):
        config = repo / ".kiro" / "agents" / "mnemo-enhanced.json"
        assert config.exists()
        data = json.loads(config.read_text())
        assert data["name"] == "mnemo-enhanced"

    def test_kiro_agent_config_has_all_hooks(self, repo):
        config = repo / ".kiro" / "agents" / "mnemo-enhanced.json"
        data = json.loads(config.read_text())
        hooks = data["hooks"]
        assert "agentSpawn" in hooks
        assert "userPromptSubmit" in hooks
        assert "preToolUse" in hooks
        assert "postToolUse" in hooks
        assert "stop" in hooks

    def test_kiro_agent_config_uses_relative_paths(self, repo):
        config = repo / ".kiro" / "agents" / "mnemo-enhanced.json"
        data = json.loads(config.read_text())
        hooks = data["hooks"]
        for key, entries in hooks.items():
            for entry in entries:
                cmd = entry["command"]
                # Must be relative — starts with .kiro/ not /
                assert not cmd.startswith("/"), f"{key} has absolute path: {cmd}"
                assert cmd.startswith(".kiro/"), f"{key} path not relative: {cmd}"

    def test_kiro_creates_skill_file(self, repo):
        skill = repo / ".kiro" / "skills" / "mnemo" / "SKILL.md"
        assert skill.exists()
        content = skill.read_text()
        assert "mnemo_recall" in content
        assert "mnemo learn" in content

    def test_kiro_hook_scripts_are_executable(self, repo):
        hooks_dir = repo / ".kiro" / "hooks"
        for script in hooks_dir.glob("*.sh"):
            mode = script.stat().st_mode
            assert mode & stat.S_IEXEC, f"{script.name} is not executable"

    def test_kiro_hook_scripts_start_with_shebang(self, repo):
        hooks_dir = repo / ".kiro" / "hooks"
        for script in hooks_dir.glob("*.sh"):
            first_line = script.read_text().splitlines()[0]
            assert first_line.startswith("#!/bin/sh"), f"{script.name} missing shebang"

    def test_kiro_hook_scripts_always_exit_zero(self, repo):
        hooks_dir = repo / ".kiro" / "hooks"
        for script in hooks_dir.glob("*.sh"):
            content = script.read_text()
            # pre-tool-use is special: it exits 1 to block commands
            if "pre-tool-use" in script.name:
                assert "exit 0" in content  # has an exit 0 path
                continue
            # All others must end with exit 0
            lines = [l.strip() for l in content.strip().splitlines() if l.strip()]
            assert lines[-1] == "exit 0", f"{script.name} doesn't end with exit 0"

    def test_kiro_spawn_hook_calls_mnemo_recall(self, repo):
        spawn = repo / ".kiro" / "hooks" / "agent-spawn.sh"
        content = spawn.read_text()
        assert "mnemo_recall" in content

    def test_kiro_stop_hook_detects_learnings(self, repo):
        stop = repo / ".kiro" / "hooks" / "stop.sh"
        content = stop.read_text()
        # Must detect bug fixes via keyword matching
        assert "LEARNING_SCORE" in content
        assert "fixed" in content or "solved" in content
        assert "root cause" in content or "the issue was" in content

    def test_kiro_pretool_hook_blocks_dangerous_commands(self, repo):
        pretool = repo / ".kiro" / "hooks" / "pre-tool-use.sh"
        content = pretool.read_text()
        assert "rm -rf /" in content
        assert "exit 2" in content
        # Blocks credential exfiltration
        assert "credential" in content.lower() or "exfil" in content.lower()

    def test_kiro_hook_scripts_no_shell_injection(self, repo):
        """Verify hooks don't pass user-controlled vars directly to --content args.

        Safe pattern: pipe through stdin or use printf '%s'
        Dangerous: --content "$USER_INPUT" (allows $(cmd) injection)
        """
        hooks_dir = repo / ".kiro" / "hooks"
        for script in hooks_dir.glob("*.sh"):
            content = script.read_text()
            lines = content.splitlines()
            for i, line in enumerate(lines, 1):
                # Check for dangerous patterns: direct variable interpolation in mnemo tool args
                # Safe: printf '%s' "..." | "$MNEMO" tool ... --content "$(cat)"
                # Dangerous: "$MNEMO" tool ... --content "$RESPONSE"
                if "mnemo" in line.lower() and "--content" in line:
                    # Allow the safe piped pattern
                    if 'printf' in line or '$(cat)' in line:
                        continue
                    # Flag direct variable interpolation
                    assert '"$RESPONSE"' not in line and '"$USER_PROMPT"' not in line, (
                        f"{script.name}:{i} has unsafe interpolation: {line.strip()}"
                    )


# ─── 3. Claude Hook Installation Tests ───────────────────────────────────────


class TestClaudeHooks:
    @pytest.fixture()
    def repo(self, tmp_path):
        with patch("shutil.which", return_value="/usr/bin/mnemo"):
            install_claude_hooks(tmp_path)
        return tmp_path

    def test_claude_creates_settings_json(self, repo):
        settings = repo / ".claude" / "settings.json"
        assert settings.exists()
        data = json.loads(settings.read_text())
        assert isinstance(data, dict)

    def test_claude_settings_has_hooks(self, repo):
        settings = repo / ".claude" / "settings.json"
        data = json.loads(settings.read_text())
        hooks = data["hooks"]
        assert "SessionStart" in hooks
        assert "UserPromptSubmit" in hooks
        assert "PreToolUse" in hooks
        assert "PostToolUse" in hooks
        assert "Stop" in hooks
        assert "PreCompact" in hooks

    def test_claude_settings_has_mcp_server(self, repo):
        settings = repo / ".claude" / "settings.json"
        data = json.loads(settings.read_text())
        assert "mnemo" in data["mcpServers"]

    def test_claude_creates_claude_md(self, repo):
        claude_md = repo / "CLAUDE.md"
        assert claude_md.exists()
        content = claude_md.read_text()
        assert "Mnemo" in content
        assert "mnemo_recall" in content

    def test_claude_preserves_existing_settings(self, tmp_path):
        """If settings.json already has other keys, they survive."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        (claude_dir / "settings.json").write_text(
            json.dumps({"existingKey": True}), encoding="utf-8"
        )
        with patch("shutil.which", return_value="/usr/bin/mnemo"):
            install_claude_hooks(tmp_path)
        data = json.loads((claude_dir / "settings.json").read_text())
        assert data["existingKey"] is True
        assert "hooks" in data

    def test_claude_md_not_duplicated(self, tmp_path):
        """Running twice doesn't duplicate the Mnemo section."""
        with patch("shutil.which", return_value="/usr/bin/mnemo"):
            install_claude_hooks(tmp_path)
            install_claude_hooks(tmp_path)
        content = (tmp_path / "CLAUDE.md").read_text()
        assert content.count("## Mnemo") == 1


# ─── 4. Git Hook Installation Tests ──────────────────────────────────────────


class TestGitHooks:
    @pytest.fixture()
    def repo(self, tmp_path):
        hooks_dir = tmp_path / ".git" / "hooks"
        hooks_dir.mkdir(parents=True)
        install_git_hooks(tmp_path)
        return tmp_path

    def test_git_creates_pre_commit_hook(self, repo):
        hook = repo / ".git" / "hooks" / "pre-commit"
        assert hook.exists()

    def test_git_pre_commit_is_executable(self, repo):
        hook = repo / ".git" / "hooks" / "pre-commit"
        mode = hook.stat().st_mode
        assert mode & stat.S_IEXEC

    def test_git_pre_commit_calls_mnemo_check(self, repo):
        hook = repo / ".git" / "hooks" / "pre-commit"
        content = hook.read_text()
        assert "mnemo check" in content

    def test_git_no_git_dir_returns_error(self, tmp_path):
        result = install_git_hooks(tmp_path)
        assert "No .git/hooks" in result

    def test_git_appends_to_existing_hook(self, tmp_path):
        hooks_dir = tmp_path / ".git" / "hooks"
        hooks_dir.mkdir(parents=True)
        hook = hooks_dir / "pre-commit"
        hook.write_text("#!/bin/sh\necho existing\n")
        install_git_hooks(tmp_path)
        content = hook.read_text()
        assert "echo existing" in content
        assert "mnemo check" in content


# ─── 5. run_check Tests ──────────────────────────────────────────────────────


class TestRunCheck:
    def test_run_check_with_no_staged_files(self, tmp_path):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = type("R", (), {"stdout": "", "returncode": 0})()
            result = run_check(tmp_path)
        assert "No staged files" in result

    def test_run_check_reports_security_issues(self, tmp_path):
        # Create a staged file with a hardcoded secret
        secret_file = tmp_path / "config.py"
        secret_file.write_text('password = "SuperSecret123!"\n')

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = type("R", (), {"stdout": "config.py\n", "returncode": 0})()
            with patch("mnemo.security.check_security") as mock_sec:
                mock_sec.return_value = "⚠️ hardcoded_secret: config.py:1"
                result = run_check(tmp_path)

        assert "Issues found" in result or "⚠️" in result


# ─── 6. Integration Tests ────────────────────────────────────────────────────


class TestIntegration:
    def test_install_hooks_dispatches_correctly(self, tmp_path):
        """Verify dispatcher routes to the right installer."""
        (tmp_path / ".git" / "hooks").mkdir(parents=True)

        with patch("shutil.which", return_value="/usr/bin/mnemo"):
            # kiro
            result = install_hooks(tmp_path, "kiro")
            assert "Kiro" in result or ".kiro" in result

            # claude-code
            result = install_hooks(tmp_path, "claude-code")
            assert "Claude" in result or ".claude" in result

            # git (default)
            result = install_hooks(tmp_path, "git")
            assert "hook" in result.lower()

    def test_install_hooks_idempotent(self, tmp_path):
        """Running install twice doesn't corrupt files."""
        (tmp_path / ".git" / "hooks").mkdir(parents=True)

        with patch("shutil.which", return_value="/usr/bin/mnemo"):
            install_hooks(tmp_path, "kiro")
            install_hooks(tmp_path, "kiro")

        # Agent config is still valid JSON
        config = tmp_path / ".kiro" / "agents" / "mnemo-enhanced.json"
        data = json.loads(config.read_text())
        assert data["name"] == "mnemo-enhanced"

        # Hook scripts haven't been corrupted
        hooks_dir = tmp_path / ".kiro" / "hooks"
        for script in hooks_dir.glob("*.sh"):
            content = script.read_text()
            assert content.startswith("#!/bin/sh")

    def test_install_hooks_default_is_git(self, tmp_path):
        """No client arg defaults to git."""
        (tmp_path / ".git" / "hooks").mkdir(parents=True)
        result = install_hooks(tmp_path)
        assert "hook" in result.lower()
