"""Inventory microservice - the evolving application.

Stdlib-only service exposing:
    GET  /health          -> {"status": "ok"}
    GET  /items/<id>      -> item record or 404
    POST /restock         -> apply restock deltas

Environment variables:
    CACHE_TTL       seconds an item cache entry stays fresh
    MAX_CONNECTIONS server connection cap
"""
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

CACHE_TTL = int(os.environ.get("CACHE_TTL", "30"))
MAX_CONNECTIONS = int(os.environ.get("MAX_CONNECTIONS", "8"))

CATALOG = {
    f"SKU-{i:04d}": {"name": f"widget-{i}", "qty": i % 17, "price": 2.5 + i % 7}
    for i in range(2000)
}


def find_item(sku):
    """Return the item record for sku, or None."""
    # BASELINE: linear scan over the catalog per lookup.
    for key, record in CATALOG.items():
        if key == sku:
            return dict(record)
    return None


def apply_restock(deltas):
    """deltas: {sku: qty_delta}. Returns {sku: new_qty} for applied keys."""
    applied = {}
    for sku, delta in deltas.items():
        if sku in CATALOG:
            CATALOG[sku]["qty"] += delta
            applied[sku] = CATALOG[sku]["qty"]
    return applied


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/health":
            self._json(200, {"status": "ok"})
        elif self.path.startswith("/items/"):
            sku = self.path.split("/items/", 1)[1]
            item = find_item(sku)
            self._json(200 if item else 404, item or {"error": "not found"})
        else:
            self._json(404, {"error": "unknown route"})

    def do_POST(self):
        if self.path == "/restock":
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length) or b"{}")
            self._json(200, apply_restock(body))
        else:
            self._json(404, {"error": "unknown route"})

    def _json(self, code, payload):
        data = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *a):
        pass


def main():
    server = HTTPServer(("0.0.0.0", 8080), Handler)
    server.request_queue_size = MAX_CONNECTIONS
    server.serve_forever()


if __name__ == "__main__":
    main()
