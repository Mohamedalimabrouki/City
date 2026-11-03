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
def city_kit(style):
    from citygen.kit import make_kit
    return make_kit(42, load_config(), style)


@pytest.fixture(scope="module")
def city(city_kit):
    return set(city_kit.pieces)


def test_interior_keeps_both_kits_materials(style, home, city_kit):
    """Review of 3 November, finding 0: the interior GLB's materials (`export.interior_materials`) keep every
    city kit material as its tiles draw it (a shop front, a boat, a pot plant seen from inside) and every
    `[interiors.palette]` one as the shell and the furniture want it; no name is both (the home kit's
    `copper`, `terracotta` and `net_green` once recoloured the city's)."""
    from citygen.interior.export import interior_materials
    got = interior_materials(city_kit.materials, home.materials)
    inner = style["interiors"]["palette"]
    assert not set(inner) & set(city_kit.materials)
    assert all(got[m] == spec for m, spec in city_kit.materials.items())
    assert all(got[m] == spec for m, spec in inner.items())
    used = {m for pc in home.pieces.values() for m in pc.parts}
    assert all(got[m] == home.materials[m] for m in used)


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
    assert len(home.pieces) == len(kit_old.names()) + len(kit_new.names())
    assert not set(kit_old.names()) & set(kit_new.names())


def test_home_pieces_modern(home, style, city):
    from citygen.interior import kit_new
    _check_table(home, style, city, kit_new)


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
    for name in ("klim_red", "klim_indigo", "mergoum", "zarbia", "hasira", "ticking", "painted", "sajjada", "mink",
                 "fleece", "net"):
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
