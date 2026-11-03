# Merge prep (helper, worktree /tmp/claude-501/merge-prep, branch wip/merge-prep from 3036039): notes
Task: cherry-pick, one at a time and in this order, wip/speed-n, wip/flats-j, wip/furnish-m onto the main
branch's latest commit 3036039; after each: pytest -q, build --quick, fingerprint compare before --allow "".
Not merged into the main branch. All three branches start at c48fb1e (one commit before 3036039, the WORKLOG).

## Baseline (20:34 UTC)
- build --quick on 3036039: ok (8.2 s); `tools/fingerprint.py save before`: 282 parts.

## Step 1: wip/speed-n (e21a2fa, cuts.py + spine.py memos, byte-identical speed round)
- Cherry-pick: clean (no conflict) -> 16985d9.
- build --quick ok (1.1 s, data reused); fingerprint compare before --allow "": 282 parts, 0 changed.
- pytest -q: 163 passed, 10 deselected (slow), 3 warnings (shapely RuntimeWarning in oriented_envelope:
  divide by zero; the same 3 tests warn on a copy of 3036039, checked) in 58 s (machine load ~20).

## Step 2: wip/flats-j (f3fd5fa, slab 247 -> 253: best_lay/scrap_hall, duplex ladder, two tests)
- Dry run first (`git merge-tree --write-tree --merge-base=c48fb1e HEAD f3fd5fa`): clean. Cherry-pick: clean
  -> db40631 (tree 09338b5, the dry run's tree).
- build --quick ok (1.2 s, data reused); fingerprint compare before --allow "": 282 parts, 0 changed.
- pytest -q: 165 passed (163 + the two flats-j tests), 10 deselected, 4 warnings (the same shapely
  oriented_envelope RuntimeWarning, now also in test_slab_duplex_ladder_from_the_couloir) in 78 s.
- Extra check (speed-n must stay byte-identical on flats-j's new paths): `citygen interior K --density sparse`
  on the quick build for the 7 homes flats-j changed (1081, 1133, 1147, 1157, 1228, 1297, 1354) with the flats-j
  tree alone (git archive f3fd5fa) and with this branch (speed-n + flats-j): rooms.json md5 equal on all 7.
  Same homes with main-branch code (3036039): different md5 (checked 1081, 1133, 1354), so the check is real.
  Script: /tmp/claude-501/mp_one.sh TREE TAG K (results /tmp/claude-501/mp_int.txt).

## Step 3: wip/furnish-m (e871984, prompt 54 round 3: hand_basin, shower_small, place "side", wc_keep,
## couple_maqsura, SPEC 6d note, the slow 2% test test_furnish_required_share)
- Dry run (`git merge-tree --write-tree --merge-base=c48fb1e <step 2 tree> e871984`): clean. Cherry-pick: clean
  -> 4b29ffe (tree cb4d135, the dry run's tree). tests/test_citygen.py is touched by flats-j and furnish-m in
  different places (lines ~4849 and ~4993); no duplicate test names.
- build --quick ok (1.7 s, data reused) and again with --force (fresh, 12.3 s): fingerprint compare before
  --allow "": 282 parts, 0 changed both times.
- pytest -q -m slow -k furnish on a copy of this exact tree (git archive cb4d135): 4 passed in 69 s, including
  the new 2% test on top of flats-j's plans (it plans the 8 homes per layout nearest the centre, slabs too).
- rooms.json of the 7 flats-j homes with all three merged: md5 equal to flats-j alone (furnish-m changes no
  plan, as its notes say). Furnish warnings on those 7 homes (sparse): 18 before furnish-m, 6 after.
- pytest -q: 165 passed, 11 deselected (slow, now with the new 2% test), 4 warnings (same shapely
  RuntimeWarning) in 89 s.
- The other slow tests on the same tree copy (`pytest -q -m slow -k "not furnish"`): 6 passed, 1 xfailed (the
  xfail marker of open item 47.1 is already on 3036039) in 234 s. So all 11 slow tests are fine too.
- Wider byte check, flats-j alone vs all three merged (rooms.json md5, quick build, sparse): 35 slab homes
  (numbers 1084 to 1390 step 9) all equal, 5 colonial homes (773, 858, 890, 958, 1019) all equal.
  Results: /tmp/claude-501/mp_int_wide.txt, mp_int_col.txt; compare script /tmp/claude-501/mp_cmp.sh.

## Result (20:43 UTC)
- All three cherry-picks clean, in order, no conflict to resolve: 16985d9 speed-n, db40631 flats-j, 4b29ffe
  furnish-m (on 3036039). 12 files, +474 -45. No em dash in the diff. Not merged into the main branch.
- Every step: pytest -q passed (163, 165, 165), build --quick ok, fingerprint 0 of 282 parts changed (and a
  fresh `--force` quick build at the end: 0 changed). Slow tests on the final tree: 10 passed, 1 xfailed.
- Interplay checked: speed-n's memos keep flats-j's new paths byte-identical (7 changed homes, 35 slab and 5
  colonial sampled homes: equal to flats-j alone); furnish-m changes no plan and its 2% test passes on flats-j's
  plans.
- Scratch copies (safe to delete): /tmp/claude-501/mp_s3 (final tree), mp_fj (flats-j tree), mp_h (3036039),
  mp_int (interiors planned for the checks).

## Next step (lead)
- Review the three commits (each still carries its "WIP ... saved at the weekly reset" message), then bring
  them onto the main branch: `git merge --ff-only wip/merge-prep` from the main branch, or cherry-pick
  16985d9 db40631 4b29ffe with `-e` to give each its real message (speed round N; 47.2 flats round J;
  prompt 54 round 3).
- Docs the helpers left to the lead: WORKLOG entries (furnish-m's draft is in docs/wip/furnish-m.md; flats-j's
  counts in its Result; speed-n's in its Result), the HANDOFF lesson in furnish-m's notes, the "Resume here"
  counts (slab 247 -> 253 of 353), and whether docs/wip/{speed-n,flats-j,furnish-m}.md stay in the main branch
  (only docs/wip/2026-11-03-review.md is there now).
