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
from .rooms import FACADE, PASS, is_court


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
