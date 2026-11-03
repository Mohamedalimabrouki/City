"""Furnishing (prompt 54, SPEC 6d "Places", "Keep-outs and clearances", "Fit", "Density", "Checks").

`furnish(interior, outside, style, density)` reads a finished plan (it never changes a room) and places the
home kit's pieces room by room, slot by slot, from the recipes `[[interiors.furnish.rooms.<function>]]`.
Every room is prepared once as a `RoomSpace` (its free floor F, its wall runs with their openings, its main
door, its hub, its keep-outs and its walk strips); every slot draws exactly four numbers on its own stream
before any test, so a new slot never moves another and a lower density is a subset of a higher one.
`check(interior, furniture, style)` tests a finished furnishing as the tests and surveys do.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import shapely
from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.ops import polylabel, unary_union
from shapely.prepared import prep

from ..rng import stream
from . import household as H
from .floors import slab
from .homekit import home_kit
from .rooms import PASS

DENSITIES = ("sparse", "lived-in", "full")
WINDOWS = ("window", "court_window", "inner_window")
DOORS = PASS + ("balcony",)
TOL_AREA = 1e-4
FORMAT = "citygen-furniture/1"
NEED_SLACK = 2000   # triangles a room may pass its budget by: need slots are never skipped for it
DEBUG = None   # a dict to count why poses fail (surveys)


# --- small geometry helpers -------------------------------------------------------------------------------
def polygons(g) -> list:
    if g is None or g.is_empty:
        return []
    if isinstance(g, Polygon):
        return [g]
    if isinstance(g, MultiPolygon):
        return list(g.geoms)
    return [p for p in getattr(g, "geoms", []) if isinstance(p, Polygon)]


def frame_poly(pts, x: float, y: float, yaw: float, sx: float = 1.0) -> Polygon:
    """An outline in a piece's frame (x along its wall, front +y), scaled sx along x, at a pose."""
    c, s = math.cos(yaw), math.sin(yaw)
    a = np.asarray(pts, dtype=float)
    px, py = a[:, 0] * sx, a[:, 1]
    return shapely.polygons(np.column_stack([x + px * c - py * s, y + px * s + py * c]))


def yaw_facing(n) -> float:
    """The yaw whose front (-sin yaw, cos yaw) is the direction n."""
    return math.atan2(-n[0], n[1])


def tags_hold(expr, tags: set) -> bool:
    """A tag expression: every word must hold, `!word` must not, `a|b` either."""
    if not expr:
        return True
    for word in str(expr).split():
        if word.startswith("!"):
            if word[1:] in tags:
                return False
        elif not any(w in tags for w in word.split("|")):
            return False
    return True


# --- the room prepared -----------------------------------------------------------------------------------
@dataclass
class Run:
    a: np.ndarray
    d: np.ndarray          # unit direction a -> b
    n: np.ndarray          # inward normal
    length: float
    ops: list              # (s0, s1, z0, z1, kind) relative to the room floor
    index: int

    def point(self, s: float) -> np.ndarray:
        return self.a + self.d * s

    def clear(self, s0: float, s1: float, top: float, margin: float = 0.0, z0: float = 0.0) -> bool:
        """No opening over [s0, s1] (grown by margin) whose height range meets [z0, top]."""
        return not any(o0 - margin < s1 and o1 + margin > s0 and oz0 - margin < top and oz1 + margin > z0
                       for o0, o1, oz0, oz1, _ in self.ops)

    @property
    def blind(self) -> bool:
        return not self.ops


@dataclass
class RoomSpace:
    room: object
    F: object
    Fp: object
    Fgrown: object
    runs: list
    door: object           # (x, y) inner point of the main door
    door_op: object        # the main door's Opening (or None for a stair)
    inner: list            # inner points of every way in or out
    hub: tuple
    keeps: list            # (polygon, z0, z1, kind)
    ceiling: float
    yaw: float             # the room's frame
    base: list = None      # the empty room's walkable parts (`reaches`)


@dataclass
class Placed:
    piece: str
    x: float
    y: float
    z: float               # over the room floor
    yaw: float
    stretch: float
    room: int
    unit: str
    role: str
    slot: int
    foot: object
    z0: float
    z1: float
    cat: str
    anchor: str
    host: int = -1         # index of the host piece (`on`, `front`, `around`, `under`, `beside`)
    group: int = -1        # the set it belongs to (its own index for a first piece)
    run: int = -1
    s: float = 0.0
    width: float = 0.0
    use: object = None
    density: str = "sparse"
    places: int = 0        # sleeping places
    part: bool = False     # a set's own part (a doukkana's mattress and cushions)
    lazy: bool = False     # its use strips are made when the fit test reaches them
    idx: int = -1          # its index in the placing order

    def to_json(self, room_z: float) -> dict:
        return {"piece": self.piece, "x": round(self.x, 3), "y": round(self.y, 3), "z": round(room_z + self.z, 3),
                "yaw": round(self.yaw, 4), "stretch": round(self.stretch, 3), "room": self.room, "unit": self.unit,
                "role": self.role, "slot": self.slot, "host": self.host, "density": self.density}


@dataclass
class Furniture:
    density: str
    period: str
    profiles: dict
    functions: dict
    pieces: list
    warnings: list
    room_z: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        return {"format": FORMAT, "density": self.density, "period": self.period,
                "profiles": {u: p.to_json() for u, p in self.profiles.items()},
                "functions": {str(k): v for k, v in self.functions.items()},
                "pieces": [p.to_json(self.room_z[p.room]) for p in self.pieces], "warnings": list(self.warnings)}


def settings(style: dict) -> dict:
    return style.get("interiors", {}).get("furnish", {})


def side_of(o, room) -> np.ndarray:
    """The unit normal of opening o pointing into `room`."""
    f = np.array([-math.sin(o.yaw), math.cos(o.yaw)])
    p = Point(o.x + 0.3 * f[0], o.y + 0.3 * f[1])
    return f if room.polygon.contains(p) else -f


def face_of(interior, o, n) -> float:
    """Meters from the opening's center to its wall's face on the side n points to."""
    from .mesh import depths
    d0, d1 = depths(interior, o)
    front = np.array([-math.sin(o.yaw), math.cos(o.yaw)])
    return -d0 if float(n @ front) < 0 else d1


def main_doors(interior) -> dict:
    """Room id -> ("op", Opening) or ("stair", Stair): how the walk from the street first reaches it."""
    out, seen, todo = {}, {-1}, [-1]
    ops = sorted((o for o in interior.openings if o.kind in PASS), key=lambda o: o.id)
    stairs = [s for s in interior.stairs if s.kind != "steps"]
    while todo:
        n = todo.pop(0)
        for o in ops:
            if n in o.rooms:
                m = o.rooms[1] if o.rooms[0] == n else o.rooms[0]
                if m not in seen:
                    seen.add(m)
                    out[m] = ("op", o)
                    todo.append(m)
        for s in stairs:
            if n in s.rooms:
                for m in s.rooms:
                    if m not in seen:
                        seen.add(m)
                        out[m] = ("stair", s)
                        todo.append(m)
    return out


class Prepared:
    """Per-interior caches: the slab of each floor, the main doors, the room spaces."""

    def __init__(self, interior, outside, style):
        self.interior, self.outside, self.style = interior, outside, style
        self.cfg = settings(style)
        self.doors = main_doors(interior)
        self._slabs: dict = {}
        self._spaces: dict = {}
        self._boxes: dict = {}
        self._trees: dict = {}
        self.by_id = {r.id: r for r in interior.rooms}

    def slab(self, f: int):
        if f not in self._slabs:
            try:
                self._slabs[f] = slab(self.interior, f, self.style, self.outside)
            except Exception:
                self._slabs[f] = None
        return self._slabs[f]

    def free_of(self, room):
        """`floors.free_of` with only the rooms that touch it (the same floor, a tree per storey)."""
        f = room.floor
        if f not in self._trees:
            rooms = [r for r in self.interior.rooms if r.floor == f]
            self._trees[f] = (rooms, shapely.STRtree([r.polygon for r in rooms]))
        rooms, tree = self._trees[f]
        half = self.interior.walls["partition"] / 2
        near = [rooms[j].polygon for j in sorted(tree.query(room.polygon, predicate="dwithin", distance=2 * half + 0.05).tolist())
                if rooms[j] is not room]
        if not near:
            return room.polygon
        return room.polygon.difference(unary_union(near).buffer(half, join_style="mitre"))

    def space(self, room) -> RoomSpace:
        if room.id not in self._spaces:
            self._spaces[room.id] = self._make(room)
        return self._spaces[room.id]

    def _make(self, room) -> RoomSpace:
        it, cfg = self.interior, self.cfg
        gap = float(cfg.get("wall_gap", 0.01))
        poly = room.polygon if room.type == "wast_ed_dar" else self.free_of(room)
        if room.floor > 0 and not room.open:
            s = self.slab(room.floor)
            if s is not None and not s.is_empty:
                poly = poly.intersection(s)
        F = unary_union([p for p in polygons(poly.buffer(-gap, join_style="mitre")) if p.area > 0.05])
        F = shapely.set_precision(F, 1e-4) if not F.is_empty else F
        ops = [o for o in it.openings if room.id in o.rooms and o.kind != "skylight"]
        runs = self._runs(F, room, ops)
        modern = it.layout not in H.TRAD
        keeps, inner = self._keeps(room, ops, F)
        hub = (0.0, 0.0)
        if not F.is_empty:
            big = max(polygons(F), key=lambda p: p.area)
            c = polylabel(big, tolerance=0.05)
            hub = (c.x, c.y)
        main = self.doors.get(room.id)
        door, door_op = None, None
        if main is not None and main[0] == "op":
            o = main[1]
            n = side_of(o, room)
            k = face_of(it, o, n) + 0.4
            door, door_op = (o.x + k * n[0], o.y + k * n[1]), o
        elif main is not None:
            st = main[1]
            q = (st.door[0], st.door[1]) if st.door is not None else (st.polygon.centroid.x, st.polygon.centroid.y)
            p = F.boundary.interpolate(F.boundary.project(Point(q))) if not F.is_empty else Point(q)
            door = (p.x, p.y)
        if door is None:
            door = hub
        walk = float(cfg.get("walk_modern" if modern else "walk", 0.8 if modern else 0.7))
        pts = inner or [door]
        strips = []
        hp = Point(hub)
        Fp0 = prep(F) if not F.is_empty else None
        for i, a in enumerate(pts if len(pts) > 1 else []):     # one way in: its box and the reach test suffice
            strips.append(LineString([a, hub]).buffer(walk / 2, cap_style="flat") if Point(a).distance(hp) > 0.05
                          else None)
            for b in pts[i + 1:]:
                seg = LineString([a, b])
                if Fp0 is not None and Fp0.contains(seg):
                    strips.append(seg.buffer(walk / 2, cap_style="flat"))
        for s in strips:
            if s is not None and not s.is_empty:
                keeps.append((s, 0.0, 99.0, "walk"))
        fl = style_floors(self.style)
        ceiling = 99.0 if room.open else room.height - float(fl.get("slab", 0.25)) - float(fl.get("beam", [0.1, 0.12])[1])
        rect = F.minimum_rotated_rectangle if not F.is_empty else None
        yaw = 0.0
        if rect is not None and isinstance(rect, Polygon):
            c = np.asarray(rect.exterior.coords)[:3]
            e1, e2 = c[1] - c[0], c[2] - c[1]
            e = e1 if np.hypot(*e1) >= np.hypot(*e2) else e2
            yaw = math.atan2(e[1], e[0])
        return RoomSpace(room, F, Fp0, prep(F.buffer(0.005)) if not F.is_empty else None, runs, door, door_op,
                         pts, hub, keeps, ceiling, yaw)

    def _runs(self, F, room, ops) -> list:
        tol = max(self.interior.walls.values()) + 0.12
        runs = []
        for p in polygons(F):
            for ring in (p.exterior, *p.interiors):
                pts = np.asarray(ring.coords)
                for a, b in zip(pts[:-1], pts[1:]):
                    v = b - a
                    L = float(np.hypot(*v))
                    if L <= 0.3:
                        continue
                    d = v / L
                    left = np.array([-d[1], d[0]])
                    probe = (a + b) / 2 + left * 0.02
                    n = left if F.contains(Point(probe)) else -left
                    near = []
                    for o in ops:
                        along = np.array([math.cos(o.yaw), math.sin(o.yaw)])
                        if abs(float(along @ d)) < 0.9:
                            continue
                        rel = np.array([o.x, o.y]) - a
                        if abs(float(rel @ n)) > tol:
                            continue
                        s = float(rel @ d)
                        s0, s1 = s - o.width / 2, s + o.width / 2
                        if s1 <= 0 or s0 >= L:
                            continue
                        near.append((s0, s1, o.z0 - room.z, o.z1 - room.z, o.kind))
                    runs.append(Run(a.copy(), d, n, L, sorted(near), len(runs)))
        return runs

    def _keeps(self, room, ops, F) -> tuple:
        it, cfg = self.interior, self.cfg
        door_keep = float(cfg.get("door_keep", 0.8))
        window_keep = float(cfg.get("window_keep", 0.25))
        stair_keep = float(cfg.get("stair_keep", 0.9))
        keeps, inner = [], []
        for o in ops:
            n = side_of(o, room)
            along = np.array([math.cos(o.yaw), math.sin(o.yaw)])
            c = np.array([o.x, o.y])
            face = face_of(it, o, n)
            if o.kind in DOORS:
                wide = o.width if room.type in cfg.get("wet", ()) else o.width + 0.2
                keeps.append((_box(c, along, n, wide, -0.4, face + door_keep), 0.0, 99.0, "door"))
                if o.kind in ("inner", "court_door") and _swings_into(it, o, room, self.by_id):
                    keeps.append((_swept(it, o, c, along, n, face, self.style.get("interiors", {}).get("openings", {})), 0.0, 99.0, "door"))
                inner.append(tuple(c + n * (face + 0.4)))
            elif o.kind in WINDOWS:
                keeps.append((_box(c, along, n, o.width + 0.2, -0.4, face + window_keep),
                              o.z0 - room.z - 0.03, o.z1 - room.z, "window"))
        for s in it.stairs:
            if not (room.id in s.rooms or (s.floor <= room.floor <= s.top and s.polygon.intersects(room.polygon)
                                           and s.polygon.intersection(room.polygon).area > 0.05)):
                continue
            g = s.polygon.buffer(0.1, join_style="mitre")
            if s.door is not None:
                g = g.union(Point(s.door[0], s.door[1]).buffer(stair_keep))
                q = F.boundary.interpolate(F.boundary.project(Point(s.door[0], s.door[1]))) if not F.is_empty else None
                if q is not None and room.id in s.rooms:
                    inner.append((s.door[0], s.door[1]))
            if s.kind == "ladder":
                g = g.buffer(0.6)
            keeps.append((g, 0.0, 99.0, "stair"))
        if room.type == "wast_ed_dar":
            for f in it.features:
                r = {"tree": 0.25 + float(cfg.get("tree_keep", 0.6)), "majel": 0.9,
                     "fesqiya": 1.1}.get(f["type"])
                if r is not None:
                    keeps.append((Point(f["x"], f["y"]).buffer(float(f.get("r", 0.0)) + r), 0.0, 99.0, "court"))
            mid = room.polygon.buffer(-float(cfg.get("court_keep", 1.2)))
            if not mid.is_empty:
                keeps.append((mid, 0.0, 99.0, "court"))
        for p in getattr(self.outside, "placements", ()) or ():
            if not (room.z - 0.3 <= p.z <= room.z + max(room.height, 1.0)):
                continue
            if not room.polygon.buffer(-0.05).contains(Point(p.x, p.y)):
                continue
            g = self._bridge_box(p)
            if g is not None:
                keeps.append((g, 0.0, 99.0, "bridge"))
        return keeps, inner

    def _bridge_box(self, p):
        kit = getattr(self.outside, "kit", None)
        if kit is None or p.piece not in kit.pieces:
            return None
        if p.piece not in self._boxes:
            pos = [np.asarray(part["pos"]).reshape(-1, 3) for part in kit.pieces[p.piece].parts.values()]
            if not pos:
                self._boxes[p.piece] = None
            else:
                a = np.concatenate(pos)
                self._boxes[p.piece] = (a[:, 0].min(), -a[:, 2].max(), a[:, 0].max(), -a[:, 2].min())
        b = self._boxes[p.piece]
        if b is None:
            return None
        x0, y0, x1, y1 = b
        return frame_poly(((x0, y0), (x1, y0), (x1, y1), (x0, y1)), p.x, p.y, p.yaw, p.scale * p.stretch)


def style_floors(style: dict) -> dict:
    return style.get("interiors", {}).get("floors", {})


def _swings_into(interior, o, room, by_id) -> bool:
    from .mesh import swing
    sigma = swing(interior, o)
    return (sigma > 0) == (o.rooms[1] == room.id)


def _swept(interior, o, c, along, n, face: float, ops: dict):
    """The floor a door's leaf sweeps on the room's side: a quarter disc at its hinge (both for a court door's
    two leaves), the hinge side read from the leaf's own stream as `mesh.leaves` draws it (no draw added)."""
    from .mesh import CASED
    rng = stream(interior.seed, "interior", interior.city_id, interior.building, "doors", o.id)
    opened = rng.random() < float(ops.get("open_share", 0.4))
    if opened:
        rng.uniform(0.0, 1.0)
    hinge = 1.0 if rng.random() < 0.5 else -1.0
    leaves = CASED.get(o.kind, 1)
    w = o.width / leaves
    out = []
    for side in ((hinge,) if leaves == 1 else (1.0, -1.0)):
        h = c + along * side * o.width / 2 + n * face
        disc = Point(h).buffer(w, quad_segs=8)
        quarter = Polygon([h, h - along * side * w * 1.01, h - along * side * w * 1.01 + n * w * 1.01, h + n * w * 1.01])
        out.append(disc.intersection(quarter))
    return unary_union(out)


def _box(c, along, n, width: float, d0: float, d1: float) -> Polygon:
    a = along * width / 2
    return Polygon([c - a + n * d0, c + a + n * d0, c + a + n * d1, c - a + n * d1])


# --- the furnisher ---------------------------------------------------------------------------------------
class Furnisher:
    def __init__(self, interior, outside, style, density: str):
        self.it, self.outside, self.style = interior, outside, style
        self.cfg = settings(style)
        self.density = density
        self.level = DENSITIES.index(density)
        self.kit = home_kit(interior.seed, style)
        self.prep = Prepared(interior, outside, style)
        self.placed: list = []
        self.warnings: list = []
        self.room_tris: dict = {}
        self.modern = interior.layout not in H.TRAD
        self.path = float(self.cfg.get("path_modern" if self.modern else "path", 0.6 if self.modern else 0.5))
        self.roles = self.cfg.get("roles", {})
        self.smaller = self.cfg.get("smaller", {})
        self.recipes = self.cfg.get("rooms", {})
        self.profiles = {u: H.profile(interior, u, style, outside) for u in H.units(interior)}
        self.functions = {}
        for u, prof in self.profiles.items():
            self.functions.update(H.functions(interior, u, prof))
        self.kids = self._kids()
        self._rtags: dict = {}
        self.pending: dict = {}
        self._room_of: tuple = (-1, {})
        self.cross = tuple(self.cfg.get("walk_cross", ("bed", "seat", "table", "rug")))
        self.crossing: dict = {}   # room id -> slots whose pieces may cross the walk strips (`cross = true`)

    def _kids(self) -> dict:
        """Room id -> the children who sleep there (the unit's children dealt to its children's rooms)."""
        out = {}
        for u, prof in self.profiles.items():
            rooms = sorted((r for r in self.it.rooms if r.unit == u and self.functions.get(r.id) == "sleep_children"),
                           key=lambda r: (-r.polygon.area, r.id))
            if not rooms:
                continue
            per = math.ceil(len(prof.children) / len(rooms))
            for i, r in enumerate(rooms):
                out[r.id] = prof.children[i * per:(i + 1) * per]
        return out

    def run(self) -> Furniture:
        rooms = sorted(self.it.rooms, key=lambda r: r.id)
        for level in range(self.level + 1):
            for r in rooms:
                self.furnish_room(r, level)
            if level == 0:
                self.sleepers()
        room_z = {r.id: r.z for r in self.it.rooms}
        return Furniture(self.density, self.cfg.get("period", "today"), self.profiles, self.functions, self.placed,
                         self.warnings, room_z)

    def budget(self, room, level: int) -> int:
        b = list(self.cfg.get("room_triangles", [1500, 4000, 8000]))[level]
        return 2 * b if room.type in ("wast_ed_dar", "stah", "qahwa", "hanout") else b

    def furnish_room(self, room, level: int) -> None:
        fn = self.functions.get(room.id)
        if fn is None:
            return
        prof = self.profiles.get(room.unit)
        if prof is None:
            return
        sp = self.prep.space(room)
        if sp.F.is_empty:
            return
        for i, slot in enumerate(self.recipes.get(fn, [])):
            if DENSITIES.index(slot.get("density", "sparse")) != level:
                continue
            self.slot(room, sp, prof, fn, i, slot, level)
        have = {p.role for p in self.in_room(room.id)}
        for role in self.pending.pop(room.id, []):
            if role not in have:
                self.warn(room, role)

    def draws(self, room, i: int, role: str) -> tuple:
        rng = stream(self.it.seed, "interior", self.it.city_id, self.it.building, "furnish", room.id, i, role)
        return tuple(float(v) for v in rng.random(4))

    def colours(self, room) -> dict:
        rng = stream(self.it.seed, "interior", self.it.city_id, self.it.building, "furnish", room.id, "colour")
        u = rng.random(6)
        pick = lambda xs, v: xs[int(v * len(xs)) % len(xs)]
        return {"velvet": pick(["red", "green", "blue"], u[0]), "fabric": pick(["beige", "grey", "red"], u[1]),
                "paint": pick(["green", "red"], u[2]), "klim": pick(["red", "indigo"], u[3]),
                "cover": pick(["mink", "white"], u[4]), "single": pick(["mink", "blue", "pink"], u[5]),
                "unit": pick(["white", "wood"], u[0] * 7 % 1.0), "bunk": pick(["iron", "wood"], u[3] * 3 % 1.0), "cushion": pick(["red", "green", "blue", "gold"], u[2] * 5 % 1.0)}

    def room_tags(self, room, prof) -> set:
        """The unit's tags and the room's own: `sedari` (a salon tunisien, by band), `nowc` (a bath in a home
        without a wc), `nodining` (a salon in a home without a dining room)."""
        if room.id in self._rtags:
            return self._rtags[room.id]
        tags = set(prof.tags)
        fns = [self.functions.get(r.id) for r in self.it.rooms if r.unit == room.unit]
        if "wc" not in fns:
            tags.add("nowc")
        if "dining" not in fns:
            tags.add("nodining")
        if self.functions.get(room.id) == "salon":
            w = self.cfg.get("sedari", {})
            share = float(w.get("colonial", 0.2)) if "colonial" in tags else float(
                w.get("rich", 0.3) if "rich" in tags else w.get("other", 0.5))
            rng = stream(self.it.seed, "interior", self.it.city_id, self.it.building, "furnish", room.id, "salon")
            tags.add("sedari" if rng.random() < share else "sofas")
        if prof.elders >= 2:
            tags.add("elders2")
        self._rtags[room.id] = tags
        return tags

    def entry(self, role: str, tags: set, u: float) -> str | None:
        entries = [e for e in self.roles.get(role, []) if tags_hold(e[2] if len(e) > 2 else "", tags)]
        if not entries:
            return None
        w = np.array([float(e[1]) for e in entries])
        if w.sum() <= 0:
            return None
        cdf = np.cumsum(w) / w.sum()
        return str(entries[int(np.searchsorted(cdf, u, side="right").clip(0, len(entries) - 1))][0])

    def slot(self, room, sp, prof, fn: str, i: int, slot: dict, level: int) -> None:
        role = slot["role"]
        u_chance, u_entry, u_place, u_count = self.draws(room, i, role)
        tags = self.room_tags(room, prof)
        if not tags_hold(slot.get("when", ""), tags):
            return
        if slot.get("unless") and any(p.role == slot["unless"] for p in self.in_room(room.id)):
            return
        if slot.get("no_room") and any(self.functions.get(r.id) == slot["no_room"] for r in self.it.rooms
                                       if r.unit == room.unit):
            return
        if slot.get("min_area") and sp.F.area < float(slot["min_area"]):
            return
        chance = slot.get("chance", 1.0)
        if isinstance(chance, str):
            chance = float(self.cfg.get(chance, 1.0) if not isinstance(self.cfg.get(chance), list)
                           else self.cfg[chance][1 if self.modern else 0])
        if u_chance >= float(chance):
            return
        need = bool(slot.get("need", False))
        if slot.get("cross"):
            self.crossing.setdefault(room.id, set()).add(i)
        names = self.names(room, sp, prof, slot, role, u_entry, u_count)
        if not names:
            if need:
                self.pending.setdefault(room.id, []).append(role)
            return
        got = 0
        for name in names:
            if not self.within_budget(room, name, level, need):
                continue
            if self.place(room, sp, prof, slot, i, role, name, u_place, level) is not None:
                got += 1
        if need and not got:
            self.pending.setdefault(room.id, []).append(role)

    def names(self, room, sp, prof, slot, role, u_entry, u_count) -> list:
        """The pieces this slot places, in order (one per copy)."""
        count = slot.get("count", 1)
        if role == "child_bed":
            return self.child_beds(room, prof)
        name = self.entry(slot.get("alias", role), self.room_tags(room, prof), u_entry)
        if name is None:
            return []
        name = name.format(**self.colours(room), goods=prof.trade or "grocer")
        if isinstance(count, list):
            lo, hi = int(count[0]), int(count[1])
            n = min(hi, lo + int(u_count * (hi - lo + 1)))
        elif count == "cots":       # small children without a children's room sleep by their parents
            housed = sum(1 for r, ks in self.kids.items() if self.prep.by_id[r].unit == room.unit for k in ks if k == "small")
            n = max(0, prof.children.count("small") - housed)
        elif count == "doors":
            n = sum(1 for o in self.it.openings if o.kind in PASS and room.id in o.rooms and any(
                self.prep.by_id.get(i) is not None and self.prep.by_id[i].unit.startswith("flat ") for i in o.rooms))
        elif count == "area":
            n = max(1, int(sp.F.area / float(self.cfg.get("cafe_area", 4.0))) - 1)
        elif count == "chairs":
            host = self.host_of(room, slot.get("place", ""))
            n = int(self.cfg.get("chairs", {}).get(host.piece.removeprefix("home/"), 4)) if host else 0
        elif count == "sleepers":
            n = max(0, prof.members - self.places(prof.unit))
        else:
            n = int(count)
        return [name] * n

    def child_beds(self, room, prof) -> list:
        kids = list(self.kids.get(room.id, []))
        beds = self.cfg.get("child_beds", {})
        out = []
        school = [k for k in kids if k in ("school", "teen")]
        if len(school) >= 2 and tags_hold(beds.get("bunk_when", "poor|middle"), prof.tags):
            out.append(beds.get("bunk", "home/bunk_bed_iron").format(**self.colours(room)))
            school = school[2:]
        for k in kids:
            if k == "small":
                out.append(beds.get("small", "home/cot"))
        for _ in school:
            if tags_hold(beds.get("single_when", "modern"), prof.tags) or tags_hold("today middle|rich", prof.tags):
                out.append(beds.get("single", "home/bed_single_{single}").format(**self.colours(room)))
            else:
                out.append(beds.get("floor", "home/mattress_floor_mink"))
        return out

    def within_budget(self, room, name: str, level: int, need: bool) -> bool:
        if need:
            return True
        pc = self.kit.pieces.get(name)
        if pc is None:
            return True
        tris = sum(len(p["idx"]) // 3 for p in pc.parts.values())
        return self.room_tris.get(room.id, 0) + tris <= self.budget(room, level)

    def warn(self, room, role: str) -> None:
        msg = f"furnish: {room.type} {room.id} has no {role}"
        if msg not in self.warnings:
            self.warnings.append(msg)

    def host_of(self, room, place: str):
        if ":" not in place:
            return None
        role = place.split(":", 1)[1]
        for p in reversed(self.in_room(room.id)):
            if p.room == room.id and p.role == role and not p.part:
                return p
        return None

    # --- placing one piece -----------------------------------------------------------------------------
    def chain(self, name: str) -> list:
        out = [name]
        seen = {name}
        while out[-1].removeprefix("home/") in self.smaller:
            nxt = self.smaller[out[-1].removeprefix("home/")]
            nxt = nxt if nxt.startswith("home/") else "home/" + nxt
            if nxt in seen:
                break
            out.append(nxt)
            seen.add(nxt)
        return out

    def place(self, room, sp, prof, slot, i, role, name, u_place, level):
        for nm in self.chain(name):
            nm = self._known(nm)
            if nm is None:
                continue
            got = self.place_one(room, sp, prof, slot, i, role, nm, u_place, level)
            if got is not None:
                return got
        return None

    def _known(self, name: str):
        if name in self.kit.pieces:
            return name
        if self.outside is not None and name.removeprefix("city/") in getattr(self.outside.kit, "pieces", {}):
            return name.removeprefix("city/")
        return None

    def spec(self, name: str):
        sp = self.kit.specs.get(name)
        if sp is not None:
            return sp
        box_ = self.prep._boxes.get(name)
        if name not in self.prep._boxes:
            from types import SimpleNamespace
            self.prep._bridge_box(SimpleNamespace(piece=name, x=0, y=0, yaw=0, scale=1, stretch=1))
            box_ = self.prep._boxes.get(name)
        if box_ is None:
            return None
        x0, y0, x1, y1 = box_
        from .homekit import HomeSpec
        return HomeSpec((x1 - x0, y1 - y0, 1.0), ((x0, y0), (x1, y0), (x1, y1), (x0, y1)), (0.0, 1.0))

    def category(self, name):
        pc = self.kit.pieces.get(name) or self.outside.kit.pieces.get(name)
        return pc.category, pc.anchor

    def place_one(self, room, sp, prof, slot, i, role, name, u_place, level):
        spec = self.spec(name)
        if spec is None:
            return None
        cat, anchor = self.category(name)
        place = slot.get("place", "wall")
        host = self.host_of(room, place) if ":" in place else None
        mode = place.split(":", 1)[0]
        if ":" in place and host is None:
            return None
        cands = self.candidates(sp, spec, anchor, mode, host, slot, name)
        spread = bool(slot.get("spread", False))
        passing = []
        run0 = None
        for pose in cands:
            if spread and run0 is not None and pose[4] != run0:
                break
            p = self.make(room, sp, name, spec, cat, anchor, pose, host, role, i, level)
            if p is not None and mode == "shopfront":     # the shopkeeper stands behind the counter
                p.use = [frame_poly(((-0.5, -0.6), (0.5, -0.6), (0.5, 0.0), (-0.5, 0.0)), p.x, p.y, p.yaw, pose[6])]
            if p is None or not self.fits(sp, p, host):
                continue
            if not spread:
                return self.commit(p, room, name, slot)
            run0 = pose[4]
            passing.append(p)
            if len(passing) >= 24:
                break
        if passing:
            return self.commit(passing[min(len(passing) - 1, int(u_place * len(passing)))], room, name, slot)
        return None

    def in_room(self, rid: int) -> list:
        """The pieces placed in a room so far (kept per room as they are placed)."""
        if self._room_of[0] != len(self.placed):
            self._room_of = (len(self.placed), {})
            for q in self.placed:
                self._room_of[1].setdefault(q.room, []).append(q)
        return self._room_of[1].get(rid, [])

    def commit(self, p, room, name, slot):
        p.places = self.sleep_places(p)
        p.idx = len(self.placed)
        self.placed.append(p)
        if p.group < 0:
            p.group = len(self.placed) - 1
        pc = self.kit.pieces.get(name) or self.outside.kit.pieces.get(name)
        self.room_tris[room.id] = self.room_tris.get(room.id, 0) + sum(len(q["idx"]) // 3 for q in pc.parts.values())
        for extra in slot.get("with", []):
            self.attach(room, p, extra, slot)
        return p

    def attach(self, room, host, extra: str, slot) -> None:
        """A set's own parts: `mattress` on a doukkana (its length), `cushions` along its back."""
        sp = self.prep.space(room)
        colours = self.colours(room)
        if extra == "mattress":
            band = "ticking" if "poor" in self.profiles[room.unit].tags else colours["velvet"]
            name = f"home/mattress_{band}"
            spec = self.kit.specs[name]
            top = self.kit.specs[host.piece].top or 0.0
            hd = self.kit.specs[host.piece].size[1]
            cx, cy = host.x - math.sin(host.yaw) * hd / 2, host.y + math.cos(host.yaw) * hd / 2
            foot = frame_poly(spec.foot, cx, cy, host.yaw, host.stretch)
            p = Placed(name, cx, cy, host.z + top, host.yaw, host.stretch, room.id, host.unit, host.role,
                       host.slot, foot, host.z + top + spec.z[0], host.z + top + spec.z[1], "seat", "on",
                       host.idx, host.group, host.run, host.s, host.width, None, host.density)
            p.part = True
            self._push(room, p)
        elif extra == "cushions":
            step = float(self.cfg.get("cushion_step", 0.6))
            name = f"home/cushion_{colours['cushion']}"
            spec = self.kit.specs[name]
            n = max(1, int(host.width // step))
            run = sp.runs[host.run]
            for k in range(n):
                s = host.s - host.width / 2 + step * (k + 0.5) + (host.width - n * step) / 2
                q = run.point(s)
                foot = frame_poly(spec.foot, q[0], q[1], host.yaw)
                p = Placed(name, float(q[0]), float(q[1]), host.z, host.yaw, 1.0, room.id, host.unit, host.role,
                           host.slot, foot, spec.z[0], spec.z[1], "seat", "wall", host.idx,
                           host.group, host.run, s, spec.size[0], None, host.density)
                p.part = True
                self._push(room, p)

    def _push(self, room, p):
        p.idx = len(self.placed)
        self.placed.append(p)
        pc = self.kit.pieces[p.piece]
        self.room_tris[room.id] = self.room_tris.get(room.id, 0) + sum(len(q["idx"]) // 3 for q in pc.parts.values())

    def sleep_places(self, p) -> int:
        table = self.cfg.get("places", {})
        base = p.piece.removeprefix("home/")
        for key, n in table.items():
            if base.startswith(key):
                if key in ("doukkana", "sedari", "sofa_3", "skifa_bench"):
                    return int(n) if p.width >= 1.8 else 0
                return int(n)
        return 0

    def places(self, unit: str) -> int:
        return sum(p.places for p in self.placed if p.unit == unit)

    def sleepers(self) -> None:
        """After the sparse pass: a unit whose beds sleep fewer than its members takes a mattress stack in
        its reception or salon (its seats sleep the rest)."""
        for u, prof in self.profiles.items():
            if prof.members == 0 or self.places(u) >= prof.members:
                continue
            rooms = sorted((r for r in self.it.rooms if r.unit == u), key=lambda r: (
                ("reception", "salon", "family", "guest", "sleep_children", "sleep_couple").index(self.functions[r.id])
                if self.functions.get(r.id) in ("reception", "salon", "family", "guest", "sleep_children",
                                                "sleep_couple") else 9, r.id))
            for r in rooms:
                sp = self.prep.space(r)
                if sp.F.is_empty:
                    continue
                slot = {"role": "mattress_stack", "place": "blind"}
                got = self.place_one(r, sp, prof, slot, 900, "mattress_stack", "home/mattress_stack", 0.0, 0)
                if got is not None:
                    got.places = prof.members - self.places(u) + got.places
                    break
            else:
                self.warnings.append(f"furnish: {u} sleeps {self.places(u)} of {prof.members}")

    # --- poses -------------------------------------------------------------------------------------------
    def lengths(self, spec, slot) -> list:
        if spec.stretch is None:
            return [1.0]
        lo, hi = spec.stretch
        hi = min(hi, float(slot.get("most", hi)))
        n = int(round((hi - lo) / 0.1))
        return [round(hi - 0.1 * k, 3) for k in range(n + 1)]

    def ranked(self, sp, mode, host, spec):
        runs = list(sp.runs)
        if mode == "facing_door":
            dx, dy = (sp.door_op.x, sp.door_op.y) if sp.door_op is not None else sp.door
            def score(r):
                mid = r.point(r.length / 2)
                v = np.array([dx, dy]) - mid
                v = v / max(1e-9, float(np.hypot(*v)))
                return float(r.n @ v)
            sc = {r.index: score(r) for r in runs}
            runs.sort(key=lambda r: (-round(sc[r.index] / 0.05), -r.length, r.index))
        elif mode == "head":
            def doorwall(r):
                return any(k in DOORS for *_, k in r.ops)
            def window(r):
                return any(k in WINDOWS for *_, k in r.ops)
            runs.sort(key=lambda r: (doorwall(r), window(r), -r.length, r.index))
        elif mode == "facing" and host is not None:
            f = np.array([-math.sin(host.yaw), math.cos(host.yaw)])
            c = np.array([host.x, host.y])
            runs = [r for r in runs if float((r.point(r.length / 2) - c) @ f) > 0.5]
            runs.sort(key=lambda r: (float(r.n @ f), r.index))
        elif mode == "window_wall":
            runs = [r for r in runs if any(k in WINDOWS for *_, k in r.ops)] + \
                   [r for r in runs if not any(k in WINDOWS for *_, k in r.ops)]
        elif mode == "next" and host is not None and host.run >= 0:
            hr = sp.runs[host.run]
            ends = (hr.a, hr.point(hr.length))
            def adj(r):
                return min(float(np.hypot(*(e - q))) for e in ends for q in (r.a, r.point(r.length)))
            runs = [r for r in runs if r.index != host.run and abs(float(r.d @ hr.d)) < 0.2 and adj(r) < 1.0]
        else:
            runs.sort(key=lambda r: (not r.blind, -r.length, r.index))
        return runs

    def candidates(self, sp, spec, anchor, mode, host, slot, name):
        """Poses (x, y, yaw, stretch, run index, s, width) in the fixed order of SPEC 6d "Places"."""
        step = float(self.cfg.get("step", 0.1))
        W, D, Hh = spec.size
        if mode in ("wall", "blind", "head", "facing_door", "corner", "facing", "window_wall", "next", "court_edge",
                    "hang", "shopfront"):
            if mode == "shopfront":
                yield from self.shopfront(sp, spec, slot)
                return
            if mode == "hang" and host is not None and host.run >= 0:
                runs = [sp.runs[host.run]]
            else:
                runs = self.ranked(sp, mode, host, spec)
            blind = mode in ("blind", "head") or slot.get("blind", False)
            z0, z1 = spec.z
            for r in runs:
                for L in self.lengths(spec, slot):
                    w = W * L
                    if w > r.length + 1e-6:
                        continue
                    lo, hi = w / 2, r.length - w / 2
                    if mode == "hang" and host is not None and host.run == r.index:
                        lo, hi = max(lo, host.s - host.width / 2 + w / 2), min(hi, host.s + host.width / 2 - w / 2)
                        if hi < lo - 1e-6:
                            continue
                    ss = self.slide(lo, hi, step, mode, r, w, slot, host)
                    for s in ss:
                        if blind and not r.clear(s - w / 2, s + w / 2, z1):
                            continue
                        if mode == "hang" and not r.clear(s - w / 2, s + w / 2, z1, 0.10, z0):
                            continue
                        q = r.point(s)
                        if anchor == "floor":
                            q = q + r.n * (D / 2)
                        yield (float(q[0]), float(q[1]), yaw_facing(r.n), L, r.index, s, w)
        elif mode == "front" and host is not None:
            hs = self.kit.specs.get(host.piece)
            f = np.array([-math.sin(host.yaw), math.cos(host.yaw)])
            e = np.array([math.cos(host.yaw), math.sin(host.yaw)])
            gap = float(self.cfg.get("front_gap", 0.25))
            if host.piece.startswith("home/sofa") or host.piece.startswith("home/armchair"):
                gap = float(self.cfg.get("front_gap_sofa", 0.40))
            depth = hs.size[1] if host.anchor == "wall" else hs.size[1] / 2
            c = np.array([host.x, host.y]) + f * (depth + gap + D / 2)
            half = max(0.0, host.width / 2 - W / 2)
            for t in self.slide(-half, half, step, "front", None, W, slot, None):
                q = c + e * t
                yield (float(q[0]), float(q[1]), host.yaw + math.pi, 1.0, -1, 0.0, W)
        elif mode == "under" and host is not None:
            e = np.array([math.cos(host.yaw), math.sin(host.yaw)])
            hs = self.kit.specs.get(host.piece)
            hw = host.width
            long_x = hw >= (hs.size[1] if hs else 0)
            yaw = host.yaw + (math.pi / 2 if long_x and D > W else 0.0)
            f = np.array([-math.sin(host.yaw), math.cos(host.yaw)])
            c0 = np.array([host.x, host.y]) + (f * hs.size[1] / 2 if host.anchor == "wall" else 0)
            for t in self.slide(-0.6, 0.6, step * 2, "front", None, W, slot, None):
                q = c0 + e * t
                yield (float(q[0]), float(q[1]), yaw, 1.0, -1, 0.0, W)
        elif mode == "beside" and host is not None:
            if host.run >= 0:
                r = sp.runs[host.run]
                for sign in (-1.0, 1.0):
                    s = host.s + sign * (host.width / 2 + W / 2 + 0.02)
                    if s - W / 2 < -1e-6 or s + W / 2 > r.length + 1e-6:
                        continue
                    q = r.point(s)
                    if anchor == "floor":
                        q = q + r.n * (D / 2)
                    yield (float(q[0]), float(q[1]), yaw_facing(r.n), 1.0, r.index, s, W)
            else:
                e = np.array([math.cos(host.yaw), math.sin(host.yaw)])
                for sign in (-1.0, 1.0):
                    q = np.array([host.x, host.y]) + e * sign * (host.width / 2 + W / 2 + 0.05)
                    yield (float(q[0]), float(q[1]), host.yaw, 1.0, -1, 0.0, W)
        elif mode == "around" and host is not None:
            hs = self.kit.specs[host.piece]
            tw, td = hs.size[0], hs.size[1]
            e = np.array([math.cos(host.yaw), math.sin(host.yaw)])
            f = np.array([-math.sin(host.yaw), math.cos(host.yaw)])
            c = np.array([host.x, host.y])
            per = max(1, int(tw // 0.55))
            for side in (1.0, -1.0):
                for k in range(per):
                    t = -tw / 2 + tw * (k + 0.5) / per
                    q = c + e * t + f * side * (td / 2 + D / 2 - 0.10)
                    yield (float(q[0]), float(q[1]), yaw_facing(-f * side), 1.0, -1, 0.0, W)
            for side in (1.0, -1.0):
                q = c + e * side * (tw / 2 + D / 2 - 0.10)
                yield (float(q[0]), float(q[1]), yaw_facing(-e * side), 1.0, -1, 0.0, W)
        elif mode == "on" and host is not None:
            hs = self.kit.specs[host.piece]
            e = np.array([math.cos(host.yaw), math.sin(host.yaw)])
            f = np.array([-math.sin(host.yaw), math.cos(host.yaw)])
            hd = hs.size[1]
            c = np.array([host.x, host.y]) + (f * hd / 2 if host.anchor == "wall" else 0)
            if anchor == "wall":
                c = c - f * (D / 2)
            half = max(0.0, (host.width - 0.06) / 2 - W / 2)
            for t in self.slide(-half, half, step, "front", None, W, slot, None):
                q = c + e * t
                yield (float(q[0]), float(q[1]), host.yaw, 1.0, -1, 0.0, W)
        elif mode == "free":
            yaw = sp.yaw
            if name.startswith("home/sajjada"):
                b = round(float(self.cfg.get("qibla", 112.0)) / 15.0) * 15.0
                yaw = -math.radians(b)
            hx, hy = sp.hub
            g = 0.25
            minx, miny, maxx, maxy = sp.F.bounds
            xs = np.arange(math.floor((minx - hx) / g), math.ceil((maxx - hx) / g) + 1) * g + hx
            ys = np.arange(math.floor((miny - hy) / g), math.ceil((maxy - hy) / g) + 1) * g + hy
            X, Y = np.meshgrid(xs, ys)
            pts = np.stack([X.ravel(), Y.ravel()], axis=1)
            d = np.hypot(pts[:, 0] - hx, pts[:, 1] - hy)
            order = np.lexsort((pts[:, 0], pts[:, 1], np.round(d, 6)))
            ok = shapely.contains_xy(sp.F, pts[order, 0], pts[order, 1])
            for k in order[ok][:240]:
                yield (float(pts[k, 0]), float(pts[k, 1]), yaw, 1.0, -1, 0.0, W)
        elif mode == "doormat":
            by_id = self.prep.by_id
            for o in sorted(self.it.openings, key=lambda o: o.id):
                if o.kind not in PASS or sp.room.id not in o.rooms or sp.room.unit != "common":
                    continue
                other = by_id.get(o.rooms[1] if o.rooms[0] == sp.room.id else o.rooms[0])
                if other is None or not other.unit.startswith("flat "):
                    continue
                n = side_of(o, sp.room)
                q = np.array([o.x, o.y]) + n * (self.it.walls["partition"] / 2 + 0.02 + D / 2)
                yield (float(q[0]), float(q[1]), yaw_facing(n), 1.0, -1, 0.0, W)
        elif mode == "grid":
            pitch = float(self.cfg.get("cafe_pitch", 1.6))
            hx, hy = sp.hub
            c, s = math.cos(sp.yaw), math.sin(sp.yaw)
            minx, miny, maxx, maxy = sp.F.bounds
            R = max(maxx - minx, maxy - miny)
            n = int(R / pitch) + 1
            pts = []
            for a in range(-n, n + 1):
                for b in range(-n, n + 1):
                    pts.append((hx + a * pitch * c - b * pitch * s, hy + a * pitch * s + b * pitch * c, abs(a) + abs(b), a, b))
            pts.sort(key=lambda t: (t[2], t[4], t[3]))
            for x, y, *_ in pts:
                if sp.F.contains(Point(x, y)):
                    yield (x, y, sp.yaw, 1.0, -1, 0.0, W)

    def slide(self, lo: float, hi: float, step: float, mode, run, w, slot, host) -> list:
        if hi < lo - 1e-6:
            return []
        if mode == "corner":
            return [lo, hi] if hi > lo + 1e-6 else [lo]
        if mode == "next" and host is not None and run is not None:
            ss = list(np.arange(lo, hi + 1e-6, step))      # from both ends inward: an L starts at a corner
            out = []
            for k in range(len(ss)):
                out.append(ss[k])
                if len(ss) - 1 - k != k:
                    out.append(ss[len(ss) - 1 - k])
            return out[:len(ss)]
        if mode == "window_wall" and run is not None:
            wins = [(o0 + o1) / 2 for o0, o1, _, _, k in run.ops if k in WINDOWS]
            out = []
            for m in wins:
                out.extend([min(max(m, lo), hi)])
            mid = (lo + hi) / 2
            n = int((hi - lo) / 2 / step + 1e-6)
            out += [mid] + [v for k in range(1, n + 1) for v in (mid - k * step, mid + k * step)]
            return out
        mid = (lo + hi) / 2
        n = int((hi - lo) / 2 / step + 1e-6)
        out = [mid]
        for k in range(1, n + 1):
            out += [mid - k * step, mid + k * step]
        if (hi - lo) / 2 - n * step > 1e-3:
            out += [lo, hi]
        return out

    def shopfront(self, sp, spec, slot):
        front = next((o for o in self.it.openings if o.kind == "shop" and sp.room.id in o.rooms), None)
        if front is None:
            return
        n = side_of(front, sp.room)
        along = np.array([math.cos(front.yaw), math.sin(front.yaw)])
        W, D, _ = spec.size
        for L in self.lengths(spec, slot):
            for t in (0.0, -0.6, 0.6, -1.2, 1.2):
                c = np.array([front.x, front.y]) + n * (face_of(self.it, front, n) + 0.9 + D) + along * t
                yield (float(c[0]), float(c[1]), yaw_facing(-n), L, -1, 0.0, W * L)

    def make(self, room, sp, name, spec, cat, anchor, pose, host, role, i, level):
        x, y, yaw, L, run, s, w = pose
        z = 0.0
        if anchor == "on" and host is not None:
            hs = self.kit.specs.get(host.piece) if host else None
            z = (host.z + (hs.top or 0.0)) if hs else 0.0
        foot = frame_poly(spec.foot, x, y, yaw, L)
        return Placed(name, x, y, z, yaw, L, room.id, room.unit, role, i, foot, z + spec.z[0], z + spec.z[1], cat,
                      anchor, -1 if host is None else host.idx, -1 if host is None else host.group, run, s, w, None,
                      DENSITIES[level], lazy=spec.use > 0)

    def uses(self, p) -> list:
        """The use strips a piece may take (a bed: either long side; else its front)."""
        spec, x, y, yaw, L, cat = self.kit.specs[p.piece], p.x, p.y, p.yaw, p.stretch, p.cat
        if cat == "bed":
            uses = [frame_poly(((sx0, spec.foot[0][1]), (sx1, spec.foot[0][1]), (sx1, spec.foot[2][1]),
                                (sx0, spec.foot[2][1])), x, y, yaw)
                    for sx0, sx1 in ((spec.size[0] / 2, spec.size[0] / 2 + spec.use),
                                     (-spec.size[0] / 2 - spec.use, -spec.size[0] / 2))]
            use = uses
        else:
            y1 = spec.foot[2][1]
            use = [frame_poly(((-0.5, y1), (0.5, y1), (0.5, y1 + spec.use), (-0.5, y1 + spec.use)), x, y, yaw,
                              spec.size[0] * L)]
        return use

    # --- fit ---------------------------------------------------------------------------------------------
    def fits(self, sp, p, host) -> bool:
        why = self.why(sp, p, host)
        if DEBUG is not None:
            DEBUG[(p.room, p.role, why)] = DEBUG.get((p.room, p.role, why), 0) + 1
        return why == ""

    def why(self, sp, p, host) -> str:
        """"" when the pose passes (SPEC 6d "Fit", cheap tests first), else the first test it fails."""
        if not sp.Fgrown.contains(p.foot):
            return "floor"
        rug = p.cat == "rug"
        on = p.anchor == "on" and host is not None
        if p.z1 > sp.ceiling - 0.05:
            return "ceiling"
        if not on:
            for g, z0, z1, kind in sp.keeps:
                top = p.z1
                if kind == "window" and p.cat == "kitchen":
                    top = min(p.z1, p.z0 + (self.kit.specs[p.piece].top or p.z1))   # a sink's tap rises before its window
                if z0 < top and z1 > p.z0 and g.intersects(p.foot) and g.intersection(p.foot).area > TOL_AREA:
                    if kind == "walk" and (p.cat in self.cross or p.slot in self.crossing.get(p.room, ())):
                        continue
                    if kind == "door" and p.piece == "home/doormat":
                        continue
                    return "keep:" + kind
        mine = self.in_room(p.room)
        for q in mine:
            if on:
                if not (q.host == p.host and q.anchor == "on" or q.z0 >= p.z0 and q.anchor != "on"):
                    continue
            elif rug != (q.cat == "rug"):
                continue
            elif q.anchor == "on":
                continue
            if q.z0 < p.z1 and q.z1 > p.z0 and q.foot.intersects(p.foot) and q.foot.intersection(p.foot).area > TOL_AREA:
                return "overlap"
        if on and p.part:
            return ""
        if on:
            hs = self.kit.specs.get(host.piece)
            top = frame_poly(hs.foot, host.x, host.y, host.yaw, host.stretch).buffer(-0.03, join_style="mitre")
            return "" if top.buffer(0.005).contains(p.foot) else "top"
        if rug:
            return ""
        if p.use is None and p.lazy:
            p.use = self.uses(p)
        if p.use is not None:
            for u in p.use:
                if self.use_ok(sp, u, p, mine):
                    p.use = [u]
                    break
            else:
                return "use"
        if p.z1 > 0.5:
            for q in mine:
                if q.use is None or q.group == p.group and p.group >= 0:
                    continue
                for u in q.use:
                    if u.intersects(p.foot) and u.intersection(p.foot).area > TOL_AREA:
                        return "other_use"
        if p.z0 < 1.0 and not reaches(sp, mine + [p], self.path):
            return "reach"
        return ""

    def use_ok(self, sp, u, p, mine) -> bool:
        if not sp.Fgrown.contains(u):
            return False
        for q in mine:
            if q.z1 <= 0.5 or (q.group == p.group and p.group >= 0) or q.cat == "rug":
                continue
            if q.z0 >= 1.0 and q.anchor == "wall":
                continue
            if q.foot.intersects(u) and q.foot.intersection(u).area > TOL_AREA:
                return False
        return True

    def reach(self, sp, pieces) -> bool:
        return reaches(sp, pieces, self.path)


def _parts_of(region, path: float) -> list:
    return polygons(region.buffer(-path / 2, join_style="mitre")) if not region.is_empty else []


def _which(parts: list, pt, tol: float):
    best = None
    for k, part in enumerate(parts):
        d = part.distance(pt)
        if d <= tol and (best is None or d < best[0]):
            best = (d, k)
    return None if best is None else best[1]


def reaches(sp, pieces, path: float) -> bool:
    """F less every standing foot (under 1.0 m, not rugs or pieces on a host), shrunk by path / 2, keeps the
    room's ways in and every use strip's middle joined as the empty room joins them (a room whose own floor
    has a neck narrower than `path` is not asked to join what its walls part)."""
    feet = [q.foot for q in pieces if q.z0 < 1.0 and q.cat != "rug" and not (q.host >= 0 and q.anchor == "on")]
    if not feet:
        return True
    pts = [Point(p) for p in sp.inner] or [Point(sp.door)]
    for q in pieces:
        if q.use and not any(m is not q and m.group == q.group and m.cat != "rug" and m.foot.intersects(q.use[0])
                             for m in pieces):
            pts.append(q.use[0].centroid)
    tol = path / 2 + 0.02
    if sp.base is None:
        sp.base = _parts_of(sp.F, path)
    parts = _parts_of(sp.F.difference(unary_union(feet)), path)
    groups: dict = {}
    for pt in pts:
        b = _which(sp.base, pt, tol)
        if b is None:
            continue
        k = _which(parts, pt, tol)
        if k is None or groups.setdefault(b, k) != k:
            return False
    return True


# --- entry points ----------------------------------------------------------------------------------------
def furnish(interior, outside, style: dict, density: str | None = None) -> Furniture:
    """Place the furniture of every room at `density` (default the style's)."""
    density = density or settings(style).get("density", "lived-in")
    if density not in DENSITIES:
        raise ValueError(f"density {density!r}: one of {', '.join(DENSITIES)}")
    return Furnisher(interior, outside, style, density).run()


def check(interior, furniture: Furniture, style: dict, outside=None) -> list:
    """Problems of a finished furnishing (SPEC 6d "Checks"): overlap, walls, clearances, reach, required,
    sleeping places, household and budget. Each piece is tested again, in placing order, against the pieces
    before it with the same rules as `fits`; then every room's walk with all its pieces."""
    cfg = settings(style)
    fu = Furnisher(interior, outside, style, furniture.density)
    fu.crossing = {}
    for p in furniture.pieces:
        slots = cfg.get("rooms", {}).get(furniture.functions.get(p.room, ""), [])
        if 0 <= p.slot < len(slots) and slots[p.slot].get("cross"):
            fu.crossing.setdefault(p.room, set()).add(p.slot)
    out = []
    rooms = {r.id: r for r in interior.rooms}
    words = {"floor": "walls", "ceiling": "ceiling", "overlap": "overlap", "top": "overlap", "use": "reach",
             "other_use": "reach", "reach": "reach"}
    by_room: dict = {}
    for k, p in enumerate(furniture.pieces):
        r = rooms[p.room]
        sp = fu.prep.space(r)
        fu.placed = furniture.pieces[:k]
        host = furniture.pieces[p.host] if p.host >= 0 else None
        use = p.use
        why = "" if p.part and p.anchor == "wall" else fu.why(sp, p, host)
        p.use = use
        if why and not (p.part and why in ("reach", "use", "other_use")):
            kind = "clearance" if why.startswith("keep") else words.get(why, why)
            out.append(f"{kind}: {p.piece} in {r.type} {p.room} ({why})")
        if p.anchor == "wall" and p.z0 >= 1.0 and 0 <= p.run < len(sp.runs):
            if not sp.runs[p.run].clear(p.s - p.width / 2, p.s + p.width / 2, p.z1, 0.10 - 1e-6, p.z0):
                out.append(f"clearance: {p.piece} in {r.type} {p.room} hangs over an opening")
        by_room.setdefault(p.room, []).append(p)
    for rid, items in sorted(by_room.items()):
        if not reaches(fu.prep.space(rooms[rid]), items, fu.path):
            out.append(f"reach: {rooms[rid].type} {rid} cannot be walked")
    warned = set(furniture.warnings)
    level = DENSITIES.index(furniture.density)
    for rid, fn in furniture.functions.items():                       # required: each need slot's role, or its warning
        r = rooms[rid]
        prof = furniture.profiles.get(r.unit)
        if prof is None:
            continue
        roles = {p.role for p in by_room.get(rid, [])}
        tags = fu.room_tags(r, prof)
        for slot in cfg.get("rooms", {}).get(fn, []):
            if not slot.get("need") or not tags_hold(slot.get("when", ""), tags) or \
                    DENSITIES.index(slot.get("density", "sparse")) > level:
                continue
            if slot["role"] == "child_bed" and not fu.kids.get(rid):
                continue
            if slot["role"] not in roles and f"furnish: {r.type} {rid} has no {slot['role']}" not in warned:
                out.append(f"required: {r.type} {rid} ({fn}) has no {slot['role']}")
    for u, prof in furniture.profiles.items():                       # sleeping places and the household
        if prof.members == 0:
            continue
        got = sum(p.places for p in furniture.pieces if p.unit == u)
        if got < prof.members:
            out.append(f"sleep: {u} sleeps {got} of {prof.members}")
        names = [p.piece for p in furniture.pieces if p.unit == u]
        if level >= 1:
            for trade, piece in cfg.get("household_check", {}).items():
                if prof.trade == trade and piece not in names:
                    out.append(f"household: the {trade}'s {u} has no {piece}")
            if "reader" in prof.tags and not any(n in ("home/rahla", "home/bookcase_full") for n in names):
                out.append(f"household: the {prof.trade}'s {u} has no books")
        small = prof.children.count("small")
        if small and names.count("home/cot") < small:
            out.append(f"household: {u} has {small} small children and {names.count('home/cot')} cots")
    budgets = list(cfg.get("room_triangles", [1500, 4000, 8000]))
    tris: dict = {}
    for p in furniture.pieces:
        pc = fu.kit.pieces.get(p.piece)
        if pc is not None:
            tris[p.room] = tris.get(p.room, 0) + sum(len(q["idx"]) // 3 for q in pc.parts.values())
    for rid, t in sorted(tris.items()):
        if t > fu.budget(rooms[rid], level) + NEED_SLACK:
            out.append(f"budget: {rooms[rid].type} {rid} draws {t} triangles")
    return out


def placements(furniture: Furniture) -> list:
    """The furniture as `Placement`s with absolute z (for `instance_groups`)."""
    from ..city.dressing import Placement
    return [Placement(p.piece, p.x, p.y, furniture.room_z[p.room] + p.z, p.yaw, on_ground=False, stretch=p.stretch)
            for p in furniture.pieces]
