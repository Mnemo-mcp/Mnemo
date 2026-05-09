You have access to Mnemo - a persistent memory system for this project.
All project context, decisions, and chat history is below. Use it to answer questions without re-reading files.

AT THE START OF EVERY CHAT:
- Call `mnemo_recall` to get the latest context. The embedded context below may be stale.

ANSWERING QUESTIONS:
- If the recalled memory already contains the answer, USE IT DIRECTLY. Do not re-read files or re-run lookups for information already in memory.
- Only call `mnemo_lookup` or read files when memory does not have enough detail to answer.

SAVING MEMORY:
- Call `mnemo_remember` AFTER any of these happen in the conversation:
  - You made a code change that affects behavior (theme change, config change, new feature, refactor)
  - A bug was found and fixed
  - A design or architecture decision was made
  - The user stated a preference or convention
  - A TODO or follow-up was identified
  - You learned something non-obvious about the codebase
- Call `mnemo_remember` when the context window is getting long to summarize progress so far.
- Call `mnemo_remember` when the user explicitly asks to remember something.
- Do NOT save trivial things like "read a file" or "answered a question with no new insight".
- When in doubt, SAVE. It is better to remember too much than to forget something useful.
- RULE: If you called `mnemo_lookup`, `mnemo_similar`, or `mnemo_who_touched` AND produced a summary or analysis from the results, you MUST call `mnemo_remember` with a concise summary before ending your response.

AVAILABLE TOOLS:
- `mnemo_lookup` - get method-level details for a file or folder
- `mnemo_similar` - find similar implementations to follow as patterns
- `mnemo_intelligence` - architecture graph, patterns, dependencies
- `mnemo_discover_apis` - discover all API endpoints
- `mnemo_search_api` - search for a specific endpoint
- `mnemo_knowledge` - search team knowledge base
- `mnemo_decide` - record a decision
- `mnemo_context` - save project metadata
- `mnemo_map` - refresh code map after changes
- `mnemo_cross_search` - search across ALL linked repos (use when code might live in a sibling service)
- `mnemo_cross_impact` - cross-repo impact analysis (what breaks in other repos if you change something here)
- `mnemo_links` - show linked repos

CROSS-REPO AWARENESS:
- This repo has linked sibling repos. Use `mnemo_links` to see them.
- ALWAYS call `mnemo_cross_search` BEFORE using grep or reading files when:
  - The user asks about code that does not exist in this repo
  - The user mentions a service, project, or module name that is not a folder in this repo
  - `mnemo_lookup` or `mnemo_similar` returned no results
- If the user asks "what breaks if I change X", use `mnemo_cross_impact` for full cross-repo analysis.
- NEVER fall back to grep for code in other repos. Use `mnemo_cross_search` instead.

---

# Project Context
- **repo_root**: /Users/nikhil.tiwari/CodeRepo/Mnemo
- **initialized**: True

# Decisions
- Layer 1 distribution: Combine Option B (unsigned binary via Homebrew tap / curl script / winget) + Option C (VS Code extension auto-downloads and manages the binary). No code signing needed at launch. - User doesn't have Apple Developer account or Windows signing cert. Homebrew bypasses Gatekeeper, Linux has no signing requirement, Windows SmartScreen is acceptable for early-stage dev tools. VS Code extension auto-downloading the binary eliminates PATH/Gatekeeper issues entirely since it runs from extension storage. This is the pattern used by rust-analyzer, clangd, and Terraform extensions.

# Memory
- User's distribution strategy has 3 layers: Layer 1 = single binary (brew/winget/curl), Layer 2 = IDE plugins (VS Code + JetBrains) that auto-configure everything, Layer 3 = team deployment via Docker/Helm/cloud marketplaces. Priority order: binary first (install conversion), then IDE plugins (setup friction), then team server (enterprise scale). [architecture]
- Distribution launch checklist (B+C): 1) git add -A && commit && push to Mnemo-future, 2) git tag v0.1.0 && push tag, 3) Create GitHub Release from tag, 4) Wait for binary-release workflow (~5min), 5) Create nikhil1057/homebrew-tap repo + add Formula/mnemo.rb with real SHA256s from release assets, 6) Create Azure DevOps PAT + VS Code Marketplace publisher (nikhil1057), 7) cd vscode-extension && npm install && vsce package && vsce publish. Install script works via raw GitHub URL: curl -fsSL https://raw.githubusercontent.com/nikhil1057/Mnemo/main/scripts/install.sh | sh. All repo URLs updated to nikhil1057/Mnemo. Must TEST before executing. [todo]
- Future task: Smart Code Review system — 1) Extract review decisions from git/PR comments, 2) Pre-commit validation against stored review feedback (flag missing agreed changes, flag repeated rejected patterns), 3) Review-aware code generation (dont repeat rejected suggestions, reference past review agreements). Requires git/PR API integration (GitHub/Azure DevOps). Medium effort. [todo]
- Future: Auto-select best analyzer per language. Detect tech stack at init time — if .NET SDK available use Roslyn for C#, if node available use TS compiler API for TypeScript, if go binary available use go/ast for Go. Fall back to tree-sitter when native toolchain is missing. User should never be aware of this choice. Needed when Smart Code Review or Convention Enforcer require type-aware analysis. [todo]

# Active Task Context
- **MNO-999**: Fix vector index timeout issue
- Relevant: `mnemo/vector_index/__init__.py` :: `_MemoryRecord`
- Relevant: `mnemo/vector_index/__init__.py` :: `VectorIndex`
- Relevant: `mnemo/test_intel/__init__.py` :: `_should_ignore`
- Relevant: `mnemo/intelligence/__init__.py` :: `_should_ignore`
- Relevant: `mnemo/vector_index/__init__.py` :: `LocalVectorIndex`

# Repo Map
(use mnemo_lookup for method-level details)

**mnemo/**
  __init__.py
  chunking.py → `Chunk`
  cli.py (11 functions)
  clients.py → `ClientTarget`
  config.py (1 functions)
  doctor.py (5 functions)
  init.py (5 functions)
  mcp_server.py (3 functions)
  memory.py (9 functions)
  repo_map.py (15 functions)
  retrieval.py (3 functions)
  storage.py → `Collections`, `StorageAdapter`, `JSONFileAdapter`
  - api_discovery/
  api_discovery/__init__.py (6 functions)
  - code_review/
  code_review/__init__.py (6 functions)
  - dependency_graph/
  dependency_graph/__init__.py (4 functions)
  - embeddings/
  embeddings/__init__.py → `SparseEmbedding`, `EmbeddingProvider`, `KeywordEmbeddingProvider`
  - errors/
  errors/__init__.py (5 functions)
  - health/
  health/__init__.py (5 functions)
  - incidents/
  incidents/__init__.py (5 functions)
  - intelligence/
  intelligence/__init__.py (9 functions)
  - knowledge/
  knowledge/__init__.py (4 functions)
  - onboarding/
  onboarding/__init__.py (1 functions)
  - sprint/
  sprint/__init__.py (6 functions)
  - team_graph/
  team_graph/__init__.py (4 functions)
  - test_intel/
  test_intel/__init__.py (4 functions)
  - vector_index/
  vector_index/__init__.py → `VectorIndex`, `_MemoryRecord`, `LocalVectorIndex`
  - workspace/
  workspace/__init__.py (9 functions)
**tests/**
  test_chunking_semantic.py (3 functions)
  test_clients.py (3 functions)
  test_doctor.py (2 functions)
  test_init.py (2 functions)
  test_intelligence_advanced.py (2 functions)
  test_mcp_semantic_tools.py (1 functions)
  test_memory.py (2 functions)
  test_repo_map_storage.py (1 functions)
  test_secondary_collections.py (4 functions)
  test_storage.py (6 functions)
**vscode-extension/**
  - src/
  src/extension.ts (11 functions)