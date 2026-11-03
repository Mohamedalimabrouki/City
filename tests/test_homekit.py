"""The home kit of interiors (prompt 52, SPEC 6d): traditional pieces and their woven images."""
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


def test_home_pieces_traditional(home, style):
    from citygen.interior import kit_old
    from citygen.kit import make_kit
    palette = {**style["palette"], **style["interiors"]["palette"]}
    city = set(make_kit(42, load_config(), style).pieces)
    for base, (cat, anchor, size, tris, extra) in kit_old.TABLE.items():
        for suffix in kit_old.VARIANTS.get(base, (None,)):
            name = f"home/{base}" if suffix is None else f"home/{base}_{suffix}"
            pc, spec = home.pieces[name], home.specs[name]
            assert (pc.category, pc.anchor, pc.source) == (cat, anchor, "procedural"), name
            assert pc.triangles <= tris == spec.tris, (name, pc.triangles)
            lo, hi = pc.bounds                                    # glTF axes: y up, -z the front
            extent = np.array([hi[0] - lo[0], hi[2] - lo[2], hi[1] - lo[1]])
            want = kit_old.SIZES.get(name[5:], size)
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
    assert len(home.pieces) == len(kit_old.names())


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
