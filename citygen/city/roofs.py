"""Roof life: the parapet around a flat roof, and the stair room standing on some of them.

`roof_layout` is the one place that decides both. The tile mesher draws what it returns
(the parapet band and the stair room); the Dresser keeps its tanks, dishes, laundry and
pots on the free roof it leaves, so nothing ever stands in the stair room or outside the
parapet. Each building has its own random stream (`roof_stream`), shared by both.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from shapely.geometry import Point

from ..mesh.builder import rectangle
from ..rng import stream
from .geo import frame

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

    @property
    def free(self):
        """The roof a prop may stand on: inside the parapet and outside the stair room."""
        if self.inner is None:
            return None
        return self.inner if self.stair is None else self.inner.difference(self.stair)


def roof_stream(seed: int, city_id: int, k: int):
    """The random stream of one building's roof (same for the mesh and the dressing)."""
    return stream(seed, "roof", city_id, k)


def roof_layout(b, kind: str, rng, cfg: dict) -> RoofLayout:
    """Parapet and stair room of building `b` in a district of `kind` (from the `[roofs]` style)."""
    if b.roof_shape != "flat":
        return RoofLayout()
    height = float(cfg.get("parapet_height", {}).get(kind, cfg.get("parapet_fallback", 0.7)))
    thick = float(cfg.get("parapet_thickness", 0.2))
    inner = b.footprint.buffer(-thick, join_style="mitre")
    if inner.is_empty or inner.area <= 0.0:
        return RoofLayout()
    band = b.footprint.difference(inner)
    if band.is_empty:
        return RoofLayout()
    layout = RoofLayout(height, band, inner)
    chance = float(cfg.get("stair_room", {}).get(kind, 0.0))
    if chance <= 0.0 or b.kind not in STAIR_KINDS or b.top:
        return layout
    if rng.random() >= chance:
        return layout
    side = float(cfg.get("stair_side", 2.5))
    gap = float(cfg.get("stair_gap", 0.25))
    started = int(rng.integers(4))
    for turn in range(4):
        stair = _stair_candidate(b, layout, side, gap, (started + turn) % 4)
        if stair is None:
            continue
        door = _stair_door(layout, stair, float(cfg.get("stair_door_reach", 0.8)))
        if door is None:   # a room with no way out is not a stair room
            continue
        layout.stair = stair
        layout.stair_height = float(cfg.get("stair_height", 2.4))
        layout.door = door
        layout.door_width = float(cfg.get("stair_door_width", 0.9))
        layout.door_height = float(cfg.get("stair_door_height", 1.95))
        return layout
    return layout


def _stair_candidate(b, layout: RoofLayout, side: float, gap: float, which: int):
    """A square of `side` meters against one side of the roof, inside the parapet, off the domes."""
    cx, cy, length, width, angle = frame(b.footprint)
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
    return stair


def _stair_door(layout: RoofLayout, stair, reach: float):
    """Center and outward yaw of the door on the side of the stair room that opens on the roof."""
    free = layout.inner.difference(stair)
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
