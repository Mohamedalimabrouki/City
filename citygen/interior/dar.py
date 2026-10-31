"""The courtyard house (`dar`, SPEC 6c "Courtyard house") and the ring of rooms round a court.

The court's frame gives the axes. The lines along the court's long sides, extended to the outer wall, cut
the ring into two long bands (`n`, `s`: beyond the long sides, corners included) and two short ones (`w`,
`e`). The entry band holds the bent skifa, the main band across the court the T room (bit with its kbou
and maqsuras), the rest the kitchen, washroom, stores and more bits; upper floors are ghorfas opening into
each other. `compact.py` runs the same ring round a covered court.
"""
from __future__ import annotations

import math

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon

from ..rng import stream
from . import rooms as R
from . import program as P
from . import stairs as S
from .cuts import (REACH, Cell, Frame, absorb, clashes, contact, cut, lines_of, partition, parts, polygonal, shared,
                   snap, straight, union, width, zone)
from .cuts import free_cut as _free_cut
from .model import Opening, Room

LONG = ("n", "s")
SIDES = ("n", "s", "w", "e")
SERVICES = ("matbakh", "bit_el_ma", "bit_el_mouna")


class Job:
    """What every step of one house's layout needs: the interior, its bridge, the `[interiors]` numbers
    and its random streams (`stream(seed, "interior", city id, k, purpose)`)."""

    def __init__(self, interior, outside, style: dict):
        cfg = style.get("interiors", {})
        interior.entry = main_opening(interior, outside.doors[0] if outside.doors else None)
        self.interior, self.outside, self.cfg = interior, outside, cfg
        op, walls, rooms = cfg.get("openings", {}), cfg.get("walls", {}), cfg.get("rooms", {})
        self.half = interior.walls["partition"] / 2
        self.ext, self.court_wall = interior.walls["exterior"], interior.walls["court"]
        self.clear = float(op.get("clear", 0.3))
        self.door = float(op.get("door", 0.9))
        self.door_height = float(op.get("door_height", 2.1))
        self.shift = float(walls.get("cut_shift", 1.2))
        self.step = float(walls.get("cut_step", 0.05))
        self.piece = float(rooms.get("piece", 0.5))
        self.minimums = {k: (float(v[0]), float(v[1])) for k, v in rooms.items() if isinstance(v, list)}
        self.dar, self.compact = cfg.get("dar", {}), cfg.get("compact", {})
        self.stairs = cfg.get("stairs", {})
        floors = cfg.get("floors", {})
        interior.rules = {"clear": self.clear, "door": self.door, "door_height": self.door_height,
                          "narrow": float(op.get("narrow", 0.7)), "narrow_clear": float(op.get("narrow_clear", 0.05)),
                          "partition": interior.walls["partition"], "exterior": self.ext, "court": self.court_wall,
                          "minimums": self.minimums, "headroom": float(self.stairs.get("headroom", 2.0)),
                          "slab": float(floors.get("slab", 0.25)),
                          "roof_ceiling": float(floors.get("roof_room_ceiling", 0.15)),
                          "stair_height": float(style.get("roofs", {}).get("stair_height", 2.4))}
        keep = interior.rules["front_keep"] = float(walls.get("front_keep", 0.0))
        self.zones = {st.floor: [zone(o, self.ext, self.clear, keep) for o in interior.openings
                                 if o.floor == st.floor and o.wall is not None] for st in interior.storeys}
        self.plain = {st.floor: [zone(o, self.ext, self.clear) for o in interior.openings
                                 if o.floor == st.floor and o.wall is not None] for st in interior.storeys}
        self.shallow = {st.floor: [zone(o, self.ext, self.clear, keep if o.kind == "door" else 0.0)
                                   for o in interior.openings if o.floor == st.floor and o.wall is not None]
                        for st in interior.storeys}
        self.roof = next((lay for m, lay in outside.roofs if m.main), None)
        self.spot = outside.doors[0] if outside.doors else None
        self.main = main_opening(interior, self.spot)
        self.wealth = float((interior.household or {}).get("wealth", 0.0))
        self.fronts = [inside(o, self.ext) for o in interior.openings
                       if o.kind in ("door", "shop") and o is not self.main and o.floor == 0]
        self.steps_need = S.steps_depth(interior.high - self.spot.z, self.stairs) if self.spot is not None else 0.0
        more = getattr(interior, "keep_steps", None)
        if more is not None:                          # a second plan: no partition across the steps (47.1)
            strip = self.entry_keep(self.steps_need + more)
            for zones in (self.zones, self.shallow, self.plain):
                if strip is not None and 0 in zones:
                    zones[0].append(strip)
        self.thin = float(self.stairs.get("landing_strip", 0.45))   # half the widest strip the droj takes
        self.roof_ladder = False          # the newel could not stand under the stair room
        self.largest = {k: float(v) for k, v in self.dar.get("largest", {}).items()}   # m2 per service
        interior.rules["largest"] = dict(self.largest)
        interior.rules["most"] = {k: float(v) for k, v in rooms.get("most", {}).items()}
        interior.rules["plan"] = {**cfg.get("checks", {}), "casing": float(op.get("casing", 0.05)),
                                  "tread_min": float(self.stairs.get("tread_min", 0.2)),
                                  "railings": tuple(op.get("railings", ()))}   # `plancheck`'s numbers
        self.court = self.rng("court")    # one stream per house: court windows, then the majel, in that order
        self.wells: dict = {}             # floor -> the light well room of a covered court
        self.made: dict = {}              # id(cell) -> (cell, room)
        self.court_room = None

    def rng(self, purpose: str):
        i = self.interior
        return stream(i.seed, "interior", i.city_id, i.building, purpose)

    def zs(self, floors=None, shallow: bool = False) -> list:
        """The opening zones of `floors`; `shallow`: `front_keep` only behind doors (a stair cell standing a
        sliver off a window's wall is judged with its strip, which joins the droj: `without`)."""
        zones = self.shallow if shallow else self.zones
        keys = sorted(zones) if floors is None else floors
        return [z for f in keys for z in zones.get(f, []) if z is not None]

    def free(self, poly, fr: Frame, axis: int, at: float, floors=None, lo=-math.inf, hi=math.inf):
        return _free_cut(poly, fr, axis, at, self.zs(floors), self.half, self.shift, self.step, lo, hi)

    def fits(self, poly, type_: str) -> bool:
        least = self.minimums.get(type_)
        return least is None or (poly.area >= least[0] and width(poly) >= least[1])

    def entry_keep(self, deep: float | None = None):
        """The floor inside the main door its entry steps and their landing need (None without steps):
        ladders keep off it (47.1); `deep` m from the wall's inner face (default: the steps or a `turn`)."""
        if self.spot is None or self.main is None or self.steps_need <= 0.0:
            return None
        s = self.spot
        inward = -np.array([s.nx, s.ny])
        along = np.array([-inward[1], inward[0]])
        face = np.array([s.x, s.y]) + inward * self.ext
        w = self.main.width / 2 + float(self.stairs.get("side", 0.1))
        deep = max(self.steps_need, float(self.stairs.get("turn", 0.9))) if deep is None else deep
        return Polygon([face - along * w, face + along * w, face + along * w + inward * deep,
                        face - along * w + inward * deep])

    def probe(self, inward: float = 0.15):
        """A point just inside the main door."""
        s = self.spot
        return Point(s.x - s.nx * (self.ext + inward), s.y - s.ny * (self.ext + inward))


def inside(o, ext: float, beyond: float = 0.15):
    """A point just inside a facade opening's wall."""
    return Point(o.x + math.sin(o.yaw) * (ext + beyond), o.y - math.cos(o.yaw) * (ext + beyond))


def main_opening(interior, spot):
    """The facade door opening of a `DoorSpot` (the nearest door on floor 0)."""
    if spot is None:
        return None
    doors = [o for o in interior.openings if o.kind == "door" and o.floor == 0]
    return min(doors, key=lambda o: (math.hypot(o.x - spot.x, o.y - spot.y), o.id), default=None)


class Ring:
    """A court and the storeys round it: the court (`kind` "open": a dar's court, outside the storeys;
    "covered": a room inside them), its wall's room face, one frame per band (u along the band's court
    side, v away from the court) and, per floor, the polygon the rooms fill."""

    def __init__(self, face, court, rings: dict, kind: str):
        self.face, self.court, self.rings, self.kind = face, court, rings, kind
        self.fr = Frame.of(face)
        self.frames = side_frames(face, self.fr)

    def contact(self, poly) -> list:
        """Straight pieces of `poly`'s boundary on the court (its wall's room face)."""
        return straight(lines_of(poly.boundary.intersection(self.face.exterior.buffer(1e-4, quad_segs=1))))


def side_frames(face, fr: Frame) -> dict:
    """A frame per side of the court: u along its longest edge on that side, v pointing away from the
    court (n and s: the long sides, w and e: the short ones); a side without an edge takes the court's
    bounding box line."""
    ring = np.asarray(face.exterior.coords)[:, :2]
    c = np.asarray(face.centroid.coords[0])
    best: dict = {}
    for a, b in zip(ring[:-1], ring[1:]):
        d = b - a
        length = float(np.hypot(*d))
        if length < 1e-6:
            continue
        du, dv = fr.local(b) - fr.local(a)
        mu, mv = fr.local((a + b) / 2)
        side = (("n" if mv > 0 else "s") if abs(du) >= abs(dv) else ("e" if mu > 0 else "w"))
        if side not in best or length > best[side][0] + 1e-9:
            best[side] = (length, a, b)
    u0, v0, u1, v1 = fr.bounds(face)
    boxes = {"n": (fr.world(u0, v1), fr.world(u1, v1)), "s": (fr.world(u1, v0), fr.world(u0, v0)),
             "w": (fr.world(u0, v0), fr.world(u0, v1)), "e": (fr.world(u1, v1), fr.world(u1, v0))}
    out = {}
    for side in SIDES:
        a, b = (best[side][1], best[side][2]) if side in best else boxes[side]
        d = b - a
        angle = math.atan2(d[1], d[0])
        f = Frame(*((a + b) / 2), angle)
        if f.local(c)[1] > 0:                        # v must point away from the court
            f = Frame(*((a + b) / 2), angle + math.pi)
        out[side] = f
    return out


# --- bands ----------------------------------------------------------------------------------------
def band_cuts(job: Job, ring, poly) -> dict:
    """Positions (v in each side's frame, 0 on the court side's line; None: dropped) of the lines along
    the court's long sides, then its short sides, each kept clear of the openings of every floor."""
    pos = {}
    rest = poly
    for side in SIDES:
        fr = ring.frames[side]
        pos[side] = job.free(rest, fr, 1, 0.0)
        if pos[side] is not None:
            rest = shapely.union_all(cut(rest, fr, 1, pos[side])[0]) if not rest.is_empty else rest
    return pos


def bands(ring, poly, pos: dict) -> list:
    """The cells of a ring polygon cut by the band lines: the pieces beyond the n line, then beyond the s,
    w and e lines in turn, and slivers beside an irregular court (x)."""
    cells, rest = [], [poly]
    for side in SIDES:
        if pos[side] is None:
            continue
        fr = ring.frames[side]
        left = []
        for p in rest:
            near, far = cut(p, fr, 1, pos[side])
            cells += [Cell(q, "band", side) for q in far]
            left += near
        rest = left
    return cells + [Cell(p, "", "x") for p in rest]


def band_of(cells: list, point) -> str | None:
    """The band of the cell holding (or nearest) a point."""
    named = [c for c in cells if c.band in SIDES]
    if not named:
        return None
    return min(named, key=lambda c: (c.poly.distance(point), SIDES.index(c.band))).band


def north(cells: list) -> str:
    """The long band on the court's north side."""
    ys = {b: np.mean([c.poly.centroid.y for c in cells if c.band == b]) for b in LONG
          if any(c.band == b for c in cells)}
    if not ys:
        return "n"
    return max(sorted(ys), key=lambda b: ys[b])


def split_along(job: Job, poly, fr: Frame, axis: int, n: int, floors) -> list:
    """`poly` cut across `axis` into n nearly equal parts (each cut kept clear by `free_cut`)."""
    t0, t1 = fr.bounds(poly)[axis], fr.bounds(poly)[axis + 2]
    pieces = [poly]
    for i in range(1, n):
        at = t0 + (t1 - t0) * i / n
        rest = pieces[-1]
        pos = job.free(rest, fr, axis, at, floors)
        if pos is None:
            continue
        lo, hi = cut(rest, fr, axis, pos)
        if len(lo) != 1 or len(hi) != 1:
            continue
        pieces = pieces[:-1] + lo + hi
    return pieces


# --- the skifa --------------------------------------------------------------------------------------
def plan_skifa(job: Job, ring, band: str, poly) -> dict | None:
    """The bent skifa in the entry band `poly`: its two halves (the street door's and the court door's,
    parted by a baffle from the court wall with an arch at its far end), the rest of the band, the arch
    and the court door. The first placement that hides the court wins (drawn length toward the longer
    side, then the other way, then longer ones up to `skifa_reach`); else the first that fits."""
    if job.main is None:
        return None
    fr = ring.frames[band]
    o, spot = job.main, job.spot
    t_d = fr.local((o.x, o.y))[0]
    n_loc = fr.local(np.array([spot.x + spot.nx, spot.y + spot.ny])) - fr.local((spot.x, spot.y))
    end_door = abs(n_loc[0]) > 0.7
    b0, b1 = fr.bounds(poly)[0], fr.bounds(poly)[2]
    margin = o.width / 2 + job.clear + job.half
    if end_door:
        starts = [(b0, 1.0)] if n_loc[0] < 0 else [(b1, -1.0)]
    else:
        longer = 1.0 if b1 - t_d >= t_d - b0 else -1.0
        starts = [(t_d - longer * margin, longer), (t_d + longer * margin, -longer)]
    lo, hi = (float(v) for v in job.dar.get("skifa", [3.0, 4.5]))
    first = float(job.rng("skifa").uniform(lo, hi))
    reach = float(job.dar.get("skifa_reach", 6.0))
    lengths = [first] + [x for x in np.arange(lo, reach + 1e-9, 0.25) if x > first + 1e-9]
    fallback = None
    for length in lengths:
        for start, sgn in starts:
            got = try_skifa(job, ring, band, poly, start, sgn, float(length), t_d, end_door)
            if got is None:
                continue
            if got["hidden"]:
                return got
            fallback = fallback or got
    short = [x for x in np.arange(float(job.dar.get("screen_length", 2.0)), lo - 1e-9, 0.25)]
    for length in short + lengths:                    # no bend along the band: one through the depth
        for start, sgn in starts:
            cell = piece_of(job, ring, band, poly, start, sgn, float(length))
            alt = screen(job, ring, band, cell[0], t_d) if cell is not None else None
            if alt is not None and alt["hidden"]:
                alt["others"] = cell[1]
                return alt
    return fallback


def try_skifa(job: Job, ring, band: str, poly, start: float, sgn: float, length: float, t_d: float,
              end_door: bool) -> dict | None:
    """One skifa placement from `start` toward `sgn` (see `plan_skifa`): bent along the band by a baffle,
    else through its depth by a screen; None when it does not fit."""
    got = bent(job, ring, band, poly, start, sgn, length, t_d, end_door)
    if got is None or got["hidden"]:
        return got
    whole = shapely.union_all(list(got["skifa"]))
    alt = screen(job, ring, band, whole, t_d) if whole.geom_type == "Polygon" else None
    if alt is not None and alt["hidden"]:
        alt["others"] = got["others"]
        return alt
    return got


def screen(job: Job, ring, band: str, skifa, t_d: float) -> dict | None:
    """A skifa bent through its depth: a screen wall parallel to the facade parts the street door's strip
    from the court's, the passage (an arch) at the screen's end away from the door, the court door
    straight opposite the street door. None when the band is too shallow (`screen_strip` m a side)."""
    fr = ring.frames[band]
    o = job.main
    face = fr.local((o.x, o.y))[1] - job.ext                       # the street wall's inner face
    court = fr.bounds(skifa)[1]
    strip = float(job.dar.get("screen_strip", 1.0))
    if face - court < 2 * strip + 2 * job.half:
        return None
    first = min((face + court) / 2, face - job.half - job.steps_need)   # the street strip holds the entry steps
    fallback = None
    for at in np.arange(first, court + strip + job.half - 1e-9, -0.1):   # deeper while the court shows
        got = screen_at(job, ring, band, skifa, t_d, float(at))
        if got is not None and got["hidden"]:
            return got
        fallback = fallback or got
    return fallback


def screen_at(job: Job, ring, band: str, skifa, t_d: float, at: float) -> dict | None:
    """The skifa of `screen` with its screen wall at `at` (None when it does not fit)."""
    fr = ring.frames[band]
    if clashes(partition(skifa, fr, 1, at, job.half), job.zs([0])):
        return None                                   # the screen stays off the door (a slanted facade)
    halves = cut(skifa, fr, 1, at)
    probe = job.probe()
    outer = [p for p in halves[1] if p.distance(probe) < 1e-6]
    inner = halves[0]
    if len(outer) != 1 or len(inner) != 1 or len(halves[1]) != 1:
        return None
    outer, inner = outer[0], inner[0]
    keep = job.clear + 2 * job.half + job.door / 2
    best = None
    for p0, p1 in ring.contact(inner):
        ta, tb = sorted((fr.local(p0)[0], fr.local(p1)[0]))
        if tb - ta < 0.7 * math.dist(p0, p1) or tb - ta < 2 * keep:
            continue
        t = min(max(t_d, ta + keep), tb - keep)
        if best is None or abs(t - t_d) < abs(best[0] - t_d):
            best = (t, np.asarray(p0), np.asarray(p1))
    seg = shapely.intersection(fr.line(1, at), skifa)
    if best is None or seg.geom_type != "LineString":
        return None
    if skifa.area > job.largest.get("skifa", 99.0):
        return None
    t, p0, p1 = best
    door_at = p0 + (p1 - p0) * (t - fr.local(p0)[0]) / (fr.local(p1)[0] - fr.local(p0)[0])
    ends = sorted((np.asarray(c) for c in seg.coords[:2]), key=lambda c: -abs(fr.local(c)[0] - t_d))
    far, other = ends
    width_ = min(job.door, float(np.hypot(*(other - far))) - 0.3)
    if width_ < float(job.dar.get("arch_min", 0.8)):
        return None
    arch_at = far + (other - far) / float(np.hypot(*(other - far))) * width_ / 2
    got = {"skifa": (outer, inner), "others": [], "arch": (arch_at, width_, -fr.v), "door": (door_at, job.door, -fr.v),
           "span": None, "baffle": None}
    got["hidden"] = skifa_hidden(job, ring, got)
    return got


def piece_of(job: Job, ring, band: str, poly, start: float, sgn: float, length: float):
    """(the skifa's cell, the band's other pieces, (ta, tb)) of a skifa from `start` toward `sgn`, its ends
    kept clear by `free_cut`; None when it does not fit (too short, too small, holding a shop front)."""
    fr = ring.frames[band]
    b0, b1 = fr.bounds(poly)[0], fr.bounds(poly)[2]
    ta, tb = sorted((start, start + sgn * length))
    ta, tb = max(ta, b0), min(tb, b1)
    if ta > b0 + 0.05:
        ta = job.free(poly, fr, 0, ta, [0], hi=ta if sgn > 0 else math.inf)
    if tb < b1 - 0.05 and ta is not None:
        tb = job.free(poly, fr, 0, tb, [0], lo=tb if sgn < 0 else -math.inf)
    if ta is None or tb is None or tb - ta < 1.2:
        return None
    rest, others = [poly], []
    if ta > b0 + 0.05:
        before, rest = cut(poly, fr, 0, ta)
        others += before
    if tb < b1 - 0.05:
        rest, after = cut(shapely.union_all(rest), fr, 0, tb)
        others += after
    probe = job.probe()
    mine = [p for p in rest if p.distance(probe) < 1e-6]
    if len(mine) != 1:
        return None
    skifa = mine[0]
    others += [p for p in rest if p is not skifa]
    if (not job.fits(skifa, "skifa") or skifa.area > job.largest.get("skifa", 99.0)
            or any(skifa.contains(p) for p in job.fronts)):
        return None                                   # a shop front or another door stays out of the skifa
    return skifa, others, (ta, tb)


def bent(job: Job, ring, band: str, poly, start: float, sgn: float, length: float, t_d: float,
         end_door: bool) -> dict | None:
    """The skifa bent along the band (see `try_skifa`)."""
    got = piece_of(job, ring, band, poly, start, sgn, length)
    if got is None:
        return None
    skifa, others, (ta, tb) = got
    fr = ring.frames[band]
    probe = job.probe()
    far = tb if sgn > 0 else ta
    w_c = job.door
    keep = job.clear + 2 * job.half + w_c / 2         # a court opening keeps a whole partition (oblique walls)
    best = None
    for p0, p1 in ring.contact(skifa):
        ta_, tb_ = sorted((fr.local(p0)[0], fr.local(p1)[0]))
        if tb_ - ta_ < 0.7 * math.dist(p0, p1) or tb_ - ta_ < 2 * keep:
            continue                                  # a piece across the band: the court's corner
        if sgn > 0:
            t = min(tb_, far) - keep
            ok = t >= ta_ + keep - 1e-9
        else:
            t = max(ta_, far) + keep
            ok = t <= tb_ - keep + 1e-9
        if ok and (best is None or sgn * t > sgn * best[0]):
            best = (t, p0, p1)
    plain = {"skifa": (skifa,), "others": others, "arch": None, "door": None, "span": (ta, tb), "baffle": None}
    if best is None:                                  # no court wall: it opens into the next room (a bend too)
        plain["hidden"] = skifa_hidden(job, ring, plain)
        return plain
    t_cd, p0, p1 = best
    p0, p1 = np.asarray(p0), np.asarray(p1)
    du = fr.local(p1)[0] - fr.local(p0)[0]
    door_at = p0 + (p1 - p0) * (t_cd - fr.local(p0)[0]) / du
    t_bf = t_cd - sgn * (w_c / 2 + job.clear + job.half)
    gap_needed = (0.9 + job.half) if end_door else (job.main.width / 2 + job.clear + job.half)
    plain["door"] = (door_at, w_c, -fr.v)
    plain["hidden"] = skifa_hidden(job, ring, plain)
    if sgn * (t_bf - (start if end_door else t_d)) < gap_needed or clashes(partition(skifa, fr, 0, t_bf, job.half),
                                                                         job.zs([0])):
        return plain                                  # no room for a baffle (off the door): one skifa
    halves = cut(skifa, fr, 0, t_bf)
    outer = [p for p in halves[0] + halves[1] if p.distance(probe) < 1e-6]
    inner = [p for p in halves[0] + halves[1] if p.distance(probe) >= 1e-6]
    if len(outer) != 1 or len(inner) != 1:
        return plain
    seg = shapely.intersection(fr.line(0, t_bf), skifa)
    if seg.geom_type != "LineString" or seg.length < 1.0:
        return plain
    a, b = (np.asarray(c) for c in seg.coords[:2])
    if fr.local(a)[1] > fr.local(b)[1]:
        a, b = b, a                                   # a on the court side, b at the outer wall
    depth = float(np.hypot(*(b - a)))
    arch = max(job.door, (1.0 - float(job.dar.get("baffle", 0.6))) * depth)
    arch = min(arch, depth - float(job.dar.get("baffle_min", 0.3)))
    if arch < float(job.dar.get("arch_min", 0.8)):
        return plain
    arch_at = b - (b - a) / depth * arch / 2
    got = {"skifa": (outer[0], inner[0]), "others": others, "arch": (arch_at, arch, fr.u * sgn),
           "door": (door_at, w_c, -fr.v), "span": (ta, tb), "baffle": t_bf}
    got["hidden"] = skifa_hidden(job, ring, got)
    return got


def skifa_hidden(job: Job, ring, got: dict) -> bool:
    """True when no straight line from the street door reaches the court through this skifa."""
    half = job.half + 0.02
    o = job.main
    front = np.array([-math.sin(o.yaw), math.cos(o.yaw)])
    gaps = [R.slot((o.x, o.y), front, o.width, half, job.ext + half)]
    if got["arch"] is not None:
        at, w, toward = got["arch"]
        gaps.append(R.slot(at, toward, w, half, half))
    if got["door"] is None:
        return True
    door_at, wc, into = got["door"]
    deep = (job.court_wall if ring.kind == "open" else 0.0) + half
    gaps.append(R.slot(door_at, into, wc, deep, half))
    return not R.seen(R.door_points(o, job.ext), ring.court, list(got["skifa"]), gaps, job.half)


# --- the T room ------------------------------------------------------------------------------------
def t_room(job: Job, ring, band: str, poly) -> list:
    """The main band's bit: its central court door (`court_door` wide, a double leaf) with up to two
    court windows, its kbou opposite the door where the band is `t_depth` deep (the rest of that back
    strip returned as cells that join the maqsuras), and a bortal in rich houses. Returns cells, the
    bit first."""
    fr = ring.frames[band]
    bit = Cell(poly, "bit", band, "middle")
    pieces = ring.contact(poly)
    if not pieces:
        return [bit]
    p0, p1 = max(pieces, key=lambda p: (math.dist(*p), p))
    center = (np.asarray(p0) + np.asarray(p1)) / 2
    wide = float(job.dar.get("court_door", 1.2))
    if math.dist(p0, p1) < wide + 2 * (job.clear + job.half):
        wide = job.door
    if math.dist(p0, p1) < wide + 2 * (job.clear + job.half):
        return [bit]                                  # no central door fits: the doors pass gives one
    out = [bit]
    rich = job.wealth > float(job.dar.get("bortal_wealth", 0.75))
    bortal = float(job.dar.get("bortal", 1.8))
    if (rich and ring.kind == "open"
            and depth_at(fr, poly, center) >= job.minimums.get("bit", (7.0, 2.0))[1] + bortal):
        front, back = _split_cross(poly, fr, fr.local(center)[1] + bortal)
        if front is not None and back is not None:
            gallery = Cell(front, "bortal", band, "bortal")
            gallery.doors.append(("arches", None))
            bit.poly = back
            out.append(gallery)
            seg = shapely.intersection(fr.line(0, fr.local(center)[0]), back)
            ends = shapely.get_coordinates(seg)
            center = min(ends, key=lambda e: fr.local(e)[1]) if len(ends) else center
            bit.doors.append(("inner", gallery, center, wide))
            poly = back
    if not bit.doors:
        bit.doors.append(("court_door", None, center, wide))
        bit.doors.append(("court_windows", None, center, wide))
    if depth_at(fr, poly, center) >= float(job.dar.get("t_depth", 3.0)):
        out += kbou(job, fr, bit, poly, center)
    return out


def depth_at(fr: Frame, poly, point) -> float:
    """Length of the line across the band (along v) through `point` inside `poly`."""
    return float(shapely.intersection(fr.line(0, fr.local(point)[0]), poly).length)


def _split_cross(poly, fr: Frame, at: float) -> tuple:
    """(court side, outer side) of `poly` cut along the band at v = `at` (single polygons, else None)."""
    near, far = cut(poly, fr, 1, at)
    return (near[0] if len(near) == 1 else None), (far[0] if len(far) == 1 else None)


def kbou(job: Job, fr: Frame, bit: Cell, poly, center) -> list:
    """The kbou: the middle `kbou` m of a back strip `kbou_depth` deep opposite the door, part of the bit
    (its `alcove`); returns the strip's other pieces (they join the maqsuras)."""
    seg = shapely.intersection(fr.line(0, fr.local(center)[0]), poly)
    if seg.is_empty:
        return []
    back = max(fr.local(c)[1] for c in shapely.get_coordinates(seg))
    front, strip = _split_cross(poly, fr, back - float(job.dar.get("kbou_depth", 1.0)))
    if front is None or strip is None:
        return []
    lo, hi = (float(v) for v in job.dar.get("kbou", [1.8, 2.6]))
    size = float(job.rng("kbou").uniform(lo, hi))
    c = fr.local(center)[0]
    left = job.free(strip, fr, 0, c - size / 2, [0], lo=c - size / 2 - 0.5, hi=c - job.door / 2)
    right = job.free(strip, fr, 0, c + size / 2, [0], lo=c + job.door / 2, hi=c + size / 2 + 0.5)
    if left is None or right is None:
        return []
    a, rest = cut(strip, fr, 0, left)
    if len(rest) != 1:
        return []
    mid, b = cut(rest[0], fr, 0, right)
    if len(mid) != 1:
        return []
    whole = union(front, mid[0])
    if whole is None:
        return []
    bit.poly, bit.alcove = whole, mid[0]
    return [Cell(p, "", bit.band, "kbou_side") for p in a + b]


# --- the ground floor -------------------------------------------------------------------------------
def ground(job: Job, ring, pos: dict, poly) -> tuple:
    """(cells, skifa plan) of floor 0 of a house round a court; `poly` is the storey less the newel cell."""
    cells = bands(ring, poly, pos)
    probe = job.probe() if job.spot is not None else None
    entry = band_of(cells, probe) if probe is not None else None
    main = (("s" if entry == "n" else "n") if entry in LONG else north(cells))
    polys = {band: [c.poly for c in cells if c.band == band] for band in SIDES}
    out = [c for c in cells if c.band == "x"]
    plan = None
    if entry is not None and polys[entry]:
        host = min(polys[entry], key=lambda p: (p.distance(probe), -p.area))
        plan = plan_skifa(job, ring, entry, host)
        if plan is None or not plan["hidden"]:
            plan = l_skifa(job, ring, entry, host, polys) or plan
        if plan is not None and not plan["hidden"] and ring.kind == "open":
            whole = shapely.union_all(list(plan["skifa"]))          # no bend fits: the skifa opens into a room
            plan = {**plan, "skifa": tuple(parts(snap(whole)))[:1] if len(parts(snap(whole))) == 1 else plan["skifa"],
                    "arch": None, "door": None, "hidden": True}
            if len(plan["skifa"]) != 1 or "turn" in plan:
                plan = None
        if plan is not None:
            polys[entry] = [p for p in polys[entry] if p is not host] + plan["others"]
            if "turn" in plan:
                other, piece, rest = plan["turn"]
                polys[other] = [p for p in polys[other] if p is not piece] + rest
            bands_of = [entry, plan["turn"][0]] if "turn" in plan else [entry] * len(plan["skifa"])
            halves = [Cell(p, "skifa", b, "skifa") for p, b in zip(plan["skifa"], bands_of)]
            if plan["arch"] is not None:
                halves[0].doors.append(("arch", halves[1], plan["arch"][0], plan["arch"][1]))
            if plan["door"] is not None:
                halves[-1].doors.append(("court_door", None, plan["door"][0], plan["door"][1]))
            out += halves
    for band in SIDES:
        if polys[band]:
            out += band_cells(job, ring, band, polys[band], band == main)
    return out, plan


def l_skifa(job: Job, ring, entry: str, host, polys: dict) -> dict | None:
    """An L-shaped skifa where the entry band is too short to bend in: the stretch of the entry band from
    the door to its end, then the end of the next band (its court door there, as far from the turn as
    fits), the two parted by a baffle along the band line with an arch at its outer end. The first that
    hides the court, trying the next band's length up to `skifa_reach` m."""
    o, spot = job.main, job.spot
    if o is None:
        return None
    fr = ring.frames[entry]
    probe = job.probe()
    t_d = fr.local((o.x, o.y))[0]
    margin = o.width / 2 + job.clear + job.half
    for other in SIDES:
        if other == entry:
            continue
        touching = sorted(((shared(p, host), i) for i, p in enumerate(polys[other])), reverse=True)
        if not touching or touching[0][0] < 1.0:
            continue
        piece = polys[other][touching[0][1]]
        sgn = 1.0 if fr.local(piece.centroid.coords[0])[0] > t_d else -1.0
        start = t_d - sgn * margin
        b0, b1 = fr.bounds(host)[0], fr.bounds(host)[2]
        if not b0 + 0.05 < start < b1 - 0.05:
            outer, rest_host = [host], []
        else:
            lo, hi = cut(host, fr, 0, job.free(host, fr, 0, start, [0], hi=start if sgn > 0 else math.inf,
                                               lo=start if sgn < 0 else -math.inf) or start)
            near_part, far_part = (hi, lo) if sgn > 0 else (lo, hi)
            outer = [p for p in near_part if p.distance(probe) < 1e-6]
            rest_host = far_part + [p for p in near_part if p.distance(probe) >= 1e-6]
        if len(outer) != 1 or shared(outer[0], piece) < 1.0 or any(outer[0].contains(p) for p in job.fronts):
            continue
        got = turn(job, ring, other, piece, outer[0], rest_host)
        if got is not None:
            return got
    return None


def turn(job: Job, ring, other: str, piece, outer, rest_host: list) -> dict | None:
    """The second leg of an L-shaped skifa in band `other` (see `l_skifa`)."""
    fo = ring.frames[other]
    b0, b1 = fo.bounds(piece)[0], fo.bounds(piece)[2]
    dirn = 1.0 if abs(fo.local(outer.centroid.coords[0])[0] - b0) < abs(fo.local(outer.centroid.coords[0])[0] - b1) else -1.0
    end = b0 if dirn > 0 else b1
    reach = float(job.dar.get("skifa_reach", 6.0))
    keep = job.clear + 2 * job.half + job.door / 2
    for length in np.arange(1.5, reach + 1e-9, 0.25):
        at = job.free(piece, fo, 0, end + dirn * length, [0])
        if at is None:
            continue
        lo, hi = cut(piece, fo, 0, at)
        near_part, rest = (lo, hi) if dirn > 0 else (hi, lo)
        inner = [p for p in near_part if shared(p, outer) > 1.0]
        if len(inner) != 1:
            continue
        inner = inner[0]
        rest = rest + [p for p in near_part if p is not inner]
        if not job.minimums.get("skifa", (0.0, 0.0))[0] <= outer.area + inner.area <= job.largest.get("skifa", 99.0):
            continue
        best = None
        for p0, p1 in ring.contact(inner):
            ta, tb = sorted((fo.local(p0)[0], fo.local(p1)[0]))
            if tb - ta < 0.7 * math.dist(p0, p1) or tb - ta < 2 * keep:
                continue
            t = (tb - keep) if dirn > 0 else (ta + keep)
            if best is None or dirn * t > dirn * best[0]:
                best = (t, np.asarray(p0), np.asarray(p1))
        if best is None:
            continue
        t, p0, p1 = best
        door_at = p0 + (p1 - p0) * (t - fo.local(p0)[0]) / (fo.local(p1)[0] - fo.local(p0)[0])
        line = max(contact(outer, inner), key=lambda q: math.dist(*q), default=None)
        if line is None:
            continue
        a, b = (np.asarray(c) for c in line)
        if ring.court.distance(Point(*a)) > ring.court.distance(Point(*b)):
            a, b = b, a                               # a toward the court, b at the outer wall
        depth = float(np.hypot(*(b - a)))
        arch = min(max(job.door, (1.0 - float(job.dar.get("baffle", 0.6))) * depth),
                   depth - float(job.dar.get("baffle_min", 0.3)))
        if arch < float(job.dar.get("arch_min", 0.8)):
            continue
        toward = np.asarray(inner.centroid.coords[0]) - np.asarray(outer.centroid.coords[0])
        got = {"skifa": (outer, inner), "others": rest_host, "turn": (other, piece, rest), "span": None,
               "arch": (b - (b - a) / depth * arch / 2, arch, toward / max(float(np.hypot(*toward)), 1e-9)),
               "door": (door_at, job.door, -fo.v), "baffle": None}
        got["hidden"] = skifa_hidden(job, ring, got)
        if got["hidden"]:
            return got
    return None


def band_cells(job: Job, ring, band: str, polys: list, main: bool) -> list:
    """The cells of one band of floor 0: long bands cut where the court's short sides extend (corners and
    middle), the main band's middle the T room; short bands split in two when long."""
    fr = ring.frames[band]
    if band not in LONG:
        out = []
        for p in polys:
            t0, t1 = fr.bounds(p)[0], fr.bounds(p)[2]
            n = 2 if t1 - t0 >= float(job.dar.get("short_split", 4.4)) else 1
            out += [Cell(q, "", band, "short") for q in split_along(job, p, fr, 0, n, [0])]
        return out
    out = []
    for p in polys:
        pieces, corner = [p], []
        for side in ("w", "e"):
            f = ring.frames[side]
            rest = shapely.union_all(pieces) if pieces else None
            if rest is None or rest.is_empty:
                break
            at = job.free(rest, f, 1, 0.0, [0])
            if at is None:
                continue
            near, far = cut(rest, f, 1, at)
            pieces, corner = near, corner + far
        out += [Cell(q, "", band, "middle") for q in pieces] + [Cell(q, "", band, "corner") for q in corner]
    middles = [c for c in out if c.part == "middle"]
    if main and middles:
        mid = max(middles, key=lambda c: c.poly.area)
        out = [c for c in out if c is not mid] + t_room(job, ring, band, mid.poly)
        middles = [c for c in middles if c is not mid]
    bit_max = float(job.dar.get("bit_max", 6.0))
    for c in middles:
        t0, t1 = fr.bounds(c.poly)[0], fr.bounds(c.poly)[2]
        n = 2 if t1 - t0 > bit_max else 1
        out = [x for x in out if x is not c]
        out += [Cell(q, "bit", band, "middle") for q in split_along(job, c.poly, fr, 0, n, [0])]
    return out


def main_band(cells: list) -> str | None:
    """The band holding the T room (the bit with a door planned on the court or its bortal)."""
    t = next((c for c in cells if c.type == "bit" and c.part == "middle" and
              any(d[0] in ("court_door", "inner") for d in c.doors)), None)
    return None if t is None else t.band


def join_kbou_sides(cells: list) -> list:
    """The back strip's pieces beside the kbou join the maqsura (or bit) they touch most: L shapes."""
    out = [c for c in cells if c.part != "kbou_side"]
    for c in (c for c in cells if c.part == "kbou_side"):
        hosts = sorted(((shared(c.poly, o.poly), i) for i, o in enumerate(out)
                        if o.type in ("maqsura", "", "bit") and o.band == c.band and o.alcove is None),
                       reverse=True)
        for s, i in hosts:
            merged = union(out[i].poly, c.poly) if s >= 1e-3 else None
            if merged is not None:
                out[i].poly = merged
                break
        else:
            out.append(c)                             # no host: a piece the clean-up places
    return out


def upper(job: Job, ring, pos: dict, poly, floor: int) -> list:
    """The cells of an upper floor: the same bands, ghorfas (split above `bit_max`)."""
    bit_max = float(job.dar.get("bit_max", 6.0))
    out = []
    for c in bands(ring, poly, pos):
        if c.band == "x":
            c.type = "ghorfa"                         # upstairs a sliver is a ghorfa in the making: merged when small
            out.append(c)
            continue
        fr = ring.frames[c.band]
        t0, t1 = fr.bounds(c.poly)[0], fr.bounds(c.poly)[2]
        n = max(1, math.ceil((t1 - t0) / bit_max - 1e-9))
        out += [Cell(q, "ghorfa", c.band, "upper") for q in split_along(job, c.poly, fr, 0, n, [floor])]
    return out


def without(poly, square, thin: float = 0.45, zones=(), half: float = 0.1):
    """(the floor's polygon less the newel cell, the droj room): strips thinner than 2 x `thin` left
    between the cell and a wall join the droj (a landing beside the stair), not a room beyond it."""
    if square is None:
        return poly, None
    rest = polygonal(shapely.difference(poly, square, grid_size=1e-6))
    opened = rest.buffer(-thin, join_style="mitre").buffer(thin, join_style="mitre")
    fr = Frame.of(square)                             # only what lies straight beside the cell, not along a wall
    u0, v0, u1, v1 = fr.bounds(square)
    beside = fr.rect(u0 - 2 * thin, v0, u1 + 2 * thin, v1).union(fr.rect(u0, v0 - 2 * thin, u1, v1 + 2 * thin))
    loose = parts(shapely.difference(rest, opened, grid_size=1e-6))
    strips = [p for q in loose for p in parts(shapely.intersection(q, beside, grid_size=1e-6))
              if p.area > 0.01 and p.distance(square) < 1e-6
              and S.walls_clear(union(square, p) or p, poly, list(zones), half)]
    if sum(p.area for p in strips) > 0.6 * square.area:
        strips = []                                   # a narrow house: the strips are rooms, not a landing
    droj = parts(snap(shapely.union_all([square.intersection(poly)] + strips)))
    if strips:
        rest = shapely.difference(rest, shapely.union_all(strips), grid_size=1e-6)
    droj.sort(key=lambda p: -p.area)
    got = parts(rest) + droj[1:]                      # a part of the cell cut off by the wall stays a room
    return (shapely.union_all(got) if got else poly), (droj[0] if droj else square)


# --- the house -----------------------------------------------------------------------------------
def plan(interior, outside, style: dict) -> None:
    """Floor plans of a courtyard house; a storey whose court closed (a narrow ring) goes to `compact`."""
    from . import compact
    st0 = interior.storeys[0]
    holes = sorted((Polygon(h) for h in outside.b.footprint.interiors), key=lambda p: -p.area)
    whole = getattr(interior, "full0", None) or st0.polygon     # a souk house's floor 0 less its shop is cut
    face = next((Polygon(h) for h in whole.interiors if holes and Polygon(h).contains(
        holes[0].representative_point())), None)
    if not holes or face is None:
        compact.plan(interior, outside, style)
        return
    court = holes[0]
    before = _state(interior)
    first = None
    for room_for_steps in (True, False):              # the bent entry before the steps' room (47.1/48.1)
        if not room_for_steps:
            first = _state(interior)
            _restore(interior, before)
        job = Job(interior, outside, style)
        if not room_for_steps:
            job.steps_need = 0.0
        ring = Ring(face, court, {st.floor: snap(st.polygon) for st in interior.storeys}, "open")
        court_room = Room(-1, 0, R.COURT, court, st0.z, outside.b.height, open=True)
        build(job, ring, court_room)
        features(job, court)
        if not R.sees_court(interior) or job.steps_need <= 0.0 and room_for_steps:
            break
        if not room_for_steps:
            _restore(interior, first)                 # the court shows either way: keep the steps' room


STATE = ("rooms", "openings", "stairs", "features", "warnings", "piers", "flats", "focus", "rules", "entry")


def _state(interior) -> dict:
    import copy
    return {k: copy.deepcopy(getattr(interior, k)) for k in STATE if hasattr(interior, k)}


def _restore(interior, state: dict) -> None:
    import copy
    for k, v in state.items():
        setattr(interior, k, copy.deepcopy(v))


def build(job: Job, ring, court_room, wells=None) -> None:
    """Rooms, doors, stairs and roof of a house round a court (`ring`); `court_room` is the dar's open
    court (outside the storeys) or the covered court of floor 0; `wells` the light wells upstairs."""
    interior = job.interior
    job.court_poly = court_room.polygon if court_room is not None and court_room.open else None
    square = newel_square(job, ring)
    top = stair_top(job)
    square = square if top > 0 else None
    served = min(top, interior.floors - 1) if square is not None else -1
    split = {f: (without(p, square, job.thin, job.zs([f]), job.half) if f <= served else (p, None))
             for f, p in ring.rings.items()}
    pos = band_cuts(job, ring, split[0][0])
    cells, skifa = ground(job, ring, pos, split[0][0])
    cells = join_kbou_sides(cells)
    per_floor = {0: cells}
    for st in interior.storeys[1:]:
        per_floor[st.floor] = upper(job, ring, pos, split[st.floor][0], st.floor)
    keep = R.KEEP + ("bortal",)
    for f, cs in per_floor.items():
        if split[f][1] is not None:
            cs = cs + [Cell(split[f][1], "droj", "", "stair")]
        takes = ()
        if ring.kind == "covered" and (f == 0 or wells.get(f) is not None):
            cs = cs + [Cell(court_room.polygon if f == 0 else wells[f], R.COURT if f == 0 else "well", "", "court")]
            takes = (R.COURT, "well")
        per_floor[f] = absorb(cs, job.minimums, keep, job.piece, takes, job.largest)
    for f in per_floor:
        per_floor[f] = repair_cells(job, per_floor[f], f)
    job.frames = ring.frames
    per_floor[0] = P.assign(job, per_floor[0])
    rooms_from(job, per_floor, ring, court_room)
    finish(job, ring, square, top)


def repair_cells(job: Job, cells: list, floor: int) -> list:
    """Cells whose partition meets a wall too near a facade opening become one (the cut dropped), before
    the program types them: the smaller joins the larger; a skifa, stair cell or court takes its neighbour."""
    zones = [z for z in job.zones.get(floor, []) if z is not None]
    fixed = R.KEEP + ("bortal",)
    for _ in range(len(cells)):
        pair = next(((a, b) for i, a in enumerate(cells) for b in cells[i + 1:]
                     if not (a.type in fixed and b.type in fixed)
                     and R.clash_polys(a.poly, b.poly, zones, job.half * 2)), None)
        if pair is None:
            break
        a, b = pair
        keep, gone = (a, b) if (a.type in fixed or (b.type not in fixed and a.poly.area >= b.poly.area)) else (b, a)
        merged = union(keep.poly, gone.poly)
        if merged is None:
            break
        keep.poly = merged
        if keep.type in job.largest and keep.type != "skifa" and merged.area > job.largest[keep.type]:
            keep.type = "bit"
        cells = [c for c in cells if c is not gone]
    return cells


def rooms_from(job: Job, per_floor: dict, ring, court_room) -> None:
    """Rooms from the cells of every floor; the dar's open court last on floor 0."""
    interior = job.interior
    made = {}
    for st in interior.storeys:
        for c in per_floor.get(st.floor, []):
            if not c.type:
                c.type = "ghorfa" if st.floor else "bit"
            if c.type == R.COURT and ring.kind == "covered":
                room = court_room
                room.id, room.polygon = len(interior.rooms), c.poly
            else:
                room = Room(len(interior.rooms), st.floor, c.type, c.poly, st.z, st.height, open=c.type == "well",
                            alcove=c.alcove)
            if c.type == "well":
                job.wells[st.floor] = room
            interior.rooms.append(room)
            made[id(c)] = (c, room)
    if ring.kind == "open" and court_room is not None:
        court_room.id = len(interior.rooms)
        interior.rooms.append(court_room)
    job.made = made
    job.court_room = court_room


def finish(job: Job, ring, square, top: int, doors=None) -> None:
    """Openings, stairs, connections and the roof, once the rooms stand (`doors`: the program's doors,
    `program_doors` by default)."""
    interior = job.interior
    R.repair(interior, job.zones)
    R.assign(interior)
    (doors or program_doors)(job, ring)
    skifa_way(job)
    newel_record(job, square, top)
    roof(job, top)
    entry_steps(job)
    R.connect(interior)
    if ring is not None and ring.kind == "covered":
        galleries(job)
    R.unclash(interior)
    for o in interior.openings:                       # merges and galleries moved some walls
        if o.kind in R.FACADE and o.piece:
            o.rooms = (-1, -1)
    interior.warnings = [w for w in interior.warnings if "no floor behind" not in w]
    R.assign(interior)
    for r in interior.rooms:
        r.lit = any(o.lit for o in interior.openings if o.rooms[0] == r.id and o.kind in ("window", "balcony"))
    upper_stores(job)
    R.renumber(interior)


def upper_stores(job: Job) -> None:
    """An upstairs ghorfa left under its minimum (a corner the gallery cut off) is a store of its size (47.1)."""
    big = job.largest.get("bit_el_mouna", 8.0)
    for r in job.interior.rooms:
        if (r.floor > 0 and r.type == "ghorfa" and not job.fits(r.polygon, "ghorfa")
                and job.fits(r.polygon, "bit_el_mouna") and r.polygon.area <= big):
            r.type = "bit_el_mouna"


def galleries(job: Job) -> None:
    """Upstairs, where the light well cuts rooms off, a `bortal` (a gallery `gallery` m wide) along the
    well's side that joins them to the reached rooms; the doors pass then runs again."""
    interior = job.interior
    wide = float(job.compact.get("gallery", 1.0))
    for f in sorted(job.wells):
        for _ in range(4):
            if not gallery(job, f, wide):
                break


def gallery(job: Job, f: int, wide: float) -> bool:
    """One gallery on floor f (see `galleries`); False when none is needed or none fits."""
    interior = job.interior
    well = job.wells[f]
    seen = R.reached(interior)
    cut_off = [r for r in interior.rooms if r.floor == f and r.id not in seen and r.type not in R.VOIDS]
    if not cut_off or well not in interior.rooms or well.type != "well":
        return False
    fr = Frame.of(well.polygon)
    u0, v0, u1, v1 = fr.bounds(well.polygon)
    strips = [fr.rect(u0, v0, u1, v0 + wide), fr.rect(u0, v1 - wide, u1, v1),
              fr.rect(u0, v0, u0 + wide, v1), fr.rect(u1 - wide, v0, u1, v1)]
    near = [r for r in interior.rooms if r.floor == f and r is not well and r.type not in R.VOIDS]

    def score(strip):
        touch = [r for r in near if shared(r.polygon, strip.intersection(well.polygon)) > 1.0]
        return (any(r.id in seen for r in touch), sum(r in cut_off for r in touch), strip.area)

    storey = interior.storeys[f].polygon
    ok = [s for s in strips if parts(snap(s.intersection(well.polygon)))
          and S.walls_clear(max(parts(snap(s.intersection(well.polygon))), key=lambda p: p.area), storey,
                            job.zs([f]), job.half)]
    best = max(ok, key=score) if ok else None
    if best is None or not score(best)[0] or not score(best)[1]:
        return ring_gallery(job, well, wide)
    walk = max(parts(snap(best.intersection(well.polygon))), key=lambda p: p.area)
    rest = parts(snap(well.polygon.difference(walk)))
    if rest and max(p.area for p in rest) >= wide * wide:
        well.polygon = max(rest, key=lambda p: p.area)
        room = Room(R.next_id(interior), f, "bortal", walk, well.z, well.height)
        interior.rooms.append(room)
    else:
        well.type, well.open, room = "bortal", False, well
    interior.openings = [o for o in interior.openings if not (o.kind == "inner_window" and o.floor == f
                         and room.polygon.distance(Point(o.x, o.y)) < 0.05)]
    R.connect(interior)
    return True


def ring_gallery(job: Job, well, wide: float) -> bool:
    """No strip joins the cut-off rooms: a gallery all round the well, the void `wide` m smaller each
    side (the whole well becomes a covered bortal when the void would be under `wide` across)."""
    interior = job.interior
    void = parts(snap(well.polygon.buffer(-wide, join_style="mitre")))
    void = max(void, key=lambda p: p.area) if void else None
    if void is not None and width(void) >= wide:
        walk = parts(snap(well.polygon.difference(void)))
        if len(walk) == 1 and S.walls_clear(walk[0], interior.storeys[well.floor].polygon, job.zs([well.floor]),
                                            job.half):
            well.polygon = void
            interior.rooms.append(Room(R.next_id(interior), well.floor, "bortal", walk[0], well.z, well.height))
            interior.openings = [o for o in interior.openings if not (o.kind == "inner_window" and
                                 o.floor == well.floor and walk[0].distance(Point(o.x, o.y)) < 0.05)]
            R.connect(interior)
            return True
    well.type, well.open = "bortal", False
    interior.openings = [o for o in interior.openings if not (o.kind == "inner_window" and o.floor == well.floor
                         and well.id in o.rooms)]
    R.connect(interior)
    return True


def stair_top(job: Job) -> int:
    """The floor a house's newel stair reaches: the roof through the stair room, else the top floor."""
    floors = job.interior.floors
    if job.roof is not None and job.roof.stair is not None and not job.roof_ladder:
        return floors
    return floors - 1


def newel_square(job: Job, ring):
    """The newel cell: inside the stair room's square when the roof has one, else the first corner of
    the long bands where it fits (the bands off the main one first, farthest from the street door)."""
    interior = job.interior
    top = stair_top(job)
    if top <= 0:
        return None
    served = [ring.rings[f] for f in range(min(top, interior.floors - 1) + 1)]
    region = polygonal(shapely.intersection_all(served))
    if ring.kind == "covered":
        region = region.difference(ring.court)
    zones = job.zs(list(range(min(top, interior.floors - 1) + 1)), shallow=True)
    big = float(job.stairs.get("newel", 2.4))
    least = float(job.stairs.get("newel_min", 1.9))
    if job.roof is not None and job.roof.stair is not None:
        sq = S.under_stair_room(job.roof.stair, region, zones, job.half, least)
        if sq is not None:
            return sq
        interior.warnings.append("the newel stair does not fit under the roof's stair room: it stands in a "
                                 "corner and a ladder rises into the stair room")
        job.roof_ladder = True
    return S.in_corner(corners(job, ring), ring.fr, region, zones, job.half, big, least)


def corners(job: Job, ring) -> list:
    """The ring's outer corners (u, v, du, dv), farthest from the street door first."""
    fr = ring.fr
    u0, v0, u1, v1 = fr.bounds(ring.rings[0])
    out = [(u0, v0, 1.0, 1.0), (u1, v0, -1.0, 1.0), (u1, v1, -1.0, -1.0), (u0, v1, 1.0, -1.0)]
    if job.spot is None:
        return out
    d = fr.local((job.spot.x, job.spot.y))
    return sorted(out, key=lambda c: (-math.hypot(c[0] - d[0], c[1] - d[1]), c[0], c[1]))


def newel_record(job: Job, square, top: int) -> None:
    """The `Stair` of the newel cell, its door on the same side on every floor, and its doors."""
    interior = job.interior
    if square is None:
        if interior.floors > 1:
            ladder_up(job)
        return
    droj = [r for r in interior.rooms if r.type == "droj" and r.floor < interior.floors]
    regions = [r.polygon for r in interior.rooms if r.floor in [d.floor for d in droj] and r.type != "droj"
               and not R.is_court(r) and r.type != "well"]
    toward = job.roof.door[2] if (job.roof is not None and job.roof.stair is not None) else None
    floors = [shapely.union_all([r.polygon for r in interior.rooms if r.floor == d.floor and r.type != "droj"
                                 and r.type != "well" and not (R.is_court(r))]) for d in droj]
    door = S.door_side(square, floors, toward) or S.door_side(square, [shapely.union_all(regions)])
    stair = S.newel(square, door, top, interior.fh, job.stairs)
    stair.rooms = [d.id for d in sorted(droj, key=lambda r: r.floor)]
    interior.stairs.append(stair)
    if door is None:
        return
    line = S.door_line(square, door)
    for d in droj:
        for r in sorted(interior.rooms, key=lambda r: r.id):
            if r.floor == d.floor and r is not d and r.type not in ("well",) and not R.is_court(r):
                if R.pieces_between(interior, d, r) and any(
                        LineString(line).distance(Point(*np.add(p[0], p[1]) / 2)) < 0.05
                        for p in R.pieces_between(interior, d, r)):
                    if R.place(interior, d, r, "inner", job.door, job.door_height, on=line) is not None:
                        break


def ladder_up(job: Job) -> None:
    """No newel cell fits: a ladder from floor 0 up (a warning)."""
    interior = job.interior
    region = polygonal(shapely.intersection_all([st.polygon for st in interior.storeys]))
    if region.is_empty:                               # stepped masses that share no floor
        interior.warnings.append("no newel stair fits: a ladder goes up, but no spot stands under every floor")
        return
    fr = Frame.of(region)
    w, d = (float(v) for v in job.stairs.get("ladder", [0.6, 1.2]))
    keep = job.entry_keep()
    spot = S.ladder(region.difference(keep), fr, region.centroid.coords[0], (w, d)) if keep is not None else None
    spot = spot or S.ladder(region, fr, region.centroid.coords[0], (w, d))
    interior.warnings.append("no newel stair fits: a ladder goes up")
    if spot is None:
        return
    rooms = []
    for st in interior.storeys:
        r = max((r for r in interior.rooms if r.floor == st.floor and not R.is_court(r)),
                key=lambda r: (r.polygon.intersection(spot).area, -r.id), default=None)
        if r is not None:
            rooms.append(r.id)
    n = S.risers(interior.fh, 0.3)
    interior.stairs.append(S.Stair("ladder", spot, 0, interior.floors - 1, n, interior.fh / n, 0.0, w,
                                   None, rooms))


def program_doors(job: Job, ring) -> None:
    """The doors the program wants: the skifa's arch and court door, the T room's, the maqsuras into
    their bit, every other room of floor 0 on the court, the ghorfas into each other."""
    interior = job.interior
    court = job.court_room
    kind = "court_door" if ring.kind == "open" else "inner"
    rng = job.court
    for c, room in sorted(job.made.values(), key=lambda t: t[1].id):
        for spec in c.doors:
            if spec[0] == "arch":
                other = job.made.get(id(spec[1]))
                if other is not None:
                    R.place(interior, room, other[1], "arch", spec[3], job.door_height, at=spec[2],
                            clear=-job.half)          # the baffle's arch reaches the outer wall
            elif spec[0] in ("court_door", "inner") and spec[1] is None:
                o = R.place(interior, room, court, kind, spec[3], tall(job, spec[3]), at=spec[2],
                            clear=job.clear - job.half if room.type == "skifa" else None)
                if o is not None and room.type == "bit":
                    interior.focus = (court.id, o.id)
            elif spec[0] == "inner":
                other = job.made.get(id(spec[1]))
                if other is not None:
                    o = R.place(interior, room, other[1], "inner", spec[3], tall(job, spec[3]), at=spec[2])
                    if o is not None:
                        interior.focus = (court.id, o.id)
            elif spec[0] == "court_windows":
                court_windows(job, ring, room, spec[2], spec[3])
            elif spec[0] == "arches":
                arches(job, ring, room)
    rooms = sorted(interior.rooms, key=lambda r: r.id)
    for r in rooms:
        if (r.floor != 0 or r.type in ("skifa", "droj", R.COURT, "well", "bortal") or has_door(interior, r)
                or r.unit != "home"):
            continue
        if r.type == "maqsura":
            bits = sorted(((shared(r.polygon, b.polygon), b.id, b) for b in rooms if b.floor == 0 and b.type == "bit"),
                          reverse=True)
            if any(R.place(interior, r, b, "inner", job.door, job.door_height) for s, _, b in bits if s > 0):
                continue
        o = R.place(interior, r, court, kind, job.door, job.door_height)
        if o is not None and r.type in ("bit", "matbakh") and rng.random() < float(job.dar.get("window_share", 0.6)):
            court_window_beside(job, ring, r, o)
    for f in range(1, interior.floors):
        ghorfas = [r for r in rooms if r.floor == f and r.type == "ghorfa"]
        for i, a in enumerate(ghorfas):
            for b in ghorfas[i + 1:]:
                R.place(interior, a, b, "inner", job.door, job.door_height)
            if ring.kind == "open":
                upper_windows(job, ring, a, "court_window", court)
            elif job.wells.get(f) is not None:
                upper_windows(job, ring, a, "inner_window", job.wells[f])


ASIDE = ("bit_el_ma", "wc", "sdb", "matbakh", "cuisine")   # rooms nobody walks through on the way in (round 6)


def skifa_way(job: Job) -> None:
    """The entry room with no way to the court but through a wet room or the matbakh gets its own: the
    shortest chain of other rooms of floor 0 from it to the court, with a door wherever the chain has none
    (dropped again when a dar's court would then show from the street; open items 47.1 + 48.1, round 6)."""
    interior, court = job.interior, job.court_room
    door = interior.entry
    if court is None or door is None or door not in interior.openings or getattr(interior, "way_free", False):
        return
    by_id = {r.id: r for r in interior.rooms}
    room = next((by_id[i] for i in door.rooms if i in by_id), None)
    if room is None or room.type in ASIDE or _way_ok(interior, room, court):
        return
    interior.way_used = True
    for chain in _chains(interior, room, court, job):
        made = []
        for a, b in zip(chain[:-1], chain[1:]):
            if _opens_on(interior, a, b):
                continue
            kind = ("court_door" if court.open else "inner") if b is court else "inner"
            o = R.place(interior, a, b, kind, job.door, job.door_height, clear=job.clear - job.half)
            if o is None:
                break
            made.append(o)
        else:
            if not (interior.layout == "dar" and R.sees_court(interior)):
                return
        interior.openings = [o for o in interior.openings if all(o is not m for m in made)]


def _chains(interior, room, court, job: Job, most: int = 4) -> list:
    """Up to `most` shortest chains of rooms from `room` to the court through rooms of its unit on floor 0
    that are no wet room, matbakh, stair cell or well, each pair sharing a piece a door fits."""
    need = job.door + 2 * job.clear - 1e-6           # the door `skifa_way` places (`clear` less half a partition)
    ok = [r for r in interior.rooms if r.floor == 0 and r.unit == room.unit and r.type not in ASIDE + ("droj", "well")
          and r is not court]
    out, todo = [], [(room,)]
    while todo and len(out) < most:
        nxt = []
        for chain in todo:
            last = chain[-1]
            near = {n.id: s for s, n in R.neighbours(interior, last)}
            on_court = max((math.dist(*p) for p in R.pieces_between(interior, last, court)), default=0.0)
            if on_court >= need:
                out.append(chain + (court,))
            nxt += [chain + (r,) for r in ok if r not in chain and near.get(r.id, 0.0) >= need]
        todo = nxt[:64]
    return out[:most]


def _opens_on(interior, r, court) -> bool:
    return any(o.kind in R.PASS and set(o.rooms) == {r.id, court.id} for o in interior.openings)


def _way_ok(interior, room, court) -> bool:
    """True when the court is reached from `room` through doors without crossing a room of `ASIDE`."""
    graph = R.links(interior)
    by_id = {r.id: r for r in interior.rooms}
    seen, todo = {room.id}, [room.id]
    while todo:
        n = todo.pop()
        if n == court.id:
            return True
        for m in sorted(graph.get(n, ())):
            if m not in seen and m in by_id and by_id[m].type not in ASIDE and by_id[m].floor == 0:
                seen.add(m)
                todo.append(m)
    return False


def has_door(interior, r) -> bool:
    return any(r.id in o.rooms and o.kind in R.PASS for o in interior.openings)


def tall(job: Job, w: float) -> float:
    """Door height: the double leaf of a T room stands taller."""
    return float(job.dar.get("court_door_height", 2.4)) if w > job.door + 1e-6 else job.door_height


def court_windows(job: Job, ring, room, center, door_w: float) -> None:
    """Up to two court windows flanking the T room's door, in the middle of what is left on each side."""
    if ring.kind != "open":
        return
    win = job.dar.get("court_window", {})
    w, sill, head = float(win.get("width", 0.8)), float(win.get("sill", 0.9)), float(win.get("head", 2.1))
    for p0, p1 in ring.contact(room.polygon):
        line = LineString([p0, p1])
        if line.distance(Point(*center)) > 0.02:
            continue
        t = line.project(Point(*center))
        for a, b in ((0.0, t - door_w / 2 - job.clear), (t + door_w / 2 + job.clear, line.length)):
            lo, hi = a + job.clear + job.half * (a == 0.0), b - job.clear - job.half * (b == line.length)
            if hi - lo >= w:
                at = line.interpolate((lo + hi) / 2).coords[0]
                R.place(job.interior, room, job.court_room, "court_window", w, head - sill, sill=sill, at=at)


def court_window_beside(job: Job, ring, room, door) -> None:
    """One court window beside a room's court door, where its wall leaves room."""
    win = job.dar.get("court_window", {})
    w, sill, head = float(win.get("width", 0.8)), float(win.get("sill", 0.9)), float(win.get("head", 2.1))
    kind = "court_window" if ring.kind == "open" else "inner_window"
    if kind == "inner_window":
        return
    face = Point(*_room_face(job, door))
    for p0, p1 in ring.contact(room.polygon):
        line = LineString([p0, p1])
        if line.distance(face) > 0.05:
            continue
        t = line.project(face)
        for a, b in ((t + door.width / 2 + job.clear, line.length), (0.0, t - door.width / 2 - job.clear)):
            lo = a + (job.clear + job.half) * (a == 0.0)
            hi = b - (job.clear + job.half) * (b == line.length)
            if hi - lo >= w:
                at = line.interpolate((lo + hi) / 2).coords[0]
                if R.place(job.interior, room, job.court_room, kind, w, head - sill, sill=sill, at=at):
                    return


def _room_face(job: Job, o) -> tuple:
    """The point of a court opening on its room's face (the opening stands on the court's face)."""
    if o.wall is None:
        return (o.x, o.y)
    front = np.array([-math.sin(o.yaw), math.cos(o.yaw)])
    return tuple(np.array([o.x, o.y]) - front * job.court_wall)


def upper_windows(job: Job, ring, room, kind: str, target) -> None:
    """Upper rooms look onto the court: one window per `window_every` m of court wall, centered."""
    key = "court_window" if kind == "court_window" else "inner_window"
    win = (job.dar if key == "court_window" else job.compact).get(key, {})
    w, sill, head = float(win.get("width", 0.8)), float(win.get("sill", 0.9)), float(win.get("head", 2.1))
    every = float(job.dar.get("window_every", 3.5))
    if kind == "court_window":
        pieces = ring.contact(room.polygon)
    else:
        pieces = R.pieces_between(job.interior, room, target)
    for p0, p1 in sorted(pieces, key=lambda p: -math.dist(*p))[:1]:
        line = LineString([p0, p1])
        room_ = line.length - 2 * (job.clear + job.half)
        n = min(max(1, int(room_ // every) + 1), int((room_ + job.clear) // (w + job.clear)))
        for i in range(n):
            at = line.interpolate(job.clear + job.half + room_ * (i + 0.5) / n).coords[0]
            R.place(job.interior, room, target, kind, w, head - sill, sill=sill, at=at)


def arches(job: Job, ring, room) -> None:
    """The bortal's arches on the court side: one per `arch_span` m, `arch` wide."""
    span, w = float(job.dar.get("arch_span", 2.2)), float(job.dar.get("arch", 1.6))
    for p0, p1 in sorted(ring.contact(room.polygon), key=lambda p: -math.dist(*p))[:1]:
        line = LineString([p0, p1])
        n = max(1, int(line.length // span))
        for i in range(n):
            at = line.interpolate(line.length * (i + 0.5) / n).coords[0]
            R.place(job.interior, room, job.court_room, "arch", w, float(job.dar.get("arch_height", 2.6)), at=at)


# --- the roof ---------------------------------------------------------------------------------------
def roof(job: Job, top: int) -> None:
    """The stah (an open room on floor = floors) reached through the stair room, with its stair room and
    menzah; a menzah on a roof without a stair room is reached by a ladder from the court."""
    interior, lay = job.interior, job.roof
    if lay is None or lay.inner is None:
        return
    has_stair, has_menzah = lay.stair is not None, lay.menzah is not None
    if not has_stair and not has_menzah:
        return
    f = interior.floors
    z = interior.high + job.outside.b.height
    pieces = parts(lay.free)
    if not pieces:
        return
    stah = Room(R.next_id(interior), f, "stah", max(pieces, key=lambda p: p.area), z, lay.height, open=True)
    interior.rooms.append(stah)
    door_h = float(getattr(lay, "door_height", 1.95))
    if has_stair:
        droj = Room(R.next_id(interior), f, "droj", lay.stair, z, lay.stair_height)
        interior.rooms.append(droj)
        roof_door(interior, droj, stah, lay.door, lay.door_width, door_h)
        stair = next((s for s in interior.stairs if s.kind == "newel"), None)
        if stair is not None and stair.top >= f:
            stair.rooms.append(droj.id)
        elif job.roof_ladder or stair is None:
            stair_ladder(job, droj)
    if has_menzah:
        men = Room(R.next_id(interior), f, "menzah", lay.menzah, z, lay.menzah_height)
        interior.rooms.append(men)
        roof_door(interior, men, stah, lay.menzah_door, lay.door_width, door_h)
        for spot in lay.menzah_windows:
            roof_window(interior, men, spot)
        if not has_stair:
            menzah_ladder(job, stah)


def roof_door(interior, room, stah, spot: tuple, width: float, height: float) -> None:
    """A roof room's door (`RoofLayout` spot: x, y and its outward yaw)."""
    x, y, out = spot
    front = (math.cos(out), math.sin(out))
    o = R.opening(interior, room, stah, "inner", (x, y), front, width, room.z, room.z + height)
    o.wall = None


def roof_window(interior, room, spot: tuple) -> None:
    """A menzah window, as the tile draws it (0.7 m wide, 1.0 to 1.8 m above the deck)."""
    x, y, out = spot
    front = (math.cos(out), math.sin(out))
    along = np.array([front[1], -front[0]])
    c = np.array([x, y])
    wall = (tuple(c - along * 1.0), tuple(c + along * 1.0))
    interior.openings.append(Opening(len(interior.openings), "window", x, y, R.yaw_of(front), 0.7, room.z + 1.0,
                                     room.z + 1.8, room.floor, (room.id, -1), wall, 1.0))


def stair_ladder(job: Job, droj) -> None:
    """A ladder from the top floor up into a stair room no newel cell stands under."""
    interior = job.interior
    top = interior.storeys[-1]
    w, d = (float(v) for v in job.stairs.get("ladder", [0.6, 1.2]))
    region = droj.polygon.intersection(top.polygon).buffer(-0.05, join_style="mitre")
    keep = job.entry_keep() if top.floor == 0 else None
    spot = None
    for area in ([region.difference(keep)] if keep is not None else []) + [region]:   # off the entry steps first
        near = droj.polygon.centroid.coords[0]
        spot = None if area.is_empty else S.ladder(area, Frame.of(droj.polygon), near, (w, d))
        if spot is not None:
            break
    below = max((r for r in interior.rooms if r.floor == top.floor and spot is not None and r.type != "well"),
                key=lambda r: (r.polygon.intersection(spot).area, -r.id), default=None)
    if spot is None or below is None:
        stah = next((r for r in interior.rooms if r.type == "stah"), None)
        if stah is not None and job.court_room is not None and R.is_court(job.court_room):
            menzah_ladder(job, stah, droj.polygon)        # a ladder from the court up to the roof instead
            if any(st.kind == "ladder" and stah.id in st.rooms for st in interior.stairs):
                return
        interior.warnings.append("the stair room has no way up")
        return
    n = S.risers(interior.fh, 0.3)
    interior.stairs.append(S.Stair("ladder", spot, top.floor, interior.floors, n, interior.fh / n, 0.0, w, None,
                                   [below.id, droj.id]))


def menzah_ladder(job: Job, stah, near=None) -> None:
    """A ladder from the court up to a roof without a stair room, next to the menzah (or `near`)."""
    interior, lay = job.interior, job.roof
    court = job.court_room
    if court is None or not R.is_court(court):
        interior.warnings.append("the menzah has no way up")
        return
    w, d = (float(v) for v in job.stairs.get("ladder", [0.6, 1.2]))
    inner = court.polygon.buffer(-0.05, join_style="mitre")
    target = (near if near is not None else lay.menzah).centroid.coords[0]
    spot = S.ladder(inner, Frame.of(court.polygon), target, (w, d)) if not inner.is_empty else None
    if spot is None:
        interior.warnings.append("the menzah has no way up")
        return
    height = stah.z - court.z
    n = S.risers(height, 0.3)
    interior.stairs.append(S.Stair("ladder", spot, 0, interior.floors, n, height / n, 0.0, w, None,
                                   [court.id, stah.id]))


def entry_steps(job: Job) -> None:
    """Steps inside the entry room of every door whose threshold is off floor 0 (SPEC 6c `steps`)."""
    interior = job.interior
    for spot in job.outside.doors:
        o = main_opening(interior, spot)
        if o is None:
            continue
        room = next((r for r in interior.rooms if r.id == o.rooms[0]), None)
        if room is None:
            continue
        rise = interior.high - spot.z
        said = len(interior.warnings)
        s = S.steps(room, spot, o.width, rise, job.stairs, interior.warnings, job.ext)
        others = [t.polygon for t in interior.stairs if t.floor == 0 and t.kind != "steps"]
        if s is not None and any(s.polygon.intersection(p).area > 0.01 for p in others):
            notes = []
            short = steps_beside(job, room, spot, o, rise, others, notes)   # short of the other stair (47.1)
            if short is not None:
                s, interior.warnings = short, interior.warnings[:said] + notes
        if s is not None:
            interior.stairs.append(s)


def steps_beside(job: Job, room, spot, o, rise: float, others: list, notes: list):
    """Entry steps in the part of `room` the other stairs of floor 0 leave free (None when they would not
    keep `tread_min`)."""
    free = room.polygon.difference(shapely.union_all(others))
    probe = job.probe() if o is job.main else inside(o, job.ext)
    part = next((p for p in parts(snap(free)) if p.distance(probe) < 0.05), None)
    if part is None:
        return None
    s = S.steps(Room(room.id, room.floor, room.type, part, room.z, room.height), spot, o.width, rise,
                job.stairs, notes, job.ext)
    if s is None or s.tread < float(job.stairs.get("tread_min", 0.2)) - 1e-9:
        return None
    return s


# --- the court ----------------------------------------------------------------------------------------
def features(job: Job, court) -> None:
    """The majel 0.8 m from a court wall, the plan's trees standing in the court, else for a rich house a
    fesqiya in the middle (stream `court`)."""
    interior, plan = job.interior, job.outside.plan
    z = interior.storeys[0].z
    rng = job.court
    xy = np.array([(t.x, t.y) for t in plan.trees]).reshape(-1, 2)
    inside = np.flatnonzero(shapely.contains_xy(court, xy[:, 0], xy[:, 1])) if len(xy) else []
    trees = [(int(i), plan.trees[int(i)]) for i in inside]
    for i, t in trees:
        interior.features.append({"type": "tree", "tree": i, "kind": t.kind, "x": round(t.x, 3),
                                  "y": round(t.y, 3), "z": round(z, 3)})
    ring = np.asarray(court.exterior.coords)
    edges = [(math.dist(a, b), i) for i, (a, b) in enumerate(zip(ring[:-1], ring[1:])) if math.dist(a, b) > 1.0]
    away = float(job.dar.get("majel", 0.8))
    if edges:
        i = edges[int(rng.integers(len(edges)))][1]
        a, b = ring[i], ring[i + 1]
        mid = (a + b) / 2
        d = (b - a) / max(float(np.hypot(*(b - a))), 1e-9)
        n = np.array([-d[1], d[0]])
        p = mid + n * away
        if not court.contains(Point(*p)):
            p = mid - n * away
        if court.contains(Point(*p)) and all(math.hypot(p[0] - t.x, p[1] - t.y) > 1.0 for _, t in trees):
            interior.features.append({"type": "majel", "x": round(float(p[0]), 3), "y": round(float(p[1]), 3),
                                      "z": round(z, 3)})
    if not trees and job.wealth > float(job.dar.get("fesqiya_wealth", 0.6)):
        from shapely.ops import polylabel
        c = polylabel(court, tolerance=0.05)
        interior.features.append({"type": "fesqiya", "x": round(c.x, 3), "y": round(c.y, 3), "z": round(z, 3)})
