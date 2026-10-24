"""Parked cars and the taxi rank (prompt 25), `[dressing.parking]` in the style.

`parked_sides` is a pure rule on the plan, shared by the road paint and the dresser: which sides of a
street have a parking row, from the carriageway left between its sidewalks (`walk_widths`). The paint
(built in the planner) moves an edge line out to the lane side of a parking row and the dresser parks
cars in it, so both must agree. `Parking` lays the cars out for `Dresser.street_props`.
"""
from __future__ import annotations

import numpy as np
import shapely
from shapely.strtree import STRtree

from ..rng import weighted
from .openings import piece_box


PARALLEL_RUN, PARALLEL_DEG = 8.0, 15.0


def street_frame(line, d: np.ndarray) -> tuple:
    """Points on a center line at distances d, and the unit left normals there."""
    p = shapely.get_coordinates(shapely.line_interpolate_point(line, d))
    a = shapely.get_coordinates(shapely.line_interpolate_point(line, np.maximum(d - 0.5, 0.0)))
    b = shapely.get_coordinates(shapely.line_interpolate_point(line, np.minimum(d + 0.5, line.length)))
    t = (b - a) / np.maximum(np.hypot(*(b - a).T), 1e-9)[:, None]
    return p, np.stack([-t[:, 1], t[:, 0]], axis=1)


def walk_extents(st, k: int, d: np.ndarray, side: int, walks: list, walk_tree, surface_tree, design: list,
                 min_carriage: float, inside: set) -> tuple:
    """(width, walk index) of the sidewalk on one side of street k at distances d. A sidewalk is its block
    grown by the district's `sidewalk_width` (`design[district]`) and clipped to the street's side strip,
    which leaves `min_carriage` m of carriageway: so along street k it is min(design, (width - min_carriage)
    / 2) wide, whichever street it is filed under (a sidewalk wraps its block and is filed under one
    street, so its own `street`, `side` and `width` hold for one side only). NaN and -1 where no sidewalk
    lies at the street's edge, or where the surface of a street not `inside` (`lying_on`) is within 1 m
    (a junction)."""
    width, which = np.full(len(d), np.nan), np.full(len(d), -1)
    if walk_tree is None or not len(d):
        return width, which
    p, n = street_frame(st.line, d)
    pts = shapely.points(p + n * side * (st.width / 2 - 0.05))
    cap = max(0.0, (st.width - min_carriage) / 2)
    inp, hit = walk_tree.query(pts, predicate="within")
    for i, h in zip(inp.tolist(), hit.tolist()):
        w = walks[h]
        if w.kind == "sidewalk":
            r = min(design[w.district], cap) if 0 <= w.district < len(design) else w.width
            if not r <= width[i]:
                width[i], which[i] = r, h
    if surface_tree is not None:
        ji, jh = surface_tree.query(pts, predicate="dwithin", distance=1.0)
        meet = np.array([int(j) not in inside for j in jh.tolist()], dtype=bool)
        width[ji[meet]], which[ji[meet]] = np.nan, -1
    return width, which


def lying_on(k: int, line, surface, line_tree, lines: list) -> set:
    """Street k and the streets lying on its surface (grid streets the planner left under a boulevard):
    wholly inside it, or running along inside it for `PARALLEL_RUN` m within `PARALLEL_DEG` degrees of
    its direction. They do not meet it."""
    out = {k}
    for j in sorted(int(i) for i in line_tree.query(surface, predicate="intersects")):
        part = lines[j].intersection(surface)
        if j == k or part.length < 1e-6:
            continue
        if part.length >= lines[j].length - 1e-6:
            out.add(j)
        elif part.length >= PARALLEL_RUN:
            c = shapely.get_coordinates(part)
            v = (c[-1] - c[0]) / max(float(np.hypot(*(c[-1] - c[0]))), 1e-9)
            _, n = street_frame(line, np.array([line.project(shapely.Point((c[0] + c[-1]) / 2))]))
            if abs(v[0] * n[0, 1] - v[1] * n[0, 0]) > np.cos(np.radians(PARALLEL_DEG)):
                out.add(j)
    return out


def street_widths(st, k: int, walks: list, walk_tree, surface_tree, design: list, min_carriage: float,
                  inside: set, step: float = 5.0) -> dict:
    """{(k, side): widest sidewalk along that side of street k, away from junctions} (sampled every `step` m)."""
    d = np.arange(step / 2, st.line.length, step)
    out = {}
    for side in (1, -1):
        w, _ = walk_extents(st, k, d, side, walks, walk_tree, surface_tree, design, min_carriage, inside)
        if np.isfinite(w).any():
            out[(k, side)] = float(np.nanmax(w))
    return out


def design_widths(style: dict, districts) -> list:
    """Each district's designed sidewalk width (`[district.<kind>] sidewalk_width`)."""
    table = style.get("district", {})
    return [float(table.get(dd.kind, {}).get("sidewalk_width", 0.0)) for dd in districts]


def walk_widths(style: dict, districts, streets, walks, kinds=None) -> tuple:
    """({(street, side): widest sidewalk}, {streets with a promenade}) of a whole city (only the streets
    of `kinds`, when given)."""
    widths: dict = {}
    promoted = {w.street for w in walks if w.kind == "promenade" and w.street >= 0}
    if not walks or not streets:
        return widths, promoted
    walk_tree = STRtree([w.polygon for w in walks])
    surfaces = [st.line.buffer(st.width / 2, cap_style="flat") for st in streets]
    lines = [st.line for st in streets]
    surface_tree, line_tree = STRtree(surfaces), STRtree(lines)
    design = design_widths(style, districts)
    min_carriage = float(style.get("streets", {}).get("min_carriageway", 5.5))
    for k, st in enumerate(streets):
        if kinds is not None and st.kind not in kinds:
            continue
        widths.update(street_widths(st, k, walks, walk_tree, surface_tree, design, min_carriage,
                                    lying_on(k, st.line, surfaces[k], line_tree, lines)))
    return widths, promoted


def parked_sides(st, k: int, widths: dict, promoted: set, cfg: dict, promenade: float) -> dict:
    """{side: curb offset} of street k's parking rows; side +1 is left of its line, -1 right, and the
    curb offset is the distance from the center line to the carriageway's edge on that side.

    Both sides when the carriageway takes two rows and two lanes, one side (the wider sidewalk's, the
    left on a tie) when it takes one row and one lane, none below that. On a boulevard each carriageway
    (between its outer curb and the promenade) parks along its outer curb when it takes a row and a lane.
    Only a side with a sidewalk (a curb) parks.
    """
    if not cfg or st.kind not in cfg.get("kinds", ()):
        return {}
    row, lane = float(cfg["row"]), float(cfg["lane"])
    walk = {s: widths[(k, s)] for s in (1, -1) if (k, s) in widths}
    if not walk:
        return {}
    if k in promoted:
        return {s: st.width / 2 - w for s, w in walk.items() if st.width / 2 - w - promenade / 2 >= row + lane}
    carriage = st.width - walk.get(1, 0.0) - walk.get(-1, 0.0)
    if len(walk) == 2 and carriage >= 2 * (row + lane):
        return {s: st.width / 2 - w for s, w in walk.items()}
    if carriage >= row + lane:
        s = max(walk, key=lambda s: (walk[s], s))
        return {s: st.width / 2 - walk[s]}
    return {}


class Parking:
    """Parked cars and the taxi rank of one city, for `Dresser.street_props` (prompt 25).

    A parking row is cut into runs between junctions (`junction_clear` m from any other street). A run
    is laid out whole, car after car from its start, each slot on its own stream
    `rng("park", street, side, run, slot)`, so a tile gets the same cars as its neighbours and keeps
    those whose center it holds. Gaps come from what is drawn: zebra crossings, trees after
    `tree_spots`, street lamps (`lamp_spot` and the piece's kit bounds), door zones and stair paths
    (`Dresser.front_of`, `door_spots`), cafe and shop fronts. Every car is checked against them with its
    kit bounds, then set on the drawn surface under its axles and pitched along the street (`tilt`).
    """

    STEP = 0.5          # meters between the samples a run is laid out on

    def __init__(self, dresser):
        from .dressing import CAFES, DRESSED, Placement, yaw_of     # here: dressing imports this module
        self.CAFES, self.DRESSED, self.Placement, self.yaw_of = CAFES, DRESSED, Placement, yaw_of
        self.d, plan = dresser, dresser.plan
        self.cfg = dresser.cfg["parking"]
        style = dresser.world.style
        self.promenade = float(style.get("streets", {}).get("promenade_width", 8.0))
        self.min_carriage = float(style.get("streets", {}).get("min_carriageway", 5.5))
        self.design = design_widths(style, plan.districts)
        self.walks = list(plan.walks)
        self.walk_tree = STRtree([w.polygon for w in self.walks]) if self.walks else None
        self.promoted = {w.street for w in self.walks if w.kind == "promenade" and w.street >= 0}
        self.lines = [m.polygon for m in plan.paint if m.kind != "crossing"]
        self.line_tree = STRtree(self.lines) if self.lines else None
        self.crossings = [m.polygon for m in plan.paint if m.kind == "crossing"]
        self.cross_tree = STRtree(self.crossings) if self.crossings else None
        kit = dresser.kit
        self.models = {kind: [f"car_{kind}_{i}" for i in range(16) if f"car_{kind}_{i}" in kit.pieces]
                       for kind, _ in self.cfg["mix"]}
        self.mix = [(kind, w) for kind, w in self.cfg["mix"] if self.models[kind]]
        self.allowed = set(self.cfg["districts"])
        self._sides: dict = {}
        self._runs: dict = {}
        self._rows: dict = {}
        self._rank = False
        self._inside: dict = {}
        self._frees: dict = {}
        self._own: dict = {}                 # street -> its surface, prepared
        self._lamp_boxes: dict = {}          # street -> plan boxes of its lamps
        self._facing: dict = {}              # apartment block -> its nearest street
        self._line_tree = None

    # --- public ---------------------------------------------------------------------------------
    def cars(self, k: int, tile) -> list:
        """The parked cars of street k whose centers lie in the tile (x0 <= x < x1, y0 <= y < y1)."""
        if not self.mix:
            return []
        x0, y0, x1, y1 = tile.bounds
        out = []
        for side in self.sides(k):
            for j, run in enumerate(self.runs(k, side)):
                bx = run[2]
                if bx[0] > x1 + 3.0 or bx[2] < x0 - 3.0 or bx[1] > y1 + 3.0 or bx[3] < y0 - 3.0:
                    continue
                for p in self.row(k, side, j):
                    if x0 <= p.x < x1 and y0 <= p.y < y1:
                        out.append(self.Placement(p.piece, p.x, p.y, p.z, p.yaw, False, tilt=p.tilt))
        return out

    def sides(self, k: int) -> dict:
        if k not in self._sides:
            st = self.d.plan.streets[k]
            widths = (street_widths(st, k, self.walks, self.walk_tree, self.d.surface_tree, self.design,
                                    self.min_carriage, self.inside(k))
                      if self.walk_tree is not None and st.kind in self.cfg["kinds"] else {})   # as the paint measures
            self._sides[k] = parked_sides(st, k, widths, self.promoted, self.cfg, self.promenade)
        return self._sides[k]

    # --- geometry along a street ----------------------------------------------------------------
    def runs(self, k: int, side: int) -> list:
        """[(start, end, bounding box of the row)] along street k between junctions, on one side."""
        key = (k, side)
        if key not in self._runs:
            self._runs[key] = self._find_runs(k, side)
        return self._runs[key]

    def _find_runs(self, k: int, side: int) -> list:
        st = self.d.plan.streets[k]
        curb = self.sides(k)[side]
        d = np.arange(0.0, st.line.length + 1e-9, 2 * self.STEP)
        p, n = street_frame(st.line, d)
        n = n * side
        pts = np.concatenate([p + n * (curb - off) for off in (0.0, float(self.cfg["row"]))])
        inp, hit = self.d.surface_tree.query(shapely.points(pts), predicate="dwithin",
                                             distance=float(self.cfg["junction_clear"]))
        bad = np.zeros(len(pts), dtype=bool)
        bad[inp[self._crossing_streets(k, hit)]] = True
        bad = bad.reshape(2, -1).any(axis=0)
        out, i = [], 0
        while i < len(d):
            if bad[i]:
                i += 1
                continue
            j = i
            while j + 1 < len(d) and not bad[j + 1]:
                j += 1
            if d[j] - d[i] >= 3.5:
                q = pts.reshape(2, -1, 2)[:, i:j + 1].reshape(-1, 2)
                out.append((float(d[i]), float(d[j]), (*q.min(axis=0), *q.max(axis=0))))
            i = j + 1
        return out

    def inside(self, k: int) -> set:
        """`lying_on` for street k (kept)."""
        if k not in self._inside:
            if self._line_tree is None:
                self._line_tree = STRtree([st.line for st in self.d.plan.streets])
            lines = [st.line for st in self.d.plan.streets]
            self._inside[k] = lying_on(k, lines[k], self.d.surfaces[k], self._line_tree, lines)
        return self._inside[k]

    def _crossing_streets(self, k: int, hit: np.ndarray) -> np.ndarray:
        """True for the streets in `hit` that meet street k (not k, nor a street lying on it)."""
        inside = self.inside(k)
        return np.array([int(j) not in inside for j in np.asarray(hit).tolist()], dtype=bool)

    # --- one run --------------------------------------------------------------------------------
    def row(self, k: int, side: int, j: int) -> list:
        key = (k, side, j)
        if key not in self._rows:
            self._rows[key] = self._lay_out(k, side, j)
        return self._rows[key]

    def _lay_out(self, k: int, side: int, j: int) -> list:
        """The cars of run j, car after car with gaps; the taxi rank first when it lies in this run."""
        d, free, curb, zones = self._free(k, side, j)
        cars: list = []
        boxes: list = []
        rank = self.rank()
        if rank is not None and rank[:3] == (k, side, j):
            self._place_rank(k, side, d, free, curb, zones, rank[3], cars, boxes)
        self._march(k, side, j, d, free, curb, zones, float(d[0]), cars, boxes)
        self._heights(cars)
        return cars

    def _free(self, k: int, side: int, j: int) -> tuple:
        """(sample distances, free samples, curb offsets) of run j: a sample is free where the curb belongs
        to an allowed district and a car there keeps clear of every obstacle (one sample of margin)."""
        if (k, side, j) not in self._frees:
            self._frees[(k, side, j)] = self._find_free(k, side, j)
        return self._frees[(k, side, j)]

    def _find_free(self, k: int, side: int, j: int) -> tuple:
        lo, hi, _ = self.runs(k, side)[j]
        d = np.arange(lo, hi + 1e-9, self.STEP)
        p, n = street_frame(self.d.plan.streets[k].line, d)
        n = n * side
        curb = self._curbs(k, side, d)
        gap = float(self.cfg["curb_gap"])
        geoms, clear = self._zones(k, side, j, p, n, curb)
        free = np.isfinite(curb)
        if geoms:
            tree = STRtree(geoms)                          # samples first; each car is checked exactly later
            for off in (0.05, 0.7, 1.4, 2.1):              # across the row, from the curb side out
                q = p + n * (np.where(free, curb, 0.0) - gap - off)[:, None]
                inp, hit = tree.query(shapely.points(q), predicate="dwithin", distance=float(clear.max()))
                if len(inp):
                    dist = shapely.distance(shapely.points(q[inp]), np.asarray(geoms, dtype=object)[hit])
                    free[inp[dist < clear[hit]]] = False
        zones = (STRtree(geoms), np.asarray(geoms, dtype=object), clear) if geoms else None
        return d, free, curb, zones

    def _curbs(self, k: int, side: int, d: np.ndarray) -> np.ndarray:
        """Distance from the center line to the curb at each sample (where the local sidewalk begins), inf
        where the side has no sidewalk, at a junction, or where its block is not in a parking district."""
        st = self.d.plan.streets[k]
        width, which = walk_extents(st, k, d, side, self.walks, self.walk_tree, self.d.surface_tree, self.design,
                                    self.min_carriage, self.inside(k))
        kinds = self.d.kinds
        ok = np.array([h >= 0 and 0 <= self.walks[h].district < len(kinds) and kinds[self.walks[h].district] in self.allowed
                       for h in which.tolist()], dtype=bool)
        return np.where(ok, st.width / 2 - np.nan_to_num(width), np.inf)

    def _zones(self, k: int, side: int, j: int, p: np.ndarray, n: np.ndarray, curb: np.ndarray) -> tuple:
        """(geometries, clearances) a parked car keeps away from along run j."""
        cfg, d = self.cfg, self.d
        ok = np.isfinite(curb)
        if not ok.any():
            return [], np.zeros(0)
        c = np.where(ok, curb, np.nanmin(np.where(ok, curb, np.nan)))
        mid = shapely.linestrings(p + n * (c - float(cfg["row"]) / 2)[:, None])
        strip = shapely.buffer(mid, float(cfg["row"]) / 2 + 0.5)
        row = shapely.buffer(mid, float(cfg["row"]) / 2, cap_style="flat")
        geoms, clear = [], []

        def add(items, distance: float) -> None:
            geoms.extend(items)
            clear.extend([distance] * len(items))

        if self.cross_tree is not None:
            hit = self.cross_tree.query(strip, predicate="dwithin", distance=float(cfg["crossing_clear"]))
            add([self.crossings[int(i)] for i in sorted(hit.tolist())], float(cfg["crossing_clear"]))
        add(self._trees(strip), float(cfg["tree_clear"]) + float(cfg["tree_trunk"]))   # to the trunk's bark
        add(self._lamps(k, strip), float(cfg["lamp_clear"]))
        doors, paths, fronts = self._doors(k, strip, row)
        add(doors, float(cfg["door_clear"]))
        add(paths, float(cfg["path_clear"]) + float(d.path_cfg.get("width", 1.4)) / 2)
        add(fronts, 0.0)
        return geoms, np.array(clear)

    def _trees(self, strip) -> list:
        """Trunk points of the planned trees near the strip, where the tile draws them (`tree_spots`)."""
        index = self.d.tree_index()
        if index is None:
            return []
        hit = sorted(index.query(strip, predicate="dwithin", distance=6.0).tolist())
        if not hit:
            return []
        xy = np.array([(self.d.plan.trees[i].x, self.d.plan.trees[i].y) for i in hit])
        xy, kept, _ = self.d.tree_spots(xy)
        return list(shapely.points(xy[kept]))

    def _lamps(self, k: int, strip) -> list:
        """Plan boxes (kit bounds) of street k's lamps near the strip."""
        if k not in self._lamp_boxes:
            self._lamp_boxes[k] = self._street_lamps(k)
        return [box for box in self._lamp_boxes[k] if strip.distance(box) <= 3.0]

    def _street_lamps(self, k: int) -> list:
        spacing = self.d.cfg.get("street_lamps", {}).get(self.d.plan.streets[k].kind)
        if not spacing or not self.d.has("street_lamp"):
            return []
        out = []
        for i in range(int(self.d.plan.streets[k].line.length // float(spacing))):
            spot = self.d.lamp_spot(k, i, float(spacing))
            if spot is not None:
                name, _ = self.d.pick("street_lamp", self.d.rng("lamp", k, i))
                out.append(piece_box(self.d.kit.pieces[name], spot[0][0], spot[0][1], self.yaw_of(-spot[1]), 0.0)[0])
        return out

    def _doors(self, k: int, strip, row) -> tuple:
        """(door free zones, stair paths carried on over the sidewalk, cafe and shop front gaps) that could
        reach the row: fronts of the buildings within `door_reach` m, doors of those whose free zone can
        reach the row (narrow sidewalks), and the stair doors of the apartment blocks around that face
        street k (or stand close)."""
        d, cfg = self.d, self.cfg
        depth = float(d.open_cfg.get("door_clear", 2.0))
        cross, half = float(cfg["path_cross"]), float(cfg["front_clear"])
        builds = d.plan.buildings
        doors, paths, fronts = [], [], []
        near = sorted(int(i) for i in d.fp_tree.query(strip, predicate="dwithin", distance=float(cfg["door_reach"])))
        close = {int(i) for i in d.fp_tree.query(row, predicate="dwithin", distance=depth + float(cfg["door_clear"]) + 0.2)}
        reach = float(d.path_cfg.get("reach", 40.0))
        slabs = sorted(int(i) for i in d.fp_tree.query(strip, predicate="dwithin", distance=reach)
                       if d._is_slab(builds[int(i)]))      # the stair doors face the nearest street
        for b in slabs:
            if b not in self._facing:
                self._facing[b] = d._nearest_street(builds[b])[0]
        slabs = [b for b in slabs if b in close or self._facing[b] == k]
        spots: list = []
        for b in near:
            if builds[b].kind not in self.DRESSED or (b not in close and d.kinds[builds[b].district] not in self.CAFES):
                continue
            main, at, kind, piece = d.front_of(b)
            if kind in ("shop", "cafe") and at is not None:
                fronts.append(shapely.Polygon(_rect(np.asarray(at), main.n, half, 15.0)))
            if b in close and not d._is_slab(builds[b]):
                if kind == "front":                       # the street door, exactly where `building` puts it
                    spots.append((at, main.n, piece, None))
                else:
                    spots += [(s.point, s.normal, s.piece, s.path) for s in d.door_spots(b)]
        for b in slabs:
            spots += [(s.point, s.normal, s.piece, s.path) for s in d.door_spots(b)]
        for at, n, piece, path in spots:
            pc = d.kit.pieces.get(piece)
            if pc is not None:
                doors.append(piece_box(pc, float(at[0]), float(at[1]), self.yaw_of(n), 0.0, depth=depth)[0])
            else:
                doors.append(shapely.Polygon(_rect(np.asarray(at), n, 0.6, depth)))
            if path is not None and len(path) >= 2:
                e = path[-1] - path[-2]
                e = e / max(float(np.hypot(*e)), 1e-9)
                paths.append(shapely.LineString(np.vstack([path, path[-1] + e * cross])))
        return doors, paths, fronts

    # --- placing cars ---------------------------------------------------------------------------
    def _car(self, k: int, side: int, d: np.ndarray, free: np.ndarray, curb: np.ndarray, zones, s: float,
             name: str, boxes: list):
        """A car `name` with its rear end at distance s along the run, or None where it does not fit."""
        piece = self.d.kit.pieces[name]
        length, width = float(piece.bounds[1][0] - piece.bounds[0][0]), float(piece.bounds[1][2] - piece.bounds[0][2])
        i0 = int(np.floor((s - d[0]) / self.STEP))
        i1 = int(np.ceil((s + length - d[0]) / self.STEP))
        if i0 < 0 or i1 >= len(d) or not free[i0:i1 + 1].all():
            return None
        c = float(np.min(curb[i0:i1 + 1]))                 # the curb nearest the center line under the car
        p, left = street_frame(self.d.plan.streets[k].line, np.array([s + length / 2]))
        center = p[0] + left[0] * side * (c - float(self.cfg["curb_gap"]) - width / 2)   # cars are symmetric across
        yaw = float(np.arctan2(-left[0, 0], left[0, 1])) + (np.pi if side > 0 else 0.0)   # facing its lane's traffic
        car = self.Placement(name, float(center[0]), float(center[1]), 0.0, yaw, False)
        foot = piece_box(piece, car.x, car.y, yaw, 0.0)[0]
        if zones is not None:                              # trees, lamps, crossings, doors, fronts: exactly
            hit = zones[0].query(foot, predicate="dwithin", distance=float(zones[2].max()))
            if len(hit) and (shapely.distance(foot, zones[1][hit]) < zones[2][hit]).any():
                return None
        return (car, foot) if self._fits(k, foot, boxes) else None

    def _fits(self, k: int, foot, boxes: list) -> bool:
        """Exact checks of a car's plan box: on its own street, off every sidewalk, painted line and other
        car, clear of other streets (junctions)."""
        d = self.d
        if k not in self._own:
            self._own[k] = d.surfaces[k].buffer(1e-6)
            shapely.prepare(self._own[k])
        if not self._own[k].contains(foot):
            return False
        if self.walk_tree is not None and len(self.walk_tree.query(foot, predicate="intersects")):
            return False
        if self.line_tree is not None and len(self.line_tree.query(foot, predicate="intersects")):
            return False
        inp = d.surface_tree.query(foot, predicate="dwithin", distance=float(self.cfg["junction_clear"]) - 0.5)
        if self._crossing_streets(k, inp).any():
            return False
        return not any(foot.intersects(b) for b in boxes)

    def _pick(self, rng) -> str:
        kind = str(weighted(rng, self.mix))
        models = self.models[kind]
        return models[int(rng.integers(len(models)))]

    def _march(self, k, side, j, d, free, curb, zones, start, cars, boxes) -> None:
        """Cars from `start` to the end of the run, each slot on its own stream."""
        cfg = self.cfg
        s, i = start, 0
        while s < d[-1] - 3.5:
            rng = self.d.rng("park", k, side, j, i)
            i += 1
            if rng.random() < float(cfg["empty"].get(self.d.plan.streets[k].kind, 0.0)):
                s += rng.uniform(*cfg["empty_length"])
                continue
            name = self._pick(rng)
            after = rng.uniform(*cfg["gap"])
            got = None
            while got is None and s < d[-1] - 3.5:
                got = self._car(k, side, d, free, curb, zones, s, name, boxes)
                if got is None:
                    s = self._next_free(d, free, s)
            if got is None:
                break
            cars.append(got[0])
            boxes.append(got[1])
            s += self._length(name) + after

    def _next_free(self, d, free, s: float) -> float:
        """The next sample position after s worth trying: one step on, or past the blocked stretch."""
        i = int(np.floor((s - d[0]) / self.STEP)) + 1
        while i < len(d) and not free[i]:
            i += 1
        return float(d[min(i, len(d) - 1)]) if i < len(d) else float(d[-1])

    def _heights(self, cars: list) -> None:
        """Each car stands on the drawn surface under its axles, pitched along the street (`tilt`)."""
        if not cars:
            return
        pts, reach = [], []
        for c in cars:
            a = 0.3 * self._length(c.piece)                 # about half the wheelbase
            u = np.array([np.cos(c.yaw), np.sin(c.yaw)]) * a
            pts += [(c.x + u[0], c.y + u[1]), (c.x - u[0], c.y - u[1])]
            reach.append(a)
        pts = np.array(pts)
        z = np.asarray(self.d.ground.surface(pts[:, 0], pts[:, 1]), dtype=np.float64).reshape(-1, 2)
        for c, (front, back), a in zip(cars, z, reach):
            c.z = float((front + back) / 2)
            c.tilt = float(np.arctan2(front - back, 2 * a))

    # --- the taxi rank ----------------------------------------------------------------------------
    def rank(self):
        """(street, side, run, whether the queue starts at the run's start) of the taxi rank: by the
        boulevard's junction with the most streets, in the nearest parking run (of the boulevard, else of a
        street around, within `rank_reach` m) that holds the whole queue, else the one holding
        most; the queue stands at the run's end nearest the junction. None without a boulevard that parks."""
        if self._rank is False:
            self._rank = self._find_rank()
        return self._rank

    def _find_rank(self):
        d = self.d
        best = None
        for k, st in enumerate(d.plan.streets):
            if st.kind != "boulevard" or not self.sides(k):
                continue
            meets = []
            hits = d.surface_tree.query(st.line, predicate="intersects")
            for jj in sorted(int(i) for i in hits[self._crossing_streets(k, hits)]):
                pts = shapely.get_coordinates(st.line.intersection(d.surfaces[jj]))
                if len(pts):
                    loc = shapely.line_locate_point(st.line, shapely.points(pts))
                    meets.append((float(loc.min()), float(loc.max()), jj))
            for lo, hi, _ in meets:
                near = [jj for a, b, jj in meets if a <= hi + 15.0 and b >= lo - 15.0]
                if best is None or len(near) > len(best[2]):
                    best = (k, (lo + hi) / 2, near)
        if best is None:
            return None
        k, at, _ = best
        junction = shapely.Point(d.plan.streets[k].line.interpolate(at))
        reach = float(self.cfg["rank_reach"])
        around = sorted(int(i) for i in d.surface_tree.query(junction, predicate="dwithin", distance=reach))
        cands = []                                  # parking runs of the boulevard and the streets around
        for street in around:
            line = d.plan.streets[street].line
            for side in sorted(self.sides(street)):
                for j, (a, b, _) in enumerate(self.runs(street, side)):
                    ends = [junction.distance(line.interpolate(x)) for x in (a, b)]
                    if b - a >= 9.0 and min(ends) <= reach:
                        cands.append((min(ends), street != k, street, side, j, ends[0] <= ends[1]))
        best_rank, want = None, int(self.cfg["rank"][0])
        for _, _, street, side, j, after in sorted(cands):   # the nearest run where the whole queue fits
            d_, free, curb, zones = self._free(street, side, j)
            got: list = []
            self._place_rank(street, side, d_, free, curb, zones, after, got, [])
            if best_rank is None or len(got) > best_rank[0]:
                best_rank = (len(got), (street, side, j, after))
            if len(got) >= want:
                break
        return best_rank[1] if best_rank else None

    def _place_rank(self, k, side, d, free, curb, zones, after: bool, cars, boxes) -> None:
        """A short row of yellow taxis at the end of the run nearest the junction (its start when the run
        lies after it), on its own stream; the other cars then fill the rest of the run around them."""
        cfg = self.cfg
        taxis = self.models.get("taxi") or []
        if not taxis:
            return
        rng = self.d.rng("taxi-rank", "row")
        lo, hi = cfg["rank"]
        queue = []
        for _ in range(int(rng.integers(int(lo), int(hi) + 1))):
            name = taxis[int(rng.integers(len(taxis)))]
            queue.append((name, self._length(name), rng.uniform(*cfg["rank_gap"])))
        total = sum(q[1] + q[2] for q in queue)
        s = float(d[0]) if after else max(float(d[0]), float(d[-1]) - total)
        for name, length, gap in queue:
            got = None
            while got is None and s < d[-1] - length:
                got = self._car(k, side, d, free, curb, zones, s, name, boxes)
                if got is None:
                    s = self._next_free(d, free, s)
            if got is None:
                break
            cars.append(got[0])
            boxes.append(got[1])
            s += length + gap

    def _length(self, name: str) -> float:
        b = self.d.kit.pieces[name].bounds
        return float(b[1][0] - b[0][0])


def _rect(at: np.ndarray, n: np.ndarray, half: float, depth: float) -> np.ndarray:
    """Corners of a rectangle on a wall at `at` (outward normal n), `half` m either way along it, `depth` m out."""
    u = np.array([n[1], -n[0]])
    return np.array([at - u * half, at + u * half, at + u * half + n * depth, at - u * half + n * depth])
