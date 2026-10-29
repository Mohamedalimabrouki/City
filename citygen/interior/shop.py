"""Shops and cafes of ground floors (SPEC 6c "Shops and cafes"), carved from floor 0 before the layout.

A shop front (`shop` opening) gets a hanout (unit `shop`) along its wall: the opening's width plus `clear`
and half a partition at both sides, clipped so the house door keeps `clear`; `[interiors.shop] depth`
(stream `shop`) or the whole band of a courtyard house, at most half the storey's depth; a makhzen behind it
when there is depth for it and for the house, else beside it away from the house door, else none. It opens
only on the street. A cafe front gives a qahwa (unit `cafe`) the street side of floor 0 with a wc and a
makhzen behind it.
"""
from __future__ import annotations

import math

import shapely
from shapely.geometry import LineString, Point

from ..rng import stream
from . import rooms as R
from .cuts import Frame, clip, parts, snap, solid
from .model import Room

E = 1.0   # meters past the region's edges


def front(interior, kind: str = "shop"):
    """The shop or cafe front opening of floor 0, or None."""
    return next((o for o in interior.openings if o.kind == "shop" and o.floor == 0 and o.piece), None)


def wall_frame(o, ext: float) -> Frame:
    """A frame at an opening's inner wall face: u along the wall, v inward."""
    inward = (math.sin(o.yaw), -math.cos(o.yaw))
    x, y = o.x + inward[0] * ext, o.y + inward[1] * ext
    return Frame(x, y, math.atan2(inward[1], inward[0]) - math.pi / 2)


def depth_in(poly, fr: Frame, at: float = 0.0) -> float:
    """Length of the first stretch of the line u = `at` from the wall inward inside `poly`."""
    p0 = fr.world(at, -0.05)
    ray = LineString([p0, fr.world(at, 100.0)]).intersection(poly)
    segs = [g for g in getattr(ray, "geoms", [ray]) if g.geom_type == "LineString" and g.length > 1e-6]
    if not segs:
        return 0.0
    first = min(segs, key=lambda g: Point(p0).distance(g))
    return float(fr.local(max(first.coords, key=lambda c: fr.local(c)[1]))[1])


def rng(interior):
    return stream(interior.seed, "interior", interior.city_id, interior.building, "shop")


def souk(job, poly, court: bool, small: bool = False) -> tuple:
    """(shop rooms, the rest of floor 0) of a house with a shop front: the hanout and its makhzen, carved
    from `poly` (floor 0). `court`: a courtyard house, whose hanout takes the whole band; `small`: a house
    whose stair found no room beside the shop (a 2 m hanout, no makhzen)."""
    interior = job.interior
    o = front(interior)
    if o is None:
        return [], poly
    cfg = job.cfg.get("shop", {})
    fr = wall_frame(o, job.ext)
    w = o.width / 2
    reach = w + job.clear + job.half
    lo_x, hi_x = -reach, reach
    door = job.main
    side, pier = 0.0, None
    if door is not None and door.floor == 0 and abs((door.yaw - o.yaw + math.pi) % (2 * math.pi) - math.pi) < 0.05:
        xd = float(fr.local((door.x, door.y))[0])
        keep = door.width / 2 + job.clear + job.half
        side = 1.0 if xd > 0 else -1.0
        gap = abs(xd) - w - door.width / 2                    # the pier between the shop front and the door
        if 0.0 < gap < job.clear + 2 * job.half:
            mid = side * (w + gap / 2)                        # too narrow to keep clear: the partition stands on it
            lo_x, hi_x = (lo_x, mid) if side > 0 else (mid, hi_x)
            a, b = sorted((side * w, side * (w + gap)))
            pier = fr.rect(a, -E, b, 0.1)
            job.interior.piers.append(pier)
        elif side > 0:
            hi_x = min(hi_x, xd - keep)
        else:
            lo_x = max(lo_x, xd + keep)
    full = depth_in(poly, fr)
    a, b = (float(v) for v in cfg.get("depth", [3.0, 4.0]))
    d = float(rng(interior).uniform(a, b))
    half = (fr.bounds(poly)[3] - 0.0) / 2                  # at most half the storey's depth
    d = min(full + E, half) if court else min(d, full / 2, 2.0 if small else 1e9)
    zones = job.zs([0])
    strip = clip(poly, fr.rect(-50, -E, 50, max(d, 0.5)))
    if not (pier is not None and side < 0):
        lo_x = side_line(job, strip, fr, lo_x, zones, -1.0, -w, -50.0)
    if not (pier is not None and side > 0):
        hi_x = side_line(job, strip, fr, hi_x, zones, 1.0, w, 50.0)
    if not court:
        band = clip(poly, fr.rect(lo_x, -E, hi_x, 100))
        got = job.free(band, fr, 1, d, [0], 1.5, full - 1.5) if full > 3.0 else None
        d = got if got is not None else d
    d = clear_of(job, fr, lo_x, hi_x, d)
    hanout = pick(poly, fr.rect(lo_x, -E, hi_x, d), fr)
    cells = [g for g in (job.roof.stair if job.roof is not None else None, getattr(job, "keep_free", None))
             if g is not None]
    for cell in cells if hanout is not None else []:
        stair = cell.buffer(0.3, join_style="mitre")
        if hanout is not None and hanout.intersects(stair):   # the house's stair cell stays the house's
            got = parts(solid(shapely.difference(hanout, stair, grid_size=1e-6)))
            inside = Point(*fr.world(0.0, 0.3))
            less = min(got, key=lambda p: (p.distance(inside), -p.area)) if got else None
            if less is not None and job.fits(less, "hanout") and less.distance(inside) < 0.05:
                hanout = less
    if hanout is None:
        return [], poly
    rest = snap(poly.difference(hanout))
    makhzen = None
    store = float(cfg.get("makhzen", 1.8))
    if not court and full - d >= store + float(cfg.get("keep", 3.0)):
        band = clip(rest, fr.rect(lo_x, d - 0.01, hi_x, 100))
        at = job.free(band, fr, 1, d + store, [0], d + 1.5, d + 2.4)
        if at is not None:
            makhzen = pick(rest, fr.rect(lo_x, d - 0.01, hi_x, at), fr)
    if makhzen is None and not small:
        makhzen = beside(job, poly, rest, fr, lo_x, hi_x, d, -side if side else -1.0, cfg)
    if small:
        makhzen = None
    if makhzen is not None and any(makhzen.distance(p) < 0.3 for p in avoid(job)):
        makhzen = None
    if makhzen is not None:
        left = snap(rest.difference(makhzen))
        if (len(parts(left)) == 1 and job.fits(makhzen, "makhzen")
                and left.area >= float(cfg.get("house_least", 20.0))):    # a tiny house keeps its floor
            rest = left
        else:
            makhzen = None
    pieces = sorted(parts(rest), key=lambda p: -p.area)
    if not pieces:
        return [], poly
    probe = job.probe() if job.spot is not None else pieces[0].representative_point()
    home = min(pieces, key=lambda p: (p.distance(probe), -p.area))
    for p in pieces:
        if p is home:
            continue
        if p.distance(hanout) < 1e-4:
            hanout = snap(shapely.union_all([hanout, p]))
        else:
            home = snap(shapely.union_all([home, p]))
    st = interior.storeys[0]
    out = [Room(R.next_id(interior), 0, "hanout", largest(hanout), st.z, st.height, unit="shop")]
    if makhzen is not None:
        out.append(Room(R.next_id(interior) + 1, 0, "makhzen", makhzen, st.z, st.height, unit="shop"))
    return out, home


def avoid(job) -> list:
    """What a shop must leave to the house: the point inside the house door, the roof stair room's floor."""
    out = [job.probe()] if job.spot is not None else []
    if job.roof is not None and job.roof.stair is not None:
        out.append(job.roof.stair)
    if getattr(job, "keep_free", None) is not None:   # the house's own stair cell (a tiny house)
        out.append(job.keep_free)
    return out


def clear_of(job, fr: Frame, lo_x: float, hi_x: float, d: float) -> float:
    """The hanout's depth cut back so it keeps clear of the house door (on another wall) and of the floor
    under the roof's stair room and of a tiny house's own stair cell; never under 1.5 m."""
    keep = (job.main.width / 2 if job.main is not None else 0.45) + job.clear + job.half
    own = getattr(job, "keep_free", None)
    for thing in avoid(job):
        u0, v0, u1, v1 = fr.bounds(thing.buffer(keep if thing.geom_type == "Point" else 0.3))
        if u1 > lo_x and u0 < hi_x and v0 < d and v0 > 0.4:
            d = max(min(d, v0), 1.5)
    return d


def side_line(job, strip, fr: Frame, at: float, zones: list, sgn: float, inner: float, outer: float) -> float:
    """A hanout side moved clear of the openings, never into the shop front."""
    got = job.free(strip, fr, 0, at, [0], *sorted((inner + sgn * job.half, at + sgn * job.shift)))
    return got if got is not None else at


def beside(job, poly, rest, fr: Frame, lo_x: float, hi_x: float, d: float, sgn: float, cfg: dict):
    """A makhzen along the wall beside the hanout (away from the house door) when `makhzen_side` m of wall
    remain there; None otherwise."""
    room = float(cfg.get("makhzen_side", 1.5))
    x0, _, x1, _ = fr.bounds(poly)
    start = hi_x if sgn > 0 else lo_x
    left = (x1 - start) if sgn > 0 else (start - x0)
    if left < room + 0.3:
        return None
    width = min(2.4, left - 0.3) if left < room + 2.6 else 2.0
    if left - width < 2.0:
        width = left + E                              # the rest of the wall: no sliver of house beyond it
    strip = clip(rest, fr.rect(-50, -E, 50, d))
    end = start + sgn * width
    if left - width >= 2.0:
        got = job.free(strip, fr, 0, end, [0], *sorted((start + sgn * room, start + sgn * (width + 0.6))))
        if got is None:
            return None
        end = got
    return pick(rest, fr.rect(min(start, end), -E, max(start, end), d), fr)


def pick(poly, rect, fr: Frame):
    got = parts(snap(clip(poly, rect)))
    if not got:
        return None
    return max(got, key=lambda p: p.area)


def largest(geom):
    got = parts(snap(geom))
    return max(got, key=lambda p: p.area) if got else geom


def doors(job) -> None:
    """The makhzen opens into its hanout (or qahwa), the wc into the qahwa."""
    interior = job.interior
    for r in sorted(interior.rooms, key=lambda r: r.id):
        if r.type in ("makhzen", "wc") and r.unit in ("shop", "cafe") and not any(
                r.id in o.rooms and o.kind in R.PASS for o in interior.openings):
            host = next((h for h in interior.rooms if h.type in ("hanout", "qahwa") and h.unit == r.unit), None)
            if host is not None and R.place(interior, r, host, "inner", job.door, job.door_height) is None:
                R.place(interior, r, host, "inner", interior.rules.get("narrow", 0.7), job.door_height,
                        clear=interior.rules.get("narrow_clear", 0.05))


def cafe(job, poly, keep=None) -> tuple:
    """(cafe rooms, the rest) of a colonial floor 0 with a cafe front: the qahwa along the street wall
    (depth `[interiors.cafe] depth`, at most half the storey), a wc and a makhzen behind it. `keep`: a
    polygon the cafe must leave alone (the core and its couloir)."""
    interior = job.interior
    o = front(interior)
    if o is None:
        return [], poly
    cfg = job.cfg.get("cafe", {})
    fr = wall_frame(o, job.ext)
    full = depth_in(poly, fr)
    a, b = (float(v) for v in cfg.get("depth", [5.0, 8.0]))
    d = min(float(rng(interior).uniform(a, b)), full / 2)
    room = poly if keep is None else snap(poly.difference(keep))
    got = job.free(room, fr, 1, d, [0], 2.5, max(full - 2.0, 2.6))
    d = got if got is not None else d
    side = [p for p in parts(snap(clip(room, fr.rect(-200, -E, 200, d))))]
    if not side:
        return [], poly
    probe = Point(*fr.world(0.0, 0.3))
    qahwa = min(side, key=lambda p: (p.distance(probe), -p.area))
    rest = snap(poly.difference(qahwa))
    st = interior.storeys[0]
    out = [Room(R.next_id(interior), 0, "qahwa", qahwa, st.z, st.height, unit="cafe")]
    deep = float(cfg.get("wc", [1.4, 1.6])[1])
    wide = float(cfg.get("wc", [1.4, 1.6])[0])
    store = float(cfg.get("makhzen", 2.0))
    q0, _, q1, _ = fr.bounds(qahwa)
    behind = clip(rest, fr.rect(q0, d - 0.01, q1, d + deep))
    if keep is not None:
        behind = solid(shapely.difference(behind, keep, grid_size=1e-6))
    far = q1 if abs(q1) >= abs(q0) else q0                    # from the end away from the door
    sgn = -1.0 if far == q1 else 1.0
    cuts = [far + sgn * store, far + sgn * (store + wide)]
    fixed = []
    for at in cuts:
        got = job.free(behind, fr, 0, at, [0], *sorted((at - 0.5, at + 0.5)))
        fixed.append(got if got is not None else at)
    m = pick(behind, fr.rect(min(far, fixed[0]), d - 0.01, max(far, fixed[0]), d + deep), fr)
    w = pick(behind, fr.rect(min(fixed), d - 0.01, max(fixed), d + deep), fr)
    for kind, piece in (("makhzen", m), ("wc", w)):
        if piece is not None and piece.distance(qahwa) < 1e-4 and job.fits(piece, kind):
            left = snap(rest.difference(piece))
            if parts(left):
                rest = shapely.union_all(parts(left))
                out.append(Room(R.next_id(interior) + len(out), 0, kind, piece, st.z, st.height, unit="cafe"))
    return out, rest
