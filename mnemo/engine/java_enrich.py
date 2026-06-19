"""Java tree-sitter enrichment — extract method invocations, object creations, and field types.

Walks into method bodies to find:
- method_invocation: obj.method() → (caller, target_type, target_method)
- object_creation_expression: new Foo() → (caller, Foo, <init>)
- field types (for type reference edges)

Uses import statements to resolve short class names to known symbols.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ..repo_map.parsers import _get_parser, _get_node_text


@dataclass
class JavaInvocation:
    caller_class: str
    caller_method: str
    target_type: str  # resolved class name or raw receiver type
    target_method: str


@dataclass
class JavaFileEnrichment:
    path: str
    invocations: list[JavaInvocation] = field(default_factory=list)
    type_refs: set[str] = field(default_factory=set)  # all type names referenced


def enrich_java_files(repo_root: Path, java_files: list[str]) -> dict[str, JavaFileEnrichment]:
    """Parse Java files and extract method invocations and type references.

    Args:
        repo_root: Repository root path
        java_files: List of relative file paths to enrich

    Returns:
        Dict mapping file path → enrichment data
    """
    parser = _get_parser("java")
    if not parser:
        return {}

    results: dict[str, JavaFileEnrichment] = {}

    for rel_path in java_files:
        filepath = repo_root / rel_path
        try:
            source = filepath.read_bytes()
        except (OSError, PermissionError):
            continue

        enrichment = _enrich_single_file(source, rel_path, parser)
        if enrichment.invocations or enrichment.type_refs:
            results[rel_path] = enrichment

    return results


def _enrich_single_file(source: bytes, path: str, parser) -> JavaFileEnrichment:
    """Extract invocations and type refs from a single Java file."""
    tree = parser.parse(source)
    enrichment = JavaFileEnrichment(path=path)

    # Collect import mappings: short name → fully qualified
    imports: dict[str, str] = {}  # ClassName → full.package.ClassName
    for node in tree.root_node.children:
        if node.type == "import_declaration":
            text = _get_node_text(node).replace("import ", "").replace("static ", "").rstrip(";").strip()
            if not text.endswith("*"):
                short = text.rsplit(".", 1)[-1]
                imports[short] = text

    # Walk class declarations
    _walk_for_classes(tree.root_node, enrichment, imports)
    return enrichment


def _walk_for_classes(node, enrichment: JavaFileEnrichment, imports: dict[str, str]):
    """Recursively find class/interface declarations and extract their body."""
    for child in node.children:
        if child.type in ("class_declaration", "interface_declaration", "enum_declaration"):
            class_name = _get_node_text(child.child_by_field_name("name"))
            if class_name:
                # Extract type refs from extends/implements
                for sub in child.children:
                    if sub.type in ("superclass", "super_interfaces"):
                        _collect_type_refs(sub, enrichment.type_refs)
                    elif sub.type in ("class_body", "interface_body", "enum_body"):
                        _walk_class_body(sub, class_name, enrichment, imports)
        elif child.type in ("program", "package_declaration"):
            pass
        _walk_for_classes(child, enrichment, imports)


def _walk_class_body(body_node, class_name: str, enrichment: JavaFileEnrichment, imports: dict[str, str]):
    """Walk a class body extracting method invocations and field types."""
    for member in body_node.children:
        if member.type == "method_declaration" or member.type == "constructor_declaration":
            method_name = _get_node_text(member.child_by_field_name("name")) or class_name
            # Walk the method body for invocations
            body = member.child_by_field_name("body")
            if body:
                _walk_for_invocations(body, class_name, method_name, enrichment, imports)
        elif member.type == "field_declaration":
            # Extract field type reference
            type_node = member.child_by_field_name("type")
            if type_node:
                _collect_type_refs(type_node, enrichment.type_refs)


def _walk_for_invocations(node, class_name: str, method_name: str, enrichment: JavaFileEnrichment, imports: dict[str, str]):
    """Recursively walk AST nodes to find method invocations and object creations."""
    if node.type == "method_invocation":
        obj_node = node.child_by_field_name("object")
        name_node = node.child_by_field_name("name")
        target_method = _get_node_text(name_node)
        if target_method:
            target_type = _resolve_receiver_type(obj_node, imports) if obj_node else class_name
            if target_type and len(target_type) >= 2:
                enrichment.invocations.append(JavaInvocation(
                    caller_class=class_name,
                    caller_method=method_name,
                    target_type=target_type,
                    target_method=target_method,
                ))
    elif node.type == "object_creation_expression":
        type_node = node.child_by_field_name("type")
        if type_node:
            type_name = _get_type_name(type_node)
            if type_name:
                enrichment.type_refs.add(type_name)
                enrichment.invocations.append(JavaInvocation(
                    caller_class=class_name,
                    caller_method=method_name,
                    target_type=type_name,
                    target_method="<init>",
                ))

    for child in node.children:
        _walk_for_invocations(child, class_name, method_name, enrichment, imports)


def _resolve_receiver_type(obj_node, imports: dict[str, str]) -> str:
    """Try to resolve the receiver of a method call to a type name."""
    if obj_node is None:
        return ""
    # If it's a simple identifier that starts with uppercase → likely a class (static call)
    text = _get_node_text(obj_node)
    if obj_node.type == "identifier" and text and text[0].isupper():
        return imports.get(text, text)
    # If it's a field_access like Foo.bar, the leftmost might be a class
    if obj_node.type == "field_access":
        obj = obj_node.child_by_field_name("object")
        if obj:
            t = _get_node_text(obj)
            if t and t[0].isupper():
                return imports.get(t, t)
    # For `this.method()` or variable.method(), we can't resolve type without symbol table
    return ""


def _get_type_name(type_node) -> str:
    """Extract type name from a type node, handling generics."""
    if type_node.type == "type_identifier":
        return _get_node_text(type_node)
    elif type_node.type == "generic_type":
        # Get just the base type, not the generic params
        for child in type_node.children:
            if child.type == "type_identifier":
                return _get_node_text(child)
    elif type_node.type == "scoped_type_identifier":
        # e.g., Map.Entry — get the full thing
        return _get_node_text(type_node)
    return _get_node_text(type_node).split("<")[0].strip()


def _collect_type_refs(node, type_refs: set[str]):
    """Collect all type identifier references from a node subtree."""
    if node.type == "type_identifier":
        name = _get_node_text(node)
        if name and name[0].isupper() and len(name) >= 2:
            type_refs.add(name)
    for child in node.children:
        _collect_type_refs(child, type_refs)
