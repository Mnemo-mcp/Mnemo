"""Mnemo Dashboard UI — local web server for visualizing Mnemo data."""

from __future__ import annotations

import json
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from ..utils.logger import get_logger

logger = get_logger("ui")

from ..config import mnemo_path
from ..storage import Collections, get_storage

TEMPLATE_DIR = Path(__file__).parent / "templates"


def _read_json(repo_root: Path, filename: str) -> Any:
    path = mnemo_path(repo_root) / filename
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _get_overview(repo_root: Path) -> dict:
    memory = _read_json(repo_root, "memory.json")
    decisions = _read_json(repo_root, "decisions.json")
    links = _read_json(repo_root, "links.json")
    tasks = _read_json(repo_root, "tasks.json")
    context = _read_json(repo_root, "context.json")

    # Graph stats
    graph_meta_path = mnemo_path(repo_root) / "graph_meta.json"
    graph_stats = {"nodes": 0, "edges": 0}
    if graph_meta_path.exists():
        try:
            graph_stats = json.loads(graph_meta_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass

    # Build recent activity from memories + tasks
    activity = []
    for m in sorted(memory, key=lambda x: x.get("timestamp", 0), reverse=True)[:10]:
        activity.append({
            "type": "memory",
            "category": m.get("category", "general"),
            "content": m.get("content", "")[:120],
            "timestamp": m.get("timestamp", 0),
        })
    for t in tasks:
        activity.append({
            "type": "task",
            "content": f"[{t.get('task_id', '')}] {t.get('description', '')}",
            "status": t.get("status", ""),
            "timestamp": t.get("created", 0),
        })

    activity.sort(key=lambda x: x.get("timestamp", 0), reverse=True)

    return {
        "repo_name": repo_root.name,
        "repo_path": str(repo_root),
        "memory_count": len(memory),
        "decisions_count": len(decisions),
        "links_count": len(links),
        "tasks_count": len(tasks),
        "graph_nodes": graph_stats.get("nodes", 0),
        "graph_edges": graph_stats.get("edges", 0),
        "context": context if isinstance(context, dict) else {},
        "activity": activity[:15],
    }


def _get_graph(repo_root: Path) -> dict:
    graph_path = mnemo_path(repo_root) / "graph.json"
    if not graph_path.exists():
        return {"nodes": [], "edges": []}
    try:
        data = json.loads(graph_path.read_text(encoding="utf-8"))
        nodes = []
        for node in data.get("nodes", []):
            nodes.append({
                "id": node.get("id", ""),
                "type": node.get("type", "unknown"),
                "name": node.get("name", node.get("id", "")),
            })
        edges = []
        # NetworkX uses "edges" key; older versions use "links"
        raw_edges = data.get("edges", []) or data.get("links", [])
        for link in raw_edges:
            edges.append({
                "source": link.get("source", ""),
                "target": link.get("target", ""),
                "type": link.get("type", ""),
            })
        return {"nodes": nodes, "edges": edges}
    except (json.JSONDecodeError, OSError):
        return {"nodes": [], "edges": []}


def _get_memory(repo_root: Path) -> dict:
    memory = _read_json(repo_root, "memory.json")
    decisions = _read_json(repo_root, "decisions.json")
    return {"memories": memory, "decisions": decisions}


def _get_links(repo_root: Path) -> list:
    links = _read_json(repo_root, "links.json")
    result = []
    for link in links:
        path = Path(link.get("path", ""))
        has_mnemo = (path / ".mnemo").exists() if path.exists() else False
        result.append({
            "name": link.get("name", ""),
            "path": str(path),
            "exists": path.exists(),
            "indexed": has_mnemo,
        })
    return result


def _get_health(repo_root: Path) -> str:
    try:
        from ..health import calculate_health
        return calculate_health(repo_root)
    except Exception:
        return "Health data unavailable."


def _get_apis(repo_root: Path) -> str:
    try:
        from ..api_discovery import discover_apis
        return discover_apis(repo_root)
    except Exception:
        return "No APIs discovered."


def _get_incidents(repo_root: Path) -> list:
    storage = get_storage(repo_root)
    data = storage.read_collection(Collections.INCIDENTS)
    return data if isinstance(data, list) else []


def _get_errors(repo_root: Path) -> list:
    storage = get_storage(repo_root)
    data = storage.read_collection(Collections.ERRORS)
    return data if isinstance(data, list) else []


def _get_tasks(repo_root: Path) -> list:
    return _read_json(repo_root, "tasks.json")


def _get_map(repo_root: Path) -> str:
    summary_path = mnemo_path(repo_root) / "summary.md"
    if summary_path.exists():
        return summary_path.read_text(encoding="utf-8")
    return "No repo map found. Run `mnemo map`."


def _get_team(repo_root: Path) -> str:
    try:
        from ..team_graph import get_experts
        return get_experts(repo_root)
    except Exception:
        return "Team data unavailable."


def _get_status_flags(repo_root: Path) -> dict:
    """Return feature flags for the dashboard banners."""
    chroma_available = False
    try:
        from ..vector_index import LocalVectorIndex
        vi = LocalVectorIndex(repo_root)
        chroma_available = vi.available()
    except Exception:
        chroma_available = False
    links = _read_json(repo_root, "links.json")
    return {"chromadb_available": chroma_available, "has_linked_repos": len(links) > 0}


def _get_token_savings(repo_root: Path) -> dict:
    """Estimate token savings from memory recall budget."""
    memory = _read_json(repo_root, "memory.json")
    total_chars = sum(len(m.get("content", "")) for m in memory)
    # Recall budget is typically ~4000 chars returned
    recall_budget = 4000
    saved = max(0, total_chars - recall_budget) if memory else 0
    return {"total_chars": total_chars, "recall_budget": recall_budget, "saved_per_recall": saved}


def _get_knowledge(repo_root: Path) -> list:
    knowledge_dir = mnemo_path(repo_root) / "knowledge"
    if not knowledge_dir.exists():
        return []
    files = []
    for f in sorted(knowledge_dir.glob("*.md")):
        content = f.read_text(encoding="utf-8", errors="replace")
        files.append({"name": f.name, "content": content[:2000]})
    return files


def create_handler(repo_root: Path):
    """Create a request handler class bound to a specific repo root."""

    class MnemoHandler(SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            pass  # Suppress default logging

        def _send_json(self, data: Any):
            body = json.dumps(data, default=str).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self, content: str):
            body = content.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urlparse(self.path).path

            if path == "/" or path == "":
                html = (TEMPLATE_DIR / "dashboard.html").read_text(encoding="utf-8")
                self._send_html(html)
            elif path == "/api/overview":
                self._send_json(_get_overview(repo_root))
            elif path == "/api/graph":
                self._send_json(_get_graph(repo_root))
            elif path == "/api/memory":
                self._send_json(_get_memory(repo_root))
            elif path == "/api/links":
                self._send_json(_get_links(repo_root))
            elif path == "/api/health":
                self._send_json({"markdown": _get_health(repo_root)})
            elif path == "/api/apis":
                self._send_json({"markdown": _get_apis(repo_root)})
            elif path == "/api/incidents":
                self._send_json(_get_incidents(repo_root))
            elif path == "/api/errors":
                self._send_json(_get_errors(repo_root))
            elif path == "/api/tasks":
                self._send_json(_get_tasks(repo_root))
            elif path == "/api/map":
                self._send_json({"markdown": _get_map(repo_root)})
            elif path == "/api/team":
                self._send_json({"markdown": _get_team(repo_root)})
            elif path == "/api/knowledge":
                self._send_json(_get_knowledge(repo_root))
            elif path == "/api/status":
                self._send_json(_get_status_flags(repo_root))
            elif path == "/api/token_savings":
                self._send_json(_get_token_savings(repo_root))
            elif path == "/api/lessons":
                self._send_json(_read_json(repo_root, "lessons.json"))
            elif path == "/api/observations":
                self._send_json(_read_json(repo_root, "observations.json")[-50:])
            elif path == "/api/slots":
                self._send_json(_read_json(repo_root, "slots.json"))
            elif path == "/api/plans":
                self._send_json(_read_json(repo_root, "plans.json"))
            elif path == "/api/audit":
                self._send_json(_read_json(repo_root, "audit.json")[-50:])
            elif path == "/api/metrics":
                try:
                    from ..utils.metrics import get_metrics
                    self._send_json(get_metrics())
                except Exception:
                    self._send_json({})
            else:
                self.send_error(404)

    return MnemoHandler


def start_server(repo_root: Path, port: int = 7890, open_browser: bool = True):
    """Start the Mnemo dashboard server."""
    handler = create_handler(repo_root)
    server = HTTPServer(("127.0.0.1", port), handler)
    url = f"http://localhost:{port}"
    logger.info(f"🧠 Mnemo Dashboard running at {url}")
    logger.info(f"   Repo: {repo_root}")
    logger.info("   Press Ctrl+C to stop")

    if open_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Dashboard stopped.")
        server.shutdown()
