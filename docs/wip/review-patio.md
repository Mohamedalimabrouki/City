# Review of wip/houses-patio (patio-house planner, 47.2 houses round 6)
Reviewer: review-patio, 3 November about 20:55 UTC. Scope: `git diff 61a8778..f5b8054` (merge base with main
is 61a8778; main has moved 4 commits since, so the merge-map decides conflicts). No code changed.

## Verdict
Correct and deterministic as far as read, safe to merge output-wise (the branch notes' hash proof: every other
house identical, maison 615 + No. 509 won). But it wins 1 house of 66 for up to +3.6 s on each failing house,
and about 70 lines are dead (floor 0). Suggest: do not merge as is; either drop the round or add a cheap
gate/budget first (see H1).

## Findings (file:line, severity, one-line fix)
- H1 citygen/interior/layout.py:88, high (cost vs value): 1 win (No. 509) for +2 to +3.6 s per failing maison
  (No. 634 2.6 -> 6.3 s); gate it (only when the blind room is on a floor whose region is a near-rectangle, or a
  fixed count budget of strips/cuts) or drop the round.
- M1 citygen/interior/layout.py:426-431, medium: `blind()` parses the fault text with a regex
  (`" (\d+) on floor "`, format from plancheck.py:492); a wording change silently turns the round off with no
  failing test; have plancheck return the room ids (or add a test pinning the message to `blind()`).
- M2 citygen/interior/patio.py:21, medium (rule "numbers live in styles"): IDEAL areas (salon 16, chambre 10,
  ...), the 0.3 m door reach (145, 183), the 0.9 m sliver width (101), the wc steps `range(2, 9)` (212) are in
  code; move them to `[interiors.villa]` in styles/maghreb.toml beside `patio_step`.
- M3 citygen/interior/patio.py:137-195, medium: floor 0 (hall at the street door, the L-shaped 2-strip ways) is
  never reached (layout.py:415 passes only floors > 0) and untested; remove it (and fix the module docstring
  lines 5-8) or test it.
- M4 tests/test_citygen.py:4723, medium: the only test is a hand-made `patio.plan` call; nothing tests the
  `layout.patio` pass (kept only when `check` passes, restored otherwise) or `blind()`; add a small test that a
  failing patio replan leaves the plan byte-identical.
- L1 citygen/interior/patio.py:272, low: the chambre count is capped at 2 per side, so a 3+ chambre floor with
  one usable side can never be met (false negative only, never a wrong plan); cap at `fl.chambres` instead.
- L2 citygen/interior/layout.py:422, low: unlike `again` (layout.py:403) the pass does not compare `dim()`;
  a passing patio plan could be darker than the kept one; add `or dim(...) > dark` for parity.
- L3 citygen/interior/villa.py:93, low (speed): when `patio_plan` returns None the floor is laid by `P.lay` as
  before and the whole pass is checked and thrown away; return early (skip `_plan` remainder) when a patio
  floor gets None.
- L4 citygen/interior/patio.py:37, low: the planner reads `[interiors.flats] strip` for its width test; a
  flats tuning then moves patio houses; give the villa its own key (or note the coupling in the toml).
- L5 citygen/interior/patio.py:76 vs 270, low: `kinds()` uses `fl.need` while `_side` gets the `need` with
  wc=0 after `_ends`; harmless (rejected at 270) but wasted work; pass `need` to `kinds`.
- L6 tests/test_citygen.py:4749, low: the area sum (63.0) does not prove no overlap; also assert
  `unary_union(cells).area == 63.0`.

## Determinism (no finding)
No random draws in patio.py; no existing stream touched (P.lay keeps its own `(kind, f)` key per floor, so a
patio floor that skips it shifts nothing). Sets are only used for membership (`ids`, `interior.patio`) or are
sorted (`_strips` line 129); dicts are filled in tuple order; ties keep the first (`>` strict). The memo key
is WKB bytes plus sorted `need`. Float positions are rounded to 3 decimals.

## rooms.check bars and SPEC
- The pass keeps a plan only when the whole `check` is empty (layout.py:422), stricter than `again`: it cannot
  add a fault, so no bar can drop; per the notes, maison passing 499 -> 500, villa 167 identical, 0 mesh/step
  faults, fingerprint 0 changed.
- SPEC: nothing in SPEC 6c describes round 6 yet (add a line when merged). SPEC lines 1418-1426: the window
  rule (a window on the street, a court or a light well; sdb and wc may stay blind) is enforced, since the pass
  keeps only a plan the full check passes and `kinds()` (patio.py:78) puts no living room on an unlit piece;
  "no room wraps a court's corner" is a colonial-band rule and "a maison's 3 m patio keeps its L rooms", so the
  slabs here (L-shaped where the region has a notch) break no SPEC rule. Quality note from the branch notes:
  No. 509's sdb is a 1.4 x 6.5 m strip across the floor (legal, mediocre; the notes' next step (2) fixes it).

## Left (time ran out)
Run: `pytest -q -k "patio_house or little_house"` on this branch: 2 passed in 1.9 s. Not run: the full suite, the
patio test on the parent (it fails there trivially: patio.py does not
exist), a look at No. 509 in 3D.

## Also checked (no finding)
- `layout.check` memo (layout.py:594-607) keys on an md5 of the pickled HELD state + `full0`; the `patio` flag
  is deleted before the check runs (layout.py:420-421), so a cached result can never belong to another plan.
- villa.py:120 `off_salon` is skipped on the patio pass, right: the patio rooms open on the couloir, not on a
  salon. Floors not in the patio set are laid by `P.lay` exactly as before.
