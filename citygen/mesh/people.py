"""People (prompt 28): stylized low-poly figures for the streets, souks and cafes, 200-400 triangles each.

Generator axes as in mesh/props.py: the figure faces +y, its right hand is on +x, z up, meters; the origin
is on the ground under the hips, so a seated figure's origin goes under the middle of its seat. Every
figure is a skeleton (hips, knees, ankles, shoulders, elbows, wrists and the head, set by its pose) dressed
by its outfit: lofts of rings (an octagon or hexagon per ring, smooth normals) for the torso, robes and
skirts, bent chains of rings for the limbs (one mitred ring at each joint, so knees and elbows never open),
a latitude-longitude ellipsoid for the head (hair, a hood or a headscarf are cut from the same rings),
octahedron hands and wedge feet. Thin cloth gets real faces on both sides: every hem, sleeve cuff, the
hood's face opening and the safsari's front edge (thin cloth rule). No faces are drawn.

Poses: `stand`, `walk` (mid-stride, the left leg forward and the right arm swinging forward), `sit`
(thighs level on a seat `seat` m up, shins down, feet flat on the ground; the hips' underside touches the
seat), `carry` (walking, a basket or a shopping bag hanging from the right hand). Body types: `male`,
`female` and `child` (a bigger head for its height). Outfits: `jebba` (the long wool robe with a red
chechia and leather slippers), `shirt` (shirt and trousers), `safsari` (the white wrap over head and body,
held at the chin), `dress` (a modern dress; with a `scarf` color it is worn with a headscarf), `boy`
(t-shirt and shorts) and `girl` (a knee-length dress).

Instancing cannot recolor, so each color scheme is its own piece `person_<key>` from `[dressing.people]`.
Height, shoulder width and belly are drawn on the piece's own stream `stream(seed, "piece", name)`.
Anatomy is in `_BODIES` (fractions of the height); heights, seat, jitter and colors come from the style.
"""
from __future__ import annotations

import math

import numpy as np

from ..rng import stream
from .builder import MeshBuilder, add_sheet
from .plants import smooth_add
from .props import _bar, _faces, _orient

PEOPLE = {   # `[dressing.people]` in the style overrides these
    "seat": 0.45,
    "heights": {"male": [1.68, 1.80], "female": [1.60, 1.70], "child": [1.10, 1.30]},
    "shoulders": 0.05,          # shoulder width varies by this fraction either way
    "belly": 0.035,             # meters of belly at most (men only)
    "lean": 6.0,                # degrees a seated figure leans back
}

# Body proportions as fractions of the height: heights of the joints, half widths and depths, radii.
_BODIES = {
    "male": {"head": 0.135, "shoulder": 0.815, "chest": 0.72, "waist": 0.615, "hip": 0.525, "knee": 0.285,
             "ankle": 0.045, "shoulder_w": 0.118, "waist_w": 0.088, "hip_w": 0.096, "chest_d": 0.064,
             "hip_x": 0.053, "thigh_r": 0.042, "knee_r": 0.030, "ankle_r": 0.019, "arm_r": 0.025,
             "elbow_r": 0.021, "wrist_r": 0.016, "neck_r": 0.027, "upper_arm": 0.18, "forearm": 0.155,
             "foot": 0.15, "stride": 0.36},
    "female": {"head": 0.14, "shoulder": 0.81, "chest": 0.72, "waist": 0.62, "hip": 0.52, "knee": 0.285,
               "ankle": 0.045, "shoulder_w": 0.106, "waist_w": 0.080, "hip_w": 0.104, "chest_d": 0.064,
               "hip_x": 0.055, "thigh_r": 0.044, "knee_r": 0.029, "ankle_r": 0.018, "arm_r": 0.022,
               "elbow_r": 0.018, "wrist_r": 0.014, "neck_r": 0.024, "upper_arm": 0.18, "forearm": 0.15,
               "foot": 0.145, "stride": 0.33},
    "child": {"head": 0.17, "shoulder": 0.76, "chest": 0.67, "waist": 0.58, "hip": 0.49, "knee": 0.27,
              "ankle": 0.045, "shoulder_w": 0.11, "waist_w": 0.085, "hip_w": 0.09, "chest_d": 0.06,
              "hip_x": 0.05, "thigh_r": 0.042, "knee_r": 0.030, "ankle_r": 0.02, "arm_r": 0.024,
              "elbow_r": 0.02, "wrist_r": 0.016, "neck_r": 0.026, "upper_arm": 0.17, "forearm": 0.145,
              "foot": 0.15, "stride": 0.38},
}
_OUTFITS = {   # body type and default colors per outfit; `hem` is the hem's height as a fraction of the height
    "jebba": {"body": "male", "robe": "cloth_wool_cream", "trim": "cloth_wool_brown", "under": "cloth_white",
              "cap": "chechia_red", "shoes": "leather_yellow", "skin": "skin_2", "hair": "hair_grey", "hem": 0.055},
    "shirt": {"body": "male", "shirt": "cloth_sky", "trousers": "cloth_charcoal", "shoes": "shoe_dark",
              "skin": "skin_2", "hair": "hair_black", "sleeves": "long"},
    "safsari": {"body": "female", "wrap": "cloth_safsari", "shoes": "shoe_dark", "skin": "skin_2", "hem": 0.05},
    "dress": {"body": "female", "dress": "cloth_teal", "legs": "skin_2", "shoes": "shoe_dark", "skin": "skin_2",
              "hair": "hair_brown", "sleeves": "three_quarter", "hem": 0.2},
    "boy": {"body": "child", "shirt": "cloth_2", "shorts": "cloth_navy", "shoes": "shoe_dark", "skin": "skin_2",
            "hair": "hair_black"},
    "girl": {"body": "child", "dress": "cloth_rose", "shoes": "shoe_dark", "skin": "skin_2", "hair": "hair_black",
             "hem": 0.36},
}
_CARRY = {"basket": "basket_straw", "bag": "bag_plastic", "bread": "bread_crust"}


def people_pieces(seed: int, cfg: dict | None) -> dict:
    """{piece name: glTF parts} for every entry of `[dressing.people.pieces]`; empty without it."""
    cfg = {**PEOPLE, **(cfg or {})}
    out = {}
    for key, spec in (cfg.get("pieces") or {}).items():
        name = "person_" + key
        out[name] = {m: {**part, "uv": None} for m, part in figure(name, spec, cfg, seed).gltf_parts().items()}
    return out


def figure(name: str, spec: dict, cfg: dict, seed: int) -> MeshBuilder:
    """One dressed figure: `spec` holds its outfit, pose and colors (outfit defaults fill the rest)."""
    look = {**_OUTFITS[spec["outfit"]], **spec}
    body = look["body"]
    rng = stream(seed, "piece", name)
    lo, hi = cfg["heights"][body]
    h = float(rng.uniform(lo, hi))
    shoulders = 1.0 + float(rng.uniform(-1.0, 1.0)) * float(cfg["shoulders"])
    belly = float(rng.uniform(0.0, 1.0)) * float(cfg["belly"])         # always drawn; only men keep it
    belly = belly if body == "male" else 0.0
    sk = _skeleton(_BODIES[body], h, look["pose"], shoulders, belly, float(cfg["seat"]), float(cfg["lean"]))
    mb = MeshBuilder()
    _DRESS[look["outfit"]](mb, sk, look)
    return mb


# --- geometry helpers -----------------------------------------------------------------------------

def _unit(v) -> np.ndarray:
    v = np.asarray(v, dtype=np.float64)
    return v / max(float(np.linalg.norm(v)), 1e-12)


def _hring(c, hw: float, hd: float, sk: dict | None = None) -> tuple:
    """A level ring (center, x half axis, y half axis), turned with the upper body when `sk` leans."""
    c, u, v = np.asarray(c, dtype=np.float64), np.array([hw, 0.0, 0.0]), np.array([0.0, hd, 0.0])
    if sk is not None:
        c, u, v = sk["up"](c), sk["R"] @ u, sk["R"] @ v
    return c, u, v


def _loft(mb: MeshBuilder, rings: list, mat: str, sides: int = 8, inner: bool = False,
          caps: tuple = (False, False), phase: float = 0.0) -> None:
    """A smooth surface through rings (center, u, v), points c + u cos t + v sin t (t = phase + 2 pi k /
    sides; with 8 sides one point lies on +v, the front). Faces point away from the rings' axis; `inner`
    adds the last band again facing in, just inside (a hem seen from below); `caps` close the ends."""
    t = phase + np.arange(sides) * 2 * math.pi / sides
    cos, sin = np.cos(t)[:, None], np.sin(t)[:, None]
    pos = np.concatenate([c + cos * u + sin * v for c, u, v in rings])
    faces, axis = [], []
    for i in range(len(rings) - 1):
        for k in range(sides):
            a, b = i * sides + k, i * sides + (k + 1) % sides
            faces += [[a, b, b + sides], [a, b + sides, a + sides]]
            axis += [(rings[i][0] + rings[i + 1][0]) / 2] * 2
    faces = np.array(faces)
    tri = pos[faces]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    if np.sum(n * (tri.mean(axis=1) - np.array(axis))) < 0:
        faces = faces[:, ::-1]
    smooth_add(mb, mat, pos, faces)
    if inner:
        last = faces[-2 * sides:]
        c0, c1 = rings[-2][0], rings[-1][0]
        ring_of = np.repeat(np.arange(len(rings)), sides)
        centers = np.where((ring_of == len(rings) - 1)[:, None], c1, c0)
        shrunk = centers + (pos - centers) * 0.94
        smooth_add(mb, mat, shrunk, last[:, ::-1])
    for end, cap in ((0, caps[0]), (len(rings) - 1, caps[1])):
        if cap:
            c = rings[end][0]
            out = c - rings[1 if end == 0 else end - 1][0]
            ring = pos[end * sides:(end + 1) * sides]
            tris = [[c, ring[k], ring[(k + 1) % sides]] for k in range(sides)]
            _add_flat(mb, tris, out, mat)


def _add_flat(mb: MeshBuilder, tris, out, mat: str) -> None:
    """Flat triangles turned to face `out`."""
    tris = np.asarray(tris, dtype=np.float64)
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    flip = (n @ np.asarray(out, dtype=np.float64)) < 0
    tris[flip] = tris[flip][:, ::-1]
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]
    pos = tris.reshape(-1, 3)
    mb.add(mat, pos, np.repeat(n, 3, axis=0), pos[:, :2], np.arange(len(pos)).reshape(-1, 3))


def _chain(mb: MeshBuilder, pts: list, radii: list, mats: list, side, sides: int = 6, inner: bool = False) -> None:
    """A bent tube through `pts` (a limb): one ring per point, mitred at the joints so a bent knee or
    elbow stays closed and keeps its thickness; band i is drawn in mats[i] (a sleeve, then skin)."""
    pts = [np.asarray(p, dtype=np.float64) for p in pts]
    dirs = [_unit(q - p) for p, q in zip(pts[:-1], pts[1:])]
    rings = []
    for i, (p, r) in enumerate(zip(pts, radii)):
        d_in, d_out = dirs[max(i - 1, 0)], dirs[min(i, len(dirs) - 1)]
        n = _unit(d_in + d_out)
        b = _unit(np.asarray(side, dtype=np.float64) - np.dot(side, n) * n)
        w = np.cross(n, b)
        u, v = b * r, w * r
        bend = d_out - d_in
        bend = bend - np.dot(bend, n) * n
        if np.linalg.norm(bend) > 1e-6:                     # stretch across the bend: a mitre
            m, stretch = _unit(bend), 1.0 / max(float(np.dot(n, d_out)), 0.3) - 1.0
            u, v = u + stretch * np.dot(u, m) * m, v + stretch * np.dot(v, m) * m
        rings.append((p, u, v))
    i = 0
    while i < len(mats):
        j = i
        while j + 1 < len(mats) and mats[j + 1] == mats[i]:
            j += 1
        _loft(mb, rings[i:j + 2], mats[i], sides, inner=inner and j == len(mats) - 1)
        i = j + 1


def _ellipsoid(c, r, sk: dict | None = None, front_vertex: bool = False, segs: int = 8,
               lats: tuple = (-45.0, 0.0, 45.0)) -> tuple:
    """A latitude-longitude ellipsoid (three rings at `lats` degrees and two poles): positions,
    normals, outward faces and each face's direction on the unit sphere (for cutting hair or a hood)."""
    rx, ry, rz = r
    lon = math.pi / 2 + (0.0 if front_vertex else math.pi / segs) + np.arange(segs) * 2 * math.pi / segs
    unit = [np.array([0.0, 0.0, -1.0])]
    for lat in np.radians(list(lats)):
        unit += [np.array([math.cos(lat) * math.cos(a), math.cos(lat) * math.sin(a), math.sin(lat)]) for a in lon]
    unit.append(np.array([0.0, 0.0, 1.0]))
    unit = np.array(unit)
    top = len(unit) - 1
    faces = [[0, 1 + (k + 1) % segs, 1 + k] for k in range(segs)]
    for ring in range(2):
        for k in range(segs):
            a, b = 1 + ring * segs + k, 1 + ring * segs + (k + 1) % segs
            faces += [[a, b, b + segs], [a, b + segs, a + segs]]
    faces += [[top, 1 + 2 * segs + k, 1 + 2 * segs + (k + 1) % segs] for k in range(segs)]
    faces = np.array(faces)
    dirs = np.array([_unit(d) for d in unit[faces].mean(axis=1)])
    pos = np.asarray(c, dtype=np.float64) + unit * np.array([rx, ry, rz])
    nrm = np.array([_unit(n) for n in unit / np.array([rx, ry, rz])])
    tri = pos[faces]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    flip = np.sum(n * (tri.mean(axis=1) - c), axis=1) < 0
    faces[flip] = faces[flip][:, ::-1]
    if sk is not None:
        pos, nrm = sk["up"](pos), nrm @ sk["R"].T
    return pos, nrm, faces, dirs


def _add_indexed(mb: MeshBuilder, mat: str, pos, nrm, faces) -> None:
    """Add some faces of an indexed mesh, keeping only the vertices they use."""
    faces = np.asarray(faces)
    if not len(faces):
        return
    used, inv = np.unique(faces.reshape(-1), return_inverse=True)
    mb.add(mat, pos[used], nrm[used], pos[used][:, :2], inv.reshape(-1, 3))


def _blob(mb: MeshBuilder, c, along, across, radii, mat: str) -> None:
    """A smooth octahedron (a hand, a bun of hair, a loaf): radii along `along`, `across` and the third axis."""
    a, b = _unit(along), _unit(across)
    b = _unit(b - np.dot(b, a) * a)
    t = np.cross(a, b)
    c = np.asarray(c, dtype=np.float64)
    pos = np.array([c + a * radii[0], c - a * radii[0], c + b * radii[1], c - b * radii[1], c + t * radii[2], c - t * radii[2]])
    faces = np.array([[0, 2, 4], [2, 1, 4], [1, 3, 4], [3, 0, 4], [2, 0, 5], [1, 2, 5], [3, 1, 5], [0, 3, 5]])
    tri = pos[faces]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    flip = np.sum(n * (tri.mean(axis=1) - c), axis=1) < 0
    faces[flip] = faces[flip][:, ::-1]
    smooth_add(mb, mat, pos, faces)


def _foot(mb: MeshBuilder, x: float, toe_y: float, pitch: float, length: float, h: float, mat: str) -> None:
    """A shoe: a wedge from heel to toe (no sole face), its toe tip on the ground at (x, toe_y), the heel
    lifted by `pitch` radians (the back foot of a stride)."""
    hw_heel, hw_toe = 0.034 * h / 1.7, 0.045 * h / 1.7
    zh, zt = 0.05 * h, 0.028 * h
    y0, y1 = -length, 0.0
    box = np.array([[-hw_heel, y0, 0], [hw_heel, y0, 0], [hw_toe, y1, 0], [-hw_toe, y1, 0],
                    [-hw_heel * 0.9, y0, zh], [hw_heel * 0.9, y0, zh], [hw_toe * 0.8, y1 - 0.02 * h, zt],
                    [-hw_toe * 0.8, y1 - 0.02 * h, zt]], dtype=np.float64)
    cp, sp = math.cos(pitch), math.sin(pitch)
    y, z = box[:, 1].copy(), box[:, 2].copy()
    box[:, 1], box[:, 2] = y * cp + z * sp, -y * sp + z * cp          # heel up about the toe tip
    box += np.array([x, toe_y, 0.0])
    quads = [[4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]]
    mid = box.mean(axis=0)
    _faces(mb, [q for idx in quads for q in _orient([box[idx]], box[idx].mean(axis=0) - mid)], mat)


# --- the skeleton ---------------------------------------------------------------------------------

def _knee(hip, ankle, l1: float, l2: float, bend) -> np.ndarray:
    """The middle joint of a two-bone limb (a knee or an elbow), bent toward `bend`."""
    hip, ankle = np.asarray(hip, dtype=np.float64), np.asarray(ankle, dtype=np.float64)
    d = ankle - hip
    dist = min(float(np.linalg.norm(d)), l1 + l2 - 1e-6)
    u = _unit(d)
    a = (l1 * l1 - l2 * l2 + dist * dist) / (2 * dist)
    perp = _unit(np.asarray(bend, dtype=np.float64) - np.dot(bend, u) * u)
    return hip + u * a + perp * math.sqrt(max(l1 * l1 - a * a, 0.0))


def _skeleton(b: dict, h: float, pose: str, shoulders: float, belly: float, seat: float, lean: float) -> dict:
    """Joints and sizes of one figure in its pose."""
    k = {key: val * h for key, val in b.items()}
    sk = {"h": h, "pose": pose, "belly": belly, "seat": seat, "sw": k["shoulder_w"] * shoulders, **{
        key: k[key] for key in ("waist_w", "hip_w", "chest_d", "thigh_r", "knee_r", "ankle_r", "arm_r", "elbow_r",
                                "wrist_r", "neck_r", "upper_arm", "forearm", "foot")}}
    thigh, shin = k["hip"] - k["knee"], k["knee"] - k["ankle"]
    hx, az, foot = k["hip_x"], k["ankle"], k["foot"]
    toe = 0.78 * foot                                        # ankle to toe tip; the heel is behind
    legs, feet = {}, []
    if pose == "sit":                                        # thighs level on the seat, shins down
        hip_z, knee_z = seat + k["thigh_r"], seat + k["knee_r"]
        for side in (-1.0, 1.0):
            hip = np.array([side * hx, 0.0, hip_z])
            knee = np.array([side * (hx + 0.006 * h), thigh, knee_z])
            ankle = np.array([side * (hx + 0.008 * h), thigh + 0.012 * h, az])
            legs[side] = [hip, knee, ankle]
            feet.append((ankle[0], ankle[1] + toe, 0.0))
    elif pose in ("walk", "carry"):                          # the left leg forward, the right one pushing off
        half = k["stride"] / 2
        hip_z = az + math.sqrt((0.995 * (thigh + shin)) ** 2 - half * half)
        front = np.array([-hx * 0.75, half, az])
        pitch = math.radians(28.0)
        toe_y = -half + toe
        back = np.array([hx * 0.75, toe_y - toe * math.cos(pitch) + az * math.sin(pitch),
                         toe * math.sin(pitch) + az * math.cos(pitch)])
        for side, ankle in ((-1.0, front), (1.0, back)):
            hip = np.array([side * hx, 0.0, hip_z])
            legs[side] = [hip, _knee(hip, ankle, thigh, shin, (0.0, 1.0, 0.0)), ankle]
        feet += [(front[0], half + toe, 0.0), (back[0], toe_y, pitch)]
    else:                                                    # standing, feet a little apart
        hip_z = k["hip"]
        for side in (-1.0, 1.0):
            hip = np.array([side * hx, 0.0, hip_z])
            ankle = np.array([side * (hx + 0.006 * h), 0.004 * h, az])
            legs[side] = [hip, _knee(hip, ankle, thigh, shin * 1.003, (0.0, 1.0, 0.0)), ankle]
            feet.append((ankle[0], ankle[1] + toe, 0.0))
    dz = hip_z - k["hip"]
    pivot = np.array([0.0, 0.0, hip_z])
    a = math.radians(lean) if pose == "sit" else 0.0
    R = np.array([[1.0, 0.0, 0.0], [0.0, math.cos(a), -math.sin(a)], [0.0, math.sin(a), math.cos(a)]])
    sk.update(legs=legs, feet=feet, hip_z=hip_z, dz=dz, R=R, up=lambda p: pivot + (np.asarray(p) - pivot) @ R.T,
              z={key: k[key] + dz for key in ("shoulder", "chest", "waist")}, thigh=thigh, shin=shin)
    rz = k["head"] / 2
    sk["head_r"] = (rz * 0.76, rz * 0.88, rz)
    sk["head_c"] = sk["up"](np.array([0.0, 0.012 * h, h - rz + dz]))
    sk["shoulder"] = {s: sk["up"](np.array([s * (sk["sw"] - 1.1 * k["arm_r"]), 0.0, k["shoulder"] + dz - 0.5 * k["arm_r"]]))
                      for s in (-1.0, 1.0)}
    sk["leg_pts"] = _leg_samples(legs, sk)
    return sk


def _leg_samples(legs: dict, sk: dict) -> list:
    """Points along both legs' axes with their radii, to fit a robe or a skirt around a stride."""
    out = []
    for hip, knee, ankle in legs.values():
        for p, q, r0, r1 in ((hip, knee, sk["thigh_r"], sk["knee_r"]), (knee, ankle, sk["knee_r"], sk["ankle_r"])):
            for t in np.linspace(0.0, 1.0, 9):
                out.append((p + (q - p) * t, r0 + (r1 - r0) * t))
    return out


def _arms(sk: dict, pose: str) -> dict:
    """{side: (shoulder, elbow, wrist)} for a free-hanging or swinging pair of arms."""
    ua, fa = sk["upper_arm"], sk["forearm"]
    swing = {"stand": {-1.0: 0.04, 1.0: 0.04}, "walk": {-1.0: -0.32, 1.0: 0.38},
             "carry": {-1.0: -0.30, 1.0: 0.0}}.get(pose, {-1.0: 0.0, 1.0: 0.0})
    flex = {"stand": {-1.0: 0.2, 1.0: 0.2}, "walk": {-1.0: 0.12, 1.0: 0.4},
            "carry": {-1.0: 0.12, 1.0: 0.05}}.get(pose, {-1.0: 0.2, 1.0: 0.2})
    out = {}
    for side in (-1.0, 1.0):
        s = sk["shoulder"][side]
        if pose == "sit":                                    # hands resting on the thighs
            hip, knee, _ = sk["legs"][side]
            wrist = hip + (knee - hip) * 0.55 + np.array([side * 0.004 * sk["h"], 0.0, sk["thigh_r"] + sk["wrist_r"] * 2.2])
            out[side] = (s, _knee(s, wrist, ua, fa, (side * 0.5, -1.0, 0.0)), wrist)
            continue
        spread, sw_, fl = 0.16, swing[side], flex[side]
        d1 = _unit([side * math.sin(spread), math.sin(sw_) * math.cos(spread), -math.cos(sw_) * math.cos(spread)])
        e = s + ua * d1
        d2 = _unit([side * math.sin(spread) * 0.6, math.sin(sw_ + fl), -math.cos(sw_ + fl)])
        out[side] = (s, e, e + fa * d2)
    return out


def _carry_arm(sk: dict, side: float, clear: float, item: str) -> tuple:
    """The loaded arm: its hand held out just past the clothes (`clear` m from the middle) above the item."""
    s = sk["shoulder"][side]
    width = 0.1 if item == "basket" else 0.065
    wrist = np.array([side * (clear + width + 0.012), 0.02 * sk["h"],
                      s[2] - 0.93 * (sk["upper_arm"] + sk["forearm"])])
    reach = sk["upper_arm"] + sk["forearm"] - 1e-3
    d = wrist - s
    if np.linalg.norm(d) > reach:
        wrist = s + _unit(d) * reach
    return s, _knee(s, wrist, sk["upper_arm"], sk["forearm"], (side * 0.6, -1.0, 0.0)), wrist


# --- body parts -----------------------------------------------------------------------------------

def _head(mb: MeshBuilder, sk: dict, skin: str, hair: str | None = None, style: str = "short",
          hide=None) -> None:
    """The head: skin, with hair cut from the same rings (`short`, `long` with a bun at the nape) or none;
    faces whose direction `hide` rejects (under a hood or a cap) are left out."""
    pos, nrm, faces, dirs = _ellipsoid(sk["head_c"], sk["head_r"], sk)
    keep = np.ones(len(faces), bool) if hide is None else ~hide(dirs)
    is_hair = np.zeros(len(faces), bool)
    if hair and style == "short":
        is_hair = ((dirs[:, 2] > 0.2) & (dirs[:, 1] < 0.75)) | (dirs[:, 2] > 0.55) | ((dirs[:, 2] > -0.6) & (dirs[:, 1] < -0.5))
    elif hair:
        is_hair = (dirs[:, 2] > 0.5) | ((dirs[:, 2] > -0.75) & (dirs[:, 1] < 0.2))
    _add_indexed(mb, skin, pos, nrm, faces[keep & ~is_hair])
    if hair:
        _add_indexed(mb, hair, pos, nrm, faces[keep & is_hair])
    if hair and style == "long":                             # hair gathered low at the back
        rx, ry, rz = sk["head_r"]
        c = sk["up"](sk["head_c"] + np.array([0.0, -ry * 0.78, -rz * 0.62]))
        _blob(mb, c, sk["R"] @ np.array([0.0, 0.25, -1.0]), (1.0, 0.0, 0.0), (rz * 0.62, rx * 0.62, ry * 0.36), hair)


def _under_hood(dirs) -> np.ndarray:
    """Head faces a hood hides: the back and the crown."""
    return (dirs[:, 1] < -0.2) | (dirs[:, 2] > 0.6)


def _neck(mb: MeshBuilder, sk: dict, skin: str) -> None:
    c, r = sk["head_c"], sk["head_r"]
    p0 = sk["up"](np.array([0.0, 0.0, sk["z"]["shoulder"] - 0.01 * sk["h"]]))
    p1 = c - sk["R"] @ np.array([0.0, 0.0, r[2] * 0.4])
    _chain(mb, [p0, p1], [sk["neck_r"], sk["neck_r"] * 0.92], [skin], (1.0, 0.0, 0.0), sides=6)


def _hood(mb: MeshBuilder, sk: dict, mat: str) -> tuple:
    """A hood (the safsari's top, a headscarf) round the head, open on the face, its rim cloth doubled
    inside; returns the ring at its foot (chin level) where the wrap or the scarf's drape carries on."""
    rx, ry, rz = sk["head_r"]
    c = sk["head_c"] + sk["R"] @ np.array([0.0, -0.1 * ry, 0.03 * rz])
    r = (rx * 1.2, ry * 1.15, rz * 1.13)
    pos, nrm, faces, dirs = _ellipsoid(c, r, sk, front_vertex=True, lats=(-45.0, 15.0, 50.0))
    face = (dirs[:, 1] > 0.6) & (dirs[:, 2] > -0.75) & (dirs[:, 2] < 0.2)      # chin to brow, 90 degrees wide
    bottom = dirs[:, 2] < -0.75
    keep = faces[~face & ~bottom]
    _add_indexed(mb, mat, pos, nrm, keep)
    rim = ~face & ~bottom & (dirs[:, 1] > -0.2) & (dirs[:, 2] < 0.75)
    inside = c + (pos - c) * 0.95
    _add_indexed(mb, mat, inside, -nrm, faces[rim][:, ::-1])
    s45 = math.sqrt(0.5)
    return (c - sk["R"] @ np.array([0.0, 0.0, r[2] * s45]), sk["R"] @ np.array([r[0] * s45, 0.0, 0.0]),
            sk["R"] @ np.array([0.0, r[1] * s45, 0.0]))


def _torso(mb: MeshBuilder, sk: dict, mat: str, bottom: float, top: bool = True, bust: float = 1.0) -> list:
    """The upper body from `bottom` (a height) to the shoulders and, with `top`, the closed neckline."""
    rings = _torso_rings(sk, bottom, top, bust)
    _loft(mb, rings, mat, 8, caps=(False, top))
    return rings


def _torso_rings(sk: dict, bottom: float, top: bool = True, bust: float = 1.0, extra: float = 0.0) -> list:
    """Rings of the upper body from `bottom` (a height) up to the shoulders and, with `top`, the
    neckline; `extra` m of looseness (a robe). Bottom first."""
    z, sw, d = sk["z"], sk["sw"], sk["chest_d"]
    belly = sk["belly"]
    rings = [_hring((0.0, belly * 0.4, bottom), sk["waist_w"] + extra, d * 0.92 + belly * 0.6 + extra, sk),
             _hring((0.0, belly * 0.5, z["waist"]), sk["waist_w"] + extra, d * 0.92 + belly + extra, sk),
             _hring((0.0, 0.0, z["chest"]), sw * 0.87 + extra, d * bust + extra, sk),
             _hring((0.0, -0.004 * sk["h"], z["shoulder"]), sw + extra * 0.5, d * 0.8 + extra * 0.5, sk)]
    if top:
        rings.append(_hring((0.0, -0.004 * sk["h"], z["shoulder"] + 0.028 * sk["h"]), sk["neck_r"] * 1.7,
                            sk["neck_r"] * 1.5, sk))
    return rings


def _pelvis(mb: MeshBuilder, sk: dict, mat: str) -> None:
    """Trousers (or shorts) from the waist down to the crotch, closed under it; on a seat, flat on it."""
    z, d, h = sk["z"], sk["chest_d"], sk["h"]
    low = sk["seat"] if sk["pose"] == "sit" else sk["hip_z"] - 0.035 * h
    rings = [_hring((0.0, sk["belly"] * 0.4, z["waist"] - 0.01 * h), sk["waist_w"] + 0.004 * h, d * 0.95 + sk["belly"] * 0.6),
             _hring((0.0, -0.004 * h, sk["hip_z"]), sk["hip_w"], d * 0.98),
             _hring((0.0, -0.006 * h, low), sk["hip_w"] * 0.92, d * 0.9)]
    _loft(mb, rings, mat, 8, caps=(False, True))


def _legs(mb: MeshBuilder, sk: dict, mats: tuple, from_knee: bool = False, short: float = 0.0) -> None:
    """Both legs: thigh and shin in mats (thigh, shin); `short` cuts the thigh's cloth that far down it
    (shorts), `from_knee` draws only the shins (under a skirt)."""
    for side, (hip, knee, ankle) in sk["legs"].items():
        if from_knee:
            _chain(mb, [knee, ankle], [sk["knee_r"], sk["ankle_r"]], [mats[1]], (1.0, 0.0, 0.0))
        elif short:
            mid = hip + (knee - hip) * short
            r = sk["thigh_r"] + (sk["knee_r"] - sk["thigh_r"]) * short
            _chain(mb, [hip, mid, knee, ankle], [sk["thigh_r"], r, sk["knee_r"], sk["ankle_r"]],
                   [mats[0], mats[1], mats[1]], (1.0, 0.0, 0.0))
        else:
            _chain(mb, [hip, knee, ankle], [sk["thigh_r"], sk["knee_r"], sk["ankle_r"]], list(mats), (1.0, 0.0, 0.0))


def _feet(mb: MeshBuilder, sk: dict, mat: str) -> None:
    for x, toe_y, pitch in sk["feet"]:
        _foot(mb, x, toe_y, pitch, sk["foot"], sk["h"], mat)


def _arm(mb: MeshBuilder, sk: dict, joints: tuple, side: float, mats: tuple, cut: float = 1.0,
         deltoid: bool = True) -> None:
    """One arm through (shoulder, elbow, wrist): cloth in mats[0] down to `cut` (0 the shoulder, 1 the
    elbow, 2 the wrist), skin or an undersleeve in mats[1] below it, a mats[2] hand at the end. The
    `deltoid` ring rounds the shoulder where no cape or seat pose hides it."""
    s, e, w = joints
    ra, re, rw = sk["arm_r"], sk["elbow_r"], sk["wrist_r"]
    marks = [(0.0, s, ra), (1.0, e, re), (2.0, w, rw)]
    if 0.0 < cut < 2.0 and cut != 1.0:
        a, b, r0, r1 = (s, e, ra, re) if cut < 1.0 else (e, w, re, rw)
        t = cut % 1.0
        marks.append((cut, a + (b - a) * t, r0 + (r1 - r0) * t))
    marks.sort(key=lambda m: m[0])
    if deltoid:
        marks.insert(0, (-0.1, s - _unit(e - s) * ra * 0.9, ra * 0.6))
    mats_ = [mats[0] if (m0[0] + m1[0]) / 2 < cut else mats[1] for m0, m1 in zip(marks[:-1], marks[1:])]
    _chain(mb, [m[1] for m in marks], [m[2] for m in marks], mats_, _side_axis(side))
    _hand(mb, sk, e, w, side, mats[2])


def _side_axis(side: float) -> tuple:
    return (side, 0.0, 0.0)


def _hand(mb: MeshBuilder, sk: dict, e, w, side: float, skin: str) -> None:
    d = _unit(w - e)
    r = sk["wrist_r"]
    _blob(mb, w + d * r * 2.2, d, (0.0, 1.0, 0.0) if abs(d[1]) < 0.9 else (1.0, 0.0, 0.0), (r * 2.3, r * 1.6, r * 1.15), skin)


def _skirt(mb: MeshBuilder, sk: dict, mat: str, levels: list, hem: float) -> list:
    """A skirt from level rings [(height, half width, half depth)] down to the hem, the hem doubled."""
    rings = _skirt_rings(sk, levels, hem)
    _loft(mb, rings, mat, 8, inner=True)
    return rings


def _skirt_rings(sk: dict, levels: list, hem: float) -> list:
    """Level rings of a robe's or a skirt's lower part, from the top down to the hem, each widened round
    the legs at its height (a stride spreads the hem)."""
    return [_fit(sk, z, hw, hd) for z, hw, hd in levels + [(hem, levels[-1][1], levels[-1][2])]]


def _fit(sk: dict, z: float, hw: float, hd: float, margin: float = 0.012) -> tuple:
    """A level ring at z of at least (hw, hd), grown to hold the legs from z to 0.25 m above it."""
    near = [(p, r) for p, r in sk["leg_pts"] if z - 0.03 <= p[2] <= z + 0.25]
    cy = 0.0
    if near:
        y0 = min(p[1] - r for p, r in near) - margin
        y1 = max(p[1] + r for p, r in near) + margin
        x1 = max(abs(p[0]) + r for p, r in near) + margin
        grow = 1.0 / math.cos(math.pi / 8)                 # an octagon's flat sides lie inside its ellipse
        if (y1 - y0) * grow > 2 * hd:
            hd, cy = (y1 - y0) / 2 * grow, (y1 + y0) / 2
        hw = max(hw, x1 * grow)
    return _hring((0.0, cy, z), hw, hd)


def _lap(mb: MeshBuilder, sk: dict, mat: str, hw: float, hem: float) -> None:
    """A seated figure's robe or skirt below the waist: over the level thighs to the knees, then hanging
    from the knees down to the hem round the shins, the hem doubled. Its underside lies on the seat."""
    seat, h = sk["seat"], sk["h"]
    _, knee, ankle = sk["legs"][1.0]
    kx = abs(knee[0]) + sk["knee_r"] + 0.018 * h
    rings = [(np.array([0.0, 0.0, sk["hip_z"]]), np.array([hw, 0.0, 0.0]), np.array([0.0, 0.0, sk["thigh_r"]])),
             (np.array([0.0, knee[1], knee[2]]), np.array([kx, 0.0, 0.0]), np.array([0.0, 0.0, knee[2] - seat])),
             (np.array([0.0, knee[1] + 0.006 * h, knee[2] - 0.04 * h]), np.array([kx * 1.02, 0.0, 0.0]),
              _unit([0.0, 1.0, 1.0]) * (knee[2] - seat + 0.012 * h)),
             (np.array([0.0, ankle[1] - 0.01 * h, hem]), np.array([kx * 1.08, 0.0, 0.0]),
              np.array([0.0, sk["knee_r"] + 0.035 * h, 0.0]))]
    _loft(mb, rings, mat, 8, inner=True)


def _seat_rings(sk: dict, hw: float, hd: float) -> list:
    """A seated figure's clothed hips below the waist: a ring at the hips and one flat on the seat."""
    h = sk["h"]
    return [_hring((0.0, -0.01 * h, sk["hip_z"]), hw, hd * 1.05), _hring((0.0, -0.012 * h, sk["seat"]), hw * 0.97, hd)]


def _strip(mb: MeshBuilder, pts: list, width: float, mat: str, out=(0.0, 1.0, 0.0)) -> None:
    """A thin band of cloth along `pts` (an edge or a trim), faces on both sides."""
    tris = []
    out = np.asarray(out, dtype=np.float64)
    for p, q in zip(pts[:-1], pts[1:]):
        p, q = np.asarray(p, dtype=np.float64), np.asarray(q, dtype=np.float64)
        a = _unit(np.cross(q - p, out)) * width / 2
        tris += [[p - a, p + a, q + a], [p - a, q + a, q - a]]
    tris = np.array(tris)
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    flip = (n @ out) < 0
    tris[flip] = tris[flip][:, ::-1]
    add_sheet(mb, tris, mat, 0.004)


def _on(rings: list, x: float, z: float, lift: float) -> np.ndarray:
    """The point of a loft of level rings in front of (x, z), `lift` m out of it."""
    zs = [c[2] for c, _, _ in rings]
    order = np.argsort(zs)
    zs = np.array(zs)[order]
    k = int(np.clip(np.searchsorted(zs, z), 1, len(zs) - 1))
    (c0, u0, v0), (c1, u1, v1) = rings[order[k - 1]], rings[order[k]]
    t = float(np.clip((z - zs[k - 1]) / max(zs[k] - zs[k - 1], 1e-9), 0.0, 1.0))
    c, hw, hd = c0 + (c1 - c0) * t, np.linalg.norm(u0) + (np.linalg.norm(u1) - np.linalg.norm(u0)) * t, \
        np.linalg.norm(v0) + (np.linalg.norm(v1) - np.linalg.norm(v0)) * t
    y = c[1] + hd * math.sqrt(max(0.0, 1.0 - ((x - c[0]) / hw) ** 2)) * math.cos(math.pi / 8)
    return np.array([x, y + lift, z])


# --- carried things -------------------------------------------------------------------------------

def _basket(mb: MeshBuilder, sk: dict, wrist, d, look: dict) -> None:
    """A palm-leaf basket (couffin) hanging from the hand by its two handles, a loaf poking out of it."""
    h = sk["h"] / 1.7
    hand = wrist + d * sk["wrist_r"] * 2.2
    rim = hand[2] - 0.15 * h
    c = np.array([hand[0], hand[1], rim])
    straw = look.get("basket", _CARRY["basket"])
    rings = [_hring(c - np.array([0.0, 0.0, 0.22 * h]), 0.065 * h, 0.12 * h), _hring(c, 0.085 * h, 0.16 * h)]
    _loft(mb, rings, straw, 6, inner=True, caps=(True, False))
    floor = c - np.array([0.0, 0.0, 0.21 * h])                    # the inside of the bottom, seen from above
    t = np.arange(6) * math.pi / 3
    ring = floor + np.stack([0.06 * h * np.cos(t), 0.11 * h * np.sin(t), 0.0 * t], axis=1)
    _add_flat(mb, [[floor, ring[k], ring[(k + 1) % 6]] for k in range(6)], (0.0, 0.0, 1.0), straw)
    for sy in (-1.0, 1.0):
        _bar(mb, c + np.array([0.0, sy * 0.11 * h, 0.0]), hand - np.array([0.0, 0.0, 0.01]), 0.007, straw)
    _blob(mb, c + np.array([0.02 * h, 0.05 * h, 0.03 * h]), (0.15, 0.6, 1.0), (1.0, 0.0, 0.0),
          (0.13 * h, 0.03 * h, 0.03 * h), look.get("bread", _CARRY["bread"]))


def _bag(mb: MeshBuilder, sk: dict, wrist, d, look: dict) -> None:
    """A plastic shopping bag, gathered into the hand at its handles."""
    h = sk["h"] / 1.7
    hand = wrist + d * sk["wrist_r"] * 2.2
    mat = look.get("bag", _CARRY["bag"])
    top = hand[2] - 0.04 * h
    x, y = hand[0], hand[1]
    rings = [_hring((x, y, top - 0.36 * h), 0.055 * h, 0.13 * h), _hring((x, y, top - 0.2 * h), 0.065 * h, 0.15 * h),
             _hring((x, y, top - 0.08 * h), 0.04 * h, 0.08 * h), _hring((x, y, top), 0.012 * h, 0.02 * h)]
    _loft(mb, rings, mat, 4, caps=(True, False), phase=math.pi / 4)


def _carrying(mb: MeshBuilder, sk: dict, look: dict, arms: dict, clear: float) -> dict:
    """With pose `carry`, replace the right arm by a loaded one and hang its basket or bag."""
    if sk["pose"] != "carry":
        return arms
    item = look.get("carry", "bag")
    arms = dict(arms)
    arms[1.0] = _carry_arm(sk, 1.0, clear, item)
    _, e, w = arms[1.0]
    (_basket if item == "basket" else _bag)(mb, sk, w, _unit(w - e), look)
    return arms


# --- outfits --------------------------------------------------------------------------------------

def _dress_jebba(mb: MeshBuilder, sk: dict, look: dict) -> None:
    """A man in a jebba: the long wool robe to the ankles with wide short sleeves and a trimmed neck
    opening, a white undershirt's sleeves, a red chechia and leather slippers (balgha)."""
    h, z, d = sk["h"], sk["z"], sk["chest_d"]
    robe, skin = look["robe"], look["skin"]
    _head(mb, sk, skin, look["hair"], "short", hide=lambda dirs: dirs[:, 2] > 0.75)
    _neck(mb, sk, skin)
    _chechia(mb, sk, look["cap"])
    loose = 0.012 * h
    rings = _torso_rings(sk, z["waist"], extra=loose)[1:][::-1]          # neckline down to the waist
    hw, hd = sk["hip_w"] + 0.02 * h, d + 0.016 * h + sk["belly"] * 0.5
    if sk["pose"] == "sit":
        _loft(mb, rings + _seat_rings(sk, hw - 0.002 * h, hd - 0.004 * h), robe, 8, caps=(True, True))
        _lap(mb, sk, robe, hw - 0.012 * h, look["hem"] * h + 0.02 * h)
        clear = hw
    else:
        low = _skirt_rings(sk, [(sk["hip_z"], hw, hd), (sk["hip_z"] - 0.2 * h, hw + 0.01 * h, hd + 0.004 * h)],
                           look["hem"] * h)
        _loft(mb, rings + low, robe, 8, inner=True, caps=(True, False))
        clear = max(float(np.linalg.norm(u)) for c, u, v in low if c[2] > 0.25 * h)
    front = [_on(rings, 0.0, z["shoulder"] + 0.02 * h, 0.004), _on(rings, 0.0, z["chest"] - 0.04 * h, 0.004)]
    _strip(mb, front, 0.022 * h, look["trim"], sk["R"] @ np.array([0.0, 1.0, 0.0]))
    arms = _carrying(mb, sk, look, _arms(sk, sk["pose"]), clear)
    for side, joints in arms.items():
        _sleeve(mb, sk, joints, side, robe, look["under"], skin)
    _feet(mb, sk, look["shoes"])


def _sleeve(mb: MeshBuilder, sk: dict, joints: tuple, side: float, robe: str, under: str, skin: str) -> None:
    """A jebba's wide sleeve from the shoulder to past the elbow, its cuff doubled; the undershirt below."""
    s, e, w = joints
    cuff = e + (w - e) * 0.3
    _chain(mb, [s, e, cuff], [sk["arm_r"] * 1.25, sk["elbow_r"] * 2.2, sk["elbow_r"] * 2.9], [robe, robe],
           _side_axis(side), inner=True)
    _chain(mb, [e, w], [sk["elbow_r"], sk["wrist_r"]], [under], _side_axis(side))
    _hand(mb, sk, e, w, side, skin)


def _chechia(mb: MeshBuilder, sk: dict, mat: str) -> None:
    """The red felt chechia: a short, slightly tapered cap with a flat top, sitting on the crown."""
    rx, ry, rz = sk["head_r"]
    c = sk["head_c"]
    base = c + sk["R"] @ np.array([0.0, -0.05 * ry, rz * 0.5])
    top = c + sk["R"] @ np.array([0.0, -0.08 * ry, rz * 1.32])
    rings = [(cc, sk["R"] @ np.array([rx * f, 0.0, 0.0]), sk["R"] @ np.array([0.0, ry * f, 0.0]))
             for cc, f in ((base, 0.95), (top, 0.86))]
    _loft(mb, rings, mat, 7, caps=(False, True))


def _dress_shirt(mb: MeshBuilder, sk: dict, look: dict) -> None:
    """A man in a shirt and trousers."""
    skin = look["skin"]
    _head(mb, sk, skin, look["hair"], "short")
    _neck(mb, sk, skin)
    _torso(mb, sk, look["shirt"], sk["z"]["waist"] - 0.035 * sk["h"])
    _pelvis(mb, sk, look["trousers"])
    _legs(mb, sk, (look["trousers"], look["trousers"]))
    cut = 0.55 if look["sleeves"] == "short" else 2.0
    arms = _carrying(mb, sk, look, _arms(sk, sk["pose"]), sk["hip_w"] + 0.004 * sk["h"])
    for side, joints in arms.items():
        _arm(mb, sk, joints, side, (look["shirt"], skin, skin), cut=cut, deltoid=sk["pose"] != "sit")
    _feet(mb, sk, look["shoes"])


def _dress_safsari(mb: MeshBuilder, sk: dict, look: dict) -> None:
    """A woman in a safsari: the white wrap over the head and the whole body to the ankles, held closed
    under the chin by one hand, its front edge crossing down the body; the other arm stays inside unless
    it carries a basket."""
    h, z, sw, d = sk["h"], sk["z"], sk["sw"], sk["chest_d"]
    wrap, skin = look["wrap"], look["skin"]
    _head(mb, sk, skin, hide=_under_hood)
    foot_ring = _hood(mb, sk, wrap)
    upper = [foot_ring,
             _hring((0.0, -0.004 * h, z["shoulder"] - 0.022 * h), sw + 0.004 * h, d + 0.016 * h, sk),
             _hring((0.0, 0.0, z["chest"]), sw + 0.02 * h, d + 0.022 * h, sk),
             _hring((0.0, 0.0, z["waist"]), sw + 0.016 * h, d + 0.022 * h, sk)]
    if sk["pose"] == "sit":
        upper.append(_hring((0.0, -0.01 * h, sk["hip_z"]), sk["hip_w"] + 0.03 * h, d + 0.026 * h))
        upper.append(_hring((0.0, -0.012 * h, sk["seat"]), sk["hip_w"] + 0.028 * h, d + 0.024 * h))
        _loft(mb, upper, wrap, 8, caps=(False, True))
        _lap(mb, sk, wrap, sk["hip_w"] + 0.02 * h, look["hem"] * h + 0.02 * h)
        rings, edge_low = upper[1:], z["waist"]
        clear = sk["hip_w"] + 0.03 * h
    else:
        hw = max(sk["hip_w"] + 0.035 * h, sw + 0.016 * h)
        lower = [_fit(sk, sk["hip_z"], hw, d + 0.028 * h), _fit(sk, sk["hip_z"] - 0.22 * h, hw + 0.006 * h, d + 0.03 * h),
                 _fit(sk, look["hem"] * h, hw + 0.012 * h, d + 0.03 * h)]
        _loft(mb, upper + lower, wrap, 8, inner=True)
        rings, edge_low = upper[1:] + lower, look["hem"] * h + 0.04 * h
        clear = max(float(np.linalg.norm(u)) for c, u, v in lower[:2])
    chin = foot_ring[0] + foot_ring[2] + sk["R"] @ np.array([0.012 * h, 0.012 * h, -0.004 * h])
    _blob(mb, chin, sk["R"] @ np.array([1.0, 0.0, 0.0]), sk["R"] @ np.array([0.0, 0.0, 1.0]),
          (sk["wrist_r"] * 2.4, sk["wrist_r"] * 1.8, sk["wrist_r"] * 1.3), skin)
    edge = [chin + sk["R"] @ np.array([-0.01 * h, 0.0, -0.02 * h])]
    for x, zz in ((-0.035 * h, z["chest"]), (-0.07 * h, z["waist"]), (-0.085 * h, edge_low)):
        if zz < edge[-1][2]:
            edge.append(_on(rings, x, zz, 0.01))
    _strip(mb, edge, 0.03 * h, wrap)
    if sk["pose"] == "carry":
        s, e, w = _carry_arm(sk, 1.0, clear, look.get("carry", "basket"))
        _chain(mb, [s, e, w], [sk["arm_r"] * 1.2, sk["elbow_r"] * 1.25, sk["wrist_r"] * 1.3], [wrap, wrap],
               _side_axis(1.0))
        _hand(mb, sk, e, w, 1.0, skin)
        (_basket if look.get("carry", "basket") == "basket" else _bag)(mb, sk, w, _unit(w - e), look)
    _feet(mb, sk, look["shoes"])


def _dress_dress(mb: MeshBuilder, sk: dict, look: dict) -> None:
    """A woman in a modern dress, with long hair gathered at the nape, or with a headscarf (`scarf`)
    and longer sleeves and hem."""
    h, z, d = sk["h"], sk["z"], sk["chest_d"]
    dress, skin = look["dress"], look["skin"]
    scarf = look.get("scarf")
    hem = look["hem"] * h
    if scarf:
        _head(mb, sk, skin, hide=_under_hood)
        foot_ring = _hood(mb, sk, scarf)
        cape = [foot_ring, _hring((0.0, -0.006 * h, z["shoulder"] + 0.006 * h), sk["neck_r"] * 2.6, sk["neck_r"] * 2.6, sk),
                _hring((0.0, -0.004 * h, z["shoulder"] - 0.05 * h), sk["sw"] + 0.022 * h, d + 0.016 * h, sk)]
        _loft(mb, cape, scarf, 8, inner=True)
    else:
        _head(mb, sk, skin, look["hair"], "long")
        _neck(mb, sk, skin)
    hw = sk["hip_w"] + 0.012 * h
    if sk["pose"] == "sit":
        rings = _torso_rings(sk, z["waist"], top=not scarf, bust=1.06)[1:][::-1]
        _loft(mb, rings + _seat_rings(sk, hw, d + 0.01 * h), dress, 8, caps=(not scarf, True))
        _lap(mb, sk, dress, hw - 0.006 * h, max(hem, 0.1 * h))
        clear = hw
    else:
        _torso(mb, sk, dress, z["waist"] - 0.03 * h, top=not scarf, bust=1.06)
        levels = [(z["waist"] - 0.005 * h, sk["waist_w"] + 0.004 * h, d * 0.95), (sk["hip_z"], hw, d + 0.01 * h)]
        if hem < sk["hip_z"] - 0.25 * h:
            levels.append((sk["hip_z"] - 0.2 * h, hw + 0.008 * h, d + 0.014 * h))
        low = _skirt(mb, sk, dress, levels, hem)
        clear = max(float(np.linalg.norm(u)) for c, u, v in low)
    knee = min(leg[1][2] for leg in sk["legs"].values()) + sk["knee_r"]
    if max(hem, 0.1 * h if sk["pose"] == "sit" else 0.0) > 0.12 * h:          # shins show below the hem
        _legs(mb, sk, (look["legs"], look["legs"]), from_knee=hem < knee or sk["pose"] == "sit")   # thighs too above the knee
    cut = {"long": 2.0, "three_quarter": 1.6, "short": 0.5}[look["sleeves"]]
    arms = _carrying(mb, sk, look, _arms(sk, sk["pose"]), clear)
    for side, joints in arms.items():
        _arm(mb, sk, joints, side, (dress, skin, skin), cut=cut, deltoid=not scarf and sk["pose"] != "sit")
    _feet(mb, sk, look["shoes"])


def _dress_boy(mb: MeshBuilder, sk: dict, look: dict) -> None:
    """A boy in a t-shirt and shorts."""
    skin = look["skin"]
    _head(mb, sk, skin, look["hair"], "short")
    _neck(mb, sk, skin)
    _torso(mb, sk, look["shirt"], sk["z"]["waist"] - 0.035 * sk["h"])
    _pelvis(mb, sk, look["shorts"])
    _legs(mb, sk, (look["shorts"], skin), short=0.7)
    for side, joints in _arms(sk, sk["pose"]).items():
        _arm(mb, sk, joints, side, (look["shirt"], skin, skin), cut=0.5, deltoid=False)
    _feet(mb, sk, look["shoes"])


def _dress_girl(mb: MeshBuilder, sk: dict, look: dict) -> None:
    """A girl in a knee-length dress, her hair gathered at the nape."""
    look = {**look, "legs": look["skin"], "sleeves": "short"}
    _dress_dress(mb, sk, look)


_DRESS = {"jebba": _dress_jebba, "shirt": _dress_shirt, "safsari": _dress_safsari, "dress": _dress_dress,
          "boy": _dress_boy, "girl": _dress_girl}
