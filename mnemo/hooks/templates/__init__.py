"""String templates for hook installation."""

HOOK_SCRIPT = """#!/bin/sh
# Mnemo pre-commit hook - validates naming, patterns, security
mnemo check "$@"
"""

_KIRO_AGENT_CONFIG_TEMPLATE = """\
{
  "name": "mnemo-enhanced",
  "description": "Mnemo-powered agent with persistent memory, automatic learning, and lifecycle hooks",
  "useLegacyMcpJson": true,

  "prompt": "You are an engineering assistant powered by Mnemo — a persistent memory system.\\n\\n## Context Loading\\n\\nYour project context is AUTOMATICALLY loaded at session start by the agentSpawn hook. You already have it as <mnemo-context>. You do NOT need to call mnemo_recall yourself — it was already done.\\n\\nIf context appears missing, use the MCP tool `mnemo_recall`. NEVER read .mnemo/ files. All memory operations are MCP tool calls only.\\n\\n## Memory Responsibilities\\n\\nHooks auto-capture user decisions from their messages. YOUR job is to persist context that only YOU can see:\\n\\n### Call `mnemo_decide` when:\\n- You make or confirm an architectural choice (database, framework, pattern, deployment target)\\n- You choose between approaches during implementation\\n- The user approves a technical direction you proposed\\n\\n### Call `mnemo_remember` when:\\n- You discover something about the codebase through investigation (category: architecture)\\n- You fix a bug — save root cause + fix (category: bug)\\n- You identify a pattern or convention in the code (category: pattern)\\n- You learn a user preference through their feedback (category: preference)\\n\\n### Call `mnemo_search_memory` before:\\n- Asking the user a question (they may have answered in a past session)\\n- Making assumptions about the project setup\\n\\n### Do NOT remember:\\n- Temporary debugging output\\n- Things obvious from the code itself\\n- File paths you modified (noise)\\n\\n## Tools\\n\\n- `mnemo_plan` — task tracking (create, status, done)\\n- `mnemo_graph` — code knowledge graph (neighbors, stats, find)\\n- `mnemo_lookup` — 360° symbol/service details\\n- `mnemo_search` — hybrid search (code + memory + APIs)\\n- `mnemo_impact` — blast radius analysis\\n- `mnemo_audit` — security, health, conventions\\n\\n## Memory Slots\\n\\nUse `mnemo_slot_set`/`mnemo_slot_get` for structured context: project_context, user_preferences, conventions, pending_items, known_gotchas.",

  "tools": [
    "read", "write", "shell", "grep", "glob", "code",
    "use_aws", "web_search", "web_fetch",
    "knowledge", "subagent", "todo_list"
  ],

  "allowedTools": [
    "read", "write", "shell", "grep", "glob", "code",
    "use_aws", "web_search", "web_fetch",
    "knowledge", "subagent", "todo_list",
    "mnemo:*"
  ],

  "resources": [],

  "hooks": {
    "agentSpawn": [
      {
        "command": "HOOK_SPAWN_PATH",
        "timeout_ms": 15000
      }
    ],
    "userPromptSubmit": [
      {
        "command": "HOOK_PROMPT_PATH",
        "timeout_ms": 5000
      }
    ],
    "preToolUse": [
      {
        "matcher": "shell",
        "command": "HOOK_PRETOOL_PATH",
        "timeout_ms": 2000
      }
    ],
    "postToolUse": [
      {
        "command": "HOOK_POSTTOOL_PATH",
        "timeout_ms": 3000
      }
    ],
    "stop": [
      {
        "command": "HOOK_STOP_PATH",
        "timeout_ms": 10000
      }
    ]
  },

  "mcpServers": {
    "mnemo": {
      "command": "MCP_BINARY_PATH",
      "args": [],
      "timeout": 30000
    }
  }
}
"""

_MNEMO_SKILL = """---
name: mnemo-memory-system
description: Reference for Mnemo MCP tool names and parameters. Use only when you need to look up the exact syntax of a specific mnemo tool.
inclusion: on_demand
---

# Mnemo — Persistent Engineering Memory

## What Hooks Handle (automatic, you don't need to do this)

- **Session start**: context loaded automatically via agentSpawn hook
- **User decisions**: user-prompt-submit hook detects naming, preferences, corrections from user messages
- **Bug fix detection**: stop hook detects learning patterns from your responses
- **Security**: pre-tool-use hook blocks dangerous commands

## What YOU Must Handle (hooks can't see this)

Hooks only see user messages and your final response. They can't see what you discover DURING work. You must persist:

| When | Tool | Category |
|------|------|----------|
| You choose an approach | `mnemo_decide` | — |
| You discover how the codebase works | `mnemo_remember` | architecture |
| You fix a bug | `mnemo_remember` | bug |
| You notice a pattern/convention | `mnemo_remember` | pattern |
| User gives feedback on your work | `mnemo_remember` | preference |

## Tool Reference

| Tool | Purpose |
|------|---------|
| `mnemo_recall` | Load context (auto-called at start) |
| `mnemo_remember` | Store context (architecture, bug, pattern, preference, general) |
| `mnemo_decide` | Permanent architectural decision (never evicted) |
| `mnemo_forget` | Delete a memory by ID |
| `mnemo_search_memory` | Search past memories |
| `mnemo_lookup` | 360° symbol/service details |
| `mnemo_search` | Hybrid search: code + memory + APIs |
| `mnemo_graph` | Knowledge graph queries |
| `mnemo_impact` | Blast radius analysis |
| `mnemo_plan` | Task tracking (create, status, done, add) |
| `mnemo_audit` | Security, health, conventions |
| `mnemo_record` | Errors, incidents, reviews, corrections |
| `mnemo_generate` | Commit/PR descriptions |
| `mnemo_map` | Regenerate repo map |
| `mnemo_lesson` | Learned patterns with decay |

## Memory Slots

Structured context via `mnemo_slot_set`/`mnemo_slot_get`:
- `project_context` — what this project is
- `user_preferences` — style, conventions
- `pending_items` — follow-ups
- `known_gotchas` — pitfalls

## Rules

- All operations are MCP tool calls to the 'mnemo' server
- NEVER read .mnemo/ files directly
- Search memory before asking the user a question
"""

_CLAUDE_SKILL = """# Mnemo Memory System

## Usage Rules

1. Always call `mnemo recall` at session start
2. Search memory before asking user for context: `mnemo tool mnemo_search_memory --query "topic"`
3. Remember important findings: `mnemo tool mnemo_remember --content "what you learned"`
4. Record decisions: `mnemo tool mnemo_decide --decision "what" --reasoning "why"`
5. Check plan status: `mnemo tool mnemo_plan --action status`
6. Use slots for structured context: `mnemo tool mnemo_slot_set --name "project_context" --content "..."`

## What to Remember
- Architecture decisions with reasoning
- Bug root causes and fixes
- Patterns and conventions discovered
- User preferences

## What NOT to Remember
- Temporary debug output
- Secrets (auto-stripped anyway)
- Things obvious from the code
"""
