# test-scrap-hall (3 November, about 21:02 UTC): tests only
From review-mp-flats: `test_slab_scrap_hall_tries_other_doors` passed even with `scrap_hall` stripped of its 0.8 m check.
- Added to that test (tests/test_citygen.py, about line 5055): a faulty plan (faults 2) with a real hall tries only its
  first door (reaches `scrap_hall` returning False, not the score break); a strip hall a couloir meets by 1.1 m tries
  only its first door (the 0.8 m check); one a salon meets by 0.5 m still tries the others.
- Mutant check (`scratchpad/scrap_mutant.py`, scrap_hall without `<= 0.8`, monkeypatched): the test now FAILS on the
  mutant (at the 1.1 m couloir case) and PASSES on the real code. `pytest -q -k "scrap_hall or flats or slab"`: 8 passed.
- No code changed. Left: nothing for this task; the duplex test's missing cases (review-mp-flats) are another task.
