"""Data model of a planned city. Coordinates are world meters (x east, y north)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class District:
    id: int
    kind: str      # medina | village | colonial | modern | residential | suburb | industrial | port | park | cemetery
    name: str
    polygon: object  # shapely Polygon or MultiPolygon
    angle: float = 0.0  # street grid direction, radians counter-clockwise from east


@dataclass
class Street:
    kind: str      # boulevard | arterial | ring | corniche | connector | street | souk | alley
    width: float
    line: object   # shapely LineString (center line)


@dataclass
class Parcel:
    polygon: object
    district: int
    frontage: bool = True  # touches a street


@dataclass
class Building:
    footprint: object  # shapely Polygon, holes are courtyards
    kind: str
    district: int
    height: float      # wall height above the highest ground point, meters
    wall: str          # material names from the style palette
    roof: str
    floors: int = 1
    roof_shape: str = "flat"  # flat | hip
    domes: list = field(default_factory=list)  # [(x, y, radius, material)] sitting on the roof
    top: dict | None = None   # minaret lantern {"side", "height", "material", "cap"}


@dataclass
class Tree:
    x: float
    y: float
    kind: str      # broadleaf | palm | cypress | olive
    height: float


@dataclass
class Landmark:
    kind: str
    name: str
    x: float
    y: float


@dataclass
class CityPlan:
    settlement: object
    boundary: object
    land: object
    medina: object | None
    districts: list
    streets: list
    blocks: list      # [(Polygon, district id)]
    parcels: list
    buildings: list
    trees: list
    landmarks: list
    stats: dict = field(default_factory=dict)
    households: list = field(default_factory=list)  # city/life.py: who lives behind each door
    souks: list = field(default_factory=list)       # city/life.py: the trade of each market street
