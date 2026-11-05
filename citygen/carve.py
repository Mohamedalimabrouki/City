"""What rivers and lakes do to the ground (prompts 60 and 61): a pure function of position, made once per world.

`Terrain.height` stays the land as the noise made it: the drainage, the settlements' scores and the city planner
read it. `Ground.height` grades that land, then comes here, so bed and banks are the same inside and outside
cities ("grade first, carve last"):

  fill   raises the ground only where water would otherwise end in the air: a rim `sill` m over a lake's level
         on a ring `shore` m off its coarse shore, and a low bank (levee) along a reach whose water is pinned to
         what it runs into but stands above the ground
  cut    height = smooth min(ground, water(s) + section(d)), s the nearest point of the river's line, d the distance
         to it: a U under the water, a bank of `bank_width` m up to `bank_rise` m, a flat valley floor, then valley
         walls that steepen with height, so even a cut of 30 m through a pit's rim is a valley and not a slot. It
         only ever lowers, and the top of a bank or a wall is rounded into the land, not a crease.

Exact distances to the river's segments, not a raster of them: a stream 3 m wide has no place on a 20 m raster,
and distances interpolated across a center line or a junction are wrong. The raster here is the index: a grid of
`CELL` m that lists the segments whose valley reaches each square (a point on no listed square costs one array
look-up), each segment's reach measured once on the land (`_reaches`). The numbers of the section are a soft mean over
the segments about as near as the nearest, so two rivers meet with no seam and a meander's two reaches too.

The water itself (`mesh/water.py`): a lake's level or a salt crust wherever the ground lies below it inside
`shore` m of its coarse shore, so the shore is where the land really meets the level; a river's ribbon, one
height across, on `River.surface`.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import shapely
from shapely.geometry import LineString, Polygon

from .hydro import along, channel, low_ground

CELL = 64.0        # meters: the index grid
PROBES = (24.0, 40.0, 64.0, 96.0, 136.0, 192.0, 256.0, 340.0)   # meters off a river where its reach is measured
CHUNK = 8          # river points to one reach
FADE = math.exp(-3.0)   # the weight of a segment `3 x soft` m farther than the nearest: nothing
MARGIN = 12.0      # meters added to a measured reach


@dataclass
class Shore:
    """One lake as the ground and the mesher see it."""
    level: float
    salt: bool
    polygon: Polygon     # the coarse shore
    zone: Polygon        # `shore` m past it: its water or salt is drawn inside this
    ring: object         # the coarse shore as a line
    reach: float         # meters off the shore where `fill` still acts
    box: tuple           # bounds of `zone`


@dataclass
class Sample:
    """The rivers at some points, as arrays, inf where no river reaches."""
    surface: np.ndarray  # the height a river's section gives the ground
    round: np.ndarray    # meters of height over which the land rounds into it
    past: np.ndarray     # meters past the bank, negative in the channel
    edge: np.ndarray     # meters past the edge of the water or of a dry oued's floor
    lip: np.ndarray      # the bank's width
    plain: np.ndarray    # the valley floor's width
    dry: np.ndarray      # on a dry oued

    def take(self, at) -> "Sample":
        return Sample(*(getattr(self, f)[at] for f in self.__dataclass_fields__))


@dataclass
class Ribbon:
    """The wet part of one river, for the mesher."""
    line: LineString
    along: np.ndarray    # meters along the river at each point of `coords`
    surface: np.ndarray
    half: np.ndarray
    start: float         # the ribbon runs from here...
    end: float           # ...to here, in meters along the line
    dug: float           # the channel runs on to here: past a ribbon's end at 0, the sea comes up it


def _section(d, half, depth, lip, rise, plain, flat, curve):
    """Height over the water at `d` meters off the center line: the bed's U, the bank, the valley floor, its walls."""
    e = np.maximum(d - half, 0.0)
    wall = np.maximum(e - lip - plain, 0.0)
    bed = -depth * (1.0 - np.minimum(d / np.maximum(half, 1e-3), 1.0) ** 2)
    x = np.minimum(e / lip, 1.0)
    return bed + rise * x * x * (3.0 - 2.0 * x) + flat * np.maximum(e - lip, 0.0) + curve * wall * wall


class Carve:
    def __init__(self, terrain, rivers: list, lakes: list, cfg: dict):
        rc = cfg["rivers"]
        self.size = terrain.size
        self.rc = rc
        self.flat, self.curve = float(rc["valley_flat"]), float(rc["valley_curve"])
        self.keep = float(rc["keep"])
        self.round_near, self.round_grow, self.round = (float(v) for v in rc["bank_round"])
        self.sill, self.sill_fade = float(rc["sill"]), float(rc["sill_fade"])
        self.soft, self.mouth_fade = float(rc["soft"]), tuple(float(v) for v in rc["mouth_fade"])
        self.levee_slope, self.levee_fade = float(rc["levee"]), float(rc["levee_fade"])
        self.rim_rise, self.rim_pad = float(rc["rim_rise"]), float(rc["rim_pad"])
        self.n = int(math.ceil(self.size / CELL)) + 1
        self.shores = self._shores(lakes, float(rc["shore"]))
        self.rivers = rivers
        self.ribbons = {}
        rows = [row for row in (self._river(terrain, r, rc) for r in rivers if len(r.coords) > 1) if row is not None]
        table, reaches, cuts, levees = zip(*rows) if rows else ((), (), (), ())
        self.table = np.concatenate(table) if table else np.zeros((0, 13))
        self.cuts = np.concatenate(cuts) if cuts else np.zeros(0)
        self.zones = shapely.union_all([sh.zone for sh in self.shores]) if self.shores else None
        self.lakes = shapely.union_all([sh.polygon for sh in self.shores]) if self.shores else None
        self.dry = np.array([r.seasonal for r in rivers], dtype=bool)[self.table[:, 12].astype(np.int64)]
        self.levees = np.concatenate(levees) if levees else np.zeros((0, 8))
        self.cells, self.levee_cells, self.lake_cells = {}, {}, {}
        self._index(np.concatenate(reaches) if reaches else np.zeros(0))
        self.near = np.zeros((self.n, self.n), dtype=bool)
        for cells in (self.cells, self.levee_cells, self.lake_cells):
            if cells:
                keys = np.fromiter(cells, dtype=np.int64)
                self.near.flat[keys] = True

    # --- what is built once ---------------------------------------------------------------------------------

    def _river(self, terrain, r, rc: dict) -> tuple | None:
        """(table rows, reaches, how deep it runs, levees) of one river, None when nothing of it is on land. Its channel
        stops at the shore: no channel on a lake's floor, and a bed comes up to the water it meets."""
        ch = channel(r, rc)
        rib = self._ribbon(terrain, r, ch)
        s = rib.along
        seg = np.flatnonzero((s[1:] >= rib.start) & (s[:-1] <= rib.dug))
        if not len(seg):
            return None
        fade, least = self.mouth_fade
        into = np.clip((rib.dug - s) / fade, least, 1.0) if r.mouth in ("sea", "lake", "basin") else 1.0
        out = np.clip((s - rib.start) / fade, least, 1.0) if r.source is not None else 1.0

        def mid(v):
            return 0.5 * (v[seg] + v[seg + 1])

        row = np.column_stack([r.coords[seg], r.coords[seg + 1], r.surface[seg], r.surface[seg + 1], ch["half"][seg],
                               ch["half"][seg + 1], mid(ch["depth"] * into * out), mid(ch["lip"]), mid(ch["rise"]),
                               mid(ch["plain"]), np.full(len(seg), r.id)])
        under = np.maximum(terrain.height(r.coords[:, 0], r.coords[:, 1]) - r.surface - ch["rise"], 0.0)
        levee = np.zeros((0, 8))
        if not r.seasonal:
            self.ribbons[r.id] = rib
            levee = self._levee(terrain, r, ch, rib)
        return row, self._reaches(terrain, r, ch)[seg], mid(under), levee

    def _shores(self, lakes: list, shore: float) -> list:
        out = []
        for k in lakes:
            poly = Polygon(k.polygon).buffer(0)
            reach = shore + self.rim_pad + self.sill_fade
            zone = poly.buffer(shore)
            out.append(Shore(k.level, k.salt, poly, zone, poly.exterior, reach, zone.bounds))
        return out

    def _reaches(self, terrain, r, ch: dict) -> np.ndarray:
        """Per segment, how far off the line its surface can lie under the land: probed on both sides, every
        `CHUNK` points, the widest probe still cut, one probe more, then `MARGIN`."""
        n = len(r.coords)
        at = np.arange(0, n, CHUNK)
        d = np.gradient(r.coords, axis=0)[at]
        nrm = np.stack([-d[:, 1], d[:, 0]], axis=1) / np.maximum(np.hypot(*d.T), 1e-9)[:, None]
        base = ch["half"][at] + ch["lip"][at]
        out = base + PROBES[0]
        for k, probe in enumerate(PROBES):
            off = base + probe
            z = r.surface[at] + _section(off, ch["half"][at], ch["depth"][at], ch["lip"][at], ch["rise"][at],
                                         ch["plain"][at], self.flat, self.curve)
            for side in (-1.0, 1.0):
                p = r.coords[at] + nrm * (side * off)[:, None]
                cut = np.asarray(terrain.height(p[:, 0], p[:, 1])) > z - self.round
                out = np.where(cut, base + PROBES[min(k + 1, len(PROBES) - 1)], out)
        out = np.maximum.reduce([out, np.roll(out, 1), np.roll(out, -1)]) if len(out) > 2 else out
        return np.repeat(out + MARGIN, CHUNK)[:n - 1]

    def _levee(self, terrain, r, ch: dict, rib: Ribbon) -> np.ndarray:
        """The segments of a river's drawn water that stand higher than `freeboard` under a bank:
        (ax, ay, bx, by, crest at a, crest at b, half width, reach): a bank falling off from the crest to the low
        ground beside it, no farther."""
        crest = r.surface + float(self.rc["freeboard"]) * ch["rise"] / max(float(ch["rise"].max()), 1e-9)
        low = low_ground(r, terrain, ch["half"] + ch["lip"], 1e9)
        need = ((crest - low) > 0.02) & (rib.along >= rib.start) & (rib.along <= rib.end)
        seg = np.flatnonzero(need[:-1] | need[1:])
        if not len(seg):
            return np.zeros((0, 8))
        a, b = r.coords[seg], r.coords[seg + 1]
        fall = np.maximum(crest[seg] - low[seg], crest[seg + 1] - low[seg + 1]) / self.levee_slope
        return np.column_stack([a, b, crest[seg], crest[seg + 1], (ch["half"] + ch["lip"])[seg], fall])

    def _ribbon(self, terrain, r, ch: dict) -> Ribbon:
        """Where a river's water is drawn: from its spring, or from its lake's real shore, where the land meets the
        level, to the shore of the lake it runs into (a little over the lake, at its level: no gap at the cell steps)
        or, on the way to the sea, to where the water reaches 0 and the sea plane takes over."""
        s = along(r.coords)
        line = LineString(r.coords)
        start, end, dug = 0.0, float(s[-1]), None
        ground = np.asarray(terrain.height(r.coords[:, 0], r.coords[:, 1]))
        if r.source is not None:                        # or from the edge of its lake's drawn water, if that comes first
            sh = self.shores[r.source]
            away = np.flatnonzero((ground >= sh.level) | ~shapely.contains_xy(sh.zone, r.coords[:, 0], r.coords[:, 1]))
            start = float(s[max(int(away[0]) - 2, 0)]) if len(away) else 0.0
        if r.mouth == "sea":
            wet, land = np.flatnonzero(r.surface <= 0.0), np.flatnonzero(ground > 0.0)
            end = float(s[wet[0]]) if len(wet) else end
            dug = float(s[min(int(land[-1]) + 2, len(s) - 1)]) if len(land) else end
        elif r.mouth in ("lake", "basin"):
            land = np.flatnonzero(ground >= self.shores[r.into].level)
            end = float(s[min(int(land[-1]) + 2, len(s) - 1)]) if len(land) else end
        elif r.mouth == "river" and r.into is not None:
            main = self.rivers[r.into]
            at = LineString(main.coords).project(shapely.points(r.coords[-1]))
            end -= 0.25 * float(np.interp(at, along(main.coords), main.widths))
        end = max(end, start)
        return Ribbon(line, s, r.surface, ch["half"], start, end, end if dug is None else max(dug, end))

    def _index(self, reach: np.ndarray) -> None:
        """The grid: each square lists the segments whose reach touches it, the levees' and the lakes' too."""
        t = self.table
        per: dict = {}
        firsts = np.flatnonzero(np.r_[True, t[1:, 12] != t[:-1, 12]]) if len(t) else np.zeros(0, dtype=np.int64)
        for first, stop in zip(firsts, np.r_[firsts[1:], len(t)]):
            for k in range(int(first), int(stop), CHUNK):   # a chunk of a river's segments at a time: they share a reach
                ids = np.arange(k, min(k + CHUNK, int(stop)))
                part, r = t[ids], float(reach[ids].max())
                x0, x1 = min(part[:, 0].min(), part[:, 2].min()) - r, max(part[:, 0].max(), part[:, 2].max()) + r
                y0, y1 = min(part[:, 1].min(), part[:, 3].min()) - r, max(part[:, 1].max(), part[:, 3].max()) + r
                for key in self._squares(x0, y0, x1, y1):
                    per.setdefault(key, []).append(ids)
        self.cells = {key: np.concatenate(v) for key, v in per.items()}
        per = {}
        for k, (ax, ay, bx, by, *_rest) in enumerate(self.levees):
            r = self._levee_reach(k)
            for key in self._squares(min(ax, bx) - r, min(ay, by) - r, max(ax, bx) + r, max(ay, by) + r):
                per.setdefault(key, []).append(k)
        self.levee_cells = {key: np.array(v, dtype=np.int64) for key, v in per.items()}
        per = {}
        for k, sh in enumerate(self.shores):
            x0, y0, x1, y1 = sh.polygon.bounds
            keys = np.array(self._squares(x0 - sh.reach, y0 - sh.reach, x1 + sh.reach, y1 + sh.reach), dtype=np.int64)
            cx, cy = (keys % self.n + 0.5) * CELL, (keys // self.n + 0.5) * CELL
            ring = shapely.distance(sh.ring, shapely.points(cx, cy)) <= sh.reach + CELL
            for key in keys[ring].tolist():
                per.setdefault(key, []).append(k)
        self.lake_cells = per

    def _levee_reach(self, k: int) -> float:
        return float(self.levees[k, 6] + self.levees[k, 7])

    def _squares(self, x0, y0, x1, y1) -> list:
        i0, i1 = max(int(x0 // CELL), 0), min(int(x1 // CELL), self.n - 1)
        j0, j1 = max(int(y0 // CELL), 0), min(int(y1 // CELL), self.n - 1)
        return [j * self.n + i for j in range(j0, j1 + 1) for i in range(i0, i1 + 1)]

    # --- what places and roads keep off ----------------------------------------------------------------------

    def wet(self, x, y) -> np.ndarray:
        """True on a lake's drawn water, a river's bed or its banks, or within `keep` m of them."""
        x, y = np.ravel(x), np.ravel(y)
        out = self.past_bank(x, y) < self.keep
        if self.zones is not None:
            out |= shapely.contains_xy(self.zones, x, y)
        return out

    def on_corridor(self, x: float, y: float) -> bool:
        """True on `corridor`, which is wider than `wet` where a river runs deep under the land round it."""
        r = PROBES[-1]
        near = self.corridor(x - r, y - r, x + r, y + r)
        return near is not None and bool(shapely.contains_xy(near, x, y))

    def crosses_lake(self, line) -> bool:
        return self.shores != [] and line.intersects(self.lakes)

    def lakes_near(self, margin: float, x, y) -> np.ndarray:
        """True within `margin` m of a lake."""
        if not self.shores:
            return np.zeros(np.shape(x), dtype=bool)
        return shapely.contains_xy(shapely.union_all([sh.polygon.buffer(margin) for sh in self.shores]), x, y)

    def corridor(self, x0: float, y0: float, x1: float, y1: float):
        """The rivers in a box as one polygon: water, banks and `keep` m, wider where the river runs deep under
        the land round it, or None. Blocks, buildings and towns keep off it; the streets of prompt 62 cross it."""
        t = self.table
        near = np.flatnonzero((np.minimum(t[:, 0], t[:, 2]) < x1) & (np.maximum(t[:, 0], t[:, 2]) > x0)
                              & (np.minimum(t[:, 1], t[:, 3]) < y1) & (np.maximum(t[:, 1], t[:, 3]) > y0))
        if not len(near):
            return None
        radii = np.maximum(t[near, 6], t[near, 7]) + t[near, 9] + self.keep + np.sqrt(self.cuts[near] / self.curve)
        lines = shapely.linestrings(np.stack([t[near, :2], t[near, 2:4]], axis=1))
        return shapely.union_all(shapely.buffer(lines, radii, quad_segs=3))

    # --- the ground -----------------------------------------------------------------------------------------

    def _groups(self, x: np.ndarray, y: np.ndarray):
        """(square, indices of the points on it) for the squares that list anything."""
        ix = np.clip((x / CELL).astype(np.int64), 0, self.n - 1)
        iy = np.clip((y / CELL).astype(np.int64), 0, self.n - 1)
        key = iy * self.n + ix
        sel = np.flatnonzero(self.near.flat[key])
        if not len(sel):
            return []
        sel = sel[np.argsort(key[sel], kind="stable")]
        k = key[sel]
        starts = np.flatnonzero(np.r_[True, k[1:] != k[:-1]])
        return [(int(k[a]), sel[a:b]) for a, b in zip(starts, np.r_[starts[1:], len(k)])]

    @staticmethod
    def _along(x, y, t):
        """(distance to each segment, how far along it) for points x, y and segments `t` (columns ax, ay, bx, by)."""
        ax, ay, bx, by = t[:, 0], t[:, 1], t[:, 2], t[:, 3]
        dx, dy = bx - ax, by - ay
        px, py = x[:, None] - ax, y[:, None] - ay
        u = np.clip((px * dx + py * dy) / np.maximum(dx * dx + dy * dy, 1e-12), 0.0, 1.0)
        return np.hypot(px - u * dx, py - u * dy), u

    def _sample(self, out: Sample, sel, x, y, ids, floor: bool) -> None:
        """One square's points. The section is measured off the nearest point of the line, never along it: a steep
        river's lower reach must not undercut its own banks upstream. Its numbers are a soft mean over the segments
        about as near as the nearest (within `3 x soft` m, weights fading to nothing there), so the surface stays
        continuous where two reaches or a tributary and its main river are equally near."""
        t = self.table[ids]
        d, u = self._along(x, y, t)
        near = d.min(axis=1)
        pi, si = np.nonzero(d < near[:, None] + 3.0 * self.soft)
        w = np.exp((near[pi] - d[pi, si]) / self.soft) - FADE
        v, along_it = t[si], u[pi, si]
        total = np.bincount(pi, w, len(x))

        def mean(values):
            return np.bincount(pi, w * values, len(x)) / total

        half = mean(v[:, 6] + along_it * (v[:, 7] - v[:, 6]))
        water = mean(v[:, 4] + along_it * (v[:, 5] - v[:, 4]))
        depth, lip, rise, plain = (mean(v[:, c]) for c in (8, 9, 10, 11))
        past = near - half - lip
        off = np.maximum(near, half + lip) if floor else near
        out.surface[sel] = water + _section(off, half, depth, lip, rise, plain, self.flat, self.curve)
        out.round[sel] = np.clip(np.minimum(self.round_near, rise) + self.round_grow * past, 1e-3, self.round)
        out.past[sel], out.edge[sel], out.lip[sel], out.plain[sel] = past, near - half, lip, plain
        out.dry[sel] = self.dry[ids[np.argmin(d, axis=1)]]

    def sample(self, x, y, floor: bool = False) -> Sample:
        """The rivers at points x, y. With `floor`, no point counts as nearer the line than the bank's top: the valley
        without the channel."""
        x, y = np.ravel(x), np.ravel(y)
        n = len(x)
        out = Sample(np.full(n, np.inf), np.full(n, 1.0), np.full(n, np.inf), np.full(n, np.inf), np.zeros(n), np.zeros(n),
                     np.zeros(n, dtype=bool))
        for key, sel in self._groups(x, y):
            ids = self.cells.get(key)
            if ids is not None:
                self._sample(out, sel, x[sel], y[sel], ids, floor)
        return out

    def past_bank(self, x, y) -> np.ndarray:
        """Meters past the nearest river's bank at each point, negative in the channel, inf where no river reaches."""
        return self.sample(x, y).past

    def fill(self, x, y, h) -> np.ndarray:
        """`h` raised at lake rims and along pinned reaches."""
        x, y = np.ravel(x), np.ravel(y)
        h = np.array(h, dtype=np.float64, copy=True).ravel()
        for key, sel in self._groups(x, y):
            lakes = self.lake_cells.get(key)
            if lakes is not None:
                for k in lakes:
                    h[sel] = self._rim(self.shores[k], x[sel], y[sel], h[sel])
            ids = self.levee_cells.get(key)
            if ids is not None:
                t = self.levees[ids]
                d, u = self._along(x[sel], y[sel], t)
                crest = t[:, 4] + u * (t[:, 5] - t[:, 4]) - np.maximum(d - t[:, 6], 0.0) * self.levee_slope
                w = np.clip((t[:, 6] + t[:, 7] - d) / (self.levee_fade * t[:, 7]), 0.0, 1.0)   # land falling away
                h[sel] += (w * w * (3.0 - 2.0 * w) * np.maximum(crest - h[sel][:, None], 0.0)).max(axis=1)   # past it
        return h

    def _rim(self, sh: Shore, x, y, h) -> np.ndarray:
        """A closed rim `sill` m over the level just past `Shore.zone`: the ground raised (never lowered) there,
        blending in over `rise` m from the shore's side and `sill_fade` m on the other."""
        short = np.flatnonzero(h < sh.level + self.sill)
        if not len(short):
            return h
        pts = shapely.points(x[short], y[short])
        d = shapely.distance(sh.ring, pts)
        out = sh.reach - self.sill_fade
        w = (np.clip((d - (out - self.rim_pad - self.rim_rise)) / self.rim_rise, 0.0, 1.0)
             * (1.0 - np.clip((d - out) / self.sill_fade, 0.0, 1.0)))
        w = w * w * (3.0 - 2.0 * w)
        on = w > 0.0
        if on.any():
            on[on] = ~shapely.contains_xy(sh.polygon, x[short[on]], y[short[on]])
            top = sh.level + self.sill
            h[short[on]] += w[on] * (top - h[short[on]])
        return h

    def rims(self, x, y, z, height: float, salt_height: float) -> tuple:
        """(how far each point lies down the bare rim of a lake, 1 at the level and 0 `height` m over it, or
        `salt_height` m over a salt flat; on a salt flat's rim)."""
        x, y, z = np.ravel(x), np.ravel(y), np.ravel(z)
        w, salt = np.zeros(len(x)), np.zeros(len(x), dtype=bool)
        for key, sel in self._groups(x, y):
            for k in self.lake_cells.get(key, ()):
                sh = self.shores[k]
                t = 1.0 - np.clip((z[sel] - sh.level) / (salt_height if sh.salt else height), 0.0, 1.0)
                on = np.flatnonzero(t > 0.0)
                if len(on):                  # it fades out `sill_fade` m past the zone on the flattest land
                    t[on] *= 1.0 - np.clip(shapely.distance(sh.zone, shapely.points(x[sel[on]], y[sel[on]]))
                                           / self.sill_fade, 0.0, 1.0)
                    w[sel[on]] = np.maximum(w[sel[on]], t[on] * t[on] * (3.0 - 2.0 * t[on]))
                    salt[sel[on]] |= sh.salt & (t[on] > 0.0)
        return w, salt

    def touches(self, poly) -> bool:
        """True when a river's reach or a lake's rim may touch the polygon's bounds."""
        x0, y0, x1, y1 = poly.bounds
        return any(self.near.flat[key] for key in self._squares(x0, y0, x1, y1))

    def cut(self, x, y, h, floor: bool = False, sample: Sample | None = None) -> np.ndarray:
        """`h` no higher than any river's surface, the top of a bank or a valley wall rounded, not a crease: a smooth
        minimum, over little height at the bank, where it must not reach the water, and more up the valley's walls.
        With `floor`, the valley without the channel: for the coarse lod1 terrain, whose 32 m points would drop
        into a channel only now and then. `sample`: this very call's `sample(x, y, floor)`, when the caller has it."""
        f = self.sample(x, y, floor) if sample is None else sample
        z, k = f.surface, f.round
        h = np.array(np.ravel(h), dtype=np.float64, copy=True)
        on = np.isfinite(z) & (z - h < k)
        if on.any():
            t = np.clip(0.5 + 0.5 * (z[on] - h[on]) / k[on], 0.0, 1.0)
            h[on] = z[on] + (h[on] - z[on]) * t - k[on] * t * (1.0 - t)
        return h

    def ground(self, x, y, h) -> np.ndarray:
        return self.cut(x, y, self.fill(x, y, h))

    def one(self, x: float, y: float, h: float) -> float:
        """`ground` at one point: one look-up off the rivers, the same array code on them."""
        key = max(min(int(y / CELL), self.n - 1), 0) * self.n + max(min(int(x / CELL), self.n - 1), 0)
        if not self.near.item(key):
            return h
        return float(self.ground(np.array([x]), np.array([y]), np.array([h]))[0])
