"""Who lives here: a household behind every house door, and a trade for every souk.

This is story data first (plan.json, gazetteer) and it also drives the look: the door color and
richness of a house, and the goods in front of the shops, come from these records.
"""
from __future__ import annotations

from dataclasses import dataclass

from ..names import NameMaker, article
from ..rng import weighted

HOUSING = {"house", "domed", "apartments", "villa"}


@dataclass
class Household:
    building: int   # index in plan.buildings
    family: str
    trade: str
    wealth: float   # 0 poor .. 1 rich
    door: str       # door piece color, e.g. door_blue
    members: int


@dataclass
class Souk:
    street: int     # index in plan.streets
    name: str       # e.g. "Souk el Attarine"
    trade: str
    ground: list    # goods pieces set out in front of the shops
    wall: list      # goods pieces hung on the wall
    shop: str = ""  # what fills the shelves inside (a key of SHOP_GOODS in mesh/props.py)


def family_name(namer: NameMaker, rng, patterns) -> str:
    core = namer.core()
    pattern = weighted(rng, patterns)
    stem = core[:-1] if core[-1] in "aeiou" else core
    nisba = stem if stem.endswith("i") else stem + "i"   # Zoghlami, not Zoghlamii
    return pattern.format(n=core, i=nisba, l=core.lower())


def households(ctx, buildings, districts) -> list:
    life = ctx.style.get("life", {})
    if not life:
        return []
    rng = ctx.rng("households")
    namer = NameMaker(ctx.style, ctx.rng("family-names"))
    lo, hi = life.get("members", [2, 8])
    out = []
    for k, b in enumerate(buildings):
        if b.kind not in HOUSING:
            continue
        kind = districts[b.district].kind
        a, bb = life.get("wealth", {}).get(kind, [2.0, 3.0])
        wealth = float(rng.beta(a, bb))
        trades = life.get("trades", {}).get(kind) or life.get("trades", {}).get("residential", [["merchant", 1]])
        door = weighted(rng, life["door_colors"])
        out.append(Household(k, family_name(namer, rng, life["family_patterns"]), weighted(rng, trades),
                             round(wealth, 2), door, int(rng.integers(lo, hi + 1))))
    return out


def souks(ctx, streets) -> list:
    """Give every souk street a trade, the way real medinas group their crafts."""
    trades = ctx.style.get("souk", [])
    if not trades:
        return []
    rng = ctx.rng("souk-trades")
    order = list(rng.permutation(len(trades)))
    repeat = ["", " el Djedid", " el Kebir", " es Sghir", " el Bahri", " el Gharbi", " ech Chergui"]
    seen: dict = {}
    out = []
    for k, st in enumerate(streets):
        if st.kind != "souk" or st.line.length < 25.0:
            continue
        if not order:
            order = list(rng.permutation(len(trades)))
        t = trades[int(order.pop())]
        word = t["word"]
        n = seen[word] = seen.get(word, -1) + 1
        name = f"Souk {article(word)} {word}" + (repeat[n] if n < len(repeat) else f" {n + 1}")
        out.append(Souk(k, name, t["trade"], list(t.get("ground", [])), list(t.get("wall", [])), t.get("shop", "")))
    return out
