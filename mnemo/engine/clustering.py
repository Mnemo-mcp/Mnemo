"""Community detection — cluster symbols into functional areas using Louvain."""

from __future__ import annotations

import csv
import tempfile
from pathlib import Path
from typing import Any

import networkx as nx


def detect_communities(conn: Any) -> int:
    """Run Louvain community detection on the code graph. Returns community count."""
    # Build a NetworkX graph from LadybugDB edges
    G = nx.Graph()

    # Add nodes from classes and functions
    result = conn.execute("MATCH (c:Class) RETURN c.id, c.name")
    while result.has_next():
        row = result.get_next()
        G.add_node(row[0], name=row[1], type="class")

    result = conn.execute("MATCH (f:Function) RETURN f.id, f.name")
    while result.has_next():
        row = result.get_next()
        G.add_node(row[0], name=row[1], type="function")

    if G.number_of_nodes() < 3:
        return 0

    # Add edges (CALLS, HAS_METHOD, FILE_DEFINES_*)
    # Co-location edges: symbols in the same file are connected
    result = conn.execute("""
        MATCH (f:File)-[:FILE_DEFINES_CLASS]->(c:Class)
        RETURN f.path, c.id
    """)
    file_to_symbols: dict[str, list[str]] = {}
    while result.has_next():
        row = result.get_next()
        file_to_symbols.setdefault(row[0], []).append(row[1])

    result = conn.execute("""
        MATCH (f:File)-[:FILE_DEFINES_FUNCTION]->(fn:Function)
        RETURN f.path, fn.id
    """)
    while result.has_next():
        row = result.get_next()
        file_to_symbols.setdefault(row[0], []).append(row[1])

    # Connect symbols in the same file (co-location = likely same module)
    for symbols in file_to_symbols.values():
        for i in range(len(symbols)):
            for j in range(i + 1, len(symbols)):
                if symbols[i] in G and symbols[j] in G:
                    G.add_edge(symbols[i], symbols[j], weight=1.0)

    # Add CALLS edges with higher weight
    result = conn.execute("MATCH (a:Function)-[c:CALLS]->(b:Function) RETURN a.id, b.id, c.confidence")
    while result.has_next():
        row = result.get_next()
        if row[0] in G and row[1] in G:
            G.add_edge(row[0], row[1], weight=row[2] * 2.0)

    # Connect symbols in same directory (weaker signal)
    dir_to_symbols: dict[str, list[str]] = {}
    for filepath, symbols in file_to_symbols.items():
        dir_path = "/".join(filepath.split("/")[:-1]) or "."
        dir_to_symbols.setdefault(dir_path, []).extend(symbols)

    for symbols in dir_to_symbols.values():
        # Only connect first symbol of each file in same dir (avoid O(n²))
        if len(symbols) > 1:
            for i in range(min(len(symbols) - 1, 10)):
                if symbols[i] in G and symbols[i + 1] in G:
                    G.add_edge(symbols[i], symbols[i + 1], weight=0.3)

    if G.number_of_edges() == 0:
        return 0

    # Run Louvain community detection
    communities = nx.community.louvain_communities(G, seed=42, resolution=1.0)

    if not communities:
        return 0

    # Name communities by most common directory prefix
    community_data = []
    membership_rows = []

    for i, community in enumerate(communities):
        if len(community) < 2:
            continue  # Skip singleton communities

        # Determine community name from file paths
        paths = set()
        for node_id in community:
            parts = node_id.split(":")
            if len(parts) >= 2:
                filepath = parts[0] if "/" in parts[0] else ""
                if filepath:
                    paths.add("/".join(filepath.split("/")[:2]))

        name = _pick_community_name(paths, i)
        cid = f"community:{i}"
        community_data.append([cid, name, f"{len(community)} symbols"])

        # Create membership edges
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

        # Community nodes
        comm_csv = tmp_path / "communities.csv"
        with open(comm_csv, "w", newline="") as f:
            csv.writer(f).writerows(community_data)
        conn.execute(f'COPY Community FROM "{comm_csv}"')

        # Membership edges (Class → Community)
        class_members = [[row[1], row[2]] for row in membership_rows if row[0] == "class"]
        if class_members:
            cm_csv = tmp_path / "member_class.csv"
            with open(cm_csv, "w", newline="") as f:
                csv.writer(f).writerows(class_members)
            try:
                conn.execute(f'COPY MEMBER_OF FROM "{cm_csv}"')
            except RuntimeError:
                pass

        # Function → Community
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


def _pick_community_name(paths: set[str], index: int) -> str:
    """Pick a human-readable name for a community based on file paths."""
    if not paths:
        return f"cluster-{index}"

    # Find most common prefix
    sorted_paths = sorted(paths)
    if len(sorted_paths) == 1:
        return sorted_paths[0].replace("/", "-") or f"cluster-{index}"

    # Use the most common top-level directory
    from collections import Counter
    tops = Counter(p.split("/")[0] for p in sorted_paths if "/" in p)
    if tops:
        return tops.most_common(1)[0][0]

    return f"cluster-{index}"
