"""Graph layout — two-pass force-directed, computed lazily at serve time."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import networkx as nx

from ..config import mnemo_path


def compute_and_save_layout(repo_root: Path, conn: Any) -> None:
    """Two-pass layout: community spring + per-cluster golden-angle scatter."""

    # Step 1: Get all community membership (single query each)
    comm_members: dict[str, list[str]] = {}
    node_comm: dict[str, str] = {}

    r = conn.execute("MATCH (c:Class)-[:MEMBER_OF]->(comm:Community) RETURN c.id, comm.id")
    while r.has_next():
        row = r.get_next()
        node_comm[row[0]] = row[1]
        comm_members.setdefault(row[1], []).append(row[0])

    r = conn.execute("MATCH (f:Function)-[:FN_MEMBER_OF]->(comm:Community) RETURN f.id, comm.id")
    while r.has_next():
        row = r.get_next()
        node_comm[row[0]] = row[1]
        comm_members.setdefault(row[1], []).append(row[0])

    if not comm_members:
        (mnemo_path(repo_root) / "layout.json").write_text("{}")
        return

    # Step 2: Get inter-community edges (single query)
    comm_edges: dict[tuple[str, str], int] = {}
    try:
        r = conn.execute("MATCH (a:Class)-[:CLASS_DEPENDS]->(b:Class) RETURN a.id, b.id")
        while r.has_next():
            row = r.get_next()
            ca, cb = node_comm.get(row[0]), node_comm.get(row[1])
            if ca and cb and ca != cb:
                key = (min(ca, cb), max(ca, cb))
                comm_edges[key] = comm_edges.get(key, 0) + 1
    except RuntimeError:
        pass

    # Step 3: Spring layout on community meta-graph (~1300 nodes, fast)
    CG = nx.Graph()
    for cid in comm_members:
        CG.add_node(cid)
    for (ca, cb), w in comm_edges.items():
        CG.add_edge(ca, cb, weight=w)

    comm_pos = nx.spring_layout(CG, k=2.0 / max(CG.number_of_nodes() ** 0.3, 1), iterations=100, seed=42)

    # Step 4: Position members using golden-angle spiral (instant, no iteration)
    layout: dict[str, list[float]] = {}
    for cid, members in comm_members.items():
        cx, cy = comm_pos.get(cid, (0.0, 0.0))
        cx, cy = float(cx), float(cy)
        layout[cid] = [cx, cy]

        spread = math.sqrt(len(members)) * 0.06
        for i, nid in enumerate(members):
            angle = i * 2.39996323  # golden angle in radians
            r = spread * math.sqrt(i + 1) / math.sqrt(len(members))
            layout[nid] = [cx + math.cos(angle) * r, cy + math.sin(angle) * r]

    # Step 5: Orphan nodes
    all_ids: set[str] = set()
    r = conn.execute("MATCH (c:Class) RETURN c.id")
    while r.has_next():
        all_ids.add(r.get_next()[0])
    r = conn.execute("MATCH (f:Function) RETURN f.id")
    while r.has_next():
        all_ids.add(r.get_next()[0])
    r = conn.execute("MATCH (p:Project) RETURN p.id")
    while r.has_next():
        all_ids.add(r.get_next()[0])

    orphans = all_ids - set(layout.keys())
    for i, nid in enumerate(orphans):
        angle = i * 2.39996323
        r = 0.2 * math.sqrt(i + 1) / max(math.sqrt(len(orphans)), 1)
        layout[nid] = [math.cos(angle) * r, math.sin(angle) * r]

    (mnemo_path(repo_root) / "layout.json").write_text(json.dumps(layout))
