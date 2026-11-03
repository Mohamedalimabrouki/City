"""The patio-house planner (SPEC 6c "Villas and houses", 47.2 houses round 6).

A maison whose plan from the spine engine still leaves a chambre, salon, salle a manger or cuisine with no
window (a patio or court house: the couloir runs along the patio and takes its windows) is planned again as
a Tunisian town house is laid: the couloir, one straight strip or two at a right angle, on the blind side,
the rooms on its sides, each cut straight across from the couloir to the windows of the street or the
patio. On floor 0 the couloir starts at the street door with a hall; on every floor it meets the palier;
it holds no window. Services (sdb, wc) may stay blind; a wc may close a couloir's dead end.
`layout.plan_interior` keeps the plan only when the whole check passes it.
"""
from __future__ import annotations

import itertools
import math

from . import rooms as R
from . import spine as P
from .cuts import parts, shared, snap, union

LIVE = ("salon", "salle_a_manger", "cuisine", "chambre")
IDEAL = {"salon": 16.0, "salle_a_manger": 12.0, "cuisine": 8.0, "chambre": 10.0, "sdb": 4.0, "wc": 1.5}
SPECIAL = ("salon", "salle_a_manger", "cuisine", "wc", "sdb")
KEYS = ("chambre",) + SPECIAL


class _Floor:
    """One floor's frame (the region turned onto its rotated rectangle) and its tests."""

    def __init__(self, job, region, entry, program: list, f: int, landing):
        from shapely import affinity
        from shapely.geometry import Point
        cfg = job.cfg.get("villa", {})
        self.job, self.region, self.landing = job, region, landing
        self.step = float(cfg.get("patio_step", 0.5))
        self.wide_c = float(cfg.get("couloir", 1.15))
        self.most = job.cfg.get("rooms", {}).get("most", {})
        self.wide, self.thin = (float(v) for v in job.cfg.get("flats", {}).get("strip", (1.6, 3.0)))
        self.sun = P.lights(job, f)
        self.zones, self.door, self.half = job.zs([f]), P.need(job), job.half
        rules = job.interior.rules
        self.wet = float(rules.get("narrow", 0.7)) + 2 * (float(rules.get("narrow_clear", 0.05)) + self.half)
        self.at = Point(entry.x, entry.y) if f == 0 else None
        self.need = {t: program.count(t) for t in SPECIAL}
        self.chambres = program.count("chambre")
        xy = list(region.minimum_rotated_rectangle.exterior.coords)
        self.angle = math.degrees(math.atan2(xy[1][1] - xy[0][1], xy[1][0] - xy[0][0]))
        self.flat = affinity.rotate(region, -self.angle, origin=(0, 0))
        self.memo = {}

    def back(self, p):
        from shapely import affinity
        return affinity.rotate(p, self.angle, origin=(0, 0))

    def bounds(self, p):
        from shapely import affinity
        return affinity.rotate(p, -self.angle, origin=(0, 0)).bounds

    def slab(self, poly, axis: int, a: float, b: float, bounds):
        """`poly` between a and b along `axis` of the frame (`bounds`: the frame bounds of `poly`)."""
        from shapely.geometry import box
        x0, y0, x1, y1 = bounds
        bx = box(a, y0 - 1, b, y1 + 1) if axis == 0 else box(x0 - 1, a, x1 + 1, b)
        return poly.intersection(self.back(bx))

    def lit(self, poly) -> bool:
        return any(poly.distance(p) < 0.05 for p in self.sun)

    def clash(self, a, b) -> bool:
        return R.clash_polys(a, b, self.zones, 2 * self.half)

    def kinds(self, poly) -> list:
        """The room types a piece can hold (a living room windowed, every room within its minimum and most)."""
        light = self.lit(poly)
        out = []
        for t in KEYS:
            if t != "chambre" and not self.need.get(t):
                continue
            if t in LIVE and not light or not self.job.fits(poly, t) or poly.area > float(self.most.get(t, 1e9)):
                continue
            if t in LIVE and P.strip(poly, self.wide) > self.thin:
                continue
            out.append(t)
        return out


def one(poly):
    got = parts(snap(poly))
    return got[0] if len(got) == 1 and not got[0].interiors else None


def plan(job, region, entry, program: list, f: int, landing) -> list | None:
    """The typed cells of one floor (hall, couloir and rooms), or None when no couloir and cuts give every
    room of the program its window and its door on the way."""
    if any(t not in KEYS + ("chambre*",) for t in program):
        return None
    fl = _Floor(job, region, entry, program, f, landing)
    best = None
    for way, axis in _ways(fl):
        for ways in _halls(fl, way, axis):
            sides = parts(snap(region.difference(way)))
            thin = [p for p in sides if not job.fits(p, "wc") or P.strip(p, 0.9) > 0.5 * p.area]
            if thin:                                  # a sliver between the couloir and a wall joins it
                grown = union(ways[-1][0], thin[0]) if len(thin) == 1 else None
                if grown is None or grown.interiors or fl.lit(grown) or not ways[-1][1] == "couloir":
                    continue
                ways = ways[:-1] + [(grown, "couloir")]
                sides = [p for p in sides if p is not thin[0]]
            for ends, need in _ends(fl, ways, axis):
                plans = [_side(fl, s, ends, need) for s in sides]
                if any(not p for p in plans):
                    continue
                got = _combine(plans, need, fl.chambres)
                if got is not None and (best is None or got[0] > best[0]):
                    best = (got[0], ends, got[1])
    if best is None:
        return None
    _, ways, rooms = best
    return [P.Cell(p, t) for p, t in ways] + [P.Cell(p, t) for p, t in rooms]


def _strips(fl):
    """(axis, polygon) of every couloir-wide strip across the floor's frame, `patio_step` / 2 apart."""
    from shapely.geometry import box
    x0, y0, x1, y1 = fl.flat.bounds
    out = []
    for axis in (0, 1):
        lo, hi = (y0, y1) if axis == 0 else (x0, x1)
        n = int((hi - lo - fl.wide_c) / (fl.step / 2)) + 1
        for s in sorted({round(lo + k * fl.step / 2, 3) for k in range(n)} | {round(hi - fl.wide_c, 3)}):
            band = box(x0 - 1, s, x1 + 1, s + fl.wide_c) if axis == 0 else box(s, y0 - 1, s + fl.wide_c, y1 + 1)
            got = one(fl.back(fl.flat.intersection(band)))
            if got is not None and fl.job.fits(got, "couloir"):
                out.append((axis, got))
    return out


def _ways(fl):
    """(the way polygon, the axis of its first strip): one strip through the street door (floor 0) or along
    the palier; on floor 0 a strip through the door that misses the palier with a second one at a right
    angle from it to the palier."""
    strips = _strips(fl)
    door, at, landing = fl.door, fl.at, fl.landing

    def starts(p):
        return p.distance(at) <= 0.3 if at is not None else landing is not None and shared(p, landing) >= door

    def meets(p):
        return landing is None or shared(p, landing) >= door
    for axis, a in strips:
        if not starts(a):
            continue
        if meets(a):
            yield a, axis
            continue
        for axis2, b in strips:                       # (floor 0: a second strip from it to the palier)
            if axis2 == axis:
                continue
            for arm in parts(snap(b.difference(a))):
                if shared(arm, a) < fl.wide_c - 0.05 or not meets(arm):
                    continue
                way = union(a, arm)
                if way is not None and not way.interiors and not fl.lit(arm):
                    yield way, axis


def _halls(fl, way, axis):
    """[(poly, "hall"), (poly, "couloir"), ...] of the way: on floor 0 the smallest hall at the street door
    cut across its first strip, the rest (one to three pieces) the couloir; a couloir with no window (the
    hall may hold one)."""
    most = fl.most
    if fl.at is None:
        if not fl.lit(way) and way.area <= float(most.get("couloir", 1e9)):
            yield [(way, "couloir")]
        return
    b = fl.bounds(way)
    lo, hi = (b[0], b[2]) if axis == 0 else (b[1], b[3])
    cuts = [lo - 1] + [lo + k * fl.step for k in range(1, int((hi - lo) / fl.step))] + [hi + 1]
    out = []
    for i, c1 in enumerate(cuts):
        for c2 in cuts[i + 1:]:
            if c1 < lo and c2 > hi:
                continue
            hall = next((p for p in parts(snap(fl.slab(way, axis, c1, c2, b))) if p.distance(fl.at) <= 0.3), None)
            if hall is None or hall.interiors or not fl.job.fits(hall, "hall"):
                continue
            if hall.area > float(most.get("hall", 1e9)):
                break
            rest = parts(snap(way.difference(hall)))
            if any(fl.lit(w) or not fl.job.fits(w, "couloir") or fl.clash(hall, w) or w.interiors for w in rest):
                continue
            out.append((hall.area, hall, rest))
            break
    if out:
        _, hall, rest = min(out, key=lambda x: x[0])
        yield [(hall, "hall")] + [(w, "couloir") for w in rest]


def _ends(fl, ways, axis):
    """The ways as they are, and (when the floor needs a wc) with the wc at a couloir's dead end: a piece
    of the couloir across its far end, entered by its narrow door."""
    yield ways, fl.need
    if not fl.need.get("wc"):
        return
    hall = next((p for p, t in ways if t == "hall"), None)
    for k, (c, t) in enumerate(ways):
        if t != "couloir":
            continue
        b = fl.bounds(c)
        for ax in (0, 1):
            lo, hi = (b[0], b[2]) if ax == 0 else (b[1], b[3])
            for far in (True, False):
                for n in range(2, 9):
                    d = n * fl.step / 2
                    w = parts(snap(fl.slab(c, ax, hi - d, hi + 1, b) if far else fl.slab(c, ax, lo - 1, lo + d, b)))
                    rest = parts(snap(fl.slab(c, ax, lo - 1, hi - d, b) if far else fl.slab(c, ax, lo + d, hi + 1, b)))
                    if len(w) != 1 or len(rest) != 1:
                        continue
                    w, rest = w[0], rest[0]
                    if w.area > float(fl.most.get("wc", 1e9)):
                        break
                    if (not fl.job.fits(w, "wc") or not fl.job.fits(rest, "couloir") or shared(w, rest) < fl.wet
                            or hall is not None and shared(w, hall) > 0.05 or fl.clash(w, rest)
                            or any(shared(w, o) > 0.05 for o, _ in ways if o is not c)):
                        continue
                    yield ways[:k] + [(rest, "couloir"), (w, "wc")] + ways[k + 1:], dict(fl.need, wc=0)
                    break


def _side(fl, side, ways, need) -> dict:
    """A side piece's cuts into rooms straight across from the way (along either axis): {state: (score,
    rooms)}, a state counting the specials and the chambres (to 2)."""
    import shapely
    spine = [p for p, t in ways if t in P.SPINE]
    key = (shapely.to_wkb(side), tuple(shapely.to_wkb(p) for p, _ in ways), tuple(sorted(need.items())))
    if key in fl.memo:
        return fl.memo[key]
    top = max(float(fl.most.get(t, 1e9)) for t in KEYS if t == "chambre" or need.get(t))
    b = fl.bounds(side)
    out = {}
    for axis in (0, 1):
        lo, hi = (b[0], b[2]) if axis == 0 else (b[1], b[3])
        pos = [lo] + [lo + k * fl.step for k in range(1, int((hi - lo) / fl.step) + 1) if lo + k * fl.step < hi - fl.step / 2] + [hi]
        last = len(pos) - 1
        okcut = {}
        for c in range(1, last):
            left, right = one(fl.slab(side, axis, pos[0] - 1, pos[c], b)), one(fl.slab(side, axis, pos[c], pos[-1] + 1, b))
            okcut[c] = left is not None and right is not None and not fl.clash(left, right)
        dp = {0: {(0,) * len(KEYS): (1e9, ())}}
        for i in range(last):
            if i not in dp or i > 0 and not okcut.get(i):
                continue
            for j in range(i + 1, last + 1):
                if j < last and not okcut.get(j):
                    continue
                raw = fl.slab(side, axis, pos[i] - (1 if i == 0 else 0), pos[j] + (1 if j == last else 0), b)
                if raw.area > top:
                    break
                p = one(raw)
                if p is None:
                    continue
                sh = max(shared(p, w) for w in spine)
                if sh < fl.wet or any(fl.clash(p, w) for w, _ in ways) or (
                        fl.landing is not None and fl.clash(p, fl.landing)):
                    continue
                ks = [t for t in fl.kinds(p) if sh >= (fl.wet if t in P.WET else fl.door)]
                for st, (sc, rooms) in dp[i].items():
                    for t in ks:
                        n = list(st)
                        n[KEYS.index(t)] += 1
                        if t != "chambre" and n[KEYS.index(t)] > need.get(t, 0):
                            continue
                        n[0] = min(n[0], 2)
                        n = tuple(n)
                        got = (min(sc, min(p.area / IDEAL[t], 1.0)), rooms + ((p, t),))
                        cur = dp.setdefault(j, {}).get(n)
                        if cur is None or got[0] > cur[0]:
                            dp[j][n] = got
        for st, got in dp.get(last, {}).items():
            if st not in out or got[0] > out[st][0]:
                out[st] = got
    fl.memo[key] = out
    return out


def _combine(plans, need, chambres):
    """The best pick of one cut per side whose rooms make the program: (score, rooms) or None."""
    want = tuple(need.get(t, 0) for t in SPECIAL)
    best = None
    for pick in itertools.product(*[list(p.items()) for p in plans]):
        tot = [sum(st[i] for st, _ in pick) for i in range(len(KEYS))]
        if tuple(tot[1:]) != want or tot[0] < chambres:
            continue
        score = min(sc for _, (sc, _) in pick)
        if best is None or score > best[0]:
            best = (score, tuple(r for _, (_, rs) in pick for r in rs))
    return best
