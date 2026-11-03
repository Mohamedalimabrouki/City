# Houses patio planner (47.2 houses round 6) - helper notes
Worktree /tmp/claude-501/houses-patio (wip/houses-patio at 61a8778), not committed.
Survey: CITYROOT=/tmp/claude-501/houses-patio <venv python> $S/hr/hr_dump.py --city "Ain Chilel" --groups villa,maison --out X.json
($S = this scratchpad; copies of round 2's hb2 scripts renamed hr_*)
## Steps
- 18:50 baseline build + fingerprint before saved.
- 19:25 Built citygen/interior/patio.py (comb planner: couloir strip(s) on the blind side, rooms cut straight
  across from it, DP per side over cut positions, wc at a couloir dead end), hooked in villa.plan (flag
  interior.patio) and layout.patio (a last pass for maisons with 'has no window', kept only when check passes);
  styles/maghreb.toml patio, patio_step. Measured: one-strip version won 1 (No. 509) of 66 blind-room maisons,
  +2 s median per failing house. Floor 0 never planned (the strip through the door rarely meets the palier).
  L-shaped ways (2 strips) version: too slow (>600 s for 66 houses), being measured.
  Debug: $S/hr/hr_floors.py blind_ids.txt out.json (per floor planned?), $S/hr/hr_one.py ids.
- 20:03 Final shape: patio.plan runs only on UPPER floors holding a blind room (layout.blind; floor 0 never
  planned in 66 houses: its strip through the door rarely meets the palier, and its sides' slabs across the
  way come out in two parts around notches; it cost up to 14 s a house). L-ways kept only for floor 0 (now unused).
  Survey (tree vs HEAD hashes, Ain Chilel): maison 499 -> 500 (won No. 509, the only changed house, none lost),
  villa 167 identical; 0 mesh/step faults on passing; time + up to 3.6 s on failing houses (No. 634 2.6 -> 6.3 s,
  488 +2.1, 485 +1.9, 554 +1.9): too costly for 1 win. pytest 162 passed (before the new test) + new
  test_patio_house_upper_floor passes (0.7 s under load, step 1.0); build --quick; fingerprint 282 parts 0 changed.
  Picture output/checks/472-patio-plans.png (worktree): 509 floor 1 three windowed chambres, but the sdb is a
  1.4 x 6.5 m strip across the floor (mediocre).
  Hash proof of other layouts: HEAD copy at $S/hr/headcopy (git archive 61a8778, output symlinked): HEAD_ain_other.json,
  HEAD_cap.json vs tree runs tree_ain_other.json / tree_cap.json.
- NEXT STEP: either drop the round (1 win, +time) or make it worth it: (1) floor 0: cut each side along the
  way AND across (slabs that split around a notch: take the part touching the way, the rest a second slab row),
  (2) the sdb/wc as a notch at the couloir rather than a full-depth slab (a family-grade bath), (3) prune the
  strips (deterministic count budget) to bring the time back under +15%.
