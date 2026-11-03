# check-brass: full tests and quick build on the fix-brass branch

Checked commit: d30fd69 "WIP fix-brass: notes (quick build checked)" (branch wip/fix-brass).
Run on 3 November, about 21:00 UTC, while about 20 other helpers shared the Mac (times are slow).

## Quick build
- `.venv/bin/python -m citygen build --quick`: PASS (exit 0), done in 9.9 s (10.7 s wall).
- World Bodjantouna (seed 42): 14 settlements, 14 roads; capital Goumosbane 1,668 buildings,
  449 streets; 9 tiles exported with 3 workers, 15 shared textures.

## Full tests
- `.venv/bin/python -m pytest -q`: PASS (exit 0). 163 passed, 11 deselected (the `slow` ones,
  skipped by default through `addopts = -m "not slow"`; not run here), 0 failed.
- Time 138 s (usually about 29 s): the Mac was shared, so this is load, not a slowdown in the code.
- 3 warnings, all the same shapely `divide by zero encountered in oriented_envelope`
  (test_roof_newel_climbs_from_top_floor, test_court_rule, test_court_against_a_party_wall).
  Harmless here (the tests pass), low severity; not caused by this branch's kit work.

## Verdict
Both checks pass on d30fd69. Nothing left to do for this check.
