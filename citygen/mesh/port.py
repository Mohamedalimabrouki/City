"""The harbor's meshes (prompt 34): quay ground and walls, the breakwater, the lighthouse, bollards and fenders.

Plan geometry comes from city/port.py, heights from `Ground` (city/ground.py), which steps at the walls: the
terrain mesh leaves out the cells a wall crosses (`ground_masks`), and `split_cells` draws them in two parts,
each side of the wall at its own ground ("raised" or "sea"), so the drawn terrain is the ground on both sides
and a vertical wall closes the step. Cells on the apron are drawn as quay paving.

The quay walls are dressed stone with a dark wet band below `wet` m and a kerb along the quay edge. The
breakwater is a rough rubble mound (a loft of jittered profiles on the port's own stream, toes on the seabed)
with a concrete crest road, a crown wall on the sea side and a half-round head carrying the lighthouse: a
white tapered tower on a stone drum, red cap, top or bands (its scheme), an iron gallery and a glazed lantern
in `lantern_glow`, which glows at night through the viewer's glow rules.

Each wall segment and breakwater station belongs to the tile holding its midpoint; the head and the
lighthouse to the tile holding the tip; bollards and fenders are kit pieces placed on the quay edge.
"""
from __future__ import annotations

import math

import numpy as np
import shapely
from shapely.geometry import LineString, Point

from ..city.dressing import Placement
from ..city.geo import lines, polygons
from ..rng import stream
from .boats import boat_pieces
from .builder import MeshBuilder, add_quads, triangulate
from .cranes import crane_pieces
from .furniture import _lathe

UP = np.array([0.0, 0.0, 1.0])


# --- kit pieces ---------------------------------------------------------------------------------------

def bollard() -> MeshBuilder:
    """A cast-iron mooring bollard: a short post flaring to a mushroom head, origin at the foot."""
    mb = MeshBuilder()
    _lathe(mb, [(0.21, -0.05), (0.21, 0.04), (0.15, 0.09), (0.13, 0.40), (0.2, 0.47), (0.2, 0.54),
                (0.12, 0.6), (0.0, 0.61)], "bollard_iron", 10)
    return mb


def fender() -> MeshBuilder:
    """A rubber fender hung on the quay wall: origin at its top on the wall face, front (+y) toward the water."""
    mb = MeshBuilder()
    w, d, h = 0.22, 0.28, 1.7
    quads = np.array([[(-w, 0, -h), (w, 0, -h), (w, d, -h), (-w, d, -h)][::-1],          # bottom
                      [(-w, d, -h), (w, d, -h), (w, d, 0), (-w, d, 0)],                  # front
                      [(-w, 0, 0), (-w, d, 0), (w, d, 0), (w, 0, 0)],                    # top
                      [(w, 0, -h), (w, 0, 0), (w, d, 0), (w, d, -h)],                    # sides
                      [(-w, 0, -h), (-w, d, -h), (-w, d, 0), (-w, 0, 0)]], dtype=np.float64)
    center = np.array([0.0, d / 2, -h / 2])
    add_quads(mb, "fender_rubber", quads, quads.mean(axis=1) - center)
    return mb


def armour_rock(seed: int, name: str, size) -> MeshBuilder:
    """An armour stone of the breakwater: a jittered, squashed icosahedron, flat faced, centered on the origin,
    about `size` (length, width, height) meters, drawn on the piece's own stream."""
    rng = stream(seed, "piece", name)
    g = (1.0 + math.sqrt(5.0)) / 2.0
    v = np.array([(-1, g, 0), (1, g, 0), (-1, -g, 0), (1, -g, 0), (0, -1, g), (0, 1, g), (0, -1, -g), (0, 1, -g),
                  (g, 0, -1), (g, 0, 1), (-g, 0, -1), (-g, 0, 1)], dtype=np.float64)
    v /= np.linalg.norm(v, axis=1)[:, None]
    v *= rng.uniform(0.78, 1.15, size=(12, 1))
    v *= np.asarray(size, dtype=np.float64) / 2.0
    faces = np.array([(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2),
                      (10, 7, 6), (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5),
                      (2, 4, 11), (6, 2, 10), (8, 6, 7), (9, 8, 1)])
    tris = v[faces]
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    out = (n * tris.mean(axis=1)).sum(axis=1) < 0
    tris[out] = tris[out][:, ::-1]
    n[out] *= -1.0
    n /= np.linalg.norm(n, axis=1)[:, None]
    pos = tris.reshape(-1, 3)
    mb = MeshBuilder()
    mb.add("rubble", pos, np.repeat(n, 3, axis=0), np.stack([pos[:, 0] + pos[:, 1], -pos[:, 2]], axis=1),
           np.arange(len(pos)).reshape(-1, 3))
    return mb


def port_pieces(seed: int, cfg: dict | None) -> dict:
    """{name: (MeshBuilder, category, anchor)} of the harbor's kit pieces: bollard, fender, the breakwater's
    armour stones (each on its own stream), the boats, cranes, rails and cargo of `[port.props]`."""
    out = {"bollard": (bollard(), "bollard", "ground"), "fender": (fender(), "fender", "wall")}
    size = (cfg or {}).get("armour", {}).get("size", [3.4, 2.7, 1.9])
    for k in range((cfg or {}).get("armour", {}).get("variants", 3)):
        name = f"armour_rock_{k}"
        out[name] = (armour_rock(seed, name, size), "rock", "ground")
    props = (cfg or {}).get("props")
    out.update(boat_pieces(seed, props))                  # boats, cranes and cargo (prompt 35)
    out.update(crane_pieces(seed, props))
    return out


# --- ground ---------------------------------------------------------------------------------------------

def ground_masks(tc, x0: np.ndarray, y0: np.ndarray, s: float) -> tuple:
    """(apron, split) over terrain cells with lower-left corners x0, y0: cells whose center lies on a quay apron
    (drawn as paving), cells a wall crosses (left to `split_cells`)."""
    apron = np.zeros(x0.shape, dtype=bool)
    split = np.zeros(x0.shape, dtype=bool)
    for port in tc.ports:
        bx0, by0, bx1, by1 = port.zone.bounds
        near = (x0 + s >= bx0) & (x0 <= bx1) & (y0 + s >= by0) & (y0 <= by1)
        if not near.any():
            continue
        apron[near] |= shapely.contains_xy(port.apron, x0[near] + s / 2, y0[near] + s / 2)
        cells = shapely.box(x0[near], y0[near], x0[near] + s, y0[near] + s)
        split[near] |= shapely.intersects(port.walls, cells)
    return apron, split


def split_cells(mb: MeshBuilder, tc, x0: np.ndarray, y0: np.ndarray, names: np.ndarray, s: float) -> None:
    """The cells a wall crosses: both triangles of each (split along the south-west to north-east diagonal, as
    the terrain mesh) cut by the raised side, each part on its own side's ground (paving on the apron, the
    cell's own material elsewhere on the raised side, the seabed's `beach` on the sea side)."""
    if not len(x0):
        return
    tris = np.concatenate([np.stack([np.stack([x0, y0], 1), np.stack([x0 + s, y0], 1), np.stack([x0 + s, y0 + s], 1)], 1),
                           np.stack([np.stack([x0, y0], 1), np.stack([x0 + s, y0 + s], 1), np.stack([x0, y0 + s], 1)], 1)])
    mats = np.concatenate([names, names])
    polys = shapely.polygons(np.concatenate([tris, tris[:, :1]], axis=1))
    out: dict = {}
    cells = np.concatenate([np.arange(len(x0)), np.arange(len(x0))])
    boxes = shapely.box(x0, y0, x0 + s, y0 + s)
    for port in tc.ports:                            # each cell by the harbor whose wall crosses it
        mine = shapely.intersects(port.walls, boxes)[cells]
        if not mine.any():
            continue
        ks = np.nonzero(mine)[0]
        for side, pieces in (("raised", shapely.intersection(polys[ks], port.raised)),
                             ("sea", shapely.difference(polys[ks], port.raised))):
            for k, geom in zip(ks, pieces):
                for poly in polygons(geom):
                    if poly.area < 1e-4:
                        continue
                    t = triangulate(poly)
                    if not len(t):
                        continue
                    if side == "sea":
                        mat = "beach"
                    else:
                        c = poly.representative_point()
                        mat = "quay" if port.apron.contains(c) else str(mats[k])
                    out.setdefault((mat, side), []).append(t)
    for (mat, side), ts in out.items():
        t = np.concatenate(ts)
        pts, inv = np.unique(np.round(t.reshape(-1, 2), 6), axis=0, return_inverse=True)
        z = np.asarray(tc.ground.height(pts[:, 0], pts[:, 1]), dtype=np.float64).reshape(-1)
        wall = np.zeros(len(pts), dtype=bool)
        for port in tc.ports:                        # on a wall: that side's ground; elsewhere the ground itself
            wall |= shapely.distance(port.walls, shapely.points(pts)) < 1e-6
        if wall.any():
            z[wall] = tc.ground.side_height(pts[wall, 0], pts[wall, 1], side)
        pos = np.column_stack([pts, z])
        idx = np.asarray(inv).reshape(-1, 3)
        nrm = _vertex_normals(pos, idx)
        mb.add(mat, pos, nrm, np.stack([pts[:, 0], -pts[:, 1]], axis=1), idx, tc.tint(pts[:, 0], pts[:, 1]))


def _vertex_normals(pos: np.ndarray, idx: np.ndarray) -> np.ndarray:
    """Area-weighted vertex normals of triangles that face up (flipped in place when one does not)."""
    a, b, c = pos[idx[:, 0]], pos[idx[:, 1]], pos[idx[:, 2]]
    n = np.cross(b - a, c - a)
    down = n[:, 2] < 0
    idx[down] = idx[down][:, ::-1]
    n[down] *= -1.0
    acc = np.zeros_like(pos)
    for j in range(3):
        np.add.at(acc, idx[:, j], n)
    length = np.linalg.norm(acc, axis=1)
    return np.where(length[:, None] > 1e-12, acc / np.maximum(length, 1e-12)[:, None], UP)


# --- quay walls -----------------------------------------------------------------------------------------

def wall_meshes(mb: MeshBuilder, tc, port, tile) -> None:
    """The walls where the raised side meets the sea, owned by this tile: dressed stone above `wet` m, the dark
    wet band below, down past the seabed; along the quays a kerb on top."""
    cfg = tc.port_cfg
    x0, y0, x1, y1 = tile.bounds
    step, bury, wet = float(cfg["wall_step"]), float(cfg["bury"]), float(cfg["wet"])
    kw, kh = (float(v) for v in cfg["kerb"])
    for line in lines(port.walls):
        if not line.intersects(tile.buffer(step)):
            continue
        pts = np.asarray(shapely.segmentize(line, step).coords)[:, :2]
        d = (pts[1] - pts[0]) / max(float(np.linalg.norm(pts[1] - pts[0])), 1e-9)
        m0 = (pts[0] + pts[1]) / 2
        if port.raised.contains(Point(m0[0] + 0.3 * d[1], m0[1] - 0.3 * d[0])):   # the sea on the right (walls face it)
            pts = pts[::-1]
        mid = (pts[:-1] + pts[1:]) / 2
        own = (mid[:, 0] >= x0) & (mid[:, 0] < x1) & (mid[:, 1] >= y0) & (mid[:, 1] < y1)
        if not own.any():
            continue
        top = tc.ground.side_height(pts[:, 0], pts[:, 1], "raised")
        bottom = tc.ground.side_height(pts[:, 0], pts[:, 1], "sea") - bury
        quay = shapely.distance(port.core, shapely.points(pts)) < 1e-3
        quay &= np.abs(top - port.level) < 1e-6
        top = np.where(quay, top + kh, top)
        for a, b in _runs(own, _corners(pts)):
            sl = slice(a, b + 1)
            sea = _normals(pts[sl])                      # toward the sea, per point
            dry_bottom = np.maximum(np.minimum(top[sl], wet), bottom[sl])
            if (top[sl] - dry_bottom).max() > 1e-3:
                _wall(mb, "quay_wall", pts[sl], top[sl], dry_bottom, sea)
            _wall(mb, "quay_wet", pts[sl], np.minimum(top[sl], wet), bottom[sl], sea)
            for qa, qb in _runs(quay[sl][:-1] & quay[sl][1:]):
                k = slice(a + qa, a + qb + 1)
                _kerb(mb, pts[k], -sea[qa:qb + 1], port.level, kw, kh)


def _corners(pts: np.ndarray, turn: float = 30.0) -> np.ndarray:
    """Indices of the inner points where a polyline turns more than `turn` degrees (a wall's corner)."""
    d = np.diff(pts, axis=0)
    a = np.arctan2(d[:, 1], d[:, 0])
    bend = np.abs((np.diff(a) + math.pi) % (2 * math.pi) - math.pi)
    return np.nonzero(bend > math.radians(turn))[0] + 1


def _normals(pts: np.ndarray) -> np.ndarray:
    """Unit right-hand normals of a polyline at its points (the mean of the segments meeting there)."""
    d = np.gradient(pts, axis=0)
    d /= np.maximum(np.linalg.norm(d, axis=1), 1e-9)[:, None]
    return np.stack([d[:, 1], -d[:, 0]], axis=1)


def _wall(mb: MeshBuilder, mat: str, pts: np.ndarray, top: np.ndarray, bottom: np.ndarray, out: np.ndarray) -> None:
    """A vertical face along `pts` from `top` down to `bottom`, facing `out`: shared vertices, u along it."""
    grid = np.stack([np.column_stack([pts, top]), np.column_stack([pts, bottom])], axis=1)
    _grid(mb, mat, grid, np.column_stack([out, np.zeros(len(out))]))


def _kerb(mb: MeshBuilder, pts: np.ndarray, inland: np.ndarray, level: float, width: float, height: float) -> None:
    """The kerb along the quay edge: its top from the wall face back `width` m, and its inner face."""
    n = len(pts)
    inner = pts + inland * width
    top = np.stack([np.column_stack([pts, np.full(n, level + height)]),
                    np.column_stack([inner, np.full(n, level + height)])], axis=1)
    _grid(mb, "curb", top)
    _wall(mb, "curb", inner, np.full(n, level + height), np.full(n, level), inland)


def quay_placements(tc, port, tile) -> list:
    """Bollards along every quay edge, `bollard_inset` m behind it, and rubber fenders on the wall between them;
    none on the breakwater's root."""
    cfg = tc.port_cfg
    x0, y0, x1, y1 = tile.bounds
    crest_z, crest_w = (float(v) for v in cfg["crest"])
    root_clear = crest_w / 2 + float(cfg["slope"]) * (crest_z + float(cfg["depth"])) + 2.0
    roots = [bw.line for bw in port.breakwaters]
    out = []
    for q in port.quays:
        line = q.line
        if not line.intersects(tile.buffer(5.0)):
            continue
        for name, step, offset in (("bollard", float(cfg["bollard_step"]), 0.5), ("fender", float(cfg["fender_step"]), 1.0)):
            n = int(line.length // step)
            for k in range(n):
                s = (line.length - (n - 1) * step) / 2 + k * step + (offset - 0.5) * step
                if not 1.0 < s < line.length - 1.0:
                    continue
                p = line.interpolate(s)
                a, b = line.interpolate(max(s - 0.5, 0.0)), line.interpolate(min(s + 0.5, line.length))
                t = np.array([b.x - a.x, b.y - a.y])
                t /= np.linalg.norm(t)
                if any(r.distance(p) < root_clear for r in roots):
                    continue
                if name == "bollard":
                    x, y = p.x - t[1] * float(cfg["bollard_inset"]), p.y + t[0] * float(cfg["bollard_inset"])
                    z, yaw = port.level, math.atan2(t[1], t[0])
                else:
                    x, y, z, yaw = p.x, p.y, port.level - 0.15, math.atan2(-t[1], -t[0])
                if x0 <= x < x1 and y0 <= y < y1:
                    out.append(Placement(name, float(x), float(y), float(z), float(yaw), on_ground=False))
    return out


def armour_placements(tc, port, plan, tile) -> list:
    """The armour stones in rows along each side of every breakwater and round its head, at `[port.armour] z`
    m on the slope, every `step` m; variant, turn, tilt and size from the breakwater's own stream, a fixed
    number of draws per stone, so every tile agrees. None on the quay the breakwater starts from."""
    cfg = tc.port_cfg
    arm = cfg["armour"]
    x0, y0, x1, y1 = tile.bounds
    crest_z, crest_w = (float(v) for v in cfg["crest"])
    step, variants = float(arm["step"]), int(arm["variants"])
    lo, hi = (float(v) for v in arm["scale"])
    out = []
    for n, bw in enumerate(port.breakwaters):
        line = bw.line
        e = np.asarray(line.coords)[-2:]
        tt = (e[1] - e[0]) / np.linalg.norm(e[1] - e[0])
        sea = np.array([-tt[1], tt[0]]) * bw.sea_side
        spots, heights = [], []
        for row, z in enumerate(float(v) for v in arm["z"]):
            d = crest_w / 2 + float(cfg["slope"]) * (crest_z - z)
            s = np.arange(float(arm["start"]) + row * step / 2, line.length, step)
            c = shapely.get_coordinates(shapely.line_interpolate_point(line, s))
            a = shapely.get_coordinates(shapely.line_interpolate_point(line, np.maximum(s - 0.5, 0.0)))
            b = shapely.get_coordinates(shapely.line_interpolate_point(line, np.minimum(s + 0.5, line.length)))
            t = (b - a) / np.maximum(np.linalg.norm(b - a, axis=1), 1e-9)[:, None]
            left = np.stack([-t[:, 1], t[:, 0]], axis=1)
            arc = int(math.ceil(math.pi * d / step))
            phi = (np.arange(arc) + 0.5 * (1 + row)) * math.pi / (arc + row)
            rim = sea[None, :] * np.cos(phi)[:, None] + tt[None, :] * np.sin(phi)[:, None]
            spots += [c + left * d, c - left * d, e[1] + rim * d]
            heights.append(np.full(2 * len(c) + arc, z + float(arm["lift"])))
        spots, heights = np.concatenate(spots), np.concatenate(heights)
        if not shapely.box(*tile.bounds).buffer(5.0).intersects(shapely.multipoints(spots)):
            continue
        rng = stream(tc.world.seed, "port", plan.settlement.id, n, "armour")
        draws = rng.random((len(spots), 6))
        for (x, y), z, r in zip(spots, heights, draws):
            x, y = x + (r[0] - 0.5) * 0.7, y + (r[1] - 0.5) * 0.7
            if x0 <= x < x1 and y0 <= y < y1 and not port.core.contains(Point(x, y)):
                out.append(Placement(f"armour_rock_{int(r[2] * variants) % variants}", float(x), float(y),
                                     float(z + (r[3] - 0.5) * 0.4), float(r[4] * 2 * math.pi), on_ground=False,
                                     scale=lo + (hi - lo) * float(r[5]), tilt=float((r[5] - 0.5) * 0.5)))
    return out


def keep_zone(port):
    """Where no other piece may stand: the open sea near the port and a meter along the quay walls."""
    sea = port.zone.difference(port.shore).difference(port.core)
    edge = port.walls.intersection(port.core.buffer(0.01)).buffer(1.0)
    zone = sea.union(edge)
    shapely.prepare(zone)
    return zone


# --- breakwater -----------------------------------------------------------------------------------------

def _frames(line: LineString) -> tuple:
    """Station points, unit tangents and left normals along the breakwater's center line."""
    p = np.asarray(line.coords)[:, :2]
    t = np.gradient(p, axis=0)
    t /= np.maximum(np.linalg.norm(t, axis=1), 1e-9)[:, None]
    return p, t, np.stack([-t[:, 1], t[:, 0]], axis=1)


def _half(cfg: dict, beds: np.ndarray, jit: np.ndarray) -> tuple:
    """One side's profile from the crest edge to the toe: (d, z, along) arrays (S, rows + 2) for beds (S,) and
    jitter (S, rows, 3) in [-1, 1] (out, up, along the line); the crest edge and the toe stay unjittered."""
    crest_z, crest_w = (float(v) for v in cfg["crest"])
    slope, rough, bury = float(cfg["slope"]), float(cfg["rough"]), float(cfg["bury"])
    hw = crest_w / 2
    bed = np.minimum(beds, crest_z - 1.5)
    f = np.asarray(cfg["rows"], dtype=np.float64)
    zn = crest_z - f[None, :] * (crest_z - bed[:, None])
    z = zn + jit[:, :, 1] * rough * 0.5
    d = hw + slope * (crest_z - zn) + jit[:, :, 0] * rough
    toe_z = bed - bury
    toe_d = hw + slope * (crest_z - toe_z)
    zero = np.zeros((len(bed), 1))
    dd = np.column_stack([np.full(len(bed), hw), d, toe_d])
    zz = np.column_stack([np.full(len(bed), crest_z), z, toe_z])
    along = np.hstack([zero, jit[:, :, 2] * rough, zero])
    return dd, zz, along


def _beds(tc, cfg: dict, c: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Seabed under the toe of a slope from center points c going out along unit directions v."""
    crest_z, crest_w = (float(v_) for v_ in cfg["crest"])
    slope = float(cfg["slope"])
    b0 = tc.ground.side_height(c[:, 0], c[:, 1], "sea")
    d = crest_w / 2 + slope * (crest_z - np.minimum(b0, crest_z - 1.5))
    q = c + v * d[:, None]
    return tc.ground.side_height(q[:, 0], q[:, 1], "sea")


def _grid(mb: MeshBuilder, mat: str, grid: np.ndarray, toward: np.ndarray | None = None) -> None:
    """A surface over a (rows, cols, 3) vertex grid with shared vertices and smooth normals. Faces turn up, or
    along `toward` ((rows, 3), per row) with meter UVs along the rows and down the height (a wall)."""
    r, c = grid.shape[:2]
    if r < 2 or c < 2:
        return
    pos = grid.reshape(-1, 3)
    i, j = np.meshgrid(np.arange(r - 1), np.arange(c - 1), indexing="ij")
    v00 = (i * c + j).ravel()
    idx = np.concatenate([np.stack([v00, v00 + c, v00 + c + 1], 1), np.stack([v00, v00 + c + 1, v00 + 1], 1)])
    a, b, cc = pos[idx[:, 0]], pos[idx[:, 1]], pos[idx[:, 2]]
    keep = np.linalg.norm(np.cross(b - a, cc - a), axis=1) > 1e-9
    idx = idx[keep]
    if not len(idx):
        return
    if toward is None:
        nrm = _vertex_normals(pos, idx)
        uv = np.stack([pos[:, 0], -pos[:, 1]], axis=1)
    else:
        row = idx[:, 0] // c
        a, b, cc = pos[idx[:, 0]], pos[idx[:, 1]], pos[idx[:, 2]]
        fn = np.cross(b - a, cc - a)
        back = (fn * toward[row]).sum(axis=1) < 0
        idx[back] = idx[back][:, ::-1]
        nrm = np.repeat(toward / np.maximum(np.linalg.norm(toward, axis=1), 1e-9)[:, None], c, axis=0)
        s0 = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(grid[:, 0, :2], axis=0), axis=1))])
        uv = np.stack([np.repeat(s0, c), -pos[:, 2]], axis=1)
    mb.add(mat, pos, nrm, uv, idx)


def _runs(own: np.ndarray, breaks=()) -> list:
    """(first, last) point indices of each run of owned segments (segment k joins points k and k + 1), also
    broken at the points `breaks`."""
    out, start = [], None
    cut = set(int(b) for b in breaks)
    for k, o in enumerate(list(own) + [False]):
        if start is not None and (not o or k in cut):
            out.append((start, k))
            start = None
        if o and start is None:
            start = k
    return out


def breakwater_meshes(mb: MeshBuilder, tc, port, plan, tile, light: bool = True) -> None:
    """Every breakwater's stretch owned by this tile: rubble slopes, crest road, crown wall; and the head with
    the lighthouse in the tile holding the tip (`light` False leaves the lighthouse out: mesh/lod.py)."""
    cfg = tc.port_cfg
    x0, y0, x1, y1 = tile.bounds
    crest_z = float(cfg["crest"][0])
    ph, pt = (float(v) for v in cfg["parapet"])
    heads = int(cfg["head"])
    for n, bw in enumerate(port.breakwaters):
        if not bw.line.buffer(60.0).intersects(tile):
            continue
        p, t, left = _frames(bw.line)
        m = len(p)
        rng = stream(tc.world.seed, "port", plan.settlement.id, n, "rubble")
        rows = len(cfg["rows"])
        jit = rng.uniform(-1.0, 1.0, size=(m + heads + 1, 2, rows, 3))
        sea_v, harbor_v = left * bw.sea_side, -left * bw.sea_side
        sea_half = _half(cfg, _beds(tc, cfg, p, sea_v), jit[:m, 0])
        harbor_half = _half(cfg, _beds(tc, cfg, p, harbor_v), jit[:m, 1])
        parts = []
        for (d, z, al), v, flip in ((harbor_half, harbor_v, True), (sea_half, sea_v, False)):
            xy = p[:, None, :] + v[:, None, :] * d[:, :, None] + t[:, None, :] * al[:, :, None]
            g = np.concatenate([xy, z[..., None]], axis=2)
            parts.append(g[:, ::-1] if flip else g)
        grid = np.concatenate(parts, axis=1)              # (m, 2 h, 3): harbor toe ... crest edges ... sea toe
        h = rows + 2
        mid = (p[:-1] + p[1:]) / 2
        own = (mid[:, 0] >= x0) & (mid[:, 0] < x1) & (mid[:, 1] >= y0) & (mid[:, 1] < y1)
        for a, b in _runs(own):
            g = grid[a:b + 1]
            _grid(mb, "rubble", g[:, :h])
            _grid(mb, "rubble", g[:, h:])
            _grid(mb, "quay", g[:, h - 1:h + 1])
            _crown(mb, p[a:b + 1], sea_v[a:b + 1], cfg, crest_z, ph, pt)
        tip = p[-1]
        if x0 <= tip[0] < x1 and y0 <= tip[1] < y1:
            last = lambda half: tuple(x[-1] for x in half)
            _head(mb, tc, cfg, tip, t[-1], sea_v[-1], last(sea_half), last(harbor_half), jit[m:, 0])
            if light:
                lighthouse_mesh(mb, cfg["lighthouse"], tip[0], tip[1], crest_z, bw.light[3])


def lighthouse_spots(tc, port, tile) -> list:
    """(x, y, z, color scheme) of each lighthouse standing in this tile, on the tip of its breakwater."""
    x0, y0, x1, y1 = tile.bounds
    crest_z = float(tc.port_cfg["crest"][0])
    tips = [(_frames(bw.line)[0][-1], bw.light[3]) for bw in port.breakwaters]
    return [(float(p[0]), float(p[1]), crest_z, scheme) for p, scheme in tips if x0 <= p[0] < x1 and y0 <= p[1] < y1]


def _crown(mb: MeshBuilder, p: np.ndarray, sea: np.ndarray, cfg: dict, z: float, height: float, thick: float) -> None:
    """The crown wall along the sea edge of the crest: outer face, top, inner face."""
    hw = float(cfg["crest"][1]) / 2
    outer, inner = p + sea * hw, p + sea * (hw - thick)
    n = len(p)
    _wall(mb, "quay_wall", outer, np.full(n, z + height), np.full(n, z), sea)
    _wall(mb, "quay_wall", inner, np.full(n, z + height), np.full(n, z), -sea)
    _grid(mb, "quay_wall", np.stack([np.column_stack([inner, np.full(n, z + height)]),
                                     np.column_stack([outer, np.full(n, z + height)])], 1))


def _head(mb: MeshBuilder, tc, cfg: dict, tip, tangent, sea, sea_end: tuple, harbor_end: tuple, jit) -> None:
    """The half-round head: the profile turned about the tip from the sea side through the forward direction to
    the harbor side, each angle on its own seabed and jitter (none at both ends, where it meets the sides' last
    profiles); the crest paved to the center."""
    k = len(jit) - 1
    phi = np.linspace(0.0, math.pi, k + 1)
    v = sea[None, :] * np.cos(phi)[:, None] + tangent[None, :] * np.sin(phi)[:, None]
    side = np.stack([-v[:, 1], v[:, 0]], axis=1)                   # along the head's rim
    c = np.tile(tip, (k + 1, 1))
    d, z, al = _half(cfg, _beds(tc, cfg, c, v), jit * np.sin(phi)[:, None, None])
    for (ed, ez, ea), sel in ((sea_end, 0), (harbor_end, k)):
        d[sel], z[sel] = ed, ez
        al[sel] = ea * float(np.sign(side[sel] @ tangent))      # the sides' jitter runs along the tangent
    xy = c[:, None, :] + v[:, None, :] * d[:, :, None] + side[:, None, :] * al[:, :, None]
    grid = np.concatenate([xy, z[..., None]], axis=2)              # (k + 1, rows + 2, 3): crest edge ... toe
    center = np.concatenate([c, np.full((k + 1, 1), float(cfg["crest"][0]))], axis=1)[:, None, :]
    _grid(mb, "quay", np.concatenate([center, grid[:, :1]], axis=1))
    _grid(mb, "rubble", grid)


# --- lighthouse -----------------------------------------------------------------------------------------

def lighthouse(cfg: dict, scheme: str) -> MeshBuilder:
    """The lighthouse at the origin, z up from its foot: stone drum, tapered tower in its color scheme, iron
    gallery and railing, glazed lantern, cap and finial."""
    mb = MeshBuilder()
    seg = int(cfg["segments"])
    rp, hp = (float(v) for v in cfg["plinth"])
    r0, r1, h = (float(v) for v in cfg["tower"])
    rg, tg = (float(v) for v in cfg["gallery"])
    rl, hl = (float(v) for v in cfg["lantern"])
    rr, hr = (float(v) for v in cfg["roof"])
    band = float(cfg["band"])
    white, red = "lighthouse_white", "lighthouse_red"
    _lathe(mb, [(rp, -0.4), (rp, hp), (r0, hp)], "quay_wall", seg)
    z0, z1 = hp, hp + h
    bands = {"white": [], "red_top": [(z1 - 2.2 * band, z1)],
             "bands": [(z0 + 0.3 * h, z0 + 0.3 * h + band), (z0 + 0.62 * h, z0 + 0.62 * h + band)]}[scheme]
    cuts = sorted({z0, z1, *[z for ab in bands for z in ab]})
    for za, zb in zip(cuts[:-1], cuts[1:]):
        mat = red if any(a <= za < b for a, b in bands) else white
        ra, rb = r0 + (r1 - r0) * (za - z0) / h, r0 + (r1 - r0) * (zb - z0) / h
        _lathe(mb, [(ra, za), (rb, zb)], mat, seg)
    iron = "canopy_iron"
    _lathe(mb, [(r1, z1), (rg, z1), (rg, z1 + tg), (0.0, z1 + tg)], iron, seg)
    zr = z1 + tg
    rail = float(cfg["railing"])
    _lathe(mb, [(rg - 0.05, zr), (rg - 0.05, zr + rail)], iron, seg)
    _lathe(mb, [(rg - 0.07, zr + rail), (rg - 0.07, zr)], iron, seg)
    _lathe(mb, [(rl, zr), (rl, zr + hl)], "lantern_glow", seg)
    zt = zr + hl
    cap = red if scheme != "bands" else iron
    _lathe(mb, [(0.0, zt), (rr, zt), (0.0, zt + hr)], cap, seg)
    _lathe(mb, [(0.12, zt + hr - 0.1), (0.12, zt + hr + 0.25), (0.0, zt + hr + 0.45)], iron, 6)
    return mb


def lighthouse_mesh(mb: MeshBuilder, cfg: dict, x: float, y: float, z: float, scheme: str) -> None:
    """The lighthouse drawn into the tile at (x, y) standing on z."""
    local = lighthouse(cfg, scheme)
    for mat, (pos, nrm, uv, tris, _n, _col) in local._parts.items():
        mb.add(mat, np.concatenate(pos) + np.array([x, y, z]), np.concatenate(nrm), np.concatenate(uv),
               np.concatenate(tris))
