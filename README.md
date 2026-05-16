<h1 align="center">Mnemo</h1>

<p align="center">
  <strong>Persistent engineering cognition for AI coding agents.</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/mnemo-dev/"><img src="https://img.shields.io/pypi/v/mnemo-dev?style=flat-square&color=blue" alt="PyPI" /></a>
  <a href="https://www.npmjs.com/package/@mnemo-dev/mcp"><img src="https://img.shields.io/npm/v/@mnemo-dev/mcp?style=flat-square&color=red" alt="npm" /></a>
  <a href="#"><img src="https://img.shields.io/badge/tests-222%20passing-brightgreen?style=flat-square" alt="Tests" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-purple?style=flat-square" alt="License" /></a>
  <a href="https://pypi.org/project/mnemo-dev/"><img src="https://img.shields.io/pypi/pyversions/mnemo-dev?style=flat-square" alt="Python" /></a>
  <a href="https://marketplace.visualstudio.com/items?itemName=Nikhil1057.mnemo-vscode"><img src="https://img.shields.io/badge/VS%20Code-extension-007ACC?style=flat-square&logo=visualstudiocode" alt="VS Code" /></a>
</p>

<p align="center">
  <code>[100% R@5]</code> <code>[2ms search]</code> <code>[58 tools]</code> <code>[16 agent-facing]</code> <code>[11 lifecycle hooks]</code> <code>[0 external DBs]</code> <code>[222 tests]</code>
</p>

<p align="center">
  <a href="#install">Install</a> • <a href="#why-mnemo">Why</a> • <a href="#benchmarks">Benchmarks</a> • <a href="#how-it-works">How It Works</a> • <a href="#supported-clients">Clients</a> • <a href="#features">Features</a> • <a href="#mcp-tools-16-agent-facing">Tools</a> • <a href="#dashboard-ui">Dashboard</a> • <a href="#architecture">Architecture</a>
</p>

---

You explain the same architecture every session. You re-discover the same bugs. You re-teach the same conventions. The agent has no memory of what worked, what broke, or what you decided yesterday.

**Mnemo fixes this.**

It silently captures decisions as they happen, builds a knowledge graph of your entire codebase, indexes everything for semantic search, and injects the right context when the next session starts. Memories decay naturally — fresh decisions stay hot, stale context fades, contradictions get superseded.

**What changes:**

Session 1: you set up a new microservice with a database layer, configure retry policies, wire up dependency injection.
Session 2: you ask the agent to add a new endpoint. It already knows your service uses a resilience pipeline, auth goes through a delegating handler, your DTOs follow the `*Request/*Response` pattern, and the orchestration uses durable workflows. No re-explaining. No grepping. The agent just *knows*.

```bash
pip install mnemo-dev    # or: brew tap Mnemo-mcp/tap && brew install mnemo
cd your-project
mnemo init              # defaults to Amazon Q (or: --client kiro, cursor, claude-code)
```

---

## Install

<table>
<tr><td><b>pip (recommended)</b></td><td>

```bash
pip install mnemo-dev
```
</td></tr>
<tr><td><b>Homebrew (macOS/Linux)</b></td><td>

```bash
brew tap Mnemo-mcp/tap && brew install mnemo
```
</td></tr>
<tr><td><b>npx (Node.js)</b></td><td>

```bash
npx @mnemo-dev/mcp
```
</td></tr>
<tr><td><b>VS Code Extension</b></td><td>

Search "Mnemo" in Extensions, or:
```bash
code --install-extension Nikhil1057.mnemo-vscode
```
</td></tr>
<tr><td><b>Standalone binary</b></td><td>

```bash
curl -fsSL https://github.com/Mnemo-mcp/Mnemo/releases/latest/download/mnemo-$(uname -s | tr A-Z a-z)-$(uname -m) -o mnemo
chmod +x mnemo && sudo mv mnemo /usr/local/bin/
```
</td></tr>
<tr><td><b>From source</b></td><td>

```bash
git clone https://github.com/Mnemo-mcp/Mnemo.git && cd Mnemo && pip install -e .
```
</td></tr>
</table>

Then initialize:

```bash
cd your-project
mnemo init                      # defaults to Amazon Q
mnemo init --client kiro        # or: cursor, claude-code, copilot, generic
```

**That's it.** Your agent now has persistent memory, semantic search, and architectural understanding.

```bash
mnemo recall          # Preview what the agent will see
mnemo serve           # Dashboard at localhost:3333
mnemo doctor          # Diagnose issues
```

---

## What It Looks Like Day-to-Day

You don't interact with Mnemo directly. You just talk to your AI agent as usual — Mnemo works in the background.

**Day 1 — Setting up a project:**
```
You:   "Set up a new payment service with retry policies and circuit breaker"
Agent: [builds the service, configures resilience]
       [Mnemo auto-captures: architecture decision, file structure, patterns used]
```

**Day 2 — Continuing work:**
```
You:   "Add a new endpoint for refund processing"
Agent: [Already knows: your service uses resilience pipelines, 
        auth goes through a delegating handler, DTOs follow *Request/*Response pattern]
       "I see your existing service uses X pattern. I'll follow the same 
        structure for the refund endpoint..."
```

**Day 5 — Debugging:**
```
You:   "The batch job is failing intermittently"
Agent: [Searches memory → finds you hit a similar issue last week with timeout config]
       "Based on a similar issue you fixed on Monday — the timeout was set too low 
        for large batches. Let me check if the same config applies here..."
```

**Day 10 — New team member's agent:**
```
You:   "How does our auth flow work?"
Agent: [mnemo_lookup on the auth service → full architecture in one call]
       "Your auth uses a delegating handler pattern with token caching.
        Here are the key classes and their methods..."
       [No file reading needed — graph has everything]
```

**Day 30 — Cross-service impact:**
```
You:   "I need to change the response format of the eligibility API"
Agent: [mnemo_cross_impact → finds 3 other services consuming this API]
       "⚠️ Changing this will affect: ServiceA (mock consumer), 
        ServiceB (integration tests), and the UI (display logic).
        Want me to show the specific callers?"
```

The agent never asks you to re-explain. Old stale context fades naturally. Critical decisions persist forever.

---

## Supported Clients

| Client | MCP | Hooks | Config |
|--------|:---:|:-----:|--------|
| **Kiro** | ✅ | 5 lifecycle hooks | Agent + skill + rules |
| **Amazon Q** | ✅ | — | .amazonq/rules |
| **Claude Code** | ✅ | 6 hooks (settings.json) | CLAUDE.md |
| **Cursor** | ✅ | — | .cursorrules |
| **Copilot** | ✅ | — | .github/copilot-instructions |
| **Windsurf** | ✅ | — | .windsurfrules |
| **Generic MCP** | ✅ | — | MNEMO.md |

Works with **any** agent that speaks MCP. One server, one memory, shared across all clients.

---

## Why Mnemo

| Without Mnemo | With Mnemo |
|:---|:---|
| Re-explain your stack every session | Agent already knows your architecture |
| Agent breaks call chains it can't see | Full dependency graph with impact analysis |
| "What caching do we use?" → agent greps 50 files | Semantic search finds the answer in **2ms** |
| Decisions lost between sessions | Permanent decisions survive forever |
| Context window wasted on repetition | ~500 tokens of targeted recall per session |
| "What broke last time?" → no idea | Error patterns, incidents, and regression warnings |
| Agent doesn't know cross-service deps | Multi-repo linking with cross-impact analysis |
| Memory file grows forever, goes stale | Natural decay: hot → warm → cold → evicted |

---

## Benchmarks

| Metric | Mnemo | Static rules (CLAUDE.md) | No memory |
|--------|-------|-------------------------|-----------|
| **Search Recall@5** | **100%** | N/A (grep) | 0% |
| **Search latency** | **2ms** | — | — |
| **Token cost/session** | **~500** | 22,000+ (full file) | 0 |
| **Cross-session persistence** | ✅ | Manual only | ❌ |
| **Contradiction handling** | ✅ auto-supersede | ❌ | ❌ |
| **Memory decay** | ✅ natural eviction | ❌ grows forever | — |
| **Code understanding** | Knowledge graph | None | None |
| **Cross-repo awareness** | ✅ | ❌ | ❌ |

### System Resources

| Resource | Value |
|----------|-------|
| RAM (with model loaded) | 265 MB |
| Disk (.mnemo/) | ~16 MB |
| ONNX model (one-time download) | 86 MB |
| External databases | **0** |
| Cloud dependencies | **0** |
| API keys required | **0** |

> Search uses ONNX all-MiniLM-L6-v2 dense embeddings + BM25 keyword + Dijkstra graph traversal, fused with Reciprocal Rank Fusion (RRF).

---

## How It Works

```
┌─── INIT (one-time, ~7s for 300 files) ───────────────────────────┐
│                                                                  │
│  1. Scan: single os.walk pass across repo                        │
│  2. Parse: tree-sitter AST (14 langs) + Roslyn (C#)              │
│  3. Graph: LadybugDB — files, classes, methods, CALLS edges      │
│  4. Scope: cross-file function call resolution                   │
│  5. Cluster: Leiden community detection                          │
│  6. Index: ONNX vector embeddings for semantic search            │
│  7. Detect: languages, services, key classes, frameworks         │
│  8. Configure: MCP server + hooks for your AI client             │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─── SESSION START (automatic via hooks) ──────────────────────────┐
│                                                                  │
│  mnemo_recall injects into agent context:                        │
│    • Architectural decisions (permanent, never evicted)          │
│    • Hot memories (scored by access × recency × importance)      │
│    • Active plan + next task                                     │
│    • Compact repo index (classes per service)                    │
│    • Project metadata (languages, frameworks, services)          │
│                                                                  │
│  Total: ~500 tokens. Agent starts fully informed.                │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─── DURING SESSION (tools + freshness) ──────────────────────────┐
│                                                                  │
│  Agent has 16 MCP tools available:                               │
│    • mnemo_lookup → full service/class architecture              │
│    • mnemo_search → semantic search (code, memory, APIs)         │
│    • mnemo_impact → blast radius if X changes                    │
│    • mnemo_remember → store decisions, patterns, bugs            │
│    • mnemo_plan → track task progress                            │
│                                                                  │
│  Background: graph + vector index refresh every 30s              │
│  User prompt hook: searches relevant memories, injects them      │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─── SESSION END (auto-capture via stop hook) ─────────────────────┐
│                                                                  │
│  • Detects learnings (bug fixes, discoveries)                    │
│  • Records session decisions                                     │
│  • Stores accomplishments                                        │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─── BETWEEN SESSIONS (decay + maintenance) ───────────────────────┐
│                                                                  │
│  Every 10th recall:                                              │
│    • Retention scored: salience × exp(-0.01 × days) + access     │
│    • Hot (≥0.5) → Warm (≥0.25) → Cold → Evicted                  │
│    • Contradictions auto-superseded (sim > 0.9)                  │
│    • Low-value pruning (cap: 200 active memories)                │
│    • Graph synced (stale memory nodes removed)                   │
│                                                                  │
│  Pinned forever: architecture, decision, preference              │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Features

### 🧠 Memory System
- **Categorized storage**: architecture, pattern, bug, preference, decision, todo
- **Retention scoring**: access frequency × recency × importance (Ebbinghaus-inspired decay)
- **Branch-aware**: memories tagged with git branch, filtered on recall
- **Contradiction detection**: new facts auto-supersede old conflicting ones (threshold: 0.6)
- **Token-budgeted recall**: never exceeds ~2000 tokens regardless of memory count
- **Memory slots**: pinned structured context (project_context, conventions, known_gotchas)
- **Auto-categorization**: regex-based category inference from content
- **Entity resolution**: resolves "this file" → actual filename from task context
- **Deduplication**: identical/near-identical memories merged, timestamps refreshed

### 🔍 Triple-Stream Search (100% R@5)
- **BM25**: IDF-weighted sparse embeddings with synonym expansion
- **Vector**: ONNX all-MiniLM-L6-v2 dense embeddings (384-dim, cosine similarity, 2ms)
- **Graph**: Dijkstra shortest-path from code symbols to linked memories (weighted edges)
- **Fusion**: Reciprocal Rank Fusion (RRF) with source diversification (max 3 per category)
- **Zero-LLM query expansion**: entity extraction, case detection, path matching

### 🏗️ Code Intelligence Engine (LadybugDB)
- **Knowledge graph**: files, folders, classes, methods, functions, projects, communities
- **14 languages**: Python, JS/TS, C#, Go, Java, Rust, Ruby, PHP, C/C++, Kotlin, Swift, Scala
- **Roslyn enrichment**: C# method signatures, implements, full AST detail
- **Leiden community detection**: automatic functional clustering
- **CALLS edges**: scope-resolved function call graph with confidence scoring
- **Impact analysis**: upstream/downstream blast radius (N-hop BFS)
- **Incremental freshness**: graph + vector index auto-update within 30s of file changes
- **Service-level lookup**: one tool call returns full service architecture (classes + methods + deps)
- **Parse caching**: unchanged files skipped on re-index

### 📋 Planning & Knowledge
- **Task plans**: create, track, mark done, dependency resolution, auto-detect completion from memory
- **Error patterns**: store errors with root cause and fix
- **Incidents**: past incidents with affected services and resolution
- **Code reviews**: feedback history per file
- **Corrections**: wrong→right pairs with confidence decay (agent learns from mistakes)
- **Lessons**: learned patterns that reinforce with repetition
- **Knowledge base**: markdown docs indexed for semantic retrieval
- **API discovery**: auto-detect OpenAPI specs + controller annotations

### 🛡️ Safety & Audit
- **Secret stripping**: auto-removes tokens, keys, passwords from memories before storage
- **Security scan**: hardcoded secrets, SQL injection, eval(), shell injection, insecure HTTP
- **Dead code detection**: symbols with no incoming edges in the graph
- **Convention checking**: naming violations per language (PascalCase, camelCase, snake_case)
- **Pre-tool-use hook**: blocks catastrophic shell commands (rm -rf /, system dirs, credential exfil)
- **Audit trail**: every memory operation logged with timestamp and action

### 🌐 Multi-Repo & Cross-Service
- **Workspace linking**: `mnemo link ../other-repo` connects sibling repos
- **Cross-repo search**: find code, APIs, knowledge across all linked repos
- **Cross-impact analysis**: what breaks in OTHER services if you change a symbol
- **Shared knowledge**: decisions and patterns visible across workspace
- **Service registry**: auto-detected from project manifests

---

## MCP Tools (58 total: 16 agent-facing + 42 specialized)

Mnemo exposes **16 consolidated agent-facing tools** via MCP — designed to cover every workflow in minimal tool calls. Under the hood, these route to **42 specialized internal tools** for granular operations.

### Agent-Facing Tools (what the AI calls)

| Tool | What it does |
|------|-------------|
| `mnemo_recall` | Load full project context at session start (budgeted ~2000 tokens) |
| `mnemo_remember` | Store important context with auto-categorization & dedup |
| `mnemo_decide` | Record permanent architectural decisions (never evicted) |
| `mnemo_forget` | Delete a specific memory by ID |
| `mnemo_search_memory` | Semantic search across memories (3-way RRF fusion) |
| `mnemo_lookup` | 360° detail: class methods, function signatures, or full service architecture |
| `mnemo_search` | Unified search: code + memory + APIs + errors + cross-repo |
| `mnemo_graph` | Query knowledge graph (stats, neighbors, find by type) |
| `mnemo_impact` | Blast radius — what breaks if X changes (N-hop BFS traversal) |
| `mnemo_plan` | Task plans: create, done, add, remove, depends, status |
| `mnemo_audit` | Security scan, health check, dead code, convention violations |
| `mnemo_record` | Store errors, incidents, reviews, corrections |
| `mnemo_generate` | Commit messages and PR descriptions from git diff |
| `mnemo_map` | Regenerate repo map from graph (instant) |
| `mnemo_ask` | Natural language → auto-routed to appropriate tools |
| `mnemo_lesson` | Learned patterns with confidence decay and reinforcement |

### Specialized Internal Tools (42 — routed through agent-facing tools)

<details>
<summary>Click to expand full tool inventory</summary>

**Code Intelligence:**
| Tool | Purpose |
|------|---------|
| `mnemo_symbol` | 360° context for a symbol (callers, callees, community) |
| `mnemo_query` | Raw Cypher queries against LadybugDB |
| `mnemo_communities` | List all detected code communities |
| `mnemo_dead_code` | Find unreferenced classes and functions |
| `mnemo_check_conventions` | Naming violation check per language |
| `mnemo_dependencies` | Dependency tree for a symbol |
| `mnemo_breaking_changes` | Detect potential breaking changes in a diff |
| `mnemo_temporal` | File instability scores (change frequency) |
| `mnemo_onboarding` | Generate onboarding guide from graph |

**Memory & Knowledge:**
| Tool | Purpose |
|------|---------|
| `mnemo_slot_get` | Read a named memory slot |
| `mnemo_slot_set` | Write a named memory slot |
| `mnemo_context` | Save/update project context key-values |
| `mnemo_search_memory` | Deep semantic memory search |
| `mnemo_episode` | Store episodic session summaries |
| `mnemo_snapshot` | Capture full memory state snapshot |
| `mnemo_knowledge` | Search project knowledge base (runbooks, docs) |
| `mnemo_corrections` | List stored wrong→right corrections |
| `mnemo_add_correction` | Add a new correction pattern |

**Safety & Security:**
| Tool | Purpose |
|------|---------|
| `mnemo_check_security` | Scan for secrets, injection, insecure patterns |
| `mnemo_add_security_pattern` | Add custom security scan pattern |
| `mnemo_check_regressions` | Check known regression risks |
| `mnemo_add_regression` | Register a new regression risk |
| `mnemo_check` | Pre-command safety check (blocks dangerous ops) |

**Engineering Records:**
| Tool | Purpose |
|------|---------|
| `mnemo_add_error` | Store error pattern with root cause |
| `mnemo_search_errors` | Search past errors |
| `mnemo_add_incident` | Record incident with affected services |
| `mnemo_incidents` | Search past incidents |
| `mnemo_add_review` | Store code review feedback |
| `mnemo_reviews` | Search review history |

**Multi-Repo & APIs:**
| Tool | Purpose |
|------|---------|
| `mnemo_links` | Show linked repos in workspace |
| `mnemo_cross_search` | Search across all linked repos |
| `mnemo_cross_impact` | Cross-service impact analysis |
| `mnemo_discover_apis` | Auto-detect API endpoints (OpenAPI + annotations) |
| `mnemo_search_api` | Search API catalog |

**Team & Velocity:**
| Tool | Purpose |
|------|---------|
| `mnemo_team` | Team activity and expertise map |
| `mnemo_who_touched` | Find who has expertise on a file/symbol |
| `mnemo_velocity` | Sprint velocity and throughput metrics |
| `mnemo_tests` | Test coverage and health insights |

**Generation:**
| Tool | Purpose |
|------|---------|
| `mnemo_commit_message` | Generate commit message from staged changes |
| `mnemo_pr_description` | Generate PR description with context |
| `mnemo_drift` | Detect architectural drift from declared rules |
| `mnemo_health` | Overall project health score |

</details>

---

## Lifecycle Hooks (per client)

Hooks are shell scripts (Kiro) or JSON config (Claude Code) that fire at key points in the agent lifecycle. They're what makes Mnemo **automatic** — you don't need to manually tell the agent to remember or recall.

### Kiro (5 hooks)

| Hook | Trigger | What it does |
|------|---------|-------------|
| **agent-spawn** | Session starts | Calls `mnemo_recall` → injects full context (decisions, memories, plans, repo map) into agent |
| **user-prompt-submit** | Every user message | Searches memories relevant to the current prompt → injects as `<mnemo-relevant-context>` |
| **pre-tool-use** | Before Bash commands | Security check: blocks catastrophic commands (rm -rf /, credential exfil, system dir mods) |
| **post-tool-use** | After Write/Edit | Records modified files in memory (`Modified file: path/to/file`) |
| **stop** | Session ends | Detects learnings (bug fixes, decisions, accomplishments) → auto-stores in memory |

### Claude Code (6 hooks via .claude/settings.json)

| Hook | Trigger | What it does |
|------|---------|-------------|
| **SessionStart** | Chat opens | Loads full recall context |
| **UserPromptSubmit** | Every message | Semantic memory search on user's prompt |
| **PreToolUse (Bash)** | Before shell command | Safety: blocks dangerous operations |
| **PostToolUse (Write\|Edit)** | After file write | Records file modification in memory |
| **Stop** | Session ends | Captures session learnings and decisions |
| **PreCompact** | Before context compaction | Re-injects recall so context survives compaction |

### Other Clients (Amazon Q, Cursor, Copilot, Windsurf)

These clients don't support hooks natively. Instead, Mnemo installs a **rules/context file** that instructs the agent to:
1. Call `mnemo_recall` at session start
2. Call `mnemo_search_memory` before asking the user a question
3. Call `mnemo_remember` after making decisions or fixing bugs
4. Call `mnemo_plan` to track task progress

The rules file is auto-generated at `mnemo init` and includes the full tool reference.

---

## Performance

| Operation | Time |
|-----------|------|
| `mnemo init` (55 files) | 3.5s |
| `mnemo init` (300 files) | 7s |
| Re-init (no changes) | 0.01s |
| `mnemo_recall` | 33ms |
| `mnemo_remember` | 5ms |
| `mnemo_search_memory` | 2ms |
| `mnemo_lookup` (service-level) | 0.5ms |
| Graph query | 0.2ms |

---

## Dashboard UI

```bash
mnemo serve    # http://localhost:3333
```

- 🕸️ Interactive knowledge graph visualization (vis-network)
- 🧠 Memory & decisions viewer with category filters
- 🏘️ Community explorer with zoom-to-cluster
- 🔍 Code search with click-to-focus on graph nodes
- 📊 Health monitoring, stats, and resource usage
- 📋 Node detail panels (methods, callers, callees, community)

---

## Architecture

```
.mnemo/
├── memory.json          Memories with retention scores & access history
├── decisions.json       Permanent architectural decisions
├── plans.json           Task tracking with dependencies
├── context.json         Auto-detected project metadata
├── graph.lbug/          LadybugDB knowledge graph (Kuzu engine)
├── vectors_code.npy     ONNX embeddings of code symbols (384-dim)
├── vectors_memory.npy   ONNX embeddings of memories
├── meta_*.json          Vector metadata for cosine search
├── engine-meta.json     File hashes for incremental detection
├── parse-cache.json     AST parse cache (skip unchanged files)
├── tree.md              Compact repo index (generated from graph)
├── corrections.json     Wrong→right patterns with confidence
├── lessons.json         Learned patterns with reinforcement
└── slots.json           Pinned structured context (conventions, gotchas)
```

**Stack**: Python · LadybugDB (Kuzu) · ONNX Runtime · tree-sitter · Roslyn · NetworkX (Leiden)

**Zero cloud. Zero API keys. Zero telemetry. Everything runs locally.**

---

## Memory Retention Model

```
Retention = Salience × Temporal_Decay + Reinforcement

Salience:       architecture=0.9  decision=0.9  preference=0.85
                pattern=0.8  bug=0.7  todo=0.6  general=0.5

Decay:          exp(-0.01 × days_old)

Reinforcement:  Σ(1 / days_since_each_access) × 0.05    (capped at 0.3)

Tiers:
  retention ≥ 0.5   → HOT    (always shown in recall)
  retention ≥ 0.25  → WARM   (shown if token budget allows)
  retention < 0.25  → COLD   (excluded from recall, findable via search)
  retention < 0.1 + age > 60d → EVICTED

Pinned categories (never evicted): architecture, decision, preference
```

---

## CLI Reference

```bash
mnemo init [--client CLIENT]     # Initialize in a repo (kiro, cursor, claude-code, amazonq, copilot)
mnemo recall [--tier TIER]       # Show agent context (compact, standard, deep)
mnemo map                        # Regenerate repo map from graph
mnemo serve [-p PORT]            # Dashboard UI (default: 3333)
mnemo doctor                     # Diagnose installation issues
mnemo reset                      # Remove Mnemo data (safe: only Mnemo-owned files)
mnemo link [TARGET]              # Link another repo to multi-repo workspace
mnemo remember "content" [-c CAT]# Store a memory
mnemo tool NAME [--args]         # Call any MCP tool from CLI
```

---

## Contributing

```bash
git clone https://github.com/Mnemo-mcp/Mnemo.git
cd Mnemo
pip install -e ".[dev]"
pytest                    # 222 tests
ruff check .              # Lint
mnemo init                # Test on self
```

---

## Links

| | |
|---|---|
| 🌐 **Website** | [mnemo-mcp.github.io/Mnemo](https://mnemo-mcp.github.io/Mnemo/) |
| 📦 **PyPI** | [pypi.org/project/mnemo-dev](https://pypi.org/project/mnemo-dev/) |
| 📦 **npm** | [npmjs.com/package/@mnemo-dev/mcp](https://www.npmjs.com/package/@mnemo-dev/mcp) |
| 🍺 **Homebrew** | `brew tap Mnemo-mcp/tap && brew install mnemo` |
| 🧩 **VS Code** | [Marketplace](https://marketplace.visualstudio.com/items?itemName=Nikhil1057.mnemo-vscode) |
| 💻 **GitHub** | [github.com/Mnemo-mcp/Mnemo](https://github.com/Mnemo-mcp/Mnemo) |
| 📋 **Changelog** | [CHANGELOG.md](CHANGELOG.md) |
| 📋 **Distribution** | [DISTRIBUTION.md](DISTRIBUTION.md) |

---

## License

[AGPL-3.0](LICENSE) — Free for personal and open-source use.
