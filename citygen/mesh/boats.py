"""Fishing boats and trawlers of the harbor (prompt 35), as in the ports of Mahdia, Kelibia and Sfax.

Generator axes as in mesh/vehicles.py: the boat's length along x (its bow toward +x), its beam along y,
z up; the origin lies on the waterline under the middle of the boat, so a boat set at z = 0 floats with
its hull dipping below the sea. Every piece fits inside its plan envelope `[port.props] size`
(length, width) and its keel reaches `draft` m down: the harbor planner (city/moorings.py) keeps
boats apart and over deep enough water with the same two numbers.

A hull is a loft of cross sections from stern to bow: a keel, a round bilge and flared topsides
up to a rising sheer line, painted like the wooden boats of the Tunisian coast: antifouling under
the water, white topsides with a colored strake under the gunwale (blue mostly, sometimes green or
red, on the piece's own stream), a trawler with a dark band over its waterline. Each painted band is
one surface with shared vertices and smooth normals; the inside of the bulwark, the gunwale cap and a
deck close the open hull, so its thin shell has real faces on both sides.

The three fishing boats share one double-ended hull with a raked stem (each is scaled to its own size):
- `boat_lateen`: an open boat with a short mast and a lateen yard with its sail furled along it, two
  thwarts and a painted eye on each side of the bow.
- `boat_cabin`: a cabin aft (dark windows) with a mast light on its roof and a net heap on the foredeck.
- `boat_rowing`: a small open boat with thwarts, a pair of oars and a heap of nets.
- `boat_trawler`: a 16 m trawler with a dark hull band, a wheelhouse forward of amidships with a mast
  and its lights, a trawl winch, a stern gantry and a foremast with its booms topped up for port.

Mast lights are `lantern_glow`: they glow at night through the viewer's glow rules.
"""
from __future__ import annotations

import math

import numpy as np
from shapely.geometry import Polygon, box

from ..rng import stream
from .builder import MeshBuilder, triangulate
from .props import _faces, _orient
from .vehicles import _box_faces

KINDS = ("boat_lateen", "boat_cabin", "boat_rowing", "boat_trawler")
FISHING = ("boat_lateen", "boat_cabin", "boat_rowing")   # one hull, three fit-outs
GLOW = "lantern_glow"
TRIM = "TRIM"           # stand-in, renamed to each piece's strake color

# Hull shapes (shares and meters): sheer height at the bow, amidships and the stern, deck height, stern
# kind, stem and stern rake, the colored strake under the gunwale, the dark band (trawler), shell thickness.
_SPECS = {
    "boat_fishing": {"sheer": (1.2, 0.78, 1.0), "deck": 0.32, "stern": "pointed", "rake": (0.5, 0.3),
                     "band": 0.22, "dark": None, "shell": 0.06},
    "boat_trawler": {"sheer": (3.05, 2.05, 2.15), "deck": 1.2, "stern": "transom", "rake": (1.1, 0.0),
                     "band": 0.32, "dark": 0.8, "shell": 0.12},
}
STATIONS = 9


def boat_pieces(seed: int, cfg: dict | None) -> dict:
    """{name: (glTF parts, category, anchor)} of the boats in `[port.props] size`; empty without it.

    The three fishing boats share one hull, like the standard wooden hulls of a Tunisian fleet fitted out
    for different fishing: their hull parts are the same dicts for every material (the strake color only
    renamed), so a tile writes the hull once (`write_glb` reuses the accessors of a part seen before) and
    each fit-out adds only its own parts (its deck among them), in materials the hull does not use. A part
    costs about 0.8 KB of glTF JSON in a tile, so fit-outs use few materials."""
    if not cfg or "size" not in cfg:
        return {}
    out = {}
    if "boat_fishing" in cfg["size"]:
        size = [float(v) for v in cfg["size"]["boat_fishing"]]
        hull = Hull(_SPECS["boat_fishing"], size, float(cfg["draft"]["boat_fishing"]), TRIM)
        mb = MeshBuilder()
        hull.draw(mb, deck=False)
        shared = _plain(mb)
        for name, rig in (("boat_lateen", _lateen), ("boat_cabin", _cabin), ("boat_rowing", _oars)):
            rng = stream(seed, "piece", name)
            trim = _trim(cfg, rng)
            fit = MeshBuilder()
            hull.deck_mesh(fit)                           # the deck joins the fit-out's woodwork: one part fewer
            rig(fit, hull, rng)
            own = _plain(fit)
            parts = {(trim if m == TRIM else m): part for m, part in shared.items()}
            assert not set(own) & set(parts), "a fit-out must not use the hull's materials"
            out[name] = ({**parts, **own}, "boat", "ground")
    if "boat_trawler" in cfg["size"]:
        rng = stream(seed, "piece", "boat_trawler")
        size = [float(v) for v in cfg["size"]["boat_trawler"]]
        hull = Hull(_SPECS["boat_trawler"], size, float(cfg["draft"]["boat_trawler"]), _trim(cfg, rng))
        mb = MeshBuilder()
        hull.draw(mb)
        _trawler(mb, hull, rng)
        out["boat_trawler"] = (_plain(mb), "boat", "ground")
    return out


def _trim(cfg: dict, rng) -> str:
    """The strake color of one boat piece, one draw on its stream."""
    trims = [(str(m), float(w)) for m, w in cfg.get("trims", [["hull_blue", 1.0]])]
    odds = np.cumsum([w for _, w in trims])
    return trims[int(np.searchsorted(odds / odds[-1], rng.random(), side="right"))][0]


def _plain(mb: MeshBuilder) -> dict:
    """glTF parts without UVs: boats are plain palette colors, and a tile pays for every vertex."""
    return {m: {**part, "uv": None} for m, part in mb.gltf_parts().items()}


# --- shared geometry --------------------------------------------------------------------------------

def surface(mb: MeshBuilder, mat: str, grid: np.ndarray, out: np.ndarray) -> None:
    """A surface over a (rows, cols, 3) grid with shared vertices and smooth normals, every face turned
    along `out` (rows, cols, 3: a rough outward direction at each vertex). Degenerate faces are left out."""
    r, c = grid.shape[:2]
    pos = grid.reshape(-1, 3)
    i, j = np.meshgrid(np.arange(r - 1), np.arange(c - 1), indexing="ij")
    v = (i * c + j).ravel()
    idx = np.concatenate([np.stack([v, v + c, v + c + 1], 1), np.stack([v, v + c + 1, v + 1], 1)])
    a, b, cc = pos[idx[:, 0]], pos[idx[:, 1]], pos[idx[:, 2]]
    n = np.cross(b - a, cc - a)
    keep = np.linalg.norm(n, axis=1) > 1e-7
    idx, n = idx[keep], n[keep]
    if not len(idx):
        return
    o = out.reshape(-1, 3)
    back = (n * (o[idx[:, 0]] + o[idx[:, 1]] + o[idx[:, 2]])).sum(axis=1) < 0
    idx[back] = idx[back][:, ::-1]
    n[back] *= -1.0
    acc = np.zeros_like(pos)
    for k in range(3):
        np.add.at(acc, idx[:, k], n)
    length = np.linalg.norm(acc, axis=1)
    nrm = np.where(length[:, None] > 1e-12, acc / np.maximum(length, 1e-12)[:, None], o)
    used = np.unique(idx)                                 # vertices only degenerate faces touched are dropped
    remap = np.full(len(pos), -1)
    remap[used] = np.arange(len(used))
    mb.add(mat, pos[used], nrm[used], pos[used][:, :2], remap[idx])


def prisms(mb: MeshBuilder, mat: str, a, b, radius, sides: int = 3) -> None:
    """Thin members (ropes, poles, lattice bars) from points a to b: `sides`-sided prisms with radial
    normals and shared vertices, no end caps (too small to see)."""
    a, b = np.atleast_2d(np.asarray(a, dtype=np.float64)), np.atleast_2d(np.asarray(b, dtype=np.float64))
    r = np.broadcast_to(np.asarray(radius, dtype=np.float64), (len(a),))
    d = b - a
    d /= np.maximum(np.linalg.norm(d, axis=1), 1e-9)[:, None]
    ref = np.where((np.abs(d[:, 2]) > 0.9)[:, None], [1.0, 0.0, 0.0], [0.0, 0.0, 1.0])
    e1 = np.cross(d, ref)
    e1 /= np.linalg.norm(e1, axis=1)[:, None]
    e2 = np.cross(d, e1)
    t = np.arange(sides) * 2 * math.pi / sides
    radial = np.cos(t)[None, :, None] * e1[:, None, :] + np.sin(t)[None, :, None] * e2[:, None, :]  # (n, s, 3)
    ring = radial * r[:, None, None]
    pos = np.concatenate([a[:, None, :] + ring, b[:, None, :] + ring], axis=1)               # (n, 2s, 3)
    nrm = np.concatenate([radial, radial], axis=1)
    k = np.arange(sides)
    k1 = (k + 1) % sides
    quad = np.stack([np.stack([k, k1, k1 + sides], 1), np.stack([k, k1 + sides, k + sides], 1)], 1).reshape(-1, 3)
    p = pos[0]
    nn = np.cross(p[quad[:, 1]] - p[quad[:, 0]], p[quad[:, 2]] - p[quad[:, 0]])
    if (nn * nrm[0][quad[:, 0]]).sum() < 0:               # every member is built the same way round
        quad = quad[:, ::-1]
    idx = (np.arange(len(a)) * 2 * sides)[:, None, None] + quad[None]
    mb.add(mat, pos.reshape(-1, 3), nrm.reshape(-1, 3), pos.reshape(-1, 3)[:, :2], idx.reshape(-1, 3))


def flat(mb: MeshBuilder, mat: str, pts, plane: str, at: float, facing: float) -> None:
    """A flat polygon (2D points) in the plane x = at ("yz"), y = at ("xz") or z = at ("xy"), shared
    vertices, its normal along +axis (facing 1) or -axis (facing -1)."""
    tri = triangulate(Polygon(pts).buffer(0))
    if not len(tri):
        return
    flat2 = tri.reshape(-1, 2)
    uniq, inv = np.unique(np.round(flat2, 6), axis=0, return_inverse=True)
    axis = {"yz": 0, "xz": 1, "xy": 2}[plane]
    others = [k for k in range(3) if k != axis]
    pos = np.zeros((len(uniq), 3))
    pos[:, axis] = at
    pos[:, others[0]], pos[:, others[1]] = uniq[:, 0], uniq[:, 1]
    idx = inv.reshape(-1, 3)
    n = np.cross(pos[idx[0, 1]] - pos[idx[0, 0]], pos[idx[0, 2]] - pos[idx[0, 0]])
    if n[axis] * facing < 0:
        idx = idx[:, ::-1]
    nrm = np.zeros_like(pos)
    nrm[:, axis] = facing
    mb.add(mat, pos, nrm, uniq, idx)


def boxes(mb: MeshBuilder, mat: str, *spans) -> None:
    """Boxes without a bottom, each (x0, x1, y0, y1, z0, z1)."""
    _faces(mb, [q for s in spans for q in _box_faces(*s)], mat)


def light(mb: MeshBuilder, x: float, y: float, z: float, r: float) -> None:
    """A small glowing lamp (`lantern_glow`): an octahedron of six shared vertices centered on (x, y, z)."""
    pos = np.array([(r, 0, 0), (0, r, 0), (-r, 0, 0), (0, -r, 0), (0, 0, 1.4 * r), (0, 0, -1.4 * r)], dtype=np.float64)
    idx = np.array([(0, 1, 4), (1, 2, 4), (2, 3, 4), (3, 0, 4), (1, 0, 5), (2, 1, 5), (3, 2, 5), (0, 3, 5)])
    nrm = pos / np.linalg.norm(pos, axis=1)[:, None]
    mb.add(GLOW, pos + np.array([x, y, z]), nrm, pos[:, :2], idx)


def heap(mb: MeshBuilder, mat: str, cx: float, cy: float, z: float, rx: float, ry: float, h: float) -> None:
    """A low lumpy mound (nets, a tarpaulin): an 8-sided squashed dome of shared vertices."""
    t = np.arange(8) * math.pi / 4 + math.pi / 8
    rings = [(1.0, 0.0), (0.82, 0.55), (0.4, 0.92)]
    grid = np.array([[(cx + rx * f * math.cos(a) * (1.0 + 0.08 * math.sin(3 * a)), cy + ry * f * math.sin(a),
                       z + h * g) for a in np.append(t, t[0])] for f, g in rings])
    out = grid - np.array([cx, cy, z - h])
    surface(mb, mat, grid, out)
    top = grid[-1, :-1]
    flat(mb, mat, top[:, :2], "xy", z + h * rings[-1][1], 1.0)


# --- the hull -------------------------------------------------------------------------------------

class Hull:
    """The hull's lines: stations from stern to bow with half-breadth, sheer and keel."""

    def __init__(self, spec: dict, size: list, draft: float, trim: str):
        self.spec, self.trim = spec, trim
        rb, rs = spec["rake"]
        self.length = size[0] - rb - rs - 0.1
        self.shift = (rs - rb) / 2.0                       # stations shifted so stem and stern fit the envelope
        self.beam = size[1] - 0.1
        self.draft, self.deck, self.shell = draft, spec["deck"], spec["shell"]
        self.t = np.linspace(-1.0, 1.0, STATIONS)
        self.x = self.t * self.length / 2 + self.shift
        bow, mid, stern = spec["sheer"]
        t = self.t
        self.half = self.beam / 2 * np.where(t >= 0, 1.0 - np.abs(t) ** 2.2,
                                             1.0 - 0.42 * t ** 2 if spec["stern"] == "transom" else 1.0 - np.abs(t) ** 2.6)
        self.sheer = mid + np.where(t >= 0, (bow - mid), (stern - mid)) * t ** 2
        self.keel = -draft * (1.0 - 0.3 * t ** 2)

    def at(self, x: float) -> tuple:
        """(half-breadth at deck height, sheer) at x, interpolated between stations."""
        return float(np.interp(x, self.x, self.half)) * 0.95, float(np.interp(x, self.x, self.sheer))

    def _rake(self, z: np.ndarray, i: int) -> np.ndarray:
        """Stem and stern rake: x pushed out with height near the ends."""
        rb, rs = self.spec["rake"]
        t = self.t[i]
        frac = (z - self.keel[i]) / max(self.sheer[i] - self.keel[i], 1e-9)
        return self.x[i] + rb * max(t, 0.0) ** 5 * frac - rs * max(-t, 0.0) ** 5 * frac

    def _section(self, i: int) -> tuple:
        """One side's section points [(y, z)] from the keel up and the material of each band."""
        hb, zs, zk = self.half[i], self.sheer[i], self.keel[i]
        band = self.spec["band"]
        pts = [(0.0, zk), (0.94 * hb, 0.0)]                  # under the water: keel to waterline, one band
        mats = ["hull_antifoul"]
        if self.spec["dark"] is not None:
            pts.append((0.965 * hb, self.spec["dark"]))
            mats.append("hull_dark")
        pts += [(0.985 * hb, zs - band), (hb, zs)]
        mats += ["hull_white", self.trim]
        return pts, mats

    def draw(self, mb: MeshBuilder, deck: bool = True) -> None:
        secs = [self._section(i) for i in range(STATIONS)]
        mats = secs[0][1]
        runs, start = [], 0
        for k in range(1, len(mats) + 1):                  # columns of each painted band
            if k == len(mats) or mats[k] != mats[start]:
                runs.append((mats[start], start, k))
                start = k
        for side in (1.0, -1.0):
            pts = np.array([[(self._rake(np.array([z]), i)[0], side * y, z) for y, z in secs[i][0]]
                            for i in range(STATIONS)])
            zc = (self.sheer + self.keel)[:, None] / 2
            out = np.stack([np.zeros(pts.shape[:2]), pts[:, :, 1], pts[:, :, 2] - zc], axis=2)
            for mat, a, b in runs:
                surface(mb, mat, pts[:, a:b + 1], out[:, a:b + 1])
            self._inside(mb, side, pts[:, -1])
        if deck:
            self.deck_mesh(mb)
        if self.spec["stern"] == "transom":
            self._transom(mb, secs[0][0])

    def _inner(self) -> tuple:
        """Inner top of the bulwark and the deck edge, half-breadths per station."""
        top = np.maximum(self.half - self.shell, 0.0)
        edge = np.maximum(self.half * 0.95 - self.shell, 0.0)
        return top, edge

    def _inside(self, mb: MeshBuilder, side: float, sheer_pts: np.ndarray) -> None:
        """The bulwark's inner face down to the deck and the gunwale cap over the shell."""
        top, edge = self._inner()
        xs = sheer_pts[:, 0]
        inner_top = np.stack([xs, side * top, self.sheer - 0.015], axis=1)
        deck = np.stack([xs, side * edge, np.full(STATIONS, self.deck)], axis=1)
        grid = np.stack([inner_top, deck], axis=1)
        out = np.zeros_like(grid)
        out[:, :, 1] = -side
        surface(mb, "hull_white", grid, out)
        cap = np.stack([sheer_pts, inner_top], axis=1)
        up = np.zeros_like(cap)
        up[:, :, 2] = 1.0
        surface(mb, self.trim, cap, up)

    def deck_mesh(self, mb: MeshBuilder) -> None:
        _, edge = self._inner()
        keep = edge > 0.02
        xs = self.x[keep]
        pts = list(zip(xs, edge[keep])) + list(zip(xs[::-1], -edge[keep][::-1]))
        flat(mb, "deck_wood", pts, "xy", self.deck, 1.0)

    def _transom(self, mb: MeshBuilder, sec: list) -> None:
        """The flat stern: antifouling under the water, the strake color above; its inside above the deck."""
        x0 = self.x[0]
        ring = [(y, z) for y, z in sec] + [(-y, z) for y, z in sec[::-1]]
        poly = Polygon(ring).buffer(0)
        lo, hi = poly.intersection(box(-9, -9, 9, 0.0)), poly.intersection(box(-9, 0.0, 9, 9))
        for part, mat in ((lo, "hull_antifoul"), (hi, self.trim)):
            for g in getattr(part, "geoms", [part]):
                if g.geom_type == "Polygon" and g.area > 1e-4:
                    flat(mb, mat, list(g.exterior.coords)[:-1], "yz", x0, -1.0)
        top, edge = self._inner()
        inner = [(edge[0], self.deck), (top[0], self.sheer[0] - 0.015), (-top[0], self.sheer[0] - 0.015),
                 (-edge[0], self.deck)]
        flat(mb, "hull_white", inner, "yz", x0 + self.shell, 1.0)


# --- rigs and fittings -----------------------------------------------------------------------------

def _thwarts(mb: MeshBuilder, hull: Hull, shares) -> None:
    """Seats across the boat at these shares of its length from the middle (wood)."""
    spans = []
    for s in shares:
        x = hull.shift + s * hull.length / 2
        hb, zs = hull.at(x)
        w = max(hb - hull.shell, 0.1)
        spans.append((x - 0.11, x + 0.11, -w, w, zs - 0.3, zs - 0.25))
    boxes(mb, "deck_wood", *spans)


def _eyes(mb: MeshBuilder, hull: Hull) -> None:
    """The painted eye on each side of the bow: a black almond on the white planking, just off it."""
    x = hull.shift + 0.78 * hull.length / 2
    i = int(np.searchsorted(hull.x, x))
    hb, zs = float(np.interp(x, hull.x, hull.half)), float(np.interp(x, hull.x, hull.sheer))
    z = zs - hull.spec["band"] - 0.12
    slope = (hull.half[i] - hull.half[i - 1]) / (hull.x[i] - hull.x[i - 1])
    for side in (1.0, -1.0):
        for mat, r, lift in (("paint_black", 0.2, 0.012),):
            y = side * (hb + lift)
            pts = [(x - r, z), (x, z + r * 0.45), (x + r, z), (x, z - r * 0.45)]
            q = [(px, y + side * (px - x) * slope, pz) for px, pz in pts]
            _faces(mb, _orient([q], (0.0, side, 0.0)), mat)


def _lateen(mb: MeshBuilder, hull: Hull, rng) -> None:
    """Short mast forward, a lateen yard slung from its head with the sail furled along it, two thwarts."""
    _thwarts(mb, hull, (-0.35, 0.12))
    xm = hull.shift + 0.3 * hull.length / 2
    lo = np.array([hull.x[-1] - 0.35, 0.0, hull.sheer[-1] + 0.15])     # the yard's foot at the stem head
    hi = np.array([hull.x[0] + 0.6, 0.0, 3.9 + 0.3 * rng.random()])     # its peak high over the stern
    u = (lo[0] - xm) / (lo[0] - hi[0])
    head = lo + (hi - lo) * u
    prisms(mb, "deck_wood", [(xm, 0.0, hull.deck)], [head + [0.0, 0.0, 0.12]], 0.07, 5)
    prisms(mb, "deck_wood", [lo], [hi], 0.045, 4)
    furl0, furl1 = lo + (hi - lo) * 0.08, lo + (hi - lo) * 0.92
    prisms(mb, "awning_cream", [furl0 + [0, 0, -0.06]], [furl1 + [0, 0, -0.06]], 0.13, 5)
    _eyes(mb, hull)


def _cabin(mb: MeshBuilder, hull: Hull, rng) -> None:
    """A small cabin aft with dark windows and a mast light on its roof, a net heap on the foredeck."""
    x0, x1 = hull.shift - 0.62 * hull.length / 2, hull.shift - 0.05 * hull.length / 2
    w = hull.at((x0 + x1) / 2)[0] * 0.62
    z0, z1 = hull.deck, hull.deck + 1.45
    boxes(mb, "cabin_white", (x0, x1, -w, w, z0, z1))
    boxes(mb, "cabin_white", (x0 - 0.06, x1 + 0.08, -w - 0.06, w + 0.06, z1, z1 + 0.08))
    zw0, zw1 = z1 - 0.62, z1 - 0.22
    glass = [[(x1 + 0.006, -w + 0.12, zw0), (x1 + 0.006, w - 0.12, zw0), (x1 + 0.006, w - 0.12, zw1),
              (x1 + 0.006, -w + 0.12, zw1)]]
    for side in (1.0, -1.0):
        y = side * (w + 0.006)
        glass += _orient([[(x1 - 0.2, y, zw0), (x1 - 0.75, y, zw0), (x1 - 0.75, y, zw1), (x1 - 0.2, y, zw1)]],
                         (0.0, side, 0.0))
    _faces(mb, _orient(glass[:1], (1.0, 0.0, 0.0)) + glass[1:], "glass_dark")
    xm = (x0 + x1) / 2
    from_roof = z1 + 0.08
    prisms(mb, "deck_wood", [(xm, 0.0, from_roof)], [(xm, 0.0, from_roof + 1.4)], 0.035, 4)
    light(mb, xm, 0.0, from_roof + 1.5, 0.07)
    _thwarts(mb, hull, (0.3,))
    xn = hull.shift + 0.45 * hull.length / 2
    heap(mb, "net_green" if rng.random() < 0.5 else "net_orange", xn, 0.0, hull.deck,
         hull.at(xn)[0] * 0.7, hull.at(xn)[0] * 0.55, 0.35)


def _oars(mb: MeshBuilder, hull: Hull, rng) -> None:
    """Thwarts, a pair of oars lying fore and aft on them and a heap of nets in the stern."""
    _thwarts(mb, hull, (-0.15, 0.3))
    hb, zs = hull.at(hull.shift)
    z = zs - 0.22
    for side in (1.0, -1.0):
        y = side * hb * 0.45
        a = (hull.shift - 0.42 * hull.length / 2, y, z)
        b = (hull.shift + 0.5 * hull.length / 2, y * 0.7, z + 0.04)
        prisms(mb, "deck_wood", [a], [b], 0.03, 4)
        boxes(mb, "deck_wood", (a[0] - 0.05, a[0] + 0.55, y - 0.07, y + 0.07, z - 0.015, z + 0.015))   # blade
    xn = hull.shift - 0.55 * hull.length / 2
    heap(mb, "net_orange" if rng.random() < 0.6 else "net_green", xn, 0.0, hull.deck,
         hull.at(xn)[0] * 0.8, hull.at(xn)[0] * 0.6, 0.3)


def _trawler(mb: MeshBuilder, hull: Hull, rng) -> None:
    """Wheelhouse with a window band and a mast, winch, stern gantry and a foremast with topped booms."""
    L, B, deck = hull.length, hull.beam, hull.deck
    x0, x1 = hull.shift + 0.02 * L, hull.shift + 0.22 * L
    w = B * 0.31
    z1 = deck + 2.55
    boxes(mb, "hull_white", (x0, x1, -w, w, deck, z1))
    boxes(mb, hull.trim, (x0 - 0.1, x1 + 0.18, -w - 0.12, w + 0.12, z1, z1 + 0.12))
    zw0, zw1 = z1 - 1.0, z1 - 0.35
    e = 0.008
    glass = [[(x1 + e, -w + 0.15, zw0), (x1 + e, w - 0.15, zw0), (x1 + e, w - 0.15, zw1), (x1 + e, -w + 0.15, zw1)],
             [(x0 - e, w - 0.3, zw0), (x0 - e, -w + 0.3, zw0), (x0 - e, -w + 0.3, zw1), (x0 - e, w - 0.3, zw1)]]
    for side in (1.0, -1.0):
        y = side * (w + e)
        glass += _orient([[(x1 - 0.2, y, zw0), (x0 + 0.25, y, zw0), (x0 + 0.25, y, zw1), (x1 - 0.2, y, zw1)]],
                         (0.0, side, 0.0))
    _faces(mb, _orient(glass[:1], (1.0, 0.0, 0.0)) + _orient(glass[1:2], (-1.0, 0.0, 0.0)) + glass[2:], "glass_dark")
    xm = (x0 + x1) / 2 - 0.3
    top = z1 + 0.12
    prisms(mb, "hull_white", [(xm, 0.0, top)], [(xm, 0.0, top + 4.2)], 0.09, 6)
    prisms(mb, "steel_rust", [(xm, -1.1, top + 3.0)], [(xm, 1.1, top + 3.0)], 0.04, 4)    # crosstree
    boxes(mb, "hull_white", (xm + 0.25, xm + 1.05, -0.25, 0.25, top, top + 0.35))              # radar box
    light(mb, xm, 0.0, top + 4.35, 0.1)
    for side in (1.0, -1.0):
        light(mb, xm, side * 1.1, top + 3.1, 0.06)
    xw = x0 - 1.2                                         # trawl winch: two drums across the deck
    for side in (1.0, -1.0):
        ring = np.array([(xw, side * 0.35, deck + 0.55)])
        prisms(mb, "steel_rust", ring, ring + [0.0, side * 0.9, 0.0], 0.42, 8)
    boxes(mb, "steel_rust", (xw - 0.35, xw + 0.35, -0.35, 0.35, deck, deck + 0.9))
    xg = hull.x[0] + 0.45                                 # the stern gantry
    hb = float(hull.half[0]) - 0.3
    zg = deck + 4.6
    prisms(mb, "crane_paint", [(xg, hb, deck), (xg, -hb, deck)], [(xg + 0.4, hb * 0.9, zg), (xg + 0.4, -hb * 0.9, zg)],
           0.14, 4)
    prisms(mb, "crane_paint", [(xg + 0.4, hb * 0.9 + 0.1, zg)], [(xg + 0.4, -hb * 0.9 - 0.1, zg)], 0.16, 4)
    for side in (1.0, -1.0):                             # trawl blocks hanging from it
        boxes(mb, "steel_rust", (xg + 0.25, xg + 0.55, side * hb * 0.6 - 0.15, side * hb * 0.6 + 0.15, zg - 0.7, zg - 0.15))
    xf = hull.shift + 0.6 * L / 2                         # foremast with its booms topped up
    zf = deck + 6.2
    prisms(mb, "hull_white", [(xf, 0.0, deck)], [(xf, 0.0, zf)], 0.1, 6)
    for side in (1.0, -1.0):
        prisms(mb, "crane_paint", [(xf, side * 0.15, deck + 1.6)], [(xf - 0.6, side * (B / 2 - 0.25), zf - 0.6)], 0.07, 4)
    xn = hull.shift - 0.3 * L
    heap(mb, "net_green", xn, 0.0, deck, 1.9, hull.at(xn)[0] * 0.6, 0.55)
