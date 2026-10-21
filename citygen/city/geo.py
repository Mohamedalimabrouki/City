"""Small geometry helpers shared by the city planner."""
from __future__ import annotations

import math

import numpy as np
import shapely
from shapely.geometry import LineString, Point, Polygon


def polygons(geom) -> list:
    """Every Polygon inside any geometry (Multi*, collections), empty parts dropped."""
    if geom is None or geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom]
    out = []
    for part in getattr(geom, "geoms", []):
        out.extend(polygons(part))
    return out


def lines(geom) -> list:
    if geom is None or geom.is_empty:
        return []
    if geom.geom_type == "LineString":
        return [geom]
    if geom.geom_type == "LinearRing":
        return [LineString(geom.coords)]
    out = []
    for part in getattr(geom, "geoms", []):
        out.extend(lines(part))
    return out


def largest(geom):
    ps = polygons(geom)
    return max(ps, key=lambda p: p.area) if ps else None


def frame(poly) -> tuple:
    """Oriented bounding box: (cx, cy, length, width, angle of the long side)."""
    env = shapely.oriented_envelope(poly)
    if env.geom_type != "Polygon":
        c = poly.centroid
        return c.x, c.y, 0.0, 0.0, 0.0
    c = np.asarray(env.exterior.coords)[:4]
    e0, e1 = c[1] - c[0], c[2] - c[1]
    l0, l1 = math.hypot(*e0), math.hypot(*e1)
    cx, cy = c.mean(axis=0)
    if l0 >= l1:
        return cx, cy, l0, l1, math.atan2(e0[1], e0[0])
    return cx, cy, l1, l0, math.atan2(e1[1], e1[0])


def noisy_loop(cx, cy, radius, noise, n=64, amp=0.14, aspect=1.0, rotation=0.0) -> Polygon:
    """Closed blob around a center; `noise` is a Perlin(x, y) used along a circle."""
    t = np.linspace(0.0, 2 * math.pi, n, endpoint=False)
    r = radius * (1.0 + amp * noise(1.6 * np.cos(t), 1.6 * np.sin(t))
                  + amp * 0.4 * noise(4.0 * np.cos(t) + 9.0, 4.0 * np.sin(t) + 9.0))
    x, y = r * np.cos(t), r * np.sin(t) * aspect
    c, s = math.cos(rotation), math.sin(rotation)
    return Polygon(np.stack([cx + x * c - y * s, cy + x * s + y * c], axis=1)).buffer(0)


def ray_exit(cx, cy, angle, poly, reach) -> Point | None:
    """First point where a ray from (cx, cy) leaves `poly`."""
    ray = LineString([(cx, cy), (cx + reach * math.cos(angle), cy + reach * math.sin(angle))])
    hit = ray.intersection(poly.boundary)
    pts = [p for p in getattr(hit, "geoms", [hit]) if not p.is_empty and p.geom_type == "Point"]
    if not pts:
        return None
    return min(pts, key=lambda p: math.hypot(p.x - cx, p.y - cy))


def tangent_angle(ring, point: Point) -> float:
    d = ring.project(point)
    a, b = ring.interpolate(max(d - 2.0, 0.0)), ring.interpolate(min(d + 2.0, ring.length))
    return math.atan2(b.y - a.y, b.x - a.x)


def scatter(region, spacing_fn, rng, attempts: int) -> np.ndarray:
    """Points inside `region`, no two closer than spacing_fn(x, y) (dart throwing)."""
    minx, miny, maxx, maxy = region.bounds
    cand = rng.uniform([minx, miny], [maxx, maxy], size=(attempts, 2))
    shapely.prepare(region)
    cand = cand[shapely.contains_xy(region, cand[:, 0], cand[:, 1])]
    pts = np.zeros((0, 2))
    for x, y in cand:
        if len(pts) and np.min(np.hypot(pts[:, 0] - x, pts[:, 1] - y)) < spacing_fn(x, y):
            continue
        pts = np.vstack([pts, [x, y]])
    return pts


def jittered_grid(region, step: float, rng, jitter: float = 0.42) -> np.ndarray:
    minx, miny, maxx, maxy = region.bounds
    xs = np.arange(minx + step / 2, maxx, step)
    ys = np.arange(miny + step / 2, maxy, step)
    if not len(xs) or not len(ys):
        return np.zeros((0, 2))
    X, Y = np.meshgrid(xs, ys)
    pts = np.stack([X.ravel(), Y.ravel()], axis=1)
    pts += rng.uniform(-jitter, jitter, size=pts.shape) * step
    shapely.prepare(region)
    return pts[shapely.contains_xy(region, pts[:, 0], pts[:, 1])]
