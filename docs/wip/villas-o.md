# villas round O (helper hy) notes
Worktree /tmp/claude-501/villas-o (wip/villas-o at c48fb1e). Not committed.
HEAD copy: scratchpad/hy/head (git archive c48fb1e). Survey: scratchpad/hy/hy_dump.py (CITYROOT=<code root>, build from villas-o/output).
## Steps
- 19:30 started: build --quick + fingerprint save before.
- 19:52 little for villas (gate + 'has no salon' for villas): 369 passes, 320 not
- 20:00 roof newel door_to (hall, salon) for little villas; box_room last pass (villa.place_box picks roomiest box, layout last pass on SHORT faults, 2+ floors): 307 -> 1 fault (salon via cuisine), 388 still 2
- 20:12 tried: narrow box in box_room scoring (307 worse: no chambre; 388 same) -> reverted. carve after box_room again kept (no win on 307 yet). Tree villa survey (before carve line): 168/178 (+369). HEAD surveys of Ain Chilel others + capital running in bg (hy/head_ain_other.json, hy/head_cap.json)
- (times above were wrong: clock check 19:52 UTC after them)
- 19:55 tree villa survey (little+door_to+box_room+carve): 168/178, only 307 (2->1 faults) and 369 (won) changed. 0 mf/sf.
- 20:00 tried + removed: day_swaps (salon <-> the cuisine it is reached through): 307 salon 11.2 < 12 min, 332 cuisine L 14.1 too thin: 0 won.
- 20:02 tried + removed: `unfit` (a chambre under its minimum, a U round the stair, cut in two by spine.halve): No. 380's is 15.2 m2 < 2 x 8: 0 won. Carve after box_room removed too (0 won).
- Final code: layout.py little gate (+ "has no salon" for villas), box_room last pass; villa.py place_box(box_room) + roomy, lit_top -> newel_rooms(door_to=("hall","salon")); spine.newel_rooms door_to tuple; toml little += villa, box_room = {villa = 2.6}; test_box_room_roomy.
- 20:03 tried + removed: little rejecting pieces with holes (No. 320's droj is a hole in its floor): still None. Code frozen; snapshot scratchpad/hy/tree; tree surveys launched (tree_ain_all.json all groups with mesh; tree_cap.json). HEAD: head_villa.json, head_ain_other.json (done), head_cap.json (running).
- 20:14 picture output/checks/472-villas-plans.png (worktree; before | after: 369 won, little plan, roof stair off the hall; 307 upper floor now 2 chambres + couloir + sdb, floor 0 still salon via cuisine). pytest running (task b1p400q52). Next: compare tree_ain_all vs head_villa+head_ain_other, tree_cap vs head_cap (hy_cmp.py), build --quick, fingerprint compare before --allow "".
- 20:14 pytest -q 164 passed (704 s under survey load); build --quick ok; fingerprint compare before --allow '': 282 parts, 0 changed. Waiting for tree_ain_all / head_cap / tree_cap.
- 20:16 PROOF Ain Chilel (rooms.json md5, HEAD copy c48fb1e vs tree snapshot hy/tree): 1004 homes, 1002 identical; changed only villa 307 (2 -> 1 fault, still fails) and 369 (won). maison 616/616 identical (499 pass), dar 57, compact 69, small 35, koubba 8, shop 41 identical. Villa 167 -> 168. Passing interiors: 0 mesh.faults, 0 step faults. Times: 369 1.07 -> 1.83 s, 307 0.57 -> 0.80 s (under load).
- Still failing villas and why (measured this round):
  250 entry steps 0.06 m treads + way (hopeless class); 353 no U stair; 390 a wall crosses an inner: not plan faults.
  307 floor 0 salon only via cuisine (east wing): a salon<->cuisine trade gives a 11.2 m2 salon (< 12): needs the spine to put the salon by the hall.
  388 38 m2 floors, a 5.9 m stair in a 6.45 m deep floor: every box leaves two strips; box_room moves it only to x=3.3 (window on the far wall), the spine still plans no chambre: needs an upper floor of one chambre + sdb beside the stair (a `little`-like upper plan).
  320 one floor 40 m2, its roof stair (droj, fixed by the roof's stair room) is a hole in the floor: `little`'s straight cuts cannot go round it (rejecting holed pieces: still none). Next: little with the droj's sides as extra grid lines.
  380 a 15.2 m2 U chambre round the stair upstairs (< 2 x 8 m2 for two): next: the thin arm as a placard/dressing joined to the couloir or sdb.
  330 upper couloir off the palier (only through a chambre); 332 salon only via an L cuisine round the stair; 399 blind chambre (relit finds no cut).
- 20:30 head_cap done (1782 s wall); tree_cap running
- 20:34 PROOF capital (quick build, every home): 1300/1300 rooms.json identical (903 pass both), 0 bad passing. Worktree code == snapshot hy/tree (diff -r). Patch: scratchpad/hy/hy_round_o.patch.
## DONE (not committed). Result: villa 167 -> 168 (won 369, 307 2->1 faults, none lost); maisons, old town, capital identical.
## Exact next step: villas 388 (an upper floor of one chambre + sdb beside a stair that spans the floor's depth) and 320 (`little` with the droj's sides as grid lines); then 380 (U chambre's thin arm as a placard).
- 20:34 note: the lead saved this tree as WIP commit 4b916ba on wip/villas-o (20:31 UTC, docs/wip/villas-o.md); its code is exactly the verified tree. Patch vs c48fb1e: scratchpad/hy/hy_round_o.patch.
