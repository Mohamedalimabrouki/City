"""The domed house (`koubba`, SPEC 6c "Domed house"): the koubba under the dome and an annex.

The koubba is the square of side twice the dome's radius (the largest of `b.domes`) under the dome, in the
storey's frame, its sides moved by `free_cut` to keep clear of every opening, clipped to the storey; its
ceiling is the dome. The rest is the annex, cut into cells about `annex_cell` m long: an entry (a skifa)
when the street door does not open into the koubba, then a matbakh, a bit el ma and a bit el mouna when
they fit (the store gives way first), other cells bits.
"""
from __future__ import annotations

import shapely

from . import dar as D
from . import program as PR
from . import rooms as R
from . import spine as P
from .cuts import Cell, Frame, absorb, cut, parts, shared, snap


def plan(interior, outside, style: dict) -> None:
    interior.layout = "koubba"
    job = D.Job(interior, outside, style)
    st0 = interior.storeys[0]
    poly = st0.polygon
    square = P.roof_newel(job, poly) if interior.floors == 1 else None
    droj_poly = None
    if square is not None:
        poly, droj_poly = D.without(poly, square, job.thin, job.zs([0]), job.half)
    fr = Frame.of(getattr(interior, "full0", None) or st0.polygon)   # a shop carved first keeps the frame
    dome = max(outside.b.domes, key=lambda d: d[2]) if outside.b.domes else None
    koubba = under_dome(job, poly, fr, dome) if dome is not None else None
    cells = []
    if koubba is None:
        koubba = max(parts(poly), key=lambda p: p.area)
    cells.append(Cell(koubba, "koubba", "", "koubba"))
    annex = [p for p in parts(snap(poly.difference(koubba)))]
    cells += annex_cells(job, annex, koubba)
    if droj_poly is not None:
        cells.append(Cell(droj_poly, "droj", "", "stair"))
    cells = absorb(cells, job.minimums, R.KEEP + PR.SERVICES, job.piece, (), job.largest)   # services keep their type
    rooms = [r for c in cells for r in P.add_rooms(job, [c], 0, "home")]
    for f in range(1, interior.floors):          # domed houses have one floor; any more are ghorfas
        rooms += P.add_rooms(job, [Cell(p, "ghorfa") for p in parts(interior.storeys[f].polygon)], f, "home")
    room_doors(job, rooms)
    swap_services(job, rooms)
    droj = next((r for r in rooms if r.type == "droj"), None)
    if square is not None and droj is not None:
        P.newel_rooms(job, square, droj)
    if interior.floors > 1:
        D.ladder_up(job)
    P.finish(job)
    k = next((r for r in interior.rooms if r.type == "koubba"), None)
    door = next((o for o in interior.openings if o.kind == "door" and o.floor == 0 and o.piece), None)
    if k is not None and door is not None:
        interior.focus = (k.id, door.id)


def under_dome(job, poly, fr: Frame, dome):
    """The square under the dome, its sides clear of the openings, clipped to the storey."""
    x, y, r = float(dome[0]), float(dome[1]), float(dome[2])
    cu, cv = fr.local((x, y))
    u0, v0, u1, v1 = fr.bounds(poly)
    lines = [(0, cu - r, u0), (0, cu + r, u1), (1, cv - r, v0), (1, cv + r, v1)]
    got = []
    for axis, at, wall in lines:
        if abs(at - wall) < 1.0 or (at < wall if wall in (u0, v0) else at > wall):
            got.append(wall - 1.0 if wall in (u0, v0) else wall + 1.0)     # the wall itself bounds it
            continue
        pos = job.free(poly, fr, axis, at, [0])
        got.append(pos if pos is not None else (wall - 1.0 if wall in (u0, v0) else wall + 1.0))
    sq = shapely.intersection(poly, fr.rect(got[0], got[2], got[1], got[3]), grid_size=1e-6)
    pieces = parts(snap(sq))
    if not pieces:
        return None
    return max(pieces, key=lambda p: p.area)


def annex_cells(job, annex: list, koubba) -> list:
    """The annex's cells and their types: the entry, then the services, other cells bits."""
    cfg = job.cfg.get("koubba", {})
    step = float(cfg.get("annex_cell", 3.0))
    cells = []
    for p in annex:
        fr = Frame.of(p)
        u0, _, u1, _ = fr.bounds(p)
        n = max(1, int(round((u1 - u0) / step)))
        pieces = [p]
        for i in range(1, n):
            at = job.free(p, fr, 0, u0 + i * (u1 - u0) / n, [0], u0 + 1.0, u1 - 1.0)
            if at is None:
                continue
            nxt = []
            for q in pieces:
                lo, hi = cut(q, fr, 0, at)
                nxt += lo + hi
            pieces = nxt
        cells += [Cell(q, "", "annex", "corner") for q in pieces]
    small = dict(job.minimums, maqsura=job.minimums.get("bit_el_mouna", (1.5, 0.9)))   # a store-sized cell stays
    cells = absorb(cells, small, R.KEEP, job.piece, (), job.largest)
    probe = job.probe() if job.spot is not None else None
    if probe is not None and not koubba.buffer(0.05).contains(probe):
        entry = next((c for c in cells if c.poly.distance(probe) < 0.05), None)
        if entry is not None and job.fits(entry.poly, "skifa") and len(cells) > 1:
            entry.type = "skifa"
    free = [c for c in cells if not c.type]
    ref = next((c.poly for c in cells if c.type == "skifa"), None)
    for service in ("matbakh", "bit_el_ma", "bit_el_mouna"):
        for avoid in (PR.avoid_way(job, cells, koubba) if service != "bit_el_mouna" else (set(),)):
            if PR.place(job, cells, free, service, ref, [], avoid) is not None:
                break
    big = job.largest.get("bit_el_mouna", 8.0)
    for c in [c for c in cells if not c.type and not job.fits(c.poly, "bit")]:
        cells.remove(c)                               # a strip too narrow for a bit: stores of their size
        cells += halves(job, c, big)
    for c in [c for c in cells if not c.type]:
        small = c.poly.area <= big and job.fits(c.poly, "bit_el_mouna")
        c.type = "bit" if job.fits(c.poly, "bit") or not small else "bit_el_mouna"
    return absorb(cells, job.minimums, R.KEEP + ("matbakh", "bit_el_ma"), job.piece, (), job.largest)


def room_doors(job, rooms: list) -> None:
    """Every annex room opens into the koubba, else into the entry; the entry into the koubba."""
    interior = job.interior
    koubba = next((r for r in rooms if r.type == "koubba"), None)
    entry = next((r for r in rooms if r.type == "skifa"), None)
    for r in sorted(rooms, key=lambda r: (r.type != "skifa", r.id)):
        if r.type in ("koubba", "droj", "ghorfa") or koubba is None:
            continue
        rules = interior.rules
        done = False
        for width, clear in ((job.door, None), (rules.get("narrow", 0.7), rules.get("narrow_clear", 0.05))):
            for host in [h for h in (koubba, entry) if h is not None and h is not r]:
                if shared(r.polygon, host.polygon) > 0.9 and R.place(interior, r, host, "inner", width,
                                                                    job.door_height, clear=clear) is not None:
                    done = True
                    break
            if done:
                break


def swap_services(job, rooms: list) -> None:
    """A matbakh or bit el ma no door reaches trades its type with a reached bit or store that holds it
    (the cut-off cell then joins a neighbour in the doors pass)."""
    interior = job.interior
    opened = {i for o in interior.openings if o.kind in R.PASS for i in o.rooms}
    order = {"matbakh": 0, "bit_el_ma": 1}
    for svc in sorted([r for r in rooms if r.type in order and r.id not in opened], key=lambda r: order[r.type]):
        for other in sorted([r for r in rooms if r.id in opened and r.type in ("bit", "bit_el_mouna")],
                            key=lambda r: r.polygon.area):
            if job.fits(other.polygon, svc.type) and other.polygon.area <= job.largest.get(svc.type, 99.0):
                if other.type == "bit" and not any(r.type == "bit" and r is not other for r in rooms):
                    continue
                svc.type, other.type = other.type, svc.type
                break


def halves(job, c, big: float) -> list:
    """A narrow annex strip halved along its length (each cut clear of the openings) until every piece is a
    store's size; the pieces, untyped."""
    if c.poly.area <= big:
        return [c]
    fr = Frame.of(c.poly)
    for axis in (0, 1):
        b0, b1 = fr.bounds(c.poly)[axis], fr.bounds(c.poly)[axis + 2]
        at = job.free(c.poly, fr, axis, (b0 + b1) / 2, [0], b0 + 0.9, b1 - 0.9)
        if at is None:
            continue
        lo, hi = cut(c.poly, fr, axis, at)
        if len(lo) == 1 and len(hi) == 1 and min(lo[0].area, hi[0].area) >= job.minimums.get("bit_el_mouna", (1.5, 0.9))[0]:
            return halves(job, Cell(lo[0], "", c.band, c.part), big) + halves(job, Cell(hi[0], "", c.band, c.part), big)
    return [c]
