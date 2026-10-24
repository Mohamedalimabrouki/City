"""Level-of-detail tiles (prompt 40): `tile_i_j_lod1.glb`, a light stand-in for each tile seen from afar.

Written right after its full tile, from the same plan data, with no dressing, people or trees:

  terrain   a `[tiles.lod] terrain_step` grid (32 m) with the full tile's COLOR_0 tint and smooth normals.
            Each tile edge keeps the full tile's 8 m points (border cells are fanned onto them), so a full
            and a lod1 tile meet exactly, and a skirt hangs `skirt` m below every edge against the
            millimetre cracks of two quantization frames. Cells a quay wall crosses are cut by the wall
            as the full tile cuts its 8 m cells, so the quay edge stays sharp.
  streets   flat ribbons draped on that terrain, `street_lift` m up; country roads too; the water plane
            whenever the full tile has one
  blocks    the buildings of one city block merged: the union of their footprints (gaps under 2 x
            `close` m closed, small courtyards filled, simplified), up to the block's mean roof height
            over the ground, each wall in the color of the building it lies on (from afar the street
            keeps its mix of ochre, cream and blue), a cap in the block's dominant roof color. A block
            belongs to the tile holding its centroid, so none is drawn twice
  skyline   tall buildings (`tall`, `tall_ratio`) and the monuments stay out of the merge as their own
            low-poly shapes: masses as prisms, minaret lanterns and caps, domes on drums, kasbah and
            rampart walls and towers with their battlements as a band, the lighthouse with 8 sides. The
            cathedral, theatre and railway station, the quay walls and breakwater are their full meshes
            simplified by vertex clustering on a world-aligned grid (`cluster`, `cluster_port` m)

Colors are flat (no texture, no UVs): a textured material's color is multiplied by the mean of its image,
so from afar a lod1 tile has the tone of the full tile's mipmapped textures.
"""
from __future__ import annotations

import io
import os
from functools import lru_cache
from pathlib import Path

import numpy as np
import shapely
from PIL import Image
from shapely.geometry import Polygon, box
from shapely.geometry.polygon import orient
from shapely.strtree import STRtree

from ..city.geo import frame, lines, polygons
from ..city.massing import masses
from .builder import (MeshBuilder, add_dome, add_hip_roof, add_skirt, extrude, rectangle, regular_polygon,
                      ribbon_edges, triangulate)
from .gltf import hex_to_rgb, write_glb
from .landmarks import landmark_mesh
from .port import breakwater_meshes, lighthouse_mesh, lighthouse_spots, split_cells, wall_meshes
from .station import station_mesh
from .textures import encoded, spec_for
from .tile import (LANDMARK_KINDS, PAVED_KINDS, ROAD_LIFT, STATION_KINDS, TileContext, cell_materials,
                   tile_bounds, water_mesh)

CLUSTERED = LANDMARK_KINDS | STATION_KINDS            # drawn by their own long mesh functions: clustered
SOLO = frozenset({"minaret", "mosque_hall", "mosque_court", "marabout", "tower", "wall", "kasbah_wall",
                  "kasbah_tower", "kasbah_gate", "kasbah_palace"})   # monuments: always their own low-poly shapes
PARAPET_KINDS = frozenset({"house", "apartments", "domed"})   # flat roofs with a parapet in the full tile


def lod_of(tc: TileContext) -> "Lod":
    """The lod settings and per-city block tables of this build, made once per process."""
    if tc.lod is None:
        tc.lod = Lod(tc)
    return tc.lod


class Lod:
    """What every lod1 tile of a build shares: settings, flat materials and each city's blocks."""

    def __init__(self, tc: TileContext):
        c = tc.lod_cfg
        m = int(round(tc.size / tc.step))                 # the full tile's cells along a side
        even = [d for d in range(2, m // 2 + 1, 2) if m % d == 0]
        target = float(c["terrain_step"]) / tc.step
        self.ratio = min(even, key=lambda d: (abs(d - target), d)) if even else 1   # 4: 32 m over 8 m
        self.skirt = float(c["skirt"])
        self.street_lift = float(c["street_lift"])
        self.street_step = float(c["street_step"])
        self.street_simplify = float(c["street_simplify"])
        self.skip_streets = frozenset(c.get("skip_streets", ()))
        self.close = float(c["close"])
        self.simplify = float(c["simplify"])
        self.min_hole = float(c["min_hole"])
        self.min_part = float(c["min_part"])
        self.sink = float(c["sink"])
        self.parapet = float(c["parapet"])
        self.hip = float(c["hip"])
        self.tall = float(c["tall"])
        self.tall_ratio = float(c["tall_ratio"])
        self.segments = int(c["dome_segments"])
        self.cluster = float(c["cluster"])
        self.cluster_port = float(c["cluster_port"])
        self.drop = frozenset(c.get("cluster_drop", ()))
        self.crease = float(c["crease"])
        self.materials = flat_materials(tc)
        self.cities = [Blocks(self, plan) for plan in tc.plans]


# --- flat materials ---------------------------------------------------------------------------------------

def _to_linear(c: np.ndarray) -> np.ndarray:
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _to_srgb(c: np.ndarray) -> np.ndarray:
    c = np.clip(c, 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1.0 / 2.4) - 0.055)


@lru_cache(maxsize=64)
def _image_mean(name: str, seed: int, spec_items: tuple) -> float:
    """Mean linear value of a texture image (they are grey): what its smallest mipmap shows."""
    data = encoded(name, seed, dict(spec_items)).data
    grey = np.asarray(Image.open(io.BytesIO(data)).convert("L"), dtype=np.float64) / 255.0
    return float(_to_linear(grey).mean())


def flat_materials(tc: TileContext) -> dict:
    """The tile materials without textures, each textured color multiplied by its image's mean."""
    out = {}
    for name, spec in tc.materials.items():
        flat = {k: v for k, v in spec.items() if k not in ("texture", "texture_size")}
        texture = spec.get("texture")
        if texture and texture in tc.texture_images:
            mean = _image_mean(texture, tc.world.seed, tuple(sorted(spec_for(tc.world.style, texture).items())))
            rgb = _to_srgb(_to_linear(np.array(hex_to_rgb(spec.get("color", "#cccccc")))) * mean)
            flat["color"] = "#" + "".join(f"{int(round(v * 255.0)):02X}" for v in rgb)
        out[name] = flat
    return out


# --- terrain -----------------------------------------------------------------------------------------------

class Terrain:
    """The lod1 terrain of one tile: 32 m cells on the full tile's 8 m lattice, the full tile's 8 m points along
    the tile edges (border cells fanned onto them), cells a quay wall crosses cut by the wall as the full tile
    cuts its 8 m cells (`split_cells`, here at 32 m). `surface(x, y)` is the drawn height."""

    def __init__(self, tc: TileContext, lod: Lod, x0: float, y0: float):
        self.tc, self.x0, self.y0 = tc, x0, y0
        self.f, self.r = tc.step, lod.ratio
        self.s = self.f * self.r
        self.n = int(round(tc.size / self.f)) // self.r   # the full grid, r of its cells to one
        n, s = self.n, self.s
        xs = x0 + np.arange(-1, n + 2) * s
        ys = y0 + np.arange(-1, n + 2) * s
        X, Y = np.meshgrid(xs, ys)
        He = tc.height(X, Y)
        gx = (He[1:-1, 2:] - He[1:-1, :-2]) / (2 * s)
        gy = (He[2:, 1:-1] - He[:-2, 1:-1]) / (2 * s)
        Xg, Yg = X[1:-1, 1:-1], Y[1:-1, 1:-1]
        self.names, self.cut = cell_materials(tc, Xg, Yg, He[1:-1, 1:-1], gx, gy, s)
        self.split = (Xg[:-1, :-1][self.cut], Yg[:-1, :-1][self.cut], self.names[self.cut])
        self.tris: list = []                      # triangles as lattice points (i, j) in steps of f from x0, y0
        self.mats: list = []
        self.cells: list = []                     # cell (cy * n + cx) of each triangle
        for cy in range(n):
            for cx in range(n):
                if not self.cut[cy, cx]:
                    self._cell(cx, cy)
        self._skirts()

    def _cell(self, cx: int, cy: int) -> None:
        """Two triangles on the full tile's diagonal, or a fan onto the 8 m points of the sides on a tile edge."""
        r, n = self.r, self.n
        i, j = cx * r, cy * r
        corners = [(i, j), (i + r, j), (i + r, j + r), (i, j + r)]          # SW, SE, NE, NW, counter-clockwise
        sides = [r > 1 and not (0 <= cx + dx < n and 0 <= cy + dy < n)      # S, E, N, W (side k: corner k to k+1)
                 for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0))]
        ring, at = [], []
        for k in range(4):
            a, b = corners[k], corners[(k + 1) % 4]
            at.append(len(ring))
            steps = r if sides[k] else 1
            for q in range(steps):
                ring.append((a[0] + (b[0] - a[0]) * q // steps, a[1] + (b[1] - a[1]) * q // steps))
        apex = next((k for k in range(4) if not sides[k] and not sides[(k - 1) % 4]), None)
        if not any(sides):
            fans = [(corners[0], corners[1], corners[2]), (corners[0], corners[2], corners[3])]   # the full diagonal
        elif apex is not None:                    # from a corner whose two sides are plain
            order = ring[at[apex]:] + ring[:at[apex]]
            fans = [(order[0], order[q], order[q + 1]) for q in range(1, len(order) - 1)]
        else:                                     # a tile one cell wide: from the cell's center
            c = (i + r // 2, j + r // 2)
            fans = [(c, ring[q], ring[(q + 1) % len(ring)]) for q in range(len(ring))]
        for t in fans:
            self.tris.append(t)
            self.mats.append(str(self.names[cy, cx]))
            self.cells.append(cy * n + cx)

    def _skirts(self) -> None:
        """A strip down from every tile edge: the 8 m edge points above, the 32 m nodes `skirt` m below."""
        m, r, n = self.n * self.r, self.r, self.n
        self.skirt_tris: list = []                 # (key or ("down", key), ...), material, outward (dx, dy)
        for side in range(4):
            for c in range(n):
                if side == 0:
                    top, cell, out = [(c * r + q, 0) for q in range(r + 1)], (0, c), (0, -1)
                elif side == 1:
                    top, cell, out = [(m, c * r + q) for q in range(r + 1)], (c, n - 1), (1, 0)
                elif side == 2:
                    top, cell, out = [(c * r + q, m) for q in range(r + 1)], (n - 1, c), (0, 1)
                else:
                    top, cell, out = [(0, c * r + q) for q in range(r + 1)], (c, 0), (-1, 0)
                a, b = ("down", top[0]), ("down", top[-1])
                half = r // 2
                tris = [(a, top[q + 1], top[q]) for q in range(half)] + [(a, b, top[half])]
                tris += [(b, top[q + 1], top[q]) for q in range(half, r)]
                for t in tris:
                    self.skirt_tris.append((t, str(self.names[cell]), out))

    def draw(self, mb: MeshBuilder, lod: Lod) -> None:
        tc, f = self.tc, self.f
        lattice = {k for t in self.tris for k in t}
        lattice.update(k[1] if isinstance(k[0], str) else k for t, _, _ in self.skirt_tris for k in t)
        keys = sorted(lattice)
        index = {k: v for v, k in enumerate(keys)}
        ij = np.array(keys, dtype=np.float64)
        x, y = self.x0 + ij[:, 0] * f, self.y0 + ij[:, 1] * f
        h = tc.height(np.concatenate([x, x + f, x - f, x, x]), np.concatenate([y, y, y, y + f, y - f]))
        z, hx1, hx0, hy1, hy0 = np.split(np.asarray(h, dtype=np.float64), 5)
        nrm = np.stack([-(hx1 - hx0) / (2 * f), -(hy1 - hy0) / (2 * f), np.ones_like(z)], axis=1)
        nrm /= np.linalg.norm(nrm, axis=1, keepdims=True)
        pos = np.column_stack([x, y, z])
        col = tc.tint(x, y)
        self.pos, self.index = pos, index
        down = pos - [0.0, 0.0, lod.skirt]
        v = len(pos)
        allpos, allnrm, allcol = np.vstack([pos, down]), np.vstack([nrm, nrm]), np.vstack([col, col])
        rows: dict = {}
        for t, mat in zip(self.tris, self.mats):
            rows.setdefault(mat, []).append([index[k] for k in t])
        ids = np.array([[index[k[1]] + v if isinstance(k[0], str) else index[k] for k in t]
                        for t, _, _ in self.skirt_tris], dtype=np.int64)
        out = np.array([o for _, _, o in self.skirt_tris], dtype=np.float64)
        p = allpos[ids]
        normal = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
        flip = normal[:, 0] * out[:, 0] + normal[:, 1] * out[:, 1] < 0     # every face out of the tile
        ids[flip] = ids[flip][:, [0, 2, 1]]
        for t, (_, mat, _) in zip(ids.tolist(), self.skirt_tris):
            rows.setdefault(mat, []).append(t)
        for mat in sorted(rows):
            t = np.array(rows[mat], dtype=np.int64)
            used, remap = np.unique(t, return_inverse=True)
            mb.add(mat, allpos[used], allnrm[used], np.zeros((len(used), 2)), remap.reshape(-1, 3), allcol[used])
        split_cells(mb, tc, *self.split, self.s)
        self._lookup()

    def _lookup(self) -> None:
        """Per cell, its triangles (for `surface`), padded with -1."""
        self.tri = np.array([[self.index[k] for k in t] for t in self.tris], dtype=np.int64).reshape(-1, 3)
        cells = np.array(self.cells, dtype=np.int64)
        count = np.bincount(cells, minlength=self.n * self.n)
        self.table = np.full((self.n * self.n, max(1, int(count.max(initial=0)))), -1, dtype=np.int64)
        for k, c in enumerate(cells):
            self.table[c, np.argmax(self.table[c] < 0)] = k

    def surface(self, x, y) -> np.ndarray:
        """Height of the drawn lod1 terrain at points x, y (the ground itself in cells a quay wall cuts)."""
        x = np.asarray(x, dtype=np.float64).reshape(-1)
        y = np.asarray(y, dtype=np.float64).reshape(-1)
        cx = np.clip(np.floor((x - self.x0) / self.s).astype(np.int64), 0, self.n - 1)
        cy = np.clip(np.floor((y - self.y0) / self.s).astype(np.int64), 0, self.n - 1)
        cand = self.table[cy * self.n + cx]                                      # (Q, K) triangles of each cell
        drawn = (cand >= 0).any(axis=1)
        out = np.zeros(len(x))
        if not drawn.all():
            out[~drawn] = np.asarray(self.tc.height(x[~drawn], y[~drawn]), dtype=np.float64).reshape(-1)
        if not drawn.any():
            return out
        cand = cand[drawn]
        p = self.pos[self.tri[np.maximum(cand, 0)]]                             # (Q, K, 3 corners, xyz)
        e1, e2 = p[..., 1, :2] - p[..., 0, :2], p[..., 2, :2] - p[..., 0, :2]
        d = np.stack([x[drawn], y[drawn]], axis=1)[:, None, :] - p[..., 0, :2]
        det = e1[..., 0] * e2[..., 1] - e2[..., 0] * e1[..., 1]
        det = np.where(np.abs(det) < 1e-12, 1e-12, det)
        l1 = (d[..., 0] * e2[..., 1] - e2[..., 0] * d[..., 1]) / det
        l2 = (e1[..., 0] * d[..., 1] - d[..., 0] * e1[..., 1]) / det
        l0 = 1.0 - l1 - l2
        worst = np.where(cand >= 0, np.minimum(np.minimum(l0, l1), l2), -np.inf)
        k = np.argmax(worst, axis=1)                                            # inside, or the nearest one
        rows = np.arange(len(k))
        out[drawn] = l0[rows, k] * p[rows, k, 0, 2] + l1[rows, k] * p[rows, k, 1, 2] + l2[rows, k] * p[rows, k, 2, 2]
        return out


# --- streets -----------------------------------------------------------------------------------------------

def street_ribbons(tc: TileContext, lod: Lod, plan, street_tree, tile) -> list:
    """[(line, width, material, lift)] of the streets crossing this tile, simplified."""
    out = []
    for k in street_tree.query(tile, predicate="intersects") if street_tree is not None else ():
        st = plan.streets[int(k)]
        if st.kind not in lod.skip_streets:
            out += [(seg, st.width, st.surface or "asphalt", lod.street_lift)
                    for seg in lines(st.line.intersection(tile)) if seg.length > 0.5]
    return out


def road_ribbons(tc: TileContext, lod: Lod, tile) -> list:
    """The same for the country roads outside the cities."""
    out = []
    for k in tc.road_tree.query(tile, predicate="intersects") if tc.road_tree is not None else ():
        piece = tc.road_lines[int(k)].intersection(tile)
        if tc.city_area is not None:
            piece = piece.difference(tc.city_area)
        out += [(seg, tc.world.roads[int(k)].width, "asphalt", max(ROAD_LIFT, lod.street_lift))
                for seg in lines(piece) if seg.length > 0.5]
    return out


def ribbons(mb: MeshBuilder, lod: Lod, items: list, surface) -> None:
    """Flat strips draped on the lod terrain, with one height query for all of them."""
    strips = []
    for line, width, mat, lift in items:
        edges = ribbon_edges(shapely.segmentize(line.simplify(lod.street_simplify), lod.street_step).coords, width)
        if edges is not None:
            strips.append((edges[2], edges[3], mat, lift))
    if not strips:
        return
    xy = np.concatenate([np.concatenate([left, right]) for left, right, _, _ in strips])
    z = np.split(surface(xy[:, 0], xy[:, 1]), np.cumsum([2 * len(left) for left, _, _, _ in strips])[:-1])
    for (left, right, mat, lift), zz in zip(strips, z):
        n = len(left)
        pos = np.empty((n, 2, 3))
        pos[:, 0, :2], pos[:, 0, 2] = left, zz[:n] + lift
        pos[:, 1, :2], pos[:, 1, 2] = right, zz[n:] + lift
        base = np.arange(n - 1) * 2
        tris = np.concatenate([np.stack([base, base + 1, base + 3], 1), np.stack([base, base + 3, base + 2], 1)])
        mb.add(mat, pos.reshape(-1, 3), np.tile([0.0, 0.0, 1.0], (2 * n, 1)), np.zeros((2 * n, 2)), tris)


# --- buildings ---------------------------------------------------------------------------------------------

class Blocks:
    """One city's buildings sorted for lod1: each into the block holding it (merged there), or drawn alone (a
    monument, a tall building, one outside every block), or clustered (the long-mesh landmarks)."""

    def __init__(self, lod: Lod, plan):
        self.plan = plan
        bs = plan.buildings
        n = len(bs)
        self.top = np.zeros(n)            # roof height above the building's highest ground, area-weighted
        self.area = np.zeros(n)
        self.roof = [""] * n              # the roof material covering most of it
        role = np.array(["block"] * n, dtype=object)
        for k, b in enumerate(bs):
            if b.kind in PAVED_KINDS:
                role[k] = "skip"
                continue
            if b.kind in CLUSTERED:
                role[k] = "cluster"
                continue
            if b.kind in SOLO:
                role[k] = "solo"
            ms = masses(b)
            areas = np.array([m.polygon.area for m in ms])
            extra = [lod.hip if m.shape == "hip" else (lod.parapet if b.kind in PARAPET_KINDS else 0.0) for m in ms]
            self.area[k] = float(areas.sum())
            self.top[k] = float(np.dot(areas, [m.top + e for m, e in zip(ms, extra)]) / max(areas.sum(), 1e-9))
            by_roof: dict = {}
            for m, a in zip(ms, areas):
                by_roof[m.roof or b.roof] = by_roof.get(m.roof or b.roof, 0.0) + a
            self.roof[k] = max(sorted(by_roof), key=lambda r: by_roof[r])
        block = np.full(n, -1, dtype=np.int64)
        if plan.blocks and n:
            tree = STRtree([poly for poly, _ in plan.blocks])
            inside, found = tree.query(shapely.point_on_surface([b.footprint for b in bs]), predicate="within")
            block[inside[::-1]] = found[::-1]             # the first block found wins
        role[(block < 0) & (role == "block")] = "solo"
        self.members: dict = {}
        for k in np.nonzero(role == "block")[0]:
            self.members.setdefault(int(block[k]), []).append(int(k))
        for bi, ks in self.members.items():               # the skyline: tall buildings stand alone
            mean = np.dot(self.area[ks], self.top[ks]) / max(self.area[ks].sum(), 1e-9)
            tall = [k for k in ks if self.top[k] >= max(lod.tall, lod.tall_ratio * mean)]
            role[tall] = "solo"
            self.members[bi] = [k for k in ks if role[k] == "block"]
        self.role = role
        cents = [shapely.centroid(plan.blocks[bi][0]) for bi in sorted(self.members)]
        self.order = sorted(self.members)
        self.block_xy = shapely.get_coordinates(cents) if cents else np.zeros((0, 2))

    def draw(self, mb: MeshBuilder, tc: TileContext, lod: Lod, centers: np.ndarray, x0, y0, x1, y1) -> None:
        bx, by = self.block_xy[:, 0], self.block_xy[:, 1]
        mine = np.nonzero((bx >= x0) & (bx < x1) & (by >= y0) & (by < y1))[0]   # blocks by their centroid
        blocks_mesh(mb, tc, lod, self, [ks for ks in (self.members[self.order[int(m)]] for m in mine) if ks])
        inside = (centers[:, 0] >= x0) & (centers[:, 0] < x1) & (centers[:, 1] >= y0) & (centers[:, 1] < y1)
        for k in np.nonzero(inside)[0]:
            b = self.plan.buildings[int(k)]
            if self.role[k] == "solo":
                solo_mesh(mb, tc, lod, b)
            elif self.role[k] == "cluster":
                local = MeshBuilder()
                if b.kind in LANDMARK_KINDS:
                    landmark_mesh(local, b, tc.height, tc.landmarks)
                else:
                    station_mesh(local, b, tc.height, tc.station, tc.world.seed)
                cluster(local, mb, lod.cluster, lod.drop, lod.crease)


def _filled(poly: Polygon, min_hole: float) -> Polygon:
    holes = [h for h in poly.interiors if Polygon(h).area >= min_hole]
    return orient(Polygon(poly.exterior, holes), sign=1.0)


def _dominant(weights: dict) -> str:
    return max(sorted(weights), key=lambda name: weights[name])


def _heights(tc: TileContext, chunks: list) -> list:
    """Ground heights at every (N, 2) array of `chunks`, with one query for all."""
    if not chunks:
        return []
    xy = np.concatenate(chunks)
    z = np.asarray(tc.height(xy[:, 0], xy[:, 1]), dtype=np.float64).reshape(-1)
    return np.split(z, np.cumsum([len(c) for c in chunks])[:-1])


def blocks_mesh(mb: MeshBuilder, tc: TileContext, lod: Lod, blocks: Blocks, owned: list) -> None:
    """The merged buildings of each block in `owned` (lists of building indices): union, closed, filled and
    simplified; walls and a cap that follow the ground at the block's mean roof height above it, each wall in
    the color of its nearest building. Two ground queries for the whole tile."""
    plan = blocks.plan
    groups = [[plan.buildings[k] for k in ks] for ks in owned]
    chunks = []
    for bs in groups:                             # every footprint's ring (its highest point) and its centroid
        chunks += [np.asarray(b.footprint.exterior.coords)[:, :2] for b in bs]
        chunks.append(shapely.get_coordinates(shapely.centroid([b.footprint for b in bs])))
    z = iter(_heights(tc, chunks))
    shapes = []
    for ks, bs in zip(owned, groups):
        high = np.array([next(z).max() for _ in bs])
        area = blocks.area[ks]
        rise = float(np.dot(area, high + blocks.top[ks] - next(z)) / max(area.sum(), 1e-9))
        roofs: dict = {}
        for a, k in zip(area, ks):
            roofs[blocks.roof[k]] = roofs.get(blocks.roof[k], 0.0) + a
        grown = shapely.buffer([b.footprint for b in bs], lod.close, join_style="mitre")
        merged = shapely.union_all(grown).buffer(-lod.close, join_style="mitre").simplify(lod.simplify)
        near = STRtree([b.footprint for b in bs])
        for poly in polygons(merged):
            if poly.area >= lod.min_part:
                poly = _filled(poly, lod.min_hole)
                rings = [np.asarray(r.coords)[:-1, :2] for r in (poly.exterior, *poly.interiors)]
                shapes.append((rings, triangulate(poly), rise, _dominant(roofs), near, bs))
    chunks = []
    for rings, tri, *_ in shapes:
        chunks += rings + [tri.reshape(-1, 2)]
    z = iter(_heights(tc, chunks))
    for rings, tri, rise, roof, near, bs in shapes:
        for pts in rings:
            gz = next(z)
            mids = shapely.points((pts + np.roll(pts, -1, axis=0)) / 2)
            color = np.array([bs[int(k)].wall for k in near.nearest(mids)], dtype=object)
            for wall in sorted(set(color)):
                add_skirt(mb, pts, gz + rise, gz - lod.sink, wall, only=color == wall)
        cap = np.column_stack([tri.reshape(-1, 2), next(z) + rise])
        if len(cap):
            mb.add(roof, cap, np.tile([0.0, 0.0, 1.0], (len(cap), 1)), np.zeros((len(cap), 2)),
                   np.arange(len(cap)).reshape(-1, 3))


def solo_mesh(mb: MeshBuilder, tc: TileContext, lod: Lod, b) -> None:
    """A monument or tall building on its own: each mass a prism (a hip roof where it has one), domes on drums,
    a minaret's lantern and cap, a corner dome or turret, battlements as a band."""
    ring = np.asarray(orient(b.footprint, sign=1.0).exterior.coords)
    ground = np.asarray(tc.height(ring[:, 0], ring[:, 1]), dtype=np.float64)
    low, high = float(ground.min()), float(ground.max())
    z0 = low - lod.sink
    band = 0.0
    if b.battlement:
        band = float(b.battlement["breast"]) + 0.5 * float(b.battlement["merlon"][2])
    for m in masses(b):
        z = high + m.top
        for poly in polygons(m.polygon.simplify(lod.simplify * 0.5)):
            poly = _filled(poly, lod.min_hole)
            if m.shape == "hip":
                extrude(mb, poly, z0, z, b.wall, None)
                cx, cy, length, width, angle = frame(poly)
                corners = np.asarray(rectangle(cx, cy, length, width, angle).exterior.coords)[:4]
                add_hip_roof(mb, corners, z, 0.32 * width, m.roof or b.roof)
            else:
                lift = lod.parapet if b.kind in PARAPET_KINDS else band
                extrude(mb, poly, z0, z + lift, b.wall, m.roof or b.roof)
    z1 = high + b.height
    seg = lod.segments
    for x, y, r, mat in b.domes:
        extrude(mb, regular_polygon(x, y, r, seg), z1, z1 + 0.18 * r, b.wall, None)
        add_dome(mb, x, y, z1 + 0.18 * r, r, mat, segments=seg, rings=2)
    if b.top and "x" in b.top:                                   # a colonial corner dome or turret
        t = b.top
        extrude(mb, regular_polygon(t["x"], t["y"], t["radius"], seg), z1, z1 + t["height"], t["material"], None)
        add_dome(mb, t["x"], t["y"], z1 + t["height"], t["radius"], t["cap"], height=t["rise"], segments=seg,
                 rings=2)
    elif b.top:                                                  # a minaret's lantern and its cap
        cx, cy, _, _, angle = frame(b.footprint)
        side, h = b.top["side"], b.top["height"]
        extrude(mb, rectangle(cx, cy, side, side, angle), z1, z1 + h, b.top["material"], None)
        add_dome(mb, cx, cy, z1 + h, side * 0.5, b.top["cap"], height=side * 0.62, segments=seg, rings=2)


def harbor_mesh(mb: MeshBuilder, tc: TileContext, lod: Lod, port, plan, tile) -> None:
    """Quay walls and the breakwater clustered, the lighthouse as its own low-poly lathe (kit pieces left out)."""
    local = MeshBuilder()
    wall_meshes(local, tc, port, tile)
    breakwater_meshes(local, tc, port, plan, tile, light=False)
    cluster(local, mb, lod.cluster_port, lod.drop, lod.crease)
    cfg = {**tc.port_cfg["lighthouse"], "segments": lod.segments}
    for x, y, z, scheme in lighthouse_spots(tc, port, tile):
        lighthouse_mesh(mb, cfg, x, y, z, scheme)


# --- vertex clustering -------------------------------------------------------------------------------------

def cluster(src: MeshBuilder, dst: MeshBuilder, cell: float, drop=frozenset(), crease: float = 45.0) -> None:
    """Simplify `src` into `dst` by vertex clustering (Rossignac and Borrel): every vertex moves to the mean of
    the vertices in its `cell` m cube of a world-aligned grid (all materials together, so seams stay closed);
    triangles that collapse go, and of triangles left on the same corners facing the same way only the one
    that was largest stays (no flicker of a window over its wall). Thin sheets (`fine`) and `drop` materials
    go first; normals are smooth within `crease` degrees (`_corner_normals`)."""
    names, pos, tris, mats = [], [], [], []
    base = 0
    for mat, p, t, fine in src.arrays():
        t = t[~fine]
        if mat in drop or not len(t):
            continue
        names.append(mat)
        pos.append(p)
        tris.append(t + base)
        mats.append(np.full(len(t), len(names) - 1))
        base += len(p)
    if not tris:
        return
    p, t, m = np.vstack(pos), np.vstack(tris), np.concatenate(mats)
    _, inv, counts = np.unique(np.floor(p / cell).astype(np.int64), axis=0, return_inverse=True,
                               return_counts=True)
    inv = np.asarray(inv).reshape(-1)
    rep = np.zeros((len(counts), 3))
    np.add.at(rep, inv, p)
    rep /= counts[:, None]
    area0 = np.linalg.norm(np.cross(p[t[:, 1]] - p[t[:, 0]], p[t[:, 2]] - p[t[:, 0]]), axis=1)
    t = inv[t]
    nrm = np.cross(rep[t[:, 1]] - rep[t[:, 0]], rep[t[:, 2]] - rep[t[:, 0]])
    area = np.linalg.norm(nrm, axis=1)
    keep = (t[:, 0] != t[:, 1]) & (t[:, 1] != t[:, 2]) & (t[:, 0] != t[:, 2]) & (area > 1e-4)
    t, m, nrm, area, area0 = t[keep], m[keep], nrm[keep], area[keep], area0[keep]
    first = np.argmin(t, axis=1)
    rot = t[np.arange(len(t))[:, None], (first[:, None] + np.arange(3)) % 3]   # same corners, same turn: same row
    order = np.argsort(-area0, kind="stable")
    _, kept = np.unique(rot[order], axis=0, return_index=True)
    sel = np.sort(order[kept])
    t, m, area = t[sel], m[sel], area[sel]
    corner = _corner_normals(t, nrm[sel] / area[:, None], area, m, np.cos(np.radians(crease)))
    for k, mat in enumerate(names):
        s = np.nonzero(m == k)[0]
        if len(s):
            dst.add(mat, rep[t[s]].reshape(-1, 3), corner[s].reshape(-1, 3), np.zeros((3 * len(s), 2)),
                    np.arange(3 * len(s)).reshape(-1, 3))


def _corner_normals(t: np.ndarray, face: np.ndarray, area: np.ndarray, m: np.ndarray, limit: float) -> np.ndarray:
    """(T, 3, 3) normal of each triangle corner: the area-weighted mean of the unit face normals `face` of the
    triangles of its material round its vertex that turn from its own by less than the crease (cosine
    `limit`). Smooth across gentle bends (rubble, domes), flat across sharp ones (walls, roofs): equal corners
    then share one vertex in the written file, and flat faces still go without NORMAL."""
    v = t.reshape(-1)
    f = np.repeat(np.arange(len(t)), 3)
    order = np.lexsort((v, m[f]))
    vs, fs = v[order], f[order]
    new = np.r_[True, (vs[1:] != vs[:-1]) | (m[fs[1:]] != m[fs[:-1]])]
    group = np.cumsum(new) - 1
    starts = np.nonzero(new)[0]
    size = np.diff(np.r_[starts, len(vs)])[group]               # corners round each corner's vertex
    a = np.repeat(np.arange(len(vs)), size)                     # every pair of corners on one vertex
    b = starts[group[a]] + np.arange(len(a)) - np.repeat(np.cumsum(size) - size, size)
    fa, fb = fs[a], fs[b]
    w = (np.einsum("ij,ij->i", face[fa], face[fb]) >= limit) * area[fb]
    acc = np.zeros((len(vs), 3))
    np.add.at(acc, a, face[fb] * w[:, None])
    out = np.empty((len(v), 3))
    out[order] = acc / np.linalg.norm(acc, axis=1, keepdims=True)
    return out.reshape(-1, 3, 3)


# --- the tile ----------------------------------------------------------------------------------------------

def build_lod(tc: TileContext, i: int, j: int, water: bool) -> MeshBuilder:
    """The lod1 meshes of tile (i, j); `water`: the full tile has its water plane."""
    lod = lod_of(tc)
    x0, y0, x1, y1 = tile_bounds(tc, i, j)
    tile = box(x0, y0, x1, y1)
    mb = MeshBuilder(origin=(x0, y0))
    ground = Terrain(tc, lod, x0, y0)
    ground.draw(mb, lod)
    if water:
        water_mesh(mb, x0, y0, x1, y1)
    strips = road_ribbons(tc, lod, tile)
    for ci, (plan, centers, _trees, street_tree, _dresser) in enumerate(tc.cities):
        port = getattr(plan, "port", None)
        if port is not None and port.zone.intersects(tile):
            harbor_mesh(mb, tc, lod, port, plan, tile)
        if not plan.boundary.intersects(tile):
            continue
        strips += street_ribbons(tc, lod, plan, street_tree, tile)
        lod.cities[ci].draw(mb, tc, lod, centers, x0, y0, x1, y1)
    ribbons(mb, lod, strips, ground.surface)
    return mb


def write_lod(tc: TileContext, i: int, j: int, folder: Path, water: bool) -> dict:
    """Write tile_i_j_lod1.glb next to the full tile; returns its part of the index entry."""
    lod = lod_of(tc)
    mb = build_lod(tc, i, j, water)
    x0, y0, _, _ = tile_bounds(tc, i, j)
    parts = {mat: {**part, "uv": None} for mat, part in mb.gltf_parts().items()}   # flat colors: no UVs
    path = Path(folder) / f"tile_{i}_{j}_lod1.glb"
    part = path.with_name(path.name + ".part")
    size = write_glb(part, parts, lod.materials, translation=(x0, 0.0, -y0), name=f"tile_{i}_{j}_lod1",
                     extras={"i": i, "j": j, "x0": x0, "y0": y0, "lod": 1}, **tc.quantize)
    os.replace(part, path)
    return {"file": path.name, "bytes": size, "triangles": mb.triangles}
