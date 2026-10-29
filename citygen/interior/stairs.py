"""Stairs of old-town houses as `Stair` records (SPEC 6c "Stairs"): the newel cell, entry steps, ladders.

Their geometry (treads, pier, rails) comes in prompt 49; here they get their place, risers, riser, tread,
width and door side. A newel cell is a square the same on every floor it serves: under the roof's stair
room when there is one, else in the first corner where it fits; its walls keep `clear` of every opening.
"""
from __future__ import annotations

import math

import numpy as np
import shapely
from shapely.geometry import LineString, Point

from ..city.geo import polygons
from .cuts import Frame, clashes
from .model import Stair

STEP = 0.05     # meters: sizes (and positions under a stair room) of a newel cell are tried in these steps
SLIDE = 0.1     # meters: the steps a corner cell slides in from its corner


def risers(height: float, riser_max: float) -> int:
    """The smallest count of risers no higher than `riser_max`."""
    return max(1, math.ceil(height / riser_max - 1e-9))


def walls_clear(square, region, zones: list, half: float, edge=None) -> bool:
    """True when the cell's sides inside `region` (its partitions) keep clear of every opening zone
    (`edge`: the region's boundary grown 0.01 m, when the caller has it)."""
    if not zones:
        return True
    edge = region.boundary.buffer(0.01, quad_segs=1) if edge is None else edge
    for poly in polygons(square):
        for ring in (poly.exterior, *poly.interiors):
            pts = np.asarray(ring.coords)
            for a, b in zip(pts[:-1], pts[1:]):
                side = LineString([a, b]).difference(edge)
                if side.is_empty or side.length < 1e-3:
                    continue
                if clashes(side.buffer(half, cap_style="flat"), zones):
                    return False
    return True


def sizes(top: float, least: float) -> list:
    """Square sides from `top` down to `least` in `STEP`s."""
    n = int(round((top - least) / STEP))
    return [round(top - i * STEP, 3) for i in range(max(n, 0) + 1)]


def under_stair_room(room, region, zones: list, half: float, least: float):
    """The largest square inside the roof's stair room square (and inside `region`) with a side of at
    least `least` whose walls keep the rule, nearest the stair room's center; None when none fits."""
    fr = Frame.of(room)
    u0, v0, u1, v1 = fr.bounds(room)
    side = min(u1 - u0, v1 - v0)
    cu, cv = (u0 + u1) / 2, (v0 + v1) / 2
    inside = region.buffer(1e-6)
    shapely.prepare(inside)
    edge = region.boundary.buffer(0.01, quad_segs=1)
    for s in sizes(side, least):
        slack = (side - s) / 2
        n = int(slack / STEP + 1e-9)
        offs = np.array(sorted(((i * STEP, j * STEP) for i in range(-n, n + 1) for j in range(-n, n + 1)),
                               key=lambda t: (abs(t[0]) + abs(t[1]), t[0], t[1])))
        us, vs = cu + offs[:, 0], cv + offs[:, 1]
        squares = fr.rects(us - s / 2, vs - s / 2, us + s / 2, vs + s / 2)
        for i in np.flatnonzero(shapely.contains(inside, squares)):
            if squares[i].difference(region).area < 1e-6 and walls_clear(squares[i], region, zones, half, edge):
                return squares[i]
    return None


def in_corner(corners: list, fr: Frame, region, zones: list, half: float, top: float, least: float,
              reach: float = 1.5):
    """The first corner (u, v, du, dv: the corner point and the directions into the house) where a square
    of side `top` down to `least`, slid in from the corner up to `reach`, fits `region` and keeps the rule."""
    inside = region.buffer(1e-6)
    shapely.prepare(inside)
    edge = region.boundary.buffer(0.01, quad_segs=1)
    n = int(round(reach / SLIDE))
    slides = np.array(sorted(((i * SLIDE, j * SLIDE) for i in range(n + 1) for j in range(n + 1)),
                             key=lambda t: (t[0] + t[1], t[0], t[1])))
    for u, v, du, dv in corners:
        for s in sizes(top, least):
            ua, va = u + du * slides[:, 0], v + dv * slides[:, 1]
            ub, vb = ua + du * s, va + dv * s
            squares = fr.rects(np.minimum(ua, ub), np.minimum(va, vb), np.maximum(ua, ub), np.maximum(va, vb))
            for i in np.flatnonzero(shapely.contains(inside, squares)):
                if squares[i].difference(region).area < 1e-6 and walls_clear(squares[i], region, zones, half, edge):
                    return squares[i]
    return None


def door_side(square, regions: list, toward: float | None = None) -> tuple | None:
    """(x, y, yaw) of the middle of the cell side the door is on, yaw the way out of the cell: the side
    facing `toward` (the stair room door's yaw) when its outside lies in every region, else the first
    side whose outside does."""
    ring = np.asarray(square.exterior.coords)[:-1]
    c = np.asarray(square.centroid.coords)[0]
    sides = []
    for a, b in zip(ring, np.roll(ring, -1, axis=0)):
        mid = (a + b) / 2
        n = mid - c
        n = n / max(float(np.hypot(*n)), 1e-9)
        ok = all(r.contains(Point(*(mid + n * 0.6))) for r in regions)
        sides.append((ok, mid, n))
    if toward is not None:
        best = max(sides, key=lambda t: math.cos(math.atan2(t[2][1], t[2][0]) - toward))
        if best[0]:
            return float(best[1][0]), float(best[1][1]), math.atan2(best[2][1], best[2][0])
    for ok, mid, n in sides:
        if ok:
            return float(mid[0]), float(mid[1]), math.atan2(n[1], n[0])
    return None


def door_line(square, door: tuple) -> tuple:
    """The cell side ((x0, y0), (x1, y1)) holding the door."""
    ring = np.asarray(square.exterior.coords)[:-1]
    p = np.array(door[:2])
    best = min(zip(ring, np.roll(ring, -1, axis=0)), key=lambda ab: float(np.hypot(*((ab[0] + ab[1]) / 2 - p))))
    return tuple(map(tuple, best))


def newel(square, door: tuple, top: int, fh: float, cfg: dict) -> Stair:
    """The record of a newel cell from floor 0 to `top`: a landing quarter, then three quarters of a turn
    of steps per floor; treads measured on the walking line `walk` m inside the cell's walls."""
    fr = Frame.of(square)
    u0, v0, u1, v1 = fr.bounds(square)
    s = min(u1 - u0, v1 - v0)
    n = risers(fh, float(cfg.get("riser_max", {}).get("traditional", 0.21)))
    walk = float(cfg.get("walk", 0.45))
    pier = float(cfg.get("pier", 0.3))
    return Stair("newel", square, 0, top, n, fh / n, 3 * (s - 2 * walk) / n, (s - pier) / 2, door)


def steps(room, door, width: float, rise: float, cfg: dict, warnings: list, ext: float) -> Stair | None:
    """Entry steps inside `room` from a door (`DoorSpot`) whose threshold lies `rise` m below floor 0 (up;
    negative: above it, down): risers of at most `riser`, treads of `tread`, as wide as the opening + 2 x
    `side`; where the room is too short (a `turn` landing kept), risers up to `riser_steep` and a warning."""
    if abs(rise) <= float(cfg.get("threshold", 0.15)):
        return None
    tread = float(cfg.get("tread", 0.3))
    inward = -np.array([door.nx, door.ny])
    face = np.array([door.x, door.y]) + inward * ext
    ray = LineString([face, face + inward * 50.0]).intersection(room.polygon)
    depth = max((g.length for g in getattr(ray, "geoms", [ray]) if g.geom_type == "LineString"), default=0.0)
    room_for = max(depth - float(cfg.get("turn", 0.9)), tread)
    n = risers(abs(rise), float(cfg.get("riser", 0.18)))
    if n * tread > room_for + 1e-9:
        n = risers(abs(rise), float(cfg.get("riser_steep", 0.22)))
        tread = min(tread, room_for / n)
        warnings.append(f"the entry steps are steep: {n} risers of {abs(rise) / n:.2f} m in {room_for:.2f} m")
    w = width + 2 * float(cfg.get("side", 0.1))
    along = np.array([-inward[1], inward[0]])
    a = face + along * w / 2
    b = face - along * w / 2
    poly = shapely.Polygon([a, b, b + inward * n * tread, a + inward * n * tread]).intersection(room.polygon)
    if poly.geom_type != "Polygon" or poly.area < 1e-3:
        return None
    sign = 1.0 if rise > 0 else -1.0
    yaw = math.atan2(-inward[1], -inward[0])
    return Stair("steps", poly, 0, 0, n, sign * abs(rise) / n, tread, w, (door.x, door.y, yaw), [room.id])


def ladder(region, fr: Frame, near, size: tuple):
    """A ladder's floor (`size` = width, depth) inside `region`, nearest the point `near`, its long side
    against the region's edge where it can; None when it fits nowhere."""
    w, d = size
    inside = region.buffer(1e-6)
    shapely.prepare(inside)
    u0, v0, u1, v1 = fr.bounds(region)
    pu, pv = fr.local(np.asarray(near))
    best = None
    for du, dv in ((w, d), (d, w)):
        us, vs = np.meshgrid(np.arange(u0, u1 - du + 1e-9, 0.1), np.arange(v0, v1 - dv + 1e-9, 0.1), indexing="ij")
        us, vs = us.ravel(), vs.ravel()
        if not len(us):
            continue
        rs = fr.rects(us, vs, us + du, vs + dv)
        ok = np.flatnonzero(shapely.contains(inside, rs))
        if not len(ok):
            continue
        dist = np.hypot(us[ok] + du / 2 - pu, vs[ok] + dv / 2 - pv)
        i = int(ok[np.argmin(dist)])
        if best is None or float(dist.min()) < best[0] - 1e-9:
            best = (float(dist.min()), rs[i])
    return None if best is None else best[1]
