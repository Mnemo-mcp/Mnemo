"""Prompt templates for client context files."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..clients import ClientTarget

# MCP-native clients call tools directly (mnemo_recall, mnemo_lookup, etc.)
_MCP_CLIENTS = {"amazonq", "cursor", "claude-code", "copilot", "kiro", "windsurf", "cline", "roo-code", "gemini-cli", "opencode", "goose"}

MNEMO_RULE_HEADER_MCP = """\
You have access to Mnemo - a persistent memory system for this project.
All project context, decisions, and chat history is below. Use it to answer questions without re-reading files.

AT THE START OF EVERY CHAT:
- Call `mnemo_recall` to get the latest context. The embedded context below may be stale.

ANSWERING QUESTIONS:
- If the recalled memory already contains the answer, USE IT DIRECTLY. Do not re-read files or re-run lookups for information already in memory.
- Only call `mnemo_lookup` or read files when memory does not have enough detail to answer.

SAVING MEMORY:
- Call `mnemo_remember` AFTER any of these happen in the conversation:
  - You made a code change that affects behavior (theme change, config change, new feature, refactor)
  - A bug was found and fixed
  - A design or architecture decision was made
  - The user stated a preference or convention
  - A TODO or follow-up was identified
  - You learned something non-obvious about the codebase
- Call `mnemo_remember` when the context window is getting long to summarize progress so far.
- Call `mnemo_remember` when the user explicitly asks to remember something.
- Do NOT save trivial things like "read a file" or "answered a question with no new insight".
- When in doubt, SAVE. It is better to remember too much than to forget something useful.
- RULE: If you called `mnemo_lookup`, `mnemo_search`, or `mnemo_who_touched` AND produced a summary or analysis from the results, you MUST call `mnemo_remember` with a concise summary before ending your response.

WHEN TO USE WHAT:
- Understanding code structure → `mnemo_lookup` or `mnemo_graph action=neighbors`
- Finding patterns/similar code → `mnemo_search` or `mnemo_graph action=find`
- Impact of a change → `mnemo_impact`
- Code relationships → `mnemo_graph action=neighbors`
- Code health/quality → `mnemo_audit report=health` or `mnemo_audit report=security`
- Team/ownership → `mnemo_record type=review action=list`
- History/context → `mnemo_search_memory`, `mnemo_record type=error action=search`
- Knowledge base → `mnemo_search_memory`
- Record decisions → `mnemo_decide`
- Refresh after code changes → `mnemo_map`
- Cross-repo search → `mnemo_search`

PLAN MODE:
- When the user asks to plan a feature, break work into tasks, or track progress → use `mnemo_plan`
- `mnemo_plan action=create` — create a new plan with tasks
- `mnemo_plan action=done` — mark a task complete (with summary)
- `mnemo_plan action=status` — show current plan progress
- After completing any work that matches an open plan item, AUTOMATICALLY call `mnemo_plan action=done`
- When starting a new chat, if plan status shows open tasks, mention what's next

CROSS-REPO AWARENESS:
- This repo may have linked sibling repos. Use `mnemo_search` to find code across them.
- If `mnemo_lookup` returned no results, try `mnemo_search` with a broader query.
- If the user asks "what breaks if I change X", use `mnemo_impact` for dependency analysis.

---

"""

MNEMO_RULE_HEADER_CLI = """\
You have access to Mnemo - a persistent memory system for this project.
Mnemo is available as a CLI tool. Run commands in the terminal to access project memory, code intelligence, and knowledge graph.

IMPORTANT: You do NOT have MCP tools. Use `mnemo tool <name> [--arg value]` shell commands instead.
Run `mnemo tools` to see all available tools.

AT THE START OF EVERY CHAT:
- Run `mnemo tool recall` in the terminal to get the latest project context.

ANSWERING QUESTIONS:
- If the recalled memory already contains the answer, USE IT DIRECTLY. Do not re-read files or re-run lookups for information already in memory.
- Only run `mnemo tool lookup --query <name>` or read files when memory does not have enough detail to answer.

SAVING MEMORY:
- Run `mnemo tool remember --content "<info>"` AFTER any of these happen:
  - You made a code change that affects behavior
  - A bug was found and fixed
  - A design or architecture decision was made
  - The user stated a preference or convention
  - A TODO or follow-up was identified
  - You learned something non-obvious about the codebase
- Do NOT save trivial things like "read a file" or "answered a question with no new insight".
- When in doubt, SAVE. It is better to remember too much than to forget something useful.

COMMAND REFERENCE:
- Get project context → `mnemo tool recall`
- Code structure → `mnemo tool lookup --query <file_or_class>`
- Remember something → `mnemo tool remember --content "<text>" --category general`
- Search memory → `mnemo tool search_memory --query "<text>"`
- Record decision → `mnemo tool decide --decision "<text>" --reasoning "<why>"`
- Knowledge graph → `mnemo tool graph --action stats`
- Graph neighbors → `mnemo tool graph --action neighbors --node <name>`
- Graph traverse → `mnemo tool graph --action traverse --node <name> --direction incoming`
- Find similar code → `mnemo tool similar --query <pattern>`
- Impact analysis → `mnemo tool impact --query <service>`
- Cross-repo search → `mnemo tool cross_search --query "<text>"`
- Cross-repo impact → `mnemo tool cross_impact --query <service>`
- Code health → `mnemo tool health`
- Dead code → `mnemo tool dead_code`
- Security scan → `mnemo tool check_security`
- Team expertise → `mnemo tool team`
- Who touched file → `mnemo tool who_touched --query <file>`
- APIs → `mnemo tool discover_apis`
- Plan status → `mnemo tool plan --action status`
- Linked repos → `mnemo tool links`
- All tools → `mnemo tools`

PLAN MODE:
- Create plan → `mnemo tool plan --action create --title "<name>" --tasks '["task1", "task2"]'`
- Mark done → `mnemo tool plan --action done --task_id MNO-001 --summary "completed"`
- Check status → `mnemo tool plan --action status`
- After completing work that matches an open plan item, AUTOMATICALLY mark it done.

CROSS-REPO AWARENESS:
- This repo may have linked sibling repos. Run `mnemo tool links` to see them.
- ALWAYS run `mnemo tool cross_search --query "<text>"` BEFORE using grep when:
  - The user asks about code that does not exist in this repo
  - The user mentions a service or module that is not a folder in this repo
- If the user asks "what breaks if I change X", run `mnemo tool cross_impact --query <name>`.

---

"""

# Backward compat alias
MNEMO_RULE_HEADER = MNEMO_RULE_HEADER_MCP


def build_rule_with_context(repo_root: Path, target: "ClientTarget | None" = None) -> str:
    """Build a thin client context file — instructions + repo identity + repo map only."""
    from ..config import mnemo_path
    from ..repo_map.identity import format_identity
    from ..memory import _recall_repo_map

    if target and target.key not in _MCP_CLIENTS:
        header = MNEMO_RULE_HEADER_CLI
    else:
        header = MNEMO_RULE_HEADER_MCP

    base = mnemo_path(repo_root)
    sections = [header]

    identity = format_identity(repo_root)
    if identity:
        sections.append(identity)

    repo_map = _recall_repo_map(base, 0)
    if repo_map:
        sections.append(repo_map)

    return "\n".join(s for s in sections if s)
