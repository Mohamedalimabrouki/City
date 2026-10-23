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
from shapely.strtree import STRtree

from ..mesh.props import ARCADE
from ..rng import stream, weighted
from .arcades import Run, band, free_spans, layout, level_steps, spans_of, turn
from .geo import frame
from .massing import corner_faces, floors_at, main_mass, massed, probes, terrace_walls, wall_height
from .openings import DoorSpot, Walls, fits, joined, open_walls, path_to_street, piece_boxes, wall_arrays
from .roofs import roof_layout, roof_stream

DRESSED = {"house", "domed", "apartments", "villa"}
FRONT_PREF = {"souk": 3.0, "alley": 2.5, "street": 2.0, "boulevard": 1.5, "ring": 1.0, "arterial": 1.0,
              "corniche": 1.0, "connector": 0.5, "impasse": 0.3}   # an impasse door only when no street has room
LANES = ("alley", "impasse")   # narrow lanes: dressed alike (laundry, cables, arches)
DOOR_WALL = 2.3                # shortest street wall that takes a door; the main facade is one if any is
TRADITIONAL = {"medina", "village"}
NO_BOXES = (np.array([], dtype=object), np.zeros(0), np.zeros(0))   # piece_boxes of nothing


@dataclass
class Placement:
    piece: str
    x: float
    y: float
    z: float        # meters: above the ground at (x, y) when on_ground, else absolute
    yaw: float      # radians about up; the piece front turns to (-sin yaw, cos yaw)
    on_ground: bool = True
    scale: float = 1.0
    stretch: float = 1.0   # extra scale along the wall (x) only: arcade bays and long balconies fit their wall


@dataclass
class Span:
    kind: str       # laundry | cable | lanterns | bunting | sabat
    a: tuple        # (x, y, z) absolute; for a sabat, the two wall points at the room's floor
    b: tuple
    seed: int = 0   # for the details hanging on it (clothes, flags)
    piece: str = ""     # lanterns: the piece hanging from the rope
    step: float = 1.6   # lanterns: meters between two of them
    top: float = 0.0    # sabat: height of its roof, absolute
    depth: float = 3.4  # sabat: length of the room along the street


@dataclass
class Facade:
    a: np.ndarray
    b: np.ndarray
    n: np.ndarray   # outward normal (toward the street)
    length: float
    street: int
    kind: str
    wall: int = -1  # index in the counter-clockwise exterior ring

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
        self.every_home = bool(self.cfg.get("every_home", True))
        self._tables: dict = {}                  # role -> pieces, odds and sizes (_role_table)
        self._corners: dict = {}                 # terrain mesh corner heights near doors (drawn)
        self.open_cfg = self.cfg.get("open_walls", {})
        self.slab_cfg = self.cfg.get("slab", {})
        self.path_cfg = self.cfg.get("paths", {})
        self.lit_cfg = self.cfg.get("lit", {})
        self.arcade_cfg = {**ARCADE, **self.cfg["arcade"]} if "arcade" in self.cfg else {}
        self.iron_cfg = self.cfg.get("balcony_iron", {})
        self._zones = None                       # arcade bands of the whole city, for street lamps (lazy)
        self._sidewalks = None                   # STRtree of the sidewalk polygons (lazy)
        self._stairs = {n for r in ("stair_window", "stair_door") for n in (self.roles[r][0] if r in self.roles else [r])}
        targets = self.surfaces + [w.polygon for w in getattr(plan, "walks", ())]
        self.target_tree = STRtree(targets) if targets else None   # where a garden path may end

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

    def walls(self, b, k: int | None = None) -> Walls:
        """Exterior walls with the street in front of each; with `k`, also which ones face open ground."""
        p, q, n, length = wall_arrays(b.footprint)
        street = self.streets_at(probes(b, p, q, n))   # a cut corner's faces look out from the old corner
        opened = (open_walls(self.fp_tree, k, p, q, n, length, float(self.open_cfg.get("clear", 3.0)))
                  if k is not None else np.zeros(len(p), dtype=bool))
        return Walls(p, q, n, length, street, opened)

    def facades(self, b, walls: Walls | None = None) -> list:
        """Walls with a street surface 1.6 m in front of their middle: the ones dressed since the start."""
        w = walls if walls is not None else self.walls(b)
        return [Facade(w.a[k], w.b[k], w.n[k], float(w.length[k]), int(w.street[k]),
                       self.plan.streets[w.street[k]].kind, int(k))
                for k in np.nonzero((w.length > 1.5) & (w.street >= 0))[0]]

    # --- buildings ------------------------------------------------------------------------
    def building(self, k: int, high: float, paths: list | None = None) -> list:
        """Placements dressing building k (`high`: highest ground under it, as the tile mesher uses).

        The street walls, then the roof, draw from one stream `rng("b", k)` in a fixed order. A colonial
        building's arcade and iron balconies (prompt 22, no draw on that stream) come next; every
        home's main door, open-wall windows and an apartment block's stair doors after them, on
        their own streams, so nothing placed before them moves. `paths` collects the paved
        paths (point arrays) from doors on open ground to the street.
        """
        b = self.plan.buildings[k]
        if b.kind not in DRESSED:
            return []
        rng = self.rng("b", k)
        out: list = []
        slots: list = []
        walls = self.walls(b, k if self.every_home else None)
        front = self._street_side(b, k, self.facades(b, walls), high, rng, out, slots)
        street, arcade, iron, shadow = self._colonial(b, k, walls, high, out, slots)
        out[:] = street
        self._roof(b, k, high, rng, out)
        self._machines(b, high, out)
        out += arcade + iron
        self._terrace_windows(k, b, high, out)
        if self.every_home:
            boxes = self._boxes(walls, front, street + iron, shadow)
            spots = self._entrances(k, b, walls, front, boxes)
            self._homes(k, b, walls, spots, high, out, boxes)
            if paths is not None:
                paths += [s.path for s in spots if s.path is not None]
        if self.lit_cfg:
            self._light(k, b, high, out)
        return out

    def entrances(self, k: int) -> list:
        """Every door into dwelling k, main door first (one, or one per stair of an apartment block)."""
        b = self.plan.buildings[k]
        if b.kind not in DRESSED:
            return []
        walls = self.walls(b, k)
        out: list = []
        slots: list = []
        high = float(building_highs(self.ground, [b])[0])
        front = self._street_side(b, k, self.facades(b, walls), high, self.rng("b", k), out, slots)   # same draws
        street, _, iron, shadow = self._colonial(b, k, walls, high, out, slots)
        return self._entrances(k, b, walls, front, self._boxes(walls, front, street + iron, shadow))

    def door_spot(self, k: int) -> DoorSpot | None:
        """The main door of dwelling k, exactly where `building` puts it; None for other buildings.

        Interiors (prompt 44), entrances (71) and addresses (79) read doors here.
        """
        spots = self.entrances(k)
        return spots[0] if spots else None

    def _street_side(self, b, k: int, fac: list, high: float, rng, out: list, slots: list | None = None) -> tuple:
        """The street walls' door or shop and windows, as dressed since the start (draws on `rng`).

        Returns (main facade, door or shop center, "front" | "shop" | "cafe" | None, door piece, threshold).
        `slots` collects the windows placed (for the iron balconies).
        """
        if not fac:
            return None, None, None, None, None
        home = self.homes.get(k)
        color = home.door if home else "door_blue"
        wealth = home.wealth if home else 0.4
        district = self.kinds[b.district]
        floors = max(1, int(b.floors))
        main = max(fac, key=lambda f: (f.length >= DOOR_WALL, FRONT_PREF.get(f.kind, 0.0), f.length))
        height = float(wall_height(b, [main.a, main.at(0.5), main.b]).min())   # a set-back floor or a low wing
        door_at, kind, piece, z = self._front(main, district, color, wealth, height, rng, out)
        self._windows(k, fac, district, color, wealth, floors, b.height / floors, high, door_at, rng, out, slots)
        return main, door_at, kind, piece, z

    def drawn(self, x, y) -> np.ndarray:
        """`Ground.drawn` (the terrain mesh's height), with the mesh corners' heights cached: the doors
        and paths of neighbouring houses share corners, and each ground call costs the same for 1 or 100 points."""
        return self.ground.drawn(x, y, self._corner_heights)

    def seed_corners(self, i0: int, j0: int, heights: np.ndarray) -> None:
        """Store terrain mesh heights already computed by a tile: heights[r, c] at corner (i0 + c, j0 + r)."""
        rows, cols = heights.shape
        i, j = np.meshgrid(np.arange(i0, i0 + cols), np.arange(j0, j0 + rows))
        self._corners.update(zip(zip(i.ravel().tolist(), j.ravel().tolist()), heights.ravel().tolist()))

    def _corner_heights(self, i: np.ndarray, j: np.ndarray) -> np.ndarray:
        keys = list(zip(i.tolist(), j.tolist()))
        miss = [k for k in dict.fromkeys(keys) if k not in self._corners]
        if miss:
            m = np.array(miss, dtype=np.int64)
            for k, h in zip(miss, np.atleast_1d(self.ground.height(m[:, 0] * self.ground.step,
                                                                   m[:, 1] * self.ground.step)).tolist()):
                self._corners[k] = h
        return np.array([self._corners[k] for k in keys])

    def front_surface(self, c: np.ndarray, n: np.ndarray) -> float:
        """Height of the drawn street surface just in front of a wall (the door threshold's level)."""
        q = c + n * self.cfg.get("threshold_reach", 0.5)
        return float(self.ground.surface(float(q[0]), float(q[1])))

    def _front(self, f: Facade, district, color, wealth, height, rng, out) -> tuple:
        """(center, "shop" | "cafe" | "front", door piece, threshold) of the main facade; Nones when too short."""
        cfg = self.cfg
        souk = self.souk_of.get(f.street) if f.kind == "souk" else None
        if souk is not None and f.length >= 3.0 and rng.random() < cfg.get("shop_on_souk", 0.85):
            c, z = self._shop(f, souk, rng, out)
            return c, "shop", None, z
        if district == "colonial" and f.length >= 3.2 and rng.random() < cfg.get("cafe", 0.3):
            c, z = self._cafe(f, rng, out)
            return c, "cafe", None, z
        if f.length < DOOR_WALL:
            return None, None, None, None
        yaw, u, n = yaw_of(f.n), f.u, f.n
        s = f.length * 0.5 + rng.uniform(-1.0, 1.0) * max(0.0, f.length * 0.5 - 1.2)   # door center along the wall
        c = f.at(s / f.length)

        def room(offset: float, half: float) -> bool:   # does a piece this wide fit on the wall there?
            return half <= s + offset <= f.length - half

        def side() -> float:
            return 1.0 if rng.random() < 0.5 else -1.0

        rich = wealth > cfg.get("rich_door", 0.72) and district in TRADITIONAL | {"colonial", "residential"}
        z = self.front_surface(c, n)
        piece = self.put(out, color + "_rich" if rich else color, rng, c, z, yaw, on_ground=False)
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
        return c, "front", piece, z

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

    def _shop(self, f: Facade, souk, rng, out) -> tuple:
        """A souk shop front with its goods: (center, threshold)."""
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
        return c, z

    def _cafe(self, f: Facade, rng, out) -> tuple:
        """A cafe front with tables outside: (center, threshold)."""
        yaw, u, n = yaw_of(f.n), f.u, f.n
        c = f.at(0.5)
        z = self.front_surface(c, n)
        self.put(out, "shop_front", rng, c, z, yaw, on_ground=False)
        self.put(out, "awning", rng, c, z, yaw, on_ground=False)
        reach = self.arcade_cfg.get("cafe_reach", 1.7) if self._arcaded(f.kind, "colonial") else 1.7   # under an arcade
        for k in range(int(rng.integers(1, 3))):
            p = c + u * (k - 0.5) * 1.9 + n * reach
            self.put(out, "cafe_set", rng, p, 0.0, yaw + rng.uniform(-0.4, 0.4))
        return c, z

    def _floors_on(self, b, a, u, s) -> np.ndarray:
        """Floors of wall (a, u) at window centers `s` m along it: where a massed building's parts differ
        (a set-back top floor, a lower step or wing), the lower side under the window's whole width."""
        s = np.asarray(s, dtype=np.float64)
        if not massed(b):
            return np.full(len(s), max(1, int(b.floors)))
        half = float(self.cfg.get("window_half", 1.3))
        both = np.concatenate([a + np.outer(s - half, u), a + np.outer(s + half, u)])
        tops = floors_at(b, both)
        return np.minimum(tops[:len(s)], tops[len(s):])

    def _windows(self, k, fac, district, color, wealth, floors, fh, high, door_at, rng, out, slots=None) -> None:
        cfg = self.cfg
        b = self.plan.buildings[k]
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
            tops = self._floors_on(b, f.a, f.u, (np.arange(count) + 0.5) * f.length / max(count, 1))
            for i in range(count):
                p = f.at((i + 0.5) / count)
                for floor in range(first, int(tops[i])):
                    if floor == 0 and door_at is not None and np.hypot(*(p - door_at)) < 1.6:
                        continue
                    if rng.random() > odds:
                        continue
                    base = high + floor * fh
                    if floor >= 1 and balconies and balcony and f.length >= 4.0 and fh >= 2.6:
                        balconies -= 1
                        if district in self.iron_cfg.get("districts", ()):   # ville nouvelle: no mashrabiya
                            self._iron_window(k, f, i, count, floor, tint, p, base + sill, yaw, balcony, rng, out, slots)
                            continue
                        self.put(out, balcony, rng, p, base + cfg.get("balcony_height", 0.45), yaw, on_ground=False)
                        continue
                    role = self._window_role(tint, traditional, bay, floor, rng.random())
                    if role:
                        self.put(out, role, rng, p, base + sill, yaw, on_ground=False)
                        if slots is not None:
                            slots.append([f, i, count, floor, p, False, False])
                    if laundry and floor >= 1 and count == 1 and f.length >= 3.6:
                        laundry -= 1
                        self.put(out, "wall_laundry", rng, p, base + sill - 0.15, yaw, on_ground=False)
                        if role and slots is not None:
                            slots[-1][6] = True

    def _iron_window(self, k, f, i, count, floor, tint, p, z, yaw, balcony, rng, out, slots) -> None:
        """A rich colonial household's balcony spot: a window that gets an iron balcony (in `_iron`).
        The old mashrabiya took exactly one draw on `rng`; so does this, every other piece stays put."""
        if balcony in self.roles:
            rng.random()
        wrng = self.rng("balcony-iron", k, "window", f.wall, floor, i)
        role = self._window_role(tint, False, False, floor, wrng.random())
        if role:
            self.put(out, role, wrng, p, z, yaw, on_ground=False)
            if slots is not None:
                slots.append([f, i, count, floor, p, True, False])

    def _window_role(self, tint: str, traditional: bool, bay: bool, floor: int, roll: float) -> str | None:
        style = ("bay" if bay and floor >= 1 and roll < self.cfg.get("bay_window", 0.35) else
                 "grille" if (traditional and roll < 0.7) or roll < 0.2 else "shutter")
        return next((r for r in (f"window_{style}_{tint}", f"window_grille_{tint}") if self.has(r)), None)

    def _roof(self, b, k: int, high: float, rng, out) -> None:
        if b.roof_shape != "flat" or b.kind not in DRESSED:
            return
        main = main_mass(b)
        top = high + main.top                      # the main roof: a set-back top floor, the tallest step
        cfg = self.cfg
        layout = roof_layout(b, self.kinds[b.district], roof_stream(self.seed, self.sid, k), self.roofs)
        area = layout.inner if layout.inner is not None else main.polygon
        for role, chance, margin in (("roof_tank", cfg.get("roof_tank", 0.3), 0.9),
                                     ("roof_dish", cfg.get("roof_dish", 0.2), 0.9),
                                     ("roof_laundry", cfg.get("roof_laundry", 0.15), 1.5),
                                     ("roof_pot", cfg.get("roof_pots", 0.15), 0.8)):
            if rng.random() >= chance:
                continue
            free = area.buffer(-margin)
            for room in layout.rooms:             # stair room, menzah, machinery, a corner dome
                free = free.difference(room.buffer(margin))
            if free.is_empty:
                continue
            minx, miny, maxx, maxy = free.bounds
            for _ in range(8):
                x, y = rng.uniform(minx, maxx), rng.uniform(miny, maxy)
                if shapely.contains_xy(free, x, y):
                    self.put(out, role, rng, (x, y), top, rng.uniform(0, 6.28), on_ground=False)
                    break

    def _machines(self, b, high: float, out: list) -> None:
        """Water tanks on steel stands where massing put them (lift motor rooms are drawn by the mesher)."""
        if "tank_stand" not in self.kit.pieces:
            return
        for m in b.machines:
            if m["kind"] == "tank":
                out.append(Placement("tank_stand", float(m["x"]), float(m["y"]), high + float(m["z"]),
                                     float(m["angle"]), on_ground=False))

    def _terrace_windows(self, k: int, b, high: float, out: list) -> None:
        """Windows on the walls of a set-back top floor, or of a villa's main part, facing its terrace:
        on every floor above the terrace, in the household's color (own stream, no other draw moves)."""
        walls = terrace_walls(b)
        if not walls:
            return
        home = self.homes.get(k)
        tint = (home.door if home else "door_blue")[5:]
        rng = self.rng("terrace", k)
        fh = b.height / max(1, int(b.floors))
        sill = float(self.cfg.get("window_sill", 0.95))
        spacing = float(self.cfg.get("window_spacing", 3.2))
        corner = float(self.open_cfg.get("corner", 0.3))
        for a, c, n, length, first, last in walls:
            count = int((length - 2 * corner) // spacing)
            u, yaw = (c - a) / max(length, 1e-9), yaw_of(n)
            for i in range(count):
                p = a + u * (i + 0.5) * length / count
                for floor in range(first, last):
                    role = self._window_role(tint, False, False, floor, rng.random())
                    if role:
                        self.put(out, role, rng, p, high + floor * fh + sill, yaw, on_ground=False)

    # --- colonial arcades and iron balconies (prompt 22) ----------------------------------------
    def _colonial(self, b, k: int, walls: Walls, high: float, street: list, slots: list) -> tuple:
        """A colonial building's arcade and iron balconies, after its street walls are dressed (no draw on
        `rng("b", k)`). Returns (street pieces kept, arcade pieces, balconies, pillar boxes): old pieces the
        arcade's slab or pillars would cut (a vine or a hood over a door) are left out, and the pillar
        boxes (from the wall out to each pillar) keep every home's new doors under the arches."""
        district = self.kinds[b.district]
        arcade, shadow, runs = [], NO_BOXES, []
        if self.arcade_cfg and district in self.arcade_cfg.get("districts", ()):
            runs, corners, bent = self._arcade_runs(b, k, walls, street, high)
            if runs:
                arcade, shadow, solid = self._arcade_pieces(b, walls, high, runs, corners, bent)
                street = self._clear_of(street, solid)
        iron = self._iron(k, b, high, runs, slots, street) if district in self.iron_cfg.get("districts", ()) else []
        return street, arcade, iron, shadow

    def _arcaded(self, kind: str, district: str) -> bool:
        """Does a wall of this district facing a street of this kind carry an arcade?"""
        cfg = self.arcade_cfg
        return bool(cfg) and district in cfg.get("districts", ()) and kind in cfg.get("kinds", ())

    def _first(self, role: str) -> str | None:
        """The first piece listed for a role (no draw), or the piece of that name."""
        found = self.roles.get(role)
        return found[0][0] if found else (role if role in self.kit.pieces else None)

    def _on_sidewalk(self, pts: np.ndarray) -> np.ndarray:
        if self._sidewalks is None:
            polys = [w.polygon for w in getattr(self.plan, "walks", ()) if w.kind == "sidewalk"]
            self._sidewalks = STRtree(polys) if polys else False
        out = np.zeros(len(pts), dtype=bool)
        if self._sidewalks is not False and len(pts):
            inp, _ = self._sidewalks.query(shapely.points(pts), predicate="within")
            out[inp] = True
        return out

    def _arcade_runs(self, b, k: int, walls: Walls, street: list, high: float) -> tuple:
        """The arcade runs of a colonial building, laid out in bays, the walls whose end a corner piece
        continues and those whose end a bend piece continues. Arcades go on every wall facing one of
        `kinds`; a square corner between two of them gets a corner piece, a corner onto another street a
        corner piece and `wrap` bays round it; walls meeting at a shallow convex bend carry one arcade
        round it; a cut street corner (prompt 23) carries it on: a bay on each face, a bend piece (a pier)
        at each turn of 45 or 22.5 degrees, and `wrap` bays into a side street without an arcade."""
        cfg = self.arcade_cfg
        if self._first("arcade_bay") is None:
            return [], [], []
        m = len(walls.length)
        arc = np.array([walls.street[i] >= 0 and walls.length[i] > 1.5 and
                        self.plan.streets[walls.street[i]].kind in cfg["kinds"] for i in range(m)])
        bends = [self._bend_piece(turn(walls.u[i], walls.u[(i + 1) % m])) for i in range(m)]
        faces = self._corner_arcs(b, walls, arc, bends)
        if not arc.any():
            return [], [], []
        runs = {int(i): r for i in np.nonzero(arc)[0]
                if (r := self._free_run(k, walls, int(i), 0.0, float(walls.length[i]), faces[i])) is not None}
        corners, bent, depth = [], [], float(cfg["depth"])
        wrap = float(cfg["wrap"]) * float(cfg["nominal"])
        for i in range(m):
            j = (i + 1) % m
            if not (arc[i] or arc[j]):
                continue
            t = turn(walls.u[i], walls.u[j])
            ri, rj = runs.get(i), runs.get(j)
            at_i = ri is not None and ri.s1 >= walls.length[i] - 1e-6
            at_j = rj is not None and rj.s0 <= 1e-6
            if 0.0 < t <= cfg["bend"] and at_i and at_j:          # a shallow convex bend: the fronts meet
                e = depth * math.tan(math.radians(t) / 2)
                ri.s1, rj.s0, ri.fix1, rj.fix0 = ri.s1 + e, rj.s0 - e, True, True
            elif bends[i] is not None and self._bend_free(walls, i, t, faces[i] or faces[j]):   # a cut corner's turn
                at_i, at_j = self._wrap(k, walls, runs, arc, i, j, wrap, at_i, at_j)
                if at_i and at_j:
                    runs[i].fix1 = runs[j].fix0 = runs[i].hold1 = runs[j].hold0 = True
                    bent.append(i)
            elif abs(t - 90.0) <= cfg["corner_angle"] and wrap > 0 and self._corner_free(k, walls, i):
                at_i, at_j = self._wrap(k, walls, runs, arc, i, j, wrap, at_i, at_j)
                if at_i and at_j:
                    runs[i].fix1 = runs[j].fix0 = runs[i].hold1 = runs[j].hold0 = True
                    corners.append(i)
        bays = [(*cfg["bay"], float(cfg["nominal"])), (*cfg["bay_relaxed"], float(cfg["nominal"]))]
        boxes = piece_boxes(self.kit, street, high) if street else NO_BOXES
        out = []
        for i, run in sorted(runs.items()):
            run.cuts = layout(run, self._pillar_zones(walls, i, run, street, boxes), bays)
            if run.cuts is not None:
                out.append(run)
        ends = {r.wall: r for r in out}
        meet = lambda i: (i in ends and (i + 1) % m in ends and ends[i].cuts[-1] >= walls.length[i] - 1e-6
                          and ends[(i + 1) % m].cuts[0] <= 1e-6)
        return out, [i for i in corners if meet(i)], [(i, bends[i]) for i in bent if meet(i)]

    def _wrap(self, k: int, walls: Walls, runs: dict, arc, i: int, j: int, wrap: float, at_i: bool, at_j: bool) -> tuple:
        """At a corner or a cut corner's last turn: `wrap` bays round into a side street without an arcade
        of its own. Returns whether runs now reach the corner from both walls."""
        if wrap <= 0:
            return at_i, at_j
        if not at_j and not arc[j] and at_i and walls.street[j] >= 0:      # round into the side street
            rj = self._free_run(k, walls, j, 0.0, min(wrap, float(walls.length[j])))
            at_j = rj is not None and rj.s0 <= 1e-6
            if at_j:
                runs[j] = rj
        elif not at_i and not arc[i] and at_j and walls.street[i] >= 0:
            li = float(walls.length[i])
            ri = self._free_run(k, walls, i, max(0.0, li - wrap), li)
            at_i = ri is not None and ri.s1 >= li - 1e-6
            if at_i:
                runs[i] = ri
        return at_i, at_j

    def _bend_piece(self, t: float) -> str | None:
        """The pier piece for a convex turn of t degrees at a cut corner (45: a chamfer, 22.5: a round)."""
        tol = float(self.arcade_cfg.get("bend_tol", 2.5))
        for angle, name in ((45.0, "arcade_bend"), (22.5, "arcade_bend_round")):
            if abs(t - angle) <= tol and name in self.kit.pieces:
                return name
        return None

    def _corner_arcs(self, b, walls: Walls, arc, bends: list) -> np.ndarray:
        """The faces of a cut corner carry the arcade of a facade they turn from (in place on `arc`): their
        probe may find the side street in the junction instead. Returns a bool per wall: is it a face?"""
        m = len(arc)
        faces = np.zeros(m, dtype=bool)
        for face in corner_faces(b, walls.a, walls.b):
            faces |= face
            for _ in range(int(face.sum())):
                for i in np.nonzero(face & ~arc & (walls.street >= 0))[0]:
                    if (arc[i - 1] and bends[i - 1]) or (arc[(i + 1) % m] and bends[i]):
                        arc[i] = True
        return faces

    def _bend_free(self, walls: Walls, i: int, t: float, corner: bool = False) -> bool:
        """Room for a bend piece past the end of wall i: nothing built in its wedge, its pier on the sidewalk
        (or, at a cut corner, on the paved corner of the lot the cut leaves open)."""
        cfg = self.arcade_cfg
        d, pd, cp = float(cfg["depth"]), float(cfg["pillar"][1]), float(cfg["cornice"])
        j = (i + 1) % len(walls.length)
        v, ni, nj = walls.b[i], walls.n[i], walls.n[j]
        nb = (ni + nj) / max(float(np.hypot(*(ni + nj))), 1e-9)
        c = math.cos(math.radians(t) / 2)
        wedge = shapely.Polygon([v, v + ni * (d + cp), v + nb * (d + cp) / c, v + nj * (d + cp)])
        idx = self.fp_tree.query(wedge, predicate="intersects")
        if len(idx) and (shapely.area(shapely.intersection(wedge, self.fp_tree.geometries[idx])) > 1e-3).any():
            return False
        return corner or bool(self._on_sidewalk((v + nb * (d - pd / 2) / c)[None, :])[0])

    def _free_run(self, k: int, walls: Walls, i: int, lo: float, hi: float, face: bool = False) -> Run | None:
        """The part of wall i between lo and hi an arcade may cover: nothing built within its depth (this
        building round a concave corner, a neighbour), sidewalk under its pillars (or, on a face of a cut
        corner, the corner of the lot the cut leaves open). Where the next building stands in line within
        2 x `join` m, the run reaches half way across the gap to meet that building's arcade."""
        cfg = self.arcade_cfg
        d, pd, reach = float(cfg["depth"]), float(cfg["pillar"][1]), 2 * float(cfg["join"])
        a, u, n = walls.a[i], walls.u[i], walls.n[i]
        poly = band(a, u, n, lo - reach, hi + reach, 0.02, d + float(cfg["cornice"]) + 0.05)
        blocked = []
        idx = self.fp_tree.query(poly, predicate="intersects")
        if len(idx):
            cut = shapely.intersection(poly, self.fp_tree.geometries[idx])
            big = shapely.area(cut) > 1e-3
            blocked += [(s0, s1, "built") for s0, s1 in spans_of(cut[big], a, u)]
        s = np.arange(lo - reach, hi + reach + 1e-9, 0.25)
        off = ~self._on_sidewalk(a + np.outer(s, u) + n * (d - pd / 2))
        if face:                                           # the lot's open corner in front of a cut
            off &= (s < lo) | (s > hi)
        blocked += [(v - 0.13, v + 0.13, "walk") for v in s[off]]
        spans = [(max(f0, lo), min(f1, hi), f0, f1) for f0, f1, _, _ in free_spans(lo - reach, hi + reach, blocked)]
        spans = [sp for sp in spans if sp[1] - sp[0] > 0.5]
        if not spans:
            return None
        s0, s1, f0, f1 = max(spans, key=lambda sp: sp[1] - sp[0])
        run = Run(i, s0, s1)
        for end, sign in ((lo, -1.0), (hi, 1.0)):
            gap = self._side_gap(k, a, u, n, end, sign, reach)
            if gap is None:
                continue
            if sign < 0 and s0 == lo and f0 <= lo - gap / 2:
                run.s0, run.fix0 = lo - gap / 2, True
            elif sign > 0 and s1 == hi and f1 >= hi + gap / 2:
                run.s1, run.fix1 = hi + gap / 2, True
        return run

    def _side_gap(self, k: int, a, u, n, end: float, sign: float, reach: float) -> float | None:
        """Meters from a wall end to the next building in line with it (its footprint just behind the
        wall line, within `reach`), or None."""
        s0, s1 = (end, end + reach) if sign > 0 else (end - reach, end)
        probe = band(a, u, n, s0, s1, -1.0, -0.02)
        idx = [j for j in self.fp_tree.query(probe, predicate="intersects") if j != k]
        if not idx:
            return None
        cut = shapely.intersection(probe, self.fp_tree.geometries[idx])
        cut = cut[shapely.area(cut) > 1e-4]
        if not len(cut):
            return None
        ext = spans_of(cut, a, u)
        return float(max(0.0, ext[:, 0].min() - end if sign > 0 else end - ext[:, 1].max()))

    def _corner_free(self, k: int, walls: Walls, i: int) -> bool:
        """Room for a corner piece past the end of wall i: nothing built there, its pier on the sidewalk."""
        cfg = self.arcade_cfg
        d, pd = float(cfg["depth"]), float(cfg["pillar"][1])
        v, u, n = walls.b[i], walls.u[i], walls.n[i]
        sq = band(v, u, n, 0.02, d + float(cfg["cornice"]), 0.02, d + float(cfg["cornice"]))
        idx = self.fp_tree.query(sq, predicate="intersects")
        if len(idx) and (shapely.area(shapely.intersection(sq, self.fp_tree.geometries[idx])) > 1e-3).any():
            return False
        return bool(self._on_sidewalk((v + (u + n) * (d - pd / 2))[None, :])[0])

    def _pillar_zones(self, walls: Walls, i: int, run: Run, street: list, boxes: tuple) -> list:
        """Spans of wall i where no pillar may stand: in front of a door or shop front on the wall, and
        wherever a piece already placed (a cafe table) reaches into the pillars' strip."""
        cfg = self.arcade_cfg
        d, (pw, pd), gap = float(cfg["depth"]), cfg["pillar"], float(cfg["gap"])
        if not street:
            return []
        a, u, n = walls.a[i], walls.u[i], walls.n[i]
        grow = pw / 2 + gap
        strip = band(a, u, n, run.s0 - 2.0, run.s1 + 2.0, d - pd - gap, d + gap)
        hit = shapely.intersects(boxes[0], strip)
        yaw = yaw_of(n)
        zones = []
        for m, p in enumerate(street):
            pc = self.kit.pieces[p.piece]
            xy = np.array([p.x, p.y]) - a
            on_wall = (pc.category in ("door", "shop") and abs(float(xy @ n)) < 0.1
                       and math.cos(p.yaw - yaw) > 0.99)
            if on_wall:                                    # a piece's +x runs along -u
                c = float(xy @ u)
                zones.append((c - pc.bounds[1][0] * p.stretch - grow, c - pc.bounds[0][0] * p.stretch + grow))
            elif hit[m]:
                s0, s1 = spans_of(boxes[0][m:m + 1], a, u)[0]
                zones.append((s0 - grow, s1 + grow))
        return zones

    def _arcade_pieces(self, b, walls: Walls, high: float, runs: list, corners: list, bent: list = ()) -> tuple:
        """The bays (stretched along the wall) and corner pieces of laid-out runs, each run made level in
        steps along its sidewalk, its terrace never more than `above` over the first floor line. Returns
        (placements, pillar boxes from the wall out, solid boxes of pillars and slabs)."""
        cfg = self.arcade_cfg
        d, (pw, pd), cp = float(cfg["depth"]), cfg["pillar"], float(cfg["cornice"])
        nominal, h, sink = float(cfg["nominal"]), float(cfg["height"]), float(cfg["sink"])
        hc = h - 0.3                                       # the walkway ceiling (mesh/props._arcade_dims)
        fh = b.height / max(1, int(b.floors))
        zmax = high + fh + float(cfg["above"]) - h
        mids = [(r.cuts[:-1] + r.cuts[1:]) / 2 for r in runs]
        pts = np.concatenate([walls.a[r.wall] + np.outer(c, walls.u[r.wall]) + walls.n[r.wall] * (d - pd / 2)
                              for r, c in zip(runs, mids)])
        zs = np.atleast_1d(self.ground.surface(pts[:, 0], pts[:, 1]))
        bay, out, shadow, solid = self._first("arcade_bay"), [], [], []
        at = 0
        for r, c in zip(runs, mids):
            a, u, n = walls.a[r.wall], walls.u[r.wall], walls.n[r.wall]
            r.z = np.minimum(level_steps(zs[at:at + len(c)], float(cfg["step"])), zmax) + 0.003 * (r.wall % 2)
            at += len(c)
            width = np.diff(r.cuts)
            yaw = yaw_of(n)
            for s, w, z in zip(c, width, r.z):
                p = a + u * s
                out.append(Placement(bay, float(p[0]), float(p[1]), float(z), yaw, on_ground=False,
                                     stretch=float(w / nominal)))
            half = pw / 2 * width / nominal
            for e, s in enumerate(r.cuts):                 # each pillar: half of the bay before, half of the one after
                left, right = (half[e - 1] if e > 0 else 0.0), (half[e] if e < len(half) else 0.0)
                zz = r.z[max(e - 1, 0):e + 1]
                lo, hi = float(zz.min()), float(zz.max())
                shadow.append((band(a, u, n, s - left, s + right, 0.0, d), lo - sink, hi + hc))
                solid.append((band(a, u, n, s - left, s + right, d - pd - 0.05, d + 0.05), lo - sink, hi + hc))
            solid += [(band(a, u, n, s0, s1, -0.1, d + cp), float(z) + hc - 0.02, float(z) + h + 0.05)
                      for s0, s1, z in zip(r.cuts[:-1], r.cuts[1:], r.z)]
        ends = {r.wall: r for r in runs}
        corner = self._first("arcade_corner")
        for i in corners if corner else []:
            j = (i + 1) % len(walls.length)
            z = min(float(ends[i].z[-1]), float(ends[j].z[0])) + 0.004   # its terrace wins a sliver of overlap
            v, u, n = walls.b[i], walls.u[i], walls.n[i]
            # a piece's +x runs against its wall's direction, so turned to the next wall's street the corner
            # piece lies past the end of wall i, in the square in front of the corner; a corner a few degrees
            # off square splits the difference between the two walls
            off = math.radians(turn(u, walls.u[j]) - 90.0) / 2
            out.append(Placement(corner, float(v[0]), float(v[1]), z, yaw_of(walls.n[j]) - off, on_ground=False))
            solid.append((band(v, u, n, 0.0, d + cp, 0.0, d + cp), z - sink, z + h + 0.05))
        for i, name in bent:                               # a cut corner's turns: a pier on the bisector
            j = (i + 1) % len(walls.length)
            z = min(float(ends[i].z[-1]), float(ends[j].z[0]))
            v, ni, nj = walls.b[i], walls.n[i], walls.n[j]
            nb = (ni + nj) / max(float(np.hypot(*(ni + nj))), 1e-9)
            c = math.cos(math.radians(turn(walls.u[i], walls.u[j])) / 2)
            out.append(Placement(name, float(v[0]), float(v[1]), z, yaw_of(nb), on_ground=False))
            wedge = shapely.Polygon([v, v + ni * (d + cp), v + nb * (d + cp) / c, v + nj * (d + cp)])
            solid.append((wedge, z - sink, z + h + 0.05))
        pack = lambda boxes: (np.array([q[0] for q in boxes], dtype=object), np.array([q[1] for q in boxes]),
                              np.array([q[2] for q in boxes]))
        return out, pack(shadow), pack(solid)

    def _clear_of(self, pieces: list, solid: tuple) -> list:
        """The pieces whose box cuts none of the arcade's solid parts (slab and pillars); doors and shop
        fronts always stay (the pillars keep clear of them and the ceiling stands above them)."""
        if not pieces or not len(solid[0]):
            return pieces
        polys, z0, z1 = piece_boxes(self.kit, pieces, 0.0)
        rel = np.array([p.on_ground for p in pieces])
        if rel.any():                                      # ground pieces: on the drawn surface under them
            xy = np.array([(p.x, p.y) for p in pieces])[rel]
            lift = np.atleast_1d(self.ground.surface(xy[:, 0], xy[:, 1]))
            z0, z1 = z0.copy(), z1.copy()
            z0[rel] += lift
            z1[rel] += lift
        keep = []
        for m, p in enumerate(pieces):
            if self.kit.pieces[p.piece].category in ("door", "shop"):
                keep.append(p)
                continue
            near = (solid[1] < z1[m]) & (solid[2] > z0[m])
            cut = near.any() and (shapely.area(shapely.intersection(polys[m], solid[0][near])) > 1e-4).any()
            if not cut:
                keep.append(p)
        return keep

    def _iron(self, k: int, b, high: float, runs: list, slots: list, street: list) -> list:
        """Wrought-iron balconies on a colonial building's street windows (own streams, one per floor of
        each facade): a floor has them with a chance that grows with the household's wealth, then each
        window, two neighbours sometimes sharing one long balcony. A rich household's old mashrabiya
        spot always gets one. None on the floor right above an arcade (its terrace), none where a
        clothesline hangs or another piece is in the way."""
        cfg = self.iron_cfg
        single, long_ = self._first("balcony_iron"), self._first("balcony_iron_long")
        if not slots or single is None:
            return []
        home = self.homes.get(k)
        wealth = home.wealth if home else 0.4
        chance = float(np.clip(cfg.get("row", 0.4) + cfg.get("wealth", 0.6) * (wealth - 0.5), 0.0, 1.0))
        width, span = float(cfg.get("width", 1.2)), float(cfg.get("span", 3.2))
        g0, g1 = cfg.get("long_gap", [3.0, 3.8])
        fh = b.height / max(1, int(b.floors))
        sill = float(self.cfg.get("window_sill", 0.95))
        pw = float(self.arcade_cfg.get("pillar", [0.8])[0]) if self.arcade_cfg else 0.0
        covered = {}
        for r in runs:
            covered.setdefault(r.wall, []).append((r.cuts[0] - pw, r.cuts[-1] + pw))
        boxes = piece_boxes(self.kit, [p for p in street if self.kit.pieces[p.piece].category != "window"], high)
        rows: dict = {}
        for slot in slots:
            rows.setdefault((slot[0].wall, slot[3]), {})[slot[1]] = slot
        out = []
        for (wall, floor), cols in rows.items():
            f = next(iter(cols.values()))[0]
            count = next(iter(cols.values()))[2]
            gap = f.length / max(count, 1)
            rng = self.rng("balcony-iron", k, wall, floor)
            row = rng.random() < chance
            draws = rng.random((count, 2))

            def wanted(i: int) -> bool:
                slot = cols.get(i)
                if slot is None or slot[6] or not (slot[5] or (row and draws[i, 0] < cfg.get("window", 0.85))):
                    return False
                s = float(np.dot(slot[4] - f.a, f.u))
                return not (floor == 1 and any(s0 < s < s1 for s0, s1 in covered.get(wall, ())))

            z = high + floor * fh + sill
            i = 0
            while i < count:
                if not wanted(i):
                    i += 1
                    continue
                p = cols[i][4]
                if (long_ and wanted(i + 1) and g0 <= gap <= g1 and draws[i, 1] < cfg.get("long", 0.35)):
                    q = (p + cols[i + 1][4]) / 2
                    cand = Placement(long_, float(q[0]), float(q[1]), z, yaw_of(f.n), False,
                                     stretch=float((gap + width) / (span + width)))
                    if self._clear(cand, boxes):
                        out.append(cand)
                        i += 2
                        continue
                cand = Placement(single, float(p[0]), float(p[1]), z, yaw_of(f.n), False)
                if self._clear(cand, boxes):
                    out.append(cand)
                i += 1
        return out

    def _clear(self, cand: Placement, boxes: tuple) -> bool:
        """Does a placed piece keep clear of every box (in plan and height)?"""
        if not len(boxes[0]):
            return True
        poly, z0, z1 = piece_boxes(self.kit, [cand], 0.0)
        near = (boxes[1] < z1[0] + 0.05) & (boxes[2] > z0[0] - 0.05)
        return not (near.any() and shapely.intersects(poly[0], boxes[0][near]).any())

    def _arcade_band(self, pts: np.ndarray) -> np.ndarray:
        """True for points within the arcade bands of the city (every colonial wall on an arcaded street,
        out to the pillars plus `lamp_clear`, and as far past each end): where no street lamp stands."""
        return self._band_push(pts, float(self.arcade_cfg["depth"]) + float(self.arcade_cfg["lamp_clear"]))[0] >= 0

    def _tree_reach(self) -> float:
        cfg = self.arcade_cfg
        return float(cfg["depth"]) + float(cfg["cornice"]) + float(cfg["tree_trunk"]) + float(cfg["tree_clear"])

    def _band_push(self, pts: np.ndarray, reach: float) -> tuple:
        """For points within `reach` m of an arcaded wall (its band, as far past each end): the wall's index
        in the zones (-1 where none) and how far the point must move out along its normal to clear it."""
        wall, push = np.full(len(pts), -1), np.zeros(len(pts))
        if self._zones is None:
            self._zones = self._arcade_zones()
        if self._zones is False or not len(pts):
            return wall, push
        tree, a, n = self._zones
        inp, hit = tree.query(shapely.points(pts), predicate="within")
        need = reach - np.einsum("ij,ij->i", pts[inp] - a[hit], n[hit])
        for i, j, e in zip(inp.tolist(), hit.tolist(), need.tolist()):
            if e > push[i]:
                wall[i], push[i] = j, e
        return wall, push

    def tree_spots(self, xy: np.ndarray) -> tuple:
        """Where planned trees stand (prompt 22): a trunk inside an arcade band (wall to pillar face and
        cornice, plus `tree_trunk` and `tree_clear`) moves straight out toward the curb until it clears;
        it is left out when that point is not on a sidewalk at least `tree_curb` m inside its edge, or lies
        in another arcade's band. The plan's trees never change. Returns (points, kept, away): `away` is
        the outward normal of the arcade a moved tree stands by (zero for the others)."""
        xy = np.array(xy, dtype=np.float64).reshape(-1, 2)
        kept, away = np.ones(len(xy), dtype=bool), np.zeros((len(xy), 2))
        if not self.arcade_cfg or not len(xy):
            return xy, kept, away
        reach = self._tree_reach()
        wall, push = self._band_push(xy, reach)
        moved = np.nonzero(wall >= 0)[0]
        if not len(moved):
            return xy, kept, away
        away[moved] = self._zones[2][wall[moved]]
        xy[moved] += away[moved] * (push[moved, None] + 1e-3)
        again, _ = self._band_push(xy[moved], reach)
        on = self._on_sidewalk(xy[moved])
        for m, i in enumerate(moved.tolist()):
            ok = again[m] < 0 and on[m]
            if ok:
                pt = shapely.Point(xy[i])
                walk = self._sidewalks.geometries[self._sidewalks.query(pt, predicate="within")]
                ok = bool(shapely.distance(shapely.boundary(walk), pt).min() >= float(self.arcade_cfg["tree_curb"]))
            kept[i] = ok
        return xy, kept, away

    def _arcade_zones(self):
        """(STRtree of the arcade bands, wall start points, outward normals) of the whole city, or False."""
        cfg = self.arcade_cfg
        if not cfg:
            return False
        reach = max(float(cfg["depth"]) + float(cfg["lamp_clear"]), self._tree_reach())
        rows = [wall_arrays(b.footprint) for b in self.plan.buildings
                if b.kind in DRESSED and self.kinds[b.district] in cfg["districts"]]
        if not rows:
            return False
        a, q, n, length = (np.concatenate([r[m] for r in rows]) for m in range(4))
        street = self.streets_at((a + q) / 2 + n * 1.6)
        kinds = set(cfg["kinds"])
        arc = np.array([street[m] >= 0 and length[m] > 1.5 and self.plan.streets[street[m]].kind in kinds
                        for m in range(len(a))], dtype=bool)
        u = (q - a) / np.maximum(length, 1e-9)[:, None]
        wrap = float(cfg["wrap"]) * float(cfg["bay_relaxed"][1])
        polys, keep, at = [], [], 0
        for r in rows:                                    # each building's walls, as a ring
            idx = np.arange(at, at + len(r[0]))
            at += len(r[0])
            for e, m in enumerate(idx):
                lo, hi = None, None
                if arc[m]:
                    lo, hi = -reach, length[m] + reach
                elif street[m] >= 0 and wrap > 0:         # the bays an arcade turns into a side street
                    if arc[idx[(e - 1) % len(idx)]]:
                        lo, hi = -reach, min(wrap, length[m]) + reach
                    if arc[idx[(e + 1) % len(idx)]]:
                        lo, hi = (-reach if lo is not None else max(0.0, length[m] - wrap) - reach), length[m] + reach
                if lo is not None:
                    polys.append(band(a[m], u[m], n[m], lo, hi, 0.0, reach))
                    keep.append(m)
        if not keep:
            return False
        return STRtree(polys), a[keep], n[keep]

    # --- every home: main doors, open walls, apartment blocks (prompt 20.1) -------------------
    def _boxes(self, walls: Walls, front: tuple, dressed: list, shadow: tuple = NO_BOXES) -> tuple:
        """Boxes of the street walls' pieces, when a new door or an open wall's windows must avoid them
        (`shadow`: an arcade's pillars, from the wall out to them)."""
        if front[2] == "front" and not (walls.open & (walls.street < 0)).any():
            return piece_boxes(self.kit, [], 0.0)
        return joined(piece_boxes(self.kit, dressed, front[4] or 0.0), shadow)   # ground pieces stand by the door or shop

    def _entrances(self, k: int, b, walls: Walls, front: tuple, boxes: tuple) -> list:
        """The doors of dwelling k, main door first. `boxes`: the street walls' pieces already placed."""
        main, door_at, kind, piece, z = front
        if kind == "front":                       # the street door, exactly as dressed since the start
            return [DoorSpot(float(door_at[0]), float(door_at[1]), float(main.n[0]), float(main.n[1]),
                             z, main.street, "street", "front", main.wall, piece=piece)]
        near = self._nearest_street(b)
        if kind is None and self._is_slab(b):
            return self._stair_doors(k, b, walls, near)
        if z is None and main is not None:        # a street wall too short for a door: its windows still count
            z = self.front_surface(main.at(0.5), main.n)
        return [self._house_door(k, b, walls, main, door_at, kind, z or 0.0, near, boxes)]

    def _is_slab(self, b) -> bool:
        return b.kind == "apartments" and self.kinds[b.district] == "modern"

    def _nearest_street(self, b) -> tuple:
        """(index, nearest point on its surface) of the street nearest to a footprint; (-1, None) without streets."""
        if self.surface_tree is None:
            return -1, None
        j = int(min(self.surface_tree.query_nearest(b.footprint)))
        q = shapely.get_coordinates(shapely.shortest_line(b.footprint, self.surfaces[j]))[1]
        return j, q

    def _toward(self, walls: Walls, idx, q) -> list:
        """Wall indices sorted so the ones facing point q come first, nearest first."""
        if q is None:
            return sorted(idx, key=lambda i: -walls.length[i])
        keys = []
        for i in idx:
            u = walls.u[i]
            s = float(np.clip(np.dot(q - walls.a[i], u), 0.0, walls.length[i]))
            d = q - (walls.a[i] + u * s)
            dist = float(np.hypot(*d))
            keys.append((float(np.dot(walls.n[i], d)) <= 0.3 * dist, dist, int(i)))
        return [i for _, _, i in sorted(keys)]

    @staticmethod
    def _positions(length: float, half: float, corner: float, s0: float, step: float = 0.25, side: float = 0.0) -> list:
        """Door centers along a wall: from s0 outward both ways (or only toward `side`), corners kept free."""
        lo, hi = half + corner, length - half - corner
        if lo > hi:
            return []
        out = [] if side else [min(max(s0, lo), hi)]
        for i in range(1, int((hi - lo) / step) + 2):
            for s in ((s0 + side * i * step,) if side else (s0 + i * step, s0 - i * step)):
                if lo <= s <= hi:
                    out.append(s)
        return out

    def _house_door(self, k: int, b, walls: Walls, main, door_at, kind, base, near: tuple, boxes) -> DoorSpot:
        """The main door of a home without a street door: beside its shop or cafe, on another street
        wall, on a wall facing open ground toward the nearest street, or squeezed toward that street."""
        cfg = self.open_cfg
        home = self.homes.get(k)
        color = home.door if home else "door_blue"
        wealth = home.wealth if home else 0.4
        district = self.kinds[b.district]
        rich = wealth > self.cfg.get("rich_door", 0.72) and district in TRADITIONAL | {"colonial", "residential"}
        drng = self.rng("house-door", k)
        narrow = self.pick(f"house_door_{color[5:]}", drng) or self.pick(color, drng)
        corner, gap, clear = cfg.get("corner", 0.3), cfg.get("gap", 0.2), cfg.get("door_clear", 0.9)
        j, q = near
        tries = []                                 # (wall, positions, reach, piece)
        if kind in ("shop", "cafe"):
            s0 = float(np.dot(door_at - walls.a[main.wall], walls.u[main.wall]))
            half = self.kit.pieces[narrow[0]].width / 2
            sides = (1.0, -1.0) if drng.random() < 0.5 else (-1.0, 1.0)
            spots = [s for sd in sides for s in self._positions(walls.length[main.wall], half, corner,
                                                                 s0 + sd * half, side=sd)]
            tries.append((main.wall, spots, "street", narrow))
        others = [i for i in np.nonzero((walls.street >= 0) & (walls.length > 1.5))[0]
                  if main is None or i != main.wall]
        opened = self._toward(walls, np.nonzero(walls.open & (walls.street < 0))[0], q)
        if others or opened:                       # a full house door, unless it belongs beside a shop
            piece = narrow if kind in ("shop", "cafe") else (
                self.pick(color + "_rich" if rich else color, self.rng("door", k)) or narrow)
            others.sort(key=lambda i: (-FRONT_PREF.get(self.plan.streets[walls.street[i]].kind, 0.0), -walls.length[i]))
            tries += [(i, None, "street", piece) for i in others] + [(i, None, "open", piece) for i in opened]
        tries += [(i, None, "enclosed", narrow) for i in self._toward(walls, range(len(walls.length)), q)]
        for i, spots, reach, (name, _) in tries:
            pc = self.kit.pieces[name]
            a, u, n, length = walls.a[i], walls.u[i], walls.n[i], walls.length[i]
            if spots is None:
                s0 = length / 2 if reach == "street" or q is None else float(np.dot(q - a, u))
                spots = self._positions(length, pc.width / 2, corner, s0)
            for s in spots:
                c = a + u * s                      # near enough in height to test overlaps: the shop's threshold
                if reach == "enclosed" or fits(pc, c[0], c[1], yaw_of(n), base, boxes, grow=gap, depth=clear):
                    street = int(walls.street[i]) if reach == "street" else j
                    return self._spots([c], n, i, street, reach, "house" if kind else "door", [name], district)[0]
        i = int(np.argmax(walls.length))           # no wall long enough anywhere: the middle of the longest
        return self._spots([walls.a[i] + walls.u[i] * walls.length[i] / 2], walls.n[i], i, j, "enclosed", "door",
                           [narrow[0]], district)[0]

    def _spots(self, cs, n, wall: int, street: int, reach: str, kind: str, pieces: list, district: str) -> list:
        """DoorSpots for doors at points `cs` on one wall, their thresholds read in one go. A door on
        open ground in a garden district gets a paved path to the street; its threshold is the path's top."""
        cfg = self.path_cfg
        width, lift = float(cfg.get("width", 1.4)), float(cfg.get("lift", 0.04))
        paths = [None] * len(cs)
        if reach == "open" and district in cfg.get("districts", ()) and self.target_tree is not None:
            paths = [path_to_street(c, n, self.target_tree, self.fp_tree, width, float(cfg.get("reach", 40.0)),
                                    float(cfg.get("step", 4.0)), self.ground.step) for c in cs]
        front = np.array([c + n * self.cfg.get("threshold_reach", 0.5) for c in cs])
        z = np.zeros(len(cs))
        for m, path in enumerate(paths):          # on a path: its top, as drawn on the terrain mesh
            if path is not None:
                sides = self._path_sides(path, width)
                z[m] = float(np.mean(self.drawn(sides[:, 0], sides[:, 1]))) + lift
        bare = np.array([path is None for path in paths])
        paved = bare & (self.streets_at(front) >= 0) if reach != "street" else bare
        if paved.any():                           # on a street or its sidewalk: as the street doors
            z[paved] = self.ground.surface(front[paved, 0], front[paved, 1])
        ground = bare & ~paved
        if ground.any():                          # on open ground: the terrain as drawn
            z[ground] = self.drawn(front[ground, 0], front[ground, 1])
        return [DoorSpot(float(c[0]), float(c[1]), float(n[0]), float(n[1]), float(zz), int(street), reach, kind,
                         int(wall), path, piece) for c, zz, path, piece in zip(cs, z, paths, pieces)]

    @staticmethod
    def _path_sides(path: np.ndarray, width: float) -> np.ndarray:
        """The two edge points of a path 0.5 m in front of the door (its second point), where add_ribbon
        drapes it on the terrain mesh (`Ground.drawn`): the threshold is their mean height plus the lift."""
        t0, t1 = path[1] - path[0], path[2] - path[1] if len(path) > 2 else path[1] - path[0]
        t0, t1 = t0 / np.hypot(*t0), t1 / np.hypot(*t1)
        vt = (t0 + t1) / np.hypot(*(t0 + t1))
        side = np.array([-vt[1], vt[0]]) * width / 2 / float(np.clip(np.dot(vt, t0), 0.5, 1.0))
        return np.array([path[1] + side, path[1] - side])

    def _stair_doors(self, k: int, b, walls: Walls, near: tuple) -> list:
        """An apartment block's stair doors, every 20-25 m along the long side facing the nearest street,
        each in a window column (the column above it holds the staircase windows). When neighbours
        leave no straight path from that side, the other long side is used if it has one."""
        cfg = self.slab_cfg
        long = walls.length >= float(cfg.get("long", 0.6)) * frame(b.footprint)[2]
        idx = np.nonzero(long)[0] if long.any() else [int(np.argmax(walls.length))]
        order = self._toward(walls, idx, near[1])
        order = [i for i in order if walls.open[i]] + [i for i in order if not walls.open[i]]
        best = None
        for i in order:
            doors = self._stair_row(k, b, walls, i, near[0])
            if best is None or sum(d.path is not None for d in doors) > sum(d.path is not None for d in best):
                best = doors
            if all(d.path is not None for d in best) or not walls.open[i]:
                break
        return best

    def _stair_row(self, k: int, b, walls: Walls, i: int, nearest: int) -> list:
        """The stair doors along wall i: one per 20-25 m, each in the window column nearest its share's middle."""
        cfg = self.slab_cfg
        length = float(walls.length[i])
        cols = self._columns(length, float(cfg.get("bay", 3.2)))
        lo, hi = cfg.get("stair_spacing", [20.0, 25.0])
        count = max(1, int(length / ((lo + hi) / 2) + 0.5))
        picks = sorted({int(np.argmin(np.abs(cols - (d + 0.5) * length / count))) for d in range(count)})
        reach = "street" if walls.street[i] >= 0 else "open" if walls.open[i] else "enclosed"
        street = int(walls.street[i]) if reach == "street" else nearest
        names = [(self.pick("stair_door", self.rng("stair", k, d)) or self.pick("door_blue", self.rng("stair", k, d)))[0]
                 for d in range(len(picks))]
        cs = [walls.a[i] + walls.u[i] * cols[col] for col in picks]
        return self._spots(cs, walls.n[i], i, street, reach, "stair", names, self.kinds[b.district])

    @staticmethod
    def _columns(length: float, bay: float) -> np.ndarray:
        """Centers of evenly spaced window columns, at least `bay` apart, half a bay from each end."""
        count = int(length // bay)
        return (np.arange(count) + 0.5) * length / count if count else np.array([length / 2])

    def _homes(self, k: int, b, walls: Walls, spots: list, high: float, out: list, boxes: tuple) -> None:
        """Place the new doors, then windows on the walls facing open ground (all after the old pieces)."""
        doors = [Placement(s.piece, s.x, s.y, s.z, yaw_of(s.normal), on_ground=False)
                 for s in spots if s.kind != "front" and s.piece]
        out += doors
        if not (walls.open & (walls.street < 0)).any():
            return
        boxes = joined(boxes, piece_boxes(self.kit, doors, 0.0))
        if self._is_slab(b):
            self._slab_windows(k, b, walls, spots, high, boxes, out)
        else:
            self._open_windows(k, b, walls, high, boxes, out)

    def _role_table(self, role: str):
        """(names, cumulative odds, extra heights, half widths, bottoms) of a role or piece, cached;
        None when the kit has nothing for it. Picks agree with `pick` for the same random number."""
        if role not in self._tables:
            found = self.roles.get(role)
            if found is None and role in self.kit.pieces:
                found = ([role], np.ones(1), [0.0])
            if found is not None:
                names, odds, heights = found
                pcs = [self.kit.pieces[n] for n in names]
                found = (names, np.asarray(odds), np.asarray(heights, dtype=np.float64),
                         np.array([pc.width / 2 for pc in pcs]), np.array([pc.bottom for pc in pcs]))
            self._tables[role] = found
        return self._tables[role]

    def _wall_pieces(self, out: list, cells: list, rng, walls: Walls, i: int, boxes) -> None:
        """Windows and balcony pieces on wall i: one (s along the wall, z, roles to try) per cell.

        A cell takes its first role whose piece keeps clear of the corners and of every piece already
        on the building (a balcony that does not fit falls back to a window). One draw per cell;
        placements keep the order of the cells.
        """
        if not cells:
            return
        cfg = self.open_cfg
        corner, grow = float(cfg.get("corner", 0.3)), float(cfg.get("gap", 0.2)) / 2
        a, u, length, yaw = walls.a[i], walls.u[i], float(walls.length[i]), yaw_of(walls.n[i])
        top = float(boxes[2].max()) + 0.1 if len(boxes[0]) else -np.inf
        xs = rng.random(len(cells))
        s = np.array([c[0] for c in cells])
        z = np.array([c[1] for c in cells])
        pts = a + np.outer(s, u)
        placed: dict = {}
        todo = list(range(len(cells)))
        for level in range(max(len(c[2]) for c in cells)):
            groups: dict = {}
            for idx in todo:
                if level < len(cells[idx][2]):
                    groups.setdefault(cells[idx][2][level], []).append(idx)
            todo = []
            for (role, dz), idx in groups.items():
                table = self._role_table(role)
                if table is None:
                    todo += idx
                    continue
                names, odds, heights, halves, bottoms = table
                idx = np.array(idx)
                m = np.minimum(np.searchsorted(odds, xs[idx], side="right"), len(names) - 1)
                zz = z[idx] + dz + heights[m]
                ok = (halves[m] + corner <= s[idx]) & (s[idx] <= length - halves[m] - corner)
                for q, cell in enumerate(idx):
                    pc = self.kit.pieces[names[m[q]]]
                    x, y = pts[cell]
                    if ok[q] and (zz[q] + bottoms[m[q]] > top or fits(pc, x, y, yaw, zz[q], boxes, grow=grow)):
                        placed[cell] = Placement(names[m[q]], float(x), float(y), float(zz[q]), yaw, on_ground=False)
                    else:
                        todo.append(cell)
        out += [placed[cell] for cell in sorted(placed)]

    def _slab_windows(self, k: int, b, walls: Walls, spots: list, high: float, boxes, out: list) -> None:
        """A modern block's open walls: a window in every column on every floor (ground floor too),
        balconies stacked in a regular rhythm of columns, staircase windows above each stair door."""
        cfg = self.slab_cfg
        rng = self.rng("open", k)
        tint = weighted(rng, cfg.get("tints", [["white", 1]]))
        window = [(f"slab_window_{tint}", float(self.cfg.get("window_sill", 0.95)))]
        period = offset = 0
        if rng.random() < cfg.get("balconies", 0.85):
            lo, hi = cfg.get("balcony_period", [2, 3])
            period = int(rng.integers(lo, hi + 1))
            offset = int(rng.integers(period))
        floors = max(1, int(b.floors))
        fh = b.height / floors
        landing = fh / 2 + float(cfg.get("stair_window", 0.55))
        flen = frame(b.footprint)[2]
        for i in np.nonzero(walls.open & (walls.street < 0) & (walls.length > 1.5))[0]:
            length = float(walls.length[i])
            long = length >= float(cfg.get("long", 0.6)) * flen
            bay = float(cfg.get("bay" if long else "gable_bay", 3.2))
            if bay <= 0:
                continue                              # blind gable ends
            cols = self._columns(length, bay)
            tops = self._floors_on(b, walls.a[i], walls.u[i], cols)   # a stepped slab: each part its floors
            stairs = {int(np.argmin(np.abs(cols - np.dot(s.point - walls.a[i], walls.u[i])))) for s in spots
                      if s.kind == "stair" and s.wall == i}
            cells = []
            for col, s in enumerate(cols):
                if col in stairs:                     # half landings above the stair door
                    cells += [(s, high + f * fh, [("stair_window", landing)]) for f in range(1, int(tops[col]) - 1)]
                    continue
                balcony = long and period and (col - offset) % period == 0
                cells += [(s, high + f * fh, [("slab_balcony", 0.0)] + window if balcony and f >= 1 else window)
                          for f in range(int(tops[col]))]
            self._wall_pieces(out, cells, rng, walls, int(i), boxes)

    def _open_windows(self, k: int, b, walls: Walls, high: float, boxes, out: list) -> None:
        """Windows on walls facing open ground, by the district's rules (traditional houses look inward:
        upper floors only, about one window in two)."""
        cfg = self.open_cfg
        district = self.kinds[b.district]
        first = int(cfg.get("first", {}).get(district, 1))
        share = float(cfg.get("share", {}).get(district, 0.5))
        floors = max(1, int(b.floors))
        if first >= floors:
            return
        home = self.homes.get(k)
        color = home.door if home else "door_blue"
        wealth = home.wealth if home else 0.4
        traditional = district in TRADITIONAL
        bay = traditional and wealth > self.cfg.get("bay_wealth", 0.55)
        fh = b.height / floors
        sill = float(self.cfg.get("window_sill", 0.95))
        spacing = float(self.cfg.get("window_spacing", 3.2))
        rng = self.rng("open", k)
        for i in np.nonzero(walls.open & (walls.street < 0) & (walls.length > 1.5))[0]:
            length = float(walls.length[i])
            count = int(length // spacing)
            tops = self._floors_on(b, walls.a[i], walls.u[i], (np.arange(count) + 0.5) * length / max(count, 1))
            cells = []
            for col in range(count):
                for floor in range(first, int(tops[col])):
                    if rng.random() > share:
                        continue
                    role = self._window_role(color[5:], traditional, bay, floor, rng.random())
                    if role is not None:
                        cells.append(((col + 0.5) * length / count, high + floor * fh, [(role, sill)]))
            self._wall_pieces(out, cells, rng, walls, int(i), boxes)

    # --- lit windows at night (prompt 21) -------------------------------------------------------
    def _light(self, k: int, b, high: float, out: list) -> None:
        """Light the windows of the rooms where someone is still up, after every piece is placed.

        A lit window becomes its `_lit` twin (the same piece with `glass_lit`); a kit window keeps its
        piece and gets its `_pane_lit` right after it. One draw on `rng("lit", k, ...)` per flat: the
        same floor of one side of the building (in a modern block, one half of one stair's section), or
        per staircase (its windows and door together). No other stream is touched, so the day look
        stays exactly as it was.
        """
        pieces = self.kit.pieces
        todo = [i for i, p in enumerate(out) if p.piece + "_lit" in pieces or p.piece + "_pane_lit" in pieces]
        if not todo:
            return
        chance, stair = self._lit_chance(k, b), float(self.lit_cfg.get("stair", 0.5))
        floors = max(1, int(b.floors))
        fh = b.height / floors
        sections = self._sections(b) if self._is_slab(b) else None
        draws: dict = {}
        lit = set()
        for i in todo:
            p = out[i]
            part = sections(p.x, p.y) if sections else (0, 0)
            if p.piece in self._stairs:
                key, odds = ("stair", part[0]), stair
            else:
                key, odds = (round(p.yaw, 4), max(0, int((p.z - high + 0.01) // fh))) + part, chance
            if key not in draws:
                draws[key] = self.rng("lit", k, *key).random()
            if draws[key] < odds:
                lit.add(i)
        new = []
        for i, p in enumerate(out):
            new.append(p)
            if i not in lit:
                continue
            if p.piece + "_lit" in pieces:
                p.piece += "_lit"
            else:
                new.append(Placement(p.piece + "_pane_lit", p.x, p.y, p.z, p.yaw, p.on_ground, p.scale))
        out[:] = new

    def _lit_chance(self, k: int, b) -> float:
        """Chance that a room of dwelling k is lit at night: bigger households and late trades stay
        up, two-person households (often an older couple) and early trades go to bed, wealth a little."""
        cfg = self.lit_cfg
        home = self.homes.get(k)
        if home is None:
            return float(cfg.get("other", 0.1))
        p = (cfg.get("base", 0.34) + cfg.get("member", 0.025) * (home.members - cfg.get("members_ref", 5))
             + cfg.get("wealth", 0.12) * (home.wealth - 0.5) + cfg.get("trades", {}).get(home.trade, 0.0)
             + cfg.get("district", {}).get(self.kinds[b.district], 0.0))
        if home.members <= 2:
            p += cfg.get("couple", -0.08)
        lo, hi = cfg.get("range", [0.05, 0.85])
        return float(np.clip(p, lo, hi))

    def _sections(self, b):
        """For a modern block: (x, y) -> (stair section, half of it) along the block's length. The
        sections are the stair doors' shares (one per 20-25 m, as `_stair_row` spaces them); each stair
        serves one flat on either side of it on every floor."""
        cx, cy, length, _, angle = frame(b.footprint)
        lo, hi = self.slab_cfg.get("stair_spacing", [20.0, 25.0])
        count = max(1, int(length / ((lo + hi) / 2) + 0.5))
        seg = max(length / count, 1e-6)
        c, s = math.cos(angle), math.sin(angle)

        def part(x: float, y: float) -> tuple:
            t = (x - cx) * c + (y - cy) * s + length / 2
            sec = min(max(int(t // seg), 0), count - 1)
            return sec, int(t - sec * seg >= seg / 2)
        return part

    # --- trees ------------------------------------------------------------------------------
    def tree(self, k: int, t, z: float, away=None) -> Placement | None:
        """A planned tree as a kit piece (a Tounes Rush palm, or the generator's own tree), scaled to its height.

        None means the kit has no tree of that kind and the tile meshes it instead. `away`: a tree moved
        out of an arcade's way (`tree_spots`) turns so its lean (the date palm leans toward its -x) points
        that way, over the street, never back into the arcade.
        """
        got = self.pick(f"tree_{t.kind}", self.rng("tree", k))
        if got is None:
            return None
        piece = self.kit.pieces[got[0]]
        scale = t.height / max(piece.top, 0.5)
        yaw = float(self.rng("tree-turn", k).uniform(0, 6.28))
        if away is not None and np.any(away):
            yaw = math.atan2(-away[1], -away[0])
        return Placement(got[0], t.x, t.y, z, yaw, False, scale)

    # --- spans across streets ----------------------------------------------------------------
    def spans(self, k: int, tile) -> list:
        st = self.plan.streets[k]
        if st.kind not in ("alley", "souk", "street", "impasse"):
            return []
        cfg = self.cfg
        step = 12.0 if st.kind == "souk" else 9.0
        out = self._covered(k, tile) if st.covered > 0 else []
        line = st.line
        for i in range(int(line.length // step)):
            d = (i + 0.5) * step
            p = line.interpolate(d)
            if not tile.covers(p) or d < st.covered + 2.0 * bool(st.covered):   # nothing under the room
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
        elif street_kind in LANES:   # an impasse's only sabat is the planned one over its mouth
            options = ((("sabat", cfg.get("sabat", 0.05)),) if street_kind == "alley" else ()) + (
                ("laundry", cfg.get("laundry", 0.35)), ("cable", cfg.get("cables", 0.1)))
        else:
            options = (("cable", cfg.get("cables", 0.1)),)
        for kind, chance in options:
            if roll < chance:
                return kind
            roll -= chance
        return None

    def _mouth(self, k: int) -> float | None:
        """Distance along impasse k from its first point (in the street it opens on) to its mouth on
        the block's edge, its second point; None for a branch off another impasse."""
        c = self.plan.streets[k].line.coords
        if not any(self.plan.streets[int(j)].kind != "impasse"
                   for j in self.surface_tree.query(shapely.Point(c[0]), predicate="within")):
            return None
        return math.dist(c[0], c[1])

    def _covered(self, k: int, tile) -> list:
        """The room over the first meters of a covered impasse, from wall to wall, when both houses
        are tall enough to carry it with headroom below (the same rule as an alley's sabat)."""
        st = self.plan.streets[k]
        d0 = self._mouth(k)
        if d0 is None:
            return []
        d = d0 + st.covered / 2
        if d >= st.line.length or not tile.covers(st.line.interpolate(d)):
            return []
        ends = self._across(st.line, d)
        if ends is None:
            return []
        (pa, top_a), (pb, top_b) = ends
        mid = (pa + pb) / 2
        ground = float(max(self.ground.surface(pa[0], pa[1]), self.ground.surface(pb[0], pb[1]),
                           self.ground.surface(mid[0], mid[1])))
        floor, roof = ground + self.cfg.get("sabat_clearance", 3.3), min(top_a, top_b)
        if roof - floor < 2.4 or np.hypot(*(pb - pa)) > self.cfg.get("sabat_reach", 5.5):
            return []
        return [Span("sabat", (pa[0], pa[1], floor), (pb[0], pb[1], floor), top=roof, depth=st.covered)]

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
        if st.kind == "impasse" and not st.covered and self.has("alley_arch"):
            d = self._mouth(k)                    # an arch just inside the mouth, never over the dead end
            if d is not None and st.line.length >= d + 4.0 and tile.covers(st.line.interpolate(d + 1.0)):
                self._gate(k, 0, d + 1.0, "alley_arch", out, self.cfg.get("impasse_arch", 0.3))
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
        """Street lamps along both edges, staggered, leaning over the street. Along a colonial arcade
        (prompt 22) a lamp moves `lamp_shift` m out toward the curb, beyond the pillars, or is left out
        when that is not on a sidewalk clear of them."""
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
            if self.arcade_cfg and self._arcade_band(q[None, :])[0]:   # along an arcade: out to the curb
                q = q - n * float(self.arcade_cfg["lamp_shift"])
                if self._arcade_band(q[None, :])[0] or not self._on_sidewalk(q[None, :])[0]:
                    continue
            if tile.covers(shapely.Point(q)) and self.streets_at(q[None, :])[0] >= 0:
                self.put(out, "street_lamp", self.rng("lamp", k, i), q, 0.0, yaw_of(-n))

    def _gate(self, k: int, end: int, d: float, role: str, out: list, chance: float | None = None) -> None:
        """An arch over an alley mouth, sized from wall to wall, or a souk gate standing free in the souk."""
        st = self.plan.streets[k]
        rng = self.rng("gate", k, end)
        if rng.random() >= (self.cfg.get(role, 0.1) if chance is None else chance):
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
        top = float(self.ground.height(best[2][0], best[2][1])) + float(wall_height(b, best[2])[0])
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
