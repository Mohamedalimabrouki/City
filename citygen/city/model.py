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
    surface: str = ""  # palette material of the ribbon; style [streets.surface], village = earth


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
class Walk:
    """A raised sidewalk or the boulevard's central promenade, in world meters."""
    kind: str          # sidewalk | promenade
    polygon: object    # shapely Polygon of the raised top
    width: float       # actual width in meters (after narrowing at tight streets)
    street: int = -1   # nearest street; the boulevard for a promenade
    side: int = 0      # +1 left of the street line, -1 right, 0 the middle (promenade)
    district: int = -1 # district of the block behind a sidewalk
    block: int = -1    # index in CityPlan.blocks


@dataclass
class Paint:
    """One painted road marking: a flat polygon over the carriageway."""
    polygon: object   # shapely Polygon in world meters
    street: int       # index in CityPlan.streets


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
    walks: list = field(default_factory=list)       # city/walks.py: raised sidewalks and promenades
    stats: dict = field(default_factory=dict)
    households: list = field(default_factory=list)  # city/life.py: who lives behind each door
    souks: list = field(default_factory=list)       # city/life.py: the trade of each market street
    paint: list = field(default_factory=list)       # city/paint.py: road markings
