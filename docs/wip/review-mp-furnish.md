# Review: the furnish-m part of merge-prep (prompt 54 round 3)
Reviewer: review-mp-furnish, 3 November about 20:55 UTC. Commit reviewed: 4b29ffe (cherry-picked furnish-m), as it
stands at merge-prep HEAD 3099981. Files: citygen/interior/furnish.py, household.py, kit_new.py,
styles/maghreb.toml, tests/test_citygen.py. weave.py: not touched by merge-prep (no commit since 3036039).
No code changed by this review.

## Findings (file:line, severity, one-line fix)
- citygen/interior/furnish.py:944, high (real bug; quality, not faults): place mode "side" centres the piece
  twice. `slide(D/2, length - D/2)` already gives the centre s along the run, then `q = r.point(s) + ... + e*(D/2)`
  moves it another D/2 along the wall (e = n turned -90 deg = +-d). So the bed spans [s, s+D] (or [s-D, s]): it is
  never flush with one corner, half the slide positions overhang the run end (rejected later, so wasted), and a
  run between D and 1.5 D long can never take it although the guard `D > r.length` lets it try. Fix: drop
  `+ e * (D / 2)` (the slide already centres it), then re-run the survey; the 2% numbers may improve.
  Also the yielded `s` (furnish.py:945) is then D/2 off the piece's real centre, so a piece hung on a "side" host
  (`host.s +- host.width/2`, furnish.py:922) is bounded over the wrong span (for example a tap `hang:wc`,
  styles/maghreb.toml:3060, if that wc slot ever gets "side"). The same one-line fix cures both.
  It blocks the very case SPEC.md:2545 names (a sedda along a maqsura's back wall): a 2.0 m piece needs a 3.0 m
  run instead of 2.0 m, and the notes' maqsuras are 2.3-2.7 m square.
- citygen/interior/furnish.py:937-945, low: "side" has no `r.clear(...)` test of the run's openings (wall mode has
  it for blind/hang); a bed along a window wall relies only on the keeps. Fix: skip spans whose
  `r.clear(s - D/2, s + D/2, spec.z[1])` fails when the slot is `blind`, as wall mode does.
- citygen/interior/household.py:168, low: `ways(r) <= 1` also accepts a maqsura with 0 PASS openings (unreachable
  or reached only through a kind not in PASS). Fix: `== 1`, or check that PASS holds every door kind a maqsura gets.
- citygen/interior/household.py:131 and furnish.py:467, low: the 4.5 default is written twice in code (the toml
  value is the real one). Fix: one module constant or read only from cfg (CLAUDE.md: numbers live in the toml).
- citygen/interior/furnish.py:678-679, low: an `else` table may override any slot key (also `need`, `role`,
  `else`, `count`). Fix: whitelist the keys an `else` table may set (place, most, ends, cross).
- tests/test_citygen.py:4879, low (fragile test): the warned room is `w.split()[2]` of a free-text warning; a
  reworded warning silently changes the count. Fix: assert the warning shape, or let furnish keep warned room ids.
- tests/test_citygen.py:4877, low (bar too easy): the denominator is `len(fu.functions)`, every room with a function,
  also rooms with no `need` slot (courts, stairs, stores), so the 2% share is diluted. Fix: count only rooms whose
  function has a `need` slot, or state in the docstring what the share is of.
- tests/test_citygen.py:4853, medium (densities): the 2% test runs only at sparse; lived-in (1.8% quick in the
  notes) and full are not tested, and full adds pieces before some `need` ones can be placed? (not checked).
  Fix: one more parametrised density (lived-in) with the same bar, slow marker kept.
- tests/test_citygen.py:4853, medium (margin): the notes measure 1.8% (quick, lived-in) and 2.2% (full capital,
  above the bar); the sparse sample passes, but with little room. A planner change (flats, houses rounds) can push
  it over. Fix: print the share in the assertion message and record the measured share in SPEC 6d.

## Random streams and determinism
- No new draws in the diff: functions() picks rooms by area/ways with `best` (no rng), "side" and `else` tables
  are deterministic loops, wc_keep is a constant. No stream gains a draw. The test orders homes with lexsort plus
  an index tie-break and sorts layouts: deterministic.
- Changing the couple's room changes which room gets which function; any per-room draws keyed by room id stay
  stable, but if a draw is sequential over rooms in function order, later rooms change (allowed: furnish output,
  not in the fingerprint, which showed 0 changed).

54 can be ticked: no, because the "side" mode offset (furnish.py:944) is a real bug in the new code, the full
capital is still at 2.2% warned (above the 2% target) and the 2% test covers only sparse; fix the offset, re-run
the two surveys, and tick it when quick and full are both at or under 2%.

## Left (not checked in the time)
- Not run: no test was run (review only); the side-mode bug is shown by reading furnish.py:937-945 with slide()
  (furnish.py:1057, which returns centres) and Run.point (furnish.py:83), not by a rendered room.
- Not checked: tie-breaks inside household `best` (determinism of equal areas); whether `full` places extra
  pieces before some `need` ones (the densities question above); kit_new.py hand_basin / shower_small sizes
  against SPEC 6d.
