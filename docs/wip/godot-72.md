# Prompt 72 (C3a Godot stream the city) - helper notes
Worktree /tmp/claude-501/godot-72, branch wip/godot-72 at c48fb1e. Godot NOT installed on this Mac.
## Done
- 19:45 UTC: read prompt, SPEC 6 tiles/quantization/instancing notes; build --quick + fingerprint save before started.
## Plan
- engine/godot/: project.godot, main.tscn, scripts/city_streamer.gd, scripts/citygen_instancing.gd (GLTFDocumentExtension),
  tools/check.gd, README.md. Tile root placed in GDScript doubles at (x0-focus.x, 0, -(y0-focus.y)).
## Next step
- verify Godot 4.3 gltf_document.cpp extension support (KHR_mesh_quantization, EXT_mesh_gpu_instancing).
## Findings (from Godot source, gltf_document.cpp at 4.3/4.4/4.5-stable/master)
- No built-in KHR_mesh_quantization nor EXT_mesh_gpu_instancing in any version: extensionsRequired check fails -> our GLTFDocumentExtension must list both in _get_supported_extensions.
- Normalized SHORT decoded as s/32768 (spec s/32767): positions 8 mm short at the box edge -> scale vertices by 32768/32767 (BYTE 128/127).
- Primitives without NORMAL: Godot generates NO normals and runs SurfaceTool.index() (merges split vertices) -> extension deindexes and writes flat face normals, re-indexes.
- Runtime generate_scene gives ImporterMeshInstance3D, converted by built-in GLTFDocumentExtensionConvertImporterMesh in import_post.
- External image uris: ResourceLoader.load(abs png/jpg) prints "No loader found" then reads bytes, per tile -> preflight strips images/textures, post_parse sets shared cached ImageTexture + uv1_scale.
- 19:53: written engine/godot/{project.godot, main.tscn, .gitignore, README.md, scripts/citygen_gltf.gd, scripts/citygen_tiles.gd, scripts/city_streamer.gd, scripts/fly_camera.gd, tools/check.gd}. Next: python test tests/test_godot_project.py, SPEC 6 "Other engines" paragraph update, pytest, build --quick, fingerprint compare.
- 19:54: tests/test_godot.py (3 static checks: res:// links, tab-only GDScript indent, extension covers every KHR/EXT name the writer uses) passes; SPEC 6 "Other engines" paragraph replaced by "Godot 4 (prompt 72 ...)" with the findings. Full pytest + build --quick + fingerprint compare running.

## Drafts for the lead (lead commits; helper did not touch these files)
ROADMAP line 89: `- [x] 72 C3a Godot: stream the city (engine/godot/; written against Godot 4.3-4.5 source, not run: Ali checks Play and tools/check.gd)`
  (Maybe keep [ ] until Ali has pressed Play: the prompt's Done-when is Ali's look.)
WORKLOG entry:
  ## 2026-11-03 - Prompt 72 C3a Godot 4: stream the city
  - engine/godot/ (Godot 4.3+): main.tscn (sky, sun, fly camera, City streamer), scripts/city_streamer.gd
    (viewer-like streaming: lod1 everywhere, full <1400 m / lod1 >1700 m, radius 2500 m, 3 loads on
    WorkerThreadPool, load-then-swap, full freed, lod1 kept; floating origin at index focus, tile root
    set in double precision), scripts/citygen_gltf.gd (GLTFDocumentExtension: KHR_mesh_quantization
    + exact 32767 dequant, flat normals for NORMAL-less surfaces, EXT_mesh_gpu_instancing ->
    MultiMeshInstance3D, shared textures decoded once), scripts/citygen_tiles.gd, tools/check.gd, README.md.
  - Findings from gltf_document.cpp 4.3/4.4/4.5/master: see SPEC 6 "Godot 4 (prompt 72)".
  - Godot not installed: nothing run. tests/test_godot.py static checks. Fingerprint: (fill in).
  - Ali: install Godot 4.3+ (free, ~100 MB) and press Play; or run tools/check.gd headless.
HANDOFF lessons:
  - Godot's runtime glTF reader (all 4.x to master) has no KHR_mesh_quantization / EXT_mesh_gpu_instancing; it
    divides normalized SHORT by 32768; NORMAL-less primitives get no normals and their split vertices merged.
  - Runtime generate_scene makes ImporterMeshInstance3D; the built-in GLTFDocumentExtensionConvertImporterMesh
    turns them into MeshInstance3D in import_post, so fix meshes on ImporterMesh in _import_post_parse.
  - External image uris: Godot first tries ResourceLoader.load (error "No loader found" outside res://),
    then decodes the bytes, per file: strip them in _import_preflight and share one ImageTexture.
  - Use preload() not class_name in scripts that `godot --script` runs (no global class cache before the editor scans).
  - Headless (dummy renderer): read ArrayMesh surface_get_format / array lengths, not surface_get_arrays.
- 20:08: full pytest 166 passed (780 s, machine loaded by other helpers); build --quick done (tiles reused); fingerprint compare: 282 parts, 0 changed.
## Status: code complete, NOT run in Godot (not installed). Not committed (lead commits).
Files: engine/godot/** (new), tests/test_godot.py (new), docs/SPEC.md (Godot paragraph in section 6 replaced).
## Exact next step
- Lead: review, add WORKLOG/HANDOFF/ROADMAP from the drafts above, commit.
- Ali (needs his yes to install Godot 4.3+): open engine/godot/project.godot, press Play; or
  `/Applications/Godot.app/Contents/MacOS/Godot --headless --path engine/godot --script res://tools/check.gd`
  expect "failures 0", MultiMesh instances > 0, surfaces without normals 0. If a GDScript parse error shows, fix it in the named file.
