"""Houses without a courtyard (SPEC 6c "House without a courtyard"): `compact` and `small`.

A compact house is the dar's ring of rooms round a covered wast ed dar, a rectangle in the middle of the
storey's frame rising through every floor as a light well under a skylight; upper rooms look into it by
high `inner_window`s. Where the storey is too narrow for a band of rooms on both sides of it, the court
stands against the wall away from the door, or spans the house; where no court fits at all, the house
gets the `small` program: an entry, one bit and a matbakh corner, or one room.
"""
from __future__ import annotations

import math
from dataclasses import replace

import numpy as np
import shapely
from shapely.geometry import Point

from . import dar as D
from . import program as P
from . import rooms as R
from . import stairs as S
from .cuts import Cell, Frame, absorb, cut, offsets, parts, polygonal, shared, snap, width
from .model import Opening, Room, Storey  # noqa: F401  (Storey: the type of interior.storeys)


def plan(interior, outside, style: dict) -> None:
    """Floor plans of a house without a courtyard (a crowded one gets the small program and says so)."""
    interior.layout = "compact"
    job = D.Job(interior, outside, style)
    st0 = interior.storeys[0]
    fr = Frame.of(getattr(interior, "full0", None) or st0.polygon)   # a shop carved first keeps the frame
    court = central(job, fr)
    if court is None:
        small_plan(job)
        return
    facade, warnings = [replace(o) for o in interior.openings], list(interior.warnings)
    rings = {st.floor: snap(st.polygon.difference(court)) for st in interior.storeys}
    ring = D.Ring(court, court, rings, "covered")
    covered = Room(-1, 0, R.COURT, largest(court.intersection(st0.polygon)), st0.z, st0.height)
    wells = {st.floor: largest(court.intersection(st.polygon)) for st in interior.storeys[1:]}
    D.build(job, ring, covered, wells)
    types = {r.type for r in interior.rooms if r.floor == 0}
    full_bit = any(r.type == "bit" and r.floor == 0 and job.fits(r.polygon, "bit") for r in interior.rooms)
    if not {"bit", "matbakh"} <= types or not full_bit:   # the court leaves no room for the program: small
        interior.rooms = [r for r in interior.rooms if r.unit != "home"]   # a shop carved before stays
        interior.stairs, interior.features = [], []
        interior.openings, interior.warnings = facade, warnings
        small_plan(D.Job(interior, outside, style))
        return
    skylight(job, court)


def largest(geom):
    """The largest polygon of a geometry, on the grid."""
    got = parts(snap(geom))
    return max(got, key=lambda p: p.area) if got else None


def small(interior, outside, style: dict) -> None:
    """Floor plans of a small house."""
    small_plan(D.Job(interior, outside, style))


def central(job: D.Job, fr: Frame):
    """The covered court: `central` of the storey's length and width (at least `central_min`), centered
    with a band of rooms at least `band` deep on both sides where it fits, else against the wall away
    from the door, else across the whole storey; its walls keep `clear` of every opening. None when no
    placement leaves the door in a band."""
    interior = job.interior
    st0 = interior.storeys[0].polygon
    region = polygonal(shapely.intersection_all([st.polygon for st in interior.storeys]))
    u0, v0, u1, v1 = fr.bounds(st0)
    cfg = job.compact
    lo, hi = (float(v) for v in cfg.get("central", [0.4, 0.45]))
    share = float(job.rng("layout").uniform(lo, hi))
    least, band = float(cfg.get("central_min", 2.6)), float(cfg.get("band", 2.0))
    most = float(cfg.get("central_most", 0.45))
    keep = float(cfg.get("central_keep", 0.8))
    door = fr.local((job.spot.x, job.spot.y)) if job.spot is not None else fr.local(st0.centroid.coords[0])
    options = [axis_options((u0, u1), door[0], share, least, band), axis_options((v0, v1), door[1], share, least, band)]
    combos = sorted(((a, b) for a in options[0] for b in options[1] if not (a[2] == "full" and b[2] == "full")),
                    key=lambda t: (RANK[t[0][2]] + RANK[t[1][2]], RANK[t[0][2]]))
    zones = job.zs()
    probe = job.probe() if job.spot is not None else None
    stair = None
    if job.roof is not None and job.roof.stair is not None:     # the stair room and the floor before its door
        x, y, out = job.roof.door
        ahead = Point(x + math.cos(out) * 0.75, y + math.sin(out) * 0.75).buffer(0.75, cap_style="square")
        stair = job.roof.stair.buffer(0.3).union(ahead)
    for (a0, a1, _), (b0, b1, _) in combos:
        for axis, d in [(None, 0.0)] + [(ax, d) for d in list(offsets(job.shift, job.step))[1:] for ax in (0, 1)]:
            du, dv = (d, 0.0) if axis == 0 else (0.0, d) if axis == 1 else (0.0, 0.0)
            rect = fr.rect(a0 + du, b0 + dv, a1 + du, b1 + dv)
            c = snap(rect.intersection(region))
            if (c.geom_type != "Polygon" or c.area < keep * rect.area or c.area > most * st0.area
                    or width(c) < least - 0.05):
                continue                              # a slot, or a court that barely meets the storey
            if probe is not None and c.distance(probe) < band - 0.3:
                continue
            if stair is not None and c.intersects(stair):
                continue                              # the stair room's newel stands outside the court
            if S.walls_clear(c, region, zones, job.half):
                return c
    return None


RANK = {"center": 0, "side": 1, "full": 2}


def axis_options(span: tuple, door: float, share: float, least: float, band: float) -> list:
    """(start, end, how) of the court along one axis: centered with bands both sides, against the side
    away from the door with one band, or across."""
    t0, t1 = span
    length = t1 - t0
    size = max(least, share * length)
    out = []
    if length >= size + 2 * band:
        mid = (t0 + t1) / 2
        out.append((mid - size / 2, mid + size / 2, "center"))
    if length >= size + band:
        out.append((t0, t0 + size, "side") if door > (t0 + t1) / 2 else (t1 - size, t1, "side"))
    out.append((t0 - 0.5, t1 + 0.5, "full"))
    return out


def skylight(job: D.Job, court) -> None:
    """A glass panel in the roof over the covered court: a `skylight` opening of the top floor's well (or of
    the court of a one-floor house) and a feature."""
    interior = job.interior
    top = interior.floors - 1
    room = next((r for r in interior.rooms if r.floor == top and r.type in (R.COURT, "well")), None)
    if room is None:
        return
    z = interior.high + job.outside.b.height
    c = room.polygon.centroid
    fr = Frame.of(room.polygon)
    u0, v0, u1, v1 = fr.bounds(room.polygon)
    interior.openings.append(Opening(len(interior.openings), "skylight", c.x, c.y, fr.angle, u1 - u0, z, z, top,
                                     (room.id, -1)))
    interior.features.append({"type": "skylight", "x": round(c.x, 3), "y": round(c.y, 3), "z": round(z, 3),
                              "polygon": [[round(x, 3), round(y, 3)] for x, y in room.polygon.exterior.coords]})


# --- small houses ------------------------------------------------------------------------------------
def small_plan(job: D.Job) -> None:
    """An entry (a skifa, when `small_entry` m of depth and a bit behind it fit), one bit and a matbakh
    corner; ghorfas upstairs; the newel cell in the corner farthest from the door."""
    interior = job.interior
    interior.layout = "small"                         # a fallback reports the layout it really got
    st0 = interior.storeys[0]
    fr = Frame.of(getattr(interior, "full0", None) or st0.polygon)   # a shop carved first keeps the frame
    ring = D.Ring(getattr(interior, "full0", None) or st0.polygon, None, {st.floor: snap(st.polygon) for st in interior.storeys}, "none")
    top = D.stair_top(job)
    square = None
    if top > 0:
        served = list(range(min(top, interior.floors - 1) + 1))
        region = polygonal(shapely.intersection_all([ring.rings[f] for f in served]))
        if job.roof is not None and job.roof.stair is not None:
            square = S.under_stair_room(job.roof.stair, region, job.zs(served), job.half,
                                        float(job.stairs.get("newel_min", 1.9)))
        if square is None:
            square = S.in_corner(D.corners(job, ring), fr, region, job.zs(served), job.half,
                                 float(job.stairs.get("newel", 2.4)), float(job.stairs.get("newel_min", 1.9)))
    served = min(top, interior.floors - 1) if square is not None else -1
    split = {f: (D.without(p, square, job.thin, job.zs([f]), job.half) if f <= served else (p, None))
             for f, p in ring.rings.items()}
    polys = {f: v[0] for f, v in split.items()}
    per_floor = {}
    for f, poly in polys.items():
        pieces = sorted(parts(poly), key=lambda p: -p.area)
        if not pieces:
            per_floor[f] = []
            continue
        big, rest = pieces[0], [Cell(p, "" if f == 0 else "ghorfa") for p in pieces[1:]]
        if f == 0:
            per_floor[f] = small_ground(job, fr, big) + rest
            continue
        u0, _, u1, _ = fr.bounds(big)
        n = max(1, math.ceil((u1 - u0) / float(job.dar.get("bit_max", 6.0)) - 1e-9))
        per_floor[f] = [Cell(p, "ghorfa", "", "upper") for p in D.split_along(job, big, fr, 0, n, [f])] + rest
    for f, cs in per_floor.items():
        if split[f][1] is not None:
            cs = cs + [Cell(split[f][1], "droj", "", "stair")]
        per_floor[f] = absorb(cs, job.minimums, R.KEEP, job.piece, (), job.largest)
    per_floor[0] = P.assign(job, per_floor[0], small=True)
    D.rooms_from(job, per_floor, ring, None)
    job.court_room = None
    D.finish(job, ring, square, top, small_doors)


def small_ground(job: D.Job, fr: Frame, poly) -> list:
    """Floor 0 of a small house: entry strip at the door (skifa and matbakh), the bit behind it; or a bit
    and a matbakh at its far end; or one room."""
    if job.spot is None:
        return [Cell(poly, "bit")]
    n = fr.local(np.array([job.spot.x + job.spot.nx, job.spot.y + job.spot.ny])) - fr.local((job.spot.x, job.spot.y))
    ax = 0 if abs(n[0]) >= abs(n[1]) else 1          # the axis across the door's wall
    sign = 1.0 if n[ax] > 0 else -1.0                # the door's wall is at the `sign` end of that axis
    t0, t1 = fr.bounds(poly)[ax], fr.bounds(poly)[ax + 2]
    depth = float(job.compact.get("small_entry", 1.6))
    bit_w = job.minimums.get("bit", (7.0, 2.0))[1]
    probe = job.probe()
    if t1 - t0 >= depth + bit_w:
        at = (t1 - depth) if sign > 0 else (t0 + depth)
        pos = job.free(poly, fr, ax, at, [0])
        if pos is not None:
            lo, hi = cut(poly, fr, ax, pos)
            strip, rest = (hi, lo) if sign > 0 else (lo, hi)
            cells = [Cell(p, "bit") for p in rest]
            for p in strip:
                cells += entry_strip(job, fr, 1 - ax, p, probe) if p.distance(probe) < 1e-6 else [Cell(p, "")]
            return cells
    far = (t0 + 1.8) if sign > 0 else (t1 - 1.8)
    pos = job.free(poly, fr, ax, far, [0])
    if pos is not None:
        lo, hi = cut(poly, fr, ax, pos)
        kitchen, rest = (lo, hi) if sign > 0 else (hi, lo)
        if kitchen and all(job.fits(p, "matbakh") for p in kitchen) and rest:
            return [Cell(p, "bit") for p in rest] + [Cell(p, "matbakh") for p in kitchen]
    return [Cell(poly, "bit")]


def entry_strip(job: D.Job, fr: Frame, ax: int, strip, probe) -> list:
    """The strip along the door's wall: the skifa from the door's nearer end to `clear` past the door,
    the rest a matbakh (or a piece the bit takes)."""
    o = job.main
    t = fr.local((o.x, o.y))[ax]
    t0, t1 = fr.bounds(strip)[ax], fr.bounds(strip)[ax + 2]
    reach = o.width / 2 + job.clear + job.half
    least = job.minimums.get("skifa", (3.5, 1.2))[0]
    deep = shapely.intersection(fr.line(ax ^ 1, fr.local(probe.coords[0])[ax ^ 1]), strip).length or 1.0
    length = max(reach, least / deep - (t - t0 if t - t0 < t1 - t else t1 - t))
    at = t + length if t - t0 < t1 - t else t - length
    pos = job.free(strip, fr, ax, at, [0], lo=min(at, t + reach) if at > t else -math.inf,
                   hi=max(at, t - reach) if at < t else math.inf)
    if pos is None:
        return [Cell(strip, "")]
    lo, hi = cut(strip, fr, ax, pos)
    out = []
    for p in lo + hi:
        if p.distance(probe) < 1e-6:
            out.append(Cell(p, "skifa" if job.fits(p, "skifa") else ""))
        else:
            out.append(Cell(p, "matbakh" if job.fits(p, "matbakh") else ""))
    return out


def small_doors(job: D.Job, ring) -> None:
    """Doors of a small house: the skifa and the matbakh into the bit, the ghorfas into each other."""
    interior = job.interior
    rooms = sorted(interior.rooms, key=lambda r: r.id)
    bits = [r for r in rooms if r.floor == 0 and r.type == "bit"]
    for r in rooms:
        if r.floor == 0 and r.type in ("skifa", "matbakh"):
            for b in sorted(bits, key=lambda b: (-shared(r.polygon, b.polygon), b.id)):
                if R.place(interior, r, b, "inner", job.door, job.door_height) is not None:
                    break
    for f in range(1, interior.floors):
        ghorfas = [r for r in rooms if r.floor == f and r.type == "ghorfa"]
        for i, a in enumerate(ghorfas):
            for b in ghorfas[i + 1:]:
                R.place(interior, a, b, "inner", job.door, job.door_height)
    main = max(bits, key=lambda r: (r.polygon.area, -r.id), default=None)
    if main is not None:
        win = next((o for o in interior.openings if o.rooms[0] == main.id and o.kind == "window"), None)
        if win is not None:
            interior.focus = (main.id, win.id)
