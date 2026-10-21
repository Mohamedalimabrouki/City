# Prompts 70-78: game-ready

Read only the section of your prompt. `CLAUDE.md` gives the routine every prompt follows.
Godot and Unreal are not installed on Ali's Mac. Before relying on one, ask Ali whether to
install it (Godot 4 is a free download of about 100 MB from godotengine.org; Unreal is large
and needs an Epic account). Without the engine, write small, careful code against the official
documentation of the exact version, and list in your report what Ali must check by hand.

## 70. C4a - Street graph for games

Model: Sonnet | Effort: medium | Size: M | Needs: 12 | Look: no

**Do.** Export `cities/<name>/streets.json` (`citygen-streets/1`): nodes (junctions and dead
ends, with x, y and z = the drawn street top, `Ground.surface`), edges (street segments: kind,
width, sidewalk widths, length, surface, node ids, polyline), and links to the country roads.
Build it from `plan.streets` by noding the center lines after `shapely.set_precision(line,
0.05)` (plain `unary_union` misses junctions where grid streets end on district borders only up
to rounding). Document the format in SPEC section 6.

**Check.** Fingerprint may change: `files/cities/*/streets.json` (new). Tests: the largest
connected component holds at least 99.5% of the street length; every edge's ends are nodes;
lengths match the geometry.

**Done when.** The graph of the capital is connected and valid.

## 71. C4b - Building entrances

Model: Sonnet | Effort: medium | Size: S | Needs: 70, 20.2 | Look: no

**Do.** One entrance per building that has a door: the main door from `door_spot(k)` (prompt
20.1, the same function the dressing uses), linked to the nearest street edge of the graph (edge
id and distance along it); households reference their entrance. Export in `streets.json` (or a
sibling `entrances.json`).

**Check.** Fingerprint may change: `files/cities/*/*.json`, `plan/*/households`. Tests: each
door lies within width/2 + sidewalk + 3 m of its edge's center line and equals the dressing's
door; every dwelling has an entrance.

**Done when.** Entrances exist for every dwelling. Tick C4.

## 72. C3a - Godot 4: stream the city

Model: Sonnet | Effort: high | Size: M | Needs: 40 | Look: Ali

**Do.**
1. `engine/godot/` (Godot 4.3 or newer): a scene that reads `tiles/index.json` from a chosen
   build folder, loads tiles near the player at runtime with `GLTFDocument`/`GLTFState`
   (lod1 far, full tiles near), and frees far ones. Godot uses single-precision floats: shift
   every tile by the focus point, as the web viewer does, so the city does not jitter 30 km from
   the origin.
2. Instancing: Godot's glTF importer may ignore `EXT_mesh_gpu_instancing`. Check the docs for
   the version you target; if it is not supported, add a `GLTFDocumentExtension` in GDScript
   that reads the extension into `MultiMeshInstance3D` nodes, decoding each accessor's component
   type and `normalized` flag (prompt 39 packs rotations as int16).
3. Textures in shared mode load from `tiles/textures/` with `KHR_texture_transform`; quantized
   meshes must load (check `KHR_mesh_quantization` support; if missing, document a build setting
   that turns quantization off for Godot exports).
4. If Ali installs Godot, check headlessly: `godot --headless --path engine/godot --script
   res://tools/check.gd` printing tile, mesh and MultiMesh instance counts.

**Done when.** Opening the project and pressing Play shows the city around the focus point
(Ali checks it if Godot is not installed here).

## 73. C3b - Godot: walk the streets

Model: Sonnet | Effort: high | Size: M | Needs: 72 | Look: Ali

**Do.** A first-person walker with collision (collision shapes generated from terrain and
building meshes when a tile loads, simplified where cheap), walking and running speeds, jump,
spawn at the `street` camera point of the index.

**Done when.** You can walk down the boulevard and into an alley without falling through or
getting stuck (Ali checks it if Godot is not installed here).

## 74. C3c - Godot: sky, light, night and a guide

Model: Sonnet | Effort: medium | Size: S | Needs: 73 | Look: Ali

**Do.** A golden-hour sky and sun with shadows and fog (the sun of prompt 8), a night toggle
where emissive materials (lamps) glow and `glass_lit` windows light up, and
`engine/godot/README.md` in plain language (install Godot, choose a build folder, play,
controls).

**Done when.** The README alone is enough for Ali to walk the city in golden hour and at night.
Tick C3.

## 75. C5 - Unreal 5 import

Model: Sonnet | Effort: high | Size: M | Needs: 39 | Look: Ali

**Do.** `engine/unreal/import_city.py`, an Unreal Editor Python script: import tiles through the
Interchange glTF importer into a World Partition level, place each tile at its root
translation, and rebuild instanced dressing as Instanced Static Mesh components by reading
`EXT_mesh_gpu_instancing` from the .glb yourself if the importer ignores it. Derive the
glTF-to-Unreal transform from one imported tile (a known door node compared with its imported
actor) and apply exactly that to the instances, or the dressing comes out mirrored or turned.
A plain-language `engine/unreal/README.md`.

**Done when.** The script and guide are complete and consistent with Unreal 5.4+ documentation;
the report lists exactly what Ali must check in Unreal, starting with the axis check. Tick C5.

## 76. C6a - Tounes Rush: city run routes

Model: Sonnet | Effort: high | Size: M | Needs: 70 | Look: Ali

**Do.**
1. Ask Ali for the Tounes Rush game (the claude.ai artifact "Tounes Rush AAA V5.2": its link, or
   the file). Read how a run's level is defined (lanes, segments, obstacles, buildings along it).
2. Propose a JSON format in one paragraph in your WORKLOG entry and docs/SPEC.md, then export
   `cities/<name>/runs/*.json`: chains of souks and streets from the street graph, the buildings
   along each side, obstacles from the dressing (carts, stalls, sabats as overhead obstacles),
   with a `python -m citygen runs CITY` command.
3. Tests: runs are continuous along graph edges and deterministic (two processes, CLAUDE.md).

**Check.** Fingerprint may change: `files/cities/*/runs/*` only.

**Done when.** Ali loads one exported run in the game (he checks).

## 77. C6b - The country map unlocks towns

Model: Sonnet | Effort: medium | Size: S | Needs: 76 | Look: Ali

**Do.** Export `runs/country.json`: towns that have runs, their positions on a simplified country
map image, and an unlock order by distance from the capital; a short doc for the game side.

**Check.** Fingerprint may change: `files/runs/*` only.

**Done when.** The file and doc are ready for the game. Tick C6.

## 78. CP7 - Checkpoint: game-ready

Model: Opus | Effort: medium | Size: review | Needs: 70-77 | Look: no

Follow the checkpoint routine of prompt 6 (`## 6.` in docs/prompts/01-foundations.md) for
prompts 70 to 77, comparing with `cp6` (pass `output/bodjantouna-42`). Extra checks:
- The JSON formats are documented in SPEC section 6, versioned (`citygen-.../1`) and stable.
- The Godot and Unreal guides are followable by a newcomer; list what still needs a test in the
  real engines.
Save `fingerprint save cp7 output/bodjantouna-42`. Fix prompts go in `## 78.1. ...`.
