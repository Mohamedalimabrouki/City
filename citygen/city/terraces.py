"""Seaside cafe terraces (prompt 37): tables under parasols along the corniche, `[corniche.terrace]`.

Like the seafront cafes of La Marsa, Sidi Bou Said or Sousse:
- cafes facing the sea: a main wall on a seafront stretch (`Dresser.seaside`) is a cafe when the colonial cafe
  chance makes it one, or by its own chance `cafe` (city/dressing._front). Its terrace (stream
  `rng("terrace", "front", k)`): `tables` cafe tables (`cafe_set`, chairs along the wall) on its sidewalk, `reach` m
  out from the wall, `pitch` m apart, from the middle outward and within the wall; each under a parasol where the
  canopy fits (not under the cafe's awning, a palm crown or a lamp), else in the open. With chance `across`
  (`rng("terrace", "across", k)`) a second group across the road, in the palm gap without a lamp nearest the cafe:
  a row on the palm line (the promenade's building side), every table under a parasol, all of it within
  `row_reach` m of the curb, so the walkway beyond stays free;
- kiosk cafes: in a palm gap long enough and clear of the steps, with chance `kiosk` (`kiosk_spacing` m apart, stream
  `rng("terrace", "kiosk", street, palm index)`), a drinks kiosk (role `cafe_kiosk`) backing onto the railing and
  facing the promenade, `kiosk_tables` tables along the railing beside it, each under a parasol, all within
  `sea_reach` m of the sea edge; that gap gets no bench (city/corniche.Seafront).
Promenade groups only where the promenade is at least `min_width` m wide. A group's parasols share one color (role
`parasol`); each table turns a little off its row and its parasol's octagon at random (`rng("terrace", "table", ...)`).
Every table set is checked with its kit bounds, every canopy as a circle in its height band, against what is drawn
around (`Squares._obstacles`: trunks and crowns, street lamps, doors with their free zone, the buildings' wall
pieces; plus the seafront's lamps, benches and railing, the flights of steps and the pieces already placed); a
table stands on its sidewalk or on the promenade, never on the carriageway, and a canopy stays over them, clear of
the walls and `rail_clear` m inside the sea edge. Customers sit on the chairs (city/crowd.py, `[people.seats]
cafe_set`); some tables have a waiter (`[people.terrace]`).
"""
from __future__ import annotations

import math

import numpy as np
import shapely
from shapely.geometry import Point
from shapely.ops import substring

from .openings import piece_box
from .parking import street_frame

INF = 1e9


class Terraces:
    def __init__(self, seafront):
        from .dressing import DRESSED   # dressing imports this module
        self.DRESSED = DRESSED
        self.sf, self.d, self.plan = seafront, seafront.d, seafront.plan
        self.Placement, self.yaw_of = seafront.Placement, seafront.yaw_of
        self.cfg = seafront.cfg.get("terrace", {})
        fur = self.d.world.style.get("dressing", {}).get("furniture", {})
        radius, rim, top, _ = (float(v) for v in fur.get("parasol", [1.2, 2.15, 2.5, 0.7]))
        self.radius = radius
        self.band = (rim - float(fur.get("parasol_valance", 0.13)), top + 0.15)   # the canopy's heights
        self._walks = None
        self.size = float(self.d.world.cfg["tiles"]["size"])
        fps = self.d.footprints
        xy = shapely.get_coordinates(shapely.centroid(fps)) if fps else np.zeros((0, 2))
        cells, counts = np.unique(np.floor(xy / self.size).astype(np.int64), axis=0, return_counts=True)
        need = int(self.c("town_tile", 1))
        self.town = {(int(i), int(j)) for (i, j), n in zip(cells.tolist(), counts.tolist()) if n >= need}

    def c(self, key: str, default: float) -> float:
        return float(self.cfg.get(key, default))

    def ok(self) -> bool:
        return bool(self.cfg) and self.d.has("cafe_set")

    def in_town(self, x: float, y: float) -> bool:
        """Does the tile holding (x, y) draw some of the town (`town_tile` buildings)? A tile holding only the sea
        half of the promenade and the beach is light (about 300 KB): a terrace with its customers would grow it a fifth."""
        return (int(math.floor(x / self.size)), int(math.floor(y / self.size))) in self.town

    # --- the places ---------------------------------------------------------------------------------
    def kiosks(self, f, palms: list) -> dict:
        """{palm gap m: [kiosk placement]}: the kiosk cafes of a stretch, before its benches (a bench gives way)."""
        if not self.ok() or not self.d.has("cafe_kiosk"):
            return {}
        out: dict = {}
        last = -INF
        st = self.plan.streets[f.street]
        stairs = [st.line.project(Point(s[0], s[1])) for s in f.stairs]
        for m in range(len(palms) - 1):
            (da, ia), (db, _) = palms[m], palms[m + 1]
            mid = (da + db) / 2.0
            if db - da < self.c("kiosk_gap", 10.0) or mid - last < self.c("kiosk_spacing", 120.0):
                continue
            p, sea, width = self.sf._frame(f, mid)
            if width < self.c("min_width", 7.5):
                continue
            if any(abs(mid - s) < (db - da) / 2.0 + self.c("stair_clear", 1.2) for s in stairs):
                continue
            rng = self.d.rng("terrace", "kiosk", f.street, ia)
            if rng.random() >= self.c("kiosk", 0.2):
                continue
            name, _ = self.d.pick("cafe_kiosk", rng)
            piece = self.d.kit.pieces[name]
            curb = st.width / 2.0 - float(self.sf.cfg["curb"])
            q = p + sea * (curb + width - self.c("kiosk_back", 0.3) - float(piece.bounds[1][2]))
            if not self.in_town(float(q[0]), float(q[1])):
                continue
            kiosk = self.Placement(name, float(q[0]), float(q[1]), 0.0, self.yaw_of(-sea))
            lit = self.d.rng("terrace", "lit", f.street, ia).random() < self.c("kiosk_lit", 0.6)
            if lit and name + "_lit" in self.d.kit.pieces:
                kiosk.piece = name + "_lit"
            foot = piece_box(piece, kiosk.x, kiosk.y, kiosk.yaw, 0.0)[0]
            if not self._on_promenade(f, foot, self.c("sea_reach", 2.8), sea_side=True):
                continue
            out[m] = [kiosk]
            last = mid
        return out

    def items(self, f, palms: list, placed: list, kiosks: dict) -> list:
        """The terraces of one stretch: the corniche cafes' (sidewalk, then across the road), then the kiosk cafes'."""
        if not self.ok():
            return []
        out: list = []
        st = self.plan.streets[f.street]
        lamp_every = int(self.sf.cfg["lamp_every"])
        free = [m for m in range(len(palms) - 1) if m % lamp_every != 0 and m not in kiosks]   # gaps without a lamp
        taken: set = set()
        for k, main in self._cafes(f):
            out += self._sidewalk(k, main, placed + out)
            rng = self.d.rng("terrace", "across", k)
            if rng.random() >= self.c("across", 0.6) or not free:
                continue
            d0 = float(st.line.project(Point(main.at(0.5))))
            m = min(free, key=lambda g: (abs((palms[g][0] + palms[g + 1][0]) / 2.0 - d0), g))
            if m in taken or abs((palms[m][0] + palms[m + 1][0]) / 2.0 - d0) > self.c("across_reach", 16.0):
                continue
            taken.add(m)
            out += self._across(f, palms, m, k, rng, placed + out)
        for m in sorted(kiosks):
            out += kiosks[m] + self._by_kiosk(f, palms, m, kiosks[m][0], placed + out)
        return out

    def _cafes(self, f) -> list:
        """[(building, main facade)] of the cafes facing the stretch, in building order."""
        d = self.d
        st = self.plan.streets[f.street]
        if d.fp_tree is None:
            return []
        band = substring(st.line, f.span[0], f.span[1]).buffer(st.width / 2.0 + 6.0, cap_style="flat")
        out = []
        for k in sorted(int(i) for i in d.fp_tree.query(band, predicate="intersects")):
            if self.plan.buildings[k].kind not in self.DRESSED:
                continue
            main, _, kind, _ = d.front_of(k)
            if kind == "cafe" and d.seaside(main) is f:
                out.append((k, main))
        return out

    # --- the groups ---------------------------------------------------------------------------------
    def _sidewalk(self, k: int, main, placed: list) -> list:
        """Tables on the cafe's sidewalk, chairs along the wall, under parasols where they fit."""
        rng = self.d.rng("terrace", "front", k)
        lo, hi = (int(v) for v in self.cfg.get("tables", [2, 4]))
        count = int(rng.integers(lo, hi + 1))
        color = self.d.pick("parasol", rng) if self.d.has("parasol") else None
        pitch, half = self.c("pitch", 2.6), float(self.d.kit.pieces["cafe_set"].bounds[1][0])
        room = main.length / 2.0 - self.c("wall_margin", 0.5) - half
        c = main.at(0.5) + main.n * self.c("reach", 1.7)
        slots = [s for s in _offsets(count + 2, pitch) if abs(s) <= room]
        region = Point(c).buffer(main.length / 2.0 + 4.0)
        boxes = self._obstacles(region, True, placed)
        inside = self._sidewalks(region)
        return self._row(("front", k), [c + main.u * s for s in slots], math.atan2(main.u[1], main.u[0]), count,
                         color and color[0], boxes, lambda g: inside.contains(g), lambda g: inside.contains(g), False)

    def _across(self, f, palms: list, m: int, k: int, rng, placed: list) -> list:
        """A row of tables under parasols on the palm line across the road from cafe k."""
        lo, hi = (int(v) for v in self.cfg.get("across_tables", [2, 3]))
        count = int(rng.integers(lo, hi + 1))
        color = self.d.pick("parasol", rng)[0] if self.d.has("parasol") else None
        mid = (palms[m][0] + palms[m + 1][0]) / 2.0
        p, sea, width = self.sf._frame(f, mid)
        if width < self.c("min_width", 7.5) or color is None:
            return []
        st = self.plan.streets[f.street]
        row = st.width / 2.0 - float(self.sf.cfg["curb"]) + float(self.sf.cfg["palm_inset"])
        ds = mid + _offsets(count, self.c("pitch", 2.6))
        q, n = street_frame(st.line, ds)
        pts = q + n * f.side * row
        t = np.array([sea[1], -sea[0]])
        region = Point(p).buffer((palms[m + 1][0] - palms[m][0]) / 2.0 + 6.0)
        boxes = self._obstacles(region, False, placed + self._stairs(f))
        reach = self.c("row_reach", 2.3)
        return self._row(("across", k), list(pts), math.atan2(t[1], t[0]), count, color, boxes,
                         lambda g: self._on_promenade(f, g, reach), lambda g: self._canopy_fits(f, g), True)

    def _by_kiosk(self, f, palms: list, m: int, kiosk, placed: list) -> list:
        """Tables along the railing either side of a kiosk cafe, each under a parasol."""
        rng = self.d.rng("terrace", "kiosk", f.street, palms[m][1], "tables")
        lo, hi = (int(v) for v in self.cfg.get("kiosk_tables", [2, 4]))
        count = int(rng.integers(lo, hi + 1))
        color = self.d.pick("parasol", rng)[0] if self.d.has("parasol") else None
        if color is None:
            return []
        mid = (palms[m][0] + palms[m + 1][0]) / 2.0
        p, sea, width = self.sf._frame(f, mid)
        st = self.plan.streets[f.street]
        t = np.array([sea[1], -sea[0]])
        pc = self.d.kit.pieces[kiosk.piece]
        clear = float(self.d.squares().c("piece_clear", 0.2))           # obstacles come grown by this
        first = float(max(-pc.bounds[0][0], pc.bounds[1][0])) + self.radius + self.c("parasol_clear", 0.15) + clear + 0.05
        pitch = self.c("pitch", 2.6)
        along = [side * (first + (j // 2) * pitch) for j, side in zip(range(4), (1.0, -1.0, 1.0, -1.0))]
        ds = mid + np.array(along)
        q, n = street_frame(st.line, ds)
        out_d = [st.width / 2.0 - float(self.sf.cfg["curb"]) + self.sf._frame(f, float(v))[2] - self.radius
                 - self.c("rail_clear", 0.2) - 0.05 for v in ds]                  # the sea edge bends a little
        pts = q + n * f.side * np.array(out_d)[:, None]
        region = Point(p).buffer(first + 2 * pitch + 3.0)
        boxes = self._obstacles(region, False, placed + [kiosk] + self._stairs(f))
        reach = self.c("sea_reach", 2.8)
        return self._row(("kiosk", f.street, palms[m][1]), list(pts), math.atan2(t[1], t[0]), count, color, boxes,
                         lambda g: self._on_promenade(f, g, reach, sea_side=True), lambda g: self._canopy_fits(f, g), True)

    def _row(self, key: tuple, slots: list, yaw0: float, count: int, color, boxes: tuple, table_ok, canopy_ok,
             shaded: bool) -> list:
        """Up to `count` table sets at the slots in order, each under a parasol where its canopy fits (always, with
        `shaded`); each placed piece becomes an obstacle for the next."""
        d = self.d
        table = d.kit.pieces["cafe_set"]
        jitter, pclear, tclear = self.c("jitter", 0.12), self.c("parasol_clear", 0.15), self.c("piece_clear", 0.15)
        polys, lo, hi = (list(v) for v in boxes)
        out: list = []
        if not slots:
            return out
        xy = np.asarray(slots, dtype=np.float64)
        zs = np.atleast_1d(d.ground.surface(xy[:, 0], xy[:, 1]))          # one ground query per row
        for j, q in enumerate(slots):
            if sum(p.piece == "cafe_set" for p in out) >= count:
                break
            rng = d.rng("terrace", "table", *key, j)
            yaw, turn = yaw0 + rng.uniform(-jitter, jitter), rng.uniform(0.0, math.pi / 4)
            z = float(zs[j])
            foot, z0, z1 = piece_box(table, float(q[0]), float(q[1]), yaw, z)
            if not self.in_town(float(q[0]), float(q[1])) or not table_ok(foot) \
                    or _hits(foot.buffer(tclear), z0, z1, polys, lo, hi):
                continue
            canopy = Point(float(q[0]), float(q[1])).buffer(self.radius, quad_segs=2)
            c0, c1 = z + self.band[0], z + self.band[1]
            shade = color is not None and canopy_ok(canopy) and not _hits(canopy.buffer(pclear), c0, c1, polys, lo, hi)
            if shaded and not shade:
                continue
            out.append(self.Placement("cafe_set", float(q[0]), float(q[1]), 0.0, yaw))
            polys.append(foot), lo.append(z0), hi.append(z1)
            if shade:
                out.append(self.Placement(color, float(q[0]), float(q[1]), 0.0, yaw + turn))
                polys.append(canopy), lo.append(c0), hi.append(c1)
        return out

    # --- checks -------------------------------------------------------------------------------------
    def _obstacles(self, region, dress: bool, extra: list) -> tuple:
        x0, y0, x1, y1 = region.bounds
        pad = 4.0                                                    # the largest piece's reach from its anchor
        stairs = [p for p in extra if isinstance(p, shapely.Geometry) and p.intersects(region)]
        pieces = [p for p in extra if not isinstance(p, shapely.Geometry) and p.piece in self.d.kit.pieces
                  and x0 - pad <= p.x <= x1 + pad and y0 - pad <= p.y <= y1 + pad]
        polys, lo, hi = self.d.squares()._obstacles(region, dress=dress, extra=pieces)
        if stairs:
            polys = np.concatenate([polys, np.array(stairs, dtype=object)])
            lo, hi = np.concatenate([lo, np.full(len(stairs), -INF)]), np.concatenate([hi, np.full(len(stairs), INF)])
        return polys, lo, hi

    def _stairs(self, f) -> list:
        """The flights of steps as circles at their head: nothing stands in front of them."""
        r = float(self.sf.cfg["stair"][0]) / 2.0 + self.c("stair_clear", 1.2)
        return [Point(s[0], s[1]).buffer(r, quad_segs=4) for s in f.stairs]

    def _sidewalks(self, region):
        """The sidewalks around a region, less the building footprints."""
        walks = [w.polygon for w in self.plan.walks if w.kind == "sidewalk" and w.polygon.intersects(region)]
        out = shapely.union_all(walks) if walks else shapely.Polygon()
        if self.d.fp_tree is not None:
            near = [self.d.footprints[int(i)] for i in self.d.fp_tree.query(region, predicate="intersects")]
            if near:
                out = out.difference(shapely.union_all(near))
        shapely.prepare(out)
        return out

    def promenade(self):
        """The seafront walks as one shape (prepared)."""
        if self._walks is None:
            polys = [w.polygon for w in self.plan.walks if w.kind == "seafront"]
            self._walks = shapely.union_all(polys).buffer(0.01) if polys else shapely.Polygon()
            shapely.prepare(self._walks)
        return self._walks

    def _on_promenade(self, f, geom, reach: float, sea_side: bool = False) -> bool:
        """On the promenade, every corner within `reach` m of its curb line (or of its sea edge)."""
        if not self.promenade().contains(geom):
            return False
        pts = shapely.points(shapely.get_coordinates(geom))
        return bool((shapely.distance(f.sea if sea_side else f.edge, pts) <= reach).all())

    def _canopy_fits(self, f, canopy) -> bool:
        """A canopy over the promenade, `rail_clear` m inside the sea edge."""
        return self.promenade().contains(canopy) and canopy.distance(f.sea) >= self.c("rail_clear", 0.2)


def _offsets(count: int, pitch: float) -> np.ndarray:
    """`count` places `pitch` m apart centered on 0, nearest the middle first."""
    s = (np.arange(count) - (count - 1) / 2.0) * pitch
    return s[np.argsort(np.abs(s) + 1e-6 * (s < 0), kind="stable")]


def _hits(geom, z0: float, z1: float, polys: list, lo: list, hi: list) -> bool:
    if not polys:
        return False
    near = (np.asarray(lo) < z1) & (np.asarray(hi) > z0)
    return bool(near.any() and shapely.intersects(geom, np.asarray(polys, dtype=object)[near]).any())
