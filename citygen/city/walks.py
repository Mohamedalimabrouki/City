"""Raised sidewalks along blocks and the central promenade of a boulevard.

A sidewalk is the part of the street surface next to a block: the block is grown by the
district's sidewalk width, the block itself is removed, and the band is clipped to the side
strips of the streets. The side strips leave at least `[streets] min_carriageway` meters of
asphalt in the middle, so a tight street simply gets a narrower sidewalk.

The boulevard's promenade is a raised strip under the middle row of trees, built as short
pieces so a piece can belong to one tile without a huge mesh crossing the map.
"""
from __future__ import annotations

import numpy as np
import shapely
from shapely.ops import substring, unary_union
from shapely.strtree import STRtree

from .geo import polygons
from .model import Walk

# old towns, parks and cemeteries keep their own ground: no raised sidewalks there
NO_WALK = {"medina", "village", "park", "cemetery"}


def _nearest_street(tree: STRtree, streets: list, point) -> tuple:
    """(street index, side) nearest to a point; side is +1 left of the line, -1 right."""
    k = int(tree.nearest(point))
    line = streets[k].line
    d = float(line.project(point))
    q = line.interpolate(d)
    a = line.interpolate(max(d - 1.0, 0.0))
    b = line.interpolate(min(d + 1.0, line.length))
    t = np.array([b.x - a.x, b.y - a.y])
    o = np.array([point.x - q.x, point.y - q.y])
    if np.hypot(*t) < 1e-9 or np.hypot(*o) < 1e-9:
        return k, 0
    return k, 1 if t[0] * o[1] - t[1] * o[0] > 0.0 else -1


def make_walks(ctx, districts, streets, blocks) -> list:
    """Sidewalks for every non-traditional block, then the boulevard promenade."""
    if not streets:
        return []
    cfg = ctx.style.get("streets", {})
    min_carriage = float(cfg.get("min_carriageway", 5.5))
    promenade_width = float(cfg.get("promenade_width", 8.0))
    promenade_piece = float(cfg.get("promenade_piece", 64.0))

    # The side strips of every street: sidewalk may use these, the middle stays carriageway.
    strips = []
    for st in streets:
        cap = (st.width - min_carriage) / 2.0
        if cap <= 0.0:
            continue
        outer = st.line.buffer(st.width / 2.0, cap_style="flat")
        inner = st.line.buffer(st.width / 2.0 - cap, cap_style="flat")
        strips.append(outer.difference(inner))
    if not strips:
        return []
    allowed = unary_union(strips)

    lines = [st.line for st in streets]
    tree = STRtree(lines)
    table = ctx.style["district"]
    walks = []
    for bi, (block, did) in enumerate(blocks):
        kind = districts[did].kind
        width = float(table.get(kind, {}).get("sidewalk_width", 0.0))
        if kind in NO_WALK or width <= 0.0:
            continue
        band = block.buffer(width, join_style="mitre", quad_segs=3).difference(block)
        band = band.intersection(allowed)
        for poly in polygons(band):
            if poly.area < 0.8 or poly.length <= 0.0:
                continue
            k, side = _nearest_street(tree, streets, poly.representative_point())
            actual = min(width, max(0.0, (streets[k].width - min_carriage) / 2.0))
            if actual < 0.8:
                continue
            walks.append(Walk("sidewalk", poly, actual, k, side, did, bi))

    for k, st in enumerate(streets):
        if st.kind != "boulevard" or st.width - promenade_width < 2.0 * min_carriage:
            continue
        for start in np.arange(0.0, st.line.length, promenade_piece):
            end = min(float(start + promenade_piece), st.line.length)
            if end - start < 2.0:
                continue
            seg = substring(st.line, float(start), end)
            poly = seg.buffer(promenade_width / 2.0, cap_style="flat", join_style="mitre")
            if poly.area > 1.0:
                walks.append(Walk("promenade", poly, promenade_width, k, 0, -1, -1))
    return walks
