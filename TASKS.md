# Mnemo Task List

Created: 2026-05-09 | Last updated: 2025-07

## Summary

| Status | Count |
|--------|-------|
| ✅ Completed | 84 |
| 🔲 Open | 42 |
| **Total** | **126** |

---

## How This Is Organized

Tasks are grouped by **functional area**, not by stage. Each area shows what's done and what's next. The priority tags are:

- 🔴 **Critical** — blocks users or other features
- 🟡 **High** — significant value, should do soon
- 🟢 **Medium** — nice to have, do when time allows
- ⚪ **Low** — future/speculative

---

## 1. Core Memory & Storage

*The brain — how Mnemo stores and retrieves knowledge.*

### ✅ Completed

| ID | Task |
|----|------|
| MNO-201 | StorageAdapter protocol |
| MNO-202 | JSONFileAdapter (local JSON backend) |
| MNO-203 | Refactor memory/context/decisions to use adapter |
| MNO-204 | Refactor secondary collections (errors, incidents, reviews, tasks) |
| MNO-205 | Repo map hashes through adapter |
| MNO-514 | Context compression (auto-triggers at 50 entries) |
| MNO-522 | Knowledge Graph — Local + Workspace (NetworkX, 886 nodes on Mock_Payer) |
| LIM-01 | Atomic file writes (tempfile + os.replace) |
| LIM-02 | Memory deduplication (85% similarity threshold) |
| LIM-05 | Memory deletion (mnemo_forget) |
| LIM-09 | Recall decomposed into sub-functions |
| LIM-12 | Token-based recall budget |
| LIM-25 | Context file refresh on code changes |
| LIM-26 | Debounced context file refresh (5s cooldown) |
| LIM-28 | Incremental re-indexing on code change |

### 🔲 Open

| ID | Priority | Task |
|----|----------|------|
| MNO-603 | 🟡 High | SQLiteAdapter (WAL + FTS5) — needed for scale beyond ~1000 entries |
| LIM-11 | 🟢 Medium | Semantic summarization in compression (needs LLM) |
| LIM-13 | 🟢 Medium | Conflict resolution for contradicting memories |
| LIM-14 | 🟡 High | Flat JSON slow at thousands of entries (solved by MNO-603) |

---

## 2. Code Intelligence & Parsing

*Understanding the codebase — parsing, patterns, architecture detection.*

### ✅ Completed

| ID | Task |
|----|------|
| MNO-301 | Chunk schema (function/class boundaries) |
| MNO-302 | Embedding provider abstraction + keyword fallback |
| MNO-303 | ChromaDB vector index with auto-install |
| MNO-304 | Semantic `mnemo_similar` |
| MNO-305 | Semantic `mnemo_knowledge` and `mnemo_search_api` |
| MNO-401 | Architecture classifier (Clean, CQRS, Hexagonal, Event-Driven, Microservices) |
| MNO-402 | Task-aware context retrieval (mnemo_context_for_task) |
| MNO-403 | Hierarchical repo map |
| MNO-404 | Improved Go/JS/TS extraction |
| MNO-510 | Roslyn analyzer for C# (full type resolution) |
| MNO-513 | Dead code detector (in-memory scan, 0.2s) |
| LIM-07 | Method-level chunks (not just class-level) |
| LIM-10 | IDF weighting in keyword fallback |
| LIM-17 | Dead code: replaced git grep with in-memory scan |

### 🔲 Open

| ID | Priority | Task |
|----|----------|------|
| MNO-711 | 🟡 High | Auto-analyzer expansion (Java, Rust, Ruby, PHP, C/C++ via tree-sitter; TS compiler API, go/ast) |
| LIM-15 | 🟡 High | Language support: Java, Rust, Ruby, PHP, C/C++ |
| LIM-16 | 🟢 Medium | Deep parsing: type inference, full call graph (native toolchain) |
| LIM-18 | 🟢 Medium | Code-tuned embeddings (CodeBERT/UniXcoder instead of MiniLM) |
| LIM-19 | ⚪ Low | Persist keyword fallback index to disk |

---

## 3. Safety & Quality

*Keeping code safe — security, breaking changes, regressions, drift.*

### ✅ Completed

| ID | Task |
|----|------|
| MNO-515 | Security pattern memory (mnemo_add_security_pattern, mnemo_check_security) |
| MNO-516 | Breaking change detector (mnemo_breaking_changes, auto-baseline on tags) |
| MNO-517 | Regression memory (mnemo_add_regression, mnemo_check_regressions) |
| MNO-518 | Architecture drift detection (mnemo_drift) |
| LIM-20 | Security scanner strips comments/strings before regex |
| LIM-21 | Auto-baseline on git tags |
| LIM-22 | Drift detection with regex intent extraction |

### 🔲 Open

| ID | Priority | Task |
|----|----------|------|
| MNO-607 | 🟡 High | Governance MVP (.mnemo/standards.yaml, rule library, mnemo_validate) |
| MNO-609 | 🟡 High | Convention enforcer (detect + enforce patterns in AI-generated code) |
| MNO-616 | 🟢 Medium | Dependency vulnerability alerts (OSV.dev API) |

---

## 4. Git Integration & Developer Workflow

*Hooks, commits, PRs, corrections, velocity.*

### ✅ Completed

| ID | Task |
|----|------|
| MNO-511 | Commit message generator (mnemo_commit_message) |
| MNO-512 | PR description generator (mnemo_pr_description) |
| MNO-519 | Git hooks (pre-commit security/pattern validation) |
| MNO-520 | Learning from corrections (mnemo_add_correction) |
| MNO-521 | Velocity tracking (mnemo_velocity) |

### 🔲 Open

| ID | Priority | Task |
|----|----------|------|
| MNO-606 | 🟡 High | Smart code review (extract decisions from PR comments, review-aware generation) |
| MNO-608 | 🟢 Medium | Temporal memory (rich ADRs, migration tracking, mnemo_history) |
| MNO-612 | 🟢 Medium | PR review bot (GitHub Action, posts comments on PR) |
| MNO-615 | 🟢 Medium | CI/CD integration (GitHub Action: health check + breaking changes) |

---

## 5. Multi-Repo & Workspace

*Working across multiple repositories.*

### ✅ Completed

| ID | Task |
|----|------|
| MNO-506 | Multi-repo linking (link, unlink, discover, links) |
| MNO-507 | Cross-repo search (mnemo_cross_search) |
| MNO-508 | Cross-repo impact analysis (mnemo_cross_impact) |
| MNO-509 | Cross-repo awareness in rule file |
| MNO-522 | WorkspaceGraph (federated graph queries across linked repos) |

### 🔲 Open

*No open tasks — workspace layer is complete. Enterprise tier (MNO-703) extends this.*

---

## 6. Distribution & Installation

*Getting Mnemo into users' hands.*

### ✅ Completed

| ID | Task |
|----|------|
| MNO-001 | Test harness (pytest) |
| MNO-002 | Packaging/runtime basics |
| MNO-004 | CI (GitHub Actions: install, ruff, pytest, build) |
| MNO-005 | `mnemo status` command |
| MNO-006 | `mnemo reset` cleanup |
| MNO-101 | Client configuration model (amazonq, cursor, claude-code, kiro, copilot, generic, all) |
| MNO-102 | `mnemo init --client` |
| MNO-103 | Claude Code context injection (CLAUDE.md) |
| MNO-104 | Cursor context injection (.cursorrules) |
| MNO-105 | README docs |
| MNO-106 | `mnemo doctor` diagnostic command |
| MNO-501 | PyPI release |
| MNO-502 | Single binary (PyInstaller, cross-platform) |
| MNO-503 | VS Code extension MVP |
| MNO-504 | Homebrew formula |
| MNO-505 | Install script (curl \| sh) |

### 🔲 Open

| ID | Priority | Task |
|----|----------|------|
| MNO-003 | ⚪ Low | Normalize text encoding in user-facing strings |
| LIM-23 | 🟢 Medium | ChromaDB auto-install fragile in corporate proxies |
| LIM-24 | 🟢 Medium | Windows-native path handling verification |

---

## 7. MCP Server & Tool Architecture

*The MCP server, tool dispatch, and protocol handling.*

### ✅ Completed

| ID | Task |
|----|------|
| MNO-007 | Fix recall timeout (46s → 0.08s) |
| MNO-008 | Fix merge commit attribution |
| MNO-009 | Auto-remember rule |
| MNO-010 | Lookup self-healing index |
| LIM-03 | Input validation on MCP tools |
| LIM-04 | mtime-based change detection (replaced MD5 scan) |
| LIM-06 | Pagination on list tools (limit/offset) |
| LIM-08 | Eliminated elif chain — full registry-based dispatch (309 → 137 lines) |

### 🔲 Open

*No open tasks — MCP server architecture is clean.*

---

## 8. Team Server & Collaboration

*Sharing Mnemo across a team.*

### ✅ Completed

*None yet — this is the next major milestone.*

### 🔲 Open

| ID | Priority | Task |
|----|----------|------|
| MNO-601 | 🔴 Critical | `mnemo serve` (FastAPI, MCP over HTTP/SSE) |
| MNO-602 | 🔴 Critical | `mnemo connect` (store server URL, redirect shared collections) |
| MNO-604 | 🟡 High | Docker deployment (docker-compose) |
| MNO-605 | 🟡 High | Team shared collection policy (shared vs local) |
| MNO-610 | 🟢 Medium | Meeting notes → memory (mnemo_ingest_notes) |
| MNO-611 | ⚪ Low | Onboarding quizzes (mnemo_quiz) |
| MNO-613 | 🟢 Medium | Jira/ADO sync (auto-fetch ticket details) |
| MNO-614 | ⚪ Low | Slack/Teams bot |

---

## 9. Enterprise Infrastructure

*Large-scale, managed, secure deployments.*

### ✅ Completed

*None yet — depends on team server.*

### 🔲 Open

| ID | Priority | Task |
|----|----------|------|
| MNO-701 | 🟡 High | PostgreSQL adapter (tenant-aware) |
| MNO-702 | 🟡 High | Qdrant adapter (production vector search) |
| MNO-703 | 🟡 High | Neo4j/OrgGraph (wraps LocalGraph + WorkspaceGraph, same protocol) |
| MNO-704 | 🔴 Critical | Enterprise auth (Azure AD/Okta OIDC, RBAC) |
| MNO-705 | 🔴 Critical | Audit logging (tool calls, writes, SIEM export) |
| MNO-706 | 🟢 Medium | Security artifacts (SBOM, vuln scan workflow) |
| MNO-708 | 🟡 High | Helm chart (K8s deployment) |
| MNO-709 | 🟢 Medium | SCIM provisioning |
| MNO-710 | ⚪ Low | Cloud marketplace packaging (AWS/Azure/GCP) |

---

## 10. AI-Native Features

*Making Mnemo smarter for AI agents.*

### ✅ Completed

| ID | Task |
|----|------|
| MNO-522 | Knowledge Graph with auto-linking (memories/decisions → code entities) |

### 🔲 Open

| ID | Priority | Task |
|----|----------|------|
| MNO-707 | 🟢 Medium | Runtime intelligence (App Insights, Datadog, OpenTelemetry) |
| MNO-712 | 🟡 High | Predictive context (pre-load related code based on active file) |
| MNO-713 | 🟡 High | Multi-agent coordination (file locks, scratchpad, agent notes) |
| MNO-714 | 🟢 Medium | Global preferences (~/.mnemo/global/) |
| MNO-715 | 🟢 Medium | Technical debt score (health + age + churn + coverage + regressions) |

---

## Priority Roadmap

### Next Up (immediate value)

1. **MNO-601 + MNO-602** — Team server (`mnemo serve` + `mnemo connect`)
2. **MNO-604 + MNO-605** — Docker + shared collection policy
3. **MNO-711 + LIM-15** — More language support (Java, Rust, Ruby)

### After That (high value)

4. **MNO-606** — Smart code review from PR history
5. **MNO-607 + MNO-609** — Governance + convention enforcement
6. **MNO-712 + MNO-713** — Predictive context + multi-agent coordination
7. **MNO-603** — SQLiteAdapter for scale

### Enterprise Track (when team server is stable)

8. **MNO-704 + MNO-705** — Auth + audit logging
9. **MNO-701 + MNO-702 + MNO-703** — PostgreSQL + Qdrant + Neo4j
10. **MNO-708** — Helm chart

---

## Architecture Layers (Current State)

```
┌─────────────────────────────────────────────────────┐
│  MCP Tools (48 tools)                               │
│  tool_registry.py → handlers + schemas              │
├─────────────────────────────────────────────────────┤
│  Knowledge Graph                                    │
│  graph/local.py (NetworkX) + graph/workspace.py     │
├─────────────────────────────────────────────────────┤
│  Semantic Search                                    │
│  vector_index/ (ChromaDB + keyword fallback)        │
├─────────────────────────────────────────────────────┤
│  Code Parsing                                       │
│  repo_map.py + analyzers/ (tree-sitter + Roslyn)    │
├─────────────────────────────────────────────────────┤
│  Storage                                            │
│  storage.py (JSONFileAdapter) → .mnemo/*.json       │
└─────────────────────────────────────────────────────┘
```

**Future (with team server):**
```
┌─────────────────────────────────────────────────────┐
│  MCP Tools (same interface)                         │
├─────────────────────────────────────────────────────┤
│  OrgGraph (wraps WorkspaceGraph + central sync)     │
├─────────────────────────────────────────────────────┤
│  Team Server (FastAPI + SSE)                        │
│  SQLiteAdapter / PostgreSQL / Qdrant / Neo4j        │
├─────────────────────────────────────────────────────┤
│  Local (unchanged — still works offline)            │
└─────────────────────────────────────────────────────┘
```
