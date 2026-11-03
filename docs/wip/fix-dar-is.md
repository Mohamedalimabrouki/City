# fix-dar-is (3 November, from wip/merge-prep)
Task: review-mp-speed says the `is not` filters at `citygen/interior/dar.py:598` and `601` could drop two equal
pieces, since the cut memos now share one object for equal inputs.

## Can it happen?
- Only if one band's list holds the same piece twice. The lists come from `bands()`: two cells with the same
  polygon would be two rooms on the same ground, which no sound plan has. So it is a latent hazard, not a
  live bug; the identity filter is exact as long as every piece in a list is unique.
- In the quick capital it does not happen: a probe wrapped `drop()` while planning every dar house (270 calls,
  0 lists holding the dropped piece twice, by identity or by equal shape).

## Change (filter by position)
- `ground()`: the host is now picked by index (`min` over positions, same key, same first-minimum tie rule as
  `min` over the pieces), and dropped with the new `drop(items, i)`.
- `l_skifa` passes the turn piece's position (`touching[0][1]`) to `turn()` (as `piece_at`: `turn()` already has a local `at`, the first WIP clashed
  with it and crashed L-skifa houses), whose `"turn"` tuple now carries
  that position instead of the piece; `ground()` drops it with `drop()`. Only `ground()` reads `"turn"` (grep).
- When every piece is unique, `drop(L, k)` equals `[p for p in L if p is not L[k]]`, so plans are unchanged.
- Test: `tests/test_dar_drop.py` (a list holding one object twice keeps one copy; the old filter lost both).

## Checked
- `pytest -q tests/test_dar_drop.py`: 1 passed.
- `build --quick` + fingerprint: 282 parts, 0 changed (expected: a build never runs interior code).
- `pytest -q -k "dar or interior or home or court or skifa"`: 25 passed.
- Survey of the quick capital's dar houses (`tools/interior_survey.py`, group dar, with the probe):
  206/210 pass, 0 crashes, the same 4 failing (227, 245, 272, 674).
- Byte-identical by construction: with no duplicate in any list, `drop(L, k)` gives exactly the old list, and
  `min` over positions picks the same first-minimal host as `min` over the pieces.

## Left
- No full `pytest -q` run here, and no rooms.json byte diff old against new (the probe's 0 duplicates is the
  proof that the lists, so the plans, are the same).
