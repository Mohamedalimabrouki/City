# Prompts 44-58: interiors and hero scenes

Read only the section of your prompt. `CLAUDE.md` gives the routine every prompt follows.
Prompt 44 (the design, SPEC 6c) rewrote prompts 45-50 with exact details; prompts 52-55 are first
drafts that prompt 51 rewrites. Always follow the latest text of your section.

Interiors are made on demand, never stored in a normal build, so the normal fingerprint check
of these prompts is `--allow ""` (plus new furniture pieces in prompts 52-53). Interiors exist
only for dwellings: houses (with or without a courtyard), domed houses, apartment blocks, villas
and the shops of souks.

## 44. H1 - Interiors: the design (no code)

Model: Opus | Effort: high | Size: L (plan) | Needs: 15, 20.2 | Look: no

**Goal.** Design interiors on demand: the inside of any of the 40,000 houses is generated only
when a scene, a game or a picture needs it, always the same for the same seed, never stored.

**Read.** SPEC (all), `city/model.py`, `city/buildings.py` (how each building kind is made;
courtyards are holes in the footprint, and most medina houses have none), `city/dressing.py`
(`facades`, `building`, `_front`, `_windows`, `pick`, `put`: the doors and windows an interior
must match), `mesh/tile.py` (`building_mesh`, `building_highs`, the parapets and stair rooms of
prompt 15), `city/life.py` (one household per dwelling), `kit.py`.

**Design, in a new SPEC section "Interiors".**
1. Command and lookup: `python -m citygen interior BUILDING [--folder BUILD] [--out FOLDER]`
   (and later `scene`) take a build folder (default: the latest) and rebuild world and plan
   from the settings stored in it (add the merged settings to `summary.json`), reusing the plan
   cache of prompt 5. Building numbers only mean something for that build. The viewer's "who
   lives here" card shows the number, and "Open interior" passes the folder it is showing.
2. Matching the outside: the facade bridge builds the `Kit` exactly like `TileContext` (seed,
   `[build] kits`, palette, `[dressing.trees]`: role picks only draw when the kit has pieces, so
   another kit set moves windows) and calls `Dresser.building(k, high)` with the tile's `high`
   (`building_highs` on the graded ground). Opening sizes come from the piece bounds
   (`Piece.width`, `Piece.height`). When the door's ground is more than 0.15 m below floor 0,
   add steps inside the skifa or hall. Partition walls meet a facade at least 0.3 m from any
   door or window (tested). Say how every dwelling is entered and lit (prompts 20.1 and 20.2
   give every dwelling a door and windows).
3. Data model: rooms (polygon, floor, type, height), openings (doors between rooms, windows on
   facades) and their link to the facade openings. Apartment blocks hold one plan household but
   several flats: flats get derived occupants from `stream(seed, "interior", city, building,
   "flat", n)` without touching `plan.households`; the plan household lives in flat 0; lit flats
   follow the same-floor-same-side rule of prompt 21.
4. Random streams: `stream(seed, "interior", city, building, ...)`.
5. Layouts, authentic to Tunisia:
   - Courtyard house (dar): street door into a bent skifa (vestibule with benches; the bend
     hides the courtyard from the street), the courtyard (wast ed dar, open to the sky, with the
     cistern mouth (majel), a tree or, in rich houses, a fountain and galleries of arches),
     rooms (bit) along its sides in the T layout (a long room with a central door on the
     courtyard, a recessed alcove (kbou) opposite the door, small side rooms (maqsura) at both
     ends), kitchen, storage, bathroom, stairs (droj) to the roof terrace (stah), sometimes an
     upper room over the skifa.
   - House without a courtyard (the most common medina house): skifa or hall, a covered central
     room lit from above (skylight), rooms around it.
   - Domed house: one koubba room plus a small annex.
   - Apartment block: stair core, landings, two to four flats per floor typed the Tunisian way
     (S+1, S+2, S+3: salon plus bedrooms), kitchen, bathroom, a balcony where the facade has one.
   - Villa: hall, salon, dining room, bedrooms upstairs, kitchen, terrace, garage.
   - Shop (hanout): shop room and a back room. (A doukkana is the built-in bench, not a shop.)
   - No interior for walls, towers, minarets, mosque courts, sheds, the kasbah, cathedral,
     theatre or station. Mosque halls and marabouts get none, or a bare prayer hall with the
     mihrab on the qibla wall, never household furniture.
6. Heights per floor from the building; wall thicknesses; how stairs fit.
7. Output: a viewable folder like a build (`tiles/interior.glb`, textures embedded, plus
   `tiles/index.json` with an `interior` camera view, so snapshots and `before_after.py` work
   from prompt 45 on) and `rooms.json`; tests, including a two-process determinism test.

**Then rewrite the bodies of prompts 45-50** in this file so each is exact (files, functions,
data, tests, a Check line, "Done when"), keeping their numbers, model and effort unless you say
why. Prompt 45 must write the viewable folder; prompt 50 then only adds the cutaway view and the
"Open interior" button. No code; commit docs only.

**Done when.** The SPEC section exists, prompts 45-50 are precise enough for a Sonnet session,
and Ali gets a 10-line plain summary of the design.

## 45. H1a - Interior model and command

Model: Sonnet | Effort: high | Size: M | Needs: 44 | Look: no

**Goal.** The `interior` command and what prompts 46-50 build on: the city rebuilt from a build folder,
the facade bridge, the data model and a viewable folder, with one placeholder room per floor.

**Read.** SPEC 6c "Interiors" once in full (this prompt builds Command, The city from the build folder,
The facade bridge, Coordinates, Data model, Output and Random streams); `build.py` (`select_area`,
`load_or_plan`, the summary), `buildkey.py`, `mesh/tile.py` (`TileContext.__init__`, `build_tile`,
`building_mesh`, `instance_groups`, `write_tile`), `city/dressing.py` (`Dresser.building`, `entrances`,
`keep_roof`, `under_roofs`, `building_highs`, `ground_heights`), `kit.py` (`Piece.bounds`, `Kit.panes`),
`kitsheet.py` (a viewable folder written by hand), `__main__.py`, `tools/before_after.py`,
`tools/fingerprint.py`, `describe` in `tools/viewer/index.html`.

**Do.**
1. `citygen/buildkey.py`: `NOT_BUILD_CODE = ("interior",)`: `_code_hash` skips `citygen/interior/**`;
   `NOT_BUILD_STYLE = ("interiors",)`: `_style_hash(name)` hashes `json.dumps(..., sort_keys=True)` of the
   parsed style (`load_style`) without those tables, and `build_key` uses it instead of the file's bytes.
   Every key changes once (Ali's builds need one rebuild); after that, interior work never makes a build
   stale.
2. `citygen/build.py`: `summary["settings"] = cfg`, the merged settings (`summary.json` is no fingerprint
   part).
3. `tools/fingerprint.py`: skip the top folder `interiors`, as `maps`, `tiles` and `checks`.
4. The package `citygen/interior/`:
   - `__init__.py`: a docstring pointing at SPEC 6c, `InteriorError(Exception)`, `LAYOUTS`.
   - `model.py`: `Storey`, `Room`, `Opening`, `Stair`, `Flat`, `Interior` with `to_json()` (polygons as
     rings, coordinates rounded to 1 mm), fields as SPEC lists them.
   - `context.py`: `BuildContext(world, plans, focus, folder=None)` (the kit, the ground and one `Dresser`
     per city, made lazily as `TileContext` makes them), `load_build(folder, log=print)`, `city_plan(ctx,
     name)`, `layout_of(plan, b)` (the SPEC table; `small` when the footprint area less its holes, shrunk
     by the exterior wall, is under `[interiors.compact] min_area`), `resolve(ctx, plan, spec) -> k` (a
     number or `pick:<layout>[:<floors>]`).
   - `outside.py`: `Outside(ctx, plan, k)`, steps 1-4 of the bridge, with `b`, `k`, `plan`, `district`,
     `high`, `fh`, `roofs`, `placements`, `doors`, `openings` (the facade `Opening`s), `kit`, `warnings`.
   - `layout.py`: `plan_interior(outside, style) -> Interior`: the storeys, then per layout a function;
     for now every layout gets one placeholder room per storey (type `room`, unit `home`) holding the
     facade openings of its floor (`rooms` = (room, -1)). Prompts 46-47 replace these functions.
   - `export.py`: `write_folder(interior, outside, out) -> Path`: the mesh (for now the tile's own shell,
     `building_mesh(mb, b, ground.height, roofs=outside.roofs)` without the plinth, and a floor cap per
     storey at its z in palette `paving`; prompts 48-49 replace both), the instances, `write_glb` with the
     root translation and only the images its materials use, `tiles/index.json` with the views
     `interior` and `overview`, `rooms.json`.
   - `command.py`: `make_interior(folder, building, city=None, out=None, log=print) -> Path`, printing the
     line SPEC "Command" gives.
5. `__main__.py`: the `interior` subcommand (`building`, `--folder`, `--city`, `--out`); an
   `InteriorError` exits with code 2 and its message.
6. `styles/maghreb.toml`: `[interiors]` (`eye` 1.6, `look` 1.4, `margin` 2.0), `[interiors.walls]`,
   `[interiors.openings]` (`frame` 0.12, `clear` 0.3, `door` 0.9), `[interiors.compact] min_area` (35 m2),
   each number with a short comment.
7. The viewer card (`describe` in `tools/viewer/index.html`): a last line "No. <k>" for every building,
   so Ali can name one.
8. `tools/before_after.py --interior SPEC [--city NAME]`: after each side's quick build, run
   `python -m citygen interior SPEC --folder <that build>` in that tree, take the folder from its
   `-> FOLDER` line and snapshot it with `--view` (`interior` or `overview`). A tree without the command
   (exit code not 0) gets a grey half labelled "Before: no interior yet". Update its docstring and SPEC 9.
9. SPEC: mark in 6c what this prompt built; a row for `citygen/interior/` in the module table; the
   `interiors/<city>-<k>/` folder and the `settings` of `summary.json` in the output table. HANDOFF: lessons.

**Tests** (`tests/test_citygen.py`, about 1.5 s in all). A module fixture `interior_build` writes a build
folder in a tmp dir from the `world` and `plan` fixtures, planning nothing again: `summary.json` with
`settings` = `world.cfg`, `area` = `world.cfg["build"]["area"]`, `build_key` = `build_key(world.cfg,
[world.capital().id])`, and `plan` pickled to `cache/<slug>-<key12>.pkl`. Later prompts reuse it.
- `test_interior_folders_for_three_layouts`: `pick:dar`, `pick:compact` and `pick:slab` each write the
  three files; `read_glb` reads the .glb back, its images are embedded, its root translation is (x0, 0, -y0)
  of the index tile; the index has the views `interior` and `overview`; one room per storey; storeys at
  `high + f * fh`.
- `test_interior_openings_match_the_facade`: for those three and `pick:colonial`, every door, window, shop
  and balcony placement of `Outside` (by the SPEC rule) is exactly one opening, its center within 0.02 m of
  its wall's line, with a room on its floor; no warnings.
- `test_outside_replays_the_tile`: for `pick:dar`, `pick:slab` and `pick:colonial`, run `build_tile` on
  the tile owning building k (`TileContext(world, [plan])`, the tile holding k's footprint centroid) with a
  spy on that city's `Dresser.building` that records the list it returns for k. Keep the recorded
  placements still in the tile's final list, by identity: `under_roofs` (`Covers.clear`) and `keep_off`
  return lists of the same objects (checked in prompt 44; `Covers.clear` lowers an awning or wall lamp in
  place, `p.z -= dz`, so both sides see it), and `ground_heights` sets z in place. They must equal
  `Outside.placements`: the same pieces in the same order, x, y and z within 1 mm, the same yaw. One tile
  build costs more than 1 s, so mark it `slow` (the three picks lie nearest the center, usually in one
  tile: build each owning tile once).
- `test_interior_bytes_repeat`: two calls on fresh `BuildContext`s give the same bytes for the three files.
- `test_interior_refuses_what_it_cannot_do`: a summary without `settings` (the message says "Build it
  again"), a minaret (the message names `minaret`), an unknown city (the message lists the build's cities).
- `test_build_key_ignores_interiors`: `_code_hash` covers no file under `citygen/interior/`; a copy of the
  style with an extra `[interiors]` table keys like the original (two tmp files).
- `test_fingerprint_tool`: also, a file under `interiors/` is no part.
- `@pytest.mark.slow` `test_interior_two_processes`: `python -m citygen interior pick:dar --folder <the
  fixture's folder>` with `--out` a and b, in two processes with `PYTHONHASHSEED` 1 and 2: the three files
  are byte-identical.

**Check.** Fingerprint: `--allow ""` (build keys are ignored). Also `.venv/bin/python -m pytest -q -m slow
-k "interior or outside"`, and `.venv/bin/python -m citygen interior pick:dar` on the quick build: it prints its time,
under 5 s. One snapshot proves the folder opens (not a Look): `.venv/bin/python -m citygen snapshot
<that folder> --view interior`.

**Done when.** `python -m citygen interior <n>` writes the folder with one placeholder room per floor and
every facade opening in rooms.json, `citygen view <folder>` opens it, and `before_after.py --interior`
pictures it.

## 46. H1b - Courtyard houses and compact houses

Model: Sonnet | Effort: high | Size: M | Needs: 45 | Look: plan image

**Goal.** Real plans for the old town's houses: the dar round its courtyard and the house without one,
with their newel stairs, entry steps, roof terrace and menzah.

**Read.** SPEC 6c (Walls, Layout engine, Courtyard house, House without a courtyard, Stairs: `newel`,
`steps`, `ladder`, Entering and light), `citygen/interior/` (prompt 45), `city/buildings.py`
(`courtyard_house`), `city/roofs.py` (`roof_layout`, `_stair_candidate`, `_stair_door`, `_menzah`),
`city/geo.py` (`frame`).

**Do.**
1. `interior/cuts.py`: `free_cut(...)` (the SPEC rule), `cut(poly, frame, axis, at)` (both sides of a line
   in a frame), `absorb(rooms, minimums)` (small pieces and undersized rooms join their longest-boundary
   neighbour, which keeps its type), `width(poly)` (twice the polylabel radius).
2. `interior/rooms.py`: `doors(interior, wanted)` (the program's doors, then the breadth-first pass that
   connects or merges), `assign(interior)` (facade openings to rooms), and `check(interior) -> list[str]`:
   coverage, overlaps, reachability (rooms, openings, stairs and the street), minimum sizes, partitions
   clear of openings, every facade opening in a room.
3. `interior/stairs.py`: the newel cell (under the stair room, else a corner), entry `steps`, `ladder`, as
   `Stair` records with risers, riser, tread and door side (their geometry comes in prompt 49).
4. `interior/dar.py`: the bands, the skifa with its bend and baffle, the T room with kbou and maqsuras,
   the other bands, the bortal, court doors and windows (stream `court`), the court features, upper floors
   in enfilade. `interior/compact.py`: `compact` round its covered well (skylight feature,
   `inner_window`s) and `small`. The stah and the menzah on the roof level. `layout.plan_interior` sends
   `dar`, `compact` and `small` there; souk houses keep their shop opening in an ordinary room until 47.
5. Style: `[interiors.walls] cut_shift`, `[interiors.rooms]` (area m2 and width m per type, for example
   bit 7 and 2.0, maqsura 2.5 and 1.2, matbakh 3.5 and 1.4, bit el ma 1.8 and 0.9, bit el mouna 1.5 and
   0.9, skifa 3.5 and 1.2, ghorfa 6 and 1.8), `[interiors.dar]`, `[interiors.compact]`, `[interiors.stairs]` (`newel`, `newel_min`,
   `pier`, `riser_max`, `headroom`, the entry step numbers).
6. `tools/interior_plans.py SPEC[@CITY] ... [--folder BUILD] [--out PNG]`: one PNG (Pillow) with the plans
   of each interior, storeys side by side at one scale (at most 1800 px wide), rooms filled by type (a
   fixed color table in the tool), exterior and court walls black, partitions grey, facade doors red,
   windows blue, inner doors as gaps, stairs hatched with an arrow up, labels in Latin letters (room type,
   flat), a title per interior (No. k, layout, floors, family). `@CITY` may name a settlement the build did
   not plan: the tool then plans it (under a second for a town), so prompt 47 can draw a villa from a
   quick build.
7. SPEC 6c: mark what is built and any rule the code had to settle; HANDOFF: lessons.

**Tests** (about 1.5 s; one module fixture plans, once, the 20 dars, 20 compact and 10 small houses
nearest the center of the 45 fixture's city).
- `test_old_town_plans_are_valid`: `rooms.check()` finds nothing in any of them.
- `test_skifa_hides_the_courtyard`: for the 20 dars, no segment from 3 points across the main door's inner
  face to the court's 1 m grid points stays inside the union of the rooms (each shrunk by half a partition)
  and the door gaps.
- `test_old_town_stairs`: a house with 2-3 floors has its newel cell at the same place on every floor and
  reaches every floor; a house with a stair room has its cell inside the stair room's square, the cell
  door on the stair room door's side and a reachable stah; a door threshold more than 0.15 m off floor 0
  gives `steps`; no ladder but for a menzah.
- `test_interior_plans_tool`: the tool writes a PNG for two specs (no browser needed).

**Check.** Fingerprint: `--allow ""`. Look: `.venv/bin/python tools/interior_plans.py pick:dar:1
pick:dar:2 pick:compact:2 --out output/checks/46.png`. Look at it yourself before you report: the skifa
bends, the main bit faces the court across from the skifa, kitchen and stores sit sensibly, the stairs
stand in a corner or under the stair room.

**Done when.** 20 sampled houses of each kind pass every check and the three plans look right.

## 47. H1c - Apartments, villas, domed houses and shops

Model: Sonnet | Effort: high | Size: L | Needs: 46 | Look: plan image

**Goal.** Every other dwelling: flats in colonial blocks and slabs with their stair cores and occupants,
villas and the houses of the new districts, domed houses, and the shops and cafes of ground floors.

**Read.** SPEC 6c (Shops and cafes, Domed house, Villas and houses of the new districts, Flats, Stairs `u`
and the roof `newel`), `citygen/interior/` (prompts 45-46), `city/dressing.py` (`_sections`,
`stair_columns`, `stair_rows`, `_stair_doors`, `front_of`, `_shop`, `_cafe`, `_house_door`, `_light`),
`city/life.py` (`households`, `family_name`), `city/massing.py` (`masses`, set-back floors, steps).
From prompt 46: reuse `dar.Job`, `cuts` (`free_cut`, `absorb`, `trim`), `rooms` (`place`, `connect`, `repair`,
`check`) and `stairs`; a shop front's zone keeps no `clear` beyond its edges (SPEC 6c Walls), so the hanout's
partition may meet the wall at the shop front's edge but must keep `clear` from the house door; `check` must
stay empty for every layout (the old-town fixture `old_town` shows the pattern).

**Do.**
1. `interior/shop.py`: the hanout and makhzen of a souk house (carved from floor 0 before the dar or
   compact layout runs on the rest) and the qahwa of a colonial cafe; `resolve` learns `pick:shop`.
2. `interior/spine.py`: the engine of hall, couloir and rooms cut across it, from a program list.
3. `interior/villa.py` (`villa`, `maison`), `interior/koubba.py`, `interior/flats.py` (colonial and slab
   cores, landings, flat regions, types, numbering, occupants, lit). `stairs.py` gains the `u` box (with
   its narrow fallback) and the top-floor newel up to a stair room.
4. Style: `[interiors.flats]` (`types`, `two_flats` 130, `min_flat` 40), `[interiors.villa]` (hall,
   couloir, `dining_area`, the programs), `[interiors.shop]`, `[interiors.cafe]`, the `u` numbers in
   `[interiors.stairs]`.
5. SPEC 6c and HANDOFF.

**Tests** (about 2 s). The 45 fixture's city gives slabs, colonial blocks, domed houses and souk houses;
the `villas` fixture's town (a `BuildContext(world, [town], town settlement)`) gives villas and maisons.
- `test_new_district_plans_are_valid`: `rooms.check()` finds nothing for 10 slabs, 10 colonial blocks
  (3 of them with a cafe or shop front), 10 villas (5 with 2 floors), 10 maisons, every domed house and 10
  souk houses with a shop.
- `test_flats`: every flat is reachable from its stair door through its core; its type matches its area;
  flat 0 holds the plan's household and `plan_json(plan)["households"]` is the same before and after;
  flats n >= 1 get the same occupants twice, and not all the same ones.
- `test_slab_flats_follow_the_lit_rule`: in 10 slabs, each flat's front windows are all lit or all dark,
  and its back windows too; a room is lit exactly when one of its windows is.
- `test_shops_stand_apart`: a hanout opens only on the street; the house door leads into the house.
- `test_only_dwellings`: one building of every other kind in the plan is refused.

**Check.** Fingerprint: `--allow ""`. Look: `.venv/bin/python tools/interior_plans.py pick:slab
pick:colonial "pick:villa:2@Ain Chilel" --out output/checks/47.png` (Ain Chilel is settlement 3 of the
quick world, the `villas` fixture's town; check with `python -m citygen list --quick`). Look at it
yourself: cores at the stair doors, S+n flats with the salon on a facade, the villa's hall, salon and stair.

**Done when.** Every dwelling layout (dar, compact, small, koubba, colonial, slab, villa, maison, with
their shops and cafes) gets a valid plan, and other kinds get none.

## 48. H1d - Interior walls and openings

Model: Sonnet | Effort: high | Size: M | Needs: 47 | Look: interior

**Goal.** The plans become walls: thick outer walls with real holes where the facade has its doors and
windows, partitions with doors, arches, and a zellige dado in traditional rooms.

**Read.** SPEC 6c (Walls, Output) and 6 (textured walls, the plinth), `citygen/interior/` (prompts 45-47),
`mesh/builder.py` (`add_walls`, `extrude`, `add_cap`, `add_arch`), `mesh/tile.py` (`building_mesh`,
`roof_mesh`, `street_frontage` and the lines of `build_tile` that compute its `walk_width` and `reach`),
`mesh/textures.py`.
From prompt 46: a skifa is two `skifa` rooms parted by a baffle (or screen) partition whose `arch` opening
reaches the outer wall: draw that partition only outside the arch; a compact house's `well` rooms upstairs
are voids (no floor, a balustrade along their edge) and its covered court's walls are partitions; court
walls are `walls.court` thick (the storey's court grows by it).

**Do.**
1. `interior/mesh.py`, `walls_mesh(mb, interior, outside, style) -> holes`: exterior and court walls as
   solids between the outer face (the footprint ring, in the tile's wall material with meter UVs, v = 0 at
   `high`, and the plinth on the same segments as the tile) and the inner face (`[interiors.palette]
   plaster_inner`); a hole for every opening, with jambs, sill and head in the inner material; partitions
   as solids centered on room boundaries, floor to ceiling, with their door holes; inner doors with a
   wooden frame and leaf (`door_leaf`, `door_frame`), `open_share` (0.4) of them open 70-100 degrees (stream
   `doors`); double leaves for `court_door`s; arches on a bortal's court side (`add_arch`); a `dado` (1.2 m)
   of zellige on the inner faces of the living rooms of `dar`, `compact`, `small` and `koubba` (bit,
   maqsura, skifa, ghorfa, koubba), broken at openings. It returns the holes it cut (opening id,
   rectangle). The facade pieces stay instances, in their holes.
2. `mesh/tile.py`: move `build_tile`'s `walk_width` and `reach` lines into `frontage_inputs(plan) ->
   (walk_width, reach)`, called from there and from the interior (the fingerprint proves the tiles unchanged).
3. `export.py`: the shell is now these walls plus the tile's own roof functions (`roof_mesh` for the flat
   roofs of `outside.roofs`, `add_hip_roof`, `add_dome`); the floor caps stay until prompt 49.
4. `mesh/textures.py`: a generated `zellige` texture (256 px, seamless, an eight-point star and cross tile
   pattern in a few glazed colors, on `stream(seed, "texture", "zellige")`), named only by
   `[interiors.palette] zellige`, so no tile uses it.
5. `[interiors.palette]`: `plaster_inner`, `zellige`, `door_leaf`, `door_frame` (nothing new in `[palette]`).
6. SPEC 6c and HANDOFF.

**Tests** (about 1.5 s).
- `test_interior_holes_match_the_facade`: for 5 interiors of every layout, every facade opening's hole
  matches the opening rectangle of its piece within 0.02 m (center along the wall, width, sill, head); no
  partition crosses a hole; every inner door's hole lies in its partition.
- `test_interior_budget`: the largest slab and the largest dar of the quick capital stay under 150,000
  triangles and 25 MB of .glb.

**Check.** Fingerprint: `--allow ""`. Look: `.venv/bin/python tools/before_after.py --view interior
--interior pick:dar:2 --out output/checks/48.png`, a command of its own; look at it. Then
`.venv/bin/python tools/make_blend.py <that dar's interior folder>`, a command of its own (make_blend was
written for builds: if it cannot read an interior folder, make the smallest fix there; a build's .blend
stays as it was), and name the .blend file for Ali.

**Done when.** The interior folder opens in the viewer and in Blender, and doors and windows line up with
the outside.

## 49. H1e - Floors, ceilings, stairs and roof terrace

Model: Sonnet | Effort: high | Size: M | Needs: 48 | Look: interior

**Goal.** Walkable houses: slabs with their stair wells, ceilings, the stairs themselves, the courtyard
floor and the roof terrace.

**Read.** SPEC 6c (Stairs, Floors and ceilings, Courtyard house: court features and roof), 6b (benches,
kiosks and fountains: `water_pool`), `citygen/interior/` (prompts 45-48), `mesh/tile.py` (`roof_mesh`,
`_coping`, `_opening`), `mesh/furniture.py` (`fountain_colonial`), `city/dressing.py` (`tree`).
From prompt 46: a `Stair` door's yaw is the way out of the cell (`steps`: the way in from the door, a negative
riser going down); a droj room may be larger than its `Stair` square (its landing strips); ladders stand in
the court (menzah), under a stair room no newel reaches, or as the last fallback; `well` rooms get no slab;
the court's trees are already instances (on the ground surface: move them to the paving).

**Do.**
1. `interior/mesh.py`, `floors_mesh`: a slab per storey (`slab` 0.25 m, top at the floor's z) less the
   stair wells, the covered court's light well and the court, with the slot rule; floor finishes (floor
   tiles in traditional houses, `terrazzo` in flats: a generated texture like `zellige`, in
   `[interiors.palette]` only); ceilings under the next slab: painted wooden beams across the shorter span
   every `beam_step` (0.45 m) in traditional rooms (colors on stream `beams`), plaster elsewhere; the
   koubba's ceiling is its dome seen from inside.
2. `stairs_mesh`: newel (pier, steps as prisms with tread and riser, the landing quarter; the cell's walls
   are its partitions), u (two flights with stringers, both landings, an iron railing on the open side),
   entry steps, ladders.
3. The roof: the deck as a slab with the stair room's square as its well; the stair room's inside (walls
   from the deck, a ceiling at deck + `stair_height` whose underside `mesh.overheads` includes, the door
   hole at `RoofLayout.door`); the parapet and
   coping from `roof_mesh`; the menzah's inside.
4. The court: paving `court_step` (0.15 m) under floor 0, the court walls' base meeting it; the majel (a
   round stone curb 0.6 m across and 0.4 m high with a wooden lid); the court trees on the paving (their
   `Dresser.tree` placement with the paving's z); the fesqiya (an octagonal marble basin 1.4 m across,
   water `water_pool`, never `water`); the skylight panel over a covered court.
5. `[interiors.floors]` and `[interiors.palette]` additions; SPEC 6c; HANDOFF.

**Tests** (about 1.5 s).
- `test_stairs_connect_floors_with_headroom`: for every stair of 5 interiors of every layout, the first
  step leaves its floor and the last reaches the next floor (or the roof deck) within 0.01 m; every riser
  is at most its `riser_max` (ladders aside); every tread point on the walking line, 0.1 m apart, has at
  least 2.0 m clear above it against every slab (with its wells), landing and flight of the interior and
  the ceiling of the roof stair room (`stairs.treads(stair)` and `mesh.overheads(interior)` give both).
- `test_court_and_roof`: inland water uses `water_pool` only; court trees stand on the paving; the stair
  room's door on the roof lies within 0.02 m of `RoofLayout.door`; no slab crosses an opening.

**Check.** Fingerprint: `--allow ""`. Look: `.venv/bin/python tools/before_after.py --view interior
--interior pick:dar:2 --out output/checks/49.png`. Then make the interiors of `pick:dar:2` and `pick:slab`
on the quick build and run `.venv/bin/python tools/make_blend.py <folder>` for each, a command of its own;
name the two .blend files for Ali.

**Done when.** A two-floor courtyard house and an apartment block can be walked through in Blender.

## 50. H1f - Interiors in the viewer

Model: Sonnet | Effort: high | Size: M | Needs: 49 | Look: interior

**Goal.** Ali clicks a house in the city and walks into it; an interior can be cut open floor by floor.

**Read.** SPEC 6c (Viewer, Command), `citygen/view.py`, `tools/viewer/index.html` (loading the index and
tiles, views, the card: `describe`, `showInfo`), `tools/viewer/gallery.html`, `tools/make_artifact.py`
(what the phone page swaps), `interior/command.py`.

**Do.**
1. Viewer: `folder=interiors/<name>` (only names matching `^interiors/[a-z0-9-]+$`) prefixes every data
   path (`data/<folder>/tiles/index.json`, its tiles, `rooms.json`). With `index.interior`: a Cut menu
   (none, roof, each floor) and the URL `cut=roof|<floor>`: one global clipping plane
   (`renderer.clippingPlanes`) at that floor's z + `CUT` (1.3 m), or at the roof deck - 0.05 m for roof;
   the orbit target on the building; a click names the room (its type and flat, floor, from rooms.json).
2. `citygen/view.py`: `GET api/interior` answers `{"ok": true}`; `GET api/interior?city=NAME&building=K`
   runs `make_interior(folder, K, city)` (one at a time behind a lock, one `BuildContext` per build folder
   kept while the server runs, so a second interior takes about a second) and answers `{"folder":
   "interiors/<slug>-<k>"}`, or status 400 with `{"error": message}`. The gallery answers the same under
   `/b/<key>/api/interior`.
3. The card: for a dwelling, an "Open interior" button when `api/interior` answers; a click shows "making
   the interior..." and opens `?folder=...&view=interior` in a new tab. Without a server (the phone page)
   the card says "Interiors: open this city with python -m citygen view on the computer".
4. Gallery: `build_folders` also finds `*/interiors/*/tiles/index.json` and
   `*/*/interiors/*/tiles/index.json`; each shows under its index `world_name` with its own Open in 3D.
5. ROADMAP: tick H1 in section H and correct its text (dwellings only). SPEC 6c and HANDOFF.

**Tests** (about 1.5 s).
- `test_view_makes_interiors`: `start_server` on the 45 fixture's folder: `api/interior` answers ok; a
  dar's city and number make the folder and `data/<folder>/tiles/index.json` is served; a minaret gets a
  400 with the message.
- `test_gallery_lists_interiors`: an interior folder under a build appears in `builds()`.

**Check.** Fingerprint: `--allow ""`. Look: `.venv/bin/python tools/before_after.py --view overview
--interior pick:dar:2 --query cut=1 --out output/checks/50.png`. The lead tries "Open interior" in the
browser pane (click a house, open it, cut it, orbit).

**Done when.** From the viewer, clicking a house and "Open interior" shows its rooms; one snapshot of an
interior. Tick H1.

## 51. H2 - Furnishing: the design (no code)

Model: Opus | Effort: medium | Size: L (plan) | Needs: 50 | Look: no

**Design, in a SPEC section "Furnishing".**
1. Catalog per room type and era. Traditional: built-in banquettes (doukkana) with mattresses
   and cushions along the walls, klim and mergoum carpets, low round tables (meida), carved
   chests (sendouk), brass lanterns, trays and tea sets, oil jars (khabia), a couscoussier and a
   clay brazier (kanoun), mirrors, canopy beds in the maqsura alcoves, a loom for weavers.
   Modern: sofa set, TV, fridge, gas stove with its butane bottle, beds, wardrobes, dining table
   and chairs, a desk with books, a washing machine on the balcony.
2. Placement rules: along walls, facing the door, clearances for doors, windows and stairs, by
   room function; the household changes it (wealth, trade, members: a tailor's sewing machine,
   a teacher's books, children's beds). Flats use their derived occupants.
3. Density levels `sparse`, `lived-in`, `full`; random streams; triangle budgets per room. New
   pieces get their own streams (never the shared "props" stream).
4. Rewrite prompts 52-55 in this file so each is exact, with Check lines. No code; commit docs
   only.

**Done when.** The SPEC section exists and prompts 52-55 are precise.

## 52. H2a - Traditional furniture pieces

Model: Sonnet | Effort: high | Size: M | Needs: 51 | Look: kit sheet

Draft. The traditional catalog from SPEC as pieces (a new `mesh/furniture.py`, category
`furniture`), low-poly but rich (100-600 triangles), carpets with small generated pattern
textures (the texture code of prompt 18).

**Check.** Fingerprint: only the new `kit/<furniture piece>` parts appear.

**Done when.** The kit sheet shows every traditional piece and each reads clearly.

## 53. H2b - Modern furniture pieces

Model: Sonnet | Effort: medium | Size: M | Needs: 51 | Look: kit sheet

Draft. The modern catalog from SPEC as pieces in the same module and category.

**Check.** Fingerprint: only the new `kit/<furniture piece>` parts appear.

**Done when.** The kit sheet shows every modern piece.

## 54. H2c - Furnishing rules and density

Model: Sonnet | Effort: high | Size: M | Needs: 52, 53 | Look: interior

Draft. Place furniture per room with `[interiors] density`, wall-aligned with clearances and the
household's influence. Tests: no overlaps, doors and windows clear, piece counts grow with
density.

**Check.** Fingerprint: `--allow ""`.

**Done when.** A "lived-in" courtyard house looks inhabited in the interior snapshot.

## 55. H2d - Light, textiles and clutter

Model: Sonnet | Effort: medium | Size: S | Needs: 54 | Look: interior at night

Draft. Interior lights (lanterns and ceiling lamps glow at night), textiles on walls, plants in
the courtyard, small clutter (tea glasses on trays, shoes at the doors, books), all scaled by
density; the viewer's night mode works inside.

**Check.** Fingerprint: `--allow ""`.

**Done when.** The night interior snapshot looks warm and lived-in. Tick H2.

## 56. H4a - Hero scenes

Model: Sonnet | Effort: high | Size: M | Needs: 55 | Look: hero scene

**Do.**
1. `python -m citygen scene (--building N | --block N | --street N) [--folder BUILD]
   [--out FOLDER]` writes one scene at full detail: the chosen block or street with all
   dressing and people, embedded textures, the furnished interiors of the chosen building or of
   every dwelling of the block, the surrounding terrain and neighbors as context. The rest of
   the world stays out.
2. Buildings with interiors drop their solid tile shell and use the interior's exterior walls
   with cut openings and see-through glass, so rooms show through windows and doors.
3. Write the scene like a build (`tiles/scene.glb` plus `tiles/index.json` with the focus and the
   cameras as `views`), and store the cameras as glTF camera nodes too (Blender, three.js and
   Godot import them).
4. A two-process determinism test.

**Check.** Fingerprint: `--allow ""` on the normal build. Look: `citygen view <scene folder>`
(one snapshot).

**Done when.** A scene of one souk block opens in the viewer and in Blender, under 60 MB, with
rooms visible through open doors.

## 57. H4b - Hero scenes in Blender

Model: Sonnet | Effort: high | Size: M | Needs: 56, 10 | Look: Blender render

**Do.** `tools/blender_scene.py`: import a scene, set up the beauty look of
`tools/blender_beauty.py` (golden-hour sky, haze, materials), use the scene's camera nodes
(street and interior), save a `.blend` and render both cameras (small sizes while testing).
Interiors need their own light: light portals in window and courtyard openings, the lanterns of
prompt 55 as small lights, and an exposure per camera, so the interior render is not black or
noisy at test samples.

**Check.** Fingerprint: `--allow ""`.

**Done when.** One golden-hour street render and one interior render of the same scene, both in
`output/checks/`. Tick H4.

## 58. CP5 - Checkpoint: interiors

Model: Opus | Effort: medium | Size: review | Needs: 44-57 | Look: interior + hero render

Follow the checkpoint routine of prompt 6 (`## 6.` in docs/prompts/01-foundations.md) for
prompts 44 to 57, comparing with `cp4`. Extra checks:
- Generate interiors for 30 random dwellings of every dwelling kind on several seeds: no crash,
  every check passes, a few plans look right to you; non-dwellings get no interior.
- Inside matches outside (doors and windows), stairs reach the roof stair room, flats in
  apartment blocks match their lit windows.
- Authenticity: room names and furniture make sense for a Tunisian home; ask Ali to look at
  one courtyard house and one apartment.
Save `fingerprint save cp5`. Fix prompts go in `## 58.1. ...`.
