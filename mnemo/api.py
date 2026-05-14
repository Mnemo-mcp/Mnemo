"""Minimal REST API for Mnemo using built-in http.server."""

from __future__ import annotations

import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

_repo_root: Path = Path(".")


class _Handler(BaseHTTPRequestHandler):
    def _json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def _body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length)) if length else {}

    def do_GET(self):
        if self.path == "/health":
            from .health import system_health
            self._json(system_health(_repo_root))
        elif self.path == "/plan/status":
            from .plan import get_status
            self._json({"status": get_status(_repo_root)})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        body = self._body()
        if self.path == "/recall":
            from .memory import recall
            self._json({"result": recall(_repo_root)})
        elif self.path == "/remember":
            from .memory import add_memory
            entry = add_memory(_repo_root, body.get("content", ""), body.get("category", "general"))
            self._json({"id": entry.get("id")})
        elif self.path == "/search":
            from .memory import search_memory
            self._json({"result": search_memory(_repo_root, body.get("query", ""))})
        else:
            self._json({"error": "not found"}, 404)

    def log_message(self, format, *args):
        pass  # suppress logs


def start_api(repo_root: Path, port: int = 7891):
    """Start the Mnemo REST API server."""
    global _repo_root
    _repo_root = repo_root
    server = HTTPServer(("127.0.0.1", port), _Handler)
    print(f"Mnemo API listening on http://127.0.0.1:{port}")
    server.serve_forever()
