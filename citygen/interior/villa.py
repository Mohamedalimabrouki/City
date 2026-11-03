"""Villas and the houses of the new districts (SPEC 6c "Villas and houses of the new districts").

Floor 0: a hall at the main door with the U stair beside it (when there are more floors), a couloir, the
salon, the salle a manger (a villa whose floor 0 is over `dining_area`), the cuisine and a wc. Upper floors:
the palier round the stair, a couloir, chambres on the facades and a salle de bain. A single storey also
holds the chambres. The rooms come from the spine engine (`spine.py`); the programs are style lists.
"""
from __future__ import annotations

import numpy as np
import shapely

from . import dar as D
from . import rooms as R
from . import spine as P
from . import stairs as S
from .cuts import parts, snap

GROUND = {"villa": ["salon", "salle_a_manger", "cuisine", "wc", "chambre*"],
          "maison": ["salon", "cuisine", "wc", "chambre*"]}
UPPER = ["chambre", "sdb", "chambre*"]
SINGLE = {"villa": ["salon", "salle_a_manger", "cuisine", "chambre", "sdb", "wc", "chambre*"],
          "maison": ["salon", "cuisine", "chambre", "sdb", "chambre*"]}


def villa(interior, outside, style: dict) -> None:
    plan(interior, outside, style, "villa")


def maison(interior, outside, style: dict) -> None:
    plan(interior, outside, style, "maison")


def programs(job, kind: str) -> dict:
    """floor -> program list (`[interiors.villa] programs` may replace the defaults)."""
    cfg = job.cfg.get("villa", {}).get("programs", {})
    floors = job.interior.floors
    dining = float(job.cfg.get("villa", {}).get("dining_area", 110.0))
    big = job.interior.storeys[0].polygon.area > dining
    out = {}
    for f in range(floors):
        if floors == 1:
            prog = list(cfg.get(f"{kind}_single", SINGLE[kind]))
        elif f == 0:
            prog = list(cfg.get(f"{kind}_ground", GROUND[kind]))
        else:
            prog = list(cfg.get("upper", UPPER))
        out[f] = [t for t in prog if t != "salle_a_manger" or big]
        if floors == 1 and job.interior.__dict__.get("tiny"):   # a tiny home's second plan (`layout.again`,
            out[f] = tiny(out[f])                               # round 8)
    return out


def tiny(prog: list) -> list:
    """A tiny one-floor home's program: no wc of its own (the sdb holds it) and the chambre placed before
    the cuisine, so the bedroom gets a cell and the cuisine the smaller one (round 8)."""
    out = [t for t in prog if t != "wc"]
    if "chambre" in out and "cuisine" in out:
        out.remove("chambre")
        out.insert(out.index("cuisine"), "chambre")
    return out


def plan(interior, outside, style: dict, kind: str) -> None:
    """Floor plans of a villa or a maison."""
    interior.layout = kind
    job = P.modern_job(interior, outside, style)
    entry = P.door_entry(job)
    floors = interior.floors
    core = place_box(job, entry, list(range(floors))) if floors > 1 and entry is not None else None
    if floors > 1 and core is None:
        interior.warnings.append("no stair fits between the floors: a ladder goes up")
    core, square = roof_stair(job, entry, core)
    box = core[0] if core else None
    job.landing = box                                 # the search's way score asks a way on it (round 10)
    top = floors - 1
    progs = programs(job, kind)
    halls, droj = [], None
    for st in interior.storeys:
        f = st.floor
        region = st.polygon
        landing = box
        if box is not None:
            region = shapely_less(region, box)
        if square is not None and f == top:
            region, cell = D.without(region, square, job.thin, job.zs([f]), job.half)
        e = entry if f == 0 else (upper_entry(job, core) if core else entry)
        if e is None:
            e = P.Entry(*region.representative_point().coords[0], 1.0, 0.0)
        cells = P.lay(job, largest(region), e, progs[f], f, (kind, f), hall=f == 0)
        if kind in job.cfg.get("villa", {}).get("halve", ()):
            halved(job, largest(region), cells, f)
        if kind in job.cfg.get("villa", {}).get("complete", ()) and f == 0:
            completed(job, largest(region), cells, f, floors)
        if kind in job.cfg.get("villa", {}).get("relight", ()):
            relit(job, cells, f)
        if (kind in job.cfg.get("villa", {}).get("way_room", ()) and f == top and "chambre" in progs[f]
                and not any(c.type == "chambre" for c in list(cells) + interior.rooms)):
            way_room(job, cells, f, e, landing)       # a home with no chambre: one from its hall or couloir
        if landing is not None:
            landing = to_landing(job, cells, landing, f)
        rest = [Cellish(p) for p in parts(snap(region.difference(largest(region))))] if len(parts(region)) > 1 else []
        for c in rest:
            cells.append(c)
        rooms = P.add_rooms(job, cells, f, "home")
        if box is None:
            rooms = P.nooks(job, rooms)
        if box is not None:
            way = P.add_rooms(job, [P.Cell(landing, "palier")], f, "home")[0]
            rooms = P.nooks(job, rooms, way)
            P.open_way(job, way, rooms)
            halls.append(way)
        if square is not None and f == top:
            droj = P.add_rooms(job, [P.Cell(cell, "droj")], f, "home")[0]
        P.doors(job, rooms)
    if core is not None:
        box, size, x, y, fd = core
        stair = S.u_record(box, fd, x, y, size, 0, top)
        stair.rooms = [r.id for r in halls]
        interior.stairs.append(stair)
    if square is not None and droj is not None:
        P.newel_rooms(job, square, droj)
    if floors > 1 and core is None:
        D.ladder_up(job)
    P.finish(job)
    focus(job)


def halved(job, region, cells: list, f: int) -> None:
    """A house's chambres, salle a manger and salon over their `most` (a room wrapping a patio, a hall no
    family would live in) cut in two (`spine.halve`, as flats have it), after the search (47.2 round C)."""
    most = job.cfg.get("rooms", {}).get("most", {})
    big = [c for c in cells if c.type in ("chambre", "salle_a_manger", "salon") and c.poly.area > float(most.get(c.type, 1e9))]
    if not big:
        return
    spine = {"F": P.couloir_frame(job, region, f), "ways": [c.poly for c in cells if c.type in ("couloir", "hall")]}
    for c in big:
        P.halve(job, spine, cells, c, f)


def completed(job, region, cells: list, f: int, floors: int) -> None:
    """A floor 0 with no salon, or a one-floor home with no chambre, takes it from the largest day room,
    cuisine or chambre cut in two (`spine.halve`: both halves windowed, each with a door's length on a way
    in), as a small house has its few rooms (47.2 round C)."""
    have = {c.type for c in cells}
    want = [t for t in ("salon", "chambre") if t not in have and (t == "salon" or floors == 1)]
    if not want:
        return
    spine = {"F": P.couloir_frame(job, region, f), "ways": [c.poly for c in cells if c.type in ("couloir", "hall")]}
    for t in want:
        donors = [c for c in cells if c.type in ("salon", "salle_a_manger", "cuisine", "chambre")]
        for c in sorted(donors, key=lambda c: -c.poly.area):
            if c.type == "chambre" and t == "chambre" or c.type == "salon" and t == "salon":
                continue
            if c.type == "chambre" and sum(x.type == "chambre" for x in cells) < 2 and t == "salon" and floors == 1:
                continue                                  # the only chambre of a one-floor home stays one
            old = c.poly
            new = P.halve(job, spine, cells, c, f)
            if new is None:
                continue
            if t == "chambre" or job.fits(new.poly, t):
                new.type = t
                break
            c.poly = old                                  # the half is too small for a salon: undone
            cells.remove(new)


def way_room(job, cells: list, f: int, entry, landing) -> None:
    """A home with no chambre on its top floor (a small house, or an upper floor whose couloir rings the
    stair): its hall or couloir, largest first, cut by one straight partition (the cuts of `repartition`)
    into a chambre and the way it keeps: the chambre windowed, within its minimum and most, with no
    corridor-like arm and a door's length on the way; the way keeping its minimum, the door or landing it
    starts from and a door's length on every room it served; the partition clear of the openings (47.2
    houses round 4)."""
    from shapely.geometry import Point
    from .cuts import shared
    sun = P.lights(job, f)
    most = job.cfg.get("rooms", {}).get("most", {})
    wide, thin = (float(v) for v in job.cfg.get("flats", {}).get("strip", (1.6, 3.0)))
    zones = job.zs([f])
    step = float(job.cfg.get("villa", {}).get("relight_step", 0.25))
    door, at = P.need(job), Point(entry.x, entry.y)
    lit = lambda poly: any(poly.distance(p) < 0.05 for p in sun)   # noqa: E731
    for c in sorted((c for c in cells if c.type in ("hall", "couloir")), key=lambda c: -c.poly.area):
        others = [x.poly for x in cells if x is not c and x.type in ("hall", "couloir")]
        served = [x.poly for x in cells if x is not c and shared(x.poly, c.poly) >= door
                  and not any(shared(x.poly, w) >= door for w in others)]
        if landing is not None and shared(landing, c.poly) >= door:
            served.append(landing)
        start = c.poly.distance(at) < 0.3

        def fine(room, way):
            if not (job.fits(room, "chambre") and lit(room) and room.area <= float(most.get("chambre", 1e9))
                    and P.strip(room, wide) <= thin and job.fits(way, c.type)):
                return False
            if max([shared(room, way)] + [shared(room, w) for w in others]) < door:
                return False
            if start and way.distance(at) > 0.05 or any(shared(x, way) < door for x in served):
                return False
            return not R.clash_polys(room, way, zones, 2 * job.half)
        got = cut_two(c.poly, step, fine)
        if got is not None:
            c.poly = got[1]
            cells.append(P.Cell(got[0], "chambre", c.band, c.part))
            return


def cut_two(u, step: float, fine):
    """(one part, the other) of `u` cut by one straight partition across or along its rotated rectangle,
    the cut nearest the middle first, the first pair `fine` takes (either way round); None when none."""
    import math
    from shapely import affinity
    from shapely.geometry import box
    from .cuts import snap
    rect = u.minimum_rotated_rectangle
    xy = list(rect.exterior.coords)
    angle = math.degrees(math.atan2(xy[1][1] - xy[0][1], xy[1][0] - xy[0][0]))
    flat = affinity.rotate(u, -angle, origin=(0, 0))
    x0, y0, x1, y1 = flat.bounds
    tries = []
    for axis, lo, hi in ((0, x0, x1), (1, y0, y1)):
        n = int((hi - lo) / step)
        tries += [(abs(k - n / 2), axis, lo + k * step) for k in range(1, n)]
    back = lambda g: affinity.rotate(g, angle, origin=(0, 0))   # noqa: E731
    for _, axis, at in sorted(tries):
        if axis == 0:
            a, b = box(x0 - 1, y0 - 1, at, y1 + 1), box(at, y0 - 1, x1 + 1, y1 + 1)
        else:
            a, b = box(x0 - 1, y0 - 1, x1 + 1, at), box(x0 - 1, at, x1 + 1, y1 + 1)
        pa, pb = parts(snap(back(flat.intersection(a)))), parts(snap(back(flat.intersection(b))))
        if len(pa) != 1 or len(pb) != 1:
            continue
        for one, two in ((pa[0], pb[0]), (pb[0], pa[0])):
            if fine(one, two):
                return one, two
    return None


def relit(job, cells: list, f: int) -> None:
    """A blind chambre or salle a manger beside a room holding two windows or more: the partition between
    them moved (the pair cut again across or along the pair's own sides) so both keep a window and a door's
    length on the hall or couloir, each within its minimum and `most`, with no corridor-like arm and the
    partition clear of the openings, as a planner gives each room a window (47.2 houses round 2)."""
    from .cuts import shared, union
    sun = P.lights(job, f)
    most = job.cfg.get("rooms", {}).get("most", {})
    wide, thin = (float(v) for v in job.cfg.get("flats", {}).get("strip", (1.6, 3.0)))
    zones = job.zs([f])
    step = float(job.cfg.get("villa", {}).get("relight_step", 0.25))
    windows = lambda poly: sum(1 for p in sun if poly.distance(p) < 0.05)   # noqa: E731
    for c in [c for c in cells if c.type in ("chambre", "salle_a_manger") and not windows(c.poly)]:
        ways = [x.poly for x in cells if x.type in ("couloir", "hall")]
        if not ways:
            return
        near = [x for x in cells if x is not c and x.type in ("salon", "salle_a_manger", "chambre", "cuisine")
                and windows(x.poly) >= 2 and shared(x.poly, c.poly) >= P.need(job)]
        for n in sorted(near, key=lambda x: (-shared(x.poly, c.poly), x.poly.area)):
            u = union(n.poly, c.poly)
            if u is None:
                continue
            got = repartition(job, u, n.type, c.type, ways, zones, most, wide, thin, step, windows)
            if got is not None:
                n.poly, c.poly = got
                break


def repartition(job, u, keep: str, other: str, ways: list, zones: list, most: dict, wide: float, thin: float,
                step: float, windows):
    """(keep's part, other's part) of `u` cut by one straight partition across or along its rotated
    rectangle, the cut nearest the middle first; None when no cut keeps both rooms windowed, on a way,
    within their minimum and most."""
    import math
    from shapely import affinity
    from shapely.geometry import box
    from .cuts import parts, shared, snap
    from .spine import strip
    rect = u.minimum_rotated_rectangle
    xy = list(rect.exterior.coords)
    angle = math.degrees(math.atan2(xy[1][1] - xy[0][1], xy[1][0] - xy[0][0]))
    flat = affinity.rotate(u, -angle, origin=(0, 0))
    x0, y0, x1, y1 = flat.bounds
    tries = []
    for axis, lo, hi in ((0, x0, x1), (1, y0, y1)):
        n = int((hi - lo) / step)
        for k in range(1, n):
            tries.append((abs(k - n / 2), axis, lo + k * step))
    back = lambda g: affinity.rotate(g, angle, origin=(0, 0))   # noqa: E731
    for _, axis, at in sorted(tries):
        if axis == 0:
            a, b = box(x0 - 1, y0 - 1, at, y1 + 1), box(at, y0 - 1, x1 + 1, y1 + 1)
        else:
            a, b = box(x0 - 1, y0 - 1, x1 + 1, at), box(x0 - 1, at, x1 + 1, y1 + 1)
        pa, pb = parts(snap(back(flat.intersection(a)))), parts(snap(back(flat.intersection(b))))
        if len(pa) != 1 or len(pb) != 1:
            continue
        for mine, rest in ((pa[0], pb[0]), (pb[0], pa[0])):
            if not (job.fits(mine, keep) and job.fits(rest, other)):
                continue
            if mine.area > float(most.get(keep, 1e9)) or rest.area > float(most.get(other, 1e9)):
                continue
            if not (windows(mine) and windows(rest)) or any(strip(x, wide) > thin for x in (mine, rest)):
                continue
            if any(max(shared(x, w) for w in ways) < P.need(job) for x in (mine, rest)):
                continue
            if R.clash_polys(mine, rest, zones, 2 * job.half):
                continue
            return mine, rest
    return None


def to_landing(job, cells: list, landing, f: int):
    """The palier (`landing`) with the strips of cells beside it thinner than 2 x `cuts.HAIR` (a couloir or
    room 0.2 m wide along the stair box: walls would swallow it and the doors on it, 47.1/48.1)."""
    from ..city.geo import polygons
    from .cuts import GRID, HAIR, clashes, shared, union
    zones = job.zs([f])
    for c in cells:
        least = job.minimums.get(c.type, (0.0, 0.0))[0]
        opened = c.poly.buffer(-HAIR, join_style="mitre").buffer(HAIR, join_style="mitre")
        core = parts(snap(opened.intersection(c.poly)))
        if not core:
            continue
        body = max(core, key=lambda p: p.area)
        for arm in polygons(shapely.difference(c.poly, body, grid_size=GRID)):
            if (arm.area < 1e-6 or not arm.buffer(-HAIR, join_style="mitre").is_empty
                    or shared(arm, landing) < 0.3 or clashes(arm, zones)):
                continue                              # (a strip at a window stays: no partition there)
            grown, rest = union(landing, arm), parts(shapely.difference(c.poly, arm, grid_size=GRID))
            if (grown is not None and len(rest) == 1 and rest[0].area >= least     # the room keeps its minimum
                    and not R.clash_polys(grown, rest[0], zones, 2 * job.half)):    # and no partition at a window
                landing, c.poly = grown, rest[0]
    return landing


class Cellish(P.Cell):
    """A piece of a storey split off by a neck (a room the doors pass connects)."""

    def __init__(self, poly):
        super().__init__(poly, "chambre")


def largest(region):
    got = parts(snap(region))
    return max(got, key=lambda p: p.area) if got else region


def shapely_less(region, box):
    got = parts(snap(region.difference(box)))
    if not got:
        return region
    return shapely.union_all(got)


def roof_stair(job, entry, core) -> tuple:
    """(core, roof newel square): when the U box takes the floor under the roof's stair room, the box
    keeps off it where it still fits (the roof newel then stands there; 47.1/48.1)."""
    interior = job.interior
    top = interior.floors - 1

    def newel(c):
        region = interior.storeys[top].polygon if c is None else snap(interior.storeys[top].polygon.difference(c[0]))
        return P.roof_newel(job, region, on_walls=True)

    square = newel(core)
    if square is not None or core is None or job.roof is None or job.roof.stair is None:
        return core, square
    off = place_box(job, entry, list(range(interior.floors)), off=job.roof.stair)
    if off is None or off[0].equals(core[0]):
        return core, square
    said, job.roof_ladder = list(interior.warnings), False
    again = newel(off)
    if again is None:
        interior.warnings, job.roof_ladder = said, True
        return core, square
    interior.warnings = [w for w in said if "the roof stair does not fit" not in w]
    return off, again


def place_box(job, entry, floors: list, off=None):
    """(box, size, x, y, door frame) of the U stair beside the hall: against the door wall beside the door
    (the side with more room first), slid along the wall and inward in 0.25 m steps until it lies inside
    every storey and its walls keep clear (and off `off`); the narrow box when no full one fits; None when
    none does."""
    fd = P.door_frame(entry)
    st0 = job.interior.storeys[0].polygon
    x0, _, x1, _ = fd.bounds(st0)
    sides = (1.0, -1.0) if x1 >= -x0 else (-1.0, 1.0)
    half = (job.main.width / 2 if job.main is not None else 0.45) + job.clear + job.half
    x_far, y_far = max(x1, -x0), fd.bounds(st0)[3]
    steps = sorted(((y, e) for y in np.arange(0.0, y_far, 0.25) for e in np.arange(0.0, x_far, 0.25)),
                   key=lambda t: (t[0] + t[1], t[0]))
    for narrow in (False, True):
        size = P.u_numbers(job, False, narrow)
        for y, e in steps:
            for s in sides:
                x = s * (half + e + size["across"] / 2)
                box = S.u_box(fd, x, float(y), size)
                if (off is None or box.intersection(off).area < 1e-4) and P.box_fits(job, box, floors):
                    return box, size, x, float(y), fd
    return None


def upper_entry(job, core):
    """Upstairs, the home is entered from the floor landing: the middle of its side toward the door."""
    box, size, x, y, fd = core
    s = 1.0 if x > 0 else -1.0
    p = fd.world(x - s * size["across"] / 2, y + size["landing"] / 2)
    n = -s * fd.u
    return P.Entry(float(p[0]), float(p[1]), float(n[0]), float(n[1]))


def focus(job) -> None:
    """The `interior` view: the salon toward its widest window."""
    interior = job.interior
    salon = next((r for r in interior.rooms if r.type == "salon"), None)
    if salon is None:
        return
    wins = [o for o in interior.openings if o.rooms[0] == salon.id and o.kind in ("window", "balcony")]
    if wins:
        interior.focus = (salon.id, max(wins, key=lambda o: (o.width, -o.id)).id)
