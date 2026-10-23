"""Impasses: dead-end lanes cut through a block to the lots that have no street (prompt 20.2).

A lot is landlocked when the house on it would have no wall at least `min_front` m long with a
street in front of it, where the dresser looks for one (`served`). Such lots are reached the way
a hara is: along the lines between lots, from the block's street side, nearest lots first, later
lots branching off an impasse already cut, so neighbours share one dead end and the lanes grow
like a tree. A lane runs along a whole side of the lot it serves, so the door may stand anywhere
on that wall.

A lane keeps half its width plus `MARGIN` away from the block's edge except where it leaves a
mouth, and its mouth meets exactly one street, so it never joins two streets. Lots it leaves
smaller than `min_lot` are dropped; a lot no lane reaches within `max_length` joins a neighbour
that has a door.

Every block is independent and has its own random stream, but all blocks advance together in
rounds (one lane per block per round), so each step is one vectorized call for the whole city
instead of one call per block: the per-block version cost 9 s on the full capital.
"""
from __future__ import annotations

import numpy as np
import shapely
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from shapely.geometry import LineString
from shapely.strtree import STRtree

from .geo import largest
from .model import Parcel, Street

INSET = 0.15     # a house stands this far inside its lot (buildings._inset)
REACH = 1.6      # the dresser looks for a street this far in front of a wall (Dresser.walls)
GRID = 0.01      # lot outlines are snapped to this grid so neighbouring lots share exact corners
MARGIN = 0.2     # a lane keeps this far (beyond half its width) from the block's edge
NEAR = 0.3       # a mouth node lies this close to its street's surface
SPAN = 1 << 20   # grid steps per axis in one block's key space (10 km)
BLOCK = 1 << 40  # node key = block position * BLOCK + local x * SPAN + local y


def served(polys, min_front: float, tree=None, souk=None, souk_front: float = 0.0, lanes=None) -> np.ndarray:
    """True for each lot whose house would have a wall at least `min_front` m long facing a street.

    The walls are the lot inset by 0.15 m, as `buildings._inset` makes a house, and a wall faces a
    street when a surface lies 1.6 m in front of its middle, as `Dresser.walls` looks. Streets are
    the surfaces in `tree` (an STRtree; `souk` marks its souks, which need `souk_front` m of wall:
    the shop takes the middle and the house door must fit beside it) and in `lanes` (an STRtree).
    """
    out = np.zeros(len(polys), dtype=bool)
    if not len(polys):
        return out
    fps = shapely.buffer(np.asarray(polys, dtype=object), -INSET, join_style="mitre")
    for k in np.nonzero(shapely.get_type_id(fps) != 3)[0]:       # split or emptied by the inset
        fps[k] = largest(fps[k])
    keep_fp = np.array([f is not None and not f.is_empty for f in fps])
    if not keep_fp.any():
        return out
    rings = shapely.get_exterior_ring(fps[keep_fp])
    owner = np.nonzero(keep_fp)[0]
    xy, idx = shapely.get_coordinates(rings, return_index=True)
    same = idx[:-1] == idx[1:]
    a, b, own = xy[:-1][same], xy[1:][same], idx[:-1][same]
    d = b - a
    length = np.hypot(d[:, 0], d[:, 1])
    keep = length >= min_front
    a, d, length, own = a[keep], d[keep], length[keep], own[keep]
    if not len(a):
        return out
    sign = np.where(shapely.is_ccw(rings)[own], 1.0, -1.0)   # outward = right of a counter-clockwise ring
    n = np.stack([d[:, 1], -d[:, 0]], 1) / length[:, None] * sign[:, None]
    probe = shapely.points(a + d / 2 + n * REACH)
    hit = np.zeros(len(a), dtype=bool)
    if tree is not None:
        inp, item = tree.query(probe, predicate="within")
        good = np.ones(len(inp), dtype=bool) if souk is None else ~souk[item] | (length[inp] >= souk_front)
        hit[inp[good]] = True
    if lanes is not None:
        hit[lanes.query(probe, predicate="within")[0]] = True
    out[owner[own[hit]]] = True
    return out


def cut_impasses(ctx, blocks, districts, parcels, streets, used=frozenset()) -> tuple:
    """(parcels, used, impasse streets): lanes to every landlocked lot of the districts in `[impasse]`.

    Runs after the lots and the neighbourhood mosques' lots (`used`, never cut) and before the
    buildings. Returns new lists: kept lots in their old order and `used` renumbered to match;
    the lanes come block by block, each block's in the order they were cut.
    """
    table = ctx.style.get("impasse", {})
    kinds = {k for k, v in table.items() if isinstance(v, dict)}
    groups: dict = {}
    fixed: dict = {}
    for i, p in enumerate(parcels):
        if p.block >= 0 and districts[p.district].kind in kinds:
            (fixed if i in used else groups).setdefault(p.block, []).append(i)
    if not groups or not streets:
        return parcels, set(used), []
    surfaces = shapely.buffer(np.array([st.line for st in streets], dtype=object),
                              np.array([st.width for st in streets]) / 2, cap_style="flat")
    tree = STRtree(surfaces)
    souk = np.array([st.kind == "souk" for st in streets], dtype=bool)
    min_front = float(table.get("min_front", 3.0))
    souk_front = float(table.get("souk_front", min_front))
    order = [i for b in sorted(groups) for i in groups[b]]
    ok = dict(zip(order, served([parcels[i].polygon for i in order], min_front, tree, souk, souk_front)))
    todo = [b for b in sorted(groups) if not all(ok[i] for i in groups[b])]
    if not todo:
        return parcels, set(used), []
    net = _Network(ctx, todo, blocks, districts, groups, fixed, parcels, ok, streets, surfaces, tree, souk, table)
    net.run()
    net.merge()
    polys = dict(zip(net.lot_ids, net.poly))
    reached = {i for i, now, before in zip(net.lot_ids, net.ok, net.ok0) if now and not before}
    out, new_index = [], {}
    for i, p in enumerate(parcels):
        poly = polys.get(i, p.polygon)
        if poly is None:
            continue
        new_index[i] = len(out)
        out.append(Parcel(poly, p.district, p.frontage or i in reached, p.block))
    lanes = [net.lanes[j] for j in sorted(range(len(net.lanes)), key=lambda j: (net.lane_blk[j], j))]
    return out, {new_index[i] for i in used if i in new_index}, lanes


class _Network:
    """The lot lines of every block with landlocked lots, as one graph, and the lanes cut in it."""

    def __init__(self, ctx, todo, blocks, districts, groups, fixed, parcels, ok, streets, surfaces, tree,
                 souk, table):
        self.tree, self.souk = tree, souk
        self.surfaces = surfaces
        self.lines = np.array([st.line for st in streets], dtype=object)
        self.min_front = float(table.get("min_front", 3.0))
        self.souk_front = float(table.get("souk_front", self.min_front))
        self.overlap = float(table.get("mouth_overlap", 1.0))
        pen = table.get("mouth_penalty", {})
        self.kind_pen = np.array([float(pen.get(st.kind, 0.0)) for st in streets])
        self.todo = todo
        self.cfg = [dict(table, **table[districts[blocks[b][1]].kind]) for b in todo]
        self.rng = [ctx.rng("impasse", b) for b in todo]

        def per_block(key, default):
            return np.array([float(c.get(key, default)) for c in self.cfg])

        self.wmax = np.array([float(c["width"][1]) for c in self.cfg])
        self.thr = self.wmax / 2 + MARGIN
        self.new_mouth = per_block("new_mouth", 0.0)
        self.max_len = per_block("max_length", 60.0)
        self.min_lot = per_block("min_lot", 30.0)
        self.junction = per_block("junction_clear", 2.0)
        geo = np.array([blocks[b][0] for b in todo], dtype=object)
        self.edge_geo = shapely.boundary(geo)
        self.grown = shapely.buffer(geo, 0.01)
        shapely.prepare(self.grown)
        self.base = np.floor(shapely.bounds(geo)[:, :2] / GRID).astype(np.int64) - 1000
        fixed_polys = [[parcels[i].polygon for i in fixed.get(b, [])] for b in todo]
        self.rim = np.array([shapely.union_all([self.edge_geo[k]] + [p.boundary for p in fp]) if fp
                             else self.edge_geo[k] for k, fp in enumerate(fixed_polys)], dtype=object)
        self.lot_ids = [i for b in todo for i in groups[b]]
        sizes = [len(groups[b]) for b in todo]
        self.lot_blk = np.repeat(np.arange(len(todo)), sizes)
        self.lots_of = np.split(np.arange(len(self.lot_ids)), np.cumsum(sizes)[:-1])
        self.poly = np.array([parcels[i].polygon for i in self.lot_ids], dtype=object)
        self.ok0 = np.array([ok[i] for i in self.lot_ids])
        self.ok = self.ok0.copy()
        self.alive = np.ones(len(self.lot_ids), dtype=bool)
        self._graph(fixed_polys)
        self._sides()
        steps = np.arange(len(todo) + 1)       # nodes, edges and sides come block by block
        self.edge_lo = np.searchsorted(self.eblk, steps)
        self.side_lo = np.searchsorted(self.sblk, steps)
        self.block_lanes: list = [[] for _ in todo]
        self.lanes: list = []          # Street objects, in the order they were cut
        self.lane_blk: list = []
        self.lane_end: list = []       # dead-end node of each lane
        self.lane_surf: list = []
        self.banned: set = set()       # (side, direction, start node) found unusable

    def _key(self, xy, blk) -> np.ndarray:
        k = np.round(np.asarray(xy) / GRID).astype(np.int64) - self.base[blk]
        return blk.astype(np.int64) * BLOCK + k[:, 0] * SPAN + k[:, 1]

    # --- the graph of lot lines -------------------------------------------------------------
    def _graph(self, fixed_polys) -> None:
        nb = len(self.todo)
        rows = [list(self.poly[self.lots_of[k]]) + fixed_polys[k] for k in range(nb)]
        rings = np.full((nb, max(len(r) for r in rows)), None, dtype=object)
        for k, r in enumerate(rows):
            rings[k, :len(r)] = shapely.get_exterior_ring(np.array(r, dtype=object))
        parts, part_blk = shapely.get_parts(shapely.union_all(rings, grid_size=GRID, axis=1), return_index=True)
        xy, ci = shapely.get_coordinates(parts, return_index=True)
        uniq, inv = np.unique(self._key(xy, part_blk[ci]), return_inverse=True)
        inv = inv.ravel()
        same = ci[:-1] == ci[1:]
        pairs = np.unique(np.sort(np.stack([inv[:-1][same], inv[1:][same]], 1), axis=1), axis=0)
        pairs = pairs[pairs[:, 0] != pairs[:, 1]]
        self.node_key = uniq
        self.node_blk = uniq // BLOCK
        local = uniq % BLOCK
        self.xy = (np.stack([local // SPAN, local % SPAN], 1) + self.base[self.node_blk]) * GRID
        n = len(uniq)
        self.node_lo = np.searchsorted(self.node_blk, np.arange(nb + 1))
        self.ea, self.eb = pairs[:, 0], pairs[:, 1]
        self.eblk = self.node_blk[self.ea]          # nondecreasing: node ids grow with the block
        a, b = self.xy[self.ea], self.xy[self.eb]
        self.elen = np.hypot(*(b - a).T)
        segs = shapely.linestrings(np.stack([a, b], 1))
        rim = self.rim[self.eblk]
        on_rim = shapely.distance(shapely.points((a + b) / 2), rim) < 0.05
        clear = shapely.distance(segs, rim) >= self.thr[self.eblk]
        self.weight = np.empty(len(self.elen))      # length with a random share, drawn block by block
        bounds = np.searchsorted(self.eblk, np.arange(nb + 1))
        for k in range(nb):
            lo, hi = bounds[k], bounds[k + 1]
            j = float(self.cfg[k].get("jitter", 0.15))
            self.weight[lo:hi] = self.elen[lo:hi] * self.rng[k].uniform(1.0 - j, 1.0 + j, hi - lo)
        pts = shapely.points(self.xy)
        self.edge_node = shapely.distance(pts, self.edge_geo[self.node_blk]) < 0.02
        self.node_clear = shapely.distance(pts, self.rim[self.node_blk]) >= self.thr[self.node_blk]
        # mouths: block-edge nodes next to exactly one street, away from junctions
        self.mouth = np.full(n, -1)
        cand = np.nonzero(self.edge_node)[0]
        if len(cand):
            near = np.unique(self.tree.query(pts[cand], predicate="dwithin", distance=NEAR)[0])
            reach = (self.wmax / 2 + self.junction)[self.node_blk[cand]]
            pairs = np.unique(np.stack(self.tree.query(pts[cand], predicate="dwithin", distance=reach), 1), axis=0)
            count = np.bincount(pairs[:, 0], minlength=len(cand))
            street = np.full(len(cand), -1)
            street[pairs[:, 0]] = pairs[:, 1]
            one = np.zeros(len(cand), dtype=bool)
            one[near] = count[near] == 1
            self.mouth[cand[one]] = street[one]
        # the lane's first point: `overlap` meters from its mouth node toward the street's middle
        self.head = np.full((n, 2), np.nan)
        m = np.nonzero(self.mouth >= 0)[0]
        if len(m):
            q = shapely.get_coordinates(shapely.shortest_line(pts[m], self.lines[self.mouth[m]])).reshape(-1, 2, 2)[:, 1]
            d = q - self.xy[m]
            dist = np.maximum(np.hypot(d[:, 0], d[:, 1]), 1e-9)
            head = self.xy[m] + d / dist[:, None] * np.minimum(self.overlap, 0.9 * dist)[:, None]
            surf = self.surfaces[self.mouth[m]]
            shapely.prepare(surf)
            inside = shapely.contains_xy(surf, head[:, 0], head[:, 1]) & (
                shapely.distance(shapely.points(head), shapely.boundary(surf)) >= 0.1)
            self.head[m] = head
            self.mouth[m[~inside]] = -1
        self.penalty = np.where(self.mouth >= 0, self.kind_pen[np.maximum(self.mouth, 0)], 0.0)
        # a lane may use an edge away from the block's edge, or one leaving a mouth into the block
        self.usable = ~on_rim & clear
        self.first_from = np.full(len(self.elen), -1)
        es, ms = [], []
        for a_, b_ in ((self.ea, self.eb), (self.eb, self.ea)):
            pick = ~on_rim & ~clear & (self.mouth[a_] >= 0) & ~self.edge_node[b_] & self.node_clear[b_]
            es.append(np.nonzero(pick)[0])
            ms.append(a_[pick])
        es, ms = np.concatenate(es), np.concatenate(ms)
        if len(es):
            other = np.where(ms == self.ea[es], self.eb[es], self.ea[es])
            fine = self._into_mouth(self.xy[ms], self.xy[other], self.node_blk[ms], self.mouth[ms])
            self.first_from[es[fine]] = ms[fine]
        self.first = self.first_from >= 0
        self.on_lane = np.zeros(n, dtype=bool)
        self.glen = np.zeros(n)        # length along its lane from the mouth
        self.root_pen = np.zeros(n)    # the mouth penalty of that lane
        self.owner = np.full(n, -1)    # the lane through each node

    def _into_mouth(self, a, b, blk, street) -> np.ndarray:
        """True where a lane from mouth point a to b leaves its block only near a, into the mouth's
        street: past twice its clearance from a it keeps clear of the block's edge (so it leaves at
        30 degrees or more), and the corners of its first meters lie in the block or that street."""
        d = b - a
        length = np.hypot(d[:, 0], d[:, 1])
        u = d / length[:, None]
        n = np.stack([-u[:, 1], u[:, 0]], 1)
        reach = 2.0 * self.thr[blk]
        fine = np.ones(len(a), dtype=bool)
        far = np.nonzero(length > reach)[0]
        if len(far):
            rest = shapely.linestrings(np.stack([a[far] + u[far] * reach[far, None], b[far]], 1))
            fine[far] = shapely.distance(rest, self.rim[blk[far]]) >= self.thr[blk[far]]
        half = (self.wmax[blk] / 2)[:, None]
        pts = []
        for t in (0.0, 0.5, 1.0):
            c = a + u * np.minimum(reach, length)[:, None] * t
            pts += [c + n * half, c - n * half]
        pts = np.stack(pts, 1)                                   # (lines, 6, 2)
        rows = np.repeat(np.arange(len(a)), pts.shape[1])
        x, y = pts[..., 0].ravel(), pts[..., 1].ravel()
        inside = shapely.contains_xy(self.grown[blk][rows], x, y) | shapely.contains_xy(self.surfaces[street][rows], x, y)
        return fine & inside.reshape(len(a), -1).all(axis=1)

    def _sides(self) -> None:
        """Every straight side of every lot: its end nodes and length, and whether a lane may run
        along it from either end (`valid[0]`: from `sa`, `valid[1]`: from `sb`)."""
        rings = shapely.simplify(shapely.set_precision(shapely.get_exterior_ring(self.poly), GRID), 0.05)
        xy, li = shapely.get_coordinates(rings, return_index=True)
        key = self._key(xy, self.lot_blk[li])
        pos = np.minimum(np.searchsorted(self.node_key, key), len(self.node_key) - 1)
        node = np.where(self.node_key[pos] == key, pos, -1)
        same = (li[:-1] == li[1:]) & (node[:-1] >= 0) & (node[1:] >= 0) & (node[:-1] != node[1:])
        self.sa, self.sb, self.slot = node[:-1][same], node[1:][same], li[:-1][same]
        self.sblk = self.lot_blk[self.slot]
        a, b = self.xy[self.sa], self.xy[self.sb]
        self.slen = np.hypot(*(b - a).T)
        lines = shapely.linestrings(np.stack([a, b], 1))
        rim = self.rim[self.sblk]
        on_rim = shapely.distance(shapely.points((a + b) / 2), rim) < 0.05
        clear = shapely.distance(lines, rim) >= self.thr[self.sblk]
        self.valid = np.stack([clear & ~on_rim, clear & ~on_rim])
        for d, (st, en) in enumerate(((self.sa, self.sb), (self.sb, self.sa))):
            idx = np.nonzero(~clear & ~on_rim & (self.mouth[st] >= 0) & self.node_clear[en])[0]
            if len(idx):
                self.valid[d, idx] = self._into_mouth(self.xy[st[idx]], self.xy[en[idx]], self.sblk[idx],
                                                      self.mouth[st[idx]])

    def _along(self, s: int, start: int, end: int) -> list:
        """Nodes on side s after `start`, up to and including `end`, in order."""
        k = self.sblk[s]
        lo, hi = self.node_lo[k], self.node_lo[k + 1]
        a, b = self.xy[start], self.xy[end]
        u = (b - a) / self.slen[s]
        p = self.xy[lo:hi] - a
        t = p @ u
        off = np.abs(p[:, 0] * u[1] - p[:, 1] * u[0])
        on = np.nonzero((off < 0.02) & (t > 0.01) & (t < self.slen[s] + 0.01))[0]
        return (lo + on[np.argsort(t[on])]).tolist()

    # --- cutting lanes ----------------------------------------------------------------------
    def run(self) -> None:
        """Rounds: every block that still has a lot without a door proposes its cheapest lane."""
        nb = len(self.todo)
        done = np.zeros(nb, dtype=bool)
        while True:
            want = self.alive & ~self.ok
            ids = np.nonzero((np.bincount(self.lot_blk[want], minlength=nb) > 0) & ~done)[0]
            if not len(ids):
                return
            nodes = _span(self.node_lo, ids)
            sides = _span(self.side_lo, ids)
            dist, pred = self._dijkstra(nodes, _span(self.edge_lo, ids))
            ends = np.searchsorted(nodes, np.stack([self.sa[sides], self.sb[sides]]))
            live = self.valid[:, sides] & want[self.slot[sides]][None, :]
            cost = np.where(live, dist[ends] + self.slen[sides], np.inf)
            dd, si = np.nonzero(np.isfinite(cost))
            order = np.lexsort((dd, sides[si], cost[dd, si], self.sblk[sides[si]]))
            dd, ss = dd[order], sides[si[order]]
            first = np.searchsorted(self.sblk[ss], np.arange(nb + 1))
            plans = []
            for k in ids:
                plan = None
                for t in range(first[k], first[k + 1]):
                    plan = self._propose(int(k), int(dd[t]), int(ss[t]), pred, nodes)
                    if plan is not None:
                        break
                if plan is None:
                    done[k] = True
                else:
                    plans.append(plan)
            if not plans:
                continue
            fine = self._tails_clear(plans)
            made = []
            for plan, f in zip(plans, fine):
                if f:
                    made.append(self._commit(plan))
                else:
                    self.banned.add(plan["key"])
            if made:
                self._cut(made)

    def _dijkstra(self, nodes, edges):
        """Distances from the cheapest source (a new mouth or a lane already cut), over the given
        nodes and edges, numbered locally (node i is nodes[i], the source is len(nodes))."""
        m = len(nodes)
        blocked = self.on_lane[nodes] | (self.mouth[nodes] >= 0)   # a lane never enters a mouth or a lane
        ea, eb = np.searchsorted(nodes, self.ea[edges]), np.searchsorted(nodes, self.eb[edges])
        usable, weight = self.usable[edges], self.weight[edges]
        u, v, w = [], [], []
        for a, b in ((ea, eb), (eb, ea)):
            keep = usable & ~blocked[b]
            u.append(a[keep])
            v.append(b[keep])
            w.append(weight[keep])
        f = np.nonzero(self.first[edges])[0]
        fa_g = self.first_from[edges[f]]
        fa = np.searchsorted(nodes, fa_g)
        fb = np.where(fa_g == self.ea[edges[f]], eb[f], ea[f])
        keep = ~blocked[fb]
        u.append(fa[keep])
        v.append(fb[keep])
        w.append(weight[f][keep])
        lane = self.on_lane[nodes]
        mouths = np.nonzero((self.mouth[nodes] >= 0) & ~lane)[0]
        lanes = np.nonzero(lane & (self.mouth[nodes] < 0))[0]   # a branch never starts in a mouth
        g_m, g_l = nodes[mouths], nodes[lanes]
        u += [np.full(len(mouths), m), np.full(len(lanes), m)]
        v += [mouths, lanes]
        w += [self.penalty[g_m] + self.new_mouth[self.node_blk[g_m]] + 1e-6, self.root_pen[g_l] + self.glen[g_l] + 1e-6]
        # every (from, to) pair is unique: lot lines are deduplicated, a mouth's first edge is never
        # usable both ways, and mouths and lane nodes are separate sources
        g = csr_matrix((np.concatenate(w), (np.concatenate(u), np.concatenate(v))), shape=(m + 1, m + 1))
        return dijkstra(g, directed=True, indices=m, return_predecessors=True)

    @staticmethod
    def _trace(pred, node: int, src: int) -> list:
        out = [node]
        while pred[out[-1]] != src and pred[out[-1]] >= 0:
            out.append(int(pred[out[-1]]))
        return out[::-1]

    def _propose(self, k: int, d: int, s: int, pred, nodes) -> dict | None:
        """The lane serving side s from end d, or None (and remembered) if it cannot be cut."""
        start, end = (int(self.sa[s]), int(self.sb[s])) if d == 0 else (int(self.sb[s]), int(self.sa[s]))
        path = nodes[self._trace(pred, int(np.searchsorted(nodes, start)), len(nodes))].tolist()
        key = (s, d, path[0])
        if key in self.banned:
            return None
        along = self._along(s, start, end)
        if (set(along) & set(path)) or any(self.on_lane[q] or self.mouth[q] >= 0 for q in along):
            self.banned.add(key)
            return None
        nodes = path + along
        pts = self.xy[nodes]
        length = float(np.sum(np.hypot(*np.diff(pts, axis=0).T)))
        head = int(nodes[0])
        root = not self.on_lane[head]
        if (0.0 if root else self.glen[head]) + length > self.max_len[k]:
            self.banned.add(key)
            return None
        plan = {"k": k, "key": key, "nodes": nodes, "root": root, "parent": -1}
        if root:
            plan["width"] = self._width(k)
            plan["coords"] = np.vstack([self.head[head], pts])
            plan["skip"] = self.overlap + plan["width"] / 2 + 0.3
            return plan
        j = int(self.owner[head])
        plan["parent"] = j
        if head == self.lane_end[j]:               # carry on from its dead end
            old = self.lanes[j]
            plan["width"], plan["extend"] = old.width, True
            plan["coords"] = np.vstack([np.asarray(old.line.coords), pts[1:]])
            plan["skip"] = old.line.length
        else:                                       # a branch off its side
            plan["width"] = self._width(k)
            plan["coords"] = pts
            plan["skip"] = self.lanes[j].width / 2 + plan["width"] / 2 + 0.3
        return plan

    def _width(self, k: int) -> float:
        lo, hi = self.cfg[k]["width"]
        return round(float(self.rng[k].uniform(lo, hi)), 1)

    def _tails_clear(self, plans) -> np.ndarray:
        """The proposed lanes past their mouths cross no street and no lane but their parent."""
        fine = np.ones(len(plans), dtype=bool)
        coords, ids, widths, which = [], [], [], []
        for m, p in enumerate(plans):
            tail = _drop_head(p["coords"], p["skip"])
            if tail is not None:
                coords.append(tail)
                ids.append(np.full(len(tail), len(which)))
                widths.append(p["width"])
                which.append(m)
        if not which:
            return fine
        lines = shapely.linestrings(np.concatenate(coords), indices=np.concatenate(ids))
        surf = shapely.buffer(lines, np.array(widths) / 2, cap_style="flat")
        which = np.array(which)
        fine[which[np.unique(self.tree.query(surf, predicate="intersects")[0])]] = False
        for t, m in enumerate(which):          # other lanes of the same block
            others = [j for j in self.block_lanes[plans[m]["k"]] if j != plans[m]["parent"]]
            if others and shapely.intersects(np.array([self.lane_surf[j] for j in others], dtype=object),
                                             surf[t]).any():
                fine[m] = False
        return fine

    def _commit(self, plan) -> int:
        k, nodes = plan["k"], plan["nodes"]
        head, end = nodes[0], nodes[-1]
        line = LineString(plan["coords"])
        if plan.get("extend"):
            j = plan["parent"]
            self.lanes[j].line = line
        else:
            lane = Street("impasse", plan["width"], line, str(self.cfg[k]["surface"]))
            if plan["root"] and self.rng[k].random() < float(self.cfg[k].get("covered", 0.0)):
                lo, hi = self.cfg[k].get("covered_length", [3.0, 5.0])
                lane.covered = round(min(float(self.rng[k].uniform(lo, hi)), 0.5 * line.length), 2)
            self.block_lanes[k].append(len(self.lanes))
            self.lanes.append(lane)
            self.lane_blk.append(k)
            self.lane_end.append(end)
            self.lane_surf.append(None)
            j = len(self.lanes) - 1
        self.lane_end[j] = end
        run = 0.0 if plan["root"] else self.glen[head]
        pen = self.penalty[head] if plan["root"] else self.root_pen[head]
        for m, q in enumerate(nodes):
            if m:
                run += float(np.hypot(*(self.xy[q] - self.xy[nodes[m - 1]])))
            if not self.on_lane[q]:
                self.on_lane[q], self.glen[q], self.root_pen[q], self.owner[q] = True, run, pen, j
        return j

    def _cut(self, made: list) -> None:
        """Cut the new lanes out of their blocks' lots, then look again which lots have a door."""
        lanes = [self.lanes[j] for j in made]
        lines = np.array([s.line for s in lanes], dtype=object)
        half = np.array([s.width for s in lanes]) / 2
        for j, g in zip(made, shapely.buffer(lines, half, cap_style="flat")):
            self.lane_surf[j] = g                 # the surface as the dresser and the ground see it
        # lots lose a little more: sharp corners outside a bend (a few walls instead of a round
        # arc of them), still clear of the drawn surface
        surf = shapely.buffer(lines, half, cap_style="flat", join_style="mitre")
        pi, li = [], []
        for m, j in enumerate(made):
            lots = self.lots_of[self.lane_blk[j]]
            lots = lots[self.alive[lots]]
            pi.append(np.full(len(lots), m))
            li.append(lots)
        pi, li = np.concatenate(pi), np.concatenate(li)
        hit = shapely.intersects(self.poly[li], surf[pi])
        pi, li = pi[hit], li[hit]
        rest = shapely.simplify(shapely.difference(self.poly[li], surf[pi]), 0.02)
        for k in np.nonzero(shapely.get_type_id(rest) != 3)[0]:
            rest[k] = largest(rest[k])
        small = np.array([r is None or r.area < self.min_lot[self.lot_blk[i]] for r, i in zip(rest, li)], dtype=bool)
        self.poly[li] = rest
        self.poly[li[small]] = None
        self.alive[li[small]] = False
        self.ok[li[small]] = False
        blocks = sorted({self.lane_blk[j] for j in made})
        check = np.concatenate([self.lots_of[k] for k in blocks])
        check = check[self.alive[check] & ~self.ok[check]]
        if len(check):   # only lots beside a new lane can have found a door
            near = STRtree(surf).query(self.poly[check], predicate="dwithin", distance=REACH + INSET + 0.1)[0]
            check = check[np.unique(near)]
        check = np.union1d(check, li[~small])   # a cut may also take the wall a lot had its door on
        if len(check):
            lanes = STRtree([self.lane_surf[j] for k in blocks for j in self.block_lanes[k]])
            self.ok[check] = served(self.poly[check], self.min_front, self.tree, self.souk, self.souk_front, lanes)

    # --- lots no lane reaches ---------------------------------------------------------------
    def merge(self) -> None:
        """Each lot still without a door joins the neighbour with a door it shares most boundary with."""
        for k in np.unique(self.lot_blk[self.alive & ~self.ok]):
            lots = self.lots_of[k]
            moved = True
            while moved:
                moved = False
                for li in lots[self.alive[lots] & ~self.ok[lots]]:
                    p = self.poly[li]
                    grown = p.buffer(0.05)
                    best, best_len = None, 1.0
                    for lj in lots[self.alive[lots] & self.ok[lots]]:
                        q = self.poly[lj]
                        if q.intersects(grown):
                            shared = q.boundary.intersection(grown).length
                            if shared > best_len:
                                best, best_len = lj, shared
                    if best is None:
                        continue
                    both = largest(shapely.union(self.poly[best], p, grid_size=GRID))
                    if both is None:
                        continue
                    self.poly[best], self.poly[li] = both, None
                    self.alive[li] = False
                    moved = True


def _drop_head(coords: np.ndarray, skip: float):
    """The points of a line after its first `skip` meters, or None when nothing is left."""
    seg = np.hypot(*np.diff(coords, axis=0).T)
    run = np.concatenate([[0.0], np.cumsum(seg)])
    if run[-1] <= skip + 0.05:
        return None
    i = int(np.searchsorted(run, skip, side="right"))
    t = (skip - run[i - 1]) / max(seg[i - 1], 1e-9)
    p = coords[i - 1] + (coords[i] - coords[i - 1]) * t
    return np.vstack([p, coords[i:]])


def _span(lo: np.ndarray, ids: np.ndarray) -> np.ndarray:
    """All indices lo[k] .. lo[k + 1] - 1 for the blocks k in `ids`, in order."""
    start, size = lo[ids], lo[ids + 1] - lo[ids]
    return np.repeat(start - np.concatenate([[0], np.cumsum(size)[:-1]]), size) + np.arange(size.sum())
