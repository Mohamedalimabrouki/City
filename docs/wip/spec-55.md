# spec-55: prompt 55 checklist (3 November, 20:57 UTC)

Branch base: 0996596 (WIP furn-55). Sources: SPEC 6d table (light, textiles, plants, clutter), `docs/prompts/05-interiors.md` section 55, `citygen/interior/kit_life.py`.

## Pieces of the SPEC 6d table (32 rows)

Done in `citygen/interior/kit_life.py` (18):
- [x] fanous, lantern_table, ceiling_lamp, chandelier, neon, bulb_bare, lamp_bedside (all 7 lights)
- [x] khomsa, photo_frame
- [x] pot_jasmine, pot_geranium, pot_basil, vase_flowers
- [x] shoes, plates_stack, fruit_bowl, oil_bidon, schoolbag

Left (14; none of them is in kit_old.py or kit_new.py either):
- [ ] frame_verse (needs the `verse` texture, step 1)
- [ ] brass_plate
- [ ] clock_wall
- [ ] mergoum_wall
- [ ] curtain (needs the `window` place, step 3)
- [ ] birdcage
- [ ] slippers
- [ ] books_stack
- [ ] bread_basket
- [ ] water_pack
- [ ] blanket_folded
- [ ] laundry_line
- [ ] broom
- [ ] pots_hanging

## Steps of prompt 55

1. Pieces: 18 of 32 done (list above). `_on` twins done (`citygen/interior/homekit.py:72-74`, `lamp_glass` -> `lamp_glow`). Left: `weave.py` adds `verse` (no `verse` texture anywhere in citygen).
2. Style: `lamp_glow` palette entry done (`styles/maghreb.toml:1933-1935`). Left: the other prompt-55 `[interiors.palette]` entries (check each against SPEC 6d) and every recipe slot for lights, curtains, wall textiles, plants and clutter in `[[interiors.furnish.rooms.<function>]]` (no life piece name appears in `styles/maghreb.toml` yet).
3. Left: `furnish.py` `window` place for curtains, the night rule (`_on` twin when its room is lit, or a blind room in a lit unit), and `index.json` `interior.lamps` (no `lamps` in furnish.py or export.py).
4. Left: viewer `LIT_AT_NIGHT` gains `lamp_glow` (not in `tools/viewer/index.html`), and up to 8 warm point lights (4 m range, no shadows) from `interior.lamps`.
5. Left: SPEC 6d (built, rules settled) and HANDOFF.

## Tests
- [x] `test_home_pieces_life` exists (`tests/test_homekit.py:65`); it will need the 14 left pieces once built.
- [ ] `test_lamps_follow_windows` (not written yet; needs step 3).
- [ ] Run `test_furnish_no_overlap`, `test_furnish_density`, `test_furnish_budget` after the new slots.

## Check and finish (all left)
- [ ] Fingerprint `--allow ""`.
- [ ] Look: `before_after.py --view interior --interior pick:dar:2 --query light=night --out output/checks/55.png`, then the slab overview `--query cut=2 --query light=night --out output/checks/55-slab.png`.
- [ ] `tools/make_blend.py <the dar's interior folder>`; name the .blend.
- [ ] Tick H2 in ROADMAP section H; WORKLOG entry; commit and push.

## Suggested order for the next session
Step 1 rest (14 pieces + `verse`), then step 2 slots, then step 3 (window place, night rule, lamps), then the new test, then step 4 viewer, then step 5 docs and the checks.

Not checked (time): whether each of the 18 built pieces matches its SPEC size and materials exactly.
