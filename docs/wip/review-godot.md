# Review of wip/godot-72 (prompt 72, Godot 4 streaming) - review-godot, 3 November
Scope: `git diff c48fb1e..ab0ebcc` (engine/godot/**, tests/test_godot.py, SPEC 6 paragraph). Godot not installed: read only, nothing run in Godot. Severity: high = would break the import or the look, medium = wrong in some cases, low = polish.

## Findings (file:line, severity, one-line fix)
- engine/godot/scripts/citygen_gltf.gd:147-150, medium: the 32768/32767 factor is hard-coded on the claim that Godot divides SHORT by 32768; if a Godot release fixes that to 32767, every position grows by 1/32767 (8 mm at a tile edge) with no warning. Fix: measure the factor per accessor (one decoded vertex from `read_accessor` vs Godot's vertex) instead of a constant, or check `Engine.get_version_info()` against the versions read.
- engine/godot/scripts/citygen_gltf.gd:155, medium: if Godot drops a primitive (empty or unsupported mode), `get_surface_count() != primitives.size()` makes `_fix_mesh` skip the WHOLE mesh silently (no flat normals, no exact positions). Fix: push_warning there, and match surfaces by order of kept primitives.
- engine/godot/scripts/citygen_gltf.gd:178, low: `add_surface(..., {}, material, name)` drops the surface flags Godot set (attribute compression), so meshes use more memory than a normal import. Fix: pass `mesh.get_surface_format(s)`-derived flags (or accept and note it).
- engine/godot/scripts/citygen_gltf.gd:122-134, low: the texture lock is held while a JPG is decoded and mipmapped, so the 3 worker threads queue behind the first texture decode at start. Fix: decode outside the lock, then insert under it (keep the first one stored).
- engine/godot/scripts/citygen_gltf.gd:49-51, low: `texCoord` other than 0 and KHR_texture_transform `rotation` are ignored without a word. Fix: return OK (leave the file to Godot) when either is present.
- engine/godot/scripts/citygen_tiles.gd:26 and :126, low: `globalize_path("res://")` and `Image.load_from_file(abs path)` only work when the project runs from its folder (editor or `godot --path`), not from an exported game. Fix: say so in README (it is a viewer for builds on disk, which is the intent).
- engine/godot/scripts/citygen_gltf.gd:162, medium: "needs flat normals" is decided by Godot's arrays (`ARRAY_NORMAL == null`), so a Godot version that fills in smooth normals itself would leave boxes soft-shaded with no warning. Fix: decide from the JSON (`not primitives[s]["attributes"].has("NORMAL")`) and always write the flat ones.
- engine/godot/scripts/citygen_gltf.gd:94, low: an ImporterMesh used by both an instanced node and a plain node becomes two ArrayMeshes (this `get_mesh()` and Godot's own conversion). Fix: none needed now (the writer gives each instance set its own mesh, gltf.py:454-456).
- engine/godot/scripts/citygen_gltf.gd:209 and citygen_tiles.gd:125, low: integer divisions raise GDScript INTEGER_DIVISION warnings (harmless unless warnings are set to errors). Fix: `int(t.size() / 3.0)` or `@warning_ignore("integer_division")`.
- tests/test_godot.py, medium: all three tests are static text checks; nothing parses GDScript, so a typo or a wrong API name only shows when Ali presses Play. Fix: when a `godot` binary is on PATH, run `tools/check.gd` headless in a test marked `slow` (skipped otherwise).

## Checked and right
- Axes and placement: the writer puts each tile root at (x0, 0, -y0) (citygen/mesh/tile.py:888, lod.py:617) and load_tile replaces it with the same point minus the focus (citygen_tiles.gd:89): consistent, Y up, -Z north; `to_godot` matches. The quantized "<name>_q" child keeps its own translation and scale (gltf.py:430-431), untouched.
- Index keys used by the streamer (tile_size, focus x/y/z/name, views cam/look, tiles i/j/x0/y0/file, lod1.file) all exist in citygen/build.py:343-348 and tile.py:894.
- Instances: quaternion order (x, y, z, w), T * R * S, normalized SHORT rotations / 32767 (glTF 3.11 rule): right.
- Flat normal direction after Godot's winding swap: (p2 - p0) x (p1 - p0) is the glTF outward normal (cyclic order kept): right.
- Units meters on both sides; no scale change needed.

## Left (time ran out)
- tools/check.gd, main.tscn, fly_camera.gd, project.godot and the SPEC 6 paragraph not read line by line.
- Godot source claims (32768 divisor, no generated normals, extensionsRequired check after preflight) taken from the helper's notes, not re-checked.
