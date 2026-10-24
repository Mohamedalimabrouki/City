# Work log

Newest first. One entry per prompt, written by the session that did the work. Checkpoints and
the final review read this first, so keep entries short and exact. Questions for Ali go here
too, so nothing is lost when a session ends.

Entry format:

```
## <date> - Prompt <N> <ID> <title>
- Commit: <hash> | Model: <model>, <effort>
- Changed: <files>
- Checks: tests (count), build time, fingerprint (parts changed), budgets when relevant
- Look: <picture path or view> - what to see
- Doubts and questions for Ali: <none, or the question>
```

## 2026-10-24 - Prompt 29 P2 People in the streets
- Commit: (see git log) | Model: Opus 5.5, medium (playbook: Sonnet, medium)
- Changed: `citygen/city/crowd.py` (new: candidates per place, halo, thinning, figure cast, checks),
  `citygen/city/dressing.py` (`Dresser.crowd()`; door benches on the street's level, `tounes/bench_sbs` backs
  onto the wall), `citygen/mesh/tile.py` (people at the end of each city), `citygen/mesh/builder.py`
  (`MeshBuilder.sizes`), `styles/maghreb.toml` (`[people]` with souk, shop, lane, sidewalk, promenade,
  landmark, square, stair, seats and outfits tables), tests (1 new), `docs/SPEC.md`, `docs/HANDOFF.md`.
- Quick capital (9 tiles): 1,857 people: 523 souk walkers, 128 shop browsers, 157 seated (106 at cafes, 37
  on doukkanas, 14 on benches), 855 on sidewalks, 11 on the promenade, 32 at the great mosque, 10 at gates,
  5 at the kiosk and fountain, 128 in medina lanes, 8 on estate stair paths; 669 walk in pairs or families
  (95 children). Outfits: 519 shirt, 417 hijab, 366 jebba, 258 safsari, 202 dress, 53 boys, 42 girls.
  Quick village 4: 23 people (16 jebba, 6 safsari, 1 dress; 5 on door benches).
- Checks: tests 84 passed (22.4 s; the new ones 0.5 s and 0.06 s); `build --quick` 10.6 s (10.0 s at density 0);
  fingerprint: the 9 tiles and `tiles/index` changed (allowed `tiles/*`); density 0 gives 0 changed parts.
  Worst quick tile bytes +7.7% (`tile_13_22`), full capital +8.3% (`tile_66_102`), budget 10%; drawn
  triangles worst +23.0% quick (`tile_13_23`), +18.1% on the 25 central full tiles, budget 30%. Full
  capital 48.0 -> 50.4 s (CPU 207 -> 224 s).
- Look: `output/checks/29.png` (souk: walkers both ways, browsers facing the goods, nobody floating) and
  `output/checks/29-cafe.png` (arcade cafe at 10 m: two men in jebba seated on the chairs facing each other,
  feet under the table, walkers under the arcade). Blender: `output/bodjantouna-42/goumosbane.blend`.
- Doubts and questions for Ali: none. For the lead: (1) bytes are the tight budget: each figure costs about
  14 KB per tile, so light tiles show only their 3-6 most frequent figures (`bytes_share`); (2) door benches
  moved up to the street's level (they stood about 0.2 m below souk ribbons) and `tounes/bench_sbs` out of
  the wall; (3) lead review: fixed the crash in `Squares._sabil_fits` on a settlement without streets
  (quick village 5): squares queries go through `_streets`/`_buildings` (nothing without streets or
  buildings), no street means no sabil, the crowd's mosque outline needs buildings; a new test dresses
  village 5 (0.06 s). Prompt 39 now notes that quantized meshes should let light tiles show more figures.

## 2026-10-24 - Prompt 28 P1 People: low-poly figures
- Commit: (see git log) | Model: Opus 5.5, high (playbook: Sonnet, high)
- Changed: `citygen/mesh/people.py` (new: skeleton, poses, outfits), `citygen/kit.py` (person pieces),
  `styles/maghreb.toml` (`[dressing.people]` with 26 pieces; palette: 17 muted `cloth_*`, 4 skin, 3 hair,
  shoes, balgha, basket, bag, bread), `tests/test_citygen.py` (1 test), docs.
- Pieces (triangles): jebba stand/walk/walk_b 329, sit 369, carry 389; shirt stand/walk 328, walk_b 352,
  sit 304, sit_b 328, carry 356; safsari stand/walk 227, sit 263, carry 319; dress stand/walk/sit 360;
  hijab stand/walk 319, sit 343, carry 347; boy 352; girl 368. Standing adults 1.60-1.79 m to the top (a
  chechia included; walkers 4-7 cm lower mid-stride), children 1.17-1.27 m.
- Seats found in the kit: `bench_iron` 0.45, `doukkana` 0.45, `cafe_set` chairs 0.46, `tounes/bench_sbs`
  0.48. Sitters touch 0.45 exactly; prompt 29 lifts them by seat - 0.45 (1 cm, 3 cm). Checked side and
  three-quarter renders on all three seats: on the seat, back clear of the backrest, feet under the
  cafe table.
- Checks: tests 82 passed (21.4 s, the new one about 0.3 s); `build --quick` 9.9 s; fingerprint against
  `before`: 26 parts changed, all new `kit/person_*`; no tile changed (no Blender refresh needed).
- Look: `output/checks/28.png` (kit sheet from about 20 m) and `output/checks/28-eye.png` (street eye
  height, 5-20 m): jebba and chechia, safsari, headscarves, children read as people; strides visible.
- Doubts and questions for Ali: none. The seated shins are 2-6 cm longer than standing ones so level
  thighs reach the ground (see HANDOFF).

## 2026-10-24 - Prompt 27 CP3 Checkpoint: facades and street life
- Commits: "CP3 fixes: paint and cars agree, cut-corner arcade zones, lamps, lit keys" and "CP3
  speed: tiles 26% faster, tests 31 s -> 20 s, output byte-identical" (see git log) | Model: Opus
  5.5, medium (lead), with an independent Opus reviewer that read only the committed history
- Reviewed prompts 17-26 with 20.1 and 20.2 (17-19 DeepSeek; 20-26 Opus helpers, each reviewed by
  the lead before its commit): every "Done when" met. Documented, kept: 52% of arcade bays flex to
  3.2-4.4 m (22); the taxi rank stands in a side street, the quick boulevard is only 76 m (25);
  colonial arterials keep their arcades as shade instead of street trees (24).
- Found and fixed (independent review, verified): paint gave empty parking rows to sides without
  parking districts; arcade zones probed cut-corner faces differently from `Dresser.walls`, so a
  side-street lamp could stand under a wrap bay; lit flats keyed a side on a float yaw (a south
  wall could split a flat); lamps of a grid street under the boulevard stood on the promenade, one
  1.3 m from the fountain (`lamp_spot` now drops lamps inside a wider street); fountain clear of
  crowns; numbers moved to `[dressing.squares]` and `[dressing.parking]`; one shared stair-path
  function; the terrain-corner cache cleared per tile; three tests made to check the real result.
- Speed (identical output, fingerprints of the quick and the full capital 0 changed): quick tiles
  4.81 -> 3.58 s in one process, full capital about 54 -> 48 s back to back, planner 17.3 -> 16.3 s,
  `pytest -q` 30.7 -> 20.4 s, `build --quick` 11.4 -> 9.9 s.
- Checks: tests 81 passed (20.4 s), 2 slow passed; `build --quick` 9.9 s; stats 296,713 triangles,
  4,046,565 drawn, 27,255 dressing pieces, 18.4 MB in 9 tiles. Against `cp2`: 98 parts changed (81
  new kit pieces, plan buildings, streets, trees and households, every tile; densest quick tile
  5.81 -> 7.40 MB). Saved `fp-cp3`.
- Textures: 14 shared images, about 0.7 MB (limit 2 MB); sharp at street level (anisotropy 8); no
  visible repeat from 135 m (`20-air.png`). Phone page rebuilt from the quick build (26 MB, biggest
  file 9.9 MB) and served locally: 9/9 tiles with textures, no console errors. Blender file
  refreshed by every prompt (`tools/make_blend.py`).
- Doors and windows: every dwelling has a door (tests); slabs have windows on every floor; no
  enclosed home on the quick or the full capital (6,641 impasses on the full capital).
- Street life: boulevard, souk and colonial streets walked in the GPU viewer: no car in a tree or
  on a crossing, no lamp or tree in an arcade after the fixes, benches and kiosk clear. The street
  view renders in 4.6 ms per frame (High, golden hour).
- Look: `output/checks/cp3-street.png` (difference 0.24: the two promenade lamps are gone) and
  `output/checks/cp3-souk.png` (0.00). Blender: `output/bodjantouna-42/goumosbane.blend`.
- Doubts and questions for Ali: none. Tile weight is the open budget (densest quick tile 7.4 MB,
  three suburb tiles just over 3 MB): prompts 39-41 handle it.

## 2026-10-24 - Prompt 26 H3b Benches, kiosks and fountains
- Commit: (see git log) | Model: Opus 5.5, medium (playbook: Sonnet, medium)
- Changed: `citygen/mesh/furniture.py` (new: `bench_iron` 180 triangles, `kiosk` 232 with a lit twin,
  `fountain_colonial` about 740, `sabil` 208), `citygen/city/squares.py` (new: islands, fountain, kiosks,
  benches, sabils, obstacle checks), `citygen/city/dressing.py` (`squares()`, `tree_spots` leaves out the
  trees a fountain replaces, door bench role `door_bench`), `citygen/kit.py` (furniture pieces, `kiosk`
  in `LIT_CATEGORIES`), `citygen/mesh/tile.py`, `styles/maghreb.toml` (palette `water_pool`, `marble`,
  `faience_white`, `kiosk_green`, `kiosk_trim`; roles `bench`, `door_bench`; `[dressing.squares]`,
  `[dressing.furniture]`), `tools/viewer/index.html` (sea test skips instanced meshes and `water_pool`),
  `tools/blender_beauty.py` (`shade_pool`), tests (2 new), `docs/SPEC.md`, `docs/HANDOFF.md`, `docs/ROADMAP.md`
- Checks: tests 81 passed (30.6 s; the 2 new ones about 0.1 s on the shared fixtures); `build --quick`
  11.3 s; fingerprint 8 changed, all allowed: `tiles/index`, `tile_13_23` (+1.6% bytes, +1.3% triangles),
  `tile_14_23` (+0.8%), new `kit/bench_iron`, `kit/kiosk`, `kit/kiosk_lit` (the kiosk's night twin, prompt 21
  rule), `kit/fountain_colonial`, `kit/sabil`; full capital 52.4 -> 53.7 s (CPU 234 -> 242 s). Quick capital:
  1 fountain, 1 kiosk (lit), 2 benches, 4 sabils; full capital: 1 fountain, 2 kiosks, 10 benches, 4 sabils.
- Look: `output/checks/26.png` (street view: an iron bench on the promenade under the trees, the green
  kiosk at the far end of the island); `output/checks/26-fountain.png` (the colonial fountain at the ring
  road head of the promenade, quick (6863.7, 12179.4), full (33428.6, 54746.9); the gate sabil shows on a
  tower in the background). The great mosque's sabil is on its south wall facing the souk across the open
  margin: quick (7019.6, 12023.4), full (33378.7, 54244.6). Blender: `output/bodjantouna-42/goumosbane.blend`.
- Doubts and questions for Ali: none. For CP3: a grid street lying under the boulevard puts its lamps on
  the promenade (one stands 1.3 m from the fountain), older than this prompt.

## 2026-10-24 - Prompt 25 H3a Parked cars and taxis
- Commit: (see git log) | Model: Opus 5.5, medium (playbook: Sonnet, medium)
- Changed: `citygen/mesh/vehicles.py` (new: hatchback, sedan, van, louage, taxi; 152-184 triangles,
  4 colors each sharing their arrays), `citygen/city/parking.py` (new: `parked_sides` rule, per-side
  sidewalk widths, `Parking` rows and taxi rank), `citygen/city/dressing.py` (`street_props` adds the
  cars; `lamp_spot`, `front_of`, `door_spots`, `fronts`; `Placement.tilt`; `CAFES`),
  `citygen/city/paint.py` (edge line on the lane side of a parking row, sidewalks measured per side,
  carriageway cuts every sidewalk on the street, crossings tagged), `citygen/city/model.py`
  (`Paint.kind`, `Walk` comment), `citygen/city/__init__.py`, `citygen/kit.py`, `citygen/mesh/tile.py`
  (instance rotation with tilt), `styles/maghreb.toml` (car palette, `[dressing.vehicles]`,
  `[dressing.parking]`), tests (3 new), `docs/SPEC.md`, `docs/HANDOFF.md`, `docs/ROADMAP.md`
- Checks: tests 79 passed (29.5 s; the 3 new ones 0.5 s); `build --quick` 11.2 s (HEAD 10.6 s);
  fingerprint 29 changed, all allowed: `tiles/*` and the 20 new `kit/car_*`; worst quick tile bytes
  +8.8% (`tile_12_22`, budget 10%), drawn triangles +7.1% worst (`tile_13_22`, budget 20%); full capital
  47.4 -> 51.8 s back to back (CPU 204 -> 228 s), worst full tile +8.5% (both before the lead's
  boulevard fix). Quick capital: 1,525 cars (652 hatchbacks, 533 sedans, 193 vans, 125 taxis, 22
  louages), 221 streets + 9 arterials with one row, 3 arterials + the boulevard with two, a rank of 5
  taxis. Full capital (before the boulevard fix): 13,664 cars (907 taxis, 201 louages).
- Lead review (boulevard): the quick boulevard is 76 m between the ring road and the corniche with a
  cross street in the middle; its outer curbs (2 x 76 m, about 30 car slots) lost, by rule in turn,
  59 / 50.5 m to junctions, 7.5 / 6 m to zebras, 13 / 12 m to palms, 0 / 2.5 m to a lamp, nothing to
  cafe fronts, doors or paths: 3 cars. Too strict: grid street 162 runs along inside the boulevard but
  pokes out past its end, so it counted as a junction (now `lying_on` also skips a street running
  8 m or more inside it within 15 degrees); a sample of margin either side of every obstacle (now each
  car is checked exactly against the zones); empty stretches now by kind (boulevard 6%). Trunks are
  kept 1 m from the bark (`tree_clear` 1.0 + `tree_trunk` 0.3). Now 17 m free per side, 6 cars, two
  between the palms in the street view. The rank needs about 20 m between two palms, so it stays in
  the side street by the boulevard's busiest junction.
- Look: `output/checks/25.png` (street view: the boulevard's edge line moved out to the parking row,
  two cars parked between the palms by the arcade, one more past the crossing), `output/checks/25-cars.png` (a colonial street parked on one side with
  gaps, the taxi rank by the boulevard junction); Blender: `output/bodjantouna-42/goumosbane.blend`
- Doubts and questions for Ali: the quick capital's boulevard is only 76 m long and mostly junction,
  so the rank (and on the full capital too) stands in a colonial side street next to the boulevard's
  busiest junction, as many Tunis ranks do. The paint fix (sidewalks measured per side) moves edge
  lines on many arterials and on the boulevard, where they used to lie hidden under the sidewalks.

## 2026-10-24 - Prompt 24 A7 More greenery
- Commit: (see git log) | Model: Opus 5.5, medium (playbook: Sonnet, medium)
- Changed: `citygen/city/greenery.py` (new: arterial tree pits, courtyard trees, villa fruit trees,
  appended last), `citygen/city/__init__.py` (greenery after the paint, `stats["greenery"]`),
  `citygen/city/dressing.py` (`arcade_zones`, `band_push`, `tree_reach`, `stair_columns` as module
  functions; `Dresser.garden` and hedges), `citygen/city/openings.py` (`villa_lots`),
  `citygen/city/ground.py` (`terrain_cells`), `citygen/mesh/tile.py` (`garden_meshes`, gardens and
  hedges per villa), `citygen/mesh/trees.py` (citrus kind, oranges), `citygen/mesh/props.py` (`hedge`
  piece, citrus color in the light tree), `citygen/kit.py`, `citygen/export/maps.py` (garden lots,
  orange citrus dots), `tools/blender_beauty.py` (garden ground), `styles/maghreb.toml` (`[greenery]`,
  `[dressing.trees.citrus]`, `[dressing.hedge]`, palette `leaf_citrus*`, `fruit_orange`,
  `leaf_hedge`, `garden`, role `tree_citrus`), tests (3 new, 2 adjusted: the massing test also switches
  greenery off and checks the old trees as a prefix; the tree test counts citrus fruit apart),
  `docs/SPEC.md`, `docs/HANDOFF.md`, `docs/ROADMAP.md`
- Checks: tests 76 passed (28.4 s, was 27.6 s); `build --quick` 10.5-10.7 s (HEAD 10.7 s back to back);
  fingerprint 13 changed, all allowed: `plan/goumosbane/trees` (7,890 -> 8,017), `stats`, `gazetteer`
  (tree count), `maps/goumosbane.png`, `tiles/*` (worst quick tile +1.3%), new `kit/hedge`,
  `kit/tree_citrus`, `_b`, `_c`. Full capital 51.4 -> 49.0 s back to back (CPU 212 -> 207 s; 48.3 s
  after the garden trim). Suburb tiles: +31-37% with the house cut out of the garden (worst
  `tile_60_103` 2.41 -> 3.29 MB), +25-30% after the lead's trim (garden left under the house): worst
  2.41 -> 3.13 MB, three tiles just over 3 MB (3.13, 3.09, 3.06), all changed tiles together +5.8%. Quick capital: 69 arterial trees (modern), 58 courtyard trees (45 citrus,
  9 broadleaf, 4 olive). Full capital: 149 arterial, 273 courtyard (213 citrus), 2,025 villa fruit trees
  (1,640 citrus, 385 olive), 2,900 gardens (98 ha), 31,099 hedge pieces (192 km).
- Look: `output/checks/24.png` (close before/after above a modern arterial, cam 7340,11305,124 look
  7268,11350,82: a row of street trees on the modern sidewalk, stopping at the lamp and before the
  zebra junction; mean difference 2.11); `output/checks/24-gardens.png` (city 1 aerial after the hedge
  change: green villa lots outlined by dark hedges, nothing showing through the houses; the bare lots
  are lots without a villa, as before).
- Lead decisions: colonial arterials keep no new street trees (their arcades are the shade, as on real
  arcaded streets; no tree pit fits beside the pillars), modern arterials get them; the garden ground
  stays under the house (hidden) to save triangles.
- Doubts and questions for Ali: three suburb tiles are now just over the 3 MB tile budget.

## 2026-10-24 - Prompt 23 AR2 Building massing with character
- Commit: (see git log) | Model: Opus 5.5, high (playbook: Sonnet, high)
- Changed: `citygen/city/massing.py` (new: the planning step after households and souks, `masses`,
  `floors_at`, `wall_height`, `outline`, `inner_walls`, `terrace_walls`), `citygen/city/model.py`
  (`Building.setback`, `steps`, `machines`, `menzah`, `corners`; `top` with a position),
  `citygen/city/__init__.py`, `citygen/city/roofs.py` (main roof of the masses, `roof_layouts`, menzah,
  `RoofLayout.rooms`), `citygen/mesh/tile.py` (massed buildings drawn as one solid, lift rooms, corner
  domes and turrets, menzah), `citygen/mesh/builder.py` (`add_walls(only=)`), `citygen/city/dressing.py`
  (window floors per wall, terrace windows, tank stands, props on the main roof, corner probes, arcade
  bend pieces and wrap at cut corners, wall heights for climbers and spans), `citygen/city/arcades.py`
  (`hold0/hold1`), `citygen/mesh/props.py` (`arcade_bend`, `tank_stand`), `citygen/export/lore.py`
  (massing in plan.json), `styles/maghreb.toml` (`[district.*]` massing numbers, `[roofs]` menzah,
  `window_half`, `bend_tol`, `[streets] apron_*`), `citygen/city/ground.py` (paved lot corners:
  `apron_top`, `apron_cells`, `surface` there interpolates the drawn triangles), `apron_mesh` in
  `citygen/mesh/tile.py`, `add_skirt(only=)`, tests (4 new, 2 adjusted:
  arcade turns count bend pieces, the stair room test reads the main roof), `docs/SPEC.md`,
  `docs/HANDOFF.md`, `docs/ROADMAP.md`
- Checks: tests 73 passed (28.1 s; HEAD 25.2 s back to back; the 4 new tests 2.6 s); `build --quick`
  10.8 s; fingerprint 14 changed: `plan/goumosbane/buildings`, `maps/goumosbane.png`, `tiles/*`, new
  `kit/arcade_bend`, `kit/arcade_bend_round` (pier pieces for cut corners) and `kit/tank_stand`;
  households, souks, streets, trees and stats unchanged. Worst tile +6.8% (`tile_13_24`, with the paved
  corners), old-town tile +3.5%. Full capital 47.0 -> 48.3 s back to back with HEAD (planner 15.8 -> 16.3 s, CPU 193 -> 207 s). Quick capital: 78 cut
  corners (58 pan coupes, 20 rounded), 18 corner tops (8 domes, 10 turrets), 59 set-back top floors,
  183 of 276 colonial buildings moved to their block's row (+-1: 122, +-2: 48, +-3: 13), 79 of 356 slabs
  stepped (70 in two parts, 9 in three), 245 lift rooms, 149 tank stands, 20 menzahs. Full capital:
  261 cut corners, 86 tops, 262 set-backs, 151 stepped slabs, 2,900 villas of which 1,020 L-shaped.
- Look: `output/checks/23.png` (colonial blocks from about 150 m: rounded corner with a dome by the
  boulevard, turrets, set-back top floors behind their terraces, steadier rows),
  `output/checks/23-villas.png` (city 1 suburb: hip-roofed villas with flat terrace wings),
  `output/checks/23-corner.png` (building 1071: pan coupe arch between two bend piers, a bay into the
  side street, paving under it), `output/checks/23-corner-round.png` (building 972: an arcade round
  three faces with slim 22.5-degree piers). Blender:
  `output/bodjantouna-42/goumosbane.blend`.
- Doubts and questions for Ali: the rows now follow each block's median floor count (one floor up or
  down, corners taller), so most colonial heights changed (lead: keep). Lead review added the paved
  lot corners and the close corner pictures. The 45-degree corner piers are massive (about 2.9 m of
  solid front with the half pillars); they read as strong corner piers, but slimmer ones would need
  the bays to take the corner. No door or shop lands on a cut face yet (the long walls win the main
  facade); the test checks a face's threshold height instead.

## 2026-10-23 - Prompt 22 AR1 Colonial arcades and iron balconies
- Commit: (see git log) | Model: Opus 5.5, high (playbook: Sonnet, high)
- Changed: `citygen/city/arcades.py` (new: free runs, bay layout around doors on a 5 cm grid, level
  steps), `citygen/city/dressing.py` (`_colonial`, `_arcade_runs`, `_free_run`, `_side_gap`,
  `_corner_free`, `_pillar_zones`, `_arcade_pieces`, `_clear_of`, `_iron`, `_iron_window`, lamp rule
  in `_lamps`, cafe tables under arcades, `Placement.stretch`), `citygen/city/openings.py` and
  `citygen/mesh/tile.py` (stretch in boxes and instance SCALE), `citygen/mesh/props.py` (`arcade_bay`,
  `arcade_corner`, `balcony_iron`, `balcony_iron_long`), `citygen/kit.py`, `styles/maghreb.toml`
  (`[dressing.arcade]`, `[dressing.balcony_iron]`, roles), tests (1 new, 1 adjusted: new doors may stand
  inside an arcade's box, its pillars are checked by the new test), `docs/SPEC.md`, `docs/HANDOFF.md`,
  `docs/ROADMAP.md`; after the lead's review: `Dresser.tree_spots` and `citygen/mesh/tile.py` (trees
  clear the arcades), `[dressing.arcade]` `tree_*`, the test also checks tree trunks
- Checks: tests 69 passed (23.1 s; HEAD 21.5 s); `build --quick` 10.0 s (HEAD 9.5 s); fingerprint 10
  changed: `kit/arcade_bay`, `kit/arcade_corner` (the corner piece, a fourth new piece), `kit/balcony_iron`,
  `kit/balcony_iron_long` and `tiles/*`, worst tile +7.6% (`tile_12_23`). Full capital 44.1 -> 43.3 s
  (same minutes; CPU 175 -> 181 s). Quick capital: 312 bays on 95 colonial facades, 17 corner pieces,
  1,523 + 335 long iron balconies, 19 of 235 lamps on those streets moved to the curb (none left out);
  planned trees by an arcade (lead review): 10 palms moved to the curb, 2 left out (plan unchanged);
  dropped under arcades: 7 climbers, 2 cascades, 1 clothesline. Bays: 48% within 3.5-4.0 m, all within 3.2-4.4 m.
- Look: `output/checks/22.png` (street: arcades along the boulevard, lamps at the curb),
  `output/checks/22-corner.png` (corner of building 972: boulevard arcade, corner piece, one bay into
  the side street; iron balconies above). Blender: `output/bodjantouna-42/goumosbane.blend`.
- Doubts and questions for Ali: about half the wall lengths cannot be cut into 3.5-4.0 m bays, so those
  use 3.2-4.4 m (continuous arcades); `bay_relaxed` in the style narrows it if he prefers gaps.

## 2026-10-23 - Prompt 21 A9 Lit windows by household
- Commit: (see git log) | Model: Opus 5.5, medium (playbook: Sonnet, medium)
- Changed: `citygen/city/dressing.py` (`_light`, `_lit_chance`, `_sections`), `citygen/kit.py`
  (`_lit_pieces`: `_lit` twins, `_pane_lit` panes from the manifest's `glass`), `citygen/mesh/props.py`
  (`lit_pane`), `citygen/mesh/gltf.py` (a part drawn twice reuses its accessors), `kits/tounes/manifest.json`
  (`glass` rectangles of 7 windows), `styles/maghreb.toml` (`glass_lit`, `[dressing.lit]`),
  `tools/viewer/index.html` (`LIT_AT_NIGHT` lights `glass_lit`; panes at night only),
  `tools/blender_import.py`, `tools/blender_beauty.py` (`hide_night_panes`), tests (2 new, 1 adjusted:
  a door spot's piece may be drawn as its `_lit` twin), `docs/SPEC.md`, `docs/HANDOFF.md`, `docs/ROADMAP.md`
- Checks: tests 68 passed (21.5 s; HEAD 21.5 s); `build --quick` 9.5 s; fingerprint 38 changed: 29
  new `kit/*_lit` pieces and `tiles/*`, worst tile +2.0% (`tile_13_24`). Quick capital: 40% of housing
  windows lit (medina 34%, colonial 39%, modern 41%). Day street picture: difference 0.00.
- Look: `output/checks/21.png` (street at night: lit kit windows by flat), `output/checks/21-night-aerial.png`
  (lead's camera over the colonial blocks, headless: grey dots), `output/checks/21-night-viewer.jpg`
  (same camera in the GPU viewer, High: the real look). Blender: `output/bodjantouna-42/goumosbane.blend`.
- Lead review: at night `glass_lit`, `lantern_glow` and `tr_glow` stay out of the fog (`CLEAR_AT_NIGHT`
  in the viewer; fog back on by day, day difference still 0.00). In the GPU viewer (browser pane,
  same camera) lit flats read as warm orange points in clusters, many dark; 1,464 kit window panes
  visible at night, 0 by day. The headless SwiftShader snapshot draws lit window glass as grey
  dots (HEAD's glowing `glass_dark` did not show there either), so judge night glass in the real viewer.
- Doubts and questions for Ali: mashrabiya balconies stay dark (no room for a pane without flicker).

## 2026-10-23 - Prompt 20.2 AD2 Impasses to landlocked houses
- Commit: (see git log) | Model: Opus 5.5, high (playbook: Sonnet, high)
- Scope: the lead extended the prompt from medina and village blocks to residential and suburb
  blocks too (one mechanism, widths and surfaces per district kind), because the full capital had
  7,802 enclosed residential houses and addresses, entrances and interiors need every home reachable.
- Changed: `citygen/city/impasses.py` (new: landlocked test as the dresser sees facades, lot-line
  graph, lanes cut nearest lots first and branching like a tree, all blocks in lockstep rounds),
  `citygen/city/__init__.py` (after the mosques' lots, before buildings; lanes appended last; stats
  `impasses`), `citygen/city/model.py` (`Street.covered`, `Parcel.block`), `citygen/city/parcels.py`,
  `citygen/city/dressing.py` (`impasse` in `FRONT_PREF` lowest, laundry and cables, covered mouth as a
  sabat of that length, arch inside some mouths, main facade long enough for a door), `citygen/city/ground.py`
  (lift 0.18 like alleys), `citygen/mesh/tile.py` (sabat depth), `citygen/export/maps.py` (drawn like
  alleys), `styles/maghreb.toml` (`[impasse]` and per kind: medina 2.2-3.0 m paving, village 2.6-3.4 m
  earth, residential 3.5-4.0 m asphalt, suburb 3.8-4.4 m asphalt; `impasse_arch`), tests (4 new, 2
  adjusted: no quick-capital dwelling is enclosed any more; impasse surfaces come from `[impasse]`),
  `docs/SPEC.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`
- Checks: tests 66 passed (21.2 s; HEAD 19.5 s); `build --quick` 9.4 s (HEAD 9.1 s); fingerprint
  156 parts, 16 changed, all in `plan/*,tiles/*,maps/*,gazetteer`. Quick capital: streets 315 ->
  488 (173 impasses: 116 open on a street, 57 branch off one; 39 covered, 6 drawn as rooms where
  both houses are tall enough, 1 arch; 3.8 km), parcels 1,793 -> 1,756, buildings 1,742 -> 1,708,
  households 1,401 -> 1,367 (all later households shift: one sequential stream), trees 7,927 ->
  7,890. Medina dwellings 769 -> 735: doors 437 street + 10 open + 322 enclosed -> 735 street
  (323 on an impasse, 267 on an alley, 145 on a souk). Full capital: 6,641 impasses (medina 939,
  residential 5,101, suburb 601; 160 km), enclosed dwellings medina 1,781 -> 0, residential 7,802
  -> 0, suburb 0; streets 4,761 -> 11,402, parcels 42,128 -> 41,947, buildings 39,555 -> 39,225,
  households 38,898 -> 38,568. Full capital time in the same minutes: 34.8 -> 42.5 s (planner
  10.6 -> 15.5 s; tiles +12%). Tiles: old town 13_23 6.06 -> 6.74 MB (+11%), 14_23 +13%,
  14_24 +4%; 12_22 and 12_23 smaller (a shutter piece no longer used there after the household shift).
- Look: `output/checks/20.2.png` (souk: shops now keep a house door beside them),
  `output/checks/20.2-aerial.png` (old town from 100 m at 45 degrees: narrow paved lanes into the
  blocks, windows on walls facing them); the quick map shows a web of dead ends off the alleys.
  Blender: `output/bodjantouna-42/goumosbane.blend` refreshed.
- Doubts and questions for Ali: the planner is 4.9 s slower on the full capital (vectorized from
  9 s per-block); covered mouths are rarely drawn because both corner houses must have two floors.

## 2026-10-23 - Prompt 20.1 AD1 Every home gets a door and windows
- Commit: (see git log) | Model: Opus 5.5, high (playbook: Sonnet, high)
- Changed: `citygen/city/dressing.py` (`door_spot`, `entrances`, open-wall windows, slab windows,
  balconies, stair doors, house doors beside shops and cafes, corner-cached `drawn`; the street
  walls' draws untouched), `citygen/city/openings.py` (new: walls, open-wall probes, piece boxes,
  paths), `citygen/city/ground.py` (`Ground.drawn`: the terrain mesh's height), `citygen/mesh/props.py`
  (new pieces from one-sided quads: `door_narrow_*`, `window_slab_*` and `_shut`, `window_stair`,
  `balcony_slab`, `stair_door`), `citygen/mesh/tile.py` (paths drawn by the owning tile, terrain
  grid seeds the dresser's corner cache), `styles/maghreb.toml` (`every_home`, `[dressing.open_walls]`,
  `[dressing.slab]`, `[dressing.paths]`, roles), tests (5 new, 1 widened), `docs/SPEC.md`,
  `docs/ROADMAP.md`, `docs/HANDOFF.md`
- Checks: tests 62 passed (20.0 s; HEAD 17.7 s); `build --quick` 9.3 s; fingerprint 156 parts, 25
  changed: `tiles/*` and the 16 new `kit/*` pieces by exact name (`kit/balcony_slab`,
  `kit/door_narrow_{blue,brown,green,red,yellow}`, `kit/stair_door`,
  `kit/window_slab_{white,blue,green,brown}` and their `_shut`, `kit/window_stair`). Quick capital:
  1,401 dwellings, 1,401 main doors placed (713 on a street, 366 on open ground, 322 enclosed for
  20.2); 225 house doors beside shops and cafes; 356 slabs with 471 stair doors, 412 with a path.
  Tile bytes: three modern-estate tiles over the +20% budget (13_22 +36.6%, 14_22 +24.9%, 12_22
  +20.5%), accepted by the lead: estate tiles had almost no dressing before; +0.26 MB at most;
  instance bytes go to prompt 39. The others +0.9% to +3.0%. Level faces of the new pieces get
  planar meter UVs (no smeared concrete stripes). Full capital `--force`: 37.0 s (HEAD measured 34.5 to 44.3 s
  on this Mac; tile work single-process +12%).
- Look: `output/checks/20.1.png` (modern estate from 150 m: window grids, balconies in columns,
  shutter colors, blind gables), `output/checks/20.1-shops.png` (re-run after `door_clear` 0.9 ->
  2.0: the blue house door stands 2.84 m from the cafe center, 0.9 m past the awning and clear of
  the chairs; the fanlight glass then moved 1.5 cm off the wall, where it flickered)
- Decision: tile byte budget on estate tiles accepted by the lead (see Checks).
- Doubts and questions for Ali: none left. 7,802 residential houses on the full capital are
  enclosed; the lead extends prompt 20.2's impasses beyond medina and village blocks to cover them.

## 2026-10-23 - Fix: no more "Blender quit unexpectedly" from agents
- Commit: (see git log) | Model: Opus 5.5, medium
- Changed: `tools/make_blend.py` (`sandboxed()`: stops before starting Blender inside a macOS
  sandbox), tests (1 new), `CLAUDE.md` (never start Blender another way), `docs/HANDOFF.md`
- Checks: tests 57 passed; `build --quick` 1.6 s (reused); sandboxed run stops with a clear
  message and no new crash report; the exact `make_blend.py` command still saved the .blend
  (20:00); Ali's terminal: `sandboxed()` is False
- Doubts and questions for Ali: none

## 2026-10-23 - Prompt 20 A2d Ground textures
- Commit: (see git log) | Model: Opus 5.5, medium (playbook: Sonnet, medium)
- Changed: `citygen/mesh/builder.py` (optional `col` per piece, ribbon u along the street from a
  start distance, v across; draped cap with per-triangle street direction; curb v from the top),
  `citygen/mesh/tile.py` (`GroundTint` COLOR_0 on terrain, ribbon start via `line.project`,
  `street_directions` for sidewalks), `citygen/mesh/props.py` (unpack), `styles/maghreb.toml`
  (ground, street, sidewalk and curb textures and sizes, softer earth/grass/scrub blotches,
  stronger asphalt patches, `urban_ground` lifted, `[ground_tint]`), `tools/viewer/index.html`
  (`vertexColors` in the shared-material key), `tools/blender_beauty.py` (palette colors from
  `baseColorFactor`), tests (5 new), `docs/SPEC.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`
- Checks: tests 56 passed (about 18.5 s; the 5 new ones about 0.9 s); `build --quick` 9.1 s,
  9 tiles; fingerprint 141 parts, 11 changed: `tiles/*` and `tiles/textures/*` as allowed, plus
  a `tiles/.DS_Store` written by Finder (not by the build). Budgets: 14 shared images, 732 KB
  (limit 2 MB); tile bytes worst +9.5% (terrain-only capital tiles, about +17 KB of COLOR_0),
  densest `tile_65_106` +0.2% (limit +10%). Full capital `--force`: 32.4 s before (first run);
  back to back later, HEAD 36.8 s and this change 37.0 s (+0.5%), 168 tiles.
- Look: `output/checks/20.png` street - paving tiles and curb stones run along the street,
  asphalt with soft patches; `output/checks/20-air.png` from about 135 m over the cemetery and
  open ground - no visible repeat (a first try with earth at full mottle showed a grid; fixed).
  Blender: `output/bodjantouna-42/goumosbane.blend`.
- Doubts and questions for Ali: none. In Blender the ground, asphalt and paving keep their
  procedural shaders (they ignore the images and the tint); sidewalk, curb, earth, desert,
  forest and rock use the imported image x tint.

## 2026-10-23 - Prompt 19 A2c Textured walls and roofs
- Commit: "Textured walls and roofs: plaster, plinths and roof tiles" (see git log) | Model:
  DeepSeek V4.1 Flash, high (playbook: Sonnet, high)
- Changed: `citygen/mesh/builder.py` (wall split at the plinth, `_wall_band` mask, planar
  hip-roof UVs with a per-face slope length, degenerate roof triangles dropped),
  `citygen/mesh/tile.py` (`[plinth]` lookup, street-facing mask from street center lines and
  sidewalks), `styles/maghreb.toml` (palette textures and sizes, `plinth_blue`/`plinth_stone`,
  `[plinth]`, stronger plaster/render strengths), `tools/viewer/index.html` (anisotropy),
  tests (4 new/changed), `docs/SPEC.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`
- Checks: tests 51 passed (15.1 s); `build --quick` 7.8 s, 9 tiles; fingerprint 140 parts,
  9 changed, all `tiles/*`. Budgets: 7 shared images, 284 KB (limit 2 MB); full capital
  `--area capital` 31.5 s, 168 tiles, tile bytes +2.21% total and +3.45% for the densest tile
  (limit +10%); quick densest +2.82%. Plinth triangles fell from 9,634 to 2,208 on the
  dense medina tile by keeping party walls plain.
- Look: `output/checks/19.png` street before/after (mean difference 4.60) - stone plinths on
  street walls, plaster grain, aligned bands; `output/checks/19-hip.png` on the `city:1` build -
  tile rows running down every hip face, including the end triangles. Blender:
  `output/bodjantouna-42/goumosbane.blend`.
- Doubts and questions for Ali: none. The plinth is drawn only on street-facing exterior walls
  (a party wall or courtyard side is never visible); the base band still follows the ground.

## 2026-10-23 - Prompt 18 A2b Generated textures
- Commit: "Generated textures: plaster, stone, tiles and paving" (see git log) | Model: DeepSeek
  V4.1 Flash, high (playbook: Sonnet, high)
- Changed: `citygen/mesh/textures.py` (rewritten: 14 seamless surfaces, periodic value noise,
  wrapped strokes, Fourier blur, one stream per texture, PNG/JPEG encoder and cache),
  `citygen/texturesheet.py` (new), `citygen/__main__.py` (`texture-sheet`), `styles/maghreb.toml`
  (`[textures]` table), tests (4 new, prompt 17 tests migrated), `docs/SPEC.md`,
  `docs/ROADMAP.md`, `docs/HANDOFF.md`
- Checks: tests 47 passed (14.5 s); `build --quick` 7.0 s, 9 tiles; fingerprint 140 parts,
  0 changed (no palette entry names a texture yet). Seam check at 256 px: every texture's
  left/right and top/bottom edge difference is within 1.2 x the mean neighbour difference
  inside the image. Sheet: 2.1 MB PNG, 14 textures at 512 px.
- Look: `output/checks/texture-sheet.png` - each surface tiled 2 x 2, name/size/repeat below.
  Weak ones were reworked twice (stone, concrete, roof tiles, paving, asphalt, ground).
- Doubts and questions for Ali: none. "not mapped" is expected until prompt 19; `render_cream`
  already carries its string course at the floor line.

## 2026-10-23 - Prompt 17 A2a Textures in the 3D files
- Commit: "Textures in the 3D files: shared, embedded or off" (see git log) | Model: DeepSeek
  V4.1 Flash, high (playbook: Sonnet, high)
- Changed: `citygen/mesh/gltf.py` (`images` table, `baseColorTexture` + `KHR_texture_transform`
  scale `1/texture_size`, `images`/`textures`/REPEAT sampler with mipmaps; embedded images as
  bufferViews), `citygen/mesh/textures.py` (new: provider `texture(name, seed)` with one neutral
  test checker on its own stream, `write_shared_textures`, `images_for`), `citygen/mesh/tile.py`
  (`TileContext` texture mode and image table, `texture_files` in each tile entry),
  `citygen/build.py` (parent writes shared images before workers start), `citygen/defaults.toml`
  (`[tiles] textures = "shared"`), `tools/viewer/index.html` (material cache keys on texture URL
  and repeat), `tools/make_artifact.py` (one base64 copy per image, blob URLs through
  `setURLModifier`), tests (5 new), `docs/SPEC.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`
- Checks: tests 44 passed (12.5 s); `build --quick` 7.1 s, 9 tiles; fingerprint 140 parts,
  0 changed with the default `shared` (the palette has no textures yet) and 0 changed on a
  `textures = "off"` build. A test build with `cream` textured (`output/checks/p17`) writes
  `tiles/textures/test.png`; tiles that use it list the file, the others do not. Embedded mode
  puts the PNG in the BIN chunk and writes no texture folder. Blender 5.2 import gives
  `cream` an Image Texture node (`test.png`, 128 x 128) fed by a Mapping node with scale
  0.25 (4 m repeat) from UVMap. The phone page served by `python -m http.server` loads 9/9
  tiles, makes no HTTP request for the image (blob URL) and renders the checker.
- Look: `output/checks/p17-street.png` - test build only, not the final look: the cream wall on
  the right shows 1 m checker squares from the placeholder texture. The normal build is
  unchanged until prompt 19 maps real textures.
- Doubts and questions for Ali: none. The checker is a placeholder; prompt 18 replaces it with
  plaster, stone, tiles and ground.

## 2026-10-23 - Prompt 16 CP2 Checkpoint: light and ground
- Commit: "CP2 fixes: sidewalks and paint stay above the asphalt, build time won back" (see git
  log) | Model: Opus, medium
- Reviewed prompts 7-15 (all DeepSeek V4.1 Flash) against their "Done when": all met, docs and
  WORKLOG entries complete and honest, own random streams, numbers in the style, no em dashes.
  One ground: every height reader outside `terrain.py`, `world.py`, the planner and `ground.py`
  goes through `Ground` (only the 2D map shading reads the raw terrain, which is right there).
- Found and fixed: (1) 223 of 1,552 sidewalk corners missed their street's lift (the block-side
  edge lies exactly on the street outline), so they sat up to 0.24 m low, under the asphalt; the
  prompt 13 test compared the formula with itself. New `Ground.walk_top` with `walk_reach`.
  (2) Sidewalks and paint were drawn with their raw corners only: triangles up to 150 m long cut
  under the ribbon or floated (paint up to 1.8 m). Now points every `walk_step` (15 m) and
  `paint_step` (6 m, like the ribbon), and a new test checks the drawn triangles. (3) Speed:
  `build --area capital --workers 8` had gone 27 s -> 55 s, the planner 9 s -> 17.5 s. Fixed
  without changing any height: `Ground.height` samples the noise only in the city edge band
  (bit-identical, checked on 300,000 points), crossings use an STRtree of street bands (same
  output), carriageways group walks by street, sidewalk bands are clipped to nearby strips (same
  area; one pair of touching pieces is now one piece).
- Changed: `citygen/city/ground.py`, `citygen/city/paint.py`, `citygen/city/walks.py`,
  `citygen/mesh/tile.py`, `styles/maghreb.toml`, `tests/test_citygen.py`, `docs/SPEC.md`,
  `docs/HANDOFF.md`, `docs/ROADMAP.md`, `docs/prompts/04-people-landmarks-port.md` (prompt 39
  note on roofs), `CLAUDE.md` (timings)
- Checks: tests 38 passed (13.3 s; 21.6 s before the fixes, 11.3 s at `before-deepseek` on the
  same Mac today); `build --quick` 7.5 s (11.1 s before, 7.0 s at the tag); capital 29.7 s with
  8 workers, 73 s with 1 (SPEC: 26 s and 71 s). Fingerprint against `before`: 9 changed, all
  `tiles/*` (bytes +1-19%, triangles +1-15%). Stats: 235,109 triangles, 2,452,551 drawn,
  14.4 MB. Saved `fp-cp2`.
- Budgets: the densest tile is 5.8 MB on the quick build and 8.2 MB on the full capital
  (`tile_65_106`; 6.2 MB at the tag, so already over the 5 MB note before the trial). Roofs grew
  it most (roof triangles 7.9k -> 28.3k): added to prompt 39 (Q5 lighter tiles) instead of a
  new fix prompt. Tile time under 2 s (budget 5 s).
- Look: `output/checks/cp2-street.png` (golden hour, top: before the fixes, bottom: after, mean
  difference 1.29: same edge lines, zebra and curbs) and `output/checks/cp2-souk.png` (night,
  0.00: the old town has no sidewalks). Noon was proven identical to the old daylight in
  prompt 8. Blender file refreshed: `output/bodjantouna-42/goumosbane.blend`.
- The DeepSeek trial: careful, readable code and exact reports; it settled two budget conflicts
  well (ground blur, roof coping). It missed what only shows across prompts or in the drawn
  result: speed lost step by step, tests that check a function against itself, drape
  resolution. About one checkpoint session to fix. Recommendation: continue with it.
- Doubts and questions for Ali: none.

## 2026-10-23 - Prompt 15 A1 Roof life
- Commit: "Roof life: parapets and stair rooms" (see git log) | Model: DeepSeek V4.1 Flash,
  high (playbook: Sonnet, medium)
- Changed: `citygen/city/roofs.py` (new: `RoofLayout`, `roof_stream`, `roof_layout`, stair room
  placement and its door), `citygen/mesh/tile.py` (`roof_mesh`, `_coping`, one layout per owned
  building), `citygen/mesh/builder.py` (`add_loft`), `citygen/city/dressing.py` (`_roof` uses
  the layout), `citygen/build.py` (index `parapets`), `styles/maghreb.toml` (`[roofs]`),
  `tools/blender_beauty.py` (skip its own parapets when the index says so), tests (2 new),
  `docs/SPEC.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`
- Checks: tests 37 passed (17.6 s); `build --quick` 10.7 s, 9 tiles; fingerprint 140 parts,
  9 changed, all allowed (`tiles/index` plus 8 `tiles/*.glb`). Tile triangles at most +20.6%
  (tile 13_23, budget 25%), bytes 1.0-21.5%. Parapets 0.6-0.9 m by district kind; stair rooms
  on 32% of houses and 59% of apartment blocks; 2,021 of 2,062 parapet bands use the paired
  coping, 41 a capped fallback. Plans, world and maps unchanged.
- Look: `output/checks/15.png` (close aerial 120 m above the old town, 45 degrees down, mean
  pixel difference 9.49). After half: raised rims around flat roofs and courtyards, small stair
  boxes with doors, domes and minaret tops unchanged.
- Doubts and questions for Ali: the top is a sloped coping from the outer edge down to the
  inset deck, not a flat 0.2 m cap. A flat cap plus an inner wall cost 41% more triangles on the
  dense old-town tile, over the 25% budget. It reads as a capped parapet from the air; say if
  you want the flat cap in a later task.

## 2026-10-23 - Prompt 14 S1 Street surfaces and markings
- Commit: "Street surfaces: asphalt, stone, earth and painted markings" (see git log) | Model:
  DeepSeek V4.1 Flash, high (playbook: Sonnet, medium)
- Changed: `citygen/city/paint.py` (new: surface table, carriageway, edge/lane lines, dashes,
  zebra crossings), `citygen/city/model.py` (`Street.surface`, `Paint`, `CityPlan.paint`),
  `citygen/city/__init__.py`, `citygen/mesh/tile.py` (`street_meshes` material, `paint_meshes`,
  paint STRtree), style (`[streets.surface]`, paint numbers, `earth` and `road_paint` colors),
  tests (2 new plus one material), `docs/SPEC.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`
- Checks: tests 35 passed (17.8 s); `build --quick` 10.4 s, 9 tiles; fingerprint 140 parts,
  9 changed, all allowed (`tiles/index` plus 8 `tiles/*.glb`). Tiles grew 1.9-14.9% in bytes and
  at most 5.3% in triangles; plans, world and maps unchanged. Every one of the 3,047 marks lies
  inside its street's carriageway. Village Hirzabouane: 7 earth alleys, no paint.
- Look: `output/checks/14.png` (street, mean pixel difference 0.62). After half: dashed lane
  lines, solid edge lines and a zebra crossing just before the side-street junction.
- Doubts and questions for Ali: none.

## 2026-10-23 - Prompt 13 A3 Sidewalks, curbs and the boulevard promenade
- Commit: "Raised sidewalks, curbs and a boulevard promenade" (see git log) | Model: DeepSeek
  V4.1 Flash, high (playbook: Sonnet, high)
- Changed: `citygen/city/walks.py` (new: block bands clipped to street side strips, boulevard
  promenade pieces), `citygen/city/model.py` (`Walk`, `CityPlan.walks`), `citygen/city/__init__.py`,
  `citygen/city/ground.py` (`Ground.surface` adds the curb on a walk; `walk_tree`),
  `citygen/mesh/builder.py` (`add_draped_cap`, `add_skirt`), `citygen/mesh/tile.py` (`walk_meshes`), style
  (`[streets]`, `sidewalk` and `curb` colors, `sidewalk_width` per district), tests (3 new),
  `docs/SPEC.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`
- Checks: tests 33 passed (16.2 s); `build --quick` 9.4 s, 9 tiles; fingerprint 140 parts,
  9 changed, all allowed: `tiles/index` plus 8 `tiles/*.glb`. Tile bytes grew 0.5-3.3% (budget
  15%); plans, world and maps unchanged. Sidewalk widths 1.25-3.2 m; every sampled walk keeps
  the 5.5 m carriageway, stays out of buildings and sits 0.15 m above its street.
- Look: `output/checks/13.png` (street, mean pixel difference 8.21). After half: light raised
  sidewalks with dark curb faces on both sides, the asphalt between them, and the boulevard
  promenade on the left with its palm row standing on it.
- Doubts and questions for Ali: none. Doors show a 0.15 m plinth under them (the building base is
  not raised) - the prompt allowed either choice.

## 2026-10-23 - Prompt 12 A4b Everything on the graded ground
- Commit: "Dressing and cameras stand on the drawn surface" (see git log) | Model: DeepSeek
  V4.1 Flash, high (playbook: Sonnet, high)
- Changed: `citygen/city/ground.py` (`STREET_LIFT` moved here, `Ground.surface`: ground or the
  highest street ribbon), `citygen/city/dressing.py` (`Dresser` takes the ground; spans, gates,
  wall tops, `ground_heights` and `building_highs`; doors, shop fronts and awnings use the
  surface 0.5 m in front of the wall), `citygen/mesh/tile.py` (dresser ground, building highs,
  ground pieces, street trees), `citygen/build.py` (camera views and index focus on the surface),
  tests (3 new), `docs/SPEC.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`
- Checks: tests 30 passed (about 16 s; the new tile fixture reuses one build, so the suite stays
  close to its old time); `build --quick --force` 9.7 s, 9 tiles; fingerprint 140 parts, 9 changed, all
  allowed: `tiles/index` plus 8 `tiles/*.glb` (tile_13_23 loses 888 triangles: one sabat no
  longer clears the raised alley surface, so it is correctly not built). Plans, world, maps,
  gazetteer and kit identical.
- Look: `output/checks/12.png` - top: HEAD, bottom: working tree. The camera rises by the street
  lift (0.2 m in the souk), so the whole frame shifts down slightly; no sunken or floating shop
  fronts or goods at the lane edges. Numeric checks: every door threshold within 0.05 m of the
  surface 0.5 m in front, every sampled wall foot in the terrain, every ground piece within
  0.05 m of `surface`.
- Doubts and questions for Ali: none. One unavoidable look change: cameras now stand on the
  ribbon, so before/after frames cannot be pixel-aligned at the same camera height by design.

## 2026-10-23 - Prompt 11 A4a City ground
- Commit: "Graded city ground inside cities" (see git log) | Model: DeepSeek V4.1 Flash, high
  (playbook: Sonnet, high)
- Changed: `citygen/city/ground.py` (new: `Ground`, `_City`, `_Blur`), `citygen/mesh/tile.py`
  (`TileContext.ground`, `height` now graded), `citygen/defaults.toml` (`[ground]`), tests (3 new),
  `docs/SPEC.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`
- Checks: tests 27 passed (10.25 s, +0.5 s for 3 tests); `build --quick --force` 7.0 s, 9 tiles;
  fingerprint 140 parts, 9 changed, all `tiles/*` (index and tile_12_22 to tile_14_24, +4 to +8
  bytes each); plans, world, maps, gazetteer and kit identical. Tile build (one process, 9 tiles):
  2.12 -> 2.46 s (+16%), slowest tile 1.31 -> 1.45 s (+11%), both under the +30% budget.
  Inside terraced blocks the ground differs from the blur by at most 0.40 m (= `terrace_max`);
  median height spread of those blocks 3.37 -> 2.56 m. Blender file refreshed:
  `output/bodjantouna-42/goumosbane.blend`.
- Look: `output/checks/11.png` - top: HEAD, bottom: graded ground. The boulevard stays even, the
  far crossing and the tree bases settle onto one surface; the difference is small because the
  quick capital's ground was already locally smooth at 8 m (measured chord error 2 mm), so the
  visible change is mostly the city-wide shift of up to 0.75 m (mean 0.05 m).
- Doubts and questions for Ali: none. One deliberate deviation inside the prompt: the blur is an
  exact disc mean of lattice cells with one terrain sample per cell, not a 17-sample pattern per
  cell - same about 60 m smoothing, about 15x cheaper (17 samples cost about +40% per tile, over
  the budget). Documented in `city/ground.py`.

## 2026-10-23 - Prompt 10 Q4 Blender 5 haze and warm grade
- Commit: "Blender 5 haze and warm grade" (see git log) | Model: DeepSeek V4.1 Flash, high
  (playbook: Sonnet, high)
- Changed: `tools/blender_beauty.py` (`setup_haze` returns early into the new `setup_haze_group`
  on `bpy.app.version` 5 and up; the 3.6 and 4.x body below stays as it was), `docs/ROADMAP.md`,
  `docs/HANDOFF.md`
- Checks: tests 24 passed (9.8 s); quick build OK (0.1 s cached); fingerprint 140 parts, 0 changed
  (`--allow ""`); Blender 5.2 log has no Python errors (only the pre-existing `World.use_nodes`
  deprecation warning).
- Look: `output/checks/10.png` - top: HEAD script on 5.2, no compositor, so no haze and no grade;
  bottom: new script, warmer walls, sky and pottery. Mean channel difference over the frame: R +2.86,
  G +0.04, B -4.78. Extra proof for the haze, which needs distance: `output/checks/10-aerial.png`
  (same pair in the aerial view) shows the far coast washed pale by the depth mix; the souk lane is
  under about 20 m deep, so there the warm grade is the visible change.
- Doubts and questions for Ali: none. The 5.x Color Balance node reports its method through a menu
  socket that cannot be listed from Python; its default is Lift/Gamma/Gain, which is exactly what
  the 3.6 code set, so the script leaves it alone and a future default change would be silent.

## 2026-10-23 - Prompt 9 V2 Ambient occlusion and clean edges
- Commit: "Ambient occlusion and a quality menu in the viewer" (see git log) | Model: DeepSeek
  V4.1 Flash, high (playbook: Sonnet, high)
- Changed: `tools/viewer/index.html` (one post chain, GTAO and SMAA, High/Fast menu, `?quality`,
  `?perf=1`, a deterministic fallback for the street camera), `README.md`, `docs/SPEC.md`,
  `docs/ROADMAP.md`, `docs/HANDOFF.md`
- Checks: tests 24 passed (9.8 s); quick build OK (0.1 s cached); fingerprint 140 parts, 0 changed
  (`--allow ""`); `before_after --view street --query quality=high` 0.18 mean (sub-pixel
  post-chain differences, the picture is visually identical), the same run without the query 0.00.
  M1, 1280x720: High 18.07 ms/frame against Fast 17.23 ms (+4.9%); 2560x1440: 21.01 against
  17.23 ms (+22%); both under the +40% budget. High render cost 2.82 against 1.47 ms (1280x720).
- Look: `output/checks/9.png` - High in the street: soft contact shadows at wall bases and tree
  trunks, no halo against the sky, cleaner silhouettes. `output/checks/9-pair.png` compares the
  HEAD viewer in Fast with the working viewer in High, same camera.
- Doubts and questions for Ali: none. On a retina screen the AO buffer is about 1 MP and is
  scaled up, a compromise that keeps the frame under budget; if it looks soft on your screen, tell
  me and we can raise `AO_PIXELS` in the viewer.

## 2026-10-22 - Prompt 8 V1 Golden hour in the viewer
- Commit: "Golden hour light menu in the viewer" (see git log) | Model: DeepSeek V4.1 Flash, high
  (playbook: Sonnet, high)
- Changed: `tools/viewer/index.html` (light presets, sky dome, per-mode sky reflection, asymmetric
  shadow box, light menu), `README.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`
- Checks: tests 24 passed (9.8 s); quick build OK (0.2 s cached); fingerprint 140 parts, 0 changed
  (`--allow ""`); `before_after --view street` 0.00 and the same with `--query light=noon` 0.00;
  the new Noon against a HEAD worktree differs by 0 of 921,600 pixels.
- Look: `output/checks/8.png` - top: HEAD daylight, sun 40 degrees, flat blue sky; bottom: golden
  hour, sun 14 degrees, pink horizon, warm walls and haze. At 14 degrees the narrow street lies
  in the shade of its buildings, so no cast shadows cross the road; the long shadows show in the
  aerial view. The new light menu is at the top right, next to the camera spot.
- Doubts and questions for Ali: none. If the golden hour feels too bright in the shade, lower
  `hemi` in `PRESETS.golden` (one number, all else follows).

## 2026-10-22 - Prompt 7 Q3 Bougainvillea that cascades
- Commit: "Q3 bougainvillea curtains" (see git log) | Model: DeepSeek V4.1 Flash, medium (playbook: Sonnet, medium)
- Changed: `citygen/mesh/plants.py` (new shared clump and tube helpers), `citygen/mesh/climbers.py`
  (new), `citygen/mesh/trees.py`, `citygen/mesh/props.py`, `citygen/kit.py`,
  `styles/maghreb.toml`, `tests/test_citygen.py`, `docs/SPEC.md`, `docs/ROADMAP.md`,
  `docs/HANDOFF.md`
- Checks: tests 24 passed (9.6 s); quick build 6.6 s; fingerprint 7 changed, all allowed:
  `kit/bougainvillea` and `kit/bougainvillea_b` 82 -> 250 triangles, four tiles +0.1 to 0.2%,
  `tiles/index` bytes; every other kit piece identical. Each climber 250 triangles, 2.4 m wide,
  0.28 m deep, 4.8 m tall.
- Look: `output/checks/7.png` - before: nine floating octahedra on a straight pole; after: a
  curtain of flat bracts from the wall top down to about 2 m, three magenta shades, green leaves
  and two or three bent stems. The kit-sheet camera also shows the next rows, which hide the
  lower half of the piece.
- Doubts and questions for Ali: at 250 triangles the mass is coarser than the Tounes cascade
  (1,714 triangles); if it reads too sparse in the streets, raise `clumps` in
  `[dressing.climber]` in a later prompt.

## 2026-10-22 - Prompt 6 CP1 Checkpoint: foundations
- Commit: "CP1 fixes" (see git log) | Model: Opus, medium
- Reviewed prompts 1-5 against their "Done when": all met. No em dashes, no unseeded randomness,
  no stray files. Prompt 1 had left out the "Checking a change" paragraph in SPEC section 9: added.
- Fixed: (1) a `--force` build stopped while writing maps left a cut-short `country.png` that the
  next build reused (found by a real Ctrl+C test): `summary.json` is now deleted before maps and
  data are rewritten; the slow resume test covers it and fails without the fix. (2) The build key
  now includes the Python and library versions (a shapely upgrade could change output or break
  cached plans). (3) The fingerprint skips Ali's `*.blend` files (they always showed as changed).
  (4) The fingerprint test now edits one plan key and checks that exactly that part changes.
- Changed: citygen/build.py, citygen/buildkey.py, tools/fingerprint.py, tests/test_citygen.py,
  docs/SPEC.md, docs/HANDOFF.md, docs/ROADMAP.md
- Checks: tests 23 passed (9.6 s) + 2 slow (21 s); quick build 6.7 s (forced 7.0 s), rerun 0.1 s;
  stats match prompt 5 (1,742 buildings, 9 tiles, 200,024 triangles, 11.7 MB). Fingerprint vs
  before the fixes: 0 changed (only the two .blend parts, now skipped). Capital `--workers 8`:
  24.7 s forced, 1.5 s rerun, 299 parts 0 changed. Saved `fp-cp1` (140 parts).
- Look: output/checks/cp1-street.png and cp1-aerial.png (before_after on the unchanged tree,
  pixel difference 0.00 both). Current state: plain wide asphalt streets without sidewalks, flat
  facades, fields and the walled medina from the air; later prompts change exactly these.
- Doubts and questions for Ali: none. Small rough edge left: the before/after labels cover the
  viewer's "tiles 9/9" box (cosmetic).

## 2026-10-22 - Lead session: DeepSeek trial and backup point
- Commit: the "DeepSeek trial" commit, tagged `before-deepseek` | Model: Opus
- Changed: docs/PROMPTS.md (which prompts stay on Claude), docs/prompts/02 (checkpoint 16 judges
  the trial), docs/HANDOFF.md, this log
- Plan: prompt 6 on Claude (Opus); prompts 7-15 with DeepSeek V4.1 Flash in OpenCode; prompt 16
  on Claude judges the trial. To undo the trial: `git reset --hard before-deepseek` (ask first).
- Doubts and questions for Ali: none

## 2026-10-22 - Prompt 5 C1b Resumable builds
- Commit: see git log | Model: Sonnet, high
- Changed: citygen/buildkey.py (new), citygen/build.py, citygen/config.py (`style_path`), citygen/mesh/tile.py (write .part, rename), citygen/__main__.py (--force), tests/test_citygen.py, README.md, docs/SPEC.md, docs/HANDOFF.md, docs/ROADMAP.md (boxes 5 and C1)
- Checks: tests 23 passed (9.5 s) + 2 slow (17 s); quick build 7 s; fingerprint vs before: 142 parts, 0 changed. Capital `--workers 8`: first run 26 s, run again 1.5 s (6%), 0 changed vs the first run. Ctrl+C at 15 s: 8 tiles kept, the plan reused, finished in 16.5 s, 299 parts 0 changed.
- Look: none.
- Doubts and questions for Ali: (1) any code edit changes the key, so the first build after an edit is always full, as the prompt asked. (2) Besides the prompt, maps and data files are also skipped when the key matches (otherwise they cost 3.5 s of the rerun). (3) Tiles keep a small note per tile in `cache/`, written by the workers, because the parent is busy with maps and could lose finished tiles on Ctrl+C.

## 2026-10-22 - Prompt 4 C1a Build tiles in parallel
- Commit: see git log | Model: Sonnet, high
- Changed: citygen/build.py (TilePool, resolve_workers), citygen/__main__.py (--workers), citygen/defaults.toml ([build] workers = 0), tests/test_citygen.py (slow test), pytest.ini (new, slow marker), README.md, docs/SPEC.md, docs/HANDOFF.md
- Checks: tests 20 passed (8 s) + 1 slow (5 s, workers 1 vs 2 give identical bytes); quick build 7 s (stays sequential); fingerprint vs before: tiles 0 changed (only Ali's open .blend file moved). Capital: `--workers 1` 71 s, `--workers 8` 25 s (7 workers 24.6 s, 5 workers 28 s), fingerprint w1 vs workers 8: 299 parts, 0 changed.
- Look: none.
- Doubts and questions for Ali: the goal was 3x; I reach 2.8x. This Mac has 4 fast and 4 slow cores, and 9 s of city planning cannot be shared between processes. Tiles alone are 4x faster. Options: accept 2.8x, or add a later task that plans a city in parallel. Answer: Ali accepted 2.8x; box 4 ticked.

## 2026-10-22 - Prompt 3 T3 Housekeeping
- Commit: (this commit) | Model: Sonnet, low
- Changed: citygen/city/geo.py, citygen/__main__.py, requirements.txt, docs/SPEC.md, docs/ROADMAP.md, .claude/agents/city-builder.md, city-checker.md
- Checked: tests 20 passed (8 s, no warnings), quick build 7 s, fingerprint 142 parts 0 changed.
- Note: editing .claude/agents needed the sandbox off.

## 2026-10-22 - Prompt 2 T2 Before/after pictures
- Commit: see git log | Model: Sonnet, medium
- Changed: tools/before_after.py (new), tools/viewer/index.html (camera ground clamp only after all tiles loaded), docs/HANDOFF.md, docs/SPEC.md, docs/ROADMAP.md
- Checks: tests and quick build, see commit. Unchanged tree: street, souk, aerial, --cam/--look and --kit-sheet --frame awning_red all 0.00. Dark `leaf` (reverted): 1.62.
- Look: output/checks/t2-street.png, t2-souk.png, t2-aerial.png, t2-cam.png, t2-kit.png, t2-leaf.png (leaf test)
- Doubts and questions for Ali: found and fixed a viewer bug: the camera was lifted to the lowest loaded tile + 1 m while tiles were still loading, so the same world gave different pictures per run. Without the fix an unchanged tree showed a difference of 36-75. The before half copies the working tree's viewer, so both halves match.

## 2026-10-22 - Prompt 1 T1 Regression fingerprint
- Commit: see git log | Model: Sonnet, medium
- Changed: tools/fingerprint.py (new), citygen/kit.py (`make_kit`), citygen/mesh/tile.py, citygen/kitsheet.py, tests/test_citygen.py, docs/SPEC.md, docs/HANDOFF.md, docs/ROADMAP.md
- Checks: 19 tests pass, quick build 6.6 s, two identical builds: "140 parts, 0 changed". Test: `clumps` 7,8 -> 6,7 in broadleaf changed only 9 parts (tiles/*, tiles/index, kit/tree_broadleaf_c, e.g. "kit/tree_broadleaf_c: triangles 164 -> 144", "tiles/tile_13_23.glb: bytes 4646196 -> 4644684, triangles 67697 -> 67637"); styles restored.
- Look: no
- Doubts and questions for Ali: none

## 2026-10-21 - Lead session: the playbook
- Commit: the "Playbook" commit | Model: Opus, high
- Changed: docs/PROMPTS.md (index), docs/prompts/01-09 (100 prompts), docs/ROADMAP.md
  (checklist), docs/WORKLOG.md (this file), CLAUDE.md (prompt routine), docs/WORKFLOW.md,
  docs/HANDOFF.md
- Checks: docs only. Two independent Opus reviews checked every prompt against the code (80
  findings, all valid ones applied); prompts 20.1 and 20.2 were added because many homes have no
  door or windows today (`Dresser.facades` needs a street within 1.6 m).
- Look: docs/PROMPTS.md
- Doubts and questions for Ali: none

## 2026-10-21 - Lead session: Q1 Natural leafy trees
- Commit: dcaac69 | Model: Sonnet helper, Opus review
- Changed: citygen/mesh/trees.py (new), mesh/props.py, kit.py, kitsheet.py, mesh/tile.py,
  styles/maghreb.toml, tests, docs
- Checks: 18 tests; tiles 11.55 to 11.65 MB (+0.9%); the 58 other kit pieces identical
- Look: before/after boulevard picture (pointed diamonds became rounded, shaded crowns)
- Doubts and questions for Ali: none

## 2026-10-21 - Lead session: Q2 Family names
- Commit: df3e57e (and 778ad09: .gitignore for .DS_Store) | Model: Sonnet helper, Opus review
- Changed: city/life.py, names.py, styles/maghreb.toml [life], tests, docs
- Checks: 17 tests; only family names changed (tiles, world and plan without names identical)
- Look: 30 sample names; Ali accepted them
- Doubts and questions for Ali: none
