"""Room layouts (SPEC 6c): the storeys of a dwelling, then the rooms of its layout.

Prompt 46 lays out the old town's houses (`dar.py`, `compact.py`), prompt 47 every other dwelling
(`koubba.py`, `villa.py`, `flats.py` on the `spine.py` engine) and the shops and cafes of ground floors
(`shop.py`); `placeholder` (one room per storey) remains for a layout without a plan.
"""
from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

from shapely import set_precision
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

from ..city.geo import polygons
from ..city.massing import masses
from . import InteriorError
from .context import exterior_wall, layout_of
from .cuts import GRID
from .model import Interior, Room, Storey

TRADITIONAL = ("dar", "compact", "small", "koubba")   # layouts with traditional partitions, beams and tiles
SOUK = ("dar", "compact", "small", "koubba", "maison")   # layouts whose shop front gets a hanout
LIGHTS = ("window", "balcony")                         # facade openings that light a room
CLOSE = 1e-4                                           # meters: masses this near are one (rounding on shared edges)


def plan_interior(outside, style: dict) -> Interior:
    """The interior of the building `outside` replays: storeys, then rooms by layout."""
    b, plan, k = outside.b, outside.plan, outside.k
    layout = layout_of(plan, b, style)
    walls_cfg = style.get("interiors", {}).get("walls", {})
    partition = walls_cfg.get("partition", 0.2) if layout in TRADITIONAL else walls_cfg.get("partition_modern", 0.15)
    walls = {"exterior": exterior_wall(style, outside.district), "court": float(walls_cfg.get("court", 0.3)),
             "partition": float(partition),
             "roof": float(style.get("interiors", {}).get("floors", {}).get("roof_wall", 0.2))}   # roof rooms (49)
    home = next((h for h in getattr(plan, "households", ()) if h.building == k), None)
    household = None if home is None else {"building": home.building, "family": home.family, "trade": home.trade,
                                           "wealth": home.wealth, "door": home.door, "members": home.members}
    interior = Interior(outside.ctx.world.seed, plan.settlement.name, plan.settlement.id, k, b.kind, layout,
                        outside.district, outside.high, outside.fh, household, walls)
    interior.storeys = storeys(outside, walls["exterior"], walls["court"])
    if not interior.storeys:
        raise InteriorError(f"No. {k} in {plan.settlement.name} is too narrow to have an inside: its walls "
                            f"({walls['exterior']} m thick) leave no floor.")
    interior.openings = [replace(o) for o in outside.openings]
    interior.warnings = list(outside.warnings)
    reveals(interior, float(walls_cfg.get("reveal", 0.2)), float(walls_cfg.get("reveal_wall", 0.15)))
    if layout in SOUK and any(o.kind == "shop" and o.floor == 0 for o in interior.openings):
        with_shop(interior, outside, style, layout)
    else:
        PLANS.get(layout, placeholder)(interior, outside, style)
    from .plancheck import settle, trim
    trim(interior)
    settle(interior)
    return interior


def with_shop(interior: Interior, outside, style: dict, layout: str) -> None:
    """A house with a shop front: the hanout and makhzen carved from floor 0 first, then the layout on the
    rest (floor 0's storey is the rest while it runs); the shop opens only on the street. When the house's
    stair then finds no room, a smaller shop (2 m, no makhzen) is tried, then one that leaves free the stair
    cell the house would have without a shop; the first plan whose stairs work wins, else the one with the
    fewest problems."""
    from . import rooms as R
    from . import shop
    from .dar import Job
    full = interior.storeys[0].polygon
    facade, warnings = [replace(o) for o in interior.openings], list(interior.warnings)

    def fresh():
        interior.rooms, interior.stairs, interior.features, interior.piers = [], [], [], []
        interior.openings, interior.warnings, interior.flats = [replace(o) for o in facade], list(warnings), []
        interior.layout, interior.focus = layout, None

    def run(small: bool, stair) -> bool:
        """One plan with a shop; False when no hanout could be carved (then the house is planned whole)."""
        fresh()
        job = Job(interior, outside, style)
        job.keep_free = stair
        job.zones = job.plain                         # the shop's lines run across the facade (no front_keep)
        rooms, rest = shop.souk(job, full, layout == "dar", small)
        interior.rules, interior.entry = {}, None
        if not rooms:
            PLANS.get(layout, placeholder)(interior, outside, style)
            return False
        interior.rooms = list(rooms)
        interior.full0 = full
        interior.storeys[0] = replace(interior.storeys[0], polygon=rest)
        try:
            PLANS.get(layout, placeholder)(interior, outside, style)
        finally:
            interior.storeys[0] = replace(interior.storeys[0], polygon=full)
            del interior.full0
        shop.doors(_door_job(interior, outside, style))
        R.renumber(interior)
        return True

    def stuck() -> bool:
        return any(w.endswith("a ladder goes up") or "no way up" in w or "ladder rises" in w for w in interior.warnings)

    tries = [(False, None), (True, None)]
    scores = []
    held = None                                       # the try the interior holds now (None: a plan without shop)
    for i in range(3):
        if i == 2:                                    # the stair cell of the house planned without its shop
            fresh()
            PLANS.get(layout, placeholder)(interior, outside, style)
            held = None
            stair = next((st.polygon for st in interior.stairs if st.kind == "newel"), None)
            if stair is None:
                break
            tries.append((True, stair))
        if not run(*tries[i]):
            return
        held = i
        if not stuck():
            return
        scores.append((len(R.check(interior)), i))
    best = min(scores)[1]
    if held != best:
        run(*tries[best])
    interior.warnings.append(SHOP_STAIR)


SHOP_STAIR = "the shop front leaves no room for the house's stair"   # a known weak spot (prompt 47)


def _door_job(interior, outside, style):
    """The numbers the shop's doors need, without a new layout job (its streams stay untouched)."""
    cfg = style.get("interiors", {}).get("openings", {})
    return SimpleNamespace(interior=interior, door=float(cfg.get("door", 0.9)),
                           door_height=float(cfg.get("door_height", 2.1)))


def storeys(outside, thickness: float, court: float | None = None) -> list:
    """One `Storey` per floor: the masses standing at that floor inside the exterior walls (`thickness`,
    mitre joins), a courtyard grown by its own wall (`court`). A neck thinner than two walls leaves
    slivers: the largest part is kept."""
    b, high, fh = outside.b, outside.high, outside.fh
    court = thickness if court is None else court
    ms = masses(b)
    out = []
    for f in range(max(1, int(b.floors))):
        mid = (f + 0.5) * fh
        standing = [m.polygon for m in ms if m.base <= mid < m.top]
        parts = []
        whole = unary_union([m.buffer(CLOSE, join_style="mitre") for m in standing]).buffer(-CLOSE, join_style="mitre")
        for part in polygons(whole) if standing else []:     # steps sharing an edge are one floor (47.1)
            inner = Polygon(part.exterior).buffer(-thickness, join_style="mitre")
            holes = [Polygon(h).buffer(court, join_style="mitre") for h in part.interiors]
            parts += polygons(inner.difference(unary_union(holes)) if holes else inner)
        if parts:
            poly = set_precision(orient(max(parts, key=lambda p: p.area), 1.0), GRID)
            out.append(Storey(f, high + f * fh, fh, orient(poly, 1.0)))
    return out


def reveals(interior: Interior, deep: float, least: float) -> None:
    """Where a facade opening stands so near a corner that the next wall's inner face crosses the floor
    behind it, the storey takes a reveal in that wall (`deep` m of floor behind the opening across its
    width), as long as the wall keeps `least` m to the outside (47.1/48.1)."""
    from .plancheck import FACADE, GAP, depths, frame_of, rect
    ext = interior.walls["exterior"]
    for i, st in enumerate(interior.storeys):
        outline = Polygon(st.polygon.exterior).buffer(ext, join_style="mitre").buffer(-least, join_style="mitre")
        notches = []
        mine = [o for o in interior.openings if o.floor == st.floor and o.kind in FACADE]
        held = unary_union([rect(*frame_of(o), -o.width / 2, o.width / 2, depths(interior, o)[0], 0.0) for o in mine])
        for o in mine:                                    # (a reveal never cuts into another opening's wall)
            c, front, along = frame_of(o)
            d0 = depths(interior, o)[0]
            near = rect(c, front, along, -o.width / 2, o.width / 2, d0 - deep, d0 - GAP)
            if near.difference(st.polygon).area > 1e-4:
                notch = rect(c, front, along, -o.width / 2 - GAP, o.width / 2 + GAP, d0 - deep, d0)   # flush with
                notches.append(notch.intersection(outline).difference(held))                  # the wall's face
        if notches:
            poly = unary_union([st.polygon] + notches)
            if poly.geom_type == "Polygon":
                interior.storeys[i] = replace(st, polygon=orient(set_precision(poly, GRID), 1.0))


def placeholder(interior: Interior, outside, style: dict) -> None:
    """One room per storey (type `room`, unit `home`) holding the facade openings of its floor."""
    for st in interior.storeys:
        lit = any(o.lit for o in interior.openings if o.floor == st.floor and o.kind in LIGHTS)
        interior.rooms.append(Room(len(interior.rooms), st.floor, "room", st.polygon, st.z, st.height, lit=lit))
    room_of = {r.floor: r.id for r in interior.rooms}
    for o in interior.openings:
        o.rooms = (room_of.get(o.floor, -1), -1)


def _plans() -> dict:
    from . import compact, dar, flats, koubba, villa
    return {"dar": dar.plan, "compact": compact.plan, "small": compact.small, "villa": villa.villa,
            "maison": villa.maison, "koubba": koubba.plan, "colonial": flats.colonial, "slab": flats.slab}


PLANS: dict = _plans()   # layout -> function(interior, outside, style)
