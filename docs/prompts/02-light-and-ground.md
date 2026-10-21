# Prompts 7-16: light and ground

Read only the section of your prompt. `CLAUDE.md` gives the routine every prompt follows.
The quick capital has no villas, hip roofs or village streets: where a prompt needs them, build
`--area city:1` (Sazouches el Gharbi: villas, hip roofs, residential and suburb districts) or
`--area city:4` (the village Hirzabouane) through `before_after.py --build-args`.

## 7. Q3 - Bougainvillea that cascades, not lollipops

Model: Sonnet | Effort: medium | Size: S | Needs: 2 | Look: kit sheet

**Goal.** The generator's own climber (`bougainvillea` and `bougainvillea_b` in
`mesh/props.py`, used by the `climber` role in `[dressing.roles]`) looks like a lollipop next
to the Tounes kit's `tounes/bougainvillea_cascade`. Rebuild it as a dense, flat mass of bracts
spread against the wall, with a twisting woody trunk.

**Do.**
1. Read `bougainvillea` and how `Dresser._plant` (`city/dressing.py`) places climbers (anchor,
   `vine_height`, `cascade_height` in `[dressing]`).
2. New shape: a trunk of 2-3 bent, tapered 4-5 sided tubes rising from the ground or a pot;
   a canopy of 25-40 small flattened clumps that spreads sideways along the wall (x), hangs
   down from the top and hugs the wall (thin in y), in 3 magenta and pink shades plus a few
   green leaves; some clumps droop over a door or window top. Reuse the clump and tube helpers
   of `mesh/trees.py` (move shared helpers into one place rather than copying them). Two
   variants, up to about 250 triangles each.
3. Its own random stream for the shape, like `tree_pieces`: `catalog` passes its shared
   `props` stream to `bougainvillea` today, so stop drawing from it there (CLAUDE.md rules).
   Numbers in a `[dressing.climber]` style table, read through `kit.make_kit`.

**Check.** Fingerprint may change: `kit/bougainvillea,kit/bougainvillea_b,tiles/*`. Every other
`kit/*` part must stay identical. Look: `--kit-sheet --frame bougainvillea`.

**Done when.** The new climbers look like the same family as the Tounes cascade; no lollipop
shapes remain; tiles grow under 1%. Tick Q3.

## 8. V1 - Golden hour in the viewer

Model: Sonnet | Effort: high | Size: M | Needs: 2 | Look: street

**Goal.** The project's signature look: low warm sun, long soft shadows, hazy distance. Today
the viewer has one daylight look plus Night.

**Read.** `tools/viewer/index.html` (three.js 0.169 from jsdelivr through the import map):
`skyEnvironment`, `placeSun` (constant `SUN_DIR`, `LX`, `LY`), `updateClipAndFog`, `setShadows`,
`setNight`, `boot`; the existing `time` URL parameter; the sun of `tools/blender_beauty.py`
(azimuth 225 degrees, elevation 14 degrees).

**Do.**
1. A light menu: Noon, Golden hour, Night (Night is today's night mode). Golden hour is the
   default. URL parameter `light=noon|golden|night`; keep `time=night` working as an alias.
2. Golden hour: the sun of `blender_beauty.py` (azimuth 225, elevation 14 degrees) so viewer and
   Blender renders agree; warm sun color, cool sky fill from a HemisphereLight, sky gradient warm
   at the horizon, distance haze matched to the sky, ACES Filmic tone mapping with a tuned
   exposure.
3. Shadows at a low sun: recompute `SUN_DIR`, `LX`, `LY` per light mode; use an asymmetric
   shadow box (about +-700 m across the light, about +-150 m along the light's up axis) and
   snap per axis, so a 4096 map keeps shadow texels small on the ground; soft edges (PCFSoft),
   bias and normal bias tuned (no acne, no peter-panning).
4. Noon and Night keep their code paths unchanged.
5. Phones keep the existing lighter-shadow path; golden hour must not cost more than today.
6. The claude.ai phone page made by `tools/make_artifact.py` reuses the viewer: keep it working.

**Check.** Fingerprint: no change (`--allow ""`). Look: `--view street` (old default vs golden).
Noon unchanged: one extra `--query light=noon` run must print difference 0.0.

**Done when.** The street image has long warm shadows with crisp edges and haze, and still
reads clearly (no crushed blacks, no white sky); Noon and Night look as before.

## 9. V2 - Ambient occlusion and clean edges

Model: Sonnet | Effort: high | Size: S | Needs: 8 | Look: street

**Goal.** Soft contact darkening in corners, alleys, under awnings and trees, plus clean edges.
This is what makes a low-poly city look rich.

**Do.**
1. One post-processing chain in day modes: RenderPass, GTAOPass
   (`three/addons/postprocessing/GTAOPass.js`), SMAA or FXAA, OutputPass. Night keeps its bloom;
   switch passes by mode on one composer.
2. A Quality toggle (High/Fast) in the menu; Fast skips the whole chain (today's rendering).
   Default High on desktop, Fast on phones and in the snapshot browser (SwiftShader is slow);
   `quality=high` in the URL forces it.
3. Tune AO radius and strength for the 1.7 m street view and the aerial view; no dark halos
   around trees against the sky.
4. `?perf=1` logs the average frame time over 120 frames; AO must cost under +40% on desktop.

**Check.** Fingerprint: no change. Look: `--view street --query quality=high`. Fast unchanged:
one extra run without `quality=high` must print difference 0.0.

**Done when.** Contact shadows at wall bases, under awnings and in alleys, without halos; Fast
mode identical to before.

## 10. Q4 - Blender 5 haze and warm grade

Model: Sonnet | Effort: high | Size: S | Needs: 1 | Look: Blender render

**Goal.** `tools/blender_beauty.py` skips its compositor on Blender 5, because the compositor
became a node group (`scene.compositing_node_group`, a Group Output node instead of Composite).
Port `setup_haze` so Blender 5.2 renders get the warm grade and haze of 3.6 and 4.x renders.

**Do.**
1. Read `setup_haze` and the version checks in `tools/blender_beauty.py`. Blender 5.2 is at
   `/Applications/Blender.app/Contents/MacOS/Blender`.
2. On Blender 5: create a compositing node group, rebuild the same chain inside it (depth or
   mist haze, the warm color grade, glare if used) into its Group Output, and assign it to
   `scene.compositing_node_group`. Find nodes by type, never by name; read enum identifiers
   instead of hard-coding them; where a 5.x node lost a property, set the value through its
   input socket.
3. The 3.6 and 4.x paths stay unchanged (branch on `bpy.app.version`).
4. Render two small souk images with 5.2 (`--view souk --samples 16 --size 960x540`): one with
   the HEAD script (save it as `tools/_beauty_head.py` with `git show HEAD:tools/blender_beauty.py`,
   so its imports work, and delete it afterwards) and one with yours; stack them with labels into
   `output/checks/10.png` (Pillow). Blender may need to run outside the sandbox.

**Check.** Fingerprint: no change.

**Done when.** The new render shows the warm grade and depth haze, the old one does not, the
Blender log has no Python errors, and the diff only adds code behind the version check. Tick Q4.

## 11. A4a - City ground: smooth, gently terraced

Model: Sonnet | Effort: high | Size: M | Needs: 2 | Look: street

**Goal.** Inside a city the ground is graded like real streets: smooth along streets, gently
flattened under blocks, blending into natural terrain at the edge. Today everything drapes on
raw noise terrain (slopes of 8-10% around the capital), so roads dip below the ground and
building bases float or sink.

**Read.** `mesh/tile.py` (`TileContext.height`, `terrain_mesh`, `street_meshes`,
`building_mesh`), `mesh/builder.py` (`add_ribbon`), `city/model.py` (`CityPlan.blocks`).

**Do.**
1. New `citygen/city/ground.py` with `Ground(world, plans)` and a vectorized `height(x, y)`
   (numpy arrays in and out) that is a pure function of position, so tiles never show seams:
   - outside every city boundary: `terrain.height`;
   - inside: `blur` = mean of the terrain over a disc of `radius` meters (about 60; a fixed
     pattern of a center plus two rings of 8 samples). For speed, evaluate the blur on a
     world-aligned lattice (8 m) and interpolate bilinearly: still a pure function of position;
   - per block (`plan.blocks`), flatten only partly: `h = blur + clamp(terrace - blur,
     -terrace_max, +terrace_max)`, where `terrace` is the blurred height at the block's center
     and `terrace_max` is about 0.4 m, blended in over `edge` meters from the block edge
     (`edge` at least 2 x `terrain_step`). No terracing for park, cemetery, industrial and
     port blocks, nor for blocks larger than `terrace_max_area` (about 6000 m2). Full terraces
     do not work here: block edges sit 3-8 m above or below their centers;
   - at the city boundary, blend to natural terrain over `edge_band` meters (about 40) with
     smoothstep.
   Find each point's block with a shapely STRtree and vectorized `contains_xy`.
2. Numbers under `[ground]` in `citygen/defaults.toml` (radius, lattice, terrace_max, edge,
   terrace_max_area, edge_band).
3. `TileContext.height` uses `Ground.height`. That covers the terrain mesh, roads, streets and
   building bases. Street dressing still reads the raw terrain until prompt 12: some pots and
   doors may float or sink in between; that is expected.
4. Tests: equal heights on both sides of a tile edge; determinism; inside a terraced block's
   inset, heights deviate from the blur by at most `terrace_max`.
5. Measure: the extra cost per tile stays under 30% of the tile's build time.

**Check.** Fingerprint may change: `tiles/*`. Plans, world and kit must not. Look:
`--view street`.

**Done when.** Even streets and calm blocks in the street image, no seams in the viewer, tile
build time up by 30% at most.

## 12. A4b - Everything stands on what is drawn

Model: Sonnet | Effort: high | Size: M | Needs: 11 | Look: souk

**Goal.** Doors, pots, carts, lamps, gates and trees stand exactly on the surface you see:
the ground, or the street ribbon, which is drawn 0.18-0.34 m above the ground (`STREET_LIFT`).

**Do.**
1. `Ground.surface(x, y)`: the top of what is drawn there: `height + STREET_LIFT[kind]` on a
   street surface (the highest where streets overlap), `height` elsewhere. Prompt 13 adds the
   sidewalks to it.
2. Give `Dresser` the `Ground` (constructor). Ground pieces, doors, gates and street trees use
   `surface`; walls and wall pieces use `height` where they belong to a building. Replace every
   `self.world.terrain.height` in `city/dressing.py` (spans, gates, wall hits) and the terrain
   in `ground_heights` and `building_highs` (called from `mesh/tile.py`), plus
   `build.camera_views` and the index `focus` height.
3. Tests: (a) along every street of the quick capital, every 4 m, the terrain mesh as drawn
   (bilinear on the `terrain_step` grid) stays below the street ribbon top; (b) no wall foot
   floats: the drawn terrain sampled every 1 m along each footprint ring is never below the wall
   bottom, and every door threshold is within 0.05 m of `surface` 0.5 m in front of it; (c)
   dressing ground pieces stand within 0.05 m of `surface` (not `height`).
4. If a test fails for good reasons, tune `[ground]`; never weaken a test to make it pass.

**Check.** Fingerprint may change: `tiles/*`, `tiles/index`. Look: `--view souk`.

**Done when.** No floating or sunken doors, pots, carts or lamps in the souk image; tests pass.
Tick A4.

## 13. A3 - Sidewalks, curbs and the boulevard promenade

Model: Sonnet | Effort: high | Size: M | Needs: 12 | Look: street

**Goal.** Raised sidewalks with crisp curbs along the streets outside the old town, and a raised
central promenade under the boulevard's middle row of trees (today that row stands on asphalt).

**Read.** `CityPlan.blocks` (a block is its district minus the street surfaces); `street_building`
in `city/buildings.py` (houses stand only 0.15 m inside the block edge, so sidewalks cannot go
inside blocks); `STREET_LIFT` in `mesh/tile.py`; `street_trees` in `city/streets.py`.

**Do.**
1. Sidewalks lie in the street surface, along blocks of districts other than medina, village,
   park and cemetery: ring = `block.buffer(width, join_style="mitre")` minus the block, clipped to
   the street surfaces (`width` per district kind in the style, about 2.0-3.5 m). Narrow or skip
   it where less than 5.5 m of carriageway would remain. The street ribbon keeps its full width
   underneath. Store the sidewalk width per street side where later prompts can read it: the
   carriageway edge (street edge minus that side's sidewalk) is where markings (14), arcades (22),
   hedges (24) and parked cars (25) align.
2. Top = the street's top (ground + street lift) + curb height (0.15 m, style), with a vertical
   curb face; new palette materials `sidewalk` and `curb`.
3. Boulevards: a raised central promenade (width in the style, about 8 m, the same curb) under
   the center tree row.
4. Each sidewalk piece belongs to the tile containing its centroid, so nothing is drawn twice.
5. `Ground.surface` returns the sidewalk or promenade top where a point is on one, so doors,
   trees, lamps and props stand on it. Make door thresholds meet the sidewalk (raise the
   building base or let a plinth show; say what you chose and why).
6. Tests: sidewalk tops above the adjacent street tops wherever you sample; no sidewalk inside a
   building footprint; at least 5.5 m of carriageway everywhere a sidewalk exists.

**Check.** Fingerprint may change: `tiles/*`. Tile bytes +15% at most. Look: `--view street`.

**Done when.** Curbs, raised sidewalks and the boulevard promenade, with trees, lamps and doors
standing on them; no flicker between sidewalks and streets when the camera moves. Tick A3.

## 14. S1 - Street surfaces: asphalt, stone and earth, with markings

Model: Sonnet | Effort: medium | Size: M | Needs: 13 | Look: street

**Goal.** A street's surface tells its kind: asphalt with lane markings and zebra crossings on
boulevards and arterials, stone paving in the old town, packed earth in villages.

**Do.**
1. `street_meshes`: surface material per street kind from the style (a `[streets]` table);
   streets inside village districts use `earth` (new palette color).
2. Markings as thin ribbons 0.03 m above the street (`road_paint`, a slightly worn white; at
   0.01 m they flicker in aerial views): dashed center lines on arterials and connectors, lane
   and edge lines on boulevards (on each carriageway, beside the central promenade of prompt 13),
   edge lines along the carriageway edge (not the street edge), zebra crossings where boulevards
   and arterials meet other streets (intersect center lines with shapely; stripes just outside
   the junction). Only on streets wider than 8 m.
3. No randomness needed. Street pieces are clipped per tile like today.
4. Test: every marking lies inside its street's carriageway.

**Check.** Fingerprint may change: `tiles/*`. Look: `--view street`. Earth streets: check one
village with `python -m citygen snapshot` on a `--area city:4` build (your second picture if you
need it; then skip the before half).

**Done when.** Markings and crossings line up with the junctions; old town and village streets
keep plain surfaces.

## 15. A1 - Roof life: parapets and stair rooms

Model: Sonnet | Effort: medium | Size: S | Needs: 2 | Look: close aerial

**Goal.** Flat roofs look lived on: low parapet walls, and stair rooms (a small room with a
door) on a share of roofs. Tanks, dishes, laundry racks and pots already come with the
dressing.

**Do.**
1. Flat roofs get a parapet 0.6-1.0 m high (per district kind in the style), 0.2 m thick, with
   a top cap, along the outer ring and around courtyard holes, in `building_mesh`
   (`mesh/tile.py`). Reference: `add_parapet` in `tools/blender_beauty.py`.
2. A share of flat roofs (style; about 35% of houses, 60% of apartment blocks) get a stair room
   of about 2.5 x 2.5 x 2.4 m with a door facing the roof. Its position comes from one function,
   `roof_layout(b, rng)` on its own stream (for example `stream(seed, "roof", city id, k)`),
   used by both `building_mesh` and `Dresser._roof`, so tanks, dishes and laundry never overlap
   the stair room or stand outside the parapet.
3. `tools/blender_beauty.py` adds its own parapets: write `"parapets": true` in `tiles/index.json`
   and make the Blender scripts skip theirs when it is set (no double parapets).
4. Domes and minaret tops keep working.
5. Test: no roof prop inside a stair room or outside the parapet.

**Check.** Fingerprint may change: `tiles/*`, `tiles/index`. Tile triangles +25% at most. Look:
`--cam/--look` about 120 m above the old town, looking down at 45 degrees (the aerial preset is
too far to judge parapets).

**Done when.** Parapets and stair rooms are clear in the close aerial picture, nothing stands
inside a stair room, triangles within budget. Tick A1.

## 16. CP2 - Checkpoint: light and ground

Model: Opus | Effort: medium | Size: review | Needs: 7-15 | Look: street + souk (current state)

Follow the checkpoint routine of prompt 6 (`## 6.` in docs/prompts/01-foundations.md) for
prompts 7 to 15, comparing with the `cp1` fingerprint and images (pass
`output/bodjantouna-42`). Extra checks:
- Walk the viewer yourself in golden hour, noon and night (or two snapshots if you cannot open a
  window): seams between tiles, flicker between streets, sidewalks and terrain, floating pieces.
- Tile size and build time against SPEC section 8; the drawn-triangle count in `stats`.
- One ground: `Ground.height` and `Ground.surface` are used by every height reader (grep for
  `terrain.height` outside `terrain.py`, `world.py`, the planner and `ground.py`).
Save `fingerprint save cp2 output/bodjantouna-42` and `output/checks/cp2-*.png`. Fix prompts go
in `## 16.1. ...`.
