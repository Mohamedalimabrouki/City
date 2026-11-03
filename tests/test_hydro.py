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
        ground = np.array([world.terrain.height(x, y) for x, y in r.coords])
        assert abs(r.profile[0] - ground[0]) < 10.0, r.id     # the bed starts on the ground at the source...
        assert np.all(ground - r.profile < 8.0), r.id          # ...and never digs deep under it


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


class _Valley:
    """A small synthetic country: a valley sloping east to the border with one round hollow near its foot.

    `ridge` meters of ridge across the hollow's bottom split a dry basin's water into two pockets."""
    def __init__(self, wet, ridge=0.0):
        self.size, self.wet, self.ridge = 20000.0, wet, ridge

    def height(self, x, y):
        x, y = np.asarray(x, float), np.asarray(y, float)
        bowl = np.clip(1 - ((x - 15000) ** 2 + (y - 10000) ** 2) / 1000.0 ** 2, 0, None)
        h = 200.0 - 0.008 * x + 0.01 * np.abs(y - 10000) - 40.0 * bowl
        return h + self.ridge * np.exp(-((x - 15000) / 200.0) ** 2) * bowl

    def moisture(self, x, y, h):
        return np.full(np.shape(h), self.wet)


def _ends_in(river, lake, cell):
    return Polygon(lake.polygon).buffer(cell).contains(Point(river.coords[-1]))


def test_a_wet_hollow_fills_to_a_fresh_lake_and_spills_on():
    cfg = load_config(quick=True)
    rivers, lakes = drainage(_Valley(0.9), cfg)
    cell = float(cfg["rivers"]["cell"])
    assert len(lakes) == 1 and not lakes[0].salt
    into = [r for r in rivers if r.mouth == "lake"]
    assert into and all(r.into == 0 and _ends_in(r, lakes[0], cell) for r in into)
    shore = Polygon(lakes[0].polygon).buffer(cell)
    outlets = [r for r in rivers if shore.contains(Point(r.coords[0])) and r.mouth != "lake"]
    assert len(outlets) == 1 and outlets[0].mouth == "border"  # the lake's outlet goes on to the border


def test_a_dry_hollow_keeps_its_water_in_a_salt_lake():
    cfg = load_config(quick=True)
    rivers, lakes = drainage(_Valley(0.02), cfg)
    cell = float(cfg["rivers"]["cell"])
    assert len(lakes) == 1 and lakes[0].salt
    into = [r for r in rivers if r.mouth == "basin"]
    assert into and all(r.into == 0 and _ends_in(r, lakes[0], cell) for r in into)
    assert not any(Polygon(lakes[0].polygon).contains(Point(r.coords[0])) for r in rivers)


@pytest.mark.xfail(strict=True, reason="review-59 finding 4: a salt basin in two pockets draws only the "
                   "bigger one, and its river can end in the other (open question in docs/wip/fix-59.md)")
def test_a_salt_basin_in_two_pockets_draws_the_pocket_its_river_ends_in():
    cfg = load_config(quick=True)
    rivers, lakes = drainage(_Valley(0.02, ridge=29.0), cfg)
    cell = float(cfg["rivers"]["cell"])
    assert len(lakes) == 1 and lakes[0].salt
    into = [r for r in rivers if r.mouth == "basin"]
    assert into and all(_ends_in(r, lakes[0], cell) for r in into)
