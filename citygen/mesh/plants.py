"""Low-poly plant geometry shared by trees and climbers.

A clump is a jittered, smooth-shaded blob: an icosahedron (20 faces) for a tree crown, a
smaller octahedron (8 faces) for one bract of a climber. A tube is a tapered prism for a
trunk or a branch. Both work in generator axes: x east, y north, z up, meters.
"""
from __future__ import annotations

import math

import numpy as np

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

_OCT_VERTS = np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]],
                      dtype=np.float64)
_OCT_FACES = np.array([[0, 2, 4], [2, 1, 4], [1, 3, 4], [3, 0, 4],
                       [2, 0, 5], [1, 2, 5], [3, 1, 5], [0, 3, 5]])

# A bract: a flat diamond against the wall and one apex out of it (4 faces, open back).
_PYR_VERTS = np.array([[1, 0, 0], [-1, 0, 0], [0, 0, 1], [0, 0, -1], [0, 1, 0]], dtype=np.float64)
_PYR_FACES = np.array([[0, 4, 2], [2, 4, 1], [1, 4, 3], [3, 4, 0]])


def smooth_add(mb: MeshBuilder, material: str, pos: np.ndarray, faces: np.ndarray) -> None:
    """Add an indexed mesh with area-weighted smooth vertex normals."""
    n = np.cross(pos[faces[:, 1]] - pos[faces[:, 0]], pos[faces[:, 2]] - pos[faces[:, 0]])
    nrm = np.zeros_like(pos)
    for k in range(3):
        np.add.at(nrm, faces[:, k], n)
    length = np.linalg.norm(nrm, axis=1)
    nrm = nrm / np.where(length > 1e-12, length, 1.0)[:, None]
    uv = np.stack([pos[:, 0] + pos[:, 1], -pos[:, 2]], axis=1)
    mb.add(material, pos, nrm, uv, faces)


def clump(mb: MeshBuilder, rng, center, rx: float, rz: float, jitter: float, material: str,
          ry: float | None = None, detail: int = 1, turn: float | None = None, roll: float = 0.0) -> None:
    """One jittered clump; `ry` is its depth (default `rx`), detail 0 the cheap 8-face octahedron.

    `roll` turns the clump about the depth axis (y); `turn` about up (z), random when None.
    Wall pieces pass `turn=0` and a small `roll`, so they stay flat against the wall. Detail 2 is
    a 4-face bract: a diamond face against the wall with one apex out of it.
    """
    if detail == 2:
        verts, faces = _PYR_VERTS, _PYR_FACES
    else:
        verts, faces = (_ICO_VERTS, _ICO_FACES) if detail else (_OCT_VERTS, _OCT_FACES)
    radii = 1.0 + rng.uniform(-jitter, jitter, len(verts))
    if turn is None:
        turn = rng.uniform(0.0, 2 * math.pi)
    c, s = math.cos(turn), math.sin(turn)
    v = verts * radii[:, None] * np.array([rx, rx if ry is None else ry, rz])
    if roll:
        cr, sr = math.cos(roll), math.sin(roll)
        v = np.stack([v[:, 0] * cr + v[:, 2] * sr, v[:, 1], -v[:, 0] * sr + v[:, 2] * cr], axis=1)
    v = np.stack([v[:, 0] * c - v[:, 1] * s, v[:, 0] * s + v[:, 1] * c, v[:, 2]], axis=1)
    smooth_add(mb, material, v + np.asarray(center, dtype=np.float64), faces)


def tube(mb: MeshBuilder, p0, p1, r0: float, r1: float, sides: int, material: str, turn: float = 0.0) -> None:
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
    smooth_add(mb, material, pos, np.array(faces))
