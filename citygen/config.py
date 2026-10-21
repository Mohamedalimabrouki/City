"""Settings: built-in defaults, then an optional world file, then command-line overrides.

The style pack (styles/<name>.toml) is loaded separately: settings say what
to build, the style says what it looks like.
"""
from __future__ import annotations

import copy
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = Path(__file__).with_name("defaults.toml")

# Small and fast: used by tests and by `build --quick`.
QUICK = {
    "world": {"size_km": 20},
    "settlements": {"population_scale": 0.22},
    "build": {"center_radius": 520.0},
}


def deep_merge(base: dict, extra: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in extra.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def load_config(world_file=None, overrides: dict | None = None, quick: bool = False) -> dict:
    cfg = tomllib.loads(DEFAULTS.read_text(encoding="utf-8"))
    if quick:
        cfg = deep_merge(cfg, QUICK)
    if world_file:
        cfg = deep_merge(cfg, tomllib.loads(Path(world_file).read_text(encoding="utf-8")))
    if overrides:
        cfg = deep_merge(cfg, overrides)
    return cfg


def load_style(name: str) -> dict:
    path = Path(name)
    if path.suffix != ".toml":
        path = ROOT / "styles" / f"{name}.toml"
    return tomllib.loads(path.read_text(encoding="utf-8"))
