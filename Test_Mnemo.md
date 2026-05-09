# Test Mnemo — Complete Feature Validation

Use these questions in Amazon Q chat to test every Mnemo capability. Run them in order — later tests depend on memory saved by earlier ones.

---

## Phase 1: Basic Memory & Recall

### Test 1.1 — Recall loads context
```
What do you know about this project?
```
**Expected:** Returns project context, patterns, repo map from `mnemo_recall`. No file reading needed.

### Test 1.2 — Remember a preference
```
Remember that I prefer functional components over class components
```
**Expected:** Calls `mnemo_remember`. Confirms stored.

### Test 1.3 — Verify memory persists (NEW CHAT)
```
What are my coding preferences?
```
**Expected:** Answers from memory without reading files. Mentions "functional components over class components".

### Test 1.4 — Record a decision
```
We decided to use Redis for session caching with a 5-minute TTL
```
**Expected:** Calls `mnemo_decide`. Confirms decision recorded.

### Test 1.5 — Verify decision persists (NEW CHAT)
```
What caching strategy did we choose?
```
**Expected:** Answers "Redis, 5-minute TTL" from memory.

---

## Phase 2: Code Understanding

### Test 2.1 — Lookup a specific file
```
Show me the methods in auth.js
```
**Expected:** Calls `mnemo_lookup`. Returns function signatures (initMsal, login, logout, getToken, checkSession, getAccount, msalReady).

### Test 2.2 — Lookup a service/folder
```
Show me the EligibilityService methods
```
**Expected:** Calls `mnemo_lookup`. Returns class structure with method signatures.

### Test 2.3 — Find similar implementations
```
Show me all payer handlers in the project
```
**Expected:** Calls `mnemo_similar`. Returns list of handler files with class signatures and content preview. Should NOT need follow-up file reads.

### Test 2.4 — Verify memory was saved from lookup (NEW CHAT)
```
What handlers exist in this project?
```
**Expected:** Answers from memory (saved by the RULE in Test 2.3). Minimal or no new lookups.

---

## Phase 3: Semantic Search (ChromaDB)

### Test 3.1 — Search by concept, not filename
```
Find code related to token refresh
```
**Expected:** Calls `mnemo_similar`. Finds ClientCredentialTokenService, auth.js getToken(), acquireTokenSilent — even though "token refresh" isn't a filename.

### Test 3.2 — Search by behavior
```
Find code that handles HTTP errors or retries
```
**Expected:** Finds resilience pipelines, DelegatingHandlers, or retry logic by meaning.

### Test 3.3 — Cross-cutting search
```
What code deals with CosmosDB?
```
**Expected:** Finds CosmosDbService, CosmosDocumentRepository, CosmosResiliencePipeline across multiple services.

---

## Phase 4: Architecture & Intelligence

### Test 4.1 — Full intelligence report
```
What's the architecture of this project?
```
**Expected:** Calls `mnemo_intelligence`. Returns patterns, service graph, dependencies, ownership, architecture classification.

### Test 4.2 — Dependency graph
```
Show me the service dependency graph
```
**Expected:** Calls `mnemo_dependencies`. Shows which service calls which.

### Test 4.3 — Impact analysis
```
What breaks if I change the EligibilityService?
```
**Expected:** Calls `mnemo_impact`. Shows downstream dependencies and affected services.

### Test 4.4 — Architecture classification
```
What architecture patterns does this project follow?
```
**Expected:** Identifies patterns like Repository, Strategy/Handler, DI, Clean Architecture, etc. with confidence scores.

---

## Phase 5: API Discovery

### Test 5.1 — Discover all endpoints
```
What API endpoints exist in this project?
```
**Expected:** Calls `mnemo_discover_apis`. Lists all controller endpoints grouped by service.

### Test 5.2 — Search for specific endpoint
```
Find the endpoint that checks eligibility
```
**Expected:** Calls `mnemo_search_api`. Returns the eligibility endpoint with method, path, and handler.

---

## Phase 6: Knowledge Base

### Test 6.1 — List knowledge files
```
What's in the knowledge base?
```
**Expected:** Calls `mnemo_knowledge` (no query). Lists available markdown files.

### Test 6.2 — Search knowledge
```
How should we handle errors in this project?
```
**Expected:** Calls `mnemo_knowledge`. Returns relevant section from knowledge docs (if any exist in `.mnemo/knowledge/`).

> **Setup:** Add a file `.mnemo/knowledge/standards.md` with error handling guidelines before running this test.

---

## Phase 7: Task Tracking

### Test 7.1 — Set active task
```
I'm working on JIRA-100: add retry logic to the proxy service
```
**Expected:** Calls `mnemo_task`. Confirms task set.

### Test 7.2 — Get task-aware context
```
What code is relevant to my current task?
```
**Expected:** Calls `mnemo_context_for_task`. Returns semantically relevant code (proxy services, retry/resilience code).

### Test 7.3 — Complete task
```
Mark JIRA-100 as done
```
**Expected:** Calls `mnemo_task_done`. Confirms completion.

---

## Phase 8: Code Ownership & Team

### Test 8.1 — Who owns a file
```
Who last modified auth.js?
```
**Expected:** Calls `mnemo_who_touched`. Returns the correct author (not merge commit author).

### Test 8.2 — Team expertise
```
Who's the expert on the eligibility service?
```
**Expected:** Calls `mnemo_team`. Returns authors ranked by commit count in that area.

### Test 8.3 — Full team map
```
Show me the team expertise map
```
**Expected:** Calls `mnemo_team` (no query). Shows all authors and their areas.

---

## Phase 9: Error Memory

### Test 9.1 — Store an error
```
Store this error: CosmosDB 429 TooManyRequests was caused by missing retry policy, fixed by adding CosmosResiliencePipeline with exponential backoff
```
**Expected:** Calls `mnemo_add_error`. Confirms stored.

### Test 9.2 — Search for known error (NEW CHAT)
```
Have we seen a CosmosDB throttling error before?
```
**Expected:** Calls `mnemo_search_errors`. Finds the stored error with cause and fix.

---

## Phase 10: Incidents

### Test 10.1 — Record an incident
```
Record this incident: Auth service went down for 10 minutes because the MSAL token cache exceeded memory limits. Root cause was no eviction policy. Fixed by adding LRU eviction with 1000 token max.
```
**Expected:** Calls `mnemo_add_incident`. Confirms recorded.

### Test 10.2 — Search incidents (NEW CHAT)
```
Any past incidents related to memory or caching?
```
**Expected:** Calls `mnemo_incidents`. Finds the stored incident.

---

## Phase 11: Code Reviews

### Test 11.1 — Store a review
```
Store this review: PR #42 for EligibilityService refactor was approved. Feedback: good separation of concerns but needs more error handling in the CosmosDB retry path.
```
**Expected:** Calls `mnemo_add_review`. Confirms stored.

### Test 11.2 — View review history
```
Show me past code reviews
```
**Expected:** Calls `mnemo_reviews`. Shows the stored review.

---

## Phase 12: Code Health

### Test 12.1 — Health report
```
What's the code health of this project?
```
**Expected:** Calls `mnemo_health`. Shows complexity hotspots, large files, potential god classes.

---

## Phase 13: Test Intelligence

### Test 13.1 — Tests for a file
```
What tests cover the EligibilityService?
```
**Expected:** Calls `mnemo_tests`. Shows test files that cover EligibilityService.

### Test 13.2 — Coverage summary
```
Give me a test coverage overview
```
**Expected:** Calls `mnemo_tests` (no query). Shows overall test coverage summary.

---

## Phase 14: Onboarding

### Test 14.1 — Generate onboarding guide
```
Give me a project onboarding guide for a new developer
```
**Expected:** Calls `mnemo_onboarding`. Returns a comprehensive overview of the project.

---

## Phase 15: Code Changes & Auto-Remember

### Test 15.1 — Make a change and verify it's remembered
```
Change the session timeout from 5 minutes to 10 minutes in the auth config
```
**Expected:** Makes the change AND calls `mnemo_remember` automatically (per the RULE).

### Test 15.2 — Verify change was remembered (NEW CHAT)
```
What was the last change made to the auth config?
```
**Expected:** Answers from memory: "Session timeout changed from 5 to 10 minutes."

---

## Phase 16: Refresh & Status

### Test 16.1 — Check status
```
Is Mnemo working?
```
**Expected:** Responds that Mnemo is active (based on successful recall).

### Test 16.2 — Refresh index
```
Refresh the code index
```
**Expected:** Calls `mnemo_map`. Confirms index refreshed.

---

## Phase 17: Multi-turn Memory Persistence

### Test 17.1 — Long conversation summary
Have a 10+ message conversation about refactoring a service, then start a NEW CHAT:
```
What did we discuss in the last conversation about refactoring?
```
**Expected:** The AI should have called `mnemo_remember` during the long conversation to summarize progress. New chat should have that summary in memory.

---

## Scoring

| Phase | Tests | Pass Criteria |
|-------|-------|---------------|
| 1. Memory & Recall | 5 | Memory persists across chats |
| 2. Code Understanding | 4 | Lookup works, results are remembered |
| 3. Semantic Search | 3 | Finds code by meaning, not just name |
| 4. Architecture | 4 | Intelligence report is accurate |
| 5. API Discovery | 2 | Endpoints found and searchable |
| 6. Knowledge Base | 2 | Docs are searchable |
| 7. Task Tracking | 3 | Task context is relevant |
| 8. Ownership & Team | 3 | Correct attribution (no merge commits) |
| 9. Error Memory | 2 | Errors stored and searchable |
| 10. Incidents | 2 | Incidents stored and searchable |
| 11. Code Reviews | 2 | Reviews stored and viewable |
| 12. Code Health | 1 | Report generated |
| 13. Test Intelligence | 2 | Tests found for files |
| 14. Onboarding | 1 | Guide generated |
| 15. Auto-Remember | 2 | Changes auto-saved to memory |
| 16. Status & Refresh | 2 | Status check and index refresh work |
| 17. Multi-turn | 1 | Long conversations are summarized |
| **Total** | **39** | |

---

## Quick Smoke Test (5 minutes)

If you only have 5 minutes, run these in order across 2 chats:

**Chat 1:**
1. "What's the architecture of this project?"
2. "Remember that we use OAuth2 with PKCE for frontend auth"
3. "Show me all payer handlers"

**Chat 2:**
4. "What auth pattern do we use?" → should answer from memory
5. "What handlers exist?" → should answer from memory

If Chat 2 answers both from memory without file reads, Mnemo is working correctly.
