"""The corniche's seafront (prompt 36): a raised promenade on the sea side of the corniche, `[corniche]`.

Like the corniches of La Marsa, Sousse or Bizerte: along the colonial, modern and residential stretches the
sea half of the corniche becomes a paved promenade, raised like a sidewalk, its curb where the land side's
sidewalk would end (`curb` m inside the corniche's sea edge), running on past the corniche's edge toward the
sea. Its sea edge is a low stone sea wall with a whitewashed coping band and a white iron railing; the
beach-side palm row stands in tree pits by the curb with lamps between the palms, and benches along the
railing face the sea. Beyond the wall lies the natural beach (sand from the terrain's beach biome), reached by
flights of steps, or, where the water comes close, the wall stands at the water with its foot in the sea.

Plan (`plan_fronts`, last in the planner, after the harbor's props): the corniche is walked in `step` m
stations. A station counts when the district on its land side is in `districts` and the sea side has room
for at least `min_width` m between the curb and the water line (where the natural ground, which is what lies
seaward of the city limit on the corniche's center line, is `water` m above the sea). The promenade is `width`
m wide where at least `beach_min` m of sand remain beyond it; as the water comes closer the wall moves out with
it, reaching the water when the room is down to `max_width` (`width_for`, continuous, measured on the narrowest
of a station and its two neighbours, then averaged over five stations and never past the water), so the wall
runs in easy curves and never reaches into the sea. The segment between two stations counts when both do,
no other street's surface covers more than `cross_area` m2 of its band (a side street ending on the corniche
grazes it; one crossing the sea half does not), and it keeps `clear` m from the harbor's ground (`Port.zone`)
and the drawn-up boats. Runs of segments make the
stretches (`Front`, `plan.fronts`); each is cut into `piece` m walks (`Walk("seafront")`) whose `edge` is the
stretch's curb line: the top is level across the promenade, at the curb's height (city/ground.py). Steps go
down to the sand every `stair_every` m where at least `stair_sand` m of sand lie beyond the wall. The beach-side palm row of
`street_trees` moves onto the promenade, `palm_inset` m from the curb at the same station: every palm keeps its
index, kind and height (its kit variant and turn are keyed on the index). Nothing else in the plan moves.

Dressing (`Seafront`, built once per city by the dresser): lamps in the palm row, in every `lamp_every`th gap
between two palms; a bench (role `seafront_bench`, else `bench`) in each gap by chance, `bench_back` m in
from the sea edge and facing the sea; the railing as `railing_sea` pieces stretched to fit the sea edge between
its bends, broken at the steps. Each choice has its own stream (`rng("seafront", "lamp" | "bench", k, palm index)`).
The cafe terraces come with them (prompt 37, city/terraces.py): a gap taken by a kiosk cafe gets no bench.
"""
from __future__ import annotations

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon
from shapely.strtree import STRtree

from .model import Front, Walk
from .moorings import land_zone
from .parking import lying_on, street_frame
from .terraces import Terraces


def _cfg(style: dict) -> dict:
    return style.get("corniche", {})


def width_for(room: float, cfg: dict) -> float:
    """Promenade width for `room` m between the curb and the water line (0 when it does not fit): `width` while
    `beach_min` m of sand remain; as the water comes closer the wall moves out with it, reaching the water
    when the room is down to `max_width`, then standing at the water. Continuous in the room, so the wall
    does not zigzag where the room hovers about `width + beach_min`."""
    width, wmax, wmin = float(cfg["width"]), float(cfg["max_width"]), float(cfg["min_width"])
    full = width + float(cfg["beach_min"])
    if room >= full:
        return width
    if room >= wmax:
        return width + (wmax - width) * (full - room) / max(full - wmax, 1e-9)
    return room if room >= wmin else 0.0


def _smooth(width: np.ndarray, cap: np.ndarray, reach: int = 2) -> np.ndarray:
    """Widths averaged over a station and `reach` on each side (the wall runs in long, easy curves), never
    more than `cap` (the room to the water), 0 where a station has no promenade."""
    pad = np.pad(width, reach, mode="edge")
    mean = np.convolve(pad, np.ones(2 * reach + 1) / (2 * reach + 1), mode="valid")
    return np.where(width > 0.0, np.minimum(mean, cap), 0.0)


def _rooms(terrain, p: np.ndarray, out: np.ndarray, curb: float, cfg: dict) -> np.ndarray:
    """Meters from the curb to the water line at each station (inf beyond the range sampled)."""
    reach = float(cfg["max_width"]) + float(cfg["beach_min"]) + 2.0
    o = curb + np.arange(0.0, reach + 0.25, 0.25)
    xs = p[:, 0, None] + out[:, 0, None] * o[None, :]
    ys = p[:, 1, None] + out[:, 1, None] * o[None, :]
    h = np.asarray(terrain.height(xs.ravel(), ys.ravel()), dtype=np.float64).reshape(xs.shape)
    wet = h <= float(cfg["water"])
    first = np.argmax(wet, axis=1)
    return np.where(wet.any(axis=1), o[first] - curb, np.inf)


def _sides(terrain, p: np.ndarray, n: np.ndarray) -> np.ndarray:
    """+1 where the sea lies left of the street (the lower ground 12 m off the line), else -1."""
    left = terrain.height(p[:, 0] + n[:, 0] * 12.0, p[:, 1] + n[:, 1] * 12.0)
    right = terrain.height(p[:, 0] - n[:, 0] * 12.0, p[:, 1] - n[:, 1] * 12.0)
    return np.where(np.asarray(left) < np.asarray(right), 1, -1)


def _districts(plan, pts: np.ndarray) -> np.ndarray:
    """Index of the district holding each point, -1 for none."""
    polys = [d.polygon for d in plan.districts]
    out = np.full(len(pts), -1)
    if not polys or not len(pts):
        return out
    inp, hit = STRtree(polys).query(shapely.points(pts), predicate="within")
    for i, j in sorted(zip(inp.tolist(), hit.tolist()), reverse=True):   # the lowest district index wins
        out[i] = j
    return out


def _blocked(ctx, plan) -> object:
    """What the promenade keeps `clear` m from besides other streets: the harbor's ground, drawn-up boats."""
    parts = []
    port = getattr(plan, "port", None)
    if port is not None and port.zone is not None:
        parts.append(port.zone)
    zone = land_zone(plan, ctx.style.get("port", {}).get("props"))
    if zone is not None:
        parts.append(zone)
    if not parts:
        return None
    out = shapely.union_all(parts)
    shapely.prepare(out)
    return out


def plan_fronts(ctx, plan) -> list:
    """The seafront stretches; appends their walks to `plan.walks` and moves the beach-side palms onto them."""
    cfg = _cfg(ctx.style)
    if not cfg or not plan.streets:
        return []
    terrain = ctx.world.terrain
    lines = [st.line for st in plan.streets]
    surfaces = [st.line.buffer(st.width / 2.0, cap_style="flat") for st in plan.streets]
    line_tree, surface_tree = STRtree(lines), STRtree(surfaces)
    blocked = _blocked(ctx, plan)
    parking = ctx.style.get("dressing", {}).get("parking", {})
    fronts = []
    for k, st in enumerate(plan.streets):
        if st.kind != "corniche" or st.line.length < 2 * float(cfg["step"]):
            continue
        inside = lying_on(k, st.line, surfaces[k], line_tree, lines, parking)
        others = [surfaces[j] for j in range(len(surfaces)) if j not in inside]
        fronts += _street_fronts(ctx, plan, k, cfg, terrain, STRtree(others) if others else None, blocked)
    for f in fronts:
        _move_palms(plan, f, cfg)
    for f in fronts:
        plan.walks += _pieces(plan, f, cfg)
    return fronts


def _street_fronts(ctx, plan, k: int, cfg: dict, terrain, others, blocked) -> list:
    st = plan.streets[k]
    step, clear = float(cfg["step"]), float(cfg["clear"])
    curb = st.width / 2.0 - float(cfg["curb"])
    d = np.arange(0.0, st.line.length + 1e-9, step)
    p, n = street_frame(st.line, d)
    side = _sides(terrain, p, n)
    out = n * side[:, None]                                   # toward the sea
    land = p - out * (st.width / 2.0 + 8.0)
    dist = _districts(plan, land)
    kinds = set(cfg["districts"])
    ok = np.array([j >= 0 and plan.districts[j].kind in kinds for j in dist.tolist()], dtype=bool)
    room = _rooms(terrain, p, out, curb, cfg)
    narrow = np.minimum(room, np.minimum(np.r_[room[:1], room[:-1]], np.r_[room[1:], room[-1:]]))
    width = _smooth(np.array([width_for(r, cfg) for r in narrow.tolist()]), narrow)
    ok &= width >= float(cfg["min_width"])
    inner = p + out * curb
    outer = p + out * (curb + width)[:, None]
    seg = np.zeros(max(len(d) - 1, 0), dtype=bool)
    for i in range(len(seg)):
        if not (ok[i] and ok[i + 1] and side[i] == side[i + 1]):
            continue
        band = Polygon([inner[i], inner[i + 1], outer[i + 1], outer[i]])
        if not band.is_valid:
            continue
        if others is not None and _crossed(others, band, float(cfg["cross_area"])):
            continue
        if blocked is not None and blocked.intersects(band.buffer(clear)):
            continue
        seg[i] = True
    fronts = []
    i = 0
    while i < len(seg):
        if not seg[i]:
            i += 1
            continue
        j = i
        while j < len(seg) and seg[j]:
            j += 1
        fronts.append(_front(k, cfg, int(side[i]), int(dist[i]), d[i:j + 1], inner[i:j + 1], outer[i:j + 1],
                             room[i:j + 1] - width[i:j + 1], out[i:j + 1]))
        i = j
    return fronts


def _crossed(others, band, area: float) -> bool:
    """Does another street's surface cover more than `area` m2 of the band? A side street ending on the
    corniche's center line may graze it with a corner (the promenade runs on over that); one running out
    across the sea half breaks the promenade."""
    hit = others.query(band, predicate="intersects")
    return any(band.intersection(others.geometries[int(j)]).area > area for j in hit)


def _front(k: int, cfg: dict, side: int, district: int, d, inner, outer, sand, out) -> Front:
    """One stretch, with its flights of steps and its meters of beach."""
    beach = sand >= float(cfg["beach_min"])
    f = Front(k, side, district, LineString(inner), LineString(outer), (float(d[0]), float(d[-1])))
    f.beach = float(sum(d[m + 1] - d[m] for m in range(len(d) - 1) if beach[m] and beach[m + 1]))
    every, width = float(cfg["stair_every"]), float(cfg["stair"][0])
    room = sand >= float(cfg["stair_sand"])
    for s in np.arange(d[0] + every / 2.0, d[-1] - width, every):
        m = min(int(np.searchsorted(d, s, side="right")) - 1, len(d) - 2)
        if s - d[0] < width or not (room[m] and room[m + 1]):
            continue
        t = (s - d[m]) / (d[m + 1] - d[m])
        q = outer[m] + (outer[m + 1] - outer[m]) * t
        u = out[m] + (out[m + 1] - out[m]) * t
        u = u / max(float(np.hypot(*u)), 1e-9)
        f.stairs.append((float(q[0]), float(q[1]), float(u[0]), float(u[1])))
    return f


def _pieces(plan, f: Front, cfg: dict) -> list:
    """The stretch as `piece` m walks (whole segments), each knowing the stretch's curb line."""
    inner = np.asarray(f.edge.coords)
    outer = np.asarray(f.sea.coords)
    per = max(1, int(round(float(cfg["piece"]) / float(cfg["step"]))))
    out = []
    for a in range(0, len(inner) - 1, per):
        b = min(a + per, len(inner) - 1)
        ring = np.vstack([inner[a:b + 1], outer[a:b + 1][::-1]])
        poly = Polygon(ring)
        if not poly.is_valid:
            poly = max(getattr(poly.buffer(0), "geoms", [poly.buffer(0)]), key=lambda g: g.area)
        width = float(np.mean(np.hypot(*(outer[a:b + 1] - inner[a:b + 1]).T)))
        out.append(Walk("seafront", poly, width, f.street, f.side, f.district, -1, f.edge))
    return out


def _move_palms(plan, f: Front, cfg: dict) -> None:
    """The beach-side palm row of `street_trees` onto the promenade, `palm_inset` m from the curb."""
    st = plan.streets[f.street]
    offset = st.width / 2.0 - 2.5                             # where street_trees planted the row
    if not plan.trees:
        return
    xy = np.array([(t.x, t.y) for t in plan.trees])
    pts = shapely.points(xy)
    dist = shapely.distance(st.line, pts)
    near = np.nonzero(np.abs(dist - offset) < 0.05)[0]
    if not len(near):
        return
    d = shapely.line_locate_point(st.line, pts[near])
    p, n = street_frame(st.line, d)
    lo, hi = f.span
    curb = st.width / 2.0 - float(cfg["curb"])
    for m, i in enumerate(near.tolist()):
        t = plan.trees[i]
        if t.kind != "palm" or not (lo + 1.0 <= d[m] <= hi - 1.0):
            continue
        if (xy[i] - p[m]) @ n[m] * f.side <= 0.0:             # the land-side row stays
            continue
        q = p[m] + n[m] * f.side * (curb + float(cfg["palm_inset"]))
        t.x, t.y = float(q[0]), float(q[1])


def palms_of(plan, f: Front, cfg: dict) -> list:
    """[(distance along the street, tree index)] of the palms standing in the stretch's palm row."""
    st = plan.streets[f.street]
    if not plan.trees:
        return []
    row = st.width / 2.0 - float(cfg["curb"]) + float(cfg["palm_inset"])
    xy = np.array([(t.x, t.y) for t in plan.trees])
    pts = shapely.points(xy)
    near = np.nonzero((np.abs(shapely.distance(st.line, pts) - row) < 0.05)
                      & (shapely.distance(f.edge, pts) < float(cfg["palm_inset"]) + 0.05))[0]
    out = [(float(st.line.project(Point(xy[i]))), int(i)) for i in near.tolist() if plan.trees[i].kind == "palm"]
    return sorted(out)


def lengths(fronts: list) -> dict:
    """Meters of promenade and of promenade with a beach beyond its wall (stats)."""
    return {"promenade_m": round(sum(f.span[1] - f.span[0] for f in fronts), 1),
            "beach_m": round(sum(f.beach for f in fronts), 1)}


# --- dressing -------------------------------------------------------------------------------------------

class Seafront:
    """Lamps, benches and the railing of the city's seafront promenade, made once, kept by tile."""

    def __init__(self, dresser):
        from .dressing import Placement, yaw_of   # dressing imports this module
        self.Placement, self.yaw_of = Placement, yaw_of
        self.d, self.plan = dresser, dresser.plan
        self.cfg = _cfg(dresser.world.style)
        self.terraces = Terraces(self)
        self._items = None
        self._area = None

    def placements(self, tile) -> list:
        """Fresh copies of the pieces whose anchor lies in the tile (x0 <= x < x1, y0 <= y < y1)."""
        if not self.area().intersects(tile):
            return []                                         # no need to lay out the seafront for a tile far from it
        x0, y0, x1, y1 = tile.bounds
        return [self.Placement(p.piece, p.x, p.y, p.z, p.yaw, p.on_ground, p.scale, p.stretch)
                for p in self.items() if x0 <= p.x < x1 and y0 <= p.y < y1]

    def area(self):
        """Where the seafront's pieces may stand: round its stretches, across the corniche to the cafes' terraces."""
        if self._area is None:
            fronts = getattr(self.plan, "fronts", ()) if self.cfg else ()
            parts = [f.sea.buffer(self.plan.streets[f.street].width + 2 * float(self.cfg["max_width"])) for f in fronts]
            self._area = shapely.union_all(parts) if parts else Polygon()
            shapely.prepare(self._area)
        return self._area

    def items(self) -> list:
        if self._items is None:
            self._items = []
            if self.cfg:
                for f in getattr(self.plan, "fronts", ()):
                    palms = palms_of(self.plan, f, self.cfg)
                    kiosks = self.terraces.kiosks(f, palms)              # cafe kiosks take their gap's bench (prompt 37)
                    base = self._lamps_and_benches(f, palms, kiosks) + self._railing(f)
                    self._items += base + self.terraces.items(f, palms, base, kiosks)
        return self._items

    def _frame(self, f: Front, d: float) -> tuple:
        """(point on the street line, unit vector toward the sea, promenade width) at distance d."""
        st = self.plan.streets[f.street]
        p, n = street_frame(st.line, np.array([d]))
        out = n[0] * f.side
        inner = np.asarray(f.edge.coords)
        outer = np.asarray(f.sea.coords)
        t = np.clip((d - f.span[0]) / max(f.span[1] - f.span[0], 1e-9) * (len(inner) - 1), 0, len(inner) - 1)
        m = min(int(t), len(inner) - 2)
        w0, w1 = (float(np.hypot(*(outer[j] - inner[j]))) for j in (m, m + 1))
        return p[0], out, w0 + (w1 - w0) * (t - m)

    def _lamps_and_benches(self, f: Front, palms: list, taken: dict) -> list:
        cfg, d = self.cfg, self.d
        st = self.plan.streets[f.street]
        curb = st.width / 2.0 - float(cfg["curb"])
        stairs = [np.array(s[:2]) for s in f.stairs]
        clear = float(cfg["stair"][0]) / 2.0 + 1.6
        out = []
        for m in range(len(palms) - 1):
            (da, ia), (db, _) = palms[m], palms[m + 1]
            if db - da < float(cfg["bench_gap"]):
                continue
            mid = (da + db) / 2.0
            p, sea, width = self._frame(f, mid)
            if m % int(cfg["lamp_every"]) == 0 and d.has("street_lamp"):
                q = p + sea * (curb + float(cfg["palm_inset"]))
                name, _ = d.pick("street_lamp", d.rng("seafront", "lamp", f.street, ia))
                out.append(self.Placement(name, float(q[0]), float(q[1]), 0.0, self.yaw_of(sea)))
            rng = d.rng("seafront", "bench", f.street, ia)
            role = "seafront_bench" if d.has("seafront_bench") else "bench"
            if d.has(role) and rng.random() < float(cfg["bench"]) and m not in taken:
                q = p + sea * (curb + width - float(cfg["bench_back"]))
                if all(float(np.hypot(*(q - s))) > clear for s in stairs):
                    name, _ = d.pick(role, rng)
                    out.append(self.Placement(name, float(q[0]), float(q[1]), 0.0, self.yaw_of(sea)))
        return out

    def _railing(self, f: Front) -> list:
        """`railing_sea` pieces along the sea edge, stretched to fit between its bends, broken at the steps."""
        cfg = self.cfg
        if "railing_sea" not in self.d.kit.pieces:
            return []
        sea = f.sea
        inset = float(cfg["railing_inset"])
        gaps = [(sea.project(Point(s[0], s[1])), float(cfg["stair"][0]) / 2.0 + 0.05) for s in f.stairs]
        cuts = [0.0] + [v for g, h in sorted(gaps) for v in (g - h, g + h)] + [sea.length]
        piece = float(cfg["railing_piece"])
        sea_dir = f.side
        out = []
        for a, b in zip(cuts[0::2], cuts[1::2]):
            if b - a < 0.3:
                continue
            count = max(1, int(round((b - a) / piece)))
            ds = np.linspace(a, b, count + 1)
            pts = shapely.get_coordinates(shapely.line_interpolate_point(sea, ds))
            for q0, q1 in zip(pts[:-1], pts[1:]):
                v = q1 - q0
                size = float(np.hypot(*v))
                if size < 1e-6:
                    continue
                u = v / size
                inward = np.array([u[1], -u[0]]) * sea_dir      # the sea edge runs with the street: land on this side
                c = (q0 + q1) / 2.0 + inward * inset
                out.append(self.Placement("railing_sea", float(c[0]), float(c[1]), 0.0,
                                          self.yaw_of(-inward), True, 1.0, size / piece))
        return out


# --- the camera -----------------------------------------------------------------------------------------

def view(plan, ground, style: dict, reach: float = 900.0) -> dict | None:
    """The "corniche" camera: at eye level on the promenade of the longest stretch near the center, a third of
    the way across from the palms, looking along it; the sea and its railing on one side, the palms, the
    corniche and the town on the other."""
    cfg = _cfg(style)
    fronts = getattr(plan, "fronts", ())
    if not cfg or not fronts:
        return None
    center = Point(plan.settlement.x, plan.settlement.y)
    near = [f for f in fronts if f.edge.distance(center) < reach] or list(fronts)
    f = max(near, key=lambda f: f.span[1] - f.span[0])
    st = plan.streets[f.street]
    lo, hi = f.span
    d0 = min(max(st.line.project(center), lo + 12.0), hi - 12.0)
    step = 60.0 if hi - d0 >= d0 - lo else -60.0               # look along the longer side
    d1 = min(max(d0 + step, lo), hi)
    curb = st.width / 2.0 - float(cfg["curb"])
    spots = []
    for d, share in ((d0, 0.42), (d1, 0.55)):
        p, n = street_frame(st.line, np.array([d]))
        q = p[0] + n[0] * f.side * (curb + float(cfg["palm_inset"]) + share * (float(cfg["width"]) - float(cfg["palm_inset"])))
        spots.append(q)
    (cx, cy), (lx, ly) = spots
    cz = float(ground.surface(cx, cy)) + 1.7
    lz = float(ground.surface(lx, ly)) + 1.4
    return {"cam": [round(float(cx), 1), round(float(cy), 1), round(cz, 1)],
            "look": [round(float(lx), 1), round(float(ly), 1), round(lz, 1)]}
