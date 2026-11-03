# check-81: full test run

- Commit tested: dd346ba (WIP fix-81), worktree /tmp/claude-501/check-81.
- Command: `.venv/bin/python -m pytest -q`
- Result: PASS. 164 passed, 10 deselected (slow marker), 0 failed, 3 warnings, 72 s.
- No failing tests.
- Warnings (not failures, low severity): shapely RuntimeWarning "divide by zero encountered in
  oriented_envelope" in tests/test_citygen.py::test_roof_newel_climbs_from_top_floor,
  ::test_court_rule and ::test_court_against_a_party_wall.
- Note: 72 s is well above the 29 s CLAUDE.md quotes; likely because about 20 helpers ran at the
  same time on this Mac.
- Left: nothing.
