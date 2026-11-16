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
        lake = None if ctx.lake is None else ctx.lake.buffer(0.5 * aw + 3.0, quad_segs=3)
        if ctx.water is not None or lake is not None:   # a district cut by a river or a lake is one ring: coast, quay
            near = coast.buffer(1.0, quad_segs=2)       # and city limit are three streets
            near = near if lake is None else near.union(lake)
            borders = shapely.GeometryCollection(lines(borders.intersection(near)) + lines(borders.difference(near)))
            if ctx.banks is not None:                   # a bank apart from the limit it runs on to, not with the coast:
                quay = ctx.banks.boundary.buffer(1.0, quad_segs=2)   # the two would be one piece again
                borders = shapely.GeometryCollection([q for p in lines(borders)
                                                      for q in lines(p.intersection(quay)) + lines(p.difference(quay))])
        for piece in lines(borders):
            mid = piece.interpolate(0.5, normalized=True)
            if medina is not None and mid.distance(medina) < ring_offset(ctx) + 1.0:
                continue
            if mid.distance(coast) < 1.0:
                corniche.append(piece)
            elif mid.distance(edge) > 1.0 or (lake is not None and lake.contains(mid)):   # a lake's quay, not a limit
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


def _heading(line, p) -> float:
    """Direction of `line` (radians) at its point nearest p."""
    d = line.project(p)
    a, b = line.interpolate(max(d - 1.0, 0.0)), line.interpolate(min(d + 1.0, line.length))
    return math.atan2(b.y - a.y, b.x - a.x)


class _Mouths:
    """Where a row's tree would stand in a roadway: off every walk and inside the ribbon of another street, either
    one that crosses or joins the row's own at more than `[streets] tree_mouth_angle` degrees, or `tree_mouth_deep` m
    inside it at any angle (a street forking off). A street lying along the row's own (a ring road on the corniche)
    is no mouth: the tree stands by its edge. The outer `tree_mouth_edge` m of a ribbon do not count."""

    def __init__(self, streets, walks, cfg: dict):
        self.streets = streets
        self.angle = math.radians(float(cfg.get("tree_mouth_angle", 20.0)))
        self.deep = float(cfg.get("tree_mouth_deep", 3.0))
        self.reach = float(cfg.get("tree_walk_reach", 0.4))
        edge = float(cfg.get("tree_mouth_edge", 0.5))
        self.ribbons = shapely.STRtree([st.line.buffer(max(st.width / 2 - edge, 0.1), cap_style="flat")
                                        for st in streets])
        self.walks = shapely.STRtree([w.polygon for w in walks])

    def holds(self, k: int, p) -> bool:
        """Is p, a spot of street k's row, in a mouth?"""
        if len(self.walks.query(p, predicate="dwithin", distance=self.reach)):
            return False
        own = _heading(self.streets[k].line, p)
        for j in self.ribbons.query(p, predicate="within").tolist():
            st = self.streets[j]
            turn = abs(own - _heading(st.line, p)) % math.pi
            if j != k and (min(turn, math.pi - turn) > self.angle or st.width / 2 - st.line.distance(p) >= self.deep):
                return True
        return False


def street_trees(ctx, streets, walks=None) -> list:
    """Palms and shade trees along the boulevard and the seafront. With `walks` (the city's sidewalks and
    promenades) a spot in the mouth of a street that crosses or joins the row's own stays empty (`_Mouths`);
    its height is drawn all the same, so every other tree keeps its own."""
    rng = ctx.rng("street-trees")
    rows = {"boulevard": [(0.0, 9.0, "broadleaf")], "corniche": []}
    mouths = None
    if walks is not None and any(st.kind in rows for st in streets):
        mouths = _Mouths(streets, walks, ctx.style.get("streets", {}))
    out = []
    for k, st in enumerate(streets):
        if st.kind not in rows:
            continue
        side = st.width / 2 - 2.5
        for offset, spacing, kind in rows[st.kind] + [(side, 14.0, "palm"), (-side, 14.0, "palm")]:
            line = st.line.offset_curve(offset) if offset else st.line
            for d in np.arange(spacing / 2, line.length, spacing):
                p = line.interpolate(d)
                height = float(rng.uniform(7.0, 11.0))
                if mouths is None or not mouths.holds(k, p):
                    out.append(Tree(p.x, p.y, kind, height))
    return out


def view_spot(streets, center, kinds, reach: float = 600.0):
    """(eye, look) points of the eye-level camera on the longest street of the first of `kinds` with one
    longer than 60 m within `reach` of `center`, or None: 50 m along the street's longer side from the
    point nearest the center (stepped off the middle row of trees on a wide street). The street camera
    (`build.camera_views`) and the boulevard landmarks (prompt 32) share it."""
    for kind in kinds:  # the first kind with a long street near the center wins
        near = [st for st in streets if st.kind == kind and st.line.length > 60.0 and st.line.distance(center) < reach]
        if near:
            break
    else:
        return None
    street = max(near, key=lambda st: st.line.length)
    line = street.line
    if street.width > 16.0:  # wide street: step off the middle row of trees
        line = line.offset_curve(street.width / 4)
    d = min(max(line.project(center), 10.0), line.length - 10.0)
    step = 50.0 if line.length - d >= d else -50.0  # look along the longer side
    return line.interpolate(d), line.interpolate(min(max(d + step, 0.0), line.length))
