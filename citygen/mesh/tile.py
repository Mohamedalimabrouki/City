"""3D tiles: everything inside one square of the world, written as one .glb file.

A tile holds terrain (colored by biome), water, country roads, and the
streets, buildings and trees of any planned city that reaches into it. Each
building and tree belongs to exactly one tile (the one holding its center),
so tiles can be loaded and unloaded independently without duplicates.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import LineString, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from shapely.strtree import STRtree

from ..city.geo import frame, lines
from ..terrain import BIOME_MATERIAL, SEA, classify
from .builder import (MeshBuilder, add_cone, add_dome, add_hip_roof, add_octahedron, add_ribbon,
                      add_triangles, extrude, rectangle, regular_polygon)
from .gltf import write_glb

STREET_LIFT = {"boulevard": 0.32, "arterial": 0.3, "ring": 0.3, "corniche": 0.3, "connector": 0.28,
               "street": 0.24, "souk": 0.2, "alley": 0.18}
ROAD_LIFT = 0.34


class TileContext:
    """Spatial indexes over the world and its planned cities, shared by every tile of a build."""

    def __init__(self, world, plans):
        self.world = world
        self.terrain = world.terrain
        self.size = int(world.cfg["tiles"]["size"])
        self.step = float(world.cfg["tiles"]["terrain_step"])
        self.palette = world.style["palette"]
        self.road_lines = [LineString(r.coords) for r in world.roads]
        self.road_tree = STRtree(self.road_lines) if self.road_lines else None
        self.plans = plans
        self.city_area = unary_union([p.boundary for p in plans]) if plans else None
        parks = [d.polygon for p in plans for d in p.districts if d.kind == "park"]
        self.park_area = unary_union(parks) if parks else None
        for area in (self.city_area, self.park_area):
            if area is not None:
                shapely.prepare(area)
        self.cities = []
        for p in plans:
            fps = [b.footprint for b in p.buildings]
            centers = shapely.get_coordinates(shapely.centroid(fps)) if fps else np.zeros((0, 2))
            trees = np.array([(t.x, t.y) for t in p.trees]) if p.trees else np.zeros((0, 2))
            street_tree = STRtree([s.line for s in p.streets]) if p.streets else None
            self.cities.append((p, centers, trees, street_tree))

    def height(self, x, y):
        return self.terrain.height(x, y)


def tile_bounds(tc: TileContext, i: int, j: int) -> tuple:
    t = tc.size
    return i * t, j * t, (i + 1) * t, (j + 1) * t


def terrain_mesh(mb: MeshBuilder, tc: TileContext, x0: float, y0: float) -> float:
    """Height-field grid colored by biome (urban ground inside cities). Returns the lowest height."""
    s = tc.step
    n = int(round(tc.size / s))
    xs = x0 + np.arange(-1, n + 2) * s
    ys = y0 + np.arange(-1, n + 2) * s
    X, Y = np.meshgrid(xs, ys)
    He = tc.height(X, Y)
    H = He[1:-1, 1:-1]
    gx = (He[1:-1, 2:] - He[1:-1, :-2]) / (2 * s)
    gy = (He[2:, 1:-1] - He[:-2, 1:-1]) / (2 * s)
    nrm = np.stack([-gx, -gy, np.ones_like(gx)], axis=-1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    Xg, Yg = X[1:-1, 1:-1], Y[1:-1, 1:-1]
    pos = np.stack([Xg, Yg, H], axis=-1).reshape(-1, 3)
    nrm = nrm.reshape(-1, 3)
    uv = np.stack([pos[:, 0], -pos[:, 1]], axis=1)
    hc = (H[:-1, :-1] + H[1:, :-1] + H[:-1, 1:] + H[1:, 1:]) / 4
    xc, yc = Xg[:-1, :-1] + s / 2, Yg[:-1, :-1] + s / 2
    slope = np.hypot((gx[:-1, :-1] + gx[1:, 1:]) / 2, (gy[:-1, :-1] + gy[1:, 1:]) / 2)
    biome = classify(hc, slope, tc.terrain.moisture(xc, yc, hc))
    names = np.array(BIOME_MATERIAL, dtype=object)[biome]
    names[biome == SEA] = "beach"
    if tc.city_area is not None:
        urban = shapely.contains_xy(tc.city_area, xc, yc) & (biome != SEA)
        names[urban] = "urban_ground"
        if tc.park_area is not None:
            names[urban & shapely.contains_xy(tc.park_area, xc, yc)] = "grass"
    cols = n + 1
    iy, ix = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    v00 = iy * cols + ix
    quads = np.stack([v00, v00 + 1, v00 + cols + 1, v00 + cols], axis=-1)
    for mat in np.unique(names):
        q = quads[names == mat]
        tris = np.concatenate([q[:, [0, 1, 2]], q[:, [0, 2, 3]]])
        used, remap = np.unique(tris, return_inverse=True)
        mb.add(str(mat), pos[used], nrm[used], uv[used], remap.reshape(-1, 3))
    return float(H.min())


def water_mesh(mb: MeshBuilder, x0, y0, x1, y1) -> None:
    pos = np.array([[x0, y0, 0.0], [x1, y0, 0.0], [x1, y1, 0.0], [x0, y1, 0.0]])
    uv = np.stack([pos[:, 0], -pos[:, 1]], axis=1)
    mb.add("water", pos, np.tile([0.0, 0.0, 1.0], (4, 1)), uv, [[0, 1, 2], [0, 2, 3]])


def road_meshes(mb: MeshBuilder, tc: TileContext, tile) -> None:
    if tc.road_tree is None:
        return
    for k in tc.road_tree.query(tile, predicate="intersects"):
        road = tc.world.roads[int(k)]
        piece = tc.road_lines[int(k)].intersection(tile)
        if tc.city_area is not None:
            piece = piece.difference(tc.city_area)
        for seg in lines(piece):
            add_ribbon(mb, shapely.segmentize(seg, 8.0).coords, road.width, tc.height, ROAD_LIFT, "asphalt")


def street_meshes(mb: MeshBuilder, tc: TileContext, plan, street_tree, tile) -> None:
    if street_tree is None:
        return
    for k in street_tree.query(tile, predicate="intersects"):
        st = plan.streets[int(k)]
        mat = "paving" if st.kind in ("souk", "alley") else "asphalt"
        for seg in lines(st.line.intersection(tile)):
            if seg.length > 0.05:
                add_ribbon(mb, shapely.segmentize(seg, 6.0).coords, st.width, tc.height,
                           STREET_LIFT.get(st.kind, 0.24), mat)


def building_mesh(mb: MeshBuilder, b, height_fn) -> None:
    fp = orient(b.footprint, sign=1.0)
    ring = np.asarray(fp.exterior.coords)
    ground = height_fn(ring[:, 0], ring[:, 1])
    low, high = float(ground.min()), float(ground.max())
    z0, z1 = low - 0.6, high + b.height
    if b.roof_shape == "hip":
        extrude(mb, fp, z0, z1, b.wall, None, z_ref=high)
        cx, cy, length, width, angle = frame(fp)
        corners = np.asarray(rectangle(cx, cy, length, width, angle).exterior.coords)[:4]
        add_hip_roof(mb, corners, z1, 0.32 * width, b.roof)
    else:
        extrude(mb, fp, z0, z1, b.wall, b.roof, z_ref=high)
    for x, y, r, mat in b.domes:
        extrude(mb, regular_polygon(x, y, r, 12), z1, z1 + 0.18 * r, b.wall, None, z_ref=high)
        add_dome(mb, x, y, z1 + 0.18 * r, r, mat)
    if b.top:
        cx, cy, _, _, angle = frame(fp)
        side, h = b.top["side"], b.top["height"]
        extrude(mb, rectangle(cx, cy, side * 1.35, side * 1.35, angle), z1, z1 + 0.6,
                b.top["material"], b.top["material"], z_ref=high)
        extrude(mb, rectangle(cx, cy, side, side, angle), z1 + 0.6, z1 + h, b.top["material"],
                b.top["material"], z_ref=high)
        add_dome(mb, cx, cy, z1 + h, side * 0.5, b.top["cap"], height=side * 0.62)


def tree_mesh(mb: MeshBuilder, t, z: float) -> None:
    h = t.height
    if t.kind == "palm":
        extrude(mb, regular_polygon(t.x, t.y, 0.22, 5), z - 0.3, z + h, "trunk", "trunk")
        top = np.array([t.x, t.y, z + h])
        tris = []
        for k in range(7):
            a = k * 2 * math.pi / 7 + 0.4
            d = np.array([math.cos(a), math.sin(a), 0.0])
            side = np.array([-d[1], d[0], 0.0]) * 0.55
            mid = top + d * 1.6 + np.array([0.0, 0.0, 0.35])
            tip = top + d * 3.4 + np.array([0.0, 0.0, -1.5])
            tris += [[top, mid - side, tip], [top, tip, mid + side]]
        add_triangles(mb, tris, "leaf_palm")
    elif t.kind == "cypress":
        add_cone(mb, t.x, t.y, z - 0.2, 1.1, h, "leaf_cypress", segments=6)
    else:
        trunk = 0.3 * h if t.kind == "broadleaf" else 0.25 * h
        extrude(mb, regular_polygon(t.x, t.y, 0.18, 4), z - 0.3, z + trunk + 0.4, "trunk", None)
        rx = 0.34 * h if t.kind == "broadleaf" else 0.42 * h
        mat = "leaf" if t.kind == "broadleaf" else "leaf_olive"
        add_octahedron(mb, t.x, t.y, z + trunk + 0.3 * h, rx, 0.36 * h, mat, twist=(t.x * 7.3) % 1.57)


def build_tile(tc: TileContext, i: int, j: int) -> MeshBuilder:
    x0, y0, x1, y1 = tile_bounds(tc, i, j)
    tile = box(x0, y0, x1, y1)
    mb = MeshBuilder(origin=(x0, y0))
    if terrain_mesh(mb, tc, x0, y0) < 0.0:
        water_mesh(mb, x0, y0, x1, y1)
    road_meshes(mb, tc, tile)
    for plan, centers, trees, street_tree in tc.cities:
        if not plan.boundary.intersects(tile):
            continue
        street_meshes(mb, tc, plan, street_tree, tile)
        inside = (centers[:, 0] >= x0) & (centers[:, 0] < x1) & (centers[:, 1] >= y0) & (centers[:, 1] < y1)
        for k in np.nonzero(inside)[0]:
            building_mesh(mb, plan.buildings[int(k)], tc.height)
        if len(trees):
            inside = (trees[:, 0] >= x0) & (trees[:, 0] < x1) & (trees[:, 1] >= y0) & (trees[:, 1] < y1)
            ks = np.nonzero(inside)[0]
            if len(ks):
                zs = tc.height(trees[ks, 0], trees[ks, 1])
                for k, z in zip(ks, zs):
                    tree_mesh(mb, plan.trees[int(k)], float(z))
    return mb


def export_tile(tc: TileContext, i: int, j: int, folder: Path) -> dict:
    mb = build_tile(tc, i, j)
    x0, y0, _, _ = tile_bounds(tc, i, j)
    path = Path(folder) / f"tile_{i}_{j}.glb"
    size = write_glb(path, mb.gltf_parts(), tc.palette, translation=(x0, 0.0, -y0),
                     name=f"tile_{i}_{j}", extras={"i": i, "j": j, "x0": x0, "y0": y0})
    return {"i": i, "j": j, "file": path.name, "x0": x0, "y0": y0,
            "triangles": mb.triangles, "bytes": size}
