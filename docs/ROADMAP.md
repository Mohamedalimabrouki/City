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
- [ ] 7 Q3 Bougainvillea that cascades
- [ ] 8 V1 Golden hour in the viewer
- [ ] 9 V2 Ambient occlusion
- [ ] 10 Q4 Blender 5 haze
- [ ] 11 A4a City ground
- [ ] 12 A4b Everything on the graded ground
- [ ] 13 A3 Sidewalks and curbs
- [ ] 14 S1 Street surfaces and markings
- [ ] 15 A1 Roof life
- [ ] 16 CP2 Checkpoint: light and ground
- [ ] 17 A2a Textures in the 3D files
- [ ] 18 A2b Generated textures
- [ ] 19 A2c Textured walls and roofs
- [ ] 20 A2d Ground textures
- [ ] 20.1 AD1 Every home gets a door and windows
- [ ] 20.2 AD2 Impasses to landlocked houses
- [ ] 21 A9 Lit windows by household
- [ ] 22 AR1 Arcades and iron balconies
- [ ] 23 AR2 Building massing
- [ ] 24 A7 More greenery
- [ ] 25 H3a Parked cars and taxis
- [ ] 26 H3b Benches, kiosks, fountains
- [ ] 27 CP3 Checkpoint: facades and street life
- [ ] 28 P1 People figures
- [ ] 29 P2 People in the streets
- [ ] 30 A5a The kasbah
- [ ] 31 A5b Covered souks
- [ ] 32 A5c Cathedral and theatre
- [ ] 33 A5d Station and clock tower
- [ ] 34 A6a Quays, breakwater, lighthouse
- [ ] 35 A6b Boats and cranes
- [ ] 36 A6c Corniche promenade and beach
- [ ] 37 H3c Seaside cafes
- [ ] 38 A8 Blender kit export
- [ ] 39 Q5 Lighter tiles
- [ ] 40 C2a Level-of-detail tiles
- [ ] 41 C2b Viewer level of detail
- [ ] 42 R1 Refresh the phone 3D page
- [ ] 43 CP4 Checkpoint: people, landmarks, port
- [ ] 44 H1 Interiors: the design
- [ ] 45 H1a Interior model and command
- [ ] 46 H1b Courtyard houses
- [ ] 47 H1c Apartments, villas, shops
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
- [ ] 99 G1 Gallery, guide and phone page
- [ ] 100 CP9 Final review

## Done (v0.1)

- [x] Country: terrain, coast, mountains, climate, settlements, road network, names, lore
- [x] City planner: old town (walls, gates, souks, alleys, great mosque), colonial quarter with
      boulevard, port, modern estates, dense housing, villas, industry, parks, cemetery
- [x] Exports: PNG maps, world.json, plan.json, gazetteer.md, 3D tiles (.glb) with index
- [x] Tools: browser viewer, snapshot to PNG, Blender import script, tests

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
- [ ] **Q3 Generated bougainvillea** (S) - The generator's own climber (`bougainvillea` in
  `mesh/props.py`) looks like a lollipop next to the kit's cascade. Rebuild it as a dense,
  flat mass of bracts against the wall with a twisting trunk, or remove it from `door_plants`.
  Done when: a close snapshot shows no lollipops.
- [ ] **Q4 Blender 5 haze and color grade** (S) - `tools/blender_beauty.py` skips its compositor
  on Blender 5 (the compositor became a node group: `scene.compositing_node_group`, a Group
  Output node instead of Composite). Port `setup_haze` and keep Blender 3.6 and 4.x working.
  Done when: a 5.2 souk render shows the warm grade like a 3.6 render.
- [ ] **Q5 Lighter old-town tiles** (M, can be done with C2) - A dressed old-town tile is about
  4.7 MB because each tile stores its own copy of every kit piece it uses. Options: leave tiny
  pieces out of far tiles, quantize positions and normals (`KHR_mesh_quantization`), or merge
  rarely used big pieces. Done when: under 3.5 MB with no visible loss up close.

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

- [ ] **A1 Roof life** (S) - Tanks, dishes, laundry racks and pots already come with the
  dressing (A0). Left: low parapet walls (0.6-1.0 m) on flat roofs and stair boxes (a small
  room with a door) on a share of roofs. Files: `mesh/tile.py` (`building_mesh`),
  `styles/maghreb.toml`. Done when: the street snapshot shows parapets, tile triangles grow under
  25%. Reference: `tools/blender_beauty.py` (`add_parapet`) does parapets in Blender.
- [ ] **A2 Facade textures** (M, Sonnet high; prompts 17-20) - Base-color textures in the glb
  writer (shared or embedded images, `KHR_texture_transform` scale so UVs stay meters) and
  generated tileable textures (plaster, stone, render, concrete, roof tiles, paving, ground) as
  neutral detail tinted by the palette colors. Windows and doors stay 3D pieces of the dressing,
  never painted. Done when: walls, roofs and ground read as materials in the viewer and Blender,
  and tests check the glb images are valid.
- [ ] **A3 Sidewalks and curbs** (M; prompt 13) - Raised sidewalks (0.15 m) inside the street
  surface along the blocks outside the old town, and a raised central promenade on boulevards,
  so streets have crisp edges. Done when: snapshot shows curbs, no z-fighting with road ribbons.
- [ ] **A4 Terrain grading** (M; prompts 11-12) - Inside city limits, smooth the ground so
  streets and buildings sit flush: terrain blurred over about 60 m, gently flattened under blocks
  (full terraces would make cliffs on these slopes). Used for terrain, ribbons, buildings and
  dressing. Done when: no road below the drawn ground, no floating wall foot, door or prop.
- [ ] **A5 Landmarks pack** (M) - Kasbah (walled citadel with towers) on the old town's highest
  edge; a colonial cathedral and a theatre on the boulevard; covered souk roofs (vaults) over
  the main souks; a train station; a lighthouse at the port. Each is a function returning
  `Building`s plus a `Landmark` with a generated name. Done when: all appear in the capital map,
  gazetteer and snapshot.
- [ ] **A6 Port and seafront** (M) - Concrete quays along port districts, a breakwater into the
  sea, simple cranes, fishing boats as props (new `CityPlan.props` list), a beach promenade on
  the corniche. Done when: visible in the aerial snapshot of a coastal capital.
- [ ] **A7 More greenery** (S) - Trees along arterials in colonial and modern districts, green
  garden ground in villa lots, olive or citrus trees in some courtyards. Done when: map and
  snapshot show it, tree count rises without slowing the build by more than 15%.
- [ ] **A8 Blender kit export** (S) - Kits and instancing exist (A0). Add
  `tools/blender_kit_export.py`: every object of a Blender collection becomes `kits/<name>/<object>.glb`
  (front +Y in Blender = glTF -Z, origin at the anchor; prompt 38) plus `manifest.json` (category and anchor
  from custom properties). Done when: a kit made in Blender shows in `python -m citygen kit-sheet`
  and a role in the style uses one of its pieces.
- [ ] **A9 Lit windows by household** (S) - At night only the generator's windows glow, all of
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
- [ ] **C2 Level of detail** (M) - A light version of every tile (buildings merged into block
  shapes, no trees, terrain step 32 m) written as `tile_<i>_<j>_lod1.glb` and listed in the
  index; the viewer uses it beyond 1.5 km.
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
- [ ] **H3 Street life, part 2** (S) - Most street life came with A0 (stalls, goods, awnings,
  carts, plants, lamps, cables, laundry, cats, mopeds). Left: parked cars along colonial and
  modern streets, benches and kiosks on squares and the corniche, cafe terraces by the sea.
  Tile-local and deterministic, through `[dressing.roles]`.
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
