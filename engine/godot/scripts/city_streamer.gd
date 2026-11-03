extends Node3D
## Streams a citygen build around the camera, like the web viewer (SPEC 6, prompt 41): every tile
## of the build shows its light lod1 version; tiles near the camera load their full version, which
## replaces the lod1 one once it is ready (load, then swap: no hole, no double); full tiles that
## fall far behind are freed. Loading runs on worker threads, at most `max_loads` at a time.
## The focus point of the index is Godot's origin (floating origin), see CitygenTiles.load_tile.

const CitygenTiles := preload("res://scripts/citygen_tiles.gd")

## Build folder (with tiles/index.json); empty = the newest build in the repository's output/.
@export var build_folder := ""
## Full tiles turn on under this distance (m, camera to the tile square) ...
@export var full_in := 1400.0
## ... and back to lod1 over this one (the band between keeps what is shown).
@export var full_out := 1700.0
## No full tile beyond this ground distance from the camera, whatever the height (m).
@export var full_radius := 2500.0
## Tiles loading at the same time.
@export var max_loads := 3
## Camera to follow (defaults to the viewport camera).
@export var camera_path: NodePath
## Start the camera at this view of the index ("street", "souk", "port", ...), if the city has it.
@export var start_view := "street"

var index := {}
var build := ""
var focus := Vector2.ZERO      # generator x, y of the focus point: the Godot origin
var focus_height := 0.0
var tile_size := 512.0
var slots := {}                # "i_j" -> {entry, lod1, full, want, loading}
var _loading := 0
var _since_update := 0.0
var _tasks := {}               # WorkerThreadPool task id -> true while it runs


func _ready() -> void:
	build = CitygenTiles.find_build(build_folder)
	if build.is_empty():
		push_error("citygen: no build found; run `python -m citygen build --quick` first")
		return
	index = CitygenTiles.read_index(build)
	if index.is_empty():
		return
	CitygenTiles.ensure_extension()
	var f: Dictionary = index.get("focus", {})
	focus = Vector2(f.get("x", 0.0), f.get("y", 0.0))
	focus_height = f.get("z", 0.0)
	tile_size = index.get("tile_size", 512)
	for entry in index.get("tiles", []):
		slots["%d_%d" % [entry["i"], entry["j"]]] = {"entry": entry, "lod1": null, "full": null, "want": "", "loading": ""}
	print("citygen: %s, %d tiles, focus %s at (%.1f, %.1f)" % [build, slots.size(), f.get("name", "?"), focus.x, focus.y])
	_place_camera()
	_update_wants()


func _exit_tree() -> void:
	for task in _tasks.keys():
		WorkerThreadPool.wait_for_task_completion(task)
	_tasks.clear()


func _camera() -> Camera3D:
	var camera := get_node_or_null(camera_path) as Camera3D
	return camera if camera != null else get_viewport().get_camera_3d()


func _place_camera() -> void:
	var camera := _camera()
	if camera == null:
		return
	var view: Dictionary = index.get("views", {}).get(start_view, {})
	if view.has("cam") and view.has("look"):
		var c: Array = view["cam"]
		var l: Array = view["look"]
		camera.position = CitygenTiles.to_godot(c[0], c[1], c[2], focus)
		camera.look_at(CitygenTiles.to_godot(l[0], l[1], l[2], focus))
	else:
		camera.position = Vector3(0.0, focus_height + 120.0, 260.0)
		camera.look_at(Vector3(0.0, focus_height, 0.0))


func _process(delta: float) -> void:
	_since_update += delta
	if _since_update >= 0.25 and not slots.is_empty():
		_since_update = 0.0
		_update_wants()


## Generator coordinates of the camera (x, y on the ground and its height over the focus).
func _camera_spot() -> Vector3:
	var camera := _camera()
	var p := camera.global_position if camera != null else Vector3.ZERO
	return Vector3(p.x + focus.x, focus.y - p.z, maxf(0.0, p.y - focus_height))


func _square_distance(entry: Dictionary, x: float, y: float) -> float:
	var x0: float = entry["x0"]
	var y0: float = entry["y0"]
	var dx := maxf(maxf(x0 - x, 0.0), x - (x0 + tile_size))
	var dy := maxf(maxf(y0 - y, 0.0), y - (y0 + tile_size))
	return sqrt(dx * dx + dy * dy)


func _update_wants() -> void:
	var spot := _camera_spot()
	var order := []
	for key in slots:
		var slot: Dictionary = slots[key]
		var ground := _square_distance(slot["entry"], spot.x, spot.y)
		var d := sqrt(ground * ground + spot.z * spot.z)
		var want: String = slot["want"]
		if want == "":
			want = "full" if d < (full_in + full_out) * 0.5 else "lod1"
		elif d < full_in:
			want = "full"
		elif d > full_out:
			want = "lod1"
		if ground > full_radius or not slot["entry"].has("file"):
			want = "lod1"
		if want == "lod1" and not slot["entry"].has("lod1"):
			want = "full"   # a build without lod1 files (before prompt 40) shows full tiles only
		slot["want"] = want
		order.append([d, key])
		_show(slot)
	order.sort_custom(func(a, b): return a[0] < b[0])
	# lod1 first for every tile showing nothing (nearest first), then full tiles by distance
	for kind in ["lod1", "full"]:
		for item in order:
			if _loading >= max_loads:
				return
			var slot: Dictionary = slots[item[1]]
			if slot["loading"] != "" or slot[kind] != null:
				continue
			if kind == "lod1" and slot["entry"].has("lod1"):
				_start_load(item[1], "lod1")
			elif kind == "full" and slot["want"] == "full":
				_start_load(item[1], "full")


func _start_load(key: String, kind: String) -> void:
	var slot: Dictionary = slots[key]
	var entry: Dictionary = slot["entry"]
	var file: String = entry["lod1"]["file"] if kind == "lod1" else entry["file"]
	slot["loading"] = kind
	_loading += 1
	var path := build.path_join("tiles").path_join(file)
	var task := WorkerThreadPool.add_task(_load_task.bind(key, kind, path, float(entry["x0"]), float(entry["y0"])), false, "citygen tile")
	_tasks[task] = true


func _load_task(key: String, kind: String, path: String, x0: float, y0: float) -> void:
	var scene := CitygenTiles.load_tile(path, x0, y0, focus)
	_loaded.call_deferred(key, kind, scene)


func _loaded(key: String, kind: String, scene: Node3D) -> void:
	_loading -= 1
	for task in _tasks.keys():
		if WorkerThreadPool.is_task_completed(task):
			WorkerThreadPool.wait_for_task_completion(task)
			_tasks.erase(task)
	var slot: Dictionary = slots[key]
	slot["loading"] = ""
	if scene == null:
		slot["entry"].erase("file" if kind == "full" else "lod1")   # do not retry a broken file
		return
	if kind == "full" and slot["want"] != "full":
		scene.free()   # no longer wanted while it loaded: dropped unseen
		return
	scene.visible = false
	add_child(scene)
	slot[kind] = scene
	_show(slot)


## Show the wanted version once it is loaded; until then the other one stays (no frame shows a hole).
func _show(slot: Dictionary) -> void:
	var full: Node3D = slot["full"]
	var lod1: Node3D = slot["lod1"]
	if slot["want"] == "full" and full != null:
		full.visible = true
		if lod1 != null:
			lod1.visible = false   # kept in memory: turning back to lod1 is instant
	elif slot["want"] == "lod1" and lod1 != null:
		lod1.visible = true
		if full != null:
			full.queue_free()      # a full tile that leaves is freed
			slot["full"] = null
	elif lod1 != null and full == null:
		lod1.visible = true


## For the stats line and the check: shown full and lod1 tiles, loads in flight.
func counts() -> Dictionary:
	var out := {"full": 0, "lod1": 0, "loading": _loading}
	for key in slots:
		var slot: Dictionary = slots[key]
		if slot["full"] != null and slot["full"].visible:
			out["full"] += 1
		elif slot["lod1"] != null and slot["lod1"].visible:
			out["lod1"] += 1
	return out
