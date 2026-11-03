# Prompt 81 (D1a District histories) - helper notes
Worktree /tmp/claude-501/lore-81, branch wip/lore-81 at c48fb1e. Do not commit (lead commits).
## Plan
- new module citygen/city/history.py: histories(ctx, plan) sets District.history (new field, default "")
  after plan_fronts in plan_city; own stream ctx.rng("history", d.id).
- templates + era rules in styles/maghreb.toml [history]; canon override cfg [canon.histories."<city>"]."<district>".
- plan.json districts get "history"; gazetteer gets a "District histories" list per planned city.
- fingerprint allow: plan/*/districts, gazetteer
## Status
- 19:41 started; baseline build + fingerprint save before running.
- 20:10 code written: citygen/city/history.py (new), District.history (model.py), call in city/__init__.py after plan_fronts,
  plan.json "history" + gazetteer "### <city>: district histories" (export/lore.py), styles/maghreb.toml [history].
  Sample via scratchpad/hz_try.py. Next: tests (tests/test_citygen.py test_district_histories), pytest, build, fingerprint compare.
- 19:53 test_district_histories added (tests/test_citygen.py before test_fingerprint_tool), passes. build --quick OK.
  fingerprint compare: only gazetteer + plan/goumosbane/districts changed (both allowed). Full pytest running.
  Next: sample other cities for variety/contradictions, then write WORKLOG/HANDOFF/ROADMAP text below.
- 19:59 polish: {place}/{folk} fields, list facts (trades variants), weighted fact choice ([history] fact_weights),
  cemetery shrines fact (counts marabout buildings), "known for" only on the main harbor, more "today" variants.
  Next: final full pytest + build --quick + fingerprint compare (allow plan/*/districts,gazetteer).

## Texts for the lead to paste
ROADMAP line 98: - [x] 81 D1a District histories
WORKLOG entry:
### 2026-11-03 - Prompt 81 (D1a): district histories
- New `citygen/city/history.py`: each district gets `history`, 2-4 sentences from the style's new `[history]`
  templates and the plan's own facts: era (from `[lore] eras`, never before the city's founding: the medina,
  village and cemetery date from the founding, the colonial quarter, port and parks from the Protectorate,
  newer kinds from the Republic), compass side from the medina, gates, kasbah, cathedral + theatre, station,
  neighborhood mosque, souks, cemetery shrines (marabout buildings), quay length + lighthouse, the city's
  harbor product (main harbor only), households' top 3 trades. Own stream `ctx.rng("history", d.id)`, run last
  in plan_city (reads the finished plan, changes nothing else). `[canon.histories."<city>"] "<district>" = "..."`
  in a world file replaces a text (prompt 84 extends canon).
- plan.json districts carry "history"; the gazetteer lists "### <city>: district histories" per planned city.
- Test test_district_histories: sentence count, eras, every named landmark stands in its district,
  deterministic, canon override.
- Fingerprint: gazetteer and plan/goumosbane/districts only.
HANDOFF lessons:
- Lore text must be built only from facts the plan holds (landmarks by point-in-district, buildings by kind,
  quays by district); never claim something the map may not show (cranes, walls, trees) without checking the
  planner (e.g. cemeteries have cypresses and marabouts: buildings.cemetery_and_parks).
- Era rule: a district era is clamped to >= the settlement's `founded`, so the gazetteer never contradicts itself.
- 20:11 gazetteer histories block moved after the size line. build --quick OK; fingerprint compare: only
  gazetteer (3532 -> 6040 bytes) and plan/goumosbane/districts changed (allowed). Final full pytest running
  (slow here, shared CPU). Next: read its result; if green, report. Not done: SPEC.md note on plan.json
  "history" field (lead may add), commit (lead).
- 20:12 DONE: full pytest 164 passed (12 min, shared CPU). Tree passing. Next step for the lead: review, paste
  WORKLOG/HANDOFF/ROADMAP texts above, optionally note plan.json districts "history" in docs/SPEC.md, commit the
  6 files (citygen/city/history.py new; __init__.py, model.py, export/lore.py, styles/maghreb.toml, tests/test_citygen.py).
