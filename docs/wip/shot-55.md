# shot-55: contact sheet of the 18 life pieces (kit_life.py) and the 7 light `_on` twins

Picture: `docs/wip/shot-55.png` (scratchpad `hg_render.py`, seed 42, z-buffer, view from above and
in front; back faces are drawn dark). No code changed.

## Limits of this picture
- The renderer uses only the base color, not the emission, so every `_on` twin looks exactly like its
  off piece. The glow of the `_on` twins is NOT checked here: look at them in the viewer or Blender.
- The view is from above, so the undersides of the ceiling pieces (ceiling_lamp diffuser) are not seen.

## Piece by piece
- fanous (0.99 m, 128 t): reads well as a hanging lantern on a rod; brass cap and foot, cream glass. OK.
- lantern_table (0.39 m, 98 t): brass cap and foot, cream glass drum. OK, a bit like a pepper mill;
  a top ring or a pierced brass band would make it a lantern.
- ceiling_lamp (0.38 m, 40 t): flat octagonal dish. The top (ceiling side) is dark, fine because it is
  never seen; check from below that the diffuser is white.
- chandelier (0.76 m, 312 t): brass ring, 8 arms, cups. Reads well. The cup tops are dark: if those are
  open cones seen from inside, they look see-through in glTF unless the material is double sided. Check.
- neon (1.07 m, 20 t): thin cream tube. OK.
- bulb_bare (0.34 m, 24 t): cord and bulb. OK.
- lamp_bedside (0.41 m, 52 t): shade, stem, white foot. Reads well. Dark top: same check as the
  chandelier (open shade + single-sided faces = see-through from above).
- pot_geranium (0.52 m, 80 t): terracotta pot, green dome, only 3 tiny red blooms. Fix: 5 to 7 bigger
  red blooms spread over the dome, or it reads as a plain bush.
- pot_basil (0.30 m, 44 t): the leaves are a 4-sided pyramid; reads as a cone, not basil. Fix: a rounder
  ball (more sides) or 2 to 3 overlapping balls.
- plates_stack (0.25 m, 24 t): one solid white octagonal drum; reads as a cake, not plates. Fix: separate
  plates (small gaps or a darker rim line between them, slight radius steps).
- fruit_bowl (0.29 m, 64 t): white bowl, one orange and one red fruit. A dark crescent shows inside the
  bowl: the inner wall or bottom is missing or faces the wrong way. Fix: give the bowl an inner surface
  and a bottom; 3 to 5 fruits would read better.
- oil_bidon (0.36 m, 35 t): yellow jerrycan with cap and handle. Reads well. OK.
- pot_jasmine (1.07 m, 128 t): tall green spindle on a small pot; the white flowers are 1 or 2 specks,
  so it reads as a cypress topiary. Fix: many more white dots, a looser shape, maybe a cane; the pot
  looks small for a 1 m plant.
- vase_flowers (0.36 m, 48 t): pale vase; the blooms FLOAT above the neck with a clear gap and no
  stems. Fix (clear bug): add thin green stems from the neck, or lower the blooms onto it.
- photo_frame (0.42 m, 12 t): dark frame, flat light-brown picture. OK as a wall frame; if it is meant
  to stand on a table it needs a back stand (none visible).
- khomsa (0.19 m, 18 t): brass hand of 5 separate blocks; reads as a hand, a bit like a glove or comb.
  Could round the palm bottom and make the two outer "thumbs" symmetric and curled out.
- shoes (0.42 m, 40 t): pair of brown blocks on black soles. Reads as shoes at room scale; blocky toe.
- schoolbag (0.45 m, 28 t): blue body, red front pocket, top handle. Reads well. OK.

## Most worth fixing first
1. vase_flowers floating blooms (no stems). 2. fruit_bowl dark hole inside. 3. plates_stack reads as one
drum. 4. pot_basil pyramid. 5. check double-sided on open shades and cups (lamp_bedside, chandelier).
6. Check the `_on` glow in the viewer (not visible here).

## Left
Nothing of the brief is left except the `_on` glow check, which needs the viewer.
