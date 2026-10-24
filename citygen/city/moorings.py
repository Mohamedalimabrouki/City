"""Boats, cranes and cargo of the harbor (prompt 35): `CityPlan.props`.

Like the ports of Mahdia, Kelibia or Sfax, the main quay (the one the breakwater shelters) is shared: from
the breakwater's root, a `commercial` share of it is the commercial quay with two or three portal cranes
on a pair of rails and a yard of containers and crates behind them; the rest, and every other quay, is
the fishing port. Along it the planner walks the quay edge and lays groups one after another: a row of
`row` fishing boats moored bow- or stern-to, side by side, or a trawler moored alongside, with stretches
of quay left empty; a quay no breakwater shelters is quieter (`open_quay`). Every boat keeps `gap` m off
the quay wall (fenders hang on it) and `side_gap` m from its neighbours. A few boats lie at anchor in the
basin, all heading into the same breeze, `swing` m apart; and when the natural beach next to the port
has room, fishing boats are drawn up on the sand, bow toward the land, stern near the water.

A boat fits where its plan envelope (`[port.props] size`, times its scale) stays off the land, the raised
quays, the corniche's sea walls and the breakwater (`breakwater_clear`), and the seabed under it lies at
least its draft plus `keel_clear` deep: the basin and the strip off every quay are dredged to the port's
`depth`, elsewhere the natural seabed counts. Cranes and cargo stand on the quay apron, `street_clear` m
off every street, walk and building and `tree_clear` m from trees; a drawn-up boat keeps `beach_clear`.

Everything comes from the port's own streams (`rng("port", "props", ...)`) and is planned after every
other part of the city, so nothing else moves. Props are drawn by the tile holding their center
(`Dresser.props`); the tiles keep every other piece off the props that stand on land (`land_zone`).
"""
from __future__ import annotations

import math

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union
from shapely.strtree import STRtree

from .model import Prop


def plan_props(ctx, plan) -> list:
    """The harbor's props, or [] for a city without a port or without `[port.props]`."""
    port = getattr(plan, "port", None)
    cfg = ctx.style.get("port", {}).get("props")
    if port is None or not cfg:
        return []
    h = Harbor(ctx, plan, cfg)
    main = port.breakwaters[0].quay if port.breakwaters else max(range(len(port.quays)),
                                                                 key=lambda k: port.quays[k].line.length)
    for k, q in enumerate(port.quays):
        if k == main:
            commercial, fishing = h.split(q)
            h.commercial(k, q, commercial)
            h.moor(k, fishing, sheltered=bool(port.breakwaters))
        else:
            h.moor(k, [(0.0, q.line.length)], sheltered=False)
    h.anchor()
    h.beach()
    return h.props


def box(prop: Prop, size) -> Polygon:
    """The prop's plan envelope: `size` (length along its x, width) times its scale, turned by its yaw."""
    length, width = (float(v) * prop.scale / 2 for v in size)
    c, s = math.cos(prop.yaw), math.sin(prop.yaw)
    return Polygon([(prop.x + x * c - y * s, prop.y + x * s + y * c)
                    for x, y in ((-length, -width), (length, -width), (length, width), (-length, width))])


def land_zone(plan, cfg: dict | None):
    """Where the props that stand on land (quay and beach) stand: no other piece may stand there."""
    if not cfg or not getattr(plan, "props", None):
        return None
    zone = unary_union([box(p, cfg["size"][_sized(p.kind)]) for p in plan.props if p.on != "sea"])
    if zone.is_empty:
        return None
    shapely.prepare(zone)
    return zone


FISHING = ("boat_lateen", "boat_cabin", "boat_rowing")


def _sized(kind: str) -> str:
    """The `[port.props] size` (and `draft`) entry of a piece: the fishing boats share one hull, the two
    cranes one portal, the two container stacks one envelope."""
    if kind in FISHING:
        return "boat_fishing"
    if kind in ("crane_0", "crane_1"):
        return "crane"
    return "cargo_containers" if kind.startswith("cargo_containers") else kind


class Harbor:
    """The planner's state: the props so far and the obstacles they keep off."""

    def __init__(self, ctx, plan, cfg: dict):
        self.ctx, self.plan, self.cfg, self.port = ctx, plan, cfg, plan.port
        self.pcfg = ctx.style["port"]
        self.props: list = []
        self.boxes: list = []                              # plan boxes of the props so far
        port = self.port
        self.blocked = unary_union([plan.land, port.raised, port.shore])
        clear = float(cfg["breakwater_clear"])
        self.rubble = unary_union([bw.line.buffer(clear) for bw in port.breakwaters]) if port.breakwaters else None
        for g in (self.blocked, self.rubble):
            if g is not None:
                shapely.prepare(g)
        built = [s.line.buffer(s.width / 2, cap_style="flat") for s in plan.streets]
        built += [w.polygon for w in getattr(plan, "walks", ())]
        built += [b.footprint for b in plan.buildings]
        self.built = STRtree(built) if built else None
        self.built_geoms = built
        self.trees = STRtree([Point(t.x, t.y) for t in plan.trees]) if plan.trees else None
        self.depth = -float(self.pcfg["depth"])
        self.crane = f"crane_{int(self.rng('crane').integers(2))}"   # one crane model per harbor

    def rng(self, *path):
        return self.ctx.rng("port", "props", *path)

    def size(self, kind: str):
        return self.cfg["size"][_sized(kind)]

    def draft(self, kind: str, scale: float) -> float:
        return float(self.cfg["draft"][_sized(kind)]) * scale

    def scale(self, kind: str, u: float) -> float:
        lo, hi = (float(v) for v in self.cfg["scale"][kind])
        return lo + (hi - lo) * u

    # --- checks -------------------------------------------------------------------------------------
    def _near_built(self, poly, clear: float) -> bool:
        if self.built is not None:
            for k in self.built.query(poly.buffer(clear)):
                if self.built_geoms[int(k)].distance(poly) < clear:
                    return True
        return False

    def _near_trees(self, poly, clear: float) -> bool:
        return self.trees is not None and len(self.trees.query(poly, predicate="dwithin", distance=clear)) > 0

    def _free(self, poly, gap: float) -> bool:
        return not any(b.distance(poly) < gap for b in self.boxes if b.bounds[0] - gap < poly.bounds[2]
                       and poly.bounds[0] - gap < b.bounds[2] and b.bounds[1] - gap < poly.bounds[3]
                       and poly.bounds[1] - gap < b.bounds[3])

    def _floats(self, poly, kind: str, scale: float) -> bool:
        """Off the land, quays, sea walls and breakwater, over water deep enough."""
        if self.blocked.intersects(poly) or (self.rubble is not None and self.rubble.intersects(poly)):
            return False
        need = -(self.draft(kind, scale) + float(self.cfg["keel_clear"]))
        pts = np.vstack([np.asarray(poly.exterior.coords)[:4], np.asarray(poly.centroid.coords)])
        dredged = shapely.contains_xy(self.port.dredge, pts[:, 0], pts[:, 1])
        sea = np.where(dredged, self.depth, self.ctx.world.terrain.height(pts[:, 0], pts[:, 1]))
        return bool(np.all(sea <= need))

    def _add(self, prop: Prop, poly) -> None:
        self.props.append(prop)
        self.boxes.append(poly)

    def _boat(self, kind: str, x: float, y: float, yaw: float, scale: float, gap: float) -> bool:
        prop = Prop(kind, round(float(x), 3), round(float(y), 3), round(float(yaw), 5), round(float(scale), 4), "sea")
        poly = box(prop, self.size(kind))
        if self._floats(poly, kind, scale) and self._free(poly, gap):
            self._add(prop, poly)
            return True
        return False

    # --- the quays ----------------------------------------------------------------------------------
    def split(self, q) -> tuple:
        """([(s0, s1)] commercial, [(s0, s1)] fishing) along the main quay: the commercial quay by the harbor
        mouth (deep water, ships need not cross the basin), the fishing port in the sheltered end by the
        breakwater's root."""
        n = q.line.length
        share = float(self.cfg["commercial"]) * n
        root = Point(self.port.breakwaters[0].line.coords[0]) if self.port.breakwaters else None
        mouth_at_end = root is None or q.line.project(root) < n / 2
        return ([(n - share, n)], [(0.0, n - share)]) if mouth_at_end else ([(0.0, share)], [(share, n)])

    def _frame(self, line: LineString, s: float) -> tuple:
        """Point, unit tangent and unit normal toward the sea (the sea lies on the line's right) at s."""
        a, b = line.interpolate(max(s - 0.5, 0.0)), line.interpolate(min(s + 0.5, line.length))
        t = np.array([b.x - a.x, b.y - a.y])
        t /= max(np.linalg.norm(t), 1e-9)
        p = line.interpolate(s)
        return np.array([p.x, p.y]), t, np.array([t[1], -t[0]])

    def _straights(self, line: LineString, spans: list) -> list:
        """Straight stretches (s0, s1) of the quay within the spans, `end_clear` m from ends and corners."""
        c = np.asarray(line.coords)[:, :2]
        s = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(c, axis=0).T))])
        end = float(self.cfg["end_clear"])
        out = []
        for a, b in zip(s[:-1], s[1:]):
            for s0, s1 in spans:
                lo, hi = max(a, s0) + end, min(b, s1) - end
                if hi - lo > 6.0:
                    out.append((lo, hi))
        return out

    def moor(self, k: int, spans: list, sheltered: bool) -> None:
        """Groups of fishing boats moored bow- or stern-to, and trawlers alongside, along the quay."""
        cfg = self.cfg
        line = self.port.quays[k].line
        rng = self.rng("quay", k)
        kinds = [str(o[0]) for o in cfg["fishing"]]
        odds = np.cumsum([float(o[1]) for o in cfg["fishing"]])
        odds /= odds[-1]
        gap, side = float(cfg["gap"]), float(cfg["side_gap"])
        crates = self.rng("quay", k, "crates")
        for s0, s1 in self._straights(line, spans):
            s = s0 + rng.uniform(0.0, 4.0)
            while s < s1:
                u = rng.random(4)
                if u[0] < float(cfg["empty"][0]) or (not sheltered and u[1] < float(cfg["open_quay"])):
                    s += float(cfg["empty"][1]) + u[2] * (float(cfg["empty"][2]) - float(cfg["empty"][1]))
                    continue
                if u[3] < float(cfg["trawler"]):
                    s = self._alongside(line, s, s1, rng, gap)
                else:
                    start = s
                    s = self._row(line, s, s1, rng, kinds, odds, gap, side)
                    self._fish_crates(line, start, s, crates)
                s += float(rng.uniform(*cfg["group_gap"]))

    def _alongside(self, line, s: float, s1: float, rng, gap: float) -> float:
        kind = "boat_trawler"
        scale = self.scale(kind, rng.random())
        length, width = (float(v) * scale for v in self.size(kind))
        bow = 1.0 if rng.random() < 0.5 else -1.0
        if s + length > s1:
            return s1
        p, t, n = self._frame(line, s + length / 2)
        c = p + n * (gap + width / 2)
        self._boat(kind, c[0], c[1], math.atan2(bow * t[1], bow * t[0]), scale, gap)
        return s + length

    def _row(self, line, s: float, s1: float, rng, kinds, odds, gap: float, side: float) -> float:
        count = int(rng.integers(int(self.cfg["row"][0]), int(self.cfg["row"][1]) + 1))
        toward = 1.0 if rng.random() < 0.5 else -1.0         # bow-to (+1) or stern-to (-1)
        for _ in range(count):
            kind = kinds[int(np.searchsorted(odds, rng.random(), side="right"))]
            scale = self.scale(kind, rng.random())
            length, width = (float(v) * scale for v in self.size(kind))
            if s + width > s1:
                return s1
            p, t, n = self._frame(line, s + width / 2)
            c = p + n * (gap + length / 2)
            self._boat(kind, c[0], c[1], math.atan2(-toward * n[1], -toward * n[0]), scale, min(gap, side))
            s += width + side
        return s

    def _fish_crates(self, line, s0: float, s1: float, rng) -> None:
        """Now and then a stack of fish crates on the quay behind a row of boats, clear of the bollards."""
        u = rng.random(3)
        if u[0] >= float(self.cfg["fish_crates"]) or s1 - s0 < 4.0:
            return
        kind = "cargo_crates"
        p, t, n = self._frame(line, s0 + (s1 - s0) * (0.2 + 0.6 * u[1]))
        c = p - n * (float(self.cfg["fish_crates_inset"]) + float(self.size(kind)[1]) / 2)
        prop = Prop(kind, round(float(c[0]), 3), round(float(c[1]), 3),
                    round(math.atan2(t[1], t[0]) + (math.pi if u[2] < 0.5 else 0.0), 5), 1.0, "quay")
        poly = box(prop, self.size(kind))
        q = self.port.apron.buffer(-0.5)
        if q.contains(poly) and self._free(poly, 1.0) and not self._near_built(poly, float(self.cfg["street_clear"])):
            self._add(prop, poly)

    # --- the commercial quay ------------------------------------------------------------------------
    def commercial(self, k: int, q, spans: list) -> None:
        """Rails and portal cranes along the quay edge, a cargo yard behind them, a trawler or two alongside."""
        cfg = self.cfg
        rng = self.rng("commercial", k)
        line = q.line
        w, g = (float(v) for v in self.size("crane"))
        inset = float(cfg["crane_inset"]) + (g - 1.0) / 2         # rail gauge is the envelope less the bogies
        step = float(self.size("crane_rails")[0])
        apron = q.apron.buffer(-0.5)
        for s0, s1 in self._straights(line, spans):
            n_rails = int((s1 - s0) // step)
            start = s0 + ((s1 - s0) - n_rails * step) / 2
            rails = []
            for i in range(n_rails):
                p, t, n = self._frame(line, start + (i + 0.5) * step)
                c = p - n * inset
                rails.append(Prop("crane_rails", round(float(c[0]), 3), round(float(c[1]), 3),
                                  round(math.atan2(-t[1], -t[0]), 5), 1.0, "quay"))
            rails = [r for r in rails if apron.contains(box(r, self.size("crane_rails")))]
            for r in rails:
                self.props.append(r)
            if not rails:
                continue
            self._cranes(line, rails, rng, inset, w, g, apron)
            self._yard(line, s0, s1, rng, apron)
        fish = self.rng("commercial", k, "alongside")
        for s0, s1 in self._straights(line, spans):
            s = s0 + float(fish.uniform(10.0, 40.0))
            while s < s1 and fish.random() < 0.7:
                s = self._alongside(line, s, s1, fish, float(cfg["gap"])) + float(fish.uniform(15.0, 60.0))

    def _cranes(self, line, rails: list, rng, inset: float, w: float, g: float, apron) -> None:
        cfg = self.cfg
        count = int(rng.integers(int(cfg["cranes"][0]), int(cfg["cranes"][1]) + 1))
        a, b = line.project(Point(rails[0].x, rails[0].y)), line.project(Point(rails[-1].x, rails[-1].y))
        spacing = (b - a) / max(count, 1)
        space = float(cfg["crane_space"])
        last = -1e9
        for i in range(count):
            s = a + spacing * (i + 0.5) + (rng.random() - 0.5) * spacing * 0.4
            kind = self.crane
            if s - last < space:
                continue
            p, t, n = self._frame(line, s)
            c = p - n * inset
            prop = Prop(kind, round(float(c[0]), 3), round(float(c[1]), 3), round(math.atan2(-t[1], -t[0]), 5),
                        1.0, "quay")
            poly = box(prop, (w, g))
            if apron.contains(poly) and not self._near_built(poly, float(cfg["street_clear"])) \
                    and not self._near_trees(poly, float(cfg["tree_clear"])):
                self._add(prop, poly)
                last = s

    def _yard(self, line, s0: float, s1: float, rng, apron) -> None:
        """Cargo in slots behind the cranes: containers and crates, aisles between them."""
        cfg = self.cfg
        along, across = (float(v) for v in cfg["yard_step"])
        kinds = [str(o[0]) for o in cfg["cargo"]]
        odds = np.cumsum([float(o[1]) for o in cfg["cargo"]])
        odds /= odds[-1]
        depth = float(cfg["yard_inset"])
        clear, trees = float(cfg["street_clear"]), float(cfg["tree_clear"])
        for row in range(4):
            d = depth + row * across
            for s in np.arange(s0 + along / 2, s1 - along / 2, along):
                u = rng.random(4)
                if u[0] > float(cfg["yard_fill"]):
                    continue
                kind = kinds[int(np.searchsorted(odds, u[1], side="right"))]
                p, t, n = self._frame(line, float(s) + (u[2] - 0.5) * 1.2)
                c = p - n * (d + float(self.size(kind)[1]) / 2)
                turn = math.atan2(-t[1], -t[0]) + (math.pi if u[3] < 0.5 else 0.0)
                prop = Prop(kind, round(float(c[0]), 3), round(float(c[1]), 3), round(turn, 5), 1.0, "quay")
                poly = box(prop, self.size(kind))
                if apron.contains(poly) and self._free(poly, 1.5) and not self._near_built(poly, clear) \
                        and not self._near_trees(poly, trees):
                    self._add(prop, poly)

    # --- at anchor and on the beach ----------------------------------------------------------------
    def anchor(self) -> None:
        """A few boats at anchor in each basin, heading into one breeze, clear of the quays and each other."""
        cfg = self.cfg
        quays = unary_union([q.line for q in self.port.quays])
        swing, clear = float(cfg["swing"]), float(cfg["anchor_clear"])
        for n, bw in enumerate(self.port.breakwaters):
            rng = self.rng("anchor", n)
            wind = rng.uniform(0.0, 2 * math.pi)
            want = int(rng.integers(int(cfg["anchored"][0]), int(cfg["anchored"][1]) + 1))
            x0, y0, x1, y1 = bw.basin.bounds
            placed, spots = 0, []
            for _ in range(60):
                u = rng.random(5)
                if placed >= want:
                    break
                x, y = x0 + u[0] * (x1 - x0), y0 + u[1] * (y1 - y0)
                p = Point(x, y)
                if not bw.basin.contains(p) or quays.distance(p) < clear or any(p.distance(o) < swing for o in spots):
                    continue
                kind = "boat_trawler" if u[2] < 0.35 else ("boat_cabin" if u[2] < 0.75 else "boat_lateen")
                if self._boat(kind, x, y, wind + (u[3] - 0.5) * 0.5, self.scale(kind, u[4]), swing / 2):
                    placed += 1
                    spots.append(p)

    def beach(self) -> None:
        """Fishing boats drawn up on the natural beach next to the port, bow to the land, stern by the water."""
        cfg = self.cfg
        port = self.port
        ends = [Point(c) for q in port.quays for c in (q.line.coords[0], q.line.coords[-1])]
        reach = float(cfg["beach_reach"])
        coast = self.plan.land.boundary.intersection(unary_union([e.buffer(reach) for e in ends]))
        coast = coast.difference(port.zone.buffer(5.0))
        pieces = sorted((g for g in getattr(coast, "geoms", [coast]) if g.geom_type == "LineString" and g.length > 20.0),
                        key=lambda g: (round(g.bounds[0], 3), round(g.bounds[1], 3)))
        if not pieces:
            return
        rng = self.rng("beach")
        kinds = [str(o[0]) for o in cfg["beach"]]
        odds = np.cumsum([float(o[1]) for o in cfg["beach"]])
        odds /= odds[-1]
        want = int(rng.integers(int(cfg["beach_boats"][0]), int(cfg["beach_boats"][1]) + 1))
        terrain = self.ctx.world.terrain
        placed = 0
        for piece in pieces:
            s = float(rng.uniform(2.0, 10.0))
            while s < piece.length - 2.0 and placed < want:
                u = rng.random(3)
                kind = kinds[int(np.searchsorted(odds, u[0], side="right"))]
                prop = self._drawn_up(piece, s, kind, self.scale(kind, u[2]), terrain)
                if prop is not None:
                    poly = box(prop, self.size(kind))
                    if self._free(poly, 0.8) and not self._near_built(poly, float(cfg["beach_clear"])) \
                            and not self._near_trees(poly, float(cfg["beach_clear"]) + 1.5):
                        self._add(prop, poly)
                        placed += 1
                s += float(cfg["beach_step"][0]) + u[1] * (float(cfg["beach_step"][1]) - float(cfg["beach_step"][0]))

    def _drawn_up(self, coast: LineString, s: float, kind: str, scale: float, terrain) -> Prop | None:
        """A boat at s along the coast, its stern where the sand stands `stern_sand` m high, bow inland."""
        a, b = coast.interpolate(max(s - 1.0, 0.0)), coast.interpolate(min(s + 1.0, coast.length))
        t = np.array([b.x - a.x, b.y - a.y])
        t /= max(np.linalg.norm(t), 1e-9)
        p = coast.interpolate(s)
        n = np.array([-t[1], t[0]])
        if not self.plan.land.contains(Point(p.x + n[0] * 3.0, p.y + n[1] * 3.0)):
            n = -n                                         # n points inland
        r = np.arange(-40.0, 20.0, 0.5)
        xy = np.array([p.x, p.y]) + r[:, None] * n
        z = terrain.height(xy[:, 0], xy[:, 1])
        above = np.nonzero(z >= float(self.cfg["stern_sand"]))[0]
        if not len(above) or above[0] == 0:
            return None
        length = float(self.size(kind)[0]) * scale
        stern = r[above[0]]
        center = np.array([p.x, p.y]) + n * (stern + length / 2 + 0.2)
        ends = np.array([np.array([p.x, p.y]) + n * (stern + 0.2), np.array([p.x, p.y]) + n * (stern + length + 0.2)])
        if np.any(terrain.height(ends[:, 0], ends[:, 1]) <= 0.05):
            return None
        return Prop(kind, round(float(center[0]), 3), round(float(center[1]), 3), round(math.atan2(n[1], n[0]), 5),
                    round(scale, 4), "beach")
