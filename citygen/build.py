"""One full build: world, then city plans, then maps, data files and 3D tiles in an output folder."""
from __future__ import annotations

import math
import time
from pathlib import Path

from shapely.geometry import Point, box

from .city import plan_city
from .export.lore import gazetteer, plan_json, slug, write_json
from .export.maps import city_map, country_map
from .mesh.tile import TileContext, export_tile
from .world import generate_world


def output_dir(cfg: dict, world) -> Path:
    return Path(cfg["build"]["output"]) / f"{slug(world.name)}-{world.seed}"


def select_area(world, area: str) -> tuple:
    """(region to export as tiles or None, settlement to focus on, settlements to plan)."""
    kind, _, arg = area.strip().partition(":")
    cfg = world.cfg["build"]
    focus = world.capital()
    if kind == "none":
        return None, focus, [focus]
    if kind == "all":
        region = box(0.0, 0.0, world.size, world.size)
    elif kind in ("capital", "city"):
        focus = world.capital() if kind == "capital" else world.find(arg)
        region = Point(focus.x, focus.y).buffer(focus.radius * 1.15)
    elif kind in ("capital-center", "city-center"):
        focus = world.capital() if kind == "capital-center" else world.find(arg)
        region = Point(focus.x, focus.y).buffer(float(cfg["center_radius"]))
    elif kind == "box":
        x0, y0, x1, y1 = (float(v) * 1000.0 for v in arg.split(","))
        region = box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))
        c = region.centroid
        focus = min(world.settlements, key=lambda s: math.hypot(s.x - c.x, s.y - c.y))
    else:
        raise ValueError(f"unknown area {area!r}; see [build] area in citygen/defaults.toml")
    needed = [s for s in world.settlements if region.distance(Point(s.x, s.y)) < s.radius * 1.35]
    return region, focus, needed


def camera_views(plan, terrain, reach: float = 600.0) -> dict:
    """Eye-level camera spots near the city center (generator coords): the boulevard, a souk."""
    center = Point(plan.settlement.x, plan.settlement.y)
    views = {}
    for name, kinds in (("street", ("boulevard", "arterial", "street")), ("souk", ("souk",))):
        for kind in kinds:  # the first kind with a long street near the center wins
            near = [st for st in plan.streets
                    if st.kind == kind and st.line.length > 60.0 and st.line.distance(center) < reach]
            if near:
                break
        else:
            continue
        street = max(near, key=lambda st: st.line.length)
        line = street.line
        if street.width > 16.0:  # wide street: step off the middle row of trees
            line = line.offset_curve(street.width / 4)
        d = min(max(line.project(center), 10.0), line.length - 10.0)
        step = 50.0 if line.length - d >= d else -50.0  # look along the longer side
        a, b = line.interpolate(d), line.interpolate(min(max(d + step, 0.0), line.length))
        ga, gb = float(terrain.height(a.x, a.y)), float(terrain.height(b.x, b.y))
        views[name] = {"cam": [round(a.x, 1), round(a.y, 1), round(ga + 1.7, 1)],
                       "look": [round(b.x, 1), round(b.y, 1), round(gb + 4.0, 1)]}
    return views


def tiles_for(region, tile: int, world_size: float) -> list:
    minx, miny, maxx, maxy = region.bounds
    last = int(math.ceil(world_size / tile)) - 1
    keys = []
    for i in range(max(0, int(minx // tile)), min(last, int(maxx // tile)) + 1):
        for j in range(max(0, int(miny // tile)), min(last, int(maxy // tile)) + 1):
            if region.intersects(box(i * tile, j * tile, (i + 1) * tile, (j + 1) * tile)):
                keys.append((i, j))
    return keys


def build(cfg: dict, area: str | None = None, log=print) -> Path:
    t0 = time.perf_counter()
    area = area or cfg["build"]["area"]
    world = generate_world(cfg)
    out = output_dir(cfg, world)
    out.mkdir(parents=True, exist_ok=True)
    log(f"world {world.name} (seed {world.seed}): {len(world.settlements)} settlements, "
        f"{len(world.roads)} roads [{time.perf_counter() - t0:.1f}s]")
    write_json(out / "world.json", world.to_json())
    country_map(world, out / "maps" / "country.png")

    region, focus, needed = select_area(world, area)
    plans = []
    for s in needed:
        plan = plan_city(world, s)
        plans.append(plan)
        st = plan.stats
        log(f"planned {s.name} ({s.kind}): {st['buildings']:,} buildings, {st['streets']:,} streets "
            f"[{st['seconds']}s]")
        write_json(out / "cities" / slug(s.name) / "plan.json", plan_json(plan))
        city_map(world, plan, out / "maps" / f"{slug(s.name)}.png")
    (out / "gazetteer.md").write_text(gazetteer(world, plans), encoding="utf-8")

    tiles = []
    if region is not None:
        tc = TileContext(world, plans)
        folder = out / "tiles"
        folder.mkdir(parents=True, exist_ok=True)
        size = tc.size
        keys = tiles_for(region, size, world.size)
        keys.sort(key=lambda k: math.hypot((k[0] + 0.5) * size - focus.x, (k[1] + 0.5) * size - focus.y))
        step = max(1, len(keys) // 10)
        for n, (i, j) in enumerate(keys, 1):
            tiles.append(export_tile(tc, i, j, folder))
            if n % step == 0 or n == len(keys):
                log(f"tiles {n}/{len(keys)} [{time.perf_counter() - t0:.0f}s]")
        write_json(folder / "index.json", {
            "format": "citygen-tiles/1", "seed": world.seed, "world_name": world.name,
            "tile_size": size, "world_size": [world.size, world.size],
            "focus": {"x": round(focus.x, 1), "y": round(focus.y, 1),
                      "z": round(float(world.terrain.height(focus.x, focus.y)), 1), "name": focus.name},
            "views": next((camera_views(p, world.terrain) for p in plans if p.settlement is focus), {}),
            "tiles": tiles})

    summary = {
        "world": world.name, "seed": world.seed, "size_km": world.size / 1000.0, "area": area,
        "settlements": {k: sum(s.kind == k for s in world.settlements) for k in ("capital", "city", "town", "village")},
        "roads": len(world.roads),
        "plans": [{"name": p.settlement.name, "kind": p.settlement.kind, **p.stats} for p in plans],
        "tiles": {"count": len(tiles), "triangles": sum(t["triangles"] for t in tiles),
                  "megabytes": round(sum(t["bytes"] for t in tiles) / 1e6, 1)},
        "seconds": round(time.perf_counter() - t0, 1),
    }
    write_json(out / "summary.json", summary)
    log(f"done in {summary['seconds']}s -> {out}")
    return out
