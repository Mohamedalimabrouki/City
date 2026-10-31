"""A couloir carved through a chambre, cuisine or sdb (open items 47.1 + 48.1, round 11).

An upper floor whose couloir the spine planned away from the stair's palier (a chambre between them), or a
salon or couloir behind the cuisine of a hall in an acute corner, is reached only through that room
(`plancheck.way_home`). `passages` finds the strips of such a room a couloir wide that run straight from
a room the entry reaches on that floor (the palier, the hall) to the room off the way, or back; `cut` gives
the strip to the hall or couloir (or makes it a couloir of its own). `layout.carve` keeps a cut only when
the plan check then finds fewer faults and the home no more dark rooms.
"""
from __future__ import annotations

import math

from shapely import set_precision
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

from .cuts import GRID, width as least_width

HOSTS = ("chambre", "cuisine", "sdb")   # rooms a passage may cut through
GOALS = ("salon", "salle_a_manger", "cuisine", "couloir", "palier")   # rooms it leads to
GROW = ("hall", "couloir")      # rooms that take the strip
TOUCH = 0.03           # m: a band this near its goal meets it
LIGHTS = ("window", "balcony")   # facade openings that light a room
OVER = 0.3             # m: a strip may stand this far past the ends of its segment (round a jog of the wall)
STEP = 0.1             # m between the strips tried along a segment
NECK = 0.8             # m: a hall or couloir narrower than this somewhere is two rooms to walk


def band(host: Polygon, seg: tuple, goal: Polygon, wide: float, step: float, most: float,
         over: float = 0.0) -> list:
    """The strips of `host` `wide` m wide that run straight in from the segment `seg` of its boundary (every
    `step` m along it) up to `goal` (or along it, when the goal lies beside the strip), meeting it on at least
    `wide` x 0.85, at most `most` m long; each a Polygon, the smallest first. `over`: instead the strips
    standing up to `over` m past the segment's ends (round a jog in the wall)."""
    (ax, ay), (bx, by) = seg
    length = math.hypot(bx - ax, by - ay)
    if length < wide:
        return []
    ux, uy = (bx - ax) / length, (by - ay) / length
    nx, ny = -uy, ux
    mx, my = (ax + bx) / 2, (ay + by) / 2
    if not host.contains(Point(mx + nx * 0.05, my + ny * 0.05)):
        nx, ny = -nx, -ny
    n = int((length - wide) / step + 1e-9)
    starts = sorted({round(i * step, 6) for i in range(n + 1)} | {round(length - wide, 6)})
    if over:                                          # only the strips past an end of the segment
        k = int(over / step + 1e-9)
        starts = ([round(-i * step, 6) for i in range(k, 0, -1)]
                  + [round(length - wide + i * step, 6) for i in range(1, k + 1)])
    out = []
    for t in starts:
        p0 = (ax + ux * t, ay + uy * t)
        p1 = (p0[0] + ux * wide, p0[1] + uy * wide)
        far = Polygon([p0, p1, (p1[0] + nx * most, p1[1] + ny * most), (p0[0] + nx * most, p0[1] + ny * most)])
        hit = far.intersection(goal)
        if hit.is_empty or hit.area < 1e-4:           # the goal beside the strip: run along it to its far end
            hit = far.buffer(TOUCH, join_style="mitre").intersection(goal)
            if hit.is_empty or hit.area < 1e-4:
                continue
            d = min(most, max((x - p0[0]) * nx + (y - p0[1]) * ny for x, y in _coords(hit)))
            got = _reach(host, goal, p0, p1, (nx, ny), d, 0.0, step)
            if got is not None:
                out.append(got)
            continue
        d = min((x - p0[0]) * nx + (y - p0[1]) * ny for x, y in _coords(hit))
        if d <= 0 or d > most:
            continue
        got = _reach(host, goal, p0, p1, (nx, ny), d, wide, step)
        if got is not None:
            out.append(got)
    return sorted(out, key=lambda p: p.area)


def _reach(host: Polygon, goal: Polygon, p0, p1, n, d: float, wide: float, step: float):
    """The strip of `host` from p0-p1 `d` m in along `n`, deepened by `step` up to `wide` more until it shares
    an edge of `wide` x 0.85 with `goal`; None when it never does."""
    nx, ny = n
    for i in range(int(wide / step) + 1):
        e = d + i * step
        rect = Polygon([p0, p1, (p1[0] + nx * e, p1[1] + ny * e), (p0[0] + nx * e, p0[1] + ny * e)])
        part = one(set_precision(rect.intersection(host), GRID))
        if part is None:
            return None
        if (part.buffer(TOUCH).intersection(goal).area >= TOUCH * wide * 0.85
                and one(set_precision(unary_union([goal, part]), GRID)) is not None):
            return part
    return None


def one(geom):
    """`geom` as one Polygon (numerical slivers dropped), else None."""
    parts = [g for g in getattr(geom, "geoms", [geom]) if g.geom_type == "Polygon" and g.area > 1e-4]
    return parts[0] if len(parts) == 1 else None


def necks(poly) -> int:
    """How many pieces `poly` falls into where a person `NECK` m wide cannot pass."""
    e = poly.buffer(-NECK / 2, join_style="mitre")
    return 0 if e.is_empty else len(getattr(e, "geoms", [e]))


def _coords(geom):
    """Every vertex of `geom`'s polygons and lines."""
    for g in getattr(geom, "geoms", [geom]):
        if g.geom_type == "Polygon":
            yield from g.exterior.coords
        elif hasattr(g, "coords"):
            yield from g.coords


def passages(interior, wide: float, most: float = 8.0, over: float = 0.0) -> list:
    """(band, host id, goal id, grown id) for every day room, couloir or palier a home's entry reaches only
    through a chambre, cuisine or sdb (`HOSTS`): strips of such a room of its floor that join it to a room
    the entry reaches there (`band`); the strip joins that room when it is a hall or couloir, else the goal
    when it is a couloir, else it becomes a couloir of its own (grown id None); the smallest first (`over`:
    see `band`)."""
    from . import plancheck as P
    from .rooms import pieces_between
    out = []
    for unit, rooms, seen, near, mine in P.homes(interior):
        for i in sorted(mine - near):
            goal = rooms[i]
            if goal.type not in GOALS:
                continue
            reach = [rooms[j] for j in sorted(seen) if rooms[j].floor == goal.floor]
            for x in sorted((rooms[j] for j in mine if rooms[j].floor == goal.floor and rooms[j].type in HOSTS
                             and j not in seen and j != i), key=lambda r: r.id):
                for s in reach:
                    pairs = [(seg, goal) for seg in pieces_between(interior, s, x)]
                    if not pairs:
                        continue
                    pairs += [(seg, s) for seg in pieces_between(interior, goal, x)]
                    into = s.id if s.type in GROW else (goal.id if goal.type in GROW else None)
                    for seg, to in pairs:
                        got = band(x.polygon, seg, to.polygon, wide, STEP, most, over)
                        out += [(b, x.id, goal.id, into) for b in got]
    return sorted(out, key=lambda t: (round(t[0].area, 4), t[1], t[2], -1 if t[3] is None else t[3]))


def cut(interior, strip: Polygon, host_id: int, into, scrap: float = 0.0) -> bool:
    """The hall or couloir `into` (a new couloir when None) takes `strip` of the chambre, cuisine or sdb
    `host_id`, which keeps one piece over its minimum and a window of its own (no stair on the strip; a window
    there lights the couloir); pieces of it left beside the strip up to `scrap` m2 go with the strip. The
    host's doors on the strip go and `rooms.connect` places what is needed again. False (nothing changed)
    when it cannot."""
    from dataclasses import replace
    from . import rooms as R
    rooms = {r.id: r for r in interior.rooms}
    host = rooms[host_id]
    f = host.floor
    if any(s.polygon.intersection(strip).area > 1e-3 for s in interior.stairs if s.floor <= f <= s.top):
        return False
    rest = set_precision(host.polygon.difference(strip), GRID)
    parts = sorted((g for g in getattr(rest, "geoms", [rest]) if g.geom_type == "Polygon" and g.area > 1e-4),
                   key=lambda g: -g.area)
    if not parts or any(g.area > scrap for g in parts[1:]):
        return False
    rest = parts[0]                                   # scraps beside the strip join the couloir
    gone = set_precision(unary_union([strip, *parts[1:]]), GRID)
    grown = one(set_precision(unary_union([rooms[into].polygon, gone]), GRID)) if into is not None else one(gone)
    holes = 0 if into is None else len(rooms[into].polygon.interiors)
    if grown is None or len(grown.interiors) > holes or len(rest.interiors) > len(host.polygon.interiors):
        return False
    if necks(grown) > (1 if into is None else max(1, necks(rooms[into].polygon))):
        return False                                  # joined by a hair: no way a person walks
    least = interior.rules["minimums"].get(host.type, (0.0, 0.0))
    if rest.area < least[0] or least_width(rest) < least[1]:
        return False
    ops = [o for o in interior.openings if host.id in o.rooms and o.floor == f]
    off = [o for o in ops if gone.distance(Point(o.x, o.y)) < rest.distance(Point(o.x, o.y)) - 1e-3]
    lights = [o for o in off if o.kind not in R.PASS]
    if lights and not any(o.kind in LIGHTS and all(o is not g for g in off) for o in ops):
        return False                                  # the host keeps a window of its own
    host.polygon = rest
    if into is None:
        into = R.next_id(interior)
        interior.rooms.insert(interior.rooms.index(host) + 1, replace(host, id=into, type="couloir", polygon=grown,
                                                                      alcove=None, lit=False))
    else:
        rooms[into].polygon = grown
    for o in lights:                                  # a window on the strip lights the couloir
        o.rooms = tuple(into if i == host.id else i for i in o.rooms)
    interior.openings = [o for o in interior.openings if o.kind not in R.PASS or all(o is not g for g in off)]
    R.renumber(interior)
    R.connect(interior)
    R.renumber(interior)
    return True
