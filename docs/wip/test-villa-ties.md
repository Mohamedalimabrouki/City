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
(pending: see below)
