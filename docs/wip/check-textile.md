# check-textile

Checked commit aa45f74 (WIP fix-textile), 3 November.

- Full tests (`.venv/bin/python -m pytest -q`): PASS. 163 passed, 11 deselected (slow), 3 warnings, 134.7 s.
  The time is high only because about twenty helpers ran at once (about 29 s alone).
  The 3 warnings are the known shapely "divide by zero in oriented_envelope" in
  test_roof_newel_climbs_from_top_floor, test_court_rule, test_court_against_a_party_wall.
- Quick build (`.venv/bin/python -m citygen build --quick`): PASS. Goumosbane (capital) 1,668 buildings,
  449 streets, 9 tiles, done in 13.0 s -> output/bodjantouna-42.
- No failing names. No code changed.
