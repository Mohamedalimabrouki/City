# Prompts 17-27: facades and street life

Read only the section of your prompt. `CLAUDE.md` gives the routine every prompt follows.
Prompts 20.1 and 20.2 were added after review: run them after 20 and before 21.

## 17. A2a - Textures in the 3D files

Model: Sonnet | Effort: high | Size: M | Needs: 1 | Look: no

**Goal.** The .glb writer can give a material a base-color texture: the foundation for textured
walls, roofs and ground (prompts 18-20).

**Read.** `mesh/gltf.py` (`_material`, `write_glb`, `read_parts`), SPEC sections 2 and 6 (UVs
are meters, and `tools/blender_beauty.py` relies on that: `bake_wall_uvs` and its shaders),
`tools/make_artifact.py` (the phone page parses tiles from base64 with `parseAsync`),
`shared()` in `tools/viewer/index.html`.

**Do.**
1. A palette entry may carry `texture = "<name>"` and `texture_size = [w, h]` (meters covered by
   one repeat). UVs stay in meters: the writer adds `KHR_texture_transform` with scale
   `[1/w, 1/h]` on the `baseColorTexture` (three.js 0.169 and Blender's importer read it), plus
   `images`, `textures` and a REPEAT sampler with mipmaps. The palette color multiplies the
   texture, so textures are neutral detail around white (prompt 18).
2. `[tiles] textures` in defaults: `"shared"` (default: each image written once per build into
   `tiles/textures/` by the parent process before any tile, so parallel workers never race, and
   referenced by a relative URI), `"embedded"` (inside each .glb, for single-file exports such
   as hero scenes), `"off"` (today's flat colors). PNG or JPEG. Images come from a provider
   function; prompt 18 fills it, so ship one simple test texture for now.
3. `read_glb` and `read_parts` keep working. The viewer's material cache must key on the
   texture too. A tile counts as finished for resume (prompt 5) only when its textures exist.
4. The phone page: `make_artifact.py` stores each image once as base64 JSON, and the page maps
   `textures/<name>` to blob URLs with `loader.manager.setURLModifier`. Test the page with
   `python -m http.server` inside the artifact folder (`citygen view` serves the normal viewer,
   not the artifact).
5. Tests: a textured part round-trips (valid image inside an embedded .glb; the URI exists in
   shared mode); image, sampler, texture and extension entries are valid glTF.

**Check.** With `textures = "off"`, fingerprint shows no change. With the test texture on one
material, the viewer shows it, and a headless Blender 5.2 import (`tools/blender_import.py`,
checked by a small script) gives that material an Image Texture node with the right mapping.

**Done when.** Tests pass, the viewer, Blender and the phone page (local server) show the test
texture.

## 18. A2b - Generated textures: plaster, stone, tiles, paving

Model: Sonnet | Effort: high | Size: M | Needs: 17 | Look: texture sheet

**Goal.** Small seamless images, made by code, that give surfaces material: plaster, cut stone,
render, concrete panels, roof tiles, flat-roof plaster, paving stones, asphalt, packed earth,
sand, grass.

**Do.**
1. New `citygen/mesh/textures.py`: `texture(name, seed) -> PIL.Image`, 256 or 512 px square,
   seamless (noise that wraps), realistic detail as near-neutral grey around white: fine grain,
   soft stains near the bottom, slight variation. The palette color tints it in glTF (color x
   texture), so one plaster texture serves every wall color; never bake palette colors in.
2. Never paint windows or doors on walls: the 3D pieces of the dressing do that. Floor bands
   (cornice lines) only on materials used by one floor height (wall materials are shared by
   districts with different floor heights): for example a new colonial-only `render_cream`
   whose texture height equals the colonial floor height; otherwise no bands.
3. `python -m citygen texture-sheet` writes `output/checks/texture-sheet.png`: every texture
   tiled 2 x 2, tinted by its palette colors, with its name.
4. Each texture on its own stream (`stream(seed, "texture", name)`); sizes and noise strengths in
   a `[textures]` table of the style. JPEG where it compresses better.
5. Tests: deterministic bytes; seamless (left and right columns, top and bottom rows match
   closely); sizes.

**Look.** The texture sheet is your picture for this prompt (no browser needed). Judge each
texture as a game artist would for a low-poly city; rework the weak ones once.

**Check.** Fingerprint: no change (textures are not used yet).

**Done when.** The sheet looks clean and realistic; tests pass.

## 19. A2c - Textured walls and roofs

Model: Sonnet | Effort: high | Size: M | Needs: 18 | Look: street

**Do.**
1. Map wall and roof materials to textures in the palette (`texture`, `texture_size`): plaster
   for plaster walls, `render_cream` for colonial walls, concrete for modern slabs, roof tiles
   for hip roofs, plaster for flat roofs, stone for ramparts and gates.
2. Walls: v = 0 at the ground floor (check `z_ref` in `add_walls`), so bands line up along a
   street. A plinth: the bottom 0.6-1.0 m of walls (per district kind in the style; a blue-grey
   band in the medina) as its own material, by splitting `add_walls` at that height.
3. Hip roofs: `add_hip_roof` gets planar meter UVs (u along the eave, v up the slope); today
   `add_triangles` gives (x + y, -z), which smears tiles into stripes.
4. Budgets: all shared textures under 2 MB per build; tile bytes +10% at most.
5. Viewer: textures stay sharp at street level (anisotropy 8 where available, mipmaps); the
   phone page stays fast.

**Check.** Fingerprint may change: `tiles/*`, `files/tiles/textures/*`. Look: `--view street`;
hip roofs exist only outside the quick capital: check them with `python -m citygen snapshot`
on a `--area city:1` build (your second picture; skip the before half).

**Done when.** Plaster grain, aligned bands and plinths; roof tiles running down the slopes; no
stretched or swimming textures; budgets met.

## 20. A2d - Ground textures

Model: Sonnet | Effort: medium | Size: S | Needs: 19 | Look: street

**Do.** Texture the terrain materials (`beach`, `desert`, `steppe`, `grass`, `forest`, `rock`,
`urban_ground`; see `BIOME_MATERIAL` in `mesh/tile.py`), the streets (asphalt, paving, earth
from prompt 14) and sidewalks and curbs (prompt 13). Choose `texture_size` so repeats do not
show at street level. Against repeats from the air, add a large-scale tint as `COLOR_0` vertex
colors on the terrain, and add vertex colors to the viewer's `shared()` material key (without
it, materials with and without vertex colors get mixed up and can render black). Road markings
stay flat colors.

**Check.** Fingerprint may change: `tiles/*`, `files/tiles/textures/*`. Budgets of prompt 19
still met. Look: `--view street`.

**Done when.** The ground reads as material up close and shows no obvious tiling at 50-200 m.
Tick A2.

## 20.1. AD1 - Every home gets a door and windows

Model: Sonnet | Effort: high | Size: M | Needs: 13 | Look: aerial over a modern estate

**Goal.** Today `Dresser.facades` (`city/dressing.py`) keeps only walls with a street surface
within 1.6 m, so every modern slab (set back 6 m) and about 40% of medina houses get no door and
no windows at all, and colonial and souk houses get a shop or cafe but no door to the homes
above. Interiors (44), entrances (71) and addresses (79) need a door for every dwelling.

**Do.**
1. Walls that face open ground (no building within 3 m) also count as facades for windows, with
   window rules per district kind (slabs: regular windows on every floor, balconies on a share).
2. Every dwelling gets a main door: on a street facade as today; otherwise on the wall facing
   the nearest street or open ground. Apartment slabs get a stair door every 20-25 m on the long
   side facing the nearest street, with a paved path (a thin paving ribbon) to the street.
3. A shop or cafe front keeps a narrow house or stair door beside it for the homes above.
4. Own streams for every new choice (CLAUDE.md rules), so walls that were already dressed keep
   exactly their pieces; one shared function `door_spot(k)` returns each building's main door, for
   prompts 44 and 71.
5. Tests: every dwelling has a door; every slab has windows on each floor; already-dressed
   street facades are unchanged.

**Check.** Fingerprint may change: `tiles/*`. Tile bytes +20% at most. Look: `--cam/--look`
over a modern estate of the quick capital (about 150 m away, 30 degrees down).

**Done when.** Modern slabs have windows, entrances and paths; colonial shops have house doors
beside them.

## 20.2. AD2 - Impasses to landlocked houses

Model: Sonnet | Effort: high | Size: M | Needs: 20.1 | Look: souk

**Goal.** Medina lots without street frontage are real (houses deep inside a block), but in a
real medina they are reached by a dead-end alley (impasse, driba). Give them one.

**Do.**
1. In the planner (`city/parcels.py` or `city/medina.py`, before buildings are made): for each
   landlocked lot in medina and village blocks, cut a 2-3 m impasse from the nearest street or
   alley, sharing it between neighbors where possible, as a new `Street(kind="impasse")`; the
   lots it reaches get frontage. Some impasses are covered for a few meters (a sabat-like room
   over the entrance).
2. Draw impasses like alleys (paving, alley lift); the dressing treats them like alleys; maps show
   them.
3. Own stream (`ctx.rng("impasse", block)`); numbers in the style.
4. Tests: every medina house has frontage on a street or impasse; buildings stay off streets.

**Check.** Fingerprint may change: `plan/*` (streets, parcels, buildings and so households
change: record it), `tiles/*`, `maps/*`, `gazetteer`. Look: `--view souk`.

**Done when.** No medina house without a way in; the city map shows a believable web of
impasses.

## 21. A9 - Lit windows by household

Model: Sonnet | Effort: medium | Size: S | Needs: 8, 20.1 | Look: street at night

**Goal.** At night today every generator window glows and every kit window stays dark. Make a
believable mix decided by who lives there.

**Do.**
1. Palette: `glass_lit` with the same color as `glass_dark` and no emissive (an emissive in the
   .glb would glow by day in the viewer and in Blender); the viewer's night code lights
   `glass_lit` only, as it lights lamps today.
2. Decide lit or dark on its own stream (`self.rng("lit", k, facade, floor)`), never on
   `rng("b", k)`: pick the window piece exactly as today, then swap it for its `_lit` twin, so
   the day look stays identical. Chance from the household (more members, bakers and students up
   late, older couples early, wealth), numbers in `[dressing]`; non-housing buildings mostly
   dark; in apartment blocks a whole flat (same floor, same side) together.
3. Tounes kit windows are single vertex-colored meshes, so `materials_map` cannot light only the
   glass: for each kit window add a lit pane piece (a `glass_lit` quad sized to the window, just
   behind its face) placed with it when lit.
4. Test: the lit share of housing windows is between 25% and 50% on the quick capital.

**Check.** Fingerprint may change: `tiles/*`, and only new `kit/*_lit` parts. Look:
`--view street --query light=night`. Day unchanged: one extra day run must print difference 0.0.

**Done when.** The night image shows a believable mix, whole flats together, more in dense
quarters; the day look is unchanged. Tick A9.

## 22. AR1 - Colonial arcades and iron balconies

Model: Sonnet | Effort: high | Size: M | Needs: 13 | Look: street

**Goal.** The boulevard looks like the ville nouvelle of Tunis: ground-floor arcades (arches on
pillars with a covered walkway behind) and wrought-iron balconies on the upper floors.

**Do.**
1. New pieces (own streams): `arcade_bay` (one arch on two half-pillars, 3.5-4 m wide, cornice
   above; anchored on the wall face at street level; the walkway depth is part of the piece),
   `balcony_iron` (slab and a rail of thin bars with a simple scroll pattern, about 1.2 x 0.6 m,
   anchored at the window sill) and `balcony_iron_long` (across two windows).
2. Arcades on every colonial facade that faces a boulevard, arterial or ring (do not rely on
   `FRONT_PREF`, which ranks streets above boulevards), wrapping round corners; shops and cafes
   sit behind the arches, set back by the walkway depth. One shared rule moves or skips street
   lamps along arcaded stretches (lamps stand 0.6 m inside the street edge).
3. Upper floors get balconies on a share of windows (style chances, more for rich households),
   decided on their own stream.
4. Instances only; numbers in the style; roles in `[dressing.roles]`.
5. Test: no arcade bay overlaps a door, shop piece or lamp.

**Check.** Fingerprint may change: `kit/arcade_bay,kit/balcony_iron,kit/balcony_iron_long,
tiles/*`. Tile bytes +15% at most. Look: `--view street`.

**Done when.** Continuous arcades along the boulevard, round the corners, with balconies above.

## 23. AR2 - Building massing with character

Model: Sonnet | Effort: high | Size: M | Needs: 15 | Look: close aerial

**Goal.** Fewer identical boxes: rooflines step, corners turn, top floors step back.

**Read.** `city/buildings.py` (`street_building`, `slab`, `villa`, `courtyard_house`,
`make_buildings`), `city/model.py` (`Building`), `mesh/tile.py` (`building_mesh`), the roof
code of prompt 15 (`roof_layout`, parapets), `Dresser._roof` and `_windows`.

**Do.**
1. Never add or remove buildings: express every change as fields on `Building` that
   `building_mesh` draws.
2. Colonial: corner buildings at junctions get a chamfered or rounded corner (polygon edit) and
   sometimes a corner dome or turret (give `top` a position instead of the footprint center);
   rows vary by one floor up or down; a share get a set-back top floor (new `Building.setback`).
3. Modern: slabs step in height along their length (new `Building.steps`: two or three parts
   with their own floor counts) and get roof machinery boxes.
4. Villas: a hip roof part plus a flat terrace part (L-shaped mass).
5. Medina: a few courtyard houses get a small roof room (menzah).
6. Update `_roof`, `roof_layout`, the parapets and `_windows` for the new parts: tanks on the
   right roof level, windows on the right walls, no prop inside a turret.
7. Every choice on its own stream path (for example `ctx.rng("massing", k)`); numbers in
   `[district.<kind>]`.

**Check.** Fingerprint may change: `plan/*/buildings`, `tiles/*`, `maps/*`. Households, souks,
streets and trees must not change. Look: `--cam/--look` about 150 m over a colonial corner; the
villas exist only outside the quick capital: check one with a `--area city:1` snapshot.

**Done when.** Varied rooflines and corner treatments; roof props on the right levels; building
count and households unchanged; the polygon tests pass.

## 24. A7 - More greenery

Model: Sonnet | Effort: medium | Size: S | Needs: 13 | Look: aerial

**Do.**
1. Street trees along arterials in colonial and modern districts, on the sidewalk next to the
   carriageway edge, on their own stream (`ctx.rng("street-trees", "arterial", k)`):
   `street_trees` uses one sequential stream today, so adding trees inside it would change the
   existing ones.
2. Villa lots: garden ground (a `garden` terrain color inside villa parcels, outside the house)
   and low box hedges along lot edges (an instanced `hedge` piece); `garden_trees` already
   exists, keep it.
3. Courtyards: check what `courtyard_tree_chance` already does and extend it on its own stream
   (`ctx.rng("courtyard-trees", k)`). Citrus is not a tree kind yet: add it properly (style
   table, role, map color, a variant of the crown code of Q1) or leave it out.

**Check.** Fingerprint may change: `plan/*/trees,plan/*/stats,gazetteer,tiles/*,maps/*,
kit/hedge`, plus `kit/tree_citrus*` if you add it. Build time +15% at most. Look:
`--view aerial`; villa gardens with a `--area city:1` snapshot.

**Done when.** Tree-lined arterials, green villa gardens and courtyard trees; existing trees
unchanged; time within budget. Tick A7.

## 25. H3a - Parked cars and taxis

Model: Sonnet | Effort: medium | Size: M | Needs: 13 | Look: street

**Goal.** Colonial and modern streets have cars parked along the curb; yellow taxis wait on the
boulevard.

**Do.**
1. Pieces in a new `mesh/vehicles.py` (own streams): a small hatchback, a sedan, a van, a white
   louage minibus with a colored stripe, and a yellow taxi; low-poly (150-350 triangles),
   simple prism wheels, dark glass; 4 muted body colors per type from the style (instancing
   cannot recolor a piece, so each color is its own piece; each tile stores only those it uses).
2. Placement in `Dresser.street_props` on its own stream per street: kinds street, arterial and
   boulevard in colonial, modern and residential districts, both sides, parallel, against the
   carriageway edge (prompt 13); gaps at junctions, crossings, shop fronts and trees; spacing
   and chances in the style; a taxi rank near the boulevard's busiest point.
3. A car belongs to the tile containing its center.
4. Test: no car within 1 m of a tree, a crossing or a junction, and none on a sidewalk.

**Check.** Fingerprint may change: `tiles/*` and the new `kit/car_*` parts only. Drawn triangles
+20% and tile bytes +10% at most. Look: `--view street`.

**Done when.** Believable parked rows with gaps; nothing on crossings, in junctions or in trees.

## 26. H3b - Benches, kiosks and fountains

Model: Sonnet | Effort: medium | Size: M | Needs: 13 | Look: street

**Do.**
1. Benches on the boulevard's central promenade (prompt 13) between the trees, facing the
   walkway (role with `tounes/bench_sbs` and a new generator `bench_iron`). Corniche benches come
   with the promenade of prompt 36.
2. A newspaper and tobacco `kiosk` (small booth with an awning) at a few boulevard junctions.
3. Fountains: a round `fountain_colonial` (basin and central column) where the boulevard meets
   the ring road or at its end; a tiled wall fountain `sabil` near the great mosque or a medina
   gate. Fountain water uses a new `water_pool` palette material (never `water`, which the
   Blender scripts hide because they draw their own sea): the viewer's `/^water/` rule already
   gives it the water look; give it a water shader in `tools/blender_beauty.py`.
4. Rules in `Dresser.street_props` or a small per-city "squares" pass, on their own streams;
   chances in the style; tile-local.

**Check.** Fingerprint may change: `tiles/*` and the new `kit/bench_iron,kit/kiosk,
kit/fountain_colonial,kit/sabil` parts. Tile bytes +5% at most. Look: `--view street`.

**Done when.** Benches and a kiosk show on the boulevard; your report says where the fountains
can be seen (they may be outside the street camera).

## 27. CP3 - Checkpoint: facades and street life

Model: Opus | Effort: medium | Size: review | Needs: 17-26 | Look: street + souk (current state)

Follow the checkpoint routine of prompt 6 (`## 6.` in docs/prompts/01-foundations.md) for
prompts 17 to 26 (with 20.1 and 20.2), comparing with `cp2` (pass `output/bodjantouna-42`).
Extra checks:
- Textures: total size, sharpness at street level, no visible tiling, the phone page (local
  server) and a Blender import still work.
- Doors and windows: every dwelling has a door; modern slabs have windows; impasses reach every
  landlocked house.
- Street life density: walk a boulevard, a souk and a modern street; nothing overlaps (cars in
  trees, benches in doors, arcades through lamps).
- Drawn triangles and tile bytes against the budgets; the viewer stays smooth.
Save `fingerprint save cp3 output/bodjantouna-42` and `output/checks/cp3-*.png`. New fix prompts
go in sections `## 27.1. ...`.
