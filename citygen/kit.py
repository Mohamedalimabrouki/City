"""Kits: 3D pieces (doors, windows, lanterns, goods...) that dress the generated city.

The generator's own procedural pieces (mesh/props.py) are always there. A kit folder
kits/<name>/ (manifest.json plus one .glb per piece, glTF axes: +Y up, front facing -Z, origin
at the anchor) adds pieces made elsewhere, for example extracted from the Tounes Rush game.
Kit pieces are named "<kit>/<piece>", e.g. "tounes/door_sbs_blue", so they never replace a
procedural piece. Pieces are stored ready to write (glTF axes), so tiles only add instance transforms.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path

import numpy as np

from .config import ROOT
from .mesh.gltf import read_parts
from .mesh.props import catalog
from .rng import stream


@dataclass
class Piece:
    name: str
    category: str   # door, window, lamp, pot, plant, awning, shop, goods, wall_goods, roof, cat, ...
    anchor: str     # "wall": bottom-center on the wall face; "ground": bottom-center on the ground
    parts: dict     # {material: {"pos", "nrm", "uv", "col", "idx"}} in glTF axes
    source: str     # "procedural" or the kit name
    tags: tuple = ()

    @property
    def triangles(self) -> int:
        return sum(len(p["idx"]) // 3 for p in self.parts.values())

    @cached_property
    def bounds(self) -> tuple:
        """(min, max) corners in glTF axes, meters."""
        pos = np.concatenate([p["pos"] for p in self.parts.values()])
        return pos.min(axis=0), pos.max(axis=0)

    @property
    def height(self) -> float:
        return float(self.bounds[1][1] - self.bounds[0][1])

    @property
    def width(self) -> float:
        return float(self.bounds[1][0] - self.bounds[0][0])

    @property
    def bottom(self) -> float:
        """Lowest point relative to the anchor (negative for pieces hanging from it)."""
        return float(self.bounds[0][1])

    @property
    def top(self) -> float:
        """Highest point above the anchor."""
        return float(self.bounds[1][1])


class Kit:
    def __init__(self, seed: int, kits=(), palette: dict | None = None, trees: dict | None = None):
        self.pieces: dict[str, Piece] = {}
        self.materials: dict = dict(palette or {})
        for name, (mb, category, anchor) in catalog(stream(seed, "props"), seed, trees).items():
            self.pieces[name] = Piece(name, category, anchor, mb.gltf_parts(), "procedural")
        for kit in kits:
            folder = Path(kit) if Path(kit).is_dir() else ROOT / "kits" / kit
            if (folder / "manifest.json").is_file():
                self._load(folder)

    def _load(self, folder: Path) -> None:
        manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        for name, spec in manifest.get("materials", {}).items():
            self.materials.setdefault(name, spec)
        for name, spec in manifest.get("pieces", {}).items():
            path = folder / spec["file"]
            if not path.is_file():
                continue
            remap = spec.get("materials_map", {})   # e.g. a canvas drawn with the lamp-glow material
            parts = {remap.get(m, m): part for m, part in read_parts(path).items()}
            for part in parts.values():
                if part.get("col") is not None and part["col"].shape[1] == 3:
                    part["col"] = np.concatenate([part["col"], np.ones((len(part["col"]), 1))], axis=1)
            key = f"{folder.name}/{name}"
            self.pieces[key] = Piece(key, spec.get("category", "ground_prop"), spec.get("anchor", "ground"), parts,
                                     folder.name, tuple(spec.get("tags", [])))


