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

    def _stats(self, params) -> dict:
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

    def _graph(self, params) -> dict:
        """Return graph data for visualization (nodes + edges, limited)."""
        conn = self._get_conn()
        limit = int(params.get("limit", ["200"])[0])

        nodes = []
        # Get classes
        r = conn.execute(f"MATCH (c:Class) RETURN c.id, c.name, c.file LIMIT {limit}")
        while r.has_next():
            row = r.get_next()
            nodes.append({"id": row[0], "name": row[1], "type": "class", "file": row[2]})

        # Get functions
        r = conn.execute(f"MATCH (f:Function) RETURN f.id, f.name, f.file LIMIT {limit // 2}")
        while r.has_next():
            row = r.get_next()
            nodes.append({"id": row[0], "name": row[1], "type": "function", "file": row[2]})

        # Get edges
        edges = []
        node_ids = {n["id"] for n in nodes}

        r = conn.execute("MATCH (a:Function)-[c:CALLS]->(b:Function) RETURN a.id, b.id, c.confidence")
        while r.has_next():
            row = r.get_next()
            if row[0] in node_ids and row[1] in node_ids:
                edges.append({"source": row[0], "target": row[1], "type": "CALLS", "confidence": row[2]})

        r = conn.execute("MATCH (f:File)-[:FILE_DEFINES_CLASS]->(c:Class) RETURN f.path, c.id")
        while r.has_next():
            row = r.get_next()
            if row[1] in node_ids:
                edges.append({"source": row[0], "target": row[1], "type": "DEFINES"})

        r = conn.execute("MATCH (c:Class)-[:HAS_METHOD]->(m:Method) RETURN c.id, m.id LIMIT 100")
        while r.has_next():
            row = r.get_next()
            if row[0] in node_ids:
                edges.append({"source": row[0], "target": row[1], "type": "HAS_METHOD"})

        return {"nodes": nodes, "edges": edges}

    def _search(self, params) -> dict:
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

    def _communities(self, params) -> dict:
        conn = self._get_conn()
        r = conn.execute("MATCH (c:Class)-[:MEMBER_OF]->(comm:Community) RETURN comm.id, comm.name, count(c) AS cnt ORDER BY cnt DESC LIMIT 30")
        communities = []
        while r.has_next():
            row = r.get_next()
            communities.append({"id": row[0], "name": row[1], "count": row[2]})
        return {"communities": communities}

    def _symbol(self, params) -> dict:
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
