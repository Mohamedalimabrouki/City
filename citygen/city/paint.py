"""Painted road markings: edge and lane lines, and zebra crossings.

A marking is a flat polygon a few centimetres above its street ribbon, clipped to the
carriageway: the street surface left between the raised sidewalks and, on a boulevard, the
central promenade. Markings are built once per plan, after the sidewalks exist, so a tile only
clips the polygons it touches. There is no randomness here: the paint follows the plan. Where a
side has a parking row (`parking.parked_sides`, prompt 25: only by the blocks of a parking district) its
edge line stands on the row's lane side; elsewhere it stays `paint_edge_inset` m in from the curb.
"""
from __future__ import annotations

import numpy as np
import shapely
from shapely.geometry import LineString
from shapely.ops import substring, unary_union
from shapely.strtree import STRtree

from .geo import lines, polygons
from .model import Paint
from .parking import parked_sides, walk_widths

MARKED = ("boulevard", "arterial", "connector")   # streets that get lines
CROSSED = ("boulevard", "arterial")               # streets whose junctions get zebra crossings


def street_surfaces(districts, streets, style) -> None:
    """Fill `Street.surface` from `[streets.surface]`; a village street is packed earth."""
    table = style.get("streets", {}).get("surface", {})
    village = unary_union([d.polygon for d in districts if d.kind == "village"])
    for st in streets:
        surface = str(table.get(st.kind, "asphalt"))
        if not village.is_empty and village.contains(st.line.representative_point()):
            surface = "earth"
        st.surface = surface


def _near(walks, tree, st, k: int) -> list:
    """The sidewalks touching street k's surface (whichever street each was filed under: a sidewalk
    wraps its whole block) and street k's promenade, in plan order."""
    area = st.line.buffer(st.width / 2.0, cap_style="flat")
    hit = sorted(int(i) for i in tree.query(area, predicate="intersects")) if tree is not None else []
    return [walks[i] for i in hit if walks[i].kind == "sidewalk" or walks[i].street == k]


def _carriageway(st, k: int, walks, promenade_width: float):
    """Street surface minus the raised sidewalks on it and, on a boulevard, the promenade strip.

    `walks` are the walks near street k (see `_near`).
    """
    area = st.line.buffer(st.width / 2.0, cap_style="flat")
    cuts = [w.polygon for w in walks if w.kind == "sidewalk"]
    if any(w.street == k and w.kind == "promenade" for w in walks):
        cuts.append(st.line.buffer(promenade_width / 2.0, cap_style="flat"))
    if cuts:
        area = area.difference(unary_union(cuts))
    return area


def carriageway(plan, k: int, promenade_width: float = 8.0):
    """The drivable surface of street k, for tests and later traffic features."""
    tree = STRtree([w.polygon for w in plan.walks]) if plan.walks else None
    return _carriageway(plan.streets[k], k, _near(plan.walks, tree, plan.streets[k], k), promenade_width)


def _offset(line, distance: float) -> list:
    """One or more lines parallel to `line`; positive is left of its direction."""
    if abs(distance) < 1e-9:
        return [line]
    return lines(shapely.offset_curve(line, distance, join_style="mitre"))


def _dashes(line, pattern) -> list:
    """Short pieces of `line` following a dash-and-gap pattern in meters."""
    on, off = float(pattern[0]), float(pattern[1])
    if on <= 0.0 or off < 0.0:
        return [line]
    out = []
    start = 0.0
    while start < line.length - 1e-6:
        end = min(start + on, line.length)
        if end - start > 0.05:
            out.append(substring(line, start, end))
        start = end + off
    return out


def _strips(geom, width: float, area, k: int) -> list:
    """Thin flat strips along line parts, clipped to the carriageway."""
    out = []
    for part in lines(geom):
        if part.length <= 0.05:
            continue
        band = part.buffer(width / 2.0, cap_style="flat", join_style="mitre")
        for poly in polygons(band.intersection(area)):
            if poly.area > 0.005:
                out.append(Paint(poly, k))
    return out


def _spaced(stations: list, distance: float) -> list:
    """Sorted stations with neighbours closer than `distance` dropped (one crossing per spot)."""
    out = []
    for s in stations:
        if not out or s - out[-1] >= distance:
            out.append(s)
    return out


def _crossing(plan_street, area, station: float, length: float, stripe: float, gap: float,
              k: int) -> list:
    """One zebra crossing: bars along the street, repeated across the carriageway."""
    line = plan_street.line
    a = line.interpolate(max(station - 1.0, 0.0))
    b = line.interpolate(min(station + 1.0, line.length))
    t = np.array([b.x - a.x, b.y - a.y])
    size = float(np.hypot(*t))
    if size < 1e-9:
        return []
    t /= size
    normal = np.array([-t[1], t[0]])
    p = np.array([line.interpolate(station).x, line.interpolate(station).y])
    out = []
    step = stripe + gap
    offset = -plan_street.width / 2.0 + stripe / 2.0
    while offset < plan_street.width / 2.0 - stripe / 2.0:
        a0 = p - t * (length / 2.0) + normal * offset
        b0 = p + t * (length / 2.0) + normal * offset
        bar = LineString([a0, b0]).buffer(stripe / 2.0, cap_style="flat")
        for poly in polygons(bar.intersection(area)):
            if poly.area > 0.01:
                out.append(Paint(poly, k, "crossing"))
        offset += step
    return out


def _crossings(bands, band_tree, k: int, st, area, length: float, stripe: float, gap: float,
               junction_gap: float) -> list:
    """Zebra bars on both approaches of every junction on one boulevard or arterial."""
    centers = []
    for j in sorted(int(i) for i in band_tree.query(st.line, predicate="intersects")):
        if j == k:
            continue
        hit = st.line.intersection(bands[j])
        if hit.is_empty:
            continue
        pts = shapely.get_coordinates(hit)
        if not len(pts):
            continue
        d = shapely.line_locate_point(st.line, shapely.points(pts))
        lo, hi = float(np.min(d)), float(np.max(d))
        for s in (lo - junction_gap - length / 2.0, hi + junction_gap + length / 2.0):
            if length / 2.0 < s < st.line.length - length / 2.0:
                centers.append(s)
    out = []
    for s in _spaced(sorted(centers), length + 2.0):
        out += _crossing(st, area, s, length, stripe, gap, k)
    return out


def make_paint(style, streets, walks, districts=()) -> list:
    """All road markings of a city: edge and lane lines first, then zebra crossings."""
    cfg = style.get("streets", {})
    min_width = float(cfg.get("marking_min_width", 8.0))
    paint_width = float(cfg.get("paint_width", 0.12))
    inset = float(cfg.get("paint_edge_inset", 0.4))
    pattern = cfg.get("paint_dash", [3.0, 4.5])
    promenade = float(cfg.get("promenade_width", 8.0))
    cross_length = float(cfg.get("crossing_length", 3.0))
    stripe = float(cfg.get("crossing_stripe", 0.55))
    cross_gap = float(cfg.get("crossing_gap", 0.55))
    junction_gap = float(cfg.get("crossing_junction_gap", 1.0))

    widths, promoted, parks = walk_widths(style, districts, streets, walks, MARKED)
    parking = style.get("dressing", {}).get("parking", {})
    row = float(parking.get("row", 0.0))

    walk_tree = STRtree([w.polygon for w in walks]) if walks else None
    out: list = []
    for k, st in enumerate(streets):
        if st.width <= min_width or st.kind not in MARKED:
            continue
        area = _carriageway(st, k, _near(walks, walk_tree, st, k), promenade)
        if area.is_empty:
            continue
        out_l = st.width / 2.0 - widths.get((k, 1), 0.0)
        out_r = st.width / 2.0 - widths.get((k, -1), 0.0)
        parked = parked_sides(st, k, widths, promoted, parking, promenade, parks)   # an edge line moves out to
        edge_l = out_l - (row if 1 in parked else inset)                    # the lane side of a parking row
        edge_r = out_r - (row if -1 in parked else inset)
        if st.kind == "boulevard":
            inner = promenade / 2.0 if k in promoted else 0.0
            for sign, edge in ((1.0, edge_l), (-1.0, edge_r)):
                lane = (inner + inset + edge) / 2.0
                if lane - inner > 1.1:
                    for part in _offset(st.line, sign * lane):
                        for seg in _dashes(part, pattern):
                            out += _strips(seg, paint_width, area, k)
                if inner + inset < edge:
                    for off in (inner + inset, edge):
                        for part in _offset(st.line, sign * off):
                            out += _strips(part, paint_width, area, k)
        else:
            shift = (edge_l - out_l + inset) - (edge_r - out_r + inset)     # 0 unless one side parks
            for part in _offset(st.line, shift / 2.0):
                for seg in _dashes(part, pattern):
                    out += _strips(seg, paint_width, area, k)
            for off in (edge_l, -edge_r):
                for part in _offset(st.line, off):
                    out += _strips(part, paint_width, area, k)

    bands = [other.line.buffer(other.width / 2.0, cap_style="flat") for other in streets]
    band_tree = STRtree(bands)
    for k, st in enumerate(streets):
        if st.width <= min_width or st.kind not in CROSSED:
            continue
        area = _carriageway(st, k, _near(walks, walk_tree, st, k), promenade)
        if area.is_empty:
            continue
        out += _crossings(bands, band_tree, k, st, area, cross_length, stripe, cross_gap, junction_gap)
    return out
