"""The modern pieces of the home kit, and those of shops and cafes (prompt 53, SPEC 6d "Catalog: modern
homes, shops and cafes").

Same frame and rules as `kit_old`: x along the wall, front +y, z up, meters; `wall` pieces stand in front of
the wall face (every y >= 0), `floor` and `on` pieces are centered on their origin at the bottom, a hanging
piece keeps its height in its own mesh (a wall cabinet starts at z 1.45). Stretch pieces are 1.0 m long.
Boxes show only the faces a person can see; doors stand a little proud of a carcass whose front shows in a
darker material, so the gaps between doors read as lines. Textured book and goods rows map one image row
to one shelf space (`_row`). Random details (a crate's shift, which cloth hangs on the rack) draw only on
`stream(seed, "piece", "home/<name>")`.
"""
from __future__ import annotations

import math

import numpy as np
from shapely.geometry import Polygon

from ..mesh.builder import MeshBuilder, add_sheet, add_triangles, triangulate
from ..mesh.furniture import _tube
from ..mesh.props import _faces, _slab
from ..rng import stream
from .kit_old import (SWAP_YZ, VELVET, _box, _lathed, _leg, _moved, _oriented, _pad, _pillow, _prism,
                      _pyramid, _ring, _rug)

# name: (category, anchor, (W, D, H), tris, extra), as kit_old.TABLE
TABLE = {
    "sofa_3": ("seat", "wall", (2.10, 0.90, 0.85), 320, {"use": 0.6}),
    "sofa_2": ("seat", "wall", (1.60, 0.90, 0.85), 260, {"use": 0.6}),
    "armchair": ("seat", "wall", (0.90, 0.85, 0.85), 200, {"use": 0.6}),
    "sedari": ("seat", "wall", (1.0, 0.75, 0.80), 60, {"stretch": (0.8, 4.0), "use": 0.5, "top": 0.34}),
    "coffee_table": ("table", "floor", (1.10, 0.60, 0.45), 80, {"top": 0.45}),
    "side_table": ("table", "wall", (0.50, 0.50, 0.55), 60, {"top": 0.55}),
    "tv_stand": ("storage", "wall", (1.60, 0.45, 0.50), 90, {"top": 0.50, "use": 0.5}),
    "tv_flat": ("decor", "on", (1.10, 0.22, 0.70), 40, {}),
    "tv_crt": ("decor", "on", (0.60, 0.50, 0.50), 60, {}),
    "receiver": ("small", "on", (0.28, 0.20, 0.05), 12, {"top": 0.05}),
    "buffet": ("storage", "wall", (1.80, 0.50, 1.90), 300, {"top": 0.86, "use": 0.6}),
    "dining_table": ("table", "floor", (1.60, 0.90, 0.76), 60, {"top": 0.76}),
    "dining_chair": ("seat", "floor", (0.45, 0.50, 0.95), 90, {}),
    "plastic_table": ("table", "floor", (0.80, 0.80, 0.72), 60, {"top": 0.72}),
    "plastic_chair": ("seat", "floor", (0.55, 0.55, 0.80), 120, {}),
    "stool": ("seat", "floor", (0.35, 0.35, 0.45), 40, {}),
    "kitchen_run": ("kitchen", "wall", (1.0, 0.60, 0.90), 40, {"stretch": (0.6, 4.0), "top": 0.90, "use": 0.6}),
    "kitchen_sink": ("kitchen", "wall", (1.00, 0.60, 1.12), 90, {"top": 0.90, "use": 0.6}),   # H: its tap
    "cooker": ("kitchen", "wall", (0.60, 0.60, 0.86), 140, {"top": 0.86, "use": 0.6}),
    "fridge": ("kitchen", "wall", (0.60, 0.65, 1.45), 70, {"use": 0.7}),
    "wall_cabinet": ("kitchen", "wall", (1.0, 0.35, 0.70), 30, {"stretch": (0.6, 3.0), "z0": 1.45}),
    "microwave": ("small", "on", (0.48, 0.36, 0.28), 40, {}),
    "table_formica": ("table", "floor", (0.90, 0.60, 0.75), 40, {"top": 0.75}),
    "bed_double": ("bed", "wall", (1.50, 2.05, 1.10), 200, {"top": 0.52, "use": 0.5}),
    "nightstand": ("storage", "wall", (0.45, 0.40, 0.50), 60, {"top": 0.50}),
    "wardrobe": ("storage", "wall", (1.50, 0.60, 2.10), 90, {"use": 0.7}),
    "coiffeuse": ("storage", "wall", (1.10, 0.45, 1.60), 150, {"top": 0.76, "use": 0.6}),
    "bed_single": ("bed", "wall", (0.95, 2.00, 0.90), 120, {"top": 0.52, "use": 0.5}),
    "bunk_bed": ("bed", "wall", (0.95, 2.00, 1.65), 260, {"use": 0.5}),
    "cot": ("bed", "wall", (0.65, 1.25, 0.95), 180, {"use": 0.4}),
    "desk": ("table", "wall", (1.10, 0.55, 0.75), 60, {"top": 0.75, "use": 0.7}),
    "desk_chair": ("seat", "floor", (0.45, 0.50, 0.90), 90, {}),
    "bookcase": ("storage", "wall", (0.80, 0.30, 1.80), 80, {"use": 0.5}),
    "piano": ("decor", "wall", (1.45, 0.60, 1.25), 180, {"top": 1.25, "use": 0.7}),
    "wc_seat": ("bath", "wall", (0.40, 0.70, 0.80), 160, {"use": 0.5}),
    "basin": ("bath", "wall", (0.55, 0.45, 0.85), 120, {"use": 0.5}),
    "mirror_bath": ("decor", "wall", (0.50, 0.04, 0.60), 20, {"z0": 1.25}),
    "shower": ("bath", "wall", (0.80, 0.80, 2.00), 90, {"use": 0.5}),
    "bathtub": ("bath", "wall", (1.60, 0.70, 0.55), 140, {"use": 0.5}),
    "water_heater": ("bath", "wall", (0.35, 0.25, 0.65), 80, {"z0": 1.40}),
    "washing_machine": ("bath", "wall", (0.60, 0.60, 0.85), 90, {"top": 0.85, "use": 0.6}),
    "drying_rack": ("textile", "floor", (1.70, 0.55, 1.00), 160, {}),
    "shoe_cabinet": ("storage", "wall", (0.80, 0.30, 0.95), 40, {"top": 0.95}),
    "coat_hooks": ("decor", "wall", (0.60, 0.08, 0.25), 30, {"z0": 1.55}),
    "doormat": ("rug", "floor", (0.60, 0.40, 0.01), 2, {}),
    "rug_floral": ("rug", "floor", (1.60, 2.30, 0.01), 10, {}),
    "shop_counter": ("shop", "wall", (1.0, 0.60, 1.00), 30, {"stretch": (0.8, 4.0), "top": 1.00, "use": 0.6}),
    "shop_shelves": ("shop", "wall", (1.0, 0.40, 2.20), 60, {"stretch": (0.6, 4.0), "use": 0.6}),
    "scale": ("small", "on", (0.40, 0.30, 0.30), 60, {}),
    "drinks_fridge": ("shop", "wall", (0.65, 0.65, 1.90), 80, {"use": 0.6}),
    "espresso": ("small", "on", (0.60, 0.50, 0.45), 120, {}),
    "tv_bracket": ("decor", "wall", (1.10, 0.30, 0.70), 50, {"z0": 2.00}),
    "chicha": ("small", "floor", (0.25, 0.25, 0.75), 100, {}),
    "crate_stack": ("storage", "wall", (0.60, 0.40, 0.90), 40, {"top": 0.90}),
}
TRADES = ("spices", "perfume", "pots", "copper", "chechia", "fruit", "cloth")   # mesh/props.SHOP_GOODS
VARIANTS = {
    "sofa_3": ("beige", "grey", "red"), "sofa_2": ("beige", "grey", "red"), "armchair": ("beige", "grey", "red"),
    "sedari": ("red", "green", "blue"), "coffee_table": ("wood", "glass"), "tv_stand": ("walnut", "beech"),
    "tv_flat": ("large", "small"), "buffet": ("walnut", "modern", "carved"), "dining_table": ("4", "6", "8"),
    "dining_chair": ("wood", "carved"), "kitchen_run": ("white", "wood"), "kitchen_sink": ("white", "wood"),
    "cooker": ("white", "steel"), "fridge": ("small", "tall"), "wall_cabinet": ("white", "wood"),
    "bed_double": ("140_mink", "140_white", "160_mink", "160_white"), "wardrobe": ("2", "3", "4", "mirror"),
    "bed_single": ("mink", "blue", "pink"), "bunk_bed": ("iron", "wood"), "bookcase": ("full", "half"),
    "water_heater": ("gas", "electric"), "rug_floral": ("medium", "large"), "shop_counter": ("hanout", "cafe"),
    "shop_shelves": ("grocer",) + TRADES,
}
VARIANT_SIZES = {
    "tv_flat_small": (0.80, 0.20, 0.52), "buffet_carved": (2.00, 0.55, 2.20), "dining_table_4": (1.20, 0.80, 0.76),
    "dining_table_8": (2.10, 1.00, 0.76), "fridge_tall": (0.70, 0.70, 1.80), "bed_double_160_mink": (1.70, 2.05, 1.10),
    "bed_double_160_white": (1.70, 2.05, 1.10), "wardrobe_2": (1.00, 0.60, 2.10), "wardrobe_4": (2.00, 0.60, 2.10),
    "wardrobe_mirror": (1.40, 0.60, 2.30), "water_heater_electric": (0.45, 0.45, 0.80), "rug_floral_large": (2.00, 2.90, 0.01),
}
VARIANT_EXTRA = {"water_heater_electric": {"z0": 1.60}}
SIZES = {**{b: row[2] for b, row in TABLE.items()}, **VARIANT_SIZES}   # `[interiors.furnish.sizes]` overrides
FABRIC = {"beige": "fabric_beige", "grey": "fabric_grey", "red": "velvet_red"}
COVER = {"mink": "mink", "white": "cotton_white", "blue": "cotton_blue", "pink": "cotton_pink"}
RUN = {"white": "formica_white", "wood": "wood_beech"}
TEX_H = {"spines": 0.28, "goods": 0.32}     # the v size of `[interiors.palette]` spines and goods: one shelf row
RUG_FLORAL = (1.6, 2.3)                     # its texture_size: the whole rug is one repeat


# --- helpers ------------------------------------------------------------------------------------------

def _quad(mb: MeshBuilder, quad, normal, mat: str) -> None:
    _faces(mb, [_oriented(quad, normal)], mat)


def _front(mb: MeshBuilder, x0, x1, z0, z1, y, mat: str, normal=(0, 1, 0)) -> None:
    """A face in the plane y, seen from the front (+y)."""
    _quad(mb, [(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)], normal, mat)


def _knob(mb: MeshBuilder, x, y, z, r: float, mat: str, out: float | None = None) -> None:
    """A small square knob on a front face at depth y, standing `out` (default 1.2 r) toward +y (4 triangles)."""
    base = [(x - r, y, z - r), (x + r, y, z - r), (x + r, y, z + r), (x - r, y, z + r)]
    _pyramid(mb, base, (x, y + (out if out is not None else 1.2 * r), z), mat)


def _uvquad(mb: MeshBuilder, mat: str, quad, uv, normal) -> None:
    """One quad with the UVs given (meters), turned to face `normal`."""
    q, u = np.asarray(quad, dtype=np.float64), np.asarray(uv, dtype=np.float64)
    n = np.cross(q[1] - q[0], q[2] - q[0])
    if float(np.dot(n, normal)) < 0:
        q, u, n = q[::-1].copy(), u[::-1].copy(), -n
    mb.add(mat, q, np.tile(n / np.linalg.norm(n), (4, 1)), u, [[0, 1, 2], [0, 2, 3]])


def _row(mb: MeshBuilder, mat: str, x0, x1, y0, y1, z0, side: bool = True) -> None:
    """A row of books or goods standing on z0: its front shows one image row exactly (its top the row's
    top), its top the colours of the image's foot; `side` adds its right end (6 triangles)."""
    h = TEX_H[mat.split("_")[0]]
    z1 = z0 + h
    _uvquad(mb, mat, [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)],
            [(x0, h), (x1, h), (x1, 0.0), (x0, 0.0)], (0, 1, 0))
    foot = h * 0.9
    _uvquad(mb, mat, [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
            [(x0, foot), (x1, foot), (x1, foot), (x0, foot)], (0, 0, 1))
    if side:
        _uvquad(mb, mat, [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
                [(x1, h), (x1 + y1 - y0, h), (x1 + y1 - y0, 0.0), (x1, 0.0)], (1, 0, 0))


def _crest(mb: MeshBuilder, a: float, b: float, z0: float, y0: float, y1: float, mat: str, n: int = 4,
           base: float = 0.0) -> None:
    """A flat carved crest in the x-z plane: a rectangle `base` tall under a half ellipse `a` wide each
    side and `b` tall, from depth y0 to y1."""
    pts = [(a * math.cos(t), z0 + base + b * math.sin(t)) for t in np.linspace(0.0, math.pi, n + 1)]
    if base > 0:
        pts += [(-a, z0), (a, z0)]
    _slab(mb, Polygon(pts), y0, y1, mat)


def _taper(mb: MeshBuilder, x, y, z0, z1, r0: float, r1: float, mat: str) -> None:
    """A square leg tapering from r1 at its top to r0 at its foot (8 triangles)."""
    _lathed(mb, [(r0, z0), (r1, z1)], mat, 4, at=(x, y, 0.0), turn=math.pi / 4)


def _frame(mb: MeshBuilder, outer, inner, z: float, mat: str) -> None:
    """A flat top at z between two rectangles (x0, x1, y0, y1), the inner one a hole (8 triangles)."""
    (a0, a1, b0, b1), (c0, c1, d0, d1) = outer, inner
    o = [(a0, b0), (a1, b0), (a1, b1), (a0, b1)]
    i = [(c0, d0), (c1, d0), (c1, d1), (c0, d1)]
    quads = [[(*o[k], z), (*o[(k + 1) % 4], z), (*i[(k + 1) % 4], z), (*i[k], z)] for k in range(4)]
    _faces(mb, [_oriented(q, (0, 0, 1)) for q in quads], mat)


def _bowl(mb: MeshBuilder, x0, x1, y0, y1, zt, zb, inset: float, mat: str) -> None:
    """An open bowl under a top at zt: four walls narrowing by `inset` to its floor at zb, and the floor."""
    a = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    b = [(x0 + inset, y0 + inset), (x1 - inset, y0 + inset), (x1 - inset, y1 - inset), (x0 + inset, y1 - inset)]
    c = np.array([(x0 + x1) / 2, (y0 + y1) / 2, zt])
    quads = []
    for k in range(4):
        q = [(*a[k], zt), (*a[(k + 1) % 4], zt), (*b[(k + 1) % 4], zb), (*b[k], zb)]
        quads.append(_oriented(q, c - np.mean(q, axis=0)))
    quads.append(_oriented([(*p, zb) for p in b], (0, 0, 1)))
    _faces(mb, quads, mat)


def _door(mb: MeshBuilder, x0, x1, z0, z1, y0, y1, mat: str) -> None:
    """A door or drawer front standing proud of its carcass: its face and its two side edges (6)."""
    _box(mb, x0, x1, y0, y1, z0, z1, mat, "bkt")


# --- the salon ----------------------------------------------------------------------------------------

def _sofa(seats: int):
    def make(s, v, rng):
        """The salon set: wooden feet, a base, a padded back and arms, seat cushions with bevelled edges
        and soft back cushions, one fabric per room."""
        w, d, h = s
        fab = FABRIC[v]
        arm = 0.17 if seats > 1 else 0.15
        mb = MeshBuilder()
        for x in (-w / 2 + 0.07, w / 2 - 0.07):
            for y in (0.08, d - 0.08):
                _leg(mb, x, y, 0.0, 0.10, 0.025, "wood_walnut")
        _box(mb, -w / 2 + arm - 0.01, w / 2 - arm + 0.01, 0.02, d - 0.03, 0.10, 0.40, fab, "bklr")
        _pad(mb, -w / 2 + arm - 0.005, w / 2 - arm + 0.005, 0.0, 0.22, 0.40, h, fab, 0.05, "k")
        for x0, x1 in ((-w / 2, -w / 2 + arm), (w / 2 - arm, w / 2)):
            _pad(mb, x0, x1, 0.0, d, 0.10, 0.64, fab, 0.05, "k")
        iw = w - 2 * arm
        cw = (iw - 0.012 * (seats - 1)) / seats
        for k in range(seats):
            cx = -iw / 2 + cw / 2 + k * (cw + 0.012)
            _pad(mb, cx - cw / 2, cx + cw / 2, 0.22, d - 0.015, 0.40, 0.54, fab, 0.04)
            tmp = MeshBuilder()
            _pillow(tmp, fab, cw - 0.02, 0.30, 0.525, 0.225, 0.29, 0.37, 0.05)
            _moved(mb, tmp, np.eye(3), (cx, 0.0, 0.0))
        return mb
    return make


def sedari(s, v, rng):
    """The salon tunisien's banquette: a walnut base, a velvet mattress piped in gold, one long back
    cushion with a gold cord along its top, its ends closed (two runs meet in a corner by collision)."""
    w, d, h = s
    vel = VELVET[v]
    mb = MeshBuilder()
    _box(mb, -w / 2, w / 2, 0.0, d, 0.0, 0.12, "wood_walnut", "bkt")
    _pad(mb, -w / 2, w / 2, 0.0, d - 0.01, 0.12, 0.34, vel, 0.035, "k")
    _tube(mb, (-w / 2, d - 0.012, 0.305), (w / 2, d - 0.012, 0.305), (0.008, 0.008), "velvet_gold")
    prof = [(0.0, 0.34), (0.22, 0.34), (0.235, 0.60), (0.18, 0.74), (0.08, h), (0.0, h)]
    _prism(mb, prof, -w / 2, w / 2, [None, vel, vel, vel, vel], vel)   # its foot lies on the mattress: not drawn
    _tube(mb, (-w / 2, 0.18, 0.742), (w / 2, 0.18, 0.742), (0.007, 0.007), "velvet_gold")
    return mb


def coffee_table(s, v, rng):
    """The salon's low table: walnut with a lower shelf, or (`_glass`) a glass top and shelf on chrome."""
    w, d, h = s
    mb = MeshBuilder()
    hx, hy = w / 2 - 0.05, d / 2 - 0.05
    if v == "glass":
        for x in (-hx, hx):
            for y in (-hy, hy):
                _tube(mb, (x, y, 0.0), (x, y, h - 0.02), (0.012, 0.012), "chrome")
        for y in (-hy, hy):
            _tube(mb, (-hx, y, h - 0.032), (hx, y, h - 0.032), (0.010, 0.012), "chrome")
        _box(mb, -w / 2, w / 2, -d / 2, d / 2, h - 0.02, h, "glass_inner", "")
        _box(mb, -hx + 0.02, hx - 0.02, -hy + 0.02, hy - 0.02, 0.10, 0.112, "glass_inner", "")
        return mb
    for x in (-hx, hx):
        for y in (-hy, hy):
            _taper(mb, x, y, 0.0, h - 0.03, 0.018, 0.026, "wood_walnut")
    _pad(mb, -w / 2, w / 2, -d / 2, d / 2, h - 0.035, h, "wood_walnut", 0.008)
    _box(mb, -hx, hx, -hy, hy, 0.10, 0.12, "wood_walnut", "b")
    return mb


def side_table(s, v, rng):
    """A small walnut table beside an armchair: four legs, a drawer, a top."""
    w, d, h = s
    mb = MeshBuilder()
    for x in (-w / 2 + 0.04, w / 2 - 0.04):
        for y in (0.04, d - 0.04):
            _taper(mb, x, y, 0.0, h - 0.03, 0.014, 0.02, "wood_walnut")
    _box(mb, -w / 2, w / 2, 0.0, d, h - 0.03, h, "wood_walnut", "")
    _box(mb, -w / 2 + 0.03, w / 2 - 0.03, 0.03, d - 0.02, h - 0.14, h - 0.03, "wood_walnut", "bkt")
    _knob(mb, 0.0, d - 0.02, h - 0.085, 0.012, "brass")
    return mb


def tv_stand(s, v, rng):
    """The low television cabinet: a plinth, two doors with handles round an open niche (the receiver's
    shelf), the television on its top."""
    w, d, h = s
    wood = "wood_beech" if v == "beech" else "wood_walnut"
    mb = MeshBuilder()
    d -= 0.036                         # the carcass; doors and handles stand out to the full depth
    nx, nz0, nz1, yn = 0.30, 0.12, 0.42, 0.08
    _box(mb, -w / 2 + 0.04, w / 2 - 0.04, 0.0, d - 0.04, 0.0, 0.06, "wood_walnut", "bkt")
    _box(mb, -w / 2, w / 2, 0.0, d, 0.06, h, wood, "bkf")
    for x0, x1, z0, z1 in ((-w / 2, -nx, 0.06, h), (nx, w / 2, 0.06, h), (-nx, nx, 0.06, nz0), (-nx, nx, nz1, h)):
        _front(mb, x0, x1, z0, z1, d, wood)
    _front(mb, -nx, nx, nz0, nz1, yn, wood)
    _quad(mb, [(-nx, yn, nz0), (nx, yn, nz0), (nx, d, nz0), (-nx, d, nz0)], (0, 0, 1), wood)
    _quad(mb, [(-nx, yn, nz1), (nx, yn, nz1), (nx, d, nz1), (-nx, d, nz1)], (0, 0, -1), wood)
    _quad(mb, [(-nx, yn, nz0), (-nx, d, nz0), (-nx, d, nz1), (-nx, yn, nz1)], (1, 0, 0), wood)
    _quad(mb, [(nx, yn, nz0), (nx, d, nz0), (nx, d, nz1), (nx, yn, nz1)], (-1, 0, 0), wood)
    for sx in (-1, 1):
        x0, x1 = sorted((sx * (nx + 0.02), sx * (w / 2 - 0.02)))
        _door(mb, x0, x1, 0.09, h - 0.03, d, d + 0.016, wood)
        k = sx * (nx + 0.08)
        _tube(mb, (k, d + 0.03, 0.36), (k, d + 0.03, 0.44), (0.006, 0.006), "chrome")
    return mb


def tv_flat(s, v, rng):
    """The flat television on its foot: a black panel with a glossy screen, a neck and a foot plate."""
    w, d, h = s
    mb = MeshBuilder()
    zb = h * 0.16
    _box(mb, -w / 2, w / 2, -0.035, 0.015, zb, h, "plastic_black", "")
    _front(mb, -w / 2 + 0.02, w / 2 - 0.02, zb + 0.03, h - 0.02, 0.017, "screen_black")
    _box(mb, -w * 0.17, w * 0.17, -d / 2, d / 2, 0.0, 0.018, "plastic_black", "b")
    _box(mb, -0.035, 0.035, -0.07, -0.035, 0.018, zb + 0.06, "plastic_black", "bt")
    return mb


def tv_crt(s, v, rng):
    """The old television of poor homes: a grey case with a bulging screen, two buttons, and the deep
    back of its tube tapering behind."""
    w, d, h = s
    mb = MeshBuilder()
    yf, yb = d / 2, d / 2 - 0.13
    _box(mb, -w / 2, w / 2, yb, yf, 0.0, h, "plastic_grey", "b")
    zc, bw, bh = h * 0.52, w * 0.28, h * 0.30
    fr = [(-w / 2 + 0.03, yb, 0.03), (w / 2 - 0.03, yb, 0.03), (w / 2 - 0.03, yb, h - 0.03), (-w / 2 + 0.03, yb, h - 0.03)]
    bk = [(-bw, -d / 2, zc - bh), (bw, -d / 2, zc - bh), (bw, -d / 2, zc + bh), (-bw, -d / 2, zc + bh)]
    centre = np.array([0.0, (yb - d / 2) / 2, zc])
    quads = [[fr[k], fr[(k + 1) % 4], bk[(k + 1) % 4], bk[k]] for k in range(4)]
    _faces(mb, [_oriented(q, np.mean(q, axis=0) - centre) for q in quads] + [_oriented(bk, (0, -1, 0))], "plastic_grey")
    ring = [(-w / 2 + 0.05, yf + 0.001, 0.10), (w / 2 - 0.05, yf + 0.001, 0.10), (w / 2 - 0.05, yf + 0.001, h - 0.05),
            (-w / 2 + 0.05, yf + 0.001, h - 0.05)]
    _pyramid(mb, ring, (0.0, yf + 0.018, (0.10 + h - 0.05) / 2), "screen_black")
    for x in (w / 2 - 0.10, w / 2 - 0.16):
        _knob(mb, x, yf, 0.055, 0.012, "plastic_black")
    return mb


def receiver(s, v, rng):
    """The satellite receiver: a black box with its display."""
    w, d, h = s
    mb = MeshBuilder()
    _box(mb, -w / 2, w / 2, -d / 2, d / 2, 0.0, h, "plastic_black", "b")
    _front(mb, 0.02, 0.09, 0.015, 0.035, d / 2 + 0.001, "screen_black")
    return mb


def _plate(mb: MeshBuilder, x, y, z, r: float, lean: float) -> None:
    """A plate standing on its rim, leaning back `lean` radians, seen from the front (6 triangles)."""
    ex, ez = np.array([1.0, 0.0, 0.0]), np.array([0.0, -math.sin(lean), math.cos(lean)])
    c = np.array([x, y, z]) + ez * r
    pts = [c + r * (math.cos(t) * ex + math.sin(t) * ez) for t in np.arange(8) * math.pi / 4]
    tris = [_oriented([pts[0], pts[k], pts[k + 1]], (0, math.cos(lean), math.sin(lean))) for k in range(1, 7)]
    add_triangles(mb, tris, "ceramic_white")


def buffet(s, v, rng):
    """The vaisselier with the good dishes: a lower cabinet of three doors with brass knobs, a top, and the
    glass case with a shelf where plates stand on their rims; a carved crest on `_carved`."""
    w, d, h = s
    wood = "wood_beech" if v == "modern" else "wood_walnut"
    mb = MeshBuilder()
    zl, dc = 0.86, 0.36
    ztop = h - (0.20 if v == "carved" else 0.0)
    _box(mb, -w / 2 + 0.03, w / 2 - 0.03, 0.0, d - 0.04, 0.0, 0.08, wood, "bkt")
    _box(mb, -w / 2 + 0.01, w / 2 - 0.01, 0.0, d - 0.02, 0.08, zl - 0.03, wood, "bkt")
    _box(mb, -w / 2, w / 2, 0.0, d, zl - 0.03, zl, wood, "k")
    edges = np.linspace(-w / 2 + 0.03, w / 2 - 0.03, 4)
    for x0, x1 in zip(edges[:-1], edges[1:]):
        _door(mb, x0 + 0.008, x1 - 0.008, 0.11, zl - 0.06, d - 0.02, d - 0.004, wood)
        _knob(mb, (x0 + x1) / 2, d - 0.004, zl - 0.16, 0.014, "brass")
    for sx in (-1, 1):
        x0, x1 = sorted((sx * (w / 2 - 0.03), sx * (w / 2 - 0.07)))
        _box(mb, x0, x1, 0.0, dc, zl, ztop - 0.08, wood, "bkt")
    _front(mb, -w / 2 + 0.07, w / 2 - 0.07, zl, ztop - 0.08, 0.01, wood)
    _box(mb, -w / 2, w / 2, 0.0, dc + 0.03, ztop - 0.08, ztop, wood, "k")
    zs = (zl + ztop - 0.08) / 2
    _box(mb, -w / 2 + 0.07, w / 2 - 0.07, 0.01, dc - 0.02, zs - 0.02, zs, wood, "bklr")
    _front(mb, -w / 2 + 0.07, w / 2 - 0.07, zl, ztop - 0.08, dc, "glass_inner")
    _tube(mb, (0.0, dc + 0.008, zl), (0.0, dc + 0.008, ztop - 0.08), (0.015, 0.008), wood)
    for z0 in (zl, zs):
        for x in np.linspace(-w / 2 + 0.20, w / 2 - 0.20, 6):
            _plate(mb, float(x), 0.06, z0, 0.11, 0.25)
    if v == "carved":
        _crest(mb, w * 0.30, 0.21, ztop - 0.01, 0.04, 0.07, wood, 6)
    return mb


def dining_table(s, v, rng):
    """The salle a manger's table: a top over an apron on four tapering legs."""
    w, d, h = s
    wood = "wood_beech" if v == "4" else "wood_walnut"
    mb = MeshBuilder()
    _box(mb, -w / 2, w / 2, -d / 2, d / 2, h - 0.035, h, wood, "")
    _box(mb, -w / 2 + 0.07, w / 2 - 0.07, -d / 2 + 0.07, d / 2 - 0.07, h - 0.13, h - 0.035, wood, "tb")
    for x in (-w / 2 + 0.08, w / 2 - 0.08):
        for y in (-d / 2 + 0.08, d / 2 - 0.08):
            _taper(mb, x, y, 0.0, h - 0.035, 0.022, 0.034, wood)
    return mb


def _chair(s, wood: str, seat: str, carved: bool) -> MeshBuilder:
    """A chair (front +y): tapering front legs, raked back legs rising into the back posts, a seat frame
    and a padded seat, a top rail (arched on a carved one) and a middle rail."""
    w, d, h = s
    zs = 0.46
    hx, yf = w / 2 - 0.03, d / 2 - 0.03
    mb = MeshBuilder()
    for x in (-hx, hx):
        _taper(mb, x, yf, 0.0, zs - 0.05, 0.014, 0.019, wood)
        _tube(mb, (x, -d / 2 + 0.06, 0.0), (x, -d / 2 + 0.018, h), (0.018, 0.018), wood, cap=True)
    _box(mb, -w / 2, w / 2, -d / 2 + 0.02, d / 2 - 0.01, zs - 0.06, zs - 0.02, wood, "t")
    _pad(mb, -w / 2 + 0.015, w / 2 - 0.015, -d / 2 + 0.05, d / 2, zs - 0.02, zs + 0.03, seat, 0.02)
    rake = lambda z: -d / 2 + 0.06 - 0.042 * z / (h - 0.01)   # noqa: E731  the back post's y at height z
    if carved:
        _crest(mb, hx, 0.10, h - 0.22, rake(h) - 0.012, rake(h) + 0.012, wood, 3, base=0.10)
    else:
        y = rake(h - 0.08)
        _box(mb, -hx, hx, y - 0.012, y + 0.012, h - 0.14, h - 0.02, wood, "")
        y = rake(zs + 0.20)
        _box(mb, -hx, hx, y - 0.01, y + 0.01, zs + 0.16, zs + 0.23, wood, "b")
    return mb


def dining_chair(s, v, rng):
    """The dining chair: beech with a beige seat, or (`_carved`, colonial) walnut, an arched rail, red velvet."""
    return _chair(s, "wood_walnut", "velvet_red", True) if v == "carved" else _chair(s, "wood_beech", "fabric_beige", False)


def desk_chair(s, v, rng):
    """The chair at every desk: beech with a grey seat."""
    return _chair(s, "wood_beech", "fabric_grey", False)


def plastic_table(s, v, rng):
    """The white plastic table of terraces and courts: a top with a deep rim on four splayed legs."""
    w, d, h = s
    mb = MeshBuilder()
    _box(mb, -w / 2, w / 2, -d / 2, d / 2, h - 0.025, h, "plastic_white", "")
    _box(mb, -w / 2 + 0.01, w / 2 - 0.01, -d / 2 + 0.01, d / 2 - 0.01, h - 0.07, h - 0.025, "plastic_white", "tb")
    for sx in (-1, 1):
        for sy in (-1, 1):
            _tube(mb, (sx * (w / 2 - 0.07), sy * (d / 2 - 0.07), h - 0.03), (sx * (w / 2 - 0.035), sy * (d / 2 - 0.035), 0.0),
                  (0.022, 0.022), "plastic_white")
    return mb


def plastic_chair(s, v, rng):
    """The white monobloc chair: a dished seat, splayed legs, arms running from the front legs to the back,
    and a bowed back of two bands (both sides drawn)."""
    w, d, h = s
    mat = "plastic_white"
    zs = 0.44
    mb = MeshBuilder()
    _pad(mb, -0.225, 0.225, -0.21, 0.24, zs - 0.035, zs, mat, 0.02)
    for sx in (-1, 1):
        _tube(mb, (sx * 0.255, -0.25, 0.0), (sx * 0.215, -0.19, zs - 0.02), (0.015, 0.02), mat)
        _tube(mb, (sx * 0.255, 0.25, 0.0), (sx * 0.232, 0.19, 0.62), (0.015, 0.02), mat)
        _tube(mb, (sx * 0.232, 0.19, 0.62), (sx * 0.24, -0.21, 0.66), (0.015, 0.018), mat)
    cols = np.linspace(-0.24, 0.24, 6)
    for z0, z1 in ((zs + 0.03, 0.60), (0.64, h)):
        tris = []
        for xa, xb in zip(cols[:-1], cols[1:]):
            q = [(x, -0.21 - 0.03 * (1 - (x / 0.24) ** 2) - 0.02 * (z - zs) / (h - zs), z)
                 for x, z in ((xa, z0), (xb, z0), (xb, z1), (xa, z1))]
            tris += [_oriented([q[0], q[1], q[2]], (0, 1, 0)), _oriented([q[0], q[2], q[3]], (0, 1, 0))]
        add_sheet(mb, tris, mat, 0.01)
    return mb


def stool(s, v, rng):
    """A beech stool: a square seat on four legs."""
    w, d, h = s
    mb = MeshBuilder()
    _box(mb, -w / 2, w / 2, -d / 2, d / 2, h - 0.03, h, "wood_beech", "")
    for x in (-w / 2 + 0.05, w / 2 - 0.05):
        for y in (-d / 2 + 0.05, d / 2 - 0.05):
            _leg(mb, x, y, 0.0, h - 0.03, 0.02, "wood_beech")
    return mb


# --- the kitchen --------------------------------------------------------------------------------------

def _run(mb: MeshBuilder, w: float, d: float, mat: str, handles=True) -> float:
    """Base cupboards: the carcass (its front in `worktop`, so the gaps read), two doors, handles; returns
    the depth of the door faces."""
    yf = d - 0.04
    _box(mb, -w / 2, w / 2, 0.0, yf, 0.0, 0.86, mat, "bktf")
    _front(mb, -w / 2, w / 2, 0.0, 0.86, yf, "worktop")
    for x0, x1 in ((-w / 2 + 0.005, -0.005), (0.005, w / 2 - 0.005)):
        _front(mb, x0, x1, 0.11, 0.84, yf + 0.018, mat)
        if handles:
            _tube(mb, (x0 + 0.08, yf + 0.03, 0.78), (x1 - 0.08, yf + 0.03, 0.78), (0.006, 0.006), "chrome")
    return yf + 0.018


def kitchen_run(s, v, rng):
    """The run of base cupboards under a worktop with its front overhang (stretch: the doors widen)."""
    w, d, h = s
    mb = MeshBuilder()
    _run(mb, w, d, RUN[v])
    _box(mb, -w / 2, w / 2, 0.0, d, 0.86, h, "worktop", "bk")
    return mb


def _tap(mb: MeshBuilder, x: float, y: float, z: float, reach: float, rise: float) -> None:
    """A chrome mixer: a riser and a spout reaching forward (16 triangles)."""
    _tube(mb, (x, y, z), (x, y, z + rise), (0.012, 0.012), "chrome", cap=False)
    _tube(mb, (x, y, z + rise), (x, y + reach, z + rise - 0.02), (0.009, 0.009), "chrome")


def kitchen_sink(s, v, rng):
    """A run unit with its steel sink: a bowl let into the worktop beside a drainer, a chrome mixer tap."""
    w, d, _h = s
    h = TABLE["kitchen_sink"][4]["top"]   # the worktop; the tap rises over it
    mb = MeshBuilder()
    _run(mb, w, d, RUN[v])
    steel = (-0.42, 0.42, 0.08, 0.52)
    bowl = (-0.38, 0.02, 0.12, 0.48)
    _frame(mb, (-w / 2, w / 2, 0.0, d), steel, h, "worktop")
    _box(mb, -w / 2, w / 2, 0.0, d, 0.86, h, "worktop", "bkt")
    _frame(mb, steel, bowl, h + 0.002, "steel")
    _bowl(mb, *bowl, h + 0.002, h - 0.17, 0.02, "steel")
    _pyramid(mb, _ring(-0.18, 0.30, h - 0.166, 0.025, 0.025, 4), (-0.18, 0.30, h - 0.163), "chrome")
    for y in (0.20, 0.30, 0.40):    # the drainer's ribs
        _front(mb, 0.08, 0.38, h + 0.002, h + 0.008, y, "steel")
    _tap(mb, -0.18, 0.05, h, 0.16, _h - h - 0.01)
    return mb


def cooker(s, v, rng):
    """The gas cooker: four black burners under two pairs of pan bars, five knobs, the oven door with its
    dark window and a long handle; white enamel or (`_steel`) steel."""
    w, d, h = s
    body = "steel" if v == "steel" else "enamel_white"
    mb = MeshBuilder()
    zt, yf = h - 0.02, d - 0.05
    _box(mb, -w / 2, w / 2, 0.0, yf, 0.0, zt, body, "bk")
    for x in (-0.14, 0.14):
        for y in (0.17, 0.41):
            r = 0.055 if (x < 0) == (y < 0.3) else 0.042
            _pyramid(mb, _ring(x, y, zt + 0.001, r, r, 6), (x, y, zt + 0.014), "iron_black")
    for y in (0.17, 0.41):
        _tube(mb, (-w / 2 + 0.04, y, zt + 0.016), (w / 2 - 0.04, y, zt + 0.016), (0.005, 0.005), "iron_black")
    for x in (-0.14, 0.14):
        _tube(mb, (x, 0.07, zt + 0.016), (x, yf - 0.05, zt + 0.016), (0.005, 0.005), "iron_black")
    _door(mb, -w / 2 + 0.02, w / 2 - 0.02, 0.10, 0.66, yf, yf + 0.02, body)
    _front(mb, -0.19, 0.19, 0.24, 0.55, yf + 0.021, "iron_black")
    _tube(mb, (-0.22, d - 0.012, 0.62), (0.22, d - 0.012, 0.62), (0.008, 0.008), "steel" if v != "steel" else "iron_black")
    for x in np.linspace(-0.22, 0.22, 5):
        _knob(mb, float(x), yf, 0.76, 0.014, "iron_black", 0.022)
    return mb


def fridge(s, v, rng):
    """The fridge: a white body on a black grille, one door (`_small`) or a freezer over the fridge
    (`_tall`), doors with rounded edges and steel handles."""
    w, d, h = s
    mb = MeshBuilder()
    yb = d - 0.05
    _box(mb, -w / 2, w / 2, 0.0, yb, 0.04, h, "enamel_white", "bkf")
    _front(mb, -w / 2, w / 2, 0.04, h, yb, "plastic_grey")
    _front(mb, -w / 2 + 0.02, w / 2 - 0.02, 0.0, 0.04, yb - 0.01, "iron_black")
    split = [(0.05, h - 0.005)] if v != "tall" else [(0.05, h * 0.70 - 0.008), (h * 0.70 + 0.008, h - 0.005)]
    for z0, z1 in split:
        tmp = MeshBuilder()
        _pad(tmp, -w / 2 + 0.005, w / 2 - 0.005, z0, z1, yb, d - 0.012, "enamel_white", 0.012)
        _moved(mb, tmp, SWAP_YZ)
        zh = z0 + 0.10 if z1 > h - 0.01 and len(split) > 1 else (z1 - 0.25 if len(split) == 1 else z1 - 0.10)
        _tube(mb, (w / 2 - 0.06, d - 0.006, zh - 0.18), (w / 2 - 0.06, d - 0.006, zh), (0.008, 0.006), "steel")
    return mb


def wall_cabinet(s, v, rng):
    """The wall cupboards over the run: a carcass hanging from z 1.45, two doors with handles at their foot."""
    w, d, h = s
    z0 = TABLE["wall_cabinet"][4]["z0"]
    mat = RUN[v]
    mb = MeshBuilder()
    yf = d - 0.02
    _box(mb, -w / 2, w / 2, 0.0, yf, z0, z0 + h, mat, "kf")
    _front(mb, -w / 2, w / 2, z0, z0 + h, yf, "worktop")
    for x0, x1 in ((-w / 2 + 0.005, -0.005), (0.005, w / 2 - 0.005)):
        _front(mb, x0, x1, z0 + 0.01, z0 + h - 0.01, d - 0.012, mat)
        _tube(mb, (x0 + 0.10, d - 0.006, z0 + 0.05), (x1 - 0.10, d - 0.006, z0 + 0.05), (0.006, 0.005), "chrome")
    return mb


def microwave(s, v, rng):
    """The microwave: a white box, a dark door window, a grey panel of controls and two dials."""
    w, d, h = s
    mb = MeshBuilder()
    _box(mb, -w / 2, w / 2, -d / 2, d / 2, 0.0, h, "enamel_white", "b")
    y = d / 2 + 0.001
    _front(mb, -w / 2 + 0.03, w / 2 - 0.15, 0.04, h - 0.04, y, "screen_black")
    _front(mb, w / 2 - 0.12, w / 2 - 0.02, 0.03, h - 0.03, y, "plastic_grey")
    for z in (h * 0.65, h * 0.35):
        _knob(mb, w / 2 - 0.07, y, z, 0.018, "plastic_black", 0.015)
    return mb


def table_formica(s, v, rng):
    """The kitchen table: a white formica top with a chrome edge band on chrome legs."""
    w, d, h = s
    mb = MeshBuilder()
    zt = h - 0.03
    _box(mb, -w / 2, w / 2, -d / 2, d / 2, zt, h, "chrome", "tb")
    _quad(mb, [(-w / 2, -d / 2, h), (w / 2, -d / 2, h), (w / 2, d / 2, h), (-w / 2, d / 2, h)], (0, 0, 1), "formica_white")
    _quad(mb, [(-w / 2, -d / 2, zt), (w / 2, -d / 2, zt), (w / 2, d / 2, zt), (-w / 2, d / 2, zt)], (0, 0, -1), "formica_white")
    for x in (-w / 2 + 0.05, w / 2 - 0.05):
        for y in (-d / 2 + 0.05, d / 2 - 0.05):
            _leg(mb, x, y, 0.0, zt, 0.016, "chrome")
    return mb


# --- bedrooms -----------------------------------------------------------------------------------------

def _bed(w: float, d: float, h: float, wood: str, cover: str, pillows: int, foot: float) -> MeshBuilder:
    """A bed with its head on the wall: a head board under an oval crest, a foot board, side rails, the
    mattress, a cover hanging over its sides with the sheet turned down over it, pillows at the head."""
    mb = MeshBuilder()
    _box(mb, -w / 2, w / 2, 0.0, 0.05, 0.0, h - 0.15, wood, "bk")
    _crest(mb, w / 2 - 0.08, 0.16, h - 0.16, 0.0, 0.05, wood, 6)    # its foot sunk in the board: no face on its top
    _box(mb, -w / 2, w / 2, d - 0.04, d, 0.0, foot, wood, "b")
    _box(mb, -w / 2 + 0.02, w / 2 - 0.02, 0.05, d - 0.04, 0.16, 0.30, wood, "bkft")
    _pad(mb, -w / 2 + 0.04, w / 2 - 0.04, 0.05, d - 0.045, 0.30, 0.50, "cotton_white", 0.04, "kf")
    _box(mb, -w / 2 + 0.008, w / 2 - 0.008, 0.62, d - 0.044, 0.22, 0.515, cover, "bk")
    _box(mb, -w / 2 + 0.002, w / 2 - 0.002, 0.55, 0.72, 0.515, 0.532, "cotton_white", "b")
    pw = (w - 0.12 - 0.04 * (pillows - 1)) / pillows
    for k in range(pillows):
        x0 = -w / 2 + 0.06 + k * (pw + 0.04)
        _pad(mb, x0, x0 + pw, 0.08, 0.50, 0.50, 0.63, "cotton_white", 0.05)
    return mb


def bed_double(s, v, rng):
    """The couple's bed (140 or 160 wide): walnut, two pillows, a mink or white cover."""
    w, d, h = s
    return _bed(w, d, h, "wood_walnut", COVER[v.split("_")[1]], 2, 0.50)


def bed_single(s, v, rng):
    """A single bed: walnut with a mink cover, or beech with a blue or pink cover."""
    w, d, h = s
    return _bed(w, d, h, "wood_walnut" if v == "mink" else "wood_beech", COVER[v], 1, 0.55)


def nightstand(s, v, rng):
    """The nightstand: two drawers with brass knobs on four short legs."""
    w, d, h = s
    mb = MeshBuilder()
    for x in (-w / 2 + 0.03, w / 2 - 0.03):
        for y in (0.03, d - 0.05):
            _leg(mb, x, y, 0.0, 0.10, 0.016, "wood_walnut")
    _box(mb, -w / 2, w / 2, 0.0, d - 0.02, 0.10, h, "wood_walnut", "bk")
    for z0, z1 in ((0.13, 0.30), (0.32, h - 0.03)):
        _door(mb, -w / 2 + 0.02, w / 2 - 0.02, z0, z1, d - 0.02, d - 0.004, "wood_walnut")
        _knob(mb, 0.0, d - 0.004, (z0 + z1) / 2, 0.012, "brass")
    return mb


def wardrobe(s, v, rng):
    """The wardrobe: a plinth, a carcass under a cornice, two to four doors with long handles; `_mirror`
    (colonial) has a mirror door in the middle and an oval crest."""
    w, d, h = s
    wood = "wood_beech" if v == "2" else "wood_walnut"
    doors = {"2": 2, "3": 3, "4": 4, "mirror": 3}[v]
    ztop = h - (0.16 if v == "mirror" else 0.0)
    mb = MeshBuilder()
    yf = d - 0.03
    _box(mb, -w / 2 + 0.03, w / 2 - 0.03, 0.0, yf - 0.02, 0.0, 0.08, wood, "bkt")
    _box(mb, -w / 2 + 0.01, w / 2 - 0.01, 0.0, yf, 0.08, ztop - 0.07, wood, "bkt")
    _box(mb, -w / 2, w / 2, 0.0, d, ztop - 0.07, ztop, wood, "k")
    edges = np.linspace(-w / 2 + 0.01, w / 2 - 0.01, doors + 1)
    for k, (x0, x1) in enumerate(zip(edges[:-1], edges[1:])):
        _door(mb, x0 + 0.004, x1 - 0.004, 0.10, ztop - 0.09, yf, yf + 0.018, wood)
        if v == "mirror" and k == 1:
            _front(mb, x0 + 0.07, x1 - 0.07, 0.30, ztop - 0.30, yf + 0.0195, "mirror")
        hx = x1 - 0.05 if k < doors / 2 else x0 + 0.05
        _tube(mb, (hx, d - 0.006, 1.00), (hx, d - 0.006, 1.22), (0.007, 0.006), "brass")
    if v == "mirror":
        _crest(mb, w * 0.28, 0.17, ztop - 0.01, 0.06, 0.09, wood, 4)
    return mb


def coiffeuse(s, v, rng):
    """The dressing table of the wedding set: a chest of three drawers on short legs, a mirror in a
    frame with an oval top, two little shelves at its sides."""
    w, d, h = s
    mb = MeshBuilder()
    zt = 0.76
    for x in (-w / 2 + 0.04, w / 2 - 0.04):
        for y in (0.04, d - 0.06):
            _leg(mb, x, y, 0.0, 0.08, 0.018, "wood_walnut")
    _box(mb, -w / 2 + 0.01, w / 2 - 0.01, 0.0, d - 0.02, 0.08, zt - 0.03, "wood_walnut", "bkt")
    _box(mb, -w / 2, w / 2, 0.0, d, zt - 0.03, zt, "wood_walnut", "k")
    edges = np.linspace(-w / 2 + 0.03, w / 2 - 0.03, 4)
    for x0, x1 in zip(edges[:-1], edges[1:]):
        _door(mb, x0 + 0.006, x1 - 0.006, 0.12, zt - 0.06, d - 0.02, d - 0.004, "wood_walnut")
        _knob(mb, (x0 + x1) / 2, d - 0.004, (0.12 + zt - 0.06) / 2, 0.012, "brass")
    a, b, spring = 0.40, 0.28, h - 0.28
    _crest(mb, a, b, zt - 0.01, 0.02, 0.05, "wood_walnut", 6, base=spring - zt + 0.01)
    inner = [((a - 0.05) * math.cos(t), spring + (b - 0.05) * math.sin(t)) for t in np.linspace(0, math.pi, 7)]
    inner += [(-(a - 0.05), zt + 0.05), (a - 0.05, zt + 0.05)]
    tris = [[(x, 0.052, z) for x, z in t] for t in triangulate(Polygon(inner))]
    add_triangles(mb, [_oriented(t, (0, 1, 0)) for t in tris], "mirror")
    for sx in (-1, 1):
        x0, x1 = sorted((sx * (a + 0.02), sx * (w / 2 - 0.02)))
        _box(mb, x0, x1, 0.02, 0.24, zt, zt + 0.30, "wood_walnut", "bk")
    return mb


def bunk_bed(s, v, rng):
    """The bunk bed of two school children: four posts, two decks of rails each with a mattress, a mink
    cover and a pillow, the upper guard rail and a ladder at the side; iron or wood."""
    w, d, h = s
    iron = v == "iron"
    mat = "iron_black" if iron else "wood_beech"
    r = 0.02 if iron else 0.03
    hx, y0, y1 = w / 2 - r, r, d - r
    mb = MeshBuilder()
    for x in (-hx, hx):
        for y in (y0, y1):
            _tube(mb, (x, y, 0.0), (x, y, h - 0.005), (r, r), mat, cap=True)
    for zd in (0.22, 1.02):
        for x in (-hx, hx):
            _tube(mb, (x, y0, zd), (x, y1, zd), (r * 0.8, r), mat)
        for y in (y0, y1):
            _tube(mb, (-hx, y, zd + 0.10), (hx, y, zd + 0.10), (r * 0.8, r * 0.8), mat)
        _pad(mb, -hx + 0.01, hx - 0.01, y0 + 0.02, y1 - 0.02, zd + 0.02, zd + 0.16, "cotton_white", 0.03)
        _box(mb, -hx + 0.004, hx - 0.004, 0.60, y1 - 0.015, zd + 0.09, zd + 0.175, "mink", "bk")
        _pad(mb, -hx + 0.08, hx - 0.08, y0 + 0.05, 0.42, zd + 0.16, zd + 0.27, "cotton_white", 0.04)
    _tube(mb, (hx, y0, 1.36), (hx, d * 0.62, 1.36), (r * 0.8, r * 0.8), mat)
    ya, yb = d - 0.42, d - 0.12
    for y in (ya, yb):
        _tube(mb, (hx + 0.005, y, 0.0), (hx + 0.005, y, 1.36), (0.012, 0.016), mat)
    for z in (0.47, 0.72, 1.24):
        _tube(mb, (hx + 0.005, ya, z), (hx + 0.005, yb, z), (0.010, 0.010), mat)
    return mb


def cot(s, v, rng):
    """The baby's cot: four posts, a head and a foot board, top rails and bars along both long sides, a
    mattress."""
    w, d, h = s
    mat = "wood_beech"
    hx, y0, y1 = w / 2 - 0.02, 0.02, d - 0.02
    mb = MeshBuilder()
    for x in (-hx, hx):
        for y in (y0, y1):
            _tube(mb, (x, y, 0.0), (x, y, h), (0.02, 0.02), mat)
    for y in (y0, y1):
        _box(mb, -hx, hx, y - 0.01, y + 0.01, 0.20, h - 0.10, mat, "b")
    for x in (-hx, hx):
        _tube(mb, (x, y0, h - 0.03), (x, y1, h - 0.03), (0.015, 0.02), mat)
        _tube(mb, (x, y0, 0.26), (x, y1, 0.26), (0.015, 0.02), mat)
        for y in np.linspace(y0, y1, 8)[1:-1]:
            _leg(mb, x, float(y), 0.27, h - 0.04, 0.009, mat)
    _pad(mb, -hx + 0.02, hx - 0.02, y0 + 0.02, y1 - 0.02, 0.28, 0.38, "cotton_white", 0.03)
    return mb


def desk(s, v, rng):
    """The school desk: a top over a pedestal of two drawers at its right, two legs and a modesty panel
    at its left."""
    w, d, h = s
    mb = MeshBuilder()
    zt = h - 0.03
    _box(mb, -w / 2, w / 2, 0.0, d, zt, h, "wood_beech", "k")
    px = w / 2 - 0.42
    _box(mb, px, w / 2 - 0.02, 0.02, d - 0.03, 0.0, zt, "wood_beech", "bkt")
    for z0, z1 in ((0.05, 0.38), (0.40, zt - 0.03)):
        _door(mb, px + 0.02, w / 2 - 0.04, z0, z1, d - 0.03, d - 0.012, "wood_beech")
        _front(mb, px + 0.14, w / 2 - 0.16, z1 - 0.06, z1 - 0.045, d - 0.011, "chrome")
    for y in (0.05, d - 0.06):
        _leg(mb, -w / 2 + 0.04, y, 0.0, zt, 0.02, "wood_beech")
    _front(mb, -w / 2 + 0.06, px, 0.35, zt, 0.05, "wood_beech")
    return mb


def bookcase(s, v, rng):
    """The bookcase: two sides, a top, five shelves, a back; rows of books on every shelf (`_full`, the
    reader's) or on three, part filled (`_half`)."""
    w, d, h = s
    wood = "wood_walnut"
    t = 0.02
    mb = MeshBuilder()
    _box(mb, -w / 2, -w / 2 + t, 0.0, d, 0.0, h, wood, "bk")
    _box(mb, w / 2 - t, w / 2, 0.0, d, 0.0, h, wood, "bk")
    _box(mb, -w / 2 + t, w / 2 - t, 0.0, d, h - t, h, wood, "bklr")
    _front(mb, -w / 2 + t, w / 2 - t, 0.0, h - t, 0.004, wood)
    levels = [0.08, 0.42, 0.76, 1.10, 1.44]
    _box(mb, -w / 2 + t, w / 2 - t, 0.0, d - 0.01, 0.0, levels[0], wood, "bklr")
    for z in levels[1:]:
        _box(mb, -w / 2 + t, w / 2 - t, 0.0, d - 0.01, z - t, z, wood, "bklr")
    full = v == "full"
    for k, z in enumerate(levels):
        if not full and k not in (0, 2, 3):
            continue
        x1 = w / 2 - t - (0.005 if full else 0.12 + 0.10 * (k % 2))
        _row(mb, "spines", -w / 2 + t + (0.0 if full else 0.0), x1, 0.02, d - 0.03, z, side=not full)
    return mb


def piano(s, v, rng):
    """The upright piano of colonial salons: a walnut case under its lid, the cheeks and keybed, white
    keys with the black keys in their twos and threes, the music desk and three brass pedals."""
    w, d, h = s
    wood = "wood_walnut"
    mb = MeshBuilder()
    yc = 0.34
    _box(mb, -w / 2, w / 2, 0.0, yc, 0.0, h - 0.03, wood, "bkt")
    _box(mb, -w / 2, w / 2, 0.0, yc + 0.03, h - 0.03, h, wood, "k")
    for x0, x1 in ((-w / 2, -w / 2 + 0.06), (w / 2 - 0.06, w / 2)):
        _box(mb, x0, x1, yc, d, 0.0, 0.80, wood, "bk")
    kx = w / 2 - 0.06
    _box(mb, -kx, kx, yc, d, 0.62, 0.70, wood, "ktlr")
    _quad(mb, [(-kx, 0.36, 0.705), (kx, 0.36, 0.705), (kx, 0.56, 0.705), (-kx, 0.56, 0.705)], (0, 0, 1), "ceramic_white")
    _front(mb, -kx, kx, 0.68, 0.705, 0.56, "ceramic_white")
    white = 2 * kx / 52
    for k in range(51):
        if k % 7 in (2, 6):
            continue
        x = -kx + (k + 1) * white
        _quad(mb, [(x - white * 0.3, 0.36, 0.717), (x + white * 0.3, 0.36, 0.717), (x + white * 0.3, 0.47, 0.717),
                   (x - white * 0.3, 0.47, 0.717)], (0, 0, 1), "iron_black")
    _front(mb, -kx + 0.10, kx - 0.10, 0.82, 1.08, yc + 0.006, wood)
    for x in (-0.08, 0.0, 0.08):
        _knob(mb, x, yc, 0.06, 0.018, "brass", 0.09)
    return mb


# --- washrooms and the balcony ------------------------------------------------------------------------

def wc_seat(s, v, rng):
    """The modern wc: the cistern on the wall with its button, the pedestal, the oval bowl with its white
    seat."""
    w, d, h = s
    mb = MeshBuilder()
    _box(mb, -w / 2 + 0.01, w / 2 - 0.01, 0.0, 0.17, 0.42, h, "ceramic_white", "k")
    _pyramid(mb, _ring(0.0, 0.09, h + 0.001, 0.03, 0.03, 4, math.pi / 4), (0.0, 0.09, h + 0.008), "chrome")
    _box(mb, -0.12, 0.12, 0.0, 0.22, 0.0, 0.42, "ceramic_white", "bkt")
    at, sc = (0.0, 0.43, 0.0), (1.0, 1.40)
    _lathed(mb, [(0.11, 0.0), (0.13, 0.18), (0.185, 0.36), (0.19, 0.40), (0.15, 0.40), (0.09, 0.30), (0.0, 0.30)],
            "ceramic_white", 8, at=at, scale=sc)
    _lathed(mb, [(0.195, 0.402), (0.195, 0.42), (0.13, 0.42)], "plastic_white", 8, at=at, scale=sc)
    return mb


def basin(s, v, rng):
    """The sdb's pedestal basin: a white pedestal, an oval bowl, a chrome mixer on its back deck."""
    w, d, h = s
    mb = MeshBuilder()
    _lathed(mb, [(0.085, 0.0), (0.065, 0.40), (0.09, 0.66)], "ceramic_white", 8, at=(0.0, 0.14, 0.0), scale=(1.0, 0.8))
    _lathed(mb, [(0.16, 0.66), (0.275, 0.78), (0.275, 0.80), (0.22, 0.80), (0.0, 0.73)], "ceramic_white", 8,
            at=(0.0, 0.225, 0.0), scale=(1.0, 0.8))
    _tap(mb, 0.0, 0.05, 0.80, 0.07, 0.045)
    return mb


def mirror_bath(s, v, rng):
    """The mirror over the basin: a mirror on a chrome-edged backing, held by two clips."""
    w, d, h = s
    z0 = TABLE["mirror_bath"][4]["z0"]
    mb = MeshBuilder()
    _box(mb, -w / 2, w / 2, 0.0, 0.015, z0, z0 + h, "chrome", "kf")
    _front(mb, -w / 2, w / 2, z0, z0 + h, 0.015, "mirror")
    for z in (z0 + 0.02, z0 + h - 0.02):
        _knob(mb, 0.0, 0.015, z, 0.014, "chrome", d - 0.015)
    return mb


def shower(s, v, rng):
    """The shower in a corner: a white tray with its drain, an L of chrome rail with the blue curtain half
    drawn, the riser and head on the back wall."""
    w, d, h = s
    mb = MeshBuilder()
    _box(mb, -w / 2, w / 2, 0.0, d, 0.0, 0.08, "ceramic_white", "bkl")
    _pyramid(mb, _ring(0.0, d / 2, 0.081, 0.03, 0.03, 4), (0.0, d / 2, 0.083), "chrome")
    xr, yr, zr = w / 2 - 0.02, d - 0.02, h - 0.02
    _tube(mb, (-w / 2, yr, zr), (xr, yr, zr), (0.008, 0.008), "chrome")
    _tube(mb, (xr, 0.0, zr), (xr, yr, zr), (0.008, 0.008), "chrome")

    def curtain(points):
        tris = []
        for a, b in zip(points[:-1], points[1:]):
            q = [(*a, 0.14), (*b, 0.14), (*b, zr - 0.03), (*a, zr - 0.03)]
            tris += [[q[0], q[1], q[2]], [q[0], q[2], q[3]]]
        add_sheet(mb, tris, "plastic_blue", 0.004)
    curtain([(x, yr + (0.025 if k % 2 else -0.025)) for k, x in enumerate(np.linspace(xr, -0.05, 7))])
    curtain([(xr + (0.025 if k % 2 else -0.025), y) for k, y in enumerate(np.linspace(0.03, yr - 0.03, 4))])
    _tube(mb, (-0.20, 0.03, 1.0), (-0.20, 0.03, 1.90), (0.009, 0.009), "chrome")
    _tube(mb, (-0.20, 0.03, 1.90), (-0.20, 0.20, 1.92), (0.008, 0.008), "chrome")
    _pyramid(mb, _ring(-0.20, 0.21, 1.90, 0.045, 0.045, 4), (-0.20, 0.21, 1.93), "chrome")
    return mb


def bathtub(s, v, rng):
    """The bathtub along the wall: a white apron, a rim round a rounded inner basin narrowing to its
    floor, the drain and a chrome spout."""
    w, d, h = s
    mb = MeshBuilder()
    _box(mb, -w / 2, w / 2, 0.0, d, 0.0, h, "ceramic_white", "bkt")
    n = 16
    t = (np.arange(n) + 0.5) * 2 * math.pi / n
    c, sn = np.cos(t), np.sin(t)
    sq = lambda v: np.sign(v) * np.abs(v) ** 0.45   # noqa: E731  a rounded rectangle
    rx, ry, cy = w / 2 - 0.08, d / 2 - 0.08, d / 2
    top = np.stack([sq(c) * rx, cy + sq(sn) * ry, np.full(n, h)], axis=1)
    low = np.stack([sq(c) * (rx - 0.10), cy + sq(sn) * (ry - 0.07), np.full(n, 0.10)], axis=1)
    rim = Polygon([(-w / 2, 0.0), (w / 2, 0.0), (w / 2, d), (-w / 2, d)], [top[:, :2]])
    add_triangles(mb, [_oriented([(x, y, h) for x, y in tri], (0, 0, 1)) for tri in triangulate(rim)], "ceramic_white")
    centre = np.array([0.0, cy, h])
    quads = [[top[k], top[(k + 1) % n], low[(k + 1) % n], low[k]] for k in range(n)]
    _faces(mb, [_oriented(q, centre - np.mean(q, axis=0)) for q in quads], "ceramic_white")
    add_triangles(mb, [_oriented([low[0], low[k], low[k + 1]], (0, 0, 1)) for k in range(1, n - 1)], "ceramic_white")
    _pyramid(mb, _ring(-w / 2 + 0.25, cy, 0.102, 0.025, 0.025, 4), (-w / 2 + 0.25, cy, 0.104), "chrome")
    _tube(mb, (-w / 2 + 0.16, 0.0, h - 0.04), (-w / 2 + 0.16, 0.12, h - 0.05), (0.012, 0.012), "chrome")
    return mb


def water_heater(s, v, rng):
    """The water heater: `_gas`, the chauffe-bain with its flame window, two dials, the flue and pipes;
    `_electric`, the white cylinder of a cumulus with its two pipes."""
    w, d, h = s
    z0 = 1.60 if v == "electric" else TABLE["water_heater"][4]["z0"]
    mb = MeshBuilder()
    if v == "electric":
        r = w / 2
        _lathed(mb, [(0.0, z0 + 0.08), (r * 0.84, z0 + 0.10), (r, z0 + 0.16), (r, z0 + h), (0.0, z0 + h)], "enamel_white",
                8, at=(0.0, r, 0.0))
        for x in (-0.07, 0.07):
            _tube(mb, (x, r, z0), (x, r, z0 + 0.10), (0.012, 0.012), "chrome")
        return mb
    zb, zt = z0 + 0.08, z0 + 0.58
    _box(mb, -w / 2, w / 2, 0.0, d, zb, zt, "enamel_white", "k")
    _front(mb, -0.04, 0.04, zb + 0.14, zb + 0.20, d + 0.001, "iron_black")
    for x in (-0.07, 0.07):
        _knob(mb, x, d, zb + 0.06, 0.016, "plastic_black", 0.015)
        _tube(mb, (x, 0.07, z0), (x, 0.07, zb), (0.010, 0.010), "chrome")
    _lathed(mb, [(0.055, zt), (0.055, z0 + h), (0.0, z0 + h)], "aluminium", 6, at=(0.0, d / 2, 0.0))
    return mb


def washing_machine(s, v, rng):
    """The front-loading washing machine: a white box, a grey control strip with a dial and a display, the
    porthole's chrome ring round the drum and its glass."""
    w, d, h = s
    mb = MeshBuilder()
    yf = d - 0.03
    _box(mb, -w / 2, w / 2, 0.0, yf, 0.0, h, "enamel_white", "bk")
    _front(mb, -w / 2 + 0.02, w / 2 - 0.02, h - 0.10, h - 0.02, yf + 0.001, "plastic_grey")
    _knob(mb, w / 2 - 0.10, yf + 0.001, h - 0.06, 0.022, "plastic_black", 0.018)
    _front(mb, -0.05, 0.10, h - 0.08, h - 0.045, yf + 0.002, "screen_black")
    zc, n = 0.40, 10
    outer = _ring(0.0, 0.0, 0.0, 0.18, 0.18, n)
    inner = _ring(0.0, 0.0, 0.0, 0.13, 0.13, n)
    at = lambda p, y: (p[0], y, zc + p[1])   # noqa: E731  ring (x, z) to the front plane
    ring = [[at(outer[k], yf + 0.004), at(outer[(k + 1) % n], yf + 0.004), at(inner[(k + 1) % n], yf + 0.004), at(inner[k], yf + 0.004)]
            for k in range(n)]
    _faces(mb, [_oriented(q, (0, 1, 0)) for q in ring], "chrome")
    drum = [at(p, yf + 0.002) for p in inner]
    add_triangles(mb, [_oriented([(0.0, yf + 0.002, zc), drum[k], drum[(k + 1) % n]], (0, 1, 0)) for k in range(n)], "steel")
    _pyramid(mb, [at(p, yf + 0.004) for p in inner], (0.0, d - 0.002, zc), "glass_inner")
    return mb


def drying_rack(s, v, rng):
    """The clothes airer of balconies and terraces: crossed aluminium legs at each end, six lines, the
    washing draped over some of them (both sides of the cloth drawn)."""
    w, d, h = s
    mb = MeshBuilder()
    xs, zt = w / 2 - 0.008, h - 0.006
    for x in (-xs, xs):
        _tube(mb, (x, -d / 2 + 0.02, 0.0), (x, d / 2 - 0.04, zt), (0.008, 0.008), "aluminium")
        _tube(mb, (x, d / 2 - 0.02, 0.0), (x, -d / 2 + 0.04, zt), (0.008, 0.008), "aluminium")
        _tube(mb, (x, -d / 2 + 0.03, zt), (x, d / 2 - 0.03, zt), (0.006, 0.006), "aluminium")
    lines = np.linspace(-d / 2 + 0.04, d / 2 - 0.04, 6)
    for y in lines:
        _tube(mb, (-xs, float(y), zt), (xs, float(y), zt), (0.003, 0.003), "aluminium")
    cloths = ("cotton_white", "cotton_blue", "velvet_red", "cotton_pink", "fabric_grey")
    x = -xs + 0.06
    for k, mat in enumerate(cloths):
        cw = float(rng.uniform(0.22, 0.38))
        if x + cw > xs - 0.04:
            break
        y = float(lines[int(rng.integers(len(lines)))])
        drop = float(rng.uniform(0.25, 0.45))
        tris = []
        for side in (-1, 1):
            q = [(x, y, zt + 0.004), (x + cw, y, zt + 0.004), (x + cw, y + side * 0.03, zt - drop), (x, y + side * 0.03, zt - drop)]
            tris += [[q[0], q[1], q[2]], [q[0], q[2], q[3]]]
        add_sheet(mb, tris, mat, 0.004)
        x += cw + float(rng.uniform(0.03, 0.10))
    return mb


def shoe_cabinet(s, v, rng):
    """The hall's shoe cabinet: two tilting doors with chrome grips."""
    w, d, h = s
    mb = MeshBuilder()
    _box(mb, -w / 2, w / 2, 0.0, d - 0.02, 0.0, h, "wood_beech", "bk")
    for z0, z1 in ((0.04, h / 2 - 0.005), (h / 2 + 0.005, h - 0.03)):
        _door(mb, -w / 2 + 0.02, w / 2 - 0.02, z0, z1, d - 0.02, d - 0.004, "wood_beech")
        _front(mb, -0.10, 0.10, z1 - 0.05, z1 - 0.035, d - 0.003, "chrome")
    return mb


def coat_hooks(s, v, rng):
    """The hall's coat rail: a board with four hooks, a scarf hanging from one."""
    w, d, h = s
    z0 = TABLE["coat_hooks"][4]["z0"]
    mb = MeshBuilder()
    _box(mb, -w / 2, w / 2, 0.0, 0.025, z0 + 0.15, z0 + h, "wood_walnut", "k")
    xs = np.linspace(-w / 2 + 0.08, w / 2 - 0.08, 4)
    for x in xs:
        _pyramid(mb, _ring(float(x), 0.025, 0.0, 0.012, 0.012, 4, math.pi / 4) * [1, 0, 0] + [0, 0.025, z0 + 0.20],
                 (float(x), d, z0 + 0.215), "chrome")
    x = float(xs[1])
    q = [(x - 0.06, 0.05, z0 + 0.20), (x + 0.06, 0.05, z0 + 0.20), (x + 0.07, 0.055, z0), (x - 0.07, 0.055, z0)]
    add_sheet(mb, [[q[0], q[1], q[2]], [q[0], q[2], q[3]]], "cotton_blue", 0.004)
    return mb


def doormat(s, v, rng):
    """The jute mat outside each flat door (one quad)."""
    w, d, h = s
    mb = MeshBuilder()
    _quad(mb, [(-w / 2, -d / 2, h), (w / 2, -d / 2, h), (w / 2, d / 2, h), (-w / 2, d / 2, h)], (0, 0, 1), "jute")
    return mb


def rug_floral(s, v, rng):
    """The machine-made floral rug: the whole rug one repeat of `rug_floral`."""
    mb = MeshBuilder()
    _rug(mb, s[0], s[1], s[2], "rug_floral", RUG_FLORAL)
    return mb


# --- shops and cafes ----------------------------------------------------------------------------------

def shop_counter(s, v, rng):
    """The counter of the hanout (beech under a worktop, two walnut panels) or of the qahwa (a zellige
    front and a chrome foot rail)."""
    w, d, h = s
    mb = MeshBuilder()
    yf = d - 0.05
    _box(mb, -w / 2, w / 2, 0.0, yf, 0.0, h - 0.04, "wood_beech", "bkt")
    _box(mb, -w / 2, w / 2, 0.0, d, h - 0.04, h, "worktop", "bk")
    _front(mb, -w / 2, w / 2, 0.0, 0.08, yf + 0.001, "worktop")
    if v == "cafe":
        _front(mb, -w / 2, w / 2, 0.14, h - 0.10, yf + 0.001, "zellige")
        _tube(mb, (-w / 2, d - 0.012, 0.16), (w / 2, d - 0.012, 0.16), (0.010, 0.010), "chrome")
    else:
        for x0, x1 in ((-w / 2 + 0.05, -0.025), (0.025, w / 2 - 0.05)):
            _front(mb, x0, x1, 0.16, h - 0.14, yf + 0.001, "wood_walnut")
    return mb


def shop_shelves(s, v, rng):
    """The shelves of a shop: beech sides, five shelves and a top, a row of goods on each shelf (`goods`
    for the grocer, `goods_<trade>` tinted for the souk trades)."""
    w, d, h = s
    goods = "goods" if v == "grocer" else f"goods_{v}"
    t = 0.025
    mb = MeshBuilder()
    _box(mb, -w / 2, -w / 2 + t, 0.0, d, 0.0, h, "wood_beech", "bk")
    _box(mb, w / 2 - t, w / 2, 0.0, d, 0.0, h, "wood_beech", "bk")
    _box(mb, -w / 2 + t, w / 2 - t, 0.0, d, h - t, h, "wood_beech", "bklr")
    levels = [0.10, 0.52, 0.94, 1.36, 1.78]
    _box(mb, -w / 2 + t, w / 2 - t, 0.0, d - 0.01, 0.0, levels[0], "wood_beech", "bklr")
    for z in levels[1:]:
        _box(mb, -w / 2 + t, w / 2 - t, 0.0, d - 0.01, z - t, z, "wood_beech", "bklr")
    for z in levels:
        _row(mb, goods, -w / 2 + t, w / 2 - t, 0.02, d - 0.05, z, side=False)
    return mb


def scale(s, v, rng):
    """The hanout's scale: a white base, a steel pan and the display tower at its back."""
    w, d, h = s
    mb = MeshBuilder()
    _box(mb, -w / 2, w / 2, -d / 2, d / 2, 0.0, 0.07, "enamel_white", "b")
    _box(mb, -w / 2 + 0.03, w / 2 - 0.03, -d / 2 + 0.07, d / 2 - 0.01, 0.07, 0.085, "steel", "b")
    _box(mb, -0.07, 0.07, -d / 2, -d / 2 + 0.05, 0.07, h, "steel", "b")
    _front(mb, -0.055, 0.055, h - 0.09, h - 0.02, -d / 2 + 0.051, "screen_black")
    return mb


def drinks_fridge(s, v, rng):
    """The drinks fridge of shop and qahwa: a white cabinet under a red header, a glass door with a steel
    handle, rows of bottles and cans on four shelves seen through it."""
    w, d, h = s
    mb = MeshBuilder()
    yf, st, zk, zh = d - 0.02, 0.05, 0.14, h - 0.22
    _box(mb, -w / 2, w / 2, 0.0, yf, 0.0, h, "enamel_white", "bkf")
    _front(mb, -w / 2, w / 2, 0.0, zk, yf, "enamel_white")
    _front(mb, -w / 2, w / 2, zh, h, yf, "awning_red")
    for x0, x1 in ((-w / 2, -w / 2 + st), (w / 2 - st, w / 2)):
        _front(mb, x0, x1, zk, zh, yf, "enamel_white")
    xi = w / 2 - st
    _quad(mb, [(-xi, 0.05, zk), (-xi, yf, zk), (-xi, yf, zh), (-xi, 0.05, zh)], (1, 0, 0), "enamel_white")
    _quad(mb, [(xi, 0.05, zk), (xi, yf, zk), (xi, yf, zh), (xi, 0.05, zh)], (-1, 0, 0), "enamel_white")
    _quad(mb, [(-xi, 0.05, zh), (xi, 0.05, zh), (xi, yf, zh), (-xi, yf, zh)], (0, 0, -1), "enamel_white")
    space = (zh - zk) / 4
    for k in range(4):
        z = zk + k * space
        _quad(mb, [(-xi, 0.05, z), (xi, 0.05, z), (xi, yf - 0.02, z), (-xi, yf - 0.02, z)], (0, 0, 1), "steel")
        hh = TEX_H["goods"]
        _uvquad(mb, "goods", [(-xi, 0.10, z), (xi, 0.10, z), (xi, 0.10, z + hh), (-xi, 0.10, z + hh)],
                [(-xi, hh), (xi, hh), (xi, 0.0), (-xi, 0.0)], (0, 1, 0))
    _front(mb, -xi, xi, zk, zh, d - 0.01, "glass_inner")
    _tube(mb, (xi - 0.04, d - 0.004, zk + 0.45), (xi - 0.04, d - 0.004, zk + 0.95), (0.008, 0.006), "steel")
    return mb


def espresso(s, v, rng):
    """The qahwa's espresso machine: a steel body on a black drip tray, two chrome group heads with black
    handles, the steam wand and two buttons."""
    w, d, h = s
    mb = MeshBuilder()
    yb = 0.04
    _box(mb, -w / 2, w / 2, -d / 2, yb, 0.06, h, "steel", "b")
    _box(mb, -w / 2, w / 2, -d / 2, d / 2, 0.0, 0.06, "iron_black", "b")
    for x in (-0.13, 0.13):
        _lathed(mb, [(0.045, 0.30), (0.038, 0.25), (0.0, 0.25)], "chrome", 6, at=(x, yb + 0.045, 0.0))
        _tube(mb, (x, yb + 0.07, 0.24), (x, d / 2 - 0.01, 0.22), (0.012, 0.010), "iron_black")
        _knob(mb, x, yb, 0.37, 0.016, "iron_black", 0.012)
    _tube(mb, (0.26, yb, 0.33), (0.26, yb + 0.10, 0.12), (0.006, 0.006), "steel")
    return mb


def tv_bracket(s, v, rng):
    """The qahwa's football screen on its wall bracket, tilted down toward the tables."""
    w, d, h = s
    z0 = TABLE["tv_bracket"][4]["z0"]
    mb = MeshBuilder()
    zc = z0 + h / 2
    _box(mb, -0.15, 0.15, 0.0, 0.02, zc - 0.08, zc + 0.08, "plastic_black", "k")
    _tube(mb, (0.0, 0.02, zc), (0.0, 0.17, zc), (0.02, 0.02), "plastic_black")
    tmp = MeshBuilder()
    hz = h / 2 - 0.002
    _box(tmp, -w / 2, w / 2, -0.025, 0.025, -hz, hz, "plastic_black", "")
    _front(tmp, -w / 2 + 0.02, w / 2 - 0.02, -hz + 0.02, hz - 0.02, 0.027, "screen_black")
    a = math.radians(10)
    rot = ((1, 0, 0), (0, math.cos(a), math.sin(a)), (0, -math.sin(a), math.cos(a)))
    _moved(mb, tmp, rot, (0.0, 0.21, zc))
    return mb


def chicha(s, v, rng):
    """The water pipe of the qahwa: a green glass base, a brass stem with its ash tray, the clay bowl and
    the hose."""
    w, d, h = s
    mb = MeshBuilder()
    _lathed(mb, [(0.055, 0.0), (0.12, 0.07), (0.11, 0.19), (0.025, 0.30)], "glaze_green", 8)
    _lathed(mb, [(0.018, 0.30), (0.013, 0.66)], "brass", 6)
    _lathed(mb, [(0.09, 0.555), (0.0, 0.565)], "brass", 6)
    _lathed(mb, [(0.015, 0.66), (0.048, 0.75), (0.0, 0.74)], "terracotta", 6)
    _tube(mb, (0.02, 0.0, 0.46), (0.117, 0.03, 0.30), (0.008, 0.008), "leather_brown")
    return mb


def crate_stack(s, v, rng):
    """Three beech crates stacked in the makhzen, each a little askew: three slats a side, a hand hole at the top."""
    w, d, h = s
    mb = MeshBuilder()
    shift = rng.uniform(-0.01, 0.01, 3)
    ch = h / 3
    for k in range(3):
        dx = float(shift[k])
        x0, x1, z0 = -w / 2 + 0.01 + dx, w / 2 - 0.01 + dx, k * ch
        _box(mb, x0, x1, 0.0, d - 0.015, z0, z0 + ch - 0.004, "wood_beech", "bk" if k == 2 else "bkt")
        for f in (0.30, 0.56):         # the gaps between the slats
            _front(mb, x0 + 0.015, x1 - 0.015, z0 + ch * f, z0 + ch * (f + 0.05), d - 0.014, "iron_black")
        _front(mb, -0.07 + dx, 0.07 + dx, z0 + ch * 0.76, z0 + ch * 0.88, d - 0.013, "iron_black")   # the hand hole
    return mb


MAKERS = {"sofa_3": _sofa(3), "sofa_2": _sofa(2), "armchair": _sofa(1), "sedari": sedari, "coffee_table": coffee_table,
          "side_table": side_table, "tv_stand": tv_stand, "tv_flat": tv_flat, "tv_crt": tv_crt, "receiver": receiver,
          "buffet": buffet, "dining_table": dining_table, "dining_chair": dining_chair, "plastic_table": plastic_table,
          "plastic_chair": plastic_chair, "stool": stool, "kitchen_run": kitchen_run, "kitchen_sink": kitchen_sink,
          "cooker": cooker, "fridge": fridge, "wall_cabinet": wall_cabinet, "microwave": microwave,
          "table_formica": table_formica, "bed_double": bed_double, "nightstand": nightstand, "wardrobe": wardrobe,
          "coiffeuse": coiffeuse, "bed_single": bed_single, "bunk_bed": bunk_bed, "cot": cot, "desk": desk,
          "desk_chair": desk_chair, "bookcase": bookcase, "piano": piano, "wc_seat": wc_seat, "basin": basin,
          "mirror_bath": mirror_bath, "shower": shower, "bathtub": bathtub, "water_heater": water_heater,
          "washing_machine": washing_machine, "drying_rack": drying_rack, "shoe_cabinet": shoe_cabinet,
          "coat_hooks": coat_hooks, "doormat": doormat, "rug_floral": rug_floral, "shop_counter": shop_counter,
          "shop_shelves": shop_shelves, "scale": scale, "drinks_fridge": drinks_fridge, "espresso": espresso,
          "tv_bracket": tv_bracket, "chicha": chicha, "crate_stack": crate_stack}


def names() -> list:
    """Every piece name of the modern table (without `home/`), variants spelled out, in table order."""
    return [n for b in TABLE for n in ([f"{b}_{v}" for v in VARIANTS[b]] if b in VARIANTS else [b])]


def pieces(seed: int, cfg: dict) -> dict:
    """{name: (MeshBuilder, category, anchor, spec dict)} of every modern piece; `cfg` is the style's
    `[interiors.furnish]` (its `sizes` override `SIZES`)."""
    over = (cfg or {}).get("sizes", {})
    out = {}
    for base, (cat, anchor, _size, tris, extra) in TABLE.items():
        for suffix in VARIANTS.get(base, (None,)):
            name = base if suffix is None else f"{base}_{suffix}"
            size = tuple(float(v) for v in over.get(name, over.get(base, SIZES.get(name, SIZES[base]))))
            rng = stream(seed, "piece", f"home/{name}")
            mb = MAKERS[base](size, suffix or "", rng)
            out[name] = (mb, cat, anchor, {"size": size, "tris": tris, **extra, **VARIANT_EXTRA.get(name, {})})
    return out
