"""Plan checks for what the walls and steps will show (open items 47.1 + 48.1, SPEC 6c "Checks").

`rooms.check` calls `faults`. The walls (`mesh.walls_mesh`) take each room's free floor (`mesh.free`: the
room less every walled neighbour grown by half a partition) and cut every opening in the faces along it;
these checks ask the same of the plan without meshing: beside every opening the free floor reaches its
wall across the opening's whole width (no partition, no sliver, no storey edge there: a court corner, a
footprint part no storey covers), an inner door or passage stands inside its partition, and no two
openings of a floor take the same piece of wall. Entry steps need treads of `tread_min`, every tread
inside their room (a short or bent skifa clips none) and nothing of another stair over them.

`settle` (run at the end of every plan) slides the inner openings these checks fault to the nearest place
they pass; a court opening that fits nowhere goes and the doors pass places what is still needed.
"""
from __future__ import annotations

import math

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from .cuts import Frame, zone
from .mesh import CASED, FACADE, GAP, depths, frame_of, free, passage, walled_in

SLACK = 1e-4      # m2 a strip may miss (rounding)
WET = ("bit_el_ma", "wc", "sdb")                     # rooms nobody walks through on the way in (round 6)
KITCHENS = ("matbakh", "cuisine")
WALK = ("door", "shop", "inner", "court_door", "arch")   # openings a person walks through (`rooms.PASS`)


def faults(interior) -> list:
    """Every wall and entry-step problem of a plan, in plain words."""
    cfg = interior.rules.get("plan", {})
    out = []
    for f in range(interior.floors):
        out += _walls(interior, f, cfg)
    out += _steps(interior, cfg)
    return out + way_in(interior)


def rect(c, front, along, t0: float, t1: float, d0: float, d1: float) -> Polygon:
    return Polygon([c + along * t0 + front * d0, c + along * t1 + front * d0,
                    c + along * t1 + front * d1, c + along * t0 + front * d1])


class Floor:
    """One storey as the walls will see it: the rooms' free floor, the partitions, the court's face."""

    def __init__(self, interior, f: int, cfg: dict):
        self.interior, self.f = interior, f
        self.half = interior.walls["partition"] / 2
        self.floor = unary_union([p for _, ps, _ in free(interior, f, self.half) for p in ps])
        self.storey = interior.storeys[f].polygon
        self.walls = self.storey.difference(self.floor)
        holes = [Polygon(r) for p in getattr(self.storey, "geoms", [self.storey]) for r in p.interiors]
        self.courts = unary_union(holes).buffer(-interior.walls["court"], join_style="mitre")
        shapely.prepare(self.floor)
        self.probe = float(cfg.get("probe", 0.1))
        self.casing = float(cfg.get("casing", 0.05))
        self.hidden = False               # `settle`: a dar whose street door sees no court (keep it so)

    def span(self, o) -> tuple | None:
        """(lo, hi) along its wall of the hole the opening cuts (a passage: the run both rooms face, less
        0.1 m a side for its side walls), or None for a passage narrowed below its width."""
        if not passage(o):
            return -o.width / 2, o.width / 2
        c, front, along = frame_of(o)
        d0, d1 = depths(self.interior, o)
        lo, hi = _passage_span(self.floor, c, front, along, d0, d1, o.width / 2)
        if hi - lo < o.width - 2 * self.half - 0.02:
            return None
        return lo + 0.1, hi - 0.1

    def faults(self, o) -> list:
        """What the walls would find wrong with opening o (its overlaps aside)."""
        f = self.f
        span = self.span(o)
        if span is None:
            return [f"the {o.kind} {o.id} on floor {f} is narrowed by the walls beside it"]
        c, front, along = frame_of(o)
        d0, d1 = depths(self.interior, o)
        grow = 0.0 if passage(o) else (self.casing if o.kind in CASED else 0.0) - 0.01   # as `mesh.faults`
        t0, t1 = span[0] - grow, span[1] + grow
        near = rect(c, front, along, t0, t1, d0 - self.probe, d0 - GAP)
        if near.difference(self.floor).area > SLACK:
            edge = near.difference(self.storey).area > SLACK
            return [f"{'the storey' if edge else 'a wall'} crosses the {o.kind} {o.id} on floor {f}"]
        far = rect(c, front, along, t0, t1, d1 + GAP, d1 + self.probe)
        if (o.wall is not None or o.kind in FACADE) and \
                rect(c, front, along, t0, t1, d0 + 2 * GAP, d1).intersection(self.storey).area > SLACK:
            return [f"the floor reaches into the wall of the {o.kind} {o.id} on floor {f}"]   # a jagged face
        if o.wall is None and o.kind not in FACADE:
            if rect(c, front, along, t0, t1, d0 + GAP, d1 - GAP).difference(self.walls).area > SLACK:
                return [f"the {o.kind} {o.id} on floor {f} is not in its partition"]
            if far.difference(self.floor).area > SLACK:
                return [f"a wall crosses the {o.kind} {o.id} on floor {f} (far side)"]
        elif o.wall is not None and o.kind not in FACADE and far.difference(self.courts).area > SLACK:
            return [f"the {o.kind} {o.id} on floor {f} runs past a corner of the court"]
        return []

    def hole(self, o):
        """The opening's hole through its wall (None for a narrowed passage)."""
        span = self.span(o)
        if span is None:
            return None
        c, front, along = frame_of(o)
        d0, d1 = depths(self.interior, o)
        return rect(c, front, along, span[0], span[1], d0 - GAP, d1 + GAP)


def _walls(interior, f: int, cfg: dict) -> list:
    ops = [o for o in interior.openings if o.floor == f and walled_in(interior, o, cfg)]
    if not ops:
        return []
    fl = Floor(interior, f, cfg)
    out = [p for o in ops for p in fl.faults(o)]
    holes = [(o, fl.hole(o)) for o in ops]
    holes = [(o, h) for o, h in holes if h is not None]
    for i, (a, ha) in enumerate(holes):
        for b, hb in holes[i + 1:]:
            if ha.intersection(hb).area > SLACK:
                out.append(f"the {a.kind} {a.id} and the {b.kind} {b.id} on floor {f} overlap")
    return out


def trim(interior) -> None:
    """Hair strips of finished rooms (thinner than 2 x `cuts.HAIR`: walls would swallow them and the doors on
    them) go to the neighbour of the same unit they share most boundary with, when no partition then meets
    a wall near an opening and the room keeps its minimum (47.1/48.1); a bent skifa's half all hair strip
    joins its other neighbour (the court: the skifa's arch then opens on it, round 6)."""
    from ..city.geo import polygons
    from .cuts import GRID, HAIR, VOID_TYPES, parts, shared, union, width
    from .rooms import KEEP, clash_polys, connect, is_court, merge, renumber, zones_of
    least = interior.rules.get("minimums", {})
    merged = False
    for f in range(interior.floors):
        rooms = [r for r in interior.rooms if r.floor == f and not is_court(r) and r.type not in VOID_TYPES]
        zones = zones_of(interior, f)
        for r in list(rooms):
            core = parts(r.polygon.buffer(-HAIR, join_style="mitre").buffer(HAIR, join_style="mitre")
                         .intersection(r.polygon))
            half = r.type == "skifa" and any(o.type == "skifa" and o is not r and o.unit == r.unit for o in rooms)
            if not core or half and width(r.polygon) < 2 * HAIR:   # a room all hair strip joins its neighbour
                hosts = rooms + ([o for o in interior.rooms if o.floor == f and o.type == "wast_ed_dar" and not o.open]
                                 if half else [])     # a skifa half: the covered court takes it
                ranked = sorted(((shared(r.polygon, o.polygon), o.id, o) for o in hosts
                                 if o is not r and o.unit == r.unit and not (half and o.type == "skifa")),
                                key=lambda t: (-t[0], t[1]))
                if ((r.type not in KEEP or half) and ranked and ranked[0][0] > 0.1   # a skifa's hair half (round 6)
                        and merge(interior, ranked[0][2], r)):
                    rooms.remove(r)
                    merged = True
                    if half:                          # its arch would open on the hair strip: the doors pass
                        host = ranked[0][2]           # finds the skifa another way in
                        interior.openings = [o for o in interior.openings if not (
                            host.id in o.rooms and o.kind in ("arch", "inner", "court_door") and any(
                                x.id in o.rooms and x.type == "skifa" for x in rooms))]
                        connect(interior)
                continue
            body = max(core, key=lambda p: p.area)
            for arm in polygons(shapely.difference(r.polygon, body, grid_size=GRID)):
                if arm.area < 1e-4 or not arm.buffer(-HAIR, join_style="mitre").is_empty:
                    continue
                ranked = sorted(((shared(arm, o.polygon), o.id, o) for o in rooms if o is not r and o.unit == r.unit),
                                key=lambda t: (-t[0], t[1]))
                if not ranked or ranked[0][0] <= shared(arm, body) + 1e-3:
                    continue
                o = ranked[0][2]
                grown, rest = union(o.polygon, arm), parts(shapely.difference(r.polygon, arm, grid_size=GRID))
                if (grown is None or len(rest) != 1 or rest[0].area < least.get(r.type, (0.0, 0.0))[0]
                        or clash_polys(grown, rest[0], zones, interior.rules["partition"])):
                    continue
                o.polygon, r.polygon = grown, rest[0]
    if merged:
        renumber(interior)


MOVABLE = ("inner", "inner_window", "arch", "court_door", "court_window")   # openings `settle` may slide
STEP = 0.05       # meters between the places `settle` tries


def settle(interior, again: bool = True) -> None:
    """Slide every inner opening (door, inner window, passage, court door or window) the walls would find
    at fault along its wall to the nearest place where they find none (a door that fits nowhere tries the
    narrow door; a passage keeps the run both rooms face). A court opening that fits nowhere goes, and the
    doors pass places what is still needed (as `rooms.unclash`). Facade openings are the tile's: they stay."""
    if not interior.rules:
        return
    from . import rooms as R
    cfg = interior.rules.get("plan", {})
    gone = set()
    by_id = {r.id: r for r in interior.rooms}
    narrow = float(interior.rules.get("narrow", 0.7))
    for f in range(interior.floors):
        ops = [o for o in interior.openings if o.floor == f and walled_in(interior, o, cfg)]
        if not ops:
            continue
        fl = Floor(interior, f, cfg)
        fl.hidden = interior.layout == "dar" and not _sees_court(interior)   # keep the bent entry bent
        holes = {o.id: fl.hole(o) for o in ops}
        for o in ops:
            if o.kind not in MOVABLE or _fits(fl, o, holes, by_id):
                continue
            old = (o.x, o.y, o.s, o.width)
            widths = (o.width, narrow) if o.kind == "inner" and o.width > narrow else (o.width,)
            places = ((w, c) for w in widths for c in _places(interior, o, w, by_id, fl.floor))
            if not any(_fits(fl, _put(o, c, w), holes, by_id) for w, c in places):
                o.x, o.y, o.s, o.width = old
                if again and o.wall is not None and not any(by_id[r].type == "skifa" for r in o.rooms if r in by_id):
                    gone.add(id(o))
                    holes.pop(o.id)
                    continue
            holes[o.id] = fl.hole(o)
    if gone:
        interior.openings = [o for o in interior.openings if id(o) not in gone]
        R.renumber(interior)
        R.connect(interior)
        R.renumber(interior)
        settle(interior, again=False)


def bend(interior) -> None:
    """The bent entry (decision D, round 6): a dar whose court shows from the street door slides the
    inner openings of its entry room, then of the rooms that room opens into, along their walls to the
    nearest place the walls accept where the court no longer shows (the skifa's door off the street
    door's line); the first such place stays."""
    door = interior.entry
    if interior.layout != "dar" or door is None or door not in interior.openings or not _sees_court(interior):
        return
    cfg = interior.rules.get("plan", {})
    by_id = {r.id: r for r in interior.rooms}
    first = [i for i in door.rooms if i in by_id]
    ops = [o for o in interior.openings if o.floor == 0 and walled_in(interior, o, cfg) and o.kind in MOVABLE]
    near = {i for o in ops if set(o.rooms) & set(first) for i in o.rooms} - set(first)
    order = [o for o in ops if set(o.rooms) & set(first)] + [o for o in ops if set(o.rooms) & near
                                                             and not set(o.rooms) & set(first)]
    fl = Floor(interior, 0, cfg)
    fl.hidden = False
    holes = {o.id: fl.hole(o) for o in ops}
    for o in order:
        old = (o.x, o.y, o.s, o.width)
        for place in _places(interior, o, o.width, by_id, fl.floor):
            if _fits(fl, _put(o, place, o.width), holes, by_id) and not _sees_court(interior):
                return
        o.x, o.y, o.s, o.width = old


def _put(o, place: tuple, width: float):
    o.x, o.y, o.s, o.width = place[0], place[1], place[2], width if place[3] is None else place[3]
    return o


def _fits(fl: Floor, o, holes: dict, by_id: dict) -> bool:
    """True when the walls find nothing at fault with o, its hole meets no other and it joins its rooms (a
    dar's skifa openings: and the street door still sees no court)."""
    a, b = by_id.get(o.rooms[0]), by_id.get(o.rooms[1])
    if fl.faults(o):
        return False
    hole = fl.hole(o)
    if any(k != o.id and h is not None and hole.intersection(h).area > SLACK for k, h in holes.items()):
        return False
    rules = fl.interior.rules
    if (fl.hidden and any(r is not None and r.type == "skifa" for r in (a, b)) and _sees_court(fl.interior)):
        return False                                  # the bent entry first
    if o.wall is not None:                            # a court opening keeps `clear` from the partitions too
        z = zone(o, rules["court"], rules["clear"], rules.get("front_keep", 0.0))
        if z is not None and z.intersection(fl.walls).area > 0.01 * rules["partition"]:
            return False
    c, front, along = frame_of(o)
    d0, d1 = depths(fl.interior, o)
    lo, hi = fl.span(o)
    if a is not None and rect(c, front, along, lo, hi, d0 - fl.probe, d0 - GAP).difference(a.polygon).area > SLACK:
        return False
    if (o.wall is None and b is not None
            and rect(c, front, along, lo, hi, d1 + GAP, d1 + fl.probe).difference(b.polygon).area > SLACK):
        return False
    return True


def _sees_court(interior) -> bool:
    from .rooms import sees_court
    return sees_court(interior)


def _places(interior, o, width: float, by_id: dict, floor=None):
    """(x, y, s, width or None) places for o, nearest its own first: along its court wall, else along the
    straight pieces its two rooms share (a passage: first recentred on the run both rooms face)."""
    c = np.array([o.x, o.y])
    out = []
    if o.wall is not None:
        a, b = np.asarray(o.wall[0], dtype=float), np.asarray(o.wall[1], dtype=float)
        length = float(np.hypot(*(b - a)))
        d = (b - a) / max(length, 1e-9)
        for t in np.arange(width / 2 + STEP, length - width / 2 - STEP + 1e-9, STEP):
            p = a + d * t
            out.append((float(np.hypot(*(p - c))), float(p[0]), float(p[1]), float(t), None))
    else:
        from .rooms import pieces_between
        ra, rb = by_id.get(o.rooms[0]), by_id.get(o.rooms[1])
        if ra is None or rb is None:
            return []
        along = np.array([math.cos(o.yaw), math.sin(o.yaw)])
        for p0, p1 in pieces_between(interior, ra, rb):
            p0, p1 = np.asarray(p0, dtype=float), np.asarray(p1, dtype=float)
            length = float(np.hypot(*(p1 - p0)))
            d = (p1 - p0) / max(length, 1e-9)
            if abs(float(d @ along)) < 0.999:          # the opening keeps its wall's direction
                continue
            half = interior.walls["partition"] / 2
            if passage(o):                            # the runs both rooms face, narrowed to them
                out += _narrowed(interior, o, p0, d, length, c, floor)
            if passage(o) and 0.8 <= length - 2 * half < width - 1e-6:   # a passage spanning the piece: narrowed
                p = (p0 + p1) / 2
                out.append((float(np.hypot(*(p - c))), float(p[0]), float(p[1]), o.s, length - 2 * half))
                continue
            for t in np.arange(width / 2 + STEP, length - width / 2 - STEP + 1e-9, STEP):
                p = p0 + d * t
                out.append((float(np.hypot(*(p - c))), float(p[0]), float(p[1]), o.s, None))
    out.sort(key=lambda x: (round(x[0], 6), x[1], x[2]))
    return [x[1:] for x in out]


def _runs(floor, c, front, along, d0: float, d1: float, half: float, inset: float) -> list:
    """The (lo, hi) runs along an opening's wall within `half` of its center where both rooms have free floor
    `inset` m from the wall's faces."""
    got = None
    for d in (d0 - inset, d1 + inset):
        line = LineString([c + along * -half + front * d, c + along * half + front * d]).intersection(floor)
        mine = []
        for g in getattr(line, "geoms", [line]):
            if g.geom_type == "LineString" and not g.is_empty:
                ts = [float((np.asarray(p) - c - front * d) @ along) for p in g.coords]
                mine.append((min(ts), max(ts)))
        got = mine if got is None else [(max(a0, b0), min(a1, b1)) for a0, a1 in got for b0, b1 in mine
                                        if min(a1, b1) > max(a0, b0)]
    return sorted(got or [])


def _narrowed(interior, o, p0, d, length: float, c, floor) -> list:
    """Places for a passage on the piece from p0 along d: each run both its rooms face `probe` m in, as wide
    as the run (at most its width, at least `passage_min`)."""
    cfg = interior.rules.get("plan", {})
    least, probe = float(cfg.get("passage_min", 0.8)), float(cfg.get("probe", 0.1))
    if floor is None:
        return []
    mid = p0 + d * length / 2
    front = np.array([-math.sin(o.yaw), math.cos(o.yaw)])
    d0, d1 = depths(interior, o)
    out = []
    for lo, hi in _runs(floor, mid, front, d, d0, d1, length / 2, probe):
        w = min(hi - lo, o.width)
        if w < least + 0.2:
            continue
        t = min(max(float((c - mid) @ d), lo + w / 2), hi - w / 2)
        p = mid + d * t
        out.append((float(np.hypot(*(p - c))), float(p[0]), float(p[1]), o.s, w))
    return out


def _passage_span(floor, c, front, along, d0: float, d1: float, half: float) -> tuple:
    """(lo, hi) along its wall of the run of a passage both its rooms face, holding its center."""
    lo, hi = -half, half
    for d in (d0 - 2 * GAP, d1 + 2 * GAP):
        line = LineString([c + along * -half + front * d, c + along * half + front * d]).intersection(floor)
        run = (0.0, 0.0)
        for g in getattr(line, "geoms", [line]):
            if g.geom_type != "LineString" or g.is_empty:
                continue
            ts = [float((np.asarray(p) - c - front * d) @ along) for p in g.coords]
            if min(ts) <= 0.0 <= max(ts):
                run = (min(ts), max(ts))
        lo, hi = max(lo, run[0]), min(hi, run[1])
    return lo, hi


def _steps(interior, cfg: dict) -> list:
    """Entry steps: treads of at least `tread_min`, all inside their room, no other stair over them."""
    others = [s for s in interior.stairs if s.kind != "steps" and s.floor == 0]
    return [f for s in interior.stairs if s.kind == "steps" for f in step_faults(s, others, cfg)]


def step_faults(s, others: list, cfg: dict) -> list:
    """The faults of one flight of entry steps (`_steps`); `others`: the stairs of floor 0."""
    least = float(cfg.get("tread_min", 0.2))
    out = []
    if s.tread < least - 1e-6:
        out.append(f"the entry steps have treads of {s.tread:.2f} m")
    x, y, yaw = s.door
    fr = Frame(x, y, yaw + math.pi / 2)
    _, v0, _, _ = fr.bounds(s.polygon)
    if s.turn:                                        # along the wall, past the door's landing
        pts = [Point(*fr.world(s.turn * (s.width / 2 + (k + 0.5) * s.tread), v0 + s.flight / 2))
               for k in range(s.risers)]
    else:
        pts = [Point(*fr.world(0.0, v0 + (k + 0.5) * s.tread)) for k in range(s.risers)]
    if not all(s.polygon.covers(p) for p in pts):
        out.append("the entry steps are clipped by their room")
    for o in others:
        if s.polygon.intersection(o.polygon).area > 0.01:
            out.append(f"the entry steps run under the {o.kind} stair")
    return out


def way_in(interior) -> list:
    """The way from the street door to the court (without one, to the hall) crosses no wet room and no
    matbakh, and no sunken entry's steps stand in one (open items 47.1 + 48.1, round 6)."""
    out = [f"the entry steps stand in the {r.type}" for s in interior.stairs if s.kind == "steps" and s.sunk >= 0
           for r in interior.rooms if r.id == s.rooms[0] and r.type in WET + KITCHENS]
    rooms = {r.id: r for r in interior.rooms}
    crossed = [rooms[i].type for i in way_rooms(interior) if rooms[i].type in WET + KITCHENS]
    if crossed:
        out.append(f"the way in crosses the {' and the '.join(crossed)}")
    return out


def way_rooms(interior) -> list:
    """The room ids of floor 0 on the way in (`way_in`): the fewest wet rooms and kitchens crossed."""
    door = interior.entry
    if door is None or door not in interior.openings or interior.flats:
        return []
    rooms = {r.id: r for r in interior.rooms if r.floor == door.floor}
    goal = {i for i, r in rooms.items() if r.type == "wast_ed_dar"} or {i for i, r in rooms.items() if r.type == "hall"}
    start = [i for i in door.rooms if i in rooms]
    return _path(interior, rooms, start, goal) if goal and start else []


def _path(interior, rooms: dict, start: list, goal: set) -> list:
    """The room ids on a way from `start` to `goal` that crosses the fewest wet rooms and kitchens (Dijkstra
    on whole rooms; [] when no way)."""
    import heapq
    graph = {i: set() for i in rooms}
    for o in interior.openings:
        a, b = o.rooms
        if o.kind in WALK and a in rooms and b in rooms:
            graph[a].add(b)
            graph[b].add(a)
    cost = lambda i: 100 if rooms[i].type in WET + KITCHENS else 1
    todo = [(cost(i), i, (i,)) for i in sorted(start)]
    done = set()
    while todo:
        c, i, way = heapq.heappop(todo)
        if i in goal:
            return list(way)
        if i in done:
            continue
        done.add(i)
        for j in sorted(graph[i] - done):
            heapq.heappush(todo, (c + cost(j), j, way + (j,)))
    return []
