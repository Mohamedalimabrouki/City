# Tounes Rush kit

51 street pieces from the game **Tounes Rush** (claude.ai artifact "Tounes Rush AAA V5.2"), so the
game and the generated cities share one look: studded Sidi Bou Said and medina doors, window
grilles, shutters and birdcage bays, mashrabiya balconies, lamps and lanterns, pots, climbers and a
bougainvillea cascade, a date palm, awnings, rugs, market goods, a handcart, a delivery moped,
arches and souk gates. `contact_sheet.png` shows them all with a 1 m ruler.

How they were made: the game's own three.js builders were run once in a headless browser and
each piece was saved with flat normals and vertex colors (linear) on four shared materials
(`tr_std`, `tr_shiny`, `tr_metal`, `tr_glow`). Every piece faces -Z (the street), +Y is up, units
are meters, and the origin is the anchor written in `manifest.json` (`origin` explains it when it
is not the bottom-center: hanging pieces hang from y = 0).

The generator loads this folder when `[build] kits` lists "tounes" (the default) and names the
pieces `tounes/<piece>`. Which piece goes where is decided in `styles/maghreb.toml` under
`[dressing.roles]`. See every piece in 3D: `python -m citygen kit-sheet`.

Changes made here by hand: `awning_canvas` uses the `tr_canvas` material (`materials_map`), so
the canvas no longer glows like a lamp.
