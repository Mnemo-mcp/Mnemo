"""Mnemo v2 API server — HTTP endpoints for the UI dashboard."""

from __future__ import annotations

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from typing import Any


class MnemoAPIHandler(BaseHTTPRequestHandler):
    """HTTP handler for Mnemo API endpoints."""

    repo_root: Path = Path(".")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        routes = {
            "/api/stats": self._stats,
            "/api/graph": self._graph,
            "/api/search": self._search,
            "/api/communities": self._communities,
            "/api/symbol": self._symbol,
            "/api/memory": self._memory,
            "/api/tasks": self._tasks,
            "/api/overview": self._overview,
            "/api/health": self._health,
            "/api/status": self._status,
            "/api/links": self._links,
            "/api/apis": self._apis,
            "/api/team": self._team,
            "/api/incidents": self._incidents,
            "/api/knowledge": self._knowledge,
            "/api/lessons": self._lessons,
            "/api/observations": self._observations,
            "/api/metrics": self._metrics,
            "/api/token_savings": self._token_savings,
            "/api/errors": self._errors,
        }

        handler = routes.get(path)
        if handler:
            try:
                result = handler(params)
                self._json_response(200, result)
            except Exception as e:
                self._json_response(500, {"error": str(e)})
        elif path == "/" or path.startswith("/assets") or path.endswith(".html"):
            self._serve_static(path)
        else:
            self._json_response(404, {"error": "Not found"})

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors_headers()
        self.end_headers()

    def _json_response(self, code: int, data: Any):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self._cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _serve_static(self, path: str):
        if path == "/":
            path = "/index.html"
        static_dir = Path(__file__).parent / "ui_static"
        file_path = static_dir / path.lstrip("/")
        if file_path.exists() and file_path.is_file():
            content = file_path.read_bytes()
            self.send_response(200)
            ct = "text/html"
            if path.endswith(".js"):
                ct = "application/javascript"
            elif path.endswith(".css"):
                ct = "text/css"
            self.send_header("Content-Type", ct)
            self.end_headers()
            self.wfile.write(content)
        else:
            # SPA fallback — serve index.html
            index = static_dir / "index.html"
            if index.exists():
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(index.read_bytes())
            else:
                self._json_response(404, {"error": "UI not found"})

    def _get_conn(self):
        from .engine.db import open_db, get_db_path
        if not get_db_path(self.repo_root).exists():
            raise RuntimeError("No graph database. Run mnemo init first.")
        _, conn = open_db(self.repo_root)
        return conn

    def _stats(self, params: dict) -> dict:
        conn = self._get_conn()
        r = conn.execute("MATCH (n) RETURN count(n)")
        nodes = r.get_next()[0]
        r = conn.execute("MATCH ()-[e]->() RETURN count(e)")
        edges = r.get_next()[0]
        r = conn.execute("MATCH (c:Community) RETURN count(c)")
        communities = r.get_next()[0]
        r = conn.execute("MATCH (f:File) RETURN count(f)")
        files = r.get_next()[0]
        r = conn.execute("MATCH (c:Class) RETURN count(c)")
        classes = r.get_next()[0]
        r = conn.execute("MATCH (f:Function) RETURN count(f)")
        functions = r.get_next()[0]
        return {"nodes": nodes, "edges": edges, "communities": communities, "files": files, "classes": classes, "functions": functions}

    def _graph(self, params: dict) -> dict:
        """Return the FULL graph — every node, every edge."""
        conn = self._get_conn()

        nodes = []
        edges = []
        node_ids = set()

        # Projects
        r = conn.execute("MATCH (p:Project) RETURN p.id, p.name")
        while r.has_next():
            row = r.get_next()
            nodes.append({"id": row[0], "name": row[1], "type": "project"})
            node_ids.add(row[0])

        # Files
        r = conn.execute("MATCH (f:File) RETURN f.path, f.language")
        while r.has_next():
            row = r.get_next()
            nodes.append({"id": row[0], "name": row[0].split("/")[-1], "type": "file"})
            node_ids.add(row[0])

        # Project → File edges
        r = conn.execute("MATCH (p:Project)-[:PROJECT_CONTAINS]->(f:File) RETURN p.id, f.path")
        while r.has_next():
            row = r.get_next()
            edges.append({"source": row[0], "target": row[1]})

        # ALL classes
        r = conn.execute("MATCH (c:Class) RETURN c.id, c.name, c.file")
        while r.has_next():
            row = r.get_next()
            nodes.append({"id": row[0], "name": row[1], "type": "class"})
            node_ids.add(row[0])
            # Connect class to its file
            if row[2] in node_ids:
                edges.append({"source": row[2], "target": row[0]})

        # ALL functions
        r = conn.execute("MATCH (f:Function) RETURN f.id, f.name, f.file")
        while r.has_next():
            row = r.get_next()
            nodes.append({"id": row[0], "name": row[1], "type": "function"})
            node_ids.add(row[0])
            if row[2] in node_ids:
                edges.append({"source": row[2], "target": row[0]})

        # ALL CALLS edges
        r = conn.execute("MATCH (a:Function)-[:CALLS]->(b:Function) RETURN a.id, b.id")
        while r.has_next():
            row = r.get_next()
            if row[0] in node_ids and row[1] in node_ids:
                edges.append({"source": row[0], "target": row[1]})

        # Project → Class edges (through files)
        r = conn.execute("MATCH (p:Project)-[:PROJECT_CONTAINS]->(f:File)<-[]-(c:Class) RETURN p.id, c.id")
        while r.has_next():
            row = r.get_next()
            if row[0] in node_ids and row[1] in node_ids:
                edges.append({"source": row[0], "target": row[1]})

        # HAS_METHOD edges (class → method)
        r = conn.execute("MATCH (c:Class)-[:HAS_METHOD]->(m:Method) RETURN c.id, m.id, m.name")
        while r.has_next():
            row = r.get_next()
            if row[0] in node_ids:
                nodes.append({"id": row[1], "name": row[2], "type": "method"})
                node_ids.add(row[1])
                edges.append({"source": row[0], "target": row[1]})

        # IMPORTS edges
        r = conn.execute("MATCH (a:File)-[:IMPORTS]->(b:File) RETURN a.path, b.path")
        while r.has_next():
            row = r.get_next()
            if row[0] in node_ids and row[1] in node_ids:
                edges.append({"source": row[0], "target": row[1]})

        # ALL communities
        r = conn.execute("MATCH (comm:Community) RETURN comm.id, comm.name")
        while r.has_next():
            row = r.get_next()
            nodes.append({"id": row[0], "name": row[1], "type": "community"})
            node_ids.add(row[0])

        # Community membership
        r = conn.execute("MATCH (c:Class)-[:MEMBER_OF]->(comm:Community) RETURN c.id, comm.id")
        while r.has_next():
            row = r.get_next()
            if row[0] in node_ids and row[1] in node_ids:
                edges.append({"source": row[1], "target": row[0]})

        r = conn.execute("MATCH (f:Function)-[:FN_MEMBER_OF]->(comm:Community) RETURN f.id, comm.id")
        while r.has_next():
            row = r.get_next()
            if row[0] in node_ids and row[1] in node_ids:
                edges.append({"source": row[1], "target": row[0]})

        # Memories
        r = conn.execute("MATCH (m:Memory) RETURN m.id, m.content, m.category")
        while r.has_next():
            row = r.get_next()
            label = row[1][:30] + "..." if len(row[1]) > 30 else row[1]
            nodes.append({"id": row[0], "name": label, "type": "memory"})
            node_ids.add(row[0])

        # Decisions
        r = conn.execute("MATCH (d:Decision) RETURN d.id, d.decision")
        while r.has_next():
            row = r.get_next()
            label = row[1][:30] + "..." if len(row[1]) > 30 else row[1]
            nodes.append({"id": row[0], "name": label, "type": "decision"})
            node_ids.add(row[0])

        return {"nodes": nodes, "edges": edges}

    def _search(self, params: dict) -> dict:
        conn = self._get_conn()
        query = params.get("q", [""])[0]
        if not query:
            return {"results": []}
        results = []
        r = conn.execute(f"MATCH (c:Class) WHERE c.name CONTAINS '{query}' RETURN c.id, c.name, c.file, 'class' LIMIT 20")
        while r.has_next():
            row = r.get_next()
            results.append({"id": row[0], "name": row[1], "file": row[2], "type": row[3]})
        r = conn.execute(f"MATCH (f:Function) WHERE f.name CONTAINS '{query}' RETURN f.id, f.name, f.file, 'function' LIMIT 20")
        while r.has_next():
            row = r.get_next()
            results.append({"id": row[0], "name": row[1], "file": row[2], "type": row[3]})
        return {"results": results}

    def _communities(self, params: dict) -> dict:
        conn = self._get_conn()
        r = conn.execute("MATCH (c:Class)-[:MEMBER_OF]->(comm:Community) RETURN comm.id, comm.name, count(c) AS cnt ORDER BY cnt DESC LIMIT 30")
        communities = []
        while r.has_next():
            row = r.get_next()
            communities.append({"id": row[0], "name": row[1], "count": row[2]})
        return {"communities": communities}

    def _symbol(self, params: dict) -> dict:
        conn = self._get_conn()
        name = params.get("name", [""])[0]
        if not name:
            return {"error": "name parameter required"}

        result: dict[str, Any] = {"name": name}

        r = conn.execute(f"MATCH (c:Class {{name: '{name}'}}) RETURN c.id, c.file, c.implements")
        if r.has_next():
            row = r.get_next()
            result.update({"type": "class", "id": row[0], "file": row[1], "implements": row[2]})

            # Methods
            r2 = conn.execute(f"MATCH (c:Class {{name: '{name}'}})-[:HAS_METHOD]->(m:Method) RETURN m.name, m.signature")
            methods = []
            while r2.has_next():
                mrow = r2.get_next()
                methods.append({"name": mrow[0], "signature": mrow[1]})
            result["methods"] = methods

        return result

    def _memory(self, params: dict) -> dict:
        from .storage import get_storage, Collections
        storage = get_storage(self.repo_root)
        memories = storage.read_collection(Collections.MEMORY) or []
        decisions = storage.read_collection(Collections.DECISIONS) or []
        return {"memories": memories, "decisions": decisions}

    def _tasks(self, params: dict) -> dict:
        from .storage import get_storage, Collections
        storage = get_storage(self.repo_root)
        tasks = storage.read_collection(Collections.TASKS) or []
        return {"tasks": tasks}

    def _overview(self, params: dict) -> dict:
        stats = self._stats(params)
        mem = self._memory(params)
        return {
            **stats,
            "memory_count": len(mem["memories"]),
            "decision_count": len(mem["decisions"]),
        }

    def _health(self, params: dict) -> dict:
        from .config import mnemo_path
        base = mnemo_path(self.repo_root)
        checks = {"initialized": base.exists(), "graph_db": False, "memory": False}
        try:
            self._get_conn()
            checks["graph_db"] = True
        except Exception:
            pass
        mem_file = base / "memory.json"
        checks["memory"] = mem_file.exists()
        return {"status": "healthy" if all(checks.values()) else "degraded", "checks": checks}

    def _status(self, params: dict) -> dict:
        stats = self._stats(params)
        health = self._health(params)
        mem = self._memory(params)
        return {**stats, **health, "memory_count": len(mem.get("memories", [])), "decision_count": len(mem.get("decisions", []))}

    def _links(self, params: dict) -> dict:
        from .config import mnemo_path
        links_file = mnemo_path(self.repo_root) / "links.json"
        if links_file.exists():
            return json.loads(links_file.read_text())
        return {"repos": []}

    def _apis(self, params: dict) -> dict:
        from .config import mnemo_path
        api_file = mnemo_path(self.repo_root) / "apis.json"
        if api_file.exists():
            return json.loads(api_file.read_text())
        return {"markdown": "No APIs discovered yet. Run `mnemo_audit` with report=full to scan."}

    def _team(self, params: dict) -> dict:
        from .config import mnemo_path
        team_file = mnemo_path(self.repo_root) / "team.json"
        if team_file.exists():
            return json.loads(team_file.read_text())
        return {"members": [], "markdown": "No team data. Use `mnemo_record type=review` to build team history."}

    def _incidents(self, params: dict) -> dict:
        from .storage import get_storage, Collections
        storage = get_storage(self.repo_root)
        data = storage.read_collection(Collections.INCIDENTS) or []
        return {"incidents": data}

    def _knowledge(self, params: dict) -> dict:
        from .config import mnemo_path
        kb_dir = mnemo_path(self.repo_root) / "knowledge"
        entries = []
        if kb_dir.exists():
            for f in kb_dir.glob("*.json"):
                try:
                    entries.append(json.loads(f.read_text()))
                except Exception:
                    pass
        return {"entries": entries}

    def _lessons(self, params: dict) -> dict:
        from .config import mnemo_path
        obs_file = mnemo_path(self.repo_root) / "observations.json"
        if obs_file.exists():
            try:
                data = json.loads(obs_file.read_text())
                lessons = [o for o in data if o.get("type") == "lesson"]
                return {"lessons": lessons}
            except Exception:
                pass
        return {"lessons": []}

    def _observations(self, params: dict) -> dict:
        from .config import mnemo_path
        obs_file = mnemo_path(self.repo_root) / "observations.json"
        if obs_file.exists():
            try:
                data = json.loads(obs_file.read_text())
                return {"observations": data[-50:]}  # last 50
            except Exception:
                pass
        return {"observations": []}

    def _metrics(self, params: dict) -> dict:
        mem = self._memory(params)
        mems = mem.get("memories", [])
        decs = mem.get("decisions", [])
        return {
            "total_memories": len(mems),
            "active_memories": len([m for m in mems if not m.get("evicted") and not m.get("superseded_by")]),
            "evicted": len([m for m in mems if m.get("evicted")]),
            "superseded": len([m for m in mems if m.get("superseded_by")]),
            "decisions": len(decs),
            "active_decisions": len([d for d in decs if d.get("active", True)]),
        }

    def _token_savings(self, params: dict) -> dict:
        mem = self._memory(params)
        total_mems = len(mem.get("memories", []))
        # Estimate: without mnemo, user would paste ~500 tokens per memory every session
        # With mnemo: ~2000 tokens total recall regardless of memory count
        naive_cost = total_mems * 500
        mnemo_cost = min(2000, total_mems * 100)
        return {"naive_tokens": naive_cost, "mnemo_tokens": mnemo_cost, "savings_pct": int((1 - mnemo_cost / max(naive_cost, 1)) * 100)}

    def _errors(self, params: dict) -> dict:
        from .storage import get_storage, Collections
        storage = get_storage(self.repo_root)
        data = storage.read_collection(Collections.ERRORS) or []
        return {"errors": data}

    def log_message(self, format, *args):
        pass  # Suppress request logging


def serve(repo_root: Path, port: int = 3333):
    """Start the Mnemo API server."""
    MnemoAPIHandler.repo_root = repo_root
    server = HTTPServer(("127.0.0.1", port), MnemoAPIHandler)
    print(f"🚀 Mnemo UI: http://localhost:{port}")
    print(f"   API: http://localhost:{port}/api/stats")
    print(f"   Repo: {repo_root}")
    print("   Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.shutdown()
