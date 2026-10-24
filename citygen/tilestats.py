"""Where the bytes of each 3D tile go (`python -m citygen stats --tiles`).

Reads every tile listed in tiles/index.json and splits its .glb size into categories: the JSON
chunk, terrain (the tinted ground grid: primitives with COLOR_0), the rest of the tile's own mesh
by material, each instanced piece's mesh, the instance transforms, and embedded textures. An
accessor drawn twice (lit window twins share their dark piece's arrays) is counted once.
"""
from __future__ import annotations

import json
from pathlib import Path

from .mesh.gltf import _DTYPES, _WIDTH, read_glb


def tile_bytes(path) -> dict:
    """{"total", "json", "terrain", "mesh": {material: bytes}, "pieces": {name: bytes},
    "instances": {name: bytes}, "counts": {name: instances}, "textures"} of one .glb file."""
    gltf, binary = read_glb(path)
    data = Path(path).read_bytes()
    json_len = int.from_bytes(data[12:16], "little")
    views = gltf.get("bufferViews", [])
    accessors = gltf.get("accessors", [])
    seen: set = set()

    def size(acc) -> int:
        """Bytes of one accessor: count x stride (quantized tiles pool many accessors in one view)."""
        if acc is None or acc in seen:
            return 0
        seen.add(acc)
        a = accessors[acc]
        element = _DTYPES[a["componentType"]]().itemsize * _WIDTH[a["type"]]
        return int(a["count"]) * int(views[a["bufferView"]].get("byteStride", element))

    def mesh_bytes(mesh: dict, out: dict | None, by_material: bool, name: str = "") -> int:
        total = 0
        for prim in mesh["primitives"]:
            n = size(prim.get("indices")) + sum(size(a) for a in prim["attributes"].values())
            total += n
            if by_material:
                mat = gltf["materials"][prim["material"]]["name"] if "material" in prim else "default"
                key = "terrain" if "COLOR_0" in prim["attributes"] else mat
                out[key] = out.get(key, 0) + n
        return total

    out = {"total": len(data), "json": 8 + json_len, "terrain": 0, "mesh": {}, "pieces": {}, "instances": {},
           "counts": {}, "textures": 0}
    meshes = gltf.get("meshes", [])
    for node in gltf.get("nodes", []):
        if "mesh" not in node:
            continue
        inst = node.get("extensions", {}).get("EXT_mesh_gpu_instancing")
        if inst is None:
            mesh_bytes(meshes[node["mesh"]], out["mesh"], True)
            continue
        name = node.get("name", f"mesh_{node['mesh']}")
        out["pieces"][name] = out["pieces"].get(name, 0) + mesh_bytes(meshes[node["mesh"]], None, False)
        attrs = inst["attributes"]
        out["instances"][name] = out["instances"].get(name, 0) + sum(size(a) for a in attrs.values())
        out["counts"][name] = out["counts"].get(name, 0) + accessors[attrs["TRANSLATION"]]["count"]
    out["terrain"] = out["mesh"].pop("terrain", 0)
    out["textures"] = sum(int(views[im["bufferView"]]["byteLength"]) for im in gltf.get("images", [])
                          if "bufferView" in im)
    return out


def _kb(n: int) -> str:
    return f"{n / 1000:9,.1f}"


def _rows(title: str, items: dict, top: int, extra: dict | None = None) -> list[str]:
    lines = [f"  {title} (KB):"]
    ranked = sorted(items.items(), key=lambda kv: (-kv[1], kv[0]))
    for name, n in ranked[:top]:
        more = f"  x{extra[name]:,d}" if extra and name in extra else ""
        lines.append(f"    {name:34s}{_kb(n)}{more}")
    rest = ranked[top:]
    if rest:
        lines.append(f"    {f'{len(rest)} others':34s}{_kb(sum(n for _, n in rest))}")
    return lines


def tiles_report(folder, tile: str | None = None, top: int = 15) -> str:
    """A table of every tile's bytes by category (heaviest first), then the detail of one tile
    (`tile`, e.g. "tile_13_23", default the heaviest): its own mesh by material and its pieces."""
    folder = Path(folder)
    index = json.loads((folder / "tiles" / "index.json").read_text(encoding="utf-8"))
    entries = index["tiles"] if isinstance(index, dict) else index
    stats = {e["file"][:-4]: tile_bytes(folder / "tiles" / e["file"]) for e in entries}
    order = sorted(stats, key=lambda k: (-stats[k]["total"], k))
    head = f"{'tile':14s}{'total':>10s}{'json':>9s}{'terrain':>9s}{'mesh':>10s}{'pieces':>9s}{'instances':>10s}" \
           f"{'textures':>9s}   (KB)"
    lines = [head]
    for name in order:
        s = stats[name]
        lines.append(f"{name:14s}{s['total'] / 1000:10,.1f}{s['json'] / 1000:9,.1f}{s['terrain'] / 1000:9,.1f}"
                     f"{sum(s['mesh'].values()) / 1000:10,.1f}{sum(s['pieces'].values()) / 1000:9,.1f}"
                     f"{sum(s['instances'].values()) / 1000:10,.1f}{s['textures'] / 1000:9,.1f}")
    lines.append(f"{len(order)} tiles, {sum(s['total'] for s in stats.values()) / 1e6:,.2f} MB in all")
    lods = [(e["lod1"]["bytes"] / e["bytes"], e["file"][:-4], e["lod1"]) for e in entries if "lod1" in e]
    if lods:                                     # lod1 tiles (prompt 40): their share of the full tile
        worst = max(lods)
        lines.append(f"lod1: {sum(lod['bytes'] for _, _, lod in lods) / 1e6:,.2f} MB, "
                     f"{sum(lod['triangles'] for _, _, lod in lods):,} triangles; median "
                     f"{sorted(r for r, _, _ in lods)[len(lods) // 2]:.1%}, worst {worst[0]:.1%} of its full tile "
                     f"({worst[1]}, {worst[2]['bytes'] / 1000:,.1f} KB)")
    name = tile or (order[0] if order else None)
    if name in stats:
        s = stats[name]
        lines.append("")
        lines.append(f"{name}: {s['total'] / 1000:,.1f} KB")
        lines += _rows("tile mesh by material", s["mesh"], top)
        lines += _rows("piece meshes", s["pieces"], top, s["counts"])
        lines += _rows("instance transforms", s["instances"], top, s["counts"])
    return "\n".join(lines)
