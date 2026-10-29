"""The facade bridge (SPEC 6c): building k exactly as its tile dresses it, and the holes its pieces stand in.

`Outside` replays `mesh.tile.build_tile` for one building: the same kit, the same `high`, and the same
order (`keep_roof`, `building`, `ground_heights`, `under_roofs`, `keep_off` with the city's zones where the
owning tile meets them). It draws nothing new: every stream it touches is one the tile already uses.
"""
from __future__ import annotations

import math

import numpy as np
import shapely
from shapely.geometry import box
from shapely.geometry.polygon import orient

from ..city.dressing import building_highs, ground_heights
from ..city.massing import massed, masses
from ..city.moorings import land_zone
from ..city.roofs import roof_layouts, roof_stream
from ..mesh.port import keep_zone
from ..mesh.station import keep_off, rail_zone
from .model import Opening

FACADE = ("door", "window", "shop", "balcony")   # piece categories that stand in a hole of the wall
GLASS = ("glass_dark", "glass_lit", "shop_dark")  # hole materials: the glass, a shop's dark inside
TURN = math.radians(1.0)    # a wall whose outward normal lies within this of the piece front carries it
ON_WALL = 0.05              # meters: ... and passes this near the hole's center
BESIDE = 0.1                # meters: a balcony this near a window stands in front of it (no hole of its own)


class Outside:
    """Building k of `plan` as its tile dresses it: `placements` are the tile's own pieces for k (same
    objects, same order, absolute z), `doors` its `DoorSpot`s (main door first), `openings` the facade
    `Opening`s their pieces make (rooms not assigned yet)."""

    def __init__(self, ctx, plan, k: int):
        world = ctx.world
        self.ctx, self.plan, self.k = ctx, plan, k
        self.b = b = plan.buildings[k]
        self.kit = ctx.kit
        self.district = plan.districts[b.district].kind
        dresser = ctx.dresser(plan)
        self.high = float(building_highs(ctx.ground, [b])[0])
        self.fh = b.height / max(1, int(b.floors))
        size = int(world.cfg["tiles"]["size"])
        cx, cy = shapely.get_coordinates(shapely.centroid(b.footprint))[0]
        self.tile = (int(cx // size), int(cy // size))       # the tile owning k, as build_tile picks it
        self.roofs = roof_layouts(b, self.district, roof_stream(world.seed, plan.settlement.id, k),
                                  world.style.get("roofs", {}))
        dresser.keep_roof(k, self.roofs)
        placements = dresser.building(k, self.high)
        ground_heights(ctx.ground, placements)
        placements = dresser.under_roofs(placements)          # a souk vault drops upper windows
        self.placements = self._keep_off(placements, box(*(v * size for v in (*self.tile, self.tile[0] + 1,
                                                                             self.tile[1] + 1))))
        self.doors = dresser.entrances(k)
        self.warnings: list = []
        frame = float(world.style.get("interiors", {}).get("openings", {}).get("frame", 0.12))
        self.openings = facade_openings(self, frame)

    def _keep_off(self, placements: list, tile) -> list:
        """`build_tile`'s keep_off passes for this city, in its order and under its conditions."""
        plan, kit = self.plan, self.kit
        zone = rail_zone(plan)
        if zone is not None:
            placements = keep_off(placements, zone, kit)
        port = getattr(plan, "port", None)
        if port is not None and port.zone.intersects(tile):
            placements = keep_off(placements, keep_zone(port), kit)
        if getattr(plan, "props", None):
            ashore = land_zone(plan, self.ctx.world.style.get("port", {}).get("props"))
            if ashore is not None and ashore.intersects(tile):
                placements = keep_off(placements, ashore, kit)
        return placements


def hole(kit, name: str, frame: float) -> tuple:
    """(x0, x1, y0, y1) of the hole a facade piece stands in, in its own frame (x along the wall, y up):
    the kit manifest's glass; else its glass (a door: glass and leaf, `door_*`; a window: the leaf only
    when it has no glass, since open shutters lie beside the hole); else its bounds less the frame."""
    if name in kit.panes:
        x0, x1, y0, y1, _ = kit.panes[name]
        return x0, x1, y0, y1
    piece = kit.pieces[name]
    glass = [p["pos"] for m, p in sorted(piece.parts.items()) if m in GLASS]
    leaf = [p["pos"] for m, p in sorted(piece.parts.items()) if m.startswith("door_")]
    use = glass + leaf if piece.category == "door" else (glass or leaf)
    if use:
        pos = np.concatenate(use)
        return float(pos[:, 0].min()), float(pos[:, 0].max()), float(pos[:, 1].min()), float(pos[:, 1].max())
    lo, hi = piece.bounds
    return float(lo[0]) + frame, float(hi[0]) - frame, float(lo[1]), float(hi[1]) - frame


def wall_segments(b) -> tuple:
    """(starts, ends, outward normals, lengths) of the footprint's exterior ring, then of every mass outline."""
    polys = [b.footprint] + ([m.polygon for m in masses(b)] if massed(b) else [])
    a, c = [], []
    for poly in polys:
        ring = np.asarray(orient(poly, 1.0).exterior.coords)[:, :2]
        a.append(ring[:-1])
        c.append(ring[1:])
    a, c = np.concatenate(a), np.concatenate(c)
    d = c - a
    length = np.hypot(d[:, 0], d[:, 1])
    keep = length > 1e-6
    a, c, d, length = a[keep], c[keep], d[keep], length[keep]
    return a, c, np.stack([d[:, 1], -d[:, 0]], axis=1) / length[:, None], length


def on_wall(segs: tuple, x: float, y: float, yaw: float) -> int | None:
    """Index of the wall segment carrying a piece centered at (x, y) facing yaw; None when none does."""
    a, c, n, length = segs
    front = np.array([-math.sin(yaw), math.cos(yaw)])
    u = (c - a) / length[:, None]
    p = np.array([x, y])
    t = np.clip(((p - a) * u).sum(axis=1), 0.0, length)
    dist = np.hypot(*(a + u * t[:, None] - p).T)
    ok = (n @ front >= math.cos(TURN)) & (dist <= ON_WALL)
    if not ok.any():
        return None
    return int(np.flatnonzero(ok)[np.argmin(dist[ok])])


def facade_openings(o: Outside, frame: float) -> list:
    """One `Opening` per door, window, shop front and balcony of the facade (SPEC 6c bridge step 4)."""
    kit, ps = o.kit, o.placements
    category = [kit.pieces[p.piece].category if p.piece in kit.pieces else "" for p in ps]
    windows = np.array([(p.x, p.y, p.z) for p, cat in zip(ps, category) if cat == "window"]).reshape(-1, 3)
    segs = wall_segments(o.b)
    floors = max(1, int(o.b.floors))
    holes: dict = {}
    out = []
    for i, (p, cat) in enumerate(zip(ps, category)):
        if cat not in FACADE:
            continue
        if cat == "balcony" and len(windows) and np.linalg.norm(windows - (p.x, p.y, p.z), axis=1).min() < BESIDE:
            continue                                   # an iron balcony in front of its own window
        if p.piece not in holes:
            holes[p.piece] = hole(kit, p.piece, frame)
        x0, x1, y0, y1 = holes[p.piece]
        along = p.scale * p.stretch
        mid = (x0 + x1) / 2 * along
        x, y = p.x + math.cos(p.yaw) * mid, p.y + math.sin(p.yaw) * mid
        z0, z1 = p.z + y0 * p.scale, p.z + y1 * p.scale
        floor = min(max(int((z0 - o.high + 0.05) // o.fh), 0), floors - 1)
        lit = p.piece.endswith("_lit") or (i + 1 < len(ps) and ps[i + 1].piece == p.piece + "_pane_lit")
        w = on_wall(segs, x, y, p.yaw)
        wall, s = None, 0.0
        if w is None:
            o.warnings.append(f"the {p.piece} at ({x:.2f}, {y:.2f}) stands on no wall of the building")
        else:
            a, c = segs[0][w], segs[1][w]
            wall = ((float(a[0]), float(a[1])), (float(c[0]), float(c[1])))
            s = float(np.dot((x, y) - a, (c - a) / segs[3][w]))
        out.append(Opening(len(out), cat, x, y, p.yaw, (x1 - x0) * along, z0, z1, floor, (-1, -1), wall, s,
                           p.piece, lit))
    return out
