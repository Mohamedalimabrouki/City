"""More greenery (prompt 24): street trees along arterials, courtyard trees, fruit trees in villa gardens.

Runs last in the planner, after massing and road paint, and only appends to `CityPlan.trees`: every
older tree keeps its index, so the dresser's `rng("tree", k)` gives it the same kit variant and turn.
Each kind of choice has its own stream (`street-trees/arterial/<street>`, `courtyard-trees/<building>`,
`garden-trees/<building>`). Numbers come from `[greenery]` in the style.

- Arterial trees stand in a row of tree pits `pit` m behind the curb face of the sidewalks of
  colonial and modern blocks, every `spacing` m along the street, one species per street. Gaps: near
  junctions (and so their zebra crossings), road paint, street lamps on the same side, the arcade
  bands of colonial facades (the trees the dresser would have to move, `dressing.arcade_zones`) and
  the paved paths from the stair doors of apartment blocks.
- Courtyard houses whose courtyard has no tree yet may get one (mostly a bitter orange): at the
  courtyard's most open point, as tall as its crown can be while clearing the walls.
- Villa gardens get a few fruit trees behind or beside the house, away from the path to the street.
"""
from __future__ import annotations

import numpy as np
import shapely
from shapely.ops import polylabel
from shapely.strtree import STRtree

from ..rng import weighted
from .geo import frame
from .model import Tree
from .openings import path_to_street, villa_lots, wall_arrays


def greenery(ctx, plan) -> list:
    """The new trees of one city, in a fixed order (arterials, courtyards, gardens)."""
    cfg = ctx.style.get("greenery", {})
    surfaces = [st.line.buffer(st.width / 2, cap_style="flat") for st in plan.streets]
    surface_tree = STRtree(surfaces) if surfaces else None
    out: list = []
    if "arterial" in cfg and surface_tree is not None:
        out += arterial_trees(ctx, plan, cfg["arterial"], surfaces, surface_tree)
    if "courtyard" in cfg:
        out += courtyard_trees(ctx, plan, cfg["courtyard"])
    if "garden" in cfg and surface_tree is not None:
        out += villa_fruit_trees(ctx, plan, cfg["garden"], surface_tree)
    return out


def crown_reach(style: dict, kind: str, height: float) -> float:
    """How far a tree's crown reaches from its trunk (`[dressing.trees.<kind>]`, else 0.45 x height)."""
    spec = style.get("dressing", {}).get("trees", {}).get(kind)
    if not spec:
        return 0.45 * height
    return (float(spec["crown_radius"]) + float(spec["clump_radius"][1])) * height


# --- arterials --------------------------------------------------------------------------------
def arterial_trees(ctx, plan, cfg: dict, surfaces: list, surface_tree) -> list:
    from ..mesh.props import ARCADE                    # imported here: mesh.props imports city.model
    from .dressing import arcade_zones, band_push, tree_reach
    kinds_of = [d.kind for d in plan.districts]
    walks: dict = {}
    for w in plan.walks:
        if w.kind == "sidewalk" and 0 <= w.district < len(kinds_of) and kinds_of[w.district] in cfg["districts"]:
            walks.setdefault(w.street, []).append(w)
    ks = [k for k, st in enumerate(plan.streets) if st.kind in cfg["kinds"] and k in walks]
    if not ks:
        return []
    cands = [(k, *_stations(plan.streets[k], walks[k], cfg)) for k in ks]
    pts = np.concatenate([c[1] for c in cands]) if cands else np.zeros((0, 2))
    if not len(pts):
        return []
    street = np.concatenate([np.full(len(c[1]), c[0]) for c in cands])
    keep = _clear_of_streets(pts, street, surface_tree, float(cfg["junction_clear"]))
    keep &= _clear_of(pts, [m.polygon for m in plan.paint], float(cfg["paint_clear"]))
    keep &= _clear_of(pts, [b.footprint for b in plan.buildings], float(cfg["wall_clear"]))
    keep &= _clear_of_lamps(ctx, plan, cands, float(cfg["lamp_clear"]))
    arcade = ctx.style.get("dressing", {}).get("arcade")
    if arcade:
        acfg = {**ARCADE, **arcade}
        zones = arcade_zones(plan, acfg, lambda q: _streets_at(surface_tree, q))
        keep &= band_push(zones, pts, tree_reach(acfg))[0] < 0
    keep &= _clear_of_paths(plan, pts, surfaces, ctx.style, float(cfg["door_clear"]))
    out, at = [], 0
    for k, p, _d, _side in cands:
        rng = ctx.rng("street-trees", "arterial", k)
        kind = str(weighted(rng, cfg["species"]))
        lo, hi = cfg["height"][kind]
        for x, y in p[keep[at:at + len(p)]]:
            out.append(Tree(float(x), float(y), kind, float(rng.uniform(lo, hi))))
        at += len(p)
    return out


def _stations(st, walks: list, cfg: dict) -> tuple:
    """Tree pit candidates of one street: every `spacing` m along it, on each side, `pit` m behind the
    curb face of the sidewalk there, inside that sidewalk. Returns (points, stations, sides)."""
    line, spacing, pit = st.line, float(cfg["spacing"]), float(cfg["pit"])
    d = np.arange(spacing / 2, line.length, spacing)
    if not len(d):
        return np.zeros((0, 2)), d, d
    p = shapely.get_coordinates(shapely.line_interpolate_point(line, d))
    a = shapely.get_coordinates(shapely.line_interpolate_point(line, np.maximum(d - 0.5, 0.0)))
    b = shapely.get_coordinates(shapely.line_interpolate_point(line, np.minimum(d + 0.5, line.length)))
    t = (b - a) / np.maximum(np.hypot(*(b - a).T), 1e-9)[:, None]
    left = np.stack([-t[:, 1], t[:, 0]], axis=1)
    pts, stations, sides = [], [], []
    for w in walks:
        if w.side == 0 or w.width < pit + float(cfg["trunk_clear"]):
            continue
        q = p + left * (w.side * (st.width / 2 - w.width + pit))
        inner = w.polygon.buffer(-float(cfg["trunk_clear"]))
        hit = shapely.contains_xy(inner, q[:, 0], q[:, 1]) if not inner.is_empty else np.zeros(len(q), dtype=bool)
        pts.append(q[hit])
        stations.append(d[hit])
        sides.append(np.full(int(hit.sum()), w.side))
    if not pts:
        return np.zeros((0, 2)), np.zeros(0), np.zeros(0)
    pts, stations, sides = np.concatenate(pts), np.concatenate(stations), np.concatenate(sides)
    order = np.lexsort((-sides, stations))             # along the street, the left side first
    return pts[order], stations[order], sides[order]


def _streets_at(surface_tree, pts: np.ndarray) -> np.ndarray:
    out = np.full(len(pts), -1)
    if len(pts):
        inp, hit = surface_tree.query(shapely.points(pts), predicate="within")
        out[inp] = hit
    return out


def _clear_of_streets(pts: np.ndarray, street: np.ndarray, surface_tree, clear: float) -> np.ndarray:
    """True where no street but the tree's own lies within `clear` m (junctions and their crossings)."""
    inp, hit = surface_tree.query(shapely.points(pts), predicate="dwithin", distance=clear)
    keep = np.ones(len(pts), dtype=bool)
    keep[inp[hit != street[inp]]] = False
    return keep


def _clear_of(pts: np.ndarray, geoms: list, clear: float) -> np.ndarray:
    keep = np.ones(len(pts), dtype=bool)
    if geoms and len(pts):
        inp, _ = STRtree(geoms).query(shapely.points(pts), predicate="dwithin", distance=clear)
        keep[inp] = False
    return keep


def _clear_of_lamps(ctx, plan, cands: list, clear: float) -> np.ndarray:
    """True where no street lamp of the same side stands within `clear` m along the street (the lamps of
    `Dresser._lamps`: one every `[dressing] street_lamps` m, at the middle of each stretch, sides alternating)."""
    lamps = ctx.style.get("dressing", {}).get("street_lamps", {})
    keep = []
    for k, _p, d, side in cands:
        spacing = lamps.get(plan.streets[k].kind)
        if not spacing or not len(d):
            keep.append(np.ones(len(d), dtype=bool))
            continue
        i = np.floor(d / float(spacing))                 # the lamp stretch each station falls in, and its neighbours
        near = np.ones(len(d), dtype=bool)
        for di in (-1.0, 0.0, 1.0):
            j = i + di
            lamp = (j + 0.5) * float(spacing)
            lamp_side = np.where(j % 2 == 1, 1.0, -1.0)
            real = (j >= 0) & (j < int(plan.streets[k].line.length // float(spacing)))
            near &= ~(real & (lamp_side == side) & (np.abs(d - lamp) < clear))
        keep.append(near)
    return np.concatenate(keep) if keep else np.zeros(0, dtype=bool)


def _clear_of_paths(plan, pts: np.ndarray, surfaces: list, style: dict, clear: float) -> np.ndarray:
    """True where no paved stair-door path of a modern block passes within `clear` m. The dresser puts
    the stair doors on one long side (the one facing the nearest street); both long sides are tested,
    with the same door columns and `path_to_street`, each path carried on `cross` m over the sidewalk."""
    from .dressing import DRESSED, stair_columns
    keep = np.ones(len(pts), dtype=bool)
    dress = style.get("dressing", {})
    pcfg, scfg = dress.get("paths", {}), dress.get("slab", {})
    if "modern" not in pcfg.get("districts", ()) or not len(pts):
        return keep
    kinds_of = [d.kind for d in plan.districts]
    slabs = [k for k, b in enumerate(plan.buildings)
             if b.kind == "apartments" and kinds_of[b.district] == "modern" and b.kind in DRESSED]
    if not slabs:
        return keep
    reach = float(pcfg.get("reach", 40.0))
    near = STRtree([plan.buildings[k].footprint for k in slabs]).query(
        shapely.points(pts), predicate="dwithin", distance=reach + 5.0)[1]
    if not len(near):
        return keep
    fp_tree = STRtree([b.footprint for b in plan.buildings])
    target_tree = STRtree(surfaces + [w.polygon for w in plan.walks])
    width, step = float(pcfg.get("width", 1.4)), float(pcfg.get("step", 4.0))
    cross = 4.0
    paths = []
    for m in sorted(set(near.tolist())):
        b = plan.buildings[slabs[m]]
        a, q, n, length = wall_arrays(b.footprint)
        long = length >= float(scfg.get("long", 0.6)) * frame(b.footprint)[2]
        for i in (np.nonzero(long)[0] if long.any() else [int(np.argmax(length))]):
            u = (q[i] - a[i]) / max(length[i], 1e-9)
            cols, picks = stair_columns(float(length[i]), scfg)
            for col in picks:
                line = path_to_street(a[i] + u * cols[col], n[i], target_tree, fp_tree, width, reach, step, step)
                if line is not None and len(line) >= 2:
                    t = line[-1] - line[-2]
                    t = t / max(float(np.hypot(*t)), 1e-9)
                    paths.append(shapely.linestrings(np.vstack([line, line[-1] + t * cross])))
    if paths:
        inp, _ = STRtree(paths).query(shapely.points(pts), predicate="dwithin", distance=clear)
        keep[inp] = False
    return keep


# --- courtyards -------------------------------------------------------------------------------
def courtyard_trees(ctx, plan, cfg: dict) -> list:
    """One more tree in some courtyards that have none (`chance` by district kind), mostly bitter
    oranges: at the courtyard's most open point, as tall as its crown may be and still clear the walls."""
    kinds_of = [d.kind for d in plan.districts]
    chance = cfg["chance"]
    courts = []                                          # (building, hole)
    for k, b in enumerate(plan.buildings):
        if b.kind == "house" and kinds_of[b.district] in chance and b.footprint.geom_type == "Polygon":
            courts += [(k, shapely.Polygon(h)) for h in b.footprint.interiors]
    if not courts:
        return []
    old = np.array([(t.x, t.y) for t in plan.trees]) if plan.trees else np.zeros((0, 2))
    taken = set()
    if len(old):
        taken = set(STRtree(shapely.points(old)).query([c for _, c in courts], predicate="contains")[0].tolist())
    out = []
    lo_h, clear = float(cfg["min_height"]), float(cfg["wall_clear"])
    for m, (k, court) in enumerate(courts):
        district = kinds_of[plan.buildings[k].district]
        rng = ctx.rng("courtyard-trees", k)
        roll, kind = rng.random(), str(weighted(rng, cfg["kinds"][district]))
        lo, hi = cfg["height"][kind]
        h = float(rng.uniform(lo, hi))
        if m in taken or roll >= float(chance[district]) or court.area < float(cfg["min_area"]):
            continue
        c = polylabel(court, tolerance=0.05)
        room = float(court.exterior.distance(c)) - clear
        h = min(h, room * h / max(crown_reach(ctx.style, kind, h), 1e-9))
        if h >= lo_h:
            out.append(Tree(float(c.x), float(c.y), kind, h))
    return out


# --- villa gardens ----------------------------------------------------------------------------
def villa_fruit_trees(ctx, plan, cfg: dict, surface_tree) -> list:
    """A few fruit trees in each villa garden, behind or beside the house (farther from the nearest
    street than the house by `behind` m, so clear of the path to the gate), clear of the house, the lot
    edges and the trees already there."""
    villas = [k for k, b in enumerate(plan.buildings) if b.kind == "villa"]
    if not villas or not plan.parcels:
        return []
    lots = villa_lots(plan, villas)
    trees = [shapely.Point(t.x, t.y) for t in plan.trees]
    tree_index = STRtree(trees) if trees else None
    out = []
    for k in villas:
        rng = ctx.rng("garden-trees", k)
        count = int(rng.integers(int(cfg["count"][0]), int(cfg["count"][1]) + 1))
        if k not in lots or not count:
            continue
        lot = plan.parcels[lots[k]].polygon
        fp = plan.buildings[k].footprint
        j = int(min(surface_tree.query_nearest(fp)))
        street = surface_tree.geometries[j]
        front = float(fp.distance(street)) + float(cfg["behind"])
        room = lot.buffer(-float(cfg["edge_clear"]), join_style="mitre")
        if tree_index is not None:
            for i in tree_index.query(lot):
                room = room.difference(trees[int(i)].buffer(float(cfg["tree_clear"]), quad_segs=4))
        for _ in range(count):
            kind = str(weighted(rng, cfg["kinds"]))
            lo, hi = cfg["height"][kind]
            h = float(rng.uniform(lo, hi))
            free = room.difference(fp.buffer(crown_reach(ctx.style, kind, h) + 0.3, quad_segs=4))
            p = _point_in(free, rng, street, front)
            if p is not None:
                out.append(Tree(float(p.x), float(p.y), kind, h))
                room = room.difference(p.buffer(float(cfg["tree_clear"]), quad_segs=4))
    return out


def _point_in(region, rng, street, front: float, tries: int = 12):
    """A random point of `region` at least `front` m from `street` (12 draws always, so the stream
    never depends on the geometry), or None."""
    xy = rng.random((tries, 2))
    if region.is_empty:
        return None
    x0, y0, x1, y1 = region.bounds
    pts = shapely.points(x0 + xy[:, 0] * (x1 - x0), y0 + xy[:, 1] * (y1 - y0))
    ok = shapely.contains(region, pts) & (shapely.distance(street, pts) >= front)
    return pts[int(np.argmax(ok))] if ok.any() else None
