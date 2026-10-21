"""The old town: great mosque, gates, souk streets, alleys with dead ends, and ramparts."""
from __future__ import annotations

import math

import numpy as np
import shapely
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra, minimum_spanning_tree
from scipy.spatial import cKDTree
from shapely.geometry import LineString, MultiPoint, Point
from shapely.ops import unary_union

from ..mesh.builder import rectangle
from .geo import jittered_grid, largest, lines, polygons, ray_exit, tangent_angle
from .model import Building, Landmark, Street


def mosque_complex(cx, cy, qibla, width, hall_depth, court_depth, minaret, district, name):
    """Prayer hall facing the qibla, arcaded courtyard behind it, square minaret at the back.

    Returns (buildings, cleared site polygon, entrance point, landmark).
    """
    u = np.array([math.cos(qibla), math.sin(qibla)])
    total = hall_depth + court_depth
    back = np.array([cx, cy]) - u * total / 2
    hall_c = back + u * (court_depth + hall_depth / 2)
    court_c = back + u * (court_depth / 2)
    hall = rectangle(*hall_c, hall_depth, width, qibla)
    arcade = max(4.0, 0.12 * width)
    court = rectangle(*court_c, court_depth, width, qibla).difference(
        rectangle(*court_c, court_depth - 2 * arcade, width - 2 * arcade, qibla))
    side, height = minaret
    mc = back + u * (side / 2)
    hall_h = 7.0 + 0.07 * width
    r = 0.16 * width
    domes = [(*(hall_c + u * (hall_depth / 2 - r - 1.0)), r, "dome_white"),
             (*(hall_c - u * (hall_depth / 2 - 0.75 * r - 1.0)), 0.75 * r, "dome_white")]
    buildings = [
        Building(hall, "mosque_hall", district, hall_h, "lime_white", "roof_white", 1, domes=domes),
        Building(court, "mosque_court", district, 6.0, "lime_white", "roof_white", 1),
        Building(rectangle(*mc, side, side, qibla), "minaret", district, height, "minaret_stone",
                 "minaret_stone", 1, top={"side": side * 0.62, "height": height * 0.16,
                                          "material": "minaret_stone", "cap": "dome_green"}),
    ]
    site = rectangle(cx, cy, total + 8.0, width + 8.0, qibla)
    entrance = back - u * 7.0
    return buildings, site, Point(*entrance), Landmark("mosque", name, cx, cy)


def gates(ctx, medina, axis: float, crossings: list, count: int) -> list:
    """Gate points on the old town's edge: toward the main axis, where roads arrive, then spread out."""
    s = ctx.s
    rng = ctx.rng("gates")
    angles = [axis] + [math.atan2(p.y - s.y, p.x - s.x) for p in crossings]
    base = rng.uniform(0, 2 * math.pi)
    angles += [base + 2 * math.pi * k / count + rng.uniform(-0.3, 0.3) for k in range(count)]
    reach = 3 * ctx.kc["medina_radius"] * s.radius + 3 * s.radius
    out = []
    for a in angles:
        if len(out) >= count:
            break
        p = ray_exit(s.x, s.y, a, medina, reach)
        if p is None or any(p.distance(q) < 60.0 for q in out):
            continue
        outward = Point(p.x + 15 * math.cos(a), p.y + 15 * math.sin(a))
        if ctx.boundary.contains(outward):
            out.append(p)
    return out


def alley_network(ctx, area, site, gate_pts, entrance, dc, medina=None, wall=0.0, reach=0.0) -> list:
    """Alleys from a Voronoi pattern: souks join gates to the mosque, other alleys are thinned out."""
    rng = ctx.rng("medina-alleys")
    cell = float(dc["cell"])
    inner = area.difference(site) if site is not None else area
    pts = jittered_grid(inner, cell, rng)
    if len(pts) < 4:
        return []
    cells = shapely.voronoi_polygons(MultiPoint(pts), extend_to=inner.envelope.buffer(3 * cell))
    pieces = [c.intersection(inner) for c in cells.geoms]
    edges = lines(unary_union([p.boundary for p in pieces if not p.is_empty]))
    rim = area.boundary
    segs = [g for g in edges if g.length > 0.5 and g.interpolate(0.5, normalized=True).distance(rim) > 0.5]
    if not segs:
        return []
    node_of: dict = {}
    ends = []
    for g in segs:
        c = g.coords
        pair = []
        for xy in (c[0], c[-1]):
            k = (round(xy[0], 2), round(xy[1], 2))
            pair.append(node_of.setdefault(k, len(node_of)))
        ends.append(pair)
    ends = np.array(ends)
    nodes = np.array(list(node_of.keys()))
    n = len(nodes)
    lengths = np.array([g.length for g in segs])
    graph = csr_matrix((np.concatenate([lengths, lengths]),
                        (np.concatenate([ends[:, 0], ends[:, 1]]), np.concatenate([ends[:, 1], ends[:, 0]]))),
                       shape=(n, n))
    edge_of = {}
    for e, (a, b) in enumerate(ends):
        edge_of[(a, b)] = edge_of[(b, a)] = e
    tree = cKDTree(nodes)
    target = int(tree.query([entrance.x, entrance.y])[1])
    _, pred = dijkstra(graph, indices=target, return_predecessors=True)
    souk = set()
    gate_nodes = []
    for g in gate_pts:
        cur = int(tree.query([g.x, g.y])[1])
        gate_nodes.append(cur)
        for _ in range(n):
            prev = pred[cur]
            if prev < 0:
                break
            souk.add(edge_of[(cur, int(prev))])
            cur = int(prev)
    keep = _thin(ends, n, souk, rng, float(dc["keep_alleys"]))
    streets = []
    for e in np.nonzero(keep)[0]:
        kind = "souk" if e in souk else "alley"
        streets.append(Street(kind, float(dc["souk_width"] if kind == "souk" else dc["alley_width"]), segs[e]))
    for g, node in zip(gate_pts, gate_nodes):
        # straight through the gate, from the ring road outside to the first crossing inside
        pts = [(g.x, g.y), tuple(nodes[node])]
        if medina is not None:
            n = _outward(medina, g, tangent_angle(medina.exterior, g))
            pts = [(g.x + n[0] * reach, g.y + n[1] * reach), (g.x, g.y),
                   (g.x - n[0] * (wall + 3.0), g.y - n[1] * (wall + 3.0)), tuple(nodes[node])]
        streets.append(Street("souk", float(dc["souk_width"]), LineString(pts)))
    return _merge(streets)


def _thin(ends: np.ndarray, n: int, souk: set, rng, keep: float) -> np.ndarray:
    """Which alleys exist: a random tree reaching every crossing (so no area is cut off),
    a few extra links for loops, then dead ends trimmed back. Lower `keep` = bigger blocks."""
    weights = rng.random(len(ends)) + 0.01
    weights[list(souk)] = 1e-6
    tree = minimum_spanning_tree(csr_matrix((weights, (ends[:, 0], ends[:, 1])), shape=(n, n))).tocoo()
    in_tree = {(min(a, b), max(a, b)) for a, b in zip(tree.row, tree.col)}
    kept = np.array([(min(a, b), max(a, b)) in in_tree for a, b in ends])
    kept |= rng.random(len(ends)) < 0.25 * keep
    kept[list(souk)] = True
    for _ in range(2):
        degree = np.bincount(ends[kept].ravel(), minlength=n)
        leaf = kept & ((degree[ends[:, 0]] == 1) | (degree[ends[:, 1]] == 1))
        leaf[list(souk)] = False
        kept &= ~(leaf & (rng.random(len(ends)) > keep))
    return kept


def _merge(streets: list) -> list:
    out = []
    for kind in sorted({s.kind for s in streets}):
        group = [s for s in streets if s.kind == kind]
        merged = shapely.line_merge(shapely.MultiLineString([s.line for s in group]))
        for line in lines(merged):
            out.append(Street(kind, group[0].width, line))
    return out


def ring_offset(ctx) -> float:
    """Distance from the old town's edge to the center line of the ring road around it."""
    aw = float(ctx.kc["arterial_width"])
    if not ctx.kc.get("walls"):
        return aw / 2 + 2.0
    return float(ctx.style["district"]["medina"]["wall_thickness"]) / 2 + 6.0 + aw / 2


def _outward(medina, p: Point, angle: float):
    n = np.array([-math.sin(angle), math.cos(angle)])
    return n if not medina.contains(Point(p.x + n[0], p.y + n[1])) else -n


def ramparts(ctx, medina, gate_pts, district: int, dc, streets=()) -> list:
    """City walls along the old town's edge, with towers and an opening at each gate.

    Where a street still meets the wall, the wall gets an opening and the tower is left out.
    """
    t, h = float(dc["wall_thickness"]), float(dc["wall_height"])
    ring = medina.exterior
    band = ring.buffer(t / 2, cap_style="flat", join_style="mitre")
    openings = []
    out = []
    for g in gate_pts:
        a = tangent_angle(ring, g)
        gw = float(dc["gate_width"])
        openings.append(rectangle(g.x, g.y, gw, 4 * t, a))
        out_n = _outward(medina, g, a) * 0.5 * t
        for side in (-1, 1):
            d = side * (gw / 2 + 1.1 * t)
            cx, cy = g.x + d * math.cos(a) + out_n[0], g.y + d * math.sin(a) + out_n[1]
            out.append(Building(rectangle(cx, cy, 2.2 * t, 2.2 * t, a), "tower", district, h + 4.0,
                                "rampart", "rampart"))
    openings += [st.line.buffer(st.width / 2 + 0.5, cap_style="flat") for st in streets]
    walls = band.difference(unary_union(openings)) if openings else band
    for p in polygons(walls):
        if p.area > 4.0:
            out.append(Building(p, "wall", district, h, "rampart", "rampart"))
    spacing = float(dc["tower_spacing"])
    for k in range(int(ring.length // spacing)):
        p = ring.interpolate(k * spacing)
        if any(p.distance(g) < 0.6 * spacing for g in gate_pts):
            continue
        a = tangent_angle(ring, p)
        n = _outward(medina, p, a) * 0.5 * t
        out.append(Building(rectangle(p.x + n[0], p.y + n[1], 2.0 * t, 2.0 * t, a), "tower", district, h + 2.5,
                            "rampart", "rampart"))
    if streets:
        clear = unary_union(openings[len(gate_pts):])
        out = [b for b in out if b.kind != "tower" or b.footprint.intersection(clear).area < 0.5]
    return out


def old_town(ctx, medina, district, axis, crossings) -> tuple:
    """Everything inside the old town except houses: (streets, buildings, cut polygon, landmarks, gates)."""
    s, kc = ctx.s, ctx.kc
    kind = "village" if kc["medina_radius"] >= 1.0 else "medina"
    dc = ctx.style["district"][kind]
    width, hall_depth, court_depth = kc["great_mosque"]
    name = ("Great Mosque of " + s.name) if kind == "medina" else ("Mosque of " + s.name)
    center = largest(medina.buffer(-0.5 * width)) if medina.area > 4 * width * width else None
    c = Point(s.x, s.y)
    if center is None or not center.contains(c):
        c = medina.representative_point() if center is None else center.representative_point()
    mosque, site, entrance, landmark = mosque_complex(c.x, c.y, ctx.qibla, width, hall_depth, court_depth,
                                                     kc["minaret"], district, name)
    count = {"capital": 6, "city": 5, "town": 4}.get(s.kind, 3)
    gate_pts = gates(ctx, medina, axis, crossings, count)
    wall = float(dc.get("wall_thickness", 3.0)) / 2 if kc.get("walls") else 0.0
    inner = medina.buffer(-(wall + float(dc["alley_width"]) / 2 + 0.6))
    streets = alley_network(ctx, inner, site, gate_pts, entrance, dc,
                            medina if kc.get("walls") else None, wall, ring_offset(ctx))
    buildings = list(mosque)
    cut = [site]
    if kc.get("walls"):
        walls = ramparts(ctx, medina, gate_pts, district, dc, streets)
        buildings += walls
        cut += [b.footprint for b in walls]
    landmarks = [landmark]
    names = ctx.namer
    for g in gate_pts:
        landmarks.append(Landmark("gate", names.district("gate"), g.x, g.y))
    return streets, buildings, unary_union(cut), landmarks, gate_pts
