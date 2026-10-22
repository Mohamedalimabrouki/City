"""The build key: one SHA-256 that changes whenever anything a build's content depends on changes.

A finished plan or tile is reused only when its key equals the key of the current build.
Simple and safe: any edit to any code file, setting, style, kit or planned city changes the key.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from .config import ROOT, style_path

CODE = Path(__file__).resolve().parent
NOT_CONTENT = ("output", "workers", "area")   # [build] settings that never change what a tile holds


def _code_hash() -> str:
    h = hashlib.sha256()
    for path in sorted(CODE.rglob("*.py")):
        h.update(path.relative_to(CODE).as_posix().encode())
        h.update(path.read_bytes())
    return h.hexdigest()


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


def build_key(cfg: dict, settlement_ids) -> str:
    """Key of a build with these merged settings and these planned settlements (by id)."""
    settings = {k: v for k, v in cfg.items() if k != "build"}
    settings["build"] = {k: v for k, v in cfg["build"].items() if k not in NOT_CONTENT}
    parts = {
        "settings": json.dumps(settings, sort_keys=True, separators=(",", ":")),
        "style": hashlib.sha256(style_path(cfg["world"]["style"]).read_bytes()).hexdigest(),
        "kits": [_kit_hash(k) for k in cfg["build"].get("kits", [])],
        "code": _code_hash(),
        "settlements": sorted(int(i) for i in settlement_ids),
    }
    return hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()
