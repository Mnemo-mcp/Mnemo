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
    java_enrichment: dict | None = None,
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

    # Build suffix index for Java imports (com/foo/Bar.java → full path)
    java_suffix_index: dict[str, str] = {}
    for fp in file_set:
        if fp.endswith(".java"):
            # Index by the package-relative suffix (e.g., com/availity/aries/Foo.java)
            # For Java monorepos, strip common prefixes like src/main/java/
            for prefix in ("src/main/java/", "src/test/java/", "src/"):
                idx = fp.find(prefix)
                if idx != -1:
                    suffix = fp[idx + len(prefix):]
                    java_suffix_index[suffix] = fp
                    break
            else:
                # Use filename as-is for last-resort match
                java_suffix_index[fp] = fp

    for r in results:
        for imp in r.imports:
            target = _resolve_import_to_file(imp, r.path, file_set, java_suffix_index)
            if target and target != r.path:
                file_imports[r.path].add(target)

    # Step 3: For each file, resolve calls via imports (fast, import-driven)
    calls: list[tuple[str, str, float, str]] = []  # (from_id, to_id, confidence, reason)

    # For large repos (>2000 files), use import-only resolution (skip brute-force scan)
    large_repo = len(files) > 2000

    for r in results:
        local_symbols = file_symbols[r.path]
        imported_files = file_imports[r.path]

        if not imported_files:
            continue

        from_id = f"{r.path}:{_get_primary_symbol(r)}"

        # Collect imported symbols (symbols defined in files we import)
        for imp_file in imported_files:
            for sym in file_symbols.get(imp_file, set()):
                if sym in local_symbols or len(sym) < 3:
                    continue
                to_id = f"{imp_file}:{sym}"
                calls.append((from_id, to_id, 0.9, "import-resolved"))

        # For small repos, also do global scan (affordable)
        if not large_repo:
            filepath = repo_root / r.path
            try:
                source = filepath.read_text(errors="replace")
            except (OSError, PermissionError):
                continue

            for symbol_name, defining_file in symbol_to_file.items():
                if defining_file == r.path or defining_file in imported_files:
                    continue
                if len(symbol_name) < 3 or symbol_name in local_symbols:
                    continue
                if symbol_name not in source:
                    continue
                to_id = f"{defining_file}:{symbol_name}"
                calls.append((from_id, to_id, 0.5, "global"))

    # Step 3b: Java enrichment — convert method invocations to CALLS edges
    if java_enrichment:
        for file_path, enrichment in java_enrichment.items():
            for inv in enrichment.invocations:
                # Resolve target_type to a file using symbol_to_file
                target_file = symbol_to_file.get(inv.target_type)
                if not target_file or target_file == file_path:
                    continue
                from_id = f"{file_path}:{inv.caller_class}"
                to_id = f"{target_file}:{inv.target_type}"
                calls.append((from_id, to_id, 0.85, "java-invocation"))

    # Step 4: Load CALLS edges via CSV
    if not calls:
        return 0

    # Deduplicate (keep highest confidence per pair)
    best: dict[tuple[str, str], tuple[float, str]] = {}
    for from_id, to_id, conf, reason in calls:
        key = (from_id, to_id)
        if key not in best or conf > best[key][0]:
            best[key] = (conf, reason)

    # Collect node IDs by type
    result = conn.execute("MATCH (f:Function) RETURN f.id")
    func_ids = set()
    while result.has_next():
        func_ids.add(result.get_next()[0])
    result = conn.execute("MATCH (c:Class) RETURN c.id")
    class_ids = set()
    while result.has_next():
        class_ids.add(result.get_next()[0])

    # Split into Function→Function and Class→Class edges
    fn_calls = []
    class_deps = []
    for (from_id, to_id), (conf, reason) in best.items():
        if from_id in func_ids and to_id in func_ids:
            fn_calls.append([from_id, to_id, conf, reason])
        elif from_id in class_ids and to_id in class_ids:
            class_deps.append([from_id, to_id, conf, reason])

    total = 0
    with tempfile.TemporaryDirectory() as tmp:
        if fn_calls:
            calls_csv = Path(tmp) / "calls.csv"
            with open(calls_csv, "w", newline="") as f:
                csv.writer(f).writerows(fn_calls)
            try:
                conn.execute(f'COPY CALLS FROM "{calls_csv}"')
                total += len(fn_calls)
            except RuntimeError:
                pass

        if class_deps:
            deps_csv = Path(tmp) / "class_deps.csv"
            with open(deps_csv, "w", newline="") as f:
                csv.writer(f).writerows(class_deps)
            try:
                conn.execute(f'COPY CLASS_DEPENDS FROM "{deps_csv}"')
                total += len(class_deps)
            except RuntimeError:
                pass

    return total


def _get_primary_symbol(r: ParseResult) -> str:
    """Get the primary symbol name for a file (first class or first function)."""
    if r.classes:
        return r.classes[0]["name"]
    if r.functions:
        return r.functions[0].split("(")[0].replace("def ", "").replace("func ", "").strip()
    return os.path.basename(r.path).split(".")[0]


def _resolve_import_to_file(import_stmt: str, source_file: str, file_set: set[str], java_suffix_index: dict[str, str] | None = None) -> str | None:
    """Resolve an import statement to a file path."""
    parts = import_stmt.replace("from ", "").replace("import ", "").replace("using ", "").split()
    if not parts:
        return None
    module = parts[0].strip("'\"").rstrip(";").strip()

    # Skip wildcard imports (e.g., java.util.*)
    if module.endswith("*"):
        return None

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
            f"{base}.java",
        ]
        if src_dir:
            candidates += [
                f"{src_dir}/{base}.py", f"{src_dir}/{base}.ts",
                f"{src_dir}/{base}.js", f"{src_dir}/{base}.cs",
            ]

    for c in candidates:
        if c in file_set:
            return c

    # Java: use suffix index for O(1) lookup
    if java_suffix_index and source_file.endswith(".java"):
        java_suffix = base + ".java"
        if java_suffix in java_suffix_index:
            return java_suffix_index[java_suffix]

    return None
