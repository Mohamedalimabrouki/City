"""Bridges (prompt 62): every crossing a street or a road makes of a river.

A city's bridges are planned with the city (`plan_bridges`, `raise_decks`): each is a `Street(kind="bridge")` after
the lanes and a `Bridge` record in `CityPlan.bridges`, never a building. A country road's are worked out when a tile
asks (`road_bridges`), from the road, the rivers and the ground alone, so `world` does not change. Roads share corridors:
where two decks overlap the wider road holds the structure and the other lies on it (`follow`).

`deck_profile` is the one rule for the height: the least concave majorant of what the deck must clear, between its
ends. Where the banks stand higher than the river needs that is a straight line, a viaduct; where they lie low it is a
ramp up from each end and a level top. A city bridge's ends are fixed on its streets, and its air gives way, down to
`clearance[0]`, before its ramps do; a country bridge's ends move out along the road until the ramps meet `grade`.
The carve and `Ground.height` never change: a deck is only what is drawn over them.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
import shapely
from shapely import STRtree
from shapely.geometry import LineString, Point, box
from shapely.ops import substring

from .geo import lines
from .ground import STREET_LIFT, Ground
from .model import Bridge, Street
from .river import Crossing, crossing_nodes

MAIN = ("arterial", "boulevard", "ring", "corniche")      # `river.cut_streets` may cut any street of a city
SIDE = ("street", "souk", "alley", "impasse")
RANK = {"connector": 0, **dict.fromkeys(MAIN, 1), **dict.fromkeys(SIDE, 2)}    # who stays when two crossings come near
KINDS = {"local": "arch", "regional": "arch", "national": "beam", "connector": "beam", **dict.fromkeys(MAIN, "beam"),
         **dict.fromkeys(SIDE, "arch")}


# --- the height of a deck ----------------------------------------------------------------------------------

def dilate(s: np.ndarray, y: np.ndarray, grade: float) -> np.ndarray:
    """The least function over `y` that climbs no faster than `grade`."""
    out = np.array(y, dtype=np.float64)
    ds = grade * np.diff(s)
    for i in range(1, len(out)):
        out[i] = max(out[i], out[i - 1] - ds[i - 1])
    for i in range(len(out) - 2, -1, -1):
        out[i] = max(out[i], out[i + 1] - ds[i])
    return out


def concave(s: np.ndarray, y: np.ndarray) -> np.ndarray:
    """The least concave majorant of the points (s, y), at s."""
    keep = [0]
    for i in range(1, len(s)):
        while len(keep) > 1:
            a, b = keep[-2], keep[-1]
            if (y[b] - y[a]) * (s[i] - s[a]) > (y[i] - y[a]) * (s[b] - s[a]):
                break
            keep.pop()
        keep.append(i)
    return np.interp(s, s[keep], y[keep])


def rounded(s: np.ndarray, z: np.ndarray, length: float) -> np.ndarray:
    """`z` averaged over `length` m, the window closing at both ends, so the ends and a straight line do not move."""
    area = np.concatenate([[0.0], np.cumsum(0.5 * (z[1:] + z[:-1]) * np.diff(s))])
    slope = np.diff(z) / np.diff(s)

    def integral(t):
        i = np.clip(np.searchsorted(s, t, side="right") - 1, 0, len(s) - 2)
        d = t - s[i]
        return area[i] + z[i] * d + 0.5 * slope[i] * d * d

    half = np.minimum(0.5 * length, np.minimum(s - s[0], s[-1] - s))
    on = half > 1e-9
    out = z.copy()
    out[on] = (integral(s[on] + half[on]) - integral(s[on] - half[on])) / (2.0 * half[on])
    return out


def ramp_ends(s, ground, water, air: float, depth: float, grade: float) -> tuple:
    """(i0, i1): where ramps at `grade` down from a deck `air` m over the water meet `ground`, or the ends of `s`."""
    wet = np.isfinite(water)
    cone = dilate(s, np.where(wet, water + air + depth, -np.inf), grade)
    first, last = (int(k) for k in np.flatnonzero(wet)[[0, -1]])
    met = np.flatnonzero(ground >= cone)
    return (int(met[met < first].max()) if (met < first).any() else 0,
            int(met[met > last].min()) if (met > last).any() else len(s) - 1)


def deck_profile(s, ground, water, air: tuple, depth: float, grade: float, crown: float) -> tuple:
    """(z, air taken): the top of a deck at stations `s`, from the first, its end, to the last, its other end.

    `ground` is the least height at each station and the height of the two ends; `water` the level under it (inf off the
    water); `air` the (least, wished) meters between water and soffit: the air gives way to `grade` down to its least, then
    the grade gives way. The crown is rounded over `crown` m, never under what is required."""
    wet = np.isfinite(water)
    reach = np.minimum(ground[0] + grade * (s - s[0]), ground[-1] + grade * (s[-1] - s))
    room = float((reach - water - depth)[wet].min()) - 0.25 * grade * crown
    take = float(np.clip(room, air[0], air[1]))
    need = ground.copy()
    need[wet] = np.maximum(need[wet], water[wet] + take + depth)
    lifted = need.copy()
    z = rounded(s, concave(s, lifted), crown)
    for _ in range(6):          # rounding takes a little off the top: what it takes is put back first
        short = np.maximum(need - z, 0.0)
        if short.max() <= 1e-3:
            break
        lifted += short + 1e-3 * (short > 0.0)
        z = rounded(s, concave(s, lifted), crown)
    return z, take


def thin(s: np.ndarray, z: np.ndarray) -> tuple:
    """Stations without those a straight line between their neighbors holds to 1 mm."""
    out = [0]
    for i in range(1, len(s) - 1):
        a = out[-1]
        run = np.arange(a + 1, i + 2)
        if np.abs(z[run] - np.interp(s[run], s[[a, i + 1]], z[[a, i + 1]])).max() > 1e-3:
            out.append(i)
    out.append(len(s) - 1)
    return s[out], z[out]


def air_wished(cfg: dict, water_width: float) -> float:
    """Meters of air a bridge should leave over `water_width` meters of water: a stream needs less than a river."""
    least, per, most = (float(v) for v in cfg["clearance"])
    return float(np.clip(least + per * water_width, least, most))


def opening(s, z, floor, depth: float, channel: tuple, cfg: dict) -> tuple:
    """The open part (s0, s1): the channel and all round it, out to where less than `open_air` m is left under the soffit.
    `s` are stations a meter apart, not thinned: a straight ramp has no station of its own where its air runs out."""
    high = z - depth - floor >= float(cfg["open_air"])
    a, b = channel
    lo, hi = int(np.searchsorted(s, a)), int(np.searchsorted(s, b))
    while lo > 0 and high[lo - 1]:
        lo -= 1
    while hi < len(s) - 1 and high[hi + 1]:
        hi += 1
    return float(min(s[lo], a)), float(max(s[hi], b))


def stations(kind: str, span: tuple, channel: tuple, cfg: dict, rise: float = np.inf) -> np.ndarray:
    """Stations of a bridge's piers: an odd number of arches, none longer than `arch_span` or than its `rise` allows
    (`arch_flat`: a stone arch this flat is no arch) nor shorter than `arch_least`, or as many beams as its length takes;
    none in the water of a stream narrower than `pier_water`."""
    length = span[1] - span[0]
    if kind == "arch":
        n = np.ceil(length / min(float(cfg["arch_span"]), max(rise, 0.5) / float(cfg["arch_flat"])) - 0.01)
        n = max(int(min(n, length // float(cfg["arch_least"]))), 1)
        n += 1 - n % 2
        n -= 2 * (n > 1 and length / n < float(cfg["arch_least"]))
    else:
        n = max(int(np.ceil(length / float(cfg["beam_span"]))), 1)
    at = span[0] + length * np.arange(1, n) / n
    a, b = channel
    if b - a < float(cfg["pier_water"]) and len(at):
        inside = (at > a) & (at < b)
        at[inside] = np.where(at[inside] - a < b - at[inside], a, b)
    at = np.unique(np.round(at, 2))
    return at[(at > span[0]) & (at < span[1])]


# --- the choice of a city's bridges ------------------------------------------------------------------------

@dataclass
class Spot:
    """A bridge's place: the line between its two streets, where it crosses which river, how far along it."""
    river: int
    along: float
    line: object
    kind: str
    width: float
    faces: int = 2        # a new bridge: on how many banks it meets a junction or a street's end


def _unit(a, b) -> np.ndarray:
    d = np.array([b[0] - a[0], b[1] - a[1]], dtype=np.float64)
    return d / max(float(np.hypot(*d)), 1e-9)


class Site:
    """The plan a bridge has to fit in: streets, what stands on the land, the rivers through the city."""

    def __init__(self, ctx, streets: list, solid: list):
        self.ctx, self.streets = ctx, streets
        self.cfg = ctx.style["bridges"]
        self.lines = [st.line for st in streets]
        self.tree = STRtree(self.lines)
        self.surfaces = [st.line.buffer(st.width / 2, cap_style="flat") for st in streets]
        self.solid = solid + self.surfaces
        self.solid_tree = STRtree(self.solid)
        self.surface_tree = STRtree(self.surfaces)
        area = box(*ctx.boundary.bounds).buffer(float(self.cfg["reach"]))
        coords = ((k, r.coords) for k, r in enumerate(ctx.world.carve.rivers) if len(r.coords) > 1)
        self.rivers = {k: line for k, line in ((k, LineString(c)) for k, c in coords) if line.intersects(area)}
        self.left = 0            # stretches of river where no new bridge found a place
        self.dropped = 0         # crossings left out: too near a better one, or no place for a deck

    def crossing_point(self, line) -> tuple | None:
        """(river, meters along it, point) where `line` crosses a river, the point nearest its middle, or None."""
        mid = line.interpolate(0.5, normalized=True)
        found = []
        for k, river in self.rivers.items():
            hit = river.intersection(line)
            for p in getattr(hit, "geoms", [hit]):
                if not p.is_empty and p.geom_type == "Point":
                    found.append((p.distance(mid), k, p))
        if not found:
            return None
        _d, k, p = min(found, key=lambda f: f[:2])
        return k, self.rivers[k].project(p), p

    def normal(self, k: int, along: float) -> np.ndarray:
        river = self.rivers[k]
        a = river.interpolate(max(along - 15.0, 0.0))
        b = river.interpolate(min(along + 15.0, river.length))
        t = _unit((a.x, a.y), (b.x, b.y))
        return np.array([-t[1], t[0]])

    def first_street(self, p, u: np.ndarray, reach: float) -> float | None:
        """Meters from `p` along `u` to the first street, or None within `reach`."""
        ray = LineString([(p.x, p.y), (p.x + u[0] * reach, p.y + u[1] * reach)])
        ids = self.tree.query(ray, predicate="intersects")
        if not len(ids):
            return None
        hits = shapely.intersection(np.asarray(self.lines, dtype=object)[ids], ray)
        return float(shapely.distance(p, hits).min())

    def landing(self, end, p, u: np.ndarray, reach: float) -> tuple:
        """Where a crossing that ends at `end`, coming from `p` along `u`, meets a street's center line."""
        q = Point(end)
        near = self.lines[int(self.tree.nearest(q))]
        if near.distance(q) < 0.05:
            return tuple(end)
        d = self.first_street(p, u, reach)
        if d is not None:
            return (p.x + u[0] * d, p.y + u[1] * d)
        got = near.interpolate(near.project(q))
        return (got.x, got.y)

    def across(self, k: int, along: float, side: np.ndarray, reach: float) -> LineString | None:
        """The line through the river at `along`, square to it, from the first street on one bank to the first on the
        other, running the way `side` points."""
        along = min(max(along, 0.0), self.rivers[k].length)
        p = self.rivers[k].interpolate(along)
        n = self.normal(k, along)
        n = n if float(n @ side) >= 0.0 else -n
        a, b = self.first_street(p, -n, reach), self.first_street(p, n, reach)
        if a is None or b is None:
            return None
        return LineString([(p.x - n[0] * a, p.y - n[1] * a), (p.x + n[0] * b, p.y + n[1] * b)])

    def clear(self, line, width: float) -> bool:
        """True when a deck on `line` stands on no block, building or street, and over a river."""
        if self.crossing_point(line) is None:
            return False
        e0, e1 = self.ends(line, width)
        if e1 - e0 < 1.0:
            return False
        deck = substring(line, e0, e1).buffer(width / 2, cap_style="flat")
        ids = self.solid_tree.query(deck, predicate="intersects")
        return all(deck.intersection(self.solid[int(i)]).area < 1.0 for i in ids)

    def ends(self, line, width: float) -> tuple:
        """(s0, s1) along `line` where the whole width of its ribbon has left the streets it joins."""
        ids = self.surface_tree.query(line.buffer(width / 2 + 1.0), predicate="intersects")
        drawn = shapely.union_all([self.surfaces[int(i)] for i in ids]) if len(ids) else None
        s0, s1 = 0.0, line.length
        if drawn is None:
            return s0, s1
        for off in (-0.5 * width + 0.05, 0.0, 0.5 * width - 0.05):
            edge = line.offset_curve(off) if off else line
            for part in lines(edge.difference(drawn)):
                a, b = (edge.project(Point(part.coords[i])) for i in (0, -1))
                if b - a > 0.5 * edge.length or (a < 0.5 * edge.length < b):      # the part over the river
                    s0, s1 = max(s0, min(a, b)), min(s1, max(a, b))
        return s0, s1

    def place(self, c: Crossing) -> Spot | None:
        """A crossing's place: its own chord within `skew` of the river's normal, and always for a connector, or for a
        link between two banks of the graph; else the river's normal through the same point."""
        a, b = c.line.coords[0], c.line.coords[-1]
        chord = LineString([a, b])
        got = self.crossing_point(chord)
        if got is None:
            self.dropped += 1
            return None
        k, along, p = got
        u = _unit(a, b)
        reach = 0.5 * chord.length + float(self.ctx.kc["arterial_width"]) * 2.0
        ends = (self.landing(a, p, -u, reach), self.landing(b, p, u, reach))
        own = LineString(ends)
        skew = float(np.degrees(np.arccos(min(abs(float(u @ self.normal(k, along))), 1.0))))
        tries = [own]
        if c.kind == "arterial":
            slides = float(self.cfg["slide"]) * np.array([0.0, *[d for n in range(1, 7) for d in (-n, n)]])
            ways = [self.across(k, along + float(d), u, float(self.cfg["reach"])) for d in slides]
            ways = [w for w in ways if w is not None]
            tries = ways + tries if skew > float(self.cfg["skew"]) else tries + ways
        for line in tries:
            if self.clear(line, c.width):
                got = self.crossing_point(line)
                return Spot(got[0], got[1], line, c.kind, c.width)
        self.dropped += 1
        return None

    def thin_out(self, spots: list, graph: tuple) -> list:
        """Of crossings within `gap` m along a river the higher kind stays, unless it alone joins two parts of the city."""
        gap = float(self.cfg["gap"])
        kept, out = [], []
        for sp in sorted(spots, key=lambda sp: (RANK[sp.kind], sp.river, sp.along)):
            near = any(o.river == sp.river and abs(o.along - sp.along) < gap for o in kept)
            (out if near else kept).append(sp)
        nodes, edges = graph
        parent = list(range(len(nodes)))

        def root(a: int) -> int:
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a

        def links(group: list) -> list:
            return crossing_nodes(edges, [Crossing(sp.line, sp.kind, sp.width) for sp in group])

        for _k, _line, a, b in edges:
            parent[root(a)] = root(b)
        for a, b in links(kept):
            parent[root(a)] = root(b)
        for sp, (a, b) in zip(out, links(out)):
            if root(a) != root(b):
                parent[root(a)] = root(b)
                kept.append(sp)
            else:
                self.dropped += 1
        return sorted(kept, key=lambda sp: spots.index(sp))

    def stretches(self, k: int) -> list:
        """(from, to) in meters along river k, where it runs through the city with streets on both banks."""
        step, reach = float(self.cfg["stretch_step"]), float(self.cfg["reach"])
        river = self.rivers[k]
        out = []
        for piece in lines(river.intersection(self.ctx.boundary)):
            a, b = sorted(river.project(Point(piece.coords[i])) for i in (0, -1))
            ds = np.arange(a, b + step, step)
            both = [self.across(k, float(d), np.array([1.0, 0.0]), reach) is not None for d in ds]
            edges = np.flatnonzero(np.diff(np.r_[False, both, False].astype(np.int8)))
            out += [(float(ds[i]), float(ds[j - 1])) for i, j in edges.reshape(-1, 2) if j - 1 > i]
        return out

    def candidates(self, k: int, lo: float, hi: float, graph: tuple) -> list:
        """Spots on river k between `lo` and `hi`: where a street's junction or end faces the river, square to it, the
        best when the far bank has one too, or else its first street, in mid-block; failing those, any place along the
        quays."""
        nodes, edges = graph
        reach, snap = float(self.cfg["reach"]), float(self.cfg["snap"])
        width = float(self.ctx.style["district"]["residential"]["street_width"])
        ks = [(k2, a, b) for k2, _line, a, b in edges if self.streets[k2].kind != "impasse"]
        degree = np.bincount([n for _k, a, b in ks for n in (a, b)], minlength=len(nodes))
        river = self.rivers[k]
        xy = np.asarray(nodes, dtype=np.float64)
        pts = shapely.points(xy)
        on = np.flatnonzero((degree != 0) & (degree != 2) & (shapely.distance(river, pts) < reach))
        out = []
        for j in on.tolist():
            along = river.project(pts[j])
            if not lo <= along <= hi:
                continue
            p = river.interpolate(along)
            far = (float(xy[j, 0]), float(xy[j, 1]))
            off = p.distance(pts[j])
            if off < 1.0:
                continue
            u = _unit(far, (p.x, p.y))
            near = self.first_street(p, -u, reach)
            d = self.first_street(p, u, reach)
            if near is None or d is None or near < off - 1.0:
                continue
            q = np.array([p.x + u[0] * d, p.y + u[1] * d])
            gaps = np.hypot(*(xy[on] - q).T)
            both = gaps.min() <= snap
            q = xy[on][int(np.argmin(gaps))] if both else q
            out.append(Spot(k, along, LineString([far, tuple(q.tolist())]), "street", width, 2 if both else 1))
        for along in np.arange(lo, hi, float(self.cfg["stretch_step"])).tolist():
            line = self.across(k, along, np.array([1.0, 0.0]), reach)
            if line is not None:
                out.append(Spot(k, along, line, "street", width, 0))
        return sorted(out, key=lambda sp: (sp.along, sp.line.coords[0]))

    def fill(self, k: int, spots: list, graph: tuple) -> list:
        """New bridges, so that no stretch of river runs more than `every` m between bridges or from one to its end."""
        every, gap = float(self.cfg["every"]), float(self.cfg["gap"])
        out = []
        at = sorted(sp.along for sp in spots if sp.river == k)
        for a, b in self.stretches(k):
            pool = self.candidates(k, a, b, graph)
            before = [d for d in at if a - every < d <= a]      # a hole in the streets is no bridge: count across it
            here = before[-1] if before else a
            while b - here > every:
                ahead = [d for d in at if d > here]
                if ahead and ahead[0] - here <= every:
                    here = ahead[0]
                    continue
                aim = here + 0.9 * every
                near = [sp for sp in pool if here + gap <= sp.along <= here + every
                        and all(abs(sp.along - d) >= gap for d in at)]
                near.sort(key=lambda sp: (-sp.faces, abs(sp.along - aim), sp.along))
                got = next((sp for sp in near if self.clear(sp.line, sp.width)), None)
                if got is None:
                    self.left += 1
                    here = ahead[0] if ahead else b
                    continue
                out.append(got)
                at = sorted(at + [got.along])
                here = got.along
        return out


def plan_bridges(ctx, streets: list, links: list, solid: list) -> tuple:
    """(crossings, decks, bridges): the crossings that hold a bridge, each bridge's `Street` and its `Bridge`, its heights
    still to come (`raise_decks`, on the finished plan). `solid`: what stands on the land besides the streets."""
    from ..export.streets import street_graph
    graph = street_graph(streets, float(ctx.world.cfg["street_graph"]["grid"]))
    site = Site(ctx, streets, solid)
    spots = [sp for sp in (site.place(c) for c in links) if sp is not None]
    spots = site.thin_out(spots, graph)
    for k in sorted(site.rivers):
        spots += site.fill(k, spots, graph)
    surface = str(ctx.style.get("streets", {}).get("surface", {}).get("bridge", "asphalt"))
    crossings, decks, bridges = [], [], []
    for i, sp in enumerate(spots):
        crossings.append(Crossing(sp.line, sp.kind, sp.width))
        decks.append(Street("bridge", sp.width, sp.line, surface))
        bridges.append(Bridge(sp.kind, sp.line, sp.width, len(streets) + i, site.ends(sp.line, sp.width), river=sp.river,
                              carries=sp.kind))
    ctx.bridge_notes = {"dropped": site.dropped, "left": site.left}
    return crossings, decks, bridges


def off_decks(trees: list, bridges: list) -> list:
    """`trees` without those on a deck."""
    if not bridges or not trees:
        return trees
    tree = STRtree([b.deck for b in bridges])
    hit = set(tree.query(shapely.points([(t.x, t.y) for t in trees]), predicate="intersects")[0].tolist())
    return [t for i, t in enumerate(trees) if i not in hit]


# --- a deck's heights --------------------------------------------------------------------------------------

def _offsets(x, y, width: float) -> tuple:
    """The points `width / 2` m off the center line (x, y), on either side."""
    tx, ty = np.gradient(x), np.gradient(y)
    n = np.maximum(np.hypot(tx, ty), 1e-9)
    nx, ny = -ty / n * width / 2, tx / n * width / 2
    return (x + nx, y + ny), (x - nx, y - ny)


def _carried(ground, x, y, width: float, floor, sample) -> np.ndarray:
    """The ground a deck must clear: by the water, where it is level across, the highest under its middle and its two
    edges; off it a ramp leans with the land (`Bridge.tilt`), and the middle will do."""
    left, right = _offsets(x, y, width)
    high = np.maximum.reduce([floor, ground.height(*left), ground.height(*right)])
    return np.where(sample.edge < 1.0, high, floor)


def _lean(ground, x, y, width: float) -> tuple:
    """Rise of the land to the left, in meters per meter, at the two ends of the points (x, y)."""
    left, right = _offsets(x, y, width)
    rise = (ground.height(*left) - ground.height(*right)) / width
    return float(rise[0]), float(rise[-1])


def _channel(carve, x, y, width: float) -> tuple:
    """(True on the water or a dry oued's floor under any part of the width, the rivers on the center line, the rivers
    under each of the middle and the two edges or -1). A river falls under a deck that crosses it aslant: `water` is the
    highest under its width."""
    left, right = _offsets(x, y, width)
    mid, a, b = carve.sample(x, y), carve.sample(*left), carve.sample(*right)
    known = np.isfinite(a.water) & np.isfinite(b.water)
    mid.water = np.where(known, np.maximum.reduce([mid.water, a.water, b.water]), mid.water)
    under = np.stack([np.where(q.edge < 0.0, q.river, -1) for q in (mid, a, b)]).astype(np.int64)
    return np.minimum.reduce([mid.edge, a.edge, b.edge]) < 0.0, mid, under


def wet_parts(grid, wet, water) -> tuple:
    """((s0, s1, level), ...): the stretches of stations `wet`, each with its highest `water`: a long deck can cross two arms
    of a river, with dry land and another level between them."""
    edges = np.flatnonzero(np.diff(np.r_[False, wet, False].astype(np.int8))).reshape(-1, 2)
    return tuple((float(grid[i]), float(grid[j - 1]), float(water[i:j].max())) for i, j in edges.tolist())


def skew_of(carve, b: Bridge, cfg: dict) -> float:
    """k of the map (s, d) to (s + k d, d) that lines a bridge's piers up with the flow: the tangent of the angle between
    the deck's normal and the river where the deck crosses most water, the river read `skew_reach` m each way, past its
    wiggles. Square under `skew_least` degrees; at most `skew_most`, and no more than the ramps leave room for."""
    a, c, _level = max(b.parts, key=lambda part: part[1] - part[0])
    m = 0.5 * (a + c)
    p, q = (b.axis.interpolate(np.clip(m + t, 0.0, b.axis.length)) for t in (-5.0, 5.0))
    t = _unit((p.x, p.y), (q.x, q.y))
    river = LineString(carve.rivers[b.river].coords)
    along, reach = river.project(b.axis.interpolate(m)), float(cfg["skew_reach"])
    p, q = (river.interpolate(np.clip(along + d, 0.0, river.length)) for d in (-reach, reach))
    flow = _unit((p.x, p.y), (q.x, q.y))
    across = float(flow @ np.array([-t[1], t[0]]))
    k = float(flow @ t) / max(abs(across), 1e-6) * (1.0 if across >= 0.0 else -1.0)
    room = 2.0 * min(b.span[0] - b.ends[0], b.ends[1] - b.span[1]) / b.width
    most = min(room, float(np.tan(np.radians(float(cfg["skew_most"])))))
    k = float(np.clip(k, -most, most))
    return 0.0 if abs(k) < np.tan(np.radians(float(cfg["skew_least"]))) else round(k, 3)


def _finish(b: Bridge, grid, floor, wet, sample, under, width: float, kind: str, cfg: dict, carve) -> None:
    """All of the record that follows from its heights; `floor`, `wet`, `sample` and `under` are on stations `grid`."""
    hit = np.flatnonzero(wet)
    channel = (float(grid[hit[0]]), float(grid[hit[-1]]))
    b.channel, b.water_width = channel, width
    b.water = float(sample.water[hit].max())
    b.parts = wet_parts(grid, wet, sample.water)
    b.dry = bool(sample.dry[hit].all())
    b.river = int(np.bincount(sample.river[hit].astype(np.int64)).argmax())
    b.rivers = tuple(int(r) for r in np.unique(np.r_[under[:, hit].ravel(), b.river]) if r >= 0)
    deck = (grid >= b.s[0]) & (grid <= b.s[-1])
    near, low, top = grid[deck], floor[deck], np.interp(grid[deck], b.s, b.z)        # a meter apart, not thinned
    b.span = channel if kind == "ford" else opening(near, top, low, b.depth, channel, cfg)
    b.kind = "beam" if kind == "arch" and b.span[1] - b.span[0] > float(cfg["arch_max"]) else kind
    if b.kind != "ford":
        on = (near >= b.span[0]) & (near <= b.span[1])
        level = np.array([b.level_at(float(t)) or -np.inf for t in near])
        b.piers = stations(b.kind, b.span, channel, cfg, float((top - b.depth - np.maximum(low, level))[on].max()))
    s = np.unique(np.concatenate([b.s, b.span, channel, b.piers]))
    if b.lean is not None:
        b.lean = np.interp(s, b.s, b.lean)
    held = (s >= near[0]) & (s <= near[-1])
    b.z, b.floor, b.s = np.interp(s, b.s, b.z), np.where(held, np.interp(s, near, low), np.interp(s, b.s, b.floor)), s
    if b.kind != "ford" and b.span[1] > b.span[0] and b.river < len(carve.rivers):
        b.skew = skew_of(carve, b, cfg)


def _city_kind(ctx, plan, c, b: Bridge, dry: bool) -> str:
    """Stone by the old town and for a street, concrete for the main streets and over a dry oued in a city."""
    ends = [Point(b.axis.coords[0]), Point(b.axis.coords[-1])]
    reach = float(ctx.style["bridges"]["old_reach"])
    b.old = plan.medina is not None and min(plan.medina.distance(e) for e in ends) <= reach
    if dry:
        return "beam"
    return "arch" if b.old else KINDS[c.kind]


def _heights_along(ground, axis, s) -> tuple:
    pts = shapely.line_interpolate_point(axis, s)
    x, y = shapely.get_x(pts), shapely.get_y(pts)
    return x, y, np.asarray(ground.height(x, y), dtype=np.float64)


def _raise_city(ctx, plan, ground, c, b: Bridge) -> None:
    """The heights of a planned bridge. On the two streets it joins its ribbon lies `tuck` m under theirs."""
    cfg = ctx.style["bridges"]
    tuck = float(cfg["tuck"])
    b.depth = float(cfg["depth"])
    e0, e1 = b.ends
    length = b.axis.length
    grid = np.unique(np.r_[np.arange(e0, e1, 1.0), e1])
    x, y, floor = _heights_along(ground, b.axis, grid)
    wet, sample, under = _channel(ctx.world.carve, x, y, b.width)
    if not wet.any():
        wet[int(np.argmin(sample.edge))] = True
    lifts = [float(ground.lift(*p, reach=0.1)) for p in (b.axis.coords[0], b.axis.coords[-1])]
    need = _carried(ground, x, y, b.width, floor, sample) + float(STREET_LIFT["bridge"])
    need[[0, -1]] = floor[[0, -1]] + np.array(lifts) - tuck
    b.tilt = _lean(ground, x, y, b.width)
    dry = bool(sample.dry[wet].all())
    width = 2.0 * float(np.median(sample.half[wet]))
    least = float(cfg["clearance"][0])
    water = np.where(wet, sample.water, np.inf)
    z, b.air = deck_profile(grid, need, water, (least, least if dry else air_wished(cfg, width)), b.depth,
                            float(cfg["grade"]), float(cfg["crown"]))
    s, z = thin(grid, z)
    head = np.arange(0.0, e0 - 1e-6, 3.0) if e0 > 0.0 else np.zeros(0)
    tail = length - np.arange(0.0, length - e1 - 1e-6, 3.0)[::-1] if e1 < length else np.zeros(0)
    b.s = np.concatenate([head, s, tail])
    b.floor = _heights_along(ground, b.axis, b.s)[2]
    on_head, on_tail = len(head), len(tail)
    b.z = np.concatenate([b.floor[:on_head] + lifts[0] - tuck, z, b.floor[len(b.s) - on_tail:] + lifts[1] - tuck])
    _finish(b, grid, floor, wet, sample, under, width, _city_kind(ctx, plan, c, b, dry), cfg, ctx.world.carve)
    b.walkway = walkway(b, ctx.style)
    if b.old:
        plan.streets[b.street].surface = str(ctx.style["streets"]["surface"]["bridge_old"])


def walkway(b: Bridge, style: dict) -> tuple:
    """The raised sidewalks of a city deck wide enough for them: (from, to) meters off the axis, along each parapet, and
    their height: what the mesher builds and `Ground.surface` reads."""
    cfg = style["bridges"]
    if b.width < float(cfg["sidewalk_from"]):
        return (0.0, 0.0, 0.0)
    thick = float(cfg["kerb"][1] if b.kind == "beam" else cfg["parapet"][1])
    out = 0.5 * b.width - thick
    return (out - float(cfg["sidewalk"][0]), out, float(style["streets"]["curb_height"]))


def raise_decks(ctx, plan, crossings: list, bridges: list) -> list:
    """Give each bridge its heights, on the finished plan's ground."""
    if bridges:
        ground = Ground(ctx.world, [plan])
        for c, b in zip(crossings, bridges):
            _raise_city(ctx, plan, ground, c, b)
    return bridges


# --- country roads -----------------------------------------------------------------------------------------

def wet_runs(carve, line) -> list:
    """(from, to) in meters along a road, where it crosses a river's channel or a dry oued's floor."""
    s = np.arange(0.0, line.length, 4.0)
    pts = shapely.line_interpolate_point(line, s)
    near = carve.sample(shapely.get_x(pts), shapely.get_y(pts))
    edges = np.flatnonzero(np.diff(np.r_[False, near.past < 0.0, False].astype(np.int8))).reshape(-1, 2)
    out = []
    for i, j in edges.tolist():
        a, b = float(s[i]) - 4.0, float(s[j - 1]) + 4.0
        t = np.arange(max(a, 0.0), min(b, line.length), 1.0)
        pts = shapely.line_interpolate_point(line, t)
        on = np.flatnonzero(carve.sample(shapely.get_x(pts), shapely.get_y(pts)).edge < 0.0)
        if len(on):
            out.append((float(t[on[0]]), float(t[on[-1]])))
    return out


def _slab(ground, x, y, width: float, floor, lift: float, cfg: dict) -> tuple:
    """(need, lean) of a ford at the points x, y: its top over the land under its two edges, and how it leans with that
    land, up to `ford_lean`: a road meets an oued's bank aslant, and a slab lies on it, not level over it."""
    left, right = (np.asarray(ground.height(*side), dtype=np.float64) for side in _offsets(x, y, width))
    limit = float(cfg["ford_lean"])
    lean = np.clip((left - right) / width, -limit, limit)
    return np.maximum.reduce([floor, left - 0.5 * width * lean, right + 0.5 * width * lean]) + lift, lean


def _ford(s, need, top, sample, wet, grade: float) -> tuple:
    """(i0, i1, z) of a ford: the ground raised at `grade` (`ford_grade`, steep: a slab on the gravel, not a causeway)
    from the top of its low banks, never dug."""
    raised = np.maximum(need, dilate(s, np.where(sample.past < 1.0, need, -np.inf), grade))
    i0, i1 = (int(k) for k in np.flatnonzero(wet)[[0, -1]])
    while i0 > 0 and raised[i0 - 1] > top[i0 - 1] + 0.01:
        i0 -= 1
    while i1 < len(s) - 1 and raised[i1 + 1] > top[i1 + 1] + 0.01:
        i1 += 1
    z = raised[i0:i1 + 1].copy()
    z[[0, -1]] = top[[i0, i1]]
    return i0, i1, z


def _ford_ends(ground, s, x, y, width: float, lift: float, z, lean, grade: float) -> tuple:
    """(z, lean) with both ends on the road: a ribbon has only edges, and the road's lies on the land under them, so an end
    takes the height and the lean of those two edges, whatever the land does at its middle, and the top comes to it at
    `grade`."""
    left, right = (np.asarray(ground.height(*side), dtype=np.float64) for side in _offsets(x, y, width))
    mid = 0.5 * (left + right) + lift
    z = np.minimum(z, np.minimum(mid[0] + grade * (s - s[0]), mid[-1] + grade * (s[-1] - s)))
    z = np.maximum(z, dilate(s, np.r_[mid[0], np.full(len(s) - 2, -np.inf), mid[-1]], grade))
    lean = lean.copy()
    lean[[0, -1]] = ((left - right) / width)[[0, -1]]
    return z, lean


def _road_bridge(world, road, k: int, line, ground, lift: float, a: float, b: float, area=None) -> Bridge | None:
    """The bridge or ford of road k over the channel from `a` to `b`: its ends move out along the road, but no farther
    than the limit of `area`, where the road stops being drawn: there the air, then the grade give way, as in a city.
    None for a ford too short to be one."""
    cfg = world.style["bridges"]
    reach = float(cfg["ramp_reach"])
    grade = float(cfg["grade"])
    lo, hi = max(a - reach, 0.0), min(b + reach, line.length)
    grid = np.unique(np.r_[np.arange(lo, hi, 1.0), hi])
    x, y, floor = _heights_along(ground, line, grid)
    wet, sample, under = _channel(world.carve, x, y, road.width)
    wet &= (grid >= a - road.width) & (grid <= b + road.width)
    top, need = floor + lift, _carried(ground, x, y, road.width, floor, sample) + lift
    dry = bool(sample.dry[wet].all())
    width = 2.0 * float(np.median(sample.half[wet]))
    depth, air, lean = 0.0, 0.0, None
    if dry:
        need, lean = _slab(ground, x, y, road.width, floor, lift, cfg)
        i0, i1, z = _ford(grid, need, top, sample, wet, float(cfg["ford_grade"]))
        if i1 == i0:                                    # one station of a dry bed: no ford, the road as it is
            return None
        z, lean = _ford_ends(ground, grid[i0:i1 + 1], x[i0:i1 + 1], y[i0:i1 + 1], road.width, lift, z, lean[i0:i1 + 1],
                             float(cfg["ford_grade"]))
    else:
        depth = float(cfg["depth"])
        least = float(cfg["clearance"][0])
        wish = max(air_wished(cfg, width), least)
        water = np.where(wet, sample.water, np.inf)
        stop = need if area is None else np.where(shapely.contains_xy(area, x, y), np.inf, need)
        i0, i1 = ramp_ends(grid, stop, water, wish, depth, grade)
        need[[i0, i1]] = top[[i0, i1]]
        z, air = deck_profile(grid[i0:i1 + 1], need[i0:i1 + 1], water[i0:i1 + 1], (least, wish), depth, grade,
                              float(cfg["crown"]))
    start = float(grid[i0])
    grid0 = grid - start
    axis = substring(line, start, float(grid[i1]))
    out = Bridge("", axis, road.width, -1, (0.0, axis.length), road=k, along=start, depth=depth, air=air)
    out.s, out.z = (grid0[i0:i1 + 1], z) if dry else thin(grid0[i0:i1 + 1], z)
    out.tilt = _lean(ground, x[i0:i1 + 1], y[i0:i1 + 1], road.width)
    out.lean = lean
    out.floor = np.interp(out.s, grid0, floor)
    _finish(out, grid0, floor, wet, sample, under, width, "ford" if dry else KINDS[road.kind], cfg, world.carve)
    return out


def clear_run(s, on, least: float) -> tuple:
    """(s0, s1): the longest run of stations `s` not `on`, or (0, 0) under `least` m."""
    edges = np.flatnonzero(np.diff(np.r_[False, ~on, False].astype(np.int8))).reshape(-1, 2)
    runs = [(float(s[j - 1] - s[i]), float(s[i]), float(s[j - 1])) for i, j in edges.tolist()]
    best = max(runs, default=(0.0, 0.0, 0.0))
    return best[1:] if best[0] >= least else (0.0, 0.0)


def eased(s, on, extra) -> np.ndarray:
    """`extra` at stations `on`; off them in proportion between its neighbors, and 0 at an end of `s` not `on`."""
    keep = on.copy()
    keep[[0, -1]] = True
    return np.interp(s, s[keep], np.where(on, extra, 0.0)[keep])


def runs_of(s, free, least: float) -> list:
    """[(s0, s1)]: the runs of stations `s` that are `free`, of `least` m at the least."""
    edges = np.flatnonzero(np.diff(np.r_[False, free, False].astype(np.int8))).reshape(-1, 2)
    return [(float(s[i]), float(s[j - 1])) for i, j in edges.tolist() if s[j - 1] - s[i] >= least]


def forked(b: Bridge, s, sides: list, own: tuple, cfg: dict) -> dict:
    """The fields of a road that forks off a wider one's deck: a wall and a parapet under each edge, each from where that
    edge leaves the deck, so the structure runs right up to the other road. Where that wedge lies over the open part the
    fork is a slab on the piers it needs: the wedge has no room for an arch."""
    least = float(cfg["own_least"])
    walls = tuple(runs_of(s, free, least) for free in sides)
    near = [next((run for run in side if run[0] <= own[1] and run[1] >= own[0]), None) for side in walls]
    if None in near:
        return {"own": own}
    start, stop = (near[0][0], near[1][0]), (near[0][1], near[1][1])
    a, c = min(start), max(stop)
    wedge = (a, max(start)) if a < own[0] else (min(stop), c)
    fields = {"own": (a, c), "walls": walls, "skew": 0.0}
    if b.kind == "arch" and wedge[0] < b.span[1] and wedge[1] > b.span[0]:
        open_part = (max(b.span[0], a), min(b.span[1], c))
        fields.update(kind="beam", piers=stations("beam", open_part, b.channel, cfg))
    return fields


def follow(b: Bridge, host: Bridge, cfg: dict) -> Bridge:
    """Bridge `b` of a road that shares its crossing with a wider road's `host`: a crossing has one structure. Its ribbon
    lies `tuck` m under the host's where they overlap, leaning with it, and comes back to its own heights by its far end.
    Of its structure it keeps what stands clear of the host's deck: nothing for a road that rides on it, the rest for one
    that forks off (`forked`), and all of it beside the host, its center line never on that deck. Where the host's ribbon
    covers its own it draws none; a road left without a structure draws none where its center line is on the host."""
    s = np.unique(np.r_[b.s, np.arange(b.ends[0], b.ends[1], 1.0)])
    x, y = shapely.get_coordinates(shapely.line_interpolate_point(b.axis, s)).T
    left, right = _offsets(x, y, b.width)
    deck = host.deck.buffer(0.1)             # a road of the host's width on the same line: its edges are the host's
    hit = [shapely.contains_xy(deck, *q) for q in (left, (x, y), right)]
    on = np.logical_or.reduce(hit)
    high, low = host.at(*left), host.at(*right)
    z, lean = np.interp(s, b.s, b.z), b.leaning(s)
    z = z + eased(s, on, 0.5 * (high + low) - float(cfg["tuck"]) - z)
    lean = lean + eased(s, on, (high - low) / b.width - lean)
    first = b.ends if b.own is None else b.own              # a second host: of what the first one left
    inside = (s >= first[0] - 1e-6) & (s <= first[1] + 1e-6)
    twin = not hit[1].any() and side_by_side(x, y, b.width, host, cfg)
    own = clear_run(s, on | ~inside, float(cfg["own_least"])) if hit[1].any() else (0.0, 0.0) if twin else first
    gone = hit[1] if own[1] <= own[0] else np.logical_and.reduce(hit)
    under = max(clear_run(s, ~gone, 0.0), b.under, key=lambda run: run[1] - run[0])
    fields = {"own": own, "twin": (host.road, host.along) if twin else b.twin}
    if b.kind != "ford" and hit[1].any() and own[1] > own[0]:
        fields.update(forked(b, s, [~q & inside for q in (hit[0], hit[2])], own, cfg))
        if "walls" in fields:
            fields["clear"] = (b.deck if b.clear is None else b.clear).difference(host.deck)
    return replace(b, s=s, z=z, lean=lean, floor=np.interp(s, b.s, b.floor), under=under, **fields)


def _along_host(host: Bridge, x, y) -> tuple:
    """(meters from the host's axis at the points x, y, True where they lie beside its deck, not past its ends)."""
    pts = shapely.points(x, y)
    return shapely.distance(host.axis, pts), (host.locate(x, y) > host.ends[0]) & (host.locate(x, y) < host.ends[1])


def side_by_side(x, y, width: float, host: Bridge, cfg: dict) -> bool:
    """True for a road that runs beside `host` all along it, its center line off that deck, the two ribbons touching: they
    want one structure. One that only touches at an end and leaves keeps its own (`stopped` stops the parapets there)."""
    off, beside = _along_host(host, x, y)
    if beside.mean() < float(cfg["twin_share"]):
        return False
    slip = float(cfg["twin_slip"])
    return float(np.ptp(off[beside])) <= slip and float(off[beside].max()) <= 0.5 * (width + host.width) + slip


def apart(s) -> np.ndarray:
    """The stations `s` in order, the last one kept, none on top of the next: two nearly equal ones turn no way at all
    (`_offsets`), and the line offset from them runs off to wherever the last one lands."""
    s = np.unique(s)
    return np.r_[s[:-1][np.diff(s) > 1e-6], s[-1]]


def widened(b: Bridge, twin: Bridge, cfg: dict) -> Bridge:
    """`b`, the structure of two roads side by side: its stations, piers and kind, its axis moved toward the twin's and as
    wide as both, so its two walls and parapets stand on the outer edges and none between them. Top and lean are the two
    ribbons' at those edges. The twin's ribbon comes and goes by what the gap between the roads changes, so a strip runs
    along the outer edge under it (`Bridge.verge`) as `seam` does between the ribbons."""
    s = apart(np.r_[b.ends, b.s[(b.s > b.ends[0]) & (b.s < b.ends[1])], np.arange(b.ends[0], b.ends[1], 2.0)])
    x, y = shapely.get_coordinates(shapely.line_interpolate_point(b.axis, s)).T
    points = shapely.get_coordinates(shapely.line_interpolate_point(twin.axis, np.linspace(*twin.ends, 40)))
    off, beside = _along_host(b, *points.T)
    off = off[beside]                                       # past the host's ends a distance says nothing of the deck
    width = 0.5 * b.width + float(off.max()) + 0.5 * twin.width
    left, right = _offsets(x, y, width - b.width)
    near = shapely.distance(twin.axis, shapely.points(left[0][0], left[1][0]))
    sign = 1.0 if near < float(shapely.distance(twin.axis, shapely.points(right[0][0], right[1][0]))) else -1.0
    mid = left if sign > 0.0 else right                     # the new axis, half the widening toward the twin
    axis = LineString(np.column_stack(mid))
    high_side, low_side = _offsets(*mid, width)
    high, low = (twin.at(*high_side), b.at(*low_side)) if sign > 0.0 else (b.at(*high_side), twin.at(*low_side))
    inner = 0.5 * b.width - 0.5 * (width - b.width)         # the host's inner edge, left of the new axis on the twin's side
    seam = (sign * inner, sign * (0.5 * width - twin.width))
    verge = (sign * (0.5 * width - float(np.ptp(off)) - float(cfg["verge_lap"])), sign * 0.5 * width)
    return replace(b, axis=axis, width=width, s=s, z=0.5 * (high + low), lean=(high - low) / width,
                   floor=np.interp(s, b.s, b.floor), walls=None, rails=None, seam=seam, verge=verge)


def ribbon_near(line, width: float, decks: list, area):
    """The ribbon of a road inside `area`: all of it but where a wider road's covers it, or None."""
    near = line.intersection(area)
    hidden = [substring(line, b.along + a, b.along + c) for b in decks for a, c in [b.under] if c > a]
    if hidden:
        near = near.difference(shapely.union_all(hidden).buffer(0.01))
    return None if near.is_empty else near.buffer(0.5 * width, cap_style="flat")


def stopped(b: Bridge, ribbons: list, cfg: dict) -> Bridge:
    """`b`, its parapets stopped where another road's ribbon crosses them: no rail runs across a road. A parapet's line is
    read inside the ribbon's edge, by half a parapet's thickness; what is left of it stands on its own two end posts."""
    if not ribbons:
        return b
    s = np.unique(np.r_[np.arange(b.ends[0], b.ends[1], 0.25), b.ends[1]])
    x, y = shapely.get_coordinates(shapely.line_interpolate_point(b.axis, s)).T
    area = shapely.union_all(ribbons)
    lines_ = _offsets(x, y, b.width - float(cfg["parapet"][1]))
    crossed = [shapely.contains_xy(area, *q) for q in lines_]
    if not any(q.any() for q in crossed):
        return b
    walled = b.walls or ([b.ends], [b.ends])
    keep = [np.logical_or.reduce([(s >= a - 1e-6) & (s <= c + 1e-6) for a, c in side]) if side else np.zeros(len(s), bool)
            for side in walled]
    return replace(b, rails=tuple(runs_of(s, ~q & on, float(cfg["rail_least"])) for q, on in zip(crossed, keep)))


def road_bridges(world, k: int, line, ground, lift: float, area=None) -> list:
    """The bridges and fords of road k, in order along it: a pure function of the road, the rivers, the ground and the
    cities' `area`, so two tiles agree. Crossings whose ramps would meet are one bridge."""
    if world.carve is None:
        return []
    road = world.roads[k]
    runs = wet_runs(world.carve, line)
    out = []
    i = 0
    while i < len(runs):
        j = i + 1
        b = _road_bridge(world, road, k, line, ground, lift, runs[i][0], runs[i][1], area)
        while b is not None and j < len(runs):
            next_one = _road_bridge(world, road, k, line, ground, lift, runs[j][0], runs[j][1], area)
            if next_one is None or next_one.along > b.along + b.axis.length:
                break
            b = _road_bridge(world, road, k, line, ground, lift, runs[i][0], runs[j][1], area)
            j += 1
        if b is not None:
            out.append(b)
        i = j
    return out
