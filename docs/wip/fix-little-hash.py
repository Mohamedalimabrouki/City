"""Hash every Ain Chilel villa and maison rooms.json (as export._write_json writes it); log little() calls."""
import hashlib, json, sys, time
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from citygen.city import plan_city
from citygen.interior.context import BuildContext, city_plan, layout_of, load_build
from citygen.interior.layout import plan_interior
from citygen.interior.outside import Outside
from citygen.interior import villa as V
calls = []
real = V.little
def spy(job, region, entry, f):
    t = time.perf_counter()
    got = real(job, region, entry, f)
    calls.append((round(region.area, 1), round(region.minimum_rotated_rectangle.area, 1), got is not None, round(time.perf_counter() - t, 2)))
    return got
V.little = spy
ctx = load_build(Path(sys.argv[2]), log=lambda m: None)
city = "Ain Chilel"
s = next(s for s in ctx.world.settlements if s.name.lower() == city.lower())
if not any(p.settlement is s for p in ctx.plans):
    ctx = BuildContext(ctx.world, [plan_city(ctx.world, s)], s)
plan = city_plan(ctx, city)
style = ctx.world.style
n = 0
for k, b in enumerate(plan.buildings):
    if b.kind not in ("house", "domed", "apartments", "villa"):
        continue
    lay = layout_of(plan, b, style)
    if lay not in ("villa", "maison"):
        continue
    before = len(calls)
    t = time.perf_counter()
    interior = plan_interior(Outside(ctx, plan, k), style)
    h = hashlib.sha256(json.dumps(interior.to_json(), separators=(",", ":")).encode()).hexdigest()[:16]
    n += 1
    print(k, lay, interior.layout, h, round(time.perf_counter() - t, 2), calls[before:], flush=True)
print("total", n, "little calls", len(calls), flush=True)
