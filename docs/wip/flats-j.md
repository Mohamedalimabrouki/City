# Flats round J (helper hs, worktree /tmp/claude-501/flats-j, branch wip/flats-j at c48fb1e): notes
Scratch: .../scratchpad/hs (hs_dump.py = round G/H survey pointed at flats-j; hs_run.sh NAME GROUPS [only];
hs_old.sh NAME SRC; hs_cmp.py A B; hs_sum.py; hs_flat.py ROOT K FLAT prints a flat; hs_tries.py ROOT K prints
best_lay tries). h0 = HEAD c48fb1e copy (snap_h0), survey started 19:15 UTC.

## Step 1 (19:16 UTC): causes of the way-home blocks (flat/*.txt)
- Scrap hall on a single-flat top floor (No. 1133, 1157, 1228, 1297): best_lay gets 3 entries; the first is on a
  palier side facing a 0.6 m strip of the region (hall 1.2-1.9 m2, `fits` False, flat_score 2); slab
  `retry_variants = 0` so the other entries are never tried; the front door opens into the scrap and a chambre
  takes a palier door. Fix: in best_lay, a first plan with a scrap hall tries the other entries (slab too).
- No. 1265, 1272: cuisine only via a chambre (a wc between the hall and the cuisine). 1088: sam only via a
  chambre (couloir meets it 1.28 m). 1199: hall at the palier, couloir not met (cuisine between). 1269: salon via
  chambre. 1354, 1147: duplex/triplex upper floors (stair lands in a chambre / sdb).
## Step 2 (19:22 UTC): flats.best_lay + scrap_hall: a first plan with a scrap hall tries the other entries
  (share 1.0, entries only, not "again"). No. 1133, 1157, 1228, 1297 then plan with no fault (hs_tries).
  Next: full survey a1 vs h0, old/ain identical check.
## Step 3 (19:24 UTC): flats.duplex (slab only, `kind` passed): a duplex ladder whose foot (room below) or head
  (cell above) is a chambre/sdb/wc/cuisine moves into the lower flat's couloir/hall (S.ladder near the way's side
  nearest the old spot; lay key + "way"), kept only when both ends are then not private (`duplex_lay`).
  No. 1354, 1147 then plan with no fault. Next: survey a1.
## Step 4 (19:33 UTC): test `test_slab_scrap_hall_tries_other_doors` (tests/test_citygen.py, hand-made, passes).
  Surveys h0 (HEAD) and a1 (steps 2+3) running in background (load average ~150, slow).
  Blind chambres looked at (not fixed): No. 1301 f3 a program room missing (score 8, the droj on f3), No. 1365 the
  duplex upper floor's lay ["chambre","sdb","chambre*"] fills the blind middle with a chambre, No. 1091 and 1198
  windows wasted on a hall / a 45 m2 salon with 3 windows while chambres stand on a blind wall.
  Way home left: 1088 (sam meets the couloir 1.28 m), 1199, 1265, 1272 (wc between hall and cuisine), 1269.
(Times above are approximate; real clock at step 4 was about 19:25 UTC.)
## Step 5 (19:30 UTC): why way_doors places nothing (hs_way.py, hs_nb.py): No. 1088 the sam shares 0.91 m with the
  couloir (the roof newel's droj notches its corner); No. 1265 the wc (2.7 m2) between the hall and the cuisine
  (cuisine-wc 0.94 m, cuisine-hall 0); No. 1272 cuisine-hall 0.90 m (need 1.3). These need the spine to keep the
  cuisine on the hall or couloir (a fix in `spine.lay`'s cuisine pick or a wet-room carve beside it), not doors.
  No. 1365: duplex upper floor lay (hs_dup.py): the blind middle-left cell (25 m2) typed chambre.
## Step 6 (19:36 UTC): build --quick ok, fingerprint compare before --allow "": 282 parts, 0 changed. Test
  `test_slab_duplex_ladder_from_the_couloir` added (hand-made, passes). Full pytest running (started before this
  test was added: rerun the two new tests with -k). Waiting for h0 / a1 surveys.
## Step 7 (20:05 UTC): a1 survey (steps 2+3): slab 247 -> 251, won 1133 1147 1157 1228 1297 1354, LOST 1086 1279,
  5 passing changed; colonial identical. Cause: scrap_hall fired on halls that still met the couloir (1086, 1135,
  1382: 1.1-1.2 m) or a big hall not `fits` (1279, 12.5 m2). Narrowed: a scrap hall meeting no couloir/salon/sam by
  more than 0.8 m (the arch length of spine.doors); wins' halls meet them by <= 0.32 m. Next: a3 survey (full).
## Step 8 (20:09 UTC): old town + capital maisons (677) and Ain Chilel villas + maisons (794): every rooms.json
  identical h0 vs a1 (scrap_hall's narrowing after a1 cannot touch them: best_lay/duplex are flats only). a3 (slab,
  narrowed scrap_hall) survey and full pytest running.
## Result (20:15 UTC), tree = snap_a3 (diff: hs/hs_round_j.diff; uncommitted in /tmp/claude-501/flats-j)
- Changed: citygen/interior/flats.py (`best_lay` + `scrap_hall`: with no second tries (slab), a first plan whose
  hall is a scrap no hall fits and meets no couloir/salon/sam by more than 0.8 m tries the flat's other doors fully
  searched; `duplex` + `duplex_lay` + `R_PRIVATE`: in a slab block a duplex ladder whose foot or head stands in a
  chambre/bath/cuisine moves into the couloir or hall below, against its side, kept only when both ends are then
  not private), tests (`test_slab_scrap_hall_tries_other_doors`, `test_slab_duplex_ladder_from_the_couloir`).
- Counts (h0 = HEAD c48fb1e copy vs a3, rooms.json hashes): slab 247 -> 253 of 353 (won 1133, 1147, 1157, 1228,
  1297, 1354; lost 0; flats 4,555 -> 4,563 of 5,140; faults 777 -> 759; 11 changed, 1 passing changed: No. 1081,
  its 2.3 m2 hall opening on a chambre, cuisine and sdb now a 10.7 m2 hall, still passing), colonial 3 of 270
  (a1: every rooms.json identical; scrap_hall is never called for colonial, share 0.5). Every passing interior 0
  mesh.faults, 0 step faults. Old town + capital maisons (677) and Ain Chilel villas + maisons (794) identical.
- Checks: pytest -q 165 passed (715 s, loaded machine); build --quick; fingerprint 282 parts, 0 changed.
- Next step: blind chambres (No. 1365 duplex upper floor: a blind room-sized leftover typed chambre by
  `spine.leftovers` since joining a neighbour passes `most`; No. 1301 f3 a program room missing beside the droj;
  No. 1091/1198 windows taken by a hall / a 3-window salon while chambres stand blind) and the way home left
  (1088 sam notched by the droj, 1265/1272 a wc between the hall and the cuisine, 1199, 1269): spine picks.
