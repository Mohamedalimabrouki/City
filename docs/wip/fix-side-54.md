# fix-side-54 (from wip/merge-prep 3099981), 3 November about 21:02 UTC
Task: review-mp-furnish found that place mode "side" moved the piece twice along the wall.

## Done
- citygen/interior/furnish.py:937-944: dropped `+ e * (D / 2)` (and the now unused `e`). `slide()` already gives the
  centre s, so the bed now spans [s - D/2, s + D/2]: flush with a corner at the run's ends, never past them, and the
  yielded s is the piece's real centre (so a piece hung on a "side" host is bounded over the right span).
- tests/test_citygen.py: `test_furnish_side_lays_a_sedda_flush_along_a_short_back_wall` (a 1.40 x 2.0 m sedda on a
  2.3 m blind run, pure geometry, under 0.1 s). It fails on the old code (checked by stashing the fix) and passes now.
- `pytest -q -k "furn or household"`: 9 passed (43 s).

## Left
- The quick capital's warned-room share before and after: see below if measured, else not done.
- Not done (other review findings, out of this task): "side" has no `r.clear` window test; household.py:168 `<= 1`.
