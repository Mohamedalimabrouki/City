"""Prompt 59: rivers and lakes from the shape of the land (citygen/hydro.py)."""
import json

import numpy as np
import pytest
import shapely
from scipy import ndimage
from shapely.geometry import LineString, Point, Polygon

from citygen.config import load_config
from citygen.hydro import _flood, _routing, drainage
from citygen.terrain import Terrain
from citygen.world import generate_world


class _Water:
    """A world's terrain and water, without settlements and roads (cheaper than a whole world)."""
    def __init__(self, quick):
        self.quick = quick
        self.cfg = load_config(quick=quick)
        self.cell = float(self.cfg["rivers"]["cell"])
        self.terrain = Terrain(42, self.cfg)
        self.size = self.terrain.size
        self.rivers, self.lakes = drainage(self.terrain, self.cfg)
        # the grid cells of a lake reach about a cell past its shore
        self.shores = shapely.unary_union([Polygon(k.polygon).buffer(1.5 * self.cell) for k in self.lakes])


@pytest.fixture(scope="module", params=[True, False], ids=["quick", "64km"])
def world(request):
    return _Water(request.param)


def _json(rivers, lakes):
    return json.dumps([[r.to_json() for r in rivers], [k.to_json() for k in lakes]])


def test_drainage_is_deterministic(world):
    cfg = load_config(quick=world.quick)
    again = drainage(Terrain(42, cfg), cfg)
    assert _json(*again) == _json(world.rivers, world.lakes)
    assert world.rivers and world.lakes


def test_every_cell_drains_to_a_lower_one(world):
    g = _routing(world.terrain, world.cfg["rivers"])
    cells = np.flatnonzero(g.recv >= 0)
    assert len(cells) > 0.3 * g.n * g.n
    assert np.all(g.flat[cells] > g.flat[g.recv[cells]])   # so highest first is upstream first: no flow is lost


def test_river_beds_never_rise_and_never_lie_above_the_ground(world):
    fed = {r.into for r in world.rivers if r.mouth == "river"}
    for r in world.rivers:
        assert len(r.profile) == len(r.coords) == len(r.widths)
        assert np.all(np.diff(r.profile) <= 1e-9), r.id
        ground = world.terrain.height(r.coords[:, 0], r.coords[:, 1])
        off = ~shapely.contains_xy(world.shores, r.coords[:, 0], r.coords[:, 1])
        assert np.all(r.profile[off] <= ground[off] + 0.1), r.id
        if r.id not in fed and off.all():              # no higher than that: nothing is dug without a reason
            line = np.arange(len(ground) - (r.mouth == "river"))
            assert np.allclose(r.profile[line], np.minimum.accumulate(ground[line]), atol=1e-6), r.id


def test_tributaries_end_on_their_main_river_s_bed(world):
    joined = [r for r in world.rivers if r.mouth == "river"]
    assert joined
    for r in joined:
        main = world.rivers[r.into]
        assert r.into < r.id                           # the order the beds are worked out in
        at = LineString(main.coords).project(Point(r.coords[-1]))
        along = np.concatenate([[0.0], np.cumsum(np.hypot(*np.diff(main.coords, axis=0).T))])
        assert abs(np.interp(at, along, main.profile) - r.profile[-1]) < 1e-6, r.id


def test_no_bed_lies_far_under_the_level_of_the_lake_it_reaches(world):
    """A lake's flat water would stand as a wall at its shore over a trench cut below its level."""
    worst = 0.0
    for r in world.rivers:
        end = r
        while end.mouth == "river":
            end = world.rivers[end.into]
        if end.mouth in ("lake", "basin"):
            level = world.lakes[end.into].level
            dry = (r.profile < level) & (world.terrain.height(r.coords[:, 0], r.coords[:, 1]) > level)
            if dry.any():
                worst = max(worst, float((level - r.profile[dry]).max()))
    assert worst < 5.0


def test_every_river_reaches_the_sea_a_lake_a_basin_or_the_border(world):
    size, cell = world.size, world.cell
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


def test_world_json_lists_the_rivers_and_lakes():
    data = json.loads(json.dumps(generate_world(load_config(quick=True)).to_json()))
    assert set(data["rivers"][0]) == {"id", "coords", "widths", "flow", "seasonal", "profile", "mouth", "into"}
    assert set(data["lakes"][0]) == {"id", "polygon", "level", "salt"}


class _Valley:
    """A small synthetic country: a valley sloping east to the border with one round hollow near its foot.

    `ridge` meters of ridge across the hollow at x = `at` split a dry basin's water into two pockets."""
    def __init__(self, wet, ridge=0.0, at=15000.0, radius=1000.0, deep=40.0):
        self.size, self.wet, self.ridge, self.at, self.radius, self.deep = 20000.0, wet, ridge, at, radius, deep

    def height(self, x, y):
        x, y = np.asarray(x, float), np.asarray(y, float)
        bowl = np.clip(1 - ((x - 15000) ** 2 + (y - 10000) ** 2) / self.radius ** 2, 0, None)
        h = 200.0 - 0.008 * x + 0.01 * np.abs(y - 10000) - self.deep * bowl
        return h + self.ridge * np.exp(-((x - self.at) / 200.0) ** 2) * bowl

    def moisture(self, x, y, h):
        return np.full(np.shape(h), self.wet)


class _WetWest(_Valley):
    """A valley rainy west of `at` and dry east of it."""
    def moisture(self, x, y, h):
        return np.where(np.asarray(x, float) < self.at, 0.9, 0.02)


def _ends_in(river, lake, cell):
    return Polygon(lake.polygon).buffer(cell).contains(Point(river.coords[-1]))


def _lake_reached(g, cell):
    """The lake a grid cell's water ends in, -1 for the sea or the border."""
    while g.recv[cell] >= 0:
        cell = g.recv[cell]
    return g.lake_id[cell]


def _one_basin(land, g, rc):
    """The flood sees the hollow as one basin: what splits it is its inner rim."""
    X, Y = np.meshgrid(g.c, g.c)
    H = land.height(X, Y)
    filled, _ = _flood(H, H <= 0.0)
    return ndimage.label(filled - H > rc["basin_depth"], np.ones((3, 3), dtype=bool))[1] == 1


def _little_water():
    """A country whose hollows get far too little water to spread a lake of `lake_min_area`."""
    return load_config(quick=True, overrides={"rivers": {"lake_area_per_flow": 1e-4}})


def test_a_wet_hollow_fills_to_a_fresh_lake_and_spills_on():
    land, cfg = _Valley(0.9), load_config(quick=True)
    rivers, lakes = drainage(land, cfg)
    cell = float(cfg["rivers"]["cell"])
    assert len(lakes) == 1 and not lakes[0].salt
    ring = lakes[0].polygon
    assert np.abs(land.height(ring[:, 0], ring[:, 1]) - lakes[0].level).max() < 2.0   # the shore meets the ground
    into = [r for r in rivers if r.mouth == "lake"]
    assert into and all(r.into == 0 and _ends_in(r, lakes[0], cell) for r in into)
    shore = Polygon(lakes[0].polygon).buffer(cell)
    outlets = [r for r in rivers if shore.contains(Point(r.coords[0])) and r.mouth != "lake"]
    assert len(outlets) == 1 and outlets[0].mouth == "border"  # the lake's outlet goes on to the border
    assert abs(outlets[0].profile[0] - lakes[0].level) < 0.1   # and it starts at the lake's level


def test_a_wet_hollow_fills_to_its_spill_however_little_water_reaches_it():
    land, cfg = _Valley(0.9), _little_water()
    rivers, lakes = drainage(land, cfg)
    g = _routing(land, cfg["rivers"])
    assert len(lakes) == 1 and not lakes[0].salt
    assert np.count_nonzero(g.lake_id == 0) > 50                   # the whole hollow, not its balanced 23 cells
    shore = Polygon(lakes[0].polygon).buffer(float(cfg["rivers"]["cell"]))
    outlet = [r for r in rivers if shore.contains(Point(r.coords[0])) and r.mouth != "lake"]
    assert len(outlet) == 1 and outlet[0].mouth == "border" and abs(outlet[0].profile[0] - lakes[0].level) < 0.1


def test_a_river_cuts_through_the_rim_of_a_pit_too_small_for_a_lake():
    land = _Valley(0.9, radius=350.0, deep=15.0)
    rivers, lakes = drainage(land, load_config(quick=True))
    assert not lakes
    river = max(rivers, key=lambda r: r.flow)
    assert river.mouth == "border"
    ground = land.height(river.coords[:, 0], river.coords[:, 1])
    assert np.all(river.profile <= ground + 0.1) and np.all(np.diff(river.profile) <= 1e-9)
    assert (ground - river.profile).max() > 4.0                    # the cut through the rim


def test_a_dry_hollow_keeps_its_water_in_a_salt_lake():
    cfg = load_config(quick=True)
    rivers, lakes = drainage(_Valley(0.02), cfg)
    cell = float(cfg["rivers"]["cell"])
    assert len(lakes) == 1 and lakes[0].salt
    into = [r for r in rivers if r.mouth == "basin"]
    assert into and all(r.into == 0 and _ends_in(r, lakes[0], cell) for r in into)
    assert not any(Polygon(lakes[0].polygon).contains(Point(r.coords[0])) for r in rivers)


def test_a_dry_hollow_stays_closed_however_little_water_reaches_it():
    land, cfg = _Valley(0.02), _little_water()
    rc = cfg["rivers"]
    rivers, lakes = drainage(land, cfg)
    g = _routing(land, rc)
    assert len(lakes) == 1 and lakes[0].salt
    assert np.count_nonzero(g.lake_id == 0) * (g.c[1] - g.c[0]) ** 2 >= rc["lake_min_area"] * 1e6
    assert all(r.mouth == "basin" for r in rivers if r.coords[0, 0] < 15000.0 and r.mouth != "river")
    assert not any(r.mouth == "border" and r.coords[0, 0] < 13000.0 for r in rivers)   # nothing runs through it


def test_a_pocket_too_small_for_a_lake_drains_into_the_lake_of_its_basin():
    land, cfg = _Valley(0.02, ridge=25.0, at=14700.0), load_config(quick=True)
    rc = cfg["rivers"]
    cell = float(rc["cell"])
    rivers, lakes = drainage(land, cfg)
    assert len(lakes) == 1 and lakes[0].salt
    # the scene this test is about: under the lake's level the ground of the hollow lies in two pockets,
    # the second one under `lake_min_area`
    g = _routing(land, rc)
    X, Y = np.meshgrid(g.c, g.c)
    H = land.height(X, Y)
    hollow = (X - 15000.0) ** 2 + (Y - 10000.0) ** 2 < 1000.0 ** 2
    pockets, count = ndimage.label(hollow & (H <= lakes[0].level))
    assert count == 2 and np.bincount(pockets.ravel())[1:].min() * cell * cell < rc["lake_min_area"] * 1e6
    into = [r for r in rivers if r.mouth == "basin"]
    assert into and all(_ends_in(r, lakes[0], cell) for r in into)   # no river ends where no shore is drawn
    drawn = Polygon(lakes[0].polygon)
    lowest = pockets[np.unravel_index(np.argmin(np.where(hollow, H, np.inf)), H.shape)]
    bottoms = [np.unravel_index(np.argmin(np.where(pockets == p, H, np.inf)), H.shape) for p in (1, 2)]
    for p, (i, j) in zip((1, 2), bottoms):
        assert drawn.contains(Point(X[i, j], Y[i, j])) == (p == lowest)
    (i, j) = bottoms[0 if lowest == 2 else 1]                          # the other pocket's water reaches the lake
    assert _lake_reached(g, i * g.n + j) == 0


def test_two_pockets_over_the_thresholds_behind_an_inner_rim_are_two_closed_salt_lakes():
    land, cfg = _Valley(0.02, ridge=30.0), _little_water()
    rc = cfg["rivers"]
    rivers, lakes = drainage(land, cfg)
    g = _routing(land, rc)
    assert _one_basin(land, g, rc)
    assert len(lakes) == 2 and all(k.salt for k in lakes) and np.all(g.recv[g.lake_id >= 0] == -1)
    X, Y = (a.ravel() for a in np.meshgrid(g.c, g.c))
    west, east = [lake.id for lake in sorted(lakes, key=lambda k: Polygon(k.polygon).centroid.x)]
    hollow = np.flatnonzero((X - 15000.0) ** 2 + (Y - 10000.0) ** 2 < 900.0 ** 2)
    assert {_lake_reached(g, c) for c in hollow[X[hollow] < 14900.0]} == {west}    # nothing crosses the rim
    assert {_lake_reached(g, c) for c in hollow[X[hollow] > 15100.0]} == {east}
    into = [r for r in rivers if r.mouth == "basin"]
    assert into and all(r.into == west and r.coords[:, 0].max() < 15000.0 for r in into)


def test_a_wet_pocket_of_a_dry_basin_fills_to_its_spill_and_runs_into_the_lake_below():
    land, cfg = _WetWest(0.02, ridge=30.0), _little_water()
    rc = cfg["rivers"]
    rivers, lakes = drainage(land, cfg)
    g = _routing(land, rc)
    assert _one_basin(land, g, rc)
    assert sorted(k.salt for k in lakes) == [False, True]              # each pocket by the biome at its own bottom
    fresh, dry = sorted(lakes, key=lambda k: k.salt)
    cells = np.flatnonzero(g.lake_id == fresh.id)
    assert {_lake_reached(g, c) for c in cells} == {dry.id}            # its water runs on into the lake below
    rim = cells[0]
    while g.lake_id[rim] == fresh.id:
        rim = g.recv[rim]
    assert abs(land.height(g.c[rim % g.n], g.c[rim // g.n]) - fresh.level) < 2.0   # it stands up to its spill
    drains = np.flatnonzero(g.recv >= 0)
    assert np.all(g.flat[drains] > g.flat[g.recv[drains]])


@pytest.mark.slow  # two processes generate the 64 km world, about 5 s
def test_world_json_two_processes(tmp_path):
    import os
    import subprocess
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    code = ("import sys; from citygen.config import load_config; from citygen.world import generate_world; "
            "from citygen.export.lore import write_json; "
            "write_json(sys.argv[1], generate_world(load_config()).to_json())")
    for name, seed in (("a", "1"), ("b", "2")):
        r = subprocess.run([sys.executable, "-c", code, str(tmp_path / f"{name}.json")], cwd=root,
                           env={**os.environ, "PYTHONHASHSEED": seed}, capture_output=True)
        assert r.returncode == 0, r.stderr.decode()[-2000:]
    assert (tmp_path / "a.json").read_bytes() == (tmp_path / "b.json").read_bytes()
