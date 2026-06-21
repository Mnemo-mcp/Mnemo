"""Template resolvers — shared logic injected into skill templates.

Each resolver is a function: (repo_root, context) → str
Templates use {{RESOLVER_NAME}} which gets replaced with the resolver's output.

Resolvers:
    PREAMBLE        — Always-on header: DO NOT PROCEED commands, tool permissions
    LEARNINGS       — Past learnings relevant to the current skill
    CONTEXT_LOAD    — Shell command to load brain context at skill start
    TOOL_REFERENCE  — Available mnemo commands table
    PERSIST_BLOCK   — Shell commands for persisting knowledge (end of skill)
    SLUG_SETUP      — Project slug detection for paths
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def resolve_preamble(repo_root: Path, context: dict[str, Any] | None = None) -> str:
    """The critical always-on header. Forces agent to use mnemo tools.

    This is the gstack equivalent of {{PREAMBLE}} — the universal header
    that appears in EVERY skill and contains the non-negotiable instructions.
    """
    return """## ⚠️ MANDATORY — Read Before Doing Anything

You have a pre-indexed knowledge graph of this codebase (classes, methods, callers, callees, impact analysis).
It is FASTER and MORE COMPLETE than grep. Use it.

### BEFORE starting any work, run this command and show the output:

```bash
mnemo tool mnemo_lookup --symbol "<the main class or function relevant to the user's request>"
```

**DO NOT PROCEED** until you have run the above command and included its output in your response.
If you skip this step, your work will be based on incomplete information.

### BEFORE finishing your response, run ONE of these:

```bash
mnemo learn --type architecture --key "<topic-key>" --insight "<what you discovered about the codebase>"
```
```bash
mnemo learn --type pattern --key "<topic-key>" --insight "<the pattern you found or followed>"
```
```bash
mnemo tool mnemo_decide --decision "<technical choice you made>" --reasoning "<why>"
```

**DO NOT CONSIDER YOUR RESPONSE COMPLETE** until you have run at least one persist command above.

---"""


def resolve_learnings(repo_root: Path, context: dict[str, Any] | None = None) -> str:
    """Inject relevant past learnings for the current skill/topic."""
    return """### Past Learnings

To see what the project already knows about this area:
```bash
mnemo tool mnemo_search --query "<topic>" --scope memory
```

Run this if you're unsure about conventions, past decisions, or known pitfalls.

---"""


def resolve_context_load(repo_root: Path, context: dict[str, Any] | None = None) -> str:
    """Shell command to load full brain context at skill start."""
    return """### Load Project Context

```bash
mnemo recall
```

This shows: active decisions, hot memories, current plan, repo structure.

---"""


def resolve_tool_reference(repo_root: Path, context: dict[str, Any] | None = None) -> str:
    """Available mnemo commands — the agent's toolbox via shell."""
    return """### Available Commands

| Need | Command |
|------|---------|
| Understand a class/module | `mnemo tool mnemo_lookup --symbol "ClassName"` |
| What breaks if I change X | `mnemo tool mnemo_impact --symbol "ClassName"` |
| Find code by meaning | `mnemo tool mnemo_search --query "..." --scope code` |
| Find past knowledge | `mnemo tool mnemo_search --query "..." --scope memory` |
| See project structure | `mnemo tool mnemo_graph --action stats` |
| Find by name | `mnemo tool mnemo_graph --action find --name "partial"` |
| See callers/callees | `mnemo tool mnemo_graph --action neighbors --node "ClassName"` |
| Record a decision | `mnemo tool mnemo_decide --decision "..." --reasoning "..."` |
| Create a plan | `mnemo tool mnemo_plan --action create --title "..." --tasks '[...]'` |
| Mark task done | `mnemo tool mnemo_plan --action done --task_id "..." --summary "..."` |
| Check plan status | `mnemo tool mnemo_plan --action status` |
| Generate commit msg | `mnemo tool mnemo_generate --target commit` |
| Generate PR desc | `mnemo tool mnemo_generate --target pr` |
| Security audit | `mnemo tool mnemo_audit --report security` |
| Store a learning | `mnemo learn --type <type> --key "<key>" --insight "<insight>"` |

Learning types: `architecture`, `pattern`, `pitfall`, `tool`, `investigation`, `preference`, `operational`

---"""


def resolve_persist_block(repo_root: Path, context: dict[str, Any] | None = None) -> str:
    """End-of-skill persistence commands."""
    return """### Persist What You Learned (MANDATORY)

Before you finish, run at least ONE:

```bash
mnemo learn --type architecture --key "<topic>" --insight "<what you discovered>"
```
```bash
mnemo learn --type pattern --key "<topic>" --insight "<the pattern: what, where, how>"
```
```bash
mnemo learn --type pitfall --key "<topic>" --insight "<what went wrong, why, how to avoid>"
```
```bash
mnemo tool mnemo_decide --decision "<choice made>" --reasoning "<why this over alternatives>"
```

**You are NOT done if you haven't persisted at least one thing.**"""


# Registry of all resolvers
RESOLVERS: dict[str, Any] = {
    "PREAMBLE": resolve_preamble,
    "LEARNINGS": resolve_learnings,
    "CONTEXT_LOAD": resolve_context_load,
    "TOOL_REFERENCE": resolve_tool_reference,
    "PERSIST_BLOCK": resolve_persist_block,
}
