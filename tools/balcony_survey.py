"""What stands behind every open balcony of a settlement (the facade round): the rails and slab balconies of
a whole city, each with the piece behind it, the way `tools/interior_survey.py` walks every house.

    python tools/balcony_survey.py [--folder BUILD] [--city NAME] [--rooms] [--every N] [--groups g,g]

Reads the placements exactly as the tiles get them (`interior.outside.Outside`). Prints balconies by what
stands behind them: a door-window, a plain window (must be 0), the slab balcony's own door, or nothing, then
door-windows with no rail in front (must be 0), mashrabiyas, and the blocks with a slab balcony and plain
windows on the same wall column (the claim of the worklog: must be 0).

--rooms plans the interiors instead and prints the room behind every door-window and slab door, by group and
kind of door: a bath or a wc must be 0 on every plan, a colonial hall, couloir or droj is a rate to read.
--every N takes 1 plan in N (a whole city's colonial blocks and slabs take about 18 minutes), --groups only
those layouts. --city villas is the biggest town with villas, as in `tools/interior_survey.py`.
"""
from __future__ import annotations

import argparse
import collections
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

RAILS = ("balcony_iron", "balcony_iron_long", "balconnet_iron")
ORDER = ("salon", "chambre", "salle_a_manger", "cuisine", "hall", "couloir", "droj", "sdb", "wc", "bit_el_ma")
WET = ("sdb", "wc", "bit_el_ma")           # the rooms that must never stand behind a balcony door
WAYS = ("hall", "couloir", "droj")         # the rooms a colonial block should keep off them where it can


def along(p, q) -> tuple:
    """(meters along p's wall, meters out of it, height) of q from p."""
    dx, dy = q.x - p.x, q.y - p.y
    return dx * math.cos(p.yaw) + dy * math.sin(p.yaw), -dx * math.sin(p.yaw) + dy * math.cos(p.yaw), q.z - p.z


def behind(kit, rail, pieces: list) -> list:
    """The window and door-window pieces within a rail's width on its wall, at its height."""
    half = kit.pieces[rail.piece].width / 2 * rail.stretch
    found = []
    for q in pieces:
        s, out, dz = along(rail, q)
        if q is rail or kit.pieces[q.piece].category not in ("window", "balcony") or q.piece in RAILS:
            continue
        if abs(s) < half and abs(out) < 0.05 and abs(dz) < 1.5 and abs(math.sin(q.yaw - rail.yaw)) < 0.02:
            found.append(q)
    return found


def survey(ctx, plan) -> tuple:
    """(counts, examples, per-building door-windows) over every dressed building of `plan`."""
    from citygen.interior.outside import Outside
    counts, examples = collections.Counter(), collections.defaultdict(list)
    for k, b in enumerate(plan.buildings):
        if b.kind not in ("house", "domed", "apartments", "villa"):
            continue
        o = Outside(ctx, plan, k)
        ps, kit = o.placements, o.kit
        names = [p.piece[:-4] if p.piece.endswith("_lit") else p.piece for p in ps]
        doors = [p for p, n in zip(ps, names) if n.startswith("window_door_")]
        for p, n in zip(ps, names):
            if n in RAILS:
                got = behind(kit, p, ps)
                door = sum(q.piece.startswith("window_door_") for q in got)
                plain = len(got) - door
                need = 2 if n == "balcony_iron_long" else 1
                what = ("door-window" if door == need and not plain else "plain window" if plain else
                        "nothing" if not got else "too few door-windows")
                counts[f"{n}: {what}"] += 1
                if what != "door-window":
                    examples[f"{n}: {what}"].append(k)
            elif n == "balcony_slab":
                got = behind(kit, p, ps)
                counts["balcony_slab: own door" + (", plain window too" if got else "")] += 1
                if got:
                    examples["balcony_slab: plain window too"].append(k)
            elif kit.pieces[p.piece].category == "balcony" and not n.startswith("window_door_"):
                counts["mashrabiya (closed, on its wall)"] += 1
        rails = [p for p, n in zip(ps, names) if n in RAILS]
        for d in doors:
            if not any(d in behind(kit, r, ps) for r in rails):
                counts["door-window with no rail"] += 1
                examples["door-window with no rail"].append(k)
    return counts, examples


def door_kind(piece: str) -> str:
    """The kind of balcony opening a facade piece is."""
    name = piece[:-4] if piece.endswith("_lit") else piece
    return ("door-window" if name.startswith("window_door_") else "slab door" if name == "balcony_slab" else
            "closed (mashrabiya)")


def behind_rooms(interior) -> list:
    """(kind of door, type of the room behind it) of every balcony opening of a planned home."""
    types = {r.id: r.type for r in interior.rooms}
    return [(door_kind(o.piece), types.get(o.rooms[0], "no room")) for o in interior.openings
            if o.kind == "balcony" and o.piece]


def room_survey(ctx, plan, every: int, groups: tuple) -> tuple:
    """(counts by (group, door kind, room), example buildings, plans read, crashes) over 1 plan in `every`."""
    from citygen.interior.context import layout_of
    from citygen.interior.layout import plan_interior
    from citygen.interior.outside import Outside
    style = ctx.world.style
    counts, examples = collections.Counter(), collections.defaultdict(list)
    seen, plans, crashes = 0, collections.Counter(), []
    for k, b in enumerate(plan.buildings):
        if b.kind not in ("house", "domed", "apartments", "villa"):
            continue
        lay = layout_of(plan, b, style)
        if groups and lay not in groups:
            continue
        seen += 1
        if (seen - 1) % every:
            continue
        try:
            interior = plan_interior(Outside(ctx, plan, k), style)
        except Exception as e:                            # a crash is a finding, not the end of the survey
            crashes.append((k, type(e).__name__))
            continue
        plans[interior.layout] += 1
        for kind, room in behind_rooms(interior):
            counts[(interior.layout, kind, room)] += 1
            if room in WET + WAYS:
                examples[(interior.layout, kind, room)].append(k)
    return counts, examples, plans, crashes


def print_rooms(counts, examples, plans, crashes) -> None:
    """One line per group and kind of door: the rooms behind them, the bad ones with their buildings."""
    rank = {t: i for i, t in enumerate(ORDER)}
    for group, kind in sorted({key[:2] for key in counts}):
        got = {r: n for (g, d, r), n in counts.items() if (g, d) == (group, kind)}
        total = sum(got.values())
        wet, ways = sum(got.get(t, 0) for t in WET), sum(got.get(t, 0) for t in WAYS)
        row = "  ".join(f"{t} {n}" for t, n in sorted(got.items(), key=lambda v: (rank.get(v[0], 99), v[0])))
        print(f"{group} {kind} ({plans[group]} plans): {total} doors, wet {wet}, ways {ways} "
              f"({100 * ways / max(total, 1):.1f}%): {row}")
        for t in WET + WAYS:
            if examples[(group, kind, t)]:
                print(f"    {t}: buildings {sorted(set(examples[(group, kind, t)]))[:10]}")
    print("plans read: " + "  ".join(f"{g} {n}" for g, n in sorted(plans.items())) +
          (f"   CRASHES {crashes[:10]}" if crashes else ""))


def city_of(ctx, city: str | None) -> tuple:
    """(context, plan) of `--city`: a city of the build, `villas`, or any other settlement of the world."""
    from citygen.city import plan_city
    from citygen.interior.context import BuildContext, city_plan, villa_town
    if city == "villas":
        town = villa_town(ctx.world)
        if town is None:
            raise SystemExit("No town of this world has villas.")
        ctx, city = BuildContext(ctx.world, [town], town.settlement), town.settlement.name
        print(f"the villa town: {city}")
    elif city:
        s = next((s for s in ctx.world.settlements if s.name.lower() == city.lower()), None)
        if s is None:
            raise SystemExit(f"No settlement called {city!r} in this world.")
        if not any(p.settlement is s for p in ctx.plans):
            ctx = BuildContext(ctx.world, [plan_city(ctx.world, s)], s)
    return ctx, city_plan(ctx, city)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="What stands behind every open balcony of a city.")
    ap.add_argument("--folder", help="a build folder (default: the latest build)")
    ap.add_argument("--city", help="a settlement of the world, or villas for the biggest town with villas "
                                   "(default: the build's focus city)")
    ap.add_argument("--rooms", action="store_true", help="plan the interiors: the room behind every balcony door")
    ap.add_argument("--every", type=int, default=1, help="with --rooms: 1 plan in N (default: all)")
    ap.add_argument("--groups", default="", help="with --rooms: comma-separated layouts (default: all)")
    args = ap.parse_args(argv)
    from citygen.interior.context import load_build
    if args.folder:
        folder = Path(args.folder)
    else:
        found = sorted((ROOT / "output").glob("*/summary.json"), key=lambda p: p.stat().st_mtime)
        if not found:
            raise SystemExit("No built world found in output/. Run: python -m citygen build --quick")
        folder = found[-1].parent
    ctx = load_build(folder, log=lambda m: None)
    ctx, plan = city_of(ctx, args.city)
    if args.rooms:
        print_rooms(*room_survey(ctx, plan, args.every, tuple(g for g in args.groups.split(",") if g)))
        return
    counts, examples = survey(ctx, plan)
    for name, n in sorted(counts.items()):
        print(f"{n:6d}  {name}" + (f"   buildings {examples[name][:8]}" if examples[name] else ""))


if __name__ == "__main__":
    main()
