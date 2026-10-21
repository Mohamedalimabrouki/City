"""Fast checks for the whole pipeline (about 20 seconds). Run: python -m pytest -q"""
import json

import numpy as np
import pytest
from shapely.strtree import STRtree

from citygen.__main__ import main
from citygen.city import plan_city
from citygen.config import load_config
from citygen.mesh.builder import MeshBuilder, extrude, rectangle
from citygen.mesh.gltf import read_glb, triangle_count, write_glb
from citygen.mesh.tile import TileContext, export_tile
from citygen.rng import stream
from citygen.world import generate_world


@pytest.fixture(scope="module")
def world():
    return generate_world(load_config(quick=True))


@pytest.fixture(scope="module")
def plan(world):
    return plan_city(world, world.capital())


def test_random_streams_are_stable_and_independent():
    a, b, c = stream(1, "x").random(3), stream(1, "x").random(3), stream(1, "y").random(3)
    assert np.array_equal(a, b)
    assert not np.array_equal(a, c)


def test_same_seed_same_world(world):
    again = generate_world(load_config(quick=True))
    assert json.dumps(world.to_json()) == json.dumps(again.to_json())
    other = generate_world(load_config(quick=True, overrides={"world": {"seed": 7}}))
    assert other.name != world.name or other.capital().x != world.capital().x


def test_settlements_are_on_land_and_apart(world):
    assert sum(s.kind == "capital" for s in world.settlements) == 1
    for s in world.settlements:
        assert world.terrain.height(s.x, s.y) > 0
    pts = np.array([(s.x, s.y, s.radius) for s in world.settlements])
    for i in range(len(pts)):
        d = np.hypot(pts[:, 0] - pts[i, 0], pts[:, 1] - pts[i, 1])
        d[i] = np.inf
        assert np.all(d > pts[:, 2] + pts[i, 2])


def test_roads_join_settlements(world):
    assert world.roads
    ids = {sid for r in world.roads for sid in r.ends if sid is not None}
    assert world.capital().id in ids


def test_plan_has_every_layer(plan):
    st = plan.stats
    assert st["buildings"] > 1000 and st["streets"] > 100 and st["trees"] > 100
    kinds = {d.kind for d in plan.districts}
    assert "medina" in kinds
    assert {b.kind for b in plan.buildings} >= {"house", "mosque_hall", "minaret", "wall"}


def test_same_seed_same_city(world, plan):
    again = plan_city(world, world.capital())
    assert again.stats["buildings"] == plan.stats["buildings"]
    assert again.buildings[100].footprint.equals_exact(plan.buildings[100].footprint, 1e-6)


def test_buildings_are_valid_and_inside_the_city(plan):
    area = plan.boundary.buffer(5.0)
    for b in plan.buildings:
        assert b.footprint.is_valid and b.footprint.area > 1.0 and b.height > 0
        assert area.contains(b.footprint.representative_point())


def test_buildings_stay_off_the_streets(plan):
    surfaces = [st.line.buffer(st.width / 2 - 0.3, cap_style="flat") for st in plan.streets]
    tree = STRtree(surfaces)
    bad = []
    for b in plan.buildings[::7]:
        for k in tree.query(b.footprint, predicate="intersects"):
            overlap = b.footprint.intersection(surfaces[int(k)]).area
            if overlap > 1.0:
                bad.append((b.kind, plan.streets[int(k)].kind, round(overlap, 1)))
    assert not bad, bad[:10]


def test_glb_roundtrip_and_axes(tmp_path):
    mb = MeshBuilder()
    extrude(mb, rectangle(5.0, 15.0, 10.0, 10.0, 0.0), 0.0, 5.0, "a", "b")
    n = write_glb(tmp_path / "t.glb", mb.gltf_parts(), {"a": {"color": "#ff0000"}})
    gltf, _ = read_glb(tmp_path / "t.glb")
    assert (tmp_path / "t.glb").stat().st_size == n
    assert triangle_count(gltf) == mb.triangles == 10
    pos = gltf["accessors"][gltf["meshes"][0]["primitives"][0]["attributes"]["POSITION"]]
    assert pos["max"][1] == pytest.approx(5.0)                      # glTF +Y is up
    assert pos["min"][2] == pytest.approx(-20.0) and pos["max"][2] == pytest.approx(-10.0)  # north is -Z


def test_tile_is_valid_glb(world, plan, tmp_path):
    tc = TileContext(world, [plan])
    s = world.capital()
    info = export_tile(tc, int(s.x // tc.size), int(s.y // tc.size), tmp_path)
    gltf, binary = read_glb(tmp_path / info["file"])
    assert triangle_count(gltf) == info["triangles"] > 1000
    assert {"lime_white", "asphalt", "paving"} <= {m["name"] for m in gltf["materials"]}
    for prim in gltf["meshes"][0]["primitives"]:
        count = gltf["accessors"][prim["attributes"]["POSITION"]]["count"]
        acc = gltf["accessors"][prim["indices"]]
        view = gltf["bufferViews"][acc["bufferView"]]
        assert view["byteOffset"] + view["byteLength"] <= len(binary)
        dtype = np.uint16 if acc["componentType"] == 5123 else np.uint32
        idx = np.frombuffer(binary, dtype, acc["count"], view["byteOffset"])
        assert idx.max() < count


def test_cli_list(capsys):
    main(["list", "--quick"])
    out = capsys.readouterr().out
    assert "capital" in out and "village" in out
