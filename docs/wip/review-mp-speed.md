# Review: the speed-n part of merge-prep (review-mp-speed, 3 November, 20:54 UTC)
Scope: `git diff 3036039 HEAD -- citygen/interior/cuts.py citygen/interior/spine.py` (commit 16985d9
cherry-picked in 3099981). Question: can the speed-up change any output or its order? Code read only, no runs.

## Verdict
No output change found. Every memo stores the result of a pure function of its key, nothing iterates over
a memo (only get, set and clear), and a cleared memo only costs time. The survey in `docs/wip/speed-n.md`
(2304 homes, warm caches against HEAD's none, 0 hash differences) and the fingerprint (0 changed) agree.

## What was checked
- Keys are complete: shape bytes (`to_wkb`: type, ring order, coordinates, Z) plus `get_precision` for every
  overlay memo (clip, shared, contact, partition, arms_of); `Frame.line` depends only on c, angle (u, v come
  from it) and the constant `REACH`, all in the `partition` key; GRID, TOUCH, HAIR are module constants that
  no test or code reassigns (grep), so module-level memos cannot go stale between builds in one process.
- Values are immutable: shapely geometries, floats, tuples; `contact` returns a fresh list of tuples of
  tuples, `arms_of` a tuple, so no caller can change a cached value.
- `shared` and `contact`: the `distance > TOUCH` test moved inside the miss branch, same result.
- `trim` through `arms_of`: same arms, same filter (area >= 0.005), same sort key, `hair` for the same arms.
- `spine.free`: `free_spans` lives on the job like `zone_points` (same lifetime, never reset), so the spans
  match the points; `free_shape` holds bounds and a convexity test that do not depend on the grid.
- Order and hash seeds: memo keys are bytes, floats and ints; dict layout depends on PYTHONHASHSEED but no
  memo is iterated; no float sums were reordered; no parallel code changed (caches are per process).

## Findings (file:line, severity, one-line fix)
- citygen/interior/spine.py:445, low (pre-existing, not from speed-n), `free_memo`'s key `mk` has no
  `get_precision(poly)` although its entries come from overlays (the notes' own lesson: bytes alone are not
  a full key) - add `shapely.get_precision(poly)` to `mk`.
- citygen/interior/cuts.py:127-137, 199-211, 241-251, 355-366, 465-476, low (memory), five module-level
  memos of up to 20000 / 10000 entries each live for the whole process; with 8 workers the notes' "about
  100 MB worst per worker" adds up - fine now, keep the caps in one place (or `defaults.toml`) if raised.
- citygen/interior/cuts.py:248 and spine.py:433, very low, float keys treat -0.0 and 0.0 as one key; a frame
  centred exactly on 0 could reuse a result whose coordinates carry the other sign of zero (only the printed
  "-0.0" could differ) - no action unless a byte diff ever shows "-0.0".
- citygen/interior/dar.py:598 and 601, low, `[p for p in polys[...] if p is not host/piece]` filters shapes by
  identity; memos now hand out one shared object for equal inputs, so two equal pieces in one list (only a
  duplicate piece, which a sound plan never has) would both be dropped where HEAD dropped one - filter by
  index instead (`del lst[i]`), or keep as is and note it.
- tests, medium (missing guard), no test compares a plan made with warm memos (another home first) against a
  cold one; the survey did this once by hand - add a small test: plan home B alone, then plan A then B in one
  process, compare the rooms bytes.

## Left
Nothing run here (no pytest, no build): the review relies on the survey and fingerprint numbers in
`docs/wip/speed-n.md`.
