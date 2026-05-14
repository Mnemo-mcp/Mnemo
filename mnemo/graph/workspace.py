"""WorkspaceGraph — federated knowledge graph across linked repos."""

from __future__ import annotations

from pathlib import Path

from . import Node
from .local import LocalGraph
from ..config import mnemo_path


class WorkspaceGraph:
    """Federated graph that queries local + all linked repos."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.local = LocalGraph(repo_root)
        self.linked: list[tuple[str, LocalGraph]] = []
        self._load_links()

    def _load_links(self) -> None:
        import json
        links_file = mnemo_path(self.repo_root) / "links.json"
        if not links_file.exists():
            return
        try:
            links = json.loads(links_file.read_text())
        except (json.JSONDecodeError, OSError):
            return
        for link_path in links:
            p = Path(link_path)
            if p.exists() and (p / ".mnemo" / "graph.json").exists():
                self.linked.append((p.name, LocalGraph(p)))

    def get_node(self, id: str) -> tuple[str, Node] | None:
        """Get node with repo source. Returns (repo_name, node)."""
        node = self.local.get_node(id)
        if node:
            return (self.repo_root.name, node)
        for name, graph in self.linked:
            node = graph.get_node(id)
            if node:
                return (name, node)
        return None

    def find_nodes(self, type: str | None = None, name_pattern: str | None = None) -> list[tuple[str, Node]]:
        """Find nodes across all repos. Returns (repo_name, node) pairs."""
        results = [(self.repo_root.name, n) for n in self.local.find_nodes(type=type, name_pattern=name_pattern)]
        for repo_name, graph in self.linked:
            results.extend([(repo_name, n) for n in graph.find_nodes(type=type, name_pattern=name_pattern)])
        return results

    def cross_impact(self, entity_name: str) -> str:
        """What breaks across ALL repos if this entity changes."""
        lines = [f"# Cross-Repo Impact: `{entity_name}`\n"]

        all_graphs = [(self.repo_root.name, self.local)] + self.linked

        for repo_name, graph in all_graphs:
            if not graph.exists():
                continue
            # Find matching nodes in this repo
            matches = graph.find_nodes(name_pattern=entity_name)
            if not matches:
                continue

            repo_impacts = []
            for node in matches:
                # Get everything that depends on this node (incoming edges)
                neighbors = graph.get_neighbors(node.id, direction="incoming")
                for edge, neighbor in neighbors:
                    if edge.type in ("calls", "implements", "inherits", "depends_on", "references"):
                        repo_impacts.append(f"- `{neighbor.name}` ({neighbor.type}) --{edge.type}--> `{node.name}`")

            if repo_impacts:
                lines.append(f"## {repo_name}")
                lines.extend(repo_impacts[:20])
                if len(repo_impacts) > 20:
                    lines.append(f"  ... +{len(repo_impacts) - 20} more")
                lines.append("")

        if len(lines) <= 2:
            return f"No cross-repo impact found for `{entity_name}`."
        return "\n".join(lines)

    def cross_search(self, query: str, type: str | None = None) -> str:
        """Search for entities across all repos."""
        results = self.find_nodes(type=type, name_pattern=query)
        if not results:
            return f"No nodes matching `{query}` across workspace."

        lines = [f"# Cross-Repo Search: `{query}`\n"]
        by_repo: dict[str, list[Node]] = {}
        for repo_name, node in results:
            by_repo.setdefault(repo_name, []).append(node)

        for repo_name, nodes in sorted(by_repo.items()):
            lines.append(f"## {repo_name}")
            for n in nodes[:15]:
                lines.append(f"- `{n.name}` ({n.type})")
            if len(nodes) > 15:
                lines.append(f"  ... +{len(nodes) - 15} more")
            lines.append("")

        return "\n".join(lines)

    def stats(self) -> str:
        """Combined stats across all repos."""
        lines = ["# Workspace Graph Stats\n"]
        all_graphs = [(self.repo_root.name, self.local)] + self.linked

        total_nodes = 0
        total_edges = 0
        for repo_name, graph in all_graphs:
            if not graph.exists():
                lines.append(f"- **{repo_name}**: no graph (run `mnemo map`)")
                continue
            s = graph.stats()
            total_nodes += s["nodes"]
            total_edges += s["edges"]
            lines.append(f"- **{repo_name}**: {s['nodes']} nodes, {s['edges']} edges")

        lines.insert(2, f"- **Total:** {total_nodes} nodes, {total_edges} edges\n")
        return "\n".join(lines)
