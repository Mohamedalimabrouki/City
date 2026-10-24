"""Procedural props: the street-life pieces the generator makes itself.

Every piece is built in its own space, generator axes: x along the wall, y out of the wall toward
the street (the side people see), z up, meters. Ground pieces have their origin at the bottom-center
on the ground. Wall pieces have it on the wall face: at street level for doors, shop fronts and
awnings (an awning carries its own height), at the sill for windows, at the hook for lamps and
anything hanging. Pieces from a kit made elsewhere (kits/<name>/) follow the same convention, so
the two mix freely.
"""
from __future__ import annotations

import math

import numpy as np
from shapely.geometry import Polygon

from ..city.model import Tree

from .builder import (MeshBuilder, add_cone, add_dome, add_octahedron, add_sheet, add_triangles, extrude,
                      regular_polygon)
from .climbers import climber_pieces
from .trees import tree_pieces

DOOR_COLORS = ("door_blue", "door_green", "door_yellow", "door_brown", "door_red")
AWNINGS = ("awning_red", "awning_green", "awning_blue", "awning_yellow")
SPICES = ("spice_red", "spice_orange", "spice_yellow", "spice_brown", "spice_green", "spice_ochre")
RUGS = (("rug_red", "rug_cream", "rug_black"), ("rug_blue", "rug_cream", "rug_red"),
        ("rug_green", "rug_orange", "rug_cream"))
CATS = ("cat_ginger", "cat_white", "cat_black", "cat_grey")
SLAB_TINTS = {"white": "plastic_white", "blue": "door_blue", "green": "door_green", "brown": "door_brown"}
SHOP_GOODS = {   # what fills a shop's shelves, by trade
    "spices": ("spice_red", "spice_orange", "spice_yellow", "spice_brown", "spice_green", "spice_ochre"),
    "perfume": ("glass_dark", "copper", "tile_panel", "spice_yellow"),
    "pots": ("terracotta", "terracotta", "tile_panel", "plastic_white"),
    "copper": ("copper",),
    "chechia": ("chechia_red", "chechia_red", "stud_black"),
    "fruit": ("orange_fruit", "spice_red", "plant_green", "spice_yellow"),
    "cloth": ("rug_red", "rug_blue", "rug_green", "rug_cream", "rug_orange", "cloth_3", "cloth_5"),
}


def _box(mb, x0, x1, y0, y1, z0, z1, mat, top=True):
    extrude(mb, Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)]), z0, z1, mat, mat if top else None)


def _bar(mb, p0, p1, r: float, mat: str) -> None:
    """A thin square bar from p0 to p1 (an awning arm, a pole)."""
    p0, p1 = np.asarray(p0, dtype=float), np.asarray(p1, dtype=float)
    d = (p1 - p0) / max(np.linalg.norm(p1 - p0), 1e-9)
    a = np.cross(d, [0.0, 0.0, 1.0] if abs(d[2]) < 0.9 else [1.0, 0.0, 0.0])
    a = a / np.linalg.norm(a) * r
    b = np.cross(d, a)
    ring = [a + b, -a + b, -a - b, a - b]
    tris = []
    for k in range(4):
        q0, q1 = ring[k], ring[(k + 1) % 4]
        tris += [[p0 + q0, p1 + q0, p1 + q1], [p0 + q0, p1 + q1, p0 + q1]]
    add_triangles(mb, tris, mat)


def _arch_outline(w: float, h: float, segments: int = 8) -> list:
    """Door outline with a round top, as a list of (x, z) points, counter-clockwise from bottom left."""
    r = w / 2
    pts = [(-r, 0.0), (r, 0.0)]
    for k in range(segments + 1):
        a = math.pi * k / segments
        pts.append((r * math.cos(a), h - r + r * math.sin(a)))
    return pts


def _slab(mb, outline, y0, y1, mat):
    """A flat slab whose front outline lies in the x-z plane, from depth y0 to y1 (y1 > y0 is toward the street).

    `outline` is a list of (x, z) points or a shapely Polygon in (x, z), holes allowed.
    """
    poly = outline if isinstance(outline, Polygon) else Polygon(np.asarray(outline))
    tmp = MeshBuilder()
    extrude(tmp, poly, y0, y1, mat, mat)
    for name, (pos, nrm, uv, tris, _n, _col) in tmp._parts.items():
        p = np.concatenate(pos)
        n = np.concatenate(nrm)
        # the prism was built along z; swap so its depth runs along y and its outline stands in x-z
        mb.add(name, p[:, [0, 2, 1]], n[:, [0, 2, 1]], np.concatenate(uv), np.concatenate(tris)[:, ::-1])


def door(color: str, rich: bool = False) -> MeshBuilder:
    """Arched door with black studs in a sandstone frame; rich houses get a carved frame and tile panels."""
    mb = MeshBuilder()
    w, h = 1.25, 2.3
    frame = Polygon(_arch_outline(w + 0.5, h + 0.28)).difference(Polygon(_arch_outline(w, h)))
    _slab(mb, frame, -0.02, 0.12, "stone_frame")
    _slab(mb, _arch_outline(w, h), -0.06, 0.03, color)
    for k in range(6):
        for side in (-1, 1):
            x = side * (0.14 + 0.18 * (k % 3))
            z = 0.35 + 0.35 * k
            if z < h - 0.45:
                _box(mb, x - 0.025, x + 0.025, 0.03, 0.06, z - 0.025, z + 0.025, "stud_black")
    _box(mb, -0.02, 0.02, 0.03, 0.07, 0.2, h - 0.25, "stud_black")
    if rich:
        for side in (-1, 1):
            x = side * (w / 2 + 0.55)
            _box(mb, x - 0.3, x + 0.3, 0.0, 0.03, 0.15, 1.95, "tile_panel")
            _box(mb, x - 0.33, x + 0.33, -0.01, 0.025, 0.1, 2.0, "stone_frame")
    return mb


def window(color: str, style: str = "grille") -> MeshBuilder:
    """Window 0.8 x 1.1 m: blue frame and shutters, or a bulging iron grille (qumriya)."""
    mb = MeshBuilder()
    w, h = 0.8, 1.1
    _box(mb, -w / 2 - 0.1, w / 2 + 0.1, -0.02, 0.06, -0.08, h + 0.08, "stone_frame")
    _box(mb, -w / 2, w / 2, 0.0, 0.07, 0.0, h, "glass_dark")
    if style == "grille":
        for k in range(5):
            x = -w / 2 + w * (k + 0.5) / 5
            _box(mb, x - 0.015, x + 0.015, 0.2, 0.23, 0.0, h, "iron")
        for z in (0.05, h / 2, h - 0.05):
            _box(mb, -w / 2, w / 2, 0.08, 0.23, z - 0.015, z + 0.015, "iron")
    else:
        for side in (-1, 1):
            x0, x1 = sorted((side * w / 2, side * (w / 2 + w / 2 * 0.95)))
            _box(mb, x0, x1, 0.06, 0.1, 0.0, h, color)
    _box(mb, -w / 2 - 0.14, w / 2 + 0.14, 0.0, 0.16, -0.12, -0.04, "stone_frame")
    return mb


def _faces(mb, quads, mat: str) -> None:
    """Flat one-sided quads (Q, 4, 3), counter-clockwise seen from their front: 4 corners, 2 triangles each.

    The pieces of every home's openings (prompt 20.1) are built from these instead of boxes: a box
    costs five faces where one shows, and a slab block repeats these pieces on every tile.
    """
    q = np.asarray(quads, dtype=np.float64).reshape(-1, 4, 3)
    if not len(q):
        return
    n = np.cross(q[:, 1] - q[:, 0], q[:, 3] - q[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]
    pos = q.reshape(-1, 3)
    base = np.arange(len(q))[:, None] * 4
    tris = np.concatenate([base + [0, 1, 2], base + [0, 2, 3]])
    level = np.repeat(np.abs(n[:, 2]) >= np.abs(n[:, :2]).max(axis=1), 4)   # sills, slabs, canopies
    uv = np.where(level[:, None], np.stack([pos[:, 0], -pos[:, 1]], axis=1),   # planar meters, as on roofs
                  np.stack([pos[:, 0] + pos[:, 1], -pos[:, 2]], axis=1))
    mb.add(mat, pos, np.repeat(n, 4, axis=0), uv, tris)


def _front(x0, x1, z0, z1, y, back: bool = False) -> list:
    """A face in the wall plane at depth y, seen from the street (or from the wall, with `back`)."""
    q = [(x1, y, z0), (x0, y, z0), (x0, y, z1), (x1, y, z1)]
    return q[::-1] if back else q


def _flat(x0, x1, y0, y1, z, down: bool = False) -> list:
    """A level face at height z, seen from above (or from below, with `down`)."""
    q = [(x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)]
    return q[::-1] if down else q


def _side(x, y0, y1, z0, z1, left: bool = False) -> list:
    """A face across the wall at x, seen from +x (or from -x, with `left`)."""
    q = [(x, y0, z0), (x, y1, z0), (x, y1, z1), (x, y0, z1)]
    return q[::-1] if left else q


def _slats(x0, x1, z0, z1, y, count: int, depth: float = 0.025) -> list:
    """Louver slats of a shutter leaf: strips tilted down and out, seen from the street and above."""
    step = (z1 - z0) / count
    out = []
    for k in range(count):
        top = z1 - step * k - 0.01
        out.append([(x1, y + depth, top - step * 0.8), (x0, y + depth, top - step * 0.8), (x0, y, top), (x1, y, top)])
    return out


def _opening(x0, x1, z0, z1, y, rim: float) -> list:
    """A frame around an opening: two jambs and a head, their faces at depth y, with reveals and soffit."""
    return [_front(x0 - rim, x0, z0, z1 + rim, y), _front(x1, x1 + rim, z0, z1 + rim, y), _front(x0, x1, z1, z1 + rim, y),
            _side(x0, 0.0, y, z0, z1), _side(x1, 0.0, y, z0, z1, left=True), _flat(x0, x1, 0.0, y, z1, down=True)]


def door_narrow(color: str) -> MeshBuilder:
    """A narrow plank house door (0.95 x 2.2 m) with a barred fanlight in a stone frame.

    The door to the homes upstairs beside a shop or a cafe, and the door of a house squeezed into
    a gap between neighbours: it stands less than 0.1 m proud of the wall.
    """
    mb = MeshBuilder()
    w, h, fan = 0.95, 2.2, 0.38
    top = h + 0.06 + fan
    _faces(mb, _opening(-w / 2, w / 2, 0.0, top, 0.08, 0.12) + [_front(-w / 2, w / 2, h, h + 0.06, 0.06)], "stone_frame")
    _faces(mb, [_front(-w / 2, w / 2, 0.0, h, 0.04)], color)
    _faces(mb, [_front(-w / 2, w / 2, h + 0.06, top, 0.015)], "glass_dark")   # off the wall face: no flicker
    bars = [_front(-w / 2 + w * k / 5 - 0.012, -w / 2 + w * k / 5 + 0.012, h + 0.06, top, 0.03) for k in range(1, 5)]
    studs = [_front(sd * 0.3 - 0.022, sd * 0.3 + 0.022, 0.45 + 0.42 * k - 0.022, 0.45 + 0.42 * k + 0.022, 0.05)
             for k in range(4) for sd in (-1, 1)]
    _faces(mb, bars + studs + [_front(0.3, 0.34, 1.0, 1.12, 0.06)], "iron")
    return mb


def window_slab(color: str, shut: bool = False) -> MeshBuilder:
    """A plain apartment window (1.2 x 1.35 m) of a modern block: concrete sill and lintel, white
    frame, and louvered shutters (persiennes) folded back against the wall, or closed against the sun."""
    mb = MeshBuilder()
    w, h, f = 1.2, 1.35, 0.05
    sill = [_flat(-w / 2 - 0.1, w / 2 + 0.1, 0.0, 0.15, 0.0), _front(-w / 2 - 0.1, w / 2 + 0.1, -0.08, 0.0, 0.15),
            _flat(-w / 2 - 0.1, w / 2 + 0.1, 0.0, 0.15, -0.08, down=True)]
    _faces(mb, sill + [_front(-w / 2 - 0.06, w / 2 + 0.06, h, h + 0.08, 0.04)], "concrete")
    frame = [_front(-w / 2 - f, -w / 2, 0.0, h, 0.05), _front(w / 2, w / 2 + f, 0.0, h, 0.05),
             _front(-w / 2, w / 2, h - f, h, 0.05), _front(-w / 2, w / 2, 0.0, f, 0.05)]
    if shut:
        _faces(mb, frame, "plastic_white")
        leaves = [(-w / 2, -0.01), (0.01, w / 2)]
        _faces(mb, [_front(x0, x1, f, h - f, 0.07) for x0, x1 in leaves], color)
        _faces(mb, [q for x0, x1 in leaves for q in _slats(x0, x1, f, h - f, 0.07, 9)], color)
        return mb
    _faces(mb, frame + [_front(-0.025, 0.025, f, h - f, 0.05)], "plastic_white")
    _faces(mb, [_front(-w / 2, w / 2, 0.0, h, 0.03)], "glass_dark")
    leaves = [(w / 2 + 0.07, w + 0.07), (-w - 0.07, -w / 2 - 0.07)]
    _faces(mb, [_front(x0, x1, 0.0, h, 0.02) for x0, x1 in leaves], color)
    _faces(mb, [q for x0, x1 in leaves for q in _slats(x0, x1, 0.0, h, 0.02, 7)], color)
    return mb


def lit_pane(x0: float, x1: float, z0: float, z1: float, y: float) -> MeshBuilder:
    """One `glass_lit` quad facing the street at depth y: the light behind a kit window's glass
    (prompt 21). Kit windows are single vertex-colored meshes, so their glass cannot be lit alone."""
    mb = MeshBuilder()
    _faces(mb, [_front(x0, x1, z0, z1, y)], "glass_lit")
    return mb


def window_stair() -> MeshBuilder:
    """A small barred window lighting a staircase (0.7 x 0.9 m), set half a floor off the flats' windows."""
    mb = MeshBuilder()
    w, h = 0.7, 0.9
    _faces(mb, [_flat(-w / 2 - 0.08, w / 2 + 0.08, 0.0, 0.12, 0.0), _front(-w / 2 - 0.08, w / 2 + 0.08, -0.07, 0.0, 0.12),
                _front(-w / 2 - 0.06, w / 2 + 0.06, h, h + 0.07, 0.04)], "concrete")
    _faces(mb, [_front(-w / 2, w / 2, 0.0, h, 0.03)], "glass_dark")
    bars = [_front(-w / 2 + w * (k + 0.5) / 4 - 0.012, -w / 2 + w * (k + 0.5) / 4 + 0.012, 0.0, h, 0.06) for k in range(4)]
    _faces(mb, bars + [_front(-w / 2, w / 2, h / 2 - 0.012, h / 2 + 0.012, 0.065)], "iron")
    return mb


def balcony_slab() -> MeshBuilder:
    """A concrete balcony of a modern block with a plain iron rail and a glazed door behind it.

    The origin is on the wall face at the floor of its storey: the slab top is level with it.
    """
    mb = MeshBuilder()
    w, d, rail, up = 2.6, 1.1, 1.0, 0.12
    x0, x1 = -w / 2, w / 2
    gw, gh = 1.0, 2.15                                                           # the door onto the balcony
    _faces(mb, [_front(-gw / 2, gw / 2, 0.0, gh, 0.03)], "glass_dark")
    _faces(mb, [_front(-gw / 2 - 0.06, -gw / 2, 0.0, gh + 0.06, 0.05), _front(gw / 2, gw / 2 + 0.06, 0.0, gh + 0.06, 0.05),
                _front(-gw / 2, gw / 2, gh, gh + 0.06, 0.05), _front(-0.025, 0.025, 0.0, gh, 0.05)], "plastic_white")
    t = 0.08
    slab = [_flat(x0, x1, 0.0, d, 0.0), _flat(x0, x1, 0.0, d, -0.16, down=True), _front(x0, x1, -0.16, up, d),
            _side(x1, 0.0, d, -0.16, up), _side(x0, 0.0, d, -0.16, up, left=True),
            _flat(x0, x1, d - t, d, up), _front(x0 + t, x1 - t, 0.0, up, d - t, back=True),          # upstand
            _flat(x0, x0 + t, 0.0, d - t, up), _side(x0 + t, 0.0, d - t, 0.0, up),
            _flat(x1 - t, x1, 0.0, d - t, up), _side(x1 - t, 0.0, d - t, 0.0, up, left=True)]
    _faces(mb, slab, "concrete")
    iron = []
    for z0, z1 in ((rail - 0.05, rail), (up + 0.08, up + 0.11)):                # hand rail and foot rail
        iron += [_front(x0, x1, z0, z1, d - 0.02), _front(x0, x1, z0, z1, d - 0.06, back=True),
                 _side(x1 - 0.02, 0.0, d - 0.02, z0, z1), _side(x1 - 0.06, 0.0, d - 0.06, z0, z1, left=True),
                 _side(x0 + 0.02, 0.0, d - 0.02, z0, z1, left=True), _side(x0 + 0.06, 0.0, d - 0.06, z0, z1)]
    iron += [_flat(x0 + 0.02, x1 - 0.02, d - 0.06, d - 0.02, rail), _flat(x0 + 0.02, x0 + 0.06, 0.0, d - 0.06, rail),
             _flat(x1 - 0.06, x1 - 0.02, 0.0, d - 0.06, rail)]
    for x in np.arange(x0 + 0.1, x1 - 0.05, 0.2):                               # balusters, both faces
        iron += [_front(x - 0.01, x + 0.01, up, rail - 0.05, d - 0.035), _front(x - 0.01, x + 0.01, up, rail - 0.05, d - 0.045, back=True)]
    for y in np.arange(0.15, d - 0.1, 0.2):
        for x, sgn in ((x1 - 0.04, False), (x0 + 0.04, True)):
            iron += [_side(x + 0.005, y - 0.01, y + 0.01, up, rail - 0.05, left=sgn),
                     _side(x - 0.005, y - 0.01, y + 0.01, up, rail - 0.05, left=not sgn)]
    _faces(mb, iron, "iron")
    return mb


def stair_door() -> MeshBuilder:
    """The glazed entrance to the staircase of an apartment block, under a small concrete canopy
    with a light (origin at the threshold)."""
    mb = MeshBuilder()
    w, h, fan, rim = 1.5, 2.3, 0.45, 0.16
    top = h + fan
    _faces(mb, _opening(-w / 2, w / 2, 0.0, top, 0.07, rim), "concrete")
    _faces(mb, [_front(-w / 2, w / 2, 0.0, top, 0.01)], "glass_dark")
    stiles = [_front(-w / 2, -w / 2 + 0.07, 0.0, top, 0.04), _front(w / 2 - 0.07, w / 2, 0.0, top, 0.04),
              _front(-0.035, 0.035, 0.0, h, 0.04)]
    rails = [_front(-w / 2 + 0.07, w / 2 - 0.07, z0, z1, 0.045) for z0, z1 in
             ((0.0, 0.25), (0.95, 1.02), (h - 0.03, h + 0.04), (top - 0.06, top))]
    _faces(mb, stiles + rails, "metal")
    _faces(mb, [_front(-0.2, -0.17, 0.9, 1.3, 0.08), _front(0.17, 0.2, 0.9, 1.3, 0.08)], "iron")   # pull handles
    cz, x = top + rim + 0.12, 1.15
    _faces(mb, [_flat(-x, x, 0.0, 1.05, cz + 0.14), _flat(-x, x, 0.0, 1.05, cz, down=True), _front(-x, x, cz, cz + 0.14, 1.05),
                _side(x, 0.0, 1.05, cz, cz + 0.14), _side(-x, 0.0, 1.05, cz, cz + 0.14, left=True)], "concrete")
    _faces(mb, [_flat(-0.12, 0.12, 0.18, 0.3, cz - 0.07, down=True), _front(-0.12, 0.12, cz - 0.07, cz, 0.3)], "lantern_glow")
    return mb


def lantern() -> MeshBuilder:
    """Wall lantern hanging from an iron bracket (origin at the hook), with a warm glow."""
    mb = MeshBuilder()
    _box(mb, -0.03, 0.03, 0.0, 0.45, -0.1, -0.06, "iron")
    _box(mb, -0.11, 0.11, 0.33, 0.55, -0.47, -0.16, "lantern_glow")
    add_cone(mb, 0.0, 0.44, -0.16, 0.17, 0.16, "iron", segments=4)
    return mb


def pot_plant(rng) -> MeshBuilder:
    mb = MeshBuilder()
    r = float(rng.uniform(0.16, 0.24))
    extrude(mb, regular_polygon(0, 0, r, 8), 0.0, r * 1.6, "terracotta", "soil")
    add_octahedron(mb, 0, 0, r * 1.6 + r * 0.9, r * 1.4, r * 1.1, "plant_green", twist=float(rng.uniform(0, 1)))
    return mb


def doukkana() -> MeshBuilder:
    """The stone bench built against the wall beside a traditional door."""
    mb = MeshBuilder()
    _box(mb, -0.8, 0.8, 0.0, 0.45, 0.0, 0.45, "stone_frame")
    return mb


def tank(color: str) -> MeshBuilder:
    """Rooftop water tank on four legs (white or the black plastic kind)."""
    mb = MeshBuilder()
    for sx in (-1, 1):
        for sy in (-1, 1):
            _box(mb, sx * 0.35 - 0.04, sx * 0.35 + 0.04, sy * 0.35 - 0.04, sy * 0.35 + 0.04, 0.0, 0.45, "iron")
    extrude(mb, regular_polygon(0, 0, 0.62, 10), 0.45, 1.55, color, color)
    add_dome(mb, 0, 0, 1.55, 0.62, color, height=0.12, segments=10, rings=2)
    return mb


def tank_stand() -> MeshBuilder:
    """A building's water tank on a steel stand, for the roofs of the housing estates (prompt 23): four
    legs, a grating and a big white tank. 1.8 m square, about 2.9 m high."""
    mb = MeshBuilder()
    for sx in (-1, 1):
        for sy in (-1, 1):
            _box(mb, sx * 0.8 - 0.05, sx * 0.8 + 0.05, sy * 0.8 - 0.05, sy * 0.8 + 0.05, 0.0, 1.1, "iron", top=False)
    _box(mb, -0.9, 0.9, -0.9, 0.9, 1.1, 1.18, "iron")
    extrude(mb, regular_polygon(0, 0, 0.82, 10), 1.18, 2.75, "tank_white", "tank_white")
    add_dome(mb, 0, 0, 2.75, 0.82, "tank_white", height=0.15, segments=10, rings=2)
    return mb


def hedge(cfg: dict) -> MeshBuilder:
    """A low clipped box hedge for villa lot edges (prompt 24): `nominal` m long along x, centered on
    its anchor, `thick` wide with chamfered top edges, `height` tall and `sink` below the ground.
    Placements stretch it along x to fill a run. 9 one-sided faces, 18 triangles, no bottom."""
    mb = MeshBuilder()
    x0, x1 = -float(cfg["nominal"]) / 2, float(cfg["nominal"]) / 2
    w, h, s = float(cfg["thick"]) / 2, float(cfg["height"]), float(cfg["sink"])
    c = 0.3 * w
    prof = [(-w, -s), (w, -s), (w, h - c), (w - c, h), (-w + c, h), (-w, h - c)]   # (y, z), counter-clockwise
    quads, normals = [], []
    for i in range(1, 6):
        (ya, za), (yb, zb) = prof[i], prof[(i + 1) % 6]
        quads.append([(x0, ya, za), (x1, ya, za), (x1, yb, zb), (x0, yb, zb)])
        normals.append((0.0, zb - za, ya - yb))
    for x, sx in ((x0, -1.0), (x1, 1.0)):
        p = [(x, y, z) for y, z in prof]
        quads += [[p[0], p[1], p[2], p[5]], [p[5], p[2], p[3], p[4]]]
        normals += [(sx, 0.0, 0.0)] * 2
    _faces(mb, [q for qs, n in zip(quads, normals) for q in _orient([qs], n)], "leaf_hedge")
    return mb


def dish() -> MeshBuilder:
    """Satellite dish on a short pole, looking up and outward."""
    mb = MeshBuilder()
    _box(mb, -0.03, 0.03, -0.03, 0.03, 0.0, 0.9, "iron")
    c = np.array([0.0, 0.1, 1.15])
    t = np.linspace(0, 2 * math.pi, 12, endpoint=False)
    tilt = math.radians(40)
    ring = np.stack([0.45 * np.cos(t), 0.45 * np.sin(t) * math.cos(tilt), 0.45 * np.sin(t) * math.sin(tilt)], 1) + c
    back = c - np.array([0.0, 0.12 * math.sin(tilt), -0.12 * math.cos(tilt)])
    add_sheet(mb, [[ring[k], ring[(k + 1) % 12], back] for k in range(12)], "dish_white")
    return mb


def cat(color: str) -> MeshBuilder:
    """A cat sitting on the doorstep."""
    mb = MeshBuilder()
    add_octahedron(mb, 0, 0, 0.16, 0.13, 0.16, color)
    add_octahedron(mb, 0, 0.06, 0.36, 0.08, 0.075, color, twist=0.78)
    for side in (-1, 1):
        add_cone(mb, side * 0.045, 0.06, 0.41, 0.025, 0.06, color, segments=3)
    _box(mb, 0.1, 0.13, -0.14, 0.12, 0.0, 0.03, color)
    return mb


def awning(colors: tuple, top: float = 2.75) -> MeshBuilder:
    """Striped shop awning fixed `top` m up the wall, 2.6 m wide, sloping 1.3 m out, with a scalloped edge."""
    mb = MeshBuilder()
    w, depth, drop = 2.6, 1.3, 0.55
    strips = 8
    for k in range(strips):
        x0, x1 = -w / 2 + w * k / strips, -w / 2 + w * (k + 1) / strips
        a, b = np.array([x0, 0.0, top]), np.array([x1, 0.0, top])
        c, d = np.array([x1, depth, top - drop]), np.array([x0, depth, top - drop])
        mat = colors[k % 2]
        add_sheet(mb, [[a, c, d], [a, b, c]], mat)
        mid = np.array([(x0 + x1) / 2, depth, top - drop - 0.2])
        add_sheet(mb, [[d, mid, c]], mat)
    for side in (-1, 1):   # an arm along each side edge and a brace back to the wall
        x = side * (w / 2 - 0.03)
        _bar(mb, (x, 0.0, top), (x, depth, top - drop), 0.015, "iron")
        _bar(mb, (x, 0.0, top - 0.75), (x, depth * 0.55, top - drop * 0.55), 0.012, "iron")
    return mb


def shop_front(goods: str = "", rng=None) -> MeshBuilder:
    """A shop opening: dark interior, wooden shelves and a counter, stocked with one trade's goods."""
    mb = MeshBuilder()
    _box(mb, -1.3, 1.3, 0.0, 0.03, 0.0, 2.5, "shop_dark")
    for z in (0.9, 1.5, 2.1):
        _box(mb, -1.2, 1.2, 0.03, 0.3, z, z + 0.05, "wood")
        if goods:
            _shelf(mb, goods, rng, z + 0.05, 0.17, 2.2)
    _box(mb, -1.2, 1.2, 0.03, 0.55, 0.0, 0.85, "wood")
    if goods:
        _shelf(mb, goods, rng, 0.85, 0.4, 2.0)
    return mb


def _shelf(mb, goods: str, rng, z: float, y: float, width: float) -> None:
    """A row of goods standing on a shelf at height z, centered y m out from the wall."""
    colors = SHOP_GOODS[goods]
    x = -width / 2 + 0.1
    while x < width / 2 - 0.1:
        mat = colors[int(rng.integers(len(colors)))]
        if goods in ("spices", "perfume"):          # jars and bottles
            r, h = (0.06, float(rng.uniform(0.14, 0.22))) if goods == "spices" else (0.035, float(rng.uniform(0.12, 0.2)))
            extrude(mb, regular_polygon(x + r, y, r, 6), z, z + h, mat, mat)
            x += 2 * r + 0.04
        elif goods in ("pots", "copper"):           # round pots and pans
            r = float(rng.uniform(0.08, 0.13))
            extrude(mb, regular_polygon(x + r, y, r, 8), z, z + r, mat, None)
            add_dome(mb, x + r, y, z + r, r, mat, height=r * 0.8, segments=8, rings=2)
            x += 2 * r + 0.05
        elif goods == "chechia":                    # stacked felt hats
            extrude(mb, regular_polygon(x + 0.1, y, 0.1, 8), z, z + 0.12 * int(rng.integers(1, 3)), mat, mat)
            x += 0.24
        elif goods == "fruit":                      # baskets heaped with fruit
            extrude(mb, regular_polygon(x + 0.15, y, 0.15, 8), z, z + 0.1, "wood", None)
            add_octahedron(mb, x + 0.15, y, z + 0.13, 0.15, 0.08, mat, twist=x)
            x += 0.36
        else:                                       # folded cloth and rugs
            w = float(rng.uniform(0.3, 0.45))
            _box(mb, x, x + w, y - 0.12, y + 0.12, z, z + float(rng.uniform(0.08, 0.25)), mat)
            x += w + 0.04


def spice_stall(rng) -> MeshBuilder:
    """Low table with spice pyramids in bright colors."""
    mb = MeshBuilder()
    _box(mb, -0.9, 0.9, 0.0, 0.7, 0.0, 0.6, "wood")
    order = rng.permutation(len(SPICES))
    for k in range(6):
        x, y = -0.6 + 0.6 * (k % 3), 0.18 + 0.35 * (k // 3)
        extrude(mb, regular_polygon(x, y, 0.16, 8), 0.6, 0.66, "tray_metal", "tray_metal")
        add_cone(mb, x, y, 0.66, 0.15, float(rng.uniform(0.22, 0.32)), SPICES[int(order[k])], segments=8)
    return mb


def chechia_shelf() -> MeshBuilder:
    """Wall shelf of red chechia hats."""
    mb = MeshBuilder()
    for row, z in enumerate((0.9, 1.35, 1.8)):
        _box(mb, -1.1, 1.1, 0.0, 0.32, z - 0.04, z, "wood")
        for k in range(7):
            x = -0.95 + 0.32 * k
            extrude(mb, regular_polygon(x, 0.16, 0.12, 8), z, z + 0.14, "chechia_red", "chechia_red")
            if (k + row) % 3 == 0:
                extrude(mb, regular_polygon(x, 0.16, 0.12, 8), z + 0.14, z + 0.28, "chechia_red", "chechia_red")
    return mb


def copper_display() -> MeshBuilder:
    """Copper trays on the wall and pots on the ground."""
    mb = MeshBuilder()
    for k, (x, z) in enumerate(((-0.7, 1.2), (0.0, 1.5), (0.7, 1.2), (-0.35, 1.9), (0.35, 1.9))):
        r = 0.22 if k % 2 else 0.3
        _slab(mb, [(x + r * math.cos(a), z + r * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 12, endpoint=False)],
              0.02, 0.05, "copper")
    for x in (-0.6, 0.0, 0.6):
        extrude(mb, regular_polygon(x, 0.45, 0.2, 10), 0.0, 0.3, "copper", None)
        add_dome(mb, x, 0.45, 0.3, 0.2, "copper", height=0.15, segments=10, rings=2)
    return mb


def rug_hang(scheme: tuple) -> MeshBuilder:
    """A kilim hanging on the wall: border, field and a diamond in the middle."""
    field, border, motif = scheme
    mb = MeshBuilder()
    w, h, z0 = 1.2, 1.9, 0.5
    _slab(mb, [(-w / 2, z0), (w / 2, z0), (w / 2, z0 + h), (-w / 2, z0 + h)], 0.02, 0.04, border)
    _slab(mb, [(-w / 2 + 0.1, z0 + 0.1), (w / 2 - 0.1, z0 + 0.1), (w / 2 - 0.1, z0 + h - 0.1), (-w / 2 + 0.1, z0 + h - 0.1)],
          0.04, 0.05, field)
    cz = z0 + h / 2
    for dz in (-0.5, 0.0, 0.5):
        _slab(mb, [(0, cz + dz - 0.22), (0.25, cz + dz), (0, cz + dz + 0.22), (-0.25, cz + dz)], 0.05, 0.06, motif)
    return mb


def fruit_crate(rng) -> MeshBuilder:
    mb = MeshBuilder()
    _box(mb, -0.35, 0.35, -0.25, 0.25, 0.0, 0.3, "wood")
    fruit = "orange_fruit" if rng.random() < 0.6 else "spice_brown"
    for k in range(9):
        add_octahedron(mb, -0.22 + 0.22 * (k % 3), -0.14 + 0.14 * (k // 3), 0.34, 0.08, 0.07, fruit, twist=0.4 * k)
    return mb


def cafe_set() -> MeshBuilder:
    """A small cafe table with two white plastic chairs."""
    mb = MeshBuilder()
    extrude(mb, regular_polygon(0, 0, 0.35, 10), 0.7, 0.74, "plastic_white", "plastic_white")
    _box(mb, -0.03, 0.03, -0.03, 0.03, 0.0, 0.7, "iron")
    for side in (-1, 1):
        x = side * 0.7
        _box(mb, x - 0.22, x + 0.22, -0.22, 0.22, 0.42, 0.46, "plastic_white")
        _box(mb, x + side * 0.2 - 0.02, x + side * 0.2 + 0.02, -0.22, 0.22, 0.46, 0.9, "plastic_white")
        for lx in (-0.18, 0.18):
            for ly in (-0.18, 0.18):
                _box(mb, x + lx - 0.02, x + lx + 0.02, ly - 0.02, ly + 0.02, 0.0, 0.42, "plastic_white")
    return mb


def street_lamp() -> MeshBuilder:
    """A cast-iron street lamp: its arm and lantern lean over the street (front)."""
    mb = MeshBuilder()
    extrude(mb, regular_polygon(0, 0, 0.12, 6), 0.0, 0.5, "iron", "iron")
    extrude(mb, regular_polygon(0, 0, 0.055, 6), 0.5, 4.3, "iron", "iron")
    _bar(mb, (0.0, 0.0, 4.15), (0.0, 0.75, 4.25), 0.025, "iron")
    _bar(mb, (0.0, 0.0, 3.7), (0.0, 0.45, 4.2), 0.02, "iron")
    _box(mb, -0.13, 0.13, 0.62, 0.88, 3.72, 4.08, "lantern_glow")
    add_cone(mb, 0.0, 0.75, 4.08, 0.2, 0.2, "iron", segments=4)
    return mb


def string_lantern() -> MeshBuilder:
    """A small lantern hanging from a rope across the street (origin at the hook)."""
    mb = MeshBuilder()
    _box(mb, -0.08, 0.08, -0.08, 0.08, -0.22, 0.0, "lantern_glow")
    add_cone(mb, 0, 0, 0.0, 0.11, 0.08, "copper", segments=4)
    return mb


def tree_mesh(mb: MeshBuilder, t, z: float) -> None:
    """A planned tree (city/model.Tree) standing at height z."""
    h = t.height
    if t.kind == "palm":
        extrude(mb, regular_polygon(t.x, t.y, 0.22, 5), z - 0.3, z + h, "trunk", "trunk")
        top = np.array([t.x, t.y, z + h])
        tris = []
        for k in range(7):
            a = k * 2 * math.pi / 7 + 0.4
            d = np.array([math.cos(a), math.sin(a), 0.0])
            side = np.array([-d[1], d[0], 0.0]) * 0.55
            mid = top + d * 1.6 + np.array([0.0, 0.0, 0.35])
            tip = top + d * 3.4 + np.array([0.0, 0.0, -1.5])
            tris += [[top, mid - side, tip], [top, tip, mid + side]]
        add_sheet(mb, tris, "leaf_palm", 0.02)
    elif t.kind == "cypress":
        add_cone(mb, t.x, t.y, z - 0.2, 1.1, h, "leaf_cypress", segments=6)
    else:
        trunk = 0.3 * h if t.kind == "broadleaf" else 0.25 * h
        extrude(mb, regular_polygon(t.x, t.y, 0.18, 4), z - 0.3, z + trunk + 0.4, "trunk", None)
        rx = 0.34 * h if t.kind == "broadleaf" else 0.42 * h
        mat = {"broadleaf": "leaf", "citrus": "leaf_citrus"}.get(t.kind, "leaf_olive")
        turn = (t.x * 7.3 + t.y * 3.1) % 6.28   # a crown of three clumps, turned differently per tree
        add_octahedron(mb, t.x, t.y, z + trunk + 0.34 * h, rx * 0.8, 0.32 * h, mat, twist=turn)
        for k in (0, 1):
            a = turn + k * 2.6
            add_octahedron(mb, t.x + math.cos(a) * rx * 0.5, t.y + math.sin(a) * rx * 0.5, z + trunk + (0.22 + 0.08 * k) * h,
                           rx * 0.6, 0.24 * h, mat, twist=turn + k)


def tree_piece(kind: str, height: float = 8.0) -> MeshBuilder:
    """A tree as a kit piece, drawn as instances and scaled to each planned tree's height."""
    mb = MeshBuilder()
    tree_mesh(mb, Tree(0.0, 0.0, kind, height), 0.0)
    return mb


# --- colonial arcades and iron balconies (prompt 22): no random draws, sizes from the style --------
ARCADE = {"bay": [3.5, 4.0], "nominal": 3.75, "depth": 2.5, "height": 3.6, "pillar": [0.8, 0.45], "spring": 1.7,
          "sink": 0.6, "cornice": 0.12, "corner_pier": 0.8,           # the pieces; then the layout (city/dressing.py)
          "districts": ["colonial"], "kinds": ["boulevard", "arterial", "ring"], "bay_relaxed": [3.2, 4.4],
          "above": 0.5, "step": 0.35, "gap": 0.08, "join": 0.3, "bend": 10.0, "corner_angle": 5.0, "wrap": 1,
          "cafe_reach": 1.25, "lamp_shift": 2.25, "lamp_clear": 0.3, "tree_trunk": 0.3, "tree_clear": 0.05,
          "tree_curb": 0.3}
IRON = {"width": 1.2, "depth": 0.6, "rail": 1.0, "span": 3.2, "sill": 0.95}


def _orient(quads, normal) -> list:
    """Quads turned (corner order reversed) where needed so each one faces `normal`."""
    out = []
    for q in quads:
        q = np.asarray(q, dtype=np.float64)
        n = np.cross(q[1] - q[0], q[3] - q[0])
        out.append(q if np.dot(n, normal) >= 0 else q[::-1])
    return out


def _arc(cx: float, r: float, zs: float, segments: int) -> np.ndarray:
    """(segments + 1, 2) points (x, z) of a half circle springing at zs, from its right foot over to its left."""
    t = np.linspace(0.0, math.pi, segments + 1)
    return np.stack([cx + r * np.cos(t), zs + r * np.sin(t)], axis=1)


def _arch_wall(a: dict, x0, x1, o0, o1, back=None, ext=(0.0, 0.0), segments: int = 8) -> dict:
    """One arched wall of an arcade, x from x0 to x1, its round arch between pillars [x0, o0] and [o1, x1]:
    front (pillar faces at y = depth) seen from the street, back seen from the walkway up to the ceiling,
    the spandrel up to the cornice, jambs, soffit, archivolt, keystone, pillar bases and capitals.

    `back` limits the back faces along x (a corner pier's inner corner); `ext` stretches the trims of
    the end pillars outward (a corner pier's outer corner, where the side wall's trims meet them).
    Returns {material: quads}. No end caps: bays meeting in a run would show two faces in one plane.
    """
    d, pd, zs, sink, top, hc = a["depth"], a["pd"], a["spring"], a["sink"], a["top"], a["hc"]
    y1, y0 = d, d - pd
    bx0, bx1 = back if back is not None else (x0, x1)
    cap, zb, e, eb = 0.16, 0.32, 0.04, 0.05
    cx, r = (o0 + o1) / 2, (o1 - o0) / 2
    pts = _arc(cx, r, zs, segments)
    crown = zs + r
    plaster, trim = [], []
    for xa, xb, ba, bb in ((x0, o0, bx0, o0), (o1, x1, o1, bx1)):          # the two pillars and the wall above them
        plaster += [_front(xa, xb, zb, zs - cap, y1), _front(xa, xb, zs, top, y1),
                    _front(ba, bb, zb, zs - cap, y0, back=True), _front(ba, bb, zs, hc, y0, back=True)]
    plaster += [_side(o0, y0, y1, zb, zs - cap), _side(o1, y0, y1, zb, zs - cap, left=True)]   # jambs
    for k in range(segments):                                               # spandrel, front and back, and soffit
        (xa, za), (xb, zb_) = pts[k], pts[k + 1]
        plaster += [[(xa, y1, za), (xb, y1, zb_), (xb, y1, top), (xa, y1, top)],
                    [(xa, y0, za), (xa, y0, hc), (xb, y0, hc), (xb, y0, zb_)]]
        plaster += _orient([[(xa, y0, za), (xb, y0, zb_), (xb, y1, zb_), (xa, y1, za)]],
                           (cx - (xa + xb) / 2, 0.0, zs - (za + zb_) / 2))
    rw = 0.13                                                               # archivolt: a band round the arch
    outer = _arc(cx, r + rw, zs, segments)
    for k in range(segments):
        trim += _orient([[(pts[k][0], y1 + 0.025, pts[k][1]), (pts[k + 1][0], y1 + 0.025, pts[k + 1][1]),
                          (outer[k + 1][0], y1 + 0.025, outer[k + 1][1]), (outer[k][0], y1 + 0.025, outer[k][1])]],
                        (0.0, 1.0, 0.0))
    kw, ky = 0.15, y1 + 0.05                                                # keystone up to the cornice
    trim += [_front(cx - kw, cx + kw, crown - 0.08, top, ky), _side(cx + kw, y1, ky, crown - 0.08, top),
             _side(cx - kw, y1, ky, crown - 0.08, top, left=True), _flat(cx - kw, cx + kw, y1, ky, crown - 0.08, down=True)]
    for z0, z1, p in ((zs - cap, zs, e), (-sink, zb, eb)):                 # capitals and bases, p proud of the pillar
        # left pillar: its trims grow into the opening at the jamb o0; behind an L-shaped corner pier
        # the back trim stops where the other wall's back trim meets it
        fa, fb, ba = x0 - ext[0], o0 + p, (bx0 + p if bx0 > x0 else x0)
        trim += [_front(fa, fb, z0, z1, y1 + p), _front(ba, fb, z0, z1, y0 - p, back=True),
                 _side(fb, y0 - p, y1 + p, z0, z1), _flat(fa, fb, y0 - p, y1 + p, z1)]
        trim += [_flat(fa, fb, y0 - p, y1 + p, z0, down=True)] if z0 > 0 else []
        fa, fb, bb = o1 - p, x1 + ext[1], (bx1 - p if bx1 < x1 else x1)   # right pillar
        trim += [_front(fa, fb, z0, z1, y1 + p), _front(fa, bb, z0, z1, y0 - p, back=True),
                 _side(fa, y0 - p, y1 + p, z0, z1, left=True), _flat(fa, fb, y0 - p, y1 + p, z1)]
        trim += [_flat(fa, fb, y0 - p, y1 + p, z0, down=True)] if z0 > 0 else []
    return {"plaster": plaster, "trim": trim}


def _arcade_dims(cfg: dict | None) -> dict:
    """Arcade sizes from the style table [dressing.arcade], with the defaults above."""
    c = {**ARCADE, **(cfg or {})}
    pw, pd = (float(v) for v in c["pillar"])
    h = float(c["height"])
    return {"w": float(c["nominal"]), "depth": float(c["depth"]), "pw": pw, "pd": pd, "spring": float(c["spring"]),
            "sink": float(c["sink"]), "cp": float(c["cornice"]), "H": h, "top": h - 0.22, "hc": h - 0.3,
            "pier": float(c["corner_pier"])}


def _arcade_slab(mb, x0, x1, a: dict, y_back: float = -0.1, side=None) -> None:
    """Ceiling over the walkway, the terrace on top and the cornice (with a fillet) along the front."""
    d, cp, top, hc, h = a["depth"], a["cp"], a["top"], a["hc"], a["H"]
    _faces(mb, [_flat(x0, x1, y_back, d - a["pd"], hc, down=True)], "warm_white")
    _faces(mb, [_flat(x0, x1, y_back, d + cp, h)], "roof_white")
    _faces(mb, [_front(x0, x1, top, h, d + cp), _flat(x0, x1, d + 0.04, d + cp, top, down=True),
                _front(x0, x1, top - 0.08, top, d + 0.04), _flat(x0, x1, d, d + 0.04, top - 0.08, down=True)], "stone_frame")


def _arcade_cap(x: float, a: dict, left: bool, y_back: float = -0.1) -> tuple:
    """End faces of a bay at x (its pillar, wall, slab and cornice in profile), facing -x with `left`."""
    d, pd, zs, sink, top, hc, h, cp = a["depth"], a["pd"], a["spring"], a["sink"], a["top"], a["hc"], a["H"], a["cp"]
    y0 = d - pd
    plaster = [_side(x, y0, d, 0.32, zs - 0.16, left), _side(x, y0, d, zs, hc, left), _side(x, y_back, d, hc, h, left)]
    trim = [_side(x, y0 - 0.05, d + 0.05, -sink, 0.32, left), _side(x, y0 - 0.04, d + 0.04, zs - 0.16, zs, left),
            _side(x, d, d + cp, top, h, left), _side(x, d, d + 0.04, top - 0.08, top, left)]
    return plaster, trim


def arcade_bay(cfg: dict | None = None) -> MeshBuilder:
    """One bay of a colonial arcade (the ville nouvelle of Tunis): a round arch on two half pillars,
    the covered walkway behind it with its ceiling, the terrace on top level with the first floor,
    and a cornice. The origin is on the wall face at street level, the bay centered on it, `nominal`
    wide (placements stretch it along the wall to 3.5-4 m); the pillars reach `sink` below street
    level so they meet a sloping sidewalk. Both ends are closed: inside a run they meet back to back."""
    a = _arcade_dims(cfg)
    mb = MeshBuilder()
    w = a["w"] / 2
    half = a["pw"] / 2
    q = _arch_wall(a, -w, w, -w + half, w - half)
    for x, left in ((-w, True), (w, False)):
        p, t = _arcade_cap(x, a, left)
        q["plaster"] += p
        q["trim"] += t
    _faces(mb, q["plaster"], "warm_white")
    _faces(mb, q["trim"], "stone_frame")
    _arcade_slab(mb, -w, w, a)
    return mb


def arcade_corner(cfg: dict | None = None) -> MeshBuilder:
    """The corner of an arcade turning round a building: a square `depth` x `depth` in front of the
    building corner (the origin; x from 0 to depth along the first facade's street front, y out toward
    the second facade's street), with a narrower arch on each street side and an L-shaped corner pier.
    Placed facing the second facade's street: its side x = 0 meets that facade's first bay, its side
    y = 0 the first facade's last bay."""
    a = _arcade_dims(cfg)
    mb = MeshBuilder()
    d, pd, half, pier = a["depth"], a["pd"], a["pw"] / 2, a["pier"]
    front = _arch_wall(a, 0.0, d, half, d - pier, back=(0.0, d - pd), ext=(0.0, 0.04), segments=6)
    side = _arch_wall(a, -d, 0.0, -d + pier, -half, back=(-d + pd, 0.0), ext=(0.04, 0.0), segments=6)
    for wall, x, left in ((front, 0.0, True), (side, 0.0, False)):   # closed where it meets the bays: corners a
        p, t = _arcade_cap(x, a, left, y_back=0.0)                     # few degrees off square leave a sliver
        wall["plaster"] += p
        wall["trim"] += t
    for mat in ("plaster", "trim"):                     # the side wall, built along its own facade: (s, t) -> (t, -s)
        side[mat] = [[(t, -s, z) for s, t, z in q] for q in side[mat]]
    _faces(mb, front["plaster"] + side["plaster"], "warm_white")
    _faces(mb, front["trim"] + side["trim"], "stone_frame")
    cp, top, hc, h = a["cp"], a["top"], a["hc"], a["H"]
    _faces(mb, [_flat(0.0, d - pd, 0.0, d - pd, hc, down=True)], "warm_white")
    _faces(mb, [_flat(0.0, d + cp, 0.0, d + cp, h)], "roof_white")
    _faces(mb, [_front(0.0, d + cp, top, h, d + cp), _flat(0.0, d + cp, d + 0.04, d + cp, top, down=True),
                _front(0.0, d + 0.04, top - 0.08, top, d + 0.04), _flat(0.0, d + 0.04, d, d + 0.04, top - 0.08, down=True),
                _side(d + cp, 0.0, d + cp, top, h), _flat(d + 0.04, d + cp, 0.0, d + 0.04, top, down=True),
                _side(d + 0.04, 0.0, d + 0.04, top - 0.08, top), _flat(d, d + 0.04, 0.0, d, top - 0.08, down=True)],
           "stone_frame")
    return mb


def arcade_bend(cfg: dict | None = None, angle: float = 45.0) -> MeshBuilder:
    """The pier of an arcade turning a cut street corner (prompt 23): a wedge in front of the corner
    where two faces meet at a convex turn of `angle` degrees (45 for a pan coupe, 22.5 between the
    faces of a rounded corner). The origin is the corner on the wall line, +y the bisector out to the
    street; each side meets its facade's last bay in the plane square to that facade, and the pillar
    face, trims, cornice, ceiling and terrace run on mitred to the other side. Symmetric."""
    a = _arcade_dims(cfg)
    mb = MeshBuilder()
    d, pd, zs, sink, top, hc, h, cp = a["depth"], a["pd"], a["spring"], a["sink"], a["top"], a["hc"], a["H"], a["cp"]
    d0, half = d - pd, math.radians(angle) / 2
    ni, nj = np.array([math.sin(half), math.cos(half)]), np.array([-math.sin(half), math.cos(half)])

    def line(o: float) -> list:                     # the faces' line o m out from both walls, mitred
        return [ni * o, np.array([0.0, o / math.cos(half)]), nj * o]

    def wall(o: float, z0: float, z1: float, out: bool = True) -> list:
        pts = line(o) if out else line(o)[::-1]     # seen from the street, or from the walkway
        return [[(*p, z0), (*q, z0), (*q, z1), (*p, z1)] for p, q in zip(pts[:-1], pts[1:])]

    def flat(o0: float, o1: float, z: float, up: bool = True) -> list:
        if o0 <= 0.0:
            p = line(o1)
            q = [[(0.0, 0.0, z), (*p[0], z), (*p[1], z), (*p[2], z)]]
        else:
            p, r = line(o0), line(o1)
            q = [[(*p[0], z), (*r[0], z), (*r[1], z), (*p[1], z)], [(*p[1], z), (*r[1], z), (*r[2], z), (*p[2], z)]]
        return _orient(q, (0.0, 0.0, 1.0 if up else -1.0))

    def cap(o0: float, o1: float, z0: float, z1: float) -> list:   # the ends that meet the bays
        out = []
        for n, toward in ((ni, (math.cos(half), -math.sin(half), 0.0)), (nj, (-math.cos(half), -math.sin(half), 0.0))):
            out += _orient([[(*(n * o0), z0), (*(n * o1), z0), (*(n * o1), z1), (*(n * o0), z1)]], toward)
        return out

    wall_q = lambda o, z0, z1, out=True: _orient(wall(o, z0, z1, out), (0.0, 1.0 if out else -1.0, 0.0))
    plaster = wall_q(d, 0.32, top) + wall_q(d0, 0.32, hc, out=False) + cap(d0, d, 0.32, hc) + cap(0.0, d + cp, hc, h)
    trim = []
    for z0, z1, e in ((-sink, 0.32, 0.05), (zs - 0.16, zs, 0.04)):          # base and capital, proud of the pier
        trim += wall_q(d + e, z0, z1) + wall_q(d0 - e, z0, z1, out=False) + flat(d0 - e, d + e, z1)
        trim += (flat(d0 - e, d + e, z0, up=False) if z0 > 0 else []) + cap(d0 - e, d + e, z0, z1)
    _faces(mb, plaster + flat(0.0, d0, hc, up=False), "warm_white")
    _faces(mb, trim, "stone_frame")
    _faces(mb, flat(0.0, d + cp, h), "roof_white")
    _faces(mb, wall_q(d + cp, top, h) + flat(d + 0.04, d + cp, top, up=False) + wall_q(d + 0.04, top - 0.08, top)
           + flat(d, d + 0.04, top - 0.08, up=False), "stone_frame")
    return mb


def _rail(x0, x1, y, z, t: float) -> list:
    """A square iron bar along x at depth y and height z (its center), t thick: four faces."""
    return [_front(x0, x1, z - t / 2, z + t / 2, y + t / 2), _front(x0, x1, z - t / 2, z + t / 2, y - t / 2, back=True),
            _flat(x0, x1, y - t / 2, y + t / 2, z + t / 2), _flat(x0, x1, y - t / 2, y + t / 2, z - t / 2, down=True)]


def _rail_side(x, y0, y1, z, t: float) -> list:
    """A square iron bar from the wall outward (along y) at x and height z: four faces."""
    return [_side(x + t / 2, y0, y1, z - t / 2, z + t / 2), _side(x - t / 2, y0, y1, z - t / 2, z + t / 2, left=True),
            _flat(x - t / 2, x + t / 2, y0, y1, z + t / 2), _flat(x - t / 2, x + t / 2, y0, y1, z - t / 2, down=True)]


def balcony_iron(cfg: dict | None = None, long: bool = False) -> MeshBuilder:
    """A wrought-iron balcony of the ville nouvelle: a thin stone slab on two consoles and a rail of thin
    bars under a frieze of rings (a simple scroll pattern), about 1.2 x 0.6 m, or `long` across two
    windows `span` m apart. The origin is at the window sill on the wall face: the slab top is level with
    the floor, `sill` m lower. Bars have faces on both sides (seen from the street and from the room)."""
    c = {**IRON, **(cfg or {})}
    d, rail, z0 = float(c["depth"]), float(c["rail"]), -float(c["sill"])
    w = float(c["width"]) + (float(c["span"]) if long else 0.0)
    x0, x1 = -w / 2, w / 2
    mb = MeshBuilder()
    slab = [_flat(x0, x1, -0.05, d, z0), _flat(x0, x1, 0.0, d, z0 - 0.1, down=True), _front(x0, x1, z0 - 0.1, z0, d),
            _side(x1, 0.0, d, z0 - 0.1, z0), _side(x0, 0.0, d, z0 - 0.1, z0, left=True)]
    consoles = np.linspace(x0 + 0.2, x1 - 0.2, 3 if long else 2)
    for x in consoles:                                   # stone consoles under the slab, tapering to the front
        lo, k = z0 - 0.1, 0.05
        slab += _orient([[(x + k, 0.0, lo - 0.32), (x + k, d - 0.12, lo - 0.06), (x + k, d - 0.12, lo), (x + k, 0.0, lo)]],
                        (1, 0, 0))
        slab += _orient([[(x - k, 0.0, lo - 0.32), (x - k, d - 0.12, lo - 0.06), (x - k, d - 0.12, lo), (x - k, 0.0, lo)]],
                        (-1, 0, 0))
        slab += _orient([[(x - k, 0.0, lo - 0.32), (x + k, 0.0, lo - 0.32), (x + k, d - 0.12, lo - 0.06),
                          (x - k, d - 0.12, lo - 0.06)]], (0, 0.3, -1))
        slab.append(_front(x - k, x + k, lo - 0.06, lo, d - 0.12))
    _faces(mb, slab, "stone_frame")
    t, yb = 0.03, d - 0.05                               # rail bars: hand rail, frieze rail, foot rail
    top, frieze, foot = z0 + rail, z0 + rail - 0.2, z0 + 0.08
    iron = []
    for z in (top, frieze, foot):
        iron += _rail(x0 + 0.03, x1 - 0.03, yb, z, t if z == top else 0.02)
        for x in (x0 + 0.03, x1 - 0.03):
            iron += _rail_side(x, 0.0, yb - 0.01, z, t if z == top else 0.02)
    posts = [x0 + 0.03, x1 - 0.03] + ([0.0] if long else [])
    for x in posts:                                      # corner posts, both faces of each side
        iron += [_front(x - 0.015, x + 0.015, z0, top, yb + 0.015), _front(x - 0.015, x + 0.015, z0, top, yb - 0.015, back=True),
                 _side(x + 0.015, yb - 0.015, yb + 0.015, z0, top), _side(x - 0.015, yb - 0.015, yb + 0.015, z0, top, left=True)]
    count = max(2, int(round((w - 0.06) / 0.11)))
    for x in np.linspace(x0 + 0.03, x1 - 0.03, count + 1)[1:-1]:    # thin bars, both faces
        iron += [_front(x - 0.008, x + 0.008, foot, frieze, yb + 0.004), _front(x - 0.008, x + 0.008, foot, frieze, yb - 0.004, back=True)]
    for y in np.arange(0.12, yb - 0.05, 0.12):          # side panels back to the wall
        for x in (x0 + 0.03, x1 - 0.03):
            iron += [_side(x + 0.004, y - 0.008, y + 0.008, foot, top), _side(x - 0.004, y - 0.008, y + 0.008, foot, top, left=True)]
    rings = max(3, int(round((w - 0.06) / 0.34)))        # the frieze: rings between frieze and hand rail, a ring's
    radius, cz = 0.08, (frieze + top) / 2 - 0.0025       # width apart, touching both rails
    for cx in np.linspace(x0 + 0.03, x1 - 0.03, rings + 1)[:-1] + (w - 0.06) / rings / 2:
        ring_in, ring_out = _arc(cx, radius - 0.006, cz, 4), _arc(cx, radius + 0.006, cz, 4)
        for sgn in (1.0, -1.0):                          # upper and lower half
            pi_, po = ring_in * [1, sgn] + [0, cz * (1 - sgn)], ring_out * [1, sgn] + [0, cz * (1 - sgn)]
            for k in range(4):
                for y, face in ((yb + 0.004, 1.0), (yb - 0.004, -1.0)):
                    iron += _orient([[(pi_[k][0], y, pi_[k][1]), (pi_[k + 1][0], y, pi_[k + 1][1]),
                                      (po[k + 1][0], y, po[k + 1][1]), (po[k][0], y, po[k][1])]], (0, face, 0))
    _faces(mb, iron, "iron")
    return mb


def catalog(rng, seed: int = 0, trees: dict | None = None, climber: dict | None = None,
            arcade: dict | None = None, iron: dict | None = None, hedge_cfg: dict | None = None) -> dict:
    """Every procedural piece: {name: (MeshBuilder, category, anchor)}.

    `trees` and `climber` are the style tables `[dressing.trees]` and `[dressing.climber]`; their
    shapes use their own random streams (from `seed`), never `rng`, so they cannot change any other
    piece. Without them the light tree pieces stay and no tree variants or climbers are made.
    `arcade` and `iron` are `[dressing.arcade]` and `[dressing.balcony_iron]` (sizes only); `hedge_cfg` is
    `[dressing.hedge]` (prompt 24), and without it no hedge piece is made.
    """
    pieces = {}
    for color in DOOR_COLORS:
        pieces[color] = (door(color), "door", "wall")
        pieces[color + "_rich"] = (door(color, rich=True), "door", "wall")
        pieces["window_grille_" + color[5:]] = (window(color, "grille"), "window", "wall")
        pieces["window_shutter_" + color[5:]] = (window(color, "shutter"), "window", "wall")
    for k, colors in enumerate(AWNINGS):
        pieces[colors] = (awning((colors, "awning_cream")), "awning", "wall")
    for k, scheme in enumerate(RUGS):
        pieces[f"rug_hang_{k}"] = (rug_hang(scheme), "wall_goods", "wall")
    for color in CATS:
        pieces[color] = (cat(color), "cat", "ground")
    pieces.update({
        "lantern": (lantern(), "lamp", "wall"),
        "pot_plant": (pot_plant(rng), "pot", "ground"),
        "pot_plant_b": (pot_plant(rng), "pot", "ground"),
        "doukkana": (doukkana(), "bench", "wall"),
        "tank_white": (tank("tank_white"), "roof", "ground"),
        "tank_black": (tank("tank_black"), "roof", "ground"),
        "dish": (dish(), "roof", "ground"),
        "shop_front": (shop_front(), "shop", "wall"),
        **{f"shop_front_{g}": (shop_front(g, rng), "shop", "wall") for g in SHOP_GOODS},
        "spice_stall": (spice_stall(rng), "goods", "ground"),
        "chechia_shelf": (chechia_shelf(), "wall_goods", "wall"),
        "copper_display": (copper_display(), "wall_goods", "wall"),
        "fruit_crate": (fruit_crate(rng), "goods", "ground"),
        "fruit_crate_b": (fruit_crate(rng), "goods", "ground"),
        "cafe_set": (cafe_set(), "furniture", "ground"),
        "string_lantern": (string_lantern(), "lamp", "ground"),
        "street_lamp": (street_lamp(), "lamp", "ground"),
        **{f"tree_{kind}": (tree_piece(kind), "tree", "ground") for kind in ("broadleaf", "olive", "cypress", "palm")},
    })
    for name, mb in tree_pieces(seed, trees or {}).items():
        pieces[name] = (mb, "tree", "ground")
    for name, mb in climber_pieces(seed, climber).items():
        pieces[name] = (mb, "plant", "wall")
    for color in DOOR_COLORS:   # every home's door and open walls (prompt 20.1); no random draws
        pieces["door_narrow_" + color[5:]] = (door_narrow(color), "door", "wall")
    for tint, mat in SLAB_TINTS.items():
        pieces["window_slab_" + tint] = (window_slab(mat), "window", "wall")
        pieces["window_slab_" + tint + "_shut"] = (window_slab(mat, shut=True), "window", "wall")
    pieces.update({
        "window_stair": (window_stair(), "window", "wall"),
        "balcony_slab": (balcony_slab(), "balcony", "wall"),
        "stair_door": (stair_door(), "door", "wall"),
    })
    pieces.update({             # colonial arcades and iron balconies (prompt 22); no random draws
        "arcade_bay": (arcade_bay(arcade), "arcade", "wall"),
        "arcade_corner": (arcade_corner(arcade), "arcade", "wall"),
        "arcade_bend": (arcade_bend(arcade, 45.0), "arcade", "wall"),           # prompt 23: cut street corners
        "arcade_bend_round": (arcade_bend(arcade, 22.5), "arcade", "wall"),
        "tank_stand": (tank_stand(), "roof", "ground"),                         # prompt 23: estate roofs
        "balcony_iron": (balcony_iron(iron), "balcony", "wall"),
        "balcony_iron_long": (balcony_iron(iron, long=True), "balcony", "wall"),
    })
    if hedge_cfg:               # villa garden hedges (prompt 24); no random draws
        pieces["hedge"] = (hedge(hedge_cfg), "plant", "ground")
    return pieces
