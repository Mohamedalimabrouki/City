"""Bougainvillea climbers: a twisting trunk and a curtain of bracts against a wall.

The piece anchors on the wall face at street level: x runs along the wall, y points out of it
toward the street (the side people see), z is up. A couple of bent, tapered stems rise from the
ground into a dense, flat mass of small flattened bracts that hangs from the top of the wall to
a ragged hem. All numbers come from the style table `[dressing.climber]`; each variant has
its own random stream, so no other kit piece changes when a climber does.
"""
from __future__ import annotations

import math

import numpy as np

from ..rng import stream
from .builder import MeshBuilder
from .plants import clump, tube


def variant_name(variant: int) -> str:
    return "bougainvillea" if variant == 0 else f"bougainvillea_{'bcdefgh'[variant - 1]}"


def _pick(rng, spec) -> float:
    lo, hi = spec if isinstance(spec, (list, tuple)) else (spec, spec)
    return float(rng.uniform(lo, hi))


def _targets(rng, spec) -> list:
    """(x, z, size) for every clump, on a staggered grid from the wall top down to a ragged hem."""
    n = int(rng.integers(spec["clumps"][0], spec["clumps"][1] + 1))
    half = _pick(rng, spec["spread"])
    top = spec["top"] + rng.uniform(-0.1, 0.1)
    drop = _pick(rng, spec["drop"])
    rows = int(spec.get("rows", 6))
    cols = int(np.ceil(n / rows))
    step = 2 * half / cols
    slots = []
    for r in range(rows):
        t = r / max(rows - 1, 1)
        z = top - drop * t
        for c in range(cols):
            x = -half + step * (c + 0.5) + (step * 0.5 if r % 2 else 0.0) + rng.uniform(-0.07, 0.07)
            zz = z + rng.uniform(-0.1, 0.1) * (1.0 + t)          # the hem is the most ragged
            slots.append((x, zz, rng.uniform(0.8, 1.0)))
    if len(slots) > n:                                          # thin out the hem, not the top
        hem = [k for k, s in enumerate(slots) if s[1] < top - drop * 0.7]
        rng.shuffle(hem)
        skip = set(hem[:len(slots) - n])
        slots = [s for k, s in enumerate(slots) if k not in skip]
    while len(slots) < n:                                       # never leave the mass short of clumps
        x, z, size = slots[int(rng.integers(len(slots)))]
        slots.append((x + rng.uniform(-0.12, 0.12), z + rng.uniform(-0.15, 0.15), size * 0.95))
    return slots[:n]


def climber_piece(spec, seed: int, variant: int) -> MeshBuilder:
    """One climber variant; `spec` is the style table `[dressing.climber]`."""
    rng = stream(seed, "props", "climber", variant)
    mb = MeshBuilder()
    mats = spec["materials"]                                   # [deep, mid, pale]
    leaf_mat = spec["leaf_material"]
    top = spec["top"]
    half = _pick(rng, spec["spread"])
    base_r = spec["trunk_radius"]
    stems = int(rng.integers(spec["trunks"][0], spec["trunks"][1] + 1))
    tips = []
    for s in range(stems):
        sides = int(rng.integers(4, 6))                        # 4 or 5 sides
        x0 = (s - (stems - 1) / 2) * half * 0.5 + rng.uniform(-0.08, 0.08)
        sign = 1.0 if s % 2 else -1.0
        mid = np.array([x0 + sign * rng.uniform(0.24, 0.42), rng.uniform(0.1, 0.16), top * rng.uniform(0.45, 0.58)])
        tip = np.array([x0 - sign * rng.uniform(0.1, 0.28), rng.uniform(0.08, 0.14), top - rng.uniform(0.25, 0.55)])
        base = np.array([x0, 0.14, -0.15])
        r_mid = base_r * rng.uniform(0.55, 0.7)
        tube(mb, base, mid, base_r, r_mid, sides, spec["trunk_material"], rng.uniform(0, 6.28))
        tube(mb, mid, tip, r_mid, base_r * spec["taper"], sides, spec["trunk_material"], rng.uniform(0, 6.28))
        tips.append(tip)
    for b in range(int(rng.integers(spec["branches"][0], spec["branches"][1] + 1))):
        start = tips[b % len(tips)]
        a = rng.uniform(0, 2 * math.pi)
        reach = rng.uniform(0.3, 0.6)
        end = start + np.array([math.cos(a) * reach, rng.uniform(0.0, 0.08), rng.uniform(0.05, 0.35)])
        tube(mb, start, end, base_r * spec["taper"], base_r * 0.18, 3, spec["trunk_material"])
    # bracts: flattened clumps that spread along the wall, stay thin in y and shade by height
    targets = _targets(rng, spec)
    lo = min(t[1] for t in targets)
    hi = max(t[1] for t in targets)
    for x, z, size in targets:
        r = _pick(rng, spec["clump_radius"]) * size
        rz = r * spec["flatten"]
        ry = r * spec["depth"]
        y = 0.03 + rng.uniform(0.0, spec.get("depth_jitter", 0.12))
        f = (z - lo) / max(hi - lo, 1e-6)
        if rng.random() < spec.get("leaves", 0.15):
            mat = leaf_mat
        else:                                                 # paler at the top, deeper in the shade
            roll = rng.random()
            pale, deep = 0.15 + 0.35 * f, 0.35 - 0.25 * f
            mat = mats[2] if roll < pale else mats[0] if roll > 1.0 - deep else mats[1]
        clump(mb, rng, (x, y, z), r, rz, spec.get("jitter", 0.2), mat, ry=ry, detail=2, turn=0.0,
              roll=rng.uniform(-0.7, 0.7))
    for _ in range(int(spec.get("back", 0))):                 # a darker layer behind fills the gaps
        x = rng.uniform(-half, half)
        z = rng.uniform(lo, hi)
        r = _pick(rng, spec["clump_radius"]) * 0.9
        clump(mb, rng, (x, 0.01, z), r, r * spec["flatten"], spec.get("jitter", 0.2), mats[0],
              ry=r * spec["depth"], detail=2, turn=0.0, roll=rng.uniform(-0.7, 0.7))
    return mb


def climber_pieces(seed: int, table: dict | None) -> dict:
    """{piece name: MeshBuilder} for the climber variants of the style table."""
    if not table:
        return {}
    return {variant_name(v): climber_piece(table, seed, v) for v in range(int(table.get("variants", 2)))}
