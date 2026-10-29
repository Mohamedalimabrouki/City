"""Room layouts (SPEC 6c): the storeys of a dwelling, then the rooms of its layout.

For now (prompt 45) every layout gets one placeholder room per storey holding the facade openings of its
floor; prompts 46-47 replace the per-layout functions in `PLANS`.
"""
from __future__ import annotations

from dataclasses import replace

from shapely.geometry.polygon import orient
from shapely.ops import unary_union

from ..city.geo import polygons
from ..city.massing import masses
from . import InteriorError
from .context import exterior_wall, layout_of
from .model import Interior, Room, Storey

TRADITIONAL = ("dar", "compact", "small", "koubba")   # layouts with traditional partitions, beams and tiles
LIGHTS = ("window", "balcony")                         # facade openings that light a room


def plan_interior(outside, style: dict) -> Interior:
    """The interior of the building `outside` replays: storeys, then rooms by layout."""
    b, plan, k = outside.b, outside.plan, outside.k
    layout = layout_of(plan, b, style)
    walls_cfg = style.get("interiors", {}).get("walls", {})
    partition = walls_cfg.get("partition", 0.2) if layout in TRADITIONAL else walls_cfg.get("partition_modern", 0.15)
    walls = {"exterior": exterior_wall(style, outside.district), "court": float(walls_cfg.get("court", 0.3)),
             "partition": float(partition)}
    home = next((h for h in getattr(plan, "households", ()) if h.building == k), None)
    household = None if home is None else {"building": home.building, "family": home.family, "trade": home.trade,
                                           "wealth": home.wealth, "door": home.door, "members": home.members}
    interior = Interior(outside.ctx.world.seed, plan.settlement.name, plan.settlement.id, k, b.kind, layout,
                        outside.district, outside.high, outside.fh, household, walls)
    interior.storeys = storeys(outside, walls["exterior"])
    if not interior.storeys:
        raise InteriorError(f"No. {k} in {plan.settlement.name} is too narrow to have an inside: its walls "
                            f"({walls['exterior']} m thick) leave no floor.")
    interior.openings = [replace(o) for o in outside.openings]
    interior.warnings = list(outside.warnings)
    PLANS.get(layout, placeholder)(interior, outside, style)
    return interior


def storeys(outside, thickness: float) -> list:
    """One `Storey` per floor: the masses standing at that floor, shrunk by the exterior wall (mitre joins,
    so courtyards grow by it). A neck thinner than two walls leaves slivers: the largest part is kept."""
    b, high, fh = outside.b, outside.high, outside.fh
    ms = masses(b)
    out = []
    for f in range(max(1, int(b.floors))):
        mid = (f + 0.5) * fh
        standing = [m.polygon for m in ms if m.base <= mid < m.top]
        parts = polygons(unary_union(standing).buffer(-thickness, join_style="mitre")) if standing else []
        if parts:
            out.append(Storey(f, high + f * fh, fh, orient(max(parts, key=lambda p: p.area), 1.0)))
    return out


def placeholder(interior: Interior, outside, style: dict) -> None:
    """One room per storey (type `room`, unit `home`) holding the facade openings of its floor."""
    for st in interior.storeys:
        lit = any(o.lit for o in interior.openings if o.floor == st.floor and o.kind in LIGHTS)
        interior.rooms.append(Room(len(interior.rooms), st.floor, "room", st.polygon, st.z, st.height, lit=lit))
    room_of = {r.floor: r.id for r in interior.rooms}
    for o in interior.openings:
        o.rooms = (room_of.get(o.floor, -1), -1)


PLANS: dict = {}   # layout -> function(interior, outside, style); prompts 46-47 fill it, the rest get `placeholder`
