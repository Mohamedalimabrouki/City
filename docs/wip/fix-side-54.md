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
- Not found: which room flips to warned (see the share below), and why.

## Warned-room share (quick capital, the 2% test's sample: 8 homes per layout nearest the centre, 2087 rooms)
- Old code (the fix undone by a monkeypatch in a throwaway test): 36 warned = 1.72%, at sparse and at lived-in alike.
- New code: 37 warned = 1.77%, at sparse and at lived-in alike. So the fix does not lower the share here: one more
  room misses a `need` piece, probably because a "side" bed now lands mid-wall (slide starts at the middle) and
  blocks another need piece that used to fit. Still under 2%. Worth a look before ticking 54: try "side" from
  the run's ends inward (`ends`-style slide) so the bed hugs a corner and leaves the rest of the wall free.
- Not done (other review findings, out of this task): "side" has no `r.clear` window test; household.py:168 `<= 1`.
