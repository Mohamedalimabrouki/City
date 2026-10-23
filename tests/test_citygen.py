"""Fast checks for the whole pipeline (about 20 seconds). Run: python -m pytest -q"""
import json
import math

import numpy as np
import pytest
import shapely
from shapely.strtree import STRtree

from citygen.__main__ import main
from citygen.city import plan_city
from citygen.config import load_config
from citygen.mesh.builder import MeshBuilder, add_hip_roof, extrude, rectangle
from citygen.mesh.gltf import read_glb, read_parts, triangle_count, write_glb
from citygen.mesh.textures import (NAMES, PIXELS, encoded, images_for, spec_for, texture,
                                    texture_names, write_shared_textures)
from citygen.mesh.tile import TileContext, export_tile, texture_files
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
    assert len(again.walks) == len(plan.walks)
    assert again.walks[0].polygon.equals_exact(plan.walks[0].polygon, 1e-6)


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


def test_textured_glb_embeds_a_valid_image(tmp_path):
    import io
    from PIL import Image
    mb = MeshBuilder()
    mb.add("wall", [[0, 0, 0], [1, 0, 0], [1, 0, 1], [0, 0, 1]], [[0, 1, 0]] * 4,
           [[0, 0], [1, 0], [1, 1], [0, 1]], [[0, 1, 2], [0, 2, 3]])
    enc = encoded("plaster", 3, {"pixels": 256})
    write_glb(tmp_path / "t.glb", mb.gltf_parts(),
              {"wall": {"color": "#ffffff", "texture": "plaster", "texture_size": [4.0, 2.0]}},
              images={"plaster": {"bytes": enc.data, "mime": enc.mime}})
    gltf, binary = read_glb(tmp_path / "t.glb")
    assert gltf["extensionsUsed"] == ["KHR_texture_transform"]
    assert gltf["samplers"] == [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}]
    info = gltf["materials"][0]["pbrMetallicRoughness"]["baseColorTexture"]
    assert info["extensions"]["KHR_texture_transform"]["scale"] == [0.25, 0.5]   # 4 m x 2 m repeats
    assert gltf["textures"][info["index"]]["source"] == 0 and gltf["textures"][info["index"]]["sampler"] == 0
    image = gltf["images"][0]
    view = gltf["bufferViews"][image["bufferView"]]
    assert image["mimeType"] == enc.mime and "uri" not in image
    assert binary[view["byteOffset"]:view["byteOffset"] + view["byteLength"]] == enc.data
    assert Image.open(io.BytesIO(enc.data)).size == (256, 256)
    assert read_parts(tmp_path / "t.glb")["wall"]["uv"].tolist() == [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]


def test_shared_texture_files_are_written_once(tmp_path):
    style = {"textures": {"plaster": {"pixels": 256}},
             "palette": {"wall": {"color": "#ffffff", "texture": "plaster", "texture_size": [3.0, 3.0]},
                         "roof": {"color": "#ffffff"}}}
    enc = encoded("plaster", 5, spec_for(style, "plaster"))
    file = f"plaster.{enc.ext}"
    assert write_shared_textures(style, 5, tmp_path) == [file]
    assert write_shared_textures(style, 5, tmp_path) == [file]   # again: same bytes, no race
    image = tmp_path / "textures" / file
    assert image.is_file() and image.read_bytes() == enc.data
    images = images_for(style, 5, "shared")
    assert images == {"plaster": {"uri": f"textures/{file}"}}
    mb = MeshBuilder()
    mb.add("wall", [[0, 0, 0], [1, 0, 0], [1, 0, 1]], [[0, 1, 0]] * 3,
           [[0, 0], [1, 0], [1, 1]], [[0, 1, 2]])
    write_glb(tmp_path / "tile_0_0.glb", mb.gltf_parts(),
              {"wall": {"color": "#ffffff", "texture": "plaster"}}, images=images)
    gltf, _ = read_glb(tmp_path / "tile_0_0.glb")
    assert gltf["images"] == [{"uri": f"textures/{file}"}]
    assert (tmp_path / gltf["images"][0]["uri"]).is_file()   # the URI resolves next to the tile


def test_textures_off_leaves_flat_colors(tmp_path):
    style = {"palette": {"wall": {"color": "#ffffff", "texture": "plaster", "texture_size": [3.0, 3.0]}}}
    assert images_for(style, 5, "off") == {}
    mb = MeshBuilder()
    mb.add("wall", [[0, 0, 0], [1, 0, 0], [1, 0, 1]], [[0, 1, 0]] * 3,
           [[0, 0], [1, 0], [1, 1]], [[0, 1, 2]])
    write_glb(tmp_path / "t.glb", mb.gltf_parts(),
              {"wall": {"color": "#ffffff", "texture": "plaster"}}, images={})
    gltf, _ = read_glb(tmp_path / "t.glb")
    assert "images" not in gltf and "textures" not in gltf and "extensionsUsed" not in gltf
    assert "baseColorTexture" not in gltf["materials"][0]["pbrMetallicRoughness"]


def test_palette_maps_walls_and_roofs_to_generated_textures():
    from citygen.config import load_style
    style = load_style("maghreb")
    for name, spec in style["palette"].items():
        texture = spec.get("texture")
        if not texture:
            continue
        assert texture in NAMES, (name, texture)
        assert texture in style["textures"], (name, texture)
        w, h = spec["texture_size"]
        assert 0.5 <= w <= 8.0 and 0.5 <= h <= 8.0, (name, w, h)
    for name in ("lime_white", "cream", "concrete", "roof_tile", "roof_white", "rampart",
                 "plinth_blue", "plinth_stone"):
        assert style["palette"][name].get("texture"), name


def test_walls_split_at_the_plinth_with_v_zero_at_the_ground():
    mb = MeshBuilder()
    extrude(mb, rectangle(5.0, 5.0, 10.0, 8.0, 0.0), -0.6, 4.0, "wall", None,
            z_ref=1.5, plinth=("plinth", 0.8))
    parts = mb.gltf_parts()
    plinth, wall = parts["plinth"], parts["wall"]
    assert plinth["pos"][:, 1].min() == pytest.approx(-0.6)
    assert plinth["pos"][:, 1].max() == pytest.approx(2.3)
    assert wall["pos"][:, 1].min() == pytest.approx(2.3)      # the split, not the buried foot
    assert wall["pos"][:, 1].max() == pytest.approx(4.0)
    split = np.isclose(plinth["pos"][:, 1], 2.3)
    assert np.allclose(plinth["uv"][split, 1], -0.8)          # v = -(z - z_ref) is continuous


def test_plinth_only_covers_frontage_segments():
    mb = MeshBuilder()
    extrude(mb, rectangle(5.0, 5.0, 10.0, 8.0, 0.0), -0.6, 4.0, "wall", None,
            z_ref=1.5, plinth=("plinth", 0.8), frontage=[True, False, True, False])
    parts = mb.gltf_parts()
    assert len(parts["plinth"]["idx"]) // 3 == 4             # two sides, two triangles each
    assert len(parts["wall"]["idx"]) // 3 == 8              # upper band on two sides + two plain sides
    assert parts["plinth"]["pos"][:, 1].min() == pytest.approx(-0.6)
    assert parts["plinth"]["pos"][:, 1].max() == pytest.approx(2.3)


def test_hip_roof_uvs_are_planar_in_meters():
    mb = MeshBuilder()
    add_hip_roof(mb, rectangle(0.0, 0.0, 10.0, 6.0, 0.3).exterior.coords[:4], 2.0, 2.5, "roof")
    part = mb.gltf_parts()["roof"]
    pos, uv, idx = part["pos"], part["uv"], part["idx"].reshape(-1, 3)
    a, b = pos[idx], uv[idx]
    area3 = 0.5 * np.linalg.norm(np.cross(a[:, 1] - a[:, 0], a[:, 2] - a[:, 0]), axis=1)
    e1, e2 = b[:, 1] - b[:, 0], b[:, 2] - b[:, 0]
    area_uv = 0.5 * np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0])
    assert np.allclose(area_uv, area3, rtol=1e-9, atol=1e-9)   # no smearing: 1 UV unit = 1 m
    assert uv[:, 1].max() == pytest.approx(math.hypot(3.0, 2.5))


def test_texture_images_are_deterministic():
    a = encoded("plaster", 9, {"pixels": 256})
    assert a.data == encoded("plaster", 9, {"pixels": 256}).data
    assert a.data != encoded("plaster", 10, {"pixels": 256}).data


def test_texture_sizes_follow_the_style():
    for name in NAMES:
        for size in PIXELS:
            assert texture(name, 4, {"pixels": size}).size == (size, size)
    with pytest.raises(ValueError):
        texture("unobtainium", 4)


def test_textures_are_seamless():
    """The last column/row is as close to the first as any two neighbours inside the image."""
    for name in NAMES:
        a = np.asarray(texture(name, 42, {"pixels": 256}), dtype=np.float64)
        lr = np.abs(a[:, 0] - a[:, -1]).mean()
        tb = np.abs(a[0, :] - a[-1, :]).mean()
        inner = (np.abs(np.diff(a, axis=1)).mean() + np.abs(np.diff(a, axis=0)).mean()) / 2.0
        assert max(lr, tb) <= 1.5 * inner + 1.5, (name, lr, tb, inner)


def test_texture_sheet_lists_every_texture(tmp_path):
    from PIL import Image
    from citygen.texturesheet import texture_sheet
    style = {"textures": {"plaster": {"pixels": 256}, "stone": {"pixels": 256}},
             "palette": {"wall": {"color": "#e8ddc8", "texture": "plaster"},
                         "kerb": {"color": "#b8b0a2", "texture": "stone"}}}
    assert texture_names(style) == ["plaster", "stone"]
    out = texture_sheet(tmp_path / "sheet.png", style, 42, columns=2)
    image = Image.open(out)
    assert image.format == "PNG" and image.width > 800 and image.height > 400


def test_tile_entry_lists_shared_textures():
    class FakeTC:
        texture_mode = "shared"
        materials = {"wall": {"texture": "test"}, "roof": {"color": "#ffffff"}}
        texture_images = {"test": {"uri": "textures/test.png"}}

    parts = {"wall": {}, "roof": {}}
    assert texture_files(FakeTC, parts, []) == ["textures/test.png"]
    FakeTC.texture_mode = "off"
    assert texture_files(FakeTC, parts, []) == []


def test_tile_is_valid_glb(world, plan, tmp_path):
    tc = TileContext(world, [plan])
    s = world.capital()
    info = export_tile(tc, int(s.x // tc.size), int(s.y // tc.size), tmp_path)
    gltf, binary = read_glb(tmp_path / info["file"])
    assert triangle_count(gltf) == info["triangles"] > 1000
    assert {"lime_white", "plinth_blue", "asphalt", "paving", "road_paint", "sidewalk", "curb"} <= {m["name"] for m in gltf["materials"]}
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


def test_dressing_is_deterministic_and_on_the_walls(world, plan, built_tile):
    from shapely.geometry import Point
    from citygen.mesh.tile import build_tile
    tc, i, j, first = built_tile
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


@pytest.fixture(scope="module")
def ground(world, plan):
    from citygen.city.ground import Ground
    return Ground(world, [plan])


def test_ground_heights_are_the_same_on_both_sides_of_a_tile_edge(ground, plan):
    c = plan.boundary.centroid
    x0 = 512.0 * round(c.x / 512.0)          # a tile edge crossing the city
    ys = np.linspace(c.y - 200.0, c.y + 200.0, 41)
    first = ground.height(np.full_like(ys, x0), ys)
    other = ground.height(np.full_like(ys, x0) - 400.0, ys - 400.0)   # fill other lattice cells
    second = ground.height(np.full_like(ys, x0), ys)
    assert np.array_equal(first, second)
    assert np.all(np.isfinite(first)) and np.ptp(first) > 1.0        # a slope, not a flat line
    assert other.shape == first.shape


def test_ground_is_deterministic_and_natural_outside_cities(world, plan, ground):
    from citygen.city.ground import Ground
    c = plan.boundary.centroid
    pts = np.stack([c.x + np.linspace(-300.0, 300.0, 60), c.y + np.linspace(-250.0, 250.0, 60)], axis=1)
    again = Ground(world, [plan]).height(pts[:, 0], pts[:, 1])
    assert np.array_equal(ground.height(pts[:, 0], pts[:, 1]), again)
    x0, y0, _, _ = plan.boundary.bounds
    outside = np.array([[x0 - 60.0, y0 - 60.0], [x0 - 300.0, y0 - 20.0]])
    assert np.array_equal(ground.height(outside[:, 0], outside[:, 1]),
                          world.terrain.height(outside[:, 0], outside[:, 1]))


def test_terraced_blocks_stay_within_terrace_max(plan, ground):
    from citygen.city.geo import jittered_grid
    from citygen.city.ground import NO_TERRACE
    checked = 0
    for poly, did in plan.blocks:
        if plan.districts[did].kind in NO_TERRACE or poly.area > ground.terrace_max_area:
            continue
        if poly.distance(plan.boundary.boundary) <= ground.edge_band:
            continue                                    # the city edge blend would mix in raw terrain
        inner = poly.buffer(-(ground.edge + 2.0))       # deep enough that the terrace is complete
        if inner.is_empty:
            continue
        pts = jittered_grid(inner, 10.0, np.random.default_rng(5))
        if not len(pts):
            continue
        h = ground.height(pts[:, 0], pts[:, 1])
        blur = ground.blur(pts[:, 0], pts[:, 1])
        assert np.all(np.isfinite(blur))
        assert np.max(np.abs(h - blur)) <= ground.terrace_max + 1e-6
        checked += 1
        if checked == 4:
            break
    assert checked >= 2


def _drawn_height(ground, step: float, x, y):
    """Bilinear height of the terrain mesh as drawn, on the world-aligned `terrain_step` grid."""
    x, y = np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)
    gx, gy = np.floor(x / step) * step, np.floor(y / step) * step
    tx, ty = (x - gx) / step, (y - gy) / step
    h00 = ground.height(gx, gy)
    h10 = ground.height(gx + step, gy)
    h01 = ground.height(gx, gy + step)
    h11 = ground.height(gx + step, gy + step)
    top = h00 * (1.0 - tx) + h10 * tx
    bottom = h01 * (1.0 - tx) + h11 * tx
    return top * (1.0 - ty) + bottom * ty


def test_every_street_ribbon_stays_above_the_drawn_terrain(world, plan, ground):
    from shapely import line_interpolate_point
    step = float(world.cfg["tiles"]["terrain_step"])
    pts = []
    for st in plan.streets:
        d = np.arange(0.0, st.line.length, 4.0)
        pts.append(shapely.get_coordinates(line_interpolate_point(st.line, d)))
    pts = np.concatenate(pts)
    drawn = _drawn_height(ground, step, pts[:, 0], pts[:, 1])
    top = ground.surface(pts[:, 0], pts[:, 1])
    assert len(pts) > 1000
    assert np.all(drawn <= top + 1e-6), np.max(drawn - top)
    assert np.max(top - ground.height(pts[:, 0], pts[:, 1])) >= 0.18 - 1e-6   # ribbons really were sampled


@pytest.fixture(scope="module")
def built_mesh(world, plan, ground):
    from citygen.mesh.tile import build_tile
    tc = TileContext(world, [plan])
    s = world.capital()
    i, j = int(s.x // tc.size), int(s.y // tc.size)
    mb, placements = build_tile(tc, i, j)
    return tc, i, j, mb, placements


@pytest.fixture(scope="module")
def built_tile(built_mesh):
    tc, i, j, _, placements = built_mesh
    return tc, i, j, placements


def test_wall_feet_stay_in_the_terrain_and_doors_meet_the_street(world, plan, ground, built_tile):
    from shapely.geometry.polygon import orient
    tc, _, _, placements = built_tile
    rings = [np.asarray(orient(b.footprint, 1.0).exterior.coords) for b in plan.buildings]
    counts = np.array([len(r) for r in rings])
    starts = np.concatenate([[0], np.cumsum(counts)[:-1]])
    pts = np.concatenate(rings)
    low = np.minimum.reduceat(tc.height(pts[:, 0], pts[:, 1]), starts)
    rings = [(k, ring) for k, b in enumerate(plan.buildings)
             for ring in (b.footprint.exterior, *b.footprint.interiors)]
    lines = shapely.segmentize(np.array([ring for _, ring in rings], dtype=object), 1.0)
    n = shapely.get_num_coordinates(lines)
    starts = np.concatenate([[0], np.cumsum(n)[:-1]])
    pts = shapely.get_coordinates(lines)
    drawn = np.minimum.reduceat(tc.height(pts[:, 0], pts[:, 1]), starts)
    bottom = low[np.array([k for k, _ in rings])] - 0.6
    assert np.all(drawn >= bottom - 1e-6), float(np.min(drawn - bottom))
    doors = [p for p in placements if tc.kit.pieces[p.piece].category == "door"]
    assert doors
    front = np.array([(p.x - math.sin(p.yaw) * 0.5, p.y + math.cos(p.yaw) * 0.5) for p in doors])
    zs = np.array([p.z for p in doors])
    assert np.all(np.abs(zs - ground.surface(front[:, 0], front[:, 1])) <= 0.05)


def test_dressing_ground_pieces_stand_on_the_surface(world, plan, ground):
    from citygen.city.dressing import DRESSED, Dresser, ground_heights
    from citygen.kit import make_kit
    kit = make_kit(world.seed, world.cfg, world.style)
    dresser = Dresser(world, plan, kit, ground)
    chosen = next((k for k, b in enumerate(plan.buildings)
                   if b.kind in DRESSED and any(f.kind == "souk" for f in dresser.facades(b))), None)
    assert chosen is not None
    b = plan.buildings[chosen]
    ring = np.asarray(b.footprint.exterior.coords)
    out = dresser.building(chosen, float(ground.height(ring[:, 0], ring[:, 1]).max()))
    pieces = [p for p in out if p.on_ground and abs(p.z) < 1e-9]   # bottoms that stand on the ground
    assert pieces and any(ground.surface(p.x, p.y) - ground.height(p.x, p.y) > 0.1 for p in pieces)
    ground_heights(ground, pieces)
    for p in pieces:
        assert abs(p.z - ground.surface(p.x, p.y)) <= 0.05, p.piece


def test_parapets_and_stair_rooms_follow_the_style(world, plan):
    from citygen.city.roofs import roof_layout, roof_stream
    from shapely.geometry import Point
    cfg = world.style["roofs"]
    thick = float(cfg["parapet_thickness"])
    seen = {"house": [], "apartments": []}
    expected = {"house": [], "apartments": []}
    stairs = 0
    for k, b in enumerate(plan.buildings):
        if b.roof_shape != "flat":
            continue
        kind = plan.districts[b.district].kind
        layout = roof_layout(b, kind, roof_stream(world.seed, plan.settlement.id, k), cfg)
        assert layout.band is not None and layout.inner is not None
        assert layout.height == pytest.approx(cfg["parapet_height"].get(kind, cfg["parapet_fallback"]))
        assert 0.6 <= layout.height <= 1.0
        thin = b.footprint.buffer(-thick, join_style="mitre")
        assert layout.inner.symmetric_difference(thin).area < 1e-6      # a 0.2 m band
        if b.kind in seen:
            seen[b.kind].append(layout.stair is not None)
            expected[b.kind].append(cfg["stair_room"].get(kind, 0.0))
        if layout.stair is None:
            continue
        stairs += 1
        assert layout.stair.area == pytest.approx(float(cfg["stair_side"]) ** 2, rel=1e-6)
        assert layout.stair_height == pytest.approx(float(cfg["stair_height"]))
        assert layout.inner.contains(layout.stair)
        x, y, yaw = layout.door
        assert layout.stair.exterior.distance(Point(x, y)) < 0.05       # the door sits on its wall
        assert layout.free.contains(Point(x + math.cos(yaw) * 0.5, y + math.sin(yaw) * 0.5))
    assert stairs > 50
    for kind in seen:
        assert len(seen[kind]) > 100
        got, want = float(np.mean(seen[kind])), float(np.mean(expected[kind]))
        assert abs(got - want) < 0.06, (kind, got, want)                # the style share is the share built
    assert 0.2 < np.mean(seen["house"]) < 0.45
    assert 0.45 < np.mean(seen["apartments"]) < 0.72


def test_roof_props_stay_inside_the_parapet_and_off_the_stair_room(world, plan, built_tile):
    from citygen.city.dressing import building_highs
    from citygen.city.roofs import roof_layout, roof_stream
    from shapely.geometry import Point
    tc, _, _, placements = built_tile
    roles = world.style["dressing"]["roles"]
    pieces = {option[0] for role in ("roof_tank", "roof_dish", "roof_laundry", "roof_pot")
              for option in roles[role]}
    tree = STRtree([b.footprint for b in plan.buildings])
    props = stairs = 0
    for p in placements:
        if p.piece not in pieces:
            continue                                # the same pieces also stand in the street
        point = Point(p.x, p.y)
        k = int(tree.query_nearest(point)[0])
        b = plan.buildings[k]
        if not b.footprint.contains(point):
            continue
        high = building_highs(tc.ground, [b])[0]
        if abs(p.z - (high + b.height)) > 1e-6:
            continue                                # a pot on a windowsill or a sidewalk, not a roof
        props += 1
        layout = roof_layout(b, plan.districts[b.district].kind,
                             roof_stream(world.seed, plan.settlement.id, k), tc.roofs)
        assert layout.free is not None
        assert layout.free.contains(point), (p.piece, k)
        if layout.stair is not None:
            stairs += 1
            assert not layout.stair.buffer(0.05).contains(point)
    assert props > 20
    assert stairs > 0                                                   # the stair room really was avoided


def test_sidewalks_are_raised_and_leave_a_carriageway(world, plan, ground):
    from citygen.city.ground import STREET_LIFT
    from citygen.city.walks import NO_WALK
    min_car = float(world.style["streets"]["min_carriageway"])
    curb = float(world.style["streets"]["curb_height"])
    walks = [w for w in plan.walks if w.kind == "sidewalk"]
    assert len(walks) > 50
    footprints = STRtree([b.footprint for b in plan.buildings])
    for w in walks:
        st = plan.streets[w.street]
        assert st.kind not in ("souk", "alley")
        assert plan.districts[w.district].kind not in NO_WALK
        assert w.width <= (st.width - min_car) / 2.0 + 0.1
        assert w.polygon.intersection(st.line.buffer(min_car / 2.0)).area < 0.1
        p = w.polygon.representative_point()
        assert ground.surface(p.x, p.y) >= (ground.height(p.x, p.y)
                                            + STREET_LIFT.get(st.kind, 0.24) + curb - 1e-6)
        pts = shapely.get_coordinates(w.polygon.exterior)[:3]
        xy = np.asarray(pts)
        top = ground.surface(xy[:, 0], xy[:, 1])
        expect = ground.height(xy[:, 0], xy[:, 1]) + ground.lift(xy[:, 0], xy[:, 1], ground.walk_reach) + curb
        assert np.all(np.abs(top - expect) < 1e-6)
        for k in footprints.query(w.polygon, predicate="intersects"):
            assert w.polygon.intersection(plan.buildings[int(k)].footprint).area < 0.05


def test_drawn_sidewalks_and_paint_stay_above_the_ribbon(world, plan, ground):
    # the triangles as mesh/tile.py draws them, checked at their centers: long blocks and lines
    # must follow the ground, and no sidewalk corner on the block side may miss its street
    from citygen.city.ground import STREET_LIFT
    from citygen.mesh.builder import triangulate
    cfg = world.style["streets"]
    curb, lift = float(cfg["curb_height"]), float(cfg["paint_lift"])

    def centers(poly, top, step):
        tri = triangulate(shapely.segmentize(poly, step))
        z = top(tri[..., 0].ravel(), tri[..., 1].ravel()).reshape(-1, 3).mean(axis=1)
        c = tri.mean(axis=1)
        return z, ground.height(c[:, 0], c[:, 1]) + ground.lift(c[:, 0], c[:, 1])

    for w in plan.walks:
        z, ribbon = centers(w.polygon, ground.walk_top, float(cfg["walk_step"]))
        assert np.all(z >= ribbon + 0.5 * curb)   # a junction with a higher ribbon eats part of the curb
    for m in plan.paint:
        z0 = STREET_LIFT.get(plan.streets[m.street].kind, 0.24) + lift
        z, ribbon = centers(m.polygon, lambda x, y: ground.height(x, y) + z0, float(cfg["paint_step"]))
        assert np.all(z >= ribbon - 0.01)       # under a crossing street's higher ribbon is fine


def test_street_paint_stays_inside_its_carriageway(world, plan):
    from citygen.city.paint import carriageway
    promenade = float(world.style["streets"]["promenade_width"])
    min_width = float(world.style["streets"]["marking_min_width"])
    assert plan.paint
    areas = {}
    for mark in plan.paint:
        k = mark.street
        if k not in areas:
            areas[k] = carriageway(plan, k, promenade)
        assert plan.streets[k].width > min_width
        assert plan.streets[k].kind in ("boulevard", "arterial", "connector")
        assert areas[k].buffer(0.01).contains(mark.polygon)
    kinds = {plan.streets[m.street].kind for m in plan.paint}
    assert {"boulevard", "arterial"} <= kinds


def test_street_surfaces_come_from_the_style(world, plan):
    from citygen.city.model import District, Street
    from citygen.city.paint import street_surfaces
    table = world.style["streets"]["surface"]
    for st in plan.streets:
        assert st.surface == table[st.kind]
    village = District(0, "village", "Test", shapely.box(0.0, 0.0, 300.0, 300.0))
    lane = Street("street", 9.0, shapely.LineString([(10.0, 10.0), (250.0, 250.0)]))
    street_surfaces([village], [lane], world.style)
    assert lane.surface == "earth"


def test_boulevard_gets_a_raised_promenade(world, plan, ground):
    from shapely import line_interpolate_point
    from citygen.city.ground import STREET_LIFT
    promenade = [w for w in plan.walks if w.kind == "promenade"]
    assert promenade
    width = float(world.style["streets"]["promenade_width"])
    curb = float(world.style["streets"]["curb_height"])
    for w in promenade:
        st = plan.streets[w.street]
        assert st.kind == "boulevard" and abs(w.width - width) < 1e-6
        p = w.polygon.representative_point()
        assert ground.surface(p.x, p.y) >= (ground.height(p.x, p.y)
                                            + STREET_LIFT["boulevard"] + curb - 1e-6)
    for st in (s for s in plan.streets if s.kind == "boulevard"):
        pts = shapely.get_coordinates(line_interpolate_point(st.line, np.arange(0.0, st.line.length, 4.0)))
        top = ground.surface(pts[:, 0], pts[:, 1])
        assert np.all(top - ground.height(pts[:, 0], pts[:, 1])
                      >= STREET_LIFT["boulevard"] + curb - 1e-6)


def test_skirt_triangles_face_outward():
    from citygen.mesh.builder import add_skirt
    mb = MeshBuilder()
    ring = np.array([[0.0, 0.0], [2.0, 0.0], [2.0, 2.0], [0.0, 2.0]])
    add_skirt(mb, ring, np.ones(4), np.zeros(4), "curb")
    part = mb.gltf_parts()["curb"]
    tri = part["pos"][part["idx"].reshape(-1, 3)]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    assert np.all(np.einsum("ij,ij->i", n, part["nrm"][part["idx"].reshape(-1, 3)[:, 0]]) > 0.0)


GROUND = {"beach", "desert", "steppe", "grass", "forest", "rock", "urban_ground"}
STREET_SURFACES = {"asphalt", "paving", "earth", "sidewalk", "curb"}


def _world_parts(mb):
    """Tile parts back in generator axes: {material: (xyz, uv, (T, 3) triangles, col or None)}."""
    out = {}
    for name, part in mb.gltf_parts().items():
        p = part["pos"]
        xyz = np.stack([p[:, 0], -p[:, 2], p[:, 1]], axis=1) + mb.origin
        out[name] = (xyz, part["uv"], part["idx"].reshape(-1, 3), part.get("col"))
    return out


def _uv_gradients(xyz, uv, tri):
    """Per flat triangle: the world (x, y) direction in which u and v grow, per meter."""
    e1 = xyz[tri[:, 1], :2] - xyz[tri[:, 0], :2]
    e2 = xyz[tri[:, 2], :2] - xyz[tri[:, 0], :2]
    m = np.stack([e1, e2], axis=1)
    keep = np.abs(np.linalg.det(m)) > 1e-3
    d = np.stack([uv[tri[:, 1]] - uv[tri[:, 0]], uv[tri[:, 2]] - uv[tri[:, 0]]], axis=1)
    g = np.linalg.solve(m[keep], d[keep])          # rows: d/dx, d/dy; columns: u, v
    return keep, g[:, :, 0], g[:, :, 1]


def _street_direction_at(plan, points):
    lines_ = [s.line for s in plan.streets]
    tree = STRtree(lines_)
    out = []
    for x, y in points:
        line = lines_[int(tree.nearest(shapely.Point(x, y)))]
        d = line.project(shapely.Point(x, y))
        a, b = line.interpolate(max(d - 1.0, 0.0)), line.interpolate(min(d + 1.0, line.length))
        v = np.array([b.x - a.x, b.y - a.y])
        out.append(v / max(np.hypot(*v), 1e-9))
    return np.array(out)


def test_ground_and_street_materials_name_existing_textures(world):
    palette, textures = world.style["palette"], world.style["textures"]
    for name in GROUND | STREET_SURFACES:
        assert palette[name].get("texture") in NAMES, name
        assert palette[name]["texture"] in textures, name
    assert not palette["road_paint"].get("texture")      # markings stay flat paint


def test_terrain_tint_is_on_terrain_parts_only(built_mesh):
    *_, mb, _ = built_mesh
    parts = _world_parts(mb)
    tinted = {name for name, (*_, col) in parts.items() if col is not None}
    assert "urban_ground" in tinted and tinted <= GROUND, tinted
    for name in tinted:
        col = parts[name][3]
        assert col.shape[1] == 3 and col.min() > 0.8 and col.max() <= 1.0, name   # subtle, never black
        assert np.ptp(col.sum(axis=1)) > 0.005, name                                 # it does vary


def test_terrain_tint_matches_on_both_sides_of_a_tile_edge(world, plan):
    from citygen.mesh.builder import MeshBuilder as MB
    from citygen.mesh.tile import terrain_mesh
    tc = TileContext(world, [plan])
    s = world.capital()
    i, j = int(s.x // tc.size), int(s.y // tc.size)
    edge = (i + 1) * tc.size
    sides = []
    for ii in (i, i + 1):
        mb = MB(origin=(ii * tc.size, j * tc.size))
        terrain_mesh(mb, tc, ii * tc.size, j * tc.size)
        rows = [np.column_stack([xyz[:, :2], col]) for xyz, _, _, col in _world_parts(mb).values()
                if col is not None]
        pts = np.concatenate(rows)
        on = pts[np.abs(pts[:, 0] - edge) < 1e-6]
        sides.append(on[np.lexsort((on[:, 1],))])
    a, b = (np.unique(np.round(side, 6), axis=0) for side in sides)
    assert len(a) > 30 and np.array_equal(a, b)


def test_street_ribbons_run_u_along_the_street_and_continue_across_tiles(world, plan):
    from citygen.mesh.builder import MeshBuilder as MB
    from citygen.mesh.tile import street_meshes
    tc = TileContext(world, [plan])
    tree = STRtree([st.line for st in plan.streets])
    s = world.capital()
    i, j = int(s.x // tc.size), int(s.y // tc.size)
    halves = []
    for ii in (i, i + 1):
        mb = MB(origin=(ii * tc.size, j * tc.size))
        street_meshes(mb, tc, plan, tree, shapely.box(*(ii * tc.size, j * tc.size,
                                                        (ii + 1) * tc.size, (j + 1) * tc.size)))
        halves.append(_world_parts(mb))
    for name in ("asphalt", "paving"):
        xyz, uv, tri, col = halves[0][name]
        assert col is None
        keep, gu, gv = _uv_gradients(xyz, uv, tri)
        along = _street_direction_at(plan, xyz[tri[keep]].mean(axis=1)[:, :2])
        cos = np.abs(np.einsum("ij,ij->i", gu, along)) / np.hypot(gu[:, 0], gu[:, 1])
        assert np.mean(cos > 0.95) > 0.85, (name, np.mean(cos > 0.95))   # u follows the street (junctions overlap)
        assert np.median(np.hypot(gu[:, 0], gu[:, 1])) == pytest.approx(1.0, abs=0.05)   # meters
        assert np.median(np.abs(np.einsum("ij,ij->i", gv, along))) < 0.05    # v runs across
    # where a street crosses the tile edge, both tiles draw the same end corner: same UV there
    meets = 0
    for name in set(halves[0]) & set(halves[1]):
        (a_xyz, a_uv), (b_xyz, b_uv) = halves[0][name][:2], halves[1][name][:2]
        other = {tuple(np.round(p, 4)): u for p, u in zip(b_xyz, b_uv)}
        for p, u in zip(a_xyz, a_uv):
            match = other.get(tuple(np.round(p, 4)))
            if match is not None:
                assert np.allclose(match, u, atol=1e-3), (name, p, u, match)
                meets += 1
    assert meets >= 4                                     # some ribbons really cross the edge


def test_sidewalk_rows_follow_the_street_and_curb_faces_hang_from_the_top(world, plan):
    from citygen.mesh.builder import MeshBuilder as MB
    from citygen.mesh.tile import walk_meshes
    tc = TileContext(world, [plan])
    s = world.capital()
    i, j = int(s.x // tc.size), int(s.y // tc.size)
    mb = MB(origin=(i * tc.size, j * tc.size))
    walk_meshes(mb, tc, plan, shapely.box(i * tc.size, j * tc.size, (i + 1) * tc.size, (j + 1) * tc.size),
                STRtree([st.line for st in plan.streets]))
    parts = _world_parts(mb)
    xyz, uv, tri, _ = parts["sidewalk"]
    keep, gu, _ = _uv_gradients(xyz, uv, tri)
    along = _street_direction_at(plan, xyz[tri[keep]].mean(axis=1)[:, :2])
    cos = np.abs(np.einsum("ij,ij->i", gu, along)) / np.hypot(gu[:, 0], gu[:, 1])
    assert np.mean(cos > 0.95) > 0.9, np.mean(cos > 0.95)   # slab rows turn with the street
    xyz, uv, tri, _ = parts["curb"]
    t = xyz[tri]                                             # (T, 3, 3)
    tu, tv = uv[tri][..., 0], uv[tri][..., 1]
    assert np.allclose(tv.min(axis=1), 0.0, atol=1e-9)        # every face starts at the curb top
    for a, b in ((0, 1), (1, 2), (0, 2)):
        flat = np.hypot(*(t[:, a, :2] - t[:, b, :2]).T)
        dz = t[:, a, 2] - t[:, b, 2]
        same = flat < 1e-9                                  # one corner above the other
        assert np.allclose(tv[same, a] - tv[same, b], -dz[same], atol=1e-9)   # v grows downward, in meters
        assert np.allclose(np.abs(tu[~same, a] - tu[~same, b]), flat[~same], atol=1e-6)   # u along the curb


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


def test_finished_tiles_need_their_textures(tmp_path):
    from citygen.build import finished_tiles
    (tmp_path / "tile_0_0.glb").write_bytes(b"abc")
    journal = tmp_path / "journal"
    journal.mkdir()
    entry = {"i": 0, "j": 0, "file": "tile_0_0.glb", "bytes": 3, "files": ["textures/test.png"]}
    (journal / "tile_0_0.json").write_text(json.dumps(entry))
    assert finished_tiles(tmp_path, journal, "k", [(0, 0)]) == {}   # the shared image is still missing
    (tmp_path / "textures").mkdir()
    (tmp_path / "textures" / "test.png").write_bytes(b"png")
    assert (0, 0) in finished_tiles(tmp_path, journal, "k", [(0, 0)])


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
