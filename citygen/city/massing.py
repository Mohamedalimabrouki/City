"""Building massing (prompt 23): rooflines that step, corners that turn, top floors that stand back.

Runs after every building is made and never adds, removes or reorders one, so households, souks,
streets and trees stay exactly as they were. Every change is a field of `Building` (city/model.py)
or an edit of a footprint inside its old outline (a cut street corner, a villa's L); each choice has
its own random stream `ctx.rng("massing", feature, k)`; the numbers live in `[district.<kind>]`.

  colonial  the buildings of one block share a cornice line, one floor up or down (corners stand
            taller); street corners are cut (the pan coupe of Tunis) or rounded, some crowned with
            a dome or a turret; a share has its top floor set back behind a terrace
  modern    slabs step in height along their length, at window column joints; lift motor rooms
            and water tanks on stands stand on their roofs
  suburb    villas as an L: a hip-roofed part and a flat terrace wing one floor lower
  medina    a few courtyard houses get a menzah, a small roof room (placed by roofs.roof_layout)

`masses(b)` turns the fields into the volumes the tile mesher draws and the dresser dresses; every
reader of a building's height or floors goes through it (`floors_at`, `wall_height`).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import shapely
from shapely.geometry import Point, Polygon
from shapely.geometry.polygon import orient
from shapely.strtree import STRtree

from ..mesh.builder import rectangle
from ..rng import weighted
from .geo import frame, largest, polygons
from .openings import wall_arrays

PROBE = 1.6   # meters in front of a wall's middle where the dresser looks for its street


@dataclass
class Mass:
    """One volume of a building: walls from `base` up to its roof at `top` (meters above the
    building's highest ground point; a base of 0 means from the ground)."""

    polygon: object
    base: float
    top: float
    floors: int            # floors counted from the ground up to this roof
    shape: str = "flat"    # flat | hip
    roof: str = ""         # roof material
    main: bool = False     # carries the stair room, the menzah, the machinery and the roof props
    terrace: bool = False  # a walkable terrace the floor above opens onto


def massed(b) -> bool:
    """Is building b more than one box?"""
    return b.setback is not None or bool(b.steps)


def masses(b) -> list:
    """The volumes of building b, as drawn: one box, a base and its set-back top floor, or steps."""
    floors = max(1, int(b.floors))
    fh = b.height / floors
    if b.setback is not None:
        return [Mass(b.footprint, 0.0, (floors - 1) * fh, floors - 1, "flat", b.roof, terrace=True),
                Mass(b.setback, (floors - 1) * fh, b.height, floors, "flat", b.roof, main=True)]
    if b.steps:
        tallest = max(range(len(b.steps)), key=lambda i: (b.steps[i][1], -i))
        hip = any(s[2] == "hip" for s in b.steps)
        return [Mass(poly, 0.0, b.height if f == floors else f * fh, int(f), shape, roof, main=i == tallest,
                     terrace=hip and shape == "flat")
                for i, (poly, f, shape, roof) in enumerate(b.steps)]
    return [Mass(b.footprint, 0.0, b.height, floors, b.roof_shape, b.roof, main=True)]


def main_mass(b) -> Mass:
    return next(m for m in masses(b) if m.main)


def floors_at(b, pts) -> np.ndarray:
    """Floors of the outer wall at points on it: the tallest mass whose walls pass there."""
    pts = np.asarray(pts, dtype=np.float64).reshape(-1, 2)
    if not massed(b):
        return np.full(len(pts), max(1, int(b.floors)))
    probe = shapely.points(pts)
    out = np.zeros(len(pts), dtype=int)
    for m in masses(b):
        on = shapely.distance(m.polygon.boundary, probe) < 0.05
        out = np.where(on, np.maximum(out, m.floors), out)
    return np.where(out > 0, out, max(1, int(b.floors)))


def wall_height(b, pts) -> np.ndarray:
    """Height of the outer wall (to its roof, parapet left out) at points on it."""
    if not massed(b):
        return np.full(len(np.asarray(pts).reshape(-1, 2)), float(b.height))
    return floors_at(b, pts) * (b.height / max(1, int(b.floors)))


def outline(b) -> np.ndarray:
    """The footprint's counter-clockwise exterior ring (closed), with every mass corner on it inserted,
    so each wall segment belongs to one set of masses. A plain building's ring is unchanged."""
    ring = np.asarray(orient(b.footprint, 1.0).exterior.coords)
    if not massed(b):
        return ring
    extra = np.concatenate([np.asarray(m.polygon.exterior.coords)[:-1] for m in masses(b)])
    return with_vertices(ring, extra)


def with_vertices(ring: np.ndarray, extra: np.ndarray, tol: float = 1e-4) -> np.ndarray:
    """A closed ring with the points of `extra` that lie on its segments inserted in order."""
    pts = np.asarray(ring, dtype=np.float64)[:, :2]
    out = []
    for a, c in zip(pts[:-1], pts[1:]):
        out.append(a)
        d = c - a
        length = float(np.hypot(*d))
        if length < 1e-9:
            continue
        u = d / length
        s = (extra - a) @ u
        off = np.abs((extra - a) @ np.array([-u[1], u[0]]))
        on = (off < tol) & (s > tol) & (s < length - tol)
        for t in np.unique(np.round(s[on], 6)):
            out.append(a + u * t)
    out.append(pts[-1])
    return np.array(out)


def inner_walls(b, tops: list):
    """Walls inside the footprint: where a taller mass rises above a neighbour or above the terrace it
    stands on. `tops` gives each mass's highest point (its roof plus any parapet). Yields (mass index,
    closed counter-clockwise ring of that mass, bool per segment, level below, level above)."""
    ms = masses(b)
    edge = b.footprint.boundary
    for k, m in enumerate(ms):
        others = [o.polygon.exterior.coords for j, o in enumerate(ms) if j != k]
        ring = with_vertices(np.asarray(orient(m.polygon, 1.0).exterior.coords),
                             np.concatenate([np.asarray(c)[:-1] for c in others]))
        a, c = ring[:-1], ring[1:]
        d = c - a
        length = np.hypot(d[:, 0], d[:, 1])
        n = np.stack([d[:, 1], -d[:, 0]], 1) / np.maximum(length, 1e-9)[:, None]
        mid = (a + c) / 2
        inside = (shapely.distance(edge, shapely.points(mid)) > 1e-3) & (length > 1e-6)
        if not inside.any():
            continue
        probe = mid + n * 0.05
        level = np.full(len(a), np.nan)
        for j, o in enumerate(ms):
            if j == k:
                continue
            hit = shapely.contains_xy(o.polygon, probe[:, 0], probe[:, 1])
            z = tops[j] if o.base >= m.base - 1e-6 else o.top      # beside it, or the deck it stands on
            level = np.where(hit, np.fmax(level, z), level)
        for lo in np.unique(level[inside & ~np.isnan(level)]):
            mask = inside & (level == lo)
            if tops[k] > lo + 1e-6:
                yield k, ring, mask, float(lo), float(tops[k])


def terrace_walls(b) -> list:
    """Walls of a mass rising over a terrace (a set-back floor, a villa's main part over its wing), with
    the floors that open onto it: [(a, b, outward normal, length, first floor, last floor + 1)]."""
    if not massed(b):
        return []
    ms = masses(b)
    out = []
    for k, ring, mask, lo, hi in inner_walls(b, [m.top for m in ms]):
        m = ms[k]
        for a, c in zip(ring[:-1][mask], ring[1:][mask]):
            d = c - a
            length = float(np.hypot(*d))
            n = np.array([d[1], -d[0]]) / max(length, 1e-9)
            p = (a + c) / 2 + n * 0.05
            under = [o for o in ms if o is not m and o.terrace and o.polygon.contains(Point(*p))]
            if under:
                out.append((a, c, n, length, int(under[0].floors), int(m.floors)))
    return out


def roof_obstacles(b, mass: Mass | None = None) -> list:
    """Things standing on a roof (the main one by default) that the stair room, the menzah and the roof
    props avoid: machinery on it and, on the main roof, a corner dome or turret."""
    out = []
    if not b.machines and not (b.top and "x" in b.top):
        return out
    mass = main_mass(b) if mass is None else mass
    for m in b.machines:
        if abs(float(m["z"]) - mass.top) < 1e-6 and mass.polygon.contains(Point(m["x"], m["y"])):
            out.append(rectangle(m["x"], m["y"], m["length"], m["width"], m["angle"]))
    if b.top and "x" in b.top and mass.main:
        out.append(Point(b.top["x"], b.top["y"]).buffer(b.top["radius"], 12))
    return out


# --- the planning step ------------------------------------------------------------------

def apply_massing(ctx, plan) -> None:
    """Massing of every building of a plan, after the buildings, households and souks are made."""
    style = ctx.style["district"]
    kinds = [d.kind for d in plan.districts]
    surfaces = [st.line.buffer(st.width / 2, cap_style="flat") for st in plan.streets]
    tree = STRtree(surfaces) if surfaces else None
    colonial = [k for k, b in enumerate(plan.buildings) if b.kind == "apartments" and kinds[b.district] == "colonial"]
    if colonial and tree is not None:
        _colonial(ctx, plan, colonial, style["colonial"], tree)
    roofs = ctx.style.get("roofs", {})
    for k, b in enumerate(plan.buildings):
        kind = kinds[b.district]
        if b.kind == "apartments" and kind == "modern":
            _slab(ctx, k, b, style[kind], ctx.style.get("dressing", {}).get("slab", {}), roofs)
        elif b.kind == "villa" and kind == "suburb":
            _villa(ctx, k, b, style[kind])
        elif b.kind == "house" and kind in ("medina", "village") and b.footprint.interiors:
            if ctx.rng("massing", "menzah", k).random() < float(style[kind].get("menzah", 0.0)):
                b.menzah = True


def street_of(tree, pts: np.ndarray) -> np.ndarray:
    """Index of the street surface each point lies in, or -1 (the dresser's rule, Dresser.streets_at)."""
    out = np.full(len(pts), -1)
    if tree is None or not len(pts):
        return out
    inp, hit = tree.query(shapely.points(pts), predicate="within")
    out[inp] = hit
    return out


def corner_faces(b, p, q) -> list:
    """For each cut corner of b, a bool per wall (p[i] to q[i]): the faces of that cut."""
    out = []
    for x, y, _kind, reach in b.corners:
        c = np.array([x, y])
        out.append((np.hypot(*(p - c).T) <= reach + 1e-3) & (np.hypot(*(q - c).T) <= reach + 1e-3))
    return out


def probes(b, p, q, n) -> np.ndarray:
    """Where the dresser looks for the street in front of each wall: 1.6 m out from its middle, or
    for the faces of a cut corner, 1.6 m out from the old corner point (the face itself stands back)."""
    out = (p + q) / 2 + n * PROBE
    for (x, y, _kind, _reach), face in zip(b.corners, corner_faces(b, p, q)):
        out[face] = np.array([x, y]) + n[face] * PROBE
    return out


def _turn(u0, u1) -> float:
    return math.degrees(math.atan2(u0[0] * u1[1] - u0[1] * u1[0], float(np.dot(u0, u1))))


def _corners(b, tree, dc) -> list:
    """Street corners of a footprint: (vertex index, turn in degrees) where two walls facing streets meet
    at a convex corner within `corner_angle` of square."""
    p, q, n, length = wall_arrays(b.footprint)
    street = street_of(tree, (p + q) / 2 + n * PROBE)
    u = (q - p) / np.maximum(length, 1e-9)[:, None]
    m = len(p)
    out = []
    for i in range(m):
        j = (i + 1) % m
        t = _turn(u[i], u[j])
        if street[i] >= 0 and street[j] >= 0 and abs(t - 90.0) <= float(dc.get("corner_angle", 4.0)):
            out.append((i, t))
    return out


def _colonial(ctx, plan, ks: list, dc: dict, tree) -> None:
    """Rows, cut corners, corner domes and set-back top floors of the ville nouvelle."""
    fh = float(dc["floor_height"])
    corners = {k: _corners(plan.buildings[k], tree, dc) for k in ks}
    blocks = STRtree([blk[0] for blk in plan.blocks]) if plan.blocks else None
    rows: dict = {}
    for k in ks:
        pt = plan.buildings[k].footprint.representative_point()
        hit = blocks.query(pt, predicate="within") if blocks is not None else []
        rows.setdefault(int(hit[0]) if len(hit) else -1, []).append(k)
    lo, hi = dc.get("row_floors", [3, 7])
    for _blk, members in sorted(rows.items()):
        row = int(round(float(np.median([plan.buildings[k].floors for k in members]))))
        for k in members:
            b = plan.buildings[k]
            table = dc.get("corner_step" if corners[k] else "row_step", [[0, 1]])
            floors = int(np.clip(row + int(weighted(ctx.rng("massing", "row", k), table)), lo, hi))
            b.floors, b.height = floors, floors * fh
    for k in ks:
        b = plan.buildings[k]
        if corners[k]:
            old = b.footprint
            _cut_corners(ctx, k, b, corners[k], dc)
            if b.corners and blocks is not None:
                _apron(b, old, blocks, float(dc.get("apron_grow", 0.3)))
        if b.corners and b.floors >= int(dc.get("dome_floors", 4)):
            _corner_top(ctx, k, b, dc, ctx.style.get("roofs", {}))
        if b.top is None and b.floors >= int(dc.get("setback_floors", 4)):
            if ctx.rng("massing", "setback", k).random() < float(dc.get("setback_share", 0.0)):
                _setback(b, tree, float(dc.get("setback_depth", 2.0)), float(dc.get("setback_min_share", 0.4)))


def _cut_corners(ctx, k: int, b, found: list, dc: dict) -> None:
    """Cut some street corners of a footprint: a chamfer (one face) or a round (three faces turning
    22.5 degrees each), inside the old outline, keeping `corner_rest` m of straight wall."""
    rng = ctx.rng("massing", "corner", k)
    ring = np.asarray(orient(b.footprint, 1.0).exterior.coords)[:-1]
    m = len(ring)
    length = np.hypot(*(np.roll(ring, -1, axis=0) - ring).T)
    used = np.zeros(m)                      # meters each wall has given to cuts at its ends
    rest = float(dc.get("corner_rest", 2.5))
    cuts = {}
    for i, t in found:
        roll, kind_roll, size_roll = rng.random(3)
        if roll >= float(dc.get("corner_cut", 0.0)):
            continue
        j = (i + 1) % m
        v = ring[j]
        u_i = (ring[j] - ring[i]) / length[i]
        u_j = (ring[(j + 1) % m] - v) / length[j]
        room = min(length[i] - used[i], length[j] - used[j]) - rest
        pts, reach, kind = None, 0.0, ""
        if kind_roll < float(dc.get("corner_round", 0.0)):
            seg = float(np.interp(size_roll, [0, 1], dc.get("round_segment", [3.25, 3.4])))
            pts, reach = _round(v, u_i, u_j, t, seg)
            kind = "round"
        if pts is None or reach > room:
            c = float(np.interp(size_roll, [0, 1], dc.get("chamfer", [3.5, 3.95])))
            reach = c / (2.0 * math.sin(math.radians(t) / 2.0))
            pts, kind = [v - u_i * reach, v + u_j * reach], "chamfer"
        if reach > room:
            continue
        used[i] += reach
        used[j] += reach
        cuts[j] = (pts, (float(v[0]), float(v[1]), kind, float(reach)))
    if not cuts:
        return
    new = []
    for idx in range(m):
        new += cuts[idx][0] if idx in cuts else [ring[idx]]
    poly = Polygon(new)
    if not poly.is_valid or poly.area < 0.6 * b.footprint.area or not b.footprint.buffer(1e-6).contains(poly):
        return
    b.footprint = poly
    b.corners = [cuts[idx][1] for idx in sorted(cuts)]


def _apron(b, old, blocks, reach: float) -> None:
    """The pieces of the lot a cut removed, grown `reach` m to meet the sidewalk at the block edge
    and kept inside the block and off the building: paved like the sidewalk (a pan coupe widens it)."""
    removed = old.difference(b.footprint)
    hit = blocks.query(b.footprint.representative_point(), predicate="within")
    if removed.is_empty or not len(hit):
        return
    block = blocks.geometries[int(hit[0])]
    apron = removed.buffer(reach, join_style="mitre").intersection(block).difference(b.footprint)
    parts = [p for p in polygons(apron) if p.area > 0.05]
    if parts:
        b.apron = parts[0] if len(parts) == 1 else shapely.MultiPolygon(parts)


def _round(v, u_i, u_j, t: float, seg: float) -> tuple:
    """Points of a rounded corner at v: three faces of `seg` m, four turns of t / 4 degrees. Returns
    (points from the first tangent point to the last, distance of the tangent points from v)."""
    step, base = math.radians(t) / 4.0, math.atan2(u_i[1], u_i[0])
    dirs = [np.array([math.cos(base + s * step), math.sin(base + s * step)]) for s in (1, 2, 3)]
    total = sum(dirs) * seg
    along = u_i + u_j
    reach = float(np.hypot(*total) / max(np.hypot(*along), 1e-9))
    pts = [v - u_i * reach]
    for d in dirs:
        pts.append(pts[-1] + d * seg)
    return pts, reach


def _corner_top(ctx, k: int, b, dc: dict, roofs: dict) -> None:
    """A dome on a drum, or a taller turret, standing on the roof right behind the first cut corner."""
    rng = ctx.rng("massing", "corner-top", k)
    if rng.random() >= float(dc.get("corner_dome", 0.0)):
        return
    shape = weighted(rng, dc.get("corner_top", [["dome", 1]]))
    spec = dc.get(shape, {})
    radius = float(rng.uniform(*spec.get("radius", [1.8, 2.2])))
    drum = float(rng.uniform(*spec.get("drum", [1.0, 1.4])))
    material = weighted(rng, dc.get("drum_material", [["wall", 1]]))
    cap = weighted(rng, dc.get("dome_cap", [["dome_white", 1]]))
    x, y, _kind, reach = b.corners[0]
    c = np.array([x, y])
    ring = np.asarray(orient(b.footprint, 1.0).exterior.coords)[:-1]
    near = ring[np.hypot(*(ring - c).T) <= reach + 1e-3]
    if len(near) < 2:
        return
    face = near.mean(axis=0)                                   # the middle of the cut
    inward = (face - c) / max(float(np.hypot(*(face - c))), 1e-9)
    clear = float(roofs.get("parapet_thickness", 0.2)) + 0.15
    center = face + inward * (radius + clear)
    if not b.footprint.buffer(-clear).contains(Point(*center).buffer(radius, 12)):
        return
    b.top = {"x": float(center[0]), "y": float(center[1]), "shape": "drum", "radius": radius, "height": drum,
             "rise": radius * float(spec.get("rise", 0.9)), "material": b.wall if material == "wall" else material,
             "cap": cap, "side": 2 * radius}


def _setback(b, tree, depth: float, share: float) -> None:
    """The top floor stands `depth` m back from every wall facing a street (party and back walls stay)."""
    p, q, n, length = wall_arrays(b.footprint)
    street = street_of(tree, probes(b, p, q, n))
    keep = (street >= 0) & (length > 1e-6)
    if not keep.any():
        return
    bands = [Polygon([a, c, c - nn * depth, a - nn * depth]) for a, c, nn in zip(p[keep], q[keep], n[keep])]
    upper = largest(b.footprint.difference(shapely.union_all(bands)))
    if upper is None:
        return
    upper = upper.simplify(0.02)
    if (upper.geom_type != "Polygon" or not upper.is_valid or upper.interiors or upper.area < share * b.footprint.area
            or upper.buffer(-1.5).is_empty):
        return
    b.setback = orient(upper, 1.0)


def _slab(ctx, k: int, b, dc: dict, slab: dict, roofs: dict) -> None:
    """Steps along a slab's length (two or three parts, cut between window columns) and roof machinery."""
    rng = ctx.rng("massing", "steps", k)
    cx, cy, length, width, angle = frame(b.footprint)
    fh = b.height / max(1, int(b.floors))
    if (length >= float(dc.get("step_min_length", 30.0)) and b.floors >= int(dc.get("step_min_floors", 3)) + 1
            and rng.random() < float(dc.get("step_share", 0.0))):
        parts = int(weighted(rng, dc.get("step_parts", [[2, 1]])))
        drop = int(weighted(rng, dc.get("step_drop", [[1, 1]])))
        middle = rng.random() < 0.5
        flip = rng.random() < 0.5
        bay = float(slab.get("bay", 3.2))
        cols = max(1, int(length // bay))
        edges = [int(round(cols * i / parts)) for i in range(parts + 1)]
        lo = int(dc.get("step_min_floors", 3))
        f = int(b.floors)
        pattern = ([f - drop, f, f - drop] if parts == 3 and middle else [f - drop * i for i in range(parts)])
        pattern = [max(lo, x) for x in (pattern[::-1] if flip else pattern)]
        widths = np.diff(edges) * length / cols
        if (len(set(pattern)) > 1 and min(widths) >= float(dc.get("step_min_part", 12.0))):
            u = np.array([math.cos(angle), math.sin(angle)])
            steps = []
            for i in range(parts):
                s0, s1 = edges[i] * length / cols - length / 2, edges[i + 1] * length / cols - length / 2
                cut = rectangle(*(np.array([cx, cy]) + u * (s0 + s1) / 2), s1 - s0, width + 2.0, angle)
                part = largest(b.footprint.intersection(cut))
                if part is None or part.geom_type != "Polygon" or not part.is_valid:
                    steps = []
                    break
                steps.append((orient(part, 1.0), pattern[i], "flat", b.roof))
            if steps and abs(sum(s[0].area for s in steps) - b.footprint.area) < 0.01:
                b.steps = steps
    if b.floors >= int(dc.get("machine_floors", 5)):
        _machines(ctx, k, b, dc, float(roofs.get("parapet_thickness", 0.2)))


def _machines(ctx, k: int, b, dc: dict, thick: float) -> None:
    """A lift motor room over the middle of each roof part (on most), a few water tanks on stands."""
    rng = ctx.rng("massing", "machines", k)
    ml, mw, mh = (float(v) for v in dc.get("lift_room", [3.0, 2.4, 2.4]))
    side = float(dc.get("tank_stand", 1.8))
    out = []
    parts = [m for m in masses(b) if m.shape == "flat"]
    for m in parts:
        roof = m.polygon.buffer(-(thick + 0.6), join_style="mitre")
        cx, cy, length, width, angle = frame(m.polygon)
        if rng.random() < float(dc.get("lift", 0.0)):
            room = rectangle(cx, cy, ml, mw, angle)
            if roof.contains(room):
                out.append({"kind": "lift", "x": cx, "y": cy, "angle": angle, "length": ml, "width": mw,
                            "height": mh, "z": m.top})
    lo, hi = dc.get("tank_stands", [0, 2])
    for _ in range(int(rng.integers(int(lo), int(hi) + 1))):
        m = parts[int(rng.integers(len(parts)))]
        cx, cy, length, width, angle = frame(m.polygon)
        u = np.array([math.cos(angle), math.sin(angle)])
        v = np.array([-u[1], u[0]])
        c = np.array([cx, cy]) + u * rng.uniform(-0.5, 0.5) * max(length - 6.0, 0.0) + v * rng.uniform(-0.25, 0.25) * width
        stand = rectangle(c[0], c[1], side, side, angle)
        roof = m.polygon.buffer(-(thick + 0.6), join_style="mitre")
        taken = [rectangle(o["x"], o["y"], o["length"] + 2.0, o["width"] + 2.0, o["angle"]) for o in out]
        if roof.contains(stand) and not any(stand.intersects(t) for t in taken):
            out.append({"kind": "tank", "x": float(c[0]), "y": float(c[1]), "angle": angle, "length": side,
                        "width": side, "height": 2.9, "z": m.top})
    b.machines = out


def _villa(ctx, k: int, b, dc: dict) -> None:
    """An L: a hip-roofed main part across one end of the house, a flat terrace wing one floor lower
    along the rest of the front or the back."""
    rng = ctx.rng("massing", "villa", k)
    if rng.random() >= float(dc.get("l_share", 0.0)) or b.floors < int(dc.get("l_min_floors", 2)):
        return
    cx, cy, length, width, angle = frame(b.footprint)
    rect = rectangle(cx, cy, length, width, angle)
    if b.footprint.area < 0.98 * rect.area:
        return
    a = length * float(rng.uniform(*dc.get("l_main", [0.55, 0.65])))
    s = width * float(rng.uniform(*dc.get("l_wing", [0.5, 0.65])))
    end = 1.0 if rng.random() < 0.5 else -1.0
    side = 1.0 if rng.random() < 0.5 else -1.0
    if min(a, width) < 5.0 or length - a < 3.5 or s < 3.5:
        return
    u = np.array([math.cos(angle), math.sin(angle)]) * end
    v = np.array([-math.sin(angle), math.cos(angle)]) * side
    at = lambda x, y: np.array([cx, cy]) + u * x + v * y     # main part at +x, wing along +y
    xa, hl, hw = length / 2 - a, length / 2, width / 2
    main = Polygon([at(xa, -hw), at(hl, -hw), at(hl, hw), at(xa, hw)])
    wing = Polygon([at(-hl, hw - s), at(xa, hw - s), at(xa, hw), at(-hl, hw)])
    shape = Polygon([at(xa, -hw), at(hl, -hw), at(hl, hw), at(-hl, hw), at(-hl, hw - s), at(xa, hw - s)])
    if not shape.is_valid or not b.footprint.buffer(1e-6).contains(shape):
        return
    b.footprint = orient(shape, 1.0)
    b.roof_shape, b.roof = "hip", "roof_tile"
    b.steps = [(orient(main, 1.0), int(b.floors), "hip", "roof_tile"),
               (orient(wing, 1.0), int(b.floors) - 1, "flat", str(dc.get("terrace_roof", "roof_white")))]
