# Mnemo Task List

Last updated: 2026-05-14

## Open Tasks

### Distribution & Publishing (P1)

| ID | Priority | Task |
|----|----------|------|
| MNO-901 | 🔴 Critical | Fix package name: rename `mnemo-dev` → `mnemo` in pyproject.toml and publish to PyPI |
| MNO-902 | 🟡 High | Deploy website to GitHub Pages |
| MNO-903 | 🟡 High | Publish `@mnemo-mcp/mcp` to npm |
| MNO-904 | 🟡 High | CI: add pip caching, coverage reporting, test-before-publish |

### Code Quality (P2)

| ID | Priority | Task |
|----|----------|------|
| MNO-911 | 🟡 High | Add TypedDict/dataclass for domain objects (Memory, Decision, Plan, Task) |
| MNO-912 | 🟢 Medium | Add enrichment pipeline tests |
| MNO-913 | 🟢 Medium | postToolUse hook: capture actual file path instead of generic message |
| MNO-914 | 🟢 Medium | Windows path handling verification |

### Memory & Intelligence (P2)

| ID | Priority | Task |
|----|----------|------|
| MNO-921 | 🟢 Medium | Memory aging: auto-archive memories older than 90 days with recall_count < 2 |
| MNO-922 | 🟢 Medium | Autonomous context assembly: auto-inject similar handlers + conventions on intent |
| MNO-923 | ⚪ Low | Learning feedback loops: track accepted/rejected suggestions |
| MNO-924 | ⚪ Low | Code-tuned embeddings (CodeBERT/UniXcoder) |

### Team Server & Enterprise (P3 — Future)

| ID | Priority | Task |
|----|----------|------|
| MNO-931 | 🔴 Critical | `mnemo serve` (REST API over HTTP/SSE) |
| MNO-932 | 🔴 Critical | Enterprise auth (SSO via browser popup) |
| MNO-933 | 🟡 High | Docker Compose deployment |
| MNO-934 | 🟡 High | Neo4j adapter for server graph |
| MNO-935 | 🟡 High | PostgreSQL + pgvector adapter |
| MNO-936 | 🟡 High | Connector workers (JIRA, Confluence) |

### UI Redesign (P3 — Deferred)

| ID | Priority | Task |
|----|----------|------|
| MNO-941 | 🟢 Medium | Dashboard: replace vis-network with custom canvas graph |
| MNO-942 | 🟢 Medium | Dashboard: inline all CDN dependencies |

---

## Recently Completed (This Session)

- ✅ `@tool` decorator pattern — eliminated boilerplate across 9 tool modules
- ✅ Lazy tool registration — no import-time side effects
- ✅ Split `_shared.py` → `indexing.py` + `linking.py`
- ✅ Input sanitization on MCP server (type validation, length limits, path traversal)
- ✅ `from __future__ import annotations` across all modules
- ✅ 43 unused imports removed (ruff auto-fix)
- ✅ Security hardening: nosec annotations, usedforsecurity=False, specific exception types
- ✅ MCP integration tests (12 new tests, 140 total)
- ✅ Portable Kiro agent init with binary discovery
- ✅ Fixed agentSpawn hook injection issue
- ✅ Code audit via desloppify (strict score: 20 → 65.4)
