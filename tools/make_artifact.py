"""Turn a built world into a folder for a claude.ai 3D page (an Artifact) that also opens on a phone.

    python tools/make_artifact.py output/bodjantouna-42 ART_DIR --title "Goumosbane in 3D"

The page is the web viewer; tiles become base64 text inside JSON files (an Artifact cannot serve
.glb files), and the city plan is cut down to what the "who lives here" card reads. Publish
ART_DIR/index.html with every other file of ART_DIR from a Claude session, to the same link as
before (see docs/HANDOFF.md). Keep the build small (--quick): each file must stay under 16 MB and
one publish under 64 MB, and a phone has to download all of it.
"""
from __future__ import annotations

import argparse
import base64
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
# hand-picked camera spots in the quick seed-42 world (x east, y north, z up); skipped elsewhere
SPOTS = {
    "carpet_souk": {"cam": [6903.2, 11960.0, 21.3], "look": [6899.1, 11955.2, 21.2]},
    "alley_arch": {"cam": [7129.1, 12027.1, 34.2], "look": [7133.3, 12031.8, 34.1]},
    "old_houses": {"cam": [6722.5, 11982.5, 9.0], "look": [6731.8, 11991.1, 11.0]},
}


def page(title: str, start: str) -> str:
    html = (ROOT / "tools" / "viewer" / "index.html").read_text(encoding="utf-8")
    # the Artifact host adds the document skeleton, charset and viewport itself
    for pattern in (r"<!doctype html>\s*", r"<html[^>]*>\s*", r"<head>\s*", r"</head>\s*", r"<body>\s*",
                    r"</body>\s*", r"</html>\s*", r'<meta charset="utf-8">\s*', r'<meta name="viewport"[^>]*>\s*',
                    r'<meta name="theme-color"[^>]*>\s*', r'<link rel="icon"[^>]*>\s*', r"<title>[^<]*</title>\s*"):
        html = re.sub(pattern, "", html, count=1)
    swaps = {
        "        addTile(await loader.loadAsync(new URL(t.file, tileBase).href));":
            "        addTile(await fetchTile(new URL(t.file, tileBase).href));",
        "async function loadTiles(list, wantsStreet) {":
            "// tiles are .glb files stored as base64 text in JSON files: decode and parse them in memory\n"
            "async function fetchTile(url) {\n"
            "  const res = await fetch(url);\n"
            "  if (!res.ok) throw new Error(`HTTP ${res.status}`);\n"
            "  const text = atob((await res.json()).glb);\n"
            "  const bytes = new Uint8Array(text.length);\n"
            "  for (let i = 0; i < text.length; i++) bytes[i] = text.charCodeAt(i);\n"
            "  return loader.parseAsync(bytes.buffer, '');\n"
            "}\n\n"
            "async function loadTiles(list, wantsStreet) {",
        "  const name = q.get('view') || 'aerial';": f"  const name = q.get('view') || '{start}';",
        "  fillViews(index, q.get('view') || 'aerial');": f"  fillViews(index, q.get('view') || '{start}');",
    }
    for old, new in swaps.items():
        if html.count(old) != 1:
            raise SystemExit(f"the viewer changed, update make_artifact.py: {old.strip()[:60]}")
        html = html.replace(old, new)
    return f'<title>{title}</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n' + html


def slim_plan(plan: dict, box: tuple) -> dict:
    """Only what the info card reads; buildings and streets outside the tiles keep their place but lose their shape."""
    x0, y0, x1, y1 = box
    inside = lambda pts: bool(pts) and x0 <= pts[0][0] <= x1 and y0 <= pts[0][1] <= y1
    r1 = lambda pts: [[round(x, 1), round(y, 1)] for x, y in pts]
    keep = set()
    buildings = []
    for k, b in enumerate(plan["buildings"]):
        ring = b["footprint"][0]
        if inside(ring):
            keep.add(k)
        buildings.append({"kind": b["kind"], "floors": b["floors"], "footprint": [r1(ring) if inside(ring) else []]})
    districts = []
    for d in plan["districts"]:
        g = d["geometry"]
        if g["type"] == "Polygon":
            geom = {"type": "Polygon", "coordinates": [r1(g["coordinates"][0])]}
        else:
            geom = {"type": "MultiPolygon", "coordinates": [[r1(c[0])] for c in g["coordinates"]]}
        districts.append({"id": d["id"], "kind": d["kind"], "name": d["name"], "geometry": geom})
    return {"format": plan["format"], "settlement": plan["settlement"], "buildings": buildings,
            "streets": [{"kind": s["kind"], "width": s["width"],
                         "coords": r1(s["coords"]) if inside(s["coords"]) else [[0, 0]]} for s in plan["streets"]],
            "districts": districts, "landmarks": plan["landmarks"], "souks": plan["souks"],
            "households": [h for h in plan["households"] if h["building"] in keep]}


def make_artifact(src: Path, art: Path, title: str, start: str) -> int:
    shutil.rmtree(art, ignore_errors=True)
    (art / "data" / "tiles").mkdir(parents=True)
    index = json.loads((src / "tiles" / "index.json").read_text(encoding="utf-8"))
    size = index["tile_size"]
    box = (min(t["x0"] for t in index["tiles"]), min(t["y0"] for t in index["tiles"]),
           max(t["x0"] for t in index["tiles"]) + size, max(t["y0"] for t in index["tiles"]) + size)
    spots = {k: v for k, v in SPOTS.items() if box[0] <= v["cam"][0] <= box[2] and box[1] <= v["cam"][1] <= box[3]}
    index["views"] = {**spots, **index.get("views", {})}
    if start not in index["views"] and start not in ("aerial", "top", "street"):
        start = "aerial"
    for t in index["tiles"]:
        glb = (src / "tiles" / t["file"]).read_bytes()
        t["file"] = t["file"].replace(".glb", ".json")
        (art / "data" / "tiles" / t["file"]).write_text(json.dumps({"glb": base64.b64encode(glb).decode()}))
    (art / "data" / "tiles" / "index.json").write_text(json.dumps(index))
    for city in index.get("cities", []):
        out = art / "data" / city["plan"]
        out.parent.mkdir(parents=True, exist_ok=True)
        plan = json.loads((src / city["plan"]).read_text(encoding="utf-8"))
        out.write_text(json.dumps(slim_plan(plan, box), separators=(",", ":")))
    (art / "index.html").write_text(page(title, start), encoding="utf-8")
    return max(f.stat().st_size for f in art.rglob("*") if f.is_file()), \
        sum(f.stat().st_size for f in art.rglob("*") if f.is_file())


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("src", help="a built world folder, e.g. output/bodjantouna-42")
    ap.add_argument("art", help="folder to write the page and its data into")
    ap.add_argument("--title", default="Goumosbane in 3D")
    ap.add_argument("--start", default="carpet_souk", help="camera spot the page opens on")
    args = ap.parse_args()
    biggest, total = make_artifact(Path(args.src), Path(args.art), args.title, args.start)
    print(f"{args.art}: {total / 1e6:.1f} MB, biggest file {biggest / 1e6:.1f} MB")
    if biggest > 16e6 or total > 64e6:
        print("too big for one publish: use a smaller build (--quick or a smaller --area)")
