"""Street dressing: doors, windows, shops, goods and street life, built tile by tile.

Nothing here is stored in the plan. A tile asks for the dressing of the buildings and streets it
owns and always gets the same answer, because every building and every street sample has its own
random stream. Huge cities stay cheap: only exported tiles pay for the detail.

Pieces come from the kit (citygen/kit.py). The style's [dressing.roles] says which pieces may play
each part (a blue door, a rich blue door, a lamp, a parked moped...) and how often, so the Tounes
Rush pieces and the generator's own mix by weight. A placement puts a piece's anchor at (x, y, z)
and turns its front (+y in piece space) to face the street.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import shapely
from shapely.geometry import LineString
from shapely.geometry.polygon import orient
from shapely.strtree import STRtree

from ..rng import stream, weighted
from .roofs import roof_layout, roof_stream

DRESSED = {"house", "domed", "apartments", "villa"}
FRONT_PREF = {"souk": 3.0, "alley": 2.5, "street": 2.0, "boulevard": 1.5, "ring": 1.0, "arterial": 1.0,
              "corniche": 1.0, "connector": 0.5}
TRADITIONAL = {"medina", "village"}


@dataclass
class Placement:
    piece: str
    x: float
    y: float
    z: float        # meters: above the ground at (x, y) when on_ground, else absolute
    yaw: float      # radians about up; the piece front turns to (-sin yaw, cos yaw)
    on_ground: bool = True
    scale: float = 1.0


@dataclass
class Span:
    kind: str       # laundry | cable | lanterns | bunting | sabat
    a: tuple        # (x, y, z) absolute; for a sabat, the two wall points at the room's floor
    b: tuple
    seed: int = 0   # for the details hanging on it (clothes, flags)
    piece: str = ""     # lanterns: the piece hanging from the rope
    step: float = 1.6   # lanterns: meters between two of them
    top: float = 0.0    # sabat: height of its roof, absolute


@dataclass
class Facade:
    a: np.ndarray
    b: np.ndarray
    n: np.ndarray   # outward normal (toward the street)
    length: float
    street: int
    kind: str

    def at(self, t: float) -> np.ndarray:
        return self.a + (self.b - self.a) * t

    @property
    def u(self) -> np.ndarray:
        return (self.b - self.a) / self.length


def yaw_of(n) -> float:
    return math.atan2(-n[0], n[1])


class Dresser:
    """Everything one city needs to dress its tiles: street lookup, households, souks, the kit."""

    def __init__(self, world, plan, kit, ground):
        self.world, self.plan, self.kit, self.ground = world, plan, kit, ground
        self.cfg = world.style.get("dressing", {})
        self.roofs = world.style.get("roofs", {})
        self.seed, self.sid = world.seed, plan.settlement.id
        self.surfaces = [st.line.buffer(st.width / 2, cap_style="flat") for st in plan.streets]
        self.surface_tree = STRtree(self.surfaces) if self.surfaces else None
        self.footprints = [b.footprint for b in plan.buildings]
        self.fp_tree = STRtree(self.footprints) if self.footprints else None
        self.homes = {h.building: h for h in getattr(plan, "households", [])}
        self.souk_of = {s.street: s for s in getattr(plan, "souks", [])}
        self.kinds = [d.kind for d in plan.districts]
        self.roles = self._roles(self.cfg.get("roles", {}))

    def rng(self, *path):
        return stream(self.seed, "city", self.sid, "dress", *path)

    # --- pieces ---------------------------------------------------------------------------
    def _roles(self, table: dict) -> dict:
        """Role -> (pieces, cumulative odds, extra heights), keeping only the pieces the kit has."""
        out = {}
        for role, options in table.items():
            keep = [(str(o[0]), float(o[1]), float(o[2]) if len(o) > 2 else 0.0)
                    for o in options if str(o[0]) in self.kit.pieces and float(o[1]) > 0]
            if keep:
                odds = np.cumsum([o[1] for o in keep])
                out[role] = ([o[0] for o in keep], odds / odds[-1], [o[2] for o in keep])
        return out

    def has(self, role: str) -> bool:
        return role in self.roles or role in self.kit.pieces

    def pick(self, role: str, rng) -> tuple | None:
        """(piece, extra height) for a role or a plain piece name; None when the kit has nothing for it."""
        found = self.roles.get(role)
        if found is None:
            return (role, 0.0) if role in self.kit.pieces else None
        names, odds, heights = found
        k = min(int(np.searchsorted(odds, rng.random(), side="right")), len(names) - 1)
        return names[k], heights[k]

    def put(self, out: list, role: str, rng, p, z: float, yaw: float, on_ground: bool = True,
            scale: float = 1.0) -> str | None:
        got = self.pick(role, rng)
        if got is None:
            return None
        out.append(Placement(got[0], float(p[0]), float(p[1]), z + got[1] * scale, yaw, on_ground, scale))
        return got[0]

    # --- lookups ------------------------------------------------------------------------
    def streets_at(self, pts: np.ndarray) -> np.ndarray:
        out = np.full(len(pts), -1)
        if self.surface_tree is None or not len(pts):
            return out
        inp, hit = self.surface_tree.query(shapely.points(pts), predicate="within")
        out[inp] = hit
        return out

    def facades(self, b) -> list:
        ring = np.asarray(orient(b.footprint, 1.0).exterior.coords)[:-1]
        p, q = ring, np.roll(ring, -1, axis=0)
        d = q - p
        length = np.hypot(d[:, 0], d[:, 1])
        ok = length > 1.5
        n = np.stack([d[:, 1], -d[:, 0]], 1) / np.maximum(length, 1e-9)[:, None]
        street = self.streets_at((p + q) / 2 + n * 1.6)
        return [Facade(p[k], q[k], n[k], float(length[k]), int(street[k]), self.plan.streets[street[k]].kind)
                for k in np.nonzero(ok & (street >= 0))[0]]

    # --- buildings ------------------------------------------------------------------------
    def building(self, k: int, high: float) -> list:
        b = self.plan.buildings[k]
        if b.kind not in DRESSED:
            return []
        rng = self.rng("b", k)
        out: list = []
        fac = self.facades(b)
        home = self.homes.get(k)
        color = home.door if home else "door_blue"
        wealth = home.wealth if home else 0.4
        district = self.kinds[b.district]
        floors = max(1, int(b.floors))
        fh = b.height / floors
        door_at = None
        if fac:
            main = max(fac, key=lambda f: (FRONT_PREF.get(f.kind, 0.0), f.length))
            door_at = self._front(main, district, color, wealth, b.height, rng, out)
            self._windows(fac, district, color, wealth, floors, fh, high, door_at, rng, out)
        self._roof(b, k, high, rng, out)
        return out

    def front_surface(self, c: np.ndarray, n: np.ndarray) -> float:
        """Height of the drawn street surface just in front of a wall (the door threshold's level)."""
        q = c + n * self.cfg.get("threshold_reach", 0.5)
        return float(self.ground.surface(float(q[0]), float(q[1])))

    def _front(self, f: Facade, district, color, wealth, height, rng, out) -> np.ndarray | None:
        cfg = self.cfg
        souk = self.souk_of.get(f.street) if f.kind == "souk" else None
        if souk is not None and f.length >= 3.0 and rng.random() < cfg.get("shop_on_souk", 0.85):
            return self._shop(f, souk, rng, out)
        if district == "colonial" and f.length >= 3.2 and rng.random() < cfg.get("cafe", 0.3):
            return self._cafe(f, rng, out)
        if f.length < 2.3:
            return None
        yaw, u, n = yaw_of(f.n), f.u, f.n
        s = f.length * 0.5 + rng.uniform(-1.0, 1.0) * max(0.0, f.length * 0.5 - 1.2)   # door center along the wall
        c = f.at(s / f.length)

        def room(offset: float, half: float) -> bool:   # does a piece this wide fit on the wall there?
            return half <= s + offset <= f.length - half

        def side() -> float:
            return 1.0 if rng.random() < 0.5 else -1.0

        rich = wealth > cfg.get("rich_door", 0.72) and district in TRADITIONAL | {"colonial", "residential"}
        self.put(out, color + "_rich" if rich else color, rng, c, self.front_surface(c, n), yaw, on_ground=False)
        if rng.random() < cfg.get("door_hood", 0.15) * (0.5 + wealth):
            self.put(out, "door_hood", rng, c, cfg.get("hood_height", 3.15), yaw)
        if rng.random() < cfg.get("door_lantern", 0.35):
            sd = side()
            if room(sd * 1.25, 0.3):
                self.put(out, "lamp", rng, c + u * sd * 1.25, cfg.get("lamp_height", 2.95), yaw)
        lo, hi = cfg.get("door_pots", [0, 2])
        for _ in range(int(rng.integers(lo, hi + 1))):
            off = side() * rng.uniform(1.15, 1.7)
            if room(off, 0.35):
                self.put(out, "pot", rng, c + u * off + n * 0.4, 0.0, rng.uniform(0, 6.28))
        if district in TRADITIONAL and rng.random() < cfg.get("doukkana", 0.25):
            off = side() * 2.1
            if room(off, 1.05):
                self.put(out, "bench", rng, c + u * off, 0.0, yaw)
        if rng.random() < cfg.get("cat", 0.07):
            self.put(out, "cat", rng, c + n * 0.6 + u * rng.uniform(-0.4, 0.4), 0.0, rng.uniform(0, 6.28))
        if rng.random() < cfg.get("door_plant", 0.2) * (0.5 + wealth):
            self._plant(f, c, yaw, height, room, side(), rng, out)
        if rng.random() < cfg.get("parked", 0.08):
            off = side() * rng.uniform(2.0, 2.8)
            if room(off, 1.1):
                turn = math.pi / 2 if rng.random() < 0.5 else -math.pi / 2   # parked along the wall
                self.put(out, "parked", rng, c + u * off + n * 0.6, 0.0, yaw + turn + rng.uniform(-0.15, 0.15))
        if district in ("colonial", "residential", "suburb") and wealth > 0.6 and rng.random() < cfg.get("planter", 0.25):
            off = side() * 2.0
            if room(off, 1.15):
                self.put(out, "planter", rng, c + u * off + n * 0.45, 0.0, yaw)
        return c

    def _plant(self, f, c, yaw, height, room, sd, rng, out) -> None:
        """A climber by the door: a vine over it, a cascade beside it, or a bougainvillea rooted in the street."""
        kind = weighted(rng, self.cfg.get("door_plants", [["climber", 1]]))
        kind = kind if self.has(kind) else "climber"   # the generator's own climber when the kit has none
        u = f.u
        top = min(self.cfg.get("cascade_height", 4.2), height - 0.2)   # hangs from the wall top on low houses
        if kind == "vine" and height >= 4.0:
            self.put(out, "vine", rng, c, self.cfg.get("vine_height", 3.4), yaw)
        elif kind == "cascade" and top >= 3.2 and room(sd * 2.4, 1.4):
            self.put(out, "cascade", rng, c + u * sd * 2.4, top, yaw)
        elif room(sd * 1.9, 0.9):
            self.put(out, "climber", rng, c + u * sd * 1.9, 0.0, yaw)

    def _shop(self, f: Facade, souk, rng, out) -> np.ndarray:
        yaw, u, n = yaw_of(f.n), f.u, f.n
        c = f.at(0.5)
        shop = f"shop_front_{souk.shop}"
        z = self.front_surface(c, n)
        self.put(out, shop if self.has(shop) else "shop_front", rng, c, z, yaw, on_ground=False)
        self.put(out, "souk_awning", rng, c, z, yaw, on_ground=False)
        for _ in range(int(rng.integers(1, 3)) if souk.ground else 0):
            role = str(souk.ground[int(rng.integers(len(souk.ground)))])
            p = c + u * rng.uniform(-0.6, 0.6) + n * rng.uniform(0.75, 1.0)
            self.put(out, role, rng, p, 0.0, yaw + rng.uniform(-0.15, 0.15))
        if souk.wall and f.length >= 5.2:
            role = str(souk.wall[int(rng.integers(len(souk.wall)))])
            side = 1.0 if rng.random() < 0.5 else -1.0
            self.put(out, role, rng, c + u * side * 2.1, 0.0, yaw)
        if f.length >= 4.2 and rng.random() < self.cfg.get("shop_lamp", 0.3):
            side = 1.0 if rng.random() < 0.5 else -1.0
            self.put(out, "lamp", rng, c + u * side * 1.75, self.cfg.get("lamp_height", 2.95), yaw)
        return c

    def _cafe(self, f: Facade, rng, out) -> np.ndarray:
        yaw, u, n = yaw_of(f.n), f.u, f.n
        c = f.at(0.5)
        z = self.front_surface(c, n)
        self.put(out, "shop_front", rng, c, z, yaw, on_ground=False)
        self.put(out, "awning", rng, c, z, yaw, on_ground=False)
        for k in range(int(rng.integers(1, 3))):
            p = c + u * (k - 0.5) * 1.9 + n * 1.7
            self.put(out, "cafe_set", rng, p, 0.0, yaw + rng.uniform(-0.4, 0.4))
        return c

    def _windows(self, fac, district, color, wealth, floors, fh, high, door_at, rng, out) -> None:
        cfg = self.cfg
        spacing = float(cfg.get("window_spacing", 3.2))
        sill = float(cfg.get("window_sill", 0.95))
        traditional = district in TRADITIONAL
        first = 1 if traditional or district == "colonial" else 0
        odds = 0.5 if traditional else 0.9
        tint = color[5:]
        bay = traditional and wealth > cfg.get("bay_wealth", 0.55)
        balconies = int(wealth > cfg.get("balcony_wealth", 0.6) and rng.random() < cfg.get("balcony", 0.4))
        balcony = next((r for r in (f"balcony_{tint}", "balcony") if self.has(r)), None)
        laundry = int(rng.random() < cfg.get("wall_laundry", 0.1))
        for f in fac:
            count = int(f.length // spacing)
            yaw = yaw_of(f.n)
            for i in range(count):
                p = f.at((i + 0.5) / count)
                for floor in range(first, floors):
                    if floor == 0 and door_at is not None and np.hypot(*(p - door_at)) < 1.6:
                        continue
                    if rng.random() > odds:
                        continue
                    base = high + floor * fh
                    if floor >= 1 and balconies and balcony and f.length >= 4.0 and fh >= 2.6:
                        balconies -= 1
                        self.put(out, balcony, rng, p, base + cfg.get("balcony_height", 0.45), yaw, on_ground=False)
                        continue
                    roll = rng.random()
                    style = ("bay" if bay and floor >= 1 and roll < cfg.get("bay_window", 0.35) else
                             "grille" if (traditional and roll < 0.7) or roll < 0.2 else "shutter")
                    role = next((r for r in (f"window_{style}_{tint}", f"window_grille_{tint}") if self.has(r)), None)
                    if role:
                        self.put(out, role, rng, p, base + sill, yaw, on_ground=False)
                    if laundry and floor >= 1 and count == 1 and f.length >= 3.6:
                        laundry -= 1
                        self.put(out, "wall_laundry", rng, p, base + sill - 0.15, yaw, on_ground=False)

    def _roof(self, b, k: int, high: float, rng, out) -> None:
        if b.roof_shape != "flat" or b.kind not in DRESSED:
            return
        top = high + b.height
        cfg = self.cfg
        layout = roof_layout(b, self.kinds[b.district], roof_stream(self.seed, self.sid, k), self.roofs)
        area = layout.inner if layout.inner is not None else b.footprint
        for role, chance, margin in (("roof_tank", cfg.get("roof_tank", 0.3), 0.9),
                                     ("roof_dish", cfg.get("roof_dish", 0.2), 0.9),
                                     ("roof_laundry", cfg.get("roof_laundry", 0.15), 1.5),
                                     ("roof_pot", cfg.get("roof_pots", 0.15), 0.8)):
            if rng.random() >= chance:
                continue
            free = area.buffer(-margin)
            if layout.stair is not None:
                free = free.difference(layout.stair.buffer(margin))
            if free.is_empty:
                continue
            minx, miny, maxx, maxy = free.bounds
            for _ in range(8):
                x, y = rng.uniform(minx, maxx), rng.uniform(miny, maxy)
                if shapely.contains_xy(free, x, y):
                    self.put(out, role, rng, (x, y), top, rng.uniform(0, 6.28), on_ground=False)
                    break

    # --- trees ------------------------------------------------------------------------------
    def tree(self, k: int, t, z: float) -> Placement | None:
        """A planned tree as a kit piece (a Tounes Rush palm, or the generator's own tree), scaled to its height.

        None means the kit has no tree of that kind and the tile meshes it instead.
        """
        got = self.pick(f"tree_{t.kind}", self.rng("tree", k))
        if got is None:
            return None
        piece = self.kit.pieces[got[0]]
        scale = t.height / max(piece.top, 0.5)
        return Placement(got[0], t.x, t.y, z, float(self.rng("tree-turn", k).uniform(0, 6.28)), False, scale)

    # --- spans across streets ----------------------------------------------------------------
    def spans(self, k: int, tile) -> list:
        st = self.plan.streets[k]
        if st.kind not in ("alley", "souk", "street"):
            return []
        cfg = self.cfg
        step = 12.0 if st.kind == "souk" else 9.0
        out = []
        line = st.line
        for i in range(int(line.length // step)):
            d = (i + 0.5) * step
            p = line.interpolate(d)
            if not tile.covers(p):
                continue
            rng = self.rng("span", k, i)
            kind = self._span_kind(st.kind, rng.random())
            if kind is None:
                continue
            ends = self._across(line, d)
            if ends is None:
                continue
            (pa, top_a), (pb, top_b) = ends
            mid = (pa + pb) / 2
            ground = float(max(self.ground.surface(pa[0], pa[1]), self.ground.surface(pb[0], pb[1]),
                               self.ground.surface(mid[0], mid[1])))
            if kind == "sabat":
                floor, roof = ground + cfg.get("sabat_clearance", 3.3), min(top_a, top_b)
                if roof - floor >= 2.4 and np.hypot(*(pb - pa)) <= cfg.get("sabat_reach", 5.5):
                    out.append(Span("sabat", (pa[0], pa[1], floor), (pb[0], pb[1], floor), top=roof))
                continue
            z = {"laundry": rng.uniform(3.2, 5.5), "cable": rng.uniform(4.0, 6.5),
                 "lanterns": rng.uniform(3.9, 4.7), "bunting": rng.uniform(4.0, 5.0)}[kind] + ground
            z = min(z, min(top_a, top_b) - 0.6)
            if z < ground + 2.8:
                continue
            span = Span(kind, (pa[0], pa[1], z), (pb[0], pb[1], z), int(rng.integers(2 ** 31)))
            if kind == "lanterns":
                got = self.pick("hanging_lantern", rng)
                if got is None:
                    continue
                span.piece = got[0]
                span.step = max(1.6, 2.6 * self.kit.pieces[got[0]].height)
            out.append(span)
        return out

    def _span_kind(self, street_kind: str, roll: float) -> str | None:
        cfg = self.cfg
        if street_kind == "souk":
            options = (("lanterns", cfg.get("souk_lanterns", 0.5)), ("bunting", cfg.get("bunting", 0.2)))
        elif street_kind == "alley":
            options = (("sabat", cfg.get("sabat", 0.05)), ("laundry", cfg.get("laundry", 0.35)),
                       ("cable", cfg.get("cables", 0.1)))
        else:
            options = (("cable", cfg.get("cables", 0.1)),)
        for kind, chance in options:
            if roll < chance:
                return kind
            roll -= chance
        return None

    def _across(self, line, d: float):
        """The two walls facing each other across a street at distance d along it: ((point, top), (point, top))."""
        p = line.interpolate(d)
        a, b = line.interpolate(max(d - 0.5, 0.0)), line.interpolate(min(d + 0.5, line.length))
        t = np.array([b.x - a.x, b.y - a.y])
        if np.hypot(*t) < 1e-6:
            return None
        t /= np.hypot(*t)
        nrm = np.array([-t[1], t[0]])
        ends = [self._wall_hit(np.array([p.x, p.y]), nrm * s) for s in (1.0, -1.0)]
        return None if None in ends else ends

    def street_props(self, k: int, tile) -> list:
        """Things that belong to a street rather than a house: arches over alley mouths, decorated
        gates at the ends of souks, handcarts in the souks."""
        st = self.plan.streets[k]
        out: list = []
        role = {"alley": "alley_arch", "souk": "souk_gate"}.get(st.kind)
        if role and st.line.length >= 12.0 and self.has(role):
            for end, d in ((0, 2.0), (1, st.line.length - 2.0)):
                if tile.covers(st.line.interpolate(d)):
                    self._gate(k, end, d, role, out)
        spacing = self.cfg.get("street_lamps", {}).get(st.kind)
        if spacing and self.has("street_lamp"):
            self._lamps(k, float(spacing), tile, out)
        if st.kind == "souk" and self.has("souk_cart"):
            for i in range(int(st.line.length // 20.0)):
                d = (i + 0.5) * 20.0
                p = st.line.interpolate(d)
                rng = self.rng("cart", k, i)
                if tile.covers(p) and rng.random() < self.cfg.get("souk_cart", 0.2):
                    a, b = st.line.interpolate(max(d - 0.5, 0.0)), st.line.interpolate(min(d + 0.5, st.line.length))
                    t = np.array([b.x - a.x, b.y - a.y]) / max(math.hypot(b.x - a.x, b.y - a.y), 1e-9)
                    q = np.array([p.x, p.y]) + np.array([t[1], -t[0]]) * rng.uniform(-0.6, 0.6)
                    flip = math.pi if rng.random() < 0.5 else 0.0   # parked along the souk, either way
                    self.put(out, "souk_cart", rng, q, 0.0, yaw_of(t) + flip)
        return out

    def _lamps(self, k: int, spacing: float, tile, out: list) -> None:
        """Street lamps along both edges, staggered, leaning over the street."""
        st = self.plan.streets[k]
        line, half = st.line, st.width / 2 - 0.6
        for i in range(int(line.length // spacing)):
            d = (i + 0.5) * spacing
            a, b = line.interpolate(max(d - 0.5, 0.0)), line.interpolate(min(d + 0.5, line.length))
            t = np.array([b.x - a.x, b.y - a.y])
            if np.hypot(*t) < 1e-6:
                continue
            t /= np.hypot(*t)
            side = 1.0 if i % 2 else -1.0
            n = np.array([-t[1], t[0]]) * side            # from the center line toward this edge
            p = line.interpolate(d)
            q = np.array([p.x, p.y]) + n * half
            if tile.covers(shapely.Point(q)) and self.streets_at(q[None, :])[0] >= 0:
                self.put(out, "street_lamp", self.rng("lamp", k, i), q, 0.0, yaw_of(-n))

    def _gate(self, k: int, end: int, d: float, role: str, out: list) -> None:
        """An arch over an alley mouth, sized from wall to wall, or a souk gate standing free in the souk."""
        st = self.plan.streets[k]
        rng = self.rng("gate", k, end)
        if rng.random() >= self.cfg.get(role, 0.1):
            return
        ends = self._across(st.line, d)
        if ends is None:
            return
        (pa, top_a), (pb, top_b) = ends
        gap = float(np.hypot(*(pb - pa)))
        name, _ = self.pick(role, rng)
        piece = self.kit.pieces[name]
        if role == "alley_arch":   # the feet sink a little into both walls
            scale = (gap + 0.4) / max(piece.width, 0.5)
            fits = 0.8 <= scale <= self.cfg.get("alley_arch_scale", 1.6)
        else:                      # free standing, with room to walk around it
            scale = self.cfg.get("souk_gate_scale", 1.25)
            fits = gap >= piece.width * scale + 1.2
        mid = (pa + pb) / 2
        ground = float(self.ground.surface(mid[0], mid[1]))
        if not fits or ground + piece.height * scale > min(top_a, top_b):
            return
        w = (pb - pa) / gap   # the width runs across the street, the front along it
        out.append(Placement(name, float(mid[0]), float(mid[1]), 0.0, math.atan2(w[1], w[0]), True, scale))

    def _wall_hit(self, p: np.ndarray, direction: np.ndarray, reach: float = 7.0):
        seg = LineString([p, p + direction * reach])
        best = None
        for j in self.fp_tree.query(seg, predicate="intersects"):
            hit = seg.intersection(self.footprints[int(j)].exterior)
            for g in getattr(hit, "geoms", [hit]):
                if g.is_empty or g.geom_type != "Point":
                    continue
                dist = math.hypot(g.x - p[0], g.y - p[1])
                if best is None or dist < best[0]:
                    best = (dist, int(j), np.array([g.x, g.y]))
        if best is None or best[0] < 0.8:
            return None
        b = self.plan.buildings[best[1]]
        top = float(self.ground.height(best[2][0], best[2][1])) + b.height
        return best[2], top


def ground_heights(ground, placements) -> None:
    """Turn ground-relative heights into absolute ones on the drawn surface (street or ground)."""
    rel = [p for p in placements if p.on_ground]
    if not rel:
        return
    xy = np.array([(p.x, p.y) for p in rel])
    zs = ground.surface(xy[:, 0], xy[:, 1])
    for p, z in zip(rel, zs):
        p.z += float(z)
        p.on_ground = False


def building_highs(ground, buildings) -> np.ndarray:
    """Highest ground point under each footprint (as the tile mesher uses). Walls stay on the ground."""
    if not buildings:
        return np.zeros(0)
    rings = [np.asarray(b.footprint.exterior.coords) for b in buildings]
    counts = np.array([len(r) for r in rings])
    pts = np.concatenate(rings)
    hz = ground.height(pts[:, 0], pts[:, 1])
    return np.maximum.reduceat(hz, np.concatenate([[0], np.cumsum(counts)[:-1]]))
