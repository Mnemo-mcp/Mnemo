"""Git hooks installation and pre-commit check."""

from __future__ import annotations

import stat
from pathlib import Path

from .templates import HOOK_SCRIPT


def install_git_hooks(repo_root: Path) -> str:
    """Install Mnemo pre-commit hook."""
    hooks_dir = repo_root / ".git" / "hooks"
    if not hooks_dir.exists():
        return "No .git/hooks directory found. Is this a git repository?"

    hook_path = hooks_dir / "pre-commit"
    if hook_path.exists():
        content = hook_path.read_text(encoding="utf-8")
        if "mnemo check" in content:
            return "Mnemo pre-commit hook already installed."
        with open(hook_path, "a", encoding="utf-8") as f:
            f.write("\n# Mnemo validation\nmnemo check\n")
        return "Mnemo check appended to existing pre-commit hook."

    hook_path.write_text(HOOK_SCRIPT, encoding="utf-8")
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IEXEC)
    return "Pre-commit hook installed."


def run_check(repo_root: Path) -> str:
    """Run pre-commit validations (security scan on staged files)."""
    import subprocess  # nosec B404

    from ..security import check_security

    try:
        result = subprocess.run(  # nosec B603 B607
            ["git", "diff", "--cached", "--name-only"],
            cwd=repo_root, capture_output=True, text=True, timeout=5,
        )
        staged = [f.strip() for f in result.stdout.splitlines() if f.strip()]
    except (subprocess.TimeoutExpired, FileNotFoundError):
        staged = []

    if not staged:
        return "No staged files to check."

    issues = []
    for file in staged:
        result = check_security(repo_root, file)
        if "No security issues" not in result:
            issues.append(result)

    if not issues:
        return f"✅ {len(staged)} files checked — no issues found."

    return "⚠️ Issues found in staged files:\n\n" + "\n".join(issues)
