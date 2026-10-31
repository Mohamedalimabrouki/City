"""Flats in colonial blocks and slabs (SPEC 6c "Flats"): stair cores, landings, flat regions, types,
numbering, occupants.

Every stair core is a U stair box at a stair door, its floor landing against the door's wall: one room per
floor, the `palier` (unit `common`). A colonial block has one core centered on its main door, slid inward
until every storey holds it (the gap is floor 0's couloir), and one flat per floor, or two cut through
the core's middle; floor 0 holds the shop or cafe and the rest as a flat (or the unit's makhzen). A slab
has a core per stair door and two flats per core and floor, split where prompt 21's lit draws part (the
section borders and middles), so each flat's front and back windows share one draw each. Each flat region
is laid out by the spine engine from its landing door.
"""
from __future__ import annotations

import math

import numpy as np
import shapely
from shapely.geometry import Point

from ..city.geo import frame as oriented
from ..city.life import family_name
from ..names import NameMaker
from ..rng import stream, weighted
from . import dar as D
from . import rooms as R
from . import shop as SH
from . import spine as P
from . import stairs as S
from .cuts import Cell, Frame, clashes, clip, offsets, partition, parts, shared, solid
from .model import Flat

BIG = 500.0


class Core:
    """A stair core: its box, numbers, door frame (u along the door wall, v inward), the box's place in it
    (x, y), the floors it serves (0..top) and its palier rooms."""

    def __init__(self, box, size, fd, x, y, top, spot, bottom: int = 0):
        self.box, self.size, self.fd, self.x, self.y, self.top, self.spot = box, size, fd, x, y, top, spot
        self.bottom = bottom                              # a ladder well over a core that stops low
        self.paliers: dict = {}
        self.keep = False                                 # slid in past entry steps (prompt 49)

    def serves(self, f: int) -> bool:
        return self.bottom <= f <= self.top

    def entry(self, region, palier=None) -> P.Entry | None:
        """Where a flat region is entered from this core's floor landing: the point of their shared edge
        nearest the landing's middle, pointing into the region."""
        land = self.fd.rect(self.x - self.size["across"] / 2 - 0.01, self.y - 0.01,
                            self.x + self.size["across"] / 2 + 0.01, self.y + self.size["landing"] + 0.01)
        way = palier if palier is not None else self.box
        edge = region.boundary.intersection(way.buffer(1e-4, quad_segs=1))
        if edge.is_empty or edge.length < 0.5:
            return None
        if palier is not None and region.boundary.intersection(self.box.buffer(1e-4, quad_segs=1)).length < 0.5:
            near = edge                                   # a flat on the landing's strip: its middle
            from shapely.ops import nearest_points
            p = nearest_points(near, Point(*np.asarray(palier.centroid.coords[0])))[0]
            seg = shapely.get_coordinates(shapely.shortest_line(Point(p.x, p.y), region.representative_point()))
            d = seg[1] - seg[0]
            d = d / max(float(np.hypot(*d)), 1e-9)
            lu = self.fd.local(np.array([p.x, p.y]) + d) - self.fd.local((p.x, p.y))
            n = self.fd.u * np.sign(lu[0]) if abs(lu[0]) >= abs(lu[1]) else self.fd.v * np.sign(lu[1])
            return P.Entry(float(p.x), float(p.y), float(n[0]), float(n[1]))
        mid = Point(*self.fd.world(self.x, self.y + self.size["landing"] / 2))
        near = edge.intersection(land)
        line = near if (not near.is_empty and near.length > 0.3) else edge
        from shapely.ops import nearest_points
        p = nearest_points(line, mid)[0]
        c = np.asarray(self.box.centroid.coords[0])
        q = np.array([p.x, p.y])
        n = q - c
        # snap the normal to the box side the point lies on
        lu, lv = self.fd.local(q) - np.array([self.x, self.y])
        half, length = self.size["across"] / 2, self.size["length"]
        sides = [(abs(lu + half), -self.fd.u), (abs(lu - half), self.fd.u), (abs(lv), -self.fd.v),
                 (abs(lv - length), self.fd.v)]
        n = min(sides, key=lambda t: t[0])[1]
        return P.Entry(float(p.x), float(p.y), float(n[0]), float(n[1]))


def colonial(interior, outside, style: dict) -> None:
    interior.layout = "colonial"
    job = P.modern_job(interior, outside, style)
    entry = P.door_entry(job)
    keep = entry_keep(job, job.spot, entry) if entry is not None else None
    core = colonial_core(job, entry, keep) if entry is not None else None
    if (core is None or core.top < interior.floors - 1) and entry is not None:
        core = ladder_core(job, entry, keep) or core    # a block too thin for any stair: a ladder well
    run(job, [core] if core is not None else [], "colonial")


def slab(interior, outside, style: dict) -> None:
    interior.layout = "slab"
    job = P.modern_job(interior, outside, style)
    cores = []
    for spot in outside.doors:
        e = P.door_entry(job, spot)
        keep = entry_keep(job, spot, e) if e is not None else None
        first = 0.0 if keep is None else math.ceil(keep[1] / 0.25 - 1e-9) * 0.25   # beyond the entry steps
        c = (place_core(job, e, list(np.arange(first, first + 2.01, 0.25)), keep=keep[0] if keep else None)
             if e is not None else None)                  # slid in when needed
        if c is None and e is not None:
            c = ladder_core(job, e, keep)                 # no U box at all: a ladder well
        if c is not None:
            c.spot, c.keep = spot, keep is not None
            cores.append(c)
    run(job, cores, "slab")


# --- cores -------------------------------------------------------------------------------------------
def entry_keep(job, spot, entry) -> tuple | None:
    """(the floor the entry steps up from a door need, its length) when the door's threshold lies more
    than `threshold` under floor 0 (prompt 49: a stair box standing there cannot be walked); else None.
    The steps' numbers are `stairs.steps`'."""
    rise = job.interior.high - spot.z
    cfg = job.stairs
    if rise <= float(cfg.get("threshold", 0.15)):
        return None
    door = min((o for o in job.interior.openings if o.kind == "door" and o.floor == 0),
               key=lambda o: (math.hypot(o.x - spot.x, o.y - spot.y), o.id), default=None)
    width = (door.width if door is not None else 1.0) + 2 * float(cfg.get("side", 0.1))
    length = (S.risers(rise, float(cfg.get("riser", 0.18))) * float(cfg.get("tread", 0.3))
              + float(cfg.get("turn", 0.9)))            # the steps and the floor kept free beyond them
    fd = P.door_frame(entry)
    return fd.rect(-width / 2, -0.1, width / 2, length), length


def place_core(job, entry, slides, x: float = 0.0, keep=None) -> Core | None:
    """The core box at a door, centered on it and slid inward through `slides` until it lies inside every
    storey (else as many floors from the ground as hold it); the narrow box when no full one fits. A box
    on `keep` (the entry steps' floor) is never taken."""
    fd = P.door_frame(entry)
    floors = job.interior.floors
    best = None
    for narrow, extra in ((False, 0.0), (False, 0.3), (False, 0.6), (True, 0.0), (True, 0.3)):
        size = dict(P.u_numbers(job, True, narrow))
        size["across"] += extra                           # wider than its flights: clear of a wide stair window
        for y in slides:
            box = S.u_box(fd, x, float(y), size)
            if keep is not None and box.intersection(keep).area > 1e-3:
                continue
            top = -1
            for f in range(floors):
                if not P.box_fits(job, box, [f]):
                    break
                top = f
            if top == floors - 1:
                return Core(box, size, fd, x, float(y), top, None)
            if top >= 1 and (best is None or top > best.top):
                best = Core(box, size, fd, x, float(y), top, None)
    return best


def ladder_core(job, entry, keep=None) -> Core | None:
    """A block too thin for a U stair: a common well `[interiors.stairs] ladder_well` m square at the door,
    slid inward until every storey holds it, a ladder in it (each floor's palier), off the entry steps."""
    side = float(job.stairs.get("ladder_well", 1.2))
    fd = P.door_frame(entry)
    size = {"across": side, "landing": side, "length": side, "ladder": True}
    floors = list(range(job.interior.floors))
    for y in np.arange(0.0, float(job.cfg.get("flats", {}).get("slide_most", 6.0)) + 1e-9, 0.25):
        for x in [0.0] + [s * d for d in np.arange(0.5, 3.01, 0.5) for s in (1.0, -1.0)]:
            box = fd.rect(x - side / 2, float(y), x + side / 2, float(y) + side)
            if keep is not None and box.intersection(keep[0]).area > 1e-3:
                continue
            if P.box_fits(job, box, floors):
                c = Core(box, size, fd, x, float(y), len(floors) - 1, job.spot)
                return c
    return None


def colonial_core(job, entry, keep=None) -> Core | None:
    """The core centered on the main door, slid inward; when no slide lets every storey hold it, slid along
    the door wall too (0.5 m steps, nearer first), else the one serving most floors."""
    cfg = job.cfg.get("flats", {})
    step, most = float(cfg.get("slide", 0.25)), float(cfg.get("slide_most", 6.0))
    slides = list(np.arange(0.0, most + 1e-9, step))
    c = None
    for x in [0.0] + [s * d for d in np.arange(0.5, 3.01, 0.5) for s in (1.0, -1.0)]:
        got = place_core(job, entry, slides, x, keep[0] if keep else None)
        if got is not None and (c is None or got.top > c.top):
            c = got
        if c is not None and c.top == job.interior.floors - 1:
            break
    if c is not None:
        c.spot = job.spot
    return c


# --- the floors ----------------------------------------------------------------------------------------
def run(job, cores: list, kind: str) -> None:
    """Paliers, flat regions laid out by the spine, doors, the roof, flat records."""
    interior = job.interior
    floors = interior.floors
    top = floors - 1
    boxes = {f: [c.box for c in cores if c.serves(f)] for f in range(floors)}
    region_top = less(interior.storeys[top].polygon, boxes[top])
    square = P.roof_newel(job, region_top)
    flats = []          # (unit, floor, type)
    droj = None
    for st in interior.storeys:
        f = st.floor
        poly = less(st.polygon, boxes[f])
        cell = None
        if square is not None and f == top:
            poly, cell = D.without(poly, square, job.thin, job.zs([f]), job.half)
        common = []
        for c in cores:
            if c.serves(f):
                c.paliers[f] = P.add_rooms(job, [Cell(c.box, "palier")], f, "common")[0]
                common.append(c.paliers[f])
        if f == 0 and kind == "colonial" and cores:
            poly, extra = ground_floor(job, cores[0], poly)
            common += extra
        if kind == "slab":
            for c in cores:                               # a core slid in: the palier reaches its door
                if c.y > 0.05 and f in c.paliers and (f == 0 or c.keep):   # every floor over entry steps (49)
                    gap = clip(poly, c.fd.rect(c.x - c.size["across"] / 2, -1.0, c.x + c.size["across"] / 2, c.y + 1e-6))
                    merged = P.union(c.paliers[f].polygon, gap) if not gap.is_empty else None
                    if merged is not None:
                        c.paliers[f].polygon = merged
                        poly = solid(shapely.difference(poly, gap, grid_size=1e-6))
        if cell is not None:
            droj = P.add_rooms(job, [Cell(cell, "droj")], f, "common")[0]
        regions = no_slivers(job, flat_regions(job, cores, poly, f, kind), cores, f)
        if cores and f > 0 and not any(c.serves(f) for c in cores):
            duplex(job, regions, f)                       # a step above the cores: the upper floor of a flat
            continue
        shop_unit = next((r.unit for r in interior.rooms if r.floor == 0 and r.unit in ("shop", "cafe")), None)
        if f == 0 and kind == "colonial" and not P.lights(job, 0) and shop_unit is not None:
            host = next(r for r in interior.rooms if r.floor == 0 and r.type in ("qahwa", "hanout"))
            for region, core in regions:                  # no window: the cafe's or shop's stores, off it
                e = shop_entry(host, region) or P.Entry(*region.representative_point().coords[0], 1.0, 0.0)
                cells = P.lay(job, region, e, ["makhzen*"], f, ("stores", 0), hall=False)
                rooms = P.add_rooms(job, cells, f, shop_unit)
                for r in rooms:
                    if r.type == "couloir":
                        P.arch(job, host, r)
                P.doors(job, rooms)
            regions = []
        sun = P.lights(job, f)
        regions = windowed(regions, sun)
        blind = [(rg, c) for rg, c in regions if not P.lit(rg, sun)]
        if f == 0 and kind == "colonial" and blind:      # a region with no window on floor 0: stores, no flat
            regions = [(rg, c) for rg, c in regions if P.lit(rg, sun)]
            for region, core in blind:
                e = (core.entry(region, core.paliers[0].polygon) if core is not None and 0 in core.paliers
                     else None) or P.Entry(*region.representative_point().coords[0], 1.0, 0.0)
                cells = P.lay(job, region, e, ["makhzen*"], f, ("stores", 0))
                rooms = P.add_rooms(job, cells, f, "common")
                P.doors(job, rooms)
                if core is not None and 0 in core.paliers:
                    P.open_way(job, core.paliers[0], rooms)
        for place, (region, core) in enumerate(regions):
            n = len(flats)
            area = region.area
            ftype = type_of(job, area)
            unit = f"flat {n}"
            e = core.entry(region, core.paliers[f].polygon if f in core.paliers else None) if core is not None else None
            if e is None:
                e = P.Entry(*region.representative_point().coords[0], 1.0, 0.0)
            cells = P.lay(job, region, e, program(job, ftype, area), f, ("flat", place))   # stacked flats repeat
            rooms = P.add_rooms(job, cells, f, unit)
            rooms = P.nooks(job, rooms)
            P.doors(job, rooms)
            if core is not None and f in core.paliers:
                front_door(job, core.paliers[f], rooms)
            flats.append((unit, f, ftype))
    for c in cores:
        if c.bottom > 0:                                  # the ladder from the core's last palier up its well
            below = next((k for k in cores if k is not c and k.bottom == 0 and c.bottom - 1 in k.paliers), None)
            if below is None:
                continue
            rise = interior.fh * (c.top - c.bottom + 1)
            n = S.risers(rise, 0.3)
            stair = S.Stair("ladder", c.box, c.bottom - 1, c.top, n, rise / n, 0.0, 0.6, None)
            stair.rooms = [below.paliers[c.bottom - 1].id] + [c.paliers[f].id for f in sorted(c.paliers)]
            interior.stairs.append(stair)
            interior.warnings.append(f"the stair core stops at floor {c.bottom - 1}: a ladder goes up from its palier")
            continue
        if c.size.get("ladder"):
            n = S.risers(interior.fh, 0.3)
            spot = c.fd.rect(c.x - 0.3, c.y + c.size["length"] - 1.2, c.x + 0.3, c.y + c.size["length"])
            stair = S.Stair("ladder", spot, 0, c.top, n, interior.fh / n, 0.0, 0.6, None)
            interior.warnings.append("no stair fits the block: a ladder rises in a common well")
        else:
            stair = S.u_record(c.box, c.fd, c.x, c.y, c.size, 0, c.top)
        stair.rooms = [c.paliers[f].id for f in sorted(c.paliers)]
        interior.stairs.append(stair)
    if square is not None and droj is not None:
        P.newel_rooms(job, square, droj)
        droj.unit = "common"
    if not cores and floors > 1:
        interior.warnings.append("no stair core fits: a ladder goes up")
        D.ladder_up(job)
    SH.doors(job)
    P.finish(job, roof_unit="common")
    records(job, flats)
    focus(job)


def shop_entry(host, region) -> P.Entry | None:
    """Where stores behind a cafe or shop are entered from it: the middle of their longest shared edge."""
    from .cuts import contact
    pieces = contact(host.polygon, region)
    if not pieces:
        return None
    a, b = max(pieces, key=lambda p: np.hypot(*np.subtract(p[1], p[0])))
    mid = (np.asarray(a) + np.asarray(b)) / 2
    d = np.subtract(b, a)
    n = np.array([-d[1], d[0]]) / max(float(np.hypot(*d)), 1e-9)
    if not region.buffer(1e-3).contains(Point(*(mid + n * 0.05))):
        n = -n
    return P.Entry(float(mid[0]), float(mid[1]), float(n[0]), float(n[1]))


def duplex(job, regions: list, f: int) -> None:
    """Rooms on a floor no core reaches (the step of a stepped block) are the upper floor of the flat below
    that overlaps them most, reached by its own ladder (a duplex; a warning)."""
    interior = job.interior
    below = [r for r in interior.rooms if r.floor == f - 1 and r.unit.startswith("flat ")]
    for region, _ in regions:
        units = {}
        for r in below:
            units[r.unit] = units.get(r.unit, 0.0) + r.polygon.intersection(region).area
        if not units or max(units.values()) < 1.0:
            continue
        unit = max(sorted(units), key=lambda u: units[u])
        lower = shapely.union_all([r.polygon for r in below if r.unit == unit]).intersection(region)
        inner = solid(lower).buffer(-0.1, join_style="mitre")
        spot = S.ladder(inner, Frame.of(region), inner.centroid.coords[0], (0.6, 1.2)) if not inner.is_empty else None
        if spot is None:
            continue
        c = spot.centroid
        cells = P.lay(job, region, P.Entry(c.x, c.y, 1.0, 0.0), ["chambre", "sdb", "chambre*"], f, ("duplex", unit), False)
        rooms = P.add_rooms(job, cells, f, unit)
        P.doors(job, rooms)
        down = max((r for r in below if r.unit == unit), key=lambda r: (r.polygon.intersection(spot).area, -r.id))
        up = max(rooms, key=lambda r: (r.polygon.intersection(spot).area, -r.id))
        n = S.risers(interior.fh, 0.3)
        interior.stairs.append(S.Stair("ladder", spot, f - 1, f, n, interior.fh / n, 0.0, 0.6, None, [down.id, up.id]))
        interior.warnings.append(f"floor {f} stands over no stair core: a flat below goes up to it by a ladder")


def upper_wells(job, cores: list) -> list:
    """Over a core that stops below the top floor (a stepped block), a common ladder well at the far end of
    its box, on every floor above that holds it (each a palier; the ladder rises from the core's last one)."""
    floors = job.interior.floors
    out = []
    if not cores or max(c.top for c in cores) >= floors - 1:
        return out
    core = max(cores, key=lambda c: c.top)
    side = float(job.stairs.get("ladder_well", 1.2))
    end = core.y + core.size["length"]
    for x, y in ((core.x, end - side), (core.x, end), (core.x, core.y - side)):
        sq = core.fd.rect(x - side / 2, y, x + side / 2, y + side)
        if P.box_fits(job, sq, list(range(core.top + 1, floors))):
            size = {"across": side, "landing": side, "length": side, "ladder": True}
            out.append(Core(sq, size, core.fd, x, y, floors - 1, core.spot, core.top + 1))
            break
    return out


def ladder_on(job, core: Core) -> None:
    """The floors above a core's top are reached by a ladder from its last palier (a warning)."""
    interior = job.interior
    top = core.top
    interior.warnings.append(f"the stair core stops at floor {top}: a ladder goes up from its palier")
    w, d = (float(v) for v in job.stairs.get("ladder", [0.6, 1.2]))
    pal = core.paliers[top]
    spot = S.ladder(pal.polygon.buffer(-0.05, join_style="mitre"), core.fd, pal.polygon.centroid.coords[0], (w, d))
    if spot is None:
        return
    rooms = [pal.id]
    for f in range(top + 1, interior.floors):
        r = max((r for r in interior.rooms if r.floor == f and r.unit == "common"),
                key=lambda r: (r.polygon.intersection(spot).area, -r.id), default=None)
        if r is None:
            r = max((r for r in interior.rooms if r.floor == f), key=lambda r: (r.polygon.intersection(spot).area, -r.id),
                    default=None)
        if r is None:
            return
        rooms.append(r.id)
    rise = interior.fh * (interior.floors - 1 - top)
    n = S.risers(rise, 0.3)
    interior.stairs.append(S.Stair("ladder", spot, top, interior.floors - 1, n, rise / n, 0.0, w, None, rooms))


def less(poly, boxes: list):
    out = poly
    for b in boxes:
        out = solid(shapely.difference(out, b, grid_size=1e-6))
    return out


def ground_floor(job, core: Core, poly) -> tuple:
    """Floor 0 of a colonial block: the couloir from the door to a slid core, the cafe or shop, the rest a
    flat (when it keeps `min_flat`) or the unit's makhzen. Returns (the flats' region, common rooms)."""
    interior = job.interior
    common = []
    if core.y > 0.05:
        x0, x1 = gap_sides(job, core, poly)
        gap = clip(poly, core.fd.rect(x0, -1.0, x1, core.y + 1e-6))
        merged = P.union(core.paliers[0].polygon, gap) if (0 in core.paliers and not gap.is_empty
                                                           and core.y < 1.5) else None
        if merged is not None:                            # a short way in: the palier reaches the door
            core.paliers[0].polygon = merged
            poly = solid(shapely.difference(poly, gap, grid_size=1e-6))
        elif not gap.is_empty and gap.area > 0.3:
            room = P.add_rooms(job, [Cell(gap, "couloir")], 0, "common")[0]
            common.append(room)
            poly = solid(shapely.difference(poly, gap, grid_size=1e-6))
            if 0 in core.paliers:
                P.arch(job, room, core.paliers[0])
    kind = job.outside.ctx.dresser(job.outside.plan).front_of(interior.building)[2]
    keep = shapely.union_all([core.box] + [r.polygon for r in common]).buffer(0.01)
    if kind == "cafe":
        rooms, rest = SH.cafe(job, poly, keep)
        unit = "cafe"
    elif kind == "shop":
        rooms, rest = SH.souk(job, poly, False)
        unit = "shop"
    else:
        return poly, common
    interior.rooms += rooms
    least = float(job.cfg.get("flats", {}).get("min_flat", 40.0))
    rest = solid(rest)
    if rooms and 0 < rest.area < least:
        host = rooms[0]
        for p in parts(rest):
            store = P.add_rooms(job, [Cell(p, "makhzen")], 0, unit)[0]
            if not job.fits(p, "makhzen") and shared(p, host.polygon) > 0.5:
                merged = P.union(host.polygon, p)
                if merged is not None:
                    host.polygon = merged
                    interior.rooms.remove(store)
        return shapely.Polygon(), common
    return rest, common


def gap_sides(job, core: Core, poly) -> tuple:
    """The sides of floor 0's couloir from the door to a slid core: the box's sides, moved out of the
    openings' zones (a wide door); a side on a pier too narrow to keep clear stands in its middle."""
    fd, half = core.fd, core.size["across"] / 2
    strip = clip(poly, fd.rect(-BIG, -1.0, BIG, core.y))
    out = []
    for sgn in (-1.0, 1.0):
        x = core.x + sgn * half
        pier = pier_at(job, fd, sgn)
        if pier is not None:
            out.append(pier)
            continue
        got = job.free(strip, fd, 0, x, [0], *sorted((x, x + sgn * 1.2)))
        out.append(got if got is not None else x)
    return out[0], out[1]


def pier_at(job, fd: Frame, sgn: float) -> float | None:
    """The middle of the pier between the main door and a shop or cafe front beside it (on side `sgn`) when
    it is narrower than `clear` and a partition (the partition stands there, SPEC 6c Walls); else None."""
    door = job.main
    if door is None:
        return None
    xd = float(fd.local((door.x, door.y))[0])
    for o in job.interior.openings:
        if o.kind != "shop" or o.floor != 0 or abs(math.remainder(o.yaw - door.yaw, 2 * math.pi)) > 0.05:
            continue
        xs = float(fd.local((o.x, o.y))[0])
        if (xs - xd) * sgn <= 0:
            continue
        gap = abs(xs - xd) - o.width / 2 - door.width / 2
        if 0.0 < gap < job.clear + 2 * job.half:
            a = xd + sgn * door.width / 2
            job.interior.piers.append(fd.rect(min(a, a + sgn * gap), -1.0, max(a, a + sgn * gap), 0.1))
            return a + sgn * gap / 2
    return None


def flat_regions(job, cores: list, poly, f: int, kind: str) -> list:
    """(region, core) of every flat of a floor."""
    pieces = parts(poly)
    if not pieces:
        return []
    serving = [c for c in cores if c.serves(f)]
    if kind == "colonial":
        core = serving[0] if serving else None
        least = float(job.cfg.get("flats", {}).get("two_flats", 130.0))
        out = []
        for piece in pieces:
            if core is not None and piece.area >= least and piece.distance(core.box) < 1e-3:
                two, strip = split_core(job, core, piece, f)
                if two:
                    if strip is not None and f in core.paliers:   # the landing reaches the flats' doors
                        merged = P.union(core.paliers[f].polygon, strip)
                        if merged is not None:
                            core.paliers[f].polygon = merged
                    out += [(p, core) for p in two]
                    continue
            out.append((piece, core if core is not None and piece.distance(core.box) < 1e-3 else None))
        return attach(out)
    return attach(slab_regions(job, serving, pieces, f))


def windowed(regions: list, sun: list) -> list:
    """A flat region with no facade window joins the windowed region it shares most with (every flat has a
    window); without one it stays (floor 0 makes it stores)."""
    regions = list(regions)
    for _ in range(len(regions)):
        blind = [i for i, (p, _) in enumerate(regions) if not P.lit(p, sun)]
        moved = False
        for i in blind:
            p, c = regions[i]
            best = max((j for j in range(len(regions)) if j != i and P.lit(regions[j][0], sun)),
                       key=lambda j: shared(p, regions[j][0]), default=None)
            if best is not None and shared(p, regions[best][0]) > 0.3:
                merged = P.union(regions[best][0], p)
                if merged is not None:
                    regions[best] = (merged, regions[best][1] or c)
                    del regions[i]
                    moved = True
                    break
        if not moved:
            break
    return regions


def no_slivers(job, regions: list, cores: list, f: int) -> list:
    """No flat under `min_flat`: a smaller region joins the flat it shares most with, else the palier it
    touches (lead decision, prompt 47)."""
    least = float(job.cfg.get("flats", {}).get("min_flat", 40.0))
    regions = list(regions)
    for _ in range(len(regions)):
        small = sorted([i for i, (p, _) in enumerate(regions) if p.area < least], key=lambda i: regions[i][0].area)
        if not small:
            break
        i = small[0]
        p, c = regions[i]
        best = max((j for j in range(len(regions)) if j != i), key=lambda j: shared(p, regions[j][0]), default=None)
        if best is not None and shared(p, regions[best][0]) > 0.3:
            merged = P.union(regions[best][0], p)
            if merged is not None:
                regions[best] = (merged, regions[best][1] or c)
                del regions[i]
                continue
        pal = next((k.paliers[f] for k in cores if f in k.paliers and shared(p, k.paliers[f].polygon) > 0.3), None)
        if pal is not None:
            merged = P.union(pal.polygon, p)
            if merged is not None:
                pal.polygon = merged
                del regions[i]
                continue
        break
    return regions


def attach(out: list) -> list:
    """A region no core reaches joins the reached region it shares most with."""
    done = [(p, c) for p, c in out if c is not None]
    for p, c in [(p, c) for p, c in out if c is None]:
        best = max(range(len(done)), key=lambda i: shared(p, done[i][0]), default=None)
        if best is not None and shared(p, done[best][0]) > 0.5:
            merged = P.union(done[best][0], p)
            if merged is not None:
                done[best] = (merged, done[best][1])
                continue
        done.append((p, None))
    return done


def split_core(job, core: Core, piece, f: int) -> tuple:
    """(two flats, palier strip or None): the cut across the door wall where the two flats get equal areas;
    through the core's middle when that place falls on the core (in front of a slid core and behind it,
    each moved clear of the openings), else the floor landing reaches along the door wall to a door's
    length past the cut (SPEC 6c, as a slab's landing) and both flats open on it. ([], None) when no cut fits."""
    fd, x = core.fd, core.x
    half = core.size["across"] / 2
    y0, y1 = core.y, core.y + core.size["length"]
    s = balance(piece, fd)
    if x - half + 0.3 <= s <= x + half - 0.3 or s is None:
        return through_core(job, core, piece, f), None
    side = 1.0 if s > x else -1.0
    edge = x + side * half
    land = clip(piece, fd.rect(-BIG, y0, BIG, y0 + core.size["landing"]))
    cut_at = job.free(solid(shapely.difference(piece, land, grid_size=1e-6)) if not land.is_empty else piece,
                      fd, 0, s, [f])
    if cut_at is None or (cut_at - edge) * side < P.need(job):
        return through_core(job, core, piece, f), None
    end = job.free(land, fd, 0, cut_at + side * P.need(job), [f], *sorted((cut_at + side * P.need(job),
                                                                           cut_at + side * (P.need(job) + 1.2))))
    if end is None:
        return through_core(job, core, piece, f), None
    strip = parts(clip(land, fd.rect(min(edge, end), y0 - 0.01, max(edge, end), y0 + core.size["landing"] + 0.01)))
    if len(strip) != 1 or P.lit(strip[0].buffer(0.6), P.lights(job, f)):   # the landing never takes a window
        return through_core(job, core, piece, f), None
    rest = solid(shapely.difference(piece, strip[0], grid_size=1e-6))
    left = clip(rest, fd.rect(-BIG, -BIG, cut_at, BIG))
    right = solid(shapely.difference(rest, left, grid_size=1e-6))
    if len(parts(left)) != 1 or len(parts(right)) != 1:
        return through_core(job, core, piece, f), None
    return [parts(left)[0], parts(right)[0]], strip[0]


def balance(piece, fd: Frame) -> float | None:
    """The u of the line across the door wall that halves the piece's area (bisection)."""
    u0, _, u1, _ = fd.bounds(piece)
    total = piece.area
    if total <= 0:
        return None
    lo, hi = u0, u1
    for _ in range(30):
        mid = (lo + hi) / 2
        if clip(piece, fd.rect(-BIG, -BIG, mid, BIG)).area < total / 2:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def through_core(job, core: Core, piece, f: int) -> list:
    """Two flats cut through the core's middle: in front of the core (a slid core) and behind it, each
    cut moved clear of the openings; [] when no cut fits."""
    fd, x = core.fd, core.x
    y0, y1 = core.y, core.y + core.size["length"]
    xs = []
    for lo, hi in ((-BIG, y0), (y1, BIG)):
        strip = clip(piece, fd.rect(-BIG, lo, BIG, hi))
        if strip.is_empty or strip.area < 0.5:
            xs.append(x)
            continue
        got = job.free(strip, fd, 0, x, [f], x - core.size["across"] / 2 - 1.0, x + core.size["across"] / 2 + 1.0)
        if got is None:
            return []
        xs.append(got)
    left = shapely.union_all([fd.rect(-BIG, -BIG, xs[0], y0), fd.rect(-BIG, y0, x, y1), fd.rect(-BIG, y1, xs[1], BIG)])
    a, b = clip(piece, left), solid(shapely.difference(piece, left, grid_size=1e-6))
    if len(parts(a)) != 1 or len(parts(b)) != 1:
        return []
    return [parts(a)[0], parts(b)[0]]


def slab_regions(job, cores: list, pieces: list, f: int) -> list:
    """The flats of a slab floor: one per (section, half) of prompt 21, split at its borders and middles
    where every window stays on its draw's side and the partition keeps clear of the openings."""
    b = job.outside.b
    cx, cy, length, _, angle = oriented(b.footprint)
    fb = Frame(cx, cy, angle)
    lo, hi = job.outside.ctx.dresser(job.outside.plan).slab_cfg.get("stair_spacing", [20.0, 25.0])
    count = max(1, int(length / ((lo + hi) / 2) + 0.5))
    seg = max(length / count, 1e-6)
    marks = splits(job, fb, length, seg, count, cores)
    out = []
    for piece in pieces:
        regions = [piece]
        for poly_left in marks:
            nxt = []
            for r in regions:
                a = clip(r, poly_left)
                bb = solid(shapely.difference(r, poly_left, grid_size=1e-6))
                nxt += parts(a) + parts(bb)
            regions = nxt
        for r in regions:
            core = min(cores, key=lambda c: (r.distance(c.box) > 1e-3, r.distance(c.box)), default=None)
            out.append((r, core if core is not None and r.distance(core.box) < 1e-3 else None))
    return out


def splits(job, fb: Frame, length: float, seg: float, count: int, cores: list) -> list:
    """The left side (a polygon) of every split line of a slab, in prompt 21's order (t = u + length / 2)."""
    ts = window_ts(job, fb, length)
    storeys = [st.polygon for st in job.interior.storeys]
    out = []
    for j in range(1, 2 * count):
        mark = j * seg / 2 - length / 2                  # the draw border, in u
        core = None
        if j % 2:
            core = min(cores, key=lambda c: abs(fb.local(c.box.centroid.coords[0])[0] - mark), default=None)
            if core is not None and abs(fb.local(core.box.centroid.coords[0])[0] - mark) > seg / 2:
                core = None
        if core is None:
            s = line_at(job, fb, storeys, mark, ts, None, j)
            out.append(fb.rect(-BIG, -BIG, s, BIG))
            continue
        bu0, bv0, bu1, bv1 = fb.bounds(core.box)
        mid = (bu0 + bu1) / 2
        door_low = abs(bv0 - fb.bounds(job.outside.b.footprint)[1]) < abs(bv1 - fb.bounds(job.outside.b.footprint)[3])
        if core.keep:                                     # slid in past entry steps: the door's side decides
            door_low = float(np.dot(core.fd.v, fb.v)) > 0.0
        far = (bv1, BIG) if door_low else (-BIG, bv0)
        s = line_at(job, fb, storeys, mid, ts, far, j)
        near = (-BIG, bv1) if door_low else (bv0, BIG)
        out.append(shapely.union_all([fb.rect(-BIG, near[0], mid, near[1]), fb.rect(-BIG, far[0], s, far[1])]))
    return out


def window_ts(job, fb: Frame, length: float) -> list:
    """(u, draw part index) of every flat window (not a staircase's) of the block; the part is prompt 21's
    (section, half) as the dresser computes it, 2 x section + half."""
    dresser = job.outside.ctx.dresser(job.outside.plan)
    stairs = dresser._stairs
    part = dresser._sections(job.outside.b)
    out = []
    for o in job.interior.openings:
        if o.kind not in ("window", "balcony") or not o.piece:
            continue
        name = o.piece[:-4] if o.piece.endswith("_lit") else o.piece
        if name in stairs:
            continue
        sec, half = part(o.x, o.y)
        u, v = fb.local((o.x, o.y))
        out.append((float(u), 2 * sec + half, float(v)))
    return out


def line_at(job, fb: Frame, storeys: list, at: float, ts: list, band, j: int) -> float:
    """The split nearest `at` (within `cut_shift`) whose partition keeps clear on every floor (only within
    `band`, a v range, when given) and leaves every window on its draw's side (parts under j before it);
    without such a place, the nearest that keeps clear."""
    for keyed, d in [(True, d) for d in offsets(job.shift, job.step)] + [(False, d) for d in offsets(job.shift, job.step)]:
        s = at + d
        if keyed and any((t > s - 0.05) if idx < j else (t < s + 0.05) for t, idx, v in ts
                         if band is None or band[0] - 1.0 <= v <= band[1] + 1.0):
            continue
        ok = True
        for f, poly in enumerate(storeys):
            area = poly if band is None else clip(poly, fb.rect(-BIG, band[0], BIG, band[1]))
            if area.is_empty:
                continue
            if clashes(partition(area, fb, 0, s, job.half), job.zs([f])):
                ok = False
                break
        if ok:
            return s
    return at


# --- the flats ---------------------------------------------------------------------------------------
def type_of(job, area: float) -> str:
    types = job.cfg.get("flats", {}).get("types", [["S+1", 60.0], ["S+2", 100.0], ["S+3", 1e9]])
    return next((t for t, under in types if area < float(under)), types[-1][0])


def program(job, ftype: str, area: float) -> list:
    """Salon, cuisine, the n chambres of an S+n, sdb, a wc from `wc_area`, a salle a manger from
    `[interiors.villa] dining_area`."""
    n = int(ftype.split("+")[1])
    out = ["salon", "cuisine"] + ["chambre"] * n + ["sdb"]
    if area >= float(job.cfg.get("flats", {}).get("wc_area", 70.0)):
        out.append("wc")
    if area >= float(job.cfg.get("villa", {}).get("dining_area", 110.0)):
        out.append("salle_a_manger")                     # a big flat's dining room
    return out


def front_door(job, palier, rooms: list) -> None:
    """The flat's door from the landing into its hall (else into the room it shares most with)."""
    hall = next((r for r in rooms if r.type == "hall"), None)
    for r in ([hall] if hall is not None else []) + sorted([r for r in rooms if r is not hall and r.type not in P.WET],
                                                          key=lambda r: -shared(palier.polygon, r.polygon)):
        if shared(palier.polygon, r.polygon) < 0.5:
            continue
        if R.place(job.interior, palier, r, "inner", job.door, job.door_height, clear=P.inner(job)) is not None:
            return
        if R.place(job.interior, palier, r, "inner", job.interior.rules.get("narrow", 0.7), job.door_height,
                   clear=job.interior.rules.get("narrow_clear", 0.05)) is not None:
            return


def occupants(job, n: int) -> dict:
    """Derived occupants of flat n >= 1, drawn as `life.households` draws (wealth, door color, family
    pattern, trade, members) from the district's tables; names on their own stream."""
    i = job.interior
    style = job.outside.ctx.world.style
    life = style.get("life", {})
    r = stream(i.seed, "interior", i.city_id, i.building, "flat", n)
    namer = NameMaker(style, stream(i.seed, "interior", i.city_id, i.building, "flat", n, "names"))
    a, b = life.get("wealth", {}).get(i.district, [2.0, 3.0])
    wealth = float(r.beta(a, b))
    trades = life.get("trades", {}).get(i.district) or life.get("trades", {}).get("residential", [["merchant", 1]])
    door = weighted(r, life["door_colors"])
    family = family_name(namer, r, life)
    trade = weighted(r, trades)
    lo, hi = life.get("members", [2, 8])
    return {"building": i.building, "family": family, "trade": trade, "wealth": round(wealth, 2), "door": door,
            "members": int(r.integers(lo, hi + 1))}


def records(job, flats: list) -> None:
    """`Flat` records, numbered by floor then left to right seen from the main door; flat 0 holds the plan's
    household, the others derived occupants. Rooms follow their new numbers (units renamed)."""
    interior = job.interior
    fd = P.door_frame(P.door_entry(job)) if job.spot is not None else Frame(0.0, 0.0, 0.0)
    keyed = []
    for unit, f, ftype in flats:
        rooms = [r for r in interior.rooms if r.unit == unit]
        if not rooms:
            continue
        c = shapely.union_all([r.polygon for r in rooms]).centroid
        keyed.append((f, round(float(fd.local((c.x, c.y))[0]), 3), unit, ftype, rooms))
    keyed = [(f, x, unit, type_of(job, sum(r.polygon.area for r in rooms)), rooms) for f, x, unit, _, rooms in keyed]
    keyed.sort(key=lambda t: (t[0], t[1], t[2]))
    for n, (f, _, unit, ftype, rooms) in enumerate(keyed):
        for r in rooms:
            r.unit = f"flat {n}"
        home = interior.household if n == 0 else occupants(job, n)
        interior.flats.append(Flat(n, f, ftype, [r.id for r in rooms], home, n == 0))


def focus(job) -> None:
    """The `interior` view: flat 0's salon toward its window."""
    interior = job.interior
    if not interior.flats:
        return
    salon = next((r for r in interior.rooms if r.id in interior.flats[0].rooms and r.type == "salon"), None)
    if salon is None:
        return
    wins = [o for o in interior.openings if o.rooms[0] == salon.id and o.kind in ("window", "balcony")]
    if wins:
        interior.focus = (salon.id, max(wins, key=lambda o: (o.width, -o.id)).id)
