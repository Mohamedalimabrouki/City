"""The corniche's seafront promenade as drawn (prompt 36, city/corniche.py): paving, curb, sea wall, steps.

A seafront walk is drawn by the tile holding its centroid, like every walk (mesh/tile.walk_meshes): its top
draped on `Ground.walk_top` (level across the promenade, curb height above the ribbon at its curb), on the same
outline points, so people standing on it (city/crowd.py) stand on these very triangles. Its outline gets:
- along the street and across an end the next piece does not continue: a curb face down to the ground;
- along the sea, and across an open end: the sea wall, a whitewashed coping band `coping` m deep over a face of
  dressed stone (the harbor's `quay_wall`) reaching `foot` m under the sand or the seabed.
A flight of steps goes down to the sand at each of its stretch's stairs (drawn by the tile holding the stair's
point): risers of at most `stair[1]` m, treads `stair[2]` m deep, paved like the promenade, sides in stone.
"""
from __future__ import annotations

import math

import numpy as np
import shapely
from shapely.geometry.polygon import orient

from .builder import MeshBuilder, add_draped_cap, add_skirt


def front_meshes(mb: MeshBuilder, tc, plan, tile, along=None) -> None:
    """The seafront walks and steps owned by this tile."""
    cfg = tc.world.style.get("corniche", {})
    if not cfg or not getattr(plan, "fronts", None):
        return
    x0, y0, x1, y1 = tile.bounds
    step = float(tc.world.style.get("streets", {}).get("walk_step", 15.0))
    fronts = [w for w in plan.walks if w.kind == "seafront"]
    tree = shapely.STRtree([w.polygon for w in fronts])
    for i, walk in enumerate(fronts):
        c = walk.polygon.centroid
        if x0 <= c.x < x1 and y0 <= c.y < y1:
            _walk(mb, tc, plan, walk, i, tree, step, cfg, along)
    for f in plan.fronts:
        for x, y, ux, uy in f.stairs:
            if x0 <= x < x1 and y0 <= y < y1:
                _stairs(mb, tc, np.array([x, y]), np.array([ux, uy]), cfg)


def _walk(mb: MeshBuilder, tc, plan, walk, index: int, tree, step: float, cfg: dict, along) -> None:
    st = plan.streets[walk.street]
    poly = shapely.segmentize(orient(walk.polygon, sign=1.0), tc.ground.walk_step(walk.polygon, step))
    add_draped_cap(mb, poly, tc.ground.walk_top, "promenade", along)
    pts = np.asarray(poly.exterior.coords)[:-1]
    top = tc.ground.walk_top(pts[:, 0], pts[:, 1])
    bottom = np.asarray(tc.height(pts[:, 0], pts[:, 1]), dtype=np.float64)
    nxt = np.roll(pts, -1, axis=0)
    curb = st.width / 2.0 - float(cfg["curb"])
    off = shapely.distance(st.line, shapely.points(pts))
    sea_pt = off > curb + 0.5 * float(cfg["min_width"])
    sea = sea_pt & np.roll(sea_pt, -1)                       # both ends on the sea edge
    mids = shapely.points((pts + nxt) / 2.0)
    inp, hit = tree.query(mids, predicate="dwithin", distance=0.01)
    shared = np.zeros(len(pts), dtype=bool)
    shared[inp[hit != index]] = True                          # the next piece of the stretch carries on here
    end = ~sea & (sea_pt | np.roll(sea_pt, -1)) & ~shared     # an open end: from the curb out to the sea edge
    add_skirt(mb, pts, top, bottom, "curb", only=~sea & ~end & ~shared)
    wall = sea | end
    band = top - float(cfg["coping"])
    add_skirt(mb, pts, top, band, "lime_white", only=wall)
    add_skirt(mb, pts, band, bottom - float(cfg["foot"]), "quay_wall", only=wall)


def _stairs(mb: MeshBuilder, tc, q: np.ndarray, u: np.ndarray, cfg: dict) -> None:
    """A flight from the promenade's top at sea edge point q down to the sand, out along u."""
    width, rise_max, tread = (float(v) for v in cfg["stair"])
    foot = float(cfg["foot"])
    v = np.array([-u[1], u[0]])
    inside = q - u * 0.05
    top = float(tc.ground.walk_top(inside[:1], inside[1:])[0])
    n = 2
    for _ in range(3):                                        # the sand where the flight lands sets its height
        land = q + u * (n - 0.5) * tread
        sand = float(tc.height(land[0], land[1]))
        n = max(2, int(math.ceil((top - sand) / rise_max - 1e-6)))
    rise = (top - sand) / n
    if rise <= 0.02:
        return
    for k in range(1, n):                                     # step k at top - k rise; the sand is the last
        a, b = (k - 1) * tread, k * tread
        z = top - k * rise
        low = min(float(tc.height(*(q + u * b))), sand) - foot
        c = [q + u * a - v * width / 2, q + u * b - v * width / 2, q + u * b + v * width / 2, q + u * a + v * width / 2]
        _face(mb, [(*c[0], z), (*c[1], z), (*c[2], z), (*c[3], z)], (0.0, 0.0, 1.0), "promenade")
        _face(mb, [(*c[1], z), (*c[1], low), (*c[2], low), (*c[2], z)], (u[0], u[1], 0.0), "quay_wall")
        _face(mb, [(*c[0], z), (*c[0], low), (*c[1], low), (*c[1], z)], (-v[0], -v[1], 0.0), "quay_wall")
        _face(mb, [(*c[3], z), (*c[2], z), (*c[2], low), (*c[3], low)], (v[0], v[1], 0.0), "quay_wall")


def _face(mb: MeshBuilder, quad: list, normal: tuple, mat: str) -> None:
    """One flat quad, its corners counter-clockwise seen from `normal`'s side; UVs in meters on the face."""
    p = np.asarray(quad, dtype=np.float64)
    n = np.asarray(normal, dtype=np.float64)
    e = p[1] - p[0]
    tris = np.array([[0, 1, 2], [0, 2, 3]])
    if np.dot(np.cross(p[1] - p[0], p[2] - p[0]), n) < 0:
        tris = tris[:, ::-1]
    s = e / max(float(np.linalg.norm(e)), 1e-9)
    t = np.cross(n, s)
    uv = np.stack([(p - p[0]) @ s, -((p - p[0]) @ t)], axis=1)
    mb.add(mat, p, np.tile(n, (4, 1)), uv, tris)
