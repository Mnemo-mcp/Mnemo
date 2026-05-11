"""Dead code detector - uses repo map symbols and single in-memory scan."""

from __future__ import annotations

from pathlib import Path

from ..config import SUPPORTED_EXTENSIONS, mnemo_path
from ..repo_map import _extract_file, _should_ignore, MAX_FILE_SIZE
from ..storage import Collections, get_storage


def detect_dead_code(repo_root: Path) -> str:
    """Scan for potentially unused classes and functions using in-memory search."""
    # 1. Collect all symbols with full signatures
    symbols: list[dict] = []
    file_contents: dict[str, str] = {}

    for ext, language in SUPPORTED_EXTENSIONS.items():
        for filepath in repo_root.rglob(f"*{ext}"):
            if _should_ignore(filepath) or filepath.stat().st_size > MAX_FILE_SIZE:
                continue
            rel = str(filepath.relative_to(repo_root))
            if "test" in rel.lower():
                continue
            try:
                source = filepath.read_bytes()
            except (OSError, PermissionError):
                continue

            file_contents[rel] = source.decode(errors="replace")

            info = _extract_file(source, language)
            if not info:
                continue

            for cls in info.get("classes", []):
                name = cls["name"]
                if name.startswith("_"):
                    continue
                impl = cls.get("implements", "")
                symbols.append({
                    "name": name, "type": "class", "file": rel,
                    "signature": f"class {name}" + (f" : {impl}" if impl else ""),
                    "methods": cls.get("methods", []),
                })
                for method in cls.get("methods", []):
                    mname = method.split("(")[0].split()[-1] if method else ""
                    if mname and not mname.startswith("_") and mname not in (
                        "__init__", "constructor", "main",
                    ):
                        symbols.append({
                            "name": mname, "type": "method", "file": rel,
                            "class": name, "signature": method,
                        })

            for func in info.get("functions", []):
                fname = func.split("(")[0].replace("def ", "").replace("func ", "").strip()
                if fname.startswith("_") or fname in ("main", "cli"):
                    continue
                symbols.append({"name": fname, "type": "function", "file": rel, "signature": func})

    if not symbols:
        return "No potentially dead code detected."

    # 2. Load remaining files (tests, etc.) into corpus — they count as usage
    for ext, language in SUPPORTED_EXTENSIONS.items():
        for filepath in repo_root.rglob(f"*{ext}"):
            if _should_ignore(filepath) or filepath.stat().st_size > MAX_FILE_SIZE:
                continue
            rel = str(filepath.relative_to(repo_root))
            if rel in file_contents:
                continue
            try:
                file_contents[rel] = filepath.read_bytes().decode(errors="replace")
            except (OSError, PermissionError):
                continue

    # 3. For each symbol, find all files that reference it
    unused = []
    for sym in symbols:
        name = sym["name"]
        refs = [rel for rel, content in file_contents.items() if name in content]
        # Only in its own file (or nowhere) = potentially dead
        if len(refs) <= 1:
            sym["referenced_in"] = refs
            unused.append(sym)

    if not unused:
        return "No potentially dead code detected."

    # 4. Build detailed report
    lines = [f"# Potentially Unused Code ({len(unused)} symbols)\n"]
    lines.append("These symbols are only referenced in their definition file.\n")

    by_file: dict[str, list[dict]] = {}
    for sym in unused:
        by_file.setdefault(sym["file"], []).append(sym)

    for file, syms in sorted(by_file.items()):
        lines.append(f"## `{file}`\n")
        for s in syms:
            parent = f" (in `{s['class']}`)" if s.get("class") else ""
            lines.append(f"### {s['type']}: `{s['name']}`{parent}")
            lines.append(f"- **Signature:** `{s['signature']}`")
            lines.append(f"- **Defined in:** `{s['file']}`")
            refs = s.get("referenced_in", [])
            if refs:
                lines.append(f"- **Only found in:** `{refs[0]}`")
            else:
                lines.append("- **Referenced in:** nowhere (completely unreachable)")
            # For classes, show their methods for context
            if s["type"] == "class" and s.get("methods"):
                lines.append(f"- **Methods:** {', '.join(f'`{m.split(chr(40))[0].split()[-1]}`' for m in s['methods'][:10])}")
            lines.append("")

    lines.append("---")
    lines.append("*Note: Some may be used via reflection, dependency injection, dynamic dispatch, or external consumers (e.g. framework routing, JSON deserialization).*")
    return "\n".join(lines)
