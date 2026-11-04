# world-59 (4 November): the first step of the "world first" order

Branch `wip/world-59` on main (fc93425). Merges prompts 70, 81 and 59, fixes what their reviews left, applies Ali's four
answers on rivers and the lead's review of 77cfe16. Worktree `/tmp/claude-501/world-59`. No tile changed, so no Blender.

## 1. What was merged, and the conflicts

| Commit | What | Conflict |
|---|---|---|
| 45e5508 | merge `wip/fix-70` | `tests/test_citygen.py`: both sides appended tests at the end; both kept |
| f5cedcd | merge `wip/fix-81b` | none |
| eb664ca | fixes of 70 and 81 | |
| 8c9e2be | merge `wip/fix-59` | `docs/SPEC.md`: section 5 (both new paragraphs kept), section 6 table (the rows of both sides) |
| 4ec2642 | Ali's answers, the reviews of 59, the street-end rule | |
| 24d60da, 77cfe16 | `tools/street_survey.py`, tidying, first notes | |
| 4edc903, ad22101 | the lead's review: every wet basin is a lake (ad22101 fixes a test bound; 4edc903 went out with it failing, my slip) | |
| 5c8a0b9 | the lead's review: pockets over the thresholds are basins of their own | |
| last commit | these notes, the pictures | |

## 2. The water: what to read first

1. **Every wet basin over the two thresholds is a lake up to its spill. Decided by the lead** (Ali: "you are the boss").
   The prompt says a filled basin over them IS a lake, and water cannot drain out of a hollow. Before, river 21 reached
   lake 38 with its bed 15.3 m under the level, 1.5 km of trench below the lake. Fresh lakes 10 -> 26 on that step.
2. **A pocket of a closed basin over the two thresholds is a basin of its own** (the lead's review, which narrows Ali's
   (b)). With the first change on, all 20 stretches over 10 m had their low point inside a salt basin: basin 39 (140
   km2, 171 m deep) sent nine rivers up to 51 m under the ground, and rivers 3 and 17 ran 2.6 and 2.4 km with beds 11.8 and
   14.5 m under the level of their lake, with the ground above it. Water cannot climb an inner rim of 47 m. `_routing` now
   finds lakes in rounds, each on the flow and heights the last one left, until a round adds no lake. The biome at a
   pocket's own bottom decides salt or fresh; a fresh one fills to its spill and runs on into the lake below. (b)'s aim
   stands: a pocket under the thresholds still drains in, and no river ends where no shore is drawn. Lakes per round: seed 42
   89, 25, 1; seed 7 80, 39, 4, 3; seed 3 87, 15, 5, 2 (and a last round that adds none). `flat` still falls along every `recv`.
3. **The bed is not the prompt's "filled height". A deviation, on purpose.** Filled heights fly over every hollow a river
   crosses (55 m at worst), and prompt 60's `min(terrain, bed + bank)` can cut the ground, never lift it. The bed is the
   running minimum of the ground under the drawn line. Per river that left 21 of 63 tributaries up to 37 m under their
   main bed, so it runs down the network, tributaries first (`hydro._beds`): the only bed that never rises, never floats
   and takes every tributary in. With 1 and 2 only small pits are left to cut through, so the price almost vanished:
   35.6 km of river over 10 m under the ground -> 0.0 km, worst 58.6 m -> 10.3 m (seed 42).
4. **Lakes grow from their basin's bottom** (`hydro._water`), one 4-connected piece: read literally, (b) leaves 8 of 73
   salt lakes under `lake_min_area` (down to 17 cells; 23 is the minimum). Rare leftover: a basin of 23 or more whose cells
   are joined only at a corner gives a lake of 18-22 cells (on 3 of 5 other seeds, measured before the rounds).
5. **Shores** follow the true contour with one cell of margin: on a test bowl the ring's worst error against the ground
   went 6.6 m -> 1.9 m (salt: 0.2 m). Prompt 60's flat water needs that edge on the ground.

**Left as it is, on purpose (your question): a first lake's `wet` counts its whole basin's inflow, although pockets found
later keep theirs.** So 23 salt lakes of seed 42 are over 20% bigger than what really reaches them says; lake 3 holds 452
cells where its true inflow gives 58. Correcting it is not simple: a loop that shrinks lakes, re-floods their basins and
looks for new pockets (a prototype took about 25 lines, 0 order faults). And it looks worse: the great chotts by Sota and
Bebgia go, every salt lake becomes a small patch of about the same size, salt area 88 -> 49 km2, 92 salt lakes. Picture:
`docs/wip/world-59-inflow.png`. I read a big lake as the floor of its whole basin, and kept it. Say if you want it anyway:
the prototype is the scratchpad's `w59_patch_shrink.py`.

**The dry country was speckled, and the lead fixed that last (his own commit on this branch):** the pockets took the salt lakes
from 63 to 87, and 49 of the 87 had no river ending in them, 40 of those at the smallest size. A salt flat needs water to come to
it, so `hydro._drawn` keeps every fresh lake and only the salt lakes a river ends in; the other hollows stay closed, on bare
ground. Salt lakes 87 -> 38 (seed 7: 93 -> 35; seed 3: 81 -> 33), towns touching a lake 14 -> 10, roads crossing one 19 -> 13.
It narrows Ali's (a) ("every dry basin ... stays a closed salt lake"): every such basin stays closed, as he chose, but only
the fed ones show salt. No river changed: none ends in those hollows. The picture shows the result.

## 3. Every finding, fixed or why not

**review-59:** 1 (dry basins): fixed, Ali's (a). 2 (bed against ground): fixed, section 2. 3 (`_snap`): fixed for real, see
rev-fix59 1. 4 (pockets): fixed, Ali's (b) as narrowed. 5 (drainage order): `test_every_cell_drains_to_a_lower_one` on both
worlds; 0 faults in 24 worlds with the rounds (12 seeds x 2 sizes), so no Kahn sort is needed. 6 (a test that could not
fail): replaced. 7 (only the quick world): every structural test runs on quick and 64 km; synthetic hollows added. 8
(numbers in code): `[rivers] basin_depth`, `map_line`. "Time the country step": section 4.
**rev-fix59:** 1 (`_snap` docstring): the rule became simple, so the docstring is true: a tributary ends on the main bed,
always (gap 0.0). 2 (xfail test): a normal test, on a scene the old rule fails, that asserts its own starting conditions
(one salt lake, two pockets under the level, the second under the threshold). 3: covered by the bed test.
**review-70:** Low 3 (z against itself): an independent check, which FOUND A BUG, below. Low 4: fine as is, the review says
so. Low 5: union length. Low 6: fixed, with a case that really fails without it. Low 7, 8, 9: SPEC wording. Info 10: left,
it matches `mesh/tile.py`. Info 11, 12: section 4.
**rev-fix70:** 1 stderr shown; 2 renamed `[street_graph] grid`; 3 accepted (the comment says what the grid does); 4, 5
accepted, as the review says; 6 blank line.
**review-81:** 12 (SPEC) done; 10 (keying): noted in SPEC, for prompt 84. **5 and 9 NOT done, as briefed.**
**rev-fix81:** 1 (the medium): every choice has its own stream (`origin`, `facts`, `today`, `fact.<key>`). 2: the `"{name}."`
fallback is gone, ` and ` moved to `and_word`. 3: `era_in_default` / `era_since_default`, no English left in the code. 4:
test that every era has its words; the era check uses the whole phrase. 5: exact polygon first; 0 of 37 landmarks and 0 of
44 souks change district on six settlements, so no overlap with review-81's 5. 6: plural table by ending.

**Found on the way, fixed:**
- One fresh lake (id 38, before the rounds) was 40 + 10 cells joined at a corner: its outlet started 505 m from any shore.
- `streets.json` z: 94 of 595 nodes of the quick capital sat on bare ground, 18-30 cm under the drawn street top (snapping
  leaves a street's end a few cm past its flat ribbon end). `node_tops` fixes it; now 577 of 595 are within 1.5 cm of the
  ribbon height, the worst 4 cm low, the rest on a curb or a higher ribbon.
- Street graph on all 131 settlements: 8 villages under the 99.5% bar. Six were graph faults, a street ending on another's
  surface short of its center line: every street end now gets the stub impasse mouths had. One part: 115 -> 125 of 131.
- `origin.park` lacked a comma. A typo-level fix, not review-81's wording work.

**Left, on purpose:**
- Street islands where ribbons really do not touch: Ain Khatane (97.4%, village), Sota, Ksar el Djabrar (two), Zouchir,
  Bazar el Djedid (all over 99.8%): 0.3 to 13 m between ribbons, all checked. A gap in the planner; fixing it moves plans.
  Gamar (97.5%): two alleys overlapping side by side. All villages move at prompt 60: recheck with `tools/street_survey.py`.
- Tests pinned to a number: none went stale, no plan moved. Four will at the names step: `tests/test_citygen.py` lines 2246,
  2703, 5353 (`world.settlements[3]`, `[5]`) and 5356 (`plan.buildings[369]`).
- Prompt 60 will move more towns: see "towns touching a lake" below.

**What Ali should look at:** `docs/wip/world-59-maps.png`, before and now. The histories changed their picks once (same
sentences to choose from), so his before/after examples of review-81's 5 and 9 should be made from this branch.

## 4. Results

**Water, 64 km world, seed 42, step by step** (measured the way `lead_water.py` does):

| | fix-59 | Ali's answers (77cfe16) | wet lakes (ad22101) | pockets too (7af6644) | now, fed salt lakes only |
|---|---|---|---|---|---|
| Lakes, fresh + salt | 10 + 31 | 10 + 63 | 26 + 63 | 28 + 87 | 28 + 38 |
| Rivers, km of river | 157, 525 | 150, 526 | 154, 495 | 148, 424 | 148, 424 |
| Over 10 m under the ground, km | | 35.6 | 24.0 | 0.0 | 0.0 |
| Over 20 m, km | | 20.2 | 14.7 | 0.0 | 0.0 |
| Worst cut, m | | 58.6 | 50.9 | 10.3 | 10.3 |
| Bed under its lake's level, ground above, worst m | | 15.3 | 14.5 | 3.1 | 3.1 |
| Towns touching a lake | 9 | 9 | 12 | 14 | 10 |
| Roads crossing a lake | 12 | 13 | 18 | 19 | 13 |

The filled bed of fix-59 flew up to 55 m over the ground; now it lies at most 0.01 m over it, off lakes.

**Now, by seed and size** (`output/checks/w59/audit.txt` here; script: the scratchpad's `w59_audit.py`):

| World | Rivers, km | Lakes, fresh + salt | Over 10 m, km | Over 20 m, km | Worst, m | Under lake level: km, worst m | Towns | Roads |
|---|---|---|---|---|---|---|---|---|
| 64 km, seed 42 | 424 | 28 + 38 | 0.0 | 0.0 | 10.3 | 2.8, 3.1 | 10 of 131 | 13 of 141 |
| 64 km, seed 7 | 419 | 33 + 35 | 0.7 | 0.0 | 18.4 | 1.5, 3.3 | 5 of 131 | 11 of 143 |
| 64 km, seed 3 | 425 | 28 + 33 | 1.5 | 0.3 | 33.4 | 2.7, 4.5 | 14 of 131 | 18 of 144 |
| Quick, seed 42 | 34 | 0 + 2 | 0.1 | 0.0 | 10.4 | 0.0, 2.6 | 0 of 14 | 0 of 14 |
| Quick, seed 7 | 26 | 0 + 4 | 0.0 | 0.0 | 4.0 | 0.5, 0.5 | 0 of 14 | 0 of 14 |
| Quick, seed 3 | 37 | 0 + 1 | 0.1 | 0.0 | 11.8 | 0.0, 0.0 | 0 of 14 | 0 of 14 |

**Every stretch over 10 m, by cause** (what lies at the low point upstream of it; 64 km unless said):
- Seed 42: none. Its worst cut, 10.3 m, is one point; no stretch averages over 10 m.
- Seed 7: 4 stretches, 0.71 km: 3 from pits in the open under the thresholds (2-21 cells, 3-18 m deep), 1 from a tributary's
  bed (0.17 km, 16.6 m).
- Seed 3: 10 stretches, 1.49 km: 7 from pits in the open, 2 from pockets of closed basins under the thresholds (7 and 9
  cells, 8 m deep), 1 from a tributary's bed.
- Quick: seed 42 one (0.05 km, a pit of 14 cells), seed 3 one (0.09 km, a pit of 12 cells), seed 7 none.
- **The only stretch over 20 m in all six worlds:** seed 3, river 60, 0.41 km up to 32.8 m. Its low point is a pit in the open
  of 21 cells, 37.8 m deep: 2 cells under `lake_min_area` (23), so it is no lake and the river cuts through its rim. The
  thresholds are the prompt's; I left them. Tell me if you want a deep small pit to count.
- What stays under lake levels: pits under the thresholds on the way to the lake, 4.5 m at worst. `lead_water.py` also shows
  a "gap" of 10.3 m at a salt lake's mouth (river 111), with 0.0 km of trench: a salt river ends on the lake's floor, under
  the water, so that gap is depth of water and no fault. Your scripts agree with every number above (`lead_water2.py`: no
  stretch over 10 m on seed 42).

**River network, seed 42:** 148 rivers: 54 end in a salt lake, 42 join a river, 31 end in a fresh lake, 18 at the sea, 3 at the
border; 13 are oueds. Sources: median 301 m (10% 71 m, 90% 545 m). Rivers reach 11.8 m wide, oueds 1.8 m.
Over 12 seeds at both sizes (24 worlds): 0 drainage-order faults, 0 rising beds, 0 mouths off a shore, every lake cell inside
its ring, junction gap 0, bed over the ground 0.055 m at worst, off lakes.

**Tests:** merge of 70 + 81: 178 passed. After their fixes: 182. At 7af6644: 206 passed. Now, with the fed-lake rule: 209 passed (run by the lead; its three new tests fail without the rule). The helper's run at 7af6644: 16 slow deselected, 62 s. `-m slow`: 15 passed, 1 xfailed,
182 s (the xfail is the old colonial one of prompt 47, `tests/test_citygen.py:4228`).
All of `tests/test_hydro.py` takes about 3 s. Each rule of 59 was removed once to see a test fail: 11 of 11 caught. The tests
you asked for each fail without their rule: two pockets (rounds off), small pocket (rule b off), wet hollow (old rule), the
bound under lake levels (rounds off). Three rules of 70 and 81 likewise on the old code.

**Two-process tests,** all in `-m slow`: `test_interior_two_processes`, `test_home_kit_deterministic`,
`test_streets_json_two_processes`, `test_world_json_two_processes`. Stronger, by hand: whole quick builds under
PYTHONHASHSEED 1 and 2: 0 of 283 parts differ.

**Builds:** `build --quick` 7.1 s (7.0 s at the baseline). `--force`: 0 of 283 parts change. `build --out output/full` on the final code: 89 s, with
the survey running beside it. Info 11: the 64 km capital plans in 64 s; its `streets_json` takes 4.4 s while the workers run
(16,156 nodes, 18,472 edges, 4.8 MB). Over all 131 settlements that would be about 40 s beside 615 s of planning. Other
worlds also build on the final code: `--seed 7`, `--seed 3`, `worlds/example.toml`.

**Fingerprint `compare w59`:** 283 parts, 5 changed, each by its cause:
- `files/cities/goumosbane/streets.json`: added (70).
- `gazetteer` 3532 -> 5994 bytes: the histories block only: with it removed the digest is the baseline's (fd98b3f8...).
- `plan/goumosbane/districts`: `history` only: without that key the digest is the baseline's (cde6faec...).
- `world` 9613 -> 33239 bytes: `rivers` and `lakes` only: without them the digest is the baseline's (a006bcb7...).
- `maps/country.png`: the water.
No tile, no other plan part, no city map changed. The quick world has no pocket over the thresholds and no wet basin, so
your two changes leave all 283 parts byte-identical to 77cfe16 (`compare w59_a`: 0 changed); they show on the 64 km world.

**Country step (64 km world, quiet machine, 5 runs):** `generate_world` 1.26-1.41 s, of which drainage 0.71 s (0.51 s before
the rounds). Budget 10 s.

**Maps, looked at myself:** rivers rise in the hills, join, run through chains of lakes to the sea; oueds end in salt lakes on
drawn shores. Fresh lakes now sit in the forest hollows. A village dot still stands inside the big lake west of Sota, and Sota
itself now touches a salt pocket to its north (1.4 km2): the overlap Ali accepted, for prompt 60. Prompt 59's "Done when" is met.

**Towns touching a lake (seed 42):** cities Chilel (salt), Sota (salt), Takiret (fresh); towns Betane el Kebir (fresh), Ras
Kabine (salt); 9 villages. The older notes name Sota as touching before the pockets: it did not, it was 1.0 km clear.

**Interior survey:** the settlements are called today Goumosbane (capital, quick world id 0) and Ain Chilel (town, id 3);
names and places change in a later step.

| Goumosbane | before | after | | Ain Chilel | before | after |
|---|---|---|---|---|---|---|
| dar | 155/159 | 155/159 | | villa | 168/178 | 168/178 |
| compact | 266/277 | 266/277 | | maison | 499/616 | 499/616 |
| small | 81/83 | 81/83 | | | | |
| koubba | 21/22 | 21/22 | | | | |
| colonial | 5/270 | 5/270 | | | | |
| slab | 253/353 | 253/353 | | | | |
| shop | 130/136 | 130/136 | | | | |

No change to explain: with the clock readings ("slowest ... s") taken out, both reports are byte-identical, ladder
warnings, failure kinds and failing buildings included (45 and 35 lines). Expected: no plan moved.

**Street survey:** quick world 12 of 12 in one part. 64 km world: 125 of 131 in one part, `street_graph` costs 10 s in all, 1.2 s at worst.

## 5. Text to paste

### docs/ROADMAP.md
- [x] 59 B1a Rivers (citygen/hydro.py; World.rivers, World.lakes; country map)
- [x] 70 C4a Street graph for games (cities/<name>/streets.json; quick capital one connected part)
- [x] 81 D1a District histories

### docs/WORKLOG.md
```
## 2026-11-04 - Prompts 59, 70, 81 (world-59): rivers and lakes, street graph, district histories
- Commit: <merge>
- Changed: citygen/hydro.py, citygen/export/streets.py, citygen/city/history.py (new); citygen/world.py,
  build.py, export/maps.py, export/lore.py, city/__init__.py, city/model.py, defaults.toml; styles/maghreb.toml;
  tests/test_hydro.py (new), tests/test_citygen.py; tools/street_survey.py (new); docs/SPEC.md.
  Notes: docs/wip/world-59.md
- Checks: tests 209 passed, slow 15 passed + the old xfail; build --quick 7.1 s, --force identical; fingerprint 5 of 283 parts:
  streets.json added, gazetteer and districts (histories only), world (rivers and lakes only), country map. Tiles and
  plans unchanged. Country step 1.4 s (budget 10 s). Interior survey unchanged.
- Rivers (Ali's answers): every dry basin over 3 m and 0.5 km2 stays closed; towns by salt lakes accepted;
  min_flow 3.0. The lead's decisions (Ali: "you are the boss"): every wet basin over the two thresholds is a lake up to
  its spill (the prompt says such a basin IS a lake, and water cannot drain out of a hollow), and a pocket of a closed
  basin over them is a basin of its own (water cannot climb an inner rim; a smaller pocket still drains in, so no river
  ends where no shore is drawn); a salt lake needs a river that ends in it (49 of 87 had none and only speckled the dry
  country; those hollows stay closed, on bare ground). 64 km world: 28 fresh + 38 salt lakes, 148 rivers, 424 km.
  Deviation from the prompt: the bed is the running minimum of the ground down the whole network, not the filled
  height, which flies up to 55 m over hollows and which prompt 60's min() cannot use. Rivers cut through the rims of pits
  too small for a lake: 10.3 m at worst on seed 42, 33 m over 0.4 km on seed 3 (a 38 m deep pit, 2 cells under the area).
- Known: 23 salt lakes are over 20% bigger than their true inflow says: a first lake counts its whole basin's inflow
  (counting only what reaches it loses the great chotts, picture docs/wip/world-59-inflow.png). 10 towns touch a lake and
  13 roads cross one, for prompt 60 to move.
- Street graph: nodes on bare ground fixed (94 of 595); any street end on another's surface gets a stub: 125 of 131
  settlements one part. Left: real gaps in the plans (Ain Khatane 97.4%) and Gamar 97.5%: recheck at prompt 60 with
  tools/street_survey.py.
- Histories: every choice on its own stream, so the capital's picks changed once, same templates (8 of 9 districts).
  Review-81 findings 5 and 9 wait for Ali's before/after examples.
- Look: docs/wip/world-59-maps.png (before and now).
- Doubts and questions for Ali: none; the lead decided the wet hollows, the pockets and the fed salt lakes.
```

### docs/LEAD.md, section 3
- **Take a number down to its causes.** "36 km of river deep under the ground" was accepted as a price until a list of every
  stretch with what lay at its low point showed one cause, pockets of salt basins, and a two-line idea removed it all.
  Scripts for a world step: keep them in the scratchpad, `lead_water*.py`.
- **The street graph of every settlement:** `tools/street_survey.py` (`--quick`, or the 64 km world in about 10 minutes):
  the settlements of more than one part and the bar of 99.5%. Run it after any step that moves villages.

### docs/HANDOFF.md, "Decisions and lessons"
- **River beds and hollows (prompt 59).** The terrain can only be cut (`min(terrain, bed + bank)`, prompt 60), so a bed must
  stay under the ground on the whole network: the filled height flies over hollows, and a running minimum per river leaves
  tributaries under their main bed. The running minimum down the network, tributaries first, is the highest bed that never
  rises, never floats and takes every tributary in. But a bed cannot leave a big hollow without a deep trench, so that rule
  only works if every hollow over the two thresholds holds a lake: wet ones up to their spill, and each pocket of a closed
  basin as a basin of its own. Doing both took the worst cut from 59 m to 10 m and 36 km of deep river to none (seed 42).
- **Water does not climb.** Two rules that sounded fine broke this: "a hollow too big for its water drains" and "a pocket
  drains into the lake of its basin". Ask of each hollow where its water goes; a small pit is the only one that may just
  be crossed.
- **A lake needs water that reaches it.** 49 of 87 salt lakes had no river: a look fault (speckle) with a logic cause. Keep
  a dry hollow closed, but show salt only where a river ends. Removing them moves no river, and fewer towns have to move.
- **A lake's size is a look as much as a number.** Pockets keep most of a big basin's water, so a strict balance shrinks
  every chott to a small patch. The first lake keeps its whole basin's inflow on purpose: read it as the basin's floor.
- **Connected cells, one ring.** A shore is drawn per 4-connected piece: water labelled with 8 connections can hold a
  piece no ring shows, and a river then ends or starts where no shore is drawn.
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
- **Read the test result before you commit.** A chained command pushed a failing test here; check, then commit.
