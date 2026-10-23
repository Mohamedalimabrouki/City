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
