# Prompt 87 (D5a Arabic place names) notes - worktree /tmp/claude-501/arabic-87 (wip/arabic-87 at c48fb1e)
## Status
- 19:35 UTC: baseline quick build + fingerprint "before" saved. Starting names.py pairs design.
## Decisions
- Prompt 68 (natural names) and 84 (canon) not done: no natural names to twin; [canon.names_ar] keyed like [canon.names] (settlement id).
## Next step
- implement names.py pairs + style *_ar twins
- 19:58 UTC: implemented names.py (Name str subclass with .ar, _pick_i, part pairs, fill_ar/join_ar/fixed_name, _twins),
  style twins (onsets_ar.. descriptors_ar, prefixes_ar, districts_ar, saints_ar, word_ar, medina/great_mosque/village_mosque/souk templates),
  name_ar on Settlement/World/District/Landmark/Souk (__post_init__ takes Name.ar), lore.py json + gazetteer both scripts, slim_plan districts.
  Quick build OK; fingerprint: gazetteer, world, plan/goumosbane/{districts,landmarks,settlement,souks} changed (all allowed).
- Next: tests in tests/test_citygen.py (twin lengths, arabic letters, strip-ar equality, collisions), pytest, viewer card.
- 20:10 UTC: hx_verify.py proved world.json and every plan part equal to "before" once name_ar is dropped.
  4 tests added at end of tests/test_citygen.py (twin lengths, no draw + arabic letters, world/plan carry arabic, slow strip test passes).
- Next: full pytest, viewer card (tools/ artifact viewer) shows name_ar, sample of 30 names for Ali.
- (clock: earlier entries were stamped wrong; real time at this step 19:45 UTC) viewer card: tools/viewer/index.html describe() returns ar, fillCard adds an rtl line (.ar css).
- Next: full pytest result, the 30-name sample (hx_sample30.py), WORKLOG/HANDOFF/ROADMAP text below.

## Texts for the lead to paste (not written into docs by this helper)
### WORKLOG entry
## 2026-11-03 - Prompt 87 (D5a): place names in Arabic script
- Every generated place name now has an Arabic twin built from the same draws: `[names]` gets *_ar lists
  (onsets, vowels, codas, endings, berber, country endings, descriptors, prefixes) each the same length as
  its Latin list, `[names.districts_ar]`, `saints_ar`, souk `word_ar`, and fixed templates (medina,
  great_mosque, village_mosque, souk, souk_repeats) that moved the English names out of the code.
- `NameMaker` builds names from (Latin, Arabic) parts with `_pick_i` (same single draw as `_pick`) and
  returns `Name`, a str carrying `.ar`; `_pick` unchanged. `name_ar` on the country, settlements,
  districts, landmarks and souks in world.json and plan.json (omitted when empty); the gazetteer shows
  "Name (الاسم)" and an Arabic column; the viewer card shows a right-to-left Arabic line; slim_plan keeps
  district name_ar. `[world] name_ar` and `[canon.names_ar]` (by settlement id) pin Arabic spellings.
- Fingerprint: world, gazetteer, plan/goumosbane/{settlement,districts,landmarks,souks} changed; a script
  proved world.json and every plan part identical to before once name_ar is dropped.
- Not done: natural names (prompt 68 not built yet; twin them when 68 lands).
### HANDOFF lesson
- **Arabic names** (prompt 87) are spelled part by part from the same draws as the Latin name: each
  `[names]` list has an `*_ar` twin of the same length, and `NameMaker._pick_i` gives the index. Rules in
  `names._spell_ar`: a dropped short "a" is written ا between equal letters and before a vowel; a coda k
  before an onset h is one خ (the Latin reads "kh"); a ة inside a word becomes ا. The article ال and بو are
  joined to the next word (`join_ar`). A name returns as `Name` (a str with `.ar`); data classes take its
  `.ar` in `__post_init__`. Removing every *_ar key turns Arabic off and changes nothing else (slow test).
### ROADMAP
- [x] 87 D5a Arabic place names
- 19:45 UTC: added gazetteer check + ڨ (g_ar) option check to tests; fast arabic tests 1.1 s. Full pytest running (hx_pytest.log).
- Next: after pytest, final build --quick + fingerprint compare + hx_verify.py, then report.
- 19:56 UTC DONE (not committed): full pytest 166 passed (12m44s); after the last test/doc edits the arabic+world+config tests
  pass (6, incl. slow strip test); final build --quick OK; fingerprint 6 parts changed (gazetteer, world,
  plan/goumosbane/{settlement,districts,landmarks,souks}), hx_verify.py: identical once name_ar dropped.
  Also documented [world] name_ar in citygen/defaults.toml and worlds/example.toml ([canon.names_ar] example).
- Next step for the lead: review the diff in /tmp/claude-501/arabic-87, paste WORKLOG/HANDOFF/ROADMAP texts above,
  commit; Ali judges the 30-name sample (open: masculine descriptors after feminine cores; vowels_ar a-choice).
