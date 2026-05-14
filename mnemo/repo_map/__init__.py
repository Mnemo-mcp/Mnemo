"""Repo map package — re-exports all public and private symbols for backward compatibility."""

from __future__ import annotations

from ..config import SUPPORTED_EXTENSIONS  # noqa: F401

from .scanner import (  # noqa: F401
    CHANGELOG_FILE,
    HASH_INDEX_FILE,
    MAX_FILE_SIZE,
    _file_hash,
    _load_hashes,
    _save_hashes,
    _should_ignore,
    has_changes,
)

from .parsers import (  # noqa: F401
    _extract_c_cpp,
    _extract_csharp,
    _extract_file,
    _extract_go,
    _extract_java,
    _extract_js,
    _extract_kotlin,
    _extract_php,
    _extract_python,
    _extract_ruby,
    _extract_rust,
    _extract_scala,
    _extract_swift,
    _get_node_text,
    _get_parser,
    _resolve_language,
)

from .generator import (  # noqa: F401
    generate_compact_tree,
    generate_summary,
    save_repo_map,
    save_summary,
)
