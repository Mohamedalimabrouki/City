# check-87: full tests and quick build on wip/fix-87 (768e90b)
No code changed; this note only.

- `python -m citygen build --quick`: PASS, done in 14.5 s (Goumosbane, 1,668 buildings, 449 streets, 9 tiles).
- `python -m pytest -q`: PASS, 167 passed, 11 deselected (the slow ones), 0 failed, in 140 s
  (slow because about 20 helpers ran at the same time; about 29 s on a quiet Mac).
- 3 warnings, all the same one (not from the last commit, which touches only names tests): shapely RuntimeWarning "divide by zero
  in oriented_envelope" in test_roof_newel_climbs_from_top_floor, test_court_rule and
  test_court_against_a_party_wall. Severity: none (warning only).
- Left: nothing. The slow tests (`-m slow`) were not run; the brief asks only for the default run.
