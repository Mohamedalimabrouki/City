extends GLTFDocumentExtension
## Reads the parts of citygen tiles that Godot's glTF importer does not (checked in the source of
## modules/gltf/gltf_document.cpp for 4.3, 4.4, 4.5 and master):
## - KHR_mesh_quantization: Godot decodes normalized integers, but refuses a file that requires the
##   extension unless an extension lists it, divides SHORT by 32768 (the glTF rule is 32767: 8 mm short
##   at the edge of a 550 m tile) and gives primitives without NORMAL no normals at all (after merging
##   their split vertices). Here every such surface gets its flat face normals back.
## - EXT_mesh_gpu_instancing: each instanced node becomes a MultiMeshInstance3D; TRANSLATION, ROTATION
##   and SCALE are decoded by component type and `normalized` flag (rotations are 16-bit, SPEC 6).
## - Shared textures (tiles/textures/*.jpg): each image is decoded once for the whole session and
##   shared by every tile, with the KHR_texture_transform scale (meters per repeat).

const QUANT := "KHR_mesh_quantization"
const INSTANCING := "EXT_mesh_gpu_instancing"
const TEXTURES_KEY := &"citygen_textures"
const INSTANCES_KEY := &"citygen_instances"

static var _texture_cache := {}   # absolute image path -> ImageTexture
static var _texture_lock := Mutex.new()


func _get_supported_extensions() -> PackedStringArray:
	return PackedStringArray([QUANT, INSTANCING])


## Before Godot parses the file: take shared (external) images out of the JSON, so they are not
## decoded again for every tile, and remember which material uses which image and transform.
func _import_preflight(state: GLTFState, _extensions: PackedStringArray) -> Error:
	var json: Dictionary = state.json
	var images: Array = json.get("images", [])
	if images.is_empty() or state.base_path.is_empty():
		return OK
	for image in images:
		if not image.has("uri") or String(image["uri"]).begins_with("data:"):
			return OK   # embedded images: Godot reads them itself
	var textures: Array = json.get("textures", [])
	var materials: Array = json.get("materials", [])
	var plan := {}
	for m in materials.size():
		var material: Dictionary = materials[m]
		for key in ["normalTexture", "occlusionTexture", "emissiveTexture"]:
			if material.has(key):
				return OK   # a texture kind this reader does not handle: leave the file to Godot
		var pbr: Dictionary = material.get("pbrMetallicRoughness", {})
		if pbr.has("metallicRoughnessTexture"):
			return OK
		if not pbr.has("baseColorTexture"):
			continue
		var ref: Dictionary = pbr["baseColorTexture"]
		var source := int(textures[int(ref["index"])]["source"])
		var uri := String(images[source]["uri"]).uri_decode()
		var transform: Dictionary = ref.get("extensions", {}).get("KHR_texture_transform", {})
		plan[m] = {
			"path": state.base_path.path_join(uri),
			"scale": transform.get("scale", [1.0, 1.0]),
			"offset": transform.get("offset", [0.0, 0.0]),
		}
	for m in plan:
		materials[m]["pbrMetallicRoughness"].erase("baseColorTexture")
	json.erase("images")
	json.erase("textures")
	json.erase("samplers")
	state.json = json
	state.set_additional_data(TEXTURES_KEY, plan)
	return OK


## After Godot parsed meshes and materials: textures, exact dequantization, flat normals, instances.
func _import_post_parse(state: GLTFState) -> Error:
	var json: Dictionary = state.json
	var buffers: Array = state.get_buffers()
	_apply_textures(state)
	var meshes: Array = state.get_meshes()
	var json_meshes: Array = json.get("meshes", [])
	for m in mini(meshes.size(), json_meshes.size()):
		_fix_mesh(json, meshes[m].mesh, json_meshes[m].get("primitives", []))
	var nodes: Array = state.get_nodes()
	var json_nodes: Array = json.get("nodes", [])
	for n in mini(nodes.size(), json_nodes.size()):
		var ext: Dictionary = json_nodes[n].get("extensions", {}).get(INSTANCING, {})
		if not ext.is_empty():
			nodes[n].set_additional_data(INSTANCES_KEY, _instance_transforms(json, buffers, ext.get("attributes", {})))
	return OK


## An instanced node becomes one MultiMeshInstance3D (Godot then names it and sets its transform).
func _generate_scene_node(state: GLTFState, gltf_node: GLTFNode, _scene_parent: Node) -> Node3D:
	var transforms = gltf_node.get_additional_data(INSTANCES_KEY)
	if transforms == null or gltf_node.mesh < 0:
		return null
	var importer_mesh: ImporterMesh = state.get_meshes()[gltf_node.mesh].mesh
	var multimesh := MultiMesh.new()
	multimesh.transform_format = MultiMesh.TRANSFORM_3D
	multimesh.mesh = importer_mesh.get_mesh()
	multimesh.instance_count = transforms.size()
	for k in transforms.size():
		multimesh.set_instance_transform(k, transforms[k])
	var node := MultiMeshInstance3D.new()
	node.multimesh = multimesh
	return node


func _apply_textures(state: GLTFState) -> void:
	var plan = state.get_additional_data(TEXTURES_KEY)
	if plan == null:
		return
	var materials: Array = state.get_materials()
	for m in plan:
		var material := materials[m] as BaseMaterial3D
		var texture := _shared_texture(plan[m]["path"])
		if material == null or texture == null:
			continue
		var scale: Array = plan[m]["scale"]
		var offset: Array = plan[m]["offset"]
		material.albedo_texture = texture
		material.uv1_scale = Vector3(scale[0], scale[1], 1.0)
		material.uv1_offset = Vector3(offset[0], offset[1], 0.0)
		material.texture_filter = BaseMaterial3D.TEXTURE_FILTER_LINEAR_WITH_MIPMAPS_ANISOTROPIC
		material.texture_repeat = true


static func _shared_texture(path: String) -> Texture2D:
	_texture_lock.lock()
	var texture: Texture2D = _texture_cache.get(path)
	if texture == null:
		var image := Image.load_from_file(path)
		if image != null:
			image.generate_mipmaps()
			texture = ImageTexture.create_from_image(image)
			_texture_cache[path] = texture
		else:
			push_warning("citygen: cannot read texture " + path)
	_texture_lock.unlock()
	return texture


static func cached_texture_count() -> int:
	return _texture_cache.size()


## Exact dequantization factor of a primitive's positions (Godot divides SHORT by 32768, BYTE by 128).
static func _position_factor(json: Dictionary, primitive: Dictionary) -> float:
	var accessor: Dictionary = json["accessors"][int(primitive["attributes"]["POSITION"])]
	if not accessor.get("normalized", false):
		return 1.0
	match int(accessor["componentType"]):
		5122:
			return 32768.0 / 32767.0
		5120:
			return 128.0 / 127.0
	return 1.0


func _fix_mesh(json: Dictionary, mesh: ImporterMesh, primitives: Array) -> void:
	if mesh == null or mesh.get_surface_count() != primitives.size():
		return
	var surfaces := []
	var changed := false
	for s in mesh.get_surface_count():
		var arrays := mesh.get_surface_arrays(s)
		var factor := _position_factor(json, primitives[s])
		var needs_normals: bool = arrays[Mesh.ARRAY_NORMAL] == null
		if factor != 1.0:
			var vertices: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			for i in vertices.size():
				vertices[i] *= factor
			arrays[Mesh.ARRAY_VERTEX] = vertices
		if needs_normals:
			arrays = _with_flat_normals(arrays)
		changed = changed or factor != 1.0 or needs_normals
		surfaces.append({"arrays": arrays, "material": mesh.get_surface_material(s), "name": mesh.get_surface_name(s),
				"primitive": mesh.get_surface_primitive_type(s)})
	if not changed:
		return
	mesh.clear()
	var no_blend_shapes: Array[Array] = []
	for surface in surfaces:
		mesh.add_surface(surface["primitive"], surface["arrays"], no_blend_shapes, {}, surface["material"], surface["name"])


## Flat normals for a surface written without NORMAL (glTF: flat when absent). Godot already swapped
## the winding to clockwise, so the outward normal of (p0, p1, p2) is (p2 - p0) x (p1 - p0).
static func _with_flat_normals(arrays: Array) -> Array:
	var tool := SurfaceTool.new()
	tool.create_from_arrays(arrays, Mesh.PRIMITIVE_TRIANGLES)
	tool.deindex()
	var flat := tool.commit_to_arrays()
	var vertices: PackedVector3Array = flat[Mesh.ARRAY_VERTEX]
	var normals := PackedVector3Array()
	normals.resize(vertices.size())
	for t in range(0, vertices.size() - 2, 3):
		var p0 := vertices[t]
		var normal := (vertices[t + 2] - p0).cross(vertices[t + 1] - p0).normalized()
		normals[t] = normal
		normals[t + 1] = normal
		normals[t + 2] = normal
	flat[Mesh.ARRAY_NORMAL] = normals
	tool = SurfaceTool.new()
	tool.create_from_arrays(flat, Mesh.PRIMITIVE_TRIANGLES)
	tool.index()   # merges corners that share position, UV and normal again
	return tool.commit_to_arrays()


## Instance transforms T * R * S, local to the instanced node (EXT_mesh_gpu_instancing).
static func _instance_transforms(json: Dictionary, buffers: Array, attributes: Dictionary) -> Array:
	var t := read_accessor(json, buffers, attributes.get("TRANSLATION", -1))
	var r := read_accessor(json, buffers, attributes.get("ROTATION", -1))
	var s := read_accessor(json, buffers, attributes.get("SCALE", -1))
	var count := maxi(t.size() / 3, maxi(r.size() / 4, s.size() / 3))
	var out := []
	out.resize(count)
	for k in count:
		var basis := Basis.IDENTITY
		if r.size() >= 4 * (k + 1):
			basis = Basis(Quaternion(r[4 * k], r[4 * k + 1], r[4 * k + 2], r[4 * k + 3]).normalized())
		if s.size() >= 3 * (k + 1):
			basis = basis * Basis.from_scale(Vector3(s[3 * k], s[3 * k + 1], s[3 * k + 2]))
		var origin := Vector3.ZERO
		if t.size() >= 3 * (k + 1):
			origin = Vector3(t[3 * k], t[3 * k + 1], t[3 * k + 2])
		out[k] = Transform3D(basis, origin)
	return out


## Flat values of an accessor, honoring byteStride, the component type and the normalized flag
## (glTF 2.0 3.11: signed normalized c -> max(c / (2^(n-1) - 1), -1), unsigned c -> c / (2^n - 1)).
static func read_accessor(json: Dictionary, buffers: Array, index) -> PackedFloat64Array:
	var out := PackedFloat64Array()
	if index == null or int(index) < 0:
		return out
	var accessor: Dictionary = json["accessors"][int(index)]
	var comps: int = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}.get(accessor["type"], 1)
	var kind := int(accessor["componentType"])
	var size: int = {5120: 1, 5121: 1, 5122: 2, 5123: 2, 5125: 4, 5126: 4}[kind]
	var normalized: bool = accessor.get("normalized", false)
	var count := int(accessor["count"])
	if not accessor.has("bufferView"):
		out.resize(count * comps)   # all zeros (glTF: an accessor without bufferView)
		return out
	var view: Dictionary = json["bufferViews"][int(accessor["bufferView"])]
	var data: PackedByteArray = buffers[int(view.get("buffer", 0))]
	var stride := int(view.get("byteStride", comps * size))
	var base := int(view.get("byteOffset", 0)) + int(accessor.get("byteOffset", 0))
	out.resize(count * comps)
	for e in count:
		for c in comps:
			var at := base + e * stride + c * size
			var v := 0.0
			match kind:
				5126:
					v = data.decode_float(at)
				5122:
					v = data.decode_s16(at)
					if normalized:
						v = maxf(v / 32767.0, -1.0)
				5123:
					v = data.decode_u16(at)
					if normalized:
						v /= 65535.0
				5120:
					v = data.decode_s8(at)
					if normalized:
						v = maxf(v / 127.0, -1.0)
				5121:
					v = data.decode_u8(at)
					if normalized:
						v /= 255.0
				5125:
					v = data.decode_u32(at)
			out[e * comps + c] = v
	return out
