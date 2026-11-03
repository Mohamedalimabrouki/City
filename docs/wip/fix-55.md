# fix-55: three fixes in citygen/interior/kit_life.py (from shot-55 and review-55)

- vase_flowers: each head (2 red, 1 green sprig) now has a thin green stem (`_tube`, 6 mm) from inside the
  vase (z 0.12) through the neck (passes at radius <= 0.027 of the 0.03 mouth) up to the head. 72/80 tris.
- fruit_bowl: the lathe outline now starts at (0, 0) and ends at (0, 0.03) on the axis, so the bottom is
  closed inside and out (no more dark hole). To stay in the 70-tri budget the inside runs straight from the lip
  to the centre (a shallow cone) instead of a flat inner floor. 64/70 tris.
- pot_jasmine: new `_lathe_radius` finds the bush's real surface (the 8-sided faces, not the profile corners)
  at each flower's height and angle; each flower sits 5 mm outside it, capped so it stays within W x D + 1 cm.
  The 3 hidden flowers now show 2.1-2.9 cm of their 5 cm; extent 0.46 x 0.46 (test allows 0.02). 128/220 tris.
- Tests: `pytest -q -k "kit or home"` 10 passed. No render looked at (no snapshot in the brief).
- Left: nothing of the brief. Not done: the other shot-55 ideas (more jasmine flowers, plates, basil).
