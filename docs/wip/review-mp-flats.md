# Review: the flats-j part of merge-prep (review-mp-flats, 3 November, about 20:55 UTC)
Scope: `citygen/interior/flats.py` (best_lay + scrap_hall, duplex + duplex_lay + R_PRIVATE) and the two new
tests in `tests/test_citygen.py`, commit db40631 (flats.py is identical in merge-prep 3099981). No code changed.
Line numbers are those in merge-prep 3099981.

## Determinism: looks right
- New choices draw on their own streams: the moved ladder's upper floor is laid with key `("duplex", unit, "way")`;
  the scrap retries reuse the flat's own key per entry, exactly like the colonial retries already do. No new draw
  on an old stream; ties broken by `-id` / lowest index; `union_all` over the room list order. No set/dict-order use.
- The memo `job.retried` is now also written for slab blocks (before, slab never got past try 0): same inputs give
  the same result, but `base` has no floor, so a failed scrap retry on floor f also suppresses it on floor f+1 with
  the same region and entries, although `P.lay` depends on f (pre-existing design, now reaches slab too).

## Findings (file:line, severity, one-line fix)
- tests/test_citygen.py:4996-5027 (test_slab_scrap_hall_tries_other_doors), MEDIUM: the "real hall is kept"
  case passes only because its score is 0 (the `score <= 1` break), never through `scrap_hall` returning False;
  and no case has a couloir/salon touching the hall, so the 0.8 m narrowing (the step 7 fix for lost No. 1086,
  1279) is untested: deleting it keeps the test green. Fix: add a slab case with a faulty plan (faults 2) whose
  hall is a real hall, and one whose scrap hall meets a couloir by 1.1 m; both must try only the first door.
- flats.py:599-608 (duplex, ladder moved into the couloir), MEDIUM: nothing checks the clear width left beside the
  ladder; a 0.6 m ladder against the side of a 1.1-1.3 m couloir leaves 0.4-0.6 m, below a passage. Fix: keep the
  moved spot only when the way minus the ladder still has its passage width (cfg value, about 0.8 m), else keep the
  old spot; add that case to test_slab_duplex_ladder_from_the_couloir.
- flats.py:540-547 (scrap_hall), LOW: the 0.8 m arch length is a number in code (rule: numbers in
  styles/defaults); it must stay equal to `spine.doors`' arch length. Fix: read both from one cfg key.
- flats.py:565 (R_PRIVATE), LOW: a copy of `plancheck.PRIVATE` (plancheck.py:545); they can drift. Fix: import
  `PRIVATE` from plancheck (check for an import cycle) or move it to one shared place.
- flats.py:429 (best_lay), LOW: `scrap_hall(job, first)` uses `first`, which is only bound by the loop body of
  try 0; correct today (i == 1 always follows i == 0) but fragile. Fix: set `first = None` with `best`.
- flats.py:601 (duplex), LOW: `solid(...)` on an empty union (a flat with couloir/hall rooms that miss the region)
  is not guarded before `.buffer`; `way.is_empty` is tested only after. Fix: test the intersection's emptiness first.
- flats.py:602, LOW (style): `from shapely.ops import nearest_points` inside the loop. Fix: module import.
- tests/test_citygen.py:5030-5061 (duplex test), LOW: only the happy path; no case where the moved ladder still
  lands private (old spot kept) or where `S.ladder` finds no spot. Fix: two more hand-made cases (cheap).

## The window and way-home checks, and the 95% bars
- No pytest pins a 95% bar for flats (grep finds none); the only measure is the helper's survey (docs/wip/flats-j.md):
  slab 253 of 353 interiors passing (72%), flats 4,563 of 5,140 (89%), colonial 3 of 270. The 95% bar is NOT met;
  round J is a real gain (6 won, 0 lost, colonial and maisons/villas identical) but not a finish.
- Way home: the two fixes target the right causes (scrap hall on a palier side; ladder foot/head in a chambre);
  left open by the notes: No. 1088, 1199, 1265, 1272, 1269 (spine's cuisine pick). Windows: round J does not touch
  them; blind chambres left (No. 1365, 1301, 1091, 1198).
- Nothing passes by luck in the city counts as far as the notes show (11 interiors changed, all accounted for);
  the luck is in the unit test above (score 0 hides the branch).

## Left (time)
- Did not re-run the survey or pytest here; did not open spine.doors to confirm its arch length is 0.8 m.
