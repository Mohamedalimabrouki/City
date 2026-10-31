"""Local web viewer server.

Serves the three.js viewer (tools/viewer/) at / and a generator output
directory at /data/, so the page can load /data/tiles/index.json and the
tiles it lists. Standard library only.

`serve_gallery` serves the city gallery instead: a page listing every world built under output/
(read from the folder at each request, so new builds appear by themselves) with the viewer of
each at /b/<key>/. The viewer loads its data relative to its page ("data/..."), so the same file
serves every build.

Both answer `api/interior` (SPEC 6c "Viewer", prompt 50): a bare GET says `{"ok": true}`, and
`api/interior?city=NAME&building=K` makes that dwelling's interior folder in the build and answers
`{"folder": "interiors/<slug>-<k>"}`. The gallery answers it under `/b/<key>/api/interior`.
"""
from __future__ import annotations

import json
import re
import sys
import threading
import time
import traceback
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

VIEWER_DIR = Path(__file__).resolve().parents[1] / "tools" / "viewer"
DATA_PREFIX = "/data"
PICTURES = (".png", ".jpg", ".jpeg")
LATEST_PICTURES = 24          # the gallery shows this many of the newest pictures in output/checks
HIDDEN_VIEW = re.compile(r"^rows\d+$")   # the kit sheet's row cameras: too many for buttons
INTERIOR_FOLDER = re.compile(r"^interiors/[a-z0-9-]+$")   # the only sub folders the viewer may open
BUILDING_NUMBER = re.compile(r"^\d{1,7}$")
CITY_NAME_MAX = 120


class Interiors:
    """Makes interiors for the viewer servers: one at a time (behind a lock, so a second click waits for the
    first), with one `BuildContext` per build folder kept while the server runs, so after the first
    interior of a build (world, plans and kit: a few seconds) the next one takes about a second. A context
    is loaded again when its build's summary.json changes (the city was built again)."""

    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.contexts: dict = {}         # resolved build folder -> (summary.json mtime, BuildContext)

    @staticmethod
    def _stamp(folder: Path) -> float:
        try:
            return (folder / "summary.json").stat().st_mtime
        except OSError:
            return -1.0

    def keep(self, folder, ctx) -> None:
        """Use `ctx` for the build in `folder` (tests hand over one they already loaded)."""
        folder = Path(folder).resolve()
        self.contexts[folder] = (self._stamp(folder), ctx)

    def make(self, folder, city: str | None, building: str, log=print) -> str:
        """Make building k's interior in the build at `folder`; returns its folder relative to the build.
        Raises `InteriorError` with a plain message for anything the command refuses."""
        from .interior.command import make_interior
        from .interior.context import load_build
        folder = Path(folder).resolve()
        with self.lock:
            stamp = self._stamp(folder)
            kept = self.contexts.get(folder)
            if kept is None or kept[0] != stamp:
                self.contexts[folder] = kept = (stamp, load_build(folder, log))
            out = make_interior(folder, building, city, log=log, ctx=kept[1])
        rel = out.resolve().relative_to(folder).as_posix()
        if not INTERIOR_FOLDER.match(rel):
            raise RuntimeError(f"unexpected interior folder {rel!r}")
        return rel


INTERIORS = Interiors()   # the one every server of this process shares


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

    def __init__(self, *args, data_dir: str, interiors: Interiors | None = None, **kwargs) -> None:
        self.data_dir = data_dir
        self.interiors = interiors or INTERIORS
        super().__init__(*args, directory=str(VIEWER_DIR), **kwargs)

    def do_GET(self) -> None:
        if unquote(urlsplit(self.path).path) == "/api/interior":
            self.answer_interior(Path(self.data_dir))
            return
        super().do_GET()

    def send_json(self, data, status: int = 200) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def answer_interior(self, folder: Path) -> None:
        """`api/interior`: `{"ok": true}` without a building, else make it (400 with {"error"} when refused).
        This request's thread waits while the interior is made; the server's other threads keep serving."""
        from .interior import InteriorError
        query = parse_qs(urlsplit(self.path).query)
        building = (query.get("building") or [""])[0].strip()
        city = (query.get("city") or [""])[0].strip() or None
        if not building and city is None:
            self.send_json({"ok": True})
            return
        if not BUILDING_NUMBER.match(building):
            self.send_json({"error": "Give the building's number (the card's No. k), for example building=190."}, 400)
            return
        if city is not None and (len(city) > CITY_NAME_MAX or not city.isprintable()):
            self.send_json({"error": "That is not a city name."}, 400)
            return
        try:
            self.send_json({"folder": self.interiors.make(folder, city, building)})
        except InteriorError as err:
            self.send_json({"error": str(err)}, 400)
        except Exception as err:                       # a bug: say so on the card and in the server's window
            traceback.print_exc()
            self.send_json({"error": f"The interior could not be made ({type(err).__name__}: {err})."}, 500)

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


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def build_folders(root: Path) -> list:
    """Every world folder under root that has a summary or tiles: output/<world>/ and output/<folder>/<world>/,
    and the interior folders made in them (<world>/interiors/<name>/, prompt 50)."""
    found = set()
    for pattern in ("*/summary.json", "*/*/summary.json", "*/tiles/index.json", "*/*/tiles/index.json",
                    "*/interiors/*/tiles/index.json", "*/*/interiors/*/tiles/index.json"):
        for p in root.glob(pattern):
            found.add(p.parent if p.name == "summary.json" else p.parent.parent)
    return sorted(f for f in found if f.relative_to(root).parts[0] != "checks")   # checks: test folders of prompts


def build_info(root: Path, folder: Path) -> dict:
    """What the gallery shows about one built world, read from its own files (never a stale copy)."""
    summary = _read_json(folder / "summary.json")
    index = _read_json(folder / "tiles" / "index.json")
    rel = folder.relative_to(root).as_posix()
    stamps = [p.stat().st_mtime for p in (folder / "summary.json", folder / "tiles" / "index.json") if p.is_file()]
    cities = [p["name"] for p in summary.get("plans", []) if p.get("name")]
    maps = sorted((folder / "maps").glob("*.png"), key=lambda p: (p.stem == "country", p.name))
    views = [v for v in (index.get("views") or {}) if not HIDDEN_VIEW.match(v)]
    tiles = summary.get("tiles") or {}
    interior = isinstance(index.get("interior"), dict)
    return {"key": rel.replace("/", "~"), "path": f"output/{rel}", "interior": interior,
            "parent": f"output/{folder.parent.parent.relative_to(root).as_posix()}" if interior else "",
            "world": summary.get("world") or index.get("world_name") or folder.name,
            "cities": cities, "size_km": summary.get("size_km"), "area": summary.get("area", ""),
            "tiles": tiles.get("count") or len(index.get("tiles", [])), "megabytes": tiles.get("megabytes"),
            "has3d": bool(index), "views": views,
            "maps": [{"name": m.stem, "url": f"/out/{rel}/maps/{m.name}"} for m in maps],
            "blend": [f"output/{rel}/{b.name}" for b in sorted(folder.glob("*.blend"))],
            "built": max(stamps, default=0.0)}


def builds(root: Path) -> list:
    """Every built world under root, newest first."""
    return sorted((build_info(root, f) for f in build_folders(root)), key=lambda b: -b["built"])


def pictures(root: Path, count: int = LATEST_PICTURES) -> list:
    """The newest pictures of output/checks (the before/after picture of every prompt), newest first."""
    found = [p for p in (root / "checks").glob("*") if p.suffix.lower() in PICTURES]
    found.sort(key=lambda p: -p.stat().st_mtime)
    return [{"name": p.name, "url": f"/out/checks/{p.name}", "time": p.stat().st_mtime} for p in found[:count]]


class _GalleryHandler(_Handler):
    """The gallery at /, its lists at /api/builds and /api/pictures, files of output/ at /out/,
    and each build's viewer at /b/<key>/ with its data at /b/<key>/data/ (key: the folder under
    output/ with "/" written as "~")."""

    def __init__(self, *args, root: str, **kwargs) -> None:
        self.root = Path(root).resolve()
        super().__init__(*args, data_dir=str(self.root), **kwargs)

    def do_GET(self) -> None:
        route = unquote(urlsplit(self.path).path)
        if route in ("/api/builds", "/api/pictures"):
            self.send_json(builds(self.root) if route == "/api/builds" else pictures(self.root))
            return
        found = re.fullmatch(r"/b/([^/]+)/api/interior", route)
        if found:
            folder = self._build(found.group(1))
            if folder is None:
                self.send_json({"error": "There is no such build in the gallery."}, 404)
            else:
                self.answer_interior(folder)
            return
        if re.fullmatch(r"/b/[^/]+", route):   # the viewer loads "data/..." relative to its page
            query = urlsplit(self.path).query
            self.send_response(301)
            self.send_header("Location", route + "/" + (f"?{query}" if query else ""))
            self.end_headers()
            return
        SimpleHTTPRequestHandler.do_GET(self)   # not _Handler's: the gallery's own api/interior is per build

    def _build(self, key: str) -> Path | None:
        folder = (self.root / key.replace("~", "/")).resolve()
        inside = folder != self.root and self.root in folder.parents
        return folder if inside and folder in build_folders(self.root) else None

    def translate_path(self, path: str) -> str:
        route = unquote(urlsplit(path).path)
        rest = "/"
        self.directory = str(VIEWER_DIR)
        if route in ("/", "/index.html"):
            rest = "/gallery.html"
        elif route.startswith("/out/"):
            self.directory, rest = str(self.root), route[len("/out"):]
        elif route.startswith("/b/"):
            key, _, tail = route[len("/b/"):].partition("/")
            folder = self._build(key)
            if folder is None:
                return str(VIEWER_DIR / "missing")      # unknown build: a plain 404
            if tail.startswith("data/") or tail == "data":
                self.directory, rest = str(folder), "/" + tail[len("data"):].lstrip("/")
            else:
                rest = "/" + (tail or "index.html")
        else:
            rest = route
        return SimpleHTTPRequestHandler.translate_path(self, rest)


def serve_gallery(root: str | Path = "output", port: int = 8765, open_browser: bool = True) -> None:
    """Serve the city gallery until Ctrl+C. Falls back to a free port if `port` is busy."""
    folder = Path(root).resolve()
    if not folder.is_dir():
        raise FileNotFoundError(f"output directory not found: {folder}")
    handler = lambda *a, **kw: _GalleryHandler(*a, root=str(folder), **kw)   # noqa: E731
    try:
        server = _Server(("127.0.0.1", port), handler)
    except OSError:
        server = _Server(("127.0.0.1", 0), handler)
        print(f"port {port} is busy, using {server.server_port} instead")
    threading.Thread(target=server.serve_forever, name="citygen-gallery", daemon=True).start()
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"citygen gallery: {url}   ({len(build_folders(folder))} builds in {folder}; Ctrl+C to stop)")
    if open_browser:
        webbrowser.open(url)
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        print()
    finally:
        server.shutdown()
        server.server_close()


def start_server(out_dir: str | Path, port: int = 0,
                 interiors: Interiors | None = None) -> tuple[ThreadingHTTPServer, str]:
    """Start the viewer server in a background thread.

    `out_dir` is the generator output directory (the one holding tiles/).
    port=0 picks a free port. Returns (server, base_url) with no trailing
    slash, e.g. "http://127.0.0.1:43211". Stop it with server.shutdown(). `interiors`: who makes the
    interiors of `api/interior` (default: the process's shared `INTERIORS`).
    """
    out = Path(out_dir).resolve()
    if not out.is_dir():
        raise FileNotFoundError(f"output directory not found: {out}")
    handler = lambda *a, **kw: _Handler(*a, data_dir=str(out), interiors=interiors, **kw)   # noqa: E731
    server = _Server(("127.0.0.1", port), handler)
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
