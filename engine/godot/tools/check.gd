extends SceneTree
## Headless check of a build (prompt 72):
##   godot --headless --path engine/godot --script res://tools/check.gd -- [--build=FOLDER] [--max=N]
## Loads every tile of tiles/index.json (full and lod1) the way the game does and prints, per tile and
## in all, the mesh nodes, MultiMesh nodes and instances, triangles, and surfaces without normals.
## Exits with 1 when a tile fails to load, a surface has no normals, or a tile root is not shifted
## next to the focus point.

const CitygenTiles := preload("res://scripts/citygen_tiles.gd")
const CitygenGltf := preload("res://scripts/citygen_gltf.gd")


func _init() -> void:
	var limit := -1
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--max="):
			limit = arg.trim_prefix("--max=").to_int()
	var build := CitygenTiles.find_build()
	var index: Dictionary = {}
	if not build.is_empty():
		index = CitygenTiles.read_index(build)
	if index.is_empty():
		print("check: no build (run python -m citygen build --quick, or pass -- --build=FOLDER)")
		quit(1)
		return
	CitygenTiles.ensure_extension()
	var f: Dictionary = index["focus"]
	var focus := Vector2(f["x"], f["y"])
	var size: float = index.get("tile_size", 512)
	var totals := {}
	var failures := 0
	var tiles := 0
	var loaded_files := 0
	var started := Time.get_ticks_msec()
	print("check: %s (Godot %s)" % [build, Engine.get_version_info()["string"]])
	for entry in index["tiles"]:
		if limit >= 0 and tiles >= limit:
			break
		tiles += 1
		var files := [entry["file"]]
		if entry.has("lod1"):
			files.append(entry["lod1"]["file"])
		for file in files:
			loaded_files += 1
			var t0 := Time.get_ticks_msec()
			var scene := CitygenTiles.load_tile(build.path_join("tiles").path_join(file), entry["x0"], entry["y0"], focus)
			if scene == null:
				print("  FAIL %s: not loaded" % file)
				failures += 1
				continue
			var root := scene.get_child(0) as Node3D
			var spot := Vector2(root.position.x, -root.position.z) + focus
			if spot.distance_to(Vector2(entry["x0"], entry["y0"])) > 0.01 or root.position.length() > 50.0 * size:
				print("  FAIL %s: tile root at %s" % [file, root.position])
				failures += 1
			var c := CitygenTiles.count(scene, {})
			for key in c:
				totals[key] = totals.get(key, 0) + c[key]
			if c.get("no_normals", 0) > 0:
				failures += 1
			print("  %-26s meshes %4d  multimeshes %4d  instances %6d  triangles %8d  no normals %d  [%d ms]" % [
					file, c.get("meshes", 0), c.get("multimeshes", 0), c.get("instances", 0), c.get("triangles", 0),
					c.get("no_normals", 0), Time.get_ticks_msec() - t0])
			scene.free()
	print("check: tiles %d, files %d, mesh nodes %d, MultiMesh nodes %d, MultiMesh instances %d, triangles %d, surfaces without normals %d, shared textures %d, failures %d [%.1f s]" % [
			tiles, loaded_files, totals.get("meshes", 0), totals.get("multimeshes", 0),
			totals.get("instances", 0), totals.get("triangles", 0), totals.get("no_normals", 0),
			CitygenGltf.cached_texture_count(), failures, (Time.get_ticks_msec() - started) / 1000.0])
	quit(1 if failures > 0 else 0)
