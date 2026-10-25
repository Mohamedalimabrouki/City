"""The railway station and its tracks (prompt 33), drawn from the plan's station records (`city/station.py`).

The head building stands in the station's frame (`city.landmarks.Frame`: s along the forecourt's street
edge, d away from the avenue, z up). It reads like the colonial stations of Tunisia: a long hall with a
pitched tiled roof and round-arched windows, a taller entrance pavilion with a pediment and a great
recessed arch, and a square clock tower at one end with four white dials and dark hands (real geometry,
all four showing the same time, set on the station's own stream), a cornice and a tiled pyramid cap.
Behind it the platforms follow the ground under the tracks; canopies on posts cover them, with an iron
valance; buffer stops close the tracks. The tracks themselves (`rail_meshes`) are drawn tile by tile:
a sleeper bed (the `ballast` texture shows the sleepers) under two thin steel rails per track; where a
street crosses, the rails run at the street's surface (a level crossing). UVs are meters, as everywhere.
"""
from __future__ import annotations

import math

import numpy as np
import shapely
from shapely.geometry import Point, Polygon
from shapely.geometry.polygon import orient

from ..city.landmarks import Frame, rect
from ..city.station import dims
from ..rng import stream
from .builder import MeshBuilder, add_boxes, add_quads, add_ribbon, add_skirt, add_walls
from .landmarks import GLASS, IRON, _band, _bar, _cap, _face, _fan, _gable_roof, _portal, _pyramid, _window


def station_mesh(mb: MeshBuilder, b, height_fn, cfg: dict, seed: int) -> None:
    """Building b of kind `station` (the head building) or `station_platforms`, with the style's `[station]`."""
    fr = Frame(b.facade)
    if b.kind == "station":
        _head(mb, fr, b, height_fn, cfg, seed)
    else:
        _platforms(mb, fr, b, height_fn, cfg)


def forecourt_skirt(mb: MeshBuilder, b, drawn) -> None:
    """The forecourt's edge: a curb face from its paving down into the ground."""
    ring = shapely.get_coordinates(shapely.segmentize(orient(b.footprint, sign=1.0).exterior, 4.0))[:-1]
    g = np.asarray(drawn(ring[:, 0], ring[:, 1]), dtype=np.float64)
    add_skirt(mb, ring, g + float(b.height), g - 0.1, "curb")


# --- the head building ------------------------------------------------------------------------------

def _head(mb: MeshBuilder, fr: Frame, b, height_fn, cfg: dict, seed: int) -> None:
    f = b.facade
    p = dims(cfg, len(f["tracks"]))
    ring = shapely.get_coordinates(shapely.segmentize(b.footprint.exterior, 2.0))
    ground = np.asarray(height_fn(ring[:, 0], ring[:, 1]), dtype=np.float64)
    floor = float(ground.max()) + float(cfg["floor"])
    z0 = float(ground.min()) - 0.6
    wall, roof, trim = str(cfg["wall"]), str(cfg["roof"]), str(cfg["trim"])
    h, front, back = f["width"] / 2, p["front"], p["back"]
    hall_h, pitch = float(cfg["hall"][2]), math.radians(float(cfg["hall"][3]))
    pw, pout, pextra = (float(v) for v in cfg["pavilion"])
    t, th = (float(v) for v in cfg["tower"])
    ts = f["tower_side"] * (h - t / 2)
    t_front = front - float(cfg["tower_out"])
    top = floor + hall_h
    depth = back - front
    # the hall: walls, a plinth course, a cornice, and the pitched roof with its gable ends
    hall = fr.poly(rect(-h, h, front, back))
    add_walls(mb, hall.exterior.coords, z0, top, wall, floor)
    _band(mb, hall, 0.12, z0, floor + 0.8, trim, floor)
    _band(mb, hall, 0.3, top - 0.55, top, trim, floor)
    along = _turned(fr, (front + back) / 2)
    ridge = top + depth / 2 * math.tan(pitch)
    _gable_roof(mb, along, depth / 2, -h, h, top, ridge, 0.5, roof)
    for sgn in (-1.0, 1.0):
        _face(mb, along, sgn * h, Polygon([(-depth / 2, top), (depth / 2, top), (0.0, ridge)]), wall, out=sgn)
    _hall_windows(mb, fr, cfg, f, floor, (-pw / 2, pw / 2), (ts - t / 2, ts + t / 2), trim)
    # the entrance pavilion: taller, through the hall, a pediment toward the forecourt and the platforms
    pf = front - pout
    ptop = top + pextra
    pav = fr.poly(rect(-pw / 2, pw / 2, pf, back + 0.4))
    add_walls(mb, pav.exterior.coords, z0, ptop, wall, floor)
    _band(mb, pav, 0.14, z0, floor + 0.8, trim, floor)
    _band(mb, pav, 0.35, ptop - 0.6, ptop, trim, floor)
    prise = ptop + pw / 2 * math.tan(math.radians(float(cfg["pediment"])))
    _gable_roof(mb, fr, pw / 2, pf, back + 0.4, ptop, prise, 0.45, roof)
    for d, out in ((pf, -1.0), (back + 0.4, 1.0)):
        _face(mb, fr, d, Polygon([(-pw / 2, ptop), (pw / 2, ptop), (0.0, prise)]), wall, out=out)
        _face(mb, fr, d + out * 0.12, Polygon([(-1.4, ptop + 0.6), (1.4, ptop + 0.6), (0.0, ptop + 0.6 + 1.4 *
              math.tan(math.radians(float(cfg["pediment"]))))]), trim, out=out)   # a stone tympanum mark
    _entrance(mb, fr, cfg, pf, floor, height_fn, trim)
    # the clock tower
    tower = fr.poly(rect(ts - t / 2, ts + t / 2, t_front, front + t))
    ttop = floor + th
    add_walls(mb, tower.exterior.coords, z0, ttop, wall, floor)
    _band(mb, tower, 0.14, z0, floor + 0.8, trim, floor)
    _band(mb, tower, 0.2, top - 0.55, top, trim, floor)
    radius, below = (float(v) for v in cfg["clock"])
    zc = ttop - below
    _band(mb, tower, 0.22, zc - radius - 0.9, zc - radius - 0.6, trim, floor)
    _band(mb, tower, 0.4, ttop - 0.7, ttop, trim, floor)
    over = fr.poly(rect(ts - t / 2 - 0.55, ts + t / 2 + 0.55, t_front - 0.55, front + t + 0.55))
    ring2 = np.asarray(orient(over, sign=1.0).exterior.coords)[:-1]
    apex = np.array([*fr.xy(ts, t_front + t / 2), ttop + float(cfg["cap"])])
    _pyramid(mb, ring2, ttop, apex, roof)
    _cap(mb, over, ttop - 0.01, trim, up=False)
    _bar(mb, apex - [0.0, 0.0, 0.3], apex + [0.0, 0.0, 1.6], 0.09, 0.09, IRON)       # the finial
    _tower_windows(mb, fr, ts, t, t_front, floor, top, zc - radius - 1.2, trim)
    _clocks(mb, fr, ts, t, t_front, zc, radius, trim, seed, f)


def _turned(fr: Frame, d: float) -> Frame:
    """The frame turned a quarter: its d runs along this one's s, its s along this one's d, origin at depth d."""
    o = fr.xy(0.0, d)
    yaw = math.atan2(-fr.u[1], -fr.u[0])
    return Frame({"x": float(o[0]), "y": float(o[1]), "yaw": yaw})


def _hall_windows(mb: MeshBuilder, fr: Frame, cfg: dict, f: dict, floor: float, pav: tuple, tower: tuple,
                  trim: str) -> None:
    """Round-arched windows (and every third bay a door) on the hall's front and back, clear of the pavilion
    and the tower; a row of smaller windows above them on the front."""
    width, height, sill, bay = (float(v) for v in cfg["window"])
    dw, dh = (float(v) for v in cfg["doors"])
    h = f["width"] / 2
    p = dims(cfg, len(f["tracks"]))
    count = int(2 * h // bay)
    step = 2 * h / count
    for i in range(count):
        s = -h + (i + 0.5) * step
        if pav[0] - 1.2 < s < pav[1] + 1.2:
            continue
        for d, out in ((p["front"], -1.0), (p["back"], 1.0)):
            if out < 0 and tower[0] - 1.2 < s < tower[1] + 1.2:
                continue
            x, y = fr.xy(s, d)
            yaw = fr.yaw((0.0, out))
            door = out < 0 and i % 3 == 1
            if door:
                _window(mb, float(x), float(y), floor, yaw, (dw, dh), 0.2, trim, glass="wood")
            else:
                _window(mb, float(x), float(y), floor + sill, yaw, (width, height), 0.2, trim)
            if out < 0:                                     # the upper row faces the forecourt only
                _window(mb, float(x), float(y), floor + sill + height + 1.4, yaw, (width * 0.6, 1.3), 0.14, trim)


def _entrance(mb: MeshBuilder, fr: Frame, cfg: dict, pf: float, floor: float, height_fn, trim: str) -> None:
    """The great recessed arch (glazed fanlight over the doors), a name panel above it, two smaller arched
    windows beside it, and the steps up from the forecourt."""
    width, height, frame = (float(v) for v in cfg["entrance"])
    pw = float(cfg["pavilion"][0])
    _portal(mb, fr, 0.0, pf, floor, floor - 0.2, (width, height, frame, 0.6), trim, GLASS)
    zb = floor + height + frame + 0.7
    _face(mb, fr, pf - 0.1, Polygon([(-pw * 0.3, zb), (pw * 0.3, zb), (pw * 0.3, zb + 1.1), (-pw * 0.3, zb + 1.1)]),
          trim)
    for sgn in (-1.0, 1.0):
        x, y = fr.xy(sgn * (width / 2 + frame + (pw / 2 - width / 2 - frame) / 2), pf)
        _window(mb, float(x), float(y), floor + 1.0, fr.yaw((0.0, -1.0)), (1.6, 4.2), 0.2, trim)
        _window(mb, float(x), float(y), floor + 6.4, fr.yaw((0.0, -1.0)), (1.2, 2.0), 0.16, trim)
    run, riser = 0.34, 0.16                                 # steps across the pavilion from the forecourt
    foot = fr.xy(np.array([-width, 0.0, width]), np.full(3, pf - 0.7))
    g = float(np.min(height_fn(foot[:, 0], foot[:, 1]))) + float(cfg["forecourt_lift"])
    n = int(min(max(math.ceil((floor - g) / riser - 1e-6), 1), 12))
    rise = (floor - g) / n
    for i in range(n):
        d0 = pf - 0.6 - (n - i) * run
        add_boxes(mb, [fr.xy(-width / 2 - frame - 0.6, d0)], [fr.u], 0.0, width + 2 * frame + 1.2,
                  pf - 0.6 - d0 + 0.6, g - 0.3, g + (i + 1) * rise, trim)


def _tower_windows(mb: MeshBuilder, fr: Frame, ts: float, t: float, t_front: float, floor: float, hall_top: float,
                   z_max: float, trim: str) -> None:
    """Narrow arched windows up each face of the tower, between the hall's cornice and the clock band."""
    rows = [z for z in np.arange(hall_top + 1.2, z_max - 2.2, 4.2)]
    faces = [(ts, t_front, (0.0, -1.0)), (ts, t_front + t, (0.0, 1.0)), (ts - t / 2, t_front + t / 2, (-1.0, 0.0)),
             (ts + t / 2, t_front + t / 2, (1.0, 0.0))]
    for s, d, out in faces:
        x, y = fr.xy(s, d)
        for z in rows:
            _window(mb, float(x), float(y), float(z), fr.yaw(out), (0.9, 2.1), 0.14, trim)


def _clocks(mb: MeshBuilder, fr: Frame, ts: float, t: float, t_front: float, zc: float, radius: float, trim: str,
            seed: int, f: dict) -> None:
    """A clock on each face of the tower: a white dial in a stone ring, twelve hour marks, two dark hands.
    The time comes from the station's own stream, so all four faces agree."""
    rng = stream(seed, "station", "clock", round(f["x"], 1), round(f["y"], 1))
    minutes = float(rng.integers(0, 720))
    hour_a, min_a = 2 * math.pi * minutes / 720.0, 2 * math.pi * (minutes % 60) / 60.0
    up = np.array([0.0, 0.0, 1.0])
    faces = [(ts, t_front, (0.0, -1.0)), (ts, t_front + t, (0.0, 1.0)), (ts - t / 2, t_front + t / 2, (-1.0, 0.0)),
             (ts + t / 2, t_front + t / 2, (1.0, 0.0))]
    k = 24
    ang = np.linspace(0.0, 2 * math.pi, k, endpoint=False)
    for s, d, out in faces:
        c2 = fr.xy(s, d)
        nv2 = fr.u * out[0] + fr.n * out[1]
        nv = np.array([nv2[0], nv2[1], 0.0])
        rv = np.cross(-nv, up)
        c = np.array([c2[0], c2[1], zc])

        def at(r, off, a=ang):
            return c + nv * off + rv * (r * np.sin(a))[:, None] + up * (r * np.cos(a))[:, None]

        _fan(mb, at(radius, 0.08), c + nv * 0.08, nv, "dial_white")
        rim_o, rim_i = at(radius + 0.28, 0.14), at(radius, 0.14)    # the stone ring round the dial
        _strip(mb, np.vstack([rim_i, rim_i[:1]]), np.vstack([rim_o, rim_o[:1]]), nv, trim)
        marks = []
        for i in range(12):
            a = 2 * math.pi * i / 12
            dirv = rv * math.sin(a) + up * math.cos(a)
            across = np.cross(dirv, nv)
            wide = 0.06 if i % 3 else 0.1
            p0, p1 = c + nv * 0.1 + dirv * radius * 0.74, c + nv * 0.1 + dirv * radius * 0.9
            marks.append([p0 - across * wide, p1 - across * wide, p1 + across * wide, p0 + across * wide])
        add_quads(mb, IRON, np.array(marks), np.tile(nv, (12, 1)))
        for a, length, width in ((hour_a, 0.55, 0.11), (min_a, 0.85, 0.07)):
            dirv = rv * math.sin(a) + up * math.cos(a)
            base = c + nv * 0.14
            _bar(mb, base - dirv * radius * 0.12, base + dirv * radius * length, width, 0.04, IRON,
                 side=np.cross(dirv, nv))


# --- the platforms ----------------------------------------------------------------------------------

def _platforms(mb: MeshBuilder, fr: Frame, b, height_fn, cfg: dict) -> None:
    """Platforms along the tracks (their tops follow the rails), canopies on posts, the concourse between
    the head building and the buffer stops, and a buffer stop at the end of each track."""
    f = b.facade
    p = dims(cfg, len(f["tracks"]))
    rail_top = float(cfg["bed_lift"]) + float(cfg["rail"][1])
    plat_h = float(cfg["platform"][2])
    ch, crise, gap, over, short = (float(v) for v in cfg["canopy"])
    mat, canopy = str(b.wall), str(b.roof)
    ds = np.linspace(p["back"], p["end"], max(int((p["end"] - p["back"]) / 10.0), 1) + 1)
    level = np.asarray(height_fn(*fr.xy(np.zeros(len(ds)), ds).T), dtype=np.float64) + rail_top
    bundle = p["bundle"] / 2
    _slab(mb, fr, -bundle, bundle, np.array([p["back"], p["stop"] - 0.4]), level[:1].repeat(2) + plat_h,
          level[:1].repeat(2) - 0.8, mat)                   # the concourse along the head building
    for s0, s1 in f["platforms"]:
        _slab(mb, fr, s0, s1, ds, level + plat_h, level - 0.8, mat)
        for s, edge in ((s0 + 0.45, s0 > -bundle + 0.1), (s1 - 0.45, s1 < bundle - 0.1)):
            if edge:                                        # the white safety line along each track edge
                _line(mb, fr, s, ds, level + plat_h + 0.01, 0.12, "road_paint")
        _canopy(mb, fr, (s0 + s1) / 2, (s1 - s0) / 2 + over, ds, level + plat_h, p["back"] + 0.5,
                p["end"] - short, ch, crise, gap, canopy)
    for s in f["tracks"]:                                   # buffer stops
        z = float(level[0]) - rail_top
        add_boxes(mb, [fr.xy(s - 1.3, p["stop"] - 0.9)], [fr.u], 0.0, 2.6, 0.5, z, z + rail_top + 0.75, IRON)
        add_boxes(mb, [fr.xy(s - 1.1, p["stop"] + 0.2)], [fr.u], 0.0, 2.2, 0.25, z + rail_top + 0.45,
                  z + rail_top + 0.85, "door_red")


def _slab(mb: MeshBuilder, fr: Frame, s0: float, s1: float, ds: np.ndarray, top: np.ndarray, bottom: np.ndarray,
          mat: str) -> None:
    """A slab between s0 and s1 along d (samples ds), its top at `top`, sides down to `bottom`, ends closed."""
    _line(mb, fr, (s0 + s1) / 2, ds, top, s1 - s0, mat)
    left, right = fr.xy(np.full(len(ds), s0), ds), fr.xy(np.full(len(ds), s1), ds)
    for pts, out in ((left, -fr.u), (right, fr.u)):
        _strip(mb, np.column_stack([pts, top]), np.column_stack([pts, bottom]), [out[0], out[1], 0.0], mat)
    quads, toward = [], []
    for j, out in ((0, -fr.n), (len(ds) - 1, fr.n)):
        quads.append([[*left[j], bottom[j]], [*right[j], bottom[j]], [*right[j], top[j]], [*left[j], top[j]]])
        toward.append([out[0], out[1], 0.0])
    add_quads(mb, mat, np.array(quads, dtype=np.float64), np.array(toward, dtype=np.float64))


def _line(mb: MeshBuilder, fr: Frame, s: float, ds: np.ndarray, z: np.ndarray, width: float, mat: str) -> None:
    """A flat strip `width` m wide along d at s, at heights z."""
    left, right = fr.xy(np.full(len(ds), s - width / 2), ds), fr.xy(np.full(len(ds), s + width / 2), ds)
    k = len(ds)
    pos = np.vstack([np.column_stack([left, z]), np.column_stack([right, z])])
    i = np.arange(k - 1)
    tris = np.concatenate([np.stack([i, k + i, k + i + 1], 1), np.stack([i, k + i + 1, i + 1], 1)])
    g = np.cross(pos[tris[0, 1]] - pos[tris[0, 0]], pos[tris[0, 2]] - pos[tris[0, 0]])
    if g[2] < 0:
        tris = tris[:, ::-1]
    mb.add(mat, pos, np.tile([0.0, 0.0, 1.0], (2 * k, 1)), np.column_stack([pos[:, 0], -pos[:, 1]]), tris)


def _canopy(mb: MeshBuilder, fr: Frame, sc: float, half: float, ds: np.ndarray, plat: np.ndarray, d0: float,
            d1: float, height: float, rise: float, gap: float, mat: str) -> None:
    """A canopy over a platform: a shallow ridged roof (both faces drawn) on a row of posts along the
    platform's middle, with brackets and an iron valance along both eaves."""
    dd = np.concatenate([[d0], ds[(ds > d0) & (ds < d1)], [d1]])
    base = np.interp(dd, ds, plat)
    eave, ridge = base + height, base + height + rise
    r = fr.xy(np.full(len(dd), sc), dd)
    for sgn in (-1.0, 1.0):
        e = fr.xy(np.full(len(dd), sc + sgn * half), dd)
        n_up = np.array([*(fr.u * sgn * rise), half])
        top_r, top_e = np.column_stack([r, ridge]), np.column_stack([e, eave])
        _strip(mb, top_r, top_e, n_up, mat)                 # the roof sheet, seen from above and below
        _strip(mb, top_r - [0.0, 0.0, 0.06], top_e - [0.0, 0.0, 0.06], -n_up, mat)
        hi, lo = np.column_stack([e, eave - 0.06]), np.column_stack([e, eave - 0.42])
        out = np.array([*(fr.u * sgn), 0.0])
        _strip(mb, hi, lo, out, IRON)                       # the valance under the eave, both faces
        _strip(mb, hi, lo, -out, IRON)
    posts = np.arange(d0 + gap / 2, d1, gap)
    zb = np.interp(posts, ds, plat)
    zt = np.interp(posts, ds, plat) + height + rise - 0.08
    quads, toward = [], []                                  # posts: four faces each, the ends hidden
    for d, z0, z1 in zip(posts, zb, zt):
        c = [fr.xy(sc + a, d + b) for a, b in ((-0.1, -0.1), (0.1, -0.1), (0.1, 0.1), (-0.1, 0.1))]
        for k in range(4):
            p0, p1 = c[k], c[(k + 1) % 4]
            quads.append([[*p0, z0], [*p1, z0], [*p1, z1], [*p0, z1]])
            mid = (p0 + p1) / 2 - fr.xy(sc, d)
            toward.append([mid[0], mid[1], 0.0])
    if quads:
        add_quads(mb, IRON, np.array(quads, dtype=np.float64), np.array(toward, dtype=np.float64))
    beam0, beam1 = fr.xy(sc, d0 + 0.3), fr.xy(sc, d1 - 0.3)     # a beam under the ridge, carried by the posts
    zb0, zb1 = float(np.interp(d0 + 0.3, ds, plat)), float(np.interp(d1 - 0.3, ds, plat))
    _bar(mb, [*beam0, zb0 + height + rise - 0.22], [*beam1, zb1 + height + rise - 0.22], 0.18, 0.28, IRON)


def _strip(mb: MeshBuilder, a: np.ndarray, b: np.ndarray, toward, mat: str) -> None:
    """A strip of quads between two rows of points (k, 3) with shared corners, turned to face `toward`;
    planar meter UVs (top view for flat faces, along the strip for upright ones)."""
    k = len(a)
    pos = np.vstack([a, b])
    i = np.arange(k - 1)
    tris = np.concatenate([np.stack([i, k + i, k + i + 1], 1), np.stack([i, k + i + 1, i + 1], 1)])
    n = np.asarray(toward, dtype=np.float64)
    n = n / max(float(np.linalg.norm(n)), 1e-12)
    g = np.cross(pos[tris[0, 1]] - pos[tris[0, 0]], pos[tris[0, 2]] - pos[tris[0, 0]])
    if float(g @ n) < 0:
        tris = tris[:, ::-1]
    if abs(n[2]) > 0.7:
        uv = np.column_stack([pos[:, 0], -pos[:, 1]])
    else:
        uv = np.column_stack([pos[:, 0] * -n[1] + pos[:, 1] * n[0], -pos[:, 2]])
    mb.add(mat, pos, np.tile(n, (2 * k, 1)), uv, tris)


# --- the tracks -------------------------------------------------------------------------------------

def rail_meshes(mb: MeshBuilder, tc, plan, tile) -> None:
    """The station's tracks inside this tile: a sleeper bed under two rails per track, the rails at a street's
    surface where it crosses (a level crossing). Each track is cut at the tile edges."""
    station = getattr(plan, "station", None)
    cfg = tc.world.style.get("station")
    if station is None or cfg is None:
        return
    ground = tc.ground
    bed, rail_h = float(cfg["bed_lift"]), float(cfg["rail"][1])
    head = float(cfg["rail"][0])
    lift = float(cfg["crossing_lift"])
    spacing = float(cfg["spacing"])
    off = float(cfg["gauge"]) / 2 + head / 2
    for track in station.tracks:
        for seg in _pieces(track.intersection(tile)):
            start = track.project(Point(seg.coords[0]))
            pts = _samples(seg, ground)
            add_ribbon(mb, pts, spacing, ground.drawn, bed, "ballast", start)
            for sgn in (-1.0, 1.0):
                rail = shapely.offset_curve(shapely.LineString(pts), sgn * off)
                if rail.is_empty or rail.geom_type != "LineString":
                    continue
                _rail(mb, np.asarray(rail.coords), ground, bed, rail_h, head, lift)


def _pieces(geom) -> list:
    if geom.is_empty:
        return []
    parts = getattr(geom, "geoms", [geom])
    return [g for g in parts if g.geom_type == "LineString" and g.length > 0.05]


def _samples(seg, ground) -> np.ndarray:
    """Points along a track piece: a point every meter, then only those the track's bends, the ground's
    bends (within 2 cm) and the street edges it crosses need, at most 40 m apart (the station's level
    ground and long straights need few)."""
    fine = shapely.get_coordinates(shapely.segmentize(seg, 1.0))
    on = np.asarray(ground.lift(fine[:, 0], fine[:, 1]), dtype=np.float64) > 0.0
    z = np.asarray(ground.drawn(fine[:, 0], fine[:, 1]), dtype=np.float64)
    pts = np.column_stack([fine, z])
    keep = [0]
    i = 0
    while i < len(fine) - 1:
        j = i + 1
        while j + 1 < len(fine) and on[j + 1] == on[i] and _straight(pts, i, j + 1) and j + 1 - i <= 40:
            j += 1
        keep.append(j)
        i = j
    return fine[np.unique(keep)]


def _straight(pts: np.ndarray, i: int, j: int, tol: float = 0.02) -> bool:
    """True when every point between i and j lies within `tol` m of the straight line from i to j."""
    if j - i < 2:
        return True
    a, b = pts[i], pts[j]
    t = np.linspace(0.0, 1.0, j - i + 1)[1:-1, None]
    return bool(np.all(np.linalg.norm(pts[i + 1:j] - (a + (b - a) * t), axis=1) < tol))


def _rail(mb: MeshBuilder, pts: np.ndarray, ground, bed: float, rail_h: float, head: float, lift: float) -> None:
    """One rail: a thin steel bar with its head `head` m wide, `rail_h` m over the sleeper bed, or flush with
    a street's surface (`lift` m over it) where it crosses one."""
    if len(pts) < 2:
        return
    street = np.asarray(ground.lift(pts[:, 0], pts[:, 1]), dtype=np.float64)
    on = street > 0.0
    top = np.where(on, np.asarray(ground.surface(pts[:, 0], pts[:, 1]), dtype=np.float64) + lift,
                   np.asarray(ground.drawn(pts[:, 0], pts[:, 1]), dtype=np.float64) + bed + rail_h)
    low = np.where(on, top - 0.03, top - rail_h)
    d = np.diff(pts, axis=0)
    t = np.vstack([d, d[-1:]])
    t[1:-1] = d[:-1] + d[1:]
    t /= np.maximum(np.hypot(t[:, 0], t[:, 1]), 1e-9)[:, None]
    n = np.column_stack([-t[:, 1], t[:, 0]]) * head / 2
    k = len(pts)
    left, right = pts + n, pts - n
    pos = np.vstack([np.column_stack([left, low]), np.column_stack([left, top]), np.column_stack([right, top]),
                     np.column_stack([right, low])])
    nn = n / (head / 2)
    nrm = np.vstack([np.column_stack([nn, np.zeros(k)]), np.column_stack([nn * 0.5, np.full(k, 0.85)]),
                     np.column_stack([-nn * 0.5, np.full(k, 0.85)]), np.column_stack([-nn, np.zeros(k)])])
    s = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(pts, axis=0).T))])
    uv = np.column_stack([np.tile(s, 4), np.repeat([0.0, -0.12, -0.19, -0.31], k)])
    i = np.arange(k - 1)
    tris = []
    for a, b in ((0, 1), (1, 2), (2, 3)):                  # the outer side, the head, the inner side
        ia, ib = a * k + i, b * k + i
        tris += [np.stack([ia, ia + 1, ib + 1], 1), np.stack([ia, ib + 1, ib], 1)]
    tris = np.concatenate(tris)
    g = np.cross(pos[tris[2 * (k - 1), 1]] - pos[tris[2 * (k - 1), 0]], pos[tris[2 * (k - 1), 2]] - pos[tris[2 * (k - 1), 0]])
    if g[2] < 0:
        tris = tris[:, ::-1]
    mb.add("rail_steel", pos, nrm, uv, tris)


def rail_zone(plan):
    """The ground no street piece, car, person or tree may stand on: the corridor and the precinct (prepared),
    or None without a station."""
    station = getattr(plan, "station", None)
    if station is None:
        return None
    from ..city.station import cut
    zone = cut(station)
    shapely.prepare(zone)
    return zone


def keep_off(placements: list, zone, kit) -> list:
    """The placements with every piece whose plan box touches the zone left out."""
    if zone is None or not placements:
        return placements
    out = []
    bounds = zone.bounds
    for p in placements:
        piece = kit.pieces.get(p.piece) if kit is not None else None
        if piece is None:
            if _outside(bounds, (p.x, p.y)) or not zone.contains(Point(p.x, p.y)):
                out.append(p)
            continue
        lo, hi = piece.bounds
        x0, x1 = lo[0] * p.stretch * p.scale, hi[0] * p.stretch * p.scale
        y0, y1 = -hi[2] * p.scale, -lo[2] * p.scale
        c, s = math.cos(p.yaw), math.sin(p.yaw)
        corners = [(p.x + x * c - y * s, p.y + x * s + y * c) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))]
        if _outside(bounds, *corners) or not zone.intersects(Polygon(corners)):
            out.append(p)
    return out


def _outside(bounds, *points) -> bool:
    """True when the points' bounding box lies wholly beside the zone's bounds: no shape test needed."""
    xs, ys = [x for x, _ in points], [y for _, y in points]
    zx0, zy0, zx1, zy1 = bounds
    return max(xs) < zx0 or min(xs) > zx1 or max(ys) < zy0 or min(ys) > zy1
