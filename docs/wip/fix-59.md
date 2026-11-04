# fix-59 (from wip/review-59), 3 November, 20:54 UTC

## Done (output byte-identical: in citygen only a docstring changed, no code line)
- Finding 3: `_snap`'s docstring (citygen/hydro.py:318-319) now says what the code does: the end height is the main
  bed unless the point before is lower; the profile never rises, so then the tributary ends below the main bed.
- Finding 6: `test_river_beds_never_rise_downstream` can now fail: the bed must start within 10 m of the ground at
  the source and never lie 8 m or more under the ground (quick world: worst 6.5 m and 4.5 m).
- Finding 7: a small synthetic country `_Valley` in tests/test_hydro.py (20 km, 134 x 134 cells, 0.04 s a run):
  a wet hollow fills to a fresh lake, its river ends in it (mouth "lake") and one outlet leaves it to the border;
  a dry hollow keeps a salt lake (mouth "basin") and no river starts in it; a dry hollow split by a 29 m ridge into
  two pockets is an `xfail(strict=True)` test that reproduces finding 4 (the river ends in the pocket with no shore).
- `pytest -q -k "river or hydro or lake"`: 6 passed, 1 xfailed, 2.1 s.

## Open questions for Ali (not changed, they change the world)
- Q1, finding 1 (water-balance rule, hydro.py:173-178): a steppe or desert basin whose inflow gives fewer wet cells
  than `lake_min_area` drains through to its spill instead of keeping its water. Suggested fix: for a salt basin use
  `wet = max(wet, min_cells)` instead of `continue`, so every dry basin over 3 m and 0.5 km2 stays endorheic.
- Q2, finding 4 (salt pockets, hydro.py:84 and 195-203): keep only the connected part of `water` that holds the basin
  bottom (`ndimage.label(water)`, keep the label at `bottom`) and let the other pockets drain into it; then remove
  the xfail mark of `test_a_salt_basin_in_two_pockets_draws_the_pocket_its_river_ends_in`.

## Left
- Finding 5's drainage-order test (`flat[i] > flat[recv[i]]`) needs `flat` and `recv` from inside `drainage`; not done.
- Findings 2 and 8 were outside this brief.
