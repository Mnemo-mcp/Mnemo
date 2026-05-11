"""Lightweight repo map — stores a hash index and pre-built markdown summary."""

from __future__ import annotations

import hashlib
import sys
import time
from pathlib import Path
from typing import Any

from .config import IGNORE_DIRS, SUPPORTED_EXTENSIONS, mnemo_path, REPO_MAP_FILE, should_ignore
from .chunking import make_code_chunks
from .retrieval import index_chunks
from .storage import Collections, get_storage

CHANGELOG_FILE = "changelog.json"
HASH_INDEX_FILE = "hashes.json"
MAX_FILE_SIZE = 100_000


def _should_ignore(path: Path) -> bool:
    return should_ignore(path)


def _file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _get_parser(language: str):
    from tree_sitter import Language, Parser

    lang = _resolve_language(language)
    if not lang:
        return None
    return Parser(Language(lang))


def _resolve_language(language: str):
    """Resolve a language string to a tree-sitter language object."""
    try:
        if language == "python":
            import tree_sitter_python
            return tree_sitter_python.language()
        elif language == "javascript":
            import tree_sitter_javascript
            return tree_sitter_javascript.language()
        elif language == "typescript":
            import tree_sitter_typescript
            return tree_sitter_typescript.language_typescript()
        elif language == "go":
            import tree_sitter_go
            return tree_sitter_go.language()
        elif language == "csharp":
            import tree_sitter_c_sharp
            return tree_sitter_c_sharp.language()
        elif language == "java":
            import tree_sitter_java
            return tree_sitter_java.language()
        elif language == "rust":
            import tree_sitter_rust
            return tree_sitter_rust.language()
        elif language == "ruby":
            import tree_sitter_ruby
            return tree_sitter_ruby.language()
        elif language == "php":
            import tree_sitter_php
            return tree_sitter_php.language()
        elif language == "c":
            import tree_sitter_c
            return tree_sitter_c.language()
        elif language == "cpp":
            import tree_sitter_cpp
            return tree_sitter_cpp.language()
        elif language == "kotlin":
            import tree_sitter_kotlin
            return tree_sitter_kotlin.language()
        elif language == "swift":
            import tree_sitter_swift
            return tree_sitter_swift.language()
        elif language == "scala":
            import tree_sitter_scala
            return tree_sitter_scala.language()
    except ImportError:
        return None
    return None


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
    result: dict = {"functions": [], "classes": []}

    def walk(node):
        if node.type == "function_declaration":
            name = _get_node_text(node.child_by_field_name("name"))
            if name:
                result["functions"].append(name)
        elif node.type == "lexical_declaration":
            text = node.text.decode(errors="replace")
            if "=>" in text:
                result["functions"].append(text.split("=")[0].replace("const", "").replace("let", "").replace("var", "").strip())
        elif node.type == "method_definition":
            name = _get_node_text(node.child_by_field_name("name"))
            if name:
                result["functions"].append(name)
        elif node.type == "class_declaration":
            cname = _get_node_text(node.child_by_field_name("name")) or "AnonymousClass"
            methods = []
            for child in node.children:
                if child.type == "class_body":
                    for member in child.children:
                        if member.type == "method_definition":
                            mname = _get_node_text(member.child_by_field_name("name"))
                            if mname:
                                methods.append(mname)
            result["classes"].append({"name": cname, "methods": methods})
        for child in node.children:
            walk(child)

    walk(tree.root_node)
    result["functions"] = sorted(set(result["functions"]))
    return {k: v for k, v in result.items() if v}


def _extract_go(source: bytes, parser) -> dict:
    tree = parser.parse(source)
    result: dict = {"functions": [], "classes": []}
    for node in tree.root_node.children:
        if node.type == "function_declaration":
            name = _get_node_text(node.child_by_field_name("name"))
            if name:
                result["functions"].append(name)
        elif node.type == "method_declaration":
            name = _get_node_text(node.child_by_field_name("name"))
            receiver = _get_node_text(node.child_by_field_name("receiver"))
            if name:
                symbol = f"{receiver}.{name}" if receiver else name
                result["functions"].append(symbol)
        elif node.type == "type_declaration":
            text = node.text.decode(errors="replace")
            for line in text.splitlines():
                line = line.strip()
                if line.startswith("type ") and " struct" in line:
                    parts = line.split()
                    if len(parts) >= 2:
                        result["classes"].append({"name": parts[1], "methods": []})
    return {k: v for k, v in result.items() if v}


def _extract_java(source: bytes, parser) -> dict:
    tree = parser.parse(source)
    result: dict = {"imports": [], "classes": []}

    def walk(node):
        for child in node.children:
            if child.type == "import_declaration":
                result["imports"].append(child.text.decode().strip())
            elif child.type in ("class_declaration", "interface_declaration", "enum_declaration"):
                result["classes"].append(_extract_java_class(child))
            elif child.type == "program" or child.type == "package_declaration":
                pass
            walk(child)

    def _extract_java_class(node) -> dict:
        name = _get_node_text(node.child_by_field_name("name"))
        implements = ""
        methods = []
        for child in node.children:
            if child.type == "superclass":
                implements = child.text.decode().lstrip("extends ").strip()
            elif child.type == "super_interfaces":
                impl_text = child.text.decode().lstrip("implements ").strip()
                implements = f"{implements}, {impl_text}".strip(", ") if implements else impl_text
            elif child.type == "class_body" or child.type == "interface_body" or child.type == "enum_body":
                for member in child.children:
                    if member.type == "method_declaration":
                        mname = _get_node_text(member.child_by_field_name("name"))
                        mparams = _get_node_text(member.child_by_field_name("parameters"))
                        mtype = _get_node_text(member.child_by_field_name("type"))
                        if mname:
                            sig = f"{mtype + ' ' if mtype else ''}{mname}{mparams}"
                            methods.append(sig.strip())
                    elif member.type == "constructor_declaration":
                        mname = _get_node_text(member.child_by_field_name("name"))
                        mparams = _get_node_text(member.child_by_field_name("parameters"))
                        if mname:
                            methods.append(f"{mname}{mparams}")
        entry = {"name": name}
        if implements:
            entry["implements"] = implements
        if methods:
            entry["methods"] = methods
        return entry

    walk(tree.root_node)
    return {k: v for k, v in result.items() if v}


def _extract_rust(source: bytes, parser) -> dict:
    tree = parser.parse(source)
    result: dict = {"functions": [], "classes": []}

    for node in tree.root_node.children:
        if node.type == "function_item":
            name = _get_node_text(node.child_by_field_name("name"))
            params = _get_node_text(node.child_by_field_name("parameters"))
            ret = _get_node_text(node.child_by_field_name("return_type"))
            if name:
                sig = f"fn {name}{params}"
                if ret:
                    sig += f" -> {ret}"
                result["functions"].append(sig)
        elif node.type == "struct_item":
            name = _get_node_text(node.child_by_field_name("name"))
            if name:
                result["classes"].append({"name": name})
        elif node.type == "enum_item":
            name = _get_node_text(node.child_by_field_name("name"))
            if name:
                result["classes"].append({"name": name})
        elif node.type == "trait_item":
            name = _get_node_text(node.child_by_field_name("name"))
            if name:
                result["classes"].append({"name": name, "implements": "trait"})
        elif node.type == "impl_item":
            type_node = node.child_by_field_name("type")
            trait_node = node.child_by_field_name("trait")
            type_name = _get_node_text(type_node)
            methods = []
            for child in node.children:
                if child.type == "declaration_list":
                    for member in child.children:
                        if member.type == "function_item":
                            mname = _get_node_text(member.child_by_field_name("name"))
                            if mname:
                                methods.append(mname)
            if type_name and methods:
                entry = {"name": type_name, "methods": methods}
                if trait_node:
                    entry["implements"] = _get_node_text(trait_node)
                result["classes"].append(entry)

    return {k: v for k, v in result.items() if v}


def _extract_ruby(source: bytes, parser) -> dict:
    tree = parser.parse(source)
    result: dict = {"classes": [], "functions": []}

    def walk(node):
        if node.type == "class":
            name = _get_node_text(node.child_by_field_name("name"))
            superclass = _get_node_text(node.child_by_field_name("superclass"))
            methods = []
            for child in node.children:
                if child.type == "body_statement":
                    for member in child.children:
                        if member.type == "method":
                            mname = _get_node_text(member.child_by_field_name("name"))
                            if mname:
                                methods.append(mname)
            entry = {"name": name}
            if superclass:
                entry["implements"] = superclass.lstrip("< ").strip()
            if methods:
                entry["methods"] = methods
            result["classes"].append(entry)
        elif node.type == "module":
            name = _get_node_text(node.child_by_field_name("name"))
            if name:
                result["classes"].append({"name": name})
        elif node.type == "method" and node.parent and node.parent.type == "program":
            name = _get_node_text(node.child_by_field_name("name"))
            if name:
                result["functions"].append(name)
        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return {k: v for k, v in result.items() if v}


def _extract_php(source: bytes, parser) -> dict:
    tree = parser.parse(source)
    result: dict = {"classes": [], "functions": []}

    def walk(node):
        if node.type == "class_declaration":
            name = _get_node_text(node.child_by_field_name("name"))
            methods = []
            base = ""
            for child in node.children:
                if child.type == "base_clause":
                    base = child.text.decode().replace("extends", "").strip()
                elif child.type == "declaration_list":
                    for member in child.children:
                        if member.type == "method_declaration":
                            mname = _get_node_text(member.child_by_field_name("name"))
                            if mname:
                                methods.append(mname)
            entry = {"name": name}
            if base:
                entry["implements"] = base
            if methods:
                entry["methods"] = methods
            result["classes"].append(entry)
        elif node.type == "function_definition":
            name = _get_node_text(node.child_by_field_name("name"))
            if name:
                result["functions"].append(name)
        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return {k: v for k, v in result.items() if v}


def _extract_c_cpp(source: bytes, parser) -> dict:
    tree = parser.parse(source)
    result: dict = {"functions": [], "classes": []}

    for node in tree.root_node.children:
        if node.type == "function_definition":
            declarator = node.child_by_field_name("declarator")
            if declarator:
                name = _get_node_text(declarator.child_by_field_name("declarator")) or _get_node_text(declarator)
                if name and "(" in name:
                    name = name.split("(")[0]
                if name:
                    result["functions"].append(name.strip())
        elif node.type in ("struct_specifier", "class_specifier"):
            name = _get_node_text(node.child_by_field_name("name"))
            if name:
                result["classes"].append({"name": name})

    return {k: v for k, v in result.items() if v}


def _extract_kotlin(source: bytes, parser) -> dict:
    tree = parser.parse(source)
    result: dict = {"imports": [], "classes": [], "functions": []}

    def walk(node):
        if node.type == "import_header":
            result["imports"].append(node.text.decode().strip())
        elif node.type in ("class_declaration", "object_declaration"):
            name = _get_node_text(node.child_by_field_name("name")) or ""
            methods = []
            supertype = ""
            for child in node.children:
                if child.type == "delegation_specifier":
                    supertype = child.text.decode().strip()
                elif child.type == "class_body":
                    for member in child.children:
                        if member.type == "function_declaration":
                            mname = _get_node_text(member.child_by_field_name("name"))
                            if mname:
                                methods.append(mname)
            if name:
                entry = {"name": name}
                if supertype:
                    entry["implements"] = supertype
                if methods:
                    entry["methods"] = methods
                result["classes"].append(entry)
        elif node.type == "function_declaration" and node.parent and node.parent.type == "source_file":
            name = _get_node_text(node.child_by_field_name("name"))
            if name:
                result["functions"].append(name)
        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return {k: v for k, v in result.items() if v}


def _extract_swift(source: bytes, parser) -> dict:
    tree = parser.parse(source)
    result: dict = {"classes": [], "functions": []}

    def walk(node):
        if node.type in ("class_declaration", "struct_declaration", "protocol_declaration", "enum_declaration"):
            name = _get_node_text(node.child_by_field_name("name"))
            methods = []
            for child in node.children:
                if child.type == "class_body" or child.type == "protocol_body":
                    for member in child.children:
                        if member.type == "function_declaration":
                            mname = _get_node_text(member.child_by_field_name("name"))
                            if mname:
                                methods.append(mname)
            if name:
                entry = {"name": name}
                if methods:
                    entry["methods"] = methods
                result["classes"].append(entry)
        elif node.type == "function_declaration" and node.parent and node.parent.type == "source_file":
            name = _get_node_text(node.child_by_field_name("name"))
            if name:
                result["functions"].append(name)
        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return {k: v for k, v in result.items() if v}


def _extract_scala(source: bytes, parser) -> dict:
    tree = parser.parse(source)
    result: dict = {"classes": [], "functions": []}

    def walk(node):
        if node.type in ("class_definition", "trait_definition", "object_definition"):
            name = _get_node_text(node.child_by_field_name("name"))
            methods = []
            for child in node.children:
                if child.type == "template_body":
                    for member in child.children:
                        if member.type == "function_definition":
                            mname = _get_node_text(member.child_by_field_name("name"))
                            if mname:
                                methods.append(mname)
            if name:
                entry = {"name": name}
                if methods:
                    entry["methods"] = methods
                result["classes"].append(entry)
        elif node.type == "function_definition" and node.parent and node.parent.type == "compilation_unit":
            name = _get_node_text(node.child_by_field_name("name"))
            if name:
                result["functions"].append(name)
        for child in node.children:
            walk(child)

    walk(tree.root_node)
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
        elif language == "go":
            return _extract_go(source, parser)
        elif language == "java":
            return _extract_java(source, parser)
        elif language == "rust":
            return _extract_rust(source, parser)
        elif language == "ruby":
            return _extract_ruby(source, parser)
        elif language == "php":
            return _extract_php(source, parser)
        elif language in ("c", "cpp"):
            return _extract_c_cpp(source, parser)
        elif language == "kotlin":
            return _extract_kotlin(source, parser)
        elif language == "swift":
            return _extract_swift(source, parser)
        elif language == "scala":
            return _extract_scala(source, parser)
        return None
    except Exception as exc:
        print(f"[mnemo] Failed to parse {language} file: {exc}", file=sys.stderr)
        return None


# --- Hash index for change detection ---

def _load_hashes(repo_root: Path) -> dict[str, str]:
    data = get_storage(repo_root).read_collection(Collections.HASHES)
    if not isinstance(data, dict):
        return {}
    return {str(path): str(file_hash) for path, file_hash in data.items()}


def _save_hashes(repo_root: Path, hashes: dict[str, str]):
    get_storage(repo_root).write_collection(Collections.HASHES, hashes)


def has_changes(repo_root: Path) -> bool:
    """Quick check if any files changed since last map generation using mtime."""
    summary_path = mnemo_path(repo_root) / "summary.md"
    if not summary_path.exists():
        return True
    last_map_time = summary_path.stat().st_mtime

    for ext in SUPPORTED_EXTENSIONS:
        for filepath in repo_root.rglob(f"*{ext}"):
            if _should_ignore(filepath) or filepath.stat().st_size > MAX_FILE_SIZE:
                continue
            try:
                if filepath.stat().st_mtime > last_map_time:
                    return True
            except OSError:
                continue
    return False


# --- Summary generation ---

def generate_summary(repo_root: Path, index: bool = True) -> str:
    """Generate a compact markdown summary of the repo structure."""
    tree: dict[str, dict[str, list[str]]] = {}
    hashes: dict[str, str] = {}
    all_chunks = []

    # Try Roslyn for C# if .NET SDK is available
    from .analyzers import roslyn_available, run_roslyn_analyzer, roslyn_to_mnemo_format
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
            hashes[rel] = hashlib.md5(source).hexdigest()

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
        from .graph.builder import build_graph
        build_graph(repo_root)
    except Exception as exc:
        import sys
        print(f"[mnemo] Graph build failed (non-fatal): {exc}", file=sys.stderr)
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
