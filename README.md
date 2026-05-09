# Mnemo

Persistent memory, code intelligence, and API discovery for AI coding assistants. One command gives Amazon Q, Cursor, Claude Code, and other MCP clients project context across chat sessions - no re-reading files, no lost context.

## Mnemo in Simple Words

Mnemo is your AI agent's project memory.

- It remembers important decisions and past fixes.
- It keeps a map of your codebase so the agent can navigate quickly.
- It helps the agent answer questions about architecture, APIs, tests, and patterns.
- It works across chats, so you do not repeat project context every time.

## Mnemo in Technical Terms

Mnemo is a local-first MCP server (`mnemo-mcp`) plus repo-side data/indexing.

- It exposes MCP tools for memory, retrieval, architecture analysis, API discovery, task context, incidents, reviews, and diagnostics.
- It builds and updates a structured repo summary and hash index in `.mnemo/`.
- It supports semantic retrieval (optional ChromaDB) with keyword fallback.
- It injects client instructions/context files (for supported AI clients) and updates them as memory changes.

## What it does

- **Persistent Memory** — Stores decisions, patterns, preferences, and chat summaries across sessions
- **Repo Map** — Parses your entire codebase and stores class structures, interfaces, and relationships
- **Code Intelligence** — Detects architecture, dependencies, patterns, ownership, and similar implementations
- **Knowledge Base** — Searchable team knowledge from markdown files (runbooks, standards, gotchas)
- **API Discovery** — Parses OpenAPI/Swagger specs and controller annotations to build a complete API catalog
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

### Step 1: Install Mnemo

```bash
pip install mnemo
```

Or from source:

```bash
git clone <repo-url>
cd Mnemo
pip install .
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

### Step 2: Initialize in your repo

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
3. Detects code patterns and conventions
4. Creates a knowledge base directory
5. Installs the right client context file, such as `.amazonq/rules/mnemo.md`, `.cursorrules`, or `CLAUDE.md`
6. Configures the MCP server in the selected client's MCP config

### Step 3: Restart your IDE

Restart your IDE or reload your AI client extension to pick up the new MCP server.

If setup does not look right, run:

```bash
mnemo doctor --client all
```

## That's it

Every new AI chat with a configured client will now:
1. Automatically recall project context before answering
2. Know the full code structure without reading files
3. Remember what happened in previous chats
4. Have access to all stored decisions and memory
5. Auto-save conversation summaries for future sessions

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

## Optional Extras

- `pip install "mnemo[semantic]"` enables ChromaDB-backed semantic indexing.
- `pip install "mnemo[binary]"` installs PyInstaller tooling for binary builds.
- Use `scripts/build_binary.ps1` (Windows) or `pyinstaller pyinstaller.spec` directly.

## VS Code Extension MVP

A starter extension is available under `vscode-extension/` with commands to:
- detect Mnemo installation
- initialize workspace (`mnemo init`)
- show status (`mnemo doctor`)
- refresh index (`mnemo map`)

## What Amazon Q Sees

### On every new chat (from the rule file + recall):

```markdown
# Project Context
- repo_root: /path/to/project
- patterns: [Repository pattern, Strategy/Handler pattern, DI container, ...]

# Decisions
- Use PostgreSQL — team expertise, ACID compliance
- Use handler pattern for vendor-specific logic

# Memory
- User prefers clean architecture
- Auth service uses cache-aside pattern with 5min TTL
- Last chat: discussed adding new vendor handler

# Repo Map
BackendService/
  Controllers/OrderController.cs → `OrderController : ControllerBase`
  Services/OrderService.cs → `OrderService : IOrderService`
AuthService/
  Controllers/AuthController.cs → `AuthController : ControllerBase`
  Services/TokenService.cs → `TokenService : ITokenService`
  ...
```

### When Q calls `mnemo_intelligence`:

```markdown
# Code Intelligence

## Patterns & Conventions
- Controllers inherit from ControllerBase (API controllers)
- Repository pattern with interfaces (9 interfaces, 17 implementations)
- Strategy/Handler pattern (12 handlers found)
- Dependency injection via built-in DI container
- Testing with xUnit + Moq + FluentAssertions

## Dependencies
AuthService: Microsoft.Identity, Polly, Newtonsoft.Json, ...
OrderService: EntityFramework, Azure.Identity, ...

## Service Architecture
APIGateway → auth, orders, payments, notifications
```

### When Q calls `mnemo_discover_apis`:

```markdown
# API Discovery

## Controller Endpoints

### OrderService
- `GET /api/orders` → GetAll()
- `POST /api/orders` → Create()
- `GET /api/orders/{id}` → GetById()

### AuthService
- `POST /api/auth/login` → Login()
- `POST /api/auth/refresh` → RefreshToken()
- `DELETE /api/auth/cache` → ClearCache()
```

### When Q calls `mnemo_similar("Handler")`:

```markdown
# Similar to 'Handler'

- PaymentService/Handlers/StripeHandler.cs — `public class StripeHandler : BasePaymentHandler`
- PaymentService/Handlers/PayPalHandler.cs — `public class PayPalHandler : BasePaymentHandler`
- PaymentService/Handlers/SquareHandler.cs — `public class SquareHandler : BasePaymentHandler`
```

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
| Onboarding | "Give me a project overview for onboarding" |
| Task tracking | "I'm working on JIRA-456" |
| Error lookup | "Have we seen this NullReferenceException before?" |
| Incidents | "We had an outage in the auth service last week" |
| Code review | "Store this review feedback for future reference" |

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
- Technical: semantic index is available with `mnemo[semantic]`; fallback keyword retrieval still works without ChromaDB.

### 4) Knowledge base search
- Simple: your internal runbooks/standards become searchable by the agent.
- Technical: markdown in `.mnemo/knowledge/` is chunked by headings and queried through `mnemo_knowledge`.

### 5) API discovery
- Simple: your agent can list endpoints and find relevant APIs quickly.
- Technical: OpenAPI specs and controller annotations are parsed; `mnemo_discover_apis` and `mnemo_search_api` expose structured and searchable API context.

### 6) Task-aware context
- Simple: when you set a task, the agent focuses on relevant code automatically.
- Technical: `mnemo_task` sets active task metadata and `mnemo_context_for_task` performs task-scoped retrieval.

### 7) Engineering memory beyond code
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

## CLI Commands

| Command | Description |
|---------|-------------|
| `mnemo init` | Initialize Mnemo in current directory |
| `mnemo init --client all` | Initialize Mnemo for all supported AI clients |
| `mnemo doctor` | Diagnose install, repo, and MCP client setup |
| `mnemo recall` | Show all stored memory (what Q sees) |
| `mnemo map` | Manually refresh the repo map |
| `mnemo remember "text"` | Store a note in memory |
| `mnemo reset` | Wipe all Mnemo data and start fresh |

---

## Supported Languages

- C# (.cs)
- Python (.py)
- JavaScript (.js, .jsx)
- TypeScript (.ts, .tsx)
- Go (.go)

---

## Requirements

- Python 3.10+
- Git (for rename/delete detection)
- Any AI client with MCP support (Amazon Q, Cursor, Claude Code, Kiro, Copilot, or generic MCP client)

---

## Roadmap

### Future Features (Decided)

| Feature | Description |
|---------|-------------|
| **Convention Enforcer** | Detect patterns and enforce them when Q generates code. "All handlers must inherit BaseHandler." |
| **Multi-repo Awareness** | Cross-repo context. Know that auth service in repo A is consumed by repos B and C. |
| **Migration Assistant** | Track migration progress (e.g. .NET 6 → 8). Q knows what's migrated and what's left. |
