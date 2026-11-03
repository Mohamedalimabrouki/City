"""The lights, plants and clutter of the home kit (prompt 55, SPEC 6d "Catalog: light, wall textiles,
plants and clutter").

Same frame and rules as `kit_old`: x along the wall, front +y, z up, meters. A `ceiling` piece hangs from
z 0 down to z -H (its spec's z0 is -H). Every piece of category `light` gets from `home_kit` its `_on`
twin (`lamp_glass` drawn as `lamp_glow`, which the viewer lights at night). Round things are lathed; the
lathe's ring has a vertex at angle 0, so its widths hold the table's sizes. The rest of the same table (wall
decor and textiles, the curtain, more plants and clutter) comes next (docs/wip/furn-55.md).
"""
from __future__ import annotations

import math

from ..mesh.builder import MeshBuilder
from ..rng import stream
from .kit_new import _front
from .kit_old import _box, _lathed

# name: (category, anchor, (W, D, H), tris, extra), as kit_old.TABLE
TABLE = {
    "fanous": ("light", "ceiling", (0.30, 0.30, 1.15), 200, {"z0": -1.15}),
    "lantern_table": ("light", "on", (0.20, 0.20, 0.40), 120, {}),
    "ceiling_lamp": ("light", "ceiling", (0.40, 0.40, 0.15), 60, {"z0": -0.15}),
    "chandelier": ("light", "ceiling", (0.80, 0.80, 0.70), 400, {"z0": -0.70}),
    "neon": ("light", "wall", (1.20, 0.08, 0.08), 24, {"z0": 2.20}),
    "bulb_bare": ("light", "ceiling", (0.08, 0.08, 0.40), 30, {"z0": -0.40}),
    "lamp_bedside": ("light", "on", (0.25, 0.25, 0.40), 60, {}),
    "pot_geranium": ("plant", "floor", (0.35, 0.35, 0.50), 120, {}),
    "pot_basil": ("plant", "floor", (0.25, 0.25, 0.30), 80, {}),
    "plates_stack": ("small", "on", (0.26, 0.26, 0.12), 40, {"top": 0.12}),
    "fruit_bowl": ("small", "on", (0.30, 0.30, 0.15), 70, {}),
    "oil_bidon": ("small", "floor", (0.20, 0.15, 0.32), 40, {}),
    "pot_jasmine": ("plant", "floor", (0.45, 0.45, 1.20), 220, {}),
    "vase_flowers": ("small", "on", (0.15, 0.15, 0.40), 80, {}),
    "photo_frame": ("decor", "wall", (0.30, 0.02, 0.40), 12, {"z0": 1.50}),
    "khomsa": ("decor", "wall", (0.16, 0.02, 0.20), 24, {"z0": 1.80}),
}
VARIANTS: dict = {}
SIZES = {b: row[2] for b, row in TABLE.items()}   # `[interiors.furnish.sizes]` overrides


def fanous(s, v, rng):
    """The brass lantern of traditional rooms on its chain: a ceiling rose, the chain, then the lantern
    (a finial, a brass bowl, the glass body, a domed cap) in its lowest 0.55 m."""
    w, d, h = s
    r, top = w / 2, -h + 0.55
    mb = MeshBuilder()
    _lathed(mb, [(0.0, -0.02), (0.05, -0.02), (0.05, 0.0)], "brass", 8)
    _box(mb, -0.006, 0.006, -0.006, 0.006, top, -0.02, "brass", "tb")
    prof = [(0.0, -h), (0.03, -h + 0.06), (r - 0.02, -h + 0.12), (r, -h + 0.17), (r, top - 0.20),
            (r - 0.02, top - 0.16), (0.05, top - 0.04), (0.0, top)]
    _lathed(mb, prof, ["brass", "brass", "brass", "lamp_glass", "brass", "brass", "brass"], 8)
    return mb


def lantern_table(s, v, rng):
    """A small brass lantern standing on a table or the floor: a foot, the glass, a pointed cap, its ring."""
    w, d, h = s
    r = w / 2
    mb = MeshBuilder()
    prof = [(r, 0.0), (r, 0.03), (r - 0.03, 0.05), (r - 0.03, h - 0.13), (r - 0.01, h - 0.11),
            (0.03, h - 0.04), (0.0, h - 0.03)]
    _lathed(mb, prof, ["brass", "brass", "lamp_glass", "brass", "brass", "brass"], 8)
    _box(mb, -0.01, 0.01, -0.003, 0.003, h - 0.03, h, "brass")
    return mb


def ceiling_lamp(s, v, rng):
    """The flush glass dome of modern rooms on its chrome rim."""
    w, d, h = s
    r = w / 2
    mb = MeshBuilder()
    prof = [(0.0, -h), (r * 0.6, -h + 0.02), (r - 0.01, -0.05), (r, 0.0)]
    _lathed(mb, prof, ["lamp_glass", "lamp_glass", "chrome"], 8)
    return mb


def chandelier(s, v, rng):
    """The brass chandelier of the salon: a rose and a stem, a turned body, a ring on two crossed spokes and
    eight glass tulips on the ring."""
    w, d, h = s
    cup, ring_z = 0.06, -h + 0.25
    reach = w / 2 - cup + 0.002
    mb = MeshBuilder()
    _lathed(mb, [(0.0, -0.02), (0.06, -0.02), (0.06, 0.0)], "brass", 8)
    body = [(0.0, -h), (0.04, -h + 0.04), (0.08, -h + 0.15), (0.05, ring_z + 0.05), (0.02, ring_z + 0.10),
            (0.015, -0.02)]
    _lathed(mb, body, "brass", 8)
    ring = reach - 0.02
    _lathed(mb, [(ring + 0.01, ring_z - 0.02), (ring + 0.01, ring_z + 0.01)], "brass", 12)
    _lathed(mb, [(ring - 0.01, ring_z + 0.01), (ring - 0.01, ring_z - 0.02)], "brass", 12)
    _box(mb, -ring, ring, -0.008, 0.008, ring_z - 0.015, ring_z, "brass", "")
    _box(mb, -0.008, 0.008, -ring, ring, ring_z - 0.015, ring_z, "brass", "")
    for k in range(8):
        a = k * math.pi / 4
        at = (reach * math.cos(a), reach * math.sin(a), ring_z)
        _lathed(mb, [(0.0, 0.0), (0.02, 0.01), (cup, 0.11)], "lamp_glass", 6, at=at)
    return mb


def neon(s, v, rng):
    """The kitchen's tube light on the wall: a white plastic batten and its glass tube."""
    w, d, h = s
    z0 = TABLE["neon"][4]["z0"]
    mb = MeshBuilder()
    _box(mb, -w / 2, w / 2, 0.0, d / 2, z0, z0 + h, "plastic_white", "k")
    _box(mb, -w / 2 + 0.03, w / 2 - 0.03, d / 2, d, z0 + 0.015, z0 + h - 0.015, "lamp_glass", "k")
    return mb


def bulb_bare(s, v, rng):
    """A bare bulb on its black wire: poor rooms, stores, the stah door."""
    w, d, h = s
    mb = MeshBuilder()
    _lathed(mb, [(0.004, -h + 0.10), (0.004, 0.0)], "iron_black", 3)
    _lathed(mb, [(0.0, -h), (w / 2, -h + 0.05), (0.012, -h + 0.10)], "lamp_glass", 6)
    return mb


def lamp_bedside(s, v, rng):
    """The bedside lamp of a nightstand: a white ceramic foot and stem, the bulb, a beige fabric shade."""
    w, d, h = s
    mb = MeshBuilder()
    _lathed(mb, [(0.06, 0.0), (0.05, 0.03), (0.012, 0.05)], "ceramic_white", 6)
    _lathed(mb, [(0.012, 0.05), (0.012, 0.24)], "ceramic_white", 4)
    _lathed(mb, [(0.03, 0.22), (0.0, 0.30)], "lamp_glass", 4)
    _lathed(mb, [(w / 2, 0.21), (0.09, h)], "fabric_beige", 8)
    return mb


def _ball(mb: MeshBuilder, x, y, z, r: float, mat: str, n: int = 4) -> None:
    """A small round thing (a fruit, a flower head): two lathed cones, `2 * 2n` triangles."""
    _lathed(mb, [(0.0, -r), (r, 0.0), (0.0, r)], mat, n, at=(x, y, z))


def _pot(mb: MeshBuilder, w: float, rim_z: float) -> None:
    """A terracotta flower pot widening to its rim at `rim_z`, the rim's top turned in: 32 triangles."""
    r = w / 2
    _lathed(mb, [(r * 0.7, 0.0), (r, rim_z), (r - 0.025, rim_z)], "terracotta", 8)


def pot_geranium(s, v, rng):
    """A geranium in its pot at a court's edge or on the stah: a mound of leaves and two red flower heads."""
    w, d, h = s
    mb = MeshBuilder()
    _pot(mb, w, 0.28)
    _lathed(mb, [(0.0, 0.24), (w / 2 - 0.015, 0.36), (0.10, 0.44), (0.0, 0.46)], "leaf_green", 8)
    for x, y in ((0.05, 0.03), (-0.06, -0.04)):
        _ball(mb, x, y, h - 0.035, 0.035, "awning_red")
    return mb


def pot_basil(s, v, rng):
    """Basil or mint in a small pot by the kitchen or on a court sill: one round clump of leaves."""
    w, d, h = s
    mb = MeshBuilder()
    _pot(mb, w, 0.13)
    _lathed(mb, [(0.0, 0.11), (w / 2 - 0.01, 0.20), (0.0, h)], "leaf_green", 6)
    return mb


def plates_stack(s, v, rng):
    """A pile of white plates on a shelf or a counter."""
    w, d, h = s
    mb = MeshBuilder()
    _lathed(mb, [(w / 2 - 0.02, 0.0), (w / 2, h), (0.0, h)], "ceramic_white", 8)
    return mb


def fruit_bowl(s, v, rng):
    """A white bowl of oranges and an apple on a dining or kitchen table."""
    w, d, h = s
    r = w / 2
    mb = MeshBuilder()
    _lathed(mb, [(0.05, 0.0), (r, 0.08), (r - 0.02, 0.08), (0.04, 0.03)], "ceramic_white", 8)
    _ball(mb, 0.04, 0.0, h - 0.04, 0.04, "awning_yellow")
    _ball(mb, -0.05, 0.02, h - 0.045, 0.04, "awning_red")
    return mb


def oil_bidon(s, v, rng):
    """The yellow plastic can of olive oil by the cooker or in the store: its cap and its handle."""
    w, d, h = s
    mb = MeshBuilder()
    body = h - 0.05
    _box(mb, -w / 2, w / 2, -d / 2, d / 2, 0.0, body, "plastic_yellow")
    _lathed(mb, [(0.02, body), (0.02, body + 0.03), (0.0, body + 0.03)], "plastic_yellow", 5, at=(0.05, 0.0, 0.0))
    _box(mb, -0.08, -0.02, -0.01, 0.01, body, h, "plastic_yellow")
    return mb


def pot_jasmine(s, v, rng):
    """The jasmine of a court corner, the stah or a balcony: a tall bush in its pot, white flowers on it."""
    w, d, h = s
    r = w / 2
    mb = MeshBuilder()
    _pot(mb, 0.34, 0.34)
    _lathed(mb, [(0.0, 0.30), (r - 0.025, 0.55), (r, 0.85), (r - 0.075, 1.08), (0.0, h - 0.05)], "leaf_green", 8)
    for k, z in enumerate((0.62, 0.74, 0.86, 0.95, 1.02)):
        a = k * 2.4
        _ball(mb, (r - 0.05) * math.cos(a), (r - 0.05) * math.sin(a), z, 0.025, "cotton_white")
    _ball(mb, 0.0, 0.0, h - 0.025, 0.025, "cotton_white")
    return mb


def vase_flowers(s, v, rng):
    """Plastic flowers in a glass vase on a coffee table or the buffet: two red heads and a green sprig."""
    w, d, h = s
    mb = MeshBuilder()
    _lathed(mb, [(0.04, 0.0), (0.065, 0.10), (0.03, 0.20)], "glass_inner", 6)
    for (x, y), mat in zip(((0.04, 0.0), (-0.02, 0.04), (-0.02, -0.04)), ("awning_red", "awning_red", "leaf_green")):
        _ball(mb, x, y, h - 0.035 - (0.03 if mat == "leaf_green" else 0.0), 0.035, mat)
    return mb


def photo_frame(s, v, rng):
    """A framed family photograph on the wall."""
    w, d, h = s
    z0 = TABLE["photo_frame"][4]["z0"]
    mb = MeshBuilder()
    _box(mb, -w / 2, w / 2, 0.0, d - 0.001, z0, z0 + h, "wood_walnut", "k")
    _front(mb, -w / 2 + 0.04, w / 2 - 0.04, z0 + 0.04, z0 + h - 0.04, d, "photo_sepia")
    return mb


def khomsa(s, v, rng):
    """The brass hand over the inside of the main door: a palm and five fingers, two of them thumbs."""
    w, d, h = s
    z0 = TABLE["khomsa"][4]["z0"]
    mb = MeshBuilder()
    _box(mb, -0.055, 0.055, 0.0, d - 0.002, z0, z0 + 0.10, "brass", "kb")
    fingers = ((-w / 2, -0.055, 0.03, 0.13), (-0.05, -0.018, 0.09, 0.19), (-0.016, 0.016, 0.09, 0.20),
               (0.018, 0.05, 0.09, 0.19), (0.055, w / 2, 0.03, 0.13))
    for x0, x1, a, b in fingers:
        _front(mb, x0, x1, z0 + a, z0 + b, d, "brass")
    return mb


MAKERS = {"fanous": fanous, "lantern_table": lantern_table, "ceiling_lamp": ceiling_lamp, "chandelier": chandelier,
          "neon": neon, "bulb_bare": bulb_bare, "lamp_bedside": lamp_bedside, "pot_geranium": pot_geranium,
          "pot_basil": pot_basil, "plates_stack": plates_stack, "fruit_bowl": fruit_bowl, "oil_bidon": oil_bidon,
          "pot_jasmine": pot_jasmine, "vase_flowers": vase_flowers, "photo_frame": photo_frame, "khomsa": khomsa}


def names() -> list:
    """Every piece name of the life table (without `home/`), variants spelled out, in table order."""
    return [n for b in TABLE for n in ([f"{b}_{v}" for v in VARIANTS[b]] if b in VARIANTS else [b])]


def pieces(seed: int, cfg: dict) -> dict:
    """{name: (MeshBuilder, category, anchor, spec dict)} of every life piece; `cfg` is the style's
    `[interiors.furnish]` (its `sizes` override `SIZES`)."""
    over = (cfg or {}).get("sizes", {})
    out = {}
    for base, (cat, anchor, _size, tris, extra) in TABLE.items():
        for suffix in VARIANTS.get(base, (None,)):
            name = base if suffix is None else f"{base}_{suffix}"
            size = tuple(float(v) for v in over.get(name, over.get(base, SIZES.get(name, SIZES[base]))))
            rng = stream(seed, "piece", f"home/{name}")
            out[name] = (MAKERS[base](size, suffix or "", rng), cat, anchor, {"size": size, "tris": tris, **extra})
    return out
