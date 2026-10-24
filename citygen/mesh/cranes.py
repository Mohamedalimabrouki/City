"""Harbor cranes and cargo of the commercial quay (prompt 35).

Generator axes: x along the quay (the crane rails), y toward the sea, z up; the origin lies on the quay top
at the middle of the piece. Pieces fit inside their plan envelope `[port.props] size` (x by y).

- `crane_0`, `crane_1`: lattice-boom portal cranes like the old level-luffing cranes of Sfax and La Goulette:
  four plate legs on rail bogies straddling the two rails, a portal frame, a slewing machinery house with
  its operator's cab and counterweight, an A-frame and a tapering lattice boom over the water with its
  luffing ropes, hoist rope and hook block. `crane_1` is slewed and luffed differently; a harbor uses one
  of the two (cranes come in batches). The boom reaches over the water, outside the envelope (only the
  portal stands on the quay).
- `crane_rails`: one length of the two crane rails, set into the quay.
- `cargo_crates`: wooden crates stacked on pallets, the stack drawn on the piece's own stream.
- `cargo_containers_0`, `cargo_containers_1`: three 20-foot containers, two side by side and one on top,
  ribbed sides, three different colors on the piece's own stream. Both share every part dict (only the
  colors are renamed), so a tile writes the geometry once.
"""
from __future__ import annotations

import math

import numpy as np

from ..rng import stream
from .boats import boxes, prisms, surface
from .builder import MeshBuilder
from .props import _faces, _orient

PAINT = "crane_paint"
CONTAINERS = ("container_red", "container_blue", "container_green", "container_grey")


def crane_pieces(seed: int, cfg: dict | None) -> dict:
    """{name: (MeshBuilder or glTF parts, category, anchor)} of the cranes, rails and cargo in `[port.props] size`."""
    if not cfg or "size" not in cfg:
        return {}
    size = cfg["size"]
    out = {}
    if "crane" in size:
        w, g = (float(v) for v in size["crane"])
        for k, (slew, luff) in enumerate(((0.0, 50.0), (24.0, 62.0))):
            out[f"crane_{k}"] = (crane(w - 1.0, g - 1.0, slew, luff, cfg.get("crane", {})), "crane", "ground")
        out["crane_rails"] = (rails(float(size["crane_rails"][0]), g - 1.0), "rail", "ground")
    if "cargo_crates" in size:
        out["cargo_crates"] = (crates(stream(seed, "piece", "cargo_crates"), *(float(v) for v in size["cargo_crates"])),
                               "cargo", "ground")
    if "cargo_containers" in size:
        slots = containers()
        for k in range(2):
            name = f"cargo_containers_{k}"
            colors = stream(seed, "piece", name).permutation(len(CONTAINERS))[:len(slots) - 1]
            parts = {(CONTAINERS[int(colors[i])] if m.startswith("SLOT") else m): part
                     for i, (m, part) in enumerate(slots.items())}
            out[name] = (parts, "cargo", "ground")
    return out


# --- the crane --------------------------------------------------------------------------------------

def crane(wheelbase: float, gauge: float, slew: float, luff: float, cfg: dict):
    """A portal crane: legs at (+-wheelbase/2, +-gauge/2), boom slewed `slew` degrees from +y, luffed
    `luff` degrees above level."""
    mb = MeshBuilder()
    portal = float(cfg.get("portal", 7.5))
    boom = float(cfg.get("boom", 26.0))
    hx, hy = wheelbase / 2, gauge / 2
    for sy in (1.0, -1.0):                                  # bogie beams on the rails, legs, portal girders
        boxes(mb, "steel_rust", (-hx - 0.45, hx + 0.45, sy * hy - 0.32, sy * hy + 0.32, 0.0, 0.55))
    for sx in (1.0, -1.0):
        for sy in (1.0, -1.0):
            _leg(mb, sx * hx, sy * hy, 0.55, portal - 0.9, 0.34, 0.46)
        boxes(mb, PAINT, (sx * hx - 0.45, sx * hx + 0.45, -hy - 0.45, hy + 0.45, portal - 0.9, portal))
    for sy in (1.0, -1.0):
        boxes(mb, PAINT, (-hx + 0.45, hx - 0.45, sy * hy - 0.4, sy * hy + 0.4, portal - 0.8, portal - 0.05))
    prisms(mb, PAINT, [(-hx, -hy, 1.2), (hx, -hy, 1.2)], [(hx, -hy, portal - 0.9), (-hx, -hy, portal - 0.9)], 0.12, 4)
    upper = MeshBuilder()
    _upper(upper, portal, boom, luff)
    a = math.radians(slew)
    c, s = math.cos(a), math.sin(a)
    rot = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
    for mat, (pos, nrm, uv, tris, _n, _col) in upper._parts.items():
        p = np.concatenate(pos) @ rot.T
        mb.add(mat, p, np.concatenate(nrm) @ rot.T, p[:, :2], np.concatenate(tris))
    return mb


def _leg(mb, x: float, y: float, z0: float, z1: float, r0: float, r1: float) -> None:
    """A tapering square plate leg: four side faces."""
    quads = []
    for (dx0, dy0), (dx1, dy1) in (((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))):
        q = [(x + dx0 * r0, y + dy0 * r0, z0), (x + dx1 * r0, y + dy1 * r0, z0),
             (x + dx1 * r1, y + dy1 * r1, z1), (x + dx0 * r1, y + dy0 * r1, z1)]
        quads += _orient([q], ((dx0 + dx1) / 2, (dy0 + dy1) / 2, 0.0))
    _faces(mb, quads, PAINT)


def _upper(mb, portal: float, boom: float, luff: float) -> None:
    """Slewing part, boom toward +y: turntable, house, cab, counterweight, A-frame, lattice boom, ropes."""
    z0 = portal
    prisms(mb, "steel_rust", [(0.0, 0.0, z0)], [(0.0, 0.0, z0 + 0.5)], 2.2, 8)   # the slewing ring
    zh = z0 + 0.5
    boxes(mb, PAINT, (-2.0, 2.0, -3.0, 1.4, zh, zh + 2.9))                     # machinery house
    boxes(mb, "steel_rust", (-1.8, 1.8, -3.9, -3.0, zh + 0.3, zh + 2.2))      # counterweight
    boxes(mb, PAINT, (-2.0, -0.8, 1.4, 2.8, zh + 0.6, zh + 2.6))                 # operator's cab
    e = 0.01
    glass = _orient([[(-1.9, 2.8 + e, zh + 1.5), (-0.9, 2.8 + e, zh + 1.5), (-0.9, 2.8 + e, zh + 2.45),
                      (-1.9, 2.8 + e, zh + 2.45)]], (0.0, 1.0, 0.0))
    glass += _orient([[(-2.0 - e, 1.5, zh + 1.5), (-2.0 - e, 2.7, zh + 1.5), (-2.0 - e, 2.7, zh + 2.45),
                       (-2.0 - e, 1.5, zh + 2.45)]], (-1.0, 0.0, 0.0))
    _faces(mb, glass, "glass_dark")
    zt = zh + 2.9                                                                # A-frame on the roof
    apex = [(-0.7, -0.6, zt + 6.0), (0.7, -0.6, zt + 6.0)]
    prisms(mb, PAINT, [(-1.6, -2.6, zt), (1.6, -2.6, zt), (-1.6, 1.2, zt), (1.6, 1.2, zt)],
           [apex[0], apex[1], apex[0], apex[1]], 0.13, 4)
    prisms(mb, PAINT, [apex[0]], [apex[1]], 0.13, 4)
    foot = np.array([0.0, 1.7, zh + 1.2])
    a = math.radians(luff)
    tip = foot + boom * np.array([0.0, math.cos(a), math.sin(a)])
    _lattice(mb, foot, tip, 1.7, 0.6, 8)
    hook = tip + [0.0, 0.4, -(tip[2] - portal * 0.9)]                            # luffing ropes, hoist rope, hook
    prisms(mb, "steel_rust", [apex[0], apex[1], tip + [0.0, 0.4, -0.2]],
           [tip + [-0.2, 0.0, 0.3], tip + [0.2, 0.0, 0.3], hook + [0.0, 0.0, 0.6]], 0.03, 3)
    boxes(mb, PAINT, (hook[0] - 0.3, hook[0] + 0.3, hook[1] - 0.2, hook[1] + 0.2, hook[2], hook[2] + 0.7),
          (tip[0] - 0.35, tip[0] + 0.35, tip[1] - 0.15, tip[1] + 0.65, tip[2] - 0.35, tip[2] + 0.45))


def _lattice(mb, foot: np.ndarray, tip: np.ndarray, w0: float, w1: float, bays: int) -> None:
    """A tapering box lattice from foot to tip: four chords and zigzag bracing on each face."""
    d = tip - foot
    d /= np.linalg.norm(d)
    side = np.array([1.0, 0.0, 0.0])
    up = np.cross(side, d)
    s = np.linspace(0.0, 1.0, bays + 1)
    centers = foot + (tip - foot) * s[:, None]
    half = (w0 + (w1 - w0) * s) / 2
    corners = [centers + (sx * side[None] + sy * up[None]) * half[:, None]
               for sx, sy in ((1, 1), (-1, 1), (-1, -1), (1, -1))]
    prisms(mb, PAINT, [c[0] for c in corners], [c[-1] for c in corners], 0.09, 4)
    a, b = [], []
    for k in range(4):
        p, q = corners[k], corners[(k + 1) % 4]
        for i in range(bays):
            a.append(p[i] if i % 2 == 0 else q[i])
            b.append(q[i + 1] if i % 2 == 0 else p[i + 1])
        a.append(p[bays])
        b.append(q[bays])
    prisms(mb, PAINT, a, b, 0.045, 3)


def rails(length: float, gauge: float):
    """Two crane rails along x at y = +-gauge/2, their heads just above the quay."""
    mb = MeshBuilder()
    for y in (gauge / 2, -gauge / 2):
        _faces(mb, _orient([[(-length / 2, y - 0.04, 0.03), (length / 2, y - 0.04, 0.03), (length / 2, y + 0.04, 0.03),
                             (-length / 2, y + 0.04, 0.03)]], (0, 0, 1)), "rail_steel")
        for sy in (1.0, -1.0):
            yy = y + sy * 0.04
            _faces(mb, _orient([[(-length / 2, yy, -0.02), (length / 2, yy, -0.02), (length / 2, yy, 0.03),
                                 (-length / 2, yy, 0.03)]], (0, sy, 0)), "rail_steel")
    return mb


# --- cargo ------------------------------------------------------------------------------------------

def crates(rng, length: float, width: float):
    """Two pallets of wooden crates, stacked one to three high, inside length x width."""
    mb = MeshBuilder()
    spans, dark = [], []
    for k, x in enumerate((-length / 4, length / 4)):
        pl, pw = length / 2 - 0.15, width - 0.2
        dark.append((x - pl / 2, x + pl / 2, -pw / 2, pw / 2, 0.0, 0.14))
        z = 0.14
        for level in range(1 + int(rng.integers(0, 3))):
            h = 0.5 + 0.25 * rng.random()
            shrink = 0.08 * level + 0.05 * rng.random()
            dx = (rng.random() - 0.5) * 0.08
            spans.append((x - pl / 2 + shrink + dx, x + pl / 2 - shrink + dx, -pw / 2 + shrink, pw / 2 - shrink, z, z + h))
            z += h
    boxes(mb, "crate_wood", *spans)
    boxes(mb, "deck_wood", *dark)
    return mb


def containers() -> dict:
    """Three 20-foot containers (6.06 x 2.44 x 2.59 m), two side by side and one on top, ribbed long sides
    and door bars: glTF parts, one placeholder material per container ("SLOT0".."SLOT2") and the bars in iron."""
    mb = MeshBuilder()
    L, W, H = 6.06, 2.44, 2.59
    for k, (x, y, z) in enumerate(((0.0, -W / 2 - 0.05, 0.0), (0.0, W / 2 + 0.05, 0.0), (0.12, -W / 2 - 0.05, H))):
        mat = f"SLOT{k}"
        x0, x1, y0, y1 = x - L / 2, x + L / 2, y - W / 2, y + W / 2
        _faces(mb, _orient([[(x0, y0, z + H), (x1, y0, z + H), (x1, y1, z + H), (x0, y1, z + H)]], (0, 0, 1)), mat)
        for xe, sx in ((x0, -1.0), (x1, 1.0)):
            _faces(mb, _orient([[(xe, y0, z), (xe, y1, z), (xe, y1, z + H), (xe, y0, z + H)]], (sx, 0, 0)), mat)
        xs = np.linspace(x0, x1, 17)
        for ye, sy in ((y0, -1.0), (y1, 1.0)):
            depth = np.where(np.arange(len(xs)) % 2 == 1, 0.04, 0.0) * sy
            grid = np.array([[(xx, ye + dd, zz) for xx, dd in zip(xs, depth)] for zz in (z, z + H)])
            out = np.zeros_like(grid)
            out[:, :, 1] = sy
            surface(mb, mat, grid, out)
        bars = [[(x1 + 0.012, yy - 0.03, z + 0.15), (x1 + 0.012, yy + 0.03, z + 0.15), (x1 + 0.012, yy + 0.03, z + H - 0.15),
                 (x1 + 0.012, yy - 0.03, z + H - 0.15)] for yy in (y + W * 0.12, y - W * 0.12, y + W * 0.38, y - W * 0.38)]
        _faces(mb, _orient(bars, (1, 0, 0)), "iron")
    parts = {m: {**part, "uv": None} for m, part in mb.gltf_parts().items()}
    return {m: parts[m] for m in ("SLOT0", "SLOT1", "SLOT2", "iron")}
