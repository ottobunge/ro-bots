"""Exercise the compiled dashboard against isolated loopback fixtures only."""
import json
import os
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

here = Path(__file__).resolve().parent
class Fixture(BaseHTTPRequestHandler):
    def log_message(self, *_):
        pass
    def do_GET(self):
        name = {"/feed/roster": "roster.json", "/feed/events": "events.sse"}.get(self.path, "agent.json")
        data = (here / name).read_bytes()
        if name == "events.sse":
            cursor = int(self.headers.get("Last-Event-ID", "-1"))
            data = b"\n\n".join(frame for frame in data.split(b"\n\n") if frame and int(frame.split(b"\n")[0].split(b":")[1]) > cursor) + b"\n\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream" if name == "events.sse" else "application/json")
        self.end_headers()
        for start in range(0, len(data), 7):
            self.wfile.write(data[start:start+7])
            self.wfile.flush()

def port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]
def get(base, path):
    with urllib.request.urlopen(base + path, timeout=2) as response:
        return response.read()
def wait(base, predicate):
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        try:
            health = json.loads(get(base, "/api/health"))
            if predicate(health):
                return health
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(.1)
    raise AssertionError("health deadline expired")

server = ThreadingHTTPServer(("127.0.0.1", 0), Fixture)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
evidence = {"evidence": "local fake HTTP fixture; no native game or host effects"}
for mode in ("live", "mock"):
    address = f"127.0.0.1:{port()}"
    base = f"http://{address}"
    env = dict(os.environ, WORLDFEED_BACKEND=mode, DASHBOARD_BIND=address,
               WORLDFEED_URL=f"http://127.0.0.1:{server.server_port}")
    process = subprocess.Popen([str(here.parent / "target/debug/dashboard")], env=env, stdout=subprocess.DEVNULL)
    try:
        health = wait(base, lambda h: h["mode"] == mode and (mode == "mock" or h["last_event_id"] == 1))
        page = get(base, "/").decode()
        assert ("MOCK DEMO" if mode == "mock" else "LIVE") in page
        evidence[mode] = {"health": health, "visually_marked": True}
        if mode == "live":
            roster = json.loads(get(base, "/api/roster"))
            id = roster["agents"][0]["persona_id"]
            detail = json.loads(get(base, "/api/agent/" + id))
            assert detail["characters"][0]["level"] is None
            assert detail["current_goal"] == "grind"
            assert "not supplied" in get(base, "/agent/" + id).decode()
            server.shutdown(); server.server_close(); thread.join(timeout=2)
            stale = wait(base, lambda h: h["status"] == "stale" and h["error"] is not None)
            assert json.loads(get(base, "/api/roster"))["agents"] == roster["agents"]
            evidence[mode]["after_upstream_shutdown"] = stale
    finally:
        process.terminate()
        process.wait(timeout=5)
print(json.dumps(evidence, indent=2))
