"""Interior meshes (SPEC 6c "Walls", prompt 48): the walls of a dwelling as solids with real holes.

Outer faces are the tile's own wall quads (`mesh.tile.building_walls`: the footprint ring and court rings
from 0.6 m under the lowest ground, the plinth on the tile's frontage, the same meter UVs), with a hole
wherever a facade piece or a court opening stands. Inner faces are the edges of each room's floor less the
partitions round it (`free`: the room less every walled neighbour grown by half a partition), so the
inner faces of exterior walls, court walls and partitions are drawn alike, each seen from its own room,
and partitions meet with clean mitres and never z-fight. Every opening cuts the faces of its wall on both
sides and gets its jambs, sill and head (`reveal`); inner and court doors get a wooden frame and leaves
(stream `doors`), a bortal's court arches a horseshoe head and a stone band. The roof rooms' walls (stair
room, menzah) are faces too, so their doors and windows are cut alike (prompt 49).

Prompt 49 adds the stairs (`stairs_mesh`: the solids, rails and ladders of `stairs.parts`) and `overheads`,
what a person on a stair may hit; the slabs, ceilings, roof deck and court are `floors.py`'s.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

import numpy as np
from shapely.geometry import Point, Polygon, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from shapely.strtree import STRtree

from ..city.geo import polygons
from ..city.massing import outline
from ..mesh.builder import _QUAD, _horseshoe, add_arch, add_cap, add_quads, extrude, triangulate
from ..mesh.tile import (PLINTH_KINDS, building_walls, frontage_inputs, ring_heights, street_frontage)
from ..rng import stream
from . import rooms as R
from .layout import TRADITIONAL

FACADE = ("door", "window", "balcony", "shop")    # openings in the exterior walls (a piece stands in each)
GLAZED = ("window", "court_window", "inner_window", "balcony")   # openings with a glazed casement
CASED = {"inner": 1, "court_door": 2}            # openings with a wooden frame, and their leaves
WAYS = ("couloir", "hall", "palier", "droj", "skifa", "bortal", R.COURT)   # a door swings away from these
PARALLEL = math.cos(math.radians(2.0))           # a face this near the opening's wall direction carries it
NEAR = 0.03          # meters: ... when it lies this near one of the wall's two faces
DEEP = 0.15          # meters: or this much beyond it, where the plan leaves a sliver (the wall is thicker)
GAP = 0.005          # meters between a leaf and its frame, and the tolerance of the checks


@dataclass
class Face:
    """A vertical wall face from a to b, seen from its right (normal (dy, -dx)), z0 to z1; u = u0 + meters
    from a, v = -(z - z_ref). `floor` -1 for an outer face; `dado` the top of its zellige band."""
    a: np.ndarray
    b: np.ndarray
    z0: float
    z1: float
    mat: str
    u0: float
    z_ref: float
    floor: int
    dado: float | None = None
    holes: list = field(default_factory=list)    # polygons in (s, z), s meters from a

    @property
    def length(self) -> float:
        return float(np.hypot(*(self.b - self.a)))


@dataclass
class Hole:
    """The hole an opening cut: its center on the front face (the outer face of an exterior or court wall,
    the other room's side of a partition), the width and z range cut there, and the width cut on the room
    side (`back`); `depth` (d0, d1) the wall's two faces from the opening's center along its front."""
    id: int
    kind: str
    x: float
    y: float
    yaw: float
    width: float
    z0: float
    z1: float
    back: float
    depth: tuple
    floor: int


class Recorder:
    """Stands in for a MeshBuilder to keep the quads `building_walls` adds."""

    def __init__(self):
        self.chunks: list = []

    def add(self, material, pos, nrm, uv, tris, col=None) -> None:
        self.chunks.append((material, np.asarray(pos, dtype=np.float64).reshape(-1, 3),
                            np.asarray(uv, dtype=np.float64).reshape(-1, 2)))


def walls_mesh(mb, interior, outside, style: dict) -> list:
    """Exterior, court and partition walls of `interior` into `mb`, with a hole for every opening; returns
    the `Hole`s cut. The facade pieces stay instances, standing in their holes."""
    cfg = style.get("interiors", {})
    walls_cfg, ops = cfg.get("walls", {}), cfg.get("openings", {})
    from .floors import roof_faces
    faces = outer_faces(interior, outside, style) + inner_faces(interior, walls_cfg) + roof_faces(interior, outside, style)
    index = _FaceIndex(faces)
    holes = []
    for o in interior.openings:
        if not walled_in(interior, o, ops):
            continue
        o, hole = cut(index, interior, o, ops)
        if hole is not None:
            holes.append(hole)
            dress(mb, interior, o, hole, ops)
    for f in faces:
        draw(mb, f)
    balustrades(mb, interior, float(walls_cfg.get("balustrade", 0.95)))
    return holes


def walled_in(interior, o, ops: dict) -> bool:
    """True for an opening the walls cut: not a skylight, not an iron balcony (`railings`: a railing in
    front of the windows, on a solid wall). A roof room's door and windows are (prompt 49)."""
    return o.kind != "skylight" and not (o.kind == "balcony" and o.piece in ops.get("railings", ()))


# --- faces ------------------------------------------------------------------------------------------
def outer_faces(interior, outside, style: dict) -> list:
    """The tile's outer wall quads of the building, as `Face`s: same rings, ground, plinth and frontage."""
    b, plan = outside.b, outside.plan
    rec = Recorder()
    plinth = frontage = None
    spec = style.get("plinth", {}).get(outside.district)
    if b.kind in PLINTH_KINDS and spec is not None:
        plinth = (str(spec["material"]), float(spec["height"]))
        walk_width, reach = frontage_inputs(plan)
        streets = STRtree([s.line for s in plan.streets]) if plan.streets else None
        frontage = street_frontage(outline(b), plan, walk_width, streets, reach)
    under = ring_heights(outside.ctx.ground, [b])[0]
    building_walls(rec, b, outside.ctx.ground.height, plinth=plinth, frontage=frontage, roofs=outside.roofs,
                   ground_z=under)
    out = []
    for mat, pos, uv in rec.chunks:
        for q in range(len(pos) // 4):
            p, t = pos[4 * q:4 * q + 4], uv[4 * q:4 * q + 4]
            out.append(Face(p[0, :2].copy(), p[1, :2].copy(), float(p[0, 2]), float(p[2, 2]), mat,
                            float(t[0, 0]), float(p[0, 2] + t[0, 1]), -1))
    return out


def inner_faces(interior, walls_cfg: dict) -> list:
    """The faces of every room of every storey, seen from the room: the edges of its `free` floor, but not
    the edges it shares with a room it has no wall to (a light well's gallery: a balustrade)."""
    half = interior.walls["partition"] / 2
    dado_rooms = tuple(walls_cfg.get("dado_rooms", ()))
    dado = float(walls_cfg.get("dado", 1.2))
    traditional = interior.layout in TRADITIONAL
    out = []
    for f in range(interior.floors):
        for room, parts, loose in free(interior, f, half):
            top = room.z + dado if traditional and room.type in dado_rooms else None
            for part in parts:
                for ring in (part.exterior, *part.interiors):
                    out += _ring_faces(np.asarray(ring.coords)[:, :2], room, top, loose)
    return out


def _ring_faces(ring: np.ndarray, room, dado, loose) -> list:
    """Faces along one ring of a counter-clockwise room part (holes clockwise), each seen from inside: the
    ring is walked backwards so the room lies on each face's right."""
    pts = ring[::-1]
    out, u = [], 0.0
    for a, b in zip(pts[:-1], pts[1:]):
        length = float(np.hypot(*(b - a)))
        if length < 1e-6:
            continue
        mid = Point(*((a + b) / 2))
        if loose is None or loose.distance(mid) > 1e-3:
            out.append(Face(a.copy(), b.copy(), room.z, room.z + room.height, "plaster_inner", u, room.z,
                            room.floor, dado))
        u += length
    return out


def free(interior, f: int, half: float) -> list:
    """(room, its free parts, the union of the neighbours it has no wall to or None) for every room of
    storey f: the room's polygon less each walled neighbour grown by half a partition (mitre joins)."""
    rooms = [r for r in interior.rooms if r.floor == f and not R.is_court(r)]
    if not rooms:
        return []
    tree = STRtree([r.polygon for r in rooms])
    grown = {}
    out = []
    for r in rooms:
        cut, loose = [], []
        for j in tree.query(r.polygon, predicate="dwithin", distance=1e-3).tolist():
            o = rooms[j]
            if o is r:
                continue
            if not walled(r, o):
                loose.append(o.polygon)
                continue
            if o.id not in grown:
                grown[o.id] = o.polygon.buffer(half, join_style="mitre")
            cut.append(grown[o.id])
        poly = r.polygon.difference(unary_union(cut)) if cut else r.polygon
        parts = [orient(p.simplify(1e-4), 1.0) for p in polygons(poly) if p.area > 0.01]
        out.append((r, [p for p in parts if not p.is_empty], unary_union(loose) if loose else None))
    return out


def walled(a, b) -> bool:
    """Rooms parted by a partition: all but a covered court's light well and its gallery (a balustrade)."""
    return {a.type, b.type} != {"well", "bortal"}


def partitions(interior, f: int) -> object:
    """The partitions of storey f: its floor less every room's free parts and the balustrade's lines."""
    half = interior.walls["partition"] / 2
    parts = [p for _, ps, _ in free(interior, f, half) for p in ps]
    return interior.storeys[f].polygon.difference(unary_union(parts)) if parts else interior.storeys[f].polygon


class _FaceIndex:
    """Faces as arrays, to find those of an opening's wall."""

    def __init__(self, faces: list):
        self.faces = faces
        self.a = np.array([f.a for f in faces]).reshape(-1, 2)
        self.b = np.array([f.b for f in faces]).reshape(-1, 2)
        d = self.b - self.a
        self.len = np.maximum(np.hypot(d[:, 0], d[:, 1]), 1e-12)
        self.n = np.stack([d[:, 1], -d[:, 0]], axis=1) / self.len[:, None]
        self.z0 = np.array([f.z0 for f in faces])
        self.z1 = np.array([f.z1 for f in faces])


# --- holes ------------------------------------------------------------------------------------------
def frame_of(o) -> tuple:
    """(center, front, along) of an opening: front (-sin yaw, cos yaw) out of its room, along its wall."""
    return (np.array([o.x, o.y]), np.array([-math.sin(o.yaw), math.cos(o.yaw)]),
            np.array([math.cos(o.yaw), math.sin(o.yaw)]))


def depths(interior, o) -> tuple:
    """The two faces of the opening's wall, meters from its center along its front: an exterior wall from
    its inner face to the footprint ring, a court wall from the room to the court, a partition both ways."""
    if o.floor >= interior.floors:                     # a roof room's wall (prompt 49), from its outer face
        return -interior.walls.get("roof", 0.2), 0.0
    if o.kind in FACADE:
        return -interior.walls["exterior"], 0.0
    if o.wall is not None:
        return -interior.walls["court"], 0.0
    half = interior.walls["partition"] / 2
    return -half, half


def outline_of(o, ops: dict) -> tuple:
    """The hole's outline in (t along the wall from its center, z), and the half width cut: a horseshoe
    for a bortal's arch on the court, the clear opening plus the frame for a cased door, else a rectangle."""
    if o.kind == "arch" and o.wall is not None:
        shape = _horseshoe(o.width, o.z1 - o.z0, 6)
        return Polygon(np.column_stack([shape[:, 0], o.z0 + shape[:, 1]])), float(np.abs(shape[:, 0]).max())
    grow = float(ops.get("casing", 0.05)) if o.kind in CASED else 0.0
    half = o.width / 2 + grow
    return box(-half, o.z0, half, o.z1 + grow), half


def passage(o) -> bool:
    """An open passage between two rooms (a hall's arch, a skifa's past its baffle): it may span the whole
    edge the rooms share, so it is cut only where both have a face (`cut`)."""
    return o.kind == "arch" and o.wall is None


def carriers(index: _FaceIndex, interior, o, ops: dict) -> tuple:
    """(mask of the faces carrying the opening's hole, their depth, their t span, the outline, its half
    width): faces parallel to its wall, on one of the wall's two faces, overlapping the hole."""
    c, front, along = frame_of(o)
    lo, hi = depths(interior, o)
    shape, half = outline_of(o, ops)
    z0, z1 = shape.bounds[1], shape.bounds[3]
    da, db = (index.a - c) @ front, (index.b - c) @ front
    ta, tb = (index.a - c) @ along, (index.b - c) @ along
    at = np.clip(-ta / np.where(np.abs(tb - ta) > 1e-9, tb - ta, 1.0), 0.0, 1.0)
    dc = da + (db - da) * at                         # the face's depth across from the opening's center
    near_lo, near_hi = (dc > lo - DEEP) & (dc < lo + NEAR), (dc > hi - NEAR) & (dc < hi + DEEP)
    on = ((np.abs(index.n @ front) >= PARALLEL) & (near_lo | near_hi)
          & (np.minimum(ta, tb) < half - GAP) & (np.maximum(ta, tb) > -half + GAP)
          & (index.z0 < z1 - GAP) & (index.z1 > z0 + GAP))
    side = np.abs(dc - hi) < np.abs(dc - lo)
    for m, nominal in ((on & ~side, lo), (on & side, hi)):   # each side: its faces nearest the nominal one
        if m.any():
            best = np.abs(dc[m] - nominal).min()
            on &= ~m | (np.abs(np.abs(dc - nominal) - best) < GAP)
    return on, dc, side, np.minimum(ta, tb), np.maximum(ta, tb), shape, half


def cut(index: _FaceIndex, interior, o, ops: dict) -> tuple:
    """Cut the opening's hole in every face of its wall (both sides); (the opening as cut, its `Hole`), or
    (o, None) when no face carries it. A passage is first narrowed to the span faced on both sides."""
    on, da, side, t0, t1, shape, half = carriers(index, interior, o, ops)
    if passage(o) and on[side].any() and on[~side].any():
        both = [_around(list(zip(t0[on & m], t1[on & m]))) for m in (side, ~side)]
        lo_t, hi_t = max(-half, both[0][0], both[1][0]), min(half, both[0][1], both[1][1])
        if hi_t - lo_t > 0.1 and (lo_t > -half + 1e-6 or hi_t < half - 1e-6):
            c, _, along = frame_of(o)
            mid = (lo_t + hi_t) / 2
            o = replace(o, x=float(c[0] + along[0] * mid), y=float(c[1] + along[1] * mid), width=hi_t - lo_t)
            on, da, side, t0, t1, shape, half = carriers(index, interior, o, ops)
    if not on.any():
        return o, None
    c, front, along = frame_of(o)
    lo, hi = depths(interior, o)
    pts = np.asarray(shape.exterior.coords)
    for k in np.flatnonzero(on).tolist():
        face = index.faces[k]
        d = (face.b - face.a) / index.len[k]
        sign = float(d @ along)                      # +1: the face runs along t, -1: against it
        s0 = float((c - face.a) @ d)
        face.holes.append(Polygon(np.column_stack([s0 + sign * pts[:, 0], pts[:, 1]])))
    spans = {True: [], False: []}
    for k in np.flatnonzero(on).tolist():
        face = index.faces[k]
        spans[bool(side[k])].append((max(t0[k], -half), min(t1[k], half), float(da[k]),
                                     max(face.z0, shape.bounds[1]), min(face.z1, shape.bounds[3])))
    front_side = spans[True] or spans[False]
    first, last, width = _cover(front_side)
    mid = (first + last) / 2
    d0 = min((s[2] for s in spans[False]), default=lo)
    d1 = max((s[2] for s in spans[True]), default=hi)
    return o, Hole(o.id, o.kind, float(c[0] + along[0] * mid), float(c[1] + along[1] * mid), o.yaw, width,
                   min(s[3] for s in front_side), max(s[4] for s in front_side),
                   _cover(spans[False])[2] if spans[False] else 0.0, (d0, d1), o.floor)


def _cover(spans: list) -> tuple:
    """(first t, last t, length covered) of overlapping spans (t0, t1, ...)."""
    spans = sorted((s[0], s[1]) for s in spans)
    total, end, first = 0.0, -math.inf, spans[0][0]
    for t0, t1 in spans:
        if t1 > end:
            total += t1 - max(t0, end)
            end = t1
    return first, end, total


def _around(spans: list) -> tuple:
    """The run of touching spans (t0, t1) holding t = 0 (else the nearest run)."""
    runs = []
    for t0, t1 in sorted(spans):
        if runs and t0 <= runs[-1][1] + 1e-3:
            runs[-1][1] = max(runs[-1][1], t1)
        else:
            runs.append([t0, t1])
    return min(runs, key=lambda r: (0.0 if r[0] <= 0.0 <= r[1] else min(abs(r[0]), abs(r[1]))))


# --- jambs, frames and leaves -------------------------------------------------------------------------
def dress(mb, interior, o, hole: Hole, ops: dict) -> None:
    """The opening's jambs, sill and head (inner plaster), or for a cased door its wooden frame and leaves;
    a bortal's arch gets its stone band on the court side."""
    c, front, along = frame_of(o)
    d0, d1 = hole.depth
    floor_z = interior.high + o.floor * interior.fh
    if o.kind in CASED:
        casing(mb, o, c, front, along, d0, d1, ops)
        leaves(mb, interior, o, c, front, along, d0, d1, ops)
        return
    shape, _ = outline_of(o, ops)
    pts = np.asarray(shape.exterior.coords)[:-1]
    sill = not (o.wall is None and o.kind not in FACADE and o.z0 <= floor_z + GAP)   # a partition's floor shows
    reveal(mb, c, front, along, d0, d1, pts, sill)
    if o.kind in FACADE and o.z0 < floor_z - GAP:     # a door below its floor: the step up inside
        h = o.width / 2
        quad = np.array([[*(c + along * -h + front * d0), o.z0], [*(c + along * h + front * d0), o.z0],
                         [*(c + along * h + front * d0), floor_z], [*(c + along * -h + front * d0), floor_z]])
        add_quads(mb, "plaster_inner", quad[None], np.array([[*front, 0.0]]))
    if o.kind in GLAZED:
        casement(mb, interior, o, c, front, along, d0, ops)
    if o.kind == "arch" and o.wall is not None:
        add_arch(mb, o.x, o.y, o.z0, math.atan2(front[1], front[0]), o.width, o.z1 - o.z0,
                 float(ops.get("arch_frame", 0.1)), "stone_frame", panel=False, proud=0.01)


def reveal(mb, c, front, along, d0: float, d1: float, pts: np.ndarray, sill: bool) -> None:
    """Quads through the wall from depth d0 to d1 along the hole's counter-clockwise outline (t, z), each
    facing into the hole (the left of its edge); the bottom edge (the sill) only when `sill`."""
    bottom = pts[:, 1].min()
    quads, toward = [], []
    for p, q in zip(pts, np.roll(pts, -1, axis=0)):
        if not sill and max(p[1], q[1]) < bottom + 1e-9:
            continue
        quads.append([[*(c + along * t + front * d), z] for (t, z), d in ((p, d0), (q, d0), (q, d1), (p, d1))])
        toward.append([*(along * -(q[1] - p[1])), q[0] - p[0]])
    if quads:
        add_quads(mb, "plaster_inner", np.array(quads, dtype=np.float64), np.array(toward, dtype=np.float64))


def _rect(c, front, along, t0: float, t1: float, d0: float, d1: float) -> Polygon:
    return Polygon([c + along * t0 + front * d0, c + along * t1 + front * d0,
                    c + along * t1 + front * d1, c + along * t0 + front * d1])


def casing(mb, o, c, front, along, d0: float, d1: float, ops: dict) -> None:
    """The wooden frame round a door's clear opening: two jambs and a head `casing` m wide, standing
    `casing_proud` m out of both faces of the wall."""
    w, p = float(ops.get("casing", 0.05)), float(ops.get("casing_proud", 0.02))
    h = o.width / 2
    for t0, t1 in ((-h - w, -h), (h, h + w)):
        extrude(mb, _rect(c, front, along, t0, t1, d0 - p, d1 + p), o.z0, o.z1, "door_frame", None, z_ref=o.z0)
    extrude(mb, _rect(c, front, along, -h - w, h + w, d0 - p, d1 + p), o.z1, o.z1 + w, "door_frame",
            "door_frame", z_ref=o.z0)
    add_cap(mb, _rect(c, front, along, -h, h, d0 - p, d1 + p), o.z1, "door_frame", up=False)


def casement(mb, interior, o, c, front, along, d0: float, ops: dict) -> None:
    """The glazed wooden casement inside a window's hole, `casement_inset` m from the wall's inner face:
    stiles, rails, a middle stile on a wide one, and see-through panes (`glass_inner`); wood in
    traditional houses, painted white elsewhere."""
    w, t = float(ops.get("casement", 0.05)), float(ops.get("casement_depth", 0.04))
    d = d0 + float(ops.get("casement_inset", 0.08))
    mat = "casement_wood" if interior.layout in TRADITIONAL else "casement_white"
    h = o.width / 2 - 0.001
    z0, z1 = o.z0 + 0.001, o.z1 - 0.001
    bars = [(-h, -h + w, z0, z1), (h - w, h, z0, z1), (-h + w, h - w, z0, z0 + w), (-h + w, h - w, z1 - w, z1)]
    if o.width > float(ops.get("mullion", 0.6)):
        bars.append((-w / 4, w / 4, z0 + w, z1 - w))
    for t0, t1, b0, b1 in bars:
        extrude(mb, _rect(c, front, along, t0, t1, d - t / 2, d + t / 2), b0, b1, mat, mat, z_ref=o.z0)
        if b0 > z0 + 1e-6:
            add_cap(mb, _rect(c, front, along, t0, t1, d - t / 2, d + t / 2), b0, mat, up=False)
    pane = np.array([[*(c + along * -h + front * d), z0], [*(c + along * h + front * d), z0],
                     [*(c + along * h + front * d), z1], [*(c + along * -h + front * d), z1]])
    add_quads(mb, "glass_inner", pane[None], np.array([[*-front, 0.0]]))


def leaves(mb, interior, o, c, front, along, d0: float, d1: float, ops: dict) -> None:
    """One leaf (two for a court door) hinged at the jambs on the face of the room it swings into; on stream
    `doors` (one per opening) `open_share` of them stand open by `open_angle` degrees."""
    rng = stream(interior.seed, "interior", interior.city_id, interior.building, "doors", o.id)
    opened = rng.random() < float(ops.get("open_share", 0.4))
    lo, hi = ops.get("open_angle", [70.0, 100.0])
    angle = math.radians(rng.uniform(float(lo), float(hi))) if opened else 0.0
    hinge = 1.0 if rng.random() < 0.5 else -1.0
    sigma = swing(interior, o)
    face = d1 if sigma > 0 else d0
    thick = float(ops.get("leaf", 0.04))
    n = CASED[o.kind]
    width = o.width / n - 2 * GAP
    for side in ((hinge,) if n == 1 else (1.0, -1.0)):
        e0, s = -side * along, sigma * front
        e = math.cos(angle) * e0 + math.sin(angle) * s
        q = math.sin(angle) * e0 - math.cos(angle) * s
        h = c + along * (side * (o.width / 2 - GAP)) + front * face
        leaf = Polygon([h, h + e * width, h + e * width + q * thick, h + q * thick])
        extrude(mb, leaf, o.z0 + 0.01, o.z1 - GAP, "door_leaf", "door_leaf", z_ref=o.z0)


def swing(interior, o) -> float:
    """+1 when the door swings into its other room (along its front), -1 into its own: into the room that
    is not a way through (couloir, hall, palier, stairs, skifa, gallery, court), else into its own room."""
    by_id = {r.id: r for r in interior.rooms}
    a, b = (by_id.get(i) for i in o.rooms)
    if b is None or R.is_court(b):
        return -1.0
    return 1.0 if a is not None and a.type in WAYS and b.type not in WAYS else -1.0


# --- drawing ------------------------------------------------------------------------------------------
def draw(mb, f: Face) -> None:
    """One face: a quad per band (the dado below, the wall above) without holes, else its polygon less the
    holes, triangulated in (s, z)."""
    length = f.length
    bands = [(f.z0, f.z1, f.mat)]
    if f.dado is not None and f.z0 < f.dado < f.z1:
        bands = [(f.z0, f.dado, "zellige"), (f.dado, f.z1, f.mat)]
    d = (f.b - f.a) / max(length, 1e-12)
    nrm = np.array([d[1], -d[0], 0.0])
    if not f.holes:
        for z0, z1, mat in bands:
            pos = np.array([[*f.a, z0], [*f.b, z0], [*f.b, z1], [*f.a, z1]])
            uv = np.array([[f.u0, -(z0 - f.z_ref)], [f.u0 + length, -(z0 - f.z_ref)],
                           [f.u0 + length, -(z1 - f.z_ref)], [f.u0, -(z1 - f.z_ref)]])
            mb.add(mat, pos, np.tile(nrm, (4, 1)), uv, _QUAD)
        return
    wall = box(0.0, f.z0, length, f.z1).difference(unary_union(f.holes))
    for z0, z1, mat in bands:
        part = wall.intersection(box(-1.0, z0, length + 1.0, z1)) if len(bands) > 1 else wall
        tri = np.concatenate([triangulate(p) for p in polygons(part)] or [np.zeros((0, 3, 2))])
        if not len(tri):
            continue
        sz = tri.reshape(-1, 2)
        pos = np.column_stack([f.a + d * sz[:, :1], sz[:, 1]])
        uv = np.column_stack([f.u0 + sz[:, 0], -(sz[:, 1] - f.z_ref)])
        mb.add(mat, pos, np.tile(nrm, (len(pos), 1)), uv, np.arange(len(pos)).reshape(-1, 3))


def balustrades(mb, interior, height: float) -> None:
    """A low wall, a partition thick, along the edge a covered court's light well shares with its gallery."""
    half = interior.walls["partition"] / 2
    wells = [r for r in interior.rooms if r.type == "well" and r.floor < interior.floors]
    for well in wells:
        for r in interior.rooms:
            if r.floor != well.floor or r.type != "bortal":
                continue
            line = well.polygon.boundary.intersection(r.polygon.boundary)
            segs = [g for g in getattr(line, "geoms", [line]) if g.geom_type in ("LineString", "MultiLineString")
                    and g.length > 1e-3]
            if not segs:
                continue
            body = unary_union([g.buffer(half, cap_style="flat", join_style="mitre") for g in segs])
            for p in polygons(body.intersection(interior.storeys[well.floor].polygon)):
                extrude(mb, p, well.z, well.z + height, "plaster_inner", "plaster_inner", z_ref=well.z)


# --- checks (tests and surveys) -----------------------------------------------------------------------
def faults(interior, holes: list, style: dict) -> list:
    """What is wrong with the walls' holes: an opening without a hole, a hole not cut full width on both
    sides of its wall (a passage may lose up to a partition), a partition crossing a hole of an exterior
    or court wall, an inner door or passage outside its partition or crossed by another partition."""
    ops = style.get("interiors", {}).get("openings", {})
    out = []
    cut_ids = {h.id for h in holes}
    for o in interior.openings:
        if walled_in(interior, o, ops) and o.id not in cut_ids:
            out.append(f"opening {o.id} ({o.kind}) has no hole")
    parts = {}
    by_id = {o.id: o for o in interior.openings}
    for h in holes:
        o = by_id[h.id]
        _, half = outline_of(o, ops)
        least = 2 * half - (interior.walls["partition"] if passage(o) else 0.0) - 0.02
        if (h.width < least or h.width > 2 * half + 0.02 or abs(h.back - h.width) > 0.02):
            out.append(f"opening {o.id} ({o.kind}) cut {h.width:.2f} / {h.back:.2f} m of {2 * half:.2f}")
        if h.floor >= interior.floors:              # roof rooms have no partitions
            continue
        if h.floor not in parts:
            parts[h.floor] = partitions(interior, h.floor)
        p = parts[h.floor]
        c, front, along = np.array([h.x, h.y]), *frame_of(o)[1:]
        d0, d1 = h.depth
        w = h.width / 2 - (0.1 if passage(o) else 0.01)   # a passage's side walls may meet it at a slant
        inside = _rect(c, front, along, -w, w, d0 - 0.1, d0 - GAP)
        if o.wall is None and o.kind not in FACADE:      # a partition's door or passage: in it, not crossed
            body = _rect(c, front, along, -w, w, d0 + GAP, d1 - GAP)
            if body.difference(p).area > 1e-4:
                out.append(f"opening {o.id} ({o.kind}) is not in its partition")
            other = _rect(c, front, along, -w, w, d1 + GAP, d1 + 0.1)
            if p.intersection(inside).area > 1e-4 or p.intersection(other).area > 1e-4:
                out.append(f"a partition crosses opening {o.id} ({o.kind})")
        elif p.intersection(inside).area > 1e-4:
            out.append(f"a partition crosses opening {o.id} ({o.kind})")
    return out


# --- stairs and overheads (prompt 49) -------------------------------------------------------------------
def stairs_mesh(mb, interior, style: dict) -> None:
    """Every stair: its steps, landings and pier (`stairs.parts`; a U flight's open side gets a stringer),
    its iron railings and its ladders."""
    from . import floors as F
    from . import stairs as S
    fl, st, _ = F.settings(style)
    steps = F.finish(interior, fl, "steps")
    h, step = float(fl.get("rail", 0.9)), float(fl.get("baluster", 0.12))
    for s in interior.stairs:
        for part in S.parts(s, interior, st, fl):
            mat = "plaster_inner" if part.kind == "pier" else steps
            for p in polygons(part.poly):
                extrude(mb, p, part.z0, part.z1, mat, mat, z_ref=part.z0)
                add_cap(mb, p, part.z0, mat, up=False)
        if s.kind == "u":
            for a, b, deep in S.stringers(s, interior, fl):
                F.bar(mb, a, b, float(fl.get("stringer", 0.05)), steps, deep)
        for line in S.rails(s, interior, st, fl):
            F.railing(mb, line, h, step)
    F.ladders(mb, interior, fl)


def overheads(interior, style: dict, outside=None) -> list:
    """What may stand over a stair's treads, as `stairs.Part`s (polygon, bottom z, top z): every slab with
    its wells, every landing and flight, the roof rooms' ceilings and the beams (`floors.overheads`)."""
    from .floors import overheads as over
    return over(interior, style, outside)
