# Mnemo Benchmarks

## Search Quality (Recall@5)

| System | R@5 | Latency | RAM |
|--------|-----|---------|-----|
| **Mnemo (BM25 + ONNX + Graph)** | **100%** | **2ms** | **265 MB** |
| Mnemo (BM25 only, no embeddings) | 73% | 47ms | 240 MB |
| Built-in (CLAUDE.md / grep) | ~40% | <1ms | 0 |

### Methodology

- 10 seeded memories covering architecture, patterns, bugs, preferences
- 11 queries: 3 exact match, 2 substring, 6 pure semantic
- Metric: does the expected memory appear in top-5 results?
- Embedding model: `all-MiniLM-L6-v2` (384-dim, ONNX, local)

### Reproduce

```bash
python3 benchmark/search_quality.py
```

## Performance

| Operation | 55 files | 300 files |
|-----------|----------|-----------|
| `mnemo init` | 3.5s | 7.0s |
| Re-init (no changes) | 0.01s | 0.01s |
| Remember 1 memory | 5ms | 5ms |
| Recall | 33ms | 33ms |
| Semantic search | 2ms | 2ms |
| Graph query | 0.2ms | 0.2ms |
| Auto-forget sweep | 12ms | 12ms |

## Scale

| Memories | Store time | Search latency | Vector index size |
|----------|-----------|----------------|-------------------|
| 50 | 265ms | 2ms | 75 KB |
| 200 | 1.2s | 2ms | 300 KB |
| 1,000 (projected) | 6s | 3ms | 1.5 MB |

## Resource Usage

| Resource | Value |
|----------|-------|
| Peak RAM | 265 MB |
| ONNX model (disk) | 86 MB (shared in ~/.cache/mnemo/) |
| .mnemo/ directory | ~16 MB (graph + vectors + JSON) |
| External databases | 0 |
| Network required | Only for first model download |

## vs Competitors

| | Mnemo | agentmemory | mem0 | Built-in (CLAUDE.md) |
|---|---|---|---|---|
| **Type** | MCP server + code graph | Memory server + hooks | Memory API | Static file |
| **Search** | BM25 + Vector + Graph | BM25 + Vector + Graph | Vector + Graph | Loads everything |
| **Code intelligence** | ✅ (LadybugDB graph) | ❌ | ❌ | ❌ |
| **Languages** | 14 | 0 (language-agnostic) | 0 | 0 |
| **Impact analysis** | ✅ | ❌ | ❌ | ❌ |
| **Community detection** | ✅ (Leiden) | ❌ | ❌ | ❌ |
| **Token budget** | ~500/session | ~1,900/session | varies | 22,000+ |
| **External deps** | 0 (all local) | iii-engine | Qdrant/pgvector | 0 |
| **RAM** | 265 MB | ~350 MB | varies | 0 |
| **Install** | `pip install mnemo-dev` | `npm install -g` | `pip install mem0ai` | built-in |

## LongMemEval-S (Planned)

[LongMemEval](https://arxiv.org/abs/2410.10813) (ICLR 2025) is an academic benchmark for long-term memory retrieval — 500 questions across ~48 sessions each.

Mnemo uses the same embedding model (`all-MiniLM-L6-v2`) and fusion approach (BM25 + Vector + RRF) as systems scoring **95.2% R@5** on this benchmark. Full evaluation script at `benchmark/longmemeval.py` (requires dataset download, ~7h runtime).

```bash
# Download dataset (264 MB)
pip install huggingface_hub
python3 -c "
from huggingface_hub import hf_hub_download
hf_hub_download(repo_id='xiaowu0162/longmemeval-cleaned', filename='longmemeval_s_cleaned.json', repo_type='dataset', local_dir='benchmark/data')
"

# Run benchmark
python3 benchmark/longmemeval.py
```
