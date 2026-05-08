# Mnemo

Persistent memory, code intelligence, and API discovery for Amazon Q chats. One command gives Amazon Q full project context across every chat session — no re-reading files, no lost context.

## What it does

- **Persistent Memory** — Stores decisions, patterns, preferences, and chat summaries across sessions
- **Repo Map** — Parses your entire codebase and stores class structures, interfaces, and relationships
- **Code Intelligence** — Detects architecture, dependencies, patterns, ownership, and similar implementations
- **Knowledge Base** — Searchable team knowledge from markdown files (runbooks, standards, gotchas)
- **API Discovery** — Parses OpenAPI/Swagger specs and controller annotations to build a complete API catalog
- **Auto-refresh** — Detects file changes (via content hash), renames (via git), and deletions
- **Zero friction** — One `mnemo init` and it works forever

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

### Step 2: Initialize in your repo

```bash
cd your-project
mnemo init
```

That's it. This single command:
1. Creates `.mnemo/` folder (added to `.gitignore` automatically)
2. Generates a compact repo map of your entire codebase
3. Detects code patterns and conventions
4. Creates a knowledge base directory
5. Installs an auto-recall rule at `.amazonq/rules/mnemo.md`
6. Configures the MCP server in `~/.aws/amazonq/mcp.json`

### Step 3: Restart your IDE

Restart your IDE (or reload the Amazon Q extension) to pick up the new MCP server.

## That's it

Every new Amazon Q chat will now:
1. Automatically recall project context before answering
2. Know the full code structure without reading files
3. Remember what happened in previous chats
4. Have access to all stored decisions and memory
5. Auto-save conversation summaries for future sessions

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
| `.amazonq/rules/mnemo.md` | Auto-loaded instructions + embedded context |
| `.mnemo/*` | All stored data (gitignored) |

---

## CLI Commands

| Command | Description |
|---------|-------------|
| `mnemo init` | Initialize Mnemo in current directory |
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
- Amazon Q IDE extension with MCP support

---

## Roadmap

### Future Features (Decided)

| Feature | Description |
|---------|-------------|
| **Convention Enforcer** | Detect patterns and enforce them when Q generates code. "All handlers must inherit BaseHandler." |
| **Multi-repo Awareness** | Cross-repo context. Know that auth service in repo A is consumed by repos B and C. |
| **Migration Assistant** | Track migration progress (e.g. .NET 6 → 8). Q knows what's migrated and what's left. |
