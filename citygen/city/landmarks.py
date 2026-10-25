"""Landmarks of the boulevard (prompt 32): a cathedral and a municipal theatre in the colonial district.

`sites` runs after the lots and impasses are cut, before the ordinary buildings are made. For each landmark
in the settlement's `boulevard_landmarks` it slides the landmark's body (front steps on the boulevard, the
building behind them) along the boulevard-facing colonial lots: the lots of one block the body touches
(3-6 of them) are merged into one site, which must hold the body. The best site stands 50-300 m ahead of
the street camera inside its view (`streets.view_spot`), on another block than the first landmark, and is
as big as the style asks. `merge` replaces the site's lots by one merged parcel at the end of the parcel
list, so no ordinary building stands there; `buildings` gives each site its `Building` (kind `cathedral`
or `theatre`, drawn by `mesh/landmarks.py`), appended at the very end of the plan's buildings, and a
`Landmark` with a name on its own stream ("landmarks", kind). A landmark no boulevard-facing site holds
(a strip of blocks too shallow for its body) may face a cross street on a block fronting the boulevard,
its flank on it (`[landmarks.fallback]`). Nobody lives in them (`life.HOUSING`), the
dresser and the massing step leave them alone (not `DRESSED`, not `apartments`), and no parked car stops
in front of their steps (`Building.facade`). Numbers live in the style's `[landmarks]` table.

Every site and the mesh share one local frame (`Frame`): s along the facade (to the right seen from the
street), d into the lot from the street edge, z up; the steps run from d = 0 to the facade.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon
from shapely.geometry.polygon import orient
from shapely.ops import unary_union
from shapely.strtree import STRtree

from ..names import NameMaker
from .model import Building, Landmark, Parcel
from .streets import view_spot

KINDS = ("cathedral", "theatre")
STREET_VIEW = ("boulevard", "arterial", "street")   # the street camera's kinds (`build.camera_views`)


class Frame:
    """The local frame of a landmark from its `facade` record: origin on the street edge at the middle of the
    front, `yaw` the outward normal (toward the street)."""

    def __init__(self, facade: dict):
        self.o = np.array([facade["x"], facade["y"]], dtype=np.float64)
        self.n = -np.array([math.cos(facade["yaw"]), math.sin(facade["yaw"])])   # into the lot
        self.u = np.array([self.n[1], -self.n[0]])        # along the facade, to the right seen from the street

    def xy(self, s, d) -> np.ndarray:
        s, d = np.asarray(s, dtype=np.float64), np.asarray(d, dtype=np.float64)
        return self.o + s[..., None] * self.u + d[..., None] * self.n

    def poly(self, sd) -> Polygon:
        sd = np.asarray(sd, dtype=np.float64)
        return orient(Polygon(self.xy(sd[:, 0], sd[:, 1])), sign=1.0)

    def yaw(self, outward_sd) -> float:
        """World yaw of a local outward direction (s, d)."""
        v = self.u * outward_sd[0] + self.n * outward_sd[1]
        return math.atan2(v[1], v[0])


def rect(s0: float, s1: float, d0: float, d1: float) -> np.ndarray:
    return np.array([(s0, d0), (s1, d0), (s1, d1), (s0, d1)])


def arc(cs: float, cd: float, r: float, a0: float, a1: float, segments: int) -> np.ndarray:
    """Points (s, d) on a circle arc from angle a0 to a1 (radians, 0 = +s, pi/2 = +d), both ends included."""
    t = np.linspace(a0, a1, segments + 1)
    return np.stack([cs + r * np.cos(t), cd + r * np.sin(t)], axis=1)


# --- plan shapes shared with the mesh ---------------------------------------------------------------

def cathedral_plan(spec: dict, cfg: dict) -> dict:
    """Local plan of the cathedral: the towers, nave, aisles, crossing and apse (s, d ranges)."""
    w, depth, steps = spec["width"], spec["depth"], spec["steps"]
    tower = float(cfg["tower"][0]) * w
    nave = w - 2 * tower
    apse = nave / 2
    cross0 = steps + depth - apse - nave
    return {"w": w, "f": steps, "tower": tower, "nave": nave, "apse": apse, "cross0": cross0,
            "cross1": cross0 + nave, "end": steps + depth}


def theatre_plan(spec: dict, cfg: dict) -> dict:
    """Local plan of the theatre: rounded body, central pavilion standing out over the landing."""
    w, depth, steps = spec["width"], spec["depth"], spec["steps"]
    k = w / float(cfg["size"][0])                       # a smaller site keeps the proportions
    pw, pd = (float(v) for v in cfg["pavilion"][:2])
    r = float(cfg["corner_radius"]) * k
    pav = min(pw * k, w - 2 * r - 2.0)
    return {"w": w, "f": steps, "end": steps + depth, "round": r, "pav": pav, "pav_front": steps - pd,
            "pav_back": steps - pd + 1.5 + 2 * float(cfg["crown"][0])}


def theatre_body(p: dict, segments: int = 4) -> np.ndarray:
    """The theatre body's outline (s, d), counter-clockwise, its two street corners rounded."""
    w, f, end, r = p["w"], p["f"], p["end"], p["round"]
    right = arc(w / 2 - r, f + r, r, -math.pi / 2, 0.0, segments)
    left = arc(-w / 2 + r, f + r, r, math.pi, 3 * math.pi / 2, segments)
    return np.vstack([right, [(w / 2, end), (-w / 2, end)], left])


def outline(kind: str, spec: dict, cfg: dict) -> Polygon:
    """The landmark's footprint in world meters: everything it stands on, front steps included."""
    fr = Frame(spec)
    if kind == "cathedral":
        p = cathedral_plan(spec, cfg)
        w, nave = p["w"], p["nave"]
        apse = np.vstack([[(nave / 2, p["cross1"])], arc(0.0, p["cross1"], p["apse"], 0.0, math.pi, 8)[1:-1],
                          [(-nave / 2, p["cross1"])]])
        sd = np.vstack([[(-w / 2, 0.0), (w / 2, 0.0), (w / 2, p["cross0"]), (nave / 2, p["cross0"])], apse,
                        [(-nave / 2, p["cross0"]), (-w / 2, p["cross0"])]])
        return fr.poly(sd)
    p = theatre_plan(spec, cfg)
    body = fr.poly(theatre_body(p))
    front = fr.poly(rect(-p["w"] / 2, p["w"] / 2, 0.0, p["f"] + 0.01))
    return orient(unary_union([body, front]).simplify(0.0), sign=1.0)


# --- choosing the sites ----------------------------------------------------------------------------

@dataclass
class Site:
    kind: str
    lots: list          # indices of the merged lots in the parcel list given to `sites`
    lot: Polygon        # the merged lot
    block: int
    district: int
    facade: dict        # x, y (middle of the front on the street edge), yaw (toward the street), width, depth, steps
    side: int           # +1 / -1: which side of its boulevard (left / right of its line)
    parcel: int = -1    # index of the merged lot in the parcel list after `merge`


def sites(ctx, parcels, districts, streets, used) -> list:
    """The landmarks' sites, in the order of `boulevard_landmarks`, on lots that are not in `used`.

    A landmark no boulevard-facing site holds (blocks too shallow for its body) may face a cross street on a
    block fronting the boulevard instead (`_fallback`, `[landmarks.fallback]`)."""
    cfg = ctx.style.get("landmarks")
    kinds = [k for k in ctx.kc.get("boulevard_landmarks", []) if cfg and k in cfg and k in KINDS]
    boulevards = [st for st in streets if st.kind == "boulevard"]
    if not kinds or not boulevards:
        return []
    lots = [k for k, p in enumerate(parcels) if districts[p.district].kind == "colonial" and k not in used]
    by_block: dict = {}
    for k in lots:
        by_block.setdefault(parcels[k].block, []).append(k)
    seeds = _seeds(cfg, parcels, lots, boulevards)
    spot = view_spot(streets, Point(ctx.s.x, ctx.s.y), STREET_VIEW)
    out: list = []
    taken: set = set()
    for kind in kinds:
        best = None
        for seed in seeds:
            if seed[0] in taken:
                continue
            for site in _fits(cfg, kind, seed, parcels, by_block, taken):
                key = _score(cfg, site, spot, out)
                if best is None or key > best[0]:
                    best = (key, site)
        if best is None and "fallback" in cfg:
            best = _fallback(cfg, kind, seeds, parcels, lots, by_block, taken, streets, spot, out)
        if best is not None:
            out.append(best[1])
            taken |= set(best[1].lots)
    return out


def _seeds(cfg: dict, parcels, lots: list, boulevards: list) -> list:
    """[(lot, street edge point in front of it, inward normal, side)] for every lot facing a boulevard."""
    reach, need = float(cfg["front_reach"]), float(cfg["min_front"])
    out = []
    for k in lots:
        poly = parcels[k].polygon
        for st in boulevards:
            edge = poly.exterior.intersection(st.line.buffer(st.width / 2 + reach, cap_style="flat"))
            if edge.length < need:
                continue
            t = st.line.project(edge.centroid)
            a, b = st.line.interpolate(max(t - 1.0, 0.0)), st.line.interpolate(min(t + 1.0, st.line.length))
            tan = np.array([b.x - a.x, b.y - a.y])
            tan /= max(float(np.hypot(*tan)), 1e-9)
            left = np.array([-tan[1], tan[0]])
            p = st.line.interpolate(t)
            c = poly.centroid
            side = 1 if (c.x - p.x) * left[0] + (c.y - p.y) * left[1] > 0 else -1
            n = left * side
            out.append((k, np.array([p.x, p.y]) + n * st.width / 2, n, side))
    return out


def _fallback(cfg: dict, kind: str, seeds: list, parcels, lots: list, by_block: dict, taken: set, streets,
              spot, out: list):
    """(score, site) of the best site of `kind` on a block fronting the boulevard but facing one of its cross
    streets (`[landmarks.fallback] streets`), its flank along the boulevard, or None. For blocks too shallow
    for any body: a narrow strip between the boulevard and the next street, as a grid parallel to it cuts."""
    fb = cfg["fallback"]
    fronting = {parcels[seed[0]].block for seed in seeds}
    cross = [st for st in streets if st.kind in fb["streets"]]
    near = _seeds(cfg, parcels, [k for k in lots if parcels[k].block in fronting], cross)
    best = None
    for seed in near:
        if seed[0] in taken:
            continue
        for site in _fits(cfg, kind, seed, parcels, by_block, taken, fb["lots"]):
            key = _score(cfg, site, spot, out)
            if best is None or key > best[0]:
                best = (key, site)
    return best


def _fits(cfg: dict, kind: str, seed: tuple, parcels, by_block: dict, taken: set, lots=None):
    """The sites of `kind` grown from one seed lot: the footprint at each shift of the largest scale the style
    lists that fits somewhere, the lots it touches merged when they are 3-6 free lots of the seed's block
    (or `lots`) that hold it."""
    k0, edge, n, side = seed
    spec = cfg[kind]
    width0, depth0 = (float(v) for v in spec["size"])
    steps, inset = float(spec["steps"]), float(cfg["inset"])     # the front stays `inset` off the street edge
    lo, hi = (int(v) for v in (cfg["lots"] if lots is None else lots))
    u = np.array([n[1], -n[0]])
    block = parcels[k0].block
    cands = by_block[block]
    polys = [parcels[k].polygon for k in cands]
    reach, step = (float(v) for v in cfg["shift"])
    shifts = [0.0] + [sign * x for x in np.arange(step, reach + 1e-9, step) for sign in (-1.0, 1.0)]
    for scale in cfg["scales"]:                         # the largest scale that fits at some shift
        w, depth = width0 * float(scale), depth0 * float(scale)
        found = False
        for shift in shifts:
            o = edge + u * float(shift) + n * inset
            yaw = math.atan2(-n[1], -n[0])
            facade = {"x": float(o[0]), "y": float(o[1]), "yaw": yaw, "width": round(w, 2),
                      "depth": round(depth, 2), "steps": steps}
            body = outline(kind, facade, spec)
            area = shapely.area(shapely.intersection(np.array(polys, dtype=object), body))
            hit = [k for k, a in zip(cands, area) if a > 1.0]
            if k0 not in hit or not lo <= len(hit) <= hi or any(k in taken for k in hit):
                continue
            lot = _merged([parcels[k].polygon for k in hit])
            if lot is None:
                continue
            if body.difference(lot).area > float(cfg["slack"]):
                continue
            found = True
            yield Site(kind, hit, lot, block, parcels[k0].district, facade, side)
        if found:
            return


def _merged(polys: list) -> Polygon | None:
    """The union of adjacent lots as one polygon (cuts that do not quite meet leave hair gaps: closed with a
    2 cm grow and shrink), or None when they do not form one piece."""
    lot = unary_union(polys)
    if lot.geom_type != "Polygon":
        lot = lot.buffer(0.02, join_style="mitre").buffer(-0.02, join_style="mitre")
    return orient(lot, sign=1.0) if lot.geom_type == "Polygon" and lot.is_valid else None


def _score(cfg: dict, site: Site, spot, chosen: list) -> tuple:
    """(seen from the street camera, on a block of its own, its size less a quarter of the lot it wastes)."""
    lo, hi, cone = (float(v) for v in cfg["view"])
    seen = False
    if spot is not None:
        a, b = spot
        look = np.array([b.x - a.x, b.y - a.y])
        look /= max(float(np.hypot(*look)), 1e-9)
        v = np.array([site.facade["x"] - a.x, site.facade["y"] - a.y])
        ahead, across = float(v @ look), float(look[0] * v[1] - look[1] * v[0])
        seen = lo <= ahead <= hi and abs(math.degrees(math.atan2(across, ahead))) <= cone
    alone = all(c.block != site.block for c in chosen)
    body = site.facade["width"] * (site.facade["depth"] + site.facade["steps"])
    return seen, alone, round(body - 0.25 * (site.lot.area - body), 3)


def merge(parcels: list, used: set, chosen: list) -> tuple:
    """(parcels, used): the chosen sites' lots replaced by one merged parcel each, appended at the end in
    the order of the sites; `used` (lots another building took) renumbered."""
    gone = {k for s in chosen for k in s.lots}
    keep = [k for k in range(len(parcels)) if k not in gone]
    index = {k: i for i, k in enumerate(keep)}
    out = [parcels[k] for k in keep]
    for s in chosen:
        s.parcel = len(out)
        out.append(Parcel(orient(s.lot, sign=1.0), s.district, True, s.block))
    return out, {index[k] for k in used if k in index}


# --- buildings, names, street trees ---------------------------------------------------------------

def buildings(ctx, chosen: list) -> tuple:
    """(buildings, landmarks) of the chosen sites, in their order."""
    cfg = ctx.style.get("landmarks", {})
    out, marks = [], []
    for s in chosen:
        spec = cfg[s.kind]
        rng = ctx.rng("landmarks", s.kind)
        facade = dict(s.facade)
        if s.kind == "cathedral":
            facade["cap"] = "dome" if rng.random() < float(spec["dome_chance"]) else "pyramid"
        fp = outline(s.kind, facade, spec)
        out.append(Building(fp, s.kind, s.district, float(spec["height"]), str(spec["wall"]), str(spec["roof"]),
                            int(spec.get("floors", 1)), facade=facade))
        c = fp.centroid                                   # the map writes its name over the building
        marks.append(Landmark(s.kind, _name(ctx, s.kind, spec), float(c.x), float(c.y)))
    return out, marks


def _name(ctx, kind: str, spec: dict) -> str:
    """'Cathedral of St Aurele de <invented place>' or 'Theatre Municipal de <city>', on its own stream."""
    namer = NameMaker(ctx.style, ctx.rng("landmarks", kind, "name"))
    saint = namer._pick(spec.get("saints", ["Aurele"]))
    return namer.district(kind, s=ctx.s.name, g=saint)


def clear_fronts(trees: list, chosen: list, reach: float) -> list:
    """The street trees with the ones standing in front of a landmark's steps left out (`reach` m out)."""
    if not chosen or not trees:
        return trees
    zones = [Frame(s.facade).poly(rect(-s.facade["width"] / 2 - 1.0, s.facade["width"] / 2 + 1.0, -reach, 0.5))
             for s in chosen]
    zone = unary_union(zones)
    xy = np.array([(t.x, t.y) for t in trees])
    inside = shapely.contains_xy(zone, xy[:, 0], xy[:, 1])
    return [t for t, hit in zip(trees, inside) if not hit]


# --- the camera views that frame them (build.camera_views) -------------------------------------------


class _Clear:
    """How many of the sight lines from a camera spot to the facade's ends and middle (eye to look height) a
    building but the landmark itself, a trunk or a tree crown blocks; None when the eye stands within
    `wall_clear` m of a wall or within `tree_margin` m of a trunk or a crown (crowns as `tree_crowns` gives
    them: radius and base as shares of the tree's height)."""

    def __init__(self, plan, f: dict, ends: np.ndarray, middle: np.ndarray, cfg: dict):
        self.fps = [b.footprint for b in plan.buildings if b.facade is not f]
        self.tree = STRtree(self.fps)
        self.targets = [ends[0], middle, ends[1]]
        self.wall, self.margin = float(cfg["wall_clear"]), float(cfg["tree_margin"])
        self.eye, self.look = float(cfg["height"]), float(cfg["look"])
        crowns, trunk = cfg["tree_crowns"], float(cfg["trunk"])
        known = [t for t in plan.trees if t.kind in crowns]
        self.xy = np.array([(t.x, t.y) for t in known]).reshape(-1, 2)
        self.top = np.array([t.height for t in known])
        self.r = np.array([float(crowns[t.kind][0]) * t.height for t in known])
        self.base = np.array([float(crowns[t.kind][1]) * t.height for t in known])
        self.trunk = trunk
        self.reach = float(self.r.max()) + self.margin if len(known) else 0.0
        self.trees = STRtree(shapely.points(self.xy)) if len(known) else None

    def _tree_hit(self, a: np.ndarray, b: np.ndarray, za: float, zb: float, pad: float) -> bool:
        """Does the segment a (height za) to b (height zb) pass through a trunk or a crown, grown by `pad`?"""
        if self.trees is None:
            return False
        seg = LineString([tuple(a), tuple(b)]) if np.any(a != b) else Point(*a)
        idx = self.trees.query(seg, predicate="dwithin", distance=self.reach)
        if not len(idx):
            return False
        v = b - a
        ll = float(v @ v)
        for i in idx:
            t = 0.0 if ll == 0.0 else min(max(float((self.xy[i] - a) @ v) / ll, 0.0), 1.0)
            d = float(np.hypot(*(a + v * t - self.xy[i])))
            z = za + (zb - za) * t
            if d < self.trunk + pad and z < self.top[i] + pad:
                return True
            if d < self.r[i] + pad and self.base[i] - pad < z < self.top[i] + pad:
                return True
        return False

    def __call__(self, cam: np.ndarray):
        p = Point(float(cam[0]), float(cam[1]))
        if len(self.tree.query(p, predicate="dwithin", distance=self.wall)):
            return None
        if self._tree_hit(cam, cam, self.eye, self.eye, self.margin):
            return None
        blocked = 0
        for q in self.targets:
            q = np.asarray(q, dtype=np.float64)
            line = LineString([p.coords[0], (float(q[0]), float(q[1]))])
            blocked += bool(len(self.tree.query(line, predicate="intersects"))
                            or self._tree_hit(cam, q, self.eye, self.look, 0.0))
        return blocked


def landmark_views(plan, cfg: dict) -> dict:
    """{kind: ((x, y, height), (x, y, height))}: for each landmark a camera on its boulevard (heights above the
    ground there) that sees its whole facade from the front or three-quarters, as near as possible to
    `distance` m away, looking at the facade's middle."""
    out = {}
    for b in plan.buildings:
        if b.kind in KINDS and b.facade is not None and b.kind not in out:
            spot = _frame_facade(plan, b.facade, cfg)
            if spot is not None:
                out[b.kind] = spot
    return out


def _frame_facade(plan, f: dict, cfg: dict):
    """(eye, look) on the boulevard, or for a facade facing another street (a fallback site) on that street or
    another within `distance` + `search` m, clear of walls and trees, seeing the whole front past buildings
    and trees (else the fewest lines blocked)."""
    fr = Frame(f)
    ends = np.array([fr.xy(-f["width"] / 2, f["steps"]), fr.xy(f["width"] / 2, f["steps"])])
    middle = fr.xy(0.0, f["steps"])
    outward = -fr.n
    o = Point(f["x"], f["y"])
    faced = min(plan.streets, key=lambda s: abs(s.line.distance(o) - s.width / 2))
    if faced.kind == "boulevard":
        streets, clear = [s for s in plan.streets if s.kind == "boulevard"], None
    else:
        reach = float(cfg["distance"]) + float(cfg["search"])   # the faced street and the others around
        mid = Point(float(middle[0]), float(middle[1]))
        streets = [faced] + [s for s in plan.streets if s is not faced and s.line.distance(mid) < reach]
        clear = _Clear(plan, f, ends, middle, cfg)
    best = None
    for st in streets:
        for off in (st.width / 4, -st.width / 4, 0.0):
            line = st.line.offset_curve(off) if off else st.line
            for t in np.arange(0.0, line.length + 1e-9, float(cfg["step"])):
                p = line.interpolate(float(t))
                cam = np.array([p.x, p.y])
                to = cam - middle
                dist = float(np.hypot(*to))
                if dist < float(cfg["min_distance"]) or float(outward @ to) < float(cfg["facing"]) * dist:
                    continue
                v = ends - cam
                ang = np.arctan2(v[:, 1], v[:, 0])
                if math.degrees(abs((ang[1] - ang[0] + math.pi) % (2 * math.pi) - math.pi)) > float(cfg["spread"]):
                    continue
                blocked = 0 if clear is None else clear(cam)
                if blocked is None:
                    continue
                key = abs(dist - float(cfg["distance"])) if clear is None else (blocked, abs(dist - float(cfg["distance"])))
                if best is None or key < best[0]:
                    best = (key, cam)
    if best is None:
        return None
    cam = best[1]
    eye = (float(cam[0]), float(cam[1]), float(cfg["height"]))
    return eye, (float(middle[0]), float(middle[1]), float(cfg["look"]))
