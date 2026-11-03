"""Courts of the new districts (47.2): a deep colonial block or maison gets courts cut from its footprint.

A room is lit when it lies within `reach` m of a wall that holds windows: a street wall or a wall facing
open ground (the dresser's own rule); party walls hold none. Where a footprint reaches deeper, courts are
cut as holes, as the old town's courtyard houses have them: a colonial block a main courtyard where the
deep part is wide and light wells (courettes) where it is narrow, a maison one patio. Every court is a
rectangle along the footprint's own frame, `front` m or more behind a windowed wall (the rooms between
keep a sensible depth), `party` m or more from a party wall (a neighbour's open-wall probe never reaches
it) and `between` m from another court. A maison too narrow for that (7-9 m lots) gets one court against a
party wall instead (`against_for`), `own` m from it: the house keeps its own wall there, so the court is
still a hole and the outer ring and the neighbours stay as they were. Numbers: `[courts]` in the style pack.

`courts_for` is a pure function of the footprint, which walls hold windows and the numbers; `apply_courts`
runs it on a plan after the rest of the massing (city/massing.py) and draws nothing.
"""
from __future__ import annotations

import math

import numpy as np
import shapely
from shapely.geometry import Point, Polygon
from shapely.strtree import STRtree

from .geo import frame
from .openings import open_walls, wall_arrays

LEFT = 0.05  # m2: dark slivers smaller than this count as lit (numerical noise)


def kinds_of(cfg: dict) -> dict:
    """Court kind -> (smallest side, largest side) in meters, from `[courts.sizes]`."""
    return {k: (float(v[0]), float(v[1])) for k, v in cfg.get("sizes", {}).items()}


def plan_of(cfg: dict, building: str) -> list:
    """The courts a building of this sort may get, in order (`[courts.plan]`, for example a main court then
    light wells)."""
    return list(cfg.get("plan", {}).get(building, []))


def courts_for(fp, lit, cfg: dict, order: list, avoid=None) -> list:
    """[(kind, Polygon)]: the courts to cut from footprint `fp` (no holes) so that no point of it lies
    farther than `reach` from a lit wall or a court. `lit` holds one bool per wall of `wall_arrays(fp)`
    (True: the wall holds windows); `order` the court kinds to try, in turn (`[courts.plan]`); `avoid` a
    geometry no court may touch. A court that lights nothing new is not cut; an empty list when nothing is
    dark or no court fits."""
    p, q, _n, length = wall_arrays(fp)
    lit = np.asarray(lit, dtype=bool) & (length > 1e-6)
    if not lit.any() or not order:
        return []
    g, reach = float(cfg.get("grid", 0.5)), float(cfg.get("reach", 6.5))
    sizes = kinds_of(cfg)
    lines = shapely.multilinestrings([[a, b] for a, b in zip(p[lit], q[lit])])
    party = ~lit & (length > 1e-6)
    walls = shapely.multilinestrings([[a, b] for a, b in zip(p[party], q[party])]) if party.any() else None
    shade = fp.difference(lines.buffer(reach, quad_segs=16))          # the dark part, exactly
    if shade.area < float(cfg.get("min_dark", 1.0)):
        return []
    grid = _Grid(fp, g)
    d_lit = shapely.distance(lines, grid.points)
    dark = grid.inside & (d_lit > reach)                              # its cells (to count what a court lights)
    half = g / 2                                      # a cell's side from its center (walls along the frame)
    allowed = grid.inside & (d_lit >= float(cfg.get("front", 4.5)) + half)
    if walls is not None:
        allowed &= shapely.distance(walls, grid.points) >= float(cfg.get("party", 3.0)) + half
    if avoid is not None and not avoid.is_empty:
        allowed &= shapely.distance(avoid, grid.points) >= half
    between = float(cfg.get("between", 3.0))
    out = []
    for kind in order:
        if shade.area < LEFT:
            break
        lo, hi = sizes[kind]
        rect = _best(grid, allowed, dark, grid.local(shade.convex_hull), lo, hi, reach)
        if rect is None:
            continue
        court = grid.polygon(*rect)
        out.append((kind, court))
        shade = shade.difference(court.buffer(reach, quad_segs=16))
        dark &= _to_rect(grid.x, grid.y, *rect) > reach
        allowed &= _to_rect(grid.x, grid.y, *rect) >= between + half
    return out


def against_for(fp, lit, cfg: dict, order: list, avoid=None, faced=None) -> list:
    """[(kind, Polygon)]: for a footprint `courts_for` leaves dark (a narrow lot with no room for a court
    clear of both party walls), a court against one party wall, as narrow Tunisian town houses have their
    patio or light well: a side patio, a light well in a back corner or a rear court across the lot. The
    court is a rectangle along that party wall, `own` m from it (the house keeps its own wall there, so
    the outer ring and every neighbour stay as they were), `front` m or more from a windowed wall; every
    other party wall lies within `own` + `snug` m of it (against it too) or `party` m or more away, and
    the floor left round it stays one piece. Chosen as `courts_for` chooses (`_choose`). `faced`: walls that
    may hold a window though `lit` leaves them out (short ones), kept `front` m away too. `[courts]`."""
    p, q, n, length = wall_arrays(fp)
    lit = np.asarray(lit, dtype=bool) & (length > 1e-6)
    party = ~lit & (length > 1e-6)
    if not lit.any() or not party.any() or not order:
        return []
    faced = lit if faced is None else lit | (np.asarray(faced, dtype=bool) & (length > 1e-6))
    g, reach = float(cfg.get("grid", 0.5)), float(cfg.get("reach", 6.5))
    own, snug = float(cfg.get("own", 0.3)), float(cfg.get("snug", 0.3))
    front, apart = float(cfg.get("front", 4.0)), float(cfg.get("party", 2.4))
    sizes = kinds_of(cfg)
    lines = shapely.multilinestrings([[a, b] for a, b in zip(p[lit], q[lit])])
    shade = fp.difference(lines.buffer(reach, quad_segs=16))
    if shade.area < float(cfg.get("min_dark", 1.0)):
        return []
    grid = _Grid(fp, g)
    dark_pts = shapely.get_coordinates(grid.points[grid.inside & (shapely.distance(lines, grid.points) > reach)])
    inner = fp.buffer(-(own - 1e-6), join_style="mitre")
    shapely.prepare(inner)
    floor = fp.buffer(-own, join_style="mitre")
    segs = shapely.linestrings(np.stack([p, q], axis=1))
    out = []
    for kind in order:
        if shade.area < LEFT:
            break
        lo, hi = sizes[kind]
        walls = np.flatnonzero(party & (length >= lo + 2 * own))
        cands = [_along(p[i], q[i], -n[i], float(length[i]), own, lo, hi, g) for i in walls]
        cands = [c for c in cands if len(c[3])]
        if not cands:
            continue
        a = np.concatenate([np.repeat(c[0][None], len(c[3]), 0) for c in cands])
        u = np.concatenate([np.repeat(c[1][None], len(c[3]), 0) for c in cands])
        v = np.concatenate([np.repeat(c[2][None], len(c[3]), 0) for c in cands])
        box = np.concatenate([c[3] for c in cands])                  # (t0, t1, y0, y1) along u, into v
        court = None
        for chunk in _choose(a, u, v, box, shade, dark_pts, reach):    # in the order of choice, a chunk at a time
            ca, cu, cv, cb = a[chunk], u[chunk], v[chunk], box[chunk]
            corners = [ca + cu * cb[:, :1] + cv * cb[:, 2:3], ca + cu * cb[:, 1:2] + cv * cb[:, 2:3],
                       ca + cu * cb[:, 1:2] + cv * cb[:, 3:4], ca + cu * cb[:, :1] + cv * cb[:, 3:4]]
            polys = shapely.polygons(np.stack(corners + corners[:1], axis=1))
            ok = shapely.contains(inner, polys)
            if avoid is not None and not avoid.is_empty:
                ok &= ~shapely.intersects(avoid, polys)
            for j in np.flatnonzero(length > 1e-6):
                d = shapely.distance(segs[j], polys)
                ok &= d >= front - 1e-6 if faced[j] else (d <= own + snug + 1e-6) | (d >= apart - 1e-6)
            court = next((polys[k] for k in np.flatnonzero(ok) if _one_piece(floor, polys[k], own)), None)
            if court is not None:
                break
        if court is None:
            continue
        out.append((kind, court))
        shade = shade.difference(court.buffer(reach, quad_segs=16))
        if len(dark_pts):
            dark_pts = dark_pts[shapely.distance(court, shapely.points(dark_pts)) > reach]
    return out


def _along(a, b, v, length: float, own: float, lo: float, hi: float, g: float) -> tuple:
    """Candidate courts against the wall a-b (inward normal v): (a, u, v, boxes), each box (t0, t1, y0, y1)
    spanning t0..t1 along the wall and own..own + w into the house; its ends on a `g` grid from either end of
    the wall, `own` m in, so a court in a corner stands against the next wall too."""
    u = (b - a) / length
    ws = np.arange(lo, hi + 1e-6, g)
    rows = []
    for h in np.arange(lo, min(hi, length - 2 * own) + 1e-6, g):
        k = np.arange(int((length - 2 * own - h) / g + 1e-6) + 1)
        t0 = np.unique(np.round(np.concatenate([own + k * g, length - own - h - k * g]), 6))
        t0, w = np.repeat(t0, len(ws)), np.tile(ws, len(t0))
        rows.append(np.stack([t0, t0 + h, np.full(len(t0), own), own + w], axis=1))
    return a, u, v, (np.concatenate(rows) if rows else np.zeros((0, 4)))


CHUNK = 64           # candidate courts checked against the walls at a time


def _choose(a, u, v, box, shade, dark_pts: np.ndarray, reach: float):
    """Chunks of candidate court indices (origin a, frame u, v, boxes as `_along` gives them) in the order of
    choice: those lighting the whole dark part (every corner of its convex hull within `reach`), the smallest
    first, then the nearest the dark part's middle; then the others, those lighting the most dark points
    first, then the same."""
    def local(pts, at):                     # (cands `at`, points) in each court's frame, a wall at a time
        x, y = np.zeros((len(at), len(pts))), np.zeros((len(at), len(pts)))
        for o in np.unique(a[at], axis=0):
            mine = np.flatnonzero((a[at] == o).all(axis=1))
            d = pts - o
            x[mine], y[mine] = d @ u[at[mine[0]]], d @ v[at[mine[0]]]
        return x, y

    x0, x1, y0, y1 = (box[:, k:k + 1] for k in range(4))
    hull = shapely.get_coordinates(shade.convex_hull)
    area = np.round((box[:, 1] - box[:, 0]) * (box[:, 3] - box[:, 2]), 6)
    centre = a + u * box[:, :2].mean(axis=1, keepdims=True) + v * box[:, 2:].mean(axis=1, keepdims=True)
    mid = np.round(np.hypot(*(centre - hull.mean(axis=0)).T), 6)
    first = np.arange(len(box))
    full = np.zeros(len(box), dtype=bool)
    for size in np.unique(area):                     # smallest first: the later sizes only when needed
        at = np.flatnonzero(area == size)
        hx, hy = local(hull, at)
        full[at] = (_to_rect(hx, hy, x0[at], x1[at], y0[at], y1[at]) <= reach).all(axis=1)
        lead = at[full[at]]
        lead = lead[np.lexsort((first[lead], mid[lead]))]
        for i in range(0, len(lead), CHUNK):
            yield lead[i:i + CHUNK]
    if not len(dark_pts):
        return
    rest = np.flatnonzero(~full)
    if not len(rest):
        return
    sx, sy = local(dark_pts, rest)
    count = (_to_rect(sx, sy, x0[rest], x1[rest], y0[rest], y1[rest]) <= reach).sum(axis=1)
    keep = count > 0
    rest, count = rest[keep], count[keep]
    order = rest[np.lexsort((first[rest], mid[rest], area[rest], -count))]
    for i in range(0, len(order), CHUNK):
        yield order[i:i + CHUNK]


def _one_piece(floor, court, own: float) -> bool:
    """Does the floor inside the walls stay one piece once the court and its own walls are cut from it?"""
    left = floor.difference(court.buffer(own, join_style="mitre"))
    return sum(1 for part in getattr(left, "geoms", [left]) if part.area > 0.5) == 1


def darkest(fp, lit, courts: list, step: float = 0.25) -> float:
    """The farthest any point of `fp` (sampled every `step` m) lies from a lit wall or a court."""
    p, q, _n, length = wall_arrays(fp)
    lit = np.asarray(lit, dtype=bool) & (length > 1e-6)
    grid = _Grid(fp, step)
    pts = grid.points[grid.inside]
    if not len(pts):
        return 0.0
    d = np.full(len(pts), np.inf)
    if lit.any():
        d = shapely.distance(shapely.multilinestrings([[a, b] for a, b in zip(p[lit], q[lit])]), pts)
    for c in courts:
        d = np.minimum(d, shapely.distance(c, pts))
    return float(d.max())


class _Grid:
    """Cell centers every `g` m over the footprint's frame (x along its long side, y across)."""

    def __init__(self, fp, g: float):
        cx, cy, length, width, angle = frame(fp)
        self.c = np.array([cx, cy])
        self.u = np.array([math.cos(angle), math.sin(angle)])
        self.v = np.array([-self.u[1], self.u[0]])
        self.g = g
        nx, ny = int(math.ceil(length / g)) + 2, int(math.ceil(width / g)) + 2
        xs = (np.arange(nx) - (nx - 1) / 2) * g
        ys = (np.arange(ny) - (ny - 1) / 2) * g
        self.xs, self.ys = xs, ys
        self.x, self.y = np.meshgrid(xs, ys, indexing="ij")       # (nx, ny)
        w = self.c + self.x[..., None] * self.u + self.y[..., None] * self.v
        self.points = shapely.points(w)
        self.inside = shapely.contains_xy(fp, w[..., 0], w[..., 1])

    def local(self, geom) -> np.ndarray:
        """The coordinates of `geom` (its outline points) in the frame."""
        pts = shapely.get_coordinates(geom) - self.c
        return np.stack([pts @ self.u, pts @ self.v], axis=1)

    def polygon(self, x0: float, x1: float, y0: float, y1: float) -> Polygon:
        corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        return Polygon([tuple(self.c + x * self.u + y * self.v) for x, y in corners])


def _to_rect(px, py, x0, x1, y0, y1):
    """Distance from points to an axis-aligned rectangle (0 inside), in the frame's coordinates."""
    dx = np.maximum(np.maximum(x0 - px, px - x1), 0.0)
    dy = np.maximum(np.maximum(y0 - py, py - y1), 0.0)
    return np.hypot(dx, dy)


def _best(grid: _Grid, allowed, dark, hull: np.ndarray, lo: float, hi: float, reach: float):
    """(x0, x1, y0, y1) of the court of sides `lo` to `hi` m standing on allowed cells that lights the
    most dark cells; a court lighting the whole dark part (every corner of its convex `hull`, in the
    frame's coordinates) wins, the smallest first, then the one nearest the dark part's middle. None when
    none fits or none lights anything."""
    g = grid.g
    bad = np.pad(np.cumsum(np.cumsum(~allowed, axis=0), axis=1), ((1, 0), (1, 0)))
    nx, ny = allowed.shape
    a, b = int(math.ceil(lo / g - 1e-6)), int(math.floor(hi / g + 1e-6))
    pairs = [(w, h) for w in range(a, min(b, nx) + 1) for h in range(a, min(b, ny) + 1)]
    middle = hull.mean(axis=0)
    found: dict = {}                      # (w, h) -> its candidates (i0, j0, w, h)
    fits: dict = {}                       # (w, h) -> those lighting the whole dark part
    least = None                          # cells of the smallest of those
    for w, h in sorted(pairs, key=lambda wh: wh[0] * wh[1]):        # smallest first: stop past the first fit
        if least is not None and w * h > least:
            break
        i0, j0 = np.nonzero((bad[w:, h:] - bad[:-w, h:] - bad[w:, :-h] + bad[:-w, :-h]) == 0)
        if not len(i0):
            continue
        found[w, h] = cand = np.stack([i0, j0, np.full(len(i0), w), np.full(len(i0), h)], axis=1)
        x0, x1, y0, y1 = _sides(grid, cand)
        full = (_to_rect(hull[:, :1], hull[:, 1:], x0, x1, y0, y1) <= reach).all(axis=0)   # its hull lit
        if full.any():
            least, fits[w, h] = w * h, cand[full]
    pool = fits if least is not None else found
    cand = [pool[wh] for wh in pairs if wh in pool]
    if not cand:
        return None
    cand = np.concatenate(cand)                                     # in the search order (w, h, then corner)
    x0, x1, y0, y1 = _sides(grid, cand)
    area = (x1 - x0) * (y1 - y0)
    mid = np.hypot((x0 + x1) / 2 - middle[0], (y0 + y1) / 2 - middle[1])
    if least is not None:
        return _pick(np.arange(len(cand)), area, mid, x0, x1, y0, y1)
    px, py = grid.x[dark], grid.y[dark]
    coarse = np.flatnonzero(((cand[:, 2] - a) % 2 == 0) & ((cand[:, 3] - a) % 2 == 0))   # sides every 2 cells
    ii, jj = np.nonzero(dark)
    every = (ii % 2 == 0) & (jj % 2 == 0)                      # ... counted on every other cell
    lit = np.zeros(len(coarse))
    for x, y in zip(px[every], py[every]):
        lit += _to_rect(x, y, x0[coarse], x1[coarse], y0[coarse], y1[coarse]) <= reach
    if not len(lit) or lit.max() <= 0:
        return None
    return _pick(coarse[lit == lit.max()], area, mid, x0, x1, y0, y1)


def _sides(grid: _Grid, cand: np.ndarray) -> tuple:
    """(x0, x1, y0, y1) of candidate courts (first cell i0, j0 and w x h cells) in the frame."""
    g = grid.g
    return (grid.xs[cand[:, 0]] - g / 2, grid.xs[cand[:, 0] + cand[:, 2] - 1] + g / 2,
            grid.ys[cand[:, 1]] - g / 2, grid.ys[cand[:, 1] + cand[:, 3] - 1] + g / 2)


def _pick(idx, area, mid, x0, x1, y0, y1) -> tuple:
    """The smallest of candidates `idx`, then the nearest the dark part's middle, then the first."""
    k = idx[np.lexsort((idx, np.round(mid[idx], 6), np.round(area[idx], 6)))[0]]
    return float(x0[k]), float(x1[k]), float(y0[k]), float(y1[k])


# --- the planning step ------------------------------------------------------------------

def courted(b, district: str, cfg: dict) -> str | None:
    """The court plan building b may get (`[courts.plan]` key), or None: colonial blocks and maisons."""
    if b.kind == "apartments" and district == "colonial":
        return "colonial"
    if b.kind == "house" and district not in ("medina", "village"):
        return "maison"
    return None


def lit_walls(b, k: int, street, fp_tree, clear: float, least: float = 1.5) -> np.ndarray:
    """One bool per wall of `wall_arrays(b.footprint)`: does it hold windows (a street wall, or one facing
    open ground, as the dresser decides; walls under `least` m are counted as holding none)?"""
    p, q, n, length = wall_arrays(b.footprint)
    opened = open_walls(fp_tree, k, p, q, n, length, clear)
    return ((np.asarray(street) >= 0) | opened) & (length > least)


def apply_courts(ctx, plan, kinds: list, street_of_walls) -> None:
    """Cut the courts of every colonial block and maison of a plan (after the rest of its massing).
    `street_of_walls(b)` gives the street in front of each wall of b (-1: none), as the dresser reads it."""
    cfg = ctx.style.get("courts", {})
    if not cfg:
        return
    clear = float(ctx.style.get("dressing", {}).get("open_walls", {}).get("clear", 3.0))
    fp_tree = STRtree([b.footprint for b in plan.buildings]) if plan.buildings else None
    for k, b in enumerate(plan.buildings):
        sort = courted(b, kinds[b.district], cfg)
        if sort is None or b.footprint.interiors:
            continue
        lit = lit_walls(b, k, street_of_walls(b), fp_tree, clear)
        avoid = None
        if b.top and "x" in b.top:                     # a corner dome or turret stands on the roof there
            avoid = Point(b.top["x"], b.top["y"]).buffer(float(b.top["radius"]) + 1.0, 12)
        courts = courts_for(b.footprint, lit, cfg, plan_of(cfg, sort), avoid)
        if not courts and cfg.get("against", {}).get(sort):          # a narrow lot: against a party wall
            faced = lit_walls(b, k, street_of_walls(b), fp_tree, clear, 0.0)   # a short wall may hold a window too
            courts = against_for(b.footprint, lit, cfg, list(cfg["against"][sort]), avoid, faced)
        if courts:
            cut(b, [c for _kind, c in courts])


def cut(b, courts: list) -> bool:
    """Cut `courts` (disjoint, inside) from b's footprint and from its set-back top floor, which keeps them
    open to the sky. The outer ring stays exactly as it was (the street side is dressed as before). Leaves
    b as it was and returns False when a court would not stay a clean hole."""
    rings = [c.exterior.coords for c in courts]
    fp = Polygon(b.footprint.exterior.coords, rings)
    if not fp.is_valid or abs(fp.area - b.footprint.area + sum(c.area for c in courts)) > 1e-6:
        return False
    upper = None
    if b.setback is not None:
        upper = Polygon(b.setback.exterior.coords, rings)
        if not all(b.setback.buffer(-0.5).contains(c) for c in courts) or not upper.is_valid:
            return False
    b.footprint = fp
    if upper is not None:
        b.setback = upper
    return True
