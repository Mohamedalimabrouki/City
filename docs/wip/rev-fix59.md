# rev-fix59: review of the last commit on wip/fix-59 (7130a01), 3 November

Checked: `pytest -q -k "river or hydro or lake"` here: 6 passed, 1 xfailed, 1.8 s. All new names are imported
(pytest, Point, Polygon, load_config, drainage). No randomness added; the 10 m and 8 m limits are test-only.
The wet and dry valley tests check real behaviour (non-empty `into`, one outlet, mouth kinds) and can fail.

## Findings
1. citygen/hydro.py:318-319 (previous commit), low: the new docstring is still not the whole rule. The code is
   `z[-1] = max(min(z[-1], z[-2]), zm)` then a running minimum, so when the tributary's own end and the point before
   are both above the main bed it ends ABOVE the main bed (on the lower of the two), not on it. Fix (words only):
   "ends at the lower of its own end and the point before, but not under the main bed there; the profile never
   rises, so if the point before is already under the main bed it ends below it".
2. tests/test_hydro.py:120-129 (xfail test), low: `xfail(strict=True)` accepts any failure, and the ridge value is a
   narrow window: probed with the same valley, ridge 20 m passes, 29 m fails on the `_ends_in` line (the right
   reason, checked), 40 m fails on `len(lakes) == 1` (two salt lakes). A toml change to `lake_min_area` or `cell`
   could move the window and leave a wrong-reason xfail that still reads green. Fix: check the preconditions (one
   salt lake, at least one "basin" river) for ridge=29 in a normal test, so the xfail can only stand for finding 4.
3. tests/test_hydro.py:42-44, very low: the bed is bounded under the ground but not above it (only at the source).
   Probably fine since the profile is a running minimum of ground heights; no change needed.

Left: I did not count how often finding 1 happens in the quick world.
