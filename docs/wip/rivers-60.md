# Prompt 60 (B1b valleys, lakes and water) helper notes - worktree /tmp/claude-501/rivers-60
Branch `wip/rivers-60`, built on `wip/rivers-59` (prompt 59 as it stands, notes in docs/wip/rivers-59.md).
Started 20:33 UTC on 3 November, saved at 20:52 (weekly usage reset at 21:00). Prompt 60 is PARTLY done.

## Built (items 1 and part of 5, plus prompt 59's open item)
- Item 1, box builds: new `build.focus_xy(area, region, focus)`; for `box:` builds the tile order and the
  `tiles/index.json` `focus` (x, y, and z from `ground.surface`) are the box center, so the viewer and
  `blender_beauty`'s aerial camera look at the box, not at the nearest settlement. `select_area` itself is
  unchanged (it still returns the nearest settlement as the focus settlement: `interior`'s default city and the
  camera `views` keep working). Other areas: same point as before.
- Item 5 (lakes part) = prompt 59's open item: lakes, fresh and salt, count as water.
  - `hydro.lake_shape(lakes)` (one prepared union) and `hydro.in_lake(lakes, X, Y, margin)`.
  - `world._place_settlements(..., lakes)`: lake cells are not `ok`, and a candidate whose disc touches a lake
    is skipped (after its draws, so no draw is added; a skip shifts later places, like any other skip).
  - `world._Router(..., lakes)`: lake cells and cells within one `routing_cell` (200 m) of a shore are water
    (without the margin the smoothed road line cut 5-20 m into two lakes on the 64 km world).
  - `layout.land_near(terrain, x, y, radius, lakes)`: a city's land leaves the lakes out (`plan_city` passes
    `world.lakes`).
- SPEC 5 (lakes count as water) and SPEC 6 (`index.json` focus) updated.

## Effects
- Quick build: fingerprint `compare before --allow "world,plan/*,tiles/*,maps/*,gazetteer"`: 282 parts,
  0 changed (the quick world's one salt lake touches no settlement or road; its capital is unchanged).
- 64 km world (not in the quick fingerprint): before, 9 settlements touched a lake (ids 3 and 7 cities, i.e.
  Chilel and Sota, 29 a town, 6 villages, overlaps up to 919 m); now none, and no road point lies in a lake.
  Because id 3 is skipped, every later place shifts: 127 of 131 settlements moved (ids 0-2 stay, so the
  capital does). So the full build's `world`, `gazetteer`, `plan/*`, `tiles/*` and `maps/*` all change; town
  names and ids move (any canon pin by id would land on another place).
- Country step still about 1.1 s for the 64 km world here.
- Box build check (20:41): `build --area box:48.54,45.97,49.74,47.17 --out output/box` (20 s, 16 tiles) around
  Zaouiet Rakeska (id 67, village, radius 230 m, a lake 242 m from its center: the only place whose land ring
  meets a lake): `index.json` focus = the box center (49140, 46570) with z 295.2 from the ground; its city map
  is fine (city maps do not draw lakes yet).

## Tests
- `tests/test_hydro.py::test_settlements_and_roads_keep_off_lakes` (64 km world, about 1 s): no settlement
  disc touches a lake, no road point in a lake.
- `tests/test_citygen.py::test_box_builds_focus_on_the_box_center` (focus_xy).
- `pytest -q` on the final code: 169 passed, 10 deselected (slow), 98 s; `build --quick` 9 s.

## Fingerprint parts changed
- Quick build: none (0 of 282). Full / box builds: `world`, `gazetteer`, `plan/*`, `tiles/*`, `maps/*`
  (settlements moved off lakes), and `tiles/index.json` focus for box builds.

## Not done yet (exact next steps, in this order)
1. Item 2, carving: after `drainage` in `generate_world`, build once per world a float32 raster (about 20 m,
   `[rivers] carve_cell`) around the rivers holding, per raster cell, the distance d to the nearest river
   center line and the bed height bed(s) of that nearest point (interpolate `River.profile` along
   `River.coords`; scipy `distance_transform_edt(return_indices=True)` on a rasterized center line gives both).
   Store it on the terrain (`terrain.carve = ...`) and apply in `Terrain.height`: `h = min(h, bed + bank(d))`,
   bank a smooth U (for example `half_w * (d / half_w) ** 2` inside the bed, then a gentle slope `[rivers]
   bank_slope` up to the ground), sampled bilinearly (scipy `map_coordinates(order=1)`), never relative to the
   local ground. Keep the height a pure function of position; check the country step stays under 10 s and the
   tile build time rises less than 20 %.
2. Item 3: lakes: inside a lake polygon clamp the terrain to `<= level` (same raster or `in_lake`); generalize
   `water_mesh` (sea at z 0) to a flat surface at `lake.level`; river water per tile: a ribbon at the profile's
   water level (`profile + [rivers] water_depth`, same z on both edges), material `water_river`.
3. Item 4: palette materials `water_lake`, `water_river` (`water_pool` exists); shaders in
   `tools/blender_beauty.py` (only `water` stays hidden); lod1 tiles keep lake and river surfaces.
4. Item 5 rest: `[rivers] road_cost` (about 8) multiplies `_Router.base_cost` on edges touching river-corridor
   cells (cells within half width + bank of a river line), so roads cross instead of following beds;
   settlements keep their whole radius off beds and banks (distance from the center to the corridor >= radius,
   the same skip as for lakes).
5. Item 7 tests: no road point in a river bed outside crossings shorter than 60 m; no settlement center
   within its radius of a bed.
6. Look: box builds before/after with the box `box:17.7,25.4,19.7,27.4` (mid course of river 0 on the 64 km
   world, flow 173 km2, to the sea) or `box:41.8,54.7,43.8,56.7` (river 1): `fingerprint.py save NAME
   output/box/<world folder>` before and after, then `.venv/bin/python tools/before_after.py --view aerial
   --build-args "--area box:17.7,25.4,19.7,27.4 --out output/box" --out output/checks/60.png`.

## Draft WORKLOG lines (for the lead, when prompt 60 is finished)
- Lakes count as water: settlements keep their whole radius off lakes (prompt 59 had put Chilel and Sota on salt
  lakes), roads keep a routing cell off the shores, a city's land leaves lakes out. Box builds focus on the box.
