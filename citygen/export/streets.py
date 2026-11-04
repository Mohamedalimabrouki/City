"""The street graph of a city for games (prompt 70): `cities/<name>/streets.json`, `citygen-streets/1`.

Nodes are junctions and dead ends, edges the street pieces between them, built by noding every
center line of `plan.streets` on a grid of `[streets] graph_grid` meters (5 cm, citygen/defaults.toml;
`unary_union` alone misses junctions that meet only up to rounding) (SPEC 6 "Street graph").
"""
from __future__ import annotations

import numpy as np
import shapely
from shapely import STRtree
from shapely.geometry import LineString, Point

from ..city.geo import lines
from ..city.parking import walk_widths

def center_lines(streets, grid: float) -> list:
    """Each street's center line. An impasse's starts at the nearest point of the street its mouth opens
    on (the planner starts the lane inside that street's surface, short of its center line), and that
    point becomes a vertex of the street too, so the grid snaps both to the same node."""
    out = [st.line for st in streets]
    others = [k for k, st in enumerate(streets) if st.kind != "impasse"]
    if len(others) == len(streets) or not others:
        return out
    tree = STRtree([streets[k].line for k in others])
    cuts: dict = {}
    for k, st in enumerate(streets):
        if st.kind != "impasse":
            continue
        mouth = Point(st.line.coords[0])
        h = others[int(tree.nearest(mouth))]
        d = streets[h].line.project(mouth)
        q = streets[h].line.interpolate(d)
        if 0.0 < mouth.distance(q) <= streets[h].width / 2 + grid:
            out[k] = LineString([(q.x, q.y), *st.line.coords])
            cuts.setdefault(h, []).append(d)
    for h, ds in cuts.items():
        out[h] = _with_vertices(streets[h].line, sorted(ds))
    return out


def _with_vertices(line, ds: list):
    """`line` with a vertex added at each distance of `ds` (sorted) along it."""
    xy = np.asarray(line.coords)
    at = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(xy, axis=0).T))])
    pts = [line.interpolate(d) for d in ds]
    order = np.argsort(np.concatenate([at, ds]), kind="stable")
    allp = [tuple(c) for c in xy.tolist()] + [(p.x, p.y) for p in pts]
    return LineString([allp[i] for i in order])


def noded(streets, grid: float) -> list:
    """(street index, LineString) of every piece between junctions, each running the way its street runs.

    A piece lying on several streets (a grid street left under a boulevard) belongs to the widest,
    the lowest index on a tie: the one drawn on top.
    """
    centers = center_lines(streets, grid)
    snapped = [shapely.set_precision(line, grid) for line in centers]
    pieces = lines(shapely.unary_union([g for g in snapped if not g.is_empty], grid_size=grid))
    tree = STRtree(snapped)
    out = []
    for piece in pieces:
        mid = piece.interpolate(0.5, normalized=True)
        hits = sorted(tree.query(mid, predicate="dwithin", distance=grid).tolist())
        if not hits:
            hits = [int(tree.nearest(mid))]
        k = max(hits, key=lambda h: (streets[h].width, -h))
        line = centers[k]
        a, b = (piece.interpolate(t, normalized=True) for t in (0.25, 0.75))   # not the ends: a ring's
        if line.project(a) > line.project(b):                                    # start is also its end
            piece = piece.reverse()
        out.append((k, piece))
    return out


def _merged(pieces: list) -> list:
    """Join pieces of one street that meet end to end where nothing else does (a node of degree 2)."""
    ends: dict = {}
    for i, (_k, piece) in enumerate(pieces):
        for p in (piece.coords[0], piece.coords[-1]):
            ends.setdefault(p, []).append(i)
    alive = [True] * len(pieces)
    pieces = list(pieces)
    for p in sorted(ends):
        ids = [i for i in ends[p] if alive[i]]
        if len(ids) != 2 or ids[0] == ids[1]:
            continue
        (ka, a), (kb, b) = pieces[ids[0]], pieces[ids[1]]
        if ka != kb:
            continue
        if a.coords[-1] == p and b.coords[0] == p:
            first, second, keep, drop = a, b, ids[0], ids[1]
        elif b.coords[-1] == p and a.coords[0] == p:
            first, second, keep, drop = b, a, ids[1], ids[0]
        else:
            continue
        pieces[keep] = (ka, LineString(list(first.coords) + list(second.coords)[1:]))
        alive[drop] = False
        far = second.coords[-1]
        ends[far] = [keep if i == drop else i for i in ends[far]]
    return [pc for pc, ok in zip(pieces, alive) if ok]


def street_graph(streets, grid: float) -> tuple:
    """(nodes as (x, y) in first-use order, edges as (street index, LineString, node a, node b))."""
    index: dict = {}
    nodes, edges = [], []
    for k, piece in _merged(noded(streets, grid)):
        ab = []
        for p in (piece.coords[0], piece.coords[-1]):
            if p not in index:
                index[p] = len(nodes)
                nodes.append(p)
            ab.append(index[p])
        edges.append((k, piece, ab[0], ab[1]))
    return nodes, edges


def road_links(world, plan, nodes: list) -> list:
    """Where each country road crosses the city limit, and the graph's nearest node to that point."""
    if not nodes:
        return []
    tree = STRtree([Point(p) for p in nodes])
    edge = plan.boundary.exterior
    out = []
    for r in world.roads:
        line = LineString(r.coords)
        if not line.intersects(edge):
            continue
        hit = line.intersection(edge)
        for p in sorted((g for g in getattr(hit, "geoms", [hit]) if g.geom_type == "Point"),
                        key=lambda g: line.project(g)):
            n = int(tree.nearest(p))
            out.append({"road": r.id, "kind": r.kind, "width": r.width, "x": round(p.x, 2), "y": round(p.y, 2),
                        "node": n, "distance": round(p.distance(Point(nodes[n])), 2)})
    return out


def streets_json(world, plan, ground) -> dict:
    """The street graph of one city; z of a node is the drawn street top there (`Ground.surface`)."""
    nodes, edges = street_graph(plan.streets, float(world.cfg["streets"]["graph_grid"]))
    xy = np.asarray(nodes, dtype=np.float64).reshape(-1, 2)
    z = np.asarray(ground.surface(xy[:, 0], xy[:, 1]), dtype=np.float64) if len(xy) else np.zeros(0)
    widths, _promoted, _parks = walk_widths(world.style, plan.districts, plan.streets, getattr(plan, "walks", []))
    degree = np.bincount([n for _k, _p, a, b in edges for n in (a, b)], minlength=len(nodes))
    return {
        "format": "citygen-streets/1",
        "city": plan.settlement.name,
        "nodes": [{"id": i, "x": round(float(x), 2), "y": round(float(y), 2), "z": round(float(h), 2),
                   "degree": int(degree[i])} for i, ((x, y), h) in enumerate(zip(xy.tolist(), z.tolist()))],
        "edges": [{"id": e, "street": k, "kind": plan.streets[k].kind, "width": plan.streets[k].width,
                   "sidewalks": [round(widths.get((k, 1), 0.0), 2), round(widths.get((k, -1), 0.0), 2)],
                   "surface": plan.streets[k].surface or "asphalt", "length": round(piece.length, 2),
                   "from": a, "to": b, "line": np.round(np.asarray(piece.coords), 2).tolist()}
                  for e, (k, piece, a, b) in enumerate(edges)],
        "roads": road_links(world, plan, nodes),
    }
