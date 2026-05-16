"""Parallel tree-sitter parsing via ProcessPoolExecutor."""

from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from .pipeline import FileInfo, ParseResult


def parse_files(repo_root: Path, files: list[FileInfo]) -> list[ParseResult]:
    """Parse files in parallel using ProcessPoolExecutor."""
    if not files:
        return []

    # For small batches, parse sequentially (process spawn overhead > savings)
    if len(files) <= 20:
        return [_parse_single(repo_root, f) for f in files]

    # Batch into chunks of ~20 files per worker
    workers = min(os.cpu_count() or 4, 8)
    chunk_size = max(1, len(files) // workers)
    chunks = [files[i:i + chunk_size] for i in range(0, len(files), chunk_size)]

    results: list[ParseResult] = []
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_parse_batch, repo_root, chunk): i for i, chunk in enumerate(chunks)}
        ordered: dict[int, list[ParseResult]] = {}
        for future in as_completed(futures):
            idx = futures[future]
            try:
                ordered[idx] = future.result()
            except Exception:
                # If a worker fails, parse sequentially as fallback
                ordered[idx] = [_parse_single(repo_root, f) for f in chunks[idx]]

    # Reassemble in order
    for i in range(len(chunks)):
        results.extend(ordered.get(i, []))

    return results


def _parse_batch(repo_root: Path, files: list[FileInfo]) -> list[ParseResult]:
    """Parse a batch of files in a worker process."""
    return [_parse_single(repo_root, f) for f in files]


def _parse_single(repo_root: Path, fi: FileInfo) -> ParseResult:
    """Parse a single file using tree-sitter."""
    filepath = Path(repo_root) / fi.path
    try:
        source = filepath.read_bytes()
    except (OSError, PermissionError):
        return ParseResult(path=fi.path, language=fi.language)

    # Use the existing tree-sitter parsers
    from ..repo_map.parsers import _extract_file
    info = _extract_file(source, fi.language)

    if not info:
        return ParseResult(path=fi.path, language=fi.language)

    return ParseResult(
        path=fi.path,
        language=fi.language,
        classes=info.get("classes", []),
        functions=info.get("functions", []),
        imports=info.get("imports", []),
    )
