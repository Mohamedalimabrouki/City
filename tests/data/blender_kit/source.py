"""Blender script that builds the test kit's source scene (prompt 38). Re-export the fixture with:

    .venv/bin/python tools/blender_kit_export.py tests/data/blender_kit/source.py --collection Kit --out tests/data/blender_kit

- house: a little house with a blue door, modeled facing -Y (custom property front = -Y), scaled
  1.5 on the object and placed away from the world origin: once exported it is 3 m wide and its
  door faces glTF -Z (generator +y, the street).
- arrow: a flat yellow arrow modeled pointing +X, then the object turned 90 degrees about Z so it
  points +Y (its front, the default): once exported its tip is at glTF -Z. No anchor property, so
  the tool warns and uses "ground".
"""
import math

import bpy


def srgb_to_linear(hex_color):
    rgb = [int(hex_color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb]


def material(name, hex_color, roughness):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*srgb_to_linear(hex_color), 1.0)
    bsdf.inputs["Roughness"].default_value = roughness
    return mat


def box(verts, faces, mats, x0, x1, y0, y1, z0, z1, m):
    base = len(verts)
    verts += [(x, y, z) for z in (z0, z1) for y in (y0, y1) for x in (x0, x1)]
    for quad in ((0, 2, 3, 1), (4, 5, 7, 6), (0, 1, 5, 4), (2, 6, 7, 3), (0, 4, 6, 2), (1, 3, 7, 5)):
        faces.append(tuple(base + i for i in quad))
        mats.append(m)


def mesh_object(name, verts, faces, mats, materials, coll):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    for mat in materials:
        mesh.materials.append(mat)
    for poly, m in zip(mesh.polygons, mats):
        poly.material_index = m
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    coll.objects.link(obj)
    return obj


coll = bpy.data.collections.new("Kit")
bpy.context.scene.collection.children.link(coll)
wall = material("cabin_white", "#F2F0EA", 0.9)        # a palette name: the palette keeps it
door = material("Door Blue", "#1F5FA8", 0.6)
roof = material("Roof Red", "#B5532F", 0.8)
arrow_mat = material("Arrow Yellow", "#E8B82E", 0.4)

verts, faces, mats = [], [], []
box(verts, faces, mats, -1.0, 1.0, -1.0, 1.0, 0.0, 2.0, 0)       # walls
box(verts, faces, mats, -0.4, 0.4, -1.1, -1.0, 0.0, 1.6, 1)      # door on the -Y side
base = len(verts)
verts += [(-1.1, -1.1, 2.0), (1.1, -1.1, 2.0), (1.1, 1.1, 2.0), (-1.1, 1.1, 2.0), (0.0, 0.0, 2.9)]
faces += [(base, base + 1, base + 4), (base + 1, base + 2, base + 4), (base + 2, base + 3, base + 4),
          (base + 3, base, base + 4), (base + 3, base + 2, base + 1, base)]
mats += [2] * 5
house = mesh_object("House", verts, faces, mats, [wall, door, roof], coll)
house.location = (6.0, -4.0, 0.0)
house.scale = (1.5, 1.5, 1.5)
house["category"], house["anchor"], house["front"], house["tags"] = "house", "ground", "-Y", "test, door"

outline = [(-0.6, -0.15), (0.2, -0.15), (0.2, -0.4), (0.8, 0.0), (0.2, 0.4), (0.2, 0.15), (-0.6, 0.15)]
n = len(outline)
verts = [(x, y, z) for z in (0.0, 0.3) for x, y in outline]
faces = [tuple(reversed(range(n))), tuple(range(n, 2 * n))]
faces += [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
arrow = mesh_object("Arrow", verts, faces, [0] * len(faces), [arrow_mat], coll)
arrow.location = (-3.0, 2.0, 0.0)
arrow.rotation_euler = (0.0, 0.0, math.pi / 2)
arrow["category"] = "sign"
