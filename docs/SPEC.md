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
  the street outline, where rounding can miss the street. Inside a city the natural terrain is
  sampled only in the edge band, where it has weight; deeper in, the height is the graded one.

## 4. Pipeline and modules

```
config.load_config()          defaults.toml + worlds/*.toml + CLI overrides
  world.generate_world()      terrain.Terrain, settlements, roads (whole country, seconds)
    city.plan_city()          one settlement -> CityPlan (seconds to a minute)
      layout                  land polygon, city limit, old town outline, neighborhoods, kinds
      medina                  great mosque, gates, souks, alleys (spanning tree), ramparts
      streets                 arterials (neighborhood borders), ring road, boulevard,
                              corniche, links to country roads, local grids, street trees
      parcels                 blocks = district minus street surfaces; recursive lot split
      impasses                dead-end lanes along lot lines to lots without a street door
                              (old town, village, residential, suburb); appended to the streets
      walks                   raised sidewalks along blocks and the boulevard promenade
      buildings               per-district building rules, mosques, parks, cemetery
      life                    a household behind every house door, a trade for every souk
  city.ground.Ground()        graded ground inside cities: smoothed, terraced under blocks,
                              blended into natural terrain at the city limit; `height` is the
                              ground, `surface` the top of the ground, street ribbon or walk
  mesh.tile.export_tile()     one 512 m square -> .glb (terrain, water, roads, city)
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
| `citygen/mesh/plants.py` | shared plant shapes: clumps (icosahedron, octahedron, 4-face bract) and tapered tubes |
| `citygen/mesh/props.py` | the generator's own kit pieces (doors, shops by trade, awnings, goods, lamps, trees...) |
| `citygen/mesh/trees.py` | broadleaf and olive crowns (jittered clumps, 3 variants each) from `[dressing.trees]` |
| `citygen/mesh/climbers.py` | bougainvillea curtains (2 variants, 250 triangles each) from `[dressing.climber]` |
| `citygen/kit.py` | `Kit`: procedural pieces plus kits from `kits/<name>/` |
| `citygen/city/life.py` | households and souk trades (story data that also drives the dressing) |
| `citygen/city/ground.py` | `Ground`: graded city ground (blurred, terraced, blended into the terrain), and `surface` for the top of ground, street ribbons and raised walks |
| `citygen/city/dressing.py` | `Dresser`: which piece goes where, tile by tile |
| `citygen/city/walks.py` | raised sidewalks along blocks, narrowed to keep a carriageway, and the boulevard promenade |
| `citygen/city/paint.py` | street surfaces per kind, painted edge and lane lines, zebra crossings |
| `citygen/city/impasses.py` | impasses: lanes cut along lot lines to landlocked lots, one round per lane for every block at once |
| `citygen/city/roofs.py` | roof layout: parapet band and coping, stair room and its door, one random stream per building |
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
- `CityPlan`: `boundary`, `land`, `medina`, `districts`, `streets`, `blocks`, `parcels`,
  `buildings`, `trees`, `landmarks`, `walks`, `households`, `souks`, `paint`, `stats`.
- `Walk(kind, polygon, width, street, side, district, block)`: a raised sidewalk (`sidewalk`)
  or the boulevard's central promenade (`promenade`). `width` is the actual width after a tight
  street narrows it; `street` and `side` (`+1` left, `-1` right) let later street features find
  the carriageway edge.
- `Paint(polygon, street)`: one painted marking, a flat polygon over the carriageway of a street.
  `make_paint` builds edge and lane lines, dashes and zebra crossings once per plan; a tile only
  clips the polygons it touches.
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

Invariants (tested): buildings are valid polygons inside the city and stay off street surfaces
(impasses included); every old-town dwelling's main door opens on a street, alley or impasse; an
impasse lies inside its block past its mouth, opens on exactly one street (or branches off exactly
one impasse) and touches no other street, so it is a dead end;
flat roofs carry the parapet from `[roofs]` and, where the layout puts one, a stair room whose
door opens on free roof; roof props always stand inside the parapet and outside the stair room;
sidewalks never enter a building footprint, keep at least `min_carriageway` meters of asphalt,
and stand `curb_height` above the street ribbon; every road marking lies inside its street's
carriageway; everything is deterministic.

## 6. Output files (`output/<country>-<seed>/`)

| File | Content |
|---|---|
| `world.json` | `citygen-world/1`: seed, name, size, settlements, roads (coords in meters) |
| `cities/<name>/plan.json` | `citygen-city/1`: districts, streets, buildings, trees, landmarks, households, souks; GeoJSON-style geometry in world meters |
| `gazetteer.md` | readable guide for stories |
| `maps/country.png`, `maps/<city>.png` | 2D maps, north up |
| `tiles/tile_<i>_<j>.glb` | 3D tile covering x `i*512..(i+1)*512`, y `j*512..(j+1)*512` |
| `tiles/textures/*.png` | base-color images shared by the tiles (`[tiles] textures = "shared"`, the default) |
| `tiles/index.json` | `citygen-tiles/1`: tile list (bytes, unique and drawn triangles, dressing pieces), `"parapets": true` when the tiles carry their own roof parapets, `focus` point, camera `views`, `cities` (name, plan file, bounds) |
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
- **Roles** (`[dressing.roles]` in the style): a role (`door_blue_rich`, `lamp`, `souk_awning`,
  `tree_palm`...) lists `[piece, weight]` or `[piece, weight, extra height]`; missing pieces are
  skipped and a role with no entry uses the piece of the same name, so the city dresses itself
  without any kit. Chances and heights are in `[dressing]`; souk goods in `[[souk]]`.
- **Dresser** (`city/dressing.py`): per building (one random stream each) the main facade gets a
  shop (souks), a cafe (colonial) or a door with lamp, hood, pots, bench, cat, climber, parked
  moped; other walls get windows by floor (grilles, shutters, birdcage bays, one mashrabiya
  balcony for rich households); flat roofs get tanks, dishes, laundry racks and pots inside the
  parapet and off the stair room. Per street:
  laundry, cables, lantern strings, bunting and sabats across alleys and souks, arches over alley
  mouths, gates and handcarts in souks, lamps along main streets. Impasses are dressed like alleys
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
  one side (yaw) of the building; in a modern block one half of one stair's section (sections as
  `stair_spacing` spaces the stairs). Staircases (`window_stair`, `stair_door`) draw once per section
  with their own chance `stair`. Chance per flat: `base + member x (members - members_ref) + wealth x
  (wealth - 0.5) + trades[trade] + district[kind]`, plus `couple` for two-person households, within
  `range`. A lit piece becomes its twin; a kit window keeps its piece and gets its pane right after
  it. Quick capital: 40% of housing windows lit (medina 34%, colonial 39%, modern 41%). The glTF
  writer reuses the accessors of a part drawn twice, so a twin costs one mesh entry, not a copy.

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
district; `[[souk]]` souk trades and their goods; `[dressing]` chances and heights;
`[dressing.roles]` which piece plays each part; `[dressing.trees.<kind>]` the natural tree
variants and `[dressing.climber]` the bougainvillea curtains (clump count and size, drop,
stems, colors). Adding a style = a new file; code must not assume
Maghreb-specific values.

## 8. Performance budgets

| Step | Budget |
|---|---|
| `pytest -q` | under 30 s (Ali's Mac today: about 13 s) |
| `build --quick` | under 90 s (Ali's Mac today: about 8 s) |
| country (64 km) | under 10 s |
| capital plan (about 60k buildings) | under 60 s |
| one tile | under 5 s, under 3 MB (under 5 MB for a dressed old-town tile) |
| `build --area capital` (168 tiles) | Ali's Mac (M1, 4 fast + 4 slow cores) today: 73 s with `--workers 1`, 30 s with `--workers 8` (CP2) |
| the same build run again (nothing changed) | under 10% of the first run (today 1.5 s, plans, tiles, maps and data reused) |

## 9. Checking results cheaply

- `python -m citygen stats` prints `summary.json`.
- Maps: `output/*/maps/*.png` (look at the image, not the data files).
- 3D: `python -m citygen snapshot --view aerial|street|top` renders the viewer to a PNG.
- The viewer starts in **Fast** on phones and in the software snapshot browser, and in **High** on a
  computer (ambient occlusion and clean edges). Add `--query quality=high` to a snapshot to force
  High; add `?perf=1` to the viewer address to log the average frame time over 120 frames.
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
- **New building shape:** a function in `mesh/builder.py`, used from `mesh/tile.building_mesh`
  via a new `roof_shape` or field on `Building`.
- **New street piece:** a builder in `mesh/props.py` added to `catalog()`, or a `.glb` in a kit
  with a manifest entry; then name it in a role in `[dressing.roles]` (or place it from
  `city/dressing.py` for a new kind of spot). Check it with `python -m citygen kit-sheet`.
- **New props that stories need (boats, cars with owners):** add a list on `CityPlan`, fill it in
  the planner, and dress it from `city/dressing.py` with the same "center decides the tile" rule.
