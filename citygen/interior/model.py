"""The data of one interior (SPEC 6c "Data model"): storeys, rooms, openings, stairs and flats.

World meters (x east, y north, z up, absolute heights), as plan.json and the tiles. Polygons are shapely
Polygons here; `Interior.to_json()` writes them as rings of [x, y] rounded to 1 mm (rooms.json).
"""
from __future__ import annotations

from dataclasses import dataclass, field

FORMAT = "citygen-interior/1"


def _r(v) -> float:
    return round(float(v), 3)


def _xy(p) -> list:
    return [_r(p[0]), _r(p[1])]


def rings(poly) -> list | None:
    """A Polygon as [exterior, *holes], each ring a list of [x, y] rounded to 1 mm (None stays None)."""
    if poly is None:
        return None
    return [[_xy(p) for p in ring.coords] for ring in (poly.exterior, *poly.interiors)]


@dataclass
class Storey:
    floor: int
    z: float          # the floor's top, absolute
    height: float     # floor to floor, meters
    polygon: object   # inside the exterior walls (courtyards are holes)

    def to_json(self) -> dict:
        return {"floor": self.floor, "z": _r(self.z), "height": _r(self.height), "polygon": rings(self.polygon)}


@dataclass
class Room:
    id: int
    floor: int
    type: str         # bit, skifa, salon... (SPEC 6c terms, lower case, "_" for spaces); `room` for a placeholder
    polygon: object
    z: float
    height: float
    unit: str = "home"   # home | flat <n> | shop | cafe | common
    open: bool = False   # no ceiling (wast ed dar, stah)
    alcove: object = None   # the kbou: a part of its bit's polygon
    lit: bool = False    # one of its facade windows is lit in the tile

    def to_json(self) -> dict:
        return {"id": self.id, "floor": self.floor, "type": self.type, "polygon": rings(self.polygon),
                "z": _r(self.z), "height": _r(self.height), "unit": self.unit, "open": self.open,
                "alcove": rings(self.alcove), "lit": self.lit}


@dataclass
class Opening:
    id: int
    kind: str         # door, window, balcony, shop (facade); inner, court_door, court_window, inner_window, arch, skylight
    x: float          # center of the hole on its wall
    y: float
    yaw: float        # the piece's yaw: its front faces (-sin yaw, cos yaw), out of the building
    width: float
    z0: float         # sill, absolute
    z1: float         # head, absolute
    floor: int
    rooms: tuple      # (inside room id, other room id or -1 for the street, the ground or the roof)
    wall: tuple | None = None   # ((ax, ay), (bx, by)) of its exterior or court wall; None for inner openings
    s: float = 0.0    # meters from the wall segment's start to the center
    piece: str = ""   # the kit piece of a facade opening
    lit: bool = False

    def to_json(self) -> dict:
        wall = None if self.wall is None else [_xy(self.wall[0]), _xy(self.wall[1])]
        return {"id": self.id, "kind": self.kind, "x": _r(self.x), "y": _r(self.y), "yaw": round(float(self.yaw), 5),
                "width": _r(self.width), "z0": _r(self.z0), "z1": _r(self.z1), "floor": self.floor,
                "rooms": list(self.rooms), "wall": wall, "s": _r(self.s), "piece": self.piece, "lit": self.lit}


@dataclass
class Stair:
    kind: str         # newel | u | steps | ladder
    polygon: object
    floor: int        # from this floor ...
    top: int          # ... to this one (the floor count for the roof)
    risers: int
    riser: float
    tread: float
    width: float
    door: tuple | None = None   # (x, y, yaw) of a newel cell's door side
    rooms: list = field(default_factory=list)   # its room on each floor it serves

    def to_json(self) -> dict:
        door = None if self.door is None else [_r(self.door[0]), _r(self.door[1]), round(float(self.door[2]), 5)]
        return {"kind": self.kind, "polygon": rings(self.polygon), "floor": self.floor, "top": self.top,
                "risers": self.risers, "riser": _r(self.riser), "tread": _r(self.tread), "width": _r(self.width),
                "door": door, "rooms": list(self.rooms)}


@dataclass
class Flat:
    id: int
    floor: int
    type: str         # S+1, S+2, S+3
    rooms: list
    household: dict | None   # as plan.json households
    plan: bool = False       # true for the plan's own household (flat 0)

    def to_json(self) -> dict:
        return {"id": self.id, "floor": self.floor, "type": self.type, "rooms": list(self.rooms),
                "household": self.household, "plan": self.plan}


@dataclass
class Interior:
    seed: int
    city: str
    city_id: int
    building: int
    kind: str
    layout: str
    district: str
    high: float       # highest ground under the footprint ring: floor 0 stands there
    fh: float         # floor height
    household: dict | None
    walls: dict       # thicknesses used: exterior, court, partition
    storeys: list = field(default_factory=list)
    rooms: list = field(default_factory=list)
    openings: list = field(default_factory=list)
    stairs: list = field(default_factory=list)
    flats: list = field(default_factory=list)
    features: list = field(default_factory=list)   # dicts with a type and a position (majel, tree, fesqiya, skylight)
    warnings: list = field(default_factory=list)

    @property
    def floors(self) -> int:
        return len(self.storeys)

    def to_json(self) -> dict:
        """rooms.json (`citygen-interior/1`)."""
        return {"format": FORMAT, "seed": self.seed, "city": self.city, "city_id": self.city_id,
                "building": self.building, "kind": self.kind, "layout": self.layout, "district": self.district,
                "household": self.household, "high": _r(self.high), "floor_height": _r(self.fh),
                "walls": {k: _r(v) for k, v in self.walls.items()},
                "storeys": [s.to_json() for s in self.storeys], "rooms": [r.to_json() for r in self.rooms],
                "openings": [o.to_json() for o in self.openings], "stairs": [s.to_json() for s in self.stairs],
                "flats": [f.to_json() for f in self.flats], "features": list(self.features),
                "warnings": list(self.warnings)}
