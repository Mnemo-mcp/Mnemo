"""Output generation: summary, compact tree, repo map."""

from __future__ import annotations

import hashlib
from pathlib import Path

from ..config import SUPPORTED_EXTENSIONS, mnemo_path
from ..chunking import make_code_chunks
from ..retrieval import index_chunks
from ..utils.logger import get_logger

from .scanner import _should_ignore, _save_hashes, MAX_FILE_SIZE
from .parsers import _extract_file

logger = get_logger("repo_map")


def generate_summary(repo_root: Path, index: bool = True) -> str:
    """Generate a compact markdown summary of the repo structure."""
    tree: dict[str, dict[str, list[str]]] = {}
    hashes: dict[str, str] = {}
    all_chunks = []

    # Try Roslyn for C# if .NET SDK is available
    from ..analyzers import roslyn_available, run_roslyn_analyzer, roslyn_to_mnemo_format
    roslyn_data: dict[str, dict] = {}
    if roslyn_available(repo_root):
        results = run_roslyn_analyzer(repo_root)
        if results:
            roslyn_data = roslyn_to_mnemo_format(results, repo_root)

    for ext, language in SUPPORTED_EXTENSIONS.items():
        for filepath in repo_root.rglob(f"*{ext}"):
            if _should_ignore(filepath) or filepath.stat().st_size > MAX_FILE_SIZE:
                continue
            try:
                source = filepath.read_bytes()
            except (OSError, PermissionError):
                continue

            rel = str(filepath.relative_to(repo_root))
            hashes[rel] = hashlib.md5(source, usedforsecurity=False).hexdigest()

            parts = rel.split("/")
            module = parts[0] if len(parts) > 1 else "."
            submodule = parts[1] if len(parts) > 2 else "_root"
            if module not in tree:
                tree[module] = {}
            if submodule not in tree[module]:
                tree[module][submodule] = []

            # Use Roslyn data if available for this file, else tree-sitter
            info = roslyn_data.get(rel) or _extract_file(source, language)
            rel_short = "/".join(parts[1:]) or rel
            if info:
                all_chunks.extend(make_code_chunks(rel, language, info))

            if info and info.get("classes"):
                class_names = []
                for cls in info["classes"]:
                    name = cls["name"]
                    impl = f" : {cls['implements']}" if cls.get("implements") else ""
                    class_names.append(f"`{name}{impl}`")
                tree[module][submodule].append(f"  {rel_short} → {', '.join(class_names)}")
            elif info and info.get("functions"):
                tree[module][submodule].append(f"  {rel_short} ({len(info['functions'])} functions)")
            else:
                tree[module][submodule].append(f"  {rel_short}")

    # Save hashes
    _save_hashes(repo_root, hashes)

    # Build markdown
    lines = []
    for module in sorted(tree.keys()):
        lines.append(f"**{module}/**")
        for submodule in sorted(tree[module].keys()):
            if submodule != "_root":
                lines.append(f"  - {submodule}/")
            for entry in sorted(tree[module][submodule]):
                lines.append(entry)
    if index and all_chunks:
        index_chunks(repo_root, "code", all_chunks)
    return "\n".join(lines)


def save_summary(repo_root: Path, index: bool = True) -> Path:
    """Generate and save the markdown summary."""
    summary = generate_summary(repo_root, index=index)
    out = mnemo_path(repo_root) / "summary.md"
    out.write_text(summary, encoding="utf-8")
    # Also generate compact tree for recall/context files
    compact = generate_compact_tree(repo_root)
    compact_out = mnemo_path(repo_root) / "tree.md"
    compact_out.write_text(compact, encoding="utf-8")
    return out


def save_repo_map(repo_root: Path, index: bool = True) -> Path:
    """Generate summary, compact tree, and knowledge graph."""
    result = save_summary(repo_root, index=index)
    # Build knowledge graph
    try:
        from ..graph.builder import build_graph
        build_graph(repo_root)
    except Exception as exc:
        logger.warning(f"Graph build failed (non-fatal): {exc}")
    return result


def generate_compact_tree(repo_root: Path) -> str:
    """Generate a compact tree showing structure + key classes per module (for recall)."""
    modules: dict[str, dict] = {}

    for ext, language in SUPPORTED_EXTENSIONS.items():
        for filepath in repo_root.rglob(f"*{ext}"):
            if _should_ignore(filepath) or filepath.stat().st_size > MAX_FILE_SIZE:
                continue
            try:
                source = filepath.read_bytes()
            except (OSError, PermissionError):
                continue

            rel = str(filepath.relative_to(repo_root))
            parts = rel.split("/")
            module = parts[0] if len(parts) > 1 else "."
            submodule = parts[1] if len(parts) > 2 else "_root"

            if module not in modules:
                modules[module] = {"subs": {}, "classes": [], "funcs": 0}
            if submodule not in modules[module]["subs"]:
                modules[module]["subs"][submodule] = 0
            modules[module]["subs"][submodule] += 1

            info = _extract_file(source, language)
            if info:
                for cls in info.get("classes", []):
                    name = cls["name"]
                    impl = cls.get("implements", "")
                    entry = f"{name} : {impl}" if impl else name
                    modules[module]["classes"].append(entry)
                modules[module]["funcs"] += len(info.get("functions", []))

    lines = []
    for module in sorted(modules.keys()):
        total = sum(modules[module]["subs"].values())
        lines.append(f"{module}/ ({total} files)")
        for sub in sorted(modules[module]["subs"].keys()):
            if sub != "_root":
                lines.append(f"  {sub}/")
        classes = sorted(set(modules[module]["classes"]))
        if classes:
            shown = classes[:8]
            lines.append(f"  Key classes: {', '.join(shown)}")
            if len(classes) > 8:
                lines.append(f"  ... +{len(classes) - 8} more classes")
        if modules[module]["funcs"]:
            lines.append(f"  Functions: {modules[module]['funcs']}")

    return "\n".join(lines)
