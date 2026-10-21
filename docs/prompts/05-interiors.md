# Prompts 44-58: interiors and hero scenes

Read only the section of your prompt. `CLAUDE.md` gives the routine every prompt follows.
Prompts 45-50 and 52-55 are first drafts: prompts 44 and 51 (the designs) rewrite them with
exact details. Always follow the latest text of your section.

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

Draft (prompt 44 refines it). Follow SPEC "Interiors". A `citygen/interior/` package with the
data model (Room, Opening, Interior), the `interior` command with its build-folder lookup, the
facade bridge (the Kit and `high` exactly as in tiles) and the JSON output, written as a
viewable folder (`tiles/interior.glb`, `tiles/index.json` with an `interior` view). The viewer
card shows the building number. Tests: deterministic output for three dwelling kinds (also
across two processes with different PYTHONHASHSEED); every facade door and window of the
building appears as an opening.

**Check.** Fingerprint: `--allow ""`.

**Done when.** `python -m citygen interior <n>` writes a folder with one placeholder room per
floor and all facade openings, and `citygen view` opens it.

## 46. H1b - Courtyard houses and compact houses

Model: Sonnet | Effort: high | Size: M | Needs: 45 | Look: plan image

Draft. The courtyard-house layout from SPEC (bent skifa, courtyard, T-shaped rooms around it,
kitchen, storage, bathroom, stairs to the roof at the stair room of prompt 15 when there is one)
and the house without a courtyard (hall, covered central room, rooms around). Tests: rooms cover
the floor without overlap, every room is reachable from the street door (graph), no straight
line of sight from the street door into the courtyard, minimum room sizes, partitions clear of
openings. One image: top-down plans of three houses drawn with Pillow (Latin labels only).

**Check.** Fingerprint: `--allow ""`.

**Done when.** 20 sampled houses of each kind pass every check and the three plans look right.

## 47. H1c - Apartments, villas, domed houses and shops

Model: Sonnet | Effort: high | Size: M | Needs: 46 | Look: plan image

Draft. Layouts from SPEC for apartment blocks (stair core, landings, S+1 to S+3 flats per floor,
balconies behind facade balconies, derived flat occupants), villas, domed houses and souk shops.
The same tests as prompt 46 per kind; one image with three plans.

**Check.** Fingerprint: `--allow ""`.

**Done when.** Every dwelling kind (house with and without a courtyard, domed house, apartment
block, villa, shop) gets a valid plan; non-dwellings get none.

## 48. H1d - Interior walls and openings

Model: Sonnet | Effort: high | Size: M | Needs: 47 | Look: interior

Draft. Meshes: exterior walls 0.4-0.5 m and interior walls 0.15-0.25 m thick, door openings with
frames and leaves (some open), window openings exactly where the facade windows are, arches
between courtyard galleries and rooms in traditional houses, a zellige tile band (dado) in
traditional rooms. Test: openings line up with the facade pieces within 2 cm.

**Check.** Fingerprint: `--allow ""`.

**Done when.** The interior folder opens in the viewer and in Blender, and doors and windows
line up with the outside.

## 49. H1e - Floors, ceilings, stairs and roof terrace

Model: Sonnet | Effort: high | Size: M | Needs: 48 | Look: interior

Draft. Floor slabs per storey (tiles in traditional houses, terrazzo in apartments), ceilings
(painted wooden beams in traditional rooms), stairs (straight or L-shaped flights in the stair
core or stair room), the roof terrace with its parapet and the stair room door, the courtyard
floor with the majel, a tree (the courtyard trees of prompt 24) or a fountain. Inland water uses
the `water_pool` palette material (never `water`, which Blender renders invisible). Tests:
stairs connect the floors; headroom over 2.0 m.

**Check.** Fingerprint: `--allow ""`.

**Done when.** A two-floor courtyard house and an apartment block can be walked through in
Blender.

## 50. H1f - Interiors in the viewer

Model: Sonnet | Effort: high | Size: M | Needs: 49 | Look: interior

Draft. A cutaway mode for interior folders in the viewer (roof and upper floors hidden on
demand, orbit around). In the city viewer, the house card gets "Open interior" when the local
`view` server can run the generator (it passes its build folder; the phone page shows a note
instead).

**Check.** Fingerprint: `--allow ""`.

**Done when.** From the viewer, clicking a house and "Open interior" shows its rooms; one
snapshot of an interior. Tick H1.

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
