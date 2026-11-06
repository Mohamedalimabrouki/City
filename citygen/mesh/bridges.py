"""What stands under a deck (prompt 62): arches, beams, piers, parapets, ramps and fords, from the `Bridge` record.

The ribbon on top is the street's or the road's (mesh/tile.py); everything else is here. A bridge is drawn whole by the
one tile that holds the middle of its axis, as a building is, on a city's plan or a country road's `TileContext.decks`.
UVs are meters (`add_quads`), flat on stone and concrete, smooth along a barrel and round a column. Heights come from
`Bridge.at`, so a parapet leans with a ramp; a foot is under the lowest ground along its wall (`_foot`), never a guess.

`Frame` turns stations and offsets into points and `sweep` draws a bar along the axis: most of a bridge is bars.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import shapely
from shapely.geometry import LineString, Polygon

from .builder import MeshBuilder, add_boxes, add_cap, add_quads, add_skirt, add_triangles, ribbon_edges
from .vaults import _grid

UP = np.array([0.0, 0.0, 1.0])
DOWN = -UP
WET = "quay_wet"
RED = "lighthouse_red"       # the bands of a ford's posts


class Frame:
    """A bridge's axis: points and heights by station s and by d, meters to the left of the axis."""

    def __init__(self, b, step: float):
        self.b, self.step = b, step
        self.deck = self.stations(*b.ends)
        p, seg, left, _right = ribbon_edges(b.axis.coords, 2.0)
        self.nodes, self.mitres = np.r_[0.0, np.cumsum(seg)], left - p      # the ribbon's corners, by station

    def stations(self, lo: float, hi: float) -> np.ndarray:
        """The stations from `lo` to `hi`: the record's and the axis's own, none further apart than `step`."""
        b = self.b
        kinks = shapely.line_locate_point(b.axis, shapely.points(np.asarray(b.axis.coords)[:, :2]))
        s = np.unique(np.round(np.r_[lo, hi, b.s[(b.s > lo) & (b.s < hi)], kinks[(kinks > lo) & (kinks < hi)]], 3))
        s = s[np.r_[True, np.diff(s) > 0.05]] if len(s) > 2 else s
        s[-1] = hi
        fill = [np.linspace(a, c, int(np.ceil((c - a) / self.step)) + 1)[1:-1] for a, c in zip(s[:-1], s[1:])]
        return np.sort(np.concatenate([s, *fill]))

    def points(self, s) -> np.ndarray:
        """Points of the axis; a station past an end is that end (shapely reads a negative one from the far end)."""
        s = np.clip(np.asarray(s, dtype=np.float64), 0.0, self.b.axis.length)
        return shapely.get_coordinates(shapely.line_interpolate_point(self.b.axis, s))

    def tangent(self, s) -> np.ndarray:
        s, end = np.asarray(s, dtype=np.float64), self.b.axis.length
        d = self.points(np.minimum(s + 0.5, end)) - self.points(np.maximum(s - 0.5, 0.0))
        return d / np.maximum(np.hypot(*d.T), 1e-9)[:, None]

    def left(self, s) -> np.ndarray:
        t = self.tangent(s)
        return np.stack([-t[:, 1], t[:, 0]], axis=1)

    def mitre(self, s) -> np.ndarray:
        """What a meter to the left moves a point at s: the ribbon's mitre at each corner of the axis, and between two
        corners both, in proportion, so an offset line runs on the ribbon's edge (`ribbon_edges`) and never folds."""
        s = np.asarray(s, dtype=np.float64)
        return np.stack([np.interp(s, self.nodes, self.mitres[:, i]) for i in (0, 1)], axis=-1)

    def off(self, s, d) -> np.ndarray:
        return self.points(s) + self.mitre(s) * np.reshape(d, (-1, 1))

    def top(self, s, d) -> np.ndarray:
        """Top of the ribbon `d` m left of the axis."""
        return self.b.at(*self.off(s, d).T)

    def at(self, s, d, z) -> np.ndarray:
        """The points (x, y, z)."""
        return np.column_stack([self.off(s, d), np.broadcast_to(z, np.shape(s))])

    def faces(self, s, sign: float) -> np.ndarray:
        """3D unit vectors along `sign` * left, one per piece between stations."""
        n = self.left(0.5 * (s[:-1] + s[1:])) * sign
        return np.column_stack([n, np.zeros(len(n))])

    def along(self, s, sign: float) -> np.ndarray:
        return np.append(self.tangent([s])[0] * sign, 0.0)

    def soffit(self, s) -> np.ndarray:
        return np.interp(s, self.b.s, self.b.z) - self.b.depth


def band(mb: MeshBuilder, mat: str, a: np.ndarray, b: np.ndarray, toward) -> None:
    """Flat quads between the polylines `a` and `b`, facing `toward`: a wall, its courses level."""
    quads = np.stack([a[:-1], a[1:], b[1:], b[:-1]], axis=1)
    keep = np.linalg.norm(np.cross(quads[:, 2] - quads[:, 0], quads[:, 3] - quads[:, 1]), axis=1) > 1e-6
    add_quads(mb, mat, quads[keep], np.broadcast_to(toward, (len(quads), 3))[keep])


def strip(mb: MeshBuilder, mat: str, a: np.ndarray, b: np.ndarray, s: np.ndarray, toward) -> None:
    """The same for a bar that follows the deck: UVs along it, so its stones run with the ramp, not across it."""
    quads = np.stack([a[:-1], a[1:], b[1:], b[:-1]], axis=1)
    n = np.cross(quads[:, 2] - quads[:, 0], quads[:, 3] - quads[:, 1])
    size = np.linalg.norm(n, axis=1)
    keep = size > 1e-6
    toward = np.broadcast_to(toward, (len(quads), 3))
    n = n / np.maximum(size, 1e-12)[:, None]
    back = (n * toward).sum(axis=1) < 0
    n[back] *= -1.0
    wide = np.linalg.norm(a - b, axis=1)
    uv = np.stack([np.stack([s[:-1], s[1:], s[1:], s[:-1]], axis=1),
                   np.stack([0.0 * wide[:-1], 0.0 * wide[1:], wide[1:], wide[:-1]], axis=1)], axis=-1)
    tris = np.array([[0, 1, 2], [0, 2, 3]])
    tris = (np.arange(int(keep.sum())) * 4)[:, None, None] + tris[None]
    flip = back[keep]
    tris[flip] = tris[flip][:, :, ::-1]
    mb.add(mat, quads[keep].reshape(-1, 3), np.repeat(n[keep], 4, axis=0), uv[keep].reshape(-1, 2), tris)


def sweep(mb: MeshBuilder, fr: Frame, mat: str, s, d0: float, d1: float, lo, hi, faces: str = "oitbe",
          deck: bool = True) -> None:
    """A bar along stations `s`, its outer face `d0` m left of the axis and its inner `d1`, from `lo` to `hi`: meters
    over the ribbon, or with `deck` False level heights. `faces` of it: o outer, i inner, t top, b bottom, e the ends."""
    s = np.asarray(s, dtype=np.float64)
    base0, base1 = (fr.top(s, d) if deck else 0.0 for d in (d0, d1))
    a0, a1 = fr.at(s, d0, base0 + lo), fr.at(s, d0, base0 + hi)
    b0, b1 = fr.at(s, d1, base1 + lo), fr.at(s, d1, base1 + hi)
    sign = 1.0 if d0 > d1 else -1.0
    if "o" in faces:
        strip(mb, mat, a1, a0, s, fr.faces(s, sign))
    if "i" in faces:
        strip(mb, mat, b1, b0, s, fr.faces(s, -sign))
    if "t" in faces:
        strip(mb, mat, a1, b1, s, UP)
    if "b" in faces:
        strip(mb, mat, a0, b0, s, DOWN)
    if "e" in faces:
        for i, way in ((0, -1.0), (-1, 1.0)):
            quad = np.stack([a1[i], b1[i], b0[i], a0[i]])[None]
            add_quads(mb, mat, quad, fr.along(s[i], way)[None])


def _posts(mb: MeshBuilder, fr: Frame, mat: str, s: np.ndarray, d: float, side: float, z0, z1) -> None:
    """Level boxes at stations `s`, centered `d` m left of the axis, square to it: a corner of the road never folds one."""
    t = fr.tangent(s)
    a = fr.off(s, d) - t * 0.5 * side + np.stack([t[:, 1], -t[:, 0]], axis=1) * 0.5 * side
    add_boxes(mb, a, t, 0.0, side, side, z0, z1, mat)


def _foot(ground, xy: np.ndarray, bury: float) -> float:
    """Under the lowest ground, as it is and as it is drawn, at the points `xy`."""
    x, y = xy.T
    return float(np.minimum(ground.height(x, y), ground.drawn(x, y)).min()) - bury


def foot_line(ground, fr: Frame, s: np.ndarray, d: float, bury: float) -> np.ndarray:
    """At each station, under the lowest ground along the line `d` m off the axis as far as its neighbors: a wall's foot
    between two stations is under all the ground between them."""
    t = np.unique(np.r_[np.arange(s[0], s[-1], 0.5), s])
    x, y = fr.off(t, d).T
    low = np.minimum(ground.height(x, y), ground.drawn(x, y))
    near = np.searchsorted(t, s)
    return np.array([low[near[max(i - 1, 0)]:near[min(i + 1, len(s) - 1)] + 1].min() for i in range(len(s))]) - bury


def _ramps(mb: MeshBuilder, ground, fr: Frame, mat: str, cfg: dict) -> None:
    """The retaining walls of the solid ramps, from the ribbon's edges down into the ground."""
    b, e = fr.b, 0.5 * fr.b.width
    bury = float(cfg["bury"])
    for lo, hi in ((b.ends[0], b.span[0]), (b.span[1], b.ends[1])):
        if hi - lo > 0.05:
            s = fr.stations(lo, hi)
            for d in (e, -e):
                band(mb, mat, fr.at(s, d, fr.top(s, d)), fr.at(s, d, foot_line(ground, fr, s, d, bury)),
                     fr.faces(s, np.sign(d)))


def _abutment(mb: MeshBuilder, ground, fr: Frame, mat: str, s: float, way: float, top: float, cfg: dict) -> None:
    """The face at the end of the open part, closing the hollow of a ramp, from `top` into the ground; `way` toward the
    opening."""
    e = 0.5 * fr.b.width
    across = np.linspace(-e, e, 9)
    bottom = _foot(ground, fr.off(np.full(9, s), across), float(cfg["bury"]))
    if top > bottom:
        high, low = fr.at([s, s], [e, -e], top), fr.at([s, s], [e, -e], bottom)
        add_quads(mb, mat, np.stack([high[0], high[1], low[1], low[0]])[None], fr.along(s, way)[None])


# --- stone ---------------------------------------------------------------------------------------------------------

@dataclass
class Arc:
    """A segment of a circle in (s, z): from (a, za) by the crown to (c, zc), round (cs, cz), r."""
    a: float
    za: float
    c: float
    zc: float
    cs: float
    cz: float
    r: float

    def angles(self) -> tuple:
        return (float(np.arctan2(self.a - self.cs, self.za - self.cz)),
                float(np.arctan2(self.c - self.cs, self.zc - self.cz)))

    def height(self, s) -> np.ndarray:
        return self.cz + np.sqrt(np.maximum(self.r ** 2 - (np.asarray(s) - self.cs) ** 2, 0.0))


def _circle(a: float, za: float, c: float, zc: float, crown: float) -> Arc:
    """The arc from (a, za) to (c, zc) through `crown` over their middle."""
    m = 0.5 * (a + c)
    ax, az, bx, bz = a - m, za - crown, c - m, zc - crown
    det = 2.0 * (ax * bz - az * bx)
    p, q = ax * ax + az * az, bx * bx + bz * bz
    cs, cz = (p * bz - q * az) / det, (q * ax - p * bx) / det
    return Arc(a, za, c, zc, m + cs, crown + cz, float(np.hypot(cs, cz)))


def spring_at(fr: Frame, s: float, cfg: dict) -> float:
    """Where an arch springs at station s: over the water or on the ground, under the soffit."""
    b = fr.b
    level = float(np.interp(s, b.s, b.floor))
    top = float(fr.soffit(s))
    if b.channel[0] - 1.0 <= s <= b.channel[1] + 1.0:
        least, part = (float(v) for v in cfg["spring_over"])
        level = max(level, b.water + max(least, part * (top - b.water)))
    return min(level, top - float(cfg["arch_gap"]))


def pier_thick(b, cfg: dict) -> float:
    ratio, least, most = (float(v) for v in cfg["pier"][:3])
    return float(np.clip(ratio * (b.span[1] - b.span[0]) / (len(b.piers) + 1), least, most))


def arches(fr: Frame, cfg: dict) -> list:
    """The bridge's arcs, one between each two of [span[0], *piers, span[1]], each under the soffit at every point."""
    b = fr.b
    edges = np.r_[b.span[0], b.piers, b.span[1]]
    half = 0.5 * pier_thick(b, cfg)
    spring = [spring_at(fr, float(s), cfg) for s in edges]
    out = []
    for i in range(len(edges) - 1):
        a = float(edges[i]) + (half if i else 0.0)
        c = float(edges[i + 1]) - (half if i < len(edges) - 2 else 0.0)
        least = max(spring[i], spring[i + 1]) + 0.1
        crown = max(float(fr.soffit(0.5 * (a + c))), least)
        t = np.linspace(a, c, 33)
        for _ in range(12):
            arc = _circle(a, spring[i], c, spring[i + 1], crown)
            over = float((arc.height(t) - fr.soffit(t)).max())
            if over <= 0.0 or crown <= least:
                break
            crown = max(crown - over - 1e-3, least)
        out.append(arc)
    return out


def stones(b) -> tuple:
    """(wall, dressed stone) of an arch bridge: warm by the old town, grey in a city, the land's own in the country."""
    if b.old:
        return "rampart", "stone_kasbah"
    return ("quay_wall", "curb") if b.road < 0 else ("plinth_stone", "curb")


def _joints(arc: Arc, length: float) -> np.ndarray:
    """Angles of the joints between an arc's stones, an odd number of them, so a keystone stands at the crown."""
    t0, t1 = arc.angles()
    n = max(int(round(abs(t1 - t0) * arc.r / length)), 3)
    return np.linspace(t0, t1, n + 1 + (n % 2 == 0))


def _on_arc(arc: Arc, t: np.ndarray, r: float) -> tuple:
    return arc.cs + r * np.sin(t), arc.cz + r * np.cos(t)


def _barrel(mb: MeshBuilder, fr: Frame, arc: Arc, t: np.ndarray, e: float, mat: str) -> None:
    """The arch's underside, seen from below: smooth along it, UVs in meters along the arc and across."""
    s, z = _on_arc(arc, t, arc.r)
    tan = fr.tangent(s)
    pos = np.stack([fr.at(s, -e, z), fr.at(s, e, z)], axis=1)
    nrm = np.column_stack([-tan * np.sin(t)[:, None], -np.cos(t)])
    uv = np.stack([np.broadcast_to((arc.r * (t - t[0]))[:, None], (len(t), 2)),
                   np.broadcast_to(np.array([-e, e]), (len(t), 2))], axis=-1)
    _grid(mb, mat, pos, np.stack([nrm, nrm], axis=1), uv)


def _ring(mb: MeshBuilder, fr: Frame, arc: Arc, t: np.ndarray, e: float, cfg: dict, mat: str) -> None:
    """The dressed stones round an arch on both faces, each a stone of its own, long and short by turns, the key the
    longest, proud of the wall, with a real joint between them."""
    depth, proud, _length, joint, short = (float(v) for v in cfg["ring"])
    depth = min(depth, fr.b.depth - float(cfg["string_course"][0]) - 0.03)
    n = len(t) - 1
    gap = 0.5 * joint / arc.r * np.sign(t[-1] - t[0])
    t0, t1 = t[:-1] + gap, t[1:] - gap
    r = arc.r + depth * np.where(np.arange(n) % 2 == (n // 2) % 2, 1.0, short)
    for way in (1.0, -1.0):
        rows = [_on_arc(arc, t0, arc.r), _on_arc(arc, t1, arc.r), _on_arc(arc, t1, r), _on_arc(arc, t0, r)]
        front = [fr.at(q[0], way * (e + proud), q[1]) for q in rows]
        back = [fr.at(q[0], way * e, q[1]) for q in rows]
        flat = fr.left(rows[0][0]) * way
        out = np.column_stack([flat, np.zeros(n)])
        add_quads(mb, mat, np.stack(front, axis=1), out)
        for i, j, q in ((2, 3, 0.5 * (t0 + t1)), (0, 3, t0 + np.pi / 2 * -np.sign(t[-1] - t[0])),
                        (2, 1, t1 + np.pi / 2 * np.sign(t[-1] - t[0]))):
            quads = np.stack([front[i], front[j], back[j], back[i]], axis=1)
            tan = fr.tangent(rows[0][0])
            toward = np.column_stack([tan * np.sin(q)[:, None], np.cos(q)])
            add_quads(mb, mat, quads, toward)


def _spandrels(mb: MeshBuilder, fr: Frame, arcs: list, mat: str, cfg: dict) -> None:
    """The two walls over the arches, from the arc and the pier's top up to the ribbon's edge."""
    b, e = fr.b, 0.5 * fr.b.width
    edge_s, edge_z = [], []
    for arc in arcs:
        t = _joints(arc, float(cfg["ring"][2]))
        s, z = _on_arc(arc, t, arc.r)
        edge_s.append(s)
        edge_z.append(z)
    edge_s, edge_z = np.concatenate(edge_s), np.concatenate(edge_z)
    s = np.unique(np.r_[edge_s, b.s[(b.s > b.span[0]) & (b.s < b.span[1])]])
    s = s[np.r_[True, np.diff(s) > 0.01]]
    under = np.interp(s, edge_s, edge_z)
    for d in (e, -e):
        band(mb, mat, fr.at(s, d, fr.top(s, d)), fr.at(s, d, under), fr.faces(s, np.sign(d)))


def _outline(half: float, long: float, nose: float) -> np.ndarray:
    """A pier's plan, (along the axis, across it), counter-clockwise, pointed at both ends across the axis."""
    return np.array([(half, -long), (half, long), (0.0, long + nose),
                     (-half, long), (-half, -long), (0.0, -long - nose)])


def _pier(mb: MeshBuilder, ground, fr: Frame, s: float, z: float, wall: str, trim: str, cfg: dict) -> None:
    """A stone pier at station s: pointed cutwaters on both faces, a capstone under the springing at `z`, the cutwaters'
    sloping caps up against the wall, its foot under the bed, dark and wet up from the water."""
    b, e = fr.b, 0.5 * fr.b.width
    half = 0.5 * pier_thick(b, cfg)
    proud = float(cfg["pier"][3])
    nose = float(cfg["nose"][0]) * 2.0 * half
    cap_h, cap_out = (float(v) for v in cfg["pier_cap"])
    c = fr.points([s])[0]
    t, n = fr.tangent([s])[0], fr.left([s])[0]

    def world(plan: np.ndarray) -> np.ndarray:
        return c + np.outer(plan[:, 0], t) + np.outer(plan[:, 1], n)

    ring = world(_outline(half, e + proud, nose))
    low = _foot(ground, np.vstack([ring, 0.5 * (ring + np.roll(ring, -1, axis=0)), c[None]]), float(cfg["bury"]))
    top = z - cap_h
    wet = b.water + float(cfg["wet_band"]) if not b.dry and float(np.interp(s, b.s, b.floor)) < b.water else low
    wet = min(wet, top)
    full = np.ones(6)
    if wet > low:
        add_skirt(mb, ring, full * wet, full * low, WET)
    if top > wet:
        add_skirt(mb, ring, full * top, full * wet, wall)
    cap = world(_outline(half + cap_out, e + proud + cap_out, nose + 1.8 * cap_out))
    add_skirt(mb, cap, full * z, full * top, trim)
    add_cap(mb, Polygon(cap), z, trim)
    add_cap(mb, Polygon(cap), top, trim, up=False)
    rise = float(cfg["nose"][1]) * nose
    tris = []
    for way in (1.0, -1.0):
        tip = world(np.array([(0.0, way * (e + proud + nose))]))[0]
        side = [world(np.array([(h, way * e)]))[0] for h in (half, -half)]
        corners = [np.append(q, z) for q in (side[0], tip, side[1])]
        apex = np.append(world(np.array([(0.0, way * e)]))[0], z + rise)
        tris += [(corners[0], corners[1], apex), (corners[1], corners[2], apex)] if way > 0 else \
                [(corners[1], corners[0], apex), (corners[2], corners[1], apex)]
    add_triangles(mb, np.array(tris), trim)


def _stone_parapets(mb: MeshBuilder, fr: Frame, wall: str, trim: str, cfg: dict) -> None:
    """Both parapets: wall, its coping, the band of stone at the deck, a stouter post at each end."""
    b, e, s = fr.b, 0.5 * fr.b.width, fr.deck
    h, thick = (float(v) for v in cfg["parapet"])
    cop_h, over = (float(v) for v in cfg["coping"])
    band_h, proud = (float(v) for v in cfg["string_course"])
    side, tall, top_h, top_out = (float(v) for v in cfg["end_post"])
    for d in (e, -e):
        sign = np.sign(d)
        sweep(mb, fr, wall, s, d, d - sign * thick, -0.06, h - cop_h, "oi")
        sweep(mb, fr, trim, s, d + sign * over, d - sign * (thick + over), h - cop_h, h, "oitbe")
        sweep(mb, fr, trim, s, d + sign * proud, d - sign * 0.02, -band_h, 0.0, "otbe")
        for mid in (b.ends[0] + 0.5 * side, b.ends[1] - 0.5 * side):
            at = np.array([mid])
            base = fr.top(at, d - sign * 0.5 * side)
            _posts(mb, fr, wall, at, d - sign * 0.5 * side, side, base - 0.2, base + tall)
            _posts(mb, fr, trim, at, d - sign * 0.5 * side, side + 2.0 * top_out, base + tall, base + tall + top_h)


def stone_bridge(mb: MeshBuilder, ground, fr: Frame, cfg: dict) -> None:
    b, e = fr.b, 0.5 * fr.b.width
    wall, trim = stones(b)
    arcs = arches(fr, cfg)
    proud = float(cfg["ring"][1])
    _ramps(mb, ground, fr, wall, cfg)
    for s, way, arc_z in ((b.span[0], 1.0, arcs[0].za), (b.span[1], -1.0, arcs[-1].zc)):
        _abutment(mb, ground, fr, wall, s, way, arc_z, cfg)
    for arc in arcs:
        t = _joints(arc, float(cfg["ring"][2]))
        _barrel(mb, fr, arc, t, e + proud, WET)
        _ring(mb, fr, arc, t, e, cfg, trim)
    _spandrels(mb, fr, arcs, wall, cfg)
    for k, s in enumerate(b.piers):
        _pier(mb, ground, fr, float(s), arcs[k].zc, wall, trim, cfg)
    _stone_parapets(mb, fr, wall, trim, cfg)


# --- concrete ------------------------------------------------------------------------------------------------------

def _slab(mb: MeshBuilder, fr: Frame, cfg: dict) -> None:
    """The deck over the open part: fascia girders at its edges, a shadow line between them and the kerb, the slab's
    soffit in the dark and girders under it."""
    b, e = fr.b, 0.5 * fr.b.width
    s = fr.stations(*b.span)
    wide, under, apart = (float(v) for v in cfg["girder"])
    high, deep = (float(v) for v in cfg["shadow"])
    for d in (e, -e):
        sign = np.sign(d)
        sweep(mb, fr, "concrete", s, d, d - sign * wide, -b.depth, -high, "oitb")
        sweep(mb, fr, "concrete_dark", s, d - sign * deep, d - sign * wide, -high, 0.0, "o")
    inner = e - 0.5 * wide
    n = max(int(round(2.0 * inner / apart)) - 1, 0)
    for d in np.linspace(-inner, inner, n + 2)[1:-1]:
        sweep(mb, fr, "concrete_dark", s, d + 0.5 * wide, d - 0.5 * wide, -b.depth, -b.depth + under, "oib")
    soffit = fr.soffit(s) + under
    band(mb, "concrete_dark", fr.at(s, e, soffit), fr.at(s, -e, soffit), DOWN)


def _concrete_abutments(mb: MeshBuilder, ground, fr: Frame, cfg: dict) -> None:
    """A wall at each end of the open part with its seat under the girders."""
    b, e = fr.b, 0.5 * fr.b.width
    out, high = (float(v) for v in cfg["seat"])
    for s, way in ((b.span[0], 1.0), (b.span[1], -1.0)):
        z = float(fr.soffit(s))
        _abutment(mb, ground, fr, "concrete", s, way, z, cfg)
        ss = np.sort([s, s + way * out])
        sweep(mb, fr, "concrete_dark", ss, e, -e, z - high, z, deck=False)


def _column(mb: MeshBuilder, mat: str, c: np.ndarray, r: float, z0: float, z1: float, sides: int) -> None:
    """A round column, smooth round."""
    a = np.linspace(0.0, 2.0 * np.pi, sides + 1)
    ring = np.column_stack([np.cos(a), np.sin(a)])
    n = np.column_stack([ring, np.zeros(sides + 1)])
    pos = np.stack([np.column_stack([c + r * ring, np.full(sides + 1, z)]) for z in (z0, z1)], axis=1)
    uv = np.stack([np.broadcast_to((r * a)[:, None], (sides + 1, 2)),
                   np.broadcast_to(np.array([-z0, -z1]), (sides + 1, 2))], axis=-1)
    _grid(mb, mat, pos, np.stack([n, n], axis=1), uv)


def _concrete_pier(mb: MeshBuilder, ground, fr: Frame, s: float, cfg: dict) -> None:
    """A cap beam on round columns on a low bridge, on a wall with round ends where it stands tall."""
    b, e = fr.b, 0.5 * fr.b.width
    z = float(fr.soffit(s))
    cap_h, cap_t, short = (float(v) for v in cfg["cap_beam"])
    sweep(mb, fr, "concrete_dark", [s - 0.5 * cap_t, s + 0.5 * cap_t], e - short, short - e, z - cap_h, z, deck=False)
    below = z - cap_h
    floor = float(np.interp(s, b.s, b.floor))
    wet = None if b.dry or floor >= b.water else b.water + float(cfg["wet_band"])
    if z - max(floor, b.water) > float(cfg["pier_tall"]):
        thick, in_from = (float(v) for v in cfg["wall_pier"])
        line = LineString(fr.off([s, s], [in_from + 0.5 * thick - e, e - in_from - 0.5 * thick]))
        ring = np.asarray(line.buffer(0.5 * thick, quad_segs=3).exterior.coords)[:-1, :2]
        ring = ring[::-1] if Polygon(ring).exterior.is_ccw is False else ring
        low = _foot(ground, ring, float(cfg["bury"]))
        full = np.ones(len(ring))
        if wet is not None:
            add_skirt(mb, ring, full * wet, full * low, "concrete_dark")
        add_skirt(mb, ring, full * below, full * (low if wet is None else wet), "concrete")
        return
    r, apart, in_from = (float(v) for v in cfg["column"])
    reach = e - in_from
    n = max(int(np.ceil(2.0 * reach / apart)) + 1, 2)
    sides = int(cfg["arc_sides"])
    for d in np.linspace(-reach, reach, n):
        c = fr.off([s], d)[0]
        a = np.linspace(0.0, 2.0 * np.pi, 7)
        low = _foot(ground, c + r * np.column_stack([np.cos(a), np.sin(a)]), float(cfg["bury"]))
        if wet is not None:
            _column(mb, "concrete_dark", c, r, low, wet, sides)
        _column(mb, "concrete", c, r, low if wet is None else wet, below, sides)


def _concrete_parapets(mb: MeshBuilder, fr: Frame, cfg: dict) -> None:
    """A low kerb with a rail of posts and two continuous bars, white in a city, iron on a country road, a block at each
    end."""
    b, e, s = fr.b, 0.5 * fr.b.width, fr.deck
    high, wide = (float(v) for v in cfg["kerb"])
    top, mid, rail_w, rail_d = (float(v) for v in cfg["rail"])
    apart, post = (float(v) for v in cfg["rail_post"])
    side, tall = (float(v) for v in cfg["concrete_end"])
    mat = "iron" if b.road >= 0 else "railing_white"
    room = b.ends[1] - b.ends[0] - 2.0 * side
    n = max(int(round(room / apart)), 1)
    stops = b.ends[0] + side + room * np.arange(n + 1) / n
    for d in (e, -e):
        sign = np.sign(d)
        sweep(mb, fr, "concrete", s, d, d - sign * wide, 0.0, high, "oitb")
        mid_d = d - sign * 0.5 * wide
        run = fr.stations(b.ends[0] + side, b.ends[1] - side)
        for z in (top, mid):
            sweep(mb, fr, mat, run, mid_d + sign * 0.5 * rail_w, mid_d - sign * 0.5 * rail_w, z - rail_d, z, "oitb")
        base = fr.top(stops, mid_d)
        _posts(mb, fr, mat, stops, mid_d, post, base + high - 0.02, base + top)
        for mid in (b.ends[0] + 0.5 * side, b.ends[1] - 0.5 * side):
            at = np.array([mid])
            z = fr.top(at, d - sign * 0.5 * side)
            _posts(mb, fr, "concrete", at, d - sign * 0.5 * side, side, z - 0.2, z + tall)


def concrete_bridge(mb: MeshBuilder, ground, fr: Frame, cfg: dict) -> None:
    _ramps(mb, ground, fr, "concrete", cfg)
    _concrete_abutments(mb, ground, fr, cfg)
    _slab(mb, fr, cfg)
    for s in fr.b.piers:
        _concrete_pier(mb, ground, fr, float(s), cfg)
    _concrete_parapets(mb, fr, cfg)


# --- a ford, sidewalks ---------------------------------------------------------------------------------------------

def _ford_posts(mb: MeshBuilder, fr: Frame, cfg: dict) -> None:
    """White marker posts with red bands along both edges over the channel, a tall banded gauge at its two ends."""
    b, e = fr.b, 0.5 * fr.b.width
    apart, side, tall, inset = (float(v) for v in cfg["ford_post"])
    first, band_h, gap = (float(v) for v in cfg["ford_bands"])
    wide, high, each = (float(v) for v in cfg["ford_gauge"])
    a, c = b.channel
    n = max(int(round((c - a) / apart)), 1)
    s = a + (c - a) * np.arange(1, n) / n
    for d in (e - inset, inset - e):
        if len(s):
            base = fr.top(s, d)
            _posts(mb, fr, "railing_white", s, d, side, base, base + first)
            _posts(mb, fr, RED, s, d, side, base + first, base + first + band_h)
            _posts(mb, fr, "railing_white", s, d, side, base + first + band_h, base + first + band_h + gap)
            _posts(mb, fr, RED, s, d, side, base + first + band_h + gap, base + tall)
        ends = np.array([a, c])
        base = fr.top(ends, d)
        for k in range(int(round(high / each))):
            _posts(mb, fr, RED if k % 2 else "railing_white", ends, d, wide, base + k * each, base + (k + 1) * each)


def ford(mb: MeshBuilder, ground, fr: Frame, cfg: dict) -> None:
    """A slab's two side faces down into the gravel, and its posts."""
    e, s = 0.5 * fr.b.width, fr.deck
    for d in (e, -e):
        band(mb, "concrete", fr.at(s, d, fr.top(s, d)), fr.at(s, d, foot_line(ground, fr, s, d, float(cfg["bury"]))),
             fr.faces(s, np.sign(d)))
    _ford_posts(mb, fr, cfg)


def _sidewalks(mb: MeshBuilder, fr: Frame, cfg: dict, curb: float) -> None:
    """A raised sidewalk along each parapet, with its curb."""
    e, s = 0.5 * fr.b.width, fr.deck
    wide, curb_w = (float(v) for v in cfg["sidewalk"])
    thick = float(cfg["kerb"][1] if fr.b.kind == "beam" else cfg["parapet"][1])
    for d in (e, -e):
        sign = np.sign(d)
        edge = d - sign * (thick + wide)
        sweep(mb, fr, "sidewalk", s, d - sign * thick, edge + sign * curb_w, 0.0, curb, "t")
        sweep(mb, fr, "curb", s, edge + sign * curb_w, edge, 0.0, curb, "ite")


def ramp_only(mb: MeshBuilder, ground, fr: Frame, cfg: dict) -> None:
    """What is left of a road's bridge past the wider road it forks off: a solid ramp with its parapets."""
    b = fr.b
    _ramps(mb, ground, fr, stones(b)[0] if b.kind == "arch" else "concrete", cfg)
    if b.kind == "arch":
        _stone_parapets(mb, fr, *stones(b), cfg)
    else:
        _concrete_parapets(mb, fr, cfg)


DRAW = {"arch": stone_bridge, "beam": concrete_bridge, "ford": ford}


def structure(mb: MeshBuilder, ground, b, style: dict) -> None:
    """All that stands under bridge `b`'s ribbon and along it."""
    cfg = style["bridges"]
    fr = Frame(b, float(cfg["step"]))
    (DRAW[b.kind] if b.span[1] > b.span[0] or b.kind == "ford" else ramp_only)(mb, ground, fr, cfg)
    if b.road < 0 and b.width >= float(cfg["sidewalk_from"]):
        _sidewalks(mb, fr, cfg, float(style["streets"]["curb_height"]))


def owned(tc, tile) -> list:
    """The bridges and fords whose axis has its middle on this tile, city and country."""
    x0, y0, x1, y1 = tile.bounds
    found = [b for plan in tc.plans for b in getattr(plan, "bridges", ())]
    if tc.road_tree is not None:
        found += [b for k in tc.road_tree.query(tile, predicate="intersects") for b in tc.decks(int(k))]

    def mine(b) -> bool:
        p = b.axis.interpolate(0.5 * (b.ends[0] + b.ends[1]))
        return x0 <= p.x < x1 and y0 <= p.y < y1

    return [b for b in (b.standing() for b in found) if b is not None and mine(b)]


def bridge_meshes(mb: MeshBuilder, tc, tile) -> None:
    for b in owned(tc, tile):
        structure(mb, tc.ground, b, tc.world.style)


# --- lod1 ----------------------------------------------------------------------------------------------------------

def bridge_box(mb: MeshBuilder, ground, b, cfg: dict) -> None:
    """A low box under the ribbon: parapet-high walls down to the soffit, or `ground` on the ramps, plain piers. `ground`
    is the terrain this box stands on, the lod1 terrain (`mesh/lod.LodGround`), coarser than the full tiles'."""
    fr = Frame(b, float(cfg["step"]) * 2.0)
    mat = {"arch": stones(b)[0], "beam": "concrete", "ford": "concrete"}[b.kind]
    e, s = 0.5 * b.width, np.unique(np.r_[fr.deck, b.span[0] + 0.02, b.span[1] - 0.02])    # a wall's foot steps at an abutment
    rise = 0.0 if b.kind == "ford" else float(cfg["parapet"][0])
    bury = float(cfg["bury"])
    openly = (s > b.span[0] + 0.01) & (s < b.span[1] - 0.01) & (b.kind != "ford")
    for d in (e, -e):
        top = fr.top(s, d)
        under = np.where(openly, top - b.depth, np.minimum(foot_line(ground, fr, s, d, bury), top))
        band(mb, mat, fr.at(s, d, top + rise), fr.at(s, d, under), fr.faces(s, np.sign(d)))
    if b.kind != "ford" and b.span[1] > b.span[0]:
        o = fr.stations(*b.span)
        band(mb, mat, fr.at(o, e, fr.top(o, e) - b.depth), fr.at(o, -e, fr.top(o, -e) - b.depth), DOWN)
    if len(b.piers):
        thick = float(cfg["wall_pier"][0])
        t = fr.tangent(b.piers)
        right = np.stack([t[:, 1], -t[:, 0]], axis=1)
        a = fr.points(b.piers) + right * e - t * 0.5 * thick
        lows = [_foot(ground, fr.off(np.full(5, float(p)), np.linspace(-e, e, 5)), bury) for p in b.piers]
        tops = fr.soffit(b.piers)
        add_boxes(mb, a, t, 0.0, thick, b.width, np.minimum(lows, tops), tops, mat)


def bridge_boxes(mb: MeshBuilder, tc, tile, ground) -> None:
    for b in owned(tc, tile):
        bridge_box(mb, ground, b, tc.world.style["bridges"])
