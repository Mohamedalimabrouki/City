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
