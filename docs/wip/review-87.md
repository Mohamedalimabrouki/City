# review-87: quick read-only review of prompt 87 (D5a Arabic place names)
Scope: `git diff c48fb1e...HEAD -- citygen tests styles` on wip/arabic-87 (fcc49c8, eb6bbfe). No code changed.

## Checked, no finding
- Determinism: `_pick_i` makes the same single `rng.integers` draw as `_pick`; the draw order in `_syllable_parts`
  (coda roll, coda, onset, vowel), `_core_parts`, the `core_parts` fallback, `country`, `settlement`, `district`
  and the saint pick (citygen/city/landmarks.py) is unchanged. Covered by `test_arabic_names_take_no_draw...`
  and the slow strip test (tests/test_citygen.py:5118).
- Latin names: the templates moved to styles/maghreb.toml:46-55 equal the old hard-coded strings (Medina of,
  Great Mosque of, Mosque of, Souk {a} {w}, the seven souk repeats). Canon: world.py:123-126 pins Latin as
  before and clears the Arabic of a pinned Latin name, so no wrong Arabic is shown.
- Collisions: `used` tracks Latin only; a scratch run of 3 x 90 settlement names (seeds 1-3) gave 0 duplicate
  Arabic spellings. No "" entry in `endings` / `berber_endings` today.

## Findings (file:line, severity, one-line fix)
1. citygen/names.py:258, Low: `fixed_name` reads `n[key]` with no default, so a style without `medina`,
   `great_mosque` or `village_mosque` now raises KeyError where the old code had built-in English; fix: a
   default per key, as `souks()` does with `names.get("souk", "Souk {a} {w}")`.
2. citygen/names.py:219, Low (latent): `country()` tests `lat[-1]` of the last part, the old code the last
   letter of the whole name; an empty ending would raise IndexError; fix: `if lat and lat[-1] in "aeiou"`
   (or a style test that endings hold no "").
3. citygen/names.py:234 and :266, Low: `_twins` checks only that the *_ar keys exist, not their lengths or the
   `prefixes_ar` kinds, so a style with a short twin list fails with KeyError/IndexError mid-build (the length
   test covers maghreb only); fix: `_twins` raises a ValueError naming the key when a twin length differs.
4. citygen/world.py:128 (and :124, older), Low: `int(sid) < len(settlements)` lets a negative id pin the last
   settlements; fix: `0 <= int(sid) < len(settlements)`.
5. citygen/export/lore.py:135, Low: the gazetteer always has an "Arabic" column, empty for a style without
   twins; fix: add the column only when some settlement has `name_ar`.
6. tests/test_citygen.py:5118, Low (test gap): the pinned-name case checks the settlement only, not that its
   plan's `{s}` landmarks (kasbah, medina, mosque, station, lighthouse) carry no `name_ar`; fix: one assert on
   a plan of the pinned settlement.

Verdict: deterministic, Latin and canon names unchanged; nothing blocks the merge. Arabic quality (feminine
cores with masculine descriptors, vowels_ar choice) is still Ali's call from the 30-name sample.
