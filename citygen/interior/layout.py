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
    court = float(walls_cfg.get("court", 0.3))
    if layout not in TRADITIONAL and b.footprint.interiors:   # a colonial block's or maison's courts (47.2):
        court = exterior_wall(style, outside.district)         # walls as thick as the street's, with facade windows
    walls = {"exterior": exterior_wall(style, outside.district), "court": court,
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
    before = _held(interior)
    _stages(interior, outside, style, layout, before)
    carved = None
    if layout in HOUSES and any(f.endswith(WAY) for f in check(interior)):
        start = _held(interior)
        carve(interior, style, whole=True)            # a cut that makes it pass spares the redraws (time) ...
        if not check(interior) and dim(interior, style):
            carved = (_held(interior), dim(interior, style))   # ... unless they may find fewer dark rooms
            _hold(interior, start)
    if layout in TRADITIONAL + HOUSES and any(not any(w in f for w in DEAF) for f in check(interior)) and not hopeless(
            interior, layout):
        again = redraw(interior, outside, style, layout, before)
    else:
        again = True
    if layout in HOUSES and again and any(f.endswith(WAY) for f in check(interior)):
        carve(interior, style)                        # (a plan the first carve saw: no second)
    if carved is not None and (check(interior) or dim(interior, style) > carved[1]):
        _hold(interior, carved[0])
    interior.__dict__.pop("checked", None)
    return interior


def carve(interior: Interior, style: dict, whole: bool = False) -> None:
    """A villa or maison whose couloir or day rooms its entry still reaches only through a chambre, cuisine or
    sdb gets a couloir cut through that room (`carve.passages`, `carve.cut`, then the way's doors), the
    smallest strip first (then those past a jog of the wall, `carve.OVER`), `[interiors.villa] carve_tries`
    cuts tried per round; a cut kept when `rooms.check` finds no new fault of another kind, fewer faults (or
    as many, with fewer rooms off the way) and the home no more dark rooms, up to `carves` cuts; `whole`: all
    kept only when the plan then passes (47.1 + 48.1 round 11)."""
    from .carve import OVER, cut, passages
    from .plancheck import settle, way_doors
    cfg = style.get("interiors", {}).get("villa", {})
    wide, scrap = float(cfg.get("couloir", 1.15)), float(cfg.get("carve_scrap", 0.0))
    bad, dark, first = check(interior), dim(interior, style), _held(interior)
    best = _score(interior, bad)
    for _ in range(int(cfg.get("carves", 0))):
        if not any(f.endswith(WAY) for f in bad):
            break
        start, won, tries = _held(interior), False, int(cfg.get("carve_tries", 0))
        for strip, host, _, into in passages(interior, wide) + passages(interior, wide, over=OVER):
            if tries > 0 and cut(interior, strip, host, into, scrap):
                tries -= 1
                if way_doors(interior):
                    settle(interior)
                got = check(interior)
                if (sum(not f.endswith(WAY) for f in got) <= sum(not f.endswith(WAY) for f in bad)
                        and _score(interior, got) < best and dim(interior, style) <= dark):
                    bad, best, won = got, _score(interior, got), True
                    break
            _hold(interior, start)
        if not won:
            break
    if whole and bad:
        _hold(interior, first)


def redraw(interior: Interior, outside, style: dict, layout: str, before: dict) -> bool:
    """An old-town house, villa or maison the plan check still faults is planned again with fresh draws
    (`Job.rng`, the shop's stream and `spine.rng` take the purpose path + ("again", n)), up to `[interiors.dar]`
    or `[interiors.villa] redraws` times; the plan with the fewest faults and no more dark rooms kept (round 8).
    True when a redrawn plan was kept."""
    best, faults, dark, kept = _held(interior), len(check(interior)), dim(interior, style), False
    times = style.get("interiors", {}).get("villa" if layout in HOUSES else "dar", {}).get("redraws", 0)
    times = int(times.get(layout, 0) if isinstance(times, dict) else times)
    for n in range(1, times + 1):
        _hold(interior, before)
        interior.redraw = n
        interior.bays_early = layout in HOUSES        # a house's redraws trade window bays in the search
        try:
            _stages(interior, outside, style, layout, before)
        finally:
            del interior.redraw, interior.bays_early
        got = len(check(interior))
        if got < faults and dim(interior, style) <= dark:   # never more dark rooms (blind or strips) for a pass
            best, faults, dark, kept = _held(interior), got, dim(interior, style), True
        if not faults:
            break
    _hold(interior, best)
    return kept


def dim(interior: Interior, style: dict) -> int:
    """The home's dark rooms: chambres, salons, salles a manger and cuisines with no facade window, balcony
    or court opening, or with over `[interiors.flats] strip` m2 in parts narrower than its width (round 8:
    a second plan is kept only when it has no more of them)."""
    from .spine import strip
    wide, most = (float(v) for v in style.get("interiors", {}).get("flats", {}).get("strip", (1.6, 3.0)))
    lit = {r for o in interior.openings for r in (o.rooms or ())
           if (o.kind in LIGHTS and o.wall is not None) or o.kind in ("court_window", "court_door")}
    return sum(1 for r in interior.rooms if r.type in DIM and (r.id not in lit or strip(r.polygon, wide) > most))


DIM = ("chambre", "salon", "salle_a_manger", "cuisine")


def _stages(interior: Interior, outside, style: dict, layout: str, before: dict) -> None:
    """The plan by layout and its retries and repairs (rounds 5-8)."""
    interior.way_used = False
    _plan(interior, outside, style, layout)
    if interior.__dict__.pop("way_moved", False):
        way_moved(interior, outside, style, layout, before)
    if layout in TRADITIONAL and interior.floors > 1 and any(w.endswith(ROOF_LADDER) for w in interior.warnings):
        newel_up(interior, outside, style, layout, before)
    if layout in TRADITIONAL:
        free_way(interior, outside, style, layout, before)
    if layout in TRADITIONAL + HOUSES and short_steps(interior, style):   # the entry room too short for its steps
        best, faults = _held(interior), len(plain(interior))
        for more in KEEP_MORE:                        # the plan keeps the steps' strip free of partitions
            _hold(interior, before)
            interior.keep_steps = more
            try:
                _plan(interior, outside, style, layout)
            finally:
                del interior.keep_steps
            got = len(plain(interior))
            if got < faults:                          # kept only when the plan check finds less
                best, faults = _held(interior), got
            if not faults:
                break
        _hold(interior, best)
    if layout in HOUSES and not interior.__dict__.get("redraw") and any(
            not any(w in f for w in SEARCH_DEAF) for f in check(interior)) and not hopeless(interior, layout):
        early_bays(interior, outside, style, layout, before)
    if layout in HOUSES and interior.floors == 1 and not interior.__dict__.get("redraw") and any(
            f.endswith(SHORT) for f in check(interior)):
        again(interior, outside, style, layout, "tiny", before, plain)
    if layout in TRADITIONAL:
        from .program import swap_way
        swap_way(interior, check)                     # services off the way in (round 6)
    if layout in TRADITIONAL + HOUSES and any("entry steps" in f for f in plan_steps(interior)):
        sunk(interior, style)                         # villas and maisons too (47.1 round 9)
    if layout == "dar":
        bent(interior)
    interior.__dict__.pop("way_used", None)
    interior.__dict__.pop("newel_up", None)


ROOF_LADDER = "a ladder rises into the stair room"


def newel_up(interior: Interior, outside, style: dict, layout: str, before: dict) -> None:
    """A house whose newel did not fit under the roof's stair room is planned again with a second newel from
    the top floor to the roof under it (`dar.roof_newel`, 47.1 round 9); kept when the ladder is gone and the
    plan check finds no more faults and the home no more dark rooms. The flag then stays for later retries."""
    first, faults, dark = _held(interior), len(check(interior)), dim(interior, style)
    _hold(interior, before)
    interior.newel_up = True
    _plan(interior, outside, style, layout)
    if (not any(w.endswith(ROOF_LADDER) for w in interior.warnings) and len(check(interior)) <= faults
            and dim(interior, style) <= dark):
        return
    del interior.newel_up
    _hold(interior, first)


def bent(interior: Interior) -> None:
    """The bent entry where the court still shows from the street door (`plancheck.bend`), kept when
    `rooms.check` finds less (round 6)."""
    from .plancheck import bend
    from .rooms import sees_court
    if not sees_court(interior):
        return
    first, faults = _held(interior), len(check(interior))
    bend(interior)
    if len(check(interior)) >= faults:
        _hold(interior, first)


def free_way(interior: Interior, outside, style: dict, layout: str, before: dict) -> None:
    """Services kept off the only way in (`program.way_cells`) and the skifa's own way to the court
    (`dar.skifa_way`) can cost a plan other faults: when they acted and faults other than the entry steps'
    are left, the plan without them is tried too, each after `program.swap_way`; the one with fewer faults
    stays (round 6)."""
    from .program import swap_way
    swap_way(interior, check)
    if not interior.__dict__.pop("way_used", False):
        return
    bad = check(interior)
    faults = len(bad)
    if all("entry steps" in f for f in bad):          # no fault, or the steps' (their retries follow)
        return
    first = _held(interior)
    _hold(interior, before)
    interior.way_free = True
    try:
        _plan(interior, outside, style, layout)
    finally:
        del interior.way_free
    swap_way(interior, check)
    if len(check(interior)) >= faults:
        _hold(interior, first)


def way_moved(interior: Interior, outside, style: dict, layout: str, before: dict) -> None:
    """An upper floor whose first faultless variant missed the landing took a later one that reaches it
    (`spine.search`, round 10): kept only when the plan check then finds fewer faults and the home has no
    more dark rooms than the plan without that choice."""
    moved, faults = _held(interior), len(check(interior))
    _hold(interior, before)
    interior.way_plain = True
    try:
        _plan(interior, outside, style, layout)
    finally:
        del interior.way_plain
    interior.__dict__.pop("way_moved", None)
    if faults < len(check(interior)) and dim(interior, style) >= dim_of(moved, interior, style):
        _hold(interior, moved)


def dim_of(state: dict, interior: Interior, style: dict) -> int:
    """`dim` of a held plan (the interior keeps its own)."""
    now = _held(interior)
    _hold(interior, state)
    n = dim(interior, style)
    _hold(interior, now)
    return n


def early_bays(interior: Interior, outside, style: dict, layout: str, before: dict) -> None:
    """A villa or maison the plan check still faults is planned again with the window bays traded inside
    the spine's variant search (`spine.bays`, as flats do), the plan with fewer faults kept (round 8)."""
    again(interior, outside, style, layout, "bays_early", before)


def again(interior: Interior, outside, style: dict, layout: str, flag: str, before: dict, count=None) -> None:
    """The house planned again from `before` with `flag` set; the plan with fewer `rooms.check` faults (or
    `count`'s) kept (round 8)."""
    count = count or check
    first, faults, dark = _held(interior), len(count(interior)), dim(interior, style)
    _hold(interior, before)
    setattr(interior, flag, True)
    try:
        _plan(interior, outside, style, layout)
    finally:
        delattr(interior, flag)
    if len(count(interior)) >= faults or dim(interior, style) > dark:
        _hold(interior, first)


def plan_steps(interior: Interior) -> list:
    from .plancheck import _steps
    return _steps(interior, interior.rules.get("plan", {}))


def sunk(interior: Interior, style: dict) -> None:
    """The sunken entry where the steps still fault (`sunken.sink`), kept when `rooms.check` finds less."""
    from .sunken import sink
    first, faults = _held(interior), len(plain(interior))
    sink(interior, style)
    if len(plain(interior)) >= faults:
        _hold(interior, first)


SHORT = ("has no chambre", "has no salon")   # a tiny one-floor house tries again with its wc in the sdb
DEAF = ("storey crosses", "no U stair", "entry steps", "has no chambre", "has no salon")   # faults no redraw
# cured (tile spikes, no room for the U stair, a tiny house's program: survey, round 8)
HOPELESS = ("storey crosses", "no U stair", "villa has no", "maison has no")   # a villa or maison faulted so is never
# planned again (47.1 + 48.1 round 11: the time; no second plan cured one, survey; "floor 0 has no" it may)


def hopeless(interior: Interior, layout: str) -> bool:
    """True for a villa or maison whose plan has a fault no second plan cures (`HOPELESS`; round 11)."""
    return layout in HOUSES and any(w in f for f in check(interior) for w in HOPELESS)


SEARCH_DEAF = ("has no", "no U stair", "storey crosses", "entry steps")   # faults a second search never cures
HOUSES = ("villa", "maison")   # modern houses retried for their steps too (47.1 round 7)
KEEP_MORE = (0.0, 0.3)   # m beyond the steps' least depth kept free on a second and third plan (47.1)


def _plan(interior: Interior, outside, style: dict, layout: str) -> None:
    """Rooms by layout (a shop front first), then hair strips trimmed and inner openings settled."""
    if layout in SOUK and any(o.kind == "shop" and o.floor == 0 for o in interior.openings):
        with_shop(interior, outside, style, layout)
    else:
        PLANS.get(layout, placeholder)(interior, outside, style)
    from .plancheck import MODERN, settle, trim
    trim(interior)
    settle(interior)
    if layout in MODERN:
        way_home(interior, style)


def way_home(interior: Interior, style: dict) -> None:
    """A villa, maison or flat whose day rooms its entry reaches only through a chambre, bath or cuisine gets
    doors on its own way (`plancheck.way_doors`), then a house trades a day room's type with a chambre on
    that way (`plancheck.way_swaps`, `[interiors.villa] way_swaps` tries, two rounds, the best trade of each
    kept); each kept when `rooms.check` then finds no new fault of another kind and fewer faults (or as many,
    with fewer rooms off the way) and the home no more dark rooms. A block of flats judges its doors by the
    wall checks of the floors they stand on (`flat_doors`: a whole block's check takes up to 0.8 s; round
    10)."""
    from .plancheck import settle, way_doors, way_swaps
    from .plancheck import way_home as faulted
    if not faulted(interior):
        return
    if interior.flats:
        flat_doors(interior)
        return
    bad, dark = check(interior), dim(interior, style)
    best = _score(interior, bad)

    def judge():
        got = check(interior)
        ok = (sum(not f.endswith(WAY) for f in got) <= sum(not f.endswith(WAY) for f in bad)
              and _score(interior, got) < best and dim(interior, style) <= dark)
        return got if ok else None

    first = _held(interior)
    if way_doors(interior):
        settle(interior)
        got = judge()
        if got is None:
            _hold(interior, first)
        else:
            bad, best = got, _score(interior, got)
    tries = int(style.get("interiors", {}).get("villa", {}).get("way_swaps", 0))
    for _ in range(2):                                # two rounds: the best trade of each kept
        start, won = _held(interior), None
        for a, b in (way_swaps(interior) if any(f.endswith(WAY) for f in bad) else [])[:tries]:
            ra, rb = (next(r for r in interior.rooms if r.id == i) for i in (a, b))
            ra.type, rb.type = rb.type, ra.type
            if way_doors(interior):
                settle(interior)
            got = judge()
            if got is not None:
                bad, best, won = got, _score(interior, got), _held(interior)
            _hold(interior, start)
        if won is None:
            return
        _hold(interior, won)


def _score(interior: Interior, bad: list) -> tuple:
    from .plancheck import astray
    return len(bad), astray(interior)


def flat_doors(interior: Interior) -> None:
    """`way_home` for a block of flats: the doors kept when the wall checks of their floors (`plancheck`) find
    no more faults and fewer rooms lie off the way."""
    from .plancheck import _walls, astray, settle, way_doors
    first, off = _held(interior), astray(interior)
    floors = way_doors(interior)
    if not floors:
        return
    settle(interior)
    cfg = interior.rules.get("plan", {})
    walls = lambda: sum(len(_walls(interior, f, cfg)) for f in sorted(floors))   # noqa: E731
    got, now, moved = walls(), astray(interior), _held(interior)
    _hold(interior, first)
    if got <= walls() and now < off:
        _hold(interior, moved)


WAY = ("only through a chambre, bath or cuisine", "every bath room only through a chambre")


HELD = ("layout", "storeys", "rooms", "openings", "stairs", "flats", "features", "warnings", "rules", "focus",
        "entry", "piers")


def _held(interior: Interior) -> dict:
    import copy
    return {k: copy.deepcopy(getattr(interior, k)) for k in HELD}


def _hold(interior: Interior, state: dict) -> None:
    import copy
    for k, v in state.items():
        setattr(interior, k, copy.deepcopy(v))


def check(interior: Interior) -> list:
    """`rooms.check`; a villa's or maison's remembered per plan state while it is planned (its retries ask the
    same plan again and again; 47.1 + 48.1 round 11, time)."""
    import hashlib
    import pickle
    from .rooms import check as rooms_check
    if interior.layout not in HOUSES:
        return rooms_check(interior)
    state = [getattr(interior, k) for k in HELD] + [getattr(interior, "full0", None)]
    key = hashlib.md5(pickle.dumps(state, protocol=5)).digest()
    memo = interior.__dict__.setdefault("checked", {})
    if key not in memo:
        memo[key] = rooms_check(interior)
    return list(memo[key])


def plain(interior: Interior) -> list:
    """`check` without the way-home faults: the steps' and tiny houses' retries choose as before them (47.1 +
    48.1 round 10; only the redraws and the way's own repairs count them)."""
    return [f for f in check(interior) if not f.endswith(WAY)]


def short_steps(interior: Interior, style: dict) -> bool:
    """True when entry steps fault the plan check (treads under `tread_min`, clipped) although the storey
    behind their door is deep enough for them (`stairs.steps_depth`)."""
    import math

    import numpy as np
    from shapely.geometry import LineString

    from .plancheck import _steps
    from .stairs import steps_depth
    if not any("entry steps" in f and "stair" not in f for f in _steps(interior, interior.rules.get("plan", {}))):
        return False
    cfg = style.get("interiors", {}).get("stairs", {})
    st0, ext = interior.storeys[0].polygon.buffer(1e-6), interior.walls["exterior"]
    for s in interior.stairs:
        if s.kind != "steps":
            continue
        x, y, yaw = s.door
        inward = -np.array([math.cos(yaw), math.sin(yaw)])     # the steps' yaw points out of the door
        face = np.array([x, y]) + inward * ext
        ray = LineString([face, face + inward * 50.0]).intersection(st0)
        deep = max((g.length for g in getattr(ray, "geoms", [ray]) if g.geom_type == "LineString"), default=0.0)
        if deep >= steps_depth(s.risers * s.riser, cfg):
            return True
    return False


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
