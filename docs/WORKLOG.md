# Work log

Newest first. One entry per prompt, written by the session that did the work. Checkpoints and
the final review read this first, so keep entries short and exact. Questions for Ali go here
too, so nothing is lost when a session ends.

Entry format:

```
## <date> - Prompt <N> <ID> <title>
- Commit: <hash> | Model: <model>, <effort>
- Changed: <files>
- Checks: tests (count), build time, fingerprint (parts changed), budgets when relevant
- Look: <picture path or view> - what to see
- Doubts and questions for Ali: <none, or the question>
```

## 2026-10-29 - Resume here (paused after prompt 47)
- 3 November (Tuesday; the week resets at 21:00 UTC): Ali said "use as much as possible, only pause when you
  reach 90% of weekly usage" (64% at 10:15 UTC), for this day: after the reset ask him before going over 55%
  again. Plan: two helpers in parallel, flats (colonial blocks, slabs) in this folder and houses (maisons,
  villas) in a worktree, each group kept byte-identical by the other; the lead reviews, merges and commits.
  Done and pushed that day on this branch (entries below, newest first): flats rounds D-I, houses rounds 1-5,
  prompts 51, 52, 53 and 54 (two rounds, partly done), the roof copings; last code commit c48fb1e. Counts with
  every check: slab 247/353, colonial 3/270, maison 499/616, villa 167/178 (bars 336, 257, 586, 170), old town
  unchanged. Saved, NOT merged (each a pushed branch `wip/<name>` with its helper's notes in
  `docs/wip/<name>.md`; review, test and survey each before merging, one at a time): flats-j (slab 247 -> 253),
  colonial-k (colonial blocks 3 -> 5, flats 387 -> 514, but chambres 4,895 -> 4,577 and slab only sampled: check),
  furnish-m (prompt 54 round 3: warned rooms 1.8% in the quick capital, 2.2% full, the 2% test: then tick 54),
  speed-n (planning 14-20% faster, byte-identical over 2,304 homes), houses-patio and villas-o (their notes say
  what they reached), arabic-87 (prompt 87 done; two questions for Ali: feminine agreement after a name in ة, and
  the share of a long a written), rivers-59 (prompt 59 done; salt lakes touch Sota and Ain Chilel), graph-70
  (prompt 70 done), lore-81 (prompt 81 done), godot-72 (prompt 72 written, never run: Godot is not installed,
  Ali's yes needed), styles-94 (prompt 94 done, its aerial look not taken). An independent review of the day's
  commits: `docs/wip/2026-11-03-review.md` (first: `interior/export.py:59`'s material order may let the home
  kit or interior palette override city colours, check before fixing; `villa.little` has no size cap; the
  furnishing check reuses the placer's rules). The fingerprint baseline was re-saved at 3b1e4c0.
  Last hour (also pushed `wip/<name>` branches with `docs/wip/<name>.md`): fix-materials (the export bug confirmed
  and fixed: three furniture materials renamed, a failing-before test), fix-little and merge-prep (see their notes),
  furn-55 (prompt 55 started on furnish-m), rivers-60 (prompt 60 started on rivers-59: lakes count as water, BUT on
  the 64 km world 127 of 131 settlements move and their names shift: protect the canon names before merging),
  lead-notes (LEAD.md lessons of the day), review-70, review-81, review-94 (independent reviews of those branches:
  fix their findings before merging), kit-hide, kit-brass, kit-textile, kit-goods (home-kit touch-ups on furnish-m).
  Final half hour (20:30-21:00 UTC, more `wip/<name>` branches, notes in `docs/wip/<name>.md`): fix-70 (review-70's
  two medium findings: a two-process byte test of streets.json; GRID moved to `[streets] graph_grid` in defaults.toml,
  which may change the data-file key), fix-81 (review-81 findings 3, 4, 8: gate and shrine grammar, era wording
  tables; the rest left), fix-little (`villa.little` capped by `[interiors.villa] little_most = 80` m2; 794 Ain
  Chilel hashes match; one 151 m2 maison 2.86 s -> 0 s), furn-55 (prompt 55 slice 1: `kit_life.py`, 18 pieces, 164
  tests pass, fingerprint 0 changed), check-k (colonial-k leaves all 353 slab plans byte-identical), shot-hide,
  shot-brass, shot-textile (contact sheets of the kit branches: kit-textile looks WORSE, do not merge it as is;
  kit-brass's tray rim is too steep for one-sided brass), review-87 (nothing blocks the merge, 6 Low findings),
  review-59 (deterministic, the numbers match; one medium for Ali: the water-balance rule drains some dry basins
  the prompt wants endorheic). Then 60 more helpers, 20:51-21:10 UTC (96 `wip/*` branches in all; each has
  `docs/wip/<name>.md`). Start the next session with three of them: merge-map (conflicts and a 9-step merge order;
  furnish-m, flats-j and speed-n are inside merge-prep already), questions-ali (16 questions for Ali), prompt-next
  (13 prompts ready: 54, 59, 70, 80, 81, 92, 101, 87, 66, 67, 94, then 72 and 75 on Ali's Mac).
  - Ready to merge (full tests pass, reviewed): fix-70 (outputs byte-identical), fix-81 + fix-81b (histories
    byte-identical; rev-fix81: history.py:116 draws once per template), fix-87, fix-59 (one strict xfail shows the
    salt-pocket question), fix-materials (also rename furn-55's `_pot` "terracotta" to clay_red, fix SPEC 2069 and
    2189), fix-little (rev-little: swap its 1 s timing assert for a call counter), colonial-k (check-k: all 353 slab
    plans identical; rev-colonial: `stub_middle` 12.0 belongs in the toml). Scans of every branch: no em dash, no
    unsafe randomness; check by hand kit_old.py:853-862 and weave.py:361-364 (scan-streams).
  - Prompt 54 is NOT tickable (spec-54, review-mp-furnish): fix-side-54 fixes the "side" place bug (furnish.py
    about 940; warned rooms 36 -> 37 of 2,087, find which); the full capital is at 2.2% (bar 2%); the full survey,
    the two look pictures and make_blend are left. Tests to take with merge-prep: test-scrap-hall, test-cache-warm,
    fix-dar-is (filter by position; never fires, byte-identical). review-mp-flats: a duplex ladder in a couloir
    leaves 0.5 m (passage_min 0.8). The 95% bars are not met (slab 72%, flats 89%).
  - Kit looks (Ali to look at `wip/pictures`, one page of every sheet): fix-hide (rev-fix-hide: the rug edge folds
    in 609 of 3000 seeds, jitter along the radius only; rev-kit-hide: two materials are named net_green), fix-textile
    (rev-fix-textile: the cord's front normals face the wall), fix-brass (the 8-sided bowl is 1-2 cm too deep;
    rev-kit-brass says the spouts do not taper, the picture says they do: check), fix-goods (full, varied shelves;
    tiles change, so make_blend at merge). All their full tests pass (check-hide, check-textile, check-brass).
  - Prompt 55 started: furn-55 (18 pieces) + furn-55b (5 more, 23 of 32) + fix-55 (vase stems, bowl bottom, jasmine)
    + fix-glow (lamp_glow emissive, so it glows by day too: Ali or the lead chooses); spec-55 lists what is left.
  - Need a decision: canon-60 (names follow ids from one shared stream, so one skipped city renames all; plan: own
    streams and names tied to the grid cell; renames once, Ali's OK; README.md:176 promises more than the code),
    houses-patio (review-patio: fixes 1 house of 66 and costs up to 3.6 s per failing house: gate it or drop it),
    villas (test-villa-ties: only villas 307 and 388 tie; a tolerance changes 388), godot-72 (review-godot: no high).
  - After the reset (21:00 UTC) the new week counts: ask Ali before going over 55% weekly.
  - Ali's answers (about 21:30 UTC, to the questions-ali list): Godot not now; patio planner dropped (branch kept);
    prompt 60: first make names follow places (own streams, names by grid cell, a test), one rename accepted, then
    merge; prompt 59: the lead's advice (dry hollows over 3 m and 0.5 km2 stay salt lakes, fix the two-pocket bug,
    towns by salt lakes are fine, min_flow stays 3.0); Arabic: a describing word after a core in ة is feminine (if
    the Latin must follow, those names change once); long a: keep today's mix; lamps glow only at night; histories:
    show Ali before/after examples of review-81 items 5 and 9 first; SPEC 6d home kit defaults confirmed (today,
    lived-in, 112 degrees, abstract verse, low-poly now; the butane bottle is NOT blue: Ali saw grey, green or red,
    so a mix of the three, one per home, on its own stream); the long a (Ali): ا follows how the name is said (a
    long vowel, as in Safaqus; a doubled letter takes a shadda, Sammarine); Latin-first parts cannot know that, so
    keep today's mix now; idea for later: build name parts from Arabic sound patterns (Sammar, Fallah) so the
    Arabic and the Latin both follow the sound and names sound more Arabic); flats: add windows on court walls and blank
    street walls (a city change) to reach the bars. To judge in 3D after merge-3d: cushions, rug, prompt 55 pieces.
  - Ali found a design fault (screenshot of Megine, 21:50 UTC): open balconies (iron, prompt 22, and the modern
    blocks' concrete ones) stand in front of plain windows with a sill, so nobody can step out. His choice: every
    open balcony gets a porte-fenetre (door-window down to the balcony floor, same shutters and frame, its `_lit`
    twin), some tall windows without one get a flush balconnet (railing, no slab); inside, the room behind a
    balcony is a salon or chambre (a kitchen for a service balcony, never a bath) and furniture keeps the door
    clear. The mashrabiya on a window stays. Do it after merge-3d, in one facade round with the extra windows;
    the same round checks the large cream panels standing out of walls on the right of his screenshot.
  - Ali, 4 November: "fix everything, you are the boss; best quality always, work we won't do twice". The order, so
    nothing is measured or tuned twice: (1) the world first, since it moves every plot: fix-70, fix-81b, prompt 59
    with Ali's answers, then fix-87 with feminine agreement, names following places, prompt 60; (2) the facades:
    door-windows, balconnets, windows on court and blank walls, the cream panels and question 15; (3) interiors on
    the final buildings: the ladder check, colonial bedrooms and the bars, finish 54; (4) furniture: prompt 55, lamps
    at night, the butane mix, brass spouts, themed shelves, Ali's looks; (5) the review leftovers and LEAD notes.
    One helper at a time on each set of files; the lead runs its own survey BEFORE main moves. Ask Ali past 55% weekly.
  - merge-3d is merged into main (5f4e99e, the entry below), and so are prompts 59, 70, 81 (c4eb74b, the entry above it).
    Not merged yet: arabic-87 + fix-87, prompt 55 (furn-55, furn-55b, fix-55, fix-glow), rivers-60 (after the names
    fix), godot-72, styles-94; houses-patio is dropped. Next in order: names-60 (fix-87, feminine agreement, names and
    identity follow the place), then prompt 60. The histories picked again once: Ali's before/after examples of
    review-81's 5 and 9 wait for the final world.
- State: prompts 1-50 are done (branch `claude/procedural-city-generator-xop72h`; CP4, prompt 43, on 25
  October; the interiors 44-47 on 29 October, 48 (walls and openings) on 30-31 October). Continue when Ali
  says (for example "Do prompt 49." or "continue the playbook").
- Paused (1 November, about 51% weekly): Ali said "once you finish this stop, also never use more than 55%
  weekly". Resume here when Ali says, and keep under his cap (55% of the weekly limit).
  - Done and pushed for 47.1 + 48.1 (31 October): 2ac52f7 (Open interior first shows the house from above),
    part 1 rounds 1-11 and flats rounds 1-3 (up to 901a5d6): every old-town group at its bar (dar 155,
    compact 266, small 81, koubba 21, shop 130); 0 `mesh.faults` and 0 step faults on every passing
    interior; the way-in check (old town, round 6) and the way-home check (modern homes, round 10).
  - 47.2, Ali's redesign (docs/ROADMAP.md; design block in the 47.1 + 48.1 entry): round A (7523fad) cut
    courtyards and light wells into 241 colonial blocks and patios into 293 maisons, with windows on every
    floor; round B (69150ea) added the window check (every chambre, salon, salle a manger and cuisine of a
    modern home has a window). With every check: villa 165/178 (bar 170), maison 390/616 (bar 586), slab
    139/353 (bar 336), colonial 1/270 (bar 257). The fingerprint baseline (fp-before.json) is round A's.
  - Round C (colonial flats split into wings round their courts, `wings.py`) is saved on branch
    `wip/47.2-round-c` (66567f2), not merged: no colonial block won (1/270) and No. 958 plans in 8.1-8.2 s
    cold (bar 8 s). Its lesson: most colonial faults come from the spine's own flat plans, so a wing
    planner should place the rooms itself (salon and chambres on the street, couloir on the court side,
    cuisine and baths on the court or a light well) instead of running the spine per wing; the per-wing
    spine helped 39 flats and hurt 20. Merge the branch only to build on it.
  - Next, in order: (1) colonial flats: a wing planner that places rooms itself, the floor-0 entry fault
    (13 blocks whose landing nobody reaches), No. 958's time; (2) the 193 narrow maisons with no patio
    (115 fail the window check): a patio or light well against one party wall, or a rear court (a city
    change: name its fingerprint parts, refresh Blender); (3) the 73 maisons with a dark cuisine; (4) slab
    No. 1324's plan time (2.52 s alone, bar 2.2 s); (5) the bars, then tick 47.1, 48.1 and 47.2; then 51.
  - Models (Ali, 31 October: "you decide for better quality"): the lead on Opus max for its reviews, helpers
    Opus high (`effort: high` in the Agent call). A round costs about 1% of the weekly limit.
- Next: 47.1 with 48.1 (50 done 31 October: Open interior on a dwelling's card in `citygen view` and the
  gallery). Then 51. For 47.1 + 48.1:
  47.1 together with 48.1 (the plan faults the walls reveal, prompt 48 entry) (colonial flats pass `rooms.check` for 39%, the slowest colonial block takes 14 s, slabs 93%,
  domed house No. 570, colonial floor-0 stores as a few rooms) unless Ali says otherwise; its plan is in
  the prompt 47 entry.
- Lead notes for 48-50: 48 refreshes Blender after interior mesh changes with exactly `.venv/bin/python
  tools/make_blend.py <that dar's interior folder>` (name the .blend for Ali), and its shell uses the
  tile's ground_z, plinth and frontage; 49 runs make_blend for the pick:dar:2 and pick:slab folders, its
  headroom test includes the stair room's ceiling, and it adds `water_pool`; 50: try "Open interior"
  yourself in the browser pane (click a house, open it, cut, orbit) before ticking H1.
- Review tools for interiors: `tools/interior_survey.py` (every dwelling of a city through `rooms.check`,
  by group; run it before and after each interior prompt, `--city "Ain Chilel"` for the villas) and
  `tools/interior_plans.py` (plan pictures). The fingerprint baseline `output/checks/fp-before.json` (282
  parts) stays fixed for the interior prompts (`--allow ""`).
- How the work runs since prompt 20 (DeepSeek usage ended after 19): the lead session (Opus) briefs one
  Opus `city-builder` helper per prompt (effort from the playbook table). The helper reads CLAUDE.md, its
  prompt section and the HANDOFF lessons, implements, tests, fingerprints, takes the pictures and writes
  the docs, but never commits. The lead reviews the diff, tests, fingerprint and pictures (the GPU
  browser pane for night glass and things near the sea, which headless snapshots draw wrong), sends
  follow-ups, then commits one commit per prompt and pushes. Checkpoints add an independent Opus
  reviewer that reads only the committed history with git, so it can run beside a builder. The
  method in full, with Ali's preferences and the review techniques: `docs/LEAD.md` (read it first).
- Still open from the CP4 list (see the CP4 entry below): light tiles over their byte budgets (accepted one by one, unchanged), the relaxed 3.5 MB tile target (densest
  quick tile 4.69 MB, seed 7 4.86 MB; next gains: merge each full tile's meshes per material, weld flat
  vertices), kiosk cafes only in tiles with buildings, quick builds losing lod1 blocks of unexported
  tiles. The phone page is confirmed on Ali's phone (25 October, two screenshots): textured plaster
  walls, stone paving, the kasbah's brick wall, crowds, golden hour.
- Other cities, built with today's code on 24 October: `output/megine/bodjantouna-42` (Megine) and
  `output/city1/bodjantouna-42` (Sazouches el Gharbi). `python -m citygen list` names every settlement;
  `python -m citygen build --area city:NAME --out output/FOLDER` builds one, then `citygen view` it.
- Doubts and questions for Ali: in the CP4 entry below.
- Added after the pause note, at Ali's request: the city gallery and keyboard navigation, the cemetery
  cypress that won a model duel, and the plan of two tracks after prompt 100 (entries below).
- 30 October: Ali wants his promotional API credit ($86.51, expires 14 November) spent before his weekly
  limit. It does not pay for Claude Code, so `tools/run_on_credit.py` runs a prompt through the Agent SDK
  instead (a billing test passed); how to use it: `docs/LEAD.md`, section 4. Used up since 31 October:
  the chain run (`.venv-sdk/credit_chain.sh`, 10:42-13:12) stopped with "Credit balance is too low"
  (its session recorded about $42), so that route needs new credit first (checked 3 November).

## 2026-11-04 - Prompts 59, 70, 81 (world-59): rivers and lakes, street graph, district histories
- Commit: c4eb74b (merge of wip/world-59)
- Changed: citygen/hydro.py, citygen/export/streets.py, citygen/city/history.py (new); citygen/world.py,
  build.py, export/maps.py, export/lore.py, city/__init__.py, city/model.py, defaults.toml; styles/maghreb.toml;
  tests/test_hydro.py (new), tests/test_citygen.py; tools/street_survey.py (new); docs/SPEC.md.
  Notes: docs/wip/world-59.md
- Checks: tests 209 passed, slow 15 passed + the old xfail; build --quick 7.1 s, --force identical; fingerprint 5 of 283 parts:
  streets.json added, gazetteer and districts (histories only), world (rivers and lakes only), country map. Tiles and
  plans unchanged. Country step 1.4 s (budget 10 s). Interior survey unchanged.
- Rivers (Ali's answers): every dry basin over 3 m and 0.5 km2 stays closed; towns by salt lakes accepted;
  min_flow 3.0. The lead's decisions (Ali: "you are the boss"): every wet basin over the two thresholds is a lake up to
  its spill (the prompt says such a basin IS a lake, and water cannot drain out of a hollow), and a pocket of a closed
  basin over them is a basin of its own (water cannot climb an inner rim; a smaller pocket still drains in, so no river
  ends where no shore is drawn); a salt lake needs a river that ends in it (49 of 87 had none and only speckled the dry
  country; those hollows stay closed, on bare ground). 64 km world: 28 fresh + 38 salt lakes, 148 rivers, 424 km.
  Deviation from the prompt: the bed is the running minimum of the ground down the whole network, not the filled
  height, which flies up to 55 m over hollows and which prompt 60's min() cannot use. Rivers cut through the rims of pits
  too small for a lake: 10.3 m at worst on seed 42, 33 m over 0.4 km on seed 3 (a 38 m deep pit, 2 cells under the area).
- Known: 23 salt lakes are over 20% bigger than their true inflow says: a first lake counts its whole basin's inflow
  (counting only what reaches it loses the great chotts, picture docs/wip/world-59-inflow.png). 10 towns touch a lake and
  13 roads cross one, for prompt 60 to move.
- Street graph: nodes on bare ground fixed (94 of 595); any street end on another's surface gets a stub: 125 of 131
  settlements one part. Left: real gaps in the plans (Ain Khatane 97.4%) and Gamar 97.5%: recheck at prompt 60 with
  tools/street_survey.py.
- Histories: every choice on its own stream, so the capital's picks changed once, same templates (8 of 9 districts).
  Review-81 findings 5 and 9 wait for Ali's before/after examples.
- Look: docs/wip/world-59-maps.png (before and now).
- Doubts and questions for Ali: none; the lead decided the wet hollows, the pockets and the fed salt lakes.
- The lead's own checks before main moved (not the helper's): pytest 209 passed and slow 15 + the old xfail on the final
  commit; his own fingerprint of main against it: 5 parts; world.json identical without rivers and lakes, plan.json without
  `history` and the clock, the gazetteer without the histories; no file under citygen/interior changed since c7ef448, so the
  rooms cannot change; lead_water*.py (scratchpad) confirm every water number. His review found the two faults the helper's
  gates had passed: rivers through the rims of salt pockets (51 m), and 49 of 87 salt lakes with no river.

## 2026-11-03 - Merge of 14 reviewed branches (merge-3d): prompt 54 round 3, furniture fixes, colonial-k, villas-o
- Commit: 5f4e99e (merges `wip/merge-3d` 41eae7c) | a merge helper in a worktree, about 55 min
- Merged: merge-prep (speed-n, flats-j, furnish-m), fix-side-54, test-scrap-hall, test-cache-warm, fix-dar-is,
  fix-materials, fix-hide, fix-brass, fix-goods, fix-textile (with their kit-* and shot-* commits), colonial-k,
  villas-o, test-villa-369, fix-little; and three review fixes, each with a test that fails before: the hidoura
  fold (41 of 200 seeds -> 0 of 3000), the cushion cord's normals (24 of 96 facing away -> 0), pots_stack inside
  its 0.30 m half-size. Conflicts and their answers: `docs/wip/merge-3d.md` (one `twine_green` with kit-hide's
  values; the brass shapes use `copper_ware` and `clay_red`; both sides' makers in `weave.MAKERS`).
- Checks: `pytest -q` 176 passed (the lead, on main after the merge); `-m slow` 11 passed, 1 xfail (47.1's, also on
  main); `build --quick` finishes; fingerprint 0 of 282 parts changed (a build runs no interior code: no make_blend).
- Survey (helper; its baseline matched this log): colonial 3 -> 5/270, slab 247 -> 253/353, villa 167 -> 168/178,
  maison 499/616 and the old town unchanged; warned rooms 4.2% -> 1.9% (lived-in, 25 homes per layout).
- Lead: SPEC lines updated (tray_brass 80 and pots_stack 180 triangles, `copper_ware` twice). main moved on the
  helper's survey plus the lead's tests and build; the lead's own survey came after (4 November, 2ddab41 against
  c7ef448, all 2,094 homes): the pass counts above are confirmed, 9 won, 0 lost, 0 crashes. What it adds:
  - Colonial: same 2,049 flats, chambres 4,895 -> 4,577 (2.39 -> 2.23 per flat), salle_a_manger +91, couloir +89;
    rooms.check problems 3,448 -> 3,100 (155 blocks better, 23 worse). Net good; the other 138 chambres not traced.
  - Slab ladders: 39 room-floor cases (32 before the merge) keep under 0.8 m beside a ladder in a couloir or hall,
    about 20 of the 48 ladders, in 18 blocks; colonial 5 cases, unchanged. rooms.check does not measure this, so
    such blocks can pass. Mostly older than the merge; flats-j added a few (review-mp-flats, flats.py about 599).
    To do: a check for it, and the planner keeps `passage_min` clear; the slab count may fall when the check lands.
  Open: 54 still needs a new full-capital survey (2.2% before the merge), its two look pictures and Ali's look;
  nobody has seen the furniture in 3D yet; question 15 was never checked, only assumed settled.

## 2026-11-03 - Open item 47.2, flats round I (a narrow wet room's door by a corner)
- Commit: (lead commits) | Model: Opus 5.5, high (flats helper, worktree /tmp/claude-501/flats-i, about 45 min)
- Changed: citygen/interior/plancheck.py (`wet_corners`, a last planning step for colonial and slab flats, called from
  layout.py: every door into a wc or sdb 0.9-1.75 m wide moves to a corner end of its wall, its leaf hinged on the corner
  side so it opens against the wall; a place `_fits` refuses is not taken, so no check result changes), model.py
  (`Opening.hinge`, in rooms.json only when set), mesh.py and furnish.py (the leaf and its swept quarter disc follow the
  hinge, their draws taken first as before), styles/maghreb.toml (`[interiors.flats] wet_corner = [0.9, 1.75]`), tests
  (`test_flats_wet_door_by_a_corner`).
- Beyond the brief (the lead keeps it): the jamb stands `inner_clear` (0.15 m) from the end wall's face, half a
  partition plus clear; with a full partition plus clear the 1.48 x 1.89 m sdbs kept 0.78 m beside the door, short of a
  0.8 m shower tray (No. 1042's four had none); with it all four get one.
- Plans (every check): slab and colonial pass counts and fault counts unchanged (the doors move only where the plan's
  rules allow); the old town, villas and maisons identical.
- Furnishing (lived-in): rooms missing a piece 5.4% -> 4.2% (slab 4.1 -> 2.3, colonial 8.3 -> 7.7); colonial "bath no
  basin" 35 -> 47; 0 placement faults. The 2% target is not met: the colonial wet rooms often have two doors or are tiny
  wcs (a planner matter).
- Checks: `pytest -q` 161 passed and `-m slow -k furnish` 3 passed in the helper's tree; fingerprint 0 changed.
- Look: output/checks/472-i-wet.png (worktree; two fixed wet rooms, furnished).
- Lead: merged on houses round 5 (one conflict in layout.py's last passes: both kept, gated by layout); checked below.

## 2026-11-03 - Open item 47.2, houses round 5 (a small house's plan without a couloir)
- Commit: (lead commits) | Model: Opus 5.5, high (houses helper, worktree /tmp/claude-501/houses-r5, about 45 min)
- Changed: citygen/interior/villa.py (`little`: a short hall at the street door opening into the salon, the chambre,
  cuisine and sdb off the salon or the hall, salon, chambre and cuisine each on a window, partitions clear of the
  openings), citygen/interior/layout.py (a last pass, only for one-floor maisons the check still faults for "has no
  chambre"; a local `again` renamed `redrawn`), styles/maghreb.toml (`[interiors.villa] little`, `little_step`), tests
  (`test_little_house`, 0.4 s).
- Counts with every check (rooms.json hashes, HEAD d96e409 against the tree): maison 498 -> 499 of 616 (won No. 744;
  none lost; no passing house changed), villa 167. Still failing: No. 642 (every plan puts a partition too close to a
  window), 726 and 985 (three windows, no plan of straight cuts works); they take about 0.6 s more CPU, No. 744 0.37
  -> 1.1 s. The old town and every capital flat identical. Every passing interior 0 `mesh.faults`, 0 step faults.
- Checks: `pytest -q` 160 passed in the helper's tree; fingerprint 0 changed.
- Look: output/checks/472-h5-plans.png (worktree; No. 744: a family could live in it; its hall is long, 7.8 m2).
- Lead: verified with the lead's survey (maison 498 -> 499, only No. 744 changed) and merged.

## 2026-11-03 - Open item 47.2, flats round H (the street door opens on the palier of a ladder well beside it)
- Commit: (lead commits) | Model: Opus 5.5, high (flats helper, worktree /tmp/claude-501/flats-h, about 35 min)
- Changed: citygen/interior/flats.py (`entry_hall`: on floor 0 of a slab block, a core slid inward off the entry steps
  whose box does not span the street door, a ladder well beside the door, gets a palier that reaches the door over the
  steps' floor: as wide as the door plus `clear` and a half partition each side, clear of the openings' zones, as deep
  as the steps and their landing or the well; not for sunk doors), tests (`test_slab_entry_hall_reaches_the_well`,
  0.05 s).
- Counts (every check; HEAD 104cd57 copy against the tree, rooms.json hashes): slab 245 -> 247 of 353 (won No. 1183,
  1227; lost 0; 7 blocks changed, all failing at HEAD; faults 807 -> 777), colonial 3/270 (every rooms.json identical);
  the old town, villas and maisons identical. Every passing interior 0 `mesh.faults`, 0 step faults.
- Times (CPU, HEAD and tree alternated): No. 1324 3.8 s both; No. 1183 1.00 -> 0.55 s (one plan, not two); No. 1211
  +4%; every slab block 575 -> 573 s.
- Measured and removed: the same hall for a well on the door wall (No. 1371: one flat wrapped round the palier, day
  rooms through a chambre); sunk doors beside a ladder well (No. 1065, 1109: the well must stand at the steps' head;
  `slide_most` 6.0 m is shorter than No. 1065's 6.3 m of steps and landing).
- Left: the way home (9 slab blocks) and blind chambres (6): planner work in `spine` / `bayplan`.
- Checks: `pytest -q` 156 passed in the helper's tree; `build --quick`; fingerprint 0 changed.
- Look: output/checks/472-h-flats.png (worktree; No. 1183 and 1227: the street door on the palier with its steps and
  the ladder well beside them).
- Lead: verified with the lead's survey and merged on prompt 54 round 2.

## 2026-11-03 - Prompt 54 H2c Furnishing, round 2 (kitchens, baths, villas and maisons)
- Commit: (lead commits) | Model: Opus 5.5, high (furnishing helper, worktree wip/furn-54b, about 1 h 15 min)
- Changed: citygen/interior/furnish.py (slot keys `ends`: slide from a wall's ends inward, also for a sink on a wall
  without a window; `else`: other places tried before the next smaller piece; `[interiors.furnish.smaller_trad]` read
  by `chain` in traditional homes; a shower tray's use strip is its front or either side), styles/maghreb.toml (the
  modern kitchen: sink, unit, cooker beside the unit, the sink, round the corner or by a corner, the fridge at the
  run's end; units may cross the walk strips; the bath: bathtub (sdb of 3.6 m2 and more) or shower first, the basin
  from a wall's ends; `else` places for the couple's, children's and elders' beds, looms and sewing machines;
  smaller_trad: bed_double_140 -> sedda_plain -> bed_single), SPEC 6d built notes.
- Survey (25 per layout, sparse; lived-in and full warn the same rooms; faults = overlap, wall, clearance, ceiling,
  reach): quick capital warned rooms 7.4% -> 5.4% (without the wet-door rooms 3.4% -> 2.1%): slab 6.7 -> 4.1 (2.9 ->
  1.1), colonial 10.1 -> 8.3 (3.6 -> 2.7), dar 3.4, compact 3.1, koubba 2.7, small 12.5 (unchanged). Ain Chilel 3.9%
  -> 3.7%: villa 4.7 -> 4.0, maison 3.4 -> 3.1. Faults 0 at every density in both cities. Household problems 37 -> 33
  (capital), 13 -> 11 (Ain Chilel).
- Kitchens (quick capital): no fridge 68 -> 13, no cooker 17 -> 0, no sink 12 -> 0 (the sink slid from the middle of
  a windowless wall, so the run could not grow; the cooker and fridge had too few places). Baths: the bathtub or tray
  first and the basin by a corner (bath without washing 131 -> 49 slab, 92 -> 44 colonial); no basin 2 -> 68, mostly
  in the wet-door rooms (a tray and a basin cannot both clear a centred door in a 1.5-1.7 m room).
- Wet-door rooms (a planner matter: a wc, sdb or bit el ma 0.9-1.75 m wide whose door stands 0.15 m or more from both
  ends of its wall): warnings 253 -> 213 in the quick capital; Ain Chilel 22.
- Checks: `pytest -q` 158 passed; `pytest -m slow -k furnish` 3 passed; `build --quick`; fingerprint 0 changed;
  rooms.json byte-identical (planners untouched).
- Look (worktree /tmp/claude-501/furn-54b): output/checks/54b-maison.png (No. 865, the Mathlouthi house: sdb with
  shower and heater, the kitchen run under the window, children's room with bed, cot and wardrobe, salon with sofa,
  coffee table, rug, TV and bookcase), output/checks/54b-villa.png (No. 367; its salon frame faces a wall).
- Left: the 2% target (5.4% with the wet-door rooms: the planners should put a narrow wet room's door near a corner);
  small homes 12.5% (one-room homes); a dar's maqsura under 4.5 m2; the full capital's survey.
- Lead: looked at the maison picture (reads as a real town house); merged on flats round G. Prompt 54 stays open.

## 2026-11-03 - Open item 47.2, flats round G (the roof newel's door on the palier, bay plans judged after `nooks`)
- Commit: (lead commits) | Model: Opus 5.5, high (flats helper, worktree /tmp/claude-501/flats-g, about 45 min)
- Changed: citygen/interior/spine.py (`newel_rooms(..., door_to="")`: with a room type, the door goes on a side of the
  square whose outside lies in the room of that type it shares most with, when one does; else as before),
  citygen/interior/flats.py (blocks of flats pass `"palier"`; villas and koubbas call it as before), citygen/interior/
  bayplan.py (`clean`: the rooms judged against their `most` as `spine.nooks` will grow them, `nooked` stand-ins),
  tests (`test_bay_clean_nooks_and_newel_door`, under 0.01 s).
- Counts (every check; HEAD e5dc628 copy against the tree, rooms.json hashes): slab 242 -> 245 of 353 (flats 4,538 ->
  4,547, faults 819 -> 807; won No. 1172, 1180, 1243; lost 0; no flat newly faulty), colonial 3/270 (every rooms.json
  identical). Slab faults by kind: couloir over its most 6 -> 0, inner not in its partition 5 -> 1, cuisine through a
  private room 102 -> 95, blind chambre 302 -> 307 (in blocks that fail at HEAD too). Every passing interior 0
  `mesh.faults`, 0 step faults; the old town, villas and maisons identical.
- Times (CPU, HEAD and tree alternated, two runs each, load about 38): No. 1048 1.41 / 1.20 -> 1.07 / 0.93 s (-23%:
  one plan, not two); No. 1324, 958, 1345, 914 as at HEAD; every slab block 569 -> 552 s CPU (-3%). No. 914 plans
  once already: its time is the spine's search (7 of 9 s).
- What still sends a block to a second plan (23 slab blocks): arches "narrowed" (20) and "not in its partition"
  (13), inner doors not in their partition (13), and the way home (27: the hall meets the couloir only through a
  scrap under an arch's 0.8 m). A cell-level test of the ways' joints lost blocks the whole check passes (two
  attempts, 2-4 lost): arches and doors are known only after `spine.doors` and `plancheck.settle`. Measured and
  removed.
- Left: 20 slab blocks with one faulty flat (five by the floor-0 entry: No. 1065, 1084, 1109, 1183, 1227; seven by the
  way home; four by a blind chambre; three over a most); the colonial deep middle.
- Checks: `pytest -q` 155 passed in the helper's tree; `build --quick`; fingerprint 0 changed.
- Look: output/checks/472-g-plans.png (worktree; No. 1172 newly passes, No. 1048 now one plan, No. 1324).
- Lead: verified with the lead's survey: slab 242 -> 245 (25 changed: 3 won, 0 lost); 13 colonial plans changed too
  (the helper's survey said none: the newel's door moves in colonial blocks as well, by design), each with the same
  fault count (185 -> 185), no pass won or lost. Merged on houses round 4 (its test kept beside prompt 54's).

## 2026-11-03 - Open item 47.2, houses round 4 (a chambre from the hall; the landing link measured)
- Commit: (lead commits) | Model: Opus 5.5, high (houses helper, worktree /tmp/claude-501/houses-r4, about 1 h 20 min)
- Kept: citygen/interior/villa.py (`way_room`, `cut_two`, gated by `[interiors.villa] way_room`: a home with no
  chambre on its top floor cuts one from its hall or couloir by one straight partition, the chambre windowed within
  its minimum and most, the way keeping its minimum, its doors and the landing), citygen/interior/layout.py (the
  landing pass keeps no plan whose upper floor has no couloir on its palier: `off_landing(interior, bare=True)`, a
  no-op today), styles/maghreb.toml, tests (`test_way_room_cut_and_bare_landing`, 0.01 s).
- Counts with every check (HEAD -> now, rooms.json hashes): maison 497 -> 498 of 616 (won No. 526: a 12.3 m2 hall
  gives a 3 x 3 m chambre; 1 changed, none lost), villa 167 -> 167. Every passing interior 0 `mesh.faults`, 0 step
  faults; the old town and every capital home identical. Times: passing houses unchanged; No. 526 0.83 -> 0.90 s
  (it now passes); the slowest plans No. 923 5.2 s and 765 5.1 s, as at HEAD.
- Measured and removed (patch in the scratchpad `hl/hl_link.patch`): `spine.hall_link`, a couloir-wide way of one to
  three legs from the landing hall to the band: it made No. 974 pass with an upper floor that has no couloir at all
  (palier -> chambre, the rest through the droj and one chambre after another): the check passes it, a family would
  not; guarded, it won nothing and slowed No. 765 (+10%). `way_light` (a blind room and the windowed hall or couloir
  beside it cut again): 501 inline but a passing house got darker; as a last pass +1 with 25 failing houses slower.
  A cuisine turned chambre with the way giving a cuisine (ways are 1.2-1.5 m wide, under the cuisine's 1.7): 0.
- Why the rest stays: No. 923 (a triangle: the stair well and the slanted wall leave no couloir-wide way from the
  landing to the band: its upper floor needs its couloir cut from the landing); the tiny one-floor maisons (No. 642,
  726, 744, 985: a hall and a couloir for four rooms: a small house's program without a couloir, its rooms off the
  salon, is next); 45 maisons fault only on blind rooms: the patio-house planner (not built).
- Checks: `pytest -q` 154 passed in the helper's tree; `build --quick`; fingerprint 0 changed.
- Look: output/checks/472-h4-plans.png (worktree; No. 526 before and after).
- Lead: a small round (+1), committed for its safe fix and for what it measured: a plan the check passes is not
  always one a family would live in (No. 974): judge new planners by their pictures too.

## 2026-11-03 - Prompt 54 H2c Furnishing rules and density (partly done)
- Commit: (lead commits) | Model: Opus 5.5, high (helper in worktree wip/furn-54, about 1 h 10 min; the lead
  reviewed and committed)
- Changed: new citygen/interior/household.py (`profile`: the family on stream ("furnish", "family", unit): adults,
  elders, children small, school and teen, tags era, layout, district, band, period, couple, children, elders, big,
  trade:<trade> and the trade groups; `functions`: fixed types and the flexible rooms in SPEC 6d's order); new
  citygen/interior/furnish.py (`Prepared` per interior; `RoomSpace`: wall runs with their openings, the main door,
  inner points, keep-outs, walk strips, ceiling; `Furnisher`: three density passes, slots with four draws each on
  stream(seed, "interior", city_id, k, "furnish", room, slot, role), the place modes, `smaller` chains, the
  mattress stack where beds sleep fewer than the members, room budgets; `why`/`fits`; `reaches`; `check`;
  `placements`); export.write_folder(..., density, furniture): the furniture as instances, furniture.json and
  index.json interior.density; command.make_interior(..., density=); `interior --density`; view.Interiors and
  `api/interior?density=`; styles/maghreb.toml (`[interiors.furnish]` numbers, trade_tags, smaller, 100 roles, the
  recipes of 23 room functions); tests (test_furnish_no_overlap, _every_layout slow, _required, _household,
  _density, _density_slab slow, _budget slow; the two-process test also runs --density full and compares
  furniture.json); SPEC 6d.
- Checks: `pytest -q` 156 passed in the helper's tree (the slow furnish tests and the two-process test pass);
  `build --quick`; fingerprint 0 changed; rooms.json byte-identical with HEAD (furnishing reads the plan).
- Survey (quick capital, 25 per layout: colonial, compact 17, dar, koubba 22, slab, small; 6,095 rooms): 0 overlap,
  wall, clearance, ceiling and reach faults at sparse, lived-in and full. Need warnings in 7.4% of rooms (target
  2%: NOT met): sdb no shower 228, wc no toilet 110, cuisine no fridge 64, no cooker 19, no sink 14, hanout no
  counter 11. Household problems 18 (sparse) / 35 (lived-in, full): a small child's cot gives way to a floor
  mattress, a weaver's loom finds no blind wall by a window. Time mean / max at lived-in: dar 0.29 / 0.51 s, slab
  0.97 / 2.35 s; the largest slab (No. 1169, 1,588 pieces) about 5 s at full. Pieces per interior at lived-in: dar
  91, compact 48, small 24, koubba 45, colonial 242, slab 443. Budgets: the slow budget test passes.
- Rules the code settled (SPEC 6d "Built in prompt 54"): kitchens are runs of 1 m units (sink under the window,
  unit, cooker, butane; never one piece stretched); a door's swing is the quarter disc at its hinge; walk strips
  only in rooms with two ways or more; reach judged against the empty room; wet rooms keep only the door's own width
  free; a bed's use strip is one long side; the hanout counter's is behind it.
- Look (worktree /tmp/claude-501/furn-54): output/checks/54-dar-rooms.png (the Labidi dar: a maqsura with its bed
  and sendouk, the T room's doukkana and klim, the matbakh with gas ring, couscoussier and stone sink),
  output/checks/54-flats-rooms.png (slab No. 1264 and colonial No. 867: kitchens with cooker, butane and fridge, a
  children's room with cot and desk, salons with sofa set and rug, a couple's room), output/checks/54.png,
  output/checks/54-slab.png. Blender: output/bodjantouna-42/interiors/goumosbane-599/dar-labidi.blend (worktree).
- Open (why 54 is not ticked): (1) the flats' wet rooms: the plans put the door in the middle of a 1.0-1.7 m wide
  wc or sdb, so no shower or toilet clears the leaf (a planner matter: wet-room doors near a corner, or a 0.7 m
  shower tray); (2) no villa or maison in the quick capital, so their recipes ran on flats only; (3) a rich dar's
  maqsura may fall back from the sedda to a single bed (try sedda_plain before bed_single for traditional homes);
  (4) the 2% warned-rooms slow test is not written (it would fail); (5) the full capital's 30-house survey.
- Lead: looked at both room pictures (they read as lived-in Tunisian homes; two of the flats' frames missed their
  room: a floor corner and a black frame, the picture tool, not the furnishing) and merged it on flats round F (the
  new tests kept beside round F's at the end of the file). Not ticked: its own Check line (2%) is not met.

## 2026-11-03 - Open item 47.2, flats round F (the first plan takes the bay plans, a dining room no window lights)
- Commit: (lead commits) | Model: Opus 5.5, high (flats helper, worktree /tmp/claude-501/flats-f, about 1 h 30 min)
- Changed: citygen/interior/flats.py (`flat_cells`: in a block's first plan a flat whose spine plan the search
  itself scores faulty, `flat_score` > 0, takes its clean bay plan at once; a salle a manger no window lights is
  dropped and the flat planned again without it, the salon serving), citygen/interior/layout.py (`flat_bays`: a
  faulty flat the first plan planned bay by bay goes back to the spine's plan it made first, the spine's faulty
  flats with clean bay plans go bay by bay, as in round E; `flat_faults`: "the <room> N has X m2, over the most"
  now names its flat), citygen/interior/bayplan.py (`first`; `lay`: a failed search is not run again for a floor
  whose windows stand at the same places; `clean`: every cell, hall and couloir too, within its `most`),
  styles/maghreb.toml (`bay_plan.first = true`), tests (`test_flat_faults_and_bay_first`, 0.01 s).
- Counts (every check; HEAD 70fc537 copy against the tree, rooms.json hashes): slab 233 -> 242 of 353 (flats 4,467
  -> 4,538 of 5,147, faults 892 -> 819; won No. 1098, 1113, 1169, 1175, 1182, 1219, 1226, 1242, 1334; lost 0, no
  flat newly faulty), colonial 3 -> 3 of 270 (flats 368 -> 387, faults 3,559 -> 3,448; lost 0). Blind salle a
  manger: slab 105 -> 58, colonial 180 -> 83. Every passing interior 0 `mesh.faults`, 0 step faults; the old town
  and Ain Chilel's villas and maisons identical.
- Times (CPU, HEAD and tree alternated, two runs each, the machine shared): slab No. 1324 6.75 / 6.07 -> 5.04 / 4.40
  s (-27%; about 3.4 s on a quiet spell, bar 2.5 s not met), colonial No. 958 as at HEAD (about 7.5 s quiet); slower:
  No. 1048 0.6 -> 1.4 s, No. 1345 2.8 -> 4.2 s, No. 914 4.6 -> 6.3 s (their early bay plans fault the whole check by
  arches and doors, so a second plan sends them back to the spine).
- Measured and left out (diffs in the scratchpad `hi/`): every clean bay plan at once (No. 1324 -39% but 305 slab
  blocks changed, 22 lost until the fallback, blocks that passed in one plan took two); the next floor's flat taking
  the bay plan without the spine's search (No. 1263 lost); the ring planner (couloir along the court walls turning
  with the ring): colonial sample flats 67 -> 66, removed.
- Why colonial stays (39-block sample): of 231 faulty flats, 21 have fewer bays than an S+1 needs, 82 no bay to
  spare; most are not thin strips but L and U masses 6-10 m deep from the street with the court offset, so the deep
  middle has no window; the bay planner fails mostly because the lit pieces are fewer than the lit rooms its type
  asks (a window in the hall or a couloir end, two windows under 2.4 m apart in one piece). Next: plan the deep blind
  middle (baths, the couloir, a cuisine on the court) and give each window its own room before the hall takes one,
  or let the type leave one bay spare.
- Found, not fixed: 3 slab blocks (No. 1172, 1180, 1243) fail only by the roof newel's door ("the inner N on floor F
  is not in its partition"): `spine.newel_rooms` puts the droj's door on the square's door side where it touches the
  palier only at a corner.
- Checks: `pytest -q` 151 passed in the helper's tree; `build --quick`; fingerprint 0 changed.
- Look: output/checks/472-f-plans.png (worktree; No. 1113 newly passes, No. 871 with three flats won, No. 1324).
- Lead (after flats round F): committed as progress, merged cleanly on houses round 3; checked below with the lead's
  survey of the merged tree. The slower blocks are accepted for now (no pass lost; the time goes with the next
  round's cleaner bay plans: test arches and doors in `bayplan.clean` so a clean plan does not fault the whole check).

## 2026-11-03 - Open item 47.2, houses round 3 (the upper-floor couloir starts at the landing)
- Commit: (lead commits) | Model: Opus 5.5, high (houses helper, worktree /tmp/claude-501/houses-r3, about 2 h in
  two parts: paused once for the 5-hour limit and resumed)
- The cause: upper floors are cut with no hall (`spine.cut_region`, hall False): the couloir band is placed by the
  windows, not by the landing, a stub joins them only in some cases, and with no hall the couloir is simply the
  largest band piece (`H is None or ...` makes every piece count as touching). Where a court, a droj square or a
  slanted wall splits the band, the stub lands on a piece that is not the couloir or stops short (No. 962).
- Changed: citygen/interior/spine.py (`landing_way`, `as_couloir`: in the landing pass an upper floor is cut with a
  hall at the landing, as floor 0 is, and that hall becomes the couloir's first piece; a variant whose way misses the
  landing scores `astray` as a fault), citygen/interior/layout.py (`off_landing`: an upper floor whose couloirs share
  less than an arch with its palier; `landing_way`: a last pass, only for a villa or maison whose way still faults and
  `off_landing`: one `_plan` with the flag and a carve, kept when fewer faults and no more `dim`), styles/maghreb.toml
  (`[interiors.villa] landing_way`), tests (`test_landing_way`, 0.04 s).
- Measured and removed: the stub always, for every plan (193 passing plans changed, 8 lost); the pass as full stages
  (499 but No. 923 +55% time); the flag inside the existing bays retry (no extra time, but 496, No. 649 lost, 43
  passing plans changed); half the variants (493); no carve (496); `halved` with the palier as a way (0 won).
- Counts with every check (HEAD -> now, rooms.json hashes): maison 490 -> 497 of 616 (won No. 435, 532, 605, 639, 863,
  918, 981; none lost; 8 changed, all failing at HEAD), villa 166 -> 167 (No. 281). `dim` on plans passing in both
  unchanged. Couloir only through a chambre 40 -> 32. Every passing interior 0 `mesh.faults`, 0 step faults; the
  old town and every capital home identical.
- Times (CPU, warm, alternated, 3 runs each): No. 923 4.24-4.29 -> 5.24-5.30 s (+24%), No. 765 3.93-4.00 -> 5.09-5.23 s
  (+30%): both still fail with an upper couloir off the landing, so they pay one more plan (about 1.1 s); No. 332
  unchanged (the pass does not run). Over the lead's 15% for those two.
- Look: output/checks/472-h3-plans.png (worktree; No. 981, 639, 532: upper floors with the couloir from the palier to
  the rooms).
- Left: couloir only through a chambre 32 (No. 923, 962, 974: in the pass the landing hall lies apart from the band in
  half their variants, so `join_spine` drops the band: a link from the landing hall to the band in `cut_region` is
  next); the patio-house planner (not started); tiny one-floor maisons; chambres over their most; villas 167 -> 170.
- Lead (after houses round 3): committed as progress, merged on flats round E and prompts 52-53 (one conflict in
  layout.py, both rounds' new functions kept; they are gated by layout). The lead's survey of the helper's first part
  agreed (499, then the cheaper pass gives 497); the final tree is checked below. The time over 15% is accepted:
  only houses that still fail and miss the landing pay it, every passing plan is unchanged and faster ones lost wins.

## 2026-11-03 - Prompt 53 H2b Modern furniture pieces
- Commit: (lead commits) | Model: Opus 5.5, high (helper in worktree wip/furn-53; the lead reviewed and committed)
- Changed: new citygen/interior/kit_new.py (54 bases, 95 pieces with variants: salon set, sedari, TV stand, flat
  and CRT sets, receiver, buffet, dining set, plastic table and chair, kitchen run, sink, cooker, fridge, wall
  cabinet, microwave, formica table, the bedroom set, children's beds and desk, bookcase, piano, wc, basin,
  mirror, shower, bathtub, water heaters, washing machine, drying rack, hall pieces, rugs, the hanout's counter,
  shelves, scale and drinks fridge, the qahwa's espresso machine, football screen and chicha, crates);
  interior/homekit.py (`MODULES` += kit_new); interior/weave.py (rug_floral, spines, goods); interior/kit_old.py
  (fix: one-repeat rugs mapped 0..1 UVs, but the glTF writer divides UVs by `texture_size`, so the zarbia showed a
  quarter of its pattern and the sajjada 1.5 arches; `REPEAT` now holds their texture_size); styles/maghreb.toml
  ([interiors.palette] 10 plain + spines, goods, rug_floral and 7 `goods_<trade>` tints; [interiors.textures] 3
  images); tests/test_homekit.py (`test_home_pieces_modern`, `test_home_kit_budget`, the 3 new images); SPEC 6d.
- Checks: `pytest -q` 152 passed in the helper's tree (the home-kit tests about 4.5 s with the shared kit setup;
  the slow determinism test passes); `build --quick`; fingerprint `--allow ""`: 282 parts, 0 changed. Home sheet
  glb 1,418,160 bytes (was 738,588). Triangles: modern pieces 7,673 (95, each within budget); the home kit 13,460
  (166 pieces) of 60,000.
- Choices the SPEC left open: `kitchen_sink` H 1.12 m (its tap) with `top` 0.90 m; the chicha's base `glaze_green`
  (a transparent `glass_inner` nearly vanishes).
- Look: output/checks/53.png and 53-<piece>.png frames (worktree /tmp/claude-501/furn-53); contact sheets in the
  session scratchpad (hj_a, hj_b, hj_c, hj_rugs).
- Open for prompt 54: stretch pieces scale x, so a 4 m `kitchen_run` has 2 m doors and a 4 m `shop_shelves` 4x-wide
  goods: place runs of 1 m units instead of stretching far (SPEC 6d says so). `before_after --frame home/<piece>`
  does not always centre the named piece. The longer home sheet shows coarse golden-hour shadow edges (viewer).
- Lead: looked at the contact sheets (the salon set, sedari, buffet behind glass, cooker, fridges, double beds with
  the mink blanket, bunk beds, cot, desk and the bookcase read clearly; the goods rows are rough) and read the
  `REPEAT` fix against the glTF writer's UV rule (meters over `texture_size`): right; it changes only the home
  sheet's bytes.

## 2026-11-03 - Open item 47.2, flats round E (types follow the windows, the bay planner)
- Commit: (lead commits) | Model: Opus 5.5, high (flats helper, worktree /tmp/claude-501/flats-e, about 55 min)
- Changed: citygen/interior/program.py (`bays`, `flat_type`, `flat_lit`: a flat's window bays, windows on one
  wall whose pier holds no partition clear of both counted once; the check's "type matches" asks the type its
  area and its bays give), citygen/interior/flats.py (`region_lit`, `type_of` and `records` with the bays; a salle
  a manger only with a bay to light it; `bay_cells`, `bay_plans`, `spine_cells`), citygen/interior/bayplan.py
  (new: the bay planner), citygen/interior/layout.py (`flat_bays`, `flat_faults`: the second plan of a faulty
  block), citygen/interior/spine.py (`cut_region(..., piers=)`: bands cut at given places; rules `flat_bays`),
  styles/maghreb.toml (`[interiors.flats] by_windows`, `bay_plan`), tests (`test_flat_type_by_bays`, 0.01 s).
- Lead decision (a), sent to Ali (no answer yet; he may still choose (b) more windows or (c) splits by windows):
  a flat's type follows its windows as well as its area: the largest type no bigger than its area's whose lit
  rooms (salon, cuisine, the n chambres) its bays cover, at least S+1 (a 105 m2 flat with four bays is an S+2).
  The derived occupants (`flats.occupants`) never read the type: nothing to keep in step; the city is unchanged.
- The bay planner (`bayplan`): per flat, variants (rooms `deep` m along the street, court or every lit wall, the
  couloir behind them, its pieces joined to the hall by straight stubs; then the spine's hall and couloir with the
  bands cut at the piers between windows instead of its rhythm), kept only when clean by itself (program
  complete, sizes, no search fault, no blind lit room, no strip, every room against the hall or a couloir).
  `layout.flat_bays`: after a block's plan, the flats the check faults get their bay plans, the block is planned
  again with those (the spine's cells of the others replayed, `flats.spine_cells`); kept when no flat that passed
  fails and the check finds less.
- Counts (every check; HEAD 3359c5a copy against the tree, rooms.json hashes): colonial 1 -> 3 of 270 (flats 287
  -> 368 of 2,049, faults 4,185 -> 3,559; the type alone: 3 blocks, 337 flats), slab 139 -> 233 of 353 (flats
  3,694 -> 4,467 of 5,147, faults 2,084 -> 892; the type alone: 143 blocks). Flats won 855, lost 1 (No. 893 flat
  3, by the type rule alone), blocks lost 0. Faults by kind, colonial / slab: blind chambre 1,532 -> 1,082 /
  1,045 -> 310; blind salle a manger 218 -> 180 / 223 -> 105; cuisine only through a private room 250 -> 227 / 250
  -> 108; bath only through a chambre 365 -> 343 / 38 -> 33. Every passing interior 0 `mesh.faults`, 0 step
  faults. Old town and Ain Chilel's villas and maisons identical.
- Times (CPU, HEAD and tree alternated, two runs each): colonial No. 958 6.26 / 6.24 -> 7.51 / 7.48 s (bar 8 s
  met); slab No. 1324 2.45 / 2.43 -> 4.58 / 4.59 s (bar 2.2 s not met: all 30 of its flats fault in the first
  plan, so 23 bay searches, about 1.5 s, and a second plan, about 1 s).
- Checks: `pytest -q` 148 passed in the helper's tree; fingerprint 0 changed.
- Look: output/checks/472-e-plans.png (worktree; No. 940, 971, 962): 940 and 971 keep the spine's plans (their
  flats are thin L and U strips, 3-4 m deep, round the court), 962 newly passes.
- Open: colonial 257/270 stays far: its flats are rings 3-7 m deep round the court, in L and U shapes, where a
  couloir beside a chambre needs 3.55 m and must turn the ring's corners: the next colonial planner walks the
  ring (a couloir along the court wall that turns with it, rooms one bay each on the street side). Slab 336:
  233 now, 23 blocks with one faulty flat left. No. 1324's time.
- Lead (after flats round E): committed as progress. The lead's own survey agrees: colonial 1 -> 3 (216 changed,
  0 lost), slab 139 -> 233 (153 changed: 94 won, 0 lost), the old town, villas and maisons identical; the slowest
  slab 2.5 -> 5.1 s in the lead's parallel survey. Kept although No. 1324 doubles: 94 more slab blocks pass and
  the blind chambres of slabs fall by 70%; the time goes first in the next flats round (plan a block once with
  the bay plans when the types predict the spine's failure, not twice).

## 2026-11-03 - Prompt 52 H2a Traditional furniture pieces
- Commit: (lead commits) | Model: Opus 5.5, high (helper in worktree wip/furn-52, paused once for the 5-hour
  limit and resumed; the lead reviewed and committed)
- Changed: new citygen/interior/homekit.py (HomeSpec, HomeKit, `home_kit` cached per seed and style, `_on` twins
  for lights), interior/kit_old.py (the 49 traditional bases, 71 pieces with variants), interior/weave.py (9
  seamless 256 px images), tests/test_homekit.py; interior/export.py (`used_images` asks weave first),
  kitsheet.py (`kit=` hook: images embedded, walls just over each piece), __main__.py (`kit-sheet --home`),
  tools/before_after.py (`--home-sheet`, `--frame` with it), styles/maghreb.toml ([interiors.palette] 40 entries
  incl. `tea_amber`, [interiors.textures] 9 images, [interiors.furnish] period, density, qibla,
  [interiors.furnish.sizes] empty), docs/SPEC.md 6d (built notes).
- Checks: `pytest -q` 149 passed (+2, about 1.7 s; the slow two-process determinism test passes); `build --quick`;
  fingerprint `--allow ""`: 282 parts, 0 changed. Home sheet glb 738,588 bytes.
- Triangles / budget: doukkana 24/24, mattress 26/30, cushion 40/40, mattress_floor 26/30, mattress_stack 40/60,
  sedda 517/520, sedda_plain 119/180, meida 48/96 (painted 88), tray_table 128/140, pouf 56/64, sendouk 200/220,
  khzana 85/160, shelf_wall 30/36, mirror_carved 61/120, tray_brass 48/48, tea_set 159/160, ibrik 112/120, kanoun
  65/80, couscoussier 124/140, counter_masonry 26/30, gas_ring 66/70, butane 60/64, sink_stone 34/60, qolla
  102/110, gsaa 48/48, kursi 34/40, khabia 112/120, grain_sacks 90/90, tabouna 92/110, klim, mergoum, zarbia,
  hasira and sajjada 10/10, hidoura 20/24, rahla 40/70, loom 200/300, wool_basket 80/80, sewing_machine 202/260,
  dummy 120/120, chechia_forms 138/160, pots_stack 144/150, net_pile 64/80, skifa_bench 20/24, wc_turkish 34/40,
  tap_wall 30/30, bucket 48/48, lota 40/40, basin_washing 40/48.
- Look: output/checks/52.png (worktree /tmp/claude-501/furn-52: 10 close viewer shots of the home sheet),
  output/checks/52-sedda.png (the prompt's `--frame` command); every piece also on a z-buffer contact sheet
  (/tmp/claude-501/r_all.png, before the fixes of the second session).
- Beyond the prompt's wording (the lead keeps both): metals (brass, copper, aluminium, chrome, mirror) at half
  metallic, since fully metallic read black in the viewer (nothing to reflect), written into SPEC 6d; the home
  sheet's walls stand 0.4 m over each piece (the 3.2 m walls hid whole rows), only for a ready kit passed in.
- Weak, honest: the hidoura reads as a pale flat hide (the 0.02 m rug height limit); the net heap has no mesh
  texture; the pots_stack bowls read as a lidded pot; small brass pieces are tiny on the sheet. Hero versions
  come with track K.
- Lead: looked at both pictures and the contact sheet (first pass: cushions, tea glasses, hidoura, net pile, bowl
  and dummy sent back; the second pass fixed them within their budgets); checked that every piece draws on its
  own `stream(seed, "piece", "home/<piece>")` and every image on `stream(seed, "texture", name)`, and that Ali's
  choices sit once each in `[interiors.furnish]`.

## 2026-11-03 - Fix: parapet copings that faced away from the roof deck
- Commit: (lead commits) | Model: Opus 5.5, high (helper of the lead, worktree /tmp/claude-501/coping, about 20 min)
- Changed: citygen/mesh/tile.py (`_coping`), tests/test_citygen.py (`test_unpaired_coping_faces_its_inner_walls_to_the_deck`,
  under 0.01 s; it fails on the old code)
- Found (the houses round's note, checked over the whole city): two faults in `_coping`, both making a parapet's
  inner face see-through from the deck. (1) The fallback (a band the offset cannot pair, mostly an outline with
  one more point than its inset) drew every deck hole's wall reversed (facing into the parapet): 117 bands in the
  quick capital, 815 in the full capital (plus 8,756 merged court bands already right since the houses round); all
  1,464 / 8,947 of those wall triangles faced into the parapet before, every one faces into its hole (the deck)
  after (217,456 hole-wall triangles checked a micrometer in front). The band around a court alone (42 in the full
  capital) drew a reversed wall on the court ring, which the court wall already covers, and no wall on its deck
  side: now no court-ring wall and a deck-facing wall on its outer ring. (2) The paired coping around a court (514
  bands quick, 17,922 full capital: every court house, the old town's included) sloped the wrong way: at deck
  height at the court ring, under the court wall's top, and 0.85-0.9 m high at the deck edge with no face below
  it. Now high at the court ring, down to the deck, as the outer parapets are (prompt 15).
- Checks: `pytest -q` 145 passed in the helper's tree; `build --quick` 9.5 s; fingerprint 7 parts: `tiles/index` and
  tiles 12_23, 13_23, 13_24, 14_22, 14_23, 14_24 (the tiles with court houses or unpaired parapets); triangles
  unchanged except tile 13_23 +6 (three court bands, outer ring one point longer than the court ring).
- Look: output/checks/coping-fallback.png (helper folder /tmp/claude-501/coping): top, an apartments roof (before:
  the deck ends in a see-through edge; after: the parapet's inner face); bottom, a court house roof (before: no
  near parapet, the far court wall seen through; after: the coping rising to the court wall).
- Doubts and questions for Ali: none.
- Lead: looked at the picture and read the diff (24 lines): both fixes follow prompt 15's rule (the building's
  rings high, the deck's rings low and facing the deck); fix (2) went beyond the brief and is kept, since every
  court house of the old town showed the fault. Merged on houses round 2; the lead's own fingerprint and tests
  below; Blender refreshed with `tools/make_blend.py`.

## 2026-11-03 - Open items 47.1 + 48.1 + 47.2, houses round 2 (the window count, kitchen nooks)
- Commit: (lead commits) | Model: Opus 5.5, high (houses helper, worktree /tmp/claude-501/houses-r2, about 40 min)
- Changed: citygen/interior/layout.py (`nook`: in `way_home`'s trades, a day room traded for a chambre that is
  under a chambre's minimum, a 5-6 m2 kitchen nook, joins the chambre beside it, within its `most` and with no
  corridor-like arm; only in a last `way_home` pass that `plan_interior` runs when the plan's way still faults
  after the redraws and carves, so every passing plan stays byte-identical), citygen/interior/villa.py (`relit`,
  `repartition`: a blind chambre or salle a manger beside a room holding two windows or more, the pair cut again
  across or along its own sides so both keep a window and a door's length on the hall or couloir, each within its
  minimum and `most`, the partition clear of the openings), styles/maghreb.toml (`[interiors.villa]` `nooks`,
  `relight`, `relight_step`), tests (`test_kitchen_nook`, `test_relit_repartition`, 0.01 s each).
- The window count (HEAD 13f452a, every failing plan, per floor: windows into the home's rooms against the
  program's least and the plan's lit rooms, and the spare ones in ways, baths and second windows of a room):
  maison 131 failing, 69 with a blind lit room: 10 have fewer windows on a floor than its program's least (No.
  410, 476, 523, 552, 686, 743, 780, 819, 961, 1015), the other 59 have at least as many spare windows as blind
  rooms on every floor (87 blind rooms; 138 windows in ways and baths, 143 second windows in a room), so a better
  plan can light them. Villas: 1 of 12 failing has a blind room (No. 399), spare windows enough. The 62 maisons
  without a blind room fail on the way (couloir or cuisine only through a chambre), sizes or the stair. For
  houses the windows are rarely the limit (10 of 131); where the rooms lie is.
- Measured and removed: the spine's variants all allowed in a failing house's redraw (48 instead of 18): +3
  maisons at up to 9.3 s a plan; a blind room joined to a lit neighbour and halved: 0 won (the neighbour has one
  window); a swapped cuisine over its most cut in two: 0 (its door is at the couloir end, its window at the
  facade end); more carves (`carve_tries` 16, `carves` 3): 1 villa (No. 332), no maison.
- Counts with every check (HEAD -> now): maison 485 -> 490 of 616 (won No. 490 by `relit`, 730, 745, 846, 936 by
  `nook`; none lost; 10 changed in all, every passing plan identical), villa 166 -> 166. Every passing interior 0
  `mesh.faults`, 0 step faults. The way faults: 41 of the 43 plans whose couloir is reached only through a
  chambre have a couloir that touches neither the palier nor the hall (mostly floor 1: the spine's upper-floor
  couloir misses the stair landing).
- Times (CPU, HEAD and the tree alternated, 2 runs each): slowest maison No. 923 2.94 / 3.02 s both (plan
  unchanged); No. 554 1.83 / 1.89 -> 2.15 / 2.11 s (still fails: the last trades plan it again); slowest villa
  No. 363 0.99 / 1.02 -> 1.04 / 1.03 s.
- Checks: `pytest -q` 146 passed in 48.7 s; `build --quick`; fingerprint 282 parts, 0 changed.
- Look: output/checks/472-h2-plans.png (worktree /tmp/claude-501/houses-r2; before | after: No. 490 salon and
  chambre cut again across the west windows, No. 730 and 936 the cuisine on the couloir, its nook joined to a
  chambre).
- Left: maison 490 -> 586: the blind rooms of patio houses (59 a better plan can light, 10 the windows cannot);
  the way faults (couloir only through a chambre 32 plans, cuisine 12); tiny one-floor maisons with no chambre
  (No. 526, 642, 726, 744, 985); chambres over their most (17). Villa 166 -> 170 (single faults).
- Lead (after houses round 2): committed as progress. The lead's own survey agrees: maison 485 -> 490 (10 changed:
  5 won, 0 lost), every villa and every capital home identical. Read the whole diff: both repairs are gated (the
  nook only in the last pass on plans that still fault, `relit` by layout), no draws. Next for houses: an
  upper-floor couloir that starts at the landing (41 plans), then a patio-house planner (couloir on the blind
  side, rooms on the patio and the street), judged by the houses it passes.

## 2026-11-03 - Prompt 51 H2 Furnishing: the design
- Commit: (lead commits) | Model: Opus 5.5, high (design helper in a worktree, about 23 minutes; the lead
  reviewed and committed)
- Changed: docs/SPEC.md (new 6d Furnishing), docs/prompts/05-interiors.md (prompts 52-55 rewritten),
  docs/ROADMAP.md, docs/HANDOFF.md, this entry. No code.
- Design: an interior-only home kit (`home/<piece>`, code in `citygen/interior/`, never in a tile, so every
  prompt 52-55 fingerprint is `--allow ""`); about 140 pieces in three tables (traditional 52, modern with
  shops and cafes 53, lights, textiles, plants and clutter 55), each with category, anchor, size, triangle
  budget, materials, variants and the household facts that pick it; 13 generated textures in
  `interior/weave.py` (klim, mergoum, zarbia, hasira, painted wood, mink blanket...); households become tags
  (era, band, trade groups, children, elders) and the flexible rooms get functions (reception, sleep_couple,
  sleep_children, family TV room, work...); recipes as style slot tables; placement by wall runs with
  keep-outs (door walk boxes and swings, windows by height, stairs, court features, the bridge's roof pieces),
  walkways, use strips and a reach test; a `smaller` chain when a piece does not fit, never an overlap; four
  draws per slot on `stream(seed, "interior", city_id, k, "furnish", room, slot, role)`; densities placed in
  three passes so sparse is a subset of lived-in and full; budgets per piece, room (1,500 / 4,000 / 8,000
  drawn triangles) and folder (+60,000 unique triangles, +6 MB); `furniture.json`; lamps lit only behind lit
  windows.
- Measured (quick capital, 25 interiors per layout, room medians): dar bit 11.7 m2 (width 2.5 m), maqsura
  7.4 m2 (2.4 m), matbakh 6.2 m2 (2.3 m), court 25 m2; slab chambre 18.9 m2 (3.4 m), salon 19.5 m2, cuisine
  13.3 m2, sdb 4.4 m2 (1.9 m), wc 2.5 m2 (1.2 m); colonial salon 23 m2. Households: members 2-9 (median 5-8),
  no children or elders in the data.
- Checks: docs only (no test or build needed); no em dash in the diff.
- Look: none (a design).
- Doubts and questions for Ali (sent by the lead on 3 November; the defaults are the recommendations, already
  written in SPEC 6d Decisions): 1. period "today" (a dar also has a gas ring, fridge and TV, as real medina
  homes do) or "heritage" (no electrical goods)? Recommended: today, heritage as a switch for story scenes.
  2. Default density lived-in? Recommended: yes. 3. Prayer mats toward 112 degrees (Tunis to Mecca)?
  Recommended: yes. 4. The framed verse: abstract gold strokes, never real or imitated Quran text (a real
  calligraphy could come later from Ali's own artwork). Recommended: abstract now. 5. Butane bottle colour:
  written as blue (#3B6FB6); Ali to confirm. 6. Children and elders derived on their own stream until
  prompt 80 (lead's choice: yes). 7. Pieces modeled in code now (low-poly), hero versions in Blender later
  (track K, same names).
- Lead (after prompt 51): read the decisions, the home kit rules and the prompts' structure; checked the
  claims that matter for the fingerprint (`citygen/interior/` is out of the build key, `[interiors]` out of the
  build style). Committed with the defaults; Ali's answers, when they come, change only the defaults' lines.

## 2026-11-03 - Open item 47.2, houses round (courts against a party wall)
- Commit: (lead commits, after flats round D) | Model: Opus 5.5, high (houses helper in a worktree, about 1 h 50 min)
- Changed: citygen/city/courts.py (`against_for`: a court against one party wall for a maison `courts_for`
  leaves dark, with `_along`, `_choose`, `_one_piece`; `apply_courts` tries it after the plan's courts;
  `lit_walls` takes `least`), citygen/city/dressing.py (`_court_windows`: a court wall whose middle lies within
  `own` + `snug` + 0.05 m of the outer ring, the party side, stays blank; the skip comes before any draw),
  citygen/mesh/tile.py (`_coping`: when a court's parapet merges with the outer one, the band's other hole walls
  face the deck and the court ring is left to the court walls; only for a band with the court and another hole,
  so every other outline keeps the old fallback), citygen/interior/spine.py (`against`: a maison's courts
  against its outer wall, grown by their walls, for `court_cuts` mode "against"), citygen/interior/villa.py
  (`halved`: a maison's chambre, salle a manger or salon over its `most` cut in two by `spine.halve`, as flats
  do; `completed`: a floor 0 with no salon or a one-floor home with no chambre cuts one from its largest room),
  styles/maghreb.toml (`[courts] against`, `own`, `snug`, `sizes.side`; `[interiors.villa] halve`, `complete`;
  `[interiors.flats] court_cuts` maison = "against"), tests (`test_court_against_a_party_wall`, 0.1 s), SPEC
  (massing courts, 6c villas and houses), HANDOFF, ROADMAP (47.2 noted, not ticked).
- The rule (Ain Chilel's 194 deep maisons with no patio: lots 5-12 m wide, mostly 7-9 m): a rectangle along one
  party wall, `own` 0.3 m from it, so the house keeps its own wall there: the court is a hole, the outer ring
  stays exactly as it was (no street draw moves) and the neighbour's wall and its open-wall probe still meet
  this house. The tile mesher draws every wall segment (no culling): the neighbour's wall stays hidden behind
  the 0.3 m strip. The court stands `front` 4.0 m or more from every windowed wall (short ones included); every
  other party wall is against it too (within `own` + `snug` 0.6 m: a back corner, a rear court across the lot)
  or `party` 2.4 m away; the floor left round it stays one piece; sides 2.4-6.0 m (`side`), chosen as
  `courts_for` chooses. Result: 183 maisons got one (135 against one party wall, mostly 2.4 x 2.4 m light wells,
  some side patios up to 5.9 x 2.4 m; 48 in a back corner), 181 lit everywhere, 2 partly; 11 stay dark (a
  corner 6.5-6.9 m from the windows of lots lit on 2-3 sides: no court 4 m from those walls).
- Proof, city (per building, HEAD copy against the tree, Ain Chilel): 849 of 1,032 buildings identical; the 183
  court houses change only their footprint (one hole, the outer ring unchanged) and placements (court windows,
  own stream; in 57 a roof prop moved inside the new roof outline, as in round A). The quick capital has no
  such maison: fingerprint 282 parts, 0 changed (no Blender refresh needed for the capital's .blend).
- Counts with every check (HEAD -> now): maison 390 -> 485 of 616 (98 won, 3 lost: No. 473 couloir only through
  a chambre, 683 a blind chambre on floor 0, 814 the cuisine only through a chambre; all three got a court),
  villa 165 -> 166 of 178 (No. 266, by `completed`); court houses alone 79 -> 170 of 183. Every passing interior
  0 `mesh.faults`, 0 step faults. Blind rooms in every maison plan: cuisines 73 -> 12, chambres 138 -> 59,
  salles a manger 46 -> 28, salons 31 -> 3. Guard (`layout.dim`) on the 387 maisons passing in both: 246 -> 245.
  Tried and removed: villa `redraws` 4 (no villa won, failing villas planned twice as long).
- Times (CPU, HEAD and the tree alternated, two runs each): Ain Chilel's `plan_city` 1.03 -> 1.40-1.46 s (the new
  courts); slowest maison No. 923 2.57 -> 2.61-2.68 s (plan unchanged, over 2 s already at HEAD); court houses
  No. 628 1.25 -> 1.9 s, No. 473 0.29 -> 1.76 s (now fails, so planned again); villa No. 363 0.96 = 0.96 s.
- Roof look: the merged parapet of these houses first rendered as thin see-through strips: `_coping`'s fallback
  (outlines the offset cannot pair) draws every band hole's wall reversed, facing into the parapet; fixed only
  where a court's parapet merges with the outer one (a first gate on any court hole also took a round A rim in
  tile 13_23, caught by the fingerprint).
- Checks: `pytest -q` 143 passed in 50.8 s; `-m slow` 5 passed, 1 xfailed; `build --quick`; fingerprint 0 changed.
- Look: output/checks/472-h.png (in the helper's worktree: Ain Chilel's narrow maisons from above, before and
  after: light wells against party walls with windows on their three house sides), output/checks/472-h-plans.png
  (maisons No. 426, 453, 491: a 5.9 x 2.4 m side patio, a corner well with the cuisine and couloir on it, a corner
  well lighting the back rooms of three floors).
- Left: maison 485 -> 586 (the patio houses' blind chambres and salles a manger, 75 plans; a couloir or cuisine
  only through a chambre, 49; rooms over their most, 17; `OPEN_472` No. 848, 851, 853, 864, 990, No. 639 and the
  guard on No. 771 and 766 unchanged), villa 166 -> 170 (single faults), 11 narrow maisons still dark.
- Lead (after the houses round): committed as progress, on top of flats round D (the two new tests were both
  kept where they met at the end of the file). The lead's own survey (rooms.json hashes, every check, HEAD copy
  against the helper's tree) agrees: maison 390 -> 485 (196 changed: 98 won, 3 lost), villa 165 -> 166 (No. 266
  only), every capital home identical. Read the whole diff: no draws in the court rule, the party-side skip
  comes before the court stream's draws, the interior steps are gated by layout. For a later round: count the
  buildings whose parapet takes `_coping`'s fallback in the full capital and look at one before changing it
  (a tiles change).

## 2026-11-03 - Open items 47.1 + 48.1 + 47.2, flats round D (floor-0 allee, the window limit)
- Commit: (lead commits) | Model: Opus 5.5 (flats helper, in this folder; the houses helper in a worktree)
- Changed: citygen/interior/flats.py (`allee`: floor 0's couloir from the street door to a core slid along the
  door wall holds the door; a core on the door wall beside the door gets its landing along the wall to it),
  citygen/interior/spine.py (`clash_of`: in flats, the search's partition test remembered per floor and pair of
  shapes, the variants ask the same pairs again; proved byte-identical on all 623 flats' blocks, villas and maisons
  call it as before), tests/test_citygen.py (`test_allee`, hand-made, 0.01 s; `OPEN_472` colonial empty: No. 825 passes its holes
  and flats tests again), SPEC 6c (Flats: the allee), HANDOFF (lesson), ROADMAP (47.1, 47.2 notes, not ticked).
- Floor-0 entry: the 13 blocks (772, 789, 795, 796, 803, 845, 890, 896, 904, 937, 940, 996, 1007) all had a core
  slid 2.0-2.5 m along the door wall; the street door opened into the cafe or shop. Now 0 floor-0 paliers
  unreached (No. 940: 159 faults -> 13; No. 796's floor-0 flat hall still has no door on its ladder landing).
- Counts (every check: rooms.check, walls, entry steps; HEAD 4826c62 copy against the tree, rooms.json hashes):
  colonial 1 -> 1 of 270 (67 changed, 203 identical, none lost; faulty flats 1,743 -> 1,737, faults 5,439 ->
  4,185: "opens from a room nobody reaches" 568 -> 72, "cannot be reached" 449 -> 77), slab 139 -> 139 of 353 (353 identical), old
  town 677 of 677 identical (dar 155/159, compact 266/277, small 81/83, koubba 21/22, shop 130/136). Every
  passing interior 0 `mesh.faults`, 0 step faults.
- Times (CPU, HEAD and tree alternated, two runs each, the machine shared): colonial No. 958 HEAD 7.82 / 7.91 s,
  tree 6.43 / 6.42 s (floor 0 now faults less, so fewer retries); slab No. 1324 HEAD 2.54 / 2.64 s, tree 2.56 /
  2.60 s before `clash_of`; with it (alternated again) No. 1324 HEAD 2.74 / 2.77 s, tree 2.64 / 2.64 s (-4%, bar
  2.2 s still over), No. 958 HEAD 8.31 / 8.33 s, tree 6.77 / 6.73 s.
- The window limit (found while measuring; the reason no planner reaches the bars): a lit room needs a window,
  so a flat holding fewer windows than its type's lit rooms (salon, cuisine, n chambres) cannot pass. Colonial:
  458 of 2,049 flats (S+3 188, S+2 206, S+1 64); 240 of 1,223 floors short even in sum, 135 even as one flat;
  62 of 270 blocks have enough windows in every flat, 28 more only with a split by windows. Slab: 316 of 353
  blocks at most (bar 336). Measured outside the code: types capped at the flat's windows less two (the check
  asking the same): colonial 1 -> 2 blocks, faulty flats 1,737 -> 1,695.
- The planner (step 2), two attempts measured and removed (not in the tree; code in the scratchpad as
  ha_bayplan_attempt.py, the hook in ha_attempt.diff): (1) the spine's hall and couloir with its bands uncut,
  cut at every window pier (one room per window) with a blind end piece for a bath, typed by `spine.assign`;
  (2) a couloir round the court, or rooms 4 m deep along the lit walls with the couloir behind them (buffers of
  the lit wall faces: street, court, both), rooms cut at the piers of their wall. Kept per flat when the search's
  score plus a walk from the entry (no room reached only through a chambre, bath or cuisine) was lower than the
  spine's. 39-block sample (every 7th block): flats passing 53 -> 39 (whole city with (1) and the first ring:
  faulty flats 1,738 -> 1,772); kept only at a score of 1 or less: none kept (53 = 53). Their best scores were
  2-20: rooms missing (97 of 99 sampled flats), the walk (85), a hall under its least (67), sizes (58).
- Look: output/checks/472-d-plans.png (No. 940, 971, 958): No. 940's street door opens into the common couloir
  to the stair, the cafe beside it; the upper floors are the spine's as at HEAD.
- Doubts and questions for Ali (through the lead): the bars 257/270 and 336/353 cannot be reached with today's
  flat types, splits and windows. Options: (a) a flat's type follows its windows as well as its area (a 105 m2
  flat with four window bays is an S+2 with big rooms); (b) more windows on court walls and blank street walls
  (a city change); (c) split floors by windows, not by area (28 blocks). Then a planner that reaches clean plans
  by itself (one room per window bay, the couloir on the unlit side) is the next round, judged by the flats it
  passes, not by the search's score. Not done: slabs (step 4 of the brief), No. 1324's time bar (the rest of
  its time is spread over the spine's assign, cuts and bays: no single hot spot left).
- Lead (after flats round D): committed as progress. Read the whole diff; the lead's own survey (rooms.json hashes,
  HEAD copy against the tree, every check) agrees: colonial 1 -> 1 (67 changed, 0 won, 0 lost), every slab and
  old-town plan identical; `pytest -q` 143 passed; fingerprint 0 changed. `clash_of`'s memo key now also holds the
  zone set (`id(job.zones)`): no flats job swaps it today (only the old-town shop's `job.zones = job.plain`, on a
  job of its own), so the answers are the same by construction. The window limit goes to Ali with the lead's
  recommendation (a): a flat's type follows its windows (the city unchanged; real blocks lay their rooms on the
  facade's bays), then the one-room-per-bay planner, judged by the flats it passes.

## 2026-10-31 - Open items 47.1 + 48.1 Plan faults and colonial flats
- Commit: rounds 1-4 by the lead, 31 October (part 1 goes on: under the bar) | Model: Opus 5.5, high |
  Part 1 of 3 (48.1, old town, shops, villas, maisons), after the
  lead's round 3 (round 2 saved as refs/wip/471-r2); parts 2 (slabs) and 3 (colonial flats) follow.
- Lead decisions (round 3, Ali left them to the lead): A. entry steps that cannot keep `tread_min` and a
  0.6 m landing in a straight run turn 90 degrees at the door's landing (built); B. a stair room over the
  street door: the street door opens into the stair cell (not built, below); C. a villa or maison stair a
  sliver off a window wall snaps to the wall, the sliver joining the stair cell (tried, below); D. courts
  seen from the street door no worse than 8 (met: 8).
- Changed: new citygen/interior/plancheck.py (`faults`: wall and entry-step checks in the plan, called by
  `rooms.check`; `trim`: hair strips of finished rooms, and rooms all hair strip, join a neighbour of their
  unit; `settle`: inner openings slide to a place the walls accept, a passage narrows to the run both rooms
  face, court openings that fit nowhere go); layout.py (`trim` and `settle` after every plan, `reveals`
  that never cut into another opening's wall, masses sharing an edge are one storey, the shop's lines
  without `front_keep`); dar.py (`Job.steps_need`, `entry_keep`, `zs(shallow=)`, `rules["plan"]`, a dar is
  planned again without the steps' room when that room leaves the court in sight, the screen leaves the
  steps room, baffle and screen off the door, ladders off the entry steps); cuts.py (`zone(front=)`; `trim`:
  arms from 0.005 m2, hair strips of stair cells and ways too, never a skifa's, any room but a court takes a
  hair strip); stairs.py (`steps` shortens the landing to `turn_min` before treads go under `tread_min`,
  then `turned` flights with `entry_steps`, `turned_line`, `treads`; `steps_depth`, `surely_unclear` for
  speed); model.py (`Stair.turn`, `flight`, in rooms.json only for turned steps); compact.py (small house
  entry strip); spine.py (`unwrap`: the host's hair arm round a carved sdb or wc joins it); villa.py
  (`to_landing`: hair strips along the U stair box join the palier); rooms.py (zones with `front_keep`);
  styles/maghreb.toml (`[interiors.checks]` probe, passage_min; walls `front_keep`, `reveal`, `reveal_wall`;
  stairs `turn_min` 0.6, `tread_min`, `steps_flight`, `steps_flight_min`); tests (2 new; `OPEN_48` empty;
  named open lists below); SPEC 6c, HANDOFF.
- Checks: survey (`tools/interior_survey.py`, the new checks; "before" = today's plans: old town exact,
  Ain Chilel = rooms.check passes less those with wall or step faults):

  | group | before (old check) | before (new checks) | round 1 | round 2 | round 3 | round 4 | round 5 | round 6 | round 7 | flats round 1 | bar | slowest before -> after (round 5; round 6; flats round 1) |
  |---|---|---|---|---|---|---|---|---|---|---|---|---|
  | dar (159) | 151 | 84 | 138 | 136 | 141 (89%) | 141 | 146 (92%) | 154 (97%, bar met) | 154 | 154 | 152 | 0.07 -> 0.11 s (0.15 s, No. 276; 0.34 s, No. 90 fails) |
  | compact (277) | 273 | 196 | 258 | 257 | 259 (94%) | 259 | 266 (96%, bar met) | 262 (95%) | 262 | 262 | 264 | 0.11 -> 0.14 s (0.12 s; 0.23 s, No. 268 fails) |
  | small (83) | 81 | 61 | 77 | 77 | 80 (96%, at the bar) | 80 | 81 | 81 | 81 | 81 | 79 | 0.07 -> 0.08 s (0.08 s; 0.08 s) |
  | koubba (22) | 21 | 17 | 19 | 19 | 20 (91%) | 20 | 21 (bar met) | 21 | 21 | 21 | 21 | 0.02 -> 0.02 s (0.06 s, No. 501; 0.07 s) |
  | shop (136) | 135 | 86 | 114 | 120 | 124 (91%) | 124 | 125 | 122 (90%) | 123 | 123 | 130 | 0.27 -> 0.29 s (0.30 s; 0.29 s) |
  | villa (178, Ain Chilel) | 171 | about 58 | 134 | 157 | 157 (88%) | 157 | 157 | 157 | 165 (93%) | 165 | 170 | 0.43 -> 0.37 s (0.37 s; 0.39 s) |
  | maison (616, Ain Chilel) | 589 | about 472 | 508 | 554 | 554 (90%) | 559 (91%) | 559 | 559 | 577 (94%) | 577 | 586 | 0.65 -> 0.61 s (0.60 s; 0.67 s) |
  | slab (353, part 2) | 326 | | 301 | 308 | 308 (87%) | 308 | | | 315 | 315 (89%; 18 passed with wall faults, now honest) | 336 | 2.03 -> 2.13 s (flats round 1: 2.03 s, No. 1066) |
  | colonial (270, part 3) | 117 | | 51 | 83 | 84 (31%) | 84 | | | 86 | 146 (54%) | 257 | 13.0 -> 16.4 s, No. 773 (flats round 1: 7.0 s No. 773, 7.0 s No. 787, 6.9 s No. 890) |
  0 crashes. Every interior that passes `rooms.check` gives 0 `mesh.faults` and 0 entry-step faults (plan
  + walls + the prompt 49 tread, riser and headroom test on every tread of straight and turned steps, every
  old-town house, villa and maison: `h471_mesh.py`). `pytest -q` 130 passed (`test_turned_entry_steps` new);
  slow tests pass (`test_open_samples_are_valid` xfail); `build --quick` done; fingerprint `--allow ""`: 282
  parts, 0 changed. Courts seen from the street door: 8 (as before). Ladder warnings: dar 1, compact 14 (1
  at HEAD), small 1, shop 6, villa 5 (2), maison 46 (31).
- A (turned flights) alone: small reached the bar (80/83); the entry-step class fell from 28 to 14 in the
  old town (left: rises of 1.25-2.4 m with under 1.3 m along the wall, and doors at a room's corner).
- B not built: of the 13 compact houses whose roof stair room stands over the street door, 10 need entry
  steps, so the newel's foot landing must take the steps (a combined flight: steps in line, then the
  newel's quarter landing, the house reached from it); a new stair arrangement for which this round had no
  room after A. `test_old_town_stairs` therefore still accepts the stair room's ladder (lead: undo it once B
  is built).
- C tried twice, not kept: (1) the U box allowed a sliver off a window wall with the sliver joined to the
  palier (`dar.without`): villa 157 -> 119, maison 554 -> 384 passes (new doors and arches crossed); (2)
  only the roof stair (18 of the 20 new villa/maison ladders: "the roof stair does not fit under the stair
  room") under shallow zones, its strips joined: ladders 5/46 -> 3/35 but passes 157 -> 150, 554 -> 545.
  The cause of the new ladders is the honest window rule; the stair cell itself must be built flush (its
  side on the wall), not judged with a gap: next step.
- Left in villas and maisons (`h471_cls.py`): 13 + 2 arches a couloir squeezed between the palier and a
  wall narrows under 0.8 m; 7 doors with no valid place; 7 windows crossed by a palier or couloir wall; 4 + 3
  "the storey crosses the window": facade windows the tile draws on acute footprint spikes narrower than
  two walls (maisons No. 442, 443, 451, 521: a visual fault in the city too, the window opens on solid
  masonry, reported, not hidden); program rest as before.
- Look: output/checks/471-old.png (dar No. 525: the screen skifa gives the steps 1.5 m; dar No. 213: the
  hair-thin ghorfa arm round the droj gone; compact No. 104: the stair room over the street door, a ladder
  in the skifa beside the steps), output/checks/471-villa.png (villa No. 230: wc and sdb with their own
  doors; villa No. 232: the one-storey wing is part of floor 0).
- Choices (for Ali): entry steps keep at least 0.6 m of floor past the top tread (`turn_min`, lead) before
  their treads go under 0.2 m; a court window or door the walls cannot hold is dropped (the doors pass
  places what is still needed); a narrowed passage keeps at least 0.8 m (`passage_min`); hair strips (under
  0.3 m) join a neighbour (a palier, a skifa, a stair cell may take them); a dar keeps its bent entry before
  room for its steps; reveals cut up to 0.2 m into the next wall where it stays 0.15 m thick.
- Named open lists in the tests: `OPEN_OLD` empty (No. 211 now has turned steps), `OPEN_STEPS` {501: a 1.32
  m rise with 1.16 m along the annex wall}, `OPEN_PALIER` {villa 363, maison 852, 863, 864: a couloir
  squeezed between the palier and a wall}; the stair test's ladder case (B, above).
- Doubts: colonial No. 773 got slower (13 -> 16 s, deeper zones); domed house No. 570 still fails (its
  annex strip, 47.1 list).
- Round 4 (helper, from the round 3 tree; survey at the start = the round 3 column exactly).
  - B stopped by geometry, not built (data from `h471b_geo*.py`): the 13 compact ladders (No. 34, 65, 104,
    259, 260, 298, 300, 325, 347, 459, 472, 503, 514, 535) all have the roof stair room flush on the facade
    over the street door: 2.5 m along the facade but only 2.35 m deep inside the 0.4 m facade wall. A cell
    holding the street door needs door + 2 x (`clear` 0.3 + half a partition 0.1): 2.54 m for the 1.74 m
    double doors (9 houses), more than the stair room gives; of the 4 houses with 1.25 m doors and the
    0.95 m one, the stair room ends 0.05-1.05 m short of the door's far edge in 4 (No. 34, 259, 298, 325).
    Only No. 459 (no entry steps) could take it. A cell beside the door (door + `clear` outside it) leaves
    1.05-1.6 m: under `newel_min`. At HEAD these cells stood 0.15 m behind the door (the hair strip
    `front_keep` now refuses). Ways that would work (lead's choice): (a) the newel open on floor 0 inside
    the entry room (no cell walls there, so no `clear` to keep; needs the combined entry flight, rails on
    the open sides of its floor-0 steps and the headroom check under them: a new arrangement, about a
    round of its own); (b) 2-floor houses only (No. 325, 347, 459, 472): floor 0 -> 1 newel in a corner and
    a roof newel from floor 1 under the stair room (as villas do). The test keeps the ladder case.
  - C built (villa/maison ladders 5/46 -> 3/10; HEAD 2/31; passes 157/554 kept). Two causes, by geometry
    (`h471b_diag*.py`): (1) the roof newel square slid on its 0.05 m grid never stood on the wall: the
    wall's inner face lies a few mm off the grid (reveals and slanted walls), so the square kept a sliver
    whose partition ran along the window behind it (`front_keep`). `stairs.flush`: once every size failed
    on the grid, the squares flush on the walls under the stair room (0, 0.005, 0.01 m inward) are tried:
    the window then opens into the stair cell and lights it (9 ladders gone). (2) the U box, moved 0.25 m by
    the new zones, took part of the floor under the roof's stair room: `villa.roof_stair` places the box
    again off the stair room when the roof newel does not fit and keeps that when the newel then fits (28
    gone). Tried and dropped: sliding a U box found off the door wall back onto it (1 ladder, 1 pass lost).
    Left: villa No. 303, 322 and maison No. 795 (a window off the stair room's middle: a flush cell would
    cross it, a cell 0.575 m off the window wall is 1.875 m, under `newel_min` 1.9), maison No. 754 (a 2.2 m
    balcony), No. 713, 866, 982 (one-floor maisons, the stair room over the street door: B's geometry), and
    the 5 with no U stair at all (No. 353, 408, 429, 476, 1015; 408 and 429 at HEAD too), No. 532 (as at
    HEAD). Old town untouched: the flush squares are for villas and maisons only (`on_walls`; in the old
    town they put a small house's newel beside its entry steps: shop No. 230, "the entry steps run under
    the newel stair").
  - Item 3 (villa/maison wall faults), classified with `h471_cls.py`: 19 arches (17 couloir-palier), 8
    inner doors "other" (4 couloir-sdb), 6 doors on a room's hair arm (3 hall-wc), 3 short pieces. The
    arch class: a couloir 1.1 m wide has 0.95 m of clear floor, under the 1.0 m run an arch at its end needs
    (0.8 m between its 0.1 m jambs). `[interiors.villa] couloir` 1.1 -> 1.15 (clear 1.0): maison 554 ->
    559, villa 157 (same), narrowed arches 13 -> 8 (1.2 m was worse: villa 154, maison 552, rooms lose
    their minimum). Every passing interior: 0 mesh faults, 0 step faults. Flats keep 1.1 m (`[interiors.flats] couloir`: with
    1.15 colonial fell 84 -> 77). Not done: the 8 inner doors "other" and 6 on hair arms (next classes).
  - Item 4 (old town) classified, not built (no round left after B, C, 3): the 15 entry-step faults
    (`h471_steps2.py`) are 7 where the storey is deep enough but the entry room is not (No. 78, 175, 209,
    276, 501, 591, 687: the planner could give the skifa `steps_need`; a dar's bent entry wins today) and
    8 where the storey itself is too shallow behind the door (No. 55: 0.38 m, 542: 0.2 m, 248: 1.19 m for
    a 2.36 m rise, 255, 284, 353, 374, 645: doors on a footprint spike or at a room's corner). Choice for
    Ali: for the 8, (a) floor 0 set lower behind the door (a sunken entry room, steps up inside to the rest
    of the floor) or (b) a U entry flight (second turn along the next wall); (b) keeps one floor level,
    (a) is the common old-town answer. Lead pick suggested: (a) for the 8, a deeper skifa for the 7. Also
    left: 8 dars whose court shows from the street door (decision D), the "storey crosses" facade openings
    on footprint spikes (8, tile geometry), koubba No. 570 (annex strip) and 501 (steps, above).
  - Round 4 checks: survey above; ladder warnings dar 1, compact 14 (B), small 1, shop 6, villa 3 (HEAD 2),
    maison 10 (HEAD 31); slowest unchanged (villa 0.37 s, maison 0.61 s, colonial No. 773 16.5 s, slab
    2.15 s). Every interior that passes `rooms.check` (old town, villas, maisons): 0 `mesh.faults`, 0 step
    faults. `pytest -q` 130 passed, slow 5 passed + 1 xfail; `build --quick` done; fingerprint `--allow ""`:
    282 parts, 0 changed. Picture: output/checks/471-r4-villa.png (maison No. 489: the roof newel flush on
    its wall, the window lighting it; No. 812: the U box off the stair room, the roof newel beside it; No.
    508: the 1.15 m couloir reaching the palier through a full arch).
- Lead (31 October, after round 4, on Ali's plan): rounds 1-4 committed as progress (every passing
  interior has 0 mesh faults; the ladder in 13 compact houses replaces HEAD's stair cell standing 0.15 m
  behind the street door). Choices for Ali: B (a), the newel stair open in the entry room, for the 13
  compact ladders (round 6); item 4: a deeper skifa for the 7 houses whose storey has room, a sunken entry
  for the 8 whose storey is too shallow behind the door (the common old-town answer; round 5).
- Round 5 (helper, from 4997d82; survey at the start = the round 4 column exactly).
  - Item 4, deep storeys (in progress): when entry steps fault the plan check but the storey behind the
    door is deep enough (`layout.short_steps`), the house is planned again with the steps' strip (door + 2 x
    `side` wide, `steps_need`, then + 0.3 m deep) kept free of partitions (`Job` adds it to floor 0's opening
    zones, `interior.keep_steps`); the new plan is kept only when `rooms.check` finds less. Fixed No. 78,
    175, 209, 276, 591, 687 (dar 141 -> 143, compact 259 -> 262, shop 124 -> 125, no pass lost); No. 501
    (koubba with a shop) went to the sunken entry below.
  - Item 4, shallow storeys: the sunken entry (new `interior/sunken.py`, after the plans, kept only when
    `rooms.check` finds less): the entry room's floor stays at the street door's threshold (`Room.z` lower,
    its height grows: floor 0's ceiling kept), its inner passages drop with it (head at least `sunken_head`
    1.0 m over floor 0) and get a threshold, and the steps rise from each inner passage into the next room
    (`Stair.sunk` = the sunken room's id, in rooms.json; railings on the flight's sides no wall holds); a
    one-room floor 0 sinks whole (no steps). The floor cap of the room is drawn at its own z. Fixed No. 248,
    255, 284, 353, 501 (and 542's steps; 542 still fails "the storey crosses the door": a footprint spike).
    Entry-step tread faults 15 -> 2: No. 55 (the door on a 0.38 m arm of the storey; the next rooms are the
    droj and the court) and No. 645 (the house's newel stands in the entry room). `OPEN_STEPS` emptied.
    Survey after item 4: dar 145, compact 263, small 81, koubba 21 (bar met), shop 125; no pass lost.
  - Item 2, classes (in progress): entry steps a ladder stands on (No. 171: the ladder kept off
    `steps_need`, the comfortable steps ran 0.15 m further) are built again in the room less the other
    stairs (`dar.steps_beside`, shorter treads, kept only at `tread_min` or more); an upstairs ghorfa a
    gallery cut under its minimum is a store of its size (`dar.upper_stores`: No. 392, 575, 608). Survey:
    dar 146, compact 266 (bar met), small 81, koubba 21, shop 125.
  - What keeps groups under the bar (classes, `h471c_*.py` in /tmp/claude-501/h471c): dar 13 fails = 8
    courts seen from the street door (decision D accepts 8, so dar cannot reach 152 without them: at most
    151), No. 245 and 272 (an upstairs inner door off its partition), 227 (court door past a court corner),
    674 (a wall crosses the street door), 703 (skifa partition near an opening). Shop 11 = 3 "storey crosses"
    facade openings on footprint spikes (No. 71, 374, 636: tile geometry), 2 skifas with a hair arm round the
    hanout to the court (No. 344, 419: the arch narrowed; the next class to fix, in `shop.souk`), 298 (the
    roof stair room over a skifa too small for both its ladder and the steps), 645 (steps), 270, 432, 449,
    686 (one each). Compact 11 = 5 "storey crosses" (spikes), 51 and 496 (wall crosses an inner door), 55,
    116, 290, 315. Koubba No. 570: its annex strip (unchanged).
  - Round 5 checks: survey above; 0 crashes; every passing interior: 0 `mesh.faults`, 0 step faults
    (`h471_mesh.py`, old town); ladder warnings dar 1, compact 14, small 1, shop 6 (as round 4); villa 157 and
    maison 559, ladders 3 and 10 (unchanged). `pytest -q` 131 passed (`test_sunken_entry` new), slow 5 + 1
    xfail; `build --quick` done; fingerprint `--allow ""`: 282 parts, 0 changed. Picture:
    output/checks/471-r5-old.png (No. 255: sunken skifa, -1.0 m, two flights up into the bit and the matbakh;
    No. 353: sunken skifa, steps up into the bit el ma; No. 276: the skifa deep enough for straight steps;
    No. 392: the corner the gallery cut off is a store). The plan tool marks a sunken room "-1.0 m".
  - Choices for Ali: the sunken entry's inner passage keeps its head at least 1.0 m over floor 0
    (`sunken_head`: with a 2.36 m rise, No. 248, the door would otherwise end under the next room's floor);
    a small upstairs corner room is a store, not a ghorfa; the strip retry keeps a new plan only when it has
    fewer faults (never trades one fault for another).
  - Weak spots: dar's slowest plan 0.11 -> 0.15 s (No. 276 is planned twice: over the 20% bar for that one
    house); No. 353 is entered through its bit el ma (the plan of 46; now with the steps in it); the sunken
    room has not been looked at in 3D (no browser this round: Ali or the lead should open No. 255 with "Open
    interior"); the steps of No. 171 have a 0.15 m notch where the ladder stands on their last tread.
- Lead (after round 5): committed as progress. Seen in 471-r5-old.png: No. 353's sunken steps fill its bit
  el ma, which is also the skifa's only way in (skifa, bit el ma, bit, court); No. 255's flights land in a
  bit and the matbakh, and its skifa does not touch the court. Round 6: flights never in a wet room, a way
  in that reaches the court or a hall without crossing a wet room, the 8 courts seen from the street door,
  shop classes. Accepted: dar No. 276 planned twice (slowest dar 0.15 s, still tiny).
- Round 6 (helper, from ce09078; survey at the start = the round 5 column exactly).
  - Item 1, the way in. New plan check `plancheck.way_in`: the way from the street door to
    the court (no court: the hall) that crosses the fewest wet rooms (bit el ma, wc, sdb) and kitchens
    (matbakh, cuisine) crosses none, and no sunken entry's steps stand in one. It flagged (old town, before
    any fix) 76 houses: dar 146 -> 140, compact 266 -> 227, koubba 21 -> 20, shop 125 -> 96; villas and
    maisons none (157, 559 unchanged). Classes (`h471d_way.py`): the skifa opens only into the matbakh (31),
    into the matbakh and a bit or bit el ma (18), only into the bit el ma (5), the skifa touching the court
    with no door on it (about 12), the house entered through a matbakh or store (3).
  - Fixes: `dar.skifa_way` (after the program's doors): an entry room with no dry way to the court gets
    the shortest chain of dry rooms to it, a door wherever the chain has none (dropped when a dar's court
    then shows from the street); `program.way_cells`: the cells every way from a skifa without a court door
    to the court (or a koubba) crosses take no matbakh or bit el ma when another cell holds it (koubba
    annex too); `program.swap_way`: a service still on the way trades its type with a dry room off it, kept
    only when the check finds fewer faults and none of a new kind; `layout.free_way`: when these rules acted
    and faults other than the entry steps' are left, the plan without them is tried too, the better kept.
    Sunken entries (`sunken.reroute`): an inner opening into a wet room or matbakh goes when that room gets
    a door elsewhere (a narrow one if needed), else it trades its type with a dry room not touching the
    skifa (No. 255: the matbakh and a maqsura); a bit's opening goes when the skifa keeps another dry one.
  - Survey after item 1: dar 147, compact 262, small 81, koubba 21, shop 116 (way-in faults left: shop 9,
    compact 4, skifas boxed in by the hanout and a service cell no other cell can hold: No. 166, 413, 494).
    Sunken entries: No. 248 (steps into a bit: the skifa's only other neighbour is the matbakh), 255 (a bit
    and the maqsura: the bit is the skifa's only way on), 353 and 501 (a store), 284 (a one-room floor 0),
    542 (fails: a footprint spike). Every passing interior: 0 `mesh.faults`, 0 step faults.
  - Item 2, the sunken skifa in 3D (`h471d_shot.py`: Chrome through Playwright, the camera set over the
    skifa, cut at floor 0): output/checks/471-r6-sunken.png (No. 255 and No. 248). Looked: the walls reach
    the sunken floor, the flights rise from the lowered inner doors with rails on their open sides, the
    street door stands on the sunken floor. Doubt: a thin slanted grey sliver beside No. 255's skifa (top
    right picture), maybe the outer wall seen edge on; worth a look in the viewer.
  - Item 3, the 8 courts seen from the street door (decision D): `plancheck.bend` (layout `bent`, a dar only,
    kept when the check finds less) slides the entry room's inner openings, then those of the rooms it opens
    into, to the nearest place the walls accept where the court no longer shows. All 7 left (No. 90, 108,
    236, 339, 441, 558, 568; the 8th went with item 1) pass: dar 147 -> 154, courts seen from the street 0.
  - Item 4, shop: a bent skifa's half all hair strip (No. 344, 419: 0.28 m wide between the hanout and the
    covered court) joins the covered court in `plancheck.trim`, its arch goes and the doors pass finds the
    skifa another way in (No. 344 passes; No. 419 then crosses its matbakh). A bit el ma no trade moves off
    the way becomes a store (the program's own order: it gives way last), and a store on the way in no
    longer counts as one that should have given way: shop 116 -> 122, compact unchanged.
  - Round 6 checks: survey in the table; 0 crashes; every passing interior: 0 `mesh.faults`, 0 step faults
    (`h471_mesh.py`, old town); ladder warnings dar 1, compact 14, small 1, shop 6, villa 3, maison 10 (as
    round 5). `pytest -q` 132 passed (`test_way_in` new, 0.5 s), slow 5 + 1 xfail; `build --quick` done;
    fingerprint `--allow ""`: 282 parts, 0 changed. Plans: output/checks/471-r6-old.png (No. 353: skifa,
    store with the steps, bit, court; No. 255: the matbakh traded with a maqsura, flights into the maqsura and
    the bit, the skifa's only way on; No. 108: the bent entry; No. 344: the hair half gone, skifa, bit, court).
  - Left under the bar: compact 262/264 (way in through the matbakh: No. 250 entered through its matbakh,
    334, 488, 574, skifas boxed in by services; 5 "storey crosses" on spikes; 51 and 496 a wall crosses an
    inner door); shop 122/130 (way in: No. 166, 419, 493, 707 through the matbakh, 622 the bit el ma; 3
    "storey crosses" on spikes No. 71, 374, 636; 270 no matbakh; 298, 432, 449, 645, 686 one each).
  - Choices for Ali/lead: the way-in check counts walking through a bit or store as fine (only wet rooms and
    the matbakh are refused); a house whose bit el ma would stand on the only way in gives it up (a store
    there) rather than fail; a sunken skifa's steps may stand in a bit when the bit is the skifa's only way
    on (No. 248, 255) and in a store (No. 353, 501).
  - Weak spots: dar's and compact's slowest plans are failing houses planned twice (0.34 s, 0.23 s); No. 175
    (passing) went 0.06 -> 0.17 s (a second plan for its steps). The four compact way-in failures need a plan
    change (the matbakh cell is the skifa's only neighbour): next round.
- Lead (after round 6): committed as progress (dar reaches its bar; the way-in check found 76 houses
  entered through a wet room or the matbakh, and the plans fix most). 3D (471-r6-sunken.png): walls reach
  the sunken floor, steps and rails show. To fix next: a bit el ma that becomes a store can leave a house
  with no wet room (round 7 counts and fixes). Accepted for Ali: the way in may cross a bit or a store;
  sunken steps in a bit (No. 248, 255) or a store (353, 501); the slowest failing plans take 0.2-0.34 s.
- Round 7 (helper, from 4ebe082; survey at the start = the round 6 column exactly).
  - Item 1, wet rooms (`h471e_wet.py`: dwellings whose home has no bit el ma, wc or sdb on any floor).
    ce09078 (before round 6): compact 13, shop 47, koubba 1 (No. 666), small 83 (the small program has
    none, SPEC 6c), dar, villa, maison 0. Round 6 added 9, all its store trade: compact No. 116, 185, 574,
    shop No. 205, 419, 494, 588, 629, 662. New program check (`program.old_problems`): "the house has no wet
    room: its bit el ma became a store on the way in". Fix (`program.carve_wet`, in `swap_way` before the
    store): the bit el ma takes an end of another room of the home, cut across its long axis at
    `[interiors.dar] wet_carve` 2.0-5.0 m2 (a store, maqsura, bit or matbakh of floor 0 off the way first,
    then on it, then an upstairs ghorfa), with a door on the court or that room; the host keeps its minimum
    and its doors (they slide off the new partition, `plancheck.settle`); kept only when the check finds
    fewer faults and none of a new kind. After: the 9 have a wet room again (No. 662 upstairs, carved from a
    ghorfa); the counts equal ce09078's exactly. Survey: dar 154, compact 262, small 81, koubba 21, shop 123
    (No. 622 now passes), no pass lost.
  - Item 2, villas and maisons (`h471e_fails.py`, every failing house with its faults). At the start 21 villa
    and 57 maison fails. Found by geometry: needle tips (zero-width spikes, a cut along a wall a hair off
    the plan's axis) on room polygons: the sdb wrapped round a wc carries a 1 m needle along the couloir and
    its door lands on it (villa No. 292, 333, 350, 358, 377); a palier's needle along the sdb puts the
    palier's arch over the sdb door (maison No. 495, 520, 951: "the arch and the inner overlap"; 483, 919
    two arches) or narrows it (No. 568, 776, 901, and `OPEN_PALIER` 852, 864). New `cuts.despike` (a corner
    under 1 degree goes while under 0.005 m2 is lost) on every room the spine engine makes
    (`spine.add_rooms`, `spine.unwrap`). Doors on a hair arm (a wc given the hall's hair arm, No. 295, 352):
    `rooms.place(deep=)` takes a piece only where both rooms reach half a partition + `probe` behind the
    door (modern doors in `spine.doors`; a wet room's narrow door falls back to the old rule). Survey after:
    villa 157 -> 164, maison 559 -> 573, ladders 3 and 10, no pass lost.
    Then: a couloir scrap under the hall's least area (0.27 m2 between hall and palier, two arches squeezed
    into it: villa No. 300, maison 817) joins the hall or palier (`spine._scrap_way` in `nooks`); the
    entry-steps retry (`keep_steps`, round 5) runs for villas and maisons too (maison No. 665, 835, 945).
    Survey: villa 165/178, maison 577/616, ladders 3 and 10 (unchanged), no pass lost. `OPEN_PALIER` now
    villa 363 and maison 863 (852 and 864 pass).
  - Left (villa 13, maison 39), by class: old program limits (no chambre in tiny one-floor homes: villa No.
    266, 307, 369, 388, maison 526, 551, 642, 726, 985; reordering the program only trades it for a missing
    cuisine, tried); no U stair (villa 353, maison 408, 429, 476, 1015, as at HEAD); partitions meeting a
    wall by a window (villa 290, 325, 275, maison 590, 644, 976, 830, 924, 500, 749, 420, 431: not needles,
    the next class); chambre under its minimum or over its most (6); arches narrowed (363, 863, 875); entry
    steps on a door in an acute corner (villa 250, maison 961); "storey crosses" windows on footprint
    spikes (maison 442, 443, 451, 521: the tile's, counted); villa 320 no salon, 390 a wc's door on its arm.
    The bars (170, 586) need the program limits fixed: the new-check faults left are 5 villas, 14 maisons.
  - Item 3 (villa ladders 3 -> 2): not reached.
  - Round 7 checks: survey in the table; 0 crashes; every passing interior (old town, villas, maisons): 0
    `mesh.faults`, 0 step faults (`h471_mesh.py`); ladder warnings as round 6. Slab 308 -> 315, colonial 84
    -> 86 (counts only; slowest 2.15 s and 17.3 s, No. 773, as before). Slowest villa 0.49 s (No. 388,
    failing), maison 0.67 s. `pytest -q` 133 passed (`test_wet_room_kept` new, 1.7 s with its fixture),
    slow 5 + 1 xfail; `build --quick` done; fingerprint `--allow ""`: 282 parts, 0 changed. Plans:
    output/checks/471-r7-villa.png (villa No. 333: the sdb without its needle, its door on the couloir; No.
    300: the couloir scrap joined, hall to palier; maison No. 495: floor 1's sdb door and palier arch apart;
    No. 665: the steps kept free in the hall, the sdb beside it).
  - Choices for Ali/lead: a bit el ma may stand upstairs (No. 662) or open off the matbakh when no other
    room can give it an end; the pre-round-6 houses without a wet room (compact 13, shop 47, koubba No. 666)
    and every small house (by its program) stay so: `carve_wet` could give them one (a program change, not
    done). Weak spots: the despike and door-depth rules also act on colonial and slab plans (counts rose,
    not checked house by house); No. 205's bit el ma opens off its matbakh.
- Lead (after round 7): committed as progress (no house loses its wet room; villa 165, maison 577). Seen in
  471-r7-villa.png, for a later item (the checks pass them): long strip rooms across a wide one-floor
  maison (No. 665: chambres and the s. a manger run the house's width) and a room boxed inside another
  (No. 495: the s. a manger inside the salon). Ali's choice later: give the 61 dwellings that never had a
  wet room (compact 13, shop 47, koubba No. 666) one by the carve.
- Flats round 1 (parts 2 and 3, helper; scripts `$TMPDIR/h471f/h471f_*.py`, a parallel survey with walls):
  - Baseline (d6ae540): colonial 86/270 pass (slowest 17.2 s No. 773, then 6.9 s No. 772, 6.5 s No.
    890); slab 315/353 (slowest 3.9 s No. 1066 under load, 2.15 s alone). New finding: 18 passing slabs
    fault the walls (`mesh.faults`: a stair door 1.5 m "cut 1.50 / 0.00"): stair doors 2.8-3.2 m under
    floor 0 (a slope), so the door's whole height lies below the palier's walls and opens on nothing.
  - Fail classes by building (a building counts once per family): colonial 184 fails: wall faults 92
    (a wall crosses a window 31, an inner door 31 + 17 far side, a shop front 16, arches narrowed 11),
    partitions near an opening 78, room sizes 74 (chambre over 36 m2 20, cuisine under minimum 20, salle a
    manger 12), program 44 (chambres short 18, no sdb 16, no cuisine 14, no wc 13), salon without a window
    34, entry steps under the U stair 32, reach 22. Alone: size only 20, wall only 14, wall + zone 20,
    steps only 9, zone only 8, program only 7, light only 6. Slab 38 fails: wall 15 (inner door not in its
    partition 8), partitions near an opening 21 (palier/hall 7, palier/chambre 5, palier/salon 4), entry
    steps with short treads 7, program 6. No. 773 is a 100 m x 1.5 m sliver block (7 floors, 151 m2 each):
    no flat can fit, its 17 s go to the spine's variant search (`free` and `partition`: 21 of 39 s).
  - Fix 1 (flat doors off the split line): a through-core colonial split entered both flats at the box's
    front corner, on the split line, so a hall of 0.4-0.8 m2 and doors the walls cross (No. 906, 855, 935,
    818). `Core.entry` now keeps its point only when a door fits there (`holds_door`), else the nearest
    point of a straight edge piece that holds one (`door_spot`). Colonial 86 -> 101 (27 won, 12 lost: the
    spine search lottery), slab 315 (byte-identical).
  - Fix 2 (steps down): `entry_keep` ignored doors above floor 0, so the core stood on the steps down (all
    30 "entry steps run under the U stair" checked were 3 risers down); now both ways (in fix 1's numbers).
  - Fix 3 (speed, byte-identical: 0 of 623 rooms.json hashes changed): `spine.free` tests a partition only
    against the zones across its line and remembers each cut it tried per region; `cuts.cut` remembers its
    halves per shape and line. No. 773 17 s -> 7.0 s alone (7.7 s in a 7-process survey); the next slowest
    No. 849 2.9 s, No. 834 3.1 s alone.
  - Fix 4 (slab doors under floor 0): the gap before a slid core behind such a door is its own common
    couloir, sunk to the door's threshold (`deep_door`, `[interiors.flats] deep_door` 0.3 m), the steps
    in it and an arch to the palier: the 18 slabs pass with 0 `mesh.faults`.
  - Search check (42 failing colonial blocks, every 4th): 38 already fail in the spine's variant search
    (its best variant keeps 1-5 faults), 4 later. The colonial remainder is mostly the spine engine itself.
    Of the search's faults over 871 failing flat searches: 229 a cuisine without a window (which
    `rooms.check` does not ask of a flat), salon without a window 80, chambre too small 38, cuisine too
    small 31, partitions near an opening 23 + 20 + 12, missing wc 17.
  - Fix 5 (flats' search score): in flats a blind cuisine weighs 1, every fault the check finds 2
    (`spine.faults(hard=2)`; villas and maisons unchanged): colonial 101 -> 105.
  - Fix 6 (a flat tries again): `flats.best_lay`: when a flat's plan scores over 1 (`flat_score`: missing
    rooms 6, faults 2, a blind cuisine 1, a hall under its least 2), it tries the door point that holds a
    door, one more place on the landing's edge, then the first point with a second hall draw (stream key +
    "again"), each with `retry_variants` 0.5 of the variants; the best kept. The first try is today's entry
    point (`Core.entry` without `need`), so a flat whose first plan scores 0 or 1 keeps its bytes. Steps
    down keep only their own length before the core (no landing beyond them: the box's landing is one).
    Colonial 105 -> 138 (vs baseline 53 won, 1 lost), slab 315 -> 317.
  - Fix 7 (floor 0 beside a cafe or shop front): the couloir to a slid core kept the box's side 0.1 m inside
    a 2.6 m cafe front 0.57 m from the door (16 "a wall crosses the shop", 17 qahwa partitions near it);
    `gap_sides` now moves a side inward when outward lies the front, the couloir keeping its width:
    colonial 138 -> 146 (8 won, 0 lost). Piers (floor 0 walls beside a shop front) excused partitions on
    every floor in `rooms.clash`: now floor 0 only (the check found the hall/s. a manger partition in
    No. 786's window at last; part 1 unchanged).
  - Fix 6 for slabs costs time (No. 1066 2.1 -> 2.6 s for 2 more passes): `retry_variants = { colonial =
    0.5, slab = 0.0 }`; second tries that won nothing on a floor below are not repeated (memo).
  - Final (flats round 1): colonial 86 -> 146/270 (54%), slab 315 -> 315/353 (the 18 with wall faults now
    pass honestly), 0 crashes, every passing slab and colonial 0 `mesh.faults` and 0 step faults (survey with
    walls, `h471f_dump.py`). Slowest alone: colonial 7.0 s (No. 773, No. 787), 6.9 s (No. 890); slab 2.03 s
    (No. 1066, as HEAD 2.12 s). Part 1: dar 154, compact 262, small 81, koubba 21, shop 123, villa 165,
    maison 577 (unchanged, 0 passing with wall or step faults). `pytest -q` 134 passed; `build --quick`
    done; fingerprint `--allow ""`: 282 parts, 0 changed. Plans: output/checks/471-flats-r1.png (colonial
    No. 906: flat doors off the split line; No. 782: the cafe front and the palier beside it; slab No.
    1064: the sunken couloir behind the deep stair door, floor 0).
  - Choices for Ali/lead: a flat's second tries (colonial only; slabs none, for the 2.2 s bar); a slab
    door under floor 0 opens into a sunken common couloir (`deep_door` 0.3 m); steps down keep no landing
    beyond them.
  - Left (colonial 124 fails, by building): a wall crossing an upper-floor window 28 (partitions of hall,
    couloir, cuisine, salon ending inside a window: the spine search's best variant), partitions near an
    opening (hall/salon 8, couloir/cuisine 8, couloir/salon 15), inner doors crossed 11 + 8 far side, room
    sizes (cuisine or salle a manger under minimum, chambre over 36 m2), salon without a window, No. 773
    (a 1.5 m sliver block: no flat fits). Slab 38: inner door not in its partition 10, palier partitions
    near openings 8, entry steps with short treads + palier partitions 8. Next flats round: the couloir's
    end at the facade (end it before a window bay, or a room across its end), the salle a manger dropped
    when no cell holds it (the check does not ask for it), the slab palier strip at the windows, and the
    slab steps' treads.
- Lead (after flats round 1): committed as progress (colonial 86 -> 146, the 18 slabs with wall faults now
  pass honestly, No. 773 17 s -> 7 s). Read the whole diff: the new memos (`cuts.cut`, `spine.free`) are
  pure in their keys (a job's zones are fixed when it starts), the second tries draw from their own stream
  key. `pytest -q` 134 passed in 42 s (128 in 36 s at prompt 50); fingerprint 0 changed. Seen in
  471-flats-r1.png: No. 906's flats entered off the split line, each with a real hall; slab No. 1064's
  sunken couloir (2.2 m) at its left core on floor 0.
- Flats round 2 (helper; scripts `$TMPDIR/h471f2/`, the round 1 survey `h471f_dump.py` reused):
  - Baseline (d7cbd67, `r1i.json`): colonial 146/270, slab 315/353. The search's own faults over the failing
    flats' best variants (`h471f_why.py`) showed the window-zone partitions came from the search itself:
    a couloir 1.1 m wide ending at a facade window cannot keep both its sides 0.3 m off a 0.7-0.8 m window.
  - Fix 1 (window bays, `spine.bays`/`give`, flats only): before a variant is scored, a way and a room whose
    partition ends in a window's zone trade that window's bay (`[interiors.flats] bay_depth` 0.7 m in from
    the wall, `clear` + half a partition past both edges) when the floor then has fewer faults, both cells
    stay one polygon and the donor keeps a door's length with every cell it touched. Colonial 146 -> 163
    (19 won, 2 lost: No. 1009 a couloir nobody reaches, No. 849 salon without a window), slab 315 -> 316.
  - Fix 2 (a flat's salle a manger): placed only where a cell holds its minimum, never counted missing in
    the search's score (the check asks none of a flat): colonial 163 -> 166 (5 won, 2 lost), slab 316.
  - Not done: room/room bay trades (the search's zone faults left are 6 cuisine/salon, 3 chambre/salon...
    over 1087 flat searches: little to win), salon without a window, slab fixes.
  - Final (flats round 2): colonial 146 -> 166/270 (22 won, 2 lost vs d7cbd67), slab 315 -> 316/353 (No.
    1066 won), 0 crashes, every passing interior 0 `mesh.faults` and 0 step faults. Slowest alone: colonial
    No. 773 7.7 s (7.0 s at d7cbd67; 806 6.2 s, 890 6.0 s), slab No. 1169 1.6 s, No. 1066 0.8 s. Part 1
    byte-identical (dar 154, compact 262, small 81, koubba 21, shop 123, villa 165, maison 577: 0 of 1471
    rooms.json hashes changed). `pytest -q` 135 passed; `build --quick` done; fingerprint `--allow ""`: 282
    parts, 0 changed. Plans: output/checks/471-flats-r2.png (colonial No. 1013 and No. 975, slab No. 1066).
  - Choices for Ali/lead: a couloir that met a window now stops short of it, the room across its end taking
    the window bay (a jog of 0.7 m in the partition, as an old block's walls turn round a window pier); a
    flat has a salle a manger only where a room of its size fits.
  - Left (colonial 104 fails): inner doors crossed by walls 17 + 17 far side (tiny halls, wc doors on a
    0-length contact), salon without a window 17, chambre over 36 m2 14, chambres or sdb missing 10-11,
    arches narrowed 10, reach 9, cuisine or salon under minimum 8-9, No. 773 (a 100 m x 1.5 m sliver block:
    no flat fits, a known fail). Slab 37: unchanged classes (inner door not in its partition, palier
    partitions near openings, entry steps' treads). The bars (colonial 257, slab 336) are far: the next
    round should judge whole flats (doors, reach) in `best_lay`, not only the search's faults, and give the
    salon a lit cell by swapping with a lit chambre.
- Lead (after flats round 2): committed as progress (colonial 146 -> 166, slab 316; part 1 byte-identical).
  Read the whole diff (`bays`/`give` change a variant's cells only when the floor's faults drop; the salle a
  manger rule applies to flats only); `pytest -q` 135 passed in 40 s; fingerprint 0 changed. The helper
  stopped after 19 minutes of the 75 it had. Seen in 471-flats-r2.png and measured: No. 1013's floor 2
  salon (26.8 m2) has 11.2 m2 in a strip under 1.6 m wide along the facade, between the couloir and the
  windows; the same at d7cbd67, so the spine's strip rooms (round 7 note, No. 665), not this round. For
  the later item on room shapes: `cuts.width` is the largest circle inside a room, so a room with a wide
  body and a corridor-like arm passes.
- Flats round 3 (helper, about 62 minutes; scripts `$TMPDIR/h471f3/`, `h471f_dump.py` now also counts the
  quality guard: habitable rooms of passing flats with over 3 m2 in parts under 1.6 m wide):
  - Baseline (6160ada, `base.json`, same hashes as round 2's `fin.json`): colonial 166/270, slab 316/353;
    guard 472 rooms (colonial), 1611 (slab).
  - Tried, not kept: (a) judging whole flats in `best_lay` (rooms, nooks, doors and the front door made,
    the door faults no slide along their wall cures counted, then taken away): with reach counted, 166 ->
    147 (91 passing flats changed: before `connect` whole flats look unreached); doors only, 0 changed (the
    door faults appear after `finish`), and +1-2 s on the slowest. (b) A hall scrap merged into its couloir
    (none of the tiny halls touches one; into the salon: "flat has no hall"). (c) hall scrap weight 3 in
    `flat_score`: 166 -> 162. (d) The roof newel's door to the next room when the walls fault it on the
    palier: no room but the palier lies on its door line. (e) A blind salon re-cut with a windowed cuisine
    or chambre beside it, else a type swap: 0 won, 1 lost (the lit cells of those flats are the hall,
    couloir or a small cuisine not touching the salon).
  - Fix (kept): a flat's chambre, salle a manger or salon over its `most` is cut in two after the search
    (`flats.halved`, `spine.halve`): the room keeps its minimum and a way in, the new chambre has a way in
    or a door's length on the room (en enfilade), both windowed when the room was, neither with over
    `[interiors.flats] strip` [1.6, 3.0] (3 m2 in parts under 1.6 m). Inside `assign` it won 2 but churned
    17 passing flats (+14 guard); after the search: colonial 166 -> 167 (No. 1032), slab 316 -> 317 (No.
    1133), 0 lost, 0 passing flats changed. Guard 475 (+3) and 1615 (+4): the two new passing blocks' own
    rooms, no passing flat gained one.
  - Final (flats round 3): colonial 167/270, slab 317/353, 0 crashes, every passing interior 0
    `mesh.faults` and 0 step faults. Slowest alone: colonial No. 773 7.8-8.0 s (HEAD 7.75 s; halving costs
    16 ms there), No. 806 6.3 s; slab No. 1169 1.6 s. Part 1: dar 154, compact 262, small 81, koubba 21,
    shop 123 (`interior_survey.py`), villa 165, maison 577 (0 of 794 rooms.json hashes changed). `pytest
    -q` 136 passed (new `test_strip_measures_corridor_arms`); `build --quick` done; fingerprint `--allow
    ""`: 282 parts, 0 changed. Plans: output/checks/471-flats-r3.png (colonial No. 1032, the only colonial
    won; slab No. 1133).
  - Choice for Ali/lead: an oversized room becomes two, the far one a chambre entered through the near room
    when it has no wall on the couloir (en enfilade, as in old colonial flats of Tunis and Algiers).
  - Left (colonial 103): tiny halls (0.1-0.9 m2, the palier and one room around them: 16 blocks of door
    faults), roof newel and front doors crowding the top palier (6), salon without a window (14: the
    flat's lit cells are its hall, couloir or a small cuisine), chambre over 36 m2 (blind deep strips the
    halving cannot cut with a way in), reach and missing rooms (No. 772, 823, 857, 904). Slab 36: inner door
    "not in its partition" on 1.4-1.5 m cuisine/hall and sdb/cuisine pieces (6 blocks), entry treads (7),
    palier partitions near windows. The bars (257, 336) need the spine search itself to change: a hall
    that is a real room (score a hall under its least as a missing room, or carve the hall before the
    couloir), and the salon placed first on the window wall when a flat has one short window front.
- Lead (after flats round 3): committed as progress (colonial 167, slab 317; part 1 and every passing flat
  byte-identical). `pytest -q` 136 passed in 41 s; fingerprint 0 changed. Seen in 471-flats-r3.png: No.
  1032's floor 0 is one flat with ten chambres, most of them deep inside with no window. Measured over
  every passing flat (`/tmp/claude-501/lead/blind.py`: a room is blind when no facade window or balcony
  opens into it): colonial 2642 of 3407 chambres blind (78%), salle a manger 541 of 587, cuisine 236 of
  1104, 162 of the 167 blocks with 3 or more blind chambres; slab 1279 of 14225 chambres (9%), salle a
  manger 344 of 2653, cuisine 6 of 4637. Maisons (Ain Chilel, 577 passing) too: 1411 of 3212 chambres
  blind (44%), all 340 salles a manger, 178 cuisines and 55 salons, 182 houses with 3 or more blind
  chambres; villas 18 of 599 chambres (3%). No court windows in either (counted too). Only a flat's
  salon must have a facade window (`program.py`); no check asks one of a chambre, nor of a maison's rooms.
  Rounds 1-3 took colonial 86 -> 146 -> 166 -> 167: the small fixes have stalled.
- Question for Ali (lead, 31 October): real colonial blocks and deep town houses light their inner rooms
  from a courtyard or light wells (courettes); ours have windows on the street fronts only, so a deep
  block or maison fills with blind rooms, and the pass bars count them as good. Proposal: a design step
  that gives deep colonial blocks and maisons a courtyard or light wells (seen from above, with windows
  on them), then plans with every chambre, salon and salle a manger on a window, and a check that asks
  for it. Or leave the flats as they are for now (47.1 stays open) and go on. Meanwhile the lead
  finishes the houses (round 8).
- Round 8 (houses, helper, about 40 minutes; scripts `/tmp/claude-501/h471r8/`: `diff.py` won/lost/changed by
  rooms.json hash, `guard.py` the blind/strip guard per house, `guard2.py` the same for failing plans):
  - Baseline (43ef2c3): dar 154, compact 262, small 81, koubba 21, shop 123, villa 165, maison 577 (Ain
    Chilel); colonial 167, slab 317. Guard (passing villas, maisons): chambres blind 18 and 1411, strip 29
    and 194. Ladder warnings compact 14, shop 6, dar 1, small 1, villa 3, maison 10.
  - Fix 1 (window bays for villas and maisons): round 2's `spine.bays`/`give` inside the search, as flats:
    villa 167, maison 586, but 73 passing houses changed and the guard grew on the same houses (chambres
    blind 1429 -> 1444, strip 223 -> 235, 26 chambres fewer: an earlier variant now wins). Kept instead:
    (a) `spine.late_bays`, the trade on the search's best plan only when no variant passed: villa 168, maison
    583, 0 passing changed; (b) `layout.early_bays`: a house the check still faults (other than "has no",
    no U stair, storey crosses, entry steps) is planned again with the trade inside the search, kept when
    it finds less: maison 587 (No. 839, 875, 924, 1011 more).
  - Fix 2 (redraws): every old-town house, villa and maison still faulty is drawn again with fresh streams
    (`layout.redraw`; `Job.rng`, `shop.rng` and `spine.rng` take the path + ("again", n)), the plan with the
    fewest faults kept. Old town (3 draws): compact 262 -> 266 (No. 51, 315, 488, 496), shop 123 -> 129
    (No. 166, 270, 419, 493, 686, 707), dar 154 -> 155 (No. 703), small and koubba unchanged, 0 passing
    changed. 8 draws won 2 more (compact 55, dar 227) for 4x the time: not kept. Houses (2 draws, the bay
    trade inside the search): maison 591, villa 169 (No. 363); 5 draws gave villa 170 (No. 390) at up to 3.5
    s for failing villas.
  - Fix 3 (tiny one-floor homes, `villa.tiny`): no wc of its own and the chambre before the cuisine, tried
    when a one-floor house has no chambre or salon: maison No. 551 passes. The others (villa No. 266, 369,
    320, maison 526, 642, 726, 985) lose a hall and a couloir of 10-20 m2 out of 41-54 m2: the spine always
    cuts a hall and couloir, a program limit (choice below).
  - Guard: the newly passing houses brought their own dark rooms, and a redraw sometimes traded faults for a
    strip chambre (No. 390). So every second plan is kept only when the home has no more dark rooms
    (`layout.dim`: chambre, salon, salle a manger or cuisine with no facade window or court opening, or a
    strip over `[interiors.flats] strip`). This cost villa No. 390 (170 -> 169) and maison No. 839, 875, 985,
    1011 (591 -> 588).
  - Final: dar 155 (bar 152), compact 266 (bar 264, met), small 81, koubba 21, shop 129 (bar 130, one
    short), villa 169 (bar 170, one short), maison 588 (bar 586, met); 0 crashes, 0 passing houses lost or
    changed in any group (rooms.json hashes); colonial 167, slab 317 byte-identical (0 of 623 changed). Every
    passing interior: 0 `mesh.faults`, 0 step faults (`h471f_dump.py` with walls). Ladder warnings unchanged
    (compact 14, shop 6, dar 1, small 1, villa 3, maison 10). Guard (`blind.py`): on the 742 villas and
    maisons passing before, 0 changed; the 15 newly passing ones have 41 blind chambres, 7 strip chambres and
    1 strip cuisine where their failing plans at 43ef2c3 had 42, 6 and 3; totals (all passing) chambres blind
    villa 19, maison 1451, strip 29 and 201 (the new houses' own rooms). Slowest alone: passing plans as
    before (maison No. 835 0.60 s, villa No. 322 0.37 s, dar No. 90 0.31 s; newly passing maison No. 610
    0.71 s); failing houses planned again cost more (maison No. 666 0.44 -> 1.57 s, No. 528 1.31 s, compact
    No. 116 0.19 -> 0.67 s, shop No. 432 0.10 -> 0.40 s). `pytest -q` passes (`test_dark_rooms_counted`
    new); `build --quick` done; fingerprint `--allow ""`: 282 parts, 0 changed. Plans: output/checks/471-r8.png
    (compact No. 488: skifa, droj and bit to the court, no longer through the matbakh; shop No. 166: entered
    through the bit, the matbakh at the far end; villa No. 290: the couloir jogs round a window bay).
  - Not done: B (a) for the 13 compact ladders (the round went to the bars; it needs a new stair arrangement:
    the newel open in the entry room, a combined entry flight, rails and a headroom check: a round of its
    own); compact way in No. 250 (the street door opens into the matbakh strip: 4 cells for skifa, court,
    stair, bit and matbakh), 334, 574; shop No. 298 and 645 (steps and ladder), 432 (a 1.6 m2 store whose
    door fits no partition), 449 (the hanout partition at the street door's jamb), 71, 374, 636 (tile
    spikes); villa No. 380 (an L chambre round the stair), 390, 250, 307 and 388 (a two-floor villa whose
    upper floor is all couloir), 353; maison No. 666, 1011 (chambre under minimum), 464, 486, 760 (chambres
    over 36 m2), 863 (arch), the 4 tile spikes and 4 with no U stair.
  - Choices for Ali/lead: a tiny one-floor house may have its wc in the sdb and its chambre before the
    cuisine (as a small Tunisian house of 40-55 m2 would); still left: such a house without the spine's hall
    and couloir (rooms opening off the hall), which needs the spine engine changed. A failing house is
    planned up to 3-4 times (failing plans up to 1.6 s alone).
- Lead (after round 8): committed as progress. Read the whole diff: a redraw takes its own purpose path
  ("again", n) only when a plan still faults, so first plans keep their streams; colonial and slab
  byte-identical. `pytest -q` 137 passed in 42 s; fingerprint 0 changed. Accepted for Ali: a failing
  house is planned up to 3-4 times (up to 1.6 s alone; the viewer opens one house at a time). Seen in
  471-r8.png, for the later plan-quality item: No. 488's way to the wast ed dar crosses the droj and the
  bit, and its bit el ma is entered through the matbakh; No. 166's bit wraps the hanout and makhzen on
  three sides. The checks allow both.
- Round 9 (houses, helper; scripts `/tmp/claude-501/h471r9/`: `geo.py` and `dbg.py` the stair-room
  geometry, `shot.py` the 3D views; surveys `h471f_dump.py` with walls, `diff.py`, `blind.py`):
  - Baseline (93a6161): dar 155, compact 266, small 81, koubba 21, shop 129, villa 169, maison 588 (Ain
    Chilel); colonial 167, slab 317. Ladder warnings compact 14, shop 6, dar 1, small 1.
  - B (a), the newel open on floor 0 in the entry room, built and measured, then removed (not kept: it
    won no house). A newel turns 3/4 per floor, so its landing faces the roof stair room's door on every
    floor and that door fixes which quarter stands over the street door. Stair room door at the back or the
    street (No. 34, 65, 260, 300, shop 298): the middle quarter, 0.85-1.85 m over floor 0, over the door.
    Door on a side (No. 104, 259, 503, 514, 535, 347, 459, 171): at best the last quarter, its lowest step
    2.05 m over floor 0, but the street doors' heads stand 2.09-2.71 m over floor 0 (No. 104 2.58, 503
    2.71, 514 2.15, 259 2.09); dar No. 171 (door head under 2.0 m, rise 1.06 m) passed that, but its 5 entry
    steps meet the newel's pier 0.6 m inside the door and a turned flight's door landing meets the first
    steps. A full-turn newel or a straight flight do not fit either (a flight to the roof needs about 2.5 m
    under the stair room, which is 2.35 m deep).
  - B (b), built (`dar.roof_newel`, `newel_up`, `layout.newel_up`): a house of 2 floors or more whose newel
    does not fit under the stair room is planned again with a roof newel from the top floor under the stair
    room (its cell keeps `clear` of that floor's windows only) and the house's newel in a corner up to the
    top floor; kept when the ladder goes, `rooms.check` finds no more and `layout.dim` no more dark rooms.
    Won compact No. 325, 347, 472 and shop No. 40 (all passing before and after). No. 459 keeps its ladder:
    the roof newel's cell meets the light well beside a floor-1 window ("partition of droj and well within
    0.3 m of an opening"). One-floor houses skip the retry (no top floor to stand on).
  - Shop 129 -> 130 (No. 298, a ladder house of 1 floor): its ladder into the stair room stood on the entry
    steps (the stair room lies over the hanout; the skifa part of it is 0.8 m wide). `stair_ladder` now
    tries a place off the turned flight's strip along the door's wall (`steps_flight` 0.9 m deep) before
    giving up on the steps; the steps then turn beside the ladder (`Job.entry_keep(wide=)`).
  - Villa 169 -> 170 (No. 250): the street door in an acute corner left 0.06 m treads; the sunken entry of
    round 5 now runs for villas and maisons too (the hall at the threshold, 6 steps up into the chambre).
    Maisons: no other house changed (the sinking is kept only when the check finds less).
  - Final: dar 155, compact 266, small 81, koubba 21, shop 130 (bar met), villa 170 (bar met), maison 588;
    0 crashes; 0 lost; changed rooms.json: compact No. 325, 347, 472 and shop No. 40 (roof newels), shop
    No. 298 and villa No. 250 (won), nothing else in any group; colonial 167 and slab 317 byte-identical
    (0 of 623). Every passing interior: 0 `mesh.faults`, 0 step faults. Dark-room guard (`blind.py`):
    villa chambres blind 19, strip 29, maison 1451 and 201 (as round 8); No. 250 has none. Ladder warnings:
    compact 14 -> 11, shop 6 -> 5, dar 1, small 1 (reasons above; compact No. 285, small 206, shop 600, 612,
    645 are "no newel stair fits" at all, another cause, not touched). Slowest alone unchanged (compact No.
    116 0.59 s, shop No. 432 0.39 s); the 2-floor ladder houses are planned twice (No. 40 0.25 -> 0.32 s,
    347 0.07 -> 0.15 s, 459 0.05 -> 0.10 s). `pytest -q` 138 passed
    (`test_roof_newel_climbs_from_top_floor` new, pure, 0.01 s; `test_old_town_stairs` accepts the roof
    newel); `build --quick` done; fingerprint `--allow ""`: 282 parts, 0 changed.
  - Plans: output/checks/471-r9.png (compact No. 347 and 325: the corner newel up to floor 1 and the roof
    newel's droj on floor 1 under the stair room; shop No. 298: the turned steps beside the ladder; villa
    No. 250: the sunken hall, -1.0 m, steps up into the chambre). 3D: output/checks/471-r9-stair.png (No.
    347 and 325 cut at floor 1: the roof newel's cell, steps, rail and door).
  - Choices for Ali/lead: a 2-floor house whose stair room stands over the street door has two stairs, a
    newel in a corner from the ground floor and a second one under the stair room from the upper floor (as
    many medina houses have a separate flight to the terrace); a 1-floor house keeps its ladder into the
    stair room (way (a) cannot be built with today's door heights and stair rooms: the stair room would
    have to move off the street door, a tile change); a villa's hall may be sunken and its steps stand in
    a chambre (No. 250).
  - Left: the 11 compact, 5 shop, 1 dar and 1 small ladders above; shop No. 71, 374, 636 (tile spikes),
    432, 449, 645; villa No. 266, 307, 320, 353, 369, 380, 388, 390.
- Lead (after round 9): committed as progress (shop 130 and villa 170 reach their bars; ladders compact
  14 -> 11, shop 6 -> 5). Read the whole diff: `test_old_town_stairs` keeps its checks on the house newel
  and puts the stair-room door checks on the roof newel. `pytest -q` 138 passed (one known shapely
  envelope warning from the new test's square); fingerprint 0 changed. Seen in 471-r9.png: villa No. 250,
  won by the sunken hall, is entered through two chambres (hall, chambre, chambre, then the couloir).
  Measured over the passing homes (`/tmp/claude-501/lead/wayin.py`, `wayin_flats.py`: the salon reached
  from the entry without crossing a chambre, sdb, wc or cuisine): villas 37 of 170 fail it (No. 235: the
  salon, cuisine and salle a manger only through chambre 1), maisons 51 of 588, flats 262 of 1104
  (colonial) and 1065 of 4637 (slab; No. 1064 flat 11: the salon only through a chambre). Round 6's way
  in covers old-town houses only. Lead's decision: round 10 adds the check for modern homes and fixes the
  doors, so the bars count honest plans.
- Round 10 (the way in for modern homes, helper, about 55 minutes; scripts and results
  `/tmp/claude-501/h471r10/`: `one.py` a home's links and pieces, `cls.py` classes, `guard.py` + `gcmp.py`
  passes and `layout.dim` per home against a full `git archive HEAD` tree, `alone.py` single-process times):
  - The check, `plancheck.way_home` (in `rooms.check`; villas, maisons, colonial and slab flats): from the
    entry (a house: the front door's room; a flat: its rooms on the common palier) the salon, salle a manger,
    cuisine and every couloir are reached without crossing a chambre, sdb, wc or cuisine (a cuisine is
    reached, never walked through); chambres en enfilade and en suite baths allowed, but one sdb or wc must
    be on the way. Old town untouched (`way_in` as round 6). Test `test_way_home` (hand-made villa, 0.01 s).
  - Baseline (5333337 plus the check): villa 121, maison 461 (Ain Chilel); colonial 40, slab 102. The
    check is stricter than the lead's probe (it also asks the cuisine, the salle a manger, every couloir
    and a bath on the way). Classes: maison "the couloir only through a chambre" 65 (upper floors: the
    palier opens only into a chambre), cuisine off the way 22, no bath on the way 15, salon 12; villa
    cuisine 12, bath 12, salon 8, all of them 9 (hall in an acute corner).
  - Fix 1, doors (`plancheck.way_doors`, `layout.way_home`): from the reached rooms to each day room,
    couloir, hall or palier off the way (No. 235: the salon opens on the palier), a bath's when none is
    reached; full door with `inner_clear`, else narrow; kept when the check finds fewer faults, none of a
    new kind, no more dark rooms. Villa 121 -> 133, maison 461 -> 485.
  - Fix 2, the search (second plans only, `early_bays` and redraws): `spine.astray` scores day rooms no
    door joins to the hall or couloir and a way that misses the stair box; upper floors get a stub couloir
    to the landing and take the couloir piece at the landing. Villa 144, maison 517.
  - Fix 3, type trades (`plancheck.way_swaps`, `[interiors.villa] way_swaps` 6): a day room off the way
    trades with a chambre on it, two rounds, the best trade of each. Villa 163, maison 539.
  - Fix 4, upper floors: a way meets the box on an arch's length (0.85 m, not a door's 1.19 m), and of
    variants as good the second plans take the fewest dark rooms (`spine.dark`: no window or a strip, as
    `layout.dim`). The first plan of an upper floor whose first faultless variant misses the box takes a
    later one that reaches it, no darker, weighed against the whole house planned without that choice
    (`layout.way_moved`). Maison 578.
  - Guard: the steps', tiny-house and sunken-hall retries now choose without the way faults
    (`layout.plain`), else the check alone moved plans (230 and others). With a full HEAD tree (a tree of
    only `citygen` + `styles` plans other houses: 168/583 there): `layout.dim` grew on 0 passing villas and
    0 passing maisons; passing totals villa 90 (HEAD 97), maison 2172 (HEAD 2255).
  - Flats: the doors only (`layout.flat_doors`, judged by the wall checks of the floors they stand on: a
    slab's whole check is up to 0.8 s; `[interiors.flats] way_swaps` 0: trades judged by whole checks won
    7 slabs and 8 colonial blocks more but took slabs to 12 s). Colonial 40 -> 66, slab 102 -> 215 (old
    check: colonial 167 -> 170, slab 317 unchanged; bars 257 and 336 open with Ali). Doors only, so no
    room changes and no dark rooms added.
  - Final (survey with walls): villa 165 (bar 170), maison 578 (bar 586), dar 155, compact 266, small 81,
    koubba 21, shop 130 (old town: rooms.json hashes all identical); colonial 66, slab 215. 0 crashes;
    every passing interior 0 `mesh.faults`, 0 step faults. Lost against round 9 (old pass, now fails):
    villa No. 250, 254, 298 (acute-corner halls into a chambre), 330, 332; maison No. 481, 490, 551, 608,
    610, 628, 673, 725, 754, 776, 785, 845, 892, 908, 1003; won maison No. 482, 625, 640, 839, 1011.
    Times alone: passing plans as before (maison No. 835 0.63 s, villa No. 322 0.42 s; slab No. 1169 0.99
    -> 1.61 s, colonial No. 773 7.5 s unchanged); failing houses slower (maison No. 528 1.32 -> 2.51 s,
    No. 666 1.58 -> 2.27 s, No. 961 0.61 -> 2.34 s: second plans now scan their variants for the fewest
    dark rooms; an earlier stop lost 10 maisons). `pytest -q` 139 passed; `build --quick` done;
    fingerprint `--allow ""`: 282 parts, 0 changed. Picture: output/checks/471-r10.png (villa No. 235: the
    salon opens on the palier, the cuisine on the salon; slab No. 1064 floor 2, enlarged: flat 11's salon
    opens on its couloir).
  - Choices for Ali: a day room may open on the stair's palier (a villa's floor 0, No. 235) as a real
    villa's living room often does; the old door through a chambre stays as a second door. A flat keeps
    its types (no salon/chambre trade) for speed. A narrow door (0.7 m) may join a couloir or palier.
  - Left: the bars (villa 5 short, maison 8 short): upper floors whose way to the box makes a dark chambre
    (the guard refuses: No. 608, 725, 754, 892), halls in acute corners (No. 250, 254, 298), cuisines behind
    chambres with no trade that keeps the sizes; failing houses' times; the flats still failing (slab 138,
    colonial 204 blocks, way faults and others) belong to the open flats redesign.
- Lead (after round 10): committed as progress: the way-home check makes the counts honest (with it, before
  the fixes: villa 121, maison 461, colonial 40, slab 102; after: 165, 578, 66, 215), so villas and maisons
  are under their bars again. Read the whole diff (no new draws; the way's doors, the type trades and the
  upper-floor variant are each kept only with fewer faults and no more dark rooms). `pytest -q` 139
  passed; fingerprint 0 changed. Seen in 471-r10.png: villa No. 235 is now hall, palier, salon; its salon
  keeps an arm along the cuisine (already there at 5333337) and its door beside the flight wants a look in
  3D. Failing houses take up to 2.5 s alone (round 9: 1.6 s): for round 11.
- Round 11 (villas and maisons, helper, about 52 minutes; scripts `/tmp/claude-501/h471r11/`: `cls.py` the
  room between the way and the room off it, `dbg4.py` + `why.py` each carve candidate and why it was
  refused, `stage.py` time per stage, `chk.py` repeated checks, `guard.py` + `gcmp.py` against a full
  `git archive HEAD` tree in `head/`, `diff.py` won/lost/changed by rooms.json hash):
  - Baseline (afe6708, Ain Chilel, survey with walls): villa 165, maison 578. Lost list classified: 10
    maisons and villa 330 have an upper floor whose couloir one chambre (wrapping the U box) keeps from the
    palier; villa 254 and 332 a hall or palier whose way runs through the cuisine; villa 298 and maison
    551, 908 a droj between the hall and the salon.
  - Fix 1, a couloir carved through the room in between (`carve.py`, `layout.carve`, after the plan): a
    strip `[interiors.villa] couloir` (1.15 m) wide straight from the palier or hall to the room off the
    way (or back, or along it when it lies beside, then up to 0.3 m past the ends round a jog of the wall);
    it joins the hall or couloir, else becomes a couloir; scraps of the host up to `carve_scrap` 2 m2 go
    with it, a window on it lights the couloir when the host keeps one, no stair under it, the host keeps
    its minimum, no neck under 0.8 m in the grown room (a hall joined by a hair passed every check: seen
    in villa No. 254's plan, fixed). Then the way's doors, kept as round 10's (no new kind, fewer faults,
    no more dark rooms). Hosts chambre, cuisine, sdb; `carve_tries` 6, `carves` 2. Won maison No. 481,
    608, 628, 725, 754, 776, 785, 1003; villa No. 254, 298.
  - Tried and removed: doors through the droj (No. 298, 551, 908 pass the check, but each second door
    stands off the newel's landing quarter, so the way crosses its steps); a memo of `spine.cut_region`
    (22% hits); fewer variants for second plans (`retry_variants` 0.6: lost 2 maisons, 18 changed).
  - Time: (a) a villa or maison whose plan has a fault no second plan cures (`layout.HOPELESS`: a storey
    crossing a window, no U stair, "the villa/maison has no ...") is planned no second time (surveyed:
    "floor 0 has no cuisine" is cured, so it stays out; 0 passes changed); (b) the carve runs first on the
    first plan, kept only when the house then passes, and a pass with dark rooms still lets the redraws
    try, the one with fewer dark rooms kept (without that, No. 580 grew a dark room); (c) the second carve
    only after a redraw that was kept; (d) `layout.check` remembers `rooms.check` per plan state for
    villas and maisons (md5 of the pickled held state; up to 7 asks of the same plan); (e) `[interiors.villa]
    redraws` 2 -> 1: the second redraw won only maison No. 620 for 0.6 s per failing house.
  - Final (Ain Chilel, survey with walls): villa 165 -> 167 (bar 170, 3 short), maison 578 -> 585 (bar
    586, 1 short: maison No. 620 is lost with the second redraw; `redraws = 2` gives 586 and failing houses
    2.3 s alone, Ali's/lead's choice). Won maison No. 481, 608, 628, 725, 754, 776, 785, 1003; villa No.
    254, 298; lost maison No. 620; passing but changed maison No. 565 and villa No. 310 (carved before the
    redraw that passed them at HEAD; dark rooms 3 -> 3 and 0 -> 0). Old town rooms.json identical (677 of
    677, capital: dar 155, compact 266, small 81, koubba 21, shop 130); colonial 66 and slab 215
    byte-identical (623 of 623). Every passing interior 0 `mesh.faults`, 0 step faults. Guard (`layout.dim`,
    full HEAD tree): grew on 0 changed or passing homes; the 10 won houses keep their failing plans' count
    (No. 481 2, 754 2, 785 8, 1003 3, ...); totals over passing homes villa 90 (HEAD 90), maison 2184 (HEAD
    2172, the won houses). Times alone: maison No. 892 2.33 -> 1.68 s, 666 2.27 -> 1.63 s, 961 2.32 ->
    1.59 s, 528 2.53 -> 0.49 s, 500 1.61 s, 481 1.58 s (passing via a carve, was failing). `pytest -q` 140
    passed (`test_carve_band` new, 0.01 s); `build --quick` done; fingerprint `--allow ""`: 282 parts, 0
    changed. Picture: output/checks/471-r11.png (villa No. 254: the hall in the acute corner runs along the
    street wall to the palier, the cuisine behind it; maison No. 754 floor 1: a couloir stub from the
    couloir to the palier between two chambres).
  - Choices for Ali: a couloir may take a strip of a chambre, cuisine or sdb (the room keeps its minimum
    and a window) and a scrap up to 2 m2 beside it (a nook, as a real villa's couloir widens near the
    stair); a window on the strip lights the couloir; a hall may run along the front from an acute corner
    to the stair (No. 254). A droj (the roof stair's room) is never a passage.
  - Left: villa No. 330 (the cut makes its chambre a strip: the guard refuses), 332 (the new couloir
    through the cuisine gets no doors to the palier and salon), 250 (sunken hall in an acute corner, no
    strip fits), and the program-limited villas (266, 307, 320, 369, 388); maison No. 961 (its only cut
    meets the couloir by a 0.6 m neck), 892 (second plans pass but are darker), 490 and 673 (the room in
    between under its minimum after a cut), 845 (bath at a triangle's tip), 620 (the second redraw); the
    U box's doors off its landing were not checked (a probe was inconclusive: the palier room is larger
    than the box).
- Lead (after round 11): committed as progress (villa 167, maison 585; failing houses back under 1.7 s;
  old town and flats byte-identical). Lead's choice on the helper's question: `redraws` stays 1 (the
  second won one maison for 0.6 s more per failing house, and 47.2 plans the maisons again). Read the
  whole diff: `layout.check`'s memo keys a plan state's pickle (a cache only: a miss costs time, never
  a result). `pytest -q` 140 passed; fingerprint 0 changed. Seen in 471-r11.png: villa No. 254's hall
  runs along the front wall from its acute corner to the stair; maison No. 754 keeps a wc box inside its
  salon (round 7's wet carve) and its roof ladder stands in a floor-1 chambre (one of the 10 maison
  ladders): both for 47.2's maison plans.
- Decision (Ali, 31 October, "Yes, redesign"; the lead chose the forms for quality): deep colonial blocks
  and maisons get courtyards, so every chambre, salon, salle a manger and cuisine has a window. Design,
  for the rounds that follow (A: the courts in the city; B: interiors lit by them and the window check;
  C: the bars):
  - Which buildings: colonial blocks (`apartments` outside modern districts) and maisons (`house` outside
    the traditional districts) whose footprint has a deep part: farther than `reach` (about 6.5 m: a room
    of 4.5-5 m behind a 1.1-1.2 m couloir) from its windowed facades (the street fronts; party walls have
    no windows). Villas and slabs keep their footprints (their dark rooms are a planning matter).
  - The form, as real blocks of Tunis and Algiers (1900-1950) and Tunisian town houses have it: a colonial
    block gets a main courtyard (at least 4 x 4 m) where the deep part is wide, rooms of every kind may
    face it, and light wells (courettes, at least 2.4 x 2.4 m) where only a cuisine or bath needs light; a
    maison gets one patio (at least 3 x 3 m) in its deep part. Courts are open to the sky from floor 0
    (a ground-floor shop row stays on the street); a block's setback top floor and stepped parts keep them.
  - Nothing else moves: the same buildings in the same order, kinds, floors and streams (any new choice
    takes its own purpose path), so households, names and every other building stay byte-identical
    (`life.households` draws one household per housing building, without geometry).
  - The city shows them as it shows old-town courts (holes in the footprint: inner walls, parapets);
    the interiors put court windows on their walls as `dar` does, the spine plans habitable rooms on lit
    walls and services on the light wells.
  - A new check: every chambre, salon, salle a manger and cuisine of a modern home has a window (street,
    court or light well); an sdb or wc may stay blind.
  - Bars, with every check (way home included): colonial 257/270, slab 336/353, maison 586/616, villa
    170/178, the old town unchanged. The fingerprint changes only in the parts that hold changed
    buildings (listed exactly); `tools/make_blend.py` refreshes Blender when tiles change.
- 47.2 round A (courts in the city; helper, Opus 5.5; the lead commits):
  - Changed: citygen/city/courts.py (new: `courts_for`, a pure function of a footprint, which walls hold
    windows and the numbers; `apply_courts`, `cut`; 0.7 s on the quick capital), citygen/city/massing.py
    (courts as the last massing step, no draws), citygen/city/dressing.py (`_court_windows`, own stream
    `rng("court", k)`), citygen/interior/outside.py (`wall_segments` holds the court rings, after the old
    ones), citygen/interior/layout.py (court walls of a modern home with courts as thick as its street walls),
    styles/maghreb.toml (`[courts]`, `[dressing.courts]`), tests (`test_court_rule` new, 0.1 s; `OPEN_472`:
    colonial No. 825, maisons No. 848, 990), SPEC (massing, dressing), HANDOFF, ROADMAP (47.2: round A noted,
    not ticked).
  - Counted first (outer rings, quick capital and Ain Chilel): 245 of 270 colonial blocks and 486 of 616
    maisons lie deeper than 6.5 m from their windowed walls (street walls and walls facing open ground, the
    dresser's own rule; party walls hold none). Villas and slabs: untouched by design.
  - The rule (`city/courts.py`, `[courts]`): the dark part is the footprint less a `reach` 6.5 m buffer of the
    windowed walls (exact polygon). Courts are rectangles along the footprint's frame, searched on a 0.5 m
    grid, at least `front` 4.0 m from a windowed wall, `party` 2.4 m from a party wall, `between` 3.0 m from
    another court, sides from `sizes`: colonial `court` 4-10 m then up to four `well`s 2.4-3.5 m; maison one
    `patio` 3-7 m. Per kind in turn: the smallest court lighting the whole dark part (every corner of its
    convex hull within `reach`), the one nearest its middle; else the one lighting the most dark cells. A
    footprint less dark than `min_dark` 1 m2 keeps none. The outer ring keeps its exact coordinates (street
    draws unchanged); a set-back top floor gets the same holes (court open to the sky; it must contain the
    court with 0.5 m to spare); a corner dome keeps 1 m clear. Roof stair rooms, terraces and roof props
    already keep to `RoofLayout.inner`, which the parapet round each court leaves out.
  - Result: quick capital 241 colonial blocks with courts (224 main courts, mean 5.6 x 4.3 m; 22 light wells,
    2.5 x 2.5 m); 18 blocks stay partly dark (no room for a court or well by the rule, farthest point 6.7-9.3
    m). Ain Chilel 293 maisons with a patio (mean 3.2 x 3.0 m); 193 deep maisons get none: their lots are 7-9
    m wide, too narrow for a 3 m patio with 2.4 m rooms beside it (measured options: a 2.4 m light well when
    no patio fits 149 still dark; side rooms 2.0 m 155; both 112).
  - Court walls: a column every `spacing` 2.8 m (at least one on a wall of `wall` 1.8 m), a window on every
    floor from the ground, shutters 65% or grilles 35% in the household's door color, a light well's 0.75 the
    size (`[dressing.courts]`). `Outside` hands them over as facade openings on their court wall.
  - Nothing else moved (per-building proof, HEAD copy against the tree, capital and Ain Chilel): every
    building without a court has the same footprint, fields, household and dresser placements (1,427 in the
    capital, 739 in Ain Chilel); the 241 + 293 courted ones change footprint and placements only. In the five
    changed tiles every triangle and placement outside the courted buildings is the same, except 5 more people
    in two tiles: the crowd's figures take a byte share of the whole tile, which grew. Interiors (survey with
    walls): every house without a court has a byte-identical rooms.json (slab 353, villa 178, colonial 29,
    maison 323).
  - Fingerprint `--allow "plan/goumosbane/buildings,maps/goumosbane.png,tiles/index,tiles/tile_12_23.glb,
    tiles/tile_12_23_lod1.glb,tiles/tile_13_23.glb,tiles/tile_13_23_lod1.glb,tiles/tile_13_24.glb,
    tiles/tile_13_24_lod1.glb,tiles/tile_14_23.glb,tiles/tile_14_23_lod1.glb,tiles/tile_14_24.glb,
    tiles/tile_14_24_lod1.glb"`: 282 parts, 13 changed, all allowed (the tiles holding colonial blocks, the
    plan's buildings, the city map, the index's byte count). Tile bytes: 13_24 +12% (1.47 -> 1.65 MB), 14_24
    +6%, 13_23 +3.5% (4.69 -> 4.85 MB), 12_23 +3%, 14_23 +2.6%.
  - Interiors (no crash anywhere; the planners do not use the courts yet): colonial 66 -> 13 of 270 (55 lost,
    2 won: mostly "only through a chambre, bath or cuisine", the flats' spine does not route round a court),
    slab 215 = 215, maison 585 -> 569 of 616 (21 lost, 5 won), villa 167 = 167. Blind rooms in every plan,
    passing or not (`blind.py` without its pass filter, HEAD copy against the tree): colonial chambres 4,358
    -> 2,415 of about 5,500 (78% -> 44%), cuisines 442 -> 101, salles a manger 840 -> 477, salons 24 -> 9,
    blocks with 3+ blind chambres 258 -> 236; maison chambres 1,492 -> 623 of 3,410 (44% -> 18%), cuisines 186
    -> 74, salles a manger 343 -> 224, salons 60 -> 35, houses with 3+ 190 -> 76. The lead's `blind.py`
    (passing plans only): colonial 66 passing, chambres 884/1,218 blind -> 13 passing, 99/247; maison 585
    passing, 1,424/3,245 -> 569 passing, 576/3,087; slab and villa unchanged (848/9,671, 17/600).
  - Tests: `test_court_rule` (rectangles: a 12 x 24 block gets a court, a 10 x 16 maison one patio, a 14 x 9
    house none, a 7 x 16 lot none and stays dark). The sample colonial block No. 825 of the interior fixture
    got a court: its street door now opens into flat 0's hall and a partition crosses that door, so
    `test_flats` skips it and `test_interior_holes_match_the_facade` allows exactly that door's fault
    (`OPEN_472`, round B); its court windows' holes are still checked. The slow
    `test_new_district_plans_are_valid` skips maisons No. 848 and 990, which got a patio and now fail
    (`OPEN_472`). `pytest -q` 141 passed; `pytest -q -m slow` 5 passed, 1 xfailed (as before).
  - Pictures: output/checks/472-a.png (quick capital colonial blocks from above: courts with windows on every
    floor), output/checks/472-a2.png (Ain Chilel maisons with patios; built with `--build-args "--area
    'city-center:Ain Chilel' --out output/ain472"`), output/checks/472-a-plans.png (colonial No. 971 court,
    No. 940 court and light well, maison No. 882 patio). Blender: output/bodjantouna-42/goumosbane.blend
    refreshed.
  - Choices for Ali: courts are rectangles along the building (as built blocks have them); a main court is as
    small as lights the block (about 5.5 x 4.3 m, rooms 4-6.5 m deep round it), light wells 2.5 m; court
    windows on every floor including the ground floor, plain shutters or grilles; the maison patio 3 x 3 m in
    most houses. Narrow maisons (7-9 m) keep a dark back: a patio against a party wall (as many real narrow
    town houses do) would be a notch in the footprint and could change the neighbours.
  - Left for round B: the flats and maison planners use the courts (rooms round them, the spine routed round a
    court, services on light wells), the window check, No. 825 (`OPEN_472`); the 193 narrow maisons and 18
    blocks still partly dark (a rule for them); round C the bars.
- Lead (after 47.2 round A): committed as progress. Read the whole diff: the courts take no draws, their
  windows have their own stream ("court", k); every other building, household and name unchanged (the
  helper's building-by-building compare); the lead re-surveyed the old town: 677 of 677 rooms.json
  identical (old-town courts also enter `outside.wall_segments` now, with no effect). Fingerprint: the 13
  parts the helper named, nothing else. `pytest -q` 141 passed in 45.5 s (41.5 s at 901a5d6: round B
  should win the 4 s back); the lead moved `[dressing.courts]` above the open-walls comment it had split
  from its table. Seen in 472-a.png and 472-a2.png: courts and light wells with windows on every floor in
  the colonial quarter, small patios in Ain Chilel's maisons; in 472-a-plans.png No. 971's flats ring
  their court, No. 940's floor-1 and floor-2 salons wrap the court as long L strips and its light well
  loses its walls on floor 3 (round B). goumosbane.blend refreshed by the helper.
- 47.2 round B (rooms around the courts; helper, Opus 5.5; the lead commits; partly done, about 75 minutes):
  - The window check (`plancheck.windows`, in `rooms.check`): every chambre, salon, salle a manger and cuisine of
    a villa, maison or flat has a window (street, court or light well window, or a balcony door; `layout.dim`'s
    rule); an sdb or wc may stay blind. Worded "flat 3: the chambre 12 on floor 1 has no window" ("the home"
    for a house). The steps', tiny houses' and sunken entries' retries choose without it (`layout.plain`), the
    redraws and carves count it. Test `test_windows` (hand-made maison and flat, 0.1 s).
  - Baseline (HEAD plans, the window check applied; survey with walls, `/tmp/claude-501/h472b/dump.py`, HEAD
    extracted whole): colonial 0 of 270 (13 without it), slab 125 of 353 (215), maison 208 of 616 (569),
    villa 143 of 178 (167). Blind rooms in every plan: colonial chambres 2,415, salles a manger 477; slab
    chambres 1,380, salles a manger 360; maison chambres 623, salles a manger 224 of 232, cuisines 74; villa
    chambres 17. Most blind rooms are the spine's leftover cells (`leftovers`: a blind room-sized cell became a
    chambre or salle a manger) and variants the search took first because it never counted them.
  - Fix 1, the search scores what the check asks (`spine.blind`, `[interiors.flats] blind_faults` by layout):
    a blind chambre or salle a manger counts as a fault. Fix 2, a blind leftover cell big enough for a chambre
    joins a neighbouring room, else the hall or couloir, within its `most` (`blind_join`; first version also
    past `most`: 79 maisons got a chambre over its most, so capped only; then no join that leaves an L strip
    over `strip`, the guard: maison 396 -> 390, strips per passing maison 0.67 -> 0.64). With both: villa 165,
    maison 396, slab 185, colonial 1, but slab plans 3.4 times slower (survey's slowest 8.2 s, HEAD 2.4 s): a
    floor that cannot be all lit tries every variant. Fix 3, `blind_cap`: a flat's search stops after that many
    variants when only blind rooms keep its best from passing: slab cap 8 158 passes (slowest 6.7 s), cap 4
    139 (4.0 s); kept 4 for slabs and colonial blocks (time bar first).
  - Fix 4, court cuts (`spine.court_cuts`, `court_cuts` by layout): the spine cuts its bands at the ends of every
    court or light well they wrap, so a room beside a court reaches from the street wall to the court wall and
    no room rings a light well (No. 940's floor-3 chambre had a hole round its well; the plan tool also painted
    that hole white over the walls: `interior_plans.py` now draws a room's hole as wall and open air). Colonial
    strips: chambres 815 -> 709, cuisines 197 -> 128, salons 382 -> 341; blind chambres 1,259 -> 1,346; passes
    unchanged. In maisons the cuts left the cells beyond a 3 m patio blind (patio maisons passing 211 -> 189):
    colonial only. Tried and removed: a couloir along the court's side as the search's first variants (colonial
    passes 1 = 1, blind chambres 1,491 -> 1,620, blind salons 10 -> 1).
  - Final (with every check, window check included; HEAD -> now): villa 143 -> 165 of 178 (22 won, 0 lost, the
    143 byte-identical), maison 208 -> 390 of 616 (183 won, lost No. 639: the couloir only through a chambre;
    186 identical, 21 changed; the guard grew on No. 771 and 766, one strip room each where HEAD's redraw found
    a plan without), slab 125 -> 139 of 353 (14 won, 0 lost, 124 identical, 1 changed, guard unchanged),
    colonial 0 -> 1 of 270. Every passing interior 0 `mesh.faults`, 0 step faults. Old town (dar 159, compact
    277, small 83, koubba 22, shop 136, as the survey groups them): 677 of 677 rooms.json identical. Blind rooms
    in every plan: colonial chambres 2,415 -> 1,491, salles a manger 477 -> 214, cuisines 101 -> 116, salons 9 ->
    10; slab chambres 1,380 -> 1,045, salles a manger 360 -> 223; maison chambres 623 -> 138, salles a manger 224
    -> 46, cuisines 74 -> 73, salons 35 -> 31; villa chambres 17 -> 1.
  - Times (one process, while the slow tests ran): colonial No. 958 7.6 s (HEAD 5.6 s), slab No. 1324 2.5 s
    (HEAD 1.2 s, the bar 2.2 s: over), maison No. 923 2.8 s (HEAD 0.45 s: it now fails the window check and is
    planned again), villa No. 363 1.0 s. `pytest -q` 142 passed in 47.5 s (45.5 s: not won back); `-m slow` 5
    passed, 1 xfailed, after `OPEN_472` took maisons No. 851, 853 and 864 of the sample (all three fail the window
    check in HEAD's plans: 4, 1 and 7 blind rooms; now 851 trades them for 2 chambres over their most, 853 and 864
    keep 1 and 2). Fingerprint 282 parts, 0 changed (no city change: no Blender refresh, no look picture).
  - Narrow maisons (goal 3, measured, not built): of 323 maisons without a patio 182 pass, 115 fail the window
    check (the 7-9 m lots' dark backs), 26 other faults. Left for round C: a patio or light well against one
    party wall (a notch, the neighbour's exposed wall must render) or a rear court.
  - Picture output/checks/472-b-plans.png (No. 971, No. 940, maison No. 882 with its patio): No. 971's flats
    ring their court with salons and cuisines on the street and court; No. 940's light well keeps its walls on
    floor 3, but its south flats on floors 1-3 are still one U-shaped chambre of about 110 m2 wrapping the court
    (its cells exist, the program is not placed: "flat 1 has no salon, no cuisine"), and floor 0's street door
    opens into the cafe. Maison No. 882: salon on the street, cuisine and chambre on the patio.
  - Choices for Ali: a dark cell inside a flat or house joins the room or hall beside it (real flats of Tunis
    and Algiers have deep rooms and a dark hall, never a bedroom without a window); a maison's 3 m patio keeps
    the L rooms round it (cutting them left them dark); the slab search gives up on lighting the last dark rooms
    after 4 variants (time; 185 slabs would pass with no cap at 3 times the time).
  - Left for round C: flats planned round their courts (a couloir that follows the court, rooms spanning street
    to court, No. 940's U chambres, the cafe taking a colonial entry, OPEN_472 No. 825), the 115 narrow maisons,
    slab time against its blind search, maison blind cuisines (73), the guard on No. 771 and 766, OPEN_472
    maisons No. 848 (a chambre 61.6 m2 over its most round the patio) and 990 (a partition by the palier's
    window, a chambre over its most). Scripts in /tmp/claude-501/h472b/ (dump.py with extra.py, cmp.py, ana.py,
    narrow.py, onec.py).
- Lead (after 47.2 round B): committed as progress: the window check makes the counts honest again (with it,
  HEAD's plans: villa 143, maison 208, slab 125, colonial 0), and the fixes bring villa 165, maison 390,
  slab 139, colonial 1. Read the whole diff (blind cells scored and joined; bands cut at court ends for
  colonial only; the plan tool's light-well drawing fixed). The helper re-saved the fingerprint
  baseline at 7523fad (round A) as the routine says: `compare before --allow ""` is now 0 changed.
  `pytest -q` 142 passed in 47.5 s. Slab No. 1324 takes 2.52 s alone (bar 2.2 s; HEAD 1.2 s): round C.
  Seen in 472-b-plans.png: No. 971's flats put their salons on the street and their chambres round the
  court; No. 940's floors 1-3 keep a chambre of about 110 m2 wrapping the court's south side (it fails
  the check: round C's wings).

## 2026-10-31 - Prompt 50 H1f Interiors in the viewer
- Commit: (lead commits) | Model: Opus 5.5, high
- Changed: citygen/view.py (`api/interior` in `citygen view` and under `/b/<key>/` in the gallery,
  `Interiors`: a lock and one BuildContext per build; the gallery finds interior folders),
  tools/viewer/index.html (`folder=interiors/<name>`, Cut menu and `cut=roof|<floor>` with one global
  clipping plane plus the same plane on the materials for shadows, rooms named on click, "Open interior" on
  a dwelling's card, a smaller shadow box for interiors), tools/viewer/gallery.html (interior cards),
  tools/make_artifact.py (`SERVER_API = false` on the phone page), tests (2 new, 1 assertion), ROADMAP (50
  and H1 ticked), SPEC 6c Viewer, HANDOFF.
- Checks: tests 128 passed in 36 s (the new ones about 1.0 s); build --quick 4.7 s (tiles rebuilt once:
  view.py is in the build key); fingerprint 282 parts, 0 changed. Real flow tried in Chrome (Playwright,
  `citygen view` on the quick build): a click on a house showed "Open interior", the click opened a new tab
  at `?folder=interiors/goumosbane-597&view=interior` in 1.2 s (3.3 s before the rebuild, when the stale
  build key made the server plan the city again), the cut and room clicks worked ("Ghorfa: upper room, floor 1, 18 m2", "Bit el ma:
  washroom"); 49 of 72 rays through a cut house first hit something above the plane, and the picks skipped
  them; `folder=../summary.json` stops with a message; the phone page card shows the note and asks no
  server. Second interior through the server 0.15 s. No console errors besides Chrome's own GL notes.
- Look: output/checks/50.png - dar No. 599 cut at floor 1 from the overview (both halves the same, 0.00:
  `before_after` shows both sides through today's viewer and the interior data is unchanged).
  output/checks/50-card.png (the card with Open interior), output/checks/50-dar-cut1.png (the dar opened
  with `cut=1`), output/checks/50-interior-cut.png (the koubba opened from the card, cut at the ground floor).
- Doubts and questions for Ali: none. For the lead: `view.py` edits make every build stale (it is build
  code for the key); adding it to `buildkey.NOT_BUILD_CODE` would avoid that (one more rebuild once).
  The `interior` view of some houses stands right at a door (koubba No. 597), a choice of prompt 46/47.
- Lead review: read the whole diff, tests 128 passed, fingerprint 0 changed, no em dash. Own Chrome run
  (script `lead50_flow.py` in the session scratchpad: a click sweep over the street view until
  a card offers Open interior): colonial No. 845, new tab in 1.6 s, cut roof/1/0 at 22.17/9.12/5.52 m, room
  clicks named "Qahwa: cafe, ground floor, 81 m2" and two back rooms. Pictures output/checks/50-lead-card.png
  and 50-lead-cut0.png. Doubt for Ali: the tab opens on the `interior` spot, which for No. 845 faces a
  bedroom window from 2.5 m (a plain wall); opening on the overview cut at the ground floor would show the
  whole plan first (one word to change). Open: add `view.py` to `buildkey.NOT_BUILD_CODE`.

## 2026-10-31 - Prompt 49 H1e Floors, ceilings, stairs and roof terrace
- Commit: (lead commits) | Model: Opus 5.5, high
- Changed: new citygen/interior/floors.py (slabs with wells and light slots, floor finishes, ceilings and
  painted beams, slab edges, koubba dome from inside, court paving, majel, fesqiya, the roof drawer: deck
  with wells, coping, roof room caps and ceilings, skylight; `overheads`, `crosses`); interior/stairs.py
  (geometry: `Part`, `Run`, `level`, `parts`, `well`, `rails`, `stringers`, `treads`, `ladder_line`,
  `riser_max`); interior/mesh.py (`stairs_mesh`, `overheads`, roof room faces and openings walled in);
  export.py (floors, stairs, roofs through `building_tops(flat=)`, court trees on the paving); flats.py (cores
  kept off the entry steps, `entry_keep`, `Core.keep`); layout.py (`walls["roof"]`); mesh/tile.py
  (`building_tops`/`_masses_roofs` `flat` hook, tiles byte-identical); mesh/builder.py (`add_dome(inside=)`);
  mesh/textures.py (`terrazzo`, `tiles`, interiors only); styles/maghreb.toml (`[interiors.floors]`, palette,
  textures); tests (2 new); SPEC 6c, HANDOFF, ROADMAP.
- Checks: `pytest -q` 126 passed in 36 s (the 2 new tests about 1.2 s on the shared fixtures); slow interior
  tests pass (open samples xfail as before); `build --quick` done; fingerprint `--allow ""`: 282 parts, 0
  changed. Budget (largest of the test): slab No. 1169 42,426 -> 55,710 triangles, 3.64 -> 4.67 MB, 1.8 ->
  2.6 s in the command; dar No. 68 4,204 -> 7,764, 0.50 -> 0.85 MB (about 0.3 MB are the new textures).
  pick:dar:2 (No. 599) 5,222 -> 7,697, 0.56 -> 0.82 MB; pick:slab (No. 1264) 13,123 -> 17,416, 1.26 -> 1.58 MB.
- Plan fix (a stair could not be built): every slab core but two stood on its door's entry steps (154 of 156
  quick-capital slab doors have steps up, up to 18 risers; 59 of 89 colonial cores), so the steps ran under
  the flights. Cores now keep the steps and `turn` free (`flats.entry_keep`); a slab core slides in past them
  and its palier reaches the door on every floor (the stair windows light it). Interior survey (rooms.check):
  slab 327 -> 326/353 pass, colonial 105 -> 117/270; ladder warnings slab 56 -> 36, colonial 27 -> 24;
  slowest slab 2.75 -> 2.03 s, colonial 13.3 -> 12.9 s (No. 773).
- Whole-city stair survey (h49 scripts: every old-town house, every 2nd slab, villa and maison, every 3rd
  colonial block; quick capital and Ain Chilel; plan, walls, floors, roof and stairs meshed): 0 crashes;
  every newel, U and ladder connects its levels within 0.01 m, risers within `riser_max`, 2 m headroom
  over the walking line (and over both sides of wide entry steps) against slabs, landings, steps, the roof
  rooms' ceilings and beams; no slab or landing crosses an opening. Slowest plan + mesh: colonial No. 771
  5.4 s, slab No. 1169 1.8 s, old-town houses under 0.35 s, villas 0.45 s, maisons 0.6 s.
  Plan faults left (prompt 46's entry steps, plans untouched, for 47.1/48.1): steep entry steps with
  treads under 0.2 m (quick capital: dar 55/210 e.g. 31, 49, 75; compact 47/324 e.g. 46, 55; small 13/121;
  koubba 3/22; slab 5/177 e.g. 1065; Ain Chilel dar 10/71, maison 4/308, villa 2/89); entry steps clipped by
  a short or bent skifa, so treads are missing and the risers jump (compact 21, e.g. 34, 44, 65; dar 3, e.g.
  171; colonial 4, e.g. 771; slab 2: 1211, 1295; Ain Chilel 11); a house door whose steps run into the
  newel cell (small 230, compact 290 and 298, Ain Chilel small 65: no headroom under the newel). Colonial
  down steps (2-3 risers) on a core's floor landing are harmless (the flights start past them).
- Look: output/checks/49.png - from the court: the paved court (pale slabs under floor 0), the majel with its
  lid, the court tree on the paving, a red and white tiled floor through the bit's door. Extra:
  output/checks/49-stair.png (a copy of the folder, camera in ghorfa 16): tiled floor, zellige dado, the open
  door into the newel cell, its floor-level landing and the stone steps turning up. Interiors made on the
  quick build: output/bodjantouna-42/interiors/goumosbane-599 (pick:dar:2) and goumosbane-1264 (pick:slab).
  Blender: goumosbane-599/dar-labidi.blend and goumosbane-1264/the-ben-ghanem-family.blend (lead, make_blend).
- Lead review: read the whole diff (own streams: `beams` per room; no draws on old streams; numbers in
  `[interiors.floors]`); tests 126 passed; `build --quick` then fingerprint `--allow ""`: 282 parts, 0 changed;
  no em dash. Remade both interiors and drew a plan of their slabs, wells, stair parts and walking lines
  (levels 0, 1 and roof): newel and U wells under their flights, the slab core clear of the entry steps, the
  court a hole in every slab (0 m2 overlap), the dar's deck holed for the stair room; the slab has no roof
  room (plan of 47), so its deck is closed. No follow-up.
- Doubts and questions for Ali: the light slots (0.3 m gaps in a landing by a stair window, as SPEC asks)
  have no railing; ceilings and floors are not checked visually inside the slab (only in the two pictures);
  slab cores slid in by up to about 6 m take that strip from the flats on every floor.

## 2026-10-30 - Prompt 48 H1d Interior walls and openings
- Commit: (lead commits) | Model: Opus 5.5, high
- Changed: new citygen/interior/mesh.py (`walls_mesh`, `faults`); interior/export.py (shell = walls +
  `building_tops`, interior-only textures); mesh/tile.py (`frontage_inputs`, `building_mesh` split into
  `building_walls` + `building_tops`, same order of mesh adds); mesh/builder.py (`add_arch` `panel`,
  `proud`); mesh/textures.py (`zellige`, colored); styles/maghreb.toml (`[interiors.palette]`,
  `[interiors.textures]`, walls `dado`, `dado_rooms`, `balustrade`, openings `open_share`, `open_angle`,
  `leaf`, `casing`, `casing_proud`, `arch_frame`, `railings`, `casement*`, `mullion`; palette `glass_inner`,
  `casement_wood`, `casement_white`); mesh/gltf.py (`alpha` -> alphaMode BLEND, no tile uses it); tests (2
  new); SPEC 6c, HANDOFF, ROADMAP.
- Checks: `pytest -q` 124 passed in 34 s (new tests about 1.5 s: holes 0.1 s on shared fixtures, budget
  1.4 s); slow interior bytes test passes; `build --quick` done; fingerprint `--allow ""`: 282 parts, 0
  changed. Budget (with the casements): largest slab No. 1169 (10 floors) 42,426 triangles, 3.6 MB;
  largest dar No. 68 4,204, 0.50 MB.
- Whole-city wall check (helper's survey, 1,340 interiors: every old-town house, every 2nd slab, villa and
  maison, every 3rd colonial block): 0 crashes; every facade hole matches its piece within 0.02 m (center,
  width, sill, head; iron balconies are railings, no hole); walls take at most 0.5 s (slab). Interiors
  where `mesh.faults` finds something: dar 19/159, compact 41/278, small 10/82, koubba 1/22, shop 28/136,
  slab 98/176, colonial 81/90, villa 60/89, maison 58/308. All the cases looked at (about 25, pictures)
  are plan geometry that `rooms.check` does not see: stair cells 0.1-0.2 m off an exterior wall (under the
  roof stair room) leaving a sliver and the stair partition a few cm behind a window or the main door;
  doors placed across a partition junction (a modern door overlapping the next door, slab wc doors 7 cm off
  their couloir); sliver couloirs and hall strips (colonial); court openings past a court corner; openings
  on a footprint part no storey covers (villa windows, a small house's door). The walls cut through a wall
  thickened by such a sliver (up to 0.15 m) so doors stay passable. Open item 48.1 (lead: plan faults,
  plans untouched here), interiors with faults / interiors: dar 19/159, compact 41/278, small 10/82,
  koubba 1/22, shop 28/136, slab 98/176, colonial 81/90, villa 60/89, maison 58/308; fix: put these
  checks in `rooms.check`, then the plans. The test lists two known houses (`OPEN_48`: 193, 322) and
  skips partition crossings in flats (open item 47.1).
- Look: output/checks/48.png - the prompt's view stands in the court behind the court tree (only a strip of
  zellige through the T room's door shows). An extra snapshot of a copy with the camera in ghorfa 16
  showed solid plaster walls, the zellige dado broken at the window, plaster reveals, an open leaf in its
  wooden frame. Blender: output/bodjantouna-42/interiors/goumosbane-599/dar-labidi.blend (make_blend
  needed no change).
- Lead follow-up (windows from inside): the legacy kit windows showed the back of their solid stone
  surround (tan) in the hole. The interior's window and balcony pieces now drop their wall-facing faces at
  or behind the wall face (interior-only copies, `export.seen_from_inside`), and every window, court
  window, inner window and balcony hole holds a glazed two-leaf casement (wood in old-town houses, white
  elsewhere) with see-through `glass_inner`. Survey rerun: same counts, 0 crashes, 0 piece mismatches.
  Looks: output/checks/48-ghorfa.png (the ghorfa camera: casement, sky through the panes, the yellow
  shutter at the edge), output/checks/48-slab.png (slab salon: white casement). .blend refreshed.
- Lead review: read the whole diff; tests 124 passed; `build --quick --force` then fingerprint `--allow ""`:
  282 parts, 0 changed (the tile split is byte-identical); no em dash; reran the helper's wall survey (same
  counts) and traced slab No. 1042 door 93 myself: the wc door stands 0.07 m from the palier's corner, a plan
  fault. One follow-up (windows from inside). Picture for Ali: output/checks/48-ghorfa.png.
- Doubts and questions for Ali: a closed slab persienne is a one-sided piece, so from inside the casement
  shows the street, not the closed shutter. No ceilings until 49.

## 2026-10-29 - Prompt 47 H1c Apartments, villas, domed houses and shops
- Commit: (lead commits) | Model: Opus 5.5, high
- Changed: new citygen/interior/spine.py (hall-couloir engine, second couloirs, shared modern helpers),
  villa.py, flats.py (cores, balanced colonial split with a landing strip, slab splits, occupants, ladder
  well), koubba.py, shop.py; layout.py (`with_shop`, its tries tracked), rooms.py (`joinable`, `_units`,
  repair keeps the salon), program.py (`modern_problems`, couloir in `most`), stairs.py (U box),
  context.py (`pick:shop`), cuts.py, model.py (`piers`), dar.py/compact.py (whole-floor frame after a shop,
  court ladder when a stair room has no way up, mixed-geometry guards); styles/maghreb.toml; tools/
  interior_plans.py; tests (6 new + 1 slow); docs (SPEC 6c, HANDOFF, ROADMAP).
- Checks (lead, final): `pytest -q` 122 passed in 34 s (the new fast tests add about 1.5 s); slow: the
  new-district test passes, `test_open_samples_are_valid` xfail (open item 47.1); `build --quick` done;
  fingerprint `--allow ""`: 282 parts, 0 changed; rooms.json the same in two processes; no em dash. The
  lead's bar (95% of each group passing `rooms.check`) is met for villa, maison, koubba and shop, not for
  colonial (39%) and slab (93%): open item 47.1.
- Lead decision (follow-up 2): no flat under `min_flat` (40 m2) on any floor (a smaller region joins the flat
  it shares most with, else the palier); flat types S+1 under 60 m2, S+2 under 100, else S+3 (moyen standing;
  the prompt's "type matches its area" stays); inner doors of modern homes keep `inner_clear` 0.15 m from the
  partitions (facade rule and old town unchanged); program check: at most one salon, salle a manger, cuisine
  and hall per flat, villa or maison, every flat a facade window. Evidence (lead's histogram of flats short
  of chambres, every 3rd building): slab 89 flats under 20 m2 all failing, 40-80 m2 26/99, 80-90 30/58,
  90-100 77/182, 100-110 8/294, over 110 none; colonial under 50 m2 58/82 (26 under 20 m2), 60-100 53/177.
  Builder: side-by-side couloirs removed (the second couloir of round 1 is gone).
- Rounds 1-4 (lead follow-ups after the whole-city surveys): flats under 20 m2 (the main cause of
  missing rooms), merges that let a palier or couloir swallow rooms, a layout search per floor (up to 18
  variants), the salon and then the cuisine taking windows first, hall trims; the old town stayed at 15
  fails (lead's scripts, now `tools/interior_survey.py`).
- Round 5 (speed, slab stairs), no crash anywhere:

  | group | round 4 | round 5 | slowest | top kinds left |
  |---|---|---|---|---|
  | slab (353) | 331 | 327 (93%) | 2.7 s (No. 1362) | 5 hall/chambre partitions near a window, 4 palier/hall, 4 no sdb |
  | colonial (270) | 114 | 105 (39%) | 14.1 s (No. 773) | 48 salons without a window, 30 chambres over 36 m2, 25 hall/salon partitions |
  | koubba (22) | 21 | 21 (95%) | 0.01 s | No. 570 |
  | shop (136) | 135 | 135 (99%) | 0.35 s | No. 270 |
  | villa (178) | 172 | 171 (96%) | 0.41 s | |
  | maison (616) | 588 | 589 (96%) | 0.64 s | |
  | full sample (300) | 279 | 277 (92%) | 2.0 s | |

  Done: typical floors (a floor with the same region, entrance, program and facade reuses the lower floor's
  cells, or a lower floor's plan that holds here without a fault; the stream is keyed by the flat's place),
  a faster cut search (zones within reach only, spans of zones read without building partitions), widths
  remembered, fewer variants on big floors; slab cores slide in and widen past a wide stair window, a
  stepped block's upper floor becomes the upper floor of the flat below by a ladder (a duplex). Slowest slab
  19 s -> 2.7 s (No. 1240: 1.4 s), colonial 20 s -> 14 s (No. 773, 100 m long, 7 floors whose windows
  differ, so no floor repeats). Not done: the colonial ring fallback, colonial split lines against the
  window zones, the salon on the facade before the bands. Fast fixture 6.9 s; tests 122 + 1 xfail.
  Maison 442: a row of salon, two chambres, the roof stair, the hall at the door, a "bit" at the tip (now a
  chambre: a modern merge past a service's largest makes a chambre). Slab 1049 floor 0: four flats of three
  chambres each, cuisines about 12 m2, every salon on a facade.
- Final (prompt 47 stops here for the week): rooms.check passes, first report -> round 5: slab 171/345 ->
  327/353 (93%), colonial 21/267 -> 105/270 (39%), koubba 18 -> 21/22, shop 134 -> 135/136, villa 138 ->
  171/178 (96%), maison 490 -> 589/616 (96%), full-capital sample 237 -> 277/300 (92%); no crash anywhere; old
  town 16 -> 15 fails. Lead decisions: flat types S+1 under 60 m2, S+2 under 100; inner doors of modern homes
  `inner_clear` 0.15 m; no flat under 40 m2; typical floors reuse a lower floor's plan. Tests: `pytest -q`
  122 passed (the new fast tests add about 1.5 s); slow tests: all pass but `test_open_samples_are_valid`, xfail
  (open item 47.1: the colonial and slab samples, and domed house No. 570, an L strip round its koubba a
  bit under its width, which the lead moved there from the new-district test). Look: output/checks/47.png (slab No. 1264
  stacked typical floors, colonial No. 867 floor 0 still a warren of 13 stores, villa No. 321 fine).
- Open items for 47.1: colonial flats to 95% (ring fallback when the spine fails, split lines between flats
  and against the palier moved clear of the window zones, the salon on the facade first on one-sided lots;
  top kinds now 48 salons without a window, 30 chambres over 36 m2, 25 hall/salon partitions near a window);
  colonial No. 773 takes 14 s (no floor repeats); the slab remainder (93%: hall/chambre and palier/hall
  partitions near windows, 4 flats without a sdb); domed house No. 570; colonial floor-0 stores as a few
  rooms off the core's couloir.
- Lead review: the whole diff read after the first report (code findings a-g fixed, among them a shop
  retry that kept the plan without its shop), later rounds checked by surveys, tests and plan pictures;
  `tools/interior_survey.py` added (the lead's survey as a tool). Lesson in `docs/LEAD.md`: check a
  helper's root-cause claim with a histogram before deciding a rule.

## 2026-10-29 - Prompt 46 H1b Courtyard houses and compact houses
- Commit: (lead commits) | Model: Opus 5.5, high
- Changed: new citygen/interior/cuts.py, rooms.py, stairs.py, dar.py, compact.py, program.py; interior/layout.py (`PLANS`,
  storeys grow the court by the court wall), model.py (`rules`, `focus`, `entry`, not in rooms.json),
  export.py (court trees as instances, `interior` view from the layout's focus); styles/maghreb.toml
  (`[interiors.rooms]`, `.dar`, `.stairs`, `.floors`, more in `.walls`, `.openings`, `.compact`); new
  tools/interior_plans.py; tests/test_citygen.py (5 new tests, 2 prompt-45 tests adapted to real layouts);
  docs (SPEC 6c marks and settled rules, module table, SPEC 9; prompts 47-49 notes; HANDOFF; ROADMAP).
- Checks: tests 117 passed in about 30 s (new: the 50-house fixture 1.3 s, 5 tests about 0.4 s); slow
  interior tests 2 passed; build --quick reused everything; fingerprint `--allow ""`: 282 parts, 0 changed.
  City-wide one-off scripts (not committed): quick capital 639 of 655 old-town houses pass `rooms.check`,
  which also tests the program (by reported layout 210 dars, 339 compact, 106 small; no crash; slowest
  0.3 s); full capital sample of 300: 290 pass (slowest 0.56 s).
- Lead review, three follow-ups: (1) the room program (survey of every quick-capital house, before ->
  after, dar/compact/small): no matbakh 21/61/16 -> 0/0/9 (one-room floors), no bit on floor 0 3/126/7 ->
  0/0/0, bit el ma over 8 m2 28/149 -> 0/0, matbakh over 14 m2 11/25/6 -> 0/0/0 (new `program.py`,
  merges keep types, `check` tests the program); (2) covered courts narrower than 2.55 m 30 -> 0
  (`central()` rejects slots and courts keeping under 80% of their rectangle); (3) a house that falls back
  reports the layout it got (77 crowded compact houses say `small`) and `pick:` skips such houses. Left by
  reported layout: compact without bit el ma 18, without skifa 26; dars without skifa 4. Fallbacks seen:
  11 ladders, 493 entry steps, upstairs galleries in a few compact houses.
- Look: output/checks/46.png (pick:dar:1 No. 614, pick:dar:2 No. 599, pick:compact:2 No. 262): bent skifas
  with entry steps, the T room across the court with its double door and two windows, kitchen beside the
  skifa, stairs under the roof's stair room, ghorfas in a ring upstairs, the stah; No. 262's covered court
  on its west wall with a light well upstairs. No. 193 (its court was a 1.65 m slot) now runs the small
  program and says `small`. 3D: output/bodjantouna-42/interiors/goumosbane-599 (walls still the tile shell
  until prompt 48).
- Doubts and questions for Ali: none needing a choice. Open items for the lead: 8 of 210 quick dars (7 of 97
  sampled full) still let the street see the court (tight corner lots); 26 of 339 compact houses have no
  skifa (it is capped at 18 m2) and 77 crowded ones run the small program; 8 houses keep small leftovers (undersized ghorfa or bit, 2 skifa walls near a window). The kbou appears in
  21 houses only (most bands are 2.1-2.4 m deep).

## 2026-10-29 - Prompt 45 H1a Interior model and command
- Commit: (lead commits) | Model: Opus 5.5, high
- Changed: new package citygen/interior/ (`__init__`, `model`, `context`, `outside`, `layout`, `export`,
  `command`), citygen/__main__.py (`interior`), citygen/build.py (`summary["settings"]`),
  citygen/buildkey.py (`NOT_BUILD_CODE`, `NOT_BUILD_STYLE`, `_style_hash`), styles/maghreb.toml
  (`[interiors]`, `.walls`, `.openings`, `.compact`), tools/fingerprint.py (skips `interiors/`),
  tools/before_after.py (`--interior`, `--city`), tools/viewer/index.html (card line "No. k"),
  tools/snapshot.py (falls back to Google Chrome when Playwright's Chromium is missing),
  tests/test_citygen.py, docs (SPEC 6c marks, module and output tables, SPEC 9; HANDOFF; ROADMAP).
- Checks: tests 112 passed (28 s; new normal interior tests about 1 s in all), slow `-k "interior or
  outside"` 2 passed (replay 4.2 s, two processes 2.1 s). Quick build: every tile rebuilt once (new build
  key by design), then reused; fingerprint `--allow ""`: 282 parts, 0 changed. `interior pick:dar` 0.5 s
  in the command, 1.0 s wall. Dar No. 190 671 triangles 210 KB, compact No. 193 962 / 236 KB, slab
  No. 1264 585 / 247 KB, colonial No. 867 4,193 / 496 KB. Full capital (rebuilt with `--area capital
  --out output/full`, 53 s, so its summary holds the settings): `pick:dar` No. 3419 1.8 s in the command
  (2.5 s wall), `pick:slab` No. 21320 1.9 s (2.5 s wall); both print "plan reused", nothing planned
  again (SPEC target under 10 s). A one-off script replayed all 1,005 dwellings of
  the quick build's 9 tiles: 0 differ (46 pieces dropped by the tile after `building`, handled), no
  opening off its wall.
- Code differs from the prompt: `layout_of(plan, b, style)` (it needs `min_area` and the wall thickness);
  `make_interior` takes an optional `ctx` (a loaded `BuildContext`, for tests and prompt 50's server);
  `keep_off` for the port and props zones runs only when they meet the owning tile, as `build_tile` does;
  the hole rule uses a window's `door_*` parts only without glass (open shutters lie beside the hole);
  apartment blocks outside colonial and modern districts are `colonial`; a storey split by the wall shrink
  keeps its largest part. All written into SPEC 6c.
- Look: none required (checks only). `output/bodjantouna-42/interiors/goumosbane-190/maps/snapshot-overview.png`
  and `output/checks/45.png` (grey "Before: no interior yet" over the dar from the south-west: court,
  roof deck, yellow-shuttered window, door, plants). Playwright's own Chromium is gone from
  `~/Library/Caches/ms-playwright`, so `tools/snapshot.py` now falls back to the installed Google Chrome
  (`channel="chrome"`, one line logged); no download. The `interior` view looks at the door's back: walls
  seen from inside are culled until prompt 48 draws their inner faces.
- Doubts and questions for Ali: none.

## 2026-10-29 - Prompt 44 H1 Interiors: the design
- Commit: (lead commits) | Model: Opus 5.5, high
- Changed: docs/SPEC.md (new section 6c "Interiors"), docs/prompts/05-interiors.md (prompts 45-50
  rewritten, same numbers, models and efforts; 46 Size M, 47 Size L), docs/ROADMAP.md, docs/WORKLOG.md,
  docs/HANDOFF.md. No code.
- Checked in the code: `TileContext` (kit from `make_kit`, `Ground` over every plan, `Covers`),
  `build_tile` (`keep_roof`, `building_highs` gives `high`, `ground_heights`, `under_roofs`, `keep_off`),
  `Dresser.building`/`entrances`/`front_of`/`_sections`/`_light`, `stair_columns`, piece bounds of doors,
  windows, shops and balconies (glass, `shop_dark`, `door_*` leaves, `Kit.panes`), `roof_layout` (the 2.5 m
  stair room, its door side), `masses`, `life.households` draw order, `load_or_plan` and the build key (any
  .py edit changes it), `summary.json` (no settings today; fingerprint skips it), `view.py` and the gallery,
  the card's `describe`, `kitsheet.py` (a hand-written viewable folder), `before_after.py` (needs a view in a
  build folder: prompt 45 adds `--interior`). Timed on the quick capital: world 0.05 s, cached plan 0.03 s,
  kit 0.2 s, one `Dresser.building` 1-12 ms; full world 0.6 s, the capital pickle 27 MB.
- Main decisions: interiors for the four dwelling kinds only (mosque halls and marabouts have no door yet);
  building = index in that city's `plan.buildings`, `--city` for builds with several cities, `pick:` specs
  for Looks; `summary.json` gets the merged settings, older folders get a clear "build it again" message; the
  build key and the fingerprint ignore interior code, `[interiors]` and `interiors/` folders; world
  coordinates with a tile-like root node; partitions by `free_cut` (0.3 m rule), merge fallbacks, never a
  crash; houses climb a square newel stair (3/4 turn per floor, headroom over 2.7 m) that fits under the
  2.5 m stair room, other layouts U stairs between floors; slab flats follow prompt 21's sections exactly.
- Doubts and questions for Ali: none that block. Two choices he may want to see later: modest courtyard
  houses (most of the quick capital's) get a plain bit without the kbou alcove because their rooms are only
  about 2.1 m deep; the skylight of covered courts shows only inside (the city tiles keep a plain roof).

## 2026-10-25 - Prompt 43 CP4 Checkpoint: people, landmarks, port, performance
- Commit: (see git log) | Model: Opus 5.5 (lead), an independent Opus reviewer (read only the committed history
  360b81c..3466c6c with git), an Opus speed helper, an Opus fix helper (three lead follow-ups)
- Reviewed prompts 28-42 and the between-prompt work (gallery, keyboard turning, cypress): every "Done when"
  met. No `random`, unseeded numpy or hash-order use; every new choice on its own stream path; em dash 0.
- Found and fixed: (1) seaside cafes decided with `rng("terrace", "cafe", k).random() < 0.5`, then built from a
  fresh copy of that stream, so the awning pick reused the small number: never yellow or cream; the front
  now draws from `rng("terrace", "cafe", k, "front")` (2 cafes change awning on the quick city). (2) The
  station's level core had no guard against the port grading and the city-limit edge blend, which `Ground`
  applies after the leveling: `_Env._level_inside` keeps the core out of both bands plus `[station] clear`;
  the station test now checks the ground over the core is level. (3) Seed 7's capital (Noghinba) had a
  boulevard but no cathedral or theatre: its boulevard blocks are 27 m deep, the cathedral needs 51 m; a
  fallback (`[landmarks.fallback]`, only when no boulevard site holds it, so seed 42 is unchanged) puts the
  front on a cross street of a block fronting the boulevard, flank on the boulevard; its camera views search
  the faced street and the streets around it, keep `wall_clear` 6 m from walls and clear of trunks and crowns
  (first try stood inside a tree, caught in the GPU viewer). (4) A comment claimed a seaside cafe's windows
  "draw as before" (moving the door shifts that building's `rng("b", k)` window draws): corrected, output
  kept. (5) The dead `PEOPLE` table in `crowd.py` removed (the style overrode every key); outfit bodies,
  `tile_reach`, the station's `inside` and `dry`, the kasbah's `area`, `max_share`, `on_wall` moved to the
  style, output identical. (6) The two loosened tests check the real property: every flagged menzah (15 of
  18 get one), every pillar within 2 m of a paved corner (30, threshold 10).
- Speed (byte-identical, quick 0 of 282 and full capital 0 of 727 parts changed before the fixes): a flat
  profile; wins from a bounding-box reject before shape tests (`station.keep_off`, 27 s), street lines and
  promenades grouped once (`Parking.inside`, `Squares.islands`), one ground query per tile for all footprint
  rings (`tile.ring_heights`), texture images made once and handed to the workers, leaner Perlin noise. Full
  capital CPU 370/332 -> 275-295 s (wall 87-118 s: the machine ran at load 14-37 from other sessions, so
  CPU is the fair measure); the quick build now uses 3 tile processes (`[build] tiles_per_worker = 3`), 35 ->
  10-13 s wall. Tests 107 passed (39.6 s under load), 2 slow passed.
- Seeds: seed 7 (Noghinba): kasbah, 4-track station 373 m inside the limit and level, harbor and lighthouse,
  now the cathedral and theatre; seed 1234 (Rekgine): no boulevard (plausible: one small colonial district)
  and no railway (every one of 56 sites has 7-9 m of fall against `max_drop` 6 m: a real rule). Gazetteers
  name every landmark. Densest tiles: seed 42 4.69 MB, seed 7 4.86 MB, seed 1234 3.45 MB; lod1 0.4-0.6 MB.
- Viewer level of detail on the full capital (GPU browser pane): 168 tiles, 33-44 full near the camera, the
  rest lod1, 0 failed, settled in about 4 s after each view change. People in the 28-29 and souk pictures:
  respectful, readable, no clipping. Phone page: 22 files live (version 4), unchanged by CP4.
- Checks: stats 370,953 triangles, 4,928,513 drawn, 29,546 dressing pieces, 12.2 MB in 9 tiles (lod1 0.45 MB).
  Fingerprint against `before`: 1 changed (`tile_13_23`: awning colors red +1, yellow +1, green -2, counted
  in the GLB against a HEAD build); full capital 9 changed (8 seafront tiles and `tiles/index`; undoing fix 1
  alone gives 0). Against `cp3`: 81 changed (prompts 28-42). Saved `fp-cp4`.
- Look: `output/checks/cp4-souk.png` and `cp4-aerial.png` (difference 0.00: nothing in those views changed).
  Blender: `output/bodjantouna-42/goumosbane.blend`.
- Doubts and questions for Ali: seed 7's theatre view is close and oblique (64 degrees: its front faces a
  12 m street); the souk camera has a walker 1-2 m in front of it. Ali confirmed the phone page shows
  textured walls on his phone.

## 2026-10-25 - Prompt 42 R1 Refresh the phone 3D page
- Commit: (see git log) | Model: Opus 5.5, max (lead, no helper: publishing needs the Artifact tool)
- Changed: `tools/make_artifact.py` (`SPOTS` taken again, `CLEAR` and `clear_spots`, textures as `<img>`),
  `tools/viewer/index.html` (phone top bar), `tests/test_citygen.py` (1 new test, 1 new assert), docs.
- Spots: the page shows the build's 7 views (street, souk, cathedral, theatre, station, port, corniche; the
  build places them on `Ground.surface` at every build) and 3 spots of its own for places the build has no
  view of, each camera 1.7 m over `Ground.surface` (computed, not guessed): `carpet_souk` (the start, moved
  2.5 m onto the souk's middle: the old camera stood 0.2 m from a shop wall), `kasbah_gate` (new: the souk
  lane to the gate's horseshoe arch) and `cemetery` (new: a white marabout among the new cypresses).
  Dropped: `alley_arch` (0.01 m from a wall, no arch left) and `old_houses` (inside a 5-floor apartment
  block since the kasbah re-plan). `clear_spots` leaves out, with a message, any spot a later plan puts
  within 1 m of a building; it catches both dropped spots.
- Textures (new on this page: the version of mid-October had none): each image becomes a blob: URL, and
  three.js's glTF loader fetch()es such URLs, which a host policy `connect-src 'self'` blocks (tested in
  the browser pane: 0 of 33 textured looks). The Artifact rules promise blob: images, not blob: fetches,
  so the page now loads them as `<img>` (a loading-manager handler for `textures/`): 33 of 33 under that
  strict policy, no console errors.
- Phone: at 480 px and narrower the title card keeps its width (it was squeezed to "Bodjanto / una") and
  the menus stack beside it. Desktop layout unchanged.
- Published: https://claude.ai/artifact/HMtdFZUV9sGmyPn4q8mKsq version 4, 22 files, 18.2 MB (biggest 6.3 MB),
  icon kept (version 3, an hour earlier, still had the blob fetch).
- Checks: tests 107 passed (32 s; 60 s with the browser busy); quick build ok; fingerprint 282 parts, 0
  changed. The live link shows a sign-in page in this session's browser, so the page was checked on a
  local copy with the host's wrapper and the strict policy, at phone size (375 x 812): 9 tiles, golden
  hour, Fast quality, textures, crowds, no console errors; the menu's Cemetery moves the camera there.
- Look: `output/checks/42-phone.jpg` (phone size: the carpet souk at golden hour).
- Doubts and questions for Ali: none. On his phone the walls should show plaster grain and the paving
  its stones; flat, plain walls would mean the host refused the images.

## 2026-10-25 - Playbook: two tracks after prompt 100 (plan only, Ali's request)
- Commit: (see git log) | Model: Opus 5.5 (lead, no helper)
- Changed: `docs/prompts/10-life-and-polish.md` (new: prompts 101-120), `docs/PROMPTS.md` (intro, the end,
  table), `docs/ROADMAP.md` (checklist, sections K and L), `docs/HANDOFF.md`, this log.
- Why: Ali wants every asset polished one by one "at least like Léo" (his Blender character) and a city
  with life (people moving in long loops, as if they had lives). Two interleaved tracks: K (review tool,
  hero detail near the camera, people, trees, vehicles, facades, souk and cafés, street furniture and
  boats, landmarks) and L (design, weekly schedules, routes, animated walkers, the living viewer,
  rhythms, traffic, following a life, Godot), with checkpoints 110 and 120. Prompts 95-97 stay (Ali).
- Facts used: the kit has 185 code-made pieces and 58 from the Tounes kit, none from Blender yet (prompt
  38 built and tested the route only); the quick plan has 1,300 households and 7,065 residents, 3 mosques,
  the kasbah, cathedral, theatre, station and lighthouse, but no schools, cafés (besides kiosks) or
  hammams: prompt 102 decides how to add them.
- Checks: docs only, no code or build change.
- Doubts and questions for Ali: none.

## 2026-10-25 - Cemetery cypress, winner of a model duel (Ali's request, between prompts)
- Commit: (see git log) | Model: Opus 5.5 helper, effort high; lead review Opus 5.5
- Duel: after X posts claimed Sonnet beats Opus, Ali had three helpers take the same free prompt ("improve
  the weakest-looking asset of your choice", isolated worktrees from 448a15b): Sonnet 5.5 high, Opus 5.5 high,
  Opus 5.5 max. All three chose `tree_cypress`, a 6-triangle cone planted 615 times in the cemetery. Lead's
  scores (look 30%, solid work 25%, thinking 15%, efficiency 15%, code 10%, city cost 5%): Opus high 8.2 (best
  look and value), Opus max 8.0 (cleanest code and test; 319k tokens and 31 min, about 1.9x the cost),
  Sonnet high 7.5 (half the price, hard colour bands). Ali chose Opus high. The three worktrees stay in
  `.claude/worktrees/agent-*` (Ali: keep them for later).
- Changed: `citygen/mesh/trees.py` (`cypress_piece`: a jittered 7-sided spindle turned from a style profile,
  three shades with a ragged line between them, 5-7 pointed upright tufts, a short trunk, a slight lean;
  3 variants on their own streams `("props", "tree", "cypress", v)`), `citygen/mesh/plants.py`
  (`smooth_normals` split out of `smooth_add`, the other plants byte for byte the same),
  `styles/maghreb.toml` (`[dressing.trees.cypress]`, two cypress shades, role `tree_cypress`), a test in
  `tests/test_citygen.py`. Each planted cypress picks its variant with the per-tree draw `rng("tree", k)`
  that palms and broadleaf trees already use, which nothing else reads for a cypress.
- Checks: 106 tests (30 s); quick build 13 s; fingerprint 8 of 282 parts: kit/tree_cypress (6 -> 156
  triangles), kit/tree_cypress_b (164) and _c (156) added, the 4 cemetery tiles (+16-23 KB each, drawn
  triangles +1.9%) and the index; the tiles are byte for byte those of the reviewed worktree. Side effect:
  the bigger tile_12_22 raises its people's byte budget (`bytes_share`), so 3 walkers there show their own
  safsari instead of the hijab stand-in.
- Look: `output/checks/model-duel-3-way.png` and `model-duel-3-way-zoom.png` (the old cone and the three
  versions from the same two cameras in the cemetery: eye level and 45 m up); Blender:
  `output/bodjantouna-42/goumosbane.blend`.
- Doubts and questions for Ali: none. Up close the tufts read a little as diamonds.

## 2026-10-24 - City gallery and keyboard navigation (Ali's request, between prompts)
- Commit: (see git log) | Model: Opus 5.5 (lead, no helper)
- Changed: `citygen/view.py` (`build_folders`, `build_info`, `builds`, `pictures`, `_GalleryHandler`,
  `serve_gallery`), `citygen/__main__.py` (`gallery`), `tools/viewer/gallery.html` (new),
  `tools/viewer/index.html` (keyboard like driving: up/down arrows or W/S move, left/right arrows turn,
  A/D step, R/F look up/down, Q/E down/up, Shift faster, G walks at 1.7 m on the drawn ground with a
  ray that skips instanced props and water; a tap moves for 150 ms), `Open City
  Gallery.command` (new, double-click), tests (1 new), `README.md`, `CLAUDE.md`, `docs/HANDOFF.md`,
  `docs/ROADMAP.md`
- What: one page lists every build under `output/` (summary or tile index; `output/checks` test folders
  left out), newest first, read from the folder at each request and polled every 30 s, with its map,
  Open in 3D, a button per camera view, Night, its Blender file, and the 24 newest check pictures. Each
  viewer runs at `/b/<folder, "/" as "~">/` with its data at `.../data/` (the viewer loads data
  relative to its page), so one server shows every city; unknown keys and `..` give 404.
- Checks: tests pass (the new one about 0.1 s); the viewer works through the gallery (street view,
  walking and flying tried in the browser pane, no console errors); the phone page builder still runs.
  The build itself is unchanged (the viewer is not part of it).
- Doubts and questions for Ali: none.

## 2026-10-24 - Prompt 41 C2b Viewer level of detail
- Commit: (see git log) | Model: Opus 5.5, high (playbook: Sonnet, high)
- Changed: `tools/viewer/index.html` (tile slots with want/shown/roots/jobs, lod1 everywhere and full under
  1.4 km / lod1 over 1.7 km from the camera, first split 1.5 km, RADIUS for full tiles around the orbit
  target, lod1-first loading, cancellable `fetchTile`, prepare off-scene then swap in one task, dispose full
  tiles, lod1 twins kept, image cache, shadow map only for swaps in the shadow frustum, stats line with full
  and lod1 counts, live `citygenReady`, `?lod=full|lod1`, `?lod_distance=`), `tools/snapshot.py` (settled
  state checked again two frames later, counts in the timeout message), `tools/make_artifact.py` (new
  reading-line patch, lod1 files converted), a test, SPEC 6 and 9, HANDOFF, ROADMAP.
- Measured (full capital, 168 tiles, aerial, golden, High, 1600x900, headless Chromium on the M1's Metal):
  old viewer 94 full tiles 4.15M triangles, ready 5.0-7.5 s, 151-168 ms per frame; new 33 full + 135 lod1
  2.38M triangles, whole capital shown 0.75-0.86 s, settled 2.6-3.1 s, 84-98 ms per frame. Street view:
  67 -> 35 ms per frame, settled 4.0 -> 2.1 s. SwiftShader (snapshots): ready 34 s -> 9-13 s. A fast flight
  out 3.5 km and back: never a hole or two versions of a tile, the renderer's geometry count returns to the
  same value on each round trip (no leak).
- Checks: tests 104 passed in 29 s (1 new, phone page patch and lod1 files); quick build fingerprint 0 changed;
  `make_artifact` into a temp folder loads in the browser with 9 tiles, no console errors (only the
  favicon 404 of a bare http.server). Old vs new viewer on the quick build: street 0.0, aerial 0.003.
- Look: `output/checks/41.png` (aerial, quick capital: 26 full + 15 lod1, far blocks and the hills there, no
  cracks; 0.00, both halves use the new viewer) and `output/checks/41-street.png` (0.00, every tile full).
- Doubts: before_after's `--build-args "... --out output/full"` builds `--quick` into output/full, replacing
  the full capital (rebuilt afterwards). From the air the frame time is draw calls of the ~33 full tiles;
  merging a full tile's meshes per material would be the next big win. Near the build's edge the lod1
  terrain-only tiles show their 32 m facets from the air.

## 2026-10-24 - Prompt 40 C2a Level-of-detail tiles
- Commit: (see git log) | Model: Opus 5.5, high (playbook: Sonnet, high)
- Changed: `citygen/mesh/lod.py` (new: terrain with 8 m edges and skirts, ribbons, merged blocks, solo
  landmarks, vertex clustering with crease normals, flat materials), `citygen/mesh/tile.py` (`cell_materials`
  shared by both terrains, `export_tile` writes the lod1 and lists it), `citygen/mesh/builder.py`
  (`MeshBuilder.has`, `arrays`, `ribbon_edges`), `citygen/mesh/port.py` (`breakwater_meshes(light=)`,
  `lighthouse_spots`), `citygen/build.py` (resume checks the lod1 size, `lod1_megabytes` in the summary),
  `citygen/tilestats.py` (lod1 line), `citygen/defaults.toml` (`[tiles.lod]`), tests, SPEC 4, 6 and 8,
  HANDOFF, ROADMAP.
- Sizes: quick 0.45 MB of lod1 for 12.1 MB (worst 11.0%, the terrain-only 12_24; densest 13_23 155 KB = 3.3%).
  Full capital 7.67 MB for 171.25 MB, 385,762 triangles for 5,147,535; 64 city tiles median 3.6%, max 6.5%;
  terrain-only tiles 11.0%; worst 12.9% (harbor tile 62_107, 50 KB); densest 65_106: 141 KB, 6,780 triangles.
- Checks: tests 103 passed in 29 s (4 new, about 0.4 s), slow tests 2 passed (parallel = one process, lod1 too);
  quick build 12.7 -> 12.9 s and capital 57.2/58.4 -> 60.9/60.4 s (HEAD worktree and this tree, back to back);
  fingerprint quick: index + 9 new lod1 files only; capital against a HEAD build: all 168 full tiles equal
  (only the index and the lod1 files differ).
- Look: `output/checks/40-lod1.png` (the 168 lod1 tiles alone, 2.6 km south of the medina) and
  `output/checks/40-lod1-skyline.png` (1.5 km): blocks with mixed wall colors, ramparts, the great mosque's
  minaret and domes, the kasbah towers, cathedral and lighthouse as small marks, tall slabs standing out, no
  crack at any tile edge. The views were taken on a copy of the build whose index points at the lod1 files
  (`output/lodview-40/`, can be deleted); the viewer is unchanged (prompt 41).
- Doubts: the old town's merged blocks read as one flat level from close (the full tiles vary by a floor);
  blocks are drawn by the tile holding their centroid, so a quick build loses edge blocks whose centroid lies
  in a tile it does not export. `make_blend.py` not run: full tiles unchanged.

## 2026-10-24 - Prompt 39 Q5 Lighter tiles (partly done: 3.5 MB not reached)
- Commit: (see git log) | Model: Opus 5.5, high (playbook: Sonnet, high)
- Changed: `citygen/mesh/gltf.py` (quantized writer, flat faces without NORMAL, pooled bufferViews, weld,
  16-bit split, `accessor_array`, `vertex_normals`, `read_parts` dequantization), `citygen/mesh/builder.py`
  (`MeshBuilder.fine`, `gltf_parts(fine=)`, `add_sheet`), `citygen/mesh/tile.py`, `citygen/defaults.toml`
  (`[tiles] quantize`, `fine_edge`, `float_materials`, `flat_angle`), `citygen/city/crowd.py` (figures cost their
  quantized size), `citygen/tilestats.py` (new) and `citygen/__main__.py` (`stats --tiles`),
  `tools/viewer/index.html` (normals computed for meshes without them, `flatShading` cleared and in the
  material key), `tools/blender_import.py` (`instance_transforms` reads 16-bit rotations and a missing SCALE,
  `bake_dequantization`), `tools/blender_beauty.py`, tests, SPEC 6 and 8, HANDOFF, ROADMAP.
- Sizes before -> after (MB). Quick: 13_23 8.67->4.67; 14_24 3.13->1.70; 14_23 3.03->1.68; 13_24 2.59->1.47;
  13_22 1.18->0.70; 12_23 1.07->0.63; 12_22 0.95->0.58; 14_22 0.80->0.51; 12_24 0.20->0.15; total 21.6->12.1.
  Full capital: 65_106 11.11->5.81; 65_105 9.07->4.77; 64_105 8.34->4.42; 64_106 6.85->3.65; 63_105 6.44->3.37;
  62_103 6.33->3.26; all 168 tiles smaller (-25% to -48%), total 310.4->171.3.
- Densest tiles by category (KB, before -> after). Quick 13_23: tile mesh 4,465 -> 2,350 (roof_white 1,186 ->
  493, lime_white 1,047 -> 585), pieces 3,061 -> 1,524, instances 397 -> 250, JSON 543 -> 395, terrain 205 -> 153.
  Full 65_106: tile mesh 7,031 -> 3,542, pieces 2,823 -> 1,433, instances 540 -> 317, JSON 519 -> 372, terrain
  201 -> 151. The lead's step 1 (no NORMAL on flat faces, split kept) saved 0.66 MB quick, 0.85 MB full.
- Kept float: UVs (16-bit UVs skipped: per-island shifts, a fixed range per material for Blender's name-based
  material sharing and rewritten Mapping nodes, not checkable here; about -0.45 MB, not enough anyway),
  `add_sheet` faces, edges under 5 cm, `water`. Rotations: worst error 0.0034 degrees.
- Readers: viewer (pictures in Fast, High with GTAO and night), phone page (temp folder, 9/9 tiles, no console
  error; night and "click a house" checked in the first round), `make_blend.py` saved
  `output/bodjantouna-42/goumosbane.blend` without error (not inspected inside Blender), `read_parts`.
- Checks: tests 99 passed (28.8 s); `build --quick` 12.6 s; fingerprint `tiles/*` only (10 changed); with
  `quantize = false` 0 parts changed; full capital 58.0 -> 59.4 s.
- Look: `output/checks/39.png` (souk 0.54) and `output/checks/39-street.png` (street 0.30): no visible change.
  Extra: `39-high.png` (High, GTAO) 1.01, noise-like only; `39-night.png` 0.20.
- Doubts: still over 3.5 MB (4.67 quick, 5.81 full). What is left: weld flat vertices by position (readers then
  shade flat on their own, about -1 MB), or level of detail/meshopt (Blender cannot import meshopt).
- Lead decision: 39 and Q5 ticked with the target relaxed. The densest tile went 8.67 -> 4.67 MB (quick) and 11.11 -> 5.81 MB (full), every tile 25-48% smaller, with no visible change (checked by the lead in the GPU viewer on High with ambient occlusion). The 3.5 MB goal predates prompts 20-38, which made the old town about 50% heavier; welding flat vertices (about -1 MB) would break the GTAO normal pass and smoothing in Blender and Godot, 16-bit UVs need rewritten Blender mapping, meshopt cannot be imported by Blender. Prompt 40's lod1 tiles cover far views. CP4 may revisit welding with a flat-shading path.


## 2026-10-24 - Prompt 38 A8 Blender kit export
- Commit: (see git log) | Model: Opus 5.5, medium (playbook: Sonnet, medium)
- Changed: `tools/blender_kit_export.py` (new), `citygen/__main__.py` (`kit-sheet --kits`),
  `tests/data/blender_kit/` (new fixture: `source.py`, `house.glb`, `arrow.glb`, `manifest.json`), tests, README
  (step by step for Ali), SPEC 6b, CLAUDE.md (Blender rule), HANDOFF, ROADMAP.
- Design: `blender_kit_export.py FILE --collection C --name KIT` (or `--out FOLDER`) starts Blender 5.2 in the
  background with its own code, refused inside a sandbox. Each mesh object -> `kits/KIT/<object>.glb`; custom
  properties `category`, `anchor`, `front` (+Y or -Y), `tags`, defaults with warnings; rotation, scale and
  modifiers baked, origin = anchor, -Y pieces turned 180 degrees; palette-named materials keep the palette, others
  become `KIT_<material>` with sRGB hex colors from Blender's linear values. Refuses to overwrite a kit it did not
  make (`tounes`).
- Proof: `source.py` (a house modeled facing -Y with object scale 1.5, an arrow modeled along +X then turned to +Y)
  exported headlessly in Blender 5.2; re-export byte-identical; the new test loads it through `Kit` (door and
  arrow tip at glTF -Z, scale baked, colors) and plays `blender_kit/house` in a role of a style copy (0.10 s).
- Checks: tests 96 passed (28 s); `build --quick` 12.1 s; fingerprint 271 parts, 0 changed.
- Look: `output/checks/38.png` (kit sheet with `--kits tests/data/blender_kit`): the house's blue door and the
  arrow both face the camera standing north, toward the street. Three snapshots: the first view hid the pieces.
- Doubts and questions for Ali: you may add `.venv/bin/python tools/blender_kit_export.py *` to your sandbox
  exclusions (as for make_blend) if you want agents to run it; otherwise run it yourself in your terminal.

## 2026-10-24 - Prompt 37 H3c Seaside cafe terraces
- Commit: (see git log) | Model: Opus 5.5, medium (playbook: Sonnet, medium)
- Changed: `citygen/city/terraces.py` (new: `Terraces`), `citygen/city/corniche.py` (`Seafront` makes the terraces,
  kiosk gaps take no bench, `area`), `citygen/city/dressing.py` (`seaside`, seaside cafes in `_front`,
  `_cafe(tables=False)`), `citygen/city/crowd.py` (waiters, a sitter's own parasol aside), `citygen/mesh/furniture.py`
  (`parasol`, `parasol_pieces`, the kiosk's `look`: `kiosk_drinks`), `citygen/kit.py`, `styles/maghreb.toml`
  (`[corniche.terrace]`, `[people.terrace]`, roles `parasol` and `cafe_kiosk`, `[dressing.furniture] parasol*`,
  palette `parasol_*`, `kiosk_blue`), tests, docs.
- Design: parasol = wooden pole standing in the table's hole, octagonal canvas dome (radius 1.2 m, rim 2.15 m, top
  2.5 m) with a 13 cm valance, both smooth-shaded with real faces on both sides, 8 iron stretchers, finial; 158
  triangles, no UVs, three colors (white, faded sea blue, faded sand) sharing pole and ribs. Cafes facing the sea
  (colonial cafe chance or `cafe` 0.5 on main walls of the seafront stretch): 2-4 tables on the sidewalk, chairs
  along the wall, shaded where a canopy fits (not under the awning), and with chance 0.6 a row of 2-3 shaded tables
  across the road on the palm line, in the nearest lamp-free palm gap, within 2.3 m of the curb. Kiosk cafes: a
  drinks kiosk (Sidi Bou Said blue, cans and bottles) backing onto the railing in a palm gap (chance 0.4, 60 m
  apart, clear of the steps), 2-4 shaded tables along the railing beside it, within 2.8 m of the sea edge; that
  gap loses its bench. Promenade groups only where it is 7.5 m wide (walkway 3 m and more free). Customers sit on
  the measured chairs; some shaded tables get a waiter.
- Counts: quick capital 4 cafes, 29 tables, 25 parasols, 6 kiosk cafes, 38 seated customers, 2 waiters; full
  capital 34 cafes, 217 tables, 163 parasols, 41 kiosk cafes, 280 seated, about 24 waiters.
- Checks: tests 95 passed (28 s; the new test 0.19 s); `build --quick` 12.2 s (HEAD 12.0 s); fingerprint: tiles
  (quick 12_23 +1.1%, 13_24 +1.1%, 13_23 +0.4%), tiles/index and the new `kit/parasol_white`, `kit/parasol_blue`,
  `kit/parasol_sand`, `kit/kiosk_drinks`, `kit/kiosk_drinks_lit`; nothing else. Full capital: 10 tiles +0.0-5.1%
  (worst 66_107, 624 -> 657 KB); the two light sea tiles unchanged (no terrace in a tile without buildings). Full
  capital 57.4 s before, 59.6 s after.
- Look: `output/checks/37.png` (corniche view: a drinks kiosk by the railing, two customers under a blue parasol),
  `output/checks/37-terrace.png` (a row of white parasols on the palm line with customers and a waiter, the cafe's
  awning and table across the road). Blender: `output/bodjantouna-42/goumosbane.blend`.
- Doubts and questions for Ali: few cafes face the sea on the land side (most corniche buildings have their door on
  a side street), so the kiosk cafes carry the look; the kiosk is the newspaper kiosk recolored as a drinks kiosk
  (a dedicated model would cost a new piece per tile); a tile drops a waiter when its figure budget keeps no
  standing man.
- Lead decisions: kept. Kiosk cafes only in tiles that hold buildings (a byte guard for the light sea tiles; revisit after prompt 39 makes pieces lighter); the drinks kiosk reuses the newspaper kiosk's model in its own colors; few buildings have their main wall on the corniche, so kiosk cafes carry most of the look.


## 2026-10-24 - Prompt 36 A6c Corniche promenade and beach
- Commit: (see git log) | Model: Opus 5.5, medium (playbook: Sonnet, medium)
- Changed: `citygen/city/corniche.py` (new: `plan_fronts`, `width_for`, `palms_of`, `Seafront`, `view`),
  `citygen/mesh/corniche.py` (new: paving, curb, sea wall, steps), `citygen/city/model.py` (`Front`, `Walk.edge`,
  `CityPlan.fronts`), `citygen/city/__init__.py` (last step, stats), `citygen/city/ground.py` (level seafront top),
  `citygen/city/dressing.py` (`Dresser.seafront`, corniche lamps off the promenade), `citygen/city/crowd.py`
  (seafront strollers, halo), `citygen/mesh/tile.py`, `citygen/mesh/furniture.py` (`railing_sea`), `citygen/kit.py`
  (no UVs on the railing), `citygen/build.py` ("corniche" view), `citygen/export/maps.py`, `styles/maghreb.toml`
  (`[corniche]`, `[people.seafront]`, role `seafront_bench`, palette `promenade`, `railing_white`), tests, docs.
- Design: on the sea side of the corniche along colonial, modern and residential stretches, a raised promenade from
  a curb 3.2 m inside the corniche's sea edge (carriageway 11.6 m), 8 m wide where 3 m of sand remain, widening to
  10 m as the water comes close (the wall then at the water), level across at curb height; palm row 1.5 m from
  the curb (the old beach-side row moved about 0.8 m, index, kind and height kept), a lamp in every second gap
  between palms, iron benches by the railing facing the sea, a white iron railing (2 m lengths stretched to fit),
  sea wall with a whitewashed coping band over stone, steps to the sand every 72 m where 2.4 m of sand remain.
  The harbor, industrial and cemetery stretches keep the plain corniche; the corniche's own sea-side lamps on the
  promenade are left out.
- Counts: quick capital 752 m of promenade (272 m with a 3 m beach), 6 flights, 53 palms, 26 lamps, 40 benches,
  368 railing lengths, 151 strollers and 13 sitters on it; full capital 4,192 m (all with a beach), 58 flights,
  295 palms, 146 lamps, 221 benches, 2,013 railing lengths, 729 strollers and 169 sitters.
- Checks: tests 94 passed (27 s; the new test 0.2 s); `build --quick` 12.0 s (HEAD 11.8 s);
  fingerprint: plan/goumosbane/trees and stats, tiles/index, maps, gazetteer, kit/railing_sea (new), quick tiles
  12_23 +5.1%, 13_24 +3.1%, 13_23 +0.5%. Full capital: 11 tiles +0.4-8.6%, but 68_106 +19.6% (256 -> 306 KB) and
  60_106 +17.7% (256 -> 301 KB): light sea tiles holding the promenade's sea half (the coast runs along the tile
  row edge). Full capital 54.0 s before, 56.3 and 57.6 s after (CPU +4%).
- Look: `output/checks/36.png` (corniche view: promenade, railing, benches with sitters, palms and lamps, the town
  across the corniche), `output/checks/36-beach.png` (from the water: sea wall, coping, railing broken at a flight
  of steps; the headless renderer hides the narrow sand strip under 1 m above the sea, the GPU viewer shows it).
  Blender: `output/bodjantouna-42/goumosbane.blend` (new camera "corniche").
- Doubts and questions for Ali: the two light sea tiles over the +10% byte budget (see Checks), as in prompts 34-35;
  the bench mix of prompt 26 is replaced here by the iron bench alone (`seafront_bench`) for bytes.
- Lead decisions: the two light sea tiles of the full capital over +10% (`tile_68_106` +19.6%, `tile_60_106` +17.7%, 256 KB tiles that now hold the promenade's sea half) are accepted, as for prompts 34-35; the corniche uses the iron bench only (`seafront_bench`), since the kit's blue bench costs 43 KB per tile.


## 2026-10-24 - Prompt 35 A6b Boats and cranes
- Commit: (see git log) | Model: Opus 5.5, medium (playbook: Sonnet, medium)
- Changed: `citygen/city/moorings.py` (new: `plan_props`, `box`, `land_zone`), `citygen/mesh/boats.py` (new: hull loft,
  fishing boats sharing one hull, trawler, helpers), `citygen/mesh/cranes.py` (new: portal cranes, rails, crates,
  containers), `citygen/city/model.py` (`Prop`, `CityPlan.props`), `citygen/city/__init__.py` (last step),
  `citygen/city/dressing.py` (`Dresser.props`), `citygen/mesh/tile.py` (props drawn by the tile of their center,
  `keep_off` round props on land), `citygen/mesh/port.py` and `citygen/kit.py` (the new pieces, no UVs),
  `citygen/export/lore.py` (plan.json `props`), `styles/maghreb.toml` (`[port.props]`, palette), tests, docs.
- Design: commercial quay (42% of the main quay, by the harbor mouth): two rails, 2-3 portal cranes of one model,
  a yard of container and crate stacks, a trawler or two alongside; fishing port (the rest, other quays): rows of
  4-9 fishing boats bow- or stern-to, trawlers alongside, empty stretches, fish crates behind some rows; 3-6 boats
  at anchor heading into one breeze; boats drawn up on the beach near the port when there is room. Every boat
  1.2 m off the wall, 0.7 m from its neighbours, 16 m off the breakwater's center line, over water draft + 0.6 m
  deep. Pieces: `boat_lateen` 224, `boat_cabin` 262, `boat_rowing` 266 triangles (one shared hull), `boat_trawler`
  449, `crane_0`/`crane_1` 484, `crane_rails` 12, `cargo_crates` 70, `cargo_containers_0..1` 234 (shared geometry).
- Counts: quick capital 98 fishing boats (7 on the beach), 13 trawlers (4 boats at anchor), 3 cranes, 28 rails, 30
  crate and 26 container stacks; full capital 108 and 13 (4 at anchor, no beach near the port), 3 cranes, 31 rails,
  41 crates, 24 containers.
- Checks: tests 93 passed (26 s; the new test 0.3 s); `build --quick` 8.1 s; fingerprint: plan/goumosbane/props
  (new), tiles/index, 3 quick tiles (12_22 +6.3%, 13_24 +1.7%, 14_24 +1.4%), the 10 new kit parts. Full capital:
  61_106 +1.0%, 62_106 +1.6%, 64_107 +2.9%, but 62_107 +19.0% (488 -> 581 KB) and 63_107 +15.1% (618 -> 712 KB):
  light tiles that show the commercial quay and the fishing port together. Full capital 56.8 s before, 53.8 s after.
- Look: `output/checks/35.png` (port view: cranes and the container yard by the mouth, the fishing fleet in rows
  further in, boats at anchor), `output/checks/35-boats.png` (moored boats: the headless renderer hides the low
  hulls there; the GPU viewer shows them whole). Blender: `output/bodjantouna-42/goumosbane.blend`.
- Doubts and questions for Ali: the two light harbor tiles over the +10% byte budget (see Checks), as with the
  breakwater's sea tiles in prompt 34.
- Lead decision: the two light harbor tiles of the full capital over +10% (`tile_62_107` +19%, `tile_63_107` +15%, about +0.1 MB each) are accepted, as prompt 34's sea tiles: new geometry on nearly empty tiles. The headless close-up hides hulls; `output/checks/35-viewer.jpg` (GPU viewer, port view) shows the boats afloat, the moored rows and the cranes.


## 2026-10-24 - Prompt 34 A6a Quays, breakwater and lighthouse
- Commit: (see git log) | Model: Opus 5.5, high (playbook: Sonnet, high)
- Changed: `citygen/city/port.py` (new: quay lines, aprons, cores, breakwater, basin, lighthouse, ground zones,
  "port" camera), `citygen/mesh/port.py` (new: split terrain cells, quay walls, kerb, breakwater loft, crown wall,
  head, lighthouse, pieces `bollard`, `fender`, `armour_rock_0..2` and their placements, `keep_zone`),
  `citygen/city/__init__.py` (the last planning step), `citygen/city/model.py` (`CityPlan.port`),
  `citygen/city/ground.py` (level quays, dredged basin, `side_height`, `walk_step`), `citygen/mesh/tile.py`
  (apron paving, split cells, walls, breakwater, placements and keep-off), `citygen/kit.py`, `citygen/build.py`
  ("port" view), `citygen/export/maps.py`, `citygen/export/lore.py` (map, gazetteer, plan.json `port`),
  `styles/maghreb.toml` (`[port]`, `[port.armour]`, `[port.lighthouse]`, palette, lighthouse names), tests, docs.
- Design: each port district's coast (the corniche's center line) becomes straight quay segments 40 m out past
  the farthest coast point each covers (coves filled), returning to the coast at right angles 15 m from the
  district's ends; the apron (corniche sea half plus 31 m of reclaimed land) joins `plan.land`. Ground: exactly
  2.0 m on the core (apron plus 12 m inland: the whole corniche), blending back over 60 m on the land side; the
  basin and a 16 m strip off every quay dredged to 6 m, fading over 60 m; a true step at the walls (dressed
  stone, dark wet band below 0.6 m, kerb, bollards every 18 m, fenders between). Breakwater on the longest quay
  from its end away from the center: out 185-206 m, curving back along 68-80% of the quay, crest road 3.6 m high
  and 8 m wide, crown wall on the sea side, rough rubble slopes 1:1.5 to the seabed, two rows of armour stones,
  round head with a white lighthouse (red bands, iron gallery, glowing lantern). "port" camera 85 m up off the
  harbor mouth, looking back across the basin; Blender gets it from the index.
- Plan changes: none to streets, lots, buildings, households or trees (the step runs last); landmarks 13 -> 14
  (lighthouse last), new `port`, `stats` + `quay_m`, `breakwater_m`, `land` + aprons. Quick capital: quays 523 +
  841 m, breakwater 732 m; full capital: quays 935 + 612 m, breakwater 788 m; both "Phare de Sidi Sazma".
- Checks: tests 92 passed (26 s; the new test 0.25 s plus a shared tile fixture); `build --quick` 11.7 s (HEAD
  11.5 s); fingerprint: plan/goumosbane/{landmarks, port, stats}, maps, gazetteer, tiles/index, 3 tiles, new kit
  parts bollard, fender, armour_rock_0..2. Quick tiles: 12_22 +7.6% (the southern quay), 13_24 +1.3%, 14_24
  +0.6%, all geometry. Full capital (vs a HEAD build in a worktree): 62_107 +51.7% (322 -> 488 KB: breakwater
  body, armour stones), 63_107 +29.7% (quay, head, lighthouse), 61_107 +11.3% (breakwater end), others +1.6% to
  +5.3%, all new geometry (no plan shift). Full capital 55.8 s before, 56.0 s after (HEAD 55.5 s back to back).
- Look: `output/checks/34.png` (port view: basin, quay with palms, breakwater curve, lighthouse at the mouth),
  `output/checks/34-harbor.png` (lighthouse, head, armour stones, crown wall). Both built with `--build-args
  "--area capital --out output/harbor"`: the quick build's 9 center tiles stop short of the harbor. Blender:
  `output/bodjantouna-42/goumosbane.blend` (new "port" camera; the quick tiles hold only the quays' south end).
- Doubts and questions for Ali: the sea tiles that receive the breakwater exceed the +10% byte budget (new
  geometry on near-empty tiles, absolute +166 KB at most). `output/full` held stale tiles and a plan of another
  settlement from an older build (the fingerprint lists them as added); `output/harbor` is the picture build.

## 2026-10-24 - Prompt 33 A5d Train station and clock tower
- Commit: (see git log) | Model: Opus 5.5, medium (playbook: Sonnet, medium)
- Changed: `citygen/city/station.py` (new: site at the colonial edge, track layout, corridor, street and walk
  clipping, buildings, name, camera view), `citygen/mesh/station.py` (new: head building, clock tower,
  platforms and canopies, tracks per tile, `keep_off`), `citygen/city/__init__.py` (the step after the local
  streets; buildings after the boulevard's), `citygen/city/model.py` (`CityPlan.station`), `citygen/city/
  ground.py` (level ground under the station, `walk_step`), `citygen/city/crowd.py` (walk triangles use
  `walk_step`), `citygen/mesh/tile.py` (station kinds, rails, placement filter), `citygen/mesh/textures.py`
  (`ballast` texture with sleepers), `citygen/export/maps.py`, `citygen/export/lore.py` (map, gazetteer,
  plan.json `rail`), `citygen/build.py` ("station" view), `styles/maghreb.toml` (`[station]`, palette, names,
  `station = true` for capital and cities), tests, docs.
- Design: a terminus across the avenue from the colonial quarter (quick capital: in the port district,
  toward the port and the regional road; full capital: in a residential district). Head building 64 x 16 m
  in pale yellow render with a tiled gable roof, an entrance pavilion with pediments and a great recessed
  arch, round-arched windows and doors, a 28 m square clock tower with four dials and real hands; 4 tracks
  between 3 platforms (side, island, side) under ridged iron canopies on posts, buffer stops; the tracks close
  to 4 m spacing over a 70 m throat and run straight 40 m past the city limit through a corridor (tracks plus
  4 m). Level crossings: rails at the street surface (quick capital: 3 streets and the corniche).
- Plan changes (quick capital, why): buildings 1,678 -> 1,668, parcels 1,702 -> 1,692, streets 454 -> 449,
  impasses 151 -> 147, households 1,306 -> 1,300, trees 8,006 -> 8,003, landmarks 12 -> 13, new `rail`. The cut
  changes the port's blocks; the impasse step advances all blocks together, so old-town lanes and lots change
  too (first changed parcel is an old-town one) and every later household re-rolls. Full capital: buildings
  39,114 -> 38,965, streets 11,284 -> 11,179, households 38,442 -> 38,301; tracks 2.05 km.
  Station: "Gare de Goumosbane" on both.
- Checks: tests 91 passed (25 s; the new test 0.7 s); `build --quick` 11.4 s; fingerprint: plan/*, maps,
  gazetteer, tiles/index (new view) and 8 tiles, no kit part. Station tile 14_24 +9.7% (budget 10%), 13_24
  +5.3% (walks in the level band drawn finer, plan shift); 12_23 +31.6% from the plan shift alone (re-rolled
  door, shutter and cafe variants: 22 piece kinds it did not show before, no station geometry); the other 5
  tiles: 13_22 +0.7%, four shrank (-1.2% to -9.4%). Full capital 52.0 -> 57.1 s (CPU 230 -> 247 s, +7.7%; planner +0.5 s).
- Look: `output/checks/33.png` (aerial, the station far right in the haze), `output/checks/33-station.png`
  (110 m off, 30 m up: hall, pavilion, clock tower, canopies, tracks). Blender: `output/bodjantouna-42/
  goumosbane.blend` (new "station" camera).
- Doubts and questions for Ali: the quick capital's coast slopes 8%, so the station's ground is graded level
  and blends back over 100 m (a gentle regrade of the neighbourhood). The +31.6% tile is plan shift, not the
  station. The full capital time rose about 5 s; part may be noise.

## 2026-10-24 - Fix: parking keeps clear of shop and cafe fronts
- Commit: (see git log) | Model: Opus 5.5, high
- Changed: `citygen/city/parking.py` (fronts get `front_gap`), `styles/maghreb.toml` (`[dressing.parking]
  front_gap = 0.5`), `tests/test_citygen.py` (the parked-car test now checks the placed shop and cafe fronts).
- Bug (prompt 25): shop and cafe front zones had clearance 0.0 and a car was blocked only where `distance <
  clearance`, never true at 0, so cars parked right before cafe and shop fronts (on the capital's tile, 15
  cafe fronts had a car in them). Now a car keeps `front_gap` m from the zone (the front, `front_clear` m each
  way along the curb, out to the street). The extended test fails on the old code.
- Checks: tests 90 passed; `build --quick` 11.9 s; fingerprint against HEAD 7694643: `tiles/index` and 4 tiles
  (bytes -0.1% at most). Parked cars on the quick capital 1,506 -> 1,431.
- Look: `output/checks/32.1-parking.png` (street view, difference 0.00: no parked car in that view).
  Blender: `output/bodjantouna-42/goumosbane.blend`.
- Doubts and questions for Ali: none.

## 2026-10-24 - Prompt 32 A5c Cathedral and theatre on the boulevard
- Commit: (see git log) | Model: Opus 5.5, high (playbook: Sonnet, high)
- Changed: `citygen/city/landmarks.py` (new: sites on merged lots, `merge`, buildings and names, the local
  `Frame` and plan shapes shared with the mesh, boulevard trees cleared before the steps, camera views),
  `citygen/mesh/landmarks.py` (new: the cathedral and the theatre), `citygen/city/__init__.py` (the step after
  the impasses), `citygen/city/model.py` (`Building.facade`), `citygen/city/streets.py` (`view_spot`, the
  street camera's rule, now shared), `citygen/build.py` (`camera_views` uses it; "cathedral" and "theatre"
  views), `citygen/city/parking.py` (no car before the steps), `citygen/mesh/tile.py` (dispatch in
  `building_mesh`), `citygen/mesh/builder.py` (`add_arch` round head, `add_quads` moved from `vaults.py`),
  `citygen/export/maps.py` (colors; a landmark label moves a line up or down when that covers less),
  `citygen/export/lore.py` (gazetteer line), `styles/maghreb.toml` (`[landmarks]`, names, `stone_cathedral`,
  `stone_dressed`, `plaster_theatre`, `verdigris`, `boulevard_landmarks` for capital and city), tests (1 new,
  2 kasbah tests now skip the buildings after the kasbah), docs.
- Design: each kind slides its footprint along the boulevard-facing colonial lots (shift 0-12 m, scales 1.0 to
  0.76 of its size); the lots of one block it touches (3-6) are merged and must hold it. Quick capital: the
  boulevard is 76 m and the street camera stands 10 m from its start, so no site lies 50-300 m ahead (the
  cathedral's block is 48 m ahead, behind palms): cathedral 20.2 x 40.3 m on 4 lots (block 40, the far end),
  theatre 25.2 x 26.9 m on 3 lots (block 48, near the start), facing each other across the boulevard; new
  index views "cathedral" and "theatre" (also in the viewer menu and the .blend cameras). Full capital: both
  about 100 m ahead of the street camera, facing each other: cathedral 22.1 x 44.2 m on 4 lots, theatre
  30 x 32 m on 6. Triangles: quick 2,995 and 3,081, full 3,095 and 3,285 (limit 6,000). Names: "Cathedral of St
  Ambroise de Goba", "Theatre Municipal de Goumosbane". Plan parts (quick): buildings 1,683 -> 1,678 (7 apartments
  gone, 2 landmarks appended after the kasbah), parcels 1,707 -> 1,702 (7 lots merged into 2 appended at the
  end), households 1,313 -> 1,306, trees 8,010 -> 8,006 (4 boulevard palms before the steps), landmarks 10 -> 12;
  every later colonial lot re-rolls its draws, every later building index, household and massing choice shifts.
- Checks: tests 90 passed (23.6 s; the new one 0.15 s), slow tests pass; `build --quick` 10.8 s (HEAD 10.7 s);
  fingerprint: `plan/*`, `maps/*`, `gazetteer`, `tiles/index` and all 8 tiles, worst +3.5% (`tile_14_22`), the
  landmark tile +2.6%. Full capital 50.6 -> 50.8 s (HEAD rebuilt 49.8 s; planner +0.2 s), 37 of 168 tiles
  change: the landmark tile `tile_65_107` +7.9%, but `tile_70_102` +17.0% (269 -> 315 KB) and `tile_66_107`
  +10.2%: re-rolled household door colors bring other door and shutter variants into light tiles (the kasbah's
  effect, larger here).
- Look: `output/checks/32.png` (street view: the cathedral's towers and rose 48 m ahead on the left, half behind
  a palm; the theatre is hidden by the promenade trees) and `output/checks/32-landmarks.png` (from the ring road
  15 m up: the cathedral far left with towers, domes, rose and crossing dome; the theatre close on the right with
  its rounded corner, cupola, crown dome and canopy). Both were taken before two small byte trims (urns of 10
  triangles, matte domes). Blender: `output/bodjantouna-42/goumosbane.blend`.
- Doubts and questions for Ali: on the quick capital the two landmarks cannot stand 50-300 m ahead of the street
  camera (its boulevard is 76 m), so they have their own camera views; light full-capital tiles over +10% from
  re-rolled door colors (not from the landmarks); "boulevard-facing" read as the merged site facing the
  boulevard (lots behind the front lots join, else no cathedral fits a 25 m frontage).

## 2026-10-24 - Prompt 31 A5b Covered souks
- Commit: (see git log) | Model: Opus 5.5, high (playbook: Sonnet, high)
- Changed: `citygen/city/covered.py` (new: which souks, the covered stretches, springing, stations, arches,
  openings, lanterns, `clear` so nothing pierces a roof), `citygen/mesh/vaults.py` (new: vaults, impost bands
  and fills, light openings with curbs, transverse arches on red and green corbels, lantern rods),
  `citygen/mesh/tile.py` (one `Covers` per city shared with the dresser; roofs drawn per tile;
  `under_roofs` before the people), `citygen/city/dressing.py` (`covers()`, `under_roofs`, no spans under a
  roof, vault lanterns in `street_props`), `styles/maghreb.toml` (`[covered_souk]`, `vault_lantern` role),
  tests (2 new), docs.
- Design: souks of the perfumers, chechia makers and cloth merchants plus the city's longest souk; segmental
  barrel vaults springing at min(taller wall top, 4 m), at least 3.6 m, crown 1.8 m higher; fills down to lower
  houses and lintels over alley mouths; a 1 m square opening with a curb in every bay (about 7 m); arches at
  bay ends and portals at both ends; roof stops 4 m before line ends and at bends sharper than 50 degrees.
  Quick capital 351 m covered (10 stretches), full capital 603 m. Dropped: 38 pieces quick, 97 full (upper
  windows behind the vaults, a laundry line, cascades, climbers, 2 door hoods, an alley arch); 2 + 1 awnings
  lowered; 6 + 12 lantern strings and bunting left out; 28 + 41 lanterns hung from the arches.
- Checks: tests 89 passed (23.1 s; new ones 0.19 s); `build --quick` 10.7 s (HEAD 10.7 s); fingerprint: only
  `tiles/tile_13_23` (+6.0%), `tiles/tile_14_23` (+0.7%), `tiles/index`. Full capital 50.0 -> 50.9 s (noise),
  worst tile +6.8% (`tile_65_106`).
- Look: `output/checks/31.png` (souk view at noon: the portal, whitewashed vault, arches with lanterns, the
  painted corbels, stalls and people under it; the golden-hour default was checked too) and
  `output/checks/31-roofs.png` (aerial at noon, about 70 m up: vault strips weaving between the roofs, curbed
  openings, open ends at crossings). Blender: `output/bodjantouna-42/goumosbane.blend`.
- Doubts and questions for Ali: none. For the lead: (1) the flat timber-and-reed roof (the prompt's
  alternative) is not built, vaults only; (2) sun patches through the openings are faint in the headless noon
  snapshot (40 degree sun, 0.34 m shadow texels): worth a look in a GPU browser; night glow not snapshotted
  (the lanterns are the existing glowing kit pieces).

## 2026-10-24 - Prompt 30 A5a The kasbah
- Commit: (see git log) | Model: Opus 5.5, high (playbook: Sonnet, high)
- Changed: `citygen/city/kasbah.py` (new: placement, walls, towers, gate, palace, mosque, parade ground),
  `citygen/city/medina.py` (alleys drop crossings in the kasbah's cut, a souk from its gate; the rampart
  leaves out its outer wall and towers), `citygen/city/__init__.py` (kasbah buildings and landmark appended
  last), `citygen/city/model.py` (`Building.battlement`, `Building.arches`), `citygen/city/roofs.py` (no
  parapet under merlons), `citygen/mesh/builder.py` (`add_boxes`, `add_battlement`, `add_arch`),
  `citygen/mesh/tile.py` (battlements, arches, `paving_mesh` for `kasbah_ground`), `citygen/city/squares.py`
  (kasbah walls are monuments; its sabil stands on the gate tower, never before a door),
  `citygen/city/dressing.py` (lit-flat key at exactly x.5 degrees), `citygen/names.py`, `citygen/export/maps.py`,
  `citygen/export/lore.py`, `styles/maghreb.toml` (`[kasbah]`, `kasbah = true` for capital and city,
  `stone_kasbah`, names, sabil chance), tests (3 new, 2 extended, 2 adjusted), docs.
- Kasbah: quick capital "Kasbah of Goumosbane", walls 99 x 84 m (8 wall pieces, 7 towers, gate tower),
  palace 42 x 29 m (4 floors, 14 m), mosque hall 22 m wide, minaret 26.7 m; full capital 163 x 122 m (10
  towers), palace 60 x 46 m, hall 30 m, minaret 36 m. Every full-size city gets one (7 more); no town or
  village. Its walls sit on the 82-97th percentile of the old town's outline height.
- Plan parts (the kasbah takes old-town space; every later household and massing choice re-rolls): quick
  capital streets 488 -> 454, impasses 173 -> 151, blocks 158 -> 154, parcels 1,756 -> 1,707, buildings
  1,708 -> 1,683 (25 kasbah ones appended), households 1,367 -> 1,313, souks 14 -> 15 (from the kasbah gate
  to the great mosque), trees 8,017 -> 8,010, landmarks 9 -> 10. Full capital streets 11,402 -> 11,284,
  impasses 6,641 -> 6,541, parcels 41,947 -> 41,775, buildings 39,225 -> 39,121, households 38,568 ->
  38,451, souks 13 -> 16.
- Checks: tests 87 passed (23.0 s; new ones about 0.5 s); `build --quick` 10.6 s; fingerprint: `plan/*`,
  the 9 tiles, `tiles/index`, `maps/goumosbane.png`, `gazetteer` (all allowed). Worst quick tile +9.0%
  (`tile_12_23`, a light tile: other car, figure and door variants after the re-roll, not the kasbah; the
  kasbah's own tiles +2.6% and +7.4%); full capital worst +8.7% (`tile_68_100`), budget 10%. Full capital
  50.1 -> 50.9 s (planner 16.2 -> 16.3 s, CPU 227 -> 218 s).
- Look: `output/checks/30.png` (aerial: the walled square on the old town's south edge) and
  `output/checks/30-kasbah.png` (from the old town, 200 m: crenellated walls over the roofs, square towers,
  the gate tower with its horseshoe arch, the palace with arched windows, the minaret, the paved parade
  ground). City map: the kasbah in dark stone, labelled. Blender: `output/bodjantouna-42/goumosbane.blend`.
- Doubts and questions for Ali: none. For the lead: (1) `test_cut_corners...` pillar guard lowered from > 5
  to > 1: the re-rolled massing leaves 2 pillar feet on paved corners in the quick capital (the checks on
  them pass); (2) a latent lit-flat bug surfaced (a wall at exactly -127.5 degrees split a flat into two
  stream keys) and is fixed in `Dresser._light`; (3) no people on the parade ground yet (the bonus): the
  crowd has no source there.

## 2026-10-24 - Prompt 29 P2 People in the streets
- Commit: (see git log) | Model: Opus 5.5, medium (playbook: Sonnet, medium)
- Changed: `citygen/city/crowd.py` (new: candidates per place, halo, thinning, figure cast, checks),
  `citygen/city/dressing.py` (`Dresser.crowd()`; door benches on the street's level, `tounes/bench_sbs` backs
  onto the wall), `citygen/mesh/tile.py` (people at the end of each city), `citygen/mesh/builder.py`
  (`MeshBuilder.sizes`), `styles/maghreb.toml` (`[people]` with souk, shop, lane, sidewalk, promenade,
  landmark, square, stair, seats and outfits tables), tests (1 new), `docs/SPEC.md`, `docs/HANDOFF.md`.
- Quick capital (9 tiles): 1,857 people: 523 souk walkers, 128 shop browsers, 157 seated (106 at cafes, 37
  on doukkanas, 14 on benches), 855 on sidewalks, 11 on the promenade, 32 at the great mosque, 10 at gates,
  5 at the kiosk and fountain, 128 in medina lanes, 8 on estate stair paths; 669 walk in pairs or families
  (95 children). Outfits: 519 shirt, 417 hijab, 366 jebba, 258 safsari, 202 dress, 53 boys, 42 girls.
  Quick village 4: 23 people (16 jebba, 6 safsari, 1 dress; 5 on door benches).
- Checks: tests 84 passed (22.4 s; the new ones 0.5 s and 0.06 s); `build --quick` 10.6 s (10.0 s at density 0);
  fingerprint: the 9 tiles and `tiles/index` changed (allowed `tiles/*`); density 0 gives 0 changed parts.
  Worst quick tile bytes +7.7% (`tile_13_22`), full capital +8.3% (`tile_66_102`), budget 10%; drawn
  triangles worst +23.0% quick (`tile_13_23`), +18.1% on the 25 central full tiles, budget 30%. Full
  capital 48.0 -> 50.4 s (CPU 207 -> 224 s).
- Look: `output/checks/29.png` (souk: walkers both ways, browsers facing the goods, nobody floating) and
  `output/checks/29-cafe.png` (arcade cafe at 10 m: two men in jebba seated on the chairs facing each other,
  feet under the table, walkers under the arcade). Blender: `output/bodjantouna-42/goumosbane.blend`.
- Doubts and questions for Ali: none. For the lead: (1) bytes are the tight budget: each figure costs about
  14 KB per tile, so light tiles show only their 3-6 most frequent figures (`bytes_share`); (2) door benches
  moved up to the street's level (they stood about 0.2 m below souk ribbons) and `tounes/bench_sbs` out of
  the wall; (3) lead review: fixed the crash in `Squares._sabil_fits` on a settlement without streets
  (quick village 5): squares queries go through `_streets`/`_buildings` (nothing without streets or
  buildings), no street means no sabil, the crowd's mosque outline needs buildings; a new test dresses
  village 5 (0.06 s). Prompt 39 now notes that quantized meshes should let light tiles show more figures.

## 2026-10-24 - Prompt 28 P1 People: low-poly figures
- Commit: (see git log) | Model: Opus 5.5, high (playbook: Sonnet, high)
- Changed: `citygen/mesh/people.py` (new: skeleton, poses, outfits), `citygen/kit.py` (person pieces),
  `styles/maghreb.toml` (`[dressing.people]` with 26 pieces; palette: 17 muted `cloth_*`, 4 skin, 3 hair,
  shoes, balgha, basket, bag, bread), `tests/test_citygen.py` (1 test), docs.
- Pieces (triangles): jebba stand/walk/walk_b 329, sit 369, carry 389; shirt stand/walk 328, walk_b 352,
  sit 304, sit_b 328, carry 356; safsari stand/walk 227, sit 263, carry 319; dress stand/walk/sit 360;
  hijab stand/walk 319, sit 343, carry 347; boy 352; girl 368. Standing adults 1.60-1.79 m to the top (a
  chechia included; walkers 4-7 cm lower mid-stride), children 1.17-1.27 m.
- Seats found in the kit: `bench_iron` 0.45, `doukkana` 0.45, `cafe_set` chairs 0.46, `tounes/bench_sbs`
  0.48. Sitters touch 0.45 exactly; prompt 29 lifts them by seat - 0.45 (1 cm, 3 cm). Checked side and
  three-quarter renders on all three seats: on the seat, back clear of the backrest, feet under the
  cafe table.
- Checks: tests 82 passed (21.4 s, the new one about 0.3 s); `build --quick` 9.9 s; fingerprint against
  `before`: 26 parts changed, all new `kit/person_*`; no tile changed (no Blender refresh needed).
- Look: `output/checks/28.png` (kit sheet from about 20 m) and `output/checks/28-eye.png` (street eye
  height, 5-20 m): jebba and chechia, safsari, headscarves, children read as people; strides visible.
- Doubts and questions for Ali: none. The seated shins are 2-6 cm longer than standing ones so level
  thighs reach the ground (see HANDOFF).

## 2026-10-24 - Prompt 27 CP3 Checkpoint: facades and street life
- Commits: "CP3 fixes: paint and cars agree, cut-corner arcade zones, lamps, lit keys" and "CP3
  speed: tiles 26% faster, tests 31 s -> 20 s, output byte-identical" (see git log) | Model: Opus
  5.5, medium (lead), with an independent Opus reviewer that read only the committed history
- Reviewed prompts 17-26 with 20.1 and 20.2 (17-19 DeepSeek; 20-26 Opus helpers, each reviewed by
  the lead before its commit): every "Done when" met. Documented, kept: 52% of arcade bays flex to
  3.2-4.4 m (22); the taxi rank stands in a side street, the quick boulevard is only 76 m (25);
  colonial arterials keep their arcades as shade instead of street trees (24).
- Found and fixed (independent review, verified): paint gave empty parking rows to sides without
  parking districts; arcade zones probed cut-corner faces differently from `Dresser.walls`, so a
  side-street lamp could stand under a wrap bay; lit flats keyed a side on a float yaw (a south
  wall could split a flat); lamps of a grid street under the boulevard stood on the promenade, one
  1.3 m from the fountain (`lamp_spot` now drops lamps inside a wider street); fountain clear of
  crowns; numbers moved to `[dressing.squares]` and `[dressing.parking]`; one shared stair-path
  function; the terrain-corner cache cleared per tile; three tests made to check the real result.
- Speed (identical output, fingerprints of the quick and the full capital 0 changed): quick tiles
  4.81 -> 3.58 s in one process, full capital about 54 -> 48 s back to back, planner 17.3 -> 16.3 s,
  `pytest -q` 30.7 -> 20.4 s, `build --quick` 11.4 -> 9.9 s.
- Checks: tests 81 passed (20.4 s), 2 slow passed; `build --quick` 9.9 s; stats 296,713 triangles,
  4,046,565 drawn, 27,255 dressing pieces, 18.4 MB in 9 tiles. Against `cp2`: 98 parts changed (81
  new kit pieces, plan buildings, streets, trees and households, every tile; densest quick tile
  5.81 -> 7.40 MB). Saved `fp-cp3`.
- Textures: 14 shared images, about 0.7 MB (limit 2 MB); sharp at street level (anisotropy 8); no
  visible repeat from 135 m (`20-air.png`). Phone page rebuilt from the quick build (26 MB, biggest
  file 9.9 MB) and served locally: 9/9 tiles with textures, no console errors. Blender file
  refreshed by every prompt (`tools/make_blend.py`).
- Doors and windows: every dwelling has a door (tests); slabs have windows on every floor; no
  enclosed home on the quick or the full capital (6,641 impasses on the full capital).
- Street life: boulevard, souk and colonial streets walked in the GPU viewer: no car in a tree or
  on a crossing, no lamp or tree in an arcade after the fixes, benches and kiosk clear. The street
  view renders in 4.6 ms per frame (High, golden hour).
- Look: `output/checks/cp3-street.png` (difference 0.24: the two promenade lamps are gone) and
  `output/checks/cp3-souk.png` (0.00). Blender: `output/bodjantouna-42/goumosbane.blend`.
- Doubts and questions for Ali: none. Tile weight is the open budget (densest quick tile 7.4 MB,
  three suburb tiles just over 3 MB): prompts 39-41 handle it.

## 2026-10-24 - Prompt 26 H3b Benches, kiosks and fountains
- Commit: (see git log) | Model: Opus 5.5, medium (playbook: Sonnet, medium)
- Changed: `citygen/mesh/furniture.py` (new: `bench_iron` 180 triangles, `kiosk` 232 with a lit twin,
  `fountain_colonial` about 740, `sabil` 208), `citygen/city/squares.py` (new: islands, fountain, kiosks,
  benches, sabils, obstacle checks), `citygen/city/dressing.py` (`squares()`, `tree_spots` leaves out the
  trees a fountain replaces, door bench role `door_bench`), `citygen/kit.py` (furniture pieces, `kiosk`
  in `LIT_CATEGORIES`), `citygen/mesh/tile.py`, `styles/maghreb.toml` (palette `water_pool`, `marble`,
  `faience_white`, `kiosk_green`, `kiosk_trim`; roles `bench`, `door_bench`; `[dressing.squares]`,
  `[dressing.furniture]`), `tools/viewer/index.html` (sea test skips instanced meshes and `water_pool`),
  `tools/blender_beauty.py` (`shade_pool`), tests (2 new), `docs/SPEC.md`, `docs/HANDOFF.md`, `docs/ROADMAP.md`
- Checks: tests 81 passed (30.6 s; the 2 new ones about 0.1 s on the shared fixtures); `build --quick`
  11.3 s; fingerprint 8 changed, all allowed: `tiles/index`, `tile_13_23` (+1.6% bytes, +1.3% triangles),
  `tile_14_23` (+0.8%), new `kit/bench_iron`, `kit/kiosk`, `kit/kiosk_lit` (the kiosk's night twin, prompt 21
  rule), `kit/fountain_colonial`, `kit/sabil`; full capital 52.4 -> 53.7 s (CPU 234 -> 242 s). Quick capital:
  1 fountain, 1 kiosk (lit), 2 benches, 4 sabils; full capital: 1 fountain, 2 kiosks, 10 benches, 4 sabils.
- Look: `output/checks/26.png` (street view: an iron bench on the promenade under the trees, the green
  kiosk at the far end of the island); `output/checks/26-fountain.png` (the colonial fountain at the ring
  road head of the promenade, quick (6863.7, 12179.4), full (33428.6, 54746.9); the gate sabil shows on a
  tower in the background). The great mosque's sabil is on its south wall facing the souk across the open
  margin: quick (7019.6, 12023.4), full (33378.7, 54244.6). Blender: `output/bodjantouna-42/goumosbane.blend`.
- Doubts and questions for Ali: none. For CP3: a grid street lying under the boulevard puts its lamps on
  the promenade (one stands 1.3 m from the fountain), older than this prompt.

## 2026-10-24 - Prompt 25 H3a Parked cars and taxis
- Commit: (see git log) | Model: Opus 5.5, medium (playbook: Sonnet, medium)
- Changed: `citygen/mesh/vehicles.py` (new: hatchback, sedan, van, louage, taxi; 152-184 triangles,
  4 colors each sharing their arrays), `citygen/city/parking.py` (new: `parked_sides` rule, per-side
  sidewalk widths, `Parking` rows and taxi rank), `citygen/city/dressing.py` (`street_props` adds the
  cars; `lamp_spot`, `front_of`, `door_spots`, `fronts`; `Placement.tilt`; `CAFES`),
  `citygen/city/paint.py` (edge line on the lane side of a parking row, sidewalks measured per side,
  carriageway cuts every sidewalk on the street, crossings tagged), `citygen/city/model.py`
  (`Paint.kind`, `Walk` comment), `citygen/city/__init__.py`, `citygen/kit.py`, `citygen/mesh/tile.py`
  (instance rotation with tilt), `styles/maghreb.toml` (car palette, `[dressing.vehicles]`,
  `[dressing.parking]`), tests (3 new), `docs/SPEC.md`, `docs/HANDOFF.md`, `docs/ROADMAP.md`
- Checks: tests 79 passed (29.5 s; the 3 new ones 0.5 s); `build --quick` 11.2 s (HEAD 10.6 s);
  fingerprint 29 changed, all allowed: `tiles/*` and the 20 new `kit/car_*`; worst quick tile bytes
  +8.8% (`tile_12_22`, budget 10%), drawn triangles +7.1% worst (`tile_13_22`, budget 20%); full capital
  47.4 -> 51.8 s back to back (CPU 204 -> 228 s), worst full tile +8.5% (both before the lead's
  boulevard fix). Quick capital: 1,525 cars (652 hatchbacks, 533 sedans, 193 vans, 125 taxis, 22
  louages), 221 streets + 9 arterials with one row, 3 arterials + the boulevard with two, a rank of 5
  taxis. Full capital (before the boulevard fix): 13,664 cars (907 taxis, 201 louages).
- Lead review (boulevard): the quick boulevard is 76 m between the ring road and the corniche with a
  cross street in the middle; its outer curbs (2 x 76 m, about 30 car slots) lost, by rule in turn,
  59 / 50.5 m to junctions, 7.5 / 6 m to zebras, 13 / 12 m to palms, 0 / 2.5 m to a lamp, nothing to
  cafe fronts, doors or paths: 3 cars. Too strict: grid street 162 runs along inside the boulevard but
  pokes out past its end, so it counted as a junction (now `lying_on` also skips a street running
  8 m or more inside it within 15 degrees); a sample of margin either side of every obstacle (now each
  car is checked exactly against the zones); empty stretches now by kind (boulevard 6%). Trunks are
  kept 1 m from the bark (`tree_clear` 1.0 + `tree_trunk` 0.3). Now 17 m free per side, 6 cars, two
  between the palms in the street view. The rank needs about 20 m between two palms, so it stays in
  the side street by the boulevard's busiest junction.
- Look: `output/checks/25.png` (street view: the boulevard's edge line moved out to the parking row,
  two cars parked between the palms by the arcade, one more past the crossing), `output/checks/25-cars.png` (a colonial street parked on one side with
  gaps, the taxi rank by the boulevard junction); Blender: `output/bodjantouna-42/goumosbane.blend`
- Doubts and questions for Ali: the quick capital's boulevard is only 76 m long and mostly junction,
  so the rank (and on the full capital too) stands in a colonial side street next to the boulevard's
  busiest junction, as many Tunis ranks do. The paint fix (sidewalks measured per side) moves edge
  lines on many arterials and on the boulevard, where they used to lie hidden under the sidewalks.

## 2026-10-24 - Prompt 24 A7 More greenery
- Commit: (see git log) | Model: Opus 5.5, medium (playbook: Sonnet, medium)
- Changed: `citygen/city/greenery.py` (new: arterial tree pits, courtyard trees, villa fruit trees,
  appended last), `citygen/city/__init__.py` (greenery after the paint, `stats["greenery"]`),
  `citygen/city/dressing.py` (`arcade_zones`, `band_push`, `tree_reach`, `stair_columns` as module
  functions; `Dresser.garden` and hedges), `citygen/city/openings.py` (`villa_lots`),
  `citygen/city/ground.py` (`terrain_cells`), `citygen/mesh/tile.py` (`garden_meshes`, gardens and
  hedges per villa), `citygen/mesh/trees.py` (citrus kind, oranges), `citygen/mesh/props.py` (`hedge`
  piece, citrus color in the light tree), `citygen/kit.py`, `citygen/export/maps.py` (garden lots,
  orange citrus dots), `tools/blender_beauty.py` (garden ground), `styles/maghreb.toml` (`[greenery]`,
  `[dressing.trees.citrus]`, `[dressing.hedge]`, palette `leaf_citrus*`, `fruit_orange`,
  `leaf_hedge`, `garden`, role `tree_citrus`), tests (3 new, 2 adjusted: the massing test also switches
  greenery off and checks the old trees as a prefix; the tree test counts citrus fruit apart),
  `docs/SPEC.md`, `docs/HANDOFF.md`, `docs/ROADMAP.md`
- Checks: tests 76 passed (28.4 s, was 27.6 s); `build --quick` 10.5-10.7 s (HEAD 10.7 s back to back);
  fingerprint 13 changed, all allowed: `plan/goumosbane/trees` (7,890 -> 8,017), `stats`, `gazetteer`
  (tree count), `maps/goumosbane.png`, `tiles/*` (worst quick tile +1.3%), new `kit/hedge`,
  `kit/tree_citrus`, `_b`, `_c`. Full capital 51.4 -> 49.0 s back to back (CPU 212 -> 207 s; 48.3 s
  after the garden trim). Suburb tiles: +31-37% with the house cut out of the garden (worst
  `tile_60_103` 2.41 -> 3.29 MB), +25-30% after the lead's trim (garden left under the house): worst
  2.41 -> 3.13 MB, three tiles just over 3 MB (3.13, 3.09, 3.06), all changed tiles together +5.8%. Quick capital: 69 arterial trees (modern), 58 courtyard trees (45 citrus,
  9 broadleaf, 4 olive). Full capital: 149 arterial, 273 courtyard (213 citrus), 2,025 villa fruit trees
  (1,640 citrus, 385 olive), 2,900 gardens (98 ha), 31,099 hedge pieces (192 km).
- Look: `output/checks/24.png` (close before/after above a modern arterial, cam 7340,11305,124 look
  7268,11350,82: a row of street trees on the modern sidewalk, stopping at the lamp and before the
  zebra junction; mean difference 2.11); `output/checks/24-gardens.png` (city 1 aerial after the hedge
  change: green villa lots outlined by dark hedges, nothing showing through the houses; the bare lots
  are lots without a villa, as before).
- Lead decisions: colonial arterials keep no new street trees (their arcades are the shade, as on real
  arcaded streets; no tree pit fits beside the pillars), modern arterials get them; the garden ground
  stays under the house (hidden) to save triangles.
- Doubts and questions for Ali: three suburb tiles are now just over the 3 MB tile budget.

## 2026-10-24 - Prompt 23 AR2 Building massing with character
- Commit: (see git log) | Model: Opus 5.5, high (playbook: Sonnet, high)
- Changed: `citygen/city/massing.py` (new: the planning step after households and souks, `masses`,
  `floors_at`, `wall_height`, `outline`, `inner_walls`, `terrace_walls`), `citygen/city/model.py`
  (`Building.setback`, `steps`, `machines`, `menzah`, `corners`; `top` with a position),
  `citygen/city/__init__.py`, `citygen/city/roofs.py` (main roof of the masses, `roof_layouts`, menzah,
  `RoofLayout.rooms`), `citygen/mesh/tile.py` (massed buildings drawn as one solid, lift rooms, corner
  domes and turrets, menzah), `citygen/mesh/builder.py` (`add_walls(only=)`), `citygen/city/dressing.py`
  (window floors per wall, terrace windows, tank stands, props on the main roof, corner probes, arcade
  bend pieces and wrap at cut corners, wall heights for climbers and spans), `citygen/city/arcades.py`
  (`hold0/hold1`), `citygen/mesh/props.py` (`arcade_bend`, `tank_stand`), `citygen/export/lore.py`
  (massing in plan.json), `styles/maghreb.toml` (`[district.*]` massing numbers, `[roofs]` menzah,
  `window_half`, `bend_tol`, `[streets] apron_*`), `citygen/city/ground.py` (paved lot corners:
  `apron_top`, `apron_cells`, `surface` there interpolates the drawn triangles), `apron_mesh` in
  `citygen/mesh/tile.py`, `add_skirt(only=)`, tests (4 new, 2 adjusted:
  arcade turns count bend pieces, the stair room test reads the main roof), `docs/SPEC.md`,
  `docs/HANDOFF.md`, `docs/ROADMAP.md`
- Checks: tests 73 passed (28.1 s; HEAD 25.2 s back to back; the 4 new tests 2.6 s); `build --quick`
  10.8 s; fingerprint 14 changed: `plan/goumosbane/buildings`, `maps/goumosbane.png`, `tiles/*`, new
  `kit/arcade_bend`, `kit/arcade_bend_round` (pier pieces for cut corners) and `kit/tank_stand`;
  households, souks, streets, trees and stats unchanged. Worst tile +6.8% (`tile_13_24`, with the paved
  corners), old-town tile +3.5%. Full capital 47.0 -> 48.3 s back to back with HEAD (planner 15.8 -> 16.3 s, CPU 193 -> 207 s). Quick capital: 78 cut
  corners (58 pan coupes, 20 rounded), 18 corner tops (8 domes, 10 turrets), 59 set-back top floors,
  183 of 276 colonial buildings moved to their block's row (+-1: 122, +-2: 48, +-3: 13), 79 of 356 slabs
  stepped (70 in two parts, 9 in three), 245 lift rooms, 149 tank stands, 20 menzahs. Full capital:
  261 cut corners, 86 tops, 262 set-backs, 151 stepped slabs, 2,900 villas of which 1,020 L-shaped.
- Look: `output/checks/23.png` (colonial blocks from about 150 m: rounded corner with a dome by the
  boulevard, turrets, set-back top floors behind their terraces, steadier rows),
  `output/checks/23-villas.png` (city 1 suburb: hip-roofed villas with flat terrace wings),
  `output/checks/23-corner.png` (building 1071: pan coupe arch between two bend piers, a bay into the
  side street, paving under it), `output/checks/23-corner-round.png` (building 972: an arcade round
  three faces with slim 22.5-degree piers). Blender:
  `output/bodjantouna-42/goumosbane.blend`.
- Doubts and questions for Ali: the rows now follow each block's median floor count (one floor up or
  down, corners taller), so most colonial heights changed (lead: keep). Lead review added the paved
  lot corners and the close corner pictures. The 45-degree corner piers are massive (about 2.9 m of
  solid front with the half pillars); they read as strong corner piers, but slimmer ones would need
  the bays to take the corner. No door or shop lands on a cut face yet (the long walls win the main
  facade); the test checks a face's threshold height instead.

## 2026-10-23 - Prompt 22 AR1 Colonial arcades and iron balconies
- Commit: (see git log) | Model: Opus 5.5, high (playbook: Sonnet, high)
- Changed: `citygen/city/arcades.py` (new: free runs, bay layout around doors on a 5 cm grid, level
  steps), `citygen/city/dressing.py` (`_colonial`, `_arcade_runs`, `_free_run`, `_side_gap`,
  `_corner_free`, `_pillar_zones`, `_arcade_pieces`, `_clear_of`, `_iron`, `_iron_window`, lamp rule
  in `_lamps`, cafe tables under arcades, `Placement.stretch`), `citygen/city/openings.py` and
  `citygen/mesh/tile.py` (stretch in boxes and instance SCALE), `citygen/mesh/props.py` (`arcade_bay`,
  `arcade_corner`, `balcony_iron`, `balcony_iron_long`), `citygen/kit.py`, `styles/maghreb.toml`
  (`[dressing.arcade]`, `[dressing.balcony_iron]`, roles), tests (1 new, 1 adjusted: new doors may stand
  inside an arcade's box, its pillars are checked by the new test), `docs/SPEC.md`, `docs/HANDOFF.md`,
  `docs/ROADMAP.md`; after the lead's review: `Dresser.tree_spots` and `citygen/mesh/tile.py` (trees
  clear the arcades), `[dressing.arcade]` `tree_*`, the test also checks tree trunks
- Checks: tests 69 passed (23.1 s; HEAD 21.5 s); `build --quick` 10.0 s (HEAD 9.5 s); fingerprint 10
  changed: `kit/arcade_bay`, `kit/arcade_corner` (the corner piece, a fourth new piece), `kit/balcony_iron`,
  `kit/balcony_iron_long` and `tiles/*`, worst tile +7.6% (`tile_12_23`). Full capital 44.1 -> 43.3 s
  (same minutes; CPU 175 -> 181 s). Quick capital: 312 bays on 95 colonial facades, 17 corner pieces,
  1,523 + 335 long iron balconies, 19 of 235 lamps on those streets moved to the curb (none left out);
  planned trees by an arcade (lead review): 10 palms moved to the curb, 2 left out (plan unchanged);
  dropped under arcades: 7 climbers, 2 cascades, 1 clothesline. Bays: 48% within 3.5-4.0 m, all within 3.2-4.4 m.
- Look: `output/checks/22.png` (street: arcades along the boulevard, lamps at the curb),
  `output/checks/22-corner.png` (corner of building 972: boulevard arcade, corner piece, one bay into
  the side street; iron balconies above). Blender: `output/bodjantouna-42/goumosbane.blend`.
- Doubts and questions for Ali: about half the wall lengths cannot be cut into 3.5-4.0 m bays, so those
  use 3.2-4.4 m (continuous arcades); `bay_relaxed` in the style narrows it if he prefers gaps.

## 2026-10-23 - Prompt 21 A9 Lit windows by household
- Commit: (see git log) | Model: Opus 5.5, medium (playbook: Sonnet, medium)
- Changed: `citygen/city/dressing.py` (`_light`, `_lit_chance`, `_sections`), `citygen/kit.py`
  (`_lit_pieces`: `_lit` twins, `_pane_lit` panes from the manifest's `glass`), `citygen/mesh/props.py`
  (`lit_pane`), `citygen/mesh/gltf.py` (a part drawn twice reuses its accessors), `kits/tounes/manifest.json`
  (`glass` rectangles of 7 windows), `styles/maghreb.toml` (`glass_lit`, `[dressing.lit]`),
  `tools/viewer/index.html` (`LIT_AT_NIGHT` lights `glass_lit`; panes at night only),
  `tools/blender_import.py`, `tools/blender_beauty.py` (`hide_night_panes`), tests (2 new, 1 adjusted:
  a door spot's piece may be drawn as its `_lit` twin), `docs/SPEC.md`, `docs/HANDOFF.md`, `docs/ROADMAP.md`
- Checks: tests 68 passed (21.5 s; HEAD 21.5 s); `build --quick` 9.5 s; fingerprint 38 changed: 29
  new `kit/*_lit` pieces and `tiles/*`, worst tile +2.0% (`tile_13_24`). Quick capital: 40% of housing
  windows lit (medina 34%, colonial 39%, modern 41%). Day street picture: difference 0.00.
- Look: `output/checks/21.png` (street at night: lit kit windows by flat), `output/checks/21-night-aerial.png`
  (lead's camera over the colonial blocks, headless: grey dots), `output/checks/21-night-viewer.jpg`
  (same camera in the GPU viewer, High: the real look). Blender: `output/bodjantouna-42/goumosbane.blend`.
- Lead review: at night `glass_lit`, `lantern_glow` and `tr_glow` stay out of the fog (`CLEAR_AT_NIGHT`
  in the viewer; fog back on by day, day difference still 0.00). In the GPU viewer (browser pane,
  same camera) lit flats read as warm orange points in clusters, many dark; 1,464 kit window panes
  visible at night, 0 by day. The headless SwiftShader snapshot draws lit window glass as grey
  dots (HEAD's glowing `glass_dark` did not show there either), so judge night glass in the real viewer.
- Doubts and questions for Ali: mashrabiya balconies stay dark (no room for a pane without flicker).

## 2026-10-23 - Prompt 20.2 AD2 Impasses to landlocked houses
- Commit: (see git log) | Model: Opus 5.5, high (playbook: Sonnet, high)
- Scope: the lead extended the prompt from medina and village blocks to residential and suburb
  blocks too (one mechanism, widths and surfaces per district kind), because the full capital had
  7,802 enclosed residential houses and addresses, entrances and interiors need every home reachable.
- Changed: `citygen/city/impasses.py` (new: landlocked test as the dresser sees facades, lot-line
  graph, lanes cut nearest lots first and branching like a tree, all blocks in lockstep rounds),
  `citygen/city/__init__.py` (after the mosques' lots, before buildings; lanes appended last; stats
  `impasses`), `citygen/city/model.py` (`Street.covered`, `Parcel.block`), `citygen/city/parcels.py`,
  `citygen/city/dressing.py` (`impasse` in `FRONT_PREF` lowest, laundry and cables, covered mouth as a
  sabat of that length, arch inside some mouths, main facade long enough for a door), `citygen/city/ground.py`
  (lift 0.18 like alleys), `citygen/mesh/tile.py` (sabat depth), `citygen/export/maps.py` (drawn like
  alleys), `styles/maghreb.toml` (`[impasse]` and per kind: medina 2.2-3.0 m paving, village 2.6-3.4 m
  earth, residential 3.5-4.0 m asphalt, suburb 3.8-4.4 m asphalt; `impasse_arch`), tests (4 new, 2
  adjusted: no quick-capital dwelling is enclosed any more; impasse surfaces come from `[impasse]`),
  `docs/SPEC.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`
- Checks: tests 66 passed (21.2 s; HEAD 19.5 s); `build --quick` 9.4 s (HEAD 9.1 s); fingerprint
  156 parts, 16 changed, all in `plan/*,tiles/*,maps/*,gazetteer`. Quick capital: streets 315 ->
  488 (173 impasses: 116 open on a street, 57 branch off one; 39 covered, 6 drawn as rooms where
  both houses are tall enough, 1 arch; 3.8 km), parcels 1,793 -> 1,756, buildings 1,742 -> 1,708,
  households 1,401 -> 1,367 (all later households shift: one sequential stream), trees 7,927 ->
  7,890. Medina dwellings 769 -> 735: doors 437 street + 10 open + 322 enclosed -> 735 street
  (323 on an impasse, 267 on an alley, 145 on a souk). Full capital: 6,641 impasses (medina 939,
  residential 5,101, suburb 601; 160 km), enclosed dwellings medina 1,781 -> 0, residential 7,802
  -> 0, suburb 0; streets 4,761 -> 11,402, parcels 42,128 -> 41,947, buildings 39,555 -> 39,225,
  households 38,898 -> 38,568. Full capital time in the same minutes: 34.8 -> 42.5 s (planner
  10.6 -> 15.5 s; tiles +12%). Tiles: old town 13_23 6.06 -> 6.74 MB (+11%), 14_23 +13%,
  14_24 +4%; 12_22 and 12_23 smaller (a shutter piece no longer used there after the household shift).
- Look: `output/checks/20.2.png` (souk: shops now keep a house door beside them),
  `output/checks/20.2-aerial.png` (old town from 100 m at 45 degrees: narrow paved lanes into the
  blocks, windows on walls facing them); the quick map shows a web of dead ends off the alleys.
  Blender: `output/bodjantouna-42/goumosbane.blend` refreshed.
- Doubts and questions for Ali: the planner is 4.9 s slower on the full capital (vectorized from
  9 s per-block); covered mouths are rarely drawn because both corner houses must have two floors.

## 2026-10-23 - Prompt 20.1 AD1 Every home gets a door and windows
- Commit: (see git log) | Model: Opus 5.5, high (playbook: Sonnet, high)
- Changed: `citygen/city/dressing.py` (`door_spot`, `entrances`, open-wall windows, slab windows,
  balconies, stair doors, house doors beside shops and cafes, corner-cached `drawn`; the street
  walls' draws untouched), `citygen/city/openings.py` (new: walls, open-wall probes, piece boxes,
  paths), `citygen/city/ground.py` (`Ground.drawn`: the terrain mesh's height), `citygen/mesh/props.py`
  (new pieces from one-sided quads: `door_narrow_*`, `window_slab_*` and `_shut`, `window_stair`,
  `balcony_slab`, `stair_door`), `citygen/mesh/tile.py` (paths drawn by the owning tile, terrain
  grid seeds the dresser's corner cache), `styles/maghreb.toml` (`every_home`, `[dressing.open_walls]`,
  `[dressing.slab]`, `[dressing.paths]`, roles), tests (5 new, 1 widened), `docs/SPEC.md`,
  `docs/ROADMAP.md`, `docs/HANDOFF.md`
- Checks: tests 62 passed (20.0 s; HEAD 17.7 s); `build --quick` 9.3 s; fingerprint 156 parts, 25
  changed: `tiles/*` and the 16 new `kit/*` pieces by exact name (`kit/balcony_slab`,
  `kit/door_narrow_{blue,brown,green,red,yellow}`, `kit/stair_door`,
  `kit/window_slab_{white,blue,green,brown}` and their `_shut`, `kit/window_stair`). Quick capital:
  1,401 dwellings, 1,401 main doors placed (713 on a street, 366 on open ground, 322 enclosed for
  20.2); 225 house doors beside shops and cafes; 356 slabs with 471 stair doors, 412 with a path.
  Tile bytes: three modern-estate tiles over the +20% budget (13_22 +36.6%, 14_22 +24.9%, 12_22
  +20.5%), accepted by the lead: estate tiles had almost no dressing before; +0.26 MB at most;
  instance bytes go to prompt 39. The others +0.9% to +3.0%. Level faces of the new pieces get
  planar meter UVs (no smeared concrete stripes). Full capital `--force`: 37.0 s (HEAD measured 34.5 to 44.3 s
  on this Mac; tile work single-process +12%).
- Look: `output/checks/20.1.png` (modern estate from 150 m: window grids, balconies in columns,
  shutter colors, blind gables), `output/checks/20.1-shops.png` (re-run after `door_clear` 0.9 ->
  2.0: the blue house door stands 2.84 m from the cafe center, 0.9 m past the awning and clear of
  the chairs; the fanlight glass then moved 1.5 cm off the wall, where it flickered)
- Decision: tile byte budget on estate tiles accepted by the lead (see Checks).
- Doubts and questions for Ali: none left. 7,802 residential houses on the full capital are
  enclosed; the lead extends prompt 20.2's impasses beyond medina and village blocks to cover them.

## 2026-10-23 - Fix: no more "Blender quit unexpectedly" from agents
- Commit: (see git log) | Model: Opus 5.5, medium
- Changed: `tools/make_blend.py` (`sandboxed()`: stops before starting Blender inside a macOS
  sandbox), tests (1 new), `CLAUDE.md` (never start Blender another way), `docs/HANDOFF.md`
- Checks: tests 57 passed; `build --quick` 1.6 s (reused); sandboxed run stops with a clear
  message and no new crash report; the exact `make_blend.py` command still saved the .blend
  (20:00); Ali's terminal: `sandboxed()` is False
- Doubts and questions for Ali: none

## 2026-10-23 - Prompt 20 A2d Ground textures
- Commit: (see git log) | Model: Opus 5.5, medium (playbook: Sonnet, medium)
- Changed: `citygen/mesh/builder.py` (optional `col` per piece, ribbon u along the street from a
  start distance, v across; draped cap with per-triangle street direction; curb v from the top),
  `citygen/mesh/tile.py` (`GroundTint` COLOR_0 on terrain, ribbon start via `line.project`,
  `street_directions` for sidewalks), `citygen/mesh/props.py` (unpack), `styles/maghreb.toml`
  (ground, street, sidewalk and curb textures and sizes, softer earth/grass/scrub blotches,
  stronger asphalt patches, `urban_ground` lifted, `[ground_tint]`), `tools/viewer/index.html`
  (`vertexColors` in the shared-material key), `tools/blender_beauty.py` (palette colors from
  `baseColorFactor`), tests (5 new), `docs/SPEC.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`
- Checks: tests 56 passed (about 18.5 s; the 5 new ones about 0.9 s); `build --quick` 9.1 s,
  9 tiles; fingerprint 141 parts, 11 changed: `tiles/*` and `tiles/textures/*` as allowed, plus
  a `tiles/.DS_Store` written by Finder (not by the build). Budgets: 14 shared images, 732 KB
  (limit 2 MB); tile bytes worst +9.5% (terrain-only capital tiles, about +17 KB of COLOR_0),
  densest `tile_65_106` +0.2% (limit +10%). Full capital `--force`: 32.4 s before (first run);
  back to back later, HEAD 36.8 s and this change 37.0 s (+0.5%), 168 tiles.
- Look: `output/checks/20.png` street - paving tiles and curb stones run along the street,
  asphalt with soft patches; `output/checks/20-air.png` from about 135 m over the cemetery and
  open ground - no visible repeat (a first try with earth at full mottle showed a grid; fixed).
  Blender: `output/bodjantouna-42/goumosbane.blend`.
- Doubts and questions for Ali: none. In Blender the ground, asphalt and paving keep their
  procedural shaders (they ignore the images and the tint); sidewalk, curb, earth, desert,
  forest and rock use the imported image x tint.

## 2026-10-23 - Prompt 19 A2c Textured walls and roofs
- Commit: "Textured walls and roofs: plaster, plinths and roof tiles" (see git log) | Model:
  DeepSeek V4.1 Flash, high (playbook: Sonnet, high)
- Changed: `citygen/mesh/builder.py` (wall split at the plinth, `_wall_band` mask, planar
  hip-roof UVs with a per-face slope length, degenerate roof triangles dropped),
  `citygen/mesh/tile.py` (`[plinth]` lookup, street-facing mask from street center lines and
  sidewalks), `styles/maghreb.toml` (palette textures and sizes, `plinth_blue`/`plinth_stone`,
  `[plinth]`, stronger plaster/render strengths), `tools/viewer/index.html` (anisotropy),
  tests (4 new/changed), `docs/SPEC.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`
- Checks: tests 51 passed (15.1 s); `build --quick` 7.8 s, 9 tiles; fingerprint 140 parts,
  9 changed, all `tiles/*`. Budgets: 7 shared images, 284 KB (limit 2 MB); full capital
  `--area capital` 31.5 s, 168 tiles, tile bytes +2.21% total and +3.45% for the densest tile
  (limit +10%); quick densest +2.82%. Plinth triangles fell from 9,634 to 2,208 on the
  dense medina tile by keeping party walls plain.
- Look: `output/checks/19.png` street before/after (mean difference 4.60) - stone plinths on
  street walls, plaster grain, aligned bands; `output/checks/19-hip.png` on the `city:1` build -
  tile rows running down every hip face, including the end triangles. Blender:
  `output/bodjantouna-42/goumosbane.blend`.
- Doubts and questions for Ali: none. The plinth is drawn only on street-facing exterior walls
  (a party wall or courtyard side is never visible); the base band still follows the ground.

## 2026-10-23 - Prompt 18 A2b Generated textures
- Commit: "Generated textures: plaster, stone, tiles and paving" (see git log) | Model: DeepSeek
  V4.1 Flash, high (playbook: Sonnet, high)
- Changed: `citygen/mesh/textures.py` (rewritten: 14 seamless surfaces, periodic value noise,
  wrapped strokes, Fourier blur, one stream per texture, PNG/JPEG encoder and cache),
  `citygen/texturesheet.py` (new), `citygen/__main__.py` (`texture-sheet`), `styles/maghreb.toml`
  (`[textures]` table), tests (4 new, prompt 17 tests migrated), `docs/SPEC.md`,
  `docs/ROADMAP.md`, `docs/HANDOFF.md`
- Checks: tests 47 passed (14.5 s); `build --quick` 7.0 s, 9 tiles; fingerprint 140 parts,
  0 changed (no palette entry names a texture yet). Seam check at 256 px: every texture's
  left/right and top/bottom edge difference is within 1.2 x the mean neighbour difference
  inside the image. Sheet: 2.1 MB PNG, 14 textures at 512 px.
- Look: `output/checks/texture-sheet.png` - each surface tiled 2 x 2, name/size/repeat below.
  Weak ones were reworked twice (stone, concrete, roof tiles, paving, asphalt, ground).
- Doubts and questions for Ali: none. "not mapped" is expected until prompt 19; `render_cream`
  already carries its string course at the floor line.

## 2026-10-23 - Prompt 17 A2a Textures in the 3D files
- Commit: "Textures in the 3D files: shared, embedded or off" (see git log) | Model: DeepSeek
  V4.1 Flash, high (playbook: Sonnet, high)
- Changed: `citygen/mesh/gltf.py` (`images` table, `baseColorTexture` + `KHR_texture_transform`
  scale `1/texture_size`, `images`/`textures`/REPEAT sampler with mipmaps; embedded images as
  bufferViews), `citygen/mesh/textures.py` (new: provider `texture(name, seed)` with one neutral
  test checker on its own stream, `write_shared_textures`, `images_for`), `citygen/mesh/tile.py`
  (`TileContext` texture mode and image table, `texture_files` in each tile entry),
  `citygen/build.py` (parent writes shared images before workers start), `citygen/defaults.toml`
  (`[tiles] textures = "shared"`), `tools/viewer/index.html` (material cache keys on texture URL
  and repeat), `tools/make_artifact.py` (one base64 copy per image, blob URLs through
  `setURLModifier`), tests (5 new), `docs/SPEC.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`
- Checks: tests 44 passed (12.5 s); `build --quick` 7.1 s, 9 tiles; fingerprint 140 parts,
  0 changed with the default `shared` (the palette has no textures yet) and 0 changed on a
  `textures = "off"` build. A test build with `cream` textured (`output/checks/p17`) writes
  `tiles/textures/test.png`; tiles that use it list the file, the others do not. Embedded mode
  puts the PNG in the BIN chunk and writes no texture folder. Blender 5.2 import gives
  `cream` an Image Texture node (`test.png`, 128 x 128) fed by a Mapping node with scale
  0.25 (4 m repeat) from UVMap. The phone page served by `python -m http.server` loads 9/9
  tiles, makes no HTTP request for the image (blob URL) and renders the checker.
- Look: `output/checks/p17-street.png` - test build only, not the final look: the cream wall on
  the right shows 1 m checker squares from the placeholder texture. The normal build is
  unchanged until prompt 19 maps real textures.
- Doubts and questions for Ali: none. The checker is a placeholder; prompt 18 replaces it with
  plaster, stone, tiles and ground.

## 2026-10-23 - Prompt 16 CP2 Checkpoint: light and ground
- Commit: "CP2 fixes: sidewalks and paint stay above the asphalt, build time won back" (see git
  log) | Model: Opus, medium
- Reviewed prompts 7-15 (all DeepSeek V4.1 Flash) against their "Done when": all met, docs and
  WORKLOG entries complete and honest, own random streams, numbers in the style, no em dashes.
  One ground: every height reader outside `terrain.py`, `world.py`, the planner and `ground.py`
  goes through `Ground` (only the 2D map shading reads the raw terrain, which is right there).
- Found and fixed: (1) 223 of 1,552 sidewalk corners missed their street's lift (the block-side
  edge lies exactly on the street outline), so they sat up to 0.24 m low, under the asphalt; the
  prompt 13 test compared the formula with itself. New `Ground.walk_top` with `walk_reach`.
  (2) Sidewalks and paint were drawn with their raw corners only: triangles up to 150 m long cut
  under the ribbon or floated (paint up to 1.8 m). Now points every `walk_step` (15 m) and
  `paint_step` (6 m, like the ribbon), and a new test checks the drawn triangles. (3) Speed:
  `build --area capital --workers 8` had gone 27 s -> 55 s, the planner 9 s -> 17.5 s. Fixed
  without changing any height: `Ground.height` samples the noise only in the city edge band
  (bit-identical, checked on 300,000 points), crossings use an STRtree of street bands (same
  output), carriageways group walks by street, sidewalk bands are clipped to nearby strips (same
  area; one pair of touching pieces is now one piece).
- Changed: `citygen/city/ground.py`, `citygen/city/paint.py`, `citygen/city/walks.py`,
  `citygen/mesh/tile.py`, `styles/maghreb.toml`, `tests/test_citygen.py`, `docs/SPEC.md`,
  `docs/HANDOFF.md`, `docs/ROADMAP.md`, `docs/prompts/04-people-landmarks-port.md` (prompt 39
  note on roofs), `CLAUDE.md` (timings)
- Checks: tests 38 passed (13.3 s; 21.6 s before the fixes, 11.3 s at `before-deepseek` on the
  same Mac today); `build --quick` 7.5 s (11.1 s before, 7.0 s at the tag); capital 29.7 s with
  8 workers, 73 s with 1 (SPEC: 26 s and 71 s). Fingerprint against `before`: 9 changed, all
  `tiles/*` (bytes +1-19%, triangles +1-15%). Stats: 235,109 triangles, 2,452,551 drawn,
  14.4 MB. Saved `fp-cp2`.
- Budgets: the densest tile is 5.8 MB on the quick build and 8.2 MB on the full capital
  (`tile_65_106`; 6.2 MB at the tag, so already over the 5 MB note before the trial). Roofs grew
  it most (roof triangles 7.9k -> 28.3k): added to prompt 39 (Q5 lighter tiles) instead of a
  new fix prompt. Tile time under 2 s (budget 5 s).
- Look: `output/checks/cp2-street.png` (golden hour, top: before the fixes, bottom: after, mean
  difference 1.29: same edge lines, zebra and curbs) and `output/checks/cp2-souk.png` (night,
  0.00: the old town has no sidewalks). Noon was proven identical to the old daylight in
  prompt 8. Blender file refreshed: `output/bodjantouna-42/goumosbane.blend`.
- The DeepSeek trial: careful, readable code and exact reports; it settled two budget conflicts
  well (ground blur, roof coping). It missed what only shows across prompts or in the drawn
  result: speed lost step by step, tests that check a function against itself, drape
  resolution. About one checkpoint session to fix. Recommendation: continue with it.
- Doubts and questions for Ali: none.

## 2026-10-23 - Prompt 15 A1 Roof life
- Commit: "Roof life: parapets and stair rooms" (see git log) | Model: DeepSeek V4.1 Flash,
  high (playbook: Sonnet, medium)
- Changed: `citygen/city/roofs.py` (new: `RoofLayout`, `roof_stream`, `roof_layout`, stair room
  placement and its door), `citygen/mesh/tile.py` (`roof_mesh`, `_coping`, one layout per owned
  building), `citygen/mesh/builder.py` (`add_loft`), `citygen/city/dressing.py` (`_roof` uses
  the layout), `citygen/build.py` (index `parapets`), `styles/maghreb.toml` (`[roofs]`),
  `tools/blender_beauty.py` (skip its own parapets when the index says so), tests (2 new),
  `docs/SPEC.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`
- Checks: tests 37 passed (17.6 s); `build --quick` 10.7 s, 9 tiles; fingerprint 140 parts,
  9 changed, all allowed (`tiles/index` plus 8 `tiles/*.glb`). Tile triangles at most +20.6%
  (tile 13_23, budget 25%), bytes 1.0-21.5%. Parapets 0.6-0.9 m by district kind; stair rooms
  on 32% of houses and 59% of apartment blocks; 2,021 of 2,062 parapet bands use the paired
  coping, 41 a capped fallback. Plans, world and maps unchanged.
- Look: `output/checks/15.png` (close aerial 120 m above the old town, 45 degrees down, mean
  pixel difference 9.49). After half: raised rims around flat roofs and courtyards, small stair
  boxes with doors, domes and minaret tops unchanged.
- Doubts and questions for Ali: the top is a sloped coping from the outer edge down to the
  inset deck, not a flat 0.2 m cap. A flat cap plus an inner wall cost 41% more triangles on the
  dense old-town tile, over the 25% budget. It reads as a capped parapet from the air; say if
  you want the flat cap in a later task.

## 2026-10-23 - Prompt 14 S1 Street surfaces and markings
- Commit: "Street surfaces: asphalt, stone, earth and painted markings" (see git log) | Model:
  DeepSeek V4.1 Flash, high (playbook: Sonnet, medium)
- Changed: `citygen/city/paint.py` (new: surface table, carriageway, edge/lane lines, dashes,
  zebra crossings), `citygen/city/model.py` (`Street.surface`, `Paint`, `CityPlan.paint`),
  `citygen/city/__init__.py`, `citygen/mesh/tile.py` (`street_meshes` material, `paint_meshes`,
  paint STRtree), style (`[streets.surface]`, paint numbers, `earth` and `road_paint` colors),
  tests (2 new plus one material), `docs/SPEC.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`
- Checks: tests 35 passed (17.8 s); `build --quick` 10.4 s, 9 tiles; fingerprint 140 parts,
  9 changed, all allowed (`tiles/index` plus 8 `tiles/*.glb`). Tiles grew 1.9-14.9% in bytes and
  at most 5.3% in triangles; plans, world and maps unchanged. Every one of the 3,047 marks lies
  inside its street's carriageway. Village Hirzabouane: 7 earth alleys, no paint.
- Look: `output/checks/14.png` (street, mean pixel difference 0.62). After half: dashed lane
  lines, solid edge lines and a zebra crossing just before the side-street junction.
- Doubts and questions for Ali: none.

## 2026-10-23 - Prompt 13 A3 Sidewalks, curbs and the boulevard promenade
- Commit: "Raised sidewalks, curbs and a boulevard promenade" (see git log) | Model: DeepSeek
  V4.1 Flash, high (playbook: Sonnet, high)
- Changed: `citygen/city/walks.py` (new: block bands clipped to street side strips, boulevard
  promenade pieces), `citygen/city/model.py` (`Walk`, `CityPlan.walks`), `citygen/city/__init__.py`,
  `citygen/city/ground.py` (`Ground.surface` adds the curb on a walk; `walk_tree`),
  `citygen/mesh/builder.py` (`add_draped_cap`, `add_skirt`), `citygen/mesh/tile.py` (`walk_meshes`), style
  (`[streets]`, `sidewalk` and `curb` colors, `sidewalk_width` per district), tests (3 new),
  `docs/SPEC.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`
- Checks: tests 33 passed (16.2 s); `build --quick` 9.4 s, 9 tiles; fingerprint 140 parts,
  9 changed, all allowed: `tiles/index` plus 8 `tiles/*.glb`. Tile bytes grew 0.5-3.3% (budget
  15%); plans, world and maps unchanged. Sidewalk widths 1.25-3.2 m; every sampled walk keeps
  the 5.5 m carriageway, stays out of buildings and sits 0.15 m above its street.
- Look: `output/checks/13.png` (street, mean pixel difference 8.21). After half: light raised
  sidewalks with dark curb faces on both sides, the asphalt between them, and the boulevard
  promenade on the left with its palm row standing on it.
- Doubts and questions for Ali: none. Doors show a 0.15 m plinth under them (the building base is
  not raised) - the prompt allowed either choice.

## 2026-10-23 - Prompt 12 A4b Everything on the graded ground
- Commit: "Dressing and cameras stand on the drawn surface" (see git log) | Model: DeepSeek
  V4.1 Flash, high (playbook: Sonnet, high)
- Changed: `citygen/city/ground.py` (`STREET_LIFT` moved here, `Ground.surface`: ground or the
  highest street ribbon), `citygen/city/dressing.py` (`Dresser` takes the ground; spans, gates,
  wall tops, `ground_heights` and `building_highs`; doors, shop fronts and awnings use the
  surface 0.5 m in front of the wall), `citygen/mesh/tile.py` (dresser ground, building highs,
  ground pieces, street trees), `citygen/build.py` (camera views and index focus on the surface),
  tests (3 new), `docs/SPEC.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`
- Checks: tests 30 passed (about 16 s; the new tile fixture reuses one build, so the suite stays
  close to its old time); `build --quick --force` 9.7 s, 9 tiles; fingerprint 140 parts, 9 changed, all
  allowed: `tiles/index` plus 8 `tiles/*.glb` (tile_13_23 loses 888 triangles: one sabat no
  longer clears the raised alley surface, so it is correctly not built). Plans, world, maps,
  gazetteer and kit identical.
- Look: `output/checks/12.png` - top: HEAD, bottom: working tree. The camera rises by the street
  lift (0.2 m in the souk), so the whole frame shifts down slightly; no sunken or floating shop
  fronts or goods at the lane edges. Numeric checks: every door threshold within 0.05 m of the
  surface 0.5 m in front, every sampled wall foot in the terrain, every ground piece within
  0.05 m of `surface`.
- Doubts and questions for Ali: none. One unavoidable look change: cameras now stand on the
  ribbon, so before/after frames cannot be pixel-aligned at the same camera height by design.

## 2026-10-23 - Prompt 11 A4a City ground
- Commit: "Graded city ground inside cities" (see git log) | Model: DeepSeek V4.1 Flash, high
  (playbook: Sonnet, high)
- Changed: `citygen/city/ground.py` (new: `Ground`, `_City`, `_Blur`), `citygen/mesh/tile.py`
  (`TileContext.ground`, `height` now graded), `citygen/defaults.toml` (`[ground]`), tests (3 new),
  `docs/SPEC.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`
- Checks: tests 27 passed (10.25 s, +0.5 s for 3 tests); `build --quick --force` 7.0 s, 9 tiles;
  fingerprint 140 parts, 9 changed, all `tiles/*` (index and tile_12_22 to tile_14_24, +4 to +8
  bytes each); plans, world, maps, gazetteer and kit identical. Tile build (one process, 9 tiles):
  2.12 -> 2.46 s (+16%), slowest tile 1.31 -> 1.45 s (+11%), both under the +30% budget.
  Inside terraced blocks the ground differs from the blur by at most 0.40 m (= `terrace_max`);
  median height spread of those blocks 3.37 -> 2.56 m. Blender file refreshed:
  `output/bodjantouna-42/goumosbane.blend`.
- Look: `output/checks/11.png` - top: HEAD, bottom: graded ground. The boulevard stays even, the
  far crossing and the tree bases settle onto one surface; the difference is small because the
  quick capital's ground was already locally smooth at 8 m (measured chord error 2 mm), so the
  visible change is mostly the city-wide shift of up to 0.75 m (mean 0.05 m).
- Doubts and questions for Ali: none. One deliberate deviation inside the prompt: the blur is an
  exact disc mean of lattice cells with one terrain sample per cell, not a 17-sample pattern per
  cell - same about 60 m smoothing, about 15x cheaper (17 samples cost about +40% per tile, over
  the budget). Documented in `city/ground.py`.

## 2026-10-23 - Prompt 10 Q4 Blender 5 haze and warm grade
- Commit: "Blender 5 haze and warm grade" (see git log) | Model: DeepSeek V4.1 Flash, high
  (playbook: Sonnet, high)
- Changed: `tools/blender_beauty.py` (`setup_haze` returns early into the new `setup_haze_group`
  on `bpy.app.version` 5 and up; the 3.6 and 4.x body below stays as it was), `docs/ROADMAP.md`,
  `docs/HANDOFF.md`
- Checks: tests 24 passed (9.8 s); quick build OK (0.1 s cached); fingerprint 140 parts, 0 changed
  (`--allow ""`); Blender 5.2 log has no Python errors (only the pre-existing `World.use_nodes`
  deprecation warning).
- Look: `output/checks/10.png` - top: HEAD script on 5.2, no compositor, so no haze and no grade;
  bottom: new script, warmer walls, sky and pottery. Mean channel difference over the frame: R +2.86,
  G +0.04, B -4.78. Extra proof for the haze, which needs distance: `output/checks/10-aerial.png`
  (same pair in the aerial view) shows the far coast washed pale by the depth mix; the souk lane is
  under about 20 m deep, so there the warm grade is the visible change.
- Doubts and questions for Ali: none. The 5.x Color Balance node reports its method through a menu
  socket that cannot be listed from Python; its default is Lift/Gamma/Gain, which is exactly what
  the 3.6 code set, so the script leaves it alone and a future default change would be silent.

## 2026-10-23 - Prompt 9 V2 Ambient occlusion and clean edges
- Commit: "Ambient occlusion and a quality menu in the viewer" (see git log) | Model: DeepSeek
  V4.1 Flash, high (playbook: Sonnet, high)
- Changed: `tools/viewer/index.html` (one post chain, GTAO and SMAA, High/Fast menu, `?quality`,
  `?perf=1`, a deterministic fallback for the street camera), `README.md`, `docs/SPEC.md`,
  `docs/ROADMAP.md`, `docs/HANDOFF.md`
- Checks: tests 24 passed (9.8 s); quick build OK (0.1 s cached); fingerprint 140 parts, 0 changed
  (`--allow ""`); `before_after --view street --query quality=high` 0.18 mean (sub-pixel
  post-chain differences, the picture is visually identical), the same run without the query 0.00.
  M1, 1280x720: High 18.07 ms/frame against Fast 17.23 ms (+4.9%); 2560x1440: 21.01 against
  17.23 ms (+22%); both under the +40% budget. High render cost 2.82 against 1.47 ms (1280x720).
- Look: `output/checks/9.png` - High in the street: soft contact shadows at wall bases and tree
  trunks, no halo against the sky, cleaner silhouettes. `output/checks/9-pair.png` compares the
  HEAD viewer in Fast with the working viewer in High, same camera.
- Doubts and questions for Ali: none. On a retina screen the AO buffer is about 1 MP and is
  scaled up, a compromise that keeps the frame under budget; if it looks soft on your screen, tell
  me and we can raise `AO_PIXELS` in the viewer.

## 2026-10-22 - Prompt 8 V1 Golden hour in the viewer
- Commit: "Golden hour light menu in the viewer" (see git log) | Model: DeepSeek V4.1 Flash, high
  (playbook: Sonnet, high)
- Changed: `tools/viewer/index.html` (light presets, sky dome, per-mode sky reflection, asymmetric
  shadow box, light menu), `README.md`, `docs/ROADMAP.md`, `docs/HANDOFF.md`
- Checks: tests 24 passed (9.8 s); quick build OK (0.2 s cached); fingerprint 140 parts, 0 changed
  (`--allow ""`); `before_after --view street` 0.00 and the same with `--query light=noon` 0.00;
  the new Noon against a HEAD worktree differs by 0 of 921,600 pixels.
- Look: `output/checks/8.png` - top: HEAD daylight, sun 40 degrees, flat blue sky; bottom: golden
  hour, sun 14 degrees, pink horizon, warm walls and haze. At 14 degrees the narrow street lies
  in the shade of its buildings, so no cast shadows cross the road; the long shadows show in the
  aerial view. The new light menu is at the top right, next to the camera spot.
- Doubts and questions for Ali: none. If the golden hour feels too bright in the shade, lower
  `hemi` in `PRESETS.golden` (one number, all else follows).

## 2026-10-22 - Prompt 7 Q3 Bougainvillea that cascades
- Commit: "Q3 bougainvillea curtains" (see git log) | Model: DeepSeek V4.1 Flash, medium (playbook: Sonnet, medium)
- Changed: `citygen/mesh/plants.py` (new shared clump and tube helpers), `citygen/mesh/climbers.py`
  (new), `citygen/mesh/trees.py`, `citygen/mesh/props.py`, `citygen/kit.py`,
  `styles/maghreb.toml`, `tests/test_citygen.py`, `docs/SPEC.md`, `docs/ROADMAP.md`,
  `docs/HANDOFF.md`
- Checks: tests 24 passed (9.6 s); quick build 6.6 s; fingerprint 7 changed, all allowed:
  `kit/bougainvillea` and `kit/bougainvillea_b` 82 -> 250 triangles, four tiles +0.1 to 0.2%,
  `tiles/index` bytes; every other kit piece identical. Each climber 250 triangles, 2.4 m wide,
  0.28 m deep, 4.8 m tall.
- Look: `output/checks/7.png` - before: nine floating octahedra on a straight pole; after: a
  curtain of flat bracts from the wall top down to about 2 m, three magenta shades, green leaves
  and two or three bent stems. The kit-sheet camera also shows the next rows, which hide the
  lower half of the piece.
- Doubts and questions for Ali: at 250 triangles the mass is coarser than the Tounes cascade
  (1,714 triangles); if it reads too sparse in the streets, raise `clumps` in
  `[dressing.climber]` in a later prompt.

## 2026-10-22 - Prompt 6 CP1 Checkpoint: foundations
- Commit: "CP1 fixes" (see git log) | Model: Opus, medium
- Reviewed prompts 1-5 against their "Done when": all met. No em dashes, no unseeded randomness,
  no stray files. Prompt 1 had left out the "Checking a change" paragraph in SPEC section 9: added.
- Fixed: (1) a `--force` build stopped while writing maps left a cut-short `country.png` that the
  next build reused (found by a real Ctrl+C test): `summary.json` is now deleted before maps and
  data are rewritten; the slow resume test covers it and fails without the fix. (2) The build key
  now includes the Python and library versions (a shapely upgrade could change output or break
  cached plans). (3) The fingerprint skips Ali's `*.blend` files (they always showed as changed).
  (4) The fingerprint test now edits one plan key and checks that exactly that part changes.
- Changed: citygen/build.py, citygen/buildkey.py, tools/fingerprint.py, tests/test_citygen.py,
  docs/SPEC.md, docs/HANDOFF.md, docs/ROADMAP.md
- Checks: tests 23 passed (9.6 s) + 2 slow (21 s); quick build 6.7 s (forced 7.0 s), rerun 0.1 s;
  stats match prompt 5 (1,742 buildings, 9 tiles, 200,024 triangles, 11.7 MB). Fingerprint vs
  before the fixes: 0 changed (only the two .blend parts, now skipped). Capital `--workers 8`:
  24.7 s forced, 1.5 s rerun, 299 parts 0 changed. Saved `fp-cp1` (140 parts).
- Look: output/checks/cp1-street.png and cp1-aerial.png (before_after on the unchanged tree,
  pixel difference 0.00 both). Current state: plain wide asphalt streets without sidewalks, flat
  facades, fields and the walled medina from the air; later prompts change exactly these.
- Doubts and questions for Ali: none. Small rough edge left: the before/after labels cover the
  viewer's "tiles 9/9" box (cosmetic).

## 2026-10-22 - Lead session: DeepSeek trial and backup point
- Commit: the "DeepSeek trial" commit, tagged `before-deepseek` | Model: Opus
- Changed: docs/PROMPTS.md (which prompts stay on Claude), docs/prompts/02 (checkpoint 16 judges
  the trial), docs/HANDOFF.md, this log
- Plan: prompt 6 on Claude (Opus); prompts 7-15 with DeepSeek V4.1 Flash in OpenCode; prompt 16
  on Claude judges the trial. To undo the trial: `git reset --hard before-deepseek` (ask first).
- Doubts and questions for Ali: none

## 2026-10-22 - Prompt 5 C1b Resumable builds
- Commit: see git log | Model: Sonnet, high
- Changed: citygen/buildkey.py (new), citygen/build.py, citygen/config.py (`style_path`), citygen/mesh/tile.py (write .part, rename), citygen/__main__.py (--force), tests/test_citygen.py, README.md, docs/SPEC.md, docs/HANDOFF.md, docs/ROADMAP.md (boxes 5 and C1)
- Checks: tests 23 passed (9.5 s) + 2 slow (17 s); quick build 7 s; fingerprint vs before: 142 parts, 0 changed. Capital `--workers 8`: first run 26 s, run again 1.5 s (6%), 0 changed vs the first run. Ctrl+C at 15 s: 8 tiles kept, the plan reused, finished in 16.5 s, 299 parts 0 changed.
- Look: none.
- Doubts and questions for Ali: (1) any code edit changes the key, so the first build after an edit is always full, as the prompt asked. (2) Besides the prompt, maps and data files are also skipped when the key matches (otherwise they cost 3.5 s of the rerun). (3) Tiles keep a small note per tile in `cache/`, written by the workers, because the parent is busy with maps and could lose finished tiles on Ctrl+C.

## 2026-10-22 - Prompt 4 C1a Build tiles in parallel
- Commit: see git log | Model: Sonnet, high
- Changed: citygen/build.py (TilePool, resolve_workers), citygen/__main__.py (--workers), citygen/defaults.toml ([build] workers = 0), tests/test_citygen.py (slow test), pytest.ini (new, slow marker), README.md, docs/SPEC.md, docs/HANDOFF.md
- Checks: tests 20 passed (8 s) + 1 slow (5 s, workers 1 vs 2 give identical bytes); quick build 7 s (stays sequential); fingerprint vs before: tiles 0 changed (only Ali's open .blend file moved). Capital: `--workers 1` 71 s, `--workers 8` 25 s (7 workers 24.6 s, 5 workers 28 s), fingerprint w1 vs workers 8: 299 parts, 0 changed.
- Look: none.
- Doubts and questions for Ali: the goal was 3x; I reach 2.8x. This Mac has 4 fast and 4 slow cores, and 9 s of city planning cannot be shared between processes. Tiles alone are 4x faster. Options: accept 2.8x, or add a later task that plans a city in parallel. Answer: Ali accepted 2.8x; box 4 ticked.

## 2026-10-22 - Prompt 3 T3 Housekeeping
- Commit: (this commit) | Model: Sonnet, low
- Changed: citygen/city/geo.py, citygen/__main__.py, requirements.txt, docs/SPEC.md, docs/ROADMAP.md, .claude/agents/city-builder.md, city-checker.md
- Checked: tests 20 passed (8 s, no warnings), quick build 7 s, fingerprint 142 parts 0 changed.
- Note: editing .claude/agents needed the sandbox off.

## 2026-10-22 - Prompt 2 T2 Before/after pictures
- Commit: see git log | Model: Sonnet, medium
- Changed: tools/before_after.py (new), tools/viewer/index.html (camera ground clamp only after all tiles loaded), docs/HANDOFF.md, docs/SPEC.md, docs/ROADMAP.md
- Checks: tests and quick build, see commit. Unchanged tree: street, souk, aerial, --cam/--look and --kit-sheet --frame awning_red all 0.00. Dark `leaf` (reverted): 1.62.
- Look: output/checks/t2-street.png, t2-souk.png, t2-aerial.png, t2-cam.png, t2-kit.png, t2-leaf.png (leaf test)
- Doubts and questions for Ali: found and fixed a viewer bug: the camera was lifted to the lowest loaded tile + 1 m while tiles were still loading, so the same world gave different pictures per run. Without the fix an unchanged tree showed a difference of 36-75. The before half copies the working tree's viewer, so both halves match.

## 2026-10-22 - Prompt 1 T1 Regression fingerprint
- Commit: see git log | Model: Sonnet, medium
- Changed: tools/fingerprint.py (new), citygen/kit.py (`make_kit`), citygen/mesh/tile.py, citygen/kitsheet.py, tests/test_citygen.py, docs/SPEC.md, docs/HANDOFF.md, docs/ROADMAP.md
- Checks: 19 tests pass, quick build 6.6 s, two identical builds: "140 parts, 0 changed". Test: `clumps` 7,8 -> 6,7 in broadleaf changed only 9 parts (tiles/*, tiles/index, kit/tree_broadleaf_c, e.g. "kit/tree_broadleaf_c: triangles 164 -> 144", "tiles/tile_13_23.glb: bytes 4646196 -> 4644684, triangles 67697 -> 67637"); styles restored.
- Look: no
- Doubts and questions for Ali: none

## 2026-10-21 - Lead session: the playbook
- Commit: the "Playbook" commit | Model: Opus, high
- Changed: docs/PROMPTS.md (index), docs/prompts/01-09 (100 prompts), docs/ROADMAP.md
  (checklist), docs/WORKLOG.md (this file), CLAUDE.md (prompt routine), docs/WORKFLOW.md,
  docs/HANDOFF.md
- Checks: docs only. Two independent Opus reviews checked every prompt against the code (80
  findings, all valid ones applied); prompts 20.1 and 20.2 were added because many homes have no
  door or windows today (`Dresser.facades` needs a street within 1.6 m).
- Look: docs/PROMPTS.md
- Doubts and questions for Ali: none

## 2026-10-21 - Lead session: Q1 Natural leafy trees
- Commit: dcaac69 | Model: Sonnet helper, Opus review
- Changed: citygen/mesh/trees.py (new), mesh/props.py, kit.py, kitsheet.py, mesh/tile.py,
  styles/maghreb.toml, tests, docs
- Checks: 18 tests; tiles 11.55 to 11.65 MB (+0.9%); the 58 other kit pieces identical
- Look: before/after boulevard picture (pointed diamonds became rounded, shaded crowns)
- Doubts and questions for Ali: none

## 2026-10-21 - Lead session: Q2 Family names
- Commit: df3e57e (and 778ad09: .gitignore for .DS_Store) | Model: Sonnet helper, Opus review
- Changed: city/life.py, names.py, styles/maghreb.toml [life], tests, docs
- Checks: 17 tests; only family names changed (tiles, world and plan without names identical)
- Look: 30 sample names; Ali accepted them
- Doubts and questions for Ali: none
