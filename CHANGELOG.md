# Changelog

All notable changes to this project will be documented in this file.

## [0.5.0] - 2026-05-16

### Added
- ONNX semantic search (all-MiniLM-L6-v2, 384-dim dense embeddings, 100% R@5)
- Incremental graph freshness — graph auto-updates within 30s of file changes
- Memory-graph integration — memories auto-link to code symbols (MEM_REF_CLASS edges)
- Dashboard UI with vis-network graph visualization
- `mnemo doctor` command for installation diagnostics
- `mnemo serve` command for dashboard UI
- 11 new API endpoints for the dashboard
- Service-level `mnemo_lookup` — one call returns full service architecture (classes, methods, cross-service calls)
- Auto-populated context.json at init (languages, services, key classes from graph)
- ONNX vector index built during init pipeline (Phase 6) — semantic search works immediately after init
- Vector index freshness — changed files get re-embedded incrementally

### Changed
- Search engine: ONNX Runtime + numpy for dense embeddings (265 MB RAM, 2ms search)
- Graph engine: NetworkX replaced with LadybugDB (Kuzu) — persistent, incremental
- Tool count: 56 internal → 16 agent-facing (consolidated via mnemo_audit, mnemo_record, mnemo_search)
- Contradiction threshold: 0.5 → 0.6 (reduces false supersession)
- Community naming: deduplicated (no more 8x "mock-payer-ui-src")
- Hooks: stop hook now captures session summaries, not just atomic learnings
- Dependencies: onnxruntime, tokenizers, numpy now mandatory

### Removed
- 12 dead modules: graph/, intelligence/, doctor.py (old), vector_index/, sqlite_adapter.py, ui/, api.py, dependency_graph/, middleware.py
- 4957 lines of dead code
- `repo_map/generator.py` — redundant filesystem scanner (unified into engine pipeline)

### Fixed
- MCP handler was returning function objects instead of calling handlers
- Graph `neighbors` query crash (Kuzu doesn't support `type(e)`)
- `mnemo_context` crash on string input
- Memory-graph wiring (linking.py imported non-existent functions)
- Decisions not syncing to graph
- `mnemo_recall` timeout — removed blocking filesystem scan from recall hot path
- `_recall_active_task` calling ONNX on every recall (cold-start risk) — now reads plans.json
- `auto_forget_sweep` only ran on deep tier — now runs for all tiers every 10th recall
- `decay_corrections` ran on every recall — now periodic (every 10th)
- `mnemo reset` deleting entire .kiro/ and .claude/ directories — now only removes Mnemo-owned files

## [0.4.0] - 2026-05-10

### Added
- LadybugDB code intelligence engine (Kuzu graph database)
- Roslyn C# enrichment (method signatures, implements)
- Leiden community detection
- 14 language support via tree-sitter
- Binary distribution (PyInstaller)
- VS Code extension scaffold

## [0.3.0] - 2026-05-09

### Added
- Knowledge Graph with NetworkX
- Plan Mode (task tracking)
- Response Enrichment
- Dashboard UI (first version)

## [0.2.0] - 2026-05-09

### Added
- Semantic retrieval foundation
- Local vector index
- Architecture classification
- PyPI release workflow
