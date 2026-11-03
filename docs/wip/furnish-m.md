# Furnishing round 3 (prompt 54, helper; worktree /tmp/claude-501/furnish-m, branch wip/furnish-m at c48fb1e; NOT committed)
## Task
(1) colonial bath no basin (47) + colonial wet warnings; (2) small homes 12.5%; (3) dar maqsura < 4.5 m2 no bed;
(4) full capital 30-house survey. Target 2% warned (quick capital); write the 2% test if met. Only furnish.py,
household.py, home kit, [interiors.furnish]. No rooms.json change. Stop by 20:50 UTC.
## Steps
- 19:10 started quick build + fingerprint save before; full capital build (output/full) in background.
- Survey script: scratchpad hu_survey.py (copy of hq_survey.py, tree = furnish-m). Run:
  `<py> hu_survey.py --dens lived-in` (HN_TREE default furnish-m).
- 19:23 machine load ~180: baseline survey slow (planning 150 interiors). hu_survey.py now caches the planned
  interiors in scratchpad hu_cache*.pkl (planners untouched, so the cache stays valid); baseline in hu_base.txt /
  hu_base_b.txt. hu_why.py k:rid,... prints one room's runs, placed pieces, fail reasons (FU.DEBUG).
- Ideas: basin -> a small wall-hung hand basin (new home kit piece `hand_basin`) as `smaller`; trad kitchen water:
  sink_stone -> qolla smaller / ends; shop counter shopfront offsets closer; maqsura: check sleep_couple chain.
- 19:40 BASELINE quick (hu_base.txt, lived-in, 25/layout): 257/6163 = 4.2%: colonial 7.7, compact 3.1, dar 3.4,
  koubba 2.7, slab 2.2, small 12.5. FULL capital baseline (hu_full_base.txt, 4 per layout = 32 houses, 1058 rooms;
  NB the hand_basin edit may already have been loaded): 5.5%: colonial 9.6, compact 6.5, dar 5.4, koubba 16.0 (4 of
  25), maison 2.7, slab 2.8, small 10.5, villa 3.7; 0 faults.
- Changes so far (uncommitted): kit_new.py new pieces hand_basin (wall-hung lave-mains, z0 0.42) and shower_small
  (70 cm tray, the shower maker); furnish.py place mode "side" (a piece lengthwise along a wall, rotated 90 deg) and
  `wc_rooms`/`wc_keep` (a wc's door keeps 0.6 m, not 0.8); toml: smaller basin->hand_basin, shower->shower_small,
  wc_seat->wc_turkish, sink_stone->qolla; beds else ["wall","side"]; wc slot else ["wall","side"]; shop counter
  else ["wall"]; bath wash/basin/wc slots cross = true (two-door sdbs: walk strips).
- Not fixable here: dar maqsuras 2.3-2.7 m square with two doors in the middle of adjacent walls (No. 195, 211, 220,
  416): no bed clears both door boxes (a planner matter); 1.0 x 1.05 m wcs (No. 23246, 38380, 16345 wc 4).
- 19:45 more: `else` entries may be tables overriding slot keys (furnish.place); shop counter else
  [{ place = "wall", most = 1.4, ends = true }]. Trad sample (dar, small, compact, koubba; hu_trad1.txt, before the
  shop table): small 12.5 -> 8.6, dar 3.4 -> 1.5, compact 3.1 -> 1.8, koubba 2.7 -> 0.7; 0 faults.
- 19:46 running: after-surveys hu_after.txt (quick, cached plans) and hu_full_after.txt (full capital); pytest -q
  (task bl2b6vwiu) started 19:41 before the shop/else-table edits: rerun after.
- Next: read both surveys; SPEC 6d built note; pytest -q; pytest -q -m slow -k furnish; build --quick;
  fingerprint compare before --allow "". 2% test only if quick < 2%.
- 19:50 household.functions(..., least=4.5): trad couple -> largest one-door maqsura >= `couple_maqsura` 4.5 m2,
  else ghorfa, else maqsura, else bit (dar No. 195, 211, 416 now have their bed; 220 still not: its only maqsura).
  Full capital after (before this household change; hu_full_after1.txt): 5.5% -> 2.2% (colonial 9.6 -> 4.4, slab
  2.8 -> 0.6, small 10.5 -> 0, dar 5.4 -> 1.8, koubba 16 -> 8, compact 6.5 -> 4.3, maison 2.7 -> 1.4, villa 3.7 ->
  1.9); 0 faults. SPEC 6d built note "Round 3" written.
- 19:50 running: hu_after.txt (quick), hu_full_after.txt (full, final code), pytest -q (task baij30n22).
- 19:50 build --quick 14.5 s; fingerprint compare before --allow '': 282 parts, 0 changed. Long lines reformatted (no behaviour change).

## WORKLOG draft (lead writes it; numbers to fill from hu_after.txt / hu_full_after.txt)
## 2026-11-03 - Prompt 54 H2c Furnishing, round 3 (small pieces, a bed along the wall, the couple's room)
- Changed: citygen/interior/kit_new.py (home/hand_basin: a wall-hung lave-mains 0.40 x 0.30 m from 0.42 m up;
  home/shower_small: a 70 cm tray), citygen/interior/furnish.py (place mode `side`: a piece lengthwise along a
  wall; `else` entries may be tables overriding slot keys; `wc_rooms`/`wc_keep`: a wc's door keeps 0.6 m),
  citygen/interior/household.py (`functions(..., least)`: a traditional couple takes a one-door maqsura of 4.5 m2
  or more, else a ghorfa, else a maqsura, else a bit), styles/maghreb.toml ([interiors.furnish] wc_rooms, wc_keep,
  couple_maqsura; smaller basin -> hand_basin, shower -> shower_small, wc_seat -> wc_turkish, sink_stone -> qolla;
  beds and the wc: else "side"; the hanout counter: else a 1.4 m counter by a corner; the bath's tray, basin and wc
  `cross`), SPEC 6d built note.
- Measured, not fixed (planners): 1.0 x 1.05 m wcs with a 0.7 m door; maqsuras 2.3-2.7 m square with doors in the
  middle of two walls and no other room for the couple (dar No. 220).
- 19:51 FULL capital after (final code, hu_full_after.txt): 58/1058 5.5% -> 23/1058 2.2% (colonial 9.6->4.4, compact 6.5->4.3, dar 5.4->1.8, koubba 16->8, maison 2.7->1.4, slab 2.8->0.6, small 10.5->0, villa 3.7->1.9); 0 faults; left mostly colonial 1 m wcs (8) and kitchens. Draft slow 2% test in hu_test2.py (8 per layout, sparse).
- 19:58 QUICK after (hu_after.txt): 257/6163 4.2% -> 114/6163 1.8% (colonial 7.7->3.4, compact 3.1->1.8, dar 3.4->0.9, koubba 2.7->0.7, slab 2.2->1.1, small 12.5->6.2); 0 faults. Writing the 2% slow test (test_furnish_required_share after test_furnish_required).
- 20:01 pytest -q: 163 passed (764 s, load ~180). SPEC note has the numbers. Running pytest -q -m slow -k furnish (task b9claakmo; includes the new 2% test).
- 20:16 DONE (not committed): pytest -q -m slow -k furnish 4 passed (new test_furnish_required_share: 8 per
  layout, sparse, <= 2% warned, 0 faults); homekit/furnish/interior fast tests 19 passed after the last
  formatting edits; full pytest -q 163 passed; build --quick ok; fingerprint 0 changed. Files: furnish.py,
  household.py, kit_new.py, SPEC.md, maghreb.toml, tests/test_citygen.py.
- Next (lead): review + commit; WORKLOG entry (draft above); HANDOFF lesson: "smaller pieces and another place
  before a warning: a lave-mains, a 70 cm tray, a squat wc, a qolla, a bed along the wall; choose the couple's room
  by its doors". Left for planners: 1.0 x 1.05 m wcs (0.7 m door), two-door maqsuras (dar No. 220), colonial
  kitchens without a fridge (12).
