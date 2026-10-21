"""Minimal binary glTF 2.0 (.glb) writer and reader.

One file holds one scene with one node (placed by `translation`) and one mesh
that has one primitive per material. Positions must already be in glTF axes
(+Y up). Only numpy is needed.
"""
from __future__ import annotations

import json
import struct
from pathlib import Path

import numpy as np

_FLOAT = 5126
_UINT = 5125
_USHORT = 5123
_UBYTE = 5121
_ARRAY_BUFFER = 34962
_ELEMENT_ARRAY_BUFFER = 34963


def hex_to_rgb(color: str) -> list[float]:
    color = color.lstrip("#")
    return [int(color[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]


def srgb_to_linear(rgb) -> list[float]:
    c = np.asarray(rgb, dtype=np.float64)
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return [round(float(v), 5) for v in lin]


def _material(name: str, spec: dict) -> dict:
    # glTF wants linear colors; style packs are written in sRGB hex like a paint picker.
    rgb = srgb_to_linear(hex_to_rgb(spec.get("color", "#cccccc")))
    mat = {
        "name": name,
        "pbrMetallicRoughness": {
            "baseColorFactor": rgb + [1.0],
            "metallicFactor": float(spec.get("metallic", 0.0)),
            "roughnessFactor": float(spec.get("roughness", 0.9)),
        },
    }
    if spec.get("double_sided"):
        mat["doubleSided"] = True
    if spec.get("emissive"):
        mat["emissiveFactor"] = srgb_to_linear(hex_to_rgb(spec["emissive"]))
    return mat


def write_glb(path, parts: dict, materials: dict, translation=(0.0, 0.0, 0.0),
              name: str = "tile", extras: dict | None = None, instances: list | None = None) -> int:
    """Write a .glb file and return its size in bytes.

    parts:     {material: {"pos": (N,3), "nrm": (N,3) or None, "uv": (N,2) or None,
                           "col": (N,3|4) linear vertex colors or None, "idx": (M,)}}
    materials: {material: {"color": "#RRGGBB", "roughness": 0.9, "metallic": 0.0,
                           "double_sided": False, "emissive": "#RRGGBB"}}
    instances: [{"name": str, "parts": {...like parts}, "t": (K,3), "r": (K,4) xyzw, "s": (K,3)}]
               each becomes a child node drawn K times (EXT_mesh_gpu_instancing): one door model
               placed on thousands of houses costs its geometry once.
    """
    chunks: list[bytes] = []
    offset = 0
    views: list[dict] = []
    accessors: list[dict] = []

    def add_accessor(arr: np.ndarray, comp: int, kind: str, target: int, minmax=False, normalized=False) -> int:
        nonlocal offset
        pad = (-offset) % 4
        if pad:
            chunks.append(b"\x00" * pad)
            offset += pad
        data = arr.tobytes()
        view = {"buffer": 0, "byteOffset": offset, "byteLength": len(data)}
        if target:
            view["target"] = target
        views.append(view)
        chunks.append(data)
        offset += len(data)
        acc = {"bufferView": len(views) - 1, "componentType": comp, "count": int(arr.shape[0]), "type": kind}
        if normalized:
            acc["normalized"] = True
        if minmax:
            acc["min"] = [float(v) for v in arr.min(axis=0)]
            acc["max"] = [float(v) for v in arr.max(axis=0)]
        accessors.append(acc)
        return len(accessors) - 1

    gl_materials: list[dict] = []
    material_index: dict = {}

    def make_primitives(parts: dict) -> list:
        prims = []
        for mat_name in sorted(parts):
            prim = make_primitive(mat_name, parts[mat_name])
            if prim:
                prims.append(prim)
        return prims

    def make_primitive(mat_name: str, part: dict):
        pos = np.ascontiguousarray(part["pos"], dtype=np.float32).reshape(-1, 3)
        idx = np.asarray(part["idx"]).reshape(-1)
        if len(pos) == 0 or len(idx) == 0:
            return None
        attrs = {"POSITION": add_accessor(pos, _FLOAT, "VEC3", _ARRAY_BUFFER, minmax=True)}
        if part.get("nrm") is not None:
            nrm = np.ascontiguousarray(part["nrm"], dtype=np.float32).reshape(-1, 3)
            attrs["NORMAL"] = add_accessor(nrm, _FLOAT, "VEC3", _ARRAY_BUFFER)
        if part.get("uv") is not None:
            uv = np.ascontiguousarray(part["uv"], dtype=np.float32).reshape(-1, 2)
            attrs["TEXCOORD_0"] = add_accessor(uv, _FLOAT, "VEC2", _ARRAY_BUFFER)
        if part.get("col") is not None:   # 8-bit RGBA: a quarter of the size of floats, plenty for flat colors
            col = np.asarray(part["col"], dtype=np.float64).reshape(len(pos), -1)
            if col.shape[1] == 3:
                col = np.concatenate([col, np.ones((len(col), 1))], axis=1)
            col = np.ascontiguousarray(np.clip(np.round(col * 255.0), 0, 255), dtype=np.uint8)
            attrs["COLOR_0"] = add_accessor(col, _UBYTE, "VEC4", _ARRAY_BUFFER, normalized=True)
        if len(pos) < 65536:
            ind = np.ascontiguousarray(idx, dtype=np.uint16)
            ind_acc = add_accessor(ind, _USHORT, "SCALAR", _ELEMENT_ARRAY_BUFFER)
        else:
            ind = np.ascontiguousarray(idx, dtype=np.uint32)
            ind_acc = add_accessor(ind, _UINT, "SCALAR", _ELEMENT_ARRAY_BUFFER)
        if mat_name not in material_index:
            material_index[mat_name] = len(gl_materials)
            gl_materials.append(_material(mat_name, materials.get(mat_name, {})))
        return {"attributes": attrs, "indices": ind_acc, "material": material_index[mat_name], "mode": 4}

    meshes: list[dict] = []
    primitives = make_primitives(parts)
    node = {"name": name, "translation": [float(v) for v in translation]}
    if extras:
        node["extras"] = extras
    gltf: dict = {
        "asset": {"version": "2.0", "generator": "citygen"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [node],
    }
    if primitives:
        node["mesh"] = len(meshes)
        meshes.append({"name": name, "primitives": primitives})
    for inst in instances or []:
        prims = make_primitives(inst["parts"])
        t = np.ascontiguousarray(inst["t"], dtype=np.float32).reshape(-1, 3)
        if not prims or not len(t):
            continue
        r = np.ascontiguousarray(inst["r"], dtype=np.float32).reshape(-1, 4)
        sc = np.ascontiguousarray(inst["s"], dtype=np.float32).reshape(-1, 3)
        child = {"name": inst["name"], "mesh": len(meshes), "extensions": {"EXT_mesh_gpu_instancing": {"attributes": {
            "TRANSLATION": add_accessor(t, _FLOAT, "VEC3", 0),
            "ROTATION": add_accessor(r, _FLOAT, "VEC4", 0),
            "SCALE": add_accessor(sc, _FLOAT, "VEC3", 0)}}}}
        meshes.append({"name": inst["name"], "primitives": prims})
        gltf["nodes"].append(child)
        node.setdefault("children", []).append(len(gltf["nodes"]) - 1)
        gltf["extensionsUsed"] = ["EXT_mesh_gpu_instancing"]
    if meshes:
        gltf["meshes"] = meshes
        gltf["materials"] = gl_materials
        gltf["accessors"] = accessors
        gltf["bufferViews"] = views

    bin_data = b"".join(chunks)
    bin_data += b"\x00" * ((-len(bin_data)) % 4)
    if bin_data:
        gltf["buffers"] = [{"byteLength": len(bin_data)}]
    json_data = json.dumps(gltf, separators=(",", ":")).encode("utf-8")
    json_data += b" " * ((-len(json_data)) % 4)

    total = 12 + 8 + len(json_data) + (8 + len(bin_data) if bin_data else 0)
    out = [struct.pack("<4sII", b"glTF", 2, total),
           struct.pack("<I4s", len(json_data), b"JSON"), json_data]
    if bin_data:
        out += [struct.pack("<I4s", len(bin_data), b"BIN\x00"), bin_data]
    Path(path).write_bytes(b"".join(out))
    return total


def read_glb(path) -> tuple[dict, bytes]:
    """Return (gltf_json, binary_chunk). Raises ValueError on a malformed file."""
    data = Path(path).read_bytes()
    magic, version, length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or length != len(data):
        raise ValueError(f"not a valid glb file: {path}")
    json_len, json_type = struct.unpack_from("<I4s", data, 12)
    if json_type != b"JSON":
        raise ValueError("first chunk is not JSON")
    gltf = json.loads(data[20:20 + json_len])
    pos = 20 + json_len
    binary = b""
    if pos < len(data):
        bin_len, bin_type = struct.unpack_from("<I4s", data, pos)
        if bin_type != b"BIN\x00":
            raise ValueError("second chunk is not BIN")
        binary = data[pos + 8:pos + 8 + bin_len]
    return gltf, binary


def triangle_count(gltf: dict) -> int:
    total = 0
    for mesh in gltf.get("meshes", []):
        for prim in mesh["primitives"]:
            total += gltf["accessors"][prim["indices"]]["count"] // 3
    return total


_DTYPES = {5126: np.float32, 5125: np.uint32, 5123: np.uint16, 5121: np.uint8}
_WIDTH = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def read_parts(path) -> dict:
    """Mesh data of a .glb as {material name: {"pos", "nrm", "uv", "col", "idx"}} (glTF axes, node transforms ignored)."""
    gltf, binary = read_glb(path)

    def array(index):
        if index is None:
            return None
        acc = gltf["accessors"][index]
        view = gltf["bufferViews"][acc["bufferView"]]
        dtype = _DTYPES[acc["componentType"]]
        width = _WIDTH[acc["type"]]
        start = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
        out = np.frombuffer(binary, dtype, acc["count"] * width, start).reshape(acc["count"], width)
        if dtype == np.uint8 and acc.get("normalized"):
            out = out / 255.0
        return out if width > 1 else out.reshape(-1)

    parts: dict = {}
    for mesh in gltf.get("meshes", []):
        for prim in mesh["primitives"]:
            name = gltf["materials"][prim["material"]]["name"] if "material" in prim else "default"
            a = prim["attributes"]
            part = {"pos": array(a["POSITION"]), "nrm": array(a.get("NORMAL")), "uv": array(a.get("TEXCOORD_0")),
                    "col": array(a.get("COLOR_0")), "idx": array(prim.get("indices"))}
            if part["idx"] is None:
                part["idx"] = np.arange(len(part["pos"]))
            if name in parts:  # several primitives with one material: append
                old = parts[name]
                base = len(old["pos"])
                for key in ("pos", "nrm", "uv", "col"):
                    if old[key] is not None and part[key] is not None:
                        old[key] = np.concatenate([old[key], part[key]])
                old["idx"] = np.concatenate([old["idx"], part["idx"].astype(np.int64) + base])
            else:
                parts[name] = part
    return parts
