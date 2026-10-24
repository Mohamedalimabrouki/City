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
from .mesh.furniture import furniture_pieces
from .mesh.people import people_pieces
from .mesh.port import port_pieces
from .mesh.props import catalog, lit_pane
from .mesh.vehicles import vehicle_pieces
from .rng import stream

DARK, LIT = "glass_dark", "glass_lit"          # window glass by day; the twin the viewer lights at night
LIT_CATEGORIES = {"window", "balcony", "door", "kiosk"}   # pieces whose glass may be lit (not shop goods)
PLAIN = {"boat", "crane", "rail", "cargo", "railing"}   # harbor pieces and the corniche's railing (prompt 36) are
                                                       # drawn in plain palette colors: no UVs to pay for


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
    def __init__(self, seed: int, kits=(), palette: dict | None = None, trees: dict | None = None,
                 climber: dict | None = None, lit: dict | None = None, arcade: dict | None = None,
                 iron: dict | None = None, hedge: dict | None = None, vehicles: dict | None = None,
                 furniture: dict | None = None, people: dict | None = None, port: dict | None = None):
        self.pieces: dict[str, Piece] = {}
        self.materials: dict = dict(palette or {})
        table = catalog(stream(seed, "props"), seed, trees, climber, arcade, iron, hedge)
        for name, (mb, category, anchor) in table.items():
            self.pieces[name] = Piece(name, category, anchor, mb.gltf_parts(), "procedural")
        for name, parts in vehicle_pieces(seed, vehicles).items():   # parked cars (prompt 25): no lit twins
            self.pieces[name] = Piece(name, "vehicle", "ground", parts, "procedural")
        for name, (mb, category, anchor) in furniture_pieces(seed, furniture).items():   # prompt 26
            parts = mb.gltf_parts()
            if category in PLAIN:
                parts = {m: {**part, "uv": None} for m, part in parts.items()}
            self.pieces[name] = Piece(name, category, anchor, parts, "procedural")
        for name, parts in people_pieces(seed, people).items():          # prompt 28: no lit twins
            self.pieces[name] = Piece(name, "person", "ground", parts, "procedural")
        for name, (mb, category, anchor) in port_pieces(seed, port).items():       # bollards and fenders (prompt 34)
            parts = mb if isinstance(mb, dict) else mb.gltf_parts()   # boats come as parts sharing their hull
            if category in PLAIN and not isinstance(mb, dict):                         # boats, cranes, cargo (prompt 35): plain colors, no UVs
                parts = {m: {**part, "uv": None} for m, part in parts.items()}
            self.pieces[name] = Piece(name, category, anchor, parts, "procedural")
        self.panes: dict = {}   # kit piece -> (x0, x1, y0, y1, z) of its glass, glTF axes (manifest "glass")
        for kit in kits:
            folder = Path(kit) if Path(kit).is_dir() else ROOT / "kits" / kit
            if (folder / "manifest.json").is_file():
                self._load(folder)
        if LIT in self.materials:
            self._lit_pieces(float((lit or {}).get("pane_offset", 0.008)))

    def _lit_pieces(self, offset: float) -> None:
        """Lit windows (prompt 21): `<piece>_lit`, the same piece with `glass_lit` for `glass_dark`,
        and for a kit window, which has no glass material of its own, `<piece>_pane_lit`: a lit quad
        over its glass, `offset` m in front of it (behind any grille), shown only at night."""
        for name, pc in list(self.pieces.items()):
            if pc.category in LIT_CATEGORIES and DARK in pc.parts:
                parts = {(LIT if m == DARK else m): part for m, part in pc.parts.items()}
                self.pieces[name + "_lit"] = Piece(name + "_lit", pc.category, pc.anchor, parts, pc.source, pc.tags)
        for name, (x0, x1, y0, y1, z) in self.panes.items():
            pc = self.pieces[name]
            key = name + "_pane_lit"
            self.pieces[key] = Piece(key, "pane", pc.anchor, lit_pane(x0, x1, y0, y1, offset - z).gltf_parts(),
                                     pc.source, pc.tags)

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
            if "glass" in spec:
                self.panes[key] = tuple(float(v) for v in spec["glass"])


def make_kit(seed: int, cfg: dict, style: dict) -> Kit:
    """The one place a Kit is built from a seed, the config and the style (tiles, kit sheet, tools)."""
    dressing = style.get("dressing", {})
    iron = {**dressing.get("balcony_iron", {}), "sill": dressing.get("window_sill", 0.95)}
    return Kit(seed, cfg["build"].get("kits", []), style["palette"], dressing.get("trees"), dressing.get("climber"),
               dressing.get("lit"), dressing.get("arcade"), iron, dressing.get("hedge"), dressing.get("vehicles"),
               dressing.get("furniture"), dressing.get("people"), style.get("port"))
