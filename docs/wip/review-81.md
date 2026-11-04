# Review of prompt 81 (D1a district histories), branch wip/lore-81 at 4bd6ad8

Reviewer: independent read of `git diff c48fb1e...HEAD -- citygen tests styles docs/SPEC.md`, plus a sample
of the histories of the capital (Goumosbane) and three other cities from the quick world. No code changed.

Verdict: sound and close to mergeable; `pytest -k district_histories` passes (1 passed, 12.8 s). No blocker. Two medium points (tests of the output, English held in
code) and a few low wording and robustness fixes.

## Findings

| # | Where | Severity | Finding | Fix in one line |
|---|---|---|---|---|
| 1 | tests/test_citygen.py:1600 | medium | The test checks `District.history` on the plan objects only. Nothing checks the output: the `"history"` key in plan.json (export/lore.py:42) or the "### <city>: district histories" block in the gazetteer (export/lore.py:177). | Add `plan_json(plan)["districts"][i]["history"] == d.history` and assert every history appears in `gazetteer(world, [plan])`. |
| 2 | citygen/city/history.py:91, 93, 154-162, 17, 171-182 | medium | English words live in code, not in the style: `{"capital": "city"}`, "the village" / "the neighborhood", the `{where}` clause ", just east of the medina", the COMPASS words, `_number` words and the `_plural` rule. Another style pack (French, Andalusian) could not change them. | Move `place`, `folk`, the `where` template and the direction words into `[history]` in styles/maghreb.toml. |
| 3 | styles/maghreb.toml:109, history.py:123 | low | `fact.gates` is plural only: one counted gate gives "One gates lead in"; two gives "among them A and B" (both of them, not "among"). | Add `fact.gate` for one gate and use "{n} gates lead in: {some}." when n <= 2. |
| 4 | styles/maghreb.toml:116, history.py:139 | low | Same plural problem for shrines: a cemetery with one marabout (a `_random_point` miss) gives "One white-domed shrines ... stand". | Add a singular `fact.shrine` template. |
| 5 | history.py:44-47, tests/test_citygen.py:1618 | low | Gates are counted by point-in-district on a 1 m buffer, first district wins. A gate on the wall line can fall outside the buffer (count too low) or inside a neighbour; the test skips gates, so it would not notice. | Count gates from all `kind == "gate"` landmarks for the medina, and drop the gate exemption in the test. |
| 6 | styles/maghreb.toml:86-88, history.py:94 | low | The medina origins always say walls ("first walls went up", "its ramparts still stand"). True today (capital, city and town all have `walls = true`), but the planner has `kc["walls"]`; a style with walls off would contradict the map. | Choose a walls-free origin list (`origin.medina_open`) when `ctx.kc.get("walls")` is false. |
| 7 | history.py:132 | low | `n.startswith("Great Mosque")` tests an English name prefix to skip the great mosque; a renamed or pinned great mosque would slip through. | Skip by landmark kind or flag (or the medina's own great mosque index), not by name text. |
| 8 | styles/maghreb.toml:76-84, 86-106 | low | "in the time of the Caravan Age" / "the time of the Exiles' Return" reads padded; "in the time of" fits a ruler ("the Salt Kings") better than an age. Natural English for the stories would be "in the Caravan Age", "under the Protectorate". | Give each era its own phrase in `[lore]` or `[history] era_phrase` ("under the Protectorate", "in the Caravan Age") and use `{era}` as that phrase. |
| 9 | styles/maghreb.toml:121, history.py:146 | low | Top-3 trades come from fixed style weights, so every colonial quarter reads "cafe owners, teachers and pharmacists" and every suburb "business owners, engineers and professors" across cities (seen in the sample). True to the plan but repetitive. | Lower `fact_weights.trades` further, or name only the top trade plus one drawn from the rest. |
| 10 | history.py:25-30 | low | Canon is keyed by city name and district name, while the existing `[canon.names]` (world.py:110) is keyed by settlement id. A pin for an unknown district is ignored silently. Fine for now, but prompt 84 should pick one keying. | Note the key choice in docs/SPEC.md and warn on a pinned district name that does not exist. |
| 11 | history.py:73, 106, 110, 161 | low | Numbers in code: the 1.0 m and 5.0 m buffers, the 3-sentence floor and the 4-sentence cap. | Move `min_sentences`, `max_sentences` and `near_m` to `[history]`. |
| 12 | docs/SPEC.md | low | No SPEC note on the new plan.json `districts[].history`, the `[history]` style table or `[canon.histories]` (the helper notes say the lead may add it). | Add three lines to the plan.json and canon sections of SPEC.md. |

## What is sound

- Determinism: every draw comes from `ctx.rng("history", d.id)`, that is `stream(seed, "city", sid, "history", did)`,
  a new stream per district. `histories()` runs last in `plan_city` (city/__init__.py:138) and only reads the
  plan; no existing stream gets a new draw. The list templates are drawn in a fixed order before the weighted
  `choice`, so the output is stable. The test re-runs it and compares.
- No existing name or canon changed: only a new `District.history` field (default "") and a new `canon.histories`
  table; `[canon.names]` is untouched. The helper's fingerprint run reports only `gazetteer` and
  `plan/goumosbane/districts` changed, which the prompt allows.
- Facts the plan holds: landmarks by point-in-district, shrines from the cemetery's `marabout` buildings,
  cypresses from the cemetery planting (buildings.py:218), quays and lighthouses from `plan.port`, souks by their
  street's midpoint, trades from households, "known for" only on the main harbor. Eras are clamped to the
  city's founding, so no district is older than its city. In the sample nothing contradicted the map.
- Reads as natural English for stories in almost every case; for example the capital's Port de Kafra: two eras,
  quay length, the lighthouse and the harbor trade in four clean sentences.
- Templates, era rules, weights and harbor trades are in `[history]` of styles/maghreb.toml with a clear header
  comment; canon override works and is tested.
- No em dash character in the diff (checked).
