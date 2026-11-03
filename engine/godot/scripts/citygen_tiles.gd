extends RefCounted
## Shared helpers for the streamer and the headless check: find a build, read its tiles/index.json
## (citygen-tiles/1, SPEC 6) and load one tile with GLTFDocument and the citygen extension.
## Used through preload(), not class_name, so `godot --script` works before the editor has
## ever scanned the project.

const CitygenGltf := preload("res://scripts/citygen_gltf.gd")

static var _extension: GLTFDocumentExtension = null


static func ensure_extension() -> void:
	if _extension == null:
		_extension = CitygenGltf.new()
		GLTFDocument.register_gltf_document_extension(_extension)


## The build folder to show: `--build=<folder>` after `--` on the command line, else `preferred`,
## else the build with the newest tiles/index.json under the repository's output/ folder.
static func find_build(preferred: String = "") -> String:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("--build="):
			return _absolute(arg.trim_prefix("--build="))
	if not preferred.is_empty():
		return _absolute(preferred)
	var output := ProjectSettings.globalize_path("res://").path_join("../../output").simplify_path()
	var best := ""
	var newest := -1
	for folder in _children(output) + _grandchildren(output):
		var index := folder.path_join("tiles/index.json")
		if FileAccess.file_exists(index) and FileAccess.get_modified_time(index) > newest:
			newest = FileAccess.get_modified_time(index)
			best = folder
	return best


static func _absolute(path: String) -> String:
	if path.is_absolute_path():
		return path.simplify_path()
	return ProjectSettings.globalize_path("res://").path_join(path).simplify_path()


static func _children(folder: String) -> Array:
	var out := []
	var dir := DirAccess.open(folder)
	if dir == null:
		return out
	for name in dir.get_directories():
		out.append(folder.path_join(name))
	return out


static func _grandchildren(folder: String) -> Array:
	var out := []
	for child in _children(folder):
		out += _children(child)
	return out


## The parsed index of a build folder, or {} with an error printed.
static func read_index(build: String) -> Dictionary:
	var path := build.path_join("tiles/index.json")
	var text := FileAccess.get_file_as_string(path)
	if text.is_empty():
		push_error("citygen: no tiles/index.json in " + build + " (run: python -m citygen build --quick)")
		return {}
	var index = JSON.parse_string(text)
	if typeof(index) != TYPE_DICTIONARY or index.get("format", "") != "citygen-tiles/1":
		push_error("citygen: " + path + " is not a citygen-tiles/1 index")
		return {}
	return index


## Load one .glb tile into a new scene (not in the tree). The tile root is moved to
## (x0 - focus.x, 0, -(y0 - focus.y)), computed in double precision here, so no float32 vertex is
## ever placed kilometers from the origin (the web viewer's rebase, SPEC 6).
static func load_tile(path: String, x0: float, y0: float, focus: Vector2) -> Node3D:
	ensure_extension()
	var document := GLTFDocument.new()
	var state := GLTFState.new()
	var err := document.append_from_file(path, state)
	if err != OK:
		push_error("citygen: cannot read %s (error %d)" % [path, err])
		return null
	var scene := document.generate_scene(state) as Node3D
	if scene == null:
		return null
	if scene.get_child_count() > 0 and scene.get_child(0) is Node3D:
		scene.get_child(0).position = Vector3(x0 - focus.x, 0.0, -(y0 - focus.y))
	return scene


## Generator coordinates (x east, y north, z up) to the shifted Godot space (Y up, -Z north).
static func to_godot(x: float, y: float, z: float, focus: Vector2) -> Vector3:
	return Vector3(x - focus.x, z, -(y - focus.y))


## Counts for the check and the stats line: mesh nodes, MultiMesh nodes and their instances, and
## surfaces left without normals (must be 0: the extension gives them flat normals).
static func count(node: Node, totals: Dictionary) -> Dictionary:
	if node is MultiMeshInstance3D and node.multimesh != null:
		totals["multimeshes"] = totals.get("multimeshes", 0) + 1
		totals["instances"] = totals.get("instances", 0) + node.multimesh.instance_count
		_count_mesh(node.multimesh.mesh, totals)
	elif node is MeshInstance3D and node.mesh != null:
		totals["meshes"] = totals.get("meshes", 0) + 1
		_count_mesh(node.mesh, totals)
	for child in node.get_children():
		count(child, totals)
	return totals


static func _count_mesh(mesh: Mesh, totals: Dictionary) -> void:
	# Format and lengths are kept on the mesh itself, so this also works with --headless (dummy renderer).
	if mesh == null:
		return
	for s in mesh.get_surface_count():
		totals["surfaces"] = totals.get("surfaces", 0) + 1
		if mesh is ArrayMesh:
			if not (mesh.surface_get_format(s) & Mesh.ARRAY_FORMAT_NORMAL):
				totals["no_normals"] = totals.get("no_normals", 0) + 1
			var corners: int = mesh.surface_get_array_index_len(s)
			if corners <= 0:
				corners = mesh.surface_get_array_len(s)
			totals["triangles"] = totals.get("triangles", 0) + corners / 3
