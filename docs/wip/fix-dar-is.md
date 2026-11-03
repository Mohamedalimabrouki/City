# fix-dar-is (3 November, from wip/merge-prep)
Task: review-mp-speed says the `is not` filters at `citygen/interior/dar.py:598` and `601` could drop two equal
pieces, since the cut memos now share one object for equal inputs.

## Can it happen?
- Only if one band's list holds the same piece twice. The lists come from `bands()`: two cells with the same
  polygon would be two rooms on the same ground, which no sound plan has. So it is a latent hazard, not a
  live bug; the identity filter is exact as long as every piece in a list is unique.
- In the quick capital: see "Checked" below.

## Change (filter by position)
- `ground()`: the host is now picked by index (`min` over positions, same key, same first-minimum tie rule as
  `min` over the pieces), and dropped with the new `drop(items, i)`.
- `l_skifa` passes the turn piece's position (`touching[0][1]`) to `turn()`, whose `"turn"` tuple now carries
  that position instead of the piece; `ground()` drops it with `drop()`. Only `ground()` reads `"turn"` (grep).
- When every piece is unique, `drop(L, k)` equals `[p for p in L if p is not L[k]]`, so plans are unchanged.
- Test: `tests/test_dar_drop.py` (a list holding one object twice keeps one copy; the old filter lost both).

## Checked
- `pytest -q tests/test_dar_drop.py`: 1 passed.
- `build --quick` + fingerprint: 282 parts, 0 changed (expected: a build never runs interior code).
