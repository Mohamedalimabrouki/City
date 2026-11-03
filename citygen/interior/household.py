"""Who lives here (prompt 54, SPEC 6d "Who lives here", "Room functions"): a unit's family and its tags, and
the function each room of the unit is given.

The households of `city/life.py` hold members, wealth and trade only: children and elders are derived per
unit on their own stream (`"furnish", "family", unit`), so no other choice of the city or the plan moves.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from shapely.geometry import Point

from ..rng import stream

TRAD = ("dar", "compact", "small", "koubba")
FIXED = {"skifa": "entry", "wast_ed_dar": "court", "bortal": "gallery", "matbakh": "kitchen", "cuisine": "kitchen",
         "bit_el_ma": "washroom", "sdb": "bath", "wc": "wc", "bit_el_mouna": "store", "makhzen": "store",
         "hall": "hall", "droj": "passage", "palier": "passage", "couloir": "passage", "well": "passage",
         "stah": "terrace", "salon": "salon", "salle_a_manger": "dining", "hanout": "shop", "qahwa": "cafe",
         "koubba": "reception", "menzah": "passage"}
FLEX = ("bit", "maqsura", "ghorfa", "chambre")
LIT = ("window", "court_window", "balcony", "court_door")   # openings that bring daylight into a room
WORK_SETS = ("weaver", "tailor", "chechia maker", "potter")


@dataclass
class Profile:
    unit: str
    members: int
    adults: int
    elders: int
    children: list            # "small" | "school" | "teen", in draw order
    trade: str
    wealth: float
    tags: set = field(default_factory=set)

    def to_json(self) -> dict:
        return {"tags": sorted(self.tags), "members": self.members, "adults": self.adults, "elders": self.elders,
                "children": list(self.children), "trade": self.trade, "wealth": self.wealth}


def record(interior, unit: str, outside=None) -> dict | None:
    """The household record of a unit (SPEC 6d): home -> the plan's; flat <n> -> its flat's; shop, cafe none."""
    if unit == "home":
        return interior.household
    if unit.startswith("flat "):
        n = int(unit.split()[1])
        flat = next((f for f in interior.flats if f.id == n), None)
        return None if flat is None else flat.household
    return None


def shop_trade(interior, outside) -> str:
    """The hanout's trade: the souk of the street nearest its shop front (within 8 m), else the grocer."""
    plan = getattr(outside, "plan", None)
    front = next((o for o in interior.openings if o.kind == "shop"), None)
    if plan is None or front is None:
        return "grocer"
    p = Point(front.x, front.y)
    best = None
    for s in getattr(plan, "souks", ()) or ():
        d = plan.streets[s.street].line.distance(p)
        if d < 8.0 and (best is None or d < best[0]):
            best = (d, s.shop or "grocer")
    return best[1] if best else "grocer"


def profile(interior, unit: str, style: dict, outside=None) -> Profile:
    """The family of one unit and the tags the recipes test."""
    cfg = style.get("interiors", {}).get("furnish", {})
    trad = interior.layout in TRAD
    if unit in ("shop", "cafe", "common"):
        trade = "cafe owner" if unit == "cafe" else (shop_trade(interior, outside) if unit == "shop" else "")
        tags = {"trad" if trad else "modern", interior.layout, interior.district, cfg.get("period", "today"), unit}
        return Profile(unit, 0, 0, 0, [], trade, 0.5, tags)
    rec = record(interior, unit) or {}
    members = max(1, int(rec.get("members", 4)))
    wealth = float(rec.get("wealth", 0.5))
    trade = str(rec.get("trade", "") or "")
    rng = stream(interior.seed, "interior", interior.city_id, interior.building, "furnish", "family", unit)
    u1, u2 = rng.random(), rng.random()
    adults = 1 if members == 1 else 2
    share = float(cfg.get("elder_share", [0.45, 0.30])[0 if trad else 1])
    elders = 0
    if members >= 4 and u1 < share:
        elders = 2 if members >= 6 and u2 < float(cfg.get("elder_two", 0.25)) else 1
    children = []
    for _ in range(max(0, members - adults - elders)):
        u = rng.random()
        children.append("small" if u < 0.15 else "school" if u < 0.85 else "teen")
    bands = cfg.get("bands", {"poor": 0.35, "rich": 0.65})
    band = "poor" if wealth < float(bands["poor"]) else "rich" if wealth >= float(bands["rich"]) else "middle"
    tags = {"trad" if trad else "modern", interior.layout, interior.district, band, cfg.get("period", "today"), "home"}
    if adults == 2:
        tags.add("couple")
    if children:
        tags.add("children")
    if "small" in children:
        tags.add("small")
    if "school" in children or "teen" in children:
        tags.add("school")
    if "teen" in children:
        tags.add("teen")
    if elders:
        tags.add("elders")
    if members >= 6:
        tags.add("big")
    if trade:
        tags.add("trade:" + trade.replace(" ", "_"))
        for group, trades in cfg.get("trade_tags", {}).items():
            if trade in trades:
                tags.add(group)
    return Profile(unit, members, adults, elders, children, trade, wealth, tags)


def units(interior) -> list:
    """The units of the interior that hold rooms, in a fixed order (home, flats by number, shop, cafe, common)."""
    seen = sorted({r.unit for r in interior.rooms},
                  key=lambda u: (0, 0) if u == "home" else (1, int(u.split()[1])) if u.startswith("flat ")
                  else (2, ("shop", "cafe", "common").index(u) if u in ("shop", "cafe", "common") else 9))
    return seen


def lit_rooms(interior) -> set:
    """Ids of the rooms with daylight (a window, a balcony or a court door)."""
    return {i for o in interior.openings if o.kind in LIT for i in o.rooms}


def functions(interior, unit: str, prof: Profile) -> dict:
    """{room id: function} for the rooms of one unit (SPEC 6d "Room functions")."""
    rooms = [r for r in interior.rooms if r.unit == unit]
    out = {}
    for r in rooms:
        if r.type in FIXED:
            out[r.id] = FIXED[r.type]
    free = [r for r in rooms if r.id not in out and r.type in FLEX]
    for r in rooms:
        if r.id not in out and r.type not in FLEX:
            out[r.id] = "store" if r.polygon.area < 6.0 else "guest"
    if unit in ("shop", "cafe", "common") or not free:
        return dict(sorted(out.items()))
    trad = "trad" in prof.tags
    lit = lit_rooms(interior)
    area = lambda r: r.polygon.area

    def take(r, fn):
        out[r.id] = fn
        free.remove(r)

    def best(cands, key=area, small=False):
        cands = [r for r in cands if r in free]
        if not cands:
            return None
        return sorted(cands, key=lambda r: ((key(r) if small else -key(r)), r.id))[0]

    has_koubba = any(v == "reception" for v in out.values())
    if trad and not has_koubba:
        r = (best([r for r in free if r.type == "bit" and r.alcove is not None])
             or best([r for r in free if r.type == "bit" and r.floor == 0 and r.id in lit])
             or best([r for r in free if r.type in ("bit", "ghorfa")]))
        if r is not None:
            take(r, "reception")
    if prof.adults >= 1:
        if trad:
            r = (best([r for r in free if r.type == "maqsura"]) or best([r for r in free if r.type == "ghorfa"])
                 or best([r for r in free if r.type == "bit"]))
        else:
            r = best([r for r in free if r.type == "chambre"]) or best(free)
        if r is not None:
            take(r, "sleep_couple")
    if prof.elders and free:
        if trad:
            r = best([r for r in free if r.floor == 0]) or best(free)
        else:
            r = best([r for r in free if r.polygon.area >= 9.0], small=True) or best(free)
        if r is not None:
            take(r, "sleep_elder")
    if prof.children:
        n = math.ceil(len(prof.children) / (4 if "poor" in prof.tags else 3))
        for _ in range(n):
            r = best(free)
            if r is None:
                break
            take(r, "sleep_children")
    if trad and "today" in prof.tags and free:
        take(best(free), "family")
    if prof.trade in WORK_SETS and free:
        r = best([r for r in free if r.id in lit])
        if r is not None:
            take(r, "work")
    if not trad and ("reader" in prof.tags or "teen" in prof.tags) and free:
        take(best(free), "study")
    for r in sorted(free, key=lambda r: r.id):
        out[r.id] = "store" if r.polygon.area < 6.0 else "guest"
    return dict(sorted(out.items()))
