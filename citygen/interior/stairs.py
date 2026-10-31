"""Stairs as `Stair` records (SPEC 6c "Stairs"): the newel cell, entry steps, ladders, the U box.

Records (prompts 46-47) give their place, risers, riser, tread, width and door side; the geometry (prompt
49) turns a record into solid `Part`s, iron rails, the holes it needs in each slab (`well`) and its walking
lines (`treads`), which the mesh and the tests share. A newel cell is a square the same on every floor it serves: under the roof's stair
room when there is one, else in the first corner where it fits; its walls keep `clear` of every opening.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon

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


def surely_unclear(squares, region, zones: list, half: float):
    """A mask of the squares `walls_clear` would refuse for sure (a side well inside an opening's zone),
    found at once: the search skips them (47.1, speed only: every other square is judged as before)."""
    if not zones or not len(squares):
        return np.zeros(len(squares), dtype=bool)
    deep = shapely.difference(shapely.union_all(zones).buffer(-0.01, join_style="mitre"),
                              region.boundary.buffer(0.02, quad_segs=1))
    return shapely.length(shapely.intersection(shapely.boundary(squares), deep)) > 0.02


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
        held = shapely.contains(inside, squares)
        held[held] = ~surely_unclear(squares[held], region, zones, half)
        for i in np.flatnonzero(held):
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
            held = shapely.contains(inside, squares)
            held[held] = ~surely_unclear(squares[held], region, zones, half)
            for i in np.flatnonzero(held):
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
        least = float(cfg.get("tread_min", 0.2))
        if room_for < n * least:                      # a shorter landing before treads under `tread_min`
            room_for = max(room_for, min(n * least, depth - float(cfg.get("turn_min", 0.6))))
        tread = min(tread, room_for / n)
        if tread < least - 1e-9:                      # too short for a straight run: turned at the door
            got = turned(room, door, width, rise, cfg, ext)
            if got is not None:
                return got
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


def turned(room, door, width: float, rise: float, cfg: dict, ext: float) -> Stair | None:
    """Entry steps turned 90 degrees (lead decision, 47.1/48.1): a landing at the door's threshold as wide as
    the door + 2 x `side` and `steps_flight` deep, then a flight `steps_flight` wide along the facade wall
    toward the side with more room, its treads `tread` (down to `tread_min`) and `turn_min` of floor kept
    beyond it; None when neither side holds it."""
    least, turn = float(cfg.get("tread_min", 0.2)), float(cfg.get("turn_min", 0.6))
    w = width + 2 * float(cfg.get("side", 0.1))
    yaw = math.atan2(door.ny, door.nx)
    fr = Frame(door.x, door.y, yaw + math.pi / 2)    # v into the room
    ray = LineString([fr.world(0.0, ext), fr.world(0.0, ext + 50.0)]).intersection(room.polygon)
    depth = max((g.length for g in getattr(ray, "geoms", [ray]) if g.geom_type == "LineString"), default=0.0)
    f = min(float(cfg.get("steps_flight", 0.9)), depth)          # a shallow room: a narrower flight
    if f < float(cfg.get("steps_flight_min", 0.7)) - 1e-9:
        return None
    best = None
    for s in (1.0, -1.0):
        start = fr.world(s * w / 2, ext + f / 2)
        ray = LineString([start, fr.world(s * (w / 2 + 50.0), ext + f / 2)]).intersection(room.polygon)
        reach = next((g.length for g in getattr(ray, "geoms", [ray]) if g.geom_type == "LineString"
                      and g.distance(Point(*start)) < 1e-6), 0.0)
        if best is None or reach > best[0]:
            best = (reach, s)
    reach, s = best
    for riser_max in (float(cfg.get("riser", 0.18)), float(cfg.get("riser_steep", 0.22))):
        n = risers(abs(rise), riser_max)
        tread = min(float(cfg.get("tread", 0.3)), (reach - turn) / n)
        if tread >= least - 1e-9:
            break
    else:
        return None
    u0, u1 = sorted((-w / 2, s * (w / 2 + n * tread)))
    landing = fr.rect(-w / 2, ext, w / 2, ext + f)
    run = fr.rect(u0, ext, u1, ext + f)
    poly = shapely.union_all([landing, run]).intersection(room.polygon)
    door_landing = fr.rect(-width / 2, ext, width / 2, ext + f)
    if poly.geom_type != "Polygon" or door_landing.difference(room.polygon).area > 0.05 * door_landing.area:
        return None
    sign = 1.0 if rise > 0 else -1.0
    return Stair("steps", poly, 0, 0, n, sign * abs(rise) / n, tread, w, (door.x, door.y, yaw), [room.id],
                 turn=int(s), flight=f)


def steps_depth(rise: float, cfg: dict) -> float:
    """The least depth a room needs from its door for entry steps rising `rise` m with treads of
    `tread_min` and a landing of `turn_min` (0 when the door needs no steps)."""
    if abs(rise) <= float(cfg.get("threshold", 0.15)):
        return 0.0
    n = risers(abs(rise), float(cfg.get("riser_steep", 0.22)))
    return n * float(cfg.get("tread_min", 0.2)) + float(cfg.get("turn_min", 0.6))


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


# --- the U stair of villas, maisons and flats (prompt 47) -----------------------------------------------
def u_size(fh: float, cfg: dict, width: float, tread: float, need: float) -> dict:
    """The numbers of a U stair box: two flights of `width` side by side `gap` apart, n risers made even
    (n/2 per flight, (n/2 - 1) treads of `tread`), the floor landing at least `need` deep (a door fits at
    each side of it) and never shallower than `width`, the half landing `width` deep."""
    n = risers(fh, float(cfg.get("riser_max", {}).get("modern", 0.18)))
    n += n % 2
    gap = float(cfg.get("u_gap", 0.1))
    landing = max(width, need)
    return {"risers": n, "riser": fh / n, "tread": tread, "width": width, "landing": landing,
            "length": landing + (n // 2 - 1) * tread + width, "across": 2 * width + gap}


def u_box(fr: Frame, x: float, y: float, size: dict):
    """The box in a door frame `fr` (u along the door wall, v inward): centered on u = x, from v = y inward."""
    half = size["across"] / 2
    return fr.rect(x - half, y, x + half, y + size["length"])


def u_record(box, fr: Frame, x: float, y: float, size: dict, floor: int, top: int) -> Stair:
    """The `Stair` of a U box from `floor` to `top`; its door is the middle of the floor landing's end,
    yaw the way out of the box there."""
    p = fr.world(x, y)
    yaw = math.atan2(-fr.v[1], -fr.v[0])
    return Stair("u", box, floor, top, size["risers"], size["riser"], size["tread"], size["width"],
                 (float(p[0]), float(p[1]), yaw))


# --- geometry (prompt 49): solids, rails, wells and walking lines ---------------------------------------
@dataclass
class Part:
    """A vertical prism of a stair: `poly` from z0 to z1; `kind` step | landing | pier | waist."""
    poly: object
    z0: float
    z1: float
    kind: str


@dataclass
class Run:
    """The walking line of one climb from level `z_from` to `z_to`: points (x, y, z of the tread under
    them) 0.1 m apart, in the order a person climbs."""
    z_from: float
    z_to: float
    pts: np.ndarray


ALONG = 0.1     # meters between the points of a walking line


def level(interior, f: int) -> float:
    """The z of floor f (the roof deck for f = floors): floor 0 at `high`, one floor height each."""
    return interior.high + f * interior.fh


def riser_max(stair, cfg: dict) -> float:
    """The highest riser a stair may have: traditional (newel), modern (u), the steep entry steps."""
    if stair.kind == "steps":
        return float(cfg.get("riser_steep", 0.22))
    kind = "traditional" if stair.kind == "newel" else "modern"
    return float(cfg.get("riser_max", {}).get(kind, 0.21 if kind == "traditional" else 0.18))


def climbs(stair) -> list:
    """The floors a stair climbs from: one climb per floor for newel and U stairs, one for steps and
    ladders (a ladder may pass several floors through its wells)."""
    if stair.kind in ("newel", "u"):
        return list(range(stair.floor, stair.top))
    return [stair.floor]


def _wedge(c: np.ndarray, a0: float, a1: float, reach: float) -> Polygon:
    """The sector from angle a0 to a1 (radians, a1 - a0 under pi) round c, `reach` m long."""
    n = max(1, int(math.ceil((a1 - a0) / (math.pi / 4))))
    angles = np.linspace(a0, a1, n + 1)
    pts = [c] + [c + reach * np.array([math.cos(a), math.sin(a)]) for a in angles]
    return Polygon(pts)


def _newel_frame(stair, cfg: dict) -> tuple:
    """(center, side, pier square, door angle) of a newel cell."""
    fr = Frame.of(stair.polygon)
    u0, v0, u1, v1 = fr.bounds(stair.polygon)
    side = min(u1 - u0, v1 - v0)
    c = fr.world((u0 + u1) / 2, (v0 + v1) / 2)
    p = float(cfg.get("pier", 0.3)) / 2
    pier = fr.rect((u0 + u1) / 2 - p, (v0 + v1) / 2 - p, (u0 + u1) / 2 + p, (v0 + v1) / 2 + p)
    door = stair.door if stair.door is not None else (*fr.world((u0 + u1) / 2, v0), fr.angle - math.pi / 2)
    a = math.atan2(door[1] - c[1], door[0] - c[0])
    return c, side, pier, a, fr


def _newel_parts(stair, interior, cfg: dict, fl: dict) -> list:
    """Per floor climbed: three quarters of a turn of steps counter-clockwise from the landing quarter in
    front of the door (the landing is the slab of each floor); the pier from the bottom floor up."""
    c, side, pier, a, _ = _newel_frame(stair, cfg)
    n, r = stair.risers, stair.riser
    waist = float(fl.get("waist", 0.15))
    out = []
    for f in climbs(stair):
        z = level(interior, f)
        for k in range(1, n + 1):
            a0 = a + math.pi / 4 + (k - 1) * 1.5 * math.pi / n
            poly = stair.polygon.intersection(_wedge(c, a0, a0 + 1.5 * math.pi / n, side)).difference(pier)
            if poly.area > 1e-4:
                out.append(Part(poly, z + k * r - r - waist, z + k * r, "step"))
    out.append(Part(pier, level(interior, stair.floor), top_of_pier(stair, interior, cfg, fl), "pier"))
    return out


def top_of_pier(stair, interior, cfg: dict, fl: dict) -> float:
    """The pier reaches the ceiling over its last landing: the roof stair room's, else the top floor's."""
    if stair.top >= interior.floors:
        roofs = [r for r in interior.rooms if r.floor == interior.floors and r.type == "droj"]
        if roofs:
            return roofs[0].z + roofs[0].height - float(fl.get("roof_room_ceiling", 0.15))
    return level(interior, stair.top) + interior.fh - float(fl.get("slab", 0.25))


def landing_quarter(stair, cfg: dict):
    """The quarter of a newel cell in front of its door, less the pier: the floor-level landing."""
    c, side, pier, a, _ = _newel_frame(stair, cfg)
    return stair.polygon.intersection(_wedge(c, a - math.pi / 4, a + math.pi / 4, side)).difference(pier)


def _u_frame(stair) -> tuple:
    """(frame at the door: u along the landing's end, v into the box; u0, u1, length, landing depth)."""
    x, y, yaw = stair.door
    fr = Frame(x, y, yaw + math.pi / 2)              # v = -(cos yaw, sin yaw): into the box
    u0, v0, u1, v1 = fr.bounds(stair.polygon)
    half = stair.risers // 2
    landing = v1 - (half - 1) * stair.tread - stair.width
    return fr, u0, u1, v1, landing


def _u_steps(stair, interior) -> list:
    """(flight, k, rect, top z) of every step of every climb: flight 1 along the -u side up to the half
    landing, flight 2 back along the +u side to the next floor's landing."""
    fr, u0, u1, length, landing = _u_frame(stair)
    w, t, r, half = stair.width, stair.tread, stair.riser, stair.risers // 2
    out = []
    for f in climbs(stair):
        z = level(interior, f)
        for k in range(1, half):
            out.append((f, 1, fr.rect(u0, landing + (k - 1) * t, u0 + w, landing + k * t), z + k * r))
        for j in range(1, half):
            v = landing + (half - 1 - j) * t
            out.append((f, 2, fr.rect(u1 - w, v, u1, v + t), z + (half + j) * r))
    return out


def _u_parts(stair, interior, cfg: dict, fl: dict) -> list:
    """The steps (each from its riser's foot), the half landings and, for the overheads, each step down to
    the flight's sloped waist (`waist` m under the nosing line)."""
    fr, u0, u1, length, landing = _u_frame(stair)
    w, t, r, half = stair.width, stair.tread, stair.riser, stair.risers // 2
    waist = float(fl.get("waist", 0.15)) * math.hypot(t, r) / t
    out = [Part(rect, top - r - waist, top, "step") for _, _, rect, top in _u_steps(stair, interior)]
    thick = float(fl.get("landing", 0.2))
    for f in climbs(stair):
        z = level(interior, f) + half * r
        out.append(Part(fr.rect(u0, landing + (half - 1) * t, u1, length), z - thick, z, "landing"))
    return out


def parts(stair, interior, cfg: dict, fl: dict) -> list:
    """The solid `Part`s of a stair (ladders have none: they stand in their wells)."""
    if stair.kind == "newel":
        return _newel_parts(stair, interior, cfg, fl)
    if stair.kind == "u":
        return _u_parts(stair, interior, cfg, fl)
    if stair.kind == "steps":
        return [Part(p, z0, z1, "step") for p, z0, z1 in entry_steps(stair, interior)]
    return []


def entry_steps(stair, interior) -> list:
    """(polygon, z0, z1) of every entry step from the door's threshold to floor 0: up steps stand on the
    ground under the slab's hole, down steps on the floor; the last step is flush with floor 0."""
    x, y, yaw = stair.door
    fr = Frame(x, y, yaw + math.pi / 2)              # v into the room, away from the door
    _, v0, _, _ = fr.bounds(stair.polygon)
    floor = level(interior, 0)
    door = floor - stair.risers * stair.riser
    out = []
    if stair.turn:
        return _turned_steps(stair, fr, v0, floor, door)
    for k in range(1, stair.risers + 1):
        band = fr.rect(-50.0, v0 + (k - 1) * stair.tread, 50.0, v0 + k * stair.tread)
        poly = stair.polygon.intersection(band)
        top = door + k * stair.riser
        if poly.area < 1e-4:
            continue
        out.append((poly, min(door, floor) - 0.3 if stair.riser > 0 else floor, top))
    return out


def _turned_steps(stair, fr: Frame, v0: float, floor: float, door: float) -> list:
    """`entry_steps` of a turned flight: the door's landing at the threshold, then the treads along the wall."""
    w, f, t, s = stair.width, stair.flight, stair.tread, stair.turn
    base = min(door, floor) - 0.3 if stair.riser > 0 else floor
    out = [(stair.polygon.intersection(fr.rect(-w / 2, v0, w / 2, v0 + f)), base, door)]
    for k in range(1, stair.risers + 1):
        a, b = sorted((s * (w / 2 + (k - 1) * t), s * (w / 2 + k * t)))
        poly = stair.polygon.intersection(fr.rect(a, v0, b, v0 + f))
        if poly.area >= 1e-4:
            out.append((poly, base, door + k * stair.riser))
    return out


def turned_line(stair, interior) -> np.ndarray:
    """The walking line of a turned flight (x, y, z): into the landing, then along the flight's middle."""
    x, y, yaw = stair.door
    fr = Frame(x, y, yaw + math.pi / 2)
    _, v0, _, _ = fr.bounds(stair.polygon)
    w, f, t, s, n = stair.width, stair.flight, stair.tread, stair.turn, stair.risers
    floor = level(interior, 0)
    door = floor - n * stair.riser
    pts = [(*fr.world(0.0, v), door) for v in np.arange(v0 + ALONG / 2, v0 + f / 2, ALONG)]
    step = min(ALONG, t / 2)
    for u in np.arange(step / 2, w / 2 + n * t, step):
        k = int((u - w / 2) // t) if u > w / 2 else -1
        p = fr.world(s * u, v0 + f / 2)
        if stair.polygon.contains(Point(*p)):
            pts.append((*p, door if k < 0 else floor - (n - 1 - min(k, n - 1)) * stair.riser))
    return np.array(pts).reshape(-1, 3)


def well(stair, f: int, interior, cfg: dict):
    """The hole the stair needs in the slab of floor f (None where it needs none): newel and U stairs over
    every floor they climb to, less that floor's landing; a ladder's footprint; up steps in floor 0."""
    if stair.kind == "steps":
        return stair.polygon if f == 0 and stair.riser > 0 else None
    if not stair.floor < f <= stair.top:
        return None
    if stair.kind == "newel":
        return stair.polygon.difference(landing_quarter(stair, cfg))
    if stair.kind == "u":
        fr, u0, u1, length, landing = _u_frame(stair)
        return stair.polygon.difference(fr.rect(u0 - 1.0, -1.0, u1 + 1.0, landing))
    return stair.polygon


def rails(stair, interior, cfg: dict, fl: dict) -> list:
    """Iron railings as polylines of (x, y, z) at hand height: a U stair's flights on their open side, the
    half landing over the gap and each floor landing's edge over the well; a newel's last landing."""
    h = float(fl.get("rail", 0.9))
    out = []
    if stair.kind == "u":
        fr, u0, u1, length, landing = _u_frame(stair)
        w, t, r, half = stair.width, stair.tread, stair.riser, stair.risers // 2
        for f in climbs(stair):
            z = level(interior, f)
            v_end = landing + (half - 1) * t
            one = [(*fr.world(u0 + w, landing), z + r + h), (*fr.world(u0 + w, v_end), z + half * r + h)]   # nosing lines
            two = [(*fr.world(u1 - w, v_end), z + (half + 1) * r + h), (*fr.world(u1 - w, landing), z + 2 * half * r + h)]
            out += [one, two]
            if u1 - w - (u0 + w) > 0.05:
                out.append([(*fr.world(u0 + w, v_end), z + half * r + h), (*fr.world(u1 - w, v_end), z + half * r + h)])
        for f in range(stair.floor + 1, stair.top + 1):   # over the gap; at the top over flight 1's well too
            z = level(interior, f) + h
            start = u0 if f == stair.top else u0 + w
            if u1 - w - start > 0.05:
                out.append([(*fr.world(start, landing), z), (*fr.world(u1 - w, landing), z)])
    elif stair.kind == "newel" and stair.top < interior.floors:
        c, side, pier, a, _ = _newel_frame(stair, cfg)
        z = level(interior, stair.top) + h
        for b in (a - math.pi / 4, a + math.pi / 4):
            far = c + np.array([math.cos(b), math.sin(b)]) * side
            edge = stair.polygon.intersection(LineString([c, far])).difference(pier)
            if not edge.is_empty and edge.length > 0.05:
                pts = shapely.get_coordinates(edge)
                out.append([(*pts[0], z), (*pts[-1], z)])
    return out


def stringers(stair, interior, fl: dict) -> list:
    """(start, end, depth) of the board along each U flight's open side, its top `stringer` m over the
    nosing line and deep enough to hide the steps' undersides."""
    fr, u0, u1, length, landing = _u_frame(stair)
    w, t, r, half = stair.width, stair.tread, stair.riser, stair.risers // 2
    th = float(fl.get("stringer", 0.05))
    waist = float(fl.get("waist", 0.15)) * math.hypot(t, r) / t
    tall = r + waist + 2 * th                          # vertical
    slope = math.atan2(r, t)
    v_end = landing + (half - 1) * t
    out = []
    for f in climbs(stair):
        z = level(interior, f)
        mid = th - tall / 2                            # the board's middle under the nosing line
        for u, (va, za), (vb, zb) in ((u0 + w + th / 2, (landing, z + r), (v_end, z + half * r)),
                                      (u1 - w - th / 2, (v_end, z + (half + 1) * r), (landing, z + 2 * half * r))):
            out.append((np.array([*fr.world(u, va), za + mid]), np.array([*fr.world(u, vb), zb + mid]),
                        tall * math.cos(slope)))
    return out


def ladder_line(stair, interior, fl: dict) -> tuple:
    """(foot (x, y, z), head (x, y, z), across unit vector): a ladder leans along its footprint's long side
    from one end at the floor (the court's paving in a court) to 1 m above the level it reaches."""
    fr = Frame.of(stair.polygon)
    u0, v0, u1, v1 = fr.bounds(stair.polygon)
    if u1 - u0 < v1 - v0:
        fr = Frame(*fr.c, fr.angle + math.pi / 2)
        u0, v0, u1, v1 = fr.bounds(stair.polygon)
    vm = (v0 + v1) / 2
    z0 = level(interior, stair.floor)
    first = next((r for r in interior.rooms if stair.rooms and r.id == stair.rooms[0]), None)
    if first is not None and first.type == "wast_ed_dar" and first.open:
        z0 -= float(fl.get("court_step", 0.15))
    z1 = level(interior, stair.top)
    return (np.array([*fr.world(u0 + 0.05, vm), z0]), np.array([*fr.world(u1 - 0.05, vm), z1 + 1.0]), fr.v, z1)


def treads(stair, interior, cfg: dict | None = None) -> list:
    """The `Run` of every climb of a stair: the walking line (0.45 m inside a newel cell's walls, the middle
    of a U flight and across its half landing, the middle of entry steps, a ladder's rungs) with the z of
    the tread under each point."""
    cfg = cfg or {}
    if stair.kind == "newel":
        return _newel_runs(stair, interior, cfg)
    if stair.kind == "u":
        return _u_runs(stair, interior)
    if stair.kind == "steps" and stair.turn:
        door = level(interior, 0) - stair.risers * stair.riser
        return [Run(door, level(interior, 0), turned_line(stair, interior))]
    if stair.kind == "steps":
        x, y, yaw = stair.door
        fr = Frame(x, y, yaw + math.pi / 2)
        _, v0, _, _ = fr.bounds(stair.polygon)
        pts = []
        step = min(ALONG, stair.tread / 2)              # every tread, however short (steep steps)
        for v in np.arange(v0 + step / 2, v0 + stair.risers * stair.tread, step):
            p = fr.world(0.0, v)
            if not stair.polygon.contains(Point(*p)):     # where the room clips them, there are none
                continue
            k = min(int((v - v0) // stair.tread), stair.risers - 1)
            pts.append((*p, level(interior, 0) - (stair.risers - 1 - k) * stair.riser))
        door = level(interior, 0) - stair.risers * stair.riser
        return [Run(door, level(interior, 0), np.array(pts).reshape(-1, 3))]
    foot, head, _, z1 = ladder_line(stair, interior, {})
    n = max(1, int(round((z1 - foot[2]) / max(stair.riser, 1e-6))))
    zs = foot[2] + (z1 - foot[2]) * np.arange(1, n) / n
    at = (zs - foot[2]) / (head[2] - foot[2])
    pts = foot[None, :2] + (head[None, :2] - foot[None, :2]) * at[:, None]
    return [Run(float(foot[2]), z1, np.column_stack([pts, zs]))]


def _newel_runs(stair, interior, cfg: dict) -> list:
    c, side, pier, a, fr = _newel_frame(stair, cfg)
    walk = float(cfg.get("walk", 0.45))
    h = side / 2 - walk
    n, r = stair.risers, stair.riser
    perim = 3 * 2 * h                                   # three quarters of the walking square
    s = np.arange(ALONG / 2, perim, ALONG)
    # walk the square path counter-clockwise from the landing's edge (angle a + 45 degrees)
    pts, angles = [], []
    corner = c + np.array([math.cos(a + math.pi / 4), math.sin(a + math.pi / 4)]) * h * math.sqrt(2)
    ring = [corner]
    for q in range(1, 4):
        b = a + math.pi / 4 + q * math.pi / 2
        ring.append(c + np.array([math.cos(b), math.sin(b)]) * h * math.sqrt(2))
    line = LineString([tuple(p) for p in ring])
    for d in s:
        p = np.asarray(line.interpolate(float(d)).coords[0])
        ang = (math.atan2(p[1] - c[1], p[0] - c[0]) - (a + math.pi / 4)) % (2 * math.pi)
        pts.append(p)
        angles.append(ang)
    k = np.minimum((np.array(angles) / (1.5 * math.pi / n)).astype(int) + 1, n)
    out = []
    for f in climbs(stair):
        z = level(interior, f)
        out.append(Run(z, level(interior, f + 1), np.column_stack([np.array(pts).reshape(-1, 2), z + k * r])))
    return out


def _u_runs(stair, interior) -> list:
    fr, u0, u1, length, landing = _u_frame(stair)
    w, t, r, half = stair.width, stair.tread, stair.riser, stair.risers // 2
    ua, ub = u0 + w / 2, u1 - w / 2
    v_end = landing + (half - 1) * t
    vm = (v_end + length) / 2
    out = []
    for f in climbs(stair):
        z = level(interior, f)
        pts = []
        for v in np.arange(landing + ALONG / 2, v_end, ALONG):
            pts.append((*fr.world(ua, v), z + (int((v - landing) // t) + 1) * r))
        for u in np.arange(ua, ub + 1e-9, ALONG):
            pts.append((*fr.world(u, vm), z + half * r))
        for v in np.arange(v_end - ALONG / 2, landing, -ALONG):
            pts.append((*fr.world(ub, v), z + (half + int((v_end - v) // t) + 1) * r))
        out.append(Run(z, level(interior, f + 1), np.array(pts).reshape(-1, 3)))
    return out
