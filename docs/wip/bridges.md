# Bridges (prompt 62): helper's notes

Rounds 1, 2 and 3 are done: plan, heights, record, maps, structure, the nine fixes of the two reviewers (section 6). Nothing
committed or added to git. The lead's brief: `docs/wip/bridges-brief.md`.

## 1. What was done
- `citygen/city/bridges.py` (new): `deck_profile`, one rule for a viaduct and a low bridge; `Site` and `plan_bridges`, the
  places; `raise_decks`, the heights on the finished plan; `road_bridges`, a country road's on demand.
- `Bridge` in `city/model.py`, with `deck`, `locate`, `at`, `fade`. `CityPlan.bridges`.
- `carve.Sample` gained `water`, `half`, `river`: read only, the ground does not change.
- `plan_city`: `plan_bridges` after `link_banks`; riverside walks after it (they are cut by `through + decks`, the streets
  before the lanes as before, plus the bridges); `streets += decks` and `raise_decks` at the very end.
- `Ground.surface` on decks (`_deck_tops`, behind a box test); `STREET_LIFT["bridge"]` 0.17, under every other street's.
- `mesh/tile.py`: street ribbons and country road ribbons on decks (`road_parts`, `deck_coords`, `TileContext.decks`);
  `mesh/lod.py`: both at lod1 as ribbons (the ramps' ends lie on the lod terrain, the rest is the deck's height).
- `parking.walk_widths` and `crowd` leave kind `bridge` out. Maps, `plan.json` `bridges`, `streets.json` edges of kind `bridge`.
- Tests: `_crossing_links` is gone, the three graph tests are plain again, `tools/street_survey.py` prints one number.

## 2. Where I went another way, and why
- **Appended last, not right after the lanes.** Same index, but no planning step sees a bridge: `boulevard.sites`,
  `apply_massing`, `greenery`, `plan_props` all read the street list. That is what keeps buildings, households, souks,
  landmarks, port and props byte-identical. Walks and trees are told about bridges explicitly.
- **`riverside_walks` gets `through + decks`, not `streets`.** With the lanes in, the band would have moved everywhere.
- **`STREET_LIFT["bridge"]` under all kinds, not just under the quay's.** A bridge can end on a street or an alley; on a
  street its ribbon takes `tuck` (2 cm) under that street's real lift, read at the axis's end.
- **`ends` is where the whole width has left the street**, three lines tested: on a skewed bridge the middle leaves first,
  and a ramp begun there would stand up through the quay at one corner.
- **`Bridge.tilt`, new field.** A level deck on a quay or road with a cross slope makes a step up to 0.4 m at its edges. A ramp
  starts leaning with the land and is level across by the open part (`fade`). `Bridge.at` includes it, so `Ground.surface`,
  the ribbon and round 2 agree. The extra "highest of the three lines" requirement applies only near the water.
- **`street` crossings always keep their chord**, like connectors: they are the only join of a part of the street graph.
- **`thin_out` keeps a crossing that alone joins two parts**, even within `gap`.
- **New bridges fall back on any place between the quays** when no junction faces the river: without that some stretches
  stayed over 1 km.
- **A country ramp stops at a city limit** (`area`): 4 villages on seed 42 had a step of 0.3-0.6 m at the limit, where the
  road stops being drawn. There the air, then the grade give way, as in a city.
- **The record's `water` is the highest under the deck**; a river falls under a skewed deck.
- **`depth` 0.6**, not my first 0.7: it costs the low bridges less ramp.
- **lod1**: the ribbons take the deck's height already (it cost 5 lines); the box under it stays for round 2.

## 3. Numbers (final code; survey `br_survey.py` in the shared scratchpad)

| world | river towns | city bridges | arch / beam | dry | grade >= 0.10 | least air | road bridges | fords |
|---|---|---|---|---|---|---|---|---|
| quick 42 | 2 | 3 | 0 / 3 | 0 | 2 (max 0.137) | 1.21 | 4 | 0 |
| quick 7 | 1 | 8 | 4 / 4 | 0 | 3 (max 0.125) | 1.07 | 4 | 0 |
| quick 3 | 2 | 7 | 3 / 4 | 0 | 2 (max 0.157) | 1.16 | 6 | 0 |
| 64 km 42 | 16 | 59 (was 44 crossings) | 22 / 37 | 4 | 9 (max 0.164) | 0.90 | 45 | 4 |
| 64 km 7 | 12 | 92 | 36 / 56 | 0 | 8 (max 0.129) | 0.95 | 43 | 2 |
| 64 km 3 | 17 | 107 | 22 / 85 | 22 | 10 (max 0.140) | 0.90 | 50 | 4 |

- **Grade.** 34 of 276 city bridges are at 0.10 or more, against the brief's "all but the listed exceptions". Three causes: a
  quay falling along the river, so the two ends differ (quick 3 Resouna, 0.157); a real viaduct with its banks 10 m apart
  (Saza es Souk, 0.164, 27 m long); a wide deck aslant, whose water runs nearly from ramp to ramp (the 0.10-0.13 group, about
  35 m between quays). By the rule the air gives way before the grade, but I did not print `b.air` bridge by bridge; the causes are from
  the three I looked at (quick 3 Resouna in full, the others by their numbers).
  Lists: the `grade>=.10` lines of `br_full*.log`, `br_quick*.log` in the scratchpad. Country roads: at most 0.09 but for three: seed 7 a 13 m ford
  (0.12, where its end meets the road) and two on seed 3 (0.114), not looked at.
- **Skew.** One over 30 degrees, a `street` link (Menzel Takhouzount, 46, 84 m), kept for the graph. Longest 146 m (seed 3, Menzel
  Takhouzount, skew 18, not looked at). The lead's oblique ones are gone: Tararet 145-150 m now 113-115 m, square.
- **Gaps.** No stretch left without a place (`left` 0 everywhere). Largest gaps by my measure 482 and 550 and 701 m on the three
  64 km worlds. The 701 is Menzel Takhouzount, river 4, from 6410 to 7111 m. The plan believes it is covered (`left` 0), so a new
  bridge there must have been counted on that river and read by the survey on a tributary near a confluence. **I did not prove this.**
- **Dropped.** Four in all. Two have a chord that crosses no river, so both ends lie on one bank (seed 42 Tazoukine, seed 7 Noghinba); two
  were too near a better crossing (seed 3 Menzel Takhouzount, Menzel Kheches).
- **Street graph.** Quick: 0 under 99.5%. 64 km seed 42: 3 under 99.5%, the same three as `valleys.md` 5.9 (Zaouiet Noudel,
  Douar Koghka, Ksar Saba), none of them a river. 126 of 131 in one part.
- **Tests.** `pytest -q`: 274 passed, 28 deselected. `-m slow`: 26 passed, 2 xfailed (34 min, with the surveys running beside it). New tests take under 0.5 s of calls; their setup is shared fixtures. `build --quick` passes.
- **Fingerprint** (`--allow "plan/*,tiles/*,maps/*,files/cities/*/streets.json"`): 21 parts changed. `plan/goumosbane`: `bridges` added, `stats`, `streets` +1, `trees` -1
  (a riverside tree the deck cut off). Buildings, households, souks, landmarks, districts, port, props, world, kit: unchanged.
  **Not allowed and changed: `gazetteer`**: its line "N streets, N trees" counts that one tree less. `stats.streets` leaves bridges out,
  so only the tree count moves. The brief wants both "the tree row stops at a bridge" and "gazetteer unchanged": they cannot both hold. Lead's call.
- **Plan picture**: the capital's bridge at the river mouth reads as a white deck between two dark edges over the river.

## 3b. Open points for the lead
- The gazetteer, above: allow it, or print a tree count without riverside trees.
- 34 grades over 0.10: are they acceptable as listed?
- A ford's ribbon can stand up to 1.23 m over its bed. That is the rule of the brief (ground raised at `grade`), but round 2
  must close it, or `ford_grade` steeper than `grade` would keep it lower.
- 22 dry city bridges on seed 3 are `beam`, as the brief says, even in `street` crossings (7).
- Junctions: a country ramp is not checked against another road meeting it.
- `street` crossings keep a chord up to 46 degrees.

## 4. What round 2 reads from the record
Everything is in `CityPlan.bridges` and `TileContext.decks(k)` (`Bridge`, `city/model.py`). Nothing else is needed.
- `kind`: `arch`, `beam`, `ford`. `width`. `street` (-1 on a road), `road`, `along` (meters along the road at s = 0).
- `axis`: a straight line in a city, the road's own polyline in the country: use `shapely.line_interpolate_point`.
- `ends`: the ribbon is the street or the road beyond them. In a city s runs on past them to the two center lines.
- `s`, `z`, `floor`: stations, top of the ribbon, ground under the center line. There is a station at each kink, end,
  abutment, channel edge and pier, so linear interpolation is exact. `b.at(x, y)` is the drawn top anywhere on the ribbon.
- `span`: abutment to abutment. Outside it, from `ends` to `span`, the ramp is solid fill: its walls run from `b.at` at the
  ribbon's edges down to the ground. Fill height can reach `z - floor` at the abutment; read it, do not assume.
- `depth`: top of deck to soffit (0 on a ford). `air`: what it was given over the water.
- `water`, `water_width`, `channel`, `dry`, `river`.
- `piers`: stations inside `span`, between arches or beam spans. Arches are between `[span[0], *piers, span[1]]` and may be
  unequal: a pier moved out of the water of a narrow stream sits at the channel's edge. With low air an arch is a segment, not
  a half circle: its rise is `z - depth - max(water, floor)` at the crown.
- `tilt`, `fade(s)`: the ramp leans at its ends, level across on `span`: parapets on a ramp must follow `at` at the edges.
- `b.deck`: the outline between `ends`. Sidewalks on a deck are round 2's: then take the `bridge` lines out of
  `parking.walk_widths` and `crowd.people`, and add lamps through `[dressing] street_lamps` if wanted.
- A ford: `span == channel`, no piers, `depth` 0, a concrete ribbon; posts along `channel`. Its ribbon can stand up to 1.2 m
  over the bed (the ground raised at `grade` from the bank tops): it needs a fill or a slab face under it, or it floats.
- The ribbon's end on a street needs nothing: it lies `tuck` under the street's.
- The lod1 box goes under the ribbon `street_ribbons` and `road_ribbons` already draw.

## 5. Round 2 (structure): checkpoint log
- Four fixes done: `RANK`/`KINDS` know every street kind; `ford_grade`, and a ford now leans with an aslant bank (`Bridge.lean`,
  `_slab`), since the 1.23 m came from a level slab over an oblique bank, not from the ramps; paint sees the decks; lod imports.
- `stations`: arches also split by `arch_flat` (rise / length), so plan `bridges` moves (piers). `Bridge.old` is new.
- `citygen/mesh/bridges.py` written: `Frame`, `sweep`, arches, piers, concrete, ford, sidewalks, lod boxes. Tests added.

### 5.1 Round 2, final state
**The four fixes.** (1) `RANK`/`KINDS` hold every street kind (`MAIN`, `SIDE`), with a test. (2) `ford_grade` 0.16. The 1.23 m was not the
ramps: on an oblique bank a level slab sat on the high edge. A ford now lies on the land under its two edges and leans with it,
up to `ford_lean`: `_slab`, `Bridge.lean`, 1 m stations, not thinned. Highest ribbon over the bed, 64 km: seed 42 0.70 m (was 1.23),
seed 7 0.48 (0.73), seed 3 0.81 (1.12). (3) `make_paint(streets + decks)`: 14 more zebra bars on quick. They enter the list in the
middle, so 8 of the 9 quick tiles change bytes but not their triangles (the paint's order only). Zero parked cars in the 8 bridge
mouths of the 64 km capital (`bs_park.py`, the dresser's junction clearance already holds). (4) lod imports sorted.

**Two record changes.** `Bridge.old` (the warm stone), `Bridge.lean`. And `stations`: `arch_flat` 0.12, `arch_least` 4.5: 20 m on a rise
of 1.5 is three arches, not one flat lid; 7 m is one arch, never three of 2 m. Against r1 the piers of arch bridges move, so
`plan/*/bridges` changes on the cities that have some (none on quick: `compare r1` shows tiles only).

**Structure.** `citygen/mesh/bridges.py` as the brief says. `Frame` (points by station and offset), `sweep` (a bar along the deck, UVs
along it so stones run with the slope), `band` (a wall: UVs level, courses level). Ring stones are separate stones, long and short
by turns, with a real 2.5 cm joint, 6 cm proud. Barrel in `quay_wet`, since the viewer's fill light turned it orange in plain stone.
Trim is `curb` (long stones) outside old towns, for contrast. No randomness at all: no stream used.

**Numbers, seed 42, 64 km, all cities, towns and roads: 103 bridges and fords.** Median triangles: arch 1,248, beam 1,846, ford 278.
Largest arch 2,430, largest 3,334 (Tararet's 115 m beam, rails mostly): 2 over 3,000. lod1 box at most 158. Most in one tile 8,526 (a town tile with several bridges).
Tiles: the largest quick tile has 137,825 triangles and no bridge. Arches on 64 km: length median 7 m, 90% under 11, longest 13; rise to
length median 0.26, lowest 0.09.

**Pictures, frozen list (`docs/wip/bridges-*.jpg`, seen by me):**
- `capital-river`: the valleys step's camera. It holds no bridge: the nearest is behind it. Nothing else changed there.
- `capital-arch`: a `street` bridge in the capital, one arch, from the bank.
- `capital-beam`: the capital's arterial bridge from the river's axis, 18 m wide, white rail, abutments.
- `oldtown-arch`: Tikmine, three arches by the old town, warm stone, from the bank.
- `oldtown-ramp`: the same bridge from the riverside walk: the walk stops at the ramp wall, string course, end posts.
- `country-arch`: road 10, 37 m, three arches, cutwaters, from the water.
- `country-beam`: road 2, cap beam on three columns, iron rail.
- `ford`: road 118, the slab on an aslant bank, side face, posts and gauges.
Other cameras in the brief: Bordj Zasakel no longer exists on seed 42 (no city in that box on 64 km; on quick the town there is
Ritar, without a bridge, and the camera looks at nothing). "A long many-span": there is none now: seed 42's longest open part is
37 m (three arches), a beam's 31 m (one pier).

**Still weak, plainly.** (1) The ring's first stones run into the ground at a flat arch's foot: true to the arc, but a thin lit joint shows
there close up. (2) `quay_wet` on a pier is nearly black in this viewer, a hard band at the water. (3) Piers square to the axis, not to the
flow: on a skew bridge a cutwater meets the river aslant. (4) No road paint, lamp, walker on a deck. The sidewalks are mesh only, and
`Ground.surface` is the ribbon there, so walkers stay off (`crowd.people`, `walk_widths` keep their `bridge` lines; the brief's notes
offered taking them out, I did not: a walker would stand in the sidewalk). (5) A wall pier is tested but no bridge of seed 42 has one;
never seen in a picture. (6) Blender not checked (the lead's).

**Fingerprint.** `compare r1 --allow "tiles/*,plan/goumosbane/streets"`: 302 parts, 8 changed, all tiles, none outside. `compare before`: 22
changed, the only one not allowed is `gazetteer` (the tree count, open since round 1).

**Text for the WORKLOG.** Prompt 62 round 2: bridges now stand: `mesh/bridges.py` draws stone arches (barrel, ring of separate stones, cutwaters,
coped parapet), concrete beams (fascia, shadow line, girders, columns or wall piers, rail), ramp walls into the ground, a ford's slab and
posts, sidewalks on wide decks, a box on lod1. A ford leans with its bank. Arches split when too flat.

**Text for the HANDOFF.** A level slab on an aslant bank is what made a ford stand 1.2 m high, not the ramps: read the cross-section before
blaming a slope. A sunlit patch on a barrel looks like a hanging plate: trace a ray through the triangles before hunting a bug
(`bs_ray.py`). Town names and cameras in old notes go stale when a world changes: check a camera holds what it says.

**Text for the LEAD.** Boxes rebuild a place in 10 to 100 s: `build --area box:...`; a country box is 8 s, so eye-height work on one bridge is
cheap. A camera from the record (`bs_frames.py`: deck, foot, bed, under) saves guessing heights.

## 6. Round 3: the nine fixes of the two reviewers
Probes: `bt_*.py` in the shared scratchpad; `bt_lib.py` loads a 64 km world with all 131 plans (seeds 7 and 3: `bt_cache/`).

1. **Stone bar.** `Frame.points` clips to 0..length. End posts are now plain boxes (`_posts`), square to the axis, so a cap overhangs
   at the end too and a road's corner cannot fold one.
2. **One structure per crossing.** The pairs (`bt_p2.py`): seed 42: 5, seed 7: 0, seed 3: 6. Seven ride the host to the end (axes 0 m apart,
   100% of the ribbon on it), r2.2/r15.0 and r15.1/r26.0 nearly so, r3.0/r32.0 and r3.2/r17.0 fork off it (27-34% on it). So:
   `TileContext.road_own(k)` is the raw list, cached; `decks(k)` passes each through `follow` for every higher road whose deck overlaps
   by `share` m2. The wider road holds it, the first on a tie, and it reads only raw lists and higher roads: same bytes built in
   reverse (`bt_p2b.py`). The follower's ribbon is not drawn where the host's covers it (`under`): no z-fight and fewer triangles. Where
   only a part is covered it lies `tuck` under the host, with its lean, and eases back to its own height by its far end.
   Its structure is the longest run clear of the host's deck (`own`, `standing`): none for a rider, the rest for a fork,
   `ramp_only` if no open part is left. Numbers: 3 worlds, 11 followers, 8 no structure, 3 trimmed, 0 m2 of structures overlap.
   Drawn ribbon against host's, mesh on mesh (`bt_p2d.py`): at most 1.5 cm above it; **it sinks up to 7.4 cm** on two forks,
   hidden under the host: a flat strip laid aslant under a crowned deck. Its edges are within 3 cm. Against the bar's "3 cm": I left
   this; matching it would mean a ribbon with a middle.
   **A fork, plainly:** `bridges-fork.jpg`. It reads well from above. The host's rail runs on across the junction, and a wedge of ribbon
   between the host and the stub has no wall under it (r17.0: 11 m long). Fixing either needs a structure per side; 3 forks of 116 decks.
   Map: `_road_crossings` widest road first, a crossing of the same river within `gap` is the same one.
   **Seeds beyond the three** (`bt_scan.py`, 13 seeds, no cities): roads run parallel, their center lines 4-9 m apart. The first search
   missed them (it asked for road lines touching the deck), now fixed. Center line on the host: no structure, no ribbon there: the
   road narrows onto the host's deck. Center line never on it: a twin, keeps its structure, height eased: 5 such pairs in 13 seeds still
   overlap, 0.3-52 m2, parapets inside each other's deck by up to 1.7 m. None on seeds 42, 7, 3. **Open.** Also found there: two decks of one
   road overlapping (seed 14 r23): ramps that met were not merged; `road_bridges` now looks at the next bridge's ramp, not its water.
3. **Offsets.** `Frame.mitre`: the ribbon's mitres at the axis's vertices, interpolated. Against the ribbon's edge: 8-18 cm before, 2e-11 m after.
   Flips on seed 42: 7 to 0; UV stretch 11.8 to 1.9. **Not all gone:** seed 7 r32.0 keeps 2 flipped slivers (4 cm) and a UV stretch of 24: a kink
   0.9 m from the deck's end, where the ribbon's own inner edge folds back 5 cm. The frame follows the ribbon, on purpose.
4. **lod1.** `LodGround` is the drawn lod terrain across tiles; `ribbons` keeps a deck's ribbon over it. Terrain over a ribbon: 0.87 to 0.
   Box feet: 1.53 m over the ground to 0.4 under (`rev_b/p9.py`, foot measured on `LodGround`, 103 bridges). The 1.53 was not only the
   fine ground: stations are rounded to 1 mm, so the abutment's station read as open and the foot rose to the soffit; now a step at
   `span +- 0.02`. A ford's box is under its lifted ribbon by up to 1.37 m: it is buried in the terrain there, nothing shows.
5. **`opening`** on stations a meter apart, in `_finish`. Resouna 7: 9.3-109.7 to 23.3-96.3; Bou Nongofir 4: 22.1-46.8 to 22.1-31.1, no pier. The rule cuts both
   ways: road 10 of seed 42 opens from 23-60 to 12-71, five arches, since a thinned station had stopped it early. `b.floor` comes from the dense
   grid too. `fade` is 1 at the ends always, over a meter at the least.
6. **Ford ends** (`_ford_ends`). Lip 0.31 to 0.00 on all 9 fords of the three worlds. The top comes down to the end at `ford_grade`, so the center lies up to 31 cm
   under its road height at an end (r4.0): as the road's own ribbon does, flat over a crown. Bridges' ends, not asked for, same probe: beams at most 9 mm; arches 14 cm on r32.0 seed 7 (that kink), 6.5 cm on seed 3 r120.0 (not looked at).
7. **`rivers`.** All rivers under the three lines of a deck, in `plan.json`. Menzel Takhouzount 16: (4, 69), 11: (13, 37).
8. **`fill`.** Counts from the last bridge within `every` before a stretch. Menzel Kheches river 2: 4413, new 4879, 5108: 695 m to 466 m. One bridge more there.
9. **Small.** Sidewalk stops at the curb, same height. No skirt of no height. `wet_band` 0.18: a thin dark line at the foot, still dark, no longer a band
   (`bridges-country-arch.jpg`, `bridges-oldtown-arch.jpg`). It is the waterline's shadow now; I would leave it.

**Gates, final code.** `pytest -q`: 293 passed (10 new, under 0.5 s of calls, all fail on the r2 copy). `build --quick --force`: passes.
`fingerprint compare r2`: 302 parts, 1 changed: `plan/goumosbane/bridges` (`rivers`; spans and piers, fix 5). Quick tiles do not change: no bridge stands in them. On 64 km,
`plan/*/bridges` changes, and `streets`, `trees` where fix 8 adds a bridge (Menzel Kheches). Not run: `-m slow`, the surveys, Blender (the lead's).

**Pictures** refreshed: country-arch, oldtown-arch, ford, from their cameras; new: fork. Not refreshed: capital-*, country-beam, oldtown-ramp (no fix shows there, beyond spans I did not check there).

**Text for the WORKLOG.** Prompt 62 round 3: nine reviewer fixes. One structure per crossing (`follow`, `standing`, `road_own`), offsets on the ribbon's edge (`Frame.mitre`), lod1 on its own terrain (`LodGround`), the open part read a meter apart, fords level with the road at both ends, `Bridge.rivers`, `fill` across a hole, small mesh fixes.

**Text for the HANDOFF.** A list of decks searched by road lines misses a parallel road whose deck overlaps but whose line does not touch: search by the deck plus a half width. A flat ribbon has only edges: compare what is drawn, mesh on mesh, not the height function. Thinned stations answer "where does the slope end", not "where does a clearance end": read clearances on the dense grid. A station rounded to 1 mm can land on the wrong side of the value it was rounded from.

**Text for the LEAD.** `TileContext(world, [])` scans a seed for road decks in about a minute: the 13 seeds of `bt_scan.py` found what the three worlds could not. Print the pairs before deciding a rule: the riders, forks and twins asked for three different answers.

## 7. Round 4: everything left open (a fresh helper; order of the brief, section 8)
Probes: `bu_*.py` in the shared scratchpad, box builds `output/bu_*` (deleted at the end).

1. **Long bridges, looked at** (Tararet 0, Tikmine 4, Noghinba 30 on seed 7, Menzel Takhouzount 11 on seed 3). Stone viaduct and beam read well. Wrong: a deck over
   two arms of a river has one `water`, the higher arm's: every pier on the land between stood in a dark wet band 1 m over the grass, and arches sprang from it (Noghinba:
   water 17.3, grass 16.5). Now `Bridge.parts`: each wet stretch with its own level (`level_at`), read by `spring_at`, `_pier`, `_concrete_pier` and the arch count. Noghinba: 9 flat arches to 7 taller ones.
   Menzel's 98 m beam: 1.5 m over the grass, cap beams lay on it. Now `pier_low` (1.4 m): a low wall, no cap beam. Wall pier (`pier_tall` 5 m) exists on no bridge of the three worlds:
   tried with `pier_tall` 1.8 on Tararet: a wall under the cap beam, it reads as a hammerhead, fine. Ramp into open part fine, no change. Found by the way: a sidewalk sliver that GEOS `segmentize`
   splits in two crashed `walk_meshes` (seed 7, Noghinba, tile of walk 3079): loop over `polygons(...)`.
2. **Forks.** A real Y: `follow` keeps `Bridge.walls`, the runs of each edge off the host's deck, each from where that edge leaves it; `Frame.side`, `walled`, `rail`, `opening`, `run`, `across` read them. Where the wedge lies over the open
   part the fork is a slab (`forked`: kind beam, its own piers): a wedge has no room for an arch. `stopped` stops any parapet where another road's drawn ribbon crosses it, end posts at each stop; works for plain roads too (`ribbon_near`).
   Host and fork stay pure functions of raw lists: `TileContext.structures` asks `decks` of all near roads, `decks` never asks `structures`. `bridges-fork.jpg` refreshed.
   r3.2/r17.0 is not a fork but an X: the road crosses the deck at 24 degrees, both rails stop twice.
3. **Skew.** `Bridge.skew`, k of (s, d) to (s + k d, d), from `skew_of`: the river read 20 m each way at the widest wet part. Square under 4 degrees, at most 45, and no more than the ramps leave room for. Piers, cutwaters, barrels, ring, spandrels, abutments, seats, slab soffit,
   girders, cap beams, columns run with the flow; deck, parapets, ribbon stay. Arches keep under the lowest soffit along the flow (`Frame.over_flow`), cap beams under the highest. Seed 42 roads: median k 0.245, 5 of 41 square. Forks: skew 0. lod1's plain box piers stay square.
4. **Life on a deck.** (a) `deck_paint`, in a list of its own, `plan.deck_paint`, drawn by `deck_paint_meshes`: appended to `plan.paint` they reordered the paint tree's answers and changed every quick tile's bytes. A dashed middle, two edge lines, on `Bridge.at`, segmentized a meter apart so they follow the crown. Kinds in `MARKED` over 8 m wide, by `Bridge.carries`.
   (b) `Dresser._deck_lamps`: the city's `street_lamp` on the parapet's line, staggered, stream `bridge_lamp`, spacing of `carries` in `[dressing] street_lamps`. (c) `Crowd._deck`, stream `people/deck`, chance `[people] deck_chance`. `Bridge.walkway` (from, to, height) is the one source for
   `Ground.surface` (`Bridge.top`) and the crowd's floors (`walkway_polygons`).
5. **Old town.** `[streets.surface] bridge_old = "paving"`; `_raise_city` sets it on the bridge's `Street`; no lines (`deck_paint` skips `b.old`).
6. **Twins.** `side_by_side`: the road beside a deck for 70% of it, the gap between center lines changing by at most 1 m: 3 of the 5 pairs of 13 seeds. No structure of its own (`Bridge.twin`); `widened` gives the host's record an axis moved toward the twin and the width of both,
   top and lean read from the two ribbons at the outer edges, `seam` a strip of asphalt under a slit. The other two pairs (r9/r25, r10.1/r33 on seed 10) only touch at an end and leave: both keep their structures. Their edges overlap by about 10 cm there, under the line `stopped` reads, so both keep their parapets, back to back for a few meters. Not measured mesh on mesh.
7. **Small.** Pale wedge: not the river's mesh. It lies on the ribbon and on past the ribbon's end, on the sea plane: the bed under translucent water near the mouth, where the carve dips under sea level (top and axis views, `bu_p2.png`, `bu_p3.png`). Left. Lit joint: it is the side of a joint between two ring stones, lit by the sky, under a pixel except from 3 m. Left.
   Fold: `forward` drops a step of an offset line that runs back at a sharp kink. Tile left out: `home`, `world.built_tiles`, the nearest built tile the deck reaches.

**Gates, final code.** `pytest -q`: 301 passed (8 new, each under 0.1 s, all fail on the committed code: they read fields and functions it does not have). `build --quick --force` passes. `fingerprint compare r3`: 302 parts, 1 changed, `plan/goumosbane/bridges` (`skew`; `plan.json` gains that field). Quick tiles byte-identical: no bridge stands in them. On 64 km, expected and not run: `plan/*/bridges`, `plan/*/streets` (paved old-town decks), tiles with a bridge. `buildings`, `households`, `kit/*`: unchanged on quick.
Tile check against a full `git archive HEAD` build of Tikmine's box (4 tiles): people and lamps gone 0, new 16 strollers and 3 lamps; two tiles the same size to the byte. That run was before `deck_paint` moved to its own list, which touches paint only. `PYTHONHASHSEED` 1 and 2: 8 of 8 tiles of that box the same bytes. Every road structure of seeds 42, 7, 3 (130): flips 0, NaN 0 (the 2 slivers of seed 7 r32 are gone). Seeds 8, 9, 10, 11, which hold the 5 pairs of the 13-seed scan (the other 9 seeds not rerun): 3 twins share a structure, 2 pairs that only touch keep theirs. Not run: `-m slow`, the surveys, Blender (the lead's); the capital and 64 km as a whole.

**Pictures (`docs/wip/bridges-*.jpg`, all seen by me, final code).** New: `long-viaduct` (Noghinba, seed 7, 7 arches over two arms), `long-arch` (Tikmine 4), `long-beam` (Menzel, seed 3, low walls), `skew` (road 10, k 0.79, from the water), `skew-beam` (road 2, column rows along the flow), `twin` (seed 9), `deck` (lines, lamp, strollers), `oldtown-deck` (paved). Refreshed: `oldtown-arch` from its old camera, `fork` from a new one (the old camera was not kept). Not refreshed: `capital-*`, `town`, `country-*`, `ford`, `oldtown-ramp`: their bridges now run skew where the river asks, so those pictures are out of date.

**Still weak, plainly.** (1) A fork off a stone host over open water is concrete: 1 in 13 extra seeds (seed 9, r34/r46); it reads as one wide deck, stone on one side and concrete on the other. (2) lod1's box piers stay square to the deck. (3) A twin's parapet stands on the widest gap between the roads: up to 0.5 m of slab shows beside the narrower stretch of the ribbon. (4) The line where a river's ribbon ends at the sea (`water_river` to `water`) shows at eye height near the capital's mouth: not asked for, left.

**Text for the WORKLOG.** Prompt 62 round 4: everything left open. Long decks read the level of each arm of a river (`Bridge.parts`), low beams stand on low walls (`pier_low`), forks are a real Y (`walls`, `rails`, `stopped`), skew bridges run with the flow (`skew`), a city deck carries lines, lamps and strollers (`deck_paint`, `_deck_lamps`, `Crowd._deck`, `walkway`), old-town decks are paved, two roads side by side share one structure (`widened`), offset lines drop a fold (`forward`), a bridge whose tile is left out goes to the nearest built tile (`home`). Fix outside the task: a sliver sidewalk that GEOS `segmentize` splits crashed `walk_meshes` on seed 7.

**Text for the HANDOFF.** A level read once for a whole deck is wrong on a long one: a deck can cross two arms of a river, with land between at another height; keep a value per wet stretch. A shear in stations (s + k d, d) gives a true skew bridge in few lines because the faces stay in the plane of the parapet: only the stations move, and the heights must be read at the moved stations (`over_flow`). Compare tiles against a whole `git archive HEAD`, not `citygen` alone: without `kits/` every kit piece changes name. `shapely.segmentize` can return a MultiPolygon for a sliver.

**Text for the LEAD.** Seeing a long bridge first paid: the worst fault of the round (a wet band 1 m over the grass) was in no bar and no test. A camera on the line of an abutment shows it as a stub: before calling a bug, compute where the wall runs. Tile check: instances by mesh and position against a build of HEAD, printing "same, gone, new": gone 0, new only strollers and lamps is the proof that streams held.

## Round 5: what the third reviewer proved

All seven faults reproduced with the reviewer's numbers, then fixed. Each has a test that fails with the fix undone (checked on a copy with the six code fixes taken out); the 7 new fast tests take under 0.1 s together.

1. **Skew ramp walls.** `_ramps` moved the wrong end. Seed 9, road 1, k 1.0, span 10-35. Before, left edge: walls 5.5-10 and 35-54, opening 15.5-40.5. After, read from the mesh: left 0-15.5 and 40.5-54, right 0-4.5 and 29.5-54, opening 4.5-29.5. Same on road 3 (k -0.51), road 5 (k -1.0), seed 42 road 10 (k 0.79). `bv_p1.py`.
2. **A bridge drawn twice.** Seed 9, box y 21.1-21.4, then 20.7-21.4 in one folder: `tile_83_41` is built again at 235,908 bytes, the same bytes as a fresh build (`cmp`), `tile_83_40` too; back to the small box: 272,272 bytes again; the same box twice: reused. `build --quick` twice: `tiles reused: 9 of 9`. **Not a new key, a note**: reuse is decided before the plans exist, and which bridges a tile draws needs the plans, so a key per tile would mean computing every bridge in the parent. Instead a tile's index entry lists the bridges of other tiles that reach it (`guests`: own tile, tiles reached, drawn here), and `finished_tiles` recomputes the rule (`homed`) for this build's tiles. It costs no plan, no world. Only a tile that would draw something else is built again; a full build draws no guest and reuses as before.
3. **The hole under a fork.** `_fork_soffit`: the deck less the host's (`Bridge.clear`, set in `follow`), cut at the stations and draped on the soffit. `p10.py`, seed 9, road 17: points with nothing under them 116 (29 m2) before, 0 of 389 after. Seen from below: closed. The interior girders still stop on `opening`'s diagonal; the soffit goes on past them, under 1 m over the bank there. No abutment at the stop line: the ground reaches the soffit there (0.19 m at s 32, under it at s 36).
4. **The slit by a twin's parapet.** `off[beside]`, and a strip along the outer edge (`Bridge.verge`, as wide as the gap moves, plus `verge_lap` 0.15 m under the ribbon), 5 cm under the top like `seam`. Whole road ribbons, `seam` and `verge` together (`bv_twinhole.py`): seed 9, 0.29 m2 without a surface, 11 cm wide, at station 1.7, on the ground at the ramp's foot; seed 8, 0. Before, slits of 0.06-0.79 and 0.11-0.39 m along the whole deck. The strip stands 0.6 cm under the twin's ribbon at worst on seed 9, 1.8 on seed 8.
   **Seed 11 is no real twin.** That deck lies 45 m from the center of Zamane el Bahri, radius 619 m: inside the town, a road stops at its limit, and with the plan `tc.decks(32)` holds nothing there (`bv_real.py`, confirmed by a build). `TileContext(world, [])` alone sees it. The reviewer's numbers there do improve (1.2-1.9 m to 0.08-0.76), but it has a 4.5 m pit at its start that no build can show, and I left that alone. Real twins: seeds 8 and 9.
5. **The spike.** `apart` drops near-equal stations. `p5.py`, `p6.py`, seed 8, road 2: axis 37.0, not 40.39; the last segments 2, 2, 1 m; both edges run straight to the end.
6. **The one-station ford.** `_road_bridge` returns None, `road_bridges` skips it. `ford.py`, seed 22: no crash. `scan.py` draws every bridge and lod1 box on seeds 22, 9, 8, 42, 3, 7, 11: no crash.
7. **The slow test.** What stood there: one `street_lamp`, 8.83 m off the axis of the capital's 18 m deck. Now `test_on_a_deck_stand_only_lamps_on_the_parapet_line_and_strollers_on_a_sidewalk`: passes.

**Checks.** `pytest -q`: 308 passed, 28 deselected, 70 s. `build --quick`: 9 tiles. `compare r3`: 302 parts, 1 changed: `plan/goumosbane/bridges`, only round 4's `skew` key (without it the digest equals r3's). No tile changed: none of the quick build's 9 tiles holds a bridge.

**Pictures (`docs/wip/bridges-*.jpg`, 13 refreshed, all seen by me, final code).** From recorded cameras: `capital-river` (the brief), `capital-arch`, `capital-beam` (`bs_cam42.txt`), `skew`, `skew-beam`, `country-arch`, `country-beam` (`bu_skcam.py`, flow and side), `fork` (`bu_fkcam.py`, seed 42, road 17). New cameras, the old ones were not kept: `twin` (from the air: no slit), `ford`, `capital-near`, `town` (now Tikmine: `town` had no camera), `oldtown-ramp` (on the walk, the same place by eye).

**Still weak, plainly.** (1) A fork's interior girders stop on the diagonal (see 3). (2) Two twins on one deck: the second's `seam` and `verge` replace the first's; never seen (3 pairs in 13 seeds, each on its own deck). (3) lod1's box does not know skew: its walls and soffit stay square. (4) The strip is plain asphalt under a ribbon that leans: on seed 9 `seam`, older, still stands up to 12.6 cm over the twin's ribbon.

**Text for the WORKLOG.** Prompt 62 round 5: seven faults of the third reviewer. Skew ramp walls end where the opening starts on their own edge, a tile's index entry notes the bridges of other tiles that reach it so reuse stays true between boxes, a fork's soffit is its deck less the host's, a strip closes the slit by a twin's parapet, near-equal stations are dropped, a one-station ford is no ford, the deck test says what stands on a deck. Seed 11's twin exists only without the town's plan.

**Text for the HANDOFF.** A probe with `TileContext(world, [])` sees decks that no build draws: a road inside a town stops at the town's limit. Before believing a fault, ask for the bridge with the plan. Reuse is decided before plans exist, so what a tile depends on must be written in its own entry, not computed in the parent.

**Text for the LEAD.** A record that holds a polygon (`clear`) ended a family of faults one diagonal could not: when a shape can enter and leave, stop describing it with a line. Check a reviewer's example in a real build: one of the three twins was not there.
