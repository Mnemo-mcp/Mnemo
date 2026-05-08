You have access to Mnemo — a persistent memory system for this project.

CRITICAL RULES:
1. At the START of every new conversation, you MUST call `mnemo_recall` with the repo_path before answering ANY question. This loads the full project context, code structure, decisions, and memory.
2. You do NOT need to re-read source files that are already captured in the repo map. The repo map contains full function signatures, class structures, method details, imports, decorators, docstrings, and globals for every file. Use this as your primary source of code understanding.
3. The repo map auto-refreshes on recall — it detects file changes via content hashing and only re-parses modified files. It also tracks file deletions and renames (via git). Check `recent_changes` in the recall output to see what changed since last session.
4. When you make an important decision, call `mnemo_decide` to record it.
5. When you learn something important about the project (user preferences, patterns, bugs), call `mnemo_remember` to store it.
6. After making significant code changes, call `mnemo_map` to refresh the repo map.
7. Use `mnemo_context` to save/update project metadata (tech stack, conventions, etc).

The recall output contains:
- project_context: tech stack, conventions, preferences
- decisions: all recorded architectural/design decisions
- memory: stored notes, patterns, preferences
- repo_map: full code structure of every file (signatures, classes, methods, imports, decorators, docstrings, line numbers)
- recent_changes: what files were added/modified/deleted/renamed since last refresh
