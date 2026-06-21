"""Production-grade workflow skill templates — SHELL COMMAND pattern.

Agent runs shell commands 33x per session but MCP tools 0x.
So every skill uses `mnemo tool <name> --args` shell commands, NOT "call mnemo_*".
This is the gstack pattern: shell commands in code blocks that the agent copies and runs.
"""

SKILL_INVESTIGATE = '''---
name: investigate
description: Deep codebase understanding before making changes. Maps dependencies, finds analogous implementations, identifies risks. Run this before any non-trivial code change.
inclusion: on-demand
---

# /investigate — Understand Before You Touch Anything

You are a senior engineer doing rigorous due diligence. READ-ONLY phase — no code changes.

## Hard Rules

1. NO code changes. Write findings down, don't fix things yet.
2. You MUST run the lookup and impact commands below.
3. You MUST find at least 2 analogous implementations.
4. You MUST persist what you learned at the end.

## Step 1: Define Scope

State: what are we investigating, why, and what's out of scope.

## Step 2: Map Architecture

Run these commands to understand the target:

```bash
mnemo tool mnemo_lookup --symbol "<primary class or module>"
```

```bash
mnemo tool mnemo_impact --symbol "<target>" --direction both
```

```bash
mnemo tool mnemo_graph --action neighbors --node "<target>"
```

From the output, document:
- Methods/functions in this class
- Who calls this (callers)
- What this depends on (callees)
- Full blast radius

If lookup returns nothing, find the correct name:
```bash
mnemo tool mnemo_graph --action find --name "<partial name>"
```

## Step 3: Find Analogous Implementations (minimum 2)

```bash
mnemo tool mnemo_search --query "<what you need to understand>" --scope code
```

Then look up each analogue:
```bash
mnemo tool mnemo_lookup --symbol "<similar class from results>"
```

Document: what file, how it handles the same problem, what conventions it follows.

## Step 4: Check Memory

```bash
mnemo tool mnemo_search --query "<topic>" --scope memory
```

Look for: past decisions, known pitfalls, existing conventions.

## Step 5: Identify Risks

From the impact results:
- Breaking changes if you modify this interface
- Edge cases: null, empty, timeout, concurrent access
- Security: user input, auth, file paths, SQL

## Step 6: Persist Findings

```bash
mnemo learn --type architecture --key "<area>-structure" --insight "<most important finding about what exists and how it works>"
```

If you found a risk:
```bash
mnemo learn --type pitfall --key "<area>-risk" --insight "<what could go wrong and why>"
```

## You Are Not Done If

- You did not run `mnemo tool mnemo_lookup`
- You did not run `mnemo tool mnemo_impact`
- You did not find 2 analogous implementations (or stated none exist)
- You did not run `mnemo learn`
'''

SKILL_PLAN = '''---
name: plan
description: Break work into tracked, file-targeted tasks with done criteria. Creates a mnemo plan with dependencies. Run after /investigate.
inclusion: on-demand
---

# /plan — Break Work Into Executable Tasks

You are a tech lead writing a plan a junior developer could execute without questions.

## Hard Rules

1. Every task MUST target specific files (not "update the code").
2. Every task MUST have a done criterion (testable, binary).
3. Tasks MUST be ≤30 minutes each.
4. 3-8 tasks per plan.
5. You MUST create the plan via the command below.

## Step 1: Load Context

```bash
cat .mnemo/investigation.md 2>/dev/null || echo "No investigation file"
```

```bash
mnemo recall
```

## Step 2: Estimate Impact

```bash
mnemo tool mnemo_impact --symbol "<primary thing being changed>"
```

How many files affected? Is this a leaf change or trunk change?

## Step 3: Decompose Into Tasks

Each task follows: `<verb> <what> in <where>`
- Verb: Add, Create, Modify, Extract, Wire, Test
- File paths specific
- Done criterion binary

## Step 4: Create Plan

```bash
mnemo tool mnemo_plan --action create --title "<feature name>" --tasks '["Task 1: <desc>", "Task 2: <desc>", "Task 3: <desc>"]'
```

## Step 5: Record Approach

```bash
mnemo tool mnemo_decide --decision "Implementation approach for <feature>: <strategy>" --reasoning "<why this over alternatives>"
```

## You Are Not Done If

- Tasks don't have specific file targets
- Tasks don't have done criteria
- You didn't run `mnemo tool mnemo_plan --action create`
- You didn't run `mnemo tool mnemo_decide`
'''

SKILL_IMPLEMENT = '''---
name: implement
description: Write code following project conventions. Find pattern first via lookup, write tests alongside, mark tasks done. Run after /plan.
inclusion: on-demand
---

# /implement — Write Code The Way This Project Does It

You are a disciplined developer who never invents patterns — always follows existing ones.

## Hard Rules

1. Find the pattern BEFORE writing. Run the lookup command below first.
2. Write tests ALONGSIDE (same commit, not after).
3. Mark tasks done immediately after completing each one.
4. State which pattern you're following and from which file.

## Step 1: Load Plan

```bash
mnemo tool mnemo_plan --action status
```

Identify the NEXT pending task. Work on ONE at a time.

## Step 2: Find the Pattern

BEFORE writing any new code:

```bash
mnemo tool mnemo_lookup --symbol "<most similar existing class>"
```

```bash
mnemo tool mnemo_search --query "<what you're building>" --scope code
```

State: "Following pattern from `<file>:<class>` which does `<similar thing>`."

## Step 3: Check Conventions

```bash
mnemo tool mnemo_search --query "conventions" --scope memory
```

Follow: naming, file structure, error handling, import patterns from memory.

## Step 4: Implement + Test

Write the code following the pattern. For every file you create/modify, write a test in the same commit.

## Step 5: Mark Task Done

```bash
mnemo tool mnemo_plan --action done --task_id "<id>" --summary "Implemented <what> following pattern from <file>"
```

## Step 6: Persist

```bash
mnemo learn --type pattern --key "<what-you-built>" --insight "Implemented <thing> in <file>. Followed pattern from <source>. Key choice: <why>."
```

## Step 7: Repeat

Go to Step 1. Next pending task. Until plan is complete.

## You Are Not Done If

- You didn't run `mnemo tool mnemo_lookup` before writing new code
- Any new file lacks a test
- Plan tasks are not marked done via `mnemo tool mnemo_plan --action done`
'''

SKILL_VERIFY = '''---
name: verify
description: Run full test suite, check callers of changed interfaces, test edge cases. Run after /implement.
inclusion: on-demand
---

# /verify — Prove It Works and Doesn't Break Others

You are a QA engineer who assumes everything is broken until proven otherwise.

## Hard Rules

1. Run the FULL test suite (not just new tests).
2. Check ALL callers of changed interfaces via the command below.
3. STOP if tests fail. Fix first, don't proceed.

## Step 1: Run Tests

```bash
# Detect and run:
if [ -f pyproject.toml ] || [ -f pytest.ini ]; then python -m pytest --tb=short -q
elif [ -f package.json ]; then npm test
elif [ -f pom.xml ]; then mvn test -q
elif [ -f build.gradle ] || [ -f build.gradle.kts ]; then ./gradlew test --quiet
else echo "No test runner detected"
fi
```

If tests FAIL → fix them NOW. Do not proceed.

## Step 2: Check Callers of Changed Interfaces

```bash
mnemo tool mnemo_impact --symbol "<changed class or method>"
```

For EACH caller: does it handle the new behavior? If you changed a signature, ALL callers must be updated.

## Step 3: Edge Cases

Test explicitly:
- Null/empty input
- Boundary values
- Error paths (dependency throws)
- Concurrent access (if applicable)

## Step 4: Persist

```bash
mnemo learn --type tool --key "verify-<feature>" --insight "Verified: <N> tests pass, <N> callers checked, edge cases: <which>"
```

## Quality Gate

✅ Tests pass → proceed to /review
❌ Tests fail → STOP. Fix first.
'''

SKILL_REVIEW = '''---
name: review
description: Two-pass code review. Pass 1 checks CRITICAL issues. Pass 2 runs specialist angles. Fix-first protocol. Run after /verify.
inclusion: on-demand
---

# /review — Structured Multi-Angle Review

You are 4 reviewers examining the diff. Every finding gets actioned — no "informational only."

## Hard Rules

1. Every finding: fix it (mechanical) or explicitly accept it (judgment).
2. Check what you DIDN'T change (callers, consumers).
3. Fix mechanical issues immediately (unused imports, typos).
4. Only surface findings you're ≥7/10 confident about.

## Step 1: Get the Diff

```bash
git diff --stat $(git merge-base HEAD main 2>/dev/null || git merge-base HEAD master 2>/dev/null || echo "HEAD~5")
```

## Pass 1 — CRITICAL Checklist

- [ ] SQL injection (string interpolation in queries)
- [ ] Shell injection (user input in subprocess)
- [ ] Path traversal (user input in file paths)
- [ ] Hardcoded secrets
- [ ] Auth bypass (missing middleware)
- [ ] N+1 queries (loop with DB call inside)
- [ ] Race conditions (read-check-write without locking)
- [ ] New enum value not handled in all consumers

Run automated scan:
```bash
mnemo tool mnemo_audit --report security
```

## Pass 2 — Specialist Angles

### Adversarial (most important)

```bash
mnemo tool mnemo_impact --symbol "<primary changed class>"
```

Check each caller: does it handle the new behavior?
What if this change is rolled back — is data corrupted?

### Performance
- O(n²) in request path?
- Unbounded queries?
- Missing indexes?

### Maintainability
- Functions >50 lines?
- Magic numbers?
- Dead code?

## Step 3: Fix-First Protocol

**Mechanical** (typo, unused import): fix it immediately.
**Judgment** (architecture choice): state tradeoff, recommend, proceed if ≥7/10 confidence.
**Critical** (security hole): MUST fix before /ship.

## Step 4: Persist

```bash
mnemo learn --type pitfall --key "review-<feature>" --insight "Review found: <key findings and how resolved>"
```

## Quality Gate

✅ No unresolved critical findings → proceed to /ship
❌ Critical findings remain → STOP. Fix first.
'''

SKILL_SHIP = '''---
name: ship
description: Verify all gates, generate commit + PR, submit. The final step. Run after /review.
inclusion: on-demand
---

# /ship — Verify Gates Then Submit

You are a release engineer who ships with confidence.

## Hard Rules

1. Do NOT ship if any gate fails. STOP and report which failed.
2. Commit messages follow conventional commits.
3. PR description includes WHY (from memory/decisions).
4. Can be re-run safely (idempotent).

## Step 1: Check Plan Completion

```bash
mnemo tool mnemo_plan --action status
```

⛔ If tasks pending → STOP. Go back to /implement.

## Step 2: Run Tests

```bash
# Use project's test runner:
if [ -f pyproject.toml ] || [ -f pytest.ini ]; then python -m pytest --tb=short -q
elif [ -f package.json ]; then npm test
elif [ -f build.gradle ] || [ -f build.gradle.kts ]; then ./gradlew test --quiet
fi
```

⛔ If tests fail → STOP. Fix first.

## Step 3: Generate Commit Message

```bash
mnemo tool mnemo_generate --target commit
```

Must follow: `<type>(<scope>): <description>`
Types: feat, fix, refactor, test, docs, chore

## Step 4: Commit

```bash
git add -A
git status
git commit -m "<generated message>"
```

## Step 5: Generate PR Description

```bash
mnemo tool mnemo_generate --target pr
```

## Step 6: Push + Create PR

```bash
git push -u origin HEAD
gh pr create --title "<title>" --body "<PR description>"
```

## Step 7: Record

```bash
mnemo learn --type tool --key "shipped-<feature>" --insight "Shipped: <summary>. Approach: <key decision>."
```

## You Are Not Done If

- You shipped with failing tests
- Plan has pending tasks
- Commit message doesn't follow conventional commits
- You didn't run `mnemo learn` to record the shipment
'''

# Map skill name → content for installation
WORKFLOW_SKILLS = {
    "investigate": SKILL_INVESTIGATE,
    "plan": SKILL_PLAN,
    "implement": SKILL_IMPLEMENT,
    "verify": SKILL_VERIFY,
    "review": SKILL_REVIEW,
    "ship": SKILL_SHIP,
}
