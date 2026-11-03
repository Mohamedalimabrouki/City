# rev-kit-textile: review of `git diff e871984..HEAD -- citygen tests styles` (3 November, 20:57 UTC)

Scope: one commit (a646d52 WIP kit-textile): the doukkana's mattress and back cushion in
`citygen/interior/kit_old.py`, and `[interiors.furnish.textiles.*]` in `styles/maghreb.toml`.
Checked by reading only (no tests run, 4 minute slot).

## Findings (file:line, severity, one-line fix)
1. kit_old.py:323 (`_smooth(mb, mat, pos, tris)` in `mattress`), low: smooth normals over the whole
   profile, so the hard back bevel and the long flat top blend at shared vertices (soft chamfer, the top
   shades as a gradient). Fix: smooth only the round's two steps; give back, bevel, top and front their
   own vertices (hard faces).
2. styles/maghreb.toml `proud` comment, low: "0 buried" is wrong. At 0 the cord's centre lies on the round,
   so half of it still shows; 1 is tangent ("sitting on it"). Fix the comment, or use
   `off = pipe * (2 * proud - 1)` so 0 really buries it.
3. kit_old.py mattress `belly`, low (naming): the front is one straight face with its foot set back, so it
   overhangs (normal tilts down) rather than bellying out. Fix: say "the front leans back to its foot",
   or add one mid point bulging forward.
4. kit_old.py:29 TABLE budget 30 for the mattress: 12 long + 10 end + the pipe tube (8 if `_tube` is an
   open 4-sided tube) = 30, exactly the budget, no headroom. Cushion: 16 band + 8 + 8 + 8 tassel = 40 =
   budget. OK, but verify `_tube`'s count.
5. kit_old.py:1215, low: `shape = {**...}` copies for nothing; fine. The config path is right
   (`homekit.py:66` passes `interiors.furnish`, so `textiles.<base>` is read).
6. Numbers: `TEXTILE` in code duplicates the toml as a fallback (same pattern as `SIZES`). OK, two places
   to keep in step.
7. Tests, medium-low: none added. Add a small test that a `textiles.mattress.round` override changes the
   mesh and that the mattress and cushion triangle counts equal their TABLE budgets.

## Looked fine
- Determinism: no new draws (rng unused in both makers), no set order, own `home/<name>` streams unchanged.
- Faces: cushion is closed (back fan + piping band + domed fan, all turned outward); mattress bottom is
  open but lies on the bench (hidden); ends capped with +-x normals. Pipe tube ends stay open, flush with
  the mattress ends (as before).
- Materials: no new ones (ticking, velvet_*, velvet_gold, velvet_red already in the kit); no clash.

## Left
- Did not run pytest or a build; did not check UVs from `_smooth`; sizes unchanged so not re-checked
  against SPEC 6.
