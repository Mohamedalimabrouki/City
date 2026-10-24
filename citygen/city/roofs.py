"""Roof life: the parapet around a flat roof, the stair room standing on some of them, and the
menzah (a small roof room) of a few old-town houses.

`roof_layout` is the one place that decides them, on a building's main roof (its top floor, its
tallest step: city/massing.py). The tile mesher draws what it returns (the parapet band, the
stair room, the menzah); the Dresser keeps its tanks, dishes, laundry and pots on the free roof
it leaves, so nothing ever stands in a roof room, on machinery or outside the parapet. Each
building has its own random stream (`roof_stream`), shared by both. `roof_layouts` adds the
parapets of a building's lower roofs (a set-back floor's terrace, lower steps), without draws.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from shapely.geometry import Point

from ..mesh.builder import rectangle
from ..rng import stream
from .geo import frame
from .massing import main_mass, masses, roof_obstacles

STAIR_KINDS = ("house", "apartments", "villa")


@dataclass
class RoofLayout:
    """What a flat roof carries: the parapet ring, the roof it leaves, and a stair room."""

    height: float = 0.0            # parapet height above the roof, meters (0 = none)
    band: object = None            # the parapet footprint: a ring with the roof area as a hole
    inner: object = None           # the roof area inside the parapet
    stair: object = None           # the stair room footprint, or None
    stair_height: float = 0.0      # meters above the roof
    door: tuple | None = None      # (x, y, yaw): center of its door, yaw = outward direction
    door_width: float = 0.9
    door_height: float = 1.95
    menzah: object = None          # the menzah footprint, or None
    menzah_height: float = 0.0
    menzah_door: tuple | None = None
    menzah_windows: list = field(default_factory=list)   # [(x, y, yaw)] window centers on its walls
    blocked: list = field(default_factory=list)          # machinery, a corner dome (city/massing.py)

    @property
    def rooms(self) -> list:
        """Everything standing on the roof deck: stair room, menzah, machinery, a corner dome."""
        return [r for r in (self.stair, self.menzah) if r is not None] + list(self.blocked)

    @property
    def free(self):
        """The roof a prop may stand on: inside the parapet and outside the stair room and the rest."""
        if self.inner is None:
            return None
        out = self.inner
        for room in self.rooms:
            out = out.difference(room)
        return out


def roof_stream(seed: int, city_id: int, k: int):
    """The random stream of one building's roof (same for the mesh and the dressing)."""
    return stream(seed, "roof", city_id, k)


def _parapet(poly, kind: str, cfg: dict) -> RoofLayout:
    """The parapet band and the roof inside it of one flat roof outline."""
    height = float(cfg.get("parapet_height", {}).get(kind, cfg.get("parapet_fallback", 0.7)))
    thick = float(cfg.get("parapet_thickness", 0.2))
    inner = poly.buffer(-thick, join_style="mitre")
    if inner.is_empty or inner.area <= 0.0:
        return RoofLayout()
    band = poly.difference(inner)
    if band.is_empty:
        return RoofLayout()
    return RoofLayout(height, band, inner)


def roof_layout(b, kind: str, rng, cfg: dict) -> RoofLayout:
    """Parapet, stair room and menzah of building `b`'s main roof in a district of `kind` (`[roofs]`)."""
    if b.roof_shape != "flat" or b.battlement is not None:   # a kasbah wall has its own battlement
        return RoofLayout()
    poly = main_mass(b).polygon
    layout = _parapet(poly, kind, cfg)
    if layout.band is None:
        return layout
    layout.blocked = roof_obstacles(b)
    _stair_room(b, poly, layout, kind, rng, cfg)
    if b.menzah:
        _menzah(b, poly, layout, cfg)
    return layout


def roof_layouts(b, kind: str, rng, cfg: dict) -> list:
    """[(Mass, RoofLayout)] for every roof of building b: the main one as `roof_layout` decides it, the
    lower flat ones (a set-back floor's terrace, lower steps, a villa's wing) with their parapet only;
    a roof's deck leaves out the mass standing on it."""
    out = []
    ms = masses(b)
    for m in ms:
        if m.main:
            layout = roof_layout(b, kind, rng, cfg)
        elif m.shape == "flat":
            layout = _parapet(m.polygon, kind, cfg)
            layout.blocked = roof_obstacles(b, m)
            for o in ms:
                if layout.inner is not None and o.base > 0.0 and abs(o.base - m.top) < 1e-6:
                    layout.inner = layout.inner.difference(o.polygon)
        else:
            layout = RoofLayout()
        out.append((m, layout))
    return out


def _stair_room(b, poly, layout: RoofLayout, kind: str, rng, cfg: dict) -> None:
    chance = float(cfg.get("stair_room", {}).get(kind, 0.0))
    if chance <= 0.0 or b.kind not in STAIR_KINDS or (b.top and "x" not in b.top):
        return
    if rng.random() >= chance:
        return
    side = float(cfg.get("stair_side", 2.5))
    gap = float(cfg.get("stair_gap", 0.25))
    started = int(rng.integers(4))
    for turn in range(4):
        stair = _stair_candidate(b, poly, layout, side, gap, (started + turn) % 4)
        if stair is None:
            continue
        free = None
        if layout.blocked:
            free = layout.inner.difference(stair)
            for o in layout.blocked:
                free = free.difference(o)
        door = _stair_door(layout, stair, float(cfg.get("stair_door_reach", 0.8)), free)
        if door is None:   # a room with no way out is not a stair room
            continue
        layout.stair = stair
        layout.stair_height = float(cfg.get("stair_height", 2.4))
        layout.door = door
        layout.door_width = float(cfg.get("stair_door_width", 0.9))
        layout.door_height = float(cfg.get("stair_door_height", 1.95))
        return


def _stair_candidate(b, poly, layout: RoofLayout, side: float, gap: float, which: int):
    """A square of `side` meters against one side of the roof, inside the parapet, off the domes."""
    cx, cy, length, width, angle = frame(poly)
    u = np.array([math.cos(angle), math.sin(angle)])
    v = np.array([-u[1], u[0]])
    inset = gap + side / 2
    if which < 2:   # west then east
        reach = length / 2
        if reach < inset + 0.1:
            return None
        c = np.array([cx, cy]) - u * (reach - inset) * (1 if which == 0 else -1)
    else:           # south then north
        reach = width / 2
        if reach < inset + 0.1:
            return None
        c = np.array([cx, cy]) - v * (reach - inset) * (1 if which == 2 else -1)
    stair = rectangle(c[0], c[1], side, side, angle)
    if not layout.inner.contains(stair):
        return None
    for x, y, radius, _mat in b.domes:
        if stair.distance(Point(x, y)) < radius + gap:
            return None
    if any(stair.distance(o) < gap for o in layout.blocked):
        return None
    return stair


def _stair_door(layout: RoofLayout, stair, reach: float, free=None):
    """Center and outward yaw of the door on the side of the stair room that opens on the roof."""
    free = layout.inner.difference(stair) if free is None else free
    if free.is_empty:
        return None
    ring = np.asarray(stair.exterior.coords)[:-1]
    center = np.asarray(stair.centroid.coords)[0]
    for p0, p1 in zip(ring, np.roll(ring, -1, axis=0)):
        mid = (p0 + p1) / 2
        n = mid - center
        n = n / max(float(np.hypot(*n)), 1e-9)
        if all(free.contains(Point(*(mid + n * t))) for t in (0.4, reach)):
            return float(mid[0] + n[0] * 0.02), float(mid[1] + n[1] * 0.02), math.atan2(n[1], n[0])
    return None


def _menzah(b, poly, layout: RoofLayout, cfg: dict) -> None:
    """The menzah of an old-town house: a small room in a corner of the roof (else against the middle
    of a side), clear of the stair room and of everything else on the roof by `menzah_gap`, its door
    on the free roof and up to `menzah_windows` windows on its outer walls. No random draws."""
    ml, mw = (float(v) for v in cfg.get("menzah_size", [3.0, 2.4]))
    gap = float(cfg.get("menzah_gap", 0.6))
    edge = float(cfg.get("stair_gap", 0.25))
    cx, cy, length, width, angle = frame(poly)
    u = np.array([math.cos(angle), math.sin(angle)])
    v = np.array([-u[1], u[0]])
    others = [r for r in (layout.stair, *layout.blocked) if r is not None]
    others += [Point(x, y).buffer(r, 12) for x, y, r, _m in b.domes]
    for fx, fy in ((-1, -1), (1, -1), (1, 1), (-1, 1), (-1, 0), (1, 0), (0, -1), (0, 1)):
        c = (np.array([cx, cy]) + u * fx * (length / 2 - edge - ml / 2) + v * fy * (width / 2 - edge - mw / 2))
        room = rectangle(c[0], c[1], ml, mw, angle)
        if not layout.inner.contains(room) or any(room.distance(o) < gap for o in others):
            continue
        free = layout.inner.difference(room)
        for o in others:
            free = free.difference(o)
        door = _stair_door(layout, room, float(cfg.get("stair_door_reach", 0.8)), free)
        if door is None:
            continue
        layout.menzah = room
        layout.menzah_height = float(cfg.get("menzah_height", 2.3))
        layout.menzah_door = door
        layout.menzah_windows = _menzah_windows(b, room, door, int(cfg.get("menzah_windows", 2)))
        return


def _menzah_windows(b, room, door: tuple, count: int) -> list:
    """Window centers (x, y, outward yaw) on the menzah's walls facing out of the house, longest first,
    never on the door's wall."""
    ring = np.asarray(room.exterior.coords)[:-1]
    center = np.asarray(room.centroid.coords)[0]
    away = center - np.asarray(b.footprint.centroid.coords)[0]
    walls = []
    for p0, p1 in zip(ring, np.roll(ring, -1, axis=0)):
        mid = (p0 + p1) / 2
        n = mid - center
        n = n / max(float(np.hypot(*n)), 1e-9)
        if math.cos(math.atan2(n[1], n[0]) - door[2]) > 0.99 or float(np.dot(n, away)) <= 0.0:
            continue
        walls.append((-float(np.hypot(*(p1 - p0))), float(mid[0] + n[0] * 0.02), float(mid[1] + n[1] * 0.02),
                      math.atan2(n[1], n[0])))
    return [(x, y, yaw) for _, x, y, yaw in sorted(walls)[:count]]
