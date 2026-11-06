"""World-wide check of the street graph (prompt 70): how much of each settlement's street length its largest
connected part holds. The tests only see the quick world; this plans every settlement of a world.

    python tools/street_survey.py [--quick] [--workers N]

Prints the settlements of more than one part, then the totals. The 64 km world takes about 10 minutes with 4 workers.
A part stays apart only where the ribbons really do not meet: that is a gap in the plan, not in the graph.
"""
from __future__ import annotations

import argparse
import collections
import multiprocessing
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from citygen.city import plan_city  # noqa: E402
from citygen.config import load_config  # noqa: E402
from citygen.export.streets import street_graph  # noqa: E402
from citygen.world import generate_world  # noqa: E402

WORLD = {}


def parts(nodes: list, edges: list) -> collections.Counter:
    """{root node: street length} of each connected part of a street graph."""
    parent = list(range(len(nodes)))

    def root(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    for _k, _line, a, b in edges:
        parent[root(a)] = root(b)
    out = collections.Counter()
    for _k, line, a, _b in edges:
        out[root(a)] += line.length
    return out


def survey(job: tuple) -> tuple:
    quick, i = job
    if quick not in WORLD:
        WORLD[quick] = generate_world(load_config(quick=quick))
    world = WORLD[quick]
    s = world.settlements[i]
    plan = plan_city(world, s)
    nodes, edges = street_graph(plan.streets, float(world.cfg["street_graph"]["grid"]))
    p = parts(nodes, edges)
    total = sum(p.values())
    return s.name, s.kind, len(plan.streets), len(p), max(p.values(), default=0.0) / total if total else 1.0


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="The street graph of every settlement of a world.")
    ap.add_argument("--quick", action="store_true", help="the quick world (default: the 64 km world)")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args(argv)
    count = len(generate_world(load_config(quick=args.quick)).settlements)
    with multiprocessing.get_context("fork").Pool(args.workers) as pool:
        rows = pool.map(survey, [(args.quick, i) for i in range(count)], chunksize=1)
    built = [r for r in rows if r[2]]
    for name, kind, streets, n, share in sorted(built, key=lambda r: r[4]):
        if n > 1:
            print(f"{name} ({kind}): {streets} streets in {n} parts, the largest {100 * share:.2f}%")
    print(f"{len(rows)} settlements, {len(built)} with streets: {sum(r[3] == 1 for r in built)} in one part, "
          f"{sum(r[4] < 0.995 for r in built)} under 99.5%")


if __name__ == "__main__":
    main()
