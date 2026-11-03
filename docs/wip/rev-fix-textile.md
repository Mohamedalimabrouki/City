# rev-fix-textile (review of HEAD aa45f74 "WIP fix-textile": the cushion's cord and one-cover dome)

Checked with a script on the cushion (0.55 x 0.18 x 0.42, velvet blue).

Findings (file:line, severity, fix):
1. citygen/interior/kit_old.py:359 and :389, MEDIUM: the cord's crown normals point back to the wall.
   6 of the 16 front-band triangles have crown vertex normals at cos -0.3 to -0.7 to their face
   (face normal y +0.92). `_smooth` weights by area, and the back band (edge sunk 1.2 r/seam = 15-20 mm
   in, wide and flat, facing -y) outweighs the narrow front band. The visible front of the cord shades dark.
   Fix: give the cord its own round normals (each point minus the cord axis point, f = 1 and y = seam on
   the same ring index, normalized; `_smooth` would need a `nrm=` argument), or make the section symmetric
   (back edge as deep as the front one).
2. kit_old.py:357, low: the crown leaves the piece's box: x to 0.2765 (w/2 = 0.275), z 0.518..0.942 (box
   0.52..0.94). Cushions edge to edge would cross by 3 mm. Inside the test's 0.02 tolerance.
   Fix: hw, hh smaller by r, or accept.
3. kit_old.py:357, low: `grow = 1 + r / min(hw, hh)` scales evenly, so the cord stands 6.5 mm out on the
   sides and 5 mm on top and bottom. Fix if it matters: offset along the outline normal.
4. kit_old.py:358, low: the sink factor 1.2 is a number in code (could be `cord_sink` in
   `[interiors.furnish.textiles.cushion]`); `fy - seam` divides by zero if a style sets face_at = 0 or
   dome = seam.
5. tests, low: no test names the cushion; `_check_table` checks only budget (72 = 72, no margin), box and
   UV presence, so finding 1 passes. Suggest a kit-wide test: every smooth triangle's vertex normals
   within 90 degrees of its face normal.

Fine: 72 triangles = budget (cover 32, cord 32, tassels 8); all cover and cord windings face out (the 3
inward faces are tassel sides, as before); normals unit and finite; no rng (determinism unchanged); the
old keys `cord` and `cord_depth` are gone from code and toml with no other users; the tassel heads now sit
on the cord at the corners.

Left: HEAD~1 (the mattress UVs) not reviewed; pytest not run here (fix-textile reported 14 pass).
