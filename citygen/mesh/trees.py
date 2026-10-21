"""Natural low-poly broadleaf and olive trees, built once as kit pieces and drawn as instances.

A crown is a handful of jittered, overlapping icosahedron clumps (20 triangles, 12 shared vertices each,
smooth normals) in three shades: dark low and inside, light on top. The trunk is a tapered prism that
leans a little; a few short branches reach from it into the crown. All numbers come from the style
(`[dressing.trees.<kind>]`). Each variant has its own random stream, so no other piece changes.
"""
from __future__ import annotations

import math

import numpy as np

from ..rng import stream
from .builder import MeshBuilder

_PHI = (1.0 + math.sqrt(5.0)) / 2.0
_ICO_VERTS = np.array([[-1, _PHI, 0], [1, _PHI, 0], [-1, -_PHI, 0], [1, -_PHI, 0],
                       [0, -1, _PHI], [0, 1, _PHI], [0, -1, -_PHI], [0, 1, -_PHI],
                       [_PHI, 0, -1], [_PHI, 0, 1], [-_PHI, 0, -1], [-_PHI, 0, 1]], dtype=np.float64)
_ICO_VERTS /= np.linalg.norm(_ICO_VERTS, axis=1)[:, None]
_ICO_FACES = np.array([[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11],
                       [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
                       [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9],
                       [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]])


def _smooth_add(mb: MeshBuilder, material: str, pos: np.ndarray, faces: np.ndarray) -> None:
    """Add an indexed mesh with area-weighted smooth vertex normals."""
    n = np.cross(pos[faces[:, 1]] - pos[faces[:, 0]], pos[faces[:, 2]] - pos[faces[:, 0]])
    nrm = np.zeros_like(pos)
    for k in range(3):
        np.add.at(nrm, faces[:, k], n)
    length = np.linalg.norm(nrm, axis=1)
    nrm = nrm / np.where(length > 1e-12, length, 1.0)[:, None]
    uv = np.stack([pos[:, 0] + pos[:, 1], -pos[:, 2]], axis=1)
    mb.add(material, pos, nrm, uv, faces)


def _clump(mb: MeshBuilder, rng, center, rx: float, rz: float, jitter: float, material: str) -> None:
    radii = 1.0 + rng.uniform(-jitter, jitter, len(_ICO_VERTS))
    turn = rng.uniform(0.0, 2 * math.pi)
    c, s = math.cos(turn), math.sin(turn)
    v = _ICO_VERTS * radii[:, None] * np.array([rx, rx, rz])
    v = np.stack([v[:, 0] * c - v[:, 1] * s, v[:, 0] * s + v[:, 1] * c, v[:, 2]], axis=1)
    _smooth_add(mb, material, v + np.asarray(center, dtype=np.float64), _ICO_FACES)


def _tube(mb: MeshBuilder, p0, p1, r0: float, r1: float, sides: int, material: str, turn: float = 0.0) -> None:
    """A tapered prism from p0 (radius r0) to p1 (radius r1), open ends, smooth sides."""
    p0, p1 = np.asarray(p0, dtype=np.float64), np.asarray(p1, dtype=np.float64)
    axis = p1 - p0
    axis /= np.linalg.norm(axis)
    side = np.cross(axis, [0.0, 0.0, 1.0] if abs(axis[2]) < 0.9 else [1.0, 0.0, 0.0])
    side /= np.linalg.norm(side)
    up = np.cross(axis, side)
    t = turn + np.arange(sides) * 2 * math.pi / sides
    ring = np.cos(t)[:, None] * side + np.sin(t)[:, None] * up
    pos = np.concatenate([p0 + ring * r0, p1 + ring * r1])
    faces = []
    for k in range(sides):
        a, b = k, (k + 1) % sides
        faces += [[a, b, sides + b], [a, sides + b, sides + a]]
    _smooth_add(mb, material, pos, np.array(faces))


def _pick(rng, spec) -> float:
    lo, hi = spec if isinstance(spec, (list, tuple)) else (spec, spec)
    return float(rng.uniform(lo, hi))


def tree_crown_piece(kind: str, spec: dict, seed: int, variant: int, height: float = 8.0) -> MeshBuilder:
    """One tree variant at `height`; `spec` is the style table `[dressing.trees.<kind>]`."""
    rng = stream(seed, "props", "tree", kind, variant)
    mb = MeshBuilder()
    mats = spec["materials"]                                  # [dark, mid, light]
    h = height
    n = int(rng.integers(spec["clumps"][0], spec["clumps"][1] + 1))
    stems = int(rng.integers(spec.get("stems", [1, 1])[0], spec.get("stems", [1, 1])[1] + 1))
    trunk_h = spec["trunk_height"] * h
    crown_r = spec["crown_radius"] * h
    lean = spec.get("lean", 0.0) * h
    lean_dir = rng.uniform(0.0, 2 * math.pi)
    clumps = []                                               # (center, rx, rz)
    top_r = _pick(rng, spec["clump_radius"]) * h
    top_rz = top_r * spec["flatten"]
    top = np.array([math.cos(lean_dir) * lean * 0.5, math.sin(lean_dir) * lean * 0.5, h - top_rz * 1.05])
    clumps.append((top, top_r, top_rz))
    crown_low = trunk_h + spec["crown_drop"] * h
    for k in range(1, n):
        a = k * 2.399963 + rng.uniform(-0.5, 0.5)              # golden angle keeps the clumps spread round
        d = crown_r * math.sqrt(k / n) * rng.uniform(0.7, 1.0)
        rx = _pick(rng, spec["clump_radius"]) * h
        rz = rx * spec["flatten"]
        z = crown_low + (h - rz * 1.6 - crown_low) * rng.uniform(0.0, 1.0) ** spec.get("low_bias", 1.0)
        clumps.append((np.array([top[0] + math.cos(a) * d, top[1] + math.sin(a) * d, z]), rx, rz))
    lo_z, hi_z = min(c[0][2] for c in clumps), max(c[0][2] for c in clumps)
    for center, rx, rz in clumps:
        f = (center[2] - lo_z) / max(hi_z - lo_z, 1e-6)
        shade = 0 if f < spec["dark_below"] else (2 if f > spec["light_above"] else 1)
        _clump(mb, rng, center, rx, rz, spec["jitter"], mats[shade])
    # wood: one or two leaning stems, then short branches into the crown
    trunk_mat = spec["trunk_material"]
    sides = int(spec["trunk_sides"])
    base_r = spec["trunk_radius"] * h
    stem_tops = []
    for s in range(stems):
        a = lean_dir + (s - (stems - 1) / 2) * 1.6 + rng.uniform(-0.3, 0.3)
        tilt = lean * (0.6 if stems == 1 else 1.0)
        base = np.array([math.cos(a) * base_r * 0.5 * (stems - 1), math.sin(a) * base_r * 0.5 * (stems - 1), -0.3])
        tip = np.array([math.cos(a) * tilt, math.sin(a) * tilt, trunk_h + spec["crown_drop"] * h * 0.5])
        _tube(mb, base, tip, base_r, base_r * spec["taper"], sides, trunk_mat, rng.uniform(0, 6.28))
        stem_tops.append(tip)
    for b in range(int(rng.integers(spec["branches"][0], spec["branches"][1] + 1))):
        start = stem_tops[b % len(stem_tops)]
        a = lean_dir + b * 2.1 + rng.uniform(-0.4, 0.4)
        reach = crown_r * rng.uniform(0.45, 0.7)
        end = start + np.array([math.cos(a) * reach, math.sin(a) * reach, h * rng.uniform(0.14, 0.24)])
        _tube(mb, start, end, base_r * spec["taper"] * 0.8, base_r * 0.25, 3, trunk_mat)
    return mb


def variant_name(kind: str, variant: int) -> str:
    return f"tree_{kind}" if variant == 0 else f"tree_{kind}_{'bcdefgh'[variant - 1]}"


def tree_pieces(seed: int, table: dict) -> dict:
    """{piece name: MeshBuilder} for every variant of each kind in the style table `[dressing.trees]`."""
    out = {}
    for kind in ("broadleaf", "olive"):
        spec = table.get(kind)
        if spec:
            for variant in range(int(spec["variants"])):
                out[variant_name(kind, variant)] = tree_crown_piece(kind, spec, seed, variant)
    return out
