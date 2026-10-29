"""Straight cuts of a storey along the axes of a frame (SPEC 6c "Walls" and "Layout engine").

Every cut goes through `free_cut`, which moves it until its partition meets the walls `clear` of every
opening (or drops it); `absorb` then joins slivers and undersized rooms to the neighbour they share the
longest boundary with. Nothing here raises: odd lots give fewer, bigger rooms. Polygons are snapped to a
1 micrometer grid, so the two sides of a cut union back cleanly.
"""
from __future__ import annotations

import math

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import polylabel

from ..city.geo import frame as oriented
from ..city.geo import polygons

GRID = 1e-6       # meters: the snapping grid of every cut and union
REACH = 1e4       # meters: half the size of a half plane
TOUCH = 1e-4      # meters: boundaries this close count as shared
EMPTY = 1e-3      # m2: a piece smaller than this is no piece (a numerical sliver)
SLIVER = 0.9      # meters: a room narrower than this with no other neighbour joins a stair cell or court


class Frame:
    """Axes for cuts: u along `angle` (the long side), v across it, both from (cx, cy)."""

    def __init__(self, cx: float, cy: float, angle: float):
        self.c = np.array([cx, cy], dtype=float)
        self.angle = float(angle)
        self.u = np.array([math.cos(angle), math.sin(angle)])
        self.v = np.array([-self.u[1], self.u[0]])

    @classmethod
    def of(cls, poly) -> "Frame":
        """The frame of a polygon's oriented bounding box (`city.geo.frame`)."""
        cx, cy, _, _, angle = oriented(poly)
        return cls(cx, cy, angle)

    def local(self, xy) -> np.ndarray:
        """World points (..., 2) as (u, v)."""
        d = np.asarray(xy, dtype=float) - self.c
        return np.stack([d @ self.u, d @ self.v], axis=-1)

    def world(self, u: float, v: float) -> np.ndarray:
        return self.c + self.u * u + self.v * v

    def bounds(self, geom) -> tuple:
        """(u0, v0, u1, v1) of a geometry in this frame."""
        uv = self.local(shapely.get_coordinates(geom))
        return float(uv[:, 0].min()), float(uv[:, 1].min()), float(uv[:, 0].max()), float(uv[:, 1].max())

    def rect(self, u0: float, v0: float, u1: float, v1: float) -> Polygon:
        """The rectangle [u0, u1] x [v0, v1] of this frame, in world coordinates."""
        return Polygon([self.world(u0, v0), self.world(u1, v0), self.world(u1, v1), self.world(u0, v1)])

    def rects(self, u0, v0, u1, v1) -> np.ndarray:
        """Many rectangles at once (arrays of the four bounds), as an array of world Polygons."""
        u0, v0, u1, v1 = (np.asarray(x, dtype=float) for x in (u0, v0, u1, v1))
        us = np.stack([u0, u1, u1, u0, u0], axis=-1)
        vs = np.stack([v0, v0, v1, v1, v0], axis=-1)
        xy = self.c + us[..., None] * self.u + vs[..., None] * self.v
        return shapely.polygons(xy)

    def side(self, axis: int, at: float, upper: bool) -> Polygon:
        """The half plane beyond (upper) or before the line {u, v}[axis] = at."""
        lo, hi = (at, REACH) if upper else (-REACH, at)
        return self.rect(lo, -REACH, hi, REACH) if axis == 0 else self.rect(-REACH, lo, REACH, hi)

    def line(self, axis: int, at: float) -> LineString:
        """The line {u, v}[axis] = at."""
        if axis == 0:
            return LineString([self.world(at, -REACH), self.world(at, REACH)])
        return LineString([self.world(-REACH, at), self.world(REACH, at)])

    def axis_dir(self, axis: int) -> np.ndarray:
        return self.u if axis == 0 else self.v


def snap(geom):
    """A geometry on the 1 micrometer grid (valid output)."""
    return shapely.set_precision(geom, GRID)


def parts(geom) -> list:
    """The polygons of a geometry larger than `EMPTY`."""
    return [p for p in polygons(geom) if p.area > EMPTY]


def solid(geom):
    """The polygons of a geometry (larger than `EMPTY`) as one geometry, on the grid; empty when none."""
    got = parts(snap(geom))
    return shapely.union_all(got) if got else Polygon()


def polygonal(geom):
    """A geometry as it is when polygonal, else its polygons (`solid`)."""
    return geom if geom.geom_type in ("Polygon", "MultiPolygon") else solid(geom)


def clip(a, b):
    """`a` inside `b`, polygons only (lines and points of the overlay, and of its inputs, dropped)."""
    return solid(shapely.intersection(polygonal(a), polygonal(b), grid_size=GRID))


def cut(poly, frame: Frame, axis: int, at: float) -> tuple:
    """(before, after): the polygons of `poly` on both sides of the line {u, v}[axis] = at."""
    lo = parts(shapely.intersection(poly, frame.side(axis, at, False), grid_size=GRID))
    hi = parts(shapely.intersection(poly, frame.side(axis, at, True), grid_size=GRID))
    return lo, hi


def union(a, b):
    """Two touching pieces as one polygon (None when they only meet at a point)."""
    for grow in (0.0, 1e-5):
        if grow:          # pieces cut apart by different operations may lie a few micrometers apart
            a, b = a.buffer(grow, join_style="mitre"), b.buffer(grow, join_style="mitre")
        out = shapely.union(a, b, grid_size=GRID)
        if grow:
            out = snap(out.buffer(-grow, join_style="mitre"))
        got = sorted(polygons(out), key=lambda p: -p.area)
        if got and all(p.area < EMPTY for p in got[1:]):
            return got[0]
    return None


_WIDTHS: dict = {}


def width(poly) -> float:
    """Twice the radius of the largest circle inside `poly` (`shapely.ops.polylabel`); remembered per shape
    (the spine tries many plans of the same cells)."""
    if poly.is_empty or poly.area <= EMPTY:
        return 0.0
    key = shapely.to_wkb(poly)
    got = _WIDTHS.get(key)
    if got is None:
        p = polylabel(poly, tolerance=0.02)
        got = 2.0 * float(poly.exterior.distance(p) if not poly.interiors else poly.boundary.distance(p))
        if len(_WIDTHS) > 50000:
            _WIDTHS.clear()
        _WIDTHS[key] = got
    return got


def near(a, b) -> bool:
    """True when the bounding boxes of two geometries come within `TOUCH` (a cheap first test)."""
    ax0, ay0, ax1, ay1 = a.bounds
    bx0, by0, bx1, by1 = b.bounds
    return ax0 <= bx1 + TOUCH and bx0 <= ax1 + TOUCH and ay0 <= by1 + TOUCH and by0 <= ay1 + TOUCH


def shared(a, b) -> float:
    """Length of the boundary two polygons share."""
    if not near(a, b) or a.distance(b) > TOUCH:
        return 0.0
    return float(a.boundary.intersection(b.buffer(TOUCH, quad_segs=1)).length)


def zone(o, thickness: float, clear: float):
    """Where no partition may meet the wall of opening `o`: along its wall `clear` beyond both edges (a shop
    front: its own width), from just outside the wall's face to just inside its inner face (+ 0.05 m)."""
    if o.wall is None:
        return None
    if o.kind == "shop":
        clear = 0.0              # a shop front's own edge may take a partition (the pier beside a house door)
    (ax, ay), (bx, by) = o.wall
    d = np.array([bx - ax, by - ay])
    d = d / max(float(np.hypot(*d)), 1e-9)
    inward = np.array([math.sin(o.yaw), -math.cos(o.yaw)])       # the piece front points out of the room
    c = np.array([o.x, o.y])
    half = o.width / 2 + clear
    a, b = c - d * half, c + d * half
    return Polygon([a - inward * 0.02, b - inward * 0.02, b + inward * (thickness + 0.05),
                    a + inward * (thickness + 0.05)])


def partition(poly, frame: Frame, axis: int, at: float, half: float):
    """The partition a cut would build: the line inside `poly` (not along its edges), `half` thick each side.
    None when the line misses the polygon's inside."""
    inside = shapely.intersection(frame.line(axis, at), poly)
    segs = [g for g in getattr(inside, "geoms", [inside]) if g.geom_type == "LineString" and g.length > 1e-6]
    keep = [g for g in segs if poly.boundary.distance(g.interpolate(0.5, normalized=True)) > 1e-4]
    if not keep:
        return None
    return shapely.union_all([g.buffer(half, cap_style="flat") for g in keep])


def clashes(strip, zones: list) -> bool:
    """True when a partition strip enters any opening's zone."""
    if strip is None or not zones:
        return False
    return bool((shapely.area(shapely.intersection(strip, zones)) > 1e-6).any())


def offsets(shift: float, step: float):
    """0, then -step, +step, -2 step... up to `shift`: nearer first, the lower one on a tie."""
    yield 0.0
    n = int(round(shift / step))
    for i in range(1, n + 1):
        yield -i * step
        yield i * step


def free_cut(poly, frame: Frame, axis: int, at: float, zones: list, half: float, shift: float,
             step: float = 0.05, lo: float = -math.inf, hi: float = math.inf) -> float | None:
    """The nearest position to `at` (within `shift`, and within [lo, hi]) where the cut splits `poly` and
    its partition keeps clear of every opening zone; None when there is none (the cut is dropped)."""
    zs = [z for z in zones if z is not None]
    if zs:                                                # the zones within 0.5 m of the polygon (as a buffer)
        zs = [z for z, ok in zip(zs, shapely.dwithin(zs, poly, 0.5)) if ok]
    for d in offsets(shift, step):
        a = at + d
        if not lo <= a <= hi:
            continue
        strip = partition(poly, frame, axis, a, half)
        if strip is None and d == 0.0:
            return a                       # the line builds no partition here: nothing to keep clear
        if strip is not None and not clashes(strip, zs):
            return a
    return None


class Cell:
    """A room in the making: its polygon, its type and where it came from (band, part)."""

    def __init__(self, poly, type: str, band: str = "", part: str = ""):
        self.poly, self.type, self.band, self.part = poly, type, band, part
        self.alcove = None
        self.doors: list = []     # explicit openings planned with the cell: (kind, x, y, width, ...)

    def __repr__(self):
        return f"Cell({self.type}, {self.band}/{self.part}, {self.poly.area:.1f} m2)"


def too_small(c: Cell, minimums: dict, piece: float) -> bool:
    """A piece under `piece` m2, a piece with no type yet, or a room under its type's minimum area or width."""
    area = c.poly.area
    if not c.type:                   # a cell with no type yet survives when it could be a maqsura
        least = minimums.get("maqsura")
        return least is None or area < least[0] or width(c.poly) < least[1]
    if area < piece:
        return True
    least = minimums.get(c.type)
    if not least:
        return False
    return area < least[0] or width(c.poly) < least[1]


def trim(cells: list, keep: tuple = (), takes: tuple = (), thin: float = 0.4) -> list:
    """Arms thinner than 2 x `thin` (a strip left along a wall by an irregular lot) leave their room for
    the neighbour they share more boundary with (a covered court among them)."""
    for c in [c for c in cells if c.type not in keep]:
        core = c.poly.buffer(-thin, join_style="mitre").buffer(thin, join_style="mitre").intersection(c.poly)
        core_parts = parts(snap(core))
        if not core_parts:
            continue
        body = max(core_parts, key=lambda p: p.area)
        arms = parts(shapely.difference(c.poly, body, grid_size=GRID))
        for arm in sorted(arms, key=lambda p: (-p.area, p.centroid.x, p.centroid.y)):
            if arm.area < 0.05:
                continue
            own = shared(arm, body)
            best, length = None, own + 1e-3
            for o in cells:
                if o is c or (o.type in keep and o.type not in takes):
                    continue
                s = shared(arm, o.poly)
                if s > length:
                    best, length = o, s
            if best is None:
                continue
            grown, rest = union(best.poly, arm), shapely.difference(c.poly, arm, grid_size=GRID)
            rest = parts(rest)
            if grown is None or len(rest) != 1:
                continue
            best.poly, c.poly = grown, rest[0]
    return cells


def absorb(cells: list, minimums: dict, keep: tuple = (), piece: float = 0.5, takes: tuple = (),
           largest: dict | None = None) -> list:
    """Small pieces and undersized rooms join the neighbour they share the longest boundary with, which
    keeps its type; repeated until none is left (at most as many passes as cells). Cells of a `keep` type
    are never merged, in either direction, but those of a `takes` type (a covered court) take pieces. A
    merge never grows a room past its type's `largest` (the piece joins another neighbour), and a bit
    merged into a service makes it a bit."""
    largest = largest or {}
    cells = merge_small(trim(list(cells), keep, takes), minimums, keep, piece, takes, largest)
    return merge_small(trim(cells, keep, takes), minimums, keep, piece, takes, largest)   # trimmed arms leave bits


def merge_small(cells: list, minimums: dict, keep: tuple, piece: float, takes: tuple, largest: dict) -> list:
    """The merging passes of `absorb`: smallest first; a piece under `piece` m2 or narrower than `SLIVER`
    with no other neighbour may join a `keep` room but a skifa (a sliver beside a stair becomes its landing)."""
    stuck: set = set()
    for _ in range(2 * len(cells) + 2):
        small = [i for i, c in enumerate(cells)
                 if c.type not in keep and id(c) not in stuck and too_small(c, minimums, piece)]
        if not small:
            break
        i = min(small, key=lambda n: (cells[n].poly.area, n))
        c = cells[i]
        merged = None
        for loose in (False, True):
            if loose and c.poly.area >= piece and width(c.poly) >= SLIVER:
                break
            ranked = sorted(((shared(c.poly, o.poly), j) for j, o in enumerate(cells) if j != i and
                             (o.type not in keep or (o.type in takes and c.poly.area < piece)
                              or (loose and o.type != "skifa"))),
                            key=lambda t: (-t[0], t[1]))
            for s, j in ranked:
                if s <= 1e-3:
                    break
                o = cells[j]
                if (o.type in largest and o.type != "skifa" and c.type != "bit"
                        and o.poly.area + c.poly.area > largest[o.type] + 1e-6):
                    continue                          # a service never grows past its largest
                merged = union(o.poly, c.poly)
                if merged is not None:
                    o.poly = merged
                    if c.type == "bit" and o.type in largest and o.type != "skifa":
                        o.type = "bit"                # a bit merged with a service is a bit
                    break
            if merged is not None:
                break
        if merged is None:
            stuck.add(id(c))
            continue
        del cells[i]
    return cells


def straight(lines, tol: float = 1e-3) -> list:
    """Straight pieces ((x0, y0), (x1, y1)) of a linear geometry, collinear neighbours merged."""
    out: list = []
    for g in getattr(lines, "geoms", [lines]):
        if g.geom_type == "LineString":
            if g.is_empty:
                continue
            pts = np.asarray(g.coords)[:, :2]
        elif g.geom_type in ("MultiLineString", "GeometryCollection"):
            out += straight(g, tol)
            continue
        else:
            continue
        run = [pts[0]]
        for p in pts[1:]:
            if len(run) >= 2:
                a, b = run[0], run[-1]
                d = b - a
                n = float(np.hypot(*d))
                off = abs(d[0] * (p[1] - a[1]) - d[1] * (p[0] - a[0])) / max(n, 1e-12)
                if off < tol and float(np.dot(p - b, d)) > 0:
                    run[-1] = p
                    continue
                out.append((tuple(run[0]), tuple(run[-1])))
                run = [run[-1], p]
            else:
                run.append(p)
        if len(run) >= 2:
            out.append((tuple(run[0]), tuple(run[-1])))
    return [s for s in out if math.dist(*s) > 1e-6]


def contact(a, b) -> list:
    """Straight pieces of the boundary polygons `a` and `b` share."""
    if not near(a, b) or a.distance(b) > TOUCH:
        return []
    return straight(lines_of(a.boundary.intersection(b.buffer(TOUCH, quad_segs=1))))


def lines_of(geom):
    """The linear parts of a geometry, merged where they join."""
    lines = [g for g in getattr(geom, "geoms", [geom]) if g.geom_type in ("LineString", "MultiLineString")]
    return shapely.line_merge(shapely.union_all(lines)) if lines else LineString()


def on_line(point, piece) -> float:
    """Distance from a point to a straight piece."""
    return LineString(piece).distance(Point(point))
