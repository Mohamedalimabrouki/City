# Roadmap

The work runs through the playbook in `docs/PROMPTS.md`: 100 numbered prompts, one session
each, in order (`Do prompt N.`). Each prompt ticks its line in the checklist below; the prompt
that finishes a task also ticks the task in its section further down. Tasks without a section
(T, V, S, AR, P, R, G and the checkpoints CP) are described only in their prompt.

Every task also requires: `python -m pytest -q` passes, `python -m citygen build --quick`
finishes, tunable numbers go in the style pack, and the task is ticked here when done.

## Playbook checklist

- [x] 1 T1 Regression fingerprint tool
- [x] 2 T2 Before/after pictures
- [x] 3 T3 Housekeeping
- [x] 4 C1a Build tiles in parallel (2.8x on the capital, accepted by Ali)
- [x] 5 C1b Resumable builds
- [x] 6 CP1 Checkpoint: foundations
- [x] 7 Q3 Bougainvillea that cascades
- [x] 8 V1 Golden hour in the viewer
- [x] 9 V2 Ambient occlusion
- [x] 10 Q4 Blender 5 haze
- [x] 11 A4a City ground
- [x] 12 A4b Everything on the graded ground
- [x] 13 A3 Sidewalks and curbs
- [x] 14 S1 Street surfaces and markings
- [x] 15 A1 Roof life
- [x] 16 CP2 Checkpoint: light and ground
- [x] 17 A2a Textures in the 3D files
- [x] 18 A2b Generated textures
- [x] 19 A2c Textured walls and roofs
- [x] 20 A2d Ground textures
- [x] 20.1 AD1 Every home gets a door and windows
- [x] 20.2 AD2 Impasses to landlocked houses
- [x] 21 A9 Lit windows by household
- [x] 22 AR1 Arcades and iron balconies
- [x] 23 AR2 Building massing
- [x] 24 A7 More greenery
- [x] 25 H3a Parked cars and taxis
- [x] 26 H3b Benches, kiosks, fountains
- [x] 27 CP3 Checkpoint: facades and street life
- [x] 28 P1 People figures
- [x] 29 P2 People in the streets
- [x] 30 A5a The kasbah
- [x] 31 A5b Covered souks
- [x] 32 A5c Cathedral and theatre
- [x] 33 A5d Station and clock tower
- [x] 34 A6a Quays, breakwater, lighthouse
- [x] 35 A6b Boats and cranes
- [x] 36 A6c Corniche promenade and beach
- [x] 37 H3c Seaside cafes
- [x] 38 A8 Blender kit export
- [x] 39 Q5 Lighter tiles (-45% bytes, densest 8.67 -> 4.67 MB; 3.5 MB target relaxed by the lead, see WORKLOG)
- [x] 40 C2a Level-of-detail tiles (lod1 next to every tile: 3.6% of a city tile, 12.9% at worst)
- [x] 41 C2b Viewer level of detail (whole capital as lod1, full near the camera; aerial frame about 155 -> 90 ms, settled 5-7 -> 3 s)
- [x] 42 R1 Refresh the phone 3D page (city of 25 October; textures as images, 3 spots of its own)
- [x] 43 CP4 Checkpoint: people, landmarks, port (6 fixes, speed round byte-identical, cathedral fallback for shallow boulevard blocks)
- [x] 44 H1 Interiors: the design (SPEC 6c; prompts 45-50 rewritten)
- [x] 45 H1a Interior model and command (`python -m citygen interior`, facade bridge, placeholder rooms)
- [x] 46 H1b Courtyard houses
- [x] 47 H1c Apartments, villas, shops
- [ ] 47.1 H1c fix: colonial flats to the bar (39% pass), the slowest colonial block (14 s)
- [ ] 48 H1d Interior walls and openings
- [ ] 49 H1e Floors, stairs, roof terrace
- [ ] 50 H1f Interiors in the viewer
- [ ] 51 H2 Furnishing: the design
- [ ] 52 H2a Traditional furniture
- [ ] 53 H2b Modern furniture
- [ ] 54 H2c Furnishing rules
- [ ] 55 H2d Light, textiles, clutter
- [ ] 56 H4a Hero scenes
- [ ] 57 H4b Hero scenes in Blender
- [ ] 58 CP5 Checkpoint: interiors
- [ ] 59 B1a Rivers
- [ ] 60 B1b Valleys and lakes
- [ ] 61 B1c Rivers in towns
- [ ] 62 B1d Bridges
- [ ] 63 B2a Fields and cactus hedges
- [ ] 64 B2b Olive groves and orchards
- [ ] 65 B3 Salt lakes and dunes
- [ ] 66 B4 Oasis towns
- [ ] 67 B5 Hilltop ksar villages
- [ ] 68 B6 Regions and natural names
- [ ] 69 CP6 Checkpoint: countryside
- [ ] 70 C4a Street graph for games
- [ ] 71 C4b Building entrances
- [ ] 72 C3a Godot: stream the city
- [ ] 73 C3b Godot: walk the streets
- [ ] 74 C3c Godot: sky, night, guide
- [ ] 75 C5 Unreal 5 import
- [ ] 76 C6a Tounes Rush city runs
- [ ] 77 C6b Country map unlocks
- [ ] 78 CP7 Checkpoint: game-ready
- [ ] 79 D7 Street names and addresses
- [ ] 80 D6 Residents
- [ ] 81 D1a District histories
- [ ] 82 D1b Notable families and guilds
- [ ] 83 D1c Local legends
- [ ] 84 D3 Canon for everything
- [ ] 85 D4a Timeline
- [ ] 86 D4b Factions
- [ ] 87 D5a Arabic place names
- [ ] 88 D5b Arabic people and street names
- [ ] 89 D2a Country poster map
- [ ] 90 D2b City poster map
- [ ] 91 CP8 Checkpoint: stories
- [ ] 92 E2 Faster terrain
- [ ] 93 E1 Whole-country builds
- [ ] 94 F4 Styles per region
- [ ] 95 F2 Medieval fantasy town
- [ ] 96 F1a Steampunk style pack
- [ ] 97 F1b Steampunk machines
- [ ] 98 F3 Two-level city: the design
- [ ] 99 G1 Gallery, guide and phone page (a first city gallery exists: extend it)
- [ ] 100 CP9 Final review
- [ ] 101 K1 Asset review tool
- [ ] 102 L1 City life: the design
- [ ] 103 K2 Hero detail near the camera
- [ ] 104 K3 Hero people
- [ ] 105 L2 Daily schedules
- [ ] 106 L3 Routes on the street graph
- [ ] 107 L4 Animated walkers
- [ ] 108 L5 The living viewer
- [ ] 109 L6 City rhythms
- [ ] 110 CP10 Checkpoint: hero people and city life
- [ ] 111 K4 Hero trees and palms
- [ ] 112 K5 Hero vehicles
- [ ] 113 L7 Traffic
- [ ] 114 K6 Facade pieces
- [ ] 115 K7 Souk and café pieces
- [ ] 116 L8 Follow a life
- [ ] 117 K8 Street furniture and boats
- [ ] 118 K9 Landmark close-ups
- [ ] 119 L9 City life in Godot
- [ ] 120 CP11 Checkpoint: hero assets and city life

## Done (v0.1)

- [x] Country: terrain, coast, mountains, climate, settlements, road network, names, lore
- [x] City planner: old town (walls, gates, souks, alleys, great mosque), colonial quarter with
      boulevard, port, modern estates, dense housing, villas, industry, parks, cemetery
- [x] Exports: PNG maps, world.json, plan.json, gazetteer.md, 3D tiles (.glb) with index
- [x] Tools: browser viewer, snapshot to PNG, Blender import script, tests, city gallery
  (`citygen gallery` / `Open City Gallery.command`, 2026-10-24) and keyboard flying and walking

## Q. Polish (weak spots seen while doing A0)

- [x] **Q1 Natural leafy trees** (S) - Broadleaf and olive trees are three blocky octahedrons
  (`tree_mesh` in `mesh/props.py`). Give them low-poly but natural crowns (for example 6 to 9
  jittered clumps with a few shades of green). They are drawn as instances, so up to about 200
  triangles per tree is fine. Done when: the street snapshot looks clearly better and tiles grow
  under 5%. Done. `mesh/trees.py` builds 3 broadleaf and 3 olive variants (122 to 184 triangles):
  7 to 8 (olive 5 to 7) jittered icosahedron clumps in dark, mid and light shades (`leaf_dark`,
  `leaf_light`, `leaf_olive_dark`, `leaf_olive_light`), a tapered leaning trunk (olive: one or two
  stems) and 2 or 3 branches. All numbers are in `[dressing.trees.*]`; roles `tree_broadleaf` and
  `tree_olive` pick a variant. Each variant has its own stream, so other pieces are unchanged.
  Undressed tiles keep the light 3-clump tree. Tiles grew 0.9% (11.55 to 11.65 MB). The street
  snapshot shows rounded crowns, darker below and lighter on top, instead of pointed diamonds.
- [x] **Q2 Family names** - Done. `family_name` picks one of five patterns from `[life]`: a
  made-up nisba (three Arabic root sounds in a word pattern, Hamdi = 1a23i from H-M-D, with sound
  rules and a rude-word blocklist in `roots.*`), a real nisba, "Ben" plus a real given name, a
  real "Bou" name, or a trade name. Random syllables had sounded foreign. One draw from the
  households stream is kept, so doors and wealth are unchanged. Test over 300 names in
  `tests/test_citygen.py`.
- [x] **Q3 Generated bougainvillea** (S) - Done. `mesh/climbers.py` builds two variants from
  `[dressing.climber]`: 2 or 3 bent, tapered stems and a 38 to 40 clump curtain of flat 4-face
  bracts (250 triangles each) in three magenta shades plus green leaves, hanging from the wall
  top to a ragged hem; it has its own stream. `mesh/plants.py` now holds the clump and tube
  helpers shared with the trees. Tiles grew 0.2%.
- [x] **Q4 Blender 5 haze and color grade** (S) - Done. `setup_haze` branches on
  `bpy.app.version`: 3.6 and 4.x keep `scene.node_tree` and the Composite node unchanged; Blender 5
  builds a `CompositorNodeTree` with a Group Output, rebuilds the same Render Layers -> haze mix ->
  color balance chain with the unified `ShaderNodeMath` and `ShaderNodeMix` (RGBA) nodes, and
  assigns it to `scene.compositing_node_group`. The 5.x Color Balance method is a menu socket whose
  default is already Lift/Gamma/Gain, so the method is not hard-coded. A 5.2 souk render shows the
  warm grade and the aerial view shows the depth haze (the souk lane is only about 20 m deep); the
  HEAD script renders both without either.
- [x] **Q5 Lighter old-town tiles** (M, can be done with C2) - A dressed old-town tile is about
  4.7 MB because each tile stores its own copy of every kit piece it uses. Options: leave tiny
  pieces out of far tiles, quantize positions and normals (`KHR_mesh_quantization`), or merge
  rarely used big pieces. Done when: under 3.5 MB with no visible loss up close.
  Prompt 39 (partly): `KHR_mesh_quantization`, 8-bit normals, no NORMAL on flat faces (split vertices,
  readers recompute them), welded vertices, 16-bit indices and rotations, no SCALE for unit pieces,
  pooled bufferViews, `stats --tiles`. Densest quick tile 8.67 -> 4.67 MB, full capital 11.11 -> 5.81 MB
  (all 168 tiles 25-48% smaller, 310 -> 171 MB), no visible change. Still over 3.5 MB; 16-bit UVs were
  skipped (see HANDOFF) and meshopt is ruled out (Blender cannot import it). Lead decision: done;
  the target was set before prompts 20-38 made the old town 50% heavier, and the last 1.2 MB would
  cost reader compatibility (welding flat vertices breaks the ambient occlusion normal pass and
  Godot/Blender smoothing; 16-bit UVs need rewritten Blender mapping). Far tiles get lod1 (prompt 40).

## A. Street level (the capital looks real up close)

- [x] **A0 Reuse the Tounes Rush kit** - Done. 51 pieces from "Tounes Rush AAA V5.2" in
  `kits/tounes/` (manifest + one .glb each, vertex colors, made by running the game's own builders
  in a headless browser), mixed with the generator's own pieces (`mesh/props.py`: shops stocked by
  trade, awnings, goods, lamps, cats, tanks, trees) through `[dressing.roles]`. Tiles draw them as
  instances. Beyond the brief: a household (family, trade, wealth, door color) behind every house
  door and a trade for every souk (`city/life.py`, in plan.json and the gazetteer), rich and poor
  doors, birdcage bays and mashrabiya balconies, sabats and arches over alleys, souk gates, carts,
  laundry and lantern strings, street lamps, palms from the kit; the viewer got a night mode and
  "click a house: who lives there". `python -m citygen kit-sheet` shows every piece.

- [x] **A1 Roof life** (S; prompt 15) - Done. `city/roofs.py` decides each flat roof once on
  its own stream (`roof_stream`): a parapet band 0.2 m thick and 0.6-0.9 m high (per district
  kind in `[roofs]`), and a 2.5 x 2.5 x 2.4 m stair room on about 35% of houses and 60% of
  apartment blocks, set against the roof edge and off the domes, with a door on a side that
  opens on free roof. `mesh/tile.py` reuses the building wall as the outer parapet face and
  adds a sloped coping strip down to the inset deck, which keeps the dense old town at +20.6%
  triangles (budget 25%). Domed roofs and minaret tops keep their shape; the index carries
  `"parapets": true` and `tools/blender_beauty.py` skips its own parapets. `Dresser._roof`
  uses the same layout, so tanks, dishes, laundry and pots stay inside the parapet and off
  the stair room.
- [x] **A2 Facade textures** (M, Sonnet high; prompts 17-20) - done: 17 (writer), 18 (generated
  images), 19 (walls and roofs), 20 (terrain, streets, sidewalks and curbs textured; streets and
  sidewalks run u along the street; a soft `COLOR_0` tint on the terrain against repeats from the
  air; road paint stays flat). Base-color
  textures in the glb writer (shared or embedded images, `KHR_texture_transform` scale so UVs
  stay meters), generated tileable textures (plaster, stone, render, concrete, roof tiles,
  paving, ground) as neutral detail tinted by the palette colors, walls mapped to plaster/render/
  concrete/stone with meter UVs and a street-facing plinth, hip roofs with planar meter UVs.
  Windows and doors stay 3D pieces of the dressing, never painted. Done when: walls, roofs and
  ground read as materials in the viewer and Blender, and tests check the glb images are valid.
- [x] **A3 Sidewalks and curbs** (M; prompt 13) - Done. `city/walks.py` grows each block of a
  district other than medina, village, park and cemetery by the district's `sidewalk_width`,
  removes the block and clips the band to the streets' side strips. A strip keeps at least
  `[streets] min_carriageway` (5.5 m) of asphalt, so a 9 m street gets 1.75 m walks and wider
  streets keep up to 3.2 m. Each piece is stored in `CityPlan.walks` with its street, side and
  actual width. Tops sit `curb_height` (0.15 m) above the ribbon, with a vertical `curb` face;
  `Ground.surface` returns the raised top, so doors, trees and lamps stand on it (a 0.15 m
  plinth shows under doors because the building base is not raised). Boulevards get an 8 m
  central promenade in 64 m pieces under the middle tree row. Tiles grew 3.3% at most; the
  street picture shows crisp curbs and the promenade with its trees.
- [x] **A4 Terrain grading** (M; prompts 11-12) - done. `[ground]` grading in
  `citygen/city/ground.py` drives `TileContext.height`, so terrain, ribbons and building bases
  sit on the smoothed, terraced ground. `Ground.surface` adds the street-ribbon lift where a
  street is drawn, and every ground reader uses it: dressing, door thresholds, gates, street
  trees, cameras and the index focus. Inside city limits, smooth the ground so streets and
  buildings sit flush: terrain blurred over about 60 m, gently flattened under blocks (full
  terraces would make cliffs on these slopes). Done when: no road below the drawn ground, no
  floating wall foot, door or prop.
- [x] **A5 Landmarks pack** (M) - Kasbah (walled citadel with towers) on the old town's highest
  edge (prompt 30); a colonial cathedral and a theatre on the boulevard (32); covered souk roofs
  (vaults) over the main souks (31); a railway station with its clock tower, platforms and tracks
  out to the city limit (33). Each returns `Building`s plus a `Landmark` with a generated name,
  appended last. Done: all appear in the capital map, gazetteer and snapshot. The lighthouse
  moved to A6 (prompt 34).
- [x] **A6 Port and seafront** (M) - Concrete quays along port districts, a breakwater and its
  lighthouse (prompt 34); fishing boats, trawlers, cranes and cargo as `CityPlan.props` (35); a raised
  seafront promenade on the corniche's sea side along colonial, modern and residential stretches, with
  palms, lamps, benches facing the sea, a low sea wall with a white railing and steps down to the beach
  (`CityPlan.fronts`, 36). Done: the "port" and "corniche" views and the aerial snapshot show them.
- [x] **A7 More greenery** (S) - Trees along arterials in colonial and modern districts, green
  garden ground in villa lots, olive or citrus trees in some courtyards. Done when: map and
  snapshot show it, tree count rises without slowing the build by more than 15%.
- [x] **A8 Blender kit export** (S) - Kits and instancing exist (A0). Add
  `tools/blender_kit_export.py`: every object of a Blender collection becomes `kits/<name>/<object>.glb`
  (front +Y in Blender = glTF -Z, origin at the anchor; prompt 38) plus `manifest.json` (category and anchor
  from custom properties). Done when: a kit made in Blender shows in `python -m citygen kit-sheet`
  and a role in the style uses one of its pieces.
- [x] **A9 Lit windows by household** (S) - At night only the generator's windows glow, all of
  them. Give windows a lit and a dark variant (`glass_lit`, lit by the viewer at night only) and
  let the household decide (bigger families and some trades stay up late); Tounes windows get a
  lit glass pane piece (prompt 21). Done when: a night snapshot shows a believable mix.

## B. Countryside

- [ ] **B1 Rivers and lakes** (L, Sonnet high or Opus low) - Flow accumulation on a coarse
  height grid, rivers (oueds) as polylines with width by flow, carve the terrain, lakes in
  closed basins, bridges where roads cross, settlements prefer river sites. Files:
  new `citygen/hydro.py`, `world.py`, `mesh/tile.py`, `export/maps.py`.
- [ ] **B2 Farmland and olive groves** (M) - Field patterns around villages and along roads
  (strip and Voronoi fields), colored terrain patches, and rows of olive trees as props in
  tiles. Must stay tile-local and deterministic.
- [ ] **B3 Salt lakes and dunes** (M) - Chott salt flats (white, perfectly flat depressions) in
  the steppe, dune fields in the far desert (directional noise). Terrain and biome changes only.
- [ ] **B4 Oasis towns** (M) - Desert settlements get a palm grove (dense palms, small walled
  gardens), mud-brick colors and narrower alleys. A new district kind `oasis`.
- [ ] **B5 Hilltop villages** (M) - Villages on steep ground become a ksar: ochre stone houses
  terraced up the slope, a granary block with vaulted cells (ghorfas). Style-driven.
- [ ] **B6 Regions and natural names** (S) - Governorates (regions around each city), named
  mountain ranges, capes and bays; shown on the country map and in the gazetteer.

## C. Game-ready

- [x] **C1 Fast, resumable builds** (M) - Build tiles in parallel (`--workers N`,
  multiprocessing; each worker rebuilds the world from settings, which takes seconds), skip
  tiles that already exist unless `--force`, reuse saved city plans. Done when: the full
  capital (`--area capital`) builds at least 3x faster on 4 cores.
- [x] **C2 Level of detail** (M) - A light version of every tile (buildings merged into block
  shapes, no trees, terrain step 32 m) written as `tile_<i>_<j>_lod1.glb` and listed in the
  index (prompt 40); the viewer shows every tile of the build as lod1 and the tiles near the camera
  full, turning full under 1.4 km and lod1 over 1.7 km, load then swap (prompt 41).
- [ ] **C3 Godot 4 starter** (M, Sonnet high) - `engine/godot/`: a project that streams tiles
  around the player from `index.json`, a first-person walker with collision, sun and sky. Plus a
  short README in plain language.
- [ ] **C4 Navigation data** (M) - Export the street network as a graph (nodes, edges, widths,
  kinds) in `cities/<name>/streets.json`, plus one entrance point per building on its street
  side, for AI pathfinding, traffic and quests.
- [ ] **C5 Unreal import** (M) - Python editor script and guide to import tiles into an Unreal
  5 World Partition level.
- [ ] **C6 City runs for Tounes Rush** (M) - Export a run route from a generated city (a chain of
  souks and streets from `plan.json`, with the buildings along it) in a format Tounes Rush can
  load, so a run can go through a real, always different medina, and a country map can unlock
  towns. Agree the format with the Tounes Rush code first.

## D. Stories

- [ ] **D1 Richer gazetteer** (M) - Per city: district histories, notable families (generated
  surnames), trades and guilds, two or three local legends, built from templates in the style
  pack. Deterministic, editable through canon.
- [ ] **D2 Poster maps** (M) - SVG versions of the country and city maps with clean labels,
  legend, compass rose and scale, ready for print or a book.
- [ ] **D3 Canon for everything** (S) - Extend `[canon]` in world files to pin district names,
  populations and landmark names; the gazetteer marks pinned facts.
- [ ] **D5 Names in Arabic and Latin** (M) - Build every name from syllables that have both an
  Arabic spelling and a French/English transliteration, and store both, so maps, games and books
  work in Arabic, French and English (as Tounes Rush does).
- [ ] **D4 Timeline and factions** (M) - A generated history: events per era tied to real
  places in the world (founding, sieges, trade booms), and factions with seats in cities.

## E. Scale

- [ ] **E1 Whole-country builds** (M) - `--area all` with C1: plan every settlement in
  parallel, report disk size and time, document results for 64 and 128 km.
- [ ] **E2 Faster noise** (M) - Cache terrain heights per tile and vectorize hot paths so a
  256 km country stays practical.

## H. Inside the houses, and rich streets

This scales because nothing is stored: an interior, or the clutter of a street, is generated only
when a scene, a game or a picture needs it, and it is always the same for the same seed. A
studio fills a few rooms by hand; rules fill every one of the 40,000 houses on demand.

- [ ] **H1 Interiors on demand** (L, Opus medium for the design, then Sonnet) -
  `python -m citygen interior BUILDING` builds the inside of any building. Courtyard houses get a
  bent entrance (skifa), the courtyard (wast ed dar), rooms around it, a kitchen and stairs to the
  roof terrace; apartment blocks get flats on every floor. Doors and windows match the facade.
  Output: one .glb plus a JSON list of rooms.
- [ ] **H2 Furnishing** (L) - Furniture and objects per room type from the kit (A0): banquettes,
  carpets (klim, mergoum), chests, low tables, lanterns, pottery, beds; fridge and TV in modern
  flats. A `density` setting: sparse, lived-in, extremely full.
- [x] **H3 Street life, part 2** (S) - Most street life came with A0 (stalls, goods, awnings,
  carts, plants, lamps, cables, laundry, cats, mopeds). Done: parked cars and taxis along colonial and
  modern streets (prompt 25), benches, kiosks, fountains and sabils (26), seaside cafe terraces under
  parasols on the corniche, with drinks kiosks by the railing (37). Tile-local and deterministic, through
  `[dressing.roles]`.
- [ ] **H4 Hero scenes** (M) - `python -m citygen scene` exports one house or one street block at
  maximum detail (H1 + H2 + H3 + A0) as a single .glb or .blend for a story scene, a trailer or a
  game level, while the rest of the world stays light.

## F. More styles (ideas from brainstorming, after A and B)

The plan layer (country, roads, districts, names) stays the same; a style is a new style pack
plus a kit of 3D pieces. Do F4 first so styles can be mixed inside one country.

- [ ] **F4 Styles per region** (M, Opus low for the design) - Let a world file give a style pack
  per region or per settlement (for example a steampunk inventors' city in the mountains),
  instead of one style for the whole country.
- [ ] **F1 Steampunk Maghreb** (L) - Brass and copper domes, copper screens on windows, clock
  towers, chimneys with smoke, steam trams on the boulevards, airships moored to minarets.
  Needs: a clock-tower landmark, chimney props, canals and bridges (after B1), an asset kit.
- [ ] **F2 Medieval fantasy town** (M) - Castle on the highest hill instead of the great mosque,
  steep tiled roofs, timber-framed walls (texture), round towers with cone roofs, forests.
  Reuses walls, gates and old-town streets as they are.
- [ ] **F3 Two-level city** (L, Opus medium for the design) - An upper city on platforms and
  bridges between towers above a dark undercity of pipes and lanes (Arcane-like). Needs a new
  vertical planning module and stacked tiles.

## K. Kit polish: hero-quality assets (after prompt 100)

Ali, 25 October 2026: every asset polished one by one, "at least like Léo" (his Blender character).
The method (reference board, the right tool, fixed cameras, two review rounds with Ali, budgets) and
the prompts are in `docs/prompts/10-life-and-polish.md`. These are the first city assets to use the
Blender route of prompt 38.

- [ ] **K1 Asset review tool** (M) - fair before/after sheets of one piece from fixed cameras (prompt 101).
- [ ] **K2 Hero detail near the camera** (M) - a rich `hero` level drawn within about 40 m (prompt 103).
- [ ] **K3 Hero people** (L) - the seven figures remade in Blender, with a rig (prompt 104).
- [ ] **K4 Hero trees and palms** (M) - prompt 111.
- [ ] **K5 Hero vehicles** (M) - prompt 112.
- [ ] **K6 Facade pieces** (M) - doors, shutters, grilles, balconies (prompt 114).
- [ ] **K7 Souk and café pieces** (M) - prompt 115.
- [ ] **K8 Street furniture and boats** (M) - prompt 117.
- [ ] **K9 Landmark close-ups** (M) - prompt 118.

## L. City life (after prompt 100)

Ali, 25 October 2026: people who move in long loops, as if they had lives. One design
(`docs/LIFE.md`, prompt 102) decides formats, budgets and the animation technique.

- [ ] **L1 City life: the design** (design) - prompt 102.
- [ ] **L2 Daily schedules** (M) - a week of plans for every resident (prompt 105).
- [ ] **L3 Routes on the street graph** (M) - prompt 106.
- [ ] **L4 Animated walkers** (L) - 2,000 instanced walkers at 60 fps (prompt 107).
- [ ] **L5 The living viewer** (L) - a clock, moving people, light that follows the time (prompt 108).
- [ ] **L6 City rhythms** (M) - prompt 109.
- [ ] **L7 Traffic** (L) - prompt 113.
- [ ] **L8 Follow a life** (M) - prompt 116.
- [ ] **L9 City life in Godot** (M) - prompt 119.
