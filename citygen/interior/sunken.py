"""The sunken entry (open items 47.1 + 48.1, SPEC 6c `steps`): where the storey is too shallow behind a
street door for its entry steps, the entry room's floor stays at the door's threshold and the steps up to
floor 0 stand in the next rooms, rising from each of its inner openings (the common old-town answer). The entry
room keeps floor 0's ceiling (it is taller), the inner opening drops with it, and the steps' open sides
take a railing (`stairs.rails`).
"""
from __future__ import annotations

import math
from types import SimpleNamespace

import numpy as np
from shapely.geometry import Point

from . import stairs as S
from .plancheck import step_faults
from . import rooms as R
from .plancheck import KITCHENS, WET
from .rooms import FACADE, PASS, is_court

ASIDE = WET + KITCHENS   # rooms no sunken entry's steps stand in (round 6)


def sink(interior, style: dict) -> list:
    """Sink the entry room of every faulty flight of entry steps that can be: the reasons the others
    cannot (empty when every faulty flight was moved)."""
    cfg = style.get("interiors", {}).get("stairs", {})
    plan = interior.rules.get("plan", {})
    others = [s for s in interior.stairs if s.kind != "steps" and s.floor == 0]
    why = []
    for s in [s for s in interior.stairs if s.kind == "steps"]:
        if step_faults(s, others, plan):
            got = _sink_one(interior, s, cfg, plan, others)
            if got:
                why.append(got)
    return why


def _sink_one(interior, s, cfg: dict, plan: dict, others: list) -> str:
    """Sink the room of flight `s` and move its steps to that room's inner openings ("" when done, else why
    not)."""
    by_id = {r.id: r for r in interior.rooms}
    room = by_id.get(s.rooms[0])
    if room is None or room.floor != 0 or s.riser <= 0.0:
        return "the steps go down or have no room"
    reroute(interior, room)
    mine = [o for o in interior.openings if o.floor == 0 and room.id in o.rooms]
    inner = [o for o in mine if o.kind not in FACADE and o.kind in PASS]   # windows stay where they are
    alone = all(r is room or r.floor != 0 for r in interior.rooms)   # a one-room floor 0 sinks whole
    if sum(o.kind in ("door", "shop") for o in mine) != 1 or not (inner or alone):
        return f"the entry room has {len(inner)} inner openings"
    if any(o.polygon.intersection(room.polygon).area > 0.01 for o in interior.stairs if o is not s):
        return "a stair stands in the entry room"
    rise = s.risers * s.riser
    notes, flights = [], []
    for o in inner:                                   # steps up through every inner opening
        new = _flight(interior, room, o, by_id, rise, cfg, notes)
        if isinstance(new, str):
            return new
        if step_faults(new, others + flights, plan) or any(new.polygon.intersects(f.polygon) for f in flights):
            return "the next room is too short for the steps"
        flights.append(new)
    i = interior.stairs.index(s)
    interior.stairs[i:i + 1] = flights
    room.z, room.height = room.z - rise, room.height + rise
    head = S.level(interior, 0) + float(cfg.get("sunken_head", 1.0))
    for o in inner:
        o.z0, o.z1 = o.z0 - rise, max(o.z1 - rise, head)
    old = next((w for w in interior.warnings if w.startswith(f"the entry steps are steep: {s.risers} risers")), None)
    interior.warnings = [w for w in interior.warnings if w is not old] + notes
    return ""


def _flight(interior, room, o, by_id: dict, rise: float, cfg: dict, notes: list):
    """The steps from the sunken `room` up through its inner opening `o` into the next room (why not, as a
    string, when that room is the court or another floor)."""
    nxt = by_id.get(o.rooms[1] if o.rooms[0] == room.id else o.rooms[0])
    if nxt is None or nxt.floor != 0 or nxt.open or is_court(nxt):
        return "the entry room opens into the court"
    front = np.array([-math.sin(o.yaw), math.cos(o.yaw)])
    if not room.polygon.contains(Point(o.x + front[0] * 0.3, o.y + front[1] * 0.3)):
        front = -front                                # the normal pointing out of the next room
    spot = SimpleNamespace(x=o.x, y=o.y, nx=float(front[0]), ny=float(front[1]))
    new = S.steps(nxt, spot, o.width, rise, cfg, notes, interior.walls["partition"] / 2)
    if new is None:
        return "the next room is too short for the steps"
    new.sunk = room.id
    return new


def reroute(interior, room) -> None:
    """`_reroute`, then a bit's opening goes where the room keeps another dry one (`_off_bits`)."""
    _reroute(interior, room)
    inner = lambda: [o for o in interior.openings if o.floor == 0 and room.id in o.rooms and o.kind in PASS
                     and o.kind not in FACADE]
    by_id = {r.id: r for r in interior.rooms}
    _off_bits(interior, inner, lambda o: by_id.get(o.rooms[1] if o.rooms[0] == room.id else o.rooms[0]))


def _reroute(interior, room) -> None:
    """The sunken `room`'s inner openings into a wet room or the matbakh go when that room can be reached
    another way (a door on a reached neighbour or the court), after `room` got a door into another
    neighbour if it had none; the steps then never stand in them (round 6). Undone when anything fails or
    a dar's court would show from the street."""
    by_id = {r.id: r for r in interior.rooms}
    inner = lambda: [o for o in interior.openings if o.floor == 0 and room.id in o.rooms and o.kind in PASS
                     and o.kind not in FACADE]
    other = lambda o: by_id.get(o.rooms[1] if o.rooms[0] == room.id else o.rooms[0])
    bad = [o for o in inner() if other(o) is not None and other(o).type in ASIDE]
    if not bad:
        return
    before = list(interior.openings)
    if all(o in bad for o in inner()) and _door(interior, room, by_id, avoid=ASIDE + ("droj",)) is None:
        return
    for o in bad:
        n = other(o)
        interior.openings.remove(o)
        if n.id not in R.reached(interior) and _door(interior, n, by_id, avoid=ASIDE, skip=room.id, narrow=True) is None:
            interior.openings = before
            _trade(interior, n, room)
            return
    if not R.reached(interior) >= {r.id for r in interior.rooms if r.type not in R.VOIDS} or (
            interior.layout == "dar" and R.sees_court(interior)):
        interior.openings = before


def _door(interior, r, by_id: dict, avoid: tuple, skip: int = -9, narrow: bool = False):
    """A door from `r` into its reached neighbour with the longest piece that holds one (none of the types
    `avoid`, not room `skip`; a narrow door when `narrow` and no full one fits); None when none does."""
    rules, seen = interior.rules, R.reached(interior)
    sizes = [(rules["door"], rules.get("inner_clear", rules["clear"]))]
    sizes += [(rules.get("narrow", 0.7), rules.get("narrow_clear", 0.05))] if narrow else []
    near = sorted(R.neighbours(interior, r), key=lambda t: (-t[0], t[1].id))
    for width, clear in sizes:
        for _, n in near:
            if n.id in seen and n.id != skip and n.floor == 0 and n.type not in avoid + R.VOIDS + ("droj",) \
                    and n.unit == r.unit:
                kind = "court_door" if is_court(n) and n.open else "inner"
                o = R.place(interior, r, n, kind, width, rules["door_height"], clear=clear)
                if o is not None:
                    return o
    return None


def _trade(interior, n, room, tries: int = 6) -> None:
    """The wet room or matbakh `n` reached only through the sunken `room` trades its type with a bit,
    maqsura or store of floor 0 that does not touch `room` when the plan check finds no more faults; the
    steps then rise into a dry room (round 6)."""
    base = len(R.check(interior))
    near = {m.id for _, m in R.neighbours(interior, room)}
    others = [r for r in interior.rooms if r.floor == 0 and r.unit == n.unit and r.id not in near and r is not room
              and r.type in ("bit", "maqsura", "bit_el_mouna")]
    for r in sorted(others, key=lambda r: (abs(r.polygon.area - n.polygon.area), r.id))[:tries]:
        n.type, r.type = r.type, n.type
        if len(R.check(interior)) <= base:
            return
        n.type, r.type = r.type, n.type


def _off_bits(interior, inner, other) -> None:
    """A bit takes the steps only when nothing else does: an opening into a bit goes when the sunken room
    keeps another into a dry room that is no bit and the bit stays reached (round 6)."""
    dry = [o for o in inner() if other(o) is not None and other(o).type not in ASIDE + ("bit",)]
    if not dry:
        return
    for o in [o for o in inner() if other(o) is not None and other(o).type == "bit"]:
        interior.openings.remove(o)
        if other(o).id not in R.reached(interior):
            interior.openings.append(o)
