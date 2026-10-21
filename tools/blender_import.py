"""Import citygen tiles into Blender (3.6+ and 4.x).

    blender --python tools/blender_import.py -- OUT_DIR/tiles --radius 1500

or set TILES_DIR below and run the file from the Scripting tab. Tiles within the radius of
the focus are imported nearest first into a "City" collection, plus a sun, a sky background
and a camera looking at the focus. Blender turns glTF Y-up into Z-up, so Blender coordinates
equal generator coordinates (x east, y north, z up, meters). Running again replaces the import.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

import bpy
from mathutils import Vector

TILES_DIR = ""        # folder with index.json and the .glb tiles; a command line path overrides it
RADIUS = 1500.0       # meters around the focus
CLIP_END = 20000.0    # 3D viewport and camera clip end

SKY_SRGB = (0.576, 0.776, 0.949)    # the web viewer's sky blue
SUN_AZIMUTH = 225.0                 # degrees clockwise from north: the sun is in the south-west
SUN_ELEVATION = 40.0
MARK = "citygen"                    # custom property on objects and materials made by this script


def read_args() -> tuple[str, float]:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser(prog="blender --python blender_import.py --", description=__doc__.splitlines()[0])
    ap.add_argument("tiles_dir", nargs="?", default=TILES_DIR, help="folder with index.json and the tiles")
    ap.add_argument("--radius", type=float, default=RADIUS, help="import tiles within this many meters of the focus")
    args = ap.parse_args(argv)
    return args.tiles_dir, args.radius


def load_index(tiles_dir: str) -> tuple[Path, dict]:
    if not tiles_dir:
        raise ValueError("set TILES_DIR at the top of the script, or pass the tiles folder after '--'")
    folder = Path(tiles_dir).expanduser()
    if not (folder / "index.json").is_file() and (folder / "tiles" / "index.json").is_file():
        folder = folder / "tiles"   # the generator output folder was given
    index_path = folder / "index.json"
    if not index_path.is_file():
        raise FileNotFoundError(f"no index.json in {folder}")
    return folder, json.loads(index_path.read_text(encoding="utf-8"))


def focus_of(index: dict) -> Vector:
    f = index.get("focus")
    if f:
        return Vector((f["x"], f["y"], f.get("z", 0.0)))
    size = index.get("tile_size", 512)   # no focus recorded: use the middle of the tile set
    xs = [t["x0"] for t in index["tiles"]]
    ys = [t["y0"] for t in index["tiles"]]
    return Vector(((min(xs) + max(xs) + size) / 2, (min(ys) + max(ys) + size) / 2, 0.0))


def pick_tiles(index: dict, focus: Vector, radius: float) -> list[dict]:
    """Tiles whose square touches the radius circle, nearest first."""
    size = index.get("tile_size", 512)
    picked = []
    for t in index["tiles"]:
        dx = max(t["x0"] - focus.x, 0.0, focus.x - (t["x0"] + size))
        dy = max(t["y0"] - focus.y, 0.0, focus.y - (t["y0"] + size))
        near = math.hypot(dx, dy)
        if near <= radius:
            middle = math.hypot(t["x0"] + size / 2 - focus.x, t["y0"] + size / 2 - focus.y)
            picked.append((near, middle, t))
    return [t for _, _, t in sorted(picked, key=lambda p: (p[0], p[1]))]


# --- scene setup ---------------------------------------------------------------

def fresh_collection(name: str) -> bpy.types.Collection:
    """The collection `name`, linked to the scene, without objects and materials an earlier run made."""
    coll = bpy.data.collections.get(name)
    if coll is None:
        coll = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(coll)
    elif name not in bpy.context.scene.collection.children:
        bpy.context.scene.collection.children.link(coll)
    for obj in [o for o in coll.objects if o.get(MARK)]:
        data = obj.data
        bpy.data.objects.remove(obj, do_unlink=True)
        if isinstance(data, bpy.types.Mesh) and data.users == 0:
            bpy.data.meshes.remove(data)
    for mat in list(bpy.data.materials):
        if mat.get(MARK) and mat.users == 0:
            bpy.data.materials.remove(mat)
    return coll


def make_active(coll: bpy.types.Collection) -> None:
    def find(layer):
        if layer.collection is coll:
            return layer
        for child in layer.children:
            hit = find(child)
            if hit:
                return hit
        return None

    layer = find(bpy.context.view_layer.layer_collection)
    if layer:
        bpy.context.view_layer.active_layer_collection = layer


_COPY_SUFFIX = re.compile(r"\.\d{3}$")


def import_tile(path: Path, city: bpy.types.Collection, materials: dict) -> None:
    """Import one .glb into `city`. Materials are shared between tiles instead of copied per tile."""
    before = {o.name for o in bpy.data.objects}
    bpy.ops.import_scene.gltf(filepath=str(path))
    fresh = [o for o in bpy.data.objects if o.name not in before]
    for obj in fresh:
        for coll in list(obj.users_collection):
            coll.objects.unlink(obj)
        city.objects.link(obj)
        obj[MARK] = True
        if obj.type != "MESH":
            continue
        for slot in obj.material_slots:
            mat = slot.material
            if mat is None:
                continue
            keep = materials.setdefault(_COPY_SUFFIX.sub("", mat.name), mat)   # "grass.012" is "grass" again
            keep[MARK] = True
            if keep is not mat:
                slot.material = keep
                if mat.users == 0:
                    bpy.data.materials.remove(mat)


def srgb_to_linear(c: float) -> float:
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def drop(name: str, blocks) -> None:
    """Remove the object `name` and its datablock (from bpy.data.lights or .cameras) left by an earlier run."""
    obj = bpy.data.objects.get(name)
    if obj is not None:
        bpy.data.objects.remove(obj, do_unlink=True)
    block = blocks.get(name)
    if block is not None:
        blocks.remove(block)


def link_new(name: str, data) -> bpy.types.Object:
    obj = bpy.data.objects.new(name, data)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def add_sun(focus: Vector) -> None:
    az, el = math.radians(SUN_AZIMUTH), math.radians(SUN_ELEVATION)
    toward_sun = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))
    drop("City Sun", bpy.data.lights)
    light = bpy.data.lights.new("City Sun", "SUN")
    light.energy = 3.0
    light.color = (1.0, 0.93, 0.8)
    light.angle = math.radians(0.6)
    sun = link_new("City Sun", light)
    sun.location = focus + toward_sun * 1000.0
    sun.rotation_euler = (-toward_sun).to_track_quat("-Z", "Y").to_euler()   # a sun shines along -Z


def add_sky() -> None:
    world = bpy.data.worlds.get("City Sky") or bpy.data.worlds.new("City Sky")
    if world.node_tree is None:   # Blender 5 worlds always have nodes; use_nodes is deprecated there
        world.use_nodes = True
    bg = world.node_tree.nodes.get("Background") or world.node_tree.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (*map(srgb_to_linear, SKY_SRGB), 1.0)
    bg.inputs["Strength"].default_value = 1.0
    bpy.context.scene.world = world


def add_camera(focus: Vector, radius: float) -> bpy.types.Object:
    """An aerial camera south-south-east of the focus, looking at it."""
    reach = max(radius, 300.0)
    bearing = math.radians(160.0)
    position = focus + Vector((math.sin(bearing) * 0.6 * reach, math.cos(bearing) * 0.6 * reach, 0.45 * reach))
    drop("City Camera", bpy.data.cameras)
    data = bpy.data.cameras.new("City Camera")
    data.lens = 28.0
    data.clip_start = 1.0
    data.clip_end = CLIP_END
    cam = link_new("City Camera", data)
    cam.location = position
    cam.rotation_euler = (focus - position).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = cam
    return cam


def set_viewports(cam: bpy.types.Object, focus: Vector) -> None:
    """Raise the clip end of every 3D viewport and point the view at the focus."""
    distance = (cam.location - focus).length
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            for space in area.spaces:
                if space.type != "VIEW_3D":
                    continue
                space.clip_end = CLIP_END
                r3d = space.region_3d
                if r3d is not None:
                    r3d.view_location = focus
                    r3d.view_distance = distance
                    r3d.view_rotation = cam.rotation_euler.to_quaternion()


def main() -> None:
    tiles_dir, radius = read_args()
    folder, index = load_index(tiles_dir)
    focus = focus_of(index)
    tiles = pick_tiles(index, focus, radius)
    print(f"citygen: {len(tiles)} of {len(index['tiles'])} tiles within {radius:g} m of "
          f"({focus.x:.0f}, {focus.y:.0f}) in {folder}")

    if not hasattr(bpy.ops.import_scene, "gltf"):
        bpy.ops.preferences.addon_enable(module="io_scene_gltf2")
    city = fresh_collection("City")
    make_active(city)
    materials: dict[str, bpy.types.Material] = {}
    done = 0
    for n, tile in enumerate(tiles, 1):
        path = folder / tile["file"]
        print(f"citygen: [{n}/{len(tiles)}] {path.name}", flush=True)
        try:
            import_tile(path, city, materials)
            done += 1
        except Exception as exc:   # keep going: one bad tile should not stop the import
            print(f"citygen: skipped {path.name}: {exc}")

    add_sky()
    add_sun(focus)
    set_viewports(add_camera(focus, radius), focus)
    print(f"citygen: imported {done} tiles into collection 'City'")


if __name__ == "__main__":
    main()
