"""String templates for hook installation."""

HOOK_SCRIPT = """#!/bin/sh
# Mnemo pre-commit hook - validates naming, patterns, security
mnemo check "$@"
"""

_KIRO_AGENT_CONFIG_TEMPLATE = """\
{
  "name": "mnemo-enhanced",
  "description": "Mnemo-powered agent with persistent memory, lifecycle hooks, and skills",
  "useLegacyMcpJson": true,

  "prompt": "You are an engineering assistant with persistent memory powered by Mnemo.\\n\\n## Context\\n\\nYour project context is pre-loaded in <mnemo-context> above via the agentSpawn hook. Do NOT call mnemo_recall unless context appears missing.\\n\\n## TOOL PREFERENCE (use Mnemo first, grep/code as fallback)\\n\\nYou have a pre-indexed knowledge graph of the entire codebase. USE IT FIRST:\\n\\n| Need | Use THIS (fast, indexed) | NOT this (slow, brute-force) |\\n|------|--------------------------|------------------------------|\\n| Understand a class/service | `mnemo_lookup` (instant) | grep + read 20 files |\\n| Find callers/dependencies | `mnemo_graph` action=neighbors | grep for import statements |\\n| What breaks if I change X | `mnemo_impact` | manually trace call chains |\\n| Find code by meaning | `mnemo_search` scope=code | grep for keywords |\\n| Find past knowledge | `mnemo_search_memory` | ask the user again |\\n| See project structure | `mnemo_map` | find + ls recursively |\\n\\nOnly fall back to grep/read when Mnemo tools don't have what you need (e.g., reading file contents to edit, running commands).\\n\\n## COMPLETION PROTOCOL (mandatory — not optional)\\n\\nYou CANNOT consider your response complete until you have persisted what you learned:\\n\\n1. **Explored code** → call mnemo_remember with a summary (category: architecture)\\n2. **Fixed a bug** → call mnemo_remember with root cause + fix (category: bug)\\n3. **Made a choice** → call mnemo_decide with decision + reasoning\\n4. **Found a pattern** → call mnemo_remember (category: pattern)\\n5. **Completed a task** → call mnemo_plan action=done\\n\\nIf you did substantive work but stored 0 memories/decisions, YOU ARE NOT DONE. Go back and persist.\\n\\nMinimum per session type:\\n- Exploration/understanding → at least 1 architecture memory\\n- Implementation → at least 1 decision + what you built\\n- Bug fix → at least 1 bug memory (root cause + fix)\\n- Any multi-step work → at least 1 memory summarizing outcome\\n\\n## Quality Bar for Memories\\n\\nGOOD: \\\"Aries uses pipe-and-filter architecture. PipeFragment subclasses process X12Documents through chains. Key modules: eligibility (270/271), claims (837), auth (SAML).\\\"\\nBAD: \\\"What services exist\\\" (this is a question, not knowledge)\\nBAD: \\\"Run mnemo_audit\\\" (this is an instruction, not knowledge)\\nBAD: \\\"auth.py\\\" (bare path, no context)\\n\\n## Memory Tools\\n\\n- `mnemo_remember` — store knowledge (categories: architecture, bug, pattern, preference)\\n- `mnemo_decide` — permanent architectural decisions (never evicted)\\n- `mnemo_search_memory` — search before asking user questions\\n- `mnemo_plan` — task tracking\\n- `mnemo_lookup` — 360° class/service/function details (methods, callers, callees)\\n- `mnemo_graph` — knowledge graph queries (neighbors, stats, find by type)\\n- `mnemo_search` — hybrid search: code + memory + APIs (scope: code, memory, all)\\n- `mnemo_impact` — blast radius: what breaks if X changes\\n- `mnemo_forget` — delete wrong memories by ID\\n\\n## Rules\\n\\n- All mnemo_* are MCP tool calls to the 'mnemo' server\\n- NEVER read .mnemo/ files directly\\n- Search memory BEFORE asking the user a question\\n- Persist knowledge DURING work, not just at the end\\n- Use mnemo_lookup/graph/search BEFORE grepping the codebase",

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
name: mnemo-persistent-engineer
description: Engineering methodology with mandatory memory persistence. Ensures the agent stores knowledge at every phase — not optional.
inclusion: always
---

# Persistent Engineering Methodology

You MUST follow these steps. Persistence is NOT optional.

## Step 1: Orient
Your context is already injected in <mnemo-context> above (via `mnemo_recall`).
Relevant code and memories for your current prompt are in <mnemo-relevant-context>.
You do NOT need to search — it's already there.

## Step 2: Work
Do the user's task. Use the code context already injected. If you need more detail:
```shell
mnemo tool mnemo_lookup --symbol "ClassName"
mnemo tool mnemo_search --query "what you need" --scope code
```

## Step 3: Persist (MANDATORY — run these shell commands)
BEFORE responding, you MUST run at least one of these:

### Discovered how something works:
```shell
mnemo learn --type architecture --key "SHORT-KEY" --insight "What you discovered about the codebase structure, patterns, or design"
```

### Found a pattern or convention:
```shell
mnemo learn --type pattern --key "SHORT-KEY" --insight "The pattern: what it is, where it applies, how to follow it"
```

### Hit a pitfall or gotcha:
```shell
mnemo learn --type pitfall --key "SHORT-KEY" --insight "What went wrong, why, and how to avoid it"
```

### Fixed a bug:
```shell
mnemo learn --type investigation --key "SHORT-KEY" --insight "Root cause: X. Fix: Y. Prevention: Z"
```

### Made a technical decision:
```shell
mnemo tool mnemo_decide --decision "What you decided" --reasoning "Why you chose this over alternatives"
```

### Learned a tool/operational thing:
```shell
mnemo learn --type tool --key "SHORT-KEY" --insight "How to use X, what flags matter, common gotchas"
```

## Key Rules
- SHORT-KEY must be lowercase with hyphens: `null-check-response`, `pipe-fragment-naming`, `gradle-dep-style`
- Insight must be >20 chars and describe WHAT you learned, not what you were asked
- Run at least ONE persist command per session. Zero = not done.
- If a persist command fails (rejected), fix the content and retry
- Do NOT store the user's question as a learning
- Do NOT store instructions you were given
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
