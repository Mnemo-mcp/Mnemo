# Mnemo v2 Architecture

> Code Intelligence + Persistent Memory for AI Agents

## Design Principle

Mnemo = GitNexus-quality code intelligence + persistent memory + multi-agent support.
Three layers, each building on the one below.

```
┌─────────────────────────────────────────────────────────┐
│  Layer 3: Agent Interface                               │
│  MCP Tools + Hooks + Skills + UI                        │
│  (Kiro, Cursor, Claude Code, Q, Copilot, Windsurf...)   │
├─────────────────────────────────────────────────────────┤
│  Layer 2: Memory                                        │
│  Decisions, Plans, Learnings, Search, Recall            │
│  Graph-boosted: memories linked to code symbols         │
├─────────────────────────────────────────────────────────┤
│  Layer 1: Code Intelligence Engine                      │
│  LadybugDB + Tree-sitter + Worker Pool + Parse Cache    │
│  Graph, FTS, Vector, Incremental, Fast                  │
└─────────────────────────────────────────────────────────┘
```

---

## Layer 1: Code Intelligence Engine

### Storage: LadybugDB

Single embedded database replacing JSON files + NetworkX + ChromaDB.

```
pip install real_ladybug
```

Provides:
- **Cypher queries** for graph traversal
- **FTS index** for keyword search (replaces custom BM25)
- **Vector index** for semantic search (replaces ChromaDB)
- **Columnar CSR adjacency** for O(1) neighbor lookups
- **ACID transactions** with WAL
- **Persistent on disk** at `.mnemo/graph.lbug`

### Graph Schema

#### Node Types

| Type | Properties | Source |
|------|-----------|--------|
| File | path, language, hash, size | scan phase |
| Folder | path | scan phase |
| Module | name, path | scan phase |
| Class | name, file, implements, docstring | parse phase |
| Interface | name, file | parse phase |
| Function | name, file, signature, returns | parse phase |
| Method | name, class, signature, visibility | parse phase |
| Route | path, method, handler | route phase |
| Community | name, description | community phase |
| Process | name, entry_point, steps | process phase |
| Memory | content, category, tier, timestamp | memory layer |
| Decision | decision, reasoning, active | memory layer |
| Plan | title, status, tasks | memory layer |

#### Edge Types

| Edge | From → To | Properties |
|------|-----------|-----------|
| CONTAINS | Folder → File | |
| DEFINES | File → Symbol | |
| CALLS | Symbol → Symbol | confidence, reason |
| IMPORTS | File → File | |
| EXTENDS | Class → Class | |
| IMPLEMENTS | Class → Interface | |
| HAS_METHOD | Class → Method | |
| ACCESSES | Function → Property | read/write |
| OVERRIDES | Method → Method | |
| MEMBER_OF | Symbol → Community | |
| STEP_IN | Symbol → Process | step_order |
| REFERENCES | Memory → Symbol | auto-linked |
| ABOUT | Decision → Symbol | auto-linked |

### Indexing Pipeline (Phased DAG)

```
Phase 1: scan        → File/Folder nodes (os.walk, <1s)
Phase 2: parse       → Symbol nodes via tree-sitter workers (parallel)
Phase 3: cross-file  → CALLS/IMPORTS edges with confidence
Phase 4: routes      → Route nodes (API endpoints, handlers)
Phase 5: communities → Leiden clustering into functional areas
Phase 6: processes   → Entry→terminal execution flow traces
```

Each phase:
- Has typed input/output
- Can be skipped (`--fast` skips phases 5-6)
- Runs incrementally (only changed files)

### Tree-sitter Worker Pool

```python
from concurrent.futures import ProcessPoolExecutor

def parse_batch(files: list[tuple[str, bytes, str]]) -> list[ParseResult]:
    """Parse files in a worker process. Cached parser per language."""
    ...

with ProcessPoolExecutor(max_workers=cpu_count()) as pool:
    results = pool.map(parse_batch, chunks)
```

- Batch files into ~10MB chunks
- Each worker has cached parsers per language
- Native tree-sitter (not WASM) — 0.1ms per file
- 16 languages supported

### Content-Addressed Parse Cache

```
.mnemo/parse-cache/
  {sha256_of_file_content}.json → ParseResult
```

- On re-index: check hash → skip if cached
- First index of 1000 files: ~5s (parallel)
- Re-index after 1 file change: <1s

### Incremental Indexing

```python
# meta.json tracks state
{
  "last_commit": "abc123",
  "file_hashes": {"src/main.py": "sha256:..."},
  "indexed_at": 1715000000
}
```

- Compare current hashes to stored hashes
- Only re-parse changed files
- Remove old nodes for changed files, insert new ones
- Re-run cross-file resolution for affected imports

---

## Layer 2: Memory

### Memory as Graph Nodes

Memories, decisions, and plans are **nodes in the same LadybugDB graph** as code symbols. This enables:

```cypher
-- Find memories about a function
MATCH (m:Memory)-[:REFERENCES]->(f:Function {name: 'handleRequest'})
RETURN m.content, m.category

-- Find decisions about a module
MATCH (d:Decision)-[:ABOUT]->(f:File)
WHERE f.path STARTS WITH 'src/auth/'
RETURN d.decision, d.reasoning

-- What was learned about this community?
MATCH (m:Memory)-[:REFERENCES]->(s)-[:MEMBER_OF]->(c:Community {name: 'PaymentProcessing'})
RETURN m.content
```

### Graph-Boosted Search

When searching memory:
1. **Keyword match** (FTS in LadybugDB)
2. **Vector similarity** (embedding index in LadybugDB)
3. **Graph expansion** — find symbols mentioned in query, traverse 1-2 hops, find memories linked to those symbols
4. **RRF fusion** — merge all three result sets

### Memory Features (preserved from v1)

- Tiered recall (hot/warm/cold with decay)
- Decision tracking with superseded_by
- Auto-contradiction detection
- Plan mode with task tracking
- Privacy filtering (secrets stripped)
- Deduplication (SHA-256)

### Auto-Linking

When a memory is stored, auto-detect code symbol references:
```python
def auto_link_memory(memory_id: str, content: str, graph: LadybugDB):
    """Find symbol names in memory content, create REFERENCES edges."""
    symbols = graph.query("MATCH (s) WHERE s.name IS NOT NULL RETURN s.name, id(s)")
    for name, node_id in symbols:
        if len(name) >= 4 and name in content:
            graph.create_edge(memory_id, node_id, "REFERENCES")
```

---

## Layer 3: Agent Interface

### MCP Tools (Consolidated — ~12 tools, not 56)

| Tool | Purpose |
|------|---------|
| `mnemo_recall` | Full context load (memories + graph summary + plan status) |
| `mnemo_remember` | Store a memory (auto-links to graph) |
| `mnemo_decide` | Record a decision (permanent, auto-links) |
| `mnemo_search` | Hybrid search (FTS + vector + graph-boosted) |
| `mnemo_context` | 360° view of a symbol (callers, callees, memories, decisions) |
| `mnemo_impact` | Blast radius analysis (upstream/downstream N hops) |
| `mnemo_query` | Ad-hoc Cypher against the graph |
| `mnemo_plan` | Create/update/complete plans |
| `mnemo_map` | Re-index the repo (incremental) |
| `mnemo_detect_changes` | Map git diff to affected symbols |
| `mnemo_rename` | Graph-assisted multi-file rename |
| `mnemo_communities` | List functional areas (Leiden clusters) |

### Hooks (Kiro + Claude Code)

| Hook | Trigger | Action |
|------|---------|--------|
| agentSpawn | Session start | Inject recall context |
| userPromptSubmit | Each message | Search relevant memories |
| preToolUse | Before shell | Security validation |
| postToolUse | After write | Track file modifications |
| stop | Session end | Auto-capture learnings, link to symbols |

### MCP Resources (URI-based, for static data)

| Resource | URI |
|----------|-----|
| Repo overview | `mnemo://repo/context` |
| Graph schema | `mnemo://repo/schema` |
| Communities | `mnemo://repo/communities` |
| Processes | `mnemo://repo/processes` |
| Active plan | `mnemo://plan/current` |

### Supported Agents

| Agent | Interface | Config Location |
|-------|-----------|----------------|
| Kiro | Hooks + MCP | `.kiro/agents/`, `.kiro/hooks/` |
| Cursor | MCP | `~/.cursor/mcp.json` |
| Claude Code | MCP + Hooks | `~/.claude/mcp.json`, `.claude/hooks/` |
| Amazon Q | MCP | `~/.aws/amazonq/mcp.json` |
| GitHub Copilot | MCP | `~/.config/github-copilot/mcp.json` |
| Windsurf | MCP | `~/.windsurf/mcp.json` |
| Cline | MCP | `~/.cline/mcp.json` |
| Roo Code | MCP | `~/.roo-code/mcp.json` |
| Gemini CLI | MCP | `~/.gemini/mcp.json` |
| OpenCode | MCP | `~/.opencode/mcp.json` |
| Goose | MCP | `~/.goose/mcp.json` |

---

## Layer 4: UI (Web Dashboard)

### Features (matching GitNexus-web + memory visualization)

| Feature | Description |
|---------|-------------|
| **Graph Explorer** | Interactive force-directed graph. Click nodes to see details, memories, decisions. Filter by type/community. |
| **Memory Timeline** | Chronological view of all memories, decisions, learnings. Filter by category, tier, linked symbol. |
| **Impact Visualizer** | Select a symbol → see blast radius highlighted in graph. Show affected memories/decisions. |
| **Community Map** | Leiden clusters as colored regions. Click to drill into module details. |
| **Process Flows** | Entry→terminal execution traces as step diagrams. |
| **Plan Board** | Kanban-style view of active plans and tasks. |
| **Search** | Unified search across code symbols + memories + decisions. |
| **Diff Impact** | Paste a git diff → see affected symbols, processes, and related memories. |
| **Health Dashboard** | Index staleness, memory stats, graph size, query performance. |

### Tech Stack

- **Vite + React + TypeScript** (same as GitNexus-web)
- **D3.js / react-force-graph** for graph visualization
- **WebSocket** connection to `mnemo serve` for live updates
- **Cyberpunk/Mission Control** aesthetic (existing design decision)

### Serve Command

```bash
mnemo serve --port 3333
# Opens browser to http://localhost:3333
# WebSocket at ws://localhost:3333/ws for live graph updates
```

---

## Storage Layout

```
<repo>/.mnemo/
  ├── graph.lbug          # LadybugDB database (graph + FTS + vector)
  ├── graph.lbug.wal      # Write-ahead log
  ├── meta.json           # lastCommit, fileHashes, indexedAt, stats
  ├── parse-cache/        # Content-addressed parse results
  │   ├── {sha256}.json
  │   └── ...
  └── config.yaml         # User preferences, ignore patterns

~/.mnemo/
  └── global.json         # Cross-repo registry, global preferences
```

---

## Performance Targets

| Operation | Target | How |
|-----------|--------|-----|
| `mnemo init` (222 files) | <5s | os.walk + parallel parse + LadybugDB bulk load |
| `mnemo init` (1000 files) | <15s | Worker pool + parse cache |
| Re-index (1 file changed) | <1s | Incremental: hash check + subgraph replace |
| `mnemo_recall` | <200ms | Cypher query + tiered memory filter |
| `mnemo_search` | <500ms | FTS + vector + graph expansion + RRF |
| `mnemo_impact` | <1s | BFS/DFS traversal with depth limit |
| `mnemo_context` | <300ms | Single Cypher query with multiple MATCH |

---

## Migration Path

1. **Phase 1**: Replace storage (LadybugDB replaces JSON + NetworkX + ChromaDB)
2. **Phase 2**: New indexing pipeline (phased DAG, worker pool, parse cache)
3. **Phase 3**: Memory-graph integration (memories as nodes, auto-linking)
4. **Phase 4**: Consolidated MCP tools (12 tools replacing 56)
5. **Phase 5**: UI rebuild (graph explorer, memory timeline, impact viz)
6. **Phase 6**: Advanced features (communities, processes, cross-repo)

Each phase is independently shippable. Phase 1-2 can land as v1.0, Phase 3-4 as v1.1, Phase 5-6 as v1.2.

---

## Dependencies (v2)

```toml
[project]
dependencies = [
    "real_ladybug>=0.15",     # Graph DB (replaces networkx + chromadb)
    "tree-sitter>=0.23",      # Parser runtime
    "tree-sitter-python",     # Language grammars (one per language)
    "tree-sitter-javascript",
    "tree-sitter-typescript",
    "tree-sitter-c-sharp",
    "tree-sitter-java",
    "tree-sitter-go",
    "tree-sitter-rust",
    "click>=8.0",             # CLI
]

[project.optional-dependencies]
all-languages = [
    "tree-sitter-ruby",
    "tree-sitter-php",
    "tree-sitter-c",
    "tree-sitter-cpp",
    "tree-sitter-kotlin",
    "tree-sitter-swift",
    "tree-sitter-scala",
]
ui = [
    "uvicorn",
    "starlette",
    "websockets",
]
```

Removed: `networkx`, `chromadb`, `onnxruntime` (LadybugDB handles all three use cases)
