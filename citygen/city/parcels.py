"""City blocks (land between streets) and the parcels (building lots) inside them."""
from __future__ import annotations

import numpy as np
import shapely
from shapely.geometry import Polygon
from shapely.strtree import STRtree
from shapely.ops import unary_union

from .geo import frame, polygons
from .model import Parcel

MIN_BLOCK = {"medina": 60.0, "village": 80.0}


def make_blocks(ctx, districts, streets, extra_cuts=None) -> list:
    """[(block polygon, district id)]: each district minus the street surfaces crossing it."""
    tree = STRtree([st.line for st in streets]) if streets else None
    reach = max((st.width for st in streets), default=0.0) / 2 + 1.0
    out = []
    for d in districts:
        cuts = []
        if tree is not None:
            for i in tree.query(d.polygon, predicate="dwithin", distance=reach):
                st = streets[int(i)]
                cuts.append(st.line.buffer(st.width / 2, quad_segs=2, cap_style="flat"))
        if extra_cuts is not None and not extra_cuts.is_empty and extra_cuts.intersects(d.polygon):
            cuts.append(extra_cuts)
        rest = d.polygon.difference(unary_union(cuts)) if cuts else d.polygon
        min_area = MIN_BLOCK.get(d.kind, 250.0)
        for p in polygons(rest):
            if p.area >= min_area and not p.buffer(-1.8).is_empty:
                out.append((p, d.id))
    return out


def subdivide(poly, target: float, rng, max_depth: int = 14) -> list:
    """Split a block across its long side, again and again, until pieces are about `target` m2."""
    out = []
    stack = [(poly, 0)]
    while stack:
        p, depth = stack.pop()
        if p.area <= target * rng.uniform(0.75, 1.45) or depth >= max_depth:
            out.append(p)
            continue
        cx, cy, length, width, angle = frame(p)
        if length < 4.0:
            out.append(p)
            continue
        u = np.array([np.cos(angle), np.sin(angle)])
        n = np.array([-u[1], u[0]])
        cut = np.array([cx, cy]) + u * length * rng.uniform(-0.12, 0.12)
        big = 2.0 * (length + width) + 10.0
        halves = (Polygon([cut + n * big, cut + n * big + u * big, cut - n * big + u * big, cut - n * big]),
                  Polygon([cut + n * big, cut - n * big, cut - n * big - u * big, cut + n * big - u * big]))
        pieces = []
        for half in halves:
            pieces += [q for q in polygons(p.intersection(half)) if q.area > 2.0]
        if len(pieces) < 2:
            out.append(p)
            continue
        stack.extend((q, depth + 1) for q in pieces)
    return out


def make_parcels(ctx, blocks, districts) -> list:
    out = []
    for k, (block, did) in enumerate(blocks):
        kind = districts[did].kind
        dc = ctx.style["district"].get(kind, {})
        if "parcel_area" not in dc:
            continue
        rng = ctx.rng("parcels", k)
        pieces = subdivide(block, float(dc["parcel_area"]), rng)
        edge = block.boundary.buffer(0.4)
        front = shapely.length(shapely.intersection(np.array([p.exterior for p in pieces], dtype=object), edge))
        for p, f in zip(pieces, front):
            out.append(Parcel(p, did, bool(f >= 3.5), k))
    return out
