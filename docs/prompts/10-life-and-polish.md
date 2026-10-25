# Prompts 101-120: hero assets and city life

Read only the section of your prompt and the rules of its track just below. `CLAUDE.md` gives the
routine every prompt follows.

Ali asked for these two tracks on 25 October 2026, to come after prompt 100 and the lead's full
review: every asset polished one by one, "at least like Léo" (his own Blender character), and a
city with life, where people move in long loops "as if they had lives". The tracks are interleaved:
**K** (kit polish: hero-quality assets) and **L** (city life). The Blender route of prompt 38
(`tools/blender_kit_export.py`) is tested but has not yet carried a single city asset: the K
prompts are its first real use.

## Rules for every K prompt (the polish method)

1. **Target first.** A reference board in `docs/art/<asset>.md`: what the real thing looks like in
   Tunisia (in words, or Ali's own photos if he gives some; never images copied from the web), what
   must read at 2 m, 20 m and 200 m, the palette names, and the triangle budget of each level (hero,
   tile, lod1).
2. **The right tool.** Organic things (people, trees, cloth) are modeled in Blender: a Blender Python
   source in `art/<kit>/` exported by `tools/blender_kit_export.py`, a model Ali makes, or live in
   Ali's open Blender through the Blender connector, whose `look` shows the model from every side
   (never start Blender any other way: `CLAUDE.md`). Regular things (doors, windows, stalls) stay in
   code when the code stays short.
3. **Look like a judge.** Pictures from `tools/asset_review.py` (prompt 101): the same fixed cameras
   before and after, never one picture alone; the GPU browser pane for close-ups and night (headless
   snapshots draw some things wrong).
4. **Two review rounds with Ali.** Round 1 ends with the review sheet and the question "what should
   change?"; round 2 applies his words. The prompt is done only when Ali says it is good.
5. **Budgets.** Hero meshes are drawn only near the camera (prompt 103); tiles and the phone page stay
   light. The fingerprint changes only for the asset's pieces and the tiles that use them; keep piece
   names, anchors and roles so nothing else moves.

## Rules for every L prompt (city life)

1. **Determinism.** One day of the city is a pure function of the seed and the time: streams
   `stream(seed, "life", ...)` only, never an existing stream; `?time=fri+13:10` shows the same scene
   every time.
2. **One design.** `docs/LIFE.md` (prompt 102) decides formats, budgets and the animation technique;
   later prompts follow it and update it when they learn something.
3. **Budgets.** The data per city and the frame time on Ali's M1 stay within the limits of
   `docs/LIFE.md`; measure in the GPU browser pane, not headless.
4. **Commands** that write life files get the two-process test of `CLAUDE.md`.

## 101. K1 - Asset review tool

Model: Sonnet | Effort: high | Size: M | Needs: 2, 38 | Look: a review sheet

**Do.** `tools/asset_review.py PIECE [--ref HEAD]` makes one labelled sheet that judges one kit piece
fairly, before (a git ref) and after (the working tree), from cameras that never change between the two:
1. kit-sheet close-ups framed on the piece's real size (tall pieces fit: `before_after.py --frame`
   cuts the top of an 8 m tree), front and three-quarter, at noon and at golden hour;
2. three city cameras where the piece stands most often: eye level (1.7 m above `Ground.surface`,
   8-15 m from one instance), street (25 m away) and air (45-60 m up); heights from the ground, never
   guessed, never inside a building;
3. the piece's triangles per level and the bytes it adds to tiles, printed on the sheet.
Share code with `before_after.py` and `snapshot.py` (move helpers, no copies). Write
`docs/art/README.md`: the polish method above, in plain words for Ali.

**Check.** Fingerprint: `--allow ""`. Tests: the camera finder is deterministic, keeps cameras above
the ground and outside buildings, and frames the whole piece.

**Done when.** One command makes the fair comparison the model duel needed by hand
(`output/checks/model-duel-3-way.png`, 25 October).

## 102. L1 - City life: the design

Model: Opus | Effort: high | Size: design | Needs: 80, 71, 41 | Look: the summary

**Do.** Design how the city lives in `docs/LIFE.md`, then adjust prompts 103-119 to it. Decide and
explain:
1. **The week.** A 24-hour clock with three kinds of day (weekday, Friday, weekend) looping as a week,
   in a Tunisian rhythm: bakers and fishermen before dawn, the souk in the morning, lunch at home,
   afternoon work, evening cafés and corniche walks, quiet nights. Prayer times and opening hours in the
   style (`[life.day]`).
2. **Who goes where.** Activities from each resident's age and occupation (prompt 80) and the places the
   plan has (homes, shops and souk trades, mosques, the station, the port, the cathedral, the theatre,
   kiosks); the places it lacks (schools, cafés, hammams, offices, workshops) and the cheapest honest way
   to add them (a role on an existing building before a new one; new buildings appended at the end).
3. **Routes.** Entrance to entrance on the street graph (prompts 70-71); walking speed by age; which trips
   are walked, driven or made by louage, taxi or train.
4. **Data and budgets.** What the build exports and what the viewer computes; a size limit per city (aim:
   a few MB for the capital, loaded by area); how many people move at once near the camera on Ali's M1
   (aim: 2,000 at 60 fps) and what is drawn farther away; how the movers and the tile crowd
   (`city/crowd.py`) share the streets without doubles.
5. **Animated figures.** Skinned meshes, morph targets or vertex animation textures for thousands of
   instanced walkers in three.js (and later Godot); the rig and the clips prompt 104 must deliver (walk,
   stand, sit, carry, a child's walk).
6. **The clock.** Time slider, speeds, `?time=` in the URL, the light following the time.
7. **The order.** Confirm or change the order of prompts 103-119.
Measure before deciding: a throwaway page with 2,000 instanced animated boxes gives the real frame time
on the M1. Write a one-page summary for Ali in plain words.

**Check.** Fingerprint: `--allow ""`.

**Done when.** Ali reads the summary and agrees.

## 103. K2 - Hero detail near the camera

Model: Opus | Effort: high | Size: M | Needs: 101, 41, 38 | Look: Ali (GPU pane)

**Do.** Any kit piece may have a third, richer level: `hero`, drawn only within `hero_distance` of the
camera (about 40 m, in the style). Hero meshes live in one shared file per kit (`hero/<kit>.glb`,
loaded once, on demand), never inside tiles; the viewer swaps nearby instances to the hero mesh and back
with hysteresis (as prompt 41 does for tiles), keeping every transform. The Blender export reads a `lod`
custom property (`hero`, `tile`, `lod1`); the kit and the index list which pieces have a hero. The phone
page and snapshots without `?hero=1` stay as today.

**Check.** Fingerprint: `tiles/index` (the hero list) and nothing else in tiles. Tests: a fixture piece
with a hero exports, loads and swaps by distance; tile bytes unchanged. Frame time in the GPU pane with
200 hero instances near the camera within 10% of today.

**Done when.** A test piece turns rich as you walk up to it, and the city stays as fast.

## 104. K3 - Hero people

Model: Opus | Effort: high | Size: L | Needs: 102, 103 | Look: Ali (review sheets)

**Do.** The seven figures (`jebba`, `shirt`, `safsari`, `dress`, `hijab`, `boy`, `girl`, in all their
poses: walk, stand, sit, carry) remade with the polish method: a reference board first
(`docs/art/people.md`: Tunisian dress, proportions by age, how the cloth falls), then Blender sources in
`art/people/`: one shared body with the rig prompt 102 chose, clothes per costume, hands and feet, a
simple face that reads at 2 m, folds that catch the light. Three levels: hero (up to about 15,000
triangles: only the few people within 40 m use it), tile (about today's bytes) and lod1. Keep every
piece name, pose and role, so the crowd, the cards and the households keep working.

**Check.** Fingerprint: the person pieces and the tiles that show people (bytes within +10%). Tests: the
same names and poses as before, every level and the rig present, feet on the ground.

**Done when.** Ali says they look like real Tunisians in the street and hold up next to his own Blender
work (Léo) at street distance.

## 105. L2 - Daily schedules

Model: Sonnet | Effort: high | Size: M | Needs: 102, 80 | Look: a sample

**Do.** As `docs/LIFE.md` decides: every resident gets a week of plans (activities, each with a place and
start and end minutes), places assigned by rules (the nearest school, a workplace matching the
household's trade, a mosque and a café near home, the souk for shopping), from
`stream(seed, "life", "plan", b, m)` (b = the building, m = the member). Export the format of
`docs/LIFE.md`; `python -m citygen life CITY --at "fri 13:10"` prints where people are (counts by kind of
place) and one family's day.

**Check.** Fingerprint: the new life files only. Tests: every day covers 24 hours without gaps; everyone
sleeps at home; children are at school in school hours; the counts at 10:00 and 23:00 are plausible; two
processes write the same bytes.

**Done when.** Three sample families' days read like real Tunisian days.

## 106. L3 - Routes on the street graph

Model: Sonnet | Effort: high | Size: M | Needs: 105, 71 | Look: a map

**Do.** Every trip becomes a route on the street graph, entrance to entrance (shortest by time; souks
and alleys for walkers, roads for vehicles), with walking speed by age and start times set so people
arrive on time. Store or recompute routes as `docs/LIFE.md` decides, within its size limit. A map: one
hour of trips drawn over the city map, thicker where more people walk.

**Check.** Fingerprint: the life files only. Tests: routes are continuous along graph edges; durations
equal length over speed; two processes write the same bytes.

**Done when.** The map shows believable flows: to the souk in the morning, home at noon, to the corniche
at golden hour.

## 107. L4 - Animated walkers

Model: Opus | Effort: high | Size: L | Needs: 104 | Look: Ali (viewer)

**Do.** The clips `docs/LIFE.md` asks for (walk, stand, sit, carry, a child's walk) on the rig of prompt
104, made in Blender and exported for instanced crowds with the technique `docs/LIFE.md` chose (for
example vertex animation textures: each person has their own phase and speed, so a crowd never moves in
unison). A test page (`?test=walkers`) shows 2,000 animated people.

**Check.** Fingerprint: the person pieces only. Tests: clips loop without a jump; feet slide less than a
few centimeters per step at the walking speed; the export is byte-identical twice.

**Done when.** 2,000 walkers move naturally at 60 fps on Ali's M1 (GPU pane).

## 108. L5 - The living viewer

Model: Opus | Effort: high | Size: L | Needs: 106, 107 | Look: Ali (viewer at four times)

**Do.** The viewer plays the city's day: a clock (time slider; play at 1x, 10x and 60x; pause; `?time=`
in the URL) and the light following it (sun, golden hour, night lamps and windows). People near the
camera walk their routes, go in and out of doors and sit in cafés; farther away they are drawn as
`docs/LIFE.md` decides; the tile crowd steps aside where movers walk. Clicking a walker shows who they
are and where they are going.

**Check.** Fingerprint: `--allow ""` unless `docs/LIFE.md` puts data in tiles. Tests: positions at a
given time match `citygen life --at` for a sample; two snapshots at the same time are identical; frame
time within the budget.

**Done when.** At 08:00, 13:00, 19:00 and 23:00 the same street looks and feels different, and Ali can
sit and watch it live.

## 109. L6 - City rhythms

Model: Sonnet | Effort: high | Size: M | Needs: 108 | Look: four times of day

**Do.** The details that make the day true: shutters and stalls open and close by the hour, the souk
busy in the morning, Friday prayer crowds around the mosques, school gates at 08:00 and 16:30, cafés full
in the evening, families on the corniche at golden hour, delivery carts and mopeds at dawn, lit windows
where people are home. Numbers in `[life.rhythm]`.

**Check.** Tests: opening hours hold; window lights follow who is home; deterministic.

**Done when.** Four pictures of the same souk (08:00, Friday 13:00, 19:00, 23:00) tell the time without
a clock.

## 110. CP10 - Checkpoint: hero people and city life

Model: Opus | Effort: high | Size: review | Needs: 101-109 | Look: the report

The checkpoint routine of prompt 6 for prompts 101-109, plus: a whole day is deterministic (two
processes, three times of day); life data sizes and frame times against `docs/LIFE.md`; hero swaps at
tile edges; the people with Ali (review sheets and the live viewer); `docs/LIFE.md` and `docs/art/`
tell the truth.

## 111. K4 - Hero trees and palms

Model: Opus | Effort: high | Size: M | Needs: 103 | Look: Ali (review sheets)

**Do.** The polish method for the trees: palms (fronds that droop and catch the light, a scaled trunk),
broadleaf, olive, citrus, and the cemetery cypress (the model duel winner, with the duel's note: its
tufts read as diamonds up close). Hero levels may use alpha-cut leaf cards near the camera; tile levels
keep today's budgets (about 120-300 triangles).

**Check.** Fingerprint: the tree pieces and the tiles with trees (bytes within +5%).

**Done when.** Ali says the palm alleys and the street trees look real at eye level and from the air.

## 112. K5 - Hero vehicles

Model: Sonnet | Effort: high | Size: M | Needs: 103 | Look: Ali (review sheets)

**Do.** The polish method for every vehicle of the kit (`car_sedan`, `car_hatch`, `car_taxi`,
`car_louage`, `car_van` and their colors, `tounes/moped_delivery`, `tounes/cart_handcart`): true
silhouettes, wheels, glass, lights that glow at night, hero detail near the camera. Prompt 113 drives
them: wheels as separate parts if `docs/LIFE.md` wants them to turn.

**Check.** Fingerprint: the vehicle pieces and the tiles that use them.

**Done when.** A parked row on the boulevard passes Ali's close look.

## 113. L7 - Traffic

Model: Opus | Effort: high | Size: L | Needs: 108, 112 | Look: Ali (viewer)

**Do.** Vehicles live the day too: cars leave their parking spots in the morning and come back in the
evening, louages and taxis carry people between the station and the districts, mopeds and handcarts
deliver at the souk's edges at dawn, trains run to a timetable on the rail line. Simple, believable
rules: lanes, keeping distance, slowing at junctions, stopping for people crossing where `docs/LIFE.md`
says.

**Check.** Tests: no two vehicles overlap on an edge; timetables hold; deterministic; frame time within
the budget.

**Done when.** The boulevard has believable traffic at 08:00 and is calm at 03:00.

## 114. K6 - Facade pieces

Model: Sonnet | Effort: high | Size: M | Needs: 103 | Look: Ali (review sheets)

**Do.** The polish method for what every facade carries: the studded doors of the medina, shop
shutters, windows and their shutters, iron grilles, balconies and mashrabiya. Regular shapes in code;
ornaments (studs, arches, grille patterns) as hero detail. Keep piece names, anchors and door spots
(prompt 20.1).

**Check.** Fingerprint: the facade pieces and the tiles that use them.

**Done when.** A medina alley and a colonial street pass Ali's close look.

## 115. K7 - Souk and café pieces

Model: Sonnet | Effort: high | Size: M | Needs: 103 | Look: Ali (review sheets)

**Do.** The polish method for the souk (stalls, awnings, the goods of each trade, carpets, lanterns) and
for the cafés and kiosks (chairs, tables, tea glasses, chicha pipes, terrace awnings). The goods follow
the households' souk trades.

**Check.** Fingerprint: the souk and café pieces and the tiles that use them.

**Done when.** Ali finds the souk rich and true at eye level.

## 116. L8 - Follow a life

Model: Sonnet | Effort: high | Size: M | Needs: 108, 82 | Look: Ali (viewer)

**Do.** Click a person and press F: the camera follows them through their day (behind them in the
street, waiting at the café, watching their door at night), with a small card (name, age, occupation,
family, where they go next; prompts 80-84). Notable residents (prompt 82's families and guilds) get
recognizable routines: the imam, the baker, the fisherman. `?follow=<resident>` replays one person's day.

**Check.** Tests: following stays on the person through doors and day changes; deterministic.

**Done when.** Ali follows one person from morning to night and it feels like a life.

## 117. K8 - Street furniture and boats

Model: Sonnet | Effort: medium | Size: M | Needs: 103 | Look: Ali (review sheets)

**Do.** The polish method for lamps, benches, kiosks, signs and bollards, and for the port's boats
(`boat_rowing`, `boat_lateen`, `boat_cabin`, `boat_trawler`) and cargo.

**Check.** Fingerprint: those pieces and the tiles that use them.

**Done when.** The corniche and the port pass Ali's close look.

## 118. K9 - Landmark close-ups

Model: Sonnet | Effort: high | Size: M | Needs: 103 | Look: Ali (review sheets)

**Do.** Hero detail where people walk up to the landmarks: minaret tiles and balconies, dome ribs, the
cathedral's portal, the medina gates, the kasbah, the station's clock, the theatre's facade, the
lighthouse. Near the camera only; tiles unchanged.

**Check.** Fingerprint: `tiles/index` (the hero list) only.

**Done when.** Each landmark holds up at the foot of its walls.

## 119. L9 - City life in Godot

Model: Sonnet | Effort: high | Size: M | Needs: 74, 108 | Look: Ali (Godot)

**Do.** The Godot walker of prompt 73 meets the same day: residents walk their routes with their
animations, at the time of day of the Godot sky (prompt 74), from the same life files. Ask Ali before
installing anything, as prompts 72-75 do.

**Done when.** Walking down the boulevard in Godot at 08:00 shows the morning crowd of the web viewer.

## 120. CP11 - Checkpoint: hero assets and city life

Model: Opus | Effort: high | Size: review | Needs: 101-119 | Look: everything

The checkpoint routine of prompt 6 for prompts 110-119, then both tracks as a whole: every polished
family side by side from the same cameras (`tools/asset_review.py`), budgets (tiles, hero files, the
phone page, life data), frame times, a week that is deterministic, and docs that tell the truth
(`docs/LIFE.md`, `docs/art/`, SPEC, HANDOFF, README). Update `docs/REVIEW.md` (what is world-class, what
is next) and report to Ali in under 15 plain lines.
