rev-fix-brass (3 November): review of wip/fix-brass (HEAD d30fd69 is notes only, so the code commits 738c555 + efe1223 against b376aed). No code changed here.
Checked by building both pieces for 40 seeds: tray_brass 80 tris (budget 80), pots_stack 180 (budget 180); 0 flipped triangles (winding agrees with the normals), 0 degenerate; no new rng draws (determinism kept); the tray skin faces out, the bowl hollow faces up and in, the hollow stays inside the lower bowl (no poke-through).
Findings:
- citygen/interior/kit_old.py:1021, low: with 8 sides the bowls get a vertex at 90 degrees, so the stack now reaches y = 0.18 + 0.13 = 0.31 (up to 0.318 with the jitter) past the 0.30 half-depth (6 sides reached 0.299). tests/test_homekit.py:36 only checks the total extent (0.02 tolerance), so it passes. Fix: `by = 0.165 + j[3, 1]` (or r1 = 0.12). The jars' x reach (0.16 + 0.14 + jitter = 0.308) is older and the same kind.
- docs/SPEC.md:2028 and :2055, low: the kit table still says 48 and 150 triangles; make them 80 and 180 at the merge.
- tests, low: nothing locks in the fix itself (the tray rim's outer skin facing out, the bowl's open hollow); a small test of the tray's outermost faces having outward normals would.
- Numbers: the new shape constants (0.006, r2 * 0.5, z2 + 0.03) live in code like every other kit_old shape number; fine by the kit's convention.
Left: not looked at in the viewer or Blender; full pytest and quick build not run here.
