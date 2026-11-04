# Review of prompt 70 (C4a street graph), branch wip/graph-70 at 8e38bab

Reviewed: `git diff 3036039...HEAD -- citygen tests docs/SPEC.md` (build.py, export/streets.py,
SPEC 6, two tests) against prompt 70 and CLAUDE.md rules. Read only; no code run, no code changed.

## Verdict
Mergeable after the two Medium items (or with them noted as accepted). No High findings. The
prompt's three checks are met by the code and tests as written; the "Done when" (capital
connected) is shown by the test on the quick capital only.

## Findings
| # | Where | Severity | Finding | Fix (one line) |
|---|-------|----------|---------|----------------|
| 1 | tests/test_citygen.py (none added) | Medium | No two-process byte test for `streets.json`. The rule in CLAUDE.md names on-demand commands, but this is a new written file and nothing else checks its bytes across PYTHONHASHSEED (no build-level two-process test exists; only `test_interior_two_processes` and test_homekit). In practice the code looks hash-safe (float tuple keys, `sorted(ends)`, insertion-ordered dicts, no sets), so this is a guard, not a known bug. | Add a `slow` test: run `streets_json` for the quick capital via `python -c` under PYTHONHASHSEED 1 and 2, `write_json` each, compare bytes. |
| 2 | citygen/export/streets.py:16 | Medium (rule) | `GRID = 0.05` is a tunable number in code; CLAUDE.md says numbers live in `defaults.toml` or the style. The prompt fixes 5 cm, so it is a format constant, but it also sets the stub reach (line 36) and attribution reach (line 67). | Move it to `defaults.toml` (for example `[streets] graph_grid = 0.05`) and read it in `streets_json`, or note in SPEC 6 that it is part of the format. |
| 3 | tests/test_citygen.py:5076 | Low | `z` is checked against `ground.surface` at the same (rounded) points: the function against itself. It proves only that `z` was filled from `Ground.surface`. | Also check a sample of nodes against an independent value, for example `z` within a few cm of `ground.height + lift` at nodes outside any walk/apron, or against the tile's street ribbon. |
| 4 | tests/test_citygen.py:5082 | Low | "Lengths match the geometry" compares `length` with the length of the same rounded polyline that the code wrote. Acceptable for the JSON, but the independent length check is the total in the fast test (line 5063). | Fine as is; optionally assert `sum(length)` of edges of street k is within 1 m of `plan.streets[k].line.length` plus its stub for non-overlapped streets. |
| 5 | tests/test_citygen.py:5063 | Low | `drawn - 1.0 < total` allows only 1 m lost to overlap (grid streets left under a boulevard are merged by the union). Passes on the quick capital; may fail spuriously on another seed or style with more overlap, without any real defect. | Compare `total` against the union length of the center lines (plus stubs), not the sum of the drawn lines. |
| 6 | citygen/export/streets.py:36 | Low | A mouth exactly on its host line (`distance == 0`) gets neither a stub nor a host vertex, the very case the HANDOFF lesson says the 5 cm union can miss after separate snapping. | Use `0.0 <= ...` for the host vertex (insert it always; add the stub only when distance > 0). |
| 7 | citygen/export/streets.py:147 vs city/paint.py:173 | Low (doc) | SPEC says sidewalks are "as the paint measures it", but the paint calls `walk_widths(..., MARKED)` (boulevard, arterial, connector only); the graph measures every kind. The graph's values are likely the better ones for games; the doc sentence is inexact. | SPEC: "measured like the paint does (`walk_widths`), for every street kind". |
| 8 | docs/SPEC.md:547 | Low (doc) | "`width` (curb to curb, sidewalks included)" contradicts itself: curb to curb is the carriageway. SPEC line 901 confirms width includes the sidewalks. | Say "the whole street ribbon, sidewalks included (carriageway = width minus both sidewalks)". |
| 9 | docs/SPEC.md:545, streets.py:89 | Low (doc) | "degree 2 only where two different streets meet end to end" is not strictly true: a closed street with no junction is one edge from a node to itself (degree 2), and same-street pieces that end head to head are not joined. | Add "or a closed street's start". |
| 10 | citygen/export/streets.py:156 | Info | `surface or "asphalt"` repeats a literal default; it matches mesh/tile.py:229 and mesh/lod.py:293, so it is consistent. | Optional: one shared default later; not for this prompt. |
| 11 | citygen/build.py:319, 331 | Info | `Ground` is now built before export instead of after; total parent time is unchanged (it was never overlapped), and `streets_json` (about 3 s per city with `walk_widths`) runs inside `write_files`, overlapped with workers. The worklog notes no build time. | Record `build --quick` time before/after in the WORKLOG entry; check a full build's parent time with many cities. |
| 12 | tests (only `plan` fixture) | Info | Connectivity is tested on the quick capital only. Other cities (impasse on impasse, mouths beyond `width/2 + GRID`) are not checked. | Before ticking C4, run the graph on every city of a full build and log the largest-part share. |

## What is sound
- Determinism: no RNG, so no new streams and no draws on old ones; no set iteration; dict keys
  are float tuples (not hash-randomized); `_merged` walks `sorted(ends)`; node ids in first-use
  order of a deterministic union. STRtree `nearest` ties resolve by input order.
- The noding follows the prompt: `set_precision(0.05)` per line, then `unary_union(grid_size=0.05)`;
  the impasse-mouth stub plus host vertex is a real fix (104 parts to 1 per the notes) and is
  documented in SPEC and HANDOFF.
- Edge orientation uses the 1/4 and 3/4 points, so rings orient correctly; the test asserts it,
  which makes the left/right sidewalk convention (`+1` left, SPEC Walk) testable.
- Tests check the output against independent data: union-find connectivity at 99.5% of length,
  every edge end is a node (index and exact coordinate), midpoints within width/2 of their
  street, degree recomputed from edges, kind against `plan.streets`, sidewalks below width, road
  links within 1 m of a node on the city limit. Fast test 0.56 s, heavy one marked `slow`.
- Format documented in SPEC 6 (table row and "Street graph" paragraph); `data_files_current`
  now requires `streets.json`, so an older build folder rewrites its data files instead of
  silently lacking the graph. Fingerprint per notes: only `files/cities/*/streets.json` added,
  as the prompt allows.
- No em dash character in the diff (checked by byte search).
