"""Graph builder — constructs knowledge graph from repo map, git, and stored data."""

from __future__ import annotations

import re
from pathlib import Path

from . import Node, Edge
from .local import LocalGraph
from .relationships import extract_call_edges, extract_dependency_edges, extract_ownership_edges
from ..config import SUPPORTED_EXTENSIONS, should_ignore
from ..repo_map import _extract_file, MAX_FILE_SIZE
from ..storage import Collections, get_storage


def build_graph(repo_root: Path, graph: LocalGraph | None = None) -> LocalGraph:
    """Build the full knowledge graph for a repository."""
    if graph is None:
        graph = LocalGraph(repo_root)
        graph._graph.clear()
        graph._loaded = True

    all_class_names: set[str] = set()
    file_sources: dict[str, str] = {}

    # Pass 1: Create service, file, class, interface, method nodes
    for ext, language in SUPPORTED_EXTENSIONS.items():
        for filepath in repo_root.rglob(f"*{ext}"):
            if should_ignore(filepath) or filepath.stat().st_size > MAX_FILE_SIZE:
                continue
            try:
                source = filepath.read_bytes()
            except (OSError, PermissionError):
                continue

            rel = str(filepath.relative_to(repo_root))
            parts = rel.split("/")
            service = parts[0] if len(parts) > 1 else "root"

            # Service node
            service_id = f"service:{service}"
            graph.upsert_node(Node(id=service_id, type="service", name=service))

            # File node
            file_id = f"file:{rel}"
            graph.upsert_node(Node(id=file_id, type="file", name=rel, properties={"language": language}))
            graph.upsert_edge(Edge(source=service_id, target=file_id, type="contains"))

            # Parse
            info = _extract_file(source, language)
            if not info:
                continue

            file_sources[rel] = source.decode(errors="replace")

            for cls in info.get("classes", []):
                name = cls["name"]
                all_class_names.add(name)
                impl = cls.get("implements", "")
                cls_id = f"class:{name}"
                graph.upsert_node(Node(id=cls_id, type="class", name=name, properties={"file": rel, "implements": impl}))
                graph.upsert_edge(Edge(source=file_id, target=cls_id, type="defines"))

                # Implements/inherits edges
                if impl:
                    for base in re.split(r'[,\s]+', impl):
                        base = base.strip()
                        if not base:
                            continue
                        # Heuristic: starts with I and uppercase = interface
                        if base.startswith("I") and len(base) > 1 and base[1].isupper():
                            iface_id = f"interface:{base}"
                            graph.upsert_node(Node(id=iface_id, type="interface", name=base))
                            graph.upsert_edge(Edge(source=cls_id, target=iface_id, type="implements"))
                        else:
                            base_id = f"class:{base}"
                            graph.upsert_node(Node(id=base_id, type="class", name=base))
                            graph.upsert_edge(Edge(source=cls_id, target=base_id, type="inherits"))

                # Method nodes
                for method_sig in cls.get("methods", []):
                    mname = method_sig.split("(")[0].split()[-1] if method_sig else ""
                    if mname and not mname.startswith("_"):
                        method_id = f"method:{name}.{mname}"
                        graph.upsert_node(Node(id=method_id, type="method", name=f"{name}.{mname}", properties={"signature": method_sig, "file": rel}))
                        graph.upsert_edge(Edge(source=cls_id, target=method_id, type="has_method"))

            for func in info.get("functions", []):
                fname = func.split("(")[0].replace("def ", "").replace("func ", "").strip()
                if fname and not fname.startswith("_"):
                    func_id = f"function:{rel}:{fname}"
                    graph.upsert_node(Node(id=func_id, type="function", name=fname, properties={"signature": func, "file": rel}))
                    graph.upsert_edge(Edge(source=file_id, target=func_id, type="defines"))

    # Pass 2: Call edges (which files reference which classes)
    for rel, source_text in file_sources.items():
        file_id = f"file:{rel}"
        # Find classes defined in THIS file to exclude self-references
        local_classes = {data.get("name", "") for _, data in graph.graph.nodes(data=True)
                        if data.get("type") == "class" and data.get("file") == rel}
        external_classes = all_class_names - local_classes
        for edge in extract_call_edges(repo_root, rel, source_text, external_classes):
            if edge.target in graph.graph:
                graph.upsert_edge(edge)

    # Pass 3: Package dependencies
    for service, pkg, meta in extract_dependency_edges(repo_root):
        service_id = f"service:{service}"
        pkg_id = f"package:{pkg}"
        graph.upsert_node(Node(id=pkg_id, type="package", name=pkg, properties=meta))
        if service_id in graph.graph:
            graph.upsert_edge(Edge(source=service_id, target=pkg_id, type="depends_on"))

    # Pass 4: Ownership from git
    for person, service, count in extract_ownership_edges(repo_root):
        person_id = f"person:{person}"
        service_id = f"service:{service}"
        graph.upsert_node(Node(id=person_id, type="person", name=person))
        if service_id in graph.graph:
            graph.upsert_edge(Edge(source=person_id, target=service_id, type="owns", properties={"commits": count}))

    # Pass 5: Link existing memories, decisions, incidents, errors
    _link_stored_data(repo_root, graph, all_class_names)

    graph.save()
    return graph


def _link_stored_data(repo_root: Path, graph: LocalGraph, known_names: set[str]) -> None:
    """Create nodes and reference edges for stored memories, decisions, incidents, errors."""
    storage = get_storage(repo_root)

    # Decisions
    decisions = storage.read_collection(Collections.DECISIONS)
    if isinstance(decisions, list):
        for d in decisions:
            did = f"decision:{d.get('id', 0)}"
            text = d.get("decision", "")
            graph.upsert_node(Node(id=did, type="decision", name=text[:80], properties={"full_text": text, "reasoning": d.get("reasoning", "")}))
            _auto_link_text(graph, did, text, known_names)

    # Memories
    memories = storage.read_collection(Collections.MEMORY)
    if isinstance(memories, list):
        for m in memories:
            mid = f"memory:{m.get('id', 0)}"
            text = m.get("content", "")
            graph.upsert_node(Node(id=mid, type="memory", name=text[:80], properties={"category": m.get("category", "general"), "full_text": text}))
            _auto_link_text(graph, mid, text, known_names)

    # Incidents
    incidents_data = storage.read_collection("incidents")
    if isinstance(incidents_data, list):
        for inc in incidents_data:
            iid = f"incident:{inc.get('id', 0)}"
            title = inc.get("title", "")
            graph.upsert_node(Node(id=iid, type="incident", name=title, properties={"severity": inc.get("severity", ""), "root_cause": inc.get("root_cause", "")}))
            # Link to services mentioned
            for svc in inc.get("services", []):
                svc_id = f"service:{svc}"
                if svc_id in graph.graph:
                    graph.upsert_edge(Edge(source=iid, target=svc_id, type="affects"))
            _auto_link_text(graph, iid, f"{title} {inc.get('root_cause', '')} {inc.get('fix', '')}", known_names)

    # Errors
    errors_data = storage.read_collection("errors")
    if isinstance(errors_data, list):
        for err in errors_data:
            eid = f"error:{err.get('id', 0)}"
            error_text = err.get("error", "")
            graph.upsert_node(Node(id=eid, type="error", name=error_text[:80], properties={"cause": err.get("cause", ""), "fix": err.get("fix", "")}))
            if err.get("file"):
                file_id = f"file:{err['file']}"
                if file_id in graph.graph:
                    graph.upsert_edge(Edge(source=eid, target=file_id, type="occurs_in"))
            _auto_link_text(graph, eid, f"{error_text} {err.get('cause', '')}", known_names)


def _auto_link_text(graph: LocalGraph, source_id: str, text: str, known_names: set[str]) -> None:
    """Auto-detect entity references in text and create reference edges."""
    if not text:
        return
    for name in known_names:
        if len(name) < 4:
            continue
        if name in text:
            target_id = f"class:{name}"
            if target_id in graph.graph:
                graph.upsert_edge(Edge(source=source_id, target=target_id, type="references"))
            # Also check service names
    # Check service nodes
    for nid, data in graph.graph.nodes(data=True):
        if data.get("type") == "service" and data.get("name", "") in text:
            graph.upsert_edge(Edge(source=source_id, target=nid, type="references"))


def incremental_update(repo_root: Path, changed_files: list[str]) -> LocalGraph:
    """Update only the subgraph for changed files."""
    graph = LocalGraph(repo_root)
    graph._ensure_loaded()

    all_class_names = {data.get("name", "") for _, data in graph.graph.nodes(data=True) if data.get("type") == "class"}

    for file_path in changed_files:
        file_id = f"file:{file_path}"

        # Remove old nodes defined by this file
        to_remove = []
        for _, target, data in graph.graph.out_edges(file_id, data=True):
            if data.get("type") == "defines":
                to_remove.append(target)
        for nid in to_remove:
            graph.remove_node(nid)

        # Re-parse and add
        full_path = repo_root / file_path
        if not full_path.exists():
            graph.remove_node(file_id)
            continue

        language = None
        for ext, lang in SUPPORTED_EXTENSIONS.items():
            if file_path.endswith(ext):
                language = lang
                break
        if not language:
            continue

        try:
            source = full_path.read_bytes()
        except (OSError, PermissionError):
            continue

        info = _extract_file(source, language)
        if not info:
            continue

        source_text = source.decode(errors="replace")

        for cls in info.get("classes", []):
            name = cls["name"]
            all_class_names.add(name)
            impl = cls.get("implements", "")
            cls_id = f"class:{name}"
            graph.upsert_node(Node(id=cls_id, type="class", name=name, properties={"file": file_path, "implements": impl}))
            graph.upsert_edge(Edge(source=file_id, target=cls_id, type="defines"))

            if impl:
                for base in re.split(r'[,\s]+', impl):
                    base = base.strip()
                    if not base:
                        continue
                    if base.startswith("I") and len(base) > 1 and base[1].isupper():
                        iface_id = f"interface:{base}"
                        graph.upsert_node(Node(id=iface_id, type="interface", name=base))
                        graph.upsert_edge(Edge(source=cls_id, target=iface_id, type="implements"))
                    else:
                        base_id = f"class:{base}"
                        graph.upsert_node(Node(id=base_id, type="class", name=base))
                        graph.upsert_edge(Edge(source=cls_id, target=base_id, type="inherits"))

            for method_sig in cls.get("methods", []):
                mname = method_sig.split("(")[0].split()[-1] if method_sig else ""
                if mname and not mname.startswith("_"):
                    method_id = f"method:{name}.{mname}"
                    graph.upsert_node(Node(id=method_id, type="method", name=f"{name}.{mname}", properties={"signature": method_sig, "file": file_path}))
                    graph.upsert_edge(Edge(source=cls_id, target=method_id, type="has_method"))

        # Call edges
        local_classes = {data.get("name", "") for _, data in graph.graph.nodes(data=True)
                        if data.get("type") == "class" and data.get("file") == file_path}
        external_classes = all_class_names - local_classes
        for edge in extract_call_edges(repo_root, file_path, source_text, external_classes):
            if edge.target in graph.graph:
                graph.upsert_edge(edge)

    graph.save()
    return graph
