"""Styles per region (prompt 94): a world file can give one settlement, or every settlement of a
kind, its own style pack instead of the country's.

    [styles.settlements]          # by name (as `citygen list` shows it) or by id number
    "Sidi Amor" = "steampunk"
    [styles.kinds]                # every settlement of a kind
    village = "steampunk"

A name or id beats a kind, and a kind beats `[world] style`. A regional pack is merged over the
country's pack, so it lists only what differs (a palette, roofs, dressing, names...).

What stays global: the terrain, the roads, where settlements stand and their names (the country's
style places and names them), the ground tint and the shared texture images. What follows the
city's style: its plan (`CityContext.style`), its dressing and kit, its palette and roofs, and the
names of its quarters and landmarks (a regional pack with a `[names]` table names them its way).

Names never collide where styles meet: the country style keeps today's names, and every other
style's materials and kit pieces are namespaced, `steampunk/brass` and `steampunk/tree_broadleaf`,
in tiles, in the kit sheet and in the fingerprint's `kit/*` parts.
"""
from __future__ import annotations

import copy
from pathlib import Path

from .config import deep_merge, load_style


def assigned_style(cfg: dict, settlement) -> str:
    """The style name one settlement is built in."""
    table = cfg.get("styles", {})
    by_name = {str(k).strip().lower(): str(v) for k, v in table.get("settlements", {}).items()}
    for key in (str(settlement.id), settlement.name.strip().lower()):
        if key in by_name:
            return by_name[key]
    return str(table.get("kinds", {}).get(settlement.kind, cfg["world"]["style"]))


def style_label(name: str) -> str:
    """The namespace of a style: its pack's file name without `.toml` (`steampunk`)."""
    return Path(name).stem


def regional_names(cfg: dict) -> list:
    """Every style the world file names besides the country's, sorted."""
    table = cfg.get("styles", {})
    names = {str(v) for v in table.get("settlements", {}).values()} | {str(v) for v in table.get("kinds", {}).values()}
    return sorted(names - {str(cfg["world"]["style"])})


def regional_style(country: dict, name: str) -> dict:
    """A regional pack merged over the country's pack."""
    return deep_merge(country, load_style(name))


class StyledWorld:
    """The world as one city sees it: everything shared, but `style` is the city's own."""

    def __init__(self, world, name: str, style: dict):
        self._world = world
        self.style_name = name
        self.style = style

    def __getattr__(self, attr):
        return getattr(self._world, attr)


def namespaced(kit, prefix: str):
    """A copy of `kit` whose pieces and materials are all called `prefix/<name>`."""
    out = copy.copy(kit)
    ns = f"{prefix}/"
    out.materials = {ns + m: spec for m, spec in kit.materials.items()}
    out.pieces = {}
    for name, piece in kit.pieces.items():
        parts = {ns + m: part for m, part in piece.parts.items()}
        out.pieces[ns + name] = copy.copy(piece)
        out.pieces[ns + name].name = ns + name
        out.pieces[ns + name].parts = parts
    out.panes = {ns + name: pane for name, pane in getattr(kit, "panes", {}).items()}
    return out


def world_kit(seed: int, cfg: dict, country: dict, names=None):
    """The country's kit plus every regional style's kit, namespaced (kit sheet, fingerprint)."""
    from .kit import make_kit                      # imported here: the kit builds on mesh code
    kit = make_kit(seed, cfg, country)
    for name in (regional_names(cfg) if names is None else names):
        ns = namespaced(make_kit(seed, cfg, regional_style(country, name)), style_label(name))
        kit.pieces.update(ns.pieces)
        kit.panes.update(ns.panes)
        kit.materials = {**kit.materials, **ns.materials}
    return kit
