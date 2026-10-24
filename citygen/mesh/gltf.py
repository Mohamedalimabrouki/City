"""Minimal binary glTF 2.0 (.glb) writer and reader.

One file holds one scene with one node (placed by `translation`) and one mesh
that has one primitive per material. Positions must already be in glTF axes
(+Y up). Only numpy is needed.

`write_glb(..., quantize=True)` writes the smaller KHR_mesh_quantization form (SPEC 7, prompt 39):
16-bit positions dequantized by a child node's uniform scale, 8-bit normals, 16-bit instance
rotations, shared vertices welded, 16-bit indices everywhere and one bufferView per kind of data.
"""
from __future__ import annotations

import json
import struct
from pathlib import Path

import numpy as np

_FLOAT = 5126
_UINT = 5125
_USHORT = 5123
_SHORT = 5122
_UBYTE = 5121
_BYTE = 5120
_ARRAY_BUFFER = 34962
_ELEMENT_ARRAY_BUFFER = 34963
_I16 = 32767.0              # normalized SHORT: value / 32767, clamped at -1
_I8 = 127.0                 # normalized BYTE
_MAX_VERTS = 65535          # vertices per primitive with 16-bit indices (65535 itself stays free)


def hex_to_rgb(color: str) -> list[float]:
    color = color.lstrip("#")
    return [int(color[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]


def srgb_to_linear(rgb) -> list[float]:
    c = np.asarray(rgb, dtype=np.float64)
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return [round(float(v), 5) for v in lin]


_SAMPLER = {"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}  # REPEAT, mipmaps


def _material(name: str, spec: dict, texture: int | None = None) -> dict:
    # glTF wants linear colors; style packs are written in sRGB hex like a paint picker.
    rgb = srgb_to_linear(hex_to_rgb(spec.get("color", "#cccccc")))
    base = {
        "baseColorFactor": rgb + [1.0],
        "metallicFactor": float(spec.get("metallic", 0.0)),
        "roughnessFactor": float(spec.get("roughness", 0.9)),
    }
    if texture is not None:
        # UVs are meters, so one repeat covers `texture_size` meters: scale the UVs instead of
        # baking a repeat into the mesh (three.js and Blender both read KHR_texture_transform).
        w, h = (float(v) for v in spec.get("texture_size", (1.0, 1.0)))
        base["baseColorTexture"] = {
            "index": texture,
            "extensions": {"KHR_texture_transform": {"scale": [1.0 / w, 1.0 / h]}},
        }
    mat = {"name": name, "pbrMetallicRoughness": base}
    if spec.get("double_sided"):
        mat["doubleSided"] = True
    if spec.get("emissive"):
        mat["emissiveFactor"] = srgb_to_linear(hex_to_rgb(spec["emissive"]))
    return mat


# --- quantization helpers ----------------------------------------------------------------

def quantize_frame(pos: np.ndarray) -> tuple[np.ndarray, float]:
    """Center and uniform half size that map `pos` into the normalized SHORT cube [-1, 1]^3.

    One size for all three axes, so the dequantization is a uniform scale: angles and normals
    keep their directions in the mesh's own space (raycasts, Blender's custom normals)."""
    lo, hi = pos.min(axis=0).astype(np.float64), pos.max(axis=0).astype(np.float64)
    center = (lo + hi) / 2.0
    half = float(np.max(hi - lo)) / 2.0
    return center, max(half, 1e-6)


def _q16(x: np.ndarray) -> np.ndarray:
    return np.clip(np.round(x * _I16), -_I16, _I16).astype(np.int16)


def _q8(x: np.ndarray) -> np.ndarray:
    return np.clip(np.round(x * _I8), -_I8, _I8).astype(np.int8)


def _pad4(a: np.ndarray) -> np.ndarray:
    """(N, 3) -> (N, 4) with a zero 4th column: vertex elements must start on 4-byte boundaries."""
    return np.ascontiguousarray(np.concatenate([a, np.zeros((len(a), 1), dtype=a.dtype)], axis=1))


def quantize_rotations(r: np.ndarray) -> np.ndarray:
    """xyzw unit quaternions as normalized SHORT (EXT_mesh_gpu_instancing allows it)."""
    return np.ascontiguousarray(_q16(np.asarray(r, dtype=np.float64)))


def short_edges(pos: np.ndarray, tris: np.ndarray, limit: float) -> np.ndarray:
    """Triangles with an edge shorter than `limit` meters: thin ropes, rods and bars, whose few
    centimeters would bend by quantization steps of about 8 mm (they stay float)."""
    if limit <= 0.0 or not len(tris):
        return np.zeros(len(tris), dtype=bool)
    t = pos[tris]
    e = np.minimum(np.minimum(((t[:, 1] - t[:, 0]) ** 2).sum(axis=1), ((t[:, 2] - t[:, 1]) ** 2).sum(axis=1)),
                   ((t[:, 0] - t[:, 2]) ** 2).sum(axis=1))
    return e < limit * limit


def _weld(arrays: list, tris: np.ndarray) -> tuple[list, np.ndarray]:
    """Merge vertices whose written bytes are all equal (a cap's shared corners, ...); keeps the
    order of first appearance, so triangles still reference nearby vertices (cache, chunking)."""
    n = len(arrays[0])
    raw = np.concatenate([np.ascontiguousarray(a).view(np.uint8).reshape(n, -1) for a in arrays], axis=1)
    key = np.ascontiguousarray(raw).view(np.dtype((np.void, raw.shape[1]))).ravel()
    _, first, inverse = np.unique(key, return_index=True, return_inverse=True)
    order = np.argsort(first, kind="stable")
    new_id = np.empty(len(first), dtype=np.int64)
    new_id[order] = np.arange(len(first))
    keep = first[order]
    used = np.zeros(len(keep), dtype=bool)
    remap = new_id[np.asarray(inverse).reshape(-1)][tris]
    used[remap.reshape(-1)] = True
    if not used.all():                     # drop vertices no triangle uses
        compact = np.cumsum(used) - 1
        keep, remap = keep[used], compact[remap]
    return [a[keep] for a in arrays], remap


def _chunks(tris: np.ndarray) -> list[tuple[int, int]]:
    """Triangle ranges that each use at most 65535 vertices, so every primitive gets 16-bit indices."""
    out, start, total = [], 0, len(tris)
    if not total or int(tris.max()) < _MAX_VERTS:     # welded vertices are compact: the usual case
        return [(0, total)]
    while start < total:
        lo, hi = start + 1, total
        if len(np.unique(tris[start:hi])) > _MAX_VERTS:
            while lo < hi:                 # the longest range from `start` that still fits
                mid = (lo + hi + 1) // 2
                if len(np.unique(tris[start:mid])) <= _MAX_VERTS:
                    lo = mid
                else:
                    hi = mid - 1
            hi = lo
        out.append((start, hi))
        start = hi
    return out


# --- writer ----------------------------------------------------------------------------

class _Buffer:
    """The binary chunk, its bufferViews and accessors.

    Float tiles give every accessor its own bufferView (today's bytes). Quantized tiles pool
    accessors of one kind (same target and stride) into one bufferView: thousands of views cost
    about 60 bytes of JSON each."""

    def __init__(self, pooled: bool):
        self.chunks: list[bytes] = []
        self.offset = 0
        self.views: list[dict] = []
        self.accessors: list[dict] = []
        self.pools: dict | None = {} if pooled else None

    def add_view(self, data: bytes, target: int = 0, stride: int = 0) -> int:
        pad = (-self.offset) % 4
        if pad:
            self.chunks.append(b"\x00" * pad)
            self.offset += pad
        view = {"buffer": 0, "byteOffset": self.offset, "byteLength": len(data)}
        if stride:
            view["byteStride"] = stride
        if target:
            view["target"] = target
        self.views.append(view)
        self.chunks.append(data)
        self.offset += len(data)
        return len(self.views) - 1

    def add_accessor(self, arr: np.ndarray, comp: int, kind: str, target: int, minmax=False, normalized=False,
                     stride: int = 0) -> int:
        """`arr` (count, columns): columns past the type's width are padding (stride)."""
        data = np.ascontiguousarray(arr).tobytes()
        if self.pools is None:
            acc = {"bufferView": self.add_view(data, target), "componentType": comp,
                   "count": int(arr.shape[0]), "type": kind}
        else:
            pool = self.pools.setdefault((target, stride, comp if not target else 0), [[], 0, []])
            pad = (-pool[1]) % 4
            if pad:
                pool[0].append(b"\x00" * pad)
                pool[1] += pad
            acc = {"bufferView": None, "byteOffset": pool[1], "componentType": comp,
                   "count": int(arr.shape[0]), "type": kind}
            pool[0].append(data)
            pool[1] += len(data)
            pool[2].append(acc)
        if normalized:
            acc["normalized"] = True
        if minmax:
            vals = arr[:, :_WIDTH[kind]]
            if comp != _FLOAT:
                cast = int
            elif self.pools is None:
                cast = float
            else:   # the shortest text that reads back as the same float32 (glTF: round to single precision)
                def cast(v):
                    return float(str(np.float32(v)))
            acc["min"] = [cast(v) for v in vals.min(axis=0)]
            acc["max"] = [cast(v) for v in vals.max(axis=0)]
        self.accessors.append(acc)
        return len(self.accessors) - 1

    def finish(self) -> bytes:
        for (target, stride, _), (datas, _, accs) in (self.pools or {}).items():
            view = self.add_view(b"".join(datas), target, stride)
            for acc in accs:
                acc["bufferView"] = view
                if not acc["byteOffset"]:
                    del acc["byteOffset"]
        data = b"".join(self.chunks)
        return data + b"\x00" * ((-len(data)) % 4)


def _float_attributes(buf: _Buffer, part: dict, pos: np.ndarray) -> dict:
    """Today's float accessors: positions (with bounds), normals, meter UVs, 8-bit colors."""
    attrs = {"POSITION": buf.add_accessor(pos, _FLOAT, "VEC3", _ARRAY_BUFFER, minmax=True)}
    if part.get("nrm") is not None:
        nrm = np.ascontiguousarray(part["nrm"], dtype=np.float32).reshape(-1, 3)
        attrs["NORMAL"] = buf.add_accessor(nrm, _FLOAT, "VEC3", _ARRAY_BUFFER)
    if part.get("uv") is not None:
        uv = np.ascontiguousarray(part["uv"], dtype=np.float32).reshape(-1, 2)
        attrs["TEXCOORD_0"] = buf.add_accessor(uv, _FLOAT, "VEC2", _ARRAY_BUFFER)
    if part.get("col") is not None:   # 8-bit RGBA: a quarter of the size of floats, plenty for flat colors
        attrs["COLOR_0"] = buf.add_accessor(_colors(part["col"], len(pos)), _UBYTE, "VEC4", _ARRAY_BUFFER,
                                            normalized=True)
    return attrs


def _colors(col, n: int) -> np.ndarray:
    col = np.asarray(col, dtype=np.float64).reshape(n, -1)
    if col.shape[1] == 3:
        col = np.concatenate([col, np.ones((len(col), 1))], axis=1)
    return np.ascontiguousarray(np.clip(np.round(col * 255.0), 0, 255), dtype=np.uint8)


def _encoded(part: dict, frame) -> list:
    """The quantized form of a part's vertices: [(name, array, componentType, type, normalized, stride)].

    `frame` = (center, half) quantizes positions to normalized SHORT; None keeps them float."""
    pos = np.asarray(part["pos"], dtype=np.float64).reshape(-1, 3)
    if frame is None:
        out = [("POSITION", np.ascontiguousarray(pos, dtype=np.float32), _FLOAT, "VEC3", False, 12)]
    else:
        center, half = frame
        out = [("POSITION", _pad4(_q16((pos - center) / half)), _SHORT, "VEC3", True, 8)]
    if part.get("nrm") is not None:
        out.append(("NORMAL", _pad4(_q8(np.asarray(part["nrm"], dtype=np.float64).reshape(-1, 3))), _BYTE, "VEC3",
                    True, 4))
    if part.get("uv") is not None:      # meter UVs stay float (SPEC 7: world meters up to 64 km)
        out.append(("TEXCOORD_0", np.ascontiguousarray(part["uv"], dtype=np.float32).reshape(-1, 2), _FLOAT,
                    "VEC2", False, 8))
    if part.get("col") is not None:
        out.append(("COLOR_0", _colors(part["col"], len(pos)), _UBYTE, "VEC4", True, 4))
    return out


def write_glb(path, parts: dict, materials: dict, translation=(0.0, 0.0, 0.0),
              name: str = "tile", extras: dict | None = None, instances: list | None = None,
              images: dict | None = None, quantize: bool = False, float_materials=(),
              fine_edge: float = 0.0, flat_angle: float = 0.0) -> int:
    """Write a .glb file and return its size in bytes.

    parts:     {material: {"pos": (N,3), "nrm": (N,3) or None, "uv": (N,2) or None,
                           "col": (N,3|4) linear vertex colors or None, "idx": (M,),
                           "fine": (M/3,) bool or absent: triangles that must stay float}}
    materials: {material: {"color": "#RRGGBB", "roughness": 0.9, "metallic": 0.0,
                           "double_sided": False, "emissive": "#RRGGBB",
                           "texture": "plaster", "texture_size": [w, h]}}
    images:    {texture name: {"uri": "textures/plaster.png"} or {"bytes": png, "mime": ...}}
               A material that names a texture in `images` gets it as a base-color texture:
               the palette color still multiplies it, and `texture_size` (meters per repeat)
               becomes a KHR_texture_transform scale so the meter UVs stay unchanged.
               "shared" builds pass URIs written once by the parent; "embedded" builds pass
               the bytes, which go into the binary chunk.
    instances: [{"name": str, "parts": {...like parts}, "t": (K,3), "r": (K,4) xyzw, "s": (K,3)}]
               each becomes a child node drawn K times (EXT_mesh_gpu_instancing): one door model
               placed on thousands of houses costs its geometry once.
    quantize:  KHR_mesh_quantization (SPEC 7). The node's own mesh keeps the float triangles
               (`fine`, edges shorter than `fine_edge` m, `float_materials`); the rest goes to a
               child node "<name>_q" whose translation and uniform scale dequantize its 16-bit
               positions. Normals are 8-bit, vertices welded, primitives split to keep 16-bit
               indices, instance rotations 16-bit; a piece gets 16-bit positions (its scale folded
               into each instance's SCALE and TRANSLATION) when that saves more than the SCALE
               accessor costs, and no SCALE accessor when every instance has scale 1.
    flat_angle: degrees; with quantize, triangles whose stored normals all lie within this angle of
               the face normal of their written (dequantized) corners go into primitives without
               NORMAL. Vertices that differed by normal stay apart, so a reader that computes vertex
               normals (glTF: flat when absent) gets the same flat normals back.
    """
    buf = _Buffer(pooled=quantize)
    extensions: set[str] = set()
    gl_materials: list[dict] = []
    material_index: dict = {}
    gl_images: list[dict] = []
    gl_textures: list[dict] = []
    texture_index: dict = {}

    def add_texture(name: str) -> int | None:
        """Index of texture `name`, adding its image, texture and the shared sampler once."""
        if name in texture_index:
            return texture_index[name]
        info = (images or {}).get(name)
        if info is None:
            return None
        if "bytes" in info:
            image = {"bufferView": buf.add_view(info["bytes"]), "mimeType": info.get("mime", "image/png")}
        else:
            image = {"uri": info["uri"]}
        gl_images.append(image)
        gl_textures.append({"sampler": 0, "source": len(gl_images) - 1})
        texture_index[name] = len(gl_textures) - 1
        extensions.add("KHR_texture_transform")
        return texture_index[name]

    def add_material(mat_name: str) -> int:
        if mat_name not in material_index:
            material_index[mat_name] = len(gl_materials)
            spec = materials.get(mat_name, {})
            texture = add_texture(spec["texture"]) if spec.get("texture") else None
            gl_materials.append(_material(mat_name, spec, texture))
        return material_index[mat_name]

    written: dict = {}   # (id(part), frame) -> [(attributes, indices)]: a part drawn again reuses its accessors

    def float_primitive(mat_name: str, part: dict):
        if id(part) in written:   # a lit window twin shares its dark piece's arrays (prompt 21)
            attrs, ind_acc = written[id(part)]
            return {"attributes": dict(attrs), "indices": ind_acc, "material": add_material(mat_name), "mode": 4}
        pos = np.ascontiguousarray(part["pos"], dtype=np.float32).reshape(-1, 3)
        idx = np.asarray(part["idx"]).reshape(-1)
        if len(pos) == 0 or len(idx) == 0:
            return None
        attrs = _float_attributes(buf, part, pos)
        if len(pos) < 65536:
            ind_acc = buf.add_accessor(np.ascontiguousarray(idx, dtype=np.uint16), _USHORT, "SCALAR",
                                       _ELEMENT_ARRAY_BUFFER)
        else:
            ind_acc = buf.add_accessor(np.ascontiguousarray(idx, dtype=np.uint32), _UINT, "SCALAR",
                                       _ELEMENT_ARRAY_BUFFER)
        written[id(part)] = (attrs, ind_acc)
        return {"attributes": dict(attrs), "indices": ind_acc, "material": add_material(mat_name), "mode": 4}

    def quantized_primitives(mat_name: str, part: dict, frame, key=None) -> list:
        key = (id(part), None if frame is None else (tuple(frame[0]), frame[1])) if key is None else key
        if key not in written:
            written[key] = encode(part, frame)
        return [{"attributes": dict(attrs), "indices": ind, "material": add_material(mat_name)}
                for attrs, ind in written[key]]

    def encode(part: dict, frame) -> list:
        tris = np.asarray(part["idx"], dtype=np.int64).reshape(-1, 3)
        if not len(tris) or not len(part["pos"]):
            return []
        enc = _encoded(part, frame)
        out = []
        for sel, normals in _flat_groups(part, enc, tris, frame, flat_angle):
            arrays, sub_tris = _weld([e[1] for e in enc], tris[sel])   # normals stay in the key: the split
            keep = [k for k, e in enumerate(enc) if normals or e[0] != "NORMAL"]   # layout recomputes them flat
            out += write_vertices([enc[k] for k in keep], [arrays[k] for k in keep], sub_tris)
        return out

    def write_vertices(enc: list, arrays: list, tris: np.ndarray) -> list:
        out = []
        ranges = _chunks(tris)
        for a, b in ranges:
            sub = tris[a:b]
            if len(ranges) == 1:
                used, remap = slice(None), sub
            else:
                used, remap = np.unique(sub, return_inverse=True)
            attrs = {}
            for (attr, _, comp, kind, norm, stride), arr in zip(enc, arrays):
                attrs[attr] = buf.add_accessor(arr[used], comp, kind, _ARRAY_BUFFER, minmax=attr == "POSITION",
                                               normalized=norm, stride=stride)
            ind = np.ascontiguousarray(np.asarray(remap).reshape(-1), dtype=np.uint16)
            out.append((attrs, buf.add_accessor(ind, _USHORT, "SCALAR", _ELEMENT_ARRAY_BUFFER)))
        return out

    meshes: list[dict] = []
    node = {"name": name, "translation": [float(v) for v in translation]}
    if extras:
        node["extras"] = extras
    gltf: dict = {
        "asset": {"version": "2.0", "generator": "citygen"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [node],
    }

    def add_child(child: dict) -> None:
        gltf["nodes"].append(child)
        node.setdefault("children", []).append(len(gltf["nodes"]) - 1)

    if not quantize:
        primitives = [p for p in (float_primitive(m, parts[m]) for m in sorted(parts)) if p]
        if primitives:
            node["mesh"] = len(meshes)
            meshes.append({"name": name, "primitives": primitives})
    else:
        extensions.add("KHR_mesh_quantization")
        fine, coarse = _split_fine(parts, set(float_materials), fine_edge)
        coarse = {m: {**p, "smooth": True} if p.get("col") is not None else p   # the tinted terrain keeps
                  for m, p in coarse.items()}                                  # its smooth normals
        primitives = [p for m in sorted(fine) for p in quantized_primitives(m, fine[m], None)]
        if primitives:
            node["mesh"] = len(meshes)
            meshes.append({"name": name, "primitives": primitives})
        if coarse:
            center, half = quantize_frame(np.concatenate([p["pos"] for p in coarse.values()]))
            frame = (center, half)
            prims = [p for m in sorted(coarse) for p in quantized_primitives(m, coarse[m], frame)]
            if prims:
                add_child({"name": f"{name}_q", "mesh": len(meshes), "translation": [float(v) for v in center],
                           "scale": [half] * 3, "extras": {"quantized": True}})
                meshes.append({"name": f"{name}_q", "primitives": prims})
    for inst in instances or []:
        t = np.ascontiguousarray(inst["t"], dtype=np.float64).reshape(-1, 3)
        if not len(t):
            continue
        r = np.ascontiguousarray(inst["r"], dtype=np.float64).reshape(-1, 4)
        sc = np.ascontiguousarray(inst["s"], dtype=np.float64).reshape(-1, 3)
        if not quantize:
            prims = [p for p in (float_primitive(m, inst["parts"][m]) for m in sorted(inst["parts"])) if p]
            if not prims:
                continue
            attrs = {"TRANSLATION": buf.add_accessor(t.astype(np.float32), _FLOAT, "VEC3", 0),
                     "ROTATION": buf.add_accessor(r.astype(np.float32), _FLOAT, "VEC4", 0),
                     "SCALE": buf.add_accessor(sc.astype(np.float32), _FLOAT, "VEC3", 0)}
        else:
            frame = _piece_frame(inst["parts"], sc, len(t), written)
            prims = [p for m in sorted(inst["parts"]) for p in quantized_primitives(m, inst["parts"][m], frame)]
            if not prims:
                continue
            for part in inst["parts"].values():
                written.setdefault(("frame", id(part)), frame)
            attrs = _instance_accessors(buf, t, r, sc, frame)
        add_child({"name": inst["name"], "mesh": len(meshes),
                   "extensions": {"EXT_mesh_gpu_instancing": {"attributes": attrs}}})
        meshes.append({"name": inst["name"], "primitives": prims})
        extensions.add("EXT_mesh_gpu_instancing")
    if extensions:
        gltf["extensionsUsed"] = sorted(extensions)
        if quantize:
            gltf["extensionsRequired"] = ["KHR_mesh_quantization"]
    bin_data = buf.finish()
    if meshes:
        gltf["meshes"] = meshes
        gltf["materials"] = gl_materials
        gltf["accessors"] = buf.accessors
        gltf["bufferViews"] = buf.views
    if gl_textures:
        gltf["samplers"] = [_SAMPLER]
        gltf["images"] = gl_images
        gltf["textures"] = gl_textures

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


def _flat_groups(part: dict, enc: list, tris: np.ndarray, frame, flat_angle: float) -> list:
    """[(triangle selection, write normals?)]: the flat triangles (their normals can be recomputed)
    and the rest. One group with normals when the part has none to drop or `flat_angle` is 0."""
    every = (slice(None), True)
    if flat_angle <= 0.0 or part.get("nrm") is None or part.get("smooth"):
        return [every]
    q = enc[0][1]
    pos = q.astype(np.float64) if frame is None else q[:, :3] / _I16 * frame[1] + frame[0]
    t = pos[tris]
    face = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
    area = np.linalg.norm(face, axis=1)
    face = face / np.maximum(area, 1e-30)[:, None]
    nrm = np.asarray(part["nrm"], dtype=np.float64).reshape(-1, 3)
    nrm = nrm / np.maximum(np.linalg.norm(nrm, axis=1), 1e-30)[:, None]
    dots = (nrm[tris] * face[:, None, :]).sum(axis=2)
    flat = (area > 1e-12) & np.all(dots >= np.cos(np.radians(flat_angle)), axis=1)
    if not flat.any():
        return [every]
    if flat.all():
        return [(slice(None), False)]
    return [(flat, False), (~flat, True)]


def _split_fine(parts: dict, float_materials: set, fine_edge: float) -> tuple[dict, dict]:
    """(float parts, parts to quantize): a part's `fine` triangles, its triangles with an edge under
    `fine_edge` m, and every material in `float_materials` keep float positions."""
    fine, coarse = {}, {}
    for mat, part in parts.items():
        pos = np.asarray(part["pos"], dtype=np.float64).reshape(-1, 3)
        tris = np.asarray(part["idx"], dtype=np.int64).reshape(-1, 3)
        if not len(pos) or not len(tris):
            continue
        if mat in float_materials:
            fine[mat] = part
            continue
        mask = short_edges(pos, tris, fine_edge)
        if part.get("fine") is not None:
            mask |= np.asarray(part["fine"], dtype=bool)
        for out, sel in ((fine, mask), (coarse, ~mask)):
            if sel.all():
                out[mat] = part
            elif sel.any():
                out[mat] = {**part, "idx": tris[sel].reshape(-1)}
    return fine, coarse


def _piece_frame(parts: dict, scales: np.ndarray, count: int, written: dict):
    """The quantization frame of an instanced piece, or None to keep its positions float.

    16-bit positions save 4 bytes per vertex, but their scale must ride on every instance: worth it
    when the piece needs a SCALE accessor anyway, or when its vertices outweigh 12 bytes per
    instance. A piece sharing its parts with one written before (a lit twin) follows that one."""
    seen = [written.get(("frame", id(p)), False) for p in parts.values()]
    if seen and all(s is not False for s in seen) and all(s is seen[0] for s in seen):
        return seen[0]
    pos = [np.asarray(p["pos"], dtype=np.float64).reshape(-1, 3) for p in parts.values() if len(p["pos"])]
    if not pos:
        return None
    vertices = sum(len(p) for p in pos)
    unit = bool(np.all(scales == 1.0))
    if unit and vertices * 4 <= count * 12:
        return None
    return quantize_frame(np.concatenate(pos))


def _instance_accessors(buf: _Buffer, t: np.ndarray, r: np.ndarray, sc: np.ndarray, frame) -> dict:
    """TRANSLATION (float), ROTATION (normalized SHORT) and, unless every scale is 1, SCALE (float).

    A quantized piece (`frame` = center c, half size h) is drawn at T + R (S * c) with scale S * h."""
    rq = quantize_rotations(r)
    if frame is not None:
        center, half = frame
        t = t + _rotate(rq.astype(np.float64) / _I16, sc * center)
        sc = sc * half
    attrs = {"TRANSLATION": buf.add_accessor(t.astype(np.float32), _FLOAT, "VEC3", 0),
             "ROTATION": buf.add_accessor(rq, _SHORT, "VEC4", 0, normalized=True)}
    if frame is not None or not np.all(sc == 1.0):
        attrs["SCALE"] = buf.add_accessor(sc.astype(np.float32), _FLOAT, "VEC3", 0)
    return attrs


def _rotate(q: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Rotate vectors v (K, 3) by quaternions q (K, 4) xyzw (as written, so not quite unit)."""
    xyz, w = q[:, :3], q[:, 3:4]
    tt = 2.0 * np.cross(xyz, v)
    return v + w * tt + np.cross(xyz, tt)


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


_DTYPES = {5126: np.float32, 5125: np.uint32, 5123: np.uint16, 5122: np.int16, 5121: np.uint8, 5120: np.int8}
_WIDTH = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}
_NORM = {5123: 65535.0, 5122: 32767.0, 5121: 255.0, 5120: 127.0}   # normalized integers: value / this


def accessor_array(gltf: dict, binary: bytes, index):
    """The decoded values of accessor `index` ((count, width), or (count,) for scalars): strided
    views are read element by element and normalized integers come back as floats (signed ones
    clamped at -1, as glTF says)."""
    if index is None:
        return None
    acc = gltf["accessors"][index]
    view = gltf["bufferViews"][acc["bufferView"]]
    dtype = np.dtype(_DTYPES[acc["componentType"]])
    width = _WIDTH[acc["type"]]
    start = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
    stride = view.get("byteStride", 0) or dtype.itemsize * width
    count = acc["count"]
    out = np.ndarray((count, width), dtype, buffer=binary, offset=start, strides=(stride, dtype.itemsize))
    if acc.get("normalized") and acc["componentType"] in _NORM:
        out = np.maximum(out / _NORM[acc["componentType"]], -1.0)
    else:
        out = np.array(out)
    return out if width > 1 else out.reshape(-1)


def _mesh_frames(gltf: dict) -> dict:
    """{mesh index: (translation, scale)} for meshes on child nodes that are not instanced: the
    dequantization of a quantized tile mesh. Root nodes' own placement is ignored, as before."""
    children = {c for nd in gltf.get("nodes", []) for c in nd.get("children", [])}
    out = {}
    for k, nd in enumerate(gltf.get("nodes", [])):
        if "mesh" in nd and k in children and "EXT_mesh_gpu_instancing" not in nd.get("extensions", {}):
            out[nd["mesh"]] = (np.asarray(nd.get("translation", (0.0, 0.0, 0.0)), dtype=np.float64),
                               np.asarray(nd.get("scale", (1.0, 1.0, 1.0)), dtype=np.float64))
    return out


def vertex_normals(pos: np.ndarray, idx: np.ndarray) -> np.ndarray:
    """Area-weighted vertex normals, as three.js `computeVertexNormals`: a quantized tile drops NORMAL on
    flat triangles and keeps their vertices split by normal, so this gives back their flat normals."""
    tris = np.asarray(idx, dtype=np.int64).reshape(-1, 3)
    p = np.asarray(pos, dtype=np.float64)
    face = np.cross(p[tris[:, 1]] - p[tris[:, 0]], p[tris[:, 2]] - p[tris[:, 0]])
    out = np.zeros_like(p)
    for c in range(3):
        np.add.at(out, tris[:, c], face)
    return out / np.maximum(np.linalg.norm(out, axis=1), 1e-30)[:, None]


def read_parts(path) -> dict:
    """Mesh data of a .glb as {material name: {"pos", "nrm", "uv", "col", "idx"}} in glTF axes.

    Positions of a quantized tile come back in meters (its child node's dequantization applied), and
    its primitives without NORMAL get their (flat) vertex normals computed; every other node transform
    and instance placement is ignored."""
    gltf, binary = read_glb(path)
    frames = _mesh_frames(gltf)
    flat_meshes = range(len(gltf.get("meshes", []))) if "KHR_mesh_quantization" in gltf.get("extensionsUsed", ()) \
        else ()

    def array(index):
        return accessor_array(gltf, binary, index)

    parts: dict = {}
    for k, mesh in enumerate(gltf.get("meshes", [])):
        for prim in mesh["primitives"]:
            name = gltf["materials"][prim["material"]]["name"] if "material" in prim else "default"
            a = prim["attributes"]
            part = {"pos": array(a["POSITION"]), "nrm": array(a.get("NORMAL")), "uv": array(a.get("TEXCOORD_0")),
                    "col": array(a.get("COLOR_0")), "idx": array(prim.get("indices"))}
            if k in frames:
                part["pos"] = part["pos"] * frames[k][1] + frames[k][0]
            if part["idx"] is None:
                part["idx"] = np.arange(len(part["pos"]))
            if part["nrm"] is None and "NORMAL" not in a and k in flat_meshes:
                part["nrm"] = vertex_normals(part["pos"], part["idx"])
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
