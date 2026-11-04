"""Rivers and lakes from the shape of the land (prompt 59).

A pure function of the terrain, no randomness. On a coarse grid (`[rivers] cell`) a
priority flood (Barnes et al. 2014, with an epsilon gradient) runs inward from the sea and
the map border: each land cell drains to the cell the flood reached it from, so every cell
drains, even on filled flats. Filled basins deep and wide enough are lakes; in steppe and
desert they are always closed (salt) basins where rivers end, and a hollow left inside one
counts as a basin in its turn. Flow is the catchment area weighted by moisture; rivers follow
the cells where it passes `[rivers] min_flow`.
"""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass

import contourpy
import numpy as np
from scipy import ndimage
from shapely.geometry import LineString, Point, Polygon

from .terrain import DESERT, STEPPE, classify

EPS = 1e-4   # meters the flood raises each cell over the one it drains to on a filled flat


@dataclass
class River:
    id: int
    coords: np.ndarray   # (N, 2) meters, from source to mouth
    widths: np.ndarray   # (N,) meters
    flow: float          # moisture-weighted catchment at the mouth, km2
    seasonal: bool       # an oued of dry country, dry most of the year
    profile: np.ndarray  # (N,) bed height in meters, never rising downstream
    mouth: str           # sea | lake | basin | border | river
    into: int | None     # the river or lake it ends in (mouth river, lake or basin)

    def to_json(self) -> dict:
        return {"id": self.id, "coords": np.round(self.coords, 1).tolist(),
                "widths": np.round(self.widths, 1).tolist(), "flow": round(self.flow, 2),
                "seasonal": self.seasonal, "profile": np.round(self.profile, 2).tolist(),
                "mouth": self.mouth, "into": self.into}


@dataclass
class Lake:
    id: int
    polygon: np.ndarray  # (N, 2) meters, the shore (closed ring)
    level: float         # water (or salt crust) height in meters
    salt: bool           # an endorheic basin of dry country

    def to_json(self) -> dict:
        return {"id": self.id, "polygon": np.round(self.polygon, 1).tolist(),
                "level": round(self.level, 2), "salt": self.salt}


@dataclass
class _Routing:
    """Where the water of each grid cell goes (cells numbered row by row, `n` to a side)."""
    n: int
    c: np.ndarray        # (n,) the cell centers' x (and y), meters
    sea: np.ndarray      # (n * n,) bool
    flat: np.ndarray     # (n * n,) the flood's heights, closed basins re-flooded: each cell above its `recv`
    recv: np.ndarray     # (n * n,) the cell each cell drains to, -1 for the sea, a salt lake and the map border
    flow: np.ndarray     # (n * n,) rain-weighted catchment, km2
    catch: np.ndarray    # (n * n,) plain catchment, km2
    lake_id: np.ndarray  # (n * n,) the lake on each cell, -1 for none
    salt: np.ndarray     # (n * n,) bool: a salt lake's cell
    lakes: list


def drainage(terrain, cfg: dict) -> tuple:
    """(rivers, lakes) of the whole country."""
    rc = cfg["rivers"]
    g = _routing(terrain, rc)
    river = (~g.sea) & (g.lake_id < 0) & (g.flow >= float(rc["min_flow"]))
    return _rivers(_chains(g.recv, g.flow, river, g.lake_id, g.n), g, terrain, rc), g.lakes


def _routing(terrain, rc: dict) -> _Routing:
    """The drainage of the grid: the flood, then lakes round by round. The rest of a closed basin is re-flooded
    from its lake, and a hollow left in it that meets the same two thresholds is a basin of its own (water cannot
    climb its rim), so each round works on the flow and heights the last one left, until a round adds no lake."""
    size = terrain.size
    n = max(8, int(math.ceil(size / float(rc["cell"]))))
    cell = size / n
    c = (np.arange(n) + 0.5) * cell
    X, Y = np.meshgrid(c, c)            # row = y index, column = x index
    H = terrain.height(X, Y)
    M = terrain.moisture(X, Y, H)
    sea = H <= 0.0
    filled, recv = _flood(H, sea)
    gy, gx = np.gradient(H, cell)
    biome = classify(H, np.hypot(gx, gy), M)
    area = cell * cell / 1e6
    dry = float(rc["dry_weight"])       # desert storms still feed oueds
    weight = np.where(sea, 0.0, dry + (1.0 - dry) * M).ravel() * area
    lake_id = np.full(n * n, -1, dtype=np.int64)
    salt = np.zeros(n * n, dtype=bool)
    lakes = []
    flat = filled.ravel()
    gid = np.arange(n * n).reshape(n, n)
    while True:
        # every cell lies higher in `flat` than the cell it drains to: highest first is upstream first
        flow, catch = _accumulate(np.argsort(-flat, kind="stable"), recv, weight, np.full(n * n, area))
        depth = np.where(sea | (lake_id.reshape(n, n) >= 0), 0.0, flat.reshape(n, n) - H)
        labels, basins = _basins(depth, H, biome, flow.reshape(n, n), cell, rc)
        if not basins:                  # a pit that failed once fails again, so this ends
            return _Routing(n, c, sea.ravel(), flat, recv, flow, catch, lake_id, salt, lakes)
        boxes = ndimage.find_objects(labels)
        for lab, wet, is_salt in basins:
            sy, sx = boxes[lab - 1]
            m, h, g = labels[sy, sx] == lab, H[sy, sx], gid[sy, sx]
            k = len(lakes)
            water, level = _water(h, m, wet, float(flat[g][m].max()))
            if is_salt:                 # endorheic: the whole basin drains to its lake, which keeps the water
                # a tiny epsilon keeps every basin cell below the spill, so `flat` still falls downstream
                sub_f, sub_r = _flood(h, water, wall=~m, border=False, eps=EPS * 1e-3)
                dry_cells = (m & ~water).ravel()
                gi = g.ravel()
                recv[gi[dry_cells]] = gi[sub_r[dry_cells]]
                flat[gi[m.ravel()]] = np.where(dry_cells, sub_f.ravel(), h.ravel())[m.ravel()]
                recv[g[water]] = -1
            lake_id[g[water]] = k
            salt[g[water]] = is_salt
            wy, wx = slice(max(sy.start - 1, 0), sy.stop + 1), slice(max(sx.start - 1, 0), sx.stop + 1)
            lakes.append(_lake(k, lake_id.reshape(n, n)[wy, wx] == k, H[wy, wx], c[wx], c[wy], level, is_salt))


def _flood(H: np.ndarray, sea: np.ndarray, wall=None, border: bool = True, eps: float = EPS) -> tuple:
    """Priority flood from the water (`sea`) and the map border: (filled heights, receivers).

    `wall` cells are left out; `border=False` keeps the grid's edge from draining."""
    n_rows, n_cols = H.shape
    w = n_cols + 2                      # padded grid: a ring of visited cells spares bounds checks
    closed = np.ones((n_rows + 2, w), dtype=bool)
    closed[1:-1, 1:-1] = sea if wall is None else sea | wall
    open_pad = np.zeros_like(closed)
    open_pad[1:-1, 1:-1] = ~closed[1:-1, 1:-1]
    water = np.zeros_like(closed)
    water[1:-1, 1:-1] = sea
    hp = np.zeros(closed.shape)
    hp[1:-1, 1:-1] = H
    near_land = ndimage.binary_dilation(open_pad, np.ones((3, 3), dtype=bool)) & water
    edge = np.zeros_like(closed)
    if border:
        edge[1, 1:-1] = edge[-2, 1:-1] = edge[1:-1, 1] = edge[1:-1, -2] = True
        edge &= open_pad
    visited = (closed | edge).ravel().tolist()
    h = hp.ravel().tolist()
    filled = list(h)
    recv = [-1] * closed.size
    heap = [(h[i], i) for i in np.flatnonzero(near_land.ravel() | edge.ravel()).tolist()]
    heapq.heapify(heap)
    offsets = (-w - 1, -w, -w + 1, -1, 1, w - 1, w, w + 1)
    push, pop = heapq.heappush, heapq.heappop
    while heap:
        f, i = pop(heap)
        for o in offsets:
            j = i + o
            if visited[j]:
                continue
            visited[j] = True
            fj = h[j]
            if fj < f + eps:
                fj = f + eps
            filled[j] = fj
            recv[j] = i
            push(heap, (fj, j))
    # back to the unpadded grid
    idx = np.arange(closed.size).reshape(closed.shape)[1:-1, 1:-1].ravel()
    to_inner = np.full(closed.size, -1, dtype=np.int64)
    to_inner[idx] = np.arange(n_rows * n_cols)
    rp = np.asarray(recv, dtype=np.int64)
    recv_inner = np.where(rp[idx] >= 0, to_inner[np.maximum(rp[idx], 0)], -1)
    return np.asarray(filled)[idx].reshape(n_rows, n_cols), recv_inner


def _basins(depth, H, biome, flow, cell, rc) -> tuple:
    """Labels of the filled basins and the lakes among them: [(label, cells of water, salt)].

    Water cannot drain out of a hollow, so a basin of wet country is a lake up to its spill and
    its river goes on from there. In steppe and desert every basin keeps its water (endorheic):
    its lake spreads until evaporation from its surface (`lake_area_per_flow` km2 per km2 of
    inflow) takes all the water that reaches it, in `lake_min_area` at the least."""
    labels, count = ndimage.label(depth > float(rc["basin_depth"]), np.ones((3, 3), dtype=bool))
    min_cells = float(rc["lake_min_area"]) * 1e6 / (cell * cell)
    cells = np.bincount(labels.ravel(), minlength=count + 1)
    ids = np.flatnonzero(cells >= min_cells)
    ids = ids[ids > 0]                  # smaller pits just drain
    if len(ids) == 0:
        return labels, []
    deepest = ndimage.maximum(depth, labels, ids)
    inflow = ndimage.maximum(flow, labels, ids)
    bottom = ndimage.minimum_position(H, labels, ids)
    out = []
    for k in range(len(ids)):
        size = cells[ids[k]]
        if deepest[k] < float(rc["lake_min_depth"]):
            continue                    # a shallow pit: it just drains
        is_salt = int(biome[bottom[k]]) in (STEPPE, DESERT)
        balance = math.ceil(float(rc["lake_area_per_flow"]) * inflow[k] * 1e6 / (cell * cell))
        wet = max(balance, math.ceil(min_cells)) if is_salt else int(size)
        out.append((int(ids[k]), wet, is_salt))
    return labels, out


def _water(h, m, wet: int, spill: float) -> tuple:
    """(cells, level) of a basin's lake (`m` the basin in its box of the grid): the water around the basin's
    bottom, at the lowest level that covers `wet` cells or at the spill. Its cells are 4-connected, so its shore
    is one ring; the hollows of the basin it does not reach stay out, for the next round of `_routing`."""
    bottom = np.unravel_index(np.argmin(np.where(m, h, np.inf)), h.shape)

    def pocket(level):
        parts, _ = ndimage.label(m & (h <= level))
        return parts == parts[bottom]

    heights = np.sort(h[m])
    if wet >= len(heights):
        return pocket(spill), spill
    lo, hi = wet - 1, len(heights) - 1
    while lo < hi:                      # the lowest level whose pocket covers `wet` cells
        mid = (lo + hi) // 2
        if np.count_nonzero(pocket(heights[mid])) >= wet:
            hi = mid
        else:
            lo = mid + 1
    return pocket(heights[lo]), float(heights[lo])


def _lake(k, mask, H, cx, cy, level, is_salt) -> Lake:
    """The shore of one lake (`mask`, in a box of the grid one cell wider): where the ground meets `level`."""
    level = level + 1e-6                # the shore around every cell at or below the level
    f = np.where(mask, H, np.maximum(H, level + 1.0))   # other hollows under the level stay out
    f = np.pad(f, 1, constant_values=level + 50.0)
    step = float(cx[1] - cx[0]) if len(cx) > 1 else float(cy[1] - cy[0])
    gx = np.concatenate([[cx[0] - step], cx, [cx[-1] + step]])
    gy = np.concatenate([[cy[0] - step], cy, [cy[-1] + step]])
    gen = contourpy.contour_generator(gx, gy, f, fill_type="OuterOffset")
    points, offsets = gen.filled(float(f.min()) - 1.0, level)
    best, ring = 0.0, None
    for pts, off in zip(points, offsets):
        outer = pts[off[0]:off[1]]
        if len(outer) >= 4:
            a = Polygon(outer).area
            if a > best:
                best, ring = a, outer
    if ring is None:                    # the basin is narrower than the contour can show: its deepest cell
        i, j = np.unravel_index(np.argmin(np.where(mask, H, np.inf)), H.shape)
        ring = np.asarray(Point(cx[j], cy[i]).buffer(step * 0.5, 4).exterior.coords)
    return Lake(k, np.asarray(ring), level, is_salt)


def _accumulate(order, recv, weight, area) -> tuple:
    """Moisture-weighted flow and plain catchment area (km2) of every cell; `order` runs upstream first."""
    rl = recv.tolist()
    flow, catch = weight.tolist(), area.tolist()
    for i in order.tolist():
        r = rl[i]
        if r >= 0:
            flow[r] += flow[i]
            catch[r] += catch[i]
    return np.asarray(flow), np.asarray(catch)


def _chains(recv, flow, river, lake_id, n) -> list:
    """Cell paths [(cells, mouth cell or None, kind)] from each source down to the mouth or the junction."""
    rl, fl, rv = recv.tolist(), flow.tolist(), river.tolist()
    best = [-1] * (n * n)               # the upstream cell with the biggest flow
    for i in range(n * n):
        r = rl[i]
        if r >= 0 and (best[r] < 0 or fl[i] > fl[best[r]]):
            best[r] = i
    chains = []
    for i in np.flatnonzero(river).tolist():
        b = best[i]
        if b >= 0 and rv[b]:
            continue                    # not a source: the main stem comes from upstream
        path = [b, i] if b >= 0 and lake_id[b] >= 0 else [i]   # a lake's outlet starts at the shore
        cur, kind = i, "border"
        while True:
            r = rl[cur]
            if r < 0:
                break                   # a border cell: the river leaves the map
            path.append(r)
            if not rv[r]:
                kind = "water"          # sea, lake or basin
                break
            if best[r] != cur:
                kind = "river"
                break
            cur = r
        chains.append((path, kind))
    return chains


def _rivers(chains, g: _Routing, terrain, rc: dict) -> list:
    flow, catch, sea, salt, lake_id, c, n = g.flow, g.catch, g.sea, g.salt, g.lake_id, g.c, g.n

    def own(path, kind):                # the chain's own river cells
        return path[(1 if lake_id[path[0]] >= 0 else 0):(None if kind == "border" else -1)]

    cell_of = {i: k for k, (path, kind) in enumerate(chains) for i in own(path, kind)}
    min_points = int(rc["min_points"])
    targets = {cell_of.get(path[-1]) for path, kind in chains if kind == "river"}
    keep = [k for k, (path, kind) in enumerate(chains) if len(path) >= min_points or k in targets]
    keep.sort(key=lambda k: (-flow[own(*chains[k])[-1]], chains[k][0][0]))   # biggest rivers first
    new_id = {k: rid for rid, k in enumerate(keep)}
    k_width, w_min, w_max = float(rc["width_k"]), float(rc["width_min"]), float(rc["width_max"])
    out = []
    for k in keep:
        path, kind = chains[k]
        cells = np.asarray(path)
        last = own(path, kind)[-1]
        dry = float(rc["dry_weight"])   # flow / catchment is the catchment's mean rain weight
        seasonal = flow[last] / catch[last] < dry + (1.0 - dry) * float(rc["seasonal_moisture"])
        xy = np.column_stack([c[cells % n], c[cells // n]])
        f = flow[cells].copy()
        if kind != "border":
            f[-1] = f[-2] if len(f) > 1 else f[-1]   # the mouth cell's own flow is the water's
        if lake_id[cells[0]] >= 0:
            f[0] = f[1]
        w = np.clip(k_width * np.sqrt(f), w_min, w_max) * (float(rc["oued_scale"]) if seasonal else 1.0)
        end = int(cells[-1])
        if kind == "border":
            mouth, into = "border", None
        elif kind == "river":
            mouth, into = "river", new_id.get(cell_of.get(end))
        elif sea[end]:
            mouth, into = "sea", None
        else:
            mouth, into = ("basin" if salt[end] else "lake"), int(lake_id[end])
        out.append((new_id[k], xy, w, float(f[-1]), bool(seasonal), mouth, into))
    lines = {r[0]: _smooth(r[1], r[2]) for r in out}
    beds = _beds(out, lines, g, terrain)
    rivers = []
    for rid, _, _, fl, seas, mouth, into in out:
        xy, w = lines[rid]
        z = beds[rid]
        if mouth == "river" and into is not None:
            xy, z = _snap(xy, z, lines[into][0], beds[into])
        rivers.append(River(rid, xy, w, fl, seas, z, mouth, into))
    return rivers


def _smooth(xy, w, rounds: int = 2) -> tuple:
    """Rounded D8 staircase: a moving average, then Chaikin corner cutting; the ends stay put."""
    if len(xy) < 3:
        return xy, w
    a = np.column_stack([xy, w])
    for _ in range(2):
        a[1:-1, :2] = (a[:-2, :2] + a[1:-1, :2] + a[2:, :2]) / 3.0
    for _ in range(rounds):
        q = 0.75 * a[:-1] + 0.25 * a[1:]
        r = 0.25 * a[:-1] + 0.75 * a[1:]
        mid = np.empty((2 * len(q), a.shape[1]))
        mid[0::2], mid[1::2] = q, r
        a = np.vstack([a[:1], mid, a[-1:]])
    return a[:, :2], a[:, 2]


def _beds(out, lines, g: _Routing, terrain) -> dict:
    """{river id: bed height along its smoothed line}, tributaries first (ids run from the biggest river down).

    The highest beds that never rise, never lie above the ground and take every tributary in: valleys can
    only be cut into the ground, never lifted out of it. So where a river crosses a pit too small for a lake it
    goes down to the floor and cuts through the rim, and its main river stays below it from their junction on.
    Over a lake the bed is `flat`: the lake's level (a fresh lake's outlet starts there), a salt lake's floor."""
    step = g.c[1] - g.c[0]
    joins, beds = {}, {}
    for rid, _, _, _, _, mouth, into in reversed(out):
        xy = lines[rid][0]
        i, j = np.clip(np.floor(xy / step).astype(np.int64), 0, g.n - 1).T
        cells = j * g.n + i
        z = np.where(g.lake_id[cells] >= 0, g.flat[cells], terrain.height(xy[:, 0], xy[:, 1]))
        for at, low in joins.get(rid, []):
            z[at] = min(z[at], low)
        beds[rid] = np.minimum.accumulate(z)
        if mouth == "river" and into is not None:
            main = lines[into][0]
            at = np.searchsorted(_along(main), LineString(main).project(Point(xy[-1])))
            joins.setdefault(into, []).append((max(int(at) - 1, 0), float(beds[rid][-1])))
    return beds


def _along(xy) -> np.ndarray:
    return np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(xy, axis=0).T))])


def _snap(xy, z, main_xy, main_z) -> tuple:
    """A tributary ends on its main river's smoothed line, on the main bed there (`_beds` keeps that bed
    no higher than the tributary's, so its profile still never rises)."""
    line = LineString(main_xy)
    s = line.project(Point(xy[-1]))
    p = line.interpolate(s)
    xy = xy.copy()
    xy[-1] = (p.x, p.y)
    z = z.copy()
    z[-1] = float(np.interp(s, _along(main_xy), main_z))
    return xy, z
