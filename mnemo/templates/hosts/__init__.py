"""Host adapter configs — one per AI client.

Each host defines:
- skills_path: where to install SKILL.md files
- frontmatter: what metadata fields to keep/transform
- path_rewrites: string replacements for host-specific paths
- suppressed_resolvers: features this host doesn't support
"""

from __future__ import annotations

from typing import Any

HOSTS: dict[str, dict[str, Any]] = {
    "kiro": {
        "name": "kiro",
        "display_name": "Kiro",
        "skills_path": ".kiro/skills",
        "frontmatter_fields": ["name", "description", "inclusion"],
        "path_rewrites": {},
        "suppressed_resolvers": [],
    },
    "claude": {
        "name": "claude",
        "display_name": "Claude Code",
        "skills_path": ".claude/skills",
        "frontmatter_fields": ["name", "description"],
        "path_rewrites": {
            ".kiro/skills": ".claude/skills",
            ".kiro/hooks": ".claude/hooks",
        },
        "suppressed_resolvers": [],
    },
    "cursor": {
        "name": "cursor",
        "display_name": "Cursor",
        "skills_path": ".cursor/skills",
        "frontmatter_fields": ["name", "description"],
        "path_rewrites": {
            ".kiro/skills": ".cursor/skills",
        },
        "suppressed_resolvers": [],
    },
    "amazonq": {
        "name": "amazonq",
        "display_name": "Amazon Q",
        "skills_path": ".amazonq/skills",
        "frontmatter_fields": ["name", "description"],
        "path_rewrites": {
            ".kiro/skills": ".amazonq/skills",
        },
        "suppressed_resolvers": [],
    },
}


def get_host_config(host: str) -> dict[str, Any]:
    """Get config for a host. Falls back to kiro if unknown."""
    return HOSTS.get(host, HOSTS["kiro"])


def list_hosts() -> list[str]:
    """List all supported host names."""
    return list(HOSTS.keys())
