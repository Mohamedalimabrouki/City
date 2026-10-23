"""Geometry for every home's openings (prompt 20.1): walls, open ground, piece boxes and paths.

Pure functions of the plan's geometry: no random draws here. `city/dressing.py` decides what goes
where; these helpers say which walls face open ground, whether a piece fits beside the others
already on a wall, and how a paved path reaches the street.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import shapely
from shapely.geometry.polygon import orient


@dataclass
class Walls:
    """The exterior walls of one footprint, counter-clockwise, as arrays (one row per wall)."""
    a: np.ndarray        # (m, 2) start corners
    b: np.ndarray        # (m, 2) end corners
    n: np.ndarray        # (m, 2) outward unit normals
    length: np.ndarray   # (m,)
    street: np.ndarray   # (m,) street index 1.6 m in front of the midpoint, or -1
    open: np.ndarray     # (m,) bool: no other building within `clear` m in front

    @property
    def u(self) -> np.ndarray:
        return (self.b - self.a) / np.maximum(self.length, 1e-9)[:, None]


@dataclass
class DoorSpot:
    """A dwelling's door: where it is on the wall and how it is reached.

    `reach` is "street" when the door opens onto street `street` (its surface or sidewalk lies
    just in front), "open" when it opens onto open ground (then `street` is the nearest street and
    `path`, when there is one, the paved path to it), and "enclosed" when neighbours stand within
    a few meters in front of every wall (prompt 20.2 cuts an impasse to it; `street` is the nearest).
    """
    x: float
    y: float
    nx: float            # outward unit normal of the wall
    ny: float
    z: float             # threshold: the drawn surface (street, walk, path or ground) 0.5 m in front
    street: int
    reach: str           # street | open | enclosed
    kind: str            # front (the street door, as before 20.1) | house (beside a shop or cafe)
                         # | door (on another wall) | stair (an apartment block's stair door)
    wall: int            # index of the wall in the counter-clockwise exterior ring
    path: np.ndarray | None = None   # (N, 2) points of the paved path, from the door outward
    piece: str = ""      # the kit piece drawn there (its bounds give the opening's size)

    @property
    def point(self) -> np.ndarray:
        return np.array([self.x, self.y])

    @property
    def normal(self) -> np.ndarray:
        return np.array([self.nx, self.ny])


def wall_arrays(footprint) -> tuple:
    """(a, b, n, length) of the counter-clockwise exterior ring, exactly as the dresser reads walls."""
    ring = np.asarray(orient(footprint, 1.0).exterior.coords)[:-1]
    p, q = ring, np.roll(ring, -1, axis=0)
    d = q - p
    length = np.hypot(d[:, 0], d[:, 1])
    n = np.stack([d[:, 1], -d[:, 0]], 1) / np.maximum(length, 1e-9)[:, None]
    return p, q, n, length


def open_walls(fp_tree, k: int, a, b, n, length, clear: float, inset: float = 0.3) -> np.ndarray:
    """True for walls with no other building (ramparts and towers included) within `clear` m in front.

    One probe rectangle per wall, shortened by `inset` at both ends so a neighbour beside the corner
    does not count, all queried against the footprint tree at once.
    """
    ok = length > 2 * inset + 0.1
    out = np.zeros(len(a), dtype=bool)
    if fp_tree is None or not ok.any():
        return out
    u = (b - a) / np.maximum(length, 1e-9)[:, None]
    a0, b0 = a + u * inset, b - u * inset
    a1, b1 = a0 + n * 0.02, b0 + n * 0.02                    # just off the wall itself
    rings = np.stack([a1, b1, b0 + n * clear, a0 + n * clear, a1], axis=1)[ok]
    probes = shapely.polygons(rings)
    idx = np.nonzero(ok)[0]
    blocked = np.zeros(len(probes), dtype=bool)
    probe, hit = fp_tree.query(probes, predicate="intersects")
    other = hit != k
    blocked[probe[other]] = True
    out[idx] = ~blocked
    return out


def piece_boxes(kit, placements, base: float) -> tuple:
    """Footprints (shapely polygons) and absolute height ranges of placed pieces, built in one go.

    Pieces standing on the ground count from `base` (the threshold of the door or shop they stand
    by): close enough to tell whether a new door or window overlaps them.
    """
    if not placements:
        return np.array([], dtype=object), np.zeros(0), np.zeros(0)
    xy = np.array([(p.x, p.y) for p in placements], dtype=np.float64)
    z = np.array([p.z for p in placements], dtype=np.float64)
    z[np.array([p.on_ground for p in placements])] += base
    yaw = np.array([p.yaw for p in placements])
    sc = np.array([(p.scale * getattr(p, "stretch", 1.0), p.scale, p.scale) for p in placements])   # x along the wall
    lo = np.array([kit.pieces[p.piece].bounds[0] for p in placements]) * sc
    hi = np.array([kit.pieces[p.piece].bounds[1] for p in placements]) * sc
    lx = np.stack([lo[:, 0], hi[:, 0], hi[:, 0], lo[:, 0]], 1)         # along the wall
    ly = np.stack([-hi[:, 2], -hi[:, 2], -lo[:, 2], -lo[:, 2]], 1)     # out of the wall
    c, s = np.cos(yaw)[:, None], np.sin(yaw)[:, None]
    corners = np.stack([xy[:, :1] + lx * c - ly * s, xy[:, 1:] + lx * s + ly * c], 2)
    return shapely.polygons(corners), z + lo[:, 1], z + hi[:, 1]


def joined(*boxes) -> tuple:
    """Several piece_boxes results as one."""
    return tuple(np.concatenate([b[k] for b in boxes]) for k in range(3))


def piece_box(piece, x: float, y: float, yaw: float, z: float, scale: float = 1.0,
              grow: float = 0.0, depth: float = 0.0) -> tuple:
    """(footprint, z0, z1) of one piece placed at (x, y, z) facing yaw.

    `grow` widens it along the wall on both sides; `depth` makes it reach at least that far out
    (the free ground in front of a door).
    """
    lo, hi = piece.bounds                                  # glTF axes: x along the wall, y up, front -z
    x0, x1 = lo[0] * scale - grow, hi[0] * scale + grow
    y0, y1 = -hi[2] * scale, max(-lo[2] * scale, depth)    # out of the wall, toward the front
    c, s = math.cos(yaw), math.sin(yaw)
    corners = np.array([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    wx = x + corners[:, 0] * c - corners[:, 1] * s
    wy = y + corners[:, 0] * s + corners[:, 1] * c
    return shapely.polygons(np.stack([wx, wy], 1)), z + lo[1] * scale, z + hi[1] * scale


def fits(piece, x: float, y: float, yaw: float, z: float, boxes: tuple, grow: float = 0.0, depth: float = 0.0,
         zpad: float = 0.1) -> bool:
    """True when the piece placed there overlaps none of `boxes` (from piece_boxes) in plan and height.

    Heights are compared first, so a window high above every other piece costs no polygon.
    """
    polys, z0, z1 = boxes
    if not len(polys):
        return True
    lo, hi = z + piece.bounds[0][1], z + piece.bounds[1][1]
    near = (z0 < hi + zpad) & (z1 > lo - zpad)
    if not near.any():
        return True
    reach = float(np.abs(np.concatenate([piece.bounds[0], piece.bounds[1]])[[0, 2, 3, 5]]).max()) + grow + depth
    box = shapely.bounds(polys[near])
    near_xy = (box[:, 0] < x + reach) & (box[:, 2] > x - reach) & (box[:, 1] < y + reach) & (box[:, 3] > y - reach)
    if not near_xy.any():
        return True
    near = np.nonzero(near)[0][near_xy]
    poly = piece_box(piece, x, y, yaw, z, grow=grow, depth=depth)[0]
    return not shapely.intersects(poly, polys[near]).any()


def path_to_street(start, n, target_tree, fp_tree, width: float, reach: float, step: float, grid: float,
                   tries: int = 8):
    """A straight paved path from a door at `start` (on the wall, facing `n`) to a street edge or
    sidewalk, crossing no building: straight out along the normal when that meets one within
    `reach`, else a short stub out of the door and then straight to the nearest point of the
    nearest street or sidewalk that can be reached so. None when every way crosses a building.

    The points run from the door outward; one point lies exactly 0.5 m in front of the door, where
    the threshold reads the path's height, and one wherever the path crosses an edge of the terrain
    mesh (cells of `grid` m), so the path follows the drawn ground exactly.
    """
    start, n = np.asarray(start, dtype=np.float64), np.asarray(n, dtype=np.float64)
    for pts in _routes(start, n, target_tree, reach, tries):
        line = _segmentized(np.array(pts), step, grid)
        band = shapely.buffer(shapely.linestrings(line[1:]), width / 2, cap_style="flat")
        if len(fp_tree.query(band, predicate="intersects")) == 0:
            return line
    return None


def _routes(start, n, target_tree, reach: float, tries: int):
    """Candidate paths, best first: straight out of the door, then a 0.8 m stub and a straight run
    to the nearest point of each street or sidewalk within reach, nearest first."""
    ray = shapely.linestrings([start + n * 0.05, start + n * reach])
    hits = target_tree.query(ray, predicate="intersects")
    if len(hits):
        cuts = shapely.intersection(ray, target_tree.geometries[hits])
        d = [shapely.line_locate_point(ray, shapely.points(shapely.get_coordinates(c))).min()
             for c in cuts if not c.is_empty]
        if d and 0.05 + min(d) >= 0.6:
            yield [start, start + n * (0.05 + float(min(d)))]
    knee = shapely.points(start + n * 0.8)
    near = target_tree.query(shapely.buffer(knee, reach))
    if not len(near):
        return
    geoms = target_tree.geometries[near]
    dist = shapely.distance(knee, geoms)
    for g in geoms[np.argsort(dist, kind="stable")[:tries]]:
        if shapely.contains(g, knee):
            return
        q = shapely.get_coordinates(shapely.shortest_line(knee, g))[1]
        if np.dot(q - start, n) > 0.8:                     # ahead of the door, never back along the wall
            yield [start, start + n * 0.8, q]


def _segmentized(pts: np.ndarray, step: float, grid: float) -> np.ndarray:
    """The polyline with a point 0.5 m in front of the door, its corners, points every `step` m, and
    a point where it crosses a terrain mesh edge (grid lines and the cells' diagonals)."""
    line = shapely.linestrings(pts)
    total = float(shapely.length(line))
    seg = np.hypot(*np.diff(pts, axis=0).T)
    start = np.concatenate([[0.0], np.cumsum(seg)])
    d = [[0.0, min(0.5, total)], np.arange(0.5 + step, total, step), start[1:-1], [total]]
    for p, q, s0, length in zip(pts[:-1], pts[1:], start[:-1], seg):
        for f in (lambda v: v[0], lambda v: v[1], lambda v: v[0] - v[1]):   # x, y and diagonal edges
            a, b = f(p) / grid, f(q) / grid
            if abs(b - a) > 1e-9:
                k = np.arange(np.ceil(min(a, b)), np.floor(max(a, b)) + 1)
                d.append(s0 + (k - a) / (b - a) * length)
    d = np.unique(np.round(np.clip(np.concatenate(d), 0.0, total), 6))
    return shapely.get_coordinates(shapely.line_interpolate_point(line, d))
