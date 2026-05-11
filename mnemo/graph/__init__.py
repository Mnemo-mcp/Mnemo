"""Knowledge Graph — schema, protocol, and graph store implementations."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass
class Node:
    """A node in the knowledge graph."""
    id: str                     # e.g. "class:AetnaHandler", "service:isAuthRequiredService"
    type: str                   # service, class, interface, method, file, package, decision, memory, incident, error, person, endpoint, pattern
    name: str                   # human-readable
    properties: dict[str, Any] = field(default_factory=dict)


@dataclass
class Edge:
    """A directed edge in the knowledge graph."""
    source: str                 # node id
    target: str                 # node id
    type: str                   # contains, defines, implements, inherits, calls, depends_on, affects, references, owns, occurs_in, touches
    properties: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class GraphStore(Protocol):
    """Unified interface for graph operations — local, workspace, or org."""

    def get_node(self, id: str) -> Node | None: ...
    def get_neighbors(self, id: str, edge_type: str | None = None, direction: str = "both") -> list[tuple[Edge, Node]]: ...
    def traverse(self, start: str, depth: int = 2, edge_types: list[str] | None = None, direction: str = "both") -> dict[str, Node]: ...
    def find_nodes(self, type: str | None = None, name_pattern: str | None = None) -> list[Node]: ...
    def upsert_node(self, node: Node) -> None: ...
    def upsert_edge(self, edge: Edge) -> None: ...
    def remove_node(self, id: str) -> None: ...
    def remove_edges(self, source: str | None = None, target: str | None = None, edge_type: str | None = None) -> int: ...
    def stats(self) -> dict[str, int]: ...
    def save(self) -> None: ...
    def load(self) -> None: ...


# Re-export implementations
from .local import LocalGraph
from .workspace import WorkspaceGraph
