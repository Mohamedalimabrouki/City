"""The traditional pieces of the home kit (prompt 52, SPEC 6d "Catalog: traditional homes").

Piece frame as 6b and 6d: x along the wall, front +y (into the room), z up, meters. `wall` pieces stand in
front of the wall face (every y >= 0, x centered), `floor` and `on` pieces are centered on their origin
at the bottom, a hanging piece keeps its height in its own mesh (a mirror starts at z 1.15). Stretch
pieces are 1.0 m long (their x is scaled by `Placement.stretch`).

Round things are lathed (`mesh/furniture._lathe`, smooth around); boxes show only the faces a person can
see (no bottoms on the floor, no backs on the wall); cloth is `add_sheet` (both sides). A piece's random
details (a sack's lean, which glasses stand on the tray) draw only on `stream(seed, "piece", "home/<name>")`.
"""
from __future__ import annotations

import math

import numpy as np
from shapely.geometry import Polygon

from ..mesh.builder import MeshBuilder, add_sheet, add_triangles, triangulate
from ..mesh.furniture import _lathe, _tube
from ..mesh.props import _arch_outline, _faces, _slab
from ..rng import stream

# name: (category, anchor, (W, D, H), tris, extra); extra: stretch [least, most], z0 (hanging pieces),
# top (what things stand on), use (the depth a person needs in front). Variants share their base's row
# unless VARIANT_SIZES gives them their own size.
TABLE = {
    "doukkana": ("seat", "wall", (1.0, 0.80, 0.40), 24, {"stretch": (0.8, 4.0), "top": 0.40, "use": 0.4}),
    "mattress": ("seat", "on", (1.0, 0.78, 0.12), 30, {"stretch": (0.8, 4.0), "top": 0.12}),
    "cushion": ("seat", "wall", (0.55, 0.18, 0.42), 40, {"z0": 0.52}),
    "mattress_floor": ("bed", "wall", (0.90, 1.90, 0.12), 30, {"use": 0.5, "top": 0.12}),
    "mattress_stack": ("storage", "wall", (0.90, 0.60, 0.55), 60, {"use": 0.6, "top": 0.55}),
    "sedda": ("bed", "wall", (1.50, 2.00, 2.30), 520, {"use": 0.5}),
    "sedda_plain": ("bed", "wall", (1.40, 1.95, 0.95), 180, {"use": 0.5}),
    "meida": ("table", "floor", (0.70, 0.70, 0.32), 96, {"top": 0.32}),
    "tray_table": ("table", "floor", (0.80, 0.80, 0.45), 140, {"top": 0.45}),
    "pouf": ("seat", "floor", (0.50, 0.50, 0.35), 64, {}),
    "sendouk": ("storage", "wall", (1.10, 0.55, 0.62), 220, {"use": 0.6, "top": 0.62}),
    "khzana": ("storage", "wall", (1.20, 0.45, 2.05), 160, {"use": 0.6}),
    "shelf_wall": ("storage", "wall", (1.0, 0.25, 0.25), 36, {"stretch": (0.6, 2.4), "z0": 1.70, "top": 1.86}),
    "mirror_carved": ("decor", "wall", (0.65, 0.05, 0.90), 120, {"z0": 1.15}),
    "tray_brass": ("small", "on", (0.60, 0.60, 0.03), 80, {"top": 0.01}),
    "tea_set": ("small", "on", (0.35, 0.25, 0.22), 160, {}),
    "ibrik": ("small", "floor", (0.35, 0.35, 0.40), 120, {}),
    "kanoun": ("kitchen", "floor", (0.34, 0.34, 0.24), 80, {"top": 0.24}),
    "couscoussier": ("kitchen", "on", (0.34, 0.34, 0.52), 140, {}),
    "counter_masonry": ("kitchen", "wall", (1.0, 0.55, 0.80), 30, {"stretch": (0.8, 3.0), "top": 0.80, "use": 0.6}),
    "gas_ring": ("kitchen", "on", (0.60, 0.35, 0.12), 70, {"top": 0.12}),
    "butane": ("kitchen", "floor", (0.30, 0.30, 0.58), 64, {}),
    "sink_stone": ("kitchen", "wall", (0.70, 0.50, 0.85), 60, {"use": 0.6}),
    "qolla": ("kitchen", "floor", (0.35, 0.35, 0.75), 110, {}),
    "gsaa": ("kitchen", "on", (0.60, 0.60, 0.12), 48, {}),
    "kursi": ("seat", "floor", (0.32, 0.32, 0.22), 40, {}),
    "khabia": ("storage", "floor", (0.55, 0.55, 0.85), 120, {}),
    "grain_sacks": ("storage", "wall", (0.90, 0.50, 0.70), 90, {}),
    "tabouna": ("kitchen", "floor", (0.70, 0.70, 0.60), 110, {"use": 0.6}),
    "klim": ("rug", "floor", (1.40, 2.20, 0.01), 10, {}),
    "mergoum": ("rug", "floor", (1.20, 2.00, 0.01), 10, {}),
    "zarbia": ("rug", "floor", (2.00, 3.00, 0.015), 10, {}),
    "hasira": ("rug", "floor", (1.80, 2.60, 0.01), 10, {}),
    "hidoura": ("rug", "floor", (0.80, 1.10, 0.02), 126, {}),
    "sajjada": ("rug", "floor", (0.65, 1.15, 0.01), 10, {}),
    "rahla": ("work", "floor", (0.32, 0.25, 0.35), 70, {}),
    "loom": ("work", "wall", (1.60, 0.80, 2.20), 300, {"use": 0.8}),
    "wool_basket": ("work", "floor", (0.50, 0.50, 0.40), 80, {}),
    "sewing_machine": ("work", "wall", (0.90, 0.50, 0.95), 260, {"use": 0.6}),
    "dummy": ("work", "floor", (0.40, 0.35, 1.55), 120, {}),
    "chechia_forms": ("work", "wall", (0.80, 0.40, 0.95), 160, {"use": 0.6}),
    "pots_stack": ("work", "floor", (0.60, 0.60, 0.70), 180, {}),
    "net_pile": ("work", "floor", (1.00, 0.80, 0.35), 80, {}),
    "skifa_bench": ("seat", "wall", (1.0, 0.45, 0.45), 24, {"stretch": (0.8, 3.0), "use": 0.4}),
    "wc_turkish": ("bath", "wall", (0.50, 0.70, 0.05), 40, {}),
    "tap_wall": ("bath", "wall", (0.10, 0.12, 0.15), 30, {"z0": 0.55}),
    "bucket": ("bath", "floor", (0.30, 0.30, 0.32), 48, {}),
    "lota": ("bath", "floor", (0.15, 0.15, 0.22), 40, {}),
    "basin_washing": ("bath", "floor", (0.65, 0.65, 0.22), 48, {}),
}
VARIANTS = {   # base: its suffixes (each its own piece home/<base>_<suffix>)
    "doukkana": ("plain", "zellige"), "mattress": ("ticking", "red", "green", "blue"),
    "cushion": ("red", "green", "blue", "gold"), "mattress_floor": ("ticking", "mink"),
    "sedda": ("painted", "walnut"), "meida": ("walnut", "painted", "large"),
    "sendouk": ("green", "red", "walnut"), "khzana": ("green", "red", "walnut"),
    "mirror_carved": ("gilt", "painted"), "tea_set": ("brass", "alu"), "khabia": ("large", "small", "glazed"),
    "klim": ("red", "indigo", "large_red", "large_indigo"),
}
VARIANT_SIZES = {"meida_large": (0.90, 0.90, 0.32), "khabia_small": (0.38, 0.38, 0.55),
                 "klim_large_red": (2.00, 3.00, 0.01), "klim_large_indigo": (2.00, 3.00, 0.01)}
SIZES = {**{b: row[2] for b, row in TABLE.items()}, **VARIANT_SIZES}   # `[interiors.furnish.sizes]` overrides
VELVET = {"red": "velvet_red", "green": "velvet_green", "blue": "velvet_blue", "gold": "velvet_gold"}
PAINTED = {"green": "wood_painted_green", "red": "wood_painted_red", "walnut": "wood_walnut"}
RUG_Z = 0.005   # rugs lie this far over the floor
REPEAT = {"klim_red": (1.4, 2.2), "klim_indigo": (1.4, 2.2), "mergoum": (1.2, 2.0), "zarbia": (2.0, 3.0),
          "sajjada": (0.65, 1.15)}   # their `texture_size`: the UVs span exactly one repeat (prompt 53 fix)


# --- helpers ------------------------------------------------------------------------------------------

def _oriented(poly, normal) -> list:
    """A flat polygon (corners in order) turned so its face looks along `normal`."""
    p = np.asarray(poly, dtype=np.float64)
    n = np.cross(p[1] - p[0], p[2] - p[0])
    if len(p) > 3 and np.linalg.norm(n) < 1e-12:
        n = np.cross(p[2] - p[0], p[3] - p[1])
    return p[::-1].tolist() if float(np.dot(n, normal)) < 0 else p.tolist()


def _box(mb: MeshBuilder, x0, x1, y0, y1, z0, z1, mat: str, skip: str = "b") -> None:
    """A box showing its top (t), bottom (b), front +y (f), back -y (k), left -x (l) and right +x (r)
    faces, less those in `skip` (default the bottom, which stands on something)."""
    faces = {"t": ([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], (0, 0, 1)),
             "b": ([(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)], (0, 0, -1)),
             "f": ([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], (0, 1, 0)),
             "k": ([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], (0, -1, 0)),
             "l": ([(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)], (-1, 0, 0)),
             "r": ([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], (1, 0, 0))}
    _faces(mb, [_oriented(q, n) for k, (q, n) in faces.items() if k not in skip], mat)


def _prism(mb: MeshBuilder, prof, x0: float, x1: float, mats, cap: str | None) -> None:
    """A profile [(y, z), ...] (closed by its last-to-first edge, which is left open: the wall or the
    floor) swept along x from x0 to x1; `mats` gives each edge's material (one string for all, None: not drawn),
    `cap` the end faces' (None: open ends)."""
    prof = [tuple(map(float, p)) for p in prof]
    ring = Polygon(prof)
    sign = 1.0 if ring.exterior.is_ccw else -1.0
    mats = [mats] * (len(prof) - 1) if isinstance(mats, str) else list(mats)
    for (ya, za), (yb, zb), mat in zip(prof[:-1], prof[1:], mats):
        if mat is None:              # an edge on the floor or under an overhang nobody sees
            continue
        out = np.array([0.0, (zb - za) * sign, -(yb - ya) * sign])    # the right of a counter-clockwise ring
        _faces(mb, [_oriented([(x0, ya, za), (x1, ya, za), (x1, yb, zb), (x0, yb, zb)], out)], mat)
    if cap:
        for tri in triangulate(ring):
            for x, nx in ((x0, -1.0), (x1, 1.0)):
                add_triangles(mb, [_oriented([(x, y, z) for y, z in tri], (nx, 0, 0))], cap)


def _smooth(mb: MeshBuilder, mat: str, pos, tris, uv=None) -> None:
    """Triangles sharing their corners, with area-weighted smooth normals (cushions, sacks, the net);
    meter UVs (x + y, -z) unless `uv` gives them."""
    pos, tris = np.asarray(pos, dtype=np.float64), np.asarray(tris, dtype=np.int64)
    n = np.zeros_like(pos)
    face = np.cross(pos[tris[:, 1]] - pos[tris[:, 0]], pos[tris[:, 2]] - pos[tris[:, 0]])
    for k in range(3):
        np.add.at(n, tris[:, k], face)
    n /= np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]
    uv = np.stack([pos[:, 0] + pos[:, 1], -pos[:, 2]], axis=1) if uv is None else uv
    mb.add(mat, pos, n, uv, tris)


def _ring(cx, cy, cz, rx, ry, count: int, phase: float = 0.0) -> np.ndarray:
    t = phase + np.arange(count) * 2 * math.pi / count
    return np.stack([cx + rx * np.cos(t), cy + ry * np.sin(t), np.full(count, float(cz))], axis=1)


def _lathed(mb: MeshBuilder, profile, mat, segments: int, at=(0.0, 0.0, 0.0), scale=(1.0, 1.0),
            turn: float = 0.0) -> None:
    """`_lathe` turned `turn` radians about z, scaled across (x, y) and moved to `at`; `mat` is one material
    or one per profile edge."""
    mats = [mat] * (len(profile) - 1) if isinstance(mat, str) else list(mat)
    for (p, q), m in zip(zip(profile[:-1], profile[1:]), mats):
        tmp = MeshBuilder()
        _lathe(tmp, [p, q], m, segments)
        for name, (pos, nrm, uv, tris, _n, _c) in tmp._parts.items():
            pos, nrm = np.concatenate(pos), np.concatenate(nrm)
            if turn:
                rot = np.array([[math.cos(turn), -math.sin(turn), 0.0], [math.sin(turn), math.cos(turn), 0.0], [0, 0, 1]])
                pos, nrm = pos @ rot.T, nrm @ rot.T
            pos = pos * [scale[0], scale[1], 1.0] + at
            nrm = nrm / [scale[0], scale[1], 1.0]
            nrm /= np.maximum(np.linalg.norm(nrm, axis=1), 1e-12)[:, None]
            mb.add(name, pos, nrm, np.concatenate(uv), np.concatenate(tris))


def _moved(mb: MeshBuilder, tmp: MeshBuilder, m, at=(0.0, 0.0, 0.0)) -> None:
    """Add what `tmp` holds to `mb` through the 3 x 3 matrix `m` and the offset `at` (normals follow; a
    mirroring matrix turns the triangles over so they still face out)."""
    m = np.asarray(m, dtype=np.float64)
    flip = np.linalg.det(m) < 0
    for name, (pos, nrm, uv, tris, _n, _c) in tmp._parts.items():
        pos = np.concatenate(pos) @ m.T + at
        nrm = np.concatenate(nrm) @ np.linalg.inv(m)
        nrm /= np.maximum(np.linalg.norm(nrm, axis=1), 1e-12)[:, None]
        tris = np.concatenate(tris)
        mb.add(name, pos, nrm, np.concatenate(uv), tris[:, ::-1] if flip else tris)


SWAP_XZ = ((0, 0, 1), (0, 1, 0), (1, 0, 0))   # a lathe's axis laid along x
SWAP_YZ = ((1, 0, 0), (0, 0, 1), (0, 1, 0))   # a standing cushion laid flat


def _soft(mb: MeshBuilder, tmp: MeshBuilder) -> None:
    """Add what `tmp` holds with its coincident corners welded and smooth normals along the profile too (a
    lathe alone is smooth only round its axis, so a dress form showed bands)."""
    for name, (pos, _nrm, _uv, tris, _n, _c) in tmp._parts.items():
        pos, tris = np.concatenate(pos), np.concatenate(tris)
        key, inverse = np.unique(np.round(pos, 6), axis=0, return_inverse=True)
        _smooth(mb, name, key, inverse.reshape(-1)[tris])


def _pyramid(mb: MeshBuilder, base, apex, mat: str) -> None:
    """Sides of a pyramid from a base ring to an apex (no base face): a stud, a tassel, a valve."""
    base, apex = np.asarray(base, dtype=np.float64), np.asarray(apex, dtype=np.float64)
    c = base.mean(axis=0)
    tris = []
    for a, b in zip(base, np.roll(base, -1, axis=0)):
        mid = (a + b + apex) / 3
        tris.append(_oriented([a, b, apex], mid - c))
    add_triangles(mb, tris, mat)


def _disc(mb: MeshBuilder, r: float, z: float, segments: int, mat: str) -> None:
    """A flat round top seen from above, with planar meter UVs (a lathe's run round, which would smear a
    painted pattern)."""
    ring = _ring(0.0, 0.0, z, r, r, segments)
    pos = np.concatenate([[[0.0, 0.0, z]], ring])
    tris = [[0, 1 + k, 1 + (k + 1) % segments] for k in range(segments)]
    mb.add(mat, pos, np.tile([0.0, 0.0, 1.0], (len(pos), 1)), np.stack([pos[:, 0], -pos[:, 1]], axis=1), tris)


def _rug(mb: MeshBuilder, w: float, d: float, h: float, mat: str, repeat=None) -> None:
    """A flat rug 0.005 m over the floor: its top and four edges (10 triangles). `repeat` (meters of one
    image repeat, its `texture_size`) maps the whole rug to exactly one repeat; else meter UVs."""
    x0, x1, y0, y1, z0, z1 = -w / 2, w / 2, -d / 2, d / 2, RUG_Z, RUG_Z + h
    tmp = MeshBuilder()
    _box(tmp, x0, x1, y0, y1, z0, z1, mat)
    for name, (pos, nrm, uv, tris, _n, _c) in tmp._parts.items():
        pos = np.concatenate(pos)
        uv = np.stack([pos[:, 0], -pos[:, 1]], axis=1) if repeat is None else \
            np.stack([(pos[:, 0] - x0) / w * repeat[0], -(pos[:, 1] - y0) / d * repeat[1]], axis=1)
        mb.add(name, pos, np.concatenate(nrm), uv, np.concatenate(tris))


def _pillow(mb: MeshBuilder, mat: str, w: float, h: float, z0: float, back: float, mid: float, front: float,
            lean: float = 0.0) -> None:
    """A soft cushion standing against the wall: a rounded outline (octagon) `mid` m out, the back pressed
    flat at `back`, the front domed to `front`, the top leaning `lean` m back (32 triangles)."""
    zc = z0 + h / 2
    c = 0.30
    out = [(w / 2, 0.0), (w / 2, h / 2 * (1 - c)), (w / 2 * (1 - c * 0.8), h / 2), (-w / 2 * (1 - c * 0.8), h / 2),
           (-w / 2, h / 2 * (1 - c)), (-w / 2, 0.0), (-w / 2, -h / 2 * (1 - c)), (-w / 2 * (1 - c * 0.8), -h / 2),
           (w / 2 * (1 - c * 0.8), -h / 2), (w / 2, -h / 2 * (1 - c))]
    out = [p for k, p in enumerate(out) if k not in (0, 5)]   # 8 corners
    k = len(out)
    pts = [(x, mid, zc + z) for x, z in out] + [(x * 0.82, front - 0.03, zc + z * 0.82) for x, z in out]
    pts += [(0.0, front, zc), (0.0, back, zc)]
    pos = np.array(pts)
    pos[:, 1] -= lean * (pos[:, 2] - zc) / (h / 2)
    tris = []
    for i in range(k):
        j = (i + 1) % k
        tris += [[i, k + i, k + j], [i, k + j, j], [k + i, 2 * k, k + j], [i, j, 2 * k + 1]]
    tris = np.array(tris)
    centre = pos[:2 * k].mean(axis=0)
    for t in range(len(tris)):     # every face looks out of the cushion
        a, b, cc = pos[tris[t]]
        if np.dot(np.cross(b - a, cc - a), (a + b + cc) / 3 - centre) < 0:
            tris[t] = tris[t][::-1]
    _smooth(mb, mat, pos, tris)


def _pad(mb: MeshBuilder, x0, x1, y0, y1, z0, z1, mat: str, bevel: float, skip: str = "") -> None:
    """A mattress-like block whose top edges are bevelled (18 triangles without a bottom): the top inset
    by `bevel`, four chamfers, four sides."""
    zb = z1 - bevel
    top = [(x0 + bevel, y0 + bevel, z1), (x1 - bevel, y0 + bevel, z1), (x1 - bevel, y1 - bevel, z1), (x0 + bevel, y1 - bevel, z1)]
    low = [(x0, y0, zb), (x1, y0, zb), (x1, y1, zb), (x0, y1, zb)]
    quads = [_oriented(top, (0, 0, 1))]
    for k, n in zip(range(4), [(0, -1, 1), (1, 0, 1), (0, 1, 1), (-1, 0, 1)]):
        quads.append(_oriented([low[k], low[(k + 1) % 4], top[(k + 1) % 4], top[k]], n))
    _faces(mb, quads, mat)
    _box(mb, x0, x1, y0, y1, z0, zb, mat, "bt" + skip)


# --- seats, beds and textiles -------------------------------------------------------------------------

def doukkana(s, v, rng):
    """The plastered masonry bench of a bit: a box whose front edge is rounded, a zellige band on the
    front of the `_zellige` one (24 triangles)."""
    w, d, h = s
    band = "zellige" if v == "zellige" else "plaster_inner"
    prof = [(0.0, h), (d - 0.08, h), (d - 0.022, h - 0.015), (d, h - 0.06), (d, h - 0.10), (d, 0.06), (d, 0.0), (0.0, 0.0)]
    mb = MeshBuilder()
    _prism(mb, prof, -w / 2, w / 2, ["plaster_inner"] * 4 + [band, "plaster_inner", None], "plaster_inner")
    return mb


def mattress(s, v, rng):
    """The doukkana's mattress: a bevelled pad with a piped front edge (velvet_gold on velvet, its own
    ticking on ticking), 26 triangles."""
    w, d, h = s
    mat = "ticking" if v == "ticking" else VELVET[v]
    mb = MeshBuilder()
    _pad(mb, -w / 2, w / 2, -d / 2, d / 2, 0.0, h, mat, 0.025)
    pipe = "ticking" if v == "ticking" else "velvet_gold"
    _tube(mb, (-w / 2, d / 2 - 0.004, h - 0.026), (w / 2, d / 2 - 0.004, h - 0.026), (0.008, 0.008), pipe)
    return mb


def cushion(s, v, rng):
    """A soft back cushion leaning on the wall over the doukkana: a rounded outline (a superellipse, as a
    stuffed cover rounds its corners), the back nearly flat, the front gently domed, smooth normals; a
    gold tassel (red on a gold cushion) at each top corner, long enough to read from a meter (38)."""
    w, d, h = s
    z0 = TABLE["cushion"][4]["z0"]
    zc = z0 + h / 2
    k = 8
    a = math.radians(22.5) + np.arange(k) * 2 * math.pi / k
    c, sn = np.cos(a), np.sin(a)
    ox = np.sign(c) * np.sqrt(np.abs(c)) / math.sqrt(math.cos(math.radians(22.5)))   # reaches +-1
    oz = np.sign(sn) * np.sqrt(np.abs(sn)) / math.sqrt(math.cos(math.radians(22.5)))
    hw, hh = w / 2 - 0.005, h / 2 - 0.003
    mid = np.stack([ox * hw, np.full(k, 0.08), zc + oz * hh], axis=1)
    front = np.stack([ox * hw * 0.70, np.full(k, 0.155), zc + oz * hh * 0.70], axis=1)
    pos = np.concatenate([mid, front, [[0.0, 0.18, zc], [0.0, 0.0, zc]]])
    lean = 0.035                                      # the top rests on the wall, the foot comes forward
    pos[:, 1] += lean * (1.0 - (pos[:, 2] - z0) / h)
    pos[:, 1] = (pos[:, 1] - pos[:, 1].min()) / (pos[:, 1].max() - pos[:, 1].min()) * (d - 0.004)
    tris = []
    for i in range(k):
        j = (i + 1) % k
        tris += [[i, k + j, k + i], [i, j, k + j], [k + i, k + j, 2 * k], [i, 2 * k + 1, j]]
    tris = np.array(tris)
    centre = pos[:2 * k].mean(axis=0)
    for n in range(len(tris)):     # every face looks out of the cushion
        p0, p1, p2 = pos[tris[n]]
        if np.dot(np.cross(p1 - p0, p2 - p0), (p0 + p1 + p2) / 3 - centre) < 0:
            tris[n] = tris[n][::-1]
    mb = MeshBuilder()
    _smooth(mb, VELVET[v], pos, tris)
    tassel = "velvet_red" if v == "gold" else "velvet_gold"
    for sx in (-1, 1):
        corner = np.array([sx * hw * 0.86, 0.06, zc + hh * 0.86])
        tip = corner + np.array([sx * 0.03, 0.01, -0.06])     # hangs from the corner
        ring = _ring(corner[0], corner[1], corner[2], 0.016, 0.016, 3)
        _pyramid(mb, ring, tip, tassel)
        add_triangles(mb, [_oriented(ring, (0, 0, 1))], tassel)          # its top, seen from above
    return mb


def mattress_floor(s, v, rng):
    """The floor mattress of children and poor homes, lying along the wall; `_mink` with a folded mink
    blanket over its foot."""
    w, d, h = s
    mb = MeshBuilder()
    _pad(mb, -w / 2, w / 2, 0.0, d, 0.0, h - 0.01, "ticking", 0.02)
    if v == "mink":
        _box(mb, -w / 2 + 0.01, w / 2 - 0.01, d * 0.45, d - 0.005, h - 0.03, h, "mink", "bk")
    else:
        _tube(mb, (-w / 2, d - 0.004, h - 0.03), (w / 2, d - 0.004, h - 0.03), (0.007, 0.007), "ticking")
    return mb


def mattress_stack(s, v, rng):
    """The day-time pile of folded mattresses and blankets, each layer a little askew."""
    w, d, h = s
    layers = [("ticking", 0.14), ("mink", 0.07), ("ticking", 0.13), ("velvet_red", 0.10), ("mink", 0.11)]
    mb = MeshBuilder()
    z = 0.0
    shift = rng.uniform(-1.0, 1.0, (len(layers), 2))
    for k, (mat, t) in enumerate(layers):
        inset = 0.0 if k == 0 else 0.015 + 0.01 * (k % 2)
        dx, dy = shift[k] * inset * 0.8
        t = t * h / sum(l[1] for l in layers)
        _box(mb, -w / 2 + inset + dx, w / 2 - inset + dx, inset + dy, d - inset + dy, z, z + t, mat, "bk")
        z += t
    return mb


def _post(mb: MeshBuilder, x: float, y: float, z1: float, mat: str, turned: bool, finial: bool) -> None:
    """A bed post: lathed with a turned collar (`turned`) and a finial, else a square bar."""
    if not turned:
        _tube(mb, (x, y, 0.0), (x, y, z1), (0.025, 0.025), mat, cap=True)
        return
    prof = [(0.03, 0.0), (0.035, 0.45), (0.05, 0.55), (0.028, 0.65), (0.028, z1 - 0.12)]
    if finial:
        prof += [(0.045, z1 - 0.06), (0.0, z1)]
    else:
        prof += [(0.0, z1 - 0.12)]
    _lathed(mb, prof, mat, 6, at=(x, y, 0.0))


def _gathered(mb: MeshBuilder, x_post: float, inward: float, y: float, top: float, tie: float, mat: str) -> None:
    """A velvet curtain hanging from the canopy rail at a front post, gathered and tied at `tie` height:
    folds as a zigzag in y, wide at the top, pinched at the tie, flaring a little to the floor (both sides)."""
    folds = 6
    rows = [(top, 0.42), (tie, 0.06), (0.08, 0.20)]
    grid = []
    for z, width in rows:
        line = []
        for k in range(folds + 1):
            t = k / folds
            amp = 0.035 * (1 if k % 2 else -1) * (width / 0.42 + 0.3)
            line.append((x_post + inward * width * t, y + amp, z))
        grid.append(line)
    tris = []
    for a, b in zip(grid[:-1], grid[1:]):
        for k in range(folds):
            tris += [[a[k], b[k], b[k + 1]], [a[k], b[k + 1], a[k + 1]]]
    add_sheet(mb, tris, mat, 0.006)


def sedda(s, v, rng):
    """The maqsura's canopy bed: four turned posts, a carved head board with a painted panel, a lower foot
    board, side rails, the mattress with its mink cover and pillow, the canopy frame with a valance and
    two gathered velvet curtains tied to the front posts."""
    w, d, h = s
    wood = "wood_walnut" if v == "walnut" else "wood_painted_green"
    panel = "wood_painted_red" if v == "walnut" else "painted"
    mb = MeshBuilder()
    hx, y0, y1 = w / 2 - 0.05, 0.05, d - 0.05
    for x in (-hx, hx):
        for y in (y0, y1):
            _post(mb, x, y, h, wood, True, True)
    head = Polygon(_arch_outline(2 * hx - 0.06, 1.45, 6)).buffer(0)
    _slab(mb, head, 0.03, 0.07, wood)
    _faces(mb, [_oriented([(-hx + 0.15, 0.072, 0.60), (hx - 0.15, 0.072, 0.60), (hx - 0.15, 0.072, 1.05), (-hx + 0.15, 0.072, 1.05)], (0, 1, 0))], panel)
    _box(mb, -hx + 0.03, hx - 0.03, y1 - 0.02, y1 + 0.02, 0.25, 0.85, wood, "b")
    _faces(mb, [_oriented([(-hx + 0.15, y1 + 0.022, 0.40), (hx - 0.15, y1 + 0.022, 0.40), (hx - 0.15, y1 + 0.022, 0.75), (-hx + 0.15, y1 + 0.022, 0.75)], (0, 1, 0))], panel)
    for x in (-hx, hx):
        _box(mb, x - 0.02, x + 0.02, y0, y1, 0.25, 0.42, wood, "bt" if x > 0 else "bt")
    _pad(mb, -hx + 0.02, hx - 0.02, y0 + 0.04, y1 - 0.03, 0.42, 0.58, "ticking", 0.03)
    _box(mb, -hx + 0.01, hx - 0.01, d * 0.38, y1 - 0.02, 0.58, 0.60, "mink", "bk")
    tmp = MeshBuilder()
    _pillow(tmp, "cotton_white", 2 * hx - 0.25, 0.34, 0.0, 0.0, 0.05, 0.12)   # laid flat at the head
    _moved(mb, tmp, SWAP_YZ, (0.0, 0.12, 0.585))
    top = h - 0.12
    for (a, b) in (((-hx, y0), (hx, y0)), ((-hx, y1), (hx, y1)), ((-hx, y0), (-hx, y1)), ((hx, y0), (hx, y1))):
        _tube(mb, (a[0], a[1], top), (b[0], b[1], top), (0.018, 0.022), wood)
    curtain = {"walnut": "velvet_red", "painted": "velvet_red"}[v]
    val = []
    for (a, b) in (((-hx, y1 + 0.03), (hx, y1 + 0.03)), ((-hx - 0.03, y0), (-hx - 0.03, y1)), ((hx + 0.03, y1), (hx + 0.03, y0))):
        p0, p1 = (a[0], a[1], top + 0.03), (b[0], b[1], top + 0.03)
        val += [[p0, p1, (b[0], b[1], top - 0.20)], [p0, (b[0], b[1], top - 0.20), (a[0], a[1], top - 0.20)]]
    add_sheet(mb, val, "velvet_gold", 0.006)
    for x, inward in ((-hx, 1.0), (hx, -1.0)):
        _gathered(mb, x + inward * 0.03, inward, y1 + 0.01, top - 0.18, 1.05, curtain)
    return mb


def sedda_plain(s, v, rng):
    """The low bed without a canopy: square posts, a head board with a round top, a foot board, rails,
    the mattress, a mink cover and a pillow."""
    w, d, h = s
    wood = "wood_painted_red"
    mb = MeshBuilder()
    hx, y0, y1 = w / 2 - 0.025, 0.03, d - 0.025
    for x in (-hx, hx):
        _tube(mb, (x, y0, 0.0), (x, y0, h), (0.025, 0.025), wood, cap=True)
        _tube(mb, (x, y1, 0.0), (x, y1, 0.65), (0.025, 0.025), wood, cap=True)
    head = Polygon(_arch_outline(2 * hx - 0.05, h - 0.02, 6))
    _slab(mb, head.difference(Polygon([(-w, -1), (w, -1), (w, 0.30), (-w, 0.30)])), 0.01, 0.04, wood)
    _box(mb, -hx, hx, y1 - 0.015, y1 + 0.015, 0.25, 0.60, wood, "b")
    for x in (-hx, hx):
        _box(mb, x - 0.02, x + 0.02, y0, y1, 0.22, 0.38, wood, "bt")
    _pad(mb, -hx + 0.02, hx - 0.02, y0 + 0.04, y1 - 0.03, 0.38, 0.52, "ticking", 0.03)
    _box(mb, -hx + 0.01, hx - 0.01, d * 0.40, y1 - 0.02, 0.52, 0.54, "mink", "bk")
    _box(mb, -hx + 0.12, hx - 0.12, 0.08, 0.42, 0.52, 0.62, "cotton_white", "bk")
    return mb


def meida(s, v, rng):
    """The low round table: a 16-sided top on its flared ring foot; `_painted` has a field of painted
    flowers inside a red border with a red medallion at its heart."""
    w, d, h = s
    r = w / 2
    mb = MeshBuilder()
    _lathed(mb, [(r * 0.80, 0.0), (r, h)], "wood_walnut", 16)
    if v == "painted":
        _lathed(mb, [(r, h), (r * 0.80, h)], "wood_painted_red", 16)     # the border
        _disc(mb, r * 0.80, h, 16, "painted")
        _disc(mb, r * 0.22, h + 0.002, 8, "wood_painted_red")             # the medallion
    else:
        _disc(mb, r, h, 16, "wood_walnut")
    return mb


def tray_table(s, v, rng):
    """The brass siniya on its folding wooden legs: a 16-sided tray with a raised lip on two crossed
    pairs of legs."""
    w, d, h = s
    r = w / 2
    mb = MeshBuilder()
    _lathed(mb, [(r - 0.02, h - 0.05), (r, h), (r - 0.025, h - 0.03), (0.0, h - 0.03)], "brass", 16)
    a = r * 0.55
    for sx in (-1, 1):
        _tube(mb, (sx * a, -a * 0.8, 0.0), (sx * a, a * 0.8, h - 0.06), (0.012, 0.02), "wood_walnut")
        _tube(mb, (sx * a, a * 0.8, 0.0), (sx * a, -a * 0.8, h - 0.06), (0.012, 0.02), "wood_walnut")
    _tube(mb, (-a, -a * 0.8, h - 0.06), (a, -a * 0.8, h - 0.06), (0.015, 0.012), "wood_walnut")
    _tube(mb, (-a, a * 0.8, h - 0.06), (a, a * 0.8, h - 0.06), (0.015, 0.012), "wood_walnut")
    return mb


def pouf(s, v, rng):
    """The leather pouf: a round cushion of eight panels, belly wider than its top."""
    w, d, h = s
    r = w / 2
    mb = MeshBuilder()
    _lathed(mb, [(r * 0.86, 0.0), (r, h * 0.40), (r * 0.94, h * 0.82), (r * 0.62, h), (0.0, h * 0.97)], "leather_brown", 8)
    return mb


def sendouk(s, v, rng):
    """The bride's chest on short legs: a painted body with framed panels, a lid with a domed front edge,
    rows of brass studs, brass corner plates, a lock plate and side handles."""
    w, d, h = s
    wood = PAINTED[v]
    panel = "wood_painted_red" if v == "walnut" else "painted"
    mb = MeshBuilder()
    hx, leg, lid = w / 2 - 0.02, 0.08, h - 0.12
    for x in (-hx + 0.04, hx - 0.04):
        for y in (0.06, d - 0.06):
            _tube(mb, (x, y, 0.0), (x, y, leg), (0.025, 0.025), "wood_walnut")
    _box(mb, -hx, hx, 0.02, d - 0.03, leg, lid, wood, "k")
    prof = [(0.0, lid), (d, lid), (d, lid + 0.05), (d - 0.03, lid + 0.10), (d - 0.10, h), (0.0, h)]
    _prism(mb, prof, -w / 2, w / 2, wood, wood)
    yf = d - 0.03 + 0.002
    for x0, x1 in ((-hx + 0.06, -0.20), (-0.15, 0.15), (0.20, hx - 0.06)):
        _faces(mb, [_oriented([(x0, yf, leg + 0.06), (x1, yf, leg + 0.06), (x1, yf, lid - 0.05), (x0, yf, lid - 0.05)], (0, 1, 0))], panel)
    studs = []
    for z in (leg + 0.025, lid - 0.02):
        studs += [(x, z) for x in np.linspace(-hx + 0.03, hx - 0.03, 10)]
    for x in (-0.175, 0.175):
        studs += [(x, z) for z in np.linspace(leg + 0.08, lid - 0.07, 4)]
    for x, z in studs:
        base = [(x - 0.008, yf, z - 0.008), (x + 0.008, yf, z - 0.008), (x + 0.008, yf, z + 0.008), (x - 0.008, yf, z + 0.008)]
        _pyramid(mb, base, (x, yf + 0.012, z), "brass")
    for sx in (-1, 1):
        x = sx * hx
        _faces(mb, [_oriented([(x - sx * 0.07, yf + 0.001, lid - 0.07), (x, yf + 0.001, lid - 0.07), (x, yf + 0.001, lid),
                               (x - sx * 0.07, yf + 0.001, lid)], (0, 1, 0))], "brass")
        _tube(mb, (x + sx * 0.003, d * 0.35, lid - 0.10), (x + sx * 0.003, d * 0.65, lid - 0.10), (0.012, 0.01), "brass")
    _faces(mb, [_oriented([(-0.05, d + 0.002, lid - 0.02), (0.05, d + 0.002, lid - 0.02), (0.04, d + 0.002, lid + 0.06),
                           (-0.04, d + 0.002, lid + 0.06)], (0, 1, 0))], "brass")
    return mb


def khzana(s, v, rng):
    """The two-door wall cupboard: a plinth, a body, two panelled doors with a painted panel each, brass
    knobs and lock plates, a cornice and a carved crest."""
    w, d, h = s
    wood = PAINTED[v]
    panel = "wood_painted_red" if v == "walnut" else "painted"
    mb = MeshBuilder()
    hx = w / 2 - 0.04
    _box(mb, -hx - 0.01, hx + 0.01, 0.0, d - 0.01, 0.0, 0.10, "wood_walnut", "bk")
    _box(mb, -hx, hx, 0.0, d - 0.04, 0.10, 1.85, wood, "bk")
    _box(mb, -w / 2, w / 2, 0.0, d, 1.85, 1.95, wood, "k")
    crest = Polygon(_arch_outline(0.70, 0.10, 6)).buffer(0)
    _slab(mb, Polygon([(x, z + 1.95) for x, z in crest.exterior.coords]), d - 0.08, d - 0.05, wood)
    yd = d - 0.04
    for sx in (-1, 1):
        x0, x1 = sorted((sx * 0.01, sx * (hx - 0.03)))
        _box(mb, x0, x1, yd, yd + 0.02, 0.14, 1.80, wood, "bk")
        m0, m1 = x0 + 0.07, x1 - 0.07
        for z0, z1 in ((0.25, 0.85), (1.00, 1.68)):
            _faces(mb, [_oriented([(m0, yd + 0.022, z0), (m1, yd + 0.022, z0), (m1, yd + 0.022, z1), (m0, yd + 0.022, z1)], (0, 1, 0))], panel)
        k = sx * 0.05
        _tube(mb, (k, yd + 0.02, 0.95), (k, yd + 0.045, 0.95), (0.012, 0.012), "brass", cap=True)
    _faces(mb, [_oriented([(-0.03, yd + 0.023, 1.02), (0.03, yd + 0.023, 1.02), (0.03, yd + 0.023, 1.12), (-0.03, yd + 0.023, 1.12)], (0, 1, 0))], "brass")
    return mb


def shelf_wall(s, v, rng):
    """The carved rfouf shelf: a board on two brackets, a toothed apron under its front and a low gallery
    rail on top (32 triangles)."""
    w, d, h = s
    z0 = TABLE["shelf_wall"][4]["z0"]
    wood = "wood_painted_green"
    mb = MeshBuilder()
    zb = z0 + 0.13
    _box(mb, -w / 2, w / 2, 0.0, d, zb, zb + 0.03, wood, "k")
    yf = d - 0.005
    _faces(mb, [_oriented([(-w / 2, yf, zb - 0.07), (w / 2, yf, zb - 0.07), (w / 2, yf, zb), (-w / 2, yf, zb)], (0, 1, 0))], wood)
    teeth = 6
    for k in range(teeth):
        a, b = -w / 2 + w * k / teeth, -w / 2 + w * (k + 1) / teeth
        add_triangles(mb, [_oriented([(a, yf, zb - 0.07), ((a + b) / 2, yf, z0), (b, yf, zb - 0.07)], (0, 1, 0))], wood)
    for x in (-w / 2 + 0.06, w / 2 - 0.06):
        tri = [(x, 0.0, zb), (x, d - 0.03, zb), (x, 0.0, z0 + 0.02)]
        add_triangles(mb, [_oriented(tri, (1, 0, 0)), _oriented(tri, (-1, 0, 0))], wood)
    _box(mb, -w / 2, w / 2, d - 0.015, d, zb + 0.03, z0 + h, wood, "blrb")
    _faces(mb, [_oriented([(-w / 2, d - 0.015, zb + 0.03), (w / 2, d - 0.015, zb + 0.03), (w / 2, d - 0.015, z0 + h),
                           (-w / 2, d - 0.015, z0 + h)], (0, -1, 0))], wood)
    return mb


def mirror_carved(s, v, rng):
    """A carved mirror: an arched frame (gilt brass, or painted wood) round its glass."""
    w, d, h = s
    z0 = TABLE["mirror_carved"][4]["z0"]
    frame = "brass" if v == "gilt" else "wood_painted_green"
    outer = Polygon([(x, z + z0) for x, z in _arch_outline(w, h, 6)])
    inner = Polygon([(x, z + z0 + 0.08) for x, z in _arch_outline(w - 0.16, h - 0.16, 6)])
    mb = MeshBuilder()
    _slab(mb, outer.difference(inner), 0.0, d, frame)
    for tri in triangulate(inner):
        add_triangles(mb, [_oriented([(x, d * 0.4, z) for x, z in tri], (0, 1, 0))], "mirror")
    return mb


def tray_brass(s, v, rng):
    """The brass tray of the meida: a steep narrow rim (so its edge reads crisp from across a room) with an
    outer skin (brass is one-sided, so the near rim stays seen from a standing view) round a flat 16-sided
    centre (80 triangles)."""
    w, d, h = s
    r = w / 2
    mb = MeshBuilder()
    _lathed(mb, [(r - 0.006, 0.0), (r, h), (r - 0.018, 0.004), (0.0, 0.003)], "brass", 16)
    return mb


def tea_set(s, v, rng):
    """Tea for guests: a small oval tray, the teapot (berrad) with its spout and handle, and beside it six
    small glasses of amber tea (7 cm) with a thin gold rim; which glass stands where draws on the piece's
    stream."""
    w, d, h = s
    metal = "brass" if v == "brass" else "aluminium"
    mb = MeshBuilder()
    _disc(mb, 0.5, 0.004, 8, metal)
    tray = mb._parts[metal]
    tray[0][-1][:, :2] *= [w, d]
    px, py = w * 0.25, 0.0
    _lathed(mb, [(0.035, 0.004), (0.060, 0.07), (0.0, h)], metal, 5, at=(px, py, 0.0))
    _tube(mb, (px - 0.05, py, 0.035), (px - 0.125, py, 0.15), (0.009, 0.003), metal)   # long tapering spout
    _tube(mb, (px + 0.04, py, 0.12), (px + 0.075, py, 0.05), (0.005, 0.010), metal)
    spots = [(x, y) for x in (-0.135, -0.08, -0.025) for y in (-0.055, 0.045)]
    for k in rng.permutation(len(spots)):
        x, y = spots[k]
        x += rng.uniform(-0.006, 0.006)
        _lathed(mb, [(0.017, 0.004), (0.022, 0.060), (0.0, 0.058)], "tea_amber", 4, at=(x, y, 0.0), turn=math.pi / 4)
        _lathed(mb, [(0.022, 0.060), (0.024, 0.070)], "brass", 4, at=(x, y, 0.0), turn=math.pi / 4)
    return mb


def ibrik(s, v, rng):
    """Ewer and basin for washing hands: the copper basin (tast) and the brass ewer standing in it with
    its spout and handle."""
    w, d, h = s
    r = w / 2
    mb = MeshBuilder()
    _lathed(mb, [(r * 0.55, 0.0), (r, 0.10), (r * 0.9, 0.10), (0.0, 0.04)], "copper_ware", 8)
    _lathed(mb, [(0.045, 0.045), (0.085, 0.16), (0.026, 0.28), (0.052, h)], "brass", 8)   # flared mouth
    _tube(mb, (0.07, 0.0, 0.17), (0.165, 0.0, 0.34), (0.012, 0.004), "brass")             # tapering spout
    _tube(mb, (-0.035, 0.0, 0.33), (-0.11, 0.0, 0.27), (0.006, 0.012), "brass")
    _tube(mb, (-0.11, 0.0, 0.27), (-0.07, 0.0, 0.16), (0.006, 0.012), "brass")
    return mb


def kanoun(s, v, rng):
    """The clay brazier: a flared bowl on a foot, glowing charcoal in it, three nubs to hold a pot."""
    w, d, h = s
    r = w / 2
    mb = MeshBuilder()
    _lathed(mb, [(r * 0.65, 0.0), (r * 0.75, h * 0.40), (r, h), (r * 0.78, h - 0.015), (0.0, h - 0.05)],
            ["clay_red", "clay_red", "clay_red", "charcoal"], 8)
    for k in range(3):
        a = k * 2 * math.pi / 3 + 0.3
        c = np.array([math.cos(a), math.sin(a), 0.0]) * r * 0.86 + [0, 0, h - 0.01]
        _pyramid(mb, _ring(c[0], c[1], c[2], 0.02, 0.02, 3), c + [0, 0, 0.035 - 0.025], "clay_red")
    return mb


def couscoussier(s, v, rng):
    """The aluminium couscoussier: the pot (borma), the steamer (keskes) on it and the lid, two handles."""
    w, d, h = s
    r = w / 2
    mb = MeshBuilder()
    b = r * 0.96
    _lathed(mb, [(b * 0.70, 0.0), (b * 0.94, h * 0.15), (b * 0.94, h * 0.48), (b * 0.82, h * 0.54), (b, h * 0.58),
                 (b * 0.88, h * 0.85), (b * 0.48, h * 0.96), (0.0, h * 0.98)], "aluminium", 8)
    for sx in (-1, 1):
        _tube(mb, (sx * b * 0.90, 0.0, h * 0.42), (sx * (r - 0.004), 0.0, h * 0.42), (0.012, 0.018), "aluminium")
    _pyramid(mb, _ring(0, 0, h * 0.97, 0.02, 0.02, 4), (0, 0, h), "aluminium")
    return mb


def counter_masonry(s, v, rng):
    """The built counter of a matbakh: a plastered body with a niche for pots, a tiled top (28 triangles)."""
    w, d, h = s
    mb = MeshBuilder()
    top = h - 0.04
    yf = d - 0.03
    a, b = -w / 2 + 0.12, w / 2 - 0.12
    zn = top - 0.18
    _faces(mb, [_oriented(q, (0, 1, 0)) for q in (
        [(-w / 2, yf, 0.0), (a, yf, 0.0), (a, yf, top), (-w / 2, yf, top)],
        [(b, yf, 0.0), (w / 2, yf, 0.0), (w / 2, yf, top), (b, yf, top)],
        [(a, yf, zn), (b, yf, zn), (b, yf, top), (a, yf, top)])], "plaster_inner")
    _box(mb, a, b, 0.10, yf, 0.0, zn, "plaster_inner", "bftk")
    _faces(mb, [_oriented([(a, 0.10, 0.0), (b, 0.10, 0.0), (b, 0.10, zn), (a, 0.10, zn)], (0, 1, 0))], "plaster_inner")
    for x, n in ((-w / 2, -1), (w / 2, 1)):
        _faces(mb, [_oriented([(x, 0.0, 0.0), (x, yf, 0.0), (x, yf, top), (x, 0.0, top)], (n, 0, 0))], "plaster_inner")
    _box(mb, -w / 2, w / 2, 0.0, d, top, h, "floor_tiles", "k")
    return mb


def gas_ring(s, v, rng):
    """The two-burner rechaud: a white enamel body, two black burners, two knobs on its front."""
    w, d, h = s
    mb = MeshBuilder()
    zb = h - 0.035
    _box(mb, -w / 2, w / 2, -d / 2, d / 2, 0.0, zb, "enamel_white", "b")
    for x in (-w * 0.24, w * 0.24):
        _lathed(mb, [(0.085, zb), (0.07, h), (0.0, h - 0.008)], "iron_black", 6, at=(x, 0.02, 0.0))
    for x in (-0.06, 0.06):
        _tube(mb, (x, d / 2 - 0.005, zb * 0.5), (x, d / 2 + 0.015, zb * 0.5), (0.014, 0.014), "iron_black", cap=True)
    return mb


def butane(s, v, rng):
    """The blue butane bottle: a round body with its foot ring and a black guard round the valve."""
    w, d, h = s
    r = w / 2
    mb = MeshBuilder()
    _lathed(mb, [(r * 0.92, 0.0), (r, 0.05), (r, h * 0.72), (0.0, h * 0.90)], "butane_bottle", 8)
    _lathed(mb, [(r * 0.50, h * 0.84), (r * 0.50, h)], "iron_black", 8)
    _pyramid(mb, _ring(0, 0, h * 0.89, 0.025, 0.025, 4), (0, 0, h * 0.95), "iron_black")
    return mb


def sink_stone(s, v, rng):
    """The matbakh's stone sink: a terrazzo basin on its pier, a chrome drain."""
    w, d, h = s
    mb = MeshBuilder()
    zt, zb = h, h - 0.15
    _box(mb, -w / 2 + 0.08, w / 2 - 0.08, 0.0, d - 0.10, 0.0, zb, "terrazzo", "btk")
    a, b, c, e = -w / 2 + 0.05, w / 2 - 0.05, 0.05, d - 0.05
    rim = [_oriented(q, (0, 0, 1)) for q in (
        [(-w / 2, 0, zt), (w / 2, 0, zt), (b, c, zt), (a, c, zt)], [(a, e, zt), (b, e, zt), (w / 2, d, zt), (-w / 2, d, zt)],
        [(-w / 2, 0, zt), (a, c, zt), (a, e, zt), (-w / 2, d, zt)], [(b, c, zt), (w / 2, 0, zt), (w / 2, d, zt), (b, e, zt)])]
    _faces(mb, rim, "terrazzo")
    _box(mb, -w / 2, w / 2, 0.0, d, zb, zt, "terrazzo", "btk")
    zf = zb + 0.02
    inside = [([(a, c, zf), (b, c, zf), (b, c, zt), (a, c, zt)], (0, 1, 0)), ([(a, e, zf), (b, e, zf), (b, e, zt), (a, e, zt)], (0, -1, 0)),
              ([(a, c, zf), (a, e, zf), (a, e, zt), (a, c, zt)], (1, 0, 0)), ([(b, c, zf), (b, e, zf), (b, e, zt), (b, c, zt)], (-1, 0, 0)),
              ([(a, c, zf), (b, c, zf), (b, e, zf), (a, e, zf)], (0, 0, 1))]
    _faces(mb, [_oriented(q, n) for q, n in inside], "terrazzo")
    _pyramid(mb, _ring(0, d / 2, zb + 0.021, 0.025, 0.025, 4), (0, d / 2, zb + 0.022), "chrome")
    return mb


def qolla(s, v, rng):
    """The porous water jar on its iron stand, a cup over its mouth."""
    w, d, h = s
    mb = MeshBuilder()
    zr = 0.36
    _lathed(mb, [(0.12, zr - 0.04), (0.12, zr)], "iron_black", 8)
    for k in range(4):
        a = k * math.pi / 2
        top = np.array([0.12 * math.cos(a), 0.12 * math.sin(a), zr])
        foot = np.array([(w / 2 - 0.012) * math.cos(a), (w / 2 - 0.012) * math.sin(a), 0.0])
        _tube(mb, foot, top, (0.008, 0.008), "iron_black")
    _lathed(mb, [(0.04, zr - 0.12), (0.13, zr + 0.10), (0.045, h - 0.10), (0.04, h - 0.05)], "clay_pale", 8)
    _pyramid(mb, _ring(0.0, 0.0, h - 0.05, 0.045, 0.045, 6), (0.0, 0.0, h), "clay_pale")   # the cup over its mouth
    return mb


def gsaa(s, v, rng):
    """The wide wooden bowl for rolling couscous (48 triangles)."""
    w, d, h = s
    r = w / 2
    mb = MeshBuilder()
    _lathed(mb, [(r * 0.62, 0.0), (r, h), (0.0, h * 0.25)], "wood_beech", 16)
    return mb


def _leg(mb: MeshBuilder, x: float, y: float, z0: float, z1: float, r: float, mat: str) -> None:
    """A thin leg as a three-sided prism (6 triangles)."""
    ring = _ring(x, y, 0.0, r, r, 3, math.pi / 6)
    quads = [[(a[0], a[1], z0), (b[0], b[1], z0), (b[0], b[1], z1), (a[0], a[1], z1)] for a, b in zip(ring, np.roll(ring, -1, 0))]
    _faces(mb, [_oriented(q, (q[0][0] + q[1][0] - 2 * x, q[0][1] + q[1][1] - 2 * y, 0)) for q in quads], mat)


def kursi(s, v, rng):
    """The low stool of kitchen and washroom: four legs and a woven halfa seat in a wooden frame."""
    w, d, h = s
    mb = MeshBuilder()
    a = w / 2 - 0.025
    for x in (-a, a):
        for y in (-a, a):
            _leg(mb, x, y, 0.0, h - 0.03, 0.022, "wood_beech")
    _box(mb, -w / 2, w / 2, -d / 2, d / 2, h - 0.03, h, "wood_beech", "bt")
    _faces(mb, [_oriented([(-w / 2, -d / 2, h), (w / 2, -d / 2, h), (w / 2, d / 2, h), (-w / 2, d / 2, h)], (0, 0, 1))], "hasira")
    return mb


def khabia(s, v, rng):
    """The oil jar: a belly on a narrow foot, a short neck with a rolled rim, two handles on the shoulder;
    `_glazed` green above the belly."""
    w, d, h = s
    r = w / 2
    mb = MeshBuilder()
    low, high = "clay_red", ("glaze_green" if v == "glazed" else "clay_red")
    prof = [(r * 0.42, 0.0), (r * 0.90, h * 0.24), (r, h * 0.47), (r * 0.80, h * 0.76), (r * 0.40, h * 0.90),
            (r * 0.44, h), (r * 0.32, h * 0.98)]
    _lathed(mb, prof, [low, low, high, high, high, high], 8)
    for sx in (-1, 1):
        _tube(mb, (sx * r * 0.40, 0.0, h * 0.88), (sx * r * 0.80, 0.0, h * 0.74), (0.012, 0.02), high)
    return mb


def grain_sacks(s, v, rng):
    """Sacks of semolina and wheat against the wall: three tied jute sacks, each a little different."""
    w, d, h = s
    mb = MeshBuilder()
    spots = [(-w * 0.32, 0.24, 1.0), (w * 0.32, 0.24, 0.92), (0.0, 0.26, 0.84)]
    for k, (x, y, scale) in enumerate(spots):
        hh = h * scale - 0.01 * rng.uniform(0.0, 1.0)
        rx, ry = w * 0.18, d * 0.48 / math.sin(math.pi / 3)   # a hexagon's sides reach sin 60 degrees
        _lathed(mb, [(0.80, 0.0), (1.0, hh * 0.45), (0.70, hh * 0.86), (0.0, hh)], "jute", 6,
                at=(x, y, 0.0), scale=(rx, ry * (0.98 if k < 2 else 0.95)))
    return mb


def tabouna(s, v, rng):
    """The clay bread oven: a plastered drum with a clay rim, its mouth open on the dark inside and a
    draught hole at the foot."""
    w, d, h = s
    r = w / 2
    mb = MeshBuilder()
    _lathed(mb, [(r, 0.0), (r * 0.98, h * 0.50), (r * 0.85, h * 0.88), (r * 0.62, h), (r * 0.52, h * 0.93),
                 (0.0, h * 0.70)], ["plaster_inner", "plaster_inner", "clay_red", "clay_red", "charcoal"], 10)
    _faces(mb, [_oriented([(-0.07, r + 0.004, 0.03), (0.07, r + 0.004, 0.03), (0.07, r + 0.004, 0.13), (-0.07, r + 0.004, 0.13)], (0, 1, 0))], "charcoal")
    return mb


def rug(base: str, mat: str, repeat: bool):
    def make(s, v, rng):
        mb = MeshBuilder()
        _rug(mb, s[0], s[1], s[2], mat, REPEAT[mat] if repeat else None)
        return mb
    return make


def klim(s, v, rng):
    mat = "klim_indigo" if v.endswith("indigo") else "klim_red"
    mb = MeshBuilder()
    _rug(mb, s[0], s[1], s[2], mat, REPEAT[mat])
    return mb


def hidoura(s, v, rng):
    """The sheepskin of the Aid: a hide outline with its four legs, neck and tail and four shaggy tufts on
    the flanks, two wool locks, one out and one in, along every edge; the fleece domed over a soft
    shoulder to its full height in the middle and thin at the ragged edge; wool locks in the image (126 triangles)."""
    w, d, h = s
    hide = [(0.0, 0.5), (0.2, 0.38), (0.5, 0.30), (0.30, 0.02), (0.5, -0.36), (0.06, -0.5),
            (-0.5, -0.36), (-0.30, 0.02), (-0.5, 0.30), (-0.2, 0.38)]
    out = []
    for i, p in enumerate(hide):                          # a tuft halfway along each flank, between the legs
        out.append(p)
        if i in (2, 3, 6, 7):
            q = hide[i + 1]
            out.append(((p[0] + q[0]) / 2 * rng.uniform(1.05, 1.18), (p[1] + q[1]) / 2))
    out = np.array(out)
    nxt = np.roll(out, -1, axis=0)                           # two wool locks along every edge, out then in
    locks = [out] + [(out + (nxt - out) * f) * k * rng.uniform(0.97, 1.03, (len(out), 1)) for f, k in ((1 / 3, 1.13), (2 / 3, 0.88))]
    out = np.stack(locks, axis=1).reshape(-1, 2) + rng.uniform(-0.02, 0.02, (3 * len(out), 2))
    out = (out - out.min(axis=0)) / (out.max(axis=0) - out.min(axis=0)) - 0.5
    m = len(out)
    edge = RUG_Z + rng.uniform(0.002, 0.006, m)               # the ragged hem, some locks lifted
    crown = RUG_Z + h - 0.005                                  # a rug stays under 2 cm: chairs stand on it
    ring = np.c_[out * 0.55 * [w, d], RUG_Z + (0.7 + rng.uniform(-0.1, 0.1, m)) * (crown - RUG_Z)]   # the soft shoulder
    pos = np.concatenate([np.c_[out * [w, d], edge], ring, [[0.0, 0.0, crown]]])
    tris = []
    for i in range(m):
        j = (i + 1) % m
        tris += [[i, j, m + j], [i, m + j, m + i], [m + i, m + j, 2 * m]]
    tris = np.array(tris)
    for n in range(len(tris)):
        p0, p1, p2 = pos[tris[n]]
        if np.cross(p1 - p0, p2 - p0)[2] < 0:
            tris[n] = tris[n][::-1]
    mb = MeshBuilder()
    _smooth(mb, "fleece", pos, tris, uv=np.stack([pos[:, 0], -pos[:, 1]], axis=1))
    return mb


def rahla(s, v, rng):
    """The folding Quran stand with its book: two crossed boards, the book open in the V they make."""
    w, d, h = s
    mb = MeshBuilder()
    half = (0.13, 0.008)
    for sy in (-1, 1):
        _tube(mb, (0.0, sy * d * 0.40, 0.0), (0.0, -sy * d * 0.45, h * 0.86), half, "wood_walnut", cap=True)
    zc = h * 0.62
    for sy in (-1, 1):
        a, b = (0.0, sy * 0.005, zc), (0.0, sy * 0.10, zc + 0.11)
        _tube(mb, a, b, (w / 2 - 0.002, 0.008), "book_green", cap=False)
        _faces(mb, [_oriented([(-w / 2 + 0.01, a[1], a[2] + 0.018), (w / 2 - 0.01, a[1], a[2] + 0.018),
                               (w / 2 - 0.01, b[1], b[2] + 0.018), (-w / 2 + 0.01, b[1], b[2] + 0.018)], (0, -sy * 0.7, 1))], "cotton_white")
    return mb


def loom(s, v, rng):
    """The upright loom: two posts braced back to the wall, the top and cloth beams, the warp as threads,
    the half-woven klim below with its beater comb, a heddle bar and balls of yarn hanging off it."""
    w, d, h = s
    mb = MeshBuilder()
    hx, yp = w / 2 - 0.04, d - 0.30
    for x in (-hx, hx):
        _tube(mb, (x, yp, 0.0), (x, yp, h), (0.04, 0.04), "wood_beech", cap=True)
        _tube(mb, (x, d - 0.03, 0.0), (x, 0.03, h * 0.75), (0.02, 0.025), "wood_beech")
    zt, zc = h - 0.20, 0.25
    for z in (zt, zc):
        tmp = MeshBuilder()
        _lathed(tmp, [(0.045, 0.0), (0.045, 2 * hx)], "wood_beech", 6)
        _moved(mb, tmp, SWAP_XZ, (-hx, yp, z))
    zw = 0.95                                         # the woven klim reaches this high
    a, b = -hx + 0.10, hx - 0.10
    add_sheet(mb, [[(a, yp, zc), (b, yp, zc), (b, yp, zw)], [(a, yp, zc), (b, yp, zw), (a, yp, zw)]], "klim_red", 0.006)
    threads = 22
    tri = []
    for k in range(threads):
        x = a + (b - a) * (k + 0.5) / threads
        tri += [[(x - 0.006, yp, zw), (x + 0.006, yp, zw), (x + 0.006, yp, zt)], [(x - 0.006, yp, zw), (x + 0.006, yp, zt), (x - 0.006, yp, zt)]]
    add_sheet(mb, tri, "wool_cream", 0.004)
    _tube(mb, (a - 0.05, yp + 0.05, zw + 0.03), (b + 0.05, yp + 0.05, zw + 0.03), (0.02, 0.03), "wood_beech")
    _tube(mb, (-hx, yp + 0.02, 1.45), (hx, yp + 0.02, 1.45), (0.015, 0.015), "wood_beech")
    colors = ["wool_cream", "klim_red", "wool_cream", "klim_red"]
    xs = np.sort(rng.uniform(a + 0.1, b - 0.1, 4))
    for k, x in enumerate(xs):
        z = zw + 0.12 + 0.05 * k % 2
        r = 0.035
        for top, sgn in ((z + r, 1), (z - r, -1)):
            _pyramid(mb, _ring(x, yp + 0.06, z, r, r * 0.8, 4), (x, yp + 0.06, top), colors[k])
    return mb


def wool_basket(s, v, rng):
    """The halfa basket of wool balls beside the loom, with two handles."""
    w, d, h = s
    r = w / 2
    mb = MeshBuilder()
    _lathed(mb, [(r * 0.72, 0.0), (r, h * 0.70), (r * 0.92, h * 0.70), (0.0, h * 0.62)], ["hasira", "hasira", "wool_cream"], 8)
    for k, (x, y) in enumerate(((-0.07, 0.02), (0.08, -0.04), (0.0, 0.08))):
        rr = 0.075
        z = h - rr
        for top in (z + rr, z - rr):
            _pyramid(mb, _ring(x, y, z, rr, rr, 4, 0.4 * k), (x, y, top), "wool_cream")
    for sx in (-1, 1):
        _tube(mb, (sx * r * 0.94, -0.06, h * 0.70), (sx * r * 0.94, 0.06, h * 0.70), (0.008, 0.02), "hasira")
    return mb


def sewing_machine(s, v, rng):
    """The treadle sewing machine: a walnut table with a drawer on cast-iron end frames, the treadle and
    its flywheel, the black machine head with its hand wheel and spool pin."""
    w, d, h = s
    mb = MeshBuilder()
    zt = 0.75
    _box(mb, -w / 2, w / 2, 0.0, d, zt - 0.03, zt, "wood_walnut", "k")
    _box(mb, -w / 2 + 0.05, -w / 2 + 0.30, 0.04, d - 0.02, zt - 0.15, zt - 0.03, "wood_walnut", "kt")
    hx = w / 2 - 0.06
    for x in (-hx, hx):
        for y0, y1 in ((0.05, d - 0.08), (d - 0.05, 0.08)):
            _tube(mb, (x, y0, 0.0), (x, y1, zt - 0.03), (0.012, 0.018), "iron_black")
        _tube(mb, (x, 0.05, 0.02), (x, d - 0.05, 0.02), (0.012, 0.02), "iron_black")
        _tube(mb, (x, 0.08, zt - 0.05), (x, d - 0.08, zt - 0.05), (0.012, 0.015), "iron_black")
    _tube(mb, (-hx, d * 0.5, 0.25), (hx, d * 0.5, 0.25), (0.01, 0.01), "iron_black")
    _box(mb, -0.25, 0.25, 0.15, d - 0.08, 0.06, 0.09, "iron_black", "b")
    fx = hx - 0.06
    tmp = MeshBuilder()
    _lathed(tmp, [(0.18, -0.012), (0.18, 0.012), (0.0, 0.012)], "iron_black", 10)
    _moved(mb, tmp, SWAP_XZ, (fx, d * 0.5, 0.35))
    _box(mb, -0.25, 0.20, 0.18, 0.36, zt, zt + 0.03, "iron_black", "b")
    _box(mb, 0.10, 0.18, 0.20, 0.32, zt + 0.03, h - 0.04, "iron_black", "b")
    _box(mb, -0.20, 0.18, 0.22, 0.31, h - 0.08, h - 0.03, "iron_black", "b")
    _box(mb, -0.24, -0.16, 0.21, 0.32, zt + 0.06, h - 0.03, "iron_black", "b")
    tmp = MeshBuilder()
    _lathed(tmp, [(0.06, 0.0), (0.06, 0.03), (0.0, 0.03)], "iron_black", 8)
    _moved(mb, tmp, SWAP_XZ, (0.18, 0.27, zt + 0.11))
    _tube(mb, (0.0, 0.265, h - 0.03), (0.0, 0.265, h), (0.004, 0.004), "brass")
    return mb


def dummy(s, v, rng):
    """The tailor's dress form: a cotton torso (hips, a narrower waist, the bust, sloping shoulders and a
    neck with a walnut cap), flattened front to back, on its pole and tripod."""
    w, d, h = s
    mb = MeshBuilder()
    prof = [(0.150, 0.96), (0.165, 1.06), (0.146, 1.20), (0.164, 1.34), (0.150, 1.45), (0.045, 1.52)]
    widest = 2 * max(r for r, _z in prof)
    sx, sy = (w - 0.01) / widest, (d - 0.01) / widest
    tmp = MeshBuilder()
    _lathed(tmp, prof, "cotton_white", 8, scale=(sx, sy))
    _soft(mb, tmp)
    _lathed(mb, [(0.045, 1.52), (0.0, h)], "wood_walnut", 8)                     # the neck cap
    _tube(mb, (0.0, 0.0, 0.08), (0.0, 0.0, 0.96), (0.012, 0.012), "wood_walnut")
    for k in range(3):
        a = math.pi / 2 + k * 2 * math.pi / 3
        foot = np.array([0.19 * math.cos(a), 0.19 * math.sin(a), 0.0])
        _tube(mb, (0.0, 0.0, 0.12), foot, (0.008, 0.012), "wood_walnut")
    return mb


def chechia_forms(s, v, rng):
    """The chechia maker's bench: a beech table carrying four wooden forms, two wearing a red chechia."""
    w, d, h = s
    mb = MeshBuilder()
    zt = 0.75
    _box(mb, -w / 2, w / 2, 0.0, d, zt - 0.03, zt, "wood_beech", "k")
    for x in (-w / 2 + 0.04, w / 2 - 0.04):
        for y in (0.04, d - 0.04):
            _tube(mb, (x, y, 0.0), (x, y, zt - 0.03), (0.02, 0.02), "wood_beech")
    for k, x in enumerate(np.linspace(-w * 0.33, w * 0.33, 4)):
        y = d * 0.5
        if k % 2 == 0:
            _lathed(mb, [(0.085, zt), (0.08, zt + 0.08)], "wood_beech", 6, at=(x, y, 0.0))
            _lathed(mb, [(0.085, zt + 0.06), (0.09, h - 0.01), (0.0, h)], "chechia_red", 6, at=(x, y, 0.0))
        else:
            _lathed(mb, [(0.085, zt), (0.08, h - 0.04), (0.0, h - 0.03)], "wood_beech", 6, at=(x, y, 0.0))
    return mb


def pots_stack(s, v, rng):
    """The potter's stock: two jars at the back, a tall green-glazed jug in front, a stack of two open bowls
    beside it (the lower one's glazed rim ring round the upper one, the upper one's glazed hollow showing),
    each set a little at random."""
    w, d, h = s
    mb = MeshBuilder()
    j = rng.uniform(-0.008, 0.008, (4, 2))
    pots = [((-0.16, -0.17), 0.14, 0.44, "clay_red"), ((0.16, -0.17), 0.14, 0.38, "clay_red"),
            ((0.15, 0.17), 0.14, h, "glaze_green")]
    for k, ((x, y), r, ph, mat) in enumerate(pots):
        x, y = x + j[k, 0], y + j[k, 1]
        _lathed(mb, [(r * 0.6, 0.0), (r, ph * 0.45), (r * 0.42, ph * 0.86), (r * 0.55, ph)], mat, 6, at=(x, y, 0.0))
    bx, by = -0.17 + j[3, 0], 0.18 + j[3, 1]
    r1, r2, zr, z2 = 0.13, 0.125, 0.08, 0.035          # radii, the lower rim's height, the upper bowl's foot
    ri = r2 * (0.5 + 0.5 * (zr - z2) / 0.08)            # the upper bowl's wall where the lower rim meets it
    _lathed(mb, [(r1 * 0.5, 0.0), (r1, zr), (ri, zr)], ["clay_red", "glaze_green"], 8, at=(bx, by, 0.0))
    _lathed(mb, [(ri, zr), (r2, z2 + 0.08), (r2 * 0.5, z2 + 0.03), (0.0, z2 + 0.025)], ["clay_red", "glaze_green", "glaze_green"],
            8, at=(bx, by, 0.0))   # 8 sides and a flat-bottomed hollow: open, not a peaked lid
    return mb


def net_pile(s, v, rng):
    """A heap of green fishing net: radial folds draped from a high middle to a wavy hem on the floor,
    its cords and dark holes in the image, with four red floats caught in it (smooth normals)."""
    w, d, h = s
    k = 8
    radii = [0.0, 0.35, 0.68, 1.0]
    heights = [1.0, 0.82, 0.45, 0.03]
    phase = rng.uniform(0.0, 2 * math.pi)
    pts = [(rng.uniform(-0.05, 0.05) * w, rng.uniform(-0.05, 0.05) * d, h)]
    for rr, zz in zip(radii[1:], heights[1:]):
        for i in range(k):
            a = i * 2 * math.pi / k + rng.uniform(-0.12, 0.12)
            fold = 1.0 + (0.35 if i % 2 else -0.35) * (zz > 0.1)           # ridges and valleys of the drape
            q = rr * (0.93 + 0.07 * math.cos(3 * a + phase))
            pts.append((q * math.cos(a) * w / 2, q * math.sin(a) * d / 2, h * min(1.0, zz * fold)))
    pos = np.array(pts)
    pos[:, 0] = pos[:, 0] / (np.ptp(pos[:, 0]) / w)
    pos[:, 1] = pos[:, 1] / (np.ptp(pos[:, 1]) / d)
    tris = [[0, 1 + i, 1 + (i + 1) % k] for i in range(k)]
    for ring in range(2):
        for i in range(k):
            a, b = 1 + ring * k + i, 1 + ring * k + (i + 1) % k
            tris += [[a, a + k, b + k], [a, b + k, b]]
    tris = np.array(tris)
    for n in range(len(tris)):
        p0, p1, p2 = pos[tris[n]]
        if np.cross(p1 - p0, p2 - p0)[2] < 0:
            tris[n] = tris[n][::-1]
    mb = MeshBuilder()
    _smooth(mb, "twine_green", pos, tris, uv=np.stack([pos[:, 0], -pos[:, 1]], axis=1))   # one top-down projection
    for i in (1, 3, 4, 6):                                # floats on the second ring's ridges
        x, y, z = pos[1 + k + i]
        _pyramid(mb, _ring(x, y, z + 0.025, 0.04, 0.03, 4), (x, y, z + 0.06), "plastic_red")
        _pyramid(mb, _ring(x, y, z + 0.025, 0.04, 0.03, 4), (x, y, z - 0.005), "plastic_red")
    return mb


def skifa_bench(s, v, rng):
    """The skifa's stone bench: a slab with a rounded nosing over a set-back face (20 triangles)."""
    w, d, h = s
    prof = [(0.0, h), (d - 0.05, h), (d, h - 0.02), (d, h - 0.06), (d - 0.04, h - 0.08), (d - 0.04, 0.0), (0.0, 0.0)]
    mb = MeshBuilder()
    _prism(mb, prof, -w / 2, w / 2, ["step_stone"] * 5 + [None], "step_stone")
    return mb


def wc_turkish(s, v, rng):
    """The squat toilet: a white pan with its oval basin sunk in a raised slab (40 triangles)."""
    w, d, h = s
    mb = MeshBuilder()
    _box(mb, -w / 2, w / 2, 0.0, d, 0.0, h, "ceramic_white", "btk")
    outer = _ring(0.0, d * 0.55, h, w * 0.30, d * 0.36, 6, math.pi / 2)
    inner = _ring(0.0, d * 0.60, 0.01, w * 0.16, d * 0.20, 6, math.pi / 2)
    corners = [(-w / 2, 0.0, h), (w / 2, 0.0, h), (w / 2, d, h), (-w / 2, d, h)]
    ring = Polygon([(x, y) for x, y, _z in corners]).difference(Polygon(outer[:, :2]))
    for tri in triangulate(ring):
        add_triangles(mb, [_oriented([(x, y, h) for x, y in tri], (0, 0, 1))], "ceramic_white")
    quads = [[outer[i], outer[(i + 1) % 6], inner[(i + 1) % 6], inner[i]] for i in range(6)]
    centre = np.array([0.0, d * 0.58, 0.0])
    _faces(mb, [_oriented(q, centre + [0, 0, h] - np.mean(q, axis=0)) for q in quads], "ceramic_white")
    _pyramid(mb, inner, (0.0, d * 0.62, 0.0), "charcoal")
    m = mb._parts["charcoal"]
    m[1][-1][:] = [0.0, 0.0, 1.0]
    return mb


def tap_wall(s, v, rng):
    """A chrome wall tap: the pipe out of the wall, the spout bending down and the flat handle (28)."""
    w, d, h = s
    z0 = TABLE["tap_wall"][4]["z0"]
    zp = z0 + 0.07
    mb = MeshBuilder()
    _tube(mb, (0.0, 0.0, zp), (0.0, d - 0.03, zp), (0.01, 0.01), "chrome")
    _tube(mb, (0.0, d - 0.03, zp), (0.0, d - 0.01, z0), (0.009, 0.009), "chrome")
    _leg(mb, 0.0, 0.05, zp, z0 + h - 0.008, 0.008, "chrome")
    _tube(mb, (-w / 2, 0.05, z0 + h - 0.008), (w / 2, 0.05, z0 + h - 0.008), (0.008, 0.008), "chrome")
    return mb


def bucket(s, v, rng):
    """The plastic bucket of washrooms and courts, with its two handle ears."""
    w, d, h = s
    r = w / 2
    mb = MeshBuilder()
    _lathed(mb, [(r * 0.80, 0.0), (r, h), (r * 0.76, 0.02), (0.0, 0.02)], "plastic_blue", 8)
    for sx in (-1, 1):
        _pyramid(mb, _ring(sx * r * 0.97, 0.0, h - 0.03, 0.012, 0.02, 4), (sx * (r + 0.005), 0.0, h - 0.03), "plastic_blue")
    return mb


def lota(s, v, rng):
    """The water jug beside every toilet: a round red body, its spout and handle."""
    w, d, h = s
    r = w / 2
    mb = MeshBuilder()
    _lathed(mb, [(r * 0.66, 0.0), (r, h * 0.38), (r * 0.58, h)], "plastic_red", 6)
    _tube(mb, (r * 0.80, 0.0, h * 0.35), (r * 0.98, 0.0, h * 0.75), (0.008, 0.008), "plastic_red")
    _tube(mb, (0.0, -r * 0.62, h * 0.92), (0.0, -r * 1.15, h * 0.45), (0.01, 0.006), "plastic_red")
    return mb


def basin_washing(s, v, rng):
    """The aluminium laundry basin (bassine): flared walls round a flat floor (40 triangles)."""
    w, d, h = s
    r = w / 2
    mb = MeshBuilder()
    _lathed(mb, [(r * 0.74, 0.0), (r, h), (r * 0.71, 0.02), (0.0, 0.02)], "aluminium", 8)
    return mb


MAKERS = {"doukkana": doukkana, "mattress": mattress, "cushion": cushion, "mattress_floor": mattress_floor,
          "mattress_stack": mattress_stack, "sedda": sedda, "sedda_plain": sedda_plain, "meida": meida,
          "tray_table": tray_table, "pouf": pouf, "sendouk": sendouk, "khzana": khzana, "shelf_wall": shelf_wall,
          "mirror_carved": mirror_carved, "tray_brass": tray_brass, "tea_set": tea_set, "ibrik": ibrik,
          "kanoun": kanoun, "couscoussier": couscoussier, "counter_masonry": counter_masonry, "gas_ring": gas_ring,
          "butane": butane, "sink_stone": sink_stone, "qolla": qolla, "gsaa": gsaa, "kursi": kursi,
          "khabia": khabia, "grain_sacks": grain_sacks, "tabouna": tabouna, "klim": klim,
          "mergoum": rug("mergoum", "mergoum", True), "zarbia": rug("zarbia", "zarbia", True),
          "hasira": rug("hasira", "hasira", False), "hidoura": hidoura, "sajjada": rug("sajjada", "sajjada", True),
          "rahla": rahla, "loom": loom, "wool_basket": wool_basket, "sewing_machine": sewing_machine,
          "dummy": dummy, "chechia_forms": chechia_forms, "pots_stack": pots_stack, "net_pile": net_pile,
          "skifa_bench": skifa_bench, "wc_turkish": wc_turkish, "tap_wall": tap_wall, "bucket": bucket,
          "lota": lota, "basin_washing": basin_washing}


def names() -> list:
    """Every piece name of the traditional table (without `home/`), variants spelled out, in table order."""
    return [n for b in TABLE for n in ([f"{b}_{v}" for v in VARIANTS[b]] if b in VARIANTS else [b])]


def pieces(seed: int, cfg: dict) -> dict:
    """{name: (MeshBuilder, category, anchor, spec dict)} of every traditional piece; `cfg` is the style's
    `[interiors.furnish]` (its `sizes` override `SIZES`)."""
    over = (cfg or {}).get("sizes", {})
    out = {}
    for base, (cat, anchor, _size, tris, extra) in TABLE.items():
        for suffix in VARIANTS.get(base, (None,)):
            name = base if suffix is None else f"{base}_{suffix}"
            size = tuple(float(v) for v in over.get(name, over.get(base, SIZES.get(name, SIZES[base]))))
            rng = stream(seed, "piece", f"home/{name}")
            mb = MAKERS[base](size, suffix or "", rng)
            out[name] = (mb, cat, anchor, {"size": size, "tris": tris, **extra})
    return out
