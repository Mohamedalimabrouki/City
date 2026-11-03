# Review of wip/villas-o (villas round O), helper review-villas, 3 November

Scope: `git diff c48fb1e..50d6f9e` (merge base with main = c48fb1e): `citygen/interior/villa.py`,
`layout.py`, `spine.py`, `styles/maghreb.toml`, `tests/test_citygen.py`. Code read only; no code changed.

## Verdict
Sound and small. Determinism holds: no new random draws, no rng stream touched, no set or dict
order used; the new box choice walks the same sorted `steps` list as before and `max` keeps the
first of a tie. Old behaviour is kept whenever the `box_room` flag is off (the early `return` path
is unchanged), and the `little` gate is unchanged for maisons. The owner's survey (docs/wip/villas-o.md)
backs it: Ain Chilel 1002/1004 rooms.json identical (only villas 307 and 369 changed, 369 won), capital
1300/1300 identical, fingerprint 0 changed. Main gap: the tests prove only `roomy`, not the three
behaviour changes.

## Findings (file:line, severity, one-line fix)
1. tests/test_citygen.py:5029, medium: the test covers `roomy` alone; nothing checks the `box_room`
   pick in `place_box`, the layout pass, or the tuple `door_to` -> add a hand-made test that calls
   `newel_rooms` with `("hall", "salon")` where only a salon touches the square, and one that
   `place_box` with `box_room` set returns the wall box, not the middle one.
2. tests (none), medium: the win on villa 369 is proved only by the off-line survey -> add a `slow`
   test that plans villa 369 of Ain Chilel and asserts `rooms.check` is empty (it locks the round's gain).
3. citygen/interior/villa.py:505-518, low (speed): with `box_room` on, every fitting box of every
   (y, e, side) step is scored with two mitre buffers per floor (369: 1.07 -> 1.83 s) -> stop the
   scan once `roomy` reaches the storey's area less the box (no better box exists), or cap the steps.
4. citygen/interior/villa.py:525-527, low (determinism across machines): `max` on float areas from
   GEOS buffers; a near-tie could flip between GEOS versions -> round the score (`round(a, 3)`)
   so ties go to the first box on every machine.
5. citygen/interior/layout.py:88-90, low: the `box_room` replan starts from `before` with only its
   own flag, so the earlier carve / landing_way / nooks results are not re-tried on it (notes say a
   carve after it won nothing) -> fine for now; say so in the comment so a later round does not assume
   they chain.
6. citygen/interior/layout.py:86, low (readability): the inline tuple duplicates `SHORT` ->
   `f.endswith(SHORT if layout == "villa" else ("has no chambre",))`.
7. citygen/interior/spine.py:1408, low (readability): the one-line `for ... if ... else ()` header is
   hard to read -> build `types = ...` on the line before, then `for t in types:`.
8. citygen/interior/villa.py:505, low: `job.interior.__dict__.get("box_room")` relies on `again`
   setting a plain attribute (same pattern as `little`, so consistent) -> no change needed; note
   `getattr(job.interior, "box_room", False)` reads the same and is plainer.
9. citygen/interior/villa.py:119, ok: `lit_top` is only set when `small` is truthy, which needs
   `floors == 1`, so the roof stair's door change touches one-floor villas only, as intended.
10. styles/maghreb.toml:2038-2039, ok: both keys sit under `[interiors.villa]`, the section both
   `layout.py` (style["interiors"]["villa"]) and `villa.py` (`job.cfg["villa"]`) read.
11. docs, low (merge): no SPEC 6c line, ROADMAP, WORKLOG or HANDOFF entry for round O yet (WIP
   commit) -> the merger adds a WORKLOG entry and a SPEC 6c sentence on `box_room` and the little villa.

## Can the new test fail?
Yes: on the parent c48fb1e `from citygen.interior.villa import roomy` raises ImportError, and the two
asserts check real numbers (middle box leaves 2.0 and 1.9 m strips, both under 2.6 m, so 0 m2;
the wall box leaves a 3.9 m strip, about 25 m2). It cannot detect a wrong pick in `place_box` (finding 1).

Run here (20:54 UTC): on 50d6f9e `pytest tests/test_citygen.py::test_box_room_roomy` passes (2.2 s with
start-up); on the parent c48fb1e (scratch worktree, the new test file copied in) it fails with
ImportError, as expected.

## Left (time limit 20:59 UTC)
Did not re-run the full `pytest -q` here (the owner's notes: 164 passed at 20:14); did not open the
472-villas-plans picture.
