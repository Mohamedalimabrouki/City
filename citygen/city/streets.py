"""Streets outside the old town: arterials, ring road, boulevard, road links and local grids."""
from __future__ import annotations

import math

import numpy as np
import shapely
from shapely import affinity
from shapely.geometry import LineString, MultiLineString, Point
from shapely.ops import nearest_points, unary_union

from .geo import lines, polygons, ray_exit
from .medina import ring_offset
from .model import Street, Tree


def major_streets(ctx, districts, medina, axis: float, land) -> list:
    s, kc = ctx.s, ctx.kc
    aw = float(kc["arterial_width"])
    out = []
    outer = [d for d in districts if d.kind not in ("medina", "village")]
    if len(outer) > 1:
        coast = land.boundary
        edge = ctx.boundary.exterior
        borders = unary_union([d.polygon.boundary for d in outer])
        corniche, arterial = [], []
        for piece in lines(borders):
            mid = piece.interpolate(0.5, normalized=True)
            if medina is not None and mid.distance(medina) < ring_offset(ctx) + 1.0:
                continue
            if mid.distance(coast) < 1.0:
                corniche.append(piece)
            elif mid.distance(edge) > 1.0:
                arterial.append(piece)
        for kind, group in (("arterial", arterial), ("corniche", corniche)):
            if group:
                for line in lines(shapely.line_merge(MultiLineString(group))):
                    out.append(Street(kind, aw, line))
    if medina is not None and medina is not ctx.boundary:
        ring = medina.buffer(ring_offset(ctx)).exterior
        for line in lines(ring.intersection(ctx.boundary)):
            if line.length > 30.0:
                out.append(Street("ring", aw, line))
    bw = float(kc.get("boulevard_width", 0.0))
    colonial = [d.polygon for d in districts if d.kind in ("colonial", "port")]
    if bw > 0 and colonial:
        start = ray_exit(s.x, s.y, axis, medina, 4 * s.radius) if medina is not None else Point(s.x, s.y)
        if start is not None and medina is not None:
            gap = ring_offset(ctx)  # begin on the ring road, clear of the ramparts
            start = Point(start.x + gap * math.cos(axis), start.y + gap * math.sin(axis))
        if start is not None:
            reach = kc.get("colonial_reach", 0.45) * s.radius * 1.6
            ray = LineString([(start.x, start.y),
                              (start.x + reach * math.cos(axis), start.y + reach * math.sin(axis))])
            inside = ray.intersection(unary_union(colonial).buffer(5.0)).intersection(ctx.boundary)
            parts = [p for p in lines(inside) if p.distance(start) < 60.0]
            if parts:
                out.append(Street("boulevard", bw, max(parts, key=lambda p: p.length)))
    return out


def road_links(ctx, roads, streets) -> list:
    """Join the country roads that reach the city limit to the nearest city street."""
    if not streets:
        return []
    network = unary_union([st.line for st in streets if st.kind in
                           ("arterial", "ring", "boulevard", "corniche", "souk")] or [st.line for st in streets])
    edge = ctx.boundary.exterior
    out = []
    for r in roads:
        line = LineString(r.coords)
        if not line.intersects(edge):
            continue
        hit = line.intersection(edge)
        for p in getattr(hit, "geoms", [hit]):
            if p.geom_type != "Point":
                continue
            q = nearest_points(network, p)[0]
            if 1.0 < p.distance(q) < ctx.s.radius:
                out.append(Street("connector", min(r.width, float(ctx.kc["arterial_width"])),
                                  LineString([(p.x, p.y), (q.x, q.y)])))
    return out


def grid_lines(poly, angle: float, a: float, b: float, rng) -> list:
    """Street center lines of a rotated grid (blocks about a by b meters) clipped to poly."""
    c = poly.centroid
    rot = affinity.rotate(poly, -angle, origin=c, use_radians=True)
    minx, miny, maxx, maxy = rot.bounds
    segs = []
    x = minx + rng.uniform(0.35, 0.75) * a
    while x < maxx:
        segs.append(((x, miny - 1.0), (x, maxy + 1.0)))
        x += a * rng.uniform(0.85, 1.15)
    y = miny + rng.uniform(0.35, 0.75) * b
    while y < maxy:
        segs.append(((minx - 1.0, y), (maxx + 1.0, y)))
        y += b * rng.uniform(0.85, 1.15)
    if not segs:
        return []
    clipped = MultiLineString(segs).intersection(rot)
    return [affinity.rotate(g, angle, origin=c, use_radians=True) for g in lines(clipped)]


def local_streets(ctx, districts) -> list:
    out = []
    for d in districts:
        dc = ctx.style["district"].get(d.kind, {})
        if "grid" not in dc:
            continue
        rng = ctx.rng("grid", d.id)
        a, b = dc["grid"]
        for poly in polygons(d.polygon):
            for line in grid_lines(poly, d.angle, float(a), float(b), rng):
                if line.length > 20.0:
                    out.append(Street("street", float(dc["street_width"]), line))
    return out


def street_trees(ctx, streets) -> list:
    """Palms and shade trees along the boulevard and the seafront."""
    rng = ctx.rng("street-trees")
    rows = {"boulevard": [(0.0, 9.0, "broadleaf")], "corniche": []}
    out = []
    for st in streets:
        if st.kind not in rows:
            continue
        side = st.width / 2 - 2.5
        for offset, spacing, kind in rows[st.kind] + [(side, 14.0, "palm"), (-side, 14.0, "palm")]:
            line = st.line.offset_curve(offset) if offset else st.line
            for d in np.arange(spacing / 2, line.length, spacing):
                p = line.interpolate(d)
                out.append(Tree(p.x, p.y, kind, float(rng.uniform(7.0, 11.0))))
    return out
