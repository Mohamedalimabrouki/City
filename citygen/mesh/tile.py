"""3D tiles: everything inside one square of the world, written as one .glb file.

A tile holds terrain (colored by biome), water, country roads, and the
streets, buildings and trees of any planned city that reaches into it. Each
building and tree belongs to exactly one tile (the one holding its center),
so tiles can be loaded and unloaded independently without duplicates.
"""
from __future__ import annotations

import math
import os
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from shapely.strtree import STRtree

from ..city.dressing import Dresser, Placement, building_highs, ground_heights
from ..city.geo import frame, lines, polygons
from ..city.ground import STREET_LIFT, Ground
from ..city.roofs import RoofLayout, roof_layout, roof_stream
from ..kit import make_kit
from ..noise import Fractal
from ..terrain import BIOME_MATERIAL, SEA, classify
from .builder import (MeshBuilder, add_cap, add_dome, add_draped_cap, add_hip_roof, add_loft, add_ribbon,
                      add_sheet, add_skirt, add_walls, extrude, rectangle, regular_polygon)
from .gltf import write_glb
from .props import tree_mesh
from .textures import images_for

ROAD_LIFT = 0.34


class TileContext:
    """Spatial indexes over the world and its planned cities, shared by every tile of a build."""

    def __init__(self, world, plans):
        self.world = world
        self.terrain = world.terrain
        self.size = int(world.cfg["tiles"]["size"])
        self.step = float(world.cfg["tiles"]["terrain_step"])
        self.palette = world.style["palette"]
        self.roofs = world.style.get("roofs", {})
        self.plinths = world.style.get("plinth", {})
        self.road_lines = [LineString(r.coords) for r in world.roads]
        self.road_tree = STRtree(self.road_lines) if self.road_lines else None
        self.plans = plans
        self.ground = Ground(world, plans)
        self.city_area = unary_union([p.boundary for p in plans]) if plans else None
        parks = [d.polygon for p in plans for d in p.districts if d.kind == "park"]
        self.park_area = unary_union(parks) if parks else None
        for area in (self.city_area, self.park_area):
            if area is not None:
                shapely.prepare(area)
        # street dressing: doors, shops, goods, street life (city/dressing.py), drawn as instances
        self.dress = bool(world.cfg["tiles"].get("dressing", True))
        self.kit = make_kit(world.seed, world.cfg, world.style) if self.dress else None
        self.materials = self.kit.materials if self.kit else self.palette
        self.texture_mode = str(world.cfg["tiles"].get("textures", "shared"))
        self.texture_images = images_for(world.style, world.seed, self.texture_mode)
        self.tint = GroundTint(world.seed, world.style.get("ground_tint", {}))
        self.cities = []
        self.paint_trees = []
        for p in plans:
            fps = [b.footprint for b in p.buildings]
            centers = shapely.get_coordinates(shapely.centroid(fps)) if fps else np.zeros((0, 2))
            trees = np.array([(t.x, t.y) for t in p.trees]) if p.trees else np.zeros((0, 2))
            street_tree = STRtree([s.line for s in p.streets]) if p.streets else None
            dresser = Dresser(world, p, self.kit, self.ground) if self.dress else None
            self.cities.append((p, centers, trees, street_tree, dresser))
            paint = [m.polygon for m in getattr(p, "paint", ())]
            self.paint_trees.append(STRtree(paint) if paint else None)

    def height(self, x, y):
        return self.ground.height(x, y)


class GroundTint:
    """Large, soft brightness and warm/cool drift over the terrain, against texture repeats from the air.

    A pure function of world x, y (its own noise seeds), so both tiles at a shared edge give the
    same color and no seam shows. Values stay in (0, 1]: glTF multiplies base color x texture x
    COLOR_0, so the tint only darkens a little and cools or warms a little, never goes black.
    """

    def __init__(self, seed: int, cfg: dict):
        self.strength = float(cfg.get("brightness", 0.0))
        self.warmth = float(cfg.get("warmth", 0.0))
        octaves = int(cfg.get("octaves", 3))
        self.light = Fractal(seed, "ground_tint", float(cfg.get("wavelength", 400.0)), octaves)
        self.warm = Fractal(seed, "ground_tint_warmth", float(cfg.get("warm_wavelength", 900.0)), octaves)

    def __call__(self, x, y) -> np.ndarray:
        """(N, 3) linear RGB multipliers for world points x, y."""
        light = 1.0 - self.strength * np.clip(0.5 - self.light(x, y), 0.0, 1.0)
        t = np.clip(0.5 + self.warm(x, y), 0.0, 1.0)            # 1 = warm, 0 = cool
        rgb = np.stack([1.0 - self.warmth * (1.0 - t), np.full_like(t, 1.0 - self.warmth * 0.5),
                        1.0 - self.warmth * t], axis=-1)
        return rgb * light[..., None]


def tile_bounds(tc: TileContext, i: int, j: int) -> tuple:
    t = tc.size
    return i * t, j * t, (i + 1) * t, (j + 1) * t


def terrain_mesh(mb: MeshBuilder, tc: TileContext, x0: float, y0: float, corners: list = ()) -> float:
    """Height-field grid colored by biome (urban ground inside cities). Returns the lowest height.

    `corners`: dressers whose terrain-corner cache gets the grid's heights (doors and garden paths
    on open ground follow the drawn mesh, see Dresser.drawn).
    """
    s = tc.step
    n = int(round(tc.size / s))
    xs = x0 + np.arange(-1, n + 2) * s
    ys = y0 + np.arange(-1, n + 2) * s
    X, Y = np.meshgrid(xs, ys)
    He = tc.height(X, Y)
    for dresser in corners:
        dresser.seed_corners(int(round(xs[0] / s)), int(round(ys[0] / s)), He)
    H = He[1:-1, 1:-1]
    gx = (He[1:-1, 2:] - He[1:-1, :-2]) / (2 * s)
    gy = (He[2:, 1:-1] - He[:-2, 1:-1]) / (2 * s)
    nrm = np.stack([-gx, -gy, np.ones_like(gx)], axis=-1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    Xg, Yg = X[1:-1, 1:-1], Y[1:-1, 1:-1]
    pos = np.stack([Xg, Yg, H], axis=-1).reshape(-1, 3)
    nrm = nrm.reshape(-1, 3)
    uv = np.stack([pos[:, 0], -pos[:, 1]], axis=1)
    col = tc.tint(pos[:, 0], pos[:, 1])
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
        mb.add(str(mat), pos[used], nrm[used], uv[used], remap.reshape(-1, 3), col[used])
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
        line = tc.road_lines[int(k)]
        piece = line.intersection(tile)
        if tc.city_area is not None:
            piece = piece.difference(tc.city_area)
        for seg in lines(piece):
            add_ribbon(mb, shapely.segmentize(seg, 8.0).coords, road.width, tc.height, ROAD_LIFT, "asphalt",
                       line.project(Point(seg.coords[0])))


def street_meshes(mb: MeshBuilder, tc: TileContext, plan, street_tree, tile) -> None:
    if street_tree is None:
        return
    for k in street_tree.query(tile, predicate="intersects"):
        st = plan.streets[int(k)]
        mat = st.surface or "asphalt"
        for seg in lines(st.line.intersection(tile)):
            if seg.length > 0.05:
                add_ribbon(mb, shapely.segmentize(seg, 6.0).coords, st.width, tc.height,
                           STREET_LIFT.get(st.kind, 0.24), mat, st.line.project(Point(seg.coords[0])))


def paint_meshes(mb: MeshBuilder, tc: TileContext, plan, paint_tree, tile) -> None:
    """Painted lines and crossings owned by this tile, a few centimeters above the ribbon."""
    if paint_tree is None:
        return
    cfg = tc.world.style.get("streets", {})
    lift = float(cfg.get("paint_lift", 0.03))
    step = float(cfg.get("paint_step", 6.0))   # same spacing as the ribbon, so a long line never sinks into it
    for k in paint_tree.query(tile, predicate="intersects"):
        mark = plan.paint[int(k)]
        st = plan.streets[mark.street]
        z = STREET_LIFT.get(st.kind, 0.24) + lift
        for poly in polygons(mark.polygon.intersection(tile)):
            if poly.area > 0.005:
                add_draped_cap(mb, shapely.segmentize(poly, step), lambda x, y, z=z: tc.height(x, y) + z, "road_paint")


def walk_meshes(mb: MeshBuilder, tc: TileContext, plan, tile, street_tree=None) -> None:
    """Raised sidewalks and promenades owned by this tile (the tile holding their centroid).

    With `street_tree` (an STRtree over the street lines) each sidewalk triangle's paving runs
    along its nearest street: one walk piece wraps a block corner, so one direction would not do.
    """
    x0, y0, x1, y1 = tile.bounds
    step = float(tc.world.style.get("streets", {}).get("walk_step", 15.0))
    along = None if street_tree is None else (lambda x, y: street_directions(street_tree, x, y))
    for walk in getattr(plan, "walks", ()):
        c = walk.polygon.centroid
        if not (x0 <= c.x < x1 and y0 <= c.y < y1):
            continue
        poly = shapely.segmentize(orient(walk.polygon, sign=1.0), step)   # long blocks follow the ground
        add_draped_cap(mb, poly, tc.ground.walk_top, "sidewalk", along)
        for ring in (poly.exterior, *poly.interiors):
            pts = np.asarray(ring.coords)[:-1]
            top = tc.ground.walk_top(pts[:, 0], pts[:, 1])
            bottom = tc.height(pts[:, 0], pts[:, 1])
            add_skirt(mb, pts, top, bottom, "curb")


def path_meshes(mb: MeshBuilder, tc: TileContext, paths: list, drawn) -> None:
    """Paved paths from doors on open ground to the street, drawn by the tile owning their building,
    draped on the terrain mesh (`drawn`: `Ground.drawn` or the dresser's cached copy)."""
    cfg = tc.world.style.get("dressing", {}).get("paths", {})
    width, lift = float(cfg.get("width", 1.4)), float(cfg.get("lift", 0.04))
    for line in paths:
        add_ribbon(mb, line, width, drawn, lift, str(cfg.get("material", "sidewalk")))


def street_directions(street_tree, x, y) -> np.ndarray:
    """(N, 2) unit direction of the nearest street line at each point (x east when undefined)."""
    pts = shapely.points(np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64))
    lines_ = street_tree.geometries[street_tree.nearest(pts)]
    d = shapely.line_locate_point(lines_, pts)
    length = shapely.length(lines_)
    a = shapely.get_coordinates(shapely.line_interpolate_point(lines_, np.maximum(d - 1.0, 0.0)))
    b = shapely.get_coordinates(shapely.line_interpolate_point(lines_, np.minimum(d + 1.0, length)))
    v = b - a
    n = np.hypot(v[:, 0], v[:, 1])
    return np.where(n[:, None] > 1e-9, v / np.maximum(n, 1e-9)[:, None], [1.0, 0.0])


PLINTH_KINDS = frozenset({"house", "domed", "apartments", "villa", "shed", "mosque_hall", "marabout"})


def building_mesh(mb: MeshBuilder, b, height_fn, roof: RoofLayout | None = None,
                  plinth: tuple[str, float] | None = None, frontage=None) -> None:
    fp = orient(b.footprint, sign=1.0)
    ring = np.asarray(fp.exterior.coords)
    ground = height_fn(ring[:, 0], ring[:, 1])
    low, high = float(ground.min()), float(ground.max())
    z0, z1 = low - 0.6, high + b.height
    if b.roof_shape == "hip":
        extrude(mb, fp, z0, z1, b.wall, None, z_ref=high, plinth=plinth, frontage=frontage)
        cx, cy, length, width, angle = frame(fp)
        corners = np.asarray(rectangle(cx, cy, length, width, angle).exterior.coords)[:4]
        add_hip_roof(mb, corners, z1, 0.32 * width, b.roof)
    else:
        parapet = roof is not None and roof.band is not None
        z_top = z1 + roof.height if parapet else z1
        extrude(mb, fp, z0, z_top, b.wall, None if parapet else b.roof, z_ref=high,
                plinth=plinth, frontage=frontage)
        roof_mesh(mb, b, roof, z1)
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


CLOTHS = ("cloth_1", "cloth_2", "cloth_3", "cloth_4", "cloth_5", "cloth_6")
FLAGS = ("awning_red", "awning_yellow", "awning_green", "awning_blue", "awning_cream")


def _quad(mb: MeshBuilder, a, b, c, d, mat: str) -> None:
    pos = np.array([a, b, c, d], dtype=np.float64)
    n = np.cross(pos[1] - pos[0], pos[3] - pos[0])
    n = n / max(np.linalg.norm(n), 1e-9)
    mb.add(mat, pos, np.tile(n, (4, 1)), np.zeros((4, 2)), [[0, 1, 2], [0, 2, 3]])


def roof_mesh(mb: MeshBuilder, b, layout: RoofLayout | None, z: float) -> None:
    """The parapet coping, the stair room and the roof deck of a flat roof (deck at z)."""
    if layout is None or layout.band is None:
        return
    for poly in polygons(layout.inner):
        add_cap(mb, poly, z, b.roof)                       # the deck inside the parapet
    z_top = z + layout.height
    for band in polygons(layout.band):
        _coping(mb, b, band, z, z_top)
    if layout.stair is None:
        return
    extrude(mb, layout.stair, z, z + layout.stair_height, b.wall, b.roof, z_ref=z)
    x, y, yaw = layout.door
    half = layout.door_width / 2
    t = np.array([-math.sin(yaw), math.cos(yaw)])       # along the stair room wall
    c = np.array([x, y]) + np.array([math.cos(yaw), math.sin(yaw)]) * 0.02
    h = layout.door_height
    _quad(mb, (c[0] - t[0] * half, c[1] - t[1] * half, z + 0.02),
          (c[0] + t[0] * half, c[1] + t[1] * half, z + 0.02),
          (c[0] + t[0] * half, c[1] + t[1] * half, z + h),
          (c[0] - t[0] * half, c[1] - t[1] * half, z + h), "wood")


def _coping(mb: MeshBuilder, b, band, z: float, z_top: float) -> None:
    """The sloped top of one parapet band: from its outer ring at z_top down to its inner ring at z.

    The outer face of the parapet is the building wall itself, drawn up to z_top, so only this
    coping strip is new geometry: 2 triangles per edge, which keeps a dense old town affordable.
    """
    band = orient(band, sign=1.0)
    outer = np.asarray(band.exterior.coords)[:, :2]
    holes = [np.asarray(h.coords)[:, :2] for h in band.interiors]
    outer = outer[:-1] if len(outer) > 1 and np.allclose(outer[0], outer[-1]) else outer
    holes = [h[:-1] if len(h) > 1 and np.allclose(h[0], h[-1]) else h for h in holes]
    if len(holes) != 1 or len(holes[0]) != len(outer):
        add_cap(mb, band, z_top, b.roof)                 # rare outline the offset could not pair
        for hole in band.interiors:
            add_walls(mb, hole.coords[::-1], z, z_top, b.wall, z)
        return
    inner = holes[0][::-1]                               # same direction as the counter-clockwise outer ring
    k = int(np.argmin(((inner - outer[0]) ** 2).sum(axis=1)))
    add_loft(mb, np.roll(inner, -k, axis=0), z, outer, z_top, b.roof)


def span_mesh(mb: MeshBuilder, span, placements: list) -> None:
    """A sagging line between two walls, with laundry, flags or lanterns hanging from it."""
    a, b = np.array(span.a, dtype=float), np.array(span.b, dtype=float)
    d = b - a
    length = float(np.linalg.norm(d))
    if length < 0.5:
        return
    sag = 0.12 + 0.025 * length

    def at(dist: float) -> np.ndarray:
        t = dist / length
        p = a + d * t
        p[2] -= sag * 4 * t * (1 - t)
        return p

    pts = [at(t * length) for t in np.linspace(0.0, 1.0, 9)]
    mat, w = ("iron", 0.012) if span.kind == "cable" else ("rope", 0.016)
    side = np.cross(d, [0.0, 0.0, 1.0])
    side = side / max(np.linalg.norm(side), 1e-9) * w
    up = np.array([0.0, 0.0, w])
    for p0, p1 in zip(pts[:-1], pts[1:]):
        _quad(mb, p0 - side, p1 - side, p1 + side, p0 + side, mat)
        _quad(mb, p0 - up, p1 - up, p1 + up, p0 + up, mat)
    rng = np.random.default_rng(span.seed)
    drop = np.array([0.0, 0.0, 1.0])
    s = 0.4
    if span.kind == "laundry":
        while s < length - 0.5:
            cw, ch = rng.uniform(0.35, 0.75), rng.uniform(0.45, 0.95)
            if s + cw > length - 0.3:
                break
            p0, p1 = at(s), at(s + cw)
            p2, p3 = p1 - drop * ch, p0 - drop * ch
            add_sheet(mb, [[p0, p1, p2], [p0, p2, p3]], CLOTHS[int(rng.integers(len(CLOTHS)))])
            s += cw + rng.uniform(0.15, 0.6)
    elif span.kind == "bunting":
        k = 0
        while s < length - 0.4:
            p0, p1 = at(s), at(s + 0.3)
            add_sheet(mb, [[p0, p1, (p0 + p1) / 2 - drop * 0.34]], FLAGS[k % len(FLAGS)], 0.005)
            s += 0.42
            k += 1
    elif span.kind == "lanterns":
        s = 0.8
        yaw = math.atan2(d[1], d[0])
        while s < length - 0.5:
            p = at(s)
            placements.append(Placement(span.piece or "string_lantern", p[0], p[1], p[2], yaw, on_ground=False))
            s += span.step


def sabat_mesh(mb: MeshBuilder, span) -> None:
    """A sabat: a room built across an alley from wall to wall, the alley running under it."""
    a, b = np.array(span.a[:2], dtype=float), np.array(span.b[:2], dtype=float)
    across = b - a
    gap = float(np.hypot(*across))
    if gap < 0.5:
        return
    w = across / gap
    a, b = a - w * 0.3, b + w * 0.3   # sink the ends into both walls
    along = np.array([-w[1], w[0]]) * 1.7
    floor, top = span.a[2], span.top
    outline = Polygon([a - along, b - along, b + along, a + along])
    extrude(mb, outline, floor, top, "lime_white", "roof_white")
    add_cap(mb, outline, floor, "lime_white", up=False)
    for sgn in (-1.0, 1.0):   # a beam under each edge and a small window on each face
        edge = along * sgn
        beam = Polygon([a + edge * 0.92, b + edge * 0.92, b + edge * 1.04, a + edge * 1.04])
        extrude(mb, beam, floor - 0.18, floor, "wood", "wood")
        mid = (a + b) / 2 + edge * 1.005
        z0, z1 = floor + 0.9, min(floor + 1.9, top - 0.3)
        if z1 - z0 > 0.4:
            half = w * min(0.45, gap * 0.2)
            _quad(mb, (*(mid - half), z0), (*(mid + half), z0), (*(mid + half), z1), (*(mid - half), z1), "glass_dark")


def street_frontage(ring, plan, walk_width: np.ndarray, street_tree, reach: float) -> np.ndarray:
    """One bool per exterior wall segment: True where the wall faces a street or its sidewalk.

    Party walls and block interiors stay plain, so the plinth costs bytes only where it can be
    seen. Distances are measured from the wall midpoint to the street center line, allowing for
    half the street plus the raised sidewalk on that street.
    """
    pts = np.asarray(ring, dtype=np.float64)[:, :2]
    if len(pts) > 1 and np.allclose(pts[0], pts[-1]):
        pts = pts[:-1]
    if len(pts) < 2 or street_tree is None:
        return np.zeros(max(len(pts), 0), dtype=bool)
    a, b = pts, np.roll(pts, -1, axis=0)
    mids = (a + b) / 2.0
    lo, hi = mids.min(axis=0) - reach, mids.max(axis=0) + reach
    mask = np.zeros(len(a), dtype=bool)
    for k in street_tree.query(box(lo[0], lo[1], hi[0], hi[1])):
        street = plan.streets[int(k)]
        gap = street.width / 2.0 + walk_width[int(k)] + 0.6
        mask |= shapely.distance(street.line, shapely.points(mids)) <= gap
    return mask


def build_tile(tc: TileContext, i: int, j: int) -> tuple:
    """Meshes of one tile, plus the dressing placements to draw as instances."""
    x0, y0, x1, y1 = tile_bounds(tc, i, j)
    tile = box(x0, y0, x1, y1)
    mb = MeshBuilder(origin=(x0, y0))
    dressers = [c[4] for c in tc.cities if c[4] is not None and c[0].boundary.intersects(tile)]
    if terrain_mesh(mb, tc, x0, y0, dressers) < 0.0:
        water_mesh(mb, x0, y0, x1, y1)
    road_meshes(mb, tc, tile)
    placements: list = []
    spans: list = []
    for ci, (plan, centers, trees, street_tree, dresser) in enumerate(tc.cities):
        if not plan.boundary.intersects(tile):
            continue
        street_meshes(mb, tc, plan, street_tree, tile)
        paint_meshes(mb, tc, plan, tc.paint_trees[ci], tile)
        walk_meshes(mb, tc, plan, tile, street_tree)
        walk_width = np.zeros(len(plan.streets))
        for walk in getattr(plan, "walks", ()):
            if walk.kind == "sidewalk" and 0 <= walk.street < len(walk_width):
                walk_width[walk.street] = max(walk_width[walk.street], float(walk.width))
        reach = 0.6 + max((s.width / 2.0 + walk_width[k] for k, s in enumerate(plan.streets)),
                          default=0.0)
        inside = (centers[:, 0] >= x0) & (centers[:, 0] < x1) & (centers[:, 1] >= y0) & (centers[:, 1] < y1)
        owned = np.nonzero(inside)[0]
        for k in owned:
            b = plan.buildings[int(k)]
            kind = plan.districts[b.district].kind
            plinth = frontage = None
            if b.kind in PLINTH_KINDS and kind in tc.plinths:
                spec = tc.plinths[kind]
                plinth = (str(spec["material"]), float(spec["height"]))
                fp = orient(b.footprint, sign=1.0)
                frontage = street_frontage(fp.exterior.coords, plan, walk_width, street_tree, reach)
            roof = roof_layout(b, kind,
                               roof_stream(tc.world.seed, plan.settlement.id, int(k)), tc.roofs)
            building_mesh(mb, b, tc.height, roof, plinth, frontage)
        if dresser is not None:
            highs = building_highs(tc.ground, [plan.buildings[int(k)] for k in owned])
            paths: list = []
            for k, high in zip(owned, highs):
                placements += dresser.building(int(k), float(high), paths)
            path_meshes(mb, tc, paths, dresser.drawn)
            if street_tree is not None:
                for k in street_tree.query(tile, predicate="intersects"):
                    spans += dresser.spans(int(k), tile)
                    placements += dresser.street_props(int(k), tile)
        if len(trees):
            inside = (trees[:, 0] >= x0) & (trees[:, 0] < x1) & (trees[:, 1] >= y0) & (trees[:, 1] < y1)
            ks = np.nonzero(inside)[0]
            if len(ks):
                zs = tc.ground.surface(trees[ks, 0], trees[ks, 1])
                for k, z in zip(ks, zs):
                    kit_tree = dresser.tree(int(k), plan.trees[int(k)], float(z)) if dresser is not None else None
                    if kit_tree is not None:
                        placements.append(kit_tree)
                    else:
                        tree_mesh(mb, plan.trees[int(k)], float(z))
    ground_heights(tc.ground, placements)
    for span in spans:
        if span.kind == "sabat":
            sabat_mesh(mb, span)
        else:
            span_mesh(mb, span, placements)
    return mb, placements


def instance_groups(tc: TileContext, placements: list, x0: float, y0: float) -> list:
    """Placements grouped by piece, as glTF instance transforms local to the tile."""
    groups: dict = {}
    for p in placements:
        if tc.kit is not None and p.piece in tc.kit.pieces:
            groups.setdefault(p.piece, []).append(p)
    out = []
    for name, ps in sorted(groups.items()):
        t = np.array([(p.x - x0, p.z, -(p.y - y0)) for p in ps])
        half = np.array([p.yaw for p in ps]) / 2.0
        zero = np.zeros(len(ps))
        r = np.stack([zero, np.sin(half), zero, np.cos(half)], axis=1)
        sc = np.repeat(np.array([p.scale for p in ps])[:, None], 3, axis=1)
        out.append({"name": name, "parts": tc.kit.pieces[name].parts, "t": t, "r": r, "s": sc})
    return out


def texture_files(tc: TileContext, parts: dict, instances: list) -> list[str]:
    """Shared texture files one tile uses; the resume check (build.py) waits for them too."""
    if tc.texture_mode != "shared":
        return []
    names = set(parts)
    for inst in instances:
        names.update(inst["parts"])
    files = set()
    for name in names:
        texture = tc.materials.get(name, {}).get("texture")
        if texture and texture in tc.texture_images:
            files.add(tc.texture_images[texture]["uri"])
    return sorted(files)


def export_tile(tc: TileContext, i: int, j: int, folder: Path) -> dict:
    mb, placements = build_tile(tc, i, j)
    x0, y0, _, _ = tile_bounds(tc, i, j)
    instances = instance_groups(tc, placements, x0, y0)
    parts = mb.gltf_parts()
    path = Path(folder) / f"tile_{i}_{j}.glb"
    part = path.with_name(path.name + ".part")   # renamed at the end: a half-written tile never counts as done
    size = write_glb(part, parts, tc.materials, translation=(x0, 0.0, -y0),
                     name=f"tile_{i}_{j}", extras={"i": i, "j": j, "x0": x0, "y0": y0}, instances=instances,
                     images=tc.texture_images)
    os.replace(part, path)
    unique = mb.triangles + sum(tc.kit.pieces[g["name"]].triangles for g in instances)
    drawn = mb.triangles + sum(len(g["t"]) * tc.kit.pieces[g["name"]].triangles for g in instances)
    entry = {"i": i, "j": j, "file": path.name, "x0": x0, "y0": y0, "triangles": unique,
             "drawn": drawn, "pieces": sum(len(g["t"]) for g in instances), "bytes": size}
    files = texture_files(tc, parts, instances)
    if files:
        entry["files"] = files
    return entry
