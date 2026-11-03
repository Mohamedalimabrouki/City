# Godot 4 starter: stream the city

This folder is a small Godot 4 project (Godot 4.3 or newer, the free "Standard" version, not .NET).
It shows a city built by the generator and loads the pieces of the city near the camera while
you move.

## Try it

1. Build a city first (from the repository folder): `.venv/bin/python -m citygen build --quick`.
2. Open Godot, click **Import**, pick `engine/godot/project.godot`, then **Import & Edit**.
3. Press **Play** (F5 or the triangle at the top right).

The camera starts at the street view of the capital. Hold the **right mouse button** and move the
mouse to look around; **W A S D** move, **Q / E** go down / up, hold **Shift** to go faster.

By default the project shows the newest build in the repository's `output/` folder (quick or full).
To choose one, select the `City` node and type the folder in **Build Folder** (for example
`../../output/full/bodjantouna-42`), or start Godot with `-- --build=<folder>`.

## How it works (in plain words)

- A *tile* is a 512 m square of the city saved as a `.glb` file (a standard 3D file). Every tile
  also has a light *lod1* version (lod = level of detail: simple blocks, seen from far away).
- `scripts/city_streamer.gd` reads `tiles/index.json` (the list of tiles), shows every tile in its
  lod1 version, and loads the full version of the tiles within about 1.4 km of the camera. The full
  tile replaces the light one only when it is ready, so you never see a hole. Tiles that fall
  behind (over 1.7 km) go back to lod1 and the full one is freed from memory. Loading runs in the
  background (at most 3 tiles at a time), so the game does not freeze. The distances are settings
  of the `City` node.
- Godot stores positions with about 7 significant digits. The city lies up to 20 km from the
  origin of the map, where that precision is only a few millimeters and moving objects shake. So
  the project puts the city's focus point at Godot's origin and moves every tile by that amount
  (computed with full precision), as the web viewer does.
- `scripts/citygen_gltf.gd` teaches Godot's glTF reader three things it does not do by itself
  (checked in Godot's source for 4.3 to 4.5):
  - **Quantized meshes** (`KHR_mesh_quantization`: positions stored as small whole numbers to save
    space). Godot refuses these files unless a script says it reads them; it also rounds them
    slightly wrong (8 mm at the edge of a tile) and gives faces stored without normals (the
    direction a face looks, needed for light) no normals at all. The script fixes all three.
  - **Instancing** (`EXT_mesh_gpu_instancing`: one lamp or tree model drawn at many places). Godot
    would draw it once; the script turns each into a `MultiMeshInstance3D`, which draws all the
    copies in one go.
  - **Shared textures** (`tiles/textures/*.jpg`): each image is read once and shared by all tiles,
    with its size in meters (`KHR_texture_transform`).

If quantized tiles ever fail in a Godot version, build without quantization: make a settings
file (for example `worlds/godot.toml`) holding the two lines `[tiles]` and `quantize = false`, and
build with `--world worlds/godot.toml` (everything else keeps its default). The tiles are then about twice as large but use only plain glTF.

## Headless check

Without opening the editor (Godot's command line tool, called `godot` here; on a Mac it is
`/Applications/Godot.app/Contents/MacOS/Godot`):

    godot --headless --path engine/godot --script res://tools/check.gd

It loads every tile of the newest build, full and lod1, and prints the tile, mesh, MultiMesh and
instance counts, and `failures 0` when all is well. Add `-- --build=<folder> --max=10` to choose
the build or check only the first 10 tiles.
