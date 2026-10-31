"""The build key: one SHA-256 that changes whenever anything a build's content depends on changes.

A finished plan or tile is reused only when its key equals the key of the current build.
Simple and safe: any edit to any code file, setting, style, kit or planned city changes the key,
and so does a new version of Python or of a library the code uses. Interiors (SPEC 6c) are made on
demand from a finished build, so their code (`citygen/interior/`) and their style tables (`[interiors]`)
never make a build stale; nor does `citygen/view.py` (the viewer's web server).
"""
from __future__ import annotations

import hashlib
import json
import platform
from importlib import metadata
from pathlib import Path

from .config import ROOT, load_style

CODE = Path(__file__).resolve().parent
NOT_CONTENT = ("output", "workers", "tiles_per_worker", "area")   # [build] settings that never change what a tile holds
LIBRARIES = ("numpy", "scipy", "shapely", "contourpy", "pillow")   # a new version may change the numbers
NOT_BUILD_CODE = ("interior", "view.py")   # code a build never runs (interiors are made on demand; the viewer server)
NOT_BUILD_STYLE = ("interiors",)    # style tables a build never reads


def _code_hash() -> str:
    h = hashlib.sha256()
    for path in sorted(CODE.rglob("*.py")):
        rel = path.relative_to(CODE)
        if rel.parts[0] in NOT_BUILD_CODE:
            continue
        h.update(rel.as_posix().encode())
        h.update(path.read_bytes())
    return h.hexdigest()


def _style_hash(name: str) -> str:
    """The parsed style without the tables a build never reads, so editing them keeps every build current."""
    style = {k: v for k, v in load_style(name).items() if k not in NOT_BUILD_STYLE}
    return hashlib.sha256(json.dumps(style, sort_keys=True).encode()).hexdigest()


def _kit_folder(kit: str) -> Path:
    return Path(kit) if Path(kit).is_dir() else ROOT / "kits" / kit


def _kit_hash(kit: str) -> str:
    folder = _kit_folder(kit)
    h = hashlib.sha256()
    for path in sorted([folder / "manifest.json", *folder.rglob("*.glb")]):
        if path.is_file():
            h.update(path.relative_to(folder).as_posix().encode())
            h.update(path.read_bytes())
    return h.hexdigest()


def _versions() -> list:
    return [platform.python_version(), *(metadata.version(name) for name in LIBRARIES)]


def build_key(cfg: dict, settlement_ids) -> str:
    """Key of a build with these merged settings and these planned settlements (by id)."""
    settings = {k: v for k, v in cfg.items() if k != "build"}
    settings["build"] = {k: v for k, v in cfg["build"].items() if k not in NOT_CONTENT}
    parts = {
        "settings": json.dumps(settings, sort_keys=True, separators=(",", ":")),
        "style": _style_hash(cfg["world"]["style"]),
        "kits": [_kit_hash(k) for k in cfg["build"].get("kits", [])],
        "code": _code_hash(),
        "versions": _versions(),
        "settlements": sorted(int(i) for i in settlement_ids),
    }
    return hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()
