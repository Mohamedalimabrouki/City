# test-cache-warm (3 November, about 21:03 UTC), from review-mp-speed's "missing guard"
- Added tests/test_citygen.py `test_warm_memos_plan_the_same_rooms` (after `test_interior_bytes_repeat`):
  plans pick:small and pick:compact of the quick capital, each from empty `cuts` memos (every module dict
  `_UPPER` in cuts.py cleared, at least 7 of them), then both again with warm memos in the other order, and
  compares the rooms.json bytes (written by export._write_json). It also asserts the memos were used.
- Run: `pytest -q -k warm_memos` 1 passed, call 1.76 s (not slow). With pick:dar + pick:compact it took
  3.29 s, so the dar was swapped for the small house.
- Left: no mutation check yet (a memo key without get_precision should make it fail, but may not fire on
  these two homes); the full `pytest -q` was not run here (only this test).
