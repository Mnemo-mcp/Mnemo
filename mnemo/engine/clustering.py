"""Community detection — cluster symbols into functional areas using Louvain."""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path
from typing import Any

import networkx as nx


def detect_communities(conn: Any) -> int:
    """Run Louvain community detection on the code graph. Returns community count."""
    G = _build_symbol_graph(conn)
    if G.number_of_nodes() < 3 or G.number_of_edges() == 0:
        return 0

    communities = nx.community.louvain_communities(G, seed=42, resolution=0.5)
    if not communities:
        return 0

    return _store_communities(conn, G, communities)


def _build_symbol_graph(conn: Any) -> nx.Graph:
    """Build a NetworkX graph from LadybugDB symbol nodes and edges."""
    G = nx.Graph()

    # Load nodes
    result = conn.execute("MATCH (c:Class) RETURN c.id, c.name")
    while result.has_next():
        row = result.get_next()
        G.add_node(row[0], name=row[1], type="class")

    result = conn.execute("MATCH (f:Function) RETURN f.id, f.name")
    while result.has_next():
        row = result.get_next()
        G.add_node(row[0], name=row[1], type="function")

    if G.number_of_nodes() < 3:
        return G

    # Build file→symbols mapping
    file_to_symbols = _get_file_symbols(conn)

    # Co-location edges (same file = likely same module)
    for symbols in file_to_symbols.values():
        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                if symbols[i] in G and symbols[j] in G:
                    G.add_edge(symbols[i], symbols[j], weight=1.0)

    # CALLS edges (higher weight)
    result = conn.execute("MATCH (a:Function)-[c:CALLS]->(b:Function) RETURN a.id, b.id, c.confidence")
    while result.has_next():
        row = result.get_next()
        if row[0] in G and row[1] in G:
            G.add_edge(row[0], row[1], weight=row[2] * 2.0)

    # Directory proximity (weaker signal)
    _add_directory_edges(G, file_to_symbols)

    # Project boundaries (strong cluster seeds)
    _add_project_edges(conn, G, file_to_symbols)

    return G


def _get_file_symbols(conn: Any) -> dict[str, list[str]]:
    """Get mapping of file paths to their defined symbols."""
    file_to_symbols: dict[str, list[str]] = {}

    result = conn.execute("MATCH (f:File)-[:FILE_DEFINES_CLASS]->(c:Class) RETURN f.path, c.id")
    while result.has_next():
        row = result.get_next()
        file_to_symbols.setdefault(row[0], []).append(row[1])

    result = conn.execute("MATCH (f:File)-[:FILE_DEFINES_FUNCTION]->(fn:Function) RETURN f.path, fn.id")
    while result.has_next():
        row = result.get_next()
        file_to_symbols.setdefault(row[0], []).append(row[1])

    return file_to_symbols


def _add_directory_edges(G: nx.Graph, file_to_symbols: dict[str, list[str]]) -> None:
    """Add weak edges between symbols in the same directory."""
    dir_to_symbols: dict[str, list[str]] = {}
    for filepath, symbols in file_to_symbols.items():
        dir_path = "/".join(filepath.split("/")[:-1]) or "."
        dir_to_symbols.setdefault(dir_path, []).extend(symbols)

    for symbols in dir_to_symbols.values():
        if len(symbols) > 1:
            for i in range(min(len(symbols) - 1, 10)):
                if symbols[i] in G and symbols[i + 1] in G:
                    G.add_edge(symbols[i], symbols[i + 1], weight=0.3)


def _add_project_edges(conn: Any, G: nx.Graph, file_to_symbols: dict[str, list[str]]) -> None:
    """Add strong intra-project edges to seed clusters along project boundaries."""
    try:
        result = conn.execute("MATCH (p:Project)-[:PROJECT_CONTAINS]->(f:File) RETURN p.id, f.path")
        project_files: dict[str, list[str]] = {}
        while result.has_next():
            row = result.get_next()
            project_files.setdefault(row[0], []).append(row[1])

        for proj_file_paths in project_files.values():
            proj_symbols = []
            for fp in proj_file_paths:
                proj_symbols.extend(file_to_symbols.get(fp, []))
            for i in range(min(len(proj_symbols) - 1, 50)):
                if proj_symbols[i] in G and proj_symbols[i + 1] in G:
                    G.add_edge(proj_symbols[i], proj_symbols[i + 1], weight=3.0)
    except RuntimeError:
        pass  # Project table may not exist in older DBs


def _store_communities(conn: Any, G: nx.Graph, communities: list[set]) -> int:
    """Store detected communities in LadybugDB. Returns count stored."""
    community_data = []
    membership_rows = []
    used_names: dict[str, int] = {}

    for i, community in enumerate(communities):
        if len(community) < 2:
            continue

        name = _pick_community_name(community, i)
        # Deduplicate names by appending a distinguishing suffix
        if name in used_names:
            used_names[name] += 1
            name = f"{name}-{used_names[name]}"
        else:
            used_names[name] = 0

        cid = f"community:{i}"
        community_data.append([cid, name, f"{len(community)} symbols"])

        for node_id in community:
            node_data = G.nodes.get(node_id, {})
            if node_data.get("type") == "class":
                membership_rows.append(("class", node_id, cid))
            elif node_data.get("type") == "function":
                membership_rows.append(("function", node_id, cid))

    if not community_data:
        return 0

    # Load into LadybugDB
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        comm_csv = tmp_path / "communities.csv"
        with open(comm_csv, "w", newline="") as f:
            csv.writer(f).writerows(community_data)
        conn.execute(f'COPY Community FROM "{comm_csv}"')

        class_members = [[row[1], row[2]] for row in membership_rows if row[0] == "class"]
        if class_members:
            cm_csv = tmp_path / "member_class.csv"
            with open(cm_csv, "w", newline="") as f:
                csv.writer(f).writerows(class_members)
            try:
                conn.execute(f'COPY MEMBER_OF FROM "{cm_csv}"')
            except RuntimeError:
                pass

        fn_members = [[row[1], row[2]] for row in membership_rows if row[0] == "function"]
        if fn_members:
            fm_csv = tmp_path / "member_fn.csv"
            with open(fm_csv, "w", newline="") as f:
                csv.writer(f).writerows(fn_members)
            try:
                conn.execute(f'COPY FN_MEMBER_OF FROM "{fm_csv}"')
            except RuntimeError:
                pass

    return len(community_data)


def _pick_community_name(community: set, index: int) -> str:
    """Pick a human-readable name for a community based on file paths."""
    paths = set()
    for node_id in community:
        parts = node_id.split(":")
        if len(parts) >= 2:
            filepath = parts[0] if "/" in parts[0] else ""
            if filepath:
                segments = filepath.split("/")
                # Use up to 3 segments for better naming
                paths.add("/".join(segments[:min(3, len(segments))]))

    if not paths:
        return f"cluster-{index}"

    sorted_paths = sorted(paths)
    if len(sorted_paths) == 1:
        return sorted_paths[0].replace("/", "-") or f"cluster-{index}"

    # Find the most common deepest shared prefix
    from collections import Counter
    tops = Counter(p for p in sorted_paths)
    if tops:
        # Pick the most common path prefix
        best = tops.most_common(1)[0][0]
        return best.replace("/", "-")

    return f"cluster-{index}"
