"""Fast checks for the whole pipeline (about 20 seconds). Run: python -m pytest -q"""
import functools
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
from citygen.mesh.gltf import accessor_array, read_glb, read_parts, triangle_count, write_glb
from citygen.mesh.textures import (NAMES, PIXELS, encoded, images_for, spec_for, texture,
                                    texture_names, write_shared_textures)
from citygen.mesh.tile import TileContext, texture_files
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
    fort = [(b.kind, b.footprint.wkb, b.arches, b.battlement) for b in plan.buildings if b.kind.startswith("kasbah")]
    assert fort and fort == [(b.kind, b.footprint.wkb, b.arches, b.battlement)
                             for b in again.buildings if b.kind.startswith("kasbah")]
    assert [m for m in again.landmarks if m.kind == "kasbah"] == [m for m in plan.landmarks if m.kind == "kasbah"]
    assert again.station.facade == plan.station.facade                       # the railway station (prompt 33)
    assert [t.wkb for t in again.station.tracks] == [t.wkb for t in plan.station.tracks]
    assert [q.line.wkb for q in again.port.quays] == [q.line.wkb for q in plan.port.quays]   # the harbor (prompt 34)
    assert [(b.line.wkb, b.light) for b in again.port.breakwaters] == [(b.line.wkb, b.light) for b in plan.port.breakwaters]
    assert again.landmarks[-1] == plan.landmarks[-1] and again.land.equals_exact(plan.land, 1e-9)


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


@functools.lru_cache(maxsize=None)
def _texture(name: str, size: int):
    """Texture images shared by the texture tests (each one costs up to 0.1 s)."""
    return texture(name, 42, {"pixels": size})


def test_texture_sizes_follow_the_style():
    for name in NAMES:
        for size in PIXELS:
            assert _texture(name, size).size == (size, size)
    with pytest.raises(ValueError):
        texture("unobtainium", 4)


def test_textures_are_seamless():
    """The last column/row is as close to the first as any two neighbours inside the image."""
    for name in NAMES:
        a = np.asarray(_texture(name, 256), dtype=np.float64)
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


def test_tile_is_valid_glb(rebuilt_tile):
    _, path, info = rebuilt_tile
    gltf, binary = read_glb(path)
    assert triangle_count(gltf) == info["triangles"] > 1000
    assert {"lime_white", "plinth_blue", "asphalt", "paving", "road_paint", "sidewalk", "curb"} <= {m["name"] for m in gltf["materials"]}
    assert gltf["extensionsRequired"] == ["KHR_mesh_quantization"]      # [tiles] quantize (prompt 39)
    own = [n["mesh"] for n in gltf["nodes"] if "mesh" in n and "extensions" not in n]
    assert len(own) == 2 and gltf["nodes"][gltf["nodes"][0]["children"][0]]["extras"] == {"quantized": True}
    for view in gltf["bufferViews"]:
        assert view["byteOffset"] + view["byteLength"] <= len(binary)
    for prim in (p for k in own for p in gltf["meshes"][k]["primitives"]):
        count = gltf["accessors"][prim["attributes"]["POSITION"]]["count"]
        acc = gltf["accessors"][prim["indices"]]
        assert acc["componentType"] == 5123 and count < 65536      # 16-bit indices everywhere
        assert accessor_array(gltf, binary, prim["indices"]).max() < count


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
        pa, pb = mb.gltf_parts(), b[name].gltf_parts()
        fruit = len(pa["fruit_orange"]["idx"]) // 3 if "fruit_orange" in pa else 0   # citrus (prompt 24)
        assert 60 <= mb.triangles - fruit <= 200, (name, mb.triangles)
        assert (fruit > 0) == name.startswith("tree_citrus") and fruit <= 120, (name, fruit)
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
    slab = kit.pieces["balcony_slab"].parts["concrete"]                 # level faces get planar UVs
    tri = slab["idx"].reshape(-1, 3)
    level = np.abs(slab["nrm"][tri[:, 0], 1]) > 0.9                   # glTF y is up
    uv = slab["uv"][tri[level]]
    e1, e2 = uv[:, 1] - uv[:, 0], uv[:, 2] - uv[:, 0]
    area = np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]) / 2
    assert level.sum() >= 4 and np.all(area > 1e-4)
    kit_pieces =[n for n, p in kit.pieces.items() if p.source != "procedural"]
    assert all(n.startswith(kit.pieces[n].source + "/") for n in kit_pieces)   # kit pieces never replace ours
    for role, options in world.style["dressing"]["roles"].items():
        for option in options:
            name = option[0]
            if "/" not in name or name.split("/")[0] in {p.source for p in kit.pieces.values()}:
                assert name in kit.pieces, f"role {role}: unknown piece {name}"
    for souk in world.style["souk"]:
        for name in souk["ground"] + souk["wall"]:
            assert name in world.style["dressing"]["roles"] or name in kit.pieces or "/" in name, name


def test_blender_kit_fixture(world, plan):
    """Prompt 38: pieces exported by tools/blender_kit_export.py (fixture made in Blender 5.2 from
    tests/data/blender_kit/source.py) load through Kit facing the street and can play a role."""
    import copy
    import sys
    from pathlib import Path
    from citygen.city.dressing import Dresser
    from citygen.kit import Kit
    from citygen.mesh.gltf import hex_to_rgb, srgb_to_linear
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
    from blender_kit_export import front_of, linear_to_srgb_hex, piece_name
    style = copy.deepcopy(world.style)
    style["dressing"]["roles"]["door_blue_rich"] = [["blender_kit/house", 1]]
    kit = Kit(world.seed, [str(Path(__file__).parent / "data" / "blender_kit")], style["palette"])
    house, arrow = kit.pieces["blender_kit/house"], kit.pieces["blender_kit/arrow"]
    assert (house.category, house.anchor, house.tags) == ("house", "ground", ("test", "door"))
    assert (arrow.category, arrow.anchor) == ("sign", "ground")        # no anchor property: the default
    walls = house.parts["cabin_white"]["pos"]                          # 2 m walls, object scale 1.5 baked
    assert np.allclose([walls.min(axis=0), walls.max(axis=0)], [[-1.5, 0.0, -1.5], [1.5, 3.0, 1.5]], atol=1e-4)
    door = house.parts["blender_kit_door_blue"]["pos"]                 # modeled facing -Y, turned on export
    assert np.allclose([door[:, 2].min(), door[:, 2].max()], [-1.65, -1.5], atol=1e-4)   # front: glTF -Z
    tip = arrow.parts["blender_kit_arrow_yellow"]["pos"]               # rotation baked: the tip is at -Z
    assert np.isclose(tip[:, 2].min(), -0.8, atol=1e-4) and abs(tip[tip[:, 2].argmin(), 0]) < 1e-4
    assert kit.materials["blender_kit_door_blue"]["color"] == "#1F5FA8"
    assert kit.materials["blender_kit_arrow_yellow"] == {"color": "#E8B82E", "roughness": 0.4, "metallic": 0.0,
                                                        "note": "Blender material 'Arrow Yellow'"}
    assert kit.materials["cabin_white"] == style["palette"]["cabin_white"]   # a palette name keeps its look
    for color in ("#1F5FA8", "#000000", "#FFFFFF", "#7F8081"):
        assert linear_to_srgb_hex(srgb_to_linear(hex_to_rgb(color))) == color
    assert (piece_name("Door Blue.001"), front_of("-y", "+Y"), front_of(None, "+Y"), front_of("x", "+Y")) == \
        ("door_blue_001", "-Y", "+Y", None)
    test_world = copy.copy(world)
    test_world.style = style
    dresser = Dresser(test_world, plan, kit, None)
    assert dresser.pick("door_blue_rich", stream(1, "test")) == ("blender_kit/house", 0.0)


def test_dressing_is_deterministic_and_on_the_walls(world, plan, built_tile, rebuilt_tile):
    from shapely.geometry import Point
    tc, i, j, first = built_tile
    again = rebuilt_tile[0]
    assert len(first) > 200 and [(p.piece, p.x, p.y, p.z) for p in first] == [(p.piece, p.x, p.y, p.z) for p in again]
    assert all(p.piece in tc.kit.pieces and np.isfinite([p.x, p.y, p.z, p.yaw, p.scale]).all() for p in first)
    tree = STRtree([b.footprint.exterior for b in plan.buildings])
    doors = [p for p in first if tc.kit.pieces[p.piece].category == "door"]
    assert doors
    for p in doors:   # every door stands on a building wall
        near = tree.query_nearest(Point(p.x, p.y))
        assert plan.buildings[int(near[0])].footprint.exterior.distance(Point(p.x, p.y)) < 0.05


def test_tile_instances_are_valid(rebuilt_tile):
    _, path, info = rebuilt_tile
    gltf, binary = read_glb(path)
    assert "EXT_mesh_gpu_instancing" in gltf["extensionsUsed"]
    nodes = [n for n in gltf["nodes"] if "EXT_mesh_gpu_instancing" in n.get("extensions", {})]
    assert sum(gltf["accessors"][n["extensions"]["EXT_mesh_gpu_instancing"]["attributes"]["TRANSLATION"]]["count"]
               for n in nodes) == info["pieces"] > 100
    for n in nodes:
        attrs = n["extensions"]["EXT_mesh_gpu_instancing"]["attributes"]
        acc = gltf["accessors"][attrs["ROTATION"]]
        q = accessor_array(gltf, binary, attrs["ROTATION"])
        assert acc["componentType"] == 5122 and acc["normalized"]     # normalized SHORT (prompt 39)
        assert np.allclose(np.linalg.norm(q, axis=1), 1.0, atol=1e-4)
        assert acc["count"] == gltf["accessors"][attrs["TRANSLATION"]]["count"]


def _check_glb(gltf: dict, binary: bytes) -> None:
    """The glTF rules a quantized tile could break: views inside the buffer, accessors inside their views,
    vertex elements on 4-byte boundaries, required extensions also listed as used."""
    assert set(gltf.get("extensionsRequired", [])) <= set(gltf.get("extensionsUsed", []))
    size = {5126: 4, 5125: 4, 5123: 2, 5122: 2, 5121: 1, 5120: 1}
    width = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}
    for view in gltf["bufferViews"]:
        assert view["byteOffset"] + view["byteLength"] <= len(binary) and view["byteOffset"] % 4 == 0
        assert view.get("byteStride", 4) % 4 == 0
    for acc in gltf["accessors"]:
        view = gltf["bufferViews"][acc["bufferView"]]
        element = size[acc["componentType"]] * width[acc["type"]]
        stride = view.get("byteStride", element)
        offset = acc.get("byteOffset", 0)
        assert offset % size[acc["componentType"]] == 0 and stride >= element
        assert offset + stride * (acc["count"] - 1) + element <= view["byteLength"]
        if view.get("target") == 34962:
            assert offset % 4 == 0


def _sorted_triangles(parts: dict, order: dict) -> dict:
    """{material: (T, 3, k) vertex rows of every triangle}, triangles taken in `order[material]`."""
    out = {}
    for mat, part in parts.items():
        cols = [part["pos"]] + [part[k] for k in ("nrm", "uv", "col") if part.get(k) is not None]
        rows = np.concatenate([np.asarray(c, dtype=np.float64).reshape(len(part["pos"]), -1) for c in cols], axis=1)
        tris = rows[np.asarray(part["idx"]).reshape(-1, 3)]
        out[mat] = tris[order[mat]] if mat in order else tris
    return out


def test_quantized_tile_matches_the_float_tile(built_mesh, tmp_path):
    """Prompt 39: the KHR_mesh_quantization write of a tile draws the float tile within half a position
    step, int8 or recomputed flat normals, the same UVs and colors, and the same instance placements."""
    from citygen.mesh.gltf import _split_fine
    from citygen.mesh.tile import instance_groups, tile_bounds
    tc, i, j, mb, placements = built_mesh
    x0, y0, _, _ = tile_bounds(tc, i, j)
    instances = instance_groups(tc, placements, x0, y0)
    parts = mb.gltf_parts(fine=True)
    q = dict(tc.quantize, quantize=True)
    full = {mode: write_glb(tmp_path / f"full{mode}.glb", parts, tc.materials, name="t", instances=instances,
                            **dict(q, quantize=mode)) for mode in (False, True)}
    assert full[True] < 0.7 * full[False]
    write_glb(tmp_path / "True.glb", parts, tc.materials, name="t", **q)
    gltf, binary = read_glb(tmp_path / "fullTrue.glb")
    _check_glb(gltf, binary)
    assert gltf["extensionsRequired"] == ["KHR_mesh_quantization"]
    assert {"KHR_mesh_quantization", "EXT_mesh_gpu_instancing"} <= set(gltf["extensionsUsed"])
    child = gltf["nodes"][gltf["nodes"][0]["children"][0]]
    half = child["scale"][0]
    assert child["scale"] == [half] * 3 and "rotation" not in child          # a uniform dequantization only
    fine, coarse = _split_fine(parts, set(q["float_materials"]), q["fine_edge"])
    assert "road_paint" in coarse and "cloth_1" not in coarse and "water" not in coarse   # sheets stay float
    # the tile's own mesh, triangle by triangle: sort both by their corners on the quantization grid
    center = np.asarray(child["translation"])
    got = read_parts(tmp_path / "True.glb")
    step = half / 32767.0
    for mat, part in parts.items():
        want = _sorted_triangles({mat: part}, {})[mat]
        have = _sorted_triangles({mat: got[mat]}, {})[mat]
        assert want.shape[:2] == have.shape[:2], mat
        keep = {tuple(t) for t in np.asarray(fine[mat]["idx"]).reshape(-1, 3)} if mat in fine else set()
        floats = np.array([tuple(t) in keep for t in np.asarray(part["idx"]).reshape(-1, 3)], dtype=bool)
        corners = want[..., :3].copy()
        corners[floats] = corners[floats].astype(np.float32)     # float triangles are written as float32
        wk, hk = (np.concatenate([np.round((x - center) / step).reshape(len(x), -1),            # grid first,
                                  np.round(x * 1e4).reshape(len(x), -1)], axis=1).astype(np.int64)   # then float
                  for x in (corners, have[..., :3]))
        want, have = want[np.lexsort(wk.T[::-1])], have[np.lexsort(hk.T[::-1])]
        assert np.abs(have[..., :3] - want[..., :3]).max() <= step / 2 + 1e-4, mat
        n0, n1 = want[..., 3:6], have[..., 3:6]
        cos = (n0 * n1).sum(axis=2) / np.linalg.norm(n0, axis=2) / np.linalg.norm(n1, axis=2)
        assert cos.min() > np.cos(np.radians(1.5)), mat       # int8 normals, or recomputed flat ones within 1 degree
        uv = part.get("uv") is not None
        if uv:
            assert np.array_equal(have[..., 6:8], want[..., 6:8].astype(np.float32)), mat     # float UVs kept
        if part.get("col") is not None:
            c = 8 if uv else 6
            assert np.abs(have[..., c:c + 3] - want[..., c:c + 3]).max() <= 0.5 / 255 + 1e-6, mat
    prims = [p for k in (0, 1) for p in gltf["meshes"][k]["primitives"]]
    flat = [p for p in prims if "NORMAL" not in p["attributes"]]
    assert flat and len(flat) < len(prims)             # walls and roofs lose NORMAL, the terrain keeps it
    assert all("NORMAL" in p["attributes"] for p in prims if "COLOR_0" in p["attributes"])
    # instances: each copy of each piece covers the same box as in the float tile
    nodes = [n for n in gltf["nodes"] if "EXT_mesh_gpu_instancing" in n.get("extensions", {})]
    assert [n["name"] for n in nodes] == [g["name"] for g in instances]
    worst, folded = 0.0, 0
    for n, inst in zip(nodes, instances):
        attrs = n["extensions"]["EXT_mesh_gpu_instancing"]["attributes"]
        prim = gltf["meshes"][n["mesh"]]["primitives"][0]
        local = np.concatenate([accessor_array(gltf, binary, p["attributes"]["POSITION"])   # flat and smooth
                                for p in gltf["meshes"][n["mesh"]]["primitives"] if p["material"] == prim["material"]])
        rq = accessor_array(gltf, binary, attrs["ROTATION"])
        dot = np.abs((rq / np.linalg.norm(rq, axis=1)[:, None] * inst["r"]).sum(axis=1))
        worst = max(worst, float(2 * np.arccos(np.minimum(dot, 1.0)).max()))
        t = accessor_array(gltf, binary, attrs["TRANSLATION"])
        if "SCALE" in attrs:
            s = accessor_array(gltf, binary, attrs["SCALE"])
        else:                                       # a float piece whose instances all have scale 1
            assert np.all(inst["s"] == 1.0) and gltf["accessors"][prim["attributes"]["POSITION"]]["componentType"] == 5126
            s = np.ones_like(t)
        folded += gltf["accessors"][prim["attributes"]["POSITION"]]["componentType"] == 5122
        src = inst["parts"][gltf["materials"][prim["material"]]["name"]]
        src = np.asarray(src["pos"], dtype=np.float64)[np.unique(np.asarray(src["idx"]))]
        for k in range(0, len(t), max(1, len(t) // 7)):
            got = _rot(np.repeat(rq[k:k + 1], len(local), 0), local * s[k]) + t[k]
            want = _rot(np.repeat(inst["r"][k:k + 1], len(src), 0), src * inst["s"][k]) + inst["t"][k]
            assert np.abs(got.min(0) - want.min(0)).max() < 2e-3 and np.abs(got.max(0) - want.max(0)).max() < 2e-3
    assert worst < 1e-4                             # 16-bit rotations: under 0.006 degrees off
    assert folded > 0


def _rot(q: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Rotate vectors (K, 3) by quaternions (K, 4) xyzw."""
    xyz, w = q[:, :3], q[:, 3:4]
    t = 2.0 * np.cross(xyz, v)
    return v + w * t + np.cross(xyz, t)


def test_quantized_parts_split_to_keep_16_bit_indices(tmp_path):
    """A part with more than 65535 distinct vertices becomes several primitives, all with 16-bit indices."""
    rng = np.random.default_rng(3)
    n = 70002
    pos = rng.uniform(-200.0, 200.0, (n, 3))
    nrm = np.tile([0.0, 1.0, 0.0], (n, 1))
    parts = {"a": {"pos": pos, "nrm": nrm, "uv": pos[:, :2], "idx": np.arange(n)}}
    write_glb(tmp_path / "t.glb", parts, {"a": {}}, quantize=True)
    gltf, binary = read_glb(tmp_path / "t.glb")
    _check_glb(gltf, binary)
    prims = [p for m in gltf["meshes"] for p in m["primitives"]]
    assert len(prims) == 2 and all(gltf["accessors"][p["indices"]]["componentType"] == 5123 for p in prims)
    back = read_parts(tmp_path / "t.glb")["a"]
    assert np.abs(back["pos"][back["idx"]] - pos).max() < 400.0 / 65534 + 1e-6
    assert np.array_equal(back["uv"][back["idx"]], pos[:, :2].astype(np.float32))


def test_stats_tiles_splits_the_bytes(rebuilt_tile, tmp_path, capsys):
    from citygen.tilestats import tile_bytes
    _, path, info = rebuilt_tile
    s = tile_bytes(path)
    parts = s["json"] + s["terrain"] + sum(s["mesh"].values()) + sum(s["pieces"].values()) + \
        sum(s["instances"].values()) + s["textures"]
    assert s["total"] == info["bytes"] and 0.97 * s["total"] < parts <= s["total"]   # the rest is padding
    assert s["terrain"] > 0 and "roof_white" in s["mesh"] and sum(s["counts"].values()) == info["pieces"]
    (tmp_path / "tiles").mkdir()
    (tmp_path / "tiles" / path.name).write_bytes(path.read_bytes())
    (tmp_path / "tiles" / "index.json").write_text(json.dumps({"tiles": [info]}))
    main(["stats", "--tiles", str(tmp_path)])
    out = capsys.readouterr().out
    assert out.startswith("tile ") and "tile_13_23" in out and "piece meshes" in out


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


@pytest.fixture(scope="module")
def rebuilt_tile(built_mesh, tmp_path_factory):
    """The same tile built again on the same context (the dresser's caches are warm) and written as a
    .glb, as export_tile does: (placements, path, index entry)."""
    from citygen.mesh.tile import build_tile, write_tile
    tc, i, j, _, _ = built_mesh
    mb, placements = build_tile(tc, i, j)
    folder = tmp_path_factory.mktemp("tile")
    info = write_tile(tc, i, j, mb, placements, folder)
    return placements, folder / info["file"], info


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
    drawn = np.maximum(ground.surface(front[:, 0], front[:, 1]), ground.drawn(front[:, 0], front[:, 1]))
    assert np.all(np.abs(zs - drawn) <= 0.05)    # street, walk, garden path, or the terrain mesh on open ground


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


def _footprint_box(kit, p, z):
    """Plan rectangle and height range of a placed piece, straight from the kit bounds (test's own math)."""
    lo, hi = kit.pieces[p.piece].bounds
    c, s = math.cos(p.yaw), math.sin(p.yaw)
    corners = [(x, y) for x, y in ((lo[0], -hi[2]), (hi[0], -hi[2]), (hi[0], -lo[2]), (lo[0], -lo[2]))]
    poly = shapely.Polygon([(p.x + x * c - y * s, p.y + x * s + y * c) for x, y in corners])
    return poly, z + lo[1], z + hi[1]


@pytest.fixture(scope="module")
def homes(world, plan, ground):
    """A sample of dwellings dressed with the every-home rules on and off (every 3rd slab, every 6th other)."""
    from citygen.city.dressing import DRESSED, Dresser, building_highs
    from citygen.kit import make_kit
    kit = make_kit(world.seed, world.cfg, world.style)
    on, off = Dresser(world, plan, kit, ground), Dresser(world, plan, kit, ground)
    off.every_home = False
    slabs = [k for k, b in enumerate(plan.buildings) if on._is_slab(b)]
    others = [k for k, b in enumerate(plan.buildings) if b.kind in DRESSED and not on._is_slab(b)]
    sample = slabs[::3] + others[::6]
    highs = building_highs(ground, [plan.buildings[k] for k in sample])
    out = {}
    for k, high in zip(sample, highs):
        paths: list = []
        out[k] = (float(high), on.building(k, float(high), paths), off.building(k, float(high)), paths,
                  on.door_spot(k))
    return kit, on, out


def test_every_home_keeps_its_street_pieces_and_gets_a_door(plan, homes):
    kit, dresser, out = homes
    reach = {"street": 0, "open": 0, "enclosed": 0}
    for k, (_, on, off, _, spot) in out.items():
        assert on[:len(off)] == off, k                           # street walls and roofs dressed as before
        assert spot is not None
        reach[spot.reach] += 1
        assert plan.buildings[k].footprint.exterior.distance(shapely.Point(spot.x, spot.y)) < 0.05
        placed = [p for p in on if p.piece in (spot.piece, spot.piece + "_lit")   # a lit fanlight at night (21)
                  and abs(p.x - spot.x) < 1e-6 and abs(p.y - spot.y) < 1e-6]
        assert placed and kit.pieces[spot.piece].category == "door", k   # the door really is drawn there
        assert abs(placed[0].z - spot.z) < 1e-6 and not placed[0].on_ground
    assert reach["street"] > 50 and reach["open"] > 50 and reach["enclosed"] == 0   # 20.2: impasses reach them


def test_every_old_town_house_opens_on_a_street_or_an_impasse(plan, homes):
    # prompt 20.2: the main door of every medina dwelling, as the dresser places it, opens on a
    # street, an alley or an impasse; some of them only on an impasse
    _, dresser, _ = homes
    medina = {d.id for d in plan.districts if d.kind == "medina"}
    spots = [dresser.door_spot(k) for k, b in enumerate(plan.buildings)
             if b.district in medina and b.kind in ("house", "domed")]
    assert len(spots) > 500
    assert all(s.reach == "street" for s in spots), sum(s.reach != "street" for s in spots)
    assert sum(plan.streets[s.street].kind == "impasse" for s in spots) > 100


def test_impasses_are_dead_ends_inside_their_blocks(world, plan):
    from shapely.ops import substring
    lanes = [k for k, st in enumerate(plan.streets) if st.kind == "impasse"]
    assert len(lanes) > 50
    cfg = world.style["impasse"]
    overlap = float(cfg["mouth_overlap"])
    surf = [st.line.buffer(st.width / 2, cap_style="flat") for st in plan.streets]
    other = [k for k, st in enumerate(plan.streets) if st.kind != "impasse"]
    streets = STRtree([surf[k] for k in other])
    blocks = STRtree([b for b, _ in plan.blocks])
    roots = covered = 0
    for k in lanes:
        st = plan.streets[k]
        kind = plan.districts[plan.blocks[int(blocks.query(st.line.interpolate(0.5, normalized=True),
                                                          predicate="within")[0])][1]].kind
        assert st.surface == cfg[kind]["surface"] and cfg[kind]["width"][0] <= st.width <= cfg[kind]["width"][1]
        head = shapely.Point(st.line.coords[0])
        mouth = [other[int(j)] for j in streets.query(head, predicate="within")]
        if mouth:                                  # opens on exactly one street, leaves it at once
            roots += 1
            covered += st.covered > 0
            assert len(mouth) == 1, (k, mouth)
            body = substring(st.line, overlap, st.line.length)
        else:                                      # or branches off exactly one other impasse
            assert st.covered == 0
            parents = [j for j in lanes if j != k and plan.streets[j].line.distance(head) < 1e-6]
            assert len(parents) == 1, (k, parents)
            body = st.line
        assert any(plan.blocks[int(b)][0].buffer(0.05).contains(body)
                   for b in blocks.query(body, predicate="intersects")), k
        tail = substring(st.line, overlap + st.width / 2 + 0.3, st.line.length) if mouth else st.line
        if tail.length > 0.1:                      # past its mouth it touches no street: a dead end
            hit = streets.query(tail.buffer(st.width / 2, cap_style="flat"), predicate="intersects")
            assert not len(hit), (k, [plan.streets[other[int(j)]].kind for j in hit])
        assert st.line.length - (overlap if mouth else 0.0) <= cfg[kind]["max_length"] + 0.01
    assert roots > 30 and covered > 5


def test_no_building_stands_on_an_impasse(plan):
    lanes = [st.line.buffer(st.width / 2, cap_style="flat") for st in plan.streets if st.kind == "impasse"]
    tree = STRtree([b.footprint for b in plan.buildings])
    left, right = tree.query(lanes, predicate="intersects")
    overlap = shapely.area(shapely.intersection(np.array(lanes, dtype=object)[left],
                                                np.array([b.footprint for b in plan.buildings], dtype=object)[right]))
    assert not len(overlap) or overlap.max() < 0.01, overlap.max()


def test_new_doors_and_windows_overlap_nothing(world, plan, ground, homes):
    kit, _, out = homes
    clear = float(world.style["dressing"]["open_walls"]["door_clear"])
    roof = {o[0] for r in ("roof_tank", "roof_dish", "roof_laundry", "roof_pot")
            for o in world.style["dressing"]["roles"][r]}
    checked = 0
    for k, (_, on, off, _, _) in out.items():
        olds = [p for p in off if p.piece not in roof   # doors stand under an arcade: its pillars are checked
                and kit.pieces[p.piece].category != "arcade"]   # in test_colonial_arcades_and_iron_balconies (22)
        zs = [p.z + (ground.surface(p.x, p.y) if p.on_ground else 0.0) for p in olds]
        boxes = [_footprint_box(kit, p, z) for p, z in zip(olds, zs)]
        standing = [b for p, b in zip(olds, boxes) if p.on_ground]
        for p in on[len(off):]:
            box = _footprint_box(kit, p, p.z)
            for other in boxes:
                if box[1] < other[2] - 1e-6 and other[1] < box[2] - 1e-6:
                    assert box[0].intersection(other[0]).area < 1e-4, (k, p.piece)
            if kit.pieces[p.piece].category == "door":            # free ground in front: no chair, goods or pot
                n = np.array([-math.sin(p.yaw), math.cos(p.yaw)])
                u = np.array([n[1], -n[0]]) * kit.pieces[p.piece].width / 2
                front = shapely.Polygon([(p.x, p.y) + u, (p.x, p.y) - u, (p.x, p.y) - u + n * clear, (p.x, p.y) + u + n * clear])
                assert all(front.intersection(g[0]).area < 1e-4 for g in standing), (k, p.piece)
            boxes.append(box)
            checked += 1
    assert checked > 5000


def test_every_slab_has_windows_on_each_floor_of_its_open_long_sides(plan, homes):
    from citygen.city.geo import frame
    kit, dresser, out = homes
    footprints = STRtree([b.footprint for b in plan.buildings])
    slabs = 0
    for k, (high, on, _, _, spot) in out.items():
        b = plan.buildings[k]
        if not dresser._is_slab(b):
            continue
        slabs += 1
        assert spot.kind == "stair" and kit.pieces[spot.piece].category == "door"
        ring = np.asarray(shapely.geometry.polygon.orient(b.footprint, 1.0).exterior.coords)
        floors, open_long = int(b.floors), 0
        for a, c in zip(ring[:-1], ring[1:]):
            wall = shapely.LineString([a, c])
            if wall.length < 0.6 * frame(b.footprint)[2]:
                continue
            u = (c - a) / wall.length
            n = np.array([u[1], -u[0]])
            probe = shapely.Polygon([a + u * 0.3 + n * 0.05, c - u * 0.3 + n * 0.05, c - u * 0.3 + n * 3.0, a + u * 0.3 + n * 3.0])
            if any(j != k for j in footprints.query(probe, predicate="intersects")):
                continue                                         # a neighbour stands within 3 m
            open_long += 1
            on_wall = [p for p in on if kit.pieces[p.piece].category in ("window", "balcony")
                       and wall.distance(shapely.Point(p.x, p.y)) < 0.05]
            seen = {int((p.z - high) // (b.height / floors)) for p in on_wall}
            assert seen >= set(range(floors)), (k, sorted(seen), floors)
        assert open_long >= 1, k
    assert slabs > 80


def test_lit_twins_look_like_their_dark_pieces_by_day(world, homes):
    # prompt 21: a `_lit` twin is its piece with glass_lit for glass_dark (same arrays); glass_lit is
    # glass_dark's exact copy, no emissive; a kit window's pane covers its glass, just in front of it
    kit = homes[0]
    palette = world.style["palette"]
    assert palette["glass_lit"] == palette["glass_dark"] and "emissive" not in palette["glass_lit"]
    twins = [n for n in kit.pieces if n.endswith("_lit") and not n.endswith("_pane_lit")]
    assert {"window_grille_blue_lit", "window_slab_white_lit", "window_stair_lit", "balcony_slab_lit",
            "door_narrow_blue_lit", "stair_door_lit"} <= set(twins)
    assert "window_slab_white_shut_lit" not in kit.pieces                   # closed shutters stay dark
    for name in twins:
        dark, lit = kit.pieces[name[:-4]].parts, kit.pieces[name].parts
        assert [("glass_lit" if m == "glass_dark" else m) for m in dark] == list(lit), name
        for m, part in dark.items():
            twin = lit["glass_lit" if m == "glass_dark" else m]
            for key in ("pos", "nrm", "uv", "idx"):
                assert np.array_equal(part[key], twin[key]), (name, m, key)
    panes = [n for n in kit.pieces if n.endswith("_pane_lit")]
    assert len(panes) == 7
    for name in panes:
        pane, window = kit.pieces[name], kit.pieces[name[:-len("_pane_lit")]]
        assert list(pane.parts) == ["glass_lit"] and pane.triangles == 2
        x0, x1, y0, y1, z = (float(v) for v in kit.panes[window.name])
        lo, hi = pane.bounds
        assert np.allclose([lo[0], hi[0], lo[1], hi[1]], [x0, x1, y0, y1]) and lo[2] == hi[2] < z
        pos = np.concatenate([p["pos"] for p in window.parts.values()])    # nothing of the window in its plane
        inside = (pos[:, 0] > x0) & (pos[:, 0] < x1) & (pos[:, 1] > y0) & (pos[:, 1] < y1)
        assert not np.any(inside & (np.abs(pos[:, 2] - lo[2]) < 0.004)), name


def test_lit_windows_follow_households_and_light_whole_flats(world, plan, homes):
    from citygen.city.dressing import Dresser
    from citygen.city.geo import frame
    kit, dresser, out = homes
    lo, hi = world.style["dressing"]["slab"]["stair_spacing"]
    windows = lit = 0
    for k, (high, on, _, _, _) in out.items():
        b = plan.buildings[k]
        fh = b.height / max(1, int(b.floors))
        cx, cy, length, _, angle = frame(b.footprint)
        seg = length / max(1, int(length / ((lo + hi) / 2) + 0.5))
        flats: dict = {}
        for i, p in enumerate(on):
            name = p.piece[:-4] if p.piece.endswith("_lit") else p.piece
            if p.piece.endswith("_pane_lit") or not (name + "_lit" in kit.pieces or name + "_pane_lit" in kit.pieces):
                continue
            on_ = p.piece.endswith("_lit") or (i + 1 < len(on) and on[i + 1].piece == p.piece + "_pane_lit")
            if on_ and p.piece + "_pane_lit" in kit.pieces:
                assert (on[i + 1].x, on[i + 1].y, on[i + 1].z, on[i + 1].yaw) == (p.x, p.y, p.z, p.yaw)
            windows += 1
            lit += on_
            t = (p.x - cx) * math.cos(angle) + (p.y - cy) * math.sin(angle) + length / 2
            half = int(t // (seg / 2)) if dresser._is_slab(b) else 0      # one flat each side of a stair
            if name in ("window_stair", "stair_door"):
                continue
            flats.setdefault((round(p.yaw, 3), int((p.z - high + 0.01) // fh), half), set()).add(on_)
        assert all(len(v) == 1 for v in flats.values()), (k, flats)          # a flat is all lit or all dark
    assert windows > 10000 and 0.25 <= lit / windows <= 0.5, lit / windows
    day = Dresser(world, plan, kit, dresser.ground)                          # without lights: the same pieces
    day.lit_cfg = {}
    for k in list(out)[::10]:
        high, on = out[k][0], out[k][1]
        night = [(p.piece[:-4] if p.piece.endswith("_lit") else p.piece, p.x, p.y, p.z, p.yaw)
                 for p in on if not p.piece.endswith("_pane_lit")]
        assert night == [(p.piece, p.x, p.y, p.z, p.yaw) for p in day.building(k, high)], k


def _plan_box(kit, p, out0=None, out1=None):
    """Plan rectangle of a placed piece from its kit bounds (stretch along the wall), optionally only the
    part between out0 and out1 meters in front of its anchor."""
    lo, hi = kit.pieces[p.piece].bounds
    x0, x1 = lo[0] * p.stretch * p.scale, hi[0] * p.stretch * p.scale
    y0, y1 = -hi[2] * p.scale, -lo[2] * p.scale
    y0, y1 = (y0 if out0 is None else out0), (y1 if out1 is None else out1)
    c, s = math.cos(p.yaw), math.sin(p.yaw)
    return shapely.Polygon([(p.x + x * c - y * s, p.y + x * s + y * c) for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1))])


@pytest.fixture(scope="module")
def colonial(plan, ground, homes):
    """Every colonial dwelling dressed once: {k: (high, placements)} (prompts 22 and 23)."""
    from citygen.city.dressing import DRESSED, building_highs
    dresser = homes[1]
    ks = [k for k, b in enumerate(plan.buildings) if b.kind in DRESSED and plan.districts[b.district].kind == "colonial"]
    highs = building_highs(ground, [plan.buildings[k] for k in ks])
    return {k: (float(high), dresser.building(k, float(high))) for k, high in zip(ks, highs)}


def test_colonial_arcades_and_iron_balconies(world, plan, ground, homes, colonial):
    # prompt 22: an arcade along every colonial facade on a boulevard, arterial or ring, its bays end to
    # end along the whole wall; no pillar in front of a door or shop front, in a cafe table or other
    # ground piece, no street lamp or planted tree trunk in or under an arcade; iron balconies only on the upper floors of
    # colonial buildings and never on the floor right above an arcade
    from shapely.geometry.polygon import orient
    from citygen.city.dressing import DRESSED, building_highs
    kit, dresser, sample = homes
    cfg = dresser.arcade_cfg
    d, (pw, pd), kinds = cfg["depth"], cfg["pillar"], set(cfg["kinds"])
    sill = world.style["dressing"]["window_sill"]
    width = kit.pieces["arcade_bay"].width
    pillars, roofs, bays_all, walls, corners = [], [], [], 0, 0
    covered = total = strict = balconies = 0
    for k, (high, out) in colonial.items():
        b = plan.buildings[k]
        bays = [p for p in out if p.piece == "arcade_bay"]
        bays_all += bays
        roofs += [_plan_box(kit, p) for p in out if kit.pieces[p.piece].category == "arcade"]
        corners += sum(p.piece.startswith("arcade_bend") for p in out)   # turns round a cut corner (23)
        for c in [p for p in out if p.piece == "arcade_corner"]:   # in the square past the corner, on no bay
            corners += 1                                    # (a sliver where the corner is a few degrees off square)
            assert all(_plan_box(kit, c).intersection(_plan_box(kit, p)).area < 0.2 for p in bays), k
        mine = []                                       # pillars: half of each bay's width end, out at the arches
        for p in bays:
            half = pw / 2 * p.stretch
            for x in (-width / 2 * p.stretch, width / 2 * p.stretch - half):
                c, s = math.cos(p.yaw), math.sin(p.yaw)
                q = shapely.Polygon([(p.x + xx * c - y * s, p.y + xx * s + y * c)
                                     for xx, y in ((x, d - pd), (x + half, d - pd), (x + half, d), (x, d))])
                mine.append((q, x + half / 2, p))
        pillars += [q for q, _, _ in mine]
        for p in out:                                   # doors and shops sit under an arch, ground pieces clear
            cat = kit.pieces[p.piece].category
            if cat in ("door", "shop"):
                front = _plan_box(kit, p, 0.0, d)           # the door and the walkway in front of it
                assert all(front.intersection(q).area < 1e-6 for q, _, _ in mine), (k, p.piece)
            elif p.on_ground and cat not in ("arcade", "tree"):
                box = _plan_box(kit, p)
                assert all(box.intersection(q).area < 1e-6 for q, _, _ in mine), (k, p.piece)
        ring = np.asarray(orient(b.footprint, 1.0).exterior.coords)
        fh = b.height / max(1, int(b.floors))
        spans = {}
        for a, c in zip(ring[:-1], ring[1:]):          # each wall on an arcaded street: bays end to end
            length = float(np.hypot(*(c - a)))
            u = (c - a) / max(length, 1e-9)
            n = np.array([u[1], -u[0]])
            on = sorted((float(np.dot((p.x, p.y) - a, u)), p.stretch * width) for p in bays
                        if abs(float(np.dot((p.x, p.y) - a, n))) < 0.02 and np.dot((-math.sin(p.yaw), math.cos(p.yaw)), n) > 0.999)
            spans[tuple(np.round(a, 6))] = (u, n, [(s - w / 2, s + w / 2) for s, w in on])
            street = dresser.streets_at(((a + c) / 2 + n * 1.6)[None, :])[0]
            if length < 4.0 or street < 0 or plan.streets[street].kind not in kinds:
                continue
            walls += 1
            total += length
            if not on:
                continue
            edges = [(s - w / 2, s + w / 2) for s, w in on]
            assert all(abs(e0[1] - e1[0]) < 1e-6 for e0, e1 in zip(edges, edges[1:])), (k, edges)   # no gap
            assert all(cfg["bay_relaxed"][0] - 1e-6 <= w <= cfg["bay_relaxed"][1] + 1e-6 for _, w in on)
            strict += sum(cfg["bay"][0] - 1e-6 <= w <= cfg["bay"][1] + 1e-6 for _, w in on)
            run = min(edges[-1][1], length) - max(edges[0][0], 0.0)
            assert run >= length - cfg["bay_relaxed"][1] - 0.5, (k, run, length)   # at most a short plain end
            covered += run
        for p in out:
            if not p.piece.startswith("balcony_iron"):
                continue
            balconies += 1
            floor = (p.z - sill - high) / fh
            assert floor > 0.99 and abs(floor - round(floor)) < 1e-6, (k, floor)         # upper floors only
            if round(floor) == 1:                           # never on the arcade's terrace
                for a, (u, n, edges) in spans.items():
                    s = float(np.dot((p.x, p.y) - np.array(a), u))
                    near = abs(float(np.dot((p.x, p.y) - np.array(a), n))) < 0.02 and np.dot(
                        (-math.sin(p.yaw), math.cos(p.yaw)), n) > 0.999
                    assert not (near and any(e0 < s < e1 for e0, e1 in edges)), (k, p.piece)
    assert len(bays_all) > 250 and covered / total > 0.85 and corners > 10, (len(bays_all), covered / total, corners)
    assert strict / len(bays_all) > 0.4 and balconies > 500   # about half the bays 3.5-4.0 m, all 3.2-4.4
    for k, (_, on, _, _, _) in sample.items():          # no iron balcony outside the ville nouvelle
        if plan.districts[plan.buildings[k].district].kind != "colonial":
            assert not any(p.piece.startswith("balcony_iron") or p.piece.startswith("arcade") for p in on), k
    tile = shapely.box(*plan.boundary.bounds)            # street lamps: none in or under an arcade
    lamps = []                                           # every street's lamps, side streets too
    for k, st in enumerate(plan.streets):
        spacing = dresser.cfg["street_lamps"].get(st.kind)
        if spacing:
            dresser._lamps(k, float(spacing), tile, lamps)
    assert len(lamps) > 100
    tree = STRtree(roofs)
    for p in lamps:
        assert not len(tree.query(_plan_box(kit, p), predicate="intersects")), (p.x, p.y)
    xy, kept, away = dresser.tree_spots(np.array([(t.x, t.y) for t in plan.trees]))   # planned trees as tiles draw them
    assert away.any(axis=1).sum() >= 5 and np.allclose(xy[~away.any(axis=1)], [(t.x, t.y) for t, a in zip(plan.trees, away) if not a.any()])
    trunks = shapely.buffer(shapely.points(xy[kept]), cfg["tree_trunk"])
    assert not len(tree.query(trunks, predicate="intersects")[0])          # no trunk in or under an arcade


def test_ground_drawn_is_the_terrain_mesh(world, plan, ground):
    from citygen.mesh.tile import terrain_mesh
    tc = TileContext(world, [plan])
    s = world.capital()
    x0, y0 = tc.size * (s.x // tc.size), tc.size * (s.y // tc.size)
    mb = MeshBuilder(origin=(x0, y0))
    terrain_mesh(mb, tc, x0, y0)
    tris = np.concatenate([(np.concatenate(part[0]) + [x0, y0, 0.0])[np.concatenate(part[3])]
                           for part in mb._parts.values()])                       # (T, 3, 3) drawn triangles
    pts = np.random.default_rng(3).uniform([x0 + 1, y0 + 1], [x0 + tc.size - 1, y0 + tc.size - 1], (300, 2))
    hit = STRtree(shapely.polygons(tris[:, :, :2])).query(shapely.points(pts), predicate="intersects")
    first = np.unique(hit[0], return_index=True)[1]
    k, t = hit[0][first], tris[hit[1][first]]
    a, b, c = t[:, 0], t[:, 1], t[:, 2]                                           # barycentric heights
    det = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (c[:, 0] - a[:, 0]) * (b[:, 1] - a[:, 1])
    wb = ((pts[k, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (c[:, 0] - a[:, 0]) * (pts[k, 1] - a[:, 1])) / det
    wc = ((b[:, 0] - a[:, 0]) * (pts[k, 1] - a[:, 1]) - (pts[k, 0] - a[:, 0]) * (b[:, 1] - a[:, 1])) / det
    mesh = a[:, 2] + wb * (b[:, 2] - a[:, 2]) + wc * (c[:, 2] - a[:, 2])
    assert len(k) == len(pts)
    assert np.max(np.abs(ground.drawn(pts[k, 0], pts[k, 1]) - mesh)) < 1e-6


def test_paths_reach_the_street_and_cross_no_building(world, plan, ground, homes):
    from citygen.mesh.builder import add_ribbon
    cfg = world.style["dressing"]["paths"]
    width, lift = float(cfg["width"]), float(cfg["lift"])
    ends = [st.line.buffer(st.width / 2, cap_style="flat") for st in plan.streets] + [w.polygon for w in plan.walks]
    ends_tree, footprints = STRtree(ends), STRtree([b.footprint for b in plan.buildings])
    _, _, out = homes
    count = 0
    for k, (_, on, _, paths, spot) in out.items():
        for line in paths:
            count += 1
            end = shapely.Point(line[-1])
            assert ends_tree.query(end.buffer(0.05), predicate="intersects").size, k   # stops at a street or walk
            band = shapely.LineString(line[1:]).buffer(width / 2 - 0.01, cap_style="flat")
            assert not footprints.query(band, predicate="intersects").size, k
            mb = MeshBuilder()
            add_ribbon(mb, line, width, ground.drawn, lift, "sidewalk")       # as path_meshes draws it
            pos = np.concatenate(mb._parts["sidewalk"][0])
            edges = np.concatenate([pos, (pos[:-2] + pos[2:]) / 2])           # corners and edge midpoints
            assert np.all(edges[:, 2] >= ground.drawn(edges[:, 0], edges[:, 1]) + 0.01), k
        if spot.path is not None:                                # the threshold meets the drawn path
            mb = MeshBuilder()
            add_ribbon(mb, spot.path, width, ground.drawn, lift, "sidewalk")
            pos = np.concatenate(mb._parts["sidewalk"][0])
            assert abs(pos[2:4, 2].mean() - spot.z) < 1e-6
    assert count > 80

def test_parapets_and_stair_rooms_follow_the_style(world, plan):
    from citygen.city.massing import main_mass
    from citygen.city.roofs import roof_layout, roof_stream
    from shapely.geometry import Point
    cfg = world.style["roofs"]
    thick = float(cfg["parapet_thickness"])
    seen = {"house": [], "apartments": []}
    expected = {"house": [], "apartments": []}
    stairs = 0
    for k, b in enumerate(plan.buildings):
        if b.roof_shape != "flat" or b.battlement is not None or b.kind == "kasbah_ground":
            continue                                       # kasbah walls carry merlons, its ground is paving
        kind = plan.districts[b.district].kind
        layout = roof_layout(b, kind, roof_stream(world.seed, plan.settlement.id, k), cfg)
        assert layout.band is not None and layout.inner is not None
        assert layout.height == pytest.approx(cfg["parapet_height"].get(kind, cfg["parapet_fallback"]))
        assert 0.6 <= layout.height <= 1.0
        thin = main_mass(b).polygon.buffer(-thick, join_style="mitre")   # the main roof (prompt 23)
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
        z, ribbon = centers(w.polygon, ground.walk_top, ground.walk_step(w.polygon, float(cfg["walk_step"])))
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
        assert st.kind == "impasse" or st.surface == table[st.kind]   # impasses: by district (test above)
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


def test_impasse_ribbons_are_drawn_like_alleys(world, plan, ground, built_mesh):
    # the ribbons as mesh/tile.py draws them: alley paving and lift in the old town, and the ground
    # reads the same lift there (doors on an impasse stand on its ribbon)
    from citygen.city.ground import STREET_LIFT
    from citygen.mesh.builder import MeshBuilder as MB
    from citygen.mesh.tile import street_meshes
    tc = built_mesh[0]
    lanes = [st for st in plan.streets if st.kind == "impasse"]
    tree = STRtree([st.line for st in lanes])
    sub = type("Lanes", (), {"streets": lanes})()
    s = world.capital()
    i, j = int(s.x // tc.size), int(s.y // tc.size)
    mb = MB(origin=(i * tc.size, j * tc.size))
    street_meshes(mb, tc, sub, tree, shapely.box(i * tc.size, j * tc.size, (i + 1) * tc.size, (j + 1) * tc.size))
    parts = _world_parts(mb)
    assert set(parts) == {"paving"}                       # the medina's lanes, paved like its alleys
    xyz = parts["paving"][0]
    assert len(xyz) > 400
    lift = xyz[:, 2] - tc.height(xyz[:, 0], xyz[:, 1])
    assert np.allclose(lift, STREET_LIFT["alley"], atol=1e-6) and STREET_LIFT["impasse"] == STREET_LIFT["alley"]
    mid = np.array([st.line.interpolate(0.5, normalized=True).coords[0] for st in lanes])
    assert np.median(ground.lift(mid[:, 0], mid[:, 1])) == pytest.approx(STREET_LIFT["alley"])


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


def test_make_blend_stops_in_sandbox(tmp_path, monkeypatch):
    import subprocess
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
    import make_blend
    assert isinstance(make_blend.sandboxed(), bool)
    (tmp_path / "tiles").mkdir()
    (tmp_path / "tiles" / "index.json").write_text(json.dumps({"focus": {"name": "X"}}))
    monkeypatch.setattr(sys, "argv", ["make_blend.py", str(tmp_path)])
    monkeypatch.setattr(make_blend, "sandboxed", lambda: True)
    monkeypatch.setattr(subprocess, "run", lambda *a, **k: pytest.fail("Blender started in a sandbox"))
    with pytest.raises(SystemExit) as stop:
        make_blend.main()
    assert "Not starting Blender" in str(stop.value)


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
        for name in (f"tile_{i}_{j}.glb", f"tile_{i}_{j}_lod1.glb"):   # and the lod1 files (prompt 40)
            assert (out[1][1] / name).read_bytes() == (out[2][1] / name).read_bytes()


def test_build_key_ignores_workers_and_output():
    from citygen.buildkey import build_key
    a = load_config(quick=True)
    b = load_config(quick=True, overrides={"build": {"workers": 3, "output": "elsewhere"}})
    c = load_config(quick=True, overrides={"tiles": {"terrain_step": 99.0}})
    assert build_key(a, [3, 1]) == build_key(b, [1, 3]) != build_key(c, [1, 3]) != build_key(a, [1, 3, 4])


def test_cached_plan_is_reused_with_the_worlds_own_settlement(world, plan, tmp_path, monkeypatch):
    from citygen import build as builder
    monkeypatch.setattr(builder, "plan_city", lambda w, s: plan)   # planning itself: test_same_seed_same_city
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


# --- building massing (prompt 23) ---------------------------------------------------------------

def test_massing_keeps_every_building_household_and_street(world, plan, monkeypatch):
    # the plan before massing: same buildings in the same order, same households, souks, streets and
    # trees; every new footprint inside the old one (so inside its lot and off the streets)
    # greenery (prompt 24) is switched off too: the old trees come first, unchanged, the new ones after them
    import citygen.city as city
    monkeypatch.setattr(city, "apply_massing", lambda ctx, plan: None)
    monkeypatch.setattr(city, "greenery", lambda ctx, plan: [])
    monkeypatch.setattr(city, "plan_fronts", lambda ctx, plan: [])   # the seafront (prompt 36) moves sea palms
    before = city.plan_city(world, world.capital())
    assert [b.kind for b in before.buildings] == [b.kind for b in plan.buildings]
    assert before.households == plan.households and before.souks == plan.souks
    old = len(before.trees)
    assert [(t.kind, t.height) for t in before.trees] == [(t.kind, t.height) for t in plan.trees[:old]]
    front = shapely.union_all([w.polygon for w in plan.walks if w.kind == "seafront"])
    moved = [k for k in range(old) if (before.trees[k].x, before.trees[k].y) != (plan.trees[k].x, plan.trees[k].y)]
    assert len(moved) > 30 and all(plan.trees[k].kind == "palm" for k in moved)
    assert all(front.contains(shapely.Point(plan.trees[k].x, plan.trees[k].y)) for k in moved)
    assert all(np.hypot(before.trees[k].x - plan.trees[k].x, before.trees[k].y - plan.trees[k].y) < 2.0 for k in moved)
    assert len(plan.trees) - old == plan.stats["greenery"] > 100
    assert [s.line.wkb for s in before.streets] == [s.line.wkb for s in plan.streets]
    skip = {"seconds", "trees", "greenery", "promenade_m", "beach_m"}
    assert {k: v for k, v in before.stats.items() if k not in skip} == {k: v for k, v in plan.stats.items() if k not in skip}
    count = {"chamfer": 0, "round": 0, "top": 0, "setback": 0, "steps": 0, "lift": 0, "tank": 0, "menzah": 0}
    for old, b in zip(before.buildings, plan.buildings):
        assert b.footprint.is_valid and old.footprint.buffer(1e-6).contains(b.footprint)
        for _x, _y, kind, _reach in b.corners:
            count[kind] += 1
        count["top"] += bool(b.top and "x" in b.top)
        count["menzah"] += b.menzah
        if b.setback is not None:
            count["setback"] += 1
            assert b.setback.is_valid and b.footprint.buffer(1e-6).contains(b.setback)
            assert b.floors == old.floors or abs(b.floors - old.floors) <= 3
        if b.steps:
            count["steps"] += plan.districts[b.district].kind == "modern"
            assert all(p.is_valid and b.footprint.buffer(1e-6).contains(p) for p, _, _, _ in b.steps)
            assert abs(sum(p.area for p, _, _, _ in b.steps) - b.footprint.area) < 0.05
            assert max(f for _, f, _, _ in b.steps) == b.floors and len({f for _, f, _, _ in b.steps}) > 1
        for m in b.machines:
            count[m["kind"]] += 1
    assert count["chamfer"] > 30 and count["round"] > 8 and count["top"] > 8 and count["setback"] > 30, count
    assert count["steps"] > 40 and count["lift"] > 100 and count["tank"] > 50 and count["menzah"] > 10, count


def _wall_triangles(mb):
    """(T, 3, 3) world-space vertical triangles of a mesh, every material."""
    out = []
    for part in mb._parts.values():
        pos = np.concatenate(part[0]) + mb.origin
        tris = np.concatenate(part[3])
        t = pos[tris]
        n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
        norm = np.linalg.norm(n, axis=1)
        keep = (norm > 1e-9) & (np.abs(n[:, 2]) < 0.05 * np.maximum(norm, 1e-12))
        out.append(t[keep])
    return np.concatenate(out) if out else np.zeros((0, 3, 3))


def _on_wall(tris, pts) -> np.ndarray:
    """For each 3D point: does a vertical triangle pass within 6 cm of it, the point inside its outline?"""
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    n = np.cross(b - a, c - a)
    n /= np.linalg.norm(n, axis=1)[:, None]
    out = []
    for p in pts:
        d = np.einsum("ij,ij->i", p - a, n)
        q = p - n * d[:, None]
        v0, v1, v2 = c - a, b - a, q - a
        d00, d01, d11 = np.einsum("ij,ij->i", v0, v0), np.einsum("ij,ij->i", v0, v1), np.einsum("ij,ij->i", v1, v1)
        d20, d21 = np.einsum("ij,ij->i", v2, v0), np.einsum("ij,ij->i", v2, v1)
        den = np.maximum(d00 * d11 - d01 * d01, 1e-12)
        u, v = (d11 * d20 - d01 * d21) / den, (d00 * d21 - d01 * d20) / den
        out.append(bool(((np.abs(d) < 0.06) & (u >= -1e-6) & (v >= -1e-6) & (u + v <= 1 + 1e-6)).any()))
    return np.array(out)


def _coplanar_overlap(mb) -> float:
    """Largest area (m2) two faces of a mesh share in one plane facing the same way: z-fighting."""
    from collections import defaultdict
    t = np.concatenate([(np.concatenate(part[0]) + mb.origin)[np.concatenate(part[3])] for part in mb._parts.values()])
    n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    area = np.linalg.norm(n, axis=1)
    t, n = t[area > 1e-8], n[area > 1e-8] / area[area > 1e-8, None]
    planes = defaultdict(list)
    for i, key in enumerate(map(tuple, np.round(np.c_[n * 1000, np.einsum("ij,ij->i", n, t[:, 0]) * 100]).astype(int))):
        planes[key].append(i)
    worst = 0.0
    for idx in planes.values():
        if len(idx) < 2:
            continue
        e1 = np.cross(n[idx[0]], [0.0, 0.0, 1.0]) if abs(n[idx[0]][2]) < 0.9 else np.array([1.0, 0.0, 0.0])
        e1 /= np.linalg.norm(e1)
        e2 = np.cross(n[idx[0]], e1)
        polys = [shapely.Polygon(t[i] @ np.c_[e1, e2]) for i in idx]
        worst = max(worst, sum(q.area for q in polys) - shapely.union_all(polys).area)
    return worst


def test_massed_buildings_dress_only_walls_and_roofs_that_exist(world, plan, ground, homes, colonial):
    # windows and balconies only on walls drawn at their height (none above a lower step's roof, none
    # on a set-back terrace's edge); roof props and tank stands on a roof deck drawn at their height,
    # never in a stair room, a menzah, a lift room or a corner dome; a cut colonial corner carries the
    # arcade on round it when both its facades have one
    from citygen.city.dressing import building_highs
    from citygen.city.massing import corner_faces, main_mass, massed
    from citygen.city.openings import wall_arrays
    from citygen.city.roofs import roof_layouts, roof_stream
    from citygen.mesh.builder import MeshBuilder
    from citygen.mesh.tile import building_mesh
    kit, dresser = homes[0], homes[1]
    roof_pieces = {o[0] for r in ("roof_tank", "roof_dish", "roof_laundry", "roof_pot")
                   for o in world.style["dressing"]["roles"][r]} | {"tank_stand"}
    ks = [k for k, b in enumerate(plan.buildings) if massed(b) or b.menzah or b.machines or b.corners]
    other = [k for k in ks if k not in colonial][::3]
    highs = building_highs(ground, [plan.buildings[k] for k in other])
    dressed = {k: v for k, v in colonial.items() if k in set(ks)}
    dressed.update({k: (float(h), dresser.building(k, float(h))) for k, h in zip(other, highs)})
    seen = {"window": 0, "upper": 0, "prop": 0, "tank_stand": 0, "menzah": 0, "bend": 0, "cut": 0}
    for k, (high, out) in dressed.items():
        b = plan.buildings[k]
        kind = plan.districts[b.district].kind
        roofs = roof_layouts(b, kind, roof_stream(world.seed, plan.settlement.id, k), world.style["roofs"])
        mb = MeshBuilder()
        building_mesh(mb, b, ground.height, roofs=roofs)
        walls = _wall_triangles(mb)
        if massed(b):
            assert _coplanar_overlap(mb) < 1e-3, k                  # no face drawn twice in one plane
        top_floor = high + (b.floors - 1) * b.height / b.floors
        for p in out:
            pc = kit.pieces[p.piece]
            if pc.category in ("window", "balcony") and p.z > high + 0.5 and massed(b):
                lo, hi = pc.bounds
                zc = p.z + (lo[1] + hi[1]) / 2 * p.scale
                u = np.array([math.cos(p.yaw), math.sin(p.yaw)]) * (pc.width / 2 * p.stretch - 0.1)
                pts = [(p.x + s * u[0], p.y + s * u[1], zc) for s in (-1.0, 1.0)]
                assert _on_wall(walls, pts).all(), (k, p.piece, round(p.z - high, 2))
                seen["window"] += 1
                seen["upper"] += b.setback is not None and p.z > top_floor
            pt = shapely.Point(p.x, p.y)
            if p.piece in roof_pieces and p.z > high + 2.5 and b.footprint.contains(pt):
                m, lay = max(((m, lay) for m, lay in roofs if m.polygon.contains(pt)), key=lambda r: r[0].top)
                assert abs(p.z - (high + m.top)) < 1e-6 and lay.inner.contains(pt), (k, p.piece)   # the top roof there
                inside = sum(r.buffer(0.05).contains(pt) for r in lay.rooms)   # a tank stand is a room itself
                assert inside == (p.piece == "tank_stand"), (k, p.piece)
                seen["tank_stand" if p.piece == "tank_stand" else "prop"] += 1
        main = [lay for m, lay in roofs if m.main][0]
        if main.menzah is not None:
            seen["menzah"] += 1
            assert main.inner.contains(main.menzah)
            assert main.stair is None or main.stair.distance(main.menzah) >= world.style["roofs"]["menzah_gap"] - 1e-6
        if kind == "colonial" and b.corners:
            p0, q0, _, length = wall_arrays(b.footprint)
            bays = [p for p in out if p.piece == "arcade_bay"]
            bends = [p for p in out if p.piece.startswith("arcade_bend")]
            for face in corner_faces(b, p0, q0):
                idx = np.nonzero(face)[0]
                before, after = (idx[0] - 1) % len(face), (idx[-1] + 1) % len(face)

                def bays_on(i):
                    u = (q0[i] - p0[i]) / length[i]
                    n = np.array([u[1], -u[0]])
                    return sorted((float(np.dot((p.x, p.y) - p0[i], u)) - p.stretch * kit.pieces["arcade_bay"].width / 2,
                                   float(np.dot((p.x, p.y) - p0[i], u)) + p.stretch * kit.pieces["arcade_bay"].width / 2)
                                  for p in bays if abs(float(np.dot((p.x, p.y) - p0[i], n))) < 0.02)
                if not (bays_on(before) and bays_on(after)):
                    continue
                seen["cut"] += 1
                for i in idx:                                       # every face covered end to end
                    on = bays_on(i)
                    assert on and on[0][0] < 1e-6 and on[-1][1] > length[i] - 1e-6, (k, i, on)
                    assert all(abs(e0[1] - e1[0]) < 1e-6 for e0, e1 in zip(on, on[1:])), (k, on)
                assert bays_on(before)[-1][1] > length[before] - 1e-6 and bays_on(after)[0][0] < 1e-6, k
                for v in [q0[before]] + [q0[i] for i in idx]:       # a pier piece at every turn
                    assert any(math.hypot(p.x - v[0], p.y - v[1]) < 1e-6 for p in bends), (k, v)
                    seen["bend"] += 1
    assert seen["window"] > 1500 and seen["upper"] > 50 and seen["prop"] > 20 and seen["tank_stand"] > 10, seen
    assert seen["menzah"] > 2 and seen["cut"] > 5 and seen["bend"] > 10, seen   # menzah 4 -> 3: prompt 33's plan shift


def test_villa_l_is_a_hip_part_and_a_terrace_wing(world):
    # villas exist only outside the quick capital: one drawn here, its L inside the old rectangle,
    # the hip part one floor above the wing, windows over the terrace, no face drawn twice
    from citygen.city.massing import _villa, masses, terrace_walls
    from citygen.city.model import Building
    from citygen.city.roofs import roof_layouts
    from citygen.mesh.builder import MeshBuilder
    from citygen.mesh.tile import building_mesh

    class Ctx:
        def rng(self, *path):
            return stream(5, *path)
    dc = {**world.style["district"]["suburb"], "l_share": 1.0}
    old = rectangle(10.0, 20.0, 15.0, 11.0, 0.4)
    b = Building(old, "villa", 0, 6.4, "lime_white", "roof_white", 2)
    _villa(Ctx(), 3, b, dc)
    assert b.roof_shape == "hip" and len(b.footprint.exterior.coords) == 7 and old.buffer(1e-6).contains(b.footprint)
    hip, wing = masses(b)
    assert (hip.shape, hip.floors, wing.shape, wing.floors, wing.terrace) == ("hip", 2, "flat", 1, True)
    assert abs(hip.polygon.area + wing.polygon.area - b.footprint.area) < 1e-6
    assert [(w[4], w[5]) for w in terrace_walls(b)] == [(1, 2)]     # the upper floor opens onto the wing's roof
    roofs = roof_layouts(b, "suburb", stream(5, "roof"), world.style["roofs"])
    mb = MeshBuilder()
    building_mesh(mb, b, lambda x, y: np.zeros_like(np.asarray(x, dtype=float)), roofs=roofs)
    assert _coplanar_overlap(mb) < 1e-3
    tile = np.concatenate(mb._parts["roof_tile"][0])
    assert abs(tile[:, 2].min() - 6.4) < 1e-9 and tile[:, 2].max() > 6.4 + 1.0      # the hip roof on its part
    deck = np.concatenate(mb._parts[dc["terrace_roof"]][0])
    assert abs(deck[:, 2].min() - 3.2) < 1e-9                                       # the terrace one floor lower


def _drawn_z(tris, pt) -> float | None:
    """Height of the up-facing triangle under a plan point (barycentric), or None."""
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    v0, v1 = b[:, :2] - a[:, :2], c[:, :2] - a[:, :2]
    v2 = np.asarray(pt, dtype=float)[None, :] - a[:, :2]
    den = v0[:, 0] * v1[:, 1] - v0[:, 1] * v1[:, 0]
    ok = np.abs(den) > 1e-12
    u = np.where(ok, (v2[:, 0] * v1[:, 1] - v2[:, 1] * v1[:, 0]) / np.where(ok, den, 1.0), -1.0)
    v = np.where(ok, (v0[:, 0] * v2[:, 1] - v0[:, 1] * v2[:, 0]) / np.where(ok, den, 1.0), -1.0)
    hit = np.nonzero(ok & (u >= -1e-9) & (v >= -1e-9) & (u + v <= 1 + 1e-9))[0]
    if not len(hit):
        return None
    i = hit[0]
    return float(a[i, 2] + u[i] * (b[i, 2] - a[i, 2]) + v[i] * (c[i, 2] - a[i, 2]))


def test_cut_corners_are_paved_and_pillars_and_doors_stand_on_the_paving(world, plan, built_tile, colonial, homes):
    # prompt 23 (lead review): the lot corner a cut leaves open is paved like the sidewalk, meets it at
    # the same height, and arcade pillars and corner doors stand on the paving as drawn
    from citygen.city.massing import corner_faces
    from citygen.city.openings import wall_arrays
    from citygen.mesh.builder import MeshBuilder
    from citygen.mesh.tile import apron_mesh
    tc = built_tile[0]
    kit, dresser = homes[0], homes[1]
    cfg = dresser.arcade_cfg
    d, pd, sink = cfg["depth"], cfg["pillar"][1], cfg["sink"]
    walks = tc.ground.walk_tree
    street_tree = STRtree([st.line for st in plan.streets])
    seen = {"apron": 0, "seam": 0, "pillar": 0, "door": 0, "face": 0}
    for k, (high, out) in colonial.items():
        b = plan.buildings[k]
        if b.apron is None:
            continue
        seen["apron"] += 1
        assert b.apron.is_valid and b.apron.intersection(b.footprint).area < 1e-6
        assert all(w.intersection(b.apron).area < 1e-6 for w in walks.geometries[walks.query(b.apron)])
        mb = MeshBuilder()
        apron_mesh(mb, tc, b, street_tree)
        part = mb._parts["sidewalk"]
        pos = np.concatenate(part[0]) + mb.origin
        tris = pos[np.concatenate(part[3])]
        on_walk = walks.query(shapely.points(pos[:, :2]), predicate="dwithin", distance=1e-4)[0]
        if len(on_walk):                                        # the seam: the sidewalk's own height
            q = pos[np.unique(on_walk)]
            assert np.abs(q[:, 2] - tc.ground.walk_top(q[:, 0], q[:, 1])).max() < 1e-6, k
            seen["seam"] += 1
        p0, q0, n0, length = wall_arrays(b.footprint)
        face = np.any(corner_faces(b, p0, q0), axis=0)
        feet = []
        for p in out:
            yaw_n = np.array([-math.sin(p.yaw), math.cos(p.yaw)])
            if p.piece == "arcade_bay":
                u = np.array([math.cos(p.yaw), math.sin(p.yaw)]) * (kit.pieces["arcade_bay"].width / 2 * p.stretch - 0.2)
                feet += [(p, np.array([p.x, p.y]) + yaw_n * (d - pd / 2) + s * u) for s in (-1.0, 1.0)]
            elif p.piece.startswith("arcade_bend"):
                half = math.radians(45.0 if p.piece == "arcade_bend" else 22.5) / 2
                feet.append((p, np.array([p.x, p.y]) + yaw_n * (d - pd / 2) / math.cos(half)))
            elif kit.pieces[p.piece].category in ("door", "shop"):
                i = int(np.argmin([shapely.LineString([a, c]).distance(shapely.Point(p.x, p.y)) for a, c in zip(p0, q0)]))
                t = np.array([p.x, p.y]) + yaw_n * 0.5
                if face[i] and b.apron.contains(shapely.Point(*t)):
                    z = _drawn_z(tris, t)
                    assert z is not None and abs(p.z - z) < 0.01, (k, p.piece, p.z, z)   # on the paving
                    seen["door"] += 1
        for i in np.nonzero(face)[0]:                          # a door on a face reads its threshold here
            mid = (p0[i] + q0[i]) / 2
            t = mid + n0[i] * dresser.cfg.get("threshold_reach", 0.5)
            if b.apron.contains(shapely.Point(*t)):
                z = _drawn_z(tris, t)
                assert z is not None and abs(dresser.front_surface(mid, n0[i]) - z) < 1e-4, k
                seen["face"] += 1
        for p, f in feet:
            if not b.apron.buffer(-0.05).contains(shapely.Point(*f)):
                continue
            z = _drawn_z(tris, f)
            assert z is not None and abs(float(tc.ground.surface(f[0], f[1])) - z) < 1e-4, k  # surface = drawn
            # the pillar foot (reaching `sink` below the bay's level) is buried in the paving, never floating,
            # and the paving stays below the top of the pillar's base, never swallowing it
            assert p.z - sink < z - 0.05 and z - p.z < 0.3, (k, p.piece, p.z, z)
            seen["pillar"] += 1
    assert seen["apron"] > 30 and seen["seam"] > 30 and seen["pillar"] > 1 and seen["face"] > 50, seen


# --- more greenery (prompt 24) -------------------------------------------------------------------

def _new_trees(plan):
    return plan.trees[len(plan.trees) - plan.stats["greenery"]:]


def test_arterial_trees_stand_in_tree_pits_clear_of_junctions_lamps_arcades_and_paths(world, plan, homes):
    kit, dresser, out = homes
    cfg = world.style["greenery"]["arterial"]
    kinds = [d.kind for d in plan.districts]
    walks = [w for w in plan.walks if w.kind == "sidewalk" and plan.streets[w.street].kind in cfg["kinds"]
             and kinds[w.district] in cfg["districts"]]
    on = STRtree([w.polygon for w in walks])
    new = _new_trees(plan)
    pts = shapely.points([(t.x, t.y) for t in new])
    inp, hit = on.query(pts, predicate="within")
    assert len(inp) == len(set(inp.tolist())) > 40 and sorted(inp.tolist()) == list(range(len(inp)))  # arterials first
    xy = np.array([(new[i].x, new[i].y) for i in inp])
    for (x, y), j in zip(xy, hit):
        w = walks[int(j)]
        st = plan.streets[w.street]
        off = st.line.distance(shapely.Point(x, y))
        assert abs(off - (st.width / 2 - w.width + cfg["pit"])) < 0.05, off   # the pit, 0.9 m behind the curb
    surfaces = [st.line.buffer(st.width / 2, cap_style="flat") for st in plan.streets]
    own = [walks[int(j)].street for j in hit]
    near = STRtree(surfaces).query(shapely.points(xy), predicate="dwithin", distance=cfg["junction_clear"] - 1e-6)
    assert all(own[i] == j for i, j in zip(*near)), "a tree by a junction"
    assert not len(STRtree([m.polygon for m in plan.paint]).query(shapely.points(xy), predicate="dwithin",
                                                                 distance=cfg["paint_clear"] - 1e-6)[0])
    moved, kept, away = dresser.tree_spots(xy)                # no tree the arcades would move or drop
    assert kept.all() and not away.any() and np.allclose(moved, xy)
    tile = shapely.box(-1e9, -1e9, 1e9, 1e9)
    lamps = [p for k in set(own) for p in dresser.street_props(k, tile) if p.piece == "street_lamp"]
    assert lamps and min(np.hypot(*(xy - [p.x, p.y]).T).min() for p in lamps) > 2.0
    paths = [shapely.LineString(np.vstack([q, q[-1] + 3.0 * (q[-1] - q[-2]) / np.hypot(*(q[-1] - q[-2]))]))
             for k, (_, _, _, ps, _) in out.items() if dresser._is_slab(plan.buildings[k]) for q in ps]
    assert len(paths) > 20
    assert not len(STRtree(paths).query(shapely.points(xy), predicate="dwithin", distance=1.2)[0])   # real stair paths
    assert {new[int(i)].kind for i in inp} <= {k for k, _ in cfg["species"]}


def test_courtyard_trees_clear_their_walls(world, plan):
    from citygen.city.greenery import crown_reach
    cfg = world.style["greenery"]["courtyard"]
    courts = [(b, shapely.Polygon(h)) for b in plan.buildings if b.kind == "house" for h in b.footprint.interiors]
    tree = STRtree([c for _, c in courts])
    new = _new_trees(plan)
    inside = tree.query(shapely.points([(t.x, t.y) for t in new]), predicate="within")
    assert len(inside[0]) > 20 and sum(new[i].kind == "citrus" for i in inside[0]) > 0.5 * len(inside[0])
    for i, j in zip(*inside):
        t, court = new[int(i)], courts[int(j)][1]
        room = court.exterior.distance(shapely.Point(t.x, t.y))
        assert crown_reach(world.style, t.kind, t.height) <= room - cfg["wall_clear"] + 1e-6
        assert t.height >= cfg["min_height"]
    old = plan.trees[:len(plan.trees) - len(new)]
    held = tree.query(shapely.points([(t.x, t.y) for t in old]), predicate="within")[1]
    assert not set(held.tolist()) & set(inside[1].tolist())        # never a second tree in a courtyard


@pytest.fixture(scope="module")
def villas(world, homes):
    """A town with villas (quick world, settlement 3): its plan, dresser and every 3rd villa's garden."""
    from citygen.city.dressing import Dresser, building_highs
    from citygen.city.ground import Ground
    town = plan_city(world, world.settlements[3])
    ground = Ground(world, [town])
    dresser = Dresser(world, town, homes[0], ground)
    ks = [k for k, b in enumerate(town.buildings) if b.kind == "villa"][::3]
    highs = building_highs(ground, [town.buildings[k] for k in ks])
    out = {}
    for k, high in zip(ks, highs):
        paths: list = []
        dresser.building(k, float(high), paths)
        out[k] = (paths, *dresser.garden(k, paths))
    return town, ground, dresser, out


def test_villa_gardens_hedges_and_fruit_trees(world, villas):
    from citygen.city.openings import villa_lots
    from citygen.mesh.tile import TileContext, garden_meshes
    town, ground, dresser, out = villas
    cfg = world.style["dressing"]["hedge"]
    lots = villa_lots(town, list(out))
    width = world.style["dressing"]["paths"]["width"]
    hedges, gates, paths_seen = [], 0, 0
    for k, (paths, garden, hedge) in out.items():
        lot = town.parcels[lots[k]].polygon
        fp = town.buildings[k].footprint
        assert garden is not None and lot.buffer(1e-6).contains(garden) and garden.buffer(1e-6).contains(fp)
        assert garden.area > lot.area - 3.0 * width * sum(shapely.LineString(p).length for p in paths)
        ways = [shapely.LineString(p).buffer(width / 2, cap_style="flat") for p in paths]
        for p in hedge:
            assert p.piece == "hedge" and lot.buffer(-0.2).contains(shapely.Point(p.x, p.y))
            assert 0.09 < p.stretch <= cfg["piece_max"] / cfg["nominal"] + 1e-9   # pieces of up to 8 m fill a run
            box = _plan_box(dresser.kit, p)
            assert all(box.intersection(w).area < 1e-3 for w in ways), k       # an opening where the path runs
            hedges.append(box)
        paths_seen += len(ways)
        gates += any(w.intersects(lot.exterior) for w in ways)
    assert len(out) > 30 and paths_seen > 30 and gates > 30
    idx = STRtree(hedges)              # shared lot lines are planted once; corners meet (a sliver at 16-20 degrees)
    a, b = idx.query(hedges, predicate="intersects")
    overlap = [hedges[int(i)].intersection(hedges[int(j)]).area for i, j in zip(a, b) if i < j]
    assert max(overlap) < 0.2 and sum(o > 0.05 for o in overlap) <= 0.1 * len(out)
    # fruit trees behind or beside the house, clear of its real path
    lot_tree = STRtree([town.parcels[lots[k]].polygon for k in out])
    new = _new_trees(town)
    xy = shapely.points([(t.x, t.y) for t in new])
    inp, hit = lot_tree.query(xy, predicate="within")
    assert len(inp) > 10 and {new[int(i)].kind for i in inp} <= {"citrus", "olive"}
    for i, j in zip(inp, hit):
        paths = out[list(out)[int(j)]][0]
        assert all(shapely.LineString(p).distance(xy[int(i)]) > 1.0 for p in paths)
    # the garden ground lies exactly on the terrain mesh, `garden_lift` above it
    tc = TileContext.__new__(TileContext)
    tc.world, tc.step = world, ground.step
    from citygen.mesh.builder import MeshBuilder
    mb = MeshBuilder()
    garden_meshes(mb, tc, [g for _, g, _ in list(out.values())[:10]], ground.drawn)
    part = mb.gltf_parts()["garden"]
    pos = part["pos"][part["idx"].reshape(-1, 3)]                 # glTF axes: x, up, -y
    c = pos.mean(axis=1)
    assert np.abs(c[:, 1] - ground.drawn(c[:, 0], -c[:, 2]) - cfg["garden_lift"]).max() < 1e-6


# --- parked cars and taxis (prompt 25) -------------------------------------------------------------

def test_vehicle_pieces_are_low_poly_colored_and_never_lit(world, built_tile):
    tc = built_tile[0]
    cfg = world.style["dressing"]["vehicles"]
    for kind in ("hatch", "sedan", "van", "louage", "taxi"):
        names = [f"car_{kind}_{i}" for i in range(len(cfg[kind]))]
        assert len(names) == 4
        bodies = set()
        for name in names:
            pc = tc.kit.pieces[name]
            assert pc.category == "vehicle" and 150 <= pc.triangles <= 350, (name, pc.triangles)
            assert "glass_dark" in pc.parts and name + "_lit" not in tc.kit.pieces
            assert pc.bounds[0][1] >= 0.0 and pc.bounds[0][1] < 0.05      # wheels on the ground
            bodies |= set(pc.parts) & set(cfg[kind])
            shared = {m: id(p) for m, p in tc.kit.pieces[names[0]].parts.items()}
            assert {id(p) for p in pc.parts.values()} >= {i for m, i in shared.items() if m == "glass_dark"}
        assert len(bodies) >= (1 if kind == "louage" else 4)        # four body colors (a louage: four stripes)
    assert "taxi_sign" in tc.kit.pieces["car_taxi_0"].parts
    assert any(m.startswith("stripe_") for m in tc.kit.pieces["car_louage_0"].parts)


def test_parked_cars_keep_clear_of_trees_crossings_junctions_walks_lamps_doors_and_paint(world, plan, ground, built_mesh):
    tc, i, j, _, placements = built_mesh
    kit = tc.kit
    x0, y0 = i * tc.size, j * tc.size
    cars = [p for p in placements if kit.pieces[p.piece].category == "vehicle"]
    assert len(cars) > 40 and len({p.piece.rsplit("_", 1)[0] for p in cars}) >= 4
    assert all(x0 <= p.x < x0 + tc.size and y0 <= p.y < y0 + tc.size for p in cars)   # its center's tile
    feet = [_plan_box(kit, p) for p in cars]
    a, b = STRtree(feet).query(feet, predicate="intersects")
    assert all(feet[int(m)].intersection(feet[int(n)]).area < 1e-6 for m, n in zip(a, b) if m < n)   # no overlap
    surfaces = [st.line.buffer(st.width / 2, cap_style="flat") for st in plan.streets]
    walks = STRtree([w.polygon for w in plan.walks])
    paint = STRtree([m.polygon for m in plan.paint])
    crossings = [m.polygon for m in plan.paint if m.kind == "crossing"]
    inner = shapely.box(x0 + 3.0, y0 + 3.0, x0 + tc.size - 3.0, y0 + tc.size - 3.0)
    trunks = [shapely.Point(p.x, p.y) for p in placements if kit.pieces[p.piece].category == "tree"]
    lamps = [_plan_box(kit, p) for p in placements if p.piece == "street_lamp"]
    depth = world.style["dressing"]["open_walls"]["door_clear"]
    doors = [_plan_box(kit, p, 0.0, depth) for p in placements if kit.pieces[p.piece].category == "door"]
    assert trunks and lamps and doors and crossings
    checked = 0
    for p, foot in zip(cars, feet):
        own = [int(k) for k in np.nonzero([s.contains(foot) for s in surfaces])[0]]
        assert own, "a car off the streets"
        k = own[0]
        for m in STRtree(surfaces).query(foot, predicate="dwithin", distance=1.0).tolist():
            if m == k:
                continue                                                 # a grid street lying on k is no junction
            part = shapely.get_coordinates(plan.streets[m].line.intersection(surfaces[k]))
            assert len(part) >= 2 and np.hypot(*(part[-1] - part[0])) >= 8.0, "a car in a junction"
            v = (part[-1] - part[0]) / np.hypot(*(part[-1] - part[0]))
            ends = shapely.get_coordinates(shapely.line_interpolate_point(plan.streets[k].line, plan.streets[k].line.project(
                shapely.Point(*(part[0] + part[-1]) / 2)) + np.array([-0.5, 0.5])))
            u = (ends[1] - ends[0]) / np.hypot(*(ends[1] - ends[0]))
            assert abs(v @ u) > 0.96, "a car in a junction"
        assert not len(walks.query(foot, predicate="intersects")), "a car on a sidewalk"
        assert not len(paint.query(foot, predicate="intersects")), "a car on a painted line"
        assert min(foot.distance(c) for c in crossings) >= 1.0
        curb = min(foot.distance(walks.geometries[int(w)]) for w in walks.query(foot, predicate="dwithin", distance=1.0))
        assert curb <= 0.25, curb                                          # against the curb
        t = shapely.get_coordinates(shapely.line_interpolate_point(
            plan.streets[k].line, plan.streets[k].line.project(shapely.Point(p.x, p.y)) + np.array([-0.5, 0.5])))
        along = (t[1] - t[0]) / np.hypot(*(t[1] - t[0]))
        assert abs(along[0] * math.sin(p.yaw) - along[1] * math.cos(p.yaw)) < 0.06   # parallel to the curb
        lo, hi = kit.pieces[p.piece].bounds
        a = 0.3 * (hi[0] - lo[0])                                        # the axles, about
        ends = np.array([(p.x + s * a * math.cos(p.yaw), p.y + s * a * math.sin(p.yaw)) for s in (1, -1)])
        wheels = p.z + np.array([a, -a]) * math.tan(p.tilt)              # pitched along a sloping street
        assert np.abs(wheels - ground.surface(ends[:, 0], ends[:, 1])).max() < 0.01 and abs(p.tilt) < 0.15
        if inner.contains(foot):                                         # the tile holds what stands around it
            bark = world.style["dressing"]["parking"]["tree_trunk"]
            assert min(foot.distance(t) for t in trunks) >= 1.0 + bark - 1e-6, "a car within 1 m of a trunk"
            assert not any(foot.intersects(q) for q in lamps), "a car in a lamp"
            assert not any(foot.intersects(q) for q in doors), "a car in front of a door"
            checked += 1
    assert checked > 30
    # no car stands before a shop or cafe front (its width, out to the street), nor within front_gap of it
    gap = world.style["dressing"]["parking"]["front_gap"]
    fronts = [_plan_box(kit, p, 0.0, 15.0) for p in placements if kit.pieces[p.piece].category == "shop"]
    tree = STRtree(fronts)
    near = [min(foot.distance(fronts[int(m)]) for m in tree.query(foot, predicate="dwithin", distance=gap))
            for foot in feet if len(tree.query(foot, predicate="dwithin", distance=gap))]
    assert fronts and not near, sorted(near)[:5]


def test_parking_rows_follow_the_carriageway_width_and_a_taxi_rank_waits(world, plan, built_mesh):
    from citygen.city.dressing import Dresser
    from citygen.city.parking import parked_sides, walk_widths
    tc = built_mesh[0]
    dresser = tc.cities[0][4]
    cfg = world.style["dressing"]["parking"]
    widths, promoted, parks = walk_widths(world.style, plan.districts, plan.streets, plan.walks)
    promenade = world.style["streets"]["promenade_width"]
    seen = {1: 0, 2: 0}
    for k, st in enumerate(plan.streets):
        sides = parked_sides(st, k, widths, promoted, cfg, promenade, parks)
        assert sides.keys() == dresser._parking.sides(k).keys(), k        # the paint and the cars agree
        assert all((k, s) in parks for s in sides), k                    # only along a parking district
        carriage = st.width - sum(widths.get((k, s), 0.0) for s in (1, -1))
        if sides and k not in promoted:
            seen[len(sides)] += 1
            need = (cfg["row"] + cfg["lane"]) * len(sides)
            assert carriage >= need - 1e-6 and st.kind in cfg["kinds"]
    assert seen[1] > 20                               # 12 m streets park on one side
    boulevard = next(k for k, st in enumerate(plan.streets) if st.kind == "boulevard")
    assert len(parked_sides(plan.streets[boulevard], boulevard, widths, promoted, cfg, promenade, parks)) == 2
    # the drawn edge lines: `row` in from the curb where a row parks, `paint_edge_inset` where none does
    # (an 18 m arterial past suburb or industrial blocks parks on its other side only, or not at all)
    from citygen.city.parking import street_frame
    scfg = world.style["streets"]
    lines_of: dict = {}
    for m in plan.paint:
        if m.kind != "crossing":
            lines_of.setdefault(m.street, []).append(m.polygon)
    free = 0
    for k, st in enumerate(plan.streets):
        if st.kind not in ("arterial", "connector") or st.width <= scfg["marking_min_width"] or k not in lines_of:
            continue
        sides = parked_sides(st, k, widths, promoted, cfg, promenade, parks)
        paint = STRtree(lines_of[k])
        p, n = street_frame(st.line, np.linspace(0.2, 0.8, 7) * st.line.length)
        for s in (1, -1):
            if (k, s) not in widths:
                continue
            curb = st.width / 2 - widths[(k, s)]
            want = curb - (cfg["row"] if s in sides else scfg["paint_edge_inset"])
            hits = [len(paint.query(shapely.Point(q), predicate="dwithin", distance=0.1)) > 0 for q in p + n * s * want]
            assert sum(hits) >= 4, (k, s, sides, hits)
            if s not in sides:
                free += 1
                wrong = [len(paint.query(shapely.Point(q), predicate="dwithin", distance=0.1)) > 0
                         for q in p + n * s * (curb - cfg["row"])]
                assert not any(wrong), (k, s)
    assert free >= 3, free
    tile = shapely.box(-1e9, -1e9, 1e9, 1e9)
    k, side, run, _ = dresser._parking.rank()
    row = dresser._parking.row(k, side, run)
    assert sum(c.piece.startswith("car_taxi") for c in row) >= cfg["rank"][0]
    boulevard = plan.streets[boulevard]
    assert min(boulevard.line.distance(shapely.Point(c.x, c.y)) for c in row) < cfg["rank_reach"]
    whole = [(p.piece, p.x, p.y) for p in dresser.street_props(k, tile) if p.piece.startswith("car_")]
    c = plan.streets[k].line.centroid
    halves = [shapely.box(-1e9, -1e9, c.x, 1e9), shapely.box(c.x, -1e9, 1e9, 1e9)]
    split = [(p.piece, p.x, p.y) for h in halves                       # each half from empty caches, as a tile
             for p in Dresser(world, plan, tc.kit, dresser.ground).street_props(k, h) if p.piece.startswith("car_")]
    assert sorted(whole) == sorted(split) and whole                    # each car in exactly one tile


def test_street_furniture_pieces_are_light_and_their_water_is_never_the_sea(world, built_mesh):
    # prompt 26: four generator pieces; fountain water is `water_pool` (Blender hides `water` for its sea)
    from pathlib import Path
    kit = built_mesh[0].kit
    budget = {"bench_iron": 250, "kiosk": 400, "fountain_colonial": 900, "sabil": 400}
    for name, most in budget.items():
        pc = kit.pieces[name]
        assert pc.source == "procedural" and 60 < pc.triangles <= most, (name, pc.triangles)
        assert "water" not in pc.parts
    assert "water_pool" in kit.pieces["fountain_colonial"].parts and "water_pool" in kit.pieces["sabil"].parts
    assert kit.pieces["sabil"].anchor == "wall" and kit.pieces["kiosk"].anchor == "ground"
    lit = kit.pieces["kiosk_lit"]                                        # an open kiosk at night (prompt 21 rules)
    assert "glass_lit" in lit.parts and "glass_dark" not in lit.parts
    assert world.style["palette"]["water_pool"] != world.style["palette"]["water"]
    root = Path(__file__).resolve().parents[1]
    assert "water_pool" in (root / "tools" / "viewer" / "index.html").read_text()      # never taken for the sea
    assert 'name == "water_pool"' in (root / "tools" / "blender_beauty.py").read_text()


def test_benches_kiosks_and_fountains_stand_clear_on_walks(world, plan, built_mesh):
    # the placed result of the capital's tile, checked with the kit bounds: no piece in a trunk, lamp, door
    # (and its free zone), shop or cafe piece, arcade, parked car, crossing or other furniture; benches,
    # kiosks and fountains on a walk, a paved corner or the promenade, never on a street crossing it;
    # the sabil on open ground or a pedestrian lane, against a wall
    from citygen.city.parking import lying_on
    from citygen.city.squares import FOOT
    tc, i, j, _, placements = built_mesh
    kit, dresser = tc.kit, tc.cities[0][4]
    x0, y0 = i * tc.size, j * tc.size
    mine = {(p.piece, round(p.x, 6), round(p.y, 6)) for p in dresser.squares().items()}
    furniture = [p for p in placements if (p.piece, round(p.x, 6), round(p.y, 6)) in mine]
    names = {p.piece.replace("_lit", "") for p in furniture}
    assert {"fountain_colonial", "kiosk", "sabil"} <= names and names & {"bench_iron", "tounes/bench_sbs"}
    assert all(x0 <= p.x < x0 + tc.size and y0 <= p.y < y0 + tc.size for p in furniture)   # its anchor's tile
    cats = {p.piece: kit.pieces[p.piece].category for p in placements}
    depth = world.style["dressing"]["open_walls"]["door_clear"]
    trunk = world.style["dressing"]["squares"]["tree_trunk"]
    solid = {"lamp", "shop", "goods", "wall_goods", "awning", "arcade", "vehicle", "door"}
    others = [_plan_box(kit, p, 0.0, depth) if cats[p.piece] == "door" else _plan_box(kit, p)
              for p in placements if cats[p.piece] in solid or p.piece == "cafe_set"]
    trunks = [shapely.Point(p.x, p.y).buffer(trunk) for p in placements if cats[p.piece] == "tree"]
    crossings = [m.polygon for m in plan.paint if m.kind == "crossing"]
    ground = shapely.union_all([w.polygon for w in plan.walks] + [b.apron for b in plan.buildings if b.apron is not None])
    surfaces = [st.line.buffer(st.width / 2, cap_style="flat") for st in plan.streets]
    lines = [st.line for st in plan.streets]
    feet = [_plan_box(kit, p, 0.05 if kit.pieces[p.piece].anchor == "wall" else None) for p in furniture]
    for p, foot in zip(furniture, feet):
        for q in others + trunks + crossings + [f for f in feet if f is not foot]:
            assert not foot.intersects(q), f"{p.piece} at ({p.x:.1f}, {p.y:.1f}) overlaps"
        if kit.pieces[p.piece].anchor == "wall":
            assert all(plan.streets[k].kind in FOOT for k in STRtree(surfaces).query(foot, predicate="intersects"))
            assert not STRtree([b.footprint for b in plan.buildings]).query(foot, predicate="intersects").size
            continue
        assert ground.buffer(0.01).contains(foot), f"{p.piece} off the walks"
        for k in STRtree(surfaces).query(foot, predicate="intersects").tolist():
            if plan.streets[k].kind == "boulevard":                      # on the promenade: no street crossing it
                inside = lying_on(k, lines[k], surfaces[k], STRtree(lines), lines, world.style["dressing"]["parking"])
                assert all(m in inside for m in STRtree(surfaces).query(foot, predicate="intersects").tolist())
    # the fountain: no tree crown over its basin (as kiosks and benches measure crowns), no street lamp of
    # any street within `lamp_clear` of it or on its island (a grid street under the boulevard had one there)
    sq = world.style["dressing"]["squares"]
    for k, fp, circle, reach in dresser.squares().fountains():
        near = [i for i, t in enumerate(plan.trees) if math.hypot(t.x - fp.x, t.y - fp.y) < 15.0]
        xy, kept, away = dresser.tree_spots(np.array([(plan.trees[i].x, plan.trees[i].y) for i in near]))
        for m, i in enumerate(near):
            put = dresser.tree(i, plan.trees[i], 0.0, away[m]) if kept[m] else None
            if put is not None:
                lo, hi = kit.pieces[put.piece].bounds
                half = (hi[0] - lo[0] + hi[2] - lo[2]) / 4 * put.scale * sq["crown_cover"]
                assert not shapely.Point(xy[m]).buffer(half).intersects(circle), ("a crown over the fountain", i)
        island = next(part for kk, part in dresser.squares().islands() if kk == k and part.intersects(circle))
        lamps: list = []
        for j, st in enumerate(plan.streets):
            spacing = dresser.cfg["street_lamps"].get(st.kind)
            if spacing:
                dresser._lamps(j, float(spacing), shapely.box(*circle.buffer(30.0).bounds), lamps)
        for p in lamps:
            box = _plan_box(kit, p)
            assert box.distance(circle) >= sq["lamp_clear"] and not island.intersects(box), (p.x, p.y)


# --- people (prompt 28) ----------------------------------------------------------------------------

def _gen(parts: dict) -> np.ndarray:
    """All of a piece's positions in generator axes (x, y, z up)."""
    pos = np.concatenate([p["pos"] for p in parts.values()])
    return np.stack([pos[:, 0], -pos[:, 2], pos[:, 1]], axis=1)


def test_people_are_low_poly_figures_standing_or_seated_right(world, built_tile):
    from citygen.mesh.people import people_pieces
    cfg = world.style["dressing"]["people"]
    seat = cfg["seat"]
    pieces = people_pieces(world.seed, cfg)
    assert 20 <= len(pieces) <= 30 and all(n.startswith("person_") for n in pieces)
    assert {s["pose"] for s in cfg["pieces"].values()} == {"stand", "walk", "sit", "carry"}
    assert {s["outfit"] for s in cfg["pieces"].values()} == {"jebba", "shirt", "safsari", "dress", "boy", "girl"}
    assert seat == world.style["dressing"]["furniture"]["seat"]          # the iron bench's seat
    kit = built_tile[0].kit
    for name, parts in pieces.items():
        spec = cfg["pieces"][name[len("person_"):]]
        pc = kit.pieces[name]
        assert pc.category == "person" and pc.anchor == "ground" and name + "_lit" not in kit.pieces
        assert 200 <= pc.triangles <= 400, (name, pc.triangles)
        g = _gen(parts)
        assert np.isfinite(g).all()
        for part in parts.values():                                      # no degenerate triangles
            t = part["pos"][part["idx"].reshape(-1, 3)].astype(np.float64)
            area = np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1) / 2
            assert area.min() > 1e-7, name
        assert abs(g[:, 2].min()) < 1e-6, name                           # feet on the ground
        assert np.abs(g[:, 0]).max() < 0.6 and -0.5 < g[:, 1].min() and g[:, 1].max() < 0.8, name
        top = g[:, 2].max()
        if spec["pose"] == "sit":                                        # the hips' underside on the seat
            over = g[(np.abs(g[:, 0]) < 0.2) & (g[:, 1] > -0.15) & (g[:, 1] < 0.2) & (g[:, 2] > 0.3)]
            assert abs(over[:, 2].min() - seat) < 0.005, (name, over[:, 2].min())
            assert 1.2 < top < 1.5, (name, top)
        elif spec["outfit"] in ("boy", "girl"):
            assert 1.05 < top < 1.35, (name, top)
        else:
            assert 1.55 < top < 1.9, (name, top)
    again = people_pieces(world.seed, cfg)                               # deterministic bytes, own streams
    for name, parts in pieces.items():
        for m, part in parts.items():
            assert all(np.array_equal(part[k], again[name][m][k]) for k in ("pos", "nrm", "idx"))
    other = people_pieces(world.seed + 1, cfg)
    assert not np.array_equal(_gen(other["person_shirt_stand"]), _gen(pieces["person_shirt_stand"]))


# --- people in the streets (prompt 29) -------------------------------------------------------------

def _low_hull(kit, p, top: float):
    """Plan outline (placed) of the convex hull of a piece's vertices less than `top` m above its origin, or None."""
    pos = np.concatenate([q["pos"] for q in kit.pieces[p.piece].parts.values()])
    pos = pos[pos[:, 1] < top / p.scale]
    if not len(pos):
        return None
    x, y = pos[:, 0] * p.scale * p.stretch, -pos[:, 2] * p.scale
    c, s = math.cos(p.yaw), math.sin(p.yaw)
    return shapely.MultiPoint(np.stack([p.x + x * c - y * s, p.y + x * s + y * c], 1)).convex_hull


def test_people_stand_on_the_drawn_ground_clear_of_walls_cars_pieces_and_each_other(world, plan, built_mesh):
    tc, i, j, mb, placements = built_mesh
    kit, cfg = tc.kit, world.style["people"]
    x0, y0 = i * tc.size, j * tc.size
    poses = {"person_" + k: s["pose"] for k, s in world.style["dressing"]["people"]["pieces"].items()}
    people = [p for p in placements if kit.pieces[p.piece].category == "person"]
    assert len(people) > 500 and all(x0 <= p.x < x0 + tc.size and y0 <= p.y < y0 + tc.size for p in people)
    sit = [p for p in people if poses[p.piece] == "sit"]
    stand = [p for p in people if poses[p.piece] != "sit"]
    assert len(sit) > 40 and len({p.piece for p in people}) >= 20
    feet = [_plan_box(kit, p) for p in stand]
    seats = [_plan_box(kit, p) for p in sit]
    dresser, centers = tc.cities[0][4], tc.cities[0][1]        # with what the neighbouring tiles draw nearby
    around = placements + dresser.crowd()._halo(shapely.box(x0, y0, x0 + tc.size, y0 + tc.size), shapely.box(
        x0 - cfg["halo"], y0 - cfg["halo"], x0 + tc.size + cfg["halo"], y0 + tc.size + cfg["halo"]), centers)
    # never inside a building or a car
    fps = STRtree([b.footprint for b in plan.buildings])
    assert not len(fps.query(feet + seats, predicate="intersects")[0])
    cars = [_plan_box(kit, p) for p in around if kit.pieces[p.piece].category == "vehicle"]
    assert cars and not len(STRtree(cars).query(feet + seats, predicate="intersects")[0])
    # standing people keep `clear` apart; closer only side by side in a pair or a family (same heading)
    tree = STRtree(feet)
    a, b = tree.query(feet, predicate="dwithin", distance=cfg["clear"] - 1e-6)
    partners = np.zeros(len(stand), dtype=int)
    for m, n in zip(a.tolist(), b.tolist()):
        if m >= n:
            continue
        p, q = stand[m], stand[n]
        heading = np.array([-math.sin(p.yaw), math.cos(p.yaw)])
        assert abs(p.yaw - q.yaw) < 1e-9 and abs(heading @ (q.x - p.x, q.y - p.y)) < 1e-6, (p, q)   # abreast
        assert feet[m].distance(feet[n]) >= cfg["pair_gap"] - 1e-6
        partners[[m, n]] += 1
    assert partners.max() <= 1 and partners.sum() > 20
    a, b = STRtree(seats).query(feet, predicate="dwithin", distance=cfg["seated_gap"])
    assert all(feet[m].distance(seats[n]) >= cfg["seated_gap"] - 1e-6 for m, n in zip(a.tolist(), b.tolist()))
    # clear of goods, stalls, carts, pots, benches, cafe sets, kiosks, fountains, lamp posts and tree trunks
    # (the hull of their parts below 1.5 m), except the seat a person sits on
    solid = {"vehicle", "kiosk", "goods", "ground_prop", "furniture", "bench", "pot", "cat", "lamp", "tree", "fountain"}
    things = [p for p in around if kit.pieces[p.piece].category in solid and kit.pieces[p.piece].anchor == "ground"]
    boxes = [_low_hull(kit, p, 1.5) for p in things]
    things, boxes = [p for p, q in zip(things, boxes) if q is not None], [q for q in boxes if q is not None]
    assert len(things) > 500
    hit_p, hit_t = STRtree(boxes).query(feet, predicate="intersects")
    for m, k in zip(hit_p.tolist(), hit_t.tolist()):
        if things[k].z - stand[m].z > 2.0:                     # a string lantern hangs over the head (prompt 33)
            continue
        assert feet[m].intersection(boxes[k]).area < 1e-4, (stand[m], things[k])   # a standing person in a piece
    things = [p for p in around if p.piece in cfg["seats"]]
    on = zip(*STRtree([_low_hull(kit, p, 1.5) for p in things]).query(seats, predicate="intersects"))
    # seated people sit on a real seat, at its height: an upward face of the piece under their origin
    seat_h = world.style["dressing"]["people"]["seat"]
    found = set()
    for m, k in on:
        p, t = sit[int(m)], things[int(k)]
        pc = kit.pieces[t.piece]
        dx, dy = p.x - t.x, p.y - t.y
        lx = (dx * math.cos(t.yaw) + dy * math.sin(t.yaw)) / (t.scale * t.stretch)
        ly = (-dx * math.sin(t.yaw) + dy * math.cos(t.yaw)) / t.scale
        for part in pc.parts.values():
            tri = part["pos"][part["idx"].reshape(-1, 3)]
            nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
            up = tri[nrm[:, 1] > 0.9 * np.linalg.norm(nrm, axis=1)]
            if not len(up):
                continue
            inside = shapely.contains_xy(shapely.polygons(np.stack([up[:, :, 0], -up[:, :, 2]], 2)), lx, ly)
            for h in up[inside][:, :, 1].mean(axis=1):
                if abs(p.z + seat_h - (t.z + h * t.scale)) < 0.015:
                    found.add(int(m))
    assert found == set(range(len(sit))), [sit[m] for m in set(range(len(sit))) - found]
    # standing on the drawn surface: the highest drawn face under the origin, below the hips, is the floor
    # (with the walks a neighbouring tile draws: a walk piece belongs to the tile holding its centroid)
    from citygen.mesh.corniche import front_meshes
    from citygen.mesh.tile import walk_meshes
    walks = MeshBuilder(origin=(x0, y0))
    walk_meshes(walks, tc, plan, shapely.box(x0 - 150.0, y0 - 150.0, x0 + tc.size + 150.0, y0 + tc.size + 150.0))
    front_meshes(walks, tc, plan, shapely.box(x0 - 150.0, y0 - 150.0, x0 + tc.size + 150.0, y0 + tc.size + 150.0))
    tris = np.concatenate([q["pos"][q["idx"].reshape(-1, 3)] for m in (mb, walks) for q in m.gltf_parts().values()])
    nrm = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    tris = tris[nrm[:, 1] > 0.2 * np.linalg.norm(nrm, axis=1)]
    plan_tris = shapely.polygons(np.stack([tris[:, :, 0] + x0, y0 - tris[:, :, 2]], 2))
    pi, ti = STRtree(plan_tris).query(shapely.points([(p.x, p.y) for p in stand]), predicate="intersects")
    top = np.full(len(stand), -np.inf)
    for m, k in zip(pi.tolist(), ti.tolist()):
        t = tris[k]
        q = np.array([stand[m].x - x0, y0 - stand[m].y])
        e1, e2 = t[1, [0, 2]] - t[0, [0, 2]], t[2, [0, 2]] - t[0, [0, 2]]
        det = e1[0] * e2[1] - e1[1] * e2[0]
        u = ((q - t[0, [0, 2]])[0] * e2[1] - (q - t[0, [0, 2]])[1] * e2[0]) / det
        v = (e1[0] * (q - t[0, [0, 2]])[1] - e1[1] * (q - t[0, [0, 2]])[0]) / det
        z = t[0, 1] + u * (t[1, 1] - t[0, 1]) + v * (t[2, 1] - t[0, 1])
        if z < stand[m].z + 0.5:
            top[m] = max(top[m], z)
    err = np.abs(top - np.array([p.z for p in stand]))
    assert err.max() < 0.05, (err.max(), stand[int(np.argmax(err))])
    # outfits follow the district: robes and wraps in the medina, more modern clothes outside it
    medina = [p for p in stand if plan.medina.contains(shapely.Point(p.x, p.y))]
    outside = [p for p in stand if not plan.medina.contains(shapely.Point(p.x, p.y))]
    trad = lambda ps: sum(p.piece.split("_")[1] in ("jebba", "safsari") for p in ps) / len(ps)   # noqa: E731
    assert len(medina) > 200 and len(outside) > 100 and trad(medina) > trad(outside) + 0.15


def test_a_settlement_without_streets_dresses_without_squares_or_crowd_errors(world, built_tile, monkeypatch):
    # quick village 5 has a mosque but no streets: no sabil, kiosk, fountain or bench, and tiles still build
    from citygen.mesh.tile import build_tile
    s = world.settlements[5]
    village = plan_city(world, s)
    assert not village.streets and any(lm.kind in world.style["dressing"]["squares"]["sabil"] for lm in village.landmarks)
    monkeypatch.setattr("citygen.mesh.tile.make_kit", lambda *a: built_tile[0].kit)   # the same kit, made once
    tc = TileContext(world, [village])
    dresser = tc.cities[0][4]
    assert dresser.squares().items() == []
    mb, placements = build_tile(tc, int(s.x // tc.size), int(s.y // tc.size))
    assert mb.triangles > 0 and all(dresser.kit.pieces[p.piece].category != "fountain" for p in placements)


def _kasbah(plan):
    """(index of the kasbah's first building, its buildings, the area inside its walls with them)."""
    first = next(k for k, b in enumerate(plan.buildings) if b.kind.startswith("kasbah"))
    later = ("cathedral", "theatre", "station", "station_platforms", "station_forecourt")   # after it (prompts 32, 33)
    fort = [b for b in plan.buildings[first:] if b.kind not in later]
    return first, fort, shapely.union_all([shapely.Polygon(b.footprint.exterior) for b in fort])


def test_kasbah_holds_the_high_edge_of_the_old_town_and_keeps_clear(world, plan):
    from citygen.city.life import HOUSING
    cfg = world.style["kasbah"]
    first, fort, area = _kasbah(plan)
    kinds = [b.kind for b in fort]
    assert {"kasbah_wall", "kasbah_tower", "kasbah_gate", "kasbah_palace", "kasbah_ground", "mosque_hall",
            "minaret"} <= set(kinds)
    assert all(b.kind.startswith("kasbah") or b.kind in ("mosque_hall", "mosque_court", "minaret") for b in fort)
    assert max(h.building for h in plan.households) < first          # appended last, nobody lives there
    marks = [m for m in plan.landmarks if m.kind == "kasbah"]
    civic = [m for m in plan.landmarks if m.kind in ("cathedral", "theatre", "station", "lighthouse")]   # after it (32-34)
    assert len(marks) == 1 and marks[0] is plan.landmarks[-1 - len(civic)] and marks[0].name.split()[0] in ("Kasbah", "Dar", "Bordj")
    # it leans on the city wall, on the old town's high edge
    walls = shapely.union_all([b.footprint for b in fort if b.kind in ("kasbah_wall", "kasbah_tower")])
    ring = plan.medina.exterior
    assert walls.intersection(ring).length > 40.0
    pts = shapely.get_coordinates(shapely.line_interpolate_point(ring, np.arange(0.0, ring.length, 5.0)))
    h = world.terrain.height(pts[:, 0], pts[:, 1])
    on = shapely.distance(walls, shapely.points(pts)) < 3.0
    assert on.sum() > 8 and h[on].mean() >= np.percentile(h, 70)
    # no house, street, gate or great mosque in it, no rampart doubled along it
    for b in plan.buildings[:first]:
        if b.kind in HOUSING or b.kind in ("wall", "tower", "mosque_hall", "mosque_court", "minaret"):
            assert b.footprint.intersection(area).area < 0.5, b.kind
    surfaces = [st.line.buffer(st.width / 2, cap_style="flat") for st in plan.streets]
    assert max(s.intersection(area).area for s in surfaces) < 0.5
    great = [m for m in plan.landmarks if m.kind == "mosque"][0]
    assert area.distance(shapely.Point(great.x, great.y)) > 40.0
    assert min(area.distance(shapely.Point(m.x, m.y)) for m in plan.landmarks if m.kind == "gate") > 20.0
    # thick, tall, crowned walls; the gate faces the old town and a souk reaches it
    rampart = max(b.height for b in plan.buildings[:first] if b.kind == "wall")
    assert all(b.height > rampart and b.battlement["chains"] for b in fort if b.kind in ("kasbah_wall", "kasbah_tower", "kasbah_gate"))
    towers = [b.footprint for b in fort if b.kind in ("kasbah_tower", "kasbah_gate")]
    assert all(sum(b.footprint.distance(x) < 0.03 for x in towers) == 2 for b in fort if b.kind == "kasbah_wall")
    gate = next(b for b in fort if b.kind == "kasbah_gate")
    assert len(gate.arches) == 2 and gate.height > float(cfg["tower_height"]) - 1e-9
    outer = shapely.Point(gate.arches[0][:2])
    assert plan.medina.buffer(-20.0).contains(shapely.Point(np.add(gate.arches[0][:2], 10.0 * np.array(
        [math.cos(gate.arches[0][2]), math.sin(gate.arches[0][2])]))))
    assert any(st.kind == "souk" and st.line.distance(outer) < 1.0 for st in plan.streets)
    palace = next(b for b in fort if b.kind == "kasbah_palace")
    houses = max(b.floors for b in plan.buildings[:first] if b.kind == "house")
    assert palace.footprint.interiors and palace.floors > houses and len(palace.arches) > 10
    ground = shapely.union_all([b.footprint for b in fort if b.kind == "kasbah_ground"])
    assert ground.area > 0.3 * area.area                               # an open parade ground


def test_kasbah_only_in_capital_and_cities(world):
    # villages and towns run old_town too: no kasbah there (no `kasbah` flag in their settlement table)
    for kind in ("village", "town"):
        s = next(s for s in world.settlements if s.kind == kind)
        other = plan_city(world, s)
        assert not any(b.kind.startswith("kasbah") for b in other.buildings)
        assert not any(m.kind == "kasbah" for m in other.landmarks)


def test_kasbah_is_drawn_with_merlons_arches_and_paving(world, plan, built_mesh, homes):
    from citygen.city.roofs import roof_layouts, roof_stream
    from citygen.mesh.tile import building_mesh, paving_mesh
    tc = built_mesh[0]
    first, fort, _ = _kasbah(plan)
    cfg = world.style["kasbah"]["battlement"]
    for k, b in enumerate(fort, start=first):
        if b.kind not in ("kasbah_gate", "kasbah_tower", "kasbah_ground"):
            continue
        mb = MeshBuilder()
        if b.kind == "kasbah_ground":
            paving_mesh(mb, tc, b)
            pos = mb.gltf_parts()["paving"]["pos"]
            x, y, z = pos[:, 0], -pos[:, 2], pos[:, 1]           # glTF is Y-up
            assert np.allclose(z, tc.ground.drawn(x, y) + b.height, atol=1e-4)
            continue
        roofs = roof_layouts(b, "medina", roof_stream(world.seed, plan.settlement.id, k), tc.roofs)
        assert all(lay.band is None for _, lay in roofs)                  # no parapet under the merlons
        building_mesh(mb, b, tc.height, roofs=roofs)
        parts = mb.gltf_parts()
        ring = np.asarray(b.footprint.exterior.coords)
        high = float(tc.height(ring[:, 0], ring[:, 1]).max())
        top = parts["stone_kasbah"]["pos"][:, 1].max()
        assert abs(top - (high + b.height + cfg["breast"] + cfg["merlon"][2])) < 1e-6
        if b.kind == "kasbah_gate":
            wood = parts["wood"]["pos"]
            xy = np.stack([wood[:, 0], -wood[:, 2]], axis=1)
            d = shapely.distance(b.footprint.exterior, shapely.points(xy))
            assert np.all(d < 0.1) and not np.any(shapely.contains_xy(b.footprint, xy[:, 0], xy[:, 1]))
            assert "stone_frame" in parts and wood[:, 1].max() > high + 5.0
            sabils = [s for s in homes[1].squares().items() if homes[0].pieces[s.piece].category == "fountain"
                      and math.hypot(s.x - b.arches[0][0], s.y - b.arches[0][1]) < 12.0]
            assert sabils                                                  # a sabil by the gate, never before it
            assert all(math.hypot(s.x - a[0], s.y - a[1]) > a[3] / 2 + a[6] for s in sabils for a in b.arches)


def _roof_quads(s):
    """Plan quad, lowest springing and highest top of every roof segment of a covered stretch."""
    reach = s.shape.w + s.shape.bd
    return [(shapely.Polygon([s.p[i] - s.m[i] * reach, s.p[i + 1] - s.m[i + 1] * reach,
                              s.p[i + 1] + s.m[i + 1] * reach, s.p[i] + s.m[i] * reach]),
             min(s.z[i], s.z[i + 1]), max(s.top[i], s.top[i + 1])) for i in range(len(s.d) - 1)]


def test_covered_souks_one_rule_for_roof_and_dressing(world, plan, ground, built_mesh):
    from citygen.city.covered import owns
    from citygen.city.dressing import Dresser
    from citygen.mesh.tile import tile_bounds
    tc, i, j, _, placements = built_mesh
    covers, cfg = tc.covers[0], world.style["covered_souk"]
    stretches = covers.all()
    assert len(stretches) >= 4 and sum(s.d[-1] - s.d[0] for s in stretches) > 200.0
    alone = Dresser(world, plan, tc.kit, ground).covers()            # the dresser alone finds the same roofs
    key = lambda ss: [(s.street, s.d.tobytes(), s.z.tobytes(), s.low.tobytes(), s.lanterns) for s in ss]  # noqa: E731
    assert key(alone.all()) == key(stretches)
    for s in stretches:
        assert plan.streets[s.street].kind == "souk" and s.shape.f <= 2.0
        assert cfg["spring_min"] - 1e-9 <= s.spring <= cfg["spring"] + 1e-9
        assert s.holes.sum() >= (s.d[-1] - s.d[0]) // (2 * cfg["bay"])            # light openings every bay
        base = s.z[:, None] - s.spring
        assert np.all(s.low >= base + cfg["fill_min"] - 1e-9) and np.all(s.low <= s.z[:, None] - s.shape.band + 1e-9)
    tile = shapely.box(*tile_bounds(tc, i, j))
    dresser = tc.cities[0][4]
    for k in covers.streets:                     # no strings, bunting or sabats under a roof
        line = plan.streets[k].line
        for span in dresser.spans(k, tile):
            d = line.project(shapely.Point((np.add(span.a[:2], span.b[:2]) / 2.0).tolist()))
            assert not any(s.d[0] <= d <= s.d[-1] for s in covers.of(k))
    hooks = {(round(q[0], 6), round(q[1], 6), round(z, 6)) for s in stretches for x, z in s.lanterns
             for q in [s.frame(x)[0]] if owns(tile, q[0], q[1])}
    lanterns = [p for p in placements if (round(p.x, 6), round(p.y, 6), round(p.z, 6)) in hooks]
    assert hooks and len(lanterns) == len(hooks)                       # one lantern on every rod
    quads = [q for s in stretches for q in _roof_quads(s)]
    tree = STRtree([q[0] for q in quads])
    under = {"person": 0, "awning": 0}
    for p in placements:
        box, z0, z1 = _footprint_box(tc.kit, p, p.z)
        for q in tree.query(box, predicate="intersects"):
            _, spring, top = quads[int(q)]
            if p in lanterns:
                assert z1 <= top - tc.kit.pieces[p.piece].top                     # under the vault
            elif z0 < top:
                assert z1 <= spring + 1e-6, (p.piece, z1 - spring)            # nothing pierces a roof
                cat = tc.kit.pieces[p.piece].category
                under[cat] = under.get(cat, 0) + 1
    assert under["person"] > 20 and under["awning"] > 5                  # shops and people stay under it


def test_covered_roof_runs_on_across_a_tile_edge(plan, built_mesh):
    from types import SimpleNamespace
    from citygen.mesh.vaults import covered_meshes
    covers = built_mesh[0].covers[0]
    s = max(covers.all(), key=lambda s: s.d[-1] - s.d[0])
    j = max(range(2, len(s.d) - 2), key=lambda j: abs(s.t[j][0]) - abs(j - len(s.d) / 2) * 1e-3)
    x = float(s.p[j][0])
    one = SimpleNamespace(all=lambda: [s], cfg=covers.cfg)

    def drawn(tile):
        mb = MeshBuilder()
        covered_meshes(mb, one, tile)
        tris = [np.concatenate(part[0])[np.concatenate(part[3])] for part in mb._parts.values()]
        return np.concatenate(tris)

    whole = drawn(shapely.box(-1e7, -1e7, 1e7, 1e7))
    left, right = drawn(shapely.box(-1e7, -1e7, x, 1e7)), drawn(shapely.box(x, -1e7, 1e7, 1e7))
    area = lambda t: np.linalg.norm(np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0]), axis=1).sum() / 2  # noqa: E731
    assert len(left) and len(right) and len(left) + len(right) == len(whole)       # nothing twice, nothing lost
    assert abs(area(left) + area(right) - area(whole)) < 1e-6 * area(whole)
    across, up, _ = s.shape.ring(s.shape.r)
    ring = np.concatenate([s.p[j] + s.m[j] * across[:, None], (s.z[j] + up)[:, None]], axis=1)
    for side in (left, right):                                           # both tiles draw the shared ring
        pts = side.reshape(-1, 3)
        assert all(np.min(np.linalg.norm(pts - r, axis=1)) < 1e-9 for r in ring)
    # low-poly, inside the souk's walls, and UVs in meters along the vault (no smearing)
    length = s.d[-1] - s.d[0]
    assert len(whole) / length < 40.0
    mb = MeshBuilder()
    covered_meshes(mb, one, shapely.box(-1e7, -1e7, 1e7, 1e7))
    part = mb._parts["lime_white"]
    pos, uv, idx = np.concatenate(part[0]), np.concatenate(part[2]), np.concatenate(part[3])
    t3, t2 = pos[idx], uv[idx]
    a3 = np.linalg.norm(np.cross(t3[:, 1] - t3[:, 0], t3[:, 2] - t3[:, 0]), axis=1) / 2
    e1, e2 = t2[:, 1] - t2[:, 0], t2[:, 2] - t2[:, 0]
    ratio = np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]) / 2 / np.maximum(a3, 1e-12)
    assert 0.9 < np.median(ratio) < 1.1 and np.percentile(ratio, 95) < 1.6 and np.percentile(ratio, 5) > 0.6
    z = pos[:, 2]
    assert z.min() >= (s.z - s.spring).min() + covers.cfg["fill_min"] - 1e-6 and z.max() <= s.top.max() + 1e-6
    reach = shapely.distance(plan.streets[s.street].line, shapely.points(pos[:, :2]))
    mitre = math.cos(math.radians(covers.cfg["max_turn"] / 2))          # a bend's outer corner reaches farther
    assert reach.max() <= (s.shape.w + s.shape.bd) / mitre + 1e-6        # within the impost bands' depth


def test_boulevard_landmarks_stand_on_merged_lots_drawn_light_and_kept_clear(world, plan, ground, built_mesh):
    # prompt 32: a cathedral and a theatre appended last, each on 3-6 colonial lots of one block merged into one
    # lot facing the boulevard, nobody living there; under 6,000 triangles with meter UVs, drawn in the tile;
    # no arcade, car, bench, kiosk, person or tree trunk on them, no car or planned tree before their steps;
    # the "cathedral" and "theatre" cameras each frame a whole facade from the boulevard
    from citygen.build import camera_views
    from citygen.city import CityContext
    from citygen.city.landmarks import Frame, rect
    from citygen.city.parcels import subdivide
    from citygen.mesh.tile import building_mesh
    cfg = world.style["landmarks"]
    civic = [k for k, b in enumerate(plan.buildings) if b.kind in ("cathedral", "theatre")]
    n = len(plan.buildings) - sum(b.kind.startswith("station") for b in plan.buildings)   # the station comes after
    assert civic == [n - 2, n - 1] and [plan.buildings[k].kind for k in civic] == ["cathedral", "theatre"]
    assert not {h.building for h in plan.households} & set(civic)
    marks = {m.kind: m.name for m in plan.landmarks if m.kind in ("cathedral", "theatre")}
    saint = marks["cathedral"].removeprefix("Cathedral of St ").split(" de ")[0]
    assert saint in cfg["cathedral"]["saints"] and plan.settlement.name in marks["theatre"]
    boulevards = [st for st in plan.streets if st.kind == "boulevard"]
    ctx = CityContext(world, plan.settlement)
    tc, _, _, mb, placements = built_mesh
    assert {"stone_cathedral", "stone_dressed", "plaster_theatre", "verdigris"} <= set(mb.gltf_parts())
    kit, fps, fronts = tc.kit, [], []
    for k in civic:
        b = plan.buildings[k]
        lot = next(q for q in plan.parcels if q.polygon.buffer(0.05).contains(b.footprint))
        assert lot in plan.parcels[-2:] and plan.districts[lot.district].kind == "colonial"
        assert any(lot.polygon.exterior.intersection(st.line.buffer(st.width / 2 + 0.6, cap_style="flat")).length
                   >= cfg["min_front"] for st in boulevards)
        block, _ = plan.blocks[lot.block]                     # the block's lots as cut before the merge
        dc = world.style["district"]["colonial"]
        before = subdivide(block, float(dc["parcel_area"]), ctx.rng("parcels", lot.block))
        inside = [p for p in before if p.intersection(lot.polygon).area > 0.5 * p.area]
        assert cfg["lots"][0] <= len(inside) <= cfg["lots"][1]
        assert abs(shapely.union_all(inside).area - lot.polygon.area) < 1.0
        assert all(q.polygon.intersection(lot.polygon).area < 1.0 for q in plan.parcels if q is not lot)
        one = MeshBuilder()
        building_mesh(one, b, tc.height, landmarks=cfg)
        assert 1500 < one.triangles < 6000, (b.kind, one.triangles)
        pts = np.concatenate([np.concatenate(part[0]) for part in one._parts.values()])
        assert shapely.contains_xy(b.footprint.buffer(1.0), pts[:, 0], pts[:, 1]).all()   # the canopy: 0.8 m out
        for mat in (b.wall, b.roof):                          # textures in meters, not smeared
            part = one._parts[mat]
            pos, uv, idx = np.concatenate(part[0]), np.concatenate(part[2]), np.concatenate(part[3])
            t3, t2 = pos[idx], uv[idx]
            a3 = np.linalg.norm(np.cross(t3[:, 1] - t3[:, 0], t3[:, 2] - t3[:, 0]), axis=1) / 2
            e1, e2 = t2[:, 1] - t2[:, 0], t2[:, 2] - t2[:, 0]
            ratio = np.abs(e1[:, 0] * e2[:, 1] - e1[:, 1] * e2[:, 0]) / 2 / np.maximum(a3, 1e-12)
            assert np.all(np.abs(ratio[a3 > 0.05] - 1.0) < 0.02), (b.kind, mat)
        f = b.facade
        fps.append(b.footprint)
        fronts.append(Frame(f).poly(rect(-f["width"] / 2 - 1.0, f["width"] / 2 + 1.0, -15.0, 0.0)))
    near = shapely.union_all(fps).buffer(40.0)
    checked = set()
    for p in placements:
        if not near.contains(shapely.Point(p.x, p.y)):
            continue
        cat = kit.pieces[p.piece].category
        checked.add(cat)
        if cat in ("tree", "plant"):                           # a crown may reach over the steps, never a trunk
            assert not any(fp.buffer(0.5).contains(shapely.Point(p.x, p.y)) for fp in fps), p.piece
            continue
        box = _plan_box(kit, p)
        assert all(box.intersection(fp).area < 1e-3 for fp in fps), (p.piece, cat)
        if cat == "vehicle":
            assert all(box.intersection(z).area < 1e-3 for z in fronts), p.piece
    assert {"arcade", "vehicle", "person", "tree"} <= checked
    trees = shapely.points([(t.x, t.y) for t in plan.trees])
    clear = [Frame(plan.buildings[k].facade).poly(rect(-plan.buildings[k].facade["width"] / 2,
                                                       plan.buildings[k].facade["width"] / 2,
                                                       -cfg["tree_clear"] + 0.5, 0.0)) for k in civic]
    assert not any(shapely.contains(z, trees).any() for z in clear)
    views, cam_cfg = camera_views(plan, ground, style=world.style), cfg["camera"]
    for k in civic:                                           # a camera on the boulevard sees each whole facade
        f = plan.buildings[k].facade
        cam = np.array(views[plan.buildings[k].kind]["cam"])
        look = np.array(views[plan.buildings[k].kind]["look"])
        fr = Frame(f)
        mid = fr.xy(0.0, f["steps"])
        assert np.allclose(look[:2], mid, atol=0.1) and cam[2] > float(ground.surface(cam[0], cam[1])) + 1.0
        to = cam[:2] - mid
        assert np.linalg.norm(to) >= cam_cfg["min_distance"] and (-fr.n) @ to >= cam_cfg["facing"] * np.linalg.norm(to)
        ends = [fr.xy(s, f["steps"]) - cam[:2] for s in (-f["width"] / 2, f["width"] / 2)]
        cos = ends[0] @ ends[1] / np.linalg.norm(ends[0]) / np.linalg.norm(ends[1])
        assert math.degrees(math.acos(cos)) <= cam_cfg["spread"] + 1e-6
        assert not any(b.footprint.contains(shapely.Point(*cam[:2])) for b in plan.buildings)


def test_station_stands_at_the_colonial_edge_and_its_tracks_leave_the_city_clear(world, plan, ground, built_mesh):
    # prompt 33: a station across an avenue from the colonial quarter (never in the old town, a park or a
    # cemetery), its three buildings and its landmark last, nobody living there; 2-4 tracks from the buffer
    # stops out past the city limit through a corridor where no other building, lot, walk or tree stands;
    # streets cross it steeply (level crossings, the rails at the street's surface); in the station's tile no
    # car, person, tree or other piece stands on the precinct or the corridor
    from citygen.build import camera_views
    from citygen.city.station import KINDS, cut
    from citygen.mesh.tile import build_tile
    cfg = world.style["station"]
    st = plan.station
    n = len(plan.buildings)
    assert [b.kind for b in plan.buildings[-3:]] == ["station_forecourt", "station", "station_platforms"] == [
        KINDS[2], KINDS[0], KINDS[1]]
    assert not {h.building for h in plan.households} & {n - 3, n - 2, n - 1}
    mark = [m for m in plan.landmarks if m.kind != "lighthouse"][-1]   # the lighthouse comes after (prompt 34)
    assert mark.kind == "station" and mark.name.startswith("Gare") and plan.settlement.name in mark.name
    assert cfg["tracks"][0] <= len(st.tracks) <= cfg["tracks"][1]
    head = plan.buildings[-2]
    avenue = plan.streets[head.facade["street"]]
    colonial = [d.polygon for d in plan.districts if d.kind == "colonial"]
    assert avenue.kind == "arterial" and min(avenue.line.distance(c.boundary) for c in colonial) < 2.0
    assert all(c.intersection(st.precinct).area < 1.0 for c in colonial)
    assert plan.districts[st.district].kind not in cfg["no_station_on"]
    surfaces = [s.line.buffer(s.width / 2, cap_style="flat") for s in plan.streets]
    for b in plan.buildings[-3:]:
        assert b.footprint.is_valid and b.footprint.area > 100.0
        assert all(b.footprint.intersection(q).area < 0.5 for q in surfaces), b.kind
    zone = cut(st)
    for t in st.tracks:                                       # out past the city limit, off the old town
        end = shapely.Point(t.coords[-1])
        assert not plan.boundary.contains(end) and plan.boundary.exterior.distance(end) > cfg["beyond"] / 4
        assert not t.intersects(plan.medina)
    assert all(b.footprint.intersection(zone).area < 0.01 for b in plan.buildings[:-3])
    assert all(q.polygon.intersection(zone).area < 0.01 for q in plan.parcels)
    assert all(w.polygon.intersection(zone).area < 0.01 for w in plan.walks)
    assert not shapely.contains_xy(zone, [t.x for t in plan.trees], [t.y for t in plan.trees]).any()
    crossings = 0
    for s in plan.streets:                                    # every street on the tracks crosses them steeply
        for piece in (g for g in getattr(s.line.intersection(st.corridor), "geoms", [s.line.intersection(st.corridor)])
                      if g.geom_type == "LineString" and g.length > 0.5):
            assert not st.corridor.buffer(-0.5).contains(shapely.Point(s.line.coords[0]))
            assert not st.corridor.buffer(-0.5).contains(shapely.Point(s.line.coords[-1]))
            crossings += 1
    assert crossings >= 1
    assert "station" in camera_views(plan, ground, style=world.style)
    tc = built_mesh[0]
    i, j = int(head.footprint.centroid.x // tc.size), int(head.footprint.centroid.y // tc.size)
    mb, placements = build_tile(tc, i, j)
    assert {"dial_white", "rail_steel", "ballast", "canopy_iron", "stone_dressed"} <= set(mb._parts)
    assert sum(tc.kit.pieces[p.piece].category == "vehicle" for p in placements) > 5
    assert all(_plan_box(tc.kit, p).intersection(zone).area < 1e-6 for p in placements)
    pos = np.concatenate(mb._parts["rail_steel"][0]) + mb.origin   # rail heads at a crossing: on the street
    top = pos[ground.lift(pos[:, 0], pos[:, 1]) > 0.0]
    if len(top):
        gap = top[:, 2] - ground.surface(top[:, 0], top[:, 1])
        assert gap.max() < cfg["crossing_lift"] + 0.03 and np.percentile(gap, 75) > 0.0


def test_quays_breakwater_and_lighthouse(world, plan, ground, built_mesh):
    # prompt 34: in port districts straight quays `level` m above the sea, reach m out past the old coast (coves
    # filled, the aprons in plan.land); the ground on them is level in Ground and in the drawn terrain, which
    # agree everywhere off the walls; a vertical wall to the dredged basin; a breakwater from a quay's end out
    # into the sea with the lighthouse (the last landmark) on its head; no piece stands in the sea or on the
    # quay edge but the harbor's own; a "port" camera over the basin
    from citygen.build import camera_views
    from citygen.city.port import lengths
    from citygen.mesh.port import breakwater_meshes
    from citygen.mesh.tile import MeshBuilder, build_tile
    cfg = world.style["port"]
    port = plan.port
    level, reach = cfg["level"], cfg["reach"]
    assert port is not None and port.level == level and port.quays and port.breakwaters
    assert all(plan.districts[q.district].kind == "port" for q in port.quays)
    for q in port.quays:
        assert q.coast.distance(q.line) >= reach - 1e-6 and q.coast.hausdorff_distance(q.line) < reach + cfg["straight"] * 2
        assert plan.land.buffer(0.01).contains(q.apron) and not plan.boundary.contains(q.line)
        corniche = [s for s in plan.streets if s.kind == "corniche" and s.line.distance(q.coast) < 1.0]
        assert corniche and all(not s.line.buffer(s.width / 2).intersects(q.line) for s in corniche)
    r = np.random.default_rng(3)
    pts = []
    for q in port.quays:
        x0, y0, x1, y1 = q.apron.bounds
        p = np.column_stack([r.uniform(x0, x1, 2000), r.uniform(y0, y1, 2000)])
        pts.append(p[shapely.contains_xy(q.apron, p[:, 0], p[:, 1])])
    pts = np.concatenate(pts)
    assert len(pts) > 200 and np.all(ground.height(pts[:, 0], pts[:, 1]) == level)
    edge = np.concatenate([np.asarray(shapely.segmentize(q.line, 10.0).coords)[2:-2] for q in port.quays])
    assert np.all(ground.side_height(edge[:, 0], edge[:, 1], "raised") == level)
    assert np.all(ground.side_height(edge[:, 0], edge[:, 1], "sea") <= -cfg["depth"] + 1e-9)
    # the tile holding the breakwater's root: the drawn terrain is the ground, level on the apron
    bw = port.breakwaters[0]
    tc = built_mesh[0]
    root = bw.line.coords[0]
    i, j = int(root[0] // tc.size), int(root[1] // tc.size)
    mb, placements = build_tile(tc, i, j)
    assert {"quay", "quay_wall", "quay_wet", "rubble", "curb"} <= set(mb._parts)
    for mat in ("quay", "urban_ground", "beach"):
        if mat not in mb._parts:
            continue
        pos = np.concatenate(mb._parts[mat][0]) + mb.origin
        flat = pos[:, 2] <= level + 1e-9 if mat == "quay" else np.ones(len(pos), dtype=bool)   # not the crest
        off = flat & (shapely.distance(port.walls, shapely.points(pos[:, :2])) > 1e-6)
        assert np.allclose(pos[off, 2], ground.height(pos[off, 0], pos[off, 1]), atol=1e-9), mat
        on = flat & shapely.contains_xy(port.apron.buffer(-0.01), pos[:, 0], pos[:, 1])
        assert np.all(pos[on, 2] == level), mat
    # the breakwater starts at the quay and stays in the sea; the lighthouse stands on its head
    line = np.asarray(bw.line.coords)
    assert port.core.distance(shapely.Point(line[0])) < 1.0 and bw.basin.area > 10000.0
    tail = line[np.cumsum(np.r_[0.0, np.hypot(*np.diff(line, axis=0).T)]) > cfg["crest"][1]]
    assert np.all(world.terrain.height(tail[:, 0], tail[:, 1]) < 0.0)
    assert not shapely.intersects(port.shore, shapely.points(tail)).any()
    light = plan.landmarks[-1]
    assert light.kind == "lighthouse" and light.name.startswith("Phare")
    assert (light.x, light.y) == bw.light[:2] == tuple(line[-1])
    head = MeshBuilder(origin=(0.0, 0.0))
    breakwater_meshes(head, tc, port, plan, shapely.box(*(np.floor(line[-1] / tc.size) * tc.size),
                                                         *(np.floor(line[-1] / tc.size) * tc.size + tc.size)))
    tower = np.concatenate(head._parts["lighthouse_white"][0])
    assert {"lantern_glow", "lighthouse_red"} <= set(head._parts)
    assert np.hypot(*(tower[:, :2] - line[-1]).T).max() < 3.0 and tower[:, 2].min() >= cfg["crest"][0] - 0.5
    # nothing but the harbor's pieces in the sea or on the quay edge; no building or tree there either
    zone = tc.port_keep[0]
    harbor = {"bollard", "fender"} | {f"armour_rock_{k}" for k in range(cfg["armour"]["variants"])}
    assert {p.piece for p in placements} >= harbor
    harbor |= {p.kind for p in plan.props}       # boats float there, a crane's boom reaches over it (prompt 35)
    for p in placements:
        if p.piece not in harbor:
            assert not zone.intersects(_plan_box(tc.kit, p)), p.piece
        elif p.piece == "bollard":
            assert port.apron.contains(shapely.Point(p.x, p.y)) and p.z == level
    assert not shapely.intersects(zone, shapely.points([(t.x, t.y) for t in plan.trees])).any()
    assert not any(zone.intersects(b.footprint) for b in plan.buildings)
    assert plan.stats["quay_m"] == lengths(port)["quays"] > 500.0
    view = camera_views(plan, ground, style=world.style)["port"]
    assert view["cam"][2] > 30.0 and bw.basin.buffer(150.0).contains(shapely.Point(view["look"][:2]))


def test_boats_cranes_and_cargo_of_the_harbor(world, plan, ground, built_mesh):
    # prompt 35: plan.props from the port's own streams; every piece fits the envelope the planner uses (a crane
    # above 1.5 m may reach out); boats float with the waterline at z = 0 over water deeper than their keel, off
    # the quays, the breakwater, the shore and each other; cranes, rails and cargo stand on the quay apron at
    # quay level clear of the bollards; drawn-up boats rest on the sand above the water; the tile holding a
    # prop's center draws it, and no other piece stands where props stand on land
    from collections import Counter
    from citygen.city import CityContext
    from citygen.city.moorings import _sized, box, plan_props
    from citygen.mesh.port import quay_placements
    from citygen.mesh.tile import build_tile
    cfg = world.style["port"]["props"]
    port, props, tc = plan.port, plan.props, built_mesh[0]
    kinds = Counter(p.kind for p in props)
    assert plan_props(CityContext(world, world.capital()), plan) == props
    assert sum(kinds[k] for k in ("boat_lateen", "boat_cabin", "boat_rowing")) >= 40 and kinds["boat_trawler"] >= 2
    cranes = [k for k in kinds if k in ("crane_0", "crane_1")]
    assert len(cranes) == 1 and 2 <= kinds[cranes[0]] <= 3 and kinds["crane_rails"] >= 10
    assert kinds["cargo_crates"] and kinds["cargo_containers_0"] + kinds["cargo_containers_1"]
    for kind in kinds:                                   # pieces fit the planner's envelopes
        pos = np.concatenate([part["pos"] for part in tc.kit.pieces[kind].parts.values()])
        if kind.startswith("crane_") and kind != "crane_rails":
            pos = pos[pos[:, 1] < 1.5]
        length, width = cfg["size"][_sized(kind)]
        assert np.abs(pos[:, 0]).max() <= length / 2 + 1e-6 and np.abs(pos[:, 2]).max() <= width / 2 + 1e-6, kind
    boats = [p for p in props if p.on == "sea"]
    polys = [box(p, cfg["size"][_sized(p.kind)]) for p in boats]
    blocked = shapely.union_all([plan.land, port.raised, port.shore] + [bw.line.buffer(cfg["breakwater_clear"])
                                                                        for bw in port.breakwaters])
    tree = STRtree(polys)
    for k, (p, poly) in enumerate(zip(boats, polys)):
        assert not blocked.intersects(poly), p
        assert all(int(o) == k or polys[int(o)].distance(poly) >= cfg["side_gap"] - 1e-6
                   for o in tree.query(poly.buffer(cfg["side_gap"])))
        pts = np.vstack([np.asarray(poly.exterior.coords), np.asarray(poly.centroid.coords)])
        draft = cfg["draft"][_sized(p.kind)] * p.scale
        assert np.all(ground.height(pts[:, 0], pts[:, 1]) <= -draft - cfg["keel_clear"] + 1e-6), p
    assert sum(1 for p in boats if port.breakwaters[0].basin.contains(shapely.Point(p.x, p.y))
               and min(q.line.distance(shapely.Point(p.x, p.y)) for q in port.quays) >= cfg["anchor_clear"]) >= 3
    apron = port.apron.buffer(1e-6)
    for p in props:
        if p.on == "quay":
            assert apron.contains(box(p, cfg["size"][_sized(p.kind)])), p
    # the tile with most props: drawn exactly there, at the right height, nothing else on their ground
    i, j = Counter((int(p.x // tc.size), int(p.y // tc.size)) for p in props).most_common(1)[0][0]
    mb, placements = build_tile(tc, i, j)
    tile = shapely.box(i * tc.size, j * tc.size, (i + 1) * tc.size, (j + 1) * tc.size)
    mine = [p for p in props if tile.covers(shapely.Point(p.x, p.y)) and p.x < (i + 1) * tc.size and p.y < (j + 1) * tc.size]
    drawn = [q for q in placements if q.piece in kinds]
    assert sorted((q.piece, q.x, q.y) for q in drawn) == sorted((p.kind, p.x, p.y) for p in mine) and len(drawn) > 50
    for q in drawn:
        piece = tc.kit.pieces[q.piece]
        if piece.category == "boat":
            assert q.z == 0.0 and piece.bottom < -0.2 and q.tilt == 0.0     # the waterline at 0, the hull below it
        else:
            assert q.z == port.level
    bollards = [b for b in quay_placements(tc, port, tile) if b.piece == "bollard"]
    zone = tc.prop_zones[0]
    assert all(zone.distance(shapely.Point(b.x, b.y)) > 0.5 for b in bollards)
    for q in placements:
        if q.piece not in kinds and q.piece not in ("bollard", "fender") and q.piece in tc.kit.pieces:
            assert not zone.intersects(_plan_box(tc.kit, q)), q.piece
    # drawn-up boats: keel on the drawn sand, both ends above the water, off streets, walks and buildings
    ashore = [p for p in props if p.on == "beach"]
    assert ashore
    dresser = tc.cities[0][4]
    for p in ashore:
        (q,) = [q for q in dresser.props(shapely.box(p.x - 0.01, p.y - 0.01, p.x + 0.01, p.y + 0.01))]
        half = cfg["size"]["boat_fishing"][0] * p.scale / 2
        c, s = math.cos(p.yaw), math.sin(p.yaw)
        ends = np.array([(p.x - c * half, p.y - s * half), (p.x + c * half, p.y + s * half)])
        assert np.all(ground.surface(ends[:, 0], ends[:, 1]) > 0.0) and abs(q.tilt) < 0.2
        keel = q.z + tc.kit.pieces[p.kind].bottom * p.scale
        assert abs(keel - (float(ground.surface(p.x, p.y)) - cfg["beach_sink"])) < 0.12
        poly = box(p, cfg["size"]["boat_fishing"])
        assert not any(s.line.buffer(s.width / 2).intersects(poly) for s in plan.streets)


def test_corniche_promenade_sea_wall_palms_benches_and_railing(world, plan, ground, built_mesh):
    # prompt 36: along colonial, modern and residential stretches of the corniche a raised promenade between the
    # carriageway and the sea, never over water or the harbor; its top level across, curb height above the
    # ribbon at its curb; the beach-side palms on it in a row; lamps in the palm row, benches by the railing
    # facing the sea; the railing along the sea edge (broken at the steps); a sea wall down past the ground;
    # strollers and sitters on it; no paint or parked car on it; a "corniche" camera on it looking along it
    from citygen.build import camera_views
    from citygen.city.corniche import lengths, palms_of
    cfg = world.style["corniche"]
    tc, i, j, mb, placements = built_mesh
    fronts = plan.fronts
    walks = [w for w in plan.walks if w.kind == "seafront"]
    assert fronts and len(walks) > 10 and plan.stats["promenade_m"] == lengths(fronts)["promenade_m"] > 500.0
    assert plan.stats["beach_m"] > 100.0 and sum(len(f.stairs) for f in fronts) >= 2
    assert all(plan.districts[f.district].kind in cfg["districts"] for f in fronts)
    union = shapely.union_all([w.polygon for w in walks])
    sidewalks = shapely.union_all([w.polygon for w in plan.walks if w.kind == "sidewalk"])
    r = np.random.default_rng(36)
    for w in walks:
        st = plan.streets[w.street]
        curb = st.width / 2 - cfg["curb"]
        poly = w.polygon
        assert poly.is_valid and cfg["min_width"] - 1e-6 <= w.width <= cfg["max_width"] + 1e-6
        assert not poly.intersects(plan.port.zone) and poly.intersection(sidewalks).area < 1e-6
        ring = np.asarray(poly.exterior.coords)
        assert np.all(shapely.distance(st.line, shapely.points(ring)) >= curb - 1e-6)    # off the carriageway
        x0, y0, x1, y1 = poly.bounds
        pts = np.column_stack([r.uniform(x0, x1, 400), r.uniform(y0, y1, 400)])
        pts = np.vstack([pts[shapely.contains_xy(poly, pts[:, 0], pts[:, 1])], ring])
        assert np.all(ground.height(pts[:, 0], pts[:, 1]) > 0.0)                         # never over water
        # level across: the top at any point is the top at the nearest point of the curb line
        q = shapely.get_coordinates(shapely.line_interpolate_point(w.edge, shapely.line_locate_point(w.edge, shapely.points(pts))))
        top = ground.surface(pts[:, 0], pts[:, 1])
        assert np.allclose(top, ground.walk_top(q[:, 0], q[:, 1]), atol=1e-9)
        assert np.allclose(ground.walk_top(q[:, 0], q[:, 1]) - ground.height(q[:, 0], q[:, 1]),
                           0.3 + world.style["streets"]["curb_height"], atol=1e-9)
    # the beach-side palms stand in a row on the promenade (moved from the carriageway: test_massing_...)
    palms = [k for f in fronts for _, k in palms_of(plan, f, cfg)]
    assert len(palms) > 30 and all(union.contains(shapely.Point(plan.trees[k].x, plan.trees[k].y)) for k in palms)
    # lamps in the palm row, benches by the railing facing the sea, the railing on the sea edge
    dresser = tc.cities[0][4]
    items = dresser.seafront().items()
    sea = shapely.union_all([f.sea for f in fronts])
    lamps = [p for p in items if p.piece == "street_lamp"]
    benches = [p for p in items if p.piece in ("bench_iron", "tounes/bench_sbs")]
    rails = [p for p in items if p.piece == "railing_sea"]
    assert len(lamps) > 10 and len(benches) > 10 and len(rails) > 200
    trunks = shapely.union_all([shapely.Point(plan.trees[k].x, plan.trees[k].y).buffer(0.5) for k in palms])
    for p in lamps + benches:
        box = _plan_box(tc.kit, p)
        assert union.contains(box) and not box.intersects(trunks), p
    for p in lamps:
        st = plan.streets[fronts[0].street]
        assert abs(st.line.distance(shapely.Point(p.x, p.y)) - (st.width / 2 - cfg["curb"] + cfg["palm_inset"])) < 0.05
    for p in benches:
        front = np.array([-math.sin(p.yaw), math.cos(p.yaw)])
        near = sea.interpolate(sea.project(shapely.Point(p.x, p.y)))
        out = np.array([near.x - p.x, near.y - p.y])
        assert front @ out / np.linalg.norm(out) > 0.95 and _plan_box(tc.kit, p).distance(sea) > 0.6
    for f in fronts:
        mine = [p for p in rails if f.sea.distance(shapely.Point(p.x, p.y)) < cfg["railing_inset"] + 0.02]
        covered = sum(cfg["railing_piece"] * p.stretch for p in mine)
        gaps = len(f.stairs) * (cfg["stair"][0] + 0.1)
        assert abs(covered + gaps - f.sea.length) < 0.05 * f.sea.length
        for p in mine:
            d = f.sea.project(shapely.Point(p.x, p.y))
            a, b = f.sea.interpolate(max(d - 0.5, 0.0)), f.sea.interpolate(min(d + 0.5, f.sea.length))
            assert abs(math.cos(p.yaw) * (b.y - a.y) - math.sin(p.yaw) * (b.x - a.x)) < 0.05 * math.hypot(b.x - a.x, b.y - a.y)
    # no street lamp of the corniche left on the promenade, no paint, no parked car on it
    for k, st in enumerate(plan.streets):
        if st.kind == "corniche":
            for n in range(int(st.line.length // 24.0)):
                spot = dresser.lamp_spot(k, n, 24.0)
                assert spot is None or not union.contains(shapely.Point(spot[0]))
    assert not any(m.polygon.intersects(union) for m in plan.paint)
    tile = shapely.box(i * tc.size, j * tc.size, (i + 1) * tc.size, (j + 1) * tc.size)
    assert union.intersects(tile)
    cars = [p for p in placements if tc.kit.pieces[p.piece].category == "vehicle"]
    assert not any(_plan_box(tc.kit, p).intersects(union) for p in cars)
    # drawn: paving, the sea wall reaching under the ground, a coping band; railing and people in the tile
    assert {"promenade", "quay_wall", "lime_white"} <= set(mb._parts)
    wall = np.concatenate(mb._parts["quay_wall"][0]) + mb.origin
    low = wall[np.argsort(wall[:, 2])[:20]]
    assert np.all(low[:, 2] < ground.height(low[:, 0], low[:, 1]) - cfg["foot"] + 0.05)
    assert any(p.piece == "railing_sea" for p in placements)
    people = [p for p in placements if tc.kit.pieces[p.piece].category == "person" and union.contains(shapely.Point(p.x, p.y))]
    poses = {"person_" + k: s["pose"] for k, s in world.style["dressing"]["people"]["pieces"].items()}
    assert len(people) > 10 and any(poses[p.piece] == "sit" for p in people)
    view = camera_views(plan, ground, style=world.style)["corniche"]
    cam, look = shapely.Point(view["cam"][:2]), shapely.Point(view["look"][:2])
    assert union.contains(cam) and union.contains(look) and 40.0 < cam.distance(look) < 80.0
    assert abs(view["cam"][2] - float(ground.surface(cam.x, cam.y)) - 1.7) < 0.06


def test_seaside_cafe_terraces(world, plan, ground, built_mesh):
    # prompt 37: cafe tables under parasols along the corniche: on the sidewalks of cafes facing the sea, across the
    # road on the palm line and round drinks kiosks by the railing. Never on the carriageway, the railing or the
    # steps, never in another piece or person; the walkway stays free; customers sit on the real chairs.
    from dataclasses import replace
    from citygen.city.dressing import ground_heights
    from citygen.city.openings import piece_boxes
    cfg, tcfg = world.style["corniche"], world.style["corniche"]["terrace"]
    fur = world.style["dressing"]["furniture"]
    tc, i, j, mb, placements = built_mesh
    kit, dresser, fronts = tc.kit, tc.cities[0][4], plan.fronts
    # the parasol: one piece per color sharing the pole and ribs, its canvas with faces on both sides
    radius, rim, top, foot = fur["parasol"]
    colors = fur["parasol_colors"]
    pcs = [kit.pieces[c] for c in colors]
    assert len(colors) == 3 and all(pc.category == "parasol" and pc.parts["wood"] is pcs[0].parts["wood"] for pc in pcs)
    for pc, c in zip(pcs, colors):
        tri = pc.parts[c]["pos"][pc.parts[c]["idx"].reshape(-1, 3)]
        up = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])[:, 1]             # glTF y is up
        assert (up > 1e-9).sum() == (up < -1e-9).sum() > 0
        lo, hi = pc.bounds
        assert abs(hi[0] - radius * math.cos(math.pi / 8)) < 0.01 and abs(lo[1] - foot) < 1e-6 and top < hi[1] < top + 0.2
        assert pc.triangles < 200
    items = dresser.seafront().items()
    tables = [p for p in items if p.piece == "cafe_set"]
    shades = [p for p in items if p.piece in colors]
    kiosks = [p for p in items if kit.pieces[p.piece].category == "kiosk"]
    mine = tables + shades + kiosks
    others = [p for p in items if p not in mine]
    prom = shapely.union_all([w.polygon for w in plan.walks if w.kind == "seafront"]).buffer(0.01)
    side = shapely.union_all([w.polygon for w in plan.walks if w.kind == "sidewalk"]).buffer(0.01)
    on_prom = [p for p in tables if prom.contains(_plan_box(kit, p))]
    on_side = [p for p in tables if side.contains(_plan_box(kit, p))]
    assert len(on_prom) + len(on_side) == len(tables)                                   # never on the carriageway
    assert len(on_side) >= 3 and len(on_prom) >= 8 and len(kiosks) >= 2 and len(shades) >= 10
    assert all(prom.contains(_plan_box(kit, p)) for p in kiosks)
    fp = STRtree([b.footprint for b in plan.buildings])
    sea, edge = shapely.union_all([f.sea for f in fronts]), shapely.union_all([f.edge for f in fronts])
    rails = shapely.union_all([_plan_box(kit, p) for p in others if p.piece == "railing_sea"])
    stairs = shapely.union_all([shapely.Point(s[0], s[1]).buffer(cfg["stair"][0] / 2) for f in fronts for s in f.stairs])
    at = {(p.x, p.y) for p in tables}
    canopies = {}
    for p in shades:                         # in a table's hole; the canopy over the walks, off walls and railing
        canopy = shapely.Point(p.x, p.y).buffer(radius, quad_segs=2)
        canopies[(p.x, p.y)] = canopy
        assert (p.x, p.y) in at and (prom.contains(canopy) or side.contains(canopy)) and not len(fp.query(canopy, predicate="intersects"))
        assert canopy.distance(sea) >= tcfg["rail_clear"] - 1e-6
    for p in tables + kiosks:
        box = _plan_box(kit, p)
        assert not len(fp.query(box, predicate="intersects")) and not box.intersects(rails) and not box.intersects(stairs)
        if prom.contains(box):               # the walkway stays free: by the curb or by the sea edge
            pts = shapely.points(shapely.get_coordinates(box))
            assert shapely.distance(edge, pts).max() <= tcfg["row_reach"] + 1e-6 or \
                shapely.distance(sea, pts).max() <= tcfg["sea_reach"] + 1e-6
    # nothing in another piece: the seafront's lamps, benches and railing, the walls' pieces, street props, trunks
    region = shapely.union_all([_plan_box(kit, p) for p in mine]).buffer(3.0)
    around = list(others)
    for k in sorted(int(b) for b in fp.query(region, predicate="intersects")):
        around += dresser.wall_pieces(k)
    for k in sorted(int(s) for s in dresser.surface_tree.query(region, predicate="intersects")):
        around += dresser.street_props(k, region)
    around = [replace(p) for p in around if p.piece in kit.pieces]
    solid = [replace(p) for p in tables + kiosks]
    ground_heights(ground, around)
    ground_heights(ground, solid)
    trunks = [shapely.Point(t.x, t.y).buffer(0.3) for t in plan.trees if region.contains(shapely.Point(t.x, t.y))]
    foot_a, a0, a1 = piece_boxes(kit, around, 0.0)
    foot_s, s0, s1 = piece_boxes(kit, solid, 0.0)
    for m, p in enumerate(solid):
        z = float(ground.surface(p.x, p.y))
        hit = (a0 < s1[m]) & (a1 > s0[m]) & shapely.intersects(foot_s[m], foot_a)
        assert not hit.any() and not any(foot_s[m].intersects(t) for t in trunks), p
        for n in range(m + 1, len(solid)):
            assert foot_s[m].intersection(foot_s[n]).area < 1e-6, (p, solid[n])
        if (p.x, p.y) in canopies:           # the canopy's height band against everything else
            c0, c1 = z + rim - fur["parasol_valance"], z + top
            hit = (a0 < c1) & (a1 > c0) & shapely.intersects(canopies[(p.x, p.y)], foot_a)
            assert not hit.any() and not ((s0 < c1) & (s1 > c0) & shapely.intersects(canopies[(p.x, p.y)], foot_s)).any()
            assert sum(c.intersection(canopies[(p.x, p.y)]).area > 1e-6 for c in canopies.values()) == 1
    # customers on the real chairs of this tile's terrace tables, facing the table; some chairs stay empty
    seats = world.style["people"]["seats"]["cafe_set"]
    poses = {"person_" + k: s["pose"] for k, s in world.style["dressing"]["people"]["pieces"].items()}
    here = [p for p in placements if p.piece == "cafe_set" and (round(p.x, 9), round(p.y, 9)) in
            {(round(x, 9), round(y, 9)) for x, y in at}]
    people = [p for p in placements if kit.pieces[p.piece].category == "person"]
    seated = 0
    for t in here:
        c, s = math.cos(t.yaw), math.sin(t.yaw)
        for sx, sy, face in seats["seats"]:
            q = (t.x + sx * c - sy * s, t.y + sx * s + sy * c)
            sit = [p for p in people if math.hypot(p.x - q[0], p.y - q[1]) < 1e-6]
            if sit:
                p = sit[0]
                assert poses[p.piece] == "sit" and abs(p.z - (t.z + seats["height"] - 0.45)) < 1e-6
                facing = np.array([-math.sin(p.yaw), math.cos(p.yaw)])
                assert facing @ (np.array([t.x, t.y]) - q) / np.hypot(t.x - q[0], t.y - q[1]) > 0.85
                seated += 1
    assert len(here) >= 4 and 3 <= seated < 2 * len(here)
    tops = [_plan_box(kit, t) for t in here]
    for p in people:                         # nobody stands in a terrace table; nobody on a carriageway
        if poses[p.piece] != "sit":
            assert not any(_plan_box(kit, p).intersects(b) for b in tops), p


# --- level of detail (prompt 40) ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def lod_tiles(built_mesh, rebuilt_tile, tmp_path_factory):
    """lod1 files of the capital's tile and of its east and north neighbours: {(i, j): (path, entry)}."""
    from citygen.mesh.lod import write_lod
    tc, i, j, mb, _ = built_mesh
    folder = rebuilt_tile[1].parent
    out = {}
    for key in ((i, j), (i + 1, j), (i, j + 1)):
        entry = write_lod(tc, *key, folder, water=mb.has("water") if key == (i, j) else False)
        out[key] = (folder / entry["file"], entry)
    return out


def _world_points(path, i: int, j: int, size: int, terrain: bool | None = None) -> np.ndarray:
    """Every written vertex of a lod1 file in world meters (x east, y north, z up); `terrain`: only the tinted
    terrain parts (True) or only the rest (False)."""
    pts = [p["pos"] for p in read_parts(path).values() if terrain is None or (p["col"] is not None) == terrain]
    pos = np.concatenate(pts)
    return np.stack([pos[:, 0] + i * size, -pos[:, 2] + j * size, pos[:, 1]], axis=1)


def test_lod1_tiles_are_valid_light_and_listed_for_resume(world, built_mesh, rebuilt_tile, lod_tiles, tmp_path):
    from citygen.mesh.tile import export_tile
    tc, i, j, _, _ = built_mesh
    path, entry = lod_tiles[(i, j)]
    gltf, binary = read_glb(path)
    _check_glb(gltf, binary)
    assert triangle_count(gltf) == entry["triangles"] > 2000 and path.stat().st_size == entry["bytes"]
    assert gltf["extensionsRequired"] == ["KHR_mesh_quantization"] and "EXT_mesh_gpu_instancing" not in str(gltf)
    assert not gltf.get("textures") and all("TEXCOORD_0" not in p["attributes"]
                                            for m in gltf["meshes"] for p in m["primitives"])
    assert entry["bytes"] < 0.15 * rebuilt_tile[2]["bytes"]           # the densest quick tile: about 3.4%
    far = (i - 6, j + 6)                                              # terrain only: the hardest ratio
    full = export_tile(tc, *far, tmp_path)
    assert full["lod1"]["file"] == f"tile_{far[0]}_{far[1]}_lod1.glb" and full["lod1"]["file"] in full["files"]
    assert (tmp_path / full["lod1"]["file"]).stat().st_size == full["lod1"]["bytes"] < 0.15 * full["bytes"]
    names = set(read_parts(tmp_path / full["lod1"]["file"]))
    assert names and not names & {"leaf", "trunk", "door_blue", "glass_dark"}   # no trees, no dressing


def test_lod1_terrain_meets_the_full_tile_and_its_neighbours_and_hangs_skirts(world, built_mesh, lod_tiles):
    tc, i, j, _, _ = built_mesh
    size, skirt = tc.size, float(tc.lod_cfg["skirt"])
    pts = {k: _world_points(path, *k, size, terrain=True) for k, (path, _) in lod_tiles.items()}
    here = pts[(i, j)]
    x0, y0 = i * size, j * size
    for axis, value in ((0, x0), (0, x0 + size), (1, y0), (1, y0 + size)):   # all four edges
        edge = here[np.abs(here[:, axis] - value) < 0.02]
        along = np.round(edge[:, 1 - axis] / tc.step).astype(int)
        top = {a: edge[along == a, 2].max() for a in np.unique(along)}
        assert len(top) == size // int(tc.step) + 1                   # the full tile's 8 m points, every one
        g = tc.height(*(np.array([[value, a * tc.step] if axis == 0 else [a * tc.step, value]
                                  for a in sorted(top)]).T))
        assert np.max(np.abs(np.array([top[a] for a in sorted(top)]) - g)) < 0.02   # as the full tile draws it
        nodes = [a for a in top if a % 4 == 0]
        for a in nodes:                                               # the skirt hangs below every 32 m node
            low = edge[along == a, 2].min()
            assert abs(top[a] - low - skirt) < 0.03, (axis, value, a)
    for other, axis in (((i + 1, j), 0), ((i, j + 1), 1)):            # shared edges: the same heights
        value = (i + 1) * size if axis == 0 else (j + 1) * size
        a = here[np.abs(here[:, axis] - value) < 0.02]
        b = pts[other][np.abs(pts[other][:, axis] - value) < 0.02]
        ta = {round(p[1 - axis] / tc.step): p[2] for p in a[np.argsort(a[:, 2])]}   # highest z per point: the top
        tb = {round(p[1 - axis] / tc.step): p[2] for p in b[np.argsort(b[:, 2])]}
        assert ta.keys() == tb.keys() and max(abs(ta[k] - tb[k]) for k in ta) < 0.02


def test_lod1_keeps_the_skyline_and_merges_blocks(world, plan, built_mesh, lod_tiles):
    from citygen.mesh.lod import lod_of
    tc, i, j, _, _ = built_mesh
    lod = lod_of(tc)
    tall = max((b for b in plan.buildings if b.kind == "minaret"), key=lambda b: b.height)
    c = tall.footprint.centroid
    assert (int(c.x // tc.size), int(c.y // tc.size)) == (i, j)       # the great mosque's minaret, in this tile
    pts = _world_points(lod_tiles[(i, j)][0], i, j, tc.size, terrain=False)
    ring = np.asarray(tall.footprint.exterior.coords)
    high = float(np.max(tc.height(ring[:, 0], ring[:, 1])))
    near = pts[np.hypot(pts[:, 0] - c.x, pts[:, 1] - c.y) < tall.top["side"]]
    top = high + tall.height + tall.top["height"]                     # the lantern's top, then its cap above
    assert np.any(np.abs(near[:, 2] - (high + tall.height)) < 0.05)   # the shaft's roof
    assert np.any(np.abs(near[:, 2] - top) < 0.05) and near[:, 2].max() > top + 0.5 * tall.top["side"]
    blocks = lod.cities[0]
    assert blocks.role[plan.buildings.index(tall)] == "solo"
    clustered = {plan.buildings[k].kind for k in np.nonzero(blocks.role == "cluster")[0]}
    assert {"cathedral", "theatre", "station"} <= clustered
    merged = sum(len(ks) for ks in blocks.members.values())
    assert merged > 0.9 * sum(b.kind in ("house", "apartments", "shed") for b in plan.buildings)
    assert len(blocks.members) < 0.2 * merged                         # many buildings to a block


def test_finished_tiles_need_their_lod1_file(tmp_path):
    from citygen.build import finished_tiles
    (tmp_path / "tile_0_0.glb").write_bytes(b"abc")
    journal = tmp_path / "journal"
    journal.mkdir()
    lod = {"file": "tile_0_0_lod1.glb", "bytes": 2, "triangles": 1}
    entry = {"i": 0, "j": 0, "file": "tile_0_0.glb", "bytes": 3, "files": [lod["file"]], "lod1": lod}
    (journal / "tile_0_0.json").write_text(json.dumps(entry))
    assert finished_tiles(tmp_path, journal, "k", [(0, 0)]) == {}     # no lod1 yet: build the tile again
    (tmp_path / "tile_0_0_lod1.glb").write_bytes(b"x")
    assert finished_tiles(tmp_path, journal, "k", [(0, 0)]) == {}     # cut short
    (tmp_path / "tile_0_0_lod1.glb").write_bytes(b"xy")
    assert (0, 0) in finished_tiles(tmp_path, journal, "k", [(0, 0)])


def test_phone_page_patches_the_viewer_and_stores_lod1_tiles(tmp_path):
    """Prompt 41: make_artifact patches the streaming viewer by exact strings and converts lod1 files too."""
    import base64
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
    import make_artifact
    src = tmp_path / "w"
    (src / "tiles" / "textures").mkdir(parents=True)
    (src / "tiles" / "textures" / "plaster.png").write_bytes(b"png")
    (src / "tiles" / "tile_0_0.glb").write_bytes(b"full tile")
    (src / "tiles" / "tile_0_0_lod1.glb").write_bytes(b"lod")
    lod = {"file": "tile_0_0_lod1.glb", "bytes": 3, "triangles": 1}
    entry = {"i": 0, "j": 0, "x0": 0, "y0": 0, "file": "tile_0_0.glb", "bytes": 9, "lod1": lod,
             "files": ["textures/plaster.png", lod["file"]]}
    (src / "tiles" / "index.json").write_text(json.dumps({"tile_size": 512, "tiles": [entry]}))
    art = tmp_path / "art"
    make_artifact.make_artifact(src, art, "T", "aerial")
    tile = json.loads((art / "data" / "tiles" / "index.json").read_text())["tiles"][0]
    assert tile["file"] == "tile_0_0.json" and tile["lod1"]["file"] == "tile_0_0_lod1.json"
    assert tile["files"] == ["textures/plaster.png", "tile_0_0_lod1.json"]
    for name, raw in (("tile_0_0.json", b"full tile"), ("tile_0_0_lod1.json", b"lod")):
        assert base64.b64decode(json.loads((art / "data" / "tiles" / name).read_text())["glb"]) == raw
    html = (art / "index.html").read_text()
    assert "atob((await res.json()).glb)" in html and "res.arrayBuffer()" not in html
    assert "fetch(url, { signal })" in html          # cancellable loads survive the patch
