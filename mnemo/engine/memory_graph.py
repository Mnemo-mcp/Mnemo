"""Memory-Graph integration — stores memories in LadybugDB and enables graph-boosted search.

Key features:
- Memories stored as nodes in the same graph as code symbols
- Auto-linking: detect symbol names in memory content, create REFERENCES edges
- Graph-boosted search: Dijkstra shortest path from query symbols to find related memories
"""

from __future__ import annotations

import heapq
import time
from pathlib import Path
from typing import Any


def store_memory_in_graph(repo_root: Path, memory_id: int, content: str, category: str) -> int:
    """Store a memory as a node in LadybugDB and auto-link to code symbols.
    Returns number of links created."""
    from .db import open_db, get_db_path
    if not get_db_path(repo_root).exists():
        return 0

    _, conn = open_db(repo_root)
    node_id = f"mem:{memory_id}"
    ts = time.time()

    # Insert memory node
    try:
        conn.execute(
            f"CREATE (:Memory {{id: '{node_id}', content: '{_escape(content[:500])}', "
            f"category: '{category}', tier: 'hot', timestamp: {ts}}})"
        )
    except RuntimeError:
        # Already exists — update
        try:
            conn.execute(
                f"MATCH (m:Memory {{id: '{node_id}'}}) SET m.content = '{_escape(content[:500])}', "
                f"m.category = '{category}', m.timestamp = {ts}"
            )
        except RuntimeError:
            return 0

    # Auto-link to code symbols
    links = _auto_link(conn, node_id, content)
    return links


def store_decision_in_graph(repo_root: Path, decision_id: int, decision: str, reasoning: str) -> int:
    """Store a decision as a node in LadybugDB and auto-link to code symbols."""
    from .db import open_db, get_db_path
    if not get_db_path(repo_root).exists():
        return 0

    _, conn = open_db(repo_root)
    node_id = f"dec:{decision_id}"
    ts = time.time()

    try:
        conn.execute(
            f"CREATE (:Decision {{id: '{node_id}', decision: '{_escape(decision[:300])}', "
            f"reasoning: '{_escape(reasoning[:300])}', active: true, timestamp: {ts}}})"
        )
    except RuntimeError:
        return 0

    links = _auto_link_decision(conn, node_id, f"{decision} {reasoning}")
    return links


def _auto_link(conn, memory_id: str, content: str) -> int:
    """Detect code symbol names in memory content and create REFERENCES edges."""
    links = 0

    # Find class names mentioned in content
    r = conn.execute("MATCH (c:Class) RETURN c.id, c.name")
    while r.has_next():
        row = r.get_next()
        name = row[1]
        if len(name) >= 4 and name in content:
            try:
                conn.execute(
                    f"MATCH (m:Memory {{id: '{memory_id}'}}), (c:Class {{id: '{row[0]}'}}) "
                    f"CREATE (m)-[:MEM_REF_CLASS]->(c)"
                )
                links += 1
            except RuntimeError:
                pass

    # Find function names
    r = conn.execute("MATCH (f:Function) RETURN f.id, f.name")
    while r.has_next():
        row = r.get_next()
        name = row[1]
        if len(name) >= 4 and name in content:
            try:
                conn.execute(
                    f"MATCH (m:Memory {{id: '{memory_id}'}}), (f:Function {{id: '{row[0]}'}}) "
                    f"CREATE (m)-[:MEM_REF_FUNCTION]->(f)"
                )
                links += 1
            except RuntimeError:
                pass

    return links


def _auto_link_decision(conn, decision_id: str, content: str) -> int:
    """Auto-link decision to code symbols."""
    links = 0
    r = conn.execute("MATCH (c:Class) RETURN c.id, c.name")
    while r.has_next():
        row = r.get_next()
        if len(row[1]) >= 4 and row[1] in content:
            try:
                conn.execute(
                    f"MATCH (d:Decision {{id: '{decision_id}'}}), (c:Class {{id: '{row[0]}'}}) "
                    f"CREATE (d)-[:DEC_ABOUT_CLASS]->(c)"
                )
                links += 1
            except RuntimeError:
                pass
    return links


def graph_boosted_search(repo_root: Path, query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Search memories using graph-boosted Dijkstra traversal.

    Strategy:
    1. Find code symbols mentioned in the query
    2. From those symbols, run Dijkstra to find nearby Memory nodes
    3. Score by: (1/distance) * relevance
    4. Also do keyword match on memory content
    5. Merge results with RRF
    """
    from .db import open_db, get_db_path
    if not get_db_path(repo_root).exists():
        return []

    _, conn = open_db(repo_root)

    # Step 1: Keyword search on memory content
    keyword_results = _keyword_search(conn, query, limit)

    # Step 2: Find symbols mentioned in query
    query_symbols = _find_symbols_in_text(conn, query)

    # Step 3: Dijkstra from query symbols to find connected memories
    graph_results = []
    if query_symbols:
        graph_results = _dijkstra_to_memories(conn, query_symbols, limit)

    # Step 4: RRF fusion
    return _rrf_merge(keyword_results, graph_results, limit)


def _keyword_search(conn, query: str, limit: int) -> list[dict[str, Any]]:
    """Simple keyword search on memory content."""
    results = []
    # Search memories containing query terms
    terms = [t for t in query.split() if len(t) >= 3]
    if not terms:
        return results

    for term in terms[:3]:  # Limit to 3 terms
        r = conn.execute(
            f"MATCH (m:Memory) WHERE m.content CONTAINS '{_escape(term)}' "
            f"RETURN m.id, m.content, m.category, m.timestamp LIMIT {limit}"
        )
        while r.has_next():
            row = r.get_next()
            results.append({
                "id": row[0], "content": row[1], "category": row[2],
                "timestamp": row[3], "source": "keyword",
            })

    # Deduplicate by id
    seen = set()
    unique = []
    for r in results:
        if r["id"] not in seen:
            seen.add(r["id"])
            unique.append(r)
    return unique[:limit]


def _find_symbols_in_text(conn, text: str) -> list[str]:
    """Find code symbol IDs mentioned in text."""
    symbols = []
    r = conn.execute("MATCH (c:Class) RETURN c.id, c.name")
    while r.has_next():
        row = r.get_next()
        if len(row[1]) >= 4 and row[1] in text:
            symbols.append(row[0])

    r = conn.execute("MATCH (f:Function) RETURN f.id, f.name")
    while r.has_next():
        row = r.get_next()
        if len(row[1]) >= 4 and row[1] in text:
            symbols.append(row[0])

    return symbols


def _dijkstra_to_memories(conn, start_symbols: list[str], limit: int) -> list[dict[str, Any]]:
    """Dijkstra shortest path from code symbols to Memory nodes.

    Edge weights:
    - MEM_REF_CLASS/FUNCTION: 1.0 (direct reference)
    - HAS_METHOD: 2.0 (class → method)
    - CALLS: 3.0 (function → function)
    - FILE_DEFINES_*: 2.0 (file → symbol)
    - MEMBER_OF: 4.0 (community membership)
    """
    # Build adjacency from the graph
    # Priority queue: (distance, node_id)
    dist: dict[str, float] = {}
    pq: list[tuple[float, str]] = []

    for sym in start_symbols:
        dist[sym] = 0.0
        heapq.heappush(pq, (0.0, sym))

    visited = set()
    found_memories: list[tuple[float, str]] = []
    max_dist = 10.0  # Don't traverse too far

    while pq and len(found_memories) < limit:
        d, node = heapq.heappop(pq)
        if node in visited:
            continue
        visited.add(node)

        if d > max_dist:
            break

        # Check if this is a memory node
        if node.startswith("mem:"):
            found_memories.append((d, node))
            continue

        # Expand neighbors
        neighbors = _get_neighbors(conn, node)
        for neighbor_id, weight in neighbors:
            new_dist = d + weight
            if neighbor_id not in dist or new_dist < dist[neighbor_id]:
                dist[neighbor_id] = new_dist
                heapq.heappush(pq, (new_dist, neighbor_id))

    # Fetch memory content for found nodes
    results = []
    for distance, mem_id in found_memories:
        r = conn.execute(f"MATCH (m:Memory {{id: '{mem_id}'}}) RETURN m.content, m.category, m.timestamp")
        if r.has_next():
            row = r.get_next()
            results.append({
                "id": mem_id, "content": row[0], "category": row[1],
                "timestamp": row[2], "source": "graph",
                "distance": distance,
            })

    return results


def _get_neighbors(conn, node_id: str) -> list[tuple[str, float]]:
    """Get neighbors of a node with edge weights for Dijkstra."""
    neighbors = []

    # Memory references (weight 1.0 — direct link)
    r = conn.execute(f"MATCH (m:Memory)-[:MEM_REF_CLASS]->(n {{id: '{node_id}'}}) RETURN m.id")
    while r.has_next():
        neighbors.append((r.get_next()[0], 1.0))

    r = conn.execute(f"MATCH (m:Memory)-[:MEM_REF_FUNCTION]->(n {{id: '{node_id}'}}) RETURN m.id")
    while r.has_next():
        neighbors.append((r.get_next()[0], 1.0))

    # Class → Method (weight 2.0)
    r = conn.execute(f"MATCH (c {{id: '{node_id}'}})-[:HAS_METHOD]->(m:Method) RETURN m.id")
    while r.has_next():
        neighbors.append((r.get_next()[0], 2.0))

    # Method → Class (reverse, weight 2.0)
    r = conn.execute(f"MATCH (c:Class)-[:HAS_METHOD]->(m {{id: '{node_id}'}}) RETURN c.id")
    while r.has_next():
        neighbors.append((r.get_next()[0], 2.0))

    # CALLS edges (weight 3.0)
    r = conn.execute(f"MATCH (a {{id: '{node_id}'}})-[:CALLS]->(b:Function) RETURN b.id")
    while r.has_next():
        neighbors.append((r.get_next()[0], 3.0))

    r = conn.execute(f"MATCH (a:Function)-[:CALLS]->(b {{id: '{node_id}'}}) RETURN a.id")
    while r.has_next():
        neighbors.append((r.get_next()[0], 3.0))

    return neighbors


def _rrf_merge(keyword_results: list[dict], graph_results: list[dict], limit: int) -> list[dict]:
    """Reciprocal Rank Fusion to merge keyword and graph results."""
    k = 60  # RRF constant
    scores: dict[str, float] = {}
    all_results: dict[str, dict] = {}

    for rank, r in enumerate(keyword_results):
        rid = r["id"]
        scores[rid] = scores.get(rid, 0) + 1.0 / (k + rank + 1)
        all_results[rid] = r

    for rank, r in enumerate(graph_results):
        rid = r["id"]
        # Graph results also get a distance-based boost
        distance_boost = 1.0 / (1.0 + r.get("distance", 5.0))
        scores[rid] = scores.get(rid, 0) + (1.0 / (k + rank + 1)) + distance_boost * 0.5
        all_results[rid] = r

    # Sort by score
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return [all_results[rid] for rid, _ in ranked[:limit]]


def _escape(s: str) -> str:
    """Escape string for Cypher."""
    return s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", " ").replace("\r", "")
