"""Rivers and lakes from the shape of the land (prompt 59).

A pure function of the terrain, no randomness. On a coarse grid (`[rivers] cell`) a
priority flood (Barnes et al. 2014, with an epsilon gradient) runs inward from the sea and
the map border: each land cell drains to the cell the flood reached it from, so every cell
drains, even on filled flats. Filled basins deep and wide enough are lakes; in steppe and
desert they are endorheic (salt) basins where rivers end. Flow is the catchment area weighted
by moisture; rivers follow the cells where it passes `[rivers] min_flow`.
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


def drainage(terrain, cfg: dict) -> tuple:
    """(rivers, lakes) of the whole country."""
    rc = cfg["rivers"]
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
    flow, _ = _accumulate(np.argsort(-filled.ravel(), kind="stable"), recv, weight, np.full(n * n, area))
    labels, basins = _basins(np.where(sea, 0.0, filled - H), H, filled, biome, flow.reshape(n, n), cell, rc)
    lake_id = np.full(n * n, -1, dtype=np.int64)
    salt = np.zeros(n * n, dtype=bool)
    lakes = []
    boxes = ndimage.find_objects(labels)
    flat = filled.ravel()
    gid = np.arange(n * n).reshape(n, n)
    for k, (lab, level, is_salt) in enumerate(basins):
        sy, sx = boxes[lab - 1]
        m, h, g = labels[sy, sx] == lab, H[sy, sx], gid[sy, sx]
        water = m & (h <= level)
        if is_salt:                     # endorheic: the basin drains to its lake, which keeps the water
            # a tiny epsilon keeps every basin cell below the spill, so `flat` still falls downstream
            sub_f, sub_r = _flood(h, water, wall=~m, border=False, eps=EPS * 1e-3)
            dry_cells = (m & ~water).ravel()
            gi = g.ravel()
            recv[gi[dry_cells]] = gi[sub_r[dry_cells]]
            flat[gi[m.ravel()]] = np.where(dry_cells, sub_f.ravel(), h.ravel())[m.ravel()]
            recv[g[water]] = -1
        lake_id[g[water]] = k
        salt[g[water]] = is_salt
        lakes.append(_lake(k, water, h, c[sx], c[sy], level, is_salt))
    # every cell lies higher in `flat` than the cell it drains to: highest first is upstream first
    flow, catch = _accumulate(np.argsort(-flat, kind="stable"), recv, weight, np.full(n * n, area))
    river = (~sea.ravel()) & (lake_id < 0) & (flow >= float(rc["min_flow"]))
    chains = _chains(recv, flow, river, lake_id, n)
    rivers = _rivers(chains, flat, flow, catch, sea.ravel(), salt, lake_id, c, n, rc)
    return rivers, lakes


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


def _basins(depth, H, filled, biome, flow, cell, rc) -> tuple:
    """Labels of the filled basins and the lakes among them: [(label, level, salt)].

    A lake spreads until evaporation from its surface (`lake_area_per_flow` km2 per km2 of
    inflow) takes all the water that reaches it: a basin of wet country that fills up spills
    over and its river goes on; in steppe and desert the basin keeps its water (endorheic)."""
    labels, count = ndimage.label(depth > 0.01, np.ones((3, 3), dtype=bool))
    min_cells = float(rc["lake_min_area"]) * 1e6 / (cell * cell)
    cells = np.bincount(labels.ravel(), minlength=count + 1)
    ids = np.flatnonzero(cells >= min_cells)
    ids = ids[ids > 0]                  # smaller pits just drain
    if len(ids) == 0:
        return labels, []
    deepest = ndimage.maximum(depth, labels, ids)
    spill = ndimage.maximum(filled, labels, ids)
    inflow = ndimage.maximum(flow, labels, ids)
    bottom = ndimage.minimum_position(H, labels, ids)
    out = []
    for k in range(len(ids)):
        size = cells[ids[k]]
        if deepest[k] < float(rc["lake_min_depth"]):
            continue                    # a shallow pit: it just drains
        wet = math.ceil(float(rc["lake_area_per_flow"]) * inflow[k] * 1e6 / (cell * cell))
        is_salt = int(biome[bottom[k]]) in (STEPPE, DESERT)
        if wet < min_cells or (not is_salt and wet < size):
            continue                    # too little water to keep a lake: a damp hollow that drains
        if wet >= size:
            level = float(spill[k])
        else:
            level = float(np.sort(H[labels == ids[k]])[wet - 1])
        out.append((int(ids[k]), level, is_salt))
    return labels, out


def _lake(k, mask, H, cx, cy, level, is_salt) -> Lake:
    """The shore of one basin (its box of the grid): where the ground inside it meets `level`."""
    level = level + 1e-6                # the shore around every cell at or below the level
    f = np.where(mask, H, level + 50.0)
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


def _rivers(chains, filled, flow, catch, sea, salt, lake_id, c, n, rc) -> list:
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
        z = np.minimum.accumulate(filled[cells])
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
        out.append([new_id[k], xy, w, float(f[-1]), bool(seasonal), z, mouth, into])
    smooth = {r[0]: _smooth(r[1], r[2], r[5]) for r in out}
    rivers = []
    for rid, _, _, fl, seas, _, mouth, into in out:
        xy, w, z = smooth[rid]
        if mouth == "river" and into is not None:
            xy, z = _snap(xy, z, smooth[into][0], smooth[into][2])
        rivers.append(River(rid, xy, w, fl, seas, z, mouth, into))
    return rivers


def _smooth(xy, w, z, rounds: int = 2) -> tuple:
    """Rounded D8 staircase: a moving average, then Chaikin corner cutting; the ends stay put.

    Every new value is an average of neighbors, so a profile that never rises stays so."""
    if len(xy) < 3:
        return xy, w, z
    a = np.column_stack([xy, w, z])
    for _ in range(2):
        a[1:-1, :2] = (a[:-2, :2] + a[1:-1, :2] + a[2:, :2]) / 3.0
    for _ in range(rounds):
        q = 0.75 * a[:-1] + 0.25 * a[1:]
        r = 0.25 * a[:-1] + 0.75 * a[1:]
        mid = np.empty((2 * len(q), a.shape[1]))
        mid[0::2], mid[1::2] = q, r
        a = np.vstack([a[:1], mid, a[-1:]])
    return a[:, :2], a[:, 2], np.minimum.accumulate(a[:, 3])


def _snap(xy, z, main_xy, main_z) -> tuple:
    """A tributary ends on its main river's smoothed line. Its last height is the main bed there, unless
    the point before is lower: the profile never rises, so then it ends below the main bed."""
    line = LineString(main_xy)
    s = line.project(Point(xy[-1]))
    p = line.interpolate(s)
    seg = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(main_xy, axis=0).T))])
    zm = float(np.interp(s, seg, main_z))
    xy = xy.copy()
    xy[-1] = (p.x, p.y)
    z = z.copy()
    z[-1] = max(min(z[-1], z[-2] if len(z) > 1 else z[-1]), zm)
    return xy, np.minimum.accumulate(z)
