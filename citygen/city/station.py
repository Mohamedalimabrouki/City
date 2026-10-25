"""The railway station and its tracks (prompt 33): a colonial station at the edge of the colonial quarter.

Like the stations of Tunis, Sousse or Sfax, the station is a terminus: a long head building with a pitched
roof, an arched entrance pavilion and a square clock tower faces the town across a paved forecourt; behind
it 2-4 tracks run between platforms under canopies on posts, then close to the line spacing in the throat
and leave the city in a straight corridor (the tracks plus `margin` m each side) to `beyond` m past the
city limit.

`place` runs after every street is drawn and before the blocks are cut. It slides the station along the
arterials that bound a colonial district, standing across the avenue (outside the colonial district, never
in the old town, a park or a cemetery), its forecourt on the avenue's edge and its tracks running straight
away from the quarter. A site must leave the old town, its ring road, the kasbah and the boulevard alone,
cross other main streets at `cross_angle` degrees or more (level crossings), stay on land and reach the
city limit; the cheapest of the corridor length, the main streets crossed and the angle away from the main
country road's entry (or the port) wins, a little jitter on the station's own stream ("station").

The station precinct and the corridor are cut from the districts before `make_blocks` (with the old
town's cut), so no block, lot, building or sidewalk lies on them; local streets running into the precinct
or along the tracks are cut back (`clip_streets`), the ones crossing them keep going over a level crossing.
The station's buildings (`buildings`: the forecourt paving, the head building, the platforms) and its
`Landmark` come last in the plan, after the boulevard's landmarks.

Planner and mesh share the landmarks' local frame (`landmarks.Frame`): s along the forecourt's street edge
(to the right seen from the avenue), d away from the avenue, z up; d = 0 is the avenue's edge.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import shapely
from shapely.geometry import LineString, Point
from shapely.ops import substring, unary_union
from shapely.strtree import STRtree

from ..names import NameMaker
from .geo import lines, polygons
from .landmarks import Frame, rect
from .model import Building, Landmark

MAJOR = ("arterial", "ring", "boulevard", "corniche", "connector")
NEVER_CROSS = ("boulevard", "ring", "souk", "alley")
KINDS = ("station", "station_platforms", "station_forecourt")   # the station's buildings (plan order: forecourt, station, platforms)


@dataclass
class Station:
    facade: dict        # frame (x, y, yaw toward the avenue) and the layout every part is drawn from
    tracks: list        # world LineStrings, one per track, from the buffer stop to `beyond` past the limit
    precinct: object    # forecourt, head building and platforms (a Polygon)
    corridor: object    # the tracks plus `margin` m each side (a Polygon), the precinct not included
    district: int       # district under the head building
    core: object = None # hull of the head building and platforms: the ground there is graded level at facade["level"]
                        # (city/ground.py), blending back over `[station] level_band` m


def layout(cfg: dict, n: int) -> dict:
    """Across the station (s): the track centers and platforms [(s0, s1)], centered on 0. Side platforms at
    both ends, an island platform between each pair of tracks: P T T P (2), P T T P T P (3), P T T P T T P (4)."""
    side, island = (float(v) for v in cfg["platform"][:2])
    edge, spacing = float(cfg["edge"]), float(cfg["spacing"])
    groups = [2] * (n // 2) + [1] * (n % 2)
    s, tracks, platforms = 0.0, [], [(0.0, side)]
    s = side
    for g, count in enumerate(groups):
        first = s + edge
        tracks += [first + i * spacing for i in range(count)]
        s = tracks[-1] + edge
        width = side if g == len(groups) - 1 else island
        platforms.append((s, s + width))
        s += width
    half = s / 2
    return {"tracks": [t - half for t in tracks], "platforms": [(a - half, b - half) for a, b in platforms],
            "width": s}


def dims(cfg: dict, n: int) -> dict:
    """The station's plan in its frame: forecourt, hall, platforms and throat (d ranges), widths (s)."""
    lay = layout(cfg, n)
    min_len, depth = (float(v) for v in cfg["hall"][:2])
    hall = max(min_len, lay["width"] + 2 * float(cfg["hall_margin"]))
    f = float(cfg["forecourt"])
    back = f + depth
    end = back + float(cfg["platform_length"])
    return {"n": n, "tracks": lay["tracks"], "platforms": lay["platforms"], "bundle": lay["width"],
            "hall": round(hall, 2), "forecourt": f, "front": f, "back": back, "stop": back + float(cfg["stop"]),
            "end": end, "throat": end + float(cfg["throat"]), "tower": float(cfg["tower"][0])}


def precinct_sd(p: dict) -> list:
    """The precinct as two rectangles (s, d): the forecourt and the head building, then the platforms."""
    h = p["hall"] / 2 + 1.0
    b = p["bundle"] / 2 + 1.0
    return [rect(-h, h, 0.0, p["back"]), rect(-b, b, p["back"] - 1.0, p["end"])]


def track_sd(cfg: dict, p: dict, i: int, d_end: float) -> np.ndarray:
    """Track i as points (s, d): straight along its platforms, an S-curve to its place on the line over the
    throat, then straight on to d_end."""
    n = p["n"]
    line = (i - (n - 1) / 2) * float(cfg["spacing"])
    s0 = p["tracks"][i]
    t = np.linspace(0.0, 1.0, 13)
    smooth = t * t * (3.0 - 2.0 * t)
    throat = np.column_stack([s0 + (line - s0) * smooth, p["end"] + (p["throat"] - p["end"]) * t])
    return np.vstack([[(s0, p["stop"])], throat, [(line, d_end)]])


# --- choosing the site ------------------------------------------------------------------------------

def place(ctx, districts, streets, medina, cut, land) -> Station | None:
    """The station of a settlement whose kind has `station = true`, or None when no site fits."""
    cfg = ctx.style.get("station")
    if not cfg or not ctx.kc.get("station"):
        return None
    colonial = [d for d in districts if d.kind == "colonial"]
    arterials = [k for k, st in enumerate(streets) if st.kind == "arterial"]
    if not colonial or not arterials:
        return None
    rng = ctx.rng("station")
    lo, hi = (int(v) for v in cfg["tracks"])
    n = int(rng.integers(lo, hi + 1))
    jitter = rng.random(4096)                       # one draw per seed, in seed order
    p = dims(cfg, n)
    env = _Env(ctx, cfg, districts, streets, medina, cut, land)
    best = None
    for k, (o, nrm, street) in enumerate(_seeds(cfg, colonial, streets, arterials)):
        site = env.check(p, o, nrm, street)
        if site is None:
            continue
        cost = site[0] + float(cfg["cost"]["jitter"]) * float(jitter[k % len(jitter)])
        if best is None or cost < best[0]:
            best = (cost, site[1])
    return best[1] if best is not None else None


def _seeds(cfg: dict, colonial: list, streets: list, arterials: list):
    """(origin on the avenue's far edge, normal away from the quarter, street index) every `step` m along
    each arterial on a colonial district's border."""
    step = float(cfg["step"])
    for d in colonial:
        edge = d.polygon.boundary
        for k in arterials:
            st = streets[k]
            if st.line.distance(edge) > 2.0:
                continue
            for t in np.arange(step / 2, st.line.length, step):
                q = st.line.interpolate(float(t))
                if q.distance(edge) > 2.0:
                    continue
                a, b = st.line.interpolate(max(t - 2.0, 0.0)), st.line.interpolate(min(t + 2.0, st.line.length))
                tan = np.array([b.x - a.x, b.y - a.y])
                tan /= max(float(np.hypot(*tan)), 1e-9)
                nrm = np.array([-tan[1], tan[0]])
                if d.polygon.contains(Point(q.x + nrm[0] * 20.0, q.y + nrm[1] * 20.0)):
                    nrm = -nrm
                yield np.array([q.x, q.y]) + nrm * st.width / 2, nrm, k


class _Env:
    """What a site is checked against: the city's streets, districts, old town, land and targets."""

    def __init__(self, ctx, cfg, districts, streets, medina, cut, land):
        self.ctx, self.cfg, self.districts, self.streets = ctx, cfg, districts, streets
        self.boundary = ctx.boundary
        self.inside = ctx.boundary.buffer(-float(cfg["inside"]))
        shapely.prepare(self.inside)
        self.level_inside = self._level_inside(ctx, cfg, districts, land)
        keep_out = [cut] if cut is not None and not cut.is_empty else []
        if medina is not None:
            from .medina import ring_offset
            keep_out.append(medina.buffer(ring_offset(ctx) + 5.0))
        self.keep_out = unary_union(keep_out) if keep_out else None
        if self.keep_out is not None:
            shapely.prepare(self.keep_out)
        self.major = [k for k, st in enumerate(streets) if st.kind in MAJOR or st.kind in NEVER_CROSS]
        self.surfaces = [streets[k].line.buffer(streets[k].width / 2, cap_style="flat") for k in self.major]
        self.tree = STRtree(self.surfaces) if self.surfaces else None
        self.forbidden = set(cfg["no_station_on"])
        self.dtree = STRtree([d.polygon for d in districts])
        self.terrain = ctx.world.terrain
        self.land = land
        self.targets = self._targets(streets, districts)
        self.min_sin = math.sin(math.radians(float(cfg["cross_angle"])))

    @staticmethod
    def _level_inside(ctx, cfg, districts, land):
        """Where the station's level core may lie: past the city limit's edge blend (`[ground] edge_band`) and
        past the port's level band (`[port] level_band`) around the coast of the port districts, where its
        quays' level core may reach (`core_inland` m inland, city/port.py), each plus `[station] clear` m:
        the ground applies both after the station's leveling (city/ground.py)."""
        margin = float(cfg["clear"])
        area = ctx.boundary.buffer(-(float(ctx.world.cfg["ground"]["edge_band"]) + margin))
        ports = [d.polygon for d in districts if d.kind == "port"]
        port = ctx.style.get("port")
        if ports and port and land is not None and not land.is_empty:
            shore = unary_union(ports).intersection(land.boundary.buffer(float(port["core_inland"]) + 1.0))
            area = area.difference(shore.buffer(float(port["level_band"]) + margin))
        shapely.prepare(area)
        return area

    def _targets(self, streets, districts) -> list:
        """[(x, y, weight)]: where the country roads enter the city (connectors start on the limit), the ports."""
        w = self.cfg["targets"]
        out = []
        for st in streets:
            if st.kind == "connector":
                x, y = st.line.coords[0]
                out.append((x, y, float(w["national"] if st.width >= 10.0 else w["regional"])))
        for d in districts:
            if d.kind == "port":
                c = d.polygon.centroid
                out.append((c.x, c.y, float(w["port"])))
        return out

    def check(self, p: dict, o: np.ndarray, nrm: np.ndarray, street: int):
        """(cost, Station) of the station with its frame at o facing -nrm, or None when it does not fit."""
        cfg = self.cfg
        facade = {"x": float(o[0]), "y": float(o[1]), "yaw": math.atan2(-nrm[1], -nrm[0])}
        fr = Frame(facade)
        precinct = unary_union([fr.poly(sd) for sd in precinct_sd(p)])
        if not self.inside.contains(precinct):
            return None
        if self.keep_out is not None and self.keep_out.intersects(precinct):
            return None
        if self.tree is not None and len(self.tree.query(precinct.buffer(-0.5), predicate="intersects")):
            return None
        head = fr.poly(rect(-p["hall"] / 2, p["hall"] / 2, p["front"], p["back"]))
        core = unary_union([head, fr.poly(rect(-p["bundle"] / 2 - 1.0, p["bundle"] / 2 + 1.0, p["back"] - 1.0,
                                                p["end"]))]).convex_hull   # convex: no kink in the blend
        if not self.level_inside.contains(core):
            return None                                   # the edge blend or the port's grading would tilt it
        drop, level = self._drop(fr, p)
        if drop > float(cfg["max_drop"]):
            return None                                   # more cut and fill than a station would take
        under = [int(i) for i in self.dtree.query(precinct, predicate="intersects")]
        if any(self.districts[i].kind in self.forbidden and self.districts[i].polygon.intersection(precinct).area > 1.0
               for i in under):
            return None
        # the line: straight on from the throat to the first exit through the city limit
        start, far = fr.xy(0.0, p["throat"]), fr.xy(0.0, p["throat"] + 4.0 * self.ctx.s.radius)
        hit = LineString([start, far]).intersection(self.boundary.exterior)
        pts = [g for g in getattr(hit, "geoms", [hit]) if g.geom_type == "Point"]
        if not pts:
            return None
        reach = min(Point(start).distance(q) for q in pts)
        d_end = p["throat"] + reach + float(cfg["beyond"])
        ds = np.arange(p["back"], d_end + 1e-9, 20.0)
        probe = fr.xy(np.zeros(len(ds)), ds)
        if np.any(self.terrain.height(probe[:, 0], probe[:, 1]) < float(cfg["dry"])):
            return None                                   # the tracks would run into the sea
        tracks = [LineString(fr.xy(sd[:, 0], sd[:, 1])) for sd in (track_sd(cfg, p, i, d_end) for i in range(p["n"]))]
        half = float(cfg["spacing"]) / 2 + float(cfg["margin"])
        corridor = unary_union([t.buffer(half, cap_style="flat", join_style="mitre") for t in tracks])
        corridor = corridor.buffer(0.01, join_style="mitre").buffer(-0.01, join_style="mitre")
        inner = corridor.intersection(self.boundary)
        if self.keep_out is not None and self.keep_out.intersects(inner):
            return None
        crossings = self._crossings(inner, fr, precinct)
        if crossings is None:
            return None
        cost = (float(cfg["cost"]["length"]) * reach / 1000.0 + float(cfg["cost"]["crossing"]) * crossings
                + float(cfg["cost"]["align"]) * self._misalign(o, nrm) + float(cfg["cost"]["drop"]) * drop)
        district = max(under, key=lambda i: self.districts[i].polygon.intersection(head).area)
        facade.update({"width": p["hall"], "depth": p["back"] - p["front"], "forecourt": p["forecourt"],
                       "tracks": [round(t, 3) for t in p["tracks"]],
                       "platforms": [[round(a, 3), round(b, 3)] for a, b in p["platforms"]],
                       "stop": p["stop"], "end": p["end"], "street": street, "level": round(level, 3)})
        return cost, Station(facade, tracks, precinct, corridor, int(district), core)

    def _drop(self, fr: Frame, p: dict) -> tuple:
        """(meters between the highest and the lowest ground under the head building and the platforms, the
        level half way between them: the station's ground is graded to it, cutting and filling the least)."""
        h, b = p["hall"] / 2, p["bundle"] / 2
        s1, d1 = np.meshgrid(np.linspace(-h, h, 9), np.linspace(p["front"], p["back"], 4))
        s2, d2 = np.meshgrid(np.linspace(-b, b, 5), np.linspace(p["back"], p["end"], 9))
        s_, d_ = np.concatenate([s1.ravel(), s2.ravel()]), np.concatenate([d1.ravel(), d2.ravel()])
        xy = fr.xy(s_, d_)
        z = self.terrain.height(xy[:, 0], xy[:, 1])
        return float(np.ptp(z)), float((z.max() + z.min()) / 2)

    def _crossings(self, corridor, fr: Frame, precinct) -> int | None:
        """How many main streets cross the corridor, or None when one may not (the boulevard, the ring road)
        or runs along it at less than `cross_angle` degrees."""
        if self.tree is None:
            return 0
        count = 0
        for i in self.tree.query(corridor, predicate="intersects"):
            st = self.streets[self.major[int(i)]]
            if st.kind in NEVER_CROSS:
                return None
            for piece in lines(st.line.intersection(corridor)):
                if piece.length < 0.5:
                    continue
                c = piece.coords
                v = np.array(c[-1]) - np.array(c[0])
                sin = abs(float(v @ fr.u)) / max(float(np.hypot(*v)), 1e-9)   # angle to the tracks, which run along n
                if sin < self.min_sin:
                    return None
                count += 1
        return count

    def _misalign(self, o: np.ndarray, nrm: np.ndarray) -> float:
        """(1 - cos) of the angle between the tracks and the nearest target, times its weight (0 with none)."""
        best = None
        for x, y, w in self.targets:
            v = np.array([x, y]) - o
            dist = float(np.hypot(*v))
            if dist < 1.0:
                continue
            cost = w * (1.0 - float(v @ nrm) / dist)
            best = cost if best is None else min(best, cost)
        return 0.0 if best is None else best


# --- what the station changes in the plan ----------------------------------------------------------

def cut(station: Station | None):
    """The ground the station takes from the districts: precinct and corridor (None without a station)."""
    return None if station is None else unary_union([station.precinct, station.corridor])


def clip_streets(cfg: dict, streets: list, station: Station | None, first: int) -> list:
    """`streets` with the local streets from index `first` on cut back from the precinct, and from the
    corridor where they run along the tracks or end on them; a street crossing the tracks at `cross_angle`
    degrees or more keeps its level crossing. Pieces shorter than 20 m go."""
    if station is None:
        return streets
    fr = Frame(station.facade)
    min_sin = math.sin(math.radians(float(cfg["cross_angle"])))
    precinct = station.precinct.buffer(1.0, join_style="mitre")
    out = list(streets[:first])
    for st in streets[first:]:
        if st.kind != "street" or not (st.line.intersects(precinct) or st.line.intersects(station.corridor)):
            out.append(st)
            continue
        gone = _intervals(st.line, precinct, lambda piece, ends: True)
        gone += _intervals(st.line, station.corridor, lambda piece, ends: ends or _sin(piece, fr) < min_sin)
        for piece in _rest(st.line, gone):
            if piece.length >= 20.0:
                out.append(type(st)(st.kind, st.width, piece, st.surface, st.covered))
    return out


def _sin(piece, fr: Frame) -> float:
    c = piece.coords
    v = np.array(c[-1]) - np.array(c[0])
    return abs(float(v @ fr.u)) / max(float(np.hypot(*v)), 1e-9)


def _intervals(line, zone, drop) -> list:
    """[(t0, t1)] along `line` of its pieces inside `zone` that `drop(piece, ends_inside)` removes, 1 m wider."""
    out = []
    for piece in lines(line.intersection(zone)):
        t0, t1 = sorted((line.project(Point(piece.coords[0])), line.project(Point(piece.coords[-1]))))
        ends = t0 < 1e-6 or t1 > line.length - 1e-6
        if drop(piece, ends):
            out.append((t0 - 1.0, t1 + 1.0))
    return out


def _rest(line, gone: list) -> list:
    """The parts of `line` outside every interval of `gone`."""
    if not gone:
        return [line]
    out, t = [], 0.0
    for a, b in sorted(gone):
        if a > t:
            out.append(substring(line, t, a))
        t = max(t, b)
    if t < line.length:
        out.append(substring(line, t, line.length))
    return [g for g in out if g.geom_type == "LineString" and g.length > 0]


def clip_walks(walks: list, station: Station | None) -> list:
    """The walks with the station's ground cut out (a sidewalk at a block corner reaches into the corridor)."""
    if station is None:
        return walks
    zone = cut(station)
    out = []
    for w in walks:
        if not w.polygon.intersects(zone):
            out.append(w)
            continue
        for poly in polygons(w.polygon.difference(zone)):
            if poly.area >= 0.8:
                out.append(type(w)(w.kind, poly, w.width, w.street, w.side, w.district, w.block))
    return out


def clear(trees: list, station: Station | None) -> list:
    """The trees with those standing on the station's ground left out."""
    if station is None or not trees:
        return trees
    zone = cut(station)
    xy = np.array([(t.x, t.y) for t in trees])
    inside = shapely.contains_xy(zone, xy[:, 0], xy[:, 1]) | (shapely.distance(zone, shapely.points(xy)) < 1.5)
    return [t for t, hit in zip(trees, inside) if not hit]


def buildings(ctx, station: Station | None) -> tuple:
    """(buildings, landmarks): the forecourt paving, the head building and the platforms, and the station's
    `Landmark` with a name on its own stream."""
    if station is None:
        return [], []
    cfg = ctx.style["station"]
    f = station.facade
    fr = Frame(f)
    p = dims(cfg, len(f["tracks"]))
    rng = ctx.rng("station", "tower")
    facade = dict(f)
    facade["tower_side"] = 1 if rng.random() < 0.5 else -1     # the clock tower at the right or left end
    d = station.district
    h = p["hall"] / 2
    t = p["tower"]
    ts = facade["tower_side"] * (h - t / 2)
    head = unary_union([fr.poly(rect(-h, h, p["front"], p["back"])),
                        fr.poly(rect(-float(cfg["pavilion"][0]) / 2, float(cfg["pavilion"][0]) / 2,
                                     p["front"] - float(cfg["pavilion"][1]), p["front"] + 1.0)),
                        fr.poly(rect(ts - t / 2, ts + t / 2, p["front"] - float(cfg["tower_out"]), p["front"] + t))])
    head = shapely.geometry.polygon.orient(head.simplify(0.0), sign=1.0)
    b = p["bundle"] / 2
    platforms = fr.poly(rect(-b, b, p["back"], p["end"]))
    court = fr.poly(rect(-h, h, 0.15, p["front"] - float(cfg["pavilion"][1]) - 0.05))
    court = court.difference(head.buffer(0.05, join_style="mitre"))
    court = max(polygons(court), key=lambda q: q.area)
    hall_h = float(cfg["hall"][2])
    out = [Building(court, "station_forecourt", d, float(cfg["forecourt_lift"]), str(cfg["paving"]),
                    str(cfg["paving"]), facade=facade),
           Building(head, "station", d, hall_h, str(cfg["wall"]), str(cfg["roof"]), 2, facade=facade),
           Building(platforms, "station_platforms", d, float(cfg["canopy"][0]), str(cfg["paving"]),
                    str(cfg["canopy_material"]), facade=facade)]
    c = head.centroid
    namer = NameMaker(ctx.style, ctx.rng("station", "name"))
    return out, [Landmark("station", namer.district("station", s=ctx.s.name), float(c.x), float(c.y))]


def view(plan, ground) -> dict | None:
    """The "station" camera: on the avenue in front of the forecourt, a three-quarter view of the head
    building from the side away from the clock tower, at eye height, looking at the entrance pavilion."""
    b = next((b for b in plan.buildings if b.kind == "station"), None)
    if b is None:
        return None
    f = b.facade
    fr = Frame(f)
    line = plan.streets[f["street"]].line
    o = Point(f["x"], f["y"])
    t = line.project(o)
    side = -f["tower_side"]
    best = None
    for dt in (60.0, -60.0, 40.0, -40.0):
        q = line.interpolate(min(max(t + dt, 0.0), line.length))
        s = float((np.array([q.x, q.y]) - fr.o) @ fr.u)
        key = (s * side < 0, abs(abs(dt) - 60.0))
        if best is None or key < best[0]:
            best = (key, q)
    q = best[1]
    look = fr.xy(0.0, f["forecourt"])
    return {"cam": [round(q.x, 1), round(q.y, 1), round(float(ground.surface(q.x, q.y)) + 1.7, 1)],
            "look": [round(float(look[0]), 1), round(float(look[1]), 1),
                     round(float(ground.surface(float(look[0]), float(look[1]))) + 9.0, 1)]}
