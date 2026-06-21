"""Knowledge MCP — team knowledge base from markdown files."""

from __future__ import annotations

from pathlib import Path

from ..config import mnemo_path

KNOWLEDGE_DIR = "knowledge"


def _knowledge_path(repo_root: Path) -> Path:
    return mnemo_path(repo_root) / KNOWLEDGE_DIR


def init_knowledge(repo_root: Path) -> Path:
    """Create the knowledge directory with a README."""
    kdir = _knowledge_path(repo_root)
    kdir.mkdir(parents=True, exist_ok=True)
    readme = kdir / "README.md"
    if not readme.exists():
        readme.write_text(
            "# Project Knowledge Base\n\n"
            "Add markdown files here for team knowledge that Amazon Q should know about.\n\n"
            "Examples:\n"
            "- `runbooks.md` — deployment and debugging procedures\n"
            "- `architecture.md` — system design decisions\n"
            "- `standards.md` — coding conventions and requirements\n"
            "- `onboarding.md` — project overview for new team members\n"
            "- `gotchas.md` — common pitfalls and workarounds\n"
        )
    return kdir


def search_knowledge(repo_root: Path, query: str) -> str:
    """Search knowledge base for relevant content."""
    kdir = _knowledge_path(repo_root)
    if not kdir.exists():
        return "No knowledge base found. Create markdown files in `.mnemo/knowledge/`."

    query_lower = query.lower()
    results: list[tuple[str, str]] = []

    for md_file in kdir.rglob("*.md"):
        try:
            content = md_file.read_text()
        except (OSError, PermissionError):
            continue

        # Score by how many query words appear
        score = sum(1 for word in query_lower.split() if word in content.lower())
        if score > 0:
            # Extract relevant section
            lines = content.splitlines()
            relevant_lines = []
            for i, line in enumerate(lines):
                if any(word in line.lower() for word in query_lower.split()):
                    # Get surrounding context (3 lines before/after)
                    start = max(0, i - 3)
                    end = min(len(lines), i + 4)
                    relevant_lines.extend(lines[start:end])
                    relevant_lines.append("---")

            if relevant_lines:
                name = md_file.relative_to(kdir)
                excerpt = "\n".join(relevant_lines[:50])
                results.append((str(name), excerpt))

    if not results:
        # Return all file names as suggestions
        files = [str(f.relative_to(kdir)) for f in kdir.rglob("*.md")]
        return f"No results for '{query}'. Available knowledge files: {', '.join(files)}"

    lines = [f"# Knowledge: '{query}'\n"]
    for name, excerpt in results[:5]:
        lines.append(f"## {name}")
        lines.append(excerpt)
        lines.append("")

    return "\n".join(lines)


def list_knowledge(repo_root: Path) -> str:
    """List all knowledge base files with their headings."""
    kdir = _knowledge_path(repo_root)
    if not kdir.exists():
        return "No knowledge base. Create `.mnemo/knowledge/` with markdown files."

    lines = ["# Knowledge Base\n"]
    for md_file in sorted(kdir.rglob("*.md")):
        name = md_file.relative_to(kdir)
        try:
            content = md_file.read_text()
            # Get first heading or first line
            for line in content.splitlines():
                if line.strip():
                    lines.append(f"- **{name}** — {line.strip('#').strip()}")
                    break
        except (OSError, PermissionError):
            lines.append(f"- **{name}**")

    return "\n".join(lines)
