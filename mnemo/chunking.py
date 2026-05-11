"""Chunk schema and builders for semantic indexing."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Chunk:
    """Canonical chunk used for local semantic retrieval."""

    id: str
    chunk_type: str
    path: str
    language: str
    symbol: str
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    hash: str = ""

    def __post_init__(self):
        if not self.hash:
            object.__setattr__(self, "hash", _hash(self.content))


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


def _chunk_id(chunk_type: str, path: str, symbol: str) -> str:
    raw = f"{chunk_type}:{path}:{symbol}"
    return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:24]


def make_code_chunks(path: str, language: str, info: dict[str, Any]) -> list[Chunk]:
    """Build code chunks from parsed file info (class-level + method-level)."""
    chunks: list[Chunk] = []

    for cls in info.get("classes", []):
        name = str(cls.get("name", "UnknownClass"))
        methods = cls.get("methods", [])
        methods_text = "\n".join(f"- {method}" for method in methods)
        content = f"class {name}\n{methods_text}".strip()
        chunks.append(
            Chunk(
                id=_chunk_id("code", path, f"class:{name}"),
                chunk_type="code",
                path=path,
                language=language,
                symbol=name,
                content=content,
                hash=_hash(content),
                metadata={"kind": "class", "method_count": len(methods)},
            )
        )
        # Method-level chunks for better search granularity
        for method in methods:
            mname = method.split("(")[0].split()[-1] if method else ""
            if not mname or mname.startswith("_"):
                continue
            method_content = f"class {name}\n  {method}"
            chunks.append(
                Chunk(
                    id=_chunk_id("code", path, f"method:{name}.{mname}"),
                    chunk_type="code",
                    path=path,
                    language=language,
                    symbol=f"{name}.{mname}",
                    content=method_content,
                    hash=_hash(method_content),
                    metadata={"kind": "method", "class": name},
                )
            )

    seen_ids: set[str] = set()
    for fn in info.get("functions", []):
        text = str(fn)
        symbol = text.split("(")[0].replace("def ", "").strip()
        chunk_id = _chunk_id("code", path, f"function:{symbol}:{_hash(text)}")
        if chunk_id in seen_ids:
            continue
        seen_ids.add(chunk_id)
        chunks.append(
            Chunk(
                id=chunk_id,
                chunk_type="code",
                path=path,
                language=language,
                symbol=symbol or "function",
                content=text,
                hash=_hash(text),
                metadata={"kind": "function"},
            )
        )
    return chunks


def markdown_heading_chunks(base_dir: Path, file_path: Path) -> list[Chunk]:
    """Split a markdown file into heading-based chunks."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    rel_path = str(file_path.relative_to(base_dir))
    lines = content.splitlines()
    sections: list[tuple[str, list[str]]] = []
    current_heading = "Document"
    current_lines: list[str] = []

    for line in lines:
        if line.startswith("#"):
            if current_lines:
                sections.append((current_heading, current_lines))
            current_heading = line.lstrip("#").strip() or "Section"
            current_lines = [line]
        else:
            current_lines.append(line)
    if current_lines:
        sections.append((current_heading, current_lines))

    chunks: list[Chunk] = []
    for heading, body_lines in sections:
        text = "\n".join(body_lines).strip()
        if not text:
            continue
        chunks.append(
            Chunk(
                id=_chunk_id("knowledge", rel_path, heading),
                chunk_type="knowledge",
                path=rel_path,
                language="markdown",
                symbol=heading,
                content=text,
                hash=_hash(text),
                metadata={"kind": "heading"},
            )
        )
    return chunks


def api_endpoint_chunk(path: str, method: str, endpoint: str, summary: str, service: str = "") -> Chunk:
    """Build a chunk from an API endpoint."""
    symbol = f"{method.upper()} {endpoint}"
    content = f"{symbol}\n{summary}".strip()
    return Chunk(
        id=_chunk_id("api", path, symbol),
        chunk_type="api",
        path=path,
        language="http",
        symbol=symbol,
        content=content,
        hash=_hash(content),
        metadata={"kind": "endpoint", "service": service},
    )
