"""ADR-010: stub WorldFeed server — same contract as
src/robots.adapters.worldfeed_server (ADR-007), empty data.

Serves the four endpoints the Rust dashboard consumes so the stack stays
up when the Python package is not importable inside the container:

  GET  /feed/roster           {"agents": [...]}
  GET  /feed/agent/{id}       persona + runtime detail (404 when unknown)
  GET  /feed/events           SSE stream of feed items
  POST /commands              operator commands (accepted, no-op'd)

Stdlib only: no fastapi/uvicorn needed on the fallback path.
"""

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

PORT = 0  # filled from WORLDFEED_PORT by run_worldfeed.sh


def _sse_body() -> bytes:
    item = {
        "ts": 0,
        "kind": "session",
        "summary": "worldfeed stub: src/robots not importable in this image "
        "(graceful degradation, ADR-010)",
        "operator_forced": False,
    }
    return f"data: {json.dumps(item)}\n\n".encode()


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, ctype: str = "application/json") -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802 (http.server API)
        if self.path == "/feed/roster":
            self._send(200, json.dumps({"agents": []}).encode())
        elif self.path.startswith("/feed/agent/"):
            agent_id = self.path.rsplit("/", 1)[-1]
            body = {"error": f"unknown agent: {agent_id}"}
            self._send(404, json.dumps(body).encode())
        elif self.path == "/feed/events":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(_sse_body())
            self.close_connection = True
        else:
            self._send(404, b'{"error": "not found"}')

    def do_POST(self) -> None:  # noqa: N802 (http.server API)
        if self.path == "/commands":
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                cmd: Any = json.loads(raw.decode() or "{}")
            except json.JSONDecodeError:
                self._send(400, b'{"error": "invalid json"}')
                return
            body = {"accepted": False, "reason": "stub server: command recorded, not applied",
                    "received": cmd if isinstance(cmd, dict) else {}}
            self._send(200, json.dumps(body).encode())
        else:
            self._send(404, b'{"error": "not found"}')

    def log_message(self, fmt: str, *args: object) -> None:
        print("[worldfeed-stub]", fmt % args, flush=True)


def main() -> None:
    import os

    port = int(os.environ.get("WORLDFEED_PORT", "8400"))
    # 0.0.0.0 inside the container: rootless docker's rootlessport proxy
    # cannot reach a 127.0.0.1-bound service. The published host side stays
    # 127.0.0.1-bound (docker-compose.worlds.yml), so exposure is still
    # localhost-only from the host's perspective.
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"[worldfeed-stub] serving ADR-007 contract on 0.0.0.0:{port} "
          "(host-published on 127.0.0.1)", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
