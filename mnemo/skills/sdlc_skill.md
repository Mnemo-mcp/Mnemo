---
name: sdlc
description: Full SDLC pipeline — one prompt triggers investigation, planning, implementation, verification, review, and shipping via chained subagents. Each agent writes artifacts that the next agent reads.
inclusion: always
---

# SDLC Pipeline — Your Engineering Team

When the user asks you to build, add, fix, or implement something substantial (more than a one-line change), run the full pipeline below using subagents. Each subagent is a specialist that writes its output to `.mnemo/artifacts/` for the next specialist to read.

**When to trigger:** User says "build", "add feature", "implement", "create", or describes a feature/fix that requires planning.
**When NOT to trigger:** Quick questions, explanations, one-line fixes, config changes.

## The Pipeline

Run this using the `subagent` tool. Each stage depends on the previous one's output.

```json
{
  "task": "<USER'S REQUEST>",
  "stages": [
    {
      "name": "investigate",
      "role": "kiro_default",
      "prompt_template": "You are a senior engineer investigating a codebase before making changes.\n\nTask: {task}\n\nYour job:\n1. Find the relevant classes/files for this task\n2. Find WHO CALLS the code you'll be changing (blast radius)\n3. Find 2-3 similar implementations already in the codebase (patterns to follow)\n4. Identify risks (what could break)\n\nWrite your complete findings to .mnemo/artifacts/investigation.md in this format:\n\n# Investigation: <topic>\n\n## Target Files\n- <file path> — <what it does>\n\n## Callers (blast radius)\n- <file:class> — <how it uses the target>\n\n## Similar Implementations (patterns to follow)\n1. <file> — <how it does something similar>\n2. <file> — <alternative approach>\n\n## Risks\n- <what could break>\n- <edge cases>\n\n## Recommended Approach\n- <what to do based on findings>\n\nBe thorough. Read the actual source files. Find ALL callers via grep."
    },
    {
      "name": "plan",
      "role": "kiro_default",
      "depends_on": ["investigate"],
      "prompt_template": "You are a tech lead creating an implementation plan.\n\nTask: {task}\n\nFirst, read the investigation:\n```bash\ncat .mnemo/artifacts/investigation.md\n```\n\nBased on the investigation findings, create a plan with 3-8 tasks. Each task must have:\n- A clear action (verb + what + where)\n- Specific file targets\n- A done criterion\n\nWrite the plan to .mnemo/artifacts/plan.md in this format:\n\n# Plan: <feature name>\n\n## Approach\n<1-2 sentences summarizing the strategy based on investigation>\n\n## Tasks\n\n### Task 1: <verb> <what> in <file>\n- Files: <specific paths>\n- Done when: <testable criterion>\n- Pattern to follow: <reference from investigation>\n\n### Task 2: ...\n\n## Dependencies\n- Task N depends on Task M because...\n\nAlso create the plan in mnemo:\n```bash\nmnemo tool mnemo_plan --action create --title \"<feature>\" --tasks '[\"Task 1: ...\", \"Task 2: ...\"]'\n```\n\nAlso record your approach decision:\n```bash\nmnemo tool mnemo_decide --decision \"<approach for this feature>\" --reasoning \"<why, based on investigation>\"\n```"
    },
    {
      "name": "implement",
      "role": "kiro_default",
      "depends_on": ["plan"],
      "prompt_template": "You are a developer implementing a plan.\n\nTask: {task}\n\nFirst, read the plan:\n```bash\ncat .mnemo/artifacts/plan.md\n```\n\nImplement ALL tasks in the plan:\n1. For each task, read the file being modified first\n2. Follow the pattern referenced in the plan\n3. Write tests alongside every change (not after)\n4. Mark each task done after completing it:\n```bash\nmnemo tool mnemo_plan --action done --task_id \"<id>\" --summary \"<what you did>\"\n```\n\nAfter all tasks are done, write a summary to .mnemo/artifacts/implementation.md:\n\n# Implementation Summary\n\n## Changes Made\n- <file> — <what changed>\n\n## Tests Written\n- <test file> — <what it tests>\n\n## Patterns Followed\n- Followed <pattern> from <source file>\n\n## Notes\n- <anything the reviewer should know>"
    },
    {
      "name": "verify",
      "role": "kiro_default",
      "depends_on": ["implement"],
      "prompt_template": "You are a QA engineer verifying an implementation.\n\nTask: {task}\n\nFirst, read what was implemented:\n```bash\ncat .mnemo/artifacts/implementation.md\n```\n\nThen:\n1. Run the full test suite:\n```bash\nif [ -f pyproject.toml ] || [ -f pytest.ini ]; then python -m pytest --tb=short -q\nelif [ -f package.json ]; then npm test\nelif [ -f build.gradle ] || [ -f build.gradle.kts ]; then ./gradlew test --quiet\nelse echo 'No test runner detected'\nfi\n```\n\n2. If tests FAIL: fix them. Re-run until green.\n\n3. Check edge cases: null inputs, empty collections, error paths.\n\n4. Write results to .mnemo/artifacts/verification.md:\n\n# Verification Results\n\n## Test Suite: PASS / FAIL\n- <N> tests passed\n- Failures: <list if any, with fixes applied>\n\n## Edge Cases Checked\n- <what you verified>\n\n## Status: READY FOR REVIEW / BLOCKED\n- <reason if blocked>"
    },
    {
      "name": "review",
      "role": "kiro_default",
      "depends_on": ["verify"],
      "prompt_template": "You are a senior code reviewer.\n\nTask: {task}\n\nFirst, read verification results:\n```bash\ncat .mnemo/artifacts/verification.md\n```\n\nThen review the actual changes:\n```bash\ngit diff --stat\ngit diff\n```\n\nCheck these angles:\n\n## Security\n- [ ] SQL/shell injection (string interpolation in queries/commands)\n- [ ] Hardcoded secrets\n- [ ] Auth bypass (missing checks)\n- [ ] Path traversal\n\n## Performance  \n- [ ] N+1 queries\n- [ ] Unbounded collections\n- [ ] O(n²) in hot paths\n\n## Maintainability\n- [ ] Functions >50 lines\n- [ ] Magic numbers\n- [ ] Dead code\n- [ ] Unclear naming\n\n## Adversarial\n- [ ] What callers of changed code might break?\n- [ ] What if this is rolled back?\n- [ ] What would a malicious input do?\n\nFix mechanical issues immediately (unused imports, typos, dead code).\n\nWrite findings to .mnemo/artifacts/review.md:\n\n# Review Findings\n\n## Critical (must fix): <count>\n- <finding + fix applied>\n\n## Fixed Automatically: <count>\n- <what was fixed>\n\n## Accepted: <count>\n- <known limitation, documented>\n\n## Status: SHIP / BLOCKED\n\nAlso persist what you learned:\n```bash\nmnemo learn --type pitfall --key \"review-<topic>\" --insight \"<key finding from this review>\"\n```"
    },
    {
      "name": "ship",
      "role": "kiro_default",
      "depends_on": ["review"],
      "prompt_template": "You are a release engineer shipping code.\n\nTask: {task}\n\nFirst, check review results:\n```bash\ncat .mnemo/artifacts/review.md\n```\n\nIf status is BLOCKED: STOP. Report why and do not ship.\n\nIf status is SHIP, proceed:\n\n1. Verify tests still pass:\n```bash\nif [ -f pyproject.toml ]; then python -m pytest --tb=short -q\nelif [ -f package.json ]; then npm test\nelif [ -f build.gradle ]; then ./gradlew test --quiet\nfi\n```\n\n2. Generate commit message:\n```bash\nmnemo tool mnemo_generate --target commit\n```\n\n3. Commit:\n```bash\ngit add -A\ngit commit -m \"<type>(<scope>): <description>\"\n```\n\n4. Generate PR description:\n```bash\nmnemo tool mnemo_generate --target pr\n```\n\n5. Push and create PR:\n```bash\ngit push -u origin HEAD\ngh pr create --title \"<title>\" --body \"<description>\" 2>/dev/null || echo \"PR body saved to .mnemo/artifacts/pr-description.md\"\n```\n\n6. Record:\n```bash\nmnemo learn --type tool --key \"shipped-<topic>\" --insight \"Shipped: <what>, approach: <how>\"\n```\n\nWrite final status to .mnemo/artifacts/ship.md:\n\n# Ship Status\n\n## Commit: <hash>\n## PR: <url or 'manual'>\n## Summary: <what was shipped>"
    }
  ]
}
```

## How to Use

When you detect the user wants a full feature implemented, call the `subagent` tool with the JSON above (replacing `{task}` with the actual user request).

If the user wants to skip phases (e.g., "just review and ship"), only include the relevant stages.

## Artifacts Location

All inter-agent documents are written to `.mnemo/artifacts/`:
```
.mnemo/artifacts/
├── investigation.md    ← Investigator's findings
├── plan.md             ← Planner's task breakdown  
├── implementation.md   ← Developer's change summary
├── verification.md     ← QA's test results
├── review.md           ← Reviewer's findings
├── ship.md             ← Ship status + PR link
└── pr-description.md   ← PR body (if gh not available)
```
