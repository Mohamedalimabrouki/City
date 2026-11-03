# Review of wip/fix-materials (review-mats, 3 November, about 20:55 UTC)

Reviewed: `git diff 3036039..941b135` (8a4bb29 the fix, 941b135 notes). No code changed by this review.

## Answers
- All uses renamed? In code, yes: kit_old (ibrik, kanoun, khabia, tabouna, pots_stack, net_pile), kit_new
  (chicha), `[interiors.palette]`. `git grep` finds no home-kit use of `copper`, `terracotta`, `net_green`
  left in citygen/interior, tools/ (make_blend.py, blender_kit_export.py, viewer index.html and
  gallery.html) or tests; `furniture.json` holds piece names and places only
  (furnish.py:142-145), no material names. The remaining uses are city ones and must stay: mesh/boats.py
  `net_green`, mesh/props.py `terracotta` and `copper`, mesh/furniture.py:281-282 `copper` (the `sabil` fountain),
  kits/tounes/manifest.json `terracotta`, `[palette]` lines 113 and 188. Two SPEC lines were missed (below).
- Does the city's value win? Yes: `interior_materials` is `{**home, **city}`. Dropping the old
  `cfg.get("palette")` is safe: `home.materials` already holds `[interiors.palette]` (homekit.py:63).
- Measured on the fix: the city and home dicts share 203 names (all of `[palette]`) and none differs;
  `[interiors.palette]` shares none with the city. So the order no longer changes any value today.

## Findings (file:line, severity, fix)
1. docs/SPEC.md:2189 (`pots_hanging` row), medium: still lists `copper`, the next 6d builder (furn-55b)
   would use the city's copper; write `copper_ware`.
2. docs/SPEC.md:2069, low: "`copper` metallic 0.5" in the metals sentence; write `copper_ware`.
3. wip/furn-55 citygen/interior/kit_life.py:141, medium (merge): `_pot` (used by `pot_geranium`,
   `pot_basil`, `pot_jasmine`) draws `"terracotta"`; after
   this fix it draws the city's #B8643C (no roughness) instead of `clay_red` #B5653F r0.9, and no test
   catches it (`[palette]` terracotta is in home.materials too). Change to `"clay_red"` when merging
   furn-55; tell furn-55b the same.
4. tests/test_homekit.py:30-42, low: the "city wins" order is not tested: with today's data the old
   order `{**city, **home}` passes every assert too (checked by script). The real guard is the
   disjoint-names assert, which is right. Optional: add
   `assert interior_materials({"x": 1}, {"x": 2})["x"] == 1`.
5. tests/test_homekit.py:41-42, low: a home piece may still use a `[palette]` (city) name and silently
   take the city colour (how finding 3 slipped through). Optional: assert each home piece material is in
   `[interiors.palette]` or a short allowed list of shell names.
6. Merge note, low: wip/furnish-m and wip/merge-prep still hold the old lines in kit_old.py and
   kit_new.py; a merge keeps the fix's lines unless those branches edited the same lines (see merge-map).

## Does the new test fail on the parent?
Yes, for the right reason. In a scratch worktree on 3036039 with the new test file copied in:
`1 failed` (it stops at the import: the parent has no `interior_materials`). The same checks run by
script on the parent's data: `[interiors.palette]` and the city share `copper`, `net_green`,
`terracotta` with different values, so the disjoint-names assert fails, and the parent's merge (home
winning) fails the city assert. On the fix all asserts pass.

## Verdict
The fix is right and complete in code; merge it after fixing SPEC lines 2069 and 2189 (findings 1-2),
and rename furn-55's `terracotta` pot (finding 3) when that branch is merged.

