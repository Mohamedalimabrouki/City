"""Styles per region (prompt 94): a world file gives a settlement or a kind its own style pack."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from citygen.config import load_config, load_style
from citygen.styles import assigned_style, namespaced, regional_names, regional_style, style_label

TINY = str(Path(__file__).with_name("data") / "tiny_style.toml")
TWO = Path(__file__).with_name("data") / "two_styles.toml"


def _cfg(styles: dict) -> dict:
    return {"world": {"style": "maghreb"}, "styles": styles}


def test_a_name_or_id_beats_a_kind_and_a_kind_beats_the_country_style():
    cfg = _cfg({"settlements": {"Sidi Amor": "steampunk", "3": "fantasy"}, "kinds": {"village": "rural"}})
    sidi = SimpleNamespace(id=7, name="Sidi Amor", kind="village")
    third = SimpleNamespace(id=3, name="Megine", kind="village")
    other = SimpleNamespace(id=5, name="Douar", kind="village")
    town = SimpleNamespace(id=6, name="Tala", kind="town")
    assert [assigned_style(cfg, s) for s in (sidi, third, other, town)] == ["steampunk", "fantasy", "rural", "maghreb"]
    assert assigned_style(_cfg({"settlements": {"sidi amor ": "steampunk"}}), sidi) == "steampunk"   # names ignore case
    assert regional_names(cfg) == ["fantasy", "rural", "steampunk"]
    assert regional_names({"world": {"style": "maghreb"}}) == []
    assert style_label(TINY) == "tiny_style" and style_label("steampunk") == "steampunk"


def test_a_regional_pack_lists_only_what_differs_and_its_kit_is_namespaced():
    country = load_style("maghreb")
    tiny = regional_style(country, TINY)
    assert tiny["palette"]["lime_white"]["color"] == "#8C5A3C"
    assert tiny["palette"]["roof_white"]["texture"] == country["palette"]["roof_white"]["texture"]   # merged, not replaced
    assert tiny["district"] == country["district"] and country["palette"]["lime_white"]["color"] != "#8C5A3C"
    piece = SimpleNamespace(name="door_wood", parts={"wood_dark": {}, "iron": {}})
    kit = SimpleNamespace(pieces={"door_wood": piece}, materials={"wood_dark": {}, "iron": {}}, panes={"door_wood": 1})
    ns = namespaced(kit, "tiny_style")
    assert list(ns.pieces) == ["tiny_style/door_wood"] and ns.pieces["tiny_style/door_wood"].name == "tiny_style/door_wood"
    assert set(ns.pieces["tiny_style/door_wood"].parts) == {"tiny_style/wood_dark", "tiny_style/iron"}
    assert set(ns.materials) == {"tiny_style/wood_dark", "tiny_style/iron"} and list(ns.panes) == ["tiny_style/door_wood"]
    assert piece.name == "door_wood" and set(piece.parts) == {"wood_dark", "iron"}   # the country's kit is untouched


@pytest.mark.slow  # two villages planned and two tiles built, about 30 s; run with: python -m pytest -q -m slow
def test_two_villages_in_two_styles_share_tiles_without_name_collisions():
    from citygen.city import plan_city
    from citygen.mesh.tile import TileContext, build_tile, instance_groups
    from citygen.world import generate_world
    world = generate_world(load_config(TWO, quick=True))
    tiny, plain = world.settlements[8], world.settlements[9]
    assert world.to_json()["styles"] == {"8": "tests/data/tiny_style.toml"}
    plans = [plan_city(world, tiny), plan_city(world, plain)]
    tc = TileContext(world, plans)
    assert tc.views[0].prefix == "tiny_style" and tc.views[1] is None
    assert tc.materials["tiny_style/lime_white"]["color"] == "#8C5A3C"
    assert tc.materials["lime_white"] == world.style["palette"]["lime_white"]
    for s, ours in ((tiny, True), (plain, False)):
        i, j = int(s.x // tc.size), int(s.y // tc.size)
        mb, placements = build_tile(tc, i, j)
        materials = set(mb._parts)
        assert materials <= set(tc.materials), materials - set(tc.materials)
        assert any(m.startswith("tiny_style/") for m in materials) == ours
        pieces = {p.piece for p in placements}
        assert pieces and all(p in tc.kit.pieces for p in pieces)
        assert any(p.startswith("tiny_style/") for p in pieces) == ours
        assert all(p.startswith("tiny_style/") for p in pieces) == ours
        for g in instance_groups(tc, placements, i * tc.size, j * tc.size):
            assert set(g["parts"]) <= set(tc.materials)
