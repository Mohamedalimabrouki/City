"""Floor plans of interiors as one PNG, to judge layouts without a 3D viewer (SPEC 6c, prompt 46).

    python tools/interior_plans.py SPEC[@CITY] ... [--folder BUILD] [--out PNG]

SPEC is a building number or pick:<layout>[:<floors>], as for `python -m citygen interior`. @CITY names a
city of the build, or any settlement of the world (the tool then plans it, under a second for a town).
Each interior is one row: its storeys side by side (and the roof when it holds rooms), north up, all at
one scale (at most 1800 px wide). Rooms are filled by type, exterior and court walls black, partitions
grey, facade and court doors red, windows blue, inner doors as gaps, stairs hatched with an arrow up.
Default folder: the latest build; default picture: output/checks/interior_plans.png.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

WIDTH = 1800          # px, the widest picture
SCALE = 40.0          # px per meter at most
PAD = 24              # px between panels
TITLE = 34            # px for the title line of a row
CAPTION = 22          # px for the caption under each panel
COLORS = {"wast_ed_dar": (236, 226, 196), "skifa": (214, 178, 132), "bit": (240, 170, 150),
          "maqsura": (247, 208, 176), "matbakh": (170, 207, 150), "bit_el_ma": (150, 200, 232),
          "bit_el_mouna": (204, 192, 170), "droj": (190, 190, 190), "ghorfa": (240, 192, 162),
          "stah": (226, 226, 214), "menzah": (232, 164, 194), "well": (252, 252, 252), "bortal": (222, 212, 170),
          "hall": (214, 178, 132), "couloir": (232, 214, 176), "palier": (190, 190, 190), "salon": (240, 170, 150),
          "salle_a_manger": (244, 196, 150), "cuisine": (170, 207, 150), "chambre": (247, 208, 176),
          "sdb": (150, 200, 232), "wc": (120, 180, 220), "koubba": (236, 160, 120), "hanout": (226, 150, 200),
          "makhzen": (204, 192, 170), "qahwa": (226, 150, 200)}
OTHER = (212, 212, 212)
WALL, PARTITION, DOOR, WINDOW, GAP = (20, 20, 20), (120, 120, 120), (210, 40, 40), (40, 90, 220), (255, 255, 255)
LABELS = {"wast_ed_dar": "wast ed dar", "bit_el_ma": "bit el ma", "bit_el_mouna": "mouna",
          "salle_a_manger": "s. a manger"}


def font(size: int):
    from PIL import ImageFont
    for name in ("/System/Library/Fonts/Helvetica.ttc", "Arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def interiors(specs: list, folder: Path, ctx=None) -> list:
    """(interior, outside) for every spec, planning a settlement the build does not hold (`ctx`: the build
    already loaded)."""
    from citygen.city import plan_city
    from citygen.export.lore import slug
    from citygen.interior.context import BuildContext, city_plan, load_build, resolve
    from citygen.interior.layout import plan_interior
    from citygen.interior.outside import Outside
    ctx = ctx or load_build(folder, log=lambda m: None)
    extra: dict = {}
    out = []
    for spec in specs:
        building, _, city = spec.partition("@")
        use = ctx
        if city:
            want = city.strip().lower()
            if not any(p.settlement.name.lower() == want or slug(p.settlement.name) == want for p in ctx.plans):
                if want not in extra:
                    s = next((s for s in ctx.world.settlements if s.name.lower() == want or slug(s.name) == want), None)
                    if s is None:
                        raise SystemExit(f"No settlement called {city!r} in this world.")
                    extra[want] = BuildContext(ctx.world, [plan_city(ctx.world, s)], s)
                use = extra[want]
        plan = city_plan(use, city or None)
        k = resolve(use, plan, building)
        outside = Outside(use, plan, k)
        out.append((plan_interior(outside, use.world.style), outside))
    return out


def panels(interior, outside) -> list:
    """(floor, label) of every panel of an interior: its storeys, then the roof when rooms stand on it."""
    out = [(st.floor, f"floor {st.floor}") for st in interior.storeys]
    if any(r.floor >= interior.floors for r in interior.rooms):
        out.append((interior.floors, "roof"))
    return out


def draw(items: list, out: Path) -> Path:
    from PIL import Image, ImageDraw
    rows = []
    for interior, outside in items:
        x0, y0, x1, y1 = outside.b.footprint.bounds
        rows.append((interior, outside, (x0 - 0.5, y0 - 0.5, x1 + 0.5, y1 + 0.5), panels(interior, outside)))
    widest = max(sum(b[2] - b[0] for _ in p) + 0 for _, _, b, p in rows)
    count = max(len(p) for _, _, _, p in rows)
    scale = min(SCALE, (WIDTH - PAD * (count + 1)) / max(widest, 1.0))
    width = int(min(WIDTH, max(PAD + sum((b[2] - b[0]) * scale + PAD for _ in p) for _, _, b, p in rows)))
    width = max(width, 640)
    height = int(sum(TITLE + (b[3] - b[1]) * scale + CAPTION + PAD for _, _, b, _ in rows) + PAD)
    image = Image.new("RGB", (width, height), (255, 255, 255))
    pen = ImageDraw.Draw(image)
    big, small = font(20), font(max(9, min(14, int(scale * 0.32))))
    y = PAD // 2
    for interior, outside, (bx0, by0, bx1, by1), ps in rows:
        pen.text((PAD, y + 4), title(interior), fill=(0, 0, 0), font=big)
        y += TITLE
        x = PAD
        for floor, label in ps:
            def at(px, py, x=x, y=y):
                return (x + (px - bx0) * scale, y + (by1 - py) * scale)
            panel(pen, interior, outside, floor, at, scale, small)
            pen.text((x, y + (by1 - by0) * scale + 4), label, fill=(60, 60, 60), font=small)
            x += (bx1 - bx0) * scale + PAD
        y += (by1 - by0) * scale + CAPTION + PAD
    out.parent.mkdir(parents=True, exist_ok=True)
    image.save(out)
    return out


def title(interior) -> str:
    home = interior.household
    family = f", the {home['family']} family" if home else ""
    floors = f"{interior.floors} floor" + ("s" if interior.floors != 1 else "")
    return f"{interior.city} No. {interior.building}: {interior.layout}, {floors}{family}"


def ring(poly, at) -> list:
    return [at(x, y) for x, y in poly.exterior.coords]


def fill(pen, poly, at, color, outline=None, width=1) -> None:
    from citygen.city.geo import polygons
    for p in polygons(poly):
        pen.polygon(ring(p, at), fill=color)
        for hole in p.interiors:
            pen.polygon([at(x, y) for x, y in hole.coords], fill=(255, 255, 255))
        if outline is not None:
            pen.line(ring(p, at), fill=outline, width=width)


def panel(pen, interior, outside, floor: int, at, scale: float, label_font) -> None:
    """One storey (or the roof): walls, rooms, openings, stairs, features and labels."""
    from shapely.ops import polylabel
    rooms = [r for r in interior.rooms if r.floor == floor]
    if floor < interior.floors:
        fill(pen, outside.b.footprint, at, WALL)
    else:
        lay = next((lay for m, lay in outside.roofs if m.main), None)
        if lay is not None and lay.band is not None:
            fill(pen, lay.band, at, WALL)
            fill(pen, lay.inner, at, (238, 238, 232))
    if floor > 0:
        court = next((r for r in interior.rooms if r.type == "wast_ed_dar" and r.open), None)
        if court is not None:
            fill(pen, court.polygon, at, (248, 248, 248))
    part = max(1, int(round(interior.walls["partition"] * scale)))
    for r in rooms:
        fill(pen, r.polygon, at, COLORS.get(r.type, OTHER))
    for r in rooms:
        if not (r.type == "wast_ed_dar" and r.open):
            pen.line(ring(r.polygon, at), fill=PARTITION, width=part)
        if r.alcove is not None:
            pen.line(ring(r.alcove, at), fill=(150, 90, 80), width=1)
    for o in interior.openings:
        if o.floor == floor:
            opening(pen, o, interior, at, scale)
    for s in interior.stairs:
        if s.floor <= floor <= max(s.top, s.floor) and (s.kind != "newel" or floor < interior.floors
                                                         or s.top >= interior.floors):
            stair(pen, s, at, scale)
    if floor == 0:
        for f in interior.features:
            if f["type"] in ("majel", "tree", "fesqiya"):
                rad = {"majel": 0.35, "tree": 0.9, "fesqiya": 0.7}[f["type"]] * scale
                cx, cy = at(f["x"], f["y"])
                color = {"majel": (60, 60, 160), "tree": (60, 140, 60), "fesqiya": (80, 150, 220)}[f["type"]]
                pen.ellipse((cx - rad, cy - rad, cx + rad, cy + rad), outline=color, width=2)
    for r in rooms:
        if r.polygon.area < 0.8:
            continue
        p = polylabel(r.polygon, tolerance=0.05)
        cx, cy = at(p.x, p.y)
        text = LABELS.get(r.type, r.type.replace("_", " "))
        if r.unit.startswith("flat "):
            text += " " + r.unit[5:]                       # the flat's number
        st = next((s for s in interior.storeys if s.floor == r.floor), None)
        if st is not None and r.z < st.z - 0.05:
            text += f" -{st.z - r.z:.1f} m"                # a sunken entry room (47.1)
        box = pen.textbbox((0, 0), text, font=label_font)
        pen.text((cx - (box[2] - box[0]) / 2, cy - (box[3] - box[1]) / 2), text, fill=(30, 30, 30), font=label_font)


def opening(pen, o, interior, at, scale: float) -> None:
    """A facade or court opening as a red (door) or blue (window) bar across its wall; an inner door or
    arch as a gap in the partition; an inner window as a thin blue bar."""
    if o.kind == "skylight":
        return
    front = (-math.sin(o.yaw), math.cos(o.yaw))
    along = (math.cos(o.yaw), math.sin(o.yaw))
    half = o.width / 2
    walls = interior.walls
    if o.kind in ("inner", "arch"):
        out, depth, color = walls["partition"] / 2 + 0.03, walls["partition"] / 2 + 0.03, GAP
    elif o.kind == "inner_window":
        out, depth, color = walls["partition"] / 2, walls["partition"] / 2, WINDOW
    elif o.kind in ("court_door", "court_window"):
        out, depth = 0.0, walls["court"]
        color = DOOR if o.kind == "court_door" else WINDOW
    else:
        out, depth = 0.0, walls["exterior"]
        color = DOOR if o.kind in ("door", "shop") else WINDOW
    pts = [(o.x + along[0] * s * half + front[0] * t, o.y + along[1] * s * half + front[1] * t)
           for s, t in ((-1, out), (1, out), (1, -depth), (-1, -depth))]
    pen.polygon([at(*p) for p in pts], fill=color)


def stair(pen, s, at, scale: float) -> None:
    """Hatching over the stair's floor and an arrow up from its door."""
    import numpy as np
    poly = s.polygon
    x0, y0, x1, y1 = poly.bounds
    from shapely.geometry import LineString
    step = 0.25
    for k in np.arange(-(y1 - y0), x1 - x0, step):
        line = LineString([(x0 + k, y0), (x0 + k + (y1 - y0), y1)]).intersection(poly)
        for g in getattr(line, "geoms", [line]):
            if g.geom_type == "LineString" and g.length > 0:
                pen.line([at(*c) for c in g.coords], fill=(90, 90, 90), width=1)
    pen.line(ring(poly, at), fill=(60, 60, 60), width=2)
    c = poly.centroid
    if s.door is not None:
        dx, dy, yaw = s.door
        sx, sy = (dx - math.cos(yaw) * 0.25, dy - math.sin(yaw) * 0.25) if s.kind == "newel" else (dx, dy)
        start, end = at(sx, sy), at(c.x, c.y)
    else:
        start, end = at(c.x, c.y - 0.4), at(c.x, c.y + 0.4)
    pen.line([start, end], fill=(0, 0, 0), width=2)
    ang = math.atan2(end[1] - start[1], end[0] - start[0])
    for side in (-1, 1):
        a = ang + math.pi + side * 0.45
        pen.line([end, (end[0] + math.cos(a) * 8, end[1] + math.sin(a) * 8)], fill=(0, 0, 0), width=2)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Floor plans of interiors as one PNG.")
    ap.add_argument("specs", nargs="+", help="building numbers or pick:<layout>[:<floors>], each with @CITY optional")
    ap.add_argument("--folder", help="a build folder (default: the latest build)")
    ap.add_argument("--out", default=str(ROOT / "output" / "checks" / "interior_plans.png"))
    args = ap.parse_args(argv)
    from citygen.interior import InteriorError
    if args.folder:
        folder = Path(args.folder)
    else:
        found = sorted((ROOT / "output").glob("*/summary.json"), key=lambda p: p.stat().st_mtime)
        if not found:
            raise SystemExit("No built world found in output/. Run: python -m citygen build --quick")
        folder = found[-1].parent
    try:
        items = interiors(args.specs, folder)
    except InteriorError as e:
        raise SystemExit(str(e)) from None
    print(draw(items, Path(args.out)))


if __name__ == "__main__":
    main()
