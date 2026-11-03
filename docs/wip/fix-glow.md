# fix-glow (from wip/furn-55)

Done:
- styles/maghreb.toml [interiors.palette]: `lamp_glow` is now `lamp_glass` plus `emissive = "#FFC77A"` (warm). The glTF export writes it as emissiveFactor (citygen/mesh/gltf.py:68), so Blender and any glTF viewer see the `_on` lamps glow.
- tools/viewer/index.html: nothing new was needed to light it, since the viewer marks every material with a non-black emissive as glowing (line 515), turns it up at night (NIGHT.glow) and puts real lights on the nearest ones, like `lantern_glow`. I only added `lamp_glow` to CLEAR_AT_NIGHT (kept out of the night fog, like `lantern_glow`) and a comment.
- tests/test_homekit.py test_home_pieces_life: `lamp_glow` differs from `lamp_glass`, only by its emissive; the glTF material of `lamp_glow` has an emissiveFactor and that of `lamp_glass` has none.
- `pytest -q -k "kit or home or export"`: 10 passed.

Note for the lead: the brief said "emissive in the palette, as glass_lit is", but `glass_lit` is not emissive in the palette (tests/test_citygen.py:984 checks it is glass_dark's exact copy); the viewer lights it only at night through LIT_AT_NIGHT. So a `_on` lamp now glows by day too (in glTF and Blender). If the lead wants "same as lamp_glass by day, lit only at night" instead, revert the palette line and add `lamp_glow: [0xffc77a, 2]` to LIT_AT_NIGHT (but then line 550 gives those lamps no real point lights).

Left: full pytest and build --quick not run; the interior glTF path was checked only through gltf._material, not through a written scene file.
