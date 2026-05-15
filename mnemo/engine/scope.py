"""Scope resolution — resolve CALLS edges with confidence scores.

Strategy:
1. Build import graph from parsed imports
2. Build symbol registry (which file defines which symbols)
3. For each file, scan source for symbol references
4. Resolve each reference: local scope → imported → global
5. Assign confidence: same-file=0.95, import-resolved=0.9, global=0.5
"""

from __future__ import annotations

import csv
import os
import re
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

from .pipeline import FileInfo, ParseResult


def resolve_calls(
    repo_root: Path,
    files: list[FileInfo],
    results: list[ParseResult],
    conn: Any,
) -> int:
    """Resolve CALLS edges and load them into LadybugDB. Returns edge count."""
    # Step 1: Build symbol registry — which file defines which symbols
    symbol_to_file: dict[str, str] = {}  # symbol_name → file_path
    file_symbols: dict[str, set[str]] = defaultdict(set)  # file → set of defined symbols

    for r in results:
        for cls in r.classes:
            name = cls["name"]
            symbol_to_file[name] = r.path
            file_symbols[r.path].add(name)
            for method in cls.get("methods", []):
                mname = method.split("(")[0].split()[-1] if method else ""
                if mname:
                    file_symbols[r.path].add(mname)

        for fn in r.functions:
            fname = fn.split("(")[0].replace("def ", "").replace("func ", "").strip()
            if fname:
                symbol_to_file[fname] = r.path
                file_symbols[r.path].add(fname)

    # Step 2: Build import graph — which file imports which
    file_imports: dict[str, set[str]] = defaultdict(set)  # file → set of imported file paths
    file_set = {fi.path for fi in files}

    for r in results:
        for imp in r.imports:
            target = _resolve_import_to_file(imp, r.path, file_set)
            if target and target != r.path:
                file_imports[r.path].add(target)

    # Step 3: For each file, find references to external symbols
    calls: list[tuple[str, str, float, str]] = []  # (from_id, to_id, confidence, reason)

    for r in results:
        filepath = repo_root / r.path
        try:
            source = filepath.read_text(errors="replace")
        except (OSError, PermissionError):
            continue

        local_symbols = file_symbols[r.path]
        imported_files = file_imports[r.path]

        # Collect imported symbols (symbols defined in files we import)
        imported_symbols: dict[str, str] = {}  # symbol_name → source_file
        for imp_file in imported_files:
            for sym in file_symbols.get(imp_file, set()):
                imported_symbols[sym] = imp_file

        # Scan source for symbol references
        # Look for class instantiation, function calls, type references
        for symbol_name, defining_file in symbol_to_file.items():
            if defining_file == r.path:
                continue  # Skip self-references
            if len(symbol_name) < 3:
                continue  # Skip very short names (too many false positives)
            if symbol_name in local_symbols:
                continue  # Skip if we define the same name locally

            # Check if this symbol appears in the source
            if symbol_name not in source:
                continue

            # Determine confidence based on resolution path
            from_id = f"{r.path}:{_get_primary_symbol(r)}"
            to_id = f"{defining_file}:{symbol_name}"

            if defining_file in imported_files:
                # Import-resolved: high confidence
                calls.append((from_id, to_id, 0.9, "import-resolved"))
            else:
                # Global resolution: lower confidence
                calls.append((from_id, to_id, 0.5, "global"))

    # Step 4: Load CALLS edges via CSV
    if not calls:
        return 0

    # Deduplicate (keep highest confidence per pair)
    best: dict[tuple[str, str], tuple[float, str]] = {}
    for from_id, to_id, conf, reason in calls:
        key = (from_id, to_id)
        if key not in best or conf > best[key][0]:
            best[key] = (conf, reason)

    # We need to map to Function node IDs that exist in the DB
    # Query existing function IDs
    result = conn.execute("MATCH (f:Function) RETURN f.id")
    func_ids = set()
    while result.has_next():
        func_ids.add(result.get_next()[0])

    # Filter to only edges where both endpoints exist
    valid_calls = []
    for (from_id, to_id), (conf, reason) in best.items():
        if from_id in func_ids and to_id in func_ids:
            valid_calls.append([from_id, to_id, conf, reason])

    if not valid_calls:
        return 0

    with tempfile.TemporaryDirectory() as tmp:
        calls_csv = Path(tmp) / "calls.csv"
        with open(calls_csv, "w", newline="") as f:
            csv.writer(f).writerows(valid_calls)
        try:
            conn.execute(f'COPY CALLS FROM "{calls_csv}"')
        except RuntimeError:
            # Fallback: insert one by one, skip failures
            for row in valid_calls:
                try:
                    conn.execute(
                        f"MATCH (a:Function {{id: '{row[0]}'}}), (b:Function {{id: '{row[1]}'}}) "
                        f"CREATE (a)-[:CALLS {{confidence: {row[2]}, reason: '{row[3]}'}}]->(b)"
                    )
                except RuntimeError:
                    pass

    return len(valid_calls)


def _get_primary_symbol(r: ParseResult) -> str:
    """Get the primary symbol name for a file (first class or first function)."""
    if r.classes:
        return r.classes[0]["name"]
    if r.functions:
        return r.functions[0].split("(")[0].replace("def ", "").replace("func ", "").strip()
    return os.path.basename(r.path).split(".")[0]


def _resolve_import_to_file(import_stmt: str, source_file: str, file_set: set[str]) -> str | None:
    """Resolve an import statement to a file path."""
    parts = import_stmt.replace("from ", "").replace("import ", "").replace("using ", "").split()
    if not parts:
        return None
    module = parts[0].strip("'\"").rstrip(";").strip()

    # Try path-based resolution
    base = module.replace(".", "/")
    src_dir = "/".join(source_file.split("/")[:-1])

    candidates = []
    if base.startswith("./") or base.startswith("../"):
        # Relative import
        if src_dir:
            resolved = os.path.normpath(f"{src_dir}/{base}")
            candidates = [f"{resolved}.py", f"{resolved}.ts", f"{resolved}.js", f"{resolved}.cs"]
    else:
        candidates = [
            f"{base}.py", f"{base}.ts", f"{base}.js", f"{base}.cs",
            f"{base}/index.ts", f"{base}/index.js", f"{base}/__init__.py",
        ]
        if src_dir:
            candidates += [
                f"{src_dir}/{base}.py", f"{src_dir}/{base}.ts",
                f"{src_dir}/{base}.js", f"{src_dir}/{base}.cs",
            ]

    for c in candidates:
        if c in file_set:
            return c
    return None
