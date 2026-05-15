"""Indexing pipeline — phased DAG: scan → parse → cross-file → load into LadybugDB."""

from __future__ import annotations

import csv
import hashlib
import os
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..config import IGNORE_DIRS, SUPPORTED_EXTENSIONS

from .db import open_db, init_schema, reset_db


@dataclass
class FileInfo:
    path: str
    language: str
    size: int
    hash: str


@dataclass
class ParseResult:
    path: str
    language: str
    classes: list[dict[str, Any]] = field(default_factory=list)
    functions: list[str] = field(default_factory=list)
    imports: list[str] = field(default_factory=list)
    methods: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class PipelineStats:
    files_scanned: int = 0
    files_parsed: int = 0
    files_cached: int = 0
    nodes_created: int = 0
    edges_created: int = 0
    scan_ms: int = 0
    parse_ms: int = 0
    load_ms: int = 0
    total_ms: int = 0


def run_pipeline(repo_root: Path, force: bool = False) -> PipelineStats:
    """Run the full indexing pipeline: scan → parse → load."""
    stats = PipelineStats()
    t_start = time.time()

    # Phase 1: Scan
    t0 = time.time()
    files = phase_scan(repo_root)
    stats.files_scanned = len(files)
    stats.scan_ms = int((time.time() - t0) * 1000)
    print(f"  Phase 1 scan: {len(files)} files ({stats.scan_ms}ms)", flush=True)

    # Check if incremental is possible
    meta = _load_meta(repo_root)
    if not force and meta:
        changed, removed = _diff_files(files, meta.get("file_hashes", {}))
        if not changed and not removed:
            stats.total_ms = int((time.time() - t_start) * 1000)
            print(f"  No changes detected — skipping ({stats.total_ms}ms)", flush=True)
            return stats

    # Phase 2: Parse (with cache)
    t0 = time.time()
    from .cache import load_cache, save_cache, get_cached
    cache = load_cache(repo_root)
    results: list[ParseResult] = []

    # Separate cached vs uncached
    to_parse: list[FileInfo] = []
    for f in files:
        cached = get_cached(cache, f.hash)
        if cached and not force:
            results.append(cached)
            stats.files_cached += 1
        else:
            to_parse.append(f)

    # Parse uncached files (parallel)
    if to_parse:
        from .workers import parse_files
        parsed = parse_files(repo_root, to_parse)
        results.extend(parsed)
        # Update cache
        for fi, pr in zip(to_parse, parsed):
            cache[fi.hash] = pr
        save_cache(repo_root, cache)

    stats.files_parsed = len(to_parse)
    stats.parse_ms = int((time.time() - t0) * 1000)
    print(f"  Phase 2 parse: {stats.files_parsed} parsed, {stats.files_cached} cached ({stats.parse_ms}ms)", flush=True)

    # Phase 3: Load into LadybugDB
    t0 = time.time()
    node_count, edge_count = phase_load(repo_root, files, results)
    stats.nodes_created = node_count
    stats.edges_created = edge_count
    stats.load_ms = int((time.time() - t0) * 1000)
    print(f"  Phase 3 load: {node_count} nodes, {edge_count} edges ({stats.load_ms}ms)", flush=True)

    # Phase 4: Scope resolution — CALLS edges
    t0 = time.time()
    from .scope import resolve_calls
    from .db import open_db
    _, conn = open_db(repo_root)
    calls_count = resolve_calls(repo_root, files, results, conn)
    scope_ms = int((time.time() - t0) * 1000)
    stats.edges_created += calls_count
    print(f"  Phase 4 scope: {calls_count} CALLS edges ({scope_ms}ms)", flush=True)

    # Phase 5: Community detection
    t0 = time.time()
    from .clustering import detect_communities
    community_count = detect_communities(conn)
    cluster_ms = int((time.time() - t0) * 1000)
    stats.nodes_created += community_count
    print(f"  Phase 5 communities: {community_count} clusters ({cluster_ms}ms)", flush=True)

    # Save metadata for incremental
    _save_meta(repo_root, files)

    stats.total_ms = int((time.time() - t_start) * 1000)
    return stats


def _load_meta(repo_root: Path) -> dict | None:
    """Load pipeline metadata (file hashes, last run info)."""
    import json
    meta_path = repo_root / ".mnemo" / "engine-meta.json"
    if not meta_path.exists():
        return None
    try:
        return json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _save_meta(repo_root: Path, files: list[FileInfo]) -> None:
    """Save pipeline metadata for incremental indexing."""
    import json
    meta_path = repo_root / ".mnemo" / "engine-meta.json"
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta = {
        "file_hashes": {f.path: f.hash for f in files},
        "file_count": len(files),
        "indexed_at": time.time(),
    }
    meta_path.write_text(json.dumps(meta), encoding="utf-8")


def _diff_files(current: list[FileInfo], old_hashes: dict[str, str]) -> tuple[list[str], list[str]]:
    """Find changed and removed files."""
    current_hashes = {f.path: f.hash for f in current}
    changed = [p for p, h in current_hashes.items() if old_hashes.get(p) != h]
    removed = [p for p in old_hashes if p not in current_hashes]
    return changed, removed


def phase_scan(repo_root: Path) -> list[FileInfo]:
    """Single os.walk pass — collect all source files with hashes."""
    ext_to_lang = {ext: lang for ext, lang in SUPPORTED_EXTENSIONS.items()}
    files: list[FileInfo] = []

    for dirpath, dirnames, filenames in os.walk(repo_root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for filename in filenames:
            ext = None
            for e in ext_to_lang:
                if filename.endswith(e):
                    ext = e
                    break
            if ext is None:
                continue

            filepath = Path(dirpath) / filename
            try:
                size = filepath.stat().st_size
            except OSError:
                continue
            if size > 200_000:  # Skip files > 200KB
                continue

            try:
                content = filepath.read_bytes()
            except (OSError, PermissionError):
                continue

            rel = str(filepath.relative_to(repo_root))
            h = hashlib.sha256(content).hexdigest()[:16]
            files.append(FileInfo(path=rel, language=ext_to_lang[ext], size=size, hash=h))

    return files


def phase_load(repo_root: Path, files: list[FileInfo], results: list[ParseResult]) -> tuple[int, int]:
    """Bulk-load nodes and edges into LadybugDB via CSV."""
    reset_db(repo_root)
    db, conn = open_db(repo_root)
    init_schema(conn)

    nodes = 0
    edges = 0

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # --- File nodes ---
        file_csv = tmp_path / "files.csv"
        with open(file_csv, "w", newline="") as f:
            w = csv.writer(f)
            for fi in files:
                w.writerow([fi.path, fi.language, fi.hash, fi.size])
        conn.execute(f'COPY File FROM "{file_csv}"')
        nodes += len(files)

        # --- Folder nodes ---
        folders = set()
        for fi in files:
            parts = fi.path.split("/")
            for i in range(1, len(parts)):
                folders.add("/".join(parts[:i]))
        if folders:
            folder_csv = tmp_path / "folders.csv"
            with open(folder_csv, "w", newline="") as f:
                w = csv.writer(f)
                for folder in sorted(folders):
                    w.writerow([folder])
            conn.execute(f'COPY Folder FROM "{folder_csv}"')
            nodes += len(folders)

        # --- CONTAINS edges (Folder → File) ---
        contains_csv = tmp_path / "contains.csv"
        with open(contains_csv, "w", newline="") as f:
            w = csv.writer(f)
            for fi in files:
                parts = fi.path.split("/")
                if len(parts) > 1:
                    parent = "/".join(parts[:-1])
                    w.writerow([parent, fi.path])
        conn.execute(f'COPY CONTAINS FROM "{contains_csv}"')

        # --- Symbol nodes from parse results ---
        # Classes
        class_rows = []
        for r in results:
            for cls in r.classes:
                cid = f"{r.path}:{cls['name']}"
                impl = cls.get("implements", "")
                class_rows.append([cid, cls["name"], r.path, impl, ""])
        if class_rows:
            cls_csv = tmp_path / "classes.csv"
            with open(cls_csv, "w", newline="") as f:
                csv.writer(f).writerows(class_rows)
            conn.execute(f'COPY Class FROM "{cls_csv}"')
            nodes += len(class_rows)

        # Functions
        func_rows = []
        for r in results:
            for fn in r.functions:
                fname = fn.split("(")[0].replace("def ", "").replace("func ", "").strip()
                fid = f"{r.path}:{fname}"
                sig = fn.replace("\n", " ").replace("\r", "")[:200]
                func_rows.append([fid, fname, r.path, sig])
        if func_rows:
            fn_csv = tmp_path / "functions.csv"
            with open(fn_csv, "w", newline="") as f:
                csv.writer(f, quoting=csv.QUOTE_MINIMAL).writerows(func_rows)
            conn.execute(f'COPY Function FROM "{fn_csv}" (PARALLEL=FALSE)')
            nodes += len(func_rows)

        # Methods
        method_rows = []
        for r in results:
            for cls in r.classes:
                seen_methods: dict[str, int] = {}
                for msig in cls.get("methods", []):
                    mname = msig.split("(")[0].split()[-1] if msig else ""
                    if mname:
                        # Deduplicate overloaded methods
                        seen_methods[mname] = seen_methods.get(mname, 0) + 1
                        suffix = f"_{seen_methods[mname]}" if seen_methods[mname] > 1 else ""
                        mid = f"{r.path}:{cls['name']}.{mname}{suffix}"
                        sig = msig.replace("\n", " ").replace("\r", "")[:200]
                        method_rows.append([mid, mname, cls["name"], r.path, sig, "public"])
        if method_rows:
            m_csv = tmp_path / "methods.csv"
            with open(m_csv, "w", newline="") as f:
                w = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
                w.writerows(method_rows)
            conn.execute(f'COPY Method FROM "{m_csv}" (PARALLEL=FALSE)')
            nodes += len(method_rows)

        # --- Edges: FILE_DEFINES_CLASS, FILE_DEFINES_FUNCTION ---
        if class_rows:
            def_cls_csv = tmp_path / "def_class.csv"
            with open(def_cls_csv, "w", newline="") as f:
                w = csv.writer(f)
                for row in class_rows:
                    w.writerow([row[2], row[0]])  # file_path, class_id
            conn.execute(f'COPY FILE_DEFINES_CLASS FROM "{def_cls_csv}"')
            edges += len(class_rows)

        if func_rows:
            def_fn_csv = tmp_path / "def_func.csv"
            with open(def_fn_csv, "w", newline="") as f:
                w = csv.writer(f)
                for row in func_rows:
                    w.writerow([row[2], row[0]])  # file_path, func_id
            conn.execute(f'COPY FILE_DEFINES_FUNCTION FROM "{def_fn_csv}"')
            edges += len(func_rows)

        if method_rows:
            has_method_csv = tmp_path / "has_method.csv"
            with open(has_method_csv, "w", newline="") as f:
                w = csv.writer(f)
                for row in method_rows:
                    cls_id = f"{row[3]}:{row[2]}"  # file:class_name
                    w.writerow([cls_id, row[0]])
            conn.execute(f'COPY HAS_METHOD FROM "{has_method_csv}"')
            edges += len(method_rows)

        # --- IMPORTS edges ---
        # Map file paths for import resolution
        file_set = {fi.path for fi in files}
        import_rows = []
        for r in results:
            for imp in r.imports:
                # Try to resolve import to a file path
                target = _resolve_import(imp, r.path, file_set)
                if target and target != r.path:
                    import_rows.append([r.path, target])
        if import_rows:
            imp_csv = tmp_path / "imports.csv"
            with open(imp_csv, "w", newline="") as f:
                csv.writer(f).writerows(import_rows)
            try:
                conn.execute(f'COPY IMPORTS FROM "{imp_csv}"')
                edges += len(import_rows)
            except RuntimeError:
                pass  # Duplicate or missing node — skip

    return nodes, edges


def _resolve_import(import_stmt: str, source_file: str, file_set: set[str]) -> str | None:
    """Best-effort import → file path resolution."""
    # Python: "from foo.bar import baz" → foo/bar.py or foo/bar/__init__.py
    # JS/TS: "import x from './utils'" → utils.ts, utils.js, utils/index.ts
    # C#: "using Namespace.Class" → heuristic match

    # Extract module path from import statement
    parts = import_stmt.replace("from ", "").replace("import ", "").split()
    if not parts:
        return None
    module = parts[0].strip("'\"").rstrip(";")

    # Try direct path resolution
    candidates = []
    if "/" in module or "." in module:
        # Relative path style
        base = module.replace(".", "/")
        candidates = [
            f"{base}.py", f"{base}.ts", f"{base}.js", f"{base}.cs",
            f"{base}/index.ts", f"{base}/index.js", f"{base}/__init__.py",
        ]
    else:
        # Simple name — look in same directory
        src_dir = "/".join(source_file.split("/")[:-1])
        if src_dir:
            candidates = [
                f"{src_dir}/{module}.py", f"{src_dir}/{module}.ts",
                f"{src_dir}/{module}.js", f"{src_dir}/{module}.cs",
            ]

    for c in candidates:
        if c in file_set:
            return c
    return None
