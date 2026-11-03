# review-55: prompt 55 first slice (wip/furn-55, 3 commits after furnish-m e871984)

Scope: `git diff e871984..HEAD` (kit_life.py, homekit.py, maghreb.toml, test_homekit.py). No code changed.
Severity: high = wrong output or a test that lies; medium = visible defect or a claim that is not true; low = polish.

## Findings (file:line, severity, one-line fix)
- citygen/interior/kit_life.py:212-214, medium: vase_flowers has no stems; the heads float at z 0.33-0.40 over a vase mouth at z 0.20 (13 cm of air). Fix: three thin leaf_green stems (3-segment lathe, 6 tris each); the piece is 48 tris now, so 66 <= 80.
- citygen/interior/kit_life.py:201-203, medium: pot_jasmine puts its flowers at radius r - 0.05 = 0.175, inside the bush (bush radius 0.19-0.22 at z 0.62-0.86): flowers k=0, 1, 2 are fully hidden, only 3 of 6 show. Fix: place each ball at the bush profile's radius at its z (interpolate the lathe profile) plus 0.01.
- maghreb.toml:1933 and kit_life.py:6, medium: "the viewer lights it at night" is not true yet; tools/viewer/index.html:1064 `LIT_AT_NIGHT` has only `glass_lit`, nothing reads `lamp_glow`. Fix: add `lamp_glow` to LIT_AT_NIGHT (and CLEAR_AT_NIGHT at 1068 if wanted) in the step that places `_on` pieces, or reword the comment to "will light".
- citygen/interior/kit_life.py:245-247, low: shoes have no upper over the front 9 cm (the toe is a bare 2.5 cm black sole), while the docstring says "the uppers lower at the toe". Fix: a low toe box (z 0.025-0.06) or one wedge per shoe; mind the 40-tri budget (now 4 boxes x 10 = 40, so a wedge in place of the upper box).
- citygen/interior/kit_life.py:22,29,35 vs SPEC 6d, low: SPEC anchors `lantern_table` "on / floor", `pot_basil` "floor / on", `photo_frame` "wall / on"; the code has one anchor each (on, floor, wall). Fix: say in furn-55.md which one furnish uses, or add a second anchor/variant later (a photo frame "on" needs a stand).
- citygen/interior/kit_life.py:228-238 vs SPEC 6d, low: khomsa lists `brass`; `glaze_blue`, but only brass is built and `glaze_blue` (maghreb.toml:1938) is used by no piece. Fix: a `khomsa_glazed` variant in glaze_blue, or drop the palette line until it is used.
- citygen/interior/kit_life.py:85, low: chandelier `reach = w/2 - cup + 0.002` makes the tulips reach 0.402, extent 0.804 > W 0.80 (inside the test's 0.02, harmless). Fix: drop the `+ 0.002`.
- citygen/interior/kit_life.py:129, low: lamp_bedside shade is single-sided fabric_beige (maghreb.toml:1913 has no double_sided): seen from below or through the open top its inside is culled, so the shade disappears from inside. Fix: a `double_sided` beige for shades, or a second inward lathe.
- citygen/interior/kit_life.py:21 (for step 3), low: fanous hangs 1.15 m; in a 2.6 m modern ceiling its bottom is at 1.45 m. Fix: furnish places it only where the ceiling leaves >= 2.0 m below it (traditional rooms are high).

## Checked and fine
- Sizes, categories and tris of all 18 rows match SPEC 6d; `_check_table` checks extent (0.02), tris <= budget, anchor faces and that every material is in the palette.
- Material clash (export.py:59, `{**city, **home, **interiors.palette}`, the interiors side wins): none of the 9 new names (lamp_glass, lamp_glow, voile, iron_white, glaze_blue, leaf_green, photo_sepia, bread, plastic_yellow) is in the city `[palette]`, so nothing of the city changes. Pre-existing, not from this diff: `terracotta` is in both (maghreb.toml:188 #B8643C city, :1880 #B5653F interiors), so inside an interior the city's terracotta pieces take the interior colour; the new pots use it. Flowers and fruit use the city's `awning_red` / `awning_yellow` as SPEC says (they follow any awning recolour).
- `_on` twins (homekit.py:71-74, pre-existing code): same Part objects, lamp_glass renamed lamp_glow, same spec; the new test checks all of that and that lamp_glow == lamp_glass in the palette. Every light uses lamp_glass (tested), so no twin is a silent copy.
- Ceiling pieces: fanous, ceiling_lamp, chandelier, bulb_bare all span z -H..0 with z0 = -H; the test checks hi <= 0.005 and lo = z0.
- Determinism: each piece has its own `stream(seed, "piece", "home/<name>")`, no maker draws from it, TABLE and MAKERS are dicts in fixed order, no sets iterated. Nothing is added to an old stream.
- Tests: the count test in test_home_pieces_traditional now adds `lights` from home.pieces, correct for twins from any module; the disjoint-names assert covers kit_life. The new test would fail on a missing twin, a renamed part or a palette drift.

## Run here
- `pytest -q tests/test_homekit.py`: 5 passed (1 slow deselected), 2.9 s. Tris now: vase_flowers 48/80, shoes 40/40, pot_jasmine 128/220, fruit_bowl 64/70, chandelier 312/400.

## Not done (time)
- No full pytest, no build, no render looked at (shot-55 does the render).
