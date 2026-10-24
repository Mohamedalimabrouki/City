# Handoff - the project's memory

Read this once when you start on a new machine, or when a task needs background. Everyday
rules are in `CLAUDE.md`, tasks in `docs/ROADMAP.md`, technical rules in `docs/SPEC.md`, cost
advice in `docs/WORKFLOW.md`, ready prompts in `docs/PROMPTS.md`.

## The owner

- **Ali**, a mechatronics engineer who also does 3D (Blender 5.2 on a Mac), video and stories.
  Not a software developer: answer in plain language (about B2 English), define jargon, keep
  reports short, and walk through screenshots step by step. Speaks English, French and Arabic.
- Never write the em dash character anywhere (code, docs, commits, answers); use "-".
- His weekly token limit matters. Efficiency is a requirement, but never at the cost of quality.

## The goal

- A procedural generator (a program that builds everything from rules) for a huge invented
  Mediterranean / North African country, Tunisia-like but fictional. It serves games, stories,
  films and more. Agents improve the code; the code builds the world for free.
- Why procedural and not hand-made or AI images: the same seed always gives the same world
  (stories stay consistent), size is only computer time, sessions stay small and cheap, and
  standard glTF files open in Blender, Godot, Unity and Unreal.
- Castles, steampunk or vertical cities are styles on top of the same plan layer (tasks F1-F4),
  not a different project.
- End point: golden-hour streets with textured walls, rich street life, and houses with real
  interiors when a scene needs them (tasks H1-H4).
- Audience: worldwide, but authentically North African. Names must sound Maghrebi (Arabic and
  Berber). Ali saw early names that sounded Hebrew and asked to fix them: `citygen/names.py`
  filters spellings and a test guards it. Arabic script comes with task D5.
- Team: Ali plus Claude. Everything is built so a small team could scale it later (style packs,
  kits, small roadmap tasks).
- **Tounes Rush** is Ali's three.js runner game (claude.ai artifact "Tounes Rush AAA V5.2").
  Its 3D pieces live in `kits/tounes/`, so both projects share one look. Task C6 will export
  run routes from generated cities for the game.

## Where things stand (October 2026)

- Done: v0.1 (country, cities, maps, data, 3D tiles, viewer, Blender scripts), **A0** (Tounes
  kit, street dressing, households and souk trades, night mode, "click a house: who lives there")
  **Q2** (family names that sound Tunisian), **Q1** (rounded, shaded leafy trees), **Q3**
  (bougainvillea curtains instead of lollipops), **P8** (golden hour as the viewer's default, with
  a Noon / Golden hour / Night menu) and **Q4** (Blender 5 beauty renders get the same depth haze
  and warm grade as 3.6 and 4.x, through the compositor node group).
- Since 21 October 2026 the work runs on Ali's Mac through the playbook `docs/PROMPTS.md`: 100
  numbered prompts (`Do prompt N.`), each with its model and effort, one session each; nine Opus
  checkpoints review the work as it goes; every session adds an entry to `docs/WORKLOG.md`.
  After prompt 100, Ali brings the work back to his lead session for a full review.
- From prompt 7, a trial runs the build prompts with DeepSeek V4.1 Flash in OpenCode (free; it
  reads `CLAUDE.md` because there is no `AGENTS.md`). Claude keeps the checkpoints, the big
  designs and the phone page (list in `docs/PROMPTS.md`). Checkpoint 16 judged the trial
  (prompts 7-15): good code and honest reports, but it let speed slip and its tests did not
  look at the drawn result; recommendation: continue with it, checkpoints catch the rest. The
  git tag `before-deepseek` stays as the backup point. DeepSeek usage ended after prompt 19
  (23 October 2026): from prompt 20 the lead session (Opus) runs each prompt with an Opus helper,
  reviews its diff, tests, fingerprint and pictures, fixes, then commits one commit per prompt.
- Prompts 1-5 (tools and fast builds) are done and checked by checkpoint 1 (CP1, 22 October
  2026): fingerprint, before/after pictures, parallel and resumable builds all work as
  documented. Reference for checkpoint 16: `output/checks/fp-cp1.json` (quick build) and the
  pictures `output/checks/cp1-street.png`, `cp1-aerial.png`.
- Prompts 6-15 are done: bougainvillea, golden hour, ambient occlusion, Blender 5 haze, A4a and
  A4b (graded ground, and every prop, door, tree and camera on its surface), A3 (raised
  sidewalks, curbs and the boulevard promenade), S1 (street surfaces and painted markings) and
  A1 (roof parapets and stair rooms). Checkpoint 2 (CP2, 23 October 2026) reviewed them, fixed
  sidewalk corners and paint lines that sank under the asphalt, and won back the build time the
  trial had lost. Reference for checkpoint 27: `output/checks/fp-cp2.json` and
  `output/checks/cp2-street.png`, `cp2-souk.png`.
- Prompts 17-26 are done (facades and street life): textures on walls, roofs and ground, a door
  and windows for every home (20.1), impasses to every landlocked house (20.2), lit windows by
  household, colonial arcades and iron balconies, building massing (cut corners, domes, set-back
  floors, stepped slabs, L villas), greenery (avenue trees, villa gardens, courtyard citrus),
  parked cars and taxis, benches, kiosks and fountains. Checkpoint 3 (CP3, 24 October 2026): an
  independent reviewer and the lead found and fixed paint rows outside parking districts,
  arcade zones at cut corners, lamps inside wider streets, a float in the lit-flat stream key and
  an unbounded cache; a speed round made tiles 26% faster and tests 31 s -> 20 s with
  byte-identical output. Reference for checkpoint 43: `output/checks/fp-cp3.json` and
  `output/checks/cp3-street.png`, `cp3-souk.png`. Next: prompt 28.
- Seed 42 makes the country **Bodjantouna** with the capital **Goumosbane**.
  `python -m citygen build --quick` writes it to `output/bodjantouna-42/` in about 10 seconds on
  Ali's Mac (20 seconds in the cloud).
- All work is on the git branch `claude/procedural-city-generator-xop72h`. Keep working on it and
  push at the end of every task (GitHub is the backup).
- 3D page for the phone (made from the quick build):
  https://claude.ai/artifact/HMtdFZUV9sGmyPn4q8mKsq . Rebuild it with `tools/make_artifact.py`
  after a big visual step, then publish the folder to that same link from a Claude session.

## Decisions and lessons (do not relearn them)

- **Measure the full capital, not only the quick build** (CP2). Prompts 11-15 each stayed under
  their own budget on the quick build, yet together they doubled `build --area capital
  --workers 8` (27 s to 55 s) and the planner (9 s to 17.5 s). The causes were all "every item
  against every item" loops: crossings buffered every street for every main street, carriageways
  scanned every walk per street, sidewalk bands were clipped against one city-wide union, and
  `Ground.height` sampled the noise terrain at every point even where the edge blend gives it
  weight 0. Use an STRtree or a dict instead, and time the capital after any planner or
  tile change.
- **Speed without changing a byte** (CP3): per-call overhead, not maths, dominated tiles (a 1-point
  `Ground.height` cost 47 us, a 1-point terrain 726 us: 23 Perlin calls; `np.allclose` 15 us). Safe:
  plain-float or stacked versions of elementwise formulas in the same order (`Ground._height_one`,
  `noise._Octaves`), one ground query per tile for many pieces, reusing a result already made from the
  same stream (`Dresser.keep_roof`), replaying `Generator.choice` exactly (`rng.weighted`). Each change
  was checked against the old path on 30,000 points before the fingerprints. Plan pickles differ run to
  run (`stats["seconds"]`): compare plans attribute by attribute, never by one pickle hash.
- **Test the drawn triangles, not the function against itself** (CP2). The prompt 13 test
  compared `Ground.surface` with the same formula, so it passed while 14% of sidewalk corners
  missed their street (they lie exactly on its outline) and long sidewalk and paint triangles
  (up to 150 m) cut under the ribbon or floated up to 1.8 m. `walk_top` takes the lift of
  streets within `walk_reach`; walks and paint are drawn with points every `walk_step` and
  `paint_step`; `test_drawn_sidewalks_and_paint_stay_above_the_ribbon` checks the triangles.

- **Roof layout** (prompt 15, `city/roofs.py`, `[roofs]`): `roof_layout` is the only place that
  decides a flat roof's parapet band, deck, stair room and door. It runs on
  `roof_stream(seed, city id, k)`, so the tile mesher and `Dresser._roof` get the same answer
  without sharing state. A parapet reuses the building wall as its outer face (free) and adds a
  sloped coping from the outer top down to the inset deck: 2 triangles per edge. Do not build a
  solid band or a flat cap with an inner wall: on the dense old-town tile (tile 13_23, 856
  buildings) the solid band was +51% and a flat cap about +41%, over the +25% budget; the coping
  version is +20.6%. `_coping` needs open rings: strip the closing point before rolling the
  inner ring, or the roll puts the duplicate in the middle and `add_loft` drops every quad (that
  bug made the first parapets invisible).
- **Textures** (prompt 17, `mesh/gltf.py`, `mesh/textures.py`): a palette `texture` +
  `texture_size` becomes a `baseColorTexture`; UVs stay meters and `KHR_texture_transform`
  scales by `1/size`. The sampler is REPEAT with mipmaps (10497 / 9987). Shared images are
  written once by the parent before any worker starts; every tile entry lists the images it uses
  in `files`, so the resume check waits for them. Embedded images are bufferViews without a
  `target` (an image is not an accessor). The fingerprint hashes GLB bytes, so keep new
  top-level JSON keys in their old insertion position (`extensionsUsed` before `meshes`):
  appending one makes every tile "content differs" although the scene is identical. The viewer
  material cache keys on the texture URL and repeat; the phone page stores each image once as
  base64 JSON and maps `textures/<name>` to a blob URL.
- **Plinths and wall UVs** (prompt 19, `mesh/builder.py`): `v = -(z - z_ref)` with `z_ref` the
  highest ground under the building, so a street sees one continuous course. Splitting a wall at
  `z_ref + height` doubles its vertices; on the dense medina tile that was +14% tile bytes. Apply
  the plinth only to exterior segments within half the street width plus that street's sidewalk
  plus 0.6 m of the wall midpoint (party walls are invisible): +3.5% on the same tile. Compute the
  mask on the *oriented* ring, because `extrude` orients the polygon. Keep the old
  `s1 = cumsum(length); s0 = s1 - length` arithmetic when no mask is given: computing `s0` from a
  cumulative array instead changed two UV bits in every kit piece that uses `extrude`, and the
  fingerprint flagged 47 kit parts as changed.
- **Hip-roof UVs** (prompt 19): planar meter UVs (u along the eave, v up the slope) need the
  slope of *that* face. Long faces use `hypot(W/2, height)`; end faces use
  `hypot((L - W)/2, height)`. Reusing the long slope stretched the end triangles by 22% on a
  10 x 6 m roof; the area test caught it. `np.cross` refuses 2D vectors in this NumPy, so test
  UV area with the determinant `e1x*e2y - e1y*e2x`. A square roof has no ridge: drop triangles
  whose 3D cross product is zero, or the degenerate end quads write NaNs.
- **Texture strength** (prompt 19): plaster at grain 0.45 / mottle 0.5 read flat at street
  level; 0.7 / 0.7 with stain 0.5 is visible but still neutral. The viewer sets anisotropy
  `min(8, max)` on a computer and 2 in the phone/Fast path, with the sampler's mipmaps.
- **Ground textures** (prompt 20, `mesh/tile.py`, `[ground_tint]`): from 150 m up, a ground
  texture's mid-size blotches (mottle, stain) tile into an obvious grid; fine detail averages
  out. Keep ground mottle/stain low (earth 0.2/0.15) and let the `COLOR_0` tint, a pure function
  of world x, y, carry the large variation. Tint values stay at or below 1 (glTF multiplies
  color x texture x COLOR_0), so the textured ground darkens: `urban_ground` was lifted to
  `#D6C7A4` to keep its old tone. A sidewalk piece wraps block corners (it fills about 10% of its
  rotated bounding box), so a per-piece direction was wrong for half of them: the slab direction
  is per triangle, from the nearest street. Ribbon u starts at the street's own distance
  (`line.project`), or the pattern jumps at every tile edge. `MeshBuilder.add` takes optional
  `col`; a part mixing pieces with and without it fills the rest with white. In Blender the glTF
  importer links a textured Base Color (texture x factor x vertex color), so the socket's value is
  default grey: `blender_beauty.py` reads palette colors from `baseColorFactor` in the tiles
  (this also fixes the walls, grey in the beauty look since prompt 19). The COLOR_0 adds about
  17 KB per tile (+9.5% on terrain-only tiles, near the +10% budget). Time the capital against a
  fresh HEAD build in the same minutes: this Mac varied 32 to 37 s for the same code.
- **Parallel tiles** (`TilePool` in `citygen/build.py`): spawn processes start while the parent
  plans and wait for one pickle file (world + plans); each builds its own `TileContext`. Use
  `multiprocessing.Pool`, not `ProcessPoolExecutor`: the Claude sandbox forbids the
  `os.sysconf` call the executor makes. Capital on the M1: 71 s -> 25 s (2.8x); the 9 s of
  planning is now the biggest serial part. The parent's file writing runs while workers load.
  Slow tests: `python -m pytest -q -m slow` (default run skips them, see `pytest.ini`).
- **Blender in the sandbox**: Blender 5.2 crashes in its first second inside any macOS sandbox
  (Claude's or Codex's): it reads the GPU name, gets nothing, and `MTLBackend::metal_is_supported`
  crashes; macOS then shows Ali "Blender quit unexpectedly". All 12 crash reports up to
  2026-10-23 were agents, never Ali. `tools/make_blend.py` now asks macOS (`sandbox_check` via
  ctypes, not an environment variable, which stays set in excluded commands) and stops before
  starting Blender. Checked: sandboxed run stops, the exact excluded command still saves the
  .blend, Ali's own terminal sees no sandbox. Direct `blender ...` calls are not guarded: never use them.
- **Blender kit export** (prompt 38, `tools/blender_kit_export.py`): the second sanctioned way to start
  Blender (it imports `sandboxed()` from `make_blend.py`). One file runs on both sides: in Blender
  (`--inside`, bpy only, no citygen imports) it bakes and exports, printing `blender_kit_export: <kind>
  <json>` lines; outside it writes the manifest and checks each .glb with `read_parts`. Lessons: in
  Blender 5.2 `mesh.materials.clear()` drops the faces' material indices (assign slots in place);
  filter glTF exporter options by `op.get_rna_type().properties` so a renamed option never breaks
  it; no UVs or vertex colors (`read_parts` cannot read Blender's normalized uint16 colors). The
  fixture `tests/data/blender_kit/` re-exports byte for byte the same.
- **Resumable builds** (`citygen/buildkey.py`, `build.py`): `build_key` = SHA-256 of settings (minus
  `output`, `workers`, `area`), style bytes, kit manifests and .glb files, every `citygen/**/*.py`
  and the sorted planned settlement ids, plus the Python and library versions; stored in `summary.json` and `tiles/index.json`. Plans
  are pickled to `cache/<slug>-<key12>.pkl` right after planning (before tile export can touch
  them); reload resets `plan.settlement` to the world's own object. Tiles are written as
  `.glb.part` then renamed; each finished tile also leaves a note `cache/tiles-<key12>/tile_i_j.json`
  (written by the worker), so Ctrl+C loses only the tiles in flight. A tile is reused when all
  files its entry lists exist (`tile_files`: add texture and lod files to the entry as `files`)
  and the .glb size matches. Maps and data files are skipped when `summary.json` has the same key;
  `summary.json` is deleted before they are written again and written last, so a build stopped
  while writing maps (even with `--force`) never leaves a cut-short map counted as done (CP1 fix).
  Any code edit changes the key, so the first build after an edit is always full. In a test that
  fakes `plan_city`, set `plan.settlement` yourself or the index loses its `views`.
- **Fingerprint** (`tools/fingerprint.py`): hash kit arrays only after skipping `None` ones
  (`tobytes()` of a None array hashes a memory address and differs every run).
  It skips `*.blend` files in the build folder: Ali saves them in Blender, so they always
  "changed" (CP1 fix).
- **Randomness** only from `citygen.rng.stream(seed, *purpose)`, one purpose path per feature, so
  adding a feature never changes the rest of the world.
- **Graded city ground** (prompt 11, `city/ground.py`, `[ground]` in defaults): inside a city the
  terrain height is a blurred (60 m disc), gently terraced copy of the natural terrain; outside
  it is the natural terrain; the two blend over 40 m at the city limit. The blur is an exact disc
  mean of heights sampled once per 8 m world-aligned lattice cell, cached lazily per process and
  interpolated bilinearly, so every tile agrees exactly on shared edges. Do not go back to 17
  samples per cell: that costs about +40% per tile (budget +30%); this way it is +16%. Only
  blocks up to 6000 m2 outside park/cemetery/industrial/port are terraced (0.4 m at most, faded
  over 18 m); bigger blocks would make cliffs. Tiles changed because the whole city ground shifts
  by up to 0.75 m. `TileContext.height` is `Ground.height`; `Ground.surface` adds the street
  ribbon lift (`STREET_LIFT`, highest where streets overlap) and is now the one height reader for
  dressing, gates, street trees, cameras and the index focus. Doors, shop fronts and awnings use
  the surface 0.5 m in front of the wall, because buildings stand 0.15 m back from the street
  edge: sampling at the wall would leave the threshold one lift below the pavement. Walls and
  wall-mounted pieces stay on `Ground.height`.
- **Street surfaces and paint** (prompt 14, `city/paint.py`, `[streets]` and `[streets.surface]`):
  a street ribbon takes its material from its kind; a street whose representative point is in a
  village district gets `earth`. Paint is a list of flat polygons in `plan.paint`, not ribbons:
  a marking is clipped once to the carriageway (`street buffer - sidewalk polygons - the
  promenade strip`), so the test can prove every piece lies inside it. Edge lines use the widest
  sidewalk on each side, not the designed width, because walks narrow at tight streets. A zebra
  bar runs along the street (3 m long, 0.55 m wide) and repeats across the carriageway, so a
  boulevard gets one set on each side of the promenade; crossings sit just outside the interval
  where the other street's ribbon covers the center line. Lift paint 0.03 m above the ribbon
  (0.01 m flickers in aerial views). `plan.json` does not list paint or surfaces, so the
  fingerprint stays on `tiles/*`.
- **Raised walks** (prompt 13, `city/walks.py`, `[streets]`): a sidewalk is `block.buffer(width)
  - block` clipped to the streets' side strips; the side strips leave 5.5 m of asphalt, so a 9 m
  street gets 1.75 m walks and a 12 m street keeps the 3.2 m design width. `CityPlan.walks` stores
  every piece with its street, side and actual width for prompt 14's carriageway lines and later
  arcades, hedges and parked cars. `Ground.surface` adds `curb_height` on a walk, so doors, trees
  and lamps stand on it; doors show a plinth because the building base is not raised. Do not tile-
  clip the polygons: each piece is drawn by the tile holding its centroid, and clipping would add
  a visible cut face at every tile edge. The curb is a vertical skirt from the walk top down to
  the ground, with outward winding (the first version had it reversed and the curb was invisible).
  The boulevard promenade is 8 m wide in 64 m pieces under the middle tree row; keep the piece
  short so a tile's mesh stays local.
- **Family names** mix real lists with made-up nisba names built from Arabic roots and patterns
  (Hamdi = 1a23i from H-M-D), with sound rules and a rude-word blocklist, because random syllables
  sounded Japanese or Italian. D5 can map roots and patterns to Arabic script.
- **Street dressing** (`city/dressing.py`) is built tile by tile from kit pieces and never stored
  in the plan. Which piece plays each part is data: `[dressing.roles]` in `styles/maghreb.toml`.
  Kit pieces are named `<kit>/<piece>`; anchors are explained in `mesh/props.py` and SPEC 6b.
- **Instancing** (`EXT_mesh_gpu_instancing`): one model drawn many times keeps tiles small.
  Blender 3.6 does not read it, Blender 4 and 5 do; `tools/blender_import.py` handles both.
- **Thin cloth and canvas** need real faces on both sides (`add_sheet` in `mesh/builder.py`):
  a double-sided material alone showed black undersides.
- **Vertex colors** are written as 8-bit RGBA (a quarter of the size of floats).
- **Night mode** in the viewer: materials with an `emissive` color glow; lit window glass
  (`glass_lit`, chosen per flat by the household, prompt 21) lights up and `glass_dark` stays dark;
  kit windows light through their `*_pane_lit` pieces, shown at night only; the nearest lamps get
  real lights.
- **Golden hour in the viewer** (prompt 8): the light menu is `PRESETS` in `tools/viewer/index.html`.
  Noon copies the old values exactly (0 pixel difference); golden copies Blender's sun (azimuth
  225, elevation 14). Two traps: three mixes fog *after* tone mapping, so `scene.fog.color` must be
  the display hex (`0xf2d2b0`), not a linear sky value, or the sea gets an orange band; and a
  change of `renderer.toneMapping` needs `needsUpdate` on every material, or they keep the old
  shader. The shadow box is asymmetric at a low sun (700 m across the light, 150 m along its up
  axis) and snaps per axis; PCFSoft with bias -0.0002 and normal bias 0.35 is clean. The sky is a
  dome shader (with three's tone-mapping includes) that only golden shows; noon and night keep the
  plain clear color. The street view looks away from the sun and its 14 degree light cannot reach
  into the canyon, so cast shadows show in the aerial view, not on the road.
- **Ambient occlusion and quality** (prompt 9): one `EffectComposer` serves every mode. Day High is
  RenderPass, GTAOPass, OutputPass, SMAAPass; night enables only UnrealBloomPass on the same chain;
  Fast day is the plain forward renderer and Fast night the bloom-only chain. The quality menu
  defaults to Fast on phones and on SwiftShader and to High on a desktop; `?quality=fast|high`
  forces it. Keep the AO buffer near 1 MP: full resolution at 1280x720 on a normal screen, scaled
  down on a retina buffer, because full 2560x1440 AO cost 45 ms/frame on the M1. SMAA must come
  after OutputPass so it works on display colors. The sky dome is BackSide while the AO normal pass
  is FrontSide, so trees against the sky get no halo. The Poisson denoise needs radius 24 and 48
  samples at that buffer size; the default 10 and 24 left a grainy band along wall bases.
  `?perf=1` logs the frame time and the render cost over 120 frames.
- **Street camera fallback** (prompt 9): when a world has no `views.street` in the index, wait for
  every tile within 200 m before `placeStreetCamera` casts its rays. Otherwise a far tile still
  loading can change the chosen camera from one load to the next.
- **Blender 5**: the physical sky is `MULTIPLE_SCATTERING` with `aerosol_density`. The compositor
  is a `CompositorNodeTree` in `scene.compositing_node_group` and ends in a Group Output, not
  `scene.node_tree` and Composite: add an output socket to `group.interface` first, then the
  Group Output node shows its input. `setup_haze_group` rebuilds the 3.6 chain with the unified
  5.x nodes: `ShaderNodeMath`, and `ShaderNodeMix` set to RGBA, where every data type has its own
  socket, so pick sockets by name plus type ("Factor"/VALUE, "A"/RGBA). Color Balance keeps
  its method in a menu socket (default Lift/Gamma/Gain, the 3.6 method) and its Lift/Gain values
  in RGBA sockets; the old `correction_method`, `lift` and `gain` properties are gone.
- **Leafy trees** (`mesh/trees.py`) are instanced kit pieces, three variants per kind, each with its
  own stream. Undressed tiles keep the light 3-clump tree from `tree_mesh`: merging 200-triangle
  trees 7,900 times into a tile would make it huge.
- **Headless snapshots** run on the CPU and are slow. Use a small `radius` in `--query`.
- **Bougainvillea** (`mesh/climbers.py`, prompt 7) is a curtain of 4-face bracts on a staggered
  grid, not blobs: 38 to 40 clumps from the wall top to a ragged hem, 2 or 3 bent 4-5 sided stems,
  three magenta shades and a few green leaves, 250 triangles per variant, its own stream. The
  clump and tube helpers moved from `trees.py` to `mesh/plants.py`; `clump(..., turn=0, roll=...)`
  keeps wall pieces thin in y. Big clumps spaced apart look like leaves, so density comes from
  overlap, not size. Numbers are in `[dressing.climber]`.
- **Generated textures** (prompt 18, `mesh/textures.py`) wrap only if every step wraps: value
  noise interpolates on a periodic lattice, `_blur` is an FFT Gaussian (Pillow's `GaussianBlur`
  refuses mode `F` on Pillow 13), and strokes go through `_WrapCanvas` at nine offsets. Pattern
  phases matter too: roof tiles start half a tile in from the edge, joints are measured in
  pixels, and the concrete seam is centred at +0.5 px. Keep every image neutral grey; the
  palette color supplies the color. `texture-sheet` is the visual check, and the encoder keeps
  the smaller of PNG and JPEG.
- **Every home's door and windows** (prompt 20.1, `Dresser.door_spot`, `city/openings.py`): new
  choices never draw from `rng("b", k)` and are appended after the old pieces, so a test can dress
  with `every_home` off and on and require the old list as a prefix of the new one. `door_spot`
  replays `_street_side` on a fresh `rng("b", k)` and goes through the same `_entrances` code the
  dresser places doors with; prompts 44, 71 and 79 must read doors there. Ground pieces in the
  overlap boxes count from the door or shop threshold (no ground call). Each `Ground.height` call
  costs about 0.25 ms whatever the number of points (the city edge distance, terrace blocks), so
  the first version made the capital's tile work +20%: thresholds on open ground and garden paths
  now read `Dresser.drawn`, which caches the terrain mesh corners and is seeded by each tile's
  terrain grid (no extra ground call); tile work is now about +12%. Draw paths on the terrain mesh
  (`Ground.drawn`), not on `Ground.height`: the 8 m mesh lies up to 0.18 m above the true height
  on steep terraces, and a ribbon draped on the true height sank under it. Instanced pieces that
  repeat on every slab must be cheap: boxes cost five faces where one shows, and the first slab
  window (270 triangles, 8 variants) added 180 KB per estate tile; one-sided quads (`_faces`) cut
  that to about 30 KB. Instances cost 40 bytes each (translation, rotation, scale as floats).
- **Impasses** (prompt 20.2, `city/impasses.py`, `[impasse]`): `Parcel.frontage` is not a "has a
  street" flag (it measures the block edge, which in the old town is also the city wall and the
  mosque site), so "landlocked" is decided exactly as the dresser sees a facade: the lot inset 0.15 m,
  a wall of `min_front` m with a street surface 1.6 m in front of its middle; a souk wall needs
  `souk_front` (8 m) because the shop takes its middle and the house door must fit beside it. A lane
  runs along a whole lot side (the door may stand anywhere on the wall). One `_Block` per block cost
  9 s on the full capital (per-call shapely overhead x 1,700 blocks); all blocks now advance together,
  one lane per block per round, each step one vectorized call over the active blocks only (a medina
  block needs up to about 300 rounds): 4.3 s. Cutting lots with round joins put arcs of 16 walls at
  every lane bend: the old-town tile got +29% triangles (walls, plinths, parapets); cut with mitre
  joins and simplify 2 cm: +11%. Aim the mouth's first point at the street's center line, not along
  the lane: by an alley's flat dead end it ended outside the street. A branch never starts in a
  mouth node (it would open on the street a second time). Recheck every lot a later cut changes: it
  can take the wall a lot had its door on. Covered mouths and arches use the alley rules (both houses
  tall enough), so few are drawn (quick capital: 39 lanes covered, 6 rooms, 1 arch). The main
  facade is now the best street wall long enough for a door (`DOOR_WALL` 2.3 m): five residential
  houses had a 2 m street wall as main facade and no room for a door on their long arterial wall.
  Cost: full capital 34.8 s -> 42.5 s in the same minutes (planner 10.6 -> 15.5 s, tile work +12%),
  `build --quick` 9.1 -> 9.4 s, old-town tile 6.06 -> 6.74 MB.
- **Lit windows** (prompt 21, `Dresser._light`): light decisions run after every piece is placed
  and swap names only, so the day list is unchanged (a test dresses with `lit_cfg` off and compares).
  Key a flat on geometry (yaw, floor from z, stair section from the block's frame), never on the
  stair door spots or on a per-building list of groups: the `every_home` off/on prefix test dresses
  with different piece sets, and a shared per-building stream would shift every decision. Panes go
  right after their window in the list, for the same prefix reason. Kit windows have no glass
  material and their near-black glass (roughness 0.9) cannot match `glass_dark`, so a pane in front
  of it would change the day picture: the viewer hides `*_pane_lit` nodes by day (day difference
  0.00) and Blender hides objects drawn only in `glass_lit`. The mashrabiya balconies got no pane: their dark
  back panel at z -0.52 sits 1-4 mm behind lattice faces, too tight to avoid z-fighting. Twins first
  cost +8% on light tiles (each twin a full mesh copy); `write_glb` now reuses the accessors of a
  part dict seen before (twins share their dark piece's part dicts): worst +2.0%. At night the
  viewer keeps lights out of the fog (`CLEAR_AT_NIGHT`: `glass_lit`, `lantern_glow`, `tr_glow`,
  `m.fog = false` with `needsUpdate`, back on by day): fogged, lit windows faded toward the dark sky
  from the air, while real lit windows stay warm points across a city. The headless SwiftShader
  snapshot renders lit glass as grey dots at aerial distance; check night glass in a GPU browser.
- **Arcades and iron balconies** (prompt 22, `city/arcades.py`, `Dresser._colonial`): a placed piece's
  +x runs against its wall's direction `u` (+x = (cos yaw, sin yaw), front = (-sin yaw, cos yaw)), so a
  piece that is not centered on its anchor (the corner piece) must be turned accordingly: the first
  version laid every corner piece back over the last bay; the test now checks that corner pieces
  overlap no bay. Symmetric pieces hide this mistake. Non-uniform instance scale (`Placement.stretch`,
  along the wall only) is how one bay piece fits 3.2-4.4 m without changing its height; three.js and
  Blender handle it. Layout the arcade before every home's new doors and give those doors the pillars'
  boxes (wall to pillar), or the doors land behind pillars; the `every_home` prefix test stays exact
  because the arcade depends only on the old street pieces. Doors on the same wall as a cafe need the
  cafe tables pulled under the arcade (`cafe_reach`), else two tables spanning 3.7 m forbid every
  pillar position. Collinear neighbours are not obstacles in front of a wall: find them behind the wall
  line beyond its end (`_side_gap`) and meet half way across the 0.3 m gap between lots. Real wall
  lengths often cannot be cut into 3.5-4.0 m bays (4-7 m, 8-10.5 m...): about half the bays use the
  relaxed 3.2-4.4 m so the arcade stays continuous. Ground pieces must be measured from the drawn
  surface under them, not from the building's highest ground point (wall lanterns were dropped by
  mistake). A square corner piece on a corner 4 degrees off square leaves a sliver: turn it to the
  bisector and close its inner sides. Boulevard palms stand 2.5 m inside the street edge, inside the
  arcade: `tree_spots` moves them at tile level (plan untouched) and turns a moved date palm so its
  lean (toward the piece's -x, about 0.1 m per meter) points over the street, else it can lean back
  into the cornice. The bands must cover the bays turned into a side street too (a corniche palm stood
  in one). Cost: worst quick tile +7.6%, full capital 44.1 -> 43.3 s (CPU +3.5%).
- **Building massing** (prompt 23, `city/massing.py`): runs after households and souks and only sets
  `Building` fields or cuts a footprint inside its old outline, so a test re-plans with `apply_massing`
  patched out and compares buildings, households, souks, streets, trees and stats. Everything that
  reads height or floors goes through `masses(b)`, `floors_at`, `wall_height` (plain buildings return
  `b.height` exactly, so their spans and pieces do not move by a float bit). Draw a massed building as
  one solid: the footprint ring once (mass corners inserted), each segment to the tallest mass there,
  in groups with `add_walls(only=...)`; u stays measured along the whole ring, so bands and plinth
  run on across a step. Drawing each mass as its own box put the base wall (up to its terrace parapet)
  and the set-back floor's wall in one plane, same facing: z-fighting. `_coplanar_overlap` in the tests
  catches it, and it caught a shapely `union` of two rectangles sharing an edge that left a valid
  zero-area spike (villa walls drawn twice): build such outlines from exact corners. A cut corner's
  face stands back from the street, so the dresser's 1.6 m probe missed it (no windows, no arcade):
  faces probe from the old corner point (`massing.probes`, also in `_arcade_zones`). A mitred arcade
  at a 45-degree turn would overlap its terraces by m2 at 3 mm apart: a pier piece (`arcade_bend`,
  `arcade_bend_round`) fills the wedge instead; a run ending at a corner or bend piece holds that end
  when it must shrink (an 8.8 m wall between a neighbour join and a bend lost its bend). A rounded
  corner's middle face stands about 3 m inside the block corner, so its pillars fall on the lot, not
  the sidewalk: allowed for faces. Window walls are checked `window_half` 1.3 m each side: at 0.7 m a
  2.54 m slab window hung past a step joint on a clipped slab. Lead review: the lot corner a cut
  leaves open is paved (`Building.apron`, `apron_mesh`, `Ground.apron_top`). Draping it on its outline
  missed `surface` by up to 5 cm (the two streets' lifts blend over it) and finer cells did not fix it
  (the sidewalk rule at the street edge is a step): `Ground.surface` now interpolates the drawn
  triangles themselves (`ground.apron_cells`, shared with the mesher), so they agree exactly. Draping
  each cell with `add_draped_cap` cost +16% on a tile and a street-direction query per cell: one
  shared-vertex mesh per apron, one paving direction. Give `add_skirt` a closed ring: on an open one
  its `np.allclose` end check (relative tolerance 1e-5, so 7 cm at x = 7000 m) merged two real corners
  and crashed the full capital. Tank stands are an instanced piece
  (as geometry, about 6 KB each); lift rooms are boxes. Cost: worst quick tile +6.8% with the aprons, full capital
  47.0 -> 48.3 s back to back (planner 15.8 -> 16.3 s, CPU +7%).
- **More greenery** (prompt 24, `city/greenery.py`, `[greenery]`, `[dressing.hedge]`): new trees are only
  appended after every older tree (the dresser keys a tree's variant on its index), in a step that runs
  last in the planner, so the massing test re-plans with `greenery` patched out too and checks the
  old trees as a prefix. `mesh.props` imports `city.model`, so `city/greenery.py` imports `dressing` and
  `ARCADE` inside its functions (a top-level import loops when the kit is imported first). Arterial
  trees reuse the dresser's own rules instead of copies: `dressing.arcade_zones`/`band_push` (moved out
  of the `Dresser`), `stair_columns` and `path_to_street` (pure geometry) for the stair paths, the lamp
  stations of `_lamps`; the test checks them against the real dresser (lamps, sampled slabs' paths,
  `tree_spots` moves none). A colonial sidewalk is 3.2 m and the arcade 2.5 m deep, so no tree pit fits
  beside an arcade (trunk needs 2.97 m from the wall, the curb is at 3.2): every colonial candidate lies
  in an arcade band. Lead decision (rule): modern arterials get street trees, arcaded colonial ones do
  not; the arcades are their shade, as on real arcaded streets. Residential arterial walks (2.4 m, attached
  houses) fail `wall_clear`; suburb ones would add about 300 trees on the full capital (style list).
  Villa gardens are cut on the terrain's own triangles: the lots are not planar (median 18 cm off a
  plane, cell twist up to 27 cm), so cells only or a coarse drape would sink under the terrain. With the
  house cut out it cost about 2.5 KB per villa (66 vertices, 73 triangles; suburb tiles +31-37%, worst
  2.41 -> 3.29 MB); lead review: keep the part under the house (hidden by it), about a quarter fewer
  triangles: suburb tiles +25-30%, worst 2.41 -> 3.13 MB. Hedges first used 2 m pieces (33 per villa, +380 KB a tile); pieces of up to
  8 m (the piece is plain along its length, untextured like the crowns) cut that to 11 per villa.
  Hedge corners: a later run stops at the body of a run already planted (not at a computed offset,
  which left 3 m gaps at gentle bends); slivers remain only at 16-20 degree lot corners. Citrus crowns
  keep the Q1 budget (60-200 triangles) plus 14 oranges (8-face clumps, 112 triangles) on their own
  stream `("props", "tree", "citrus", variant, "fruit")`. Cost: full capital 51.4 -> 49.0 s back to
  back (noise; planner +1 s), quick build unchanged.
- **Parked cars** (prompt 25, `mesh/vehicles.py`, `city/parking.py`): `Walk.street`, `side` and `width`
  hold for ONE side of a block only (a sidewalk polygon wraps its whole block and is filed under the
  street nearest its representative point): the boulevard had no sidewalk filed at all, so its edge
  lines lay under the raised walks and its carriageway included them. Measure per side instead
  (`walk_extents`: the sidewalk at the street's edge, min(district `sidewalk_width`, (width -
  min_carriageway) / 2)); `_carriageway` now cuts every sidewalk on the street. Measuring the band
  with a segment intersection was exact too but 3 times slower. The planner left grid streets lying
  on the boulevard's surface (parallel, 8.9 m off its center), one poking out past its end: "a street
  that meets this one" must skip streets lying on it, wholly or running along inside it (`lying_on`),
  or a whole side reads as a junction (lead review: the boulevard had 3 cars, now 6, all it holds).
  Check each car exactly against the obstacles instead of adding a sample of margin to each.
  Instancing cannot recolor, so the 4 color pieces of a type share every part dict: `write_glb`
  writes the geometry once and a color costs about 1.1 KB of JSON. No UVs on car parts (-25% bytes);
  hidden tread faces and a mirror's back face left out; first version +10.7% on a quick tile, now
  +8.8% worst (budget 10%): tile bytes are the tight budget here, not triangles (+7.1% drawn). Do not
  drop the normals to save more: three's GTAO normal pass reads them. A run is laid out whole on
  0.5 m samples (obstacles as point distances, then an exact kit-bounds check per car), so tiles
  agree; replaying a whole `entrances` for every building along a run cost +16% tile work: `front_of`
  replays `_front` alone (its draws come first on `rng("b", k)`), door zones only where a sidewalk is
  narrow enough for them to reach the row, stair paths only from blocks facing the street. Cars sit on
  the surface under their axles with `Placement.tilt` (the instance rotation is yaw after a tilt about
  the piece's glTF z); sitting on the lowest point sank the other end 12 cm on a 7% street. Cost: full
  capital 47.4 -> 51.8 s back to back (CPU +12%, all tile work), `build --quick` 10.6 -> 11.1 s.
- **Benches, kiosks and fountains** (prompt 26, `mesh/furniture.py`, `city/squares.py`): the promenade is
  not all free paving: in the plan the ring road and the corniche run over its two ends (the boulevard
  starts on the ring's center line) and a cross street over its middle, so furniture uses islands (the
  promenade less the surfaces of streets crossing it, not those lying on it). A grid street lying under
  the boulevard puts its own lamps on the promenade (older quirk, not fixed here: one stands 1.3 m from
  the quick fountain; for CP3). The tree piece's box as a crown left no kiosk spot in a 9 m row (crown
  base 2.1-4.1 m, kiosk 2.8 m): crowns are circles of `crown_cover` x half width, and kiosks are placed
  before benches (a bench gives way): full capital 0 -> 2 kiosks. Colonial cut corners all lie in arcade
  bands, so check the band and the surface before dressing the buildings around (kiosk search 0.52 ->
  0.01 s). Full water curtains round a column read as blue glass in the viewer (water opacity 0.82):
  thin double-sided streams instead. The viewer's sea test reads an instanced mesh's box in piece space,
  where a basin's water lies at 0.46 m: it now skips instanced meshes and `water_pool`. The door bench
  role is now `door_bench` (same pieces and draws), so `bench` is the promenade's mix. A fountain removes
  the planned trees it replaces through `tree_spots`, so parked cars and tiles agree. Cost: 0.36 s per
  process on the quick capital, 0.87 s on the full one; full capital 52.4 -> 53.7 s, worst quick tile +1.6%.
- **People** (prompt 28, `mesh/people.py`): build a figure as a skeleton plus an outfit; limbs as one
  chain of mitred rings (no open joints at a bent knee), robes as one loft from the neckline to the
  hem (a separate torso and skirt cost 16 more triangles for an unseen seam). A seated person's real
  shin is too short for a 0.45 m seat with level thighs (the real thigh slopes down and squashes): the
  sit pose places the knee at seat + knee radius and lets the shin reach the ground (2-6 cm longer;
  it reads right). A hood is the head's ellipsoid scaled up with the face faces removed; with rings at
  -45/0/45 degrees the opening reached the crown and the hood looked like a bald head: rings at
  -45/15/50 put its top at the brow. An octagon's flat sides lie inside its ellipse, so rings fitted
  round legs grow by 1/cos(22.5 degrees) or a shin pokes through a skirt. A skirt above the knee needs
  the thighs drawn. Check shapes with a throwaway z-buffer render first: a painter's sort showed the
  head through its own hood.
- **People in the streets** (prompt 29, `city/crowd.py`, `[people]`): tile bytes are the tight budget, not
  triangles: each figure a tile shows costs its mesh (about 14 KB as written), so all 26 cost 500 KB and a
  light tile (300-800 KB) can afford 2-5. A cast by people count passed the quick build and failed the full
  capital (+15% on 360 KB tiles); `_cast` now keeps the most frequent figures within `bytes_share` of
  `tile_bytes` (within 10% of the written size; people are estimated on the high side). A person belongs
  to the tile holding its origin, but who gives way must agree on both sides of an edge: candidates come
  from sources that do not depend on the tile (street stations, seats, shops), and one gives way to any
  earlier candidate too close whatever becomes of that one (no chain), measured with its pose's largest kit
  box so a tile may still swap the figure. Obstacles across an edge come from a halo (`wall_pieces` of the
  neighbours' buildings, their street props, cars, squares, trees). Kit boxes are too coarse for arcade
  bays, trees, lamps and kiosks with awnings: test the piece's triangles in the person's height band, as
  plan hulls (an upright face is a line) in an STRtree; a union of buffered hulls cost 0.57 s per tile.
  Drawn walks sit up to 5 cm off `Ground.surface` between their 15 m outline points: people stand on the
  walk's own triangles (`_walk_z`); a walk piece is drawn by the tile holding its centroid, so the test adds
  the neighbours' walks. Door benches stood on the terrain at the wall, about 0.2 m below the souk ribbon
  (a sitter's feet sank): `_front` now sets them on `front_surface`, and `tounes/bench_sbs` (ground anchor)
  no longer stands half inside the wall. Doukkana walls are a few mm off straight: sitters 0.26 m out.
  A settlement without streets (quick village 5) crashed `Squares._sabil_fits` (`surface_tree` None): squares
  now query through `_streets`/`_buildings` and give such a place no sabil, kiosk, fountain or bench.
- **The kasbah** (prompt 30, `city/kasbah.py`, `[kasbah]`): a landmark that takes space shifts every later
  house, so every later household (one sequential stream) and every massing choice keyed on the building
  index re-rolls: about half the full capital's tiles change and light tiles swing by car, figure and
  door variants (+8.7% worst, budget 10%); a sample-count guard in a test (pillars on paved corners) fell
  from 6 to 2 for that reason only. Draw the alley crossings first and drop the ones in the kasbah's cut:
  the rest of the old town keeps its crossings. Cut the kasbah rectangle by the old town's outline so its
  outer side IS the rampart line, and leave the outer wall plus the kasbah towers out of the rampart: no
  doubled wall, and the towers close the rampart's ends. A gate's souk must start at a crossing wholly in
  front of the gate tower: the nearest crossing could lie beside it and the street clipped the tower
  (two full-size cities). Battlements: a building with merlons gets no parapet (`roof_layout`), the
  breastwork stands on the roof deck flush with the wall face (no face drawn twice), and each side after
  the first starts `depth` in, so no two boxes share a corner square. A sabil by a monument with
  `arches` keeps clear of its doors (it first landed in the kasbah gate). Lit flats were keyed on
  `round(degrees(yaw))`: a wall at exactly x.5 degrees split one flat in two keys by float noise; the key
  now floors `degrees + 0.5 + 1e-7`.
- **Covered souks** (prompt 31, `city/covered.py`, `mesh/vaults.py`, `[covered_souk]`): one rule, `Covers`,
  built once per city by `TileContext` and handed to the dresser (`dresser._covers`); a dresser alone builds an
  equal one (the test compares stations, heights and lanterns). Nothing is stored in the plan. Souk lines are
  Voronoi zigzags that turn 40-100 degrees at every alley junction, so a vault cannot run straight on: rings at a
  bend are mitred on the bisector (up to `max_turn` 50), sharper bends break the roof (an open crossing), and
  every other station keeps `(w + band_depth) tan(turn / 2)` from a bend, or the inner side of the segment folds
  back over itself. Arches keep clear of bends too, so a bay across a bend is 12-14 m (it reads as the vault
  turning). A run of owned segments i0..i1 needs stations i0..i1 + 1: the first version passed one too few and
  dropped the last segment of every run; the seam test (left tile + right tile == one big tile, same area) caught
  it. Sun through the openings: the viewer's noon sun is 40 degrees high and a shadow texel 0.34 m, so a 0.8 m
  hole through a 0.3 m shell with a 0.3 m curb (a 0.6 m deep shaft, 0.7 m of sideways shift) let almost no light
  in; 1.0 m holes, a 0.25 m shell and a 0.15 m curb let about 0.45 m2 through each, still faint in the headless
  snapshot. Nothing pierces a roof: a kit box is tested against the roof's underside (the intrados inside the
  vault, the fill bottom over the impost bands); every wall piece reaches the band zone, so on a souk wall all
  stays under the band; upper windows behind the vault go (hidden anyway), awnings and lamps are lowered
  instead (`lower`). Cost: about 26 triangles per meter; worst tile +6.0% quick, +6.8% full; capital time
  unchanged (50.0 -> 50.9 s, noise).
- **Boulevard landmarks** (prompt 32, `city/landmarks.py`, `mesh/landmarks.py`, `[landmarks]`): merging lots
  removes buildings, so every later building index, household and massing choice shifts; on the full capital
  light tiles swung +10-17% by door and shutter variants (re-rolled door colors), not by the landmarks. Read
  "boulevard-facing" as the merged site facing the boulevard: a colonial block offers 20-30 m of frontage,
  so a cathedral needs the lots behind the front ones. Check containment with the real footprint, not its
  bounding rectangle: the rectangle with a 1 m2 slack poked 0.15 m into the ring road at a rounded corner.
  Lot unions can be MultiPolygons by hair gaps (cuts that do not quite meet): close with a 2 cm grow and
  shrink. Two facades facing each other across a 34 m boulevard cannot be framed by one camera: one view per
  landmark. Draw in a local frame (s along the facade, d into the lot) shared by planner and mesh, so the
  footprint and the drawn shape agree. Bytes, not triangles, are the cost: a non-indexed cap or face costs 3
  vertices per triangle (32 bytes each); sharing corners (`np.unique`) cut the two landmarks from about 395 to
  335 KB. Parking "fronts" with clearance 0.0 never block a car (`distance < 0` is never true): the landmark
  steps use 0.05; the shop and cafe fronts of prompt 25 still use 0.0 (a latent bug, left for review).
  Metallic dome materials band with the viewer's sky reflection: keep patina matte.
- **Railway station** (prompt 33, `city/station.py`, `mesh/station.py`, `[station]`): cutting ground before
  `make_blocks` shifts the whole plan, not only the lots it takes: the impasse step advances every block
  together, so changing the port's blocks changed old-town lanes and lots too (first changed parcel: an
  old-town one), then every later household and door color. A light colonial tile grew +31.6% from re-rolled
  door, shutter and cafe variants alone (22 piece kinds it did not show before), none of it station geometry.
  The quick capital lies on an 8% coastal slope: no site had less than 3.8 m of fall under a 64 m head
  building, so the station's ground is graded level (`Ground`, `core` = convex hull of head building and
  platforms, level half way between highest and lowest). A plain smoothstep over 24-40 m bent the ground
  enough to sink 15 m sidewalk triangles under the ribbon; the second derivative of `graded + w (L - graded)`
  carries `2 w' graded'`, so on a slope a wider band does not cure it alone. What works: the hull (a T-shaped
  core put a kink in the distance field at its inner corners), smootherstep over 100 m, and walks in that band
  drawn with 10 m outline points (`Ground.walk_step`, shared by mesher, crowd and test: margin 0.109 m for
  0.075 needed). The station tile must stay under +10%: 1 m track samples thinned to what bends need (2 cm)
  halved the rails; posts without ends, shared-vertex strips for canopies, valances, slab sides and dial rings.
  `keep_off` filters placements last in `build_tile` by their kit box, so no rule upstream needs to know about
  the tracks. The people test counted a string lantern hanging 4 m up as a piece under a walker's feet: it
  now skips pieces more than 2 m above the person.
- **Harbor** (prompt 34, `city/port.py`, `mesh/port.py`, `[port]`): a height field cannot hold a vertical wall,
  so the ground steps at the wall line (`Ground` is discontinuous there by design) and the terrain cells a wall
  crosses are cut by the raised side and drawn in two parts, each on its own side's ground; only vertices lying
  on a wall use `Ground.side_height`, so the drawn terrain equals `Ground.height` everywhere else (the test checks
  every vertex of the root tile). Without the split, the triangles crossing the wall left a 2 m sloping strip
  above the water in front of it. The corniche's center line IS the coast (`land`'s 0.8 m contour), its sea half
  lay on the natural beach: the level core takes the whole corniche, and next to a quay's ends the level band
  lifts the corniche's sea edge, so a decaying sea wall runs on along it. Planning last and reading only districts
  and land moved nothing (plan parts changed: landmarks, port, stats). Level must be exact on the quay edge:
  points from `segmentize` fall 1e-12 m outside the core polygon, so the blend uses `w >= 1.0`, not "inside the
  core". Shared-vertex strips (`_grid`, walls, kerb, crown wall) cost about half of `add_skirt`/`add_quads`. The
  quick build (520 m round the center) does not reach the harbor: pictures need `--build-args "--area capital
  --out output/harbor"`. Bytes: sea tiles that receive the breakwater grow far past +10% (full capital: +52% on a
  322 KB sea tile, +166 KB: rubble loft, 815 armour stones at 40 B, crown wall); every other tile stays within
  +7.6%. A throwaway numpy z-buffer render of `build_tile` parts (no water) caught the composition and the
  stones' scale before the two real pictures.
- **Boats, cranes and cargo** (prompt 35, `city/moorings.py`, `mesh/boats.py`, `mesh/cranes.py`, `[port.props]`): a
  new piece kind in a light tile costs its whole mesh, and in glTF each part (material) also costs about 0.8 KB of
  JSON: a 280-vertex boat in 9 materials wrote 15 KB, 7 of them JSON. Cut materials before vertices (a fit-out's
  deck joins its woodwork; the eye is one black almond). Pieces of one family can share part dicts (like the
  cars): the three fishing boats share one hull (renamed strake color only) and the two container stacks share
  all geometry, so a tile writes them once; a fit-out must not use the hull's materials or the merged part is
  no longer shared. One crane model per harbor. Even so, a light harbor tile showing the commercial quay and the
  fishing port together (crane, containers, crates, rails, four boats) grows +19% on the full capital (62_107,
  488 -> 581 KB) and 63_107 +15%: an open question for the lead. The planner's footprint is a `[port.props]
  size` envelope that every piece is built to fit (the test checks the kit vertices; a crane only below 1.5 m,
  its boom reaches over the water), and the draft comes from the same table, so planner and pieces cannot drift
  apart. The headless SwiftShader snapshot hides everything below about 1 m above the sea at a grazing view
  (fishing hulls, decks, a trawler's dark band) while the GPU viewer shows them: judge low harbor things in
  the real viewer (`python -m citygen view`), not only in `before_after` close-ups (unshared hulls gave the
  same picture, so it is not the shared parts). Commercial quay by the mouth, fishing port in the sheltered end:
  realistic and it reads in the "port" view (cranes in front, the fleet behind).
- **Seafront promenade** (prompt 36, `city/corniche.py`, `mesh/corniche.py`, `[corniche]`): the corniche's center
  line is the city limit, so its sea half and the beach lie outside the city and the ground there is the natural
  terrain: the planner can find the water line from `terrain.height` before any `Ground` exists. A walk's top
  normally follows the ground under each point (h + lift + curb); across the promenade that is a 0.65 m cross
  fall (the street lift ends at the corniche's edge and the beach falls away), so a seafront walk is level across:
  `Ground._walk_top` takes the walk top at the nearest point of the stretch's curb line (`Walk.edge`, one line
  shared by all its pieces, so pieces meet at one height). The sea wall is then only the walk's skirt in other
  materials (coping band, stone), down `foot` m under the ground. A width rule with a step (8 m, else 10 m
  where the sand is short) zigzagged the wall where the room hovered at the threshold: `width_for` is
  continuous and widths are averaged over five stations. Side streets ending on the center line graze the band
  with a corner of their surface: they break it only above `cross_area` m2, or the promenade had 8 m holes at
  every junction. The people test adds the neighbours' walks to find the drawn floor: it must add their seafront
  pieces too (`front_meshes`). Bytes: the kit's blue bench (43 KB a tile) took half a light tile's budget, so
  the role `seafront_bench` keeps the iron bench only; the railing as shared-vertex bars is 160 vertices (the
  first, with `add_triangles` bars and lozenges, 1,250 vertices, 44 KB). Two light sea tiles of the full capital
  (60_106, 68_106: the coast runs along the tile row edge y = 54,272 m, so they get the promenade's sea half)
  grow +18-20% (about +45-50 KB: bench, lamp, railing, one figure, paving); quick tiles +5.1% at most. The
  headless snapshot hides the narrow beach and the steps' lower treads (under 1 m above the sea).
- **Seaside cafe terraces** (prompt 37, `city/terraces.py`, `[corniche.terrace]`): only 5 of the 24 quick buildings
  on the corniche have their main wall there (`FRONT_PREF` ranks a side street higher), so the land side gives few
  cafes; kiosk cafes by the railing carry the corniche view. A seaside cafe is decided after the door's draws and the
  door pieces dropped (`del out[first:]`), so `rng("b", k)` makes the same draws and the windows stay; a colonial
  cafe there keeps its draws with `_cafe(tables=False)`. The parasol stands in the table's hole (one placement at
  the table's point), so the people test must ignore a sitter's own parasol pole (`Crowd._shades`) and the overlap
  test pairs them. Obstacles come grown by `Squares` `piece_clear` (0.2): a canopy beside a kiosk needs that too.
  The sea edge bends between stations: place railing-side tables with the width at their own station, not the gap's.
  Passing the whole stretch's pieces to `Squares._obstacles` cost 4.9 s per process on the full capital (it sets
  ground heights for all of them): keep only those near the region (1.9 s with the town's sidewalks;
  `Seafront.placements` skips tiles far from the seafront). Bytes: a kiosk cafe added 20% to the two light sea
  tiles (about 300 KB: the promenade's sea half, no building); pieces now anchor only in tiles holding a
  building (`town_tile`), the drinks kiosk has nine plain materials without UVs (29 -> 21 KB) and the parasol
  shares its canvas corners (12 -> 8 KB). Waiters are often left out by `_cast` (no standing figure kept in a
  seafront tile): "if cheap", as asked.
- **Lighter tiles** (prompt 39, `mesh/gltf.py`, `[tiles] quantize`): measure first (`stats --tiles`); on the
  densest tiles the tile mesh (walls, roofs) and the piece meshes are almost 90% of the bytes, JSON 6%, instance
  data 5%. What paid, on the densest quick tile (8.67 MB): 16-bit positions and 8-bit normals (12 of 32
  bytes per vertex), the weld of equal written vertices (roof caps wrote 3 vertices per triangle: roof_white
  1.19 -> 0.59 MB), one bufferView per kind (167 KB of JSON), 16-bit rotations and no SCALE for unit pieces
  (instances 397 -> 250 KB): 5.33 MB; then no NORMAL on flat faces (4 bytes per flat vertex, vertices kept
  split by normal so readers recompute the same flat normals): 4.67 MB. Test flatness on the written,
  dequantized corners, not the float ones (a 6 cm triangle tilts by degrees at 8 mm steps), and keep the
  tinted terrain's smooth normals by name of the case (`smooth`), not by COLOR_0 (kit pieces carry colors
  too). In three.js, GLTFLoader gives meshes without normals a `flatShading` material clone: compute the
  normals and clear the flag before `shared()`, or the first clone seen shades smooth pieces faceted.
  Welding by position alone (dropping the split) would save about 1 MB more but needs every reader to
  shade flat on its own. What did not: sharing coping vertices (flat shading: 96% of coping
  corners turn more than 20 degrees, only 4% could share; smoothing them would shade every parapet face
  wrong), 16-bit UVs (one texture transform per material across tile mesh, caps and pieces, and Blender's
  importer leaves normalized values in the UV map that `blender_beauty.py` reads as meters; doing it cleanly
  needs per-island UV shifts by whole texture repeats, one fixed range per material for Blender's name-based
  material sharing, and rewriting the importer's Mapping nodes, none checkable here without looking inside
  Blender; worth about -0.45 MB on the densest quick tile, not enough for 3.5 MB anyway). Quantize with a
  **uniform** node scale: a non-uniform one exaggerates slopes in the mesh's own space, where three.js
  raycasts report `face.normal` (the street camera looks for `normal.y > 0.7`). Keep float what is thinner
  than a few steps (8.4 mm): `add_sheet` faces (`MeshBuilder.fine`), edges under `fine_edge` (ropes 3.2 cm,
  cables and rods 2.4 cm), and `water` (the viewer's sea test reads the geometry's own box). Gaps that stay
  safe at 8.4 mm: road paint 3 cm, garden ground 2 cm, roof-room doors 2 cm, station paint 1 cm on flat
  platforms. A piece's quantization scale rides on every instance, so a small piece with many copies stays
  float (12 bytes of SCALE per copy would cost more). Twins must follow their dark piece's choice, or they
  stop sharing accessors. With `quantize = false` the build is byte for byte the old one (fingerprint 0
  changed): the way to prove a refactor of the writer. People: the figure budget stays `bytes_share` of the
  tile's float-size estimate but figures cost their quantized size (`piece_bytes(quantized=True)`), so light
  tiles show more figures and still end 25-48% smaller. The souk and street pictures differ by 0.54 and
  0.30 (edges move by under one quantization step), not 0.00; souk on High (GTAO) 1.01 (noise), night 0.20.
- **Level-of-detail tiles** (prompt 40, `mesh/lod.py`, `[tiles.lod]`): the lod1 terrain keeps the full tile's
  8 m points on every tile edge (border cells fanned onto them from a corner with plain sides): a skirt only
  hides a crack where the lod1 edge is the higher one, and the full tiles have none, so a 32 m edge would
  leave slivers wherever the true ground bulges above the 32 m chord. Normals come from the same 8 m
  differences as the full tile, so the edge also shades alike. Cells a quay wall crosses: refining them to
  8 m cost a harbor tile 22% of its full tile; cutting the 32 m cells with `split_cells` keeps the quay edge
  sharp for a few triangles. Ground queries cost about 220 us each in overhead: one query per tile for all
  blocks and one for all ribbons took the lod pass from 13.8 to 7.7 s of CPU on the full capital (about 3%
  of tile time; capital 57-58 s -> 60-61 s back to back). Vertex clustering gives every triangle its own
  corners: crease normals (smooth under 45 degrees) let rubble and domes share vertices (a harbor lod1
  86 -> 50 KB) while walls stay flat. The lighthouse (2 m wide) needs its own 8-sided lathe: a 3 m cluster
  cell mangles it. Block walls take the color of their nearest building per segment (no extra vertices: a
  skirt's quads are apart anyway), or a colonial street turns one grey from afar. Terrain-only tiles are the
  hardest ratio (11%: the full one is only terrain), not the dense ones (3.6%). Debug renders: a numpy
  z-buffer of `read_parts` (painter's order lies with large water quads) cost no snapshot.
- **Viewer level of detail** (prompt 41, `tools/viewer/index.html`): load every lod1 file before any full
  tile. Mixing full tiles in early by distance made every frame draw them while the rest loaded: the full
  capital from the air covered in 6.9 s and settled in 7 s; lod1 first covers it in 0.8 s and settles in
  about 3 s (old viewer: 94 full tiles, 5-7.5 s). Re-rendering the shadow map on each of 200 swaps cost more than
  the tiles; only a swap whose box meets the shadow frustum marks it dirty. Frame time from the air is
  draw calls, not triangles (a full tile is about 180 meshes, a lod1 tile 2-3; GTAO and the shadow pass draw
  them again): 151-168 -> 84-98 ms on High (street 67 -> 35 ms) in headless Chromium on the M1's Metal (`channel="chromium"`,
  `--use-angle=metal`; the headless shell and the Claude browser pane, when hidden, are no use for GPU
  timings). Snapshots stay deterministic because the want of a tile seen for the first time splits at
  1500 m and depends only on the camera; hysteresis only acts once the camera moves. `citygenReady` is
  live (false while tiles load) and `snapshot.py` checks it again two frames later. A quick build is
  small enough that every tile is full in the street and aerial views (old and new viewer: 0.0 and
  0.003 pixel difference).
- **Old-town tiles** reach about 4.7 MB on the quick build and 5.8 MB on the full capital after prompt 39
  (`tile_65_106`; 8.7 and 11.1 MB before).

## Known weak spots

Task Q5 in the roadmap: heavy old-town tiles. Prompt 39 quantized them and dropped flat normals (densest
quick tile 8.7 -> 4.7 MB, full capital 11.1 -> 5.8 MB, all 168 full tiles 310 -> 171 MB), still over the
3.5 MB goal (WORKLOG, prompt 39). The viewer still renders the street view in about 4.6 ms per
frame on High (M1, golden hour), so prompts 39-41 (lighter tiles, level of detail) have room to
work before it matters. Since prompt 20.2 every dwelling in old towns,
villages, residential and suburb districts opens on a street, alley or impasse (full capital: 6,641
impasses, 160 km; none enclosed). The planner is 4.9 s slower for it (15.5 s on the full capital);
cutting several far-apart lanes per block per round would shorten the old town's 300 rounds.
Modern-estate tiles grew +20% to +37% in bytes with their windows (instances plus piece meshes); prompt 39
cut their instance data to 20 bytes per window (16-bit rotation, no SCALE).

## Checking the look without wasting tokens

- Best: Ali looks himself. `python -m citygen view` opens the browser (camera spots in the top
  menu, Night button, click a house). Or open the tiles in Blender:
  `/Applications/Blender.app/Contents/MacOS/Blender --python tools/blender_import.py -- output/bodjantouna-42/tiles`
- One command for a visual change: `python tools/before_after.py --view street` (last commit above
  the working tree, same camera, labelled, difference printed; 0.00 = identical). Options:
  `--ref`, `--cam x,y,z --look x,y,z`, `--kit-sheet --frame PIECE`, `--build-args`, `--no-build`.
  It needs the local web server (outside the sandbox). Both halves use the working tree's viewer.
  The viewer only clamps the camera above the ground once the view first settled (before, the
  camera height depended on tile load order, so snapshots of one world differed from run to run).
  `before_after.py --build-args` adds to `build --quick`: with `--out output/full` it replaces the full
  capital build there with a quick one (41 tiles); rebuild it without `--quick` afterwards.
- Claude takes at most two snapshots per task (`python -m citygen snapshot --view street`; views
  street = the boulevard, souk, aerial, top), then stops and asks Ali. On Ali's Mac `.venv` has
  playwright 1.56.0 because it matches the Chromium already in `~/Library/Caches/ms-playwright`
  (newer versions want a new download of about 250 MB). In a sandboxed Claude session the
  snapshot's small local web server needs local port binding: run it outside the sandbox, or set
  `sandbox.network.allowLocalBinding: true`.
- Every piece of the kit in one grid: `python -m citygen kit-sheet`, then
  `python -m citygen view output/kit-sheet`.
