"""Inland water in a tile (prompts 60 and 61): lakes, salt flats, river ribbons, and the fine ground around rivers.

A lake or a salt flat is drawn cell by cell of the terrain grid: every cell inside the lake's zone with a corner
of the ground below the level, at the level. The ground hides what lies over it, so the shore is where the land
really meets the level, and the outer edge of the drawn cells always lies under the ground (`Carve.fill` closes
the zone with a rim). Inland water uses `water_lake`, `water_river`, never `water`, which Blender hides for its sea.

A river's water is a ribbon one height across, on `River.surface`, a little wider than the water, so its edges
lie under the banks: the bank line is where ground and water really meet.

The channel is far narrower than the 8 m terrain grid, so the cells it crosses are drawn on a finer grid
(`[rivers] mesh_step`). Inside those cells every fine point takes the true ground; on the outer edge of the fine
cells the points stay on the coarse edge between its two corners, so the mesh has no crack and no seam.
"""
from __future__ import annotations

import numpy as np
import shapely
from shapely.geometry import Point
from shapely.ops import substring

from ..city.geo import lines
from .builder import MeshBuilder, ribbon_edges
from .gltf import hex_to_rgb, srgb_to_linear

TUCK = 1.5   # meters a ribbon's edge reaches under the bank


def upsample(a: np.ndarray, k: int) -> np.ndarray:
    """Bilinear: `k` fine cells to each coarse cell of a grid of nodes."""
    def along_axis(v, axis):
        n = v.shape[axis]
        t = np.arange((n - 1) * k + 1) / k
        i = np.minimum(t.astype(np.int64), n - 2)
        f = t - i
        shape = [1, 1]
        shape[axis] = len(t)
        f = f.reshape(shape)
        return np.take(v, i, axis) * (1.0 - f) + np.take(v, i + 1, axis) * f
    return along_axis(along_axis(a, 0), 1)


def fine_ground(tc, X, Y, Hu, H, past, names, skip, s: float, mb: MeshBuilder) -> tuple:
    """Draw the terrain cells a river's channel crosses on the fine grid, in one material colored per point (`shore_colors`).
    X, Y, Hu (before the rivers), H (after them) and `past` (meters past a bank) are the terrain grid with one cell
    of padding, `names` the tile's cell materials, `skip` its cells drawn apart. Returns (those cells as a mask over
    `names`, the lowest fine height)."""
    carve = tc.ground.carve
    k = int(round(s / float(carve.rc["mesh_step"])))
    padded = np.minimum.reduce([past[:-1, :-1], past[1:, :-1], past[:-1, 1:], past[1:, 1:]]) < 0.25 * s   # the water's edge is in
    fine = padded[1:-1, 1:-1] & ~skip
    if k < 2 or not fine.any():
        return np.zeros(names.shape, dtype=bool), np.inf
    padded = padded.copy()
    padded[1:-1, 1:-1] = fine
    cells = np.repeat(np.repeat(padded, k, axis=0), k, axis=1)
    inner = np.zeros((cells.shape[0] + 1, cells.shape[1] + 1), dtype=bool)
    inner[1:-1, 1:-1] = cells[:-1, :-1] & cells[1:, :-1] & cells[:-1, 1:] & cells[1:, 1:]
    Z = upsample(H, k)
    fs = s / k
    xs, ys = X[0, 0] + np.arange(Z.shape[1]) * fs, Y[0, 0] + np.arange(Z.shape[0]) * fs
    jj, ii = np.nonzero(inner)
    Z[jj, ii] = carve.cut(xs[ii], ys[jj], upsample(Hu, k)[jj, ii])
    own = np.zeros(cells.shape, dtype=bool)                 # the tile's own fine cells, without the padding
    own[k:-k, k:-k] = cells[k:-k, k:-k]
    fy, fx = np.nonzero(own)
    cols = Z.shape[1]
    sw, se, ne, nw = (fy * cols + fx, fy * cols + fx + 1, (fy + 1) * cols + fx + 1, (fy + 1) * cols + fx)
    z = Z.ravel()
    rise = np.abs(z[sw] - z[ne]) <= np.abs(z[se] - z[nw])   # each cell split along its flatter diagonal: a bank
    tris = np.concatenate([np.stack([sw, se, ne], 1)[rise], np.stack([sw, ne, nw], 1)[rise],   # never saws
                           np.stack([sw, se, nw], 1)[~rise], np.stack([se, ne, nw], 1)[~rise]])
    used, remap = np.unique(tris, return_inverse=True)
    j, i = used // cols, used % cols
    gx = (Z[j, i + 1] - Z[j, i - 1]) / (2 * fs)
    gy = (Z[j + 1, i] - Z[j - 1, i]) / (2 * fs)
    nrm = np.stack([-gx, -gy, np.ones(len(used))], axis=-1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    pos = np.stack([xs[i], ys[j], Z[j, i]], axis=-1)
    parent = np.clip(np.minimum(j, Z.shape[0] - 2) // k - 1, 0, names.shape[0] - 1), \
        np.clip(np.minimum(i, Z.shape[1] - 2) // k - 1, 0, names.shape[1] - 1)
    mb.add("river_bed", pos, nrm, np.stack([pos[:, 0], -pos[:, 1]], axis=1), remap.reshape(-1, 3),
           shore_colors(tc, pos[:, 0], pos[:, 1], pos[:, 2], names[parent]))
    return fine, float(pos[:, 2].min())


def land_tint(tc, x, y, sample=None) -> np.ndarray:
    """(N, 3) COLOR_0 of the ground at points x, y: the tile's tint, greener along the rivers. `sample`: the rivers
    there (`Carve.sample`), if at hand."""
    col = tc.tint(x, y)
    carve = tc.ground.carve
    cfg = tc.world.style.get("ground_tint", {})
    if carve is None or "riparian" not in cfg:
        return col
    f = carve.sample(x, y) if sample is None else sample
    near = np.isfinite(f.edge)
    if near.any():
        t = np.clip((f.past[near] - f.plain[near]) / float(cfg["riparian_fade"]), 0.0, 1.0)
        w = 1.0 - t * t * (3.0 - 2.0 * t)
        col[near] *= 1.0 + w[:, None] * (np.asarray(cfg["riparian"], dtype=np.float64) - 1.0)
    return col


def shore_colors(tc, x, y, z, names, slope=None) -> np.ndarray:
    """(N, 3) COLOR_0 of the ground drawn in `river_bed`, which carries one pale gravel while its points carry every
    color: the land's own (its material's over `river_bed`'s, from afar) out in the band, bare earth on a bank or a
    lake's rim, dark wet pebbles under the water, pale gravel on a dry oued's floor, a pale crust on a salt flat's
    rim, bare rock up a valley's steep wall (`slope`, per point). So a shore fades into the land, with no stair of cells."""
    flat = _flat_colors(tc)
    base = flat["river_bed"]
    land = np.array([flat[str(n)] for n in names]) / base
    style = tc.world.style.get("water", {})
    bank, bed, dry_bed, rim = (_linear(style[k]) / base for k in ("bank", "bed", "oued", "salt_rim"))
    carve = tc.ground.carve
    f = carve.sample(x, y)
    t = np.clip(f.past / float(style["bank_fade"]), 0.0, 1.0)
    w = (1.0 - t * t * (3.0 - 2.0 * t))[:, None]
    wet = np.clip(-f.edge / float(style["bed_fade"]), 0.0, 1.0)[:, None]
    floor = np.clip(1.0 - f.edge / f.lip.clip(1e-3), 0.0, 1.0)[:, None]
    channel = np.where(f.dry[:, None], bank + (dry_bed - bank) * floor, bank + (bed - bank) * wet)
    col = land + (channel - land) * w
    shore, salt = carve.rims(x, y, z, float(style["rim_height"]), float(style["salt_rim_height"]))
    col += (np.where(salt[:, None], rim, bank) - col) * shore[:, None] * (1.0 - w)
    if slope is not None:
        lo, hi = (float(v) for v in style["rock_slope"])
        t = np.clip((slope - lo) / (hi - lo), 0.0, 1.0)
        col += (flat["rock"] / base - col) * (t * t * (3.0 - 2.0 * t))[:, None]
    return np.clip(col, 0.0, 1.0) * land_tint(tc, x, y, f)


def rim_cells(tc, Xg, Yg, H) -> np.ndarray:
    """The terrain cells on a lake's bare rim."""
    style = tc.world.style.get("water", {})
    w = tc.ground.carve.rims(Xg, Yg, H, float(style["rim_height"]), float(style["salt_rim_height"]))[0].reshape(H.shape)
    return np.maximum.reduce([w[:-1, :-1], w[1:, :-1], w[:-1, 1:], w[1:, 1:]]) > 0.0


def wall_cells(tc, Hu, H, slope) -> np.ndarray:
    """The terrain cells on a river valley's steep walls: cut into the land and steep enough to bare the rock. The
    8 m cells of a rock material would stand out in stairs, so these fade to it point by point (`shore_colors`)."""
    lo = float(tc.world.style["water"]["rock_slope"][0])
    cut = Hu - H
    return ((np.maximum.reduce([cut[:-1, :-1], cut[1:, :-1], cut[:-1, 1:], cut[1:, 1:]]) > 0.2)
            & (np.maximum.reduce([slope[:-1, :-1], slope[1:, :-1], slope[:-1, 1:], slope[1:, 1:]]) > lo))


def rim_mesh(mb: MeshBuilder, tc, quads, pos, nrm, uv, names, n: int, slope) -> None:
    """Terrain cells `quads` (node numbers of a grid of `n` + 1 to a side) in `river_bed`, each node colored."""
    tris = np.concatenate([quads[:, [0, 1, 2]], quads[:, [0, 2, 3]]])
    used, remap = np.unique(tris, return_inverse=True)
    j, i = np.minimum(used // (n + 1), n - 1), np.minimum(used % (n + 1), n - 1)
    mb.add("river_bed", pos[used], nrm[used], uv[used], remap.reshape(-1, 3),
           shore_colors(tc, pos[used, 0], pos[used, 1], pos[used, 2], names[j, i], slope.ravel()[used]))


def _linear(color: str) -> np.ndarray:
    return np.array(srgb_to_linear(hex_to_rgb(color)), dtype=np.float64)


def _flat_colors(tc) -> dict:
    """Every ground material's color as seen from afar, linear, made once per process."""
    if getattr(tc, "flat_colors", None) is None:
        from .lod import flat_materials
        tc.flat_colors = {k: _linear(v.get("color", "#cccccc")) for k, v in flat_materials(tc).items()}
    return tc.flat_colors


def level_cells(mb: MeshBuilder, tc, Xg, Yg, Hu, s: float) -> None:
    """Lakes and salt flats over a grid of nodes Xg, Yg with ground Hu before the rivers (a river's channel never
    lets a lake in)."""
    carve = tc.ground.carve
    if carve is None:
        return
    x0, y0, x1, y1 = Xg[0, 0], Yg[0, 0], Xg[-1, -1], Yg[-1, -1]
    low = None
    for sh in carve.shores:
        bx0, by0, bx1, by1 = sh.box
        if bx1 < x0 or bx0 > x1 or by1 < y0 or by0 > y1:
            continue
        if low is None:
            low = np.minimum.reduce([Hu[:-1, :-1], Hu[1:, :-1], Hu[:-1, 1:], Hu[1:, 1:]])
        cx, cy = Xg[:-1, :-1] + s / 2, Yg[:-1, :-1] + s / 2
        m = (low < sh.level) & shapely.contains_xy(sh.zone, cx, cy)
        if m.any():
            _flat(mb, tc, "salt_crust" if sh.salt else "water_lake", m, Xg, Yg, sh.level)


def _flat(mb: MeshBuilder, tc, mat: str, m: np.ndarray, Xg, Yg, z: float) -> None:
    """The cells `m` of a grid of nodes at height z. A salt crust keeps every node, for its tint; water is one
    long quad per run of cells along a row."""
    cols = Xg.shape[1]
    if mat == "salt_crust":
        jj, ii = np.nonzero(m)
        v00 = jj * cols + ii
        quads = np.stack([v00, v00 + 1, v00 + cols + 1, v00 + cols], axis=-1)
    else:
        edges = np.diff(np.pad(m.astype(np.int8), ((0, 0), (1, 1))), axis=1)
        (jj, first), (_, last) = np.nonzero(edges == 1), np.nonzero(edges == -1)
        quads = np.stack([jj * cols + first, jj * cols + last, (jj + 1) * cols + last, (jj + 1) * cols + first], axis=-1)
    tris = np.concatenate([quads[:, [0, 1, 2]], quads[:, [0, 2, 3]]])
    used, remap = np.unique(tris, return_inverse=True)
    x, y = Xg.ravel()[used], Yg.ravel()[used]
    pos = np.column_stack([x, y, np.full(len(used), z)])
    mb.add(mat, pos, np.tile([0.0, 0.0, 1.0], (len(used), 1)), np.stack([x, -y], axis=1), remap.reshape(-1, 3),
           tc.tint(x, y) if mat == "salt_crust" else None)


def ribbons_in(tc, tile) -> list:
    """[(ribbon, start, end)]: the stretches of river water on this tile, in meters along each river."""
    if tc.ribbon_tree is None:
        return []
    out = []
    for k in tc.ribbon_tree.query(tile, predicate="intersects"):
        rib = tc.ribbons[int(k)]
        for seg in lines(rib.line.intersection(tile)):
            a, b = seg.coords[0], seg.coords[-1]
            s = sorted((rib.line.project(Point(a)), rib.line.project(Point(b))))
            lo, hi = max(s[0], rib.start), min(s[1], rib.end)
            if hi - lo > 0.05:
                out.append((rib, lo, hi))
    return out


def river_meshes(mb: MeshBuilder, tc, tile) -> None:
    """The water of the rivers on this tile, one height across."""
    for rib, lo, hi in ribbons_in(tc, tile):
        edges = ribbon_edges(substring(rib.line, lo, hi).coords, 2.0)
        if edges is None:
            continue
        p, seg, left, right = edges
        s = lo + np.concatenate([[0.0], np.cumsum(seg)])
        half = np.interp(s, rib.along, rib.half) + np.where(np.interp(s, rib.along, rib.half) > 0.05, TUCK, 0.0)
        z = np.interp(s, rib.along, rib.surface)
        pos = np.empty((len(p), 2, 3))
        pos[:, 0, :2], pos[:, 1, :2] = p + (left - p) * half[:, None], p + (right - p) * half[:, None]
        pos[:, 0, 2] = pos[:, 1, 2] = z
        uv = np.empty((len(p), 2, 2))
        uv[:, :, 0] = s[:, None]
        uv[:, 0, 1], uv[:, 1, 1] = -half, half
        base = np.arange(len(p) - 1) * 2
        tris = np.concatenate([np.stack([base, base + 1, base + 3], 1), np.stack([base, base + 3, base + 2], 1)])
        mb.add("water_river", pos.reshape(-1, 3), np.tile([0.0, 0.0, 1.0], (2 * len(p), 1)), uv.reshape(-1, 2), tris)
