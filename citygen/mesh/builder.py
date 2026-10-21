"""Mesh building blocks.

Everything here works in generator axes: x = east, y = north, z = up, in
meters. A MeshBuilder collects triangles per material, relative to a tile
origin, and converts to glTF axes (+Y up, -Z north) only on export.

UVs are in meters (1 UV unit = 1 m), so a tiling texture with a known size in
meters can be applied in Blender or a game engine without unwrapping.
"""
from __future__ import annotations

import math

import numpy as np
import shapely
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient

_QUAD = np.array([[0, 1, 2], [0, 2, 3]])


class MeshBuilder:
    def __init__(self, origin=(0.0, 0.0)):
        self.origin = np.array([origin[0], origin[1], 0.0])
        self._parts: dict[str, list] = {}

    def add(self, material: str, pos, nrm, uv, tris) -> None:
        pos = np.asarray(pos, dtype=np.float64).reshape(-1, 3)
        if len(pos) == 0:
            return
        part = self._parts.setdefault(material, [[], [], [], [], 0])
        part[0].append(pos - self.origin)
        part[1].append(np.asarray(nrm, dtype=np.float64).reshape(-1, 3))
        part[2].append(np.asarray(uv, dtype=np.float64).reshape(-1, 2))
        part[3].append(np.asarray(tris, dtype=np.int64).reshape(-1, 3) + part[4])
        part[4] += len(pos)

    @property
    def triangles(self) -> int:
        return sum(sum(len(t) for t in part[3]) for part in self._parts.values())

    def gltf_parts(self) -> dict:
        out = {}
        for mat, (pos, nrm, uv, tris, _count) in self._parts.items():
            pos = np.concatenate(pos)
            nrm = np.concatenate(nrm)
            out[mat] = {"pos": _to_gltf(pos), "nrm": _to_gltf(nrm),
                        "uv": np.concatenate(uv), "idx": np.concatenate(tris).reshape(-1)}
        return out


def _to_gltf(v: np.ndarray) -> np.ndarray:
    # generator (east, north, up) -> glTF (east, up, south)
    return np.stack([v[:, 0], v[:, 2], -v[:, 1]], axis=1)


# --- polygons ---------------------------------------------------------------

def triangulate(poly: Polygon) -> np.ndarray:
    """Constrained triangulation of a polygon (holes allowed). Returns (T, 3, 2), counter-clockwise."""
    try:
        parts = shapely.get_parts(shapely.constrained_delaunay_triangles(poly))
    except shapely.errors.GEOSException:
        return np.zeros((0, 3, 2))
    if len(parts) == 0:
        return np.zeros((0, 3, 2))
    tri = shapely.get_coordinates(parts).reshape(len(parts), 4, 2)[:, :3].copy()
    a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
    cross = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])
    flip = cross < 0
    tri[flip, 1], tri[flip, 2] = c[flip], b[flip]
    return tri[np.abs(cross) > 1e-9]


def add_walls(mb: MeshBuilder, ring, z0: float, z1: float, material: str, z_ref: float) -> None:
    """Vertical walls along a ring. Exterior rings must be CCW and holes CW (see shapely orient)."""
    pts = np.asarray(ring, dtype=np.float64)[:, :2]
    if len(pts) > 1 and np.allclose(pts[0], pts[-1]):
        pts = pts[:-1]
    if len(pts) < 2:
        return
    a, b = pts, np.roll(pts, -1, axis=0)
    d = b - a
    length = np.hypot(d[:, 0], d[:, 1])
    keep = length > 1e-6
    a, b, d, length = a[keep], b[keep], d[keep], length[keep]
    k = len(a)
    s1 = np.cumsum(length)
    s0 = s1 - length
    pos = np.empty((k, 4, 3))
    pos[:, 0, :2], pos[:, 1, :2], pos[:, 2, :2], pos[:, 3, :2] = a, b, b, a
    pos[:, :2, 2], pos[:, 2:, 2] = z0, z1
    nrm = np.zeros((k, 4, 3))
    nrm[:, :, 0] = (d[:, 1] / length)[:, None]
    nrm[:, :, 1] = (-d[:, 0] / length)[:, None]
    uv = np.empty((k, 4, 2))
    uv[:, 0, 0], uv[:, 1, 0], uv[:, 2, 0], uv[:, 3, 0] = s0, s1, s1, s0
    uv[:, :2, 1], uv[:, 2:, 1] = -(z0 - z_ref), -(z1 - z_ref)
    tris = (np.arange(k) * 4)[:, None, None] + _QUAD[None]
    mb.add(material, pos.reshape(-1, 3), nrm.reshape(-1, 3), uv.reshape(-1, 2), tris)


def add_cap(mb: MeshBuilder, poly: Polygon, z: float, material: str, up: bool = True) -> None:
    """Flat horizontal surface facing up (or down, for the underside of something)."""
    tri = triangulate(poly)
    if len(tri) == 0:
        return
    pos = np.concatenate([tri, np.full((len(tri), 3, 1), z)], axis=2).reshape(-1, 3)
    nrm = np.tile([0.0, 0.0, 1.0 if up else -1.0], (len(pos), 1))
    uv = np.stack([pos[:, 0], -pos[:, 1]], axis=1)
    idx = np.arange(len(pos)).reshape(-1, 3)
    mb.add(material, pos, nrm, uv, idx if up else idx[:, ::-1])


def extrude(mb: MeshBuilder, poly: Polygon, z0: float, z1: float, wall: str, roof: str | None,
            z_ref: float | None = None) -> None:
    """Solid prism: walls for every ring plus a flat roof (skip the roof with roof=None)."""
    poly = orient(poly, sign=1.0)
    z_ref = z0 if z_ref is None else z_ref
    add_walls(mb, poly.exterior.coords, z0, z1, wall, z_ref)
    for hole in poly.interiors:
        add_walls(mb, hole.coords, z0, z1, wall, z_ref)
    if roof:
        add_cap(mb, poly, z1, roof)


def add_triangles(mb: MeshBuilder, tris, material: str) -> None:
    """Flat-shaded triangles, (T, 3, 3) counter-clockwise when seen from outside."""
    tris = np.asarray(tris, dtype=np.float64).reshape(-1, 3, 3)
    if len(tris) == 0:
        return
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    norm = np.linalg.norm(n, axis=1)
    ok = norm > 1e-12
    tris, n = tris[ok], n[ok] / norm[ok, None]
    pos = tris.reshape(-1, 3)
    nrm = np.repeat(n, 3, axis=0)
    uv = np.stack([pos[:, 0] + pos[:, 1], -pos[:, 2]], axis=1)
    mb.add(material, pos, nrm, uv, np.arange(len(pos)).reshape(-1, 3))


def add_sheet(mb: MeshBuilder, tris, material: str, thickness: float = 0.01) -> None:
    """Thin cloth or canvas seen from both sides: each triangle plus a reversed twin just behind it.

    Real faces on both sides render the same everywhere; a double-sided material alone shows a
    black underside in some renderers.
    """
    tris = np.asarray(tris, dtype=np.float64).reshape(-1, 3, 3)
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]
    add_triangles(mb, tris, material)
    add_triangles(mb, tris[:, ::-1] - n[:, None, :] * thickness, material)


# --- roofs and details ------------------------------------------------------

def add_dome(mb: MeshBuilder, cx: float, cy: float, z: float, radius: float, material: str,
             height: float | None = None, segments: int = 12, rings: int = 4) -> None:
    """Smooth half-ellipsoid sitting on z."""
    h = radius if height is None else height
    phi = np.linspace(0.0, math.pi / 2, rings + 1)[:, None]
    theta = np.linspace(0.0, 2 * math.pi, segments + 1)[None, :]
    cp, sp, ct, st = np.cos(phi), np.sin(phi), np.cos(theta), np.sin(theta)
    pos = np.stack(np.broadcast_arrays(cx + radius * cp * ct, cy + radius * cp * st, z + h * sp), axis=-1)
    nrm = np.stack(np.broadcast_arrays(cp * ct / radius, cp * st / radius, sp / h), axis=-1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    uv = np.stack(np.broadcast_arrays(theta * radius + 0 * phi, -phi * h + 0 * theta), axis=-1)
    cols = segments + 1
    i, j = np.meshgrid(np.arange(rings), np.arange(segments), indexing="ij")
    v00 = (i * cols + j).ravel()
    v01, v11, v10 = v00 + 1, v00 + cols + 1, v00 + cols
    tris = np.concatenate([np.stack([v00, v01, v11], 1), np.stack([v00, v11, v10], 1)])
    mb.add(material, pos.reshape(-1, 3), nrm.reshape(-1, 3), uv.reshape(-1, 2), tris)


def add_hip_roof(mb: MeshBuilder, corners, z: float, height: float, material: str) -> None:
    """Hip roof on a rectangle given as 4 counter-clockwise corners."""
    c = np.asarray(corners, dtype=np.float64)[:4, :2]
    if np.linalg.norm(c[1] - c[0]) < np.linalg.norm(c[2] - c[1]):
        c = np.roll(c, -1, axis=0)
    long_len = np.linalg.norm(c[1] - c[0])
    short_len = np.linalg.norm(c[2] - c[1])
    u = (c[1] - c[0]) / max(long_len, 1e-9)
    center = c.mean(axis=0)
    half = max(long_len - short_len, 0.0) / 2
    r0 = np.append(center - u * half, z + height)
    r1 = np.append(center + u * half, z + height)
    p = np.concatenate([c, np.full((4, 1), z)], axis=1)
    tris = [[p[0], p[1], r1], [p[0], r1, r0], [p[1], p[2], r1],
            [p[2], p[3], r0], [p[2], r0, r1], [p[3], p[0], r0]]
    add_triangles(mb, tris, material)


def add_cone(mb: MeshBuilder, cx: float, cy: float, z0: float, radius: float, height: float,
             material: str, segments: int = 6) -> None:
    t = np.linspace(0.0, 2 * math.pi, segments, endpoint=False)
    ring = np.stack([cx + radius * np.cos(t), cy + radius * np.sin(t), np.full(segments, z0)], 1)
    apex = np.array([cx, cy, z0 + height])
    tris = [[ring[k], ring[(k + 1) % segments], apex] for k in range(segments)]
    add_triangles(mb, tris, material)


def add_octahedron(mb: MeshBuilder, cx: float, cy: float, zc: float, rx: float, rz: float,
                   material: str, twist: float = 0.0) -> None:
    t = twist + np.arange(4) * math.pi / 2
    ring = np.stack([cx + rx * np.cos(t), cy + rx * np.sin(t), np.full(4, zc)], 1)
    top, bottom = np.array([cx, cy, zc + rz]), np.array([cx, cy, zc - rz])
    tris = []
    for k in range(4):
        a, b = ring[k], ring[(k + 1) % 4]
        tris.append([a, b, top])
        tris.append([b, a, bottom])
    add_triangles(mb, tris, material)


def regular_polygon(cx: float, cy: float, radius: float, sides: int, rotation: float = 0.0) -> Polygon:
    t = rotation + np.arange(sides) * 2 * math.pi / sides
    return Polygon(np.stack([cx + radius * np.cos(t), cy + radius * np.sin(t)], 1))


def rectangle(cx: float, cy: float, length: float, width: float, angle: float) -> Polygon:
    """Rectangle centered on (cx, cy); `length` runs along `angle` (radians from east)."""
    u = np.array([math.cos(angle), math.sin(angle)]) * length / 2
    v = np.array([-math.sin(angle), math.cos(angle)]) * width / 2
    c = np.array([cx, cy])
    return Polygon([c - u - v, c + u - v, c + u + v, c - u + v])


# --- ribbons (roads) ----------------------------------------------------------

def add_ribbon(mb: MeshBuilder, coords, width: float, height_fn, lift: float, material: str) -> None:
    """Flat strip of `width` along a polyline, draped on the terrain via height_fn(x, y)."""
    p = np.asarray(coords, dtype=np.float64)[:, :2]
    if len(p) < 2:
        return
    d = np.diff(p, axis=0)
    seg = np.hypot(d[:, 0], d[:, 1])
    keep = np.concatenate([[True], seg > 1e-6])
    p = p[keep]
    if len(p) < 2:
        return
    d = np.diff(p, axis=0)
    seg = np.hypot(d[:, 0], d[:, 1])
    t = d / seg[:, None]
    vt = np.empty((len(p), 2))
    vt[0], vt[-1] = t[0], t[-1]
    vt[1:-1] = t[:-1] + t[1:]
    vlen = np.hypot(vt[:, 0], vt[:, 1])
    vt = np.where(vlen[:, None] > 1e-9, vt / np.maximum(vlen, 1e-9)[:, None], np.vstack([t, t[-1:]]))
    scale = np.ones(len(p))
    if len(p) > 2:
        cos = np.einsum("ij,ij->i", vt[1:-1], t[:-1])
        scale[1:-1] = 1.0 / np.clip(cos, 0.5, 1.0)
    n = np.stack([-vt[:, 1], vt[:, 0]], axis=1) * (width / 2 * scale)[:, None]
    left, right = p + n, p - n
    zl = height_fn(left[:, 0], left[:, 1]) + lift
    zr = height_fn(right[:, 0], right[:, 1]) + lift
    pos = np.empty((len(p), 2, 3))
    pos[:, 0, :2], pos[:, 0, 2] = left, zl
    pos[:, 1, :2], pos[:, 1, 2] = right, zr
    s = np.concatenate([[0.0], np.cumsum(seg)])
    uv = np.empty((len(p), 2, 2))
    uv[:, 0, 0], uv[:, 1, 0] = 0.0, width
    uv[:, :, 1] = -s[:, None]
    nrm = np.tile([0.0, 0.0, 1.0], (len(p) * 2, 1))
    base = np.arange(len(p) - 1) * 2
    tris = np.concatenate([np.stack([base, base + 1, base + 3], 1), np.stack([base, base + 3, base + 2], 1)])
    mb.add(material, pos.reshape(-1, 3), nrm, uv.reshape(-1, 2), tris)
