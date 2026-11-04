"""A river through a city (prompt 61): a barrier the plan is cut along, not a street crossing it.

The capital and the cities never move for water, so a river may run anywhere through them. `Carve.corridor` gives
what no plan may touch: the water, its banks and `[rivers] keep` m. The plan then keeps off it from the start:

  old town   stands on one bank, the largest piece of its outline that leaves room for the ring road
  districts  each neighborhood's Voronoi cell is cut along the corridor, so both banks hold pieces of one
             cell, and the cut edge becomes an arterial along the bank, a quay; a border that crosses the river
             ends on both quays, face to face: a `Crossing`, where prompt 62 puts a bridge
  streets    what still crosses (a link to a country road) is cut at the corridor, also leaving a `Crossing`
  station    its site must keep its tracks on dry land
  walks      a paved riverside walk runs on the corridor's edge in cities and towns, with a row of trees

A village has no quays: it stands on the bank its center lies on (its land leaves the corridor out). Nothing
else in the plan knows about rivers: blocks, lots and buildings stand on what is left. A city no river reaches is
planned exactly as before, draw for draw.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
import shapely
from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

from ..names import NameMaker
from .geo import lines, polygons
from .model import District, Tree, Walk

MIN_PIECE = 6000.0   # square meters: a smaller piece of a neighborhood across the river is left to the bank


@dataclass
class Crossing:
    """Where a street would cross the river: a bridge's place for prompt 62."""
    line: object       # LineString from one bank's street end to the other's
    kind: str          # the street kind cut there
    width: float


def walk_width(ctx) -> float:
    """Meters of riverside walk on each bank, 0 where the settlement has none."""
    return float(ctx.style.get("river", {}).get("walk", 0.0)) if ctx.kc.get("riverside") else 0.0


def corridor(world, s):
    """The rivers' corridor round a settlement, or None."""
    if world.carve is None:
        return None
    r = 1.5 * s.radius + 300.0
    return world.carve.corridor(s.x - r, s.y - r, s.x + r, s.y + r)


def banks(ctx):
    """What the districts keep off: the corridor, the riverside walk and half a quay."""
    return ctx.water.buffer(walk_width(ctx) + 0.5 * float(ctx.kc["arterial_width"]), quad_segs=4).simplify(1.5)


def cut_streets(streets: list, water) -> tuple:
    """(streets, crossings): every street off the corridor, a crossing left where one was cut in two."""
    tree = shapely.STRtree([st.line for st in streets]) if streets else None
    hit = set(tree.query(water, predicate="intersects").tolist()) if tree is not None else set()
    out, crossings = [], []
    for k, st in enumerate(streets):
        if k not in hit:
            out.append(st)
            continue
        parts = [p for p in lines(st.line.difference(water)) if p.length > 4.0]
        parts.sort(key=lambda p: st.line.project(shapely.Point(p.coords[0])))
        out += [replace(st, line=p) for p in parts]
        for a, b in zip(parts[:-1], parts[1:]):
            crossings.append(Crossing(LineString([a.coords[-1], b.coords[0]]), st.kind, st.width))
    return out, crossings


def split_districts(ctx, districts: list) -> list:
    """Cut the neighborhoods along the river: a district keeps its id, kind and name on its largest piece, a piece
    across the river is a new district at the end of the list, so no other district changes. Returns the
    crossings this leaves: each border between two neighborhoods broken by the cut, from bank to bank."""
    outer = [d for d in districts if d.kind not in ("medina", "village")]
    borders = unary_union([d.polygon.boundary for d in outer]).intersection(ctx.banks) if outer else None
    namer = NameMaker(ctx.style, ctx.rng("river", "district-names"))
    namer.used.update(d.name.split()[-1] for d in districts)
    for d in outer:
        if not d.polygon.intersects(ctx.banks):
            continue
        pieces = sorted(polygons(d.polygon.difference(ctx.banks)), key=lambda p: -p.area)
        fit = [p for p in pieces if p.area > MIN_PIECE and not p.buffer(-12.0).is_empty]
        d.polygon = (fit or pieces or [Polygon()])[0]
        kind = "industrial" if d.kind == "port" else d.kind      # one harbor to a port: its largest piece
        for p in fit[1:]:
            districts.append(District(len(districts), kind, namer.district(kind), p, d.angle))
    if borders is None:
        return []
    edge = ctx.banks.boundary
    width = float(ctx.kc["arterial_width"])
    out = []
    for piece in lines(shapely.line_merge(borders)):
        ends = shapely.points(np.asarray(piece.coords)[[0, -1]])
        if piece.length > 2.0 and np.all(shapely.distance(edge, ends) < 1.0):
            out.append(Crossing(piece, "arterial", width))
    return out


def link_banks(ctx, streets: list, crossings: list) -> list:
    """`crossings`, and one more for each part of the street graph no crossing reaches: the shortest way from it to
    the rest of the city, where that way crosses the river. Prompt 62's bridges then join every bank."""
    from ..export.streets import street_graph
    nodes, edges = street_graph(streets, float(ctx.world.cfg["street_graph"]["grid"]))
    parent = list(range(len(nodes)))

    def root(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for _k, _line, a, b in edges:
        parent[root(a)] = root(b)
    for c in crossings:
        ends = shapely.points(np.asarray(c.line.coords)[[0, -1]])
        a, b = (int(np.argmin(shapely.distance(shapely.points(nodes), e))) for e in ends)
        parent[root(a)] = root(b)
    parts: dict = {}
    for _k, line, a, _b in edges:
        parts.setdefault(root(a), []).append(line)
    pieces = sorted((shapely.MultiLineString(v) for v in parts.values()), key=lambda g: (-g.length, g.bounds))
    out = list(crossings)
    joined = pieces[0] if pieces else None
    for part in pieces[1:]:
        if part.length < float(ctx.style["river"]["min_part"]):
            continue
        way = shapely.shortest_line(part, joined)
        if way.intersects(ctx.water):
            out.append(Crossing(way, "street", float(ctx.style["district"]["residential"]["street_width"])))
            joined = joined.union(part)
    return out


def riverside_walks(ctx, streets: list, keep_off) -> list:
    """The paved walk along the corridor's edge, in pieces a tile can own; `keep_off` the old town and what else
    it must leave alone."""
    width, piece = walk_width(ctx), float(ctx.style.get("river", {}).get("walk_piece", 64.0))
    if width <= 0.0:
        return []
    band = ctx.water.buffer(width, quad_segs=4).difference(ctx.water).intersection(ctx.boundary)
    cuts = [st.line.buffer(st.width / 2, quad_segs=2, cap_style="flat") for st in streets
            if st.line.distance(band) < st.width]
    band = band.difference(unary_union(cuts + ([keep_off] if keep_off is not None else [])))
    x0, y0, x1, y1 = band.bounds if not band.is_empty else (0.0, 0.0, 0.0, 0.0)
    xs = np.arange(x0 // piece, x1 // piece + 1) * piece
    ys = np.arange(y0 // piece, y1 // piece + 1) * piece
    squares = [box(x, y, x + piece, y + piece) for x in xs for y in ys]
    near = band.buffer(0.0)
    out = []
    for sq in squares:
        for p in polygons(sq.intersection(near)):
            if p.area > 12.0 and not p.buffer(-0.8).is_empty:
                out.append(Walk("riverside", p, width))
    return out


def riverside_trees(ctx, walks: list) -> list:
    """A row of shade trees down the middle of the walk, each stretch on its own stream: appended before the greenery,
    which keeps clear of them."""
    if not walks:
        return []
    cfg = ctx.style["river"]
    spacing, width = float(cfg["tree_spacing"]), walks[0].width
    middle = ctx.water.buffer(0.5 * width, quad_segs=4).boundary.intersection(unary_union([w.polygon for w in walks]))
    out = []
    for k, line in enumerate(lines(shapely.line_merge(middle))):
        rng = ctx.rng("riverside", k)
        for d in np.arange(0.5 * spacing, line.length, spacing):
            p = line.interpolate(float(d))
            out.append(Tree(p.x, p.y, str(cfg["tree"]), float(rng.uniform(*cfg["tree_height"]))))
    return out
