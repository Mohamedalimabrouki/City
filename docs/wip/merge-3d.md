# merge-3d (helper, 3 November 21:40-23:45 UTC): one branch with the day's saved work, for the 3D view
Folder /tmp/claude-501/merge-3d, branch `wip/merge-3d`, from main 2ddab41. Not merged into main (the lead reviews it).
Scratch (lead's scratchpad): `m3d_survey_*.txt` (rooms.check), `m3d_furn_*.txt` (warned rooms), `m3d_furn.py`
(furnish-m's `hu_survey.py` pointed at this folder, plan cache off), `m3d_pytest*.txt`, `m3d_folds.py`.

## 1. Baseline on main 2ddab41
- Fingerprint `main3d` (saved by the first helper at 21:25 UTC after `build --quick` on 2ddab41) reused.
- `tools/interior_survey.py` (capital; `--city "Ain Chilel" --groups villa,maison`): exactly the WORKLOG's counts,
  see the table below. Warned rooms (furnish-m's survey, lived-in, 25 homes per layout nearest the centre):
  257 of 6163 = 4.2%, as furnish-m's own baseline.

## 2. Merged (each `--no-ff`, in the brief's order; area tests after each, then pushed)
1. merge-prep (speed-n, flats-j, furnish-m): clean. 26 interior/kit/furnish/slab tests passed.
2. fix-side-54, test-scrap-hall, test-cache-warm, fix-dar-is: clean (tests auto-merged at different places). 28 passed.
3. fix-materials: clean; homekit tests 5 passed; no furniture uses `copper`, `terracotta` or `net_green` after it.
4. fix-hide, fix-brass, fix-goods, fix-textile (each on furnish-m's original e871984, so each also brought furnish-m's
   changes a second time; git sees them as new against the base c48fb1e). Conflicts and how they were solved:
   - fix-hide, `furnish.py` place mode "side": kept ours (fix-side-54's fix); theirs was furnish-m's older line.
   - fix-hide, `styles/maghreb.toml` `[interiors.palette]`: one `twine_green` with kit-hide's new values (white, the
     `net` image, 0.4 m tile); `kit_old.py` net_pile: fix-hide's line (top-down UVs, four floats) with `twine_green`.
   - fix-brass, `kit_old.py` ibrik and pots_stack: fix-brass's shapes with the new names (`copper_ware`, `clay_red`).
   - fix-goods, `weave.py`: both sides added makers at one place; kept `_fleece`, `_net` (kit-hide) and
     `_goods_row` (fix-goods), one `MAKERS` with all. The merged file = fix-goods' file plus kit-hide's two makers
     (checked by diff).
   - fix-textile, `kit_old.py` `_smooth`: both added `uv=`; kept fix-textile's (converts uv to an array).
   - After each: the diff against the branch before equalled the kit branch's own diff over e871984 (same files, same
     line counts), so nothing of furnish-m was doubled or lost. `grep` after step 4: the only `"copper"` left is
     `kit_new.TRADES` (a shop trade, not a material); fix-materials' shared-name test passes.
5. colonial-k, villas-o, test-villa-369, fix-little: clean. 12 colonial/villa/little/flats tests passed.
- No em dash in `git diff 2ddab41 HEAD`.

## 3. The three review fixes (one commit each, each test fails before its fix)
- 67bfbff hidoura (rev-fix-hide): the outline jitter is along the radius only (`* rng.uniform(0.96, 1.04, (n, 1))`).
  Folded hides: 41 of 200 seeds before, 0 of 3000 after (my check on the real code; the reviewer's `folds.py`:
  radial-only 0 of 3000). Test `test_hidoura_never_folds` (200 seeds: the triangles' areas seen from above add up to
  the outline's). Only the hidoura's own stream; seed 42 had no fold but its hide changes a little.
- 522ff78 cushion cord (rev-fix-textile): `_smooth(..., nrm=)`; the cord's normals point out from its axis (the
  seam ring at the same index). Cord vertex normals facing away from their triangle: 24 of 96 (cos down to -0.73)
  before, 0 after (lowest cos 0.05: a three-point section). Test `test_cushion_cord_normals_face_out`.
  Not changed: the cover itself has 12 vertex normals at cos down to -0.19 at the sharp seam between the domed
  front and the flat back (one smooth cover over the seam, as fix-textile chose).
- b9f3be6 pots_stack (rev-fix-brass): bowls at (-0.16, 0.16) (were -0.17, 0.18), back jars at x +-0.15 (were 0.16).
  Reach over 200 seeds: x 0.308 / y 0.318 before, 0.298 / 0.299 after (half size 0.30). Test
  `test_pots_stack_stays_in_its_size`. The jars were the older overreach of the same kind, fixed with it so the
  test can hold the whole piece.

## 4. Gates
- `pytest -q`: 176 passed, 12 deselected, 4 warnings (shapely oriented_envelope, known) in 63 s.
- `pytest -q -m slow`: 11 passed, 1 xfailed (open item 47.1's marker, on main too) in 153 s.
- `build --quick` ok, and `--force` fresh (6.7 s); `fingerprint.py compare main3d`: 282 parts, 0 changed both times.
  Why none: a build never runs interior planning, furnishing or the home kit (all merged code is interior code).
- Interior survey (rooms.check pass counts; no group down):

| group | main 2ddab41 | merge-3d | cause |
|---|---|---|---|
| dar | 155/159 | 155/159 | |
| compact | 266/277 | 266/277 | |
| small | 81/83 | 81/83 | |
| koubba | 21/22 | 21/22 | |
| shop | 130/136 | 130/136 | |
| colonial | 3/270 | 5/270 | colonial-k |
| slab | 247/353 | 253/353 | flats-j |
| villa (Ain Chilel) | 167/178 | 168/178 | villas-o (No. 369) |
| maison (Ain Chilel) | 499/616 | 499/616 | |

- Warned rooms (lived-in, 25 per layout): 257/6163 = 4.2% -> 117/6139 = 1.9% (colonial 7.7 -> 3.6, compact 3.1 -> 1.8,
  dar 3.4 -> 0.9, koubba 2.7 -> 0.7, slab 2.2 -> 1.1, small 12.5 -> 7.0); 0 furnishing faults before and after.
  Colonial rooms 1797 -> 1773: colonial-k plans some sampled blocks differently.

## Left out, and open
- Nothing left out: every branch of the brief is merged and every gate holds.
- Not checked here: colonial-k's "chambres 4,895 -> 4,577" doubt from the WORKLOG (not a gate; a count of chambres
  over the colonial blocks would settle it); fix-side-54's own 2087-room sample went 1.72% -> 1.77% (one room).
- SPEC 6d kit table still says tray_brass 48 and pots_stack 150 triangles (now 80 and 180; rev-fix-brass), and the
  `kit_old.TABLE` already has 80 and 180; SPEC not touched (the brief allows SPEC edits only for conflicts).
- Not looked at in the 3D viewer or Blender (the lead runs `tools/make_blend.py`).
