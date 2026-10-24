"""Covered souks (prompt 31): the whitewashed barrel vaults over the main souks, drawn per tile.

The stretches come from `city/covered.py` (the rule the dresser reads too). Each segment between two
rings belongs to the tile holding its midpoint, each arch and lantern chain to the tile holding its
center; neighbouring tiles compute the shared rings from the same numbers, so the roof runs on across a
tile edge with no gap and no face drawn twice. A segment is the vault (intrados seen from the street,
extrados from the air, smooth along the ring), the impost bands it springs from (filled down to a lower
house, a lintel over a side opening) and, every few meters, a square light opening in the crown.
UVs are meters: along the souk and along the arc on the vault, along the souk and up on the bands.
"""
from __future__ import annotations

import numpy as np

from ..city.covered import owns, runs
from .builder import MeshBuilder, add_quads as _flat

VAULT = "lime_white"           # whitewashed plaster, inside and out
PAINT = ("door_red", "door_green")   # the painted corbels under the arches, as in the souks of Tunis


def covered_meshes(mb: MeshBuilder, covers, tile, chains: bool = True) -> None:
    """Every roof segment, arch and lantern chain of the covered souks this tile owns."""
    if covers is None:
        return
    for s in covers.all():
        mids = (s.p[:-1] + s.p[1:]) / 2.0
        mine = owns(tile, mids[:, 0], mids[:, 1])
        for i0, i1 in runs(mine):
            _segments(mb, s, i0, i1 + 2)          # segments i0..i1: stations i0..i1 + 1
        for x in s.arches:
            p = s.frame(x)[0]
            if owns(tile, p[0], p[1]):
                _arch(mb, s, x, covers.cfg)
        if chains:
            for x, hook in s.lanterns:
                p, _, t, z = s.frame(x)
                if owns(tile, p[0], p[1]):
                    _rod(mb, p, t, hook, z + s.shape.f - float(covers.cfg.get("arch_proud", 0.12)))


def _grid(mb: MeshBuilder, mat: str, pos: np.ndarray, nrm: np.ndarray, uv: np.ndarray, keep=None) -> None:
    """Quads over an (n, k) grid of shared vertices, each turned to face its vertex normals."""
    n, k = pos.shape[:2]
    idx = np.arange(n * k).reshape(n, k)
    quads = np.stack([idx[:-1, :-1], idx[1:, :-1], idx[1:, 1:], idx[:-1, 1:]], axis=-1)
    quads = quads.reshape(-1, 4) if keep is None else quads[keep]
    if not len(quads):
        return
    p, nn = pos.reshape(-1, 3), nrm.reshape(-1, 3)
    g = np.cross(p[quads[:, 2]] - p[quads[:, 0]], p[quads[:, 3]] - p[quads[:, 1]])
    flip = (g * nn[quads].sum(axis=1)).sum(axis=1) < 0
    quads[flip] = quads[flip][:, ::-1]
    used, inv = np.unique(quads, return_inverse=True)
    quads = inv.reshape(-1, 4)
    tris = np.concatenate([quads[:, [0, 1, 2]], quads[:, [0, 2, 3]]])
    mb.add(mat, p[used], nn[used], uv.reshape(-1, 2)[used], tris)


def _shell(mb: MeshBuilder, s, i0: int, i1: int, radius: float, sign: float, keep, edge: float | None = None):
    """One face of the vault over stations i0..i1-1: the ring points at `radius`, smooth normals turned
    down (sign -1, the intrados) or up (+1, the extrados), UVs along the souk and along the arc. With
    `edge`, the two end points move out to that across offset at the springing (the extrados reaches
    over the impost bands). Returns the (stations, ring) positions."""
    sh = s.shape
    across, up, ang = sh.ring(radius)
    if edge is not None:
        across, up = across.copy(), up.copy()
        across[0], across[-1], up[0], up[-1] = -edge, edge, 0.0, 0.0
    p, m, z, d = s.p[i0:i1], s.m[i0:i1], s.z[i0:i1], s.d[i0:i1]
    pos = np.concatenate([p[:, None, :] + m[:, None, :] * across[None, :, None],
                          (z[:, None] + up[None, :])[..., None]], axis=2)
    nhat = m / np.linalg.norm(m, axis=1)[:, None]
    nrm = np.concatenate([nhat[:, None, :] * np.sin(ang)[None, :, None],
                          np.broadcast_to(np.cos(ang)[None, :, None], (len(d), len(ang), 1))], axis=2) * sign
    uv = np.stack([np.broadcast_to(d[:, None], pos.shape[:2]),
                   np.broadcast_to(-radius * ang[None, :], pos.shape[:2])], axis=-1)
    _grid(mb, VAULT, pos, nrm, uv, keep)
    return pos


def _segments(mb: MeshBuilder, s, i0: int, i1: int) -> None:
    """Vault, impost bands and openings over stations i0..i1-1 (segments i0..i1-2)."""
    sh = s.shape
    c = sh.crown()
    keep = np.ones((i1 - i0 - 1, len(sh.s) - 1), dtype=bool)
    keep[s.holes[i0:i1 - 1], c] = False
    inner = _shell(mb, s, i0, i1, sh.r, -1.0, keep)
    outer = _shell(mb, s, i0, i1, sh.r + sh.t, 1.0, keep, sh.w + sh.bd)
    _holes(mb, s, i0, i1, inner, outer, c)
    _bands(mb, s, i0, i1)
    for end, j in ((0, 0), (len(s.d) - 1, i1 - i0 - 1)):
        if i0 <= end < i1:
            out = s.t[end] * (-1.0 if end == 0 else 1.0)
            quads = np.stack([inner[j, :-1], inner[j, 1:], outer[j, 1:], outer[j, :-1]], axis=1)
            _flat(mb, VAULT, quads, np.tile([out[0], out[1], 0.0], (len(quads), 1)))
            ends = []
            for side, sgn in ((0, -1.0), (1, 1.0)):
                a, b = s.p[end] + s.m[end] * sgn * sh.w, s.p[end] + s.m[end] * sgn * (sh.w + sh.bd)
                lo, hi = s.low[end, side], s.z[end]
                ends.append([[a[0], a[1], lo], [b[0], b[1], lo], [b[0], b[1], hi], [a[0], a[1], hi]])
            _flat(mb, VAULT, np.array(ends), np.tile([out[0], out[1], 0.0], (2, 1)))


def _holes(mb: MeshBuilder, s, i0: int, i1: int, inner: np.ndarray, outer: np.ndarray, c: int) -> None:
    """The light openings: the vault's thickness seen round each square hole, and a low curb round it
    on the roof (it keeps the rain out and shows the openings from the air)."""
    height, thick = s.shape.curb
    quads, toward = [], []
    for i in np.nonzero(s.holes[i0:i1 - 1])[0]:
        center = (inner[i, c] + inner[i + 1, c + 1]) / 2.0
        for (ia, ja), (ib, jb) in (((i, c), (i + 1, c)), ((i, c + 1), (i + 1, c + 1)),
                                   ((i, c), (i, c + 1)), ((i + 1, c), (i + 1, c + 1))):
            a, b = inner[ia, ja], inner[ib, jb]
            quads.append([a, b, outer[ib, jb], outer[ia, ja]])
            toward.append(center - (a + b) / 2.0)
        loop = [outer[i, c], outer[i + 1, c], outer[i + 1, c + 1], outer[i, c + 1]]
        top = max(q[2] for q in loop) + height
        mid = np.mean(loop, axis=0)
        out = [q[:2] + (q[:2] - mid[:2]) / np.linalg.norm(q[:2] - mid[:2]) * thick * np.sqrt(2.0) for q in loop]
        for e in range(4):
            a, b, oa, ob = loop[e], loop[(e + 1) % 4], out[e], out[(e + 1) % 4]
            side = (a[:2] + b[:2]) / 2.0 - mid[:2]
            quads.append([a, b, np.r_[b[:2], top], np.r_[a[:2], top]])
            toward.append(np.r_[-side, 0.0])
            quads.append([np.r_[oa, a[2] - 0.06], np.r_[ob, b[2] - 0.06], np.r_[ob, top], np.r_[oa, top]])
            toward.append(np.r_[side, 0.0])
            quads.append([np.r_[a[:2], top], np.r_[b[:2], top], np.r_[ob, top], np.r_[oa, top]])
            toward.append(np.array([0.0, 0.0, 1.0]))
    if quads:
        _flat(mb, VAULT, np.array(quads, dtype=float), np.array(toward))


def _bands(mb: MeshBuilder, s, i0: int, i1: int) -> None:
    """The impost bands the vault springs from: inner face and underside on both sides, and the outer
    face where it shows (over a lower house's roof or a side opening)."""
    sh = s.shape
    p, m, z, low, d = s.p[i0:i1], s.m[i0:i1], s.z[i0:i1], s.low[i0:i1], s.d[i0:i1]
    nhat = m / np.linalg.norm(m, axis=1)[:, None]
    n = len(d)
    for side, sgn in ((0, -1.0), (1, 1.0)):
        a = p + m * sgn * sh.w
        b = p + m * sgn * (sh.w + sh.bd)
        lo = low[:, side]
        face = np.stack([np.concatenate([a, lo[:, None]], axis=1), np.concatenate([a, z[:, None]], axis=1)], axis=1)
        nf = np.broadcast_to(np.concatenate([-sgn * nhat, np.zeros((n, 1))], axis=1)[:, None, :], (n, 2, 3))
        uvf = np.stack([np.broadcast_to(d[:, None], (n, 2)), -face[:, :, 2]], axis=-1)
        _grid(mb, VAULT, face, nf, uvf)
        under = np.stack([np.concatenate([a, lo[:, None]], axis=1), np.concatenate([b, lo[:, None]], axis=1)], axis=1)
        nu = np.broadcast_to(np.array([0.0, 0.0, -1.0]), (n, 2, 3))
        uvu = np.stack([np.broadcast_to(d[:, None], (n, 2)), np.broadcast_to([0.0, sh.bd], (n, 2))], axis=-1)
        _grid(mb, VAULT, under, nu, uvu)
        shows = (z - lo) > sh.band + 0.02                  # deeper than the band: a fill or a lintel
        seg = shows[:-1] | shows[1:]
        if seg.any():
            back = np.stack([np.concatenate([b, lo[:, None]], axis=1), np.concatenate([b, z[:, None]], axis=1)], axis=1)
            nb = np.broadcast_to(np.concatenate([sgn * nhat, np.zeros((n, 1))], axis=1)[:, None, :], (n, 2, 3))
            uvb = np.stack([np.broadcast_to(d[:, None], (n, 2)), -back[:, :, 2]], axis=-1)
            _grid(mb, VAULT, back, nb, uvb, seg[:, None])


def _arch(mb: MeshBuilder, s, x: float, cfg: dict) -> None:
    """A transverse arch standing `arch_proud` m below the vault, on a painted corbel at each foot;
    the first and last arches are the portals at the two ends of the stretch."""
    sh = s.shape
    aw, proud = float(cfg.get("arch_width", 0.45)), float(cfg.get("arch_proud", 0.12))
    e0, e1 = (x, x + aw) if x <= s.d[0] else (x - aw, x) if x >= s.d[-1] else (x - aw / 2, x + aw / 2)
    rings = []
    for e in (e0, e1):
        p, n, t, z = s.frame(e)
        rings.append((p, n, t, z, e))
    radius = sh.r - proud
    across, up, ang = sh.ring(radius)
    pos = np.array([[np.r_[p + n * a, z + u] for a, u in zip(across, up)] for p, n, t, z, e in rings])
    nrm = -np.array([[np.r_[n * np.sin(g), np.cos(g)] for g in ang] for p, n, t, z, e in rings])
    uv = np.array([[(e, -radius * g) for g in ang] for p, n, t, z, e in rings])
    _grid(mb, VAULT, pos, nrm, uv)                         # the soffit
    across0, up0, _ = sh.ring(sh.r)
    across1, up1, _ = sh.ring(sh.r - proud)
    quads, toward = [], []
    for (p, n, t, z, e), sgn in ((rings[0], -1.0), (rings[1], 1.0)):
        lo = [np.r_[p + n * a, z + u] for a, u in zip(across1, up1)]
        hi = [np.r_[p + n * a, z + u] for a, u in zip(across0, up0)]
        for j in range(len(lo) - 1):
            quads.append([lo[j], lo[j + 1], hi[j + 1], hi[j]])
            toward.append(np.r_[t * sgn, 0.0])
    _flat(mb, VAULT, np.array(quads), np.array(toward))
    red, green = (float(v) for v in cfg.get("corbel", (0.35, 0.25)))
    p0, n0, t0, z0, _ = rings[0]
    p1, n1, t1, z1, _ = rings[1]
    back = sh.half + 0.2                                   # into the house wall (0.15 m behind the street edge)
    for side in (-1.0, 1.0):
        for mat, top, bottom in ((PAINT[1], 0.0, -green), (PAINT[0], -green, -green - red)):
            quads, toward = [], []
            f0, f1 = p0 + n0 * side * (sh.w - proud), p1 + n1 * side * (sh.w - proud)
            b0, b1 = p0 + n0 * side * back, p1 + n1 * side * back
            lo0, lo1, hi0, hi1 = z0 + bottom, z1 + bottom, z0 + top, z1 + top
            quads.append([np.r_[f0, lo0], np.r_[f1, lo1], np.r_[f1, hi1], np.r_[f0, hi0]])
            toward.append(np.r_[-n0 * side, 0.0])
            quads.append([np.r_[f0, lo0], np.r_[b0, lo0], np.r_[b0, hi0], np.r_[f0, hi0]])
            toward.append(np.r_[-t0, 0.0])
            quads.append([np.r_[f1, lo1], np.r_[b1, lo1], np.r_[b1, hi1], np.r_[f1, hi1]])
            toward.append(np.r_[t0, 0.0])
            if mat == PAINT[0]:
                quads.append([np.r_[f0, lo0], np.r_[f1, lo1], np.r_[b1, lo1], np.r_[b0, lo0]])
                toward.append(np.array([0.0, 0.0, -1.0]))
            _flat(mb, mat, np.array(quads), np.array(toward))


def _rod(mb: MeshBuilder, p: np.ndarray, t: np.ndarray, z0: float, z1: float, w: float = 0.012) -> None:
    """The iron rod a lantern hangs from: a thin square post from its hook up to the arch."""
    n = np.array([-t[1], t[0]])
    corners = [p + (t * a + n * b) * w for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    quads, toward = [], []
    for j in range(4):
        a, b = corners[j], corners[(j + 1) % 4]
        quads.append([np.r_[a, z0], np.r_[b, z0], np.r_[b, z1], np.r_[a, z1]])
        toward.append(np.r_[(a + b) / 2 - p, 0.0])
    _flat(mb, "iron", np.array(quads), np.array(toward))
