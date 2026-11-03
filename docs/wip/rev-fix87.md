# rev-fix87: review of wip/fix-87 (HEAD 768e90b tests + notes, and HEAD~1 c13b77a the code it tests)
No High or Medium findings. Run: `pytest -q -k "fixed_names_and_arabic or twins or lore"` 3 passed (25 s). Full suite and quick build left to check-87.

1. citygen/names.py:260, Low: `n.get(key, FIXED_DEFAULTS[key])` looks up `FIXED_DEFAULTS[key]` first, so a future key that the style has but FIXED_DEFAULTS lacks raises KeyError. Today's callers (city/__init__.py:83 medina, city/medina.py:247 great_mosque / village_mosque) are all in the dict, so nothing breaks now. Fix: `n[key] if key in n else FIXED_DEFAULTS[key]`.
2. tests/test_citygen.py:5137, Low: the comment says "no Arabic" but only `str(...)` is checked. Fix: also assert `fixed_name({"names": {}}, "medina", s="X").ar == ""`.
3. tests/test_citygen.py:5136-5143, Low: the new `prefixes_ar.<kind>` length check (names.py:273-275) is untested. Fix: set `n["prefixes"] = {"city": ["El"]}` and expect ValueError matching "prefixes_ar.city".
4. Findings 2, 4, 5 of review-87 still have no test (the fix notes say so), Low. Cheapest: a gazetteer test on a world whose settlements have no name_ar, checking the header has no "Arabic" and every table row has 7 cells.
5. tests/test_citygen.py:5132-5133, OK: the slow test can fail; Landmark always has `name_ar` (filled from `name.ar` at city/model.py:96), so the `getattr(..., "")` default hides nothing. Plain `m.name_ar` would read clearer (Info).
6. citygen/export/lore.py:131-140, OK: header, separator and rows have 8 cells with Arabic and 7 without; byte-identical for maghreb (it has twins).
7. citygen/world.py:124 and 128, Info: negative and too-large canon ids are now skipped silently; a warning would let a typo be noticed.
8. Determinism: no new random draws, no set order; the `_twins` loop over the TOML dict only decides which error comes first. Numbers in toml: FIXED_DEFAULTS is English text that was in code before prompt 87 too (Info: fixed_name reads only style["names"], so moving it to defaults.toml would need a merge).
Left: nothing of this review.
