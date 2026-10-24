# citygen - technical spec

This is the contract every change must respect. Read the sections your task touches.

## 1. Principles

1. **The code builds the world.** No hand-made map data. A world is fully defined by
   `seed + settings + style pack`; the same inputs always give byte-identical outputs.
2. **Coarse to fine.** The country (terrain, settlements, roads) is cheap and computed whole.
   Cities are planned only when needed. 3D tiles are built only for the requested area.
3. **Local output.** A tile can be built without the rest of the country's tiles, so huge
   worlds stream in a game engine and build in parallel.
4. **Content is data.** Names, colors, district rules and building rules live in
   `styles/*.toml`; world settings live in `citygen/defaults.toml` and `worlds/*.toml`.
5. **Fast feedback.** `pytest` about 20 s, `build --quick` about 1 min. Keep it that way. (Today on Ali's Mac: tests about 13 s, quick build about 8 s.)

## 2. Coordinates and units

- Meters. Generator axes: **x = east, y = north, z = up**. The country spans `0..size` on x and y.
- Angles in code: radians, counter-clockwise from east. Angles in settings: compass bearings in
  degrees (0 = north, 90 = east), converted with `radians(90 - bearing)`.
- glTF export (only there): `(x, y, z) -> (x, z, -y)`, so +Y is up and north is -Z.
- UVs are in meters (1 UV unit = 1 m) for walls, roofs, terrain and roads.

## 3. Determinism

- All randomness: `citygen.rng.stream(seed, *path)` returns a numpy Generator keyed by a
  purpose path, e.g. `stream(seed, "city", city_id, "parcels", block_index)`.
- Each feature gets its own path, so adding a feature never reshuffles existing ones.
  Inside a city, use `ctx.rng(*path)` (already prefixed with the city).
- Never use the `random` module, unseeded numpy, wall-clock time, or set/dict order that
  depends on hashing of unsorted keys.
- Noise (`citygen.noise.Perlin`, `Fractal`) is a pure function of position.
- The graded city ground (`citygen/city/ground.py`) is a pure function of position too: its blur
  is sampled on a world-aligned `[ground] lattice` (8 m) and interpolated bilinearly, so two
  tiles that share an edge compute exactly the same height there. The lattice cells are filled
  lazily and cached per process, never stored. `Ground.surface` is pure as well: it adds the
  street-ribbon lift (`STREET_LIFT`, highest where streets overlap) and the curb height of a
  raised sidewalk or promenade to that height. On a walk, the lift of any street within
  `[streets] walk_reach` counts (`Ground.walk_top`), because a sidewalk's block-side edge lies on
  the street outline, where rounding can miss the street. The corniche's seafront promenade (prompt 36) is
  level across: a point on it takes the walk top of the nearest point of its stretch's curb line
  (`Walk.edge`, shared by the stretch's pieces, so they meet at one height). Inside a city the natural terrain is
  sampled only in the edge band, where it has weight; deeper in, the height is the graded one.

## 4. Pipeline and modules

```
config.load_config()          defaults.toml + worlds/*.toml + CLI overrides
  world.generate_world()      terrain.Terrain, settlements, roads (whole country, seconds)
    city.plan_city()          one settlement -> CityPlan (seconds to a minute)
      layout                  land polygon, city limit, old town outline, neighborhoods, kinds
      medina                  great mosque, gates, souks, alleys (spanning tree), ramparts
      kasbah                  the citadel on the old town's high edge (capital and cities);
                              placed before the alleys, its buildings appended last
      streets                 arterials (neighborhood borders), ring road, boulevard,
                              corniche, links to country roads, local grids, street trees
      station                 the railway station across an avenue from the colonial quarter and
                              its tracks out past the city limit; precinct and corridor cut with
                              the old town's cut, local streets cut back; its buildings come last
      parcels                 blocks = district minus street surfaces; recursive lot split
      impasses                dead-end lanes along lot lines to lots without a street door
                              (old town, village, residential, suburb); appended to the streets
      landmarks               cathedral and theatre: 3-6 colonial lots facing the boulevard merged
                              into one lot each; their buildings appended after the kasbah's
      walks                   raised sidewalks along blocks and the boulevard promenade
      buildings               per-district building rules, mosques, parks, cemetery
      life                    a household behind every house door, a trade for every souk
      massing                 rows, cut corners, domes, set-back top floors, stepped slabs, villa
                              L's, roof machinery and roof rooms (never adds or moves a building)
      greenery                street trees on arterials, courtyard trees, villa fruit trees
                              (last, after the road paint; only appends to `trees`)
      port                    quays along the port districts' coast, a breakwater and its lighthouse
                              (after everything: adds `port`, the aprons to `land`, the lighthouse landmark)
      moorings                boats, cranes and cargo of the harbor (only sets `props`)
      corniche                the seafront promenade (the very last step: sets `fronts`, appends seafront
                              walks, moves the beach-side palms onto them, each keeping its index)
  city.ground.Ground()        graded ground inside cities: smoothed, terraced under blocks, level under
                              the station (blending back over [station] level_band), level on the quays
                              and stepping down at their walls to a dredged basin,
                              blended into natural terrain at the city limit; `height` is the
                              ground, `surface` the top of the ground, street ribbon or walk
  mesh.tile.export_tile()     one 512 m square -> .glb (terrain, water, roads, city)
    city.covered              which souk stretches are roofed (one rule for mesher and dresser)
    mesh.vaults               the souk vaults, impost bands, arches and light openings
    city.dressing             doors, windows, shops, goods, lamps, plants, spans, sabats, trees,
                              placed from kit pieces (kit.Kit) and drawn as instances
  export.maps / export.lore   PNG maps, world.json, plan.json, gazetteer.md
build.build()                 orchestrates the above into output/<country>-<seed>/
```

| Module | Responsibility |
|---|---|
| `citygen/rng.py` | keyed random streams, weighted choice |
| `citygen/noise.py` | Perlin and fractal noise, smoothstep |
| `citygen/terrain.py` | height, moisture, slope, biome classes |
| `citygen/names.py` | invented names from the style's sounds |
| `citygen/world.py` | `World`, `Settlement`, `Road`; placement and road routing (Dijkstra on a cost grid) |
| `citygen/city/*.py` | the city planner (see pipeline) |
| `citygen/mesh/builder.py` | mesh primitives: extrude, walls, caps, domes, hip roofs, ribbons, trees |
| `citygen/mesh/gltf.py` | dependency-free .glb writer and reader |
| `citygen/mesh/tile.py` | what goes into one tile |
| `citygen/mesh/lod.py` | the tile's light twin for distant views (prompt 40): coarse terrain with skirts, ribbons, merged blocks, low-poly landmarks, vertex clustering |
| `citygen/mesh/vaults.py` | covered souks (prompt 31): barrel vaults, impost bands, transverse arches, light openings, lantern rods |
| `citygen/mesh/landmarks.py` | the cathedral and the theatre (prompt 32): portals, rose window, towers, gables, crossing dome, apse; rounded corners, parapet, pavilion, crown, canopy, stage tower |
| `citygen/mesh/port.py` | the harbor (prompt 34): quay paving and the terrain cells a wall crosses drawn in two parts, quay walls with the wet band and kerb, the rubble breakwater (loft, crest road, crown wall, round head), the lighthouse; kit pieces `bollard`, `fender`, `armour_rock_0..2` and their placements |
| `citygen/mesh/corniche.py` | the corniche's seafront (prompt 36): promenade paving on the walk's own outline points, curb, sea wall (whitewashed coping band over `quay_wall` stone reaching `foot` m under the ground), flights of steps to the beach |
| `citygen/mesh/boats.py` | boats (prompt 35): a lofted hull with painted bands; fishing boats `boat_lateen`, `boat_cabin`, `boat_rowing` sharing one hull, the `boat_trawler`; shared helpers `surface`, `prisms`, `flat`, `boxes`, `heap`, `light` |
| `citygen/mesh/cranes.py` | the commercial quay (prompt 35): lattice-boom portal cranes `crane_0`, `crane_1`, `crane_rails`, `cargo_crates`, `cargo_containers_0..1` |
| `citygen/mesh/station.py` | the railway station (prompt 33): head building with entrance pavilion and clock tower (dials and hands), platforms with canopies on posts, buffer stops; the tracks tile by tile (sleeper bed, rails, level crossings); `keep_off` |
| `citygen/mesh/plants.py` | shared plant shapes: clumps (icosahedron, octahedron, 4-face bract) and tapered tubes |
| `citygen/mesh/props.py` | the generator's own kit pieces (doors, shops by trade, awnings, goods, lamps, trees...) |
| `citygen/mesh/people.py` | people (prompt 28): low-poly figures, one piece per outfit, pose and color scheme from `[dressing.people]` |
| `citygen/city/crowd.py` | people in the streets (prompt 29): who walks, stands and sits where, per tile, from `[people]` |
| `citygen/mesh/vehicles.py` | parked cars (prompt 25): hatchback, sedan, van, louage, yellow taxi; one piece per body color, sharing their part arrays |
| `citygen/mesh/trees.py` | broadleaf, olive and citrus crowns (jittered clumps, 3 variants each; citrus with oranges) from `[dressing.trees]` |
| `citygen/mesh/climbers.py` | bougainvillea curtains (2 variants, 250 triangles each) from `[dressing.climber]` |
| `citygen/kit.py` | `Kit`: procedural pieces plus kits from `kits/<name>/` |
| `citygen/city/life.py` | households and souk trades (story data that also drives the dressing) |
| `citygen/city/covered.py` | covered souks (prompt 31): which stretches are roofed, springing, stations, nothing piercing a roof |
| `citygen/city/ground.py` | `Ground`: graded city ground (blurred, terraced, blended into the terrain), and `surface` for the top of ground, street ribbons and raised walks |
| `citygen/city/dressing.py` | `Dresser`: which piece goes where, tile by tile |
| `citygen/city/walks.py` | raised sidewalks along blocks, narrowed to keep a carriageway, and the boulevard promenade |
| `citygen/city/paint.py` | street surfaces per kind, painted edge and lane lines, zebra crossings |
| `citygen/city/parking.py` | which sides of a street park (`parked_sides`, shared by paint and dresser), sidewalk widths measured per side, `Parking`: parked cars and the taxi rank |
| `citygen/city/impasses.py` | impasses: lanes cut along lot lines to landlocked lots, one round per lane for every block at once |
| `citygen/city/roofs.py` | roof layout: parapet band and coping, stair room and its door, menzah, one random stream per building; `roof_layouts` for every roof of a massed building |
| `citygen/city/greenery.py` | more greenery (prompt 24): arterial tree pits, courtyard trees, villa fruit trees, appended after every older tree |
| `citygen/city/kasbah.py` | the kasbah (prompt 30): placement on the old town's high edge, walls, towers, gate tower, palace, mosque, parade ground |
| `citygen/city/landmarks.py` | the boulevard's cathedral and theatre (prompt 32): sites on merged colonial lots, the local frame and plan shapes shared with the mesh, names, their camera views |
| `citygen/city/port.py` | the harbor (prompt 34): quay lines from the port districts' coast, aprons and level cores, the breakwater, basin and lighthouse (name, color scheme), the ground zones (shore, raised side, walls, dredge), the "port" camera |
| `citygen/city/corniche.py` | the corniche's seafront (prompt 36): `plan_fronts` fills `CityPlan.fronts` and the seafront walks and moves the beach-side palms; `Seafront` (lamps, benches, railing; `Dresser.seafront()`); the "corniche" camera |
| `citygen/city/terraces.py` | seaside cafe terraces (prompt 37): `Terraces` (cafes facing the sea, rows across the road, kiosk cafes by the railing), made by `Seafront` |
| `citygen/city/moorings.py` | boats, cranes and cargo (prompt 35): `plan_props` fills `CityPlan.props`; `box` (a prop's plan envelope), `land_zone` (where props stand on land) |
| `citygen/city/station.py` | the railway station (prompt 33): site at the colonial edge, track layout and corridor, street and walk clipping, buildings and name, its camera view |
| `citygen/city/massing.py` | building massing (prompt 23): the planning step, `masses(b)` (the volumes drawn and dressed), `floors_at`/`wall_height` (floors and wall height at a point of the outer wall), `outline`, `inner_walls`, `terrace_walls` |
| `citygen/kitsheet.py` | `python -m citygen kit-sheet`: every piece in one viewable grid |
| `citygen/export/maps.py` | country and city PNG maps |
| `citygen/export/lore.py` | JSON data files and the gazetteer |
| `citygen/build.py` | area selection and the full build |
| `citygen/view.py`, `tools/` | browser viewer, snapshot, Blender import |

**Impasses** (prompt 20.2, `city/impasses.py`, `[impasse]`): after the lots and the neighborhood
mosques' lots, before the buildings. A lot is landlocked when its house (the lot inset 0.15 m)
would have no wall of `min_front` m with a street surface 1.6 m in front of its middle, exactly
where the dresser looks (a souk wall needs `souk_front` m: the shop takes its middle). Per block,
the lot outlines (snapped to 1 cm) form a graph; a lane may use a lot line that keeps half its
width plus 0.2 m from the block's edge, or one leaving a mouth (a block-edge node next to exactly
one street, `junction_clear` from any other) that enters the block at 30 degrees or more. A
Dijkstra from all mouths (cost `mouth_penalty` by street kind plus `new_mouth`) and all lanes
already cut (cost their length from the mouth) finds the cheapest lot side to run along, nearest
lots first; the lane follows the path and the whole side, so it starts a new impasse, branches off
one, or carries one on from its dead end, and grows into a tree. Past its mouth a lane may touch no
street and no other lane but its parent, and stays within `max_length`. Lots lose the lane's
surface (sharp corners outside bends, simplified 2 cm), lots under `min_lot` are dropped, and a
lot no lane reaches joins the neighbour with a door it shares most boundary with. All blocks run
together, one lane per block per round, so each step is one vectorized call (random choices per
block on `rng("impasse", block)`: lot line jitter, widths, covered share and length).

## 5. Data model (`citygen/city/model.py`, `citygen/world.py`)

- `Settlement(id, name, kind, x, y, population, radius, elevation, coastal, biome, known_for, founded)`;
  kinds: `capital`, `city`, `town`, `village`. Ids are stable for a given seed and settings.
- `Road(id, kind, width, coords, ends)`; kinds `national`, `regional`, `local`.
- `CityPlan`: `boundary`, `land` (with the quay aprons since prompt 34), `medina`, `districts`, `streets`, `blocks`, `parcels`,
  `buildings`, `trees`, `landmarks`, `walks`, `households`, `souks`, `paint`, `stats`, `station`
  (a `city.station.Station` or None: `facade`, `tracks`, `precinct`, `corridor`, `district`, `core`), `port`
  (a `city.port.Port` or None: `level`, `quays` [`Quay`: `district`, `line` (the quay edge, the sea on its
  right), `coast`, `apron`, `core`], `breakwaters` [`Breakwater`: `line`, `quay`, `basin`, `sea_side`, `light`
  (x, y, yaw, scheme)], and the ground zones `core`, `apron`, `shore`, `raised`, `walls`, `dredge`, `zone`),
  `props` (prompt 35: [`Prop(kind, x, y, yaw, scale, on)`]: a kit piece the planner places itself; `yaw` turns
  the piece's +x, a boat's bow, to (cos yaw, sin yaw); `on` is `sea` (floats, waterline at z = 0), `quay` (on
  the quay top) or `beach` (drawn up on the sand)), `fronts` (prompt 36: [`Front(street, side, district, edge,
  sea, span, stairs, beach)`]: a stretch of the corniche's seafront promenade; `edge` the curb line and `sea` the
  sea wall's top edge, point for point opposite, along the street's direction; `span` (start, end) meters along
  the street; `stairs` [(x, y, ux, uy)] flights to the beach at the sea edge, (ux, uy) out to sea; `beach` meters
  with at least `beach_min` m of sand beyond the wall).
- `Walk(kind, polygon, width, street, side, district, block, edge)`: a raised sidewalk (`sidewalk`),
  the boulevard's central promenade (`promenade`) or a piece of the corniche's seafront promenade
  (`seafront`, prompt 36, `edge` its stretch's curb line). `width` is the actual width after a tight
  street narrows it; `street` and `side` (`+1` left, `-1` right) let later street features find
  the carriageway edge.
- `Tree(x, y, kind, height)`: kinds `broadleaf`, `palm`, `cypress`, `olive`, `citrus` (prompt 24).
  The dresser picks each tree's kit variant and turn from `rng("tree", k)` by its index k, so new
  trees are only ever appended: `stats["greenery"]` counts the ones `city/greenery.py` added at the end.
  Greenery (prompt 24, `[greenery]`): arterial trees first, one row of tree pits per sidewalk of a
  colonial or modern block on an arterial, `pit` m behind the curb face, every `spacing` m along the
  street (one species per street on `rng("street-trees", "arterial", k)`), left out within
  `junction_clear` of any other street, `paint_clear` of road paint, `wall_clear` of a building,
  `lamp_clear` along the street of a same-side lamp (the stations of `Dresser._lamps`), inside an
  arcade band (`dressing.arcade_zones`, the bands the dresser moves trees out of, so it never moves
  these; walls probe for their street as `Dresser.walls` does, from the old corner for a cut corner's
  faces) or `door_clear` of a stair-door path (`dressing.stair_rows`, `door_path` and `carried` on both
  long sides of nearby slabs, the dresser's own functions, carried `[dressing.paths] cross` m over the sidewalk). Then a tree in some courtyards without one
  (`chance` by district, `rng("courtyard-trees", k)`, mostly citrus) at the courtyard's pole of
  inaccessibility, its height capped so its crown (`crown_radius` + largest `clump_radius`, times
  the height) clears the walls by `wall_clear`; then 0-2 fruit trees per villa garden
  (`rng("garden-trees", k)`, 12 draws per tree whatever the geometry) farther from the nearest
  street than the house by `behind` m (the gate path lies between), `edge_clear` from the lot edges
  and `tree_clear` from other trees. Rule: modern arterials get street trees; arcaded colonial ones do
  not (their arcades are the shade, as on real arcaded streets, and no tree pit fits beside the
  pillars: the trunk needs 2.97 m from the wall, the 3.2 m sidewalk ends at 3.2). Quick capital: 69
  arterial trees (all modern), 58 courtyard trees (45 citrus); full capital: 149 arterial, 273
  courtyard (213 citrus), 2,025 villa fruit trees (1,640 citrus).
- `Paint(polygon, street, kind)`: one painted marking (`line` or `crossing`, a zebra bar), a flat
  polygon over the carriageway of a street. `make_paint` builds edge and lane lines, dashes and zebra
  crossings once per plan; a tile only clips the polygons it touches. The carriageway is the street
  surface minus every sidewalk on it (whichever street a sidewalk is filed under) and the promenade;
  edge lines stand `paint_edge_inset` inside the widest sidewalk of each side, measured on that side
  (`parking.walk_widths`), and `[dressing.parking] row` inside it where that side has a parking row
  (prompt 25: cars never straddle the line; a side parks only along sidewalks of the parking
  `districts`, as the cars do); with one row the center line moves half a row toward the
  free side.
- `Household(building, family, trade, wealth 0..1, door, members)`: one per house, domed house,
  apartment block and villa. `Souk(street, name, trade, ground, wall, shop)`: one per souk street.
- `District.kind`: `medina`, `village`, `colonial`, `modern`, `residential`, `suburb`,
  `industrial`, `port`, `park`, `cemetery`.
- `Street.kind`: `boulevard`, `arterial`, `ring`, `corniche`, `connector`, `street`, `souk`, `alley`,
  `impasse`; `Street.surface` is the palette material of its ribbon from `[streets.surface]` (a
  village street is `earth`; an impasse takes `[impasse.<district kind>] surface`). Impasses come
  last in `CityPlan.streets`, so every other street keeps its index. An impasse's line runs from
  its first point, `mouth_overlap` m inside the street it opens on (or on the impasse it branches
  off), to its dead end; `Street.covered` is how many meters from its mouth a room covers it.
- `Parcel(polygon, district, frontage, block)`: `block` indexes `CityPlan.blocks`; `frontage` is
  also True for a lot an impasse reaches.
- `Building`: `footprint` (holes = courtyards), `kind`, `height` (above the highest ground
  point), `wall`/`roof` material names, `floors`, `roof_shape` (`flat`/`hip`), `domes`, `top`.
  Massing fields (prompt 23, `city/massing.py`, all empty by default): `setback` (the footprint of
  a top floor standing back from the street walls), `steps` ([(polygon, floors, roof_shape, roof)]:
  parts of the footprint with their own floor count, a stepped slab or a villa's hip part and flat
  wing), `machines` (roof machinery dicts: `lift` motor rooms, `tank` stands, with their position,
  size and roof height `z`), `menzah` (a roof room is wanted; `roof_layout` places it), `corners`
  ([(x, y, kind, reach)]: street corners cut, `chamfer` or `round`, at the old corner point; a cut's
  faces are the walls with both ends within `reach` of it), `apron` (the lot corner the cuts leave
  open, grown `apron_grow` m to the block edge, inside the block: paved like the sidewalk, as a pan
  coupe widens it), and `top` with `x`, `y`, `shape: "drum"`,
  `radius`, `height`, `rise` for a corner dome or turret. `height` and `floors` stay the tallest
  part's; `masses(b)` gives the volumes: one box; or the footprint up to `floors - 1` (its roof a
  terrace) and the set-back floor on it; or the steps side by side. The main mass (the top floor,
  the tallest step, else the box) carries the stair room, menzah, machinery and roof props.
  **Massing** (`apply_massing`, after households and souks, every choice on `ctx.rng("massing",
  feature, k)`, numbers in `[district.<kind>]`): colonial buildings of one block share a row height
  (the median of their floors) plus `row_step` (`corner_step` on a street corner, taller); street
  corners within `corner_angle` of square are cut with chance `corner_cut`: a pan coupe face of
  `chamfer` m or, `corner_round` of them when the walls are long enough, three faces of
  `round_segment` m turning 22.5 degrees each (one window and one arcade bay per face); `corner_dome`
  of the cut buildings of `dome_floors`+ floors get a `dome` or a taller `turret` on a drum right
  behind the cut; `setback_share` of the others with `setback_floors`+ floors set the top floor
  `setback_depth` m back from every street wall (party and back walls stay flush). Modern slabs of
  `step_min_length`+ m step (`step_share`): 2 or 3 parts cut between window columns, floors dropping
  by `step_drop` (descending or the middle part highest), each at least `step_min_part` m; slabs of
  `machine_floors`+ floors get a lift motor room over the middle of each roof part (`lift`) and
  `tank_stands` water tanks on stands. Two-storey suburb villas on a plain rectangle become an L
  (`l_share`): the hip-roofed part across one end (`l_main` of the length), a flat terrace wing one
  floor lower (`l_wing` of the depth, `terrace_roof`). Old-town courtyard houses get a menzah with
  chance `menzah`.
  Fortification fields (prompt 30, `city/kasbah.py`): `battlement` ({"chains", "breast", "merlon",
  "depth"}: a breastwork with merlons along each chain of the roof edge, the building's inside on the
  left; such a building gets no parapet from `roof_layout`) and `arches` ([(x, y, yaw, width, height,
  sill, frame, material)]: horseshoe-arched gates, doors and windows on a wall face, drawn by
  `building_mesh`; sill 0 stands on the ground at the spot, a window's sill counts from the highest
  ground).
- **Kasbah** (prompt 30, `[kasbah]`, settlements with `kasbah = true`: capital and cities, never towns
  or villages): after the great mosque and gates, before the alleys, the old town's outline is sampled
  every `step` m and scored by the mean terrain height of the stretch the kasbah would take; highest
  first, a rectangle of side clamp(`side`[0] x the old town's width, `side`[1], `side`[2]) along the
  wall and `depth` x side deep, cut by the outline (so its outer side IS the city wall line), must lean
  on the wall over 60% of its side and keep its `cut` (outline + `clearance`, plus the gate tower) at
  `mosque_clear` from the great mosque's site, `gate_clear` from every city gate and `souk_clear` from
  the straight line between each gate and the mosque. The alleys drop the crossings inside the cut (the
  rest of the old town keeps its own) and route around it; a souk runs from in front of its gate tower
  to the mosque; lots and impasses avoid the cut like the mosque site. The rampart leaves out the outer
  wall and the kasbah towers (`keep_out`), and its towers within `rampart_tower_clear` m. Buildings,
  appended after every other building (no household, so none moves) with the landmark after every other
  landmark: `kasbah_wall` pieces between the towers (`wall_thickness` 2.5 m, `wall_height` above the
  ramparts), square `kasbah_tower`s flush inside and standing out (at bends sharper than `corner_turn`
  and every `tower_gap` m), the `kasbah_gate` tower facing the old town with a horseshoe arch on both
  faces, all in `stone_kasbah` with a battlement; the `kasbah_palace` round a courtyard in a back
  corner (`palace`: more floors than any house, arched windows on the upper floors, its door toward the
  gate); a small mosque facing the qibla (`mosque_complex`: `mosque_hall`, `mosque_court`, `minaret`);
  and `kasbah_ground`, the parade ground and courtyards, paving draped on the terrain mesh (never
  extruded). `Landmark("kasbah")` stands at the gate's face (its sabil, `[dressing.squares] sabil`,
  stands beside the arch on the gate tower); its name comes from `[names.districts] kasbah` on
  `ctx.rng("kasbah", "name")`. Massing never touches it (no housing kind).
- **Boulevard landmarks** (prompt 32, `city/landmarks.py`, `mesh/landmarks.py`, `[landmarks]`, settlements
  with `boulevard_landmarks`: capital and cities, when the boulevard has room): after the impasses, before
  the ordinary buildings, each kind in turn (cathedral, then theatre) slides its footprint (front steps on
  the boulevard's edge, `inset` off it, the building behind) along every colonial lot with `min_front` m of
  boulevard frontage, `shift` m either way, at the largest of `scales` x `size` that fits somewhere; the
  lots of that block it touches must be 3-6 (`lots`) free lots whose union holds it (`slack`). The best site
  is seen from the street camera (`streets.view_spot`, shared with `build.camera_views`: 50-300 m ahead within
  `view`[2] degrees), then on a block of its own, then the biggest. `merge` removes its lots from the parcel
  list and appends the merged lot at the end (nothing ordinary is built there: every later colonial lot
  re-rolls its draws); the buildings (kind `cathedral` / `theatre`, `facade` {x, y, yaw, width, depth, steps,
  cap}) and `Landmark`s (at the footprint's centroid; names from `[names.districts]` on
  `ctx.rng("landmarks", kind, "name")`, a saint from `saints`) come after the kasbah's. Boulevard trees within `tree_clear` m in front of the steps are left
  out. No household lives there, the massing and the dresser leave them alone (not housing, not `DRESSED`),
  no car parks in front of the steps (`Parking._landmark_steps`). `building_mesh` hands them to
  `mesh/landmarks.py`: cathedral (neo-Romanesque with a Byzantine dome): two square towers with belfries,
  octagonal lanterns and domes or pyramids, a gabled nave with clerestory, lean-to aisles with buttresses,
  three recessed round-arched portals with tympana, a rose window of three rings and twelve spokes, a
  crossing dome on a windowed drum, a semicircular apse; theatre (Art Nouveau): rounded street corners with
  cupolas, three rows of round-arched windows, cornice, a parapet with piers and urns, a central pavilion
  with a great window, a curved gable and a dome, a glass and iron canopy, a stage tower. The floor stands
  `base` m over the foot of the steps (higher where the ground behind is higher), walls reach 0.6 m under the
  lowest ground; each under 6,000 triangles (quick capital 2,995 and 3,081, full capital 3,095 and 3,285;
  faces share their corner vertices to save bytes). The index gets a
  "cathedral" and a "theatre" camera view (`landmark_views`: from the boulevard, near `distance` m, the whole
  facade within `spread` degrees).
- **Railway station** (prompt 33, `city/station.py`, `mesh/station.py`, `[station]`, settlements with
  `station = true`: capital and cities): a terminus like the colonial stations of Tunis, Sousse or Sfax. After
  the local streets, before the blocks, `place` tries a site every `step` m along each arterial on a colonial
  district's border: the station stands across the avenue (outside the colonial district, never on
  `no_station_on` districts), its frame (the landmarks' `Frame`: s along the avenue's edge, d away from it) at
  the avenue's far edge. Plan in d: the paved forecourt (`forecourt` m), the head building (`hall` depth),
  the platforms (`platform_length`), the throat (`throat`), then the line. Across (s): side platforms at both
  ends and an island between each pair of tracks (`layout`; 2-4 `tracks` on `rng("station")`), tracks
  `spacing` apart on the line, `edge` m from a platform's edge. A site fails when its precinct leaves the city
  (5 m in), touches the old town's cut or ring road (5 m), a main street (0.5 m in), or when the ground falls
  more than `max_drop` m under it; its line runs straight on from the throat to the first exit through the
  city limit plus `beyond` m, must stay on land and cross main streets at `cross_angle` degrees or more,
  never the boulevard or the ring road. Cheapest wins: corridor km, main streets crossed, (1 - cos) of the
  angle off the nearest target (where a country road enters the city, weighted national 1.0, regional 1.3,
  the port districts 1.15), meters of fall, a little jitter. The precinct (forecourt, head building,
  platforms) and the corridor (each track buffered by `spacing / 2 + margin`: the tracks plus 4 m) join the
  old town's cut before `make_blocks`, so no block, lot or building lies on them; `clip_streets` cuts local
  streets back from the precinct (1 m) and from the corridor where they run along the tracks (under
  `cross_angle`) or end on them, steeper ones keep a level crossing (pieces under 20 m go); `clip_walks`
  cuts sidewalks out of both; street and greenery trees there are left out (`clear`). Buildings, appended
  after the boulevard's: `station_forecourt` (paving draped on the terrain `forecourt_lift` m up, a curb
  skirt), `station` (the head building) and `station_platforms`, all with the same `facade` record (frame,
  layout, `level`, `tower_side`, the avenue's index), and `Landmark("station")` named from `[names.districts]
  station` on `rng("station", "name")`. Nobody lives there; nothing dresses them. The ground under the hull
  of the head building and the platforms (`core`) is graded level at `facade["level"]` (half way between the
  highest and lowest terrain there) and blends back over `level_band` m (smootherstep, convex hull so no
  kink); walks within that blend are drawn with `[station] walk_step` outline points (`Ground.walk_step`,
  used by the mesher, the crowd and the test). Mesh (`mesh/station.py`): the hall (`hall` wall height,
  tiled gable roof at `pitch`, cornice, plinth course, round-arched windows and doors, `window`/`doors`),
  the entrance pavilion (`pavilion`: taller, through the hall, a pediment each end, the great recessed arch
  `entrance` with a glazed fanlight and doors, a name panel, side windows, steps from the forecourt), the
  square clock tower at one end (`tower`, `tower_out`, `rng("station", "tower")`): string courses, narrow
  windows, four clocks (`clock`: white `dial_white` dial in a stone ring, twelve marks, hour and minute hands
  as bars, one time on `stream(seed, "station", "clock", x, y)`), a cornice and a tiled pyramid (`cap`) with
  a finial; platforms following the station's level (`platform`[2] over the rail top) with white edge lines,
  a concourse, ridged `canopy_iron` canopies (`canopy`) on posts with a ridge beam and an iron valance,
  buffer stops. Tracks (`rail_meshes`, each cut at tile edges, drawn even past the city limit): a `ballast`
  sleeper bed `spacing` wide, `bed_lift` over the terrain mesh (its texture shows four sleepers per 2.6 m),
  two `rail_steel` rails (`rail`, `gauge`); on a street the rails run at its surface plus `crossing_lift`
  (a level crossing). Points every meter are thinned to what the track's and the ground's bends (2 cm) and
  the street edges need. `keep_off` drops every placement whose kit box touches the precinct or the
  corridor (cars, people, lamps, trees). The map draws beds, rails and buildings; the gazetteer lists the
  station; plan.json has `rail` (tracks, corridor); the index gets a "station" camera on the avenue.
- **Harbor** (prompt 34, `city/port.py`, `mesh/port.py`, `[port]`, settlements with `port = true` on the coast:
  capital and cities; like La Goulette, Sousse, Sfax or Bizerte). Last in the planner, reading only districts and
  land, so no street, lot, building or tree moves. The coast of each port district (the corniche's center line,
  `land`'s edge) with `min_quay` m left after `end_inset` m off each end becomes a quay: the coast simplified by
  `straight` m, each segment pushed out to `reach` m past the farthest point of the coast it covers (every cove
  behind it filled), the segments joined at their crossings; it returns to the coast at right angles at both
  ends. The apron (old coast to quay edge: the corniche's sea half and the reclaimed land) joins `plan.land`.
  The longest `breakwaters` quays get a breakwater from the end farther from the city center: a cubic curve out
  along the quay's normal by `out` (share of the quay, clamped), turning to run back along it for `run` of its
  length (`bend` brings the head back toward the shore), stations every `step` m; past its root it keeps
  `shore + land_clear` m off the land (else the other end is tried). The basin lies between the quay, the
  breakwater and the mouth. The lighthouse stands on the head, its color scheme (`white` with a red cap,
  `red_top`, `bands`) on `rng("port", "lighthouse", n)`, its `Landmark("lighthouse")` (appended after every
  other landmark) named from `[names.districts] lighthouse` on `rng("port", "lighthouse", n, "name")`.
  Ground: the core (the apron plus `core_inland` m behind the old coast, the whole corniche) is exactly `level`
  m; on the land side (the core and `shore`, the land plus `shore` m) the ground blends back over `level_band` m
  (smootherstep from the core); the open sea keeps the natural seabed, dredged to `depth` m in the basin and
  `toe` m off every quay wall, fading over `dredge_band` m. The ground steps at the walls (where the raised side,
  the core plus the shore within the level band, meets the open sea): the quay walls along the core and a sea
  wall along the corniche's edge next to a quay's ends. `Ground.side_height(x, y, "raised" | "sea")` gives each
  side's ground there. Mesh: terrain cells with their center on an apron are `quay` paving; cells a wall crosses
  are drawn in two parts (`split_cells`), each on its own side's ground (only vertices on a wall use
  `side_height`), so the drawn terrain is `Ground.height` everywhere off the walls. Walls (`quay_wall` dressed
  stone above `wet` m, `quay_wet` below, down to `bury` m under the seabed; a `kerb` along the core) are cut by
  segment midpoint per tile. The breakwater: a loft of rough profiles (crest edge, `rows` jittered points, toe on
  the seabed, slopes `slope`:1, `rough` m jitter on `stream(seed, "port", city, n, "rubble")`), a `quay` crest
  road `crest` m high and wide, a `quay_wall` crown wall `parapet` on the sea side, a half-round head; two rows
  of armour stones (`[port.armour]`, kit pieces `armour_rock_0..2` on their own piece streams, placed on
  `stream(seed, "port", city, n, "armour")`); the lighthouse (`[port.lighthouse]`: stone drum, tapered
  `lighthouse_white` tower with `lighthouse_red` parts, `canopy_iron` gallery and railing, `lantern_glow`
  lantern that glows at night, cap and finial). Bollards every `bollard_step` m `bollard_inset` m behind the
  quay edge and fenders on the wall between them (none on the breakwater's root); `keep_zone` drops every other
  placement in the open sea or within 1 m of a quay wall. The map draws the aprons, quay edges, breakwater and
  lighthouse (its bounds take in the harbor); the gazetteer lists the harbor and the lighthouse; plan.json has
  `port`; `stats` has `quay_m` and `breakwater_m`; the index gets a "port" camera (`[port] camera`: up over the
  water off the harbor mouth, looking back across the basin). Quick capital: quays 523 + 841 m, a 732 m
  breakwater; full capital: quays 935 + 612 m, a 788 m breakwater; both "Phare de Sidi Sazma".
- **Boats, cranes and cargo** (prompt 35, `city/moorings.py`, `mesh/boats.py`, `mesh/cranes.py`, `[port.props]`):
  the very last planning step, on the port's own streams (`rng("port", "props", ...)`), so nothing else moves;
  it fills `CityPlan.props`. On the main quay (the one the breakwater shelters, else the longest) the
  `commercial` share by the harbor mouth is the commercial quay: rails (`crane_rails`, `size` lengths) with
  the sea-side rail `crane_inset` m behind the edge, 2-3 portal cranes of one model per harbor (`crane_0` or
  `crane_1`, `crane_space` m apart) on them, a yard of containers and crates in slots (`yard_step`, filled at
  `yard_fill`) from `yard_inset` m behind the edge, and a trawler or two alongside. The rest, and every other
  quay, is the fishing port: walking each straight stretch (`end_clear` m from ends and corners), groups of
  `row` fishing boats moored bow- or stern-to side by side (`side_gap`), or a trawler alongside (`trawler`
  odds), `group_gap` m apart, with stretches left `empty` (more on a quay no breakwater shelters,
  `open_quay`), and now and then fish crates on the quay behind a row (`fish_crates`). A few boats lie at
  anchor in the basin (`anchored`), `anchor_clear` m off the quays, `swing` m apart, all heading into one
  breeze. Near the port (`beach_reach` m from a quay's end, off the port's ground zone) fishing boats are
  drawn up on the natural beach, bow inland, stern where the sand stands `stern_sand` m high. A boat fits
  where its envelope (`[port.props] size` x its scale from `[port.props.scale]`) stays off the land, the raised
  quays, the shore and `breakwater_clear` m of the breakwater, `gap` m off the quay wall, over water at least
  its `draft` x scale plus `keel_clear` deep (the dredged depth in `port.dredge`, else the natural seabed);
  cranes and cargo stand inside the apron `street_clear` m off streets, walks and buildings and `tree_clear` m
  from trees; drawn-up boats keep `beach_clear`. The tile holding a prop's center draws it (`Dresser.props`):
  boats at z = 0 (the hull dips `draft` below), quay props at the quay level, a drawn-up boat with its keel
  `beach_sink` m into the drawn sand and tilted along its length to the ground under its ends; before that,
  `keep_off` drops every other piece whose kit box touches the props standing on land (`land_zone`). Quick
  capital: 98 fishing boats (7 drawn up on the beach) and 13 trawlers (4 boats at anchor), 3 cranes on 28 rail
  lengths, 30 crate stacks and 26 container stacks; full capital: 108 and 13 (4 at anchor, no beach near the
  port), 3 cranes, 31 rails, 41 crates, 24 containers.
- **Seafront promenade** (prompt 36, `city/corniche.py`, `mesh/corniche.py`, `[corniche]`): the very last
  planning step. The corniche is walked in `step` m stations; a station counts where the district on its land
  side is in `districts` (colonial, modern, residential: the harbor, industrial and cemetery stretches keep the
  plain corniche) and the sea side has room: from the curb, `curb` m inside the corniche's sea edge, to the water
  line (the natural ground `water` m above the sea; seaward of the corniche's center line lies the city limit, so
  the ground there is the natural terrain). The width is `width` while `beach_min` m of sand remain; as the water
  comes closer the wall moves out with it, reaching the water at `max_width` (`width_for`, continuous), averaged
  over five stations and never past the water; under `min_width` no promenade. A segment between two stations
  counts when no other street covers more than `cross_area` m2 of its band and it keeps `clear` m from the
  harbor's ground (`Port.zone`) and the drawn-up boats (`land_zone`). Runs of segments are the `Front`s, cut
  into `piece` m `Walk("seafront")`s; steps every `stair_every` m where `stair_sand` m of sand lie beyond the
  wall. The beach-side palm row of `street_trees` moves onto the promenade, `palm_inset` m from the curb at the
  same station (index, kind and height kept). `stats` gets `promenade_m` and `beach_m`. Drawn (the tile holding
  the walk's centroid): paving (`promenade`, 0.8 m slabs along the street), a curb face on the street side, the
  sea wall on the sea side and at open ends (`coping` m of `lime_white` over `quay_wall`, down to `foot` m under
  the ground), flights of steps (risers up to `stair[1]`, treads `stair[2]`). Dressed (`Dresser.seafront()`, once
  per city, a tile keeps what it holds): a `street_lamp` in the palm row in every `lamp_every`th gap between
  palms (`rng("seafront", "lamp", k, palm)`), a bench (role `seafront_bench`: the iron bench) by chance `bench`
  in each gap, `bench_back` m in from the sea edge and facing the sea (`rng("seafront", "bench", k, palm)`), and
  the `railing_sea` piece (white iron, 2 m, stretched between the sea edge's bends, broken at the steps); the
  corniche's own street lamps on the promenade are left out (`lamp_spot`). Strollers walk between the palms and
  the benches (`[people.seafront]`), sitters take the benches. The index gets a "corniche" camera (eye level on
  the promenade of the longest stretch near the center, looking 60 m along it). Quick capital: 752 m of
  promenade (272 m with a beach), 6 flights, 53 palms, 26 lamps, 40 benches; full capital: 4192 m (all with a
  beach), 58 flights, 295 palms, 146 lamps, 221 benches.
- **Seaside cafe terraces** (prompt 37, `city/terraces.py`, `[corniche.terrace]`, `Seafront.terraces`): a main wall
  on a seafront stretch, on the land side (`Dresser.seaside`: its middle `end` m inside the stretch) is a cafe when
  the colonial cafe chance makes it one, or by `cafe` on `rng("terrace", "cafe", k)`, drawn after the door's draws,
  whose pieces are then dropped, so the windows draw as before (`_front`; `_cafe(tables=False)` still makes the
  tables' draws). Its terrace (`rng("terrace", "front", k)`): `tables` `cafe_set`s on its sidewalk, chairs along the
  wall, `reach` m out, `pitch` m apart from the middle outward, inside the wall's ends, each under a parasol where the
  canopy fits (not under the awning, a crown or a lamp), else in the open; with chance `across`
  (`rng("terrace", "across", k)`) a row of `across_tables` under parasols on the palm line across the road, in the
  lamp-free palm gap nearest the cafe (within `across_reach` m), all within `row_reach` m of the curb. Kiosk cafes
  (decided before the benches; that gap gets no bench): in a palm gap of `kiosk_gap` m or more, clear of the steps,
  chance `kiosk` on `rng("terrace", "kiosk", k, palm)`, `kiosk_spacing` m apart, a `kiosk_drinks` (role
  `cafe_kiosk`; lit with chance `kiosk_lit`) backing onto the railing `kiosk_back` m from the sea edge and facing
  the promenade, `kiosk_tables` tables along the railing beside it under parasols, all within `sea_reach` m of the
  sea edge. Promenade groups only where the promenade is `min_width` m wide, so a walkway of 3 m and more stays
  free. One parasol color per group (role `parasol`); each table turns up to `jitter` off its row and its parasol's
  octagon at random (`rng("terrace", "table", ...)`). Checks: table sets by kit bounds (`piece_clear`), canopies as
  circles in their height band (`parasol_clear`), against `Squares._obstacles` (trunks and crowns, street lamps,
  doors with their free zone, the buildings' wall pieces) plus the seafront's lamps, benches and railing, the steps
  (`stair_clear`) and the pieces already placed; tables on their sidewalk or the promenade, canopies over them,
  off the walls, `rail_clear` m inside the sea edge; every piece in a tile holding `town_tile` buildings (a tile
  with only the promenade's sea half and the beach is light: a kiosk cafe would add a fifth to it). Customers sit
  on the chairs (`[people.seats] cafe_set`), a waiter stands by some shaded tables (`[people.terrace]`). Pieces:
  `parasol_white`, `parasol_blue`, `parasol_sand` (`parasol` in `mesh/furniture.py`, one piece per
  `parasol_colors` entry sharing the pole and ribs: a wooden pole from just under the table top, an octagonal
  canvas in a gentle dome and a valance, smooth-shaded with real faces on both sides, eight iron stretchers, a
  finial; 158 triangles, no UVs; sizes `parasol` and `parasol_valance` in `[dressing.furniture]`) and
  `kiosk_drinks` (the kiosk in Sidi Bou Said blue, racks of cans and bottles, no tobacco diamond, nine plain
  materials, no UVs; lit twin `kiosk_drinks_lit`). Quick capital: 4 cafes, 29 tables, 25 parasols, 6 kiosk cafes,
  38 customers seated; full capital: 34 cafes, 217 tables, 163 parasols, 41 kiosk cafes, 280 seated.

Invariants (tested): buildings are valid polygons inside the city and stay off street surfaces
(impasses included); every old-town dwelling's main door opens on a street, alley or impasse; an
impasse lies inside its block past its mouth, opens on exactly one street (or branches off exactly
one impasse) and touches no other street, so it is a dead end;
flat roofs carry the parapet from `[roofs]` and, where the layout puts one, a stair room whose
door opens on free roof; roof props always stand inside the parapet and outside the stair room;
massing keeps every building, household, souk, street and tree, and every new footprint lies inside
the old one; greenery keeps every older tree as a prefix of `trees`, its arterial trees stand in their
pits clear of junctions, paint, lamps, real stair-door paths and arcade bands, its courtyard crowns
clear the walls, and each villa garden lies in its lot off the house with an opening in its hedge
where the path runs; windows and balconies stand only on walls drawn at their height; roof props and tank
stands stand on the topmost roof deck drawn at their position, never in a roof room, a lift room or
a corner dome; a massed building draws no face twice in one plane; a cut colonial corner carries
the arcade round it when both its facades have one; its paved lot corner meets the sidewalk at the
sidewalk's height and `Ground.surface` there is what is drawn;
sidewalks never enter a building footprint, keep at least `min_carriageway` meters of asphalt,
and stand `curb_height` above the street ribbon; every road marking lies inside its street's
carriageway; the kasbah leans on the city wall on the old town's high edge, holds no house, street,
gate or great mosque, no rampart runs along it, a souk reaches its gate, its merlons crown walls drawn
without a parapet and its paving lies on the terrain mesh; the cathedral and the theatre stand on one merged
lot of 3-6 colonial lots facing the boulevard, house nobody, stay under 6,000 triangles with meter UVs, carry
no arcade, car, furniture, person or trunk, have no car or planned tree before their steps, and their camera
views see the whole facade; the station stands across an avenue from the colonial quarter, off every street,
its buildings last and housing nobody; its 2-4 tracks end past the city limit; no other building, lot,
walk or tree lies on its precinct or corridor; every street on the corridor crosses it; in its tile no
piece touches them; quays stand `reach` m off the old coast in port districts, clear of the corniche, their
aprons in `land`, the ground on them exactly `level` m and the drawn terrain equal to the ground off the
walls; the water off a quay is dredged to `depth`; the breakwater starts at a quay and stays in the sea with
the lighthouse (the last landmark) on its head; no building, tree or other piece stands in the sea or on the
quay edge but bollards, fenders, armour stones and the harbor's props; boats float with the waterline at 0 over
water deeper than their keel, off the quays, the breakwater, the shore and each other, cranes, rails and cargo
stand on the apron at quay level clear of the bollards, drawn-up boats rest on the sand above the water, and
nothing else stands where props stand on land; the seafront promenade lies between the corniche's carriageway
and the sea, off the harbor and never over water, level across at curb height above the ribbon at its curb,
with the beach-side palms on it (same index, kind, height), lamps in the palm row, benches by the railing facing
the sea, the railing along the sea edge, no paint or parked car on it; everything is deterministic.

## 6. Output files (`output/<country>-<seed>/`)

| File | Content |
|---|---|
| `world.json` | `citygen-world/1`: seed, name, size, settlements, roads (coords in meters) |
| `cities/<name>/plan.json` | `citygen-city/1`: districts, streets, buildings, trees, landmarks, households, souks, and `rail` (track center lines, corridor) when the city has a station, `port` (quay edges and aprons,
breakwater lines, basins, lighthouses) when it has a harbor, `props` (`kind`, `x`, `y`, `yaw`, `scale`, `on`: boats, cranes, rails, cargo; empty without a harbor); GeoJSON-style geometry in world meters |
| `gazetteer.md` | readable guide for stories |
| `maps/country.png`, `maps/<city>.png` | 2D maps, north up |
| `tiles/tile_<i>_<j>.glb` | 3D tile covering x `i*512..(i+1)*512`, y `j*512..(j+1)*512` |
| `tiles/tile_<i>_<j>_lod1.glb` | the same tile for distant views (prompt 40): merged blocks, low-poly landmarks, 32 m terrain, flat colors |
| `tiles/textures/*.png` | base-color images shared by the tiles (`[tiles] textures = "shared"`, the default) |
| `tiles/index.json` | `citygen-tiles/1`: tile list (bytes, unique and drawn triangles, dressing pieces, `lod1`: file, bytes, triangles; `files`: shared textures and the lod1 file), `"parapets": true` when the tiles carry their own roof parapets, `focus` point, camera `views` (street, souk, and cathedral, theatre, station, port and corniche when the city has them), `cities` (name, plan file, bounds) |
| `summary.json` | counts and timings (read this instead of big files) |

**.glb conventions:** one root node per tile with `translation = [x0, 0, -y0]`; vertices are
local to it. One primitive per material; material names are palette names from the style pack
(colors are written linear, palettes are sRGB hex). A building or tree belongs to the tile that
contains its center, so tiles never duplicate objects. Terrain edges match between neighbors.
Street dressing and trees are drawn with `EXT_mesh_gpu_instancing`: one child node per piece
(named like the piece, e.g. `tounes/door_sbs_blue`) with TRANSLATION, ROTATION and SCALE arrays,
local to the tile root. Kit pieces may carry `COLOR_0` (linear, 8-bit RGBA) on white materials,
terrain parts carry it as a soft tint (see "Ground textures"),
and lamps an `emissiveFactor`. Importers without the extension (Blender 3.6) show one copy per
piece; `tools/blender_import.py` and `tools/blender_beauty.py` place all copies themselves.

**Quantized tiles (prompt 39, `[tiles] quantize = true`, `write_glb(quantize=True)`):** the tile
lists `KHR_mesh_quantization` in `extensionsUsed` and `extensionsRequired`. The root node's own mesh
holds only the triangles that must stay float: `add_sheet` faces (cloth, flags, landmark glass and
iron, marked with `MeshBuilder.fine`), triangles with an edge under `[tiles] fine_edge` (0.05 m:
ropes, cables, vault rods, thin bars, dome tips) and `[tiles] float_materials` (`water`: the viewer
finds the sea from the water's own height). Everything else goes to the child node `tile_i_j_q`
(extras `{"quantized": true}`): positions as normalized SHORT, padded to 8 bytes, dequantized by that
node's `translation` and one **uniform** `scale` (the half size of the mesh's box, so a step of about
8.4 mm on a 550 m tile; uniform keeps normals and raycast face normals right in the mesh's own
space). The root's translation is never used for dequantization: it would also move the instance
nodes. Normals are normalized BYTE (padded to 4 bytes); **flat faces have no NORMAL**: triangles whose
stored normals all lie within `[tiles] flat_angle` (1 degree) of the face normal of their written,
dequantized corners go into primitives without NORMAL (walls, roofs, flat pieces; the tinted terrain,
trees, domes, people and other smooth surfaces keep theirs). Their vertices stay split exactly where
the normals differed (the weld key still holds the normal), so area-weighted vertex normals are the
flat normals again: the viewer calls `computeVertexNormals()` on every mesh without normals right
after a tile loads and clears GLTFLoader's `flatShading` (the `shared()` key holds `flatShading`
too); Blender's importer shades such faces flat; `read_parts` computes the same normals
(`vertex_normals`). UVs stay float (meters: walls
and the tile mesh share each material and its one `KHR_texture_transform` with world-meter caps,
the terrain and the pieces; Blender's importer would leave normalized values in the UV map that
`blender_beauty.py` reads as meters), colors stay 8-bit. Vertices whose written bytes are equal are
welded (shared cap corners, stair rooms, landmark faces), in order of first use, and a primitive
over 65,535 vertices is split, so every index is 16-bit. Instances: TRANSLATION float, ROTATION
normalized SHORT (worst angle error under 1e-4 rad, tested), no SCALE accessor when every instance
of a float piece has scale 1. A piece gets 16-bit positions in its own frame (center c, half size h)
when its vertices outweigh 12 bytes per instance or it needs SCALE anyway; its instances are then
written at `T + R (S * c)` with scale `S * h`. Accessors of one kind share one bufferView (with
`byteStride`). `read_parts` and `accessor_array` (`mesh/gltf.py`) decode strides, int8/int16 and
normalization and apply the child node's dequantization; `instance_transforms` in
`tools/blender_import.py` reads 16-bit rotations and a missing SCALE as 1, and `bake_dequantization`
applies the `_q` object's transform to its mesh after Blender imports it. `quantize = false` writes
the float tiles byte for byte as before. `python -m citygen stats --tiles [FOLDER] [--tile NAME]`
lists every tile's bytes by category (JSON, terrain, tile mesh, piece meshes, instance transforms,
textures) and details the heaviest one by material and by piece.

**Level-of-detail tiles (prompt 40, `citygen/mesh/lod.py`, `[tiles.lod]`):** right after each full tile
the same worker writes `tile_i_j_lod1.glb` from the same plan data (no dressing, people, trees or textures),
with the same root node (`translation = [x0, 0, -y0]`, extras `"lod": 1`) and the same quantized writer;
materials keep their palette names, without texture or UVs, each textured color multiplied by the mean of
its image (so the far look matches the full tile's mipmapped textures). Content:
- *Terrain*: 32 m cells (`terrain_step`, rounded to an even multiple of the full step that divides the tile)
  on the full tile's lattice, the full tile's diagonal, COLOR_0 tint and smooth normals (from the same 8 m
  differences as the full tile); along every tile edge the full tile's 8 m points (border cells fanned onto
  them), so a full and a lod1 tile, or two lod1 tiles, share every edge vertex. A skirt hangs `skirt` m
  (4 m) below each edge (8 m points on top, 32 m nodes below, terrain normals and tint) against cracks
  between two quantization frames. Cells a quay wall crosses are cut by `split_cells` at 32 m (sharp quay
  edge). The water plane when the full tile has one.
- *Streets and roads*: flat ribbons (no UVs) draped on the drawn lod terrain `street_lift` m up, lines
  simplified by 1 m and sampled every 16 m; impasses left out (`skip_streets`).
- *Blocks*: each building belongs to the block (`plan.blocks`) holding its `point_on_surface`; a block is
  drawn by the tile holding the block's centroid. Its buildings' footprints are grown by `close`, united,
  shrunk back, simplified by `simplify`, courtyards under `min_hole` m2 filled, pieces under `min_part`
  dropped. Walls run from the ground `sink` m down up to the ground plus the block's rise (area-weighted mean
  of each building's highest ground + roof height - ground at its centroid; roof height = masses' tops,
  + `parapet` on flat house and apartment roofs, + `hip` on hip roofs); each wall segment takes the wall
  color of its nearest building; the cap (draped the same way) the block's dominant roof color.
- *Skyline, drawn alone* by the tile holding the building's center: monuments (minaret, mosque hall and
  court, marabout, rampart wall and tower, kasbah wall, tower, gate and palace) and buildings at least `tall`
  m (20) or `tall_ratio` (1.6) times their block's mean; also buildings in no block. Each mass is a prism
  (hip roof where it has one), domes on 8-sided drums, a minaret's lantern box and dome cap, a corner dome or
  turret, battlements as a band (breast + half a merlon). The lighthouse is its own lathe with 8 sides.
- *Clustered*: the cathedral, theatre, station head and platforms, quay walls and breakwater are drawn
  with their full mesh functions, then simplified by vertex clustering (`cluster` 1.2 m, `cluster_port`
  3 m, world-aligned grid): thin sheets and `cluster_drop` materials (glass, iron, wood) left out,
  collapsed and duplicate triangles dropped, corner normals smooth within `crease` degrees (rubble and
  domes share vertices, walls stay flat and go without NORMAL).
The index entry gets `"lod1": {"file", "bytes", "triangles"}` and the lod1 file in `files`, so resume counts a
tile as finished only when its lod1 file exists at its written size. Sizes (full capital): 7.7 MB in all
for 171 MB of full tiles; city tiles 3.6% of their full tile (densest 141 KB, 6,780 triangles, for 5.8 MB),
terrain-only tiles 11%, worst 12.9% (a harbor tile). `stats --tiles` prints the lod1 total and ratios.

**Viewer level of detail (prompt 41, `tools/viewer/index.html`):** one slot per index tile holds what is
shown (`full`, `lod1` or nothing), the parsed versions in memory and the loads in flight. Every camera
move recomputes each tile's want from `d`, the 3D distance from the camera to the tile's square at the
focus height: full under `LOD_IN` (1400 m), lod1 over `LOD_OUT` (1700 m), in between it keeps its want
(a tile seen for the first time splits at 1500 m, so a still camera always gets the same tiles).
Full tiles also need the tile within `RADIUS` (2500 m, `?radius=`) of the orbit target; lod1 covers every
tile of the build. Loads: lod1 first for every tile showing nothing, nearest first (the whole capital in
under a second), then full tiles by distance, at most 6 at a time; `fetch` with an AbortController
cancels a full load no longer wanted, and a tile parsed after that is disposed unseen. A parsed tile is
prepared off-scene (normals, shared materials, night lists) and swapped in the same task as the old
version leaves, so no frame shows both or a hole. A full tile that leaves is disposed (geometry,
instance buffers; shared materials and their textures stay); lod1 twins stay in memory, so turning back
to lod1 is instant. Images are fetched and decoded once (`THREE.Cache`). The shadow map re-renders
only when a swapped tile's box meets the shadow frustum. `extent` (fog, far plane) spans the wanted
tiles, the camera clamp uses the lowest shown tile of either kind, the street fallback waits for the
tiles within 200 m of the focus to reach their version. URL settings: `lod=full` (full tiles only,
the viewer before prompt 41), `lod=lod1`, `lod_distance=1500`. The stats line shows the full and
lod1 counts; `window.citygenStats` adds `full`, `lod1`, `loading`, `settled`, `coveredMs` and
`settledMs`. `window.citygenReady` is live: true on a frame drawn in the settled state (every tile at
its version, nothing in flight, the street camera placed) after the first full load, false while
the camera move makes tiles load. `tools/make_artifact.py` swaps the one reading line of `fetchTile`
for its base64 JSON files and converts the lod1 files too.

**Other engines (note for prompt 72, Godot 4):** not verified here. Godot 4's glTF importer is
believed to read `KHR_mesh_quantization` and to generate normals when NORMAL is absent (to verify in
prompt 72: they must come out flat on the split vertices); `EXT_mesh_gpu_instancing` support is not confirmed (it
may need a `GLTFDocumentExtension` that turns each instance node into a `MultiMeshInstance3D`, or
expanding the copies on import). Test one quick tile in Godot first; `[tiles] quantize = false`
removes the quantization requirement if needed.

**Textures:** a palette entry may carry `texture = "<name>"` and `texture_size = [w, h]` (meters
one repeat covers). The writer emits `images`, `textures`, one REPEAT sampler with mipmaps
(`wrapS`/`wrapT` 10497, `minFilter` 9987) and a `baseColorTexture` with
`KHR_texture_transform` scale `[1/w, 1/h]`, so the meter UVs never change. The palette color
still multiplies the image (`baseColorFactor` x texture), so images stay near-neutral detail
around white. `[tiles] textures` is `"shared"` (each image written once by the parent into
`tiles/textures/`, tiles link it with a relative URI; a tile counts as finished only when the
files in its entry exist), `"embedded"` (bytes inside every .glb, for single-file exports) or
`"off"` (flat colors). The phone page (`tools/make_artifact.py`) stores each image once as
base64 JSON and maps `textures/<name>` to blob URLs with `loader.manager.setURLModifier`.

**Generated surfaces (prompt 18):** `citygen/mesh/textures.py` makes the images with code:
plaster, render, render_cream, stone, concrete, roof_tile, roof_flat, paving, asphalt, earth,
sand, grass, rock and scrub. Each is 256 or 512 px square, seamless (periodic noise, a wrapped
stroke canvas, a Fourier blur) and near-neutral grey around white: the palette color tints it,
and no palette color, window or door is baked in. Each texture owns
`stream(seed, "texture", name)`. Sizes and noise strengths live in `[textures]` of the style;
`band` adds the colonial string course to `render_cream`, one per repeat, and its palette
`texture_size = [3.0, 3.6]` matches the colonial floor height. `python -m citygen
texture-sheet` writes `output/checks/texture-sheet.png` with every texture tiled 2 x 2, tinted
by its palette color (or its `tint` sample) and labelled with its name, size and repeat. Files
are PNG or JPEG, whichever is smaller.

**Textured walls and roofs (prompt 19):** the maghreb palette maps plaster walls
(`lime_white`, `warm_white`, `sand`, `ochre`, `dome_white`) to `plaster` at 3 m, colonial walls
(`cream`, `pale_yellow`) to `render_cream` at 3 x 3.6 m, `pastel_blue` to `render`, modern slabs
to `concrete` at 2.4 m, ramparts, minarets and stone plinths to `stone` at 2.4 x 1.8 m, flat
roofs to `roof_flat` at 2.5 m and hip roofs to `roof_tile` at 2 x 1.6 m. Wall UVs put `v = 0` at
`z_ref` (the highest ground under the building), so bands line up along a street. `add_walls`
splits the wall at `z_ref + plinth height`; `[plinth]` gives each district kind its material and
height (a blue-grey band in the medina, stone or concrete elsewhere). Only street-facing exterior
segments get the plinth (distance to the street center line allows for half the street plus its
sidewalk), and courtyard holes stay plain: party walls cannot be seen and would cost bytes. Hip
roofs use planar meter UVs (u along the eave, v up the slope, each end face with its own slope
length), so tile rows run down every face instead of smearing. The viewer sets anisotropy 8 on a
computer (2 on phones, which keep the Fast quality) with mipmaps from the shared sampler.

**Massed buildings (prompt 23, `mesh/tile.building_mesh` with `roofs`):** a building that is more
than one box is drawn as one solid. The outer walls go once round `massing.outline(b)` (the
footprint ring with every mass corner on it inserted), each segment up to the tallest mass whose
outline runs there plus its parapet, drawn in groups of one height with `add_walls(only=...)`: u
stays measured along the whole ring and `z_ref` is the building's highest ground point, so the
plaster bands and the plinth run on unbroken across a step or under a set-back floor. Inside the
footprint, `inner_walls` draws where a taller mass rises over a neighbour (from the neighbour's
parapet top) or over the terrace it stands on (from the deck). Each roof is drawn by its kind: a hip
roof on its part's rectangle, or the deck (leaving out a mass standing on it), parapet coping and
rooms of `roof_layouts`. Lift motor rooms are boxes in the wall and roof materials with a steel door;
a corner dome or turret is a 12-sided drum, a stone ring and a dome (`_roof_things`). A menzah is a
box like the stair room with a door and up to two windows (glass panels) on its outer walls.
A cut corner's `apron` is drawn by the tile owning the building (`apron_mesh`): sidewalk paving on
the triangles of `ground.apron_cells` (the polygon cut in `[streets] apron_cell` m squares on the
world grid), corners at `Ground.apron_top` (ground height, a blend of the lifts of the streets within
`apron_reach` weighted (1 - d / reach)^2 / (d + 1 m)^2, the sidewalk's own rule within `walk_reach` so it meets the
sidewalk at its height, plus the curb), rows along the nearest street, a curb skirt where it meets
lower ground. `Ground.surface` interpolates those same triangles there, so doors, arcade pillars and
trees stand exactly on what is drawn.

**Ground textures (prompt 20):** every terrain material is textured (`beach` sand 6 m, `desert`
sand 8 m, `steppe` scrub 5 m, `grass` grass 3 m, `forest` scrub 4 m, `rock` rock 8 m,
`urban_ground` earth 8 m), and so are the streets (`asphalt` 6 m, `paving` 3.2 m = 0.8 m slabs,
`earth` 5 m), `sidewalk` (paving at 2 m = 0.5 m tiles) and `curb` (stone at 3 x 1.8 m = 1 m
stones). `road_paint` stays a flat color. UVs stay meters: terrain is planar (x, -y); a street
ribbon has u along the street, counted from the street's start (so a street cut by a tile edge
keeps one pattern) and v across from the center line; a sidewalk triangle turns its planar UVs
so u runs along its nearest street (one walk piece wraps a block corner, so the direction is per
triangle); the curb face has u along the curb and v down from its top edge. Against repeats
from the air the terrain carries `COLOR_0` from `[ground_tint]`: a brightness drift and a slight
warm/cool shift from world-position noise (`Fractal(seed, "ground_tint")` and
`"ground_tint_warmth"`), always in (0, 1] so it only darkens or shifts a little, identical on
both sides of a tile edge. Only terrain parts carry it. The viewer keys its shared materials on
`vertexColors` too, so a tinted and an untinted part with one material name never share a
material. In Blender the importer multiplies `COLOR_0` into the materials it keeps;
`tools/blender_beauty.py` replaces the ground, asphalt and paving with its own procedural
shaders (which ignore the image and the tint) and takes their palette color from the tiles'
`baseColorFactor`, since a textured material's Base Color socket is linked, not set.

## 6b. Kits and street dressing

- **Pieces** are small meshes in their own space: x along the wall, front toward the street
  (generator +y, glTF -Z), up z. Ground pieces have their origin at the bottom-center on the
  drawn surface (`Ground.surface`: ground, street ribbon or raised sidewalk); wall pieces on the
  wall face at street level for doors, shop fronts and awnings (the surface 0.5 m in front), at
  the sill for windows, at the hook for lamps and anything hanging.
- **Procedural pieces** (`mesh/props.py`) keep plain names (`door_blue`, `shop_front_spices`,
  `tree_palm`). **Kit pieces** load from `kits/<kit>/manifest.json` (`citygen-kit/1`: materials,
  then pieces with file, category, anchor, tags, optional `materials_map`) and are named
  `<kit>/<piece>`, so a kit never replaces a procedural piece. `[build] kits` lists the kits used.
  `python -m citygen kit-sheet --kits <kit or folder> ...` shows other kits (default `[build] kits`).
- **Kits from Blender** (prompt 38, `tools/blender_kit_export.py FILE --collection C --name KIT`):
  a plain script that starts Blender in the background (refused inside a sandbox, `sandboxed()`
  of `make_blend.py`) with its own export code. Every mesh object of the collection (sub-collections
  too) becomes `kits/<KIT>/<object>.glb` (name lowercased, other characters `_`) plus the manifest
  (`"made_by"` marks it; the tool refuses to write over a kit it did not make, such as `tounes`,
  and removes the .glb of pieces gone from the collection). Custom properties on the object:
  `category` (default `ground_prop`), `anchor` (`ground` or `wall`, default `ground`; warnings for
  both), `front` (`+Y` or `-Y`, default `--front`, `+Y`), `tags` (comma-separated). Axes: the
  front is Blender +Y = generator +y; the glTF exporter (`export_yup`) maps it to glTF -Z. A piece
  modeled facing -Y is turned 180 degrees about Z. Rotation, scale (a mirrored one flips the
  normals) and modifiers are baked into the mesh, the translation is dropped, so the object's
  origin is the anchor and the .glb has no node transform (`read_parts` ignores them). Materials
  with a palette name keep the palette's look; others become `<KIT>_<material>` with the Principled
  BSDF base color, roughness, metallic and emission written to the manifest (Blender's linear
  values as sRGB hex). No UVs and no vertex colors are exported. A `.py` file instead of a `.blend`
  builds the scene in a fresh Blender first: `tests/data/blender_kit/source.py` makes the test
  fixture (a house modeled facing -Y and an arrow), re-exported byte for byte the same.
- **Roles** (`[dressing.roles]` in the style): a role (`door_blue_rich`, `lamp`, `souk_awning`,
  `tree_palm`...) lists `[piece, weight]` or `[piece, weight, extra height]`; missing pieces are
  skipped and a role with no entry uses the piece of the same name, so the city dresses itself
  without any kit. Chances and heights are in `[dressing]`; souk goods in `[[souk]]`.
- **Dresser** (`city/dressing.py`): per building (one random stream each) the main facade gets a
  shop (souks), a cafe (colonial) or a door with lamp, hood, pots, bench, cat, climber, parked
  moped; other walls get windows by floor (grilles, shutters, birdcage bays, one mashrabiya
  balcony for rich households; in the colonial district a window with an iron balcony instead); flat roofs get tanks, dishes, laundry racks and pots inside the
  parapet and off the stair room. Per street:
  laundry, cables, lantern strings, bunting and sabats across alleys and souks (none under a souk roof),
  arches over alley
  mouths, gates and handcarts in souks, lamps along main streets (`Dresser.lamp_spot`: none off the
  street or inside the surface of a wider street, such as a grid street lying under the boulevard). Impasses are dressed like alleys
  (laundry and cables; `FRONT_PREF` lowest, so a house with a street wall keeps its door there); a
  covered impasse gets a sabat as long as `covered` over its mouth, an uncovered one sometimes an
  arch just inside its mouth (`impasse_arch`); both need houses tall enough on both sides. The main
  facade is the best street wall long enough for a door (2.3 m), if any is. Planned trees become instances.
  Nothing is stored in the plan: a tile asks for what it owns and always gets the same answer.
- **Every home** (prompt 20.1, `[dressing] every_home`, `[dressing.open_walls]`, `[dressing.slab]`,
  `[dressing.paths]`, geometry helpers in `city/openings.py`): after the street walls and the roof
  (which keep their one stream `rng("b", k)` and so every piece placed before), each dwelling gets
  its main door from `Dresser.door_spot(k)` (all its doors: `entrances(k)`), the one function the
  dressing itself places doors through. A `DoorSpot` holds the point on the wall, the outward
  normal, the threshold height, the wall index, the piece, how it is reached (`street` with the
  street index, `open` ground with the nearest street, or `enclosed`) and an optional paved path.
  Order: the street door as before; beside a shop or cafe a narrow house door (`house_door_*`,
  own stream `house-door`) where the wall has room clear of the shop, awning, goods, lamps and a
  `door_clear` zone in front; else another street wall, a wall facing open ground toward the
  nearest street (`door` stream), or, fully enclosed, the wall toward the nearest street (prompt
  20.2 cuts an impasse to it). Walls with no other building (ramparts and towers included) within
  `clear` m in front are open: one probe rectangle per wall against the footprint STRtree. Open
  walls get windows by district (`first` floor, `share`, `open` stream), never cutting a corner or
  overlapping any piece already on the building. Modern slabs: a window in every `bay` column on
  every floor, ground floor too (`slab_window_<tint>`, one tint per block, some shutters closed),
  concrete balconies stacked in a rhythm of columns, blind gable ends; stair doors (`stair_door`,
  glazed, with a canopy and light; `stair` stream) every `stair_spacing` m on the long side facing
  the nearest street, each in a window column whose stair windows sit half a floor up. Doors on
  open ground in `[dressing.paths] districts` get a paving ribbon straight to the nearest
  sidewalk or street edge that crosses no building; it is draped on `Ground.drawn` (the terrain
  mesh as drawn) with a small lift, and the door threshold is the path top. Other doors on open
  ground also stand on `Ground.drawn`; doors on a street or walk on `Ground.surface`.
- **Lit windows at night** (prompt 21, `[dressing.lit]`, `Dresser._light`): the palette's `glass_lit`
  is an exact copy of `glass_dark` (color, roughness, no emissive), so nothing glows by day in the
  viewer or in Blender; the viewer's night code (`LIT_AT_NIGHT`) lights `glass_lit` only. `Kit` adds
  a twin `<piece>_lit` for every window, balcony and door piece with `glass_dark` (the same part
  arrays, `glass_lit` for `glass_dark`; closed slab shutters have no glass and no twin). A kit window
  that declares its glass in the manifest (`"glass": [x0, x1, y0, y1, z]`, glTF axes) gets
  `<piece>_pane_lit`: one `glass_lit` quad over that rectangle, `pane_offset` m in front of the glass
  (behind its grille); the viewer draws `*_pane_lit` nodes at night only and Blender hides objects
  drawn only in `glass_lit`. After every piece of a building is placed exactly as by day, one draw
  on `rng("lit", k, side, floor, section, half)` per flat decides lit or dark: a flat is one floor of
  one side of the building (its outward direction in whole degrees, modulo 360); in a modern block one half of one stair's section (sections as
  `stair_spacing` spaces the stairs). Staircases (`window_stair`, `stair_door`) draw once per section
  with their own chance `stair`. Chance per flat: `base + member x (members - members_ref) + wealth x
  (wealth - 0.5) + trades[trade] + district[kind]`, plus `couple` for two-person households, within
  `range`. A lit piece becomes its twin; a kit window keeps its piece and gets its pane right after
  it. Quick capital: 40% of housing windows lit (medina 34%, colonial 39%, modern 41%). The glTF
  writer reuses the accessors of a part drawn twice, so a twin costs one mesh entry, not a copy.
- **Colonial arcades and iron balconies** (prompt 22, `[dressing.arcade]`, `[dressing.balcony_iron]`,
  layout in `city/arcades.py`, glue in `Dresser._colonial`): after the street walls and the roof (no
  draw on `rng("b", k)`), every wall of a colonial building facing one of `kinds` (boulevard, arterial,
  ring; the street 1.6 m in front of the wall decides, not `FRONT_PREF`) gets a ground-floor arcade over
  its sidewalk: `arcade_bay` pieces (a round arch on two half pillars with base and capital, archivolt,
  keystone, the walkway with its ceiling, a terrace slab and a cornice; 168 triangles), stretched along
  the wall by `Placement.stretch` (an extra scale on the piece's x, written into the instance's SCALE)
  so the bays fill the run end to end. A run is the part of the wall with nothing built within the
  arcade's depth and sidewalk under its pillars; where the next building stands in line within
  2 x `join` m it reaches half way across the gap, so neighbours' arcades meet. Bay edges (pillars) keep
  `gap` m clear of every door and shop front on the wall and of any piece reaching the pillars' strip
  (least squares on a 5 cm grid, `bay` 3.5-4.0 m, else `bay_relaxed` 3.2-4.4 m, else the run is
  shortened at a free end); cafe tables on such walls stand `cafe_reach` m out, under the arcade. Each
  run is made level in groups while its sidewalk rises less than `step`, never more than `above` over
  the first floor line; pillars reach `sink` below street level. A square corner (within
  `corner_angle`) between two arcades gets `arcade_corner` (narrow arches on both streets, an L-shaped
  pier), a corner onto another street the corner piece and `wrap` bays into it; shallow convex bends
  (under `bend`) carry one arcade round them. Old pieces the slab or pillars would cut (vines, hoods,
  cascades, a clothesline under a first-floor window) are left out, doors and shops always stay; every
  home's new doors avoid the pillars (their boxes run from the wall out to the pillars). Street lamps
  standing in an arcade band (every such wall, and the first bays of a side street an arcade turns into,
  out to the pillars plus `lamp_clear`) move `lamp_shift` m toward the curb, or are left out when that is
  not on a sidewalk clear of it. Planned trees (the plan is unchanged; `Dresser.tree_spots`, used by the
  tile) whose trunk falls within the pillars, cornice, `tree_trunk` and `tree_clear` of such a wall move
  straight out toward the curb until clear, turned so a palm leans over the street; left out unless they
  then stand `tree_curb` m inside the sidewalk. Iron balconies
  (`balcony_iron` 1.2 x 0.6 m, 278 triangles; `balcony_iron_long` across two windows, stretched to their
  spacing; a stone slab on consoles, bars with faces on both sides, a frieze of rings) go on street
  windows of the upper floors, never on the floor right above an arcade: per floor of each facade one
  draw on `rng("balcony-iron", k, wall, floor)` for the row (`row` + `wealth` x (wealth - 0.5)), then per
  window. Quick capital: 312 bays on 95 facades, 17 corners, 1,523 + 335 balconies; 19 lamps and 10
  palms moved to the curb, 2 palms left out. Cut corners (prompt 23): a cut's faces read their street
  from the old corner point (`massing.probes`) and carry the arcade of a facade they turn from; each
  face gets its bays, each turn of 45 degrees (`arcade_bend`) or 22.5 degrees (`arcade_bend_round`,
  within `bend_tol`) a pier piece on the bisector (a wedge: pillar faces, trims, cornice, ceiling and
  terrace mitred; 72 triangles), and `wrap` bays turn into a side street without an arcade. Their
  pillars may stand on the lot's open corner in front of the cut. A run whose end meets a corner or
  bend piece gives way at its other end first when it must be shortened.
- **Villa gardens and hedges** (prompt 24, `Dresser.garden`, `[dressing.hedge]`): the tile owning a
  villa asks for its garden after dressing it: the lot (the parcel holding a point of the footprint,
  `openings.villa_lots`) minus its door paths (shrunk 5 cm, so the garden slips under the path edges);
  the part under the house stays in, hidden by it (a hole costs about a quarter more triangles). `garden_meshes` cuts it on the terrain mesh's own triangles (`ground.terrain_cells`:
  8 m cells split along the south-west to north-east diagonal) and drapes it on `Ground.drawn`,
  `garden_lift` m up, in the `garden` material (the grass texture): exact on the terrain, unlike
  recoloured 8 m cells. Hedges (`hedge`, 18 triangles, a box with chamfered top `thick` x `height`,
  `sink` below ground) run `thick` / 2 inside every lot edge; an edge shared with another villa lot is
  planted only by the lot of lower parcel index; a corner belongs to the run planted first (later runs
  stop at its body), acute corners end at the lot edge; runs open where a path crosses (`gate` m wider
  than it; a villa without a path opens on its edge nearest the house) and round planned trunks
  (`trunk_clear`); each run is filled by pieces of at most `piece_max` m, stretched along x
  (`Placement.stretch`). Full capital: 2,900 gardens (98 ha), 31,100 hedge pieces, 192 km of hedge.
  The map paints villa lots `GARDEN_RGB` and citrus trees orange.
- **Parked cars and taxis** (prompt 25, `mesh/vehicles.py`, `city/parking.py`, `[dressing.vehicles]`,
  `[dressing.parking]`): pieces `car_<type>_<i>` (category `vehicle`, so no lit twins) for `hatch`,
  `sedan`, `van`, `louage` (white minibus with a red, blue or yellow stripe; a roof rack with luggage on
  some, `stream(seed, "piece", name)`) and `taxi` (the sedan body in yellow with a white roof sign), four
  body colors each from the style. Each is a side profile drawn across the width (bumpers, bonnet,
  arches, boot or hatch) under a narrower cabin with flush `glass_dark`, octagonal tyres, lamps, grille,
  mirrors and a sill strip: 152-164 triangles (184 with a rack), no UVs; the color pieces of a type share every part
  array, so a tile writes each type's geometry once. Rows: a street of `kinds` parks on both sides
  when its carriageway (width minus the widest sidewalk of each side) holds 2 rows + 2 lanes (`row`
  2.4, `lane` 3.0), on the wider sidewalk's side when it holds 1 + 1, else not; a boulevard along the
  outer curb of each carriageway; only along sidewalks of `districts` (colonial, modern, residential).
  A row is cut into runs `junction_clear` from every street that meets it (not the grid streets lying
  on a boulevard: wholly inside, or running 8 m or more inside it within 15 degrees, `lying_on`); each
  run is laid out whole on 0.5 m samples, slot by slot on `rng("park", street, side, run, slot)` (an
  empty stretch with chance `empty` by street kind, or a car of the `mix` and its gap), so a
  car is the same in every tile and belongs to the tile holding its center. A car stands `curb_gap` off
  the local curb (the sidewalk measured at that spot), faces its lane's traffic (driving on the
  right), sits on the drawn surface under its axles and is pitched along the street (`Placement.tilt`,
  written into the instance rotation). Gaps: `crossing_clear` from zebra bars, `tree_clear` from the bark of
  trunks as drawn (after `tree_spots`; radius `tree_trunk`), `lamp_clear` from lamps (`Dresser.lamp_spot`, kit bounds), `front_clear`
  either side of a cafe or shop front (`Dresser.front_of` replays `_front` alone), `door_clear` from the
  free zone of doors near narrow sidewalks and from stair paths carried `[dressing.paths] cross` m on
  (`Dresser.door_spots`). Every car is then checked exactly with its kit bounds: on its own street,
  off sidewalks, painted lines and other cars. Taxi rank (`rng("taxi-rank", "row")`): `rank` taxis at
  the end nearest the boulevard's junction with the most streets of the nearest parking run within
  `rank_reach` that holds them (the boulevard first). Quick capital: 1,525 cars (652 hatchbacks, 533
  sedans, 193 vans, 125 taxis, 22 louages), 127 streets and 7 arterials with one row, the boulevard with
  two (CP3: sides along non-parking blocks no longer count), a rank of 5 taxis in a colonial street by the
  boulevard; full capital about 13,700 cars (907 taxis, 201 louages).
- **Benches, kiosks and fountains** (prompt 26, `mesh/furniture.py`, `city/squares.py`, `[dressing.squares]`,
  `[dressing.furniture]`): pieces `bench_iron` (two iron side frames of closed bars, four wooden seat slats
  and three back slats; 180 triangles), `kiosk` (a dark green booth with cream trims, a serving hatch
  with a `glass_dark` pane over a counter of papers, a striped awning, magazine racks on both sides, a sign
  board and the red tobacco diamond; 232 triangles; category `kiosk` is in `LIT_CATEGORIES`, so the kit
  adds `kiosk_lit`; magazine colors on `stream(seed, "piece", "kiosk")`), `fountain_colonial` (lathed:
  marble basin on a step sunk `sink` m, column, two bowls, iron finial, `water_pool` in the basin and bowls,
  thin double-sided streams from each lip; about 740 triangles) and `sabil` (a wall piece: sandstone frame
  around an arched niche lined with `tile_panel` and `faience_white`, tiled jambs and band, marble cornice,
  copper spout and stream, marble basin; 208 triangles). A per-city pass (`Dresser.squares()`, built once,
  lazily; a tile keeps the pieces whose anchor it holds) cuts each boulevard's promenade into islands
  where other streets cross it (not the grid streets lying on it, `parking.lying_on`), then places, each
  on its own stream: a fountain at the island end nearest the ring road (else the boulevard's far end),
  `fountain_margin` m in, the planned trees within its radius plus `fountain_trees` left out
  (`Squares.keeps`, applied by `Dresser.tree_spots`, so tiles and parked cars agree); kiosks (at most
  `kiosks`, `kiosk_spacing` apart, chance `kiosk` per spot) on a paved cut corner (`Building.apron`)
  within `apron_reach` of the boulevard, else at an island end moved in up to `kiosk_slide` m, facing the
  junction, lit at night with chance `kiosk_lit` (`rng("lit", "kiosk", k, i)`); then a bench (role `bench`:
  `bench_iron` 3, `tounes/bench_sbs` 1) between each two kept trees of the middle row, its back to the tree
  line, turned to the walkway on alternate sides by the tree's place in the row. Door benches use the
  role `door_bench`. Every piece is checked with its kit bounds (the fountain as a circle, which no crown may overhang
  at any height) against trunks
  (`tree_trunk` + `tree_clear`) and crowns (a circle of `crown_cover` times the tree piece's half width,
  from its lowest leaf up), lamps of every street around, zebra crossings, parked cars, arcade bands and
  every piece of the dressed buildings around (doors with their `door_clear` free zone), and must stand
  inside its island or on the corner's paving and walks. A `sabil` stands by the great mosque (a mosque
  landmark inside the medina) and, with chance `sabil.gate`, by each gate: walls within `sabil_reach`,
  monuments (mosque, ramparts, towers) before houses, facing a souk before an alley before open ground
  (the first street within `sabil_face` m in front), then nearest; `sabil_front` m free in front, off any
  carriageway, `sabil_gap` from corners and wall pieces; one draw among the first `sabil_choice`. Quick
  capital: 1 fountain, 1 kiosk, 2 benches (the 76 m boulevard has two islands with one tree gap each),
  4 sabils (the great mosque's south wall, 3 gates); full capital: 1 fountain, 2 kiosks, 10 benches,
  4 sabils. Water: `water_pool` (never `water`, which the Blender scripts hide for their sea) gets the
  viewer's `/^water/` look but never starts the viewer's sea plane, and `shade_pool` in
  `tools/blender_beauty.py`.
- **People** (prompt 28, `mesh/people.py`, `[dressing.people]`): 26 kit pieces `person_<key>`, category
  `person`, ground anchor, no lit twin, 227-389 triangles each, no UVs (plain colors, like the cars). A
  figure is a skeleton in its pose dressed by its outfit: level-ring lofts (8 sides, smooth normals) for the
  torso, robe, wrap and skirts; mitred ring chains (6 sides) for limbs, so a bent knee or elbow stays
  closed; a latitude-longitude ellipsoid head whose faces are cut into skin and hair, or hidden under a
  hood or a chechia; octahedron hands; wedge shoes. No faces. Body types `male`, `female`, `child`
  (`_BODIES`: joint heights, widths and radii as fractions of the height; the child's head is bigger).
  Poses: `stand`; `walk` (left leg forward, right arm swinging forward, the back heel lifted 28 degrees,
  the hips lowered to reach the stride); `sit` (the hips' underside and the level thighs at `seat` = 0.45
  m, knees at seat + knee radius, shins vertical, feet flat; the origin is under the middle of the seat,
  so a sitter is placed at the seat's center, facing away from its back, at height seat height - 0.45:
  `bench_iron` and `doukkana` 0.45, `cafe_set` chairs 0.46 (0.7 m either side of the table, facing it),
  `tounes/bench_sbs` 0.48; the upper body leans back `lean` degrees); `carry` (walking, the right hand
  held out past the clothes with a palm-leaf basket and a loaf, or a plastic bag). Outfits: `jebba` (wool
  robe to the ankles with a trimmed neck, wide sleeves with doubled cuffs over white undersleeves, red
  `chechia_red` cap, `leather_yellow` balgha), `shirt` (shirt and trousers, sleeves long or short),
  `safsari` (a hood open from chin to brow, the wrap falling to the ankles, one hand holding it at the
  chin, its front edge a doubled strip), `dress` (modern dress, hair gathered at the nape; with `scarf` a
  headscarf hood and a short cape over the shoulders, long sleeves and a long hem), `boy` (t-shirt,
  shorts), `girl` (knee-length dress). Robes and skirts grow round the legs at each ring's height, so a
  stride spreads the hem; every hem and cuff and the hood's rim have faces inside too. Height (per body
  type in `heights`), shoulder width (`shoulders`) and a man's belly (`belly`) are drawn in that order on
  `stream(seed, "piece", name)`. Palette: muted `cloth_*` everyday colors, `skin_1`-`skin_4`, `hair_*`,
  `shoe_dark`, `leather_yellow`, `basket_straw`, `bag_plastic`, `bread_crust`. Placed by prompt 29 (next).
- **People in the streets** (prompt 29, `city/crowd.py`, `[people]`): `Dresser.crowd().people(tile, placements,
  centers, tile_bytes)` runs at the end of each city in `build_tile`, after the tile's other placements got
  absolute heights. Candidates, each on its own stream `rng("people", <place>, ...)`: souk walkers
  (`[people.souk]`: two lanes `lane` m off the center line, a station every `step` m per lane staggered by
  half a step, keeping to the right with chance 1 - `flip`, some carrying a basket or a bag); browsers at
  each souk shop front (`[people.shop]`: two slots, `reach` m from the wall, beyond the goods, facing the
  shop); sitters on every seat piece of `[people.seats]` (seat points, height and facing measured on the
  kit: `cafe_set` chairs 0.7 m either side of the table facing it, both customers turned `turn` degrees
  the same way so their feet pass; `doukkana`, `bench_iron`, `tounes/bench_sbs` facing their front; at
  seat height - `[dressing.people] seat`); sidewalk strollers on both sides of every street with walks
  (`[people.sidewalk]`, chance by the district behind the walk, along the walk's middle from
  `parking.walk_extents`); promenade strollers on the boulevard's islands (`[people.promenade]`) and on the
  corniche's seafront promenade between the palms and the benches (`[people.seafront]`); people
  along the great mosque's outline and round each medina gate (`[people.landmark]`, half standing and
  facing it); kiosk customers at the window and people round a fountain (`[people.square]`); now and then a
  waiter beside a shaded cafe table, facing it (`[people.terrace]`; a seated customer's own parasol aside); walkers in
  medina lanes and village streets (`[people.lane]`); and on the stair paths of modern estates
  (`[people.stair]`, walking or two neighbours chatting). A walker may come as a pair or a parent with a
  child, side by side (`pair_gap`). Outfits from `[people.outfits]` by district kind (`cafe` for cafes,
  `children` beside a parent); every chance times `density`.
  The tile also gathers a halo (`halo` m) of what its neighbours own: wall pieces of their buildings
  (`Dresser.wall_pieces`), street props and cars, squares, the seafront's pieces and trees. Candidates are
  sorted (seats, squares, shops, landmarks, stairs, promenade, seafront, sidewalks, souks, lanes) and one gives way to any earlier one too
  close, judged on the candidates alone with each pose's largest kit box: standing people `clear` apart,
  `seated_gap` from a seated one, `pair_gap` within a group; so tiles agree at their edges. The tile's own
  then go through `_cast` (each figure shown costs its mesh in the tile: the most frequent figures are
  kept while they fit in `bytes_share` of the tile's estimated bytes, `tile_bytes`; others take a kept
  figure of the same pose and outfit, else body, else are left out) and the checks: no footprint within
  `wall_gap` (seated: touching); all four box corners and the origin on one floor kind the place allows
  (a walk or paved corner, a pedestrian lane: souk, alley, impasse, medina street or earth village street,
  or open ground; never a carriageway; seated: anywhere but a carriageway); no piece's triangles below
  head height and above `foot_level` within `piece_gap` (a person may stand under an arcade, an awning or a
  crown, not in a pillar, trunk, lamp post, stall, cart, goods, bench, kiosk, fountain or car; a sitter's
  own seat piece aside). Heights: walks from their drawn triangles (as `walk_meshes` drapes them, a few cm
  off `Ground.surface` between outline points), lanes and paved corners `Ground.surface`, open ground the
  terrain mesh (`Ground.drawn`), a stair path its top. The door bench (`_front`) now stands on the street's
  level like the door (`front_surface`), and a free-standing one (`tounes/bench_sbs`) backs onto the wall
  instead of half inside it. Quick capital: 1,857 people (523 souk walkers, 128 browsers, 157 seated, 855
  on sidewalks, 11 on the promenade, 42 at the mosque and gates, 128 in lanes); the old-town tile shows all
  26 figures, light tiles 3-6. Costs: worst tile +8.3% bytes and +23% drawn triangles.
- **Covered souks** (prompt 31, `city/covered.py`, `mesh/vaults.py`, `[covered_souk]`): souks of the listed
  `trades` (Attarine, Chaouachia, Kmach) and the city's `longest` souk street are roofed. `Covers` (one
  per city, built by `TileContext` and handed to the dresser; a dresser alone builds the same one) works the stretches out from the plan and the ground, nothing is
  stored: the line is probed every `probe` m on both sides for a house wall (`CARRIERS`) within `reach` m
  beyond the street edge; a one-sided opening up to `bridge` m (an alley mouth) is bridged by a lintel; the
  roof stops where both sides open, at a longer opening, within half the width + 1 m of a bend sharper than
  `max_turn`, `end_gap` m before the line's ends (crossings, gates, the mosque), and a stretch starts and
  ends between two walls (at least `min_run` m). It springs at min(the taller wall top, `spring`) above the
  street, at least `spring_min`, constant along a stretch (it follows the street's slope); the crown is
  `rise` higher (at most 2 m). A segmental barrel vault (`ring` fractions across, `thickness`) springs from
  impost bands (`band` high, `band_depth` deep, their face `inset` m beyond the street edge): a house lower
  than the springing gets its wall filled up to it (never lower than `fill_min`), a side opening a `lintel`.
  Stations: the bends (rings mitred on the bisector; other stations keep `(w + band_depth) tan(turn / 2)`
  away so nothing folds), transverse arches every about `bay` m of each straight run (portal arches at both
  ends; none within reach of a bend), the edges of a square light opening (`hole`, with a low `curb` on the
  roof) in the middle of each bay, and every `step` m. Arches stand `arch_proud` below the vault on corbels
  painted red and green (`door_red`, `door_green`); a lantern (`vault_lantern` role, chance `lantern`, own
  stream `covered/lantern`) hangs on an iron rod `chain` m under each inner arch. Each segment belongs to the
  tile holding its midpoint, an arch or a rod to the tile holding its center; tiles share the rings exactly.
  The dresser hangs no strings, bunting or laundry within 1 m of a stretch, places the lanterns, and
  `Dresser.under_roofs` (in `build_tile`, after all placements got absolute heights, before the people)
  drops every piece whose kit box reaches into the roof (above the intrados inside the vault, above the fill
  bottom over the bands, below the roof top), except the roles in `lower` (wall lamps, shop awnings), which
  are lowered while their bottom stays that high. Quick capital: 351 m covered in 10 stretches (49 openings,
  50 arches, 28 lanterns), 38 pieces dropped (upper windows behind the vault, a laundry line, a cascade, an
  alley arch), 2 awnings lowered, 6 lantern strings left out; full capital 603 m (97 dropped, 1 lowered, 12
  strings left out). Costs: worst tile +6.0% quick, +6.8% full (about 26 triangles per meter of souk).
- **Massed buildings** (prompt 23, `city/massing.py`): the street windows, open-wall windows and slab
  windows of each column go up to the floors of the wall there (`floors_at` under the window's whole
  width, `[dressing] window_half` m each side), so none floats above a lower step or on a set-back
  terrace's edge; staircase windows stop below their part's roof. Walls of a set-back floor or of a
  villa's main part facing their terrace get windows on every floor above it (`terrace` stream).
  Props stand on the main roof (`main_mass`), off the stair room, menzah, machinery and a corner dome
  (`RoofLayout.rooms`); tank stands are the `tank_stand` piece (110 triangles) where massing put them.
  A door's climber and a span's height read the wall height there (`wall_height`).

- **Boats, cranes and cargo** (prompt 35, `mesh/boats.py`, `mesh/cranes.py`, `[port.props]`): category `boat`,
  `crane`, `rail` or `cargo`, plain palette colors without UVs (a tile pays for every vertex), each inside its
  envelope `[port.props] size`; random details on `stream(seed, "piece", name)`. A hull is a loft of 9 cross
  sections (keel, waterline, flared topsides to a sheer rising fore and aft), one shared-vertex smooth surface per
  painted band: `hull_antifoul` under the water, `hull_dark` (trawler) over it, `hull_white` topsides, a strake in
  `trims` color under the gunwale; the bulwark's inside and the gunwale cap close the thin shell. The three
  fishing boats (224-266 triangles) share one double-ended 7.2 m hull with a raked stem, its part dicts the same
  objects in every piece (the strake color only renamed), so a tile writes it once; each fit-out uses other
  materials: `boat_lateen` (scale 0.94-1.06: mast, lateen yard with the sail furled along it, thwarts, a painted
  eye each side of the bow), `boat_cabin` (1.04-1.16: cabin aft with dark windows and a mast light, a net heap),
  `boat_rowing` (0.72-0.84: thwarts, two oars, a net heap). `boat_trawler` (449 triangles, 16 m, scale 0.92-1.08:
  transom stern, wheelhouse with a window band, a mast with its lights, trawl winch, stern gantry, a foremast with
  topped booms, a net heap). Mast lights are `lantern_glow` (they glow at night). Origin on the waterline under
  the middle of the boat, the bow toward +x. `crane_0`, `crane_1` (484 triangles): portal of four plate legs on
  bogie beams straddling the rails, girders, slewing ring, machinery house with cab and counterweight, A-frame, a
  26 m tapering box lattice boom (8 bays) with luffing and hoist ropes and a hook block; `crane_1` slewed 24
  degrees and luffed to 62 instead of 50; origin on the quay at the portal's middle, the boom toward +y (the sea).
  `crane_rails` (12): two rails, one 12 m length. `cargo_crates` (70): two pallets of crates stacked 1-3 high.
  `cargo_containers_0..1` (234): three 20-foot containers with ribbed sides and door bars, two side by side and
  one on top, three colors each on its stream, sharing every part dict.

## 7. Style pack (`styles/<name>.toml`)

`[names]` sounds and templates, `[lore]` eras and products, `[palette]` materials (color and
optional `texture` + `texture_size`), `[textures]` generated-surface noise strengths, `[ground_tint]` the terrain `COLOR_0` tint,
`[plinth]` the base material and height per district kind, `[impasse]` lane rules and, per
district kind, width range, surface, `max_length`, `min_lot` and the covered share, `[streets]` curb height, minimum
carriageway, promenade width, the paint numbers and the outline
steps of drawn walks and paint (`walk_step`, `paint_step`: long pieces follow the ground),
`[streets.surface]` the ribbon material per street kind, `[roofs]` parapet thickness, height by
district kind and the stair room share and size, `[district.<kind>]` street
grid, sidewalk width, lot size, floors, materials and special rules,
`[settlement.<kind>]` population, density, old town size, which district kinds exist and the
`rings` mix by distance from the center. `[life]` door colors, family name patterns, real name
lists and the root sounds and word patterns for made-up nisba names, wealth and trades by
district; `[[souk]]` souk trades and their goods; `[covered_souk]` which souks are roofed and the
vault's measures; `[dressing]` chances and heights;
`[dressing.roles]` which piece plays each part; `[dressing.trees.<kind>]` the natural tree
variants (citrus with `fruit` oranges), `[dressing.hedge]` the villa hedges and garden lift,
`[dressing.vehicles]` the car body colors and `[dressing.parking]` the parking rule, gaps, car mix and
taxi rank,
`[greenery]` the street, courtyard and villa trees of prompt 24 and `[dressing.climber]` the bougainvillea curtains (clump count and size, drop,
stems, colors), `[dressing.people]` the figures and `[people]` where they go (density, gaps, one table per
place, `[people.seats]` the seats measured on the kit, `[people.outfits]` the mix by district). Adding a style = a new file; code must not assume
Maghreb-specific values.

## 8. Performance budgets

| Step | Budget |
|---|---|
| `pytest -q` | under 30 s (Ali's Mac today: about 13 s) |
| `build --quick` | under 90 s (Ali's Mac today: about 8 s) |
| country (64 km) | under 10 s |
| capital plan (about 60k buildings) | under 60 s |
| one tile | under 5 s, under 3 MB (target 3.5 MB for a dressed old-town tile; prompt 39: quick 4.7 MB, full capital 5.8 MB) |
| `build --area capital` (168 tiles) | Ali's Mac (M1, 4 fast + 4 slow cores) today: 73 s with `--workers 1`, 30 s with `--workers 8` (CP2) |
| lod1 tiles (prompt 40) | under 15% of their full tile's bytes; the lod pass about 3% of tile time (full capital +2.5 s) |
| the same build run again (nothing changed) | under 10% of the first run (today 1.5 s, plans, tiles, maps and data reused) |

## 9. Checking results cheaply

- `python -m citygen stats` prints `summary.json`; `stats --tiles` shows where each tile's bytes go.
- Maps: `output/*/maps/*.png` (look at the image, not the data files).
- 3D: `python -m citygen snapshot --view aerial|street|top` renders the viewer to a PNG.
- The viewer starts in **Fast** on phones and in the software snapshot browser, and in **High** on a
  computer (ambient occlusion and clean edges). Add `--query quality=high` to a snapshot to force
  High; add `?perf=1` to the viewer address to log the average frame time over 120 frames and the
  load times (every tile shown, settled). Snapshots wait for the viewer's settled state (all tiles at
  their level of detail, nothing in flight), so one build always gives one picture.
- `python tools/before_after.py --view street|souk|aerial` compares the last commit with the working
  tree in one labelled picture and prints the pixel difference (see HANDOFF.md).

**Checking a change.** `python tools/fingerprint.py save before` records a hash of every part
of the latest build (world, each plan section, each tile, each kit piece, maps, other files;
timings and build keys ignored) in `output/checks/fp-before.json`. After the edit and a new
build, `python tools/fingerprint.py compare before --allow "tiles/*,kit/tree_*"` lists each
changed part with a short detail and exits with code 1 when a part outside the patterns changed
(`--allow ""` allows nothing). Pass the build folder for builds outside `output/`, for example
`output/full/bodjantouna-42`.

## 10. Extending

- **New district kind:** add `[district.<kind>]` to the style, a branch in
  `city/buildings.make_buildings`, a color in `export/maps.py`, and put it in a settlement's
  `rings` mix or in `layout.assign_kinds`.
- **New building shape:** a function in `mesh/builder.py`, used from `mesh/tile.building_mesh`; a
  new massing feature: fields on `Building`, set in `city/massing.py`, drawn through `masses(b)`
  via a new `roof_shape` or field on `Building`.
- **New street piece:** a builder in `mesh/props.py` added to `catalog()`, or a `.glb` in a kit
  with a manifest entry; then name it in a role in `[dressing.roles]` (or place it from
  `city/dressing.py` for a new kind of spot). Check it with `python -m citygen kit-sheet`.
- **New props that stories need (boats, cars with owners):** add a list on `CityPlan`, fill it in
  the planner, and dress it from `city/dressing.py` with the same "center decides the tile" rule.
