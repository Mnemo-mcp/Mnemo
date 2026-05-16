<p align="center">
  <img src="website/public/mnemo-logo.svg" alt="Mnemo" width="80" />
</p>

<h1 align="center">Mnemo</h1>

<p align="center">
  <strong>Your AI agent forgets everything after every session. Mnemo fixes that.</strong>
</p>

<p align="center">
  <a href="https://pypi.org/project/mnemo-dev/"><img src="https://img.shields.io/pypi/v/mnemo-dev?style=flat-square&color=blue" alt="PyPI" /></a>
  <a href="#"><img src="https://img.shields.io/badge/tests-222%20passing-brightgreen?style=flat-square" alt="Tests" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-AGPL--3.0-purple?style=flat-square" alt="License" /></a>
  <a href="https://pypi.org/project/mnemo-dev/"><img src="https://img.shields.io/pypi/pyversions/mnemo-dev?style=flat-square" alt="Python" /></a>
  <a href="https://marketplace.visualstudio.com/items?itemName=Nikhil1057.mnemo-vscode"><img src="https://img.shields.io/badge/VS%20Code-extension-007ACC?style=flat-square&logo=visualstudiocode" alt="VS Code" /></a>
</p>

<p align="center">
  Persistent memory · Semantic code search · Knowledge graph · Impact analysis<br/>
  <b>One MCP server. Every AI coding agent. Zero cloud dependencies.</b>
</p>

---

## What Mnemo Does

Your AI agent starts every session blind — no memory of past decisions, no understanding of your architecture, no awareness of what broke last time.

**Mnemo gives it a brain that persists.**

```
┌─────────────────────────────────────────────────────┐
│ Session starts → Agent instantly knows:             │
│                                                     │
│  • Every architectural decision ever made           │
│  • Your code's dependency graph & communities       │
│  • What was fixed, what broke, what to avoid        │
│  • The active task and what's next                  │
│  • Cross-service relationships across repos         │
│                                                     │
│ Session ends → Learnings auto-captured              │
│                Memory decays naturally over time     │
│                Old contradicted facts get evicted    │
└─────────────────────────────────────────────────────┘
```

---

## Install

<table>
<tr><td><b>pip (recommended)</b></td><td>

```bash
pip install mnemo-dev
```
</td></tr>
<tr><td><b>VS Code Extension</b></td><td>

Search "Mnemo" in Extensions marketplace, or:
```bash
code --install-extension Nikhil1057.mnemo-vscode
```
</td></tr>
<tr><td><b>Standalone binary</b></td><td>

```bash
# macOS / Linux
curl -fsSL https://github.com/Mnemo-mcp/Mnemo/releases/latest/download/mnemo-$(uname -s | tr A-Z a-z)-$(uname -m) -o mnemo
chmod +x mnemo && sudo mv mnemo /usr/local/bin/
```
</td></tr>
<tr><td><b>From source</b></td><td>

```bash
git clone https://github.com/Mnemo-mcp/Mnemo.git
cd Mnemo && pip install -e .
```
</td></tr>
</table>

Then initialize in your project:

```bash
cd your-project
mnemo init --client kiro    # or: cursor, claude-code, amazonq, copilot, generic
```

**Done.** Your agent now has persistent memory, code intelligence, and semantic search.

---

## Before & After

| Without Mnemo | With Mnemo |
|:---|:---|
| Re-explain your stack every session | Agent already knows your architecture |
| Agent breaks call chains it can't see | Full dependency graph with impact analysis |
| "What caching do we use?" → agent greps files | Semantic search finds the answer in 2ms |
| Decisions lost between sessions | Permanent decisions survive forever |
| Context window wasted on repetition | ~500 tokens of targeted recall |

---

## How It Works

```
 ┌── INIT (once) ──────────────────────────────────────────────┐
 │ tree-sitter parse → LadybugDB graph → ONNX vector index    │
 │ 14 languages · Roslyn C# enrichment · Leiden communities    │
 └─────────────────────────────────────────────────────────────┘
              ↓
 ┌── DURING SESSIONS (automatic) ──────────────────────────────┐
 │ Graph freshness: re-indexes changed files every 30s         │
 │ Memory capture: decisions, bugs, patterns auto-stored       │
 │ Triple search: BM25 + ONNX vectors + Dijkstra graph        │
 └─────────────────────────────────────────────────────────────┘
              ↓
 ┌── BETWEEN SESSIONS (decay) ─────────────────────────────────┐
 │ Hot → Warm → Cold → Evicted (based on access × recency)    │
 │ Contradictions auto-superseded · Memory compression         │
 │ Decisions & architecture: pinned forever                    │
 └─────────────────────────────────────────────────────────────┘
```

---

## Supported Clients

| Client | MCP | Hooks | Status |
|--------|:---:|:-----:|--------|
| **Kiro** | ✅ | 5 lifecycle hooks | Full agent + skill |
| **Amazon Q** | ✅ | — | Rules injection |
| **Claude Code** | ✅ | 6 hooks | settings.json + CLAUDE.md |
| **Cursor** | ✅ | — | .cursorrules |
| **Copilot** | ✅ | — | .github/copilot-instructions |
| **Generic MCP** | ✅ | — | Works with any MCP client |

---

## Performance

| | |
|---|---|
| **Search** | 2ms (100% R@5) |
| **Recall** | 33ms |
| **Remember** | 5ms |
| **Init (300 files)** | 7s |
| **RAM** | 265 MB |
| **External deps** | 0 (fully local) |

---

## MCP Tools (16)

| Tool | What it does |
|------|-------------|
| `mnemo_recall` | Load full project context at session start |
| `mnemo_remember` | Store important context with auto-categorization |
| `mnemo_decide` | Record permanent architectural decisions |
| `mnemo_search_memory` | Semantic search across all memories |
| `mnemo_lookup` | 360° symbol/service detail (methods, callers, deps) |
| `mnemo_search` | Search code, memory, APIs, errors |
| `mnemo_graph` | Query knowledge graph (stats, neighbors, find) |
| `mnemo_impact` | Blast radius analysis (upstream/downstream) |
| `mnemo_plan` | Task tracking with dependency resolution |
| `mnemo_audit` | Security, health, dead-code, conventions |
| `mnemo_record` | Store errors, incidents, reviews |
| `mnemo_generate` | Commit messages, PR descriptions |
| `mnemo_map` | Regenerate repo map from graph |
| `mnemo_ask` | Natural language → auto-routed query |
| `mnemo_lesson` | Learned patterns with confidence decay |
| `mnemo_forget` | Delete a specific memory |

---

## Dashboard

```bash
mnemo serve    # http://localhost:3333
```

Interactive knowledge graph · Memory viewer · Community explorer · Code search · Health monitoring

---

## Architecture

```
.mnemo/
├── memory.json          Memories with retention scores
├── decisions.json       Permanent architectural decisions
├── graph.lbug           LadybugDB knowledge graph (Kuzu)
├── vectors_*.npy        ONNX dense embeddings (384-dim)
├── plans.json           Task tracking
├── context.json         Auto-detected project metadata
├── tree.md              Compact repo index
└── engine-meta.json     File hashes for incremental updates
```

**Stack**: Python · LadybugDB (Kuzu) · ONNX Runtime · tree-sitter · Roslyn

**Zero cloud. Zero API keys. Everything runs locally.**

---

## Links

[Website](https://mnemo-mcp.github.io/Mnemo/) · [PyPI](https://pypi.org/project/mnemo-dev/) · [GitHub](https://github.com/Mnemo-mcp/Mnemo) · [VS Code](https://marketplace.visualstudio.com/items?itemName=Nikhil1057.mnemo-vscode) · [Changelog](CHANGELOG.md)

## License

[AGPL-3.0](LICENSE) — Free for personal and open-source use. Commercial licensing available.
