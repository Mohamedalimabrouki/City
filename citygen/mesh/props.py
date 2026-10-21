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
from .trees import tree_pieces

DOOR_COLORS = ("door_blue", "door_green", "door_yellow", "door_brown", "door_red")
AWNINGS = ("awning_red", "awning_green", "awning_blue", "awning_yellow")
SPICES = ("spice_red", "spice_orange", "spice_yellow", "spice_brown", "spice_green", "spice_ochre")
RUGS = (("rug_red", "rug_cream", "rug_black"), ("rug_blue", "rug_cream", "rug_red"),
        ("rug_green", "rug_orange", "rug_cream"))
CATS = ("cat_ginger", "cat_white", "cat_black", "cat_grey")
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
    for name, (pos, nrm, uv, tris, _n) in tmp._parts.items():
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


def bougainvillea(rng) -> MeshBuilder:
    """A climber against the wall: a trunk and clouds of pink bracts reaching about 4.5 m."""
    mb = MeshBuilder()
    _box(mb, -0.05, 0.05, 0.05, 0.15, 0.0, 3.2, "trunk")
    for k in range(9):
        x = float(rng.uniform(-1.1, 1.1))
        z = float(rng.uniform(2.0, 4.6))
        mat = "bougainvillea" if k % 3 else "leaf"
        add_octahedron(mb, x, 0.25, z, float(rng.uniform(0.35, 0.6)), float(rng.uniform(0.3, 0.45)), mat,
                       twist=float(rng.uniform(0, 1.5)))
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
        mat = "leaf" if t.kind == "broadleaf" else "leaf_olive"
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


def catalog(rng, seed: int = 0, trees: dict | None = None) -> dict:
    """Every procedural piece: {name: (MeshBuilder, category, anchor)}.

    `trees` is the style table `[dressing.trees]`; the crowns use their own random streams (from `seed`),
    never `rng`, so they cannot change any other piece. Without it the light three-clump trees are used.
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
        "bougainvillea": (bougainvillea(rng), "plant", "wall"),
        "bougainvillea_b": (bougainvillea(rng), "plant", "wall"),
        "string_lantern": (string_lantern(), "lamp", "ground"),
        "street_lamp": (street_lamp(), "lamp", "ground"),
        **{f"tree_{kind}": (tree_piece(kind), "tree", "ground") for kind in ("broadleaf", "olive", "cypress", "palm")},
    })
    for name, mb in tree_pieces(seed, trees or {}).items():
        pieces[name] = (mb, "tree", "ground")
    return pieces
