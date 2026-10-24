"""The cathedral and the municipal theatre of the boulevard (prompt 32), drawn from their plan records.

Both are built in the landmark's local frame (`city.landmarks.Frame`: s along the facade, to the right seen
from the street; d into the lot from the street edge; z up), from the plan shapes the planner used for the
footprint, so mesh and footprint agree. The floor stands `base` m over the foot of the front steps (higher
when the ground behind is higher); walls go down to 0.6 m under the lowest ground of the footprint and
their texture's v is 0 at the floor. Everything is real geometry: recessed round-arched portals with their
reveals, tympana and doors, a rose window of three rings and spokes, round-arched windows with stone frames,
gables, towers with belfries, lanterns and domes or pyramids, a crossing dome, an apse; the theatre's
rounded corners, cornice, decorated parapet with piers and urns, pavilion with its great window, curved
crown and dome, glass and iron canopy and stage tower. UVs are meters, as everywhere.

The cathedral reads like St Vincent de Paul in Tunis (neo-Romanesque with a Byzantine dome), the theatre
like the Municipal Theatre of Tunis (Art Nouveau). Each stays under 6,000 triangles (the test counts them).
"""
from __future__ import annotations

import math

import numpy as np
import shapely
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient

from ..city.landmarks import Frame, arc, cathedral_plan, rect, theatre_body, theatre_plan
from .builder import (MeshBuilder, add_arch, add_boxes, add_dome, add_quads, add_sheet, add_walls,
                      extrude, round_head, triangulate)

DOOR, GLASS, IRON = "wood", "glass_dark", "iron"
CORNER_SEGMENTS = 4      # faces of each rounded corner of the theatre (city.landmarks.theatre_body)


def landmark_mesh(mb: MeshBuilder, b, height_fn, cfg: dict) -> None:
    """Building b of kind `cathedral` or `theatre`, with the style's `[landmarks]` table `cfg`."""
    spec = cfg[b.kind]
    fr = Frame(b.facade)
    ring = shapely.get_coordinates(shapely.segmentize(b.footprint.exterior, 1.0))
    ground = np.asarray(height_fn(ring[:, 0], ring[:, 1]), dtype=np.float64)
    w = b.facade["width"]
    foot = fr.xy(np.array([-w / 2, 0.0, w / 2]), np.zeros(3))
    g_foot = float(np.min(height_fn(foot[:, 0], foot[:, 1])))
    floor = max(g_foot + float(spec["base"]), float(ground.max()) + 0.1)
    z0 = float(ground.min()) - 0.6
    if b.kind == "cathedral":
        _cathedral(mb, fr, b, spec, floor, z0, g_foot)
    else:
        _theatre(mb, fr, b, spec, floor, z0, g_foot)


# --- shared pieces --------------------------------------------------------------------------------

def _steps(mb: MeshBuilder, fr: Frame, s0: float, s1: float, d1: float, landing: float, g_foot: float,
           floor: float, z0: float, riser: float, mat: str) -> None:
    """Front steps from the street edge (d = 0) up to the floor at d1, then a landing on to `landing`."""
    rise = max(floor - g_foot, riser)
    n = int(min(max(math.ceil(rise / riser - 1e-6), 2), 24))
    tread = d1 / n
    for i in range(n):          # the last tread runs on as the landing
        end = (i + 1) * tread if i < n - 1 else landing
        add_boxes(mb, [fr.xy(s0, i * tread)], [fr.u], 0.0, s1 - s0, end - i * tread, z0, g_foot + (i + 1) * rise / n,
                  mat)


def _box(mb: MeshBuilder, fr: Frame, s0, s1, d0, d1, z0, z1, mat: str) -> None:
    """A box standing on the frame's axes (no bottom)."""
    add_boxes(mb, [fr.xy(s0, d0)], [fr.u], 0.0, s1 - s0, d1 - d0, z0, z1, mat)


def _prism(mb: MeshBuilder, fr: Frame, sd, z0: float, z1: float, wall: str, top: str | None, z_ref: float) -> Polygon:
    poly = fr.poly(sd)
    extrude(mb, poly, z0, z1, wall, top, z_ref=z_ref)
    return poly


def _band(mb: MeshBuilder, poly: Polygon, reach: float, z0: float, z1: float, mat: str, z_ref: float) -> None:
    """A course standing `reach` m out of a wall all round `poly`, from z0 to z1 (top and underside drawn)."""
    outer = orient(poly.buffer(reach, join_style="mitre"), sign=1.0)
    add_walls(mb, outer.exterior.coords, z0, z1, mat, z_ref)
    ring = outer.difference(poly)
    _cap(mb, ring, z1, mat)
    _cap(mb, ring, z0, mat, up=False)


def _cap(mb: MeshBuilder, poly: Polygon, z: float, mat: str, up: bool = True) -> None:
    """`add_cap` with one vertex per corner (the same faces in fewer bytes)."""
    tri = triangulate(poly)
    if not len(tri):
        return
    pts, inv = np.unique(tri.reshape(-1, 2), axis=0, return_inverse=True)
    idx = np.asarray(inv).reshape(-1, 3)
    pos = np.column_stack([pts, np.full(len(pts), z)])
    mb.add(mat, pos, np.tile([0.0, 0.0, 1.0 if up else -1.0], (len(pts), 1)), np.column_stack([pts[:, 0], -pts[:, 1]]),
           idx if up else idx[:, ::-1])


def _plane(fr: Frame, d: float, sz: np.ndarray) -> np.ndarray:
    """(s, z) points on the facade plane at depth d to world (k, 3)."""
    xy = fr.xy(sz[:, 0], np.full(len(sz), d))
    return np.column_stack([xy, sz[:, 1]])


def _face(mb: MeshBuilder, fr: Frame, d: float, poly_sz: Polygon, mat: str, out: float = -1.0) -> None:
    """A flat face in the plane d = const, its outline given in (s, z); `out` -1 faces the street, +1 the back."""
    tri = triangulate(poly_sz)
    if not len(tri):
        return
    if out > 0:
        tri = tri[:, ::-1]
    pts, inv = np.unique(tri.reshape(-1, 2), axis=0, return_inverse=True)   # one vertex per corner (bytes)
    pos = _plane(fr, d, pts)
    nrm = np.tile([*(fr.n * out), 0.0], (len(pos), 1))
    uv = np.column_stack([pts[:, 0] * -out, -pts[:, 1]])
    mb.add(mat, pos, nrm, uv, np.asarray(inv).reshape(-1, 3))


def _fan(mb: MeshBuilder, pts: np.ndarray, center: np.ndarray, normal, mat: str) -> None:
    """A planar fan from `center` to the closed ring `pts` (k, 3), turned to face `normal`."""
    k = len(pts)
    pos = np.vstack([center[None], pts])
    tris = np.stack([np.zeros(k, dtype=np.int64), 1 + np.arange(k), 1 + (np.arange(k) + 1) % k], axis=1)
    g = np.cross(pos[tris[0, 1]] - pos[0], pos[tris[0, 2]] - pos[0])
    if float(np.dot(g, normal)) < 0:
        tris = tris[:, ::-1]
    n = np.asarray(normal, dtype=np.float64) / max(float(np.linalg.norm(normal)), 1e-12)
    if abs(n[2]) > 0.7:
        uv = np.column_stack([pos[:, 0], -pos[:, 1]])
    else:
        uv = np.column_stack([pos[:, 0] * -n[1] + pos[:, 1] * n[0], -pos[:, 2]])
    mb.add(mat, pos, np.tile(n, (len(pos), 1)), uv, tris)


def _bar(mb: MeshBuilder, p0, p1, width: float, depth: float, mat: str, side=None) -> None:
    """A square-ish bar from p0 to p1 (3D), `width` across along `side` (horizontal by default), `depth` the
    other way: four long faces and two ends."""
    p0, p1 = np.asarray(p0, dtype=np.float64), np.asarray(p1, dtype=np.float64)
    e = p1 - p0
    e /= max(float(np.linalg.norm(e)), 1e-12)
    if side is None:
        side = np.cross(e, [0.0, 0.0, 1.0]) if abs(e[2]) < 0.95 else np.array([1.0, 0.0, 0.0])
    v = np.asarray(side, dtype=np.float64)
    v = v - e * float(v @ e)
    v /= max(float(np.linalg.norm(v)), 1e-12)
    wv = np.cross(e, v)
    c = [v * width / 2 + wv * depth / 2, -v * width / 2 + wv * depth / 2, -v * width / 2 - wv * depth / 2,
         v * width / 2 - wv * depth / 2]
    quads, toward = [], []
    for i in range(4):
        a, b = c[i], c[(i + 1) % 4]
        quads.append([p0 + a, p0 + b, p1 + b, p1 + a])
        toward.append((a + b) / 2)
    quads += [[p0 + c[0], p0 + c[1], p0 + c[2], p0 + c[3]], [p1 + c[0], p1 + c[1], p1 + c[2], p1 + c[3]]]
    toward += [-e, e]
    add_quads(mb, mat, np.array(quads), np.array(toward))


def _window(mb: MeshBuilder, x: float, y: float, z: float, yaw: float, size, frame: float, trim: str,
            glass: str = GLASS) -> None:
    add_arch(mb, x, y, z, yaw, float(size[0]), float(size[1]), frame, glass, trim, head="round")


def _side_windows(mb: MeshBuilder, fr: Frame, s: float, out: float, d0: float, d1: float, bay: float,
                  rows: list, trim: str) -> list:
    """Round-arched windows along a wall s = const facing `out` * u, one per bay between d0 and d1, in each
    row [(width, height, z)]. Returns the bay centers."""
    count = int((d1 - d0) // bay)
    if count <= 0:
        return []
    step = (d1 - d0) / count
    ds = [d0 + (i + 0.5) * step for i in range(count)]
    yaw = fr.yaw((out, 0.0))
    for d in ds:
        x, y = fr.xy(s, d)
        for width, height, z in rows:
            _window(mb, float(x), float(y), z, yaw, (width, height), 0.18, trim)
    return ds


def _portal(mb: MeshBuilder, fr: Frame, s: float, d: float, floor: float, bottom: float, spec, trim: str,
            wall_mat: str) -> None:
    """A recessed round-arched portal in the facade plane d: a stone frame block standing `depth` m out with
    the arch cut through it, the reveal faces, a threshold, a wooden door and a carved tympanum."""
    width, height, fw, depth = (float(v) for v in spec)
    segs = 10
    head = round_head(width, height, segs)              # left foot, right foot, arc from the right jamb top
    hole = np.vstack([head[1:], head[:1]])[::-1] + [s, floor]   # clockwise ring of the opening
    outer = [(s - width / 2 - fw, bottom), (s + width / 2 + fw, bottom), (s + width / 2 + fw, floor + height + fw),
             (s - width / 2 - fw, floor + height + fw)]
    front = d - depth
    _face(mb, fr, front, Polygon(outer, [hole]), trim)
    ring = np.vstack([head[1:], head[:1]]) + [s, floor]   # right foot, up the arc, left foot (counter-clockwise)
    quads, toward = [], []
    cen = np.array([s, floor + max(height - width / 2, 0.0)])
    for a, b in zip(ring[:-1], ring[1:]):
        if abs(a[1] - floor) < 1e-9 and abs(b[1] - floor) < 1e-9:
            continue                                    # the bottom edge is the threshold
        pa, pb = _plane(fr, front, np.array([a, b])), _plane(fr, d, np.array([a, b]))
        quads.append([pa[0], pa[1], pb[1], pb[0]])
        mid = (a + b) / 2
        inward = cen - mid if mid[1] > cen[1] else np.array([s - mid[0], 0.0])
        toward.append([*(fr.u * inward[0]), inward[1]])
    add_quads(mb, trim, np.array(quads), np.array(toward))
    x0, x1, top = s - width / 2 - fw, s + width / 2 + fw, floor + height + fw
    sides = [([x0, bottom], [x0, top], -fr.u), ([x1, bottom], [x1, top], fr.u)]
    quads, toward = [], []
    for (pa, pb, n) in sides:
        q0, q1 = _plane(fr, front, np.array([pa, pb])), _plane(fr, d, np.array([pa, pb]))
        quads.append([q0[0], q1[0], q1[1], q0[1]])
        toward.append([n[0], n[1], 0.0])
    q0, q1 = _plane(fr, front, np.array([[x0, top], [x1, top]])), _plane(fr, d, np.array([[x0, top], [x1, top]]))
    quads.append([q0[0], q0[1], q1[1], q1[0]])
    toward.append([0.0, 0.0, 1.0])
    sill = fr.xy(np.array([s - width / 2, s + width / 2, s + width / 2, s - width / 2]),
                 np.array([front, front, d, d]))
    quads.append(np.column_stack([sill, np.full(4, floor)]))
    toward.append([0.0, 0.0, 1.0])
    add_quads(mb, trim, np.array(quads, dtype=np.float64), np.array(toward, dtype=np.float64))
    spring = floor + max(height - width / 2, 0.0)
    door = Polygon([(s - width / 2, floor), (s + width / 2, floor), (s + width / 2, spring), (s - width / 2, spring)])
    _face(mb, fr, d - 0.03, door, DOOR)
    tymp = arc(s, spring, width / 2, 0.0, math.pi, segs)
    _face(mb, fr, d - 0.03, Polygon(tymp), wall_mat)


def _rose(mb: MeshBuilder, fr: Frame, d: float, zc: float, radius: float, trim: str) -> None:
    """A rose window: dark glass behind three stone rings (rim, middle, hub) joined by twelve spokes."""
    segs = 20
    t = np.linspace(0.0, 2 * math.pi, segs, endpoint=False)
    circle = np.stack([np.cos(t), np.sin(t)], axis=1)
    out = -fr.n

    def at(r: float, dd: float) -> np.ndarray:
        return _plane(fr, dd, circle * r + [0.0, zc])

    _fan(mb, at(radius * 0.86, d - 0.04), np.array([*fr.xy(0.0, d - 0.04), zc]), [out[0], out[1], 0.0], GLASS)
    for r0, r1, dd in ((radius * 0.84, radius, d - 0.3), (radius * 0.52, radius * 0.6, d - 0.18),
                       (radius * 0.12, radius * 0.22, d - 0.18)):
        ring = Polygon(circle * r1 + [0.0, zc], [(circle * r0 + [0.0, zc])[::-1]])
        _face(mb, fr, dd, ring, trim)
    a, b = at(radius, d - 0.3), at(radius, d)              # the rim's outer and inner cylinders
    ai, bi = at(radius * 0.84, d - 0.3), at(radius * 0.84, d - 0.04)
    quads, toward = [], []
    for i in range(segs):
        j = (i + 1) % segs
        radial = (a[i] + a[j]) / 2 - np.array([*fr.xy(0.0, d - 0.3), zc])
        quads.append([a[i], a[j], b[j], b[i]])
        toward.append(radial)
        quads.append([ai[i], ai[j], bi[j], bi[i]])
        toward.append(-radial)
    add_quads(mb, trim, np.array(quads), np.array(toward))
    for k in range(12):
        ang = 2 * math.pi * (k + 0.5) / 12
        dirv = np.array([math.cos(ang), math.sin(ang)])
        p0 = _plane(fr, d - 0.12, (dirv * radius * 0.2 + [0.0, zc])[None])[0]
        p1 = _plane(fr, d - 0.12, (dirv * radius * 0.86 + [0.0, zc])[None])[0]
        _bar(mb, p0, p1, 0.14, 0.16, trim, side=[*(fr.u * -dirv[1]), dirv[0]])


def _cross(mb: MeshBuilder, fr: Frame, x: float, y: float, z: float, size: float) -> None:
    """An iron cross `size` m high standing at (x, y, z), its arm along the facade."""
    _bar(mb, [x, y, z], [x, y, z + size], 0.12, 0.12, IRON)
    arm = np.array([x, y, z + size * 0.68])
    half = np.array([*fr.u * size * 0.28, 0.0])
    _bar(mb, arm - half, arm + half, 0.11, 0.11, IRON, side=[0.0, 0.0, 1.0])


def _pyramid(mb: MeshBuilder, ring: np.ndarray, z: float, apex: np.ndarray, mat: str) -> None:
    """Triangles from a closed ring (k, 2) at height z up to `apex` (3,)."""
    k = len(ring)
    tris = []
    for i in range(k):
        a, b = ring[i], ring[(i + 1) % k]
        tris.append([[a[0], a[1], z], [b[0], b[1], z], apex])
    tris = np.array(tris)
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]
    eave = np.linalg.norm(tris[:, 1, :2] - tris[:, 0, :2], axis=1)
    slope = np.linalg.norm(apex - (tris[:, 0] + tris[:, 1]) / 2, axis=1)
    uv = np.stack([np.stack([np.zeros(k), np.zeros(k)], 1), np.stack([eave, np.zeros(k)], 1),
                   np.stack([eave / 2, slope], 1)], axis=1)
    mb.add(mat, tris.reshape(-1, 3), np.repeat(n, 3, axis=0), uv.reshape(-1, 2), np.arange(3 * k).reshape(-1, 3))


def _octagon(fr: Frame, cs: float, cd: float, r: float, sides: int = 8) -> np.ndarray:
    """A regular polygon (world xy, counter-clockwise) with faces square to the frame."""
    t = (np.arange(sides) + 0.5) * 2 * math.pi / sides
    return fr.xy(cs + r * np.cos(t), cd + r * np.sin(t))


def _polygon_windows(mb: MeshBuilder, ring: np.ndarray, center: np.ndarray, every: int, z: float, size, trim: str,
                     offset: int = 0) -> None:
    """A round-arched window on every `every`-th face of a closed ring (world xy)."""
    k = len(ring)
    for i in range(offset, k, every):
        a, b = ring[i], ring[(i + 1) % k]
        mid = (a + b) / 2
        out = mid - center
        _window(mb, float(mid[0]), float(mid[1]), z, math.atan2(out[1], out[0]), size, 0.12, trim)


def _gable_roof(mb: MeshBuilder, fr: Frame, half: float, d0: float, d1: float, eave: float, ridge: float,
                over: float, mat: str) -> None:
    """Two roof slopes over s in [-half, half], ridge along d, overhanging `over` m at the eaves; UVs u along
    the eave, v up the slope (as the hip roofs)."""
    drop = over * (ridge - eave) / half
    slope = math.hypot(half + over, ridge - eave + drop)
    for sign in (1.0, -1.0):
        e0 = np.array([*fr.xy(sign * (half + over), d0), eave - drop])
        e1 = np.array([*fr.xy(sign * (half + over), d1), eave - drop])
        r0 = np.array([*fr.xy(0.0, d0), ridge])
        r1 = np.array([*fr.xy(0.0, d1), ridge])
        pos = np.array([e0, e1, r1, r0])
        n = np.cross(pos[1] - pos[0], pos[3] - pos[0])
        if n[2] < 0:
            pos = pos[[1, 0, 3, 2]]
            n = -n
        n /= max(float(np.linalg.norm(n)), 1e-12)
        length = d1 - d0
        uv = np.array([[0.0, 0.0], [length, 0.0], [length, slope], [0.0, slope]])
        mb.add(mat, pos, np.tile(n, (4, 1)), uv, np.array([[0, 1, 2], [0, 2, 3]]))


# --- the cathedral --------------------------------------------------------------------------------

def _cathedral(mb: MeshBuilder, fr: Frame, b, spec: dict, floor: float, z0: float, g_foot: float) -> None:
    p = cathedral_plan(b.facade, spec)
    w, f, t, nave, c0, c1 = p["w"], p["f"], p["tower"], p["nave"], p["cross0"], p["cross1"]
    wall, roof, trim, dome = (str(spec[k]) for k in ("wall", "roof", "trim", "dome"))
    hn = floor + float(b.height)
    ridge = hn + nave / 2 * math.tan(math.radians(float(spec["pitch"])))
    _steps(mb, fr, -w / 2, w / 2, f, f, g_foot, floor, z0, float(spec["riser"]), trim)
    # nave, its front gable and roof, the cornice bands along its eaves
    _prism(mb, fr, rect(-nave / 2, nave / 2, f, c0), z0, hn, wall, None, floor)
    _face(mb, fr, f, Polygon([(-nave / 2, hn), (nave / 2, hn), (0.0, ridge)]), wall)
    _gable_roof(mb, fr, nave / 2, f, c0, hn, ridge, 0.35, roof)
    rake = [np.array([*fr.xy(sgn * (nave / 2 + 0.3), f - 0.12), hn - 0.2]) for sgn in (-1.0, 1.0)]
    top = np.array([*fr.xy(0.0, f - 0.12), ridge + 0.25])
    for e in rake:
        _bar(mb, e, top, 0.45, 0.3, trim, side=[*fr.n, 0.0])
    _cross(mb, fr, *fr.xy(0.0, f + 0.2), ridge + 0.2, 2.2)
    for sgn in (-1.0, 1.0):
        _box(mb, fr, *sorted((sgn * nave / 2, sgn * (nave / 2 + 0.25))), f + t, c0, hn - 0.55, hn, trim)
    # facade: the central portal and the rose window over it
    _portal(mb, fr, 0.0, f, floor, z0, spec["portal"], trim, wall)
    rose_r, rose_z = float(spec["rose"][0]), float(spec["rose"][1])
    _rose(mb, fr, f, floor + rose_z, min(rose_r, nave / 2 - 1.0), trim)
    _box(mb, fr, -nave / 2, nave / 2, f - 0.25, f, floor + rose_z - rose_r - 0.95, floor + rose_z - rose_r - 0.65, trim)
    # aisles behind the towers, with buttresses and windows, and the clerestory over their roofs
    ha, rise = (float(v) for v in spec["aisle"])
    bay = float(spec["bay"])
    aw = [float(v) for v in spec["aisle_window"]]
    cw = [float(v) for v in spec["clerestory"]]
    for sgn in (-1.0, 1.0):
        s_in, s_out = sgn * nave / 2, sgn * w / 2
        _prism(mb, fr, rect(*sorted((s_in, s_out)), f + t, c0), z0, floor + ha, wall, None, floor)
        lean = np.array([[*fr.xy(s_out + sgn * 0.3, f + t), floor + ha - 0.3 * rise / t],
                         [*fr.xy(s_out + sgn * 0.3, c0 + 0.3), floor + ha - 0.3 * rise / t],
                         [*fr.xy(s_in, c0 + 0.3), floor + ha + rise], [*fr.xy(s_in, f + t), floor + ha + rise]])
        _slope(mb, lean, roof)
        ds = _side_windows(mb, fr, s_out, sgn, f + t, c0, bay, [(aw[0], aw[1], floor + aw[2])], trim)
        _side_windows(mb, fr, s_in, sgn, f + t, c0, bay, [(cw[0], cw[1], floor + ha + rise + 0.5)], trim)
        for d in ([f + t] + [(x + y) / 2 for x, y in zip(ds[:-1], ds[1:])] + [c0]):
            d = min(max(d, f + t + 0.35), c0 - 0.35)
            _box(mb, fr, *sorted((s_out, s_out + sgn * 0.5)), d - 0.35, d + 0.35, z0, floor + ha - 0.6, wall)
        _box(mb, fr, *sorted((s_out, s_out + sgn * 0.2)), f + t, c0, floor + ha - 0.45, floor + ha, trim)
    # towers: shaft, side portal and window, string courses, belfry, cornice, lantern, cap and cross
    tw = [float(v) for v in spec["tower"]]
    ht, bh = floor + tw[1], tw[2]
    ln_r, ln_h = float(spec["lantern"][0]) * t, float(spec["lantern"][1])
    for sgn in (-1.0, 1.0):
        s_c = sgn * (w / 2 - t / 2)
        sq = rect(s_c - t / 2, s_c + t / 2, f, f + t)
        shaft = _prism(mb, fr, sq, z0, ht, wall, wall, floor)
        _portal(mb, fr, s_c, f, floor, z0, spec["side_portal"], trim, wall)
        x, y = fr.xy(s_c, f)
        _window(mb, float(x), float(y), floor + 9.5, fr.yaw((0.0, -1.0)), (1.1, 2.6), 0.18, trim)
        for z in (hn - 0.5, ht - bh - 1.6):
            _band(mb, shaft, 0.14, z, z + 0.35, trim, floor)
        _band(mb, shaft, 0.3, ht - 0.55, ht + 0.05, trim, floor)
        for out in ((0.0, -1.0), (0.0, 1.0), (-1.0, 0.0), (1.0, 0.0)):
            c = np.array([s_c + out[0] * t / 2, f + t / 2 + out[1] * t / 2])
            along = np.array([out[1], -out[0]])
            for k in (-1.0, 1.0):
                q = c + along * k * t * 0.2
                x, y = fr.xy(q[0], q[1])
                _window(mb, float(x), float(y), ht - bh - 1.1, fr.yaw(out), (t * 0.24, bh), 0.12, trim, IRON)
        cd = f + t / 2
        lantern = _octagon(fr, s_c, cd, ln_r)
        extrude(mb, Polygon(lantern), ht + 0.05, ht + 0.05 + ln_h, wall, wall, z_ref=floor)
        center = fr.xy(s_c, cd)
        _polygon_windows(mb, lantern, center, 2, ht + 0.45, (ln_r * 0.5, ln_h * 0.62), trim, offset=1)
        cap_z = ht + 0.05 + ln_h
        _band(mb, Polygon(lantern), 0.12, cap_z - 0.25, cap_z, trim, floor)
        if b.facade.get("cap") == "dome":
            r = ln_r * 1.02
            add_dome(mb, float(center[0]), float(center[1]), cap_z, r, dome, height=r * float(spec["cap"]["dome"]),
                     segments=12, rings=4)
            tip = cap_z + r * float(spec["cap"]["dome"])
        else:
            tip = cap_z + float(spec["cap"]["pyramid"])
            _pyramid(mb, _octagon(fr, s_c, cd, ln_r * 1.08), cap_z, np.array([center[0], center[1], tip]), dome)
        _cross(mb, fr, float(center[0]), float(center[1]), tip - 0.05, 1.8)
    # crossing: a square block over the nave, a drum with windows and the dome
    cross_top = ridge + 1.2
    _prism(mb, fr, rect(-nave / 2, nave / 2, c0, c1), z0, cross_top, wall, wall, floor)
    _band(mb, fr.poly(rect(-nave / 2, nave / 2, c0, c1)), 0.2, cross_top - 0.4, cross_top, trim, floor)
    tw_ = [float(v) for v in spec["transept_window"]]
    for sgn in (-1.0, 1.0):                                             # the crossing's sides read as transept ends
        x, y = fr.xy(sgn * nave / 2, (c0 + c1) / 2)
        _window(mb, float(x), float(y), floor + tw_[2], fr.yaw((sgn, 0.0)), (tw_[0], tw_[1]), 0.3, trim)
    dr, dh, rise_d = float(spec["crossing"][0]) * nave, float(spec["crossing"][1]), float(spec["crossing"][2])
    cc = fr.xy(0.0, (c0 + c1) / 2)
    drum = _octagon(fr, 0.0, (c0 + c1) / 2, dr, 12)
    extrude(mb, Polygon(drum), cross_top, cross_top + dh, wall, None, z_ref=floor)
    _polygon_windows(mb, drum, cc, 2, cross_top + 0.6, (dr * 0.3, dh * 0.62), trim)
    _band(mb, Polygon(drum), 0.15, cross_top + dh - 0.3, cross_top + dh, trim, floor)
    add_dome(mb, float(cc[0]), float(cc[1]), cross_top + dh, dr * 1.03, dome, height=dr * rise_d, segments=16, rings=5)
    _cross(mb, fr, float(cc[0]), float(cc[1]), cross_top + dh + dr * rise_d - 0.05, 2.0)
    # apse with its windows and half-cone roof
    ah, arise = (float(v) for v in spec["apse"])
    rim = arc(0.0, c1, p["apse"], 0.0, math.pi, 8)
    apse = fr.poly(np.vstack([rim, [(0.0, c1)]]))
    add_walls(mb, apse.exterior.coords, z0, floor + ah, wall, floor)
    world_rim = fr.xy(rim[:, 0], rim[:, 1])
    apex = np.array([*fr.xy(0.0, c1), floor + ah + arise])
    tris = [[[*world_rim[i + 1], floor + ah], [*world_rim[i], floor + ah], apex] for i in range(len(rim) - 1)]
    _cone_part(mb, np.array(tris), roof)
    for i in (2, 4, 5, 7):                                              # faces symmetric about the axis
        a, bb = world_rim[i - 1], world_rim[i]
        mid = (a + bb) / 2
        out = mid - fr.xy(0.0, c1)
        _window(mb, float(mid[0]), float(mid[1]), floor + aw[2], math.atan2(out[1], out[0]), (aw[0], aw[1]), 0.18, trim)


def _slope(mb: MeshBuilder, quad: np.ndarray, mat: str) -> None:
    """A sloping roof quad (eave edge first, counter-clockwise from above), UVs u along the eave and v up
    the slope in meters, as the hip roofs."""
    quad = np.asarray(quad, dtype=np.float64)
    e = quad[1] - quad[0]
    e /= max(float(np.linalg.norm(e)), 1e-12)
    n = np.cross(quad[1] - quad[0], quad[3] - quad[0])
    if n[2] < 0:
        quad, n = quad[[1, 0, 3, 2]], -n
        e = -e
    n /= max(float(np.linalg.norm(n)), 1e-12)
    up = np.cross(n, e)
    rel = quad - quad[0]
    mb.add(mat, quad, np.tile(n, (4, 1)), np.column_stack([rel @ e, rel @ up]), np.array([[0, 1, 2], [0, 2, 3]]))


def _cone_part(mb: MeshBuilder, tris: np.ndarray, mat: str) -> None:
    """Roof triangles (eave edge first, apex last), UVs u along the eave, v up the slope."""
    n = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    flip = n[:, 2] < 0
    tris[flip] = tris[flip][:, [1, 0, 2]]
    n[flip] *= -1.0
    n /= np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]
    k = len(tris)
    eave = np.linalg.norm(tris[:, 1, :2] - tris[:, 0, :2], axis=1)
    slope = np.linalg.norm(tris[:, 2] - (tris[:, 0] + tris[:, 1]) / 2, axis=1)
    uv = np.stack([np.zeros((k, 2)), np.stack([eave, np.zeros(k)], 1), np.stack([eave / 2, slope], 1)], axis=1)
    mb.add(mat, tris.reshape(-1, 3), np.repeat(n, 3, axis=0), uv.reshape(-1, 2), np.arange(3 * k).reshape(-1, 3))


# --- the theatre ----------------------------------------------------------------------------------

def _theatre(mb: MeshBuilder, fr: Frame, b, spec: dict, floor: float, z0: float, g_foot: float) -> None:
    p = theatre_plan(b.facade, spec)
    w, f, end, rc, pav, pf = p["w"], p["f"], p["end"], p["round"], p["pav"], p["pav_front"]
    wall, roof, trim, dome = (str(spec[k]) for k in ("wall", "roof", "trim", "dome"))
    h = floor + float(b.height)
    _steps(mb, fr, -w / 2, w / 2, pf, f, g_foot, floor, z0, float(spec["riser"]), trim)
    body = fr.poly(theatre_body(p, CORNER_SEGMENTS))
    add_walls(mb, body.exterior.coords, z0, h, wall, floor)
    _band(mb, body, 0.12, z0, floor + 0.9, trim, floor)                  # plinth course
    _band(mb, body, 0.15, floor + 4.7, floor + 5.0, trim, floor)         # string course over the ground floor
    ch, cr = (float(v) for v in spec["cornice"])
    _band(mb, body, cr, h - ch, h, trim, floor)
    ph, pt, gap, prise = (float(v) for v in spec["parapet"])
    inner = orient(body.buffer(-pt, join_style="mitre"), sign=1.0)
    ring = orient(body.difference(inner), sign=1.0)
    add_walls(mb, ring.exterior.coords, h, h + ph, wall, floor)
    for hole in ring.interiors:
        add_walls(mb, hole.coords, h, h + ph, wall, floor)
    _cap(mb, ring, h + ph, trim)
    _cap(mb, inner, h, roof)
    _parapet_piers(mb, body, fr, pav, h + ph, gap, prise, trim)
    cr_, ch_, crise_ = (float(v) for v in spec["corner_cupola"])
    for sgn in (-1.0, 1.0):                                             # a cupola over each rounded corner
        c = np.array([sgn * (w / 2 - rc), f + rc]) + np.array([sgn, -1.0]) / math.sqrt(2) * (rc - cr_ - 0.8)
        drum = _octagon(fr, c[0], c[1], cr_, 12)
        extrude(mb, Polygon(drum), h, h + ch_, wall, None, z_ref=floor)
        _band(mb, Polygon(drum), 0.1, h + ch_ - 0.25, h + ch_, trim, floor)
        cc = fr.xy(c[0], c[1])
        add_dome(mb, float(cc[0]), float(cc[1]), h + ch_, cr_ * 1.04, dome, height=cr_ * crise_, segments=12, rings=4)
        tip = h + ch_ + cr_ * crise_
        add_dome(mb, float(cc[0]), float(cc[1]), tip - 0.05, 0.22, trim, height=0.55, segments=6, rings=2)
    _theatre_windows(mb, fr, p, spec, floor, trim)
    # stage tower at the back
    fw, fd, fh = (float(v) for v in spec["fly"])
    fly = _prism(mb, fr, rect(-w * fw / 2, w * fw / 2, end - (end - f) * fd, end - 0.3), z0, h + fh, wall, roof, floor)
    _band(mb, fly, 0.2, h + fh - 0.5, h + fh, trim, floor)
    # the pavilion: pilasters, doors, canopy, great window, curved crown and dome
    top = h + float(spec["pavilion"][2])
    pav_poly = _prism(mb, fr, rect(-pav / 2, pav / 2, pf, p["pav_back"]), z0, top, wall, roof, floor)
    _band(mb, pav_poly, 0.3, top - 0.7, top, trim, floor)
    for sgn in (-1.0, 1.0):
        _box(mb, fr, *sorted((sgn * pav / 2, sgn * (pav / 2 - 0.7))), pf - 0.3, pf, floor, top - 0.7, trim)
    gw = [float(v) for v in spec["ground_window"]]
    yaw = fr.yaw((0.0, -1.0))
    for s in (-pav / 3.2, 0.0, pav / 3.2):
        x, y = fr.xy(s, pf)
        _window(mb, float(x), float(y), floor, yaw, (gw[0], gw[1]), 0.22, trim)
    bw, bh, bs = (float(v) for v in spec["big_window"])
    bw = min(bw, pav - 2.4)
    x, y = fr.xy(0.0, pf)
    _window(mb, float(x), float(y), floor + bs, yaw, (bw, bh), 0.4, trim)
    spring = floor + bs + bh - bw / 2
    for s in (-bw / 6, bw / 6):                                          # mullions and a transom
        head = spring + math.sqrt(bw * bw / 4 - s * s) - 0.05
        _bar(mb, [*fr.xy(s, pf - 0.12), floor + bs], [*fr.xy(s, pf - 0.12), head], 0.12, 0.1, IRON)
    _bar(mb, [*fr.xy(-bw / 2, pf - 0.12), spring], [*fr.xy(bw / 2, pf - 0.12), spring], 0.12, 0.1, IRON,
         side=[0.0, 0.0, 1.0])
    _canopy(mb, fr, pav, pf, floor, spec)
    _crown(mb, fr, pav, pf, top, spec, wall, trim, dome)


def _parapet_piers(mb: MeshBuilder, body: Polygon, fr: Frame, pav: float, z: float, gap: float, rise: float,
                   trim: str) -> None:
    """Piers standing on the parapet every `gap` m along the front, the rounded corners and the sides, each
    carrying an urn; none behind the pavilion or along the back."""
    ring = body.exterior
    pts = shapely.get_coordinates(shapely.line_interpolate_point(ring, np.arange(gap / 2, ring.length, gap)))
    s = (pts - fr.o) @ fr.u
    d = (pts - fr.o) @ fr.n
    back = d.max() - 1.0
    keep = (np.abs(s) > pav / 2 + 0.6) & (d < back)
    for q in pts[keep]:
        at = ring.project(shapely.Point(q))
        a, bb = ring.interpolate(max(at - 0.3, 0.0)), ring.interpolate(min(at + 0.3, ring.length))
        tan = np.array([bb.x - a.x, bb.y - a.y])
        tan /= max(float(np.hypot(*tan)), 1e-9)
        add_boxes(mb, [q], [tan], -0.28, 0.28, 0.5, z, z + rise, trim)
        c = q + np.array([-tan[1], tan[0]]) * 0.25
        add_dome(mb, float(c[0]), float(c[1]), z + rise, 0.2, trim, height=0.42, segments=5, rings=1)


def _theatre_windows(mb: MeshBuilder, fr: Frame, p: dict, spec: dict, floor: float, trim: str) -> None:
    """Three rows of round-arched windows: on the straight fronts beside the pavilion, on the rounded corners
    and along both sides."""
    w, f, end, rc, pav = p["w"], p["f"], p["end"], p["round"], p["pav"]
    gw = [float(v) for v in spec["ground_window"]]
    mw = [float(v) for v in spec["main_window"]]
    tw = [float(v) for v in spec["attic_window"]]
    rows = [(gw[0], gw[1], floor + 0.4), (mw[0], mw[1], floor + mw[2]), (tw[0], tw[1], floor + tw[2])]
    yaw = fr.yaw((0.0, -1.0))
    straight = w / 2 - rc - pav / 2
    if straight >= mw[0] + 0.8:
        for sgn in (-1.0, 1.0):
            x, y = fr.xy(sgn * (pav / 2 + straight / 2), f)
            for width, height, z in rows:
                _window(mb, float(x), float(y), z, yaw, (width, height), 0.18, trim)
    seg = CORNER_SEGMENTS
    chord = 2 * rc * math.sin(math.pi / 4 / seg)
    for sgn in (-1.0, 1.0):
        cs, cd = sgn * (w / 2 - rc), f + rc
        for k in (1.5, seg - 1.5):                                      # on two faces of each rounded corner
            a = -math.pi / 2 + (k / seg) * math.pi / 2
            a = a if sgn > 0 else math.pi - a
            r = rc * math.cos(math.pi / 4 / seg)
            x, y = fr.xy(cs + r * math.cos(a), cd + r * math.sin(a))
            out = fr.u * math.cos(a) + fr.n * math.sin(a)
            for width, height, z in rows:
                _window(mb, float(x), float(y), z, math.atan2(out[1], out[0]), (min(width, chord - 0.45), height),
                        0.16, trim)
        _side_windows(mb, fr, sgn * w / 2, sgn, f + rc + 0.6, end - 0.6, float(spec["bay"]), rows, trim)


def _canopy(mb: MeshBuilder, fr: Frame, pav: float, pf: float, floor: float, spec: dict) -> None:
    """A glass and iron canopy over the doors: its front edge a flat arc, rising a little toward it, with an
    iron fascia and three tie rods to the wall."""
    zc, reach, fascia = (float(v) for v in spec["canopy"])
    half = pav / 2 + 0.4
    s = np.linspace(-half, half, 9)
    front = pf - reach * (0.55 + 0.45 * (1.0 - (s / half) ** 2))
    back = np.full_like(s, pf)
    z_of = lambda d: floor + zc + (pf - d) * 0.12                       # noqa: E731 - rises toward the street
    tris = []
    for i in range(len(s) - 1):
        a0 = [*fr.xy(s[i], back[i]), z_of(back[i])]
        a1 = [*fr.xy(s[i + 1], back[i + 1]), z_of(back[i + 1])]
        b0 = [*fr.xy(s[i], front[i]), z_of(front[i])]
        b1 = [*fr.xy(s[i + 1], front[i + 1]), z_of(front[i + 1])]
        tris += [[a0, b1, a1], [a0, b0, b1]]
    tris = np.array(tris)
    up = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    tris[up[:, 2] < 0] = tris[up[:, 2] < 0][:, ::-1]
    add_sheet(mb, tris, GLASS, 0.02)
    edge = [np.array([*fr.xy(s[i], front[i]), z_of(front[i])]) for i in range(len(s))]
    band = []
    for a, bb in zip(edge[:-1], edge[1:]):
        lo_a, lo_b = a - [0.0, 0.0, fascia], bb - [0.0, 0.0, fascia]
        band += [[a, lo_a, lo_b], [a, lo_b, bb]]
    add_sheet(mb, np.array(band), IRON, 0.03)
    for i in (1, 7):                                                    # tie rods to the wall under the great window
        _bar(mb, edge[i], [*fr.xy(s[i], pf), floor + zc + 1.2], 0.06, 0.06, IRON)


def _crown(mb: MeshBuilder, fr: Frame, pav: float, pf: float, top: float, spec: dict, wall: str,
           trim: str, dome: str) -> None:
    """The pavilion's crown: a curved Art Nouveau gable on its front edge, and a dome on a drum behind it."""
    r = pav * 0.36
    gable = Polygon(np.vstack([[(-r, top), (r, top)], arc(0.0, top + 0.6, r, 0.0, math.pi, 12)]))
    d0, d1 = pf + 0.1, pf + 0.6
    _face(mb, fr, d0, gable, wall)
    _face(mb, fr, d1, gable, wall, out=1.0)
    ring = np.asarray(gable.exterior.coords)[:-1]
    quads, toward = [], []
    c = np.array([0.0, top])
    for a, bb in zip(ring, np.roll(ring, -1, axis=0)):
        if abs(a[1] - top) < 1e-9 and abs(bb[1] - top) < 1e-9:
            continue
        pa, pb = _plane(fr, d0, np.array([a, bb])), _plane(fr, d1, np.array([a, bb]))
        quads.append([pa[0], pa[1], pb[1], pb[0]])
        mid = (a + bb) / 2 - c
        toward.append([*(fr.u * mid[0]), mid[1]])
    add_quads(mb, trim, np.array(quads), np.array(toward))
    x, y = fr.xy(0.0, d0)
    _window(mb, float(x), float(y), top + 0.9, fr.yaw((0.0, -1.0)), (r * 0.7, r * 0.75), 0.15, trim)
    cr, ch, crise = (float(v) for v in spec["crown"])
    cd = pf + 0.9 + cr                                                  # behind the gable
    cc = fr.xy(0.0, cd)
    drum = _octagon(fr, 0.0, cd, cr, 12)
    extrude(mb, Polygon(drum), top, top + ch, wall, None, z_ref=top)
    _band(mb, Polygon(drum), 0.12, top + ch - 0.25, top + ch, trim, top)
    add_dome(mb, float(cc[0]), float(cc[1]), top + ch, cr * 1.02, dome, height=cr * crise, segments=16, rings=5)
    tip = top + ch + cr * crise
    _bar(mb, [cc[0], cc[1], tip - 0.1], [cc[0], cc[1], tip + 1.1], 0.14, 0.14, trim)
    add_dome(mb, float(cc[0]), float(cc[1]), tip + 1.1, 0.28, trim, height=0.5, segments=6, rings=2)
