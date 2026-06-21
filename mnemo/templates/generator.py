"""Template generator — transforms SKILL.md.tmpl → SKILL.md per host.

Same pattern as gstack's gen-skill-docs.ts:
1. Read template file (SKILL.md.tmpl)
2. For each {{PLACEHOLDER}}: look up resolver, call it, replace
3. Apply host-specific transforms (path rewrites, frontmatter)
4. Write output to host's skill directory
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from . import RESOLVERS
from .hosts import get_host_config


def generate_skill(
    template: str,
    repo_root: Path,
    host: str = "kiro",
    context: dict[str, Any] | None = None,
) -> str:
    """Resolve a skill template into final SKILL.md content.

    Args:
        template: Raw template content with {{PLACEHOLDER}} markers.
        repo_root: Repository root for context.
        host: Target host (kiro, claude, cursor, amazonq).
        context: Additional context (skill_name, etc.).

    Returns:
        Resolved SKILL.md content ready to write.
    """
    ctx = context or {}
    host_config = get_host_config(host)

    # Resolve all {{PLACEHOLDER}} markers
    def replacer(match: re.Match) -> str:
        name = match.group(1)
        resolver = RESOLVERS.get(name)
        if resolver is None:
            return match.group(0)  # Leave unresolved placeholders as-is
        return resolver(repo_root, ctx)

    resolved = re.sub(r"\{\{(\w+)\}\}", replacer, template)

    # Apply host-specific path rewrites
    for old, new in host_config.get("path_rewrites", {}).items():
        resolved = resolved.replace(old, new)

    return resolved


def generate_all_skills(
    repo_root: Path,
    host: str = "kiro",
    templates_dir: Path | None = None,
) -> dict[str, str]:
    """Generate all skills from templates for a given host.

    Args:
        repo_root: Repository root.
        host: Target host.
        templates_dir: Directory containing SKILL.md.tmpl files.
                      Defaults to mnemo/skills/templates/.

    Returns:
        Dict of {skill_name: resolved_content}.
    """
    if templates_dir is None:
        templates_dir = Path(__file__).parent.parent / "skills" / "templates"

    results = {}
    if not templates_dir.exists():
        return results

    for tmpl_path in templates_dir.glob("*/SKILL.md.tmpl"):
        skill_name = tmpl_path.parent.name
        template = tmpl_path.read_text(encoding="utf-8")
        context = {"skill_name": skill_name, "host": host}
        resolved = generate_skill(template, repo_root, host=host, context=context)
        results[skill_name] = resolved

    return results


def install_skills(repo_root: Path, host: str = "kiro") -> list[str]:
    """Generate and install all skills for a host.

    Returns list of installed skill names.
    """
    host_config = get_host_config(host)
    skills_dir = repo_root / host_config["skills_path"]
    generated = generate_all_skills(repo_root, host=host)

    installed = []
    for name, content in generated.items():
        skill_dir = skills_dir / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")
        installed.append(name)

    return installed
