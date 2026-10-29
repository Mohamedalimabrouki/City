"""Headless screenshots of the web viewer, for quick visual checks of a generated city.

    python tools/snapshot.py OUT_DIR --png shot.png --view aerial

Needs Playwright with Chromium (pip install playwright; playwright install chromium).
WebGL runs on the CPU (SwiftShader), so big scenes are slow: lower the load with
--query radius=1000. The page loads three.js from a CDN; use --three-dir for offline runs.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from citygen.view import start_server  # noqa: E402

INSTALL_HINT = ("Playwright is not installed. Install it with:\n"
                "  pip install playwright\n"
                "  playwright install chromium")
CDN = re.compile(r"https://cdn\.jsdelivr\.net/npm/three@[^/]+/(.*)")
SOFTWARE_GL = ["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"]
BROWSER_GLOBS = (
    "chromium_headless_shell-*/chrome-*/headless_shell", "chromium_headless_shell-*/chrome-*/headless_shell.exe",
    "chromium-*/chrome-linux*/chrome", "chromium-*/chrome-win*/chrome.exe",
    "chromium-*/chrome-mac*/Chromium.app/Contents/MacOS/Chromium",
)


class SnapshotError(RuntimeError):
    """The screenshot could not be taken."""


def _find_browser() -> str | None:
    """Newest Chromium in the Playwright browser cache, for when its revision differs from ours."""
    roots = [os.environ.get("PLAYWRIGHT_BROWSERS_PATH"), "~/.cache/ms-playwright",
             "~/Library/Caches/ms-playwright", "~/AppData/Local/ms-playwright"]
    found = []
    for root in (Path(r).expanduser() for r in roots if r):
        for pattern in BROWSER_GLOBS:
            for exe in root.glob(pattern):
                revision = re.search(r"-(\d+)$", exe.relative_to(root).parts[0])
                if revision and exe.is_file():
                    found.append((int(revision.group(1)), "headless_shell" in exe.name, str(exe)))
    return max(found)[2] if found else None


def _launch(pw, gpu: bool):
    from playwright.sync_api import Error

    opts: dict = {"headless": True, "args": [] if gpu else SOFTWARE_GL}
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if proxy:
        # <-loopback> must come first: Playwright otherwise sends 127.0.0.1 through the proxy too
        opts["proxy"] = {"server": proxy, "bypass": "<-loopback>,localhost,127.0.0.1"}
    try:
        return pw.chromium.launch(**opts)
    except Error as exc:
        missing = "Executable doesn't exist" in str(exc)
        exe = _find_browser() if missing else None
        if exe is not None:
            return pw.chromium.launch(executable_path=exe, **opts)
        if missing:   # no Playwright Chromium at all: the installed Google Chrome, if any
            try:
                browser = pw.chromium.launch(channel="chrome", **opts)
                print("snapshot: Playwright's Chromium is missing, using Google Chrome", file=sys.stderr)
                return browser
            except Error:
                pass
        raise SnapshotError(f"could not start Chromium ({str(exc).splitlines()[0]}).\n"
                            "Try: playwright install chromium") from exc


def _serve_three(page, three_dir: Path) -> None:
    root = three_dir.resolve()

    def handler(route) -> None:
        file = (root / CDN.match(route.request.url).group(1)).resolve()
        if root in file.parents and file.is_file():
            route.fulfill(path=str(file), content_type="text/javascript", headers={"access-control-allow-origin": "*"})
        else:
            route.fulfill(status=404, body="")

    page.route(CDN, handler)


def _wait_ready(page, timeout: float) -> None:
    """Wait for the viewer's settled state: every tile near the camera full, every far tile lod1, nothing
    in flight, and a frame drawn of it (`citygenReady`, prompt 41), so one build always gives one picture."""
    deadline = time.monotonic() + timeout
    while True:
        state = page.evaluate("() => ({ready: window.citygenReady === true, error: window.citygenError || null,"
                              " stats: window.citygenStats || null})")
        stats = state["stats"] or {}
        if state["error"]:
            hint = "\nUse --three-dir for offline runs." if "CDN" in state["error"] else ""
            raise SnapshotError(f"viewer error: {state['error']}{hint}")
        if state["ready"]:
            if stats.get("failed"):
                print(f"warning: {stats['failed']} of {stats['requested']} tiles failed to load", file=sys.stderr)
            return
        if time.monotonic() > deadline:
            kinds = f", {stats['full']} full, {stats['lod1']} lod1, {stats['loading']} loading" if "full" in stats else ""
            raise SnapshotError(f"timed out after {timeout:.0f} s waiting for the viewer "
                                f"(tiles {stats.get('loaded', 0)}/{stats.get('requested', '?')}{kinds}); software "
                                "rendering is slow, try --query radius=800 or a longer --timeout")
        page.wait_for_timeout(250)


def snapshot(out_dir: str | Path, png_path: str | Path, view: str = "aerial", width: int = 1600, height: int = 900,
             query: str = "", timeout: float = 180.0, three_dir: str | Path | None = None, gpu: bool = False) -> Path:
    """Render the city in `out_dir` with the web viewer and save a PNG. Returns the PNG path.

    `query` is extra viewer URL parameters, e.g. "radius=1000&shadows=0" or "cam=x,y,z&look=x,y,z".
    `three_dir` is a local copy of the npm package three@0.169.0, served instead of the CDN.
    `gpu=True` keeps Chromium's default (hardware) GL instead of forcing SwiftShader.
    """
    try:
        from playwright.sync_api import Error, sync_playwright
    except ImportError as exc:
        raise SnapshotError(INSTALL_HINT) from exc

    png = Path(png_path)
    png.parent.mkdir(parents=True, exist_ok=True)
    params = [] if "view=" in query else [f"view={quote(view)}"]
    if query:
        params.append(query.lstrip("?&"))
    problems: list[str] = []

    server, base = start_server(out_dir)
    try:
        with sync_playwright() as pw:
            browser = _launch(pw, gpu)
            try:
                page = browser.new_page(viewport={"width": width, "height": height})
                page.on("console", lambda m: problems.append(m.text) if m.type == "error" else None)
                page.on("pageerror", lambda e: problems.append(str(e)))
                # ERR_ABORTED is only Chromium reporting streamed tile downloads, which do complete
                page.on("requestfailed", lambda r: None if r.failure == "net::ERR_ABORTED"
                        else problems.append(f"request failed: {r.url} {r.failure}"))
                if three_dir:
                    _serve_three(page, Path(three_dir))
                page.goto(f"{base}/?{'&'.join(params)}", wait_until="commit")
                _wait_ready(page, timeout)
                page.evaluate("() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)))")
                _wait_ready(page, timeout)   # still settled two frames later (nothing started meanwhile)
                page.screenshot(path=str(png), timeout=60_000)
            finally:
                browser.close()
    except Error as exc:
        raise SnapshotError(str(exc).splitlines()[0]) from exc
    finally:
        server.shutdown()
        server.server_close()
        for problem in problems:
            print(f"browser: {problem}", file=sys.stderr)
    return png


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Screenshot a generated city with the web viewer.")
    ap.add_argument("out_dir", help="generator output directory (contains tiles/index.json)")
    ap.add_argument("--png", default=None, help="output file (default: snapshot_<view>.png)")
    ap.add_argument("--view", default="aerial",
                    help="aerial, street, top or a name from the views in tiles/index.json (default: aerial)")
    ap.add_argument("--width", type=int, default=1600)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--query", default="", help='extra viewer parameters, e.g. "radius=1000&shadows=0&ui=0"')
    ap.add_argument("--timeout", type=float, default=180.0, help="seconds to wait for the scene (default: 180)")
    ap.add_argument("--three-dir", default=None, help="local three@0.169.0 package to use instead of the CDN")
    ap.add_argument("--gpu", action="store_true", help="use the default GL backend instead of software rendering")
    args = ap.parse_args(argv)
    try:
        path = snapshot(args.out_dir, args.png or f"snapshot_{args.view}.png", args.view, args.width, args.height,
                        args.query, args.timeout, args.three_dir, args.gpu)
    except (SnapshotError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(path.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
