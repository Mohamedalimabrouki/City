"""The city from a build folder (SPEC 6c): world, plans, kit, ground and dressers, as the build had them.

`load_build` rebuilds the world from the settings a build stored in its `summary.json` and takes the
plans from the build's plan cache (prompt 5), so an interior costs seconds, not a new build.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import shapely

from ..build import load_or_plan, select_area
from ..buildkey import build_key
from ..city.dressing import Dresser
from ..city.ground import Ground
from ..city.life import HOUSING
from ..export.lore import slug
from ..kit import make_kit
from ..world import generate_world
from . import LAYOUTS, InteriorError

TRADITIONAL = ("medina", "village")   # districts whose houses are dars, compact or small houses
NO_SETTINGS = ("This build was made before interiors existed (its summary.json has no settings). Build it "
               "again with the same command, for example python -m citygen build --quick, then run interior again.")
STALE = ("The code, style or kits changed since this build was made: the interior follows today's code, and "
         "the build's tiles may not match it until you build again.")


class BuildContext:
    """World and plans of one build, with the kit, the ground and one `Dresser` per city made lazily,
    exactly as `TileContext` makes them (so the bridge replays the tile's own pieces)."""

    def __init__(self, world, plans, focus, folder=None):
        self.world, self.plans, self.focus = world, list(plans), focus
        self.folder = None if folder is None else Path(folder)
        self.warnings: list = []
        self._kit = self._ground = None
        self._dressers: dict = {}

    @property
    def kit(self):
        if self._kit is None:
            self._kit = make_kit(self.world.seed, self.world.cfg, self.world.style)
        return self._kit

    @property
    def ground(self) -> Ground:
        if self._ground is None:
            self._ground = Ground(self.world, self.plans)
        return self._ground

    def index(self, plan) -> int:
        """Position of `plan` in the build's plans (by identity: comparing plans field by field is slow)."""
        return next(i for i, p in enumerate(self.plans) if p is plan)

    def dresser(self, plan) -> Dresser:
        i = self.index(plan)
        if i not in self._dressers:
            if not self.world.cfg["tiles"].get("dressing", True):
                raise InteriorError("This build has no street dressing ([tiles] dressing = false), so its houses "
                                    "have no doors or windows to match. Build it again with dressing on.")
            self._dressers[i] = Dresser(self.world, plan, self.kit, self.ground)
        return self._dressers[i]


def load_build(folder, log=print) -> BuildContext:
    """The world and plans of the build in `folder`, from its summary's settings and its plan cache."""
    folder = Path(folder)
    try:
        summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise InteriorError(f"{folder} holds no finished build (no readable summary.json). Build one first, for "
                            "example python -m citygen build --quick, or name a build folder with --folder.") from None
    settings = summary.get("settings")
    if not settings:
        raise InteriorError(NO_SETTINGS)
    world = generate_world(settings)
    _, focus, needed = select_area(world, summary.get("area") or settings["build"]["area"])
    key = build_key(settings, [s.id for s in needed])
    ctx = BuildContext(world, [], focus, folder)
    if key != summary.get("build_key"):
        ctx.warnings.append(STALE)
        log(f"warning: {STALE}")
    ctx.plans = [load_or_plan(world, s, folder / "cache", key[:12], False, log) for s in needed]
    return ctx


def city_plan(ctx: BuildContext, name: str | None = None):
    """The plan of the city `name` (any case, or its slug); the build's focus city without a name."""
    if name is None:
        return next((p for p in ctx.plans if p.settlement is ctx.focus), ctx.plans[0])
    want = name.strip().lower()
    for p in ctx.plans:
        if p.settlement.name.lower() == want or slug(p.settlement.name) == want:
            return p
    names = ", ".join(p.settlement.name for p in ctx.plans)
    raise InteriorError(f"This build has no city called {name!r}. Its cities: {names}. Name one of them with --city.")


def exterior_wall(style: dict, district: str) -> float:
    """Thickness of an exterior wall in a district of this kind (`[interiors.walls]`)."""
    walls = style.get("interiors", {}).get("walls", {})
    return float(walls.get("exterior", {}).get(district, walls.get("exterior_fallback", 0.3)))


def layout_of(plan, b, style: dict) -> str | None:
    """The layout of dwelling b (SPEC 6c "Who gets one"); None for a building that gets no interior."""
    district = plan.districts[b.district].kind
    if b.kind == "domed":
        return "koubba"
    if b.kind == "villa":
        return "villa"
    if b.kind == "apartments":
        return "slab" if district == "modern" else "colonial"   # the dresser's own split (Dresser._is_slab)
    if b.kind != "house":
        return None
    if district not in TRADITIONAL:
        return "maison"
    if b.footprint.interiors:
        return "dar"
    inner = b.footprint.buffer(-exterior_wall(style, district), join_style="mitre")
    least = float(style.get("interiors", {}).get("compact", {}).get("min_area", 35.0))
    return "compact" if inner.area >= least else "small"


def resolve(ctx: BuildContext, plan, spec) -> int:
    """Building number k from a number or `pick:<layout>[:<floors>]` (the dwelling of that layout nearest
    the settlement center, the lower number on a tie)."""
    spec = str(spec).strip()
    city = plan.settlement.name
    if spec.isdigit():
        k = int(spec)
        if k >= len(plan.buildings):
            raise InteriorError(f"{city} has buildings No. 0 to No. {len(plan.buildings) - 1} in this build, "
                                f"not No. {k}.")
        b = plan.buildings[k]
        if b.kind not in HOUSING:
            raise InteriorError(f"No. {k} in {city} is a {b.kind.replace('_', ' ')}: only dwellings have an "
                                "interior (houses, domed houses, apartment blocks and villas).")
        return k
    parts = spec.split(":")
    if parts[0] != "pick" or len(parts) not in (2, 3) or (len(parts) == 3 and not parts[2].isdigit()):
        raise InteriorError(f"{spec!r} is not a building: give its number (the viewer's card shows it as No. k) "
                            "or pick:<layout>[:<floors>], for example pick:dar or pick:slab:4.")
    layout, floors = parts[1], int(parts[2]) if len(parts) == 3 else None
    if layout not in LAYOUTS:
        raise InteriorError(f"There is no layout called {layout!r}. Layouts: {', '.join(LAYOUTS)}.")
    centers = shapely.get_coordinates(shapely.centroid([b.footprint for b in plan.buildings]))
    d = np.hypot(centers[:, 0] - plan.settlement.x, centers[:, 1] - plan.settlement.y)
    for k in np.lexsort((np.arange(len(d)), d)).tolist():
        b = plan.buildings[k]
        if (b.kind in HOUSING and (floors is None or int(b.floors) == floors)
                and layout_of(plan, b, ctx.world.style) == layout):
            return k
    with_floors = f" with {floors} floors" if floors is not None else ""
    raise InteriorError(f"{city} has no {layout} dwelling{with_floors} in this build.")
