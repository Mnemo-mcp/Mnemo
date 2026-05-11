"""LocalGraph — single-repo knowledge graph backed by NetworkX."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import networkx as nx

from . import Node, Edge
from ..config import mnemo_path

GRAPH_FILE = "graph.json"
GRAPH_META_FILE = "graph_meta.json"


class LocalGraph:
    """Knowledge graph for a single repository."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self._graph: nx.MultiDiGraph = nx.MultiDiGraph()
        self._loaded = False

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.load()
            self._loaded = True

    @property
    def graph(self) -> nx.MultiDiGraph:
        self._ensure_loaded()
        return self._graph

    # --- Protocol implementation ---

    def get_node(self, id: str) -> Node | None:
        g = self.graph
        if id not in g:
            return None
        data = g.nodes[id]
        return Node(id=id, type=data.get("type", ""), name=data.get("name", ""), properties={k: v for k, v in data.items() if k not in ("type", "name")})

    def get_neighbors(self, id: str, edge_type: str | None = None, direction: str = "both") -> list[tuple[Edge, Node]]:
        g = self.graph
        if id not in g:
            return []
        results = []

        if direction in ("outgoing", "both"):
            for _, target, key, data in g.out_edges(id, keys=True, data=True):
                etype = data.get("type", "")
                if edge_type and etype != edge_type:
                    continue
                edge = Edge(source=id, target=target, type=etype, properties={k: v for k, v in data.items() if k != "type"})
                node = self.get_node(target)
                if node:
                    results.append((edge, node))

        if direction in ("incoming", "both"):
            for source, _, key, data in g.in_edges(id, keys=True, data=True):
                etype = data.get("type", "")
                if edge_type and etype != edge_type:
                    continue
                edge = Edge(source=source, target=id, type=etype, properties={k: v for k, v in data.items() if k != "type"})
                node = self.get_node(source)
                if node:
                    results.append((edge, node))

        return results

    def traverse(self, start: str, depth: int = 2, edge_types: list[str] | None = None, direction: str = "both") -> dict[str, Node]:
        g = self.graph
        if start not in g:
            return {}
        visited: dict[str, Node] = {}
        queue = [(start, 0)]

        while queue:
            current, d = queue.pop(0)
            if current in visited or d > depth:
                continue
            node = self.get_node(current)
            if not node:
                continue
            visited[current] = node

            if d < depth:
                neighbors = self.get_neighbors(current, direction=direction)
                for edge, neighbor in neighbors:
                    if edge_types and edge.type not in edge_types:
                        continue
                    if neighbor.id not in visited:
                        queue.append((neighbor.id, d + 1))

        return visited

    def find_nodes(self, type: str | None = None, name_pattern: str | None = None) -> list[Node]:
        g = self.graph
        results = []
        pattern_lower = name_pattern.lower() if name_pattern else None
        for nid, data in g.nodes(data=True):
            if type and data.get("type") != type:
                continue
            if pattern_lower and pattern_lower not in data.get("name", "").lower():
                continue
            results.append(Node(id=nid, type=data.get("type", ""), name=data.get("name", ""), properties={k: v for k, v in data.items() if k not in ("type", "name")}))
        return results

    def upsert_node(self, node: Node) -> None:
        self.graph.add_node(node.id, type=node.type, name=node.name, **node.properties)

    def upsert_edge(self, edge: Edge) -> None:
        self.graph.add_edge(edge.source, edge.target, type=edge.type, **edge.properties)

    def remove_node(self, id: str) -> None:
        g = self.graph
        if id in g:
            g.remove_node(id)

    def remove_edges(self, source: str | None = None, target: str | None = None, edge_type: str | None = None) -> int:
        g = self.graph
        to_remove = []
        for s, t, key, data in g.edges(keys=True, data=True):
            if source and s != source:
                continue
            if target and t != target:
                continue
            if edge_type and data.get("type") != edge_type:
                continue
            to_remove.append((s, t, key))
        for s, t, key in to_remove:
            g.remove_edge(s, t, key)
        return len(to_remove)

    def stats(self) -> dict[str, int]:
        g = self.graph
        node_types: dict[str, int] = {}
        for _, data in g.nodes(data=True):
            t = data.get("type", "unknown")
            node_types[t] = node_types.get(t, 0) + 1
        edge_types: dict[str, int] = {}
        for _, _, data in g.edges(data=True):
            t = data.get("type", "unknown")
            edge_types[t] = edge_types.get(t, 0) + 1
        return {"nodes": g.number_of_nodes(), "edges": g.number_of_edges(), "node_types": node_types, "edge_types": edge_types}

    def save(self) -> None:
        base = mnemo_path(self.repo_root)
        base.mkdir(parents=True, exist_ok=True)
        data = nx.node_link_data(self._graph)
        (base / GRAPH_FILE).write_text(json.dumps(data, default=str), encoding="utf-8")
        stats = self.stats()
        (base / GRAPH_META_FILE).write_text(json.dumps({"nodes": stats["nodes"], "edges": stats["edges"]}, default=str), encoding="utf-8")

    def load(self) -> None:
        path = mnemo_path(self.repo_root) / GRAPH_FILE
        if not path.exists():
            self._graph = nx.MultiDiGraph()
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            self._graph = nx.node_link_graph(data, directed=True, multigraph=True)
        except (json.JSONDecodeError, OSError, Exception) as exc:
            print(f"[mnemo] Failed to load graph: {exc}", file=sys.stderr)
            self._graph = nx.MultiDiGraph()

    def exists(self) -> bool:
        return (mnemo_path(self.repo_root) / GRAPH_FILE).exists()
