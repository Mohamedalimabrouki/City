"""City footprint and districts: land, city limit, old town, neighborhoods and their kinds."""
from __future__ import annotations

import math

import contourpy
import numpy as np
import shapely
from shapely.geometry import MultiPoint, Point, Polygon
from shapely.ops import unary_union

from ..names import NameMaker
from ..noise import Perlin
from ..rng import weighted
from .geo import frame, largest, noisy_loop, polygons, scatter
from .model import District


def land_near(terrain, x: float, y: float, radius: float):
    """Land (above 0.8 m) within `radius` of a point, as a polygon traced from the height field."""
    step = max(6.0, radius / 250.0)
    n = int(2 * radius / step) + 1
    xs = np.linspace(x - radius, x + radius, n)
    ys = np.linspace(y - radius, y + radius, n)
    X, Y = np.meshgrid(xs, ys)
    H = terrain.height(X, Y)
    if H.min() > 0.8:
        return Polygon([(xs[0], ys[0]), (xs[-1], ys[0]), (xs[-1], ys[-1]), (xs[0], ys[-1])])
    gen = contourpy.contour_generator(xs, ys, H, fill_type=contourpy.FillType.OuterOffset)
    pts, offsets = gen.filled(0.8, 1e9)
    parts = []
    for p, o in zip(pts, offsets):
        rings = [p[o[k]:o[k + 1]] for k in range(len(o) - 1)]
        poly = Polygon(rings[0], [r for r in rings[1:] if len(r) >= 4]).buffer(0)
        if poly.area > 3000.0:
            parts.append(poly)
    return unary_union(parts).simplify(1.0)


def city_boundary(ctx, land):
    s = ctx.s
    loop = noisy_loop(s.x, s.y, s.radius, Perlin(ctx.seed, "boundary", s.id), n=80, amp=0.12)
    inside = loop.intersection(land)
    parts = polygons(inside)
    center = Point(s.x, s.y)
    for p in parts:
        if p.buffer(1.0).contains(center):
            return p
    return largest(inside) or loop


def main_axis(ctx, roads) -> float:
    """Direction (radians) of the city's main axis: toward the sea, else along its busiest road."""
    s, terrain = ctx.s, ctx.world.terrain
    t = np.linspace(0.0, 2 * math.pi, 72, endpoint=False)
    for frac in (0.6, 1.0, 1.5):
        h = terrain.height(s.x + frac * s.radius * np.cos(t), s.y + frac * s.radius * np.sin(t))
        wet = h < 0.5
        if wet.any():
            return math.atan2(np.sin(t[wet]).sum(), np.cos(t[wet]).sum())
    best = None
    for r in roads:
        if s.id in r.ends:
            other = r.coords[-1] if r.ends[0] == s.id else r.coords[0]
            rank = {"national": 0, "regional": 1, "local": 2}[r.kind]
            if best is None or rank < best[0]:
                best = (rank, math.atan2(other[1] - s.y, other[0] - s.x))
    return best[1] if best else ctx.rng("axis").uniform(0.0, 2 * math.pi)


def medina_outline(ctx, boundary):
    """The old town. For villages the whole settlement is traditional."""
    s, kc = ctx.s, ctx.kc
    if kc["medina_radius"] >= 1.0:
        return boundary
    rng = ctx.rng("medina-shape")
    shape = noisy_loop(s.x, s.y, kc["medina_radius"] * s.radius, Perlin(ctx.seed, "medina", s.id),
                       n=48, amp=0.15, aspect=rng.uniform(0.68, 0.95), rotation=rng.uniform(0, math.pi))
    medina = largest(shape.intersection(boundary.buffer(-8.0)))
    if medina is None or medina.area < 5000.0:
        return None
    # round off sharp inward notches: ramparts and their ring road follow smooth curves
    return largest(medina.buffer(15.0, quad_segs=4).buffer(-15.0, quad_segs=4)).simplify(0.5)


def neighborhoods(ctx, boundary, medina) -> list:
    """Voronoi neighborhoods outside the old town. Their borders become the main streets."""
    s, kc = ctx.s, ctx.kc
    if medina is not None:
        from .medina import ring_offset
        rest = boundary.difference(medina.buffer(ring_offset(ctx)))
    else:
        rest = boundary
    if rest.area < 4000.0:
        return []
    rng = ctx.rng("neighborhoods")
    s0, s1 = kc["neighborhood_spacing"]

    def spacing(x, y):
        r = min(1.0, math.hypot(x - s.x, y - s.y) / s.radius)
        return s0 + (s1 - s0) * r

    attempts = int(rest.area / (s0 * s0) * 8) + 20
    seeds = scatter(rest, spacing, rng, attempts)
    if len(seeds) < 2:
        return [District(0, "", "", rest)]
    cells = shapely.voronoi_polygons(MultiPoint(seeds), extend_to=boundary.envelope.buffer(2 * s1))
    out = []
    for cell in cells.geoms:
        for piece in polygons(cell.intersection(rest)):
            if piece.area > 6000.0 and not piece.buffer(-12.0).is_empty:
                out.append(District(len(out), "", "", piece))
    return out


def assign_kinds(ctx, districts, medina, axis: float, land) -> None:
    """Decide what each neighborhood is (old town, colonial, port, park...) and name it."""
    s, kc = ctx.s, ctx.kc
    rng = ctx.rng("district-kinds")
    ax, ay = math.cos(axis), math.sin(axis)
    coast = land.boundary
    info = []
    for d in districts:
        c = d.polygon.centroid
        dx, dy = c.x - s.x, c.y - s.y
        dist = math.hypot(dx, dy)
        info.append({"r": dist / s.radius, "cos": (dx * ax + dy * ay) / max(dist, 1.0),
                     "near_medina": medina is not None and d.polygon.distance(medina) < 60.0,
                     "coast": d.polygon.distance(coast) < 60.0, "area": d.polygon.area,
                     "h": float(ctx.world.terrain.height(c.x, c.y))})
    free = set(range(len(districts)))

    def take(candidates, count, key):
        chosen = sorted(candidates, key=key)[:count]
        for i in chosen:
            free.discard(i)
        return chosen

    kinds = {}
    if kc.get("port") and s.coastal:
        # along the shore but not touching the old town: the colonial quarter goes in between
        cand = [i for i in free if info[i]["coast"] and not info[i]["near_medina"]
                and info[i]["r"] > 0.25 and info[i]["cos"] > -0.3]
        for i in take(cand, 2 if s.kind == "capital" else 1, lambda i: -info[i]["cos"] + info[i]["r"]):
            kinds[i] = "port"
    if kc.get("colonial"):
        # the newer quarter grew outside the walls, toward the port and along the main axis
        reach = kc.get("colonial_reach", 0.45)
        count = max(1, round(kc.get("colonial_share", 0.1) * len(districts)))
        cand = [i for i in free if info[i]["r"] < reach and info[i]["cos"] > -0.1]
        if not cand:
            cand = [i for i in free if info[i]["near_medina"]]
        for i in take(cand, count, lambda i: info[i]["r"] - 0.5 * info[i]["cos"]):
            kinds[i] = "colonial"
    if kc.get("cemetery"):
        cand = [i for i in free if info[i]["near_medina"] and info[i]["cos"] < 0.0 and info[i]["area"] < 6e5]
        for i in take(cand, 1, lambda i: info[i]["area"]):
            kinds[i] = "cemetery"
    for _ in range(int(kc.get("parks", 0))):
        cand = [i for i in free if 0.15 < info[i]["r"] < 0.75]
        for i in take(cand, 1, lambda i: -(info[i]["h"] + rng.uniform(0, 25))):
            kinds[i] = "park"
    n_ind = round(kc.get("industrial_share", 0.0) * len(districts))
    cand = [i for i in free if info[i]["r"] > 0.5]
    for i in take(cand, n_ind, lambda i: info[i]["cos"] + rng.uniform(0, 0.6)):
        kinds[i] = "industrial"
    for i in sorted(free):
        for ring in kc["rings"]:
            if info[i]["r"] < ring["until"]:
                kinds[i] = weighted(rng, ring["mix"])
                break
        else:
            kinds[i] = "suburb"

    namer = NameMaker(ctx.style, ctx.rng("district-names"))
    namer.used.update(t.name.split()[-1] for t in ctx.world.settlements)
    for i, d in enumerate(districts):
        d.kind = kinds[i]
        d.name = namer.district(d.kind)
        if d.kind == "colonial":
            d.angle = axis
        else:
            d.angle = frame(d.polygon)[4] + rng.uniform(-0.12, 0.12)
