"""Colonial flats planned round their court in wings (47.2 round C, SPEC 6c "Flats").

A floor of a Tunis or Algiers block of 1900-1950 rings its court in wings: straight bands between the street
wall and the court wall. A flat region that wraps a court is split at the court's corners (the lines of the
court's sides, moved clear of the openings) into wing pieces and corner pieces; each corner joins the wing
beyond it as seen from the flat's entry, so the corner where two wings meet holds the second wing's hall or
couloir end. The wings are laid one by one by the spine, the first from the landing with the hall, each next one
from the way (hall or couloir) of the wing before it, carried on to their shared edge; the program is shared
out by the room sizes `[interiors.flats] wing_need` (day rooms near the entry, chambres where room is left, the
baths with the chambres).
"""
from __future__ import annotations

import numpy as np
import shapely
from shapely.geometry import Point

from . import spine as P
from .cuts import Cell, Frame, clip, cut, parts, shared, snap, solid, union, width

BIG = 500.0
DAY = ("salon", "salle_a_manger", "cuisine")


def split(region, court, F: Frame, ats: list) -> list:
    """The pieces of `region` cut by the lines `ats` [(axis, at)] of frame F, each (polygon, (iu, iv)): iu, iv
    = 0, 1, 2 as the piece's middle lies before, along or beyond the court's span on that axis (a wing: one of
    them 1; a corner: neither)."""
    pieces = [region]
    for axis, at in ats:
        nxt = []
        for p in pieces:
            lo, hi = cut(p, F, axis, at)
            nxt += lo + hi
        pieces = nxt
    c0, d0, c1, d1 = F.bounds(court)
    out = []
    for p in pieces:
        u, v = F.local(p.representative_point().coords[0])
        out.append((p, (0 if u < c0 else 2 if u > c1 else 1, 0 if v < d0 else 2 if v > d1 else 1)))
    return out


def group(pieces: list, start, least: float = 12.0, narrow: float = 2.4, way: float = 1.1) -> list:
    """The wings of split pieces in order from the piece nearest `start` (a Point), each (polygon, parent index
    or None): a corner joins the wing beyond it (farther from the start; on a tie, the longer shared edge), a thin
    corner (narrower than `narrow`) or the start corner the wing it shares most with, a wider wing first. A piece
    narrower than `way`, or under `least` m2 and not thin, joins the neighbour it shares most with; a thin wing
    between two others stays: it is a couloir (a gallery along the court), at an end it joins its neighbour."""
    polys = [p for p, _ in pieces]
    kinds = [k for _, k in pieces]
    if len(polys) < 2:
        return []
    near = lambda a, b: shared(a, b) > 0.5     # noqa: E731
    thin = [width(p) < narrow for p in polys]
    first = min(range(len(polys)), key=lambda i: (round(polys[i].distance(start), 3), -polys[i].area))
    hops = {first: 0}
    todo = [first]
    while todo:
        i = todo.pop(0)
        for j in range(len(polys)):
            if j not in hops and near(polys[i], polys[j]):
                hops[j] = hops[i] + 1
                todo.append(j)
    groups = {i: [i] for i in range(len(polys)) if 1 in kinds[i]}
    for i in range(len(polys)):
        if 1 in kinds[i]:
            continue
        nb = [j for j in groups if near(polys[i], polys[j])]
        if not nb:
            groups[i] = [i]
            continue
        wide = [j for j in nb if not thin[j]] or nb
        if thin[i] or i == first:
            j = max(wide, key=lambda j: (shared(polys[i], polys[j]), -j))
        else:
            j = max(wide, key=lambda j: (hops.get(j, -1), shared(polys[i], polys[j]), -j))
        groups[j].append(i)
    wings = []
    for members in groups.values():
        got = polys[members[0]]
        for m in members[1:]:
            got = union(got, polys[m]) or got
        wings.append(got)
    changed = True
    while changed and len(wings) > 1:
        changed = False
        for i, w in enumerate(wings):
            nb = [j for j in range(len(wings)) if j != i and shared(w, wings[j]) > 0.5]
            wd = width(w)
            if wd >= way and (w.area >= least or wd < narrow) and not (wd < narrow and len(nb) < 2):
                continue
            j = max(nb, key=lambda j: (shared(w, wings[j]), -j), default=None)
            merged = union(wings[j], w) if j is not None else None
            if merged is None:
                continue
            wings[j] = merged
            del wings[i]
            changed = True
            break
    return order(wings, start)


def order(wings: list, start) -> list:
    """(wing, parent index) in walking order from the wing nearest `start`; a wing no edge reaches is left out."""
    if not wings:
        return []
    first = min(range(len(wings)), key=lambda i: (round(wings[i].distance(start), 3), -wings[i].area))
    out, idx, todo = [(wings[first], None)], {first: 0}, [first]
    while todo:
        i = todo.pop(0)
        for j in sorted(range(len(wings)), key=lambda j: (-shared(wings[i], wings[j]), j)):
            if j not in idx and shared(wings[i], wings[j]) > 0.5:
                idx[j] = len(out)
                out.append((wings[j], idx[i]))
                todo.append(j)
    return out


def court_of(job, region, f: int):
    """The largest court of floor f the region wraps (its sides at least `wing_court` m), or None."""
    cfg = job.cfg.get("flats", {})
    side = float(cfg.get("wing_court", 3.9))
    got = []
    for c in P.courts(job, f):
        if region.distance(c) > 0.05:
            continue
        cf = Frame.of(c)
        u0, v0, u1, v1 = cf.bounds(c)
        if min(u1 - u0, v1 - v0) >= side - 1e-6:
            got.append(c)
    return max(got, key=lambda c: c.area, default=None)


def wings_of(job, region, f: int, entry: P.Entry) -> list:
    """The flat region's wings in walking order [(polygon, parent)], or [] when it wraps no court."""
    court = court_of(job, region, f)
    if court is None:
        return []
    F = Frame.of(court)
    c0, d0, c1, d1 = F.bounds(court)
    ats = []
    for axis, at, sgn in ((0, c0, -1.0), (0, c1, 1.0), (1, d0, -1.0), (1, d1, 1.0)):
        lo, hi = sorted((at, at + sgn * 0.6))         # moved off the court's span, clear of the openings
        got = job.free(region, F, axis, at, [f], lo, hi)
        if got is not None:
            ats.append((axis, got))
    cfg = job.cfg.get("flats", {})
    pieces = split(region, court, F, ats)
    return group(pieces, Point(entry.x, entry.y), float(cfg.get("wing_least", 12.0)), narrow(job), P.couloir(job))


def narrow(job) -> float:
    """`[interiors.flats] wing_narrow`: a wing narrower than this is a couloir (a gallery along the court)."""
    return float(job.cfg.get("flats", {}).get("wing_narrow", 2.4))


def share(job, wings: list, prog: list) -> list | None:
    """The program of every wing (in `prog`'s order): day rooms in the first wing that holds them, chambres
    where most room is left, the baths in the wing with most chambres; None when a wing gets nothing."""
    cfg = job.cfg.get("flats", {})
    need = {k: float(v) for k, v in cfg.get("wing_need", {}).items()}
    way = float(cfg.get("wing_way", 0.3))
    gallery = [width(w) < narrow(job) for w, _ in wings]
    cap = [-1e9 if g else w.area * (1.0 - way) for (w, _), g in zip(wings, gallery)]
    out: list = [[] for _ in wings]

    def put(i, t):
        out[i].append(t)
        cap[i] -= need.get(t, 10.0)

    for t in [t for t in prog if t in DAY]:
        i = next((i for i in range(len(wings)) if cap[i] >= need.get(t, 10.0)), None)
        put(i if i is not None else max(range(len(wings)), key=lambda i: (cap[i], -i)), t)
    for t in [t for t in prog if t == "chambre"]:
        empty = [i for i in range(len(wings)) if not out[i] and cap[i] >= need.get(t, 10.0)]   # every wing a room
        put(max(empty or range(len(wings)), key=lambda i: (cap[i], i)), t)
    for t in [t for t in prog if t not in DAY and t != "chambre"]:
        fit = [i for i in range(len(wings)) if cap[i] >= need.get(t, 4.0)]
        pick = max(fit or range(len(wings)), key=lambda i: (out[i].count("chambre"), cap[i], i))
        put(pick, t)
    if any(not o and not g for o, g in zip(out, gallery)) or all(gallery):
        return None
    rank = {t: k for k, t in enumerate(dict.fromkeys(prog))}
    return [sorted(o, key=lambda t: rank[t]) for o in out]


def reach(job, cells: list, wing, child, f: int):
    """The way (hall or couloir) of `cells` (one wing) carried on to the child wing's edge, the cells it crosses
    trimmed (each kept whole and fit for its type): straight on along the way, else along it to the wing's end
    and a couloir wide across that end to the child (a turn at the corner); the child's entry on it, or None."""
    door = P.ARCH + 0.1                                 # ways meet by an arch (`spine.doors`)
    ways = sorted([c for c in cells if c.type in ("hall", "couloir")], key=lambda c: (c.type != "couloir", -c.poly.area))
    for w in ways:
        if shared(w.poly, child) >= door:
            return entry_on(w.poly, child)
    line = wing.boundary.intersection(child.buffer(1e-4, quad_segs=1))
    end = clip(wing, line.buffer(P.couloir(job), cap_style="flat")) if not line.is_empty else None
    for turn in (False, True):
        for w in ways:
            e = extension(w.poly, wing, child, end if turn else None, door)
            if e is not None and carry(job, cells, w, e):
                return entry_on(w.poly, child)
    for w in ways:                                       # across the wing, a couloir wide, from the way to the child
        for e in crossings(w.poly, wing, line, P.couloir(job), child, door):
            if carry(job, cells, w, e):
                return entry_on(w.poly, child)
    return None


def crossings(way, wing, line, c: float, child, door: float) -> list:
    """The strips of `wing` `c` m wide square to its shared edge `line` with the child, from the way to the
    child: at both ends of the edge first, then every 0.5 m from the end nearer the way."""
    from .flats import segments
    seg = max(segments(line), key=lambda t: t[2], default=None) if not line.is_empty else None
    if seg is None or seg[2] < c:
        return []
    a, b, length = seg
    d = (b - a) / length
    H = Frame(float(a[0]), float(a[1]), float(np.arctan2(d[1], d[0])))
    starts = [0.0, length - c] + [x for x in np.arange(0.5, length - c, 0.5)]
    near_way = float(H.local(np.asarray(way.centroid.coords[0]))[0])
    starts = starts[:2] + sorted(starts[2:], key=lambda x: abs(x + c / 2 - near_way))
    out = []
    for x in starts:
        strip = clip(wing, H.rect(x, -BIG, x + c, BIG))
        for p in parts(snap(shapely.difference(strip, way, grid_size=1e-6))):
            if shared(p, way) > 0.5 and shared(p, child) >= door:
                out.append(p)
    return out


def extension(way, wing, child, end, door: float):
    """The piece of `wing` that carries `way` on to `child`: the way's band straight on (with `end`, up to the
    wing's end strip, joined to it), touching the child on at least `door` m; None when there is none."""
    G = Frame.of(way)
    _, v0, _, v1 = G.bounds(way)
    band = clip(wing, G.rect(-BIG, v0, BIG, v1))
    got = []
    for p in parts(snap(shapely.difference(band, way, grid_size=1e-6))):
        if shared(p, way) <= 0.5:
            continue
        if end is not None and not end.is_empty and p.distance(end) < 1e-3:
            p = union(p, solid(shapely.difference(end, way, grid_size=1e-6))) if not p.intersects(end) else \
                solid(shapely.union(p, shapely.difference(end, way, grid_size=1e-6), grid_size=1e-6))
            if p is None or len(parts(p)) != 1:
                continue
            p = parts(p)[0]
        if shared(p, child) >= door:
            got.append(p)
    if not got and end is not None and not end.is_empty:
        p = solid(shapely.difference(end, way, grid_size=1e-6))
        if len(parts(p)) == 1 and shared(parts(p)[0], way) > 0.5 and shared(parts(p)[0], child) >= door:
            got.append(parts(p)[0])
    return min(got, key=lambda p: p.area) if got else None


def carry(job, cells: list, w, e) -> bool:
    """`e` joins the way cell w, cut out of the cells it crosses, when w stays one polygon and every crossed
    room stays one piece fit for its type (a way or untyped cell may go); False (nothing changed) otherwise."""
    grown = union(w.poly, e)
    if grown is None:
        return False
    trimmed = []
    for c in cells:
        if c is w or c.poly.intersection(e).area < 1e-3:
            continue
        rest = sorted(parts(snap(shapely.difference(c.poly, e, grid_size=1e-6))), key=lambda p: -p.area)
        for p in rest[1:]:                                # a room the way crosses: its smaller part joins a room
            host = max((o for o in cells if o is not c and o is not w and o.type not in ("hall", "couloir")),
                       key=lambda o: shared(o.poly, p), default=None)
            if host is None or shared(host.poly, p) < 0.5 or host.poly.intersects(e):
                return False
            trimmed.append((host, p))
        rest = rest[:1]
        if rest and c.type and c.type not in ("hall", "couloir") and not job.fits(rest[0], c.type):
            return False
        if not rest and c.type and c.type not in ("hall", "couloir"):
            return False
        trimmed.append((c, rest[0] if rest else None))
    joins = [(c, p) for c, p in trimmed if p is not None and c.poly.intersection(e).area < 1e-3]   # the hosts
    cuts = [(c, p) for c, p in trimmed if (c, p) not in joins]
    grown_hosts = []
    for c, p in joins:
        g = union(c.poly, p)
        if g is None:
            return False
        grown_hosts.append((c, g))
    w.poly = grown
    for c, rest in cuts:
        if rest is None:
            cells.remove(c)
        else:
            c.poly = rest
    for c, g in grown_hosts:
        c.poly = g
    return True


def joined(job, cells: list, before: list, wing, f: int) -> bool:
    """True when a way of the wing's cells meets a way of the wing before by an arch, the wing's way carried on
    to it when needed (`reach`)."""
    ways = [c.poly for c in before if c.type in ("hall", "couloir")]
    if not ways:
        return False
    target = shapely.union_all(ways)
    door = P.ARCH + 0.1
    if any(shared(c.poly, w) >= door for c in cells if c.type in ("hall", "couloir") for w in ways):
        return True
    return reach(job, cells, wing, target, f) is not None and any(
        shared(c.poly, w) >= door for c in cells if c.type in ("hall", "couloir") for w in ways)


def walk(job, cells: list, entry: P.Entry) -> int:
    """The rooms of a flat's cells no door joins to its way in, as `rooms.check` walks it: from the way at the
    entry through arches to the other ways and through doors (`need`) to a salon or salle a manger; the ways not
    reached, then every other room (a bath: a narrow door's length) sharing too little with what is reached."""
    ways = [c for c in cells if c.type in ("hall", "couloir")]
    door = Point(entry.x, entry.y)
    got = [w for w in ways if w.poly.distance(door) < 0.3]
    todo = list(got)
    while todo:
        a = todo.pop()
        for c in cells:
            if any(c is g for g in got):
                continue
            if (c.type in ("hall", "couloir") and shared(a.poly, c.poly) >= P.ARCH + 0.05) or (
                    c.type in ("salon", "salle_a_manger") and shared(a.poly, c.poly) >= P.need(job)):
                got.append(c)
                todo.append(c)
    n = sum(1 for w in ways if all(w is not g for g in got))
    for c in cells:
        if c.type in P.SPINE or not c.type or any(c is g for g in got):
            continue
        need = P.wet_need(job) if c.type in P.WET else P.need(job)
        if not any(shared(c.poly, g.poly) >= need for g in got):
            n += 1
    return n


def entry_on(way, child) -> P.Entry | None:
    """The middle of the longest straight piece way and child share, its normal pointing into the child."""
    from .flats import segments
    edge = way.boundary.intersection(child.buffer(1e-4, quad_segs=1))
    best = max(segments(edge), key=lambda s: s[2], default=None)
    if best is None:
        return None
    a, b, length = best
    m = (a + b) / 2
    d = (b - a) / length
    n = np.array([-d[1], d[0]])
    if not child.buffer(1e-6).contains(Point(*(m + n * 0.05))):
        n = -n
    return P.Entry(float(m[0]), float(m[1]), float(n[0]), float(n[1]))


def lay(job, region, entry: P.Entry, prog: list, f: int, key: tuple) -> list | None:
    """The flat's cells laid wing by wing, or None when the region wraps no court (or a wing cannot be entered)."""
    if not job.cfg.get("flats", {}).get("wings", {}).get(job.interior.layout):
        return None
    memo = job.__dict__.setdefault("wing_memo", {})    # a typical floor: the same wings again (time)
    tk = P.typical_key(job, region, entry, prog, f, key, True)
    if tk not in memo:
        memo[tk] = laid(job, region, entry, prog, f, key)
    got = memo[tk]
    return None if got is None else [Cell(c.poly, c.type, c.band, c.part) for c in got]


def laid(job, region, entry: P.Entry, prog: list, f: int, key: tuple) -> list | None:
    """`lay` without its memo."""
    wings = wings_of(job, region, f, entry)
    while len(wings) > 1:
        progs = share(job, wings, prog)
        if progs is not None:
            break
        later = [i for i in range(1, len(wings)) if width(wings[i][0]) >= narrow(job)] or list(range(1, len(wings)))
        i = min(later, key=lambda i: (wings[i][0].area, i))   # the smallest later wing joins its parent
        w, p = wings[i]
        merged = union(wings[p][0], w)
        if merged is None:
            return None
        polys = [x for k, (x, _) in enumerate(wings) if k not in (i, p)] + [merged]
        wings = order(polys, Point(entry.x, entry.y))
    if len(wings) < 2:
        return None
    cells: list = []
    mine: list = []
    for i, ((w, parent), sub) in enumerate(zip(wings, progs)):
        if parent is None:
            e, hall = entry, True
        else:
            e, hall = reach(job, mine[parent], wings[parent][0], w, f), False
            if e is None:
                return None
        if width(w) < narrow(job):                      # a gallery along the court: one couloir
            got = [Cell(w, "couloir", "spine", "couloir")]
        else:
            moved = job.interior.__dict__.get("way_moved")
            job.cap_scale = float(job.cfg.get("flats", {}).get("wing_variants", 1.0))
            try:
                got = P.lay(job, w, e, sub, f, key + ("wing", i), hall=hall)
            finally:
                del job.cap_scale
            if not moved:                               # a later wing's way found from its edge is weighed here
                job.interior.__dict__.pop("way_moved", None)   # (`joined`, `walk`), not by `layout.way_moved`
            if parent is not None and not joined(job, got, mine[parent], w, f):
                return None                             # the wing's way does not meet the one before: one region
        mine.append(got)
    for got in mine:
        cells += got
    return cells
