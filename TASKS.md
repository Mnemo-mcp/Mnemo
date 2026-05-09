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
  - Candidate from docs: ChromaDB.
  - Keep optional until install strategy is settled.

- [x] `MNO-304` Upgrade `mnemo_similar`.
  - Use semantic retrieval when an index exists.
  - Fall back to current keyword search when it does not.

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
  - Done when `pip install mnemo` installs a working release.

- [x] `MNO-502` Prototype single binary.
  - Build Windows, macOS, and Linux artifacts using PyInstaller or Nuitka.
  - Done when Mnemo runs without a local Python installation.

- [x] `MNO-503` Design VS Code extension MVP.
  - Detect Mnemo install.
  - Run init on workspace open.
  - Show index/MCP status.
  - Add refresh index action.

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

- [ ] `MNO-606` Add PR Intelligence MVP.
  - Diff parser, summary, risk score, missing tests, reviewer recommendation.

- [ ] `MNO-607` Add Governance MVP.
  - `.mnemo/standards.yaml`, built-in rule library, `mnemo_validate`.

- [ ] `MNO-608` Add temporal memory.
  - Rich ADRs, migration tracking, `mnemo_history`.

- [ ] `MNO-609` Add multi-repo workspace mode.
  - `mnemo init --workspace`, cross-repo dependency graph.

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

## Current Next Task

Next task: `MNO-601` - implement `mnemo serve` for team usage (MNO-003 intentionally deferred).
