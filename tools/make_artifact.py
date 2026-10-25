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

from shapely.geometry import Point, Polygon
from shapely.strtree import STRtree

ROOT = Path(__file__).resolve().parents[1]
# The page shows the build's own views (index.json "views") and these hand-picked spots in the quick seed-42
# capital, for places the build has no view of (x east, y north, z up; the camera 1.7 m over Ground.surface,
# taken again in prompt 42). Skipped elsewhere, and when a later plan puts a building within CLEAR meters.
SPOTS = {
    "carpet_souk": {"cam": [6900.9, 11960.9, 21.3], "look": [6897.9, 11953.6, 21.5]},
    "kasbah_gate": {"cam": [7052.4, 11974.6, 32.0], "look": [7067.8, 11964.8, 35.5]},
    "cemetery": {"cam": [7014.3, 11577.1, 52.4], "look": [7023.1, 11609.9, 52.4]},
}
CLEAR = 1.0


def page(title: str, start: str) -> str:
    html = (ROOT / "tools" / "viewer" / "index.html").read_text(encoding="utf-8")
    # the Artifact host adds the document skeleton, charset and viewport itself
    for pattern in (r"<!doctype html>\s*", r"<html[^>]*>\s*", r"<head>\s*", r"</head>\s*", r"<body>\s*",
                    r"</body>\s*", r"</html>\s*", r'<meta charset="utf-8">\s*', r'<meta name="viewport"[^>]*>\s*',
                    r'<meta name="theme-color"[^>]*>\s*', r'<link rel="icon"[^>]*>\s*', r"<title>[^<]*</title>\s*"):
        html = re.sub(pattern, "", html, count=1)
    swaps = {
        # tiles (full and lod1) are .glb files stored as base64 text in JSON files: decode, parse in memory
        "  return loader.parseAsync(await res.arrayBuffer(), tileBase.href);":
            "  const text = atob((await res.json()).glb);\n"
            "  const bytes = new Uint8Array(text.length);\n"
            "  for (let i = 0; i < text.length; i++) bytes[i] = text.charCodeAt(i);\n"
            "  return loader.parseAsync(bytes.buffer, tileBase.href);",
        "const loader = new GLTFLoader();":
            "const loader = new GLTFLoader();\n"
            "// texture images travel as base64 JSON; each becomes one blob URL shared by every tile\n"
            "const textureFiles = await (await fetch('data/textures.json')).json();\n"
            "const textureUrls = new Map();\n"
            "for (const [name, data] of Object.entries(textureFiles)) {\n"
            "  const binary = atob(data);\n"
            "  const bytes = new Uint8Array(binary.length);\n"
            "  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);\n"
            "  const type = /\\.jpe?g$/i.test(name) ? 'image/jpeg' : 'image/png';\n"
            "  textureUrls.set('textures/' + name, URL.createObjectURL(new Blob([bytes], { type })));\n"
            "}\n"
            "loader.manager.setURLModifier((url) => {\n"
            "  const name = url.split('/').pop().split('?')[0];\n"
            "  return textureUrls.get('textures/' + name) || url;\n"
            "});\n"
            "// loaded as <img>: the Artifact host lets a page show blob: images but may refuse to fetch() them\n"
            "loader.manager.addHandler(/^textures\\//, new THREE.TextureLoader(loader.manager));",
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


def clear_spots(spots: dict, plans: list) -> dict:
    """The spots whose camera stands CLEAR meters or more from every building of the plans."""
    walls = [Polygon(f[0], f[1:]) for plan in plans for f in (b["footprint"] for b in plan["buildings"])
             if len(f[0]) > 2]
    tree = STRtree(walls)
    keep = {}
    for name, spot in spots.items():
        p = Point(spot["cam"][:2])
        if any(walls[i].distance(p) < CLEAR for i in tree.query(p.buffer(CLEAR))):
            print(f"spot {name} skipped: a building stands within {CLEAR:g} m of its camera")
        else:
            keep[name] = spot
    return keep


def _store_tile(src: Path, art: Path, name: str) -> str:
    """Copy one .glb tile as base64 text in a JSON file; returns the new file name."""
    stored = name.replace(".glb", ".json")
    glb = (src / "tiles" / name).read_bytes()
    (art / "data" / "tiles" / stored).write_text(json.dumps({"glb": base64.b64encode(glb).decode()}))
    return stored


def make_artifact(src: Path, art: Path, title: str, start: str) -> int:
    shutil.rmtree(art, ignore_errors=True)
    (art / "data" / "tiles").mkdir(parents=True)
    index = json.loads((src / "tiles" / "index.json").read_text(encoding="utf-8"))
    size = index["tile_size"]
    box = (min(t["x0"] for t in index["tiles"]), min(t["y0"] for t in index["tiles"]),
           max(t["x0"] for t in index["tiles"]) + size, max(t["y0"] for t in index["tiles"]) + size)
    plans = {city["plan"]: json.loads((src / city["plan"]).read_text(encoding="utf-8"))
             for city in index.get("cities", [])}
    spots = {k: v for k, v in SPOTS.items() if box[0] <= v["cam"][0] <= box[2] and box[1] <= v["cam"][1] <= box[3]}
    index["views"] = {**clear_spots(spots, list(plans.values())), **index.get("views", {})}
    if start not in index["views"] and start not in ("aerial", "top", "street"):
        start = "aerial"
    for t in index["tiles"]:
        t["file"] = _store_tile(src, art, t["file"])
        if "lod1" in t:   # the light twin the viewer shows far away (prompt 41)
            old = t["lod1"]["file"]
            t["lod1"]["file"] = _store_tile(src, art, old)
            t["files"] = [t["lod1"]["file"] if f == old else f for f in t.get("files", [])]
    (art / "data" / "tiles" / "index.json").write_text(json.dumps(index))
    for name, plan in plans.items():
        out = art / "data" / name
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(slim_plan(plan, box), separators=(",", ":")))
    # one base64 copy per texture image; the page turns each into a blob URL the tiles share
    textures = {path.name: base64.b64encode(path.read_bytes()).decode()
                for path in sorted((src / "tiles" / "textures").glob("*"))
                if path.is_file() and path.suffix.lower() in (".png", ".jpg", ".jpeg")}
    (art / "data" / "textures.json").write_text(json.dumps(textures))
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
