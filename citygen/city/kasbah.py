"""The kasbah (prompt 30): the walled citadel on the old town's highest edge, as in Tunis or Sousse.

`place` runs after the old town's outline, gates and great mosque and before the alleys: it slides a
rough rectangle along the city wall, highest stretch first, until one keeps clear of the mosque, the
gates and the straight way from each gate to the mosque. The rectangle is cut by the old town's outline,
so its outer side runs on the city wall line and replaces that stretch of the rampart. The alleys, souks,
impasses and lots then avoid `Kasbah.cut`; one souk leads from its gate to the great mosque.

`buildings` draws it: 2.5 m walls taller than the ramparts with a breastwork and merlons, square towers at
the corners and every 40-60 m, a gate tower toward the old town with a horseshoe arch on both faces, a
governor's palace round a courtyard, a small mosque with a square minaret (`medina.mosque_complex`) and the
paved parade ground. They are appended at the very end of the plan's buildings: no household lives in
them, so no household moves. Numbers live in the style's `[kasbah]` table.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import shapely
from shapely.geometry import LinearRing, LineString, Point, Polygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

from ..mesh.builder import rectangle
from ..names import NameMaker
from .geo import frame, largest, polygons, tangent_angle
from .model import Building, Landmark

GROUND = "kasbah_ground"    # paving draped on the terrain, never extruded (mesh/tile.PAVED_KINDS)
INSET = 0.3   # meters a tower reaches inside the wall's inner face, so it cuts the wall through


@dataclass
class Kasbah:
    outline: Polygon        # the wall's center line; its outer side runs on the old town's edge
    angle: float            # direction of the side along the city wall (radians)
    inward: np.ndarray      # unit vector from the city wall into the old town (the gate faces it)
    origin: np.ndarray      # the point of the city wall the kasbah is centered on
    gate: np.ndarray        # middle of the gate on the wall line
    face: np.ndarray        # middle of the gate tower's outer face
    front: np.ndarray       # a few meters in front of the gate: the souk from the alleys starts here
    cut: object             # the outline plus `clearance`: no lot, alley or souk there
    keep_out: object        # what the city rampart leaves out: the outer wall and the towers
    towers: list            # square tower footprints
    gate_tower: Polygon
    buildings: list = field(default_factory=list)
    landmark: Landmark | None = None


def place(ctx, medina, site, entrance, gate_pts) -> Kasbah | None:
    """The kasbah of a walled medina with `kasbah = true`, or None (villages, towns, no room)."""
    cfg = ctx.style.get("kasbah")
    if not cfg or not ctx.kc.get("kasbah") or not ctx.kc.get("walls") or medina is None:
        return None
    share, lo, hi = (float(v) for v in cfg["side"])
    side = float(np.clip(share * frame(medina)[3], lo, hi))
    depth = float(cfg["depth"]) * side
    ring = medina.exterior
    n = max(int(ring.length // float(cfg["step"])), 8)
    pts = shapely.get_coordinates(shapely.line_interpolate_point(ring, np.arange(n) * ring.length / n))
    h = np.asarray(ctx.world.terrain.height(pts[:, 0], pts[:, 1]), dtype=np.float64)
    reach = max(1, int(round(side / 2 / (ring.length / n))))       # the wall stretch the kasbah takes
    score = np.mean([np.roll(h, k) for k in range(-reach, reach + 1)], axis=0)
    for i in np.argsort(-score, kind="stable")[:int(cfg["tries"])]:
        k = _candidate(ctx, cfg, medina, Point(pts[i]), side, depth, site, entrance, gate_pts)
        if k is not None:
            return k
    return None


def _candidate(ctx, cfg, medina, p: Point, side, depth, site, entrance, gate_pts) -> Kasbah | None:
    from .medina import _outward                  # medina imports this module
    theta = tangent_angle(medina.exterior, p)
    u = np.array([math.cos(theta), math.sin(theta)])
    inward = -_outward(medina, p, theta)
    o = np.array([p.x, p.y])
    rect = rectangle(*o, side, 2 * depth, theta)   # reaching `depth` beyond the edge too: the cut follows the wall
    k = largest(rect.intersection(medina))
    lo, hi = (float(v) for v in cfg["area"])
    if k is None or not (lo * side * depth <= k.area <= hi * side * depth) or k.area > float(cfg["max_share"]) * medina.area:
        return None
    if k.exterior.intersection(medina.exterior.buffer(0.5)).length < float(cfg["on_wall"]) * side:
        return None                                          # it must lean on the city wall
    k = orient(k.simplify(0.05), sign=1.0)
    tk, clear = float(cfg["wall_thickness"]), float(cfg["clearance"])
    gl, gd, _gh = (float(v) for v in cfg["gate"])
    gate = o + inward * depth
    face = gate + inward * (gd - tk / 2)
    front = face + inward * (clear + 6.0)
    edge = LineString([gate - u * side / 2, gate + u * side / 2])
    if not medina.buffer(-clear).contains(edge) or not medina.buffer(-(clear + 4.0)).contains(Point(front)):
        return None
    gate_tower = rectangle(*(gate + inward * (gd / 2 - tk / 2)), gl, gd, theta)
    cut = unary_union([k.buffer(clear, join_style="mitre"), gate_tower.buffer(2.0, join_style="mitre")])
    if site is not None and cut.distance(site) < float(cfg["mosque_clear"]):
        return None
    for g in gate_pts:
        if cut.distance(g) < float(cfg["gate_clear"]):
            return None
        if cut.distance(LineString([(g.x, g.y), (entrance.x, entrance.y)])) < float(cfg["souk_clear"]):
            return None
    towers = _towers(k, gate, cfg)
    if any(t.intersects(gate_tower) for t in towers):
        return None
    tw = float(ctx.style["district"]["medina"]["wall_thickness"])
    keep_out = unary_union([k.buffer(max(tw, tk) / 2 + 0.05, join_style="mitre"), gate_tower] + towers)
    return Kasbah(k, theta, inward, o, gate, face, front, cut, keep_out, towers, gate_tower)


def _stations(ring: np.ndarray, gate: np.ndarray, cfg) -> list:
    """(distance along the closed ring, kind, vertex) of the corners, the gate and the towers between them
    (vertex: the corner's index in the ring, else -1)."""
    a, b = ring[:-1], ring[1:]
    seg = np.hypot(*(b - a).T)
    start = np.concatenate([[0.0], np.cumsum(seg)])
    total = float(start[-1])
    d_in, d_out = (a - np.roll(a, 1, axis=0)), (b - a)
    turn = np.degrees(np.abs(np.arctan2(d_in[:, 0] * d_out[:, 1] - d_in[:, 1] * d_out[:, 0],
                                        (d_in * d_out).sum(axis=1))))
    stops = [(float(start[i]), "corner", int(i)) for i in np.nonzero(turn > float(cfg["corner_turn"]))[0]]
    stops.append((float(LineString(ring).project(Point(gate))), "gate", -1))
    stops.sort()
    lo, hi = (float(v) for v in cfg["tower_gap"])
    out = list(stops)
    for (s0, _, _), (s1, _, _) in zip(stops, stops[1:] + [(stops[0][0] + total, "", -1)]):
        run = s1 - s0
        options = range(0, int(run // lo) + 2)
        m = min(options, key=lambda m: (max(lo - run / (m + 1), run / (m + 1) - hi, 0.0), m))
        out += [((s0 + run * (j + 1) / (m + 1)) % total, "tower", -1) for j in range(m)]
    return sorted(out)


def _towers(k: Polygon, gate: np.ndarray, cfg) -> list:
    """Square towers standing out of the wall (a little inside its inner face too): one at each corner of
    the outline and every 40-60 m between (the gate tower counts as one)."""
    ring = np.asarray(k.exterior.coords)[:, :2]
    line = LineString(ring)
    ts, tk = float(cfg["tower_side"]), float(cfg["wall_thickness"])
    pts = ring[:-1]
    out = []
    for s, kind, i in _stations(ring, gate, cfg):
        if kind == "gate":
            continue
        if kind == "corner":
            p = pts[i]
            d1, d2 = p - pts[i - 1], pts[(i + 1) % len(pts)] - p
            longer = d1 if np.hypot(*d1) > np.hypot(*d2) else d2
            d1, d2 = d1 / np.hypot(*d1), d2 / np.hypot(*d2)
            n = np.array([d1[1], -d1[0]]) + np.array([d2[1], -d2[0]])    # outward: right of a CCW ring
            c = p + n / max(np.hypot(*n), 1e-9) * math.sqrt(2.0) * (ts / 2 - tk / 2 - INSET)
            d = longer
        else:
            p = np.asarray(line.interpolate(s).coords[0])
            d = np.asarray(line.interpolate((s + 1.0) % line.length).coords[0]) - p
            d = d / np.hypot(*d)
            c = p + np.array([d[1], -d[0]]) * (ts / 2 - tk / 2 - INSET)
        out.append(rectangle(*c, ts, ts, math.atan2(d[1], d[0])))
    return out


# --- the buildings --------------------------------------------------------------------------------

def buildings(ctx, kas: Kasbah, district: int, qibla: float) -> list:
    """Walls, towers, the gate tower, the palace, the mosque and the paved ground, in that order."""
    from .medina import mosque_complex          # medina imports this module
    cfg = ctx.style["kasbah"]
    rng = ctx.rng("kasbah", "layout")
    tk = float(cfg["wall_thickness"])
    fort = _fort(kas, cfg, district)
    inner = kas.outline.buffer(-tk / 2, join_style="mitre")
    free = inner.difference(unary_union(kas.towers + [kas.gate_tower]).buffer(float(cfg["gap"]), join_style="mitre"))
    free = free.buffer(-float(cfg["gap"]), join_style="mitre")
    shapely.prepare(free)
    palace = _palace(kas, cfg, free, rng, district)
    taken = [palace.footprint] if palace is not None else []
    mosque = _mosque(kas, cfg, free, taken, qibla, district, mosque_complex)
    built = ([palace] if palace is not None else []) + mosque
    fps = [b.footprint for b in fort + built]
    ground = [Building(orient(p, sign=1.0), GROUND, district, float(cfg["paving_lift"]), str(cfg["paving"]),
                       str(cfg["paving"]))                 # the parade ground and the courtyards
              for p in polygons(inner.difference(unary_union(fps))) if p.area > 10.0]
    return fort + built + ground


def _battlement(cfg, chains: list) -> dict:
    b = cfg["battlement"]
    return {"chains": chains, "breast": float(b["breast"]), "merlon": [float(v) for v in b["merlon"]],
            "depth": float(b["depth"])}


def _fort(kas: Kasbah, cfg, district: int) -> list:
    """The wall pieces between the towers, the towers and the gate tower with its arches."""
    tk = float(cfg["wall_thickness"])
    ring = LinearRing(kas.outline.exterior.coords)
    band = ring.buffer(tk / 2, cap_style="flat", join_style="mitre")
    cuts = []                               # across the wall at each tower: one piece per stretch between them
    for t in kas.towers + [kas.gate_tower]:
        s = ring.project(t.centroid)
        a, b = ring.interpolate(s - 0.5), ring.interpolate(s + 0.5)
        cuts.append(rectangle(*ring.interpolate(s).coords[0], 0.02, 3 * tk, math.atan2(b.y - a.y, b.x - a.x)))
    walls = band.difference(unary_union(kas.towers + [kas.gate_tower] + cuts))
    out = []
    for p in polygons(walls):
        if p.area <= 1.5:                   # a sliver beside a tower
            continue
        p = orient(p, sign=1.0)
        out.append(Building(p, "kasbah_wall", district, float(cfg["wall_height"]), "stone_kasbah",
                            "stone_kasbah", battlement=_battlement(cfg, _outer_chains(p, kas.outline, tk))))
    for t in kas.towers:
        t = orient(t, sign=1.0)
        out.append(Building(t, "kasbah_tower", district, float(cfg["tower_height"]), "stone_kasbah",
                            "stone_kasbah", battlement=_battlement(cfg, [list(t.exterior.coords)])))
    g = orient(kas.gate_tower, sign=1.0)
    aw, ah, af = (float(v) for v in cfg["gate_arch"])
    yaw = math.atan2(kas.inward[1], kas.inward[0])
    back = kas.gate - kas.inward * (tk / 2)
    arches = [(float(kas.face[0]), float(kas.face[1]), yaw, aw, ah, 0.0, af, "wood"),
              (float(back[0]), float(back[1]), yaw + math.pi, aw, ah, 0.0, af, "wood")]
    out.append(Building(g, "kasbah_gate", district, float(cfg["gate"][2]), "stone_kasbah", "stone_kasbah",
                        battlement=_battlement(cfg, [list(g.exterior.coords)]), arches=arches))
    return out


def _outer_chains(p: Polygon, outline: Polygon, tk: float) -> list:
    """The runs of a wall piece's outline on the wall's outer face (the battlement side)."""
    ring = np.asarray(p.exterior.coords)[:, :2]
    mids = shapely.points((ring[:-1] + ring[1:]) / 2)
    outer = shapely.distance(outline, mids) > tk / 4
    chains, cur = [], []
    for i, on in enumerate(outer):
        if on:
            cur = cur or [tuple(ring[i])]
            cur.append(tuple(ring[i + 1]))
        elif cur:
            chains.append(cur)
            cur = []
    if cur:
        if chains and outer[0] and chains[0][0] == cur[-1]:
            chains[0] = cur[:-1] + chains[0]               # the run goes on across the ring's start
        else:
            chains.append(cur)
    return [[(float(x), float(y)) for x, y in c] for c in chains]


def _palace(kas: Kasbah, cfg, free, rng, district: int) -> Building | None:
    """The governor's palace round its courtyard, in a back corner (by the outer wall, away from the gate)."""
    pc = cfg["palace"]
    depth = float(np.hypot(*(kas.gate - kas.origin)))
    width = kas.outline.area / max(depth, 1.0)                          # along the city wall
    length = float(np.clip(pc["length"][0] * width, pc["length"][1], pc["length"][2]))
    deep = float(np.clip(pc["depth"][0] * depth, pc["depth"][1], pc["depth"][2]))
    u = np.array([math.cos(kas.angle), math.sin(kas.angle)])
    signs = (1.0, -1.0) if rng.random() < 0.5 else (-1.0, 1.0)
    for scale in (1.0, 0.85, 0.7):
        L, D = length * scale, deep * scale
        for sign in signs:
            for t in np.arange(0.0, depth, 1.0):
                for s in np.arange(width / 2 - L / 2, -1e-9, -2.0):
                    c = kas.origin + u * sign * s + kas.inward * (t + D / 2)
                    fp = rectangle(*c, L, D, kas.angle)
                    if free.contains(fp):
                        return _palace_building(kas, cfg, fp, c, L, D, district)
    return None


def _palace_building(kas: Kasbah, cfg, fp: Polygon, c, length: float, deep: float, district: int) -> Building:
    pc = cfg["palace"]
    wing = float(pc["wing"])
    if length - 2 * wing > 6.0 and deep - 2 * wing > 6.0:
        fp = fp.difference(rectangle(*c, length - 2 * wing, deep - 2 * wing, kas.angle))
    fp = orient(fp, sign=1.0)
    floors, fh = int(pc["floors"]), float(pc["floor_height"])
    return Building(fp, "kasbah_palace", district, floors * fh, str(pc["wall"]), str(pc["roof"]), floors,
                    arches=_palace_openings(kas, cfg, fp, floors, fh))


def _palace_openings(kas: Kasbah, cfg, fp: Polygon, floors: int, fh: float) -> list:
    """Arched windows on the upper floors of the outer walls and the door on the wall facing the gate."""
    ww, wh, step = (float(v) for v in cfg["palace_windows"])
    dw, dh, df = (float(v) for v in cfg["palace_door"])
    ring = np.asarray(fp.exterior.coords)[:, :2]
    out = []
    best, door, door_yaw = -1.0, None, 0.0
    for a, b in zip(ring[:-1], ring[1:]):
        d = b - a
        length = float(np.hypot(*d))
        if length < step:
            continue
        u = d / length
        yaw = math.atan2(-u[0], u[1])                           # outward: right of a CCW ring
        n = np.array([math.cos(yaw), math.sin(yaw)])
        count = int((length - 2.0) // step)
        for j in range(count):
            p = a + u * (length / 2 + (j - (count - 1) / 2) * step)
            for f in range(1, floors):
                out.append((float(p[0]), float(p[1]), yaw, ww, wh, f * fh + 0.9, 0.0, "glass_dark"))
        facing = float(np.dot(n, kas.inward))
        if facing > best:
            best, door = facing, (a + b) / 2
            door_yaw = yaw
    if door is not None:
        out.append((float(door[0]), float(door[1]), door_yaw, dw, dh, 0.0, df, "wood"))
    return out


def _mosque(kas: Kasbah, cfg, free, taken: list, qibla: float, district: int, mosque_complex) -> list:
    """A small mosque facing the qibla (hall, arcaded court, square minaret), as far back as it fits."""
    share, lo, hi = (float(v) for v in cfg["mosque"])
    depth = float(np.hypot(*(kas.gate - kas.origin)))
    width = kas.outline.area / max(depth, 1.0)
    hw = float(np.clip(share * width, lo, hi))
    hd, cd = (float(v) * hw for v in cfg["mosque_depth"])
    ms, mh, mmin = (float(v) for v in cfg["minaret"])
    room = free.difference(unary_union(taken).buffer(float(cfg["gap"]), join_style="mitre")) if taken else free
    shapely.prepare(room)
    u = np.array([math.cos(kas.angle), math.sin(kas.angle)])
    for scale in (1.0, 0.85):
        w, d1, d2 = hw * scale, hd * scale, cd * scale
        for t in np.arange(0.0, depth, 1.0):
            for s in np.arange(width / 2, -width / 2, -2.0):
                c = kas.origin + u * s + kas.inward * t
                if not room.contains(rectangle(*c, d1 + d2, w, qibla)):
                    continue
                parts, _site, _door, _mark = mosque_complex(float(c[0]), float(c[1]), qibla, w, d1, d2,
                                                             (ms * w, max(mh * w, mmin)), district, "")
                if all(room.contains(b.footprint) for b in parts):
                    return parts
    return []


def landmark(ctx, kas: Kasbah) -> Landmark:
    """'Kasbah of <city>' or a Dar el Bey-like name, on its own stream; it stands at the gate (where the
    old town meets it and a sabil may stand)."""
    namer = NameMaker(ctx.style, ctx.rng("kasbah", "name"))
    return Landmark("kasbah", namer.district("kasbah", s=ctx.s.name), float(kas.face[0]), float(kas.face[1]))
