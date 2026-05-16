# Mnemo v0.5.0 — Deployment Plan

## Release Summary

**Codename:** Autonomous Engine + ONNX Semantic Search
**Version:** 0.5.0
**Target Date:** Next commit (pending review)
**Tests:** 223 passing, 1 skipped

## What's New in v0.5.0

### Major Features
1. **ONNX Semantic Search** — local all-MiniLM-L6-v2 embeddings, 100% R@5, 2ms search
2. **Incremental Graph Freshness** — graph updates within 30s of file changes during sessions
3. **Memory-Graph Integration** — memories auto-link to code symbols (MEM_REF_CLASS edges)
4. **Code Intelligence Engine v2** — LadybugDB (Kuzu) with Roslyn C# enrichment
5. **Dashboard UI** — vis-network graph, communities, memory view, search, detail panels

### Bug Fixes
- MCP handler was returning function objects instead of results
- Graph `neighbors` query crash (Kuzu `type(e)` not supported)
- Contradiction threshold too aggressive (0.5 → 0.6)
- `mnemo_context` crash on string input
- Community naming duplicates

### Removed (Desloppify)
- `mnemo/ui/` (replaced by `serve.py` + `ui_static/`)
- `mnemo/graph/` (replaced by `engine/` LadybugDB)
- `mnemo/intelligence/` (no longer needed)
- `mnemo/doctor.py` (merged into `mnemo_audit`)
- `mnemo/vector_index/` (replaced by ONNX retrieval)
- `mnemo/sqlite_adapter.py` (unused)
- `mnemo/api.py` (merged into serve)

## Pre-Release Checklist

- [ ] Review all modified files (60+ files)
- [ ] Run `python3 -m pytest tests/ -q` — 223 pass
- [ ] Run `python3 -m ruff check mnemo/ --select E,F` — check for errors
- [ ] Test `mnemo init` on fresh repo
- [ ] Test `mnemo ui` (serve on port 3333)
- [ ] Test semantic search with real queries
- [ ] Verify ONNX model downloads on first run
- [ ] Test on all 3 repos: MockPayer, ProviderSearch, InternalAttestation
- [ ] Update version in `pyproject.toml` (0.4.0 → 0.5.0)
- [ ] Update CHANGELOG.md

## Deployment Steps

### 1. Version Bump
```bash
# pyproject.toml: version = "0.5.0"
# mnemo/__init__.py: __version__ = "0.5.0"
```

### 2. Commit
```bash
git add -A
git commit -m "feat: Mnemo v0.5 — ONNX semantic search, incremental graph, memory-graph integration

- ONNX all-MiniLM-L6-v2 for dense embeddings (100% R@5, 2ms search)
- Incremental graph freshness (30s staleness window)
- Memory-Graph wiring: memories auto-link to code symbols
- Desloppify: removed 12 dead modules (-4957 lines)
- Contradiction threshold fix (0.5 → 0.6)
- Dashboard UI with vis-network graph
- 223 tests passing"
```

### 3. Tag & Push
```bash
git tag v0.5.0
git push origin main --tags
```

### 4. PyPI Release
GitHub Actions will auto-publish on tag push via `.github/workflows/`.

### 5. Post-Release
- [ ] Verify `pip install mnemo-dev==0.5.0` works
- [ ] Verify ONNX model auto-downloads on first `mnemo init`
- [ ] Update website (if needed)
- [ ] Post release notes

## New Dependencies

| Package | Version | Size | Purpose |
|---------|---------|------|---------|
| `onnxruntime` | >=1.17 | ~30MB | Embedding inference |
| `tokenizers` | >=0.15 | ~5MB | Model tokenizer |
| `numpy` | >=1.24 | ~15MB | Vector storage + cosine |

## ONNX Model Distribution

The `all-MiniLM-L6-v2` model (86MB ONNX) is downloaded on first `mnemo init` to:
```
~/.cache/mnemo/models/all-MiniLM-L6-v2/
  model.onnx (86MB)
  tokenizer.json (466KB)
```

Downloaded via `curl` from HuggingFace. If offline, Mnemo falls back to keyword-only search (graceful degradation).

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|-----------|
| ONNX model download fails | Search degrades to keyword-only | Graceful fallback, error message |
| Large graph (5000+ nodes) | UI may be slow | vis-network handles 2000 nodes fine; filter pills to reduce |
| LadybugDB WAL corruption | Graph queries fail | Auto-delete WAL on next open |
| Contradiction threshold too high | Misses some supersessions | Tuned to 0.6 via testing |

## Performance Targets

| Operation | Target | Actual |
|-----------|--------|--------|
| Init (300 files) | <10s | 7s |
| Recall | <100ms | 33ms |
| Semantic search | <100ms | 2ms |
| Remember (1 memory) | <50ms | 5ms |
| Graph query | <10ms | 0.2ms |
| RAM | <400MB | 265MB |
