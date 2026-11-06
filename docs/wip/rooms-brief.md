# Interiors on the final buildings, step 1: the room behind a balcony (the lead's brief)

Where this comes from: the first bullet but one of the WORKLOG "Resume here" entry (the order of work), `docs/wip/facades.md` section 8, `docs/LEAD.md` section 3 ("Judge interiors on more than one plan", "Check a helper's root cause", "A cause is proved by taking one thing out"). Read those. Rules: `CLAUDE.md`.

Interiors are made on demand: `citygen/interior/`, `python -m citygen interior`. A build's parts do not change: `tools/fingerprint.py compare before --allow ""` must show 0 changed (baseline saved at c936562). The facade does not change either: the planner adapts to the facade, never the reverse.

## What the lead measured on c936562

`tools/interior_survey.py`, pass counts of `rooms.check`:

| plan | dar | compact | small | koubba | colonial | slab | villa | maison | shop |
|---|---|---|---|---|---|---|---|---|---|
| quick capital | 149/159 | 263/268 | 86/88 | 25/26 | 9/278 | 263/347 | | | 122/137 |
| villa town Takobka | 35/37 | 82/82 | 20/22 | 1/2 | | | 123/146 | 383/500 | 41/46 |

`tools/balcony_survey.py`, quick capital: 3,150 door-windows with a rail, 9,863 slab balconies with their own door, 0 before a plain window.

Behind a balcony door today, 1 plan in 4 of the capital (`facades.md` section 8): 91 baths and wcs (34 colonial, 57 slab), 60 colonial and 440 slab kitchens, 132 colonial halls, couloirs and droj.

## Do, in this order

1. **See it first.** Add a `--rooms` option to `tools/balcony_survey.py`: the room behind every door-window and slab door, by kind and by group, over a whole city or 1 plan in N. This is your bar, and it stays in the repo.
2. **Never a bath behind a balcony.** The room behind a balcony is a salon or a chambre; a kitchen for a service balcony. Never a bath or a wc, 0 on every plan. In a colonial block also no hall, couloir or droj where another cell can take it: report the rate. `spine.py:105` and `bayplan.py:72` treat a colonial balcony door as a window, so that typical floors share a plan: floors of one stack share cells, so a cell with a balcony door on any floor of the stack is closed to a bath on all of them.
3. **The small slab wcs.** `test_furnish_required_share` carries an xfail: 49 of 2,142 rooms, 2.29%, bar 2%, from 1.3 m2 wcs in stacked plans since the gable windows. Find the cause by taking one thing out, get under the bar, take the xfail off.
4. **Furniture keeps the door clear.** `furnish.py` `DOORS` holds `balcony`; once baths are gone drop the wet-room exception in `_keeps` (lines 353-359) and check that nothing stands in a balcony door.
5. **A curtain to the floor on door-windows**, as SPEC 6d says for balcony doors. Reuse what the home kit holds if it can do it; a new piece gets its own stream and an exact name in the allow list.
6. **Dark rooms.** `facades.md` counted 88 rooms in the sample with no possible window (party walls). Count them on the final plans. If the planner can avoid them within this step's rules, do; if it needs courts, say so and stop on it.

## How to judge

- Never fix one house for its own sake: a rate on one plan is partly memory of that plan. Judge on the quick capital, `--city villas`, and two other worlds: seed 5 (it has a villa town) and seed 7. `tools/interior_survey.py` takes about 18 minutes for all groups on the capital because of colonials and slabs: run it in the background, without polling; `--groups dar,compact,small,shop` for other worlds.
- No group may fall on the capital or the villa town: if one does, read why before going on. The 47.1 and 47.2 work won colonial blocks and slabs only slowly: this step is about balconies, not those bars. If a fix wins them, good; do not chase them.
- Slow tests that read what you touch, run them yourself: `pytest -q -m slow -k "furnish or new_district or slab or colonial or old_town or balcon"`, and `pytest -q`.
- New tests at most 2 s on `pytest -q`; on-demand commands keep their two-process byte test.
- Pictures: two interiors, a colonial chambre and a slab salon with their balcony door and curtain, as `docs/wip/rooms-1-*.jpg`, each looked at by you.

## Environment

`.venv/bin/python`, never `python`. `pytest -q` 70 s, `-m slow` 5 minutes, `build --quick` 13 s. Never open files in `output/`. Never start Blender. Do not commit, do not `git add`. Scripts of yours in the shared scratchpad start with `rm_`. Snapshots start a web server: sandbox off. Your context is the main cost: grep before you read, read only the lines you need, keep outputs short.

## End

`docs/wip/rooms-1.md` current at each checkpoint: what is done, numbers before and after per group and per plan, what is left, text ready for WORKLOG, HANDOFF, LEAD and SPEC. Report under 200 words, with what you did not manage, plainly.
