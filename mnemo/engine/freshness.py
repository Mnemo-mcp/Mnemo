"""Incremental graph freshness — updates graph for changed files without full rebuild."""

from __future__ import annotations

import time
from pathlib import Path

_last_check: dict[str, float] = {}  # repo_path → last check timestamp
_STALE_THRESHOLD = 30  # seconds between freshness checks


def ensure_graph_fresh(repo_root: Path) -> None:
    """Check if source files changed since last index, incrementally update graph if so."""
    from .db import get_db_path

    # Skip if no graph exists (not yet initialized)
    if not get_db_path(repo_root).exists():
        return

    # Throttle: don't check more than once per 30s
    key = str(repo_root)
    now = time.time()
    if now - _last_check.get(key, 0) < _STALE_THRESHOLD:
        return
    _last_check[key] = now

    # Load meta to get last indexed hashes
    from .pipeline import _load_meta, phase_scan, _diff_files
    meta = _load_meta(repo_root)
    if not meta:
        return

    # Quick scan for changed files
    files = phase_scan(repo_root)
    old_hashes = meta.get("file_hashes", {})
    changed, removed = _diff_files(files, old_hashes)

    if not changed and not removed:
        return

    # Incremental update — only re-process changed/removed files
    _incremental_update(repo_root, files, changed, removed, old_hashes)


def _incremental_update(repo_root: Path, all_files, changed: list[str], removed: list[str], old_hashes: dict) -> None:
    """Delete old nodes for changed/removed files, re-parse and insert new ones."""
    from .db import open_db
    from .pipeline import _save_meta, _build_chunks
    from .workers import parse_files

    _, conn = open_db(repo_root)

    # Delete nodes for changed + removed files
    for file_path in changed + removed:
        _delete_file_nodes(conn, file_path)

    # Re-parse changed files
    changed_files = [f for f in all_files if f.path in changed]
    parsed_results = []
    if changed_files:
        from .cache import load_cache, save_cache, get_cached
        cache = load_cache(repo_root)

        to_parse = []
        for f in changed_files:
            cached = get_cached(cache, f.hash)
            if cached:
                _insert_file_nodes(conn, f, cached)
                parsed_results.append((f, cached))
            else:
                to_parse.append(f)

        if to_parse:
            parsed = parse_files(repo_root, to_parse)
            for fi, pr in zip(to_parse, parsed):
                cache[fi.hash] = pr
                _insert_file_nodes(conn, fi, pr)
                parsed_results.append((fi, pr))
            save_cache(repo_root, cache)

    # Update vector index: remove old chunks for changed/removed, add new
    if changed or removed:
        from ..retrieval import _index_path
        import json
        import numpy as np
        vec_path, meta_path = _index_path(repo_root, "code")
        if vec_path.exists() and meta_path.exists():
            vectors = np.load(vec_path)
            meta = json.loads(meta_path.read_text())
            affected = set(changed + removed)
            keep = [i for i, m in enumerate(meta) if m.get("metadata", {}).get("path") not in affected]
            if len(keep) < len(meta):
                vectors = vectors[keep] if keep else np.zeros((0, 384), dtype=np.float32)
                meta = [meta[i] for i in keep]
                np.save(vec_path, vectors)
                meta_path.write_text(json.dumps(meta))

        # Index new chunks for changed files
        if parsed_results:
            chunks = _build_chunks([f for f, _ in parsed_results], [r for _, r in parsed_results])
            if chunks:
                from ..retrieval import index_chunks
                index_chunks(repo_root, "code", chunks)

    # Update meta with new hashes
    _save_meta(repo_root, all_files)


def _delete_file_nodes(conn, file_path: str) -> None:
    """Remove all nodes and edges associated with a file."""
    fp = file_path.replace("'", "\\'")
    # Delete methods belonging to classes in this file
    try:
        conn.execute(f"MATCH (c:Class {{file: '{fp}'}})-[e:HAS_METHOD]->(m:Method) DELETE e")
        conn.execute(f"MATCH (m:Method {{file: '{fp}'}}) DELETE m")
    except RuntimeError:
        pass
    # Delete classes
    try:
        conn.execute(f"MATCH (c:Class {{file: '{fp}'}})-[e]->() DELETE e")
        conn.execute(f"MATCH ()-[e]->(c:Class {{file: '{fp}'}}) DELETE e")
        conn.execute(f"MATCH (c:Class {{file: '{fp}'}}) DELETE c")
    except RuntimeError:
        pass
    # Delete functions
    try:
        conn.execute(f"MATCH (f:Function {{file: '{fp}'}})-[e]->() DELETE e")
        conn.execute(f"MATCH ()-[e]->(f:Function {{file: '{fp}'}}) DELETE e")
        conn.execute(f"MATCH (f:Function {{file: '{fp}'}}) DELETE f")
    except RuntimeError:
        pass
    # Delete file node
    try:
        conn.execute(f"MATCH (f:File {{id: '{fp}'}})-[e]->() DELETE e")
        conn.execute(f"MATCH ()-[e]->(f:File {{id: '{fp}'}}) DELETE e")
        conn.execute(f"MATCH (f:File {{id: '{fp}'}}) DELETE f")
    except RuntimeError:
        pass


def _insert_file_nodes(conn, fi, parse_result) -> None:
    """Insert nodes for a single parsed file into the graph."""
    fp = fi.path.replace("'", "\\'")

    # File node
    try:
        conn.execute(f"CREATE (:File {{id: '{fp}', language: '{fi.language}', hash: '{fi.hash}', size: {fi.size}}})")
    except RuntimeError:
        pass

    # Classes
    for cls in parse_result.classes:
        name = cls.get("name", "").replace("'", "\\'")
        impl = (cls.get("implements") or "").replace("'", "\\'")
        node_id = f"{fp}:{name}"
        try:
            conn.execute(f"CREATE (:Class {{id: '{node_id}', name: '{name}', file: '{fp}', implements: '{impl}'}})")
        except RuntimeError:
            pass
        # Methods
        for method in cls.get("methods", []):
            mname = method if isinstance(method, str) else method.get("name", "")
            msig = method if isinstance(method, str) else method.get("signature", mname)
            mname_esc = mname.replace("'", "\\'")
            msig_esc = str(msig)[:200].replace("'", "\\'")
            mid = f"{fp}:{name}.{mname_esc}"
            try:
                conn.execute(f"CREATE (:Method {{id: '{mid}', name: '{mname_esc}', file: '{fp}', signature: '{msig_esc}'}})")
                conn.execute(f"MATCH (c:Class {{id: '{node_id}'}}), (m:Method {{id: '{mid}'}}) CREATE (c)-[:HAS_METHOD]->(m)")
            except RuntimeError:
                pass

    # Functions
    for func in parse_result.functions:
        fname = func if isinstance(func, str) else func.get("name", "")
        fname_esc = fname.replace("'", "\\'")
        fid = f"{fp}:{fname_esc}"
        try:
            conn.execute(f"CREATE (:Function {{id: '{fid}', name: '{fname_esc}', file: '{fp}', signature: '{fname_esc}'}})")
        except RuntimeError:
            pass
