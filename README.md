# Mnemo

Persistent engineering cognition for AI coding agents.

One command gives Amazon Q, Cursor, Claude Code, Kiro, and other MCP clients accumulated engineering understanding across chat sessions -- architecture intelligence, historical decisions, proactive guidance, and institutional memory.

---

## What Mnemo Does (Plain Words)

- Remembers decisions, fixes, and patterns across chat sessions so you never repeat context.
- Builds a knowledge graph of your codebase (classes, services, relationships, ownership).
- Searches code by meaning using hybrid retrieval (BM25 + vector + graph).
- Tracks plans automatically and updates progress as work happens.
- Surfaces warnings, next steps, and related decisions in every response.
- Works across multiple repos so the agent understands your full platform.
- Filters secrets and PII before storing anything to disk.

## What Mnemo Is (Technical)

Mnemo is a local-first MCP server (`mnemo-mcp`) plus repo-side data and indexing. It exposes 56 MCP tools over JSON-RPC (stdin/stdout) and an optional REST API on port 7891. It builds a knowledge graph with NetworkX, performs hybrid search with BM25 + ChromaDB vector + graph-boosted RRF fusion, manages memory with retention scoring and auto-eviction, and enriches every tool response with proactive context. Zero external databases required -- all state lives in `.mnemo/` as JSON files.

## Key Stats

| Metric | Value |
|--------|-------|
| MCP Tools | 56 |
| Supported Languages | 14 |
| Test Suite | 128 tests |
| Typical Graph Size | 880+ nodes, 1400+ edges |
| External DBs Required | 0 |

---

## What It Does

### Knowledge Graph

NetworkX-based graph capturing services, classes, interfaces, methods, files, packages, people, decisions, and incidents. Supports 14 languages via tree-sitter. Structural relationships include implements, inherits, calls, depends_on, owns, contains, defines, and references. Queryable for neighbors, paths, hubs, traversals, and impact analysis.

### Persistent Memory

Tiered retrieval system with retention scoring. Memories are categorized (decision, pattern, preference, fix, context), scored by access frequency and recency, and auto-evicted when stale. Branch-aware storage prevents cross-branch context bleed.

### Hybrid Search

Triple-stream retrieval combining BM25 (with stemming and synonym expansion), vector similarity (ChromaDB + all-MiniLM-L6-v2), and graph-boosted results. Streams are fused via Reciprocal Rank Fusion (RRF). Falls back to keyword matching if ChromaDB is unavailable.

### Plan Mode

Auto-creates trackable plans from memories and decisions. Supports task dependencies, frontier scoring (next actionable task), draft plans, routine templates, and auto-completion when the agent reports matching work done. Plans sync to TASKS.md automatically.

### Response Enrichment

Every tool response is enriched with proactive context: next plan task, regression warnings, related decisions, and relevant memories. The agent never needs to call extra tools to stay informed.

### Memory Lifecycle

Retention formula based on access count, recency, and category weight. Auto-eviction removes low-scoring memories. Contradiction detection flags conflicting information. Consolidation merges related memories. Lessons system extracts reusable patterns from completed work.

### Privacy Filtering

16 secret patterns (API keys, tokens, passwords, connection strings, private keys, etc.) are auto-stripped before any content is written to disk.

### Memory Slots

Named bounded regions for structured context. Slots provide fixed-size containers for specific types of information (active task, current branch, session goals) that overwrite rather than accumulate.

### Lifecycle Hooks

Passive capture for Kiro and Claude Code. Hooks observe agent activity and auto-remember significant findings without explicit tool calls.

### Observation Capture

Records every tool call for pattern mining. Enables frequency analysis, workflow detection, and usage-based recommendations.

### Crystallization

Auto-summarizes completed tasks into concise memory entries. Reduces memory bloat while preserving key learnings.

### Multi-Repo Workspace

Federated graph queries across linked repositories. Cross-repo impact analysis, semantic search, and API discovery span all linked repos transparently.

### Code Intelligence

Architecture detection, dead code analysis, convention checking, security scanning, breaking change detection, drift analysis, and code health reports.

### REST API

HTTP endpoints on port 7891 for external integrations. Exposes memory, graph, search, and plan operations over HTTP.

### Dashboard UI

Web dashboard on port 7890 with interactive knowledge graph visualization, memory heatmap, code health metrics, and command palette. Dark theme, zero dependencies beyond CDN assets.

### Git Snapshots

State time-travel via git-based snapshots of `.mnemo/` data. Restore previous states of memory, graph, and plans.

### Obsidian Export

Export memories and decisions as markdown files with YAML frontmatter, compatible with Obsidian and other knowledge management tools.

---

## Installation

### Option A: VS Code Extension

Install the **Mnemo** extension from the VS Code Marketplace. Open a project, click "Initialize Mnemo" when prompted. The extension handles binary download, initialization, and MCP configuration.

### Option B: Homebrew (macOS/Linux)

```bash
brew tap Mnemo-mcp/tap
brew install mnemo
cd your-project && mnemo init
```

### Option C: pip

```bash
pip install mnemo-dev
cd your-project && mnemo init
```

Or from source:

```bash
git clone https://github.com/Mnemo-mcp/Mnemo.git
cd Mnemo && pip install -e .
cd your-project && mnemo init
```

### Option D: npx (no install)

```bash
npx @mnemo-mcp/mcp
```

This downloads and runs the MCP server directly. Requires `mnemo` CLI to be installed separately for `mnemo init`.

### Option E: Standalone Binary

Download from [GitHub Releases](https://github.com/Mnemo-mcp/Mnemo/releases) or use the install script:

```bash
curl -fsSL https://raw.githubusercontent.com/Mnemo-mcp/Mnemo/main/scripts/install.sh | sh
cd your-project && mnemo init
```

### Client Configuration

```bash
mnemo init                    # defaults to Amazon Q
mnemo init --client cursor
mnemo init --client claude-code
mnemo init --client all
```

---

## Supported Agents

| Agent | Config Flag |
|-------|-------------|
| Amazon Q | `amazonq` |
| Cursor | `cursor` |
| Claude Code | `claude-code` |
| Kiro | `kiro` |
| GitHub Copilot | `copilot` |
| Gemini CLI | `gemini` |
| Windsurf | `windsurf` |
| Cline | `cline` |
| Roo Code | `roo-code` |
| OpenCode | `opencode` |
| Goose | `goose` |

---

## MCP Tools (56)

### Memory and Context

| Tool | Description |
|------|-------------|
| `mnemo_recall` | Load decisions, preferences, active task, graph summary, recent memories |
| `mnemo_remember` | Save information (auto-categorized, auto-creates plans) |
| `mnemo_search_memory` | Semantic memory search |
| `mnemo_decide` | Record a decision |
| `mnemo_context` | Save/update project metadata |
| `mnemo_forget` | Delete a memory by ID |
| `mnemo_slot` | Read/write named memory slots |
| `mnemo_crystallize` | Summarize completed task into memory |
| `mnemo_lessons` | Query extracted lessons |

### Knowledge Graph

| Tool | Description |
|------|-------------|
| `mnemo_graph` | Query graph (stats, neighbors, traverse, path, find, hubs) |

### Plan Mode

| Tool | Description |
|------|-------------|
| `mnemo_plan` | Create/track/update plans (create, done, add, remove, status, draft, routine) |

### Code Understanding

| Tool | Description |
|------|-------------|
| `mnemo_lookup` | Method-level details for a file or folder |
| `mnemo_map` | Regenerate repo map and knowledge graph |
| `mnemo_intelligence` | Full code intelligence report |
| `mnemo_similar` | Find similar implementations |
| `mnemo_context_for_task` | Retrieve context scoped to active task |

### Search

| Tool | Description |
|------|-------------|
| `mnemo_search` | Hybrid search (BM25 + vector + graph) |

### Multi-Repo

| Tool | Description |
|------|-------------|
| `mnemo_links` | Show linked repos |
| `mnemo_cross_search` | Search across all linked repos |
| `mnemo_cross_impact` | Cross-repo impact analysis |

### Safety and Quality

| Tool | Description |
|------|-------------|
| `mnemo_check_security` | Security scan |
| `mnemo_add_security_pattern` | Add custom security pattern |
| `mnemo_breaking_changes` | Detect breaking changes |
| `mnemo_add_regression` | Record regression risk |
| `mnemo_check_regressions` | Check file regression risks |
| `mnemo_drift` | Architecture drift detection |
| `mnemo_check_conventions` | Check code against conventions |
| `mnemo_dead_code` | Detect unused code |
| `mnemo_health` | Code health report |

### Git and Workflow

| Tool | Description |
|------|-------------|
| `mnemo_commit_message` | Generate commit message from staged changes |
| `mnemo_pr_description` | Generate PR description |
| `mnemo_hooks_install` | Install pre-commit hooks |
| `mnemo_check` | Run pre-commit validations |
| `mnemo_add_correction` | Store AI correction for learning |
| `mnemo_corrections` | Show stored corrections |
| `mnemo_velocity` | Development velocity metrics |
| `mnemo_snapshot` | Create/restore git snapshots of state |

### Knowledge and APIs

| Tool | Description |
|------|-------------|
| `mnemo_knowledge` | Search team knowledge base |
| `mnemo_discover_apis` | Discover all API endpoints |
| `mnemo_search_api` | Search for specific endpoint |

### Team and Operations

| Tool | Description |
|------|-------------|
| `mnemo_team` | Team expertise map |
| `mnemo_who_touched` | Who last modified a file |
| `mnemo_add_error` | Store error/cause/fix |
| `mnemo_search_errors` | Search known errors |
| `mnemo_add_incident` | Record production incident |
| `mnemo_incidents` | Search/list incidents |
| `mnemo_add_review` | Store code review |
| `mnemo_reviews` | Show review history |
| `mnemo_dependencies` | Service dependency graph |
| `mnemo_impact` | Impact analysis |
| `mnemo_onboarding` | Generate onboarding guide |
| `mnemo_task` | Set/get current task |
| `mnemo_task_done` | Mark task complete |
| `mnemo_tests` | Test coverage info |
| `mnemo_observe` | Query observation log |
| `mnemo_export_obsidian` | Export to Obsidian-compatible markdown |

---

## Knowledge Graph

### Node Types

| Type | Examples |
|------|----------|
| service | AuthService, PaymentService |
| class | AetnaHandler, CosmosDbService |
| interface | IPayerHandler, ICacheService |
| method | AetnaHandler.BuildResponse |
| file | Services/PayerHandlers/AetnaHandler.cs |
| package | Azure.Cosmos, Moq |
| person | Contributors from git history |
| decision | Recorded architectural decisions |
| memory | Stored context from chats |
| incident | Production issues |

### Edge Types

| Edge | Meaning |
|------|---------|
| contains | service to file |
| defines | file to class/interface |
| implements | class to interface |
| inherits | class to base class |
| calls | file to class (usage) |
| has_method | class to method |
| depends_on | service to package |
| owns | person to service |
| references | decision/memory to code entity |
| affects | incident to service |

### Query Examples

```
"What implements IPayerHandler?"        -> graph traverse
"What depends on CosmosDbService?"      -> graph neighbors incoming
"Path from AetnaHandler to CosmosDB"    -> graph path
"Most connected code in the repo"       -> graph hubs
```

---

## Plan Mode

### How It Works

When you describe work with steps, Mnemo auto-detects it as a plan and creates tracked tasks with IDs. No explicit plan creation needed.

### Auto-Completion

When the agent later reports completing work that matches a task, Mnemo auto-marks it done and includes confirmation in the response.

### Task Dependencies

Tasks can declare dependencies. Frontier scoring identifies the next actionable task (all dependencies met, not yet started). Draft plans allow iterating on task lists before committing. Routine templates enable recurring plan patterns.

### Proactive Hints

Every tool response includes the next frontier task:

```
Plan 'SOAP Migration' (2/4) -- next: MNO-003 Update models with XML serialization
```

---

## Search

### Triple-Stream Architecture

1. **BM25** -- Token-based ranking with Porter stemming and synonym expansion. Fast keyword matching with IDF weighting.
2. **Vector** -- ChromaDB with all-MiniLM-L6-v2 (ONNX). Semantic similarity for meaning-based retrieval.
3. **Graph** -- Knowledge graph traversal boosts results connected to query entities.

### Fusion

Reciprocal Rank Fusion (RRF) combines all three streams into a single ranked result set. Graph boost elevates results with strong structural connections to the query context.

### Fallback

If ChromaDB is unavailable, search falls back to BM25 + graph without vector similarity.

---

## Memory Lifecycle

### Retention Formula

```
score = (access_count * 0.3) + (recency_days_inverse * 0.4) + (category_weight * 0.3)
```

Category weights: decision (1.0), pattern (0.8), fix (0.7), preference (0.6), context (0.5).

### Auto-Eviction

Memories below the retention threshold are evicted during periodic cleanup. High-value memories (decisions, frequently accessed) persist indefinitely.

### Contradiction Detection

New memories are checked against existing entries. Contradictions are flagged and the newer entry takes precedence with a reference to what it supersedes.

### Consolidation

Related memories are periodically merged into consolidated entries to reduce redundancy while preserving information.

### Lessons System

Completed tasks are analyzed for reusable patterns. Extracted lessons are stored separately and surfaced when similar work begins.

### Decay

Memories that are never accessed decay in score over time. Access resets the decay clock.

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `mnemo init` | Initialize Mnemo in current directory |
| `mnemo init --client all` | Initialize for all AI clients |
| `mnemo ui` | Open dashboard (port 7890) |
| `mnemo api` | Start REST API server (port 7891) |
| `mnemo doctor` | Diagnose setup issues |
| `mnemo status` | Quick health check |
| `mnemo recall` | Show stored memory |
| `mnemo map` | Refresh repo map and knowledge graph |
| `mnemo remember "text"` | Store a note |
| `mnemo update` | Update to latest version |
| `mnemo reset` | Wipe all Mnemo data |
| `mnemo link <path>` | Link a sibling repo |
| `mnemo link --discover <dir>` | Auto-discover and link repos |
| `mnemo unlink <name>` | Remove a linked repo |
| `mnemo links` | Show linked repos |
| `mnemo snapshot` | Create state snapshot |
| `mnemo export --obsidian` | Export to Obsidian format |

---

## Architecture

```
+-----------------------------------------------------+
|  MCP Tools (56 tools via tool_registry.py)          |
+-----------------------------------------------------+
|  Response Enrichment (enrichment.py)                |
|  -> plan hints, regression warnings, decision refs  |
+-----------------------------------------------------+
|  Knowledge Graph (graph/)                           |
|  -> LocalGraph (NetworkX) + WorkspaceGraph          |
+-----------------------------------------------------+
|  Plan Mode (plan/)                                  |
|  -> auto-create, auto-complete, dependencies,       |
|     frontier scoring, TASKS.md sync                 |
+-----------------------------------------------------+
|  Hybrid Search (search/)                            |
|  -> BM25 + Vector (ChromaDB) + Graph boost + RRF   |
+-----------------------------------------------------+
|  Memory Lifecycle (memory/)                         |
|  -> retention, eviction, contradiction, lessons     |
+-----------------------------------------------------+
|  Privacy Filter (privacy.py)                        |
|  -> 16 secret patterns stripped before storage      |
+-----------------------------------------------------+
|  Code Parsing (repo_map.py + analyzers/)            |
|  -> tree-sitter (14 languages) + Roslyn             |
+-----------------------------------------------------+
|  REST API (api.py -> :7891)                         |
+-----------------------------------------------------+
|  Storage (storage.py -> .mnemo/*.json)              |
+-----------------------------------------------------+
```

Storage layout:

```
.mnemo/
├── summary.md          # detailed code map
├── tree.md             # compact tree
├── graph.json          # knowledge graph
├── graph_meta.json     # graph stats
├── hashes.json         # change detection
├── memory.json         # memories
├── decisions.json      # decisions
├── context.json        # project metadata
├── plans.json          # tracked plans
├── links.json          # linked repos
├── slots.json          # memory slots
├── observations.json   # tool call log
├── lessons.json        # extracted lessons
├── snapshots/          # git snapshots
├── index/chroma/       # semantic search index
└── knowledge/          # team docs
```

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Core | Python 3.10+ |
| MCP Server | JSON-RPC over stdin/stdout |
| REST API | Built-in HTTP server (port 7891) |
| Knowledge Graph | NetworkX (serialized to JSON) |
| Code Parsing | tree-sitter (14 languages) + Roslyn (.NET 8 for C#) |
| Vector Search | ChromaDB + all-MiniLM-L6-v2 (ONNX) |
| Keyword Search | Custom BM25 with stemming and synonyms |
| Fusion | Reciprocal Rank Fusion (RRF) |
| Storage | JSON files in `.mnemo/` |
| Change Detection | mtime-based + git rename tracking |
| Team Graph | GitPython (git log analysis) |
| CLI | Click |
| Binary Distribution | PyInstaller |
| VS Code Extension | TypeScript |
| Dashboard | Tailwind + vis-network (CDN) |
| CI/CD | GitHub Actions |

---

## Supported Languages

### Core (included with `pip install mnemo`)

| Language | Extensions |
|----------|------------|
| Python | `.py` |
| JavaScript | `.js`, `.jsx` |
| TypeScript | `.ts`, `.tsx` |
| Go | `.go` |
| C# | `.cs` (+ Roslyn enhanced) |
| Java | `.java` |
| Rust | `.rs` |

### Optional (`pip install mnemo[all-languages]`)

| Language | Extensions |
|----------|------------|
| Ruby | `.rb` |
| PHP | `.php` |
| C | `.c`, `.h` |
| C++ | `.cpp`, `.cc`, `.hpp` |
| Kotlin | `.kt`, `.kts` |
| Swift | `.swift` |
| Scala | `.scala`, `.sc` |

Optional languages are gracefully skipped if their grammar is not installed.

---

## Requirements

- Python 3.10+
- Git (for rename/delete detection and team graph)
- Any AI client with MCP support

---

## License

AGPL-3.0. See [LICENSE](./LICENSE).

This means: anyone can use, modify, and contribute to Mnemo. You cannot close-source it or build proprietary products from it. If you modify and deploy it (even as a network service), you must share your source code under the same license.

Copyright (c) 2024 Mnemo Contributors
