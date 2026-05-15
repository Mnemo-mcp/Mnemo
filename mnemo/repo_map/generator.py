"""Output generation: summary, compact tree, repo map."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from ..config import SUPPORTED_EXTENSIONS, mnemo_path
from ..chunking import make_code_chunks
from ..retrieval import index_chunks
from ..utils.logger import get_logger

from .scanner import _should_ignore, _save_hashes, _load_hashes, MAX_FILE_SIZE
from .parsers import _extract_file

logger = get_logger("repo_map")


def _save_index_manifest(repo_root: Path, files: set[str]) -> None:
    """Track indexed files in .mnemo/index_manifest.json."""
    import json
    manifest_path = mnemo_path(repo_root) / "index_manifest.json"
    manifest_path.write_text(json.dumps(sorted(files)), encoding="utf-8")


def _scan_repo(repo_root: Path) -> list[tuple[str, str, bytes, dict[str, Any] | None]]:
    """Single scan pass: returns list of (rel_path, language, source, parsed_info)."""
    import os

    # Try Roslyn for C# if .NET SDK is available
    from ..analyzers import roslyn_available, run_roslyn_analyzer, roslyn_to_mnemo_format
    roslyn_data: dict[str, dict] = {}
    if roslyn_available(repo_root):
        print("  Running Roslyn analyzer for C#...", flush=True)
        results = run_roslyn_analyzer(repo_root)
        if results:
            roslyn_data = roslyn_to_mnemo_format(results, repo_root)
            print(f"  Roslyn analyzed {len(roslyn_data)} C# files", flush=True)

    # Build extension lookup
    ext_to_lang = {ext: lang for ext, lang in SUPPORTED_EXTENSIONS.items()}

    file_count = 0
    scanned: list[tuple[str, str, bytes, dict[str, Any] | None]] = []

    # Single os.walk pass instead of 20+ rglob calls
    from ..config import IGNORE_DIRS
    for dirpath, dirnames, filenames in os.walk(repo_root):
        # Prune ignored directories in-place
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]

        for filename in filenames:
            # Check extension
            ext = None
            for e in ext_to_lang:
                if filename.endswith(e):
                    ext = e
                    break
            if ext is None:
                continue

            filepath = Path(dirpath) / filename
            if filepath.stat().st_size > MAX_FILE_SIZE:
                continue

            try:
                source = filepath.read_bytes()
            except (OSError, PermissionError):
                continue

            file_count += 1
            if file_count % 100 == 0:
                print(f"  Scanned {file_count} files...", flush=True)

            rel = str(filepath.relative_to(repo_root))
            language = ext_to_lang[ext]
            info = roslyn_data.get(rel) or _extract_file(source, language)
            scanned.append((rel, language, source, info))

    print(f"  Scanned {file_count} files total", flush=True)
    return scanned


def generate_summary(repo_root: Path, index: bool = True, scanned: list | None = None) -> str:
    """Generate a compact markdown summary of the repo structure."""
    if scanned is None:
        scanned = _scan_repo(repo_root)

    tree: dict[str, dict[str, list[str]]] = {}
    hashes: dict[str, str] = {}
    all_chunks = []

    # MNO-030: Load previous hashes for incremental indexing
    old_hashes = _load_hashes(repo_root) if index else {}

    for rel, language, source, info in scanned:
        hashes[rel] = hashlib.md5(source, usedforsecurity=False).hexdigest()

        parts = rel.split("/")
        module = parts[0] if len(parts) > 1 else "."
        submodule = parts[1] if len(parts) > 2 else "_root"
        if module not in tree:
            tree[module] = {}
        if submodule not in tree[module]:
            tree[module][submodule] = []

        rel_short = "/".join(parts[1:]) or rel
        if info:
            # MNO-030: Only index chunks for files with changed hashes
            if not index or hashes.get(rel) != old_hashes.get(rel):
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

    # MNO-030: Delete chunks for removed files and update manifest
    if index:
        from ..retrieval import delete_chunks
        removed = set(old_hashes.keys()) - set(hashes.keys())
        for removed_file in removed:
            delete_chunks(repo_root, "code", removed_file)
        _save_index_manifest(repo_root, set(hashes.keys()))

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
        print(f"  Indexing {len(all_chunks)} chunks...", flush=True)
        index_chunks(repo_root, "code", all_chunks)
    return "\n".join(lines)


def generate_compact_tree(repo_root: Path, scanned: list | None = None) -> str:
    """Generate a compact tree showing structure + key classes per module (for recall)."""
    if scanned is None:
        scanned = _scan_repo(repo_root)

    modules: dict[str, dict] = {}

    for rel, language, source, info in scanned:
        parts = rel.split("/")
        module = parts[0] if len(parts) > 1 else "."
        submodule = parts[1] if len(parts) > 2 else "_root"

        if module not in modules:
            modules[module] = {"subs": {}, "classes": [], "funcs": 0}
        if submodule not in modules[module]["subs"]:
            modules[module]["subs"][submodule] = 0
        modules[module]["subs"][submodule] += 1

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


def save_summary(repo_root: Path, index: bool = True, scanned: list | None = None) -> Path:
    """Generate and save the markdown summary."""
    if scanned is None:
        scanned = _scan_repo(repo_root)
    summary = generate_summary(repo_root, index=index, scanned=scanned)
    out = mnemo_path(repo_root) / "summary.md"
    out.write_text(summary, encoding="utf-8")
    # Also generate compact tree for recall/context files — reuses same scan
    compact = generate_compact_tree(repo_root, scanned=scanned)
    compact_out = mnemo_path(repo_root) / "tree.md"
    compact_out.write_text(compact, encoding="utf-8")
    return out


def save_repo_map(repo_root: Path, index: bool = True) -> Path:
    """Generate summary, compact tree, and knowledge graph."""
    # Single scan pass — shared across summary, tree, and graph
    scanned = _scan_repo(repo_root)
    result = save_summary(repo_root, index=index, scanned=scanned)
    # Build knowledge graph — pass scanned data to avoid re-scanning
    print("⏳ Building knowledge graph...", flush=True)
    try:
        from ..graph.builder import build_graph
        build_graph(repo_root, scanned=scanned)
    except Exception as exc:
        logger.warning(f"Graph build failed (non-fatal): {exc}")
    return result
