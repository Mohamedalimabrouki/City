# Review 59 (rivers) - read-only, `git diff c48fb1e...HEAD -- citygen tests styles` (3 November, 20:50 UTC)
No code changed. Severity: H high, M medium, L low, N note.

## Determinism: OK
- No randomness; heap ties broken by cell index; stable argsorts; sets only for membership; `drainage` runs before
  `_place_settlements` and draws no rng stream, so settlements, roads and plans cannot move (matches the notes:
  only `world` and `maps/country.png` changed). Only one process is tested, but nothing depends on hash order.

## The prompt's numbers: match
- cell 150 m, lake_min_depth 3 m, lake_min_area 0.5 km2, epsilon priority flood from sea and border, square-root
  width, profile = filled height with a running minimum, World.rivers (id, coords, widths, flow, seasonal, profile)
  and World.lakes (polygon, level, salt) in world.json: all as asked. Extra: `lake_area_per_flow`, `dry_weight`,
  `min_points`, fields `mouth`/`into` (additive, fine).
- 10 s country budget: hydro alone ~4-5 s on the loaded machine for the 64 km world; the whole country step was not
  timed. Fix: time `generate_world` on the full world once on an idle machine.

## Findings
1. citygen/hydro.py:173-178 - M - deviation from the prompt: the water-balance rule drops steppe/desert basins
   whose inflow gives `wet < min_cells`, so some dry basins over 3 m and 0.5 km2 are NOT endorheic and rivers run
   through them to the spill (the prompt says steppe/desert basins are endorheic). Fix: keep every dry basin
   endorheic with a lake of at least `min_cells`, or have the owner accept the rule in the prompt and SPEC.
2. citygen/hydro.py:272 (with 97) - N - the profile is the filled height, as the prompt asks, but in the wet
   basins that the rule above lets drain, the bed runs at the spill level above the hollow (notes: one basin
   171 m deep). Fix: before 3D river beds use `profile`, test `max(profile - terrain.height(coords))` and lake
   or carve those basins.
3. citygen/hydro.py:327-328 - L - in `_snap`, `max(..., zm)` is undone by the following `np.minimum.accumulate`
   whenever zm > z[-2], so "never below the main river's bed" does not hold. Fix:
   `z = np.maximum(np.minimum.accumulate(z), zm)`.
4. citygen/hydro.py:84 and 195-203 - L/M - a salt basin's `water = m & (h <= level)` can be several pockets;
   `_lake` keeps only the biggest ring while every pocket gets `lake_id` and `recv = -1`, so a river can end in a
   pocket with no drawn shore (the mouth test would fail; the quick world has 1 salt lake, the full one 31).
   Fix: keep only the connected part of `water` that holds the basin bottom (`ndimage.label`).
5. citygen/hydro.py:87-97 - L - "highest first is upstream first" after the salt re-flood is assumed, not
   checked; on a filled flat wider than about 100 cells (0.01 m / EPS) it could break and flow would be lost.
   Fix: a test `assert np.all(flat[i] > flat[recv[i]])` for every cell with a receiver.

## Tests of the output
6. tests/test_hydro.py:39-42 - L - `test_river_beds_never_rise_downstream` cannot fail: `_rivers` and `_smooth`
   build the profile with `np.minimum.accumulate`. Fix: test the drainage-order invariant (item 5) and that each
   profile starts within a few meters of `terrain.height` at the source.
7. tests/test_hydro.py:15-20 - L - only the quick world (11 rivers, 1 salt lake): fresh lakes, lake outlets
   (`path = [b, i]`, mouth "lake") and multi-pocket salt basins are never exercised. Fix: a small synthetic
   terrain (a bowl with a spill, one in desert) or one slow-marked full-world test.
8. citygen/export/maps.py:118, citygen/hydro.py:159 - L - drawn width `0.8 + widths / 6.0` px and the basin
   threshold 0.01 m are hard-coded. Fix: move them to `[rivers]` in citygen/defaults.toml if the owner tunes them.
