"""`python -m citygen interior BUILDING`: one dwelling's interior folder from a build (SPEC 6c "Command")."""
from __future__ import annotations

import time
from pathlib import Path

from ..export.lore import slug
from .context import city_plan, load_build, resolve
from .export import write_folder
from .layout import plan_interior
from .outside import Outside


def make_interior(folder, building, city: str | None = None, out=None, log=print, ctx=None) -> Path:
    """Write the interior of `building` (a number or `pick:<layout>[:<floors>]`) of `city` in the build at
    `folder`; returns the folder written (default `<folder>/interiors/<city slug>-<k>/`). `ctx`: a
    `BuildContext` already loaded for that folder (the viewer keeps one per build)."""
    t0 = time.perf_counter()
    folder = Path(folder)
    ctx = ctx or load_build(folder, log)
    plan = city_plan(ctx, city)
    k = resolve(ctx, plan, building)
    outside = Outside(ctx, plan, k)
    interior = plan_interior(outside, ctx.world.style)
    for warning in interior.warnings:
        log(f"warning: {warning}")
    out = Path(out) if out else folder / "interiors" / f"{slug(plan.settlement.name)}-{k}"
    write_folder(interior, outside, out)
    log(f"interior {k} ({interior.layout}, {_count(interior.floors, 'floor')}, {_count(len(interior.rooms), 'room')}) "
        f"in {time.perf_counter() - t0:.1f} s -> {out}")
    return out


def _count(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"
