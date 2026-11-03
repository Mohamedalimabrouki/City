# check-mats: full test run

Branch: detached worktree on 941b135 (WIP fix-materials: notes with the GLB proof on building 32).
Command: `.venv/bin/python -m pytest -q` (run with `-p no:cacheprovider`, so no cache folder is written).

Result: PASS. 164 passed, 10 deselected (the `slow` tests, skipped by the default settings), 3 warnings, 72.6 s.

Failing tests: none.

Warnings (not failures, low severity): shapely `oriented_envelope` "divide by zero" RuntimeWarning in
tests/test_citygen.py::test_roof_newel_climbs_from_top_floor, ::test_court_rule and
::test_court_against_a_party_wall.

Left: nothing (the slow tests were not run; the brief asked only for `pytest -q`).
