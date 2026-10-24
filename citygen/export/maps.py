"""2D map images (PNG): the whole country, and one city in detail."""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import MultiPolygon, Polygon

from ..city.openings import villa_lots
from ..terrain import classify

BIOME_RGB = np.array([(58, 120, 155), (232, 214, 168), (134, 160, 90), (191, 174, 120),
                      (223, 194, 140), (86, 111, 62), (156, 141, 121)], dtype=np.float64)
DISTRICT_RGB = {
    "medina": (236, 226, 204), "village": (236, 226, 204), "colonial": (240, 222, 190),
    "modern": (226, 222, 214), "residential": (238, 232, 220), "suburb": (225, 232, 210),
    "industrial": (214, 210, 204), "port": (208, 212, 218), "park": (170, 196, 130),
    "cemetery": (200, 206, 180),
}
BUILDING_RGB = {
    "medina": (150, 128, 100), "village": (160, 132, 100), "colonial": (186, 140, 96),
    "modern": (128, 128, 136), "residential": (170, 150, 128), "suburb": (190, 150, 120),
    "industrial": (120, 124, 132), "port": (110, 120, 140), "park": (140, 140, 120),
    "cemetery": (160, 160, 150),
}
TREE_RGB = {"citrus": (214, 136, 46)}   # bitter oranges (prompt 24); every other tree is green
GARDEN_RGB = (176, 204, 128)            # villa gardens (prompt 24)
ROAD_STYLE = {"national": ((196, 72, 52), 3.2), "regional": ((222, 150, 60), 2.2),
              "local": ((120, 110, 96), 1.2)}


def _font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10.1
        return ImageFont.load_default()


def _shade(terrain, x0, y0, x1, y1, w, h):
    """RGB array (h, w, 3) of biome colors with hill shading, north at the top."""
    xs = np.linspace(x0, x1, w)
    ys = np.linspace(y1, y0, h)
    X, Y = np.meshgrid(xs, ys)
    H = terrain.height(X, Y)
    px = (x1 - x0) / max(w - 1, 1)
    gy, gx = np.gradient(H, px)
    gy = -gy  # image rows go south
    slope = np.hypot(gx, gy)
    biome = classify(H, slope, terrain.moisture(X, Y, H))
    rgb = BIOME_RGB[biome]
    # sun from the north-west
    shade = np.clip(1.0 + (-gx * 0.7 + gy * 0.7) * 2.2, 0.55, 1.35)
    land = H > 0
    rgb[land] *= shade[land, None]
    depth = np.clip(-H / 120.0, 0.0, 1.0)
    rgb[~land] = (BIOME_RGB[0] * (1.15 - 0.45 * depth[..., None]))[~land]
    return np.clip(rgb, 0, 255).astype(np.uint8), H


def country_map(world, path, width: int = 1800) -> Path:
    size = world.size
    # the terrain is smooth at this scale: shade at low resolution, then enlarge
    img_arr, _ = _shade(world.terrain, 0.0, 0.0, size, size, min(width, 640), min(width, 640))
    img = Image.fromarray(img_arr).resize((width, width), Image.BICUBIC)
    draw = ImageDraw.Draw(img)
    k = width / size

    def px(x, y):
        return (x * k, (size - y) * k)

    for kind in ("local", "regional", "national"):
        color, w = ROAD_STYLE[kind]
        for r in world.roads:
            if r.kind == kind:
                draw.line([px(x, y) for x, y in r.coords], fill=color, width=max(1, round(w * width / 1800)))
    small, big = _font(max(10, width // 130)), _font(max(12, width // 85))
    for s in sorted(world.settlements, key=lambda s: -s.population):
        cx, cy = px(s.x, s.y)
        r = max(2.0, s.radius * k)
        fill = {"capital": (150, 30, 40), "city": (60, 40, 40), "town": (90, 70, 60), "village": (110, 100, 90)}[s.kind]
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(235, 225, 205), outline=fill, width=2 if s.kind != "village" else 1)
        if s.kind != "village":
            font = big if s.kind in ("capital", "city") else small
            label = s.name.upper() if s.kind == "capital" else s.name
            draw.text((cx + r + 3, cy - r - 2), label, fill=(30, 25, 25), font=font,
                      stroke_width=2, stroke_fill=(250, 246, 236))
    title = f"{world.name}  -  seed {world.seed}  -  {size / 1000:.0f} x {size / 1000:.0f} km"
    draw.text((16, 12), title, fill=(25, 25, 30), font=_font(max(14, width // 60)),
              stroke_width=3, stroke_fill=(250, 246, 236))
    _scale_bar(draw, k, width, width)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, optimize=True)
    return path


def _scale_bar(draw, k, w, h):
    meters = 10 ** math.floor(math.log10(0.2 * w / k))
    for m in (meters * 5, meters * 2, meters):
        if m * k < 0.25 * w:
            meters = m
            break
    x0, y0 = 20, h - 30
    draw.rectangle([x0 - 6, y0 - 22, x0 + meters * k + 60, y0 + 10], fill=(250, 246, 236))
    draw.line([(x0, y0), (x0 + meters * k, y0)], fill=(20, 20, 20), width=4)
    label = f"{meters / 1000:g} km" if meters >= 1000 else f"{meters:g} m"
    draw.text((x0, y0 - 20), label, fill=(20, 20, 20), font=_font(14))


def city_map(world, plan, path, meters_per_px: float | None = None, max_px: int = 4096) -> Path:
    minx, miny, maxx, maxy = plan.boundary.buffer(150).bounds
    span = max(maxx - minx, maxy - miny)
    mpp = meters_per_px or max(span / max_px, 0.6)
    w, h = int((maxx - minx) / mpp), int((maxy - miny) / mpp)
    scale = max(1, max(w, h) // 500)
    base, H = _shade(world.terrain, minx, miny, maxx, maxy, w // scale + 1, h // scale + 1)
    img = Image.fromarray(base).resize((w, h), Image.BILINEAR)
    # fade the countryside so the city stands out
    img = Image.blend(img, Image.new("RGB", (w, h), (246, 240, 228)), 0.35)
    draw = ImageDraw.Draw(img)

    def ring(coords):
        c = np.asarray(coords)
        return list(zip((c[:, 0] - minx) / mpp, (maxy - c[:, 1]) / mpp))

    def fill_poly(geom, color, outline=None):
        polys = geom.geoms if isinstance(geom, MultiPolygon) else [geom]
        for p in polys:
            if p.is_empty:
                continue
            draw.polygon(ring(p.exterior.coords), fill=color, outline=outline)

    for d in plan.districts:
        fill_poly(d.polygon, DISTRICT_RGB.get(d.kind, (230, 230, 230)))
    for st in sorted(plan.streets, key=lambda s: s.width):
        color = (250, 250, 248) if st.kind not in ("alley", "souk", "impasse") else (252, 246, 232)
        draw.line(ring(st.line.coords), fill=color, width=max(1, round(st.width / mpp)))
    kinds = {i: d.kind for i, d in enumerate(plan.districts)}
    for j in villa_lots(plan, [k for k, b in enumerate(plan.buildings) if b.kind == "villa"]).values():
        fill_poly(plan.parcels[j].polygon, GARDEN_RGB)
    for b in plan.buildings:
        color = BUILDING_RGB.get(kinds.get(b.district, "residential"), (150, 140, 130))
        if b.kind in ("mosque_hall", "minaret", "mosque_court"):
            color = (60, 120, 90)
        elif b.kind in ("wall", "tower"):
            color = (150, 110, 70)
        fill_poly(Polygon(b.footprint.exterior), color)
        for hole in b.footprint.interiors:
            draw.polygon(ring(hole.coords), fill=DISTRICT_RGB.get(kinds.get(b.district), (235, 225, 205)))
    tree_r = max(1.0, 2.2 / mpp)
    for t in plan.trees:
        cx, cy = (t.x - minx) / mpp, (maxy - t.y) / mpp
        draw.ellipse([cx - tree_r, cy - tree_r, cx + tree_r, cy + tree_r], fill=TREE_RGB.get(t.kind, (92, 130, 70)))
    font = _font(max(12, int(w / 110)))
    for d in plan.districts:
        if d.kind in ("medina", "village") or d.polygon.area < 60000:
            continue
        p = d.polygon.representative_point()
        draw.text(((p.x - minx) / mpp, (maxy - p.y) / mpp), d.name, fill=(70, 60, 50), font=font,
                  anchor="mm", stroke_width=2, stroke_fill=(250, 246, 236))
    for lm in plan.landmarks:
        draw.text(((lm.x - minx) / mpp, (maxy - lm.y) / mpp - 14), lm.name, fill=(20, 60, 45),
                  font=font, anchor="mm", stroke_width=2, stroke_fill=(250, 246, 236))
    s = plan.settlement
    draw.text((16, 12), f"{s.name}  -  {s.kind}, population {s.population:,}", fill=(25, 25, 30),
              font=_font(max(16, w // 55)), stroke_width=3, stroke_fill=(250, 246, 236))
    _scale_bar(draw, 1.0 / mpp, w, h)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, optimize=True)
    return path
