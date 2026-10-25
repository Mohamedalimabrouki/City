"""People in the streets (prompt 29): who walks, stands and sits where, `[people]` in the style.

Figures are the kit's `person_*` pieces (prompt 28, mesh/people.py), drawn as instances. Where they go:
- souks: browsers at the shop fronts, beyond the goods and facing them, and walkers in two lanes down the
  middle, keeping to the right; pairs and a few families;
- cafes and benches: customers on the `cafe_set` chairs facing the table (some chairs stay empty), people
  on the promenade benches and on the door benches (doukkana), each seat as `[people.seats]` measures it
  in the kit, the figure's origin under the middle of the seat;
- sidewalks (by the district of the block) and the boulevard's promenade islands: strollers, pairs and
  families (a parent and a child side by side);
- around the great mosque, at the medina gates, at kiosk windows and around fountains; now and then a waiter
  beside a cafe table under a parasol (prompt 37);
- medina lanes and village streets: a few walkers; modern estates: a few by the stair doors, on their paths.
Outfits come from `[people.outfits]` by district kind (cafes have their own mix, children walk or stand
with a parent). Every choice has its own stream: `rng("people", <place>, ...)` per street station, shop,
seat, landmark point or stair door, so leaving one person out moves nobody else.

A tile draws the people whose origin it holds. It checks them against everything drawn around: its own
placements plus a halo (`halo` m) of what neighbouring tiles own (their buildings' wall pieces, street
props, cars, furniture and trees), so a person at a tile edge clears pieces of both tiles. Standing people
keep `clear` m between their kit boxes (members of a pair or family `pair_gap`), `seated_gap` from seated
people; candidates are taken in a fixed order (seats first) and one gives way to any earlier candidate too
close, decided on the candidates alone, so both tiles at an edge agree. Then a person must stand clear of
building footprints, of every piece below head height (a piece's triangles in that height band, so a
person may stand under an arcade or an awning but not in a pillar, a trunk or a lamp post) and on one kind
of floor: a raised walk or paved corner, a pedestrian lane (souk, alley, impasse, medina and village
streets) or open ground, never a carriageway. Standing people stand on what is drawn: a walk's own
triangles, `Ground.surface` on lanes and paved corners, the terrain mesh (`Ground.drawn`) on open ground, a
stair path's top; seated ones on their seat. Each figure a tile shows costs its mesh in the tile, so a light
tile keeps only its most frequent figures (`bytes_share` of its bytes, `_cast`).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

import numpy as np
import shapely
from shapely.geometry import LineString, Point
from shapely.geometry.polygon import orient
from shapely.strtree import STRtree

from ..mesh.builder import triangulate
from .openings import piece_boxes
from .parking import design_widths, lying_on, street_frame, walk_extents

FOOT = ("souk", "alley", "impasse")
GROUND, WALK, LANE, ROAD = 0, 1, 2, 3          # floor kinds
ANY_FLOOR = (GROUND, WALK, LANE)
RANK = {"seat": 0, "square": 1, "shop": 2, "landmark": 3, "stair": 4, "promenade": 5, "seafront": 6, "sidewalk": 7,
        "souk": 8, "lane": 9}                   # who gives way to whom: a later rank to an earlier one

INSTANCE = 40                                   # bytes of one instance in a tile (translation, rotation, scale)
INSTANCE_Q = 20                                 # ... quantized (prompt 39): float translation, 16-bit rotation
PIECE_JSON, PART_JSON = 1000, 800               # about: a piece's node and instance accessors; a part's accessors,
                                                # primitive and material (measured on written tiles)


def piece_bytes(piece, part_json: int = PART_JSON, piece_json: int = PIECE_JSON, quantized: bool = False) -> int:
    """About what a kit piece's mesh adds to a tile that shows it: float positions and normals (16-bit
    positions and 8-bit normals in a quantized tile), UVs and 8-bit colors when it has them, 16-bit
    indices, some JSON per part and per piece."""
    total = piece_json
    for part in piece.parts.values():
        n = len(part["pos"])
        total += n * (12 if quantized else 24) + len(part["idx"]) * (2 if n < 65536 else 4) + part_json
        total += n * 8 if part.get("uv") is not None else 0
        total += n * 4 if part.get("col") is not None else 0
    return total


def tile_bytes(kit, mb, placements: list) -> int:
    """About how big a tile's .glb is: its mesh (a MeshBuilder: float positions and normals, UVs, colors,
    indices), each kit piece it shows once, and its instances. Rather less than more (lit twins share their
    arrays, pieces share materials): people get a share of it."""
    total = sum(n * 32 + t * 3 * (2 if n < 65536 else 4) + 300 + (n * 4 if col else 0) for n, t, col in mb.sizes())
    names = {p.piece for p in placements if p.piece in kit.pieces}
    return total + sum(piece_bytes(kit.pieces[n], 300, 0) for n in sorted(names)) + INSTANCE * len(placements)


@dataclass
class Cand:
    rank: int
    key: tuple
    piece: str
    x: float
    y: float
    yaw: float
    floors: tuple = ANY_FLOOR     # the floor kinds it may stand on (all of its box on one of them)
    group: tuple = ()             # a pair, a family or one seat piece's sitters may be closer
    seat: int = -1                # seated: index of the seat piece in the obstacle list
    seat_z: float = 0.0           # seated: the figure's origin height
    path: object = None           # on a stair path: the path's surface (a Polygon)


def yaw_to(f) -> float:
    """Yaw that turns a piece's front (+y) to face direction f."""
    return math.atan2(-f[0], f[1])


class Crowd:
    def __init__(self, dresser):
        from .dressing import DRESSED, Placement, ground_heights   # dressing imports this module
        self.DRESSED, self.Placement, self.ground_heights = DRESSED, Placement, ground_heights
        self.d, self.plan, self.kit = dresser, dresser.plan, dresser.kit
        style = dresser.world.style
        self.cfg = style["people"]          # every number lives in the style
        self.density = float(self.cfg["density"])
        self.figure_seat = float(style.get("dressing", {}).get("people", {}).get("seat", 0.45))
        self.quantized = bool(dresser.world.cfg["tiles"].get("quantize", False))   # figures cost less (prompt 39)
        self.path_lift = float(dresser.cfg.get("paths", {}).get("lift", 0.04))
        self.path_width = float(dresser.cfg.get("paths", {}).get("width", 1.4))
        self.by: dict = {}                       # (outfit, pose) -> piece names
        for key, spec in (style.get("dressing", {}).get("people", {}).get("pieces") or {}).items():
            name = "person_" + key
            if name in self.kit.pieces:
                self.by.setdefault((key.split("_")[0], str(spec["pose"])), []).append(name)
        self.rect: dict = {}                     # piece -> (x0, x1, y0, y1) of its kit bounds in plan
        self.pose = {n: ("walk" if ps == "carry" else ps, o) for (o, ps), names in self.by.items() for n in names}
        self.env: dict = {}                      # pose -> (x0, x1, y0, y1) holding every piece of that pose
        for n, (ps, _) in sorted(self.pose.items()):
            b = self.bounds(n)
            e = self.env.get(ps, b)
            self.env[ps] = (min(e[0], b[0]), max(e[1], b[1]), min(e[2], b[2]), max(e[3], b[3]))
        plan = self.plan
        self.walks = list(plan.walks)
        self.walk_tree = STRtree([w.polygon for w in self.walks]) if self.walks else None
        floors = [w.polygon for w in self.walks] + [b.apron for b in plan.buildings if b.apron is not None]
        self.floor_tree = STRtree(floors) if floors else None
        medina = plan.medina
        self.shared = np.array([st.kind in FOOT or st.surface == "earth" or (
            st.kind == "street" and medina is not None and medina.contains(st.line.interpolate(0.5, normalized=True)))
            for st in plan.streets], dtype=bool)
        polys = [dd.polygon for dd in plan.districts]
        self.district_tree = STRtree(polys) if polys else None
        self.design = design_widths(style, plan.districts)
        self.min_carriage = float(style.get("streets", {}).get("min_carriageway", 5.5))
        self.lines = [st.line for st in plan.streets]
        self.line_tree = STRtree(self.lines) if self.lines else None
        self._inside: dict = {}
        self._tris: dict = {}                    # piece -> plan triangles and their height ranges
        self._low: dict = {}                     # (piece, band) -> plan shape of its triangles in that band
        self._mosque = None
        self._walk_mesh: dict = {}               # walk -> its drawn triangles (as mesh/tile.walk_meshes drapes them)
        self.walk_step = float(style.get("streets", {}).get("walk_step", 15.0))

    def chance(self, base: float) -> float:
        return min(1.0, float(base) * self.density)

    # --- public ---------------------------------------------------------------------------------
    def people(self, tile, placed: list, centers: np.ndarray, tile_bytes: float | None = None) -> list:
        """The people whose origin lies in the tile (x0 <= x < x1, y0 <= y < y1), as placements with
        absolute heights. `placed`: everything the tile draws, heights already absolute; `centers`: the
        building centers that decide which tile owns a building; `tile_bytes`: about how big the tile is
        without them (`bytes_share` of it is theirs, see `_cast`)."""
        if self.density <= 0.0 or not self.by:
            return []
        x0, y0, x1, y1 = tile.bounds
        h = float(self.cfg["halo"])
        region = shapely.box(x0 - h, y0 - h, x1 + h, y1 + h)
        near = [p for p in placed if p.piece in self.kit.pieces and self.kit.pieces[p.piece].category != "person"]
        near += self._halo(tile, region, centers)
        cands = self._candidates(region, near)
        if not cands:
            return []
        m = float(self.cfg["clear"]) + float(self.cfg["tile_reach"])   # who can reach a person of this tile
        cands = [cd for cd in cands if x0 - m <= cd.x < x1 + m and y0 - m <= cd.y < y1 + m]
        cands = list({(cd.rank, cd.key): cd for cd in sorted(cands, key=lambda cd: (cd.rank, cd.key))}.values())
        alive = self._thin(cands)
        mine = [cd for cd, a in zip(cands, alive) if a and x0 <= cd.x < x1 and y0 <= cd.y < y1]
        budget = None if tile_bytes is None else float(self.cfg["bytes_share"]) * tile_bytes
        return self._place(self._cast(mine, budget), near)

    # --- what the neighbours own ----------------------------------------------------------------
    def _halo(self, tile, region, centers: np.ndarray) -> list:
        """Placements owned by neighbouring tiles within the halo, with absolute heights."""
        d, plan = self.d, self.plan
        x0, y0, x1, y1 = tile.bounds

        def own(x, y) -> bool:
            return x0 <= x < x1 and y0 <= y < y1

        out: list = []
        if d.fp_tree is not None:
            for k in sorted(int(i) for i in d.fp_tree.query(region, predicate="intersects")):
                if plan.buildings[k].kind in self.DRESSED and not own(*centers[k]):
                    out += d.wall_pieces(k)
        ring = region.difference(tile)
        if d.surface_tree is not None:
            for j in sorted(int(i) for i in d.surface_tree.query(ring, predicate="intersects")):
                out += [p for p in d.street_props(j, ring) if not own(p.x, p.y)]
        if "squares" in d.cfg:
            out += [p for p in d.squares().placements(region) if not own(p.x, p.y)]
        out += [p for p in d.seafront().placements(region) if not own(p.x, p.y)]
        if plan.trees and d.tree_index() is not None:
            ks = [int(i) for i in sorted(d.tree_index().query(ring, predicate="intersects"))
                  if not own(plan.trees[int(i)].x, plan.trees[int(i)].y)]
            if ks:
                xy, kept, away = d.tree_spots(np.array([(plan.trees[k].x, plan.trees[k].y) for k in ks]))
                zs = np.atleast_1d(d.ground.surface(xy[:, 0], xy[:, 1]))
                for m, k in enumerate(ks):
                    if kept[m]:
                        t = plan.trees[k]
                        if away[m].any():
                            t = replace(t, x=float(xy[m, 0]), y=float(xy[m, 1]))
                        put = d.tree(k, t, float(zs[m]), away[m])
                        if put is not None:
                            out.append(put)
        out = [p for p in out if p.piece in self.kit.pieces]
        self.ground_heights(d.ground, out)
        return out

    # --- candidates -----------------------------------------------------------------------------
    def _candidates(self, region, near: list) -> list:
        out: list = []
        plan = self.plan
        streets = sorted(int(i) for i in self.d.surface_tree.query(region, predicate="intersects")) \
            if self.d.surface_tree is not None else []
        x0, y0, x1, y1 = region.bounds
        self._box = (x0, y0, x1, y1)
        for k in streets:
            st = plan.streets[k]
            if st.kind == "souk":
                out += self._souk(k)
            elif self.shared[k]:
                out += self._lane(k)
            if self.walk_tree is not None and not self.shared[k]:
                out += self._sidewalk(k)
        out += self._promenade()
        out += self._seafront()
        for idx, p in enumerate(near):
            if not (x0 <= p.x < x1 and y0 <= p.y < y1):
                continue
            pc = self.kit.pieces[p.piece]
            if p.piece in self.cfg["seats"]:
                out += self._seats(idx, p)
            elif p.piece.startswith("shop_front"):
                out += self._shop(p)
            elif pc.category == "kiosk":
                out += self._kiosk(p)
            elif pc.category == "fountain":
                out += self._fountain(p)
            elif pc.category == "parasol":
                out += self._waiter(p)
        out += self._landmarks(region)
        out += self._stairs(region)
        return out

    def _in(self, q) -> bool:
        x0, y0, x1, y1 = self._box
        return x0 <= q[0] < x1 and y0 <= q[1] < y1

    def _kind_at(self, q) -> str:
        if self.district_tree is None:
            return "other"
        hit = sorted(int(i) for i in self.district_tree.query(Point(q), predicate="intersects"))
        return self.d.kinds[hit[0]] if hit else "other"

    def _mix(self, kind: str) -> dict:
        table = self.cfg["outfits"]
        return table.get(kind, table.get("other", {"shirt": 1.0}))

    def _figure(self, rng, mix: dict, pose: str, carry: float = 0.0) -> str | None:
        """A piece for one person: outfit by the mix, then the pose (walkers sometimes carry something)."""
        r_out, r_pose, r_piece = rng.random(), rng.random(), rng.random()
        for ps in (("carry", pose) if pose == "walk" and r_pose < carry else (pose,)):
            options = [(o, float(w)) for o, w in mix.items() if float(w) > 0 and (o, ps) in self.by]
            if options:
                odds = np.cumsum([w for _, w in options])
                o = options[min(int(np.searchsorted(odds / odds[-1], r_out, side="right")), len(options) - 1)][0]
                names = self.by[(o, ps)]
                return names[min(int(r_piece * len(names)), len(names) - 1)]
        return None

    def bounds(self, name: str) -> tuple:
        """(x0, x1, y0, y1) of a piece's kit bounds in plan: x to its right, y to its front."""
        if name not in self.rect:
            lo, hi = self.kit.pieces[name].bounds
            self.rect[name] = (float(lo[0]), float(hi[0]), float(-hi[2]), float(-lo[2]))
        return self.rect[name]

    def _group(self, rng, rank: str, key: tuple, c, heading, mix: dict, pose: str, carry: float, cfg: dict,
               floors: tuple, path=None) -> list:
        """One walker or stander at c facing `heading`, or a pair, or a parent and a child, side by side."""
        r = rng.random()
        pair, family = r < self.chance(cfg.get("pair", 0.0)), False
        if not pair:
            family = r < self.chance(cfg.get("pair", 0.0)) + self.chance(cfg.get("family", 0.0))
        h = np.asarray(heading, dtype=float) / max(float(np.hypot(*heading)), 1e-9)
        yaw = yaw_to(h) + rng.uniform(-1.0, 1.0) * float(self.cfg["jitter"])
        first = self._figure(rng, mix, pose, carry)
        if first is None:
            return []
        if not (pair or family):
            return [Cand(RANK[rank], key, first, float(c[0]), float(c[1]), yaw, floors, path=path)]
        second = self._figure(rng, self.cfg["outfits"].get("children", {"boy": 1.0, "girl": 1.0}) if family else mix,
                              pose, 0.0 if family else carry)
        if second is None:
            return [Cand(RANK[rank], key, first, float(c[0]), float(c[1]), yaw, floors, path=path)]
        right = np.array([math.cos(yaw), math.sin(yaw)])
        gap = float(self.cfg["pair_gap"])
        a, b = self.env[self.pose[first][0]], self.env[self.pose[second][0]]   # room for any piece of the pose
        if rng.random() < 0.5:                       # the child (or the second) on either side
            pa, pb = c - right * (a[1] + gap / 2), c + right * (gap / 2 - b[0])
        else:
            pa, pb = c + right * (gap / 2 - a[0]), c - right * (b[1] + gap / 2)
        grp = (RANK[rank],) + key
        return [Cand(RANK[rank], key + (0,), first, float(pa[0]), float(pa[1]), yaw, floors, grp, path=path),
                Cand(RANK[rank], key + (1,), second, float(pb[0]), float(pb[1]), yaw, floors, grp, path=path)]

    def _stations(self, line, step: float, start: float = 0.0, end: float = 0.0) -> tuple:
        """Indices, points, left normals and tangents every `step` m along a line (station i at (i + 0.5) step)."""
        n_st = int(line.length // step)
        i = np.arange(n_st)
        d = (i + 0.5) * step
        ok = (d >= start) & (d <= line.length - end)
        i, d = i[ok], d[ok]
        if not len(d):
            return i, np.zeros((0, 2)), np.zeros((0, 2)), np.zeros((0, 2))
        p, n = street_frame(line, d)
        t = np.stack([n[:, 1], -n[:, 0]], 1)
        return i, p, n, t

    def _souk(self, k: int) -> list:
        """Walkers in two lanes down a souk, each keeping to its right; lanes staggered by half a step."""
        cfg = self.cfg["souk"]
        st = self.plan.streets[k]
        step = float(cfg["step"])
        mix = self._mix("medina")
        out = []
        for li, lane in enumerate((1.0, -1.0)):
            line = st.line
            i, p, n, t = self._stations(line, step, 3.0, 3.0)
            shift = step / 2 if li else 0.0
            for m in range(len(i)):
                rng = self.d.rng("people", "souk", k, int(i[m]), li)
                if rng.random() >= self.chance(cfg["chance"]):
                    continue
                head = -lane if rng.random() >= float(self.cfg["flip"]) else lane     # n is to the left of t
                off = lane * float(cfg["lane"]) + rng.uniform(-1.0, 1.0) * float(cfg["spread"])
                c = p[m] + n[m] * off + t[m] * (shift + rng.uniform(-0.3, 0.3) * step)
                if self._in(c):
                    out += self._group(rng, "souk", (k, int(i[m]), li), c, t[m] * head, mix, "walk",
                                       float(cfg["carry"]), cfg, (LANE,))
        return out

    def _lane(self, k: int) -> list:
        """A few walkers in a medina lane or a village street."""
        cfg = self.cfg["lane"]
        st = self.plan.streets[k]
        i, p, n, t = self._stations(st.line, float(cfg["step"]), 1.0, 1.0)
        out = []
        kind = None
        for m in range(len(i)):
            if not self._in(p[m]):
                continue
            kind = kind or self._kind_at(p[m])
            rng = self.d.rng("people", "lane", k, int(i[m]))
            if rng.random() >= self.chance(cfg["chance"].get(kind, cfg["chance"].get("other", 0.0))):
                continue
            off = rng.uniform(-1.0, 1.0) * max(0.0, st.width / 2 - 0.7)
            head = 1.0 if rng.random() < 0.5 else -1.0
            out += self._group(rng, "lane", (k, int(i[m])), p[m] + n[m] * off, t[m] * head, self._mix(kind),
                               "walk", float(cfg["carry"]), cfg, (LANE,))
        return out

    def inside(self, k: int) -> set:
        if k not in self._inside:
            self._inside[k] = lying_on(k, self.lines[k], self.d.surfaces[k], self.line_tree, self.lines,
                                       self.d.cfg.get("parking", {}))
        return self._inside[k]

    def _sidewalk(self, k: int) -> list:
        """Strollers, pairs and families along both sidewalks of a street, by the district behind them."""
        cfg = self.cfg["sidewalk"]
        st = self.plan.streets[k]
        step = float(cfg["step"])
        i, p, n, t = self._stations(st.line, step)
        keep = np.array([self._in(q) for q in p], dtype=bool) if len(p) else np.zeros(0, dtype=bool)
        if not keep.any():
            return []
        i, p, n, t = i[keep], p[keep], n[keep], t[keep]
        d = (i + 0.5) * step
        out = []
        for si, side in enumerate((1, -1)):
            w, which = walk_extents(st, k, d, side, self.walks, self.walk_tree, self.d.surface_tree, self.design,
                                    self.min_carriage, self.inside(k))
            for m in range(len(i)):
                if which[m] < 0 or not np.isfinite(w[m]):
                    continue
                dist = self.walks[int(which[m])].district
                kind = self.d.kinds[dist] if 0 <= dist < len(self.d.kinds) else "other"
                rng = self.d.rng("people", "walk", k, si, int(i[m]))
                if rng.random() >= self.chance(cfg["chance"].get(kind, 0.0)):
                    continue
                spread = max(0.0, float(w[m]) / 2 - float(cfg["edge"]))
                off = st.width / 2 - float(w[m]) / 2 + rng.uniform(-1.0, 1.0) * spread
                c = p[m] + n[m] * side * off + t[m] * rng.uniform(-0.35, 0.35) * step
                head = 1.0 if rng.random() < 0.5 else -1.0
                out += self._group(rng, "sidewalk", (k, si, int(i[m])), c, t[m] * head, self._mix(kind), "walk",
                                   float(cfg["carry"]), cfg, (WALK,))
        return out

    def _promenade(self) -> list:
        """Strollers on the boulevard's promenade islands, on both sides of the tree row."""
        if "squares" not in self.d.cfg:
            return []
        cfg = self.cfg["promenade"]
        x0, y0, x1, y1 = self._box
        out = []
        islands = [(k, part) for k, part in self.d.squares().islands()
                   if part.intersects(shapely.box(x0, y0, x1, y1))]
        for k in sorted({k for k, _ in islands}):
            parts = [part for kk, part in islands if kk == k]
            line = self.plan.streets[k].line
            i, p, n, t = self._stations(line, float(cfg["step"]))
            lo, hi = cfg["offset"]
            for si, side in enumerate((1, -1)):
                for m in range(len(i)):
                    if not self._in(p[m]):
                        continue
                    rng = self.d.rng("people", "promenade", k, si, int(i[m]))
                    if rng.random() >= self.chance(cfg["chance"]):
                        continue
                    c = p[m] + n[m] * side * rng.uniform(float(lo), float(hi)) + t[m] * rng.uniform(-1.5, 1.5)
                    if not any(part.contains(Point(c)) for part in parts):
                        continue
                    head = 1.0 if rng.random() < 0.5 else -1.0
                    out += self._group(rng, "promenade", (k, si, int(i[m])), c, t[m] * head,
                                       self._mix(self._kind_at(c)), "walk", float(cfg["carry"]), cfg, (WALK,))
        return out

    def _seafront(self) -> list:
        """Strollers on the corniche's seafront promenade (prompt 36): every `step` m, anywhere across the free
        band between the palm row and the benches along the railing."""
        fronts = getattr(self.plan, "fronts", ())
        cfg_f = self.d.world.style.get("corniche", {})
        if not fronts or not cfg_f:
            return []
        cfg = self.cfg["seafront"]
        x0, y0, x1, y1 = self._box
        box = shapely.box(x0, y0, x1, y1)
        near = box.buffer(16.0)
        out = []
        for fi, f in enumerate(fronts):
            if not f.sea.intersects(near):
                continue
            st = self.plan.streets[f.street]
            curb = st.width / 2.0 - float(cfg_f["curb"])
            lo = curb + float(cfg_f["palm_inset"]) + 0.9
            i, p, n, t = self._stations(st.line, float(cfg["step"]), f.span[0] + 1.0, st.line.length - f.span[1] + 1.0)
            if not len(i):
                continue
            far = shapely.distance(f.sea, shapely.points(p)) - 0.5           # from the line to the sea edge, less a margin
            hi = np.minimum(far, curb + float(cfg_f["width"]) + 2.0) - float(cfg_f["bench_back"]) - 0.75
            for m in range(len(i)):
                if not near.contains(Point(p[m])):            # the farthest stroller stands about 13 m off the line
                    continue
                rng = self.d.rng("people", "seafront", f.street, fi, int(i[m]))
                if rng.random() >= self.chance(cfg["chance"]) or hi[m] <= lo:
                    continue
                c = p[m] + n[m] * f.side * rng.uniform(lo, float(hi[m])) + t[m] * rng.uniform(-1.5, 1.5)
                if not self._in(c):
                    continue
                head = 1.0 if rng.random() < 0.5 else -1.0
                out += self._group(rng, "seafront", (f.street, fi, int(i[m])), c, t[m] * head,
                                   self._mix(self._kind_at(p[m] - n[m] * f.side * (st.width / 2.0 + 8.0))), "walk",
                                   float(cfg["carry"]), cfg, (WALK,))
        return out

    @staticmethod
    def _pos_key(p) -> tuple:
        return (int(round(p.x * 100)), int(round(p.y * 100)))

    def _seats(self, idx: int, p) -> list:
        """People on a seat piece's seats (`[people.seats]`): cafe customers face the table, turned a little
        the same way so their feet pass; benches face their front."""
        spec = self.cfg["seats"][p.piece]
        key = self._pos_key(p)
        rng = self.d.rng("people", "seat", *key)
        turn = math.radians(rng.uniform(*spec.get("turn", [0.0, 0.0]))) * (1.0 if rng.random() < 0.5 else -1.0)
        mix = self.cfg["outfits"].get(spec["mix"]) if "mix" in spec else None
        c, s = math.cos(p.yaw), math.sin(p.yaw)
        out = []
        for j, (sx, sy, face) in enumerate(spec["seats"]):
            r = self.d.rng("people", "seat", *key, j)
            if r.random() >= self.chance(spec["chance"]):
                continue
            lx, ly = sx * p.scale * p.stretch, sy * p.scale
            q = (p.x + lx * c - ly * s, p.y + lx * s + ly * c)
            name = self._figure(r, mix or self._mix(self._kind_at(q)), "sit")
            if name is None:
                continue
            z = p.z + float(spec["height"]) * p.scale - self.figure_seat
            out.append(Cand(RANK["seat"], key + (j,), name, float(q[0]), float(q[1]),
                            p.yaw + math.radians(face) + turn, ANY_FLOOR, (0,) + key, idx, z))
        return out

    def _shop(self, p) -> list:
        """Browsers in front of a souk shop, beyond its goods, facing them."""
        n = np.array([-math.sin(p.yaw), math.cos(p.yaw)])
        q = np.array([p.x, p.y]) + n * 2.0
        hit = self.d.streets_at(q[None, :])[0]
        if hit < 0 or self.plan.streets[int(hit)].kind != "souk":
            return []
        cfg = self.cfg["shop"]
        u = np.array([math.cos(p.yaw), math.sin(p.yaw)])
        key = self._pos_key(p)
        mix = self._mix("medina")
        out = []
        for j, ch in enumerate(cfg["slots"]):
            rng = self.d.rng("people", "shop", *key, j)
            if rng.random() >= self.chance(ch):
                continue
            side = 1.0 if rng.random() < 0.5 else -1.0
            at = np.array([p.x, p.y]) + u * side * rng.uniform(0.15, 1.0) * float(cfg["along"]) \
                + n * rng.uniform(*cfg["reach"])
            face = -n + u * rng.uniform(-1.0, 1.0) * float(cfg["turn"])
            out += self._group(rng, "shop", key + (j,), at, face, mix, "stand", 0.0,
                               {"family": cfg["family"]}, (LANE,))
        return out

    def _kiosk(self, p) -> list:
        """Customers at a kiosk's window (its front), facing it."""
        cfg = self.cfg["square"]
        low = self._shape(p.piece, float(self.cfg["foot_level"]), 1.8)
        front = float(low[1][3]) if low is not None else self.bounds(p.piece)[3]
        u, n = np.array([math.cos(p.yaw), math.sin(p.yaw)]), np.array([-math.sin(p.yaw), math.cos(p.yaw)])
        key = self._pos_key(p)
        out = []
        for j, ch in enumerate(cfg["kiosk"]):
            rng = self.d.rng("people", "kiosk", *key, j)
            if rng.random() >= self.chance(ch):
                continue
            at = np.array([p.x, p.y]) + n * (front + rng.uniform(*cfg["kiosk_reach"]) + 0.2) \
                + u * (j - 0.5) * 1.3 + u * rng.uniform(-0.15, 0.15)
            out += self._group(rng, "square", key + (j,), at, -n, self._mix("colonial"), "stand", 0.0, {}, ANY_FLOOR)
        return out

    def _waiter(self, p) -> list:
        """Now and then a waiter standing beside a shaded cafe table, facing it (prompt 37)."""
        cfg = self.cfg["terrace"]
        key = self._pos_key(p)
        rng = self.d.rng("people", "waiter", *key)
        if rng.random() >= self.chance(cfg["waiter"]):
            return []
        name = self._figure(rng, {"shirt": 1.0}, "stand")
        if name is None:
            return []
        side = 1.0 if rng.random() < 0.5 else -1.0
        u = np.array([math.cos(p.yaw), math.sin(p.yaw)])
        n = np.array([-math.sin(p.yaw), math.cos(p.yaw)]) * side
        at = np.array([p.x, p.y]) + n * float(cfg["reach"]) + u * rng.uniform(-0.3, 0.3)
        return [Cand(RANK["square"], key + (100,), name, float(at[0]), float(at[1]), yaw_to(-n), ANY_FLOOR)]

    def _fountain(self, p) -> list:
        """People standing round a fountain's basin, facing the water."""
        cfg = self.cfg["square"]
        low = self._shape(p.piece, float(self.cfg["foot_level"]), 1.8)
        if low is None:
            return []
        radius = float(np.abs(low[1]).max())
        key = self._pos_key(p)
        count = int(cfg["fountain"])
        out = []
        for j in range(count):
            rng = self.d.rng("people", "fountain", *key, j)
            if rng.random() >= self.chance(cfg["fountain_chance"]):
                continue
            a = p.yaw + 2 * math.pi * (j + rng.uniform(-0.25, 0.25)) / count
            r = radius + rng.uniform(*cfg["fountain_reach"]) + 0.2
            at = np.array([p.x + r * math.cos(a), p.y + r * math.sin(a)])
            out += self._group(rng, "square", key + (j,), at, np.array([p.x, p.y]) - at, self._mix("colonial"),
                               "stand", 0.0, {"family": 0.15}, ANY_FLOOR)
        return out

    def _landmarks(self, region) -> list:
        """People round the great mosque (along its outline) and at the medina gates."""
        cfg = self.cfg["landmark"]
        out = []
        medina = self.plan.medina
        for li, lm in enumerate(self.plan.landmarks):
            at = Point(lm.x, lm.y)
            if lm.kind == "gate" and "gate" in cfg and region.distance(at) < cfg["gate"]["reach"][1] + 2.0:
                g = cfg["gate"]
                count = int(g["count"])
                for j in range(count):
                    rng = self.d.rng("people", "landmark", li, j)
                    if rng.random() >= self.chance(g["chance"]):
                        continue
                    a = 2 * math.pi * (j + rng.uniform(-0.4, 0.4)) / count
                    q = np.array([lm.x, lm.y]) + rng.uniform(*g["reach"]) * np.array([math.cos(a), math.sin(a)])
                    out += self._visitor(rng, (li, j), q, np.array([lm.x, lm.y]), cfg)
            elif lm.kind == "mosque" and "mosque" in cfg and medina is not None and medina.contains(at):
                ring = self._mosque_ring(li, lm)
                if ring is None or region.distance(ring) > cfg["mosque"]["reach"][1] + 2.0:
                    continue
                g = cfg["mosque"]
                step = float(g["step"])
                for j in range(int(ring.length // step)):
                    rng = self.d.rng("people", "landmark", li, j)
                    if rng.random() >= self.chance(g["chance"]):
                        continue
                    d = (j + rng.uniform(0.0, 1.0)) * step
                    p, nrm = street_frame(ring, np.array([d]))
                    q = p[0] - nrm[0] * rng.uniform(*g["reach"])       # the ring runs counter-clockwise: out is right
                    if self._in(q):
                        out += self._visitor(rng, (li, j), q, p[0], cfg)
        return out

    def _mosque_ring(self, li: int, lm):
        """The outline of the great mosque's buildings (hall, court, minaret), counter-clockwise."""
        if self._mosque is None and self.d.fp_tree is None:
            self._mosque = False
        if self._mosque is None:
            fps = [self.plan.buildings[int(i)].footprint for i in sorted(self.d.fp_tree.query(
                Point(lm.x, lm.y), predicate="dwithin", distance=80.0))
                if self.plan.buildings[int(i)].kind in ("mosque_hall", "mosque_court", "minaret")]
            merged = shapely.union_all([f.buffer(0.3) for f in fps]).buffer(-0.3) if fps else None
            parts = [g for g in getattr(merged, "geoms", [merged]) if g is not None and not g.is_empty]
            if parts:
                best = max(parts, key=lambda g: g.area)
                self._mosque = LineString(shapely.geometry.polygon.orient(best, 1.0).exterior.coords)
            else:
                self._mosque = False
        return self._mosque or None

    def _visitor(self, rng, key: tuple, q, target, cfg: dict) -> list:
        """Someone near a landmark: standing and facing it, or walking past."""
        if rng.random() < float(cfg["stand"]):
            return self._group(rng, "landmark", key, q, target - q, self._mix("medina"), "stand", 0.0, cfg, ANY_FLOOR)
        v = target - q
        tangent = np.array([v[1], -v[0]]) * (1.0 if rng.random() < 0.5 else -1.0)
        return self._group(rng, "landmark", key, q, tangent, self._mix("medina"), "walk", 0.2, cfg, ANY_FLOOR)

    def _stairs(self, region) -> list:
        """A few people by the stair doors of modern estates: on the door's path, walking it or chatting."""
        cfg = self.cfg["stair"]
        out = []
        if self.d.fp_tree is None:
            return out
        for k in sorted(int(i) for i in self.d.fp_tree.query(region, predicate="intersects")):
            b = self.plan.buildings[k]
            if not self.d._is_slab(b):
                continue
            for m, s in enumerate(self.d.door_spots(k)):
                if s.path is None or len(s.path) < 2:
                    continue
                rng = self.d.rng("people", "stair", k, m)
                if rng.random() >= self.chance(cfg["chance"]):
                    continue
                line = LineString(s.path)
                dist = min(rng.uniform(*cfg["reach"]), line.length - 0.6)
                if dist < 1.0:
                    continue
                p, nrm = street_frame(line, np.array([dist]))
                t = np.array([nrm[0, 1], -nrm[0, 0]])             # along the path, away from the door
                path = line.buffer(self.path_width / 2, cap_style="flat")
                mix = self._mix("modern")
                if rng.random() < float(cfg["chat"]):              # two neighbours facing each other
                    out += self._chat(rng, (k, m), p[0], t, mix, path)
                else:
                    head = t if rng.random() < 0.5 else -t
                    out += self._group(rng, "stair", (k, m), p[0], head, mix, "walk", 0.2, {}, (GROUND,), path)
        return out

    def _chat(self, rng, key: tuple, c, t, mix: dict, path) -> list:
        a, b = self._figure(rng, mix, "stand"), self._figure(rng, mix, "stand")
        if a is None or b is None:
            return []
        ya = yb = self.env["stand"]
        half = float(self.cfg["clear"]) / 2 + 0.05
        pa, pb = c - t * (ya[3] + half), c + t * (yb[3] + half)
        grp = (RANK["stair"],) + key
        return [Cand(RANK["stair"], key + (0,), a, float(pa[0]), float(pa[1]), yaw_to(t), (GROUND,), grp, path=path),
                Cand(RANK["stair"], key + (1,), b, float(pb[0]), float(pb[1]), yaw_to(-t), (GROUND,), grp, path=path)]

    # --- who gives way --------------------------------------------------------------------------
    def boxes(self, cands: list, grow: float = 0.0, env: bool = False) -> np.ndarray:
        """Plan rectangles (kit bounds) of placed people, grown by `grow`; with `env`, the rectangle holding
        every piece of the person's pose instead."""
        if not cands:
            return np.array([], dtype=object)
        r = np.array([self.env[self.pose[cd.piece][0]] if env else self.bounds(cd.piece) for cd in cands])
        lx = np.stack([r[:, 0] - grow, r[:, 1] + grow, r[:, 1] + grow, r[:, 0] - grow], 1)
        ly = np.stack([r[:, 2] - grow, r[:, 2] - grow, r[:, 3] + grow, r[:, 3] + grow], 1)
        yaw = np.array([cd.yaw for cd in cands])
        c, s = np.cos(yaw)[:, None], np.sin(yaw)[:, None]
        x = np.array([cd.x for cd in cands])[:, None]
        y = np.array([cd.y for cd in cands])[:, None]
        return shapely.polygons(np.stack([x + lx * c - ly * s, y + lx * s + ly * c], 2))

    def _thin(self, cands: list) -> np.ndarray:
        """False for a candidate too close to any earlier one (whatever becomes of that one): standing people
        `clear` apart, `pair_gap` within a group, `seated_gap` from a seated one; seated ones never overlap."""
        alive = np.ones(len(cands), dtype=bool)
        boxes = self.boxes(cands, env=True)     # a tile may still swap a piece for another of its pose (_cast)
        clear, seated_gap = float(self.cfg["clear"]), float(self.cfg["seated_gap"])
        a, b = STRtree(boxes).query(boxes, predicate="dwithin", distance=clear)
        keep = a < b
        a, b = a[keep], b[keep]
        if not len(a):
            return alive
        dist = shapely.distance(boxes[a], boxes[b])
        for i, j, dd in zip(a.tolist(), b.tolist(), dist.tolist()):
            ci, cj = cands[i], cands[j]
            if ci.group and ci.group == cj.group:
                continue
            sit = (ci.seat >= 0) + (cj.seat >= 0)
            need = clear if sit == 0 else (seated_gap if sit == 1 else 1e-9)
            if dd < need:
                alive[j] = False
        return alive

    def _cast(self, cands: list, budget: float | None) -> list:
        """Each figure a tile shows costs its mesh (about 14 KB, 8 KB quantized) in the tile, each person 40
        bytes (20 quantized): the most frequent figures are kept while they fit in `budget` bytes; a person
        with another one takes a kept figure of the same pose, of the same outfit if one is kept, else of the
        same body (men, women, children), else is left out. The budget stays a share of the tile's float
        size (`tile_bytes`), so quantized tiles show more figures and still end up smaller than before."""
        if budget is None or not cands:
            return cands
        count: dict = {}
        for cd in cands:
            count[cd.piece] = count.get(cd.piece, 0) + 1
        order = sorted(count, key=lambda n: (-count[n], n))
        used = (INSTANCE_Q if self.quantized else INSTANCE) * len(cands)
        kept = []
        for n in order:
            used += piece_bytes(self.kit.pieces[n], quantized=self.quantized)
            if used > budget:
                break
            kept.append(n)
        if len(kept) == len(order):
            return cands
        limit = len(kept)
        body = self.cfg["outfits"]["bodies"]
        swap: dict = {}
        for n in order[limit:]:
            ps, o = self.pose[n]
            same = [k for k in kept if self.pose[k] == (ps, o)] or \
                [k for k in kept if self.pose[k][0] == ps and body.get(self.pose[k][1]) == body.get(o)]
            swap[n] = same[0] if same else None
        out = []
        for cd in cands:
            piece = swap.get(cd.piece, cd.piece)
            if piece is not None:
                cd.piece = piece
                out.append(cd)
        return out

    # --- checks against what is drawn ---------------------------------------------------------
    def floors(self, pts: np.ndarray) -> np.ndarray:
        """Floor kind under each point: WALK (a raised walk or paved corner), LANE (a pedestrian street),
        ROAD (a carriageway) or GROUND."""
        out = np.full(len(pts), GROUND)
        if not len(pts):
            return out
        geoms = shapely.points(pts)
        if self.d.surface_tree is not None:
            inp, hit = self.d.surface_tree.query(geoms, predicate="intersects")
            road = np.zeros(len(pts), dtype=bool)
            np.logical_or.at(road, inp, ~self.shared[hit])
            out[inp] = LANE
            out[road] = ROAD
        if self.floor_tree is not None:
            inp, _ = self.floor_tree.query(geoms, predicate="intersects")
            out[inp] = WALK
        return out

    def _place(self, cands: list, near: list) -> list:
        if not cands:
            return []
        n = len(cands)
        ok = np.ones(n, dtype=bool)
        seated = np.array([cd.seat >= 0 for cd in cands])
        boxes = self.boxes(cands)
        # building footprints
        if self.d.fp_tree is not None:
            gap = np.where(seated, 0.0, float(self.cfg["wall_gap"]))
            inp, _ = self.d.fp_tree.query(shapely.buffer(boxes, gap, join_style="mitre"), predicate="intersects")
            ok[inp] = False
        # the floor: corners and origin all on one allowed kind (seated: never on a carriageway)
        corners = shapely.get_coordinates(boxes).reshape(n, 5, 2)[:, :4]
        pts = np.concatenate([corners, np.array([[cd.x, cd.y] for cd in cands])[:, None, :]], 1)
        kinds = self.floors(pts.reshape(-1, 2)).reshape(n, 5)
        for m, cd in enumerate(cands):
            if seated[m]:
                ok[m] &= not (kinds[m] == ROAD).any()
            else:
                ok[m] &= bool((kinds[m] == kinds[m, 4]).all() and kinds[m, 4] in cd.floors)
                if cd.path is not None:
                    ok[m] &= bool(shapely.contains_xy(cd.path, pts[m, :, 0], pts[m, :, 1]).all())
        # heights
        z = np.array([cd.seat_z for cd in cands])
        stand = np.nonzero(~seated & ok)[0]
        if len(stand):
            on_ground = np.array([kinds[m, 4] == GROUND for m in stand])
            xy = np.array([(cands[m].x, cands[m].y) for m in stand])
            if (~on_ground).any():
                zs = np.atleast_1d(self.d.ground.surface(xy[~on_ground, 0], xy[~on_ground, 1]))
                drawn = self._walk_z(xy[~on_ground])          # a walk's triangles lie a few cm off the formula
                z[stand[~on_ground]] = np.where(np.isnan(drawn), zs, drawn)
            if on_ground.any():
                lift = np.array([self.path_lift if cands[m].path is not None else 0.0 for m in stand[on_ground]])
                z[stand[on_ground]] = self.d.drawn(xy[on_ground, 0], xy[on_ground, 1]) + lift
        ok &= self._clear_of_pieces(cands, boxes, z, near, ok)
        return [self.Placement(cd.piece, cd.x, cd.y, float(z[m]), cd.yaw, False) for m, cd in enumerate(cands) if ok[m]]

    def _walk_z(self, xy: np.ndarray) -> np.ndarray:
        """Height of the drawn sidewalk or promenade triangles at each point; NaN off them."""
        out = np.full(len(xy), np.nan)
        if self.walk_tree is None or not len(xy):
            return out
        inp, hit = self.walk_tree.query(shapely.points(xy), predicate="intersects")
        for m, w in zip(inp.tolist(), hit.tolist()):
            if w not in self._walk_mesh:
                poly = self.walks[w].polygon
                tri = triangulate(shapely.segmentize(orient(poly, sign=1.0), self.d.ground.walk_step(poly, self.walk_step)))
                zs = np.asarray(self.d.ground.walk_top(tri[..., 0].ravel(), tri[..., 1].ravel())).reshape(-1, 3)
                self._walk_mesh[w] = (tri, zs, STRtree(shapely.polygons(tri)))
            tri, zs, tree = self._walk_mesh[w]
            for k in tree.query(Point(xy[m]), predicate="intersects").tolist():
                a, b, c = tri[k]
                det = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
                u = ((xy[m, 0] - a[0]) * (c[1] - a[1]) - (xy[m, 1] - a[1]) * (c[0] - a[0])) / det
                v = ((b[0] - a[0]) * (xy[m, 1] - a[1]) - (b[1] - a[1]) * (xy[m, 0] - a[0])) / det
                z = zs[k, 0] + u * (zs[k, 1] - zs[k, 0]) + v * (zs[k, 2] - zs[k, 0])
                out[m] = z if np.isnan(out[m]) else max(out[m], z)
        return out

    def _clear_of_pieces(self, cands: list, boxes, z: np.ndarray, near: list, ok: np.ndarray) -> np.ndarray:
        """False where a person meets a piece below head height (its own seat piece aside)."""
        out = np.ones(len(cands), dtype=bool)
        if not near or not ok.any():
            return out
        foot, z0, z1 = piece_boxes(self.kit, near, 0.0)
        tops = np.array([self.kit.pieces[cd.piece].top for cd in cands])
        grown = shapely.buffer(boxes, float(self.cfg["piece_gap"]), join_style="mitre")
        idx = np.nonzero(ok)[0]
        a, b = STRtree(foot).query(grown[idx], predicate="intersects")
        a = idx[a]
        level = float(self.cfg["foot_level"])
        for m, j in zip(a.tolist(), b.tolist()):
            if not out[m] or cands[m].seat == j or self._shades(cands[m].seat, near, j):
                continue
            lo, hi = z[m] + level, z[m] + tops[m]
            if z0[j] >= hi or z1[j] <= lo:
                continue
            p = near[j]
            sx, sy = p.scale * p.stretch, p.scale
            shape = self._shape(p.piece, (lo - p.z) / sy, (hi - p.z) / sy)
            if shape is None:
                continue
            c, s = math.cos(p.yaw), math.sin(p.yaw)
            pts = shapely.get_coordinates(grown[m]) - (p.x, p.y)
            local = np.stack([(pts[:, 0] * c + pts[:, 1] * s) / sx, (-pts[:, 0] * s + pts[:, 1] * c) / sy], 1)
            if len(shape[0].query(shapely.Polygon(local), predicate="intersects")):
                out[m] = False
        return out

    def _shades(self, seat: int, near: list, j: int) -> bool:
        """Is piece j the parasol standing in the hole of seat piece `seat`'s table (prompt 37)?"""
        if seat < 0 or self.kit.pieces[near[j].piece].category != "parasol":
            return False
        return abs(near[j].x - near[seat].x) < 1e-6 and abs(near[j].y - near[seat].y) < 1e-6

    def _shape(self, name: str, lo: float, hi: float):
        """(STRtree, bounds) of a piece's triangles between heights lo and hi above its origin, in plan (piece
        axes: x right, y front; an upright face is a line), bands rounded outward to 0.25 m (kept); None
        when it has nothing there."""
        q = 0.25
        key = (name, math.floor(lo / q), math.ceil(hi / q))
        if key not in self._low:
            if name not in self._tris:
                pc = self.kit.pieces[name]
                tris = np.concatenate([p["pos"][p["idx"].reshape(-1, 3)] for p in pc.parts.values()])
                self._tris[name] = (np.stack([tris[:, :, 0], -tris[:, :, 2]], 2), tris[:, :, 1].min(1), tris[:, :, 1].max(1))
            plan, zlo, zhi = self._tris[name]
            sel = (zhi > key[1] * q) & (zlo < key[2] * q)
            shape = None
            if sel.any():
                hulls = shapely.convex_hull(shapely.multipoints(plan[sel]))
                shape = (STRtree(hulls), shapely.total_bounds(hulls))
            self._low[key] = shape
        return self._low[key]
