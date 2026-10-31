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
- State: prompts 1-50 are done (branch `claude/procedural-city-generator-xop72h`; CP4, prompt 43, on 25
  October; the interiors 44-47 on 29 October, 48 (walls and openings) on 30-31 October). Continue when Ali
  says (for example "Do prompt 49." or "continue the playbook").
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
  instead (a billing test passed); how to use it: `docs/LEAD.md`, section 4.

## 2026-10-31 - Open items 47.1 + 48.1 Plan faults and colonial flats
- Commit: (lead commits) | Model: Opus 5.5 | Part 1 of 3 (48.1, old town, shops, villas, maisons), after the
  lead's round 2; parts 2 (slabs) and 3 (colonial flats) follow.
- Changed: new citygen/interior/plancheck.py (`faults`: wall and entry-step checks in the plan, called by
  `rooms.check`; `trim`: hair strips of finished rooms, and rooms all hair strip, join a neighbour of their
  unit; `settle`: inner openings slide to a place the walls accept, a passage narrows to the run both rooms
  face, court openings that fit nowhere go); layout.py (`trim` and `settle` after every plan, `reveals`,
  masses sharing an edge are one storey, the shop's lines without `front_keep`); dar.py (`Job.steps_need`,
  `entry_keep`, `zs(shallow=)`, `rules["plan"]`, a dar is planned again without the steps' room when that
  room leaves the court in sight, the screen leaves the steps room, baffle and screen off the door, ladders
  off the entry steps); cuts.py (`zone(front=)`; `trim`: arms from 0.005 m2, hair strips of skifas and stair
  cells too, any room but a court takes a hair strip); stairs.py (`steps` shortens the landing to `turn_min`
  before treads go under `tread_min`, `steps_depth`, `surely_unclear` for speed); compact.py (small house
  entry strip); spine.py (`unwrap`: the host's hair arm round a carved sdb or wc joins it); villa.py
  (`to_landing`: hair strips of rooms along the U stair box join the palier); rooms.py (zones with
  `front_keep`); styles/maghreb.toml (`[interiors.checks]` probe, passage_min; walls `front_keep`, `reveal`,
  `reveal_wall`; stairs `turn_min` 0.6, `tread_min`); tests (1 new; `OPEN_48` empty; named open lists, see
  below); SPEC 6c, HANDOFF.
- Checks: survey (`tools/interior_survey.py`, the new checks; "before" = today's plans: old town exact,
  Ain Chilel = rooms.check passes less those with wall or step faults):

  | group | before (old check) | before (new checks) | after | bar | slowest before -> after |
  |---|---|---|---|---|---|
  | dar (159) | 151 | 84 | 136 (86%) | 152 | 0.07 -> 0.11 s |
  | compact (277) | 273 | 196 | 257 (93%) | 264 | 0.11 -> 0.14 s |
  | small (83) | 81 | 61 | 77 (93%) | 79 | 0.07 -> 0.08 s |
  | koubba (22) | 21 | 17 | 19 (86%) | 21 | 0.02 -> 0.02 s |
  | shop (136) | 135 | 86 | 120 (88%) | 130 | 0.27 -> 0.29 s |
  | villa (178, Ain Chilel) | 171 | about 58 | 157 (88%) | 170 | 0.43 -> 0.37 s |
  | maison (616, Ain Chilel) | 589 | about 472 | 554 (90%) | 586 | 0.65 -> 0.68 s |
  | slab (353, part 2) | 326 | | 308 (87%) | | 2.03 -> 2.13 s |
  | colonial (270, part 3) | 117 | | 83 (31%) | | 13.0 -> 16.4 s (No. 773) |

  0 crashes. Every interior that passes `rooms.check` gives 0 `mesh.faults` and 0 entry-step faults (plan
  + walls + the prompt 49 tread, riser and headroom test, every old-town house, villa and maison:
  `h471_mesh.py`). `pytest -q` 129 passed; slow tests pass (`test_open_samples_are_valid` xfail); `build
  --quick` done; fingerprint `--allow ""`: 282 parts, 0 changed. Court seen from the street door: 9 dars
  (8 before). Ladder warnings: compact 1 -> 14, villa 2 -> 5, maison 31 -> 46 (open, below).
- Bar NOT met. Classes left, by count: old town: 28 entry steps a shallow skifa band, annex or entry strip
  cannot hold with treads of 0.2 m and a 0.6 m landing (rises 0.6-2.4 m; a turned flight is needed, a new
  stair form not built here); 9 courts seen (one more than before); 9 openings on footprint spikes
  narrower than two walls (lot shape); villas and maisons (classified with `h471_cls.py`): 13 + 2 arches a
  couloir squeezed between the U stair's palier and a wall narrows below 0.8 m, 7 doors with no valid
  place, 7 + 4 windows and partitions at a palier, the program rest (no chambre, chambre over the most, U
  stair not reaching every floor) as before.
- Ladders (lead point 1), cause found, not fixed: compact's 13 new ladders are houses whose roof stair room
  stands over the street door; the newel had to stand under it, a sliver off the door wall (every one of
  them a wall fault: a partition across the street door, 5 also on the entry steps). With a cell kept off
  the door the newel goes to a corner and a ladder rises to the roof (1-floor houses: only that ladder).
  Villa and maison: the U stair box may no longer stand a sliver off a window wall; letting it (front_keep
  behind doors only) brings the ladders back to 2/34 but passes fall to 119/378. A real fix needs the
  street door opening into the stair cell, or turned entry steps: a choice for the lead. So
  `test_old_town_stairs` still accepts the stair room's ladder.
- Look: output/checks/471-old.png (dar No. 525: the screen skifa gives the steps 1.5 m; dar No. 213: the
  hair-thin ghorfa arm round the droj gone; compact No. 104: the stair room over the street door, a ladder
  in the skifa beside the steps), output/checks/471-villa.png (villa No. 230: wc and sdb with their own
  doors; villa No. 232: the one-storey wing is part of floor 0).
- Choices (for Ali): entry steps keep at least 0.6 m of floor past the top tread (`turn_min`, lead) before
  their treads go under 0.2 m; a court window or door the walls cannot hold is dropped (the doors pass
  places what is still needed); a narrowed passage keeps at least 0.8 m (`passage_min`); hair strips (under
  0.3 m) join a neighbour (a palier, a skifa, a stair cell may take them); a dar keeps its bent entry before
  room for its steps; reveals cut up to 0.2 m into the next wall where it stays 0.15 m thick.
- Named open lists in the tests: `OPEN_OLD` {211: a 1.12 m rise in a 1.36 m skifa band}, `OPEN_STEPS`
  {482, 501: domed houses whose annex is too shallow for 1.0-1.3 m rises}, `OPEN_PALIER` {villa 363, maison
  852, 863, 864: a couloir squeezed between the palier and a wall}; the stair test's ladder case (above).
- Doubts: colonial No. 773 got slower (13 -> 16 s, deeper zones); domed house No. 570 still fails (its
  annex strip, 47.1 list).

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
