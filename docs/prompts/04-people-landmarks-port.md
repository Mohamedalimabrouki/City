# Prompts 28-43: people, landmarks, port, performance

Read only the section of your prompt. `CLAUDE.md` gives the routine every prompt follows.
Landmarks change the plan: adding them to `plan.buildings` before `households()` shifts every
later household. Append landmark buildings at the end of the list (and give space-takers their
own stream), and record in your WORKLOG entry which plan parts changed and why.

## 28. P1 - People: low-poly figures

Model: Sonnet | Effort: high | Size: M | Needs: 2 | Look: kit sheet

**Goal.** Streets need people. Stylized low-poly figures that fit the low-poly city: clear
silhouettes, no faces, respectful and recognizably North African without caricature.

**Do.**
1. New `citygen/mesh/people.py`: a figure builder (head, torso, arms, legs, simple hands and
   feet; 200-400 triangles) with poses: standing, walking (mid-stride), sitting (hips at 0.45 m
   to fit `cafe_set` chairs and benches), carrying (basket or bag), and a child scale.
2. Outfits as separate pieces: jebba (long robe) with a red chechia; shirt and trousers; a woman
   in a white safsari (wrap); a woman in a modern dress with or without a headscarf; children.
   Cloth colors from a `cloth_*` palette set; a few warm skin tones.
3. Catalog pieces `person_<outfit>_<pose>`, category `person`, ground anchor; small proportion
   jitter on their own streams; 20-30 pieces in all (each tile stores only those it uses).

**Check.** Fingerprint: only new `kit/person_*` parts. Look: `--kit-sheet --frame` on a
person; also judge the silhouettes from street eye height in the viewer.

**Done when.** Figures read as people at 20 m, sitting poses fit benches and cafe chairs,
400 triangles at most each.

## 29. P2 - People in the streets

Model: Sonnet | Effort: medium | Size: M | Needs: 28, 13 | Look: souk

**Do.**
1. Placement rules in a `[people]` style table: souks dense (browsing at shop fronts, walking
   in the middle), cafes (seated at cafe sets), sidewalks and the boulevard promenade (strollers,
   pairs, families), near the great mosque and the gates, villages sparse.
2. Each person stands on `Ground.surface`, faces along the street or toward the shop or table;
   outfit mix by district (more jebba and safsari in the medina, more modern clothes in colonial
   and modern districts); own stream per street or facade.
3. Tile-local; nobody inside a building, a car, a stall or another person.
4. `[people] density` (1.0 default) scales everything for lighter builds. Drawn triangles +30%
   and tile bytes +10% at most at density 1.
5. Test: no person inside a footprint, a car or within 0.5 m of another person.

**Check.** Fingerprint may change: `tiles/*`. Look: `--view souk`.

**Done when.** The souk feels busy but walkable, cafes have customers, nobody floats, sinks or
overlaps.

## 30. A5a - The kasbah

Model: Sonnet | Effort: high | Size: M | Needs: 12 | Look: aerial

**Goal.** A walled citadel with towers on the old town's highest edge, like the kasbahs of
Tunis or Sousse.

**Read.** `city/medina.py` (`old_town`, `ramparts`, `gates`, `mosque_complex`), `city/__init__.py`
(`plan_city` order), `city/model.py` (`Landmark`), `export/lore.py`, `export/maps.py`.

**Do.**
1. Only for real medinas: a style flag (`kasbah = true` for capital and city) - `old_town` also
   runs for villages, where it must not appear.
2. In the planner, after the old town outline and before alleys: find the highest point near the
   medina wall (sample the outline); the kasbah is a rough rectangle with a side of
   clamp(0.3 x medina width, 60, 160) m touching the wall there, never over the great mosque
   site, a gate, or a souk that runs from a gate to the mosque; alleys, souks and houses avoid it.
3. Thick walls (2.5 m) taller than the ramparts, square towers at the corners and every 40-60 m,
   a monumental gate toward the medina; inside a governor's palace (courtyard building), a small
   mosque with a square minaret and an open parade ground.
4. Geometry as `Building`s appended at the end of the list (walls and towers through the path
   ramparts already use, or a new kind that `building_mesh` handles), a `stone_kasbah` palette
   material, a `Landmark(kind="kasbah")` with a generated name on its own stream.
5. The city map shows it; the gazetteer lists it.

**Check.** Fingerprint may change: `plan/*` (space is taken), `tiles/*`, `maps/*`, `gazetteer`.
Tile bytes +10% at most. Look: `--view aerial`.

**Done when.** The kasbah dominates the high edge of the old town at a sensible size; the
building-validity and off-street tests pass.

## 31. A5b - Covered souks

Model: Sonnet | Effort: high | Size: M | Needs: 2 | Look: souk

**Do.**
1. The main souks (style: the N longest souk streets, or souks of chosen trades such as the
   perfumers) get roofs: barrel vaults, or flat timber and reed roofs on arches, with light
   openings (round oculi or slots) every few meters. Half the medina houses have one floor
   (3.4 m), so spring the roof at min(adjacent wall tops, 4 m), keep the crown at most 2 m
   higher, and fill the wall up to the springing where a house is lower.
2. Built per tile from the street line, like `sabat_mesh`; each segment belongs to the tile
   containing its midpoint, and the roof is continuous across tile edges.
3. Under a covered stretch: no sabats, bunting or lantern strings; hanging lanterns instead
   (the dressing and the mesh share one deterministic `covered` rule).
4. The souk camera still sees the stalls; night mode still glows.

**Check.** Fingerprint may change: `tiles/*` (and `plan/*/souks` if you store the flag). Tile
bytes +10% at most. Look: `--view souk`.

**Done when.** A covered market with openings for light, resting on the houses; no prop pierces
the roof.

## 32. A5c - Cathedral and theatre on the boulevard

Model: Sonnet | Effort: high | Size: M | Needs: 22 | Look: street

**Do.**
1. Two landmarks in the colonial district: a cathedral (nave with a gabled roof, two front
   towers with small domes or pyramids, a rose window, front steps) and a municipal theatre
   (Art Nouveau: rounded corners, a central crown or dome, big arched windows, a decorated
   parapet). Colonial parcels average 380 m2: merge 3-6 adjacent boulevard-facing parcels per
   landmark before buildings are made, on its own stream.
2. Place them 50-300 m ahead of the street camera (see `build.camera_views`), or add a camera
   view that frames them.
3. New builder functions (a `mesh/landmarks.py`: gables, towers, a rose window ring, arched
   windows as geometry), `Building.kind` = `cathedral` / `theatre` dispatched in
   `building_mesh`, `Landmark`s with generated names; no household lives in them.

**Check.** Fingerprint may change: `plan/*`, `tiles/*`, `maps/*`, `gazetteer`. Tile bytes +10%
at most. Look: `--view street`.

**Done when.** Both stand on the boulevard and read clearly from the street camera; under 6,000
triangles each.

## 33. A5d - Train station and clock tower

Model: Sonnet | Effort: medium | Size: M | Needs: 1 | Look: aerial

**Do.** A station at the colonial district's edge toward the main country road or the port: a
long hall with a pitched roof, an arched entrance, a square clock tower with clock faces,
platform canopies, and 2-4 tracks (rails as thin steel ribbons on a sleeper-colored bed) running
out to the city edge. Cut the rail corridor (tracks plus 4 m) before `make_blocks`, passed in
`extra_cuts` like the medina cut, so no building stands on the tracks. Own streams; a `Landmark`
with a generated name.

**Check.** Fingerprint may change: `plan/*`, `tiles/*`, `maps/*`, `gazetteer`. Tile bytes +10%
at most. Look: `--view aerial`.

**Done when.** The station, its clock tower and tracks leaving the city through a clear corridor.
Tick A5 when 30-33 are all done.

## 34. A6a - Quays, breakwater and lighthouse

Model: Sonnet | Effort: high | Size: M | Needs: 12 | Look: port

**Do.**
1. In port districts the coastline becomes straight concrete quays (2 m above the sea, bollards
   as instances), filling small coves (edit `plan.land` at plan time).
2. A breakwater: a curved rubble mound (jittered rock blocks or a rough-profile ribbon) from the
   port's end into the sea, enclosing a harbor, with a small lighthouse at its tip (`Landmark`
   with a generated name).
3. Plan-level geometry in a new `city/port.py` on its own streams; meshes in tiles; the city map
   draws them.
4. A `port` camera view in `build.camera_views` (the aerial camera looks away from the sea here:
   the harbor is about 2 km away in its background).

**Check.** Fingerprint may change: `plan/*`, `tiles/*`, `tiles/index`, `maps/*`, `gazetteer`.
Look: `--view port` (the before half falls back to aerial).

**Done when.** A harbor with quays, a breakwater and a lighthouse, seen from the port camera.

## 35. A6b - Boats and cranes

Model: Sonnet | Effort: medium | Size: M | Needs: 34 | Look: port

**Do.** A new `CityPlan.props` list (kind, x, y, yaw, scale), exported in plan.json (update SPEC
sections 5 and 6), filled by the port planner on its own stream: fishing boats (blue and white
hulls with a small cabin or mast, three variants) moored along quays and drawn up on beaches,
a few trawlers, two or three lattice cranes and stacked crates on the commercial quay. The
dresser draws `plan.props` with the rule "the center decides the tile".

**Check.** Fingerprint may change: `plan/*/props` (new), `tiles/*`, and the new `kit/boat_*`,
`kit/crane*` parts. Tile bytes +10% at most. Look: `--view port`.

**Done when.** A working harbor; boats float at sea level and touch no quay.

## 36. A6c - Corniche promenade and beach

Model: Sonnet | Effort: medium | Size: M | Needs: 34, 13 | Look: corniche

**Read first.** `street_trees` already plants palm rows on the corniche at +-(width/2 - 2.5 m),
inside the carriageway; the water line is only about 18-20 m from the corniche center line; the
corniche also passes port, industrial and cemetery districts.

**Do.**
1. Along colonial, modern and residential stretches of the corniche, on the sea side: a paved
   promenade (6-10 m where it fits) with a low sea wall and railing, lamps and benches facing
   the sea; move the beach-side palm row onto the promenade. A sand beach beyond it only where
   room remains; elsewhere the sea wall stands at the water.
2. A `corniche` camera view in `build.camera_views` (eye level on the promenade, looking along
   it) and in the viewer's menu.

**Check.** Fingerprint may change: `tiles/*`, `tiles/index`, and if `street_trees` changes,
`plan/*/trees,plan/*/stats,gazetteer,maps/*`. Tile bytes +10% at most. Look: `--view corniche`
(the before half falls back to aerial).

**Done when.** Promenade, railing, palms, benches and beach or sea wall read clearly from the
corniche camera. Tick A6 when 34-36 are done.

## 37. H3c - Seaside cafe terraces

Model: Sonnet | Effort: medium | Size: S | Needs: 36, 29 | Look: corniche

**Do.** Cafe terraces on the promenade: groups of `cafe_set` tables under parasols (new
`parasol` piece: pole and octagonal canvas, three colors) with seated people (the rules of
prompt 29), in front of buildings facing the corniche and as small kiosk cafes on the
promenade; chances in the style; own streams. Test: no table on the carriageway or the railing.

**Check.** Fingerprint may change: `tiles/*` and the new `kit/parasol*` parts. Look:
`--view corniche`.

**Done when.** Terraces with parasols and customers along the corniche. Tick H3.

## 38. A8 - Blender kit export

Model: Sonnet | Effort: medium | Size: S | Needs: 1 | Look: no

**Do.**
1. `tools/blender_kit_export.py`: every object of a Blender collection becomes
   `kits/<name>/<object>.glb` plus a `manifest.json` (`citygen-kit/1`: category and anchor from
   custom properties; material colors written as sRGB hex, converted from Blender's linear
   values).
2. Axes: a piece's front is generator +y (SPEC 6b), which is +Y in Blender; Blender's glTF
   exporter maps +Y to glTF -Z, the front citygen expects. Rotate pieces modeled facing -Y by
   180 degrees about Z. Bake rotation and scale into the mesh (`read_parts` ignores node
   transforms); the origin is the anchor.
3. `citygen kit-sheet --kits ...` (default: `[build] kits`), so another kit can be shown.
4. Test it headlessly with Blender 5.2 (run outside the sandbox if needed): a script makes an
   asymmetric piece whose front must land at glTF -Z and a second simple piece, exports them,
   `Kit` loads them and the kit sheet shows both facing the right way.
5. Document it in SPEC 6b and the README.

**Check.** Fingerprint: no change to the real build.

**Done when.** A kit made in Blender shows in the kit sheet facing the street, and a role in a
test copy of the style uses one of its pieces. Tick A8.

## 39. Q5 - Lighter tiles

Model: Sonnet | Effort: high | Size: M | Needs: 1 | Look: souk

**Goal.** The heaviest dressed old-town tile under 3.5 MB with no visible loss up close; all
tiles smaller.

**Do.**
1. Measure first: bytes per tile by category (terrain, buildings, each instanced piece, textures)
   with a `python -m citygen stats --tiles` option.
2. `KHR_mesh_quantization` (listed in `extensionsRequired`), switch `[tiles] quantize = true`:
   - positions as normalized int16 with a dequantization scale on the tile mesh's own child
     node (a node scale would also scale `EXT_mesh_gpu_instancing` translations and skew
     rotations): keep instanced piece geometry in float, or fold a uniform scale into the
     instances' SCALE and TRANSLATION;
   - normals as int8; UVs as int16 only for materials with tile-local UVs, with the scale in
     `KHR_texture_transform` (terrain and roof caps use world meters up to 64 km: keep them
     float);
   - keep float for materials with tiny offsets (`road_paint` 0.03 m above streets, `add_sheet`
     cloth 0.005-0.02 m thick), where 1-2 cm steps would break them;
   - instance rotations as normalized int16 if precise enough.
3. Teach both readers the new types: `read_parts` in `mesh/gltf.py` (int8 and int16 in its dtype
   table, normalization) and `instance_transforms` in `tools/blender_import.py` (used by
   `blender_beauty.py` too).
4. If still over budget: merge rarely used big pieces. Do not drop pieces by distance to the
   build focus: a tile must not depend on the area built (it breaks tile locality and resume).
5. Check that three.js and Blender 5.2 read the result; note for prompt 72 what Godot supports.

**Check.** Fingerprint may change: `tiles/*`. Look: `--view souk`: the printed difference must
be near 0 (no visible change).

**Done when.** The heaviest tile is under 3.5 MB (report sizes before and after per tile),
nothing visible changed, Blender import works. Tick Q5.

## 40. C2a - Level-of-detail tiles

Model: Sonnet | Effort: high | Size: M | Needs: 39 | Look: no

**Do.** For every tile also write `tile_<i>_<j>_lod1.glb`: buildings merged per block into
simple extruded shapes with the roof color (union of footprints, simplified, at the block's mean
height; a block belongs to the tile of its centroid), terrain at a 32 m step with skirts (a
vertical strip 3-5 m down along each tile edge, so no crack shows where a full tile meets a
lod1 tile), streets as simple flat ribbons, water surfaces kept, no trees and no dressing. List
it in `index.json` (file, bytes, triangles); a tile counts as finished for resume only when its
lod1 file exists too.

**Check.** Fingerprint may change: `tiles/*` (new lod files), `tiles/index`. Tests: lod files
are valid and under 15% of their full tile's bytes.

**Done when.** Every tile has a valid lod1 file under 15% of its size.

## 41. C2b - The viewer uses level of detail

Model: Sonnet | Effort: high | Size: M | Needs: 40, 4 | Look: aerial

**Do.**
1. The viewer loads lod1 for tiles beyond 1.5 km from the camera and full tiles when close
   (distance from the index or a viewer setting), with hysteresis and load-then-swap so nothing
   pops in storms; geometry of replaced tiles is disposed. The tile radius (`RADIUS`, 2500 m)
   applies to full tiles only: lod1 covers every tile of the build.
2. `tools/make_artifact.py` patches the viewer by exact strings (`addTile(await
   loader.loadAsync(...))`, `async function loadTiles(`): update its patterns for your rewrite,
   make it convert the lod1 files too, and run it once into a temp folder to prove it still works.

**Check.** Fingerprint: no change. Look: `--view aerial --build-args "--area capital --workers 8
--out output/full" --timeout 600`.

**Done when.** The whole capital shows quickly from the air and refines as you fly in; the phone
page builder works. Tick C2.

## 42. R1 - Refresh the phone 3D page

Model: Sonnet | Effort: medium | Size: S | Needs: 41 | Look: phone

**Do.**
1. Quick build, then `.venv/bin/python tools/make_artifact.py output/bodjantouna-42
   output/artifact --title "Goumosbane in 3D"`. The page's camera spots (`SPOTS` in
   `make_artifact.py`) predate the ground grading and the kasbah: derive them from the index
   views, with heights from `Ground.surface` + 1.7 m.
2. With the Artifact tool, first read https://claude.ai/artifact/HMtdFZUV9sGmyPn4q8mKsq, then
   publish `output/artifact/index.html` with every file under `output/artifact/data/` to that
   same URL (keep its icon; mind the size limits). Open it to check it loads. If this session
   has no Artifact tool, stop and tell Ali.

**Done when.** The page shows today's city (golden hour, textures, street life, people) and
Ali can open it on his phone.

## 43. CP4 - Checkpoint: people, landmarks, port, performance

Model: Opus | Effort: medium | Size: review | Needs: 28-42 | Look: souk + aerial (current state)

Follow the checkpoint routine of prompt 6 (`## 6.` in docs/prompts/01-foundations.md) for
prompts 28 to 42, comparing with `cp3` (pass `output/bodjantouna-42`). Extra checks:
- People: respectful, readable, no clipping; density and drawn triangles within budget.
- Landmarks and port: plausible placement on several seeds (quick builds with
  `--seed 7 --out output/seeds` and `--seed 1234 --out output/seeds`, and their city maps),
  names in the gazetteer.
- Tile sizes after Q5, LOD switching in the viewer, the phone page.
Save `fingerprint save cp4 output/bodjantouna-42` (after rebuilding the seed 42 quick build) and
`output/checks/cp4-*.png`. Fix prompts go in `## 43.1. ...`.
