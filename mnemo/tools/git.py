"""Git & Workflow tools."""

from __future__ import annotations

from pathlib import Path

from ..tool_registry import tool


@tool("mnemo_commit_message",
      "Generate a commit message from staged git changes and recent memory context. Returns a conventional commit format message.")
def _commit_message(root: Path, args: dict) -> str:
    from ..commit_gen import generate_commit_message
    return generate_commit_message(root)


@tool("mnemo_pr_description",
      "Generate a PR description from branch diff, active task context, and recent memory. Returns markdown formatted PR body.")
def _pr_description(root: Path, args: dict) -> str:
    from ..pr_gen import generate_pr_description
    return generate_pr_description(root)


@tool("mnemo_hooks_install",
      "Install Mnemo pre-commit git hook for security and pattern validation.")
def _hooks_install(root: Path, args: dict) -> str:
    from ..hooks import install_hooks
    return install_hooks(root, args.get("client", "git"))


@tool("mnemo_check",
      "Run pre-commit validations (security scan) on staged files.")
def _check(root: Path, args: dict) -> str:
    from ..hooks import run_check
    return run_check(root)


@tool("mnemo_snapshot",
      "Create, list, or restore git-backed state snapshots of .mnemo/ data. Actions: create, list, restore.",
      properties={
          "action": {"type": "string", "description": "create, list, or restore"},
          "commit": {"type": "string", "description": "Commit hash to restore (for restore action)"},
      },
      required=["action"])
def _snapshot(root: Path, args: dict) -> str:
    from ..persistence.snapshot import create_snapshot, list_snapshots, restore_snapshot
    action = args.get("action", "create")
    if action == "create":
        return create_snapshot(root)
    elif action == "list":
        entries = list_snapshots(root)
        if not entries:
            return "No snapshots yet."
        lines = ["# Snapshots\n"]
        for e in entries:
            lines.append(f"- `{e['hash'][:8]}` {e['message']}")
        return "\n".join(lines)
    elif action == "restore":
        commit = args.get("commit", "")
        if not commit:
            return "Provide a commit hash to restore."
        return restore_snapshot(root, commit)
    return f"Unknown snapshot action: {action}"


@tool("mnemo_velocity",
      "Show development velocity metrics — commits/day, lines changed, activity by author.")
def _velocity(root: Path, args: dict) -> str:
    from ..velocity import calculate_velocity
    return calculate_velocity(root)
