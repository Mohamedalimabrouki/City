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
  (bougainvillea curtains instead of lollipops) and **P8** (golden hour as the viewer's default,
  with a Noon / Golden hour / Night menu).
- Since 21 October 2026 the work runs on Ali's Mac through the playbook `docs/PROMPTS.md`: 100
  numbered prompts (`Do prompt N.`), each with its model and effort, one session each; nine Opus
  checkpoints review the work as it goes; every session adds an entry to `docs/WORKLOG.md`.
  After prompt 100, Ali brings the work back to his lead session for a full review.
- From prompt 7, a trial runs the build prompts with DeepSeek V4.1 Flash in OpenCode (free; it
  reads `CLAUDE.md` because there is no `AGENTS.md`). Claude keeps the checkpoints, the big
  designs and the phone page (list in `docs/PROMPTS.md`). Checkpoint 16 judges the trial; the
  git tag `before-deepseek` is the backup point from before it.
- Prompts 1-5 (tools and fast builds) are done and checked by checkpoint 1 (CP1, 22 October
  2026): fingerprint, before/after pictures, parallel and resumable builds all work as
  documented. Reference for checkpoint 16: `output/checks/fp-cp1.json` (quick build) and the
  pictures `output/checks/cp1-street.png`, `cp1-aerial.png`.
- Seed 42 makes the country **Bodjantouna** with the capital **Goumosbane**.
  `python -m citygen build --quick` writes it to `output/bodjantouna-42/` in about 7 seconds on
  Ali's Mac (20 seconds in the cloud).
- All work is on the git branch `claude/procedural-city-generator-xop72h`. Keep working on it and
  push at the end of every task (GitHub is the backup).
- 3D page for the phone (made from the quick build):
  https://claude.ai/artifact/HMtdFZUV9sGmyPn4q8mKsq . Rebuild it with `tools/make_artifact.py`
  after a big visual step, then publish the folder to that same link from a Claude session.

## Decisions and lessons (do not relearn them)

- **Parallel tiles** (`TilePool` in `citygen/build.py`): spawn processes start while the parent
  plans and wait for one pickle file (world + plans); each builds its own `TileContext`. Use
  `multiprocessing.Pool`, not `ProcessPoolExecutor`: the Claude sandbox forbids the
  `os.sysconf` call the executor makes. Capital on the M1: 71 s -> 25 s (2.8x); the 9 s of
  planning is now the biggest serial part. The parent's file writing runs while workers load.
  Slow tests: `python -m pytest -q -m slow` (default run skips them, see `pytest.ini`).
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
- **Blender 5**: the physical sky is `MULTIPLE_SCATTERING` with `aerosol_density`; the
  compositor moved to node groups, so the beauty render skips its haze there (task Q4).
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
- **Old-town tiles** reach about 5 MB with all the dressing (SPEC budget note; task Q5).

## Known weak spots

Listed as tasks Q4 and Q5 in the roadmap: no haze in Blender 5 beauty renders and heavy
old-town tiles. Also: modern slabs and houses deep inside medina blocks
have no door or windows, because the dressing only dresses walls within 1.6 m of a street
(prompts 20.1 and 20.2).

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
