"""Floors, ceilings, the roof deck and the court of an interior (SPEC 6c "Floors and ceilings", prompt 49).

A slab per level (`[interiors.floors] slab` thick, its top at the floor's z) spans the storey and the ceiling
of the storey under it, less the holes the stairs need (`stairs.well`), a covered court's light well and,
in the roof deck, the skylight and a koubba's dome. Where a slab or a landing would still cross an exterior,
court or roof opening, it stops `slot` m short of that wall over the opening's width + 0.2 m (a light slot).
Each room draws its own floor finish and ceiling from its free floor (`mesh.free`): tiles and painted beams
(stream `beams`) in traditional houses, terrazzo and plaster elsewhere. The flat roofs replace the tile's
`roof_mesh` (`roof`): the deck with its wells, the tile's parapet coping, the roof rooms' caps and ceilings
(their walls come with the other walls, `mesh.walls_mesh`). The court is paved `court_step` m under floor 0
with its majel, fesqiya and trees on the paving.
"""
from __future__ import annotations

import numpy as np
from shapely.geometry import Point
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

from ..city.geo import polygons
from ..mesh.builder import add_cap, add_dome, add_walls, regular_polygon
from ..mesh.furniture import _lathe
from ..mesh.tile import _coping
from ..rng import stream
from . import rooms as R
from . import stairs as S
from .cuts import Frame
from .layout import TRADITIONAL

TOL = 0.01          # meters: a slab this near an opening's sill or head does not cross it
ROOF_ROOMS = ("droj", "menzah")


def settings(style: dict) -> tuple:
    """([interiors.floors], [interiors.stairs], [interiors.openings]) of the style."""
    cfg = style.get("interiors", {})
    return cfg.get("floors", {}), cfg.get("stairs", {}), cfg.get("openings", {})


# --- geometry: holes, slots, slabs ---------------------------------------------------------------------
def free_of(interior, room):
    """A room's floor less every other room of its floor grown by half a partition (a light well less its
    walls and balustrades)."""
    half = interior.walls["partition"] / 2
    others = [r.polygon for r in interior.rooms if r.floor == room.floor and r is not room]
    if not others:
        return room.polygon
    return room.polygon.difference(unary_union(others).buffer(half, join_style="mitre"))


def domes(interior, outside, fl: dict) -> list:
    """(x, y, inner radius, room) of each koubba on the top floor under a dome of the building."""
    out = []
    b = outside.b
    wall = float(fl.get("dome_wall", 0.25))
    for r in interior.rooms:
        if r.type != "koubba" or r.floor != interior.floors - 1:
            continue
        for x, y, rad, _ in b.domes:
            if r.polygon.contains(Point(x, y)) and rad > wall + 0.5:
                out.append((float(x), float(y), float(rad) - wall, r))
                break
    return out


def wells(interior, f: int, style: dict, outside=None) -> list:
    """The holes in the slab of level f (f = floors: the roof deck): the stairs' wells, the light well of a
    covered court; in the deck the skylight and the koubba's dome."""
    fl, st, _ = settings(style)
    out = []
    for s in interior.stairs:
        w = S.well(s, f, interior, st)
        if w is not None and not w.is_empty:
            out.append(w)
    if 0 < f < interior.floors:
        out += [free_of(interior, r) for r in interior.rooms if r.floor == f and r.type == "well"]
    if f == interior.floors:
        for o in interior.openings:
            if o.kind == "skylight":
                room = next((r for r in interior.rooms if r.id == o.rooms[0]), None)
                if room is not None:
                    out.append(free_of(interior, room))
        if outside is not None:
            out += [regular_polygon(x, y, r, 12) for x, y, r, _ in domes(interior, outside, fl)]
    return [w for w in out if not w.is_empty]


def base(interior, f: int):
    """What the slab of level f spans: floor 0; the storey under it and the storey on it; the top storey
    for the roof deck."""
    st = interior.storeys
    if f == 0:
        return st[0].polygon
    return unary_union([st[f - 1].polygon] + ([st[f].polygon] if f < len(st) else []))


def crosses(interior, o, plate, top: float, thick: float, fl: dict, st: dict) -> bool:
    """True when a slab or landing (`plate` from top - thick to top) passes behind the opening: through the
    0.1 m just inside its wall over its width and between its sill and head. A door's own floor may stand up
    to `threshold` over its sill (the step inside a door)."""
    if o.kind == "skylight" or (o.wall is None and o.kind not in ("door", "window", "balcony", "shop")
                                and o.floor < interior.floors):
        return False
    if top <= o.z0 + TOL or top - thick >= o.z1 - TOL:
        return False
    if abs(top - S.level(interior, o.floor)) < TOL and top - o.z0 <= float(st.get("threshold", 0.15)) + TOL:
        return False
    zone = _zone(interior, o, o.width / 2, -0.1, -0.005)
    return plate.intersection(zone).area > 1e-4


def _zone(interior, o, half: float, d0: float, d1: float):
    """The rectangle from d0 to d1 m past the room-side face of an opening's wall, `half` m each way."""
    from .mesh import _rect, depths, frame_of
    c, front, along = frame_of(o)
    face = depths(interior, o)[0]
    return _rect(c, front, along, -half, half, face + d0, face + d1)


def slots(interior, region, top: float, thick: float, fl: dict, st: dict) -> list:
    """The light slots a plate needs: `slot` m from the wall over each opening it would cross + 0.2 m."""
    slot = float(fl.get("slot", 0.3))
    return [_zone(interior, o, o.width / 2 + 0.1, -slot, 0.05) for o in interior.openings
            if crosses(interior, o, region, top, thick, fl, st)]


def slab(interior, f: int, style: dict, outside=None):
    """The slab of level f: its span less the wells and the light slots."""
    fl, st, _ = settings(style)
    region = base(interior, f)
    holes = wells(interior, f, style, outside)
    if holes:
        region = region.difference(unary_union(holes))
    z, thick = S.level(interior, f), float(fl.get("slab", 0.25))
    cut = slots(interior, region, z, thick, fl, st)
    return region.difference(unary_union(cut)) if cut else region


def plates(interior, style: dict, outside=None) -> list:
    """Every horizontal plate as `stairs.Part`s: the slabs of levels 1 to floors (the roof deck), the stairs'
    landings and steps (the landings stopped short of openings), the pier."""
    fl, st, _ = settings(style)
    thick = float(fl.get("slab", 0.25))
    out = []
    for f in range(1, interior.floors + 1):
        z = S.level(interior, f)
        out += [S.Part(p, z - thick, z, "slab") for p in polygons(slab(interior, f, style, outside))]
    for s in interior.stairs:
        for p in S.parts(s, interior, st, fl):
            if p.kind == "landing":
                cut = slots(interior, p.poly, p.z1, p.z1 - p.z0, fl, st)
                p.poly = p.poly.difference(unary_union(cut)) if cut else p.poly
            out.append(p)
    return out


def overheads(interior, style: dict, outside=None) -> list:
    """Everything a person on a stair may hit overhead, as `stairs.Part`s: every slab with its wells, every
    landing and flight, the roof rooms' ceilings and the beams."""
    fl, _, _ = settings(style)
    out = plates(interior, style, outside)
    c = float(fl.get("roof_room_ceiling", 0.15))
    for r in interior.rooms:
        if r.floor == interior.floors and r.type in ROOF_ROOMS:
            out.append(S.Part(r.polygon, r.z + r.height - c, r.z + r.height, "ceiling"))
    for f in range(interior.floors):
        for room, poly, z in ceilings(interior, f, style, outside):
            out += [S.Part(p, z0, z1, "beam") for p, z0, z1, _ in beams(interior, room, poly, z, fl)]
    return out


def ceilings(interior, f: int, style: dict, outside=None) -> list:
    """(room, ceiling polygon, z) of every covered room of floor f: its free floor under the next slab."""
    from .mesh import free
    fl, _, _ = settings(style)
    above = slab(interior, f + 1, style, outside)
    z = S.level(interior, f + 1) - float(fl.get("slab", 0.25))
    out = []
    for room, parts, _ in free(interior, f, interior.walls["partition"] / 2):
        if room.open and room.type != "well":
            continue
        poly = unary_union(parts).intersection(above) if parts else None
        if poly is not None and poly.area > 1e-3:
            out.append((room, poly, z))
    return out


def beams(interior, room, poly, z: float, fl: dict) -> list:
    """(polygon, z0, z1, material) of the painted beams under a traditional room's ceiling: across its
    shorter span every `beam_step` m, their color on stream `beams` (one per room)."""
    if interior.layout not in TRADITIONAL or room.type not in fl.get("beam_rooms", ()):
        return []
    colors = list(fl.get("beam_colors", ["door_frame"]))
    rng = stream(interior.seed, "interior", interior.city_id, interior.building, "beams", room.id)
    mat = colors[int(rng.integers(len(colors)))]
    width, depth = (float(v) for v in fl.get("beam", [0.1, 0.12]))
    step = float(fl.get("beam_step", 0.45))
    fr = Frame.of(poly)
    u0, v0, u1, v1 = fr.bounds(poly)
    n = int((u1 - u0) // step)
    out = []
    start = (u0 + u1) / 2 - (n - 1) * step / 2
    for i in range(n):
        u = start + i * step
        for p in polygons(poly.intersection(fr.rect(u - width / 2, v0 - 1.0, u + width / 2, v1 + 1.0))):
            if p.area > 1e-3:
                out.append((p, z - depth, z, mat))
    return out


# --- drawing --------------------------------------------------------------------------------------------
def finish(interior, fl: dict, key: str) -> str:
    """The material of a floor (`finish`) or of stair steps (`steps`): traditional or modern."""
    kind = "traditional" if interior.layout in TRADITIONAL else "modern"
    return str(fl.get(key, {}).get(kind, "plaster_inner"))


def floors_mesh(mb, interior, outside, style: dict) -> None:
    """Each room's floor finish over its slab, the slab's edges round its holes, each covered room's ceiling
    (with painted beams in a traditional room), a koubba's dome from inside, and the court."""
    from .mesh import free
    fl, _, _ = settings(style)
    thick = float(fl.get("slab", 0.25))
    half = interior.walls["partition"] / 2
    mat = finish(interior, fl, "finish")
    for f in range(interior.floors):
        z = S.level(interior, f)
        region = slab(interior, f, style, outside)
        frees = free(interior, f, half)
        for room, parts, _ in frees:
            if room.type == "well" or R.is_court(room):
                continue
            zf = room.z if room.z < z - TOL else z        # a sunken entry room (47.1) lies under floor 0
            for p in polygons(unary_union(parts).intersection(region)) if parts else []:
                add_cap(mb, p, zf, mat)
        if f > 0:
            edges(mb, region, base(interior, f), faced(interior, f - 1, half), z - thick, z)
        for room, poly, zc in ceilings(interior, f, style, outside):
            beamed = beams(interior, room, poly, zc, fl)
            for p in polygons(poly):
                add_cap(mb, p, zc, "ceiling_boards" if beamed else "plaster_inner", up=False)
            for p, z0, z1, m in beamed:
                add_walls(mb, p.exterior.coords, z0, z1, m, z0)
                add_cap(mb, p, z0, m, up=False)
    for x, y, r, room in domes(interior, outside, fl):
        dome_inside(mb, interior, outside, x, y, r, fl)
    court(mb, interior, outside, fl)


def faced(interior, f: int, half: float):
    """The lines of floor f's drawn wall faces (each room's free floor less the edges onto a room it has no
    wall to), grown 1 mm: a slab edge on them is hidden in the wall."""
    from .mesh import free
    lines = []
    for room, parts, loose in free(interior, f, half):
        for p in parts:
            line = p.boundary
            if loose is not None:
                line = line.difference(loose.buffer(1e-3))
            lines.append(line)
    return unary_union(lines).buffer(1e-3) if lines else None


def edges(mb, region, span, hidden, z0: float, z1: float, mat: str = "plaster_inner") -> None:
    """The vertical faces of a slab round its holes, seen from the hole: every edge of `region` that is not
    on its span's outline (the wall's inner face) nor on a wall face of the floor below."""
    from .mesh import Face, draw
    outline = span.boundary.buffer(1e-3)
    for p in polygons(region):
        p = orient(p, 1.0)                               # the slab on each edge's left, the hole on its right
        for ring in (p.exterior, *p.interiors):
            pts = np.asarray(ring.coords)[:, :2]
            for a, b in zip(pts[:-1], pts[1:]):
                if float(np.hypot(*(b - a))) < 1e-4:
                    continue
                mid = Point(*((a + b) / 2))
                if outline.contains(mid) or (hidden is not None and hidden.contains(mid)):
                    continue
                draw(mb, Face(a.copy(), b.copy(), z0, z1, mat, 0.0, z1, -1))


def dome_inside(mb, interior, outside, x: float, y: float, r: float, fl: dict) -> None:
    """A koubba's ceiling is its dome: the drum's inner face from the ceiling up and the dome over it."""
    from .mesh import Face, draw
    z = S.level(interior, interior.floors)
    rad = r + float(fl.get("dome_wall", 0.25))
    top = z + 0.18 * rad                              # the tile's drum (`building_tops`)
    ring = np.asarray(regular_polygon(x, y, r, 12).exterior.coords)[:, :2]
    for a, c in zip(ring[::-1][:-1], ring[::-1][1:]):  # walked clockwise: seen from inside
        draw(mb, Face(a.copy(), c.copy(), z - float(fl.get("slab", 0.25)), top, "plaster_inner", 0.0, top, -1))
    add_dome(mb, x, y, top, r, "plaster_inner", inside=True)


def court(mb, interior, outside, fl: dict) -> None:
    """The court's paving `court_step` m under floor 0, the majel (a stone curb with a wooden lid) and the
    fesqiya (an octagonal marble basin of `water_pool`)."""
    room = next((r for r in interior.rooms if R.is_court(r) and r.floor == 0), None)
    if room is None:
        return
    z = paving_z(interior, fl)
    for p in polygons(room.polygon):
        add_cap(mb, p, z, str(fl.get("court", "paving")))
    across, high = (float(v) for v in fl.get("majel", [0.6, 0.4]))
    width = float(fl.get("fesqiya", 1.4)) / 2
    for feat in interior.features:
        at = _At(mb, feat["x"], feat["y"], z)
        if feat["type"] == "majel":
            r = across / 2
            _lathe(at, [(r, 0.0), (r, high), (r - 0.08, high), (r - 0.08, high - 0.05)], "step_stone", 16)
            _lathe(at, [(r - 0.08, high - 0.05), (0.0, high - 0.05)], "door_leaf", 16)
        elif feat["type"] == "fesqiya":
            rim = width - 0.12
            _lathe(at, [(width, 0.0), (width, 0.45), (rim, 0.45), (rim, 0.12)], "marble", 8)
            _lathe(at, [(rim, 0.35), (0.0, 0.35)], "water_pool", 8)
            _lathe(at, [(0.09, 0.35), (0.07, 0.62), (0.16, 0.68), (0.0, 0.72)], "marble", 8)


def paving_z(interior, fl: dict) -> float:
    """The court's paving: `court_step` m under floor 0."""
    return S.level(interior, 0) - float(fl.get("court_step", 0.15))


class _At:
    """A MeshBuilder stand-in that moves what is added to (x, y, z)."""

    def __init__(self, mb, x: float, y: float, z: float):
        self.mb, self.d = mb, np.array([x, y, z])

    def add(self, material, pos, nrm, uv, tris, col=None) -> None:
        self.mb.add(material, np.asarray(pos, dtype=np.float64) + self.d, nrm, uv, tris)


# --- the roof ---------------------------------------------------------------------------------------------
def roof_drawer(interior, outside, style: dict):
    """A `building_tops` `flat` drawer: the deck less its wells (with their edges), the tile's parapet
    coping, the roof rooms' caps and ceilings and the skylight's curb and glass."""
    fl, _, _ = settings(style)
    thick = float(fl.get("slab", 0.25))
    half = interior.walls["partition"] / 2

    def draw_roof(mb, b, lay, z, roof=None) -> None:
        if lay is None or lay.band is None:
            return
        roof = b.roof if roof is None else roof
        f = int(round((z - interior.high) / interior.fh))
        holes = [h for h in wells(interior, f, style, outside) if h.intersects(lay.inner)] if f >= 1 else []
        deck = lay.inner.difference(unary_union(holes)) if holes else lay.inner
        for p in polygons(deck):
            add_cap(mb, p, z, roof)
        if holes and 1 <= f <= interior.floors:
            edges(mb, deck, lay.inner, faced(interior, f - 1, half), z - thick, z)
        for band in polygons(lay.band):
            _coping(mb, b, band, z, z + lay.height, roof)
        for r in interior.rooms:
            if r.floor == interior.floors and r.type in ROOF_ROOMS and abs(r.z - z) < TOL:
                add_cap(mb, r.polygon, z + r.height, roof)
                inner = r.polygon.buffer(-interior.walls.get("roof", 0.2), join_style="mitre")
                for p in polygons(inner):
                    add_cap(mb, p, z + r.height - float(fl.get("roof_room_ceiling", 0.15)), "plaster_inner", up=False)
        if f == interior.floors:
            skylight(mb, interior, b, z, fl)

    return draw_roof


def skylight(mb, interior, b, z: float, fl: dict) -> None:
    """The skylight over a covered court: a curb round its hole and a glass panel on it."""
    curb = float(fl.get("skylight_curb", 0.2))
    for o in interior.openings:
        if o.kind != "skylight":
            continue
        room = next((r for r in interior.rooms if r.id == o.rooms[0]), None)
        if room is None:
            continue
        hole = free_of(interior, room)
        for p in polygons(hole):
            ring = p.buffer(0.1, join_style="mitre").difference(p)
            for q in polygons(ring):
                add_walls(mb, q.exterior.coords, z, z + curb, b.wall, z)
                for h in q.interiors:
                    add_walls(mb, h.coords, z - float(fl.get("slab", 0.25)), z + curb, "plaster_inner", z)
                add_cap(mb, q, z + curb, b.roof or "roof_white")
            add_cap(mb, p, z + curb - 0.02, "glass_inner")


def roof_faces(interior, outside, style: dict) -> list:
    """The walls of the roof rooms (the stair room, the menzah) as `mesh.Face`s: the outer faces where the
    tile draws its solid box (`[roofs]` wall), the inner faces `roof_wall` m in, up to the ceiling."""
    from .mesh import Face
    fl, _, _ = settings(style)
    t, c = interior.walls.get("roof", 0.2), float(fl.get("roof_room_ceiling", 0.15))
    out = []
    for r in interior.rooms:
        if r.floor != interior.floors or r.type not in ROOF_ROOMS:
            continue
        for p in polygons(r.polygon):
            pts = np.asarray(p.exterior.coords)[:, :2]
            if _signed(pts) < 0:
                pts = pts[::-1]
            u = 0.0
            for a, b in zip(pts[:-1], pts[1:]):
                out.append(Face(a.copy(), b.copy(), r.z, r.z + r.height, outside.b.wall, u, r.z, interior.floors))
                u += float(np.hypot(*(b - a)))
        for p in polygons(r.polygon.buffer(-t, join_style="mitre")):
            pts = np.asarray(p.exterior.coords)[:, :2]
            if _signed(pts) > 0:
                pts = pts[::-1]                          # clockwise: each face seen from inside
            u = 0.0
            for a, b in zip(pts[:-1], pts[1:]):
                out.append(Face(a.copy(), b.copy(), r.z, r.z + r.height - c, "plaster_inner", u, r.z, interior.floors))
                u += float(np.hypot(*(b - a)))
    return out


def _signed(pts: np.ndarray) -> float:
    """Twice the signed area of a closed ring (positive: counter-clockwise)."""
    x, y = pts[:, 0], pts[:, 1]
    return float(np.sum(x[:-1] * y[1:] - x[1:] * y[:-1]))


def ladders(mb, interior, fl: dict) -> None:
    """Every ladder: two wooden rails leaning along its footprint and a rung per riser."""
    for s in interior.stairs:
        if s.kind != "ladder":
            continue
        foot, head, across, z1 = S.ladder_line(s, interior, fl)
        half = s.width / 2 - 0.03
        for side in (-half, half):
            off = np.array([*(across * side), 0.0])
            bar(mb, foot + off, head + off, 0.05, "door_frame")
        n = max(1, int(round((z1 - foot[2]) / max(s.riser, 1e-6))))
        for k in range(1, n + int((head[2] - z1) // max(s.riser, 1e-6)) + 1):
            zk = foot[2] + k * (z1 - foot[2]) / n
            if zk > head[2] - 0.05:
                break
            p = foot + (head - foot) * (zk - foot[2]) / (head[2] - foot[2])
            bar(mb, p - np.array([*(across * half), 0.0]), p + np.array([*(across * half), 0.0]), 0.03, "door_frame")


def bar(mb, p, q, w: float, mat: str, depth: float | None = None) -> None:
    """A bar `w` m wide (and `depth` m deep, square without) from point p to point q, four sides, open ends."""
    p, q = np.asarray(p, dtype=np.float64), np.asarray(q, dtype=np.float64)
    d = q - p
    length = float(np.linalg.norm(d))
    if length < 1e-6:
        return
    d = d / length
    side = np.cross(d, [0.0, 0.0, 1.0])
    if np.linalg.norm(side) < 1e-6:
        side = np.array([1.0, 0.0, 0.0])
    side = side / np.linalg.norm(side) * w / 2
    up = np.cross(side / np.linalg.norm(side), d) * (w if depth is None else depth) / 2
    corners = [side + up, -side + up, -side - up, side - up]
    pos, nrm, tris = [], [], []
    for i in range(4):
        a, b = corners[i], corners[(i + 1) % 4]
        n = (a + b) / np.linalg.norm(a + b)        # outward (the faces of a deep bar are near enough)
        base_i = len(pos)
        pos += [p + a, p + b, q + b, q + a]
        nrm += [n] * 4
        tris += [[base_i, base_i + 2, base_i + 1], [base_i, base_i + 3, base_i + 2]]
    pos = np.array(pos)
    uv = np.column_stack([pos[:, 0] + pos[:, 1], -pos[:, 2]])
    mb.add(mat, pos, np.array(nrm), uv, np.array(tris))


def railing(mb, line: list, h: float, step: float, mat: str = "iron") -> None:
    """An iron railing along a polyline of hand-rail points: the rail and a baluster every `step` m down
    to `h` m under it."""
    pts = np.asarray(line, dtype=np.float64)
    for a, b in zip(pts[:-1], pts[1:]):
        bar(mb, a, b, 0.04, mat)
        run = float(np.hypot(*(b[:2] - a[:2])))
        n = max(1, int(run // step))
        for i in range(n + 1):
            p = a + (b - a) * (i / n)
            bar(mb, p - np.array([0.0, 0.0, h]), p, 0.016, mat)
