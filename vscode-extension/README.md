# Mnemo — VS Code Extension

Persistent engineering cognition for AI coding agents. Your agent remembers decisions, understands code relationships, and never asks the same question twice.

## Features

- **Auto-init** — prompts to initialize when you open a workspace without `.mnemo/`
- **Client detection** — auto-detects Kiro, Amazon Q, Cursor, Claude Code; asks if none found
- **Status bar** — shows Mnemo status (Active/Inactive)
- **Refresh index** — re-scan codebase after major changes
- **Doctor** — diagnose installation and MCP connectivity

## Commands

| Command | Description |
|---------|-------------|
| `Mnemo: Initialize Workspace` | Set up Mnemo with client picker |
| `Mnemo: Show Status` | Run diagnostics (doctor) |
| `Mnemo: Refresh Index` | Re-scan and rebuild code graph |
| `Mnemo: Reset` | Wipe all memory (with confirmation) |
| `Mnemo: Check Installation` | Verify mnemo binary is available |

## How It Works

1. Extension activates on workspace open
2. If `.mnemo/` doesn't exist → prompts "Initialize project memory?"
3. Auto-detects your AI client (Kiro, Amazon Q, Cursor, Claude Code)
4. If multiple or none detected → shows picker
5. Runs `mnemo init --client <choice>` which:
   - Builds knowledge graph (classes, methods, calls, communities)
   - Installs lifecycle hooks for your client
   - Configures MCP server
   - Downloads embedding model (one-time, 86MB)

## What Your Agent Gets

After initialization, your AI agent has access to 16 MCP tools:

- **Memory**: recall, remember, forget, decide, search
- **Code Intelligence**: lookup, graph, impact, search, communities
- **Planning**: create plans, track progress, mark done
- **Safety**: security scan, dead code, conventions audit

## Requirements

- Python 3.10+
- `pip install mnemo-dev` (or extension auto-downloads binary)

## Supported Clients

| Client | Auto-detected | How |
|--------|--------------|-----|
| Kiro | ✅ | `.kiro/` directory in workspace |
| Amazon Q | ✅ | VS Code extension installed |
| Cursor | ✅ | `~/.cursor/` exists |
| Claude Code | ✅ | `~/.claude/` exists |
| Copilot | Manual pick | Select from QuickPick |
| Generic | Manual pick | Creates MNEMO.md instructions |

## Performance

- Init: 3-7 seconds (depending on repo size)
- Search: 2ms (semantic + keyword + graph)
- RAM: ~265 MB
- No external databases or servers
