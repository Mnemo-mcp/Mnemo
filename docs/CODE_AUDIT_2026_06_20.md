# Mnemo Code Audit — Complete Findings

> Date: 2026-06-20
> Method: Full read of every .py file in mnemo/ (95 files, ~8,500 LOC)

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Total source files | 95 .py |
| Total LOC (approx) | ~8,500 |
| Critical bugs found | 7 |
| Security vulnerabilities | 4 (all Cypher injection) |
| Dead code instances | 12 |
| Duplicate/redundant code | 18 instances |
| Untested modules | 15 of 33 |
| AI slop score | 4/10 (mostly competent, some obvious patterns) |
| Duplicate MCP tools | 15 of 58 (26%) |

---

## Critical Bugs (Must Fix)

| # | File | Bug | Impact |
|---|------|-----|--------|
| 1 | `engine/freshness.py` | `_delete_file_nodes` queries `File {id: ...}` but File PK is `path` | Incremental graph updates silently fail — deleted files remain as ghost nodes |
| 2 | `tools/engine.py` | Registers `mnemo_impact` but `tools/team.py` also registers `mnemo_impact` — last import wins | Engine's sophisticated BFS impact tool is dead code; users get the naive version |
| 3 | `tools/meta.py` | Architecture intent routes to `get_handler("mnemo_ask")` — which IS this handler | Infinite recursion on architecture queries |
| 4 | `memory/store.py` | `forget_memory` doesn't remove from vector index | Forgotten memories remain searchable via semantic search |
| 5 | `repo_map/identity.py` | `save_identity` accesses `identity['patterns']` and `identity['conventions']` which are never set | KeyError crash when called |
| 6 | `hooks/__init__.py` | Shell injection in generated scripts — `$SUMMARY`, `$CMD`, `$USER_PROMPT` unescaped in double-quoted strings | Malicious or accidental content in tool output can execute arbitrary shell commands |
| 7 | `cli.py` | `contribute` command indentation bug — always prints "Edit it, then run:" even in auto mode | Confusing UX, editor opens unnecessarily |

---

## Security Vulnerabilities

| # | File | Issue | Fix |
|---|------|-------|-----|
| 1 | `tools/engine.py` | f-string Cypher: `f"WHERE b.name = '{name}'"` | Use Kuzu parameterized queries |
| 2 | `tools/code.py` | f-string Cypher: `f"WHERE c.name = '{symbol}'"` | Use Kuzu parameterized queries |
| 3 | `memory/search.py` | `lookup()` — user input interpolated into Cypher | Use Kuzu parameterized queries |
| 4 | `conventions/__init__.py` | `f"WHERE f.path CONTAINS '{file}'"` | Use Kuzu parameterized queries |

All are the same class: **Cypher injection via f-string interpolation of user input**. Fix once with a `query_safe(conn, cypher, params)` helper.

---

## Dead Code

| # | File | What | Evidence |
|---|------|------|----------|
| 1 | `hooks/__init__.py` | `_CLAUDE_SPAWN_SCRIPT`, `_CLAUDE_STOP_SCRIPT` | Defined but never referenced |
| 2 | `hooks/extractor.py` | Entire file (32 lines) | Never imported by hooks or anything else |
| 3 | `cli.py` | `filled_lines` loop in `contribute` | Computed but never used |
| 4 | `memory/retention.py` | `_next_id(entries + compressed)` call | Return value discarded |
| 5 | `memory/hierarchy.py` | `TIERS` tuple constant | Never referenced |
| 6 | `memory/linking.py` | `unlink_from_graph` function | Never called from memory package |
| 7 | `tools/engine.py` | `mnemo_impact` handler | Shadowed by team.py's version |
| 8 | `memory/indexing.py` | `MEMORY_NAMESPACE` redefinition | Already defined in `_shared.py` |
| 9 | `engine/clustering.py` | README claims "Leiden" | Code uses Louvain (documentation lie) |
| 10 | `sprint/__init__.py` | Entire module | Superseded by `plan/__init__.py` |
| 11 | `test_intel/__init__.py` | Entire module (C#-only) | Useless for 13/14 supported languages |
| 12 | `mcp_server.py` | Path traversal check (blocks only `/etc`, `/proc`) | Security theater — trivially bypassed |

---

## Duplicate / Redundant Code

### Duplicate MCP Tools (15 tools that are aliases)

| Alias Tool | Already handled by |
|---|---|
| `mnemo_add_review` | `mnemo_record type=review action=add` |
| `mnemo_reviews` | `mnemo_record type=review action=list` |
| `mnemo_add_error` | `mnemo_record type=error action=add` |
| `mnemo_search_errors` | `mnemo_record type=error action=search` |
| `mnemo_add_incident` | `mnemo_record type=incident action=add` |
| `mnemo_incidents` | `mnemo_record type=incident action=list` |
| `mnemo_add_correction` | `mnemo_record type=correction action=add` |
| `mnemo_corrections` | `mnemo_record type=correction action=list` |
| `mnemo_commit_message` | `mnemo_generate target=commit` |
| `mnemo_pr_description` | `mnemo_generate target=pr` |
| `mnemo_task` | `mnemo_plan action=task` |
| `mnemo_task_done` | `mnemo_plan action=task_done` |
| `mnemo_symbol` | `mnemo_lookup` (subset of functionality) |
| `mnemo_find` (engine.py) | `mnemo_graph action=find` |
| `mnemo_impact` (team.py) | `mnemo_impact` (engine.py) — CONFLICT |

### Duplicate Logic

| # | What | Where | Fix |
|---|------|-------|-----|
| 1 | `CATEGORY_WEIGHTS` dict | Defined TWICE in `memory/search.py` | Extract to `_shared.py` |
| 2 | `_recall_standard` / `_recall_deep` | `memory/search.py` | ~80% identical — merge with `detail_level` param |
| 3 | `_FILE_PATH_RE` regex | `memory/_shared.py` AND `memory/slots.py` | Use one from `_shared` |
| 4 | `_auto_categorize` pattern | `memory/store.py` AND `memory/search.py` (_infer_search_category) | Extract to `_shared.py` |
| 5 | `_traverse_callers` / `_traverse_callees` | `tools/engine.py` | 90% identical — one function with `direction` param |
| 6 | Import resolution | `engine/pipeline.py` AND `engine/scope.py` | Different implementations of same thing |
| 7 | "Find mnemo binary" | `doctor.py` AND `cli.py` (via clients) | Centralize |
| 8 | `_recall_counter` | THREE separate counters in `search.py` and `slots.py` | Consolidate |
| 9 | Cursor iteration pattern | Every graph query across 6+ files | Extract `query_all()` helper |
| 10 | Graph DB open guard | Every tool that uses graph | Extract decorator/context manager |

---

## AI Slop Patterns

| Pattern | Where | Fix |
|---------|-------|-----|
| Verbose docstring justifying why `utils/` exists | `utils/__init__.py` | Delete, replace with 1 line |
| "100% accuracy on test set" claim | `intent.py` | Remove unsubstantiated claim |
| `load_mnemoignore` 10-line docstring for 5-line function | `config.py` | Trim to 2 lines |
| 500+ lines of shell scripts as Python heredoc strings | `hooks/__init__.py` | Move to template files |
| `_KIRO_AGENT_CONFIG_TEMPLATE` 70-line JSON string | `hooks/__init__.py` | Dict → json.dumps, or template file |
| `_MNEMO_SKILL` 80-line markdown as Python string | `hooks/__init__.py` | Separate .md file |
| Comment blocks explaining what's about to happen | Various | Let code speak for itself |

---

## Architecture Issues

### 1. hooks/__init__.py (751 lines, 7+ responsibilities)

Should be split into:
```
hooks/
├── kiro.py          # Kiro agent config + hook scripts
├── claude.py        # Claude Code settings.json + hook config
├── git.py           # Pre-commit hook
├── scripts/         # Shell script templates as .sh files
│   ├── spawn.sh
│   ├── prompt-submit.sh
│   ├── pre-tool-use.sh
│   ├── post-tool-use.sh
│   └── stop.sh
└── discovery.py     # Binary path resolution
```

### 2. tools/team.py (346 lines, 16 tools, 4+ domains)

Should be split into:
```
tools/
├── records.py       # mnemo_record (errors, incidents, reviews, corrections)
├── code_intel.py    # mnemo_impact (BFS), mnemo_dependencies, mnemo_onboarding
├── team.py          # mnemo_team, mnemo_who_touched (git-based)
└── Remove aliases entirely from tool surface
```

### 3. memory/search.py (380 lines, 3 responsibilities)

Should be split into:
```
memory/
├── search.py        # search_memory() only
├── recall.py        # _recall_compact, _recall_standard, _recall_deep
└── lookup.py        # lookup() code intelligence query
```

### 4. Single-file packages (22 modules)

These are fine architecturally — a single `__init__.py` per module is perfectly valid Python. The real issue is that they're **untested**, not that they're single-file.

### 5. sprint/ vs plan/ duplication

`sprint/` should be deleted. `pr_gen/` should use `plan/` instead of `sprint/Collections.TASKS`.

---

## Proposed Clean Structure

```
mnemo/
├── __init__.py
├── cli.py                    # CLI commands
├── config.py                 # Constants, paths
├── init.py                   # mnemo init orchestration
├── mcp_server.py             # MCP JSON-RPC server
├── tool_registry.py          # @tool decorator + registry
├── doctor.py                 # Diagnostics
│
├── memory/                   # CORE: persistence + recall
│   ├── __init__.py           # Public API
│   ├── _shared.py            # Constants, helpers (NO sibling imports)
│   ├── store.py              # CRUD
│   ├── recall.py             # NEW: recall logic extracted from search.py
│   ├── search.py             # Search only (BM25 + vector + graph fusion)
│   ├── retention.py          # Scoring, compression, eviction
│   ├── linking.py            # Graph integration
│   ├── indexing.py           # Vector indexing (merge into store?)
│   ├── hierarchy.py          # Tiered storage
│   ├── services.py           # Side effects (plans, consolidation)
│   ├── slots.py              # Named memory slots
│   ├── lessons.py            # ✅ Clean
│   ├── temporal.py           # ✅ Clean
│   └── episodes.py           # ✅ Clean
│
├── engine/                   # CORE: code intelligence
│   ├── db.py                 # ✅ Clean
│   ├── schema.py             # Graph DDL
│   ├── pipeline.py           # Indexing DAG
│   ├── scope.py              # Cross-file call resolution
│   ├── clustering.py         # Community detection
│   ├── freshness.py          # Incremental updates (BUGFIX NEEDED)
│   ├── memory_graph.py       # Memory↔code linking
│   ├── workers.py            # ✅ Clean
│   ├── cache.py              # ✅ Clean
│   ├── layout.py             # Graph visualization layout
│   └── java_enrich.py        # Java AST enrichment
│
├── embeddings/               # Vector search
│   ├── __init__.py           # BM25 sparse
│   └── dense.py              # ONNX MiniLM dense
│
├── repo_map/                 # Tree-sitter parsing
│   ├── scanner.py            # File discovery
│   ├── parsers.py            # 14-language AST extraction
│   └── identity.py           # Repo identity (BUGFIX NEEDED)
│
├── hooks/                    # RESTRUCTURE NEEDED
│   ├── kiro.py               # Kiro-specific generation
│   ├── claude.py             # Claude Code generation
│   ├── git.py                # Pre-commit hook
│   ├── discovery.py          # Binary path resolution
│   └── scripts/              # Shell templates as actual .sh files
│
├── tools/                    # MCP tool handlers (CONSOLIDATE)
│   ├── memory.py             # recall, remember, forget, search, decide, slots, lessons
│   ├── code_intel.py         # lookup, graph, impact, map, communities (MERGE engine+code+graph)
│   ├── records.py            # record (errors, incidents, reviews, corrections)
│   ├── safety.py             # audit, security, breaking, regressions, conventions, drift, health, dead_code
│   ├── search.py             # unified search, knowledge, API discovery, cross-repo
│   ├── plan.py               # plan, task tracking
│   ├── git.py                # generate (commit/PR), hooks, snapshot, velocity
│   ├── capture.py            # auto_capture (hook-only)
│   └── meta.py               # ask (NL routing)
│
├── plan/                     # ✅ Keep (592 lines, well-built)
├── workspace/                # ✅ Keep (multi-repo)
├── health/                   # ✅ Keep
├── security/                 # ✅ Keep
├── dead_code/                # ✅ Keep
├── conventions/              # ✅ Keep
├── drift/                    # ✅ Keep
├── breaking/                 # ✅ Keep
├── corrections/              # ✅ Keep
├── errors/                   # ✅ Keep
├── incidents/                # ✅ Keep
├── knowledge/                # ✅ Keep
├── commit_gen/               # ✅ Keep
├── pr_gen/                   # ✅ Keep (update to use plan/ not sprint/)
├── team_graph/               # ⚠️ Keep with caching
├── velocity/                 # ⚠️ Keep
├── prompts/                  # ✅ Keep
├── api_discovery/            # ⚠️ Keep, extend beyond C#
├── onboarding/               # ⚠️ Low priority
│
├── REMOVE:
│   ├── sprint/               # Duplicate of plan/
│   ├── test_intel/           # C#-only, useless
│   ├── hooks/extractor.py    # Dead code
│   ├── persistence/          # Empty package
│   └── analyzers/            # Unclear purpose, low value
│
└── utils/                    # Shared utilities
    ├── __init__.py           # Barrel (trim docstring)
    ├── privacy.py
    ├── dedup.py
    ├── circuit_breaker.py
    ├── observations.py
    └── query.py              # NEW: safe Cypher query helper
```

---

## Priority Actions

### Immediate (before any new features):

1. **Fix Cypher injection** — create `utils/query.py` with `execute_safe(conn, cypher, params)`, update all graph queries
2. **Fix `mnemo_impact` shadow** — rename team.py's version or merge into engine.py's
3. **Fix `freshness.py` File PK bug** — change `{id: ...}` to `{path: ...}`
4. **Fix shell injection in hooks** — pipe content via stdin, not interpolation
5. **Fix `identity.py` KeyError** — either implement the missing fields or remove the broken functions
6. **Fix `forget_memory` vector index cleanup** — add `remove_from_vector_index(entry_id)`
7. **Delete dead code** — all 12 items listed above

### Short-term (during Tier 0-1 work):

8. **Split hooks/__init__.py** into 4 files
9. **Extract `memory/recall.py`** from search.py
10. **Consolidate tools/** — merge engine+code+graph into `code_intel.py`
11. **Remove 15 alias tools** — keep only the primary tool names
12. **Delete sprint/** — update pr_gen to use plan/
13. **Parameterize all Cypher queries**

### Medium-term:

14. **Test all untested modules** (15 modules)
15. **Add integration test** for full lifecycle (init → hook → capture → recall)
16. **Fix BM25 IDF persistence** — `save_state`/`load_state` must be called
17. **Fix MAX_FILE_SIZE inconsistency** (100K vs 200K)
