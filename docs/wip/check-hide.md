# check-hide

Checked commit 2e77e6e ("WIP fix-hide (round 2)", hidoura wool locks in `citygen/interior/kit_old.py`).
Both commands ran in this folder and imported this folder's `citygen` (checked).

- `.venv/bin/python -m pytest -q`: PASS. 163 passed, 11 deselected (slow), 3 warnings, 140 s
  (slow because about 20 helpers ran at once; about 29 s when the Mac is quiet).
  The 3 warnings are shapely "divide by zero in oriented_envelope" in test_roof_newel_climbs_from_top_floor,
  test_court_rule and test_court_against_a_party_wall: a RuntimeWarning, not a failure.
- `.venv/bin/python -m citygen build --quick`: PASS. Exit 0, done in 10.8 s, 9 tiles, Goumosbane 1,668
  buildings and 449 streets; no warning or error in the log.

No failing names. Nothing left to do.
