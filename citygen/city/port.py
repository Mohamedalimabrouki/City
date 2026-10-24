"""The harbor (prompt 34): quays along the port districts' coast, a breakwater closing a basin, a lighthouse.

Like the ports of La Goulette, Sousse, Sfax or Bizerte, the port districts meet the sea in straight concrete
quays standing `level` m above the water, with a vertical quay wall down to a basin dredged to `depth` m; the
main harbor (the longest quay) is closed by a curved rubble-mound breakwater from the port's far end, with a
small lighthouse on its round head.

The coast of each port district (the corniche runs on it) is straightened into a few quay segments: the coast
simplified by `straight` m, each segment pushed out to `reach` m past the farthest point of the coast it
covers, so every small cove behind it is filled. The quay stops `end_inset` m from the district's ends and
returns to the coast at right angles. Between the old coast and the quay edge lies the apron (the corniche's
sea half and the reclaimed land); `plan.land` takes it in. The quays never cut the corniche: its whole width
lies on the level ground behind the quay edge.

`plan_port` runs last in the planner and only reads streets and districts: it moves no street, lot,
building or tree. The lighthouse's `Landmark` is appended after every other landmark.

Ground (city/ground.py): the core (the apron plus the corniche, `core_inland` m behind the old coast) is
level at `level`; on the land side the city ground blends back to it over `level_band` m; the open sea
(off the land and the corniche's sea half, `shore` m past the old coast) keeps the natural seabed, dredged
to `depth` m in the basin and `toe` m off every quay wall, fading out over `dredge_band` m. The walls (where
the raised side meets the open sea) are a true step in the ground: the quay walls along the core, and a
sea wall along the corniche's edge where the level band lifts it next to a quay's end.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import shapely
from shapely.geometry import LineString, MultiLineString, Point, Polygon
from shapely.ops import substring, unary_union

from ..names import NameMaker
from .geo import largest, lines
from .model import Landmark


@dataclass
class Quay:
    district: int          # the port district
    line: LineString       # the quay edge, the sea on its right
    coast: LineString      # the old coast it replaces, in the same direction
    apron: Polygon         # between the old coast and the quay edge: the corniche's sea half and reclaimed land
    core: Polygon          # level ground: the apron plus the corniche, `core_inland` m behind the old coast


@dataclass
class Breakwater:
    line: LineString       # crest center line, every `step` m from its root on a quay's end to the head
    quay: int              # the quay whose basin it closes
    basin: Polygon         # the water between the quay, the breakwater and the harbor mouth
    sea_side: int          # +1: the open sea lies to the left of `line`, -1: to the right
    light: tuple           # the lighthouse on the head: (x, y, yaw along the line at the tip, color scheme)


@dataclass
class Port:
    level: float           # quay top above the sea
    quays: list
    breakwaters: list = field(default_factory=list)
    core: object = None    # every quay's core: ground level at `level`
    apron: object = None   # every quay's apron: drawn as quay paving
    shore: object = None   # the land plus `shore` m (the corniche's sea half), near the port: never open sea
    raised: object = None  # the core plus the shore within the level band: the raised side of every wall
    walls: object = None   # where the raised side meets the open sea (quay walls and sea walls)
    dredge: object = None  # the basins and a `toe` m strip off every quay wall, dredged to `depth`
    zone: object = None    # everywhere the ground differs from the city's: core + level band, dredge + its band


def plan_port(ctx, districts: list, land) -> tuple:
    """(Port or None, the lighthouses' landmarks, the land with the aprons added)."""
    cfg = ctx.style.get("port")
    if not cfg or not ctx.kc.get("port") or not ctx.s.coastal:
        return None, [], land
    coast = land.boundary
    quays = []
    for d in districts:
        if d.kind != "port":
            continue
        near = lines(coast.intersection(d.polygon.buffer(1.0)))
        merged = lines(shapely.line_merge(MultiLineString(near))) if near else []
        for piece in merged:
            if piece.length >= float(cfg["min_quay"]) + 2.0 * float(cfg["end_inset"]):
                q = _quay(cfg, piece, land, d.id)
                if q is not None:
                    quays.append(q)
    if not quays:
        return None, [], land
    port = Port(float(cfg["level"]), quays)
    port.core = unary_union([q.core for q in quays])
    port.apron = unary_union([q.apron for q in quays])
    marks = []
    order = sorted(range(len(quays)), key=lambda k: -quays[k].line.length)
    for k in order[:int(cfg.get("breakwaters", 1))]:
        bw = _breakwater(ctx, cfg, quays, k, land, len(port.breakwaters))
        if bw is not None:
            port.breakwaters.append(bw)
    for n, bw in enumerate(port.breakwaters):
        namer = NameMaker(ctx.style, ctx.rng("port", "lighthouse", n, "name"))
        marks.append(Landmark("lighthouse", namer.district("lighthouse", s=ctx.s.name), bw.light[0], bw.light[1]))
    _ground_zones(cfg, port, land)
    return port, marks, unary_union([land, port.apron])


# --- quays --------------------------------------------------------------------------------------------

def _sea_right(line: LineString, land) -> LineString:
    """The line turned so the sea lies on its right."""
    mid = line.interpolate(0.5, normalized=True)
    a = line.interpolate(max(line.project(mid) - 2.0, 0.0))
    b = line.interpolate(min(line.project(mid) + 2.0, line.length))
    t = np.array([b.x - a.x, b.y - a.y])
    t /= max(np.linalg.norm(t), 1e-9)
    left = Point(mid.x - 3.0 * t[1], mid.y + 3.0 * t[0])
    return line if land.contains(left) else LineString(list(line.coords)[::-1])


def _cross(a, b) -> float:
    return float(a[0] * b[1] - a[1] * b[0])


def _quay(cfg: dict, piece: LineString, land, district: int) -> Quay | None:
    """The quay replacing one stretch of coast: straight segments `reach` m past the coast they cover."""
    inset, reach = float(cfg["end_inset"]), float(cfg["reach"])
    c = _sea_right(substring(piece, inset, piece.length - inset), land)
    pts = np.asarray(c.coords)[:, :2]
    along = np.array([c.project(Point(p)) for p in pts])
    v = np.asarray(c.simplify(float(cfg["straight"])).coords)[:, :2]
    sv = np.array([c.project(Point(p)) for p in v])
    lines_ = []
    for i in range(len(v) - 1):
        t = v[i + 1] - v[i]
        t /= max(np.linalg.norm(t), 1e-9)
        n = np.array([t[1], -t[0]])                      # toward the sea
        cover = pts[(along >= sv[i] - 1e-6) & (along <= sv[i + 1] + 1e-6)]
        off = reach + max(0.0, float(((cover - v[i]) @ n).max())) if len(cover) else reach
        lines_.append((v[i] + n * off, v[i + 1] + n * off, t, off))
    q = [lines_[0][0]]
    for (a0, b0, t0, o0), (a1, b1, t1, o1) in zip(lines_[:-1], lines_[1:]):
        cr = _cross(t0, t1)
        p = (b0 + a1) / 2
        if abs(cr) > 0.05:
            hit = a0 + t0 * (_cross(a1 - a0, t1) / cr)
            if np.linalg.norm(hit - p) < 2.0 * max(o0, o1):
                p = hit
        q.append(p)
    q.append(lines_[-1][1])
    line = LineString(q).simplify(1.0)
    if not line.is_simple or line.length < float(cfg["min_quay"]):
        t = pts[-1] - pts[0]
        t /= max(np.linalg.norm(t), 1e-9)
        n = np.array([t[1], -t[0]])
        off = reach + max(0.0, float(((pts - pts[0]) @ n).max()))
        line = LineString([pts[0] + n * off, pts[-1] + n * off])
    apron = largest(Polygon(list(c.coords) + list(line.coords)[::-1]).buffer(0))
    if apron is None or apron.area < 100.0:
        return None
    core = largest(unary_union([apron, c.buffer(float(cfg["core_inland"]), cap_style="flat")]).buffer(0))
    return Quay(district, line, c, apron, core)


# --- breakwater -----------------------------------------------------------------------------------------

def _bezier(p0, p1, p2, p3, n: int) -> np.ndarray:
    t = np.linspace(0.0, 1.0, n)[:, None]
    return ((1 - t) ** 3) * p0 + 3 * ((1 - t) ** 2) * t * p1 + 3 * (1 - t) * t * t * p2 + t ** 3 * p3


def _breakwater(ctx, cfg: dict, quays: list, k: int, land, n: int) -> Breakwater | None:
    """A curved rubble mound from the end of quay k away from the city center: out to sea along the quay's
    normal, then turning to run back along it, leaving the harbor mouth at the other end."""
    q = quays[k]
    rng = ctx.rng("port", "breakwater", n)
    share, lo, hi = (float(v) for v in cfg["out"])
    run0, run1 = (float(v) for v in cfg["run"])
    bend = float(rng.uniform(*cfg["bend"]))
    run_share = float(rng.uniform(run0, run1))
    ends = np.asarray(q.line.coords)[:, :2]
    center = np.array([ctx.s.x, ctx.s.y])
    first = [-1, 0] if np.linalg.norm(ends[-1] - center) >= np.linalg.norm(ends[0] - center) else [0, -1]
    other_cores = [x.core for i, x in enumerate(quays) if i != k]
    for root_at in first:                                  # the far end first, then the near one
        coords = ends if root_at == 0 else ends[::-1]      # from the root along the quay
        root, nxt = coords[0], coords[1]
        u = coords[-1] - root
        length = float(np.linalg.norm(u))
        u /= max(length, 1e-9)
        t = nxt - root
        t /= max(np.linalg.norm(t), 1e-9)
        nrm = np.array([t[1], -t[0]]) if root_at == 0 else np.array([-t[1], t[0]])   # toward the sea
        out = min(max(share * length, lo), hi)
        run = run_share * length
        tip = root + nrm * out * (1.0 - bend) + u * run
        curve = _bezier(root, root + nrm * out, tip - u * min(run, out) * 0.9, tip, 240)
        line = LineString(curve)
        step = float(cfg["step"])
        line = LineString([line.interpolate(s) for s in np.append(np.arange(0.0, line.length, step), line.length)])
        tail = substring(line, float(cfg["crest"][1]) * 2.0, line.length)
        clear = float(cfg["shore"]) + float(cfg["land_clear"])
        if tail.distance(land) < clear or any(tail.distance(c) < clear for c in other_cores):
            continue
        basin = largest(Polygon(list(map(tuple, coords)) + list(line.coords)[::-1]).buffer(0))
        if basin is None or basin.area < 1000.0:
            continue
        mid = line.interpolate(0.5, normalized=True)
        a, b = line.interpolate(line.project(mid) - 1.0), line.interpolate(line.project(mid) + 1.0)
        d = np.array([b.x - a.x, b.y - a.y]) / 2.0
        sea_side = -1 if basin.contains(Point(mid.x - 20.0 * d[1], mid.y + 20.0 * d[0])) else 1
        e = np.asarray(line.coords)[-2:]
        yaw = math.atan2(e[1][1] - e[0][1], e[1][0] - e[0][0])
        schemes = list(cfg["lighthouse"]["schemes"])
        scheme = schemes[int(ctx.rng("port", "lighthouse", n).integers(len(schemes)))]
        return Breakwater(line, k, basin, sea_side, (float(e[1][0]), float(e[1][1]), yaw, scheme))
    return None


# --- ground zones ---------------------------------------------------------------------------------------

def _ground_zones(cfg: dict, port: Port, land) -> None:
    """The shore, raised side, walls, dredged water and influence zone the ground and the mesher read."""
    band, dband = float(cfg["level_band"]), float(cfg["dredge_band"])
    toe = float(cfg["toe"])
    dredge = [q.line.buffer(-toe, single_sided=True) for q in port.quays]   # the sea lies on the right
    dredge += [bw.basin for bw in port.breakwaters]
    port.dredge = unary_union(dredge).difference(port.core)
    region = unary_union([port.core.buffer(band + 20.0), port.dredge.buffer(dband + 20.0)])
    port.shore = land.buffer(float(cfg["shore"]), quad_segs=4).simplify(0.5).intersection(region)
    port.raised = unary_union([port.core, port.shore.intersection(port.core.buffer(band))])
    walls = port.raised.boundary.difference(port.shore.buffer(-0.05))
    port.walls = shapely.line_merge(MultiLineString([g for g in lines(walls) if g.length > 0.5]))
    port.zone = unary_union([port.core.buffer(band + 0.5), port.dredge.buffer(dband + 0.5)])
    for g in (port.core, port.apron, port.shore, port.raised, port.dredge, port.zone):
        shapely.prepare(g)


# --- the camera -----------------------------------------------------------------------------------------

def view(plan, ground, cfg: dict) -> dict | None:
    """The "port" camera: up over the water off the harbor mouth, looking back across the basin past the
    lighthouse at the breakwater curving away to its root, the quay along the shore on the other side."""
    port = getattr(plan, "port", None)
    if port is None or not port.breakwaters:
        return None
    bw = port.breakwaters[0]
    q = port.quays[bw.quay]
    root = np.asarray(bw.line.coords[0])
    ends = np.asarray(q.line.coords)[:, :2]
    mouth = ends[-1] if np.linalg.norm(ends[0] - root) < np.linalg.norm(ends[-1] - root) else ends[0]
    u = root - mouth
    u /= np.linalg.norm(u)
    tip = np.array(bw.light[:2])
    sea = tip - mouth - u * float((tip - mouth) @ u)
    sea /= max(np.linalg.norm(sea), 1e-9)
    back, side, height = (float(v) for v in cfg["camera"])
    cam = mouth - u * back + sea * side
    focus = np.asarray(bw.basin.centroid.coords[0]) * 0.6 + tip * 0.25 + root * 0.15
    z = max(float(ground.surface(cam[0], cam[1])), 0.0) + height
    return {"cam": [round(float(cam[0]), 1), round(float(cam[1]), 1), round(z, 1)],
            "look": [round(float(focus[0]), 1), round(float(focus[1]), 1), round(port.level, 1)]}


def lengths(port) -> dict:
    """Meters of quay edge and of breakwater (map, gazetteer, stats)."""
    if port is None:
        return {"quays": 0.0, "breakwaters": 0.0}
    return {"quays": round(sum(q.line.length for q in port.quays), 1),
            "breakwaters": round(sum(bw.line.length for bw in port.breakwaters), 1)}
