# Prompt 55 step 2, more life pieces (helper furn-55b; worktree /tmp/claude-501/furn-55b, branch wip/furn-55b)
Built on wip/furn-55 0996596. 3 November, 20:52-20:59 UTC.

## Done (added to `citygen/interior/kit_life.py`, sizes and tris as the SPEC 6d table)
- `brass_plate` (wall, z 1.50-2.00, 24 tris), `clock_wall` (wall, z 1.80-2.12, 28 tris, two black hands):
  wall discs, lathed then turned by `kit_old.SWAP_YZ` / `_moved` (helper `_wall_disc`).
- `birdcage` (anchor `ceiling`, z0 -0.55, 86 tris): blue tray, white body and dome drawn closed (no bars yet).
- `slippers` (floor, 24 tris): blue soles and a brown band on top (the band's sides are open).
- `water_pack` (floor, 58 tris): a `glass_inner` block and six blue cone caps.
- `tests/test_homekit.py` `test_home_pieces_life`: the wall discs face the room and are round.

## Left (from the 6d table)
`khomsa_blue` (`glaze_blue` variant: renaming `khomsa` needs a care for its users), `frame_verse` (needs the
`verse` weave, step 2 of the notes), `mergoum_wall` (UV quad as `kit_old._rug`), `curtain` (anchor `window`,
stretch), `books_stack` (`spines` UVs), `bread_basket` (`hasira`, `bread`), `blanket_folded` (`mink`),
`laundry_line` (stretch), `broom` (`hasira` UVs), `pots_hanging` (check the `copper` / `copper_ware` rename
of wip/fix-materials first). Then steps 2-6 of docs/wip/furn-55.md.

## To look at
None of these pieces is looked at on the kit sheet yet (`python -m citygen kit-sheet --home`).

## Checks
- Full `pytest -q`: 164 passed, 11 deselected (75 s, with other helpers running).
- `build --quick`, then `tools/fingerprint.py compare before55b --allow ""` (before = this commit with the
  base `kit_life.py`): 282 parts, 0 changed (the home kit is never in the build).
