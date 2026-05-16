# Mnemo

**Persistent engineering cognition for AI coding agents.**

[![PyPI](https://img.shields.io/pypi/v/mnemo-dev)](https://pypi.org/project/mnemo-dev/)
[![Tests](https://img.shields.io/badge/tests-223%20passing-brightgreen)]()
[![License](https://img.shields.io/badge/license-AGPL--3.0-blue)](LICENSE)

One command gives your AI agent accumulated engineering understanding across sessions — architecture intelligence, semantic search, code graph, and institutional memory.

```bash
pip install mnemo-dev
mnemo init
```

Your agent now remembers decisions, understands code relationships, and never asks the same question twice.

---

## Why Mnemo

| Without Mnemo | With Mnemo |
|---------------|-----------|
| Re-explain your stack every session | Agent already knows your architecture |
| Agent breaks call chains it can't see | Full dependency graph with impact analysis |
| "What caching do we use?" → agent greps | Semantic search finds "Redis for sessions" instantly |
| Decisions lost between sessions | Permanent decisions survive forever |
| Context window wasted on repetition | ~500 tokens of targeted recall per session |

## Benchmarks

| Metric | Mnemo | Built-in (CLAUDE.md) |
|--------|-------|---------------------|
| **Search R@5** | **100%** | N/A (grep) |
| **Search latency** | **2ms** | — |
| **RAM** | **265 MB** | 0 |
| **Store 1 memory** | **5ms** | manual edit |
| **Token cost/session** | ~500 | 22,000+ (full file) |
| **Cross-session persistence** | ✅ | ❌ (resets) |

> Search uses ONNX all-MiniLM-L6-v2 dense embeddings + BM25 keyword + knowledge graph traversal, fused with Reciprocal Rank Fusion.

## Quick Start

```bash
# Install
pip install mnemo-dev

# Initialize in your repo
cd your-project
mnemo init --client kiro    # or: cursor, claude-code, amazonq, copilot, generic

# That's it. Your agent now has persistent memory.
```

### What `mnemo init` does:
1. Scans your codebase (tree-sitter + Roslyn for C#)
2. Builds a knowledge graph (classes, methods, calls, communities)
3. Installs lifecycle hooks (auto-capture learnings, inject context)
4. Configures MCP server for your AI client
5. Downloads embedding model (~86MB, one-time)

### Verify it works:
```bash
mnemo recall          # See what the agent will know
mnemo serve           # Open dashboard at localhost:3333
mnemo doctor          # Diagnose any issues
```

---

## How It Works

```
Session Start (agent-spawn hook)
  → mnemo_recall injects: decisions + memories + active task + repo map
  → Agent starts with full context (~500 tokens)

User asks a question (user-prompt-submit hook)
  → Semantic search finds relevant memories
  → Injected as <mnemo-relevant-context>

Agent works (tools available via MCP)
  → mnemo_lookup: class details, methods, signatures
  → mnemo_graph: neighbors, communities, impact analysis
  → mnemo_search: find code by meaning
  → mnemo_remember: store important context
  → mnemo_decide: record permanent decisions

Session ends (stop hook)
  → Auto-captures learnings, decisions, session summary
  → Memories decay over time (hot → warm → cold → evicted)
  → Contradictions detected and superseded
```

## Features

### 🧠 Memory System
- **Categorized storage**: architecture, pattern, bug, preference, decision
- **Retention scoring**: access frequency × recency × importance
- **Branch-aware**: memories tagged with git branch, filtered on recall
- **Contradiction detection**: new facts supersede old conflicting ones
- **Token-budgeted recall**: never exceeds ~2000 tokens regardless of memory count
- **Memory slots**: pinned context (project_context, user_preferences, known_gotchas)

### 🔍 Triple-Stream Search
- **BM25**: stemmed keyword matching with synonym expansion
- **Vector**: ONNX all-MiniLM-L6-v2 dense embeddings (384-dim, cosine similarity)
- **Graph**: Dijkstra traversal from code symbols to linked memories
- **Fusion**: Reciprocal Rank Fusion (RRF) combines all three streams

### 🏗️ Code Intelligence (LadybugDB)
- **Knowledge graph**: files, classes, methods, functions, projects, communities
- **14 languages**: Python, JS, TS, C#, Go, Java, Rust + 7 optional
- **Roslyn enrichment**: C# method signatures, implements, full AST
- **Leiden clustering**: automatic community detection
- **Impact analysis**: upstream/downstream dependency tracing
- **Incremental freshness**: graph auto-updates within 30s of file changes

### 📋 Planning & Records
- **Task plans**: create, track progress, mark done
- **Error patterns**: store errors with causes and fixes
- **Incidents**: root cause analysis with affected services
- **Code reviews**: feedback history per file
- **Corrections**: wrong→right pairs the agent learns from

### 🛡️ Safety & Audit
- **Security scan**: hardcoded secrets, SQL injection, insecure HTTP
- **Dead code detection**: symbols with no incoming edges
- **Convention checking**: naming violations
- **Pre-tool-use hook**: blocks catastrophic shell commands

### 🌐 Dashboard UI
```bash
mnemo serve    # http://localhost:3333
```
- Interactive knowledge graph (vis-network)
- Memory & decisions viewer
- Community explorer with zoom-to-cluster
- Code search with click-to-focus
- Health monitoring

---

## MCP Tools (16 agent-facing)

| Tool | Purpose |
|------|---------|
| `mnemo_recall` | Load full project context (budgeted) |
| `mnemo_remember` | Store a memory with category |
| `mnemo_forget` | Delete a memory |
| `mnemo_decide` | Record permanent decision |
| `mnemo_search_memory` | Semantic search across memories |
| `mnemo_search` | Search code graph (classes/methods/files) |
| `mnemo_lookup` | Detailed symbol info (methods, signatures) |
| `mnemo_graph` | Query graph (stats/neighbors/find) |
| `mnemo_impact` | Upstream/downstream dependency analysis |
| `mnemo_plan` | Create and track task plans |
| `mnemo_audit` | Security, health, dead-code reports |
| `mnemo_record` | Store errors, incidents, reviews |
| `mnemo_generate` | Commit messages and PR descriptions |
| `mnemo_map` | Regenerate repo map |
| `mnemo_ask` | Combined graph + memory lookup |
| `mnemo_lesson` | Store/retrieve learned patterns |

---

## Supported Clients

| Client | MCP | Hooks | Agent Config |
|--------|-----|-------|-------------|
| **Kiro** | ✅ | 5 hooks | ✅ agent + skill |
| **Amazon Q** | ✅ | — | ✅ rules |
| **Claude Code** | ✅ | — | ✅ CLAUDE.md |
| **Cursor** | ✅ | — | ✅ .cursorrules |
| **Copilot** | ✅ | — | ✅ instructions |
| **Generic MCP** | ✅ | — | ✅ MNEMO.md |

---

## Performance

| Operation | Time |
|-----------|------|
| `mnemo init` (55 files) | 3.5s |
| `mnemo init` (300 files) | 7s |
| Re-init (no changes) | 0.01s |
| Remember 1 memory | 5ms |
| Recall | 33ms |
| Semantic search | 2ms |
| Graph query | 0.2ms |

| Resource | Value |
|----------|-------|
| RAM | 265 MB |
| Disk (.mnemo/) | ~16 MB |
| Model (one-time download) | 86 MB |
| External databases | 0 |

---

## Architecture

```
.mnemo/
├── memory.json          # Memories with retention scores
├── decisions.json       # Permanent architectural decisions
├── plans.json           # Task tracking
├── graph.lbug           # LadybugDB knowledge graph
├── vectors_memory.npy   # Dense embedding vectors
├── meta_memory.json     # Vector metadata
├── engine-meta.json     # File hashes for incremental updates
├── parse-cache.json     # AST parse cache
├── tree.md              # Compact repo map
└── context.json         # Project context key-values
```

**Stack**: Python · LadybugDB (Kuzu) · ONNX Runtime · tree-sitter · Roslyn

---

## Links

- **Website**: [mnemo-mcp.github.io/Mnemo](https://mnemo-mcp.github.io/Mnemo/)
- **PyPI**: [pypi.org/project/mnemo-dev](https://pypi.org/project/mnemo-dev/)
- **GitHub**: [github.com/Mnemo-mcp/Mnemo](https://github.com/Mnemo-mcp/Mnemo)
- **VS Code Extension**: [Marketplace](https://marketplace.visualstudio.com/items?itemName=Nikhil1057.mnemo-vscode)

## License

[AGPL-3.0](LICENSE)
