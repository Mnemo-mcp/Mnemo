# Mnemo Implementation Task List

Created: 2026-05-09

This plan is based on:

- `Mnemo_Evolution_Plan.docx`
- `Mnemo_TRD.docx`
- `InstallationProblemDoc.docx`
- Current source code under `mnemo/`

## Product Stages

Mnemo will be built in three usage stages:

1. **Local Dev Work** - a single developer installs Mnemo easily, runs it locally, and uses it from their AI client without manual MCP setup.
2. **Team Usage** - one team shares decisions, incidents, knowledge, standards, and repo intelligence through a lightweight shared server.
3. **Enterprise Usage** - large organizations deploy Mnemo with SSO, RBAC, audit trails, governance, runtime intelligence, and managed infrastructure.

The rule: local dev must stay simple and working while team and enterprise capabilities are added.

## Ground Rules

- Keep local solo mode working throughout all changes.
- Make install and first use as close to one command as possible.
- Prefer small, shippable increments over platform rewrites.
- Add tests before broad refactors.
- Preserve JSON file storage as the default local backend.
- Do not introduce hosted or cloud dependencies into Local Dev mode.

## Stage 1 - Local Dev Work

Goal: make Mnemo easy to install, easy to initialize, and genuinely useful for one developer across AI clients.

### Local Foundation

- [x] `MNO-001` Add a test harness with `pytest`.
  - Added initial tests for client config, init behavior, and storage adapter behavior.

- [x] `MNO-002` Fix packaging/runtime basics.
  - Confirm CLI entry points `mnemo` and `mnemo-mcp`.
  - Verify install from source in a clean environment.
  - Decide whether the package stays at Python 3.10+ or moves to Python 3.12+.
  - Done when `pip install .`, `mnemo --help`, and `mnemo-mcp` work.
  - Verified on Windows with Python 3.14 in a clean venv (`.venv-mno002`); kept baseline at Python 3.10+ per `pyproject.toml`.

- [ ] `MNO-003` Normalize text encoding in user-facing strings.
  - CLI/init output is improved.
  - Older modules and README still need a complete encoding cleanup pass.

- [x] `MNO-004` Add basic CI.
  - Added GitHub Actions for install, ruff, pytest, and package build.
  - Added semantic-smoke CI job (installs with ChromaDB, runs full test suite).

- [x] `MNO-005` Add `mnemo status` command.
  - Quick one-line check: initialized + MCP server responding.
  - Live JSON-RPC ping to verify MCP server is alive.

- [x] `MNO-006` Add `mnemo reset` cleanup.
  - Now removes `.mnemo/` AND all client context files (.amazonq/rules/mnemo.md, .cursorrules, CLAUDE.md, etc.).

- [x] `MNO-007` Fix `mnemo_recall` timeout.
  - Root cause: ChromaDB auto-install + ONNX model download triggered during recall.
  - Fix: recall skips indexing (index=False), auto-install only during `mnemo init`.
  - Recall time: 46s → 0.08s.

- [x] `MNO-008` Fix code ownership merge commit attribution.
  - `no_merges=True` in git log iteration so merge authors don't get false ownership.

- [x] `MNO-009` Add auto-remember rule.
  - Rule file now mandates `mnemo_remember` after code changes, bug fixes, architecture analysis.
  - "When in doubt, SAVE" + hard RULE for lookup/similar/who_touched results.

- [x] `MNO-010` Add `mnemo_lookup` self-healing index.
  - Lookup now feeds discovered code into ChromaDB so future queries benefit.

### Easy Local Setup

- [x] `MNO-101` Add client configuration model.
  - Supports `amazonq`, `cursor`, `claude-code`, `kiro`, `copilot`, `generic`, and `all`.

- [x] `MNO-102` Add `mnemo init --client`.
  - Keeps Amazon Q as the default.
  - Adds explicit client selection and `all`.

- [x] `MNO-103` Add Claude Code context injection.
  - Generates `CLAUDE.md`.

- [x] `MNO-104` Add Cursor context injection.
  - Generates `.cursorrules`.

- [x] `MNO-105` Update README installation and usage docs.
  - Documents multi-client setup and Windows PATH friction.

- [x] `MNO-106` Add install doctor command.
  - New command: `mnemo doctor`.
  - Check Python version, package version, `mnemo-mcp` availability, client config files, context files, and `.mnemo` health.
  - Live MCP server connectivity check (JSON-RPC ping).
  - ChromaDB status reporting.
  - Runtime mode detection (binary vs python-package).
  - Done when a user can diagnose install problems without reading docs.

### Local Storage

- [x] `MNO-201` Define `StorageAdapter`.
  - Added synchronous adapter protocol and collection constants.

- [x] `MNO-202` Implement `JSONFileAdapter`.
  - Added local JSON backend preserving `.mnemo/*.json`.
  - Supports get, put, list, query, delete, and keyword search.

- [x] `MNO-203` Refactor memory/context/decisions to use adapter.
  - Target `mnemo/memory.py` first because it is the central recall path.
  - Done when no direct JSON reads/writes remain for memory, decisions, or context.

- [x] `MNO-204` Refactor secondary collections to use adapter.
  - Errors, incidents, reviews, sprint tasks.
  - Done when all write-heavy MCP tools use `StorageAdapter`.

- [x] `MNO-205` Refactor repo map hashes through adapter or a dedicated index store.
  - Keep `summary.md` as a generated artifact for now.

### Local Intelligence

- [x] `MNO-301` Design chunk schema.
  - Code chunks at function/class boundaries.
  - Knowledge chunks by markdown heading.
  - Include metadata: file path, language, symbol, chunk type, hash.

- [x] `MNO-302` Add local embedding provider abstraction.
  - Start with a provider interface and a cheap fallback keyword provider for tests.
  - Add local model support later behind optional extras.

- [x] `MNO-303` Add local vector index.
  - ChromaDB with auto-install on first `mnemo init` (gated by MNEMO_AUTO_INSTALL env var).
  - Keyword fallback (SparseEmbedding with token overlap scoring) when ChromaDB unavailable.
  - Fixed duplicate chunk ID bug (hash full composite key).
  - PersistentClient stored in `.mnemo/index/chroma/`.

- [x] `MNO-304` Upgrade `mnemo_similar`.
  - Use semantic retrieval when an index exists.
  - Fall back to current keyword search when it does not.
  - Returns content preview inline so AI doesn't need follow-up lookups.

- [x] `MNO-305` Upgrade `mnemo_knowledge` and `mnemo_search_api`.
  - Use semantic retrieval over knowledge docs and endpoint chunks.

- [x] `MNO-401` Add formal architecture classifier.
  - Detect Clean Architecture, CQRS, Hexagonal, Event-Driven, Microservices.

- [x] `MNO-402` Add task-aware context retrieval.
  - Use active `mnemo_task` as a relevance signal.
  - Add `mnemo_context_for_task`.

- [x] `MNO-403` Make repo map hierarchical.
  - Generate module/service sections.
  - Lazy-load details via `mnemo_lookup`.

- [x] `MNO-404` Improve parser coverage.
  - Current Go extraction appears incomplete despite Go being listed as supported.
  - Improve TypeScript/JavaScript extraction beyond top-level functions.

### Local Distribution

- [x] `MNO-501` Prepare PyPI release.
  - Versioning, changelog, build workflow, package metadata.
  - Added `readme`, `license`, `authors`, `classifiers`, `project.urls` to pyproject.toml.
  - Added `[semantic]` and `[binary]` optional extras.
  - Release workflow publishes to PyPI on tag push.

- [x] `MNO-502` Prototype single binary.
  - PyInstaller spec with hidden imports for tree-sitter grammars.
  - Cross-platform GitHub Actions workflow (macOS arm64/x64, Linux x64, Windows x64).
  - Binaries attached to GitHub Releases automatically.
  - `sys.frozen` detection in clients.py for binary mode.

- [x] `MNO-503` Design VS Code extension MVP.
  - Auto-detects if Mnemo binary is installed; if not, downloads from GitHub Releases.
  - Prompts "Initialize project memory?" on workspace open.
  - Status bar indicator ("Mnemo: Active" / spinning during indexing).
  - Commands: Initialize Workspace, Show Status, Refresh Index, Check Installation.

- [x] `MNO-504` Add Homebrew formula.
  - Formula template in `scripts/homebrew/mnemo.rb`.
  - Supports macOS arm64/x64 and Linux x64.
  - Users install with `brew install nikhil1057/tap/mnemo`.

- [x] `MNO-505` Add install script.
  - `scripts/install.sh` for macOS/Linux.
  - Auto-detects platform, downloads latest release from GitHub.
  - Users install with `curl -fsSL ... | sh`.

### Multi-Repo Workspace

- [x] `MNO-506` Implement multi-repo linking.
  - `mnemo link <path>` — link a sibling repo.
  - `mnemo link --discover <dir>` — auto-discover all git repos under a directory.
  - `mnemo link --discover <dir> --init` — discover, link, AND initialize all repos.
  - `mnemo unlink <name>` — remove a link.
  - `mnemo links` — show all linked repos with status.
  - Links stored in `.mnemo/links.json`.

- [x] `MNO-507` Implement cross-repo search.
  - `mnemo_cross_search` MCP tool — searches this repo + all linked repos.
  - Results tagged with repo name, merged and ranked by score.
  - Supports code, api, and knowledge namespaces.

- [x] `MNO-508` Implement cross-repo impact analysis.
  - `mnemo_cross_impact` MCP tool — shows what breaks across ALL linked repos.
  - Groups results by repo.

- [x] `MNO-509` Add cross-repo awareness to rule file.
  - AI instructed to use `mnemo_cross_search` when code doesn't exist locally.
  - Never fall back to grep for code in other repos.

### Smart Analyzer

- [x] `MNO-510` Implement Roslyn analyzer for C#.
  - .NET 8 console app using Microsoft.CodeAnalysis.
  - Outputs JSON with full type-resolved method signatures, constructors, inheritance.
  - Auto-detected: if .NET SDK available + .csproj/.sln found → uses Roslyn.
  - Falls back to tree-sitter when .NET SDK not available.
  - User is never aware of analyzer choice.

## Stage 2 - Team Usage

Goal: let a team share Mnemo context without each developer maintaining isolated knowledge.

- [ ] `MNO-601` Implement `mnemo serve`.
  - FastAPI server with health endpoint.
  - Expose MCP over HTTP/SSE.
  - Done when local MCP tools can route through server mode.

- [ ] `MNO-602` Implement `mnemo connect`.
  - Store server URL/API key locally.
  - Redirect shared collections to server.
  - Personal data stays local.

- [ ] `MNO-603` Add `SQLiteAdapter`.
  - SQLite with WAL mode and FTS5.
  - Done when all adapter tests pass against JSON and SQLite.

- [ ] `MNO-604` Add Docker deployment.
  - Dockerfile and docker-compose.yml.
  - Done when `docker compose up` starts a working team server.

- [ ] `MNO-605` Add team shared collection policy.
  - Shared: decisions, incidents, errors, reviews, knowledge, standards.
  - Local: chat summaries, preferences, active task.

- [ ] `MNO-606` Add Smart Code Review.
  - Extract review decisions from git/PR comments (GitHub/Azure DevOps API).
  - Pre-commit validation: flag missing agreed changes, flag repeated rejected patterns.
  - Review-aware code generation: don't repeat rejected suggestions, reference past agreements.

- [ ] `MNO-607` Add Governance MVP.
  - `.mnemo/standards.yaml`, built-in rule library, `mnemo_validate`.

- [ ] `MNO-608` Add temporal memory.
  - Rich ADRs, migration tracking, `mnemo_history`.

- [ ] `MNO-609` Add Convention Enforcer.
  - Detect patterns and enforce them when AI generates code.
  - "All handlers must inherit BaseHandler."
  - Requires type-aware analysis (Roslyn/TS compiler).

## Stage 3 - Enterprise Usage

Goal: support regulated, large-scale, self-hosted or managed enterprise deployments.

- [ ] `MNO-701` Add PostgreSQL adapter.
  - Tenant-aware schema and migration scripts.

- [ ] `MNO-702` Add Qdrant adapter.
  - Production vector retrieval and hybrid search.

- [ ] `MNO-703` Add Neo4j graph engine.
  - Cross-repo service graph, ownership graph, incident graph.

- [ ] `MNO-704` Add enterprise auth.
  - Azure AD/Okta OIDC, RBAC, service accounts.

- [ ] `MNO-705` Add audit logging.
  - Tool call logs, write logs, export hooks for SIEM.

- [ ] `MNO-706` Add enterprise security artifacts.
  - SBOM per release, vulnerability scan workflow, security page content.

- [ ] `MNO-707` Add runtime intelligence.
  - App Insights, Datadog, CloudWatch, OpenTelemetry correlation.

- [ ] `MNO-708` Add Helm chart.
  - Kubernetes deployment with health checks, autoscaling, and configuration.

- [ ] `MNO-709` Add SCIM provisioning.
  - Automated user lifecycle management.

- [ ] `MNO-710` Add cloud marketplace packaging.
  - AWS, Azure, and GCP marketplace deployment paths.

- [ ] `MNO-711` Add auto-analyzer expansion.
  - TypeScript: use TS compiler API when `node` available for full type resolution.
  - Go: use `go/ast` when `go` binary available for interface satisfaction.
  - Fall back to tree-sitter when native toolchain missing.

## Current Next Task

Next task: `MNO-601` - implement `mnemo serve` for team usage (MNO-003 intentionally deferred).
