# fix-little: bound the little house's search (review of 3 November, finding 2)

Branch `wip/fix-little` from 3036039. Helper session of 3 November, 20:33-20:52 UTC.

## The finding
`citygen/interior/villa.py` `little()` (47.2 houses round 5) tries every guillotine cut of the floor's
rotated rectangle into 4 rooms on a `little_step` (0.5 m) grid, with no size limit.

## Measurements (this machine, load average 10-60, other sessions running)
The reviewer's stub job (`/tmp/claude-501/rv_little.py W H 0.5`: zones empty, windows on three walls), HEAD:

| floor | m2 | plan | s |
|---|---|---|---|
| 6 x 8 | 48 | found | 0.28 |
| 7 x 10 | 70 | found | 0.57 |
| 8 x 10 | 80 | found | 1.07 (3 other jobs running) |
| 9 x 9 | 81 | found | 1.17 (3 other jobs running) |
| 9 x 12 | 108 | found | 0.87-1.24 |
| 10 x 10 | 100 | found | 1.02 |
| 12 x 16 | 192 | none | 2.0 |
| 15 x 20 | 300 | none | 2.95 |

Profile of 9 x 12 (cProfile): 92 % of the time is `kinds()` on 8891 boxes (`piece()` shapely
intersection 1.07 s, the fits/strip/lit tests 0.84 s); the split enumeration and the plan loop are small.
So deduping splits reached by cuts in another order, and caching `shared`, were tried and gave nothing
measurable (reverted: the smallest change).

Real calls in Ain Chilel (HEAD, `hash_rooms.py` spy, region m2 / rotated rectangle m2 / plan / s):
794 villas and maisons, 5 `little()` calls (all maisons): k 530 137.9 / 150.8 / none / 2.86;
k 642 41.3 / 41.3 / none / 0.19; k 726 43.6 / 43.7 / none / 0.79; k 744 50.8 / 58.2 / found / 1.51;
k 985 54.2 / 54.2 / none / 0.21 (times with 3-4 jobs running). Only k 530 is over 80 m2 and it found no
plan at HEAD, so the bound changes no plan; it saves its 2.9 s.

## The bound
`[interiors.villa] little_most = 80.0` (styles/maghreb.toml): `little()` gives None at once when the
floor's rotated rectangle is over it (the grid, so the search's cost, is the rectangle's, not the floor's).
The cost grows about as the cube of the side; 80 m2 is about 1 s on the stub. A "little house" is small
anyway: the five rooms' `most` sum to 148 m2 but the hall has no most in `little()`, so there is no exact
bound from the room sizes.

## Proof (byte-identical rooms.json)
`docs/wip/fix-little-hash.py CODE_ROOT BUILD` plans every Ain Chilel villa and maison (the survey's loop,
`tools/interior_survey.py --city "Ain Chilel" --groups villa,maison`) and hashes `interior.to_json()` as
`export._write_json` writes it. HEAD code (a `git archive HEAD` copy) and the branch, same quick build
(output/bodjantouna-42 of this worktree):
**all 794 hashes equal, 0 differ** (finished 20:49 UTC). k 530's call now takes 0.0 s, its whole plan
0.91 s instead of 4.16 s; k 744's found plan has the same bytes. Output files: scratchpad `hash_head.txt` / `hash_new.txt` of this helper session
(`/private/tmp/claude-501/-Users-mohamedalimabrouki-Desktop/3a588b2b-bf2f-4191-acd4-5b1ae750c3f3/scratchpad/`).

## Checks
- `pytest -q`: 164 passed, 10 deselected, 3 warnings (165 s; the new `test_little_house_large_floor` and
  `test_little_house` pass, 2.0 s together).
- `build --quick`: done in 4.1 s; `tools/fingerprint.py compare before --allow ""`: 282 parts, 0 changed
  (the before fingerprint saved from the HEAD quick build before the edit).

## Next step
1. (Proof done: 794 of 794 equal.) To rerun it: `git archive 3036039 | tar -x -C <dir>`, then
   `python docs/wip/fix-little-hash.py <dir> output/bodjantouna-42` and the same with the branch root.
2. Merge the one commit onto the main branch; add `little_most` (with `little`, `little_step`) to SPEC 6c
   (review finding 6 says houses round 5 is not there yet) and a WORKLOG line.
3. Only if a little house over 80 m2 is ever wanted: speed the search itself. 92 % of its time is `kinds()`
   on every box; an exact pre-filter (a box smaller than the least room minimum cannot hold a room) before
   the shapely `piece()` is the place to start.
