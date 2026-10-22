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


def test_names_sound_north_african():
    from citygen.config import load_style
    from citygen.names import NameMaker
    style = load_style("maghreb")
    maker = NameMaker(style, stream(3, "names-test"))
    avoid = {a.lower() for a in style["names"]["avoid"]}
    for kind in ("village", "town", "city"):
        for _ in range(150):
            name = maker.settlement(kind).lower()
            assert not any(foreign in name for foreign in ("sh", "ts", "q", "oo")), name
            assert not set(name.split()) & avoid, name


def test_family_names_sound_tunisian():
    from citygen.city.life import family_name
    from citygen.config import load_style
    from citygen.names import NameMaker, _clumsy, _root_fits
    style = load_style("maghreb")
    life = style["life"]
    roots = life["roots"]
    avoid = {a.lower() for a in style["names"]["avoid"]}

    def draw():
        maker = NameMaker(style, stream(7, "family-test"))
        rng = stream(7, "households-test")
        return [family_name(maker, rng, life) for _ in range(300)]

    names = draw()
    assert names == draw()                                   # same seed, same names
    assert len(set(names)) >= 150
    real = set(life["nisba_names"]) | set(life["bou_names"]) | set(life["trade_names"])
    nisba = 0
    for name in names:
        assert len(name) <= 14, name
        assert not name.lower().endswith("ka"), name
        assert not any(part in name.lower() for part in roots["avoid_parts"]), name
        if name.startswith("Ben "):
            assert name[4:] in life["given_names"], name
        elif name not in real:                               # a made-up nisba
            assert name.endswith("i") and not _clumsy(name) and name.lower() not in avoid, name
        nisba += name in life["nisba_names"] or (name not in real and not name.startswith("Ben "))
    assert nisba >= 0.35 * len(names)
    assert _root_fits("1a23i", ["h", "m", "d"], roots)       # Hamdi
    assert not _root_fits("1a23i", ["b", "f", "n"], roots)   # b and f are the same class


def test_trees_are_natural_and_deterministic(world):
    from citygen.mesh.trees import tree_pieces
    table = world.style["dressing"]["trees"]
    a, b = tree_pieces(world.seed, table), tree_pieces(world.seed, table)
    assert len(a) == sum(int(spec["variants"]) for spec in table.values())
    for name, mb in a.items():
        assert 60 <= mb.triangles <= 200, (name, mb.triangles)
        pa, pb = mb.gltf_parts(), b[name].gltf_parts()
        assert pa.keys() == pb.keys()
        for mat in pa:
            assert mat in world.style["palette"], mat
            assert (pa[mat]["pos"] == pb[mat]["pos"]).all() and (pa[mat]["idx"] == pb[mat]["idx"]).all()
        assert 7.0 < max(p["pos"][:, 1].max() for p in pa.values()) < 8.3   # crown top near the 8 m piece height
    assert len({tuple(p["pos"].shape) + (float(p["pos"].sum()),) for p in
                (a["tree_broadleaf"].gltf_parts()["trunk"], a["tree_broadleaf_b"].gltf_parts()["trunk"])}) == 2


def test_climbers_hug_the_wall_and_are_deterministic(world):
    from citygen.mesh.climbers import climber_pieces
    spec = world.style["dressing"]["climber"]
    a, b = climber_pieces(world.seed, spec), climber_pieces(world.seed, spec)
    assert sorted(a) == ["bougainvillea", "bougainvillea_b"]
    for name, mb in a.items():
        assert 200 <= mb.triangles <= 280, (name, mb.triangles)
        parts = mb.gltf_parts()
        assert sum(len(p["idx"]) for p in parts.values()) == 3 * mb.triangles
        assert all(mat in world.style["palette"] for mat in parts)
        pos = np.concatenate([p["pos"] for p in parts.values()])
        width, height, depth = np.ptp(pos, axis=0)     # glTF axes: x along the wall, y up, z out of it
        assert width > 1.6 and height > 3.6 and depth < 0.8, (width, height, depth)
        assert len([m for m in parts if m.startswith("bougainvillea")]) == 3   # three bract shades
        assert "leaf_dark" in parts                                           # a few green leaves
        for mat, part in parts.items():
            other = b[name].gltf_parts()[mat]
            assert np.array_equal(part["pos"], other["pos"]) and np.array_equal(part["idx"], other["idx"])


def test_kit_names_and_roles(world):
    from citygen.kit import Kit
    kit = Kit(world.seed, world.cfg["build"].get("kits", []), world.style["palette"],
                  world.style["dressing"].get("trees"), world.style["dressing"].get("climber"))
    assert kit.pieces["door_blue"].source == "procedural"
    kit_pieces = [n for n, p in kit.pieces.items() if p.source != "procedural"]
    assert all(n.startswith(kit.pieces[n].source + "/") for n in kit_pieces)   # kit pieces never replace ours
    for role, options in world.style["dressing"]["roles"].items():
        for option in options:
            name = option[0]
            if "/" not in name or name.split("/")[0] in {p.source for p in kit.pieces.values()}:
                assert name in kit.pieces, f"role {role}: unknown piece {name}"
    for souk in world.style["souk"]:
        for name in souk["ground"] + souk["wall"]:
            assert name in world.style["dressing"]["roles"] or name in kit.pieces or "/" in name, name


def test_dressing_is_deterministic_and_on_the_walls(world, plan):
    from shapely.geometry import Point
    from citygen.mesh.tile import build_tile
    tc = TileContext(world, [plan])
    s = world.capital()
    i, j = int(s.x // tc.size), int(s.y // tc.size)
    _, first = build_tile(tc, i, j)
    _, again = build_tile(tc, i, j)
    assert len(first) > 200 and [(p.piece, p.x, p.y, p.z) for p in first] == [(p.piece, p.x, p.y, p.z) for p in again]
    assert all(p.piece in tc.kit.pieces and np.isfinite([p.x, p.y, p.z, p.yaw, p.scale]).all() for p in first)
    tree = STRtree([b.footprint.exterior for b in plan.buildings])
    doors = [p for p in first if tc.kit.pieces[p.piece].category == "door"]
    assert doors
    for p in doors:   # every door stands on a building wall
        near = tree.query_nearest(Point(p.x, p.y))
        assert plan.buildings[int(near[0])].footprint.exterior.distance(Point(p.x, p.y)) < 0.05


def test_tile_instances_are_valid(world, plan, tmp_path):
    tc = TileContext(world, [plan])
    s = world.capital()
    info = export_tile(tc, int(s.x // tc.size), int(s.y // tc.size), tmp_path)
    gltf, binary = read_glb(tmp_path / info["file"])
    assert "EXT_mesh_gpu_instancing" in gltf["extensionsUsed"]
    nodes = [n for n in gltf["nodes"] if "EXT_mesh_gpu_instancing" in n.get("extensions", {})]
    assert sum(gltf["accessors"][n["extensions"]["EXT_mesh_gpu_instancing"]["attributes"]["TRANSLATION"]]["count"]
               for n in nodes) == info["pieces"] > 100
    for n in nodes:
        attrs = n["extensions"]["EXT_mesh_gpu_instancing"]["attributes"]
        acc = gltf["accessors"][attrs["ROTATION"]]
        view = gltf["bufferViews"][acc["bufferView"]]
        q = np.frombuffer(binary, np.float32, acc["count"] * 4, view.get("byteOffset", 0)).reshape(-1, 4)
        assert np.allclose(np.linalg.norm(q, axis=1), 1.0, atol=1e-5)
        assert acc["count"] == gltf["accessors"][attrs["TRANSLATION"]]["count"]


def test_households_and_souks(plan):
    assert len(plan.households) > 100
    kinds = {plan.buildings[h.building].kind for h in plan.households}
    assert kinds <= {"house", "domed", "apartments", "villa"}
    assert all(0.0 <= h.wealth <= 1.0 and h.members >= 1 for h in plan.households)
    assert plan.souks and all(plan.streets[k.street].kind == "souk" for k in plan.souks)
    assert len({k.name for k in plan.souks}) == len(plan.souks)   # every souk has its own name


def test_fingerprint_tool(tmp_path, monkeypatch):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
    import fingerprint
    folder = tmp_path / "w"
    (folder / "tiles").mkdir(parents=True)
    (folder / "maps").mkdir()
    (folder / "world.json").write_text(json.dumps({"name": "T", "seed": 1, "style": "maghreb"}))
    (folder / "tiles" / "index.json").write_text(json.dumps({"tiles": [], "seconds": 1.0}))
    (folder / "tiles" / "tile_0_0.glb").write_bytes(b"abc")
    (folder / "cities" / "c").mkdir(parents=True)
    (folder / "cities" / "c" / "plan.json").write_text(json.dumps({"streets": [1, 2], "trees": [1]}))
    monkeypatch.chdir(tmp_path)
    assert fingerprint.main(["save", "a", str(folder)]) == 0
    assert fingerprint.main(["compare", "a", str(folder), "--allow", ""]) == 0
    (folder / "tiles" / "index.json").write_text(json.dumps({"tiles": [], "seconds": 9.0}))
    assert fingerprint.main(["compare", "a", str(folder), "--allow", ""]) == 0   # timings are ignored
    saved = json.loads((tmp_path / "output" / "checks" / "fp-a.json").read_text())["parts"]
    (folder / "cities" / "c" / "plan.json").write_text(json.dumps({"streets": [1, 2], "trees": [1, 2]}))
    changes = fingerprint.compare(saved, fingerprint.fingerprint(folder)["parts"])
    assert changes == [("plan/c/trees", "n 1 -> 2")]   # exactly the edited key
    assert fingerprint.main(["compare", "a", str(folder), "--allow", "plan/c/trees"]) == 0
    assert fingerprint.main(["compare", "a", str(folder), "--allow", ""]) == 1
    (folder / "cities" / "c" / "plan.json").write_text(json.dumps({"streets": [1, 2], "trees": [1]}))
    (folder / "tiles" / "tile_0_0.glb").write_bytes(b"abcd")
    assert fingerprint.main(["compare", "a", str(folder), "--allow", ""]) == 1
    assert fingerprint.main(["compare", "a", str(folder), "--allow", "tiles/*"]) == 0


def test_make_blend_command():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
    import make_blend
    index = {"focus": {"name": "Goumosbane"}, "views": {"souk": {}, "street": {}, "corniche": {}}}
    views = make_blend.views_of(index)
    assert views == ["street", "aerial", "corniche", "souk"]           # street stays the active camera
    assert make_blend.views_of({"focus": {"name": "X"}}) == ["aerial"]  # an index without views
    out = make_blend.blend_path(Path("w"), index)
    assert out.name == "goumosbane.blend"
    cmd = make_blend.command("blender", Path("w"), views, out)
    assert cmd[cmd.index("--view") + 1] == "street" and "--setup-only" in cmd
    assert all(view in cmd[cmd.index("--python-expr") + 1] for view in views)
    assert '"CAMERA"' in cmd[cmd.index("--python-expr") + 1]           # opens looking through the camera


@pytest.mark.slow  # about 5 s and needs processes; run with: python -m pytest -q -m slow
def test_parallel_tiles_match_one_process(world, plan, tmp_path):
    from citygen.build import export_tiles
    size = int(world.cfg["tiles"]["size"])
    s = world.capital()
    i, j = int(s.x // size), int(s.y // size)
    keys = [(i, j), (i + 1, j), (i, j + 1)]
    out = {}
    for workers in (1, 2):
        folder = tmp_path / f"w{workers}"
        folder.mkdir()
        out[workers] = (export_tiles(world, [plan], keys, folder, workers, lambda n: None), folder)
    assert out[1][0] == out[2][0]
    for i, j in keys:
        name = f"tile_{i}_{j}.glb"
        assert (out[1][1] / name).read_bytes() == (out[2][1] / name).read_bytes()


def test_build_key_ignores_workers_and_output():
    from citygen.buildkey import build_key
    a = load_config(quick=True)
    b = load_config(quick=True, overrides={"build": {"workers": 3, "output": "elsewhere"}})
    c = load_config(quick=True, overrides={"tiles": {"terrain_step": 99.0}})
    assert build_key(a, [3, 1]) == build_key(b, [1, 3]) != build_key(c, [1, 3]) != build_key(a, [1, 3, 4])


def test_cached_plan_is_reused_with_the_worlds_own_settlement(world, plan, tmp_path):
    from citygen import build as builder
    messages = []
    first = builder.load_or_plan(world, world.capital(), tmp_path / "cache", "aaaa", False, messages.append)
    assert first.settlement is world.capital() and messages[0].startswith("planned")
    again = builder.load_or_plan(world, world.capital(), tmp_path / "cache", "aaaa", False, messages.append)
    assert messages[1].startswith("plan reused") and again.settlement is world.capital()
    assert again.stats == first.stats and len(again.buildings) == len(first.buildings)
    (tmp_path / "cache" / "tiles-aaaa").mkdir()
    (tmp_path / "cache" / "tiles-aaaa" / "tile_0_0.json").write_text("{}")
    (tmp_path / "cache" / "tiles-bbbb").mkdir()
    builder.clean_cache(tmp_path / "cache", "bbbb", False)   # other builds' files go, this key's stay
    assert [p.name for p in (tmp_path / "cache").iterdir()] == ["tiles-bbbb"]


def test_finished_tiles_need_every_file(tmp_path):
    from citygen.build import finished_tiles
    entry = lambda i, **more: {"i": i, "j": 0, "file": f"tile_{i}_0.glb", "bytes": 3, **more}
    for i in (0, 1, 2, 3):
        (tmp_path / f"tile_{i}_0.glb").write_bytes(b"abc")
    (tmp_path / "tile_3_0.glb").write_bytes(b"ab")   # cut short: wrong size
    (tmp_path / "index.json").write_text(json.dumps({"build_key": "k", "tiles": [entry(0), entry(1)]}))
    journal = tmp_path / "journal"
    journal.mkdir()
    for e in (entry(2), entry(3), entry(4), entry(5, files=["lod_5.glb"])):
        (journal / f"tile_{e['i']}_0.json").write_text(json.dumps(e))
    (journal / "tile_6_0.json").write_text('{"i": 6, "j"')   # cut short
    keys = [(i, 0) for i in range(8)]
    assert sorted(finished_tiles(tmp_path, journal, "k", keys)) == [(0, 0), (1, 0), (2, 0)]
    assert finished_tiles(tmp_path, tmp_path / "none", "other", keys) == {}   # another key: nothing counts


def _tiny_build(tmp_path, monkeypatch, plan, calls, force=False, **tiles):
    """One small build into tmp_path; planning is counted and answered by the shared fixture plan."""
    from citygen import build as builder

    def fake_plan(world, settlement):
        calls.append(settlement.name)
        plan.settlement = settlement
        return plan

    monkeypatch.setattr(builder, "plan_city", fake_plan)
    cfg = load_config(quick=True, overrides={"build": {"output": str(tmp_path), "center_radius": 150.0,
                                                      "workers": 1}, "tiles": tiles})
    messages = []
    out = builder.build(cfg, log=messages.append, force=force)
    return out, messages


def _bytes_of(out):
    return {p.name: p.read_bytes() for p in sorted(out.rglob("*")) if p.is_file() and "cache" not in p.parts}


@pytest.mark.slow  # four small builds, about 15 s; run with: python -m pytest -q -m slow
def test_resumed_builds_match_and_a_changed_setting_rebuilds(world, plan, tmp_path, monkeypatch):
    calls = []
    out, _ = _tiny_build(tmp_path, monkeypatch, plan, calls)
    first = _bytes_of(out)
    index = json.loads(first["index.json"])
    key = json.loads(first["summary.json"])["build_key"]
    assert len(calls) == 1 and index["build_key"] == key and index["views"] and not list(out.rglob("*.part"))
    (out / "tiles" / index["tiles"][0]["file"]).unlink()   # an interrupted build: one tile is missing
    stale = out / "tiles" / "tile_9_9.glb.part"
    stale.write_bytes(b"half")
    out, messages = _tiny_build(tmp_path, monkeypatch, plan, calls)
    assert len(calls) == 1 and any(m.startswith("plan reused") for m in messages)
    assert f"tiles reused: {len(index['tiles']) - 1} of {len(index['tiles'])}" in messages and not stale.exists()
    second = _bytes_of(out)
    for name in first:   # the rebuilt tile, plan.json and the index views come out the same
        if name != "summary.json":   # its timings differ
            assert second[name] == first[name], name
    out, messages = _tiny_build(tmp_path, monkeypatch, plan, calls, terrain_step=20.0)
    assert len(calls) == 2 and not any("reused" in m for m in messages)
    assert json.loads((out / "summary.json").read_text())["build_key"] != key
    assert len(list((out / "cache").glob("*.pkl"))) == 1   # the plan of the old key was deleted
    _tiny_build(tmp_path, monkeypatch, plan, calls, terrain_step=20.0)
    assert len(calls) == 2   # the same key again: nothing is planned
    from citygen import build as builder
    country_map = builder.country_map

    def stopped(*args):   # Ctrl+C while a --force build writes the maps
        raise KeyboardInterrupt
    monkeypatch.setattr(builder, "country_map", stopped)
    with pytest.raises(KeyboardInterrupt):
        _tiny_build(tmp_path, monkeypatch, plan, calls, force=True, terrain_step=20.0)
    monkeypatch.setattr(builder, "country_map", country_map)
    out, messages = _tiny_build(tmp_path, monkeypatch, plan, calls, terrain_step=20.0)
    assert "maps and data files reused" not in messages   # the cut-short maps are written again
