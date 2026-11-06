"""Data model of a planned city. Coordinates are world meters (x east, y north)."""
from __future__ import annotations

from dataclasses import dataclass, field, replace

import numpy as np
import shapely
from shapely.ops import substring


@dataclass
class District:
    id: int
    kind: str      # medina | village | colonial | modern | residential | suburb | industrial | port | park | cemetery
    name: str
    polygon: object  # shapely Polygon or MultiPolygon
    angle: float = 0.0  # street grid direction, radians counter-clockwise from east
    history: str = ""   # city/history.py: two to four sentences for stories (prompt 81)
    name_ar: str = ""   # the name in Arabic script ("" when the style or a pin gives none)

    def __post_init__(self):
        # a Name from citygen.names carries its Arabic spelling; the plan keeps plain strings
        if not self.name_ar:
            self.name_ar = getattr(self.name, "ar", "")
        self.name = str(self.name)


@dataclass
class Street:
    kind: str      # boulevard | arterial | ring | corniche | connector | street | souk | alley | impasse | bridge
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
    name_ar: str = ""

    def __post_init__(self):
        # a Name from citygen.names carries its Arabic spelling; the plan keeps plain strings
        if not self.name_ar:
            self.name_ar = getattr(self.name, "ar", "")
        self.name = str(self.name)


@dataclass
class Prop:
    """A piece the planner places itself (prompt 35, city/moorings.py): boats, cranes, rails, cargo."""
    kind: str      # a kit piece: boat_lateen | boat_cabin | boat_rowing | boat_trawler | crane_0 | crane_1 |
                   # crane_rails | cargo_crates | cargo_containers_0 | cargo_containers_1
    x: float
    y: float
    yaw: float     # radians: the piece's +x (a boat's bow) turns to (cos yaw, sin yaw)
    scale: float = 1.0
    on: str = "sea"    # sea: floats, waterline at z = 0 | quay: on the quay top | beach: drawn up on the sand


@dataclass
class Walk:
    """A raised sidewalk or the boulevard's central promenade, in world meters."""
    kind: str          # sidewalk | promenade | seafront (the corniche's, prompt 36) | riverside (prompt 61)
    polygon: object    # shapely Polygon of the raised top
    width: float       # actual width in meters (after narrowing at tight streets) along `street`
    street: int = -1   # nearest street; the boulevard for a promenade. A sidewalk wraps its whole
                       # block, so `street`, `side` and `width` hold for one side only: measure the
                       # other streets with `parking.walk_extents` (prompt 25)
    side: int = 0      # +1 left of the street line, -1 right, 0 the middle (promenade)
    district: int = -1 # district of the block behind a sidewalk
    block: int = -1    # index in CityPlan.blocks
    edge: object = None  # seafront (prompt 36): its stretch's curb line; the top is level across, at the curb


@dataclass
class Front:
    """A stretch of the corniche's seafront promenade (prompt 36, city/corniche.py), from station to station."""
    street: int        # the corniche
    side: int          # +1: the sea lies left of the street line, -1: right
    district: int      # the district on the land side
    edge: object       # LineString: the curb (street side), along the street's direction
    sea: object        # LineString: the sea wall's top edge, point for point opposite `edge`
    span: tuple        # (start, end) meters along the street line
    stairs: list = field(default_factory=list)  # [(x, y, ux, uy)]: flights down to the beach, at the sea edge,
                       # (ux, uy) pointing out to sea
    beach: float = 0.0 # meters of the stretch with at least `beach_min` m of sand beyond the wall


@dataclass
class Paint:
    """One painted road marking: a flat polygon over the carriageway."""
    polygon: object   # shapely Polygon in world meters
    street: int       # index in CityPlan.streets
    kind: str = "line"   # line (edge, lane and center lines) | crossing (a zebra bar)


@dataclass
class Bridge:
    """A bridge or a ford, all a mesher needs (city/bridges.py). Stations s are meters along `axis`."""
    kind: str             # arch (stone) | beam (concrete) | ford (a concrete slab over a dry oued)
    axis: object          # LineString: a street's center line, or the piece of a road between `ends`
    width: float          # of the ribbon
    street: int           # index in plan.streets, -1 on a country road
    ends: tuple           # (s0, s1) where the ribbon leaves its street or road; beyond them it is that street
    river: int = -1       # index in world.rivers: the one under most of the deck
    span: tuple = (0.0, 0.0)       # (s0, s1) the open part, abutment to abutment; outside it the ramp is solid fill
    s: object = None               # stations, with one at each kink, at `ends`, at `span`, at `channel` and at each pier
    z: object = None               # top of the ribbon at each station (the deck is level across)
    floor: object = None           # the ground under the center line at each station
    depth: float = 0.0             # deck, from its top to its soffit
    air: float = 0.0               # meters from the water to the soffit it was given
    water: float = 0.0             # the water's level, or a dry oued's floor
    water_width: float = 0.0       # meters, square to the river
    channel: tuple = (0.0, 0.0)    # (s0, s1) over the water or the floor
    piers: object = field(default_factory=lambda: np.zeros(0))   # stations inside `span`: the piers between arches or beams
    dry: bool = False     # over a dry oued
    tilt: tuple = (0.0, 0.0)       # rise to the left of the axis, m per m, at the two ends: a ramp starts leaning with the
                                   # land under its street or road, and is level across by the open part
    road: int = -1        # index in world.roads, -1 in a city
    along: float = 0.0    # meters along the road at s = 0
    old: bool = False     # an end by the old town: its warm stone
    lean: object = None   # a ford only, at each station: rise to the left, m per m, as the land under the slab leans
    rivers: tuple = ()    # all the rivers under the deck, in `world.rivers`; `water` is the highest of their levels
    own: object = None    # a road that shares a crossing with a wider one: (s0, s1) of the structure it keeps, clear of
                          # that road's deck; (0, 0) none. None: this record is the crossing's structure (city/bridges.follow)
    under: tuple = (0.0, 0.0)      # (s0, s1) where the wider road's ribbon covers this one's, which is not drawn there

    @property
    def deck(self):
        """The ribbon's outline between `ends`, a street's surface being the street's beyond them."""
        return substring(self.axis, *self.ends).buffer(self.width / 2, cap_style="flat")

    def standing(self):
        """The record of what stands here, or None: a road that follows a wider one draws only `own`."""
        if self.own is None:
            return self
        a, c = self.own
        if c <= a:
            return None
        span = tuple(float(np.clip(s, a, c)) for s in self.span)
        channel = tuple(float(np.clip(s, a, c)) for s in self.channel)
        return replace(self, ends=(a, c), span=span, channel=channel, own=None, piers=self.piers[(self.piers > a) & (self.piers < c)])

    def shown(self) -> list:
        """[(s0, s1)]: the stretches of the axis that have a ribbon."""
        pieces = ((0.0, self.under[0]), (self.under[1], self.axis.length)) if self.under[1] > self.under[0] else \
                 ((0.0, self.axis.length),)
        return [(a, c) for a, c in pieces if c > a]

    def locate(self, x, y) -> np.ndarray:
        """Stations of the points x, y."""
        return np.minimum(shapely.line_locate_point(self.axis, shapely.points(np.ravel(x), np.ravel(y))), self.axis.length)

    def at(self, x, y) -> np.ndarray:
        """Top of the ribbon at the points x, y."""
        x, y = np.ravel(x).astype(np.float64), np.ravel(y).astype(np.float64)
        s = self.locate(x, y)
        z = np.interp(s, self.s, self.z)
        lean = self.leaning(s)
        on = np.flatnonzero(lean != 0.0)
        if len(on):
            a = shapely.get_coordinates(shapely.line_interpolate_point(self.axis, np.maximum(s[on] - 0.5, 0.0)))
            b = shapely.get_coordinates(shapely.line_interpolate_point(self.axis, np.minimum(s[on] + 0.5, self.axis.length)))
            t = (b - a) / np.maximum(np.hypot(*(b - a).T), 1e-9)[:, None]
            mid = 0.5 * (a + b)                     # the point of the axis, to the half meter
            z[on] += lean[on] * (t[:, 0] * (y[on] - mid[:, 1]) - t[:, 1] * (x[on] - mid[:, 0]))
        return z

    def leaning(self, s) -> np.ndarray:
        """Rise of the ribbon to the left of the axis at stations s, in meters per meter."""
        if self.lean is not None:
            return np.interp(s, self.s, self.lean)
        return self.fade(s) * np.where(s < 0.5 * self.axis.length, self.tilt[0], self.tilt[1])

    def fade(self, s) -> np.ndarray:
        """1 at `ends`, 0 on the open part: how much of the land's lean a ramp keeps, over a meter at the least."""
        e0, e1 = self.ends
        a, c = max(self.span[0], e0 + 1.0), min(self.span[1], e1 - 1.0)
        return np.maximum(np.clip((a - s) / (a - e0), 0.0, 1.0), np.clip((s - c) / (e1 - c), 0.0, 1.0))


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
    port: object = None       # city/port.py: quays, breakwater, lighthouse and the ground zones they change (prompt 34)
    props: list = field(default_factory=list)   # city/moorings.py: boats, cranes and cargo of the harbor (prompt 35)
    fronts: list = field(default_factory=list)  # city/corniche.py: the corniche's seafront promenade (prompt 36)
    crossings: list = field(default_factory=list)  # city/river.py: where streets stop at a river, each with a bridge
    bridges: list = field(default_factory=list)    # city/bridges.py: Bridge records, each with its Street (prompt 62)
