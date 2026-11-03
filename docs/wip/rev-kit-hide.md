# rev-kit-hide: review of `git diff e871984..HEAD -- citygen tests styles` (kit-hide: hidoura fleece, net pile)

Reviewed in 4 minutes; read the diff only (no build, no snapshot, no test run).

## Findings (file:line, severity, one-line fix)
1. citygen/interior/kit_old.py:1065, MEDIUM (UV). Net pile UV v = -(y + z): on the heap's north (+y) side
   the slope is about dz/dy = -1 (ring 1 to 2: -1.06, ring 2 to 3 ridges: -1.57 for size 1.00 x 0.80 x 0.35),
   so v hardly changes there (or runs backwards) and the diamond meshes smear into stripes or mirror.
   Fix: v = -(y - sign(y) * z) (always grows with the slope length), or a radial UV; check in a snapshot
   from the north.
2. styles/maghreb.toml:1900 vs styles/maghreb.toml:113, MEDIUM (material clash, check). There are two
   materials named `net_green`: the city's (boats, citygen/mesh/boats.py:383,399,447: "#3E6B57", no
   texture) and the interior one now "#FFFFFF" + texture "net". If any export or tools/make_blend.py
   merges materials by name, the boats' nets turn white or the heap loses its image. Fix: rename the
   interior one (for example `net_heap`) or confirm the names never meet in one file.
3. citygen/interior/kit_old.py:858, LOW (z-fight). The hidoura's hem now starts at RUG_Z + 0.0015 (was
   + 0.002); when it lies on another rug (top at RUG_Z) 1.5 mm may flicker at a distance. Fix: keep the
   lowest edge at RUG_Z + 0.002 (uniform(0.002, 0.004)).
4. citygen/interior/kit_old.py:61, LOW (budget). Registry still says 24 triangles; the piece now makes
   22 (14 outline + 4 joins + 4 crown). Fine as a budget, but if it is meant as the count, set 22.

## Checked and fine
- Hidoura geometry: outline order is monotonic in angle, so `near` (quadrant of each outer point)
  only steps to the next inner point; no fold-over; the z-cross check keeps every face up; top-view
  UV (x, -y) suits a 2 cm hide; texture_size 0.25 m gives about 1 cm locks.
- Determinism: the hidoura and net pile draw only from their own piece `rng`; the images use
  `stream(seed, "texture", name)` (citygen/interior/weave.py:417); no set order, no `random`.
- Both images wrap: `cells` meshes across 256 px (any whole number works), locks on tiled noise.
- Numbers are in styles/maghreb.toml; no em dash.
- tests/test_homekit.py:74: the two new images join the wrap and same-bytes checks (they can fail).

## Left
- No test checks the hidoura/net UVs or that the net's v grows with slope; no snapshot looked at.
