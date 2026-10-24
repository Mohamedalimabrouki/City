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


def closed(pts) -> bool:
    """`len(pts) > 1 and np.allclose(pts[0], pts[-1])` for float64 rows: the same test, without
    numpy's per-call cost (rings are checked thousands of times per tile)."""
    if len(pts) < 2:
        return False
    return all((abs(p - q) <= 1e-8 + 1e-5 * abs(q) and math.isfinite(q)) or p == q
               for p, q in zip(pts[0].tolist(), pts[-1].tolist()))


class MeshBuilder:
    def __init__(self, origin=(0.0, 0.0)):
        self.origin = np.array([origin[0], origin[1], 0.0])
        self._parts: dict[str, list] = {}
        self._fine: dict[str, list] = {}   # material -> indices of chunks added while `fine` was on
        self.fine = False   # on: these triangles keep float positions in a quantized tile (add_sheet)

    def add(self, material: str, pos, nrm, uv, tris, col=None) -> None:
        """Append triangles; `col` (N, 3) linear vertex colors is optional (the terrain tint)."""
        pos = np.asarray(pos, dtype=np.float64).reshape(-1, 3)
        if len(pos) == 0:
            return
        part = self._parts.setdefault(material, [[], [], [], [], 0, []])
        part[0].append(pos - self.origin)
        part[1].append(np.asarray(nrm, dtype=np.float64).reshape(-1, 3))
        part[2].append(np.asarray(uv, dtype=np.float64).reshape(-1, 2))
        part[3].append(np.asarray(tris, dtype=np.int64).reshape(-1, 3) + part[4])
        part[5].append(None if col is None else np.asarray(col, dtype=np.float64).reshape(-1, 3))
        part[4] += len(pos)
        if self.fine:
            self._fine.setdefault(material, []).append(len(part[3]) - 1)

    @property
    def triangles(self) -> int:
        return sum(sum(len(t) for t in part[3]) for part in self._parts.values())

    def sizes(self) -> list:
        """[(vertices, triangles, has colors)] per material, without building the arrays."""
        return [(part[4], sum(len(t) for t in part[3]), any(c is not None for c in part[5]))
                for part in self._parts.values()]

    def gltf_parts(self, fine: bool = False) -> dict:
        """{material: {"pos", "nrm", "uv", "idx", "col"?}} in glTF axes; `fine` adds a per-triangle
        "fine" mask where some triangles were added with `self.fine` on (they stay float in a quantized tile)."""
        out = {}
        for mat, (pos, nrm, uv, tris, _count, col) in self._parts.items():
            out[mat] = {"pos": _to_gltf(np.concatenate(pos)), "nrm": _to_gltf(np.concatenate(nrm)),
                        "uv": np.concatenate(uv), "idx": np.concatenate(tris).reshape(-1)}
            if any(c is not None for c in col):
                # a piece without colors in a tinted part stays untinted: white, never black
                out[mat]["col"] = np.concatenate([np.ones((len(p), 3)) if c is None else c
                                                  for p, c in zip(pos, col)])
            if fine and mat in self._fine:
                chunk = np.zeros(len(tris), dtype=bool)
                chunk[self._fine[mat]] = True
                out[mat]["fine"] = np.repeat(chunk, [len(t) for t in tris])
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


def add_walls(mb: MeshBuilder, ring, z0: float, z1: float, material: str, z_ref: float,
              plinth: tuple[str, float] | None = None, frontage=None, only=None) -> None:
    """Vertical walls along a ring. Exterior rings must be CCW and holes CW (see shapely orient).

    `plinth` = (material, height): the part of the wall from the bottom up to `height` meters
    above `z_ref` (the building's highest ground point) is drawn in that material, so a base
    band follows the street instead of the buried foot of the wall. `frontage`, when given, is
    one bool per ring segment: only those segments get the plinth (street-facing walls), which
    keeps party walls and block interiors out of the tile bytes. `only` (one bool per segment) draws
    just those segments, their u still measured along the whole ring (a massed building's walls are
    drawn in groups of one height, the texture running on across them).
    """
    if only is not None:
        only = np.asarray(only, dtype=bool)
        front = only if frontage is None else only & np.asarray(frontage, dtype=bool)
        split = z_ref + float(plinth[1]) if plinth is not None else z0
        if plinth is not None and z0 < split < z1:
            _wall_band(mb, ring, z0, split, plinth[0], z_ref, front)
            _wall_band(mb, ring, split, z1, material, z_ref, front)
            _wall_band(mb, ring, z0, z1, material, z_ref, only & ~front)
        else:
            _wall_band(mb, ring, z0, z1, material, z_ref, only)
        return
    if plinth is not None:
        base_material, base_height = plinth
        split = z_ref + float(base_height)
        if z0 < split < z1:
            mask = None if frontage is None else np.asarray(frontage, dtype=bool)
            _wall_band(mb, ring, z0, split, base_material, z_ref, mask)
            _wall_band(mb, ring, split, z1, material, z_ref, mask)
            if mask is not None:
                _wall_band(mb, ring, z0, z1, material, z_ref, ~mask)
            return
    _wall_band(mb, ring, z0, z1, material, z_ref)


def _wall_band(mb: MeshBuilder, ring, z0: float, z1: float, material: str, z_ref: float,
               mask=None) -> None:
    """One vertical band of a wall; v = 0 at z_ref so wall textures line up along a street."""
    pts = np.asarray(ring, dtype=np.float64)[:, :2]
    if closed(pts):
        pts = pts[:-1]
    if len(pts) < 2:
        return
    a, b = pts, np.roll(pts, -1, axis=0)
    d = b - a
    length = np.hypot(d[:, 0], d[:, 1])
    keep = length > 1e-6
    if mask is None:
        a, b, d, length = a[keep], b[keep], d[keep], length[keep]
        s1 = np.cumsum(length)
        s0 = s1 - length
    else:
        s_all = np.concatenate([[0.0], np.cumsum(length)])
        s0_all, s1_all = s_all[:-1], s_all[1:]
        keep &= np.asarray(mask, dtype=bool)
        a, b, d, length = a[keep], b[keep], d[keep], length[keep]
        s0, s1 = s0_all[keep], s1_all[keep]
    k = len(a)
    if not k:
        return
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


def add_draped_cap(mb: MeshBuilder, poly: Polygon, height_fn, material: str, along=None) -> None:
    """Horizontal cap that follows a height function at every vertex (a raised sidewalk).

    UVs are planar meters (x, -y). `along(cx, cy) -> (T, 2)` gives each triangle a unit direction
    (the nearest street's) and turns its UVs so u runs along it and v across: rows of paving
    slabs then follow the street, and turn with it at a corner, instead of the world axes.
    """
    tri = triangulate(poly)
    if len(tri) == 0:
        return
    pos = np.concatenate([tri, np.zeros((len(tri), 3, 1))], axis=2).reshape(-1, 3)
    pos[:, 2] = height_fn(pos[:, 0], pos[:, 1])
    _add_cap(mb, tri, pos, material, along)


def add_draped_caps(mb: MeshBuilder, polys: list, height_fn, material: str, lifts: list) -> None:
    """`add_draped_cap(mb, poly, height_fn + lift, material)` for each polygon and lift in turn, with
    one `height_fn` call for all their vertices (`height_fn` must work point by point, as the ground does)."""
    tris, adds = [], []
    for poly, lift in zip(polys, lifts):
        tri = triangulate(poly)
        if len(tri):
            tris.append(tri)
            adds.append(lift)
    if not tris:
        return
    pos = [np.concatenate([t, np.zeros((len(t), 3, 1))], axis=2).reshape(-1, 3) for t in tris]
    every = np.concatenate(pos)
    z = np.split(np.asarray(height_fn(every[:, 0], every[:, 1]), dtype=np.float64),
                 np.cumsum([len(p) for p in pos])[:-1])
    for t, p, zz, lift in zip(tris, pos, z, adds):
        p[:, 2] = zz + lift
        _add_cap(mb, t, p, material)


def _add_cap(mb: MeshBuilder, tri: np.ndarray, pos: np.ndarray, material: str, along=None) -> None:
    nrm = np.tile([0.0, 0.0, 1.0], (len(pos), 1))
    if along is None:
        uv = np.stack([pos[:, 0], -pos[:, 1]], axis=1)
    else:
        center = tri.mean(axis=1)
        c, s = np.repeat(np.asarray(along(center[:, 0], center[:, 1]), dtype=np.float64), 3, axis=0).T
        uv = np.stack([pos[:, 0] * c + pos[:, 1] * s, pos[:, 0] * s - pos[:, 1] * c], axis=1)
    mb.add(material, pos, nrm, uv, np.arange(len(pos)).reshape(-1, 3))


def add_skirt(mb: MeshBuilder, ring, top, bottom, material: str, only=None) -> None:
    """Vertical face around a ring, with a different height at every vertex.

    `ring` is an open coordinate ring (the closing point is optional). The caller orients
    exterior rings counter-clockwise and holes clockwise, so the normal points out of the solid.
    UVs are meters: u along the ring, v down from the top edge (a curb stone's top is v = 0).
    `only` (one bool per segment) draws just those segments.
    """
    pts = np.asarray(ring, dtype=np.float64)[:, :2]
    if closed(pts):
        pts = pts[:-1]
    top, bottom = np.asarray(top, dtype=np.float64), np.asarray(bottom, dtype=np.float64)
    if len(top) == len(pts) + 1:
        top, bottom = top[:-1], bottom[:-1]
    if len(pts) < 2 or len(top) != len(pts) or len(bottom) != len(pts):
        return
    a, b = pts, np.roll(pts, -1, axis=0)
    d = b - a
    length = np.hypot(d[:, 0], d[:, 1])
    keep = length > 1e-6
    if only is not None:
        keep &= np.asarray(only, dtype=bool)
    a, b, d, length = a[keep], b[keep], d[keep], length[keep]
    ta, tb, ba, bb = top[keep], np.roll(top, -1)[keep], bottom[keep], np.roll(bottom, -1)[keep]
    k = len(a)
    if not k:
        return
    pos = np.empty((k, 4, 3))
    pos[:, 0, :2], pos[:, 1, :2], pos[:, 2, :2], pos[:, 3, :2] = a, b, b, a
    pos[:, 0, 2], pos[:, 1, 2], pos[:, 2, 2], pos[:, 3, 2] = ta, tb, bb, ba
    nrm = np.zeros((k, 4, 3))
    nrm[:, :, 0] = (d[:, 1] / length)[:, None]
    nrm[:, :, 1] = (-d[:, 0] / length)[:, None]
    s = np.concatenate([[0.0], np.cumsum(length)])
    uv = np.empty((k, 4, 2))
    uv[:, 0, 0], uv[:, 1, 0], uv[:, 2, 0], uv[:, 3, 0] = s[:-1], s[1:], s[1:], s[:-1]
    uv[:, 0, 1], uv[:, 1, 1], uv[:, 2, 1], uv[:, 3, 1] = 0.0, 0.0, tb - bb, ta - ba
    tris = (np.arange(k) * 4)[:, None, None] + np.array([[0, 2, 1], [0, 3, 2]])[None]
    mb.add(material, pos.reshape(-1, 3), nrm.reshape(-1, 3), uv.reshape(-1, 2), tris)


def add_loft(mb: MeshBuilder, inner, z_inner: float, outer, z_outer: float, material: str) -> None:
    """Quad strip between two matching rings at two heights (a roof coping).

    `inner` and `outer` are equal-length coordinate rings in the same direction, vertex i of one
    facing vertex i of the other. Faces point up, as seen from above.
    """
    a = np.asarray(inner, dtype=np.float64)[:, :2]
    b = np.asarray(outer, dtype=np.float64)[:, :2]
    if closed(a):
        a = a[:-1]
    if closed(b):
        b = b[:-1]
    if len(a) < 3 or len(a) != len(b):
        return
    a1, b1 = np.roll(a, -1, axis=0), np.roll(b, -1, axis=0)
    pos = np.stack([np.column_stack([a, np.full(len(a), z_inner)]),
                    np.column_stack([a1, np.full(len(a), z_inner)]),
                    np.column_stack([b1, np.full(len(a), z_outer)]),
                    np.column_stack([b, np.full(len(a), z_outer)])], axis=1)
    n = np.cross(pos[:, 1] - pos[:, 0], pos[:, 3] - pos[:, 0])
    norm = np.linalg.norm(n, axis=1)
    keep = norm > 1e-9
    if not keep.any():
        return
    pos, n, norm = pos[keep], n[keep] / norm[keep, None], norm[keep]
    flip = n[:, 2] < 0        # seen from below: turn the face over
    pos[flip] = pos[flip][:, ::-1]
    n[flip] *= -1.0
    uv = np.stack([pos[:, :, 0], -pos[:, :, 1]], axis=-1)
    tris = (np.arange(len(pos)) * 4)[:, None, None] + _QUAD[None]
    mb.add(material, pos.reshape(-1, 3), np.repeat(n, 4, axis=0), uv.reshape(-1, 2), tris)


def extrude(mb: MeshBuilder, poly: Polygon, z0: float, z1: float, wall: str, roof: str | None,
            z_ref: float | None = None, plinth: tuple[str, float] | None = None,
            frontage=None) -> None:
    """Solid prism: walls for every ring plus a flat roof (skip the roof with roof=None).

    A plinth goes on the outside ring only: courtyard walls keep their plain finish, which keeps
    the dense old-town tiles inside the +10% byte budget of prompt 19. `frontage` selects the
    exterior segments that get it (see add_walls); None means every exterior segment.
    """
    poly = orient(poly, sign=1.0)
    z_ref = z0 if z_ref is None else z_ref
    add_walls(mb, poly.exterior.coords, z0, z1, wall, z_ref, plinth, frontage)
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
    was, mb.fine = mb.fine, True      # the two faces lie millimeters apart: never quantize them
    add_triangles(mb, tris, material)
    add_triangles(mb, tris[:, ::-1] - n[:, None, :] * thickness, material)
    mb.fine = was


def add_quads(mb: MeshBuilder, mat: str, quads: np.ndarray, toward: np.ndarray) -> None:
    """Flat quads (q, 4, 3), each turned so its normal points along `toward` (q, 3); planar meter UVs."""
    if not len(quads):
        return
    n = np.cross(quads[:, 2] - quads[:, 0], quads[:, 3] - quads[:, 1])
    n /= np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]
    flip = (n * toward).sum(axis=1) < 0
    quads[flip] = quads[flip][:, ::-1]
    n[flip] *= -1.0
    u = np.where(np.abs(n[:, 2:3]) > 0.7, quads[:, :, 0], quads[:, :, 0] * -n[:, 1:2] + quads[:, :, 1] * n[:, 0:1])
    v = np.where(np.abs(n[:, 2:3]) > 0.7, -quads[:, :, 1], -quads[:, :, 2])
    tris = (np.arange(len(quads)) * 4)[:, None, None] + np.array([[0, 1, 2], [0, 2, 3]])[None]
    mb.add(mat, quads.reshape(-1, 3), np.repeat(n, 4, axis=0), np.stack([u, v], axis=-1).reshape(-1, 2), tris)


# --- roofs and details ------------------------------------------------------

def add_boxes(mb: MeshBuilder, a, u, s0, s1, depth: float, z0, z1, material: str) -> None:
    """Many boxes with no bottom in one call: box i runs from a[i] + u[i] * s0[i] to a[i] + u[i] * s1[i]
    along its outer face and `depth` m to the left of u (inward), from z0[i] to z1[i]. Walls u in meters
    along each face, v = -z, like `add_walls`; tops planar (x, -y)."""
    a, u = np.asarray(a, dtype=np.float64).reshape(-1, 2), np.asarray(u, dtype=np.float64).reshape(-1, 2)
    k = len(a)
    if not k:
        return
    s0, s1, z0, z1 = (np.broadcast_to(np.asarray(v, dtype=np.float64), (k,)) for v in (s0, s1, z0, z1))
    n = np.stack([-u[:, 1], u[:, 0]], axis=1) * depth
    p0, p1 = a + u * s0[:, None], a + u * s1[:, None]
    q0, q1 = p0 + n, p1 + n
    sides = [(p0, p1), (q1, q0), (q0, p0), (p1, q1)]     # outer, inner, start and end faces (normal on the right)
    pa = np.concatenate([s[0] for s in sides])
    pb = np.concatenate([s[1] for s in sides])
    lo, hi = np.tile(z0, 4), np.tile(z1, 4)
    d = pb - pa
    length = np.maximum(np.hypot(d[:, 0], d[:, 1]), 1e-9)
    m = len(pa)
    pos = np.empty((m, 4, 3))
    pos[:, 0, :2], pos[:, 1, :2], pos[:, 2, :2], pos[:, 3, :2] = pa, pb, pb, pa
    pos[:, :2, 2], pos[:, 2:, 2] = lo[:, None], hi[:, None]
    nrm = np.zeros((m, 4, 3))
    nrm[:, :, 0], nrm[:, :, 1] = (d[:, 1] / length)[:, None], (-d[:, 0] / length)[:, None]
    uv = np.empty((m, 4, 2))
    uv[:, 0, 0], uv[:, 1, 0], uv[:, 2, 0], uv[:, 3, 0] = 0.0, length, length, 0.0
    uv[:, :, 1] = -pos[:, :, 2]
    top = np.stack([p0, p1, q1, q0], axis=1)
    tpos = np.concatenate([top, np.broadcast_to(z1[:, None, None], (k, 4, 1))], axis=2)
    tnrm = np.tile([0.0, 0.0, 1.0], (k, 4, 1))
    tuv = np.stack([top[:, :, 0], -top[:, :, 1]], axis=2)
    pos = np.concatenate([pos, tpos]).reshape(-1, 3)
    nrm = np.concatenate([nrm, tnrm]).reshape(-1, 3)
    uv = np.concatenate([uv, tuv]).reshape(-1, 2)
    tris = (np.arange(m + k) * 4)[:, None, None] + _QUAD[None]
    mb.add(material, pos, nrm, uv, tris)


def add_battlement(mb: MeshBuilder, chains: list, z: float, breast: float, merlon, depth: float,
                   material: str) -> None:
    """A breastwork `breast` m high and `depth` m thick along each chain of points (the building's inside
    on its left) standing on a flat roof at z, with merlons on it (width, gap, height), spread evenly
    along each side. In a chain each side after the first (and every side of a closed chain) starts
    `depth` m in, so two boxes never share a corner square (their tops would flicker)."""
    w, gap, mh = (float(v) for v in merlon)
    a, u, s0, s1, z0, z1 = [], [], [], [], [], []
    for chain in chains:
        pts = np.asarray(chain, dtype=np.float64)[:, :2]
        ring = len(pts) > 3 and np.allclose(pts[0], pts[-1])
        for i in range(len(pts) - 1):
            d = pts[i + 1] - pts[i]
            length = float(np.hypot(*d))
            start = depth if (i > 0 or ring) else 0.0
            if length - start < 0.1:
                continue
            ui = d / length
            a.append(pts[i]), u.append(ui), s0.append(start), s1.append(length), z0.append(z), z1.append(z + breast)
            count = int((length - start + gap) // (w + gap))
            if count <= 0:
                continue
            first = start + (length - start - (count * w + (count - 1) * gap)) / 2
            for j in range(count):
                a.append(pts[i]), u.append(ui)
                s0.append(first + j * (w + gap)), s1.append(first + j * (w + gap) + w)
                z0.append(z + breast), z1.append(z + breast + mh)
    add_boxes(mb, a, u, s0, s1, depth, z0, z1, material)


def _horseshoe(width: float, height: float, segments: int) -> np.ndarray:
    """(N, 2) outline (s, z) of a horseshoe arch, counter-clockwise from the bottom left: jambs `width`
    apart, the arc a circle a little wider than them closing at `height`."""
    tilt = math.radians(30.0)                       # the arc runs on 30 degrees below its center each side
    r = width / 2 / math.cos(tilt)
    zc = max(height - r, r * math.sin(tilt))
    t = np.linspace(-tilt, math.pi + tilt, segments + 1)
    arc = np.stack([r * np.cos(t), zc + r * np.sin(t)], axis=1)
    return np.vstack([[-width / 2, 0.0], [width / 2, 0.0], arc])


def round_head(width: float, height: float, segments: int) -> np.ndarray:
    """(N, 2) outline (s, z) of a round-arched opening, counter-clockwise from the bottom left: jambs `width`
    apart, a half circle closing at `height` (prompt 32)."""
    t = np.linspace(0.0, math.pi, segments + 1)
    zc = max(height - width / 2, 0.0)
    arc = np.stack([width / 2 * np.cos(t), zc + width / 2 * np.sin(t)], axis=1)
    return np.vstack([[-width / 2, 0.0], [width / 2, 0.0], arc])


def add_arch(mb: MeshBuilder, x: float, y: float, z: float, yaw: float, width: float, height: float,
             frame: float, material: str, frame_material: str = "stone_frame", head: str = "horseshoe") -> None:
    """A horseshoe-arched (or with `head` "round", round-arched) door or window on a wall face: the panel
    just in front of the wall at (x, y) (yaw = outward normal), its foot at z, and a stone band `frame` m
    wide round the jambs and arc."""
    n = np.array([math.cos(yaw), math.sin(yaw)])
    t = np.array([-math.sin(yaw), math.cos(yaw)])      # (t, up, n) right-handed: CCW in (s, z) faces out
    segs = 10 if width > 2.0 else 6
    shape = _horseshoe if head == "horseshoe" else round_head
    out = shape(width, height, segs)

    def world(sz, off):
        xy = np.array([x, y]) + n * off + sz[:, :1] * t
        return np.column_stack([xy, z + sz[:, 1]])

    if head == "horseshoe":
        r = width / 2 / math.cos(math.radians(30.0))
        zc = max(height - r, r * 0.5)
    else:
        zc = max(height - width / 2, 0.0)
    center = np.array([[0.0, zc]])
    pos = world(np.vstack([center, out]), 0.06)
    m = len(out)
    fan = np.stack([np.zeros(m, dtype=np.int64), 1 + np.arange(m), 1 + (np.arange(m) + 1) % m], axis=1)
    nrm = np.tile([n[0], n[1], 0.0], (len(pos), 1))
    mb.add(material, pos, nrm, np.column_stack([np.vstack([center, out])[:, 0], -np.vstack([center, out])[:, 1]]), fan)
    if frame <= 0.0:
        return
    inner = out[1:]                                    # from the right foot up, over, down to the left foot
    outer = shape(width + 2 * frame, height + frame, segs)[1:]
    outer = np.vstack([outer, [[-(width / 2 + frame), 0.0]]])
    inner = np.vstack([inner, [[-width / 2, 0.0]]])
    pos = np.vstack([world(inner, 0.12), world(outer, 0.12)])
    k = len(inner)
    i = np.arange(k - 1)
    tris = np.concatenate([np.stack([i, k + i, k + i + 1], axis=1), np.stack([i, k + i + 1, i + 1], axis=1)])
    both = np.vstack([inner, outer])
    mb.add(frame_material, pos, np.tile([n[0], n[1], 0.0], (len(pos), 1)), np.column_stack([both[:, 0], -both[:, 1]]), tris)

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
    """Hip roof on a rectangle given as 4 counter-clockwise corners.

    UVs are planar in meters: u along the eave, v up the slope, so roof-tile rows run down every
    face (4.0 m of eave and 1.6 m of slope per texture repeat with the maghreb palette) instead
    of smearing into stripes under the old (x + y, -z) projection.
    """
    c = np.asarray(corners, dtype=np.float64)[:4, :2]
    if np.linalg.norm(c[1] - c[0]) < np.linalg.norm(c[2] - c[1]):
        c = np.roll(c, -1, axis=0)
    long_len = float(np.linalg.norm(c[1] - c[0]))
    short_len = float(np.linalg.norm(c[2] - c[1]))
    if long_len < 1e-9 or short_len < 1e-9:
        return
    u = (c[1] - c[0]) / long_len
    n = np.array([-u[1], u[0]])                     # into the rectangle, for counter-clockwise corners
    hw = short_len / 2.0
    slope = math.hypot(hw, height)
    half = max(long_len - short_len, 0.0) / 2.0     # ridge end inset from each end eave
    end_slope = math.hypot(half, height)

    def at(x: float, y: float, zz: float) -> np.ndarray:
        p = c[0] + u * x + n * y
        return np.array([p[0], p[1], zz])

    p00, p10 = at(0.0, 0.0, z), at(long_len, 0.0, z)
    p01, p11 = at(0.0, short_len, z), at(long_len, short_len, z)
    r0, r1 = at(half, hw, z + height), at(long_len - half, hw, z + height)
    # (vertices, uvs): ridge vertices are `slope` meters up their face, eave vertices are 0
    faces = (
        ((p00, p10, r1, r0), ((0.0, 0.0), (long_len, 0.0), (long_len - half, slope), (half, slope))),
        ((p11, p01, r0, r1), ((long_len, 0.0), (0.0, 0.0), (half, slope), (long_len - half, slope))),
        ((p01, p00, r0), ((short_len, 0.0), (0.0, 0.0), (hw, end_slope))),
        ((p10, p11, r1), ((0.0, 0.0), (short_len, 0.0), (hw, end_slope))),
    )
    for verts, uv in faces:
        pos = np.asarray(verts)
        nrm = np.cross(pos[1] - pos[0], pos[-1] - pos[0])
        nrm /= max(float(np.linalg.norm(nrm)), 1e-12)
        tris = _QUAD if len(pos) == 4 else np.array([[0, 1, 2]])
        if len(tris) > 1:   # a square roof has no ridge: its two end quads collapse to triangles
            area = np.cross(pos[tris[:, 1]] - pos[tris[:, 0]], pos[tris[:, 2]] - pos[tris[:, 0]])
            tris = tris[np.linalg.norm(area, axis=1) > 1e-9]
        if len(tris):
            mb.add(material, pos, np.tile(nrm, (len(pos), 1)), np.asarray(uv), tris)


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

def add_ribbon(mb: MeshBuilder, coords, width: float, height_fn, lift: float, material: str,
               start: float = 0.0) -> None:
    """Flat strip of `width` along a polyline, draped on the terrain via height_fn(x, y).

    UVs are meters: u along the line from `start` (the distance of the first point along the
    whole street, so a street cut by tile edges keeps one continuous pattern), v across from the
    center line (-width/2 on the left, +width/2 on the right).
    """
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
    s = start + np.concatenate([[0.0], np.cumsum(seg)])
    uv = np.empty((len(p), 2, 2))
    uv[:, :, 0] = s[:, None]
    uv[:, 0, 1], uv[:, 1, 1] = -width / 2, width / 2
    nrm = np.tile([0.0, 0.0, 1.0], (len(p) * 2, 1))
    base = np.arange(len(p) - 1) * 2
    tris = np.concatenate([np.stack([base, base + 1, base + 3], 1), np.stack([base, base + 3, base + 2], 1)])
    mb.add(material, pos.reshape(-1, 3), nrm, uv.reshape(-1, 2), tris)
