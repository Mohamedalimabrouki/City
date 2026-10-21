"""Buildings for each parcel, chosen by district rules from the style pack."""
from __future__ import annotations

import math

import numpy as np
from shapely.geometry import Point

from ..mesh.builder import rectangle
from ..rng import weighted
from .geo import frame, jittered_grid, largest
from .model import Building, Landmark, Tree


def _inset(poly, d):
    return largest(poly.buffer(-d, join_style="mitre")) if d > 0 else poly


def courtyard_house(parcel, dc, rng, did, trees) -> list:
    if rng.random() < float(dc.get("empty_share", 0.0)):
        c = parcel.polygon.representative_point()
        trees.append(Tree(c.x, c.y, "olive" if rng.random() < 0.6 else "palm", rng.uniform(4.0, 7.0)))
        return []
    fp = _inset(parcel.polygon, 0.15)
    if fp is None or fp.area < 12.0:
        return []
    floors = int(weighted(rng, dc["floors"]))
    wall, roof = weighted(rng, dc["walls"]), weighted(rng, dc["roofs"])
    if rng.random() < float(dc.get("dome_chance", 0.0)) and fp.area < 450.0:
        cx, cy, length, width, _ = frame(fp)
        mat = "dome_green" if rng.random() < 0.3 else "dome_white"
        return [Building(fp, "domed", did, 4.4, "lime_white", roof, 1,
                         domes=[(cx, cy, 0.38 * min(length, width), mat)])]
    if fp.area >= float(dc.get("courtyard_min_area", 1e9)):
        court = _inset(fp, max(2.8, 0.27 * math.sqrt(fp.area)))
        if court is not None and court.area >= 9.0:
            court = court.simplify(0.3)
            with_court = fp.difference(court)
            if with_court.geom_type == "Polygon" and with_court.is_valid:
                fp = with_court
                if rng.random() < float(dc.get("courtyard_tree_chance", 0.0)) and court.area > 20.0:
                    c = court.centroid
                    trees.append(Tree(c.x, c.y, "broadleaf", rng.uniform(4.0, 6.5)))
    return [Building(fp, "house", did, floors * float(dc["floor_height"]), wall, roof, floors)]


def street_building(parcel, dc, rng, did, kind) -> list:
    if dc.get("perimeter") and not parcel.frontage:
        return []
    fp = _inset(parcel.polygon, 0.15)
    if fp is None or fp.area < 15.0:
        return []
    floors = int(weighted(rng, dc["floors"]))
    return [Building(fp, kind, did, floors * float(dc["floor_height"]),
                     weighted(rng, dc["walls"]), weighted(rng, dc["roofs"]), floors)]


def slab(parcel, dc, rng, did) -> list:
    inner = _inset(parcel.polygon, float(dc["setback"]))
    if inner is None:
        return []
    cx, cy, length, width, angle = frame(inner)
    length = min(length, float(dc["slab_max_length"]))
    depth = min(width, float(dc["slab_depth"]))
    if length < 12.0 or depth < 8.0:
        return []
    rect = rectangle(cx, cy, length, depth, angle)
    fp = largest(rect.intersection(inner))
    if fp is None or fp.area < 0.7 * rect.area:
        return []
    floors = int(weighted(rng, dc["floors"]))
    return [Building(fp, "apartments", did, floors * float(dc["floor_height"]),
                     weighted(rng, dc["walls"]), weighted(rng, dc["roofs"]), floors)]


def villa(parcel, dc, rng, did, trees) -> list:
    inner = _inset(parcel.polygon, float(dc["setback"]))
    if inner is None:
        return []
    cx, cy, length, width, angle = frame(inner)
    lmax, wmax = dc["house_max"]
    lx = min(length, float(lmax)) * rng.uniform(0.72, 1.0)
    wy = min(width, float(wmax)) * rng.uniform(0.72, 1.0)
    if lx < 7.0 or wy < 6.0:
        return []
    rect = rectangle(cx, cy, lx, wy, angle)
    fp = largest(rect.intersection(inner))
    if fp is None or fp.area < 40.0:
        return []
    floors = int(weighted(rng, dc["floors"]))
    b = Building(fp, "villa", did, floors * float(dc["floor_height"]), weighted(rng, dc["walls"]),
                 weighted(rng, dc["roofs"]), floors)
    if fp.area > 0.98 * rect.area and rng.random() < float(dc.get("hip_roof_chance", 0.0)):
        b.roof_shape, b.roof = "hip", "roof_tile"
    lo, hi = dc.get("garden_trees", [0, 0])
    garden = parcel.polygon.difference(fp.buffer(2.5))
    for _ in range(int(rng.integers(int(lo), int(hi) + 1))):
        p = _random_point(garden, rng)
        if p is not None:
            kind = "palm" if rng.random() < 0.3 else ("olive" if rng.random() < 0.4 else "broadleaf")
            trees.append(Tree(p.x, p.y, kind, rng.uniform(4.0, 9.0)))
    return [b]


def shed(parcel, dc, rng, did) -> list:
    inner = _inset(parcel.polygon, float(dc["setback"]))
    if inner is None:
        return []
    cx, cy, length, width, angle = frame(inner)
    rect = rectangle(cx, cy, length * 0.9, width * 0.85, angle)
    fp = largest(rect.intersection(inner))
    if fp is None or fp.area < 60.0:
        return []
    lo, hi = dc["height"]
    h = float(rng.uniform(lo, hi))
    return [Building(fp, "shed", did, h, weighted(rng, dc["walls"]), weighted(rng, dc["roofs"]),
                     max(1, int(h // 4.5)))]


def _random_point(poly, rng, tries: int = 12):
    if poly is None or poly.is_empty:
        return None
    minx, miny, maxx, maxy = poly.bounds
    for _ in range(tries):
        p = Point(rng.uniform(minx, maxx), rng.uniform(miny, maxy))
        if poly.contains(p):
            return p
    return None


def make_buildings(ctx, parcels, districts, skip=frozenset()) -> tuple:
    """Buildings and trees for every parcel, district by district (each with its own random stream)."""
    buildings, trees = [], []
    by_district: dict = {}
    for k, p in enumerate(parcels):
        if k not in skip:
            by_district.setdefault(p.district, []).append(p)
    for did, group in sorted(by_district.items()):
        kind = districts[did].kind
        dc = ctx.style["district"][kind]
        rng = ctx.rng("buildings", did)
        for parcel in group:
            if kind in ("medina", "village"):
                buildings += courtyard_house(parcel, dc, rng, did, trees)
            elif kind == "colonial":
                buildings += street_building(parcel, dc, rng, did, "apartments")
            elif kind == "residential":
                buildings += street_building(parcel, dc, rng, did, "house")
            elif kind == "modern":
                buildings += slab(parcel, dc, rng, did)
            elif kind == "suburb":
                buildings += villa(parcel, dc, rng, did, trees)
            elif kind in ("industrial", "port"):
                buildings += shed(parcel, dc, rng, did)
    return buildings, trees


def neighborhood_mosques(ctx, districts, parcels) -> tuple:
    """Some neighborhoods get a small mosque on a lot near their middle.

    Returns (buildings, landmarks, indices of the parcels used).
    """
    rng = ctx.rng("neighborhood-mosques")
    chance = float(ctx.kc.get("mosque_chance", 0.0))
    u = np.array([math.cos(ctx.qibla), math.sin(ctx.qibla)])
    v = np.array([-u[1], u[0]])
    buildings, landmarks, used = [], [], set()
    for d in districts:
        if d.kind not in ("residential", "modern", "suburb", "colonial") or rng.random() >= chance:
            continue
        c = d.polygon.centroid
        lots = [k for k, p in enumerate(parcels)
                if p.district == d.id and p.polygon.area >= 320.0 and p.frontage]
        if not lots:
            continue
        k = min(lots, key=lambda k: parcels[k].polygon.centroid.distance(c))
        lot = parcels[k].polygon
        size = min(math.sqrt(lot.area) * 0.72, 24.0)
        pc = lot.centroid
        inner = _inset(lot, 0.8)
        hall = largest(rectangle(pc.x, pc.y, size, size, ctx.qibla).intersection(inner)) if inner else None
        if hall is None or hall.area < 80.0:
            continue
        hc = hall.centroid
        side = 3.6
        tower = None
        for su, sv in ((-1, 1), (-1, -1), (1, 1), (1, -1)):  # back corners first, then front
            m = np.array([hc.x, hc.y]) + su * u * (size / 2 - side / 2) + sv * v * (size / 2 - side / 2)
            fp = rectangle(m[0], m[1], side, side, ctx.qibla)
            if inner.contains(fp):
                tower = fp
                break
        if tower is None:
            continue
        buildings.append(Building(hall, "mosque_hall", d.id, 6.5, "lime_white", "roof_white", 1,
                                  domes=[(hc.x, hc.y, 0.26 * size, "dome_white")]))
        buildings.append(Building(tower, "minaret", d.id,
                                  float(rng.uniform(18.0, 26.0)), "lime_white", "lime_white", 1,
                                  top={"side": side * 0.62, "height": 3.2, "material": "lime_white",
                                       "cap": "dome_green"}))
        used.add(k)
        landmarks.append(Landmark("mosque", ctx.namer.district("mosque"), hc.x, hc.y))
    return buildings, landmarks, used


def cemetery_and_parks(ctx, districts, blocks) -> tuple:
    rng = ctx.rng("green")
    buildings, trees = [], []
    for block, did in blocks:
        d = districts[did]
        if d.kind == "park":
            step = float(ctx.style["district"]["park"]["tree_spacing"])
            for x, y in jittered_grid(block, step, rng, jitter=0.35):
                kind = "palm" if rng.random() < 0.15 else "broadleaf"
                trees.append(Tree(x, y, kind, rng.uniform(6.0, 12.0)))
        elif d.kind == "cemetery":
            dc = ctx.style["district"]["cemetery"]
            for x, y in jittered_grid(block, float(dc["tree_spacing"]), rng, jitter=0.35):
                trees.append(Tree(x, y, "cypress", rng.uniform(8.0, 13.0)))
            for _ in range(int(dc.get("marabouts", 0))):
                p = _random_point(block.buffer(-6.0), rng)
                if p is not None:
                    a = rng.uniform(0, math.pi)
                    fp = rectangle(p.x, p.y, 7.0, 7.0, a)
                    buildings.append(Building(fp, "marabout", did, 4.2, "lime_white", "roof_white", 1,
                                              domes=[(p.x, p.y, 2.9, "dome_white")]))
    return buildings, trees
