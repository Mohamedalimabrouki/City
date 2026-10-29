"""City-wide survey of interior plans: how many dwellings of each group pass `rooms.check`, and why the
others fail (the lead's review tool since prompts 46-47; tests only see a fixture, this sees every house).

    python tools/interior_survey.py [--folder BUILD] [--city NAME] [--groups g,g] [--limit N]

Groups: dar, compact, small (by the layout each plan really got, a fallback included), koubba, colonial,
slab, villa, maison, and shop (every house with a shop front). Prints per group the pass count, crashes,
the stair warnings and the slowest plan, then the failure kinds (numbers dropped) and the first failing
buildings. --city plans any settlement of the world (Ain Chilel holds the quick world's villas).
Default folder: the latest build. The old-town and new-district counts of prompts 46-47 are in the WORKLOG.
"""
from __future__ import annotations

import argparse
import collections
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

GROUPS = ("dar", "compact", "small", "koubba", "colonial", "slab", "villa", "maison", "shop")


def survey(folder: Path, city: str | None, groups: tuple, limit: int) -> None:
    from citygen.city import plan_city
    from citygen.interior import rooms as R
    from citygen.interior.context import BuildContext, city_plan, layout_of, load_build
    from citygen.interior.layout import plan_interior
    from citygen.interior.outside import Outside
    ctx = load_build(folder, log=lambda m: None)
    if city:
        s = next((s for s in ctx.world.settlements if s.name.lower() == city.lower()), None)
        if s is None:
            raise SystemExit(f"No settlement called {city!r} in this world.")
        if not any(p.settlement is s for p in ctx.plans):
            ctx = BuildContext(ctx.world, [plan_city(ctx.world, s)], s)
    plan = city_plan(ctx, city)
    style = ctx.world.style
    front = ctx.dresser(plan).front_of
    count, fails, crashes = collections.Counter(), collections.Counter(), collections.defaultdict(list)
    kinds, first, warns = collections.Counter(), collections.defaultdict(list), collections.Counter()
    slowest: dict = {}
    for k, b in enumerate(plan.buildings):
        if b.kind not in ("house", "domed", "apartments", "villa"):
            continue
        lay = layout_of(plan, b, style)
        shop = b.kind == "house" and front(k)[2] == "shop"
        if not (shop and "shop" in groups) and lay not in groups:
            continue
        t = time.perf_counter()
        try:
            interior = plan_interior(Outside(ctx, plan, k), style)
        except Exception as e:                            # a crash is a finding, not the end of the survey
            crashes["shop" if shop else lay].append((k, type(e).__name__))
            continue
        took = time.perf_counter() - t
        group = "shop" if shop and "shop" in groups else interior.layout
        if count[group] >= limit:
            continue
        count[group] += 1
        if took > slowest.get(group, (0.0, -1))[0]:
            slowest[group] = (took, k)
        warns[group] += any("ladder" in w or "no stair" in w for w in interior.warnings)
        bad = R.check(interior)
        if bad:
            fails[group] += 1
            first[group].append(k)
            for p in bad:
                kinds[(group, " ".join(w for w in p.split() if not any(c.isdigit() for c in w)))] += 1
    for g in GROUPS:
        if count[g] or crashes[g]:
            took, k = slowest.get(g, (0.0, -1))
            print(f"{g}: {count[g] - fails[g]}/{count[g]} pass, {len(crashes[g])} crashes, {warns[g]} with a "
                  f"ladder warning, slowest {took:.2f} s (No. {k})")
    print("--- failure kinds")
    for (g, p), n in kinds.most_common(30):
        print(f"{n:5d} {g}: {p}")
    for g in GROUPS:
        if first[g] or crashes[g]:
            print(f"{g} failing: {first[g][:20]}" + (f"  crashes: {crashes[g][:10]}" if crashes[g] else ""))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="City-wide survey of interior plans (rooms.check by group).")
    ap.add_argument("--folder", help="a build folder (default: the latest build)")
    ap.add_argument("--city", help="a settlement of the world (default: the build's focus city)")
    ap.add_argument("--groups", default=",".join(GROUPS), help="comma-separated groups (default: all)")
    ap.add_argument("--limit", type=int, default=10**9, help="at most this many dwellings per group")
    args = ap.parse_args(argv)
    if args.folder:
        folder = Path(args.folder)
    else:
        found = sorted((ROOT / "output").glob("*/summary.json"), key=lambda p: p.stat().st_mtime)
        if not found:
            raise SystemExit("No built world found in output/. Run: python -m citygen build --quick")
        folder = found[-1].parent
    survey(folder, args.city, tuple(g for g in args.groups.split(",") if g), args.limit)


if __name__ == "__main__":
    main()
