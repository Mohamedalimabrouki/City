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
