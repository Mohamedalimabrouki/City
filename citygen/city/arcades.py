"""Colonial arcades (prompt 22): where the bays of a ground-floor arcade stand along a facade.

Pure geometry, no random draws. `Dresser._arcades` (city/dressing.py) decides which walls of a colonial
building carry an arcade (by the street in front of each wall), finds the stretch of each wall the
arcade may cover, lays the bays out around the doors, shop fronts and cafe tables the old rules placed,
and draws them as `arcade_bay` pieces stretched along the wall. Positions along a wall are `s`, in
meters from its first corner; `zones` are spans of `s` where no bay edge (pillar) may stand.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import shapely


@dataclass
class Run:
    """One continuous arcade along wall `wall`, from s0 to s1."""
    wall: int
    s0: float
    s1: float
    fix0: bool = False          # the arcade goes on past s0 (a corner, a bend, the next building's arcade)
    fix1: bool = False          # ... past s1
    cuts: np.ndarray | None = None                       # bay edges along the wall, s0 ... s1
    z: np.ndarray = field(default_factory=lambda: np.zeros(0))   # each bay's street level (its anchor)

    @property
    def keep(self) -> str:
        """The ends that must stay where they are: both | s0 | s1 | none."""
        return {(True, True): "both", (True, False): "s0", (False, True): "s1", (False, False): "none"}[(self.fix0, self.fix1)]


def band(a, u, n, s0: float, s1: float, y0: float, y1: float):
    """The plan rectangle in front of a wall from s0 to s1, y0 to y1 out of it."""
    return shapely.polygons([a + u * s0 + n * y0, a + u * s1 + n * y0, a + u * s1 + n * y1, a + u * s0 + n * y1])


def spans_of(polys, a, u) -> np.ndarray:
    """(N, 2) extent along the wall (a, u) of each polygon."""
    out = np.zeros((len(polys), 2))
    for m, g in enumerate(polys):
        s = (shapely.get_coordinates(g) - a) @ u
        out[m] = (s.min(), s.max()) if len(s) else (np.inf, -np.inf)
    return out


def free_spans(lo: float, hi: float, blocked: list) -> list:
    """Parts of [lo, hi] outside every blocked (start, end, tag): (start, end, tag before, tag after);
    a tag is None where the span reaches lo or hi itself."""
    out, at, tag = [], lo, None
    for b0, b1, t in sorted(blocked, key=lambda x: (x[0], x[1])):
        if b1 <= at:
            continue
        if b0 > at:
            out.append((at, min(b0, hi), tag, t if b0 < hi else None))
        if b1 > at:
            at, tag = b1, t
        if at >= hi:
            break
    if at < hi:
        out.append((at, hi, tag, None))
    return out


def even_cuts(s0: float, s1: float, bay) -> np.ndarray | None:
    """Edges of equal bays from s0 to s1 with widths within `bay` (min, max, nominal); None if no count fits."""
    length = s1 - s0
    lo, hi, nominal = bay
    counts = [c for c in range(max(1, math.ceil(length / hi - 1e-9)), int(length / lo + 1e-9) + 1)]
    if not counts or length <= 0:
        return None
    c = min(counts, key=lambda c: (abs(length / c - nominal), c))
    return np.linspace(s0, s1, c + 1)


def flex_cuts(s0: float, s1: float, zones: list, bay, step: float = 0.05) -> np.ndarray | None:
    """Bay edges from s0 to s1 with no edge inside a zone, widths within `bay` (min, max, nominal), as
    close to the nominal width as they can be (least squares, on a grid of about `step` m); None if
    impossible. Without zones the bays are equal."""
    zones = [(z0, z1) for z0, z1 in zones if z1 > s0 and z0 < s1]
    if not zones:
        return even_cuts(s0, s1, bay)
    length = s1 - s0
    k_all = max(1, int(round(length / step)))
    h = length / k_all
    grid = s0 + np.arange(k_all + 1) * h
    bad = np.zeros(k_all + 1, dtype=bool)
    for z0, z1 in zones:
        bad |= (grid > z0) & (grid < z1)
    if bad[0] or bad[-1]:
        return None
    lo, hi, nominal = bay
    w0, w1 = max(1, math.ceil(lo / h - 1e-9)), int(hi / h + 1e-9)
    if w1 < w0:
        return None
    widths = np.arange(w0, w1 + 1)
    cost = (widths * h - nominal) ** 2
    best = np.full(k_all + 1, np.inf)
    back = np.zeros(k_all + 1, dtype=np.int64)
    best[0] = 0.0
    for k in range(w0, k_all + 1):
        if bad[k]:
            continue
        prev = k - widths
        ok = prev >= 0
        if not ok.any():
            continue
        tot = np.where(ok, best[np.maximum(prev, 0)] + cost, np.inf)
        m = int(np.argmin(tot))
        best[k], back[k] = tot[m], prev[m]
    if not np.isfinite(best[k_all]):
        return None
    edges, k = [k_all], k_all
    while k > 0:
        k = int(back[k])
        edges.append(k)
    return grid[np.array(edges[::-1])]


def layout(run: Run, zones: list, bays: list, shrink: float = 3.0, step: float = 0.25) -> np.ndarray | None:
    """Bay edges for a run: the whole run with each width range in `bays` (strict first, then relaxed);
    else the run shortened at its free end(s) a step at a time, at most `shrink` m, so its fixed end
    keeps meeting the corner or the next building (when both ends are fixed, one of them gives way,
    s1 first). None when nothing fits."""
    for bay in bays:
        cuts = flex_cuts(run.s0, run.s1, zones, bay)
        if cuts is not None:
            return cuts
    a, b = run.s0, run.s1
    for cut in np.arange(step, shrink + 1e-9, step):
        tries = {"s0": [(a, b - cut)], "s1": [(a + cut, b)], "both": [(a, b - cut), (a + cut, b)],
                 "none": [(a + cut / 2, b - cut / 2), (a, b - cut), (a + cut, b)]}[run.keep]
        for s0, s1 in tries:
            if s1 - s0 < bays[-1][0]:
                return None
            cuts = flex_cuts(s0, s1, zones, bays[-1])
            if cuts is not None:
                return cuts
    return None


def level_steps(z: np.ndarray, step: float) -> np.ndarray:
    """Street levels of consecutive bays made level in groups: a group grows while its sidewalk rises
    or falls less than `step`, and stands at its lowest point (so no pillar foot floats)."""
    out = np.array(z, dtype=np.float64)
    start, lo, hi = 0, np.inf, -np.inf
    for i, v in enumerate(z):
        if max(hi, v) - min(lo, v) > step:
            out[start:i] = lo
            start, lo, hi = i, v, v
        else:
            lo, hi = min(lo, v), max(hi, v)
    out[start:] = lo
    return out


def turn(u0, u1) -> float:
    """Degrees the ring turns from one wall to the next (positive: a convex corner of a counter-clockwise ring)."""
    return math.degrees(math.atan2(u0[0] * u1[1] - u0[1] * u1[0], float(np.dot(u0, u1))))
