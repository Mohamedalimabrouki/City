# fix-87 (from wip/review-87): the six Low findings of docs/wip/review-87.md
Done, all six, output byte-identical:
1. `fixed_name` (citygen/names.py) falls back to `FIXED_DEFAULTS` (the old built-in English: Medina of, Great Mosque of, Mosque of) when a style lacks the key.
2. `country()` tests `lat and lat[-1]`, so an empty ending no longer raises IndexError.
3. `_twins` raises a ValueError naming the key when a `*_ar` list (or a `prefixes_ar.<kind>`) length differs from its Latin list.
4. citygen/world.py: a canon id must be `0 <= id < len(settlements)` (a negative id no longer pins the last settlements).
5. citygen/export/lore.py: the gazetteer's Arabic column appears only when some settlement has `name_ar`.
6. tests: the slow pinned-name test also plans settlement 2 and checks its "{s}" landmarks carry no `name_ar`; a new fast test covers 1 and 3.

Checks: `pytest -q -k "name or lore or canon or twins"` 9 passed; the slow test passed. Quick build before and after: every output file
has the same hash except summary.json and plan.json `stats/seconds` (timing, changes every run) and tiles/index.json `build_key` (a hash of the code).
Left: no test for findings 2, 4 and 5 (simple guards, checked by reading only).
