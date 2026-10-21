# Prompts 59-69: countryside

Read only the section of your prompt. `CLAUDE.md` gives the routine every prompt follows.

- Country-scale looks: the country map (`output/*/maps/country.png`) is the cheapest picture;
  stack the before and after maps with Pillow.
- 3D looks: build a countryside box with `before_after.py --build-args "--area
  box:X0,Y0,X1,Y1 --out output/box"` (km). A town's id or name may change when settlements
  move, so name places by a box, not by `city:NAME`, in prompts that move settlements.
- The quick build's tiles only cover the capital, so the normal fingerprint cannot see the
  countryside: also fingerprint the box build before and after (`fingerprint.py save NAME
  output/box/<world folder>`, then `compare`).
- Inland water uses the palette materials `water_lake`, `water_river` and `water_pool`, never
  `water` (the Blender scripts hide `water` because they draw their own sea).

## 59. B1a - Rivers from the shape of the land

Model: Sonnet | Effort: high | Size: M | Needs: 1 | Look: country map

**Do.**
1. New `citygen/hydro.py`, called in `world.generate_world` right after the terrain, on a coarse
   grid (`[rivers] cell`, about 150 m):
   - priority-flood seeded from the sea and the map border with an epsilon gradient (Barnes et
     al. 2014), or each cell's receiver taken from the flood order, so every land cell drains
     (D8 directions are undefined on plain filled flats);
   - a filled basin is a lake only if deeper than `[rivers] lake_min_depth` (about 3 m) and
     larger than `lake_min_area` (about 0.5 km2); small pits just drain;
   - basins in steppe and desert are endorheic: rivers end there (prompt 65 turns them into
     chotts); rivers may also leave the map at its border;
   - flow accumulation weighted by moisture (`terrain.moisture`); rivers where it passes a
     threshold; smoothed polylines; width from flow (square-root law); oueds in dry biomes are
     thinner and flagged seasonal.
2. Per river, store a bed profile: the filled height along its D8 path, made non-increasing with
   a running minimum. `World.rivers` (id, coords, widths, flow, seasonal, profile) and
   `World.lakes` (polygon, level, salt), exported in world.json (update SPEC sections 5 and 6).
3. The country map draws rivers (width by flow) and lakes.
4. No randomness needed: a pure function of the terrain. The country step stays under its
   10 s budget.
5. Tests: deterministic; every river's profile never rises downstream; every river ends at the
   sea, a lake, an endorheic basin or the map border.

**Check.** Fingerprint may change: `world`, `maps/country.png`. Plans and tiles must not change
yet. Look: the country map before/after.

**Done when.** A believable network: rivers start in the mountains, join, reach the sea or a
dry basin; thin oueds in dry country.

## 60. B1b - Valleys, lakes and water in the terrain

Model: Sonnet | Effort: high | Size: M | Needs: 59 | Look: aerial (box)

**Do.**
1. First, box builds: `select_area` uses the box center (with its ground height) as the focus,
   so the viewer loads the box's tiles, not the nearest settlement's.
2. The terrain height carves river beds to the stored profile: `height = min(terrain,
   bed(s) + bank(d))` with a smooth U shape and gentle banks (s = position along the river,
   d = distance from its center line), never relative to the local ground. Use a fast distance
   field (for example a float32 raster of about 20 m around the rivers, built once per world,
   sampled bilinearly); the height stays a pure function of position.
3. Lakes: terrain inside a lake at or below its level, a flat water surface at the lake level
   (generalize `water_mesh`, which only knows the sea at z = 0). River water in every tile: a
   ribbon at the profile's water level (the same z on both edges), material `water_river`.
4. New palette materials `water_lake` and `water_river` (`water_pool` exists since prompt 26);
   the viewer's `/^water/` rule already gives them the water look; add their shader to
   `tools/blender_beauty.py` (only `water` stays hidden there). lod1 tiles keep lake and river
   surfaces.
5. Order in `generate_world`: terrain, rivers, carving, then settlements and roads. Lakes count
   as water in `_place_settlements` (its `ok` test), in `_Router` and in `layout.land_near`;
   river-corridor cells cost `[rivers] road_cost` (about 8x), so roads cross rivers instead of
   following their beds; settlements keep their whole radius off beds and banks.
6. Budgets: country under 10 s; tile build time +20% at most.
7. Tests: no road point in a lake, nor in a river bed outside crossings shorter than 60 m; no
   settlement center within its radius of a bed.

**Check.** Fingerprint may change: `world`, `plan/*`, `tiles/*`, `maps/*`, `gazetteer` (and the
box build's parts). Look: `--view aerial` on a box around a river (choose it from the country
map).

**Done when.** Rivers in their beds with water, a lake with a flat surface, roads crossing
instead of following rivers; no seams.

## 61. B1c - Rivers in cities and towns

Model: Sonnet | Effort: high | Size: M | Needs: 60 | Look: aerial (box)

**Do.**
1. Settlement placement scores sites near rivers higher (never in the bed or on the banks).
2. Grade first, carve last: `Ground.height` (prompt 11) grades the uncarved terrain, then applies
   the same river and lake carve as the terrain, so bed and banks are identical inside and
   outside cities; blocks never cover the river corridor (the 60 m blur would otherwise fill
   the bed).
3. The city planner treats a river as a barrier: streets stop at it (bridges come in prompt 62),
   buildings keep off the water and its banks, a riverside walk follows it in towns; city maps
   draw the river.
4. Tests: in a river town, water z never rises downstream and lies 0.2-1.0 m below both bank
   tops; no building footprint touches the river corridor.

**Check.** Fingerprint may change: everything except `kit/*` (and the box build's parts). Look:
`--view aerial` on a box around a river town.

**Done when.** A river town looks natural on its map and in 3D, with no building in the water.

## 62. B1d - Bridges

Model: Sonnet | Effort: medium | Size: M | Needs: 61 | Look: aerial (box)

**Do.**
1. Where roads and streets cross rivers: bridges with a deck above the water (`[bridges]
   clearance`), parapets, and piers or arches by span (stone arch bridges for old roads and
   medina streets, concrete beams for main roads). Over a bridge the road ribbon takes its
   height from the deck (a straight line between the abutments), not from the carved ground.
2. City bridges go in a new `CityPlan.bridges` list, never in `plan.buildings` (building numbers
   are used by interiors, entrances and canon pins). Country-road bridges are computed per tile
   from the roads and the rivers, so `world` does not change.
3. Streets cut by the river in prompt 61 cross on bridges where the street plan needs a link;
   maps mark bridges.

**Check.** Fingerprint may change: `plan/*` (bridges, streets), `tiles/*`, `maps/*`. Look:
`--view aerial` on the same box as prompt 61.

**Done when.** Every crossing has a bridge and no road dips into the water. Tick B1.

## 63. B2a - Fields and cactus hedges

Model: Sonnet | Effort: high | Size: M | Needs: 60 | Look: aerial (box)

**Do.**
1. Around villages and towns and along roads, in green and steppe biomes: strip fields
   perpendicular to roads near villages, irregular Voronoi fields on open plains. Fields come
   from pure functions of position: world-space cells (about 150-300 m) each with a seed point
   from `stream(seed, "fields", ci, cj)`, so any tile finds the same fields. Keep fields out of
   settlements using world-level circles (radius x 1.15), never the planned city boundaries
   (a tile must not differ between `--area capital` and `--area all`), and out of rivers and
   lakes.
2. Crops as terrain colors per field (wheat gold, barley pale, fallow brown, green fodder,
   plowed earth). Split terrain squares along field edges (or snap field edges to the 8 m grid)
   so colors meet the hedges cleanly instead of in staircases.
3. Field edges: rows of prickly-pear cactus (tabia, an instanced `cactus_hedge` piece) or low
   dry-stone walls (`stone_wall`), by region; own streams.
4. Budget: at most 400k drawn triangles per countryside tile.

**Check.** Fingerprint may change: `tiles/*` and the new `kit/cactus_hedge*,kit/stone_wall*`
parts (and the box build's tiles). Look: `--view aerial` on a box around a village.

**Done when.** A patchwork countryside around villages from the air, continuous across tiles.

## 64. B2b - Olive groves and orchards

Model: Sonnet | Effort: medium | Size: M | Needs: 63 | Look: aerial (box)

**Do.** Olive groves in rows (the olive pieces of Q1, instanced, with slight jitter): 8-12 m
apart in green biomes, 18-24 m in the steppe (Sfax style), on hills near villages; citrus
orchards near the coast (if prompt 24 added a citrus tree, else olives), almond trees in the
mountains (a variant of the broadleaf crown, own stream); whole fields from prompt 63 become
groves; tile-local; at most 400k drawn triangles per tile.

**Check.** Fingerprint may change: `tiles/*` and only new `kit/*` tree variants (and the box
build's tiles). Look: the same box as prompt 63.

**Done when.** Groves show from the air; drawn triangles per tile within budget. Tick B2.

## 65. B3 - Salt lakes and dunes

Model: Sonnet | Effort: high | Size: M | Needs: 60 | Look: aerial (box)

**Do.** Chotts come from the hydrology: the endorheic dry basins of prompt 59 become salt flats
(a level salt crust at the basin level, a pale slightly shiny material, a dry rim, no water
surface); oueds end in them. Dunes: directional ridged noise (crescent-like ridges) in the far
desert, a pure function of position. Terrain and biome changes only; maps show both.

**Check.** Fingerprint may change: `world`, `tiles/*`, `maps/*` (and plans if a settlement
moved). Look: `--view aerial` on a box over a chott or dunes.

**Done when.** A salt flat and a dune field read clearly from the air and on the map. Tick B3.

## 66. B4 - Oasis towns

Model: Sonnet | Effort: high | Size: M | Needs: 1 | Look: aerial (box)

**Do.** Desert settlements get a palm grove (dense palms, small walled gardens, irrigation
channels as thin `water_river` ribbons), mud-brick colors and decorated brick facades (Tozeur
style, through palette and textures), narrower alleys. A new district kind `oasis`: follow SPEC
section 10 "New district kind" step by step. New pieces on their own streams.

**Check.** Fingerprint may change: `plan/*`, `tiles/*`, `maps/*`, `gazetteer` for desert towns
only (and new `kit/*` pieces by name). Look: `--view aerial` on a box around a desert town.

**Done when.** An oasis town reads clearly from the air. Tick B4.

## 67. B5 - Hilltop ksar villages

Model: Sonnet | Effort: high | Size: M | Needs: 12 | Look: aerial (box)

**Do.**
1. Only villages in steppe, desert or rock biomes with at least `[settlement.village]
   ksar_relief` meters of relief inside their radius become ksour (the quick world's steepest
   steppe village has about 17 m, the full world's reach about 60 m; green northern hill
   villages stay as they are).
2. A ksar: ochre stone houses terraced up the slope (each house steps with the ground), a ghorfa
   granary (vaulted cells stacked two to four high with outside stairs) at the top, narrow
   stepped lanes; style-driven (a `[settlement.village]` rule and new building functions).
3. `[ground]` gets per-kind values, so ksour use a small blur (about 15 m) and one terrace per
   house instead of the city grading that would flatten the slope.

**Check.** Fingerprint may change: `plan/*` of affected villages, `tiles/*`, `maps/*`. Look:
`--view aerial` on a box around a steep dry village.

**Done when.** A ksar climbs its hill with a granary on top. Tick B5.

## 68. B6 - Regions and natural names

Model: Sonnet | Effort: medium | Size: S | Needs: 59, 65 | Look: country map

**Do.** Governorates (the land around each city and town), named mountain ranges (Djebel ...),
capes (Ras ...), bays, rivers (Oued ...), lakes, big salt flats (Chott ...) and small ones
(Sebkha ...), from `NameMaker` templates in the style on their own streams; country map labels
placed without collisions (Latin only: Pillow here cannot shape Arabic); a gazetteer chapter;
world.json fields.

**Check.** Fingerprint may change: `world`, `maps/*`, `gazetteer`. Look: the country map.

**Done when.** The country map reads like an atlas page with regions and natural names. Tick B6.

## 69. CP6 - Checkpoint: countryside

Model: Opus | Effort: medium | Size: review | Needs: 59-68 | Look: country map + aerial

Follow the checkpoint routine of prompt 6 (`## 6.` in docs/prompts/01-foundations.md) for
prompts 59 to 68, comparing with `cp5` (pass `output/bodjantouna-42`) and with a box fingerprint.
Extra checks:
- Several seeds (`--seed 7`, `--seed 1234`, `--size-km 96`, with `--out output/seeds`): rivers,
  lakes, chotts and dunes stay plausible; no settlement or road in water.
- Country generation time and memory; tile seams over rivers and fields.
Save `fingerprint save cp6 output/bodjantouna-42`. Fix prompts go in `## 69.1. ...`.
