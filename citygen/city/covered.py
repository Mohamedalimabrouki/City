"""Covered souks (prompt 31): which souk streets get a roof, where it runs and how high it springs.

One deterministic rule serves both sides of a tile: the mesher draws the vaults from it
(`mesh/vaults.py`) and the dresser reads it (no strings or bunting under a roof, lanterns hung
from its arches, nothing piercing it). Nothing is stored in the plan: `Covers` works the answer
out from the plan and the ground, so every tile and every process gets the same one.

A covered stretch runs between walls: its line is probed every `probe` m on both sides for a house
wall within `reach` m beyond the street edge. A side alley's mouth is bridged by a lintel (an
opening on one side up to `bridge` m long); the roof stops short where both sides open, at a wider
opening, at a sharp bend and `end_gap` m before the souk's ends (its crossings, gates, the mosque).
The roof springs at min(the taller wall top, `spring`) above the street (at least `spring_min`):
a lower house gets its wall filled up to the springing, an opening a lintel. Stations (the rings
the vault is drawn through) sit at the bends, at the transverse arches every `bay` m, at the edges
of the light openings in the crown and every `step` m in between.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import shapely
from shapely.strtree import STRtree

from ..rng import stream
from .massing import wall_height

CARRIERS = {"house", "domed", "apartments"}   # walls a souk roof may rest on


def covered_streets(plan, cfg: dict, souks: list) -> list:
    """Sorted indices of the covered souk streets: souks of the trades listed by their word (`souks` is
    the style's [[souk]] table), and the `longest` longest souk streets of the city."""
    if not cfg:
        return []
    trades = set(cfg.get("trades", ()))
    word = {t["trade"]: t["word"] for t in souks}
    out = {s.street for s in getattr(plan, "souks", ()) if word.get(s.trade) in trades}
    longest = sorted((k for k, st in enumerate(plan.streets) if st.kind == "souk"),
                     key=lambda k: (-plan.streets[k].line.length, k))
    return sorted(out | set(longest[:int(cfg.get("longest", 0))]))


@dataclass
class Shape:
    """Cross-section of a souk vault, the same for every souk of one width."""
    half: float     # half the street width
    w: float        # across offset of the vault's inner face (the impost band face)
    f: float        # rise of the vault above its springing
    r: float        # radius of the intrados
    phi: float      # half angle of the intrados arc
    t: float        # vault thickness
    bd: float       # depth of the impost band and fills, outward from w
    band: float     # height of the impost band under the springing
    curb: tuple     # (height, thickness) of the curb round a light opening, on the roof
    s: tuple        # ring fractions from one side (0) to the other (1); the crown band is the hole band

    @classmethod
    def of(cls, width: float, cfg: dict) -> "Shape":
        half = width / 2.0
        w = half + float(cfg.get("inset", 0.05))
        f = min(float(cfg.get("rise", 1.8)), w)
        r = (w * w + f * f) / (2.0 * f)
        ring = tuple(float(v) for v in cfg.get("ring", (0.0, 0.25, 0.425, 0.575, 0.75, 1.0)))
        return cls(half, w, f, r, math.asin(min(1.0, w / r)), float(cfg.get("thickness", 0.25)),
                   float(cfg.get("band_depth", 0.5)), float(cfg.get("band", 0.45)),
                   tuple(float(v) for v in cfg.get("curb", (0.15, 0.1))), ring)

    def crown(self) -> int:
        """Index of the ring band holding the crown (where the light openings are cut)."""
        return int(np.searchsorted(self.s, 0.5) - 1)

    def ring(self, radius: float) -> tuple:
        """(across, up, angle) of the ring points on a circle of `radius` round the intrados center."""
        a = self.phi * (2.0 * np.asarray(self.s) - 1.0)
        return radius * np.sin(a), radius * np.cos(a) - (self.r - self.f), a

    def up(self, across) -> np.ndarray:
        """Height of the intrados above the springing at an across offset (|across| <= w)."""
        a = np.minimum(np.abs(np.asarray(across, dtype=float)), self.w)
        return np.sqrt(np.maximum(self.r * self.r - a * a, 0.0)) - (self.r - self.f)


@dataclass
class Stretch:
    street: int
    shape: Shape
    d: np.ndarray        # station distances along the street line, a .. b
    p: np.ndarray        # (n, 2) station points on the center line
    m: np.ndarray        # (n, 2) across vector (unit normal; mitred at a bend, so the width holds)
    t: np.ndarray        # (n, 2) unit tangent (the bisector at a bend)
    z: np.ndarray        # (n,) springing, absolute
    low: np.ndarray      # (n, 2) fill bottom, absolute, on the -m and +m sides
    holes: np.ndarray    # (n - 1,) bool: a light opening in the crown band of that segment
    arches: list         # distances of the transverse arches; the first and last are the portals
    lanterns: list       # (distance, hook z) of the lanterns hung from the arches
    spring: float        # springing above the street, meters

    @property
    def top(self) -> np.ndarray:
        """Height of the roof's highest point (the curbs on the crown) at each station."""
        return self.z + self.shape.f + self.shape.t + self.shape.curb[0]

    def frame(self, d: float) -> tuple:
        """(point, across vector, tangent, springing) at distance d inside the stretch (not at a bend)."""
        i = int(np.clip(np.searchsorted(self.d, d) - 1, 0, len(self.d) - 2))
        u = (d - self.d[i]) / max(self.d[i + 1] - self.d[i], 1e-9)
        p = self.p[i] + (self.p[i + 1] - self.p[i]) * u
        t = self.p[i + 1] - self.p[i]
        t = t / max(float(np.hypot(*t)), 1e-9)
        return p, np.array([-t[1], t[0]]), t, float(self.z[i] + (self.z[i + 1] - self.z[i]) * u)


class Covers:
    """The covered stretches of one city, worked out on first use and kept."""

    def __init__(self, world, plan, ground):
        self.cfg = world.style.get("covered_souk", {})
        self.plan, self.ground = plan, ground
        self.seed, self.sid = world.seed, plan.settlement.id
        self.streets = covered_streets(plan, self.cfg, world.style.get("souk", []))
        self._stretches: dict = {}
        self._segments = None
        self._fp = None                          # footprints and their STRtree (lazy)

    def of(self, k: int) -> list:
        """The covered stretches of street k (none for most streets)."""
        if k not in self.streets:
            return []
        if k not in self._stretches:
            self._stretches[k] = self._build(k)
        return self._stretches[k]

    def all(self) -> list:
        return [s for k in self.streets for s in self.of(k)]

    def covered(self, k: int, d: float, margin: float = 0.0) -> bool:
        """Is distance d along street k under a roof (or within `margin` m of one)?"""
        return any(s.d[0] - margin <= d <= s.d[-1] + margin for s in self.of(k))

    # --- the rule ------------------------------------------------------------------------------
    def _build(self, k: int) -> list:
        cfg, st = self.cfg, self.plan.streets[k]
        line = st.line
        shape = Shape.of(st.width, cfg)
        gap, probe = float(cfg.get("end_gap", 4.0)), float(cfg.get("probe", 1.5))
        ds = np.arange(gap, line.length - gap + 1e-9, probe)
        if len(ds) < 2:
            return []
        coords = np.asarray(line.coords)[:, :2]
        cum = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(coords, axis=0).T))])
        turns = _turns(coords)
        pts, nrm = _points(coords, cum, ds)
        g = np.atleast_1d(self.ground.surface(pts[:, 0], pts[:, 1]))
        tops = self._walls(pts, nrm, shape.half + float(cfg.get("reach", 1.4))) - g[:, None]   # nan: no carrier
        miss = np.isnan(tops)
        bad = miss.all(axis=1)
        for side in (0, 1):
            bad |= _long_runs(miss[:, side], int(float(cfg.get("bridge", 4.5)) // probe) + 1)
        sharp = np.abs(turns) > float(cfg.get("max_turn", 50.0))
        for v in np.nonzero(sharp)[0]:
            bad |= np.abs(ds - cum[v + 1]) < shape.half + 1.0
        out = []
        for lo, hi in runs(~bad):
            while lo < hi and miss[lo].any():      # a portal stands between two walls
                lo += 1
            while hi > lo and miss[hi].any():
                hi -= 1
            if ds[hi] - ds[lo] < float(cfg.get("min_run", 12.0)):
                continue
            spring = float(np.clip(np.nanmax(tops[lo:hi + 1], axis=1).min(),
                                   float(cfg.get("spring_min", 3.6)), float(cfg.get("spring", 4.0))))
            s = self._stretch(k, len(out), shape, coords, cum, turns, ds[lo], ds[hi], spring,
                              ds[lo:hi + 1], tops[lo:hi + 1])
            if s is not None:
                out.append(s)
        return out

    def _walls(self, pts: np.ndarray, nrm: np.ndarray, reach: float) -> np.ndarray:
        """(n, 2) absolute top of the carrier wall each side of each point (-nrm, +nrm), nan where none."""
        from .dressing import building_highs
        out = np.full((len(pts), 2), np.nan)
        if self._fp is None:
            fps = np.array([b.footprint for b in self.plan.buildings], dtype=object)
            self._fp = (fps, STRtree(fps))
        fps, tree = self._fp
        rays = shapely.linestrings(np.stack([np.repeat(pts, 2, axis=0),
                                             np.repeat(pts, 2, axis=0) + np.tile([[-1.0], [1.0]], (len(pts), 1))
                                             * np.repeat(nrm, 2, axis=0) * reach], axis=1))
        ri, bi = tree.query(rays, predicate="intersects")
        if not len(ri):
            return out
        hits = shapely.intersection(rays[ri], shapely.get_exterior_ring(fps[bi]))
        best: dict = {}
        origin = np.repeat(pts, 2, axis=0)
        for r, b, h in zip(ri.tolist(), bi.tolist(), hits):
            xy = shapely.get_coordinates(h)
            if not len(xy):
                continue
            dist = np.hypot(*(xy - origin[r]).T)
            j = int(np.argmin(dist))
            if r not in best or dist[j] < best[r][0]:
                best[r] = (float(dist[j]), b, xy[j])
        keep = [(r, b, xy) for r, (dist, b, xy) in sorted(best.items())
                if self.plan.buildings[b].kind in CARRIERS and dist >= 0.8]
        if not keep:
            return out
        owners = sorted({b for _, b, _ in keep})
        high = dict(zip(owners, building_highs(self.ground, [self.plan.buildings[b] for b in owners]).tolist()))
        for r, b, xy in keep:
            out[r // 2, r % 2] = high[b] + float(wall_height(self.plan.buildings[b], xy[None, :])[0])
        return out

    def _stretch(self, k, index, shape, coords, cum, turns, a, b, spring, ds, tops) -> Stretch | None:
        """Stations, arches, openings and lanterns of one covered stretch from a to b."""
        cfg = self.cfg
        clear = (shape.w + shape.bd) * np.tan(np.radians(np.abs(turns)) / 2.0) + 0.05   # no fold at a bend
        verts = [(cum[v + 1], clear[v]) for v in range(len(turns)) if a < cum[v + 1] < b]
        if verts and verts[0][0] - a < verts[0][1]:          # an end too close to a bend moves onto it
            a = verts.pop(0)[0]
        if verts and b - verts[-1][0] < verts[-1][1]:
            b = verts.pop()[0]
        if b - a < float(cfg.get("min_run", 12.0)):
            return None
        breaks = [a] + [v for v, _ in verts] + [b]
        near = {v: c for v, c in verts}
        bay, hole, aw = float(cfg.get("bay", 7.0)), float(cfg.get("hole", 1.0)), float(cfg.get("arch_width", 0.45))
        arches, edges, hole_mid = [a], [], []
        for r0, r1 in zip(breaks[:-1], breaks[1:]):   # straight runs between the bends: bays of about `bay` m
            v0, v1 = near.get(r0, 0.0), near.get(r1, 0.0)
            n = max(1, int(round((r1 - r0) / bay)))
            marks = [r0 + (r1 - r0) * i / n for i in range(n + 1)]
            arches += [x for x in marks[1:-1] if x - r0 >= v0 + aw and r1 - x >= v1 + aw]
            for x0, x1 in zip(marks[:-1], marks[1:]):  # a light opening in the middle of each bay
                mid = (x0 + x1) / 2.0
                lo, hi = mid - hole / 2, mid + hole / 2
                if lo - r0 >= v0 + 0.3 and r1 - hi >= v1 + 0.3 and x1 - x0 >= hole + 2.0:
                    edges += [lo, hi]
                    hole_mid.append(mid)
        arches.append(b)
        keys = sorted(set(breaks) | set(arches) | set(edges))
        step = float(cfg.get("step", 3.0))
        d = []
        for x0, x1 in zip(keys[:-1], keys[1:]):
            n = max(1, int(math.ceil((x1 - x0) / step - 1e-9)))
            d += [x0 + (x1 - x0) * i / n for i in range(n)]
        d.append(keys[-1])
        d = np.array([x for x in d if x in keys or all(abs(x - v) >= c for v, c in verts)])
        p, m, t = _frames(coords, cum, d)
        g = np.atleast_1d(self.ground.surface(p[:, 0], p[:, 1]))
        z = g + spring
        rel = _nearest(ds, tops, d)                              # wall top above the street, nan: opening
        band, lintel = shape.band, float(cfg.get("lintel", 0.7))
        low = np.where(np.isnan(rel), spring - lintel, np.minimum(np.nan_to_num(rel, nan=0.0), spring - band))
        low = g[:, None] + np.clip(low, float(cfg.get("fill_min", 2.9)), spring - band)
        mids = (d[:-1] + d[1:]) / 2.0
        holes = np.array([any(abs(x - h) < 1e-6 for h in hole_mid) for x in mids], dtype=bool)
        s = Stretch(k, shape, d, p, m, t, z, low, holes, [float(x) for x in arches], [], spring)
        drop, chance = float(cfg.get("arch_proud", 0.12)) + float(cfg.get("chain", 0.4)), float(cfg.get("lantern", 0.8))
        for i, x in enumerate(arches[1:-1]):                   # a lantern on a rod under the inner arches
            if stream(self.seed, "city", self.sid, "covered", "lantern", k, index, i).random() < chance:
                s.lanterns.append((float(x), s.frame(x)[3] + shape.f - drop))
        return s

    # --- nothing pierces a roof ---------------------------------------------------------------
    def segments(self) -> tuple:
        """(STRtree of the plan quads of every roof segment, [(stretch, i)]): what the roof covers."""
        if self._segments is None:
            polys, refs = [], []
            for s in self.all():
                out = s.shape.w + s.shape.bd
                for i in range(len(s.d) - 1):
                    q = [s.p[i] - s.m[i] * out, s.p[i + 1] - s.m[i + 1] * out,
                         s.p[i + 1] + s.m[i + 1] * out, s.p[i] + s.m[i] * out]
                    polys.append(shapely.Polygon(q))
                    refs.append((s, i))
            self._segments = (STRtree(polys) if polys else None, refs)
        return self._segments

    def clear(self, placements: list, kit, lower: dict | None = None) -> list:
        """The placements without those piercing a roof. A piece named in `lower` (piece -> lowest
        bottom above the street: a wall lamp, a shop awning) is lowered under the roof instead, while
        its bottom stays that high. Placements are absolute."""
        tree, refs = self.segments()
        if tree is None or not placements:
            return placements
        from .openings import piece_boxes
        boxes, z0, z1 = piece_boxes(kit, placements, 0.0)
        pi, si = tree.query(boxes, predicate="intersects")
        if not len(pi):
            return placements
        lower = lower or {}
        drop = set()
        for j in np.unique(pi).tolist():
            ceiling, ground, top = math.inf, -math.inf, -math.inf
            corners = shapely.get_coordinates(boxes[j])[:4]
            for q in si[pi == j].tolist():
                c, g, t = _ceiling(*refs[q], corners)
                ceiling, ground, top = min(ceiling, c), max(ground, g), max(top, t)
            if z1[j] <= ceiling + 1e-6 or z0[j] >= top:
                continue
            p = placements[j]
            dz = z1[j] - ceiling + 0.05
            if p.piece in lower and z0[j] - dz >= ground + lower[p.piece]:
                p.z -= float(dz)
            else:
                drop.add(j)
        return [p for j, p in enumerate(placements) if j not in drop]


def owns(tile, x, y):
    """Does the tile own the point(s)? Half-open bounds, so a point on a tile edge has one owner."""
    x0, y0, x1, y1 = tile.bounds
    return (x0 <= x) & (x < x1) & (y0 <= y) & (y < y1)


def _ceiling(s: Stretch, i: int, corners: np.ndarray) -> tuple:
    """(lowest roof underside over the corners, street level, roof top) for segment i of stretch s:
    the intrados inside the vault, the fill bottom over the impost bands."""
    a, b = s.p[i], s.p[i + 1]
    ab = b - a
    length2 = max(float(ab @ ab), 1e-12)
    u = np.clip(((corners - a) @ ab) / length2, 0.0, 1.0)
    n = np.array([-ab[1], ab[0]]) / math.sqrt(length2)
    across = (corners - (a + u[:, None] * ab)) @ n
    z = s.z[i] + (s.z[i + 1] - s.z[i]) * u
    low = np.where(across < 0, s.low[i, 0] + (s.low[i + 1, 0] - s.low[i, 0]) * u,
                   s.low[i, 1] + (s.low[i + 1, 1] - s.low[i, 1]) * u)
    sh = s.shape
    c = np.where(np.abs(across) <= sh.w, z + sh.up(across),
                 np.where(np.abs(across) <= sh.w + sh.bd, low, np.inf))
    return float(c.min()), float(z.max() - s.spring), float(z.max() + sh.f + sh.t + sh.curb[0] + 0.05)


def _turns(coords: np.ndarray) -> np.ndarray:
    """Signed turn in degrees at each interior vertex of a polyline."""
    v = np.diff(coords, axis=0)
    ang = np.degrees(np.arctan2(v[:, 1], v[:, 0]))
    return (np.diff(ang) + 180.0) % 360.0 - 180.0


def _points(coords: np.ndarray, cum: np.ndarray, ds: np.ndarray) -> tuple:
    """Points at distances ds along a polyline and the unit normal of the segment each lies on."""
    j = np.clip(np.searchsorted(cum, ds, side="right") - 1, 0, len(coords) - 2)
    seg = coords[j + 1] - coords[j]
    length = np.hypot(*seg.T)[:, None]
    tan = seg / np.maximum(length, 1e-9)
    p = coords[j] + tan * (ds - cum[j])[:, None]
    return p, np.stack([-tan[:, 1], tan[:, 0]], axis=1)


def _frames(coords: np.ndarray, cum: np.ndarray, d: np.ndarray) -> tuple:
    """(points, across vectors, tangents) at distances d; at a vertex the ring lies on the bisector,
    its across vector stretched by 1 / cos(half the turn) so both segments keep their width."""
    p, n = _points(coords, cum, d)
    t = np.stack([n[:, 1], -n[:, 0]], axis=1)
    m = n.copy()
    for i, x in enumerate(d):
        v = int(np.searchsorted(cum, x))
        if not (0 < v < len(cum) - 1 and abs(cum[v] - x) < 1e-9):
            continue
        if i == len(d) - 1:                    # the last ring ends its own segment, square to it
            t0 = (coords[v] - coords[v - 1]) / max(cum[v] - cum[v - 1], 1e-9)
            p[i], t[i], m[i] = coords[v], t0, np.array([-t0[1], t0[0]])
        elif i > 0:                            # the first ring stands on the next segment already
            t0 = (coords[v] - coords[v - 1]) / max(cum[v] - cum[v - 1], 1e-9)
            t1 = (coords[v + 1] - coords[v]) / max(cum[v + 1] - cum[v], 1e-9)
            tb = (t0 + t1) / max(float(np.hypot(*(t0 + t1))), 1e-9)
            nb = np.array([-tb[1], tb[0]])
            p[i], t[i] = coords[v], tb
            m[i] = nb / max(float(nb @ np.array([-t1[1], t1[0]])), 0.2)
    return p, m, t


def _nearest(ds: np.ndarray, values: np.ndarray, d: np.ndarray) -> np.ndarray:
    j = np.clip(np.searchsorted(ds, d), 1, len(ds) - 1)
    j -= (d - ds[j - 1]) < (ds[j] - d)
    return values[j]


def runs(mask: np.ndarray) -> list:
    """(first, last) index of every run of True."""
    out, start = [], None
    for i, v in enumerate(mask.tolist() + [False]):
        if v and start is None:
            start = i
        elif not v and start is not None:
            out.append((start, i - 1))
            start = None
    return out


def _long_runs(mask: np.ndarray, count: int) -> np.ndarray:
    """True on every run of True at least `count` long."""
    out = np.zeros(len(mask), dtype=bool)
    for lo, hi in runs(mask):
        if hi - lo + 1 >= count:
            out[lo:hi + 1] = True
    return out
