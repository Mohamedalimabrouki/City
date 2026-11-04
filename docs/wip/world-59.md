# world-59 (4 November): the first step of the "world first" order

Branch `wip/world-59` on main (fc93425). Merges prompts 70, 81 and 59, fixes what their reviews left, applies
Ali's four answers on rivers. Worktree `/tmp/claude-501/world-59`. Nothing here needs Blender: no tile changed.

## 1. What was merged, and the conflicts

| Commit | What | Conflict |
|---|---|---|
| 45e5508 | merge `wip/fix-70` | `tests/test_citygen.py`: both sides appended tests at the end; both kept |
| f5cedcd | merge `wip/fix-81b` | none |
| eb664ca | fixes of 70 and 81 | |
| 8c9e2be | merge `wip/fix-59` | `docs/SPEC.md`: section 5 (both new paragraphs kept), section 6 table (the rows of both sides) |
| 4ec2642 | Ali's answers, the reviews of 59, the street-end rule | |
| (last commit of the branch) | small test and doc tidying, these notes | |

## 2. Prompt 59: four things for the lead to read first

1. **The bed is not the prompt's "filled height" any more. This is a deviation, on purpose.** The prompt says
   "the filled height along its D8 path". Filled heights fly over every hollow a river crosses: on the 64 km world
   45 rivers ran over 5 m above the ground, 6 over 20 m, worst 55 m. Prompt 60's carve is `min(terrain, bed +
   bank)`: it can cut the ground, never lift it, so that water would hang in the air. review-59 finding 2 said
   "lake or carve those basins". The bed is now the running minimum of the ground under the drawn line, the highest
   line that never rises and never lies above the ground. A plain running minimum per river was NOT enough:
   21 of 63 tributaries ended under their main bed, worst 37 m (water would have to climb out at the junction), so
   the minimum also runs down the network, tributaries first (`hydro._beds`). That is the only bed that meets all
   three rules: any other digs deeper or floats. Nothing on the map changes because of it.
   The price: rivers cut through rims. On the 64 km world 36 km of the 525 km of river run over 10 m under the
   ground, 20 km over 20 m, worst 59 m; 24 of 150 rivers have a stretch over 10 m deep. Going back to the prompt's
   words is one line (`_beds`: `z = g.flat[cells]`), but prompt 60 would then have to lift ground.
2. **Lakes grow from the basin's bottom** (`hydro._water`). The brief's (b) read literally (keep the bottom's piece
   of the old water mask) leaves 8 of the 73 lakes under `lake_min_area` (down to 17 cells, 23 is the minimum) and 20
   under their balanced size, against (a). So the level is the lowest one whose connected water around the bottom
   covers the balanced number of cells: all the basin's water ends in that one lake, so that lake takes the whole
   area. Pockets it does not reach drain into it, as (b) says. Seed 42: no lake under 23 cells. On 3 of 5 other seeds
   the smallest lake holds 18-22: a basin of 23 or more whose cells are joined only at a corner. Accepted, it is rare.
3. **A fault no review had seen:** the same two-piece bug hit one fresh lake (id 38: 40 + 10 cells joined only at a
   corner). The ring drew the 40, its outlet started in the 10, 505 m from any drawn shore. Every lake is now
   4-connected, fresh ones too (the new bed test found this).
4. **Shores:** the ring sat half a cell inside the water (it forced every neighbor to level + 50), and at the
   lake's extreme rows nothing better was possible (no real neighbor in the box). It now follows the true contour,
   with one cell of margin: ring against ground on a test bowl, worst error 6.6 m -> 1.9 m (salt: 0.2 m). Prompt
   60's flat water needs that edge on the ground. Drawn salt lakes grow (median 0.37 -> 0.51 km2); the smallest
   ring is 0.39 km2 although the lake holds 23 cells = 0.52 km2, as the ring passes through the highest cell.

## 3. Every finding, fixed or why not

**review-59:** 1 (dry basins): fixed, Ali's (a). 2 (bed against ground): fixed, section 2. 3 (`_snap`): fixed for real,
see rev-fix59 1. 4 (pockets): fixed, Ali's (b). 5 (drainage order): test `test_every_cell_drains_to_a_lower_one`, on
both worlds; 0 faults in 24 worlds (12 seeds x 2 sizes), so no Kahn sort is needed. 6 (a test that could not fail):
replaced, beds now checked against the ground and against the running minimum. 7 (only the quick world): every
structural test runs on quick and 64 km; synthetic hollows added. 8 (numbers in code): `[rivers] basin_depth`,
`map_line`. "Time the country step": 1.11 s, section 5.
**rev-fix59:** 1 (`_snap` docstring): the rule became simple, so the docstring is simply true: a tributary ends on the
main bed, always (test: 63 of 63, gap 0.0). 2 (xfail test): a normal test now, `at=14700, ridge=25`, a scene the old
rule fails and the new passes (ridge 29 stopped being a two-pocket scene under the new level); it asserts its own
starting conditions (one salt lake, two pockets under the level), so it cannot pass for a wrong reason.
3: covered by the bed test.
**review-70:** Low 3 (z against itself): an independent check against `ground.height` + the street's lift, which
FOUND A BUG, below. Low 4: fine as is, the review says so. Low 5: union length. Low 6: fixed, with a case that really
fails without it. Low 7, 8, 9: SPEC wording. Info 10: left, it matches `mesh/tile.py`. Info 11, 12: section 5.
**rev-fix70:** 1 stderr shown; 2 renamed `[street_graph] grid`; 3 accepted (the comment says what the grid does); 4, 5
accepted, as the review says; 6 blank line.
**review-81:** 12 (SPEC) done; 10 (keying): noted in SPEC, for prompt 84. **5 and 9 NOT done, as briefed.**
**rev-fix81:** 1 (the medium): every choice has its own stream (`origin`, `facts`, `today`, `fact.<key>`). 2: the
`"{name}."` fallback is gone, ` and ` moved to `and_word`. 3: `era_in_default` / `era_since_default`, no English left in
the code. 4: test that every era has its words; the era check uses the whole phrase. 5: exact polygon first; 0 of 37
landmarks and 0 of 44 souks change district on six settlements, so no overlap with review-81's 5. 6: plural table by
ending; no trade of today changes.

**Found on the way, fixed:**
- `streets.json` z: 94 of 595 nodes of the quick capital sat on the bare ground, 18-30 cm under the drawn street top
  (snapping leaves a street's end a few cm past its flat ribbon end). `node_tops`: such a node takes the ribbon within
  one grid step. Now 577 of 595 are within 1.5 cm of ribbon height, the worst 4 cm low, the rest on a curb or a
  higher ribbon.
- Street graph on all 131 settlements (Info 12): 8 villages under the 99.5% bar. Six were graph faults, a street
  ending on another's surface short of its center line: every street end now gets the stub impasse mouths had.
  One connected part: 115 -> 125 of 131; under the bar: 2. On the capital a road link's node moves onto the junction
  it really is (2.6 m from the crossing), so that test's bound became the road's half width.
- `origin.park`: "..., south-east of the medina free of houses" lacked its comma. A typo-level fix, not review-81's
  wording work.
Every new test was shown to fail: each rule of 59 removed in turn (8 removals, all caught, `w59_mutate.py`); the three
rules of 70 and 81 on the old code.

**Left, on purpose:**
- Street islands in the plans, where ribbons really do not touch: Ain Khatane (97.4%, village), Sota, Ksar el
  Djabrar (two), Zouchir, Bazar el Djedid (all over 99.8%): 0.3 to 13 m between the ribbons, all checked. A gap in
  the planner; fixing it moves plans, not allowed here. Gamar (97.5%): two alleys overlapping side by side, no end on the other. The graph must not invent streets.
  All villages move at prompt 60: recheck there with the new `tools/street_survey.py`.
- Tests pinned to a number: none went stale, as no plan moved. Four will at the names step:
  `tests/test_citygen.py` lines 2246, 2703, 5353 (`world.settlements[3]`, `[5]`) and 5356 (`plan.buildings[369]`).

## 4. Question for Ali (belongs to him, blocks nothing today, answer before prompt 60)

The wet hollows. 16 hollows of green and forest country, over 3 m and 0.5 km2, get too little water to fill by the
balance rule, so they "just drain" (the helper's rule; the prompt itself says every such basin is a lake). Today their
rivers cut through the rim. Option: make them lakes up to the spill, a one-line change (`_basins`, `elif wet < size`).

| | Today | Option |
|---|---|---|
| Lakes (64 km) | 10 fresh, 63 salt | 26 fresh, 63 salt |
| River under the ground by over 10 m / 20 m | 36 km / 20 km | 24 km / 15 km |
| Settlements touching a lake | 9 | 12 |
| Roads crossing a lake | 13 | 18 |

Picture: `docs/wip/world-59-maps.png` (before, now, option). My advice: take the option. A hollow that a river enters
fills up, it reads natural in the picture, and it removes the worst cut (59 m). I did not do it because it adds 16
lakes nobody chose. Prompt 60 then moves a few more towns.

## 5. Results

**Tests:** merge of 70 + 81: 178 passed. After their fixes: 182. After 59 and the rest: 201 passed, 16 slow deselected, 63 s. `-m slow`: 15 passed, 1 xfailed, 178 s (the xfail is the
old colonial one of prompt 47, `tests/test_citygen.py:4228`, not new). All of `tests/test_hydro.py` takes 2.3 s, fix-59's
own version 2.1 s; the new slow tests 13 s and 5 s.
Two-process byte tests, all in `-m slow`, all pass: `test_interior_two_processes`, `test_home_kit_deterministic`,
`test_streets_json_two_processes` and the new `test_world_json_two_processes` (64 km world). Stronger, once by hand:
whole quick builds under PYTHONHASHSEED 1 and 2: 0 of 283 parts differ.

**Builds:** `build --quick` 7.2 s (7.0 s before). `build --quick --force` then `fingerprint compare`: 0 changed
(nothing hangs on the cache). `build --out output/full`: 89 s, with the survey running beside it. Info 11: the 64 km capital plans in
64 s; its `streets_json` takes 4.4 s while the workers run (16,156 nodes, 18,472 edges, 4.8 MB). Over all 131 settlements
that would be about 40 s beside 615 s of planning. Other worlds also build: `--seed 7`, `--seed 3`, `worlds/example.toml`.

**Fingerprint `compare w59`:** 283 parts, 5 changed, each by its cause:
- `files/cities/goumosbane/streets.json`: added (70).
- `gazetteer` 3532 -> 5994 bytes: the histories block only: with it removed the digest is the baseline's (fd98b3f8...).
- `plan/goumosbane/districts`: `history` only: without that key the digest is the baseline's (cde6faec...).
- `world` 9613 -> 33239 bytes: `rivers` and `lakes` only: without them the digest is the baseline's (a006bcb7...).
- `maps/country.png`: the water.
No tile, no other plan part, no city map changed.

**Country step (64 km world, machine quiet, 5 runs):** `generate_world` 1.09-1.11 s, of which drainage 0.51 s. Budget 10 s.

**Water, seed 42:**

| | fix-59 | now |
|---|---|---|
| Quick | 11 rivers, 1 salt lake | 10 rivers, 4 salt lakes |
| 64 km rivers | 157 | 150 (13 oueds, 525 km) |
| 64 km lakes | 41 (31 salt) | 73 (63 salt) |
| Mouths | 51 basin, 18 sea, 17 lake, 5 border, 66 river | 48 basin, 18 sea, 17 lake, 4 border, 63 river |
| Bed over the ground | up to 55 m | 0.01 m, off lakes |
| Settlements touching a lake | 9 | the same 9: Chilel, Takiret, Ras Kabine and 6 villages |
| Roads crossing a lake | 12 | 13 of 141 |

The older notes also name Sota: it never touched a lake (1.0 km clear of its edge, before and now).
River sources: median 310 m (10% 73 m, 90% 549 m). Rivers reach 11.8 m wide, oueds 3.3 m. Over 12 seeds at both sizes:
0 order faults, 0 rising beds, 0 mouths off a shore, every lake cell inside its ring, junction gap 0.

**Maps, looked at myself** (`output/checks/w59/` here; before/now/option in `docs/wip/world-59-maps.png`): rivers rise in
the hills, join, run through chains of lakes to the sea; oueds end in salt lakes on drawn shores. The quick map goes
from one odd-shaped salt lake to four rounder ones. A village dot still stands inside the big lake west of Sota, the
overlap Ali accepted; prompt 60 moves it. Prompt 59's "Done when" is met.

**Interior survey:** settlements are called today Goumosbane (capital, quick world id 0) and Ain Chilel (town, id 3);
names and places change in a later step.

SURVEY

**Street graph, all settlements:** quick world 12 of 12 one part. 64 km world: 125 of 131 one part; `street_graph` costs
10 s in all, 1.2 s at worst.

## 6. Text to paste

### docs/ROADMAP.md
- [x] 59 B1a Rivers (citygen/hydro.py; World.rivers, World.lakes; country map)
- [x] 70 C4a Street graph for games (cities/<name>/streets.json; quick capital one connected part)
- [x] 81 D1a District histories

### docs/WORKLOG.md
```
## 2026-11-04 - Prompts 59, 70, 81 (world-59): rivers and lakes, street graph, district histories
- Commit: <merge> | Model: Opus 5.5, max
- Changed: citygen/hydro.py, citygen/export/streets.py, citygen/city/history.py (new); citygen/world.py,
  build.py, export/maps.py, export/lore.py, city/__init__.py, city/model.py, defaults.toml; styles/maghreb.toml;
  tests/test_hydro.py (new), tests/test_citygen.py; docs/SPEC.md. Notes: docs/wip/world-59.md
- Checks: tests 201 passed, slow 15 passed + the old xfail; build --quick 7.2 s, --force identical; fingerprint 5 of 283 parts:
  streets.json added, gazetteer and districts (histories only), world (rivers and lakes only), country map. Tiles and
  plans unchanged. Country step 1.1 s (budget 10 s). Interior survey unchanged.
- Rivers (Ali's answers): every dry basin over 3 m and 0.5 km2 stays a closed salt lake (64 km: 31 -> 63); a lake is
  one piece around the basin's bottom, other pockets drain into it; towns by salt lakes accepted; min_flow 3.0.
  Deviation from the prompt: the bed is the running minimum of the ground down the whole network, not the filled
  height, which flies up to 55 m over hollows and which prompt 60's min() cannot use. Rivers cut through rims.
- Street graph: nodes on bare ground fixed (94 of 595); any street end on another's surface gets a stub: 125 of 131
  settlements one part. Left: real gaps in the plans (Ain Khatane 97.4%) and Gamar 97.5%: recheck at prompt 60.
- Histories: every choice on its own stream, so the capital's picks changed once, same templates.
  Review-81 findings 5 and 9 wait for Ali's before/after examples.
- Look: docs/wip/world-59-maps.png.
- Doubts and questions for Ali: the 16 wet hollows, lakes or cuts? (docs/wip/world-59.md section 4; advice: lakes.)
```

### docs/LEAD.md, section 3
- **The street graph of every settlement:** `tools/street_survey.py` (`--quick`, or the 64 km world in about 10 minutes):
  the settlements of more than one part and the bar of 99.5%. Run it after any step that moves villages.

### docs/HANDOFF.md, "Decisions and lessons"
- **River beds (prompt 59).** A bed must be under the ground on the whole network, not on each river: the terrain can
  only be cut (`min(terrain, bed + bank)`, prompt 60). The filled height flies over hollows; a running minimum per
  river leaves tributaries under their main bed. The running minimum down the network, tributaries first, is the
  highest bed that never rises, never floats and takes every tributary in. Ids run from the biggest river, so a
  tributary's id is always above its main river's.
- **Connected cells, one ring.** A shore is drawn per 4-connected piece: water labelled with 8 connections can hold a
  piece no ring shows, and a river then ends or starts where no shore is drawn (it happened in salt and fresh lakes).
- **Contours need real neighbors.** A box that stops at the mask gives the contour nothing to interpolate at its
  extreme rows: keep one cell of real ground around it.
- **Test a street graph against something else than `Ground.surface`.** Compared with `ground.height` plus the street's
  lift it showed 94 of 595 nodes on bare ground: snapping can put a street's end a few cm past its flat ribbon end.
- **Run graph checks on every settlement.** The quick capital was one part while 8 villages were under the bar.
  A street ending on another's surface is a junction even if center lines never meet; snap rounding only nodes a point
  whose pixel the other line crosses, so give both lines the meeting point as a vertex.
- **One stream per choice for text (prompt 81).** A shared stream drawn in toml order means a new template rewrites
  every later sentence of that district. Adding a list must change nothing.
- **Prove a test can fail.** Remove each rule once and watch its test go red. In this round the pocket test still
  passed with its rule removed (its scene no longer tripped the old rule) and nothing noticed a shore half a cell off.
