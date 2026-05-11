# Mnemo

Persistent memory, knowledge graph, and code intelligence for AI coding assistants. One command gives Amazon Q, Cursor, Claude Code, and other MCP clients project context across chat sessions — no re-reading files, no lost context.

## Mnemo in Simple Words

Mnemo is your AI agent's project brain.

- It remembers important decisions and past fixes.
- It builds a knowledge graph of your codebase (classes, services, relationships).
- It helps the agent answer questions about architecture, APIs, tests, and patterns.
- It works across chats, so you do not repeat project context every time.
- It searches across multiple repos so the agent knows your full platform.
- It tracks plans and auto-updates progress as work happens.
- It proactively surfaces warnings, decisions, and next steps in every response.

## Mnemo in Technical Terms

Mnemo is a local-first MCP server (`mnemo-mcp`) plus repo-side data/indexing.

- It exposes 48 MCP tools for memory, knowledge graph, retrieval, architecture analysis, API discovery, plan tracking, task context, incidents, reviews, and diagnostics.
- It builds a knowledge graph (NetworkX) with structural relationships (implements, inherits, calls, depends_on, owns).
- It supports semantic retrieval (ChromaDB auto-installed on first use) with keyword fallback.
- It supports multi-repo workspaces with cross-repo graph queries and impact analysis.
- It enriches every tool response with proactive context (plan status, regression warnings, related decisions).
- It auto-detects plans from memories/decisions and auto-marks tasks done.

## What it does

- **Knowledge Graph** — Builds a graph of services, classes, interfaces, methods, packages, and people with structural relationships (886 nodes, 1459 edges on a typical microservices repo)
- **Persistent Memory** — Stores decisions, patterns, preferences, and chat summaries across sessions with tiered retrieval (never loses context, never overloads it)
- **Plan Mode** — Auto-creates trackable plans from memories/decisions, auto-marks tasks done, syncs to TASKS.md
- **Response Enrichment** — Every tool response includes proactive hints (next plan task, regression warnings, related decisions)
- **Repo Map** — Compact tree showing all services equally, with key classes per module
- **Code Intelligence** — Detects architecture, dependencies, patterns, ownership, and similar implementations
- **Semantic Search** — Finds code by meaning, not just filename (powered by ChromaDB)
- **Multi-Repo Workspace** — Federated graph queries across linked repos, cross-repo impact analysis
- **Knowledge Base** — Searchable team knowledge from markdown files (runbooks, standards, gotchas)
- **API Discovery** — Parses OpenAPI/Swagger specs and controller annotations to build a complete API catalog
- **Auto-Remember** — Automatically saves meaningful findings to memory for future chats
- **Auto-refresh** — Detects file changes (via mtime), renames (via git), and deletions
- **Zero friction** — One `mnemo init` and it works forever
- **Dashboard UI** — Visual web dashboard showing knowledge graph, memory, repos, health, and more (`mnemo ui`)

## How Smooth Is It?

For day-to-day work, it is designed to feel close to "install once, forget forever":

1. Run `mnemo init` once in a repo.
2. Restart your AI client.
3. Ask normal questions in plain language.
4. Mnemo tools are called automatically when needed.

In practice, the experience is smooth when:
- Python and `mnemo-mcp` are on PATH.
- Your client MCP config is present.
- You run `mnemo map` after large refactors (or let normal recall refresh run).

If anything is off, `mnemo doctor --client all` gives actionable diagnostics.

## Installation

### Option A: VS Code Extension (easiest)

1. Install the **Mnemo** extension from the VS Code Marketplace
2. Open a project → extension prompts "Initialize Mnemo?"
3. Click Yes → done

The extension auto-downloads the binary, initializes the repo, and configures MCP. No Python needed.

### Option B: Homebrew (macOS/Linux)

```bash
brew tap Mnemo-mcp/tap
brew install mnemo
```

Then in your repo:

```bash
cd your-project
mnemo init
```

### Option C: pip (all platforms)

```bash
pip install mnemo
```

Or from source:

```bash
git clone https://github.com/Mnemo-mcp/Mnemo.git
cd Mnemo
pip install -e .
```

Then in your repo:

```bash
cd your-project
mnemo init
```

> **Note (macOS):** If you get a warning about scripts not being on PATH:
> ```bash
> echo 'export PATH="$HOME/Library/Python/3.12/bin:$PATH"' >> ~/.zshrc
> source ~/.zshrc
> ```

> **Note (Linux):** If installed with `--user`:
> ```bash
> echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
> source ~/.bashrc
> ```

> **Note (Windows):** If `mnemo` is not found after install, add your Python Scripts directory to PATH.

### Option D: Standalone binary (no Python needed)

Download from [GitHub Releases](https://github.com/Mnemo-mcp/Mnemo/releases):

| Platform | Download |
|----------|----------|
| macOS (Apple Silicon) | `mnemo-macos-arm64` |
| macOS (Intel) | `mnemo-macos-x64` |
| Linux | `mnemo-linux-x64` |
| Windows | `mnemo-windows-x64.exe` |

Or use the install script:

```bash
# macOS/Linux
curl -fsSL https://raw.githubusercontent.com/Mnemo-mcp/Mnemo/main/scripts/install.sh | sh

# Windows (PowerShell)
irm https://raw.githubusercontent.com/Mnemo-mcp/Mnemo/main/scripts/install.ps1 | iex
```

Then:

```bash
cd your-project
mnemo init
```

### Initialize your repo

```bash
cd your-project
mnemo init
```

By default this configures Amazon Q. Target another client or all:

```bash
mnemo init --client cursor
mnemo init --client claude-code
mnemo init --client all
```

Supported: `amazonq`, `cursor`, `claude-code`, `kiro`, `copilot`, `generic`, `all`.

This command:
1. Creates `.mnemo/` folder (added to `.gitignore` automatically)
2. Generates a compact repo map + knowledge graph
3. Indexes code into semantic search (ChromaDB auto-installs on first use)
4. Detects code patterns and conventions
5. Creates a knowledge base directory
6. Installs the right client context file
7. Configures the MCP server in the selected client's MCP config

### Restart your IDE

Restart your IDE or reload your AI client extension to pick up the new MCP server.

```bash
mnemo doctor --client all  # if setup doesn't look right
mnemo status               # quick check
```

---

## Knowledge Graph

Mnemo builds a knowledge graph of your codebase during `mnemo init` / `mnemo map`.

### What it captures

| Node Type | Examples |
|-----------|----------|
| service | isAuthRequiredService, providerSearchService |
| class | AetnaHandler, CosmosDbService |
| interface | IPayerHandler, ICacheService |
| method | AetnaHandler.BuildResponse |
| file | Services/PayerHandlers/AetnaHandler.cs |
| package | Azure.Cosmos, Moq |
| person | Nikhil, Ayushy (from git) |
| decision | "Use Redis for caching" |
| memory | Stored context from chats |
| incident | Production issues |

### Relationships (edges)

| Edge | Meaning |
|------|---------|
| contains | service → file |
| defines | file → class/interface |
| implements | class → interface |
| inherits | class → base class |
| calls | file → class (usage) |
| has_method | class → method |
| depends_on | service → package |
| owns | person → service |
| references | decision/memory → code entity |
| affects | incident → service |

### Query examples

```
"What implements IPayerHandler?"     → graph traverse
"What depends on CosmosDbService?"   → graph neighbors incoming
"Path from AetnaHandler to CosmosDB" → graph path
"Most connected code in the repo"    → graph hubs
```

### Architecture: Local → Workspace → Enterprise

```
┌─────────────────────────────────────────────────┐
│  Tier 3: Organization (future — mnemo serve)    │
│  ┌───────────────────────────────────────────┐  │
│  │  Tier 2: Workspace (federated)            │  │
│  │  ┌─────────────────────────────────────┐  │  │
│  │  │  Tier 1: Local (per repo)           │  │  │
│  │  │  NetworkX graph → .mnemo/graph.json │  │  │
│  │  └─────────────────────────────────────┘  │  │
│  │  Queries fan out to all linked repos      │  │
│  └───────────────────────────────────────────┘  │
│  Same GraphStore protocol — just wraps lower    │
└─────────────────────────────────────────────────┘
```

---

## Plan Mode

Mnemo automatically tracks plans and progress.

### How it works

You don't need to explicitly create plans. When you tell the AI about work to do:

```
User: "We need to migrate Service Review and Eligibility to SOAP APIs.
       Steps: convert controllers, add WSDL, update models, update tests"

AI calls mnemo_remember or mnemo_decide with this content

Mnemo auto-detects it's a plan → creates tracked tasks:
  📋 Auto-created plan:
  - [ ] MNO-001 Convert controllers to SOAP endpoints
  - [ ] MNO-002 Add WSDL definitions for each service
  - [ ] MNO-003 Update models with XML serialization
  - [ ] MNO-004 Update tests with XML payloads
```

### Auto-completion

When the AI later remembers completing work that matches a task:

```
AI calls mnemo_remember "Implemented WSDL definitions for eligibility and service review"

Mnemo auto-detects match → marks MNO-002 done
Response includes: "✅ Auto-completed MNO-002: Add WSDL definitions"
```

### Proactive hints

Every tool response includes the next task:

```
📋 Plan 'SOAP Migration' (2/4) — next: MNO-003 Update models with XML serialization
```

Plans sync to `TASKS.md` automatically.

---

## Response Enrichment

Every tool response is enriched with proactive context. The AI doesn't need to call extra tools — Mnemo injects relevant information automatically.

| When you call... | Mnemo also shows... |
|---|---|
| `mnemo_lookup "PayerHandler"` | ⚠️ Regression risk + 📌 Related decision + 📋 Next plan task |
| `mnemo_remember "fixed the bug"` | ✅ Auto-completed matching plan task |
| `mnemo_similar "Handler"` | 📋 Next plan task |
| `mnemo_health` | 📋 Next plan task |

This means the AI always has context about what's important right now, without needing to remember to check.

---

## Multi-Repo Workspace

Mnemo searches across multiple repositories with federated graph queries.

### Link repos

```bash
mnemo link ../auth-service
mnemo link --discover ~/CodeRepo
mnemo link --discover ~/CodeRepo --init
mnemo unlink auth-service
mnemo links
```

### What it enables

| What you ask | What happens |
|---|---|
| "Find authentication code across all services" | Cross-repo graph + semantic search |
| "What breaks if I change the token format?" | Federated graph traversal |
| "What APIs does the auth service expose?" | Searches linked repo's API index |

---

## Semantic Search

ChromaDB-powered search by meaning, not just filename.

| Query | Finds |
|---|---|
| "token refresh" | `getToken()`, `acquireTokenSilent()`, `ClientCredentialTokenService` |
| "error handling" | retry pipelines, DelegatingHandlers, catch blocks |
| "database access" | CosmosDbService, repositories, connection code |

Falls back to keyword matching if ChromaDB is unavailable.

---

## MCP Tools (48 total)

### Memory & Context

| Tool | Description |
|------|-------------|
| `mnemo_recall` | Load decisions, preferences, active task, graph summary, and recent memories |
| `mnemo_remember` | Save information (auto-categorized, auto-creates plans if plan-like) |
| `mnemo_search_memory` | Search all memories semantically |
| `mnemo_decide` | Record a decision (auto-creates plan if reasoning has steps) |
| `mnemo_context` | Save/update project metadata |
| `mnemo_forget` | Delete a memory by ID |

### Knowledge Graph

| Tool | Description |
|------|-------------|
| `mnemo_graph` | Query the knowledge graph (stats, neighbors, traverse, path, find, hubs) |

### Plan Mode

| Tool | Description |
|------|-------------|
| `mnemo_plan` | Create/track/update plans (create, done, add, remove, status) |

### Code Understanding

| Tool | Description |
|------|-------------|
| `mnemo_lookup` | Get method-level details for a file or folder |
| `mnemo_map` | Regenerate repo map + knowledge graph |
| `mnemo_intelligence` | Full code intelligence report |
| `mnemo_similar` | Find similar implementations |
| `mnemo_context_for_task` | Retrieve context scoped to active task |

### Multi-Repo

| Tool | Description |
|------|-------------|
| `mnemo_links` | Show linked repos |
| `mnemo_cross_search` | Search across all linked repos |
| `mnemo_cross_impact` | Cross-repo impact analysis |

### Safety & Quality

| Tool | Description |
|------|-------------|
| `mnemo_check_security` | Scan for security issues |
| `mnemo_add_security_pattern` | Add custom security pattern |
| `mnemo_breaking_changes` | Detect breaking changes against baseline |
| `mnemo_add_regression` | Record regression risk for a file |
| `mnemo_check_regressions` | Check file regression risks |
| `mnemo_drift` | Detect architecture drift |
| `mnemo_dead_code` | Detect unused code (in-memory scan, <0.3s) |
| `mnemo_health` | Code health report |

### Git & Workflow

| Tool | Description |
|------|-------------|
| `mnemo_commit_message` | Generate commit message from staged changes |
| `mnemo_pr_description` | Generate PR description |
| `mnemo_hooks_install` | Install pre-commit hooks |
| `mnemo_check` | Run pre-commit validations |
| `mnemo_add_correction` | Store AI correction for learning |
| `mnemo_corrections` | Show stored corrections |
| `mnemo_velocity` | Development velocity metrics |

### Knowledge & APIs

| Tool | Description |
|------|-------------|
| `mnemo_knowledge` | Search team knowledge base |
| `mnemo_discover_apis` | Discover all API endpoints |
| `mnemo_search_api` | Search for specific endpoint |

### Team & Operations

| Tool | Description |
|------|-------------|
| `mnemo_team` | Team expertise map |
| `mnemo_who_touched` | Who last modified a file |
| `mnemo_add_error` | Store error → cause → fix |
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

---

## How to Use in Chat

Just ask naturally:

| What you want | What to ask |
|---------------|-------------|
| Project overview | "What do you know about this project?" |
| Code relationships | "What implements IPayerHandler?" |
| Impact analysis | "What breaks if I change CosmosDbService?" |
| Plan work | "We need to migrate to SOAP — here are the steps..." |
| Plan status | "What's the plan status?" |
| Code details | "Show me the AuthorizationService methods" |
| Follow patterns | "I need to add a new payer handler" |
| Architecture | "What's the architecture?" |
| Dead code | "Find unused code" |
| Security | "Run a security scan" |
| Cross-repo | "Find auth code across all services" |

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `mnemo init` | Initialize Mnemo in current directory |
| `mnemo init --client all` | Initialize for all AI clients |
| `mnemo ui` | Open the Mnemo dashboard in your browser |
| `mnemo doctor` | Diagnose setup |
| `mnemo status` | Quick health check |
| `mnemo recall` | Show stored memory |
| `mnemo map` | Refresh repo map + knowledge graph |
| `mnemo remember "text"` | Store a note |
| `mnemo update` | Update to latest version |
| `mnemo reset` | Wipe all Mnemo data |
| `mnemo link <path>` | Link a sibling repo |
| `mnemo link --discover <dir>` | Auto-discover and link repos |
| `mnemo unlink <name>` | Remove a linked repo |
| `mnemo links` | Show linked repos |

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│  MCP Tools (48 tools via tool_registry.py)          │
├─────────────────────────────────────────────────────┤
│  Response Enrichment (enrichment.py)                │
│  → plan hints, regression warnings, decision refs   │
├─────────────────────────────────────────────────────┤
│  Knowledge Graph (graph/)                           │
│  → LocalGraph (NetworkX) + WorkspaceGraph           │
├─────────────────────────────────────────────────────┤
│  Plan Mode (plan/)                                  │
│  → auto-create, auto-complete, TASKS.md sync        │
├─────────────────────────────────────────────────────┤
│  Semantic Search (vector_index/ + ChromaDB)          │
├─────────────────────────────────────────────────────┤
│  Code Parsing (repo_map.py + analyzers/)            │
│  → tree-sitter (14 languages) + Roslyn              │
├─────────────────────────────────────────────────────┤
│  Storage (storage.py → .mnemo/*.json)               │
└─────────────────────────────────────────────────────┘
```

**Storage layout:**
```
.mnemo/
├── summary.md       ← detailed code map (for lookup)
├── tree.md          ← compact tree (for recall)
├── graph.json       ← knowledge graph (NetworkX)
├── graph_meta.json  ← graph stats
├── hashes.json      ← change detection
├── memory.json      ← memories
├── decisions.json   ← decisions
├── context.json     ← project metadata
├── plans.json       ← tracked plans
├── links.json       ← linked repos
├── index/chroma/    ← semantic search index
└── knowledge/       ← team docs
```

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Core | Python 3.10+ |
| MCP Server | JSON-RPC over stdin/stdout |
| Knowledge Graph | NetworkX (serialized to JSON) |
| Code Parsing | tree-sitter (14 languages) + Roslyn (.NET 8 for C#) |
| Semantic Search | ChromaDB + all-MiniLM-L6-v2 (ONNX) |
| Keyword Fallback | Custom sparse embedding (IDF-weighted token overlap) |
| Storage | JSON files in `.mnemo/` |
| Change Detection | mtime-based + git rename tracking |
| Team Graph | GitPython (git log analysis) |
| CLI | Click |
| Binary Distribution | PyInstaller |
| VS Code Extension | TypeScript |
| CI/CD | GitHub Actions |

### Dependencies

**Required:**
- `click` — CLI framework
- `tree-sitter` + language grammars (Python, JS, TS, Go, C#, Java, Rust)
- `gitpython` — git history analysis
- `networkx` — knowledge graph

**Auto-installed on first use:**
- `chromadb` — vector database for semantic search

**Optional (`pip install mnemo[all-languages]`):**
- `tree-sitter-ruby`, `tree-sitter-php`, `tree-sitter-c`, `tree-sitter-cpp`, `tree-sitter-kotlin`, `tree-sitter-swift`, `tree-sitter-scala`

**Optional (detected at runtime):**
- .NET SDK 8+ — enables Roslyn analyzer for richer C# analysis

---

## Supported Languages

### Core (included with `pip install mnemo`)

| Language | Extensions |
|----------|------------|
| Python | `.py` |
| JavaScript | `.js`, `.jsx` |
| TypeScript | `.ts`, `.tsx` |
| Go | `.go` |
| C# | `.cs` (+ Roslyn enhanced analysis) |
| Java | `.java` |
| Rust | `.rs` |

### Optional (install with `pip install mnemo[all-languages]`)

| Language | Extensions |
|----------|------------|
| Ruby | `.rb` |
| PHP | `.php` |
| C | `.c`, `.h` |
| C++ | `.cpp`, `.cc`, `.hpp` |
| Kotlin | `.kt`, `.kts` |
| Swift | `.swift` |
| Scala | `.scala`, `.sc` |

Optional languages are gracefully skipped if their grammar is not installed — no errors, no crashes.

---

## Requirements

- Python 3.10+
- Git (for rename/delete detection and team graph)
- Any AI client with MCP support (Amazon Q, Cursor, Claude Code, Kiro, Copilot, or generic)

---

## Dashboard UI

Mnemo includes a built-in web dashboard to visualize your project's knowledge graph, memory, linked repos, and more.

```bash
mnemo ui                  # opens http://localhost:7890
mnemo ui --port 9000      # custom port
mnemo ui --no-open        # don't auto-open browser
```

### What the dashboard shows

| Section | Content |
|---------|--------|
| Overview | Stat cards (memories, graph nodes, linked repos, tasks, decisions) + activity timeline |
| Knowledge Graph | Interactive force-directed visualization with search and type filter |
| Memory | All memories with category filter badges + decisions log |
| Linked Repos | Cards showing each repo's name, path, indexed/exists status |
| Tasks | Active/completed tasks with status indicators |
| Health | Code complexity hotspots, large files, god classes |
| APIs | Discovered API endpoints |
| Team | Git-based expertise map |
| Incidents & Errors | Operational memory with severity badges |
| Knowledge Base | Rendered markdown from `.mnemo/knowledge/` |

Dark theme, glassmorphism design, zero dependencies (Tailwind + vis-network from CDN).

---

## Dashboard UI

Mnemo includes a built-in web dashboard to visualize your project's knowledge graph, memory, linked repos, and more.

```bash
mnemo ui                  # opens http://localhost:7890
mnemo ui --port 9000      # custom port
mnemo ui --no-open        # don't auto-open browser
```

Dark theme, glassmorphism design, zero dependencies (Tailwind + vis-network from CDN).

---

## Roadmap

| Feature | Status |
|---------|--------|
| Knowledge Graph (Local + Workspace) | ✅ Done |
| Plan Mode (auto-create, auto-complete) | ✅ Done |
| Response Enrichment | ✅ Done |
| Multi-Language Support (14 languages) | ✅ Done |
| Dashboard UI (`mnemo ui`) | ✅ Done |
| Team Server (`mnemo serve`) | 🔲 Next |
| Convention Enforcer | 🔲 Planned |
| Smart Code Review | 🔲 Planned |
| Enterprise (Auth, Audit, Neo4j) | 🔲 Future |
