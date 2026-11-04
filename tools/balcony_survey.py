"""What stands behind every open balcony of a settlement (the facade round): the rails and slab balconies of
a whole city, each with the piece behind it, the way `tools/interior_survey.py` walks every house.

    python tools/balcony_survey.py [--folder BUILD] [--city NAME]

Reads the placements exactly as the tiles get them (`interior.outside.Outside`). Prints balconies by what
stands behind them: a door-window, a plain window (must be 0), the slab balcony's own door, or nothing, then
door-windows with no rail in front (must be 0), mashrabiyas, and the blocks with a slab balcony and plain
windows on the same wall column (the claim of the worklog: must be 0).
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


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="What stands behind every open balcony of a city.")
    ap.add_argument("--folder", help="a build folder (default: the latest build)")
    ap.add_argument("--city", help="a settlement of the world (default: the build's focus city)")
    args = ap.parse_args(argv)
    from citygen.interior.context import city_plan, load_build
    if args.folder:
        folder = Path(args.folder)
    else:
        found = sorted((ROOT / "output").glob("*/summary.json"), key=lambda p: p.stat().st_mtime)
        if not found:
            raise SystemExit("No built world found in output/. Run: python -m citygen build --quick")
        folder = found[-1].parent
    ctx = load_build(folder, log=lambda m: None)
    counts, examples = survey(ctx, city_plan(ctx, args.city))
    for name, n in sorted(counts.items()):
        print(f"{n:6d}  {name}" + (f"   buildings {examples[name][:8]}" if examples[name] else ""))


if __name__ == "__main__":
    main()
