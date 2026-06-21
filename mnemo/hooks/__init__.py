"""Lifecycle hooks installation for Kiro, Claude Code, and git."""

from __future__ import annotations

from pathlib import Path


def install_hooks(repo_root: Path, client: str = "git") -> str:
    """Install hooks for the specified client."""
    if client == "kiro":
        from .kiro import install_kiro_hooks
        return install_kiro_hooks(repo_root)
    elif client == "claude-code":
        from .claude import install_claude_hooks
        return install_claude_hooks(repo_root)
    from .git import install_git_hooks
    return install_git_hooks(repo_root)


def run_check(repo_root: Path) -> str:
    """Run pre-commit validations (security scan on staged files)."""
    from .git import run_check as _run_check
    return _run_check(repo_root)
