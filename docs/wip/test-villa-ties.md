# test-villa-ties (3 November, from wip/villas-o; no code changed)

Question (review-villas finding 4): `place_box` keeps `max(fit, key=score)` over float areas from GEOS buffers
(citygen/interior/villa.py:518, scores from `roomy` at villa.py:526); a near tie could pick another box on another
machine. How many villas and maisons have their best two boxes within 1e-9?

How: scratchpad `tvt_ties.py` wraps `villa.place_box` and `villa.roomy` in memory (nothing on disk changes),
plans every home, and for each `place_box` call that scores boxes records the gap between the best two scores.
Build used: /tmp/claude-501/villas-o/output/bodjantouna-42 (the quick build), code at 50d6f9e.

## Quick capital
- 0 villas and 0 maisons (the quick capital has none; the tests' comment at tests/test_citygen.py:1985 says the
  same). So 0 ties there, nothing to do for the capital.
- Maisons never score boxes anyway: `box_room = { villa = 2.6 }` (styles/maghreb.toml:2039) has no maison key, so
  `room` is None and `place_box` returns the first box that fits (villa.py:514-515), with no float compare.

## Ain Chilel (the `villas` town, where the box_room replans really run)
- 178 villas planned, 0 crashes, 23 s. Only 2 `place_box` calls score boxes: villas 307 and 388 (both still fail
  rooms.check). Villa 369 (passes) never runs the scored search, so its 1.07 -> 1.83 s (review-villas finding 3)
  is not the box scoring; probably the `little` replan.
- Both have an EXACT tie at the top (gap 0.0): 307 boxes 10, 14, 17 at 21.975989868 m2; 388 boxes 12, 14 at
  20.871159850 m2. `max` keeps the first (10, 12), so the pick is stable on this machine.
- Both also have a NEAR tie about 5e-7 m2 below the best (307: 21.975989314; 388: 20.871159333 at box 9). So the
  float noise between boxes that are equal in practice is about 1e-6, far above 1e-9: a check within 1e-9 alone
  would miss it.

## Rounding change (finding, low, determinism across machines)
- citygen/interior/villa.py:518 -> replace `return max(fit, key=lambda t: t[0])[1:]` with
  `best = max(t[0] for t in fit)` and `return next(t for t in fit if t[0] >= best - 1e-3)[1:]` (ties within
  1e-3 m2 go to the first box in the walk, with no rounding edge, unlike `round(a, 3)`). 1e-3 inline like the
  1e-4 on villa.py:513, or a toml key if preferred.
- Effect, checked on the recorded scores: 307 keeps box 10; 388 moves from box 12 to box 9 (the earlier box
  5e-7 m2 smaller). `round(a, 3)` and a 1e-6 tolerance pick the same. So the change is NOT byte-identical: 388's
  rooms.json changes (it fails before and after; re-run its rooms.check when applying). Capital: unchanged (none).
