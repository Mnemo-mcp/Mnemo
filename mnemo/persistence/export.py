"""Export Mnemo data to external formats (Obsidian, etc.)."""

from __future__ import annotations

import json
from pathlib import Path

from ..config import mnemo_path


def export_obsidian(repo_root: Path, output_dir: Path) -> str:
    """Export memories and decisions as Obsidian-compatible markdown with YAML frontmatter."""
    base = mnemo_path(repo_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    decisions_dir = output_dir / "decisions"
    decisions_dir.mkdir(exist_ok=True)
    count = 0
    links: list[str] = []

    # Export memories
    mem_file = base / "memory.json"
    if mem_file.exists():
        for m in json.loads(mem_file.read_text()):
            mid = m.get("id", count)
            fname = f"memory-{mid}.md"
            frontmatter = (
                f"---\nid: {mid}\ncategory: {m.get('category', 'general')}\n"
                f"tags: [{', '.join(m.get('tags', []))}]\n"
                f"created: {m.get('timestamp', '')}\nconfidence: {m.get('confidence', 1.0)}\n---\n\n"
            )
            (output_dir / fname).write_text(frontmatter + m.get("content", ""), encoding="utf-8")
            links.append(f"- [[memory-{mid}]]")
            count += 1

    # Export decisions
    dec_file = base / "decisions.json"
    if dec_file.exists():
        for d in json.loads(dec_file.read_text()):
            did = d.get("id", count)
            fname = f"decision-{did}.md"
            frontmatter = (
                f"---\nid: {did}\ncategory: decision\ntags: [decision]\n"
                f"created: {d.get('timestamp', '')}\nconfidence: 1.0\n---\n\n"
            )
            body = d.get("decision", "") + ("\n\n**Reasoning:** " + d.get("reasoning", "") if d.get("reasoning") else "")
            (decisions_dir / fname).write_text(frontmatter + body, encoding="utf-8")
            links.append(f"- [[decisions/decision-{did}]]")
            count += 1

    # Generate MOC
    moc = "# Map of Content\n\n" + "\n".join(links) if links else "# Map of Content\n\nNo entries."
    (output_dir / "MOC.md").write_text(moc, encoding="utf-8")
    count += 1

    return f"Exported {count} files to {output_dir}"
