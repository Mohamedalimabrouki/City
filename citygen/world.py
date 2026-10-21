"""The country: terrain, settlements and the roads that join them.

Everything here is coarse (hundreds of meters per cell) and computed for the
whole country at once, which takes seconds. Detailed city plans and 3D tiles
are built later, only where they are needed.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from scipy import ndimage
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from shapely.geometry import LineString

from .config import load_style
from .names import NameMaker
from .rng import stream
from .terrain import BIOME_NAMES, Terrain, classify

KINDS = ["capital", "city", "town", "village"]
RANK = {k: i for i, k in enumerate(KINDS)}
ROAD_WIDTH = {"national": 11.0, "regional": 8.0, "local": 6.0}


@dataclass
class Settlement:
    id: int
    name: str
    kind: str
    x: float
    y: float
    population: int
    radius: float
    elevation: float
    coastal: bool
    biome: str
    known_for: list = field(default_factory=list)
    founded: str = ""

    def to_json(self) -> dict:
        return {"id": self.id, "name": self.name, "kind": self.kind,
                "x": round(self.x, 1), "y": round(self.y, 1), "population": self.population,
                "radius": round(self.radius, 1), "elevation": round(self.elevation, 1),
                "coastal": self.coastal, "biome": self.biome,
                "known_for": self.known_for, "founded": self.founded}


@dataclass
class Road:
    id: int
    kind: str          # national | regional | local
    width: float
    coords: np.ndarray  # (N, 2) meters
    ends: tuple         # settlement ids at each end, or None

    def to_json(self) -> dict:
        return {"id": self.id, "kind": self.kind, "width": self.width,
                "ends": list(self.ends), "coords": np.round(self.coords, 1).tolist()}


@dataclass
class World:
    seed: int
    cfg: dict
    style: dict
    name: str
    terrain: Terrain
    settlements: list
    roads: list

    @property
    def size(self) -> float:
        return self.terrain.size

    def capital(self) -> Settlement:
        return next(s for s in self.settlements if s.kind == "capital")

    def find(self, key: str) -> Settlement:
        """Settlement by "capital", id number, or name (case-insensitive)."""
        key = str(key).strip()
        if key.lower() == "capital":
            return self.capital()
        if key.isdigit():
            return self.settlements[int(key)]
        for s in self.settlements:
            if s.name.lower() == key.lower():
                return s
        raise KeyError(f"no settlement called {key!r}; try `python -m citygen list`")

    def to_json(self) -> dict:
        return {"format": "citygen-world/1", "seed": self.seed, "name": self.name,
                "style": self.cfg["world"]["style"], "size": self.size,
                "sea_direction": [round(v, 4) for v in self.terrain.sea_dir],
                "settlements": [s.to_json() for s in self.settlements],
                "roads": [r.to_json() for r in self.roads]}


def generate_world(cfg: dict) -> World:
    seed = int(cfg["world"]["seed"])
    style = load_style(cfg["world"]["style"])
    terrain = Terrain(seed, cfg)
    settlements = _place_settlements(seed, cfg, style, terrain)
    namer = NameMaker(style, stream(seed, "names"))
    name = cfg["world"].get("name") or namer.country()
    for s in settlements:
        s.name = namer.settlement(s.kind)
    canon = cfg.get("canon", {}).get("names", {})
    for sid, new_name in canon.items():
        if int(sid) < len(settlements):
            settlements[int(sid)].name = str(new_name)
    _add_lore(seed, style, settlements)
    roads = _build_roads(seed, cfg, terrain, settlements)
    return World(seed, cfg, style, name, terrain, settlements, roads)


# --- settlements ----------------------------------------------------------------

def _place_settlements(seed: int, cfg: dict, style: dict, terrain: Terrain) -> list:
    size = terrain.size
    sc = cfg["settlements"]
    n = max(8, int(size // 400))
    cell = size / n
    c = (np.arange(n) + 0.5) * cell
    X, Y = np.meshgrid(c, c)
    H = terrain.height(X, Y)
    gy, gx = np.gradient(H, cell)
    slope = np.hypot(gx, gy)
    M = terrain.moisture(X, Y, H)
    land = H > 2.0
    if land.all():
        coast_d = np.full(H.shape, size)
    else:
        coast_d = ndimage.distance_transform_edt(land) * cell
    margin = 0.05 * size
    ok = land & (slope < 0.12) & (H < 1050) & (X > margin) & (X < size - margin)
    ok &= (Y > margin) & (Y < size - margin)

    rng = stream(seed, "settlements")
    jitter = rng.uniform(-0.45, 0.45, size=(2, n, n)) * cell
    PX, PY = X + jitter[0], Y + jitter[1]
    base = 1.0 + 0.5 * M - H / 2600.0 - slope * 3.5 + 0.45 * np.exp(-coast_d / 2500.0)
    central = 1.0 - np.hypot(X - size / 2, Y - size / 2) / (0.75 * size)
    area_k = (size / 1000.0) ** 2 / 1000.0
    counts = {"capital": 1,
              "city": round(area_k * sc["cities_per_1000_km2"]),
              "town": round(area_k * sc["towns_per_1000_km2"]),
              "village": round(area_k * sc["villages_per_1000_km2"])}
    spacing = {"capital": sc["city_spacing"], "city": sc["city_spacing"],
               "town": sc["town_spacing"], "village": sc["village_spacing"]}

    placed: list[Settlement] = []
    taken = np.zeros((0, 4))  # x, y, radius, rank of placed settlements
    for kind in KINDS:
        kc = style["settlement"][kind]
        score = base + rng.uniform(0.0, 0.1 if kind == "capital" else 0.7, size=H.shape)
        if kind == "capital":
            # near the sea, but far enough back to leave room for a port quarter
            lo, hi = kc["population"]
            typical = math.sqrt(math.sqrt(lo * hi) * sc["population_scale"] / kc["density"] / math.pi) * 1000.0
            ideal = 0.3 * typical
            score = score + 1.6 * np.exp(-((coast_d - ideal) / (0.5 * ideal + 400.0)) ** 2) + 0.8 * central
        elif kind == "city":
            score = score + 0.7 * np.exp(-coast_d / 3000.0)
        # weighted random order (better spots tend to come first, but not always),
        # so small places also appear inland instead of filling the coast only
        sharp = {"capital": 14.0, "city": 5.0, "town": 3.0, "village": 2.2}[kind]
        weight = np.where(ok, np.exp(sharp * (score - score[ok].max())), 0.0) if ok.any() else np.zeros_like(score)
        keys = np.log(rng.random(score.shape)) / np.maximum(weight, 1e-300)
        got = 0
        for flat in np.argsort(-keys, axis=None):
            if got >= counts[kind] or weight.flat[flat] <= 0.0:
                break
            x, y = float(PX.flat[flat]), float(PY.flat[flat])
            lo, hi = kc["population"]
            pop = int(math.exp(rng.uniform(math.log(lo), math.log(hi))) * sc["population_scale"])
            radius = math.sqrt(pop / kc["density"] / math.pi) * 1000.0
            if _conflicts(x, y, radius, RANK[kind], taken, spacing[kind]):
                continue
            h = float(terrain.height(x, y))
            if h < 2.0:
                continue
            placed.append(Settlement(len(placed), "", kind, x, y, pop, radius, h,
                                     bool(coast_d.flat[flat] < radius + 900.0), ""))
            taken = np.vstack([taken, [x, y, radius, RANK[kind]]])
            got += 1
    for s in placed:
        h = terrain.height(s.x, s.y)
        b = classify(np.array([h]), terrain.slope(np.array([s.x]), np.array([s.y])),
                     terrain.moisture(np.array([s.x]), np.array([s.y])))
        s.biome = BIOME_NAMES[int(b[0])]
    return placed


def _conflicts(x, y, radius, rank, taken: np.ndarray, spacing) -> bool:
    if not len(taken):
        return False
    d = np.hypot(taken[:, 0] - x, taken[:, 1] - y)
    if np.any(d < taken[:, 2] + radius + 400.0):
        return True
    return bool(np.any((taken[:, 3] <= rank) & (d < spacing)))


def _add_lore(seed: int, style: dict, settlements: list) -> None:
    lore = style.get("lore", {})
    eras = lore.get("eras", [])
    products = lore.get("products", {})
    rng = stream(seed, "lore")
    for s in settlements:
        pool = []
        if s.coastal:
            pool += products.get("coast", [])
        biome_key = {"green": "green", "forest": "green", "steppe": "steppe",
                     "desert": "desert", "rock": "mountain"}.get(s.biome, "steppe")
        pool += products.get(biome_key, [])
        if s.elevation > 450:
            pool += products.get("mountain", [])
        if pool:
            k = min(len(pool), 1 + int(rng.integers(2)))
            s.known_for = [str(v) for v in rng.choice(pool, size=k, replace=False)]
        if eras:
            # big places tend to be old
            weights = np.linspace(1.0, 0.4, len(eras)) if RANK[s.kind] < 2 else np.ones(len(eras))
            s.founded = str(eras[int(rng.choice(len(eras), p=weights / weights.sum()))])


# --- roads -------------------------------------------------------------------------

class _Router:
    """Least-cost routes over a terrain grid: roads avoid water, steep slopes and peaks."""

    def __init__(self, terrain: Terrain, cell: float):
        size = terrain.size
        self.n = n = max(8, int(math.ceil(size / cell)))
        self.cell = size / n
        c = (np.arange(n) + 0.5) * self.cell
        self.X, self.Y = np.meshgrid(c, c)
        self.H = terrain.height(self.X, self.Y)
        self.water = (self.H < 1.0).ravel()
        self.mult = np.ones(n * n)
        idx = np.arange(n * n).reshape(n, n)
        a_list, b_list, d_list = [], [], []
        for dy, dx in [(0, 1), (1, 0), (1, 1), (1, -1)]:
            ys, yb = slice(0, n - dy), slice(dy, n)
            xs, xb = (slice(0, n - dx), slice(dx, n)) if dx >= 0 else (slice(-dx, n), slice(0, n + dx))
            a, b = idx[ys, xs].ravel(), idx[yb, xb].ravel()
            a_list.append(a)
            b_list.append(b)
            d_list.append(np.full(len(a), self.cell * math.hypot(dx, dy)))
        a, b, d = np.concatenate(a_list), np.concatenate(b_list), np.concatenate(d_list)
        keep = ~(self.water[a] | self.water[b])
        self.a, self.b, self.d = a[keep], b[keep], d[keep]
        h = self.H.ravel()
        grade = np.abs(h[self.a] - h[self.b]) / self.d
        high = np.clip(np.maximum(h[self.a], h[self.b]) - 600.0, 0.0, None) / 500.0
        self.base_cost = self.d * (1.0 + (grade / 0.045) ** 2) * (1.0 + high)
        self.graph = None
        self.rebuild()

    def rebuild(self) -> None:
        cost = self.base_cost * 0.5 * (self.mult[self.a] + self.mult[self.b])
        N = self.n * self.n
        self.graph = csr_matrix((np.concatenate([cost, cost]),
                                 (np.concatenate([self.a, self.b]), np.concatenate([self.b, self.a]))),
                                shape=(N, N))

    def node(self, x: float, y: float) -> int | None:
        n = self.n
        ix = min(n - 1, max(0, int(x / self.cell)))
        iy = min(n - 1, max(0, int(y / self.cell)))
        for r in range(4):
            best = None
            for jy in range(max(0, iy - r), min(n, iy + r + 1)):
                for jx in range(max(0, ix - r), min(n, ix + r + 1)):
                    k = jy * n + jx
                    if not self.water[k]:
                        d = (jx - ix) ** 2 + (jy - iy) ** 2
                        if best is None or d < best[0]:
                            best = (d, k)
            if best:
                return best[1]
        return None

    def coords(self, path) -> np.ndarray:
        path = np.asarray(path)
        return np.stack([self.X.ravel()[path], self.Y.ravel()[path]], axis=1)


def _walk(pred: np.ndarray, target: int, source: int | None = None):
    path = [target]
    cur = target
    for _ in range(len(pred)):
        if source is not None and cur == source:
            return path[::-1]
        nxt = pred[cur]
        if nxt < 0:
            return path[::-1] if source is None else None
        path.append(int(nxt))
        cur = int(nxt)
    return None


def _rng_edges(pts: np.ndarray) -> list:
    """Relative neighborhood graph: joins near neighbors, like real road networks."""
    D = np.hypot(pts[:, None, 0] - pts[None, :, 0], pts[:, None, 1] - pts[None, :, 1])
    edges = []
    for i in range(len(pts)):
        for j in range(i + 1, len(pts)):
            if not np.any(np.maximum(D[i], D[j]) < D[i, j]):
                edges.append((i, j))
    return edges


def _smooth(coords: np.ndarray, tolerance: float) -> np.ndarray:
    if len(coords) < 3:
        return coords
    pts = np.asarray(LineString(coords).simplify(tolerance).coords)
    for _ in range(2):
        q = 0.75 * pts[:-1] + 0.25 * pts[1:]
        r = 0.25 * pts[:-1] + 0.75 * pts[1:]
        mid = np.empty((2 * len(q), 2))
        mid[0::2], mid[1::2] = q, r
        pts = np.vstack([pts[:1], mid, pts[-1:]])
    return pts


def _build_roads(seed: int, cfg: dict, terrain: Terrain, settlements: list) -> list:
    router = _Router(terrain, float(cfg["roads"]["routing_cell"]))
    nodes = {s.id: router.node(s.x, s.y) for s in settlements}
    roads: list[Road] = []
    tol = router.cell * 0.6

    def add(kind, path, ends):
        xy = router.coords(path)
        for k, sid in ((0, ends[0]), (-1, ends[1])):
            if sid is not None:
                xy[k] = (settlements[sid].x, settlements[sid].y)
        if len(xy) >= 2:
            roads.append(Road(len(roads), kind, ROAD_WIDTH[kind], _smooth(xy, tol), ends))
        router.mult[np.asarray(path)] = np.minimum(router.mult[np.asarray(path)], 0.45)

    def connect(group: list, kind: str, skip: set, max_len: float):
        pts = np.array([(s.x, s.y) for s in group])
        pairs = []
        for i, j in _rng_edges(pts):
            a, b = group[i], group[j]
            if (a.id, b.id) in skip or nodes[a.id] is None or nodes[b.id] is None:
                continue
            if kind == "regional" and a.kind != "town" and b.kind != "town":
                continue
            if math.hypot(a.x - b.x, a.y - b.y) > max_len:
                continue
            pairs.append((a, b))
        sources = sorted({nodes[a.id] for a, _ in pairs})
        if not sources:
            return set()
        _, pred = dijkstra(router.graph, indices=sources, return_predecessors=True)
        row = {src: k for k, src in enumerate(sources)}
        done = set()
        for a, b in pairs:
            path = _walk(pred[row[nodes[a.id]]], nodes[b.id], nodes[a.id])
            if path and len(path) > 1:
                add(kind, path, (a.id, b.id))
                done.add((a.id, b.id))
        router.rebuild()
        return done

    big = [s for s in settlements if s.kind in ("capital", "city")]
    national = connect(big, "national", set(), math.inf) if len(big) > 1 else set()
    mid = [s for s in settlements if s.kind != "village"]
    connect(mid, "regional", national, float(cfg["roads"]["max_regional_km"]) * 1000.0)

    villages = [s for s in settlements if s.kind == "village" and nodes[s.id] is not None]
    sources = set(np.nonzero(router.mult < 1.0)[0].tolist())
    sources |= {nodes[s.id] for s in mid if nodes[s.id] is not None}
    if villages and sources:
        dist, pred, _src = dijkstra(router.graph, indices=sorted(sources), min_only=True,
                                    return_predecessors=True)
        for v in villages:
            target = nodes[v.id]
            if not np.isfinite(dist[target]) or target in sources:
                continue
            path = _walk(pred, target)
            if path and len(path) > 1:
                add("local", path, (None, v.id))
    return roads
