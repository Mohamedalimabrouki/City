"""Fingerprint of a build: which parts changed after a code edit.

  python tools/fingerprint.py save NAME [FOLDER]
  python tools/fingerprint.py compare NAME [FOLDER] [--allow "tiles/*,kit/tree_*"]

FOLDER defaults to the latest build. Fingerprints live in output/checks/fp-NAME.json.
`compare` exits with code 1 when a part changed that --allow does not cover.
"""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from citygen.config import load_config, load_style  # noqa: E402
from citygen.kit import make_kit  # noqa: E402

CHECKS = Path("output/checks")
SKIP_KEYS = ("build_key",)
BLEND = re.compile(r"\.blend\d*$")   # Ali's Blender file and its backups change when he saves them


def _latest(folder) -> Path:
    if folder:
        return Path(folder)
    found = sorted(Path("output").glob("*/summary.json"), key=lambda p: p.stat().st_mtime)
    if not found:
        sys.exit("No built world found in output/. Run: python -m citygen build")
    return found[-1].parent


def _timing(key: str) -> bool:
    return key == "seconds" or key.endswith("_seconds") or key in SKIP_KEYS


def _clean(obj):
    """JSON data without timing keys and build keys."""
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items() if not _timing(k)}
    if isinstance(obj, list):
        return [_clean(v) for v in obj]
    return obj


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def _json_digest(obj) -> str:
    return _digest(json.dumps(_clean(obj), sort_keys=True, separators=(",", ":")).encode())


def _part(h: str, **detail) -> dict:
    return {"h": h, "d": detail}


def _plan_parts(city: str, path: Path) -> dict:
    plan = json.loads(path.read_text(encoding="utf-8"))
    return {f"plan/{city}/{k}": _part(_json_digest(v), n=len(v) if hasattr(v, "__len__") else 1)
            for k, v in plan.items()}


def _kit_parts(world: dict) -> dict:
    """One part per kit piece; the kit is made once per process for a seed and style (tests call this often)."""
    return {name: _part(p["h"], **p["d"]) for name, p in _kit_digests(world["seed"], world["style"]).items()}


@lru_cache(maxsize=4)
def _kit_digests(seed: int, style: str) -> dict:
    kit = make_kit(seed, load_config(), load_style(style))
    out = {}
    for name in sorted(kit.pieces):
        piece = kit.pieces[name]
        h = hashlib.sha256()
        for material in sorted(piece.parts):
            h.update(material.encode())
            for key in sorted(piece.parts[material]):
                h.update(key.encode())
                array = piece.parts[material][key]
                if array is not None:
                    h.update(str(array.dtype).encode() + np.ascontiguousarray(array).tobytes())
        out[f"kit/{name}"] = _part(h.hexdigest()[:16], triangles=piece.triangles)
    return out


def _file_part(path: Path) -> dict:
    data = path.read_bytes()
    if path.suffix == ".json":
        return _part(_json_digest(json.loads(data)), bytes=len(data))
    return _part(_digest(data), bytes=len(data))


def _tile_parts(folder: Path) -> dict:
    index = folder / "tiles" / "index.json"
    tris = {}
    if index.is_file():
        tris = {t["file"]: t.get("triangles") for t in json.loads(index.read_text(encoding="utf-8")).get("tiles", [])}
    out = {}
    for path in sorted((folder / "tiles").glob("*")):
        if path.name == "index.json":
            out["tiles/index"] = _file_part(path)
        elif path.is_file() and not path.name.startswith("."):   # Finder's .DS_Store is not the build
            part = _file_part(path)
            part["d"]["triangles"] = tris.get(path.name)
            out[f"tiles/{path.name}"] = part
    return out


def fingerprint(folder: Path) -> dict:
    world = json.loads((folder / "world.json").read_text(encoding="utf-8"))
    parts = {"world": _file_part(folder / "world.json")}
    if (folder / "gazetteer.md").is_file():
        parts["gazetteer"] = _file_part(folder / "gazetteer.md")
    for plan in sorted((folder / "cities").glob("*/plan.json")):
        parts.update(_plan_parts(plan.parent.name, plan))
    parts.update(_tile_parts(folder))
    parts.update(_kit_parts(world))
    for path in sorted((folder / "maps").glob("*")):
        if path.is_file() and not path.name.startswith("."):
            parts[f"maps/{path.name}"] = _file_part(path)
    covered = {"world.json", "gazetteer.md", "summary.json"}
    for path in sorted(folder.rglob("*")):
        rel = path.relative_to(folder)
        top = rel.parts[0]
        if (not path.is_file() or "cache" in rel.parts or top in ("maps", "tiles", "checks")
                or str(rel) in covered or path.name.startswith(".") or BLEND.search(path.name)
                or (top == "cities" and path.name == "plan.json")):
            continue
        parts[f"files/{rel.as_posix()}"] = _file_part(path)
    return {"world": world["name"], "seed": world["seed"], "parts": parts}


def _describe(old: dict, new: dict) -> str:
    bits = []
    for key in sorted(set(old["d"]) | set(new["d"])):
        a, b = old["d"].get(key), new["d"].get(key)
        if a != b:
            bits.append(f"{key} {a} -> {b}")
    return ", ".join(bits) or "content differs"


def compare(old: dict, new: dict) -> list[tuple[str, str]]:
    """List of (part, text) for every changed, added or removed part."""
    changes = []
    for key in sorted(set(old) | set(new)):
        if key not in new:
            changes.append((key, "removed"))
        elif key not in old:
            changes.append((key, "added"))
        elif old[key]["h"] != new[key]["h"]:
            changes.append((key, _describe(old[key], new[key])))
    return changes


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["save", "compare"])
    ap.add_argument("name")
    ap.add_argument("folder", nargs="?")
    ap.add_argument("--allow", default=None, help="comma-separated fnmatch patterns of parts allowed to change")
    args = ap.parse_args(argv)
    path = CHECKS / f"fp-{args.name}.json"
    now = fingerprint(_latest(args.folder))
    if args.cmd == "save":
        CHECKS.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(now, sort_keys=True), encoding="utf-8")
        print(f"saved {len(now['parts'])} parts -> {path}")
        return 0
    if not path.is_file():
        sys.exit(f"No fingerprint {path}. Run: python tools/fingerprint.py save {args.name}")
    before = json.loads(path.read_text(encoding="utf-8"))
    if (before["world"], before["seed"]) != (now["world"], now["seed"]):
        sys.exit(f"Different world: saved {before['world']} seed {before['seed']}, "
                 f"now {now['world']} seed {now['seed']}")
    changes = compare(before["parts"], now["parts"])
    for key, text in changes:
        print(f"{key}: {text}")
    total = len(set(before["parts"]) | set(now["parts"]))
    print(f"{total} parts, {len(changes)} changed")
    if args.allow is None:
        return 0
    patterns = [p.strip() for p in args.allow.split(",") if p.strip()]
    bad = [k for k, _ in changes if not any(fnmatch.fnmatchcase(k, p) for p in patterns)]
    if bad:
        print(f"NOT ALLOWED to change: {len(bad)} parts, first: {bad[0]}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
