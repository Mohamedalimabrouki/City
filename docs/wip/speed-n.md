# hv notes: speed round N (byte-identical interior planning), worktree /tmp/claude-501/speed-n (wip/speed-n at c48fb1e)
Scripts in scratchpad/hv/: hv_dump.py (parallel survey: CPU + rooms.json md5 per home), hv_run.sh NAME SRC|keep
(survey capital + Ain Chilel into hv/NAME_cap.json, NAME_ain.json), hv_time.py ROOT CITY K.. (cpu+hash),
hv_prof.py / hv_callers.py (cProfile), hv_reps.py (repeat rates of cuts functions). HEAD copy: hv/snap_head.
Build input for all: /tmp/claude-501/flats-g/output/bodjantouna-42 (as rounds G-I).

## Done
- 19:10 quick build + fingerprint save before (worktree output/checks/fp-before.json).
- HEAD survey started (hv_run.sh head keep).
- Profile 914: cut_region 39%, assign 35%; shapely per-call overhead. Repeats: shared 70%, contact 66%,
  partition 50%, clip 80% of calls repeat the same shapes.
- cuts.py: memos for shared, contact, partition, clip keyed by (wkb, get_precision) of shapes.
  LESSON: wkb alone is NOT a full key: a set_precision'd shape carries its grid and overlays snap to it
  (958's hash changed until get_precision was in the key).
  914: 8.8 -> ~7.8 s, 958 12.1 -> 11.6 (machine loaded), hashes equal on 914/958.

- caps lowered after the survey snapshot: _SHARED 20000, _CONTACTS 10000 (memory ~100 MB worst per worker; caps never change values)
## Next
- more wins (free() per-call overhead, cut_region repeats), then survey "mine" and compare hashes with hv_cmp.
- 19:37 also: cuts.arms_of (trim's opening per shape, memo), spine.free per-frame zone spans + per-shape
  bounds/convex memo. 914 ~7.1, 958 ~10.9, 1324 ~4.9 (loaded machine), hashes equal.
  AABB cheap reject for width(): tested, settles 0 of 8812: dropped.
- 19:37 froze code; survey "mine" started (hv_run.sh mine /tmp/claude-501/speed-n -> hv/snap_mine), HEAD survey
  still running. Then: hv_cmp.py to compare hashes + CPU; pytest; build --quick; fingerprint compare.
- ~19:50 pytest: 163 passed. HEAD survey done (hv/head_cap.json, head_ain.json). Quick build + fingerprint compare running; mine survey running.
- build --quick ok (12.3 s, data reused); fingerprint compare before --allow '': 282 parts, 0 changed.
## Result (20:22 UTC)
- hv_cmp.py head mine: capital 1300 homes, Ain Chilel 1004 homes, 0 hash differences, 0 crashes.
- Survey CPU (8 workers, loaded machine): modern capital 1994 -> 1711 s (-14%), Ain 472 -> 380 s (-20%);
  slab 629 -> 559, colonial 1365 -> 1153, maison 430 -> 342, villa 42.6 -> 37.4.
- Back to back, one process (b2b_cap.txt): colonial 858 13.8->11.5, 1019 12.9->9.1, 890 13.2->11.1,
  773 12.7->10.0, 958 12.6->10.4, slab 1210 8.3->7.5; maisons (Ain) 923 5.5->3.5, 765 5.3->4.5, 532 4.7->3.9.
- Tree: only citygen/interior/cuts.py + spine.py changed, uncommitted. Tests 163 passed, fingerprint 0 changed.
## Next step
- Lead merges the diff of /tmp/claude-501/speed-n (git diff c48fb1e -- citygen/interior/cuts.py spine.py).
- Further wins: cut_region repeats (84/353 calls on 914 repeat, ~7%), to_wkb per-call cost now the top line
  (key memos by a cheaper id, e.g. cache wkb on the Cell), polylabel (maximum_inscribed_circle ~12% on 923).
