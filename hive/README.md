# Hive

**Shared team knowledge for Mnemo-powered teams.**

Your personal Mnemo remembers what YOU learned. Hive remembers what the TEAM learned. When anyone solves a hard problem, debugs a tricky issue, or makes an architectural decision — Hive makes it available to everyone's agent automatically.

## Quick Start

```bash
# Initialize hive (creates or clones the shared repo)
mnemo hive init

# Contribute knowledge
mnemo hive contribute

# Search team knowledge
mnemo hive search "retry patterns"

# Pull latest from team
mnemo hive pull
```

## How It Works

```
Engineer A solves a gnarly bug
       ↓
mnemo hive contribute → writes it up as structured markdown
       ↓
Pushed to shared git repo (PR reviewed by team)
       ↓
Engineer B's agent auto-pulls on next session
       ↓
When B hits a similar problem → agent finds A's solution in Hive
```

The agent searches **both** personal memory AND Hive together. No extra commands needed — it just knows more.

## What Belongs in Hive

| Type | When to Contribute | Example |
|------|---|---|
| **Pattern** | Reusable solution to a recurring problem | "Cache-aside with per-tenant TTL" |
| **Gotcha** | Non-obvious trap you fell into | "Azure Function cold start kills DI with EF Core" |
| **Decision** | Team made a significant architectural choice | "Why we chose Service Bus over direct HTTP" |
| **Playbook** | Step-by-step for a recurring scenario | "Debugging EDI 271 response parsing failures" |

## What Does NOT Belong

- Personal notes or WIP
- Secrets, credentials, PII
- One-off fixes unlikely to recur
- Content that's already in your wiki and better left there

## Auto-Suggest

When the Mnemo council catches something during evaluation, it checks: "Is this team-relevant?" If yes, it suggests:

```
💡 The council caught a pattern: "Redis timeout with no fallback is a recurring 
   issue in this codebase (3rd time caught)."
   
   → Contribute to Hive? (mnemo hive contribute --type gotcha)
```

## Directory Structure

```
~/.mnemo/hive/                    ← Local clone of shared repo
├── knowledge/
│   ├── patterns/                 ← Reusable solutions
│   ├── gotchas/                  ← Non-obvious traps
│   ├── decisions/                ← ADRs (Architecture Decision Records)
│   ├── playbooks/                ← Step-by-step procedures
│   └── onboarding/              ← Getting-started knowledge
├── templates/                    ← Contribution templates
└── docs/                         ← Hive maintenance docs
```

## Contributing

```bash
# Interactive (picks template, opens editor)
mnemo hive contribute

# Quick contribute from last council finding
mnemo hive contribute --from-council

# Direct (specify type)
mnemo hive contribute --type gotcha --title "EF Core in Azure Functions"
```

Every contribution:
1. Uses a template (YAML frontmatter + structured sections)
2. Creates a branch + commit
3. Opens a PR for team review
4. Once merged → available to everyone on next `hive pull`

## Comparison to Atlas Nexus

| Feature | Atlas Nexus | Mnemo Hive |
|---------|---|---|
| Storage | Git repo | Git repo |
| Search | Kiro knowledge tool | Mnemo's triple-stream search (BM25 + vector + graph) |
| Auto-pull | On session start | On session start |
| Auto-suggest contributions | ❌ No | ✅ Council suggests team-relevant findings |
| Personal + shared search | Separate | Unified (one search, both sources) |
| Contribution | Manual file creation | `mnemo hive contribute` (interactive CLI) |
| Quality gate | MR review | MR review + optional freshness expiry |
| Works without team repo | ❌ | ✅ (local-only mode for solo devs) |
