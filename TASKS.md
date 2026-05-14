# Mnemo v0.5 — Autonomous Engine + Quality Over Quantity

Last updated: 2026-05-14

## Vision

Transform Mnemo from a toolbox (56 tools the agent must call) into an autonomous engine (invisible infrastructure that learns passively). Fewer tools, higher quality, token-aware, self-verifying.

---

## Phase 1: Passive Intelligence

**Goal**: Agent gets smarter without calling any tools. Hooks do the work.

### MNO-013: userPromptSubmit — Inject Relevant Memories Per Prompt
**Priority**: 🔴 Critical | **Effort**: Medium | **Dependencies**: None

**What**: When user sends a prompt, search memory semantically and inject 2-3 most relevant memories into agent context (max 500 tokens).

**Implementation**:
- `.kiro/hooks/user-prompt-submit.sh` receives user prompt via STDIN JSON
- Extract prompt text from `{"prompt": "..."}`
- Call `mnemo tool mnemo_search_memory --query "<prompt_text>" --deep false`
- Format top 2-3 results as concise context block
- Output to stdout (Kiro injects into agent context)
- Token budget: truncate each memory to 150 chars, max 3 results

**Files**: `mnemo/hooks/__init__.py` (template), `.kiro/hooks/user-prompt-submit.sh` (generated)

**Acceptance**: Agent receives relevant past context without calling any tool.

---

### MNO-014: stop Hook — Auto-Extract Facts From Response
**Priority**: 🔴 Critical | **Effort**: High | **Dependencies**: None

**What**: When agent finishes responding, parse the response and auto-save facts, decisions, patterns, and bug fixes.

**Implementation**:
- `.kiro/hooks/stop.sh` receives agent response via STDIN JSON
- Extract response text from `{"response": "..."}`
- Pattern match for extractable content:
  - "We decided X" / "I chose X" → `mnemo_decide`
  - "The issue was X because Y" / "Fixed by Z" → `mnemo_remember --category bug`
  - "User prefers X" / "Convention: X" → `mnemo_remember --category preference`
  - "Pattern: X" / "Always do X" → `mnemo_remember --category pattern`
- Skip if response is short (<100 chars) or is a question
- Skip if extracted fact is duplicate (dedup handles this)
- Rate limit: max 2 extractions per response

**Files**: `mnemo/hooks/__init__.py` (template), `mnemo/hooks/extractor.py` (new — fact extraction logic)

**Acceptance**: After 10 conversations, memory.json has auto-extracted entries the user never explicitly saved.

---

### MNO-015: Session Summarization
**Priority**: 🟡 High | **Effort**: Medium | **Dependencies**: MNO-014

**What**: Every 5 tool calls, summarize what happened in the session and store as working memory.

**Implementation**:
- Track tool call count in `observations.json` (already exists)
- In middleware, after every 5th call: summarize recent observations
- Store as `tier: "working"` memory with `forget_after: session_end + 24h`
- Summary format: "Session [date]: worked on [files], made [decisions], found [issues]"

**Files**: `mnemo/middleware.py`, `mnemo/memory/services.py`

**Acceptance**: `mnemo_recall` shows a session summary even if agent never called remember.

---

## Phase 2: Tool Consolidation (56 → 15)

**Goal**: Fewer tools, each excellent. Agents can discover and use them easily.

**Dependencies**: Phase 1 complete (passive intelligence reduces need for explicit tools)

### MNO-016: Unified mnemo_search
**Priority**: 🟡 High | **Effort**: Medium | **Dependencies**: None

**What**: Merge `search_memory`, `search_api`, `search_errors`, `cross_search` into one tool with `scope` parameter.

**Implementation**:
```python
@tool("mnemo_search", "Search across memory, code, APIs, errors, or all linked repos.",
      properties={
          "query": {"type": "string"},
          "scope": {"type": "string", "description": "memory|code|api|errors|cross-repo|all (default: all)"},
      }, required=["query"])
```
- `scope=all` (default): search memory first, then code, return combined
- `scope=memory`: only memory
- `scope=code`: only code/vector index
- Keep old tool names as aliases for backward compat (register both names)

**Files**: `mnemo/tools/search.py`

---

### MNO-017: Unified mnemo_audit
**Priority**: 🟡 High | **Effort**: Medium | **Dependencies**: None

**What**: Merge `check_security`, `dead_code`, `drift`, `health`, `breaking_changes`, `check_conventions` into one tool.

**Implementation**:
```python
@tool("mnemo_audit", "Run code quality checks.",
      properties={
          "report": {"type": "string", "description": "security|dead-code|drift|health|breaking|conventions|full (default: full)"},
          "file": {"type": "string", "description": "Optional file scope"},
      })
```
- `report=full`: run all checks, return combined report
- Individual reports for focused analysis
- Keep old names as aliases

**Files**: `mnemo/tools/safety.py`

---

### MNO-018: Unified mnemo_record
**Priority**: 🟢 Medium | **Effort**: Medium | **Dependencies**: None

**What**: Merge error/incident/review/correction CRUD into one tool.

**Implementation**:
```python
@tool("mnemo_record", "Store or search engineering records.",
      properties={
          "type": {"type": "string", "description": "error|incident|review|correction"},
          "action": {"type": "string", "description": "add|search|list"},
          ...type-specific fields...
      }, required=["type", "action"])
```

**Files**: `mnemo/tools/team.py`

---

### MNO-019: Unified mnemo_generate
**Priority**: 🟢 Medium | **Effort**: Low | **Dependencies**: None

**What**: Merge `commit_message` + `pr_description` into one tool.

**Implementation**:
```python
@tool("mnemo_generate", "Generate commit message or PR description from context.",
      properties={"target": {"type": "string", "description": "commit|pr"}})
```

**Files**: `mnemo/tools/git.py`

---

### MNO-020: Merge task into plan
**Priority**: 🟢 Medium | **Effort**: Low | **Dependencies**: None

**What**: Add `action=task` and `action=task_done` to existing `mnemo_plan`.

**Files**: `mnemo/tools/plan.py`, `mnemo/tools/team.py`

---

## Phase 3: Token Budget Engine

**Goal**: 60% less context tokens with same or better quality.

**Dependencies**: Phase 2 (fewer tools = less schema overhead)

### MNO-021: Tiered Recall
**Priority**: 🔴 Critical | **Effort**: High | **Dependencies**: MNO-013

**What**: Three tiers of context injection.

**Implementation**:
- **Tier 1** (auto-injected via hook, ~500 tokens): Active task + 3 most relevant memories + next plan step + 1 warning
- **Tier 2** (on `mnemo_recall`, ~2000 tokens): Full decisions, hot memories, graph summary, repo identity
- **Tier 3** (on `mnemo_recall --deep`, unlimited): Everything including warm memories, full repo map

**Files**: `mnemo/memory/search.py` (recall function), `mnemo/hooks/__init__.py`

**Acceptance**: Default recall output is <2000 tokens. Agent still has full context.

---

### MNO-022: Memory Compression for Injection
**Priority**: 🟡 High | **Effort**: Medium | **Dependencies**: MNO-021

**What**: Before injecting memories into context, compress long entries to 1-2 sentences.

**Implementation**:
- If memory content > 200 chars, truncate to first sentence + key terms
- Format: `[category] content_summary (files: x.py, y.py)`
- Store compressed version as `summary` field on the entry (cache it)

**Files**: `mnemo/memory/retention.py` (add summarize function)

---

### MNO-023: Context Dedup
**Priority**: 🟢 Medium | **Effort**: Medium | **Dependencies**: MNO-021

**What**: Track what's already been injected this session, don't repeat.

**Implementation**:
- Maintain session-level set of injected memory IDs (in observations.json)
- `userPromptSubmit` hook checks: skip memories already injected this session
- Reset on new session (agentSpawn)

**Files**: `mnemo/utils/observations.py`, hook scripts

---

## Phase 4: Self-Learning Loop

**Goal**: Mnemo improves itself over time without human intervention.

**Dependencies**: Phase 1 (passive capture provides data to learn from)

### MNO-024: Confidence Reinforcement
**Priority**: 🟡 High | **Effort**: Medium | **Dependencies**: MNO-014

**What**: When agent uses a memory and gets corrected → decay confidence. When confirmed → boost.

**Implementation**:
- On `mnemo_add_correction`: find memories matching the correction context, decay their confidence by 0.1
- On `mnemo_remember` that references an existing memory: boost that memory's confidence by 0.05
- Memories below confidence 0.3 get demoted to cold tier

**Files**: `mnemo/memory/retention.py`, `mnemo/corrections/__init__.py`

---

### MNO-025: Observation Mining
**Priority**: 🟢 Medium | **Effort**: High | **Dependencies**: MNO-015

**What**: Analyze tool call patterns and extract workflow lessons.

**Implementation**:
- On every 50th tool call, analyze last 50 observations
- Detect patterns: "always searches X before doing Y", "frequently looks up Z"
- Store as lessons with source="observation_mining"
- Surface in enrichment: "You usually check X before doing this"

**Files**: `mnemo/utils/observations.py`, `mnemo/memory/lessons.py`

---

### MNO-026: Self-Verification
**Priority**: 🟡 High | **Effort**: High | **Dependencies**: MNO-013

**What**: Before agent responds, check if response contradicts stored decisions.

**Implementation**:
- In `preToolUse` hook (for `mnemo_remember` and `mnemo_decide`): search existing decisions for contradictions
- If similarity > 0.5 with an existing decision, inject warning
- Format: "⚠️ This may contradict Decision #X: ..."

**Files**: `mnemo/hooks/__init__.py`, hook scripts

---

### MNO-027: Auto-Slot Detection
**Priority**: ⚪ Low | **Effort**: Low | **Dependencies**: MNO-025

**What**: If agent searches same topic 3+ times, auto-create a memory slot.

**Implementation**:
- Track search queries in observations
- If same topic (similarity > 0.8) searched 3+ times: create slot
- Slot name derived from query: "auth_tokens", "database_config", etc.

**Files**: `mnemo/memory/slots.py`, `mnemo/utils/observations.py`

---

## Phase 5: ChromaDB Reliability

**Goal**: Vector search always available, always fresh.

**Dependencies**: None (can run in parallel with other phases)

### MNO-028: Auto-Install ChromaDB
**Priority**: 🟡 High | **Effort**: Low | **Dependencies**: None

**What**: On `mnemo init`, check if chromadb is installed. If not, install it.

**Implementation**:
- In `init.py`: try `import chromadb`. If ImportError: `pip install chromadb`
- Show progress: "Installing semantic search (chromadb)..."
- If install fails (corporate proxy): warn and continue without it

**Files**: `mnemo/init.py`

---

### MNO-029: Stale Index Health Check
**Priority**: 🟢 Medium | **Effort**: Low | **Dependencies**: None

**What**: If ChromaDB index is >24h old, auto-rebuild on next recall.

**Implementation**:
- Check `.mnemo/index/chroma/` mtime
- If older than 24h and `has_changes()`: rebuild index
- Add to `mnemo doctor` output

**Files**: `mnemo/memory/search.py`, `mnemo/doctor.py`

---

### MNO-030: Incremental Indexing
**Priority**: 🟡 High | **Effort**: Medium | **Dependencies**: MNO-029

**What**: Only re-index changed files, not full rebuild.

**Implementation**:
- Compare current file hashes against stored hashes
- Only upsert chunks for files with changed hashes
- Delete chunks for deleted files
- Track indexed file set in `.mnemo/index_manifest.json`

**Files**: `mnemo/repo_map/generator.py`, `mnemo/retrieval.py`

---

## Phase 6: Quality Hardening

**Goal**: Every claim is tested. Performance is measured.

**Dependencies**: Phases 1-5 (test what we built)

### MNO-031: Full Cycle Integration Tests
**Priority**: 🔴 Critical | **Effort**: Medium | **Dependencies**: MNO-028

**What**: Test remember → search → recall with ChromaDB active.

**Implementation**:
- Test: store 10 memories, search semantically, verify top result is correct
- Test: store contradicting memories, verify old one is superseded
- Test: store 100 memories, verify consolidation triggers
- Test: verify eviction removes lowest-retention entries

**Files**: `tests/test_full_cycle.py`

---

### MNO-032: Self-Maintenance Tests
**Priority**: 🟡 High | **Effort**: Medium | **Dependencies**: MNO-031

**What**: Prove contradiction detection, consolidation, and eviction work end-to-end.

**Implementation**:
- Test: add memory "use Redis", then "use Memcached" → first is superseded
- Test: add 100 memories, trigger consolidation, verify count reduced
- Test: add old zero-access memories, run sweep, verify evicted
- Test: verify pinned categories never evicted

**Files**: `tests/test_self_maintenance.py`

---

### MNO-033: Performance Benchmarks
**Priority**: 🟢 Medium | **Effort**: Medium | **Dependencies**: MNO-030

**What**: Measure and track recall latency, search quality, token usage.

**Implementation**:
- Benchmark: `mnemo_recall` should complete in <500ms
- Benchmark: `mnemo_search` precision@5 should be >0.7
- Benchmark: Tier 1 context should be <500 tokens
- Store results in `.mnemo/benchmarks.json`
- Add to `mnemo doctor` output

**Files**: `tests/benchmark_performance.py`, `mnemo/doctor.py`

---

### MNO-034: Enhanced mnemo doctor
**Priority**: 🟢 Medium | **Effort**: Low | **Dependencies**: MNO-029, MNO-033

**What**: Doctor checks everything actually works.

**Implementation**:
- Check: ChromaDB installed and index exists
- Check: Memory count vs active count (eviction working?)
- Check: Any superseded memories? (contradiction detection working?)
- Check: Graph node count matches file count (graph fresh?)
- Check: Hashes.json matches actual files (change detection working?)
- Check: Recall latency <500ms
- Report: "5/5 checks passed" or specific failures

**Files**: `mnemo/doctor.py`

---

## Dependency Graph

```
Phase 1 (Passive Intelligence) — No dependencies, start immediately
  MNO-013 (prompt injection) ──► MNO-021 (tiered recall)
  MNO-014 (fact extraction) ──► MNO-024 (confidence reinforcement)
  MNO-015 (summarization) ──► MNO-025 (observation mining)

Phase 2 (Tool Consolidation) — Can start after Phase 1
  MNO-016 through MNO-020 are independent of each other

Phase 3 (Token Budget) — Depends on Phase 1
  MNO-013 ──► MNO-021 (tiered recall) ──► MNO-022 (compression) ──► MNO-023 (dedup)

Phase 4 (Self-Learning) — Depends on Phase 1
  MNO-014 ──► MNO-024 (confidence)
  MNO-015 ──► MNO-025 (mining) ──► MNO-027 (auto-slots)
  MNO-013 ──► MNO-026 (self-verification)

Phase 5 (ChromaDB) — Independent, can run in parallel
  MNO-028 ──► MNO-029 ──► MNO-030

Phase 6 (Quality) — After everything else
  MNO-028 ──► MNO-031 ──► MNO-032
  MNO-030 ──► MNO-033 ──► MNO-034
```

## Implementation Priority (Sprint Order)

### Sprint 1 (This Week)
1. **MNO-013** — userPromptSubmit hook (biggest impact)
2. **MNO-014** — stop hook fact extraction
3. **MNO-028** — ChromaDB auto-install

### Sprint 2 (Next Week)
4. **MNO-021** — Tiered recall (token savings)
5. **MNO-016** — Unified search tool
6. **MNO-029** — Stale index health check

### Sprint 3
7. **MNO-015** — Session summarization
8. **MNO-022** — Memory compression
9. **MNO-030** — Incremental indexing
10. **MNO-017** — Unified audit tool

### Sprint 4
11. **MNO-024** — Confidence reinforcement
12. **MNO-026** — Self-verification
13. **MNO-018** — Unified record tool
14. **MNO-019** — Unified generate tool

### Sprint 5
15. **MNO-031** — Full cycle tests
16. **MNO-032** — Self-maintenance tests
17. **MNO-033** — Benchmarks
18. **MNO-034** — Enhanced doctor

### Sprint 6 (Polish)
19. **MNO-020** — Merge task into plan
20. **MNO-023** — Context dedup
21. **MNO-025** — Observation mining
22. **MNO-027** — Auto-slot detection

---

## Success Metrics

| Metric | Current (v0.4) | Target (v0.5) |
|--------|---------------|---------------|
| Tools | 56 | 15 |
| Recall tokens | ~4000 | <2000 (Tier 2), <500 (Tier 1) |
| Auto-saved memories per session | 0 | 3-5 |
| Search precision@5 | Unknown | >0.7 |
| Recall latency | ~800ms | <500ms |
| ChromaDB availability | ~60% | >95% |
| Test coverage (memory lifecycle) | Partial | Full cycle tested |
| Agent tool calls for context | 3-5 per session | 0-1 (hooks do the rest) |
