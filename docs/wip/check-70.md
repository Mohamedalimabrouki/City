# check-70 (3 Nov, about 20:53 UTC): is wip/fix-70 ready to merge?

Compared 7cc1e2d (WIP fix-70) with 57c8c1d (WIP review-70, the commit before it; worktree /tmp/claude-501/check-70-base).

- Quick build: both finish (15.7 s each, run side by side). 41 output files each, cache left out.
- Byte-identical: 38 of 41 files, among them `cities/goumosbane/streets.json`, every tile and every map.
  The 3 that differ differ only where they must: `summary.json` and `tiles/index.json` carry the new
  build key, `summary.json` also echoes the new `settings/streets` section, and `plan.json` /
  `summary.json` record the planning time (5.7 s vs 6.0 s, a clock reading, differs between any two runs).
- Tests: full `pytest -q` (not slow) still running at the first push; see the next commit.
- Cache: yes, the build redoes its cached data once. `build_key` (citygen/buildkey.py:61) hashes every
  setting, so the new `[streets]` section changes the key, and `clean_cache` then drops the old plan
  pickles and the tile journal (cache/goumosbane-<key>.pkl, cache/tiles-<key>): the next build re-plans
  every city and re-exports every tile. It does not matter: the key also hashes the code of every build
  file (`_code_hash`), and fix-70 edits citygen/export/streets.py, so the key would change without the
  new section too, as after any code merge. One cost to know: `graph_grid` only shapes streets.json,
  yet changing it later re-plans every city (a few seconds per city in a quick build, longer in a full
  one); Ali will rarely touch it, so leave it.
- Verdict: pending the tests.
