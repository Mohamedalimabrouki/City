"""Turn a collection of a Blender file into a citygen kit: one .glb per piece plus manifest.json.

    python tools/blender_kit_export.py FILE --collection NAME (--name KIT | --out FOLDER)
                                       [--front +Y|-Y] [--blender PATH] [--timeout SECONDS]

FILE is a .blend file (or a .py script that builds the scene in a fresh Blender, used for the
test fixture). Every mesh object of the collection (sub-collections included) becomes
kits/<KIT>/<object>.glb, ready for [build] kits and the style's [dressing.roles]. Custom
properties on each object (Object Properties > Custom Properties) describe it:

    category  door, window, lamp, pot, plant, sign...   (default ground_prop, with a warning)
    anchor    ground (bottom-center on the ground) or wall (on the wall face)  (default ground)
    front     +Y (the piece looks toward Blender +Y) or -Y (turned 180 degrees about Z on export)
    tags      words separated by commas (optional)

The object's origin is the anchor; its rotation, scale and modifiers are baked into the mesh.
Materials keep a palette name (lime_white...) as is; others become <KIT>_<material>, with their
Principled BSDF color written to the manifest as sRGB hex. Vertex colors and UVs are not exported.

Blender crashes at start inside the Claude sandbox (see tools/make_blend.py): inside a sandbox
this tool stops before starting Blender.
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path

MARK = "blender_kit_export:"
MADE_BY = "tools/blender_kit_export.py"
PROPS = ("category", "anchor", "front", "tags")
DEFAULTS = {"category": "ground_prop", "anchor": "ground"}
ANCHORS = ("ground", "wall")


def piece_name(text: str) -> str:
    """A file and piece name from a Blender name: "Door Blue.001" -> "door_blue_001"."""
    return re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_") or "piece"


def linear_to_srgb_hex(rgb) -> str:
    """Blender's linear color (0-1 floats) as the sRGB "#RRGGBB" the palette and manifests use."""
    out = []
    for c in rgb[:3]:
        c = min(max(float(c), 0.0), 1.0)
        s = c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
        out.append(round(s * 255))
    return "#{:02X}{:02X}{:02X}".format(*out)


def front_of(value, default: str) -> str | None:
    """"+Y" or "-Y" from a custom property value (also "y", "-y", "+y"); None when not understood."""
    text = str(value if value is not None else default).strip().upper().replace(" ", "")
    return {"Y": "+Y", "+Y": "+Y", "-Y": "-Y"}.get(text)


# ------------------------------------------------------------------ inside Blender

def _report(kind: str, data) -> None:
    print(MARK, kind, json.dumps(data), flush=True)


def _material_info(mat) -> dict:
    """Linear color, roughness, metallic and emission of a material (Principled BSDF, else viewport)."""
    info = {"color": list(mat.diffuse_color[:3]), "roughness": float(mat.roughness),
            "metallic": float(mat.metallic), "emission": [0.0, 0.0, 0.0], "textured": False}
    nodes = mat.node_tree.nodes if mat.use_nodes and mat.node_tree else []
    bsdf = next((n for n in nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        return info

    def value(key, default):
        sock = bsdf.inputs.get(key)
        if sock is None:
            return default
        info["textured"] |= sock.is_linked and key == "Base Color"
        return sock.default_value

    info["color"] = list(value("Base Color", info["color"])[:3])
    info["roughness"] = float(value("Roughness", info["roughness"]))
    info["metallic"] = float(value("Metallic", info["metallic"]))
    strength = float(value("Emission Strength", 0.0))
    emission = list(value("Emission Color", (0.0, 0.0, 0.0, 1.0))[:3])
    info["emission"] = [min(1.0, c * strength) for c in emission]
    return info


def _export_args(op) -> dict:
    """glTF exporter options for one baked object, keeping only those this Blender version knows."""
    wanted = {"export_format": "GLB", "use_selection": True, "export_yup": True, "export_apply": False,
              "export_materials": "EXPORT", "export_texcoords": False, "export_normals": True,
              "export_vertex_color": "NONE", "export_colors": False, "export_attributes": False,
              "export_extras": False, "export_cameras": False, "export_lights": False,
              "export_animations": False, "export_skins": False, "export_morph": False,
              "export_image_format": "NONE"}
    known = {p.identifier for p in op.get_rna_type().properties}
    return {k: v for k, v in wanted.items() if k in known}


def inside_blender(opts: dict) -> None:
    import bpy
    from mathutils import Matrix

    coll = bpy.data.collections.get(opts["collection"])
    if coll is None:
        names = ", ".join(sorted(c.name for c in bpy.data.collections)) or "none"
        _report("error", f"no collection named {opts['collection']!r} (collections: {names})")
        return
    objects = sorted((o for o in coll.all_objects if o.type == "MESH"), key=lambda o: o.name)
    if not objects:
        _report("error", f"collection {opts['collection']!r} has no mesh object")
        return
    palette, kit = set(opts["palette"]), opts["kit"]
    materials = {}
    for mat in sorted({s.material for o in objects for s in o.material_slots if s.material}, key=lambda m: m.name):
        info = _material_info(mat)
        new = mat.name if mat.name in palette else f"{kit}_{piece_name(mat.name)}"
        info["blender"] = mat.name
        mat.name = new          # the .blend is never saved: renaming only names the exported material
        if mat.name != new:
            _report("error", f"two materials both become {new!r}: rename one of them in Blender")
            return
        materials[new] = info
    temp = bpy.data.collections.new("citygen_export")
    bpy.context.scene.collection.children.link(temp)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    turn = Matrix.Rotation(math.pi, 4, "Z")
    names = [piece_name(o.name) for o in objects]
    twins = sorted({n for n in names if names.count(n) > 1})
    if twins:
        _report("error", f"several objects become the piece {twins[0]!r}: rename them in Blender")
        return
    for obj in objects:
        props = {k: obj.get(k) for k in PROPS}
        props = {k: (None if v is None else str(v)) for k, v in props.items()}
        front = front_of(props["front"], opts["front"])
        mesh = bpy.data.meshes.new_from_object(obj.evaluated_get(depsgraph), depsgraph=depsgraph)
        for i, slot in enumerate(obj.material_slots):   # object-linked slots too; clear() would drop the indices
            if i < len(mesh.materials):
                mesh.materials[i] = slot.material
            else:
                mesh.materials.append(slot.material)
        bake = obj.matrix_world.to_3x3().to_4x4()   # rotation and scale only: the origin is the anchor
        if front == "-Y":
            bake = turn @ bake
        mesh.transform(bake)
        if bake.determinant() < 0:                  # a mirrored scale turns faces inside out
            mesh.flip_normals()
        name = piece_name(obj.name)
        baked = bpy.data.objects.new(name, mesh)
        temp.objects.link(baked)
        for o in bpy.context.view_layer.objects:
            o.select_set(False)
        baked.select_set(True)
        bpy.context.view_layer.objects.active = baked
        path = f"{opts['folder']}/{name}.glb"
        bpy.ops.export_scene.gltf(filepath=path, **_export_args(bpy.ops.export_scene.gltf))
        _report("piece", {"name": name, "blender": obj.name, "file": f"{name}.glb", "props": props,
                          "front": front, "empty": not mesh.polygons})
    _report("done", {"materials": materials})


# ------------------------------------------------------------------ outside Blender (Ali's terminal)

def _manifest(found: dict, folder, source: str, warn) -> dict:
    """The citygen-kit/1 manifest of the exported pieces, checking each .glb reads back cleanly."""
    from citygen.mesh.gltf import read_glb, read_parts
    import numpy as np

    shapes = {p["name"]: read_parts(folder / p["file"]) for p in found["pieces"] if not p["empty"]}
    used = {m for parts in shapes.values() for m in parts}
    materials = {}
    for name, info in sorted(found["materials"].items()):
        if name not in used:
            continue
        if name in found["palette"]:
            if found["palette"][name].get("texture"):
                warn(f"material {name}: the palette gives it a texture, but kit pieces carry no UVs (flat color)")
            continue                       # the palette keeps its own look
        if info["textured"]:
            warn(f"material {info['blender']}: Base Color is linked to a texture; only its plain color is used")
        spec = {"color": linear_to_srgb_hex(info["color"]), "roughness": round(info["roughness"], 3),
                "metallic": round(info["metallic"], 3)}
        if max(info["emission"]) > 0.0:
            spec["emissive"] = linear_to_srgb_hex(info["emission"])
        spec["note"] = f"Blender material {info['blender']!r}"
        materials[name] = spec
    pieces = {}
    for p in found["pieces"]:
        if p["empty"]:
            warn(f"{p['blender']}: no faces, skipped")
            continue
        gltf, _ = read_glb(folder / p["file"])
        for node in gltf.get("nodes", []):
            if any(k in node for k in ("rotation", "scale", "matrix")) or any(node.get("translation", [0])):
                warn(f"{p['blender']}: the .glb has a node transform, which citygen ignores")
        parts = shapes[p["name"]]
        pos = np.concatenate([part["pos"] for part in parts.values()])
        lo, hi = pos.min(axis=0), pos.max(axis=0)
        props = p["props"]
        spec = {"file": p["file"]}
        for key in ("category", "anchor"):
            value = props[key]
            if not value:
                warn(f"{p['blender']}: no '{key}' custom property, using {DEFAULTS[key]!r}")
                value = DEFAULTS[key]
            spec[key] = value
        if spec["anchor"] not in ANCHORS:
            warn(f"{p['blender']}: anchor {spec['anchor']!r} is not ground or wall, using 'ground'")
            spec["anchor"] = "ground"
        if props["front"] is not None and front_of(props["front"], "+Y") is None:
            warn(f"{p['blender']}: front {props['front']!r} is not +Y or -Y, used +Y")
        spec["tags"] = [t.strip() for t in (props["tags"] or "").split(",") if t.strip()]
        spec["size"] = [round(float(v), 3) for v in hi - lo]
        spec["triangles"] = int(sum(len(part["idx"]) // 3 for part in parts.values()))
        spec["source"] = f"Blender object {p['blender']!r}, modeled facing {p['front']}"
        spec["bounds"] = {"min": [round(float(v), 3) for v in lo], "max": [round(float(v), 3) for v in hi]}
        pieces[p["name"]] = spec
    return {"format": "citygen-kit/1", "source": source, "made_by": MADE_BY, "units": "meters",
            "axes": "glTF: +Y up, front faces -Z, x along the wall, origin at the anchor",
            "materials": materials, "pieces": pieces}


def _command(blender: str, source, folder, opts: dict) -> list[str]:
    me = str(Path(__file__).resolve())
    head = [blender, "-b", "--factory-startup"]
    if source.suffix == ".py":
        head += ["--python", str(source)]
    else:
        head.insert(3, str(source))
    return head + ["--python", me, "--", "--inside", json.dumps({**opts, "folder": str(folder)})]


def _target(args, root):
    if bool(args.name) == bool(args.out):
        sys.exit("Give either --name KIT (writes kits/KIT/) or --out FOLDER.")
    out = Path(args.out).resolve() if args.out else root / "kits" / piece_name(args.name)
    old = out / "manifest.json"
    if old.is_file():
        try:
            made = json.loads(old.read_text(encoding="utf-8")).get("made_by")
        except ValueError:
            made = None
        if made != MADE_BY:
            sys.exit(f"{out} holds a kit this tool did not make (for example kits/tounes): choose another name.")
    elif any(out.glob("*.glb")):
        sys.exit(f"{out} holds .glb files but no kit manifest: choose another name or folder.")
    return out


def main(argv: list[str] | None = None) -> None:
    import argparse
    import shutil
    import subprocess
    import tempfile

    root = Path(__file__).resolve().parents[1]
    for p in (str(root), str(root / "tools")):
        if p not in sys.path:
            sys.path.insert(0, p)
    from citygen.config import load_config, load_style
    from make_blend import BLENDER, sandboxed

    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("file", help="the .blend file (or a .py script that builds the scene)")
    ap.add_argument("--collection", required=True, help="the Blender collection holding the pieces")
    ap.add_argument("--name", help="kit name: writes kits/<name>/")
    ap.add_argument("--out", help="write the kit to this folder instead (its folder name is the kit name)")
    ap.add_argument("--front", default="+Y", choices=["+Y", "-Y"],
                    help="facing of pieces with no 'front' property (default +Y)")
    ap.add_argument("--blender", default=BLENDER, help="path to the Blender program")
    ap.add_argument("--timeout", type=int, default=600, help="seconds before giving up")
    args = ap.parse_args(argv)
    source = Path(args.file).resolve()
    if not source.is_file() or source.suffix not in (".blend", ".py"):
        sys.exit(f"Not a .blend or .py file: {source}")
    out = _target(args, root)
    palette = load_style(load_config()["world"]["style"])["palette"]
    if sandboxed():
        sys.exit("Not starting Blender: this command runs inside a sandbox, where Blender crashes at start "
                 "(it cannot see the GPU). Run it in your own terminal, or as an agent with the sandbox off.")
    out.parent.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []
    with tempfile.TemporaryDirectory(dir=out.parent, prefix=f".{out.name}-") as tmp:
        opts = {"collection": args.collection, "kit": out.name, "front": args.front, "palette": sorted(palette)}
        run = subprocess.run(_command(args.blender, source, tmp, opts), capture_output=True, text=True,
                             timeout=args.timeout)
        found = {"pieces": [], "materials": {}, "palette": palette}
        done = False
        for line in run.stdout.splitlines():
            if not line.startswith(MARK):
                continue
            kind, _, data = line[len(MARK):].strip().partition(" ")
            data = json.loads(data)
            if kind == "error":
                sys.exit(f"Blender: {data}")
            if kind == "piece":
                found["pieces"].append(data)
            if kind == "done":
                found["materials"], done = data["materials"], True
        if not done:
            print("\n".join((run.stdout + run.stderr).splitlines()[-15:]))
            sys.exit("Blender stopped before the export finished (see its last lines above).")
        tmp = Path(tmp)
        manifest = _manifest(found, tmp, f"Blender: {source.name}, collection {args.collection}", warnings.append)
        old = out / "manifest.json"
        stale = set(json.loads(old.read_text(encoding="utf-8")).get("pieces", {})) if old.is_file() else set()
        out.mkdir(exist_ok=True)
        for name in stale - set(manifest["pieces"]):
            (out / f"{name}.glb").unlink(missing_ok=True)
        for name, spec in manifest["pieces"].items():
            shutil.move(str(tmp / spec["file"]), str(out / spec["file"]))
        (out / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    for w in warnings:
        print("warning:", w)
    kit = out.name
    print(f"Kit {kit}: {len(manifest['pieces'])} pieces in {out}")
    for name, spec in manifest["pieces"].items():
        print(f"  {kit}/{name:24s} {spec['category']:12s} {spec['anchor']:6s} {spec['triangles']:6d} tris")
    print(f'Use it: add "{kit}" to [build] kits, then a role such as door_blue = [["{kit}/<piece>", 1], ...].')


if __name__ == "__main__":
    if "--inside" in sys.argv:
        inside_blender(json.loads(sys.argv[sys.argv.index("--inside") + 1]))
    else:
        main()
