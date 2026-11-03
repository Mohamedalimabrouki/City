"""Prompt 59: rivers and lakes from the shape of the land (citygen/hydro.py)."""
import json

import numpy as np
import pytest
from shapely.geometry import LineString, Point, Polygon

from citygen.config import load_config
from citygen.hydro import drainage
from citygen.terrain import Terrain


class _Water:
    """The quick world's terrain and water, without settlements and roads (cheaper than a whole world)."""
    def __init__(self):
        self.cfg = load_config(quick=True)
        self.terrain = Terrain(42, self.cfg)
        self.size = self.terrain.size
        self.rivers, self.lakes = drainage(self.terrain, self.cfg)


@pytest.fixture(scope="module")
def world():
    return _Water()


def _json(rivers, lakes):
    return json.dumps([[r.to_json() for r in rivers], [k.to_json() for k in lakes]])


def test_drainage_is_deterministic(world):
    cfg = load_config(quick=True)
    again = drainage(Terrain(42, cfg), cfg)
    assert _json(*again) == _json(world.rivers, world.lakes)
    assert world.rivers and world.lakes


def test_river_beds_never_rise_downstream(world):
    for r in world.rivers:
        assert len(r.profile) == len(r.coords) == len(r.widths)
        assert np.all(np.diff(r.profile) <= 1e-9), r.id


def test_every_river_reaches_the_sea_a_lake_a_basin_or_the_border(world):
    size, cell = world.size, float(world.cfg["rivers"]["cell"])
    lakes = {k.id: Polygon(k.polygon).buffer(cell) for k in world.lakes}
    for r in world.rivers:
        seen, cur = set(), r
        while cur.mouth == "river":            # follow the tributaries down to the main river's mouth
            assert cur.into is not None and cur.into not in seen
            main = world.rivers[cur.into]
            assert LineString(main.coords).distance(Point(cur.coords[-1])) < 1.0
            seen.add(cur.into)
            cur = main
        x, y = cur.coords[-1]
        if cur.mouth == "sea":
            assert world.terrain.height(x, y) <= 0.0
        elif cur.mouth in ("lake", "basin"):
            lake = world.lakes[cur.into]
            assert lake.salt == (cur.mouth == "basin") and lakes[lake.id].contains(Point(x, y))
        else:
            assert cur.mouth == "border" and min(x, y, size - x, size - y) < cell


def test_oueds_are_thin_and_seasonal(world):
    rc = world.cfg["rivers"]
    assert any(r.seasonal for r in world.rivers) and any(not r.seasonal for r in world.rivers)
    for r in world.rivers:
        top = rc["width_max"] * (rc["oued_scale"] if r.seasonal else 1.0)
        assert np.all(r.widths <= top + 1e-9) and np.all(r.widths > 0)
    salt = [Polygon(k.polygon) for k in world.lakes if k.salt]
    assert salt                                # endorheic basins keep their water: no river leaves them
    assert not any(p.contains(Point(r.coords[0])) for p in salt for r in world.rivers)


def test_settlements_and_roads_keep_off_lakes():
    """Prompt 60: lakes count as water. On the 64 km world (41 lakes; prompt 59 put Sota and Chilel on salt
    lakes) no settlement's disc touches a lake and no road point lies in one."""
    from citygen.hydro import lake_shape
    from citygen.world import generate_world
    w = generate_world(load_config())
    wet = lake_shape(w.lakes)
    assert wet is not None
    for s in w.settlements:
        assert wet.distance(Point(s.x, s.y)) >= s.radius, s.name
    for r in w.roads:
        assert not any(wet.contains(Point(x, y)) for x, y in r.coords), r.kind
