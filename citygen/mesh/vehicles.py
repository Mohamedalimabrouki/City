"""Parked cars (prompt 25): the small cars, vans, louages and yellow taxis of a Tunisian street.

Generator axes as in mesh/props.py, with the car's length along x (its nose toward +x), its width
along y and z up; the origin is on the ground under the middle of the car. Each body is a side
profile drawn across the car's width: a lower body (bumpers, bonnet, wheel arches, boot) and a
narrower cabin on top of it (windscreen, roof, rear window), with flush dark glass on its sides,
octagonal wheels, lamps, a grille and mirrors: about 200-260 triangles.

Instancing cannot recolor a piece, so every body color is its own kit piece (`car_<type>_<i>`).
The color pieces of one type share the same part dicts for every material: a tile writes the
geometry once (`write_glb` reuses the accessors of a part seen before) and only adds a material
per color. The yellow taxi is the sedan body with a roof sign. A louage may carry a roof rack
with luggage, drawn on the piece's own stream `stream(seed, "piece", name)`.
"""
from __future__ import annotations

import numpy as np
from shapely.geometry import Polygon, box

from ..rng import stream
from .builder import MeshBuilder, triangulate
from .props import _faces, _orient

BODY, STRIPE = "BODY", "STRIPE"     # stand-ins, renamed to each piece's body and stripe colors
TYPES = ("hatch", "sedan", "van", "louage", "taxi")

# Side profiles (x, z) counter-clockwise from the rear bumper's foot, with the material of the edge
# that starts at each point (None: an underside nobody sees). Arches are cut in later.
_SPECS = {
    "hatch": {      # a small five-door hatchback (the Peugeot 208 or Clio of every Tunisian street)
        "width": 1.74, "wheel": 0.31, "axles": (-1.22, 1.30), "track": 0.03,
        "lower": [(-1.86, 0.30, "car_trim"), (1.90, 0.30, "car_trim"), (1.98, 0.44, BODY), (1.98, 0.66, BODY),
                  (1.84, 0.80, BODY), (0.62, 0.96, BODY), (-1.80, 0.98, BODY), (-1.97, 0.90, BODY),
                  (-1.98, 0.44, "car_trim")],
        "cabin": [(-1.80, 0.98), (0.62, 0.96), (-0.30, 1.44), (-1.50, 1.45)], "tumble": 0.12,
        "windows": [(-0.50, 9.0), (-1.30, -0.62)], "head": (0.52, 0.63), "tail": (0.70, 0.86),
    },
    "sedan": {      # a small saloon with a boot (Peugeot 301, Dacia Logan, Hyundai Accent)
        "width": 1.75, "wheel": 0.31, "axles": (-1.30, 1.35), "track": 0.03,
        "lower": [(-2.12, 0.30, "car_trim"), (2.14, 0.30, "car_trim"), (2.22, 0.44, BODY), (2.22, 0.66, BODY),
                  (2.06, 0.79, BODY), (0.78, 0.97, BODY), (-2.08, 1.00, BODY), (-2.21, 0.90, BODY),
                  (-2.22, 0.46, "car_trim")],
        "cabin": [(-1.40, 1.00), (0.78, 0.97), (-0.05, 1.45), (-0.95, 1.46)], "tumble": 0.12,
        "windows": [(-0.18, 9.0), (-9.0, -0.30)], "head": (0.52, 0.63), "tail": (0.72, 0.88),
    },
    "van": {        # a small van (Peugeot Partner, Renault Kangoo) with a window in its sliding door
        "width": 1.81, "wheel": 0.32, "axles": (-1.35, 1.38), "track": 0.03,
        "lower": [(-2.10, 0.32, "car_trim"), (2.12, 0.32, "car_trim"), (2.19, 0.46, BODY), (2.19, 0.72, BODY),
                  (2.02, 0.92, BODY), (1.32, 1.04, BODY), (-2.17, 1.06, BODY), (-2.19, 0.46, "car_trim")],
        "cabin": [(-2.17, 1.06), (1.32, 1.04), (0.52, 1.78), (-2.10, 1.82)], "tumble": 0.05,
        "windows": [(-0.05, 9.0), (-1.05, -0.20)], "rear_glass": (1.30, 1.66), "head": (0.58, 0.70),
        "tail": (0.62, 1.00),
    },
    "louage": {     # the white shared taxi between towns: a minibus with a colored stripe along its sides
        "width": 1.92, "wheel": 0.33, "axles": (-1.55, 1.65), "track": 0.04,
        "lower": [(-2.46, 0.34, "car_trim"), (2.48, 0.34, "car_trim"), (2.55, 0.48, BODY), (2.55, 0.76, BODY),
                  (2.36, 0.98, BODY), (1.80, 1.10, BODY), (-2.53, 1.12, BODY), (-2.55, 0.48, "car_trim")],
        "cabin": [(-2.53, 1.12), (1.80, 1.10), (0.95, 1.98), (-2.45, 2.04)], "tumble": 0.06,
        "windows": [(0.25, 9.0), (-0.55, 0.12), (-1.40, -0.68), (-9.0, -1.53)], "rear_glass": (1.34, 1.88),
        "head": (0.62, 0.74), "tail": (0.62, 1.02), "stripe": (0.86, 1.00),
    },
}


def vehicle_pieces(seed: int, cfg: dict | None) -> dict:
    """{piece name: glTF parts} for every vehicle type and body color in `[dressing.vehicles]`; empty without it."""
    if not cfg:
        return {}
    shared = {kind: _parts(_shape(spec)) for kind, spec in _SPECS.items()}
    shared["taxi"] = {**shared["sedan"], **_parts(_taxi_sign())}
    rack = _parts(_rack(_SPECS["louage"]))
    out = {}
    for kind in TYPES:
        stripes = cfg.get(kind + "_stripe", [])
        for i, color in enumerate(cfg.get(kind, [])):
            name = f"car_{kind}_{i}"
            names = {BODY: str(color), STRIPE: str(stripes[i % len(stripes)]) if stripes else str(color)}
            parts = {names.get(m, m): part for m, part in shared[kind].items()}
            if kind == "louage" and stream(seed, "piece", name).random() < float(cfg.get("louage_rack", 0.0)):
                parts.update(rack)
            out[name] = parts
    return out


def _parts(mb: MeshBuilder) -> dict:
    """glTF parts without UVs: car paint and glass are plain colors, and a tile pays for every vertex."""
    return {m: {**part, "uv": None} for m, part in mb.gltf_parts().items()}


def _shape(spec: dict) -> MeshBuilder:
    """One vehicle body with its wheels, glass, lamps and mirrors, colored BODY (and STRIPE)."""
    mb = MeshBuilder()
    hw = spec["width"] / 2
    lower = _arched(spec)
    _band(mb, lower, hw)
    for sign in (1.0, -1.0):
        _cap(mb, [(x, z) for x, z, _ in lower], sign * hw, BODY)
    _cabin(mb, spec, hw - spec["tumble"])
    for xa in spec["axles"]:
        for sign in (1.0, -1.0):
            _wheel(mb, xa, sign, hw - spec["track"], spec["wheel"])
    _lamps(mb, spec, hw)
    _mirrors(mb, spec, hw - spec["tumble"])
    z0 = lower[0][1] + 0.12                               # a dark rubbing strip along the sills
    xa, xb = spec["axles"][0] + spec["wheel"] + 0.14, spec["axles"][1] - spec["wheel"] - 0.14
    for sign in (1.0, -1.0):
        y = sign * (hw + 0.004)
        _faces(mb, _orient([[(xa, y, z0), (xb, y, z0), (xb, y, z0 + 0.08), (xa, y, z0 + 0.08)]], (0, sign, 0)), "car_trim")
    if "stripe" in spec:
        z0, z1 = spec["stripe"]
        x0, x1 = lower[0][0] - 0.05, spec["cabin"][1][0] + 0.45
        for sign in (1.0, -1.0):
            y = sign * (hw + 0.004)
            _faces(mb, _orient([[(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)]], (0, sign, 0)), STRIPE)
    return mb


def _arched(spec: dict) -> list:
    """The lower profile with a wheel arch cut into its bottom edge over each axle."""
    pts = list(spec["lower"])
    r, z0 = spec["wheel"], pts[0][1]
    top = 2 * r + 0.05
    arches = []
    for xa in spec["axles"]:
        arches += [(xa - r - 0.11, z0, "car_trim"), (xa - r - 0.03, top, "car_trim"), (xa + r + 0.03, top, "car_trim"),
                   (xa + r + 0.11, z0, None)]
    return [(pts[0][0], z0, None)] + arches + pts[1:]


def _band(mb, profile: list, hw: float) -> None:
    """Quads across the car along every edge of a counter-clockwise (x, z, material) profile."""
    quads: dict = {}
    for (x0, z0, mat), (x1, z1, _) in zip(profile, profile[1:] + profile[:1]):
        if mat is not None:
            quads.setdefault(mat, []).append([(x0, hw, z0), (x1, hw, z1), (x1, -hw, z1), (x0, -hw, z0)])
    for mat, qs in quads.items():
        _faces(mb, qs, mat)


def _cap(mb, pts: list, y: float, mat: str) -> None:
    """A flat side face of a profile at y, facing out (+y for y > 0)."""
    tri = triangulate(Polygon(pts))                       # counter-clockwise in (x, z): faces -y
    if not len(tri):
        return
    if y > 0:
        tri = tri[:, ::-1]
    flat = tri.reshape(-1, 2)
    uniq, inv = np.unique(np.round(flat, 6), axis=0, return_inverse=True)
    pos = np.column_stack([uniq[:, 0], np.full(len(uniq), y), uniq[:, 1]])
    nrm = np.tile([0.0, 1.0 if y > 0 else -1.0, 0.0], (len(uniq), 1))
    mb.add(mat, pos, nrm, np.stack([uniq[:, 0] + y, -uniq[:, 1]], axis=1), inv.reshape(-1, 3))


def _edge_patch(p, q, t0: float, t1: float, y0: float, y1: float, out: float = 0.006) -> list:
    """A quad lying on the profile edge p -> q (from t0 to t1 along it, y0 to y1 across), just outside."""
    p, q = np.asarray(p, dtype=float), np.asarray(q, dtype=float)
    d = q - p
    n = np.array([d[1], -d[0]]) / max(float(np.hypot(*d)), 1e-9) * out   # outward for a counter-clockwise profile
    a, b = p + d * t0 + n, p + d * t1 + n
    return [(a[0], y1, a[1]), (b[0], y1, b[1]), (b[0], y0, b[1]), (a[0], y0, a[1])]


def _cabin(mb, spec: dict, hw: float) -> None:
    """The cabin: roof and pillars in the body color, glass on its sides, windscreen and rear window."""
    c = spec["cabin"]
    _band(mb, [(x, z, None if i == 0 else BODY) for i, (x, z) in enumerate(c)], hw)
    for sign in (1.0, -1.0):
        _cap(mb, c, sign * hw, BODY)
    glass = []
    shell = Polygon(c).buffer(-0.07, join_style="mitre")
    for x0, x1 in spec["windows"]:                        # side windows, split by the pillars
        win = shell.intersection(box(x0, -1.0, x1, 9.0))
        for poly in getattr(win, "geoms", [win]):
            if poly.geom_type == "Polygon" and poly.area > 0.02:
                for sign in (1.0, -1.0):
                    _cap(mb, list(poly.exterior.coords)[:-1], sign * (hw + 0.006), "glass_dark")
    glass.append(_edge_patch(c[1], c[2], 0.06, 0.94, -(hw - 0.08), hw - 0.08))   # windscreen
    if "rear_glass" in spec:                              # upright rear doors: glass in their upper half
        z0, z1 = spec["rear_glass"]
        p, q = c[3], c[0]
        t0, t1 = sorted(((z - p[1]) / (q[1] - p[1]) for z in (z1, z0)))
        glass += [_edge_patch(p, q, t0, t1, 0.05, hw - 0.10), _edge_patch(p, q, t0, t1, -(hw - 0.10), -0.05)]
    else:
        glass.append(_edge_patch(c[3], c[0], 0.08, 0.90, -(hw - 0.10), hw - 0.10))
    _faces(mb, glass, "glass_dark")


def _wheel(mb, xa: float, sign: float, y_out: float, r: float, depth: float = 0.21) -> None:
    """An octagonal tyre (axis across the car), its outer face at y_out on side `sign`. Only the three
    upper tread faces are drawn: the others face the road or hide under the bumpers."""
    a = np.radians(22.5 + 45.0 * np.arange(8))
    ring = np.stack([xa + r * np.cos(a), r + r * np.sin(a)], axis=1)
    yo, yi = sign * y_out, sign * (y_out - depth)
    tread = []
    for k in (0, 1, 2):                                   # front-upper, top and rear-upper tread faces
        (x0, z0), (x1, z1) = ring[k], ring[(k + 1) % 8]
        mid = ((x0 + x1) / 2 - xa, 0.0, (z0 + z1) / 2 - r)
        tread += _orient([[(x0, yo, z0), (x1, yo, z1), (x1, yi, z1), (x0, yi, z0)]], mid)
    face = [[ring[i] for i in idx] for idx in ((0, 1, 2, 3), (0, 3, 4, 7), (4, 5, 6, 7))]
    side = _orient([[(x, yo, z) for x, z in q] for q in face], (0, sign, 0))
    _faces(mb, tread + side, "car_trim")


def _lamps(mb, spec: dict, hw: float) -> None:
    """Headlamps and a grille on the nose, tail lamps on the back."""
    xs = [x for x, _, _ in spec["lower"]]
    xf, xr = max(xs) + 0.006, min(xs) - 0.006
    (h0, h1), (t0, t1) = spec["head"], spec["tail"]
    head, tail, grille = [], [], []
    for sign in (1.0, -1.0):
        ya, yb = sorted((sign * (hw - 0.40), sign * (hw - 0.07)))
        head.append([(xf, ya, h0), (xf, yb, h0), (xf, yb, h1), (xf, ya, h1)])
        ya, yb = sorted((sign * (hw - 0.30), sign * (hw - 0.06)))
        tail.append([(xr, yb, t0), (xr, ya, t0), (xr, ya, t1), (xr, yb, t1)])
    gy = hw - 0.46
    grille.append([(xf, -gy, h0 - 0.04), (xf, gy, h0 - 0.04), (xf, gy, h1 - 0.02), (xf, -gy, h1 - 0.02)])
    _faces(mb, head, "car_light")
    _faces(mb, tail, "car_tail")
    _faces(mb, grille, "car_trim")


def _mirrors(mb, spec: dict, hw: float) -> None:
    """Door mirrors just behind the windscreen's foot: front, outer and top faces."""
    x = spec["cabin"][1][0] - 0.22
    z = spec["cabin"][1][1] + 0.10
    quads = []
    for sign in (1.0, -1.0):
        y0, y1 = sign * hw, sign * (hw + 0.20)
        lo, hi = sorted((y0, y1))
        quads += _orient([[(x + 0.05, lo, z), (x + 0.05, hi, z), (x + 0.05, hi, z + 0.14), (x + 0.05, lo, z + 0.14)]], (1, 0, 0))
        quads += _orient([[(x - 0.05, y1, z), (x + 0.05, y1, z), (x + 0.05, y1, z + 0.14), (x - 0.05, y1, z + 0.14)]], (0, sign, 0))
        quads += _orient([[(x - 0.05, lo, z + 0.14), (x + 0.05, lo, z + 0.14), (x + 0.05, hi, z + 0.14), (x - 0.05, hi, z + 0.14)]], (0, 0, 1))
    _faces(mb, quads, BODY)


def _box_faces(x0, x1, y0, y1, z0, z1) -> list:
    """Top and four sides of a box (no bottom), each facing out."""
    c = ((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
    quads = [[(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
             [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], [(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)],
             [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)]]
    out = []
    for q in quads:
        m = np.mean(q, axis=0)
        out += _orient([q], m - np.array(c))
    return out


def _taxi_sign() -> MeshBuilder:
    """The white TAXI box on a yellow taxi's roof (the sedan's roof is 1.46 m up)."""
    mb = MeshBuilder()
    _faces(mb, _box_faces(-0.62, -0.36, -0.30, 0.30, 1.455, 1.62), "taxi_sign")
    return mb


def _rack(spec: dict) -> MeshBuilder:
    """A louage's roof rack with a tarpaulin bundle of luggage."""
    mb = MeshBuilder()
    hw = spec["width"] / 2 - spec["tumble"] - 0.12
    roof = spec["cabin"][3][1]
    _faces(mb, _box_faces(-2.15, 0.40, -hw, hw, roof - 0.01, roof + 0.12), "iron")
    _faces(mb, _box_faces(-1.70, -0.25, -hw + 0.12, hw - 0.20, roof + 0.12, roof + 0.46), "car_tarp")
    return mb
