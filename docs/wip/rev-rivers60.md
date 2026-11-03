# rev-rivers60: review of the rivers-60 commits (e7faef5, d1c5be0 on top of rivers-59 0c43b43)

Scope: citygen/build.py, city/__init__.py, city/layout.py, hydro.py, world.py, tests. No code changed.

## Good
- Determinism: no new random streams and no new draws. In `_place_settlements` the new lake
  check (world.py:192) comes after the existing `rng.uniform` draw, like the other `continue`s,
  so it only changes which spots are accepted (the expected prompt 60 shift). `unary_union` over
  the lake list keeps list order; no set iteration.
- `focus_xy` (build.py:61): `area` is never None there (build.py:286 fills it from the config).
- `land_near` (layout.py:20): `_dry_land` can already return a MultiPolygon, so `difference`
  adds no new shape type for `city_boundary`.
- `_Router.node` (world.py:279) already looks for a dry neighbor, so the one-cell lake margin
  cannot strand a settlement node.

## Findings (file:line, severity, one-line fix)
1. tests/test_hydro.py:85-86, medium: the road check tests only road vertices; a straight
   segment between two dry vertices can still cut across a lake corner. Fix:
   `assert not wet.intersects(LineString(r.coords)), r.kind`.
2. tests/test_hydro.py:81, medium (speed): the test builds a whole new 64 km world
   (`generate_world(load_config())`) instead of reusing a module or session fixture; CLAUDE.md
   allows about 2 s per new test. Fix: share one world fixture, or mark it `slow`.
3. world.py:251, low (numbers in code): the road lake margin "one routing cell" is fixed in
   code. Fix: `lake_margin` (in cells or meters) under `[roads]` in citygen/defaults.toml.
4. hydro.py:58 / world.py:144,160 / layout.py:24, low (speed): `lake_shape` rebuilds the union
   of all 41 lakes on every call (twice in `_place_settlements`, once per router, once per city
   plan). Fix: build it once in `generate_world` (or cache on the World) and pass the shape.
5. world.py:144, low: the `ok` mask tests lake cells at the grid centers X, Y, while candidates
   use PX, PY; harmless because world.py:192 re-checks the real point with the full radius.
   Fix: none needed; maybe a comment.
6. build.py:356, low: for a box build `focus.name` is still the nearest settlement's name while
   x, y are the box center; fine for the viewer, but the name can mislead. Fix: a "box" name or
   keep it and say so in the docstring.

## Left (not done in 4 minutes)
- Did not run pytest or a build here; did not check the fingerprint or the SPEC.md edit text.
