"""Villas and the houses of the new districts (SPEC 6c "Villas and houses of the new districts").

Floor 0: a hall at the main door with the U stair beside it (when there are more floors), a couloir, the
salon, the salle a manger (a villa whose floor 0 is over `dining_area`), the cuisine and a wc. Upper floors:
the palier round the stair, a couloir, chambres on the facades and a salle de bain. A single storey also
holds the chambres. The rooms come from the spine engine (`spine.py`); the programs are style lists.
"""
from __future__ import annotations

import numpy as np
import shapely

from . import dar as D
from . import spine as P
from . import stairs as S
from .cuts import parts, snap

GROUND = {"villa": ["salon", "salle_a_manger", "cuisine", "wc", "chambre*"],
          "maison": ["salon", "cuisine", "wc", "chambre*"]}
UPPER = ["chambre", "sdb", "chambre*"]
SINGLE = {"villa": ["salon", "salle_a_manger", "cuisine", "chambre", "sdb", "wc", "chambre*"],
          "maison": ["salon", "cuisine", "chambre", "sdb", "chambre*"]}


def villa(interior, outside, style: dict) -> None:
    plan(interior, outside, style, "villa")


def maison(interior, outside, style: dict) -> None:
    plan(interior, outside, style, "maison")


def programs(job, kind: str) -> dict:
    """floor -> program list (`[interiors.villa] programs` may replace the defaults)."""
    cfg = job.cfg.get("villa", {}).get("programs", {})
    floors = job.interior.floors
    dining = float(job.cfg.get("villa", {}).get("dining_area", 110.0))
    big = job.interior.storeys[0].polygon.area > dining
    out = {}
    for f in range(floors):
        if floors == 1:
            prog = list(cfg.get(f"{kind}_single", SINGLE[kind]))
        elif f == 0:
            prog = list(cfg.get(f"{kind}_ground", GROUND[kind]))
        else:
            prog = list(cfg.get("upper", UPPER))
        out[f] = [t for t in prog if t != "salle_a_manger" or big]
    return out


def plan(interior, outside, style: dict, kind: str) -> None:
    """Floor plans of a villa or a maison."""
    interior.layout = kind
    job = P.modern_job(interior, outside, style)
    entry = P.door_entry(job)
    floors = interior.floors
    core = place_box(job, entry, list(range(floors))) if floors > 1 and entry is not None else None
    if floors > 1 and core is None:
        interior.warnings.append("no stair fits between the floors: a ladder goes up")
    box = core[0] if core else None
    top = floors - 1
    top_region = interior.storeys[top].polygon if box is None else snap(interior.storeys[top].polygon.difference(box))
    square = P.roof_newel(job, top_region)
    progs = programs(job, kind)
    halls, droj = [], None
    for st in interior.storeys:
        f = st.floor
        region = st.polygon
        if box is not None:
            region = shapely_less(region, box)
        if square is not None and f == top:
            region, cell = D.without(region, square, job.thin, job.zs([f]), job.half)
        e = entry if f == 0 else (upper_entry(job, core) if core else entry)
        if e is None:
            e = P.Entry(*region.representative_point().coords[0], 1.0, 0.0)
        cells = P.lay(job, largest(region), e, progs[f], f, (kind, f), hall=f == 0)
        rest = [Cellish(p) for p in parts(snap(region.difference(largest(region))))] if len(parts(region)) > 1 else []
        for c in rest:
            cells.append(c)
        rooms = P.add_rooms(job, cells, f, "home")
        if box is None:
            rooms = P.nooks(job, rooms)
        if box is not None:
            way = P.add_rooms(job, [P.Cell(box, "palier")], f, "home")[0]
            rooms = P.nooks(job, rooms, way)
            P.open_way(job, way, rooms)
            halls.append(way)
        if square is not None and f == top:
            droj = P.add_rooms(job, [P.Cell(cell, "droj")], f, "home")[0]
        P.doors(job, rooms)
    if core is not None:
        box, size, x, y, fd = core
        stair = S.u_record(box, fd, x, y, size, 0, top)
        stair.rooms = [r.id for r in halls]
        interior.stairs.append(stair)
    if square is not None and droj is not None:
        P.newel_rooms(job, square, droj)
    if floors > 1 and core is None:
        D.ladder_up(job)
    P.finish(job)
    focus(job)


class Cellish(P.Cell):
    """A piece of a storey split off by a neck (a room the doors pass connects)."""

    def __init__(self, poly):
        super().__init__(poly, "chambre")


def largest(region):
    got = parts(snap(region))
    return max(got, key=lambda p: p.area) if got else region


def shapely_less(region, box):
    got = parts(snap(region.difference(box)))
    if not got:
        return region
    return shapely.union_all(got)


def place_box(job, entry, floors: list):
    """(box, size, x, y, door frame) of the U stair beside the hall: against the door wall beside the door
    (the side with more room first), slid along the wall and inward in 0.25 m steps until it lies inside
    every storey and its walls keep clear; the narrow box when no full one fits; None when none does."""
    fd = P.door_frame(entry)
    st0 = job.interior.storeys[0].polygon
    x0, _, x1, _ = fd.bounds(st0)
    sides = (1.0, -1.0) if x1 >= -x0 else (-1.0, 1.0)
    half = (job.main.width / 2 if job.main is not None else 0.45) + job.clear + job.half
    x_far, y_far = max(x1, -x0), fd.bounds(st0)[3]
    steps = sorted(((y, e) for y in np.arange(0.0, y_far, 0.25) for e in np.arange(0.0, x_far, 0.25)),
                   key=lambda t: (t[0] + t[1], t[0]))
    for narrow in (False, True):
        size = P.u_numbers(job, False, narrow)
        for y, e in steps:
            for s in sides:
                x = s * (half + e + size["across"] / 2)
                box = S.u_box(fd, x, float(y), size)
                if P.box_fits(job, box, floors):
                    return box, size, x, float(y), fd
    return None


def upper_entry(job, core):
    """Upstairs, the home is entered from the floor landing: the middle of its side toward the door."""
    box, size, x, y, fd = core
    s = 1.0 if x > 0 else -1.0
    p = fd.world(x - s * size["across"] / 2, y + size["landing"] / 2)
    n = -s * fd.u
    return P.Entry(float(p[0]), float(p[1]), float(n[0]), float(n[1]))


def focus(job) -> None:
    """The `interior` view: the salon toward its widest window."""
    interior = job.interior
    salon = next((r for r in interior.rooms if r.type == "salon"), None)
    if salon is None:
        return
    wins = [o for o in interior.openings if o.rooms[0] == salon.id and o.kind in ("window", "balcony")]
    if wins:
        interior.focus = (salon.id, max(wins, key=lambda o: (o.width, -o.id)).id)
