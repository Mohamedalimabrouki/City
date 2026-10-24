"""Natural low-poly broadleaf, olive and citrus trees, built once as kit pieces and drawn as instances.

A crown is a handful of jittered, overlapping icosahedron clumps (20 triangles, 12 shared vertices each,
smooth normals) in three shades: dark low and inside, light on top. The trunk is a tapered prism that
leans a little; a few short branches reach from it into the crown. All numbers come from the style
(`[dressing.trees.<kind>]`). Each variant has its own random stream, so no other piece changes.
A citrus crown (prompt 24) carries `fruit` small oranges on its surface, from a second stream of its own.
"""
from __future__ import annotations

import math

import numpy as np

from ..rng import stream
from .builder import MeshBuilder
from .plants import clump, tube


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
        clump(mb, rng, center, rx, rz, spec["jitter"], mats[shade])
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
        tube(mb, base, tip, base_r, base_r * spec["taper"], sides, trunk_mat, rng.uniform(0, 6.28))
        stem_tops.append(tip)
    for b in range(int(rng.integers(spec["branches"][0], spec["branches"][1] + 1))):
        start = stem_tops[b % len(stem_tops)]
        a = lean_dir + b * 2.1 + rng.uniform(-0.4, 0.4)
        reach = crown_r * rng.uniform(0.45, 0.7)
        end = start + np.array([math.cos(a) * reach, math.sin(a) * reach, h * rng.uniform(0.14, 0.24)])
        tube(mb, start, end, base_r * spec["taper"] * 0.8, base_r * 0.25, 3, trunk_mat)
    if spec.get("fruit"):
        _fruit(mb, stream(seed, "props", "tree", kind, variant, "fruit"), clumps, spec, h)
    return mb


def _fruit(mb: MeshBuilder, rng, clumps: list, spec: dict, h: float) -> None:
    """Small oranges (8-face clumps) just outside the crown's outer and upper clumps, never inside."""
    size = float(spec["fruit_size"]) * h
    centers = np.array([c[0] for c in clumps])
    mid = centers.mean(axis=0)
    for _ in range(int(spec["fruit"])):
        center, rx, rz = clumps[int(rng.integers(0, len(clumps)))]
        a, up = rng.uniform(0.0, 2 * math.pi), rng.uniform(-0.25, 0.75)
        out = np.array([math.cos(a), math.sin(a), 0.0]) * math.sqrt(1.0 - up * up) + np.array([0.0, 0.0, up])
        side = center[:2] - mid[:2]
        if np.dot(out[:2], side) < 0:                  # face away from the crown's middle
            out[:2] = -out[:2]
        p = center + out * np.array([rx, rx, rz]) * (1.0 - float(spec["jitter"]) * 0.5)
        clump(mb, rng, p, size, size, 0.1, spec["fruit_material"], detail=0)


def variant_name(kind: str, variant: int) -> str:
    return f"tree_{kind}" if variant == 0 else f"tree_{kind}_{'bcdefgh'[variant - 1]}"


def tree_pieces(seed: int, table: dict) -> dict:
    """{piece name: MeshBuilder} for every variant of each kind in the style table `[dressing.trees]`."""
    out = {}
    for kind in ("broadleaf", "olive", "citrus"):
        spec = table.get(kind)
        if spec:
            for variant in range(int(spec["variants"])):
                out[variant_name(kind, variant)] = tree_crown_piece(kind, spec, seed, variant)
    return out
