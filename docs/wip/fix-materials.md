# fix-materials (review of 3 November, finding 0)

Branch `wip/fix-materials`, from 3036039. Helper notes for the lead, 3 November 2026.

## The collisions, measured

Quick build (seed 42), a `pick:dar` interior: the city kit (`make_kit`, `[palette]` plus kit manifests)
has 208 materials, the home kit 276 (`[palette]` + `[interiors.palette]`), `[interiors.palette]` 76.
203 names are shared; 200 have equal values (they are the `[palette]` the home kit copies). Three differ,
all three because `[interiors.palette]` redefined a `[palette]` name (no manifest-only name collides):

| name | city (`[palette]`) | interior (`[interiors.palette]`) | city pieces using it | home kit pieces using it |
|---|---|---|---|---|
| `copper` | #B8733A r0.35 m0.8 | #B5653A r0.4 m0.5 | copper_display, sabil, shop_front_copper, shop_front_perfume, string_lantern | home/ibrik |
| `net_green` | #3E6B57 r0.95 | #3E7A55 r0.9 | boat_rowing, boat_trawler | home/net_pile |
| `terracotta` | #B8643C (no roughness) | #B5653F r0.9 | pot_plant, pot_plant_b, shop_front_pots | home/chicha, kanoun, khabia_glazed, khabia_large, khabia_small, pots_stack, tabouna |

So inside every interior those city pieces took the furniture's colours. The review's order-only fix
was not enough: `**cfg.get("palette", {})` came last and holds the same three names, and with the city
winning the ibrik would have taken the city's copper (metallic 0.8, which the palette note says reads
black in the viewer).

## The fix

- `styles/maghreb.toml` `[interiors.palette]`: `copper` -> `copper_ware`, `terracotta` -> `clay_red`
  (next to `clay_pale`), `net_green` -> `twine_green`; numbers unchanged, so the furniture looks the same.
- `citygen/interior/kit_old.py` (6 + 1 + 1 uses) and `kit_new.py` (1 use, the chicha) use the new names.
  `kit_new.TRADES` keeps `"copper"`: it is a shop trade, not a material.
- `citygen/interior/export.py`: new `interior_materials(city, home)` = `{**home, **city}` (the city kit
  wins a shared name; `home` already holds `[interiors.palette]`, so the third merge was dropped).
- `docs/SPEC.md` 6d: the home kit table and palette list use the new names, plus one sentence on the rule.

## Tests

- New `tests/test_homekit.py::test_interior_keeps_both_kits_materials` (real city kit and home kit):
  no `[interiors.palette]` name is a city material; every city material and every `[interiors.palette]`
  entry keeps its value in the merge; every home piece's material keeps the home kit's value. On the old
  code it fails (ImportError; with the old merge order shimmed in, the shared-names assert fails).
  The `city` fixture now reuses a new `city_kit` fixture (no second `make_kit`).
- `pytest -q`: 164 passed, 10 deselected (92.9 s, machine loaded; the 3 warnings are in
  test_citygen's newel and court tests, untouched here); `pytest -q -m slow -k furnish`: 3 passed.
- `build --quick` then `fingerprint compare before --allow ""`: 282 parts, 0 changed (the build never
  reads `[interiors.palette]`).
- Interiors written from the quick build (to $TMPDIR, never output/): `pick:dar` and `pick:compact` GLBs
  hold `clay_red` #B5653F r0.9 (the furniture unchanged); dar, compact, colonial, slab and small show no
  colliding city piece. Building 32 (Goumosbane, a house with a pots shop: `pot_plant`,
  `shop_front_pots` in its placements) shows the bug and the fix in its GLB: old code `terracotta`
  #B5653F (the furniture's), new code `terracotta` #B8643C (the city's, as in its tile) and the jars
  `clay_red` #B5653F. Roughness 0.9 in all (the city entry has none; the GLB default is 0.9).
  Scripts: scratchpad `collide.py` (the table above), `glbmats.py` (GLB values), `findcity.py`.

## Next step

Lead: review the diff and merge `wip/fix-materials`. Nothing else is open for this finding; WORKLOG
and HANDOFF entries are left to the lead (lesson: an `[interiors.palette]` name must be new, the test
now says so).
