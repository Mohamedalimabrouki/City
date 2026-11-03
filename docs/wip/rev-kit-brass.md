# rev-kit-brass: review of `git diff e871984..HEAD -- citygen tests styles` (3 November, 20:57 UTC)

Only `citygen/interior/kit_old.py` changed (tray_brass, tea_set, ibrik, pots_stack). No test or style change.

## Findings (file:line, severity, one-line fix)
1. kit_old.py:622 and kit_old.py:641, medium: `_tube`'s `half` is the two half sizes of a
   rectangular section, not start and end radii (citygen/mesh/furniture.py:297). So (0.009, 0.003) and
   (0.012, 0.004) make flat blades of even width (18 x 6 mm, 24 x 8 mm), not the "tapering spouts" the
   comments say. Fix: keep the section square and taper by chaining 2 or 3 `_tube` pieces of shrinking
   size (or a thin cone along the spout); correct the comments.
2. kit_old.py:622, low: the teapot spout's root moved to 0.05 m from the pot's axis at z 0.035, where the
   pot wall is about 0.047 m, so the open root end stands 0 to 6 mm off the wall (a visible slot). The
   old root (0.045 at z 0.05, wall 0.052) was buried. Fix: start the root inside the wall, for example
   (px - 0.04, py, 0.04).
3. kit_old.py:606, medium: the tray rim is one surface facing inward and up (`_lathe` normal (dz, -dr)),
   with no outside. Made steeper (about 55 deg instead of 33 deg), the near rim now faces away from any
   eye lower than about 55 deg, so seen from across a room (about 20 deg) it is culled and the near edge
   disappears: the opposite of the docstring's aim. Fix: add the rim's outside (a second, outward-facing
   lathe from (r - 0.018, 0.0) to (r, h)) and raise the budget at kit_old.py:42 from 48 to about 80, or
   go back to the 0.04 slope.
4. kit_old.py:640, low (old, now more visible): the ibrik's mouth is open and one-sided; the wider flare
   (0.052 m) shows more of the culled inside, so from above you see through the neck. Fix: a short inner
   wall facing in (for example from (0.048, h) to (0.0, 0.30)), still within the 120 budget.
5. kit_old.py:1021-1024, fine: `ri` lies exactly on the upper bowl's wall (0.0977 m at z 0.08), the glazed
   ring and the glazed hollow face up, nothing crosses. Triangles by hand: 108 + 42 = 150, exactly the
   budget at kit_old.py:69 (no room for any later change; info).
6. Determinism, fine: no new draws, no new streams; `rng` use in tea_set and pots_stack is unchanged.
7. Materials, fine: only brass, copper, terracotta and glaze_green (styles/maghreb.toml:1881), all
   already used by these pieces. Piece names and sizes in the kit table are unchanged; spout tips stay
   inside their boxes (ibrik tip x 0.169 < 0.175, z 0.342 < 0.40).
8. Tests, missing: nothing tests a spout's taper or a one-sided rim, so 1 and 3 pass the suite. Suggest a
   test that the tray has some outward-facing rim triangle (normal with a positive radial part at r > 0.28).

## Left
Triangle counts are by hand (not run); SPEC 6 text not re-read line by line (sizes unchanged).
