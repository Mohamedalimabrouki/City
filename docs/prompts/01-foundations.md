# Prompts 1-6: foundations

Read only the section of your prompt. `CLAUDE.md` gives the routine every prompt follows
(fingerprint before and after, before/after picture for "Look" prompts, work log, commit, push).

## 1. T1 - Regression fingerprint: prove what a change touched

Model: Sonnet | Effort: medium | Size: S | Needs: - | Look: no

**Goal.** A tool that records a fingerprint of a build and later lists exactly which parts
changed, so every later prompt can prove "only the trees changed" instead of hoping. The lead
session did this by hand for Q1 and Q2 (hashes of tiles, plan.json without some keys, world.json
and every kit piece); make it a real tool.

**Do.**
1. One helper builds the kit for everyone: `kit.make_kit(seed, cfg, style)` (seed, `[build]
   kits`, palette, `[dressing.trees]`, and later style tables), used by `mesh/tile.TileContext`,
   `kitsheet.py` and the tool, so they can never drift apart.
2. New `tools/fingerprint.py` (standard library, numpy and the citygen package only):
   - `python tools/fingerprint.py save NAME [FOLDER]` writes `output/checks/fp-NAME.json`.
     FOLDER defaults to the latest build (same rule as `_latest` in `citygen/__main__.py`).
     The file records the world name and seed; `compare` refuses a different world.
   - `python tools/fingerprint.py compare NAME [FOLDER] [--allow PATTERNS]` prints one line per
     changed, added or removed part with a short, useful detail (list lengths before and after
     for plan sections, bytes and triangles for tiles, piece names for kit parts), then a
     summary "N parts, K changed". With `--allow "tiles/*,kit/tree_*"` (comma-separated fnmatch
     patterns; `--allow ""` allows nothing) it exits with code 1 when any other part changed.
3. Parts, each hashed on its own:
   - `world` (world.json);
   - `plan/<city>/<key>` for every top-level key of each `cities/<city>/plan.json`, with `stats`
     hashed without timing keys (`seconds` and anything ending in `_seconds`);
   - `tiles/<file>` for each tile file, `tiles/index` (index.json without timings);
   - `kit/<piece>` for every piece of `make_kit(...)`: geometry arrays and material names (not
     colors: a palette color change shows in tiles, not in kit parts);
   - `maps/<file>`, `gazetteer`;
   - `files/<relative path>` for any other file in the build folder, so outputs added by later
     prompts are covered automatically.
   Skip `summary.json` (timings), `output/checks/`, any `cache/` folder and any `build_key`
   field (prompt 5 adds them; they change with every code edit).
4. Fast (a few seconds on the quick build) and quiet.
5. Test (under 3 s): save and compare a small temp folder (no change), then edit one JSON key
   in it and see exactly that part change and `--allow` behave.
6. Docs: a short "Checking a change" paragraph in docs/SPEC.md section 9 with the commands.

**Check.** Two quick builds of the same code compare as 0 changed. Then temporarily change
`clumps` in `[dressing.trees.broadleaf]`, rebuild, compare (only `tiles/*` and
`kit/tree_broadleaf*` should change), and restore the file with `git checkout styles/`.

**Done when.** The tool works as above, tests pass, and the example output (a few lines) is in
your WORKLOG entry.

## 2. T2 - Before/after pictures in one command

Model: Sonnet | Effort: medium | Size: S | Needs: 1 | Look: yes (the tool itself)

**Goal.** One command that shows a visual change: the last commit next to the working tree,
same camera, one labelled image. Every "Look" prompt uses it; it is the task's two snapshots.

**Do.**
1. The viewer (`tools/viewer/index.html`) already reads `view`, `time`, `radius`, `shadows`,
   `ui` and `pick` from the URL. Add `cam=x,y,z` and `look=x,y,z` (generator coordinates in
   meters) to place the camera anywhere.
2. New `tools/before_after.py`:
   `python tools/before_after.py --view street [--ref HEAD] [--out output/checks/NAME.png]
   [--query k=v ...] [--cam x,y,z --look x,y,z] [--build-args "..."] [--kit-sheet]
   [--frame PIECE] [--size 1280x720] [--timeout 120] [--keep]`
   - Before: `git archive REF` into a temp folder under `output/checks/`, run
     `python -m citygen build --quick <build-args>` there with the same interpreter
     (`sys.executable`; split `--build-args` with `shlex`), snapshot it with that tree's own
     `tools/snapshot.py`.
   - After: build the working tree the same way (unless `--no-build`) and snapshot it. On both
     sides, snapshot the folder the build reports ("done ... -> FOLDER"), which `--out` in
     `--build-args` may move away from `output/<world>`.
   - Stack both, label "Before (<ref> <short hash>)" and "After (working tree)" with Pillow in
     a readable size (32-40 px), save to `--out` (default
     `output/checks/before-after-<view>.png`), delete the temp tree unless `--keep`.
   - Print the mean absolute pixel difference between the halves (0.0 = identical), so prompts
     can prove "the look did not change" without extra pictures.
   - If the before build has no such view (a prompt adds a new one), use `aerial` for the before
     half and say so in its label.
   - `--kit-sheet`: run `python -m citygen kit-sheet` on both sides and snapshot the sheets;
     `--frame PIECE` points the camera at one piece (rows shift when pieces are added).
3. Snapshots start a local web server, which the Claude sandbox blocks: when binding fails,
   print one line: "run outside the sandbox, or set sandbox.network.allowLocalBinding".
4. Note the command in docs/HANDOFF.md ("Checking the look") and docs/SPEC.md section 9.

**Check.** On an unchanged tree the halves are identical (difference 0.0). With a temporary
visible change (a much darker `leaf` color, reverted afterwards) they differ. Image under 400 KB
(optimised PNG, or `--out x.jpg`).

**Done when.** The command works for `street`, `souk`, `aerial`, `--cam/--look` and
`--kit-sheet --frame`; your WORKLOG entry names the test image path.

## 3. T3 - Housekeeping: quiet warnings, true docs

Model: Sonnet | Effort: low | Size: S | Needs: 1 | Look: no

**Do.**
1. `citygen/city/geo.py` `frame()`: wrap `shapely.oriented_envelope(poly)` in
   `with np.errstate(invalid="ignore"):` with a one-line comment (shapely 2.2 warns on a few
   normal polygons; results checked valid on 21 Oct 2026). Tests and builds print no warnings.
2. `citygen/__main__.py`: the snapshot `--view` help lists every view the index offers
   (aerial, street, souk, top).
3. `requirements.txt`: next to the playwright line, note that `playwright==1.56.0` matches the
   Chromium already cached on Ali's Mac (newer versions download a new browser).
4. docs/SPEC.md sections 1 and 8: add today's timings on Ali's Mac (tests about 8 s, quick
   build about 7 s) next to the budgets, which stay as they are.
5. `.claude/agents/city-builder.md` and `.claude/agents/city-checker.md`: use `.venv/bin/python`
   when there is no `python` command.

**Check.** `python tools/fingerprint.py compare before --allow ""` shows 0 changes.

**Done when.** No warnings in tests and builds; docs match reality.

## 4. C1a - Build tiles in parallel

Model: Sonnet | Effort: high | Size: M | Needs: 1 | Look: no

**Goal.** `python -m citygen build --area capital --workers 8` uses the Mac's cores; the output
is byte-identical to `--workers 1`.

**Read.** `citygen/build.py` (`build`, `tiles_for`), `citygen/mesh/tile.py` (`TileContext`,
`export_tile`), `citygen/__main__.py`.

**Do.**
1. `--workers N` on `build` (default from `[build] workers` in `citygen/defaults.toml`, set to
   0 = all cores minus one; 1 = today's sequential path, kept as is).
2. `concurrent.futures.ProcessPoolExecutor` with the "spawn" context (macOS). Each worker builds
   its own `TileContext` once, in an initializer: either rebuild world and plans from the same
   settings (deterministic) or receive the plans pickled (shapely 2 geometries pickle). Measure
   both on `--area capital` and keep the faster. No shared mutable state. Anything written once
   per build (later: shared textures) is written by the parent process before the tiles.
3. Workers return what `export_tile` returns; the parent restores today's order (sorted by
   distance to the focus) before writing `index.json`, so the index is identical.
4. Small builds stay sequential (parallel only when tiles > 2 x workers), so `--quick` does not
   pay process start-up.
5. Test: workers 1 and 2 give identical tile bytes on a tiny area (under 10 s, or with a `slow`
   marker that the default run skips; document how to run slow tests).

**Check.** Full builds go to `output/full` (see CLAUDE.md): build `--area capital --workers 1
--out output/full`, `fingerprint save w1 output/full/<world folder>`; build again with
`--workers 8`, `fingerprint compare w1 output/full/<world folder> --allow ""`: 0 changes. Time
both.

**Done when.** The full capital builds at least 3x faster with 4 or more workers, the output is
identical, tests pass. Timings in WORKLOG and SPEC section 8.

## 5. C1b - Resumable builds: skip what is already built

Model: Sonnet | Effort: high | Size: M | Needs: 4 | Look: no

**Goal.** Re-running a build only redoes what changed; an interrupted big build continues
where it stopped.

**Do.**
1. A build key: SHA-256 of the merged settings (cfg as sorted JSON), the style file bytes, each
   used kit's manifest and .glb bytes, every `citygen/**/*.py` file (any code change
   invalidates: simple and safe), and the sorted ids of the planned settlements (a tile's
   content depends on which cities were planned). Store it as `build_key` in `summary.json` and
   `tiles/index.json` (the fingerprint tool already ignores `build_key`).
2. Plans: after planning a city, pickle it to `output/<world>/cache/<slug>-<key12>.pkl`; with
   the same key, load it instead of planning (log "plan reused"). After loading, set
   `plan.settlement` back to the world's own `Settlement` object (the pickle holds a copy, and
   `build.py` compares settlements with `is`, which would empty the index views). Delete cache
   files that carry another key.
3. Tiles: skip a tile when all its files exist, the stored key matches and `--force` is not
   given; reuse its entry from the previous `index.json`. Write files to a temp name and rename
   at the end, so a half-written tile never counts as done. (Later prompts add textures and
   lod1 files: a tile counts as finished only when every file it lists exists.)
4. `--force` rebuilds everything; a different key rebuilds everything.
5. Tests: a second run of a tiny build reuses plan and tiles and gives identical output, with
   the index views intact; changing a setting (for example `[tiles] terrain_step`) rebuilds.

**Check.** A reused build compares to a fresh one with 0 changes (`fingerprint`).

**Done when.** A second `--area capital --workers 8 --out output/full` run takes under 10% of
the first; a build stopped halfway (Ctrl+C) and run again finishes correctly; tests pass.
Tick C1.

## 6. CP1 - Checkpoint: foundations

Model: Opus | Effort: medium | Size: review | Needs: 1-5 | Look: street + aerial (current state)

You are the reviewer for prompts 1 to 5. Be strict but fix things yourself when they are small.
1. For each prompt: read its WORKLOG entry and its commit (`git show --stat`, then only the
   files that matter). Check the result against the prompt's "Done when". Look for: randomness
   not on its own `stream` path (CLAUDE.md rules), numbers in code that belong in the style or
   defaults, weak or missing tests, docs not updated, files committed by mistake, em dashes,
   dead code.
2. Run the tests, `build --quick` and `python -m citygen stats`; compare with the WORKLOG.
3. Use the tools as a newcomer would: fingerprint save/compare, `before_after.py` on an
   unchanged tree, a parallel build, a resumed build. Smooth any rough edge.
4. Fix small problems yourself (commit "CP1 fixes: ..."). For a bigger problem, add a fix task
   to the docs/ROADMAP.md checklist and a new section `## 6.1. ...` at the end of this file
   (same format), add its row to docs/PROMPTS.md, and tell Ali to run it before prompt 7.
5. Save the reference for the next checkpoint on the quick build, naming the folder:
   `python tools/fingerprint.py save cp1 output/bodjantouna-42`, and snapshots
   `output/checks/cp1-street.png`, `output/checks/cp1-aerial.png` (two snapshots).
6. Update docs/HANDOFF.md "Where things stand", add a WORKLOG entry, commit, push. Report to Ali
   in under 12 plain lines: what is solid, what you fixed, what he should look at.
