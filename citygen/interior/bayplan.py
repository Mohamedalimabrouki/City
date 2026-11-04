"""Flats planned one room per window bay (47.2 flats round E, SPEC 6c "Flats").

The spine cuts its bands every `rhythm` m whatever the windows, so cells hold no window or two, and the
search spends the bays on couloirs, halls and baths. Real blocks of Tunis and Algiers (1900-1950) lay the
rooms the other way round: one room per bay along the lit walls (street, court, light well), the couloir on
the unlit side, the hall at the entry, the baths in the blind pieces or by the couloir. Two kinds of variants: rooms
`deep` m along the lit walls (street, court or both) with the couloir behind them, its pieces joined to the
hall by straight stubs (`along`); and the spine's hall and couloir (`spine.cut_region`) with its bands cut
at the piers between their windows instead of its rhythm (each piece holds one bay; a band running on past
its last window keeps a blind end piece for a bath). The pieces are typed here: the lit ones are the salon,
cuisine, salle a manger and chambres (a piece too small for any joins its neighbour, else the way), the
blind ones the sdb and wc, else a bath is carved from a room's corner on the couloir (`carve`); a blind
piece left over joins the way or a room. A plan is given only when it is clean by itself: every program room there and within its
minimum and `most`, no fault the search counts (`spine.faults`, blind rooms included) and every room
against the hall or couloir for its door. `flats.run` plans a flat with it only where the spine's plan
faults and this one passes the whole plan check (`layout.flat_bays`). Where `middle` names the layout (colonial
blocks, deep L and U masses), the blind middle holds the ways: a hall too small grows, a blind piece between a
way and a lit piece no way reaches joins the way, and couloir pieces join by stubs up to `stub_middle` m.
Numbers: `[interiors.flats] bay_plan`.
"""
from __future__ import annotations

import math

import numpy as np
import shapely

from . import rooms as R
from . import spine as P
from .cuts import Cell, cut, shared, union

BIG = 1e3          # meters: a rhythm no band reaches (the spine's bands come back uncut)
LIT = ("salon", "cuisine", "salle_a_manger", "chambre")


def numbers(job) -> dict:
    """`[interiors.flats] bay_plan` with defaults: `room` the least length of a lit piece along its band,
    `wet` the least and `wet_most` the longest blind end piece kept for a bath."""
    cfg = job.cfg.get("flats", {}).get("bay_plan", {})
    return {"room": float(cfg.get("room", 2.4)), "wet": float(cfg.get("wet", 1.2)),
            "wet_most": float(cfg.get("wet_most", 2.4)), "side": float(cfg.get("side", 2.45)),
            "stub": float(cfg.get("stub", 6.0)), "stub_middle": float(cfg.get("stub_middle", 12.0))}


def on(job) -> bool:
    """True when `[interiors.flats] bay_plan.layouts` names the job's layout."""
    return job.interior.layout in job.cfg.get("flats", {}).get("bay_plan", {}).get("layouts", [])


def middle(job) -> bool:
    """True when `[interiors.flats] bay_plan.middle` names the job's layout: the blind middle of a deep flat
    holds its ways (a hall grown past its least where that one is too small, a blind piece between a way and
    a lit piece no way reaches joining the way: 47.2 colonial round K)."""
    return job.interior.layout in job.cfg.get("flats", {}).get("bay_plan", {}).get("middle", [])


def first(job) -> bool:
    """True when a block's first plan plans every flat bay by bay at once where that plan is clean
    (`[interiors.flats] bay_plan.first`; else only a flat the check faults, in a second plan): one plan
    instead of two, and the rooms on the bays (47.2 flats round F)."""
    return bool(job.cfg.get("flats", {}).get("bay_plan", {}).get("first", False))


def lay(job, region, entry, prog: list, floor: int, key: tuple):
    """The cells of a clean bay plan of a flat region, or None. Stacked flats repeat (a memo per region,
    entrance, program and facade, as `spine.typical`; a search that failed is not run again for a floor whose
    windows stand at the same places, balcony doors or windows: 47.2 flats round F)."""
    memo = job.__dict__.setdefault("bay_memo", {})
    tk = P.typical_key(job, region, entry, prog, floor, key, True)
    if tk not in memo:
        miss = job.__dict__.setdefault("bay_miss", set())   # a floor below with the windows in the same
        lk = tk[:5] + (tuple(sorted(("light" if k in ("window", "balcony") else k, *rest) for k, *rest in tk[5])),)
        memo[tk] = None if lk in miss else search(job, region, entry, prog, floor)   # places (a balcony door
        if memo[tk] is None:                                                      # for a window) failed: no
            miss.add(lk)                                                          # second search (time)
    got = memo[tk]
    return None if got is None else [Cell(c.poly, c.type, c.band, c.part) for c in got]


def search(job, region, entry, prog: list, floor: int):
    """The first clean plan of the variants: rooms along the street, court or every lit wall, as deep as the
    region less the couloir (both sides: half of that), 3 or 4 m; then the spine's couloir as the rules say,
    then turned, placed by the rules, then against either side wall, with the least hall, then a deeper one."""
    cfg = dict(P.numbers(job), side=numbers(job)["side"])
    seen = set()
    for which in ("street", "court", "all"):          # rooms along the lit walls, the couloir behind them
        reach = reach_of(job, region, floor, which)
        if reach is None:
            continue
        far = reach - cfg["couloir"] if which != "all" else (reach - cfg["couloir"]) / 2
        for deep in sorted({round(min(max(v, cfg["side"]), 4.5), 2) for v in (far, 3.0, 4.0)}):
            got = along(job, region, entry, floor, cfg, which, deep)
            if got is None:
                continue
            cells = got
            sig = tuple(sorted(round(c.poly.area, 2) for c in cells))
            if sig in seen:
                continue
            seen.add(sig)
            if types(job, cells, prog, floor) and clean(job, cells, prog, floor):
                return cells
    for depth, wide in ((cfg["hall"][0], cfg["hall_width"][0]), (cfg["hall"][1], cfg["hall_width"][0])):
        for turn in (False, True):
            for place in ("auto", "low", "high"):
                at = lambda poly, F, b0, b1: pier_cuts(job, poly, F, floor, b0, b1)   # noqa: E731
                try:
                    cells, spine = P.cut_region(job, region, entry, floor, cfg, depth, wide, BIG, True, turn, place, at)
                except (ValueError, shapely.errors.GEOSException):
                    continue
                sig = tuple(sorted(round(c.poly.area, 2) for c in cells))
                if sig in seen:
                    continue
                seen.add(sig)
                if types(job, cells, prog, floor) and clean(job, cells, prog, floor):
                    return cells
    return None


def piers(job, cells: list, spine: dict, floor: int) -> list:
    """The uncut band cells cut across the piers between their windows: one cut in every pier wide enough
    for a partition clear of both windows (`spine.free` on the floor's zones), each piece at least `room` m
    along the band; a band running on past its end window by `wet` m or more keeps a blind end piece (at
    most `wet_most` m) for a bath."""
    F = spine["F"]
    out = []
    for c in cells:
        if c.type or c.band not in ("A", "B"):
            out.append(c)
            continue
        b0, _, b1, _ = F.bounds(c.poly)
        pieces = [c.poly]
        for at in pier_cuts(job, c.poly, F, floor, b0, b1):
            nxt = []
            for p in pieces:
                lo_, hi_ = cut(p, F, 0, at)
                nxt += lo_ + hi_
            pieces = nxt
        out += [Cell(p, "", c.band, f"{F.bounds(p)[0]:.2f}") for p in pieces]
    return out


def pier_cuts(job, poly, F, floor: int, b0: float, b1: float) -> list:
    """Where a band is cut along u of frame F: in every pier between two of its windows wide enough for a
    partition clear of both, and before a blind end piece (see `piers`)."""
    from .dar import inside
    nb = numbers(job)
    ops = [o for o in job.interior.openings if o.floor == floor and o.kind in ("window", "balcony") and o.piece]
    pts = [(inside(o, job.ext), o.width) for o in ops]
    keep = job.clear + job.half
    wins = sorted((float(F.local(p.coords[0])[0]), w / 2) for p, w in pts if poly.distance(p) < 0.05)
    ats = []
    for (ua, ha), (ub, hb) in zip(wins, wins[1:]):
        lo, hi = ua + ha + keep, ub - hb - keep
        if hi < lo:
            continue                                  # two windows too close: one room
        got = P.free(job, poly, F, 0, (lo + hi) / 2, floor, lo, hi)
        if got is not None:
            ats.append(got)
    if wins:
        for end, edge, sgn in ((b0, wins[0][0] - wins[0][1] - keep, -1.0), (b1, wins[-1][0] + wins[-1][1] + keep, 1.0)):
            blank = abs(end - edge)
            if blank < nb["wet"] or sgn * (end - edge) < 0:
                continue
            at = edge if blank <= nb["wet_most"] else end - sgn * nb["wet_most"]
            got = P.free(job, poly, F, 0, at, floor, *sorted((at, at - sgn * 0.5)))
            if got is not None:
                ats.append(got)
    chosen, last = [], b0
    for at in sorted(ats):
        room = nb["wet"] if not any(w[0] < at for w in wins) else nb["room"]
        after = nb["wet"] if not any(w[0] > at for w in wins) else nb["room"]
        if at - last >= room - 1e-6 and b1 - at >= after - 1e-6:
            chosen.append(at)
            last = at
    return chosen


def ways(cells: list) -> list:
    return [c for c in cells if c.type in ("hall", "couloir")]


def door_on_way(job, c, cells: list) -> bool:
    """True when the cell shares a door's length with the hall or a couloir (a bath: its narrow door)."""
    need = P.wet_need(job) if c.type in P.WET else P.need(job)
    return any(shared(c.poly, w.poly) >= need for w in ways(cells))


def join(cells: list, a, b) -> bool:
    """Cell a joins cell b (b keeps its type); False when their union is not one piece."""
    got = union(a.poly, b.poly) if shared(a.poly, b.poly) > 0.3 else None
    if got is None or got.geom_type != "Polygon":
        return False
    b.poly = got
    cells.remove(a)
    return True


def types(job, cells: list, prog: list, floor: int) -> bool:
    """Types for the untyped pieces (see the module doc); False when the program does not fit them."""
    sun = P.lights(job, floor)
    most = job.cfg.get("rooms", {}).get("most", {})
    free = lambda: [c for c in cells if not c.type]                     # noqa: E731
    lit = lambda: [c for c in free() if P.lit(c.poly, sun)]             # noqa: E731
    small = True
    while small:                                     # a lit piece no lit room fits joins its band neighbour
        small = False
        for c in sorted(lit(), key=lambda c: (c.poly.area, c.part)):
            if job.fits(c.poly, "cuisine"):
                continue
            nbs = sorted((n for n in free() if n is not c and shared(c.poly, n.poly) > 1.0),
                         key=lambda n: (not job.fits(union(c.poly, n.poly) or c.poly, "cuisine"), not P.lit(n.poly, sun),
                                        n.poly.area, n.part))
            if not nbs:                                  # else the way beside it (a lit couloir end)
                nbs = [w for w in ways(cells) if shared(c.poly, w.poly) > 0.5]
            if not nbs or not join(cells, c, nbs[0]):
                return False
            small = True
            break
    want = [t for t in prog if t in LIT]
    if len(lit()) < len(want):
        return False
    on_way = lambda c: door_on_way(job, c, cells)   # noqa: E731
    if middle(job):
        reach(job, cells, len(want), sun, most)

    def take(t, pool, key):
        got = [c for c in pool if job.fits(c.poly, t) and c.poly.area <= float(most.get(t, 1e9)) + 0.01 and on_way(c)]
        if not got:
            return None
        c = min(got, key=key)
        c.type = t
        return c

    if take("cuisine", lit(), lambda c: (c.poly.area, c.part)) is None:
        return False
    salon = take("salon", lit(), lambda c: (-c.poly.area, c.part))
    if salon is None:
        return False
    if "salle_a_manger" in want and take("salle_a_manger", lit(), lambda c: (-shared(c.poly, salon.poly), -c.poly.area, c.part)) is None:
        return False
    for _ in range(want.count("chambre")):
        if take("chambre", lit(), lambda c: (-c.poly.area, c.part)) is None:
            return False
    for c in sorted(lit(), key=lambda c: (c.poly.area, c.part)):   # spare bays: more chambres, else a room's
        if job.fits(c.poly, "chambre") and c.poly.area <= float(most.get("chambre", 1e9)) and on_way(c):
            c.type = "chambre"
            continue
        nbs = [n for n in cells if n.type in LIT and shared(c.poly, n.poly) > 1.0
               and (c.poly.area + n.poly.area) <= float(most.get(n.type, 1e9))]
        if not nbs:                                    # else the way beside it
            nbs = [w for w in ways(cells) if shared(c.poly, w.poly) > 0.5
                   and c.poly.area + w.poly.area <= float(most.get(w.type, 1e9))]
        if not nbs or not join(cells, c, min(nbs, key=lambda n: (n.poly.area, n.part))):
            return False
    for t in [t for t in prog if t in P.WET]:
        pool = sorted(free(), key=lambda c: (P.lit(c.poly, sun), c.poly.area, c.part))
        got = [c for c in pool if job.fits(c.poly, t) and c.poly.area <= job.largest.get(t, float(most.get(t, 1e9)))]
        if not got:
            big = [c for c in pool if job.fits(c.poly, t)]
            if big and wet_end(job, cells, big[0], t, floor):
                continue
            if not carve(job, cells, t, floor):
                return False
            continue
        got[0].type = t
    for c in free():                                   # a blind piece left over joins the way beside it,
        nbs = [w for w in ways(cells) if shared(c.poly, w.poly) > 0.5   # else a room's end (an alcove)
               and c.poly.area + w.poly.area <= float(most.get(w.type, 1e9))]
        nbs = nbs or sorted((n for n in cells if n.type in LIT and shared(c.poly, n.poly) > 1.0
                             and c.poly.area + n.poly.area <= float(most.get(n.type, 1e9))),
                            key=lambda n: (n.poly.area, n.part))
        if not nbs or not join(cells, c, nbs[0]):
            return False
    return True


def reach(job, cells: list, want: int, sun: list, most: dict) -> None:
    """While fewer lit pieces than `want` a room fits stand on a way, a blind untyped piece sharing a door's
    length with a lit piece no way reaches and touching a way joins that way (the hall first: the blind
    middle of a deep flat holds the hall and couloir, the rooms round it on the windows)."""
    room = lambda c: job.fits(c.poly, "cuisine")                       # noqa: E731
    while sum(room(c) and door_on_way(job, c, cells) for c in cells if not c.type and P.lit(c.poly, sun)) < want:
        off = sorted((c for c in cells if not c.type and P.lit(c.poly, sun) and room(c) and not door_on_way(job, c, cells)),
                     key=lambda c: (-c.poly.area, c.part))
        done = False
        for c in off:
            nbs = sorted((n for n in cells if not n.type and not P.lit(n.poly, sun) and shared(c.poly, n.poly) >= P.need(job)),
                         key=lambda n: (n.poly.area, n.part))
            for n in nbs:
                ws = sorted((w for w in ways(cells) if shared(n.poly, w.poly) >= P.need(job)
                             and n.poly.area + w.poly.area <= float(most.get(w.type, 1e9))),
                            key=lambda w: (w.type != "hall", w.poly.area, w.part))
                if ws and join(cells, n, ws[0]):
                    done = True
                    break
            if done:
                break
        if not done:
            return


def wet_end(job, cells: list, c, t: str, floor: int) -> bool:
    """A bath at the end of a blind piece too big for one (its `largest` x 0.8 along the band), the rest
    staying untyped; False when no cut keeps a partition clear."""
    from .cuts import Frame
    F = Frame.of(c.poly)
    u0, _, u1, _ = F.bounds(c.poly)
    want = job.largest.get(t, 4.0) * 0.8
    deep = c.poly.area / max(u1 - u0, 1e-6)
    at = P.free(job, c.poly, F, 0, u0 + want / max(deep, 0.5), floor, u0 + 1.0, u1 - 1.0)
    if at is None:
        return False
    lo, hi = cut(c.poly, F, 0, at)
    if len(lo) != 1 or len(hi) != 1:
        return False
    cells.remove(c)
    cells += [Cell(lo[0], t, c.band, c.part + "w"), Cell(hi[0], "", c.band, c.part + "r")]
    return True


def carve(job, cells: list, t: str, floor: int) -> bool:
    """A bath carved from a lit room's corner on the couloir (as the baths of real flats stand by the
    couloir, the rooms reaching past them to their windows): `[interiors.flats] bay_plan.bath` (width along
    the couloir, depth) for `t`, at either end of the room's longest piece on a way; kept where the room
    keeps its minimum, a door's length on the way and no partition meets a wall near an opening."""
    from .cuts import Frame, contact
    nb = job.cfg.get("flats", {}).get("bay_plan", {}).get("bath", {})
    bw, bd = (float(v) for v in nb.get(t, (1.7, 2.0) if t == "sdb" else (1.0, 1.3)))
    zones = job.zs([floor])
    rooms = sorted((c for c in cells if c.type in ("chambre", "salon", "salle_a_manger", "cuisine")),
                   key=lambda c: (c.type == "cuisine", -(c.poly.area - job.minimums[c.type][0]), c.part))
    for c in rooms:
        for w in ways(cells):
            for a, b in sorted(contact(c.poly, w.poly), key=lambda ab: -math.dist(*ab)):
                if math.dist(a, b) < bw + P.need(job):
                    continue
                for p, q in ((a, b), (b, a)):
                    F = Frame(p[0], p[1], math.atan2(q[1] - p[1], q[0] - p[0]))
                    inward = 1.0 if c.poly.contains(shapely.Point(*F.world(bw / 2, 0.1))) else -1.0
                    bath = c.poly.intersection(F.rect(0.0, min(0.0, inward * bd), bw, max(0.0, inward * bd)))
                    if bath.geom_type != "Polygon" or not job.fits(bath, t):
                        continue
                    rest = c.poly.difference(bath)
                    if rest.geom_type != "Polygon" or not job.fits(rest, c.type) or shared(rest, w.poly) < P.need(job):
                        continue
                    new = [Cell(bath, t, c.band, c.part + "b"), Cell(rest, c.type, c.band, c.part)]
                    if any(R.clash_polys(x.poly, y.poly, zones, job.half * 2) for x in new for y in cells + new
                           if y is not c and x is not y and R.near(x.poly, y.poly)):
                        continue
                    cells.remove(c)
                    cells += new
                    return True
    return False


def clean(job, cells: list, prog: list, floor: int) -> bool:
    """True when the plan needs no mending: the program's rooms all there, every room within its minimum and
    `most`, no fault the search counts (blind rooms and partitions included) and every room against the hall
    or a couloir for its door."""
    if any(not c.type for c in cells):
        return False
    if sum(max(0, prog.count(t) - sum(c.type == t for c in cells)) for t in sorted(set(prog))):
        return False
    if any(c.type == "hall" and not job.fits(c.poly, "hall") for c in cells):
        return False
    most = job.cfg.get("rooms", {}).get("most", {})
    if any(c.poly.area > float(most.get(c.type, 1e9)) + 0.01 for c in cells):   # (a hall or couloir too)
        return False
    if any(a > float(most.get(t, 1e9)) + 0.01 for t, a in nooked(job, cells)):  # as the rooms grow by `nooks`
        return False
    if P.faults(job, cells, floor, True, 2):
        return False
    sun = P.lights(job, floor)
    if any(c.type in LIT and not P.lit(c.poly, sun) for c in cells):
        return False
    return strip_ok(job, cells) and all(door_on_way(job, c, cells) for c in cells if c.type not in P.SPINE)


def nooked(job, cells: list) -> list:
    """(type, area) of the rooms the cells become once `spine.nooks` has joined their scraps to their
    neighbours (a couloir scrap to the couloir: 47.2 flats round G), on stand-ins for the rooms."""
    from types import SimpleNamespace as NS
    rooms = [NS(id=i, type=c.type, polygon=c.poly) for i, c in enumerate(cells)]
    P.nooks(NS(interior=NS(rooms=list(rooms)), minimums=job.minimums, fits=job.fits), rooms)
    return [(r.type, r.polygon.area) for r in rooms]


def strip_ok(job, cells: list) -> bool:
    """No lit room with more than `[interiors.flats] strip` m2 in parts too narrow to live in."""
    wide, most = (float(v) for v in job.cfg.get("flats", {}).get("strip", (1.6, 3.0)))
    return all(P.strip(c.poly, wide) <= most for c in cells if c.type in LIT)



def reach_of(job, region, floor: int, which: str) -> float | None:
    """The middle depth of the region behind its lit walls (`which`): from each window's inside point
    straight in to the far wall, the median; None without such a window."""
    from shapely.geometry import LineString
    from .dar import inside
    courts = P.courts(job, floor)
    out = []
    for o in job.interior.openings:
        if o.floor != floor or o.kind not in ("window", "balcony") or not o.piece or o.wall is None:
            continue
        p = inside(o, job.ext)
        if region.distance(p) > 0.05:
            continue
        wall = LineString(o.wall)
        court = any(k.distance(wall.interpolate(0.5, normalized=True)) < job.ext + 0.3 for k in courts)
        if which != "all" and court != (which == "court"):
            continue
        n = np.array([math.sin(o.yaw), -math.cos(o.yaw)])
        ray = LineString([p.coords[0], tuple(np.array(p.coords[0]) + n * 20.0)]).intersection(region.buffer(0.01))
        first = next((g for g in shapely.get_parts(ray) if g.distance(p) < 0.1), None)
        if first is not None:
            out.append(first.length)
    return float(np.median(out)) if out else None


def lit_edges(job, region, floor: int, which: str):
    """The region's wall faces holding its windows on a floor (`which`: "street", "court" or "all"), as lines
    along those walls; None when there are none."""
    from shapely.geometry import LineString
    from .dar import inside
    courts = P.courts(job, floor)
    out = []
    for o in job.interior.openings:
        if o.floor != floor or o.kind not in ("window", "balcony") or not o.piece or o.wall is None:
            continue
        if region.distance(inside(o, job.ext)) > 0.05:
            continue
        wall = LineString(o.wall)
        court = any(k.distance(wall.interpolate(0.5, normalized=True)) < job.ext + 0.3 for k in courts)
        if which != "all" and court != (which == "court"):
            continue
        d = np.subtract(o.wall[1], o.wall[0])
        d = d / max(float(np.hypot(*d)), 1e-9)
        edge = region.boundary.intersection(wall.buffer(2 * job.ext + 0.2, cap_style="flat"))
        for g in shapely.get_parts(shapely.line_merge(edge) if edge.geom_type == "MultiLineString" else edge):
            xy = shapely.get_coordinates(g)
            if g.geom_type != "LineString" or g.length < 1.0:   # a reveal's jog is no lit wall
                continue
            e = (xy[-1] - xy[0]) / max(float(np.hypot(*(xy[-1] - xy[0]))), 1e-9)
            if abs(float(e @ d)) > 0.98:
                out.append(g)
    return shapely.union_all(out) if out else None


def along(job, region, entry, floor: int, cfg: dict, which: str, deep: float):
    """Untyped cells of a flat whose rooms stand `deep` m deep along its lit walls (`which`), the couloir
    (`couloir` m) behind them, the hall at the entry (the least, its sides clear of the openings) with a
    stub to the couloir when they do not meet; the rooms cut at their wall's piers (`wall_cuts`), what lies
    beyond the couloir blind pieces. None when the ways come apart."""
    from shapely.geometry import LineString
    from shapely.ops import nearest_points
    from .cuts import clip, parts, polygonal, snap, solid
    lit = lit_edges(job, region, floor, which)
    if lit is None:
        return None
    c = cfg["couloir"]
    near = lit.buffer(deep, cap_style="flat", join_style="mitre")
    band = solid(shapely.intersection(region, polygonal(shapely.difference(
        lit.buffer(deep + c, cap_style="flat", join_style="mitre"), near)), grid_size=1e-6))   # no sliver line in the overlay
    fd = P.door_frame(entry)
    sizes = [(cfg["hall"][0], cfg["hall_width"][0])]
    if middle(job):                                     # the least hall too small: deeper, then wider
        sizes += [(cfg["hall"][1], cfg["hall_width"][0]), (cfg["hall"][1], cfg["hall_width"][1])]
    for d, w in sizes:
        strip = clip(region, fd.rect(-w / 2 - 1.0, -1.0, w / 2 + 1.0, d))
        a = P.free_side(job, strip, fd, 0, -w / 2, floor, -w / 2 - 1.0)
        b = P.free_side(job, strip, fd, 0, w / 2, floor, w / 2 + 1.0)
        got = P.free(job, clip(region, fd.rect(a, -1.0, b, d + 1.0)), fd, 1, d, floor, d - 0.6, d + 0.6)
        hall = P.largest_near(clip(region, fd.rect(a, -1.0, b, got if got is not None else d)), entry)
        if hall is None or job.fits(hall, "hall"):
            break
    if hall is None or band.is_empty:
        return None
    band = solid(shapely.difference(band, hall, grid_size=1e-6))
    left = [q for q in parts(band) if q.area >= c * c]
    got_ = [hall]
    ways_, stubs = [], []
    while left:                                         # each couloir piece joined to the hall, the nearest
        q0 = min(left, key=lambda q: (round(q.distance(shapely.union_all(got_)), 3), -q.area))   # first: a stub
        left.remove(q0)                                 # when they do not meet (straight, at most `stub` m)
        to = shapely.union_all(got_)
        if q0.distance(to) > 1e-4:
            p, q = nearest_points(to, q0)
            if p.distance(q) > (numbers(job)["stub_middle"] if middle(job) else numbers(job)["stub"]):
                continue
            stub = solid(shapely.difference(clip(region, LineString([p, q]).buffer(c / 2, cap_style="flat", join_style="mitre")),
                                            to, grid_size=1e-6))
            if stub.is_empty or stub.distance(q0) > 1e-4 or stub.distance(to) > 1e-4:
                continue
            stubs.append(stub)
            got_.append(stub)
        ways_.append(q0)
        got_.append(q0)
    if not ways_:
        return None
    rest = shapely.difference(region, shapely.union_all([hall] + ways_ + stubs), grid_size=1e-6)
    cells = [Cell(hall, "hall", "spine", "hall")] + [Cell(q, "couloir", "spine", "couloir") for q in ways_]
    for stub in stubs:
        cells += [Cell(q, "couloir", "spine", "stub") for q in parts(snap(stub))]
    for piece in parts(snap(rest)):
        cells += wall_cuts(job, piece, floor)
    return cells


def wall_cuts(job, piece, floor: int) -> list:
    """A room piece cut at the piers of the wall holding most of its windows (`piers`' rule), as untyped
    cells; a piece with no window stays one blind cell."""
    from .cuts import Frame
    from .dar import inside
    ops = [o for o in job.interior.openings if o.floor == floor and o.kind in ("window", "balcony") and o.piece
           and o.wall is not None and piece.distance(inside(o, job.ext)) < 0.05]
    if not ops:
        return [Cell(piece, "", "A", "blind")]
    walls = {}
    for o in ops:
        walls.setdefault(tuple(round(v, 2) for v in (*o.wall[0], *o.wall[1])), []).append(o)
    (ax, ay, bx, by), _ = max(walls.items(), key=lambda kv: (len(kv[1]), kv[0]))
    F = Frame(ax, ay, math.atan2(by - ay, bx - ax))
    return piers(job, [Cell(piece, "", "A", "wall")], {"F": F}, floor)
