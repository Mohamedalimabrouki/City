"""Street furniture (prompt 26): the iron bench, the newspaper kiosk, the colonial fountain and the sabil;
the corniche's railing (prompt 36); the drinks kiosk and the cafe parasols (prompt 37).

Generator axes as in mesh/props.py: x along the piece's width, y toward its front (the side people use),
z up, meters. The bench, kiosk and fountain stand on the ground (origin at the bottom-center on the drawn
surface); the sabil hangs on a wall (origin on the wall face at street level). Pieces that may stand on a
slope reach a little below their origin (`sink`), so no edge floats on a sloping promenade or alley.

Round parts are lathed (`_lathe`): smooth normals around, flat along the profile, so a basin reads round
with few triangles. Fountain water uses the palette's `water_pool`, never `water` (the Blender scripts
hide `water` and draw their own sea); falling water is thin ribbons with faces on both sides. The kiosk's
glass pane is `glass_dark`, so the kit gives it a lit twin (`kiosk_lit`) for open kiosks at night.
Random details (the kiosk's magazine covers) come from the piece's own stream `stream(seed, "piece", name)`.
"""
from __future__ import annotations

import math

import numpy as np
from shapely.geometry import Polygon, box

from ..rng import stream
from .builder import MeshBuilder, add_cone, add_sheet, add_triangles, triangulate
from .props import _arch_outline, _bar, _faces, _flat, _front, _side, _slab

FURNITURE = {   # sizes in meters; `[dressing.furniture]` in the style overrides them
    "bench_length": 1.8, "seat": 0.45, "fountain_radius": 2.3, "fountain_height": 2.9,
    "kiosk": [2.2, 1.5, 2.45], "sabil": [1.9, 2.9], "sink": 0.25, "railing_length": 2.0, "railing_height": 1.0,
    "parasol": [1.2, 2.15, 2.5, 0.7], "parasol_valance": 0.13,
    "parasol_colors": ["parasol_white", "parasol_blue", "parasol_sand"],
}
COVERS = ("awning_red", "spice_yellow", "rug_blue", "plastic_white", "door_green", "spice_orange",
          "chechia_red", "cloth_2", "cloth_4", "rug_cream")   # magazine and newspaper covers
DRINKS = ("awning_red", "awning_blue", "plastic_white", "awning_cream")   # cans, bottles and cups, in colors it has
NEWS = {"name": "kiosk", "body": "kiosk_green", "band": "awning_red", "stripes": ("awning_green", "awning_cream"),
        "covers": COVERS, "tobacco": True, "plinth": "concrete_dark"}
CAFE_KIOSK = {"name": "kiosk_drinks", "body": "kiosk_blue", "band": "awning_red", "stripes": ("awning_blue", "awning_cream"),
              "covers": DRINKS, "tobacco": False, "plinth": "kiosk_trim"}   # the corniche's drinks kiosk (prompt 37):
                                                                           # few plain colors, no UVs (tile bytes)
CANVAS = "CANVAS"   # stand-in, renamed to each parasol's color


def _cfg(cfg: dict | None) -> dict:
    return {**FURNITURE, **(cfg or {})}


def _lathe(mb: MeshBuilder, profile, mat: str, segments: int = 16) -> None:
    """A surface of revolution about the z axis from a profile [(r, z), ...]. The outside lies to the
    right of the profile's travel (normal (dz, -dr)): up the outside of a wall, inward across a top."""
    prof = np.asarray(profile, dtype=np.float64)
    t = np.linspace(0.0, 2 * math.pi, segments + 1)
    c, s = np.cos(t), np.sin(t)
    base = np.arange(segments)
    for (r0, z0), (r1, z1) in zip(prof[:-1], prof[1:]):
        dr, dz = r1 - r0, z1 - z0
        length = math.hypot(dr, dz)
        if length < 1e-9 or (r0 < 1e-9 and r1 < 1e-9):
            continue
        nr, nz = dz / length, -dr / length
        pos = np.concatenate([np.stack([r0 * c, r0 * s, np.full_like(t, z0)], 1),
                              np.stack([r1 * c, r1 * s, np.full_like(t, z1)], 1)])
        nrm = np.tile(np.stack([nr * c, nr * s, np.full_like(t, nz)], 1), (2, 1))
        uv = np.concatenate([np.stack([t * max(r0, r1), np.full_like(t, -z0)], 1),
                             np.stack([t * max(r0, r1), np.full_like(t, -z1)], 1)])
        n = segments + 1
        tris = []
        if r0 > 1e-9:
            tris.append(np.stack([base, base + 1, base + n + 1], 1))
        if r1 > 1e-9:
            tris.append(np.stack([base, base + n + 1, base + n], 1))
        mb.add(mat, pos, nrm, uv, np.concatenate(tris))


def _streams(mb: MeshBuilder, r0: float, z0: float, r1: float, z1: float, count: int) -> None:
    """Thin streams of water falling from a bowl's lip, leaving it outward and dropping onto the water
    below: ribbons of two segments with faces on both sides (thin cloth rule), `count` round the bowl."""
    w = 0.035
    for a in (np.arange(count) + 0.5) * 2 * math.pi / count:
        u, t = np.array([math.cos(a), math.sin(a), 0.0]), np.array([-math.sin(a), math.cos(a), 0.0])
        pts = [u * r0 + [0, 0, z0], u * (r0 + 0.6 * (r1 - r0)) + [0, 0, z0 - 0.25 * (z0 - z1)], u * r1 + [0, 0, z1]]
        tris = []
        for p, q in zip(pts[:-1], pts[1:]):
            tris += [[p - t * w, q - t * w, q + t * w], [p - t * w, q + t * w, p + t * w]]
        add_sheet(mb, tris, "water_pool", 0.004)


def _beam(mb: MeshBuilder, section, x0: float, x1: float, mat: str) -> None:
    """A straight bar along x with a four-cornered cross-section [(y, z)] (counter-clockwise seen from +x):
    four long faces and two end caps."""
    sec = [np.asarray(p, dtype=np.float64) for p in section]
    quads = []
    for k in range(4):
        (ya, za), (yb, zb) = sec[k], sec[(k + 1) % 4]
        quads.append([(x0, ya, za), (x0, yb, zb), (x1, yb, zb), (x1, ya, za)])
    quads.append([(x1, y, z) for y, z in sec])
    quads.append([(x0, y, z) for y, z in sec[::-1]])
    _faces(mb, quads, mat)


def _plate(mb: MeshBuilder, poly: Polygon, y: float, mat: str) -> None:
    """A flat shape in the x-z plane at depth y, seen from the front (+y)."""
    tris = [[(a[0], y, a[1]), (c[0], y, c[1]), (b[0], y, b[1])] for a, b, c in triangulate(poly)]
    add_triangles(mb, tris, mat)


def bench_iron(cfg: dict | None = None) -> MeshBuilder:
    """The cast-iron bench of a colonial promenade: two iron side frames (legs, seat rail, back post and
    armrest, all closed bars) carrying four wooden seat slats and three back slats. The front (+y) is the
    side people sit facing; about 190 triangles."""
    c = _cfg(cfg)
    half, seat = float(c["bench_length"]) / 2, float(c["seat"])
    mb = MeshBuilder()
    for x in (-half + 0.12, half - 0.12):
        for p0, p1 in (((0.21, -0.04), (0.19, seat - 0.03)), ((-0.24, -0.04), (-0.19, seat - 0.03)),   # legs
                       ((0.25, seat - 0.03), (-0.21, seat - 0.03)),                                      # seat rail
                       ((-0.19, seat - 0.03), (-0.30, seat + 0.43)),                                     # back post
                       ((-0.24, seat + 0.20), (0.25, seat + 0.20)), ((0.21, seat - 0.03), (0.25, seat + 0.20))):
            _bar(mb, (x, p0[0], p0[1]), (x, p1[0], p1[1]), 0.022, "iron")
    for y in (0.18, 0.075, -0.03, -0.135):                    # seat slats, a gap between each
        _beam(mb, [(y - 0.04, seat - 0.03), (y + 0.04, seat - 0.03), (y + 0.04, seat), (y - 0.04, seat)],
              -half, half, "wood")
    a, b = np.array([-0.19, seat - 0.01]), np.array([-0.30, seat + 0.43])   # back slats along the back post
    u = (b - a) / np.linalg.norm(b - a)
    n = np.array([u[1], -u[0]])                               # toward the front
    for t in (0.18, 0.5, 0.82):
        m = a + (b - a) * t + n * 0.035
        lo, hi = m - u * 0.045, m + u * 0.045
        _beam(mb, [tuple(lo), tuple(lo + n * 0.025), tuple(hi + n * 0.025), tuple(hi)], -half, half, "wood")
    return mb


def kiosk(seed: int = 0, cfg: dict | None = None, look: dict | None = None) -> MeshBuilder:
    """A newspaper and tobacco kiosk of a Tunis boulevard: a dark green booth on a low plinth with cream
    trims, a serving hatch with a glass pane (lit at night in its twin) over a wooden counter of folded
    papers, a striped awning on iron arms, racks of magazines on both sides, a sign board on the roof and
    the red tobacco diamond on a corner bracket. The front (+y) is the hatch; about 300 triangles.
    `look` (CAFE_KIOSK): the corniche's drinks kiosk, Sidi Bou Said blue, racks of cans and bottles, no diamond."""
    c = _cfg(cfg)
    look = look or NEWS
    w, d, h = (float(v) for v in c["kiosk"])
    x0, x1, y0, y1, sink = -w / 2, w / 2, -d / 2, d / 2, float(c["sink"])
    hx, z_counter, z_top = w / 2 - 0.32, 1.0, h - 0.4          # the hatch
    rng = stream(seed, "piece", look["name"])
    covers_of = look["covers"]
    mb = MeshBuilder()
    plinth, base = [], 0.14
    plinth += [_front(x0 - 0.03, x1 + 0.03, -sink, base, y1 + 0.03), _front(x0 - 0.03, x1 + 0.03, -sink, base, y0 - 0.03, back=True),
               _side(x1 + 0.03, y0 - 0.03, y1 + 0.03, -sink, base), _side(x0 - 0.03, y0 - 0.03, y1 + 0.03, -sink, base, left=True),
               _flat(x0 - 0.03, x1 + 0.03, y0 - 0.03, y1 + 0.03, base)]
    _faces(mb, plinth, look["plinth"])
    walls = [_front(x0, -hx, base, h, y1), _front(hx, x1, base, h, y1), _front(-hx, hx, base, z_counter, y1),
             _front(-hx, hx, z_top, h, y1), _front(x0, x1, base, h, y0, back=True),
             _side(x1, y0, y1, base, h), _side(x0, y0, y1, base, h, left=True)]
    _faces(mb, walls, look["body"])
    inset = y1 - 0.12                                           # the hatch: reveals and the glass behind them
    _faces(mb, [_side(-hx, inset, y1, z_counter, z_top), _side(hx, inset, y1, z_counter, z_top, left=True),
                _flat(-hx, hx, inset, y1, z_top, down=True)], "kiosk_trim")
    _faces(mb, [_front(-hx, hx, z_counter, z_top, inset)], "glass_dark")
    _faces(mb, [_front(x0 - 0.01, x1 + 0.01, h - 0.12, h, y1 + 0.01), _front(x0 - 0.01, x0 + 0.07, base, h - 0.12, y1 + 0.01),
                _front(x1 - 0.07, x1 + 0.01, base, h - 0.12, y1 + 0.01)], "kiosk_trim")   # cornice band, corner posts
    roof = [_flat(x0 - 0.15, x1 + 0.15, y0 - 0.15, y1 + 0.15, h + 0.12),
            _flat(x0 - 0.15, x1 + 0.15, y0 - 0.15, y1 + 0.15, h, down=True),
            _front(x0 - 0.15, x1 + 0.15, h, h + 0.12, y1 + 0.15), _front(x0 - 0.15, x1 + 0.15, h, h + 0.12, y0 - 0.15, back=True),
            _side(x1 + 0.15, y0 - 0.15, y1 + 0.15, h, h + 0.12), _side(x0 - 0.15, y0 - 0.15, y1 + 0.15, h, h + 0.12, left=True)]
    _faces(mb, roof, "kiosk_trim")
    sx0, sx1, sy0, sy1, sz = -w / 2 + 0.1, w / 2 - 0.1, y1 - 0.06, y1 - 0.02, h + 0.36   # the sign board
    sign = [_front(sx0, sx1, h + 0.12, sz, sy1), _front(sx0, sx1, h + 0.12, sz, sy0, back=True), _flat(sx0, sx1, sy0, sy1, sz),
            _side(sx1, sy0, sy1, h + 0.12, sz), _side(sx0, sy0, sy1, h + 0.12, sz, left=True)]
    _faces(mb, sign, "kiosk_trim")
    _faces(mb, [_front(-w / 2 + 0.2, w / 2 - 0.2, h + 0.2, h + 0.28, y1 - 0.015)], look["band"])   # the name band
    counter = [_flat(-hx - 0.05, hx + 0.05, inset, y1 + 0.28, z_counter + 0.04),
               _flat(-hx - 0.05, hx + 0.05, inset, y1 + 0.28, z_counter, down=True),
               _front(-hx - 0.05, hx + 0.05, z_counter, z_counter + 0.04, y1 + 0.28),
               _side(hx + 0.05, y1, y1 + 0.28, z_counter, z_counter + 0.04),
               _side(-hx - 0.05, y1, y1 + 0.28, z_counter, z_counter + 0.04, left=True)]
    _faces(mb, counter, "wood")
    for k in range(5):                                          # folded papers in piles on the counter
        px = -hx + 0.12 + k * (2 * hx - 0.24) / 4
        mat = covers_of[int(rng.integers(len(covers_of)))]
        top = z_counter + 0.045 + 0.012 * (k % 3)
        _faces(mb, [_flat(px - 0.13, px + 0.13, y1 + 0.02, y1 + 0.24, top)], "plastic_white")
        _faces(mb, [_flat(px - 0.13, px + 0.13, y1 + 0.16, y1 + 0.24, top + 0.002)], mat)
    for sx in (-1.0, 1.0):                                      # magazine racks on both sides
        x = sx * (w / 2 + 0.02)
        covers: dict = {}
        for row, z in enumerate((1.05, 1.42, 1.79)):
            for col in range(4):
                yc = y0 + 0.2 + col * (d - 0.4) / 3
                q = _side(x, yc - 0.1, yc + 0.1, z, z + 0.29, left=sx < 0)
                covers.setdefault(covers_of[int(rng.integers(len(covers_of)))], []).append(q)
            covers.setdefault("iron", []).append(_side(x + sx * 0.01, y0 + 0.06, y1 - 0.06, z - 0.03, z, left=sx < 0))
        for mat, quads in covers.items():
            _faces(mb, quads, mat)
    stripes = 6                                                 # the awning: striped canvas, faces on both sides
    ya, yb, za, zb = y1 + 0.01, y1 + 0.75, h - 0.05, h - 0.42
    for k in range(stripes):
        sx0, sx1 = -w / 2 - 0.05 + k * (w + 0.1) / stripes, -w / 2 - 0.05 + (k + 1) * (w + 0.1) / stripes
        mat = look["stripes"][k % 2]
        add_sheet(mb, [[(sx0, ya, za), (sx0, yb, zb), (sx1, yb, zb)], [(sx0, ya, za), (sx1, yb, zb), (sx1, ya, za)],
                       [(sx0, yb, zb), (sx0, yb, zb - 0.16), (sx1, yb, zb - 0.16)], [(sx0, yb, zb), (sx1, yb, zb - 0.16), (sx1, yb, zb)]],
                  mat)
    for sx in (-1.0, 1.0):
        _bar(mb, (sx * (w / 2 - 0.02), y1, za - 0.55), (sx * (w / 2 + 0.03), yb - 0.02, zb + 0.01), 0.015, "iron")
    if not look["tobacco"]:
        return mb
    bx, by = x0 - 0.02, y1 - 0.08                               # the tobacco diamond on its bracket
    _bar(mb, (bx, by, h - 0.25), (bx - 0.32, by, h - 0.25), 0.015, "iron")
    add_cone(mb, bx - 0.3, by, h - 0.48, 0.09, 0.2, "awning_red", segments=4)
    ring = [(bx - 0.3 + 0.09 * math.cos(a), by + 0.09 * math.sin(a), h - 0.48) for a in np.arange(4) * math.pi / 2]
    add_triangles(mb, [[ring[(k + 1) % 4], ring[k], (bx - 0.3, by, h - 0.68)] for k in range(4)], "awning_red")
    return mb


def fountain_colonial(cfg: dict | None = None) -> MeshBuilder:
    """The round fountain of a colonial square: a marble basin on a sunken step with a broad rim, a turned
    column carrying a wide lower bowl and a small upper bowl, a finial, still water in the basin and the
    bowls and thin streams of water falling from each bowl's lip. About 740 triangles."""
    c = _cfg(cfg)
    r, top, sink = float(c["fountain_radius"]), float(c["fountain_height"]), float(c["sink"])
    k = top / 2.6                                               # the column and bowls scale with the height
    rim, wz = 0.3, 0.46
    mb = MeshBuilder()
    _lathe(mb, [(r + 0.35, -sink), (r + 0.35, 0.12), (r, 0.12), (r, 0.6), (r - rim, 0.6), (r - rim, wz)], "marble", 24)
    _lathe(mb, [(r - rim, wz), (0.0, wz)], "water_pool", 24)
    low, up = 1.0 * k, 0.48 * k
    z1, z2 = 1.28 * k, 1.95 * k
    _lathe(mb, [(0.34, wz - 0.02), (0.34, 0.62), (0.22, 0.78 * k), (0.17, 1.02 * k), (low - 0.05, z1 - 0.07),
                (low, z1 + 0.04), (low - 0.08, z1 + 0.04), (low - 0.08, z1)], "marble", 16)
    _lathe(mb, [(low - 0.08, z1), (0.0, z1)], "water_pool", 16)
    _lathe(mb, [(0.13, z1 - 0.01), (0.11, 1.75 * k), (up - 0.03, z2 - 0.04), (up, z2 + 0.03), (up - 0.05, z2 + 0.03),
                (up - 0.05, z2)], "marble", 12)
    _lathe(mb, [(up - 0.05, z2), (0.0, z2)], "water_pool", 12)
    _lathe(mb, [(0.07, z2 - 0.01), (0.07, z2 + 0.2), (0.12, z2 + 0.32), (0.0, top)], "iron", 8)
    _streams(mb, low + 0.01, z1 + 0.035, low + 0.32, wz + 0.005, 8)
    _streams(mb, up + 0.01, z2 + 0.025, up + 0.22, z1 + 0.005, 6)
    return mb


def sabil(cfg: dict | None = None) -> MeshBuilder:
    """A tiled wall fountain (sabil): a sandstone frame standing out from the wall around an arched niche
    lined with blue and white faience, faience strips on its jambs, a tiled band under a marble cornice,
    a brass spout with its thin stream and a small marble basin of still water. The origin is on the wall
    face at street level; about 330 triangles."""
    c = _cfg(cfg)
    w, h = (float(v) for v in c["sabil"])
    sink, depth = float(c["sink"]), 0.16
    nw, n0 = 1.1, 0.32                                          # niche width and sill
    niche = Polygon([(x, z + n0) for x, z in _arch_outline(nw, 2.0)])
    mb = MeshBuilder()
    _slab(mb, box(-w / 2, -sink, w / 2, h).difference(niche), 0.0, depth, "stone_frame")
    _plate(mb, niche, 0.012, "tile_panel")
    tile, cols = nw / 8, 8                                      # the niche's faience: a white field in a blue border
    rows = int((2.0 - nw / 2 - 0.66 + n0) // tile)
    white = []
    for i in range(1, cols - 1):
        for j in range(1, rows - 1):
            if (i + j) % 2 == 0:
                xa, za = -nw / 2 + i * tile, 0.66 + j * tile
                white.append(_front(xa + 0.008, xa + tile - 0.008, za + 0.008, za + tile - 0.008, 0.02))
    _faces(mb, white, "faience_white")
    jamb, step = (w - nw) / 4, 0.16                             # strips on both jambs, alternating tiles
    strips = {"tile_panel": [], "faience_white": []}
    for sx in (-1.0, 1.0):
        xc = sx * (nw / 2 + (w - nw) / 4)
        for m in range(int((2.0 + n0 - 0.2) // step)):
            z = 0.2 + m * step
            strips["tile_panel" if m % 2 == 0 else "faience_white"].append(
                _front(xc - jamb / 2, xc + jamb / 2, z, z + step, depth + 0.004))
    band = h - 0.42                                             # the tiled band under the cornice
    for m in range(9):
        xa = -w / 2 + 0.08 + m * (w - 0.16) / 9
        strips["tile_panel" if m % 2 == 0 else "faience_white"].append(
            _front(xa, xa + (w - 0.16) / 9, band, band + 0.22, depth + 0.004))
    for mat, quads in strips.items():
        _faces(mb, quads, mat)
    cor = [_flat(-w / 2 - 0.08, w / 2 + 0.08, -0.02, depth + 0.12, h + 0.12),
           _flat(-w / 2 - 0.08, w / 2 + 0.08, 0.0, depth + 0.12, h, down=True),
           _front(-w / 2 - 0.08, w / 2 + 0.08, h, h + 0.12, depth + 0.12),
           _side(w / 2 + 0.08, 0.0, depth + 0.12, h, h + 0.12), _side(-w / 2 - 0.08, 0.0, depth + 0.12, h, h + 0.12, left=True)]
    _faces(mb, cor, "marble")
    _faces(mb, [_front(-0.09, 0.09, 1.02, 1.2, 0.03)], "copper")   # the spout's rosette and spout
    _bar(mb, (0.0, 0.03, 1.12), (0.0, 0.25, 1.08), 0.022, "copper")
    bx, by, bz, wz = 0.48, 0.5, 0.64, 0.58                       # the basin, its water just under the rim
    add_sheet(mb, [[(-0.012, 0.255, 1.07), (-0.012, 0.27, wz), (0.012, 0.27, wz)],
                   [(-0.012, 0.255, 1.07), (0.012, 0.27, wz), (0.012, 0.255, 1.07)]], "water_pool", 0.004)
    ri = 0.07
    basin = [_front(-bx, bx, -sink, bz, by), _side(bx, 0.0, by, -sink, bz), _side(-bx, 0.0, by, -sink, bz, left=True),
             _flat(-bx, bx, by - ri, by, bz), _flat(-bx, bx, 0.0, ri, bz), _flat(-bx, -bx + ri, ri, by - ri, bz),
             _flat(bx - ri, bx, ri, by - ri, bz),
             _front(-bx + ri, bx - ri, wz, bz, ri), _front(-bx + ri, bx - ri, wz, bz, by - ri, back=True),
             _side(-bx + ri, ri, by - ri, wz, bz), _side(bx - ri, ri, by - ri, wz, bz, left=True)]
    _faces(mb, basin, "marble")
    _faces(mb, [_flat(-bx + ri, bx - ri, ri, by - ri, wz)], "water_pool")
    return mb


def _tube(mb: MeshBuilder, p0, p1, half: tuple, mat: str, cap: bool = False) -> None:
    """A thin straight bar of rectangular section (`half` = half sizes across), four sides sharing their
    corners (8 vertices, smooth normals: at a few centimeters the bar reads round), open ends unless `cap`
    (the top end closed)."""
    p0, p1 = np.asarray(p0, dtype=np.float64), np.asarray(p1, dtype=np.float64)
    d = (p1 - p0) / max(float(np.linalg.norm(p1 - p0)), 1e-9)
    a = np.cross(d, [0.0, 0.0, 1.0] if abs(d[2]) < 0.9 else [0.0, 1.0, 0.0])
    a /= np.linalg.norm(a)
    b = np.cross(d, a)
    ring = [a * half[0] + b * half[1], -a * half[0] + b * half[1], -a * half[0] - b * half[1], a * half[0] - b * half[1]]
    pos = np.array([p0 + r for r in ring] + [p1 + r for r in ring])
    nrm = np.array([r / np.linalg.norm(r) for r in ring] * 2)
    s = np.concatenate([np.zeros(4), np.full(4, float(np.linalg.norm(p1 - p0)))])
    uv = np.stack([s, np.tile(np.arange(4) * 0.02, 2)], axis=1)
    tris = [[k, (k + 1) % 4, 4 + (k + 1) % 4] for k in range(4)] + [[k, 4 + (k + 1) % 4, 4 + k] for k in range(4)]
    tris = np.array(tris)
    if np.dot(np.cross(pos[1] - pos[0], pos[5] - pos[0]), ring[0] + ring[1]) < 0:   # faces outward
        tris = tris[:, ::-1]
    mb.add(mat, pos, nrm, uv, tris)
    if cap:
        top = (p1 + np.array(ring)).tolist()
        _faces(mb, [top if np.cross(np.subtract(top[1], top[0]), np.subtract(top[3], top[0])) @ d > 0 else top[::-1]], mat)


def railing_sea(cfg: dict | None = None) -> MeshBuilder:
    """One length of the corniche's white-painted iron railing (prompt 36): a flat handrail, a bottom rail and
    plain balusters between them, carried by half posts at both ends (two lengths side by side make one post).
    Its x runs along the sea edge; placements stretch it to fit (`Placement.stretch`). Thin bars share their
    corners, so the piece stays small (about 180 vertices)."""
    c = _cfg(cfg)
    half, height = float(c["railing_length"]) / 2, float(c["railing_height"])
    mb = MeshBuilder()
    m = "railing_white"
    low = 0.1
    _tube(mb, (-half, 0.0, height - 0.025), (half, 0.0, height - 0.025), (0.04, 0.025), m)    # handrail
    _tube(mb, (-half, 0.0, low), (half, 0.0, low), (0.015, 0.02), m)                           # bottom rail
    for x in (-half + 0.015, half - 0.015):                                                    # half posts
        _tube(mb, (x, 0.0, -0.06), (x, 0.0, height + 0.02), (0.015, 0.035), m, cap=True)
    count = max(2, int(round(2 * half / 0.125)))
    for x in np.linspace(-half, half, count + 1)[1:-1]:                                        # balusters
        _tube(mb, (x, 0.0, low + 0.02), (x, 0.0, height - 0.05), (0.008, 0.008), m)
    return mb


def parasol(cfg: dict | None = None) -> MeshBuilder:
    """A cafe parasol standing in a table's hole (prompt 37): a wooden pole from just under the table top, an
    octagonal canvas (CANVAS) in a gentle dome with a short valance round its rim, both with real faces on both
    sides (thin cloth rule), eight iron stretchers from a runner on the pole to the canopy's ribs, and a finial.
    Radius, rim and top heights, pole bottom: `parasol` in `[dressing.furniture]`; about 170 triangles."""
    c = _cfg(cfg)
    radius, rim, top, foot = (float(v) for v in c["parasol"])
    drop, sides = float(c["parasol_valance"]), 8
    mb = MeshBuilder()
    _tube(mb, (0.0, 0.0, foot), (0.0, 0.0, top + 0.05), (0.022, 0.022), "wood", cap=True)
    a = (np.arange(sides) + 0.5) * 2 * math.pi / sides
    ring = np.stack([np.cos(a), np.sin(a), np.zeros(sides)], 1)
    mid_r, mid_z = 0.5 * radius, rim + 0.55 * (top - rim)         # a little fuller than a cone
    apex = np.array([0.0, 0.0, top])
    mid = ring * mid_r + [0.0, 0.0, mid_z]
    edge = ring * radius + [0.0, 0.0, rim]
    m, e = 1 + np.arange(sides), 1 + sides + np.arange(sides)
    nxt = np.roll(np.arange(sides), -1)
    tris = np.concatenate([np.stack([np.zeros(sides, int), m, m[nxt]], 1),          # counter-clockwise from above
                           np.stack([m, e, e[nxt]], 1), np.stack([m, e[nxt], m[nxt]], 1)])
    _soft_sheet(mb, np.vstack([apex, mid, edge]), tris, 0.012)
    low = edge - [0.0, 0.0, drop]
    i = np.arange(sides)
    flaps = np.concatenate([np.stack([i, sides + i, sides + nxt], 1), np.stack([i, sides + nxt, nxt], 1)])   # facing out
    _soft_sheet(mb, np.vstack([edge, low]), flaps, 0.008)
    runner = rim - 0.32
    for k in range(sides):
        rib = mid[k] * 0.98 + [0.0, 0.0, -0.03]
        _tube(mb, (0.0, 0.0, runner), rib, (0.008, 0.008), "iron")
    add_cone(mb, 0.0, 0.0, top + 0.05, 0.035, 0.09, "wood", segments=4)
    return mb


def _soft_sheet(mb: MeshBuilder, pos: np.ndarray, tris: np.ndarray, thickness: float) -> None:
    """A smooth-shaded canvas sharing its corners (CANVAS), with its back as real faces `thickness` behind it."""
    face = np.cross(pos[tris[:, 1]] - pos[tris[:, 0]], pos[tris[:, 2]] - pos[tris[:, 0]])
    nrm = np.zeros_like(pos)
    for c in range(3):
        np.add.at(nrm, tris[:, c], face)
    nrm /= np.maximum(np.linalg.norm(nrm, axis=1), 1e-12)[:, None]
    uv = np.zeros((len(pos), 2))
    mb.add(CANVAS, pos, nrm, uv, tris)
    mb.add(CANVAS, pos - nrm * thickness, -nrm, uv, tris[:, ::-1])


def parasol_pieces(cfg: dict | None) -> dict:
    """{name: glTF parts} of the parasols, one piece per canvas color in `parasol_colors` (instancing cannot
    recolor): the pieces share every part dict but the canvas, so a tile writes the pole and ribs once; no UVs."""
    c = _cfg(cfg)
    colors = [str(v) for v in c.get("parasol_colors", [])]
    if not colors:
        return {}
    shared = {m: {**part, "uv": None} for m, part in parasol(c).gltf_parts().items()}
    return {color: {(color if m == CANVAS else m): part for m, part in shared.items()} for color in colors}


def _plain(mb: MeshBuilder) -> dict:
    """glTF parts without UVs, for a piece drawn in plain palette colors."""
    return {m: {**part, "uv": None} for m, part in mb.gltf_parts().items()}


def furniture_pieces(seed: int, cfg: dict | None) -> dict:
    """{name: (MeshBuilder, category, anchor)} of the furniture pieces; only the kiosk draws randomness, on its
    own stream."""
    return {
        "bench_iron": (bench_iron(cfg), "bench", "ground"),
        "kiosk": (kiosk(seed, cfg), "kiosk", "ground"),
        "kiosk_drinks": (_plain(kiosk(seed, cfg, CAFE_KIOSK)), "kiosk", "ground"),   # the corniche's cafe kiosks (prompt 37)
        "fountain_colonial": (fountain_colonial(cfg), "fountain", "ground"),
        "sabil": (sabil(cfg), "fountain", "wall"),
        "railing_sea": (railing_sea(cfg), "railing", "ground"),   # the corniche's railing (prompt 36)
    }
