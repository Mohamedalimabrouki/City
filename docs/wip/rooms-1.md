# Interiors on the final buildings, step 1: the room behind a balcony (helper's notes)

Brief: `docs/wip/rooms-brief.md`. Base commit c936562. Nothing committed: the lead reviews.

## What changed (working tree, nothing committed)
- `tools/balcony_survey.py --rooms [--every N] [--groups g,g] [--city villas]`: the room behind every balcony door, by group and kind of door.
- `spine.doors_out`, `spine.dry`: a cell with a balcony door on any floor is closed to a bath on all floors. Read by `candidates`, `slide_wet`, `hall_corner`, `leftovers`, `give`, `bayplan.types`, `wet_end`, `carve`.
- `plancheck.balcony_baths` in `rooms.check`: a bath or wc behind a balcony door is now a plan fault.
- `[interiors.flats] bay_plan.bath`: `bayplan.carve`'s sizes from the style, wc 1.1 x 1.6 m (the code's default was 1.0 x 1.3 m).
- `rooms._connect`: a bath room is the last neighbour tried as a way in.
- `furnish`: the wet-room exception is gone; `Furnisher.curtains`, `curtain_over`; `home/curtain` (`kit_new`, its own stream), `voile` in `[interiors.palette]`. Curtains from `lived-in` up, modern homes, balcony doors only: windows wait for prompt 55.
- Tests: `test_balcony_baths_rule` (fast), `test_balcony_doors_lead_to_rooms` (slow). The xfail stays, with a new reason.
- Pictures, looked at: `docs/wip/rooms-1-colonial-chambre.jpg`, `docs/wip/rooms-1-slab-salon.jpg`.

## State (oldest first)
- Item 1 done: `tools/balcony_survey.py --rooms [--every N] [--groups g,g]`. Baseline running on a frozen copy of c936562.
- Baseline of whole plans at c936562 (frozen copy, per-building dumps in the scratchpad): capital and villa town match the lead's table. Capital: colonial 3,519 door-windows (chambre 1,278, salon 1,122, hall 341, cuisine 311, salle a manger 139, couloir 138, sdb 108, wc 56, droj 14, palier 12); slab 9,863 doors (chambre 4,965, salon 2,054, cuisine 1,457, salle a manger 1,042, sdb 152, hall 144, couloir 39, droj 10).
- Item 2 in progress: `spine.doors_out`, `dry`, `door_ways`, `[interiors.flats] door_way`, `plancheck.balcony_baths`. Item 4 and the curtain (item 5) are coded, not yet judged. A bath got a door by a third way: `spine.give` (window bays).
- Item 3 checkpoint. The brief's "49 of 2,142" is stale: at c936562 the test itself reads **69 of 1,952, 3.53%** (`pytest --runxfail` on a frozen copy; plans moved with valleys and bridges). By group: colonial 42, slab 15, small 6, compact 2, dar 2, koubba 2. The slab cause is proved by taking one thing out: `bayplan.carve`'s code default wc 1.0 x 1.3 m (free floor 0.83 x 1.13 m: seat 0.7 + door keep 0.6 = 1.3 m do not fit). `bath.wc = [1.1, 1.6]` alone: slab wcs warned 22 -> 5. What did not help, each tried on its own: `wc_keep` 0.45 (no change), wc doors swinging out (15 -> 14), both with a narrower path (51 -> 49, slabs up): dropped. `rooms.connect` no longer gives a room its door through a bath where another reached neighbour exists: 56 -> 51.
- First whole capital after item 2 (`a1`): baths behind balcony doors 0 of 13,382 (316 before); slab fell 263 -> 254. Read: the stack's doors used for the salon and cuisine choice (kitchens behind slab doors 1,457 -> 87, salons 2,054 -> 3,284) took windows from chambres (18 new "has no window"): a kitchen behind a balcony is allowed, so that part is taken out again. `door_way` moved nothing (colonial halls 341 -> 345).
- Item 6, 1 plan in 4 of the capital on `a1`: colonial 219 dark of 2,327 rooms: 145 touch only a party wall, 31 no outside wall, 27 a court, 8 an open long wall, 5 a closed wall under 1.5 m, 3 a street wall. Slab 55 of 6,992: 38 no outside wall, 16 open long wall, 1 gable. Baseline crash, not ours: seed 7 colonial No. 3790 (GEOS topology error) at c936562.
- Halls and couloirs in colonial blocks: two attempts, both taken out, neither moved the rate. (1) A fraction of a fault per hall or couloir behind a door in the search: halls 341 -> 345. (2) Giving the door's window bay to a room beside the way (`spine.give`): hall 17 of 210 in a sample against 15. Why: of 7 blocks read, the halls behind a door are 10-15 m2, wider than the bay, so the piece does not touch a room beside them (133 of 183 tries), or no room stands beside them (39). What would do it: cut a big hall across, its front a room. That is a planner change, not this step's. The droj stands under the roof's stair room and the palier in the stair core, both given by the building.
- Item 4: 1 block in 6 of the capital at full density: 2,218 balcony doors, 2,218 curtains, 0 pieces in a door, 0 faults. A curtain counted as an obstacle in `reaches` broke `test_furnish_no_overlap_every_layout` (No. 847): one walks through a curtain, now excluded.
- Seed 7 found a fourth way a bath gets a door: `spine.unwrap` hands the host's hair-thin arms to the carved bath (6 sdbs on 4 blocks). `carve_wet` now refuses such a place. Final dumps of all five plans running.
- Item 6, final plans, 1 plan in 4 of the capital: colonial 206 dark of 2,317 rooms: **140 touch only a party wall**, 27 no outside wall, 25 a court, 7 an open long wall, 5 a closed wall under 1.5 m, 2 a street wall. Slab 40 of 7,052: 20 open long wall, 19 no outside wall, 1 gable. The party-wall rooms stand in flats deep between two neighbours: the lit frontage is too short for the rooms the area asks. The planner cannot light them: **they need courts or light wells.** Stopped there, as the brief says. (`facades.md`'s 88 was another capital.)
- Final dumps of the five plans done (below). Checks on the final code: `pytest -q` 309 passed; the brief's slow set 7 passed, 1 xfailed; `build --quick` fine; fingerprint 302 parts, 0 changed (`--allow ""`: the home kit is not in a build). Baths behind balcony doors 0 on all five plans. Seeds 5 and 7 are built in `output/rooms-seeds/`.

## Numbers before and after (whole plans; pass counts of `rooms.check`)
| plan | dar | compact | small | koubba | colonial | slab | villa | maison | shop |
|---|---|---|---|---|---|---|---|---|---|
| capital before | 149/159 | 263/268 | 86/88 | 25/26 | 9/278 | 263/347 | | | 122/137 |
| capital after | 149/159 | 263/268 | 86/88 | 25/26 | 8/278 | 259/347 | | | 122/137 |
| villa town before and after | 35/37 | 82/82 | 20/22 | 1/2 | | | 123/146 | 383/500 | 41/46 |
| seed 5 before | 167/172 | 315/319 | 103/110 | 25/26 | 5/272 | | 375/407 | 3,529/4,422 | 134/151 |
| seed 5 after | 167/172 | 315/319 | 103/110 | 25/26 | 5/272 | | 375/407 | 3,528/4,422 | 134/151 |
| seed 7 before | 232/241 | 396/402 | 122/127 | 39/40 | 33/1,555 | 166/300 | 985/1,066 | | 154/175 |
| seed 7 after | 232/241 | 396/402 | 122/127 | 39/40 | 32/1,555 | 170/300 | 985/1,066 | | 154/175 |
| seed 5 villa town, before and after | 21/22 | 12/14 | 2/2 | | | | 165/176 | | |

Seed 7's one crash (colonial No. 3790, a GEOS topology error) is in the baseline too.

| behind a balcony door | capital before | after | seed 5 before | after | seed 7 before | after |
|---|---|---|---|---|---|---|
| colonial doors | 3,519 | same | 2,788 | same | 17,206 | same |
| colonial bath or wc | 164 | **0** | 115 | **0** | 612 | **0** |
| colonial hall, couloir, droj | 493 (14.0%) | 548 (15.6%) | 488 (17.5%) | 536 (19.2%) | 3,158 (18.4%) | 3,328 (19.3%) |
| colonial palier | 12 | 12 | 12 | 12 | 129 | 129 |
| slab doors | 9,863 | same | | | 7,831 | same |
| slab bath or wc | 152 | **0** | | | 116 | **0** |
| slab hall, couloir, droj | 193 | 206 | | | 581 | 572 |

The colonial ways rose: a bath that leaves a door's cell often leaves that cell to the hall or couloir. Plans moved: capital 291 of 1,303, villa town 4 of 835, seed 5 170 of 5,879, seed 7 864 of 3,907.

The capital's slab fall (263 -> 259), read case by case by taking one thing out: Nos. 1141 and 1142 passed only with a bath behind a balcony door, which is now a fault; Nos. 1104 and 750 (colonial) pass only with the bath where the door is; No. 1351 by the larger carved wc. Price of the rule: capital colonial flats with no sdb 18 -> 30, no wc 15 -> 20; seed 5 21 -> 24 and 23 -> 25; seed 7 146 -> 158 and 121 -> 125.

## Required furniture (`test_furnish_required_share`, quick capital, at sparse)
Before 69 of 1,952, 3.53% (colonial 42, slab 15, small 6, compact 2, dar 2, koubba 2). After 49 of 1,971, 2.49% (colonial 35, small 6, compact 2, dar 2, koubba 2, slab 2). Slab wcs warned 14 -> 0. The bar needs 39: **not reached, the xfail stays with a new reason.** Left in colonial blocks: wc 13, kitchen fridge 8, sdb wash 8, wc in a sdb 5, basin 1. Tried beyond that, no real gain: wc minimum 1.5 m2 x 0.95 m (49 -> 47).

## Left for the lead
- Item 3's bar: colonial rooms, not slabs. Many of those wcs are 1.2-1.4 m squares whose door takes the depth a seat needs.
- Colonial halls of 10-15 m2 behind a door: a planner change (cut the hall across, its front a room).
- Dark rooms on party walls: courts or light wells.
- The curtain's height is fixed at 2.30 m: head + 0.15 for a slab door (2.15 m), head + 0.25 for a colonial door-window (2.05 m). `stretch` works along the wall only.

## Text for the docs
- WORKLOG: Interiors step 1, the room behind a balcony. No bath or wc behind a balcony door on any plan (capital 316, seed 5 115, seed 7 728 before); `rooms.check` now faults it. Curtains on balcony doors from lived-in up, nothing stands in a door (2,218 doors probed at full). Carved wc 1.1 x 1.6 m: slab wcs warned 14 -> 0. Not reached: the 2% furniture bar (2.49%, colonial), colonial halls behind doors (15.6%), party-wall dark rooms (need courts). Capital slab 263 -> 259, colonial 9 -> 8.
- HANDOFF: A cell with a balcony door on any floor is closed to baths on all floors (`spine.dry`). A bath got a door by four ways: the choice of cell, `leftovers`, `give` and `unwrap`: any new code that grows a wet room asks `dry`. The stack's doors must not steer the salon or kitchen: it took windows from chambres. A brief's number can be stale: `pytest --runxfail` read 69 of 1,952, not 49 of 2,142.
- LEAD: Dump one JSON record per building, in 7 shards from a frozen copy: every later question (who moved, what fell, rates by plan) is then a 20-line script with no new planning. A rule proved on three plans held only on the fourth: seed 7 found `unwrap`.
- SPEC 6c: flats and modern homes: no bath or wc behind a balcony door, on any floor of the stack; a bath is the last neighbour `rooms.connect` tries; `bay_plan.bath`. SPEC 6d: `curtain` built for balcony doors only (`Furnisher.curtains`, `curtain_over`, level lived-in, 2.30 m high, `voile`); windows wait for prompt 55; `reaches` does not count a curtain. `DOORS` holds `balcony` with no wet exception. Tools: `balcony_survey.py --rooms`.
