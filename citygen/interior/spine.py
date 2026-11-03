"""The spine engine of modern homes (SPEC 6c "Villas and houses of the new districts", "Flats").

A hall at the entrance, a couloir along the region (parallel to its windowed walls, so the rooms on both
sides reach a window), and rooms cut across the couloir on both sides. The cells are then typed by light
and a program list: the salon takes the largest windowed cell (a balcony door's cell first), the salle a
manger the windowed cell beside it, the cuisine the windowed cell farthest from the entrance, the
chambres the other windowed cells, the sdb and the wc blind cells (or are carved from a room's couloir
end). Cells the program leaves over join a neighbour. Nothing raises: odd regions give fewer rooms.
"""
from __future__ import annotations

import math
from typing import NamedTuple

import numpy as np
import shapely
from shapely.geometry import Point

from ..rng import stream
from . import rooms as R
from . import stairs as S
from .cuts import Cell, Frame, absorb, clashes, clip, contact, cut, despike, offsets, partition, parts, shared, snap, solid, union, width

LIVING = ("salon", "salle_a_manger", "cuisine", "chambre")   # want a facade window
WET = ("sdb", "wc")
SPINE = ("hall", "couloir", "palier")                       # the ways in: never typed, merged or carved
MARGIN = 1.0      # meters: rectangles reach this far past the region so its edges stay its own
SLIVER_GAP = 1.2  # meters: a hall this near a wall reaches it (no strip of room between them)


class Entry(NamedTuple):
    """Where a home is entered: a point on its region's edge and the unit normal pointing in."""
    x: float
    y: float
    nx: float
    ny: float


def couloir(job) -> float:
    """The couloir's width: `[interiors.villa] couloir`, in flats `[interiors.flats] couloir` (47.1/48.1)."""
    width = float(job.cfg.get("villa", {}).get("couloir", 1.1))
    if job.interior.layout in ("colonial", "slab"):
        return float(job.cfg.get("flats", {}).get("couloir", width))
    return width


def numbers(job) -> dict:
    """The spine's numbers (`[interiors.villa]`), with defaults."""
    cfg = job.cfg.get("villa", {})
    return {"hall": [float(v) for v in cfg.get("hall", [2.0, 3.0])],
            "hall_width": [float(v) for v in cfg.get("hall_width", [1.8, 2.6])],
            "couloir": couloir(job), "side": float(cfg.get("side", 2.6)),
            "rhythm": [float(v) for v in cfg.get("rhythm", [3.6, 3.2, 2.8])],
            "variants": int(cfg.get("variants", 24))}


def rng(job, *key):
    i = job.interior
    n = i.__dict__.get("redraw")                      # a faulty plan drawn again (`layout.redraw`, round 8)
    return stream(i.seed, "interior", i.city_id, i.building, "layout", *key, *(("again", n) if n else ()))


def wet_need(job) -> float:
    """The shared length a sdb's or wc's narrow door needs (`[interiors.openings] narrow`, `narrow_clear`)."""
    rules = job.interior.rules
    return rules.get("narrow", 0.7) + 2 * (rules.get("narrow_clear", 0.05) + job.half)


def inner(job) -> float:
    """How far an inner door of a modern home keeps from the partitions beside it (`inner_clear`, lead
    decision for prompt 47: a door frame needs about 0.12 m); the facade rule `clear` stays for openings."""
    return float(job.interior.rules.get("inner_clear", job.clear))


def deep(job) -> float:
    """How far both rooms reach behind a door the plan check accepts: half a partition and its `probe`."""
    return job.half + float(job.interior.rules.get("plan", {}).get("probe", 0.1)) + 0.02


def need(job) -> float:
    """The shared length an inner door needs: its width and `inner_clear` plus half a partition at both sides."""
    return job.door + 2 * (inner(job) + job.half)


def lay(job, region, entry: Entry, program: list, floor: int, key: tuple, hall: bool = True) -> list:
    """The typed cells of one modern home's floor in `region`, entered at `entry`. `program`: room types in
    order (`chambre*` makes every windowed cell left a chambre). `key` names the layout stream (one per
    home and floor). Variants are tried in a fixed order (the drawn hall then the least; the rhythms coarsest
    first; the couloir along the windowed walls, then turned; placed as the rules say, then against either
    side wall), at most `variants` of them: the first with no fault (`faults`) wins, else the fewest."""
    memo = typical(job, region, entry, program, floor, key, hall)
    if memo is not None:
        return memo
    cells = search(job, region, entry, program, floor, key, hall)
    job.__dict__.setdefault("typical", {})[typical_key(job, region, entry, program, floor, key, hall)] = cells
    base = typical_key(job, region, entry, program, floor, key, hall)[:5]
    job.__dict__.setdefault("stacked", {}).setdefault(base, []).append(cells)
    return [Cell(c.poly, c.type, c.band, c.part) for c in cells]


def typical_key(job, region, entry: Entry, program: list, floor: int, key: tuple, hall: bool) -> tuple:
    """What a floor's plan depends on: the region, the entrance, the program, the stream key and the facade
    openings near it (kind, place, width; not the lit state)."""
    near = region.buffer(1.0)
    same = job.interior.layout == "colonial"              # a colonial balcony door lights as its window would
    kind = lambda o: "light" if same and o.kind in ("window", "balcony") else o.kind   # noqa: E731
    ops = tuple(sorted((kind(o), round(o.x, 2), round(o.y, 2), round(o.width, 2)) for o in job.interior.openings
                       if o.floor == floor and o.piece and near.contains(Point(o.x, o.y))))
    return (shapely.to_wkb(shapely.set_precision(region, 1e-3)), tuple(round(v, 3) for v in entry), tuple(program),
            key, hall, ops)


def typical(job, region, entry: Entry, program: list, floor: int, key: tuple, hall: bool):
    """A typical floor (stacked flats, stacked plumbing): when an earlier floor had this region, entrance,
    program and facade, its cells again (copies); None otherwise."""
    tk = typical_key(job, region, entry, program, floor, key, hall)
    got = job.__dict__.get("typical", {}).get(tk)
    if got is not None:
        return [Cell(c.poly, c.type, c.band, c.part) for c in got]
    for plan in job.__dict__.get("stacked", {}).get(tk[:5], []):   # a floor below with other windows: kept
        cells = [Cell(c.poly, c.type, c.band, c.part) for c in plan]   # when it holds here without a fault
        if faults(job, cells, floor, hall) == 0:
            return cells
    return None


def search(job, region, entry: Entry, program: list, floor: int, key: tuple, hall: bool) -> list:
    """The variant search of `lay`."""
    cfg = numbers(job)
    r = rng(job, *key)
    depth = float(r.uniform(*cfg["hall"]))
    wide = float(r.uniform(*cfg["hall_width"]))
    best = None
    seen = set()
    cuts = 0
    cap = max(6, min(cfg["variants"], int(cfg["variants"] * 120.0 / max(region.area, 120.0))))   # big floors: fewer
    cap = max(6, int(cap * job.__dict__.get("cap_scale", 1.0)))   # a flat's second tries: fewer (`flats.best_lay`)
    small = (cfg["hall"][0], cfg["hall_width"][0])      # a variant with the least hall
    hard = 2 if job.interior.layout in ("colonial", "slab") else 1   # flats: a blind cuisine weighs less than
    # a fault `rooms.check` finds (it asks no window of a flat's cuisine; 47.1 flats round 1)
    early = hard > 1 or job.interior.__dict__.get("bays_early", False)   # a failing house's second plan (round 8)
    way = job.interior.__dict__.get("bays_early", False)   # a failing house's second plan: day rooms off the
    # way score too, and of variants as good the fewest dark rooms (round 10)
    first = None        # an upper floor's first faultless variant whose couloir misses the landing (round 10)
    sun = lights(job, floor)
    blind_cap = int(job.cfg.get("flats", {}).get("blind_cap", {}).get(job.interior.layout, 10 ** 6))
    for d, w in ((depth, wide), small):
        for cell in cfg["rhythm"]:
            for turn in (False, True):
                for place in ("auto", "low", "high"):
                    cuts += 1
                    if (len(seen) >= cap or cuts > 3 * cap) and best is not None:
                        if first is not None:
                            return first[0]
                        return late_bays(job, best, floor, hall, hard)   # time: the best of the first variants
                    up = not hall and landing_way(job)  # the landing pass: an upper floor's couloir starts at
                    cells, spine = cut_region(job, region, entry, floor, cfg, d, w, cell, hall or up, turn, place)
                    if up:                              # the landing as the hall below does (47.2 houses round 3)
                        cells, spine = as_couloir(cells, spine)
                    sig = tuple(sorted(round(c.poly.area, 2) for c in cells))
                    if sig in seen:
                        continue                        # the same cells as a variant already tried
                    seen.add(sig)
                    missing = assign(job, cells, spine, program, floor, entry)
                    score = len(missing) * 3 * hard + faults(job, cells, floor, hall, hard)
                    if score > len(missing) * 3 * hard and early and bay_depth(job) > 0.0:   # flats: window bays
                        score = len(missing) * 3 * hard + bays(job, cells, floor, hall, hard, score - len(missing) * 3 * hard)
                    if way:
                        score += hard * astray(job, cells, entry) + dark(job, cells, floor) / 100.0
                    elif up:                            # a couloir off the landing weighs as a fault
                        score += hard * astray(job, cells, entry)
                    elif (score == 0 and not hall and not job.interior.__dict__.get("way_plain")
                          and (first is not None or astray(job, cells, entry))):
                        if astray(job, cells, entry) == 0 and dark(job, cells, floor) <= first[1]:
                            job.interior.way_moved = True   # `layout.way_moved` weighs it against the first
                            return cells                # a later variant reaches the landing, no darker
                        first = first or (cells, dark(job, cells, floor))
                        continue
                    if score == 0:
                        return cells
                    if best is None or score < best[1]:
                        best = (cells, score, len(missing))
                    if len(seen) >= blind_cap and best[1] <= hard * blind(job, best[0], sun):
                        return late_bays(job, best, floor, hall, hard)   # only blind rooms left: time (47.2 B)
    if first is not None:
        return first[0]
    return late_bays(job, best, floor, hall, hard)


def landing_way(job) -> bool:
    """A house's upper floors in its landing pass (`layout.landing_way`): the couloir starts at the stair
    landing, as in a real house (`[interiors.villa] landing_way` lists the layouts; 47.2 houses round 3)."""
    return (job.interior.__dict__.get("landing_way", False)
            and job.interior.layout in job.cfg.get("villa", {}).get("landing_way", ()))


def as_couloir(cells: list, spine: dict) -> tuple:
    """An upper floor cut with a hall at the landing: the hall becomes the couloir's first piece."""
    for c in cells:
        if c.type == "hall":
            c.type = "couloir"
    cells = join_spine(cells)
    ways = [c.poly for c in cells if c.type == "couloir"]
    return cells, {**spine, "couloir": ways[0] if ways else None, "hall": None, "ways": ways}


def dark(job, cells: list, floor: int) -> int:
    """The chambres, salons, salles a manger and cuisines among a floor's cells with no window or with a strip
    over `[interiors.flats] strip` (`layout.dim`)."""
    sun = lights(job, floor)
    wide, most = (float(v) for v in job.cfg.get("flats", {}).get("strip", (1.6, 3.0)))
    return sum(1 for c in cells if c.type in LIVING and (not lit(c.poly, sun) or strip(c.poly, wide) > most))


def astray(job, cells: list, entry: Entry) -> int:
    """The day rooms (salon, salle a manger, cuisine) of a floor's cells no door can join to its way in: the
    hall or couloir the entry opens into, or a salon or salle a manger joined to it (a shared edge of
    `need`), plus one when no hall or couloir reaches the entry (a house's stair box: room for an arch on any side;
    47.1 + 48.1 round 10)."""
    door = Point(entry.x, entry.y)
    ways = [c for c in cells if c.type in ("hall", "couloir")]
    if not ways:
        return 0
    box = job.__dict__.get("landing")                 # a house's stair box: a way opens on it
    if box is not None:
        n = 0 if any(shared(c.poly, box) >= ARCH + 0.05 for c in ways) else 1   # the palier's arch (`arch`)
    else:
        n = 0 if any(c.poly.distance(door) < 0.3 for c in ways) else 1
    day = [c for c in cells if c.type in ("salon", "salle_a_manger", "cuisine")]
    got, todo = list(ways), list(ways)
    while todo:
        a = todo.pop()
        for c in day:
            if all(c is not g for g in got) and shared(a.poly, c.poly) >= need(job):
                got.append(c)
                if c.type != "cuisine":
                    todo.append(c)
    return n + sum(1 for c in day if all(c is not g for g in got))


def late_bays(job, best: tuple, floor: int, hall: bool, hard: int) -> list:
    """Villas and maisons: the window bays (`bays`) traded on the search's best plan only when no variant
    passed, so a plan that passes keeps its cells (47.1 round 8)."""
    cells, score, missing = best
    if hard == 1 and score > missing * 3 and bay_depth(job) > 0.0 and not job.interior.__dict__.get("bays_early"):
        bays(job, cells, floor, hall, hard, score - missing * 3)
    return cells


def bay(o, ext: float, clear: float, half: float, depth: float):
    """The window bay of facade opening o: along its wall `clear` + `half` (+ 0.02 m) beyond both edges, from
    just outside the wall to `depth` m inside its inner face. A partition along the bay's inner and side
    edges keeps clear of the opening."""
    from .mesh import frame_of
    c, front, along = frame_of(o)
    t = o.width / 2 + clear + half + 0.02
    a, b = -(ext + depth), 0.05
    return shapely.Polygon([c + along * -t + front * a, c + along * t + front * a,
                            c + along * t + front * b, c + along * -t + front * b])


def bay_depth(job) -> float:
    """`bays`: how deep a window bay is traded (`[interiors.flats]` or `[interiors.villa] bay_depth`; 0: never)."""
    part = "flats" if job.interior.layout in ("colonial", "slab") else "villa"
    return float(job.cfg.get(part, {}).get("bay_depth", 0.0))


def bays(job, cells: list, floor: int, hall: bool, hard: int, n: int) -> int:
    """A way (couloir, hall) and a room whose partition ends inside a window's zone: one gives the other
    its piece of the window bay (`[interiors.flats] bay_depth`), the partition then turning along the
    bay's edges, when that leaves the floor with fewer faults (`faults`, `n` before); the faults left."""
    depth = bay_depth(job)
    ops = [o for o in job.interior.openings if o.floor == floor and o.wall is not None and o.kind != "shop"]
    if depth <= 0.0 or not ops:
        return n
    zones = job.zs([floor])
    rules = job.interior.rules
    boxes = [bay(o, job.ext, rules["clear"], job.half, depth) for o in ops]
    for i, a in enumerate(cells):
        for b in cells[i + 1:]:
            if not ({a.type, b.type} & {"couloir", "hall"}) or not R.clash_polys(a.poly, b.poly, zones, job.half * 2):
                continue
            for box in boxes:
                if a.poly.distance(box) > 1e-6 or b.poly.distance(box) > 1e-6:
                    continue
                n = give(job, a, b, box, cells, floor, hall, hard, n)
                n = give(job, b, a, box, cells, floor, hall, hard, n)
                if n == 0:
                    return n
    return n


def give(job, donor, taker, box, cells: list, floor: int, hall: bool, hard: int, n: int) -> int:
    """`bays`: the donor cell's piece of a window bay joins the taker when both stay one polygon, the donor
    keeps a door's width with every cell it touched and the floor has fewer than `n` faults; the faults."""
    piece = shapely.union_all(parts(shapely.intersection(donor.poly, box, grid_size=1e-6)))
    if piece.is_empty or piece.area < 0.05:
        return n
    rest = parts(snap(shapely.difference(donor.poly, box, grid_size=1e-6)))
    got = parts(snap(shapely.union(taker.poly, piece, grid_size=1e-6)))
    if len(rest) != 1 or len(got) != 1 or R.clash_polys(rest[0], got[0], job.zs([floor]), job.half * 2):
        return n
    door = need(job)
    keep = [c for c in cells if c is not donor and c is not taker and shared(donor.poly, c.poly) >= door - 1e-6]
    if any(shared(rest[0], c.poly) < door - 1e-6 for c in keep):
        return n
    old = donor.poly, taker.poly
    donor.poly, taker.poly = rest[0], got[0]
    m = faults(job, cells, floor, hall, hard)
    if m < n:
        return m
    donor.poly, taker.poly = old
    return n


def faults(job, cells: list, floor: int, hall: bool = False, hard: int = 1) -> int:
    """What `rooms.check` would find in one home's floor before it exists: rooms under their minimum or over
    their `most`, and partitions meeting a wall within `clear` of an opening. Each counts `hard`, a blind
    cuisine in a lit home 1; with `[interiors.flats] blind_faults` a blind chambre or salle a manger `hard`
    (the window check, 47.2 round B)."""
    most = job.cfg.get("rooms", {}).get("most", {})
    zones = job.zs([floor])
    n = 0 if not hall or any(c.type == "hall" for c in cells) else 3 * hard
    sun = lights(job, floor)
    if any(lit(c.poly, sun) for c in cells):              # a lit home: the salon gets a window, then the cuisine
        for t in ("salon", "cuisine"):
            if any(c.type == t for c in cells) and not any(c.type == t and lit(c.poly, sun) for c in cells):
                n += 2 * hard if t == "salon" else 1
        n += hard * blind(job, cells, sun)
    for c in cells:
        if c.type in SPINE or c.type in ("droj",):
            if c.type in most and c.poly.area > float(most[c.type]) + 0.01:
                n += hard
            continue
        if not job.fits(c.poly, c.type) or c.poly.area > float(most.get(c.type, 1e9)) + 0.01:
            n += hard
    memo = job.__dict__.setdefault("clash_memo", {}) if job.interior.layout in ("colonial", "slab") else None
    for i, a in enumerate(cells):
        for b in cells[i + 1:]:
            if clash_of(job, a.poly, b.poly, zones, floor, memo):
                n += hard
    return n


def clash_of(job, a, b, zones: list, floor: int, memo) -> bool:
    """`rooms.clash_polys` of two cells, remembered per floor and pair of shapes in flats (`memo`; the variants
    of a flat's search score the same pairs again: time, same answers)."""
    if memo is None:
        return R.clash_polys(a, b, zones, job.half * 2)
    if not R.near(a, b):
        return False
    key = (floor, id(job.zones), shapely.to_wkb(a), shapely.to_wkb(b))   # zones: a swapped set asks again
    got = memo.get(key)
    if got is None:
        got = memo[key] = R.clash_polys(a, b, zones, job.half * 2)
    return got


def blind(job, cells: list, sun: list) -> int:
    """With `[interiors.flats] blind_faults` (by layout), the blind chambres and salles a manger of a floor's
    cells (the window check, 47.2 round B); else 0."""
    if not job.cfg.get("flats", {}).get("blind_faults", {}).get(job.interior.layout):
        return 0
    return sum(1 for c in cells if c.type in ("chambre", "salle_a_manger") and not lit(c.poly, sun))


# --- cutting -------------------------------------------------------------------------------------------
def lights(job, floor: int, kinds=("window", "balcony")) -> list:
    """Points just inside every facade window (and balcony door) of a floor."""
    from .dar import inside
    return [inside(o, job.ext) for o in job.interior.openings if o.floor == floor and o.kind in kinds and o.piece]


def lit(poly, points: list) -> bool:
    """True when a window's inside point lies in the cell (as `rooms.assign` will put the window there)."""
    return any(poly.distance(p) < 0.05 for p in points)


def couloir_frame(job, region, floor: int) -> Frame:
    """The region's frame turned so u runs along the walls with the most window width (rooms on both sides
    of the couloir then reach them); on a tie, along the region's long side."""
    fr = Frame.of(region)
    score = [0.0, 0.0]
    for o in job.interior.openings:
        if o.floor != floor or o.kind not in ("window", "balcony") or not o.piece:
            continue
        from .dar import inside
        if region.distance(inside(o, job.ext)) > 0.2:
            continue
        along = np.array([math.cos(o.yaw), math.sin(o.yaw)])
        score[0 if abs(float(along @ fr.u)) >= abs(float(along @ fr.v)) else 1] += o.width
    u0, v0, u1, v1 = fr.bounds(region)
    deep = float(job.cfg.get("villa", {}).get("deep", 6.0))
    c = couloir(job)
    turned_deep = ((u1 - u0) - c) / 2 > deep and ((v1 - v0) - c) / 2 <= deep
    if score[1] > score[0] + 1e-6 and not turned_deep:
        return Frame(fr.c[0], fr.c[1], fr.angle + math.pi / 2)
    return fr


def free_band(job, region, F: Frame, at: float, c: float, lo: float, hi: float, floor: int) -> float | None:
    """The couloir's lower line nearest `at` (within `cut_shift`, in [lo, hi]) where both its lines keep
    clear of every opening; None when none does."""
    zones = job.zs([floor])
    reach = max(job.shift, at - lo, hi - at)
    for d in offsets(reach, job.step):
        a = at + d
        if not lo - 1e-9 <= a <= hi + 1e-9:
            continue
        if all(not clashes(partition(region, F, 1, x, job.half), zones) for x in (a, a + c)):
            return a
    return None


def zone_points(job, floor: int) -> tuple:
    """(corner points, zone index of each) of a floor's opening zones, kept on the job."""
    memo = job.__dict__.setdefault("zone_points", {})
    if floor not in memo:
        zs = job.zs([floor])
        pts = [np.asarray(z.exterior.coords)[:, :2] for z in zs]
        memo[floor] = ((np.concatenate(pts), np.concatenate([np.full(len(p), i) for i, p in enumerate(pts)]))
                       if pts else (np.zeros((0, 2)), np.zeros(0, dtype=int)))
    return memo[floor]


def free(job, poly, F: Frame, axis: int, at: float, floor: int, lo=-math.inf, hi=math.inf):
    """`free_cut` on one floor's zones: the nearest place within `cut_shift` whose partition keeps clear;
    a place no zone reaches within half a partition is clear without building its partition (time)."""
    if poly.is_empty:
        return None
    b0, b1 = F.bounds(poly)[axis], F.bounds(poly)[axis + 2]
    pts, ids = zone_points(job, floor)
    if len(pts):
        t = (pts - F.c) @ (F.u if axis == 0 else F.v)
        lo_z = np.full(int(ids.max()) + 1, np.inf)
        hi_z = np.full(int(ids.max()) + 1, -np.inf)
        np.minimum.at(lo_z, ids, t)
        np.maximum.at(hi_z, ids, t)
        lo_z, hi_z = lo_z - job.half - 0.01, hi_z + job.half + 0.01
    zones = None
    convex = poly.area > 0.995 * poly.convex_hull.area     # a line across it meets every zone on its walls
    memo = job.__dict__.setdefault("free_memo", {})     # the variants ask the same cuts again (time)
    seen = memo.setdefault((shapely.to_wkb(poly), *F.c.tolist(), F.angle, axis, floor), {})
    for d in offsets(job.shift, job.step):
        a = at + d
        if not lo <= a <= hi:
            continue
        inside = b0 + 0.05 < a < b1 - 0.05
        hit = bool(len(pts)) and bool(np.any((lo_z <= a) & (a <= hi_z)))
        if inside and not hit:
            return a
        if inside and convex and np.any((lo_z + 0.03 <= a) & (a <= hi_z - 0.03)):
            continue                                    # well inside a zone's span: it clashes
        key = round(a, 6)
        if key not in seen:
            strip = partition(poly, F, axis, a, job.half)
            if strip is None:
                seen[key] = None
            else:
                if zones is None:
                    zones = job.zs([floor])
                near = np.flatnonzero((lo_z <= a) & (a <= hi_z)) if len(pts) else ()   # only zones across
                seen[key] = clashes(strip, [zones[i] for i in near])   # the line can meet it (time, same answer)
        if seen[key] is None and d == 0.0:
            return a
        if seen[key] is False:
            return a
    return None


def cut_region(job, region, entry: Entry, floor: int, cfg: dict, depth: float, wide: float, cell: float,
               hall: bool, turn: bool = False, place: str = "auto", piers=None) -> tuple:
    """(cells, spine) of a region: the hall (or a couloir end, `hall` False), the couloir and untyped room
    cells cut across it every `cell` m. `turn` turns the couloir a quarter, `place` puts it as the rules
    say ("auto") or against the low or high side wall. `spine` holds the couloir's frame and polygons.
    `piers` (band, frame, b0, b1 -> places along u) cuts the bands there instead (`bayplan`: at the piers)."""
    F = couloir_frame(job, region, floor)
    if turn:
        F = Frame(F.c[0], F.c[1], F.angle + math.pi / 2)
    u0, v0, u1, v1 = F.bounds(region)
    du, dv = F.local((entry.x, entry.y))
    n = F.local((entry.x + entry.nx, entry.y + entry.ny)) - np.array([du, dv])
    end = abs(n[0]) >= abs(n[1])
    c, side, door = cfg["couloir"], cfg["side"], need(job)
    span = v1 - v0
    cv0 = None
    if end:
        if span >= 2 * side + c:                        # the middle: rooms of one depth both sides, the hall
            cv0 = v0 + (span - c) / 2                   # reaching from the door to it
            if abs(dv - (cv0 + c / 2)) < wide / 2:
                cv0 = min(max(dv - c / 2, v0 + side), v1 - side - c)
        elif span >= side + c:
            cv0 = v0 if dv - v0 <= v1 - dv else v1 - c
    else:
        low = n[1] > 0
        if span >= 2 * side + c:
            cv0 = v0 + (span - c) / 2
        elif span >= side + c:
            cv0 = v0 if low else v1 - c
    if cv0 is not None and span >= 2 * side + c:      # windows on one side only: that band a room deep
        vs = [float(F.local(p.coords[0])[1]) for p in lights(job, floor) if region.distance(p) < 0.2]
        if vs and (max(vs) < (v0 + v1) / 2 or min(vs) > (v0 + v1) / 2):
            deep = min(max(side, float(job.cfg.get("villa", {}).get("room_depth", 4.5))), span - c - side)
            cv0 = v0 + deep if max(vs) < (v0 + v1) / 2 else v1 - deep - c
    if place != "auto" and span >= side + c:          # a variant: the couloir along a side wall
        cv0 = v0 if place == "low" else v1 - c
    if cv0 is not None and v0 + 1e-6 < cv0 < v1 - c - 1e-6:
        lo, hi = (v0 + side, v1 - side - c) if span >= 2 * side + c else (cv0, cv0)
        got = free_band(job, region, F, cv0, c, lo, hi, floor)
        if got is None:                                 # along a side wall: only one line is a partition
            for flush in sorted((v0, v1 - c), key=lambda f: abs(f - cv0)):
                line = flush + c if flush == v0 else flush
                if not clashes(partition(region, F, 1, line, job.half), job.zs([floor])):
                    got = flush
                    break
        cv0 = got if got is not None else (None if span < 2 * side + c else cv0)
    E = MARGIN
    rect = lambda a, b, p, q: F.rect(min(a, b), min(p, q), max(a, b), max(p, q))   # noqa: E731
    # the hall
    if end:
        sgn = 1.0 if n[0] > 0 else -1.0
        wall = du
        room = (u1 - du) if sgn > 0 else (du - u0)
        d = min(depth, max(room - side, 0.5 * room)) if hall else 0.0
        hv0, hv1 = dv - wide / 2, dv + wide / 2
        bridge = None
        if cv0 is not None and not (hv0 <= cv0 and cv0 + c <= hv1):
            if cv0 >= hv1 - c or cv0 + c <= hv0 + c:    # the couloir lies off the hall: a stub joins them
                bridge = (hv1, cv0 + c) if cv0 >= hv1 - c else (cv0, hv0)
            hv0, hv1 = (min(hv0, cv0), max(hv1, cv0 + c)) if bridge is None else (hv0, hv1)
        hv0, hv1 = max(hv0, v0), min(hv1, v1)
        if hv0 - v0 < SLIVER_GAP:
            hv0 = v0 - E
        if v1 - hv1 < SLIVER_GAP:
            hv1 = v1 + E
        back = wall + sgn * d
        if hall:
            strip = clip(region, rect(wall - sgn * E, back, v0 - E, v1 + E))
            hv0, hv1 = (free_side(job, strip, F, 1, v, floor, keep) for v, keep in ((hv0, v0 - E), (hv1, v1 + E)))
            strip = clip(region, rect(u0 - E, u1 + E, hv0, hv1))
            got = free(job, strip, F, 0, back, floor)
            back = got if got is not None else back
        hall_rect = rect(wall - sgn * E, back, hv0, hv1) if hall else None
        stub = None
        if bridge is not None and hall:
            stub = rect(back - sgn * c, back, *bridge)
        elif bridge is not None and job.interior.__dict__.get("bays_early"):   # a failing house's upper floor:
            stub = rect(wall, wall + sgn * c, *bridge)  # its couloir reaches the landing too (round 10)
        hu = (min(wall, back), max(wall, back))
    else:
        low = n[1] > 0
        wall = dv
        hu0, hu1 = du - wide / 2, du + wide / 2
        if hu0 - u0 < SLIVER_GAP:
            hu0 = u0 - E
        if u1 - hu1 < SLIVER_GAP:
            hu1 = u1 + E
        reach = (cv0 if low else cv0 + c) if cv0 is not None else wall + (1 if low else -1) * min(depth, span - side)
        far = wall + (1 if low else -1) * min(abs(reach - wall), depth if hall else 0.0)
        if hall and cv0 is not None and abs(reach - wall) < c + 0.05:    # the couloir runs along the door wall
            far = wall + (1 if low else -1) * max(min(depth, span - side), abs(reach - wall))
        if hall and abs(reach - far) > 0.05:
            strip = clip(region, rect(hu0, hu1, v0 - E, v1 + E))
            sgn_v = 1 if low else -1
            limit = reach if abs(reach - wall) > abs(far - wall) else far + sgn_v * job.shift
            got = free(job, strip, F, 1, far, floor, *sorted((wall + sgn_v * 0.9, limit)))
            far = got if got is not None else reach
        if hall:
            strip = clip(region, rect(u0 - E, u1 + E, wall - (1 if low else -1) * E, far))
            hu0, hu1 = (free_side(job, strip, F, 0, u, floor, keep) for u, keep in ((hu0, u0 - E), (hu1, u1 + E)))
        hall_rect = rect(hu0, hu1, wall - (1 if low else -1) * E, far) if hall else None
        stub = None
        if cv0 is not None and abs(reach - far) > 0.05:
            stub = rect(du - c / 2, du + c / 2, far, reach)
        hu = (hu0, hu1)
    H = largest_near(clip(region, hall_rect), entry) if hall_rect is not None else None
    S = parts(snap(clip(region, stub))) if stub is not None else []
    if H is not None:
        S = parts(snap(shapely.union_all([shapely.difference(p, H, grid_size=1e-6) for p in S]))) if S else []
    taken = ([H] if H is not None else []) + S
    used = shapely.union_all(taken) if taken else None

    def less(poly):
        poly = shapely.union_all(parts(poly)) if parts(poly) else shapely.Polygon()
        return parts(snap(poly if used is None or poly.is_empty else shapely.difference(poly, used, grid_size=1e-6)))

    cells: list = []
    if H is not None:
        cells.append(Cell(H, "hall", "spine", "hall"))
    bands = []
    if cv0 is None:
        bands = [("A", p) for p in less(region)]
        cor_full = []
    else:
        cor_full = less(clip(region, rect(u0 - E, u1 + E, cv0, cv0 + c)))
        bands += [("A", p) for p in less(clip(region, rect(u0 - E, u1 + E, v0 - E, cv0)))]
        bands += [("B", p) for p in less(clip(region, rect(u0 - E, u1 + E, cv0 + c, v1 + E)))]
    spans = []
    for name, poly in bands:
        b0, _, b1, _ = F.bounds(poly)
        k = max(1, int(round((b1 - b0) / cell))) if piers is None else 1
        cuts_at = court_cuts(job, poly, F, floor, b0, b1)   # no room wraps a court's corner (47.2 round B)
        if piers is not None:
            cuts_at += [x for x in piers(poly, F, b0, b1) if all(abs(x - y) > 1.2 for y in cuts_at)]
        for i in range(1, k):
            at = b0 + i * (b1 - b0) / k
            got = free(job, poly, F, 0, at, floor, b0 + 1.2, b1 - 1.2)
            if got is not None and all(abs(got - x) > 1.2 for x in cuts_at):
                cuts_at.append(got)
        pieces = [poly]
        for at in sorted(cuts_at):
            nxt = []
            for p in pieces:
                lo_, hi_ = cut(p, F, 0, at)
                nxt += lo_ + hi_
            pieces = nxt
        for p in pieces:
            pb = F.bounds(p)
            cells.append(Cell(p, "", name, f"{pb[0]:.2f}"))
            spans.append((pb[0], pb[2]))
    # the couloir reaches every cell's door
    if cor_full:
        h0, h1 = hu
        lo_u, hi_u = h0, h1
        reach = door + wet_need(job)                      # room for a bath room's door beside the room's own
        for a, b in spans:
            if b > h1 + 1e-6:
                hi_u = max(hi_u, min(a + reach, b))
            if a < h0 - 1e-6:
                lo_u = min(lo_u, max(b - reach, a))
        strip = shapely.union_all(cor_full)
        if hi_u < u1 - 0.05:                            # the couloir's ends keep clear of the openings too
            got = free(job, strip, F, 0, hi_u, floor, hi_u - 0.3, u1)
            hi_u = got if got is not None else hi_u
        if lo_u > u0 + 0.05:
            got = free(job, strip, F, 0, lo_u, floor, u0, lo_u + 0.3)
            lo_u = got if got is not None else lo_u
        keep = rect(lo_u, hi_u, cv0 - E, cv0 + c + E)
        on = []
        for p in cor_full:
            inner = parts(snap(clip(p, keep)))
            outer = parts(snap(shapely.difference(p, keep, grid_size=1e-6)))
            on += inner
            cells += [Cell(q, "", "end", "end") for q in outer]
        touching = [p for p in on if H is None or p.distance(H) < 1e-4 or any(p.distance(s) < 1e-4 for s in S)]
        main = max(touching, key=lambda p: p.area) if touching else (max(on, key=lambda p: p.area) if on else None)
        if H is None and on and job.interior.__dict__.get("bays_early"):   # a failing house's upper floor: the
            door_at = Point(entry.x, entry.y)          # couloir is the piece at the landing (round 10)
            main = min(on, key=lambda p: (round(p.distance(door_at), 1), -p.area))
        for p in on:
            cells.append(Cell(p, "couloir" if p is main else "", "spine" if p is main else "end", "couloir"))
    for p in S:
        cells.append(Cell(p, "couloir", "spine", "stub"))
    cells = join_spine(cells)
    if hall and not any(c.type == "hall" and job.fits(c.poly, "hall") for c in cells):
        hall_from_couloir(job, cells, F, entry, floor)
    trim_hall(job, cells, F, entry, floor)
    cells = absorb(cells, job.minimums, SPINE + ("palier", "droj"), job.piece, (), job.largest)
    main = next((c.poly for c in cells if c.type == "couloir"), None)
    spine = {"F": F, "couloir": main, "entry": entry, "hall": next((c.poly for c in cells if c.type == "hall"), None),
             "ways": [c.poly for c in cells if c.type in ("couloir", "hall")]}
    return cells, spine


def courts(job, floor: int) -> list:
    """The courts and light wells of a floor as the storey sees them (its holes: the court walls' inner faces)."""
    st = next((s for s in job.interior.storeys if s.floor == floor), None)
    return [shapely.Polygon(h) for h in st.polygon.interiors] if st is not None else []


def against(job) -> list:
    """The courts of the footprint standing against its outer wall (a narrow maison's, `courts.against_for`),
    grown by their walls: the storey has them as notches, not holes (47.2 round C)."""
    fp = job.outside.b.footprint
    near = job.ext + job.court_wall + 0.05
    out = []
    for h in fp.interiors:
        court = shapely.Polygon(h)
        if court.distance(fp.exterior) < near:
            out.append(court.buffer(job.court_wall, join_style="mitre"))
    return out


def court_cuts(job, poly, F: Frame, floor: int, b0: float, b1: float) -> list:
    """The cuts across a band at the ends of every court or light well it wraps, each nearest the court's edge
    line where its partition keeps clear of the openings, 1.2 m from the band's ends and from one another: the
    piece beside the court then reaches from the street wall to the court wall and no room wraps a corner
    (`[interiors.flats] court_cuts` by layout; 47.2 round B)."""
    out: list = []
    mode = job.cfg.get("flats", {}).get("court_cuts", {}).get(job.interior.layout, False)
    if not mode:
        return out
    for court in (courts(job, floor) if mode is True else against(job)):
        if poly.distance(court) > 0.05:
            continue
        c0, _, c1, _ = F.bounds(court)
        for at in (c0, c1):
            if not b0 + 1.2 < at < b1 - 1.2:
                continue
            got = free(job, poly, F, 0, at, floor, at - 0.6, at + 0.6)
            if got is not None and b0 + 1.2 <= got <= b1 - 1.2 and all(abs(got - x) > 1.2 for x in out):
                out.append(got)
    return out


def trim_hall(job, cells: list, F: Frame, entry: Entry, floor: int) -> None:
    """A hall over its `most` keeps a square of that area round the entrance (its sides moved clear of the
    openings); the rest are free cells."""
    top = float(job.cfg.get("rooms", {}).get("most", {}).get("hall", 20.0))
    h = next((c for c in cells if c.type == "hall"), None)
    if h is None or h.poly.area <= top:
        return
    side = math.sqrt(top) * 0.95
    du, dv = F.local((entry.x, entry.y))
    a, p, b, q = du - side / 2, dv - side / 2, du + side / 2, dv + side / 2
    got = [free(job, h.poly, F, ax, at, floor) for ax, at in ((0, a), (1, p), (0, b), (1, q))]
    a, p, b, q = (g if g is not None else d for g, d in zip(got, (a, p, b, q)))
    keep = parts(clip(h.poly, F.rect(min(a, b), min(p, q), max(a, b), max(p, q))))
    if not keep:
        return
    pt = Point(entry.x, entry.y)
    core = min(keep, key=lambda k: (k.distance(pt), -k.area))
    if not job.fits(core, "hall"):
        return
    rest = parts(solid(shapely.difference(h.poly, core, grid_size=1e-6)))
    h.poly = core
    cells += [Cell(r, "", "end", "hall") for r in rest]


def hall_from_couloir(job, cells: list, F: Frame, entry: Entry, floor: int) -> None:
    """No hall fits at the entrance (a narrow way in beside a stair core): the couloir's first stretch from
    the entrance becomes the hall (the whole couloir when within the hall's most), or the cell at the
    entrance; any hall scrap joins it."""
    p = Point(entry.x, entry.y)
    top = float(job.cfg.get("rooms", {}).get("most", {}).get("hall", 20.0))
    cor = min((c for c in cells if c.type == "couloir" or (not c.type and c.poly.area <= top)),
              key=lambda c: (round(c.poly.distance(p), 2), c.type != "couloir"), default=None)
    if cor is None or (cor.poly.distance(p) > 0.3 and min(c.poly.distance(p) for c in cells) < 0.3):
        return                                            # (a door on a neck with no floor: the nearest cell)
    for h in [c for c in cells if c.type == "hall"]:
        merged = union(cor.poly, h.poly) if h is not cor else None
        if merged is not None:
            cor.poly = merged
            cells.remove(h)
        elif h is not cor:
            h.type = ""                                   # a hall scrap off the way in: a cell like any other
    if cor.poly.area > top:
        a, _, b, _ = F.bounds(cor.poly)
        eu = F.local((entry.x, entry.y))[0]
        at = eu + 3.0 if abs(eu - a) < abs(eu - b) else eu - 3.0
        pos = free(job, cor.poly, F, 0, at, floor, a + 1.5, b - 1.5)
        if pos is None:
            return
        lo, hi = cut(cor.poly, F, 0, pos)
        if len(lo) != 1 or len(hi) != 1:
            return
        mine, rest = (lo[0], hi[0]) if lo[0].distance(p) < hi[0].distance(p) else (hi[0], lo[0])
        cor.poly = rest
        cells.append(Cell(mine, "hall", "spine", "hall"))
        return
    cor.type = "hall"


def free_side(job, strip, F: Frame, axis: int, at: float, floor: int, wall: float) -> float:
    """A hall side moved clear of the openings (the door among them); the wall when it cannot be."""
    if abs(at - wall) < 1e-9 or strip.is_empty:
        return at
    got = free(job, strip, F, axis, at, floor)
    return wall if got is None else got


def largest_near(geom, entry: Entry):
    """The part of a geometry holding the entry point (else the largest)."""
    got = parts(snap(geom))
    if not got:
        return None
    p = Point(entry.x, entry.y)
    return min(got, key=lambda q: (q.distance(p) > 0.05, -q.area))


def join_spine(cells: list) -> list:
    """Couloir pieces (the stub and the couloir) become one couloir; ends join their longest neighbour."""
    cors = [c for c in cells if c.type == "couloir"]
    while len(cors) > 1:
        a, b = cors[0], cors[1]
        merged = union(a.poly, b.poly) if shared(a.poly, b.poly) > 1e-3 else None
        if merged is None:
            b.type = ""
            cors = cors[:1] + cors[2:]
            continue
        a.poly = merged
        cells = [c for c in cells if c is not b]
        cors = [c for c in cells if c.type == "couloir"]
    for c in [c for c in cells if c.band == "end"]:
        best = max((o for o in cells if o is not c and o.band != "end"),
                   key=lambda o: (shared(c.poly, o.poly), o.type == ""), default=None)
        if best is None or shared(c.poly, best.poly) < 1e-3:
            continue
        merged = union(best.poly, c.poly)
        if merged is not None:
            best.poly = merged
            cells = [x for x in cells if x is not c]
    return cells


# --- the program ------------------------------------------------------------------------------------
def assign(job, cells: list, spine: dict, program: list, floor: int, entry: Entry) -> list:
    """Room types for the untyped cells (see the module doc); returns the program items no cell holds."""
    sun = lights(job, floor)
    balconies = lights(job, floor, ("balcony",))
    door = Point(entry.x, entry.y)
    free_cells = [c for c in cells if not c.type]
    light = {id(c): lit(c.poly, sun) for c in free_cells}
    most = job.cfg.get("rooms", {}).get("most", {})
    missing = []
    flat = job.interior.layout in ("colonial", "slab")

    def fits(c, t):
        return job.fits(c.poly, t)

    def take(c, t):
        c.type = t
        free_cells.remove(c)

    salon = None
    for t in program:
        if t == "chambre*":
            for c in sorted([c for c in free_cells if light[id(c)] and fits(c, "chambre")], key=lambda c: -c.poly.area):
                take(c, "chambre")
            continue
        if t == "makhzen*":                             # a floor of stores (a colonial floor 0 with no window)
            for c in list(free_cells):
                take(c, "makhzen")
            continue
        cands = candidates(job, t, cells, free_cells, light, most)
        if t in ("salon", "cuisine") and cands and not any(light[id(c)] for c in cands):
            got = divide(job, spine, cells, t, floor, light, windowed=True)
            if got is not None:                         # the windowed half of a big room, before a blind cell
                if t == "salon":
                    salon = got
                continue
        if t == "salon":
            key = lambda c: (not lit(c.poly, balconies), -c.poly.area, c.poly.distance(door))   # noqa: E731
        elif t == "salle_a_manger":
            key = lambda c: (-(shared(c.poly, salon.poly) if salon else 0.0), -c.poly.area)   # noqa: E731
        elif t == "cuisine":
            key = lambda c: (lit(c.poly, balconies), c.poly.area > job.largest.get("cuisine", 99.0),   # noqa: E731
                             -round(c.poly.distance(door), 1), c.poly.area)
        elif t == "chambre":
            key = lambda c: -c.poly.area   # noqa: E731
        else:
            key = lambda c: (light[id(c)], c.poly.area > job.largest.get(t, 99.0), c.poly.area)   # noqa: E731
        if cands:
            c = min(cands, key=key)
            if t == "salle_a_manger" and flat and not fits(c, t):
                continue                                # a flat's dining room only where a cell holds it
            take(c, t)
            if t == "salon":
                salon = c
            if t in WET and c.poly.area > job.largest.get(t, 99.0) and not trim_wet(job, spine, c, cells, floor):
                c.type = ""                                     # too big to be one: carve it instead
                free_cells.append(c)
                if carve_wet(job, spine, cells, t, floor):
                    continue
                missing.append(t)
                continue
            if t == "cuisine" and c.poly.area > job.largest.get(t, 99.0):
                rest = split_off(job, spine, c, floor, job.largest[t] * 0.8)
                if rest is not None:
                    cells.append(rest)
                    free_cells.append(rest)
                    light[id(rest)] = lit(rest.poly, sun)
            continue
        if t in WET and carve_wet(job, spine, cells, t, floor):
            continue
        if t in LIVING:
            got = divide(job, spine, cells, t, floor, light)
            if got is not None:                         # a big room halved: both keep a door on a way in
                if t == "salon":
                    salon = got
                continue
        if not (t == "salle_a_manger" and flat):       # `rooms.check` asks no dining room of a flat
            missing.append(t)
    leftovers(job, cells, most, light, program)
    for c in [c for c in cells if c.type == "cuisine" and c.poly.area > job.largest.get("cuisine", 99.0)]:
        rest = split_off(job, spine, c, floor, job.largest["cuisine"] * 0.8)
        if rest is not None:                            # a kitchen grown past its largest gives its end away
            cells.append(rest)
            leftovers(job, cells, most, light, program)
    return missing


def strip(poly, wide: float) -> float:
    """m2 of `poly` in parts narrower than `wide` (what an opening by half of `wide` leaves out)."""
    h = wide / 2
    return float(poly.difference(poly.buffer(-h, join_style="mitre").buffer(h, join_style="mitre")).area)


def halve(job, spine: dict, cells: list, c, floor: int):
    """A flat's chambre, salle a manger or salon over its `most` (a hall no family would live in) cut in two:
    the room, keeping its minimum and a door's length on a way in, and a new chambre with a door's length on
    a way in or on the room (en enfilade, as in old town flats), both windowed when the room was (47.1
    flats round 3); the new cell, or None when no cut keeps that."""
    F = spine["F"]
    ways = spine.get("ways") or []
    sun = lights(job, floor)
    least = job.minimums.get("chambre", (8.0, 2.4))
    windowed = lit(c.poly, sun)
    wide, most_strip = (float(v) for v in job.cfg.get("flats", {}).get("strip", (1.6, 3.0)))
    for axis in (0, 1):
        a, p, b, q = F.bounds(c.poly)
        lo, hi = (a, b) if axis == 0 else (p, q)
        for frac in (0.5, 0.45, 0.55, 0.4, 0.6, 0.35, 0.65):
            pos = free(job, c.poly, F, axis, lo + frac * (hi - lo), floor, lo + least[1], hi - least[1])
            if pos is None:
                continue
            one, two = cut(c.poly, F, axis, pos)
            if len(one) != 1 or len(two) != 1:
                continue
            for mine, rest in ((one[0], two[0]), (two[0], one[0])):
                if not (job.fits(mine, "chambre") and job.fits(rest, c.type)):
                    continue
                if windowed and not (lit(mine, sun) and lit(rest, sun)):
                    continue
                if any(strip(x, wide) > most_strip for x in (mine, rest)):
                    continue                            # no corridor-like arm a room's area hides
                on = [max((shared(x, w) for w in ways), default=0.0) >= need(job) for x in (mine, rest)]
                if not on[1] or not on[0] and shared(mine, rest) < need(job):
                    continue                            # the far chambre entered through the near room (enfilade)
                c.poly = rest
                new = Cell(mine, "chambre", c.band, c.part)
                cells.append(new)
                return new
    return None


def candidates(job, t: str, cells: list, free_cells: list, light: dict, most: dict) -> list:
    """The cells that may hold room type t, best kind first: a sdb or wc any cell up to 1.6 x its largest;
    the salon, salle a manger and cuisine a windowed cell, two windowed cells joined, a windowed cell of
    their area, then a blind one (one-sided lots), then two cells joined; a chambre a windowed cell, a blind
    one, then two cells joined. Rooms over their `most` only when nothing else holds them."""
    top = float(most.get(t, 1e9))

    def keep(cs):
        under = [c for c in cs if c.poly.area <= top]
        return under or cs

    fits = [c for c in free_cells if job.fits(c.poly, t)]
    if t in WET:
        return [c for c in fits if c.poly.area <= job.largest.get(t, 99.0) * 1.6]
    if t not in LIVING:
        return fits
    windowed = keep([c for c in fits if light[id(c)]])
    if windowed:
        return windowed
    if t != "chambre":
        pair = pair_up(job, cells, free_cells, light, t, True, top)
        if pair is not None:
            return [pair]
        odd = keep([c for c in free_cells if light[id(c)] and c.poly.area >= job.minimums.get(t, (0, 0))[0]])
        if odd:
            return odd
    if fits:
        return keep(fits)
    pair = pair_up(job, cells, free_cells, light, t, False, top)
    return [pair] if pair is not None else []


def divide(job, spine: dict, cells: list, t: str, floor: int, light: dict, windowed: bool = False):
    """No cell holds room type t: the largest room (or free cell) that can be cut in two gives it a part (the
    windowed part when t wants light, never the windowed part of a salon or cuisine), both parts keeping
    their minimum and a door's length on a way in; the new cell, or None."""
    F = spine["F"]
    ways = spine.get("ways") or []
    sun = lights(job, floor)
    least_t = job.minimums.get(t, (8.0, 2.4))
    hosts = sorted([c for c in cells if (not c.type or c.type in ("chambre", "salle_a_manger", "salon", "cuisine"))
                    and c.poly.area >= least_t[0] + job.minimums.get(c.type or "chambre", (8.0, 2.4))[0]],
                   key=lambda c: (c.type in ("salon", "cuisine"), -c.poly.area))
    for host in hosts[:4]:                              # the largest rooms only (time)
        keep_type = host.type or "chambre"
        for axis in (0, 1):
            a, p, b, q = F.bounds(host.poly)
            lo, hi = (a, b) if axis == 0 else (p, q)
            for frac in (0.5, 0.45, 0.55, 0.4, 0.6, 0.35, 0.65):
                pos = free(job, host.poly, F, axis, lo + frac * (hi - lo), floor, lo + least_t[1], hi - least_t[1])
                if pos is None:
                    continue
                one, two = cut(host.poly, F, axis, pos)
                if len(one) != 1 or len(two) != 1:
                    continue
                for mine, rest in ((one[0], two[0]), (two[0], one[0])):
                    if not job.fits(mine, t) or not job.fits(rest, keep_type):
                        continue
                    if windowed and not lit(mine, sun):
                        continue
                    if keep_type in ("salon", "cuisine") and lit(host.poly, sun) and not lit(rest, sun):
                        continue                    # the host keeps its window
                    if any(max((shared(x, w) for w in ways), default=0.0) < need(job) for x in (mine, rest)):
                        continue
                    host.poly = rest
                    c = Cell(mine, t, host.band, host.part)
                    cells.append(c)
                    light[id(c)] = lit(mine, sun)
                    return c
    return None


def pair_up(job, cells: list, free_cells: list, light: dict, t: str, windowed: bool = True, top: float = 1e9):
    """Two free cells of one band side by side (one windowed when `windowed`) joined into one that holds room
    type t within `top` m2; the joined cell, or None."""
    best = None
    for i, a in enumerate(free_cells):
        for b in free_cells[i + 1:]:
            if (a.band != b.band or (windowed and not (light[id(a)] or light[id(b)]))
                    or shared(a.poly, b.poly) < 1.0):
                continue
            merged = union(a.poly, b.poly)
            if merged is None or not job.fits(merged, t) or merged.area > top:
                continue
            if best is None or merged.area < best[0].area:
                best = (merged, a, b)
    if best is None:
        return None
    merged, a, b = best
    a.poly = merged
    light[id(a)] = light[id(a)] or light[id(b)]
    free_cells.remove(b)
    cells.remove(b)
    return a


def split_off(job, spine: dict, c, floor: int, area: float):
    """A room cut across the couloir to about `area` m2 (the end nearer the entrance kept); the rest a
    free cell, or None when no cut keeps both at their minimums."""
    F = spine["F"]
    a, p, b, q = F.bounds(c.poly)
    w = area / max(q - p, 0.5)
    for at in (a + w, b - w):
        pos = free(job, c.poly, F, 0, at, floor, a + job.minimums.get(c.type, (0, 1.7))[1], b - 1.2)
        if pos is None:
            continue
        lo, hi = cut(c.poly, F, 0, pos)
        mine, rest = (lo, hi) if at < (a + b) / 2 else (hi, lo)
        if len(mine) == 1 and len(rest) == 1 and job.fits(mine[0], c.type) and rest[0].area > 2.0:
            c.poly = mine[0]
            return Cell(rest[0], "", c.band, c.part)
    return None


def couloir_side(spine: dict, poly) -> float | None:
    """+1 when the couloir lies above the cell in v, -1 below, None when the cell does not touch it."""
    F = spine["F"]
    ways = [w for w in (spine["couloir"], spine["hall"]) if w is not None and poly.distance(w) < 1e-4]
    if not ways:
        return None
    cor = max(ways, key=lambda w: shared(poly, w))
    return 1.0 if F.local(cor.centroid.coords[0])[1] > F.local(poly.centroid.coords[0])[1] else -1.0


def carve_wet(job, spine: dict, cells: list, t: str, floor: int) -> bool:
    """A sdb or wc carved from a room beside the couloir or hall (the sdb for a wc first, else the largest
    room that keeps its minimum): a rectangle against the way in, slid along it until its walls keep
    clear and it opens on the way; the room wraps round it."""
    F = spine["F"]
    ways = spine.get("ways") or [w for w in (spine["couloir"], spine["hall"]) if w is not None]
    hosts = sorted([c for c in cells if c.type in ("sdb", "chambre", "salle_a_manger", "salon", "cuisine")],
                   key=lambda c: (c.type != "sdb" if t == "wc" else c.type == "salon", -c.poly.area))
    least_a, least_w = job.minimums.get(t, (1.2, 0.8))
    big = job.largest.get(t, 6.0)
    top = float(job.interior.rules.get("most", {}).get(t, 1e9))
    w = max(least_w + 0.2, wet_need(job) + 0.05, 1.2 if t == "wc" else 1.9)
    deep = max(big * 0.85 / w, least_w + 0.1)
    zones = job.zs([floor])
    door = wet_need(job)
    for host in hosts:
        for way in ways:
            if shared(host.poly, way) < door:
                continue
            for piece_way in contact(host.poly, way):
                got = slide_wet(job, F, host, way, piece_way, t, w, deep, top, door, zones, ways)
                if got is not None:
                    wet, host.poly = unwrap(job, *got)
                    cells.append(Cell(wet, t, host.band, host.part))
                    return True
    hall = next((c for c in cells if c.type == "hall"), None)
    if hall is not None:                                # off the hall, in a corner away from the door
        got = hall_corner(job, F, hall, w, max(least_a / w, least_w) + 0.3, door, zones, spine.get("entry"), t)
        if got is not None:
            wet, hall.poly = unwrap(job, *got)
            cells.append(Cell(wet, t, "spine", "wc"))
            return True
    return False


def unwrap(job, wet, rest) -> tuple:
    """(wet room, host) with the host's hair-thin arms round the carved room (narrower than a partition and
    0.1 m: walls would swallow them and the doors on them) given to the wet room (47.1/48.1)."""
    from ..city.geo import polygons
    e = job.half + 0.05
    core = parts(snap(rest.buffer(-e, join_style="mitre").buffer(e, join_style="mitre").intersection(rest)))
    if not core:
        return despike(wet), despike(rest)
    body = max(core, key=lambda p: p.area)
    for arm in sorted(polygons(shapely.difference(rest, body, grid_size=1e-6)), key=lambda p: (-p.area, p.centroid.x)):
        if arm.area < 1e-8 or shared(arm, wet) < 0.05:
            continue
        grown, left = union(wet, arm), parts(shapely.difference(rest, arm, grid_size=1e-6))
        if grown is not None and len(left) == 1:
            wet, rest = grown, left[0]
    return despike(wet), despike(rest)


def hall_corner(job, F: Frame, hall, w: float, d: float, door: float, zones: list, entry, t: str = "wc"):
    """(wc, the hall's rest) of a w x d rectangle in a corner of the hall that keeps the hall at its minimum
    with the entrance in it and the wc opening on it; None."""
    u0, v0, u1, v1 = F.bounds(hall.poly)
    for du, dv in ((w, d), (d, w)):
        for cu, cv in ((u0, v0), (u1, v0), (u0, v1), (u1, v1)):
            a, b = (cu, cu + du) if cu == u0 else (cu - du, cu)
            p, q = (cv, cv + dv) if cv == v0 else (cv - dv, cv)
            piece = parts(clip(hall.poly, F.rect(a, p, b, q)))
            if len(piece) != 1 or not job.fits(piece[0], t) or piece[0].area > job.largest.get(t, 4.0):
                continue
            rest = parts(solid(shapely.difference(hall.poly, piece[0], grid_size=1e-6)))
            if len(rest) != 1 or not job.fits(rest[0], "hall") or shared(piece[0], rest[0]) < door:
                continue
            if entry is not None and rest[0].distance(Point(entry.x, entry.y)) > 0.05:
                continue
            if S.walls_clear(piece[0], hall.poly, zones, job.half):
                return piece[0], rest[0]
    return None


def slide_wet(job, F: Frame, host, way, piece_way, t: str, w: float, deep: float, top: float, door: float,
              zones: list, ways=()):
    """(wet room, the host's rest) of a rectangle slid along one straight contact with the way in (along
    either axis); None when no place keeps the rules."""
    uv = F.local(np.asarray(piece_way))
    ax = 0 if abs(uv[0, 0] - uv[1, 0]) >= abs(uv[0, 1] - uv[1, 1]) else 1     # the contact runs along u or v
    if abs(uv[0, 1 - ax] - uv[1, 1 - ax]) > 0.05 or abs(uv[0, ax] - uv[1, ax]) < door:
        return None
    ca, cb, vc = float(uv[:, ax].min()), float(uv[:, ax].max()), float(uv[:, 1 - ax].mean())
    up = 1.0 if F.local(host.poly.representative_point().coords[0])[1 - ax] > vc else -1.0
    xs = list(np.arange(ca, cb - w + 1e-9, 0.15)) + [cb - w]
    for x0 in sorted(xs, key=lambda x: min(abs(x - ca), abs(cb - w - x))):
        lo_v, hi_v = min(vc, vc + up * deep), max(vc, vc + up * deep)
        rect = F.rect(x0, lo_v, x0 + w, hi_v) if ax == 0 else F.rect(lo_v, x0, hi_v, x0 + w)
        piece = parts(clip(host.poly, rect))
        if len(piece) != 1 or not job.fits(piece[0], t) or piece[0].area > top:
            continue
        rest = parts(solid(shapely.difference(host.poly, piece[0], grid_size=1e-6)))
        if (len(rest) != 1 or not job.fits(rest[0], host.type) or shared(piece[0], way) < door
                or max(shared(rest[0], x) for x in (ways or [way])) < need(job)):
            continue
        if S.walls_clear(piece[0], host.poly, zones, job.half):
            return piece[0], rest[0]
    return None


def trim_wet(job, spine: dict, c, cells: list, floor: int) -> bool:
    """A sdb or wc over its `largest`: first narrowed across the couloir, then cut back to the part by the
    couloir; the pieces cut off are free cells (they join a neighbour or become rooms). False when it
    stays over its `most`."""
    F = spine["F"]
    big = job.largest.get(c.type, 99.0)
    least_w = job.minimums.get(c.type, (1.0, 0.8))[1]
    a, p, b, q = F.bounds(c.poly)
    if c.poly.area > big and b - a > 2.6:
        rest = split_off(job, spine, c, floor, max(least_w + 0.4, 2.0) * (q - p))
        if rest is not None:
            cells.append(rest)
    sgn = couloir_side(spine, c.poly)
    if c.poly.area > big and sgn is not None:
        a, p, b, q = F.bounds(c.poly)
        deep = max(big * 0.85 / max(b - a, 0.1), least_w + 0.1)
        at = q - deep if sgn > 0 else p + deep
        pos = free(job, c.poly, F, 1, at, floor, p + least_w, q - 0.9)
        if pos is not None:
            lo, hi = cut(c.poly, F, 1, pos)
            mine, rest = (hi, lo) if sgn > 0 else (lo, hi)
            if len(mine) == 1 and job.fits(mine[0], c.type):
                c.poly = mine[0]
                cells += [Cell(piece, "", c.band, c.part) for piece in rest]
    return c.poly.area <= float(job.interior.rules.get("most", {}).get(c.type, 1e9))


def leftovers(job, cells: list, most: dict, light: dict | None = None, program=()) -> None:
    """Untyped cells: each joins the room it shares most with when that keeps the room within its
    `largest` and `most` (a room-sized one only when blind in a lit home, `[interiors.flats] blind_join`,
    47.2 round B); else it is a room itself (a windowed one a chambre, a blind one on a floor with a
    salon its salle a manger, else a chambre); a sliver joins the couloir or hall."""
    light = light or {}
    living = "salon" in program
    join = job.cfg.get("flats", {}).get("blind_join", {}).get(job.interior.layout, False)
    dark = join and bool(light) and any(light.values())   # a lit home's blind cells join rooms (47.2 round B)
    wide, thin = (float(v) for v in job.cfg.get("flats", {}).get("strip", (1.6, 3.0)))
    for _ in range(len(cells) + 1):
        todo = sorted([c for c in cells if not c.type], key=lambda c: c.poly.area)
        if not todo:
            return
        c = todo[0]
        ranked = sorted(((shared(c.poly, o.poly), o) for o in cells if o is not c and o.type and o.type != "palier"),
                        key=lambda t: (t[1].type in SPINE, -t[0]))
        room = job.fits(c.poly, "chambre")
        unlit = room and dark and not light.get(id(c))   # a blind one may join a room or way within its most
        done = False
        for capped, ways in ((True, False), (True, True), (False, False), (False, True)):
            if done or (room and (not capped or (ways and not unlit))):   # a room-sized cell stays a room
                break
            for s, o in ranked:                         # a scrap grows a room past its most only as a last resort
                grown = o.poly.area + c.poly.area
                if s < 1e-3 or grown > job.largest.get(o.type, 1e9) or (capped and grown > float(most.get(o.type, 1e9))):
                    continue
                if (o.type in SPINE) != ways or (ways and grown > float(most.get(o.type, 1e9))):
                    continue                            # a couloir or hall never grows past its most
                merged = union(o.poly, c.poly)
                if merged is not None and unlit and o.type in LIVING and strip(merged, wide) > thin:
                    continue                            # no L strip for a blind cell (the dark-room guard)
                if merged is not None:
                    o.poly = merged
                    done = True
                    break
        if done:
            cells.remove(c)
            continue
        dining = any(o.type == "salle_a_manger" for o in cells)
        if light.get(id(c)) or not living or dining:
            c.type = "chambre"
        else:
            c.type = "salle_a_manger" if job.fits(c.poly, "salle_a_manger") else "chambre"


# --- rooms and doors --------------------------------------------------------------------------------
def doors(job, rooms: list) -> None:
    """The doors of one home's rooms: the hall and the couloir by an arch, every other room into the
    couloir or the hall (the longer shared piece first)."""
    interior = job.interior
    hall = next((r for r in rooms if r.type == "hall"), None)
    ways = [r for r in rooms if r.type in ("hall", "couloir")]
    for i, a in enumerate(ways):                      # the hall and the couloirs open into each other
        for b in ways[i + 1:]:
            if shared(a.polygon, b.polygon) > 0.8:
                arch(job, a, b)
    for r in sorted(rooms, key=lambda r: r.id):
        if r.type in SPINE or r.type in ("droj",):
            continue
        done = False
        for w in sorted(ways, key=lambda w: -max((math.dist(*p) for p in R.pieces_between(interior, r, w)), default=0)):
            width = 1.4 if r.type == "salon" and w is hall else job.door
            if R.place(interior, r, w, "inner", width, job.door_height, clear=inner(job), deep=deep(job)) is not None:
                done = True
                break
            if width != job.door and R.place(interior, r, w, "inner", job.door, job.door_height,
                                             clear=inner(job), deep=deep(job)) is not None:
                done = True
                break
        if not done and r.type in WET:                # a bath room's narrow door
            rules = interior.rules
            for d, w in [(d, w) for d in (deep(job), 0.0) for w in ways]:   # a hair arm only when nothing else
                if R.place(interior, r, w, "inner", rules.get("narrow", 0.7), job.door_height,
                           clear=rules.get("narrow_clear", 0.05), deep=d) is not None:
                    break


ARCH = 0.8      # m: the shortest open passage between two ways


def arch(job, a, b) -> bool:
    """An open passage between two rooms on their longest shared piece (at most 2 m); False when no piece
    is 0.8 m long."""
    pieces = sorted(R.pieces_between(job.interior, a, b), key=lambda p: -math.dist(*p))
    if not pieces or math.dist(*pieces[0]) - 0.02 < ARCH:
        return False
    piece = pieces[0]
    w = min(math.dist(*piece) - 0.02, 2.0)
    return R.place(job.interior, a, b, "arch", w, job.door_height, at=tuple(np.add(piece[0], piece[1]) / 2),
                   clear=-job.half) is not None


def open_way(job, way, rooms: list) -> None:
    """A stair's palier opens into a home: an arch to every hall or couloir it touches, else a door into the
    room it shares most with."""
    done = False
    for r in sorted([r for r in rooms if r.type in ("hall", "couloir")], key=lambda r: -shared(way.polygon, r.polygon)):
        done = arch(job, way, r) or done
    if done:
        return
    for r in sorted([r for r in rooms if r is not way and r.type not in WET],
                    key=lambda r: (-shared(way.polygon, r.polygon), r.id)):
        if R.place(job.interior, way, r, "inner", job.door, job.door_height, clear=inner(job)) is not None:
            return


def nooks(job, rooms: list, palier=None) -> list:
    """Rooms under their minimum (a nook between the stair box and a wall, a scrap of a cut) join the
    stair's palier when beside it, else the room of their home they share most with."""
    interior = job.interior
    for r in list(rooms):
        least = job.minimums.get(r.type, (0.0, 0.0))[0]
        if r.type == "couloir" and r.polygon.area < job.minimums.get("hall", (2.5, 1.1))[0]:
            if _scrap_way(interior, r, rooms, palier):    # a couloir scrap between the hall and the palier
                continue
        if r.type in SPINE or r.type in WET or job.fits(r.polygon, r.type) or r.polygon.area >= least:
            continue                                      # only a scrap under its type's least area
        hosts = ([palier] if palier is not None and shared(r.polygon, palier.polygon) >= 1.0 else [])
        hosts += sorted([o for o in rooms if o is not r and o.type not in WET and shared(r.polygon, o.polygon) > 0.3],
                        key=lambda o: (o.type in SPINE, -shared(r.polygon, o.polygon)))
        for host in hosts:
            merged = union(host.polygon, r.polygon)
            if merged is not None:
                host.polygon = merged
                interior.rooms.remove(r)
                rooms.remove(r)
                break
    return rooms


# --- shared by villas, maisons and flats ---------------------------------------------------------------
def _scrap_way(interior, r, rooms: list, palier) -> bool:
    """A couloir under the hall's least area joins the hall or palier it shares most with (no arch then
    squeezes into it, 47.1 round 7); True when it did."""
    ways = [o for o in rooms if o is not r and o.type in ("hall", "couloir")] + ([palier] if palier is not None else [])
    for host in sorted(ways, key=lambda o: (-shared(r.polygon, o.polygon), o.id)):
        merged = union(host.polygon, r.polygon) if shared(r.polygon, host.polygon) > 0.3 else None
        if merged is not None:
            host.polygon = merged
            interior.rooms.remove(r)
            rooms.remove(r)
            return True
    return False


def modern_job(interior, outside, style: dict):
    """A `dar.Job` with the services' `largest` of modern homes (`[interiors.villa] largest`)."""
    from .dar import Job
    job = Job(interior, outside, style)
    job.largest = {k: float(v) for k, v in job.cfg.get("villa", {}).get("largest", {}).items()}
    interior.rules["largest"] = dict(job.largest)
    flats = job.cfg.get("flats", {})
    interior.rules["inner_clear"] = float(job.cfg.get("openings", {}).get("inner_clear", job.clear))
    interior.rules["min_flat"] = float(flats.get("min_flat", 40.0))
    interior.rules["dining_area"] = float(job.cfg.get("villa", {}).get("dining_area", 110.0))
    interior.rules["wc_area"] = float(flats.get("wc_area", 70.0))
    interior.rules["flat_bays"] = bool(flats.get("by_windows", {}).get(interior.layout, False))
    interior.rules["flat_types"] = [(t, float(u)) for t, u in flats.get("types", [["S+1", 60.0], ["S+2", 100.0], ["S+3", 1e9]])]
    return job


def door_entry(job, spot=None) -> Entry | None:
    """The entry of a facade door (`DoorSpot`): the point on the wall's inner face, pointing in."""
    spot = spot or job.spot
    if spot is None:
        return None
    return Entry(spot.x - spot.nx * job.ext, spot.y - spot.ny * job.ext, -spot.nx, -spot.ny)


def door_frame(entry: Entry) -> Frame:
    """A frame at an entry: u along its wall, v pointing in."""
    return Frame(entry.x, entry.y, math.atan2(entry.ny, entry.nx) - math.pi / 2)


def u_numbers(job, core: bool, narrow: bool = False) -> dict:
    """The U box's numbers: modern width (`u_width`), a core's (`core_width`), or the narrow fallback."""
    cfg = job.stairs
    if narrow:
        w, tread = float(cfg.get("u_narrow", 0.8)), float(cfg.get("u_narrow_tread", 0.24))
    else:
        w, tread = float(cfg.get("core_width" if core else "u_width", 1.1 if core else 1.0)), float(cfg.get("u_tread", 0.28))
    return S.u_size(job.interior.fh, cfg, w, tread, need(job))


def box_fits(job, box, floors: list) -> bool:
    """True when a stair box lies inside every storey of `floors` and its walls keep clear of every opening."""
    for f in floors:
        st = job.interior.storeys[f].polygon
        if box.difference(st).area > 1e-4 or not S.walls_clear(box, st, job.zs([f]), job.half):
            return False
    return True


def roof_newel(job, region, on_walls: bool = False):
    """The newel cell from the top floor to the roof, under the roof's stair room (SPEC 6c `newel`): the
    largest square inside the stair room's square that keeps the rule; None without a stair room or when
    none fits (then a ladder rises into the stair room, a warning); `on_walls`: see `stairs.under_stair_room`."""
    if job.roof is None or job.roof.stair is None:
        return None
    sq = S.under_stair_room(job.roof.stair, region, job.zs([job.interior.floors - 1]), job.half,
                            float(job.stairs.get("newel_min", 1.9)), on_walls)
    if sq is None:
        job.interior.warnings.append("the roof stair does not fit under the stair room: a ladder rises into it")
        job.roof_ladder = True
    return sq


def newel_rooms(job, square, droj, door_to: str = "") -> None:
    """The `Stair` of the roof newel (top floor to the roof) and its door into the room it touches most
    (a core's palier first). `door_to` (a room type, flats: "palier"): the door on a side the square shares
    with such a room when one does, not on a side that meets it only at a corner (47.2 flats round G)."""
    from shapely.geometry import LineString
    interior = job.interior
    top = interior.floors - 1
    others = [r for r in interior.rooms if r.floor == top and r is not droj]
    floor = shapely.union_all([r.polygon for r in others]) if others else None
    toward = job.roof.door[2] if job.roof is not None and job.roof.door is not None else None
    door = None
    if door_to and floor is not None:
        to = sorted((r for r in others if r.type == door_to), key=lambda r: (-shared(droj.polygon, r.polygon), r.id))
        door = S.door_side(square, [floor, to[0].polygon], toward) if to else None
    door = door or (S.door_side(square, [floor], toward) if floor is not None else None) or S.door_side(square, [square.buffer(5)])
    stair = S.newel(square, door, interior.floors, interior.fh, job.stairs)
    stair.floor = top
    stair.rooms = [droj.id]
    interior.stairs.append(stair)
    line = S.door_line(square, door)
    ranked = sorted(others, key=lambda r: (r.type != "palier", -sum(math.dist(*p) for p in R.pieces_between(interior, droj, r)
                                                                   if LineString(line).distance(Point(*np.add(p[0], p[1]) / 2)) < 0.05),
                                           -shared(droj.polygon, r.polygon), r.id))
    for r in ranked:
        if R.place(interior, droj, r, "inner", job.door, job.door_height, on=line, clear=inner(job)) is not None:
            droj.unit = "common" if r.unit == "common" else r.unit
            return
    for r in sorted(others, key=lambda r: (r.type != "palier", -shared(droj.polygon, r.polygon), r.id)):
        if R.place(interior, droj, r, "inner", job.door, job.door_height, clear=inner(job)) is not None:
            droj.unit = r.unit
            return


def finish(job, roof_unit: str = "home") -> None:
    """Facade openings in their rooms, the roof (stah, stair room, menzah), entry steps, the doors still
    missing, lit rooms, ids as positions."""
    from . import dar as D
    interior = job.interior
    R.repair(interior, job.zones)
    R.assign(interior)
    n = len(interior.rooms)
    D.roof(job, interior.floors)
    for r in interior.rooms[n:]:
        r.unit = roof_unit
    D.entry_steps(job)
    R.connect(interior)
    for o in interior.openings:
        if o.kind in R.FACADE and o.piece:
            o.rooms = (-1, -1)
    interior.warnings = [w for w in interior.warnings if "no floor behind" not in w]
    R.assign(interior)
    for r in interior.rooms:
        r.lit = any(o.lit for o in interior.openings if o.rooms[0] == r.id and o.kind in ("window", "balcony"))
    R.renumber(interior)


def add_rooms(job, cells: list, floor: int, unit: str) -> list:
    """Rooms from the typed cells of one home's floor."""
    from .model import Room
    interior = job.interior
    st = interior.storeys[floor]
    out = []
    for c in cells:
        room = Room(R.next_id(interior), floor, c.type or "chambre", despike(c.poly), st.z, st.height, unit=unit)
        interior.rooms.append(room)
        out.append(room)
    return out
