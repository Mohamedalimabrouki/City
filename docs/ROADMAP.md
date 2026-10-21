# Roadmap

Each task is sized for **one cheap session** (Sonnet, medium effort, unless noted).
How to run one: open Claude Code in this folder and say
`Do task A1 from docs/ROADMAP.md.` (see docs/WORKFLOW.md).

Every task also requires: `python -m pytest -q` passes, `python -m citygen build --quick`
finishes, tunable numbers go in the style pack, and the task is ticked here when done.

Suggested order: C1, H1, H2, H3, H4, A4, A3, A1, A9, B1, B2, C3, D1, D5, then anything you like.

## Done (v0.1)

- [x] Country: terrain, coast, mountains, climate, settlements, road network, names, lore
- [x] City planner: old town (walls, gates, souks, alleys, great mosque), colonial quarter with
      boulevard, port, modern estates, dense housing, villas, industry, parks, cemetery
- [x] Exports: PNG maps, world.json, plan.json, gazetteer.md, 3D tiles (.glb) with index
- [x] Tools: browser viewer, snapshot to PNG, Blender import script, tests

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
- [ ] **A2 Facade textures** (M, Sonnet high) - Add optional base-color textures to the glb
  writer (embedded PNG, `KHR_texture_transform` not needed since UVs are meters). Generate small
  tileable facade images per wall material (windows per floor, a door band on the ground floor,
  blue doors and shutters for `lime_white`). Files: `mesh/gltf.py`, new `mesh/textures.py`,
  palette entries get `texture = "facade_..."`. Done when: Blender and the viewer show windows,
  and a test checks the glb image is valid. Reference: the facade shaders in
  `tools/blender_beauty.py` (`old_openings`, `colonial_openings`, `modern_openings`) show the
  target look and the window and door rules.
- [ ] **A3 Sidewalks and curbs** (M) - Raised sidewalks (0.15 m, `paving`) along the edges of
  every block outside the old town, so streets have crisp edges. Build them from block rings in
  `mesh/tile.py` (each block belongs to the tile holding its center). Done when: snapshot shows
  curbs, no z-fighting with road ribbons.
- [ ] **A4 Terrain grading** (M) - Inside city limits, smooth the ground so streets and
  buildings sit flush: a city height function = terrain blurred over ~60 m and terraced per
  block. Use it for terrain, ribbons and buildings in tiles touching a city. Files:
  `mesh/tile.py` (height function per tile), maybe `terrain.py`. Done when: no road below the
  ground in the street snapshot, building bases within 0.5 m of the ground.
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
  (front -Y in Blender = glTF -Z, origin at the anchor) plus `manifest.json` (category and anchor
  from custom properties). Done when: a kit made in Blender shows in `python -m citygen kit-sheet`
  and a role in the style uses one of its pieces.
- [ ] **A9 Lit windows by household** (S) - At night only the generator's windows glow, all of
  them. Give windows a lit and a dark variant (a `glass_lit` material with a warm emissive) and
  let the household decide (bigger families and some trades stay up late); Tounes windows get a
  lit copy through `materials_map`. Done when: a night snapshot shows a believable mix.

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

- [ ] **C1 Fast, resumable builds** (M) - Build tiles in parallel (`--workers N`,
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
