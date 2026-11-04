# Prompt 59 (rivers) helper notes - worktree /tmp/claude-501/rivers-59
## Done
- 19:35 quick build + fingerprint save before (282 parts); country map copied to output/checks/59_country_before.png
## Plan
- citygen/hydro.py: priority-flood (heap, epsilon) on [rivers] cell grid, receivers from flood order;
  basins = components of fill depth; lake if depth>lake_min_depth & area>lake_min_area; dry (steppe/desert
  bottom) basins endorheic (sink, salt lake); moisture-weighted accumulation; chains by main child;
  smooth (moving avg + Chaikin on x,y,w,z); widths sqrt law; seasonal by catchment moisture.
- World.rivers/lakes, to_json, country map draws, tests tests/test_hydro.py, defaults [rivers], SPEC 5/6.
## Next step
- write citygen/hydro.py
- 19:41 hydro.py works (full world: 157 rivers, 41 lakes of which 31 salt, ~4-5 s on the loaded machine; quick 11 rivers, 1 salt lake).
  Decision: lake size by water balance (`lake_area_per_flow` 0.04 km2 lake per km2 inflow): without it the noise
  terrain gave 89 lakes (63 salt) and blobs everywhere. Wet basins too big for their inflow just drain; dry basins
  keep a salt lake of the balanced size; the dry basin rim is re-flooded from its lake so rivers run to the lake.
  `dry_weight` 0.15 so desert storms still feed oueds. World, defaults [rivers], maps._draw_water done.
- Next: tests/test_hydro.py, SPEC 5/6/8, quick build, fingerprint compare, picture output/checks/59.png
- 19:47 tests/test_hydro.py (4 tests, ~1.1 s) pass; SPEC 4 (module table), 5, 6 updated. Running full pytest + quick build.
- Next: fingerprint compare before --allow "world,maps/country.png"; stack before/after -> output/checks/59.png; full-world map check

## Draft WORKLOG entry (lead pastes at top of docs/WORKLOG.md)
### 2026-11-03 - Prompt 59 (B1a): rivers from the shape of the land
- New `citygen/hydro.py`, called in `generate_world` right after the terrain: priority flood (Barnes 2014,
  epsilon 1e-4 m) on a 150 m grid from the sea and the map border, receivers from the flood, so every cell
  drains. Basins over 3 m deep and 0.5 km2 are weighed by a water balance (`lake_area_per_flow`): a wet basin
  its inflow fills is a fresh lake that spills on; one it cannot fill drains; steppe/desert basins are
  endorheic salt lakes of the balanced size (rim re-flooded from the lake). Flow = catchment x
  (0.15 + 0.85 x moisture); rivers from `min_flow`; main stem by biggest upstream flow; smoothed lines; width
  0.9 x sqrt(flow); oueds (catchment moisture < 0.3) seasonal and x0.6. Profile = filled height, running min.
- `World.rivers`, `World.lakes` in world.json; country map draws lakes, salt lakes, rivers by flow, oueds.
- Full world (64 km): 157 rivers (16 oueds), 41 lakes (31 salt). Quick: see report.
- Tests: tests/test_hydro.py (deterministic, profile never rises, every river reaches sea/lake/basin/border,
  oueds thin, nothing leaves a salt lake).
- Doubt for Ali/prompt 60: several salt lakes touch settlements (Sota, Chilel); prompt 60 makes lakes count as water.

## Draft HANDOFF lessons
- The noise terrain is full of deep closed hollows (89 basins > 3 m and 0.5 km2 on the 64 km world, one 140 km2
  and 171 m deep): filling them all to the spill gives a map of blobs. A water balance (lake surface per km2 of
  inflow) is what makes the lake count believable; keep it when prompt 65 turns salt lakes into chotts.
- Inside a filled basin the flood's receivers point to the spill, not to the bottom: an endorheic basin must be
  re-flooded from its own lake (tiny epsilon so it stays under the spill) before accumulating flow.
- Filled heights strictly fall along receivers, so `argsort(-filled)` is a valid upstream-first order (no Kahn).

## ROADMAP line
- [x] 59 B1a Rivers from the shape of the land (citygen/hydro.py; World.rivers, World.lakes; country map)
- 20:00 DONE: pytest 167 passed (13 min, machine load 130+), quick build ok (world 1.2 s loaded), fingerprint:
  only world (9.6k -> 34k bytes) and maps/country.png changed. Pictures: output/checks/59.png (quick), 59_full.png (64 km).
  Quick world: 11 rivers (2 oueds; 6 sea, 2 basin, 2 join, 1 border), 1 salt lake. Full: 157 rivers (16 oueds), 41 lakes (31 salt).
  Option tried: min_flow 2.0 gives 221 rivers, more headwaters in the hills (not applied; tests ran with 3.0).
- Next step (lead): review, paste WORKLOG/HANDOFF/ROADMAP drafts above, commit hydro.py, world.py, maps.py,
  defaults.toml, SPEC.md, tests/test_hydro.py.
