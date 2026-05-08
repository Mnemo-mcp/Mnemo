"""Lightweight repo map — stores a hash index and pre-built markdown summary."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from .config import IGNORE_DIRS, SUPPORTED_EXTENSIONS, mnemo_path, REPO_MAP_FILE

CHANGELOG_FILE = "changelog.json"
HASH_INDEX_FILE = "hashes.json"
MAX_FILE_SIZE = 100_000


def _should_ignore(path: Path) -> bool:
    return any(part in IGNORE_DIRS for part in path.parts)


def _file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _get_parser(language: str):
    import tree_sitter_python
    import tree_sitter_javascript
    import tree_sitter_typescript
    import tree_sitter_go
    import tree_sitter_c_sharp
    from tree_sitter import Language, Parser

    lang_map = {
        "python": tree_sitter_python.language(),
        "javascript": tree_sitter_javascript.language(),
        "typescript": tree_sitter_typescript.language_typescript(),
        "go": tree_sitter_go.language(),
        "csharp": tree_sitter_c_sharp.language(),
    }
    lang = lang_map.get(language)
    if not lang:
        return None
    return Parser(Language(lang))


def _get_node_text(node) -> str:
    return node.text.decode() if node else ""


# --- Extractors (return compact dict per file) ---

def _extract_csharp(source: bytes, parser) -> dict:
    tree = parser.parse(source)
    result: dict = {"imports": [], "classes": []}

    def extract_class(node) -> dict:
        name = _get_node_text(node.child_by_field_name("name"))
        base = ""
        methods = []
        for child in node.children:
            if child.type == "base_list":
                base = child.text.decode().lstrip(": ").strip()
            if child.type == "declaration_list":
                for member in child.children:
                    if member.type in ("method_declaration", "constructor_declaration"):
                        mname = _get_node_text(member.child_by_field_name("name"))
                        if not mname:
                            continue
                        params = ""
                        ret = ""
                        for part in member.children:
                            if part.type == "parameter_list":
                                params = part.text.decode()
                            elif part.type in ("predefined_type", "identifier", "generic_name",
                                              "nullable_type", "array_type", "void_keyword", "qualified_name"):
                                name_node = member.child_by_field_name("name")
                                if name_node and part.end_byte < name_node.start_byte:
                                    ret = part.text.decode()
                        sig = f"{ret + ' ' if ret else ''}{mname}{params}".strip()
                        methods.append(sig)
        entry = {"name": name}
        if base:
            entry["implements"] = base
        if methods:
            entry["methods"] = methods
        return entry

    def walk(node):
        for child in node.children:
            if child.type == "using_directive":
                result["imports"].append(child.text.decode().strip())
            elif child.type in ("class_declaration", "interface_declaration",
                                "struct_declaration", "record_declaration"):
                result["classes"].append(extract_class(child))
            elif child.type in ("file_scoped_namespace_declaration",
                                "namespace_declaration", "declaration_list"):
                walk(child)

    walk(tree.root_node)
    return {k: v for k, v in result.items() if v}


def _extract_python(source: bytes, parser) -> dict:
    tree = parser.parse(source)
    root = tree.root_node
    result: dict = {"imports": [], "classes": [], "functions": []}

    for node in root.children:
        if node.type in ("import_statement", "import_from_statement"):
            result["imports"].append(node.text.decode().strip())

        actual = node
        decs = []
        if node.type == "decorated_definition":
            for child in node.children:
                if child.type == "decorator":
                    decs.append(child.text.decode().strip())
                elif child.type in ("function_definition", "class_definition"):
                    actual = child

        if actual.type == "function_definition":
            name = _get_node_text(actual.child_by_field_name("name"))
            params = _get_node_text(actual.child_by_field_name("parameters"))
            ret = _get_node_text(actual.child_by_field_name("return_type"))
            sig = f"def {name}{params}"
            if ret:
                sig += f" -> {ret}"
            if decs:
                sig = f"{decs[0]} {sig}"
            result["functions"].append(sig)

        elif actual.type == "class_definition":
            cname = _get_node_text(actual.child_by_field_name("name"))
            methods = []
            body = actual.child_by_field_name("body")
            if body:
                for child in body.children:
                    fn = child
                    if child.type == "decorated_definition":
                        for sub in child.children:
                            if sub.type == "function_definition":
                                fn = sub
                    if fn.type == "function_definition":
                        mname = _get_node_text(fn.child_by_field_name("name"))
                        mparams = _get_node_text(fn.child_by_field_name("parameters"))
                        methods.append(f"{mname}{mparams}")
            entry = {"name": cname}
            if methods:
                entry["methods"] = methods
            result["classes"].append(entry)

    return {k: v for k, v in result.items() if v}


def _extract_js(source: bytes, parser) -> dict:
    tree = parser.parse(source)
    result: dict = {"functions": []}
    for node in tree.root_node.children:
        if node.type == "function_declaration":
            name = _get_node_text(node.child_by_field_name("name"))
            if name:
                result["functions"].append(name)
    return {k: v for k, v in result.items() if v}


def _extract_file(source: bytes, language: str) -> dict | None:
    parser = _get_parser(language)
    if not parser:
        return None
    try:
        if language == "csharp":
            return _extract_csharp(source, parser)
        elif language == "python":
            return _extract_python(source, parser)
        elif language in ("javascript", "typescript"):
            return _extract_js(source, parser)
        return None
    except Exception:
        return None


# --- Hash index for change detection ---

def _load_hashes(repo_root: Path) -> dict[str, str]:
    path = mnemo_path(repo_root) / HASH_INDEX_FILE
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _save_hashes(repo_root: Path, hashes: dict[str, str]):
    path = mnemo_path(repo_root) / HASH_INDEX_FILE
    path.write_text(json.dumps(hashes))


def has_changes(repo_root: Path) -> bool:
    """Quick check if any files changed since last map generation."""
    old_hashes = _load_hashes(repo_root)
    if not old_hashes:
        return True

    for ext, language in SUPPORTED_EXTENSIONS.items():
        for filepath in repo_root.rglob(f"*{ext}"):
            if _should_ignore(filepath) or filepath.stat().st_size > MAX_FILE_SIZE:
                continue
            rel = str(filepath.relative_to(repo_root))
            try:
                h = _file_hash(filepath)
            except (OSError, PermissionError):
                continue
            if old_hashes.get(rel) != h:
                return True

    # Check for deletions
    for rel in old_hashes:
        if not (repo_root / rel).exists():
            return True

    return False


# --- Summary generation ---

def generate_summary(repo_root: Path) -> str:
    """Generate a compact markdown summary of the repo structure."""
    tree: dict[str, list[str]] = {}
    hashes: dict[str, str] = {}

    for ext, language in SUPPORTED_EXTENSIONS.items():
        for filepath in repo_root.rglob(f"*{ext}"):
            if _should_ignore(filepath) or filepath.stat().st_size > MAX_FILE_SIZE:
                continue
            try:
                source = filepath.read_bytes()
            except (OSError, PermissionError):
                continue

            rel = str(filepath.relative_to(repo_root))
            hashes[rel] = hashlib.md5(source).hexdigest()

            parts = rel.split("/")
            top = parts[0] if len(parts) > 1 else "."
            if top not in tree:
                tree[top] = []

            info = _extract_file(source, language)
            rel_short = "/".join(parts[1:]) or rel

            if info and info.get("classes"):
                class_names = []
                for cls in info["classes"]:
                    name = cls["name"]
                    impl = f" : {cls['implements']}" if cls.get("implements") else ""
                    class_names.append(f"`{name}{impl}`")
                tree[top].append(f"  {rel_short} → {', '.join(class_names)}")
            elif info and info.get("functions"):
                tree[top].append(f"  {rel_short} ({len(info['functions'])} functions)")
            else:
                tree[top].append(f"  {rel_short}")

    # Save hashes
    _save_hashes(repo_root, hashes)

    # Build markdown
    lines = []
    for service in sorted(tree.keys()):
        lines.append(f"**{service}/**")
        for entry in sorted(tree[service]):
            lines.append(entry)
    return "\n".join(lines)


def save_summary(repo_root: Path) -> Path:
    """Generate and save the markdown summary."""
    summary = generate_summary(repo_root)
    out = mnemo_path(repo_root) / "summary.md"
    out.write_text(summary)
    return out


# Also keep save_repo_map for backward compat with init
def save_repo_map(repo_root: Path) -> Path:
    """Generate summary (replaces old JSON map)."""
    return save_summary(repo_root)
