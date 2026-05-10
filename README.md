# Mnemo

Persistent memory, code intelligence, and API discovery for AI coding assistants. One command gives Amazon Q, Cursor, Claude Code, and other MCP clients project context across chat sessions - no re-reading files, no lost context.

## Mnemo in Simple Words

Mnemo is your AI agent's project memory.

- It remembers important decisions and past fixes.
- It keeps a map of your codebase so the agent can navigate quickly.
- It helps the agent answer questions about architecture, APIs, tests, and patterns.
- It works across chats, so you do not repeat project context every time.
- It searches across multiple repos so the agent knows your full platform.

## Mnemo in Technical Terms

Mnemo is a local-first MCP server (`mnemo-mcp`) plus repo-side data/indexing.

- It exposes MCP tools for memory, retrieval, architecture analysis, API discovery, task context, incidents, reviews, and diagnostics.
- It builds and updates a structured repo summary and hash index in `.mnemo/`.
- It supports semantic retrieval (ChromaDB auto-installed on first use) with keyword fallback.
- It supports multi-repo workspaces with cross-repo search and impact analysis.
- It injects client instructions/context files (for supported AI clients) and updates them as memory changes.

## What it does

- **Persistent Memory** — Stores decisions, patterns, preferences, and chat summaries across sessions
- **Repo Map** — Parses your entire codebase and stores class structures, interfaces, and relationships
- **Code Intelligence** — Detects architecture, dependencies, patterns, ownership, and similar implementations
- **Semantic Search** — Finds code by meaning, not just filename (powered by ChromaDB)
- **Multi-Repo Workspace** — Search across linked repos, cross-repo impact analysis
- **Knowledge Base** — Searchable team knowledge from markdown files (runbooks, standards, gotchas)
- **API Discovery** — Parses OpenAPI/Swagger specs and controller annotations to build a complete API catalog
- **Auto-Remember** — Automatically saves meaningful findings to memory for future chats
- **Auto-refresh** — Detects file changes (via content hash), renames (via git), and deletions
- **Zero friction** — One `mnemo init` and it works forever

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
brew tap nikhil1057/tap
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
git clone https://github.com/nikhil1057/Mnemo.git
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

> **Note (Windows):** If `mnemo` is not found after install, add your Python Scripts directory to PATH. Common locations are `$env:APPDATA\Python\Python312\Scripts`, `$env:APPDATA\Python\Python311\Scripts`, and `$env:APPDATA\Python\Python310\Scripts`.

### Option D: Standalone binary (no Python needed)

Download from [GitHub Releases](https://github.com/nikhil1057/Mnemo/releases):

| Platform | Download |
|----------|----------|
| macOS (Apple Silicon) | `mnemo-macos-arm64` |
| macOS (Intel) | `mnemo-macos-x64` |
| Linux | `mnemo-linux-x64` |
| Windows | `mnemo-windows-x64.exe` |

Or use the install script:

```bash
# macOS/Linux
curl -fsSL https://raw.githubusercontent.com/nikhil1057/Mnemo/main/scripts/install.sh | sh

# Windows (PowerShell)
irm https://raw.githubusercontent.com/nikhil1057/Mnemo/main/scripts/install.ps1 | iex
```

Then:

```bash
cd your-project
mnemo init
```

### Initialize your repo

After installing via any method above:

```bash
cd your-project
mnemo init
```

By default this configures Amazon Q. You can target another client, or configure every supported client at once:

```bash
mnemo init --client cursor
mnemo init --client claude-code
mnemo init --client all
```

Supported values are `amazonq`, `cursor`, `claude-code`, `kiro`, `copilot`, `generic`, and `all`.

That's it. This command:
1. Creates `.mnemo/` folder (added to `.gitignore` automatically)
2. Generates a compact repo map of your entire codebase
3. Indexes code into semantic search (ChromaDB auto-installs on first use)
4. Detects code patterns and conventions
5. Creates a knowledge base directory
6. Installs the right client context file, such as `.amazonq/rules/mnemo.md`, `.cursorrules`, or `CLAUDE.md`
7. Configures the MCP server in the selected client's MCP config

### Restart your IDE

Restart your IDE or reload your AI client extension to pick up the new MCP server.

If setup does not look right, run:

```bash
mnemo doctor --client all
```

### Check status

```bash
mnemo status
```

Output:
- `✅ Mnemo active — MCP server responding`
- `⚠️  Mnemo initialized but MCP server not responding — restart your IDE`
- `❌ Not initialized. Run: mnemo init`

## That's it

Every new AI chat with a configured client will now:
1. Automatically recall project context before answering
2. Know the full code structure without reading files
3. Remember what happened in previous chats
4. Have access to all stored decisions and memory
5. Auto-save meaningful findings for future sessions
6. Search across linked repos when code lives elsewhere

---

## Multi-Repo Workspace

Mnemo can search across multiple repositories. This is useful when your platform spans several repos (auth-service, order-service, frontend, etc.).

### Link repos

```bash
# Link a specific repo
mnemo link ../auth-service

# Auto-discover and link all repos under a directory
mnemo link --discover ~/CodeRepo

# Auto-discover AND initialize all found repos
mnemo link --discover ~/CodeRepo --init

# Remove a link
mnemo unlink auth-service

# Show linked repos and their status
mnemo links
```

### What it enables in chat

| What you ask | What happens |
|---|---|
| "Find authentication code across all services" | Searches this repo + all linked repos |
| "What breaks if I change the token format?" | Cross-repo impact analysis |
| "What APIs does the auth service expose?" | Searches linked auth-service's API index |
| "Show me linked repos" | Lists all linked repos with status |

### How it works

Each repo keeps its own `.mnemo/` index. When you query, Mnemo searches the local index first, then fans out to linked repos' indexes. Results are merged and ranked by relevance.

```
your-project/.mnemo/links.json → ["../auth-service", "../order-service"]
```

### IDE Setup for cross-repo file reading

If your AI client needs to read actual source files in linked repos (not just index data), enable read access outside your workspace:

**VS Code (Amazon Q):** Settings → "Allow read-only tools outside your workspace" → Enable

---

## Semantic Search

Mnemo uses ChromaDB for semantic code search. This means you can find code by **meaning**, not just filename or keyword.

### Examples

| Query | Finds |
|---|---|
| "token refresh" | `getToken()`, `acquireTokenSilent()`, `ClientCredentialTokenService` |
| "error handling" | retry pipelines, DelegatingHandlers, catch blocks |
| "database access" | CosmosDbService, repositories, connection code |

### How it works

- ChromaDB auto-installs on first `mnemo init` (no manual setup)
- Code is chunked at class/function boundaries and embedded
- Queries match by semantic similarity, not just text overlap
- Falls back to keyword matching if ChromaDB is unavailable

### No ChromaDB? Still works

Without ChromaDB, Mnemo uses a keyword-based fallback (token overlap scoring). It's less accurate but requires zero dependencies beyond the base install.

---

## Using Mnemo With AI Agents

You can work naturally with your AI assistant; you do not need to memorize tool names.

### Setup per agent/client

- `mnemo init --client amazonq`
- `mnemo init --client cursor`
- `mnemo init --client claude-code`
- `mnemo init --client kiro`
- `mnemo init --client copilot`
- `mnemo init --client generic`
- `mnemo init --client all` (configure everything in one run)

### Recommended first-chat prompt

Use this once after setup/restart:

```text
Use Mnemo context for this repo first, then help me with my task.
```

### Daily workflow

1. Start task context:
   - "I'm working on ABC-123: migrate auth token validation."
2. Ask implementation/analysis questions naturally:
   - "Show me similar handlers and where to plug a new one."
3. Persist important outcomes:
   - "Remember we chose Redis cache-aside for token introspection."
4. Capture delivery hygiene:
   - "Store this review summary."
   - "Record this production incident."

---

## MCP Tools

### Memory & Context

| Tool | Description |
|------|-------------|
| `mnemo_recall` | Load all stored memory, decisions, context, and repo map |
| `mnemo_remember` | Save important information for future chat sessions |
| `mnemo_decide` | Record an architectural or design decision with reasoning |
| `mnemo_context` | Save/update project metadata (tech stack, conventions) |

### Code Understanding

| Tool | Description |
|------|-------------|
| `mnemo_lookup` | Get method-level details for a specific file or folder |
| `mnemo_map` | Regenerate the repo map after code changes |
| `mnemo_intelligence` | Full code intelligence report (architecture, patterns, dependencies, ownership) |
| `mnemo_similar` | Find similar implementations to follow as patterns |
| `mnemo_context_for_task` | Retrieve semantic context scoped to the active task |

### Multi-Repo

| Tool | Description |
|------|-------------|
| `mnemo_links` | Show all linked repos in the workspace |
| `mnemo_cross_search` | Search across this repo AND all linked repos |
| `mnemo_cross_impact` | Cross-repo impact analysis — what breaks everywhere if you change something |

### Knowledge & APIs

| Tool | Description |
|------|-------------|
| `mnemo_knowledge` | Search the team knowledge base (or list all files) |
| `mnemo_discover_apis` | Discover all API endpoints from controllers and OpenAPI specs |
| `mnemo_search_api` | Search for a specific endpoint, schema, or service |

### Code Review

| Tool | Description |
|------|-------------|
| `mnemo_add_review` | Store a code review summary with feedback and outcome |
| `mnemo_reviews` | Show code review history |

### Error Memory

| Tool | Description |
|------|-------------|
| `mnemo_add_error` | Store an error → cause → fix mapping |
| `mnemo_search_errors` | Search known errors (use when hitting a bug to check if it's been seen before) |

### Dependency Graph

| Tool | Description |
|------|-------------|
| `mnemo_dependencies` | Show the full service dependency graph |
| `mnemo_impact` | Impact analysis — what breaks if you change a service or file |

### Onboarding

| Tool | Description |
|------|-------------|
| `mnemo_onboarding` | Generate a complete project onboarding guide for new team members |

### Sprint/Task Context

| Tool | Description |
|------|-------------|
| `mnemo_task` | Set or get the current task/ticket being worked on |
| `mnemo_task_done` | Mark a task as completed |

### Test Intelligence

| Tool | Description |
|------|-------------|
| `mnemo_tests` | Show which tests cover a file, or get overall test coverage summary |

### Code Health

| Tool | Description |
|------|-------------|
| `mnemo_health` | Code health report — complexity hotspots, large files, potential god classes |

### Team Knowledge Graph

| Tool | Description |
|------|-------------|
| `mnemo_team` | Show team expertise map — who knows what based on git history |
| `mnemo_who_touched` | Find who last modified a specific file |

### Incident Memory

| Tool | Description |
|------|-------------|
| `mnemo_add_incident` | Record a production incident with root cause and fix |
| `mnemo_incidents` | Search or list production incidents |

---

## How to Use in Chat

You don't need to mention "mnemo" — just ask naturally:

| What you want | What to ask |
|---------------|-------------|
| Project overview | "What do you know about this project?" |
| Code details | "Show me the AuthorizationService methods" |
| Follow patterns | "I need to add a new payer handler, show me existing ones" |
| Architecture | "What's the architecture of this project?" |
| APIs | "What API endpoints exist?" |
| Knowledge | "What's in the knowledge base?" |
| Save context | "Remember that we decided to use Redis for caching" |
| Code health | "What's the code health of this project?" |
| Test coverage | "What tests cover AuthorizationService?" |
| Team expertise | "Who knows about the payment service?" |
| Impact analysis | "What breaks if I change AuthService?" |
| Cross-repo search | "Find authentication code across all services" |
| Cross-repo impact | "What breaks in other repos if I change the token format?" |
| Onboarding | "Give me a project overview for onboarding" |
| Task tracking | "I'm working on JIRA-456" |
| Error lookup | "Have we seen this NullReferenceException before?" |
| Incidents | "We had an outage in the auth service last week" |
| Code review | "Store this review feedback for future reference" |

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `mnemo init` | Initialize Mnemo in current directory |
| `mnemo init --client all` | Initialize Mnemo for all supported AI clients |
| `mnemo doctor` | Diagnose install, repo, and MCP client setup |
| `mnemo status` | Quick check — is Mnemo active and MCP responding? |
| `mnemo recall` | Show all stored memory (what Q sees) |
| `mnemo map` | Manually refresh the repo map and semantic index |
| `mnemo remember "text"` | Store a note in memory |
| `mnemo reset` | Wipe all Mnemo data and client context files |
| `mnemo link <path>` | Link a sibling repo for cross-repo queries |
| `mnemo link --discover <dir>` | Auto-discover and link all repos under a directory |
| `mnemo link --discover <dir> --init` | Discover, link, AND initialize all repos |
| `mnemo unlink <name>` | Remove a linked repo |
| `mnemo links` | Show all linked repos and their status |

---

## Feature Guide: Simple + Technical

### 1) Memory and decisions
- Simple: your agent remembers project decisions and team preferences.
- Technical: persisted in `.mnemo/memory.json`, `.mnemo/decisions.json`, `.mnemo/context.json` via `mnemo_recall`, `mnemo_remember`, `mnemo_decide`, `mnemo_context`.

### 2) Repo understanding
- Simple: your agent can explain "where things are" quickly.
- Technical: Mnemo parses supported languages and generates `.mnemo/summary.md` plus `.mnemo/hashes.json` for change detection; tools include `mnemo_map`, `mnemo_lookup`.

### 3) Semantic code retrieval
- Simple: "find me code similar to this feature" works by meaning, not just exact name.
- Technical: ChromaDB auto-installs on first `mnemo init`. Code is chunked at class/function boundaries, embedded with all-MiniLM-L6-v2, and stored in `.mnemo/index/chroma/`. Falls back to keyword scoring without ChromaDB.

### 4) Multi-repo workspace
- Simple: your agent can search code across all your team's repos at once.
- Technical: `.mnemo/links.json` stores paths to sibling repos. `mnemo_cross_search` and `mnemo_cross_impact` fan out queries to linked repos' indexes. Each repo maintains its own `.mnemo/` independently.

### 5) Knowledge base search
- Simple: your internal runbooks/standards become searchable by the agent.
- Technical: markdown in `.mnemo/knowledge/` is chunked by headings and queried through `mnemo_knowledge`.

### 6) API discovery
- Simple: your agent can list endpoints and find relevant APIs quickly.
- Technical: OpenAPI specs and controller annotations are parsed; `mnemo_discover_apis` and `mnemo_search_api` expose structured and searchable API context.

### 7) Task-aware context
- Simple: when you set a task, the agent focuses on relevant code automatically.
- Technical: `mnemo_task` sets active task metadata and `mnemo_context_for_task` performs task-scoped retrieval.

### 8) Auto-remember
- Simple: the agent automatically saves important findings so you never lose context.
- Technical: the rule file instructs the AI to call `mnemo_remember` after code changes, bug fixes, architecture decisions, or any analysis that produced non-obvious insights.

### 9) Engineering memory beyond code
- Simple: your agent remembers incidents, errors, reviews, ownership, and health signals.
- Technical: dedicated MCP tools persist/query this operational memory (`mnemo_add_error`, `mnemo_incidents`, `mnemo_reviews`, `mnemo_team`, `mnemo_health`, etc.).

## Knowledge Base

Add markdown files to `.mnemo/knowledge/` for team knowledge that Q should know:

```
.mnemo/knowledge/
├── architecture.md    ← system design, service boundaries
├── runbooks.md        ← deployment, debugging procedures
├── standards.md       ← coding conventions, naming rules
├── onboarding.md      ← project overview for new members
└── gotchas.md         ← common pitfalls and workarounds
```

Q can search these with `mnemo_knowledge`.

---

## Architecture

```
┌─────────────────────────────────────────────┐
│                YOUR IDE                      │
│                                             │
│  Amazon Q ←── reads .amazonq/rules/mnemo.md │
│      │                                      │
│      │ JSON-RPC (stdin/stdout)              │
│      ▼                                      │
│  mnemo-mcp (background process)             │
│      │                                      │
└──────┼──────────────────────────────────────┘
       │
       ▼
  .mnemo/
  ├── summary.md      ← compact code map
  ├── hashes.json     ← change detection
  ├── memory.json     ← chat summaries & notes
  ├── decisions.json  ← architectural decisions
  ├── context.json    ← project metadata
  ├── links.json      ← linked sibling repos
  ├── index/chroma/   ← semantic search index
  └── knowledge/      ← team docs (searchable)
```

**Config files:**

| File | Purpose |
|------|---------|
| `~/.aws/amazonq/mcp.json` | Registers mnemo-mcp server with Amazon Q |
| `~/.cursor/mcp.json` | Registers mnemo-mcp server with Cursor |
| `~/.claude/mcp.json` | Registers mnemo-mcp server with Claude Code |
| `.amazonq/rules/mnemo.md` | Amazon Q auto-loaded instructions + embedded context |
| `.cursorrules` | Cursor instructions + embedded context |
| `CLAUDE.md` | Claude Code instructions + embedded context |
| `MNEMO.md` | Generic MCP client instructions + embedded context |
| `.mnemo/*` | All stored data (gitignored) |

---

## Optional Extras

- `pip install "mnemo[semantic]"` explicitly installs ChromaDB (auto-installed on first use anyway).
- `pip install "mnemo[binary]"` installs PyInstaller tooling for binary builds.
- Use `scripts/build_binary.ps1` (Windows) or `pyinstaller pyinstaller.spec` directly.

## VS Code Extension

A VS Code extension is available under `vscode-extension/` that provides:
- Auto-detection and download of the Mnemo binary
- One-click workspace initialization (prompts on first open)
- Status bar indicator ("Mnemo: Active")
- Commands: Initialize Workspace, Show Status, Refresh Index

## Supported Languages

- C# (.cs)
- Python (.py)
- JavaScript (.js, .jsx)
- TypeScript (.ts, .tsx)
- Go (.go)

---

## Requirements

- Python 3.10+
- Git (for rename/delete detection and team graph)
- Any AI client with MCP support (Amazon Q, Cursor, Claude Code, Kiro, Copilot, or generic MCP client)

---

## Smart Analyzer Selection

Mnemo automatically picks the best code analyzer based on your tech stack. You don't configure anything — it just works.

| Language | Best Analyzer | Fallback | What you get |
|----------|--------------|----------|-------------|
| C# | **Roslyn** (needs .NET SDK) | tree-sitter | Full return types, parameter names, generics, inheritance chains, DI dependencies |
| Python | tree-sitter | — | Classes, functions, decorators, imports |
| JavaScript/TypeScript | tree-sitter | — | Classes, methods, arrow functions, exports |
| Go | tree-sitter | — | Functions, methods with receivers, structs |

### How it works

During `mnemo init`:
1. Detects `.csproj`/`.sln` files → checks if `dotnet` is on PATH → uses Roslyn
2. If .NET SDK is not available → falls back to tree-sitter (still works, less detail)
3. Results are merged into the same index regardless of which analyzer produced them

### Roslyn vs tree-sitter output

**Tree-sitter:**
```
class AuthorizationService : IAuthorizationService
  - ProcessAuthorizationRequestAsync
  - ValidateRequest
```

**Roslyn:**
```
class AuthorizationService : IAuthorizationService
  - Task<object?> ProcessAuthorizationRequestAsync(string payerId, string payerName, object request, string correlationId, CancellationToken ct)
  - List<string> ValidateRequest(string payerId, object request)
  - AuthorizationService(IPayerHandlerFactory handlerFactory, IPayerLookupRepository payerLookupRepo, IAuditLogRepository auditLogRepository, ILogger<AuthorizationService> logger)
```

The user sees no difference in how they ask questions — just better answers.

---

## Tech Stack

What Mnemo is built with:

| Component | Technology |
|-----------|------------|
| Core | Python 3.10+ |
| MCP Server | JSON-RPC over stdin/stdout |
| Code Parsing (default) | tree-sitter (Python, C#, JS/TS, Go) |
| Code Parsing (C# enhanced) | Roslyn / Microsoft.CodeAnalysis (.NET 8) |
| Semantic Search | ChromaDB + all-MiniLM-L6-v2 (ONNX) |
| Keyword Fallback | Custom sparse embedding (token overlap scoring) |
| Storage | JSON files in `.mnemo/` |
| Change Detection | MD5 content hashing + git rename tracking |
| Team Graph | GitPython (git log analysis) |
| CLI | Click |
| Binary Distribution | PyInstaller |
| VS Code Extension | TypeScript |
| CI/CD | GitHub Actions |

### Dependencies

**Required:**
- `click` — CLI framework
- `tree-sitter` + language grammars (Python, JS, TS, Go, C#)
- `gitpython` — git history analysis

**Auto-installed on first use:**
- `chromadb` — vector database for semantic search

**Optional (detected at runtime):**
- .NET SDK 8+ — enables Roslyn analyzer for richer C# analysis

---

## Roadmap

### Future Features (Decided)

| Feature | Description |
|---------|-------------|
| **Smart Code Review** | Extract review decisions from git/PR comments. Pre-commit validation against stored feedback. Review-aware code generation. |
| **Convention Enforcer** | Detect patterns and enforce them when Q generates code. "All handlers must inherit BaseHandler." |
| **Team Server (`mnemo serve`)** | Central server for team-wide shared memory, cross-repo indexing without local clones. |
| **Migration Assistant** | Track migration progress (e.g. .NET 6 → 8). Q knows what's migrated and what's left. |
