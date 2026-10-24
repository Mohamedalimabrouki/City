"""Benches, kiosks and fountains (prompt 26): a small per-city "squares" pass, `[dressing.squares]`.

The boulevard's promenade is cut into islands where other streets cross it (the ring road and the
seafront run over its ends in the plan; cross streets over its middle). On each boulevard:
- a round `fountain_colonial` at the head of the island nearest the ring road (else the far end), its
  basin `fountain_margin` m in from the island's end; the planned trees it takes the place of are left
  out (`keeps`, read by `Dresser.tree_spots`, so the tile and the parked cars agree);
- kiosks at a few junctions: on a paved cut corner (`Building.apron`) by the boulevard, else at an
  island's end (moved in up to `kiosk_slide` m to find room), facing the junction;
- then a bench (role `bench`) between each two trees of the middle row where it fits, its back to the
  tree line, facing the walkway on alternate sides.
Near the great mosque (and, by chance, a medina gate) a `sabil` hangs on a wall facing a souk, an alley or
the open square around the mosque: monuments' walls first (nothing is dressed on them), then houses'.

Every choice has its own stream (`rng("fountain", k)`, `rng("bench", k, i)`, `rng("kiosk", k, i)`,
`rng("sabil", landmark)`, `rng("lit", "kiosk", k, i)`); the whole city's list is made once and a tile
keeps the pieces whose anchor it holds. Each piece is checked with its kit bounds (the fountain as a
circle) against what is drawn around it: tree trunks and crowns (after `tree_spots`), street lamps,
zebra crossings, parked cars, arcade bands and every piece of the nearby dressed buildings (doors with
their free zone in front), and must stand on a walk, a paved corner, the promenade or open ground.
"""
from __future__ import annotations

import math

import numpy as np
import shapely
from shapely.geometry import Point
from shapely.strtree import STRtree

from .geo import polygons
from .openings import piece_box, piece_boxes, wall_arrays
from .parking import lying_on, street_frame

MONUMENTS = {"mosque_hall", "mosque_court", "wall", "tower", "marabout"}   # undressed walls a sabil may use
FOOT = ("souk", "alley", "impasse")         # pedestrian lanes: a sabil's basin may stand on them
INF = 1e9


class Squares:
    def __init__(self, dresser):
        from .dressing import DRESSED, Placement, ground_heights, yaw_of   # dressing imports this
        self.DRESSED, self.Placement, self.yaw_of = DRESSED, Placement, yaw_of
        self.ground_heights = ground_heights
        self.d, self.plan = dresser, dresser.plan
        self.cfg = dresser.cfg.get("squares", {})
        self.walk_polys = [w.polygon for w in getattr(self.plan, "walks", ())]
        self.walk_tree = STRtree(self.walk_polys) if self.walk_polys else None
        self.crossings = [m.polygon for m in getattr(self.plan, "paint", ()) if m.kind == "crossing"]
        self.cross_tree = STRtree(self.crossings) if self.crossings else None
        self._islands = None
        self._fountains = None
        self._items = None
        self._area = None
        self._lamps: dict = {}
        self._dressed: dict = {}
        self._crown: dict = {}

    def _streets(self, geom, **kw) -> np.ndarray:
        """`surface_tree.query`, or nothing for a settlement without streets."""
        tree = self.d.surface_tree
        return tree.query(geom, **kw) if tree is not None else np.zeros(0, dtype=int)

    def _buildings(self, geom, **kw) -> np.ndarray:
        """`fp_tree.query`, or nothing for a settlement without buildings."""
        tree = self.d.fp_tree
        return tree.query(geom, **kw) if tree is not None else np.zeros(0, dtype=int)

    def c(self, key: str, default: float) -> float:
        return float(self.cfg.get(key, default))

    # --- public ---------------------------------------------------------------------------------
    def placements(self, tile) -> list:
        """Fresh copies of the furniture whose anchor lies in the tile (x0 <= x < x1, y0 <= y < y1)."""
        if not self.cfg or not self.area().intersects(tile):
            return []
        x0, y0, x1, y1 = tile.bounds
        return [self.Placement(p.piece, p.x, p.y, p.z, p.yaw, p.on_ground) for p in self.items()
                if x0 <= p.x < x1 and y0 <= p.y < y1]

    def keeps(self, xy: np.ndarray) -> np.ndarray:
        """False for planned trees a fountain takes the place of."""
        keep = np.ones(len(xy), dtype=bool)
        for _, p, _, reach in self.fountains():
            keep &= np.hypot(xy[:, 0] - p.x, xy[:, 1] - p.y) > reach
        return keep

    def items(self) -> list:
        if self._items is None:
            fountains = [f[1] for f in self.fountains()]
            kiosks = self._kiosks(fountains)                    # before the benches: a bench gives way
            self._items = fountains + kiosks + self._benches(fountains + kiosks) + self._sabils()
        return self._items

    def area(self):
        """Where furniture may stand: around the islands and the landmarks a sabil may stand by."""
        if self._area is None:
            parts = [part.buffer(self.c("area_reach", 25.0)) for _, part in self.islands()]
            reach = self.c("sabil_reach", 40.0) + self.c("sabil_area_pad", 10.0)
            parts += [Point(lm.x, lm.y).buffer(reach) for lm in self.plan.landmarks if lm.kind in self.cfg.get("sabil", {})]
            self._area = shapely.union_all(parts) if parts else shapely.Polygon()
        return self._area

    # --- islands and fountains ---------------------------------------------------------------------
    def islands(self) -> list:
        """[(boulevard, part)]: the promenade less the surfaces of the streets crossing it (`island_clear` m
        wider), in the order of the boulevard."""
        if self._islands is None:
            self._islands = []
            lines = [st.line for st in self.plan.streets]
            line_tree = STRtree(lines) if lines else None
            clear = self.c("island_clear", 0.6)
            for k, st in enumerate(self.plan.streets):
                proms = [w.polygon for w in self.plan.walks if w.kind == "promenade" and w.street == k]
                if not proms:
                    continue
                prom = shapely.union_all(proms)
                inside = lying_on(k, st.line, self.d.surfaces[k], line_tree, lines, self.d.cfg.get("parking", {}))
                cut = [self.d.surfaces[j] for j in sorted(int(i) for i in self._streets(prom, predicate="intersects"))
                       if j not in inside]
                if cut:
                    prom = prom.difference(shapely.union_all(cut).buffer(clear))
                parts = [p for p in polygons(prom) if p.area > self.c("island_min_area", 4.0)]
                parts.sort(key=lambda p: st.line.project(p.centroid))
                self._islands += [(k, p) for p in parts]
        return self._islands

    def _span(self, k: int, part) -> tuple:
        """(start, end) distances of an island part along its boulevard."""
        line = self.plan.streets[k].line
        d = shapely.line_locate_point(line, shapely.points(shapely.get_coordinates(part.exterior)))
        return float(d.min()), float(d.max())

    def fountains(self) -> list:
        """[(boulevard, placement, basin circle, tree reach)]: at most one fountain per boulevard."""
        if self._fountains is None:
            self._fountains = []
            if self.d.has("fountain_colonial") and self.cfg:
                for k in sorted({k for k, _ in self.islands()}):
                    found = self._fountain(k)
                    if found is not None:
                        self._fountains.append(found)
        return self._fountains

    def _fountain(self, k: int):
        rng = self.d.rng("fountain", k)
        if rng.random() >= self.c("fountain", 1.0):
            return None
        st = self.plan.streets[k]
        name, _ = self.d.pick("fountain_colonial", rng)
        piece = self.d.kit.pieces[name]
        radius = float(max(abs(piece.bounds[0][0]), piece.bounds[1][0]))
        margin = self.c("fountain_margin", 1.0)
        ring = [st2.line for st2 in self.plan.streets if st2.kind == "ring"]
        ends = []
        for _, part in [ip for ip in self.islands() if ip[0] == k]:
            lo, hi = self._span(k, part)
            for d_end, sign in ((lo, 1.0), (hi, -1.0)):
                q = st.line.interpolate(d_end)
                near_ring = min((q.distance(r) for r in ring), default=INF)
                far = min(d_end, st.line.length - d_end)
                ends.append((0 if near_ring < st.width else 1, far, d_end, sign, part))
        for _, _, d_end, sign, part in sorted(ends, key=lambda e: e[:3]):
            d = d_end + sign * (margin + radius)
            p, n = street_frame(st.line, np.array([d]))
            circle = Point(p[0]).buffer(radius, quad_segs=8)
            if not part.contains(circle) or self._crossing(circle, self.c("crossing_clear", 0.6)):
                continue
            near = sorted(int(j) for j in self._streets(circle, predicate="dwithin", distance=self.c("lamp_reach", 3.0)))
            if any(circle.distance(box) < self.c("lamp_clear", 0.3) for j in near for box in self._street_lamps(j)):
                continue
            reach = radius + self.c("fountain_trees", 1.6)
            if self._under_trees(circle, Point(p[0]), reach):
                continue
            return k, self.Placement(name, float(p[0, 0]), float(p[0, 1]), 0.0, self.yaw_of(n[0]), True), circle, reach
        return None

    def _under_trees(self, circle, at, reach: float) -> bool:
        """Does the basin meet a trunk or a crown (the same circles kiosks and benches keep clear of, but in
        plan only: no crown hangs over the water) of a tree the fountain does not replace?"""
        polys: list = []
        self._trees(circle, lambda geoms, z0, z1: polys.extend(geoms), skip=(at, reach))
        return bool(polys) and bool(shapely.intersects(circle, np.array(polys, dtype=object)).any())

    # --- benches ------------------------------------------------------------------------------------
    def _benches(self, placed: list) -> list:
        """A bench between each two trees of the middle row (gap at least `bench_gap` m), its back to the
        tree line, facing the walkway on alternate sides. A bench is keyed and turned by the place of the
        tree before it in the boulevard's middle row (as planned), so leaving a tree out moves no other bench."""
        if not self.d.has("bench") or not self.plan.trees:
            return []
        out = []
        plan_xy = np.array([(t.x, t.y) for t in self.plan.trees])
        xy, kept, _ = self.d.tree_spots(plan_xy)
        for k, part in self.islands():
            line = self.plan.streets[k].line
            on_line = shapely.distance(line, shapely.points(plan_xy)) < 0.5
            row = np.sort(shapely.line_locate_point(line, shapely.points(plan_xy[on_line])))   # the middle row
            here = kept & shapely.contains_xy(part, xy[:, 0], xy[:, 1])
            if here.sum() < 2:
                continue
            d = np.sort(shapely.line_locate_point(line, shapely.points(xy[here])))
            boxes = self._obstacles(part.buffer(1.0), dress=False, extra=placed)
            for m in range(len(d) - 1):
                if d[m + 1] - d[m] < self.c("bench_gap", 6.0):
                    continue
                i = int(np.argmin(np.abs(row - d[m])))
                rng = self.d.rng("bench", k, i)
                if rng.random() >= self.c("bench", 0.85):
                    continue
                name, _ = self.d.pick("bench", rng)
                side = 1.0 if i % 2 == 0 else -1.0
                p, n = street_frame(line, np.array([(d[m] + d[m + 1]) / 2]))
                face = n[0] * side
                at = p[0] + face * self.c("bench_offset", 0.35)
                cand = self.Placement(name, float(at[0]), float(at[1]), 0.0, self.yaw_of(face), True)
                if self._fits(cand, boxes, part):
                    out.append(cand)
        return out

    # --- kiosks -------------------------------------------------------------------------------------
    def _kiosks(self, placed: list) -> list:
        if not self.d.has("kiosk"):
            return []
        out: list = []
        spacing = self.c("kiosk_spacing", 30.0)
        for k in sorted({k for k, _ in self.islands()}):
            count = 0
            for idx, (spots, surface) in enumerate(self._kiosk_spots(k)):
                if count >= int(self.c("kiosks", 3)):
                    break
                rng = self.d.rng("kiosk", k, idx)                 # its own stream: drawing it moves nothing else
                if rng.random() >= self.c("kiosk", 0.7):
                    continue
                name, _ = self.d.pick("kiosk", rng)
                piece = self.d.kit.pieces[name]
                spots = [(at, yaw) for at, yaw in spots(piece)                # plan checks first: no dressing for nothing
                         if surface.contains(piece_box(piece, float(at[0]), float(at[1]), yaw, 0.0)[0])
                         and not any(math.hypot(at[0] - o.x, at[1] - o.y) < spacing for o in out)
                         and not self._in_band(self.Placement(name, float(at[0]), float(at[1]), 0.0, yaw))]
                if not spots:
                    continue
                xy = np.array([at for at, _ in spots])
                zs = np.atleast_1d(self.d.ground.surface(xy[:, 0], xy[:, 1]))
                boxes = self._obstacles(shapely.MultiPoint([tuple(q) for q in xy]).buffer(self.c("kiosk_region", 6.0)),
                                        dress=True, extra=placed + out)
                for (at, yaw), z in zip(spots, zs):
                    foot, z0, z1 = piece_box(piece, float(at[0]), float(at[1]), yaw, float(z))
                    if self._clear(foot, z0, z1, boxes):
                        cand = self.Placement(name, float(at[0]), float(at[1]), 0.0, float(yaw), True)
                        lit = self.d.rng("lit", "kiosk", k, idx).random() < self.c("kiosk_lit", 0.5)
                        if lit and name + "_lit" in self.d.kit.pieces:
                            cand.piece = name + "_lit"
                        out.append(cand)
                        count += 1
                        break
        return out

    def _kiosk_spots(self, k: int) -> list:
        """[(piece -> positions to try in order, where the kiosk must stand)] by boulevard k: its paved cut
        corners, then each island end not taken by the fountain (the kiosk's front, from its kit bounds,
        `kiosk_margin` m in from the end)."""
        st = self.plan.streets[k]
        out = []
        reach = self.c("apron_reach", 1.0)
        surface = self.d.surfaces[k]
        for b in sorted(int(i) for i in self._buildings(surface, predicate="dwithin", distance=reach + 1.0)):
            apron = self.plan.buildings[b].apron
            if apron is None or apron.distance(surface) > reach:
                continue
            for part in polygons(apron):
                if part.area < self.c("apron_min_area", 4.0):
                    continue
                walks = [self.walk_polys[int(i)] for i in self.walk_tree.query(part, predicate="dwithin", distance=0.5)] \
                    if self.walk_tree is not None else []
                ground = shapely.union_all([part] + walks).buffer(0.01)
                x0, y0, x1, y1 = part.bounds
                gx, gy = np.meshgrid(np.arange(x0, x1, 0.5), np.arange(y0, y1, 0.5))
                grid = np.stack([gx.ravel(), gy.ravel()], 1)
                grid = grid[shapely.contains_xy(part, grid[:, 0], grid[:, 1])]
                c = np.array(part.centroid.coords[0])
                grid = grid[np.argsort(np.hypot(*(grid - c).T), kind="stable")][:int(self.c("kiosk_tries", 60))]
                spots = []
                for q in grid:
                    near = np.array(st.line.interpolate(st.line.project(Point(q))).coords[0])
                    f = (near - q) / max(float(np.hypot(*(near - q))), 1e-9)
                    spots.append((q, self.yaw_of(f)))
                out.append((lambda piece, spots=spots: spots, ground))
        taken = [f[2] for f in self.fountains() if f[0] == k]
        for _, part in [ip for ip in self.islands() if ip[0] == k]:
            lo, hi = self._span(k, part)
            for d_end, sign in ((lo, 1.0), (hi, -1.0)):
                end = Point(st.line.interpolate(d_end).coords[0])
                if any(t.distance(end) < self.c("kiosk_fountain_gap", 10.0) for t in taken):
                    continue
                out.append((lambda piece, d_end=d_end, sign=sign, lo=lo, hi=hi: self._end_spots(k, piece, d_end, sign, lo, hi),
                            part))
        return out

    def _end_spots(self, k: int, piece, d_end: float, sign: float, lo: float, hi: float) -> list:
        """Kiosk positions at an island's end, facing it: its front (-z in the kit) `kiosk_margin` m in from
        the end, then sliding in by 0.5 m up to `kiosk_slide` m."""
        front = -float(piece.bounds[0][2])
        ds = d_end + sign * (self.c("kiosk_margin", 0.5) + front + np.arange(0.0, self.c("kiosk_slide", 8.0), 0.5))
        ds = ds[(ds > lo) & (ds < hi)]
        if not len(ds):
            return []
        p, n = street_frame(self.plan.streets[k].line, ds)
        t = np.stack([n[:, 1], -n[:, 0]], 1) * -sign      # along the boulevard, toward this end
        return [(p[m], self.yaw_of(t[m])) for m in range(len(ds))]

    def _in_band(self, cand) -> bool:
        """Does the piece reach into an arcade's band (pillars plus `lamp_clear`, as street lamps keep out)?"""
        a = self.d.arcade_cfg
        if not a:
            return False
        poly = piece_box(self.d.kit.pieces[cand.piece], cand.x, cand.y, cand.yaw, 0.0)[0]
        pts = np.vstack([shapely.get_coordinates(poly), [[cand.x, cand.y]]])
        return bool((self.d._band_push(pts, float(a["depth"]) + float(a["lamp_clear"]))[0] >= 0).any())

    # --- sabils -------------------------------------------------------------------------------------
    def _sabils(self) -> list:
        table = self.cfg.get("sabil", {})
        if not table or not self.d.has("sabil") or not self.plan.streets:   # no street, no square to dress
            return []
        out = []
        medina = self.plan.medina
        for li, lm in enumerate(self.plan.landmarks):
            if lm.kind not in table:
                continue
            if lm.kind == "mosque" and (medina is None or not medina.contains(Point(lm.x, lm.y))):
                continue                                         # the great mosque, not a neighbourhood one
            rng = self.d.rng("sabil", li)
            if rng.random() >= float(table[lm.kind]):
                continue
            spot = self._sabil(lm, rng)
            if spot is not None:
                out.append(spot)
        return out

    def _sabil(self, lm, rng):
        """A sabil on the best wall near a landmark: monuments before houses, a souk before an alley before
        the open square, then nearest; one draw picks among the first few that fit."""
        name, _ = self.d.pick("sabil", rng)
        piece = self.d.kit.pieces[name]
        width, gap = piece.width, self.c("sabil_gap", 0.4)
        face, room = self.c("sabil_face", 6.0), self.c("sabil_front", 1.6)
        steps = np.arange(0.5, face + 1e-9, 0.5)
        here = Point(lm.x, lm.y)
        cands = []
        for b in sorted(int(i) for i in self._buildings(here, predicate="dwithin", distance=self.c("sabil_reach", 40.0))):
            bd = self.plan.buildings[b]
            dressed = bd.kind in self.DRESSED
            if not dressed and bd.kind not in MONUMENTS:
                continue
            a, q, n, length = wall_arrays(bd.footprint)
            for i in np.nonzero(length >= width + 2 * gap)[0].tolist():
                u = (q[i] - a[i]) / length[i]
                s = np.arange(width / 2 + gap, length[i] - width / 2 - gap + 1e-9, 1.0)
                cs = a[i] + u * s[:, None]
                probe = (cs[:, None, :] + n[i] * steps[:, None]).reshape(-1, 2)
                hit = self.d.streets_at(probe).reshape(len(s), len(steps))
                for m in range(len(s)):
                    first = hit[m][hit[m] >= 0]
                    kind = self.plan.streets[int(first[0])].kind if len(first) else "square"
                    rank = {"souk": 0, "alley": 1, "square": 2}.get(kind)
                    if rank is not None:
                        cands.append((int(dressed), rank, float(here.distance(Point(cs[m]))), b, i, cs[m], n[i]))
        cands.sort(key=lambda c: c[:3])
        valid = []
        for dressed, _, _, b, i, c, n in cands:
            cand = self.Placement(name, float(c[0]), float(c[1]), self.d.front_surface(c, n), self.yaw_of(n), False)
            if self._sabil_fits(cand, b, c, n, room, gap):
                valid.append(cand)
                if len(valid) >= int(self.c("sabil_choice", 3)):
                    break
        return valid[int(rng.integers(len(valid)))] if valid else None

    def _sabil_fits(self, cand, b: int, c, n, room: float, gap: float) -> bool:
        piece = self.d.kit.pieces[cand.piece]
        u = np.array([n[1], -n[0]])
        half = piece.width / 2 + gap
        front = shapely.Polygon([c + u * half + n * 0.05, c - u * half + n * 0.05, c - u * half + n * room, c + u * half + n * room])
        if len(self._buildings(front, predicate="intersects")):
            return False                                         # the wall bends or another house stands in front
        foot = piece_box(piece, cand.x, cand.y, cand.yaw, 0.0)[0]
        for j in self._streets(foot, predicate="intersects").tolist():
            if self.plan.streets[int(j)].kind not in FOOT:
                return False                                     # never on a carriageway
        boxes = self._obstacles(front.buffer(3.0), dress=True, props=True)
        grown = piece_box(piece, cand.x, cand.y, cand.yaw, cand.z, grow=gap)
        return self._clear(grown[0], grown[1], grown[2], boxes)

    # --- obstacles ----------------------------------------------------------------------------------
    def _obstacles(self, region, dress: bool, extra: list = (), props: bool = False) -> tuple:
        """(plan shapes, z0, z1) of what is drawn around `region`, each grown by its clearance: trunks and
        crowns, lamps, crossings, parked cars, furniture already placed and, with `dress`, every piece of
        the dressed buildings around (doors with their free zone in front, arcades, shops, cafes); with
        `props`, the street pieces (arches, gates, carts) too."""
        polys, lo, hi = [], [], []

        def add(geoms, z0, z1):
            polys.extend(geoms)
            lo.extend(np.broadcast_to(z0, len(geoms)).tolist())
            hi.extend(np.broadcast_to(z1, len(geoms)).tolist())

        if self.cross_tree is not None:
            clear = self.c("crossing_clear", 0.6)
            hit = sorted(int(i) for i in self.cross_tree.query(region, predicate="dwithin", distance=clear))
            add([self.crossings[i].buffer(clear) for i in hit], -INF, INF)
        streets = sorted(int(i) for i in self._streets(region, predicate="intersects"))
        for j in streets:
            add([box.buffer(self.c("lamp_clear", 0.3)) for box in self._street_lamps(j) if box.intersects(region)], -INF, INF)
        self._trees(region, add)
        cars = []
        if "parking" in self.d.cfg:
            if self.d._parking is None:
                from .parking import Parking
                self.d._parking = Parking(self.d)
            tile = shapely.box(*region.bounds)
            for j in streets:
                cars += self.d._parking.cars(j, tile)
        near = list(extra) + cars
        if props:
            tile = shapely.box(*region.bounds)
            for j in streets:
                near += [p for p in self.d.street_props(j, tile) if p.piece != "street_lamp"]
        if dress:
            near += self._dressed_near(region, add)
        if near:
            near = [self.Placement(p.piece, p.x, p.y, p.z, p.yaw, p.on_ground, p.scale, p.stretch) for p in near]
            self.ground_heights(self.d.ground, near)
            box, z0, z1 = piece_boxes(self.d.kit, near, 0.0)
            add(list(shapely.buffer(box, self.c("piece_clear", 0.2))), z0, z1)
        return np.array(polys, dtype=object), np.array(lo), np.array(hi)

    def _trees(self, region, add, skip=None) -> None:
        """Trunks (`tree_trunk` + `tree_clear`) up to the crown, and crowns above: a circle of `crown_cover`
        times the tree piece's half width (the leaves are a round mass, not their bounding box). `skip`:
        (point, reach), trees with a trunk that close are left out (those a fountain replaces)."""
        index = self.d.tree_index()
        if index is None:
            return
        hit = sorted(int(i) for i in index.query(region, predicate="dwithin", distance=self.c("tree_query", 6.0)))
        if not hit:
            return
        xy = np.array([(self.plan.trees[i].x, self.plan.trees[i].y) for i in hit])
        xy, kept, away = self.d.tree_spots(xy)
        zs = np.atleast_1d(self.d.ground.surface(xy[:, 0], xy[:, 1]))
        trunk = self.c("tree_trunk", 0.3) + self.c("tree_clear", 0.5)
        for m, i in enumerate(hit):
            if not kept[m] or (skip is not None and math.hypot(xy[m, 0] - skip[0].x, xy[m, 1] - skip[0].y) <= skip[1]):
                continue
            t = self.plan.trees[i]
            put = self.d.tree(i, t, float(zs[m]), away[m])
            base = float(zs[m]) + 0.35 * t.height
            if put is not None:
                base = float(zs[m]) + self._crown_base(put.piece) * put.scale
                lo, hi = self.d.kit.pieces[put.piece].bounds
                half = (hi[0] - lo[0] + hi[2] - lo[2]) / 4 * put.scale * self.c("crown_cover", 0.8)
                add([Point(xy[m]).buffer(float(half), quad_segs=4)], base - self.c("crown_pad", 0.1), float(zs[m]) + hi[1] * put.scale)
            add([Point(xy[m]).buffer(trunk, quad_segs=4)], -INF, base)

    def _crown_base(self, name: str) -> float:
        """Height of a tree piece's lowest leaf (unscaled); 0.6 of its top when it has no leaf material."""
        if name not in self._crown:
            pc = self.d.kit.pieces[name]
            leaf = [p["pos"][:, 1].min() for m, p in pc.parts.items() if m.startswith("leaf")]
            self._crown[name] = float(min(leaf)) if leaf else 0.6 * pc.top
        return self._crown[name]

    def _street_lamps(self, j: int) -> list:
        """Plan boxes (kit bounds) of street j's lamps."""
        if j not in self._lamps:
            spacing = self.d.cfg.get("street_lamps", {}).get(self.plan.streets[j].kind)
            out = []
            if spacing and self.d.has("street_lamp"):
                for i in range(int(self.plan.streets[j].line.length // float(spacing))):
                    spot = self.d.lamp_spot(j, i, float(spacing))
                    if spot is not None:
                        name, _ = self.d.pick("street_lamp", self.d.rng("lamp", j, i))
                        out.append(piece_box(self.d.kit.pieces[name], spot[0][0], spot[0][1], self.yaw_of(-spot[1]), 0.0)[0])
            self._lamps[j] = out
        return self._lamps[j]

    def _dressed_near(self, region, add) -> list:
        """The wall pieces of the dressed buildings near the region (`Dresser.wall_pieces`: no roof, no
        lights); doors also add their free zone."""
        depth = float(self.d.open_cfg.get("door_clear", 2.0))
        out = []
        for b in sorted(int(i) for i in self._buildings(region, predicate="dwithin", distance=self.c("dressed_reach", 4.0))):
            if self.plan.buildings[b].kind not in self.DRESSED:
                continue
            if b not in self._dressed:
                self._dressed[b] = self.d.wall_pieces(b)
            for p in self._dressed[b]:
                pc = self.d.kit.pieces.get(p.piece)
                if pc is not None and pc.category == "door":
                    add([piece_box(pc, p.x, p.y, p.yaw, 0.0, depth=depth)[0]], -INF, INF)
            out += self._dressed[b]
        return out

    def _crossing(self, geom, clear: float) -> bool:
        return self.cross_tree is not None and len(self.cross_tree.query(geom, predicate="dwithin", distance=clear)) > 0

    # --- checks -------------------------------------------------------------------------------------
    def _fits(self, cand, boxes: tuple, surface) -> bool:
        """The placed piece stands inside `surface` and clear of every obstacle (in plan and height)."""
        z = float(self.d.ground.surface(cand.x, cand.y))
        foot, z0, z1 = piece_box(self.d.kit.pieces[cand.piece], cand.x, cand.y, cand.yaw, z)
        if not surface.contains(foot):
            return False
        return self._clear(foot, z0, z1, boxes)

    @staticmethod
    def _clear(foot, z0: float, z1: float, boxes: tuple) -> bool:
        polys, lo, hi = boxes
        if not len(polys):
            return True
        near = (lo < z1) & (hi > z0)
        return not (near.any() and shapely.intersects(foot, polys[near]).any())
