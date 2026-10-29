"""Doors between rooms, facade openings in their rooms, and every check of a plan (SPEC 6c "Layout engine").

`doors` places the doors a program wants, then connects every room it did not reach from the street (a
door to a reached neighbour, else a merge into it). `check` holds every rule the tests and tools share:
coverage, overlaps, reachability, minimum sizes, partitions clear of openings, facade openings in rooms,
headroom, and for a courtyard house that the bent skifa hides the court.
"""
from __future__ import annotations

import math

import numpy as np
import shapely
from shapely.geometry import LinearRing, LineString, Point, Polygon
from shapely.prepared import prep
from shapely.strtree import STRtree

from .cuts import TOUCH, contact, lines_of, near, shared, straight, union, width, zone
from .model import Opening

FACADE = ("door", "window", "balcony", "shop")      # openings in the exterior walls
PASS = ("door", "shop", "inner", "court_door", "arch")   # openings a person walks through
COURT = "wast_ed_dar"
VOIDS = ("well",)                                   # no floor: a covered court's light well upstairs
KEEP = ("droj", COURT, "well", "stah", "menzah", "skifa", "palier", "hall", "couloir", "koubba", "hanout",
        "makhzen", "qahwa")   # rooms nothing merges into or out of
WAYS = {"palier", "hall", "couloir"}   # a repair never lets a way in swallow a room (prompt 47)
RANK = ("salon", "salle_a_manger", "cuisine", "chambre")   # which modern room a merge keeps, first first
TOLERANCE = 0.01    # meters: how far a partition's face may reach into an opening's `clear` (rounding)


def court_room(interior, floor: int = 0):
    """The open court of a courtyard house (outside the storey polygon), or None."""
    return next((r for r in interior.rooms if r.type == COURT and r.open), None)


def next_id(interior) -> int:
    """A room id no room has (merges leave gaps; `renumber` closes them at the end)."""
    return max((r.id for r in interior.rooms), default=-1) + 1


def is_court(r) -> bool:
    return r.type == COURT and r.open


def joinable(a, b) -> bool:
    """True when a door may join rooms a and b: the same unit, or a common stair core and a home or flat
    (a shop or cafe opens only on the street and into its own rooms)."""
    if a.unit == b.unit:
        return True
    units = {a.unit, b.unit}
    return "common" in units and not units & {"shop", "cafe"}


def court_ring(interior, floor: int):
    """The court-side face ring of the rooms of `floor` (the storey's hole holding the court), or None."""
    court = court_room(interior)
    if court is None or floor >= interior.floors:
        return None
    pt = court.polygon.representative_point()
    whole = getattr(interior, "full0", None) if floor == 0 else None     # a souk house's floor 0 with its shop
    for ring in (whole or interior.storeys[floor].polygon).interiors:
        if Polygon(ring).contains(pt):
            return ring
    return None


def pieces_between(interior, a, b) -> list:
    """Straight pieces of the boundary rooms a and b share; with b the open court, a's pieces on the
    court wall's room face."""
    if is_court(b):
        ring = court_ring(interior, a.floor)
        if ring is None:
            return []
        return straight(lines_of(a.polygon.boundary.intersection(LinearRing(ring).buffer(TOUCH, quad_segs=1))))
    if a.floor != b.floor:
        return []
    return contact(a.polygon, b.polygon)


def court_face(court_poly, point) -> tuple:
    """(point on the court's face nearest `point`, its segment ((ax, ay), (bx, by)), s along it)."""
    ring = np.asarray(court_poly.exterior.coords)[:, :2]
    p = np.asarray(point, dtype=float)
    best = None
    for a, b in zip(ring[:-1], ring[1:]):
        d = b - a
        n = float(d @ d)
        if n < 1e-12:
            continue
        t = min(max(float((p - a) @ d) / n, 0.0), 1.0)
        q = a + d * t
        dist = float(np.hypot(*(q - p)))
        if best is None or dist < best[0] - 1e-9:
            best = (dist, q, ((float(a[0]), float(a[1])), (float(b[0]), float(b[1]))), t * math.sqrt(n))
    return best[1], best[2], best[3]


def yaw_of(front) -> float:
    """The yaw whose piece front (-sin yaw, cos yaw) is `front`."""
    return math.atan2(-float(front[0]), float(front[1]))


def opening(interior, a, b, kind: str, center, front, width: float, z0: float, z1: float) -> Opening:
    """An opening of room a toward b (a room, or the open court: then on the court's face) at `center` on
    a's boundary, `front` pointing from a toward b."""
    x, y = float(center[0]), float(center[1])
    wall, s = None, 0.0
    if is_court(b):
        q, wall, s = court_face(b.polygon, center)
        x, y = float(q[0]), float(q[1])
    o = Opening(len(interior.openings), kind, x, y, yaw_of(front), width, z0, z1, a.floor, (a.id, b.id), wall, s)
    interior.openings.append(o)
    return o


def front_toward(a, b, piece) -> np.ndarray:
    """Unit normal of `piece` pointing from room a toward b."""
    p0, p1 = np.asarray(piece[0]), np.asarray(piece[1])
    d = (p1 - p0) / max(float(np.hypot(*(p1 - p0))), 1e-12)
    n = np.array([-d[1], d[0]])
    mid = (p0 + p1) / 2
    probe = Point(*(mid + n * 0.05))
    return n if not a.polygon.contains(probe) else -n


def place(interior, a, b, kind: str, width: float, height: float, on=None, sill: float = 0.0,
          at=None, clear: float | None = None) -> Opening | None:
    """A door or window of `width` between rooms a and b: in the middle of the longest straight piece of
    their shared boundary that holds width + 2 x (clear + half a partition) (only pieces along `on` when
    given), or at the point `at` on it. None when no piece holds it."""
    rules = interior.rules
    clear = rules["clear"] if clear is None else clear
    side = rules["partition"] if kind.startswith("court") else rules["partition"] / 2   # an oblique partition's face
    need = width + 2 * (clear + side)
    best = None
    for piece in pieces_between(interior, a, b):
        length = math.dist(*piece)
        if on is not None and LineString(on).distance(Point(*np.add(piece[0], piece[1]) / 2)) > 0.05:
            continue
        if at is not None:
            line = LineString(piece)
            t = line.project(Point(*at))
            room = width / 2 + clear + side
            if line.distance(Point(*at)) < 0.02 and room - 1e-6 <= t <= length - room + 1e-6:
                best = (length, piece)
                break
            continue
        if length >= need - 1e-9 and (best is None or length > best[0] + 1e-9):
            best = (length, piece)
    if best is None:
        return None
    piece = best[1]
    center = np.asarray(at, dtype=float) if at is not None else (np.asarray(piece[0]) + np.asarray(piece[1])) / 2
    z = a.z
    return opening(interior, a, b, kind, center, front_toward(a, b, piece), width, z + sill, z + sill + height)


def assign(interior) -> None:
    """Every facade opening into the room just inside its wall (rooms = (room, -1))."""
    ext = interior.walls["exterior"]
    for o in interior.openings:
        if o.kind not in FACADE or o.rooms[0] >= 0:
            continue
        inward = np.array([math.sin(o.yaw), -math.cos(o.yaw)])
        probe = Point(*(np.array([o.x, o.y]) + inward * (ext + 0.1)))
        cands = [r for r in interior.rooms if r.floor == o.floor and not is_court(r) and r.type not in VOIDS]
        if not cands:
            continue
        r = min(cands, key=lambda r: (0 if r.polygon.contains(probe) else 1, r.polygon.distance(probe), r.id))
        o.rooms = (r.id, -1)
        if r.polygon.distance(probe) > ext + 0.1:
            interior.warnings.append(f"the {o.kind} {o.piece} at ({o.x:.2f}, {o.y:.2f}) opens on a stretch of wall "
                                     "with no floor behind it (a neck thinner than two walls): it lights the nearest room")


def clash(interior, a, b, zones: list) -> bool:
    """True when the partition of rooms a and b (less the openings between them) meets a wall within
    `clear` of an opening (`zones`)."""
    rules = interior.rules
    gaps = [gap(o, rules) for o in interior.openings if set(o.rooms) == {a.id, b.id}] + list(interior.piers)
    return clash_polys(a.polygon, b.polygon, zones, rules["partition"], gaps)


def clash_polys(a, b, zones: list, partition: float, gaps=()) -> bool:
    """`clash` for two polygons (`gaps`: the openings between them)."""
    if not zones or not near(a, b) or a.distance(b) > TOUCH:
        return False
    for piece in contact(a, b):
        line = LineString(piece)
        for g in gaps:
            line = line.difference(g)
        if line.is_empty or line.length < 1e-3:
            continue
        strip = line.buffer(partition / 2, cap_style="flat")
        if (shapely.area(shapely.intersection(strip, zones)) > TOLERANCE * partition).any():
            return True
    return False


def repair(interior, zones: dict) -> None:
    """Rooms whose partition meets a wall too near a facade opening become one room (the cut dropped):
    the smaller joins the larger, a stair cell or skifa takes its neighbour."""
    for f, zs in sorted(zones.items()):
        zs = [z for z in zs if z is not None]
        if not zs:
            continue
        for _ in range(len(interior.rooms)):
            rooms = [r for r in interior.rooms if r.floor == f and not is_court(r) and r.type not in VOIDS
                     and any(near(r.polygon, z) for z in zs)]   # only rooms reaching a zone can clash
            pair = next(((a, b) for i, a in enumerate(rooms) for b in rooms[i + 1:]
                         if a.unit == b.unit and not (a.type in KEEP and b.type in KEEP)
                         and not ({a.type, b.type} & WAYS and not {a.type, b.type} <= WAYS | set(KEEP))
                         and clash(interior, a, b, zs)), None)
            if pair is None:
                break
            a, b = pair
            keep, gone = (a, b) if (a.type in KEEP or (b.type not in KEEP and a.polygon.area >= b.polygon.area)) else (b, a)
            if keep.type in RANK and gone.type in RANK and RANK.index(gone.type) < RANK.index(keep.type):
                keep, gone = gone, keep                   # a modern home keeps its salon, then its other rooms
            if not merge(interior, keep, gone):
                break


def unclash(interior) -> None:
    """Court openings too near a partition (one standing at a slant or along the wall) give way: they
    are removed and the doors pass places what is still needed."""
    rules = interior.rules
    gone = set()
    for f in range(interior.floors):
        rooms = [r for r in interior.rooms if r.floor == f and not is_court(r)]
        mine = [(o, zone(o, rules["court"], rules["clear"])) for o in interior.openings
                if o.floor == f and o.kind in ("court_door", "court_window")]
        if not mine:
            continue
        everything = [z for _, z in mine]
        for i, a in enumerate(rooms):
            for b in rooms[i + 1:]:
                if clash(interior, a, b, everything):
                    gone.update(id(o) for o, z in mine if clash(interior, a, b, [z]))
    if gone:
        interior.openings = [o for o in interior.openings if id(o) not in gone]
        connect(interior)


def links(interior) -> dict:
    """Room id -> the room ids (and -1, the street) a person reaches in one step."""
    out: dict = {r.id: set() for r in interior.rooms}
    out[-1] = set()

    def link(a, b):
        out.setdefault(a, set()).add(b)
        out.setdefault(b, set()).add(a)

    for o in interior.openings:
        if o.kind in PASS:
            link(o.rooms[0], o.rooms[1])
    for s in interior.stairs:
        if s.kind == "steps":
            continue
        for a, b in zip(s.rooms[:-1], s.rooms[1:]):
            link(a, b)
    return out


def reached(interior) -> set:
    """Room ids reached from the street (-1) through doors, arches and stairs."""
    graph = links(interior)
    seen, todo = {-1}, [-1]
    while todo:
        n = todo.pop()
        for m in sorted(graph.get(n, ())):
            if m not in seen:
                seen.add(m)
                todo.append(m)
    return seen


def merge(interior, keep, gone) -> bool:
    """Room `gone` joins room `keep` (which keeps its type); openings and stairs follow. False when the
    two only meet at a point."""
    poly = union(keep.polygon, gone.polygon)
    if poly is None:
        return False
    keep.polygon = poly
    keep.lit = keep.lit or gone.lit
    big = {k: v for k, v in interior.rules.get("largest", {}).items() if k != "skifa"}
    if keep.type in big and (gone.type == "bit" or poly.area > big[keep.type] + 0.01):
        old = interior.layout in ("dar", "compact", "small", "koubba")
        keep.type = "bit" if old else "chambre"       # a merge never grows a service past its largest
    interior.openings = [o for o in interior.openings if set(o.rooms) != {keep.id, gone.id}]
    for o in interior.openings:
        o.rooms = tuple(keep.id if r == gone.id else r for r in o.rooms)
    for s in interior.stairs:
        s.rooms = [keep.id if r == gone.id else r for r in s.rooms]
    interior.rooms = [r for r in interior.rooms if r is not gone]
    return True


def neighbours(interior, r) -> list:
    """(shared length, room) of every room next to r on its floor (the open court through its wall)."""
    out = []
    court = court_room(interior)
    for o in interior.rooms:
        if o is r:
            continue
        if o.floor == r.floor:
            s = shared(r.polygon, o.polygon)
        elif o is court and r.floor == 0:
            s = sum(math.dist(*p) for p in pieces_between(interior, r, o))
        else:
            continue
        if s > 1e-3:
            out.append((s, o))
    return out


def connect(interior) -> None:
    """Give every room the street does not reach a door to its reached neighbour with the longest piece
    that holds one, else merge it into that neighbour; repeated until nothing changes. Where neither
    works, a narrow door (`narrow` wide, `narrow_clear` from the partitions) on the longest piece."""
    rules = interior.rules
    clear = rules.get("inner_clear", rules["clear"])   # modern homes: `inner_clear` (prompt 47)
    _connect(interior, rules["door"], clear, False)
    _connect(interior, rules.get("narrow", 0.7), rules.get("narrow_clear", 0.05), False)
    _connect(interior, rules.get("narrow", 0.7), 0.0, False)
    _connect(interior, rules["door"], clear, True)
    _connect(interior, rules["door"], clear, True, last=True)


def _connect(interior, door: float, clear: float, merging: bool, last: bool = False) -> None:
    """One doors pass; `last`: a room still cut off joins any neighbour that is no void nor open court
    (a stair cell or skifa too, the reached first), so groups coalesce and get their door."""
    rules = interior.rules
    for _ in range(len(interior.rooms) + 1):
        seen = reached(interior)
        todo = [r for r in interior.rooms if r.id not in seen and r.type not in VOIDS]
        if not todo:
            return
        changed = False
        for r in todo:
            near = sorted(neighbours(interior, r), key=lambda t: (-t[0], t[1].id))
            done = False
            for _, n in near:
                if n.id in seen and n.type not in VOIDS and joinable(r, n):
                    kind = "court_door" if is_court(n) else "inner"
                    if place(interior, r, n, kind, door, rules["door_height"], clear=clear) is not None:
                        done = True
                        break
            if not done and merging:
                for _, n in near:
                    if (n.id in seen and n.type not in KEEP and n.type not in VOIDS and r.type not in KEEP
                            and n.unit == r.unit):
                        done = merge(interior, n, r)
                        if done:
                            break
            if not done and last and r.type == COURT and not r.open:
                r.type = "bit"                        # a covered court nobody reaches is a plain room
            if not done and last and r.type not in KEEP:
                for _, n in sorted(near, key=lambda t: (t[1].id not in seen, t[1].type in KEEP, -t[0], t[1].id)):
                    if (n.type not in VOIDS and not is_court(n) and n.type not in ("stah", "menzah", "droj")
                            and n.unit == r.unit and n.type not in ("palier", "hall", "couloir")):
                        done = merge(interior, n, r)
                        if done:
                            break
            if done:
                changed = True
                break                       # the graph changed: look again
        if not changed:
            return


def renumber(interior) -> None:
    """Room and opening ids as their positions, every reference following."""
    ids = {r.id: i for i, r in enumerate(interior.rooms)}
    ids[-1] = -1
    for i, r in enumerate(interior.rooms):
        r.id = i
    for i, o in enumerate(interior.openings):
        o.id = i
        o.rooms = tuple(ids.get(r, -1) for r in o.rooms)
    for s in interior.stairs:
        s.rooms = [ids.get(r, -1) for r in s.rooms]
    if interior.focus is not None:
        room, op = interior.focus
        interior.focus = (ids.get(room, -1), op)


# --- checks ---------------------------------------------------------------------------------------
def gap(o, rules: dict):
    """The free passage of an opening through its wall, half a partition into the rooms on both sides."""
    front = np.array([-math.sin(o.yaw), math.cos(o.yaw)])
    half = rules["partition"] / 2 + 0.02
    if o.kind in ("inner", "arch", "inner_window"):
        depth = half
    elif o.kind in ("court_door", "court_window"):
        depth = rules["court"] + half
    else:
        depth = rules["exterior"] + half
    return slot((o.x, o.y), front, o.width, half, depth)


def slot(center, front, width: float, out: float, depth: float):
    """A rectangle `width` wide across a wall at `center`: `out` m along `front`, `depth` m against it."""
    front = np.asarray(front, dtype=float)
    along = np.array([front[1], -front[0]])
    c = np.asarray(center, dtype=float)
    w = along * width / 2
    return Polygon([c - w + front * out, c + w + front * out, c + w - front * depth, c - w - front * depth])


def zones_of(interior, floor: int) -> list:
    """The no-partition zones of every facade and court opening of a floor."""
    rules = interior.rules
    out = []
    for o in interior.openings:
        if o.floor != floor or o.wall is None:
            continue
        t = rules["court"] if o.kind in ("court_door", "court_window") else rules["exterior"]
        z = zone(o, t, rules["clear"])
        if z is not None:
            out.append(z)
    return out


def sees_court(interior) -> bool:
    """True when a straight line from the main door's inner face reaches a court point (1 m grid) inside
    the rooms of floor 0 (each shrunk by half a partition), their door gaps and the court."""
    court = court_room(interior)
    if court is None:
        return False
    door = interior.entry
    if door is None or door not in interior.openings:
        return False
    rules = interior.rules
    rooms = [r.polygon for r in interior.rooms if r.floor == 0 and r is not court]
    gaps = [gap(o, rules) for o in interior.openings if o.floor == 0 and o.kind in PASS + ("court_window",)]
    return seen(door_points(door, rules["exterior"]), court.polygon, rooms, gaps, rules["partition"] / 2)


def door_points(door, ext: float) -> list:
    """Three points across a facade door's inner face."""
    along = np.array([math.cos(door.yaw), math.sin(door.yaw)])
    inward = np.array([math.sin(door.yaw), -math.cos(door.yaw)])
    face = np.array([door.x, door.y]) + inward * (ext + 0.01)
    return [face + along * t for t in (-door.width / 2 + 0.05, 0.0, door.width / 2 - 0.05)]


def seen(starts: list, court, rooms: list, gaps: list, half: float) -> bool:
    """True when a segment from a start point to a court point of the 1 m grid stays inside the rooms
    (each shrunk by `half`), the gaps and the court."""
    free = [r.buffer(-half, join_style="mitre") for r in rooms] + list(gaps) + [court]
    free = prep(shapely.union_all(free))
    x0, y0, x1, y1 = court.bounds
    grid = [(x, y) for x in np.arange(math.floor(x0), x1 + 1) for y in np.arange(math.floor(y0), y1 + 1)]
    ends = [p for p in grid if court.contains(Point(p))] or [court.representative_point().coords[0]]
    return any(free.covers(LineString([s, e])) for s in starts for e in ends)


def check(interior) -> list:
    """Every problem of a plan, in plain words (an empty list: the plan is valid)."""
    out: list = []
    for st in interior.storeys:
        out += _coverage(interior, st)
    for f in sorted({r.floor for r in interior.rooms}):
        out += _overlaps(interior, f)
        if f < interior.floors:                       # roof rooms stand free: their walls are no partitions
            out += _partitions(interior, f)
    out += _sizes(interior)
    out += _facade(interior)
    out += _reach(interior)
    out += _units(interior)
    out += _headroom(interior)
    if interior.layout == "dar" and sees_court(interior):
        out.append("the court can be seen from the street door")
    from .program import problems
    return out + problems(interior)


def _coverage(interior, st) -> list:
    rooms = [r.polygon for r in interior.rooms if r.floor == st.floor and not is_court(r)]
    if not rooms:
        return [f"floor {st.floor} has no room"]
    got = shapely.union_all(rooms)
    miss = st.polygon.symmetric_difference(got).area
    if miss > 0.005 * st.polygon.area:
        return [f"floor {st.floor}: the rooms leave {miss:.2f} m2 of the storey uncovered or spill out of it"]
    return []


def _overlaps(interior, floor: int) -> list:
    rooms = [r for r in interior.rooms if r.floor == floor]
    tree = STRtree([r.polygon for r in rooms])
    out = []
    for i, r in enumerate(rooms):
        for j in tree.query(r.polygon):
            j = int(j)
            if j > i and r.polygon.intersection(rooms[j].polygon).area > 0.01:
                out.append(f"rooms {r.id} ({r.type}) and {rooms[j].id} ({rooms[j].type}) overlap on floor {floor}")
    return out


def _partitions(interior, floor: int) -> list:
    """No partition meets a wall within `clear` of an opening of that floor on that wall."""
    rules = interior.rules
    zones = zones_of(interior, floor)
    rooms = [r for r in interior.rooms if r.floor == floor and not is_court(r)
             and any(near(r.polygon, z) for z in zones)]
    return [f"the partition of rooms {a.id} ({a.type}) and {b.id} ({b.type}) meets a wall within "
            f"{rules['clear']} m of an opening on floor {floor}"
            for i, a in enumerate(rooms) for b in rooms[i + 1:] if clash(interior, a, b, zones)]


def _sizes(interior) -> list:
    """Rooms under their type's minimum that a neighbour could have taken."""
    rules = interior.rules
    least = rules["minimums"]
    out = []
    for r in interior.rooms:
        if r.type in KEEP or r.type in VOIDS or r.type not in least:
            continue
        area_min, width_min = least[r.type]
        if r.polygon.area >= area_min - 1e-6 and width(r.polygon) >= width_min - 0.03:
            continue
        if any(n.type not in KEEP and n.type not in VOIDS and not is_court(n) for _, n in neighbours(interior, r)):
            out.append(f"room {r.id} ({r.type}, {r.polygon.area:.1f} m2) is under its minimum")
    for f in sorted({r.floor for r in interior.rooms if r.type == "skifa"}):
        area = sum(r.polygon.area for r in interior.rooms if r.type == "skifa" and r.floor == f)
        if area < least.get("skifa", (0, 0))[0] - 1e-6:
            out.append(f"the skifa of floor {f} has {area:.1f} m2")
    return out


def _facade(interior) -> list:
    ext = interior.walls["exterior"]
    by_id = {r.id: r for r in interior.rooms}
    out = []
    for o in interior.openings:
        if o.kind not in FACADE:
            continue
        r = by_id.get(o.rooms[0])
        if r is None or r.floor != o.floor:
            out.append(f"the {o.kind} {o.id} ({o.piece}) is in no room of its floor")
            continue
        inward = np.array([math.sin(o.yaw), -math.cos(o.yaw)])
        probe = Point(*(np.array([o.x, o.y]) + inward * (ext + 0.1)))
        cands = [x for x in interior.rooms if x.floor == o.floor and not is_court(x) and x.type not in VOIDS]
        near = min(cands, key=lambda x: (0 if x.polygon.contains(probe) else 1, x.polygon.distance(probe), x.id))
        if near is not r:
            out.append(f"the {o.kind} {o.id} ({o.piece}) is not in the room behind its wall")
    return out


def _reach(interior) -> list:
    seen = reached(interior)
    out = [f"room {r.id} ({r.type}, floor {r.floor}) cannot be reached" for r in interior.rooms
           if r.id not in seen and r.type not in VOIDS]
    for o in interior.openings:
        if o.rooms[0] not in seen and o.rooms[0] >= 0 and o.kind in PASS:
            out.append(f"the {o.kind} {o.id} opens from a room nobody reaches")
    for s in interior.stairs:
        if any(r not in seen for r in s.rooms):
            out.append(f"the {s.kind} stair from floor {s.floor} stands in a room nobody reaches")
    return out


def _units(interior) -> list:
    """Doors join rooms of one unit (or a stair core and a home or flat); the shop and cafe fronts open into
    their shop or cafe, the doors into the home or the core."""
    by_id = {r.id: r for r in interior.rooms}
    out = []
    for o in interior.openings:
        if o.kind not in PASS:
            continue
        a, b = by_id.get(o.rooms[0]), by_id.get(o.rooms[1])
        if a is not None and b is not None and not joinable(a, b):
            out.append(f"the {o.kind} {o.id} joins {a.type} ({a.unit}) and {b.type} ({b.unit})")
        if a is not None and o.rooms[1] == -1 and o.kind in ("door", "shop"):
            if (o.kind == "shop") != (a.unit in ("shop", "cafe")):
                out.append(f"the {o.kind} {o.id} ({o.piece}) opens into the {a.type} ({a.unit})")
    return out


def _headroom(interior) -> list:
    rules = interior.rules
    out = []
    for s in interior.stairs:
        if s.kind != "newel":
            continue
        if interior.fh - rules["slab"] < rules["headroom"]:
            out.append(f"the newel stair has {interior.fh - rules['slab']:.2f} m of headroom")
        if s.top >= interior.floors and rules["stair_height"] - rules["roof_ceiling"] < rules["headroom"]:
            out.append("the stair room is too low over the roof landing")
    return out
