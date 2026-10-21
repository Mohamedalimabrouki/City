"""A preview of every kit piece in a labeled grid, viewable with the 3D viewer (python -m citygen kit-sheet)."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from .config import load_config, load_style
from .export.lore import write_json
from .kit import Kit
from .mesh.builder import MeshBuilder, add_cap, extrude, rectangle
from .mesh.gltf import write_glb


def kit_sheet(out_dir, kits=("tounes",), seed: int = 42, columns: int = 8, spacing: float = 4.0) -> Path:
    style = load_style(load_config()["world"]["style"])
    kit = Kit(seed, kits, style["palette"], style.get("dressing", {}).get("trees"))
    names = sorted(kit.pieces, key=lambda n: (kit.pieces[n].source != "procedural", kit.pieces[n].category, n))
    rows = (len(names) + columns - 1) // columns
    width, depth = columns * spacing, rows * spacing
    mb = MeshBuilder()
    add_cap(mb, rectangle(width / 2, depth / 2, width + 4, depth + 4, 0.0), 0.0, "urban_ground")
    instances = []
    for k, name in enumerate(names):
        x, y = (k % columns + 0.5) * spacing, depth - (k // columns + 0.5) * spacing
        piece = kit.pieces[name]
        if piece.anchor == "wall":  # a short wall behind wall pieces, so they read as mounted
            extrude(mb, rectangle(x, y - 0.15, 3.2, 0.3, 0.0), 0.0, 3.2, "lime_white", "roof_white")
        lift = max(0.0, -piece.bottom)   # hanging pieces (lamps, awnings) shown above the ground
        instances.append({"name": name, "parts": piece.parts, "t": np.array([[x, lift, -y]]),
                          "r": np.array([[0.0, 0.0, 0.0, 1.0]]), "s": np.ones((1, 3))})
    folder = Path(out_dir) / "tiles"
    folder.mkdir(parents=True, exist_ok=True)
    size = write_glb(folder / "sheet.glb", mb.gltf_parts(), kit.materials, name="kit", instances=instances)
    write_json(folder / "index.json", {
        "format": "citygen-tiles/1", "seed": seed, "world_name": "Kit sheet", "tile_size": max(width, depth) + 8,
        "focus": {"x": width / 2, "y": depth / 2, "z": 0.0, "name": f"{len(names)} pieces"},
        "views": _views(width, depth, rows, spacing),
        "tiles": [{"i": 0, "j": 0, "file": "sheet.glb", "x0": 0, "y0": 0, "triangles": 0, "bytes": size}]})
    (Path(out_dir) / "pieces.txt").write_text(
        "\n".join(f"{k:3d} {n:28s} {kit.pieces[n].category:12s} {kit.pieces[n].source:11s} "
                  f"{kit.pieces[n].triangles:6d} tris" for k, n in enumerate(names)) + "\n", encoding="utf-8")
    return Path(out_dir)


def _views(width: float, depth: float, rows: int, spacing: float) -> dict:
    """Pieces face north, so every camera stands north of what it shows: one overview, then two rows at a time."""
    views = {"sheet": {"cam": [width / 2, depth * 1.5, depth * 0.9], "look": [width / 2, depth * 0.45, 0.0]}}
    for r in range(0, rows, 2):
        y = depth - (r + 1) * spacing
        views[f"rows{r}"] = {"cam": [width / 2, y + width * 0.55, width * 0.42], "look": [width / 2, y, 0.8]}
    return views
