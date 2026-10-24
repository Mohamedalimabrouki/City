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
    kind: str      # boulevard | arterial | ring | corniche | connector | street | souk | alley | impasse
    width: float
    line: object   # shapely LineString (center line); an impasse runs from its mouth to its dead end
    surface: str = ""  # palette material of the ribbon; style [streets.surface], village = earth
    covered: float = 0.0  # impasse: meters covered by a room (a sabat) from the mouth inward


@dataclass
class Parcel:
    polygon: object
    district: int
    frontage: bool = True  # touches a street (or, after city/impasses.py, an impasse reaches it)
    block: int = -1        # index in CityPlan.blocks


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
    top: dict | None = None   # minaret lantern {"side", "height", "material", "cap"}; a colonial corner
                              # dome or turret adds "x", "y", "shape": "drum" (city/massing.py)
    # massing (prompt 23, city/massing.py): what makes a building more than one box
    setback: object = None    # footprint of a top floor standing back from the street walls (a Polygon)
    steps: list = field(default_factory=list)     # [(polygon, floors, roof_shape, roof)] parts of the
                              # footprint with their own floor count and roof (a stepped slab, a villa's L)
    machines: list = field(default_factory=list)  # roof machinery [{"kind", "x", "y", "angle", "length",
                              # "width", "height", "z"}]: "lift" motor rooms (drawn), "tank" stands (a piece)
    menzah: bool = False      # a small roof room, placed by roof_layout (old-town courtyard houses)
    corners: list = field(default_factory=list)   # [(x, y, "chamfer" | "round", reach)]: street corners
                              # cut, at the old corner point
    apron: object = None      # the lot corner a cut leaves open, paved like the sidewalk (a Polygon or
                              # MultiPolygon inside the block, drawn by the tile owning the building)
    # fortifications and openings (prompt 30, city/kasbah.py)
    battlement: dict | None = None  # {"chains": [[(x, y), ...]], "breast", "merlon": [width, gap, height],
                              # "depth"}: a breastwork with merlons on the roof edge along each chain (the
                              # building's inside to the left; a chain closed when its first point is its last)
    arches: list = field(default_factory=list)    # [(x, y, yaw, width, height, sill, frame, material)]:
                              # horseshoe-arched gates, doors and windows on a wall face (yaw = outward
                              # normal), with a stone frame band `frame` m wide; `sill` 0 stands on the ground
                              # at the spot, a window's sill is measured from the highest ground (as floors)
    # landmarks of the boulevard (prompt 32, city/landmarks.py)
    facade: dict | None = None  # a cathedral's or theatre's front: {"x", "y"} middle of the front on the street
                              # edge, "yaw" (outward, toward the street), "width", "depth" (behind the steps),
                              # "steps" (meters of front steps), a cathedral's tower "cap"; no car parks before it


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
    width: float       # actual width in meters (after narrowing at tight streets) along `street`
    street: int = -1   # nearest street; the boulevard for a promenade. A sidewalk wraps its whole
                       # block, so `street`, `side` and `width` hold for one side only: measure the
                       # other streets with `parking.walk_extents` (prompt 25)
    side: int = 0      # +1 left of the street line, -1 right, 0 the middle (promenade)
    district: int = -1 # district of the block behind a sidewalk
    block: int = -1    # index in CityPlan.blocks


@dataclass
class Paint:
    """One painted road marking: a flat polygon over the carriageway."""
    polygon: object   # shapely Polygon in world meters
    street: int       # index in CityPlan.streets
    kind: str = "line"   # line (edge, lane and center lines) | crossing (a zebra bar)


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
    station: object = None    # city/station.py: the railway station's tracks, precinct and corridor (prompt 33)
