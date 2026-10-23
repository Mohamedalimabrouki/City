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
  git tag `before-deepseek` stays as the backup point.
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
  `output/checks/cp2-street.png`, `cp2-souk.png`. Next: prompt 18.
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
- **Night mode** in the viewer: materials with an `emissive` color glow; window glass
  (`glass_dark`) lights up; the nearest lamps get real lights. Kit windows stay dark.
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
- **Old-town tiles** reach about 5 MB on the quick build and 8 MB on the full capital
  (`tile_65_106`, mostly roofs since prompt 15); task Q5 (prompt 39) brings them down.

## Known weak spots

Task Q5 in the roadmap: heavy old-town tiles. Since prompt 20.1 every dwelling has a door, but
houses deep inside blocks only get a narrow door squeezed toward the nearest street: 322 on the
quick capital, and on the full capital 1,781 medina houses and 7,802 residential houses (inner
residential parcels without frontage; prompt 20.2 cuts impasses in medina and village blocks
only). Modern-estate tiles grew +20% to +37% in bytes with their windows (instances plus piece
meshes), over the +20% budget (prompt 39, Q5, can shrink instance data).

## Checking the look without wasting tokens

- Best: Ali looks himself. `python -m citygen view` opens the browser (camera spots in the top
  menu, Night button, click a house). Or open the tiles in Blender:
  `/Applications/Blender.app/Contents/MacOS/Blender --python tools/blender_import.py -- output/bodjantouna-42/tiles`
- One command for a visual change: `python tools/before_after.py --view street` (last commit above
  the working tree, same camera, labelled, difference printed; 0.00 = identical). Options:
  `--ref`, `--cam x,y,z --look x,y,z`, `--kit-sheet --frame PIECE`, `--build-args`, `--no-build`.
  It needs the local web server (outside the sandbox). Both halves use the working tree's viewer.
  The viewer only clamps the camera above the ground once all tiles are loaded (before, the
  camera height depended on tile load order, so snapshots of one world differed from run to run).
- Claude takes at most two snapshots per task (`python -m citygen snapshot --view street`; views
  street = the boulevard, souk, aerial, top), then stops and asks Ali. On Ali's Mac `.venv` has
  playwright 1.56.0 because it matches the Chromium already in `~/Library/Caches/ms-playwright`
  (newer versions want a new download of about 250 MB). In a sandboxed Claude session the
  snapshot's small local web server needs local port binding: run it outside the sandbox, or set
  `sandbox.network.allowLocalBinding: true`.
- Every piece of the kit in one grid: `python -m citygen kit-sheet`, then
  `python -m citygen view output/kit-sheet`.
