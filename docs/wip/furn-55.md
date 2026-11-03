# Prompt 55 H2d (light, textiles, clutter), first slice (helper; worktree /tmp/claude-501/furn-55, branch wip/furn-55)
Built on wip/furnish-m e871984 (prompt 54 round 3, not merged yet). Started 20:33 UTC, saved 20:50 UTC (weekly reset).

## Built (step 1 and 2 in part)
- `citygen/interior/kit_life.py` (new, same pattern as `kit_new`: TABLE, VARIANTS, SIZES, MAKERS, names(), pieces()):
  the 7 lights `fanous`, `lantern_table`, `ceiling_lamp`, `chandelier`, `neon`, `bulb_bare`, `lamp_bedside`,
  and 5 plants and clutter `pot_geranium`, `pot_basil`, `plates_stack`, `fruit_bowl`, `oil_bidon`, sizes and
  tris as the SPEC 6d table. Ceiling pieces hang from z 0 down to z -H (spec `z0` = -H, as the test's ceiling
  rule `hi <= 0.005` wants). Helpers `_ball` (fruit, flower head) and `_pot` (terracotta pot, 32 tris).
- `homekit.MODULES` gains `kit_life`; the `_on` twins were already made by `home_kit` (category `light`):
  12 + 7 twins new in the home kit.
- `styles/maghreb.toml` `[interiors.palette]`: `lamp_glass` #F3E6C8 and `lamp_glow` (exact copy), `voile`
  (alpha 0.5, double sided), `iron_white`, `glaze_blue`, `leaf_green`, `photo_sepia`, `bread`, `plastic_yellow`
  (first values for Ali to judge on the kit sheet).
- `tests/test_homekit.py`: `test_home_pieces_life` (the life table as `_check_table`; every light has its `_on`
  twin, the same parts with `lamp_glass` as `lamp_glow`, same spec; `lamp_glow == lamp_glass`);
  `test_home_pieces_traditional` counts kit_life names plus the twins.

## Checks
- `pytest -q tests/test_homekit.py`: 5 passed (3.4 s). Full `pytest -q`: 164 passed, 11 deselected (166 s).
- `build --quick` 13.9 s; fingerprint `compare life55 --allow ""` against the base commit: 282 parts, 0 changed
  (the home kit is never in the build).
- Not looked at yet: the new pieces on the kit sheet (`python -m citygen kit-sheet --home`).

## Exact next steps
1. Rest of the SPEC 6d table in `kit_life.TABLE`/`MAKERS` (test_home_pieces_life walks the table, so each
   new row is tested at once): `frame_verse`, `khomsa`, `brass_plate`, `photo_frame`, `clock_wall` (wall
   discs and plates facing +y: use `kit_old.SWAP_YZ` / `_moved` as kit_old's wall round pieces do),
   `mergoum_wall` (UV quad like `kit_old._rug`, `mergoum`), `curtain` (anchor `window`, stretch [0.8, 3.5],
   H = head + 0.15, `fabric_*` / `voile`: `homekit._spec` and the test need the `window` anchor),
   `birdcage`, `pot_jasmine`, `vase_flowers`, `slippers`, `shoes`, `books_stack` (`spines`, UVs as
   `kit_new._row`), `bread_basket` (`hasira`, `bread`), `water_pack`, `schoolbag`, `blanket_folded` (`mink`),
   `laundry_line` (stretch [2.0, 5.0]), `broom`, `pots_hanging`. Budget: test_home_kit_budget (60,000 tris).
2. `weave.py`: maker `verse` (abstract gold strokes on deep green, never real or imitated script, SPEC 6d
   rule 7), `[interiors.textures] verse`, palette `verse` (texture, texture_size [0.55, 0.40]); add it to
   `test_weave_images`.
3. Style recipes: light, curtain, wall textile, plant and clutter slots in
   `[[interiors.furnish.rooms.<function>]]`, densities as SPEC 6d "Density" (who gets what: the table's last
   column). Ceiling pieces need a `ceiling` place in `furnish.py` (piece z = room z + height - H).
4. `furnish.py`: `window` place (curtains over each window and balcony door of modern rooms), the night rule
   (a lamp's `_on` twin when its room is lit, or blind with a lit room in its unit; lit windows: HANDOFF
   prompt 21), `index.json` `interior.lamps` (only `_on` lamps); test `test_lamps_follow_windows`.
5. Viewer `LIT_AT_NIGHT` + `lamp_glow`, up to 8 warm point lights (4 m, no shadows) from `interior.lamps`.
6. SPEC 6d built note, HANDOFF, the two looks and `make_blend.py` as the prompt says.
