"""Claude Code lifecycle hooks installation."""

from __future__ import annotations

import json
import shutil
from pathlib import Path




def install_claude_hooks(repo_root: Path) -> str:
    """Install Claude Code hooks via .claude/settings.json + CLAUDE.md + MCP config."""
    mnemo_bin = shutil.which("mnemo") or "mnemo"
    mnemo_mcp = shutil.which("mnemo-mcp") or "mnemo-mcp"

    claude_dir = repo_root / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)

    # 1. Write .claude/settings.json with hooks
    settings_path = claude_dir / "settings.json"
    existing = {}
    if settings_path.exists():
        try:
            existing = json.loads(settings_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    existing["hooks"] = {
        "SessionStart": [{
            "hooks": [{
                "type": "command",
                "command": f"{mnemo_bin} tool mnemo_recall"
            }]
        }],
        "UserPromptSubmit": [{
            "hooks": [{
                "type": "command",
                "command": f"{mnemo_bin} tool mnemo_search_memory --query \"$ARGUMENTS\"",
                "timeout": 10
            }]
        }],
        "PreToolUse": [{
            "matcher": "Bash",
            "hooks": [{
                "type": "command",
                "command": f"{mnemo_bin} check",
                "timeout": 5
            }]
        }],
        "PostToolUse": [{
            "matcher": "Write|Edit",
            "hooks": [{
                "type": "command",
                "command": f"{mnemo_bin} tool mnemo_remember --content \"Modified file: ${{tool_input.file_path}}\" --category general",
                "timeout": 5
            }]
        }],
        "Stop": [{
            "hooks": [{
                "type": "command",
                "command": f"{mnemo_bin} tool mnemo_remember --content \"Session ended\" --category general",
                "timeout": 10
            }]
        }],
        "PreCompact": [{
            "hooks": [{
                "type": "command",
                "command": f"{mnemo_bin} tool mnemo_recall"
            }]
        }],
    }

    # Ensure MCP server is configured
    if "mcpServers" not in existing:
        existing["mcpServers"] = {}
    existing["mcpServers"]["mnemo"] = {
        "command": mnemo_mcp,
        "args": [],
    }

    settings_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    # 2. Write/append CLAUDE.md with Mnemo instructions
    claude_md = repo_root / "CLAUDE.md"
    mnemo_section = """
## Mnemo — Persistent Memory

This project uses Mnemo for persistent engineering memory across sessions.

### Available via MCP tools (call directly):
- `mnemo_recall` — load full project context
- `mnemo_remember` — store important decisions, patterns, fixes
- `mnemo_decide` — record permanent architectural decisions
- `mnemo_search_memory` — search past memories semantically
- `mnemo_lookup` — get detailed class/method info
- `mnemo_graph` — explore code relationships
- `mnemo_impact` — analyze upstream/downstream dependencies
- `mnemo_plan` — create and track task plans

### Rules:
- Search memory before asking the user something they may have told you before
- Record decisions with mnemo_decide (they persist forever)
- Use mnemo_remember for important context worth keeping
- Learnings are auto-captured at session end via hooks
"""
    if claude_md.exists():
        content = claude_md.read_text(encoding="utf-8")
        if "Mnemo" not in content:
            claude_md.write_text(content + mnemo_section, encoding="utf-8")
    else:
        claude_md.write_text(mnemo_section.lstrip(), encoding="utf-8")

    return (
        f"Claude Code configured:\n"
        f"- Hooks: .claude/settings.json (SessionStart, UserPromptSubmit, PreToolUse, PostToolUse, Stop, PreCompact)\n"
        f"- MCP: mnemo server registered\n"
        f"- Instructions: CLAUDE.md updated\n"
        f"MCP server: {mnemo_mcp}"
    )
