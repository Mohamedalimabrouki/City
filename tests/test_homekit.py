"""The home kit of interiors (prompts 52 and 53, SPEC 6d): traditional and modern pieces, their images."""
import numpy as np
import pytest

from citygen.config import load_config, load_style


@pytest.fixture(scope="module")
def style():
    return load_style(load_config()["world"]["style"])


@pytest.fixture(scope="module")
def home(style):
    from citygen.interior.homekit import home_kit
    return home_kit(42, style)


@pytest.fixture(scope="module")
def city(style):
    from citygen.kit import make_kit
    return set(make_kit(42, load_config(), style).pieces)


def _check_table(home, style, city, module):
    palette = {**style["palette"], **style["interiors"]["palette"]}
    for base, (cat, anchor, size, tris, extra) in module.TABLE.items():
        for suffix in module.VARIANTS.get(base, (None,)):
            name = f"home/{base}" if suffix is None else f"home/{base}_{suffix}"
            pc, spec = home.pieces[name], home.specs[name]
            assert (pc.category, pc.anchor, pc.source) == (cat, anchor, "procedural"), name
            assert pc.triangles <= tris == spec.tris, (name, pc.triangles)
            lo, hi = pc.bounds                                    # glTF axes: y up, -z the front
            extent = np.array([hi[0] - lo[0], hi[2] - lo[2], hi[1] - lo[1]])
            want = module.SIZES.get(name[5:], size)
            assert np.abs(extent - np.array(want)).max() <= 0.02, (name, extent, want)
            assert abs(lo[1] - spec.z[0]) <= 0.02, name
            if anchor == "wall":
                assert hi[2] <= 0.005, name                       # nothing behind the wall face
            if anchor == "ceiling":
                assert hi[1] <= 0.005, name
            if cat == "rug":
                assert hi[1] <= 0.02, name
            for mat, part in pc.parts.items():
                assert mat in palette, (name, mat)
                assert (part.get("uv") is not None) == bool(palette[mat].get("texture")), (name, mat)
            assert name not in city


def test_home_pieces_traditional(home, style, city):
    from citygen.interior import kit_new, kit_old
    _check_table(home, style, city, kit_old)
    from citygen.interior import kit_life
    lights = sum(1 for pc in home.pieces.values() if pc.category == "light" and not pc.name.endswith("_on"))
    assert len(home.pieces) == len(kit_old.names()) + len(kit_new.names()) + len(kit_life.names()) + lights
    assert not set(kit_old.names()) & set(kit_new.names())
    assert not (set(kit_old.names()) | set(kit_new.names())) & set(kit_life.names())


def test_home_pieces_modern(home, style, city):
    from citygen.interior import kit_new
    _check_table(home, style, city, kit_new)


def test_home_pieces_life(home, style, city):
    """Prompt 55: the lights (first slice of the life table); every `light` piece has its `_on` twin, the
    same parts with `lamp_glass` as `lamp_glow`, and `lamp_glow` is an exact copy of `lamp_glass`."""
    from citygen.interior import kit_life
    _check_table(home, style, city, kit_life)
    inner = style["interiors"]["palette"]
    assert inner["lamp_glow"] == inner["lamp_glass"]
    lights = [n for n, pc in home.pieces.items() if pc.category == "light" and not n.endswith("_on")]
    assert lights
    for name in lights:
        pc, on = home.pieces[name], home.pieces[name + "_on"]
        assert "lamp_glass" in pc.parts and "lamp_glow" not in pc.parts, name
        assert set(on.parts) == set(pc.parts) - {"lamp_glass"} | {"lamp_glow"}, name
        assert on.parts["lamp_glow"] is pc.parts["lamp_glass"], name
        assert all(on.parts[m] is p for m, p in pc.parts.items() if m != "lamp_glass"), name
        assert home.specs[name + "_on"] == home.specs[name], name
    for name in ("brass_plate", "clock_wall"):            # wall discs turned to face the room (glTF -z)
        lo, hi = home.pieces[f"home/{name}"].bounds
        assert lo[2] < -0.01 and hi[2] <= 0.005, name
        assert abs((hi[0] - lo[0]) - (hi[1] - lo[1])) <= 0.02, name   # round, not squashed


def test_home_kit_budget(home, tmp_path):
    """The whole home kit (prompts 52 and 53) holds at most 60,000 triangles, and its parts and images
    write at most 6 MB on the kit sheet."""
    from citygen.kitsheet import kit_sheet
    assert sum(pc.triangles for pc in home.pieces.values()) <= 60_000
    kit_sheet(tmp_path, kit=home)
    assert (tmp_path / "tiles" / "sheet.glb").stat().st_size <= 6_000_000


def test_weave_images(style):
    from citygen.interior import weave
    spec = style["interiors"]["textures"]
    for name in ("klim_red", "klim_indigo", "mergoum", "zarbia", "hasira", "ticking", "painted", "sajjada", "mink"):
        a = np.asarray(weave.texture(name, 42, spec[name]), dtype=np.float64)
        assert a.shape == (256, 256, 3), name
        rows = (np.abs(a[1] - a[0]).mean() + np.abs(a[-1] - a[-2]).mean()) / 2 + 0.5   # the neighbour rows' difference
        cols = (np.abs(a[:, 1] - a[:, 0]).mean() + np.abs(a[:, -1] - a[:, -2]).mean()) / 2 + 0.5
        assert np.abs(a[0] - a[-1]).mean() < 2 * rows and np.abs(a[:, 0] - a[:, -1]).mean() < 2 * cols, name
        assert weave.texture(name, 42, spec[name]).tobytes() == weave.texture(name, 42, spec[name]).tobytes()
    for name in ("rug_floral", "spines", "goods"):      # prompt 53; book and goods rows tile across only
        a = np.asarray(weave.texture(name, 42, spec[name]), dtype=np.float64)
        assert a.shape == (256, 256, 3), name
        cols = (np.abs(a[:, 1] - a[:, 0]).mean() + np.abs(a[:, -1] - a[:, -2]).mean()) / 2 + 0.5
        assert np.abs(a[:, 0] - a[:, -1]).mean() < 2 * cols, name
        if name == "rug_floral":
            rows = (np.abs(a[1] - a[0]).mean() + np.abs(a[-1] - a[-2]).mean()) / 2 + 0.5
            assert np.abs(a[0] - a[-1]).mean() < 2 * rows, name
        assert weave.texture(name, 42, spec[name]).tobytes() == weave.texture(name, 42, spec[name]).tobytes()


@pytest.mark.slow
def test_home_kit_deterministic(tmp_path):
    import os
    import subprocess
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    for name, seed in (("a", "1"), ("b", "2")):
        subprocess.run([sys.executable, "-m", "citygen", "kit-sheet", "--home", "--out", str(tmp_path / name)], cwd=root,
                       env={**os.environ, "PYTHONHASHSEED": seed}, check=True, capture_output=True)
    for f in ("tiles/sheet.glb", "tiles/index.json", "pieces.txt"):
        assert (tmp_path / "a" / f).read_bytes() == (tmp_path / "b" / f).read_bytes(), f
