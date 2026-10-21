"""Local web viewer server.

Serves the three.js viewer (tools/viewer/) at / and a generator output
directory at /data/, so the page can load /data/tiles/index.json and the
tiles it lists. Standard library only.
"""
from __future__ import annotations

import sys
import threading
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

VIEWER_DIR = Path(__file__).resolve().parents[1] / "tools" / "viewer"
DATA_PREFIX = "/data"


class _Handler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".glb": "model/gltf-binary",
        ".gltf": "model/gltf+json",
        ".json": "application/json",
        ".js": "text/javascript",
        ".mjs": "text/javascript",
        ".html": "text/html; charset=utf-8",
    }

    def __init__(self, *args, data_dir: str, **kwargs) -> None:
        self.data_dir = data_dir
        super().__init__(*args, directory=str(VIEWER_DIR), **kwargs)

    def translate_path(self, path: str) -> str:
        # /data/... comes from the output directory, everything else from the viewer
        if path == DATA_PREFIX or path.startswith((DATA_PREFIX + "/", DATA_PREFIX + "?", DATA_PREFIX + "#")):
            self.directory = self.data_dir
            path = path[len(DATA_PREFIX):] or "/"
        else:
            self.directory = str(VIEWER_DIR)
        return super().translate_path(path)

    def end_headers(self) -> None:
        # the generator rewrites tiles in place, so never let the browser reuse old ones
        self.send_header("Cache-Control", "no-store, max-age=0")
        self.send_header("Pragma", "no-cache")
        super().end_headers()

    def log_message(self, format: str, *args) -> None:
        pass


class _Server(ThreadingHTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address) -> None:
        # browsers abort requests all the time (reloads, cancelled tile fetches)
        if isinstance(sys.exc_info()[1], ConnectionError):
            return
        super().handle_error(request, client_address)


def start_server(out_dir: str | Path, port: int = 0) -> tuple[ThreadingHTTPServer, str]:
    """Start the viewer server in a background thread.

    `out_dir` is the generator output directory (the one holding tiles/).
    port=0 picks a free port. Returns (server, base_url) with no trailing
    slash, e.g. "http://127.0.0.1:43211". Stop it with server.shutdown().
    """
    out = Path(out_dir).resolve()
    if not out.is_dir():
        raise FileNotFoundError(f"output directory not found: {out}")
    server = _Server(("127.0.0.1", port), lambda *a, **kw: _Handler(*a, data_dir=str(out), **kw))
    threading.Thread(target=server.serve_forever, name="citygen-view", daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_port}"


def serve(out_dir: str | Path, port: int = 8765, open_browser: bool = True) -> None:
    """Serve the viewer until Ctrl+C. Falls back to a free port if `port` is busy."""
    try:
        server, url = start_server(out_dir, port)
    except OSError:
        if port == 0:
            raise
        server, url = start_server(out_dir, 0)
        print(f"port {port} is busy, using {server.server_port} instead")
    if not (Path(out_dir) / "tiles" / "index.json").is_file():
        print(f"warning: {Path(out_dir) / 'tiles' / 'index.json'} does not exist yet")
    print(f"citygen viewer: {url}/   (Ctrl+C to stop)")
    if open_browser:
        webbrowser.open(url + "/")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print()
    finally:
        server.shutdown()
        server.server_close()
