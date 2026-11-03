"""The home kit (prompt 52, SPEC 6d "The home kit"): the furniture of interiors as kit pieces `home/<piece>`.

Made on demand for one seed and style (cached), never by `kit.make_kit`: no tile, build or fingerprint
part changes. Each piece module (`kit_old`, later `kit_new` and `kit_life`) exports
`pieces(seed, cfg) -> {name: (MeshBuilder, category, anchor, spec)}`; `home_kit` turns them into
`kit.Piece`s (source `procedural`, glTF axes) and `HomeSpec`s. Parts keep UVs only for textured
materials (their palette entry names a texture); plain colors need none (HANDOFF prompt 29: bytes).
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from ..kit import Piece
from . import kit_old

MODULES = (kit_old,)
LIGHT = "light"   # category whose pieces get an `_on` twin (`lamp_glass` as `lamp_glow`)


@dataclass(frozen=True)
class HomeSpec:
    size: tuple            # (W, D, H) meters; stretch pieces have W 1.0
    foot: tuple            # plan outline in the piece frame (generator axes)
    z: tuple               # (z0, z1) over the floor, what it occupies
    use: float = 0.0       # depth in front a person needs
    top: float | None = None   # height things stand on, or None
    stretch: tuple | None = None   # [least, most] length in meters along the wall
    tris: int = 0          # triangle budget


@dataclass
class HomeKit:
    pieces: dict           # home/<piece> -> kit.Piece
    specs: dict            # home/<piece> -> HomeSpec
    materials: dict        # [palette] + [interiors.palette]
    images: dict           # embedded images of the textured materials (as `export.used_images`)


def _spec(anchor: str, s: dict) -> HomeSpec:
    w, d, h = s["size"]
    z0 = float(s.get("z0", 0.0))
    y0, y1 = (0.0, d) if anchor == "wall" else (-d / 2, d / 2)
    foot = ((-w / 2, y0), (w / 2, y0), (w / 2, y1), (-w / 2, y1))
    stretch = tuple(s["stretch"]) if s.get("stretch") else None
    return HomeSpec((w, d, h), foot, (z0, z0 + h), float(s.get("use", 0.0)), s.get("top"), stretch, int(s["tris"]))


def _parts(mb, materials: dict) -> dict:
    return {m: ({**part, "uv": None} if not materials.get(m, {}).get("texture") else part)
            for m, part in mb.gltf_parts().items()}


_CACHE: dict = {}


def home_kit(seed: int, style: dict) -> HomeKit:
    """The home kit for a seed and style, made once per process."""
    inner = style.get("interiors", {})
    key = (seed, json.dumps([style.get("palette", {}), inner], sort_keys=True, default=str))
    if key not in _CACHE:
        from .export import used_images
        materials = {**style.get("palette", {}), **inner.get("palette", {})}
        pieces, specs = {}, {}
        for module in MODULES:
            for name, (mb, cat, anchor, spec) in module.pieces(seed, inner.get("furnish", {})).items():
                key_name = f"home/{name}"
                pieces[key_name] = Piece(key_name, cat, anchor, _parts(mb, materials), "procedural")
                specs[key_name] = _spec(anchor, spec)
        for name, pc in list(pieces.items()):
            if pc.category == LIGHT:
                parts = {("lamp_glow" if m == "lamp_glass" else m): p for m, p in pc.parts.items()}
                pieces[name + "_on"] = Piece(name + "_on", pc.category, pc.anchor, parts, pc.source)
                specs[name + "_on"] = specs[name]
        images = used_images(style, seed, materials, sorted({m for pc in pieces.values() for m in pc.parts}))
        _CACHE[key] = HomeKit(pieces, specs, materials, images)
    return _CACHE[key]
