"""Painted road markings: edge and lane lines, and zebra crossings.

A marking is a flat polygon a few centimetres above its street ribbon, clipped to the
carriageway: the street surface left between the raised sidewalks and, on a boulevard, the
central promenade. Markings are built once per plan, after the sidewalks exist, so a tile only
clips the polygons it touches. There is no randomness here: the paint follows the plan.
"""
from __future__ import annotations

import numpy as np
import shapely
from shapely.geometry import LineString
from shapely.ops import substring, unary_union

from .geo import lines, polygons
from .model import Paint

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


def _carriageway(st, k: int, walks, promenade_width: float):
    """Street surface minus its raised sidewalks and, on a boulevard, the promenade strip."""
    area = st.line.buffer(st.width / 2.0, cap_style="flat")
    cuts = [w.polygon for w in walks if w.street == k and w.kind == "sidewalk"]
    if any(w.street == k and w.kind == "promenade" for w in walks):
        cuts.append(st.line.buffer(promenade_width / 2.0, cap_style="flat"))
    if cuts:
        area = area.difference(unary_union(cuts))
    return area


def carriageway(plan, k: int, promenade_width: float = 8.0):
    """The drivable surface of street k, for tests and later traffic features."""
    return _carriageway(plan.streets[k], k, plan.walks, promenade_width)


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
                out.append(Paint(poly, k))
        offset += step
    return out


def _crossings(streets, k: int, st, area, length: float, stripe: float, gap: float,
               junction_gap: float) -> list:
    """Zebra bars on both approaches of every junction on one boulevard or arterial."""
    centers = []
    for j, other in enumerate(streets):
        if j == k:
            continue
        band = other.line.buffer(other.width / 2.0, cap_style="flat")
        hit = st.line.intersection(band)
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


def make_paint(style, streets, walks) -> list:
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

    widths: dict = {}
    promoted = set()
    for w in walks:
        if w.kind == "sidewalk" and w.street >= 0:
            key = (w.street, w.side)
            widths[key] = max(widths.get(key, 0.0), w.width)
        elif w.kind == "promenade" and w.street >= 0:
            promoted.add(w.street)

    out: list = []
    for k, st in enumerate(streets):
        if st.width <= min_width or st.kind not in MARKED:
            continue
        area = _carriageway(st, k, walks, promenade)
        if area.is_empty:
            continue
        out_l = st.width / 2.0 - widths.get((k, 1), 0.0)
        out_r = st.width / 2.0 - widths.get((k, -1), 0.0)
        if st.kind == "boulevard":
            inner = promenade / 2.0 if k in promoted else 0.0
            for sign, outer in ((1.0, out_l), (-1.0, out_r)):
                lane = (inner + outer) / 2.0
                if lane - inner > 1.1:
                    for part in _offset(st.line, sign * lane):
                        for seg in _dashes(part, pattern):
                            out += _strips(seg, paint_width, area, k)
                if inner + inset < outer - inset:
                    for off in (inner + inset, outer - inset):
                        for part in _offset(st.line, sign * off):
                            out += _strips(part, paint_width, area, k)
        else:
            for seg in _dashes(st.line, pattern):
                out += _strips(seg, paint_width, area, k)
            for off in (out_l - inset, -(out_r - inset)):
                for part in _offset(st.line, off):
                    out += _strips(part, paint_width, area, k)

    for k, st in enumerate(streets):
        if st.width <= min_width or st.kind not in CROSSED:
            continue
        area = _carriageway(st, k, walks, promenade)
        if area.is_empty:
            continue
        out += _crossings(streets, k, st, area, cross_length, stripe, cross_gap, junction_gap)
    return out
