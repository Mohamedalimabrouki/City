"""Graded ground inside cities: smooth, gently terraced, blending into the natural terrain.

Raw noise terrain has 8-10% slopes around the capital, so a street ribbon dips under the ground
and a wall base floats or sinks. Inside a city this module replaces the terrain height with a
graded one:

  outside every city     the natural terrain height, unchanged
  inside a city          a blurred terrain (mean over a disc of `radius` meters), partly
                         flattened under each block (at most `terrace_max` meters), blended
                         back to the natural terrain over `edge_band` meters at the city limit

`height` is the ground itself; `surface` is the top of what is drawn there, adding the street
ribbon's lift and the curb of a raised sidewalk or promenade. Everything is a pure function of
position. The blur is sampled on a world-aligned
lattice and interpolated bilinearly, so two neighbouring tiles compute exactly the same height on
their shared edge and no seam can appear.
"""
from __future__ import annotations

import math

import numpy as np
import shapely
from shapely.geometry import box
from shapely.ops import unary_union
from shapely.strtree import STRtree

from ..mesh.builder import triangulate
from ..noise import smoothstep

# districts whose blocks are left alone: open land or very large plots, where a terrace would
# only cut a cliff into the slope
NO_TERRACE = ("park", "cemetery", "industrial", "port")

# how far a street ribbon is drawn above the ground (mesh/tile.py uses the same numbers)
STREET_LIFT = {"boulevard": 0.32, "arterial": 0.3, "ring": 0.3, "corniche": 0.3, "connector": 0.28,
               "street": 0.24, "souk": 0.2, "alley": 0.18, "impasse": 0.18}


class _Blur:
    """Mean terrain height over a disc of `radius`, on a world-aligned lattice, filled lazily.

    The terrain is sampled once per lattice cell. The disc mean is then an exact convolution of
    those cells (cell centers inside the radius, equal weights), so a tile pays for one terrain
    sample per cell it touches, not for a pattern of samples per cell. Cells are cached, so
    neighbouring tiles share them.
    """

    def __init__(self, terrain, boundary, radius: float, lattice: float):
        self.terrain = terrain
        self.lattice = lattice
        minx, miny, maxx, maxy = boundary.bounds
        margin = radius + 2.0 * lattice
        self.i0 = int(math.floor((minx - margin) / lattice))
        self.j0 = int(math.floor((miny - margin) / lattice))
        i1 = int(math.floor((maxx + margin) / lattice))
        j1 = int(math.floor((maxy + margin) / lattice))
        self.shape = (j1 - self.j0 + 2, i1 - self.i0 + 2)
        self.raw = np.full(self.shape, np.nan)
        self.values = np.full(self.shape, np.nan)
        self.k = max(1, int(math.ceil(radius / lattice)))
        limit = (radius / lattice) ** 2
        self.kernel = [(di, dj) for dj in range(-self.k, self.k + 1) for di in range(-self.k, self.k + 1)
                       if di * di + dj * dj <= limit]

    def _raw_fill(self, i0: int, i1: int, j0: int, j1: int) -> None:
        """Terrain height for every missing cell of the index box (clipped to the lattice)."""
        i0, j0 = max(i0, 0), max(j0, 0)
        i1, j1 = min(i1, self.shape[1] - 1), min(j1, self.shape[0] - 1)
        if i0 > i1 or j0 > j1:
            return
        sub = self.raw[j0:j1 + 1, i0:i1 + 1]
        jj, ii = np.nonzero(np.isnan(sub))
        if not len(ii):
            return
        x = (self.i0 + i0 + ii) * self.lattice
        y = (self.j0 + j0 + jj) * self.lattice
        sub[jj, ii] = self.terrain.height(x, y)

    def _fill(self, i0: int, i1: int, j0: int, j1: int) -> None:
        """Compute the missing blurred cells of the index box (clipped to the lattice)."""
        i0, j0 = max(i0, 0), max(j0, 0)
        i1, j1 = min(i1, self.shape[1] - 1), min(j1, self.shape[0] - 1)
        if i0 > i1 or j0 > j1:
            return
        sub = self.values[j0:j1 + 1, i0:i1 + 1]
        missing = np.isnan(sub)
        if not missing.any():
            return
        rj, ri = np.nonzero(missing)
        self._raw_fill(i0 - self.k, i1 + self.k, j0 - self.k, j1 + self.k)
        ii, jj = ri + i0, rj + j0
        total = np.zeros(len(ii))
        count = np.zeros(len(ii))
        for di, dj in self.kernel:   # only cells whose disc reaches inside the lattice
            si, sj = ii + di, jj + dj
            ok = (si >= 0) & (si < self.shape[1]) & (sj >= 0) & (sj < self.shape[0])
            total[ok] += self.raw[sj[ok], si[ok]]
            count[ok] += 1.0
        sub[rj, ri] = total / np.maximum(count, 1.0)

    def __call__(self, x, y):
        fx = np.asarray(x, dtype=np.float64) / self.lattice - self.i0
        fy = np.asarray(y, dtype=np.float64) / self.lattice - self.j0
        h, w = self.shape
        fx = np.minimum(np.maximum(fx, 0.0), w - 1.0)
        fy = np.minimum(np.maximum(fy, 0.0), h - 1.0)
        i = np.minimum(np.maximum(np.floor(fx).astype(np.int64), 0), w - 2)
        j = np.minimum(np.maximum(np.floor(fy).astype(np.int64), 0), h - 2)
        self._fill(int(i.min()), int(i.max()) + 1, int(j.min()), int(j.max()) + 1)
        tx, ty = fx - i, fy - j
        v = self.values.ravel()   # a view: values is contiguous
        at = j * w + i
        top = v[at] * (1.0 - tx) + v[at + 1] * tx
        bottom = v[at + w] * (1.0 - tx) + v[at + w + 1] * tx
        return top * (1.0 - ty) + bottom * ty

    def one(self, x: float, y: float) -> float:
        """`__call__` at one point with plain floats: the same operations in the same order."""
        h, w = self.shape
        fx = min(max(x / self.lattice - self.i0, 0.0), w - 1.0)
        fy = min(max(y / self.lattice - self.j0, 0.0), h - 1.0)
        i = min(max(math.floor(fx), 0), w - 2)
        j = min(max(math.floor(fy), 0), h - 2)
        self._fill(i, i + 1, j, j + 1)
        tx, ty = fx - i, fy - j
        v = self.values
        top = v[j, i] * (1.0 - tx) + v[j, i + 1] * tx
        bottom = v[j + 1, i] * (1.0 - tx) + v[j + 1, i + 1] * tx
        return float(top * (1.0 - ty) + bottom * ty)


def _smoothstep(edge0: float, edge1: float, x: float) -> float:
    """`noise.smoothstep` for one float (same operations)."""
    t = min(max((x - edge0) / (edge1 - edge0), 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


class _City:
    """One planned city: its blur field, and the blocks that get a terrace."""

    def __init__(self, plan, ground):
        self.plan = plan
        self.blur = _Blur(ground.terrain, plan.boundary, ground.radius, ground.lattice)
        self.blocks, centers, bounds = [], [], []
        for poly, did in plan.blocks:
            if plan.districts[did].kind in NO_TERRACE or poly.area > ground.terrace_max_area:
                continue
            self.blocks.append(poly)
            centers.append((poly.centroid.x, poly.centroid.y))
            bounds.append(poly.bounds)
        self.centers = np.asarray(centers, dtype=np.float64).reshape(-1, 2)
        self.bounds_xy = np.asarray(bounds, dtype=np.float64).reshape(-1, 4)
        self.terrace = np.full(len(self.blocks), np.nan)
        self.tree = STRtree(self.blocks) if self.blocks else None
        self.bounds = plan.boundary.bounds
        self.edge_line = plan.boundary.boundary
        self._overlap = None
        st = getattr(plan, "station", None)             # the station stands on level ground (prompt 33)
        self.level = self.level_zone = None
        if st is not None and st.core is not None:
            band = float(ground.level_band)
            zone = st.core.buffer(band)
            shapely.prepare(st.core)
            shapely.prepare(zone)
            self.level = (st.core, zone.bounds, float(st.facade["level"]), band)
            self.level_zone = zone

    def leveled(self, x: np.ndarray, y: np.ndarray, pts, out: np.ndarray) -> np.ndarray:
        """`out` graded toward the station's level: all the way on its core, blending out over the band."""
        core, (x0, y0, x1, y1), level, band = self.level
        sel = np.nonzero((x >= x0) & (x <= x1) & (y >= y0) & (y <= y1))[0]
        if len(sel):
            t = np.clip(shapely.distance(core, pts[sel]) / band, 0.0, 1.0)
            w = 1.0 - t * t * t * (t * (6.0 * t - 15.0) + 10.0)    # smootherstep: no kink in the slope at either end
            out[sel] = out[sel] * (1.0 - w) + level * w
        return out

    def _overlapping(self) -> bool:
        """True when two terraced blocks share interior points (then a point's block depends on
        the tree's order, so `block_at` keeps the tree query)."""
        if self._overlap is None:
            a, b = self.tree.query(self.blocks, predicate="intersects")
            pair = a < b
            geoms = np.asarray(self.blocks, dtype=object)
            self._overlap = bool(shapely.relate_pattern(geoms[a[pair]], geoms[b[pair]], "T********").any())
        return self._overlap

    def _candidates(self, x: np.ndarray, y: np.ndarray):
        """Blocks whose bounds meet the points' bounding box."""
        lo_x, hi_x, lo_y, hi_y = x.min(), x.max(), y.min(), y.max()
        if self._overlapping():
            return self.tree.query(box(lo_x, lo_y, hi_x, hi_y))
        b = self.bounds_xy
        return np.nonzero((b[:, 0] <= hi_x) & (b[:, 2] >= lo_x) & (b[:, 1] <= hi_y) & (b[:, 3] >= lo_y))[0]

    def terraces(self, k: np.ndarray) -> np.ndarray:
        """Terrace height per block, computed once at the block center."""
        out = self.terrace[k]
        miss = np.isnan(out)
        if miss.any():
            self.terrace[k[miss]] = self.blur(self.centers[k[miss], 0], self.centers[k[miss], 1])
            out = self.terrace[k]
        return out

    def block_one(self, x: float, y: float, pt) -> tuple:
        """`block_at` for one point (`pt` the same point as a shapely Point)."""
        if self.tree is None:
            return -1, 0.0
        for k in self._candidates(np.array([x]), np.array([y])):
            x0, y0, x1, y1 = self.bounds_xy[k]
            if x0 <= x <= x1 and y0 <= y <= y1 and shapely.contains_xy(self.blocks[int(k)], x, y):
                return int(k), float(shapely.distance(pt, self.blocks[int(k)].boundary))
        return -1, 0.0

    def block_at(self, x: np.ndarray, y: np.ndarray, pts=None) -> tuple:
        """Index of the terraced block under each point (-1 = none) and distance to its edge.

        `pts`: the same points as shapely points, when the caller has them already.
        """
        idx = np.full(len(x), -1, dtype=np.int64)
        dist = np.zeros(len(x))
        if self.tree is None or not len(x):
            return idx, dist
        if pts is None:
            pts = shapely.points(x, y)
        for k in self._candidates(x, y):
            x0, y0, x1, y1 = self.bounds_xy[k]
            sel = np.nonzero((idx < 0) & (x >= x0) & (x <= x1) & (y >= y0) & (y <= y1))[0]
            if not len(sel):
                continue
            poly = self.blocks[int(k)]
            hit = shapely.contains_xy(poly, x[sel], y[sel])
            sel = sel[hit]
            if not len(sel):
                continue
            idx[sel] = k
            dist[sel] = shapely.distance(pts[sel], poly.boundary)
        return idx, dist


class Ground:
    """The graded ground of every planned city, as a pure vectorized function of position."""

    def __init__(self, world, plans):
        cfg = world.cfg["ground"]
        self.terrain = world.terrain
        self.radius = float(cfg["radius"])
        self.lattice = float(cfg["lattice"])
        self.terrace_max = float(cfg["terrace_max"])
        self.edge = max(float(cfg["edge"]), 2.0 * float(world.cfg["tiles"]["terrain_step"]))
        self.terrace_max_area = float(cfg["terrace_max_area"])
        self.edge_band = float(cfg["edge_band"])
        self.step = float(world.cfg["tiles"]["terrain_step"])   # the terrain mesh's grid (mesh/tile.py)
        self.level_band = float(world.style.get("station", {}).get("level_band", 100.0))
        self.level_walk_step = float(world.style.get("station", {}).get("walk_step", 10.0))
        self.cities = [_City(p, self) for p in plans]
        self.area = unary_union([p.boundary for p in plans]) if plans else None
        if self.area is not None:
            shapely.prepare(self.area)
        surfaces, lifts = [], []
        for plan in plans:
            for st in plan.streets:
                surfaces.append(st.line.buffer(st.width / 2, cap_style="flat"))
                lifts.append(STREET_LIFT.get(st.kind, 0.24))
        self.street_lift = np.asarray(lifts, dtype=np.float64)
        self.street_tree = STRtree(surfaces) if surfaces else None
        streets_cfg = world.style.get("streets", {})
        self.curb_height = float(streets_cfg.get("curb_height", 0.15))
        self.walk_reach = float(streets_cfg.get("walk_reach", 0.05))
        walks = [w.polygon for plan in plans for w in getattr(plan, "walks", [])]
        self.walk_tree = STRtree(walks) if walks else None
        fronts = [w for plan in plans for w in getattr(plan, "walks", []) if w.kind == "seafront"]
        self.front_tree = STRtree([w.polygon for w in fronts]) if fronts else None   # the corniche's (prompt 36)
        self.front_edges = np.array([w.edge for w in fronts], dtype=object)
        self.front_box = shapely.total_bounds(self.front_tree.geometries) if fronts else None
        aprons = [b.apron for plan in plans for b in plan.buildings if getattr(b, "apron", None) is not None]
        self.apron_tree = STRtree(aprons) if aprons else None   # paved lot corners at cut corners (prompt 23)
        self.apron_reach = float(streets_cfg.get("apron_reach", 6.0))
        self.apron_cell = float(streets_cfg.get("apron_cell", 2.0))
        self._apron_tris = None                                  # their drawn triangles (lazy, _apron_drawn)
        cfg_port = world.style.get("port", {})                   # quays and harbor basins (prompt 34)
        self.harbors = [(p.port, p.port.zone.bounds) for p in plans if getattr(p, "port", None) is not None]
        self.port_band = float(cfg_port.get("level_band", 60.0))
        self.dredge_band = float(cfg_port.get("dredge_band", 60.0))
        self.depth = float(cfg_port.get("depth", 6.0))

    def walk_step(self, poly, step: float) -> float:
        """Meters between a walk's outline points: `step`, or the finer `[station] walk_step` where the
        ground bends round the station's level ground, so the drawn walk keeps its curb over the ribbon."""
        for city in self.cities:
            if city.level_zone is not None and city.level_zone.intersects(poly):
                return min(step, self.level_walk_step)
        for port, _bounds in self.harbors:            # the level band behind a quay bends the ground too
            if port.zone.intersects(poly):
                return min(step, self.level_walk_step)
        return step

    def _select(self, x: np.ndarray, y: np.ndarray) -> list:
        """(city, indices) for the points inside each city; cities never overlap."""
        inside = shapely.contains_xy(self.area, x, y)
        out = []
        for city in self.cities:
            x0, y0, x1, y1 = city.bounds
            sel = np.nonzero(inside & (x >= x0) & (x <= x1) & (y >= y0) & (y <= y1))[0]
            if len(sel):
                sel = sel[shapely.contains_xy(city.plan.boundary, x[sel], y[sel])]
            if len(sel):
                inside[sel] = False
                out.append((city, sel))
        return out

    def blur(self, x, y):
        """The blurred terrain under each point (nan outside every city), for checks and tests."""
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        out = np.full(x.shape, np.nan)
        if self.area is not None:
            xf, yf, of = np.ravel(x), np.ravel(y), np.ravel(out)
            for city, sel in self._select(xf, yf):
                of[sel] = city.blur(xf[sel], yf[sel])
        return out

    def _graded(self, city: _City, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """City ground at points inside `city`'s boundary: blur, terrace, then edge blend.

        The natural terrain is sampled only inside the edge band: deeper in, its weight is
        exactly 0, so skipping it changes no height and saves most of a tile's terrain noise.
        """
        blur = city.blur(x, y)
        out = blur.copy()
        pts = shapely.points(x, y)
        idx, dist = city.block_at(x, y, pts)
        hit = idx >= 0
        if hit.any():
            terrace = city.terraces(idx[hit])
            w = smoothstep(0.0, self.edge, dist[hit])
            out[hit] = blur[hit] + w * np.clip(terrace - blur[hit], -self.terrace_max, self.terrace_max)
        if city.level is not None:
            out = city.leveled(x, y, pts, out)
        edge = shapely.distance(pts, city.edge_line)
        b = smoothstep(0.0, self.edge_band, edge)
        near = b < 1.0
        if near.any():
            natural = np.asarray(self.terrain.height(x[near], y[near]), dtype=np.float64)
            out[near] = natural * (1.0 - b[near]) + out[near] * b[near]
        return out

    def _graded_one(self, city: _City, x: float, y: float) -> float:
        """`_graded` at one point with plain floats: the same operations in the same order."""
        blur = out = city.blur.one(x, y)
        pt = shapely.points(x, y)
        k, dist = city.block_one(x, y, pt)
        if k >= 0:
            terrace = float(city.terraces(np.array([k]))[0])
            w = _smoothstep(0.0, self.edge, dist)
            out = blur + w * min(max(terrace - blur, -self.terrace_max), self.terrace_max)
        if city.level is not None:
            core, (x0, y0, x1, y1), level, band = city.level
            if x0 <= x <= x1 and y0 <= y <= y1:
                t = min(max(float(shapely.distance(core, pt)) / band, 0.0), 1.0)
                w = 1.0 - t * t * t * (t * (6.0 * t - 15.0) + 10.0)
                out = out * (1.0 - w) + level * w
        b = _smoothstep(0.0, self.edge_band, float(shapely.distance(pt, city.edge_line)))
        if b < 1.0:
            natural = float(self.terrain.height(np.array([x]), np.array([y]))[0])
            out = natural * (1.0 - b) + out * b
        return out

    def _height_one(self, x: float, y: float) -> float:
        """`height` at one point: most dressing calls ask for one, and plain floats skip numpy's
        per-call overhead (same operations, same order, so the same bits)."""
        h = None
        if shapely.contains_xy(self.area, x, y):
            for city in self.cities:
                x0, y0, x1, y1 = city.bounds
                if x0 <= x <= x1 and y0 <= y <= y1 and shapely.contains_xy(city.plan.boundary, x, y):
                    h = self._graded_one(city, x, y)
                    break
        if h is None:
            h = float(self.terrain.height(np.array([x]), np.array([y]))[0])
        for _port, (x0, y0, x1, y1) in self.harbors:     # near a harbor: the same array code as `height`
            if x0 <= x <= x1 and y0 <= y <= y1:
                return float(self._harbor(np.array([x]), np.array([y]), np.array([h]))[0])
        return h

    def height(self, x, y):
        """Graded ground height in meters, in arrays out for arrays in (or a float for floats)."""
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        if self.area is None or x.size == 0:
            h = np.asarray(self.terrain.height(x, y), dtype=np.float64)
            return float(h) if h.ndim == 0 else h
        if x.size == 1 and y.size == 1:
            h = self._height_one(float(x.flat[0]), float(y.flat[0]))
            return h if x.ndim == 0 else np.full(x.shape, h)
        out = self._height(np.ravel(x), np.ravel(y))
        if x.ndim == 0:
            return float(out[0])
        return out.reshape(x.shape)

    def _height(self, xf: np.ndarray, yf: np.ndarray, side: str | None = None) -> np.ndarray:
        """`height` for flat arrays; `side` ("raised" or "sea") evaluates a harbor's ground as seen from one
        side of its walls, where the ground steps (the mesher draws the two sides of a wall apart)."""
        out = np.empty(len(xf))
        rest = np.ones(len(xf), dtype=bool)
        for city, sel in self._select(xf, yf):
            out[sel] = self._graded(city, xf[sel], yf[sel])
            rest[sel] = False
        if rest.any():
            out[rest] = self.terrain.height(xf[rest], yf[rest])
        return self._harbor(xf, yf, out, side) if self.harbors else out

    def side_height(self, x, y, side: str) -> np.ndarray:
        """Ground height on the "raised" side (quay, corniche) or the "sea" side of a harbor's walls."""
        xf = np.ravel(np.asarray(x, dtype=np.float64))
        yf = np.ravel(np.asarray(y, dtype=np.float64))
        if self.area is None or not len(xf):
            return np.asarray(self.terrain.height(xf, yf), dtype=np.float64)
        return self._height(xf, yf, side)

    def _harbor(self, x: np.ndarray, y: np.ndarray, h: np.ndarray, side: str | None = None) -> np.ndarray:
        """The ground changed by the quays (prompt 34, city/port.py): level on the core, blending back over
        the level band on the land side; the open sea dredged in the basins and off the quays, fading out."""
        for port, (x0, y0, x1, y1) in self.harbors:
            sel = np.nonzero((x >= x0) & (x <= x1) & (y >= y0) & (y <= y1))[0]
            if len(sel):
                sel = sel[shapely.contains_xy(port.zone, x[sel], y[sel])]
            if not len(sel):
                continue
            xs, ys, hs = x[sel], y[sel], h[sel].copy()
            core = shapely.contains_xy(port.core, xs, ys)
            if side is None:
                land = core | shapely.contains_xy(port.shore, xs, ys)
            else:
                land = np.full(len(sel), side == "raised")
            pts = shapely.points(xs, ys)
            if land.any():
                t = np.clip(shapely.distance(port.core, pts[land]) / self.port_band, 0.0, 1.0)
                w = 1.0 - t * t * t * (t * (6.0 * t - 15.0) + 10.0)      # smootherstep: no kink at either end
                hs[land] = np.where(w >= 1.0, port.level, hs[land] + w * (port.level - hs[land]))   # exact on the core
            sea = ~land
            if sea.any():
                t = np.clip(shapely.distance(port.dredge, pts[sea]) / self.dredge_band, 0.0, 1.0)
                w = 1.0 - t * t * t * (t * (6.0 * t - 15.0) + 10.0)
                hs[sea] = hs[sea] + w * (np.minimum(hs[sea], -self.depth) - hs[sea])
            h[sel] = hs
        return h

    def lift(self, x, y, reach: float = 0.0):
        """Highest street-ribbon lift at each point (0 where no street lies).

        With `reach`, streets up to that many meters away count too.
        """
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        out = np.zeros(x.shape)
        if self.street_tree is None or x.size == 0:
            return float(out) if out.ndim == 0 else out
        xf, yf, of = np.ravel(x), np.ravel(y), np.ravel(out)
        pts = shapely.points(xf, yf)
        if reach > 0.0:
            inp, hit = self.street_tree.query(pts, predicate="dwithin", distance=reach)
        else:
            inp, hit = self.street_tree.query(pts, predicate="intersects")
        if len(inp):
            np.maximum.at(of, inp, self.street_lift[hit])
        if out.ndim == 0:
            return float(of[0])
        return out

    def surface(self, x, y):
        """Top of what is drawn at each point: ground, street ribbon, or a raised walk.

        Overlapping streets take the highest ribbon; a sidewalk or promenade adds the curb
        height above that ribbon (see `walk_top`). Like `height`, this is a pure function of
        position, so neighbouring tiles agree on every shared point.
        """
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        h = np.asarray(self.height(x, y), dtype=np.float64)
        if (self.street_tree is None and self.walk_tree is None) or h.size == 0:
            return float(h) if h.ndim == 0 else h
        xf, yf, hf = np.ravel(x), np.ravel(y), np.ravel(h)
        lift = np.ravel(np.asarray(self.lift(xf, yf), dtype=np.float64))
        out = hf + lift
        pts = shapely.points(xf, yf)
        if self.walk_tree is not None:
            inp, _hit = self.walk_tree.query(pts, predicate="intersects")
            if len(inp):
                on = np.unique(inp)
                out[on] = self._walk_top(xf[on], yf[on], hf[on])
        if self.apron_tree is not None:
            inp, _hit = self.apron_tree.query(pts, predicate="intersects")
            if len(inp):
                on = np.unique(inp)
                out[on] = self._apron_drawn(xf[on], yf[on])
        if h.ndim == 0:
            return float(out[0])
        return out.reshape(h.shape)

    def drawn(self, x, y, corners=None):
        """Height of the terrain mesh as the tiles draw it, in arrays out for arrays in.

        The mesh samples `height` on a world-aligned grid of `terrain_step` cells and splits each
        cell into two triangles along its south-west to north-east diagonal (mesh/tile.terrain_mesh).
        On curved ground it can lie a few centimeters off `height`, up to about 0.2 m on steep
        terraces: thin things laid on open ground (garden paths, doorsteps) follow this instead.
        `corners(i, j)` may supply the heights at grid corners (i * step, j * step), from a cache.
        """
        x = np.asarray(x, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)
        s = self.step
        i, j = np.floor(np.ravel(x) / s).astype(np.int64), np.floor(np.ravel(y) / s).astype(np.int64)
        ci, cj = np.concatenate([i, i + 1, i, i + 1]), np.concatenate([j, j, j + 1, j + 1])
        h = corners(ci, cj) if corners is not None else self.height(ci * s, cj * s)
        h00, h10, h01, h11 = np.split(np.asarray(h, dtype=np.float64), 4)
        tx, ty = (np.ravel(x) - i * s) / s, (np.ravel(y) - j * s) / s
        out = np.where(tx >= ty, h00 + tx * (h10 - h00) + ty * (h11 - h10), h00 + ty * (h01 - h00) + tx * (h11 - h01))
        return float(out[0]) if np.ndim(x) == 0 else out.reshape(np.shape(x))

    def _walk_top(self, x: np.ndarray, y: np.ndarray, h: np.ndarray) -> np.ndarray:
        out = h + np.ravel(np.asarray(self.lift(x, y, self.walk_reach), dtype=np.float64)) + self.curb_height
        if self.front_tree is not None and len(x):
            self._front_top(x, y, out)
        return out

    def _front_top(self, x: np.ndarray, y: np.ndarray, out: np.ndarray) -> None:
        """On the corniche's seafront promenade (prompt 36) the top is level across: a point takes the walk top
        of the point of its stretch's curb line (`Walk.edge`) nearest to it, curb height above the ribbon there.
        A stretch's pieces share one curb line, so they meet at one height."""
        x0, y0, x1, y1 = self.front_box
        r = self.walk_reach
        sel = np.nonzero((x >= x0 - r) & (x <= x1 + r) & (y >= y0 - r) & (y <= y1 + r))[0]
        if not len(sel):
            return
        pts = shapely.points(x[sel], y[sel])
        inp, hit = self.front_tree.query(pts, predicate="dwithin", distance=r)
        if not len(inp):
            return
        first = np.unique(inp, return_index=True)[1]
        inp, hit = inp[first], hit[first]
        edges = self.front_edges[hit]
        q = shapely.get_coordinates(shapely.line_interpolate_point(edges, shapely.line_locate_point(edges, pts[inp])))
        hq = np.ravel(np.asarray(self.height(q[:, 0], q[:, 1]), dtype=np.float64))
        lift = np.ravel(np.asarray(self.lift(q[:, 0], q[:, 1], self.walk_reach), dtype=np.float64))
        out[sel[inp]] = hq + lift + self.curb_height

    def _apron_lift(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Street lift a paved lot corner takes: the lifts of the streets within `apron_reach`, weighted by
        (1 - d / reach)^2 / (d + 1 m)^2, so it blends smoothly between the two streets of a corner; within
        `walk_reach` of a street the highest such lift, exactly as the sidewalk it meets there."""
        out = np.zeros(len(x))
        if self.street_tree is None or not len(x):
            return out
        pts = shapely.points(x, y)
        inp, hit = self.street_tree.query(pts, predicate="dwithin", distance=self.apron_reach)
        if not len(inp):
            return out
        dist = shapely.distance(self.street_tree.geometries[hit], pts[inp])
        w = (1.0 - np.minimum(dist / self.apron_reach, 1.0)) ** 2 / (dist + 1.0) ** 2   # fades out at the reach
        num, den = np.zeros(len(x)), np.zeros(len(x))
        np.add.at(num, inp, w * self.street_lift[hit])
        np.add.at(den, inp, w)
        out = np.where(den > 0, num / np.maximum(den, 1e-12), 0.0)
        edge = dist <= self.walk_reach                     # on a sidewalk's edge: the sidewalk's own rule
        if edge.any():
            top = np.full(len(x), -np.inf)
            np.maximum.at(top, inp[edge], self.street_lift[hit[edge]])
            out = np.where(np.isfinite(top), top, out)
        return out

    def _apron_drawn(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Height of the paved lot corners as drawn: `apron_top` at the corners of their triangles
        (`apron_cells`, the same ones mesh/tile.apron_mesh draws), interpolated inside each one."""
        if self._apron_tris is None:
            tris = np.concatenate([apron_cells(p, self.apron_cell) for g in self.apron_tree.geometries
                                   for p in getattr(g, "geoms", [g])])
            z = self.apron_top(tris[..., 0].ravel(), tris[..., 1].ravel()).reshape(-1, 3)
            self._apron_tris = (tris, z, STRtree(shapely.polygons(tris)))
        tris, z, tree = self._apron_tris
        out = self.apron_top(x, y)                         # on an outline point no triangle claims
        inp, hit = tree.query(shapely.points(x, y), predicate="intersects")
        if len(inp):
            first = np.unique(inp, return_index=True)[1]
            inp, hit = inp[first], hit[first]
            a, b, c = tris[hit, 0], tris[hit, 1], tris[hit, 2]
            p = np.stack([x[inp], y[inp]], axis=1)
            v0, v1, v2 = b - a, c - a, p - a
            den = v0[:, 0] * v1[:, 1] - v0[:, 1] * v1[:, 0]
            u = (v2[:, 0] * v1[:, 1] - v2[:, 1] * v1[:, 0]) / den
            v = (v0[:, 0] * v2[:, 1] - v0[:, 1] * v2[:, 0]) / den
            zz = z[hit]
            out[inp] = zz[:, 0] + u * (zz[:, 1] - zz[:, 0]) + v * (zz[:, 2] - zz[:, 0])
        return out

    def apron_top(self, x, y):
        """Top of a paved lot corner (`Building.apron`) at points on it: as a sidewalk, curb above the
        ribbon of the streets beside it."""
        x = np.ravel(np.asarray(x, dtype=np.float64))
        y = np.ravel(np.asarray(y, dtype=np.float64))
        h = np.ravel(np.asarray(self.height(x, y), dtype=np.float64))
        return h + self._apron_lift(x, y) + self.curb_height

    def walk_top(self, x, y):
        """Top of a sidewalk or promenade at points known to lie on one (its outline included).

        A walk's edge on the block side lies on the street outline itself, where rounding can
        miss the street: walk points take the lift of any street within `walk_reach`, so no
        corner of a sidewalk drops under the asphalt.
        """
        x = np.ravel(np.asarray(x, dtype=np.float64))
        y = np.ravel(np.asarray(y, dtype=np.float64))
        return self._walk_top(x, y, np.ravel(np.asarray(self.height(x, y), dtype=np.float64)))


def apron_cells(poly, cell: float) -> np.ndarray:
    """(T, 3, 2) triangles of a paved lot corner: the polygon cut in `cell` m squares on the world grid,
    each piece triangulated, so the paving follows the ground and its two streets closely."""
    x0, y0, x1, y1 = poly.bounds
    xs = np.arange(math.floor(x0 / cell), math.ceil(x1 / cell)) * cell
    ys = np.arange(math.floor(y0 / cell), math.ceil(y1 / cell)) * cell
    cells = shapely.intersection(boxes(xs, ys, cell), poly)
    parts = [p for g in cells for p in getattr(g, "geoms", [g]) if p.geom_type == "Polygon" and p.area > 1e-6]
    tris = [triangulate(p) for p in parts]
    return np.concatenate(tris) if tris else np.zeros((0, 3, 2))


def boxes(xs: np.ndarray, ys: np.ndarray, cell: float) -> np.ndarray:
    """`box(x, y, x + cell, y + cell)` for every x in `xs`, then every y in `ys` (same rings, same order)."""
    x, y = (a.ravel() for a in np.meshgrid(xs, ys, indexing="ij"))
    x1, y1 = x + cell, y + cell
    return shapely.polygons(np.stack([np.stack(c, axis=-1) for c in
                                      ((x1, y), (x1, y1), (x, y1), (x, y), (x1, y))], axis=1).reshape(-1, 5, 2))


def terrain_cells(poly, step: float) -> np.ndarray:
    """(T, 3, 2) triangles of a polygon cut on the terrain mesh's own triangles (cells of `step` m on the
    world grid, split along their south-west to north-east diagonal, as `Ground.drawn` and the tile mesher
    do), so a cap draped on `Ground.drawn` lies in the terrain's planes exactly (villa gardens, prompt 24)."""
    x0, y0, x1, y1 = poly.bounds
    i, j = np.meshgrid(np.arange(math.floor(x0 / step), math.ceil(x1 / step)),
                       np.arange(math.floor(y0 / step), math.ceil(y1 / step)), indexing="ij")
    i, j = i.ravel() * step, j.ravel() * step
    c00, c10, c11, c01 = (np.stack([i + dx, j + dy], axis=1) for dx, dy in ((0, 0), (step, 0), (step, step), (0, step)))
    rings = np.concatenate([np.stack([c00, c10, c11, c00], axis=1), np.stack([c00, c11, c01, c00], axis=1)])
    pieces = shapely.intersection(shapely.polygons(rings), poly)
    parts = [p for g in pieces for p in shapely.get_parts(g) if p.geom_type == "Polygon" and p.area > 1e-6]
    tris = [triangulate(p) for p in parts]
    return np.concatenate(tris) if tris else np.zeros((0, 3, 2))
