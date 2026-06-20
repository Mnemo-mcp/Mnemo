# Mnemo Restructuring Strategy

> Date: 2026-06-20
> Principle: Every change must leave tests green. Restructure in small, atomic commits.

---

## Current State

```
mnemo/                         # 95 .py files, ~8,500 LOC
├── __init__.py                # 5 LOC — package marker
├── cli.py                     # 370 LOC — Click CLI (has bugs)
├── config.py                  # 85 LOC — paths, constants
├── init.py                    # 160 LOC — orchestrates mnemo init
├── mcp_server.py              # 145 LOC — MCP stdio server
├── tool_registry.py           # 95 LOC — @tool decorator + registry
├── doctor.py                  # 130 LOC — diagnostics
├── intent.py                  # 120 LOC — decision classifier
├── serve.py                   # 609 LOC — dashboard HTTP server
├── storage.py                 # 235 LOC — StorageAdapter + JSONFileAdapter
├── clients.py                 # 210 LOC — client config generation (amazonq, cursor, copilot)
├── enrichment.py              # 204 LOC — Roslyn C# enrichment
├── retrieval.py               # 101 LOC — vector retrieval utilities
├── chunking.py                # 36 LOC — text chunker
├── types.py                   # 55 LOC — shared type definitions
├── watcher.py                 # 95 LOC — session file watcher (prototype)
│
├── memory/          # 12 files, ~1,300 LOC — the memory system
├── engine/          # 12 files, ~1,900 LOC — graph intelligence
├── tools/           # 13 files, ~1,400 LOC — MCP tool handlers
├── hooks/           # 2 files, 780 LOC — hook generation (god file)
├── utils/           # 9 files, ~350 LOC — shared utilities
├── embeddings/      # 2 files, 200 LOC — BM25 + ONNX vector
├── repo_map/        # 4 files, 600 LOC — tree-sitter parsing
├── plan/            # 1 file, 592 LOC — task planning
├── workspace/       # 1 file, 244 LOC — multi-repo
│
├── 20 domain modules (single __init__.py each):
│   health, security, conventions, drift, dead_code, breaking,
│   corrections, errors, incidents, code_review, knowledge,
│   commit_gen, pr_gen, api_discovery, onboarding, team_graph,
│   velocity, test_intel, sprint, regressions
│
├── DEAD/REDUNDANT:
│   sprint/          # Duplicate of plan/
│   test_intel/      # C#-only, useless for 13/14 languages
│   persistence/     # Empty __init__.py + 2 orphan files
│   analyzers/       # Unclear purpose
│   hooks/extractor.py  # Never imported
│   ui_static/       # Single HTML file (belongs in serve.py or templates/)
│   rules/           # Single markdown file
│   code_review/     # 74 LOC, zero tests, overlaps with mnemo_record
```

---

## Target State

```
mnemo/
├── __init__.py                # Package + version
├── cli.py                     # CLI commands (cleaned)
├── config.py                  # Paths, constants, ignore logic
├── init.py                    # mnemo init orchestration
├── server.py                  # MCP JSON-RPC server (renamed from mcp_server.py)
├── tool_registry.py           # @tool decorator + registry
├── doctor.py                  # Diagnostics (auto-fix removed)
├── types.py                   # Shared types/protocols
│
├── memory/                    # Core memory system
│   ├── __init__.py            # Public API
│   ├── constants.py           # Shared constants (renamed from _shared.py)
│   ├── store.py               # CRUD operations
│   ├── recall.py              # Recall orchestration (NEW — extracted from search.py)
│   ├── search.py              # Search only (BM25 + vector + graph RRF)
│   ├── retention.py           # Scoring, decay, eviction, contradiction
│   ├── indexing.py            # Vector index management
│   ├── linking.py             # Memory ↔ graph integration
│   ├── hierarchy.py           # Tier management
│   ├── services.py            # Side effects orchestration
│   ├── slots.py               # Named memory slots
│   ├── lessons.py             # Learned patterns
│   ├── temporal.py            # File change tracking
│   └── episodes.py            # Session episodes
│
├── engine/                    # Code intelligence (graph)
│   ├── __init__.py
│   ├── db.py                  # Database open/close/reset
│   ├── query.py               # NEW: safe parameterized query helper
│   ├── schema.py              # Graph DDL
│   ├── pipeline.py            # Indexing DAG (scan → parse → load → scope → cluster → vectors)
│   ├── scope.py               # Cross-file call resolution
│   ├── clustering.py          # Community detection (fix: rename to louvain, not leiden)
│   ├── freshness.py           # Incremental updates (BUGFIX: File PK)
│   ├── memory_graph.py        # Memory nodes in graph + Dijkstra search
│   ├── workers.py             # Parallel tree-sitter workers
│   ├── cache.py               # Content-addressed parse cache
│   ├── layout.py              # Force-directed visualization layout
│   └── java_enrich.py         # Java-specific AST enrichment
│
├── embeddings/                # Search infrastructure
│   ├── __init__.py            # BM25 sparse embeddings
│   └── dense.py               # ONNX MiniLM-L6-v2
│
├── repo_map/                  # Source parsing
│   ├── __init__.py
│   ├── scanner.py             # File discovery + hashing
│   ├── parsers.py             # 14-language tree-sitter extraction
│   └── identity.py            # Repo identity detection (BUGFIX: missing keys)
│
├── hooks/                     # RESTRUCTURED from 751-line god file
│   ├── __init__.py            # Public API: install_hooks(client, root)
│   ├── kiro.py                # Kiro agent config + hooks generation
│   ├── claude.py              # Claude Code settings.json hooks
│   ├── git.py                 # Pre-commit hook
│   ├── discovery.py           # Binary path resolution
│   └── templates/             # Shell scripts as actual .sh files
│       ├── spawn.sh
│       ├── prompt_submit.sh
│       ├── pre_tool_use.sh
│       ├── post_tool_use.sh
│       └── stop.sh
│
├── tools/                     # MCP tool handlers (CONSOLIDATED)
│   ├── __init__.py            # Auto-imports all handlers
│   ├── memory.py              # recall, remember, forget, search_memory, decide, context, slots, lessons
│   ├── code_intel.py          # NEW: merged engine.py + code.py + graph.py
│   ├── records.py             # NEW: record (unified errors/incidents/reviews/corrections)
│   ├── safety.py              # audit, security, breaking, regressions, conventions, drift, health, dead_code
│   ├── search.py              # unified search, knowledge, API discovery, cross-repo
│   ├── plan.py                # plan management
│   ├── git.py                 # generate (commit/PR), snapshot, velocity
│   ├── capture.py             # auto_capture (hook-only)
│   └── meta.py                # ask (NL routing) — fix recursive bug
│
├── plan/                      # Task planning engine
│   └── __init__.py            # 592 LOC — well-built, keep as-is
│
├── workspace/                 # Multi-repo workspace
│   └── __init__.py
│
├── records/                   # NEW: unified engineering records
│   ├── __init__.py            # errors, incidents, reviews, corrections in one module
│   └── corrections.py         # Correction-specific logic (confidence decay)
│
├── quality/                   # NEW: grouped code quality modules
│   ├── __init__.py
│   ├── security.py            # Secret/injection scanning
│   ├── conventions.py         # Naming convention checks
│   ├── drift.py               # Architecture drift detection
│   ├── health.py              # System/code health scoring
│   ├── dead_code.py           # Unreferenced symbol detection
│   └── breaking.py            # Breaking change detection
│
├── git/                       # NEW: git-related features
│   ├── __init__.py
│   ├── commit_gen.py          # Commit message generation
│   ├── pr_gen.py              # PR description generation
│   ├── team.py                # Team expertise from git history
│   └── velocity.py            # Velocity metrics
│
├── knowledge/                 # Knowledge base
│   └── __init__.py
│
├── api_discovery/             # API endpoint detection
│   └── __init__.py
│
├── intent.py                  # Decision classifier
├── clients.py                 # Client config generators (amazonq, cursor, copilot, etc.)
├── enrichment.py              # Roslyn C# enrichment
├── retrieval.py               # Vector retrieval utilities
├── serve.py                   # Dashboard HTTP server
├── watcher.py                 # Session file watcher
│
└── utils/                     # Shared utilities
    ├── __init__.py            # Clean 1-line docstring
    ├── privacy.py             # Secret stripping
    ├── stemmer.py             # Word stemming
    ├── dedup.py               # Deduplication
    ├── circuit_breaker.py     # Circuit breaker pattern
    ├── logger.py              # Logging setup
    ├── observations.py        # Observation tracking
    ├── synonyms.py            # Synonym expansion
    ├── audit.py               # Audit trail
    └── metrics.py             # Performance metrics
```

---

## What Changes (Summary)

| Action | Details |
|--------|---------|
| **DELETE** | `sprint/`, `test_intel/`, `persistence/`, `analyzers/`, `hooks/extractor.py`, `code_review/`, `ui_static/`, `rules/`, `chunking.py` |
| **SPLIT** | `hooks/__init__.py` → 4 files + templates/ dir |
| **MERGE** | `tools/engine.py` + `tools/code.py` + `tools/graph.py` → `tools/code_intel.py` |
| **MERGE** | `tools/team.py` records portion → `tools/records.py` |
| **EXTRACT** | `memory/search.py` recall logic → `memory/recall.py` |
| **CREATE** | `engine/query.py` — safe parameterized Cypher helper |
| **GROUP** | 6 quality modules → `quality/` subpackage |
| **GROUP** | 4 git modules → `git/` subpackage |
| **GROUP** | errors + incidents + corrections + code_review → `records/` |
| **RENAME** | `memory/_shared.py` → `memory/constants.py` |
| **RENAME** | `mcp_server.py` → `server.py` |
| **REMOVE** | 15 duplicate MCP tool aliases |

---

## Execution Plan — 8 Phases

### Phase 0: Preparation (no code changes yet)

**Purpose**: Establish a safety net before touching anything.

1. Create branch `restructure/cleanup`
2. Run full test suite, confirm 226 pass
3. Record test output as baseline
4. Create `.restructure_progress.md` to track what's been done

**Rule**: After EVERY phase, run full tests. If anything breaks, fix before proceeding.

---

### Phase 1: Delete Dead Code

**Purpose**: Remove weight. Less code = less confusion.

**Actions:**
```
DELETE mnemo/sprint/                    # Duplicate of plan/
DELETE mnemo/test_intel/                # C#-only stub, useless
DELETE mnemo/persistence/__init__.py    # Empty file
DELETE mnemo/analyzers/                 # Unclear purpose, no consumers
DELETE mnemo/hooks/extractor.py         # Never imported
DELETE mnemo/code_review/              # Overlaps with mnemo_record, zero tests
DELETE mnemo/ui_static/                 # Move index.html into serve.py or templates/
DELETE mnemo/rules/                     # Single markdown file, can go in prompts/
DELETE mnemo/chunking.py               # 36 LOC, only used in 1 place — inline it
```

**Also remove from within files:**
- `cli.py`: dead `filled_lines` loop in `contribute`
- `hooks/__init__.py`: unused `_CLAUDE_SPAWN_SCRIPT`, `_CLAUDE_STOP_SCRIPT`
- `memory/retention.py`: discarded `_next_id()` call
- `memory/hierarchy.py`: unused `TIERS` tuple
- `memory/linking.py`: unused `unlink_from_graph`
- `memory/indexing.py`: duplicate `MEMORY_NAMESPACE`
- `mcp_server.py`: fake path traversal check (security theater)

**Update imports**: Any file importing from deleted modules must be updated.
- `pr_gen/__init__.py` imports from `sprint` → change to import from `plan/`
- `tools/__init__.py` may import deleted modules → update

**Tests to update**: Remove tests for deleted modules (if any exist).

**Expected result**: ~500 LOC removed, zero new functionality, all remaining tests still pass.

---

### Phase 2: Fix Critical Bugs

**Purpose**: Fix the 7 critical bugs and 4 security vulnerabilities. No restructuring yet — just correctness.

**Bug fixes:**

| # | Fix | File | Change |
|---|-----|------|--------|
| 1 | Freshness File PK | `engine/freshness.py` | Change `{id: '{fp}'}` → `{path: '{fp}'}` |
| 2 | Impact tool shadow | `tools/team.py` | Rename to `mnemo_impact_imports` or remove; keep engine.py's BFS version |
| 3 | Meta recursive loop | `tools/meta.py` | Architecture intent → call `mnemo_lookup` not `mnemo_ask` |
| 4 | Forget vector cleanup | `memory/store.py` | Add vector index removal in `forget_memory` |
| 5 | Identity KeyError | `repo_map/identity.py` | Add missing fields to `generate_identity` or guard in `save_identity` |
| 6 | Shell injection | `hooks/__init__.py` | Escape variables or pipe via stdin in generated scripts |
| 7 | CLI indentation | `cli.py` | Fix `contribute` else-block indentation |

**Security fixes:**

Create `engine/query.py`:
```python
"""Safe parameterized Cypher query execution."""

def execute(conn, cypher: str, params: dict | None = None) -> list[tuple]:
    """Execute Cypher with parameters, return all rows."""
    result = conn.execute(cypher, params or {})
    rows = []
    while result.has_next():
        rows.append(result.get_next())
    return rows
```

Then update ALL f-string Cypher queries across:
- `tools/engine.py` (5+ queries)
- `tools/code.py` (3+ queries)
- `tools/graph.py` (2+ queries)
- `memory/search.py` lookup() (2 queries)
- `conventions/__init__.py` (2 queries)
- `engine/memory_graph.py` (10+ queries)
- `engine/freshness.py` (3+ queries)

**Pattern**: Change `f"WHERE n.name = '{name}'"` → `"WHERE n.name = $name"` with `params={"name": name}`

**Expected result**: All bugs fixed, all queries parameterized, tests still pass.

---

### Phase 3: Split hooks/__init__.py

**Purpose**: Break the 751-line god file into maintainable pieces.

**New structure:**
```
hooks/
├── __init__.py          # Public API: install_hooks(client, root), install_git_hook(root)
├── kiro.py              # _install_kiro_hooks() logic + agent config template
├── claude.py            # _install_claude_hooks() logic
├── git.py               # Pre-commit hook + run_check()
├── discovery.py         # find_mnemo_mcp_command(), binary path resolution
└── templates/
    ├── spawn.sh         # Agent spawn hook script
    ├── prompt_submit.sh # User prompt submit hook script
    ├── pre_tool_use.sh  # Pre-tool-use security hook script
    ├── post_tool_use.sh # Post-tool-use tracking hook script
    └── stop.sh          # Session end learning capture hook script
```

**How templates work:**
- Shell scripts stored as actual `.sh` files (can be linted, tested independently)
- Variables like `{{MNEMO_PATH}}` replaced at install time with `str.replace()`
- Shell-unsafe user content (prompts, tool output) piped via stdin, not interpolated

**Migration steps:**
1. Create `hooks/discovery.py` — move `find_mnemo_mcp_command()` there
2. Create `hooks/templates/` with the 5 shell scripts extracted from string literals
3. Create `hooks/kiro.py` — move Kiro agent config + skill generation
4. Create `hooks/claude.py` — move Claude Code settings logic
5. Create `hooks/git.py` — move pre-commit hook + `run_check`
6. Update `hooks/__init__.py` to be a thin dispatcher that imports from submodules
7. Verify: `mnemo init --client kiro` still produces correct output

**Expected result**: Same functionality, 751 LOC → 5 focused files + 5 shell templates.

---

### Phase 4: Consolidate tools/

**Purpose**: Eliminate duplicate tools, merge related files, fix organization.

**Step 4a: Remove 15 alias tools**

These tools add zero value — they're just shortcuts for existing parameterized tools:

```python
# REMOVE these registrations (the handlers stay in mnemo_record/mnemo_generate/mnemo_plan):
mnemo_add_review      →  use mnemo_record type=review action=add
mnemo_reviews         →  use mnemo_record type=review action=list
mnemo_add_error       →  use mnemo_record type=error action=add
mnemo_search_errors   →  use mnemo_record type=error action=search
mnemo_add_incident    →  use mnemo_record type=incident action=add
mnemo_incidents       →  use mnemo_record type=incident action=list
mnemo_add_correction  →  use mnemo_record type=correction action=add
mnemo_corrections     →  use mnemo_record type=correction action=list
mnemo_commit_message  →  use mnemo_generate target=commit
mnemo_pr_description  →  use mnemo_generate target=pr
mnemo_task            →  use mnemo_plan action=task
mnemo_task_done       →  use mnemo_plan action=task_done
mnemo_symbol          →  use mnemo_lookup (superset)
mnemo_find            →  use mnemo_graph action=find
```

Keep `mnemo_impact` from engine.py (BFS), remove team.py's naive version.

After removal: **58 → 43 tools** (15 core agent-facing + 28 specialized).

**Step 4b: Merge tools/engine.py + tools/code.py + tools/graph.py → tools/code_intel.py**

All three do code intelligence via graph queries. Merged file exposes:
- `mnemo_lookup` — 360° symbol/service/folder details
- `mnemo_graph` — stats, neighbors, find
- `mnemo_impact` — BFS blast radius (from engine.py's version)
- `mnemo_query` — raw Cypher
- `mnemo_communities` — cluster listing
- `mnemo_map` — repo tree regeneration

**Step 4c: Slim down tools/team.py → tools/records.py**

Move `mnemo_record` (the unified handler) + its sub-handlers to `tools/records.py`.
Move `mnemo_team`, `mnemo_who_touched` to `tools/git.py`.
Move `mnemo_dependencies`, `mnemo_onboarding`, `mnemo_tests` to `tools/code_intel.py`.

**Step 4d: Delete tools/observe.py (53 LOC)**

Move `mnemo_ask` into `tools/meta.py` (where the logic already lives).
Move `mnemo_episode` into `tools/memory.py`.
Move `mnemo_temporal` into `tools/memory.py`.

**Final tools/ structure:**
```
tools/
├── __init__.py        # Wire-up
├── memory.py          # recall, remember, forget, search_memory, decide, context, slots, lessons, episode, temporal
├── code_intel.py      # lookup, graph, impact, query, communities, map, dependencies, onboarding, tests
├── records.py         # record (unified for errors, incidents, reviews, corrections)
├── safety.py          # audit + all quality sub-tools
├── search.py          # search (unified), knowledge, API, cross-repo
├── plan.py            # plan management
├── git.py             # generate, snapshot, velocity, team, who_touched
├── capture.py         # auto_capture (hook-only)
└── meta.py            # ask (NL routing)
```

**Expected result**: 13 files → 10 files, 15 fewer tools, no overlapping functionality.

---

### Phase 5: Group Domain Modules

**Purpose**: Reduce top-level module count from 20+ to organized subpackages.

**Step 5a: Create `quality/` subpackage**

```
quality/
├── __init__.py        # Re-exports: check_security, check_conventions, etc.
├── security.py        # ← from security/__init__.py
├── conventions.py     # ← from conventions/__init__.py
├── drift.py           # ← from drift/__init__.py
├── health.py          # ← from health/__init__.py
├── dead_code.py       # ← from dead_code/__init__.py
└── breaking.py        # ← from breaking/__init__.py
```

These 6 modules share a common pattern (scan code/graph, report issues) and are all consumed by the same tool (`mnemo_audit`).

**Step 5b: Create `records/` subpackage**

```
records/
├── __init__.py        # Unified add/search/list for all record types
├── corrections.py     # ← from corrections/__init__.py (has special confidence decay logic)
└── (errors, incidents, reviews are simple enough to inline in __init__)
```

Merge `errors/`, `incidents/`, `code_review/` logic into `records/__init__.py`. They all follow the same pattern: load JSON list, append, save, search by keyword.

**Step 5c: Create `git/` subpackage**

```
git/
├── __init__.py        # Re-exports
├── commit_gen.py      # ← from commit_gen/__init__.py
├── pr_gen.py          # ← from pr_gen/__init__.py
├── team.py            # ← from team_graph/__init__.py
└── velocity.py        # ← from velocity/__init__.py
```

**Step 5d: Absorb remaining tiny modules**

- `regressions/__init__.py` (83 LOC) → merge into `quality/` as `quality/regressions.py`
- `onboarding/__init__.py` (84 LOC) → keep standalone (low priority, clear purpose)
- `api_discovery/__init__.py` (143 LOC) → keep standalone (clear purpose)
- `knowledge/__init__.py` (118 LOC) → keep standalone (clear purpose)

**Expected result**: Top-level package list goes from 33 directories to 15.

---

### Phase 6: Clean memory/ Internals

**Purpose**: Fix architectural issues within the most critical module.

**Step 6a: Extract `memory/recall.py` from `memory/search.py`**

`search.py` currently does 3 things:
1. `search_memory()` — hybrid search with RRF
2. `lookup()` — code intelligence query via graph
3. `_recall_compact/standard/deep` — context generation for session start

Extract (3) into `recall.py`. Move `lookup()` logic to use `engine/query.py` helper.

**Step 6b: Fix `_shared.py` importing from siblings**

Currently `_shared.py` imports `_memory_to_chunk` from `indexing.py` and `_graph_link_entry` from `linking.py`. This is backwards.

Fix: Move those re-exports to `__init__.py` (the barrel file) instead. `_shared.py` becomes a true leaf with zero sibling imports.

**Step 6c: Deduplicate**

- `CATEGORY_WEIGHTS` → define once in `constants.py`, import everywhere
- `_FILE_PATH_RE` → define once in `constants.py`
- `_recall_standard` + `_recall_deep` → one function with `tier` parameter
- Three `_recall_counter` → one counter in `recall.py`

**Step 6d: Fix `sys.modules` hack in `store.py`**

Replace:
```python
sys.modules[__name__.rsplit(".", 1)[0]]._get_current_branch(repo_root)
```
With:
```python
from .constants import get_current_branch
```

**Expected result**: Cleaner dependency graph within memory/, no circular imports, deduplicated constants.

---

### Phase 7: Cleanup & Polish

**Purpose**: Final quality pass.

**7a: Fix config.py inconsistency**
- Make `should_ignore()` use `ignore_dirs_for(repo_root)` instead of just `IGNORE_DIRS`
- Unify MAX_FILE_SIZE (pick one: 100KB or 200KB, not both)

**7b: Fix embeddings IDF persistence**
- Ensure `save_state()`/`load_state()` are called during pipeline and at MCP server shutdown
- Without this, BM25 has no IDF weighting (all terms equally weighted)

**7c: Fix doctor.py**
- `graph.lbug` is a directory — use `sum(f.stat().st_size for f in path.rglob('*'))` for size
- Separate auto-fix into explicit `mnemo fix` command
- Unify "find mnemo binary" with `hooks/discovery.py`

**7d: Clean AI slop**
- Delete verbose `utils/__init__.py` docstring
- Remove "100% accuracy" claim from `intent.py`
- Trim `load_mnemoignore` docstring to 2 lines

**7e: Fix clustering documentation**
- Code uses Louvain → update README/docs to say "Louvain" not "Leiden"
- Or switch to Leiden if networkx supports it (it does via `community_louvain` alternative)

**Expected result**: No more known bugs, no AI slop, documentation matches code.

---

### Phase 8: Add Missing Tests

**Purpose**: Ensure restructured code is verified.

Priority order:
1. `hooks/` — test each generated script produces correct output
2. `memory/recall.py` — test that recall returns correct context for various scenarios
3. `memory/store.py` — test forget removes from vector index
4. `engine/query.py` — test parameterized queries are safe
5. `engine/freshness.py` — test incremental update deletes correct nodes
6. `tools/code_intel.py` — test merged tool still handles all action types
7. `quality/` modules — 1 test each proving they return valid output
8. `git/` modules — 1 test each with mock git repo
9. `workspace/` — test link + cross-search with temp repos
10. Integration: `mnemo init` → store memory → forget → recall → verify

**Expected result**: Coverage of all critical paths. No module ships without at least 1 test proving it works.

---

## Module Dependency Graph (Target)

```
                    cli.py
                      │
          ┌───────────┼───────────┐
          │           │           │
        init.py    doctor.py   serve.py
          │           │
          ▼           ▼
    ┌─────────────────────────────┐
    │         server.py           │ ← MCP entry point
    │      tool_registry.py       │
    └──────────┬──────────────────┘
               │
               ▼
    ┌─────────────────────────────┐
    │         tools/              │ ← Thin handlers only
    │  (memory, code_intel,       │
    │   records, safety, search,  │
    │   plan, git, capture, meta) │
    └──────────┬──────────────────┘
               │ delegates to
               ▼
    ┌─────────────────────────────────────────┐
    │              SERVICE LAYER               │
    │                                         │
    │  memory/     engine/     quality/       │
    │  plan/       workspace/  records/       │
    │  knowledge/  git/        api_discovery/ │
    └──────────────────┬──────────────────────┘
                       │ uses
                       ▼
    ┌─────────────────────────────────────────┐
    │           INFRASTRUCTURE                 │
    │                                         │
    │  embeddings/   repo_map/   utils/       │
    │  config.py     types.py    storage.py   │
    │  engine/db.py  engine/query.py          │
    └─────────────────────────────────────────┘
```

**Rules:**
1. `tools/` NEVER contains business logic — only validation + delegation
2. Service modules NEVER import from `tools/`
3. Infrastructure modules NEVER import from services or tools
4. All Cypher goes through `engine/query.py`
5. All file I/O for .mnemo/ JSON goes through `storage.py`

---

## Migration Safety Rules

1. **One phase per commit**. Each phase is a single atomic commit that keeps tests green.
2. **Run tests after every file move/delete**. `python3.12 -m pytest -q` must show 226 pass (minus tests for deleted modules).
3. **Update imports immediately**. When you move a module, grep for all imports of the old path and update them in the same commit.
4. **Preserve public API**. External consumers (hooks, CLI, MCP) must not see any change in behavior.
5. **No behavior changes during restructuring**. Bug fixes in Phase 2 are separate from moves in Phases 3-6.
6. **Git history matters**. Use `git mv` for renames so git tracks the file history.

---

## Metrics — Before vs After

| Metric | Before | After |
|--------|--------|-------|
| Top-level directories | 33 | 15 |
| Total .py files | 95 | ~75 |
| Total LOC | ~8,500 | ~7,500 (remove ~1000 dead/duplicate) |
| MCP tools | 58 | 43 |
| Untested modules | 15 | 0 (target) |
| Known bugs | 7 critical | 0 |
| Security vulns | 4 | 0 |
| Longest file | 751 (hooks/__init__) | ~300 |
| Duplicate code instances | 18 | 0 |
| Files with zero consumers | 6 | 0 |

---

## Timeline Estimate

| Phase | Effort | Dependencies |
|-------|--------|-------------|
| Phase 0: Preparation | 10 min | None |
| Phase 1: Delete dead code | 30 min | Phase 0 |
| Phase 2: Fix critical bugs | 2-3 hours | Phase 1 |
| Phase 3: Split hooks/ | 1-2 hours | Phase 2 |
| Phase 4: Consolidate tools/ | 1-2 hours | Phase 2 |
| Phase 5: Group domain modules | 1 hour | Phase 4 |
| Phase 6: Clean memory/ | 1-2 hours | Phase 2 |
| Phase 7: Cleanup & polish | 1 hour | All above |
| Phase 8: Add tests | 3-4 hours | All above |

**Total: ~12-16 hours of careful, test-verified work.**

Phases 3, 4, 5, 6 can be done in parallel (they touch different files). Phases 1 and 2 are prerequisites for everything else.
