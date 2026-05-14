# Mnemo

**[Website](https://mnemo-mcp.github.io/Mnemo/)** · **[PyPI](https://pypi.org/project/mnemo-dev/)** · **[GitHub](https://github.com/Mnemo-mcp/Mnemo)**

Persistent memory, knowledge graph, and code intelligence for AI coding assistants. One install gives your AI agent full project context across every chat session.

## The Problem

Every time you start a new AI chat, your assistant forgets everything — what you decided, what you built, how your code is structured. You repeat context, re-explain architecture, and lose insights from previous conversations.

## The Solution

Mnemo gives your AI agent a persistent brain. It builds a knowledge graph of your codebase, remembers decisions, tracks plans, and proactively surfaces relevant context — automatically.

---

## Capabilities

### 🧠 Persistent Memory
Your AI remembers across chat sessions — with smart retrieval that never overloads context:
- Architectural decisions and reasoning
- Bug fixes and their root causes
- Team preferences and conventions
- Production incidents and resolutions
- Auto-categorized, deduplicated, tiered retrieval
- No memory is ever deleted — grows forever without eating your context window

### 🕸️ Knowledge Graph
Your AI understands code relationships instantly:
- Services, classes, interfaces, methods, packages, people as nodes
- Structural edges: implements, inherits, calls, depends_on, owns
- Query: neighbors, traverse, path, find, hubs
- Federated across linked repos (WorkspaceGraph)
- Auto-links memories and decisions to code entities

### 📋 Plan Mode
Work gets tracked automatically:
- Auto-creates plans when you describe work with steps
- Auto-marks tasks done when matching work is remembered
- Proactive hints in every response ("Next: MNO-003 — Update models")
- Syncs to TASKS.md

### 🔔 Response Enrichment
Every tool response includes proactive context:
- Active plan next task
- Regression warnings on risky files
- Related architectural decisions
- No extra tool calls needed — Mnemo injects it automatically

### 🗺️ Code Intelligence
Your AI understands your codebase without reading every file:
- Compact repo tree with equal representation for all services
- Architecture pattern detection (Clean Architecture, CQRS, Hexagonal, Microservices)
- Dependency graph and impact analysis
- Code health reports (complexity hotspots, large files)
- Dead code detection (in-memory scan, <0.3s)
- Smart analyzer selection (Roslyn for C# when .NET SDK available, tree-sitter otherwise)

### 🔍 Semantic Code Search
Find code by meaning, not just filename:
- "Find token refresh logic" → finds `getToken()`, `acquireTokenSilent()`, `ClientCredentialTokenService`
- "Show me error handling" → finds retry pipelines, DelegatingHandlers, catch blocks
- "Database access code" → finds CosmosDbService, repositories, connection code
- Powered by ChromaDB (auto-installed, zero config)

### 🔗 Multi-Repo Workspace
Search across your entire platform:
- Link sibling repos with one command
- Cross-repo semantic search ("find auth code across all services")
- Cross-repo impact analysis ("what breaks in other repos if I change this?")
- Auto-discover and link all repos in a directory

### 📚 Knowledge Base
Your team docs become searchable by the AI:
- Architecture docs, runbooks, coding standards, gotchas
- Searched by meaning, not just keywords
- Add markdown files to `.mnemo/knowledge/`

### 🌐 API Discovery
Your AI knows every endpoint:
- Parses OpenAPI/Swagger specs automatically
- Detects controller annotations (ASP.NET, Express, etc.)
- Semantic search across all discovered endpoints

### 👥 Team Intelligence
Know who owns what:
- Code ownership from git history (excludes merge commits)
- Team expertise map — who knows which service
- "Who last modified this file?"

### 📋 Task-Aware Context
Your AI focuses on what matters:
- Set active task: "I'm working on JIRA-456"
- AI automatically retrieves relevant code for your task
- Task completion tracking

### 🐛 Error & Incident Memory
Never debug the same issue twice:
- Store error → cause → fix mappings
- "Have we seen this NullReferenceException before?" → finds the stored fix
- Record production incidents with root cause and prevention

### 📝 Code Review Memory
Learn from past reviews:
- Store review feedback and outcomes
- Track rejected suggestions so AI doesn't repeat them
- Reference past review agreements

### 🚀 Auto-Remember
The AI saves important findings automatically:
- Code changes that affect behavior
- Bug fixes and their solutions
- Architecture decisions made during conversation
- Non-obvious insights about the codebase

---

## Getting Started

1. Install this extension
2. Open a project folder
3. Click "Yes" when prompted to initialize Mnemo
4. If no AI client is detected, you'll be asked which one you use
5. Start chatting — your AI now has full project context

No terminal commands. No config files. No setup friction.

### Resetting

To wipe all memory and start fresh:
- Open command palette (`Ctrl+Shift+P` / `Cmd+Shift+P`)
- Run **Mnemo: Reset (Wipe All Memory)**
- Confirm the reset
- Run **Mnemo: Initialize Workspace** to start over

---

## What to Ask Your AI

You don't need special syntax — just ask naturally:

| What you want | What to say |
|---|---|
| Project overview | "What do you know about this project?" |
| Code relationships | "What implements IPayerHandler?" |
| Impact analysis | "What breaks if I change CosmosDbService?" |
| Plan work | "We need to migrate to SOAP — steps: ..." |
| Plan status | "What's the plan status?" |
| Find code | "Show me the AuthorizationService methods" |
| Follow patterns | "Show me existing handlers I can follow" |
| Architecture | "What's the architecture of this project?" |
| APIs | "What API endpoints exist?" |
| Save context | "Remember we chose Redis for caching" |
| Search memory | "What do we know about auth tokens?" |
| Cross-repo | "Find authentication code across all services" |
| Code health | "What's the code health?" |
| Dead code | "Find unused code" |
| Security | "Run a security scan" |
| Tests | "What tests cover this file?" |
| Team | "Who knows about the payment service?" |
| Errors | "Have we seen this error before?" |
| Task tracking | "I'm working on JIRA-456" |
| Incidents | "Record this outage" |

---

## Works With

- **Amazon Q** — Full MCP integration
- **Cursor** — Full MCP integration
- **Claude Code** — Full MCP integration
- **GitHub Copilot** — MCP support
- **Kiro** — MCP support
- **Any MCP-compatible client**

---

## Extension Commands

| Command | What it does |
|---|---|
| **Mnemo: Initialize Workspace** | Set up Mnemo in your current project |
| **Mnemo: Show Status** | Run diagnostics, check MCP server health |
| **Mnemo: Refresh Index** | Rebuild code index after major changes |
| **Mnemo: Reset (Wipe All Memory)** | Delete all Mnemo data and start fresh |
| **Mnemo: Check Installation** | Verify Mnemo is available |

---

## Supported Languages

**Core (14 languages):**
- Python (.py)
- JavaScript (.js, .jsx)
- TypeScript (.ts, .tsx)
- Go (.go)
- C# (.cs) — Enhanced with Roslyn when .NET SDK available
- Java (.java)
- Rust (.rs)

**Optional (install with `pip install mnemo[all-languages]`):**
- Ruby (.rb)
- PHP (.php)
- C (.c, .h)
- C++ (.cpp, .cc, .hpp)
- Kotlin (.kt, .kts)
- Swift (.swift)
- Scala (.scala, .sc)

Optional languages are gracefully skipped if not installed — no errors.

---

## How It Works

```
You install extension → Extension downloads Mnemo → Mnemo indexes your code
→ AI client connects via MCP → Every chat has full project context
```

No Python required on your machine. No PATH configuration. The extension handles everything.

---

## Requirements

- VS Code 1.92+
- Git (for team graph and change detection)
- An AI client with MCP support

---

## Links

- [GitHub](https://github.com/Mnemo-mcp/Mnemo)
- [Full Documentation](https://github.com/Mnemo-mcp/Mnemo#readme)
- [Report Issues](https://github.com/Mnemo-mcp/Mnemo/issues)
